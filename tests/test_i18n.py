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
