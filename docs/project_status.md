<!-- markdownlint-disable MD013 MD033 -->

# PhysioFlow — Status do Projeto

> **Documento de handoff.** Snapshot do estado do projeto. Atualizar sempre que houver mudança estrutural.

**Última atualização:** 2026-09-27
**Versão do app:** 1.0 (tag `v1.0`; commit `bc69e10` é o citado no artigo)
**Mantenedor atual:** Daniel Hilário da Silva ([ORCID 0000-0002-0800-065X](https://orcid.org/0000-0002-0800-065X))

---

## TL;DR

PhysioFlow é uma aplicação Streamlit open-source para análise de dados de fisiologia vegetal (IRGA, clorofilômetro, ceptômetro) com forte ênfase em *guard-rails estatísticos* (confundimento categórico via Cramér's V, VIF com awareness de variáveis derivadas, GroupKFold por sítio, kriging em UTM, STL com bloqueio de séries esparsas, etc.). O app está deployado em [physioflow.streamlit.app](https://physioflow.streamlit.app/), com login via Supabase.

O **software paper** foi submetido à **Software Impacts** (manuscrito SIMPAC-D-26-00172); a revisão R1 foi reenviada em **2026-09-27** e aguarda decisão. O que restou de pendência está em §5, agora dividido entre o que depende da revista e o backlog técnico.

---

## 1. Visão geral

* **Nome:** PhysioFlow
* **Repositório:** [github.com/ML-Carbon-Project/physioFlow](https://github.com/ML-Carbon-Project/physioFlow) (**público**; espelho em `danielhilario-if/physioflow`)
* **Demo ao vivo:** [physioflow.streamlit.app](https://physioflow.streamlit.app/)
* **Cápsula reproduzível:** [10.24433/CO.9901925.v1](https://doi.org/10.24433/CO.9901925.v1) (Code Ocean, publicada)
* **Licença:** GPL-2.0-or-later (decisão consciente — não trocar para MIT)
* **Stack:** Streamlit + pandas + scipy + statsmodels + scikit-learn + esda + libpysal + geopandas + pyproj
* **Domínio:** ecofisiologia de culturas (soja e cana-de-açúcar), com dataset de referência do Goiás Verde (Rio Verde, GO)
* **Iniciativa:** Projeto Goiás Verde (IF Goiano – Campus Rio Verde + CEAGRE)

---

## 2. Estado do código

### 2.1 Páginas da UI (9)

1. **Upload** — validação de schema, 3 tiers, detecção de coluna vazia
2. **Pipeline e Processamento** — 4 etapas + 6 modos de réplica (mean, **median** ← adição feita por sugestão de pesquisador, unfold, replica-1/2/3)
3. **EDA** — 12 abas: Resumo, Qualidade (com **detecção de confundimento via Cramér's V**), Distribuições, Boxplots, Pairplot, Correlação, Espacial exploratório, Temporal, Composição, Inferência (KW + normalidade + **Q-Q plots** + VIF com **caveat de derivadas**), Hotspots, Outliers (5 métodos + consenso ≥3 com **caption de pressupostos**)
4. **Regressão** — bivariada com presets fisiológicos e custom
5. **Modelagem** — 5 modelos + holdout + CV; **GroupKFold opcional** com seletor de coluna de agrupamento
6. **Análise Espacial** — 6 abas (IDW, Moran's I/LISA, Getis-Ord Gi*, Grade UTM, Kriging, Basemap) — **todas em metros UTM internamente** (EPSG 32722 para Rio Verde)
7. **Série Temporal** — agregação diária + STL com **guard-rail bloqueando série < 10 datas reais**
8. **Comparação por grupo** — Mann-Whitney + log-linear por grupo + padrão horário
9. **Estatística Experimental** — ANOVA orientada ao delineamento (DIC, DBC, quadrado latino, fatorial 2–3 fatores, parcelas subdivididas, faixas, hierárquico), ANCOVA, regressão de doses e correlação; pressupostos (Shapiro–Wilk, Levene) com QQ-plot; comparação de médias (Tukey, Scott-Knott, Duncan, LSD, Scheffé, Dunnett) **todas usando o QMR do modelo ajustado**; exporta script Python reprodutível

### 2.2 Módulos de apoio

* `src/schema.py` — schema declarativo de 31 colunas em 3 tiers
* `src/pipeline.py` — pipeline determinístico + helper de detecção de data
* `src/stats_utils.py` — Cramér's V + detecção de confundimento + **todo o motor de delineamentos** (ANOVA por delineamento, ANCOVA, erro composto, comparação de médias, Dunnett)
* `src/ml/model_registry.py` — registro declarativo de 5 regressores e 7 classificadores
* `src/components/` — controles de dataset, filtros e helper de figuras compartilhados entre páginas
* `src/auth.py` — autenticação Supabase opcional (controlada por `enabled` em secrets)
* `src/i18n/` — 3 idiomas (PT/EN/ES) em **paridade total** (audit_keys retorna 0 missing / 0 extra)

### 2.3 Testes

* **171 testes passando** (113 funções `pytest`), **76 %** de cobertura total
* `src/stats_utils.py`: 92 % de cobertura
* `src/pipeline.py`: 86 %
* `src/schema.py`: 85 %
* `src/state.py`: 72 %
* `src/auth.py`: 12 % — **maior lacuna restante**
* Inclui testes *headless* de página via `streamlit.testing.v1.AppTest` e regressões congeladas contra o R em `tests/test_sample_datasets.py::TestPostHocVsR`

### 2.4 CI/CD

* `.github/workflows/ci.yml`: lint (ruff) + types (mypy) + tests (pytest com coverage) em Python 3.10/3.11/3.12. **Verde desde `bc69e10`** (2026-09-27) — antes disso nunca havia passado, por três causas independentes descritas no [`CHANGELOG.md`](../CHANGELOG.md). `ruff` e `mypy` estão **pinados** em `requirements-dev.txt`: com faixa aberta o resultado passava a depender da data da execução, não do código
* `.github/workflows/build-manual.yml`: gera PDF do manual via pandoc + XeLaTeX em tags `v*`, mudanças em manual/screenshots, ou workflow_dispatch manual

---

## 3. Estado da documentação

### 3.1 Documentação para usuário final

* **[`docs/manual.pt.md`](manual.pt.md)** — 1325 linhas, 17 capítulos, 26 screenshots
* **[`docs/manual.en.md`](manual.en.md)** — 1323 linhas, **tradução completa** (não é mais esqueleto)
* **[`docs/manual.es.md`](manual.es.md)** — 1291 linhas, **tradução completa**

### 3.2 Documentação para desenvolvedor

* [`docs/architecture.md`](architecture.md) — layout dos módulos
* [`docs/data_dictionary.md`](data_dictionary.md) — schema oficial das 31 colunas
* [`docs/deployment.md`](deployment.md) — Docker, Streamlit Cloud
* [`docs/contributing.md`](contributing.md) — PR workflow
* [`docs/i18n.md`](i18n.md) — como adicionar idiomas

### 3.3 Documentos do projeto

* `README.md` / `README.pt.md` / `README.es.md` — com badges, link para manual e demo
* [`CITATION.cff`](../CITATION.cff) — Citation File Format 1.2.0, com os 11 autores e ORCIDs
* [`CHANGELOG.md`](../CHANGELOG.md) — separa a v1.0 (`bc69e10`, a versão citada no artigo) do que veio depois. **Necessário** porque a `main` já divergiu com uma mudança que altera resultados
* [`docs/validacao_externa.md`](validacao_externa.md) — validação número a número contra o R, dataset por dataset
* `data/data-README.md` e `data/data-LICENSE.txt` — proveniência e licença de cada arquivo em `data/`

### 3.4 Infraestrutura de geração PDF

* `scripts/build_manual_pdf.sh` — script bash (pandoc + XeLaTeX)
* `docs/manual_metadata.yaml` — config pandoc (capa, fontes, geometria A4)
* `.github/workflows/build-manual.yml` — gera PDF automático em release tag

---

## 4. Decisões metodológicas

Lista das decisões mais importantes tomadas durante a auditoria, com justificativa. Importante manter — se mudar algo aqui, atualizar o capítulo correspondente do manual.

| # | Decisão | Justificativa |
|---|---|---|
| 1 | **Tratamento de coluna 100 % vazia** flagged separadamente de "ausente" | Caso `Manejo` e `Textura` no dataset Rio Verde — coluna existia mas era inútil; antes passava como "presente" |
| 2 | **Warning quando descarte > 50 %** em qualquer etapa do pipeline | Dataset Rio Verde perde 95 % nas etapas (grade incompleta) — usuário precisa saber |
| 3 | **VIF com caption sobre variáveis derivadas** | `Ci/Ca`, `A/Ci`, `EUA`, `ETR` inflam VIF por construção matemática; não é problema de dados |
| 4 | **Q-Q plot ao lado de testes de normalidade** | Para n > algumas centenas, Shapiro rejeita quase sempre — usuário precisa do diagnóstico visual |
| 5 | **Kruskal-Wallis com slider de N mínimo por grupo** | Padrão antigo aceitava grupos com n=2 (sem poder); novo default n=5 com coluna `dropped_levels` |
| 6 | **STL bloqueado quando < 10 datas distintas** | Dataset Rio Verde só tem 3 datas — STL com 90 % interpolação é estatisticamente vazia |
| 7 | **EllipticEnvelope no consenso de outliers fica, mas com caption** | Assume normalidade multivariada — não confiável em dados bimodais (soja+cana) |
| 8 | **Modo Mediana** adicionado aos 5 modos de réplica originais | Sugestão de pesquisador; equivalente à média com n=2, ganho real só em IAF (n=3) |
| 9 | **`t()` agora honra argumento `default=`** | O padrão `t("chave", default="texto")` espalhado pelo código era mentira — fallback nunca usado |
| 10 | **Helper único de detecção de data** | Páginas tinham listas inconsistentes; agora `find_date_column()` em `pipeline.py` coage object→datetime64 |
| 11 | **Detecção de confundimento via Cramér's V** na aba Qualidade | Caso `Fazenda ⟷ Cultura ⟷ Uso atual` redundantes no Rio Verde — Moran's I altíssimo era confundimento, não estrutura espacial |
| 12 | **GroupKFold opcional na Modelagem** com seletor de coluna | Pseudoreplicação inflama R² aleatório; coluna sintética "Fazenda + Ponto" é o default |
| 13 | **Reprojeção UTM dinâmica para IDW, kriging, Moran KNN, Gi*** | Distância em graus de lat/lon é anisotrópica; agora EPSG calculado automaticamente, alcance em metros físicos |
| 14 | **Dunnett usa o QMR do delineamento** (`ms_error`/`df_error` do modelo), não um erro one-way | Era o único método de comparação que não recebia o erro do modelo: num DBC a variação de bloco entrava no resíduo e inflava o valor-p. No `sk_rcbd` isso invertia uma decisão a 5 % (p = 0,0385 → 0,0539). Corrigido **depois** da submissão — o §5 do artigo descreve a limitação como ela está na v1.0 |
| 15 | **Semente fixa no integrador da t multivariada** (Dunnett) | A cdf é estimada por quase-Monte Carlo; sem semente, os mesmos dados davam valores-p ligeiramente diferentes a cada execução |

---

## 5. Pendências

### 5.1 Resolvidas desde a versão anterior deste documento

| # | Item | Como ficou |
|---|---|---|
| 1 | Lista final de autores + ORCIDs + afiliações | 11 autores no `CITATION.cff`, no `pyproject.toml` e no artigo |
| 2 | Repositório público | Feito, com espelho em `danielhilario-if/physioflow` |
| 3 | Tag `v1.0` | Criada |
| 4 | Cobertura de testes > 70 % | **76 %** (era 57 %) |
| 5 | Tradução completa do manual EN | Feita; ES também |
| 6 | CI passando | Verde desde `bc69e10`; ver [`CHANGELOG.md`](../CHANGELOG.md) |
| 7 | Submissão do paper | Submetido à Software Impacts; R1 reenviada em 2026-09-27 |

### 5.2 Abertas

| # | Item | Situação |
|---|---|---|
| A | **Decisão da revista sobre a R1** | Aguardando. Nada a fazer até a resposta |
| B | **DOI Zenodo** | Não feito — o `CITATION.cff` ainda tem o campo `doi` comentado. O artigo não depende dele (C2 aponta o commit, C3 a cápsula do Code Ocean), mas ele daria citabilidade ao próprio código |
| C | **Release no GitHub** | A tag `v1.0` existe, mas não há *release* publicada. É pré-requisito do webhook do Zenodo |
| D | **Tabela comparativa com alternativas** | Não entrou no artigo, que tem só a tabela de metadados e a da ANOVA do oats. A introdução cita softwares vizinhos (`apsimNGpy`, `prismatools`), mas não há comparação sistemática |
| E | **Validação por usuário externo** | Só feedback informal dos usuários do Goiás Verde. O artigo declara isso explicitamente, sem alegar avaliação controlada |
| F | **Cobertura de `src/auth.py`** (12 %) | Maior lacuna de teste restante |

### 5.3 Backlog técnico

| # | Item | Esforço |
|---|---|---|
| G | Ajuda contextual no app via `help=` em selectboxes/sliders | Médio |
| H | Aviso de "variável quase-constante" no painel de correlação | Baixo |
| I | Validação de faixa fisiológica no schema (`valid_range` em `ColumnSpec`) | Médio |
| J | Integrar a aba "Dicionário" do Excel como tooltips | Baixo |
| K | Imagem de social preview (1280×640) | Baixo |
| L | Imagem Docker pública para deploy em um comando | Médio |

---

## 6. Próximos passos

O caminho crítico agora é externo: **aguardar a decisão da Software Impacts sobre a R1**.

Enquanto isso, em ordem de retorno sobre esforço:

1. **Publicar a release `v1.0`** no GitHub a partir da tag existente (5 min) e **ativar o webhook do Zenodo** — sai o DOI do código, que hoje falta no `CITATION.cff`.
2. **Cobrir `src/auth.py`** com testes: é o único módulo em cobertura de um dígito.
3. Backlog de UX (§5.3 G–J), que melhora o app sem tocar em estatística.

Se a revista pedir uma R2, o material de trabalho está no repositório do manuscrito (`physioflow_Software_Impacts`), que é separado deste.

---

## 7. Quick start para nova sessão

Se você (ou outra IA) abrir este projeto sem o histórico desta conversa, comece por:

1. **Ler este arquivo** (você está lendo).
2. **Ler `docs/manual.pt.md`** para entender o que o app faz do ponto de vista do usuário.
3. **Ler `docs/architecture.md`** para entender a estrutura do código.
4. **Ler `CITATION.cff`** para entender autoria e licença.
5. **Rodar `git log --oneline -20`** para ver mudanças recentes.
6. **Rodar `pytest`** para confirmar que tudo passa (esperado: **171 passed**). O `pythonpath` está declarado no `pyproject.toml`, então não é preciso exportar `PYTHONPATH`.
7. **Verificar `.streamlit/secrets.toml.example`** para entender o setup de auth (se for ativar).
8. **Verificar `docs/img/manual/README.md`** para entender a convenção de screenshots.

Depois disso, você tem ~80 % do contexto do projeto.

---

## 8. Histórico das fases de desenvolvimento

| Fase | Período | Entregáveis |
|---|---|---|
| **0. Pré-existente** | Antes de 2026-05 | App básico com 6 páginas, fork do projeto "ChamberFlux" para fluxo de gases |
| **1. Auditoria estatística** | 2026-05-28 | 11 prioridades de correção implementadas + opção D UTM + Mediana (sugestão de pesquisador) + correção de `t()` |
| **2. Manual de operação** | 2026-05-28 | 1248 linhas em PT, 26 screenshots, 15 capítulos. Espelho EN com Abstract + Cap 1; ES esqueleto |
| **3. Identidade do projeto** | 2026-05-28 | Rename ChamberFlux → PhysioFlow em todos os arquivos; ORCID Daniel; CITATION.cff |
| **4. Deploy & infraestrutura** | 2026-05-28 | Streamlit Cloud em `physioflow.streamlit.app`; remoção do `geobr` (incompatível com Python 3.14 do Cloud); workflows GitHub Actions |
| **5. Paper** | 2026-06 a 2026-08 | Manuscrito Software Impacts redigido e submetido (SIMPAC-D-26-00172) |
| **6. Revisão R1** | 2026-09 | Respostas aos revisores; cápsula Code Ocean publicada (DOI 10.24433/CO.9901925.v1); validação post-hoc contra o R incorporada ao repositório; CI destravado; R1 reenviada em 27/09 |
| **7. Correções pós-submissão** | 2026-09-27+ | Dunnett passa a usar o QMR do delineamento (altera resultados — ver §4, decisão 14); `CHANGELOG.md` criado para separar a v1.0 do que veio depois |

---

*Para perguntas sobre este documento ou sobre o projeto, abra uma issue em [github.com/ML-Carbon-Project/physioFlow/issues](https://github.com/ML-Carbon-Project/physioFlow/issues).*
