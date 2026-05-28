# Crop Physiology - Goiás Verde

> An open-source interactive web platform for exploratory data analysis, spatial modeling, and machine learning of crop ecophysiological parameters (soybean and sugarcane).

[English](./README.md) | [Português](./README.pt.md) | [Español](./README.es.md)

**Version:** 1.0  
**Initiative:** Goiás Verde Project (*Instituto Federal Goiano – Campus Rio Verde* & *Center of Excellence in Exponential Agriculture – CEAGRE*)

---

> ### 📖 [**System Operation Manual →**](./docs/manual.en.md)
>
> End-to-end walkthrough: installation, data upload, cleaning pipeline, EDA, modeling, spatial analysis, time series, group comparison, statistical glossary, and FAQ. **15 chapters, 26 screenshots.**
> *Extended abstract and introductory chapter available in English; complete edition currently in Portuguese — see [`manual.pt.md`](./docs/manual.pt.md). Spanish edition: incremental translation in progress.*

---

## 📋 Overview

This repository contains the Streamlit application developed to consolidate the cleaning, descriptive analysis, predictive modeling, and geospatial modeling workflow of **Crop Physiology** field datasets. The application validates data collected by photosynthesis systems (IRGA), chlorophyll meters, and ceptometers, applying an automated pipeline for cleaning and advanced analysis.

The tool is dataset-agnostic, provided the spreadsheet columns map correctly to the expected variables (e.g., photosynthesis rate `A`, transpiration `E`, stomatal conductance `gs`, chlorophylls, leaf area index `LAI/IAF`, etc.).

---

## 🛠️ Main Features

1.  **Ingestion & Schema Validation** — Ingestion of Excel (`.xlsx`, `.xls`) or CSV files with real-time validation against a 31-column physiological schema categorized by priority (*Required*, *Recommended*, *Optional*). It performs type coercion checks and geographic coordinate limits validation.
2.  **Cleaning Pipeline** — Transparent application of reactive filters: column removal, deselecting records without essential metadata, eliminating empty grid points, and **5 modes of replicate treatment** (mean average, replica expansion into independent rows via `melt`, or single replicate selection).
3.  **Exploratory Data Analysis (EDA)** — Complete descriptive statistics, data completeness checks, histograms, boxplots, correlation heatmaps (Pearson, Spearman, Kendall), category composition, normality tests (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), multicollinearity (VIF), hotspot rankings, and a multi-method outlier consensus audit.
4.  **Regression** — Bivariate regression fitting with presets tailored for crop physiology (e.g., *gs vs. A*, *Ci vs. A*, *gs vs. E*) with support for confidence intervals and faceting.
5.  **Predictive Modeling** — Training and evaluation of machine learning models (Linear Regression, Random Forest, Gradient Boosting, Decision Tree, KNN) to estimate the photosynthetic rate `A` based on other parameters, featuring cross-validation metrics, holdout validation, and feature importance charts.
6.  **Spatial Analysis** — Inverse Distance Weighting (IDW) interpolation, spatial autocorrelation via global Moran's I and local LISA (map of significant clusters), Getis-Ord Gi* hotspots, regular UTM grid cells aggregation, Ordinary Kriging with a fitted spherical variogram model, and a point-distribution map overlaid on Rio Verde (GO) municipal boundaries (via the `geobr` library).
7.  **Time Series** — Daily aggregation and STL time series decomposition (Trend, Seasonal, and Residuals).
8.  **Group Comparison** — Statistical comparisons between groups (e.g., soybean vs. sugarcane) using the Mann-Whitney U test, log-linear regression, and cumulative hourly profiles.

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
│   ├── schema.py               # Schema specifications and ranges
│   ├── pipeline.py             # Cleaning and replicates pipeline
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

## 👥 Support and Acknowledgments

This project was developed with support and funding from CNPq, CAPES, FAPEG, the Federal Institute Goiano (IF Goiano – Campus Rio Verde), and the Center of Excellence in Exponential Agriculture (CEAGRE).
