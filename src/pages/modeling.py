from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from src.components.charts import show_fig
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold, cross_val_score, train_test_split

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.config.settings import MODEL_DEFAULT_FEATURES
from src.i18n import t
from src.ml import (
    CLASSIFIER_REGISTRY,
    DEFAULT_CLASSIFIER_KEYS,
    DEFAULT_MODEL_KEYS,
    MODEL_REGISTRY,
    build_model_pipeline,
    extract_feature_importance,
)

# Acima deste limite de categorias uma coluna numerica nao e oferecida como
# alvo de classificacao (provavelmente e continua ou um identificador).
_MAX_TARGET_CLASSES = 20


def render():
    st.subheader(t("modeling.title"))

    df_raw = ensure_raw_dataframe(t("modeling.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("model_use_processed")
    if df is None:
        df = df_raw

    # Aplica os filtros na página
    from src.components.filters import render_page_filters
    df = render_page_filters(df)

    task = st.radio(
        t("modeling.task"),
        options=["regression", "classification"],
        format_func=lambda key: t(f"modeling.task.{key}"),
        horizontal=True,
        key="modeling_task",
    )
    if task == "classification":
        _render_classification(df)
        return

    numeric_cols = list(df.select_dtypes(include="number").columns)
    all_columns = list(df.columns)

    if len(numeric_cols) < 2:
        st.warning(t("modeling.warn_min_numeric"))
        return

    # "A" (fotossíntese) só é um default válido se for de fato numérica — em
    # datasets genéricos pode existir uma coluna categórica chamada "A".
    default_target = "A" if "A" in numeric_cols else numeric_cols[0]
    target = st.selectbox(t("modeling.target"), options=numeric_cols, index=numeric_cols.index(default_target))

    default_features = [column for column in MODEL_DEFAULT_FEATURES if column in all_columns and column != target]
    if not default_features:
        # Perfil genérico (sem features de fisiologia): usa as numéricas restantes.
        default_features = [column for column in numeric_cols if column != target][:8]
    features = st.multiselect(t("modeling.features"), options=[column for column in all_columns if column != target], default=default_features)

    if not features:
        st.warning(t("modeling.warn_min_feature"))
        return

    selected_models = st.multiselect(
        t("modeling.models"),
        options=list(MODEL_REGISTRY.keys()),
        default=DEFAULT_MODEL_KEYS,
        format_func=lambda model_key: t(MODEL_REGISTRY[model_key].label_key),
    )
    if not selected_models:
        st.warning(t("modeling.warn_min_model"))
        return

    c1, c2 = st.columns(2)
    test_size = c1.slider(t("modeling.holdout"), 0.10, 0.40, 0.30, 0.05)
    cv_folds = c2.slider(t("modeling.cv_folds"), 3, 10, 5, 1)

    # Estratégia de validação cruzada: KFold ingênuo trata cada réplica como
    # independente — o que infla R² holdout/CV quando há pseudoreplicação
    # (várias medições no mesmo sítio). GroupKFold permite agrupar por
    # Fazenda + Ponto (ou outra coluna escolhida pelo usuário) para que todas
    # as réplicas de um sítio fiquem juntas no mesmo fold.
    cv_strategy = st.radio(
        t("modeling.cv_strategy"),
        options=["random", "group"],
        format_func=lambda key: t(f"modeling.cv_strategy.{key}"),
        horizontal=True,
        key="modeling_cv_strategy",
        help=t("modeling.cv_strategy_help"),
    )

    group_col_candidates: list[str] = []
    group_col_choice: str | None = None
    if cv_strategy == "group":
        group_col_candidates = [
            c for c in df.columns
            if not pd.api.types.is_numeric_dtype(df[c]) and 2 <= df[c].nunique(dropna=True)
        ]
        # Adiciona uma opção sintética combinando Fazenda+Ponto quando ambas existem
        composite_label = None
        if "Fazenda" in df.columns and "Ponto" in df.columns:
            composite_label = "Fazenda + Ponto"
            group_col_candidates = [composite_label] + group_col_candidates
        if not group_col_candidates:
            st.warning(t("modeling.warn_no_group_col"))
            cv_strategy = "random"
        else:
            default_group = composite_label or next(
                (c for c in ("Fazenda", "ID", "LABEL") if c in group_col_candidates),
                group_col_candidates[0],
            )
            group_col_choice = st.selectbox(
                t("modeling.cv_group_col"),
                options=group_col_candidates,
                index=group_col_candidates.index(default_group),
                key="modeling_cv_group_col",
            )

    df_model = df.dropna(subset=features + [target]).copy()
    if len(df_model) < 30:
        st.warning(t("modeling.warn_too_few_rows"))
        return

    X = df_model[features]
    y = df_model[target]

    numeric_features = [
        column for column in features
        if pd.api.types.is_numeric_dtype(df_model[column]) and not pd.api.types.is_bool_dtype(df_model[column])
    ]
    categorical_features = [column for column in features if column not in numeric_features]

    # Resolve a coluna de agrupamento (pode ser sintética "Fazenda + Ponto").
    groups = None
    if cv_strategy == "group" and group_col_choice is not None:
        if group_col_choice == "Fazenda + Ponto":
            groups = (
                df_model["Fazenda"].astype(str) + "__" + df_model["Ponto"].astype(str)
            )
        else:
            groups = df_model[group_col_choice].astype(str)

        n_groups = int(groups.nunique())
        if n_groups < cv_folds:
            st.warning(
                t(
                    "modeling.warn_groups_lt_folds",
                    n_groups=n_groups,
                    folds=cv_folds,
                    new_folds=max(2, n_groups),
                )
            )
            cv_folds = max(2, n_groups)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    if cv_strategy == "group":
        cv = GroupKFold(n_splits=cv_folds)
    else:
        cv = KFold(n_splits=cv_folds, shuffle=True, random_state=42)

    results = []
    model_details: dict[str, pd.DataFrame] = {}
    holdout_predictions: dict[str, pd.DataFrame] = {}
    failures = []

    with st.spinner(t("modeling.training")):
        for model_key in selected_models:
            model_def = MODEL_REGISTRY[model_key]
            pipeline = build_model_pipeline(model_key, categorical_features, numeric_features)

            try:
                pipeline.fit(X_train, y_train)
                predictions = pipeline.predict(X_test)
                if groups is not None:
                    cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="r2", groups=groups)
                else:
                    cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="r2")
            except Exception as exc:
                failures.append(t("modeling.warn_train_failed", error=f"{t(model_def.label_key)}: {exc}"))
                continue

            results.append(
                {
                    t("modeling.col.model"): t(model_def.label_key),
                    t("modeling.col.r2_holdout"): r2_score(y_test, predictions),
                    t("modeling.col.mae_holdout"): mean_absolute_error(y_test, predictions),
                    t("modeling.col.rmse_holdout"): mean_squared_error(y_test, predictions) ** 0.5,
                    t("modeling.col.cv_mean"): cv_scores.mean(),
                    t("modeling.col.cv_std"): cv_scores.std(),
                }
            )

            holdout_predictions[t(model_def.label_key)] = pd.DataFrame({"observed": y_test.to_numpy(), "predicted": predictions})

            feature_importance = extract_feature_importance(pipeline)
            if feature_importance is not None and not feature_importance.empty:
                model_details[t(model_def.label_key)] = feature_importance.head(15)

    for failure in failures:
        st.warning(failure)

    if not results:
        st.error(t("modeling.error_no_models"))
        return

    results_df = pd.DataFrame(results).sort_values(t("modeling.col.cv_mean"), ascending=False)
    st.dataframe(results_df, use_container_width=True)

    best_row = results_df.iloc[0]
    c1, c2 = st.columns(2)
    c1.metric(t("modeling.metric.best_cv"), f"{best_row[t('modeling.col.cv_mean')]:.4f}")
    c1.caption(best_row[t("modeling.col.model")])
    c2.metric(t("modeling.metric.best_holdout"), f"{best_row[t('modeling.col.r2_holdout')]:.4f}")
    c2.caption(best_row[t("modeling.col.model")])

    # ---------------- Predicted vs. observed ----------------
    if holdout_predictions:
        st.markdown(f"#### {t('modeling.predicted_title')}")
        models_for_pred = list(holdout_predictions.keys())
        chosen = st.selectbox(t("modeling.predicted_select"), options=models_for_pred, key="modeling_pred_select")
        pred_df = holdout_predictions[chosen]

        fig_pred, ax_pred = plt.subplots(figsize=(6, 6))
        ax_pred.scatter(pred_df["observed"], pred_df["predicted"], alpha=0.6, s=24, color="#0f766e")
        lim_min = min(pred_df["observed"].min(), pred_df["predicted"].min())
        lim_max = max(pred_df["observed"].max(), pred_df["predicted"].max())
        ax_pred.plot([lim_min, lim_max], [lim_min, lim_max], linestyle="--", color="#b91c1c", linewidth=1.5)
        ax_pred.set_xlabel(t("modeling.chart.observed"))
        ax_pred.set_ylabel(t("modeling.chart.predicted"))
        ax_pred.set_title(chosen)
        show_fig(fig_pred)
        plt.close(fig_pred)
        st.caption(t("modeling.predicted_caption"))

    # ---------------- Feature importance bar chart ----------------
    if model_details:
        st.markdown(f"#### {t('modeling.importance_title')}")
        detail_model = st.selectbox(t("modeling.importance_select"), options=list(model_details.keys()))
        importance_df = model_details[detail_model]
        st.dataframe(importance_df, use_container_width=True)

        fig_imp, ax_imp = plt.subplots(figsize=(8, max(3, 0.35 * len(importance_df))))
        sns.barplot(
            data=importance_df,
            x="importance",
            y="feature",
            hue="feature",
            legend=False,
            palette="crest",
            ax=ax_imp,
        )
        ax_imp.set_title(t("modeling.importance_chart_title", n=len(importance_df)))
        ax_imp.set_xlabel(t("modeling.chart.importance"))
        ax_imp.set_ylabel("")
        show_fig(fig_imp)
        plt.close(fig_imp)


def _classification_target_candidates(df: pd.DataFrame) -> list[str]:
    """Colunas elegíveis como alvo de classificação: categóricas ou numéricas de
    baixa cardinalidade (2 a _MAX_TARGET_CLASSES níveis)."""
    candidates = []
    for col in df.columns:
        n_unique = df[col].nunique(dropna=True)
        if n_unique < 2:
            continue
        if pd.api.types.is_numeric_dtype(df[col]) and n_unique > _MAX_TARGET_CLASSES:
            continue
        candidates.append(col)
    return candidates


@st.cache_data(show_spinner=False)
def _train_classifiers(data, features, target, model_keys, scaler, cv_kind, cv_folds, test_size):
    """Treina e avalia os classificadores selecionados (função pura, cacheável).

    Não chama ``st.*`` nem ``t(...)`` — devolve estrutura independente de idioma,
    chaveada por ``model_key``, para que a tradução/plotagem fiquem na renderização
    e o cache permaneça válido ao trocar de idioma.
    """
    features = list(features)
    model_keys = list(model_keys)
    X = data[features]
    y = data[target].astype(str)

    class_counts = y.value_counts()
    min_class = int(class_counts.min())
    eff_folds = cv_folds
    fold_warning = None
    if cv_kind == "stratified":
        if min_class < cv_folds:
            eff_folds = max(2, min_class)
            fold_warning = (min_class, cv_folds, eff_folds)
        cv = StratifiedKFold(n_splits=eff_folds, shuffle=True, random_state=42)
        stratify = y if min_class >= 2 else None
    else:
        cv = KFold(n_splits=eff_folds, shuffle=True, random_state=42)
        stratify = None

    numeric_features = [
        column for column in features
        if pd.api.types.is_numeric_dtype(data[column]) and not pd.api.types.is_bool_dtype(data[column])
    ]
    categorical_features = [column for column in features if column not in numeric_features]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    labels = sorted(y.unique())

    metrics = []
    confusion: dict[str, pd.DataFrame] = {}
    importances: dict[str, pd.DataFrame] = {}
    failures = []

    for model_key in model_keys:
        pipeline = build_model_pipeline(
            model_key, categorical_features, numeric_features, registry=CLASSIFIER_REGISTRY, scaler=scaler
        )
        try:
            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict(X_test)
            cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
        except Exception as exc:
            failures.append((model_key, str(exc)))
            continue

        metrics.append(
            {
                "model_key": model_key,
                "accuracy": float(accuracy_score(y_test, predictions)),
                "f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
                "precision": float(precision_score(y_test, predictions, average="macro", zero_division=0)),
                "recall": float(recall_score(y_test, predictions, average="macro", zero_division=0)),
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
            }
        )
        cm = confusion_matrix(y_test, predictions, labels=labels)
        confusion[model_key] = pd.DataFrame(cm, index=labels, columns=labels)
        fi = extract_feature_importance(pipeline)
        if fi is not None and not fi.empty:
            importances[model_key] = fi.head(15)

    return {
        "metrics": metrics,
        "confusion": confusion,
        "importances": importances,
        "failures": failures,
        "labels": labels,
        "fold_warning": fold_warning,
    }


def _render_classification(df: pd.DataFrame) -> None:
    all_columns = list(df.columns)

    target_candidates = _classification_target_candidates(df)
    if not target_candidates:
        st.warning(t("modeling.warn_clf_no_target"))
        return

    target = st.selectbox(
        t("modeling.clf.target"),
        options=target_candidates,
        help=t("modeling.clf.target_help"),
        key="modeling_clf_target",
    )

    feature_options = [column for column in all_columns if column != target]
    default_features = [c for c in feature_options if pd.api.types.is_numeric_dtype(df[c])]
    features = st.multiselect(
        t("modeling.features"),
        options=feature_options,
        default=default_features,
        key="modeling_clf_features",
    )
    if not features:
        st.warning(t("modeling.warn_min_feature"))
        return

    selected_models = st.multiselect(
        t("modeling.models"),
        options=list(CLASSIFIER_REGISTRY.keys()),
        default=DEFAULT_CLASSIFIER_KEYS,
        format_func=lambda model_key: t(CLASSIFIER_REGISTRY[model_key].label_key),
        key="modeling_clf_models",
    )
    if not selected_models:
        st.warning(t("modeling.warn_min_model"))
        return

    c1, c2 = st.columns(2)
    test_size = c1.slider(t("modeling.holdout"), 0.10, 0.40, 0.30, 0.05, key="modeling_clf_holdout")
    cv_folds = c2.slider(t("modeling.cv_folds"), 3, 10, 5, 1, key="modeling_clf_cv")

    c3, c4 = st.columns(2)
    scaler = c3.selectbox(
        t("modeling.scaler"),
        options=["standard", "minmax", "none"],
        format_func=lambda key: t(f"modeling.scaler.{key}"),
        help=t("modeling.scaler_help"),
        key="modeling_clf_scaler",
    )
    cv_kind = c4.selectbox(
        t("modeling.cv_kind"),
        options=["stratified", "kfold"],
        format_func=lambda key: t(f"modeling.cv_kind.{key}"),
        help=t("modeling.cv_kind_help"),
        key="modeling_clf_cv_kind",
    )

    data = df.dropna(subset=features + [target])[features + [target]].copy()
    if len(data) < 30:
        st.warning(t("modeling.warn_too_few_rows"))
        return

    if data[target].astype(str).nunique() < 2:
        st.warning(t("modeling.warn_clf_one_class"))
        return

    # Treino + CV cacheados: interações de UI (trocar o modelo da matriz, etc.)
    # não retreinam tudo; só recomputa quando dados/parâmetros mudam.
    with st.spinner(t("modeling.training")):
        out = _train_classifiers(
            data, tuple(features), target, tuple(selected_models),
            scaler, cv_kind, int(cv_folds), float(test_size),
        )

    if out["fold_warning"] is not None:
        mc, folds, new_folds = out["fold_warning"]
        st.warning(t("modeling.warn_clf_folds", min_class=mc, folds=folds, new_folds=new_folds))

    for model_key, err in out["failures"]:
        st.warning(t("modeling.warn_train_failed", error=f"{t(CLASSIFIER_REGISTRY[model_key].label_key)}: {err}"))

    if not out["metrics"]:
        st.error(t("modeling.error_no_models"))
        return

    labels = out["labels"]
    st.caption(t("modeling.clf.n_classes", n=len(labels), classes=", ".join(map(str, labels))))

    col_model = t("modeling.col.model")
    col_cvm = t("modeling.col.cv_acc_mean")
    col_f1 = t("modeling.col.f1")
    results_df = pd.DataFrame(
        [
            {
                col_model: t(CLASSIFIER_REGISTRY[m["model_key"]].label_key),
                t("modeling.col.accuracy"): m["accuracy"],
                col_f1: m["f1"],
                t("modeling.col.precision"): m["precision"],
                t("modeling.col.recall"): m["recall"],
                col_cvm: m["cv_mean"],
                t("modeling.col.cv_acc_std"): m["cv_std"],
            }
            for m in out["metrics"]
        ]
    ).sort_values(col_cvm, ascending=False)
    st.dataframe(results_df, use_container_width=True)

    best_row = results_df.iloc[0]
    m1, m2 = st.columns(2)
    m1.metric(t("modeling.metric.best_cv_acc"), f"{best_row[col_cvm]:.4f}")
    m1.caption(best_row[col_model])
    m2.metric(t("modeling.metric.best_f1"), f"{best_row[col_f1]:.4f}")
    m2.caption(best_row[col_model])

    # ---------------- Matriz de confusão ----------------
    confusion = out["confusion"]
    if confusion:
        st.markdown(f"#### {t('modeling.clf.confusion_title')}")
        cm_label_to_key = {t(CLASSIFIER_REGISTRY[k].label_key): k for k in confusion}
        chosen_label = st.selectbox(
            t("modeling.predicted_select"), options=list(cm_label_to_key.keys()), key="modeling_clf_cm_select"
        )
        cm_df = confusion[cm_label_to_key[chosen_label]]
        fig_cm, ax_cm = plt.subplots(figsize=(max(4, 0.7 * len(labels)), max(3.5, 0.6 * len(labels))))
        sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", ax=ax_cm)
        ax_cm.set_xlabel(t("modeling.clf.predicted"))
        ax_cm.set_ylabel(t("modeling.clf.true"))
        ax_cm.set_title(chosen_label)
        show_fig(fig_cm, fraction=0.65)
        plt.close(fig_cm)
        st.caption(t("modeling.clf.confusion_caption"))

    # ---------------- Importâncias / coeficientes ----------------
    importances = out["importances"]
    if importances:
        st.markdown(f"#### {t('modeling.importance_title')}")
        imp_label_to_key = {t(CLASSIFIER_REGISTRY[k].label_key): k for k in importances}
        detail_label = st.selectbox(
            t("modeling.importance_select"), options=list(imp_label_to_key.keys()), key="modeling_clf_imp_select"
        )
        importance_df = importances[imp_label_to_key[detail_label]]
        st.dataframe(importance_df, use_container_width=True)

        fig_imp, ax_imp = plt.subplots(figsize=(8, max(3, 0.35 * len(importance_df))))
        sns.barplot(
            data=importance_df,
            x="importance",
            y="feature",
            hue="feature",
            legend=False,
            palette="crest",
            ax=ax_imp,
        )
        ax_imp.set_title(t("modeling.importance_chart_title", n=len(importance_df)))
        ax_imp.set_xlabel(t("modeling.chart.importance"))
        ax_imp.set_ylabel("")
        show_fig(fig_imp)
        plt.close(fig_imp)
