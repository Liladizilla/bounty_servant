import unittest
from datetime import datetime, timedelta, timezone

from bounty_servant import classify_reward, extract_reward, has_positive_reward, score_issue, status_flags


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
        self.assertEqual(status, "Potential bounty; amount unverified")
        self.assertIsNone(amount)

    def test_bounty_label_is_not_proof_of_amount(self):
        status, amount = classify_reward("Fix bug", "Bounty available", ["bounty"])
        self.assertEqual(status, "Potential bounty; amount unverified")
        self.assertIsNone(amount)

    def test_no_reward_evidence_is_flagged(self):
        status, amount = classify_reward("Improve docs", "Some cleanup", [])
        self.assertEqual(status, "Needs manual verification")
        self.assertIsNone(amount)

    def test_stale_issue_gets_warning(self):
        old = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
        flags = status_flags({"updated_at": old}, "A bounty exists")
        self.assertTrue(any("Stale" in flag for flag in flags))

    def test_claimed_signal_gets_warning(self):
        flags = status_flags({}, "The bounty has been claimed by @developer")
        self.assertTrue(any("claimed/paid" in flag for flag in flags))

    def test_upfront_fee_gets_risk_warning(self):
        flags = status_flags({}, "Pay an upfront fee to participate")
        self.assertTrue(any("Risk signal" in flag for flag in flags))

    def test_claimed_candidate_scores_lower(self):
        recent = datetime.now(timezone.utc).isoformat()
        base = {"title": "Fix parser bounty", "body": "A $100 reward is available.", "labels": [],
                "updated_at": recent, "comments": 2}
        claimed = {**base, "body": "A $100 reward is available. The bounty has been claimed."}
        self.assertLess(score_issue(claimed)[0], score_issue(base)[0])

    def test_zero_dollar_reward_is_not_positive(self):
        self.assertFalse(has_positive_reward("$0"))
        self.assertTrue(has_positive_reward("$25"))


if __name__ == "__main__":
    unittest.main()
