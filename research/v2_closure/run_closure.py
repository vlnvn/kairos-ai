"""Run the fixed-recipe KAIROS V2 closure benchmark exactly once per phase."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PREREGISTRATION_SHA256 = "4737d10d38c70c7a26a9e4692a0c63900513fa4f3ab39704fdaf216490b01f41"
SEED = 20260810
BOOTSTRAP_REPLICATES = 2000
FEATURES = [
    "slack_to_start_h", "slack_to_end_h", "window_width_h", "accept_hour_sin",
    "accept_hour_cos", "day_of_week", "task_lng", "task_lat",
    "accept_to_task_km", "accept_gps_missing", "prior_courier_accepts_day",
    "prior_aoi_accepts_day", "pending_other_count", "pending_same_aoi_count",
    "pending_due_before_count", "pending_overlap_count", "oldest_pending_age_h",
    "pending_centroid_distance_km", "pending_location_missing", "region_id", "aoi_type",
]
CATEGORICAL = ["region_id", "aoi_type"]
NUMERIC = [name for name in FEATURES if name not in CATEGORICAL]


def verify_preregistration(path: Path) -> None:
    """Fail if the preregistration bytes differ from the pre-metric lock."""
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != PREREGISTRATION_SHA256:
        raise RuntimeError(f"preregistration mismatch: {actual}")


def split_paths(root: Path, split: str) -> list[Path]:
    paths = sorted(root.glob(f"*_{split}.parquet"))
    if len(paths) != 5:
        raise RuntimeError(f"expected five {split} files, found {len(paths)}")
    return paths


def load_split(root: Path, split: str) -> pd.DataFrame:
    return pd.concat(
        [pd.read_parquet(path) for path in split_paths(root, split)],
        ignore_index=True,
    )


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    matrix = frame[FEATURES].copy()
    for column in CATEGORICAL:
        matrix[column] = matrix[column].fillna(-1).round().astype("int64").astype("string")
    return matrix


def logistic_recipe() -> Pipeline:
    return Pipeline([
        ("prepare", ColumnTransformer([
            ("numeric", StandardScaler(), NUMERIC),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ])),
        ("model", LogisticRegression(
            C=1.0,
            class_weight="balanced",
            solver="saga",
            max_iter=100,
            random_state=SEED,
            tol=1e-3,
        )),
    ])


def catboost_recipe() -> CatBoostClassifier:
    return CatBoostClassifier(
        iterations=300,
        depth=6,
        learning_rate=0.05,
        loss_function="Logloss",
        auto_class_weights="Balanced",
        random_seed=SEED,
        verbose=False,
        allow_writing_files=False,
        thread_count=-1,
    )


def fit_models(frame: pd.DataFrame) -> tuple[Pipeline, CatBoostClassifier, dict]:
    x = feature_matrix(frame)
    y = frame["off_window"].to_numpy(dtype=np.int8)
    logistic = logistic_recipe()
    started = time.perf_counter()
    logistic.fit(x, y)
    logistic_seconds = time.perf_counter() - started
    catboost = catboost_recipe()
    started = time.perf_counter()
    catboost.fit(x, y, cat_features=CATEGORICAL)
    catboost_seconds = time.perf_counter() - started
    return logistic, catboost, {
        "training_rows": int(len(frame)),
        "logistic_seconds": logistic_seconds,
        "catboost_seconds": catboost_seconds,
    }


def selection_mask(frame: pd.DataFrame, scores: np.ndarray, fraction: float) -> np.ndarray:
    groups = frame["decision_group_id"].to_numpy(dtype=np.int64)
    order = np.lexsort((-scores, groups))
    ordered_groups = groups[order]
    starts = np.r_[0, np.flatnonzero(ordered_groups[1:] != ordered_groups[:-1]) + 1]
    stops = np.r_[starts[1:], len(order)]
    selected = np.zeros(len(frame), dtype=bool)
    for start, stop in zip(starts, stops):
        count = max(1, math.ceil(fraction * (stop - start)))
        selected[order[start:start + count]] = True
    return selected


def subgroup_recall(labels: np.ndarray, selected: np.ndarray, subgroup: np.ndarray) -> dict:
    eligible = (labels == 1) & subgroup
    positives = int(eligible.sum())
    captured = int((eligible & selected).sum())
    return {
        "recall_at_10": captured / positives if positives else None,
        "captured": captured,
        "positives": positives,
    }


def evaluate(frame: pd.DataFrame, scores: np.ndarray) -> dict:
    labels = frame["off_window"].to_numpy(dtype=np.int8)
    result: dict = {
        "task_count": int(len(frame)),
        "positive_count": int(labels.sum()),
        "target_prevalence": float(labels.mean()),
        "pr_auc": float(average_precision_score(labels, scores)),
    }
    selections = {}
    for name, fraction in (("recall_at_5", 0.05), ("recall_at_10", 0.10), ("recall_at_20", 0.20)):
        selected = selection_mask(frame, scores, fraction)
        selections[name] = selected
        result[name] = float(labels[selected].sum() / labels.sum())
        result[f"review_count_{int(fraction * 100)}"] = int(selected.sum())
    selected10 = selections["recall_at_10"]
    result["city_recall_at_10"] = {}
    cities = frame["city"].astype(str).to_numpy()
    for city in sorted(set(cities)):
        result["city_recall_at_10"][city] = subgroup_recall(
            labels, selected10, cities == city,
        )["recall_at_10"]
    target_class = frame["target_class"].to_numpy(dtype=np.int8)
    result["early_diagnostic"] = subgroup_recall(labels, selected10, target_class == 0)
    result["late_diagnostic"] = subgroup_recall(labels, selected10, target_class == 2)
    return result


def score_models(
    frame: pd.DataFrame,
    logistic: Pipeline,
    catboost: CatBoostClassifier,
) -> tuple[np.ndarray, np.ndarray]:
    x = feature_matrix(frame)
    logistic_scores = np.asarray(logistic.decision_function(x), dtype=np.float64)
    catboost_scores = np.asarray(
        catboost.predict(x, prediction_type="RawFormulaVal"), dtype=np.float64,
    )
    return logistic_scores, catboost_scores


def date_bootstrap(
    frame: pd.DataFrame,
    logistic_scores: np.ndarray,
    catboost_scores: np.ndarray,
) -> dict:
    labels = frame["off_window"].to_numpy(dtype=np.int8)
    logistic_selected = selection_mask(frame, logistic_scores, 0.10)
    catboost_selected = selection_mask(frame, catboost_scores, 0.10)
    dates = pd.to_datetime(frame["source_date"]).dt.strftime("%Y-%m-%d").to_numpy()
    unique_dates = np.asarray(sorted(set(dates)))
    positives = np.zeros(len(unique_dates), dtype=np.int64)
    logistic_hits = np.zeros(len(unique_dates), dtype=np.int64)
    catboost_hits = np.zeros(len(unique_dates), dtype=np.int64)
    for index, date in enumerate(unique_dates):
        mask = dates == date
        positives[index] = int(labels[mask].sum())
        logistic_hits[index] = int(labels[mask & logistic_selected].sum())
        catboost_hits[index] = int(labels[mask & catboost_selected].sum())
    rng = np.random.default_rng(SEED)
    deltas = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for replicate in range(BOOTSTRAP_REPLICATES):
        sampled = rng.integers(0, len(unique_dates), size=len(unique_dates))
        denominator = positives[sampled].sum()
        deltas[replicate] = 100.0 * (
            catboost_hits[sampled].sum() - logistic_hits[sampled].sum()
        ) / denominator
    return {
        "unit": "source_date",
        "date_count": int(len(unique_dates)),
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": SEED,
        "delta_pp_95_ci": [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))],
    }


def write_once(path: Path, payload: dict) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite one-shot result: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_validation(processed_root: Path, output: Path) -> None:
    train = load_split(processed_root, "train")
    logistic, catboost, training = fit_models(train)
    validation = load_split(processed_root, "validation")
    logistic_scores, catboost_scores = score_models(validation, logistic, catboost)
    logistic_metrics = evaluate(validation, logistic_scores)
    catboost_metrics = evaluate(validation, catboost_scores)
    write_once(output, {
        "phase": "V2_VALIDATION_ONE_SHOT_CHARACTERIZATION",
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "parameters_changed_after_preregistration": False,
        "training": training,
        "B0_logistic": logistic_metrics,
        "B1_catboost_recipe_control": catboost_metrics,
        "catboost_minus_logistic_recall_at_10_pp": 100.0 * (
            catboost_metrics["recall_at_10"] - logistic_metrics["recall_at_10"]
        ),
    })


def run_final(processed_root: Path, validation_results: Path, output: Path) -> None:
    validation_payload = json.loads(validation_results.read_text(encoding="utf-8"))
    if validation_payload.get("preregistration_sha256") != PREREGISTRATION_SHA256:
        raise RuntimeError("validation result is not bound to the frozen preregistration")
    train = load_split(processed_root, "train")
    validation = load_split(processed_root, "validation")
    fitting = pd.concat([train, validation], ignore_index=True)
    logistic, catboost, training = fit_models(fitting)
    known_couriers = set(fitting["courier_id"].tolist())
    known_aois = set(fitting["aoi_id"].tolist())
    del train, validation, fitting
    final = load_split(processed_root, "final")
    logistic_scores, catboost_scores = score_models(final, logistic, catboost)
    logistic_metrics = evaluate(final, logistic_scores)
    catboost_metrics = evaluate(final, catboost_scores)
    labels = final["off_window"].to_numpy(dtype=np.int8)
    logistic_selected = selection_mask(final, logistic_scores, 0.10)
    catboost_selected = selection_mask(final, catboost_scores, 0.10)
    unseen_courier = ~final["courier_id"].isin(known_couriers).to_numpy()
    unseen_aoi = ~final["aoi_id"].isin(known_aois).to_numpy()
    payload = {
        "phase": "V2_FINAL_ONE_SHOT_CHARACTERIZATION",
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "parameters_changed_after_validation": False,
        "training": training,
        "B0_logistic": logistic_metrics,
        "B1_catboost_recipe_control": catboost_metrics,
        "catboost_minus_logistic_recall_at_10_pp": 100.0 * (
            catboost_metrics["recall_at_10"] - logistic_metrics["recall_at_10"]
        ),
        "paired_bootstrap": date_bootstrap(final, logistic_scores, catboost_scores),
        "unseen_entities": {
            "definition": "entity absent from combined TRAIN plus VALIDATION fitting rows",
            "B0_logistic": {
                "unseen_courier": subgroup_recall(labels, logistic_selected, unseen_courier),
                "unseen_aoi": subgroup_recall(labels, logistic_selected, unseen_aoi),
            },
            "B1_catboost_recipe_control": {
                "unseen_courier": subgroup_recall(labels, catboost_selected, unseen_courier),
                "unseen_aoi": subgroup_recall(labels, catboost_selected, unseen_aoi),
            },
            "unseen_courier_task_count": int(unseen_courier.sum()),
            "unseen_aoi_task_count": int(unseen_aoi.sum()),
        },
    }
    write_once(output, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("validation", "final"))
    parser.add_argument("--processed-root", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-results", type=Path)
    args = parser.parse_args()
    verify_preregistration(args.preregistration)
    if args.output.exists():
        raise RuntimeError(f"refusing to reopen one-shot result: {args.output}")
    if args.phase == "validation":
        run_validation(args.processed_root, args.output)
    else:
        if args.validation_results is None:
            parser.error("--validation-results is required for final")
        run_final(args.processed_root, args.validation_results, args.output)


if __name__ == "__main__":
    main()
