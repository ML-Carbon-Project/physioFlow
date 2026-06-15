from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
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

    default_target = "A" if "A" in all_columns else numeric_cols[0]
    target = st.selectbox(t("modeling.target"), options=numeric_cols, index=numeric_cols.index(default_target))

    default_features = [column for column in MODEL_DEFAULT_FEATURES if column in all_columns and column != target]
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
        st.pyplot(fig_pred)
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
        st.pyplot(fig_imp)
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

    df_model = df.dropna(subset=features + [target]).copy()
    if len(df_model) < 30:
        st.warning(t("modeling.warn_too_few_rows"))
        return

    X = df_model[features]
    y = df_model[target].astype(str)

    class_counts = y.value_counts()
    if class_counts.size < 2:
        st.warning(t("modeling.warn_clf_one_class"))
        return

    min_class = int(class_counts.min())
    eff_folds = cv_folds
    if cv_kind == "stratified":
        # StratifiedKFold exige >= cv_folds amostras na menor classe; reduzimos as
        # dobras quando alguma classe e rara para nao falhar.
        if min_class < cv_folds:
            eff_folds = max(2, min_class)
            st.warning(t("modeling.warn_clf_folds", min_class=min_class, folds=cv_folds, new_folds=eff_folds))
        cv = StratifiedKFold(n_splits=eff_folds, shuffle=True, random_state=42)
        stratify = y if min_class >= 2 else None
    else:
        cv = KFold(n_splits=eff_folds, shuffle=True, random_state=42)
        stratify = None

    numeric_features = [
        column for column in features
        if pd.api.types.is_numeric_dtype(df_model[column]) and not pd.api.types.is_bool_dtype(df_model[column])
    ]
    categorical_features = [column for column in features if column not in numeric_features]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    labels = sorted(y.unique())

    results = []
    confusion: dict[str, pd.DataFrame] = {}
    importances: dict[str, pd.DataFrame] = {}
    failures = []

    for model_key in selected_models:
        model_def = CLASSIFIER_REGISTRY[model_key]
        pipeline = build_model_pipeline(
            model_key, categorical_features, numeric_features, registry=CLASSIFIER_REGISTRY, scaler=scaler
        )
        try:
            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict(X_test)
            cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
        except Exception as exc:
            failures.append(t("modeling.warn_train_failed", error=f"{t(model_def.label_key)}: {exc}"))
            continue

        label = t(model_def.label_key)
        results.append(
            {
                t("modeling.col.model"): label,
                t("modeling.col.accuracy"): accuracy_score(y_test, predictions),
                t("modeling.col.f1"): f1_score(y_test, predictions, average="macro", zero_division=0),
                t("modeling.col.precision"): precision_score(y_test, predictions, average="macro", zero_division=0),
                t("modeling.col.recall"): recall_score(y_test, predictions, average="macro", zero_division=0),
                t("modeling.col.cv_acc_mean"): cv_scores.mean(),
                t("modeling.col.cv_acc_std"): cv_scores.std(),
            }
        )

        cm = confusion_matrix(y_test, predictions, labels=labels)
        confusion[label] = pd.DataFrame(cm, index=labels, columns=labels)

        feature_importance = extract_feature_importance(pipeline)
        if feature_importance is not None and not feature_importance.empty:
            importances[label] = feature_importance.head(15)

    for failure in failures:
        st.warning(failure)

    if not results:
        st.error(t("modeling.error_no_models"))
        return

    st.caption(t("modeling.clf.n_classes", n=len(labels), classes=", ".join(map(str, labels))))

    results_df = pd.DataFrame(results).sort_values(t("modeling.col.cv_acc_mean"), ascending=False)
    st.dataframe(results_df, use_container_width=True)

    best_row = results_df.iloc[0]
    m1, m2 = st.columns(2)
    m1.metric(t("modeling.metric.best_cv_acc"), f"{best_row[t('modeling.col.cv_acc_mean')]:.4f}")
    m1.caption(best_row[t("modeling.col.model")])
    m2.metric(t("modeling.metric.best_f1"), f"{best_row[t('modeling.col.f1')]:.4f}")
    m2.caption(best_row[t("modeling.col.model")])

    # ---------------- Matriz de confusão ----------------
    if confusion:
        st.markdown(f"#### {t('modeling.clf.confusion_title')}")
        chosen = st.selectbox(t("modeling.predicted_select"), options=list(confusion.keys()), key="modeling_clf_cm_select")
        cm_df = confusion[chosen]
        fig_cm, ax_cm = plt.subplots(figsize=(max(4, 0.7 * len(labels)), max(3.5, 0.6 * len(labels))))
        sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", ax=ax_cm)
        ax_cm.set_xlabel(t("modeling.clf.predicted"))
        ax_cm.set_ylabel(t("modeling.clf.true"))
        ax_cm.set_title(chosen)
        st.pyplot(fig_cm)
        plt.close(fig_cm)
        st.caption(t("modeling.clf.confusion_caption"))

    # ---------------- Importâncias / coeficientes ----------------
    if importances:
        st.markdown(f"#### {t('modeling.importance_title')}")
        detail_model = st.selectbox(
            t("modeling.importance_select"), options=list(importances.keys()), key="modeling_clf_imp_select"
        )
        importance_df = importances[detail_model]
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
        st.pyplot(fig_imp)
        plt.close(fig_imp)
