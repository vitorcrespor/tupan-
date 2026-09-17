# Carteira de demonstração e mapa ITBI — 13/09/2026

## Dados gravados

- Carteira `Demonstração Ceres · Indaiatuba`, vinculada à associação existente da conta solicitante.
- 12 imóveis no escopo da organização, identificados por `source_name=ceres_demo_academic_v1` e `attributes.is_demo=true`.
- Endereços geocodificados a partir da planilha acadêmica. Área, tipo, quartos, banheiros, vagas, anúncio e DOM são simulados e discriminados em `synthetic_fields`.
- `estimated_price` e `last_sale_price` permanecem nulos. O valor histórico de referência fica em atributos, sem passar por venda real do imóvel fictício.
- IDs determinísticos e inserções `ON CONFLICT DO NOTHING` permitem repetir a preparação sem duplicar nem sobrescrever alterações do usuário.
- Consultas de treinamento e agregação global excluem imóveis demo e registros com `training_allowed=false`.

## Mapa global de transações reais

A publicação não lê a carteira demo. Usa diretamente registros da planilha:

| Etapa | Quantidade |
| --- | ---: |
| Linhas originais | 64.163 |
| Transações elegíveis após filtros e deduplicação | 24.437 |
| Endereços consultados no Google | 128 |
| Endereços aceitos | 81 |
| Transações com geocodificação aceita | 4.790 |
| Células H3, resolução 9 | 62 |

Filtros: venda e compra sem leilão/arrematação/cessão, transferência de 100%, preço declarado de R$ 100 mil a R$ 3 milhões, rua/número/bairro completos. Duplicatas são identificadas por cadastro, data de emissão e preço.

Geocodificação aceita apenas cidade e número compatíveis, sem correspondência parcial, com precisão `ROOFTOP` ou `RANGE_INTERPOLATED`. A seleção prioriza endereços frequentes para limitar chamadas. **É uma amostra enviesada para endereços frequentes; não cobre todo o município.** Datas são de emissão, conforme a fonte, e não foram confirmadas como datas exatas de venda.

As células publicadas têm `scope=platform`, sem organização, endereço exato, cadastro ou portfólio. Exibem contagem de transações e valor médio/mediano declarado, em BRL. Não são inventário de anúncios, preço/m² ou escore de aquecimento.

## Contratos conectados

- `GET /api/v1/market/regions?published_only=true`: cidades/bairros publicados. Com `false`, inclui também imóveis do tenant autenticado.
- `GET /api/v1/market/heatmap`: leitura dos agregados pré-calculados.
- `metrics.dataset_kind=transactions`: apresentação de ITBI e suas unidades, distinguindo anúncios.
- Filtros começam sem cidade imposta. Alterar cidade limpa o bairro anterior.
- O mapa enquadra as geometrias retornadas. Não fica fixo em São Paulo.
- O antigo basemap CARTO retornava mosaicos com a marca “API key required”. Foi substituído pelo endpoint padrão OpenStreetMap, com atribuição visível e cache normal do navegador, conforme a [política de tiles](https://operations.osmfoundation.org/policies/tiles/).
- Carteira e detalhe expõem a descrição da demonstração.

## Candidato XGBoost

Artefato local separado: `ceres/train/artifacts/academic_address_candidate.json` e respectivo metadata. Usa a transação mais recente de cada cadastro geocodificado, para evitar repetir o imóvel entre janelas. Entradas: localização, cidade e estado. Não imputa área ou quartos.

| Resultado | Valor |
| --- | ---: |
| Treino / calibração / teste | 2.330 / 777 / 777 |
| MAE no teste | R$ 167.304 |
| Erro percentual absoluto mediano | 35,31% |
| Cobertura observada do intervalo nominal de 80% | 68,21% |
| Largura mediana do intervalo / previsão | 112,22% |

O candidato tem `promotion_status=candidate` e `production_eligible=false`. A localização é geocodificação atual, sem certificação histórica; a fonte não confirma transação entre partes independentes nem contém características estruturais. Estes limites impedem tratar o ensaio como modelo de produção. Os resultados não são comparáveis diretamente ao candidato anterior de Campinas, que usa outra população e outros atributos.

## Reexecução

No diretório `ceres`, com as credenciais somente no `.env` do backend:

```powershell
python -m backend.seed_demo_portfolio --source <planilha.xlsx> --city Indaiatuba --max-geocodes 128
python -m backend.seed_demo_portfolio --source <planilha.xlsx> --city Indaiatuba --max-geocodes 128 --email <conta-existente> --apply --train
python -m backend.verify_demo_portfolio --email <conta-existente> --output ../data/enrichment/demo_api_snapshot.json
```

Primeiro comando prepara sem gravar no banco. O segundo aplica o seed e treina. O terceiro verifica rotas com transporte ASGI isolado e a associação real do banco, sem criar sessões ou alterar autenticação da API em execução. Sua captura alimenta o teste visual opcional `tests/demo-data.test.mjs`.

O processador global configurado por `PLATFORM_INTELLIGENCE_DATABASE_URL` ainda aponta para um host que não resolve. Esta preparação pontual usa a conexão administrativa já configurada em `DATABASE_API_URL`. Isso não valida o agendamento de futuras atualizações globais.

## Verificações executadas

- 19 testes direcionados: passaram.
- Suíte backend: 59 testes, 55 passaram, 3 ignorados e 1 falha preexistente no teste de readiness, que espera 503 mesmo com `DATABASE_API_URL` configurado.
- Verificação real do banco através das rotas ASGI: portfólio, catálogo, imóvel, comparação, comparação de par, regiões, mapa e métricas publicadas retornaram 200. Todos os componentes da análise do portfólio tiveram sucesso. A ramificação AVM da análise individual retornou degradação por timeout, sem derrubar o restante.
- Acesso a imóvel e portfólio com outro tenant: 404, sem dados.
- Teste de apresentação com captura das respostas reais do backend: carteira e 62 células renderizaram sem erro JavaScript. Autenticação foi substituída somente nesse navegador isolado de teste; não representa um novo login real.
- Build de produção e lint: passaram.
- Typecheck: 86 erros restantes de tipagem preexistente, incluindo componentes de tabela, interfaces React, seletores e `ScoreBar`; o erro introduzido no tipo dos metadados de mapa foi corrigido.
- API local reiniciada: `/health` voltou a responder 200.
