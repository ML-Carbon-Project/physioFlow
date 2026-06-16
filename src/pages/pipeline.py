from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from src.components.dataset_controls import ensure_raw_dataframe
from src.pipeline import aggregate_by_group, clean_fisiologia_data, build_step_report, count_repetitions
from src.profile import is_physiology
from src.state import get_processed_dataframe, get_report_dataframe, set_processed_dataset
from src.i18n import t, translate_step


def _render_generic_pipeline(df_raw: pd.DataFrame) -> None:
    """Pipeline para datasets genéricos: passa-direto, com agregação opcional de
    repetições (média/mediana) — sem cleaning específico de fisiologia."""
    st.info(t("pipeline.generic.intro"))
    work = df_raw.copy()

    cols = list(work.columns)
    agg_on = st.checkbox(t("pipeline.generic.aggregate_toggle"), value=False,
                         help=t("pipeline.generic.aggregate_help"), key="pipe_gen_agg")
    group_cols: list[str] = []
    method = "media"
    if agg_on:
        group_cols = st.multiselect(t("pipeline.generic.group_cols"), options=cols, key="pipe_gen_groups")
        method = st.radio(
            t("pipeline.generic.agg_method"), options=["media", "mediana"],
            format_func=lambda m: t("sidebar.rep.media") if m == "media" else t("sidebar.rep.mediana"),
            horizontal=True, key="pipe_gen_method",
        )
        if group_cols:
            reps = count_repetitions(work, group_cols)
            if reps > 0:
                st.caption(t("pipeline.generic.reps_found", n=reps))
                work = aggregate_by_group(work, group_cols, method)
            else:
                st.caption(t("pipeline.generic.reps_none"))

    set_processed_dataset(work, pd.DataFrame())

    c1, c2 = st.columns(2)
    c1.metric(t("pipeline.metric.original"), len(df_raw))
    c2.metric(t("pipeline.metric.processed"), len(work))

    st.markdown(f"#### {t('pipeline.preview_title')}")
    st.dataframe(work.head(20), use_container_width=True)

    st.markdown(f"#### {t('pipeline.export_title')}")
    col_csv, col_xlsx = st.columns(2)
    col_csv.download_button(
        f"⬇️ {t('pipeline.export_csv')}",
        data=work.to_csv(index=False).encode("utf-8-sig"),
        file_name="dataset_processado.csv", mime="text/csv", use_container_width=True,
    )
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        work.to_excel(writer, index=False, sheet_name="Dados")
    col_xlsx.download_button(
        f"⬇️ {t('pipeline.export_xlsx')}",
        data=xlsx_buffer.getvalue(), file_name="dataset_processado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def render():
    st.subheader(t("pipeline.title"))

    df_raw = ensure_raw_dataframe(t("pipeline.warn_no_data"))
    if df_raw is None:
        return

    # Perfil genérico: pula todo o cleaning de fisiologia (filtro de metadados,
    # consolidação de réplicas Chl/IAF) e oferece agregação genérica opcional.
    if not is_physiology(df_raw):
        _render_generic_pipeline(df_raw)
        return

    # Recupera o método de réplica atual do sidebar/estado
    rep_method = st.session_state.get("rep_method", "media")
    
    # Exibe informações sobre as etapas automatizadas de Fisiologia
    st.markdown(f"### {t('pipeline.section_info')}")
    st.info(
        "\n".join(
            [
                t("pipeline.info_intro"),
                "1. " + t("pipeline.info_step_1"),
                "2. " + t("pipeline.info_step_2"),
                "3. " + t("pipeline.info_step_3"),
                "4. " + t("pipeline.info_step_4"),
            ]
        )
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
                        # translate_step traduz o nome da etapa preservando os
                        # nomes em pt-BR como fonte canônica nos testes.
                        step=translate_step(step["Etapa"]),
                        pct=f"{step['% removidas']:.1f}",
                        before=int(step["Linhas antes"]),
                        after=int(step["Linhas depois"]),
                    )
                )
        # Cria uma cópia para exibição com nomes de etapa e cabeçalhos traduzidos.
        # O DataFrame original em `report` mantém os nomes em pt-BR (fonte de
        # verdade) — só a renderização visual é localizada.
        display_report = report.copy()
        display_report["Etapa"] = display_report["Etapa"].map(translate_step)
        display_report = display_report.rename(
            columns={
                "Etapa": t("pipeline.report.col.step"),
                "Linhas antes": t("pipeline.report.col.rows_before"),
                "Linhas depois": t("pipeline.report.col.rows_after"),
                "Removidas": t("pipeline.report.col.removed"),
                "% removidas": t("pipeline.report.col.percent_removed"),
            }
        )
        st.dataframe(display_report, use_container_width=True)
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
