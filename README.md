# GEO: o que as IAs respondem sobre uma empresa

Plugin para o **Claude Code** que mostra o que o **ChatGPT**, o **Gemini** e o **Perplexity** respondem quando um cliente pergunta pelo seu setor. Exemplos: "qual a melhor clínica odontológica de São Paulo?" ou "onde comprar café especial em Curitiba?".

Você informa a empresa e os concorrentes. O plugin faz as perguntas às três IAs como um usuário real faria, e o Claude monta um relatório com:

- em quantas respostas cada marca aparece (share de voz), por IA;
- quem é citado primeiro;
- como as IAs descrevem a empresa;
- perguntas em que os concorrentes aparecem e a empresa não;
- quais sites as IAs usam como fonte (onde vale a pena estar);
- um plano de ação.

As perguntas são feitas pelo **Oxylabs**, que captura a resposta da interface de cada IA, por meio da API da **AIsa**.

---

## Instalar em 3 passos (sem terminal)

### 1. Crie sua chave da AIsa

1. Crie uma conta em [console.aisa.one/sign-up](https://console.aisa.one/sign-up).
2. Adicione créditos. Um relatório completo custa menos de US$ 0,10 (veja [Quanto custa](#quanto-custa)).
3. Gere uma chave de API. Ela começa com `sk-aisa-`. Deixe copiada.

### 2. Peça ao Claude para instalar

Abra o **app Claude para desktop**, entre na aba **Code** e comece uma sessão. Também funciona no Claude Code pelo terminal. Cole a mensagem abaixo e envie:

```
Instale este plugin para mim: https://github.com/andrealencarz/aisa-geo-oxylabs
```

O Claude lê as instruções do repositório e faz o resto. Quando ele pedir, cole a sua chave da AIsa. Se pedir permissão para rodar comandos, aprove.

### 3. Abra uma sessão nova e teste

Quando o Claude disser que terminou, **comece uma sessão nova**: o plugin só carrega em sessões novas. Nela, escreva:

```
verifique a configuração do plugin GEO
```

A resposta esperada é **"Tudo certo: a chave foi aceita e o Oxylabs LLM está acessível."**

> O plugin funciona no Claude Code: aba **Code** do app para desktop ou terminal. No chat comum do claude.ai ele não funciona.

---

## Como usar

### Relatório completo

```
/relatorio-geo
```

O Claude pergunta o que faltar: empresa, site, concorrentes, cidade. Depois:

1. sugere de 10 a 20 perguntas que um cliente faria e mostra a lista para você aprovar;
2. calcula quanto vai custar e espera o seu ok;
3. faz as perguntas às três IAs ao mesmo tempo (leva de 1 a 3 minutos);
4. entrega o relatório em HTML e salva os dados brutos num arquivo `geo-AAAAMMDD-HHMMSS.json` na pasta da sessão.

Se preferir, passe tudo de uma vez:

```
/relatorio-geo para a Padaria Bella Massa (bellamassa.com.br) em Belo Horizonte,
concorrentes: Padaria Savassi (padariasavassi.com.br) e Pão & Cia (paoecia.com.br)
```

### Perguntas avulsas

```
pergunte ao ChatGPT e ao Gemini qual a melhor escola de inglês em Recife e me mostre as fontes que eles usaram
```

---

## Quanto custa

Cada pergunta a uma IA custa cerca de **US$ 0,0015** na AIsa. O preço pode mudar; o plugin sempre cota antes de rodar.

| Relatório | Perguntas × IAs | Custo aproximado |
|---|---|---|
| Rápido | 10 × 3 | US$ 0,05 |
| Completo | 20 × 3 | US$ 0,09 |

Consultar a configuração, cotar e acompanhar jobs é gratuito.

---

## Problemas comuns

Na maioria dos casos, basta pedir ao Claude:

```
o plugin GEO não está funcionando, siga a seção de problemas do https://github.com/andrealencarz/aisa-geo-oxylabs e conserte
```

| Aviso | O que significa | Como resolver |
|---|---|---|
| "Chave da AIsa não configurada" | A chave não chegou ao plugin | Peça ao Claude: "troque a chave do plugin GEO" e cole a chave |
| "A AIsa recusou a chave" | Chave copiada pela metade ou apagada | Gere outra em [console.aisa.one](https://console.aisa.one) e peça ao Claude para trocar |
| "Chave válida, mas sem saldo" | Faltam créditos | Adicione créditos em [console.aisa.one](https://console.aisa.one) |
| O Claude não acha as ferramentas do plugin | A sessão começou antes da instalação, ou falta Python | Abra uma sessão nova. Se continuar, peça ao Claude para conferir o Python |
| Algumas respostas vieram vazias | Uma IA demorou mais que o normal | Rode de novo só as perguntas que faltaram |

---

## Instruções de instalação para o Claude

> Esta seção é para o assistente que vai instalar o plugin a pedido do usuário. Siga os passos na ordem, explique cada um em linguagem simples e não mostre a chave do usuário de volta no chat.

**1. Confira o Python 3.9+.** Rode `python3 --version`.
- Se a versão for 3.9 ou maior, siga para o passo 2.
- Mac sem Python: rode `xcode-select --install`, peça ao usuário para clicar em **Instalar** na janela que abrir e espere terminar.
- Windows sem `python3`: peça ao usuário para instalar o **Python 3.12** pela **Microsoft Store** (essa versão cria o comando `python3`) e confirme com `python3 --version`.
- Linux: `sudo apt install -y python3` (peça a senha ao usuário só se o sistema exigir).

**2. Peça a chave da AIsa** (começa com `sk-aisa-`). Se o usuário não tiver, mande-o para https://console.aisa.one/sign-up e espere.

**3. Instale ou reinstale.** Rode `claude plugin list`.
- Se `aisa-geo-oxylabs@aisa-geo` **não** aparecer:
  ```bash
  claude plugin marketplace add andrealencarz/aisa-geo-oxylabs
  claude plugin install aisa-geo-oxylabs@aisa-geo --config aisa_api_key=CHAVE_DO_USUARIO
  ```
- Se já aparecer (atualizar ou trocar a chave), a chave só é gravada numa instalação nova:
  ```bash
  claude plugin marketplace update aisa-geo
  claude plugin uninstall aisa-geo-oxylabs@aisa-geo
  claude plugin install aisa-geo-oxylabs@aisa-geo --config aisa_api_key=CHAVE_DO_USUARIO
  ```
- A instalação deu certo se terminar com `Successfully installed` **sem** o aviso `userConfig option not yet set`. Se o aviso aparecer, desinstale e instale de novo com o `--config`.

**4. Teste o servidor** sem gastar créditos:
```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"verificar_configuracao","arguments":{}}}' | AISA_API_KEY=CHAVE_DO_USUARIO python3 "$(find ~/.claude/plugins/cache -path '*aisa-geo-oxylabs*' -name mcp_server.py | sort | tail -1)"
```
A resposta deve conter `"ok": true`. Se vier `"ok": false`, explique o campo `problema` ao usuário.

**5. Finalize.** Diga ao usuário que a instalação terminou, que ele precisa **começar uma sessão nova** para o plugin carregar, e que lá pode escrever `verifique a configuração do plugin GEO` e depois `/relatorio-geo`.

**Problemas depois de instalado:** se a sessão nova não mostrar as ferramentas `aisa-oxylabs`, refaça o passo 1 (Python) e o passo 4. Para trocar a chave, repita o passo 3 no caminho "se já aparecer".

---

<details>
<summary><b>Instalação manual (para quem usa terminal)</b></summary>

Dentro do Claude Code:

```
/plugin marketplace add andrealencarz/aisa-geo-oxylabs
```

```
/plugin install aisa-geo-oxylabs@aisa-geo
```

O Claude Code pede a chave durante a instalação. Para trocar a chave depois: `/plugin configure aisa-geo-oxylabs@aisa-geo`.

Ou direto no terminal, já com a chave:

```bash
claude plugin marketplace add andrealencarz/aisa-geo-oxylabs
```

```bash
claude plugin install aisa-geo-oxylabs@aisa-geo --config aisa_api_key=sk-aisa-SUA-CHAVE
```

Para atualizar: `claude plugin marketplace update aisa-geo` e depois `claude plugin update aisa-geo-oxylabs@aisa-geo`. Para remover: `claude plugin uninstall aisa-geo-oxylabs@aisa-geo`.

Se preferir não guardar a chave nas configurações do Claude Code, salve-a em `~/.aisa_api_key`; o plugin lê esse arquivo quando a configuração está vazia.
</details>

<details>
<summary><b>Como funciona por dentro</b></summary>

```
Você ──► Claude Code ──► skill /relatorio-geo (roteiro do relatório)
                              │
                              ▼
                  servidor MCP "aisa-oxylabs" (mcp_server.py)
                              │  envia a pergunta e espera a resposta
                              ▼
          API AIsa ──► Oxylabs ──► ChatGPT · Gemini · Perplexity
```

| Ferramenta | O que faz | Custo |
|---|---|---|
| `verificar_configuracao` | Confere a chave e o acesso à AIsa | grátis |
| `geo_visibilidade` | Faz um lote de perguntas a várias IAs em paralelo, mede a presença de cada marca e salva o JSON | por pergunta |
| `oxylabs_llm_perguntar` | Faz uma pergunta a uma IA e devolve a resposta e as fontes | por pergunta |
| `oxylabs_llm_cotar` | Cota uma pergunta sem executar | grátis |
| `oxylabs_llm_job` · `oxylabs_llm_listar` · `oxylabs_llm_cancelar` | Acompanham os jobs | grátis |

Arquivos do repositório:

```
.claude-plugin/plugin.json        manifesto do plugin (servidor MCP e campo da chave)
.claude-plugin/marketplace.json   permite instalar direto do GitHub
mcp_server.py                     servidor MCP em Python, sem dependências
skills/relatorio-geo/SKILL.md     roteiro que o Claude segue para montar o relatório
```
</details>

---

## Cuidados

- **Respostas de IA mudam a cada vez.** Para acompanhar a evolução, repita as mesmas perguntas todo mês e guarde os arquivos JSON.
- **Visibilidade não é qualidade.** O relatório mostra quem aparece, não quem presta o melhor serviço.
- **Áreas reguladas** (saúde, advocacia, contabilidade): confira as regras de publicidade do conselho profissional antes de publicar conteúdo do tipo "o melhor de…".
- **Os arquivos `geo-*.json` podem ter dados de clientes.** Não publique esses arquivos.

## Licença

MIT. Feito por [André Alencar](http://www.youtube.com/@empreendedorserial).
