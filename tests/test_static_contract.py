from __future__ import annotations

import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")


class StaticProductContractTests(unittest.TestCase):
    def test_assets_are_external_and_csp_compatible(self):
        self.assertIn('href="/styles.css"', HTML)
        self.assertIn('src="/app.js"', HTML)
        self.assertNotRegex(HTML, r"<style(?:\s|>)")
        self.assertNotRegex(HTML, r"<script(?![^>]+src=)")
        self.assertNotRegex(HTML, r"\son[a-z]+=")

    def test_product_does_not_render_score_or_worker_identifiers(self):
        product = (HTML + SCRIPT).lower()
        forbidden = (
            "risk_score",
            "review_score",
            "courier_key",
            "courier id",
            "worker score",
            "failure chance",
            "risk percentage",
            "confidence",
            "likelihood",
            "probability",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, product)

    def test_dom_rendering_avoids_html_injection_sinks(self):
        self.assertNotIn("innerHTML", SCRIPT)
        self.assertNotIn("insertAdjacentHTML", SCRIPT)
        self.assertIn("textContent", SCRIPT)

    def test_primary_workflow_and_status_states_exist(self):
        self.assertIn("Protect Promises", HTML)
        self.assertEqual(HTML.count('id="run"'), 1)
        self.assertIn('aria-live="polite"', HTML)
        for state in (
            "INVALID JSON",
            "INVALID SNAPSHOT",
            "MODEL UNAVAILABLE",
            "FUTURE DATA REJECTED",
            "8 MiB local-demo limit",
            "real request duration",
        ):
            with self.subTest(state=state):
                self.assertIn(state, SCRIPT)

    def test_queue_and_focus_use_semantic_controls(self):
        self.assertIn("document.createElement('button')", SCRIPT)
        self.assertIn('id="back-to-queue"', HTML)
        self.assertIn("input.type = 'radio'", SCRIPT)
        self.assertIn("label.dataset.selected", SCRIPT)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("prefers-reduced-motion", STYLES)

    def test_manifest_instrument_and_mode_transition_are_explicit(self):
        self.assertIn("promise-instrument", SCRIPT)
        self.assertIn("promise-axis", SCRIPT)
        self.assertIn("accepted-label", SCRIPT)
        self.assertIn("showTaskFocus", SCRIPT)
        self.assertIn("showOnly('focus')", SCRIPT)
        self.assertNotIn("setTimeout", SCRIPT)

    def test_capacity_changes_cutoff_through_real_request(self):
        self.assertIn("snapshot.review_budget_fraction = capacity", SCRIPT)
        self.assertIn("if (wasOutput)", SCRIPT)
        self.assertIn("runScoring();", SCRIPT)

    def test_capacity_counts_follow_the_loaded_target_count(self):
        capacity_block = SCRIPT.split("const CAPACITIES =", 1)[1].split("];", 1)[0]
        for canonical_count in ("7 tasks", "14 tasks", "27 tasks", "134 tasks"):
            self.assertNotIn(canonical_count, capacity_block)
        self.assertIn("Math.max(1, Math.ceil(fraction * totalTargets))", SCRIPT)
        self.assertIn("snapshot.target_task_ids.length", SCRIPT)
        self.assertIn("metadata.total_targets", SCRIPT)
        self.assertIn("count === 1 ? 'task' : 'tasks'", SCRIPT)
        self.assertIn("`${count} ${unit}`", SCRIPT)
        self.assertNotIn("option.count", SCRIPT)
        synthetic_total = 11
        self.assertEqual(
            [max(1, math.ceil(fraction * synthetic_total)) for fraction in (0.05, 0.1, 0.2, 1)],
            [1, 2, 3, 11],
        )
        self.assertNotEqual([1, 2, 3, 11], [7, 14, 27, 134])

    def test_cross_date_promise_windows_render_both_dates(self):
        self.assertIn("startDate: start.slice(0, 2).join(' ')", SCRIPT)
        self.assertIn("endDate: end.slice(0, 2).join(' ')", SCRIPT)
        self.assertIn("parts.startDate === parts.endDate", SCRIPT)
        self.assertIn("`${parts.endDate} ${parts.end}`", SCRIPT)

    def test_product_ui_has_no_stale_release_sha(self):
        self.assertNotIn("6d42fbbe", HTML + SCRIPT)

    def test_responsive_contract_has_desktop_tablet_and_mobile_rules(self):
        widths = [int(value) for value in re.findall(r"max-width:(\d+)px", STYLES)]
        self.assertTrue(any(width >= 900 for width in widths))
        self.assertTrue(any(width <= 700 for width in widths))


if __name__ == "__main__":
    unittest.main()
