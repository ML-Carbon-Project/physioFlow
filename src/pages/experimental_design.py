"""Página de Estatística Experimental (delineamentos).

Ferramenta genérica — não assume nomes de colunas de fisiologia — para analisar
experimentos em DIC, DBC ou esquema fatorial sobre qualquer dataset carregado
(do projeto ou de terceiros). O usuário mapeia colunas para papéis (resposta,
tratamento, bloco, 2º fator) e a página infere o delineamento, roda a ANOVA,
testa pressupostos e compara médias por Tukey ou Scott-Knott.

Inspirada no fluxo do "Estatística Experimental no Rbio" (Bhering & Teodoro) e
no conceito *design-aware* do AgroDesign: além de exibir os resultados, oferece
o script Python equivalente para download — análise reprodutível e auditável.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.config.settings import PRIMARY_COLOR
from src.i18n import t
from src.stats_utils import (
    compare_means,
    fit_experimental_anova,
    homoscedasticity_test,
    normality_test,
)

_DESIGN_LABEL_KEYS = {
    "DIC": "exp.design.dic",
    "DBC": "exp.design.dbc",
    "Fatorial": "exp.design.factorial",
    "Fatorial+Bloco": "exp.design.factorial_block",
}


def _format_p(p: float) -> str:
    if p != p:  # NaN
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.4f}"


def _build_script(
    response: str, treatment: str, block: str | None, factor2: str | None,
    formula: str, factor: str, method: str, alpha: float,
) -> str:
    """Gera um script Python autossuficiente que reproduz a análise.

    Reusa a mesma estratégia da página: renomeia as colunas para identificadores
    seguros (``y``, ``trat``, ``fator2``, ``bloco``) e aplica a fórmula patsy
    literal — robusto a nomes com espaços/acentos no dataset original.
    """
    rename = {response: "y", treatment: "trat"}
    if factor2:
        rename[factor2] = "fator2"
    if block:
        rename[block] = "bloco"
    cat_internal = [v for k, v in rename.items() if v != "y"]
    factor_internal = rename[factor]

    if method == "scott-knott":
        compare = (
            "# --- Scott-Knott (grupos disjuntos) --------------------------------------\n"
            "# Scott-Knott não vem no statsmodels; implementação em src/stats_utils.py\n"
            "# (scott_knott_groups). Abaixo, as médias por nível; combine com a função\n"
            "# para obter as letras de agrupamento.\n"
            f'means = data.groupby("{factor_internal}")["y"].agg(["count", "mean", "std"])\n'
            'print(means.sort_values("mean", ascending=False))\n'
        )
    else:
        compare = (
            "# --- Tukey HSD ------------------------------------------------------------\n"
            "from statsmodels.stats.multicomp import pairwise_tukeyhsd\n\n"
            f'tukey = pairwise_tukeyhsd(data["y"], data["{factor_internal}"], alpha={alpha})\n'
            "print(tukey.summary())\n"
        )

    return f'''"""Análise de delineamento experimental gerada pelo PhysioFlow.

Delineamento (fórmula): {formula}
Mapeamento de colunas:
  resposta   = {response!r}  -> y
  tratamento = {treatment!r}  -> trat{f"""
  2º fator   = {factor2!r}  -> fator2""" if factor2 else ""}{f"""
  bloco      = {block!r}  -> bloco""" if block else ""}

Edite à vontade para novas análises ou melhoramentos.
"""
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols
from scipy import stats

# 1. Carregue os dados exportados pela página (botão "Baixar dados").
data = pd.read_csv("dados_experimento.csv")
data = data.rename(columns={rename!r})
data = data.dropna(subset=["y"] + {cat_internal!r})
for col in {cat_internal!r}:
    data[col] = data[col].astype(str)

# 2. ANOVA orientada ao delineamento.
model = ols("{formula}", data=data).fit()
anova = sm.stats.anova_lm(model, typ=2)
anova["mean_sq"] = anova["sum_sq"] / anova["df"]
print(anova)

ms_error = anova.loc["Residual", "sum_sq"] / anova.loc["Residual", "df"]
cv = (ms_error ** 0.5) / data["y"].mean() * 100
print(f"CV% = {{cv:.2f}}")

# 3. Pressupostos.
print("Shapiro-Wilk (normalidade):", stats.shapiro(model.resid))
groups = [g["y"].dropna().values for _, g in data.groupby("{factor_internal}")]
print("Levene (homocedasticidade):", stats.levene(*groups, center="median"))

# 4. Comparação de médias.
{compare}'''


def _render_anova_tab(result, df_clean: pd.DataFrame) -> None:
    st.markdown(f"#### {t('exp.anova.title')}")
    c1, c2, c3 = st.columns(3)
    c1.metric(t("exp.metric.design"), t(_DESIGN_LABEL_KEYS.get(result.design, result.design)))
    c2.metric(t("exp.metric.cv"), f"{result.cv_percent:.2f}%")
    c3.metric(t("exp.metric.n"), result.n_obs)

    display = result.table.copy()
    display["p_value"] = display["p_value"].map(_format_p)
    display = display.rename(columns={
        "df": t("exp.anova.col.df"),
        "sum_sq": t("exp.anova.col.sq"),
        "mean_sq": t("exp.anova.col.ms"),
        "F": "F",
        "p_value": t("exp.anova.col.p"),
    })
    st.dataframe(
        display.style.format({
            t("exp.anova.col.df"): "{:.0f}",
            t("exp.anova.col.sq"): "{:.4f}",
            t("exp.anova.col.ms"): "{:.4f}",
            "F": "{:.3f}",
        }, na_rep="—"),
        use_container_width=True,
    )

    # Interpretação automática dos termos de tratamento.
    msgs = []
    for term in result.factor_terms:
        match = [idx for idx in result.table.index if idx == term]
        if match:
            p = result.table.loc[term, "p_value"]
            key = "exp.anova.sig" if p < 0.05 else "exp.anova.nonsig"
            msgs.append(t(key, term=term, p=_format_p(p)))
    if msgs:
        st.info("  \n".join(msgs))

    st.download_button(
        t("exp.anova.download"),
        data=result.table.to_csv().encode("utf-8-sig"),
        file_name="anova_table.csv",
        mime="text/csv",
    )


def _render_assumptions_tab(result, df_clean: pd.DataFrame, treatment: str, response: str) -> None:
    st.markdown(f"#### {t('exp.assumptions.title')}")
    st.caption(t("exp.assumptions.caption"))

    norm = normality_test(result.residuals)
    homo = homoscedasticity_test(df_clean, response, treatment)

    rows = [
        {
            "test": t("exp.assumptions.normality"),
            "statistic": round(norm.statistic, 4) if norm.statistic == norm.statistic else None,
            "p_value": _format_p(norm.p_value),
            "ok": "✅" if norm.passed else "⚠️",
        },
        {
            "test": t("exp.assumptions.homoscedasticity"),
            "statistic": round(homo.statistic, 4) if homo.statistic == homo.statistic else None,
            "p_value": _format_p(homo.p_value),
            "ok": "✅" if homo.passed else "⚠️",
        },
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if not (norm.passed and homo.passed):
        st.warning(t("exp.assumptions.violated"))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    # QQ-plot dos resíduos
    from scipy import stats as sps
    res = result.residuals[~np.isnan(result.residuals)]
    sps.probplot(res, dist="norm", plot=axes[0])
    axes[0].set_title(t("exp.assumptions.qq_title"))
    axes[0].get_lines()[0].set_markerfacecolor(PRIMARY_COLOR)
    axes[0].get_lines()[0].set_markeredgecolor(PRIMARY_COLOR)
    axes[0].get_lines()[1].set_color("#b45309")
    # Resíduos vs ajustados
    axes[1].scatter(result.fitted, result.residuals, alpha=0.6, color=PRIMARY_COLOR, s=24)
    axes[1].axhline(0, color="#b45309", linewidth=1.2)
    axes[1].set_xlabel(t("exp.assumptions.fitted"))
    axes[1].set_ylabel(t("exp.assumptions.residuals"))
    axes[1].set_title(t("exp.assumptions.resid_title"))
    st.pyplot(fig)
    plt.close(fig)


def _render_comparison_tab(result, df_clean: pd.DataFrame, response: str) -> str:
    st.markdown(f"#### {t('exp.compare.title')}")
    st.caption(t("exp.compare.caption"))

    col1, col2 = st.columns(2)
    factor = col1.selectbox(
        t("exp.compare.factor"), options=result.factor_terms, key="exp_compare_factor"
    )
    method_label = col2.radio(
        t("exp.compare.method"),
        options=["tukey", "scott-knott"],
        format_func=lambda m: "Tukey HSD" if m == "tukey" else "Scott-Knott",
        horizontal=True,
        key="exp_compare_method",
    )

    table = compare_means(
        df_clean, response, factor, result.ms_error, result.df_error, method=method_label
    )
    if table.empty:
        st.info(t("exp.compare.no_data"))
        return method_label

    show = table.rename(columns={
        "group": t("exp.compare.col.group"),
        "n": "n",
        "mean": t("exp.compare.col.mean"),
        "std": t("exp.compare.col.std"),
        "group_letter": t("exp.compare.col.letter"),
    })
    st.dataframe(
        show.style.format({t("exp.compare.col.mean"): "{:.4f}", t("exp.compare.col.std"): "{:.4f}"}),
        use_container_width=True, hide_index=True,
    )
    st.caption(t("exp.compare.legend"))

    # Gráfico de barras com letras e erro-padrão.
    fig, ax = plt.subplots(figsize=(max(6, len(table) * 1.2), 5))
    se = table["std"] / np.sqrt(table["n"].clip(lower=1))
    bars = ax.bar(table["group"], table["mean"], yerr=se, capsize=4,
                  color=PRIMARY_COLOR, alpha=0.85, edgecolor="white")
    for bar, letter, m in zip(bars, table["group_letter"], table["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + se.max() * 0.15,
                str(letter), ha="center", va="bottom", fontweight="bold", color="#b45309")
    ax.set_ylabel(response)
    ax.set_xlabel(factor)
    ax.set_title(t("exp.compare.plot_title", var=response, factor=factor))
    plt.xticks(rotation=30, ha="right")
    st.pyplot(fig)
    plt.close(fig)

    st.download_button(
        t("exp.compare.download"),
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"means_{factor}_{method_label}.csv",
        mime="text/csv",
    )
    return method_label


def _render_reproducibility_tab(
    result, df_clean: pd.DataFrame, response: str, treatment: str,
    block: str | None, factor2: str | None, factor: str, method: str,
) -> None:
    st.markdown(f"#### {t('exp.code.title')}")
    st.caption(t("exp.code.caption"))

    script = _build_script(
        response, treatment, block, factor2, result.formula, factor, method, 0.05
    )
    # Trecho essencial: do bloco "# 2. ANOVA" até antes dos pressupostos.
    lines = script.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("# 2."))
        end = next(i for i, ln in enumerate(lines) if ln.startswith("# 3."))
        snippet = "\n".join(lines[start:end]).strip()
    except StopIteration:
        snippet = script
    with st.expander(t("exp.code.expander"), expanded=False):
        st.code(snippet, language="python")

    c1, c2 = st.columns(2)
    c1.download_button(
        t("exp.code.download_py"),
        data=script.encode("utf-8"),
        file_name="analise_delineamento.py",
        mime="text/x-python",
        use_container_width=True,
    )
    c2.download_button(
        t("exp.code.download_data"),
        data=df_clean.to_csv(index=False).encode("utf-8-sig"),
        file_name="dados_experimento.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render() -> None:
    st.subheader(t("exp.title"))
    st.caption(t("exp.intro"))

    df_raw = ensure_raw_dataframe(t("exp.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("exp_use_processed")
    if df is None:
        df = df_raw

    numeric_cols = list(df.select_dtypes(include="number").columns)
    cat_cols = [c for c in df.columns if c not in numeric_cols]
    if not numeric_cols:
        st.warning(t("exp.no_numeric"))
        return
    if not cat_cols:
        st.warning(t("exp.no_cat"))
        return

    st.markdown(f"#### {t('exp.config.title')}")
    st.caption(t("exp.config.caption"))
    none_label = t("common.none")

    c1, c2 = st.columns(2)
    response = c1.selectbox(t("exp.config.response"), options=numeric_cols, key="exp_response")
    treatment = c2.selectbox(t("exp.config.treatment"), options=cat_cols, key="exp_treatment")

    c3, c4 = st.columns(2)
    block_choice = c3.selectbox(
        t("exp.config.block"), options=[none_label] + [c for c in cat_cols if c != treatment],
        key="exp_block", help=t("exp.config.block_help"),
    )
    factor2_choice = c4.selectbox(
        t("exp.config.factor2"),
        options=[none_label] + [c for c in cat_cols if c != treatment],
        key="exp_factor2", help=t("exp.config.factor2_help"),
    )
    block = None if block_choice == none_label else block_choice
    factor2 = None if factor2_choice == none_label else factor2_choice
    if factor2 and factor2 == block:
        st.error(t("exp.config.block_factor_clash"))
        return

    cols = [response, treatment] + ([factor2] if factor2 else []) + ([block] if block else [])
    df_clean = df[cols].dropna().copy()
    for c in [treatment] + ([factor2] if factor2 else []) + ([block] if block else []):
        df_clean[c] = df_clean[c].astype(str)

    if df_clean[treatment].nunique() < 2:
        st.warning(t("exp.config.few_levels"))
        return
    if len(df_clean) < 4:
        st.warning(t("exp.config.few_rows"))
        return

    try:
        result = fit_experimental_anova(df_clean, response, treatment, block, factor2)
    except ValueError as exc:
        st.error(t("exp.error_fit", msg=str(exc)))
        return

    st.success(t("exp.detected", design=t(_DESIGN_LABEL_KEYS.get(result.design, result.design))))

    tabs = st.tabs([
        t("exp.tab.anova"),
        t("exp.tab.assumptions"),
        t("exp.tab.compare"),
        t("exp.tab.code"),
    ])
    with tabs[0]:
        _render_anova_tab(result, df_clean)
    with tabs[1]:
        _render_assumptions_tab(result, df_clean, treatment, response)
    with tabs[2]:
        method = _render_comparison_tab(result, df_clean, response)
    with tabs[3]:
        factor = st.session_state.get("exp_compare_factor", treatment)
        method = st.session_state.get("exp_compare_method", "tukey")
        _render_reproducibility_tab(
            result, df_clean, response, treatment, block, factor2, factor, method
        )
