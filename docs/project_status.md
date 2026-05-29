<!-- markdownlint-disable MD013 MD033 -->

# PhysioFlow — Status do Projeto

> **Documento de handoff.** Snapshot do estado do projeto na conclusão da fase 1 (auditoria estatística + manual + deploy + preparação para artigo). Atualizar sempre que houver mudança estrutural.

**Última atualização:** 2026-05-28
**Versão do app:** 1.0 (não-tagueada ainda — aguardando lista final de autores)
**Mantenedor atual:** Daniel Hilário da Silva ([ORCID 0000-0002-0800-065X](https://orcid.org/0000-0002-0800-065X))

---

## TL;DR

PhysioFlow é uma aplicação Streamlit open-source para análise de dados de fisiologia vegetal (IRGA, clorofilômetro, ceptômetro) com forte ênfase em *guard-rails estatísticos* (confundimento categórico via Cramér's V, VIF com awareness de variáveis derivadas, GroupKFold por sítio, kriging em UTM, STL com bloqueio de séries esparsas, etc.). O app está deployado em [physioflow.streamlit.app](https://physioflow.streamlit.app/), com login via Supabase. A próxima fase é submeter um **software paper** para **Software Impacts** ou **SoftwareX** (recomendado começar pelo primeiro). Faltam algumas pendências antes da submissão — todas listadas em §5.

---

## 1. Visão geral

* **Nome:** PhysioFlow
* **Repositório:** [github.com/ML-Carbon-Project/physioFlow](https://github.com/ML-Carbon-Project/physioFlow) (atualmente privado)
* **Demo ao vivo:** [physioflow.streamlit.app](https://physioflow.streamlit.app/) (depende do repo estar público; cai quando Cloud reiniciar)
* **Licença:** GPL-2.0-or-later (decisão consciente — não trocar para MIT)
* **Stack:** Streamlit + pandas + scipy + statsmodels + scikit-learn + esda + libpysal + geopandas + pyproj
* **Domínio:** ecofisiologia de culturas (soja e cana-de-açúcar), com dataset de referência do Goiás Verde (Rio Verde, GO)
* **Iniciativa:** Projeto Goiás Verde (IF Goiano – Campus Rio Verde + CEAGRE)

---

## 2. Estado do código

### 2.1 Páginas da UI (8)

1. **Upload** — validação de schema, 3 tiers, detecção de coluna vazia
2. **Pipeline e Processamento** — 4 etapas + 6 modos de réplica (mean, **median** ← adição feita por sugestão de pesquisador, unfold, replica-1/2/3)
3. **EDA** — 12 abas: Resumo, Qualidade (com **detecção de confundimento via Cramér's V**), Distribuições, Boxplots, Pairplot, Correlação, Espacial exploratório, Temporal, Composição, Inferência (KW + normalidade + **Q-Q plots** + VIF com **caveat de derivadas**), Hotspots, Outliers (5 métodos + consenso ≥3 com **caption de pressupostos**)
4. **Regressão** — bivariada com presets fisiológicos e custom
5. **Modelagem** — 5 modelos + holdout + CV; **GroupKFold opcional** com seletor de coluna de agrupamento
6. **Análise Espacial** — 6 abas (IDW, Moran's I/LISA, Getis-Ord Gi*, Grade UTM, Kriging, Basemap) — **todas em metros UTM internamente** (EPSG 32722 para Rio Verde)
7. **Série Temporal** — agregação diária + STL com **guard-rail bloqueando série < 10 datas reais**
8. **Comparação por grupo** — Mann-Whitney + log-linear por grupo + padrão horário

### 2.2 Módulos de apoio

* `src/schema.py` — schema declarativo de 31 colunas em 3 tiers
* `src/pipeline.py` — pipeline determinístico + helper de detecção de data
* `src/stats_utils.py` — Cramér's V + detecção de confundimento
* `src/auth.py` — autenticação Supabase opcional (controlada por `enabled` em secrets)
* `src/i18n/` — 3 idiomas (PT/EN/ES) em **paridade total** (audit_keys retorna 0 missing / 0 extra)

### 2.3 Testes

* **47 testes passando**, 57 % de cobertura total
* `src/schema.py`: 86 % de cobertura
* `src/stats_utils.py`: 89 %
* `src/pipeline.py`: 79 %
* `src/i18n`: 60 %
* `src/auth.py`, `src/ml/`, `src/state.py`, `src/config/`: cobertura baixa ou 0 % — **pendência para SoftwareX**

### 2.4 CI/CD

* `.github/workflows/ci.yml`: lint (ruff) + types (mypy) + tests (pytest com coverage) em Python 3.10/3.11/3.12
* `.github/workflows/build-manual.yml`: gera PDF do manual via pandoc + XeLaTeX em tags `v*`, mudanças em manual/screenshots, ou workflow_dispatch manual

---

## 3. Estado da documentação

### 3.1 Documentação para usuário final

* **[`docs/manual.pt.md`](manual.pt.md)** — 1248 linhas, 15 capítulos, 26 screenshots, completo
* **[`docs/manual.en.md`](manual.en.md)** — Extended Abstract de ~500 palavras + Capítulo 1 traduzido; demais como esqueleto
* **[`docs/manual.es.md`](manual.es.md)** — só esqueleto espelhado

### 3.2 Documentação para desenvolvedor

* [`docs/architecture.md`](architecture.md) — layout dos módulos
* [`docs/data_dictionary.md`](data_dictionary.md) — schema oficial das 31 colunas
* [`docs/deployment.md`](deployment.md) — Docker, Streamlit Cloud
* [`docs/contributing.md`](contributing.md) — PR workflow
* [`docs/i18n.md`](i18n.md) — como adicionar idiomas

### 3.3 Documentos do projeto

* `README.md` / `README.pt.md` / `README.es.md` — com badges, link para manual e demo
* [`CITATION.cff`](../CITATION.cff) — formato Citation File Format 1.2.0; ORCID do Daniel já incluído

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

---

## 5. Pendências para submissão do paper

### 5.1 Bloqueantes (precisam ser resolvidos antes da submissão)

| # | Pendência | Esforço | Responsável |
|---|---|---|---|
| 1 | **Definir lista final de autores + ORCIDs + afiliações** — não publicar DOI antes (versão imutável) | Externo (alinhamento com equipe) | Daniel |
| 2 | Atualizar `CITATION.cff` e `pyproject.toml` com lista final de autores | Trivial (eu faço quando você passar) | Eu, sob direção |
| 3 | **Criar release v1.0** no GitHub | 5 min | Daniel |
| 4 | **Conectar repo ao Zenodo** + ativar webhook | 5 min | Daniel |
| 5 | Atualizar `CITATION.cff` com DOI gerado | Trivial | Eu |
| 6 | Adicionar badge DOI nos 3 READMEs | Trivial | Eu |
| 7 | **Tornar repo público novamente** antes da submissão (necessário para revisores) | 1 min | Daniel |
| 8 | **Tabela comparativa com alternativas** no manuscrito (R `agricolae`, R `nlme`, FluxSync, Plotly Dash apps similares) | Médio (revisão de literatura) | Daniel + eu |
| 9 | **Validação por usuário externo** — 1-2 pesquisadores testando e dando feedback público (issue ou citação) | Externo | Daniel |

### 5.2 Não-bloqueantes (qualidade)

| # | Item | Esforço |
|---|---|---|
| A | Subir cobertura de testes para >70 % (cobrir `ml/`, `state.py`, `auth.py`) | Médio |
| B | Tradução completa do manual para EN | Médio-alto |
| C | Ajuda contextual no app via `help=` em selectboxes/sliders (camada 3 da estratégia (d) do manual) | Médio |
| D | Aviso de "variável quase-constante" no painel de correlação (caso `Ca` no Rio Verde) | Baixo |
| E | Validação de faixa fisiológica nos limites do schema (`valid_range` em `ColumnSpec`) | Médio |
| F | Integrar a aba "Dicionário" do Excel como tooltips no app | Baixo |
| G | Social preview image (1280×640 png) para link no Twitter/LinkedIn | Baixo |

### 5.3 Escolha entre revistas

* **Software Impacts** (Elsevier, OA) — porta de entrada mais natural agora. 3-6 páginas. Aceita software em maturação. Tempo de revisão ~2-3 meses.
* **SoftwareX** (Elsevier, OA) — mais exigente. 6-10 páginas. Costuma exigir validação externa publicada e cobertura de testes alta. Viável em 6-12 meses se trabalhar nas pendências 5.2-A, B e C.

---

## 6. Próximos passos imediatos

Em ordem de prioridade (dependências entre eles):

1. **Definir lista de autores** (você + equipe) — sem isso o DOI não pode ser feito de forma honesta.
2. **Atualizar `CITATION.cff` e `pyproject.toml`** com a lista (1 min meu trabalho).
3. **Tornar repo público + criar tag `v1.0` + release + ativar Zenodo** → DOI sai automático (~10 min seu trabalho).
4. **Adicionar badge DOI nos READMEs** (1 min meu).
5. **Esboçar manuscrito** Software Impacts (~5-6 páginas) reaproveitando o Extended Abstract de `manual.en.md`. **Estrutura típica:**
   - Motivation and significance
   - Software description (architecture, functionalities)
   - Illustrative examples (caso Rio Verde já documentado)
   - Impact
   - Conclusions
   - References
6. **Tabela comparativa com alternativas** (item 5.1-8). Pesquisa de literatura nas alternativas: `agricolae` (R), `nlme` (R), FluxSync, alguns Plotly Dash apps de agronomia.
7. **Convidar 1-2 pesquisadores externos** a testar o app (Goiás Verde tem time) e arquivar feedback como GitHub Issues ou citações.
8. **Submeter para Software Impacts**.

---

## 7. Quick start para nova sessão

Se você (ou outra IA) abrir este projeto sem o histórico desta conversa, comece por:

1. **Ler este arquivo** (você está lendo).
2. **Ler `docs/manual.pt.md`** para entender o que o app faz do ponto de vista do usuário.
3. **Ler `docs/architecture.md`** para entender a estrutura do código.
4. **Ler `CITATION.cff`** para entender autoria e licença.
5. **Rodar `git log --oneline -20`** para ver mudanças recentes.
6. **Rodar `PYTHONPATH=. pytest tests/`** para confirmar que tudo passa (esperado: 47 passed).
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
| **5. (em curso) Paper** | 2026-05-29+ | Manuscrito Software Impacts a redigir |

---

*Para perguntas sobre este documento ou sobre o projeto, abra uma issue em [github.com/ML-Carbon-Project/physioFlow/issues](https://github.com/ML-Carbon-Project/physioFlow/issues).*
