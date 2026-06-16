from __future__ import annotations

import pandas as pd
import streamlit as st

from src.i18n import t
from src.profile import (
    PROFILE_AUTO,
    PROFILE_OPTIONS,
    get_profile_setting,
    is_physiology,
    resolve_profile,
    set_profile_setting,
)
from src.schema import validate_dataframe
from src.state import get_excel_sheets, get_raw_dataframe, load_data, set_loaded_dataset

_TIER_ORDER = ("required", "recommended", "optional")
_TIER_LABEL_KEY = {
    "required": "upload.schema.tier_required",
    "recommended": "upload.schema.tier_recommended",
    "optional": "upload.schema.tier_optional",
}
_STATUS_LABEL_KEY = {
    "present": "upload.schema.status_present",
    "missing": "upload.schema.status_missing",
    "type_mismatch": "upload.schema.status_type_mismatch",
    "empty": "upload.schema.status_empty",
}


def _render_generic_summary(df: pd.DataFrame) -> None:
    """Resumo neutro para datasets não-fisiológicos (sem schema do domínio)."""
    numeric = df.select_dtypes(include="number").columns
    categorical = [c for c in df.columns if c not in numeric]
    st.markdown(f"#### {t('upload.summary.title')}")
    st.caption(t("upload.summary.caption"))
    c1, c2, c3 = st.columns(3)
    c1.metric(t("upload.summary.numeric"), len(numeric))
    c2.metric(t("upload.summary.categorical"), len(categorical))
    c3.metric(t("upload.summary.missing"), int(df.isna().sum().sum()))
    types = pd.DataFrame({
        t("upload.summary.col.column"): df.columns,
        t("upload.summary.col.type"): [str(df[c].dtype) for c in df.columns],
        t("upload.summary.col.nonnull"): [int(df[c].notna().sum()) for c in df.columns],
    })
    with st.expander(t("upload.summary.expander"), expanded=False):
        st.dataframe(types, use_container_width=True)


def _render_schema_report(df: pd.DataFrame) -> None:
    result = validate_dataframe(df)

    st.markdown(f"#### {t('upload.schema.title')}")
    st.caption(t("upload.schema.caption"))

    counts = {tier: 0 for tier in _TIER_ORDER}
    missing_counts = {tier: 0 for tier in _TIER_ORDER}
    for row in result.rows:
        counts[row["tier"]] += 1
        if row["status"] == "missing":
            missing_counts[row["tier"]] += 1

    cols = st.columns(len(_TIER_ORDER))
    for i, tier in enumerate(_TIER_ORDER):
        present = counts[tier] - missing_counts[tier]
        cols[i].metric(t(_TIER_LABEL_KEY[tier]), f"{present}/{counts[tier]}")

    if result.errors:
        for err in result.errors:
            st.error(err)
    if result.required_missing:
        st.warning(t("upload.schema.required_missing", cols=", ".join(result.required_missing)))
    if result.required_empty:
        st.warning(t("upload.schema.required_empty", cols=", ".join(result.required_empty)))
    if result.recommended_missing:
        st.info(t("upload.schema.recommended_missing", cols=", ".join(result.recommended_missing)))
    if result.recommended_empty:
        st.info(t("upload.schema.recommended_empty", cols=", ".join(result.recommended_empty)))
    for w in result.warnings:
        st.caption(":warning: " + w)

    table = pd.DataFrame([
        {
            t("upload.schema.col.tier"): t(_TIER_LABEL_KEY[r["tier"]]),
            t("upload.schema.col.label"): r["label"],
            t("upload.schema.col.expected"): r["expected"],
            t("upload.schema.col.found"): r["found"] or "—",
            t("upload.schema.col.type"): r["type_found"] or "—",
            t("upload.schema.col.status"): t(_STATUS_LABEL_KEY[r["status"]]),
            t("upload.schema.col.feature"): r["feature"],
        }
        for r in result.rows
    ])
    with st.expander(t("upload.schema.expander"), expanded=False):
        st.dataframe(table, use_container_width=True)
        st.download_button(
            t("upload.schema.download"),
            data=table.to_csv(index=False).encode("utf-8-sig"),
            file_name="schema_validation.csv",
            mime="text/csv",
        )


_DELIMITER_KEYS = ("auto", "comma", "semicolon", "tab", "space")
_TEXT_EXTENSIONS = (".csv", ".txt", ".tsv")


def _render_profile_selector(df_raw: pd.DataFrame) -> None:
    """Seletor de perfil de dados — vive na página de Upload (e não no sidebar),
    pois o perfil é uma propriedade do dataset carregado. O valor persiste em
    ``st.session_state``; as demais páginas o leem via ``resolve_profile``."""
    current = get_profile_setting()
    options = list(PROFILE_OPTIONS)
    selected = st.selectbox(
        t("sidebar.profile_data"),
        options=options,
        index=options.index(current) if current in options else 0,
        format_func=lambda code: t(f"sidebar.profile_data.{code}"),
        key="upload_profile_selector",
        help=t("sidebar.profile_data_help"),
    )
    if selected != current:
        set_profile_setting(selected)
        st.rerun()
    # Em modo automático, mostra qual perfil foi detectado para o dataset atual.
    if selected == PROFILE_AUTO:
        detected = resolve_profile(df_raw)
        st.caption(t("sidebar.profile_data_detected", profile=t(f"sidebar.profile_data.{detected}")))


def render():
    st.subheader(t("upload.title"))
    uploaded = st.file_uploader(
        t("upload.uploader_label"),
        type=["csv", "txt", "tsv", "xlsx", "xls"],
        key="upload_file",
    )

    if uploaded:
        file_bytes = uploaded.getvalue()
        file_name = uploaded.name

        try:
            sheets = get_excel_sheets(file_bytes, file_name)
        except Exception as exc:
            st.error(t("upload.error_inspect", error=exc))
            sheets = None

        if sheets is not None:
            sheet_name = None
            if sheets:
                sheet_name = st.selectbox(t("upload.select_sheet"), sheets, key="upload_sheet")

            delimiter = "auto"
            if file_name.lower().endswith(_TEXT_EXTENSIONS):
                delimiter = st.selectbox(
                    t("upload.select_delimiter"),
                    _DELIMITER_KEYS,
                    format_func=lambda k: t(f"upload.delimiter.{k}"),
                    key="upload_delimiter",
                )

            if st.button(t("upload.load_button"), type="primary"):
                try:
                    df_loaded = load_data(file_bytes, file_name, sheet_name, delimiter)
                except Exception as exc:
                    st.error(t("upload.error_load", error=exc))
                else:
                    set_loaded_dataset(df_loaded)
                    st.success(t("upload.success_loaded", rows=len(df_loaded), cols=len(df_loaded.columns)))

    # Bloco do dataset carregado: roda mesmo que o uploader esteja vazio (o
    # dataset persiste na sessão), garantindo que o perfil fique acessível depois.
    df_raw = get_raw_dataframe()
    if df_raw is None:
        st.info(t("upload.info_send_file"))
        return

    _render_profile_selector(df_raw)

    c1, c2 = st.columns(2)
    c1.metric(t("upload.metric_rows"), len(df_raw))
    c2.metric(t("upload.metric_cols"), len(df_raw.columns))
    if is_physiology(df_raw):
        _render_schema_report(df_raw)
    else:
        _render_generic_summary(df_raw)
    st.markdown(f"#### {t('upload.preview_title')}")
    st.dataframe(df_raw.head(20), use_container_width=True)
