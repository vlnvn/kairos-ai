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
from kairos_ai.engine import FEATURES, KairosRanker, SnapshotError, build_features, parse_timestamp


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
        bad = copy.deepcopy(self.snapshot); bad["tasks"][0]["pickup_time"] = "2024-06-22T08:00:00"
        with self.assertRaisesRegex(SnapshotError, "forbidden future/outcome"):
            self.ranker.score(bad)

    def test_feature_schema_and_causal_context(self):
        frame, ids = build_features(self.snapshot)
        self.assertEqual(frame.columns.tolist(), FEATURES)
        self.assertEqual(len(frame), len(ids))
        self.assertFalse({"pickup_time", "courier_id", "aoi_id", "target"} & set(frame.columns))
        self.assertTrue((frame.pending_other_count >= 0).all())

    def test_ranking_budget_and_output_schema(self):
        result = self.ranker.score(self.snapshot)
        self.assertEqual(len(result), 134)
        self.assertEqual(sum(x["decision"] == "WINDOW_REVIEW" for x in result), 14)
        self.assertEqual([x["rank"] for x in result], list(range(1, 135)))
        self.assertTrue({"task_id", "decision", "rank", "risk_score", "evidence_signals"}.issubset(result[0]))

    def test_deterministic_inference(self):
        first = json.dumps(self.ranker.score(self.snapshot), sort_keys=True)
        second = json.dumps(self.ranker.score(self.snapshot), sort_keys=True)
        self.assertEqual(hashlib.sha256(first.encode()).hexdigest(), hashlib.sha256(second.encode()).hexdigest())

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
