from __future__ import annotations

import pandas as pd
import streamlit as st

from src.i18n import t
from src.pipeline import (
    clean_fisiologia_data,
    coerce_date_series,
    find_date_column,
    find_first_existing,
)
from src.profile import is_physiology
from src.state import get_raw_dataframe, set_processed_dataset


def render_page_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Renderiza os filtros dinâmicos no topo da página (dentro de um expander)
    e retorna o dataframe filtrado.
    """
    df_raw = get_raw_dataframe()
    if df_raw is None or df is None or df.empty:
        return df

    # Trabalha sobre o dataframe processado ativo
    filtered_df = df.copy()

    st.markdown(f"#### ⚙️ {t('filters.title', default='Painel de Configurações e Filtros')}")
    st.markdown(t("filters.description", default="Utilize os filtros abaixo para restringir a análise a culturas, locais ou períodos específicos.\nAs alterações serão aplicadas de forma reativa em todos os gráficos e modelos."))

    with st.expander("🔍 " + t("sidebar.filters_title", default="Filtros Globais"), expanded=True):
        # Primeira linha de filtros. O tratamento de réplicas consolida réplicas
        # de clorofila/IAF — conceito específico de fisiologia. No perfil genérico
        # ele é omitido (a agregação de repetições fica na página Pipeline).
        if is_physiology(df_raw):
            c1, c2, c3 = st.columns(3)
            with c1:
                method_options = {
                    "media": t("sidebar.rep.media", default="Média das Réplicas"),
                    "mediana": t("sidebar.rep.mediana", default="Mediana das Réplicas"),
                    "desdobrar": t("sidebar.rep.desdobrar", default="Desdobrar em Linhas"),
                    "replica_1": t("sidebar.rep.replica_1", default="Réplica 1 Apenas"),
                    "replica_2": t("sidebar.rep.replica_2", default="Réplica 2 Apenas"),
                    "replica_3": t("sidebar.rep.replica_3", default="Réplica 3 Apenas (IAF)"),
                }
                current_method = st.session_state.get("rep_method", "media")
                method_keys = list(method_options.keys())
                method_idx = method_keys.index(current_method) if current_method in method_keys else 0
                selected_method = st.selectbox(
                    t("sidebar.rep_method_label", default="Tratamento de Réplicas"),
                    options=method_keys,
                    index=method_idx,
                    format_func=lambda x: method_options[x],
                    key="filter_rep_method"
                )
                if selected_method == "mediana":
                    st.caption(":information_source: " + t("sidebar.rep.mediana_note"))
                if selected_method != current_method:
                    st.session_state["rep_method"] = selected_method
                    df_processed, logs = clean_fisiologia_data(df_raw, rep_method=selected_method)
                    set_processed_dataset(df_processed, pd.DataFrame())
                    st.rerun()
        else:
            c2, c3 = st.columns(2)

        with c2:
            # 2. Filtro de Cultura
            col_cultura = find_first_existing(filtered_df, ["Cultura", "Crop_Type"])
            selected_culturas = []
            if col_cultura:
                culturas = sorted(filtered_df[col_cultura].dropna().unique())
                selected_culturas = st.multiselect(
                    t("sidebar.filter_crop", default="Cultura"),
                    options=culturas,
                    default=culturas,
                    key="filter_culturas"
                )
                if selected_culturas:
                    filtered_df = filtered_df[filtered_df[col_cultura].isin(selected_culturas)]

        with c3:
            # 3. Filtro de Município
            col_municipio = find_first_existing(filtered_df, ["Município", "MUNICIPIO"])
            selected_mun = "Todos"
            if col_municipio:
                municipios = ["Todos"] + sorted(filtered_df[col_municipio].dropna().unique())
                selected_mun = st.selectbox(
                    t("sidebar.filter_mun", default="Município"),
                    options=municipios,
                    key="filter_municipio"
                )
                if selected_mun != "Todos":
                    filtered_df = filtered_df[filtered_df[col_municipio] == selected_mun]

        # Segunda linha de filtros (3 colunas): Fazenda, Época, Intervalo de Datas
        c4, c5, c6 = st.columns(3)

        with c4:
            # 4. Filtro de Fazenda
            col_fazenda = find_first_existing(filtered_df, ["Fazenda", "FAZENDA", "Coll_Cluster"])
            if col_fazenda:
                # Se filtrou município, limita as fazendas pertencentes àquele município
                fazendas_disponiveis = sorted(filtered_df[col_fazenda].dropna().unique())
                fazenda_options = ["Todas"] + fazendas_disponiveis
                selected_faz = st.selectbox(
                    t("sidebar.filter_faz", default="Fazenda"),
                    options=fazenda_options,
                    key="filter_fazenda"
                )
                if selected_faz != "Todas":
                    filtered_df = filtered_df[filtered_df[col_fazenda] == selected_faz]

        with c5:
            # 5. Filtro de Época
            col_epoca = find_first_existing(filtered_df, ["Época", "Season", "EPOCA"])
            if col_epoca:
                epocas = sorted(filtered_df[col_epoca].dropna().unique())
                selected_epocas = st.multiselect(
                    t("sidebar.filter_season", default="Época / Estação"),
                    options=epocas,
                    default=epocas,
                    key="filter_epocas"
                )
                if selected_epocas:
                    filtered_df = filtered_df[filtered_df[col_epoca].isin(selected_epocas)]

        with c6:
            # 6. Filtro de Período (Data de Coleta)
            col_data = find_date_column(filtered_df)
            if col_data:
                try:
                    filtered_df[col_data] = coerce_date_series(filtered_df[col_data])
                    # Após a coerção, NaTs aparecem onde havia strings inválidas;
                    # ignoramos esses valores para definir a faixa selecionável.
                    valid_dates = filtered_df[col_data].dropna()
                    if valid_dates.empty:
                        raise ValueError("nenhuma data válida")
                    min_date = valid_dates.min().date()
                    max_date = valid_dates.max().date()
                    
                    if min_date < max_date:
                        selected_dates = st.date_input(
                            t("sidebar.filter_date_range", default="Intervalo de Datas"),
                            value=(min_date, max_date),
                            min_value=min_date,
                            max_value=max_date,
                            key="filter_dates"
                        )
                        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                            start_dt = pd.to_datetime(selected_dates[0])
                            end_dt = pd.to_datetime(selected_dates[1])
                            filtered_df = filtered_df[filtered_df[col_data].between(start_dt, end_dt)]
                except Exception:
                    pass

        # Exibe métrica do número de pontos após filtros
        st.markdown(
            f"**{t('sidebar.metric_filtered_points', default='Pontos Filtrados')}:** "
            f"`{len(filtered_df)}` de `{len(df)}` registros"
        )

    return filtered_df
