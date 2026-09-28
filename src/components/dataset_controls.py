from __future__ import annotations

import pandas as pd
import streamlit as st

from src.i18n import t
from src.state import get_active_dataframe, get_raw_dataframe


def ensure_raw_dataframe(warning_message: str) -> pd.DataFrame | None:
    df_raw = get_raw_dataframe()
    if df_raw is None:
        st.warning(warning_message)
    return df_raw


def render_dataset_source_toggle(toggle_key: str, default: bool = True) -> pd.DataFrame | None:
    use_processed = st.toggle(t("dataset.use_processed"), value=default, key=toggle_key)
    return get_active_dataframe(use_processed)
