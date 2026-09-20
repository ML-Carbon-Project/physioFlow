#!/usr/bin/env python3
"""Reproduce the public-dataset results reported in the PhysioFlow paper.

Runs the two Section 3.2 analyses head-lessly -- no interface, no login -- from
the public datasets shipped in ``data/sample/test/``:

    1. Yates (1935) oats split-plot ANOVA   -> paper Table 2 (F to the decimal)
    2. Palmer penguins EDA + classification -> r = 0.87, ~1.00 / ~0.99 accuracy

Every number printed here comes from the very same ``src/`` engine the Streamlit
application calls, so this script reproduces the reported computational results
without the graphical interface. It is also the entry point of the Code Ocean
reproducible capsule.

Usage
-----
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python reproduce_examples.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from src.ml.model_registry import CLASSIFIER_REGISTRY, build_model_pipeline
from src.stats_utils import (
    correlation_analysis,
    fit_experimental_anova,
    fit_split_plot,
)

DATA = Path(__file__).resolve().parent / "data" / "sample" / "test"


def _banner(title: str) -> None:
    print("\n" + "=" * 72 + f"\n{title}\n" + "=" * 72)


def oats_split_plot() -> None:
    """Section 3.2 / Table 2: split-plot ANOVA of the Yates oats trial."""
    _banner("1. Yates oats split-plot ANOVA  (paper Table 2)")
    df = pd.read_csv(DATA / "yates.oats.txt", sep="\t", engine="python")
    res = fit_split_plot(
        df, response="yield", whole_plot="gen", subplot="nitro", block="block"
    )
    tbl = res.table
    print(f"{'Term (stratum)':<18}{'df':>5}{'F':>12}{'p':>12}")
    for term in ["gen", "nitro", "gen × nitro"]:
        row = tbl.loc[term]
        print(f"{term:<18}{int(row['df']):>5}{row['F']:>12.3f}{row['p_value']:>12.4g}")
    print(
        "Reference nlme::Oats: gen F=1.485 (0.272) | nitro F=37.686 (<0.001) | "
        "gen×nitro F=0.303 (0.932)"
    )


def penguins() -> None:
    """Section 3.2: Palmer penguins EDA anchors and species classification."""
    _banner("2. Palmer penguins  (paper Section 3.2)")
    df = pd.read_csv(DATA / "penguins.csv", sep=",", engine="python")

    # --- EDA anchors -------------------------------------------------------
    anova = fit_experimental_anova(
        df, response="flipper_length_mm", treatment="species"
    )
    f_species = anova.table.loc["species", "F"]
    df_species = int(anova.table.loc["species", "df"])
    print(
        f"flipper ~ species : F({df_species},{int(anova.df_error)}) = {f_species:.2f}"
        "   (published 594.80)"
    )
    corr = correlation_analysis(df, ["flipper_length_mm", "body_mass_g"], "pearson")
    r = corr.corr.loc["flipper_length_mm", "body_mass_g"]
    print(f"Pearson flipper x body_mass = {r:.3f}   (published ~0.87)")

    # --- classification via the app's own pipeline builder -----------------
    feats = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    d = df.dropna(subset=feats + ["species"])
    X, y = d[feats], d["species"]
    x_tr, x_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42
    )
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    print(f"\n{'Classifier':<20}{'holdout acc':>13}{'CV acc (5-fold)':>18}")
    for key in ["random_forest_clf", "svm_clf", "knn_clf"]:
        pipe = build_model_pipeline(
            key, categorical_features=[], numeric_features=feats,
            registry=CLASSIFIER_REGISTRY,
        )
        pipe.fit(x_tr, y_tr)
        hold = accuracy_score(y_te, pipe.predict(x_te))
        cv = cross_val_score(
            build_model_pipeline(
                key, categorical_features=[], numeric_features=feats,
                registry=CLASSIFIER_REGISTRY,
            ),
            X, y, cv=skf, scoring="accuracy",
        ).mean()
        print(f"{key:<20}{hold:>13.3f}{cv:>18.3f}")
    print("Paper: RF, SVM and k-NN at 1.00 holdout accuracy and 0.99 stratified CV.")


if __name__ == "__main__":
    oats_split_plot()
    penguins()
    _banner("Done. Every value above was produced by src/ without the interface.")
