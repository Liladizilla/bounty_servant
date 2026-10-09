# Bounty Servant

**A daily radar for software-development bounties hiding in GitHub issues.**

Bounty Servant searches open GitHub issues for bounty, reward, paid-task, and cash-payout signals. It ranks candidates, flags stale or possibly claimed offers, and creates a Markdown report plus JSON data that you can inspect from your phone.

## What it does

- Runs 14 overlapping GitHub issue searches and deduplicates results.
- Scores reward evidence, bounty wording, labels, recency, and comment count.
- Flags issues that have not been updated in more than 90 days.
- Flags text that may indicate a bounty has already been claimed or paid.
- Flags dangerous requests for upfront payments or secrets.
- Generates a ranked Markdown report and JSON file.
- Runs daily at **07:17 East Africa Time** using GitHub Actions, plus a manual run option.
- Uploads reports as workflow artifacts for 30 days.

## Important limitations

GitHub has no universal complete bounty registry. This tool finds discoverable candidates, not every bounty on the internet. A detected amount is only text evidence, not proof that a reward is funded or payable. Automated claimed/paid warnings are heuristics and can be wrong. Always inspect the issue and its newest comments.

External board links are included as a manual verification directory only. They are **not** represented as live API integrations because platform APIs, access policies, and availability change.

## Run locally

Requires Python 3.10+; no third-party packages are needed.

Run: `python bounty_servant.py`

For higher GitHub API limits, set a token in your environment. Never paste tokens into source files or commit them.

Linux/macOS: `export GITHUB_TOKEN="your-token"`

Windows PowerShell: `$env:GITHUB_TOKEN="your-token"`

## Daily automation

The workflow file at .github/workflows/daily.yml runs at 04:17 UTC (07:17 in Kenya). Start it manually from Actions → Bounty Servant Daily Radar → Run workflow.

Open a workflow run to read the summary or download its report artifact. GitHub may delay scheduled runs during periods of high load.

## Current scope

Version 0.2 searches GitHub issues and includes links to external bounty boards for manual checking. It does not submit proposals, comment on issues, claim bounties, or perform work automatically. Those actions remain under your control.
