"""Tests for the safe bounty patch proposal helper."""
import unittest

from bounty_agent import AgentError, parse_issue_url, validate_patch


class BountyAgentTests(unittest.TestCase):
    def test_parses_public_issue_url(self):
        self.assertEqual(
            parse_issue_url("https://github.com/owner-name/repo.py/issues/42"),
            ("owner-name", "repo.py", 42),
        )

    def test_rejects_pull_request_url(self):
        with self.assertRaises(ValueError):
            parse_issue_url("https://github.com/owner/repo/pull/42")

    def test_rejects_non_github_url(self):
        with self.assertRaises(ValueError):
            parse_issue_url("https://example.com/owner/repo/issues/42")

    def test_accepts_simple_unified_diff(self):
        patch = (
            "diff --git a/src/example.py b/src/example.py\n"
            "--- a/src/example.py\n+++ b/src/example.py\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        self.assertEqual(validate_patch(patch), patch)

    def test_rejects_path_traversal(self):
        patch = (
            "diff --git a/../secrets.txt b/../secrets.txt\n"
            "--- a/../secrets.txt\n+++ b/../secrets.txt\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        with self.assertRaises(AgentError):
            validate_patch(patch)

    def test_rejects_workflow_edits(self):
        patch = (
            "diff --git a/.github/workflows/pwn.yml b/.github/workflows/pwn.yml\n"
            "--- a/.github/workflows/pwn.yml\n+++ b/.github/workflows/pwn.yml\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        with self.assertRaises(AgentError):
            validate_patch(patch)

    def test_rejects_non_diff_output(self):
        with self.assertRaises(AgentError):
            validate_patch("Here is a patch plan.")


if __name__ == "__main__":
    unittest.main()
