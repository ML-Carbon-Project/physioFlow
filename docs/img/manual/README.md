# Screenshots do manual de operação

Este diretório armazena as capturas de tela referenciadas em [`docs/manual.pt.md`](../../manual.pt.md).

## Convenções

* **Formato:** PNG (preserva nitidez dos rótulos e dataframes).
* **Resolução:** capture com a janela do navegador em ~1280 × 720 (modo desktop "normal", sem zoom). Streamlit responsivo já dá boa leitura nesse tamanho.
* **Dataset:** sempre usar `data/sample/0_Dados_Fisiologia_RIO VERDE.xlsx` carregado, para que os exemplos sejam reproduzíveis.
* **Idioma:** capturar com a interface em **Português** (seletor da sidebar = "Português").
* **Nomenclatura:** `NN_pagina_acao.png`, onde `NN` é uma ordem global no manual (01, 02, …, 99). Exemplos:
  * `01_upload_inicial.png` — tela de boas-vindas
  * `04_pipeline_relatorio.png` — relatório de etapas do pipeline
  * `07_eda_confundimento.png` — painel de confundimento na aba Qualidade

## Lista canônica de prints requeridos pelo manual

A ordem abaixo segue os capítulos de `manual.pt.md`. Cada item indica:
1. nome do arquivo;
2. página/aba do app;
3. ação a executar antes de capturar.

### Capítulo 2 — Instalação

| Arquivo | Tela | Ação |
|---|---|---|
| `01_terminal_streamlit_run.png` | Terminal | Print da saída de `python -m streamlit run app.py` (até a linha "Local URL: http://localhost:8501"). |
| `02_app_primeira_tela.png` | Browser, página Upload | App recém-aberto, sem nenhum arquivo carregado. Sidebar visível. |

### Capítulo 3 — Carregando seus dados

| Arquivo | Tela | Ação |
|---|---|---|
| `03_upload_arquivo_carregado.png` | Upload | Após escolher `0_Dados_Fisiologia_RIO VERDE.xlsx` e clicar em "Carregar". Mostrar as duas métricas (linhas, colunas) + tela do schema. |
| `04_upload_schema_resumo.png` | Upload, painel "Validação do schema" | Capturar APENAS o painel do schema (métricas obrigatórias/recomendadas/opcionais + warnings de "vazia"). |
| `05_upload_schema_tabela.png` | Upload, schema expandido | Clicar no expander "Detalhes do schema" e capturar a tabela completa. |

### Capítulo 4 — Pipeline

| Arquivo | Tela | Ação |
|---|---|---|
| `06_pipeline_dropdown_replicas.png` | Pipeline e Processamento | Abrir o dropdown "Alterar Tratamento de Réplicas" mostrando as 6 opções. |
| `07_pipeline_warning_descarte.png` | Pipeline e Processamento | Após rodar com `media`, capturar o `st.warning` amarelo de "Pipeline removeu 94,9% das linhas" + o `st.warning` de etapa específica. |
| `08_pipeline_relatorio_etapas.png` | Pipeline | A tabela "Relatório de etapas" com as 4 etapas. |
| `09_pipeline_mediana_caption.png` | Pipeline | Selecionar "Mediana das Réplicas" no dropdown; capturar a caption explicativa logo abaixo do select. |

### Capítulo 5 — Filtros globais

| Arquivo | Tela | Ação |
|---|---|---|
| `10_eda_filtros_globais.png` | EDA, painel "Filtros Globais" expandido | Mostrar todos os 6 filtros (Réplicas, Cultura, Município, Fazenda, Época, Datas). |

### Capítulo 6 — EDA

| Arquivo | Tela | Ação |
|---|---|---|
| `11_eda_resumo_estatistico.png` | EDA, aba "Resumo" | Tabela de describe expandida. |
| `12_eda_qualidade_metrics.png` | EDA, aba "Qualidade" | Métricas (linhas, colunas) + barras de missing. |
| `13_eda_qualidade_confounding.png` | EDA, aba "Qualidade", seção "Confundimento" | Tabela mostrando Fazenda ⟷ Cultura redundantes + warning amarelo. |
| `14_eda_correlacao_spearman.png` | EDA, aba "Correlação" | Heatmap com Spearman selecionado. |
| `15_eda_normalidade_tabela.png` | EDA, aba "Inferência" → seção "Normalidade" | A tabela com Shapiro/Anderson/D'Agostino. |
| `16_eda_normalidade_qqplots.png` | EDA, aba "Inferência" | Grade de Q-Q plots logo abaixo. |
| `17_eda_vif_painel.png` | EDA, aba "Inferência" → VIF | Tabela VIF + caption sobre variáveis derivadas. |
| `18_eda_kruskal_min_n.png` | EDA, aba "Inferência" → KW | Slider "N mínimo por grupo" + tabela com coluna `dropped_levels`. |
| `19_eda_outliers_assumptions.png` | EDA, aba "Outliers" | Capturar a caption nova de pressupostos + métricas e gráfico. |

### Capítulo 8 — Modelagem

| Arquivo | Tela | Ação |
|---|---|---|
| `20_modelagem_groupkfold.png` | Modelagem | Radio "Estratégia de CV" = GroupKFold, selectbox visível em "Fazenda + Ponto", tabela de resultados. |

### Capítulo 9 — Espacial

| Arquivo | Tela | Ação |
|---|---|---|
| `21_espacial_idw.png` | Análise Espacial, aba IDW | Mapa IDW de uma variável (ex. `A`). |
| `22_espacial_moran.png` | Análise Espacial, aba Moran | Mapa LISA + métrica I=0,xx e gráfico de dispersão de Moran. |
| `23_espacial_variograma_metros.png` | Análise Espacial, aba Kriging | Variograma com eixo "Distância h (m)" + caption EPSG. |

### Capítulo 10 — Série temporal

| Arquivo | Tela | Ação |
|---|---|---|
| `24_temporal_stl_bloqueado.png` | Série Temporal → STL | Mostrar o aviso "Apenas 3 datas com medição real (mínimo 10)". |

### Capítulo 11 — Comparativa

| Arquivo | Tela | Ação |
|---|---|---|
| `25_comparativa_setup.png` | Comparativa | Setup dos grupos (Cultura = Soja vs. Cana) + métrica de N por grupo. |
| `26_comparativa_mannwhitney.png` | Comparativa, aba Resumo | Tabela de Mann-Whitney com p-values. |

## Captura prática

No macOS: `Cmd + Shift + 4`, depois `Space` para capturar uma janela inteira, ou arraste para selecionar uma região. Salve em `docs/img/manual/` com o nome correto.
