"""Utilitários estatísticos compartilhados entre as páginas do app.

Estas funções são puramente computacionais e não dependem de Streamlit;
podem ser testadas isoladamente com pytest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import pi, sqrt
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ConfoundingPair:
    """Resultado da auditoria de confundimento entre duas categóricas.

    Attributes:
        col_a, col_b: nomes das colunas comparadas.
        cramers_v: Cramér's V (1.0 = associação perfeita; 0.0 = independência).
        determines_a_to_b: fração de níveis de ``col_a`` cujas observações caem em
            um único nível de ``col_b`` (1.0 quando A determina B).
        determines_b_to_a: análogo invertido.
        n_levels_a, n_levels_b: cardinalidade de cada coluna.
        n_obs: número de linhas usadas (após dropar NaN nas duas colunas).
    """

    col_a: str
    col_b: str
    cramers_v: float
    determines_a_to_b: float
    determines_b_to_a: float
    n_levels_a: int
    n_levels_b: int
    n_obs: int

    @property
    def is_redundant(self) -> bool:
        """True quando as duas colunas particionam as linhas exatamente igual.

        Mesmo número de níveis e cada nível de A mapeia para um único nível de B
        e vice-versa — efetivamente a mesma coluna com rótulos diferentes
        (caso Fazenda↔Cultura no dataset de fisiologia).
        """
        return (
            self.n_levels_a == self.n_levels_b
            and self.determines_a_to_b >= 0.999
            and self.determines_b_to_a >= 0.999
        )

    @property
    def is_confounded(self) -> bool:
        """True quando ao menos uma direção determina a outra com alta certeza.

        Não exige equivalência perfeita; o threshold padrão é 0.95 para tolerar
        ruído de digitação ou poucas linhas anômalas.
        """
        return self.determines_a_to_b >= 0.95 or self.determines_b_to_a >= 0.95


def cramers_v(df: pd.DataFrame, col_a: str, col_b: str) -> float:
    """Cramér's V corrigido por viés (Bergsma & Wicher 2013).

    Mede a força de associação entre duas categóricas em [0, 1].
    Retorna 0.0 quando as colunas não têm variação ou n=0.
    """
    work = df[[col_a, col_b]].dropna()
    if work.empty:
        return 0.0
    contingency = pd.crosstab(work[col_a], work[col_b]).to_numpy()
    if contingency.size == 0 or contingency.shape[0] < 2 or contingency.shape[1] < 2:
        return 0.0

    chi2 = _chi2_from_contingency(contingency)
    n = float(contingency.sum())
    r, c = contingency.shape
    phi2 = chi2 / n
    # correção de viés
    phi2_corr = max(0.0, phi2 - ((r - 1) * (c - 1)) / (n - 1))
    r_corr = r - ((r - 1) ** 2) / (n - 1)
    c_corr = c - ((c - 1) ** 2) / (n - 1)
    denom = min(r_corr - 1, c_corr - 1)
    if denom <= 0:
        return 0.0
    return float(np.sqrt(phi2_corr / denom))


def _chi2_from_contingency(contingency: np.ndarray) -> float:
    """Estatística χ² simples (sem usar scipy para manter este módulo leve)."""
    row_sums = contingency.sum(axis=1, keepdims=True)
    col_sums = contingency.sum(axis=0, keepdims=True)
    total = contingency.sum()
    if total == 0:
        return 0.0
    expected = row_sums * col_sums / total
    with np.errstate(divide="ignore", invalid="ignore"):
        diff_sq = (contingency - expected) ** 2
        terms = np.where(expected > 0, diff_sq / expected, 0.0)
    return float(terms.sum())


def _determination_ratio(df: pd.DataFrame, src: str, dst: str) -> float:
    """Fração de níveis de ``src`` cujas linhas caem em um único nível de ``dst``."""
    work = df[[src, dst]].dropna()
    if work.empty:
        return 0.0
    counts = work.groupby(src)[dst].nunique()
    if counts.empty:
        return 0.0
    return float((counts <= 1).mean())


def audit_pair_confounding(df: pd.DataFrame, col_a: str, col_b: str) -> ConfoundingPair:
    """Audita um único par de colunas categóricas."""
    work = df[[col_a, col_b]].dropna()
    return ConfoundingPair(
        col_a=col_a,
        col_b=col_b,
        cramers_v=cramers_v(work, col_a, col_b),
        determines_a_to_b=_determination_ratio(work, col_a, col_b),
        determines_b_to_a=_determination_ratio(work, col_b, col_a),
        n_levels_a=int(work[col_a].nunique()),
        n_levels_b=int(work[col_b].nunique()),
        n_obs=int(len(work)),
    )


def detect_confounded_pairs(
    df: pd.DataFrame,
    cat_cols: Sequence[str],
    min_levels: int = 2,
    max_levels: int = 30,
) -> list[ConfoundingPair]:
    """Audita todos os pares de colunas categóricas e devolve só os confundidos.

    Filtra previamente colunas com cardinalidade fora do intervalo ``[min_levels,
    max_levels]`` para não disparar em IDs únicos (cardinalidade = n) nem em
    constantes (cardinalidade = 1).

    Resultado ordenado por força de associação (Cramér's V) descendente.
    """
    usable = [
        c for c in cat_cols
        if c in df.columns and min_levels <= df[c].nunique(dropna=True) <= max_levels
    ]
    pairs: list[ConfoundingPair] = []
    for i, a in enumerate(usable):
        for b in usable[i + 1:]:
            result = audit_pair_confounding(df, a, b)
            if result.is_confounded and result.n_obs >= 5:
                pairs.append(result)
    pairs.sort(key=lambda p: p.cramers_v, reverse=True)
    return pairs


# ---------------------------------------------------------------------------
# Estatística experimental (delineamentos) — DIC, DBC, Fatorial.
#
# Estas funções implementam o núcleo da página "Estatística Experimental":
# ANOVA orientada ao delineamento, testes de pressupostos, e comparação de
# médias por Tukey (com letras) e Scott-Knott. São puramente computacionais
# (sem Streamlit) para permitir teste isolado com pytest.
#
# Decisão de projeto: tanto Tukey quanto Scott-Knott recebem o quadrado médio
# do resíduo (``ms_error``) e seus graus de liberdade (``df_error``) extraídos
# do modelo ajustado ao delineamento completo. Assim a comparação de médias em
# DBC usa o erro correto (com bloco), e não uma recomputação one-way — que seria
# estatisticamente inconsistente com o delineamento.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentalAnova:
    """Resultado de uma ANOVA orientada ao delineamento experimental.

    Attributes:
        design: rótulo interno do delineamento ("DIC", "DBC", "Fatorial",
            "Fatorial+Bloco").
        formula: fórmula patsy usada no ajuste (nomes internos seguros).
        table: quadro da ANOVA com índice = termo legível e colunas
            ``df, sum_sq, mean_sq, F, p_value``.
        ms_error: quadrado médio do resíduo (QMR).
        df_error: graus de liberdade do resíduo.
        cv_percent: coeficiente de variação experimental (%).
        grand_mean: média geral da variável-resposta.
        n_obs: número de observações usadas (após dropar NaN).
        residuals, fitted: resíduos e valores ajustados (para QQ-plot/diagnóstico).
        factor_terms: colunas (nomes originais) elegíveis para comparação de médias.
    """

    design: str
    formula: str
    table: pd.DataFrame
    ms_error: float
    df_error: float
    cv_percent: float
    grand_mean: float
    n_obs: int
    residuals: np.ndarray
    fitted: np.ndarray
    factor_terms: list[str] = field(default_factory=list)
    # Campos de ANCOVA (preenchidos só quando há covariável):
    covariate: Optional[str] = None
    covariate_slope: Optional[float] = None
    covariate_pvalue: Optional[float] = None
    adjusted_means: Optional[dict[str, float]] = None


# Tokens que representam ausência/lixo num fator categórico e devem ser tratados
# como dados faltantes (ex.: "." e "NA" na coluna sex do Palmer Penguins).
_JUNK_LEVELS = {"", ".", "na", "n/a", "nan", "null", "none", "?", "-", "--"}


def clean_factor_levels(df: pd.DataFrame, factor_cols: Sequence[str]) -> pd.DataFrame:
    """Remove linhas cujos fatores contêm níveis-lixo (``"."``, ``"NA"``, vazio…).

    Compara em minúsculas e com espaços removidos. Não altera colunas numéricas
    (NaN nelas já é tratado por ``dropna`` nas funções de análise).
    """
    work = df.copy()
    mask = pd.Series(True, index=work.index)
    for col in factor_cols:
        if col in work.columns:
            normalized = work[col].astype(str).str.strip().str.lower()
            mask &= ~normalized.isin(_JUNK_LEVELS)
    return work[mask]


def _term_label(term: str, names: dict[str, str]) -> str:
    """Converte um termo patsy (ex.: ``C(trat):C(fator2)``) em rótulo legível."""
    parts = term.split(":")
    human = []
    for part in parts:
        inner = part
        if part.startswith("C(") and part.endswith(")"):
            inner = part[2:-1]
        human.append(names.get(inner, inner))
    return " × ".join(human)


def fit_experimental_anova(
    df: pd.DataFrame,
    response: str,
    treatment: str,
    block: Optional[str] = None,
    factor2: Optional[str] = None,
    row: Optional[str] = None,
    column: Optional[str] = None,
    factor3: Optional[str] = None,
    covariate: Optional[str] = None,
) -> ExperimentalAnova:
    """Ajusta a ANOVA apropriada ao delineamento e devolve o quadro completo.

    O delineamento é inferido das colunas informadas:

    - apenas ``treatment``                         → DIC  (``y ~ trat``)
    - ``treatment`` + ``block``                    → DBC  (``y ~ trat + bloco``)
    - ``treatment`` + ``factor2``                  → Fatorial (``y ~ trat * fator2``)
    - ``treatment`` + ``factor2`` + ``factor3``    → Fatorial de 3 fatores
      (``y ~ trat * fator2 * fator3``, com todas as interações)
    - qualquer fatorial + ``block``                → Fatorial+Bloco
    - ``treatment`` + ``row`` + ``column``         → Quadrado Latino
      (``y ~ trat + linha + coluna`` — dois controles locais ortogonais)

    Quando ``row`` e ``column`` são informados, o delineamento é Quadrado Latino
    e ``block``/``factor2``/``factor3`` são ignorados. Linhas com níveis-lixo nos
    fatores (``"."``, ``"NA"``, vazio…) são descartadas.

    As colunas categóricas são convertidas para texto e renomeadas para
    identificadores seguros antes do ajuste, evitando que nomes com espaços ou
    caracteres especiais (ex.: ``"TS_2 initial_value"``) quebrem a fórmula patsy.

    Raises:
        ValueError: se faltarem dados suficientes (sem variação de tratamento,
            graus de liberdade de resíduo não positivos, ou média geral nula).
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols

    latin_square = bool(row and column)
    if latin_square:
        block = factor2 = factor3 = covariate = None
    if factor3 and not factor2:
        raise ValueError("O 3º fator exige um 2º fator definido.")

    factor_cols = [treatment] + [f for f in (factor2, block, row, column, factor3) if f]
    cols = [response] + factor_cols + ([covariate] if covariate else [])
    work = df[cols].dropna().copy()
    work = clean_factor_levels(work, factor_cols)

    rename = {response: "y", treatment: "trat"}
    if factor2:
        rename[factor2] = "fator2"
    if factor3:
        rename[factor3] = "fator3"
    if block:
        rename[block] = "bloco"
    if row:
        rename[row] = "linha"
    if column:
        rename[column] = "coluna"
    if covariate:
        rename[covariate] = "cov"
    work = work.rename(columns=rename)

    for cat in ("trat", "fator2", "fator3", "bloco", "linha", "coluna"):
        if cat in work.columns:
            work[cat] = work[cat].astype(str)

    if work["trat"].nunique() < 2:
        raise ValueError("O fator de tratamento precisa de pelo menos 2 níveis.")

    if latin_square:
        formula = "y ~ C(trat) + C(linha) + C(coluna)"
        design = "Quadrado Latino"
    else:
        treatment_terms = ["C(trat)"]
        if factor2:
            treatment_terms.append("C(fator2)")
        if factor3:
            treatment_terms.append("C(fator3)")
        if len(treatment_terms) > 1:
            rhs = " * ".join(treatment_terms)  # fatorial completo (todas as interações)
            design = "Fatorial"
        else:
            rhs = "C(trat)"
            design = "DIC"
        if block:
            rhs += " + C(bloco)"
            design = "DBC" if design == "DIC" else "Fatorial+Bloco"
        if covariate:
            rhs += " + cov"  # covariável contínua (ANCOVA)
        formula = "y ~ " + rhs

    model = ols(formula, data=work).fit()
    aov = sm.stats.anova_lm(model, typ=2)

    if "Residual" not in aov.index or aov.loc["Residual", "df"] <= 0:
        raise ValueError("Graus de liberdade do resíduo insuficientes para a ANOVA.")

    ms_error = float(aov.loc["Residual", "sum_sq"] / aov.loc["Residual", "df"])
    df_error = float(aov.loc["Residual", "df"])
    grand_mean = float(work["y"].mean())
    if grand_mean == 0:
        raise ValueError("Média geral igual a zero: CV% indefinido.")
    cv_percent = float(sqrt(ms_error) / abs(grand_mean) * 100.0)

    names = {
        "trat": treatment, "fator2": factor2 or "", "fator3": factor3 or "",
        "bloco": block or "", "linha": row or "", "coluna": column or "",
        "cov": covariate or "",
    }
    table = pd.DataFrame({
        "df": aov["df"].astype(float),
        "sum_sq": aov["sum_sq"].astype(float),
        "mean_sq": (aov["sum_sq"] / aov["df"]).astype(float),
        "F": aov["F"],
        "p_value": aov["PR(>F)"],
    })
    table.index = [
        "Residual" if term == "Residual" else _term_label(term, names)
        for term in aov.index
    ]

    factor_terms = [treatment] + [f for f in (factor2, factor3) if f]

    # ANCOVA: inclinação/significância da covariável e médias ajustadas.
    covariate_slope = covariate_pvalue = None
    adjusted_means = None
    if covariate:
        covariate_slope = float(model.params.get("cov", float("nan")))
        if covariate in (table.index):
            covariate_pvalue = float(table.loc[covariate, "p_value"])
        # Médias ajustadas só no caso de fator único (sem fatorial), onde a
        # fórmula clássica ȳ_i - b(x̄_i - x̄) é direta e inequívoca.
        if not factor2:
            cov_overall = float(work["cov"].mean())
            adjusted_means = {}
            for level, sub in work.groupby("trat"):
                adjusted_means[str(level)] = float(
                    sub["y"].mean() - covariate_slope * (sub["cov"].mean() - cov_overall)
                )

    return ExperimentalAnova(
        design=design,
        formula=formula,
        table=table,
        ms_error=ms_error,
        df_error=df_error,
        cv_percent=cv_percent,
        grand_mean=grand_mean,
        n_obs=int(len(work)),
        residuals=model.resid.to_numpy(),
        fitted=model.fittedvalues.to_numpy(),
        factor_terms=factor_terms,
        covariate=covariate,
        covariate_slope=covariate_slope,
        covariate_pvalue=covariate_pvalue,
        adjusted_means=adjusted_means,
    )


@dataclass(frozen=True)
class AssumptionResult:
    """Resultado de um teste de pressuposto da ANOVA."""

    name: str
    statistic: float
    p_value: float

    @property
    def passed(self) -> bool:
        """True quando não se rejeita o pressuposto a 5% (p > 0.05)."""
        return self.p_value > 0.05


def normality_test(residuals: np.ndarray) -> AssumptionResult:
    """Shapiro-Wilk sobre os resíduos do modelo (H0: resíduos normais)."""
    from scipy import stats as sps

    res = np.asarray(residuals, dtype=float)
    res = res[~np.isnan(res)]
    if len(res) < 3:
        return AssumptionResult("Shapiro-Wilk", float("nan"), float("nan"))
    stat, p = sps.shapiro(res)
    return AssumptionResult("Shapiro-Wilk", float(stat), float(p))


def homoscedasticity_test(
    df: pd.DataFrame, response: str, group: str
) -> AssumptionResult:
    """Levene (centrado na mediana) entre os níveis de ``group``.

    H0: variâncias homogêneas entre os grupos. Robusto a não-normalidade.
    """
    from scipy import stats as sps

    samples = [
        sub[response].dropna().to_numpy()
        for _, sub in df.groupby(group)
        if sub[response].dropna().size >= 2
    ]
    if len(samples) < 2:
        return AssumptionResult("Levene", float("nan"), float("nan"))
    stat, p = sps.levene(*samples, center="median")
    return AssumptionResult("Levene", float(stat), float(p))


def group_means(df: pd.DataFrame, response: str, factor: str) -> pd.DataFrame:
    """Tabela de médias por nível do fator, ordenada por média decrescente."""
    rows = []
    for level, sub in df.groupby(factor):
        x = sub[response].dropna()
        if len(x) == 0:
            continue
        rows.append({
            "group": str(level),
            "n": int(len(x)),
            "mean": float(x.mean()),
            "std": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
        })
    out = pd.DataFrame(rows).sort_values("mean", ascending=False).reset_index(drop=True)
    return out


def _maximal_cliques(nodes: list[str], adj: dict[str, set[str]]) -> list[set[str]]:
    """Enumera cliques maximais (Bron-Kerbosch com pivô). N pequeno → custo baixo."""
    cliques: list[set[str]] = []

    def bk(r: set[str], p: set[str], x: set[str]) -> None:
        if not p and not x:
            cliques.append(set(r))
            return
        pivot = next(iter(p | x))
        for v in list(p - adj[pivot]):
            bk(r | {v}, p & adj[v], x & adj[v])
            p = p - {v}
            x = x | {v}

    bk(set(), set(nodes), set())
    return cliques


def _compact_letter_display(
    means: dict[str, float], not_different: set[frozenset]
) -> dict[str, str]:
    """Atribui letras de significância a partir dos pares NÃO diferentes.

    Dois grupos compartilham ao menos uma letra se, e somente se, não diferem
    significativamente. Implementado via cliques maximais do grafo de
    não-diferença — correto mesmo quando as relações não são transitivas.
    """
    groups = list(means)
    adj: dict[str, set[str]] = {g: set() for g in groups}
    for pair in not_different:
        a, b = tuple(pair)
        adj[a].add(b)
        adj[b].add(a)

    cliques = _maximal_cliques(groups, adj)
    # Ordena cliques pela maior média interna (decrescente) → letra 'a' no topo.
    cliques.sort(key=lambda c: max(means[g] for g in c), reverse=True)

    letters: dict[str, list[str]] = {g: [] for g in groups}
    for idx, clique in enumerate(cliques):
        letter = chr(ord("a") + idx)
        for g in clique:
            letters[g].append(letter)
    return {g: "".join(sorted(set(ls))) for g, ls in letters.items()}


def tukey_groups(
    means: dict[str, float],
    ns: dict[str, int],
    ms_error: float,
    df_error: float,
    alpha: float = 0.05,
) -> dict[str, str]:
    """Tukey-Kramer (HSD) usando o QMR do delineamento; devolve letras por grupo.

    Para cada par usa o intervalo da amplitude estudentizada
    ``q(alpha, k, df_error)`` e ``HSD_ij = q * sqrt((QMR/2)(1/n_i + 1/n_j))``,
    o que acomoda repetições desiguais (versão Tukey-Kramer).
    """
    from scipy import stats as sps

    groups = list(means)
    k = len(groups)
    if k < 2:
        return {g: "a" for g in groups}

    q = float(sps.studentized_range.ppf(1 - alpha, k, df_error))
    not_different: set[frozenset] = set()
    for i in range(k):
        for j in range(i + 1, k):
            a, b = groups[i], groups[j]
            hsd = q * sqrt((ms_error / 2.0) * (1.0 / ns[a] + 1.0 / ns[b]))
            if abs(means[a] - means[b]) <= hsd:
                not_different.add(frozenset((a, b)))
    return _compact_letter_display(means, not_different)


def scott_knott_groups(
    means: dict[str, float],
    ns: dict[str, int],
    ms_error: float,
    df_error: float,
    alpha: float = 0.05,
) -> dict[str, str]:
    """Agrupamento de médias por Scott-Knott (1974).

    Diferente do Tukey, produz grupos disjuntos: cada tratamento recebe
    exatamente uma letra (sem ambiguidade), o que é o padrão em melhoramento
    vegetal brasileiro. Implementa a formulação de Jelihovschi et al. (2014):

    - estima ``sigma2_0`` uma única vez com todas as k médias;
    - para cada nó, encontra a partição contígua que maximiza B;
    - estatística ``lambda = (pi/(2(pi-2))) * B / sigma2_0`` comparada a
      ``chi2`` com ``nu0 = k/(pi-2)`` graus de liberdade.

    Para repetições desiguais usa a média harmônica das repetições como ``r``.
    """
    from scipy import stats as sps

    groups_sorted = sorted(means, key=lambda g: means[g], reverse=True)
    k = len(groups_sorted)
    if k < 2:
        return {g: "a" for g in groups_sorted}

    vals = [means[g] for g in groups_sorted]
    n_values = [ns[g] for g in groups_sorted]
    r_harm = k / sum(1.0 / n for n in n_values)  # média harmônica das repetições
    s2_mean = ms_error / r_harm                   # variância estimada de uma média

    overall = sum(vals) / k
    sigma2_0 = (sum((v - overall) ** 2 for v in vals) + df_error * s2_mean) / (k + df_error)
    if sigma2_0 <= 0:
        return {g: "a" for g in groups_sorted}

    nu0 = k / (pi - 2.0)
    chi2_crit = float(sps.chi2.ppf(1 - alpha, nu0))
    factor = pi / (2.0 * (pi - 2.0))

    def best_cut(sub: list[float]) -> tuple[float, int]:
        g = len(sub)
        total = sum(sub)
        best_b, best_c = -1.0, 1
        for cut in range(1, g):
            t1 = sum(sub[:cut])
            t2 = total - t1
            b = t1 * t1 / cut + t2 * t2 / (g - cut) - total * total / g
            if b > best_b:
                best_b, best_c = b, cut
        return best_b, best_c

    assignment: dict[str, str] = {}
    letter_state = ["a"]

    def recurse(indices: list[int]) -> None:
        if len(indices) == 1:
            assignment[groups_sorted[indices[0]]] = letter_state[0]
            letter_state[0] = chr(ord(letter_state[0]) + 1)
            return
        sub = [vals[i] for i in indices]
        b_max, cut = best_cut(sub)
        lam = factor * (b_max / sigma2_0)
        if lam > chi2_crit:
            recurse(indices[:cut])
            recurse(indices[cut:])
        else:
            letter = letter_state[0]
            for i in indices:
                assignment[groups_sorted[i]] = letter
            letter_state[0] = chr(ord(letter) + 1)

    recurse(list(range(k)))
    return assignment


def _letters_from_threshold(means, ns, threshold_fn) -> dict[str, str]:
    """CLD a partir de uma função de limiar por par ``(n_i, n_j) -> limite``.

    Dois grupos não diferem quando ``|m_i - m_j| <= threshold_fn(n_i, n_j)``.
    """
    groups = list(means)
    not_different: set[frozenset] = set()
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a, b = groups[i], groups[j]
            if abs(means[a] - means[b]) <= threshold_fn(ns[a], ns[b]):
                not_different.add(frozenset((a, b)))
    return _compact_letter_display(means, not_different)


def lsd_groups(
    means: dict[str, float], ns: dict[str, int],
    ms_error: float, df_error: float, alpha: float = 0.05,
) -> dict[str, str]:
    """Fisher LSD / DMS: ``LSD_ij = t(α/2, gl) · sqrt(QMR(1/n_i + 1/n_j))``.

    Mais liberal (sem correção para comparações múltiplas); acomoda n desiguais.
    """
    from scipy import stats as sps

    if len(means) < 2:
        return {g: "a" for g in means}
    t = float(sps.t.ppf(1 - alpha / 2, df_error))
    return _letters_from_threshold(
        means, ns, lambda na, nb: t * sqrt(ms_error * (1.0 / na + 1.0 / nb))
    )


def scheffe_groups(
    means: dict[str, float], ns: dict[str, int],
    ms_error: float, df_error: float, alpha: float = 0.05,
) -> dict[str, str]:
    """Scheffé: limiar ``sqrt((k-1)·F(α,k-1,gl)) · sqrt(QMR(1/n_i + 1/n_j))``.

    O mais conservador dos testes pareados; acomoda n desiguais.
    """
    from scipy import stats as sps

    k = len(means)
    if k < 2:
        return {g: "a" for g in means}
    crit = sqrt((k - 1) * float(sps.f.ppf(1 - alpha, k - 1, df_error)))
    return _letters_from_threshold(
        means, ns, lambda na, nb: crit * sqrt(ms_error * (1.0 / na + 1.0 / nb))
    )


def duncan_groups(
    means: dict[str, float], ns: dict[str, int],
    ms_error: float, df_error: float, alpha: float = 0.05,
) -> dict[str, str]:
    """Teste de amplitude múltipla de Duncan (rank-based).

    Para duas médias separadas por ``p`` posições no ranking, o limiar usa a
    amplitude estudentizada com nível de proteção ``α_p = 1 - (1-α)^(p-1)``:
    ``R_p = q(α_p, p, gl) · sqrt(QMR / r)``. Para n desiguais usa a média
    harmônica das repetições como ``r``.
    """
    from scipy import stats as sps

    groups_sorted = sorted(means, key=lambda g: means[g], reverse=True)
    k = len(groups_sorted)
    if k < 2:
        return {g: "a" for g in groups_sorted}
    r_harm = k / sum(1.0 / ns[g] for g in groups_sorted)
    se = sqrt(ms_error / r_harm)

    not_different: set[frozenset] = set()
    for i in range(k):
        for j in range(i + 1, k):
            p = j - i + 1
            alpha_p = 1.0 - (1.0 - alpha) ** (p - 1)
            q_p = float(sps.studentized_range.ppf(1 - alpha_p, p, df_error))
            r_p = q_p * se
            a, b = groups_sorted[i], groups_sorted[j]
            if abs(means[a] - means[b]) <= r_p:
                not_different.add(frozenset((a, b)))
    return _compact_letter_display(means, not_different)


def dunnett_test(
    df: pd.DataFrame, response: str, factor: str, control: str, alpha: float = 0.05
) -> pd.DataFrame:
    """Teste de Dunnett: cada tratamento vs um controle (não usa letras).

    Devolve uma tabela com média, diferença para o controle, valor-p (bicaudal)
    e se difere do controle. Usa ``scipy.stats.dunnett`` (distribuição t
    multivariada — o ajuste correto para comparações com um controle).
    """
    from scipy.stats import dunnett

    groups = group_means(df, response, factor)
    levels = groups["group"].tolist()
    if control not in levels or len(levels) < 2:
        return pd.DataFrame()

    control_vals = df.loc[df[factor].astype(str) == control, response].dropna().to_numpy()
    others = [lvl for lvl in levels if lvl != control]
    samples = [df.loc[df[factor].astype(str) == lvl, response].dropna().to_numpy() for lvl in others]

    res = dunnett(*samples, control=control_vals, alternative="two-sided")
    mean_map = dict(zip(groups["group"], groups["mean"]))
    n_map = dict(zip(groups["group"], groups["n"]))
    ctrl_mean = mean_map[control]
    rows = [{
        "group": control, "n": n_map[control], "mean": ctrl_mean,
        "diff_vs_control": 0.0, "p_value": float("nan"), "is_control": True,
        "differs": False,
    }]
    for lvl, stat, p in zip(others, res.statistic, res.pvalue):
        rows.append({
            "group": lvl, "n": n_map[lvl], "mean": mean_map[lvl],
            "diff_vs_control": float(mean_map[lvl] - ctrl_mean),
            "p_value": float(p), "is_control": False, "differs": bool(p < alpha),
        })
    return pd.DataFrame(rows).sort_values("mean", ascending=False).reset_index(drop=True)


# Despachante de métodos de comparação de médias.
MEAN_COMPARISON_METHODS: dict[str, object] = {
    "tukey": tukey_groups,
    "scott-knott": scott_knott_groups,
    "duncan": duncan_groups,
    "lsd": lsd_groups,
    "scheffe": scheffe_groups,
}


def compare_means(
    df: pd.DataFrame,
    response: str,
    factor: str,
    ms_error: float,
    df_error: float,
    method: str = "tukey",
    alpha: float = 0.05,
    means_override: Optional[dict[str, float]] = None,
) -> pd.DataFrame:
    """Tabela de médias com letras de significância pelo método escolhido.

    ``method`` ∈ {``"tukey"``, ``"scott-knott"``, ``"duncan"``, ``"lsd"``,
    ``"scheffe"``}. Devolve a tabela de ``group_means`` acrescida da coluna
    ``group_letter``.

    ``means_override`` substitui as médias brutas (ex.: médias ajustadas de
    ANCOVA); ``n`` e ``std`` brutos são mantidos (usados só na visualização).
    """
    table = group_means(df, response, factor)
    if table.empty:
        return table
    if means_override is not None:
        table["mean"] = table["group"].map(means_override)
        table = table.sort_values("mean", ascending=False).reset_index(drop=True)
    means = dict(zip(table["group"], table["mean"]))
    ns = dict(zip(table["group"], table["n"]))
    fn = MEAN_COMPARISON_METHODS.get(method, tukey_groups)
    letters = fn(means, ns, ms_error, df_error, alpha)
    table["group_letter"] = table["group"].map(letters)
    return table


# ---------------------------------------------------------------------------
# Parcelas subdivididas (split-plot) — delineamento com erro composto.
#
# Dois fatores e DOIS termos de erro: o fator de parcela (whole-plot) é testado
# contra o Erro(a) [bloco×parcela]; o fator de subparcela e a interação são
# testados contra o Erro(b) [resíduo]. Implementação para dados balanceados em
# blocos (RCBD), seguindo a montagem clássica de EMS. statsmodels fornece as
# somas de quadrados (ortogonais no caso balanceado); os testes F com o
# denominador correto são montados manualmente.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SplitPlotAnova:
    """Quadro de ANOVA de parcelas subdivididas com os dois termos de erro."""

    table: pd.DataFrame          # índice = fonte de variação; cols df, sum_sq, mean_sq, F, p_value
    formula: str
    n_obs: int
    grand_mean: float
    cv_a_percent: float          # CV das parcelas (Erro a)
    cv_b_percent: float          # CV das subparcelas (Erro b)
    residuals: np.ndarray
    fitted: np.ndarray


def fit_split_plot(
    df: pd.DataFrame,
    response: str,
    whole_plot: str,
    subplot: str,
    block: str,
) -> SplitPlotAnova:
    """Ajusta a ANOVA de parcelas subdivididas (split-plot em blocos).

    - ``whole_plot``: fator aplicado às parcelas (testado contra o Erro a);
    - ``subplot``: fator aplicado às subparcelas (testado contra o Erro b);
    - ``block``: bloco/repetição. O Erro(a) é a interação bloco×parcela.

    Pressupõe dados balanceados. Raises ValueError se faltar variação ou se os
    graus de liberdade de algum erro forem não positivos.
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from scipy import stats as sps

    factor_cols = [whole_plot, subplot, block]
    work = df[[response] + factor_cols].dropna().copy()
    work = clean_factor_levels(work, factor_cols)
    work = work.rename(columns={response: "y", whole_plot: "A", subplot: "B", block: "blk"})
    for c in ("A", "B", "blk"):
        work[c] = work[c].astype(str)

    if work["A"].nunique() < 2 or work["B"].nunique() < 2 or work["blk"].nunique() < 2:
        raise ValueError("Parcelas subdivididas exigem ≥2 níveis de parcela, subparcela e bloco.")

    formula = "y ~ C(blk) + C(A) + C(blk):C(A) + C(B) + C(A):C(B)"
    model = ols(formula, data=work).fit()
    aov = sm.stats.anova_lm(model, typ=1)

    def cell(term: str) -> tuple[float, float]:
        return float(aov.loc[term, "sum_sq"]), float(aov.loc[term, "df"])

    ss_blk, df_blk = cell("C(blk)")
    ss_a, df_a = cell("C(A)")
    ss_ea, df_ea = cell("C(blk):C(A)")
    ss_b, df_b = cell("C(B)")
    ss_ab, df_ab = cell("C(A):C(B)")
    ss_eb, df_eb = float(aov.loc["Residual", "sum_sq"]), float(aov.loc["Residual", "df"])

    if df_ea <= 0 or df_eb <= 0:
        raise ValueError("Graus de liberdade de erro insuficientes (dados desbalanceados?).")

    ms_ea, ms_eb = ss_ea / df_ea, ss_eb / df_eb
    f_a = (ss_a / df_a) / ms_ea
    f_b = (ss_b / df_b) / ms_eb
    f_ab = (ss_ab / df_ab) / ms_eb
    nan = float("nan")
    rows = [
        (block, df_blk, ss_blk, ss_blk / df_blk, nan, nan),
        (whole_plot, df_a, ss_a, ss_a / df_a, f_a, float(sps.f.sf(f_a, df_a, df_ea))),
        ("Erro(a)", df_ea, ss_ea, ms_ea, nan, nan),
        (subplot, df_b, ss_b, ss_b / df_b, f_b, float(sps.f.sf(f_b, df_b, df_eb))),
        (f"{whole_plot} × {subplot}", df_ab, ss_ab, ss_ab / df_ab, f_ab, float(sps.f.sf(f_ab, df_ab, df_eb))),
        ("Erro(b)", df_eb, ss_eb, ms_eb, nan, nan),
    ]
    table = pd.DataFrame(
        rows, columns=["source", "df", "sum_sq", "mean_sq", "F", "p_value"]
    ).set_index("source")

    grand_mean = float(work["y"].mean())
    return SplitPlotAnova(
        table=table,
        formula=formula,
        n_obs=int(len(work)),
        grand_mean=grand_mean,
        cv_a_percent=float(sqrt(ms_ea) / abs(grand_mean) * 100.0),
        cv_b_percent=float(sqrt(ms_eb) / abs(grand_mean) * 100.0),
        residuals=model.resid.to_numpy(),
        fitted=model.fittedvalues.to_numpy(),
    )


# ---------------------------------------------------------------------------
# Faixas (strip-plot) e hierárquico (nested) — delineamentos de erro composto.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompositeAnova:
    """Quadro de ANOVA de delineamento com múltiplos termos de erro."""

    design: str
    table: pd.DataFrame          # fonte de variação × (df, sum_sq, mean_sq, F, p_value)
    formula: str
    n_obs: int
    grand_mean: float
    residuals: np.ndarray
    fitted: np.ndarray


def _fit_composite(df, response, factor_cols, rename, formula, design, f_tests):
    """Helper: ajusta OLS, monta o quadro e aplica testes F com erro escolhido.

    ``f_tests`` mapeia termo testado → termo de erro (ambos no índice do anova_lm).
    Linhas sem teste explícito ficam com F/p = NaN (termos de erro/bloco).
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from scipy import stats as sps

    work = df[[response] + factor_cols].dropna().copy()
    work = clean_factor_levels(work, factor_cols)
    work = work.rename(columns=rename)
    for c in rename.values():
        if c != "y":
            work[c] = work[c].astype(str)

    model = ols(formula, data=work).fit()
    aov = sm.stats.anova_lm(model, typ=1)

    ms = {term: float(aov.loc[term, "sum_sq"]) / float(aov.loc[term, "df"]) for term in aov.index}
    nan = float("nan")
    rows = []
    for term in aov.index:
        f_val = p_val = nan
        if term in f_tests:
            err = f_tests[term]
            f_val = ms[term] / ms[err]
            p_val = float(sps.f.sf(f_val, float(aov.loc[term, "df"]), float(aov.loc[err, "df"])))
        rows.append({
            "source": term, "df": float(aov.loc[term, "df"]),
            "sum_sq": float(aov.loc[term, "sum_sq"]), "mean_sq": ms[term],
            "F": f_val, "p_value": p_val,
        })
    table = pd.DataFrame(rows).set_index("source")
    return CompositeAnova(
        design=design, table=table, formula=formula, n_obs=int(len(work)),
        grand_mean=float(work["y"].mean()),
        residuals=model.resid.to_numpy(), fitted=model.fittedvalues.to_numpy(),
    )


def fit_strip_plot(df, response, factor_a, factor_b, block) -> CompositeAnova:
    """Faixas (strip-plot/split-block): A e B em faixas cruzadas, 3 erros.

    A é testado vs Erro(a)=bloco×A; B vs Erro(b)=bloco×B; A×B vs Erro(c)=resíduo.
    Pressupõe dados balanceados em blocos.
    """
    rename = {response: "y", factor_a: "A", factor_b: "B", block: "blk"}
    formula = "y ~ C(blk) + C(A) + C(blk):C(A) + C(B) + C(blk):C(B) + C(A):C(B)"
    res = _fit_composite(
        df, response, [factor_a, factor_b, block], rename, formula, "Faixas",
        f_tests={"C(A)": "C(blk):C(A)", "C(B)": "C(blk):C(B)", "C(A):C(B)": "Residual"},
    )
    names = {"C(blk)": block, "C(A)": factor_a, "C(B)": factor_b,
             "C(blk):C(A)": "Erro(a)", "C(blk):C(B)": "Erro(b)",
             "C(A):C(B)": f"{factor_a} × {factor_b}", "Residual": "Erro(c)"}
    res.table.index = [names.get(i, i) for i in res.table.index]
    return res


def fit_nested(df, response, factor_a, factor_b) -> CompositeAnova:
    """Hierárquico (nested): B aninhado em A. A é testado vs B(A); B(A) vs resíduo.

    O fator aninhado recebe um rótulo único ``A::B`` antes do ajuste, garantindo
    a decomposição correta mesmo quando os níveis de B se repetem entre níveis de
    A (ex.: subamostras 1,2,3 dentro de cada A).
    """
    from scipy import stats as sps

    work = df[[response, factor_a, factor_b]].dropna().copy()
    work = clean_factor_levels(work, [factor_a, factor_b])
    work = work.rename(columns={response: "y", factor_a: "A", factor_b: "B"})
    work["A"] = work["A"].astype(str)
    work["AB"] = work["A"] + " :: " + work["B"].astype(str)  # rótulo aninhado único

    # Decomposição nested clássica por somas de quadrados (exata; evita as
    # armadilhas de codificação do patsy para fatores aninhados).
    y = work["y"].to_numpy(dtype=float)
    n_obs = len(work)
    grand = float(y.mean())
    n_a = work["A"].nunique()
    n_ab = work["AB"].nunique()
    if n_a < 2 or n_ab <= n_a or n_obs <= n_ab:
        raise ValueError("Dados insuficientes para o delineamento hierárquico.")

    ss_total = float(((y - grand) ** 2).sum())
    ss_a = float(work.groupby("A")["y"].apply(lambda s: len(s) * (s.mean() - grand) ** 2).sum())
    ab_means = work.groupby("AB")["y"].transform("mean")
    ss_ab = float(((ab_means - grand) ** 2).sum())   # entre subgrupos
    ss_ba = ss_ab - ss_a                              # B dentro de A
    ss_resid = ss_total - ss_ab

    df_a, df_ba, df_resid = n_a - 1, n_ab - n_a, n_obs - n_ab
    ms_a, ms_ba, ms_resid = ss_a / df_a, ss_ba / df_ba, ss_resid / df_resid
    f_a, f_ba = ms_a / ms_ba, ms_ba / ms_resid
    nan = float("nan")
    rows = [
        (factor_a, df_a, ss_a, ms_a, f_a, float(sps.f.sf(f_a, df_a, df_ba))),
        (f"{factor_b} ({factor_a})", df_ba, ss_ba, ms_ba, f_ba, float(sps.f.sf(f_ba, df_ba, df_resid))),
        ("Erro", df_resid, ss_resid, ms_resid, nan, nan),
    ]
    table = pd.DataFrame(rows, columns=["source", "df", "sum_sq", "mean_sq", "F", "p_value"]).set_index("source")
    residuals = (work["y"] - ab_means).to_numpy()
    return CompositeAnova(
        design="Hierárquico", table=table, formula="y ~ A + B(A) (nested)", n_obs=n_obs,
        grand_mean=grand, residuals=residuals, fitted=ab_means.to_numpy(),
    )


# ---------------------------------------------------------------------------
# Regressão de doses (fator quantitativo) — resposta a níveis crescentes de um
# insumo (adubo, lâmina de irrigação, densidade etc.).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DoseResponse:
    """Ajuste polinomial da resposta a um fator quantitativo (dose)."""

    degree: int
    coef: list[float]            # [b0, b1, b2, ...] crescente em grau
    r2: float
    r2_adj: float
    f_pvalue: float
    top_term_pvalue: float       # significância do termo de maior grau
    n: int
    equation: str
    x_grid: np.ndarray
    y_grid: np.ndarray


def fit_dose_response(
    df: pd.DataFrame, dose: str, response: str, degree: int = 2
) -> DoseResponse:
    """Ajusta um polinômio de grau ``degree`` (1=linear, 2=quadrático, 3=cúbico).

    Devolve coeficientes, R²/R² ajustado, significância global (F) e do termo de
    maior grau, além de uma grade densa para traçar a curva.

    Raises:
        ValueError: se houver níveis de dose insuficientes para o grau pedido.
    """
    import statsmodels.api as sm

    work = df[[dose, response]].dropna()
    x = work[dose].astype(float).to_numpy()
    y = work[response].astype(float).to_numpy()
    if len(np.unique(x)) <= degree:
        raise ValueError(
            "Níveis de dose insuficientes para o grau do polinômio "
            f"(precisa de mais de {degree} doses distintas)."
        )

    design = np.column_stack([x ** d for d in range(1, degree + 1)])
    design = sm.add_constant(design)
    model = sm.OLS(y, design).fit()
    coef = [float(c) for c in model.params]

    terms = [f"{coef[0]:.4g}"]
    for d in range(1, degree + 1):
        terms.append(f"{coef[d]:+.4g}·x" + (f"^{d}" if d > 1 else ""))
    equation = "y = " + " ".join(terms)

    x_grid = np.linspace(float(x.min()), float(x.max()), 100)
    grid_design = sm.add_constant(
        np.column_stack([x_grid ** d for d in range(1, degree + 1)]), has_constant="add"
    )
    y_grid = grid_design @ np.array(coef)

    return DoseResponse(
        degree=degree,
        coef=coef,
        r2=float(model.rsquared),
        r2_adj=float(model.rsquared_adj),
        f_pvalue=float(model.f_pvalue),
        top_term_pvalue=float(model.pvalues[-1]),
        n=int(len(work)),
        equation=equation,
        x_grid=x_grid,
        y_grid=y_grid,
    )


# ---------------------------------------------------------------------------
# Correlação (Pearson / Spearman) e correlação parcial.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrelationResult:
    """Matrizes de correlação e de valores-p entre variáveis numéricas."""

    method: str
    corr: pd.DataFrame
    pvalues: pd.DataFrame
    n_obs: int


def correlation_analysis(
    df: pd.DataFrame, columns: Sequence[str], method: str = "pearson"
) -> CorrelationResult:
    """Matriz de correlação (Pearson ou Spearman) com valores-p pareados.

    Usa apenas linhas completas (listwise) nas colunas selecionadas.
    """
    from scipy import stats as sps

    cols = list(columns)
    work = df[cols].dropna()
    n = len(cols)
    corr = pd.DataFrame(np.eye(n), index=cols, columns=cols)
    pvals = pd.DataFrame(np.zeros((n, n)), index=cols, columns=cols)

    fn = sps.spearmanr if method == "spearman" else sps.pearsonr
    for i in range(n):
        for j in range(i + 1, n):
            xi = work[cols[i]].to_numpy()
            xj = work[cols[j]].to_numpy()
            if len(xi) < 3:
                r, p = float("nan"), float("nan")
            else:
                r, p = fn(xi, xj)
            corr.iloc[i, j] = corr.iloc[j, i] = float(r)
            pvals.iloc[i, j] = pvals.iloc[j, i] = float(p)
    return CorrelationResult(method=method, corr=corr, pvalues=pvals, n_obs=int(len(work)))


def partial_correlation(
    df: pd.DataFrame, x: str, y: str, covars: Sequence[str], method: str = "pearson"
) -> tuple[float, float]:
    """Correlação parcial entre ``x`` e ``y`` controlando por ``covars``.

    Calcula a correlação entre os resíduos de ``x`` e de ``y`` após regressão
    linear sobre as covariáveis. Devolve ``(r, p)``.
    """
    from scipy import stats as sps

    cols = [x, y] + list(covars)
    work = df[cols].dropna()
    if len(work) < len(covars) + 3:
        return float("nan"), float("nan")

    c = work[list(covars)].to_numpy(dtype=float)
    c = np.column_stack([np.ones(len(c)), c])

    def _resid(v: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(c, v, rcond=None)
        return v - c @ beta

    rx = _resid(work[x].to_numpy(dtype=float))
    ry = _resid(work[y].to_numpy(dtype=float))
    fn = sps.spearmanr if method == "spearman" else sps.pearsonr
    r, p = fn(rx, ry)
    return float(r), float(p)


__all__ = [
    "ConfoundingPair",
    "ExperimentalAnova",
    "AssumptionResult",
    "CompositeAnova",
    "CorrelationResult",
    "DoseResponse",
    "SplitPlotAnova",
    "MEAN_COMPARISON_METHODS",
    "audit_pair_confounding",
    "clean_factor_levels",
    "compare_means",
    "correlation_analysis",
    "cramers_v",
    "detect_confounded_pairs",
    "duncan_groups",
    "dunnett_test",
    "fit_dose_response",
    "fit_experimental_anova",
    "fit_nested",
    "fit_split_plot",
    "fit_strip_plot",
    "group_means",
    "partial_correlation",
    "homoscedasticity_test",
    "lsd_groups",
    "normality_test",
    "scheffe_groups",
    "scott_knott_groups",
    "tukey_groups",
]
