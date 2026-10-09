import pathlib
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
        self.assertIn("raw.githubusercontent.com/Liladizilla/bounty_servant/main/data/ledger.json", self.source)
        self.assertIn("api.github.com/repos/Liladizilla/bounty_servant/actions/runs", self.source)
        self.assertIn("cache:\"no-store\"", self.source)

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


if __name__ == "__main__":
    unittest.main()
