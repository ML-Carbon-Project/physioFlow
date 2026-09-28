"""Carregador de tabelas de traducao a partir de JSON.

As traducoes ficam em ``src/i18n/locales/{code}.json``. Para adicionar um novo
idioma basta criar um novo arquivo JSON nesse diretorio com as mesmas chaves
do ``pt.json`` e registra-lo no dicionario ``AVAILABLE_LANGUAGES`` abaixo.

A funcao ``audit_keys()`` ajuda a verificar se todos os idiomas tem as mesmas
chaves; util em CI ou em script de manutencao.
"""
from __future__ import annotations

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

# Idioma padrao: usado quando uma chave esta ausente no idioma atual.
DEFAULT_LANGUAGE = "pt"

# Lista de idiomas oferecidos no seletor da sidebar. A ordem e mantida na UI.
AVAILABLE_LANGUAGES: dict[str, str] = {
    "pt": "Portugues",
    "en": "English",
    "es": "Espanol",
}


def _load_locale(code: str) -> dict[str, str]:
    """Carrega um arquivo JSON de locale; retorna dict vazio se nao existir."""
    path = LOCALES_DIR / f"{code}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_all() -> dict[str, dict[str, str]]:
    return {code: _load_locale(code) for code in AVAILABLE_LANGUAGES}


# Carregadas no import; em desenvolvimento, reinicie o Streamlit para recarregar.
TRANSLATIONS: dict[str, dict[str, str]] = _load_all()


def reload_translations() -> None:
    """Recarrega os JSONs do disco, util para hot-reload em desenvolvimento."""
    global TRANSLATIONS
    TRANSLATIONS = _load_all()


def audit_keys(reference: str = DEFAULT_LANGUAGE) -> dict[str, dict[str, list[str]]]:
    """Compara todas as locales com a de referencia e retorna chaves faltantes/extras.

    Resultado no formato::

        {
            "en": {"missing": ["key.x"], "extra": []},
            "es": {"missing": [], "extra": ["key.y"]},
        }
    """
    ref_keys: set[str] = set(TRANSLATIONS.get(reference, {}).keys())
    report: dict[str, dict[str, list[str]]] = {}
    for code, table in TRANSLATIONS.items():
        if code == reference:
            continue
        keys = set(table.keys())
        report[code] = {
            "missing": sorted(ref_keys - keys),
            "extra": sorted(keys - ref_keys),
        }
    return report
