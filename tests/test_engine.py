from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kairos_ai.engine import (
    EXPECTED_MODEL_SHA256,
    FEATURES,
    KairosRanker,
    ModelArtifactError,
    SnapshotError,
    build_features,
    parse_timestamp,
    verify_model_artifact,
)

EXPECTED_FEATURES = [
    "slack_to_start_h", "slack_to_end_h", "window_width_h", "accept_hour_sin",
    "accept_hour_cos", "day_of_week", "task_lng", "task_lat",
    "accept_to_task_km", "accept_gps_missing", "prior_courier_accepts_day",
    "prior_aoi_accepts_day", "pending_other_count", "pending_same_aoi_count",
    "pending_due_before_count", "pending_overlap_count", "oldest_pending_age_h",
    "pending_centroid_distance_km", "pending_location_missing", "region_id", "aoi_type",
]


class KairosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / "examples" / "input_snapshot.json").read_text(encoding="utf-8"))
        cls.ranker = KairosRanker(ROOT / "artifacts" / "kairos_final.cbm")

    def test_timestamp_and_window_parsing(self):
        self.assertEqual(parse_timestamp("2024-06-22T07:36:00").year, 2024)
        bad = copy.deepcopy(self.snapshot); bad["tasks"][0]["window_start"] = "not-a-time"
        with self.assertRaises(SnapshotError): build_features(bad)
        bad = copy.deepcopy(self.snapshot); bad["tasks"][0]["window_start"], bad["tasks"][0]["window_end"] = bad["tasks"][0]["window_end"], bad["tasks"][0]["window_start"]
        with self.assertRaises(SnapshotError): build_features(bad)

    def test_future_field_rejection(self):
        for field in (
            "pickup_time", "actual_pickup_timestamp", "pickup_gps_lng", "completed_at",
            "outcome", "violation", "route_realization",
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.snapshot)
                bad["tasks"][0][field] = "forbidden"
                with self.assertRaisesRegex(SnapshotError, "forbidden future/outcome"):
                    self.ranker.score(bad)

    def test_feature_schema_and_causal_context(self):
        frame, ids = build_features(self.snapshot)
        self.assertEqual(FEATURES, EXPECTED_FEATURES)
        self.assertEqual(frame.columns.tolist(), EXPECTED_FEATURES)
        self.assertEqual(len(EXPECTED_FEATURES), 21)
        self.assertTrue(frame["region_id"].map(lambda value: isinstance(value, str)).all())
        self.assertTrue(frame["aoi_type"].map(lambda value: isinstance(value, str)).all())
        self.assertEqual(self.ranker.model.feature_names_, EXPECTED_FEATURES)
        self.assertEqual(self.ranker.model.get_cat_feature_indices(), [19, 20])
        self.assertEqual(len(frame), len(ids))
        self.assertFalse({"pickup_time", "courier_id", "aoi_id", "target"} & set(frame.columns))
        self.assertTrue((frame.pending_other_count >= 0).all())

    def test_target_after_decision_timestamp_is_rejected(self):
        bad = copy.deepcopy(self.snapshot)
        target = next(task for task in bad["tasks"] if str(task["task_id"]) in bad["target_task_ids"])
        target["accepted_at"] = "2024-06-22T07:37:00"
        with self.assertRaisesRegex(SnapshotError, "accepted after snapshot"):
            self.ranker.score(bad)

    def test_context_after_decision_timestamp_is_rejected(self):
        bad = copy.deepcopy(self.snapshot)
        context = next(task for task in bad["tasks"] if str(task["task_id"]) not in bad["target_task_ids"])
        context["accepted_at"] = "2024-06-22T07:37:00"
        with self.assertRaisesRegex(SnapshotError, "accepted after snapshot"):
            self.ranker.score(bad)

    def test_ranking_budget_and_output_schema(self):
        result = self.ranker.score(self.snapshot)
        self.assertEqual(len(result), 134)
        self.assertEqual(sum(x["decision"] == "WINDOW_REVIEW" for x in result), 14)
        self.assertEqual([x["rank"] for x in result], list(range(1, 135)))
        self.assertTrue({"task_id", "decision", "rank", "risk_score", "evidence_signals"}.issubset(result[0]))

    def test_deterministic_inference(self):
        runs = [json.dumps(self.ranker.score(self.snapshot), sort_keys=True) for _ in range(3)]
        digests = {hashlib.sha256(run.encode()).hexdigest() for run in runs}
        self.assertEqual(len(digests), 1)

    def test_frozen_model_hash_is_enforced(self):
        model = ROOT / "artifacts" / "kairos_final.cbm"
        self.assertEqual(verify_model_artifact(model), model.resolve())
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(), EXPECTED_MODEL_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            modified = Path(tmp) / "kairos_final.cbm"
            data = bytearray(model.read_bytes())
            data[-1] ^= 1
            modified.write_bytes(data)
            with self.assertRaisesRegex(ModelArtifactError, "SHA-256 mismatch"):
                KairosRanker(modified)

    def test_cli_integration(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.json"
            env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT / "src")
            subprocess.run([sys.executable, "-m", "kairos_ai.cli", str(ROOT / "examples" / "input_snapshot.json"), "--model", str(ROOT / "artifacts" / "kairos_final.cbm"), "--output", str(output)], check=True, env=env)
            scored = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(scored), 134)
            self.assertEqual(scored[0]["decision"], "WINDOW_REVIEW")


if __name__ == "__main__":
    unittest.main()
