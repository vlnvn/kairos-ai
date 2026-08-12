"""Verify the frozen KAIROS AI release boundary without retraining."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from importlib.metadata import version
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
EXPECTED_FEATURE_SCHEMA_SHA256 = "b36985270b8ff9659fb5750c56eebefb58cb54bbcb6279e7346c2e3895deb7df"
EXPECTED_VERSIONS = {"catboost": "1.2.10", "numpy": "2.3.5", "pandas": "3.0.1"}


def normalized_output(result: list[dict]) -> bytes:
    return json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def main() -> int:
    checks: dict[str, bool] = {}
    try:
        model_path = ROOT / "artifacts" / "kairos_final.cbm"
        manifest = json.loads((ROOT / "artifacts" / "manifest.json").read_text(encoding="utf-8"))
        release_manifest = json.loads(
            (ROOT / "artifacts" / "ai_release_manifest.json").read_text(encoding="utf-8")
        )
        snapshot = json.loads((ROOT / "examples" / "input_snapshot.json").read_text(encoding="utf-8"))

        model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
        checks["model_sha"] = model_sha == EXPECTED_MODEL_SHA256
        checks["feature_count"] = len(FEATURES) == 21
        checks["manifest_features"] = manifest["features"] == FEATURES
        feature_schema_bytes = json.dumps(
            FEATURES, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        checks["feature_schema_sha"] = (
            hashlib.sha256(feature_schema_bytes).hexdigest()
            == EXPECTED_FEATURE_SCHEMA_SHA256
        )
        checks["python_version"] = sys.version_info >= (3, 11)
        checks["dependency_versions"] = all(
            version(package) == expected
            for package, expected in EXPECTED_VERSIONS.items()
        )
        checks["release_manifest"] = (
            release_manifest["production_artifact"]["sha256"] == EXPECTED_MODEL_SHA256
            and release_manifest["production_artifact"]["feature_count"] == 21
            and release_manifest["regression"]["canonical_golden_sha256"]
            == EXPECTED_GOLDEN_SHA256
        )

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
