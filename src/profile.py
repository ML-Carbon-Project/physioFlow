"""Perfil de dados — adapta a interface ao tipo de dataset carregado.

Em vez de assumir sempre o domínio de Fisiologia Vegetal, a plataforma resolve
um *perfil*:

* ``"fisiologia"`` — dataset reconhecido pelo schema de fisiologia (defaults,
  presets e relatório de schema específicos do domínio ficam ativos);
* ``"generico"`` — qualquer outro dataset (defaults neutros, sem presets de
  fisiologia e sem o ruído de "coluna obrigatória faltando").

A configuração do usuário (``"auto" | "fisiologia" | "generico"``) fica na
sessão; em ``"auto"`` o perfil é detectado pelo schema (:func:`detect_profile`).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from src.config.settings import SESSION_PROFILE_KEY
from src.schema import detect_profile

PROFILE_AUTO = "auto"
PROFILE_PHYSIOLOGY = "fisiologia"
PROFILE_GENERIC = "generico"

PROFILE_OPTIONS = (PROFILE_AUTO, PROFILE_PHYSIOLOGY, PROFILE_GENERIC)


def get_profile_setting() -> str:
    """Preferência do usuário (default ``"auto"``)."""
    return st.session_state.get(SESSION_PROFILE_KEY, PROFILE_AUTO)


def set_profile_setting(value: str) -> None:
    st.session_state[SESSION_PROFILE_KEY] = value


def resolve_profile(df: Optional[pd.DataFrame]) -> str:
    """Perfil efetivo: respeita o override manual; em ``"auto"`` detecta pelo df."""
    setting = get_profile_setting()
    if setting in (PROFILE_PHYSIOLOGY, PROFILE_GENERIC):
        return setting
    if df is None:
        return PROFILE_GENERIC
    return detect_profile(df)


def is_physiology(df: Optional[pd.DataFrame]) -> bool:
    """True quando o perfil efetivo é o de fisiologia."""
    return resolve_profile(df) == PROFILE_PHYSIOLOGY


__all__ = [
    "PROFILE_AUTO",
    "PROFILE_PHYSIOLOGY",
    "PROFILE_GENERIC",
    "PROFILE_OPTIONS",
    "get_profile_setting",
    "set_profile_setting",
    "resolve_profile",
    "is_physiology",
]
