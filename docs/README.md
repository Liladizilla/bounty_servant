# Bounty Servant dashboard

A dependency-free, responsive dashboard for the public repository ledger and recent GitHub Actions runs.

## Publish with GitHub Pages

The dashboard lives at `docs/index.html`. In the repository settings, open **Pages** and select **Deploy from a branch**, then choose `main` and `/docs`. Once enabled, the dashboard URL is:

`https://liladizilla.github.io/bounty_servant/`

The page reads `data/ledger.json` from the public `main` branch and the public GitHub Actions API. It does not require a personal access token or a backend server.

## Metric definitions

- **Tracked opportunities:** records in `data/ledger.json`.
- **Verified pre-check:** records marked `verified_paid_candidate`; this is an automated shortlist signal, not proof that a bounty is funded or payable.
- **Manual review:** records marked `needs_manual_review`.
- **Confirmed paid:** records explicitly marked `status: paid`. This is not inferred from reward text.
- **First-seen trend:** number of ledger entries whose `first_seen` date falls on each of the last 14 days. It is not a daily scan-volume chart.
- **Score distribution:** latest heuristic scores. Scores are not payment probabilities.
- **Automation health:** recent workflow status and conclusions returned by GitHub Actions.

The opportunity table supports search, verification/status filters, and CSV export. The dashboard is read-only and does not comment on issues, claim bounties, push code, or open pull requests.
