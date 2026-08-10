"""Verify the frozen KAIROS AI release boundary without retraining."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kairos_ai.engine import (  # noqa: E402
    EXPECTED_MODEL_SHA256,
    FEATURES,
    FROZEN_CATEGORICAL_FEATURE_INDICES,
    KairosRanker,
    SnapshotError,
)

EXPECTED_GOLDEN_SHA256 = "f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8"


def normalized_output(result: list[dict]) -> bytes:
    return json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def main() -> int:
    checks: dict[str, bool] = {}
    try:
        model_path = ROOT / "artifacts" / "kairos_final.cbm"
        manifest = json.loads((ROOT / "artifacts" / "manifest.json").read_text(encoding="utf-8"))
        snapshot = json.loads((ROOT / "examples" / "input_snapshot.json").read_text(encoding="utf-8"))

        model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
        checks["model_sha"] = model_sha == EXPECTED_MODEL_SHA256
        checks["feature_count"] = len(FEATURES) == 21
        checks["manifest_features"] = manifest["features"] == FEATURES

        ranker = KairosRanker(model_path)
        checks["model_features"] = ranker.model.feature_names_ == FEATURES
        checks["categorical_indices"] = (
            tuple(ranker.model.get_cat_feature_indices())
            == FROZEN_CATEGORICAL_FEATURE_INDICES
        )

        first = ranker.score(snapshot)
        second = ranker.score(snapshot)
        first_bytes = normalized_output(first)
        checks["deterministic_repeat"] = first_bytes == normalized_output(second)
        checks["canonical_golden"] = hashlib.sha256(first_bytes).hexdigest() == EXPECTED_GOLDEN_SHA256

        forbidden = copy.deepcopy(snapshot)
        forbidden["tasks"][0]["actual_pickup_timestamp"] = "forbidden"
        try:
            ranker.score(forbidden)
            checks["future_field_rejection"] = False
        except SnapshotError:
            checks["future_field_rejection"] = True

        capacity_outputs = {}
        for fraction in (0.05, 0.1, 0.2):
            changed = copy.deepcopy(snapshot)
            changed["review_budget_fraction"] = fraction
            capacity_outputs[fraction] = ranker.score(changed)
        baseline = capacity_outputs[0.1]
        checks["capacity_ranking"] = all(
            [item["task_id"] for item in result] == [item["task_id"] for item in baseline]
            for result in capacity_outputs.values()
        )
        checks["capacity_scores"] = all(
            [item["review_score"] for item in result] == [item["review_score"] for item in baseline]
            for result in capacity_outputs.values()
        )
    except Exception:
        print(json.dumps({"result": "FAIL", "checks": checks}, sort_keys=True))
        return 1

    result = "PASS" if checks and all(checks.values()) else "FAIL"
    print(json.dumps({"result": result, "checks": checks}, sort_keys=True))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
