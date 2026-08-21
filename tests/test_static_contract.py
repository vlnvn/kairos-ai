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
            "Invalid JSON",
            "Snapshot rejected",
            "verified model is unavailable",
            "8 MiB local-demo limit",
            "Scoring accepted pickup promises",
        ):
            with self.subTest(state=state):
                self.assertIn(state, SCRIPT)

    def test_queue_uses_real_buttons_and_accessible_filters(self):
        self.assertIn("document.createElement('button')", SCRIPT)
        self.assertIn("aria-current", SCRIPT)
        self.assertIn("aria-pressed", HTML)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("prefers-reduced-motion", STYLES)

    def test_responsive_contract_has_desktop_tablet_and_mobile_rules(self):
        widths = [int(value) for value in re.findall(r"max-width:(\d+)px", STYLES)]
        self.assertTrue(any(width >= 900 for width in widths))
        self.assertTrue(any(width <= 700 for width in widths))


if __name__ == "__main__":
    unittest.main()
