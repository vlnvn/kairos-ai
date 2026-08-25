from __future__ import annotations

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

    def test_responsive_contract_has_desktop_tablet_and_mobile_rules(self):
        widths = [int(value) for value in re.findall(r"max-width:(\d+)px", STYLES)]
        self.assertTrue(any(width >= 900 for width in widths))
        self.assertTrue(any(width <= 700 for width in widths))


if __name__ == "__main__":
    unittest.main()
