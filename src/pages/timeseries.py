"""Página de Série Temporal: agregação por data e decomposição STL."""
from __future__ import annotations

from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.i18n import t

_DATE_CANDIDATES = ("Data", "Date", "DATE", "data", "date", "Date_Time", "DateTime")


def _find_date_column(df: pd.DataFrame) -> Optional[str]:
    for candidate in _DATE_CANDIDATES:
        if candidate in df.columns:
            return candidate
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def _aggregate_daily(df: pd.DataFrame, date_col: str, target: str, agg: str) -> pd.Series:
    work = df[[date_col, target]].dropna().copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    if work.empty:
        return pd.Series(dtype=float)
    series = work.set_index(date_col).sort_index()[target]
    series = series.resample("D").agg(agg)
    return series


def _render_aggregate_tab(df: pd.DataFrame, date_col: str, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('timeseries.agg.title')}")
    st.caption(t("timeseries.agg.caption"))

    targets = st.multiselect(
        t("timeseries.agg.targets"),
        options=numeric_cols,
        default=[c for c in ("FCO2_DRY", "FCH4_DRY") if c in numeric_cols] or numeric_cols[:1],
        key="ts_agg_targets",
    )
    agg_label = st.radio(
        t("timeseries.agg.method"),
        options=[t("timeseries.agg.mean"), t("timeseries.agg.median")],
        horizontal=True,
        key="ts_agg_method",
    )
    agg = "mean" if agg_label == t("timeseries.agg.mean") else "median"

    if not targets:
        st.info(t("timeseries.agg.select_var"))
        return

    fig, ax = plt.subplots(figsize=(11, 4.5))
    palette = plt.get_cmap("tab10")
    plotted_any = False
    for idx, target in enumerate(targets):
        series = _aggregate_daily(df, date_col, target, agg)
        if series.dropna().empty:
            continue
        ax.plot(series.index, series.values, marker="o", color=palette(idx % 10), label=target, linewidth=1.4, markersize=4)
        plotted_any = True

    if not plotted_any:
        st.info(t("timeseries.agg.no_data"))
        plt.close(fig)
        return

    ax.set_xlabel(t("timeseries.agg.x"))
    ax.set_ylabel(t("timeseries.agg.y"))
    ax.set_title(t("timeseries.agg.title_dynamic", agg=agg_label))
    ax.legend()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    st.pyplot(fig)
    plt.close(fig)


def _render_stl_tab(df: pd.DataFrame, date_col: str, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('timeseries.stl.title')}")
    st.caption(t("timeseries.stl.caption"))

    try:
        from statsmodels.tsa.seasonal import STL
    except ImportError:
        st.warning(t("timeseries.stl.missing_deps"))
        return

    target = st.selectbox(
        t("timeseries.stl.target"),
        options=numeric_cols,
        index=numeric_cols.index("FCO2_DRY") if "FCO2_DRY" in numeric_cols else 0,
        key="ts_stl_target",
    )
    period = st.slider(
        t("timeseries.stl.period"),
        min_value=2,
        max_value=60,
        value=7,
        step=1,
        key="ts_stl_period",
    )
    interpolate = st.checkbox(t("timeseries.stl.interpolate"), value=True, key="ts_stl_interp")

    # Conta datas distintas com medição real ANTES da interpolação para evitar
    # decompor uma série em que >> 70% dos pontos são fabricados pela interpolação.
    raw_series = _aggregate_daily(df, date_col, target, "median")
    n_observed = int(raw_series.dropna().shape[0])
    min_observed_dates = 10
    if n_observed < min_observed_dates:
        st.warning(
            t(
                "timeseries.stl.too_few_dates",
                n=n_observed,
                need=min_observed_dates,
            )
        )
        return

    series = raw_series
    if interpolate:
        series = series.interpolate(method="time").dropna()
        observed_share = n_observed / max(len(series), 1)
        if observed_share < 0.3:
            st.warning(
                t(
                    "timeseries.stl.heavy_interpolation",
                    observed=n_observed,
                    total=len(series),
                    pct=f"{observed_share * 100:.1f}",
                )
            )
    else:
        series = series.dropna()

    if len(series) < period * 2 + 4:
        st.info(t("timeseries.stl.too_few", n=len(series), need=period * 2 + 4))
        return

    try:
        stl = STL(series, period=period, robust=True).fit()
    except Exception as exc:
        st.error(t("timeseries.stl.error", error=str(exc)))
        return

    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(series.index, series.values, color="#0f766e", linewidth=1.3)
    axes[0].set_ylabel(t("timeseries.stl.observed"))
    axes[1].plot(stl.trend.index, stl.trend.values, color="#1f77b4", linewidth=1.3)
    axes[1].set_ylabel(t("timeseries.stl.trend"))
    axes[2].plot(stl.seasonal.index, stl.seasonal.values, color="#ff7f0e", linewidth=1.0)
    axes[2].set_ylabel(t("timeseries.stl.seasonal"))
    axes[3].plot(stl.resid.index, stl.resid.values, color="#7f7f7f", linewidth=0.9)
    axes[3].axhline(0, color="black", linewidth=0.5)
    axes[3].set_ylabel(t("timeseries.stl.residual"))
    axes[3].set_xlabel(t("timeseries.agg.x"))
    fig.suptitle(t("timeseries.stl.title_dynamic", var=target, period=period), y=0.995)
    fig.autofmt_xdate()
    st.pyplot(fig)
    plt.close(fig)

    obs_var = float(np.var(series.values))
    res_var = float(np.var(stl.resid.values))
    seas_var = float(np.var(stl.seasonal.values))
    trend_var = float(np.var(stl.trend.values))

    c1, c2, c3 = st.columns(3)
    if obs_var > 0:
        c1.metric(t("timeseries.stl.metric_trend_strength"), f"{max(0.0, 1 - res_var / max(obs_var - seas_var, 1e-12)):.3f}")
        c2.metric(t("timeseries.stl.metric_seasonal_strength"), f"{max(0.0, 1 - res_var / max(obs_var - trend_var, 1e-12)):.3f}")
    c3.metric(t("timeseries.stl.metric_n"), len(series))


def render() -> None:
    st.subheader(t("timeseries.title"))

    df_raw = ensure_raw_dataframe(t("timeseries.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("ts_use_processed")
    if df is None:
        df = df_raw

    date_col = _find_date_column(df)
    if date_col is None:
        st.info(t("timeseries.no_date"))
        return

    numeric_cols = list(df.select_dtypes(include="number").columns)
    if not numeric_cols:
        st.info(t("timeseries.no_numeric"))
        return

    tabs = st.tabs([t("timeseries.tab.aggregate"), t("timeseries.tab.stl")])
    with tabs[0]:
        _render_aggregate_tab(df, date_col, numeric_cols)
    with tabs[1]:
        _render_stl_tab(df, date_col, numeric_cols)
