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


class TestBuildStepReport:
    def test_percent_removed(self):
        logs = [StepLog(step="test", before=100, after=80)]
        report = build_step_report(logs)
        assert report.iloc[0]["% removidas"] == pytest.approx(20.0)

    def test_zero_before_no_division_error(self):
        logs = [StepLog(step="empty", before=0, after=0)]
        report = build_step_report(logs)
        assert report.iloc[0]["% removidas"] == 0
