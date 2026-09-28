# PhysioFlow — Crop Physiology Data Analysis Platform

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://physioflow.streamlit.app/)

> An open-source interactive web platform for exploratory data analysis, spatial modeling, and machine learning of crop ecophysiological parameters (soybean and sugarcane). Built within the **Goiás Verde Project**.

> ### 🌐 [**Live demo →**](https://physioflow.streamlit.app/)
>
> Deployed on Streamlit Community Cloud. Login-protected via Supabase — request credentials from the maintainer.

[English](./README.md) | [Português](./README.pt.md) | [Español](./README.es.md)

**Version:** 1.0  
**Initiative:** Goiás Verde Project (*Instituto Federal Goiano – Campus Rio Verde* & *Center of Excellence in Exponential Agriculture – CEAGRE*)

---

> ### 📖 [**System Operation Manual →**](./docs/manual.en.md)
>
> End-to-end walkthrough: installation, data upload, cleaning pipeline, EDA, modeling, spatial analysis, time series, group comparison, experimental statistics, statistical glossary, and FAQ. **16 chapters, 26 screenshots.**
> *Available in English, Portuguese ([`manual.pt.md`](./docs/manual.pt.md)) and Spanish ([`manual.es.md`](./docs/manual.es.md)).*

---

## 📋 Overview

This repository contains the Streamlit application developed to consolidate the cleaning, descriptive analysis, predictive modeling, and geospatial modeling workflow of **Crop Physiology** field datasets. The application validates data collected by photosynthesis systems (IRGA), chlorophyll meters, and ceptometers, applying an automated pipeline for cleaning and advanced analysis.

The tool is dataset-agnostic, provided the spreadsheet columns map correctly to the expected variables (e.g., photosynthesis rate `A`, transpiration `E`, stomatal conductance `gs`, chlorophylls, leaf area index `LAI/IAF`, etc.).

---

## 🛠️ Main Features

1.  **Ingestion & Data Profile** — Ingestion of Excel (`.xlsx`, `.xls`), CSV, or TXT/TSV files with a delimiter selector. An automatic **data profile** (Physiology / Generic) adapts the whole interface: physiology datasets are validated against a 31-column schema (priority tiers *Required / Recommended / Optional*, type coercion and coordinate-range checks); any other dataset gets a neutral summary, with no physiology-specific assumptions.
2.  **Cleaning Pipeline** — Transparent, reactive cleaning. In the **physiology profile**: column removal, dropping records without essential metadata, removing empty grid points, and **5 modes of replicate treatment** (mean, median, replicate expansion via `melt`, or single replicate). In the **generic profile**: pass-through with optional repetition aggregation by mean/median.
3.  **Exploratory Data Analysis (EDA)** — Complete descriptive statistics, data completeness checks, histograms, boxplots, correlation heatmaps (Pearson, Spearman, Kendall), category composition, normality tests (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), multicollinearity (VIF), hotspot rankings, and a multi-method outlier consensus audit.
4.  **Regression** — Bivariate regression fitting with presets tailored for crop physiology (e.g., *gs vs. A*, *Ci vs. A*, *gs vs. E*) with support for confidence intervals and faceting.
5.  **Predictive Modeling (Regression & Classification)** — Training and comparison of `scikit-learn` models with cross-validation, holdout metrics, and feature-importance charts. **Regression** (Linear, Random Forest, HistGradientBoosting, Decision Tree, KNN) and **Classification** (Logistic, Random Forest, Decision Tree, Gradient Boosting, HistGradientBoosting, KNN, SVM, Naive Bayes) with accuracy/F1/precision/recall, confusion matrix, optional GroupKFold and feature scaling.
6.  **Experimental Statistics (designs)** — Design-aware ANOVA for CRD, RCBD, Latin square, factorial (2–3 factors), split-plot, strip-plot and nested designs; assumption tests (Shapiro–Wilk, Levene) with Q–Q plots; mean-comparison procedures (Tukey, Scott-Knott, Duncan, Scheffé, LSD, Dunnett vs. control); ANCOVA; dose/polynomial regression; correlation (Pearson, Spearman, partial). Exports a reproducible Python script. **Validated number-by-number against R** (`aov`, `car::Anova`, `emmeans`, `ScottKnott`, `agricolae`, `multcomp`) — see [`docs/validacao_externa.md`](./docs/validacao_externa.md).
7.  **Spatial Analysis** — Inverse Distance Weighting (IDW) interpolation, spatial autocorrelation via global Moran's I and local LISA (map of significant clusters), Getis-Ord Gi* hotspots, regular UTM grid cells aggregation, Ordinary Kriging with a fitted spherical variogram model, and an optional point-distribution map overlaid on Rio Verde (GO) municipal boundaries (via the optional `geobr` library, installed locally).
8.  **Time Series** — Daily aggregation and STL time series decomposition (Trend, Seasonal, and Residuals).
9.  **Group Comparison** — Statistical comparisons between groups (e.g., soybean vs. sugarcane) using the Mann-Whitney U test, log-linear regression, and cumulative hourly profiles.

---

## 📂 Project Layout

```
fisiologia-streamlit/
├── app.py                      # Streamlit app entry point
├── requirements.txt            # Production dependencies
├── pyproject.toml              # Pytest configuration
├── src/
│   ├── auth.py                 # Login integration (Supabase)
│   ├── state.py                # Session state helpers
│   ├── schema.py               # Schema specs, ranges, and profile detection
│   ├── profile.py              # Data profile (Physiology / Generic) resolution
│   ├── pipeline.py             # Cleaning and replicates pipeline
│   ├── stats_utils.py          # Experimental-design engine (ANOVA, tests, designs)
│   ├── components/             # Reusable UI components (Sidebar, Top-Filters)
│   │   ├── sidebar.py
│   │   └── filters.py
│   ├── config/
│   │   └── settings.py         # Custom style configurations (CSS) and constants
│   ├── i18n/                   # Translation module (PT, EN, ES)
│   └── pages/                  # Modules rendering individual pages
├── tests/                      # Automated unit tests (pytest)
└── docs/                       # Documentation (Architecture, Data dictionary)
```

---

## 🚀 How to Run Locally

**Quickstart (copy-paste):**

```bash
git clone https://github.com/ML-Carbon-Project/physioFlow.git
cd physioFlow
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -U pip wheel && pip install -r requirements.txt
python -m streamlit run app.py                       # opens http://localhost:8501
```

The step-by-step version follows.

### 1. Create and Activate Virtual Environment
```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -U pip wheel
pip install -r requirements.txt
```

### 3. Run the Streamlit Application
```bash
python -m streamlit run app.py
```
The application will open in your default browser at `http://localhost:8501`.

---

## 🧪 Running Unit Tests

The test suite validates data pipeline transformations and schema validation integrity:
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```

---

## 🔁 Reproduce the paper's results

The two public examples in the *Software Impacts* article (Section 3.2) regenerate from a clean checkout with a single headless command (no interface, no login):

```bash
python reproduce_examples.py
```

Straight from the same `src/` engine the app uses, it prints:

- the **Yates oats split-plot ANOVA** (paper Table 2): variety *F* = 1.485, nitrogen *F* = 37.686, variety × nitrogen *F* = 0.303, matching `nlme::Oats` to the decimal;
- the **Palmer penguins** flipper–body-mass Pearson *r* = 0.871 and species classification (Random Forest, SVM, k-NN at 1.00 holdout and 0.98–0.99 cross-validated accuracy).

The experimental-design engine is additionally cross-validated number-by-number against R (`aov`, `car::Anova` type II, `emmeans`, `ScottKnott`, `agricolae`, `multcomp`); see [`docs/validacao_externa.md`](./docs/validacao_externa.md).

Changes made after v1.0 — the version cited in the Software Impacts article — are listed in [`CHANGELOG.md`](./CHANGELOG.md).

---

## 📄 Article

The manuscript describing this software, submitted to *Software Impacts*, lives in its own repository: [ML-Carbon-Project/physioflow_Software_Impacts](https://github.com/ML-Carbon-Project/physioflow_Software_Impacts).

---

## 👥 Support and Acknowledgments

This project was developed with support and funding from CNPq, CAPES, FAPEG, the Federal Institute Goiano (IF Goiano – Campus Rio Verde), and the Center of Excellence in Exponential Agriculture (CEAGRE).
