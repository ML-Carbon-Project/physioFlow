"""Gera uma cópia des-identificada da campanha de campo, para as figuras do artigo.

A campanha de Rio Verde não pode ser publicada, mas as figuras do manuscrito
derivam dela — e o artigo afirma que são *de-identified*. Este script produz a
cópia que sustenta essa afirmação: mantém **todas as medições intactas** (para
que os números do texto continuem valendo) e remove o que identifica as
propriedades.

O que muda:

* ``Fazenda`` — nomes reais viram ``Farm A``…``Farm E``. O mapeamento é fixo:
  a fazenda de cana é ``Farm A`` e a de soja é ``Farm B``, como na Seção 5.1.
* ``Latitude``/``Longitude`` — substituídas por coordenadas sintéticas. Quatro
  casas decimais localizam a propriedade; com duas fazendas na região, o nome
  mascarado não protegeria nada.

O que **não** muda: nenhuma variável medida, nem as datas — a janela de coleta
já está escrita no artigo.

O arquivo de saída fica fora do repositório por padrão: é derivado de dados que
não podem ser distribuídos.

    .venv/bin/python scripts/deidentify_field_dataset.py --out /caminho/campo_deid.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIELD = ROOT / "data" / "sample" / "0_Dados_Fisiologia_RIO VERDE.xlsx"
SYNTHETIC = ROOT / "data" / "sample" / "physiology_synthetic.csv"

# Âncoras da Seção 3.1: "Farm A ≡ sugarcane, 27 records; Farm B ≡ soybean, 54".
# Deliberadamente expressas por *cultura*, não por nome de fazenda: este script é
# versionado, e uma tabela com os nomes reais em código desfaria a
# des-identificação das figuras no momento em que o repositório for público.
CROP_ANCHORS = (("cana", "Farm A"), ("soja", "Farm B"))


def build_farm_map(df: pd.DataFrame, farm_col: str) -> dict[str, str]:
    """Mapa nome real → rótulo neutro, derivado dos dados.

    As duas fazendas do estudo são identificadas pela cultura que cada uma
    cultiva; as demais recebem letras na ordem em que aparecem no arquivo.
    """
    crop_col = next((c for c in df.columns if str(c).strip() == "Cultura"), None)
    mapping: dict[str, str] = {}

    if crop_col is not None:
        for token, label in CROP_ANCHORS:
            match = df[df[crop_col].astype(str).str.lower().str.startswith(token)]
            farms = {str(v) for v in match[farm_col].dropna().unique()}
            if len(farms) != 1:
                raise SystemExit(
                    f"cultura {token!r} não identifica uma única fazenda: {sorted(farms)}"
                )
            mapping[farms.pop()] = label

    taken = set(mapping.values())
    letters = [f"Farm {chr(c)}" for c in range(ord("A"), ord("Z") + 1)]
    for name in dict.fromkeys(str(v) for v in df[farm_col].dropna()):
        if name in mapping:
            continue
        label = next(x for x in letters if x not in taken)
        mapping[name] = label
        taken.add(label)
    return mapping


def normalize_dates(out: pd.DataFrame) -> int:
    """Uniformiza ``Data da coleta`` para ISO; devolve quantas linhas mudaram.

    Duas linhas da planilha vêm como texto em M/D/YYYY ("12/19/2025") enquanto o
    resto é datetime. ``coerce_date_series`` não converte essas duas, elas viram
    NaT e o filtro de intervalo de datas do app as descarta — o que derruba o
    n da modelagem de 71 para 69 e desalinha a figura do texto do artigo. As
    datas em si já existem no conjunto; só a grafia é inconsistente.
    """
    col = next((c for c in out.columns if str(c).strip() == "Data da coleta"), None)
    if col is None:
        return 0

    parsed = pd.to_datetime(out[col], errors="coerce")
    pending = parsed.isna() & out[col].notna()
    if pending.any():
        parsed.loc[pending] = pd.to_datetime(
            out.loc[pending, col], format="%m/%d/%Y", errors="coerce"
        )
    changed = int((parsed.notna() & (out[col].astype(str) != parsed.dt.strftime("%Y-%m-%d"))).sum())
    out[col] = parsed.dt.strftime("%Y-%m-%d")
    return changed


def deidentify(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    out = df.copy()

    farm_col = next(c for c in out.columns if str(c).strip() == "Fazenda")
    farm_map = build_farm_map(out, farm_col)
    out[farm_col] = out[farm_col].map(lambda v: farm_map.get(str(v), v) if pd.notna(v) else v)

    lat_col = next((c for c in out.columns if str(c).strip().lower() == "latitude"), None)
    lon_col = next((c for c in out.columns if str(c).strip().lower() == "longitude"), None)
    if lat_col and lon_col:
        synth = pd.read_csv(SYNTHETIC)
        # Um par sintético por par real distinto: o mesmo ponto amostral continua
        # tendo a mesma coordenada. Substituir linha a linha faria um mesmo ponto
        # aparecer em lugares diferentes, o que numa figura parece erro de dados.
        # Cada ponto amostral é realocado para uma coordenada sintética, mas o
        # desvio interno de cada leitura em relação ao seu ponto é preservado.
        # Assim o jitter de GPS continua com a cara do original — remapear leitura
        # a leitura espalharia o mesmo ponto por dezenas de quilômetros.
        id_col = next((c for c in out.columns if str(c).strip() == "ID"), None)
        pt_col = next((c for c in out.columns if str(c).strip() == "Ponto"), None)
        if id_col and pt_col:
            keys = list(zip(out[id_col].astype(str), out[pt_col].astype(str)))
        else:
            keys = [(str(lat), str(lon)) for lat, lon in zip(out[lat_col], out[lon_col])]

        synth_pairs = list(dict.fromkeys(zip(synth["LATITUDE"], synth["LONGITUDE"])))
        distinct = list(dict.fromkeys(keys))
        if len(synth_pairs) < len(distinct):
            raise SystemExit(
                f"coordenadas sintéticas insuficientes: {len(synth_pairs)} < {len(distinct)}"
            )
        anchor_synth = dict(zip(distinct, synth_pairs))

        anchor_real: dict[tuple[str, str], tuple[float, float]] = {}
        for key, lat, lon in zip(keys, out[lat_col], out[lon_col]):
            anchor_real.setdefault(key, (lat, lon))

        out[lat_col] = [
            anchor_synth[k][0] + (lat - anchor_real[k][0])
            for k, lat in zip(keys, out[lat_col])
        ]
        out[lon_col] = [
            anchor_synth[k][1] + (lon - anchor_real[k][1])
            for k, lon in zip(keys, out[lon_col])
        ]
        out[lat_col] = out[lat_col].round(6)
        out[lon_col] = out[lon_col].round(6)

    return out, farm_map


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="caminho do CSV de saída")
    args = ap.parse_args()

    if not FIELD.exists():
        print(f"base de campo não encontrada: {FIELD}", file=sys.stderr)
        return 1

    df = pd.read_excel(FIELD)
    out, farm_map = deidentify(df)
    fixed = normalize_dates(out)

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Sem BOM: com utf-8-sig o loader do app lê a 1ª coluna como "﻿ID" e o
    # validador de schema deixa de reconhecê-la.
    out.to_csv(dest, index=False, encoding="utf-8")

    print(f"escrito: {dest}  ({out.shape[0]} linhas × {out.shape[1]} colunas)")
    print(f"datas normalizadas para ISO: {fixed} linhas")
    print("mapa de fazendas:")
    for real, label in sorted(farm_map.items(), key=lambda kv: kv[1]):
        print(f"  {real:22} → {label}")

    leaked = [c for c in out.columns if out[c].astype(str).isin(farm_map).any()]
    print("colunas com nome real remanescente:", leaked or "nenhuma")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
