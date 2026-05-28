"""Validação do schema esperado para o dataset de Fisiologia Vegetal.

Define três tiers de colunas:

* **required** — sem essas colunas, partes essenciais do app não funcionam.
  Não causam falha; são reportadas com severidade alta.
* **recommended** — habilitam análises padrão (EDA, pipeline default,
  regressão padrão). Reportadas com severidade média.
* **optional** — habilitam funcionalidades específicas (espacial, temporal,
  réplicas extras). Reportadas com severidade informativa.

A função :func:`validate_dataframe` retorna um relatório estruturado que pode
ser renderizado na Upload page sem alterar o fluxo de carregamento.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ColumnSpec:
    """Especificação de uma coluna esperada."""

    candidates: tuple[str, ...]  # nomes alternativos aceitos
    label: str
    tier: str  # "required" | "recommended" | "optional"
    expected_type: str  # "numeric" | "categorical" | "datetime"
    feature: str  # módulo/feature que depende dessa coluna
    notes: str = ""


# Schema de referência para o dataset de Fisiologia Vegetal
SCHEMA_SPECS: tuple[ColumnSpec, ...] = (
    ColumnSpec(
        ("Cultura", "CULTURA", "Crop_Type"),
        "Cultura",
        tier="required",
        expected_type="categorical",
        feature="EDA, Comparativa, Modelagem, Filtros",
    ),
    ColumnSpec(
        ("Uso atual", "USO_ATUAL", "Uso atual", "Land_Use"),
        "Uso atual",
        tier="required",
        expected_type="categorical",
        feature="EDA, Comparativa, Filtros",
    ),
    ColumnSpec(
        ("Época", "EPOCA", "Season", "Estação"),
        "Época / Estação do ano",
        tier="required",
        expected_type="categorical",
        feature="EDA, Comparativa, Filtros",
    ),
    ColumnSpec(
        ("A", "Fotossíntese", "Photosynthesis"),
        "A (Taxa Fotossintética)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Regressão, Modelagem Preditiva",
        notes="Medida pelo IRGA (µmol m⁻² s⁻¹)",
    ),
    ColumnSpec(
        ("E", "Transpiração", "Transpiration"),
        "E (Taxa Transpiratória)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Regressão",
        notes="Medida pelo IRGA (mmol m⁻² s⁻¹)",
    ),
    ColumnSpec(
        ("gs", "Condutância", "Stomatal_Conductance"),
        "gs (Condutância Estomática)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Regressão, Modelagem Preditiva",
        notes="Medida pelo IRGA (mol m⁻² s⁻¹)",
    ),
    ColumnSpec(
        ("Ca", "CO2_Externo"),
        "Ca (CO₂ Externo)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Modelagem Preditiva",
        notes="Medida pelo IRGA (µmol m⁻² s⁻¹)",
    ),
    ColumnSpec(
        ("Ci", "CO2_Interno"),
        "Ci (CO₂ Interno)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Modelagem Preditiva",
        notes="Medida pelo IRGA (µmol m⁻² s⁻¹)",
    ),
    ColumnSpec(
        ("Ci/Ca", "Ci_Ca"),
        "Relação Ci/Ca",
        tier="recommended",
        expected_type="numeric",
        feature="EDA",
    ),
    ColumnSpec(
        ("EUA", "WUE"),
        "EUA (Eficiência no uso da água)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Regressão",
    ),
    ColumnSpec(
        ("A/Ci", "A_Ci"),
        "Eficiência de carboxilação (A/Ci)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA",
    ),
    ColumnSpec(
        ("YII", "Yield_II"),
        "YII (Rendimento Quântico de FSII)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Modelagem Preditiva",
    ),
    ColumnSpec(
        ("ETR", "Electron_Transport"),
        "ETR (Taxa de transporte de elétrons)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Modelagem Preditiva",
    ),
    ColumnSpec(
        ("Chl a", "Clorofila_a", "Chlorophyll_a"),
        "Clorofila a",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Pipeline (média/desdobrar)",
        notes="Medida pelo Clorofilog",
    ),
    ColumnSpec(
        ("Chl b", "Clorofila_b", "Chlorophyll_b"),
        "Clorofila b",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Pipeline (média/desdobrar)",
        notes="Medida pelo Clorofilog",
    ),
    ColumnSpec(
        ("IAF", "LAI"),
        "IAF (Índice de Área Foliar)",
        tier="recommended",
        expected_type="numeric",
        feature="EDA, Pipeline (média/desdobrar)",
        notes="Medido pelo Ceptômetro",
    ),
    ColumnSpec(
        ("Fazenda", "FAZENDA", "Coll_Cluster"),
        "Fazenda",
        tier="recommended",
        expected_type="categorical",
        feature="EDA, Filtros, Comparativa",
    ),
    ColumnSpec(
        ("Município", "MUNICIPIO"),
        "Município",
        tier="recommended",
        expected_type="categorical",
        feature="EDA, Filtros, Comparativa",
    ),
    ColumnSpec(
        ("ID", "Id"),
        "Identificação da amostra",
        tier="optional",
        expected_type="categorical",
        feature="EDA, Pipeline",
    ),
    ColumnSpec(
        ("Ponto", "PONTO"),
        "Ponto Amostral",
        tier="optional",
        expected_type="numeric",
        feature="EDA, Pipeline, Filtros",
    ),
    ColumnSpec(
        ("LATITUDE", "Latitude", "latitude"),
        "Latitude",
        tier="optional",
        expected_type="numeric",
        feature="Análise Espacial, Mapas Folium",
    ),
    ColumnSpec(
        ("LONGITUDE", "Longitude", "longitude"),
        "Longitude",
        tier="optional",
        expected_type="numeric",
        feature="Análise Espacial, Mapas Folium",
    ),
    ColumnSpec(
        ("Data da coleta", "Data", "Date", "DATE", "DATE_TIME"),
        "Data da coleta",
        tier="optional",
        expected_type="datetime",
        feature="Série Temporal, Filtro de Período",
    ),
    ColumnSpec(
        ("Estágio", "Estágio ", "Estagio", "Phenological_Stage"),
        "Estágio Fenológico",
        tier="optional",
        expected_type="categorical",
        feature="EDA, Comparativa",
    ),
    ColumnSpec(
        ("Peso Seco", "Biomassa_Seca", "Dry_Weight"),
        "Peso Seco",
        tier="optional",
        expected_type="numeric",
        feature="EDA",
    ),
    ColumnSpec(
        ("Chl a.1", "Clorofila_a_rep1"),
        "Clorofila a (Réplica 1)",
        tier="optional",
        expected_type="numeric",
        feature="Pipeline (média/desdobrar)",
    ),
    ColumnSpec(
        ("Chl b.1", "Clorofila_b_rep1"),
        "Clorofila b (Réplica 1)",
        tier="optional",
        expected_type="numeric",
        feature="Pipeline (média/desdobrar)",
    ),
    ColumnSpec(
        ("IAF.1", "LAI_rep1"),
        "IAF (Réplica 1)",
        tier="optional",
        expected_type="numeric",
        feature="Pipeline (média/desdobrar)",
    ),
    ColumnSpec(
        ("IAF.2", "LAI_rep2"),
        "IAF (Réplica 2)",
        tier="optional",
        expected_type="numeric",
        feature="Pipeline (média/desdobrar)",
    ),
    ColumnSpec(
        ("Manejo", "MANEJO", "Soil_Management"),
        "Manejo do Solo",
        tier="optional",
        expected_type="categorical",
        feature="EDA, Filtros futuros",
    ),
    ColumnSpec(
        ("Textura", "TEXTURA", "Soil_Texture"),
        "Textura do Solo",
        tier="optional",
        expected_type="categorical",
        feature="EDA, Filtros futuros",
    ),
)


@dataclass
class ValidationResult:
    rows: list[dict]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def required_missing(self) -> list[str]:
        return [r["label"] for r in self.rows if r["tier"] == "required" and r["status"] == "missing"]

    @property
    def recommended_missing(self) -> list[str]:
        return [r["label"] for r in self.rows if r["tier"] == "recommended" and r["status"] == "missing"]

    @property
    def required_empty(self) -> list[str]:
        return [r["label"] for r in self.rows if r["tier"] == "required" and r["status"] == "empty"]

    @property
    def recommended_empty(self) -> list[str]:
        return [r["label"] for r in self.rows if r["tier"] == "recommended" and r["status"] == "empty"]

    @property
    def has_blocking_issues(self) -> bool:
        return bool(self.required_missing) or bool(self.errors)


def _first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _check_type(series: pd.Series, expected: str) -> tuple[bool, str]:
    non_null = series.dropna()
    if non_null.empty:
        # Coluna existe mas está 100% nula: não é mismatch de tipo, mas precisa
        # ser sinalizada para que features dependentes não falhem silenciosamente.
        return True, "empty"

    if expected == "numeric":
        if pd.api.types.is_numeric_dtype(series):
            return True, "numeric"
        coerced = pd.to_numeric(non_null, errors="coerce")
        if coerced.notna().sum() / len(non_null) >= 0.9:
            return True, "numeric (coercível)"
        return False, str(series.dtype)
    if expected == "datetime":
        if pd.api.types.is_datetime64_any_dtype(series):
            return True, "datetime"
        coerced = pd.to_datetime(non_null, errors="coerce")
        if coerced.notna().sum() / len(non_null) >= 0.9:
            return True, "datetime (coercível)"
        return False, str(series.dtype)
    if expected == "categorical":
        return not pd.api.types.is_numeric_dtype(series) or series.nunique(dropna=True) <= 30, str(series.dtype)
    return True, str(series.dtype)


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    rows: list[dict] = []
    warnings: list[str] = []
    errors: list[str] = []

    # Remove extra whitespace in column names before checking
    df = df.rename(columns=lambda c: c.strip() if isinstance(c, str) else c)

    for spec in SCHEMA_SPECS:
        found = _first_existing(df, spec.candidates)
        if found is None:
            rows.append({
                "label": spec.label,
                "expected": " | ".join(spec.candidates),
                "found": None,
                "tier": spec.tier,
                "status": "missing",
                "type_ok": None,
                "type_found": None,
                "feature": spec.feature,
            })
            continue

        ok, dtype = _check_type(df[found], spec.expected_type)
        if dtype == "empty":
            status = "empty"
        elif ok:
            status = "present"
        else:
            status = "type_mismatch"
        rows.append({
            "label": spec.label,
            "expected": " | ".join(spec.candidates),
            "found": found,
            "tier": spec.tier,
            "status": status,
            "type_ok": ok,
            "type_found": dtype,
            "feature": spec.feature,
        })
        if status == "type_mismatch":
            warnings.append(
                f"Coluna '{found}' encontrada para {spec.label} mas o tipo não é {spec.expected_type} ({dtype})."
            )
        elif status == "empty" and spec.tier in ("required", "recommended"):
            warnings.append(
                f"Coluna '{found}' (para {spec.label}) existe mas está 100% vazia — funcionalidades dependentes podem falhar."
            )

    lat = _first_existing(df, ("Latitude", "LATITUDE"))
    lon = _first_existing(df, ("Longitude", "LONGITUDE"))
    if lat and lon:
        try:
            lat_num = pd.to_numeric(df[lat], errors="coerce").dropna()
            lon_num = pd.to_numeric(df[lon], errors="coerce").dropna()
            if not lat_num.empty and not (-90 <= lat_num.min() <= lat_num.max() <= 90):
                errors.append("Latitude fora do intervalo [-90, 90].")
            if not lon_num.empty and not (-180 <= lon_num.min() <= lon_num.max() <= 180):
                errors.append("Longitude fora do intervalo [-180, 180].")
        except Exception:
            pass

    return ValidationResult(rows=rows, warnings=warnings, errors=errors)
