"""Testes unitários para src/pipeline.py de Fisiologia Vegetal

Rode com:
    pytest tests/ -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.pipeline import (
    StepLog,
    build_step_report,
    clean_fisiologia_data,
    coerce_date_series,
    find_date_column,
    find_first_existing,
)


def _make_df(**kwargs) -> pd.DataFrame:
    return pd.DataFrame(kwargs)


class TestFindFirstExisting:
    def test_exact_match(self):
        df = _make_df(A=[1], B=[2])
        assert find_first_existing(df, ["A"]) == "A"

    def test_case_insensitive(self):
        df = _make_df(CULTURA=["Soja"])
        assert find_first_existing(df, ["cultura"]) == "CULTURA"

    def test_with_spaces_in_df(self):
        df = _make_df(**{"Cultura ": ["Soja"]})
        assert find_first_existing(df, ["Cultura"]) == "Cultura "


class TestCleanFisiologiaData:
    def setup_method(self):
        # Cria um dataset mockup de Fisiologia
        self.df_raw = pd.DataFrame({
            "Cultura": ["Soja", "Soja", np.nan, "Cana", "Cana"],
            "Uso atual": ["Perene", "Perene", "Perene", np.nan, "Perene"],
            "Época": ["Verão", "Verão", "Verão", "Verão", "Verão"],
            "A": [25.0, np.nan, 30.0, 15.0, np.nan],
            "E": [10.0, np.nan, 12.0, 5.0, np.nan],
            "gs": [0.5, np.nan, 0.6, 0.2, np.nan],
            "Chl a": [30.0, np.nan, 32.0, 20.0, np.nan],
            "Chl a.1": [28.0, np.nan, 30.0, 22.0, np.nan],
            "Chl b": [10.0, np.nan, 12.0, 8.0, np.nan],
            "Chl b.1": [8.0, np.nan, 10.0, np.nan, np.nan],
            "IAF": [3.0, np.nan, 4.0, 2.0, np.nan],
            "IAF.1": [2.8, np.nan, 3.8, 2.2, np.nan],
            "IAF.2": [3.2, np.nan, 4.2, np.nan, np.nan],
        })

    def test_clean_pipeline_media(self):
        # Executa limpeza no modo média
        df_clean, logs = clean_fisiologia_data(self.df_raw, rep_method="media")
        
        # 1. Deve remover linhas com metadados essenciais nulos (linhas índice 2 (Cultura nula) e 3 (Uso atual nulo))
        # 2. Deve remover linhas onde todas as variáveis agronômicas são nulas (linha índice 1 e 4 (nulas))
        # Portanto, deve restar apenas a linha 0
        assert len(df_clean) == 1
        row = df_clean.iloc[0]
        assert row["Cultura"] == "Soja"
        
        # Média de Clorofila a: mean(30.0, 28.0) = 29.0
        assert row["Chl_a_media"] == pytest.approx(29.0)
        # Média de Clorofila b: mean(10.0, 8.0) = 9.0
        assert row["Chl_b_media"] == pytest.approx(9.0)
        # Média de IAF: mean(3.0, 2.8, 3.2) = 3.0
        assert row["IAF_media"] == pytest.approx(3.0)

    def test_clean_pipeline_desdobrar(self):
        # Executa limpeza no modo desdobrar (melt de réplicas)
        df_clean, logs = clean_fisiologia_data(self.df_raw, rep_method="desdobrar")
        
        # A linha 0 (válida) tem réplicas 1, 2 e 3 válidas.
        # Deve gerar 3 linhas a partir da linha 0 original
        assert len(df_clean) >= 3
        
        reps = df_clean[df_clean["Cultura"] == "Soja"]
        assert len(reps) == 3
        
        r1 = reps[reps["Replica"] == "Réplica 1"].iloc[0]
        r2 = reps[reps["Replica"] == "Réplica 2"].iloc[0]
        r3 = reps[reps["Replica"] == "Réplica 3"].iloc[0]
        
        assert r1["Chl_a_media"] == 30.0
        assert r2["Chl_a_media"] == 28.0
        assert r3["Chl_a_media"] is None or np.isnan(r3["Chl_a_media"])
        
        assert r1["IAF_media"] == 3.0
        assert r2["IAF_media"] == 2.8
        assert r3["IAF_media"] == 3.2

    def test_clean_pipeline_replica_especifica(self):
        df_clean, _ = clean_fisiologia_data(self.df_raw, rep_method="replica_1")
        assert len(df_clean) == 1
        row = df_clean.iloc[0]
        assert row["Chl_a_media"] == 30.0  # valor original de Chl a (Replica 1)
        assert row["IAF_media"] == 3.0

        df_clean2, _ = clean_fisiologia_data(self.df_raw, rep_method="replica_2")
        assert len(df_clean2) == 1
        row2 = df_clean2.iloc[0]
        assert row2["Chl_a_media"] == 28.0  # valor de Chl a.1 (Replica 2)
        assert row2["IAF_media"] == 2.8

    def test_clean_pipeline_mediana(self):
        df_clean, logs = clean_fisiologia_data(self.df_raw, rep_method="mediana")
        assert len(df_clean) == 1
        row = df_clean.iloc[0]
        # Chl a: median(30.0, 28.0) = 29.0  → idêntico à média com n=2
        assert row["Chl_a_media"] == pytest.approx(29.0)
        # Chl b: median(10.0, 8.0) = 9.0  → idêntico à média com n=2
        assert row["Chl_b_media"] == pytest.approx(9.0)
        # IAF: median(3.0, 2.8, 3.2) = 3.0  → coincide com a média neste caso
        assert row["IAF_media"] == pytest.approx(3.0)
        # Verifica que a etapa correta foi registrada
        assert any("mediana" in step.step.lower() for step in logs)

    def test_mediana_robustness_with_outlier_iaf(self):
        # Cenário em que mediana e média divergem: outlier em IAF.2.
        df = pd.DataFrame({
            "Cultura": ["Soja"],
            "Uso atual": ["Perene"],
            "Época": ["Verão"],
            "A": [25.0],
            "IAF": [3.0],
            "IAF.1": [3.1],
            "IAF.2": [99.0],  # leitura espúria (ex.: ceptômetro lendo o céu)
        })
        media_clean, _ = clean_fisiologia_data(df, rep_method="media")
        mediana_clean, _ = clean_fisiologia_data(df, rep_method="mediana")
        # média puxa o resultado pelo outlier; mediana descarta-o
        assert media_clean.iloc[0]["IAF_media"] == pytest.approx((3.0 + 3.1 + 99.0) / 3)
        assert mediana_clean.iloc[0]["IAF_media"] == pytest.approx(3.1)


class TestFindDateColumn:
    def test_finds_canonical_name(self):
        df = pd.DataFrame({"Data da coleta": pd.date_range("2025-01-01", periods=5)})
        assert find_date_column(df) == "Data da coleta"

    def test_finds_datetime64_by_dtype(self):
        df = pd.DataFrame({"foo_date": pd.date_range("2025-01-01", periods=5), "other": [1] * 5})
        assert find_date_column(df) == "foo_date"

    def test_finds_object_with_datetime_mixture(self):
        # Cenário do dataset real: Excel devolve object com datetime + str + NaN
        import datetime as dt
        col = [dt.datetime(2025, 12, 19)] * 3 + ["1/16/2026", np.nan, np.nan, np.nan]
        df = pd.DataFrame({"Outra": ["x"] * 7, "Data da coleta": col})
        assert find_date_column(df) == "Data da coleta"

    def test_returns_none_when_no_date(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        assert find_date_column(df) is None

    def test_returns_none_for_empty_df(self):
        assert find_date_column(pd.DataFrame()) is None


class TestCoerceDateSeries:
    def test_passes_through_datetime64(self):
        s = pd.Series(pd.date_range("2025-01-01", periods=3))
        out = coerce_date_series(s)
        assert out is s or out.equals(s)
        assert pd.api.types.is_datetime64_any_dtype(out)

    def test_coerces_mixed_object_to_datetime(self):
        import datetime as dt
        s = pd.Series([dt.datetime(2025, 12, 19), "1/16/2026", np.nan, "garbage"])
        out = coerce_date_series(s)
        assert pd.api.types.is_datetime64_any_dtype(out)
        # Linha válida real → datetime; "garbage" e NaN → NaT
        assert out.notna().sum() == 2


class TestUtmProjection:
    """Verifica o helper de projeção lon/lat → UTM usado nas análises espaciais."""

    def test_southern_hemisphere_epsg(self):
        from src.pages.spatial import _utm_epsg_from_lon
        # Rio Verde, GO: ~ -17.8°, -51°  → UTM zone 22 South = EPSG 32722
        assert _utm_epsg_from_lon(-51.0, -17.8) == 32722

    def test_northern_hemisphere_epsg(self):
        from src.pages.spatial import _utm_epsg_from_lon
        # Lon -60°, lat 10° (norte da América do Sul) → UTM zone 21 Norte = EPSG 32621
        assert _utm_epsg_from_lon(-60.0, 10.0) == 32621

    def test_projection_returns_metres(self):
        from src.pages.spatial import _project_lonlat_to_utm
        lon = np.array([-51.0, -51.0])
        lat = np.array([-17.8, -17.9])  # ~11 km de distância em latitude
        x_m, y_m, epsg = _project_lonlat_to_utm(lon, lat)
        # Distância no eixo Y deve ser ~11 km (1° lat ≈ 111 km, 0.1° ≈ 11 km)
        assert epsg == 32722
        dist_m = abs(y_m[0] - y_m[1])
        assert 10_500 < dist_m < 11_500, f"esperado ~11 km, obtido {dist_m}"

    def test_projection_handles_arrays(self):
        from src.pages.spatial import _project_lonlat_to_utm
        lon = np.linspace(-51.5, -50.7, 10)
        lat = np.linspace(-18.0, -17.3, 10)
        x_m, y_m, epsg = _project_lonlat_to_utm(lon, lat)
        assert x_m.shape == lon.shape
        assert y_m.shape == lat.shape
        assert epsg > 0


class TestBuildStepReport:
    def test_percent_removed(self):
        logs = [StepLog(step="test", before=100, after=80)]
        report = build_step_report(logs)
        assert report.iloc[0]["% removidas"] == pytest.approx(20.0)

    def test_zero_before_no_division_error(self):
        logs = [StepLog(step="empty", before=0, after=0)]
        report = build_step_report(logs)
        assert report.iloc[0]["% removidas"] == 0
