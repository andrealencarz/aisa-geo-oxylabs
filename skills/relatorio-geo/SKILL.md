---
name: relatorio-geo
description: 'Relatório de GEO (visibilidade em respostas de IA) de uma empresa contra concorrentes. Pergunta ao ChatGPT, Gemini e Perplexity como um usuário real (Oxylabs via API AIsa), mede em quantas respostas cada marca aparece, quem aparece primeiro e quais sites as IAs usam como fonte, e entrega um relatório HTML com plano de ação. Use quando o usuário pedir relatório GEO, "o que as IAs falam da minha empresa", visibilidade no ChatGPT/Gemini/Perplexity ou comparação de presença em IA com concorrentes.'
---

# Relatório GEO: o que as IAs respondem sobre uma empresa

Mede a presença de uma empresa e dos concorrentes nas respostas do **ChatGPT**, **Gemini** e **Perplexity**, usando o Oxylabs LLM pela API da AIsa (as perguntas são feitas na interface de cada IA, como um usuário real faria).

## Ferramentas (servidor MCP `aisa-oxylabs` deste plugin)

- `verificar_configuracao`: confere se a chave da AIsa está configurada e é aceita. Gratuito.
- `geo_visibilidade`: roda o lote inteiro (perguntas × IAs) em paralelo, salva um JSON e devolve o resumo por marca.
- `oxylabs_llm_cotar`: cota uma pergunta sem executar. Gratuito.
- `oxylabs_llm_perguntar`: uma pergunta a uma IA, com resposta e fontes.
- `oxylabs_llm_job`, `oxylabs_llm_listar`, `oxylabs_llm_cancelar`: controle de jobs.

Não peça a chave da AIsa ao usuário: ela vem da configuração do plugin. Se a ferramenta disser que a chave não está configurada, oriente o usuário a preenchê-la nas configurações do plugin.

## Passo a passo

0. **Confira a configuração.** Na primeira vez da conversa, chame `verificar_configuracao`. Se `ok` vier `false`, mostre o `problema` ao usuário em linguagem simples e pare até ele resolver.

1. **Colete o contexto.** Pergunte só o que faltar:
   - empresa analisada (nome e domínio);
   - concorrentes (2 a 5, nome e domínio). Se o usuário não souber, faça 2 ou 3 perguntas de descoberta com `oxylabs_llm_perguntar` e use as marcas que mais aparecem;
   - setor e cidade/região (se o negócio for local);
   - idioma das perguntas (padrão: português do Brasil).

2. **Monte as perguntas (10 a 20).** Escreva como um cliente escreveria, sem citar a marca analisada. Misture:
   - descoberta: "qual a melhor {categoria} em {cidade}?", "{categoria} recomendada em {cidade}";
   - por necessidade/especialidade: "onde fazer {serviço} em {cidade}?";
   - por perfil: preço, premium, perto de um bairro, atendimento rápido;
   - comparação direta: "{marca} ou {concorrente}, qual é melhor?" (no máximo 2 ou 3 dessas);
   - reputação: "{marca} é confiável?" (1 por marca, opcional).
   Mostre a lista ao usuário antes de rodar.

3. **Cote e confirme o custo.** Chame `oxylabs_llm_cotar` para uma pergunta de cada IA, multiplique pelo número de perguntas e informe o total estimado. Rode só depois do "ok" do usuário, a menos que ele já tenha autorizado um orçamento.

4. **Rode** `geo_visibilidade` com as perguntas, as IAs (padrão: as três), as marcas (com `aliases` para grafias alternativas e `dominio`) e `geo_location` (ex.: "Brazil"). Use `output_dir` na pasta do projeto do usuário.

5. **Analise** o JSON salvo (caminho em `arquivo`). Leia as respostas completas, não só a contagem:
   - share de voz por marca e por IA (`resumo_por_marca`);
   - quem aparece primeiro com mais frequência (`primeira_citada`);
   - como cada IA descreve a empresa (pontos fortes, ressalvas, informações erradas ou desatualizadas);
   - perguntas em que concorrentes aparecem e a empresa não (lacunas);
   - domínios mais citados (`dominios_mais_citados`): são os sites que moldam a resposta das IAs e os alvos de relações públicas, diretórios e avaliações;
   - falhas e respostas vazias, para reportar no método.

6. **Entregue o relatório** como página HTML (artifact), com:
   - resposta curta: onde a empresa está em relação aos concorrentes;
   - matriz marca × IA com share de voz;
   - tabela pergunta × marca (mencionada sim/não, posição);
   - como as IAs descrevem a empresa (trechos curtos);
   - fontes que as IAs mais usam e se a empresa está nelas;
   - plano de ação priorizado (entrar nas fontes citadas, conteúdo que responda às perguntas sem presença, consistência de nome/endereço/telefone, avaliações, dados estruturados);
   - método e limitações: data, número de perguntas, respostas de IA variam a cada execução, custo total (`custo_total_usd`).

## Complementos opcionais

Se o conector AIsa (MCP de SEO, `mcp.aisa.one/seo/mcp`) estiver ativo, o relatório pode ganhar uma seção de SEO clássico: posição no Google orgânico e no Maps para as mesmas perguntas, autoridade de domínio e backlinks da empresa e dos concorrentes.

## Cuidados

- Respostas de IA mudam a cada execução. Para comparar ao longo do tempo, repita as mesmas perguntas e guarde os JSONs.
- Visibilidade em IA não mede qualidade do produto ou serviço.
- Em saúde, advocacia e outras áreas reguladas, recomendações de conteúdo devem respeitar as regras de publicidade do conselho profissional.
