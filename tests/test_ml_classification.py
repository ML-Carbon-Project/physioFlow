"""Validação do módulo de ML de classificação contra o Palmer Penguins.

Classificar a espécie a partir das medidas morfométricas é o benchmark clássico
do dataset (acurácia ~99% com modelos fortes). Estes testes travam o
comportamento dos 7 classificadores e cobrem dois riscos específicos da
implementação:
- Naive Bayes (GaussianNB) exige matriz **densa** — o OneHotEncoder precisa
  devolver array denso (``requires_dense``), senão o fit quebra.
- ``extract_feature_importance`` precisa lidar com ``coef_`` **multiclasse**
  (shape (n_classes, n_features)) da Regressão Logística.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from src.ml import (
    CLASSIFIER_REGISTRY,
    DEFAULT_CLASSIFIER_KEYS,
    build_model_pipeline,
    extract_feature_importance,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample" / "test"
_FEATURES = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "island", "sex"]


def _penguins_xy():
    path = SAMPLE_DIR / "penguins.csv"
    if not path.exists():
        pytest.skip(f"fixture ausente: {path}")
    df = pd.read_csv(path).dropna(subset=_FEATURES + ["species"]).copy()
    return df[_FEATURES], df["species"].astype(str)


def test_registry_has_seven_classifiers():
    assert len(CLASSIFIER_REGISTRY) == 7
    assert set(DEFAULT_CLASSIFIER_KEYS).issubset(CLASSIFIER_REGISTRY)


def test_all_classifiers_train_and_predict():
    """Os 7 modelos treinam e preveem sem erro — em especial o Naive Bayes,
    cujo caminho denso quebraria com OneHotEncoder esparso."""
    X, y = _penguins_xy()
    num = [c for c in _FEATURES if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in _FEATURES if c not in num]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    for key in CLASSIFIER_REGISTRY:
        pipe = build_model_pipeline(key, cat, num, registry=CLASSIFIER_REGISTRY)
        pipe.fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        assert len(pred) == len(yte)
        assert accuracy_score(yte, pred) > 0.7  # ate o pior modelo passa folgado aqui


def test_strong_models_reach_literature_accuracy():
    """RF e Logística devem cravar o benchmark de ~99% em CV."""
    X, y = _penguins_xy()
    num = [c for c in _FEATURES if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in _FEATURES if c not in num]
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    for key in ("logistic", "random_forest_clf"):
        pipe = build_model_pipeline(key, cat, num, registry=CLASSIFIER_REGISTRY)
        scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")
        assert scores.mean() > 0.95


def test_scaler_option_changes_scale_sensitive_models():
    """O parâmetro ``scaler`` deve valer para todos os modelos: sem escala, o KNN
    (sensível a distância) degrada visivelmente frente ao StandardScaler."""
    import pytest as _pytest
    from src.ml.model_registry import build_model_pipeline as _build

    X, y = _penguins_xy()
    num = [c for c in _FEATURES if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in _FEATURES if c not in num]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    def acc(scaler):
        pipe = _build("knn_clf", cat, num, registry=CLASSIFIER_REGISTRY, scaler=scaler)
        pipe.fit(Xtr, ytr)
        return accuracy_score(yte, pipe.predict(Xte))

    assert acc("standard") - acc("none") > 0.1   # escalar ajuda muito o KNN aqui

    with _pytest.raises(ValueError):
        _build("knn_clf", cat, num, registry=CLASSIFIER_REGISTRY, scaler="invalido")


def test_naive_bayes_dense_holds_with_explicit_scaler():
    """O caminho denso do GaussianNB deve continuar válido com escala explícita."""
    X, y = _penguins_xy()
    num = [c for c in _FEATURES if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in _FEATURES if c not in num]
    pipe = build_model_pipeline("naive_bayes", cat, num, registry=CLASSIFIER_REGISTRY, scaler="minmax")
    pipe.fit(X, y)  # não deve levantar (matriz densa)
    assert len(pipe.predict(X)) == len(y)


def test_multiclass_logistic_feature_importance_is_aligned():
    """coef_ multiclasse (3×n_features) deve ser resumido e alinhado às features,
    não retornar None por incompatibilidade de tamanho."""
    X, y = _penguins_xy()
    num = [c for c in _FEATURES if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in _FEATURES if c not in num]
    pipe = build_model_pipeline("logistic", cat, num, registry=CLASSIFIER_REGISTRY)
    pipe.fit(X, y)
    fi = extract_feature_importance(pipe)
    assert fi is not None
    n_features_out = len(pipe.named_steps["preprocess"].get_feature_names_out())
    assert len(fi) == n_features_out
    # bill_length e o separador morfometrico dominante entre especies.
    assert "bill_length" in str(fi.iloc[0]["feature"])
