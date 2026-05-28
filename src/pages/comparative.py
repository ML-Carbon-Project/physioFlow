"""Página de comparação entre dois grupos categóricos.

O usuário escolhe a coluna categórica e define quais valores formam o
Grupo A e o Grupo B. Há também um classificador opcional por padrão de
substring (case-insensitive): valores cujo texto contém o padrão entram
no Grupo A; os demais entram no Grupo B. Esse mecanismo é totalmente
genérico — não depende de domínio ecológico, agronômico ou qualquer
outro contexto: o padrão é informado pelo usuário (ex.: "mata", "no-till",
"control", "rainy"). O componente também suporta uma variável dependente
para ajuste log-linear (apenas valores positivos) e uma coluna de
data/hora para o padrão horário e o fluxo cumulativo.
"""
from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.i18n import t
from src.pipeline import DATE_COLUMN_CANDIDATES, coerce_date_series, find_date_column

# Mantido para retrocompatibilidade: usuários externos podem importar
# DATE_CANDIDATES desta página.
DATE_CANDIDATES = DATE_COLUMN_CANDIDATES


def _first_existing(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _matches_pattern(value: object, pattern: str) -> bool:
    if not pattern:
        return False
    if pd.isna(value):
        return False
    return pattern.strip().lower() in str(value).strip().lower()


def _summary_table(df: pd.DataFrame, group_col: str, numeric_cols: list[str]) -> pd.DataFrame:
    rows = []
    for grp_value, sub in df.groupby(group_col):
        for col in numeric_cols:
            x = sub[col].dropna()
            if len(x) == 0:
                continue
            rows.append({
                "group": grp_value,
                "variable": col,
                "n": int(len(x)),
                "mean": round(float(x.mean()), 4),
                "se": round(float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0, 4),
                "median": round(float(x.median()), 4),
            })
    return pd.DataFrame(rows)


def _render_summary_tab(df: pd.DataFrame, group_col: str, numeric_cols: list[str], labels: tuple[str, str]) -> None:
    st.markdown(f"#### {t('comparative.summary.title')}")
    st.caption(t("comparative.summary.caption"))

    default_targets = [c for c in ("FCO2_DRY", "FCH4_DRY", "TS_2 initial_value", "SWC_2 initial_value") if c in numeric_cols]
    targets = st.multiselect(
        t("comparative.summary.targets"),
        options=numeric_cols,
        default=default_targets or numeric_cols[:3],
        key="comp_summary_targets",
    )
    if not targets:
        st.info(t("comparative.summary.select_var"))
        return

    table = _summary_table(df, group_col, targets)
    st.dataframe(table, use_container_width=True)
    st.download_button(
        t("comparative.summary.download"),
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="group_comparison_summary.csv",
        mime="text/csv",
    )

    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        st.warning(t("comparative.summary.missing_scipy"))
        return

    test_rows = []
    g1, g2 = labels
    for col in targets:
        x = df.loc[df[group_col] == g1, col].dropna().to_numpy()
        y = df.loc[df[group_col] == g2, col].dropna().to_numpy()
        if len(x) < 3 or len(y) < 3:
            continue
        try:
            stat, p = mannwhitneyu(x, y, alternative="two-sided")
        except Exception:
            continue
        test_rows.append({
            "variable": col,
            "g1": g1, "g2": g2,
            "n_g1": int(len(x)), "n_g2": int(len(y)),
            "U": round(float(stat), 2),
            "p_value": float(p),
            "significant_5%": bool(p < 0.05),
        })
    if test_rows:
        st.markdown(f"##### {t('comparative.summary.test_title')}")
        st.dataframe(pd.DataFrame(test_rows), use_container_width=True)


def _render_loglinear_tab(df: pd.DataFrame, group_col: str, numeric_cols: list[str], labels: tuple[str, str]) -> None:
    st.markdown(f"#### {t('comparative.loglinear.title')}")
    st.caption(t("comparative.loglinear.caption"))

    if len(numeric_cols) < 2:
        st.info(t("comparative.loglinear.too_few_numeric"))
        return

    try:
        from scipy import stats as scstats
    except ImportError:
        st.warning(t("comparative.summary.missing_scipy"))
        return

    default_y = "FCO2_DRY" if "FCO2_DRY" in numeric_cols else numeric_cols[0]
    y_col = st.selectbox(
        t("comparative.loglinear.y_var"),
        options=numeric_cols,
        index=numeric_cols.index(default_y),
        key="comp_log_y",
    )
    default_x = "TS_2 initial_value" if "TS_2 initial_value" in numeric_cols else (numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0])
    x_options = [c for c in numeric_cols if c != y_col]
    x_col = st.selectbox(
        t("comparative.loglinear.x_var"),
        options=x_options,
        index=x_options.index(default_x) if default_x in x_options else 0,
        key="comp_log_x",
    )

    fig, ax = plt.subplots(figsize=(9, 5.5))
    palette = {labels[0]: "#0a7d3b", labels[1]: "#b45309"}

    rows = []
    for grp_value, sub in df.groupby(group_col):
        sub = sub[[x_col, y_col]].dropna()
        sub = sub[sub[y_col] > 0]
        if len(sub) < 5:
            continue
        log_y = np.log(sub[y_col].to_numpy())
        x = sub[x_col].to_numpy()
        slope, intercept, r, p, se = scstats.linregress(x, log_y)
        ax.scatter(x, log_y, alpha=0.5, s=22, color=palette.get(grp_value, "#475569"), label=f"{grp_value} (n={len(sub)})")
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, intercept + slope * xs, color=palette.get(grp_value, "#475569"), linewidth=2)
        rows.append({
            "group": grp_value, "n": int(len(sub)),
            "intercept": round(float(intercept), 4),
            "slope": round(float(slope), 4),
            "R2": round(float(r ** 2), 4),
            "p_value": float(p),
            "se_slope": round(float(se), 4),
        })

    ax.set_xlabel(x_col)
    ax.set_ylabel(t("comparative.loglinear.y_label", var=y_col))
    ax.set_title(t("comparative.loglinear.title_dynamic", x=x_col, y=y_col))
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


def _render_hourly_tab(df: pd.DataFrame, group_col: str, numeric_cols: list[str], labels: tuple[str, str]) -> None:
    st.markdown(f"#### {t('comparative.hourly.title')}")
    st.caption(t("comparative.hourly.caption"))

    # Lista de candidatos cresce o conjunto detectado: nomes conhecidos,
    # dtype datetime64, e colunas object com conteúdo majoritariamente datetime.
    date_options: list[str] = []
    primary = find_date_column(df)
    if primary is not None:
        date_options.append(primary)
    for c in df.columns:
        if c in date_options:
            continue
        if c in DATE_CANDIDATES or pd.api.types.is_datetime64_any_dtype(df[c]):
            date_options.append(c)

    if not date_options:
        st.info(t("comparative.hourly.missing_cols"))
        return

    date_col = st.selectbox(
        t("comparative.hourly.date_col"),
        options=date_options,
        key="comp_hourly_date",
    )
    default_y = "FCO2_DRY" if "FCO2_DRY" in numeric_cols else (numeric_cols[0] if numeric_cols else None)
    if default_y is None:
        st.info(t("comparative.hourly.no_numeric"))
        return
    y_col = st.selectbox(
        t("comparative.hourly.y_var"),
        options=numeric_cols,
        index=numeric_cols.index(default_y),
        key="comp_hourly_y",
    )

    work = df[[group_col, date_col, y_col]].copy()
    work[date_col] = coerce_date_series(work[date_col])
    work = work.dropna(subset=[date_col, y_col])
    if work.empty:
        st.info(t("comparative.hourly.no_data"))
        return
    work["hour"] = work[date_col].dt.hour

    hourly = (
        work.groupby([group_col, "hour"], as_index=False)
        .agg(mean=(y_col, "mean"), median=(y_col, "median"), n=(y_col, "size"))
        .sort_values([group_col, "hour"])
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    palette = {labels[0]: "#0a7d3b", labels[1]: "#b45309"}
    for grp, sub in hourly.groupby(group_col):
        axes[0].plot(sub["hour"], sub["mean"], marker="o", color=palette.get(grp, "#475569"), label=grp, linewidth=1.6)
    axes[0].set_xlabel(t("comparative.hourly.x"))
    axes[0].set_ylabel(t("comparative.hourly.y_mean", var=y_col))
    axes[0].set_title(t("comparative.hourly.mean_title", var=y_col))
    axes[0].legend()

    for grp, sub in hourly.groupby(group_col):
        cum = sub["mean"].cumsum()
        axes[1].plot(sub["hour"], cum, marker="o", color=palette.get(grp, "#475569"), label=grp, linewidth=1.6)
    axes[1].set_xlabel(t("comparative.hourly.x"))
    axes[1].set_ylabel(t("comparative.hourly.y_cumulative", var=y_col))
    axes[1].set_title(t("comparative.hourly.cumulative_title", var=y_col))
    axes[1].legend()
    st.pyplot(fig)
    plt.close(fig)

    st.dataframe(hourly, use_container_width=True)
    st.download_button(
        t("comparative.hourly.download"),
        data=hourly.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"hourly_{y_col}_by_group.csv",
        mime="text/csv",
    )


def render() -> None:
    st.subheader(t("comparative.title"))

    df_raw = ensure_raw_dataframe(t("comparative.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("comparative_use_processed")
    if df is None:
        df = df_raw

    cat_cols = [c for c in df.columns if c not in df.select_dtypes(include="number").columns]
    if not cat_cols:
        st.info(t("comparative.no_cat"))
        return

    st.markdown(f"#### {t('comparative.config.title')}")
    st.caption(t("comparative.config.caption"))

    default_group_col = next((c for c in ("Crop_Type", "Cultura", "cultura") if c in cat_cols), cat_cols[0])
    group_col = st.selectbox(
        t("comparative.config.group_col"),
        options=cat_cols,
        index=cat_cols.index(default_group_col) if default_group_col in cat_cols else 0,
        key="comp_group_col",
    )
    levels = sorted(df[group_col].dropna().astype(str).unique().tolist())
    if len(levels) < 2:
        st.info(t("comparative.config.few_levels"))
        return

    use_pattern = st.checkbox(t("comparative.config.pattern_toggle"), value=False, key="comp_use_pattern")

    pattern_match: list[str] = []
    pattern_other: list[str] = []
    if use_pattern:
        pattern = st.text_input(
            t("comparative.config.pattern_input"),
            value="",
            help=t("comparative.config.pattern_help"),
            key="comp_pattern",
        )
        if pattern:
            pattern_match = [v for v in levels if _matches_pattern(v, pattern)]
            pattern_other = [v for v in levels if v not in pattern_match]
            if not pattern_match:
                st.warning(t("comparative.config.pattern_no_match"))
                use_pattern = False

    if use_pattern and pattern_match:
        col1, col2 = st.columns(2)
        with col1:
            label_a = st.text_input(t("comparative.config.label_a"), value="Match", key="comp_label_a")
            st.caption(", ".join(pattern_match))
            values_a = pattern_match
        with col2:
            label_b = st.text_input(t("comparative.config.label_b"), value="Other", key="comp_label_b")
            st.caption(", ".join(pattern_other))
            values_b = pattern_other
    else:
        col1, col2 = st.columns(2)
        with col1:
            label_a = st.text_input(t("comparative.config.label_a"), value=levels[0], key="comp_label_a")
            values_a = st.multiselect(
                t("comparative.config.values_a"),
                options=levels,
                default=[levels[0]],
                key="comp_values_a",
            )
        with col2:
            label_b = st.text_input(t("comparative.config.label_b"), value=levels[1] if len(levels) > 1 else "Other", key="comp_label_b")
            default_b = [v for v in levels if v not in values_a] or [levels[-1]]
            values_b = st.multiselect(
                t("comparative.config.values_b"),
                options=levels,
                default=default_b,
                key="comp_values_b",
            )

    overlap = set(values_a) & set(values_b)
    if overlap:
        st.error(t("comparative.config.overlap", values=", ".join(sorted(overlap))))
        return
    if not values_a or not values_b:
        st.info(t("comparative.config.empty_groups"))
        return

    df = df.copy()
    df["_compare_group"] = pd.NA
    df.loc[df[group_col].astype(str).isin(values_a), "_compare_group"] = label_a
    df.loc[df[group_col].astype(str).isin(values_b), "_compare_group"] = label_b
    valid = df.dropna(subset=["_compare_group"])
    counts = valid["_compare_group"].value_counts()

    c1, c2 = st.columns(2)
    c1.metric(label_a, int(counts.get(label_a, 0)))
    c2.metric(label_b, int(counts.get(label_b, 0)))

    if counts.get(label_a, 0) < 3 or counts.get(label_b, 0) < 3:
        st.warning(t("comparative.config.too_few_per_group"))
        return

    numeric_cols = [c for c in valid.select_dtypes(include="number").columns if c != "_compare_group"]
    labels = (label_a, label_b)

    tabs = st.tabs([
        t("comparative.tab.summary"),
        t("comparative.tab.loglinear"),
        t("comparative.tab.hourly"),
    ])
    with tabs[0]:
        _render_summary_tab(valid, "_compare_group", numeric_cols, labels)
    with tabs[1]:
        _render_loglinear_tab(valid, "_compare_group", numeric_cols, labels)
    with tabs[2]:
        _render_hourly_tab(valid, "_compare_group", numeric_cols, labels)
