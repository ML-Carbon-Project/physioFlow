"""Testes da função de tradução t()."""
from __future__ import annotations

import pytest


def test_t_returns_translation_when_key_exists():
    # Importações dentro dos testes para evitar inicializar Streamlit sem necessidade.
    from src.i18n import t
    # 'eda.summary.title' existe em pt.json.
    out = t("eda.summary.title")
    assert isinstance(out, str)
    assert out != "eda.summary.title"


def test_t_honors_default_when_key_missing():
    from src.i18n import t
    out = t("this.key.does.not.exist", default="Fallback Visible")
    assert out == "Fallback Visible"


def test_t_returns_key_when_no_default_and_key_missing():
    from src.i18n import t
    out = t("another.missing.key")
    assert out == "another.missing.key"


def test_t_default_is_not_propagated_as_placeholder():
    from src.i18n import t
    # default não deve ser passado para format() — não deve causar erro
    # mesmo que o template não tenha {default}.
    out = t("eda.summary.title", default="ignored fallback")
    # Como a chave existe, default é ignorado.
    assert out != "ignored fallback"
    assert "{default}" not in out


def test_t_format_params_still_work():
    from src.i18n import t
    # 'pipeline.warn_heavy_discard' tem {pct}, {before}, {after}.
    out = t("pipeline.warn_heavy_discard", pct="95.0", before=100, after=5, default="X")
    assert "95.0" in out
    assert "100" in out
    assert "5" in out


def test_t_missing_key_with_format_params_uses_default():
    from src.i18n import t
    out = t("totally.missing", default="Hello {name}", name="World")
    assert out == "Hello World"


# --- Rotulos do quadro de ANOVA (delineamentos de erro composto) -------------
# stats_utils.py devolve os termos de erro em pt-BR canonico; a traducao e
# feita na exibicao. Ver src/i18n/__init__.py:translate_anova_source.


@pytest.fixture
def language():
    """Troca o idioma e restaura o anterior ao fim do teste."""
    from src.i18n import get_language, set_language
    original = get_language()
    yield set_language
    set_language(original)


@pytest.mark.parametrize("code,expected", [
    ("pt", "Erro(a)"),
    ("en", "Error(a)"),
    ("es", "Error(a)"),
])
def test_translate_anova_source_translates_error_terms(language, code, expected):
    from src.i18n import translate_anova_source
    language(code)
    assert translate_anova_source("Erro(a)") == expected


def test_translate_anova_source_keeps_factor_names_untouched(language):
    from src.i18n import translate_anova_source
    language("en")
    # Nomes de fator vem das colunas do dataset e nao devem ser traduzidos.
    assert translate_anova_source("Variety") == "Variety"
    assert translate_anova_source("Variety × nitro") == "Variety × nitro"


@pytest.mark.parametrize("code", ["pt", "en", "es"])
def test_anova_error_labels_match_the_legend_below_the_table(language, code):
    """O rotulo na tabela e o termo citado na legenda devem coincidir.

    Regressao: a tabela mostrava "Erro(a)" enquanto a legenda logo abaixo dizia
    "Error(a)" com a interface em ingles.
    """
    from src.i18n import t, translate_anova_source
    language(code)

    split_legend = t("exp.split.legend", whole="A", sub="B")
    assert translate_anova_source("Erro(a)") in split_legend
    assert translate_anova_source("Erro(b)") in split_legend

    strip_legend = t("exp.strip.legend", a="A", b="B")
    for term in ("Erro(a)", "Erro(b)", "Erro(c)"):
        assert translate_anova_source(term) in strip_legend


@pytest.mark.parametrize("code", ["pt", "en", "es"])
def test_split_plot_table_renders_translated_labels(language, code):
    """Integracao: o quadro do stats_utils, ao ser exibido, sai traduzido."""
    import numpy as np
    import pandas as pd

    from src.i18n import translate_anova_source
    from src.stats_utils import fit_split_plot

    rng = np.random.default_rng(7)
    rows = [
        {"y": 10 + 2 * a + b + rng.normal(0, 0.3), "A": f"a{a}", "B": f"b{b}", "blk": f"r{r}"}
        for r in range(3) for a in range(2) for b in range(2)
    ]
    res = fit_split_plot(pd.DataFrame(rows), "y", "A", "B", "blk")

    # Canonico em pt-BR na camada de calculo...
    assert "Erro(a)" in res.table.index and "Erro(b)" in res.table.index

    # ...traduzido na camada de exibicao, preservando o nome do indice.
    language(code)
    display = res.table.rename(index=translate_anova_source)
    assert display.index.name == "source"
    assert translate_anova_source("Erro(a)") in display.index
    assert translate_anova_source("Erro(b)") in display.index
