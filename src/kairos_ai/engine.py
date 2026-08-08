"""Frozen, future-free feature and ranking engine."""
from __future__ import annotations

import math
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
FUTURE_FIELDS = {"pickup_time", "pickup_gps_time", "pickup_gps_lng", "pickup_gps_lat", "label", "target", "off_window", "actual_duration", "completed_at"}
TOP_FIELDS = {"snapshot_time", "review_budget_fraction", "target_task_ids", "tasks"}
TASK_FIELDS = {"task_id", "courier_key", "accepted_at", "window_start", "window_end", "region_id", "aoi_key", "aoi_type", "lng", "lat", "accept_gps_lng", "accept_gps_lat", "prior_courier_accepts_day", "prior_aoi_accepts_day", "is_pending"}
REQUIRED_TASK = {"task_id", "courier_key", "accepted_at", "window_start", "window_end", "region_id", "aoi_key", "aoi_type", "lng", "lat", "is_pending"}


class SnapshotError(ValueError):
    """Fail-closed snapshot validation error."""


def parse_timestamp(value) -> pd.Timestamp:
    try:
        parsed = pd.Timestamp(value)
    except Exception as exc:
        raise SnapshotError(f"invalid timestamp: {value}") from exc
    if pd.isna(parsed):
        raise SnapshotError(f"invalid timestamp: {value}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("UTC").tz_localize(None)
    return parsed


def haversine(lon1, lat1, lon2, lat2):
    if not all(np.isfinite([lon1, lat1, lon2, lat2])):
        return np.nan
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return float(6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1))))


def validate_snapshot(snapshot: dict) -> None:
    if not isinstance(snapshot, dict):
        raise SnapshotError("snapshot must be an object")
    if set(snapshot) != TOP_FIELDS:
        raise SnapshotError(f"top-level fields must be exactly {sorted(TOP_FIELDS)}")
    if snapshot["review_budget_fraction"] != 0.1:
        raise SnapshotError("review_budget_fraction must equal 0.1")
    now = parse_timestamp(snapshot["snapshot_time"])
    targets = list(map(str, snapshot["target_task_ids"]))
    if not targets or len(targets) != len(set(targets)):
        raise SnapshotError("target_task_ids must be nonempty and unique")
    seen, tasks = set(), {}
    for task in snapshot["tasks"]:
        future = set(task) & FUTURE_FIELDS
        if future:
            raise SnapshotError(f"forbidden future/outcome fields: {sorted(future)}")
        unknown = set(task) - TASK_FIELDS
        if unknown:
            raise SnapshotError(f"unknown task fields: {sorted(unknown)}")
        missing = REQUIRED_TASK - set(task)
        if missing:
            raise SnapshotError(f"missing task fields: {sorted(missing)}")
        key = str(task["task_id"])
        if key in seen:
            raise SnapshotError(f"duplicate task_id: {key}")
        seen.add(key); tasks[key] = task
        accepted = parse_timestamp(task["accepted_at"])
        start, end = parse_timestamp(task["window_start"]), parse_timestamp(task["window_end"])
        if accepted > now:
            raise SnapshotError(f"task {key} accepted after snapshot")
        if start > end or accepted > end:
            raise SnapshotError(f"task {key} has invalid/actionably expired window")
        if task["is_pending"] is not True:
            raise SnapshotError(f"task {key} is not pending")
    if not set(targets).issubset(seen):
        raise SnapshotError("target_task_ids must exist in tasks")
    for key in targets:
        task = tasks[key]
        if parse_timestamp(task["accepted_at"]) != now:
            raise SnapshotError(f"target {key} must be scored at acceptance")
        for name in ["prior_courier_accepts_day", "prior_aoi_accepts_day"]:
            if task.get(name) is None or int(task[name]) < 0:
                raise SnapshotError(f"target {key} requires nonnegative {name}")


def build_features(snapshot: dict) -> tuple[pd.DataFrame, list[str]]:
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
        }); ids.append(task_id)
    return pd.DataFrame(rows, columns=FEATURES), ids


class KairosRanker:
    def __init__(self, model_path: str | Path):
        self.model = CatBoostClassifier()
        self.model.load_model(str(model_path))

    def score(self, snapshot: dict) -> list[dict]:
        features, ids = build_features(snapshot)
        scores = self.model.predict_proba(features)[:, 1]
        order = sorted(range(len(ids)), key=lambda i: (-scores[i], ids[i]))
        ranks = {idx: rank for rank, idx in enumerate(order, 1)}
        budget = max(1, math.ceil(0.1 * len(ids)))
        output = []
        for i, task_id in enumerate(ids):
            output.append({
                "task_id": task_id,
                "decision": "WINDOW_REVIEW" if ranks[i] <= budget else "KEEP_ASSIGNMENT",
                "rank": ranks[i], "priority": ranks[i], "risk_score": round(float(scores[i]), 10),
                "evidence_signals": [
                    {"signal": "slack_to_end_h", "value": round(float(features.at[i, "slack_to_end_h"]), 3)},
                    {"signal": "pending_other_count", "value": int(features.at[i, "pending_other_count"])},
                    {"signal": "pending_overlap_count", "value": int(features.at[i, "pending_overlap_count"])},
                ],
                "explanation_notice": "Non-causal model risk signals; dispatcher owns the decision.",
            })
        return sorted(output, key=lambda x: x["rank"])

