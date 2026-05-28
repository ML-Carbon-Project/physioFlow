<!-- markdownlint-disable MD013 MD033 -->

# PhysioFlow — System Operation Manual

> Manual version: 1.0 (aligned with application 1.x)
> Reference language: English. Mirrored at [`manual.pt.md`](manual.pt.md) (Portuguese, canonical) and [`manual.es.md`](manual.es.md) (Spanish).

---

## Extended Abstract

**PhysioFlow** is an open-source, interactive web application built on Streamlit for the end-to-end processing, exploration, modelling and visualisation of **ecophysiological field datasets** — measurements collected by infrared gas analysers (IRGA), chlorophyll meters and ceptometers in commercial crops, with the canonical use case being soybean and sugarcane experiments in the Brazilian Cerrado.

The platform bundles a **strict declarative schema** with three severity tiers (required / recommended / optional) covering 31 reference columns, a deterministic four-step cleaning pipeline, and six interchangeable replicate-handling modes (mean, median, unfold, replicate-1/2/3-only). Replicate consolidation produces stable downstream column names (`Chl_a_media`, `Chl_b_media`, `IAF_media`) regardless of the selected mode, so user-defined filters and models remain compatible.

A twelve-tab Exploratory Data Analysis (EDA) module covers descriptive statistics with skewness/kurtosis, missing-value audits, **categorical confounding detection via Cramér's V** (a feature seldom integrated into ecophysiology software), pairwise correlations in Pearson/Spearman/Kendall, distribution diagnostics with **paired Q-Q plots and normality tests** (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), **Variance Inflation Factor with explicit awareness of mathematically derived variables** (Ci/Ca, A/Ci, EUA = A/E, ETR from YII), Kruskal-Wallis with a **minimum-group-size filter** to prevent unreliable p-values on small subsets, and outlier consensus across five algorithms (Z-score, IQR, Isolation Forest, LOF, Elliptic Envelope) with explicit assumption captions.

Predictive modelling supports five regressors (Linear, Random Forest, Gradient Boosting, Decision Tree, KNN) with **optional GroupKFold cross-validation** that mitigates the pseudoreplication leak common to field datasets — automatically downscaling the number of folds when the chosen grouping column has fewer levels than the requested CV depth. Geospatial analyses (IDW, Moran's I, LISA, Getis-Ord Gi*, UTM grid aggregation, ordinary kriging with spherical semivariogram) run **internally in UTM metres** with dynamic EPSG selection by longitude/hemisphere, eliminating the anisotropic distortion that emerges when computing Euclidean distances on raw lat/lon. Time-series decomposition (STL) is **blocked when fewer than ten observation dates exist** or when more than 70 % of the series is interpolated — guard-rails that prevent the common pitfall of "publishable looking" decompositions on sparse field campaigns. A pairwise group comparison page exposes Mann-Whitney U, log-linear regression per group, and hourly cumulative patterns.

The application is **trilingual** (Portuguese, English, Spanish) with full i18n parity, ships with 47 unit tests (57 % coverage), continuous integration (lint + types + tests), and is distributed under GPL-2.0-or-later. The companion 15-chapter user manual (this document and its Portuguese counterpart) is rendered as Markdown in-repo and as PDF via a pandoc + XeLaTeX pipeline that produces release artifacts on every tagged version. A reference dataset from a Goiás Verde sugarcane/soybean campaign in Rio Verde, Goiás (Brazil) ships with the application and is used throughout this manual to illustrate every feature with reproducible numerical examples.

---

## Table of contents

1. [Introduction](#1-introduction)
2. Installation and first run
3. Loading your data
4. Cleaning pipeline
5. Global filters
6. Exploratory Data Analysis (EDA)
7. Bivariate regression
8. Predictive modelling
9. Spatial analysis
10. Time series
11. Group comparison
12. Statistical glossary
13. Troubleshooting (FAQ)
14. References
15. Contributing

---

## 1. Introduction

### 1.1 Who this manual is for

This manual targets **researchers, postgraduate students and field technicians** who will use the *PhysioFlow* application to analyse ecophysiological data collected in the field (IRGA, chlorophyll meter and ceptometer measurements). It assumes neither prior Streamlit experience nor Python programming background; it does assume basic familiarity with plant-physiology terms (`A` for net photosynthesis, `gs` for stomatal conductance, `Ci` for intercellular CO₂, leaf area index, chlorophyll a/b).

### 1.2 What the application does

In one sentence: **validates, cleans, explores and models** field spreadsheets of crop ecophysiology, with additional support for **spatial** analyses (over the municipality of Rio Verde, Goiás, Brazil) and **temporal** analyses. The default workflow is Upload → Pipeline → EDA → Regression / Modelling / Spatial / Temporal / Comparative. All analysis pages operate on the same session dataset and respect the global filters applied in the sidebar.

### 1.3 Typographic conventions

* `File/paths` and `code` appear in `monospace`.
* **Bold** marks interface elements (buttons, tabs, selector labels).
* *Italic* marks technical terms at first occurrence — each has an entry in the [Glossary](#12-statistical-glossary).
* `>` introduces an action instruction ("> click **Upload**").
* Screenshots use the bundled sample dataset `data/sample/0_Dados_Fisiologia_RIO VERDE.xlsx`.

### 1.4 Suggested reading paths

Different audiences benefit from different entry points:

| If you are… | Read in this order |
|---|---|
| A field technician about to upload a new dataset | Ch. 2 → Ch. 3 → Ch. 4 → glance at Ch. 13 (FAQ). |
| A graduate student running the standard analyses | Ch. 2 → Ch. 3 → Ch. 4 → Ch. 6 (EDA, in full) → the analysis chapter you need. |
| A senior researcher reviewing methodology | Ch. 6 → Ch. 8 (GroupKFold) → Ch. 9 (UTM projection, kriging) → Ch. 11 (pairwise comparison). |
| A peer reviewer or replicator | The Extended Abstract → Ch. 12 (Glossary) → Ch. 14 (References). |
| A contributor to the codebase | This manual → [`docs/architecture.md`](architecture.md) → [`docs/contributing.md`](contributing.md). |

### 1.5 What this manual does *not* cover

* Statistical theory beyond brief operational definitions — the [Glossary](#12-statistical-glossary) gives 2–3 line summaries; the [References](#14-references) point to primary literature.
* Field-collection protocols (how to use the IRGA, chlorophyll meter or ceptometer) — those belong to the instrument manufacturer manuals.
* Custom analyses not exposed in the UI — for those, export the processed dataset (Ch. 4) and use external tools.

---

## 2. Installation and first run

*Translation pending. See the canonical Portuguese version at [`manual.pt.md` §2](manual.pt.md#2-instalação-e-primeira-execução).*

## 3. Loading your data

*Translation pending. See [`manual.pt.md` §3](manual.pt.md#3-carregando-seus-dados).*

## 4. Cleaning pipeline

*Translation pending. See [`manual.pt.md` §4](manual.pt.md#4-pipeline-de-limpeza).*

## 5. Global filters

*Translation pending. See [`manual.pt.md` §5](manual.pt.md#5-filtros-globais).*

## 6. Exploratory Data Analysis (EDA)

*Translation pending. See [`manual.pt.md` §6](manual.pt.md#6-análise-exploratória-eda).*

## 7. Bivariate regression

*Translation pending. See [`manual.pt.md` §7](manual.pt.md#7-regressão-bivariada).*

## 8. Predictive modelling

*Translation pending. See [`manual.pt.md` §8](manual.pt.md#8-modelagem-preditiva).*

## 9. Spatial analysis

*Translation pending. See [`manual.pt.md` §9](manual.pt.md#9-análise-espacial).*

## 10. Time series

*Translation pending. See [`manual.pt.md` §10](manual.pt.md#10-série-temporal).*

## 11. Group comparison

*Translation pending. See [`manual.pt.md` §11](manual.pt.md#11-comparação-por-grupos).*

## 12. Statistical glossary

*Translation pending. See [`manual.pt.md` §12](manual.pt.md#12-glossário-estatístico).*

## 13. Troubleshooting (FAQ)

*Translation pending. See [`manual.pt.md` §13](manual.pt.md#13-solução-de-problemas-faq).*

## 14. References

*Identical bibliography to the Portuguese edition — see [`manual.pt.md` §14](manual.pt.md#14-referências).*

## 15. Contributing

Found a bug, have a feature request, or want to add a new analysis?

* **Bug reports and feature requests:** open an issue on the project GitHub repository.
* **Code or documentation contributions:** see [`docs/contributing.md`](contributing.md) for the PR workflow, testing standards, and how to add languages.
* **Build this manual as PDF:** run `scripts/build_manual_pdf.sh --lang en`. See [`manual.pt.md` §15.3](manual.pt.md#153-gerando-este-manual-em-pdf) for prerequisites.

---

*End of manual. Version 1.0 — aligned with application 1.x.*
