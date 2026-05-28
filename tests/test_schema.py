"""Testes unitários para src/schema.py de Fisiologia Vegetal."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.schema import SCHEMA_SPECS, validate_dataframe


def _full_dataset(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "Cultura": rng.choice(["Soja", "Cana-de-açúcar"], n),
        "Uso atual": rng.choice(["Perene", "Rotativo"], n),
        "Época": rng.choice(["Verão", "Primavera"], n),
        "A": rng.normal(25, 5, n),
        "E": rng.normal(8, 2, n),
        "gs": rng.normal(0.5, 0.1, n),
        "Ca": rng.normal(390, 5, n),
        "Ci": rng.normal(250, 20, n),
        "Ci/Ca": rng.uniform(0.5, 0.8, n),
        "EUA": rng.uniform(2.0, 5.0, n),
        "A/Ci": rng.uniform(0.05, 0.15, n),
        "YII": rng.uniform(0.1, 0.3, n),
        "ETR": rng.uniform(80, 180, n),
        "Chl a": rng.normal(30, 3, n),
        "Chl b": rng.normal(10, 2, n),
        "IAF": rng.normal(3.5, 1.0, n),
        "Fazenda": rng.choice(["Fazenda A", "Fazenda B"], n),
        "Município": rng.choice(["Rio Verde", "Jataí"], n),
        "Latitude": rng.uniform(-17.9, -17.5, n),
        "Longitude": rng.uniform(-51.2, -50.8, n),
    })


class TestValidateDataframeFullSchema:
    def test_full_schema_marks_all_present(self):
        df = _full_dataset()
        result = validate_dataframe(df)
        assert result.required_missing == []
        assert result.recommended_missing == []
        statuses = {r["label"]: r["status"] for r in result.rows}
        assert statuses["Cultura"] == "present"
        assert statuses["A (Taxa Fotossintética)"] == "present"
        assert statuses["Latitude"] == "present"

    def test_no_blocking_issues_on_full_dataset(self):
        df = _full_dataset()
        result = validate_dataframe(df)
        assert not result.has_blocking_issues


class TestValidateDataframeMissingColumns:
    def test_missing_required_column_is_reported(self):
        # Cultura é obrigatório
        df = _full_dataset().drop(columns=["Cultura"])
        result = validate_dataframe(df)
        assert "Cultura" in result.required_missing
        assert result.has_blocking_issues

    def test_missing_recommended_does_not_block(self):
        # A é recomendada (não obrigatória)
        df = _full_dataset().drop(columns=["A"])
        result = validate_dataframe(df)
        assert "A (Taxa Fotossintética)" in result.recommended_missing
        assert not result.has_blocking_issues

    def test_optional_missing_is_silent(self):
        df = _full_dataset().drop(columns=["Latitude", "Longitude"])
        result = validate_dataframe(df)
        latitude_status = next(r["status"] for r in result.rows if r["label"] == "Latitude")
        longitude_status = next(r["status"] for r in result.rows if r["label"] == "Longitude")
        assert latitude_status == "missing"
        assert longitude_status == "missing"
        assert "Latitude" not in result.required_missing
        assert "Latitude" not in result.recommended_missing


class TestValidateDataframeTypeChecking:
    def test_string_A_flagged_as_type_mismatch(self):
        df = _full_dataset()
        df["A"] = ["invalido"] * len(df)
        result = validate_dataframe(df)
        a_row = next(r for r in result.rows if r["label"] == "A (Taxa Fotossintética)")
        assert a_row["status"] == "type_mismatch"
        assert any("A" in w for w in result.warnings)


class TestValidateDataframeCoordinateRanges:
    def test_latitude_out_of_range_flags_error(self):
        df = _full_dataset()
        df.loc[0, "Latitude"] = 120.0
        result = validate_dataframe(df)
        assert any("Latitude" in e for e in result.errors)


class TestValidateDataframeEmpty:
    def test_empty_dataframe_marks_all_missing(self):
        df = pd.DataFrame()
        result = validate_dataframe(df)
        assert all(r["status"] == "missing" for r in result.rows)
        assert result.required_missing
        assert len(result.rows) == len(SCHEMA_SPECS)


class TestValidateDataframeAllNullColumn:
    def test_required_column_all_null_is_flagged_as_empty(self):
        df = _full_dataset()
        df["Uso atual"] = np.nan
        result = validate_dataframe(df)
        uso_row = next(r for r in result.rows if r["label"] == "Uso atual")
        assert uso_row["status"] == "empty"
        assert "Uso atual" in result.required_empty
        assert "Uso atual" not in result.required_missing
        assert any("100% vazia" in w for w in result.warnings)

    def test_recommended_column_all_null_is_flagged_as_empty(self):
        df = _full_dataset()
        df["A"] = np.nan
        result = validate_dataframe(df)
        a_row = next(r for r in result.rows if r["label"] == "A (Taxa Fotossintética)")
        assert a_row["status"] == "empty"
        assert "A (Taxa Fotossintética)" in result.recommended_empty

    def test_optional_column_all_null_emits_no_warning(self):
        df = _full_dataset()
        df["Latitude"] = np.nan
        result = validate_dataframe(df)
        lat_row = next(r for r in result.rows if r["label"] == "Latitude")
        # Status ainda marcado como "empty" para inspeção via tabela,
        # mas sem warning porque é coluna opcional.
        assert lat_row["status"] == "empty"
        assert not any("Latitude" in w for w in result.warnings)

    def test_empty_required_column_does_not_block(self):
        # `has_blocking_issues` depende só de required_missing/errors, não de empty.
        # O bloqueio fica a cargo do warning visual.
        df = _full_dataset()
        df["Uso atual"] = np.nan
        result = validate_dataframe(df)
        assert not result.has_blocking_issues
