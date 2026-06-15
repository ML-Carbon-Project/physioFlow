from __future__ import annotations

from dataclasses import dataclass

APP_PAGE_TITLE = "Goias Verde - Fisiologia Vegetal"
APP_LAYOUT = "wide"
APP_SIDEBAR_TITLE = "Projeto Goias Verde"
PRIMARY_COLOR = "#1b4d3e" # Premium Forest Green
AUTH_VALIDATION_TTL_SECONDS = 300

SESSION_RAW_KEY = "df_raw"
SESSION_PROCESSED_KEY = "df_processed"
SESSION_REPORT_KEY = "df_report"
SESSION_AUTH_ACCESS_TOKEN_KEY = "auth_access_token"
SESSION_AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token"
SESSION_AUTH_USER_KEY = "auth_user"
SESSION_AUTH_VALIDATED_AT_KEY = "auth_validated_at"

# Chave para guardar o tratamento das replicas
SESSION_REP_METHOD_KEY = "rep_method"

SIDEBAR_CSS = """
<style>
/* Sidebar Container Background & Border */
section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border-color, rgba(0, 0, 0, 0.1));
    background: linear-gradient(180deg, rgba(27, 77, 62, 0.15) 0%, rgba(27, 77, 62, 0.0) 100%), var(--secondary-background-color) !important;
}

/* CEAGRE Project Title */
.ceagre-title {
    font-size: 0.95rem;
    color: var(--primary-color) !important;
    margin-top: 0.25rem;
    margin-bottom: 0.8rem;
    text-align: center;
    font-weight: 700;
    letter-spacing: 0.5px;
}

/* Ensure language label and selectbox text are always readable based on theme colors */
section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
    color: var(--text-color) !important;
}

/* Ensure the selected option in the selectbox has correct theme color */
section[data-testid="stSidebar"] div[data-baseweb="select"] {
    color: var(--text-color) !important;
}

/* Option Menu - styling navigation links to adapt to theme */
div[data-testid="stSidebar"] .nav-link {
    color: var(--text-color) !important;
}
div[data-testid="stSidebar"] .nav-link:hover {
    background-color: rgba(27, 77, 62, 0.12) !important;
    color: var(--primary-color) !important;
}
</style>
"""


@dataclass(frozen=True)
class NavigationItem:
    key: str
    label_key: str  # i18n key resolved at render time via src.i18n.t()
    icon: str


NAVIGATION_ITEMS = [
    NavigationItem(key="upload", label_key="nav.upload", icon="cloud-arrow-up"),
    NavigationItem(key="pipeline", label_key="nav.pipeline", icon="sliders"),
    NavigationItem(key="eda", label_key="nav.eda", icon="bar-chart"),
    NavigationItem(key="regression", label_key="nav.regression", icon="graph-up-arrow"),
    NavigationItem(key="modeling", label_key="nav.modeling", icon="cpu"),
    NavigationItem(key="spatial", label_key="nav.spatial", icon="geo-alt"),
    NavigationItem(key="timeseries", label_key="nav.timeseries", icon="clock-history"),
    NavigationItem(key="comparative", label_key="nav.comparative", icon="bar-chart-steps"),
    NavigationItem(key="experimental", label_key="nav.experimental", icon="diagram-3"),
]

PIPELINE_DROP_CANDIDATES = [
    "Textura",
    "Manejo",
    "Estágio",
]

EDA_DEFAULT_DISTRIBUTION_COLUMNS = ["A", "E", "gs", "Chl_a_media", "Chl_b_media", "IAF_media"]
EDA_DEFAULT_PAIR_COLUMNS = ["A", "gs", "E", "Ci", "Chl_a_media", "IAF_media"]

REGRESSION_PRESETS = [
    ("Condutância Estomática (gs) vs. Fotossíntese (A)", "gs", "A", "Cultura"),
    ("CO2 Interno (Ci) vs. Fotossíntese (A)", "Ci", "A", "Cultura"),
    ("Condutância Estomática (gs) vs. Transpiração (E)", "gs", "E", "Cultura"),
    ("Clorofila a vs. Fotossíntese (A)", "Chl_a_media", "A", "Cultura"),
]

MODEL_DEFAULT_FEATURES = [
    "gs",
    "Ca",
    "Ci",
    "Ci/Ca",
    "E",
    "YII",
    "ETR",
    "Chl_a_media",
    "Chl_b_media",
    "IAF_media",
    "Cultura",
    "Fazenda",
    "Época",
]
