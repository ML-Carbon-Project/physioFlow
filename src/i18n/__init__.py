"""API publica de internacionalizacao.

Uso tipico:

    from src.i18n import t, set_language
    st.title(t("upload.title"))

A linguagem ativa e armazenada em ``st.session_state["language"]`` e o seletor
fica na sidebar. Caso uma chave nao exista no idioma atual, faz fallback para
o idioma padrao definido em ``DEFAULT_LANGUAGE``.
"""
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from src.i18n.translations import (
    AVAILABLE_LANGUAGES,
    DEFAULT_LANGUAGE,
    TRANSLATIONS,
)

LANGUAGE_KEY = "language"


def get_language() -> str:
    return st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)


def set_language(language: str) -> None:
    if language not in AVAILABLE_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    st.session_state[LANGUAGE_KEY] = language


def t(key: str, **params: Any) -> str:
    """Retorna a traducao da chave no idioma corrente.

    Aplica ``str.format(**params)`` quando ha parametros nomeados.

    Resolucao em ordem:
    1. Locale ativo.
    2. Locale padrao (``DEFAULT_LANGUAGE``).
    3. Argumento ``default=`` (se passado).
    4. Propria chave (para facilitar depuracao).

    O parametro ``default`` e tratado a parte e nao e propagado para
    ``str.format``; os demais ``**params`` viram placeholders nomeados.
    """
    fallback = params.pop("default", None)

    language = get_language()
    template = TRANSLATIONS.get(language, {}).get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
    if template is None:
        template = fallback if fallback is not None else key

    if params:
        try:
            return template.format(**params)
        except (KeyError, IndexError):
            return template
    return template


# ---- Traducao em runtime das mensagens StepLog produzidas em pipeline.py ----
# pipeline.py mantem as mensagens em pt-BR (compatibilidade com testes). A
# traducao ocorre apenas na hora de exibir o relatorio.
#
# Duas familias de padroes coexistem:
#   * legacy (ChamberFlux): patterns regex genericos que casam com nomes
#     dinamicos como "Filtro R2 (CO2_DRY >= 0.9)";
#   * physioflow: mapeamento direto (string-para-string) com os 9 nomes
#     de etapa atuais do pipeline de Fisiologia Vegetal.
_STEP_PATTERNS_EN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^Filtro diagnostico \((.+) == (.+)\)$"), "Diagnostic filter ({0} == {1})"),
    (re.compile(r"^Remocao de variaveis \((\d+) colunas\)$"), "Variable removal ({0} columns)"),
    (re.compile(r"^Remocao de variaveis ignorada \(sem colunas validas\)$"), "Variable removal skipped (no valid columns)"),
    (re.compile(r"^Filtro R2 \((.+) >= ([\d.]+)\)$"), "R2 filter ({0} >= {1})"),
    (re.compile(r"^Filtro R2 \(sem colunas R2 encontradas\)$"), "R2 filter (no R2 columns found)"),
    (re.compile(r"^Outliers por quantil \(([\d.]+)-([\d.]+)\) por (.+)$"), "Outliers by quantile ({0}-{1}) per {2}"),
    (re.compile(r"^Outliers por quantil \(([\d.]+)-([\d.]+)\) global$"), "Outliers by quantile ({0}-{1}) global"),
    (re.compile(r"^Outliers ignorado \(sem colunas validas\)$"), "Outliers skipped (no valid columns)"),
    (re.compile(r"^Agregacao de repeticoes por (\w+) \((\d+) grupos com N_REPS>1\)$"), "Replicate aggregation by {0} ({1} groups with N_REPS>1)"),
    (re.compile(r"^Agregacao REP ignorada \((.+)\)$"), "REP aggregation skipped ({0})"),
]

# Mapeamento exato dos nomes de etapa atuais do PhysioFlow.
# Quando o pipeline.py cria um StepLog(step="<x>"), procuramos primeiro aqui
# antes de tentar os padroes legacy acima.
_STEP_MAP_EN: dict[str, str] = {
    "Padronização de texto (stripping de strings)": "Text standardization (string stripping)",
    "Remoção de registros sem metadados essenciais": "Removal of records without essential metadata",
    "Remoção de pontos de grade vazios (sem medição)": "Removal of empty grid points (no measurements)",
    "Consolidação de réplicas por média aritmética": "Replicate consolidation by arithmetic mean",
    "Consolidação de réplicas por mediana": "Replicate consolidation by median",
    "Desdobramento de réplicas em registros separados": "Replicate unfolding into separate records",
    "Seleção exclusiva da Réplica 1": "Replicate 1 only",
    "Seleção exclusiva da Réplica 2": "Replicate 2 only",
    "Seleção exclusiva da Réplica 3 (IAF)": "Replicate 3 only (LAI)",
}

_STEP_MAP_ES: dict[str, str] = {
    "Padronização de texto (stripping de strings)": "Estandarización de texto (stripping de cadenas)",
    "Remoção de registros sem metadados essenciais": "Eliminación de registros sin metadatos esenciales",
    "Remoção de pontos de grade vazios (sem medição)": "Eliminación de puntos de cuadrícula vacíos (sin medición)",
    "Consolidação de réplicas por média aritmética": "Consolidación de réplicas por media aritmética",
    "Consolidação de réplicas por mediana": "Consolidación de réplicas por mediana",
    "Desdobramento de réplicas em registros separados": "Desdoblamiento de réplicas en registros separados",
    "Seleção exclusiva da Réplica 1": "Sólo Réplica 1",
    "Seleção exclusiva da Réplica 2": "Sólo Réplica 2",
    "Seleção exclusiva da Réplica 3 (IAF)": "Sólo Réplica 3 (IAF)",
}


def translate_step(step: str) -> str:
    """Traduz uma mensagem StepLog gerada em pt-BR para o idioma corrente.

    Ordem de resolucao:
    1. Mapeamento exato no dicionario do idioma ativo (etapas atuais do PhysioFlow).
    2. Patterns regex legacy (compatibilidade com ChamberFlux) — apenas en.
    3. Retorna o original em pt-BR.
    """
    language = get_language()
    if language == "en":
        if step in _STEP_MAP_EN:
            return _STEP_MAP_EN[step]
        for pattern, template in _STEP_PATTERNS_EN:
            match = pattern.match(step)
            if match:
                return template.format(*match.groups())
    elif language == "es":
        if step in _STEP_MAP_ES:
            return _STEP_MAP_ES[step]
    return step


__all__ = [
    "AVAILABLE_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "get_language",
    "set_language",
    "t",
    "translate_step",
]
