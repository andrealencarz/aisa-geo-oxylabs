#!/usr/bin/env node
/**
 * Extensão do Claude Desktop: GEO com Oxylabs via API AIsa.
 * Pergunta ao ChatGPT, Gemini e Perplexity como um usuário real e mede quais
 * marcas aparecem nas respostas. Servidor MCP via stdio (JSON-RPC 2.0), sem
 * dependências: roda com o Node embutido no Claude Desktop.
 */

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const http = require("http");
const readline = require("readline");
const { spawn } = require("child_process");

const SERVER_NAME = "aisa-oxylabs";
const SERVER_VERSION = "0.5.0";
const PROTOCOL_VERSION = "2025-06-18";

const API_BASE = (process.env.AISA_API_BASE || "https://api.aisa.one").replace(/\/+$/, "");
const LLM_PATH = "/apis/v1/oxylabs/llm";
const SOURCES = ["chatgpt", "gemini", "perplexity"];
const FINAL_STATUSES = ["completed", "failed", "cancelled"];
const KEY_FILE = path.join(os.homedir(), ".aisa_api_key");
const MISSING_KEY = "Chave da AIsa não configurada.";
const CONFIG_HTML = path.join(__dirname, "config.html");
const CONFIG_TTL_MS = 15 * 60 * 1000;
let keyOverride = null;

const SERVER_INSTRUCTIONS =
  "Use estas ferramentas quando o usuário quiser saber o que ChatGPT, Gemini ou Perplexity respondem " +
  "para uma pergunta, ou medir a presença de uma marca/empresa nas respostas de IA (GEO). " +
  "Na primeira vez da conversa, chame 'verificar_configuracao'. Se a chave da AIsa não estiver configurada, " +
  "a tela de configuração abre sozinha no navegador: avise o usuário, passe o link 'url' e espere ele salvar. " +
  "Para configurar ou trocar a chave a pedido do usuário, chame 'abrir_configuracao'. Se o usuário colar a " +
  "chave no chat, use 'configurar_chave_aisa'. Para relatórios com várias perguntas e " +
  "concorrentes, siga o prompt 'relatorio-geo' e use 'geo_visibilidade'. Antes de lotes grandes, use " +
  "'oxylabs_llm_cotar' e informe o custo ao usuário. Cada pergunta é cobrada na conta AIsa do usuário.";

// --------------------------------------------------------------------------- API AIsa

function apiKey() {
  if (keyOverride) return keyOverride;
  let key = (process.env.AISA_API_KEY || "").trim();
  if ((!key || key.startsWith("${")) && fs.existsSync(KEY_FILE)) {
    key = fs.readFileSync(KEY_FILE, "utf8").trim();
  }
  if (!key || key.startsWith("${")) throw new Error(MISSING_KEY);
  return key;
}

const maskKey = (key) => (key.length > 16 ? key.slice(0, 8) + "…" + key.slice(-4) : "(curta demais)");

// --------------------------------------------------------------------------- Tela de configuração

const configPage = { server: null, url: null };

function openBrowser(url) {
  const [cmd, args] =
    process.platform === "darwin" ? ["open", [url]]
    : process.platform === "win32" ? ["cmd", ["/c", "start", "", url]]
    : ["xdg-open", [url]];
  try {
    spawn(cmd, args, { stdio: "ignore", detached: true }).on("error", () => {}).unref();
    return true;
  } catch {
    return false;
  }
}

function sendJson(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
  res.end(body);
}

// Abre no navegador uma página local (127.0.0.1, link com token) para colar a chave da AIsa.
async function openConfigPage() {
  if (!configPage.server) {
    const token = crypto.randomBytes(16).toString("base64url");
    const base = "/" + token;
    const server = http.createServer((req, res) => {
      if (req.method === "GET" && (req.url === base || req.url === base + "/")) {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
        return res.end(fs.readFileSync(CONFIG_HTML, "utf8"));
      }
      if (req.method === "GET" && req.url === base + "/status") {
        try {
          return sendJson(res, 200, { configurada: true, chave: maskKey(apiKey()) });
        } catch {
          return sendJson(res, 200, { configurada: false });
        }
      }
      if (req.method === "POST" && req.url === base + "/salvar") {
        let raw = "";
        req.on("data", (c) => (raw += c));
        req.on("end", async () => {
          let result;
          try {
            result = await saveKey(JSON.parse(raw || "{}").chave);
          } catch (e) {
            result = { ok: false, problema: e.message };
          }
          delete result.detalhe;
          sendJson(res, 200, result);
        });
        return;
      }
      sendJson(res, 404, {});
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    server.unref();
    setTimeout(() => {
      server.close();
      configPage.server = configPage.url = null;
    }, CONFIG_TTL_MS).unref();
    configPage.server = server;
    configPage.url = `http://127.0.0.1:${server.address().port}${base}`;
  }
  return {
    ok: true,
    url: configPage.url,
    aberta_no_navegador: openBrowser(configPage.url),
    mensagem:
      "Abri a tela de configuração no navegador. Cole a chave da AIsa, clique em 'Salvar e testar' e volte aqui. " +
      "Se a página não abriu, use o link. Ele vale por 15 minutos.",
  };
}

// Testa a chave na AIsa e, se for aceita, guarda em ~/.aisa_api_key (só o usuário lê).
async function saveKey(key) {
  key = String(key || "").trim();
  if (!key.startsWith("sk-")) {
    return { ok: false, problema: "Isso não parece uma chave da AIsa: ela começa com sk-aisa-. Copie de novo em console.aisa.one." };
  }
  const previous = keyOverride;
  keyOverride = key;
  const result = await checkSetup();
  if (!result.ok && String(result.problema).includes("recusou")) {
    keyOverride = previous;
    return result;
  }
  fs.writeFileSync(KEY_FILE, key + "\n", { encoding: "utf8", mode: 0o600 });
  result.salva_em = KEY_FILE;
  result.chave = maskKey(key);
  if (result.ok) result.mensagem = "Chave salva e aceita pela AIsa. Não precisa configurar de novo.";
  return result;
}

async function request(method, urlPath, body, headers = {}) {
  const res = await fetch(API_BASE + urlPath, {
    method,
    headers: {
      Authorization: "Bearer " + apiKey(),
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(60000),
  });
  const raw = await res.text();
  let data;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { raw: raw.slice(0, 2000) };
  }
  if (!res.ok) {
    const err = new Error(`AIsa HTTP ${res.status} em ${method} ${urlPath}: ${JSON.stringify(data).slice(0, 2000)}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

function llmBody(source, prompt, geoLocation, parse = true) {
  source = String(source || "").trim().toLowerCase();
  if (!SOURCES.includes(source)) throw new Error("source deve ser um de: " + SOURCES.join(", "));
  if (!String(prompt || "").trim()) throw new Error("prompt vazio");
  const body = { source, prompt: String(prompt).trim(), parse: Boolean(parse) };
  if (geoLocation) body.geo_location = geoLocation;
  return body;
}

const quote = (source, prompt, geo) =>
  request("POST", LLM_PATH, llmBody(source, prompt, geo), {
    "Idempotency-Key": crypto.randomUUID(),
    "X-AISA-Cost-Mode": "quote",
  });

const submit = (source, prompt, geo) =>
  request("POST", LLM_PATH, llmBody(source, prompt, geo), { "Idempotency-Key": crypto.randomUUID() });

const getJob = (id) => request("GET", `${LLM_PATH}/${encodeURIComponent(id)}`);
const cancelJob = (id) => request("POST", `${LLM_PATH}/${encodeURIComponent(id)}/cancel`);

function listJobs(status, limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  return request("GET", `${LLM_PATH}?${params}`);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitJob(job, timeoutS = 240, intervalS = 4) {
  const deadline = Date.now() + timeoutS * 1000;
  while (!FINAL_STATUSES.includes(job.status)) {
    if (Date.now() > deadline) return { ...job, timeout: true };
    await sleep(intervalS * 1000);
    job = await getJob(job.id);
  }
  return job;
}

// --------------------------------------------------------------------------- Extração da resposta

const TEXT_KEYS = ["response_text", "markdown_text", "answer_text", "text", "answer", "content", "markdown"];
const LINK_KEYS = ["citations", "sources", "links", "references", "search_results"];

function findText(node, depth = 0) {
  if (depth > 8 || node === null || typeof node !== "object") return null;
  if (!Array.isArray(node)) {
    for (const k of TEXT_KEYS) {
      if (typeof node[k] === "string" && node[k].trim().length > 20) return node[k];
    }
  }
  for (const v of Object.values(node)) {
    const found = findText(v, depth + 1);
    if (found) return found;
  }
  return null;
}

function findLinks(node, out = [], depth = 0) {
  if (depth > 8 || node === null || typeof node !== "object") return out;
  if (!Array.isArray(node)) {
    for (const k of LINK_KEYS) {
      if (!Array.isArray(node[k])) continue;
      for (const item of node[k]) {
        if (typeof item === "string" && item.startsWith("http")) out.push({ url: item });
        else if (item && typeof item === "object") {
          const url = item.url || item.link || item.href;
          if (typeof url === "string" && url.startsWith("http")) out.push({ url, title: item.title || item.text || null });
        }
      }
    }
  }
  for (const v of Object.values(node)) findLinks(v, out, depth + 1);
  return out;
}

function domainOf(url) {
  const m = /^https?:\/\/([^/]+)/i.exec(url || "");
  return m ? m[1].toLowerCase().replace(/^www\./, "") : "";
}

function summarizeJob(job) {
  const seen = new Set();
  const fontes = [];
  for (const link of findLinks(job.output)) {
    if (seen.has(link.url)) continue;
    seen.add(link.url);
    fontes.push({ ...link, domain: domainOf(link.url) });
  }
  const pricing = job.pricing || {};
  return {
    job_id: job.id,
    status: job.status,
    error: job.error || null,
    timeout: Boolean(job.timeout),
    resposta: findText(job.output) || "",
    fontes,
    custo_usd: (pricing.finalMicrosUSD || pricing.authorizedMicrosUSD || 0) / 1e6,
  };
}

// --------------------------------------------------------------------------- Análise de marcas

const norm = (s) =>
  String(s || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();

function brandHits(text, links, brand) {
  const terms = [brand.nome, ...(brand.aliases || [])].filter((t) => t && t.trim()).map(norm);
  const ntext = norm(text);
  let first = null;
  for (const t of terms) {
    const i = ntext.indexOf(t);
    if (i >= 0 && (first === null || i < first)) first = i;
  }
  const domain = String(brand.dominio || "").toLowerCase().replace(/^www\./, "");
  const cited = Boolean(domain) && links.some((l) => l.domain === domain || l.domain.endsWith("." + domain));
  return { mencionada: first !== null, posicao_char: first, citada_como_fonte: cited };
}

function rankMentions(text, links, brands) {
  const hits = {};
  for (const b of brands) hits[b.nome] = brandHits(text, links, b);
  Object.entries(hits)
    .filter(([, h]) => h.mencionada)
    .sort((a, b) => a[1].posicao_char - b[1].posicao_char)
    .forEach(([name], i) => (hits[name].ordem = i + 1));
  return hits;
}

async function pool(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i]);
    }
  });
  await Promise.all(workers);
  return results;
}

function defaultOutputDir() {
  return process.env.GEO_OUTPUT_DIR && !process.env.GEO_OUTPUT_DIR.startsWith("${")
    ? process.env.GEO_OUTPUT_DIR
    : path.join(os.homedir(), "Documents", "Relatorios GEO");
}

async function runGeo(prompts, sources, brands, geoLocation, outputDir, timeoutS = 300) {
  const tasks = prompts.flatMap((prompt) => sources.map((source) => ({ prompt, source })));

  const results = await pool(tasks, 8, async ({ prompt, source }) => {
    let res;
    try {
      res = summarizeJob(await waitJob(await submit(source, prompt, geoLocation), timeoutS));
    } catch (e) {
      res = { status: "erro", error: e.message, resposta: "", fontes: [], custo_usd: 0 };
    }
    return { ...res, prompt, source, marcas: rankMentions(res.resposta, res.fontes, brands) };
  });

  const ok = results.filter((r) => r.status === "completed");
  const pct = (n, d) => (d ? Math.round((1000 * n) / d) / 10 : null);
  const resumo = {};
  for (const b of brands) {
    const name = b.nome;
    const porIa = {};
    for (const s of sources) {
      const rs = ok.filter((r) => r.source === s);
      const m = rs.filter((r) => r.marcas[name].mencionada).length;
      porIa[s] = { respostas: rs.length, mencoes: m, share_pct: pct(m, rs.length) };
    }
    const mencoes = ok.filter((r) => r.marcas[name].mencionada).length;
    resumo[name] = {
      total_respostas: ok.length,
      mencoes,
      share_pct: pct(mencoes, ok.length),
      primeira_citada: ok.filter((r) => r.marcas[name].ordem === 1).length,
      citada_como_fonte: ok.filter((r) => r.marcas[name].citada_como_fonte).length,
      por_ia: porIa,
    };
  }

  const domains = {};
  for (const r of ok) for (const d of new Set(r.fontes.map((l) => l.domain).filter(Boolean))) domains[d] = (domains[d] || 0) + 1;

  const now = new Date();
  const report = {
    gerado_em: now.toISOString(),
    geo_location: geoLocation || null,
    fontes_ia: sources,
    marcas: brands,
    resumo_por_marca: resumo,
    dominios_mais_citados: Object.entries(domains)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 25)
      .map(([dominio, respostas]) => ({ dominio, respostas })),
    falhas: results
      .filter((r) => r.status !== "completed")
      .map((r) => ({ prompt: r.prompt, source: r.source, status: r.status, error: r.error })),
    custo_total_usd: Math.round(results.reduce((s, r) => s + (r.custo_usd || 0), 0) * 10000) / 10000,
    respostas: results,
  };

  const dir = outputDir || defaultOutputDir();
  fs.mkdirSync(dir, { recursive: true });
  const stamp = now.toISOString().replace(/[-:]/g, "").replace("T", "-").slice(0, 15);
  const file = path.join(dir, `geo-${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 2), "utf8");
  report.arquivo = file;
  return report;
}

async function checkSetup() {
  const info = { node: process.version, api: API_BASE };
  let key;
  try {
    key = apiKey();
  } catch (e) {
    return { ...info, ok: false, problema: e.message, tela_de_configuracao: await openConfigPage() };
  }
  info.chave = maskKey(key);
  try {
    await listJobs(undefined, 1);
  } catch (e) {
    if (e.status === 401 || e.status === 403)
      return { ...info, ok: false, problema: "A AIsa recusou a chave. Confira se copiou a chave inteira em console.aisa.one.", detalhe: e.message };
    if (e.status === 402)
      return { ...info, ok: false, problema: "Chave válida, mas sem saldo ou sem acesso ao Oxylabs. Adicione créditos em console.aisa.one.", detalhe: e.message };
    return { ...info, ok: false, problema: "Falha ao falar com a API da AIsa.", detalhe: e.message };
  }
  return { ...info, ok: true, mensagem: "Tudo certo: a chave foi aceita e o Oxylabs LLM está acessível." };
}

// --------------------------------------------------------------------------- MCP: ferramentas

const SOURCE_SCHEMA = { type: "string", enum: SOURCES, description: "IA a consultar." };
const GEO_SCHEMA = { type: "string", description: "Localização do usuário simulado, ex.: 'Brazil'. Opcional." };

const TOOLS = [
  {
    name: "abrir_configuracao",
    description: "Abre no navegador a tela de configuração da extensão, onde o usuário cola a chave da AIsa e salva. Use quando o usuário pedir para configurar, cadastrar ou trocar a chave.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "configurar_chave_aisa",
    description: "Cadastra a chave da API AIsa do usuário (começa com sk-aisa-): testa na AIsa e guarda no computador para as próximas conversas. Use quando a chave não estiver configurada ou o usuário quiser trocá-la.",
    inputSchema: {
      type: "object",
      properties: { chave: { type: "string", description: "Chave da AIsa colada pelo usuário." } },
      required: ["chave"],
    },
  },
  {
    name: "verificar_configuracao",
    description: "Verifica se a chave da AIsa está configurada e aceita pela API (gratuito). Use na primeira vez da conversa ou quando outra ferramenta falhar por autenticação.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "oxylabs_llm_perguntar",
    description: "Faz uma pergunta ao ChatGPT, Gemini ou Perplexity como um usuário real (Oxylabs via AIsa), espera a resposta e devolve o texto e as fontes citadas. Cobrado por pergunta.",
    inputSchema: {
      type: "object",
      properties: {
        source: SOURCE_SCHEMA,
        prompt: { type: "string", description: "Pergunta, como um usuário escreveria." },
        geo_location: GEO_SCHEMA,
        timeout_s: { type: "integer", default: 240, description: "Tempo máximo de espera em segundos." },
        incluir_bruto: { type: "boolean", default: false, description: "Inclui o output bruto do Oxylabs." },
      },
      required: ["source", "prompt"],
    },
  },
  {
    name: "oxylabs_llm_cotar",
    description: "Cota o custo de uma pergunta ao Oxylabs LLM sem executar. Gratuito.",
    inputSchema: {
      type: "object",
      properties: { source: SOURCE_SCHEMA, prompt: { type: "string" }, geo_location: GEO_SCHEMA },
      required: ["source", "prompt"],
    },
  },
  {
    name: "geo_visibilidade",
    description:
      "Relatório de GEO: envia várias perguntas a várias IAs em paralelo e mede, para cada marca, em quantas respostas ela aparece, " +
      "quantas vezes aparece primeiro e se o domínio dela é citado como fonte. Lista os domínios mais citados pelas IAs. " +
      "Salva tudo num JSON na pasta de resultados e devolve o resumo. Custo: nº de perguntas × nº de IAs × preço por pergunta.",
    inputSchema: {
      type: "object",
      properties: {
        prompts: { type: "array", items: { type: "string" }, minItems: 1, maxItems: 50, description: "Perguntas do setor, como clientes perguntariam." },
        sources: { type: "array", items: SOURCE_SCHEMA, default: SOURCES },
        marcas: {
          type: "array",
          minItems: 1,
          items: {
            type: "object",
            properties: {
              nome: { type: "string" },
              aliases: { type: "array", items: { type: "string" }, description: "Outras grafias do nome." },
              dominio: { type: "string", description: "Domínio do site, sem https:// nem www." },
            },
            required: ["nome"],
          },
          description: "Empresa analisada e concorrentes.",
        },
        geo_location: GEO_SCHEMA,
        incluir_respostas: { type: "boolean", default: true, description: "Inclui o texto de cada resposta no retorno (o JSON salvo sempre inclui)." },
      },
      required: ["prompts", "marcas"],
    },
  },
  {
    name: "oxylabs_llm_job",
    description: "Consulta um job do Oxylabs LLM pelo id (gratuito).",
    inputSchema: { type: "object", properties: { job_id: { type: "string" } }, required: ["job_id"] },
  },
  {
    name: "oxylabs_llm_listar",
    description: "Lista jobs recentes do Oxylabs LLM desta chave (gratuito).",
    inputSchema: {
      type: "object",
      properties: {
        status: { type: "string", enum: ["queued", "running", "completed", "failed", "cancelled"] },
        limit: { type: "integer", default: 20 },
      },
    },
  },
  {
    name: "oxylabs_llm_cancelar",
    description: "Cancela um job do Oxylabs LLM em andamento.",
    inputSchema: { type: "object", properties: { job_id: { type: "string" } }, required: ["job_id"] },
  },
];

async function callTool(name, args) {
  switch (name) {
    case "abrir_configuracao":
      return openConfigPage();
    case "configurar_chave_aisa":
      return saveKey(args.chave);
    case "verificar_configuracao":
      return checkSetup();
  }
  try {
    apiKey();
  } catch (e) {
    return { ok: false, problema: e.message, tela_de_configuracao: await openConfigPage() };
  }
  return callApiTool(name, args);
}

async function callApiTool(name, args) {
  switch (name) {
    case "oxylabs_llm_perguntar": {
      const job = await waitJob(await submit(args.source, args.prompt, args.geo_location), args.timeout_s || 240);
      const res = summarizeJob(job);
      if (args.incluir_bruto) res.output_bruto = job.output;
      return res;
    }
    case "oxylabs_llm_cotar":
      return quote(args.source, args.prompt, args.geo_location);
    case "geo_visibilidade": {
      const report = await runGeo(args.prompts, args.sources && args.sources.length ? args.sources : SOURCES, args.marcas, args.geo_location);
      if (args.incluir_respostas === false) {
        report.respostas = report.respostas.map((r) => ({
          prompt: r.prompt,
          source: r.source,
          status: r.status,
          marcas_mencionadas: Object.entries(r.marcas).filter(([, h]) => h.mencionada).map(([n]) => n),
        }));
      }
      return report;
    }
    case "oxylabs_llm_job": {
      const job = await getJob(args.job_id);
      return { ...summarizeJob(job), output_bruto: job.output };
    }
    case "oxylabs_llm_listar":
      return listJobs(args.status, args.limit || 20);
    case "oxylabs_llm_cancelar":
      return cancelJob(args.job_id);
    default:
      throw new Error("Ferramenta desconhecida: " + name);
  }
}

// --------------------------------------------------------------------------- MCP: prompt do relatório

const REPORT_PROMPT = fs.readFileSync(path.join(__dirname, "relatorio-geo.md"), "utf8");

const PROMPTS = [
  {
    name: "relatorio-geo",
    title: "Relatório GEO",
    description: "Relatório do que ChatGPT, Gemini e Perplexity respondem sobre uma empresa e seus concorrentes.",
    arguments: [
      { name: "empresa", description: "Empresa analisada e site (ex.: Padaria Bella Massa, bellamassa.com.br)", required: false },
      { name: "concorrentes", description: "Concorrentes e sites, separados por vírgula (opcional)", required: false },
      { name: "cidade", description: "Cidade ou região, se o negócio for local (opcional)", required: false },
    ],
  },
];

function getPrompt(name, args = {}) {
  if (name !== "relatorio-geo") throw new Error("Prompt desconhecido: " + name);
  const context = [
    args.empresa && `Empresa analisada: ${args.empresa}`,
    args.concorrentes && `Concorrentes: ${args.concorrentes}`,
    args.cidade && `Cidade/região: ${args.cidade}`,
  ].filter(Boolean);
  const text = REPORT_PROMPT + (context.length ? "\n\n## Dados informados pelo usuário\n\n" + context.join("\n") : "");
  return {
    description: PROMPTS[0].description,
    messages: [{ role: "user", content: { type: "text", text } }],
  };
}

// --------------------------------------------------------------------------- JSON-RPC

async function handle(msg) {
  const params = msg.params || {};
  switch (msg.method) {
    case "initialize":
      return {
        protocolVersion: params.protocolVersion || PROTOCOL_VERSION,
        capabilities: { tools: {}, prompts: {} },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
        instructions: SERVER_INSTRUCTIONS,
      };
    case "tools/list":
      return { tools: TOOLS };
    case "tools/call":
      try {
        const result = await callTool(params.name, params.arguments || {});
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      } catch (e) {
        return { isError: true, content: [{ type: "text", text: "Erro: " + e.message }] };
      }
    case "prompts/list":
      return { prompts: PROMPTS };
    case "prompts/get":
      return getPrompt(params.name, params.arguments || {});
    case "ping":
      return {};
    default:
      return undefined;
  }
}

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", async (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    return;
  }
  if (msg.id === undefined) return; // notificação
  try {
    const result = await handle(msg);
    if (result === undefined) send({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "Método não suportado: " + msg.method } });
    else send({ jsonrpc: "2.0", id: msg.id, result });
  } catch (e) {
    process.stderr.write(String(e.stack || e) + "\n");
    send({ jsonrpc: "2.0", id: msg.id, error: { code: -32603, message: e.message } });
  }
});
