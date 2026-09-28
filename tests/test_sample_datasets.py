"""Validação interna do motor de estatística experimental contra datasets reais.

Os arquivos de teste, públicos e pequenos, ficam em ``data/sample/test/`` e são
versionados como fixtures. Cobrem os tipos de delineamento/análise da ferramenta
contra resultados publicados (ver ``docs/validacao_externa.md``).

Natureza da validação:
- **Penguins** e **Oats (Yates)** são âncoras fortes: reproduzem números
  publicados (F da ANOVA, agrupamento de Tukey, quadro de split-plot).
- **australia.soybean** e **penguins** trazem correlações cruzadas de forma
  **independente** contra ``scipy`` (não são só baseline do próprio código).
- Demais asserções são baselines de regressão: travam o comportamento atual.

Cada teste é pulado (``skip``) se o arquivo não estiver presente.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from scipy import stats as sps

from src.stats_utils import (
    compare_means,
    correlation_analysis,
    fit_experimental_anova,
    fit_split_plot,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample" / "test"

# Separador por arquivo (BESAG é separado por espaços; os demais por tab/vírgula).
_SEP = {
    "BESAG_ELBATAN.txt": r"\s+",
    "penguins.csv": ",",
    "yates.oats.txt": "\t",
    "australia.soybean.txt": "\t",
    "SPRING_BARLEY.txt": "\t",
    "sk_crd1.csv": ",",
    "sk_rcbd.csv": ",",
    "sk_sorghum.csv": ",",
    "sweetpotato.csv": ",",
    "plantgrowth.csv": ",",
}


def _partition(groups: dict[str, str]) -> frozenset:
    """Conjunto de conjuntos de níveis que compartilham a mesma letra."""
    buckets: dict[str, set] = {}
    for level, letter in groups.items():
        buckets.setdefault(letter, set()).add(level)
    return frozenset(frozenset(v) for v in buckets.values())


def _load(name: str) -> pd.DataFrame:
    path = SAMPLE_DIR / name
    if not path.exists():
        pytest.skip(f"fixture ausente: {path}")
    return pd.read_csv(path, sep=_SEP[name], engine="python")


class TestBesagElbatan:
    """Ensaio de campo 50 genótipos × 3 colunas → DBC com bloco codificado em número.

    Confirma que o motor aceita um bloco numérico (``col`` = 1,2,3): ele é
    coagido a texto internamente — o que a melhoria de UI passou a permitir
    selecionar.
    """

    def test_rcbd_with_numeric_block(self):
        df = _load("BESAG_ELBATAN.txt")
        assert pd.api.types.is_numeric_dtype(df["col"])      # bloco vem como inteiro
        res = fit_experimental_anova(df, response="yield", treatment="gen", block="col")
        assert res.design == "DBC"
        assert res.df_error == 98                            # 149 - 49(gen) - 2(col)
        assert res.table.loc["gen", "p_value"] == pytest.approx(0.0066, abs=0.003)


class TestPenguins:
    """Palmer Penguins (clássico) — comparação com resultados publicados.

    Referências (ver docs/validacao_externa.md):
    - flipper ~ species → F(2,339) = 594,80 (publicado);
    - correlação flipper × body_mass ≈ 0,87;
    - Gentoo mais pesado e isolado; Adelie ≈ Chinstrap (mesma letra).
    """

    def test_flipper_anova_matches_published_F(self):
        df = _load("penguins.csv")
        res = fit_experimental_anova(df, response="flipper_length_mm", treatment="species")
        assert res.table.loc["species", "df"] == 2
        assert res.df_error == 339
        assert res.table.loc["species", "F"] == pytest.approx(594.80, abs=0.5)

    def test_body_mass_anova_and_tukey_letters(self):
        df = _load("penguins.csv")
        res = fit_experimental_anova(df, response="body_mass_g", treatment="species")
        assert res.design == "DIC"
        assert res.n_obs == 342                       # 344 - 2 com body_mass ausente
        assert res.table.loc["species", "p_value"] < 1e-50
        assert 8.0 < res.cv_percent < 14.0

        means = compare_means(df, "body_mass_g", "species", res.ms_error, res.df_error, "tukey")
        letters = dict(zip(means["group"], means["group_letter"]))
        # Gentoo isolado; Adelie e Chinstrap compartilham letra (massas ~iguais).
        assert not (set(letters["Gentoo"]) & set(letters["Adelie"]))
        assert set(letters["Adelie"]) & set(letters["Chinstrap"])

    def test_flipper_bodymass_correlation_matches_literature(self):
        df = _load("penguins.csv")
        res = correlation_analysis(df, ["flipper_length_mm", "body_mass_g"], "pearson")
        r = res.corr.loc["flipper_length_mm", "body_mass_g"]
        r_ref, _ = sps.pearsonr(df["flipper_length_mm"].dropna(),
                                df.loc[df["flipper_length_mm"].notna(), "body_mass_g"])
        assert r == pytest.approx(0.871, abs=0.01)    # ~0,87 publicado

    def test_factorial_species_by_sex_matches_r_type2(self):
        # sex tem "." e vazios; clean_factor_levels descarta-os → fatorial 3×2.
        # F de referência: car::Anova(type=2) no R (mesmo tipo de SQ que usamos).
        df = _load("penguins.csv")
        res = fit_experimental_anova(df, response="body_mass_g", treatment="species", factor2="sex")
        assert res.design == "Fatorial"
        assert res.n_obs == 333                       # 168 MALE + 165 FEMALE
        assert res.table.loc["species", "F"] == pytest.approx(749.016, abs=0.5)
        assert res.table.loc["sex", "F"] == pytest.approx(387.460, abs=0.5)
        inter = next(i for i in res.table.index if "×" in i)
        assert res.table.loc[inter, "F"] == pytest.approx(8.757, abs=0.05)

    def test_ancova_flipper_covariate_matches_r(self):
        # ANCOVA body_mass ~ flipper(cov) + species. Referência: car::Anova(type=2)
        # + emmeans (médias ajustadas) no R.
        df = _load("penguins.csv")
        res = fit_experimental_anova(
            df, response="body_mass_g", treatment="species", covariate="flipper_length_mm"
        )
        assert res.covariate == "flipper_length_mm"
        assert res.covariate_slope == pytest.approx(40.7054, abs=0.01)
        assert res.table.loc["flipper_length_mm", "F"] == pytest.approx(175.687, abs=0.5)
        assert res.table.loc["species", "F"] == pytest.approx(18.393, abs=0.05)
        # médias ajustadas batem com emmeans
        assert res.adjusted_means["Adelie"] == pytest.approx(4147, abs=2)
        assert res.adjusted_means["Chinstrap"] == pytest.approx(3940, abs=2)
        assert res.adjusted_means["Gentoo"] == pytest.approx(4414, abs=2)


class TestYatesOatsSplitPlot:
    """Yates (1935) oats — exemplo canônico de parcelas subdivididas.

    Quadro publicado (nlme::Oats, livros de modelos mistos):
    gen F(2,10)=1,485; nitro F(3,45)=37,69; gen×nitro F(6,45)=0,303.
    """

    def test_reproduces_published_anova(self):
        df = _load("yates.oats.txt")
        res = fit_split_plot(df, response="yield", whole_plot="gen", subplot="nitro", block="block")
        tbl = res.table
        assert tbl.loc["Erro(a)", "df"] == 10
        assert tbl.loc["Erro(b)", "df"] == 45
        assert tbl.loc["gen", "F"] == pytest.approx(1.485, abs=0.01)
        assert tbl.loc["nitro", "F"] == pytest.approx(37.69, abs=0.05)
        assert tbl.loc["gen × nitro", "F"] == pytest.approx(0.303, abs=0.01)
        assert tbl.loc["gen", "p_value"] > 0.05
        assert tbl.loc["nitro", "p_value"] < 0.001


class TestAustraliaSoybean:
    """Ensaio multiambiente de soja (8 ambientes, 58 genótipos, 6 variáveis).

    Restaura a validação de correlação com um caso agronômico clássico: o
    *trade-off* proteína × óleo na soja (correlação negativa forte).
    """

    def test_protein_oil_tradeoff_correlation(self):
        df = _load("australia.soybean.txt")
        res = correlation_analysis(df, ["protein", "oil"], "pearson")
        r = res.corr.loc["protein", "oil"]
        r_ref, p_ref = sps.pearsonr(df["protein"], df["oil"])
        assert r == pytest.approx(r_ref, abs=1e-9)    # cruzamento independente
        assert r == pytest.approx(-0.758, abs=0.02)   # trade-off proteína-óleo
        assert p_ref < 1e-6

    def test_factorial_location_by_year(self):
        df = _load("australia.soybean.txt")
        res = fit_experimental_anova(df, response="yield", treatment="loc", factor2="year")
        assert res.design == "Fatorial"
        assert any("×" in idx for idx in res.table.index)   # termo de interação


class TestScottKnottVsR:
    """Scott-Knott validado contra o pacote oficial ``ScottKnott`` do R.

    Os agrupamentos esperados foram gerados rodando ``ScottKnott::SK`` (CRAN) nos
    datasets que acompanham o pacote (GPL). Nossa implementação deve reproduzir
    o MESMO particionamento, treatment a treatment, sem ambiguidade.
    """

    def _our_partition(self, df, treatment, block):
        res = fit_experimental_anova(df, "y", treatment, block=block)
        table = compare_means(df, "y", treatment, res.ms_error, res.df_error, method="scott-knott")
        return _partition(dict(zip(table["group"], table["group_letter"])))

    def test_crd1_matches_official(self):
        df = _load("sk_crd1.csv")
        expected = frozenset({frozenset({"tr-1", "tr-2", "tr-3"}), frozenset({"tr-4"})})
        assert self._our_partition(df, "x", None) == expected

    def test_rcbd_matches_official(self):
        df = _load("sk_rcbd.csv")
        expected = frozenset({frozenset({"A", "B", "C", "D"}), frozenset({"E"})})
        assert self._our_partition(df, "tra", "blk") == expected

    def test_sorghum_16_treatments_matches_official(self):
        # Exemplo do artigo Jelihovschi et al. (2014): rendimento de sorgo.
        df = _load("sk_sorghum.csv")
        expected = frozenset({
            frozenset({"1", "2", "3", "4", "5", "7", "8", "9", "14"}),
            frozenset({"6", "10", "11", "12", "13", "15", "16"}),
        })
        assert self._our_partition(df, "x", "r") == expected


class TestPostHocVsR:
    """Tukey, LSD, Duncan, Scheffé e Dunnett contra referências do R.

    As referências vêm de ``TukeyHSD`` (R base), ``agricolae`` (LSD, Duncan,
    Scheffé) e ``multcomp::glht`` (Dunnett), congeladas em
    ``data/sample/test/posthoc_reference_R.json`` por
    ``scripts/gerar_referencia_posthoc_R.R`` — a suíte não precisa do R.

    Comparamos a **decisão por par** (difere / não difere a 5 %), que é o que o
    usuário lê nas letras. Datasets: sweetpotato (agricolae), PlantGrowth (R
    base), penguins (n desigual) e sorgo em DBC com 16 tratamentos.
    """

    # dataset -> (arquivo, resposta, tratamento, bloco)
    SETS = {
        "sweetpotato": ("sweetpotato.csv", "yield", "virus", None),
        "plantgrowth": ("plantgrowth.csv", "weight", "group", None),
        "penguins": ("penguins.csv", "body_mass_g", "species", None),
        "sorghum": ("sk_sorghum.csv", "y", "x", "r"),
    }

    @pytest.fixture(scope="class")
    def ref(self):
        path = SAMPLE_DIR / "posthoc_reference_R.json"
        if not path.exists():
            pytest.skip(f"referência ausente: {path}")
        return json.loads(path.read_text())

    def _frame(self, name):
        fname, resp, trt, blk = self.SETS[name]
        df = _load(fname)
        if name == "penguins":
            df = df[df["body_mass_g"].notna() & (df["species"] != "")]
        if name == "sorghum":
            df = df.astype({"x": str, "r": str})
        return df, resp, trt, blk

    @pytest.mark.parametrize("dataset", sorted(SETS))
    @pytest.mark.parametrize("method", ["tukey", "lsd", "duncan", "scheffe"])
    def test_pairwise_decisions_match_r(self, ref, dataset, method):
        df, resp, trt, blk = self._frame(dataset)
        res = fit_experimental_anova(df, resp, trt, block=blk)
        table = compare_means(df, resp, trt, res.ms_error, res.df_error, method=method)
        letters = dict(zip(table["group"].astype(str), table["group_letter"]))
        for g1, g2, differs_in_r in ref[dataset][method]:
            differs_here = not (set(letters[g1]) & set(letters[g2]))
            assert differs_here == differs_in_r, (
                f"{dataset}/{method}: par ({g1}, {g2}) difere={differs_here}, R={differs_in_r}"
            )

    @pytest.mark.parametrize("dataset,control", [
        ("plantgrowth", "ctrl"), ("sweetpotato", "cc"), ("penguins", "Adelie"),
    ])
    def test_dunnett_pvalues_match_multcomp(self, ref, dataset, control):
        from src.stats_utils import dunnett_test

        df, resp, trt, _ = self._frame(dataset)
        out = dunnett_test(df, resp, trt, control=control)
        got = dict(zip(out["group"].astype(str), out["p_value"]))
        for group, p_r in ref["_dunnett"][dataset].items():
            # a cdf da t multivariada é estimada numericamente; 1e-3 cobre a
            # diferença de algoritmo sem mascarar erro de especificação.
            assert got[group] == pytest.approx(p_r, abs=1e-3)

    def test_dunnett_with_block_matches_multcomp(self, ref):
        """Dunnett num DBC precisa do QMR do delineamento, não do erro one-way.

        Regressão do defeito corrigido em 27/09/2026: ``dunnett_test`` estimava
        a variância só entre as repetições do tratamento, jogando a variação de
        bloco para dentro do erro. No ``sk_rcbd`` isso muda a decisão do
        tratamento E a 5 % (p = 0,038 em vez de 0,054).
        """
        from src.stats_utils import dunnett_test

        spec = ref["_dunnett_rcbd"]
        df = pd.read_csv(SAMPLE_DIR / spec["dataset"])
        df[spec["block"]] = df[spec["block"]].astype(str)
        res = fit_experimental_anova(df, spec["response"], spec["factor"], block=spec["block"])

        assert res.ms_error == pytest.approx(spec["ms_error"], rel=1e-6)
        assert int(res.df_error) == spec["df_error"]

        out = dunnett_test(
            df, spec["response"], spec["factor"], control=spec["control"],
            ms_error=res.ms_error, df_error=res.df_error,
        )
        got = dict(zip(out["group"].astype(str), out["p_value"]))
        for group, p_r in spec["p"].items():
            assert got[group] == pytest.approx(p_r, abs=1e-3)

    def test_dunnett_without_error_terms_falls_back_to_one_way(self):
        """Sem ms_error/df_error, reproduz o ``scipy.stats.dunnett`` (caso DIC)."""
        from scipy.stats import dunnett as scipy_dunnett

        from src.stats_utils import dunnett_test

        df = pd.read_csv(SAMPLE_DIR / "plantgrowth.csv")
        levels = sorted(df["group"].astype(str).unique())
        others = [lv for lv in levels if lv != "ctrl"]
        samples = [df.loc[df["group"].astype(str) == lv, "weight"].to_numpy() for lv in others]
        control = df.loc[df["group"].astype(str) == "ctrl", "weight"].to_numpy()
        expected = scipy_dunnett(*samples, control=control,
                                 alternative="two-sided", random_state=0)

        got = dict(zip(*(lambda o: (o["group"].astype(str), o["p_value"]))(
            dunnett_test(df, "weight", "group", control="ctrl"))))
        for lv, p_scipy in zip(others, expected.pvalue, strict=True):
            assert got[lv] == pytest.approx(p_scipy, abs=1e-3)
