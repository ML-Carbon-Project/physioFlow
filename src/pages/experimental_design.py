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
    clean_factor_levels,
    compare_means,
    correlation_analysis,
    fit_dose_response,
    fit_experimental_anova,
    homoscedasticity_test,
    normality_test,
    partial_correlation,
)

# Cardinalidade máxima para sugerir uma coluna numérica como fator por padrão.
_MAX_FACTOR_LEVELS = 20

_DESIGN_LABEL_KEYS = {
    "DIC": "exp.design.dic",
    "DBC": "exp.design.dbc",
    "Fatorial": "exp.design.factorial",
    "Fatorial+Bloco": "exp.design.factorial_block",
    "Quadrado Latino": "exp.design.latin_square",
}

# Rótulos dos métodos de comparação de médias (nomes próprios, não traduzidos).
_METHOD_LABELS = {
    "tukey": "Tukey HSD",
    "scott-knott": "Scott-Knott",
    "duncan": "Duncan",
    "lsd": "LSD / DMS (Fisher)",
    "scheffe": "Scheffé",
}

# Função de src.stats_utils que implementa cada método (citada no script gerado).
_METHOD_FUNCS = {
    "scott-knott": "scott_knott_groups",
    "duncan": "duncan_groups",
    "lsd": "lsd_groups",
    "scheffe": "scheffe_groups",
}


def _format_p(p: float) -> str:
    if p != p:  # NaN
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.4f}"


def _build_script(
    response: str, treatment: str, block: str | None, factor2: str | None,
    formula: str, factor: str, method: str, alpha: float, factor3: str | None = None,
) -> str:
    """Gera um script Python autossuficiente que reproduz a análise.

    Reusa a mesma estratégia da página: renomeia as colunas para identificadores
    seguros (``y``, ``trat``, ``fator2``, ``fator3``, ``bloco``) e aplica a
    fórmula patsy literal — robusto a nomes com espaços/acentos no dataset.
    """
    rename = {response: "y", treatment: "trat"}
    if factor2:
        rename[factor2] = "fator2"
    if factor3:
        rename[factor3] = "fator3"
    if block:
        rename[block] = "bloco"
    cat_internal = [v for k, v in rename.items() if v != "y"]
    factor_internal = rename[factor]

    if method == "tukey":
        compare = (
            "# --- Tukey HSD ------------------------------------------------------------\n"
            "from statsmodels.stats.multicomp import pairwise_tukeyhsd\n\n"
            f'tukey = pairwise_tukeyhsd(data["y"], data["{factor_internal}"], alpha={alpha})\n'
            "print(tukey.summary())\n"
        )
    else:
        func = _METHOD_FUNCS.get(method, "scott_knott_groups")
        label = _METHOD_LABELS.get(method, method)
        compare = (
            f"# --- {label} -----------------------------------------------------\n"
            f"# {label} não vem no statsmodels; implementação em src/stats_utils.py\n"
            f"# ({func}). Abaixo, as médias por nível; combine com a função para\n"
            f"# obter as letras de agrupamento (precisa de ms_error e df do resíduo).\n"
            f'means = data.groupby("{factor_internal}")["y"].agg(["count", "mean", "std"])\n'
            'print(means.sort_values("mean", ascending=False))\n'
        )

    return f'''"""Análise de delineamento experimental gerada pelo PhysioFlow.

Delineamento (fórmula): {formula}
Mapeamento de colunas:
  resposta   = {response!r}  -> y
  tratamento = {treatment!r}  -> trat{f"""
  2º fator   = {factor2!r}  -> fator2""" if factor2 else ""}{f"""
  3º fator   = {factor3!r}  -> fator3""" if factor3 else ""}{f"""
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

    if result.covariate:
        st.caption(t(
            "exp.anova.covariate_info",
            cov=result.covariate,
            slope=f"{result.covariate_slope:.4g}",
            p=_format_p(result.covariate_pvalue),
        ))

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
    method_label = col2.selectbox(
        t("exp.compare.method"),
        options=["tukey", "scott-knott", "duncan", "lsd", "scheffe"],
        format_func=lambda m: _METHOD_LABELS.get(m, m),
        key="exp_compare_method",
    )

    # ANCOVA: compara médias AJUSTADAS pela covariável (só no fator tratamento).
    use_adjusted = bool(result.adjusted_means) and factor == result.factor_terms[0]
    override = result.adjusted_means if use_adjusted else None
    table = compare_means(
        df_clean, response, factor, result.ms_error, result.df_error,
        method=method_label, means_override=override,
    )
    if table.empty:
        st.info(t("exp.compare.no_data"))
        return method_label
    if use_adjusted:
        st.caption(t("exp.compare.adjusted_note", cov=result.covariate))

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
    factor3: str | None = None,
) -> None:
    st.markdown(f"#### {t('exp.code.title')}")
    st.caption(t("exp.code.caption"))

    script = _build_script(
        response, treatment, block, factor2, result.formula, factor, method, 0.05, factor3
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


def _render_design_mode(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str]) -> None:
    st.markdown(f"#### {t('exp.config.title')}")
    st.caption(t("exp.config.caption"))
    none_label = t("common.none")

    # Fatores codificados como número (bloco/repetição 1,2,3…) são comuns em
    # dados de campo. Permite promover colunas numéricas a fator; por padrão,
    # sugere as de baixa cardinalidade.
    low_card = [c for c in numeric_cols if df[c].nunique(dropna=True) <= _MAX_FACTOR_LEVELS]
    as_factor = st.multiselect(
        t("exp.config.numeric_as_factor"),
        options=numeric_cols, default=low_card,
        help=t("exp.config.numeric_as_factor_help"),
        key="exp_as_factor",
    )
    factor_cols = cat_cols + [c for c in as_factor]
    response_cols = [c for c in numeric_cols if c not in as_factor]

    if not factor_cols:
        st.warning(t("exp.no_cat"))
        return
    if not response_cols:
        st.warning(t("exp.config.no_response_left"))
        return

    c1, c2 = st.columns(2)
    response = c1.selectbox(t("exp.config.response"), options=response_cols, key="exp_response")
    treatment = c2.selectbox(t("exp.config.treatment"), options=factor_cols, key="exp_treatment")
    other_cats = [c for c in factor_cols if c != treatment]

    c3, c4 = st.columns(2)
    block_choice = c3.selectbox(
        t("exp.config.block"), options=[none_label] + other_cats,
        key="exp_block", help=t("exp.config.block_help"),
    )
    factor2_choice = c4.selectbox(
        t("exp.config.factor2"), options=[none_label] + other_cats,
        key="exp_factor2", help=t("exp.config.factor2_help"),
    )
    block = None if block_choice == none_label else block_choice
    factor2 = None if factor2_choice == none_label else factor2_choice

    factor3 = None
    if factor2:
        factor3_choice = st.selectbox(
            t("exp.config.factor3"),
            options=[none_label] + [c for c in other_cats if c != factor2],
            key="exp_factor3", help=t("exp.config.factor3_help"),
        )
        factor3 = None if factor3_choice == none_label else factor3_choice

    # Covariável: qualquer numérica (exceto a resposta), mesmo que numérica
    # tenha sido promovida a fator — o que importa é não usá-la em dois papéis.
    cov_options = [c for c in numeric_cols if c != response]
    covariate_choice = st.selectbox(
        t("exp.config.covariate"), options=[none_label] + cov_options,
        key="exp_covariate", help=t("exp.config.covariate_help"),
    )
    covariate = None if covariate_choice == none_label else covariate_choice

    with st.expander(t("exp.config.latin_square"), expanded=False):
        st.caption(t("exp.config.latin_help"))
        cl1, cl2 = st.columns(2)
        row_choice = cl1.selectbox(t("exp.config.row"), options=[none_label] + other_cats, key="exp_row")
        col_choice = cl2.selectbox(t("exp.config.column"), options=[none_label] + other_cats, key="exp_column")
    row = None if row_choice == none_label else row_choice
    column = None if col_choice == none_label else col_choice

    if row and column:
        block = factor2 = factor3 = covariate = None  # quadrado latino tem prioridade
        if row == column:
            st.error(t("exp.config.row_col_clash"))
            return
    elif factor2 and factor2 == block:
        st.error(t("exp.config.block_factor_clash"))
        return

    used = [treatment] + [c for c in (factor2, factor3, block, row, column) if c]
    if covariate and covariate in used:
        st.error(t("exp.config.covariate_clash"))
        return
    cols = [response] + used + ([covariate] if covariate else [])
    df_clean = df[cols].dropna().copy()
    df_clean = clean_factor_levels(df_clean, used)
    for c in used:
        df_clean[c] = df_clean[c].astype(str)

    if df_clean[treatment].nunique() < 2:
        st.warning(t("exp.config.few_levels"))
        return
    if len(df_clean) < 4:
        st.warning(t("exp.config.few_rows"))
        return

    try:
        result = fit_experimental_anova(
            df_clean, response, treatment, block, factor2, row, column, factor3, covariate
        )
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
        _render_comparison_tab(result, df_clean, response)
    with tabs[3]:
        factor = st.session_state.get("exp_compare_factor", treatment)
        method = st.session_state.get("exp_compare_method", "tukey")
        _render_reproducibility_tab(
            result, df_clean, response, treatment, block, factor2, factor, method, factor3
        )


def _render_dose_mode(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('exp.dose.title')}")
    st.caption(t("exp.dose.caption"))
    if len(numeric_cols) < 2:
        st.warning(t("exp.dose.need_numeric"))
        return

    c1, c2, c3 = st.columns(3)
    dose = c1.selectbox(t("exp.dose.dose_col"), options=numeric_cols, key="exp_dose_x")
    y_options = [c for c in numeric_cols if c != dose]
    response = c2.selectbox(t("exp.dose.response_col"), options=y_options, key="exp_dose_y")
    degree = c3.selectbox(
        t("exp.dose.degree"), options=[1, 2, 3], index=1,
        format_func=lambda d: {1: t("exp.dose.linear"), 2: t("exp.dose.quadratic"), 3: t("exp.dose.cubic")}[d],
        key="exp_dose_degree",
    )

    try:
        res = fit_dose_response(df, dose, response, degree)
    except ValueError as exc:
        st.warning(str(exc))
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("R²", f"{res.r2:.4f}")
    m2.metric(t("exp.dose.r2_adj"), f"{res.r2_adj:.4f}")
    m3.metric(t("exp.dose.top_term_p"), _format_p(res.top_term_pvalue))
    st.code(res.equation, language="text")
    if res.top_term_pvalue >= 0.05 and degree > 1:
        st.info(t("exp.dose.top_term_ns"))

    work = df[[dose, response]].dropna()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(work[dose], work[response], alpha=0.55, s=28, color=PRIMARY_COLOR, label=t("exp.dose.observed"))
    ax.plot(res.x_grid, res.y_grid, color="#b45309", linewidth=2.2, label=t("exp.dose.fit"))
    ax.set_xlabel(dose)
    ax.set_ylabel(response)
    ax.set_title(t("exp.dose.plot_title", y=response, x=dose))
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)


def _render_correlation_mode(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('exp.corr.title')}")
    st.caption(t("exp.corr.caption"))
    if len(numeric_cols) < 2:
        st.warning(t("exp.dose.need_numeric"))
        return

    method = st.radio(
        t("exp.corr.method"), options=["pearson", "spearman"],
        format_func=lambda m: "Pearson" if m == "pearson" else "Spearman",
        horizontal=True, key="exp_corr_method",
    )
    default_cols = numeric_cols[: min(8, len(numeric_cols))]
    selected = st.multiselect(
        t("exp.corr.vars"), options=numeric_cols, default=default_cols, key="exp_corr_vars"
    )
    if len(selected) < 2:
        st.info(t("exp.corr.select_two"))
        return

    res = correlation_analysis(df, selected, method=method)
    st.caption(t("exp.corr.n_obs", n=res.n_obs))

    fig, ax = plt.subplots(figsize=(0.9 * len(selected) + 2, 0.8 * len(selected) + 1.5))
    im = ax.imshow(res.corr.to_numpy(), vmin=-1, vmax=1, cmap="RdYlGn")
    ax.set_xticks(range(len(selected)))
    ax.set_xticklabels(selected, rotation=45, ha="right")
    ax.set_yticks(range(len(selected)))
    ax.set_yticklabels(selected)
    for i in range(len(selected)):
        for j in range(len(selected)):
            ax.text(j, i, f"{res.corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(t("exp.corr.heatmap_title", method=method.capitalize()))
    st.pyplot(fig)
    plt.close(fig)

    st.download_button(
        t("exp.corr.download"),
        data=res.corr.to_csv().encode("utf-8-sig"),
        file_name=f"correlacao_{method}.csv",
        mime="text/csv",
    )

    with st.expander(t("exp.corr.partial_title"), expanded=False):
        st.caption(t("exp.corr.partial_help"))
        pc1, pc2 = st.columns(2)
        x = pc1.selectbox(t("exp.corr.partial_x"), options=selected, key="exp_pc_x")
        y_opts = [c for c in selected if c != x]
        y = pc2.selectbox(t("exp.corr.partial_y"), options=y_opts, key="exp_pc_y")
        covar_opts = [c for c in selected if c not in (x, y)]
        covars = st.multiselect(t("exp.corr.partial_covars"), options=covar_opts, key="exp_pc_covars")
        if covars:
            r, p = partial_correlation(df, x, y, covars, method=method)
            raw = res.corr.loc[x, y]
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric(t("exp.corr.partial_raw"), f"{raw:.4f}")
            cc2.metric(t("exp.corr.partial_r"), f"{r:.4f}")
            cc3.metric(t("exp.corr.partial_p"), _format_p(p))
        else:
            st.info(t("exp.corr.partial_pick_covar"))


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

    mode = st.radio(
        t("exp.mode.label"),
        options=["design", "dose", "correlation"],
        format_func=lambda m: {
            "design": t("exp.mode.design"),
            "dose": t("exp.mode.dose"),
            "correlation": t("exp.mode.correlation"),
        }[m],
        horizontal=True,
        key="exp_mode",
    )
    st.divider()

    if mode == "design":
        _render_design_mode(df, numeric_cols, cat_cols)
    elif mode == "dose":
        _render_dose_mode(df, numeric_cols)
    else:
        _render_correlation_mode(df, numeric_cols)
