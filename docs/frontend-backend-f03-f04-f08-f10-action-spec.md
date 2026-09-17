# CERES — plano de ação para F03, F04, F08 e F10

Data: 2026-09-15.
Estado: F03 e F10 implementados e verificados em código em 2026-09-15; publicação
F03 em produção permanece uma etapa operacional posterior ao deploy. F04 continua
em diagnóstico. F08 foi definido e implementado a partir do intervalo calibrado
da AVM, sem limites percentuais fixos.

Fechamento de consumidores ativos em 2026-09-16: a Visão Geral agora envia o
horizonte global e apresenta a série de liquidez publicada; catálogo, detalhe e
comparação recebem `market_heat` da mesma publicação H3 normalizada no backend.
O join do catálogo é feito na consulta da página, sem N+1. O artefato XGBoost
transacional permanece `candidate`: análise fresca só receberá faixa/classificação
calibrada quando um artefato revisado for promovido; estimativas armazenadas sem
limites persistidos retornam `INSUFFICIENT_CONFIDENCE`. Isso é uma trava de
linhagem deliberada, não uma lacuna a ser preenchida com percentuais arbitrários.

Verificação operacional de 2026-09-15: o refresh autorizado das resoluções H3
7, 8, 9 e 10 concluiu sem erro, mas encontrou zero imóveis e zero vendas elegíveis
em produção. Portanto nenhum valor regional de liquidez/heat foi publicado; o
frontend deve continuar exibindo indisponibilidade, não zero. O produtor precisa
ser executado novamente depois que dados globais reais, geocodificados e
`training_allowed` estiverem populados.

Complementa `frontend-backend-alignment-spec.md`. Os estados de implementação
daquele documento continuam válidos até implementação e verificação.

## 1. Decisões e escopo

| Item | Direção definida | Resultado esperado |
| --- | --- | --- |
| F03 | Liquidez regional baseada nas vendas da própria célula H3 | IMPLEMENTADO EM CÓDIGO — probabilidade de venda por célula, resolução e horizonte; requer refresh pós-deploy e suporte real |
| F04 | Esclarecer e verificar o artefato de forecast | Diagnóstico dos modelos treinados existentes e dos dados temporais necessários antes de escolher treinamento |
| F08 | Classificação autoritativa contra o intervalo calibrado da AVM | IMPLEMENTADO — abaixo/dentro/acima da faixa; intervalo ausente ou não calibrado retorna confiança insuficiente |
| F10 | Similaridade por cosseno calculada no backend | IMPLEMENTADO — score/ordenação/metadados no detalhe e par; contagem canônica no catálogo |

O trabalho continua na arquitetura atual: FastAPI, serviços determinísticos,
PostgreSQL/PostGIS, publicação offline e frontend consumidor. Não requer novo
serviço, fila, LLM ou banco vetorial. F09 e as demais lacunas mantêm seus estados.

## 2. Evidência no código atual

- `ceres/backend/services/liquidity_survival.py`: Kaplan–Meier para imóveis e
  portfólios; estratos atuais por cidade/bairro/tipo, sem H3. Suporte padrão de
  20 observações e 3 vendas. São limites operacionais existentes, não garantia
  de calibração estatística.
- `ceres/backend/repositories/platform_intelligence.py::liquidity_training_sources`:
  consulta status e duração, mas ainda não seleciona coordenadas.
- `ceres/backend/services/platform_intelligence.py::refresh_heatmaps`: publicação
  por resolução e observações históricas; local adequado para integrar resultados
  regionais pré-calculados.
- `ceres/ui/tupan-intel-core/src/api/market.js`: lê `indicators.liquidity`, mas
  `getMarketCells` ainda não aceita horizonte de liquidez. `periodDays` é rejeitado
  como filtro não suportado e não deve ser reutilizado silenciosamente.
- `ceres/train/analytics.py::analyze_tendency`: o caminho padrão lança
  `ForecastArtifactMissingError`; a rotina experimental instancia um regressor
  sem carregar árvores treinadas.
- `ceres/backend/services/forecast.py`: contrato de P10/P50/P90 e crescimento
  esperado existe, mas depende desse caminho indisponível.
- `ceres/backend/repositories/tenant_data.py::list_estate_comparables`: candidatos
  autorizados, ativos, do mesmo tipo e próximos; ordena por distância/data.
  `estate_local_statistics` calcula a contagem sobre todo o conjunto elegível.
- `ceres/ui/tupan-intel-core/src/api/properties.js`: contagem no catálogo e
  crescimento esperado ainda são `null`; a análise detalhada já recebe contagem.

## 3. F03 — liquidez por célula H3

### 3.1 População e definição

Para cada resolução selecionada, geocodificar cada episódio de anúncio na sua
célula e ajustar a curva usando somente episódios dessa célula. Não buscar
imóveis semelhantes, vizinhos ou uma curva municipal para preencher uma célula
sem suporte. Uma resolução mais ampla deve ser uma seleção explícita do usuário.

Vendas confirmadas são eventos. Anúncios ativos são observações censuradas à
direita: sabe-se que ainda não venderam até a data observada. Ambos precisam
entrar no denominador; usar apenas vendidos enviesaria a estimativa.

Definição regional proposta:

`liquidity_score(H3, T) = 100 × [1 − S_H3(T)]`

Interpretação: probabilidade estimada de venda até T dias desde a entrada no
mercado, para a população observada daquela célula. O mapa não possui a idade
de um anúncio individual. Por isso essa métrica difere da probabilidade
condicional de um imóvel já ativo há `a` dias, existente no backend:

`100 × [1 − S(a + T) / S(a)]`.

O portfólio mantém sua curva baseada exclusivamente no próprio histórico,
conforme a decisão anterior. Não será substituído pelo score regional.

### 3.2 Dados elegíveis e verificações

- Origem: base global autorizada para analytics, processada pelo publisher;
  nenhuma consulta individual de tenant calcula a população global.
- Exigir coordenadas válidas, identificação interna do episódio para deduplicar,
  status confiável, início do anúncio e data de venda/censura coerentes.
- Duração documentada pode ser usada quando sua semântica e data de referência
  forem verificadas. Não transformar datas invertidas em duração zero.
- Uma escritura/ITBI com data e preço, sem início do anúncio ou duração confiável,
  não basta para sobrevivência. Vincular ao episódio real ou reportar exclusão.
- Excluir demonstrações, duplicatas e eventos posteriores à data de corte.
- Distinguir retirada do mercado de venda; retirada não será contada como venda.
  A primeira versão seguirá a população active/sold atual e documentará a
  limitação de cobertura de anúncios retirados e possível viés de seleção.
- Preservar contagens de elegíveis/excluídos e motivos no relatório do publisher.
- Manter inicialmente os mínimos 20 observações/3 vendas; não extrapolar além
  do acompanhamento suportado. Ausência de evidência retorna `null` com motivo.
- Avaliar cobertura de durações e estabilidade por horizonte/resolução antes
  de publicação; não afirmar confiança calibrada com base só na contagem.

### 3.3 Publicação e contratos

1. Ampliar a extração offline com coordenadas e identidade interna para deduplicar.
2. Reutilizar as funções de sobrevivência com agrupamento exato por H3.
3. Calcular separadamente as resoluções 7, 8, 9 e 10; continuar validando 0–15
   na infraestrutura. Não obter score de célula pai pela média dos filhos.
4. Pré-calcular os horizontes existentes: 30, 60, 90, 180 e 365 dias. `custom`
   permanece sem score enquanto não houver horizonte numérico e publicação.
5. Persistir os valores por horizonte no agregado global existente, com schema
   de payload versionado. Reutilizar JSONB se comportar os campos sem nova tabela.
6. Acrescentar `liquidity_horizon_days` às consultas do mapa e métricas publicadas;
   API apenas seleciona o valor já publicado. Ausente: estado explícito, sem
   assumir silenciosamente 90 dias. Horizonte inválido: erro de validação.
7. Preservar `indicators.liquidity` como saída numérica compatível e acrescentar
   objeto tipado `liquidity_details` com `horizon_days`, `status`, `reason`,
   `observation_count`, `sale_event_count`, `model_version`, `as_of` e definição.
8. Histórico de liquidez usa dimensão `horizon_days`; consultas e unicidade
   incluem horizonte, H3, resolução e versão. Não misturar curvas de 30/365 dias.
9. Atualizar adapter, hooks e chaves de cache: célula/resolução/horizonte/filtros.
   Cancelar requisição anterior quando o seletor muda e evitar resposta antiga.
10. RegionPanel, mapa e MarketIntelligence exibem o valor, horizonte e suporte.
    Não substituir média de scores H3 por liquidez municipal/global sem um
    produtor específico para essa população.

Cada publicação é idempotente e substitui somente seu escopo/versionamento.
Trocar o horizonte não dispara treinamento, refresh ou agregação no HTTP.
Filtros sem publicação compatível continuam explicitamente não suportados.

Cache proposto: reutilizar o cache cliente existente, `staleTime` de 60 segundos,
com chave incluindo API/usuário autenticado, filtros, resolução e horizonte.
Limpar em logout; invalidar em refresh confirmado ou mudança do seletor.
Fonte de verdade: agregado PostgreSQL. O cache pode atrasar até 60 segundos
além da idade da publicação, cuja data deve ser exibida. Não adicionar Redis.

Não publicar imóveis, IDs de tenants, endereços ou curvas individuais. Somente
agregados com suporte mínimo cruzam a API global. Reutilizar exclusões, controle
de acesso e auditoria da publicação global já estabelecidos.

## 4. F10 — comparáveis por similaridade de cosseno

### 4.1 Responsabilidade e representação

O serviço de comparáveis será dono da seleção, cálculo e ranking. A API
transporta o score; React formata e exibe. Similaridade estrutural não é
probabilidade de venda, confiança da AVM ou proximidade de preço.

Proposta inicial de vetor: área, quartos, banheiros e vagas. Tipo e geografia
continuam filtros de elegibilidade; distância continua campo separado.
Não incluir estimativa AVM, preço pedido, scores 4L indisponíveis ou texto
gerado. Os valores estruturados continuam relacionais; pgvector não é necessário.

`similarity_score = dot(z_alvo, z_candidato) / (norm(z_alvo) × norm(z_candidato))`

- Versão inicial: transformação `log1p` dos quatro valores não negativos e
  padronização por médias/desvios congelados em referência autorizada/versionada.
  Pesos iguais são uma hipótese inicial explícita a validar.
- Congelar ordem, unidades, transformações e parâmetros em
  `similarity_feature_version`; não ajustar escalas por par ou página de resultados.
- Política inicial conservadora: exigir os quatro campos válidos para pontuar.
  Zero quartos/vagas pode ser observação válida; `null` não é zero.
  Vetor sem suporte completo ou com norma zero retorna `null` e motivo.
- Cosseno mede direção: vetores proporcionais podem ter score alto. Testes com
  imóveis de escalas muito diferentes devem verificar a representação antes de
  promovê-la. Um resultado ruim exige revisar o vetor, sem renomear outra métrica
  como cosseno.
- Escala canônica `[-1, 1]`, porque a padronização admite valores negativos.
  UI: “Similaridade (cosseno) · 0,87”, sem apresentar 87% de certeza.

### 4.2 Busca, contagens e API

1. Autorizar o imóvel alvo; manter o conjunto atual do mesmo tenant, tipo e raio
   (ou cidade/bairro quando faltarem coordenadas). Nenhum candidato privado de
   outro tenant pode aparecer como comparável.
2. Buscar conjunto limitado de candidatos antes de pontuar: proposta de até
   500 por distância/data/ID, com limite configurado no backend e timeout.
3. Ordenar esse conjunto por cosseno decrescente; desempatar por distância e ID.
   Scores ausentes ficam ao fim e permanecem identificados como não avaliados.
4. Retornar no máximo o limite de exibição atual. Se houve corte em 500,
   declarar ranking limitado ao conjunto recuperado, sem prometer top global.
5. Adicionar a `ComparableEstate`: `similarity_score: float|null`,
   `similarity_status`, `similarity_method: cosine`, `similarity_feature_version`.
6. Metadados da resposta distinguem `candidate_count`, `scored_count`,
   `returned_count`, `candidate_limit` e `truncated`.
7. `local_statistics.comparable_count` continua a contagem total elegível;
   estatísticas continuam referentes à população elegível, sem trocar
   silenciosamente para a amostra ranqueada.
8. No catálogo, resolver contagens em consulta em lote para a página autorizada,
   usando os mesmos predicados do detalhe. Evitar uma análise por linha.
   Similaridade é sempre relativa a um alvo; não atribuir um score solto a
   cada imóvel do catálogo.
9. Exibir score na tabela de comparáveis de PropertyDetail. Comparação direta
   entre dois imóveis pode reutilizar exatamente o mesmo serviço/versão.
   Tipos distintos ficam fora do domínio definido nesta versão.
10. AI recebe os mesmos resultados autorizados e metadados; pode explicá-los,
    sem recalcular score ou transformar ausência em valor.

Se a referência para padronização usar a base global, ela será publicada offline
somente como parâmetros agregados autorizados; nunca carregar dados privados de
outros tenants durante uma requisição. Não acrescentar cache de scores na primeira
versão; medir o custo para justificar eventual cache posterior.

## 5. F04 — o que significa artefato temporal

É o modelo já treinado e persistido para prever um valor futuro em um horizonte
definido. Em XGBoost inclui árvores aprendidas (divisões e valores das folhas),
objetivo, transformações/ordem das features, versão, data de corte e horizonte.
Um arquivo com `max_depth`, `learning_rate` etc. contém hiperparâmetros; ele não
substitui as árvores ajustadas aos dados.

Uma AVM de valor atual treinada não resolve automaticamente forecast. O alvo
precisa representar o futuro em relação à data de observação. Adicionar uma data
como feature de uma AVM corrente, por si só, não demonstra capacidade de prever
valorização. P10/P50/P90 de valor atual também não são quantis de preço futuro.

Plano para este item:

1. Inventariar arquivos de modelos existentes e carregar candidatos offline.
   Verificar árvores, alvo, features, horizonte, transformações e proveniência;
   corrigir a conclusão anterior se já existir artefato temporal válido.
2. Auditar dados com estado conhecido em `t` e alvo observado em `t+T`, evitando
   usar dados futuros no vetor. Verificar maturação de labels e cobertura por
   horizonte; negócios de imóveis diferentes não viram automaticamente uma
   série histórica do mesmo imóvel.
3. Documentar a definição do preço de referência de `expected_growth_pct`.
   Comparar futuro com preço pedido pode medir outra coisa que valorização;
   contrato deve explicitar denominador, data base e horizonte.
4. Se existir artefato válido, planejar adaptador de inferência e exposição.
   Se não existir, apresentar desenho de treinamento e limitações da base
   antes de introduzir um novo produtor.
5. Validar em corte temporal e por entidade para evitar vazamento; comparar com
   baseline, medir erro por horizonte, pinball loss e cobertura dos quantis.
   Quantis não devem cruzar. Critérios de promoção serão declarados antes do treino.
6. Somente depois conectar forecast individual e definir agregação regional/
   portfólio. Não fazer média ingênua de percentuais ou somar quantis como se
   isso produzisse intervalo de previsão calibrado do portfólio.

Esta especificação não autoriza afirmar que um forecast treinado já está
disponível. A pergunta sobre F04 fica respondida; criação de modelo novo e
publicação exigem o diagnóstico acima e decisão sobre o produtor.

## 6. F08 — classificação por intervalo calibrado

O backend compara o preço pedido diretamente aos limites inferior e superior
produzidos pelo artefato AVM promovido e calibrado com erros fora da amostra.
Valores abaixo, dentro (limites inclusivos) e acima retornam, respectivamente,
`BELOW_ESTIMATED_RANGE`, `WITHIN_ESTIMATED_RANGE` e
`ABOVE_ESTIMATED_RANGE`. Ausência de intervalo calibrado ou limites inválidos
retorna `INSUFFICIENT_CONFIDENCE`; ausência do preço pedido ou da estimativa
central não produz classificação. O frontend apenas traduz e apresenta esse
contrato junto da estimativa, faixa e desvio percentual. Não existem margens
fixas de ±5% ou ±10%.

## 7. Ordem de execução e critérios de conclusão

| Etapa | Entrega verificável | Critério |
| --- | --- | --- |
| 1 | Auditoria de durações/geocodificação F03 e candidatos/modelos F04/F10 | Relatório real de cobertura e artefatos; nenhum mock ocupa lacuna |
| 2 | Produtor regional F03 e contratos | Célula exata, horizonte e resolução reproduzíveis em fixtures conhecidas |
| 3 | Persistência offline e API F03 | Publicação idempotente; HTTP apenas consulta; histórico separa horizontes |
| 4 | Consumidores F03 | Seletor atual altera score, label e cache corretamente; null/motivo visíveis |
| 5 | Representação, ranking e contratos F10 | Cosseno reproduzível; tenant isolado; truncamento e ausência explícitos |
| 6 | Detalhe, comparação e contagem de catálogo F10 | Mesmo produtor; consulta em lote; contagens e população consistentes |
| 7 | Diagnóstico F04 e fechamento documental | Candidato existente conectado se validado; caso contrário lacuna e plano de treino explícitos |

Testes necessários: sobrevivência calculada à mão, censura, datas inválidas,
duplicatas, célula exata, várias resoluções, suporte insuficiente, horizonte
fora de acompanhamento, monotonicidade por horizonte, idempotência, ausência de
treinamento em HTTP, isolamento de tenant; cosseno conhecido, identidade,
simetria, unidades, norma zero, campos ausentes, escalas proporcionais, ranking
determinístico, contagens completas e truncamento. Testes de integração do
seletor devem conferir requests, respostas e atualização dos consumidores.

Executar testes backend pertinentes, testes frontend existentes, typecheck,
lint e build; registrar falhas anteriores separadamente. Publicação real será
verificada como etapa própria: código aprovado em teste não demonstra suporte
estatístico na base de produção. Atualizar o documento canônico por subcontrato,
distinguindo implementado, publicado, com suporte e consumido.

## 8. Fontes técnicas consultadas

- [XGBoost — Model IO](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html):
  persistência de árvores e objetivo, distinta de configuração de treinamento.
- [lifelines — KaplanMeierFitter](https://lifelines.readthedocs.io/en/stable/fitters/univariate/KaplanMeierFitter.html):
  durações e indicação de evento observado/censura.
- [scikit-learn — Pairwise metrics](https://scikit-learn.org/stable/modules/metrics.html):
  cosseno como produto interno normalizado. A representação dos imóveis e as
  políticas propostas acima são decisões de projeto CERES a verificar.
