import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_metrics_history import make_snapshot, update_history


class MetricsHistoryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc)  # 12:00 Nairobi
        self.ledger = {"opportunities": {
            "a": {"first_seen": "2026-10-09T08:00:00+00:00", "last_score": 18, "verification": "verified_paid_candidate", "status": "discovered"},
            "b": {"first_seen": "2026-10-08T20:00:00+00:00", "last_score": 6, "verification": "needs_manual_review", "status": "submitted"},
            "c": {"first_seen": "2026-10-08T19:00:00+00:00", "last_score": 2, "verification": "not_verified", "status": "paid"},
        }}

    def test_snapshot_counts_real_ledger_fields(self):
        result = make_snapshot(self.ledger, self.now)
        self.assertEqual(result["date"], "2026-10-09")
        self.assertEqual(result["tracked_opportunities"], 3)
        self.assertEqual(result["new_first_seen_today"], 1)
        self.assertEqual(result["verification_counts"]["verified_paid_candidate"], 1)
        self.assertEqual(result["status_counts"]["paid"], 1)
        self.assertEqual(result["score_distribution"]["15_19"], 1)
        self.assertEqual(result["average_score"], 8.67)

    def test_repeated_run_updates_same_day_without_duplicate(self):
        first = update_history(self.ledger, None, self.now)
        later = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)
        second = update_history(self.ledger, first, later)
        self.assertEqual(len(second["snapshots"]), 1)
        self.assertEqual(second["snapshots"][0]["updated_at"], later.isoformat())

    def test_history_is_sorted_and_retains_latest_365_days(self):
        old = [{"date": f"2025-01-{i:02d}", "tracked_opportunities": i} for i in range(1, 29)]
        history = update_history(self.ledger, {"snapshots": old}, self.now)
        dates = [item["date"] for item in history["snapshots"]]
        self.assertEqual(dates, sorted(dates))
        self.assertLessEqual(len(dates), 365)
        self.assertEqual(dates[-1], "2026-10-09")


if __name__ == "__main__":
    unittest.main()
