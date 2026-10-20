# Relatório GEO: o que as IAs respondem sobre uma empresa

Monte um relatório de GEO (visibilidade em respostas de IA) usando as ferramentas da extensão **GEO (Oxylabs via AIsa)**. Elas perguntam ao ChatGPT, Gemini e Perplexity como um usuário real faria.

## Passo a passo

0. **Confira a configuração.** Chame `verificar_configuracao`. Se `ok` vier `false`, explique o `problema` em linguagem simples e pare até o usuário resolver. Para trocar a chave: Configurações → Extensões → GEO.

1. **Colete o contexto.** Pergunte só o que faltar:
   - empresa analisada (nome e site);
   - concorrentes (2 a 5, nome e site). Se o usuário não souber, faça 2 ou 3 perguntas de descoberta com `oxylabs_llm_perguntar` e proponha as marcas que mais aparecem;
   - setor e cidade/região, se o negócio for local.

2. **Monte de 10 a 20 perguntas** como um cliente escreveria, sem citar a marca analisada:
   - descoberta: "qual a melhor {categoria} em {cidade}?";
   - por necessidade: "onde fazer {serviço} em {cidade}?";
   - por perfil: preço, premium, bairro, atendimento rápido;
   - comparação direta: "{marca} ou {concorrente}, qual é melhor?" (no máximo 2 ou 3);
   - reputação: "{marca} é confiável?" (opcional).
   Mostre a lista e espere o usuário aprovar.

3. **Cote e confirme o custo.** Chame `oxylabs_llm_cotar` para uma pergunta de cada IA, multiplique pelo total de perguntas e informe o custo estimado em dólares. Rode só depois do "ok".

4. **Rode** `geo_visibilidade` com as perguntas, as três IAs, as marcas (com `aliases` para grafias alternativas e `dominio`) e `geo_location` "Brazil" (ou o país do negócio). Leva de 1 a 3 minutos.

5. **Analise** o retorno, lendo as respostas completas e não só a contagem:
   - share de voz por marca e por IA (`resumo_por_marca`);
   - quem aparece primeiro com mais frequência (`primeira_citada`);
   - como cada IA descreve a empresa: pontos fortes, ressalvas, informações erradas ou desatualizadas;
   - perguntas em que concorrentes aparecem e a empresa não;
   - domínios mais citados (`dominios_mais_citados`): os sites que moldam a resposta das IAs;
   - falhas e respostas vazias.

6. **Entregue o relatório como um artifact HTML**, com:
   - resposta curta: onde a empresa está em relação aos concorrentes;
   - matriz marca × IA com share de voz;
   - tabela pergunta × marca (mencionada sim/não, posição);
   - como as IAs descrevem a empresa (trechos curtos);
   - fontes que as IAs mais usam e se a empresa está nelas;
   - plano de ação priorizado (entrar nas fontes citadas, conteúdo para as perguntas sem presença, consistência de nome/endereço/telefone, avaliações, dados estruturados);
   - método e limitações: data, nº de perguntas, respostas de IA variam a cada execução, custo total (`custo_total_usd`) e onde ficou salvo o JSON (`arquivo`).

## Cuidados

- Respostas de IA mudam a cada execução. Para acompanhar a evolução, repita as mesmas perguntas e compare os JSONs.
- Visibilidade em IA não mede a qualidade do produto ou serviço.
- Em saúde, advocacia e outras áreas reguladas, as recomendações de conteúdo devem respeitar as regras de publicidade do conselho profissional.
