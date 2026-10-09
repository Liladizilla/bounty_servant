# Bounty Servant

**A daily radar for software-development bounties hiding in GitHub issues.**

Bounty Servant searches open GitHub issues for bounty, reward, paid-task, and cash-payout signals. It ranks candidates, flags stale or possibly claimed offers, and creates a Markdown report plus JSON data you can inspect from your phone.

## What it does

- Runs 14 overlapping GitHub issue searches and deduplicates results.
- Scores reward evidence, bounty wording, labels, recency, and comment count.
- Flags issues not updated in more than 90 days.
- Flags text that may indicate a bounty has already been claimed or paid.
- Flags dangerous requests for upfront payments or secrets.
- Generates a ranked Markdown report and JSON file.
- Runs daily at **07:17 East Africa Time**, with a manual run option.
- Uploads reports as workflow artifacts for 30 days.
- Can send a short Telegram alert when you configure two GitHub Actions secrets.

## Enable Telegram alerts

1. In Telegram, open the official @BotFather account and create a bot with /newbot.
2. Copy the bot token and keep it private.
3. Open your new bot and press Start.
4. Obtain your numeric chat ID using a trusted Telegram bot/API method. Do not share your bot token publicly.
5. In this repository, open Settings → Secrets and variables → Actions → New repository secret.
6. Add TELEGRAM_BOT_TOKEN with the token and TELEGRAM_CHAT_ID with your chat ID.
7. Run the workflow manually from Actions → Bounty Servant Daily Radar → Run workflow.

Until both secrets exist, the Telegram step safely skips sending. Never put the token directly in a code file or issue.

## Important limitations

GitHub has no universal complete bounty registry. This tool finds discoverable candidates, not every bounty on the internet. A detected amount is text evidence, not proof that a reward is funded or payable. Automated claimed/paid warnings are heuristics and can be wrong. Always inspect the issue and its newest comments.

External board links in the report are a manual verification directory, not live API integrations. Platform APIs, access policies, and availability change.

## Run locally

Requires Python 3.10+; no third-party packages are needed.

Run the script with: python bounty_servant.py

For higher GitHub API limits, set GITHUB_TOKEN in your environment. Never paste tokens into source files or commit them.

## Daily automation

The workflow file at .github/workflows/daily.yml runs at 04:17 UTC (07:17 in Kenya). Start it manually from Actions → Bounty Servant Daily Radar → Run workflow.

Open a workflow run to read the summary or download its report artifact. GitHub may delay scheduled runs during periods of high load.

## Current scope

Version 0.3 searches GitHub issues, flags stale/claimed/risky signals, and can send optional Telegram alerts. It does not submit proposals, comment on issues, claim bounties, or perform work automatically. Those actions remain under your control.
