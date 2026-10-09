import unittest
from notify_telegram import build_message

class TelegramMessageTests(unittest.TestCase):
    def test_message_includes_top_candidate_and_link(self):
        message = build_message({
            "candidate_count": 1, "query_count": 14, "empty_or_failed_queries": 0,
            "candidates": [{
                "title": "Fix parser", "score": 12, "reward_evidence": "$100",
                "reward_status": "Amount detected; verify the offer and terms",
                "url": "https://github.com/example/project/issues/1", "flags": [],
            }],
        })
        self.assertIn("Fix parser", message)
        self.assertIn("$100", message)
        self.assertIn("https://github.com/example/project/issues/1", message)

    def test_empty_candidates_are_reported(self):
        message = build_message({
            "candidate_count": 0, "query_count": 14,
            "empty_or_failed_queries": 2, "candidates": [],
        })
        self.assertIn("No candidates surfaced today", message)

if __name__ == "__main__":
    unittest.main()
