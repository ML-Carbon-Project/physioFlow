# Contributing

Thanks for considering a contribution. The project is small, opinionated and
intentionally keeps the runtime in a single Streamlit process.

## Setup

```bash
git clone https://github.com/danielhilario-if/physioflow.git
cd physioflow
python3.10 -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\Activate.ps1 on Windows
pip install -U pip wheel
pip install -r requirements.txt
pytest tests/ -v             # expect 40 passed
```

If GDAL fails on Windows, see `docs/deployment.md` for the Conda route.

## Adding a new analysis page

1. Create `src/pages/<your_page>.py` with a top-level `render() -> None`.
2. Register it in `src/pages/__init__.py::PAGE_RENDERERS`.
3. Add a `NavigationItem` to `src/config/settings.py::NAVIGATION_ITEMS`.
4. Add **all** strings to `src/i18n/locales/pt.json`, then mirror them in
   `en.json` and `es.json`. Run `python -m scripts.i18n_audit` to verify
   parity.
5. Use `ensure_raw_dataframe(...)` and `render_dataset_source_toggle(...)`
   at the start of `render()` so users can switch between raw and processed
   data.
6. Heavy operations should be cached with `@st.cache_data` — see
   `_load_rio_verde_boundary()` in `src/pages/spatial.py` for an example.

## Adding a new pipeline step

1. Implement the cleaning primitive in `src/pipeline.py` returning
   `(DataFrame, StepLog)`. The function must be pure: take a dataframe in,
   return a new dataframe; never mutate the input.
2. Add a UI block to `src/pages/pipeline.py::render`. Wrap the controls in
   the existing `st.form`; gate the call by a `st.checkbox`.
3. Translate every UI string (pt/en/es).
4. Add unit tests under `tests/test_<your_step>.py` covering both the
   happy path and the edge cases (missing column, no valid columns,
   NaN preservation, etc.).
5. If the step adds a new column to `df_processed`, update the EDA
   defaults in `src/config/settings.py`.

## Adding a new schema column

1. Append a `ColumnSpec(...)` entry to `SCHEMA_SPECS` in `src/schema.py`,
   choosing the right tier (`required` only if the app cannot work
   without it).
2. Update `tests/test_schema.py` to cover the new column.
3. Document the column in `docs/architecture.md`.

## Code style

- Python 3.10+ syntax (`from __future__ import annotations`).
- Type hints on public functions; not strictly required on local helpers.
- Docstrings only when the *why* is non-obvious. Names should carry the
  *what*.
- `seaborn`/`matplotlib` for static plots; we deliberately avoid Plotly
  to keep the bundle small. Streamlit-native widgets where possible.

## Tests

- All cleaning primitives and the schema validator must have unit tests.
- UI interactions are not unit-tested (Streamlit makes this hard); rely
  on smoke tests during the PR review.
- Aim to keep the suite under one second on CI.

## Translating

- Translations live in `src/i18n/locales/{pt,en,es}.json`.
- Portuguese is the reference: every key must exist in `pt.json`.
- English and Spanish must mirror the keys exactly. Run the audit
  script before opening a PR:
  ```bash
  python -m scripts.i18n_audit
  ```

## Commit and PR conventions

- Conventional-style messages are appreciated but not enforced
  (`feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `test: ...`).
- Keep PRs focused. A new analysis page in one PR; a new pipeline step
  in another.
- Include a screenshot in the PR description for visual changes.
- Run `pytest tests/ -v` before pushing.

## Roadmap (v1.1+)

- Folium-based interactive map for LISA classes.
- Replace ad-hoc ordinary kriging with `skgstat` or `pykrige`.
- Empirical Bayesian kriging.
- Public Docker image for one-command deployment.
- Direct ingestion of LI-COR JSON exports without spreadsheet
  intermediation.
- N₂O-aware validation rules for the LI-7820.

## Reporting bugs

Open an issue at
<https://github.com/danielhilario-if/physioflow/issues> with:

- Streamlit and Python versions (`streamlit --version`, `python --version`).
- The first 20 rows of the dataset (or the *Schema validation* CSV
  download from the Upload page).
- The exact error message and the navigation steps to reproduce it.
