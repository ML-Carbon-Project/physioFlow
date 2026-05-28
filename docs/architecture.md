# Architecture

`physioflow` is a single-page Streamlit application backed by a
small Python package under `src/`. The runtime is a single process; data is
held in `st.session_state` and cached with `@st.cache_data` to avoid re-parsing
files between page navigations.

## Module layout

```
src/
├── auth.py                # Optional Supabase login layer
├── components/            # Reusable UI components
│   ├── dataset_controls.py
│   └── sidebar.py
├── config/
│   └── settings.py        # NavigationItem, primary color, default columns
├── i18n/
│   ├── translations.py    # Loader + AVAILABLE_LANGUAGES dict
│   └── locales/{pt,en,es}.json
├── ml/
│   └── model_registry.py  # Wraps scikit-learn estimators in a registry
├── pages/                 # One module per left-menu entry
│   ├── upload.py
│   ├── pipeline.py
│   ├── eda.py
│   ├── regression.py
│   ├── modeling.py
│   ├── spatial.py
│   ├── timeseries.py
│   └── comparative.py
├── pipeline.py            # Pure-function cleaning primitives
├── schema.py              # Upload-time schema validation
└── state.py               # Session-state helpers
```

The entry point `app.py` reads the navigation selection from
`src/config/settings.py::NAVIGATION_ITEMS`, routes the request to a
`render()` function in the matching `src/pages/` module, and delegates
authentication to `src.auth` when enabled.

## Page responsibilities

| Page              | Module                         | Purpose                                                                       |
| ----------------- | ------------------------------ | ----------------------------------------------------------------------------- |
| Upload            | `pages/upload.py`              | File ingestion, schema validation, in-memory caching                          |
| Pipeline          | `pages/pipeline.py`            | Configurable cleaning steps (drop, diagnostic, R², CV/threshold, outliers, Q10–Q90, REP) |
| EDA               | `pages/eda.py`                 | 12 tabs: descriptives, quality, distributions, boxplots, scatter, correlation, spatial, temporal, composition, inference, hotspots, outliers |
| Regression        | `pages/regression.py`          | Bivariate presets + free regression                                           |
| Modeling          | `pages/modeling.py`            | Holdout + CV comparison of five sklearn estimators                            |
| Spatial Analysis  | `pages/spatial.py`             | IDW, Moran's I/LISA, Getis-Ord G\*, UTM grid, ordinary kriging, geobr basemap |
| Time Series       | `pages/timeseries.py`          | Daily aggregation + STL decomposition                                         |
| Group comparison  | `pages/comparative.py`         | Two-group summary, log-linear regression, hourly cumulative profile           |

## Data flow

```
                 ┌──────────────┐
   user upload → │ Upload page  │ → set_loaded_dataset()
                 └──────┬───────┘
                        │ session_state["df_raw"]
                        ▼
                 ┌──────────────┐
                 │ Pipeline page│ → set_processed_dataset()
                 └──────┬───────┘
                        │ session_state["df_processed"]
                        ▼
   any of: EDA, Regression, Modeling, Spatial, Time Series, Comparative
```

Pages always read from `session_state` via `state.get_active_dataframe(...)`,
toggling between *raw* and *processed* using the dataset toggle defined in
`components/dataset_controls.py`.

## Cleaning primitives (`src/pipeline.py`)

The data cleaning and processing pipeline is implemented in `clean_fisiologia_data(df, rep_method) -> (DataFrame, list[StepLog])`. It processes the uploaded dataset through 4 key sequential steps, returning the cleaned DataFrame and log details:

| Step / Phase | Description |
|---|---|
| **1. Text Standardization** | Trims leading/trailing whitespace from categorical fields (`Cultura`, `Uso atual`, `Época`, `Fazenda`, `Município`, `Estágio`) and coerces empty or `"nan"` strings to actual `NaN` values. |
| **2. Essential Metadata Filter** | Removes rows where crucial metadata fields (`Cultura`, `Uso atual`, `Época`) are empty, ensuring all samples belong to a valid crop, management style, and collection period. |
| **3. Empty Grid Points Filter** | Removes empty rows where all 13 core physiological parameters (`A`, `E`, `gs`, `Ca`, `Ci`, `Ci/Ca`, `EUA`, `A/Ci`, `YII`, `ETR`, `Chl a`, `Chl b`, `IAF`) are null. |
| **4. Replicate Treatment** | Consolidates or expands replicates for Chlorophyll (`Chl a`, `Chl b`) and LAI (`IAF`) based on the chosen mode: **Média** (averages reps), **Desdobrar** (expands reps into individual rows), or **Réplica 1/2/3** (selects a specific rep). |

## Schema validator (`src/schema.py`)

`SCHEMA_SPECS` declares 31 expected columns tiered as **required**, **recommended**, or **optional**, specifying their expected types (`numeric`, `categorical`, `datetime`).

* **Required:** Metadata fields essential for the core filters (`Cultura`, `Uso atual`, `Época`).
* **Recommended:** Key physiological variables (`A`, `E`, `gs`, `Ca`, `Ci`, `Ci/Ca`, `EUA`, `A/Ci`, `YII`, `ETR`, `Chl a`, `Chl b`, `IAF`), plus location fields (`Fazenda`, `Município`).
* **Optional:** Geographic coordinates (`Latitude`, `Longitude`), collection date (`Data da coleta`), phenological stage (`Estágio`), dry weight (`Peso Seco`), replicate columns (`Chl a.1`, `Chl b.1`, `IAF.1`, `IAF.2`), and future filters (`Manejo`, `Textura`).

`validate_dataframe(df) -> ValidationResult` runs type check and range validations:
1. **Type coercion check:** Verifies if at least 90% of numeric/datetime values can be coerced.
2. **Coordinate range check:** Verifies that Latitude is in `[-90, 90]` and Longitude in `[-180, 180]`.

## State (`src/state.py`)

Three keys in `st.session_state`:

- `df_raw` — raw upload (after sheet selection).
- `df_processed` — current pipeline output.
- `df_report` — step-by-step report dataframe.

Plus auth keys when Supabase is enabled.

## i18n (`src/i18n/`)

`t("key.path", **kwargs)` resolves keys against `pt.json`, falling back to the key string when missing.

## Spatial implementation notes

The Spatial page uses the following dependencies:

- `geopandas` + `shapely`: vectors, reprojection (UTM grid).
- `geobr.read_municipality(code_muni=5218805, year=2020)`: Rio Verde boundary, cached with `@st.cache_data`. Requires internet on first use.
- `libpysal.weights.KNN`: k-nearest-neighbour spatial weights.
- `esda.moran.{Moran, Moran_Local}`, `esda.getisord.G_Local`: global and local autocorrelation.
- `scipy.optimize.least_squares`: variogram fitting (manual ordinary kriging).

The UTM EPSG code is computed from the mean longitude (`32700 + zone` for the southern hemisphere), so the page works elsewhere in South America without code changes.

## Testing

`tests/` uses pytest to validate the functionality of the schema and processing components:

- `test_pipeline.py` — covers the cleaning steps, standardizations, and replica consolidation/expansion.
- `test_schema.py` — verifies schema-validator coverage (type mismatch, missing columns, coordinate range, empty dataframes).

All tests run successfully using:
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```

