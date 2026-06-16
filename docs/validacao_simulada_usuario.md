# Validação por sessão simulada de usuário — Biologia + Agro

Este documento registra uma **sessão completa simulando um usuário** da plataforma
PhysioFlow, executada de forma *headless* contra as **mesmas funções que as páginas
do Streamlit chamam** (`load_uploaded_file`, `fit_experimental_anova`,
`fit_split_plot`, `compare_means`, `correlation_analysis`, `fit_dose_response`,
`build_model_pipeline`). Os resultados são então comparados com o que já existe
publicado (Kaggle, livros de estatística experimental, R/`nlme`, literatura do
Palmer Penguins).

Complementa o `validacao_externa.md`: aquele foca o motor de **estatística
experimental**; este adiciona a validação externa do **módulo de Machine
Learning** (classificação + regressão), até então sem comparação publicada.

## Metodologia

- Dois datasets de domínio público: **um de biologia** (Palmer Penguins) e
  **um de agronomia** (Yates Oats 1935).
- Parâmetros idênticos aos *defaults* da UI: holdout 30%, validação cruzada
  5-fold, `random_state=42`, `StandardScaler` para os modelos sensíveis a escala,
  `StratifiedKFold` na classificação.
- Reprodutível: `data/sample/test/` + `tests/test_sample_datasets.py` e
  `tests/test_ml_classification.py`.

---

## A. Biologia — Palmer Penguins (`penguins.csv`, 344×7, 3 espécies)

### A.1 EDA / Estatística

| Análise | PhysioFlow | Publicado | Confere |
|---|---|---|---|
| Pearson flipper × massa | **0,871** | ~0,87 | ✅ |
| Pearson bill_depth × massa | **−0,472** | negativo (paradoxo de Simpson) | ✅ |
| ANOVA massa ~ espécie | p ≈ 3×10⁻⁸², n=342, CV 11,0% | F(2,339) sig., p<0,001 | ✅ |
| Tukey HSD massa | Gentoo **a** (5076 g); Chinstrap **b** (3733); Adelie **b** (3701) | Gentoo isolado e mais pesado; Adelie ≈ Chinstrap | ✅ |

### A.2 ML — Classificação de espécie (n=334; holdout 30%; CV 5-fold estratificada)

| Modelo | Acurácia (holdout) | F1-macro | CV acurácia |
|---|---|---|---|
| Random Forest | **1,000** | 1,000 | 0,994 ± 0,007 |
| SVM | **1,000** | 1,000 | 0,994 ± 0,012 |
| KNN | **1,000** | 1,000 | 0,994 ± 0,007 |
| Regressão Logística | 0,990 | 0,988 | 0,994 ± 0,012 |
| Gradient Boosting (Hist) | 0,990 | 0,988 | 0,988 ± 0,006 |
| Árvore de Decisão | 0,980 | 0,983 | 0,967 ± 0,022 |
| Naive Bayes | 0,663 | 0,632 | 0,769 ± 0,065 |

**Comparação com Kaggle/publicado:** notebooks de referência reportam acurácia
**mediana ≥ 0,95**, com os modelos fortes (RF/SVM/logística) em **0,97–1,00**;
um notebook mais simples reporta ~0,905. Os 6 modelos fortes do PhysioFlow caem
exatamente nessa faixa de topo. ✅

O **Naive Bayes (0,66)** é o único fora da curva — esperado: o GaussianNB assume
independência entre features, premissa violada pelas medidas morfométricas
correlacionadas + one-hot de `island`/`sex`. É o baseline fraco conhecido, não um
defeito da ferramenta.

### A.3 ML — Regressão de massa corporal (n=334; alvo `body_mass_g`)

| Modelo | R² (holdout) | MAE | CV R² |
|---|---|---|---|
| Regressão Linear | **0,893** | 200 g | 0,866 |
| Gradient Boosting (Hist) | 0,867 | 235 g | 0,854 |
| Random Forest | 0,865 | 234 g | 0,856 |
| KNN | 0,860 | 228 g | 0,843 |
| Árvore de Decisão | 0,774 | 291 g | 0,734 |

**Comparação com publicado:** o modelo de **um preditor** (flipper) tem
R² ≈ 0,871² ≈ **0,76**; modelos **multipreditor** (flipper + espécie + sexo)
publicados ficam em **~0,85–0,87**. O CV R² da Regressão Linear do PhysioFlow
(**0,866**) reproduz a referência multipreditor. ✅

---

## B. Agronomia — Yates Oats 1935 (`OATS.csv`, 72×5) — split-plot

3 variedades × 4 doses de N × 6 blocos. Exemplo canônico de parcelas subdivididas,
com ANOVA publicada em livros de modelos mistos e no `nlme::Oats` do R.

### B.1 ANOVA split-plot

| Termo | Estrato | PhysioFlow | Publicado (Yates / `nlme`) | Confere |
|---|---|---|---|---|
| Variety (parcela) | Erro(a), gl 10 | F(2,10) = **1,485**, p = 0,272 | 1,485, p = 0,272 | ✅ |
| nitro (subparcela) | Erro(b), gl 45 | F(3,45) = **37,686**, p < 10⁻¹¹ | 37,686, p < 0,001 | ✅ |
| Variety × nitro | Erro(b), gl 45 | F(6,45) = **0,303**, p = 0,932 | 0,303, p = 0,932 | ✅ |

CV(a) = 23,59%, CV(b) = 12,80%. **Coincidência decimal** nos três F-valores.

### B.2 Resposta à dose de N (análises agronômicas)

| Análise | PhysioFlow | Interpretação |
|---|---|---|
| ANOVA `yield ~ nitro` (DBC) | p = 4,2×10⁻¹¹ | resposta ao N altamente significativa |
| Tukey nas doses | 0,6 **a** (123,4) · 0,4 **a** (114,2) · 0,2 **b** (98,9) · 0,0 **c** (79,4) | resposta dose-dependente clássica, com saturação entre 0,4 e 0,6 |
| Dose-resposta quadrática `yield ~ nitro` | R² = 0,385 | N sozinho explica ~38% (variedade e bloco respondem pelo resto) |

### B.3 ML — Regressão de produtividade (n=72; alvo `yield`; features Variety+nitro+Block)

| Modelo | R² (holdout) | CV R² |
|---|---|---|
| Random Forest | 0,393 | 0,540 |
| Regressão Linear | 0,382 | **0,582** |
| KNN | 0,189 | 0,405 |
| Gradient Boosting (Hist) | 0,023 | 0,204 |
| Árvore de Decisão | −0,117 | 0,084 |

**Leitura honesta:** desempenho modesto — esperado, e **concordante com a
estatística**. Com apenas 72 observações e a variância de produtividade dominada
por bloco + dose de N (o split-plot mostra Variety não-significativa), não há sinal
suficiente para o ML brilhar. O ML aqui **confirma** a conclusão experimental
(o N manda; a variedade pouco), em vez de superá-la. Não há benchmark de Kaggle
direto para este dataset clássico — a referência é a literatura de modelos mistos.

---

## C. Conclusão consolidada

| Domínio | Módulo | Veredito |
|---|---|---|
| Biologia (penguins) | EDA/ANOVA/Tukey/correlação | reproduz a literatura ✅ |
| Biologia (penguins) | **ML classificação** | iguala o **topo do Kaggle** (0,97–1,00) ✅ |
| Biologia (penguins) | **ML regressão** | reproduz R² multipreditor publicado (~0,87) ✅ |
| Agro (oats) | split-plot | **coincidência decimal** com Yates/`nlme` ✅ |
| Agro (oats) | dose-resposta/Tukey | resposta a N clássica e significativa ✅ |
| Agro (oats) | ML regressão | modesto, mas **coerente** com a estatística (N domina) ✅ |

Os números do PhysioFlow batem com as referências publicadas em todos os casos
com referência forte. O único resultado "baixo" (Naive Bayes em penguins) é o
comportamento esperado do algoritmo, e o ML fraco em oats é fidedigno ao tamanho
e à estrutura do experimento — não falhas da ferramenta.

## Como reexecutar

```bash
pytest tests/test_sample_datasets.py tests/test_ml_classification.py -v
```

## Fontes

- Penguins — classificação (Kaggle/RF): https://www.kaggle.com/code/brsahan/penguins-species-classification-with-random-forest
- Penguins — regressão multipreditor (Cornell INFO 2950): https://info2950.infosci.cornell.edu/ae/ae-14-palmerpenguins-A.html
- Penguins — regressão single-predictor (STA 199, Duke): https://sta199-f22-1.github.io/ae/ae-13-palmerpenguins-A.html
- Yates Oats / split-plot — `nlme::Oats` (Pinheiro & Bates) e Yates (1935), reproduzido em `validacao_externa.md` §3
- Palmer Penguins — Gorman, Williams & Fraser (2014), Palmer Station LTER
