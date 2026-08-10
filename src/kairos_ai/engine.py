"""Frozen, future-free feature and ranking engine."""
from __future__ import annotations

import hashlib
import math
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

FEATURES = [
    "slack_to_start_h", "slack_to_end_h", "window_width_h", "accept_hour_sin",
    "accept_hour_cos", "day_of_week", "task_lng", "task_lat",
    "accept_to_task_km", "accept_gps_missing", "prior_courier_accepts_day",
    "prior_aoi_accepts_day", "pending_other_count", "pending_same_aoi_count",
    "pending_due_before_count", "pending_overlap_count", "oldest_pending_age_h",
    "pending_centroid_distance_km", "pending_location_missing", "region_id", "aoi_type",
]
FROZEN_FEATURES = tuple(FEATURES)
FROZEN_CATEGORICAL_FEATURE_INDICES = (19, 20)
COUNTER_FIELDS = ("prior_courier_accepts_day", "prior_aoi_accepts_day")
EXPECTED_MODEL_SHA256 = "b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315"
FUTURE_FIELDS = {
    "actual_duration", "actual_pickup_at", "actual_pickup_timestamp",
    "completed_at", "completion_status", "is_violation", "label", "off_window",
    "outcome", "pickup_gps_lat", "pickup_gps_lng", "pickup_gps_time",
    "pickup_time", "post_decision_route", "route_completed_at", "route_realization",
    "target", "violated_window", "violation",
}
TOP_FIELDS = {"snapshot_time", "review_budget_fraction", "target_task_ids", "tasks"}
TASK_FIELDS = {"task_id", "courier_key", "accepted_at", "window_start", "window_end", "region_id", "aoi_key", "aoi_type", "lng", "lat", "accept_gps_lng", "accept_gps_lat", "prior_courier_accepts_day", "prior_aoi_accepts_day", "is_pending"}
REQUIRED_TASK = {"task_id", "courier_key", "accepted_at", "window_start", "window_end", "region_id", "aoi_key", "aoi_type", "lng", "lat", "is_pending"}


class SnapshotError(ValueError):
    """Fail-closed snapshot validation error."""


class ModelArtifactError(RuntimeError):
    """Raised when the frozen model artifact cannot be trusted."""


def verify_model_artifact(model_path: str | Path) -> Path:
    """Return a resolved path only when the frozen model hash is exact."""
    path = Path(model_path).resolve()
    if not path.is_file():
        raise ModelArtifactError(f"model artifact not found: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != EXPECTED_MODEL_SHA256:
        raise ModelArtifactError(
            f"model artifact SHA-256 mismatch: expected {EXPECTED_MODEL_SHA256}, got {actual}"
        )
    return path


def parse_timestamp(value) -> pd.Timestamp:
    """Parse a request timestamp into the engine's timezone-naive UTC form."""
    if not isinstance(value, str) or not value.strip():
        raise SnapshotError("timestamp must be a nonempty string")
    try:
        parsed = pd.Timestamp(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise SnapshotError(f"invalid timestamp: {value}") from exc
    if pd.isna(parsed):
        raise SnapshotError(f"invalid timestamp: {value}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("UTC").tz_localize(None)
    return parsed


def _is_finite_real(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _normalize_identifier(value, field: str) -> str:
    if (
        value is None
        or isinstance(value, (bool, dict, list, tuple, set))
        or (isinstance(value, Real) and not _is_finite_real(value))
    ):
        raise SnapshotError(f"{field} must be a nonempty string or finite number")
    normalized = str(value)
    if not normalized.strip():
        raise SnapshotError(f"{field} must be a nonempty string or finite number")
    return normalized


def _finite_number(value, field: str) -> float:
    if not _is_finite_real(value):
        raise SnapshotError(f"{field} must be a finite number")
    return float(value)


def _validate_coordinate_pair(task: dict, lon_field: str, lat_field: str) -> None:
    lon, lat = task.get(lon_field), task.get(lat_field)
    if lon is None and lat is None:
        return
    if lon is None or lat is None:
        raise SnapshotError(f"{lon_field} and {lat_field} must both be null or numeric")
    lon_value = _finite_number(lon, lon_field)
    lat_value = _finite_number(lat, lat_field)
    if not -180 <= lon_value <= 180:
        raise SnapshotError(f"{lon_field} must be between -180 and 180")
    if not -90 <= lat_value <= 90:
        raise SnapshotError(f"{lat_field} must be between -90 and 90")


def _validate_counter(value, field: str) -> None:
    number = _finite_number(value, field)
    if number < 0 or not number.is_integer():
        raise SnapshotError(f"{field} must be a nonnegative integer")


def _validate_finite_duration(later: pd.Timestamp, earlier: pd.Timestamp) -> None:
    try:
        seconds = (later - earlier).total_seconds()
    except (OverflowError, TypeError, ValueError) as exc:
        raise SnapshotError("timestamp range is not supported") from exc
    if not math.isfinite(seconds):
        raise SnapshotError("timestamp range is not supported")


def haversine(lon1, lat1, lon2, lat2):
    """Return the great-circle distance in kilometers for finite coordinates."""
    if not all(np.isfinite([lon1, lat1, lon2, lat2])):
        return np.nan
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return float(6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1))))


def validate_snapshot(snapshot: dict) -> None:
    """Validate an Operational Review Request or raise ``SnapshotError``."""
    if not isinstance(snapshot, dict):
        raise SnapshotError("snapshot must be an object")
    if set(snapshot) != TOP_FIELDS:
        raise SnapshotError(f"top-level fields must be exactly {sorted(TOP_FIELDS)}")
    review_budget_fraction = snapshot["review_budget_fraction"]
    if (
        not _is_finite_real(review_budget_fraction)
        or not 0 < review_budget_fraction <= 1
    ):
        raise SnapshotError(
            "review_budget_fraction must be a finite number greater than 0 "
            "and less than or equal to 1"
        )
    now = parse_timestamp(snapshot["snapshot_time"])
    target_values = snapshot["target_task_ids"]
    if not isinstance(target_values, list):
        raise SnapshotError("target_task_ids must be an array")
    targets = [
        _normalize_identifier(value, "target_task_ids item")
        for value in target_values
    ]
    if not targets or len(targets) != len(set(targets)):
        raise SnapshotError("target_task_ids must be nonempty and unique")
    task_values = snapshot["tasks"]
    if not isinstance(task_values, list) or not task_values:
        raise SnapshotError("tasks must be a nonempty array")
    seen, tasks = set(), {}
    for task in task_values:
        if not isinstance(task, dict):
            raise SnapshotError("each task must be an object")
        future = set(task) & FUTURE_FIELDS
        if future:
            raise SnapshotError(
                f"forbidden future/outcome fields: {sorted(map(str, future))}"
            )
        unknown = set(task) - TASK_FIELDS
        if unknown:
            raise SnapshotError(f"unknown task fields: {sorted(map(str, unknown))}")
        missing = REQUIRED_TASK - set(task)
        if missing:
            raise SnapshotError(f"missing task fields: {sorted(missing)}")
        key = _normalize_identifier(task["task_id"], "task_id")
        if key in seen:
            raise SnapshotError(f"duplicate task_id: {key}")
        seen.add(key)
        tasks[key] = task
        for field in ("courier_key", "region_id", "aoi_key", "aoi_type"):
            _normalize_identifier(task[field], field)
        accepted = parse_timestamp(task["accepted_at"])
        start, end = parse_timestamp(task["window_start"]), parse_timestamp(task["window_end"])
        if accepted > now:
            raise SnapshotError(f"task {key} accepted after snapshot")
        if start > end or accepted > end:
            raise SnapshotError(f"task {key} has invalid/actionably expired window")
        if task["is_pending"] is not True:
            raise SnapshotError(f"task {key} is not pending")
        _validate_finite_duration(now, accepted)
        _validate_finite_duration(start, accepted)
        _validate_finite_duration(end, start)
        _validate_coordinate_pair(task, "lng", "lat")
        _validate_coordinate_pair(task, "accept_gps_lng", "accept_gps_lat")
        for name in COUNTER_FIELDS:
            if name in task and task[name] is not None:
                _validate_counter(task[name], name)
    if not set(targets).issubset(seen):
        raise SnapshotError("target_task_ids must exist in tasks")
    for key in targets:
        task = tasks[key]
        if parse_timestamp(task["accepted_at"]) != now:
            raise SnapshotError(f"target {key} must be scored at acceptance")
        for name in COUNTER_FIELDS:
            if task.get(name) is None:
                raise SnapshotError(f"target {key} requires nonnegative {name}")


def _verify_loaded_model_contract(model: CatBoostClassifier) -> None:
    if tuple(FEATURES) != FROZEN_FEATURES:
        raise ModelArtifactError("frozen feature contract mismatch")
    if tuple(model.feature_names_) != FROZEN_FEATURES:
        raise ModelArtifactError("model feature contract mismatch")
    if tuple(model.get_cat_feature_indices()) != FROZEN_CATEGORICAL_FEATURE_INDICES:
        raise ModelArtifactError("model categorical feature contract mismatch")


def build_features(snapshot: dict) -> tuple[pd.DataFrame, list[str]]:
    """Build the frozen feature frame and normalized target task IDs."""
    validate_snapshot(snapshot)
    now = parse_timestamp(snapshot["snapshot_time"])
    by_id = {str(x["task_id"]): x for x in snapshot["tasks"]}
    by_courier = {}
    for task in snapshot["tasks"]:
        by_courier.setdefault(str(task["courier_key"]), []).append(task)
    rows, ids = [], []
    for task_id in map(str, snapshot["target_task_ids"]):
        task = by_id[task_id]
        accepted = parse_timestamp(task["accepted_at"])
        start, end = parse_timestamp(task["window_start"]), parse_timestamp(task["window_end"])
        others = [x for x in by_courier[str(task["courier_key"])] if str(x["task_id"]) != task_id]
        locations = [x for x in others if x.get("lng") is not None and x.get("lat") is not None]
        if locations and task.get("lng") is not None and task.get("lat") is not None:
            centroid_distance = haversine(float(task["lng"]), float(task["lat"]), np.mean([float(x["lng"]) for x in locations]), np.mean([float(x["lat"]) for x in locations]))
            location_missing = 0
        else:
            centroid_distance, location_missing = np.nan, 1
        hour = accepted.hour + accepted.minute / 60
        gps_missing = task.get("accept_gps_lng") is None or task.get("accept_gps_lat") is None
        rows.append({
            "slack_to_start_h": (start-accepted).total_seconds()/3600,
            "slack_to_end_h": (end-accepted).total_seconds()/3600,
            "window_width_h": (end-start).total_seconds()/3600,
            "accept_hour_sin": math.sin(2*math.pi*hour/24), "accept_hour_cos": math.cos(2*math.pi*hour/24),
            "day_of_week": accepted.dayofweek, "task_lng": task["lng"], "task_lat": task["lat"],
            "accept_to_task_km": np.nan if gps_missing else haversine(float(task["accept_gps_lng"]), float(task["accept_gps_lat"]), float(task["lng"]), float(task["lat"])),
            "accept_gps_missing": int(gps_missing),
            "prior_courier_accepts_day": int(task["prior_courier_accepts_day"]), "prior_aoi_accepts_day": int(task["prior_aoi_accepts_day"]),
            "pending_other_count": len(others),
            "pending_same_aoi_count": sum(str(x["aoi_key"]) == str(task["aoi_key"]) for x in others),
            "pending_due_before_count": sum(parse_timestamp(x["window_end"]) <= end for x in others),
            "pending_overlap_count": sum(parse_timestamp(x["window_start"]) <= end and parse_timestamp(x["window_end"]) >= start for x in others),
            "oldest_pending_age_h": max([(now-parse_timestamp(x["accepted_at"])).total_seconds()/3600 for x in others], default=0.0),
            "pending_centroid_distance_km": centroid_distance, "pending_location_missing": location_missing,
            "region_id": str(task["region_id"]), "aoi_type": str(task["aoi_type"]),
        })
        ids.append(task_id)
    return pd.DataFrame(rows, columns=FEATURES), ids


class KairosRanker:
    """Reusable deterministic adapter from a validated snapshot to ranked tasks.

    ``score`` accepts an Operational Review Request-shaped dictionary and returns
    priority-ordered task decision dictionaries. Invalid snapshots raise
    :class:`SnapshotError`; an absent or modified model raises
    :class:`ModelArtifactError` during construction. The verified CatBoost model
    is loaded once per ranker instance and reused. Identical inputs, model bytes,
    and runtime versions produce identical ordering, with ``task_id`` as the
    stable tie-breaker.
    """

    def __init__(self, model_path: str | Path):
        self.model_path = verify_model_artifact(model_path)
        self.model = CatBoostClassifier()
        try:
            self.model.load_model(str(self.model_path))
        except Exception as exc:
            raise ModelArtifactError("model artifact could not be loaded") from exc
        _verify_loaded_model_contract(self.model)

    def score(self, snapshot: dict) -> list[dict]:
        _verify_loaded_model_contract(self.model)
        features, ids = build_features(snapshot)
        try:
            scores = self.model.predict_proba(features)[:, 1]
        except Exception as exc:
            raise ModelArtifactError("model scoring failed") from exc
        if len(scores) != len(ids) or not np.isfinite(scores).all():
            raise ModelArtifactError("model produced invalid scores")
        order = sorted(range(len(ids)), key=lambda i: (-scores[i], ids[i]))
        ranks = {idx: rank for rank, idx in enumerate(order, 1)}
        review_budget_fraction = float(snapshot["review_budget_fraction"])
        budget = max(1, math.ceil(review_budget_fraction * len(ids)))
        output = []
        for i, task_id in enumerate(ids):
            output.append({
                "task_id": task_id,
                "decision": "WINDOW_REVIEW" if ranks[i] <= budget else "KEEP_ASSIGNMENT",
                "rank": ranks[i], "priority": ranks[i], "review_score": round(float(scores[i]), 10),
                "evidence_signals": [
                    {"signal": "slack_to_end_h", "value": round(float(features.at[i, "slack_to_end_h"]), 3)},
                    {"signal": "pending_other_count", "value": int(features.at[i, "pending_other_count"])},
                    {"signal": "pending_overlap_count", "value": int(features.at[i, "pending_overlap_count"])},
                ],
                "explanation_notice": "Uncalibrated ordering score with non-causal signals; dispatcher owns the decision.",
            })
        return sorted(output, key=lambda x: x["rank"])
