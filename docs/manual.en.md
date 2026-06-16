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

1. Introduction
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
12. Experimental Statistics (designs)
13. Statistical glossary
14. Troubleshooting (FAQ)
15. References
16. Contributing

---

## 1. Introduction

### 1.1 Who this manual is for

This manual targets **researchers, postgraduate students and field technicians** who will use the *PhysioFlow* application to analyse ecophysiological data collected in the field (IRGA, chlorophyll meter and ceptometer measurements). It assumes neither prior Streamlit experience nor Python programming background; it does assume basic familiarity with plant-physiology terms (`A` for net photosynthesis, `gs` for stomatal conductance, `Ci` for intercellular CO₂, leaf area index, chlorophyll a/b).

### 1.2 What the application does

In one sentence: **validates, cleans, explores and models** field spreadsheets of crop ecophysiology, with additional support for **spatial** analyses (over the municipality of Rio Verde, Goiás, Brazil) and **temporal** analyses. The default workflow is Upload → Pipeline → EDA → Regression / Modelling / Spatial / Temporal / Comparative. All analysis pages operate on the same session dataset and respect the global filters applied in the sidebar.

### 1.3 Typographic conventions

* `File/paths` and `code` appear in `monospace`.
* **Bold** marks interface elements (buttons, tabs, selector labels).
* *Italic* marks technical terms at first occurrence — each has an entry in the [Glossary](#13-statistical-glossary).
* `>` introduces an action instruction ("> click **Upload**").
* Screenshots use the bundled sample dataset `data/sample/0_Dados_Fisiologia_RIO VERDE.xlsx`.

### 1.4 Suggested reading paths

Different audiences benefit from different entry points:

| If you are… | Read in this order |
|---|---|
| A field technician about to upload a new dataset | Ch. 2 → Ch. 3 → Ch. 4 → glance at Ch. 13 (FAQ). |
| A graduate student running the standard analyses | Ch. 2 → Ch. 3 → Ch. 4 → Ch. 6 (EDA, in full) → the analysis chapter you need. |
| A senior researcher reviewing methodology | Ch. 6 → Ch. 8 (GroupKFold) → Ch. 9 (UTM projection, kriging) → Ch. 11 (pairwise comparison). |
| A peer reviewer or replicator | The Extended Abstract → Ch. 13 (Glossary) → Ch. 15 (References). |
| A contributor to the codebase | This manual → [`docs/architecture.md`](architecture.md) → [`docs/contributing.md`](contributing.md). |

### 1.5 What this manual does *not* cover

* Statistical theory beyond brief operational definitions — the [Glossary](#13-statistical-glossary) gives 2–3 line summaries; the [References](#15-references) point to primary literature.
* Field-collection protocols (how to use the IRGA, chlorophyll meter or ceptometer) — those belong to the instrument manufacturer manuals.
* Custom analyses not exposed in the UI — for those, export the processed dataset (Ch. 4) and use external tools.

---

## 2. Installation and first run

> **Before installing:** a hosted version is available at [physioflow.streamlit.app](https://physioflow.streamlit.app/). If you only want to try out features or share with collaborators without installing anything, ask the project maintainer for credentials and use it straight from the browser. The instructions below are for those who need to run the app **locally** (development, sensitive data, or when the deploy is unavailable).

### 2.1 Prerequisites

| Item | Minimum | Recommended |
|---|---|---|
| Operating system | Linux, macOS or Windows 10+ | macOS / Linux |
| Python | 3.12 | 3.12 or 3.14 |
| RAM | 4 GB | 8 GB |
| Disk space | 1 GB free | 2 GB free |
| Browser | Recent Chrome or Firefox | any Chromium-based |

### 2.2 Installing the environment

From the project root folder, open a terminal and run:

```bash
# 1) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# 2) Upgrade installers and install dependencies
pip install -U pip wheel
pip install -r requirements.txt
```

The installation downloads, among others, `streamlit`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, `esda`, `libpysal`, `geopandas`, `pyproj` and `geobr`. The first run can take from 30 seconds to 2 minutes while Streamlit caches resources.

### 2.3 Running the application

With the virtual environment activated:

```bash
python -m streamlit run app.py
```

The terminal will show something like:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

![Terminal showing Streamlit started](img/manual/01_terminal_streamlit_run.png)

The browser should open automatically at `http://localhost:8501`. If it does not, copy the **Local URL** and paste it into your browser.

### 2.4 The first screen

You will see the **Upload** page loaded, with the sidebar on the left containing:

* the **CEAGRE / Goiás Verde** logo;
* a **Language** selector (`Português` / `English` / `Español`);
* a navigation menu with **Upload**, **Pipeline and Processing**, **EDA**, **Regression**, **Modelling**, **Spatial Analysis**, **Time Series** and **Comparative**.

![First screen of the application](img/manual/02_app_primeira_tela.png)

### 2.5 Changing the language

Use the **Language** selector at the top of the sidebar. The change is instant; all pages, labels and warning messages switch to the chosen language. The default language is Portuguese.

### 2.6 Login (optional)

If the environment was configured with [Supabase](https://supabase.com) (variables `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the `.streamlit/secrets.toml` file), the application displays a login screen before the menu. If those variables do not exist, login is disabled and the app opens directly on Upload — the default behaviour for local use.

---

## 3. Loading your data

### 3.1 Accepted formats

| Extension | Notes |
|---|---|
| `.xlsx` | Recommended. Supports multiple sheets — you choose which one to load. |
| `.xls` | Legacy Excel, accepted. |
| `.csv` | Accepted. Use UTF-8 or Latin-1 encoding. |
| `.txt` / `.tsv` | Accepted. A **delimiter selector** appears (automatic, comma, semicolon, tab, space). |

Per-file limit: **500 MB** (Streamlit limit). For larger files, split them into separate sheets.

### 3.2 Data profile (Physiology / Generic)

On loading, the application resolves a **data profile**, selectable on the Upload page itself (Automatic / Physiology / Generic):

* **Physiology** — the dataset matches the physiology schema (see §3.3): schema validation, domain defaults and presets, and replicate handling all become active.
* **Generic** — any other dataset: the interface becomes neutral (a column summary instead of the schema report, no physiology assumptions, no replicates). This is what lets you use the platform with **any dataset**.

In **Automatic** (default), the profile is detected from the columns present; you can force it manually whenever you want.

### 3.3 Expected schema (Physiology profile)

The application compares your file's header against a **reference schema** with three severities:

| Severity | What it means | What happens if it is missing |
|---|---|---|
| **Required** | Without this column, the essential workflow does not work. | Highlighted warning; the pipeline may fail. |
| **Recommended** | Enables the standard analyses (EDA, regression, modelling). | Medium warning; specific analyses come out empty. |
| **Optional** | Enables specific modules (Spatial, Temporal, replicates). | Informational warning; the corresponding module is disabled. |

The complete column dictionary — canonical names, accepted synonyms, expected type and dependent module — is in [`docs/data_dictionary.md`](data_dictionary.md). The canonical list is generated from [`src/schema.py`](../src/schema.py); whenever the app is updated, that dictionary reflects the truth of the code.

> **Important:** the application accepts several spellings for the same column. `Cultura`, `CULTURA` and `Crop_Type` are treated as the same field; the same goes for `Latitude` / `LATITUDE`, `Data da coleta` / `Data` / `Date`, and so on. The actual file column appears in the "Found" column of the validation report.

### 3.4 Loading the file

> Click **Upload** > **Browse files**, choose the `.xlsx` file and click **Load file**.

If the file is an Excel workbook with several sheets, the app displays a selector to choose which one to load. After loading, two metrics appear at the top:

* **Rows** — total number of records read.
* **Columns** — total number of columns in the header.

![File loaded with metrics and start of schema](img/manual/03_upload_arquivo_carregado.png)

### 3.5 Reading the validation report

Right below the metrics is the **Expected schema validation** panel, with three summary boxes (required / recommended / optional) in the format `present / total`.

![Schema summary](img/manual/04_upload_schema_resumo.png)

#### Common warnings and what to do

| Message | Diagnosis | Suggested action |
|---|---|---|
| **"Missing required columns"** | Critical columns are missing from the file. | Rename the column in Excel to one of the accepted names (see dictionary); reload. |
| **"Required columns present but 100% empty"** | The column exists in the header, but all cells are empty. Common with `Manejo` and `Textura`. | Check whether the column should be filled in. If it is optional data for your study, ignore it — the pipeline still works, but some analyses will not consider that variable. |
| **"Latitude out of range [-90, 90]"** | Possible swap of Latitude and Longitude, or values in another unit (degrees minutes seconds). | Reopen the file, check the values and convert to decimal degrees. |
| Column flagged as **"type mismatch"** | The column was found but its content does not match the expected type (e.g. text in a numeric column). | Look for cells with text, comments or odd characters in the corresponding column. |

#### See the full table

> Click **Schema details** to expand a table with every expected column: name found, detected type, status (`present`, `empty (100% null)`, `missing`, `type mismatch`) and which app module depends on it.

![Detailed schema table](img/manual/05_upload_schema_tabela.png)

> **Tip:** clicking the **Download validation report** button saves this table as a CSV — useful to send to whoever is responsible for the spreadsheet asking for specific corrections.

### 3.6 What does NOT happen during Upload

* The file **is not sent** to any external server. Everything is processed locally, in your Streamlit session.
* No data is **discarded** at this stage. The cleaning pipeline only runs when you open the next tab (**Pipeline and Processing**).
* Columns with unknown names are **kept** in the dataset — you can use them in the EDA filters and charts, even if they are not part of the official schema.

### 3.7 When to reload

* If you fixed the spreadsheet externally (in Excel) and want to apply the changes, just repeat the upload — the app replaces the previously loaded file.
* If you switched language, you do **not** need to reload; only the UI changes, the dataset stays.

---

## 4. Cleaning pipeline

> Page **Pipeline and Processing** in the sidebar.

The spreadsheet uploaded on the Upload tab contains the **raw** dataset. Before any analysis, the application applies a pipeline of **4 deterministic steps** that standardise the text, remove rows without essential information, discard empty grid points and handle the replicates of the leaf measurements (Chlorophyll a/b and LAI). The result is the **processed** dataset, used by default in all subsequent analyses.

### 4.1 The 4 pipeline steps

Each step is recorded in the execution report, with `Rows before`, `Rows after` and `% removed`. Fixed order:

1. **Text standardisation** — removes extra spaces from the categorical columns (`Cultura`, `Uso atual`, `Época`, `Fazenda`, `Município`, `Estágio`) and converts "nan" / "None" / empty strings into `NaN`. It does not remove rows; it only normalises.
2. **Removal of records without essential metadata** — discards rows where **any one** of the columns `Cultura`, `Uso atual` or `Época` is empty. Without these three fields, the record cannot be grouped in the comparative analyses.
3. **Removal of empty grid points** — discards rows where **all** the agronomic/physiological variables are null (`A`, `E`, `gs`, `Ca`, `Ci`, `Ci/Ca`, `EUA`, `A/Ci`, `YII`, `ETR`, `Chl a`, `Chl b`, `IAF`). These are sample points planned in the grid but that received no measurement.
4. **Replicate handling** — consolidates the Chlorophyll a/b and LAI replicates according to the selected mode (see §4.2). It is the only step whose behaviour the user controls.

### 4.2 Replicate handling — choosing among the 6 modes

The spreadsheet contains **two replicates** of Chlorophyll a (`Chl a`, `Chl a.1`), **two** of Chlorophyll b (`Chl b`, `Chl b.1`) and **three** of LAI (`IAF`, `IAF.1`, `IAF.2`). The **Change Replicate Handling** dropdown offers six modes. Regardless of which one you choose, three output columns are created to standardise the interface: `Chl_a_media`, `Chl_b_media` and `IAF_media`.

![Replicate handling dropdown](img/manual/06_pipeline_dropdown_replicas.png)

| Mode | What it does | When to use |
|---|---|---|
| **Mean of Replicates** | Arithmetic mean of the available replicates. | Default. Appropriate when the replicates reflect genuine biological variability of the leaf/canopy. |
| **Median of Replicates** | Median of the replicates. Equivalent to the mean when n=2 (Chl a/b case); robust to an outlier in LAI (n=3). | When one of the readings may have been spurious (e.g. the ceptometer reading the sky by mistake) and you do not want it to pull the consolidated value. |
| **Unfold into Rows** | Creates one row per replicate, with the `Replica` column indicating 1, 2 or 3. It can even **triple** the number of rows. | When you want to treat each reading as an independent observation (e.g. to visualise intra-site variability in boxplots). |
| **Replicate 1 Only** | Uses only `Chl a`, `Chl b`, `IAF`. | Protocol comparisons between datasets that only kept the 1st replicate. |
| **Replicate 2 Only** | Uses only `Chl a.1`, `Chl b.1`, `IAF.1`. | Auditing — compare against Replicate 1 mode to detect discrepant readings. |
| **Replicate 3 Only (LAI)** | Only `IAF.2`; Chl a/b come out empty (there is only 1 extra replicate for LAI). | Specific ceptometer auditing. |

#### Why "Median" may give the same result as "Mean"

When there are only **2 replicates** (Chl a, Chl b), the median of two values is mathematically equal to their mean. That is why the application shows an explanatory caption right below the dropdown when you select the Median mode:

![Median mode caption](img/manual/09_pipeline_mediana_caption.png)

The real robustness gain only appears **for LAI** (3 replicates) — the median discards the most extreme value among the three readings.

### 4.3 Discard warnings

The pipeline runs silently, but displays highlighted yellow warnings when **more than 50 %** of the rows are discarded in a single step or in the final balance. This threshold was calibrated for the typical physiology-spreadsheet scenario: small losses (1-5 %) are expected; large losses usually mean that something odd is happening at the data source.

![Massive discard warning](img/manual/07_pipeline_warning_descarte.png)

In the sample dataset `0_Dados_Fisiologia_RIO VERDE.xlsx`, step 2 removes 94.9 % of the rows — because the spreadsheet has 1576 sample-grid points registered (with Latitude/Longitude and Fazenda) but **without** Cultura, Uso atual and Época filled in. These points represent locations planned for collection but that had no actual measurements. **The behaviour is correct**; the warning is there for you to confirm whether that is really the case or whether there is a data-entry problem that needs fixing at the source.

#### When to worry about the warning

| Scenario | Likely cause | Action |
|---|---|---|
| Discard > 90 % in step 2 | Spreadsheet contains a sample grid filled only with coordinates, with no crop metadata. | Check whether those rows were expected. If so, ignore the warning. |
| Discard ~50 % in step 2 | Half the spreadsheet has `Cultura` (or `Uso atual`, or `Época`) missing. | Go back to Excel and investigate which column. Probably something was lost in the export. |
| Discard > 10 % in step 3 | Several collection points without any physiological measurement. | Could be real (interrupted collection) or a leak of empty cells. |
| Warnings persist after you adjust | Wrong replicate mode, or a spreadsheet with an unexpected format. | Try switching among the 6 modes to see which one keeps the most rows. |

### 4.4 Reading the steps report

Right below the warnings (if any), the page displays the **Steps report** table with five columns: `Step`, `Rows before`, `Rows after`, `Removed`, `% removed`.

![Pipeline steps report](img/manual/08_pipeline_relatorio_etapas.png)

For the sample dataset, the typical reading is:

| Step | Before | After | Removed |
|---|---|---|---|
| Text standardisation | 1661 | 1661 | 0 |
| Removal without essential metadata | 1661 | 85 | 1576 |
| Removal of empty grid points | 85 | 81 | 4 |
| Replicate consolidation by mean | 81 | 81 | 0 |

Result: **81 analytical rows**, derived from the original 1661.

> **Tip:** if you select the *Unfold into Rows* mode, the last step will have `Rows after > Rows before` (up to 3×) — it is the only case in which the pipeline **grows** the number of rows. The "% removed" warning shows a negative value in that case, which is expected.

### 4.5 "Use processed data" toggle

Each of the analytical pages (EDA, Regression, Modelling, Spatial, Temporal, Comparative) has a **Use processed data** switch at the top:

* **On** (default): the page uses the dataset **processed** by the pipeline.
* **Off**: the page uses the **raw** dataset (the direct output of Upload, without any pipeline step).

Use the "off" position when you want to inspect the original spreadsheet — for example, to check whether a row that disappeared from the EDA was really absent at the source or was removed in one of the steps. For the main analysis, keep the toggle **on**.

### 4.6 Exporting the processed dataset

At the bottom of the page there are two buttons:

* **⬇ CSV** — `dataset_fisiologia_limpo.csv` file with UTF-8 BOM encoding (opens straight in Excel without breaking accents).
* **⬇ Excel** — `dataset_fisiologia_limpo.xlsx` file with the single sheet `Fisiologia_Limpo`.

Both contain the dataset **after the pipeline**, in the currently selected replicate mode. The three consolidated columns (`Chl_a_media`, `Chl_b_media`, `IAF_media`) are present in any mode; in *Unfold* mode, the `Replica` column appears additionally.

> **Reproducibility tip:** after loading a raw spreadsheet and choosing a replicate mode, export the processed CSV and archive it together with your results. You will have a snapshot of what was actually analysed, independent of future evolutions of the pipeline.

---

## 5. Global filters

> **⚙️ Settings and Filters Panel** at the top of the EDA, Regression, Modelling, Spatial and Time Series pages.

Even after the pipeline, we rarely want to analyse the entire dataset at once. The global filters panel lets you reactively restrict the analysis to a subset — by crop, by farm, by season, by date range — without having to reprocess the file. The filters are applied on each page independently and their changes are propagated to all charts and models on the page in real time.

### 5.1 Panel structure

The panel is an *expander* — click the header to expand or collapse it. By default it opens expanded on the first visit to the page. Inside it, six filters organised into two rows of three columns:

![Global filters panel](img/manual/10_eda_filtros_globais.png)

Row 1: **Replicate Handling** • **Crop** • **Municipality**
Row 2: **Farm** • **Season** • **Date Range**

Below the filters, a "Filtered Points" metric shows `n_filtered / n_total` — useful to quickly check how many rows are left after combining all the criteria.

### 5.2 Details of each filter

#### Replicate Handling (shortcut)

Replicates the Pipeline page dropdown here in the panel. Changing the mode in the sidebar **reprocesses the entire dataset** with the new mode, keeping the other filters. Useful when you are on an analysis page and want to compare the effect of switching from "Mean" to "Median" without going back to the Pipeline page.

> **Note:** changing the mode here causes the page to reload (Streamlit `st.rerun()`). Your selections on the other tabs are preserved.

#### Crop

Multiselect with all the crops present in the dataset. By default, all are checked. Uncheck crops to exclude them from the analysis.

> In the sample dataset: options *Soybean* and *Sugarcane*.

#### Municipality

Single-select selectbox with the special option **"All"** at the top. Useful when the dataset has more than one city — it restricts to a single municipality.

> In the sample dataset: only *Rio Verde*. The filter is available but has no practical effect.

#### Farm

Selectbox with **"All"** + one entry per farm present. **Important:** if you have already filtered by Municipality, only the farms of that municipality appear (filters are chained).

> In the sample dataset: *Farm B* (soybean) and *Farm A* (sugarcane). Remember: these two farms are **redundant** with the `Cultura` column — see the confounding panel on the EDA **Quality** tab. Filtering by one is equivalent to filtering by the other.

#### Season

Multiselect with the available seasons. Behaviour identical to the Crop filter.

> In the sample dataset: *Summer* (52 rows after pipeline) and *Spring* (29 rows).

#### Date Range

`date_input` with **two pointers** — set the start date and the end date. By default it uses the full range of the dataset.

> In the sample dataset: three unique dates (2025-12-19, 2026-01-16, 2026-02-28). The filter is of little use here given the small number of collections, but it becomes powerful in datasets with monthly series.

### 5.3 Combining filters — AND behaviour

All filters are applied **simultaneously** (logical **AND** operator). For example: selecting *Soybean* in Crop **and** *Summer* in Season keeps only the rows that satisfy **both** criteria.

> **Diagnostic tip:** if the "Filtered Points" metric shows 0, some combination of your filters eliminated all rows. Collapse the panel and try reopening a selection; the most common case is crossing contradictory Crop and Farm (e.g. Sugarcane × Farm B in the sample dataset, which gives 0).

### 5.4 Filter scope — per page, not global

Despite the name "global", each page has **its own filter panel**. Switching to the EDA tab, adjusting filters, and going back to Regression does **not** apply the adjustments to Regression — you need to configure them there too. This is intentional: it lets you compare analyses on different subsets side by side.

The exception is **Replicate Handling** — changing it affects the processed dataset and is reflected on all pages, because it is a pipeline decision and not a visualisation filter.

### 5.5 When NOT to use filters

* **Before the initial EDA.** Start by looking at the entire dataset to detect patterns and *outliers*. Use the filters later, to isolate specific groups.
* **To clean bad data.** A filter is not cleaning. If a row is wrong, fix it in the source spreadsheet and redo the upload; do not hide it with a filter.
* **To create two groups to compare.** For that, use the **Comparative** page (chapter 11), which has dedicated tools (Mann-Whitney, log-linear by group).

## 6. Exploratory Data Analysis (EDA)

> Page **EDA** in the sidebar.

Exploratory Data Analysis is the most extensive module of the application. Twelve tabs, each with a distinct family of questions: how do the values distribute? Is there missing data? Are variables correlated? Do the groups differ from one another? Where are the sample points in space? When were they collected? Are there *outliers* to investigate?

Use the EDA **before** any regression or modelling — it is here that you discover that `Fazenda` is redundant with `Cultura`, that `Ca` is practically constant (and therefore correlations with it are spurious), that half your dataset has `Peso Seco` missing, or that a reading was recorded as 9999 by mistake.

The 12 tabs are organised into three families:

* **Descriptive:** Statistical Summary, Data Quality, Bivariate Relations, Boxplots, Scatter, Correlation, Composition.
* **Geographic and Temporal:** Spatial, Temporal.
* **Inference and Auditing:** Inference (KW + Normality + VIF), Hotspots, Outliers.

### 6.1 Statistical Summary

Shows the classic descriptive statistics (count, mean, std, min, quartiles, max) plus **skewness** and **kurtosis** for each numeric variable.

![EDA statistical summary](img/manual/11_eda_resumo_estatistico.png)

**How to read it:**

| Indicator | Interpretation |
|---|---|
| `count = 0` | Column 100 % empty (the case of `Manejo` and `Textura` in the sample dataset). |
| Large difference between `mean` and `50%` (median) | Skewed distribution. |
| `skewness` between -0.5 and 0.5 | Approximately symmetric distribution. |
| `|skewness|` > 1 | Strongly skewed distribution — consider a log transformation or non-parametric methods. |
| `kurtosis` > 3 | Heavy tails (more *outliers* than a normal). |
| `kurtosis` < 0 | Flattened distribution (lighter tails than a normal). |

> **Tip:** the **Download statistical summary (CSV)** button exports this table. It is useful to include as an appendix in a field report.

### 6.2 Data Quality

Combines three blocks: row/column counts, *missing* per column (table + chart) and — since v1.1 — an audit of **confounding between categoricals**.

![Metrics and missing per column](img/manual/12_eda_qualidade_metrics.png)

#### Missing per column

Table sorted from most to least missing, with `missing` (absolute count) and `percent` (proportion). Right below, a bar chart with the columns that have at least 1 missing value.

> **In the Rio Verde dataset (*unfold* mode):** `Manejo` and `Textura` appear at 100 % missing; `IAF.2` and `Peso Seco` at ~52 %; `IAF.1`, `Chl b.1`, `Chl a.1` at ~18 %; `gs` at ~6 %. This pattern (the 3rd replicate less filled in than the 2nd, which is less than the 1st) is typical of field collections.

#### Category frequency

Selectbox where you choose a categorical column (`Cultura`, `Fazenda`, `Estágio`, etc.) and see the count table per level. Useful to detect typing problems ("Verão" vs "verao", "soja" vs "Soja").

#### Confounding between categories

This is a **fundamental** section that prevents misleading conclusions in the rest of the manual. It shows a table with the pairs of categorical columns that partition the rows in the **same way**, computed via *Cramér's V* (see Glossary §13).

![Confounding-between-categories panel](img/manual/13_eda_qualidade_confounding.png)

**Types of relationship that appear:**

| Relationship | What it means | Example in the Rio Verde dataset |
|---|---|---|
| **Redundant (A ≡ B)** | The two columns are equivalent; one is just a relabelling of the other. **Cramér's V = 1.000 in both directions.** | `Fazenda ⟷ Cultura ⟷ Uso atual` — all partition the 81 rows into "Farm B / Soybean / Short Cycle" vs "Farm A / Sugarcane / Perennial". |
| **{A} determines {B}** | Each level of A belongs to a single level of B, but the converse is not true (B has more levels). | `Estágio` determines `Cultura` (each phenological stage occurs in only one crop). |
| **High (partial) association** | Strong association, but neither direction is deterministic. | Rare in this dataset. |

**Why this matters:**

When two columns are redundant, any "effect" attributed to one is statistically **indistinguishable** from the effect of the other. If you run a Moran's I and find a huge spatial cluster (HH on one farm, LL on the other), what is being captured may be a **biological difference between the crops**, not **real spatial autocorrelation**. Likewise, comparing `gs` between farms is equivalent to comparing `gs` between crops — only with a different label.

> **When there are redundant pairs**, the app displays a highlighted yellow warning: *"There are fully redundant pairs — do not use both as independent factors in models or comparisons."*

### 6.3 Bivariate Relations (univariate distributions)

Despite the name, this tab shows **univariate distributions** — one histogram per selected variable. The name reflects a historical choice of the app; the content is strictly *univariate*.

**Settings:**

* **Variables** (multiselect) — up to 3 numeric variables, with sensible defaults.
* **Bins** (slider) — number of histogram classes (10 to 100).
* **KDE** (checkbox) — overlays a kernel density estimate.

**How to use:** start with the defaults and adjust `bins` if the distribution looks "rough" (too few bins) or "noisy" (too many bins). The KDE helps to identify bimodality — useful to flag when a variable is a mixture of two populations (e.g. soybean + sugarcane). When the KDE shows two peaks, consider running analyses **by group** (with `hue` on the Boxplot tab or in the Comparative).

### 6.4 Boxplots by Group

Box-plots (or *violin plots*) of a numeric variable grouped by a categorical column, optionally with a second categorical as `hue`.

**Main settings:**

* **Target variable** — the numeric one that goes on the Y axis.
* **Grouping (X)** — the categorical that goes on the X axis.
* **Colour (hue)** — optional, a second categorical that colours the boxes side by side.
* **Type** — Boxplot or Violinplot.

**How to read it:**

| Element | Meaning |
|---|---|
| Box | 25th to 75th percentile (interquartile range, IQR). |
| Horizontal line in the box | Median. |
| "Whiskers" | Extend up to 1.5 × IQR. |
| Isolated points | Outliers (beyond 1.5 × IQR). |

Violinplot adds the shape of the distribution (width proportional to local density). Use **violin** when the shape matters (bimodality); use **boxplot** when you want to compare many groups quickly.

> **Beware of a redundant `hue`:** if you select `Cultura` on the X axis **and** `Fazenda` as `hue` in the Rio Verde dataset, you will see two identical boxes side by side per category — because they are the same partition (see §6.2). Choose a `hue` that **differentiates** within the group (e.g. `Estágio` within Cultura).

### 6.5 Scatter (pairplot)

Scatter of **pairs** of numeric variables in a lower-triangular grid. Optionally colouring the points by a categorical.

**Settings:**

* **Variables** (multiselect) — between 2 and 6 variables. More than 6 becomes illegible.
* **Colour (hue)** — optional. Useful to visualise separation between crops.
* **Sample** (slider 100-5000) — limits the number of plotted points. For the 81-row Rio Verde dataset, irrelevant; important in large datasets to keep the render fast.

**What to look for:**

* **Pairs with visible correlation** (clear ascending or descending line) — confirm later on the Correlation tab (§6.6).
* **Extreme outliers** — points that lie visibly far from the cloud. Make a mental note to investigate on the Outliers tab (§6.12).
* **Non-linearities** — curves or U-shaped patterns suggest that linear regression is inadequate and Spearman is better than Pearson.

### 6.6 Correlation

Correlation heatmap between the selected numeric variables, in three alternative metrics:

| Method | Measures | When to use |
|---|---|---|
| **Pearson** | Linear association. | Approximately normal variables and a linear relationship. |
| **Spearman** | Monotonic (rank) association. | **Recommended default** — robust to outliers and to monotonic non-linearities. |
| **Kendall** | Pairwise concordance. | Small datasets (n < 30) with many ties. |

![Spearman correlation heatmap](img/manual/14_eda_correlacao_spearman.png)

**How to read typical values:**

| Range of r | Interpretation |
|---|---|
| `|r|` ≥ 0.8 | Very strong correlation — confirm it is not by mathematical construction (Ci/Ca derived from Ci/Ca). |
| 0.5 ≤ `|r|` < 0.8 | Strong. |
| 0.3 ≤ `|r|` < 0.5 | Moderate. |
| `|r|` < 0.3 | Weak to negligible. |

> **In the Rio Verde dataset:** you will see `E ↔ gs` ≈ 0.93 (a classic physiological one), `YII ↔ ETR` ≈ 0.96 (derived — ETR is a function of YII), `Ci ↔ Ci/Ca` = 1.00 (Ca nearly constant, so Ci/Ca ≈ Ci × const). These three pairs are **expected** and do not indicate a data problem; they reflect the chemistry/mathematics of the variables themselves.

Use the **Download correlation (CSV)** button to include the matrix in a report.

### 6.7 Spatial (exploratory)

Scatter map of the collection points plotted in Longitude × Latitude, coloured and sized by a chosen variable. Optionally faceted by a categorical (e.g. one panel per Crop).

**Difference from the Spatial Analysis page:** here it is only **exploratory visualisation** — there is no interpolation, autocorrelation or kriging. Use this tab to get a quick view of the geographic distribution before moving on to statistical-spatial analyses (ch. 9).

### 6.8 Temporal (exploratory)

Aggregated time series (daily mean or median) of a variable, optionally coloured by a categorical.

> For the Rio Verde dataset, with only three distinct dates, the series appears as three points. In datasets with long series (monthly or weekly campaigns), this tab becomes the overview chart before STL decomposition (ch. 10).

### 6.9 Composition

Dual chart (bars + pie) showing the composition of a categorical column. Useful for presentations — it visually communicates "60 % of the dataset is soybean, 40 % is sugarcane".

### 6.10 Inference

This tab combines **three distinct statistical analyses** in a single screen: Kruskal-Wallis (comparison between groups), normality tests (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson) and VIF (multicollinearity). It is the densest tab in the EDA.

#### Kruskal-Wallis (KW)

Non-parametric test to compare the **distributions** of a numeric variable across **two or more groups** defined by a categorical column. Null hypothesis: all groups come from the same distribution.

**Settings:**

* **Grouping column** — categorical (`Cultura`, `Época`, `Estágio`, etc.).
* **Numeric variables** — one or more (multiselect).
* **Alpha (α)** — significance level (default 0.05).
* **Minimum N per group** — automatically excludes levels with fewer than N samples (default 5). See why in the next box.

![Minimum N slider + table with dropped_levels](img/manual/18_eda_kruskal_min_n.png)

**Why the "Minimum N per group" exists:** with groups of size 2 or 3, the KW has **low statistical power** and the p-value becomes imprecise. The slider lets you discard these groups before the test. The `dropped_levels` column in the results table shows which ones were excluded — useful for auditing. If there is any discard, the app emits an explanatory warning below the table.

**How to read the results table:**

| Column | Meaning |
|---|---|
| `variable` | The tested variable. |
| `groups` | Number of groups that survived the minimum-N filter. |
| `H` | Kruskal-Wallis statistic (non-parametric). |
| `p_value` | Probability under H₀. |
| `significant` | `True` if p < α. |
| `dropped_levels` | Levels excluded for having n < minimum. |

> **When k = 2 groups**, the Kruskal-Wallis is mathematically equivalent to the **Mann-Whitney U** *two-sided*. The app keeps the "Kruskal-Wallis" label for consistency, but you can report it as Mann-Whitney when describing the test in your paper.

#### Normality tests

Three complementary tests applied to each selected variable:

| Test | Characteristic |
|---|---|
| **Shapiro-Wilk** | The most sensitive for n < 5000. Literature standard. |
| **Anderson-Darling** | Good power in the tails. Returns an A² statistic + critical value at 5 %. |
| **D'Agostino-Pearson (K²)** | Combines skewness and kurtosis tests. Robust to ties. |

The `normal_at_alpha` column is `True` only when **all three** tests agree that normality is not rejected.

![Normality tests table](img/manual/15_eda_normalidade_tabela.png)

**Mind the sample size:** with a large n (above a few hundred), the three tests detect minimal deviations from normality and almost always reject. This does **not** mean the distribution is unusable for parametric analyses — it just means it is not *perfectly* normal. The app includes an explanatory caption right below the table.

To judge the **magnitude** of the deviation (and not just its significance), look at the **Q-Q plot** that appears right below:

![Grid of Q-Q plots](img/manual/16_eda_normalidade_qqplots.png)

**How to read a Q-Q plot:**

* Points on the red line (or close to it) → distribution close to normal.
* Points forming an "S" curve → lighter or heavier tails than a normal.
* Points far from the line at the ends → outliers or deviations in the tails (typical in physiological variables).

#### VIF — Variance Inflation Factor

Measures multicollinearity among explanatory variables. For each variable, the VIF is computed by regressing it against all the others and returning `1 / (1 - R²)`.

| VIF range | Interpretation |
|---|---|
| VIF < 5 | Low multicollinearity — variables independent enough. |
| 5 ≤ VIF < 10 | Moderate multicollinearity. |
| VIF ≥ 10 | Severe multicollinearity — consider removing one of the variables. |

![VIF panel with caption about derived variables](img/manual/17_eda_vif_painel.png)

> **Beware of derived variables:** the app shows a caption warning that `Ci/Ca`, `A/Ci`, `EUA = A/E` and `ETR` are ratios/functions of other variables in the schema, which inflates the VIF **by mathematical construction**, without that reflecting a data-quality problem. In the Rio Verde dataset, for example, `Ci/Ca` reaches VIF ≈ 149,000 — that is not a number suggesting you remove Ci/Ca, it is a sign that Ca is practically constant and Ci/Ca has become a rescaling of Ci.

### 6.11 Hotspots

Ranking of the `top_n` groups with the highest mean (or median) value of a target variable, with a horizontal bar chart. Optionally faceted by a second categorical.

**When to use:** quickly identify which farms, stages or regions concentrate the highest values of a physiological variable. Output exportable as CSV for inclusion in field reports.

### 6.12 Outliers (multi-method)

Outlier detection combining **five** methods with very different criteria:

| Method | Assumption | Robust to outliers? |
|---|---|---|
| **Z-score** (\|z\| > 3) | Approximately normal distribution. | No — the standard deviation is pulled by the outliers themselves. |
| **IQR (1.5×)** | None (non-parametric). | Yes. |
| **Isolation Forest** | Non-parametric, tree-based. | Yes. |
| **LOF** (Local Outlier Factor) | Non-parametric, based on local density. | Yes. |
| **Elliptic Envelope** | **Multivariate normality.** | **No — sensitive to bimodal or skewed data.** |

![Outliers panel with assumptions caption](img/manual/19_eda_outliers_assumptions.png)

**Consensus ≥3 votes:** the app marks a row as an outlier by consensus when at least **3 of the 5 methods** agree. It is a deliberately conservative rule: each method on its own generates false positives with a different profile; requiring a majority drastically reduces false markings.

> **Limitation in the Rio Verde dataset:** since it has only 81 rows and two crops with very distinct distributions, the normality-based methods (Z-score, Elliptic Envelope) tend to under-detect, while the density-based ones (LOF) may mark **entire crops** as "outliers". Use the audit table to investigate case by case before removing.

The output table lists the first 200 rows with each binary flag (z_score, iqr, isolation_forest, lof, elliptic_envelope), the vote count, and the final consensus. Available for download as CSV.

## 7. Bivariate regression

> Page **Regression** in the sidebar.

This page is dedicated to **simple linear regression** between **two numeric variables**, with options for colouring by category (`hue`) and faceting. It is useful for inspecting classic physiological relationships (gs vs. A, Ci vs. A) and visually validating whether the relationship is approximately linear before moving on to more sophisticated modelling (ch. 8).

### 7.1 Physiological presets

At the top of the page, a **Preset** selector offers four pre-configured combinations based on physiologically meaningful pairs:

| Preset | X | Y | Colour | Interpretation |
|---|---|---|---|---|
| Stomatal Conductance (gs) vs. Photosynthesis (A) | gs | A | Cultura | Classic relationship: higher gs → more CO₂ enters → higher A, up to a saturation point. |
| Internal CO₂ (Ci) vs. Photosynthesis (A) | Ci | A | Cultura | A-Ci curve — fundamental in the Farquhar model of photosynthesis. |
| Stomatal Conductance (gs) vs. Transpiration (E) | gs | E | Cultura | Almost always strongly linear: gs governs transpiration. |
| Chlorophyll a vs. Photosynthesis (A) | Chl_a_media | A | Cultura | Expected positive association — more chlorophyll, more light capture. |

> The presets only appear when **both** columns are present in the dataset. If you selected a replicate mode that does not create the columns (`Chl_a_media`, etc.), the respective preset disappears.

### 7.2 Custom regression

Below the presets, a **Custom regression** section gives full control:

* **X variable** (numeric selectbox).
* **Y variable** (numeric selectbox, excluding X).
* **Colour (hue)** — optional, categorical.
* **Facet (col)** — optional, a categorical that opens one panel per level.
* **Confidence interval** (slider 0-99 %) — shaded band around the line.
* **Maximum sample** (slider 100-5000) — limits plotted points for performance.

The output is a seaborn `lmplot`: scatter + regression line + CI band. When `hue` is enabled, each category gets its own line (regression **by group**).

### 7.3 How to read the result

Below the chart, a caption shows the **Pearson correlation** between X and Y and the `n` of the chart. Use it for a quick check — if r is close to zero but the chart looks linear, there is probably some underlying log/sqrt transformation that would make the relationship appear.

> **Limitations of this page:**
>
> * It is **linear only** — there is no polynomial, log-linear or mixed-model fitting. For those cases, use the Comparative page (log-linear regression by group, ch. 11) or export the processed dataset and use R/Python externally.
> * It does not print coefficients (intercept, slope, p-value) — only the chart and the correlation. For regression **with full diagnostics**, use the Modelling page (ch. 8) selecting the `Linear Regression` model.

---

## 8. Predictive modelling

> Page **Modelling** in the sidebar.

This page lets you **train and compare multiple models** simultaneously, with cross-validation and holdout metrics. A selector at the top (**Task type**) switches between **Regression** (numeric target — e.g. predicting photosynthesis `A`) and **Classification** (categorical target — e.g. predicting the species/crop). Subsections 8.1–8.7 describe the regression workflow; §8.8 covers classification.

### 8.1 Choosing target and features

* **Target variable** — a numeric variable. Default: `A`.
* **Features** — multiple explanatory variables, numeric and categorical. Default (in the Rio Verde dataset): `gs`, `Ca`, `Ci`, `Ci/Ca`, `E`, `YII`, `ETR`, `Chl_a_media`, `Chl_b_media`, `IAF_media`, `Cultura`, `Fazenda`, `Época`.

Categorical features are automatically encoded via `OneHotEncoder`. Numeric features that need scaling (LR and KNN) receive `StandardScaler` in the pipeline.

### 8.2 Available models

Five `scikit-learn` models, all with sensible pre-configured hyperparameters:

| Model | Characteristics | When to prefer |
|---|---|---|
| **Linear Regression** | Interpretable coefficients; assumes linearity. | When you seek *explanation* more than pure *prediction*. |
| **Random Forest** | 200 trees; good out-of-the-box performance; captures non-linearities and interactions. | Recommended default for predictive modelling. |
| **Decision Tree** | Simple model, easy to visualise. | Only as a baseline or to understand rules. |
| **Gradient Boosting** | Often more accurate than Random Forest; more prone to overfitting. | When you want maximum accuracy and have time to tune. |
| **KNN** | No training; prediction depends on the k=5 neighbours. | Small, smooth datasets. |

### 8.3 Holdout and cross-validation

Two sliders control the validation scheme:

* **Holdout size** (0.10 to 0.40) — fraction of the data reserved for testing. Default 0.30.
* **Cross-validation folds** (3 to 10) — number of folds. Default 5.

### 8.4 Cross-validation strategy

This is the most important decision on this page. A radio offers two options:

![Modelling with GroupKFold by Farm + Point](img/manual/20_modelagem_groupkfold.png)

| Strategy | Description | When to use |
|---|---|---|
| **Random KFold** | Rows distributed randomly across folds. | When there is **no pseudoreplication** — every row in the dataset is a genuinely independent observation. |
| **GroupKFold (by site)** | All replicates from the same site stay **in the same fold**. The model never sees in training rows correlated with those in the test set. | **Recommended** whenever there is more than one measurement per sampling point (*unfold* replicate modes; sites with multiple dates; etc.). |

#### Grouping column

When you choose GroupKFold, a **Grouping column** selectbox appears with candidates:

* **Fazenda + Ponto** — a synthetic option that combines the two columns, creating a unique site identifier. Recommended default.
* **Fazenda** — groups by farm; may yield too few groups if the dataset has only 2-3 farms.
* **ID**, **LABEL** — unique per-row identifiers; almost equivalent to random KFold.
* Other categorical columns present in the dataset.

> **Automatic fold adjustment:** if the number of groups is smaller than the chosen number of folds, the app automatically reduces the folds and shows a yellow warning (e.g. "Only 4 groups available; reducing folds from 5 to 4").

#### Why this matters for the Rio Verde dataset

We confirmed during the audit that the leak in this specific dataset is small (R² ~0.946 with random vs. ~0.944 with GroupKFold for Linear Regression). **However:** this scenario is favoured by the very strong mechanistic signal between `A` and the predictors. In future datasets with more replicates per site (e.g. 3 replicates × several dates × 2 crops), the difference may be much larger — and random KFold will **overestimate** the R² expected in the field. GroupKFold gives a more conservative and realistic estimate.

### 8.5 Reading the results table

The table compares the selected models on five metrics:

| Metric | Meaning |
|---|---|
| `R² Holdout` | Coefficient of determination on the holdout (30% of the data). |
| `MAE Holdout` | Mean absolute error (same unit as the target). |
| `RMSE Holdout` | Root mean squared error. |
| `CV R² mean` | Mean R² across the K CV folds. |
| `CV R² std` | Standard deviation of R² across folds (model stability). |

The **best model** is highlighted in two large metrics above the table ("Best CV R²" and "Best Holdout R²"). The baseline row is usually Linear Regression; more sophisticated models (RF, GB) need to beat it by a clear margin to justify their use.

### 8.6 Predicted vs. observed

For any trained model, you can plot a **predicted × observed** chart. Points along the red diagonal indicate perfect prediction. Systematic deviations (all points below or above the line) indicate bias that warrants investigation.

### 8.7 Feature importance

For tree-based models (RF, GB, DT), a bar chart of **feature importances** appears (sklearn's feature_importances_). For Linear Regression, it shows the absolute **|coefficients|** after standardisation. KNN provides no importance.

> **Interpretation caveat:** tree importances **split the credit** among correlated variables. If `Ci` and `Ci/Ca` carry nearly the same information (VIF > 10⁴ in Rio Verde, see §6.10), the model splits the importance between them, and neither appears as "very important" on its own. Look at the set, not each bar in isolation.

### 8.8 Classification mode

Selecting **Classification** in *Task type*, the target becomes a **categorical** column (e.g. crop, species, management class). Up to **8 classifiers** from `scikit-learn` are trained and compared: Logistic Regression, Random Forest, Decision Tree, Gradient Boosting, HistGradientBoosting, KNN, SVM and Naive Bayes.

The evaluation uses cross-validation (with the option of **GroupKFold** by site, as in regression) and holdout, reporting:

* **Accuracy, F1, Precision and Recall** (macro) per model, in the comparison table;
* **Confusion matrix** of the best model;
* **Feature importance** (or |coefficients| for Logistic Regression).

There is also a **scaling** selector (StandardScaler / none) for the scale-sensitive models (Logistic, KNN, SVM). The workflow is symmetric to regression — the difference is the categorical target and the classification metrics.

---

## 9. Spatial analysis

> Page **Spatial Analysis** in the sidebar.

This page gathers **six tabs** of geospatial analysis: deterministic interpolation (IDW), global and local autocorrelation (Moran's I), hotspots (Getis-Ord Gi*), aggregation in a regular UTM grid, ordinary kriging with a spherical semivariogram, and a map over the administrative boundaries of Rio Verde, Goiás.

Since v1.1, **all distance analyses** (IDW, kriging, Moran KNN, Gi*) operate internally in **UTM metres** (EPSG 32722 for Rio Verde), even when the map axes appear in latitude/longitude. This eliminates the anisotropy introduced when Euclidean distance is computed in degrees (1° of longitude ≈ 105 km vs. 1° of latitude ≈ 111 km at -17.8°).

### 9.1 IDW — Inverse Distance Weighting

> **IDW** tab.

Estimates the value of a variable on a regular grid using the weighted average of the known sample points, with **weight inversely proportional to distance**.

![IDW map of a variable](img/manual/21_espacial_idw.png)

**Settings:**

* **Target variable** — which variable to interpolate.
* **Facet by** — optional categorical; generates one map per level (useful to compare Soybean vs. Sugarcane side by side).
* **Grid size** (80-320) — interpolation resolution. Higher = prettier, but slower. Default 180.
* **Power** (0.5-4.0) — exponent of the inverse distance. Default 2.
  * `power=1`: strong smoothing, values tend to the mean.
  * `power=2`: default, balanced.
  * `power=4`: each point dominates its immediate surroundings.

**How to read the map:** the colours follow the `viridis` palette. The white circles are the **actual sample points**; the rest of the surface is interpolated. Areas far from any sampled point have an unreliable value — IDW forces continuity even where there is no data.

> **Limitation:** IDW is **deterministic** — there is no uncertainty band. For statistical uncertainty, use Kriging (§9.5).

### 9.2 Moran's I — Spatial autocorrelation

> **Moran** tab.

Measures whether **similar** values tend to be close together in space. Returns a global index and maps of local clusters (LISA).

![LISA map + Moran scatterplot](img/manual/22_espacial_moran.png)

**Settings:**

* **Target variable**.
* **k nearest neighbours** (3-12) — how many neighbours define the "surroundings" of each point.
* **Number of permutations** (99-999) — the higher, the more precise the p-value (Monte Carlo).

**Global metrics:**

| Metric | Interpretation |
|---|---|
| `I` close to +1 | Strong positive autocorrelation (similar values cluster). |
| `I` close to 0 | Random distribution in space. |
| `I` close to -1 | Negative autocorrelation (similar values stay apart; rare). |
| `p_sim` < 0.05 | I is statistically significant. |

**LISA map — four categories:**

| Cluster | Colour | Meaning |
|---|---|---|
| **HH** | Red | Site with a high value surrounded by high neighbours (hotspot). |
| **LL** | Blue | Site with a low value surrounded by low neighbours (coldspot). |
| **HL** | Orange | High site surrounded by low ones (high outlier). |
| **LH** | Light blue | Low site surrounded by high ones (low outlier). |
| **NS** | Grey | Not significant. |

> **Beware of confounding:** if the Quality tab (§6.2) reports `Fazenda ⟷ Cultura` as redundant, and each crop is concentrated on one farm, the **Moran's I will be very high** (~0.9). But that spatial cluster may be just the reflection of the crop effect disguised as a space effect. Confirm by running Moran conditionally: filter by a single crop, restrict the dataset, and see whether I stays high.

### 9.3 Getis-Ord Gi* — Formal hotspots

> **Gi*** tab.

Detects **hotspots** (clusters of high values) and **coldspots** (clusters of low values) using a distance band instead of KNN. More formal and direct than LISA when the goal is **just to identify where the concentrations are**.

**Computing the d* band:** the app takes each point, finds the distance to its k-th neighbour, and uses the **maximum** of those distances × 1.001. This guarantees that every point has at least k neighbours in the Gi* computation. The d* value appears in metres, with a caption indicating the UTM EPSG used.

Output: a map with points coloured as **Hotspot** (red), **Coldspot** (blue) or **NS** (grey); a summary table with mean and median per class; exportable CSV.

### 9.4 Regular UTM grid

> **UTM Grid** tab.

Instead of interpolating a continuous surface, it aggregates the sample points into **regular square cells** (in km) and computes the mean/median of a variable per cell. Useful for presenting average values "per quadrant" in communication for managers.

**Settings:**

* **Target variable**.
* **Cell size** (0.5-10 km) — side of the square.
* **Facet by** — optional.
* **Aggregation** — mean or median.

Output: a choropleth map (coloured polygons) + a table of the top-50 cells sorted by value + CSV.

### 9.5 Ordinary kriging

> **Kriging** tab.

**Statistical** interpolation based on the spatial structure of the data. Unlike IDW, it returns estimates based on a fitted **variogram** — it captures how similar the relationship between pairs of points is as a function of distance.

![Variogram with axis in metres and EPSG caption](img/manual/23_espacial_variograma_metros.png)

**Two-step workflow:**

#### Step 1: fit the variogram

* **Target variable**.
* **Number of lags** (6-30) — distance classes in the empirical variogram.
* **Maximum fraction** (0.3-0.95) — uses only pairs up to that fraction of the maximum distance (discarding the "edge" of the variogram, which has few pairs).
* **Winsorize** (checkbox) — clips the tails at 2 % and 98 % before fitting; useful when there are extreme outliers.

The empirical variogram appears as green points, and the **fitted spherical model** as a red line. Three parameters are reported (all in **metres**):

| Parameter | Meaning |
|---|---|
| **Nugget (C₀)** | Variance at zero distance — reflects measurement error + fine-scale variance. |
| **Sill (C)** | Difference between the asymptotic level and the nugget. |
| **Range (a)** | Distance at which the variogram stabilises. Beyond this radius, points are considered spatially independent. |

**Diagnostic:** if the variogram **does not stabilise** within the considered window (it keeps rising to the end), the fitted range will come out as an absurdly high number (10⁵ to 10⁷ metres). This means there is **no detectable spatial structure** at this scale — probably the dataset is too small, or the variable is poorly correlated with position. Do not run the kriging in this situation.

#### Step 2: run the kriging (on demand)

Kriging is computationally expensive, so it only runs when you check the **Run ordinary kriging** checkbox. The output map uses the same lat/lon grid on the axes, but the internal computation is entirely in UTM.

### 9.6 Map over Rio Verde

> **Basemap** tab.

Shows the sample points coloured by a variable, **overlaid on the administrative boundaries of Rio Verde, Goiás** (loaded via the `geobr` library). Useful for presentations that need to show the geographic context of the municipality.

> Requires an internet connection on first run (it downloads the municipality shapefile via geobr). Afterwards it stays cached.

> **Limitation on cloud deploys:** the `geobr` library was removed from the default [`requirements.txt`](../requirements.txt) because it pulls `lxml` as a transitive dependency, which has no pre-compiled wheel for Python 3.14 (the version used by Streamlit Community Cloud). Without `geobr` installed, the app keeps working — only this tab shows "unavailable" and ignores the municipality overlay. To re-enable it **locally**, just run `pip install geobr>=0.2.2` in your venv.

## 10. Time series

> Page **Time Series** in the sidebar.

This page is specific to **univariate longitudinal** analysis — it aggregates a variable per day and, optionally, decomposes the series into trend, seasonality and residual components. **Unlike the EDA Temporal tab** (§6.8), the focus here is the **formal temporal structure** of the series, not just exploratory visualisation.

### 10.1 Date column detection

The app automatically looks for a candidate date column: `Data da coleta`, `Data`, `Date`, `DATE_TIME initial_value` and similar (canonical list in [`src/pipeline.py`](../src/pipeline.py) in the `find_date_column` function). Since v1.1, the detection also coerces columns with **`object` dtype containing a mixture of `datetime.datetime` + `str` + `NaN`** — a typical case of Excel exported in field datasets.

If no column is detected, the page displays **"Date column not found"** and stays empty. Check in Excel whether the date column is named according to one of the accepted variants and whether the cells are **real dates** (not text).

### 10.2 Daily aggregation

> **Daily aggregation** tab.

Settings:

* **Variables to plot** (multiselect) — one or more.
* **Aggregation method** (radio) — mean or median per day.

Each variable becomes a coloured line; the X axis shows the dates with automatic formatting. For the Rio Verde dataset, with only 3 collection dates, the chart appears as 3 connected points — useful to visualise temporal evolution, but of little statistical interpretability.

### 10.3 STL decomposition

> **STL decomposition** tab.

STL decomposition (*Seasonal-Trend decomposition using LOESS*, Cleveland et al., 1990) separates a time series into three components:

* **Trend** — slow long-term variation.
* **Seasonality** — cyclical pattern that repeats with a fixed period.
* **Residual** — noise after removing trend and seasonality.

**Settings:**

* **Target variable** (default: `FCO2_DRY` if it exists, otherwise the first numeric one).
* **Seasonal period (days)** — slider 2 to 60. Default 7 (weekly seasonality).
* **Interpolate temporal gaps** (checkbox) — fills days without measurement by linear interpolation in time.

#### STL guard-rails

To avoid misleading interpretations, the app imposes **two blocks**:

![Warning of too few dates for STL](img/manual/24_temporal_stl_bloqueado.png)

| Condition | What happens |
|---|---|
| Fewer than **10 dates with a real measurement** | STL is blocked with a warning: *"Only N dates with a real measurement (minimum 10). STL decomposition requires enough points — one-off campaigns do not meet the requirement."* |
| Interpolation covers **more than 70 %** of the series | STL runs, but with a highlighted warning: the trend/seasonality strength metrics largely reflect the interpolation itself, not the observed signal. |

> **In the Rio Verde dataset:** only 3 distinct dates (Dec/2025, Jan/2026, Feb/2026) → the app blocks STL with a clear message. This is the correct behaviour; the decomposition would need monthly campaigns (~12 dates) or weekly ones (~10+) to be statistically honest.

#### Output when STL runs

When there is enough data, the page produces four stacked charts (Observed, Trend, Seasonality, Residual) and three metrics:

* **Trend strength** — `1 − Var(residual) / Var(observed − seasonal)`. Close to 1 = very clear trend.
* **Seasonality strength** — `1 − Var(residual) / Var(observed − trend)`. Close to 1 = very clear seasonality.
* **n** — number of points in the series after aggregation/interpolation.

---

## 11. Group comparison

> Page **Group comparison** in the sidebar.

This page implements the classic use case **"does Group A differ from Group B?"** with robust statistical tools. Unlike the EDA Boxplot tab (§6.4), here you have:

* **Flexible group definition** — manual choice of which values go into A and B, or pattern matching by substring.
* **Formal statistical test** — Mann-Whitney U *two-sided* for each variable.
* **Log-linear regression by group** — fits the relationship log(Y) ~ X separately in A and B.
* **Hourly pattern** — aggregates Y per hour of the day for each group (useful for daytime vs. night-time flows).

### 11.1 Group configuration

![Comparative setup: Sugarcane vs. Soybean](img/manual/25_comparativa_setup.png)

**Categorical column** — selectbox at the top. Defines which column will be partitioned into two groups. Default: `Cultura`.

**Two ways to define A and B:**

#### Manual mode (default)

Two multiselects, side by side:

* **Values in Group A** + customisable label (default: first value of the column).
* **Values in Group B** + customisable label (default: the second value).

You can assign multiple values to the same group (e.g. group "R1", "R2", "R3" into a single "Early reproductive stage").

> **Automatic validation:** if any value appears on both sides, the app shows an `st.error` and prevents you from proceeding.

#### Pattern matching mode

Check the **Classify automatically by text pattern** checkbox. A text field appears where you type a pattern (case-insensitive):

* Values that **contain** the pattern → Group A (Match).
* Values that **do not contain** it → Group B (Other).

Useful when the column has many levels (e.g. 14 phenological stages) and you quickly want to separate "everything that contains 'maturation'" from the rest. The app shows the list of each group in a caption for you to check before analysing.

#### N-per-group metrics

After configuration, two large metrics show how many rows fell into each group:

> **In the Rio Verde dataset (Unfold mode):** Sugarcane = 54, Soybean = 104. In Mean mode it would be 27 vs. 54 — keep an eye on the number because it governs the statistical power of the tests that follow.

### 11.2 Summary & test — Mann-Whitney U

> First tab inside the Comparative.

For each selected numeric variable, it returns two blocks:

**Descriptive summary table** (`group`, `variable`, `n`, `mean`, `se`, `median`):

**Mann-Whitney U test table:**

![Mann-Whitney table in the Comparative](img/manual/26_comparativa_mannwhitney.png)

| Column | Meaning |
|---|---|
| `variable` | The tested variable. |
| `g1`, `g2` | Group labels. |
| `n_g1`, `n_g2` | Size of each group. |
| `U` | Mann-Whitney statistic. |
| `p_value` | Probability under H₀ (same distribution). |
| `significant_5%` | `True` if p < 0.05. |

#### When Mann-Whitney is appropriate

| Condition | Implication |
|---|---|
| The two groups have a **similar** distribution shape | Mann-Whitney compares medians (direct interpretation). |
| Distributions have **different** shapes | Mann-Whitney compares overall distributions (rejection does not mean "different median", but "different distribution"). |
| There is **pseudoreplication** (replicates at the same site) | inflated n → artificially small p. Consider aggregating by site (Mean or Median replicate mode) before comparing. |

> **In the Rio Verde dataset:** running Sugarcane vs. Soybean on Latitude and Longitude, the p-values are of the order of 10⁻⁸ — which does **not** mean that sugarcane and soybean have "different latitudes" in the physiological sense. It means that **the two farms are in geographically distinct locations** and each has only one crop (recall the Fazenda ⟷ Cultura confounding). For a biologically meaningful finding, test physiological variables (`A`, `gs`, `E`, etc.) and read them together with the Confounding tab (§6.2).

### 11.3 Log-linear by group

> Second tab inside the Comparative.

Fits a simple linear regression on a **log(Y)** scale versus X, **separately for each group**. Useful when the Y-X relationship is exponential or multiplicative (saturation, decay).

**Settings:**

* **Y variable** (numeric) — only **strictly positive** values enter (log(0) and negative log are discarded silently).
* **X variable** (numeric).

Output: scatter coloured by group + fitted lines + a table with `intercept`, `slope`, `R²`, `p_value`, `se_slope` per group.

> **Beware when Y has values ≤ 0:** the app discards those rows before the log. If a group has many negatives (the case of FCO2_DRY in uptake, FCH4_DRY in a sink), you compare drastically different N values between groups, **compromising comparability**. Always check the `n` reported for each group in the chart.

### 11.4 Hourly pattern

> Third tab inside the Comparative.

For datasets with a **date/time** column (not just a date), it extracts the hour of each measurement and computes the mean/median of Y per hour-of-day, separately for each group.

Output: two charts side by side:

* **Left:** mean (or median) per hour, one line per group.
* **Right:** cumulative sum per hour — useful to visualise accumulated flow over the day (e.g. daytime CO₂ emission).

Table exportable as CSV.

> **In the Rio Verde dataset:** the `Data da coleta` column only has the date part (no hour), so all measurements fall on hour `00:00`. The tab looks visually empty, except for the single bar at zero. In soil-flux datasets with a complete timestamp (IRGA measuring every 1-2 hours) the tab is much more useful.

---

## 12. Experimental Statistics (designs)

> Page **Experimental Statistics** in the sidebar.

A **generic** experimental-design tool — works with any dataset, not just physiology. You map columns to *roles* (response, treatment, block, factors) and the tool infers the design, fits the ANOVA, checks assumptions and compares means. Inspired by the *Estatística Experimental no Rbio* workflow (Bhering & Teodoro).

> **Validation:** the analyses were checked **number-by-number against R** (`aov`, `car::Anova` type II, `emmeans`, the `ScottKnott` package). See [`docs/validacao_externa.md`](validacao_externa.md).

The page has three modes (selector at the top):

### 12.1 Design mode (ANOVA)

Map the columns:

* **Response variable** — numeric (e.g. yield, `A`).
* **Treatment** — main factor (categorical). Low-cardinality numeric columns can be promoted to a factor via *"Treat as factor"*.
* **Block / replicate** (optional) → block design.
* **2nd and 3rd factor** (optional) → factorial scheme with interactions.
* **Covariate** (optional, numeric) → ANCOVA (adjusted means).

The **design is auto-detected**:

| Mapped columns | Design |
|---|---|
| Treatment | **CRD** (completely randomised design) |
| Treatment + block | **RCBD** (randomised complete block design) |
| Treatment + 2nd (and 3rd) factor | **Factorial** (with interactions) |
| Treatment + row + column | **Latin square** |

**Composite-error designs** (their own expander, with priority): **split-plot**, **strip-plot** and **nested** — each with its multiple error terms and F-tests using the correct denominator.

Four result tabs:

1. **ANOVA** — full table (df, SS, MS, F, p-value), experimental **CV%** and automatic interpretation of the terms.
2. **Assumptions** — Shapiro-Wilk (residual normality) and Levene (homoscedasticity), with Q–Q plot and residuals × fitted chart.
3. **Mean comparison** — choice of method: **Tukey, Scott-Knott, Duncan, Scheffé, LSD/DMS** (with significance letters and bar chart), or **Dunnett** (each treatment vs. a control). In ANCOVA, means are adjusted by the covariate.
4. **Reproducibility** — code snippet + button to **download the full Python script** that reproduces the analysis, plus the data CSV.

![ANOVA table of a split-plot design (Yates oats data): the whole-plot factor (`gen`) is tested against Error(a) and the subplot factor (`nitro`) against Error(b), with separate CV(a) and CV(b). The F values reproduce R exactly.](img/manual/27_experimental_anova.png)

### 12.2 Dose regression

For a **quantitative** factor (fertiliser dose, irrigation depth, density…): polynomial fit (linear, quadratic or cubic) with R², adjusted R², significance of the highest-order term and an observed + fitted-curve chart.

### 12.3 Correlation

**Pearson** or **Spearman** correlation matrix (heatmap + p-values), with download, and **partial correlation** (controlling for covariates).

---

## 13. Statistical glossary

Short definitions of the technical terms used in the manual. For more depth, see the References (§15).

* **Anderson-Darling** — normality test sensitive to deviations in the tails. Returns an A² statistic and a critical value at 5 %; rejects if A² > critical.
* **Cramér's V** — measure of association between two categorical variables, in the range [0, 1]. V=1 indicates perfect equivalence; used in the app to detect confounding.
* **D'Agostino-Pearson (K²)** — normality test that combines skewness and kurtosis. Robust to ties; recommended for moderate n.
* **Elliptic Envelope** — outlier-detection method that assumes **multivariate normality**. Unreliable on bimodal or strongly skewed data.
* **Getis-Ord Gi*** — local statistic that classifies each point as a hotspot (cluster of highs), coldspot (cluster of lows) or not significant, based on its neighbourhood via a distance band.
* **GroupKFold** — cross-validation variant that keeps all rows of the same "group" (site, farm, point) in the same fold. Avoids inflating R² when there is pseudoreplication.
* **IDW (Inverse Distance Weighting)** — deterministic interpolation that estimates each grid point as a weighted average of the sampled points, with weight ∝ 1/distance^power.
* **Isolation Forest** — outlier-detection algorithm based on random trees. Non-parametric, scales well to many dimensions.
* **Kruskal-Wallis (KW)** — non-parametric test that compares distributions across 2 or more groups. Equivalent to Mann-Whitney when there are exactly 2 groups.
* **Ordinary kriging** — **statistical** interpolation based on the spatial structure of the data, fitted via a variogram. Returns estimates + uncertainty.
* **LISA (Local Indicators of Spatial Association)** — local version of Moran's I; classifies each point as HH, HL, LH, LL or NS according to its value and that of its neighbourhood.
* **LOF (Local Outlier Factor)** — outlier method based on local density. Flags points whose neighbourhood is less dense than that of their neighbours.
* **Mann-Whitney U** — non-parametric test to compare two independent samples. Equivalent to Kruskal-Wallis with k=2.
* **Moran's I** — global spatial-autocorrelation index, in the range [-1, +1]. Positive → similar values cluster in space.
* **Pearson (r)** — linear correlation coefficient. Sensitive to outliers; assumes a linear relationship.
* **Pseudoreplication** — when replicates (measurements) of the same site are treated as independent observations. Inflates the effective n and yields optimistic p-values.
* **Q-Q plot** — chart that compares the sample quantiles to the theoretical normal ones. Points aligned on the diagonal indicate visual normality.
* **Shapiro-Wilk (W)** — normality test. The most sensitive for n < 5000; literature standard.
* **Spearman (ρ)** — rank correlation coefficient. Robust to outliers and captures non-linear monotonic relationships.
* **STL (Seasonal-Trend decomposition using LOESS)** — decomposes a time series into trend, seasonality and residual via robust local regression.
* **UTM (Universal Transverse Mercator)** — cartographic projection system in metres. Rio Verde, Goiás lies in zone 22 South (EPSG 32722).
* **Variogram** — function that describes the semivariance between pairs of points as a function of distance. Parameters: nugget (variance at h=0), sill (asymptote) and range (distance at which it stabilises).
* **VIF (Variance Inflation Factor)** — measures multicollinearity. VIF=1/(1-R²) where R² comes from regressing the variable against all the others. VIF ≥ 10 indicates severe collinearity.
* **Z-score** — number of standard deviations above/below the mean. The |z|>3 criterion flags outliers; **non-robust** (the outlier itself inflates the standard deviation).

---

## 14. Troubleshooting (FAQ)

### "`sidebar.rep.media` (or another raw key) appears instead of the translated text"

Streamlit caches the translations module on the first import. If you updated the app after the server was already running, the new keys do not appear until you restart. **Solution:** `Ctrl+C` in the terminal and `python -m streamlit run app.py` again.

### "The pipeline emptied my dataset (or removed almost everything)"

Go to **Pipeline and Processing** and read the highlighted yellow warning. The cause is almost always step 2 — one of the required columns (`Cultura`, `Uso atual` or `Época`) is empty in many rows. Go back to Excel, identify which column is missing, and redo the upload with the corrected spreadsheet.

### "The Time Series page says 'Date column not found'"

Check in Excel whether your column is named `Data da coleta`, `Data`, `Date`, `DATE_TIME initial_value` or some recognised variant (full list in [`docs/data_dictionary.md`](data_dictionary.md)). If the name is correct, open the column and check whether the cells are **real dates** (Excel shows `2025-12-19` aligned to the right) and not **text** ("2025-12-19" aligned to the left). Save the file and reload.

### "GroupKFold reduced my folds automatically"

It means that the number of unique groups in the chosen column is smaller than the number of folds you configured. For example: you asked for 5 folds, but there are only 4 farms — the app adjusts to 4 folds. If you want to keep the 5 folds, choose a grouping column with more levels (e.g. `Fazenda + Ponto` instead of just `Fazenda`).

### "Some variables show an infinite or astronomical VIF"

This is expected for **variables mathematically derived** from others: `Ci/Ca` is Ci divided by Ca (with Ca nearly constant, it becomes a rescaling of Ci); `EUA = A/E`; `A/Ci` is a ratio; `ETR` is a function of YII. A high VIF among these indicates multicollinearity **by construction**, not a data problem. Include only one representative of the derived pair in the models.

### "Moran's I came out at 0.9 — is my data extremely spatially clustered?"

Before celebrating the discovery of a cluster, check the **EDA Quality → Confounding between categories** tab. If `Fazenda ⟷ Cultura` (or similar) appears as redundant, the Moran's I is capturing a **biological difference between crops** more than true spatial autocorrelation. Redo the Moran filtering for a single crop via the global filter, and see whether the index stays high.

### "The kriging variogram does not stabilise"

Your dataset probably has **no detectable spatial structure** at the scale of the experiment (too few sample points, or a variable dominated by factors other than position). Do not run the kriging in this situation — the fitted parameters (range in millions of metres) are numerically valid but statistically useless. Consider going back to IDW (§9.1) or reviewing the collection.

### "The `Replicate 1`, `Replicate 2` and `Replicate 3` modes seem to give different results for Chl a and b"

They really are different — each one takes a specific measurement from the spreadsheet. `Replicate 1` uses the original `Chl a` column; `Replicate 2` uses `Chl a.1`. **Replicate 3 leaves Chl a/b empty** (only `IAF.2` exists, not `Chl a.2`). Use these modes when you want to audit/compare specific readings; for normal analysis, use **Mean** or **Median**.

---

## 15. References

### Statistical methods

* Anderson, T. W., & Darling, D. A. (1952). Asymptotic theory of certain "goodness of fit" criteria based on stochastic processes. *Annals of Mathematical Statistics*, 23(2), 193-212.
* Bergsma, W., & Wicher, M. (2013). A bias-correction for Cramér's V and Tschuprow's T. *Journal of the Korean Statistical Society*, 42(3), 323-328.
* Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on loess. *Journal of Official Statistics*, 6(1), 3-73.
* D'Agostino, R. B., Belanger, A., & D'Agostino Jr., R. B. (1990). A suggestion for using powerful and informative tests of normality. *American Statistician*, 44(4), 316-321.
* Getis, A., & Ord, J. K. (1992). The analysis of spatial association by use of distance statistics. *Geographical Analysis*, 24(3), 189-206.
* Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *JASA*, 47(260), 583-621.
* Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. *Annals of Mathematical Statistics*, 18(1), 50-60.
* Moran, P. A. P. (1948). The interpretation of statistical maps. *Journal of the Royal Statistical Society, Series B*, 10(2), 243-251.
* Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality. *Biometrika*, 52(3-4), 591-611.

### Outliers and modelling

* Breunig, M. M., Kriegel, H. P., Ng, R. T., & Sander, J. (2000). LOF: Identifying density-based local outliers. *SIGMOD Record*, 29(2), 93-104.
* Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. *ICDM*, 413-422.
* Rousseeuw, P. J., & van Driessen, K. (1999). A fast algorithm for the minimum covariance determinant estimator. *Technometrics*, 41(3), 212-223.

### Plant physiology

* Farquhar, G. D., von Caemmerer, S., & Berry, J. A. (1980). A biochemical model of photosynthetic CO₂ assimilation in leaves of C3 species. *Planta*, 149(1), 78-90.

### Libraries

* McKinney, W. (2010). pandas — Data analysis with Python. <https://pandas.pydata.org>
* Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. *JMLR*, 12, 2825-2830.
* Rey, S. J., & Anselin, L. (2010). PySAL: A Python library of spatial analytical methods. <https://pysal.org>
* Seabold, S., & Perktold, J. (2010). statsmodels: Econometric and statistical modeling. <https://www.statsmodels.org>
* Streamlit Inc. (2024). Streamlit. <https://streamlit.io>
* Virtanen, P. et al. (2020). SciPy 1.0. *Nature Methods*, 17, 261-272.

## 16. Contributing

Found a bug, have a feature request, or want to add a new analysis?

### 16.1 Reporting bugs and proposing features

Open an issue on the project GitHub repository. Include:

1. **App version** (check the footer or `pyproject.toml`).
2. **Steps to reproduce** — always start with "I went to tab X, clicked Y, expected Z but saw W".
3. **Screenshot** (if it is a visual problem).
4. **Dataset snippet** (anonymised) that triggers the problem, whenever possible.

### 16.2 Contributing code

* See [`docs/contributing.md`](contributing.md) for the PR workflow and testing standards.
* See [`docs/architecture.md`](architecture.md) to understand the layout of the modules.
* See [`docs/i18n.md`](i18n.md) to add a new language or extend the translations.

### 16.3 Building this manual as PDF

The canonical source of this manual is the Markdown file you are reading (`docs/manual.pt.md`). The PDF is a derivative, generated by [pandoc](https://pandoc.org/) + XeLaTeX.

#### Locally

```bash
# 1) Prerequisites (once per machine)
brew install pandoc                       # macOS
brew install --cask basictex
sudo tlmgr install fancyhdr xurl booktabs longtable

# Ubuntu equivalent:
# sudo apt-get install pandoc texlive-xetex \
#   texlive-fonts-recommended texlive-latex-recommended

# 2) Generate the PDF
scripts/build_manual_pdf.sh                       # → docs/manual.pt.pdf
scripts/build_manual_pdf.sh --lang en             # when manual.en.md exists
scripts/build_manual_pdf.sh --output /tmp/x.pdf   # custom path
```

The PDF is generated at `docs/manual.<lang>.pdf` and `.gitignore` prevents it from being committed by accident.

#### Via GitHub Actions

The [`build-manual.yml`](../.github/workflows/build-manual.yml) workflow generates the PDF automatically:

* **Push to a `v*` tag** — attaches the PDF as an artifact of the corresponding release.
* **Changes in `docs/manual.*.md`** or in the screenshots — runs the build to validate that nothing broke.
* **Manual execution** — go to *Actions → Build manual PDF → Run workflow* and choose the language.

The artifacts are available for 30 days and can be downloaded without needing to install pandoc locally.

### 16.4 Translating to other languages

The skeleton of this manual is ready to receive English and Spanish mirrors:

```bash
cp docs/manual.pt.md docs/manual.en.md
cp docs/manual.pt.md docs/manual.es.md
```

Translate the content while keeping the heading structure. The images in `docs/img/manual/` are shared between the three languages — you only need one copy.

---

*End of manual. Version 1.0 — aligned with application 1.x.*
