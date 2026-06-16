from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


@dataclass(frozen=True)
class ModelDefinition:
    key: str
    label_key: str
    scale_numeric: bool
    estimator_factory: Callable[[], Any]
    # GaussianNB nao aceita matriz esparsa; modelos com requires_dense=True
    # forcam o OneHotEncoder a devolver array denso.
    requires_dense: bool = False


MODEL_REGISTRY = {
    "linear_regression": ModelDefinition(
        key="linear_regression",
        label_key="modeling.label.linear",
        scale_numeric=True,
        estimator_factory=lambda: LinearRegression(),
    ),
    "random_forest": ModelDefinition(
        key="random_forest",
        label_key="modeling.label.rf",
        scale_numeric=False,
        estimator_factory=lambda: RandomForestRegressor(n_estimators=200, random_state=42),
    ),
    "decision_tree": ModelDefinition(
        key="decision_tree",
        label_key="modeling.label.dt",
        scale_numeric=False,
        estimator_factory=lambda: DecisionTreeRegressor(random_state=42),
    ),
    "gradient_boosting": ModelDefinition(
        key="gradient_boosting",
        label_key="modeling.label.gb",
        scale_numeric=False,
        # HistGradientBoosting é muito mais rápido em escala; exige matriz densa.
        estimator_factory=lambda: HistGradientBoostingRegressor(random_state=42),
        requires_dense=True,
    ),
    "knn": ModelDefinition(
        key="knn",
        label_key="modeling.label.knn",
        scale_numeric=True,
        estimator_factory=lambda: KNeighborsRegressor(n_neighbors=5),
    ),
}

DEFAULT_MODEL_KEYS = ["linear_regression", "random_forest"]


# Classificadores clássicos — espelham as famílias da regressão e somam SVM e
# Naive Bayes, sem contrapartida no lado de regressão.
CLASSIFIER_REGISTRY = {
    "logistic": ModelDefinition(
        key="logistic",
        label_key="modeling.label.logistic",
        scale_numeric=True,
        estimator_factory=lambda: LogisticRegression(max_iter=1000),
    ),
    "random_forest_clf": ModelDefinition(
        key="random_forest_clf",
        label_key="modeling.label.rf",
        scale_numeric=False,
        estimator_factory=lambda: RandomForestClassifier(n_estimators=200, random_state=42),
    ),
    "decision_tree_clf": ModelDefinition(
        key="decision_tree_clf",
        label_key="modeling.label.dt",
        scale_numeric=False,
        estimator_factory=lambda: DecisionTreeClassifier(random_state=42),
    ),
    "gradient_boosting_clf": ModelDefinition(
        key="gradient_boosting_clf",
        label_key="modeling.label.gb",
        scale_numeric=False,
        # HistGradientBoosting é muito mais rápido em escala; exige matriz densa.
        estimator_factory=lambda: HistGradientBoostingClassifier(random_state=42),
        requires_dense=True,
    ),
    "knn_clf": ModelDefinition(
        key="knn_clf",
        label_key="modeling.label.knn",
        scale_numeric=True,
        estimator_factory=lambda: KNeighborsClassifier(n_neighbors=5),
    ),
    "svm_clf": ModelDefinition(
        key="svm_clf",
        label_key="modeling.label.svm",
        scale_numeric=True,
        estimator_factory=lambda: SVC(random_state=42),
    ),
    "naive_bayes": ModelDefinition(
        key="naive_bayes",
        label_key="modeling.label.nb",
        scale_numeric=False,
        estimator_factory=lambda: GaussianNB(),
        requires_dense=True,
    ),
}

DEFAULT_CLASSIFIER_KEYS = ["logistic", "random_forest_clf"]


def _numeric_transformer(model_def: ModelDefinition, scaler: str | None):
    """Resolve a transformação das colunas numéricas.

    ``scaler=None`` mantém o comportamento por modelo (``scale_numeric``); um
    valor explícito ("standard"/"minmax"/"none") sobrepõe para todos os modelos.
    """
    if scaler is None:
        return StandardScaler() if model_def.scale_numeric else "passthrough"
    if scaler == "standard":
        return StandardScaler()
    if scaler == "minmax":
        return MinMaxScaler()
    if scaler == "none":
        return "passthrough"
    raise ValueError(f"Escala desconhecida: {scaler!r}")


def build_model_pipeline(
    model_key: str,
    categorical_features: list[str],
    numeric_features: list[str],
    registry: dict[str, ModelDefinition] = MODEL_REGISTRY,
    scaler: str | None = None,
) -> Pipeline:
    model_def = registry[model_key]
    numeric_transformer = _numeric_transformer(model_def, scaler)

    preprocess = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=not model_def.requires_dense),
                categorical_features,
            ),
            ("num", numeric_transformer, numeric_features),
        ],
        # sparse_threshold=0 garante saida densa quando o estimador exige (GaussianNB).
        sparse_threshold=0 if model_def.requires_dense else 0.3,
    )

    return Pipeline(steps=[("preprocess", preprocess), ("model", model_def.estimator_factory())])


def extract_feature_importance(model_pipeline: Pipeline) -> pd.DataFrame | None:
    preprocess = model_pipeline.named_steps["preprocess"]
    estimator = model_pipeline.named_steps["model"]
    feature_names = preprocess.get_feature_names_out()

    if hasattr(estimator, "feature_importances_"):
        importance_values = np.asarray(estimator.feature_importances_)
    elif hasattr(estimator, "coef_"):
        coef = np.asarray(estimator.coef_)
        # Classificacao multiclasse: coef_ tem shape (n_classes, n_features).
        # Resumimos pela media do |coef| entre as classes para alinhar com feature_names.
        if coef.ndim == 2 and coef.shape[0] > 1:
            importance_values = np.abs(coef).mean(axis=0)
        else:
            importance_values = np.abs(np.ravel(coef))
    else:
        return None

    if len(feature_names) != len(importance_values):
        return None

    return pd.DataFrame({"feature": feature_names, "importance": importance_values}).sort_values(
        "importance", ascending=False
    )
