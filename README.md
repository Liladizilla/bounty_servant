# Bounty Servant

**A daily radar for software-development bounties hiding in GitHub issues.**

Bounty Servant searches open GitHub issues for bounty, reward, paid-task, and cash-payout signals. It ranks candidates and creates a Markdown report you can inspect from your phone.

## What it does

- Searches several GitHub issue queries and deduplicates results.
- Scores issues using reward evidence, bounty-related wording, recency, labels, and comment count.
- Separates **payout evidence found** from **potential bounty / unverified payout**.
- Produces a Markdown report and JSON data file.
- Runs daily at **07:17 East Africa Time** using GitHub Actions, plus a manual **Run workflow** option.
- Uploads each run's report as a downloadable workflow artifact.

## Important limitation

GitHub does not have one universal, complete bounty registry. This tool finds *discoverable candidates*, not every bounty on the internet. Search results can include false positives, and a mention of money is not a guarantee that a maintainer will pay. Read the original issue, bounty terms, eligibility rules, and payout method before doing work.

## Run it locally

Requires Python 3.10+; no third-party packages are needed.

```bash
python bounty_servant.py
```

For higher GitHub API limits, set a token in your environment. Never paste tokens into source files or commit them.

Linux/macOS:
```bash
export GITHUB_TOKEN="your-token"
python bounty_servant.py
```

Windows PowerShell:
```powershell
$env:GITHUB_TOKEN="your-token"
python bounty_servant.py
```

Without a token, GitHub's unauthenticated API limits are lower.

## Daily automation

The workflow at `.github/workflows/daily.yml` runs at 04:17 UTC (07:17 in Kenya), and can also be started manually from **Actions → Bounty Servant Daily Radar → Run workflow**.

Open a workflow run to read its summary or download the `bounty-servant-report` artifact. GitHub may delay scheduled runs during periods of high load.

## Current scope

Version 0.1 searches GitHub issues only. It does not submit proposals, comment on issues, claim bounties, or perform work automatically. Those actions should remain under your control.
