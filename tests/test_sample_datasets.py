"""Validação interna do motor de estatística experimental contra datasets reais.

Os arquivos vêm do *ASReml Cookbook* (https://cookbook.asreml.vsni.co.uk/
datasets.html) e ficam em ``data/sample/``. São de domínio público e pequenos,
versionados como fixtures.

IMPORTANTE — natureza desta validação:
- Os resultados "oficiais" do cookbook usam **modelos mistos/espaciais (REML)**.
  Estes testes exercitam a **ANOVA clássica** da ferramenta, então os números
  NÃO batem com os do site — a comparação justa é contra a mesma ANOVA clássica
  em R/Rbio.
- Para SALMON, a correlação é cruzada de forma **independente** contra
  ``scipy.stats.pearsonr`` (não é só baseline do próprio código).
- Os demais valores são *baselines de regressão*: travam o comportamento atual
  para detectar mudanças acidentais. Se a estatística mudar de propósito,
  atualize o valor esperado conscientemente.

Cada teste é pulado (``skip``) se o arquivo correspondente não estiver presente,
para não quebrar ambientes sem as fixtures.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from scipy import stats as sps

from src.stats_utils import (
    compare_means,
    correlation_analysis,
    fit_dose_response,
    fit_experimental_anova,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"

# Separador por arquivo (BESAG é separado por espaços; os demais por tab/vírgula).
_SEP = {
    "BESAG_ELBATAN.txt": r"\s+",
    "DURBAN_ROWCOL.txt": "\t",
    "RATPUP.txt": "\t",
    "SALMON.txt": "\t",
    "PRESSURE.txt": "\t",
    "penguins.csv": ",",
}


def _load(name: str) -> pd.DataFrame:
    path = SAMPLE_DIR / name
    if not path.exists():
        pytest.skip(f"fixture ausente: {path}")
    return pd.read_csv(path, sep=_SEP[name], engine="python")


class TestRatpup:
    """Pesos de filhotes de rato: 3 tratamentos × sexo → bom caso de DIC/Fatorial."""

    def test_one_way_treatment_is_significant(self):
        df = _load("RATPUP.txt")
        res = fit_experimental_anova(df, response="weight", treatment="treatment")
        assert res.design == "DIC"
        assert res.table.loc["treatment", "p_value"] < 0.05

    def test_factorial_treatment_by_sex(self):
        df = _load("RATPUP.txt")
        res = fit_experimental_anova(df, response="weight", treatment="treatment", factor2="sex")
        assert res.design == "Fatorial"
        assert any("×" in idx for idx in res.table.index)   # termo de interação presente
        assert res.table.loc["treatment", "p_value"] < 0.05
        assert 5.0 < res.cv_percent < 15.0

    def test_ancova_with_litter_size_covariate(self):
        # lsize (tamanho da ninhada) é a covariável clássica deste dataset:
        # ninhadas maiores → filhotes mais leves. Ajusta os pesos por tratamento.
        df = _load("RATPUP.txt")
        res = fit_experimental_anova(
            df, response="weight", treatment="treatment", covariate="lsize"
        )
        assert res.covariate == "lsize"
        assert res.covariate_pvalue < 0.001        # tamanho da ninhada importa muito
        assert res.covariate_slope < 0             # ninhada maior → peso menor
        assert res.adjusted_means is not None                  # CV experimental plausível


class TestSalmon:
    """Score de brânquia × carga amebiana: correlação e regressão (sem fator)."""

    def test_pearson_matches_scipy_independently(self):
        df = _load("SALMON.txt")
        res = correlation_analysis(df, ["mean_gill_score", "amoebic_load"], method="pearson")
        r_tool = res.corr.loc["mean_gill_score", "amoebic_load"]
        r_ref, p_ref = sps.pearsonr(df["mean_gill_score"], df["amoebic_load"])
        assert r_tool == pytest.approx(r_ref, abs=1e-9)     # cruzamento independente
        assert r_tool == pytest.approx(-0.817, abs=0.01)    # forte correlação negativa
        assert p_ref < 1e-6

    def test_quadratic_dose_response_runs(self):
        df = _load("SALMON.txt")
        res = fit_dose_response(df, dose="amoebic_load", response="mean_gill_score", degree=2)
        assert res.degree == 2
        assert 0.5 < res.r2 < 0.9


class TestBesagElbatan:
    """Ensaio de campo 50 genótipos × 3 colunas → DBC com bloco codificado em número.

    Confirma que o motor aceita um bloco numérico (``col`` = 1,2,3): ele é
    coagido a texto internamente — exatamente o que a melhoria de UI passou a
    permitir selecionar.
    """

    def test_rcbd_with_numeric_block(self):
        df = _load("BESAG_ELBATAN.txt")
        assert pd.api.types.is_numeric_dtype(df["col"])      # bloco vem como inteiro
        res = fit_experimental_anova(df, response="yield", treatment="gen", block="col")
        assert res.design == "DBC"
        assert res.df_error == 98                            # 149 - 49(gen) - 2(col)
        assert res.table.loc["gen", "p_value"] == pytest.approx(0.0066, abs=0.003)


class TestDurbanRowcol:
    """Ensaio linha-coluna com 272 genótipos: ANOVA roda como DBC (gen+rep)."""

    def test_rcbd_runs_with_many_treatments(self):
        df = _load("DURBAN_ROWCOL.txt")
        res = fit_experimental_anova(df, response="yield", treatment="gen", block="rep")
        assert res.design == "DBC"
        assert df["gen"].nunique() == 272
        assert "rep" in res.table.index


class TestPenguins:
    """Palmer Penguins (clássico) — comparação com resultados publicados.

    Referências cruzadas (ver docs/validacao_externa.md):
    - correlação flipper × body_mass ≈ 0,87 (literatura);
    - Gentoo é a espécie mais pesada e se separa das demais;
    - Adelie e Chinstrap têm massa praticamente igual (mesma letra).
    """

    def test_body_mass_anova_by_species_and_tukey_letters(self):
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
        assert r == pytest.approx(0.871, abs=0.01)    # ~0,87 publicado
        # Simpson: bill_depth × body_mass é negativo no agregado.
        res2 = correlation_analysis(df, ["bill_depth_mm", "body_mass_g"], "pearson")
        assert res2.corr.loc["bill_depth_mm", "body_mass_g"] < 0

    def test_factorial_species_by_sex_cleans_junk_levels(self):
        # sex tem "." e vazios; clean_factor_levels (no fit) deve descartá-los,
        # restando só MALE/FEMALE → fatorial 3×2 válido.
        df = _load("penguins.csv")
        res = fit_experimental_anova(df, response="body_mass_g", treatment="species", factor2="sex")
        assert res.design == "Fatorial"
        sex_term = next(i for i in res.table.index if i not in ("species", "Residual") and "×" not in i)
        assert res.table.loc["species", "p_value"] < 0.05
        assert res.table.loc[sex_term, "p_value"] < 0.05
        # apenas 2 níveis de sexo entraram (333 = 168 MALE + 165 FEMALE)
        assert res.n_obs == 333


class TestPressureThreeWay:
    """Pressão arterial: fatorial 3×2×2 (drug × biofeed × diet), balanceado."""

    def test_three_way_factorial_includes_triple_interaction(self):
        df = _load("PRESSURE.txt")
        res = fit_experimental_anova(
            df, response="pressure", treatment="drug", factor2="biofeed", factor3="diet"
        )
        assert res.design == "Fatorial"
        # termo de interação tripla presente (dois "×" no rótulo)
        assert any(idx.count("×") == 2 for idx in res.table.index)
        assert res.table.loc["drug", "p_value"] < 0.05
        assert res.factor_terms == ["drug", "biofeed", "diet"]

    def test_factor3_requires_factor2(self):
        df = _load("PRESSURE.txt")
        with pytest.raises(ValueError):
            fit_experimental_anova(df, response="pressure", treatment="drug", factor3="diet")
