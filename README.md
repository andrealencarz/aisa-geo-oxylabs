# GEO: o que as IAs respondem sobre uma empresa

Plugin para o **Claude Code** que mostra o que o **ChatGPT**, o **Gemini** e o **Perplexity** respondem quando um cliente pergunta pelo seu setor. Exemplos: "qual a melhor clínica odontológica de São Paulo?" ou "onde comprar café especial em Curitiba?".

Você informa a empresa e os concorrentes. O plugin faz as perguntas às três IAs como um usuário real faria, e o Claude monta um relatório com:

- em quantas respostas cada marca aparece (share de voz), por IA;
- quem é citado primeiro;
- como as IAs descrevem a empresa;
- perguntas em que os concorrentes aparecem e a empresa não;
- quais sites as IAs usam como fonte (onde vale a pena estar);
- um plano de ação.

As perguntas são feitas pelo **Oxylabs**, que captura a resposta da interface de cada IA, por meio da API da **AIsa**. Você só precisa de uma chave da AIsa.

---

## Do que você precisa

| Item | Para quê | Como conseguir |
|---|---|---|
| **Claude Code** | Onde o plugin roda | Terminal (`claude`) ou a aba **Code** do app Claude para desktop. Veja [claude.com/claude-code](https://claude.com/claude-code). |
| **Chave da AIsa** com saldo | Paga as perguntas às IAs | Passo 1 abaixo |
| **Python 3.9 ou mais novo** | Roda o plugin | Passo 2 abaixo |

> O plugin funciona no Claude Code. No chat comum do claude.ai ele não funciona.

---

## Passo 1: criar a chave da AIsa

1. Crie uma conta em [console.aisa.one/sign-up](https://console.aisa.one/sign-up).
2. Adicione créditos. Um relatório completo costuma custar menos de US$ 0,50 (veja [Quanto custa](#quanto-custa)).
3. Gere uma chave de API. Ela começa com `sk-aisa-`. Copie e guarde: você vai colar no passo 3.

## Passo 2: conferir o Python

Abra o Terminal (no Windows, o **PowerShell**) e rode:

```bash
python3 --version
```

Se aparecer `Python 3.9` ou um número maior, está pronto. Se der erro:

- **Mac:** rode `xcode-select --install` e aceite a instalação. Depois teste de novo.
- **Windows:** instale o **Python 3** pela **Microsoft Store**. Essa versão cria o comando `python3`; o instalador do site python.org não cria.
- **Linux:** `sudo apt install python3` (Ubuntu/Debian).

## Passo 3: instalar o plugin

Abra o Claude Code no terminal e digite os dois comandos, um de cada vez:

```
/plugin marketplace add andrealencarz/aisa-geo-oxylabs
```

```
/plugin install aisa-geo-oxylabs@aisa-geo
```

O Claude Code vai pedir a **Chave da API AIsa**. Cole a chave do passo 1 e confirme. Depois **feche e abra o Claude Code de novo** para o plugin carregar.

<details>
<summary><b>Prefere instalar sem abrir o Claude Code?</b> (comandos de terminal)</summary>

```bash
claude plugin marketplace add andrealencarz/aisa-geo-oxylabs
```

```bash
claude plugin install aisa-geo-oxylabs@aisa-geo
```

Instalando assim, o Claude Code pode não pedir a chave. Nesse caso, siga a opção B de "A chave não foi pedida" em [Problemas comuns](#problemas-comuns).
</details>

<details>
<summary><b>Usa o app Claude para desktop (aba Code)?</b></summary>

Rode os comandos de terminal acima uma vez, no Terminal do seu computador. Depois abra uma sessão nova na aba **Code**: o plugin já estará lá.
</details>

## Passo 4: testar

Numa conversa nova do Claude Code, escreva:

```
verifique a configuração do plugin GEO
```

A resposta esperada é **"Tudo certo: a chave foi aceita e o Oxylabs LLM está acessível."** Se aparecer outro aviso, veja [Problemas comuns](#problemas-comuns).

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
4. entrega o relatório em HTML e salva os dados brutos num arquivo `geo-AAAAMMDD-HHMMSS.json` na pasta onde você abriu o Claude Code.

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

**"Chave da AIsa não configurada"**
A chave não chegou ao plugin. Use uma das opções abaixo.

**A chave não foi pedida na instalação**
- **Opção A:** no Claude Code, digite `/plugin`, abra **aisa-geo-oxylabs** e escolha a opção de configurar. Cole a chave e reinicie o Claude Code.
- **Opção B:** salve a chave num arquivo que o plugin lê sozinho. No Mac ou Linux, rode no terminal (troque pela sua chave):
  ```bash
  echo "sk-aisa-SUA-CHAVE" > ~/.aisa_api_key
  ```
  No Windows (PowerShell):
  ```powershell
  "sk-aisa-SUA-CHAVE" | Out-File -Encoding ascii $HOME\.aisa_api_key
  ```
  Depois reinicie o Claude Code.

**"A AIsa recusou a chave"**
A chave foi copiada pela metade ou foi apagada no painel. Gere outra em [console.aisa.one](https://console.aisa.one) e configure de novo.

**"Chave válida, mas sem saldo"**
Adicione créditos em [console.aisa.one](https://console.aisa.one).

**O Claude não encontra as ferramentas do plugin**
- Reinicie o Claude Code depois de instalar.
- Rode `/mcp` e veja se o servidor **aisa-oxylabs** aparece como conectado. Se aparecer com falha, quase sempre o problema é o Python: refaça o [passo 2](#passo-2-conferir-o-python).

**Algumas respostas voltaram vazias ou com timeout**
Às vezes uma IA demora mais que o normal. O relatório lista as falhas; rode de novo só as perguntas que faltaram.

---

## Atualizar e desinstalar

Atualizar para a versão mais nova:

```
/plugin marketplace update aisa-geo
```

Desinstalar:

```
/plugin uninstall aisa-geo-oxylabs@aisa-geo
```

---

## Como funciona

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

### Testar o servidor sem o Claude

```bash
AISA_API_KEY=sk-aisa-SUA-CHAVE python3 mcp_server.py
```

Depois cole uma linha JSON-RPC e tecle Enter:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"verificar_configuracao","arguments":{}}}
```

---

## Cuidados

- **Respostas de IA mudam a cada vez.** Para acompanhar a evolução, repita as mesmas perguntas todo mês e guarde os arquivos JSON.
- **Visibilidade não é qualidade.** O relatório mostra quem aparece, não quem presta o melhor serviço.
- **Áreas reguladas** (saúde, advocacia, contabilidade): confira as regras de publicidade do conselho profissional antes de publicar conteúdo do tipo "o melhor de…".
- **Os arquivos `geo-*.json` podem ter dados de clientes.** O `.gitignore` deste repositório já evita que eles subam para o GitHub.

## Licença

MIT. Feito por [André Alencar](http://www.youtube.com/@empreendedorserial).
