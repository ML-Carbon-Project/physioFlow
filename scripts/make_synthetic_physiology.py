"""Gera um dataset SINTÉTICO de fisiologia vegetal com o schema de referência.

Serve para reproduzir o fluxo completo do PhysioFlow (e as figuras do artigo)
sem expor dados reais de campo. Reproduz de propósito as características
estruturais discutidas no artigo:

* confundimento perfeito Fazenda <-> Cultura <-> Uso atual (Cramér's V = 1.0);
* grade de amostragem incompleta (maioria dos pontos sem medição);
* réplicas de clorofila e IAF;
* poucas datas distintas (bloqueia a decomposição STL);
* colunas Manejo/Textura presentes, porém vazias.

Uso:
    python scripts/make_synthetic_physiology.py -o data/sample/physiology_synthetic.csv
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

COLUMNS = [
    "ID", "Ponto", "LATITUDE", "LONGITUDE", "Fazenda", "Município", "Textura",
    "Uso atual", "Cultura", "Manejo", "Época", "Data da coleta", "A", "E", "gs",
    "Ca", "Ci", "Ci/Ca", "EUA", "A/Ci", "YII", "ETR", "Chl a", "Chl b", "IAF",
    "Chl a.1", "Chl b.1", "IAF.1", "IAF.2", "Estágio", "Peso Seco",
]

# Fazenda determina Cultura e Uso atual -> confundimento perfeito, de propósito.
FARMS = {
    "Farm A": {"Cultura": "Cana-de-açúcar", "Uso atual": "Perene", "n_points": 27},
    "Farm B": {"Cultura": "Soja", "Uso atual": "Anual", "n_points": 54},
}
DATES = ["2025-12-19", "2026-01-23", "2026-02-28"]  # 3 datas: STL fica bloqueado


def build(seed: int = 42, n_grid: int = 1661) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    measured = 0

    for farm, cfg in FARMS.items():
        for point in range(1, cfg["n_points"] + 1):
            measured += 1
            # Fotossíntese e variáveis acopladas (relações fisiológicas plausíveis)
            gs = float(np.clip(rng.normal(0.22, 0.06), 0.05, 0.5))
            ca = float(rng.normal(415, 8))
            a = float(np.clip(rng.normal(24, 6) * (0.5 + gs), 2, 45))
            e = float(np.clip(a / rng.normal(4.2, 0.7), 0.5, 12))
            ci = float(np.clip(ca * rng.normal(0.62, 0.07), 80, 380))
            chl_a = float(np.clip(rng.normal(28, 5), 8, 50))
            chl_b = float(np.clip(rng.normal(11, 3), 3, 25))
            iaf = float(np.clip(rng.normal(3.1, 0.8), 0.4, 6.5))
            yii = float(np.clip(rng.normal(0.72, 0.06), 0.3, 0.85))

            rows.append({
                "ID": f"D-{point:02d}", "Ponto": point,
                "LATITUDE": round(float(rng.uniform(-17.90, -17.40)), 4),
                "LONGITUDE": round(float(rng.uniform(-51.20, -50.80)), 4),
                "Fazenda": farm, "Município": "Municipality 1",
                "Textura": None,                      # presente, 100% vazia
                "Uso atual": cfg["Uso atual"], "Cultura": cfg["Cultura"],
                "Manejo": None,                       # presente, 100% vazia
                "Época": "Verão",
                "Data da coleta": rng.choice(DATES),
                "A": round(a, 4), "E": round(e, 4), "gs": round(gs, 4),
                "Ca": round(ca, 3), "Ci": round(ci, 3),
                "Ci/Ca": round(ci / ca, 4), "EUA": round(a / e, 4),
                "A/Ci": round(a / ci, 5),
                "YII": round(yii, 4), "ETR": round(yii * rng.normal(210, 25), 3),
                # réplicas de clorofila / IAF
                "Chl a": round(chl_a, 2), "Chl b": round(chl_b, 2), "IAF": round(iaf, 2),
                "Chl a.1": round(chl_a + rng.normal(0, 1.5), 2),
                "Chl b.1": round(chl_b + rng.normal(0, 0.8), 2),
                "IAF.1": round(iaf + rng.normal(0, 0.25), 2),
                "IAF.2": round(iaf + rng.normal(0, 0.25), 2),
                "Estágio": rng.choice(["V4", "R1", "R3"]),
                "Peso Seco": round(float(np.clip(rng.normal(85, 20), 20, 200)), 2),
            })

    # Grade incompleta: pontos planejados sem medição (o filtro de metadados remove).
    for i in range(n_grid - measured):
        rows.append({c: None for c in COLUMNS} | {
            "ID": f"D-{(i % 90) + 1:02d}", "Ponto": (i % 90) + 1,
            "LATITUDE": round(float(rng.uniform(-17.90, -17.40)), 4),
            "LONGITUDE": round(float(rng.uniform(-51.20, -50.80)), 4),
            "Fazenda": rng.choice(list(FARMS)), "Município": "Municipality 1",
        })

    return pd.DataFrame(rows, columns=COLUMNS).sample(frac=1, random_state=seed).reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", default="data/sample/physiology_synthetic.csv")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    df = build(seed=args.seed)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"{len(df)} linhas x {df.shape[1]} colunas -> {args.output}")
