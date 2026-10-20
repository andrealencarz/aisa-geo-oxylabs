#!/usr/bin/env python3
"""
Instalador do plugin aisa-geo-oxylabs no Claude Code, em um comando só.
Atualiza o marketplace, instala ou atualiza o plugin e, se a chave da AIsa
for informada, testa a chave (sem custo) e salva em ~/.aisa_api_key.

Uso:  python3 instalar.py [--chave sk-aisa-...]
"""

import argparse
import glob
import json
import os
import subprocess
import sys

MARKETPLACE = "aisa-geo"
REPO_URL = "https://github.com/andrealencarz/aisa-geo-oxylabs"
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


def save_key(key):
    """Usa a ferramenta configurar_chave_aisa do próprio plugin: testa a chave e salva."""
    servers = sorted(glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache",
                                            MARKETPLACE, "aisa-geo-oxylabs", "*", "mcp_server.py")))
    if not servers:
        fail("O plugin foi instalado, mas não encontrei o servidor dele. Rode este mesmo comando de novo.")
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "configurar_chave_aisa", "arguments": {"chave": key}}})
    proc = subprocess.run([sys.executable, servers[-1]], input=request + "\n", capture_output=True, text=True)
    try:
        return json.loads(json.loads(proc.stdout)["result"]["content"][0]["text"])
    except (ValueError, KeyError, IndexError):
        fail("O teste da chave falhou.", (proc.stdout + proc.stderr)[:1500])


def main():
    parser = argparse.ArgumentParser(description="Instala o plugin GEO (Oxylabs via AIsa) no Claude Code.")
    parser.add_argument("--chave", help="Chave da API AIsa (sk-aisa-...). Opcional: sem ela, a tela de "
                                        "configuração abre no primeiro uso.")
    key = (parser.parse_args().chave or "").strip()

    if sys.version_info < (3, 9):
        fail("Python %s é antigo demais. Instale o Python 3.9 ou mais novo." % sys.version.split()[0])
    if key and not key.startswith("sk-"):
        fail("A chave não parece uma chave da AIsa (ela começa com sk-aisa-). Copie de novo em console.aisa.one.")

    step("Atualizando o marketplace %s" % MARKETPLACE)
    code, out = run(["claude", "plugin", "marketplace", "update", MARKETPLACE])
    if code != 0:
        code, out = run(["claude", "plugin", "marketplace", "add", REPO_URL])
        if code != 0:
            fail("Não consegui adicionar o marketplace.", out)

    code, out = run(["claude", "plugin", "list", "--json"])
    if code == 0 and PLUGIN in out:
        step("Atualizando o plugin")
        code, out = run(["claude", "plugin", "update", PLUGIN])
    else:
        step("Instalando o plugin")
        code, out = run(["claude", "plugin", "install", PLUGIN])
    if code != 0:
        fail("A instalação não terminou.", out)

    if key:
        step("Testando e salvando a sua chave (sem custo)")
        result = save_key(key)
        if not result.get("ok"):
            fail("Plugin instalado, mas a chave não passou no teste: " + result.get("problema", ""))
        print("\n✔ Plugin instalado e chave aceita pela AIsa.")
    else:
        print("\n✔ Plugin instalado. Na primeira vez que você usar, a tela de configuração da chave abre no navegador.")
    print("  Abra uma sessão nova do Claude Code e escreva: verifique a configuração do plugin GEO")


if __name__ == "__main__":
    main()
