"""Teste de fumaça *headless* da página de Modelagem via ``streamlit.testing``.

Roda a página inteira sem navegador (mesmo processo, sem auth/sidebar) e verifica
que o fluxo de **classificação** renderiza sem exceção e produz os elementos que
uma ferramenta apresentável deve ter: tabela de métricas, cartões de destaque,
matriz de confusão e gráfico de importâncias.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

PENGUINS = Path(__file__).resolve().parents[1] / "data" / "sample" / "test" / "penguins.csv"


def _app(path: str):
    """Script executado pelo AppTest: semeia o penguins e renderiza a página."""
    import pandas as pd
    import streamlit as st

    from src.pages.modeling import render

    df = pd.read_csv(path)
    st.session_state["df_raw"] = df
    st.session_state["df_processed"] = df.copy()
    render()


def _make_app():
    return AppTest.from_function(_app, kwargs={"path": str(PENGUINS)}, default_timeout=90)


@pytest.mark.skipif(not PENGUINS.exists(), reason="fixture penguins ausente")
def test_regression_page_renders_headless():
    at = _make_app()
    at.run()
    # Modo padrão é regressão. Com o penguins não há as features default de
    # fisiologia, então a página exibe o aviso "selecione features" de forma
    # graciosa — o que importa aqui é renderizar sem exceção (sem-dado tratado).
    assert not at.exception, at.exception


@pytest.mark.skipif(not PENGUINS.exists(), reason="fixture penguins ausente")
def test_classification_page_renders_headless():
    at = _make_app()
    at.run()
    assert not at.exception, at.exception

    # Alterna para classificação; defaults (alvo species, features numéricas,
    # Logística + Random Forest, StandardScaler, StratifiedKFold) já rodam.
    at.radio(key="modeling_task").set_value("classification").run()
    assert not at.exception, at.exception

    # Tabela de métricas (acurácia/F1/precisão/revocação/CV) presente.
    assert len(at.dataframe) >= 1
    # Cartões de destaque: melhor CV acurácia + melhor F1.
    assert len(at.metric) >= 2
    # Matriz de confusão + gráfico de importâncias são figuras matplotlib
    # (st.pyplot é exposto como "imgs" no AppTest).
    assert len(at.get("imgs")) >= 1


@pytest.mark.skipif(not PENGUINS.exists(), reason="fixture penguins ausente")
def test_classification_scaler_and_cv_controls_exist():
    at = _make_app()
    at.run()
    at.radio(key="modeling_task").set_value("classification").run()
    assert not at.exception, at.exception

    keys = {sb.key for sb in at.selectbox}
    assert "modeling_clf_scaler" in keys
    assert "modeling_clf_cv_kind" in keys

    # Trocar a escala para "none" não pode quebrar a página.
    at.selectbox(key="modeling_clf_scaler").set_value("none").run()
    assert not at.exception, at.exception
