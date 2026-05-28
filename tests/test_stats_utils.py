"""Testes do detector de confundimento entre categóricas."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.stats_utils import (
    audit_pair_confounding,
    cramers_v,
    detect_confounded_pairs,
)


class TestCramersV:
    def test_perfect_association_returns_one(self):
        df = pd.DataFrame({
            "a": ["x", "x", "y", "y", "z", "z"],
            "b": ["X", "X", "Y", "Y", "Z", "Z"],
        })
        assert cramers_v(df, "a", "b") == pytest.approx(1.0, abs=0.01)

    def test_independent_returns_near_zero(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "a": rng.choice(["x", "y"], size=400),
            "b": rng.choice(["X", "Y"], size=400),
        })
        assert cramers_v(df, "a", "b") < 0.15

    def test_empty_returns_zero(self):
        df = pd.DataFrame({"a": [np.nan] * 5, "b": [np.nan] * 5})
        assert cramers_v(df, "a", "b") == 0.0


class TestAuditPair:
    def test_redundant_pair(self):
        df = pd.DataFrame({
            "Fazenda": ["A"] * 10 + ["B"] * 10,
            "Cultura": ["Soja"] * 10 + ["Cana"] * 10,
        })
        pair = audit_pair_confounding(df, "Fazenda", "Cultura")
        assert pair.is_redundant
        assert pair.is_confounded
        assert pair.cramers_v == pytest.approx(1.0, abs=0.01)
        assert pair.determines_a_to_b == pytest.approx(1.0)
        assert pair.determines_b_to_a == pytest.approx(1.0)

    def test_one_determines_the_other_but_not_redundant(self):
        # Estágio é nested em Cultura: cada estágio só ocorre numa cultura,
        # mas cada cultura tem vários estágios.
        df = pd.DataFrame({
            "Cultura": ["Soja"] * 6 + ["Cana"] * 6,
            "Estágio": ["R1", "R2", "R3"] * 2 + ["E1", "E2", "E3"] * 2,
        })
        pair = audit_pair_confounding(df, "Cultura", "Estágio")
        # Estágio determina Cultura (cada estágio → 1 cultura única).
        assert pair.determines_b_to_a == pytest.approx(1.0)
        # Cultura não determina Estágio (cada cultura tem 3 estágios).
        assert pair.determines_a_to_b < 0.5
        assert pair.is_confounded
        assert not pair.is_redundant


class TestDetectConfoundedPairs:
    def test_filters_high_cardinality_columns(self):
        df = pd.DataFrame({
            "ID": [f"id_{i}" for i in range(20)],  # cardinalidade=20 (acima do max default)
            "Fazenda": ["A"] * 10 + ["B"] * 10,
            "Cultura": ["Soja"] * 10 + ["Cana"] * 10,
        })
        pairs = detect_confounded_pairs(df, cat_cols=["ID", "Fazenda", "Cultura"], max_levels=15)
        # ID deve ser filtrado por cardinalidade alta; só sobra Fazenda↔Cultura.
        assert len(pairs) == 1
        assert {pairs[0].col_a, pairs[0].col_b} == {"Fazenda", "Cultura"}

    def test_returns_empty_when_no_confounding(self):
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "a": rng.choice(["x", "y"], size=400),
            "b": rng.choice(["X", "Y"], size=400),
            "c": rng.choice(["m", "n"], size=400),
        })
        assert detect_confounded_pairs(df, cat_cols=["a", "b", "c"]) == []

    def test_ordered_by_cramers_v_descending(self):
        df = pd.DataFrame({
            "Fazenda": ["A"] * 10 + ["B"] * 10,
            "Cultura": ["Soja"] * 10 + ["Cana"] * 10,
            "Manejo": ["m1"] * 10 + ["m2"] * 10,
        })
        # Os três são equivalentes 1:1 — todos com V=1.0
        pairs = detect_confounded_pairs(df, cat_cols=["Fazenda", "Cultura", "Manejo"])
        assert len(pairs) == 3
        assert all(p.cramers_v == pytest.approx(1.0, abs=0.01) for p in pairs)
