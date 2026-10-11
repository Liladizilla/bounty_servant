# Bounty Servant

**A daily, safety-first radar for software-development bounties hiding in GitHub issues.**

Bounty Servant searches open GitHub issues for bounty, reward, paid-task, and cash-payout signals. It ranks candidates, reads issue details and comments for the strongest results, flags stale/claimed/risky offers, maintains a durable ledger, and creates a Markdown report plus JSON data you can inspect from your phone.

## What it does

- Runs 14 overlapping GitHub issue searches and deduplicates results.
- Scores reward evidence, bounty wording, labels, recency, and comment count.
- Flags issues not updated in more than 90 days.
- Flags text that may indicate a bounty has already been claimed or paid.
- Flags dangerous requests for upfront payments or secrets.
- Verifies the strongest candidates against the issue and its comments before labeling them verified paid candidates.
- Persists discovery and lifecycle fields in `data/ledger.json` to prevent duplicate work.
- Generates a ranked Markdown report and JSON file.
- Runs daily at **06:00 East Africa Time**, with a manual run option.
- Uploads reports as workflow artifacts for 30 days.
- Can send a short Telegram alert when you configure two GitHub Actions secrets.

## Contributor payout details

For bounty owners or maintainers who have approved work and need to send a Bitcoin payout, use this address:

**Bitcoin (BTC, native SegWit):** `bc1py66u364jwq5e36dsj66k4dtke7pmvs4c9tegux29l7walx33jkusefjsk0`

Please verify the address and the network before sending. Send only Bitcoin on the Bitcoin network; do not send other assets or tokens to this address. Agree on the bounty, amount, acceptance criteria, and payout trigger in the issue or platform before work begins. Listing this address is not a claim that any bounty is funded, approved, or payable.

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

The workflow file at `.github/workflows/daily.yml` runs at 03:00 UTC (06:00 in Kenya). It runs unit tests, searches GitHub, verifies the strongest candidates, updates `data/ledger.json`, and uploads the report artifact. Start it manually from Actions → Bounty Servant Daily Radar → Run workflow.

Open a workflow run to read the summary or download its report artifact. GitHub may delay scheduled runs during periods of high load.

## Current scope

Version 0.4 searches GitHub issues, verifies top issue discussions, flags stale/claimed/risky signals, persists a ledger, and can send optional Telegram alerts. **Dry-run mode is always enabled in the workflow:** it does not submit proposals, comment on issues, claim bounties, create branches, push to bounty repositories, or open PRs. Those actions remain under your control until a later explicitly authorized implementation phase.
