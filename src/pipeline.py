from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass
class StepLog:
    step: str
    before: int
    after: int


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum())


def find_first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    cols = list(df.columns)
    exact = {c: c for c in cols}
    norm_map = {_norm(c): c for c in cols}

    for cand in candidates:
        if cand in exact:
            return cand
        cand_norm = _norm(cand)
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None


# Lista canônica de candidatos a coluna de data, em ordem de preferência.
# Inclui as variantes que historicamente apareceram nos três datasets do projeto
# (fisiologia, fluxo de solo) — qualquer página deve usar find_date_column ao
# invés de manter sua própria lista.
DATE_COLUMN_CANDIDATES: tuple[str, ...] = (
    "Data da coleta",
    "Data",
    "Date",
    "DATE",
    "data",
    "date",
    "DATE_TIME initial_value",
    "Date_Time",
    "DateTime",
    "datetime",
)


def _looks_like_datetime_object_series(series: pd.Series, sample: int = 50) -> bool:
    """True se uma série dtype=object tem pelo menos 30% de valores parseáveis como data.

    Útil quando o Excel devolve mistura de datetime.datetime, str e NaN num mesmo
    objeto (caso do dataset de fisiologia do projeto).
    """
    if series.empty:
        return False
    head = series.dropna().head(sample)
    if head.empty:
        return False
    coerced = pd.to_datetime(head, errors="coerce")
    return coerced.notna().sum() / len(head) >= 0.3


def find_date_column(df: pd.DataFrame, extra_candidates: Iterable[str] = ()) -> Optional[str]:
    """Detecta a coluna de data em ``df`` de forma robusta.

    Ordem de busca:
    1. Candidatos explícitos (extras passados pelo chamador + DATE_COLUMN_CANDIDATES).
    2. Qualquer coluna com dtype datetime64.
    3. Qualquer coluna object cuja amostra seja majoritariamente parseável como data
       (típico do Excel com mistura ``datetime.datetime`` + ``str``).

    Retorna o nome da coluna ou ``None``.
    """
    if df is None or df.empty:
        return None

    candidates = list(extra_candidates) + list(DATE_COLUMN_CANDIDATES)
    found = find_first_existing(df, candidates)
    if found is not None:
        return found

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col

    for col in df.columns:
        if df[col].dtype == object and _looks_like_datetime_object_series(df[col]):
            return col

    return None


def coerce_date_series(series: pd.Series) -> pd.Series:
    """Coerce uma série heterogênea (datetime + str + NaN) para datetime64.

    Valores impossíveis viram NaT (não levantam exceção). Garante que páginas
    consumidoras (séries temporais, filtros de data) possam usar ``.dt`` sem
    crashar quando o Excel devolveu object dtype.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce")


TEXT_EXTENSIONS = (".csv", ".txt", ".tsv")

# Mapeia a escolha de delimitador (vinda da UI) para o parametro ``sep`` do
# pandas. ``None`` aciona o sniffer automatico (engine="python").
DELIMITER_SEP = {
    "auto": None,
    "comma": ",",
    "semicolon": ";",
    "tab": "\t",
    "space": r"\s+",
}


def load_uploaded_file(
    uploaded_file,
    sheet_name: Optional[str] = None,
    delimiter: str = "auto",
) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(TEXT_EXTENSIONS):
        sep = DELIMITER_SEP.get(delimiter)
        # O engine "python" so e necessario para o sniffer automatico (sep=None)
        # e para o separador por regex de espacos (\s+). Para delimitadores
        # literais usamos o engine C (padrao), bem mais rapido em arquivos grandes.
        if sep is None or sep == r"\s+":
            df = pd.read_csv(uploaded_file, sep=sep, engine="python")
        else:
            df = pd.read_csv(uploaded_file, sep=sep)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        if sheet_name:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        else:
            df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Formato não suportado. Envie CSV, TXT/TSV ou Excel.")
    
    # Strip spaces from column names
    df = df.rename(columns=lambda c: c.strip() if isinstance(c, str) else c)
    return df


def available_excel_sheets(uploaded_file) -> list[str]:
    name = uploaded_file.name.lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls")):
        return []
    xls = pd.ExcelFile(uploaded_file)
    return list(xls.sheet_names)


def clean_fisiologia_data(
    df: pd.DataFrame,
    rep_method: str = "media",
) -> tuple[pd.DataFrame, list[StepLog]]:
    """Aplica o pipeline completo de limpeza e tratamento de réplicas de Fisiologia.

    Modos de tratamento de réplicas (rep_method):
    - "media": Calcula a média aritmética entre as repetições disponíveis.
    - "mediana": Calcula a mediana entre as repetições (robusta a outliers; com
      n=2 réplicas é matematicamente idêntica à média).
    - "desdobrar": Desdobra as réplicas 1, 2 e 3 em linhas independentes.
    - "replica_1": Utiliza apenas as colunas da réplica 1.
    - "replica_2": Utiliza apenas as colunas da réplica 2.
    - "replica_3": Utiliza apenas as colunas da réplica 3 (IAF.2).
    """
    logs: list[StepLog] = []
    before_initial = len(df)
    out = df.copy()

    # 1. Limpar espaços extras em strings de colunas categóricas
    colunas_texto = ["Cultura", "Uso atual", "Época", "Fazenda", "Município", "Estágio"]
    for col_cand in colunas_texto:
        # Encontra o nome exato da coluna
        col = find_first_existing(out, [col_cand])
        if col:
            out[col] = out[col].astype(str).str.strip()
            out[col] = out[col].replace(["nan", "NaN", "None", ""], np.nan)

    logs.append(StepLog(step="Padronização de texto (stripping de strings)", before=before_initial, after=len(out)))

    # 2. Remover linhas sem metadados essenciais (Cultura, Uso atual, Época)
    before = len(out)
    col_cultura = find_first_existing(out, ["Cultura", "Crop_Type"])
    col_uso = find_first_existing(out, ["Uso atual", "Land_Use"])
    col_epoca = find_first_existing(out, ["Época", "Season"])

    essential_cols = [c for c in [col_cultura, col_uso, col_epoca] if c is not None]
    if essential_cols:
        out = out.dropna(subset=essential_cols).copy()
    logs.append(StepLog(step="Remoção de registros sem metadados essenciais", before=before, after=len(out)))

    # 3. Remover linhas onde todas as variáveis agronômicas/fisiológicas são nulas (pontos de grade não coletados)
    before = len(out)
    agronomic_candidates = [
        "A", "E", "gs", "Ca", "Ci", "Ci/Ca", "EUA", "A/Ci", 
        "YII", "ETR", "Chl a", "Chl b", "IAF"
    ]
    resolved_vars = []
    for cand in agronomic_candidates:
        col = find_first_existing(out, [cand])
        if col:
            resolved_vars.append(col)
            # Garantir tipo numérico para cálculos
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if resolved_vars:
        # Mantém apenas as linhas onde pelo menos uma das variáveis agronômicas não é nula
        out = out[~out[resolved_vars].isnull().all(axis=1)].copy()

    logs.append(StepLog(step="Remoção de pontos de grade vazios (sem medição)", before=before, after=len(out)))

    # 4. Tratamento de réplicas de Clorofila e IAF
    before = len(out)

    # Identificar colunas de réplicas
    c_chl_a = find_first_existing(out, ["Chl a"])
    c_chl_a_1 = find_first_existing(out, ["Chl a.1"])
    c_chl_b = find_first_existing(out, ["Chl b"])
    c_chl_b_1 = find_first_existing(out, ["Chl b.1"])
    c_iaf = find_first_existing(out, ["IAF"])
    c_iaf_1 = find_first_existing(out, ["IAF.1"])
    c_iaf_2 = find_first_existing(out, ["IAF.2"])

    if rep_method == "media":
        # Calcula a média aritmética das réplicas disponíveis
        if c_chl_a or c_chl_a_1:
            out["Chl_a_media"] = out[[c for c in [c_chl_a, c_chl_a_1] if c]].mean(axis=1)
        else:
            out["Chl_a_media"] = np.nan

        if c_chl_b or c_chl_b_1:
            out["Chl_b_media"] = out[[c for c in [c_chl_b, c_chl_b_1] if c]].mean(axis=1)
        else:
            out["Chl_b_media"] = np.nan

        if c_iaf or c_iaf_1 or c_iaf_2:
            out["IAF_media"] = out[[c for c in [c_iaf, c_iaf_1, c_iaf_2] if c]].mean(axis=1)
        else:
            out["IAF_media"] = np.nan

        step_desc = "Consolidação de réplicas por média aritmética"

    elif rep_method == "mediana":
        # Mediana das réplicas: mais robusta a outliers que a média.
        # Note: com n=2 (Chl a/b), mediana == média; o ganho aparece em IAF (n=3).
        # Os nomes das colunas de saída ficam idênticos ("Chl_a_media", "IAF_media",
        # etc.) para manter compatibilidade com filtros, EDA e modelagem; apenas o
        # cálculo subjacente muda.
        if c_chl_a or c_chl_a_1:
            out["Chl_a_media"] = out[[c for c in [c_chl_a, c_chl_a_1] if c]].median(axis=1)
        else:
            out["Chl_a_media"] = np.nan

        if c_chl_b or c_chl_b_1:
            out["Chl_b_media"] = out[[c for c in [c_chl_b, c_chl_b_1] if c]].median(axis=1)
        else:
            out["Chl_b_media"] = np.nan

        if c_iaf or c_iaf_1 or c_iaf_2:
            out["IAF_media"] = out[[c for c in [c_iaf, c_iaf_1, c_iaf_2] if c]].median(axis=1)
        else:
            out["IAF_media"] = np.nan

        step_desc = "Consolidação de réplicas por mediana"

    elif rep_method == "desdobrar":
        # Cria três dataframes independentes representando cada réplica
        dfs = []
        
        # Réplica 1
        df1 = out.copy()
        df1["Replica"] = "Réplica 1"
        df1["Chl_a_media"] = df1[c_chl_a] if c_chl_a else np.nan
        df1["Chl_b_media"] = df1[c_chl_b] if c_chl_b else np.nan
        df1["IAF_media"] = df1[c_iaf] if c_iaf else np.nan
        dfs.append(df1)

        # Réplica 2
        df2 = out.copy()
        df2["Replica"] = "Réplica 2"
        df2["Chl_a_media"] = df2[c_chl_a_1] if c_chl_a_1 else np.nan
        df2["Chl_b_media"] = df2[c_chl_b_1] if c_chl_b_1 else np.nan
        df2["IAF_media"] = df2[c_iaf_1] if c_iaf_1 else np.nan
        dfs.append(df2)

        # Réplica 3 (Somente IAF possui Réplica 2 no excel)
        df3 = out.copy()
        df3["Replica"] = "Réplica 3"
        df3["Chl_a_media"] = np.nan
        df3["Chl_b_media"] = np.nan
        df3["IAF_media"] = df3[c_iaf_2] if c_iaf_2 else np.nan
        dfs.append(df3)

        # Concatenar todos
        combined = pd.concat(dfs, ignore_index=True)
        # Remover linhas onde todas as variáveis desdobradas são nulas (ex: réplicas 2 ou 3 que não existem para um ponto)
        out = combined.dropna(subset=["Chl_a_media", "Chl_b_media", "IAF_media"], how="all").copy()
        step_desc = "Desdobramento de réplicas em registros separados"

    elif rep_method == "replica_1":
        out["Chl_a_media"] = out[c_chl_a] if c_chl_a else np.nan
        out["Chl_b_media"] = out[c_chl_b] if c_chl_b else np.nan
        out["IAF_media"] = out[c_iaf] if c_iaf else np.nan
        step_desc = "Seleção exclusiva da Réplica 1"

    elif rep_method == "replica_2":
        out["Chl_a_media"] = out[c_chl_a_1] if c_chl_a_1 else np.nan
        out["Chl_b_media"] = out[c_chl_b_1] if c_chl_b_1 else np.nan
        out["IAF_media"] = out[c_iaf_1] if c_iaf_1 else np.nan
        step_desc = "Seleção exclusiva da Réplica 2"

    elif rep_method == "replica_3":
        out["Chl_a_media"] = np.nan
        out["Chl_b_media"] = np.nan
        out["IAF_media"] = out[c_iaf_2] if c_iaf_2 else np.nan
        step_desc = "Seleção exclusiva da Réplica 3 (IAF)"

    logs.append(StepLog(step=step_desc, before=before, after=len(out)))

    return out, logs


def build_step_report(logs: list[StepLog]) -> pd.DataFrame:
    rows = []
    for item in logs:
        removed = item.before - item.after
        rows.append(
            {
                "Etapa": item.step,
                "Linhas antes": item.before,
                "Linhas depois": item.after,
                "Removidas": removed,
                "% removidas": (removed / item.before * 100) if item.before else 0,
            }
        )
    return pd.DataFrame(rows)
