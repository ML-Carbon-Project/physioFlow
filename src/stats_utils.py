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
) -> ExperimentalAnova:
    """Ajusta a ANOVA apropriada ao delineamento e devolve o quadro completo.

    O delineamento é inferido das colunas informadas:

    - apenas ``treatment``                         → DIC  (``y ~ trat``)
    - ``treatment`` + ``block``                    → DBC  (``y ~ trat + bloco``)
    - ``treatment`` + ``factor2``                  → Fatorial (``y ~ trat * fator2``)
    - ``treatment`` + ``factor2`` + ``block``      → Fatorial+Bloco

    As colunas categóricas são convertidas para texto e renomeadas para
    identificadores seguros antes do ajuste, evitando que nomes com espaços ou
    caracteres especiais (ex.: ``"TS_2 initial_value"``) quebrem a fórmula patsy.

    Raises:
        ValueError: se faltarem dados suficientes (sem variação de tratamento,
            graus de liberdade de resíduo não positivos, ou média geral nula).
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols

    cols = [response, treatment]
    if factor2:
        cols.append(factor2)
    if block:
        cols.append(block)
    work = df[cols].dropna().copy()

    rename = {response: "y", treatment: "trat"}
    if factor2:
        rename[factor2] = "fator2"
    if block:
        rename[block] = "bloco"
    work = work.rename(columns=rename)

    for cat in ("trat", "fator2", "bloco"):
        if cat in work.columns:
            work[cat] = work[cat].astype(str)

    if work["trat"].nunique() < 2:
        raise ValueError("O fator de tratamento precisa de pelo menos 2 níveis.")

    if factor2 and block:
        formula = "y ~ C(trat) * C(fator2) + C(bloco)"
        design = "Fatorial+Bloco"
    elif factor2:
        formula = "y ~ C(trat) * C(fator2)"
        design = "Fatorial"
    elif block:
        formula = "y ~ C(trat) + C(bloco)"
        design = "DBC"
    else:
        formula = "y ~ C(trat)"
        design = "DIC"

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

    names = {"trat": treatment, "fator2": factor2 or "", "bloco": block or ""}
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

    factor_terms = [treatment] + ([factor2] if factor2 else [])

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
) -> pd.DataFrame:
    """Tabela de médias com letras de significância pelo método escolhido.

    ``method`` ∈ {``"tukey"``, ``"scott-knott"``, ``"duncan"``, ``"lsd"``,
    ``"scheffe"``}. Devolve a tabela de ``group_means`` acrescida da coluna
    ``group_letter``.
    """
    table = group_means(df, response, factor)
    if table.empty:
        return table
    means = dict(zip(table["group"], table["mean"]))
    ns = dict(zip(table["group"], table["n"]))
    fn = MEAN_COMPARISON_METHODS.get(method, tukey_groups)
    letters = fn(means, ns, ms_error, df_error, alpha)
    table["group_letter"] = table["group"].map(letters)
    return table


__all__ = [
    "ConfoundingPair",
    "ExperimentalAnova",
    "AssumptionResult",
    "MEAN_COMPARISON_METHODS",
    "audit_pair_confounding",
    "compare_means",
    "cramers_v",
    "detect_confounded_pairs",
    "duncan_groups",
    "fit_experimental_anova",
    "group_means",
    "homoscedasticity_test",
    "lsd_groups",
    "normality_test",
    "scheffe_groups",
    "scott_knott_groups",
    "tukey_groups",
]
