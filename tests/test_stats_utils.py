"""Testes do detector de confundimento entre categóricas e do motor de
estatística experimental (ANOVA, pressupostos, Tukey e Scott-Knott)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.stats_utils import (
    MEAN_COMPARISON_METHODS,
    audit_pair_confounding,
    compare_means,
    correlation_analysis,
    cramers_v,
    detect_confounded_pairs,
    duncan_groups,
    fit_dose_response,
    fit_experimental_anova,
    group_means,
    homoscedasticity_test,
    lsd_groups,
    normality_test,
    partial_correlation,
    scheffe_groups,
    scott_knott_groups,
    tukey_groups,
)


def _crd_dataset() -> pd.DataFrame:
    """DIC: 3 tratamentos bem separados, 5 repetições, ruído pequeno."""
    rng = np.random.default_rng(123)
    rows = []
    for trat, base in (("A", 10.0), ("B", 20.0), ("C", 30.0)):
        for _ in range(5):
            rows.append({"trat": trat, "y": base + rng.normal(0, 0.5)})
    return pd.DataFrame(rows)


def _rcbd_dataset() -> pd.DataFrame:
    """DBC: 3 tratamentos × 4 blocos, com efeito de bloco aditivo."""
    rng = np.random.default_rng(7)
    block_effect = {"I": 0.0, "II": 2.0, "III": 4.0, "IV": -1.0}
    rows = []
    for trat, base in (("T1", 10.0), ("T2", 14.0), ("T3", 18.0)):
        for blk, beff in block_effect.items():
            rows.append({"trat": trat, "bloco": blk, "y": base + beff + rng.normal(0, 0.3)})
    return pd.DataFrame(rows)


class TestFitExperimentalAnova:
    def test_dic_detects_significant_treatment(self):
        result = fit_experimental_anova(_crd_dataset(), response="y", treatment="trat")
        assert result.design == "DIC"
        assert result.formula == "y ~ C(trat)"
        assert result.df_error == 12  # 15 obs - 3 níveis
        assert result.cv_percent < 10
        # tratamento fortemente significativo
        assert result.table.loc["trat", "p_value"] < 0.001

    def test_dbc_adds_block_term(self):
        result = fit_experimental_anova(
            _rcbd_dataset(), response="y", treatment="trat", block="bloco"
        )
        assert result.design == "DBC"
        assert "bloco" in result.table.index
        assert result.table.loc["trat", "p_value"] < 0.01

    def test_latin_square_design(self):
        # Quadrado latino 3x3: 3 tratamentos, 3 linhas, 3 colunas.
        rng = np.random.default_rng(3)
        layout = {
            ("L1", "C1"): "T1", ("L1", "C2"): "T2", ("L1", "C3"): "T3",
            ("L2", "C1"): "T2", ("L2", "C2"): "T3", ("L2", "C3"): "T1",
            ("L3", "C1"): "T3", ("L3", "C2"): "T1", ("L3", "C3"): "T2",
        }
        base = {"T1": 10.0, "T2": 15.0, "T3": 20.0}
        rows = []
        for (linha, coluna), trat in layout.items():
            rows.append({"trat": trat, "linha": linha, "coluna": coluna,
                         "y": base[trat] + rng.normal(0, 0.5)})
        df = pd.DataFrame(rows)
        result = fit_experimental_anova(
            df, response="y", treatment="trat", row="linha", column="coluna"
        )
        assert result.design == "Quadrado Latino"
        assert "linha" in result.table.index and "coluna" in result.table.index
        assert result.factor_terms == ["trat"]

    def test_factorial_includes_interaction(self):
        rng = np.random.default_rng(1)
        rows = []
        for a in ("a1", "a2"):
            for b in ("b1", "b2"):
                base = 10 + (5 if a == "a2" else 0) + (3 if b == "b2" else 0)
                for _ in range(4):
                    rows.append({"A": a, "B": b, "y": base + rng.normal(0, 0.5)})
        df = pd.DataFrame(rows)
        result = fit_experimental_anova(df, response="y", treatment="A", factor2="B")
        assert result.design == "Fatorial"
        assert any("×" in idx for idx in result.table.index)  # termo de interação

    def test_three_way_factorial_has_triple_interaction(self):
        rng = np.random.default_rng(9)
        rows = []
        for a in ("a1", "a2"):
            for b in ("b1", "b2"):
                for c in ("c1", "c2"):
                    base = 10 + (4 if a == "a2" else 0) + (3 if b == "b2" else 0) + (2 if c == "c2" else 0)
                    for _ in range(4):
                        rows.append({"A": a, "B": b, "C": c, "y": base + rng.normal(0, 0.4)})
        df = pd.DataFrame(rows)
        result = fit_experimental_anova(df, response="y", treatment="A", factor2="B", factor3="C")
        assert result.design == "Fatorial"
        assert result.factor_terms == ["A", "B", "C"]
        assert any(idx.count("×") == 2 for idx in result.table.index)  # interação tripla

    def test_factor3_without_factor2_raises(self):
        df = pd.DataFrame({"A": ["a", "b"] * 6, "C": ["c", "d"] * 6, "y": range(12)})
        with pytest.raises(ValueError):
            fit_experimental_anova(df, response="y", treatment="A", factor3="C")

    def test_junk_factor_levels_are_dropped(self):
        df = _crd_dataset()
        # injeta linhas com nível-lixo no tratamento; devem ser removidas.
        junk = pd.DataFrame({"trat": [".", "NA", ""], "y": [99.0, 99.0, 99.0]})
        dirty = pd.concat([df, junk], ignore_index=True)
        result = fit_experimental_anova(dirty, response="y", treatment="trat")
        assert result.n_obs == len(df)            # 3 linhas-lixo descartadas
        assert result.table.loc["trat", "p_value"] < 0.001

    def test_raises_without_treatment_variation(self):
        df = pd.DataFrame({"trat": ["A"] * 6, "y": [1.0, 2, 3, 4, 5, 6]})
        with pytest.raises(ValueError):
            fit_experimental_anova(df, response="y", treatment="trat")

    def test_handles_column_names_with_spaces(self):
        df = _crd_dataset().rename(columns={"y": "TS_2 initial_value", "trat": "Cultura"})
        result = fit_experimental_anova(
            df, response="TS_2 initial_value", treatment="Cultura"
        )
        assert result.design == "DIC"


class TestAssumptions:
    def test_normality_passes_on_normal_residuals(self):
        rng = np.random.default_rng(0)
        res = normality_test(rng.normal(0, 1, size=200))
        assert res.name == "Shapiro-Wilk"
        assert res.passed

    def test_normality_flags_skewed(self):
        rng = np.random.default_rng(0)
        res = normality_test(rng.exponential(1.0, size=200))
        assert not res.passed

    def test_homoscedasticity_passes_equal_variance(self):
        res = homoscedasticity_test(_crd_dataset(), "y", "trat")
        assert res.name == "Levene"
        assert res.passed


class TestMeanComparison:
    def test_tukey_separates_well_spread_means(self):
        result = fit_experimental_anova(_crd_dataset(), response="y", treatment="trat")
        df = _crd_dataset()
        table = compare_means(
            df, "y", "trat", result.ms_error, result.df_error, method="tukey"
        )
        letters = dict(zip(table["group"], table["group_letter"]))
        # Três médias muito separadas → três letras distintas, sem compartilhar.
        assert letters["A"] != letters["B"] != letters["C"]
        assert set(letters["A"]).isdisjoint(letters["C"])

    def test_scott_knott_groups_identical_means_together(self):
        # Dois tratamentos quase idênticos e um bem distante.
        means = {"A": 10.0, "B": 10.05, "C": 30.0}
        ns = {"A": 5, "B": 5, "C": 5}
        letters = scott_knott_groups(means, ns, ms_error=0.5, df_error=12)
        assert letters["A"] == letters["B"]      # agrupados
        assert letters["A"] != letters["C"]      # separados

    def test_tukey_shares_letter_for_close_means(self):
        means = {"A": 10.0, "B": 10.1, "C": 25.0}
        ns = {"A": 5, "B": 5, "C": 5}
        letters = tukey_groups(means, ns, ms_error=1.0, df_error=12)
        # A e B próximos → compartilham letra; C isolado.
        assert set(letters["A"]) & set(letters["B"])
        assert not (set(letters["A"]) & set(letters["C"]))

    def test_group_means_sorted_descending(self):
        table = group_means(_crd_dataset(), "y", "trat")
        assert list(table["mean"]) == sorted(table["mean"], reverse=True)


class TestAdditionalComparisonMethods:
    # Médias bem separadas → todos os métodos dão letras distintas.
    WELL_SPREAD = ({"A": 10.0, "B": 20.0, "C": 30.0}, {"A": 5, "B": 5, "C": 5})
    # A e B colados, C distante.
    TWO_CLOSE = ({"A": 10.0, "B": 10.1, "C": 25.0}, {"A": 5, "B": 5, "C": 5})

    @pytest.mark.parametrize("fn", [lsd_groups, scheffe_groups, duncan_groups])
    def test_well_spread_gives_distinct_letters(self, fn):
        means, ns = self.WELL_SPREAD
        letters = fn(means, ns, ms_error=0.5, df_error=12)
        assert len({letters["A"], letters["B"], letters["C"]}) == 3
        assert not (set(letters["A"]) & set(letters["C"]))

    @pytest.mark.parametrize("fn", [lsd_groups, scheffe_groups, duncan_groups])
    def test_close_means_share_letter(self, fn):
        means, ns = self.TWO_CLOSE
        letters = fn(means, ns, ms_error=1.0, df_error=12)
        assert set(letters["A"]) & set(letters["B"])
        assert not (set(letters["A"]) & set(letters["C"]))

    def test_scheffe_more_conservative_than_lsd(self):
        # k=3 com o par extremo (A-C, diff=3.5) entre os limiares LSD e Scheffé:
        # LSD (liberal) separa A de C; Scheffé (conservador) agrupa tudo.
        # Para k=2 ambos coincidem (sqrt(F(1,gl)) = t(gl)), por isso usa-se k=3.
        means = {"A": 10.0, "B": 11.75, "C": 13.5}
        ns = {"A": 4, "B": 4, "C": 4}
        lsd = lsd_groups(means, ns, ms_error=4.0, df_error=9)
        scheffe = scheffe_groups(means, ns, ms_error=4.0, df_error=9)
        assert not (set(lsd["A"]) & set(lsd["C"]))          # LSD separa os extremos
        assert set(scheffe["A"]) & set(scheffe["C"])        # Scheffé agrupa

    def test_compare_means_dispatches_all_methods(self):
        df = _crd_dataset()
        result = fit_experimental_anova(df, response="y", treatment="trat")
        for method in MEAN_COMPARISON_METHODS:
            table = compare_means(df, "y", "trat", result.ms_error, result.df_error, method=method)
            assert "group_letter" in table.columns
            assert table["group_letter"].notna().all()


class TestDoseResponse:
    def _dose_df(self, b0=5.0, b1=2.0, b2=-0.1, noise=0.3):
        rng = np.random.default_rng(11)
        rows = []
        for dose in (0, 5, 10, 15, 20):
            for _ in range(4):
                y = b0 + b1 * dose + b2 * dose ** 2 + rng.normal(0, noise)
                rows.append({"dose": dose, "y": y})
        return pd.DataFrame(rows)

    def test_quadratic_fit_recovers_high_r2(self):
        res = fit_dose_response(self._dose_df(), "dose", "y", degree=2)
        assert res.degree == 2
        assert res.r2 > 0.95
        assert len(res.coef) == 3                 # b0, b1, b2
        assert res.top_term_pvalue < 0.05         # termo quadrático significativo
        assert res.x_grid.shape == res.y_grid.shape

    def test_linear_fit_has_two_coefficients(self):
        res = fit_dose_response(self._dose_df(b2=0.0), "dose", "y", degree=1)
        assert len(res.coef) == 2
        assert res.equation.startswith("y = ")

    def test_raises_when_too_few_dose_levels(self):
        df = pd.DataFrame({"dose": [0, 0, 10, 10], "y": [1.0, 2, 3, 4]})
        with pytest.raises(ValueError):
            fit_dose_response(df, "dose", "y", degree=2)  # 2 doses, grau 2


class TestCorrelation:
    def test_pearson_matrix_is_symmetric_with_unit_diagonal(self):
        rng = np.random.default_rng(0)
        x = rng.normal(0, 1, 100)
        df = pd.DataFrame({"x": x, "y": 2 * x + rng.normal(0, 0.1, 100), "z": rng.normal(0, 1, 100)})
        res = correlation_analysis(df, ["x", "y", "z"], method="pearson")
        assert np.allclose(np.diag(res.corr.to_numpy()), 1.0)
        assert res.corr.loc["x", "y"] == pytest.approx(res.corr.loc["y", "x"])
        assert res.corr.loc["x", "y"] > 0.98           # forte correlação
        assert res.pvalues.loc["x", "y"] < 0.001

    def test_spearman_method(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 4, 9, 16, 25]})  # monotônica
        res = correlation_analysis(df, ["a", "b"], method="spearman")
        assert res.corr.loc["a", "b"] == pytest.approx(1.0)

    def test_partial_correlation_removes_confounder(self):
        # z dirige x e y; controlando por z, a correlação parcial cai a ~0.
        rng = np.random.default_rng(5)
        z = rng.normal(0, 1, 300)
        df = pd.DataFrame({
            "z": z,
            "x": z + rng.normal(0, 0.3, 300),
            "y": z + rng.normal(0, 0.3, 300),
        })
        r_raw = correlation_analysis(df, ["x", "y"]).corr.loc["x", "y"]
        r_partial, p_partial = partial_correlation(df, "x", "y", ["z"])
        assert r_raw > 0.7                # correlação bruta alta
        assert abs(r_partial) < 0.25      # some ao controlar por z


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
