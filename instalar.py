#!/usr/bin/env python3
"""
Instalador do plugin aisa-geo-oxylabs em um comando só.
Atualiza o marketplace, (re)instala o plugin gravando a chave da AIsa e
testa a chave sem gastar créditos.

Uso:  python3 instalar.py --chave sk-aisa-...
"""

import argparse
import glob
import json
import os
import subprocess
import sys

MARKETPLACE = "aisa-geo"
REPO = "andrealencarz/aisa-geo-oxylabs"
PLUGIN = "aisa-geo-oxylabs@" + MARKETPLACE


def run(args):
    proc = subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def step(msg):
    print("• " + msg, flush=True)


def fail(msg, detail=""):
    print("\n✖ " + msg)
    if detail:
        print(detail)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Instala o plugin GEO (Oxylabs via AIsa) no Claude Code.")
    parser.add_argument("--chave", required=True, help="Chave da API AIsa (sk-aisa-...)")
    key = parser.parse_args().chave.strip()

    if sys.version_info < (3, 9):
        fail("Python %s é antigo demais. Instale o Python 3.9 ou mais novo." % sys.version.split()[0])
    if not key.startswith("sk-"):
        fail("A chave não parece uma chave da AIsa (ela começa com sk-aisa-). Copie de novo em console.aisa.one.")

    step("Atualizando o marketplace %s" % MARKETPLACE)
    code, out = run(["claude", "plugin", "marketplace", "add", REPO])
    if code != 0:
        fail("Não consegui adicionar o marketplace.", out)
    run(["claude", "plugin", "marketplace", "update", MARKETPLACE])

    code, out = run(["claude", "plugin", "list", "--json"])
    if code == 0 and PLUGIN in out:
        step("Removendo a instalação anterior (a chave só é gravada numa instalação nova)")
        run(["claude", "plugin", "uninstall", PLUGIN])

    step("Instalando o plugin com a sua chave")
    code, out = run(["claude", "plugin", "install", PLUGIN, "--config", "aisa_api_key=" + key])
    if code != 0 or "not yet set" in out:
        fail("A instalação não terminou.", out.replace(key, "sk-aisa-***"))

    step("Testando a chave na AIsa (sem custo)")
    servers = sorted(glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache",
                                            MARKETPLACE, "aisa-geo-oxylabs", "*", "mcp_server.py")))
    if not servers:
        fail("O plugin foi instalado, mas não encontrei o servidor dele. Reinstale com este mesmo comando.")
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "verificar_configuracao", "arguments": {}}})
    proc = subprocess.run([sys.executable, servers[-1]], input=request + "\n", capture_output=True, text=True,
                          env=dict(os.environ, AISA_API_KEY=key))
    try:
        result = json.loads(json.loads(proc.stdout)["result"]["content"][0]["text"])
    except (ValueError, KeyError, IndexError):
        fail("O teste do servidor falhou.", (proc.stdout + proc.stderr)[:1500])

    if not result.get("ok"):
        fail("Plugin instalado, mas a chave não passou no teste: " + result.get("problema", ""))

    print("\n✔ Plugin instalado e chave aceita pela AIsa.")
    print("  Abra uma sessão nova do Claude Code e escreva: verifique a configuração do plugin GEO")


if __name__ == "__main__":
    main()
