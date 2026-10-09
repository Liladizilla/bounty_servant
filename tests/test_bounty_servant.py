import unittest
from datetime import datetime, timezone

from bounty_servant import classify_reward, extract_reward, score_issue


class RewardDetectionTests(unittest.TestCase):
    def test_detects_dollar_amount(self):
        self.assertEqual(extract_reward("Reward: $250 for the fix"), "$250")

    def test_detects_crypto_amount(self):
        self.assertEqual(extract_reward("Payout is 150 USDC after merge"), "150 USDC")

    def test_detects_rtc_bounty_amount(self):
        self.assertEqual(extract_reward("BOUNTY: 2 RTC"), "2 RTC")

    def test_bare_bounty_number_is_not_proof_of_payout(self):
        self.assertIsNone(extract_reward("BOUNTY: 2"))
        status, amount = classify_reward("Fix bug", "BOUNTY: 2", ["bounty"])
        self.assertEqual(status, "Potential bounty; payout amount unverified")
        self.assertIsNone(amount)

    def test_bounty_label_is_not_proof_of_amount(self):
        status, amount = classify_reward("Fix bug", "Bounty available", ["bounty"])
        self.assertEqual(status, "Potential bounty; payout amount unverified")
        self.assertIsNone(amount)

    def test_no_reward_evidence_is_flagged(self):
        status, amount = classify_reward("Improve docs", "Some cleanup", [])
        self.assertEqual(status, "Needs manual verification")
        self.assertIsNone(amount)

    def test_scoring_rewards_explicit_amount(self):
        base = {
            "title": "Fix parser",
            "body": "The issue needs a fix.",
            "labels": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "comments": 2,
        }
        paid = {**base, "body": "A $100 bounty is available for a merged fix."}
        self.assertGreater(score_issue(paid)[0], score_issue(base)[0])


if __name__ == "__main__":
    unittest.main()
