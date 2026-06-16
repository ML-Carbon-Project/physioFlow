from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from src.components.charts import show_fig

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.config.settings import REGRESSION_PRESETS
from src.i18n import t
from src.profile import is_physiology


def _localized_preset_label(internal_key: str) -> str:
    return internal_key


def render():
    st.subheader(t("regression.title"))

    df_raw = ensure_raw_dataframe(t("regression.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("reg_use_processed")
    if df is None:
        df = df_raw

    # Aplica os filtros na página
    from src.components.filters import render_page_filters
    df = render_page_filters(df)

    numeric_cols = list(df.select_dtypes(include="number").columns)
    cat_cols = [column for column in df.columns if column not in numeric_cols]
    if len(numeric_cols) < 2:
        st.warning(t("regression.warn_min_numeric"))
        return

    none_label = t("common.none")

    # Presets bivariados são específicos de fisiologia; só no perfil de fisiologia.
    if is_physiology(df):
        st.markdown(f"#### {t('regression.preset_title')}")
        available_presets: list[tuple[str, str]] = []
        for preset in REGRESSION_PRESETS:
            if preset[1] in df.columns and preset[2] in df.columns:
                available_presets.append((preset[0], _localized_preset_label(preset[0])))

        preset_options = [none_label] + [label for _, label in available_presets]
        selected_label = st.selectbox(t("regression.preset_select"), options=preset_options, key="reg_preset")

        if selected_label != none_label:
            internal = next(internal for internal, label in available_presets if label == selected_label)
            _, x_p, y_p, hue_p = next(preset for preset in REGRESSION_PRESETS if preset[0] == internal)
            plot_df = df[[x_p, y_p] + ([hue_p] if hue_p in df.columns else [])].dropna().copy()
            if len(plot_df) > 3000:
                plot_df = plot_df.sample(3000, random_state=42)
                st.caption(t("regression.preset_caption_sample"))

            if hue_p in df.columns:
                grid = sns.lmplot(
                    data=plot_df,
                    x=x_p,
                    y=y_p,
                    hue=hue_p,
                    palette="viridis",
                    height=5,
                    aspect=1.4,
                    scatter_kws={"alpha": 0.5, "s": 20},
                    line_kws={"linewidth": 2},
                )
            else:
                grid = sns.lmplot(
                    data=plot_df,
                    x=x_p,
                    y=y_p,
                    height=5,
                    aspect=1.4,
                    scatter_kws={"alpha": 0.5, "s": 20},
                    line_kws={"linewidth": 2},
                )
            grid.fig.suptitle(selected_label, y=1.02)
            show_fig(grid.fig)

    st.markdown(f"#### {t('regression.custom_title')}")
    default_x = "gs" if "gs" in numeric_cols else numeric_cols[0]
    default_y = "A" if "A" in numeric_cols else next(column for column in numeric_cols if column != default_x)
    x_var = st.selectbox(t("regression.x"), options=numeric_cols, index=numeric_cols.index(default_x), key="reg_x")
    y_options = [column for column in numeric_cols if column != x_var]
    y_var = st.selectbox(
        t("regression.y"),
        options=y_options,
        index=y_options.index(default_y) if default_y in y_options else 0,
        key="reg_y",
    )

    hue_options = [none_label] + cat_cols
    default_hue = "Cultura" if "Cultura" in cat_cols else none_label
    hue_var = st.selectbox(
        t("regression.hue"),
        options=hue_options,
        index=hue_options.index(default_hue) if default_hue in hue_options else 0,
        key="reg_hue",
    )
    facet_options = [none_label] + cat_cols
    facet_var = st.selectbox(t("regression.facet"), options=facet_options, index=0, key="reg_facet")
    ci_value = st.slider(t("regression.ci"), 0, 99, 95, 1, key="reg_ci")
    sample_n = st.slider(t("regression.sample"), 100, 5000, 2000, 100, key="reg_sample")

    plot_columns = [x_var, y_var]
    if hue_var != none_label:
        plot_columns.append(hue_var)
    if facet_var != none_label and facet_var not in plot_columns:
        plot_columns.append(facet_var)

    plot_df = df[plot_columns].dropna().copy()
    if len(plot_df) > sample_n:
        plot_df = plot_df.sample(sample_n, random_state=42)
        st.caption(t("regression.caption_sample", n=sample_n))

    lm_kwargs = {
        "data": plot_df,
        "x": x_var,
        "y": y_var,
        "height": 5,
        "aspect": 1.35,
        "ci": ci_value,
        "scatter_kws": {"alpha": 0.5, "s": 20},
        "line_kws": {"linewidth": 2},
    }
    if hue_var != none_label:
        lm_kwargs["hue"] = hue_var
        lm_kwargs["palette"] = "viridis"
    if facet_var != none_label:
        lm_kwargs["col"] = facet_var

    grid = sns.lmplot(**lm_kwargs)
    grid.fig.suptitle(t("regression.title_dynamic", x=x_var, y=y_var), y=1.02)
    show_fig(grid.fig)

    corr = plot_df[[x_var, y_var]].corr().iloc[0, 1]
    st.caption(t("regression.caption_corr", x=x_var, y=y_var, corr=f"{corr:.4f}", n=len(plot_df)))
