"""Utilitários estatísticos compartilhados entre as páginas do app.

Estas funções são puramente computacionais e não dependem de Streamlit;
podem ser testadas isoladamente com pytest.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

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


__all__ = [
    "ConfoundingPair",
    "audit_pair_confounding",
    "cramers_v",
    "detect_confounded_pairs",
]
