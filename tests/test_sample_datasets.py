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
}


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

    def test_factorial_species_by_sex_cleans_junk_levels(self):
        # sex tem "." e vazios; clean_factor_levels (no fit) deve descartá-los,
        # restando só MALE/FEMALE → fatorial 3×2 válido.
        df = _load("penguins.csv")
        res = fit_experimental_anova(df, response="body_mass_g", treatment="species", factor2="sex")
        assert res.design == "Fatorial"
        assert res.table.loc["species", "p_value"] < 0.05
        # apenas 2 níveis de sexo entraram (333 = 168 MALE + 165 FEMALE)
        assert res.n_obs == 333


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
