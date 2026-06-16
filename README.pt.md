# PhysioFlow — Plataforma de Análise de Fisiologia Vegetal

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://physioflow.streamlit.app/)

> Uma plataforma web open-source interativa para análise exploratória de dados, modelagem espacial e aprendizado de máquina para parâmetros ecofisiológicos de culturas agrícolas (soja e cana-de-açúcar). Desenvolvida no âmbito do **Projeto Goiás Verde**.

> ### 🌐 [**Demonstração ao vivo →**](https://physioflow.streamlit.app/)
>
> Aplicação publicada no Streamlit Community Cloud. Acesso protegido por login Supabase — solicite credenciais ao mantenedor.

[English](./README.md) | [Português](./README.pt.md) | [Español](./README.es.md)

**Versão:** 1.0  
**Iniciativa:** Projeto Goiás Verde (*Instituto Federal Goiano – Campus Rio Verde* & *Centro de Excelência em Agricultura Exponencial – CEAGRE*)

---

> ### 📖 [**Manual de Operação do Sistema →**](./docs/manual.pt.md)
>
> Guia completo passo a passo: instalação, carga de dados, pipeline de limpeza, EDA, modelagem, análise espacial, série temporal, comparação por grupos, estatística experimental, glossário estatístico e FAQ. **16 capítulos, 26 capturas de tela.**

---

## 📋 Visão Geral

Este repositório contém a aplicação Streamlit desenvolvida para consolidar o fluxo de tratamento, análise descritiva, modelagem preditiva e geoespacial de dados de **Fisiologia Vegetal**. O aplicativo valida planilhas de campo contendo dados coletados por analisadores de fotossíntese (IRGA), clorofilômetros e ceptômetros, aplicando um pipeline automatizado de limpeza e análise avançada.

A ferramenta é agnóstica em termos de arquivos, desde que as colunas da planilha correspondam ao dicionário de dados (ex: fotossíntese `A`, transpiração `E`, condutância estomática `gs`, clorofilas, `IAF`, etc.).

---

## 🛠️ Funcionalidades Principais

1.  **Carga & Perfil de Dados** — Ingestão de arquivos Excel (`.xlsx`, `.xls`), CSV ou TXT/TSV com seletor de delimitador. Um **perfil de dados** automático (Fisiologia / Genérico) adapta toda a interface: datasets de fisiologia são validados contra o schema de 31 colunas (níveis *Obrigatórias / Recomendadas / Opcionais*, verificação de tipos e de limites geográficos); qualquer outro dataset recebe um resumo neutro, sem premissas de fisiologia.
2.  **Pipeline de Limpeza** — Limpeza reativa e transparente. No **perfil de fisiologia**: remoção de variáveis, descarte de registros sem metadados obrigatórios, eliminação de pontos de grade vazios e **5 modos de tratamento de réplicas** (média, mediana, desdobramento via `melt`, ou seleção de réplica). No **perfil genérico**: passa-direto, com agregação opcional de repetições por média/mediana.
3.  **Análise Exploratória (EDA)** — Estatística descritiva completa, qualidade de preenchimento (dados ausentes), histogramas, boxplots dinâmicos, matriz de correlação (Pearson, Spearman e Kendall), distribuição de categorias, testes de normalidade (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), multicolinearidade (VIF), rankings de hotspots e auditoria de outliers usando consenso de 5 métodos de Machine Learning.
4.  **Regressão** — Ajuste de modelos de regressão bivariada com presets comuns na fisiologia vegetal (ex.: *gs vs. A*, *Ci vs. A*, *gs vs. E*) com suporte a intervalos de confiança e facetamento.
5.  **Modelagem Preditiva (Regressão & Classificação)** — Treinamento e comparação de modelos `scikit-learn` com validação cruzada, holdout e gráficos de importância. **Regressão** (Linear, Ridge, Random Forest, Gradient Boosting, HistGradientBoosting, Árvore de Decisão, KNN) e **Classificação** (Logística, Random Forest, Árvore, Gradient Boosting, HistGradientBoosting, KNN, SVM, Naive Bayes) com acurácia/F1/precisão/revocação, matriz de confusão, GroupKFold opcional e escalonamento.
6.  **Estatística Experimental (delineamentos)** — ANOVA orientada ao delineamento para DIC, DBC, Quadrado Latino, fatorial (2–3 fatores), parcelas subdivididas, faixas e hierárquico; testes de pressupostos (Shapiro–Wilk, Levene) com QQ-plots; comparação de médias (Tukey, Scott-Knott, Duncan, Scheffé, LSD, Dunnett vs. controle); ANCOVA; regressão de doses/polinomial; correlação (Pearson, Spearman, parcial). Exporta script Python reprodutível. **Validada número a número contra o R** (`aov`, `car::Anova`, `emmeans`, `ScottKnott`) — ver [`docs/validacao_externa.md`](./docs/validacao_externa.md).
7.  **Análise Espacial** — Interpolação por Inverso da Distância (IDW), autocorrelação espacial por Moran's I global e LISA local (mapas de clusters significativos), estatísticas Getis-Ord Gi*, agregação em grade UTM regular, interpolação por Krigagem ordinária com semivariograma esférico e mapa de pontos opcional sobre os limites de Rio Verde, GO (via biblioteca `geobr`, instalada localmente).
8.  **Série Temporal** — Agregação diária e decomposição de séries temporais STL (Tendência, Sazonalidade e Resíduos).
9.  **Comparação por Grupos** — Testes estatísticos de Mann-Whitney U, regressão log-linear por grupo e comportamento horário cumulativo.

---

## 📂 Estrutura do Projeto

```
fisiologia-streamlit/
├── app.py                      # Ponto de entrada do aplicativo
├── requirements.txt            # Dependências de produção
├── pyproject.toml              # Configurações do pytest
├── src/
│   ├── auth.py                 # Integração de Login (Supabase)
│   ├── state.py                # Gerenciamento de estado em sessão
│   ├── schema.py               # Validador de colunas, limites e detecção de perfil
│   ├── profile.py              # Resolução do perfil de dados (Fisiologia / Genérico)
│   ├── pipeline.py             # Algoritmo de limpeza e réplicas
│   ├── stats_utils.py          # Motor de delineamentos (ANOVA, testes, designs)
│   ├── components/             # Componentes visuais (Sidebar, Filtros Globais)
│   │   ├── sidebar.py
│   │   └── filters.py
│   ├── config/
│   │   └── settings.py         # Configuração de estilos (CSS) e variáveis padrão
│   ├── i18n/                   # Internacionalização (PT, EN, ES)
│   └── pages/                  # Módulos de interface de cada aba
├── tests/                      # Testes automatizados (pytest)
└── docs/                       # Documentação (Arquitetura, Dicionário de dados)
```

---

## 🚀 Como Executar Localmente

### 1. Criar e Ativar Ambiente Virtual
```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2. Instalar Dependências
```bash
pip install -U pip wheel
pip install -r requirements.txt
```

### 3. Rodar o Streamlit
```bash
python -m streamlit run app.py
```
O aplicativo abrirá no seu navegador padrão no endereço `http://localhost:8501`.

---

## 🧪 Executando os Testes Unitários

A suíte de testes valida a integridade do pipeline de dados e as regras de validação do schema:
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```

---

## 👥 Apoio e Patrocínio

Este projeto foi desenvolvido com suporte e incentivo do CNPq, CAPES, FAPEG, do Instituto Federal Goiano (IF Goiano – Campus Rio Verde) e do Centro de Excelência em Agricultura Exponencial (CEAGRE).
