from __future__ import annotations

import pandas as pd
import streamlit as st

from src.i18n import t
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


def render():
    st.subheader(t("upload.title"))
    uploaded = st.file_uploader(t("upload.uploader_label"), type=["csv", "xlsx", "xls"], key="upload_file")

    if not uploaded:
        st.info(t("upload.info_send_file"))
        return

    file_bytes = uploaded.getvalue()
    file_name = uploaded.name

    try:
        sheets = get_excel_sheets(file_bytes, file_name)
    except Exception as exc:
        st.error(t("upload.error_inspect", error=exc))
        return

    sheet_name = None
    if sheets:
        sheet_name = st.selectbox(t("upload.select_sheet"), sheets, key="upload_sheet")

    if st.button(t("upload.load_button"), type="primary"):
        try:
            df_raw = load_data(file_bytes, file_name, sheet_name)
        except Exception as exc:
            st.error(t("upload.error_load", error=exc))
        else:
            set_loaded_dataset(df_raw)
            st.success(t("upload.success_loaded", rows=len(df_raw), cols=len(df_raw.columns)))

    df_raw = get_raw_dataframe()
    if df_raw is not None:
        c1, c2 = st.columns(2)
        c1.metric(t("upload.metric_rows"), len(df_raw))
        c2.metric(t("upload.metric_cols"), len(df_raw.columns))
        _render_schema_report(df_raw)
        st.markdown(f"#### {t('upload.preview_title')}")
        st.dataframe(df_raw.head(20), use_container_width=True)
