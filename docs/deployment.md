# Deployment

This document covers two scenarios:

1. **Local installation** — for individual researchers and reviewers.
2. **Multi-user institutional deployment** — with Supabase authentication.

For a Docker-based one-command deployment, see the v1.1 roadmap.

## 1. Local installation

### Requirements

- **Python 3.10+** (3.11 and 3.12 also work).
- On Windows, `geopandas`, `geobr`, `libpysal` and `esda` rely on **GDAL**.
  We recommend the Conda route to avoid binary issues — see below.

### Option A — `pip` venv (recommended for v1.0; Linux/macOS/Windows)

```bash
git clone https://github.com/ML-Carbon-Project/physioFlow.git
cd physioflow
python3.10 -m venv .venv
source .venv/bin/activate         # or .venv\Scripts\Activate.ps1 on Windows
pip install -U pip wheel
pip install -r requirements.txt
python -m streamlit run app.py
```

Modern pip wheels for `shapely>=2`, `pyproj`, `pyogrio` and `geopandas>=1`
are self-contained on Windows (no system GDAL needed); `libpysal`, `esda`
and `geobr` install cleanly from PyPI as well. The full stack downloads in
about 1–2 minutes on a typical broadband connection.

### Option B — Conda fallback

If a wheel is unavailable for your platform/Python combination:

```bash
conda create -n goiasverde -c conda-forge python=3.11 \
    geopandas shapely libpysal esda statsmodels scipy streamlit pytest
conda activate goiasverde
pip install streamlit-option-menu supabase geobr
python -m streamlit run app.py
```

> Note: the Conda solver may take 10+ minutes on Windows when installing the
> geo stack into an existing `base` env. Creating a fresh env (as above) is
> usually faster than mutating `base`.

### Smoke test

```bash
pytest tests/ -v          # 40 passed
python -m streamlit run app.py
```

The default port is 8501. Open `http://localhost:8501` in your browser.

## 2. Institutional deployment with Supabase auth

### a. Create a Supabase project

1. Go to <https://supabase.com> and create a project.
2. Under *Project Settings → API*, copy the **Project URL** and the
   **anon public** (also called *publishable*) API key.
3. Enable the *Authentication → Providers → Email* provider.

### b. Configure secrets

Copy the example file and fill the values:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
[supabase]
url = "https://YOUR-PROJECT.supabase.co"
publishable_key = "YOUR-ANON-PUBLIC-KEY"
```

### c. Configure the role mapping

The application maps the Supabase `user_metadata.role` field to a UI label
(`administrator` vs `user`). Set the metadata via the Supabase dashboard or
via the API after sign-up.

### d. Run the app

```bash
python -m streamlit run app.py
```

When `secrets.toml` is present, the login gate is shown automatically. The
five-minute session-validation cache (`AUTH_VALIDATION_TTL_SECONDS = 300` in
`src/config/settings.py`) reduces network calls.

### e. Hosting options

- **Streamlit Community Cloud** — free, integrates with GitHub. Add the
  Supabase secrets to the *Secrets* panel of the deployed app.
- **Self-hosted (Docker, VPS)** — see `docs/contributing.md` for the
  v1.1 Docker image roadmap.
- **Behind a reverse proxy (Nginx)** — Streamlit's default settings
  (`server.headless = true`, `server.enableCORS = false`) work behind a
  proxy serving `/`. WebSocket support (`/_stcore/stream`) must be
  proxied for the live updates.

## Resetting state

To wipe the local state and restart from a clean slate:

```bash
streamlit cache clear
rm -rf .streamlit/.cache
```

Re-uploading a file is enough to refresh the session state.

## Environment variables

| Variable                | Purpose                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| `STREAMLIT_SERVER_PORT` | Override the default port (8501)                                     |
| `STREAMLIT_SERVER_HEADLESS` | Set to `true` for production deployments                          |
| `GOIAS_VERDE_DEFAULT_LANG` | Currently not respected; planned for v1.1                         |

## Troubleshooting

- **`ImportError: libgdal.so.X` on Linux** — install the system package
  `gdal-bin libgdal-dev` (Ubuntu/Debian) or `gdal` (Fedora) before
  `pip install`.
- **`ModuleNotFoundError: streamlit_option_menu`** — re-run
  `pip install -r requirements.txt`; the package is required for the
  sidebar menu.
- **Slow first run of the Spatial page** — the first call to
  `geobr.read_municipality` downloads the boundary shapefile and caches
  it under `~/.cache/geobr/`. Offline use is supported after the first
  successful download.
- **Anaconda Windows: `ImportError: DLL load failed while importing
  pyexpat`** — usually caused by an interrupted `conda update` that left
  a trashed DLL. Look for a file named `libexpat.dll.c~.conda_trash`
  under `C:\Users\<you>\anaconda3\Library\bin\`. If it exists, simply
  rename it back to `libexpat.dll`. After that both `pip` and
  `pandas.read_excel` recover. If the file is gone, run
  `conda install -n base -c conda-forge --force-reinstall libexpat python`
  to regenerate it.
- **`pip install geobr` is needed even after Conda** — `geobr` is
  pip-only and not available in conda-forge. After
  `conda install -c conda-forge geopandas shapely libpysal esda`, run
  `pip install geobr` to add it.
- **`pip install` itself fails with the pyexpat error above** — pip uses
  `xml.parsers.expat`. Fix the `libexpat.dll` issue first; pip recovers
  immediately afterwards.
