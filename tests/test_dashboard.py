import os
import pathlib
import shutil
import subprocess
import unittest
from html.parser import HTMLParser

DASHBOARD = pathlib.Path(__file__).resolve().parents[1] / "docs" / "index.html"


class DashboardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = 0
        self.viewport = False
        self.table_headers = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "script":
            self.scripts += 1
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = True
        if tag == "th":
            self.table_headers += 1


class DashboardSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DASHBOARD.read_text(encoding="utf-8")
        cls.parser = DashboardParser()
        cls.parser.feed(cls.source)

    def test_html_has_responsive_viewport_and_semantic_structure(self):
        self.assertTrue(self.parser.viewport)
        self.assertIn("<main", self.source)
        self.assertIn("<table", self.source)
        self.assertGreaterEqual(self.parser.table_headers, 5)

    def test_dashboard_has_live_data_endpoints(self):
        self.assertIn("const LEDGER_URL", self.source)
        self.assertIn("data/ledger.json", self.source)
        self.assertIn("api.github.com/repos/", self.source)
        self.assertIn("/actions/runs?per_page=12", self.source)
        self.assertIn('cache:"no-store"', self.source)

    def test_metrics_and_interactions_exist(self):
        for element_id in ("total", "verified", "review", "paid", "trend", "scores",
                           "opportunityRows", "runSummary", "search", "export", "refresh"):
            self.assertIn(element_id, self.parser.ids)
        self.assertIn("addEventListener", self.source)
        self.assertIn("createObjectURL", self.source)

    def test_labels_do_not_claim_estimates_are_payments(self):
        self.assertIn("not payment proof", self.source)
        self.assertIn("not success probability", self.source)
        self.assertIn("Confirmed paid", self.source)
        self.assertIn("Dry-run remains enabled", self.source)

    def test_dashboard_is_self_contained(self):
        self.assertNotIn("https://cdn.jsdelivr.net", self.source)
        self.assertNotIn("https://unpkg.com", self.source)
        self.assertGreater(self.parser.scripts, 0)

    def test_dashboard_interactions_in_utc_and_western_timezone(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is not installed")
        harness = pathlib.Path(__file__).with_name("dashboard_behavior.cjs")
        for timezone in ("UTC", "America/Los_Angeles"):
            with self.subTest(timezone=timezone):
                env = {**os.environ, "TZ": timezone}
                result = subprocess.run(["node", str(harness)], env=env, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
