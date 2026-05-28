# PhysioFlow — Plataforma de Análise de Fisiologia Vegetal

> Uma plataforma web open-source interativa para análise exploratória de dados, modelagem espacial e aprendizado de máquina para parâmetros ecofisiológicos de culturas agrícolas (soja e cana-de-açúcar). Desenvolvida no âmbito do **Projeto Goiás Verde**.

[English](./README.md) | [Português](./README.pt.md) | [Español](./README.es.md)

**Versão:** 1.0  
**Iniciativa:** Projeto Goiás Verde (*Instituto Federal Goiano – Campus Rio Verde* & *Centro de Excelência em Agricultura Exponencial – CEAGRE*)

---

> ### 📖 [**Manual de Operação do Sistema →**](./docs/manual.pt.md)
>
> Guia completo passo a passo: instalação, carga de dados, pipeline de limpeza, EDA, modelagem, análise espacial, série temporal, comparação por grupos, glossário estatístico e FAQ. **15 capítulos, 26 capturas de tela.**

---

## 📋 Visão Geral

Este repositório contém a aplicação Streamlit desenvolvida para consolidar o fluxo de tratamento, análise descritiva, modelagem preditiva e geoespacial de dados de **Fisiologia Vegetal**. O aplicativo valida planilhas de campo contendo dados coletados por analisadores de fotossíntese (IRGA), clorofilômetros e ceptômetros, aplicando um pipeline automatizado de limpeza e análise avançada.

A ferramenta é agnóstica em termos de arquivos, desde que as colunas da planilha correspondam ao dicionário de dados (ex: fotossíntese `A`, transpiração `E`, condutância estomática `gs`, clorofilas, `IAF`, etc.).

---

## 🛠️ Funcionalidades Principais

1.  **Carga & Validação de Schema** — Ingestão de arquivos Excel (`.xlsx`, `.xls`) ou CSV com validação instantânea contra o schema de 31 colunas fisiológicas organizadas por níveis de importância (*Obrigatórias*, *Recomendadas*, *Opcionais*). Realiza verificação de tipos e validação de limites geográficos.
2.  **Pipeline de Limpeza** — Aplicação transparente de filtros reativos: remoção de variáveis indesejadas, descarte de registros sem metadados obrigatórios, eliminação de pontos de grade vazios e **5 modos de tratamento de réplicas** (média aritmética das réplicas, desdobramento das réplicas em linhas independentes via `melt`, ou seleção de réplicas específicas).
3.  **Análise Exploratória (EDA)** — Estatística descritiva completa, qualidade de preenchimento (dados ausentes), histogramas, boxplots dinâmicos, matriz de correlação (Pearson, Spearman e Kendall), distribuição de categorias, testes de normalidade (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), multicolinearidade (VIF), rankings de hotspots e auditoria de outliers usando consenso de 5 métodos de Machine Learning.
4.  **Regressão** — Ajuste de modelos de regressão bivariada com presets comuns na fisiologia vegetal (ex.: *gs vs. A*, *Ci vs. A*, *gs vs. E*) com suporte a intervalos de confiança e facetamento.
5.  **Modelagem Preditiva** — Treinamento e comparação de modelos de Machine Learning (Regressão Linear, Random Forest, Gradient Boosting, Decision Tree, KNN) para estimar a taxa fotossintética `A` com base nos demais parâmetros, com métricas de validação cruzada, holdout e gráficos de importância de features.
6.  **Análise Espacial** — Interpolação por Inverso da Distância (IDW), autocorrelação espacial por Moran's I global e LISA local (mapas de clusters significativos), estatísticas Getis-Ord Gi*, agregação em grade UTM regular, interpolação por Krigagem ordinária com semivariograma esférico e mapa de pontos plotado sobre os limites geográficos de Rio Verde, GO (via biblioteca `geobr`).
7.  **Série Temporal** — Agregação diária e decomposição de séries temporais STL (Tendência, Sazonalidade e Resíduos).
8.  **Comparação por Grupos** — Testes estatísticos de Mann-Whitney U, regressão log-linear por grupo e comportamento horário cumulativo.

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
│   ├── schema.py               # Validador de colunas e limites
│   ├── pipeline.py             # Algoritmo de limpeza e réplicas
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
