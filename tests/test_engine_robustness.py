from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import kairos_ai.engine as engine
from kairos_ai.engine import (
    FUTURE_FIELDS,
    KairosRanker,
    ModelArtifactError,
    SnapshotError,
    build_features,
)

GOLDEN_SHA256 = "f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8"
APPROVED_SIGNALS = {"slack_to_end_h", "pending_other_count", "pending_overlap_count"}


def canonical_bytes(result: list[dict]) -> bytes:
    return json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class EngineRobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(
            (ROOT / "examples" / "input_snapshot.json").read_text(encoding="utf-8")
        )
        cls.model_path = ROOT / "artifacts" / "kairos_final.cbm"
        cls.ranker = KairosRanker(cls.model_path)
        cls.target_id = str(cls.snapshot["target_task_ids"][0])

    def target(self, snapshot: dict | None = None) -> dict:
        snapshot = snapshot or self.snapshot
        targets = set(map(str, snapshot["target_task_ids"]))
        return next(task for task in snapshot["tasks"] if str(task["task_id"]) in targets)

    def context(self, snapshot: dict | None = None) -> dict:
        snapshot = snapshot or self.snapshot
        targets = set(map(str, snapshot["target_task_ids"]))
        return next(task for task in snapshot["tasks"] if str(task["task_id"]) not in targets)

    def assert_snapshot_error(self, snapshot) -> None:
        with self.assertRaises(SnapshotError):
            self.ranker.score(snapshot)

    def test_top_level_type_and_field_failures_are_closed(self):
        for value in (None, [], "snapshot"):
            with self.subTest(value=value):
                self.assert_snapshot_error(value)
        for field in self.snapshot:
            with self.subTest(missing=field):
                bad = copy.deepcopy(self.snapshot)
                del bad[field]
                self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["extra"] = True
        self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["review_budget_fraction"] = 10 ** 1000
        self.assert_snapshot_error(bad)

    def test_target_task_ids_container_and_normalization(self):
        for value in (None, 7, "1009620", {}, []):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.snapshot)
                bad["target_task_ids"] = value
                self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        numeric_id = int(self.target_id)
        bad["target_task_ids"] = [numeric_id, str(numeric_id)]
        self.assert_snapshot_error(bad)

    def test_tasks_container_and_non_object_failures_are_closed(self):
        for value in (None, 7, "tasks", {}, []):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.snapshot)
                bad["tasks"] = value
                self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["tasks"][0] = "not-an-object"
        self.assert_snapshot_error(bad)

    def test_task_schema_duplicates_and_missing_target(self):
        required = {
            "task_id", "courier_key", "accepted_at", "window_start", "window_end",
            "region_id", "aoi_key", "aoi_type", "lng", "lat", "is_pending",
        }
        for field in required:
            with self.subTest(missing=field):
                bad = copy.deepcopy(self.snapshot)
                del bad["tasks"][0][field]
                self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["tasks"][0]["unknown"] = 1
        self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["tasks"][1]["task_id"] = bad["tasks"][0]["task_id"]
        self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["target_task_ids"][0] = "absent-target"
        self.assert_snapshot_error(bad)

    def test_pending_flag_is_strict_boolean_true(self):
        for value in (False, None, 1, "true"):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.snapshot)
                self.target(bad)["is_pending"] = value
                self.assert_snapshot_error(bad)

    def test_timestamp_and_window_failures_are_closed(self):
        for value in (None, 0, "NaT", "not-a-time", "999999-01-01T00:00:00"):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.snapshot)
                bad["snapshot_time"] = value
                self.assert_snapshot_error(bad)
        for field in ("accepted_at", "window_start", "window_end"):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.snapshot)
                self.context(bad)[field] = "not-a-time"
                self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        task = self.context(bad)
        task["window_start"], task["window_end"] = task["window_end"], task["window_start"]
        self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        task = self.context(bad)
        task["accepted_at"] = bad["snapshot_time"]
        task["window_start"] = "2024-06-22T06:00:00"
        task["window_end"] = "2024-06-22T07:00:00"
        self.assert_snapshot_error(bad)

    def test_numeric_and_geospatial_failures_are_closed(self):
        cases = {
            "lng": ("121", float("nan"), float("inf"), float("-inf"), True, 180.01, -180.01, 10 ** 1000),
            "lat": ("37", float("nan"), float("inf"), float("-inf"), True, 90.01, -90.01),
            "accept_gps_lng": ("121", float("nan"), float("inf"), True, 181),
            "accept_gps_lat": ("37", float("nan"), float("-inf"), True, -91),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    bad = copy.deepcopy(self.snapshot)
                    task = self.target(bad)
                    if field.startswith("accept_gps"):
                        task["accept_gps_lng"] = 121.0
                        task["accept_gps_lat"] = 37.0
                    task[field] = value
                    self.assert_snapshot_error(bad)
        bad = copy.deepcopy(self.snapshot)
        task = self.target(bad)
        task["accept_gps_lng"], task["accept_gps_lat"] = 121.0, None
        self.assert_snapshot_error(bad)

    def test_counter_failures_are_closed_without_coercion(self):
        invalid = ("1", float("nan"), float("inf"), float("-inf"), True, -1, 1.5, 10 ** 1000)
        for field in ("prior_courier_accepts_day", "prior_aoi_accepts_day"):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    bad = copy.deepcopy(self.snapshot)
                    self.target(bad)[field] = value
                    self.assert_snapshot_error(bad)

    def test_task_array_permutation_is_byte_invariant(self):
        bad = copy.deepcopy(self.snapshot)
        random.Random(20260810).shuffle(bad["tasks"])
        self.assertEqual(
            canonical_bytes(self.ranker.score(self.snapshot)),
            canonical_bytes(self.ranker.score(bad)),
        )

    def test_target_input_order_is_byte_invariant(self):
        bad = copy.deepcopy(self.snapshot)
        bad["target_task_ids"].reverse()
        self.assertEqual(
            canonical_bytes(self.ranker.score(self.snapshot)),
            canonical_bytes(self.ranker.score(bad)),
        )

    def test_unrelated_courier_context_is_invariant(self):
        bad = copy.deepcopy(self.snapshot)
        unrelated = copy.deepcopy(self.context(bad))
        unrelated["task_id"] = "unrelated-context"
        unrelated["courier_key"] = "unrelated-courier"
        bad["tasks"].append(unrelated)
        self.assertEqual(
            canonical_bytes(self.ranker.score(self.snapshot)),
            canonical_bytes(self.ranker.score(bad)),
        )

    def test_capacity_changes_only_decisions(self):
        baseline = self.ranker.score(self.snapshot)
        for fraction in (0.01, 0.5, 1.0):
            with self.subTest(fraction=fraction):
                changed = copy.deepcopy(self.snapshot)
                changed["review_budget_fraction"] = fraction
                result = self.ranker.score(changed)
                for expected, actual in zip(baseline, result):
                    expected_without_decision = {k: v for k, v in expected.items() if k != "decision"}
                    actual_without_decision = {k: v for k, v in actual.items() if k != "decision"}
                    self.assertEqual(expected_without_decision, actual_without_decision)
                expected_count = max(1, math.ceil(fraction * len(result)))
                self.assertEqual(
                    sum(item["decision"] == "WINDOW_REVIEW" for item in result),
                    expected_count,
                )

    def test_timezone_equivalent_request_is_byte_invariant(self):
        equivalent = copy.deepcopy(self.snapshot)

        def shift(value: str) -> str:
            return engine.parse_timestamp(value).tz_localize("UTC").tz_convert("-07:00").isoformat()

        equivalent["snapshot_time"] = shift(equivalent["snapshot_time"])
        for task in equivalent["tasks"]:
            for field in ("accepted_at", "window_start", "window_end"):
                task[field] = shift(task[field])
        self.assertEqual(
            canonical_bytes(self.ranker.score(self.snapshot)),
            canonical_bytes(self.ranker.score(equivalent)),
        )

    def test_serialization_is_repeatable_and_golden(self):
        runs = [canonical_bytes(self.ranker.score(self.snapshot)) for _ in range(3)]
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[1], runs[2])
        self.assertEqual(hashlib.sha256(runs[0]).hexdigest(), GOLDEN_SHA256)

    def test_all_future_fields_rejected_on_target_and_context(self):
        for location in ("target", "context"):
            for field in sorted(FUTURE_FIELDS):
                with self.subTest(location=location, field=field):
                    bad = copy.deepcopy(self.snapshot)
                    task = self.target(bad) if location == "target" else self.context(bad)
                    task[field] = "forbidden"
                    self.assert_snapshot_error(bad)

    def test_model_absence_corruption_and_schema_drift_fail_before_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.cbm"
            with self.assertRaises(ModelArtifactError):
                KairosRanker(missing)
            modified = Path(tmp) / "modified.cbm"
            data = bytearray(self.model_path.read_bytes())
            data[-1] ^= 1
            modified.write_bytes(data)
            with self.assertRaises(ModelArtifactError):
                KairosRanker(modified)

        original = engine.FEATURES[:]
        try:
            engine.FEATURES[:] = list(reversed(original))
            with self.assertRaises(ModelArtifactError):
                self.ranker.score(self.snapshot)
            engine.FEATURES[:] = original[:-1] + [original[-2]]
            with self.assertRaises(ModelArtifactError):
                self.ranker.score(self.snapshot)
        finally:
            engine.FEATURES[:] = original

    def test_output_integrity_matches_raw_score_contract(self):
        features, ids = build_features(self.snapshot)
        raw_scores = self.ranker.model.predict_proba(features)[:, 1]
        expected_ids = [
            ids[index]
            for index in sorted(range(len(ids)), key=lambda i: (-raw_scores[i], ids[i]))
        ]
        result = self.ranker.score(self.snapshot)
        self.assertEqual([item["task_id"] for item in result], expected_ids)
        self.assertEqual(len(result), len(set(item["task_id"] for item in result)))
        self.assertEqual([item["rank"] for item in result], list(range(1, len(result) + 1)))
        self.assertTrue(all(item["priority"] == item["rank"] for item in result))
        self.assertTrue(all(math.isfinite(item["review_score"]) for item in result))
        budget = max(1, math.ceil(self.snapshot["review_budget_fraction"] * len(result)))
        self.assertTrue(all(item["decision"] == "WINDOW_REVIEW" for item in result[:budget]))
        self.assertTrue(all(item["decision"] == "KEEP_ASSIGNMENT" for item in result[budget:]))
        for item in result:
            self.assertEqual({signal["signal"] for signal in item["evidence_signals"]}, APPROVED_SIGNALS)
            self.assertNotIn("risk_score", item)
            self.assertNotIn("courier_key", item)

    def test_valid_edge_requests_score_deterministically(self):
        one = copy.deepcopy(self.snapshot)
        target = copy.deepcopy(self.target(one))
        one["target_task_ids"] = [str(target["task_id"])]
        one["tasks"] = [target]
        self.assertEqual(len(self.ranker.score(one)), 1)

        full = copy.deepcopy(one)
        full["review_budget_fraction"] = 1.0
        self.assertEqual(self.ranker.score(full)[0]["decision"], "WINDOW_REVIEW")

        no_gps = copy.deepcopy(one)
        no_gps["tasks"][0]["accept_gps_lng"] = None
        no_gps["tasks"][0]["accept_gps_lat"] = None
        self.assertEqual(self.ranker.score(no_gps), self.ranker.score(no_gps))

        same_courier = copy.deepcopy(self.snapshot)
        selected_ids = list(map(str, same_courier["target_task_ids"][:2]))
        selected = [
            task for task in same_courier["tasks"] if str(task["task_id"]) in selected_ids
        ]
        selected[1]["courier_key"] = selected[0]["courier_key"]
        same_courier["target_task_ids"] = selected_ids
        same_courier["tasks"] = selected
        self.assertEqual(len(self.ranker.score(same_courier)), 2)

        unknown_category = copy.deepcopy(one)
        unknown_category["tasks"][0]["region_id"] = "unknown-region"
        unknown_category["tasks"][0]["aoi_type"] = "unknown-aoi-type"
        self.assertEqual(len(self.ranker.score(unknown_category)), 1)

        unicode_id = copy.deepcopy(one)
        unicode_id["target_task_ids"] = ["tugas-雪-🚚"]
        unicode_id["tasks"][0]["task_id"] = "tugas-雪-🚚"
        result = self.ranker.score(unicode_id)
        self.assertEqual(result[0]["task_id"], "tugas-雪-🚚")


if __name__ == "__main__":
    unittest.main()
