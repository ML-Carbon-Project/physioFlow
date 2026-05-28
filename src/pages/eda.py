from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.config.settings import EDA_DEFAULT_DISTRIBUTION_COLUMNS, EDA_DEFAULT_PAIR_COLUMNS
from src.i18n import t

def _find_date_column(df: pd.DataFrame) -> str | None:
    from src.pipeline import find_first_existing
    return find_first_existing(df, ["Data da coleta", "Data", "Date", "DATE"])


def render():
    st.subheader(t("eda.title"))

    df_raw = ensure_raw_dataframe(t("eda.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("eda_use_processed")
    if df is None:
        df = df_raw

    # Aplica os filtros globais da barra lateral
    from src.components.filters import render_page_filters
    df = render_page_filters(df)

    all_columns = list(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)
    cat_cols = [column for column in all_columns if column not in numeric_cols]

    if not numeric_cols:
        st.warning(t("eda.warn_no_numeric"))
        return

    none_label = t("common.none")

    tabs = st.tabs(
        [
            t("eda.tab.summary"),
            t("eda.tab.quality"),
            t("eda.tab.bivariate"),
            t("eda.tab.boxplots"),
            t("eda.tab.scatter"),
            t("eda.tab.correlation"),
            t("eda.tab.spatial"),
            t("eda.tab.temporal"),
            t("eda.tab.composition"),
            t("eda.tab.inference"),
            t("eda.tab.hotspots"),
            t("eda.tab.outliers"),
        ]
    )
    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = tabs

    # ---------------- Tab 0: summary ----------------
    with tab0:
        st.markdown(f"#### {t('eda.summary.title')}")
        desc = df[numeric_cols].describe().T
        desc["skewness"] = df[numeric_cols].skew().round(4)
        desc["kurtosis"] = df[numeric_cols].kurt().round(4)
        desc = desc.round(4)
        st.dataframe(desc, use_container_width=True)
        st.download_button(
            t("eda.summary.download"),
            data=desc.to_csv(index=True).encode("utf-8-sig"),
            file_name="resumo_estatistico.csv",
            mime="text/csv",
        )

    # ---------------- Tab 1: data quality ----------------
    with tab1:
        st.markdown(f"#### {t('eda.quality.title')}")
        c1, c2 = st.columns(2)
        c1.metric(t("eda.quality.metric_rows"), len(df))
        c2.metric(t("eda.quality.metric_cols"), len(df.columns))

        missing_df = (
            df.isna()
            .sum()
            .rename("missing")
            .to_frame()
            .assign(percent=lambda data: (data["missing"] / len(df) * 100).round(2))
            .sort_values("missing", ascending=False)
        )
        st.markdown(f"##### {t('eda.quality.missing_title')}")
        st.dataframe(missing_df, use_container_width=True)

        non_zero_missing = missing_df[missing_df["missing"] > 0]
        if not non_zero_missing.empty:
            fig_missing, ax_missing = plt.subplots(figsize=(10, 4))
            sns.barplot(
                x=non_zero_missing.index,
                y=non_zero_missing["missing"].values,
                hue=non_zero_missing.index,
                legend=False,
                palette="crest",
                ax=ax_missing,
            )
            ax_missing.tick_params(axis="x", rotation=45)
            ax_missing.set_title(t("eda.quality.missing_chart_title"))
            st.pyplot(fig_missing)
            plt.close(fig_missing)

        if cat_cols:
            st.markdown(f"##### {t('eda.quality.cat_title')}")
            default_cat = next((c for c in ("Season", "Época") if c in cat_cols), cat_cols[0])
            cat_col = st.selectbox(
                t("eda.quality.cat_select"),
                options=cat_cols,
                index=cat_cols.index(default_cat),
                key="eda_quality_cat",
            )
            counts = df[cat_col].value_counts(dropna=False).rename_axis(cat_col).reset_index(name="count")
            st.dataframe(counts, use_container_width=True)

    # ---------------- Tab 2: bivariate (univariate distributions) ----------------
    with tab2:
        st.markdown(f"#### {t('eda.bivariate.title')}")
        default_dist = [column for column in EDA_DEFAULT_DISTRIBUTION_COLUMNS if column in numeric_cols]
        dist_cols = st.multiselect(
            t("eda.bivariate.select"),
            options=numeric_cols,
            default=default_dist or numeric_cols[:3],
            key="eda_dist_cols",
        )
        bins = st.slider(t("eda.bivariate.bins"), 10, 100, 30, key="eda_bins")
        show_kde = st.checkbox(t("eda.bivariate.kde"), value=True, key="eda_kde")

        for column in dist_cols:
            fig_hist, ax_hist = plt.subplots(figsize=(8, 4))
            sns.histplot(df[column].dropna(), bins=bins, kde=show_kde, color="#0f766e", ax=ax_hist)
            ax_hist.set_title(t("eda.bivariate.dist_title", col=column))
            st.pyplot(fig_hist)
            plt.close(fig_hist)

    # ---------------- Tab 3: boxplots / violin ----------------
    with tab3:
        st.markdown(f"#### {t('eda.boxplot.title')}")
        if not cat_cols:
            st.info(t("eda.boxplot.no_cat"))
        else:
            target = st.selectbox(t("eda.boxplot.target"), options=numeric_cols, key="eda_box_target")
            x_cat = st.selectbox(t("eda.boxplot.x"), options=cat_cols, key="eda_box_x")
            hue_options = [none_label] + cat_cols
            hue_col = st.selectbox(t("eda.boxplot.hue"), options=hue_options, index=0, key="eda_box_hue")
            kind_label = st.radio(
                t("eda.boxplot.kind"),
                options=[t("eda.boxplot.kind.box"), t("eda.boxplot.kind.violin")],
                horizontal=True,
                key="eda_box_kind",
            )

            cols_to_use = [x_cat, target]
            if hue_col != none_label:
                cols_to_use.append(hue_col)
            plot_df = df[cols_to_use].dropna().copy()

            if plot_df.empty:
                st.info("Não há dados válidos para exibir esta análise com os filtros atuais.")
            else:
                try:
                    fig_box, ax_box = plt.subplots(figsize=(10, 5))
                    plot_func = sns.boxplot if kind_label == t("eda.boxplot.kind.box") else sns.violinplot
                    if hue_col != none_label:
                        plot_func(data=plot_df, x=x_cat, y=target, hue=hue_col, palette="Set2", ax=ax_box)
                    else:
                        plot_func(data=plot_df, x=x_cat, y=target, color="#5fb49c", ax=ax_box)
                    ax_box.tick_params(axis="x", rotation=45)
                    ax_box.set_title(t("eda.boxplot.title_dynamic", target=target, x=x_cat))
                    st.pyplot(fig_box)
                    plt.close(fig_box)
                except Exception as e:
                    st.error(f"Erro ao renderizar o gráfico: {e}")

    # ---------------- Tab 4: scatter / pairplot ----------------
    with tab4:
        st.markdown(f"#### {t('eda.scatter.title')}")
        default_pair = [column for column in EDA_DEFAULT_PAIR_COLUMNS if column in numeric_cols]
        pair_cols = st.multiselect(
            t("eda.scatter.select"),
            options=numeric_cols,
            default=default_pair or numeric_cols[:4],
            key="eda_pair_cols",
        )
        hue_options = [none_label] + cat_cols
        hue_col = st.selectbox(t("eda.scatter.hue"), options=hue_options, index=0, key="eda_pair_hue")
        sample_n = st.slider(t("eda.scatter.sample"), 100, 5000, 1200, 100, key="eda_pair_sample")

        if len(pair_cols) < 2:
            st.info(t("eda.scatter.info_min"))
        elif len(pair_cols) > 6:
            st.warning(t("eda.scatter.warn_max"))
        else:
            plot_df = df[pair_cols + ([] if hue_col == none_label else [hue_col])].dropna().copy()
            if len(plot_df) > sample_n:
                plot_df = plot_df.sample(sample_n, random_state=42)
                st.caption(t("eda.scatter.caption_sample", n=sample_n))

            if hue_col == none_label:
                grid = sns.pairplot(plot_df, vars=pair_cols, corner=True, plot_kws={"alpha": 0.5, "s": 18})
            else:
                grid = sns.pairplot(
                    plot_df,
                    vars=pair_cols,
                    hue=hue_col,
                    corner=True,
                    plot_kws={"alpha": 0.5, "s": 18},
                    palette="viridis",
                )
            grid.fig.suptitle(t("eda.scatter.title_dynamic"), y=1.02)
            st.pyplot(grid.fig)

    # ---------------- Tab 5: correlation ----------------
    with tab5:
        st.markdown(f"#### {t('eda.corr.title')}")
        default_corr = numeric_cols[:6] if len(numeric_cols) >= 2 else numeric_cols
        selected_corr = st.multiselect(
            t("eda.corr.select"),
            numeric_cols,
            default=default_corr,
            key="eda_corr_cols",
        )
        method_label = st.radio(
            t("eda.corr.method"),
            options=[t("eda.corr.method.pearson"), t("eda.corr.method.spearman"), t("eda.corr.method.kendall")],
            horizontal=True,
            key="eda_corr_method",
        )
        if method_label == t("eda.corr.method.pearson"):
            method = "pearson"
        elif method_label == t("eda.corr.method.spearman"):
            method = "spearman"
        else:
            method = "kendall"
        if len(selected_corr) >= 2:
            corr_df = df[selected_corr].corr(method=method, numeric_only=True)
            fig_corr, ax_corr = plt.subplots(figsize=(8, 6))
            sns.heatmap(corr_df, annot=True, cmap="coolwarm", ax=ax_corr)
            ax_corr.set_title(t("eda.corr.title_dynamic", method=method_label))
            st.pyplot(fig_corr)
            st.dataframe(corr_df, use_container_width=True)
            st.download_button(
                t("eda.corr.download"),
                data=corr_df.to_csv(index=True).encode("utf-8"),
                file_name=f"correlacao_{method}.csv",
                mime="text/csv",
            )
        else:
            st.info(t("eda.corr.info_min"))

    # ---------------- Tab 6: spatial ----------------
    with tab6:
        st.markdown(f"#### {t('eda.spatial.title')}")
        if "Latitude" not in df.columns or "Longitude" not in df.columns:
            st.info(t("eda.spatial.no_coords"))
        else:
            map_var = st.selectbox(t("eda.spatial.var"), options=numeric_cols, key="eda_map_var")
            facet_options = [none_label] + cat_cols
            facet_col = st.selectbox(t("eda.spatial.facet"), options=facet_options, key="eda_map_facet")

            if facet_col == none_label:
                fig_map, ax_map = plt.subplots(figsize=(9, 6))
                sns.scatterplot(
                    data=df,
                    x="Longitude",
                    y="Latitude",
                    hue=map_var,
                    size=map_var,
                    sizes=(20, 180),
                    palette="magma_r",
                    alpha=0.75,
                    ax=ax_map,
                )
                ax_map.set_title(t("eda.spatial.title_dynamic", var=map_var))
                st.pyplot(fig_map)
            else:
                grid = sns.relplot(
                    data=df,
                    x="Longitude",
                    y="Latitude",
                    hue=map_var,
                    size=map_var,
                    sizes=(20, 160),
                    col=facet_col,
                    kind="scatter",
                    palette="magma_r",
                    alpha=0.75,
                    height=4.5,
                    aspect=1,
                )
                grid.figure.suptitle(t("eda.spatial.title_facet", var=map_var, facet=facet_col), y=1.02)
                st.pyplot(grid.figure)

    # ---------------- Tab 7: temporal (NEW) ----------------
    with tab7:
        st.markdown(f"#### {t('eda.temporal.title')}")
        date_col = _find_date_column(df)
        if date_col is None:
            st.info(t("eda.temporal.no_date"))
        else:
            default_var = "A" if "A" in numeric_cols else numeric_cols[0]
            var = st.selectbox(
                t("eda.temporal.var"),
                options=numeric_cols,
                index=numeric_cols.index(default_var),
                key="eda_temporal_var",
            )
            hue_options = [none_label] + cat_cols
            default_hue = next((c for c in ("Crop_Type", "Cultura") if c in cat_cols), none_label)
            hue_col = st.selectbox(
                t("eda.temporal.hue"),
                options=hue_options,
                index=hue_options.index(default_hue),
                key="eda_temporal_hue",
            )
            agg_label = st.radio(
                t("eda.temporal.aggregate"),
                options=[t("eda.temporal.aggregate.mean"), t("eda.temporal.aggregate.median")],
                horizontal=True,
                key="eda_temporal_agg",
            )
            agg_func = "mean" if agg_label == t("eda.temporal.aggregate.mean") else "median"

            try:
                work = df[[date_col, var] + ([hue_col] if hue_col != none_label else [])].dropna().copy()
                work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
                work = work.dropna(subset=[date_col])
                if work.empty:
                    st.info("Não há dados válidos temporais com os filtros selecionados.")
                else:
                    group_cols = [date_col] + ([hue_col] if hue_col != none_label else [])
                    series = work.groupby(group_cols, as_index=False)[var].agg(agg_func)

                    fig_ts, ax_ts = plt.subplots(figsize=(10, 4.5))
                    if hue_col == none_label:
                        sns.lineplot(data=series, x=date_col, y=var, marker="o", color="#0f766e", ax=ax_ts)
                    else:
                        sns.lineplot(data=series, x=date_col, y=var, hue=hue_col, marker="o", palette="viridis", ax=ax_ts)
                    ax_ts.set_title(t("eda.temporal.title_dynamic", var=var))
                    ax_ts.tick_params(axis="x", rotation=30)
                    st.pyplot(fig_ts)
                    plt.close(fig_ts)
            except Exception as e:
                st.error(f"Erro ao processar análise temporal: {e}")

    # ---------------- Tab 8: composition (NEW) ----------------
    with tab8:
        st.markdown(f"#### {t('eda.composition.title')}")
        if not cat_cols:
            st.info(t("eda.composition.no_cat"))
        else:
            default_cat = next((c for c in ("Crop_Type", "Cultura") if c in cat_cols), cat_cols[0])
            comp_col = st.selectbox(
                t("eda.composition.col"),
                options=cat_cols,
                index=cat_cols.index(default_cat),
                key="eda_composition_col",
            )
            counts = df[comp_col].value_counts(dropna=False)
            fig_comp, (ax_bar, ax_pie) = plt.subplots(1, 2, figsize=(12, 5))
            sns.barplot(
                x=counts.index.astype(str),
                y=counts.values,
                hue=counts.index.astype(str),
                legend=False,
                palette="viridis",
                ax=ax_bar,
            )
            ax_bar.tick_params(axis="x", rotation=30)
            ax_bar.set_title(t("eda.composition.title_dynamic", col=comp_col))
            ax_pie.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%", colors=sns.color_palette("viridis", len(counts)))
            ax_pie.set_title(t("eda.composition.title_dynamic", col=comp_col))
            st.pyplot(fig_comp)
            plt.close(fig_comp)

    # ---------------- Tab 9: inference (Kruskal-Wallis) ----------------
    with tab9:
        st.markdown(f"#### {t('eda.inference.title')}")
        st.caption(t("eda.inference.caption"))
        try:
            from scipy.stats import kruskal
        except ImportError:
            st.warning(t("eda.inference.missing_scipy"))
        else:
            if not cat_cols:
                st.info(t("eda.inference.no_cat"))
            else:
                default_group = next((c for c in ("Season", "Época") if c in cat_cols), cat_cols[0])
                group_col = st.selectbox(
                    t("eda.inference.group"),
                    options=cat_cols,
                    index=cat_cols.index(default_group),
                    key="eda_inf_group",
                )
                default_targets = [c for c in ("FCO2_DRY", "FCH4_DRY", "TS_2 initial_value", "SWC_2 initial_value") if c in numeric_cols]
                targets = st.multiselect(
                    t("eda.inference.targets"),
                    options=numeric_cols,
                    default=default_targets or numeric_cols[:3],
                    key="eda_inf_targets",
                )
                alpha = st.slider(t("eda.inference.alpha"), 0.001, 0.10, 0.05, 0.005, key="eda_inf_alpha")
                min_per_group = st.slider(
                    t("eda.inference.min_per_group"),
                    min_value=2,
                    max_value=30,
                    value=5,
                    step=1,
                    key="eda_inf_min_n",
                    help=t("eda.inference.min_per_group_help"),
                )

                rows = []
                for col in targets:
                    work = df[[group_col, col]].dropna()
                    if work.empty:
                        continue
                    grouped = list(work.groupby(group_col))
                    kept = [(name, g[col].values) for name, g in grouped if len(g) >= min_per_group]
                    dropped = [name for name, g in grouped if len(g) < min_per_group]
                    groups = [vals for _, vals in kept]
                    if len(groups) < 2:
                        rows.append({
                            "variable": col,
                            "groups": len(groups),
                            "H": np.nan,
                            "p_value": np.nan,
                            "significant": False,
                            "dropped_levels": ", ".join(map(str, dropped)) if dropped else "",
                        })
                        continue
                    try:
                        stat, p_value = kruskal(*groups)
                    except Exception:
                        rows.append({
                            "variable": col,
                            "groups": len(groups),
                            "H": np.nan,
                            "p_value": np.nan,
                            "significant": False,
                            "dropped_levels": ", ".join(map(str, dropped)) if dropped else "",
                        })
                        continue
                    rows.append({
                        "variable": col,
                        "groups": len(groups),
                        "H": round(float(stat), 4),
                        "p_value": float(p_value),
                        "significant": bool(p_value < alpha),
                        "dropped_levels": ", ".join(map(str, dropped)) if dropped else "",
                    })
                if rows:
                    result_df = pd.DataFrame(rows)
                    st.dataframe(result_df, use_container_width=True)
                    if (result_df["dropped_levels"] != "").any():
                        st.caption(":warning: " + t("eda.inference.dropped_caption", n=min_per_group))
                    st.download_button(
                        t("eda.inference.download"),
                        data=result_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"kruskal_{group_col}.csv",
                        mime="text/csv",
                    )

            st.markdown("---")
            st.markdown(f"##### {t('eda.normality.title')}")
            st.caption(t("eda.normality.caption"))
            try:
                from scipy.stats import shapiro, anderson, normaltest
            except ImportError:
                st.warning(t("eda.inference.missing_scipy"))
            else:
                default_norm = [c for c in ("FCO2_DRY", "FCH4_DRY", "TS_2 initial_value", "SWC_2 initial_value") if c in numeric_cols]
                norm_targets = st.multiselect(
                    t("eda.normality.targets"),
                    options=numeric_cols,
                    default=default_norm or numeric_cols[:3],
                    key="eda_norm_targets",
                )
                norm_alpha = st.slider(t("eda.normality.alpha"), 0.001, 0.10, 0.05, 0.005, key="eda_norm_alpha")
                norm_rows = []
                for col in norm_targets:
                    sample = df[col].dropna().to_numpy()
                    if len(sample) < 8:
                        continue
                    try:
                        sw_stat, sw_p = shapiro(sample[:5000]) if len(sample) > 5000 else shapiro(sample)
                    except Exception:
                        sw_stat, sw_p = float("nan"), float("nan")
                    try:
                        ad_res = anderson(sample, dist="norm")
                        ad_stat = float(ad_res.statistic)
                        ad_crit5 = float(ad_res.critical_values[2])
                        ad_reject = bool(ad_stat > ad_crit5)
                    except Exception:
                        ad_stat, ad_crit5, ad_reject = float("nan"), float("nan"), False
                    try:
                        dap_stat, dap_p = normaltest(sample)
                    except Exception:
                        dap_stat, dap_p = float("nan"), float("nan")
                    norm_rows.append({
                        "variable": col,
                        "n": int(len(sample)),
                        "shapiro_W": round(float(sw_stat), 4) if sw_stat == sw_stat else float("nan"),
                        "shapiro_p": float(sw_p) if sw_p == sw_p else float("nan"),
                        "anderson_A2": round(ad_stat, 4) if ad_stat == ad_stat else float("nan"),
                        "anderson_crit_5%": round(ad_crit5, 4) if ad_crit5 == ad_crit5 else float("nan"),
                        "anderson_reject_5%": ad_reject,
                        "dagostino_K2": round(float(dap_stat), 4) if dap_stat == dap_stat else float("nan"),
                        "dagostino_p": float(dap_p) if dap_p == dap_p else float("nan"),
                        "normal_at_alpha": bool((sw_p == sw_p and sw_p > norm_alpha) and (dap_p == dap_p and dap_p > norm_alpha) and not ad_reject),
                    })
                if norm_rows:
                    norm_df = pd.DataFrame(norm_rows)
                    st.dataframe(norm_df, use_container_width=True)
                    st.caption(":bulb: " + t("eda.normality.large_n_hint"))
                    st.download_button(
                        t("eda.normality.download"),
                        data=norm_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name="normality_tests.csv",
                        mime="text/csv",
                    )

                    # Q-Q plot por variável: complementa o p-value com diagnóstico visual,
                    # essencial quando n > algumas centenas e qualquer desvio leve gera p ≈ 0.
                    try:
                        from scipy.stats import probplot
                    except ImportError:
                        pass
                    else:
                        st.markdown(f"###### {t('eda.normality.qq_title')}")
                        qq_cols = [r["variable"] for r in norm_rows]
                        n_qq = len(qq_cols)
                        cols_per_row = min(3, n_qq) if n_qq > 0 else 1
                        n_rows_qq = (n_qq + cols_per_row - 1) // cols_per_row
                        fig_qq, axes_qq = plt.subplots(
                            n_rows_qq,
                            cols_per_row,
                            figsize=(4.5 * cols_per_row, 3.6 * n_rows_qq),
                            squeeze=False,
                        )
                        for idx, col in enumerate(qq_cols):
                            r, c = divmod(idx, cols_per_row)
                            ax = axes_qq[r][c]
                            sample = df[col].dropna().to_numpy()
                            if len(sample) >= 8:
                                probplot(sample, dist="norm", plot=ax)
                                ax.set_title(col, fontsize=10)
                                ax.grid(True, alpha=0.3)
                        for empty_idx in range(n_qq, n_rows_qq * cols_per_row):
                            r, c = divmod(empty_idx, cols_per_row)
                            axes_qq[r][c].axis("off")
                        fig_qq.tight_layout()
                        st.pyplot(fig_qq)
                        plt.close(fig_qq)

            st.markdown("---")
            st.markdown(f"##### {t('eda.vif.title')}")
            st.caption(t("eda.vif.caption"))
            st.caption(":information_source: " + t("eda.vif.derived_note"))
            try:
                from statsmodels.stats.outliers_influence import variance_inflation_factor
                from statsmodels.tools.tools import add_constant
            except ImportError:
                st.warning(t("eda.vif.missing_statsmodels"))
            else:
                default_vif = [c for c in ("TS_2 initial_value", "SWC_2 initial_value", "Latitude", "Longitude") if c in numeric_cols]
                vif_targets = st.multiselect(
                    t("eda.vif.targets"),
                    options=numeric_cols,
                    default=default_vif or numeric_cols[:3],
                    key="eda_vif_targets",
                )
                if len(vif_targets) >= 2:
                    vif_data = df[vif_targets].dropna()
                    if len(vif_data) >= len(vif_targets) + 1:
                        try:
                            X = add_constant(vif_data.to_numpy())
                            vif_rows = [
                                {"variable": col, "VIF": round(float(variance_inflation_factor(X, i + 1)), 4)}
                                for i, col in enumerate(vif_targets)
                            ]
                            vif_df = pd.DataFrame(vif_rows).sort_values("VIF", ascending=False)
                            st.dataframe(vif_df, use_container_width=True)
                            st.download_button(
                                t("eda.vif.download"),
                                data=vif_df.to_csv(index=False).encode("utf-8-sig"),
                                file_name="vif.csv",
                                mime="text/csv",
                            )
                        except Exception as exc:
                            st.error(t("eda.vif.error", error=str(exc)))
                    else:
                        st.info(t("eda.vif.too_few"))

    # ---------------- Tab 10: hotspots ----------------
    with tab10:
        st.markdown(f"#### {t('eda.hotspots.title')}")
        st.caption(t("eda.hotspots.caption"))
        if not cat_cols:
            st.info(t("eda.hotspots.no_cat"))
        else:
            default_group = next((c for c in ("Coll_Cluster", "Fazenda") if c in cat_cols), cat_cols[0])
            group_col = st.selectbox(
                t("eda.hotspots.group"),
                options=cat_cols,
                index=cat_cols.index(default_group),
                key="eda_hot_group",
            )
            default_target = "A" if "A" in numeric_cols else numeric_cols[0]
            target = st.selectbox(
                t("eda.hotspots.target"),
                options=numeric_cols,
                index=numeric_cols.index(default_target),
                key="eda_hot_target",
            )
            facet_options = [none_label] + cat_cols
            facet_col = st.selectbox(
                t("eda.hotspots.facet"),
                options=facet_options,
                key="eda_hot_facet",
            )
            top_n = st.slider(t("eda.hotspots.top_n"), 3, 30, 10, 1, key="eda_hot_topn")
            agg_label = st.radio(
                t("eda.hotspots.agg"),
                options=[t("eda.hotspots.agg.median"), t("eda.hotspots.agg.mean")],
                horizontal=True,
                key="eda_hot_agg",
            )
            agg_func = "median" if agg_label == t("eda.hotspots.agg.median") else "mean"

            keys = [group_col] if facet_col == none_label else [facet_col, group_col]
            ranking = (
                df[keys + [target]]
                .dropna()
                .groupby(keys)
                .agg(value=(target, agg_func), n=(target, "size"))
                .reset_index()
                .sort_values(["value"] if facet_col == none_label else [facet_col, "value"], ascending=[False] if facet_col == none_label else [True, False])
            )
            if facet_col != none_label:
                ranking = ranking.groupby(facet_col, group_keys=False).head(top_n)
            else:
                ranking = ranking.head(top_n)
            ranking["value"] = ranking["value"].round(4)

            st.dataframe(ranking, use_container_width=True)
            st.download_button(
                t("eda.hotspots.download"),
                data=ranking.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"hotspots_{target}_{group_col}.csv",
                mime="text/csv",
            )

            fig_h, ax_h = plt.subplots(figsize=(10, max(4, 0.35 * len(ranking))))
            if facet_col == none_label:
                order = ranking[group_col].astype(str).tolist()
                sns.barplot(
                    data=ranking,
                    y=group_col,
                    x="value",
                    order=order,
                    palette="rocket_r",
                    hue=group_col,
                    legend=False,
                    ax=ax_h,
                )
            else:
                sns.barplot(
                    data=ranking,
                    y=group_col,
                    x="value",
                    hue=facet_col,
                    palette="viridis",
                    ax=ax_h,
                )
            ax_h.set_xlabel(t("eda.hotspots.x_label", agg=agg_label, var=target))
            ax_h.set_ylabel(group_col)
            ax_h.set_title(t("eda.hotspots.title_dynamic", var=target, group=group_col))
            st.pyplot(fig_h)
            plt.close(fig_h)

    # ---------------- Tab 11: outliers (multi-method) ----------------
    with tab11:
        st.markdown(f"#### {t('eda.outliers.title')}")
        st.caption(t("eda.outliers.caption"))
        st.caption(":information_source: " + t("eda.outliers.assumptions"))

        default_out = [c for c in ("A", "E", "gs", "Chl_a_media", "IAF_media") if c in numeric_cols]
        out_targets = st.multiselect(
            t("eda.outliers.targets"),
            options=numeric_cols,
            default=default_out or numeric_cols[:3],
            key="eda_out_targets",
        )
        contamination = st.slider(t("eda.outliers.contamination"), 0.01, 0.20, 0.05, 0.01, key="eda_out_cont")

        if len(out_targets) >= 1:
            data = df[out_targets].dropna().copy()
            if len(data) < 20:
                st.info(t("eda.outliers.too_few"))
            else:
                z = (data - data.mean()) / data.std(ddof=0).replace(0, 1)
                z_flag = (z.abs() > 3).any(axis=1).astype(int)

                q1 = data.quantile(0.25)
                q3 = data.quantile(0.75)
                iqr = q3 - q1
                lo = q1 - 1.5 * iqr
                hi = q3 + 1.5 * iqr
                iqr_flag = ((data < lo) | (data > hi)).any(axis=1).astype(int)

                if_flag = pd.Series(0, index=data.index, dtype=int)
                lof_flag = pd.Series(0, index=data.index, dtype=int)
                env_flag = pd.Series(0, index=data.index, dtype=int)
                try:
                    from sklearn.ensemble import IsolationForest
                    from sklearn.neighbors import LocalOutlierFactor
                    from sklearn.covariance import EllipticEnvelope
                    from sklearn.preprocessing import StandardScaler

                    Xs = StandardScaler().fit_transform(data.to_numpy())
                    if_pred = IsolationForest(contamination=contamination, random_state=42).fit_predict(Xs)
                    if_flag = pd.Series((if_pred == -1).astype(int), index=data.index)
                    lof_pred = LocalOutlierFactor(contamination=contamination).fit_predict(Xs)
                    lof_flag = pd.Series((lof_pred == -1).astype(int), index=data.index)
                    if data.shape[1] >= 2 and len(data) >= 5 * data.shape[1]:
                        try:
                            env_pred = EllipticEnvelope(contamination=contamination, support_fraction=None, random_state=42).fit_predict(Xs)
                            env_flag = pd.Series((env_pred == -1).astype(int), index=data.index)
                        except Exception:
                            pass
                except ImportError:
                    st.warning(t("eda.outliers.missing_sklearn"))

                consensus = z_flag + iqr_flag + if_flag + lof_flag + env_flag
                audit = data.copy()
                audit["z_score"] = z_flag
                audit["iqr"] = iqr_flag
                audit["isolation_forest"] = if_flag
                audit["lof"] = lof_flag
                audit["elliptic_envelope"] = env_flag
                audit["votes"] = consensus
                audit["consensus_outlier"] = (consensus >= 3).astype(int)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Z-score", int(z_flag.sum()))
                c2.metric("IQR", int(iqr_flag.sum()))
                c3.metric("IsolationForest", int(if_flag.sum()))
                c4.metric("LOF", int(lof_flag.sum()))
                c5.metric(t("eda.outliers.consensus"), int(audit["consensus_outlier"].sum()))

                st.dataframe(audit.head(200), use_container_width=True)
                st.download_button(
                    t("eda.outliers.download"),
                    data=audit.to_csv(index=True).encode("utf-8-sig"),
                    file_name="outliers_audit.csv",
                    mime="text/csv",
                )

                fig_o, ax_o = plt.subplots(figsize=(8, 4.5))
                method_counts = {
                    "Z-score": int(z_flag.sum()),
                    "IQR": int(iqr_flag.sum()),
                    "IsolationForest": int(if_flag.sum()),
                    "LOF": int(lof_flag.sum()),
                    "EllipticEnvelope": int(env_flag.sum()),
                    t("eda.outliers.consensus"): int(audit["consensus_outlier"].sum()),
                }
                names = list(method_counts.keys())
                vals = list(method_counts.values())
                sns.barplot(x=names, y=vals, hue=names, palette="rocket", legend=False, ax=ax_o)
                ax_o.set_ylabel(t("eda.outliers.count"))
                ax_o.set_title(t("eda.outliers.summary_title"))
                ax_o.tick_params(axis="x", rotation=20)
                st.pyplot(fig_o)
                plt.close(fig_o)
