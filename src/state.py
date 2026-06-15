from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import streamlit as st

from src.config.settings import SESSION_PROCESSED_KEY, SESSION_RAW_KEY, SESSION_REPORT_KEY
from src.pipeline import available_excel_sheets, load_uploaded_file


class _UploadedBytesIO(io.BytesIO):
    def __init__(self, file_bytes: bytes, name: str):
        super().__init__(file_bytes)
        self.name = name


@st.cache_data(show_spinner=False)
def load_data(
    file_bytes: bytes,
    file_name: str,
    sheet_name: Optional[str],
    delimiter: str = "auto",
) -> pd.DataFrame:
    return load_uploaded_file(
        _UploadedBytesIO(file_bytes, file_name),
        sheet_name=sheet_name,
        delimiter=delimiter,
    )


@st.cache_data(show_spinner=False)
def get_excel_sheets(file_bytes: bytes, file_name: str) -> list[str]:
    return available_excel_sheets(_UploadedBytesIO(file_bytes, file_name))


def set_loaded_dataset(df_raw: pd.DataFrame):
    st.session_state[SESSION_RAW_KEY] = df_raw
    st.session_state[SESSION_PROCESSED_KEY] = df_raw.copy()
    st.session_state[SESSION_REPORT_KEY] = pd.DataFrame()


def set_processed_dataset(df_processed: pd.DataFrame, df_report: pd.DataFrame):
    st.session_state[SESSION_PROCESSED_KEY] = df_processed
    st.session_state[SESSION_REPORT_KEY] = df_report


def get_raw_dataframe() -> Optional[pd.DataFrame]:
    return st.session_state.get(SESSION_RAW_KEY)


def get_processed_dataframe() -> Optional[pd.DataFrame]:
    return st.session_state.get(SESSION_PROCESSED_KEY)


def get_report_dataframe() -> pd.DataFrame:
    return st.session_state.get(SESSION_REPORT_KEY, pd.DataFrame())


def get_active_dataframe(use_processed: bool) -> Optional[pd.DataFrame]:
    if use_processed:
        df_processed = get_processed_dataframe()
        if df_processed is not None:
            return df_processed
    return get_raw_dataframe()
