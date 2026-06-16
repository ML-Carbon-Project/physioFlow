"""Robustez das páginas contra datasets adversariais (perfil genérico).

Cada página deve renderizar SEM exceção mesmo com datasets de borda: só
numéricos, só categóricos, mínimos, coluna categórica chamada "A" (colisão com o
default de fisiologia) e coluna única. Captura a classe de bug do
``lista.index(default)`` / ``lista[0]`` em lista vazia.

Roda via ``streamlit.testing`` (headless). Limitado às páginas analíticas que
fazem inferência de tipos de coluna — as que mais sofrem com dados arbitrários.
"""
from __future__ import annotations

import itertools

import pytest
from streamlit.testing.v1 import AppTest

_PAGES = ["eda", "regression", "modeling", "comparative", "experimental", "pipeline"]
_DATASETS = ["num_only", "cat_heavy", "minimal", "cat_A", "one_num"]


def _run(page: str, ds: str):
    import numpy as np
    import pandas as pd
    import streamlit as st

    from src.config.settings import SESSION_PROCESSED_KEY, SESSION_RAW_KEY
    from src.pages import PAGE_RENDERERS

    rng = np.random.default_rng(0)
    if ds == "num_only":
        df = pd.DataFrame({c: rng.normal(0, 1, 40) for c in ("x", "y", "z")})
    elif ds == "cat_heavy":
        df = pd.DataFrame({"g1": ["a", "b", "c", "d"] * 10, "g2": ["x", "y"] * 20, "val": rng.normal(0, 1, 40)})
    elif ds == "minimal":
        df = pd.DataFrame({"grp": ["a", "b"] * 10, "v": rng.normal(0, 1, 20)})
    elif ds == "cat_A":
        df = pd.DataFrame({"A": ["x", "y", "z"] * 10, "B": ["p", "q"] * 15,
                           "blk": list(range(1, 31)), "y": rng.normal(0, 1, 30)})
    else:  # one_num
        df = pd.DataFrame({"only": rng.normal(0, 1, 30)})

    st.session_state[SESSION_RAW_KEY] = df
    st.session_state[SESSION_PROCESSED_KEY] = df.copy()
    st.session_state["data_profile"] = "generico"
    PAGE_RENDERERS[page]()


@pytest.mark.parametrize("page,ds", list(itertools.product(_PAGES, _DATASETS)))
def test_page_does_not_crash_on_adversarial_dataset(page, ds):
    at = AppTest.from_function(_run, kwargs={"page": page, "ds": ds}, default_timeout=60).run()
    assert not at.exception, f"{page} × {ds}: {at.exception}"
