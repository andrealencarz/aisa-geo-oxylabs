#!/usr/bin/env python3
"""
Servidor MCP (Model Context Protocol) para o Oxylabs LLM via API AIsa.
Pergunta ao ChatGPT, Gemini e Perplexity como um usuário real e mede quais
marcas aparecem nas respostas (GEO). Executa via stdio (JSON-RPC 2.0) sem
dependências externas.
"""

import sys
import json
import os
import re
import time
import uuid
import unicodedata
import traceback
import secrets
import platform
import threading
import subprocess
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

SERVER_NAME = "aisa-oxylabs"
SERVER_VERSION = "0.5.0"
PROTOCOL_VERSION = "2025-06-18"

API_BASE = os.environ.get("AISA_API_BASE", "https://api.aisa.one").rstrip("/")
LLM_PATH = "/apis/v1/oxylabs/llm"
SOURCES = ("chatgpt", "gemini", "perplexity")
FINAL_STATUSES = ("completed", "failed", "cancelled")

SERVER_INSTRUCTIONS = (
    "Use estas ferramentas quando o usuário quiser saber o que ChatGPT, Gemini ou Perplexity "
    "respondem para uma pergunta, ou medir a presença de uma marca/empresa nas respostas de IA (GEO). "
    "Na primeira vez da conversa, chame 'verificar_configuracao'. Se a chave da AIsa não estiver configurada, "
    "a tela de configuração abre sozinha no navegador: avise o usuário, passe o link 'url' e espere ele salvar. "
    "Para configurar ou trocar a chave a pedido do usuário, chame 'abrir_configuracao'. Se o usuário colar a "
    "chave no chat, use 'configurar_chave_aisa'. Para relatórios com várias perguntas e concorrentes, use 'geo_visibilidade'. Antes de rodar lotes "
    "grandes, use 'oxylabs_llm_cotar' e informe o custo ao usuário. Cada pergunta é cobrada na conta AIsa."
)


# --------------------------------------------------------------------------- API AIsa

KEY_FILE = os.path.join(os.path.expanduser("~"), ".aisa_api_key")
MISSING_KEY = "Chave da AIsa não configurada."
CONFIG_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extensao", "server", "config.html")
CONFIG_TTL_S = 900
_key_override = None


def _api_key():
    if _key_override:
        return _key_override
    key = os.environ.get("AISA_API_KEY", "").strip()
    if (not key or key.startswith("${")) and os.path.isfile(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
    if not key or key.startswith("${"):
        raise RuntimeError(MISSING_KEY)
    return key


def save_key(key):
    """Testa a chave na AIsa e, se for aceita, guarda em ~/.aisa_api_key (só o usuário lê)."""
    global _key_override
    key = (key or "").strip()
    if not key.startswith("sk-"):
        return {"ok": False, "problema": "Isso não parece uma chave da AIsa: ela começa com sk-aisa-. Copie de novo em console.aisa.one."}
    previous, _key_override = _key_override, key
    result = check_setup()
    if not result.get("ok") and "recusou" in result.get("problema", ""):
        _key_override = previous
        return result
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    result["salva_em"] = KEY_FILE
    result["chave"] = _mask(key)
    if result.get("ok"):
        result["mensagem"] = "Chave salva e aceita pela AIsa. Não precisa configurar de novo."
    return result


def _mask(key):
    return key[:8] + "…" + key[-4:] if len(key) > 16 else "(curta demais)"


# --------------------------------------------------------------------------- Tela de configuração

_config = {"server": None, "url": None}


def _open_browser(url):
    system = platform.system()
    if system == "Darwin":
        cmd = ["open", url]
    elif system == "Windows":
        cmd = ["cmd", "/c", "start", "", url]
    else:
        cmd = ["xdg-open", url]
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


class _ConfigHandler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, *args):
        pass  # stdout é do protocolo MCP

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        base = "/" + self.token
        if self.path in (base, base + "/"):
            with open(CONFIG_HTML, encoding="utf-8") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == base + "/status":
            try:
                status = {"configurada": True, "chave": _mask(_api_key())}
            except RuntimeError:
                status = {"configurada": False}
            self._send(200, json.dumps(status, ensure_ascii=False))
        else:
            self._send(404, "{}")

    def do_POST(self):
        if self.path != "/" + self.token + "/salvar":
            return self._send(404, "{}")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            chave = json.loads(self.rfile.read(length) or b"{}").get("chave", "")
            result = save_key(chave)
        except Exception as e:
            result = {"ok": False, "problema": str(e)}
        result.pop("detalhe", None)
        self._send(200, json.dumps(result, ensure_ascii=False))


def open_config_page():
    """Abre no navegador uma página local para colar a chave da AIsa."""
    if _config["server"] is None:
        token = secrets.token_urlsafe(16)
        handler = type("Handler", (_ConfigHandler,), {"token": token})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def close():
            server.shutdown()
            server.server_close()
            _config.update(server=None, url=None)

        timer = threading.Timer(CONFIG_TTL_S, close)
        timer.daemon = True
        timer.start()
        _config.update(server=server, url="http://127.0.0.1:%d/%s" % (server.server_address[1], token))
    opened = _open_browser(_config["url"])
    return {
        "ok": True,
        "url": _config["url"],
        "aberta_no_navegador": opened,
        "mensagem": "Abri a tela de configuração no navegador. Cole a chave da AIsa, clique em 'Salvar e testar' "
                    "e volte aqui. Se a página não abriu, use o link. Ele vale por 15 minutos.",
    }


def _request(method, path, body=None, headers=None, timeout=60):
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + _api_key())
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"raw": raw[:2000]}
        raise RuntimeError("AIsa HTTP %s em %s %s: %s" % (e.code, method, path, json.dumps(payload, ensure_ascii=False)[:2000]))


def _body(source, prompt, geo_location=None, parse=True):
    source = (source or "").strip().lower()
    if source not in SOURCES:
        raise ValueError("source deve ser um de: %s" % ", ".join(SOURCES))
    if not (prompt or "").strip():
        raise ValueError("prompt vazio")
    body = {"source": source, "prompt": prompt.strip(), "parse": bool(parse)}
    if geo_location:
        body["geo_location"] = geo_location
    return body


def quote(source, prompt, geo_location=None):
    _, data = _request("POST", LLM_PATH, _body(source, prompt, geo_location),
                       headers={"Idempotency-Key": str(uuid.uuid4()), "X-AISA-Cost-Mode": "quote"})
    return data


def submit(source, prompt, geo_location=None, parse=True, max_price_usd=None):
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    if max_price_usd:
        headers["X-AISA-Max-Price-USD"] = str(max_price_usd)
    _, data = _request("POST", LLM_PATH, _body(source, prompt, geo_location, parse), headers=headers)
    return data


def get_job(job_id):
    _, data = _request("GET", "%s/%s" % (LLM_PATH, job_id))
    return data


def cancel_job(job_id):
    _, data = _request("POST", "%s/%s/cancel" % (LLM_PATH, job_id))
    return data


def list_jobs(status=None, limit=20, cursor=None):
    params = ["limit=%d" % int(limit)]
    if status:
        params.append("status=" + status)
    if cursor:
        params.append("cursor=" + urllib.request.quote(cursor))
    _, data = _request("GET", LLM_PATH + "?" + "&".join(params))
    return data


def wait_job(job, timeout_s=240, interval_s=4):
    deadline = time.time() + timeout_s
    while job.get("status") not in FINAL_STATUSES:
        if time.time() > deadline:
            job["timeout"] = True
            return job
        time.sleep(interval_s)
        job = get_job(job["id"])
    return job


# --------------------------------------------------------------------------- Extração da resposta

TEXT_KEYS = ("response_text", "markdown_text", "answer_text", "text", "answer", "content", "markdown")
LINK_KEYS = ("citations", "sources", "links", "references", "search_results")


def _find_text(node, depth=0):
    if depth > 8:
        return None
    if isinstance(node, dict):
        for k in TEXT_KEYS:
            v = node.get(k)
            if isinstance(v, str) and len(v.strip()) > 20:
                return v
        for v in node.values():
            found = _find_text(v, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_text(v, depth + 1)
            if found:
                return found
    return None


def _find_links(node, out, depth=0):
    if depth > 8:
        return out
    if isinstance(node, dict):
        for k in LINK_KEYS:
            v = node.get(k)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item.startswith("http"):
                        out.append({"url": item})
                    elif isinstance(item, dict):
                        url = item.get("url") or item.get("link") or item.get("href")
                        if isinstance(url, str) and url.startswith("http"):
                            out.append({"url": url, "title": item.get("title") or item.get("text")})
        for v in node.values():
            _find_links(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _find_links(v, out, depth + 1)
    return out


def _domain(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().removeprefix("www.") if m else ""


def summarize_job(job):
    output = job.get("output")
    text = _find_text(output) or ""
    seen, links = set(), []
    for link in _find_links(output, []):
        if link["url"] not in seen:
            seen.add(link["url"])
            link["domain"] = _domain(link["url"])
            links.append(link)
    pricing = job.get("pricing") or {}
    return {
        "job_id": job.get("id"),
        "status": job.get("status"),
        "error": job.get("error"),
        "timeout": job.get("timeout", False),
        "resposta": text,
        "fontes": links,
        "custo_usd": (pricing.get("finalMicrosUSD") or pricing.get("authorizedMicrosUSD") or 0) / 1e6,
    }


# --------------------------------------------------------------------------- Análise de marcas

def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


def brand_hits(text, links, brand):
    """brand: {'nome': str, 'aliases': [str], 'dominio': str}"""
    terms = [brand.get("nome", "")] + list(brand.get("aliases") or [])
    terms = [_norm(t) for t in terms if t and t.strip()]
    ntext = _norm(text)
    first = None
    for t in terms:
        i = ntext.find(t)
        if i >= 0 and (first is None or i < first):
            first = i
    domain = (brand.get("dominio") or "").lower().removeprefix("www.")
    cited = bool(domain) and any(l["domain"] == domain or l["domain"].endswith("." + domain) for l in links)
    return {"mencionada": first is not None, "posicao_char": first, "citada_como_fonte": cited}


def rank_mentions(text, links, brands):
    hits = {b["nome"]: brand_hits(text, links, b) for b in brands}
    order = sorted((h["posicao_char"], name) for name, h in hits.items() if h["mencionada"])
    for pos, (_, name) in enumerate(order, 1):
        hits[name]["ordem"] = pos
    return hits


def run_geo(prompts, sources, brands, geo_location=None, timeout_s=300, max_workers=8, output_dir=None):
    tasks = [(p, s) for p in prompts for s in sources]

    def one(task):
        prompt, source = task
        try:
            job = wait_job(submit(source, prompt, geo_location), timeout_s=timeout_s)
            res = summarize_job(job)
        except Exception as e:
            res = {"status": "erro", "error": str(e), "resposta": "", "fontes": [], "custo_usd": 0}
        res.update({"prompt": prompt, "source": source})
        res["marcas"] = rank_mentions(res["resposta"], res["fontes"], brands)
        return res

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(one, tasks))

    ok = [r for r in results if r.get("status") == "completed"]
    resumo = {}
    for b in brands:
        name = b["nome"]
        row = {"total_respostas": len(ok), "mencoes": 0, "citada_como_fonte": 0, "primeira_citada": 0, "por_ia": {}}
        for s in sources:
            rs = [r for r in ok if r["source"] == s]
            m = sum(1 for r in rs if r["marcas"][name]["mencionada"])
            row["por_ia"][s] = {"respostas": len(rs), "mencoes": m,
                                "share_pct": round(100.0 * m / len(rs), 1) if rs else None}
        row["mencoes"] = sum(1 for r in ok if r["marcas"][name]["mencionada"])
        row["citada_como_fonte"] = sum(1 for r in ok if r["marcas"][name]["citada_como_fonte"])
        row["primeira_citada"] = sum(1 for r in ok if r["marcas"][name].get("ordem") == 1)
        row["share_pct"] = round(100.0 * row["mencoes"] / len(ok), 1) if ok else None
        resumo[name] = row

    domains = {}
    for r in ok:
        for d in {l["domain"] for l in r["fontes"] if l["domain"]}:
            domains[d] = domains.get(d, 0) + 1
    top_fontes = sorted(domains.items(), key=lambda kv: -kv[1])[:25]

    report = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "geo_location": geo_location,
        "fontes_ia": list(sources),
        "marcas": brands,
        "resumo_por_marca": resumo,
        "dominios_mais_citados": [{"dominio": d, "respostas": n} for d, n in top_fontes],
        "falhas": [{"prompt": r["prompt"], "source": r["source"], "status": r.get("status"), "error": r.get("error")}
                   for r in results if r.get("status") != "completed"],
        "custo_total_usd": round(sum(r.get("custo_usd") or 0 for r in results), 4),
        "respostas": results,
    }

    out_dir = output_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "geo-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["arquivo"] = path
    return report


# --------------------------------------------------------------------------- MCP

SOURCE_SCHEMA = {"type": "string", "enum": list(SOURCES), "description": "IA a consultar."}
GEO_SCHEMA = {"type": "string", "description": "Localização do usuário simulado, ex.: 'Brazil' ou 'São Paulo, Brazil'. Opcional."}

TOOLS = [
    {
        "name": "abrir_configuracao",
        "description": "Abre no navegador a tela de configuração do plugin, onde o usuário cola a chave da AIsa e salva. Use quando o usuário pedir para configurar, cadastrar ou trocar a chave.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "configurar_chave_aisa",
        "description": "Cadastra a chave da API AIsa do usuário (começa com sk-aisa-): testa na AIsa e guarda no computador para as próximas conversas. Use quando a chave não estiver configurada ou o usuário quiser trocá-la.",
        "inputSchema": {
            "type": "object",
            "properties": {"chave": {"type": "string", "description": "Chave da AIsa colada pelo usuário."}},
            "required": ["chave"],
        },
    },
    {
        "name": "verificar_configuracao",
        "description": "Verifica se a chave da AIsa está configurada e aceita pela API (gratuito). Use quando o usuário acabou de instalar o plugin ou quando outra ferramenta falhar por autenticação.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "oxylabs_llm_perguntar",
        "description": "Faz uma pergunta ao ChatGPT, Gemini ou Perplexity como um usuário real (Oxylabs via AIsa), espera a resposta e devolve o texto e as fontes citadas. Cobrado por pergunta.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": SOURCE_SCHEMA,
                "prompt": {"type": "string", "description": "Pergunta, como um usuário escreveria."},
                "geo_location": GEO_SCHEMA,
                "timeout_s": {"type": "integer", "default": 240, "description": "Tempo máximo de espera em segundos."},
                "incluir_bruto": {"type": "boolean", "default": False, "description": "Inclui o output bruto do Oxylabs."},
            },
            "required": ["source", "prompt"],
        },
    },
    {
        "name": "oxylabs_llm_cotar",
        "description": "Cota o custo de uma pergunta ao Oxylabs LLM sem executar. Gratuito.",
        "inputSchema": {
            "type": "object",
            "properties": {"source": SOURCE_SCHEMA, "prompt": {"type": "string"}, "geo_location": GEO_SCHEMA},
            "required": ["source", "prompt"],
        },
    },
    {
        "name": "geo_visibilidade",
        "description": (
            "Relatório de GEO: envia várias perguntas a várias IAs em paralelo e mede, para cada marca, "
            "em quantas respostas ela aparece, quantas vezes aparece primeiro e se o domínio dela é citado como fonte. "
            "Também lista os domínios mais citados pelas IAs. Salva tudo num JSON e devolve o resumo. "
            "Custo aproximado: nº de perguntas × nº de IAs × preço por pergunta."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompts": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 50,
                            "description": "Perguntas do setor, como clientes perguntariam."},
                "sources": {"type": "array", "items": SOURCE_SCHEMA, "default": list(SOURCES)},
                "marcas": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}, "description": "Outras grafias do nome."},
                            "dominio": {"type": "string", "description": "Domínio do site, sem https:// nem www."},
                        },
                        "required": ["nome"],
                    },
                    "description": "Empresa analisada e concorrentes.",
                },
                "geo_location": GEO_SCHEMA,
                "output_dir": {"type": "string", "description": "Pasta onde salvar o JSON. Padrão: diretório atual."},
                "incluir_respostas": {"type": "boolean", "default": False,
                                      "description": "Inclui o texto de cada resposta no retorno (o JSON salvo sempre inclui)."},
            },
            "required": ["prompts", "marcas"],
        },
    },
    {
        "name": "oxylabs_llm_job",
        "description": "Consulta um job do Oxylabs LLM pelo id (gratuito).",
        "inputSchema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
    },
    {
        "name": "oxylabs_llm_listar",
        "description": "Lista jobs recentes do Oxylabs LLM desta chave (gratuito).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["queued", "running", "completed", "failed", "cancelled"]},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "oxylabs_llm_cancelar",
        "description": "Cancela um job do Oxylabs LLM em andamento.",
        "inputSchema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
    },
]


def check_setup():
    info = {"python": sys.version.split()[0], "api": API_BASE}
    try:
        key = _api_key()
    except RuntimeError as e:
        return info | {"ok": False, "problema": str(e), "tela_de_configuracao": open_config_page()}
    info["chave"] = _mask(key)
    try:
        list_jobs(limit=1)
    except RuntimeError as e:
        msg = str(e)
        if "HTTP 401" in msg or "HTTP 403" in msg:
            return info | {"ok": False, "problema": "A AIsa recusou a chave. Confira se copiou a chave inteira em console.aisa.one.", "detalhe": msg}
        if "HTTP 402" in msg:
            return info | {"ok": False, "problema": "Chave válida, mas sem saldo ou sem acesso ao Oxylabs. Adicione créditos em console.aisa.one.", "detalhe": msg}
        return info | {"ok": False, "problema": "Falha ao falar com a API da AIsa.", "detalhe": msg}
    except OSError as e:
        return info | {"ok": False, "problema": "Sem conexão com %s: %s" % (API_BASE, e)}
    return info | {"ok": True, "mensagem": "Tudo certo: a chave foi aceita e o Oxylabs LLM está acessível."}


def call_tool(name, args):
    if name == "abrir_configuracao":
        return open_config_page()
    if name == "configurar_chave_aisa":
        return save_key(args.get("chave"))
    if name == "verificar_configuracao":
        return check_setup()
    try:
        _api_key()
    except RuntimeError as e:
        return {"ok": False, "problema": str(e), "tela_de_configuracao": open_config_page()}
    return _call_api_tool(name, args)


def _call_api_tool(name, args):
    if name == "oxylabs_llm_perguntar":
        job = wait_job(submit(args["source"], args["prompt"], args.get("geo_location")),
                       timeout_s=int(args.get("timeout_s") or 240))
        res = summarize_job(job)
        if args.get("incluir_bruto"):
            res["output_bruto"] = job.get("output")
        return res
    if name == "oxylabs_llm_cotar":
        return quote(args["source"], args["prompt"], args.get("geo_location"))
    if name == "geo_visibilidade":
        report = run_geo(args["prompts"], args.get("sources") or list(SOURCES), args["marcas"],
                         geo_location=args.get("geo_location"), output_dir=args.get("output_dir"))
        if not args.get("incluir_respostas"):
            report["respostas"] = [
                {"prompt": r["prompt"], "source": r["source"], "status": r.get("status"),
                 "marcas_mencionadas": [n for n, h in r["marcas"].items() if h["mencionada"]]}
                for r in report["respostas"]
            ]
        return report
    if name == "oxylabs_llm_job":
        job = get_job(args["job_id"])
        res = summarize_job(job)
        res["output_bruto"] = job.get("output")
        return res
    if name == "oxylabs_llm_listar":
        return list_jobs(args.get("status"), args.get("limit") or 20)
    if name == "oxylabs_llm_cancelar":
        return cancel_job(args["job_id"])
    raise ValueError("Ferramenta desconhecida: " + name)


def handle(msg):
    method = msg.get("method")
    if method == "initialize":
        return {
            "protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": SERVER_INSTRUCTIONS,
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = msg.get("params", {})
        try:
            result = call_tool(params.get("name"), params.get("arguments") or {})
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": "Erro: %s" % e}]}
    if method == "ping":
        return {}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:
            continue  # notificação
        try:
            result = handle(msg)
            if result is None:
                reply = {"jsonrpc": "2.0", "id": msg["id"],
                         "error": {"code": -32601, "message": "Método não suportado: %s" % msg.get("method")}}
            else:
                reply = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
