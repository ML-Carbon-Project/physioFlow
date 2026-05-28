from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe
from src.pipeline import clean_fisiologia_data, build_step_report
from src.state import get_processed_dataframe, get_report_dataframe, set_processed_dataset
from src.i18n import t


def render():
    st.subheader(t("pipeline.title"))

    df_raw = ensure_raw_dataframe(t("pipeline.warn_no_data"))
    if df_raw is None:
        return

    # Recupera o método de réplica atual do sidebar/estado
    rep_method = st.session_state.get("rep_method", "media")
    
    # Exibe informações sobre as etapas automatizadas de Fisiologia
    st.markdown(f"### {t('pipeline.section_info', default='Pipeline de Limpeza Automatizada de Fisiologia')}")
    st.info(
        "Este pipeline executa as seguintes etapas estruturadas:\n"
        "1. **Padronização:** Limpeza de espaços extras em colunas de texto.\n"
        "2. **Filtro de Metadados:** Remoção de linhas sem informações essenciais (Cultura, Uso atual, Época).\n"
        "3. **Filtro de Grade Vazia:** Remoção de linhas da grade amostral que não possuem medições reais.\n"
        "4. **Tratamento de Réplicas:** Consolidação ou desdobramento de Clorofila e IAF conforme o modo selecionado."
    )

    # Exibe a opção de tratamento de réplicas também na página para conveniência
    method_options = {
        "media": t("sidebar.rep.media", default="Média das Réplicas") + " (" + t("pipeline.rep_grouped", default="Agrupado") + ")",
        "mediana": t("sidebar.rep.mediana", default="Mediana das Réplicas") + " (" + t("pipeline.rep_grouped", default="Agrupado") + ")",
        "desdobrar": t("sidebar.rep.desdobrar", default="Desdobrar em Linhas") + " (" + t("pipeline.rep_expanded", default="Expandido") + ")",
        "replica_1": t("sidebar.rep.replica_1", default="Réplica 1 Apenas"),
        "replica_2": t("sidebar.rep.replica_2", default="Réplica 2 Apenas"),
        "replica_3": t("sidebar.rep.replica_3", default="Réplica 3 Apenas (IAF)"),
    }

    method_keys = list(method_options.keys())
    method_idx = method_keys.index(rep_method) if rep_method in method_keys else 0
    selected_method = st.selectbox(
        t("pipeline.rep_method_label", default="Alterar Tratamento de Réplicas:"),
        options=method_keys,
        index=method_idx,
        format_func=lambda x: method_options[x],
        key="pipeline_rep_method"
    )
    if selected_method == "mediana":
        st.caption(":information_source: " + t("sidebar.rep.mediana_note"))

    # Se mudar na página, atualiza e re-executa
    if selected_method != rep_method:
        st.session_state["rep_method"] = selected_method
        df_processed, logs = clean_fisiologia_data(df_raw, rep_method=selected_method)
        set_processed_dataset(df_processed, build_step_report(logs))
        st.rerun()

    # Executa o pipeline se ainda não foi processado
    df_processed = get_processed_dataframe()
    if df_processed is None or df_processed.equals(df_raw):
        df_processed, logs = clean_fisiologia_data(df_raw, rep_method=selected_method)
        set_processed_dataset(df_processed, build_step_report(logs))
        st.rerun()

    report = get_report_dataframe()

    c1, c2 = st.columns(2)
    c1.metric(t("pipeline.metric.original"), len(df_raw))
    c2.metric(t("pipeline.metric.processed"), len(df_processed))

    if len(df_raw) > 0:
        overall_removed_pct = (1 - len(df_processed) / len(df_raw)) * 100
        if overall_removed_pct >= 50:
            st.warning(
                t(
                    "pipeline.warn_heavy_discard",
                    pct=f"{overall_removed_pct:.1f}",
                    before=len(df_raw),
                    after=len(df_processed),
                )
            )

    st.markdown(f"#### {t('pipeline.report_title')}")
    if not report.empty:
        heavy_steps = report[report["% removidas"] >= 50]
        if not heavy_steps.empty:
            for _, step in heavy_steps.iterrows():
                st.warning(
                    t(
                        "pipeline.warn_step_discard",
                        step=step["Etapa"],
                        pct=f"{step['% removidas']:.1f}",
                        before=int(step["Linhas antes"]),
                        after=int(step["Linhas depois"]),
                    )
                )
        st.dataframe(report, use_container_width=True)
    else:
        st.info(t("pipeline.report_empty"))

    st.markdown(f"#### {t('pipeline.preview_title')}")
    st.dataframe(df_processed.head(20), use_container_width=True)

    st.markdown(f"#### {t('pipeline.export_title')}")
    col_csv, col_xlsx = st.columns(2)
    csv_data = df_processed.to_csv(index=False).encode("utf-8-sig")
    col_csv.download_button(
        f"⬇️ {t('pipeline.export_csv')}",
        data=csv_data,
        file_name="dataset_fisiologia_limpo.csv",
        mime="text/csv",
        use_container_width=True,
    )
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df_processed.to_excel(writer, index=False, sheet_name="Fisiologia_Limpo")
    col_xlsx.download_button(
        f"⬇️ {t('pipeline.export_xlsx')}",
        data=xlsx_buffer.getvalue(),
        file_name="dataset_fisiologia_limpo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
