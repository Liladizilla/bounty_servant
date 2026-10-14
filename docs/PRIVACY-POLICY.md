# Privacy Policy

**Effective date:** 14 October 2026  
**Project:** Bounty Servant

This is a project-level policy draft for the current open-source application. It describes intended handling for the repository and dashboard as they exist today. It is not a substitute for jurisdiction-specific legal review.

## Data the current radar processes
Bounty Servant searches public GitHub issues and reads public issue metadata and comments to identify possible software-development bounties. It stores opportunity metadata, scoring and verification signals, timestamps, lifecycle status, and daily aggregate metrics in repository JSON files and generated reports. A public GitHub Pages dashboard can display this data to anyone who can access the site.

If an operator configures optional notifications, the workflow uses the configured Telegram bot token and chat ID to send an alert. Credentials should be stored only as GitHub Actions secrets and must not be included in reports or logs.

## Data not intentionally collected
The current public radar does not require a visitor account and does not intentionally request a visitor's name, email address, precise location, or payment-card details. Do not submit private repository code, credentials, personal data, or confidential information into public issues or reports.

## Third-party services
The current workflow may communicate with GitHub APIs, GitHub Actions, GitHub Pages, and optionally Telegram. Each service processes data under its own terms and privacy policy. Public issue content remains subject to GitHub's service and repository settings.

A future premium pull-request analysis feature may require GitHub authorization and may send selected pull-request diffs to a configured AI provider. That future processing is not represented as implemented by this policy. Before launch, disclose exactly what code and metadata are accessed, whether code leaves GitHub, which provider receives it, retention, processing region where known, and how access is revoked. Private-repository code must not be sent to an AI provider until the user has been clearly informed and has explicitly enabled that processing.

## Retention and deletion
The current workflow retains uploaded report artifacts for 30 days where configured. Ledger and history files committed to the repository persist in Git history until repository history is changed; deleting a current file does not erase previous commits or third-party copies.

For the future connected feature, provide a way to disconnect GitHub, revoke granted access, and delete stored integration metadata and analysis history where applicable. Do not retain access tokens longer than required.

## Security
Keep tokens in GitHub Actions secrets or a managed secret store, use least privilege, rotate exposed credentials, and never commit secrets. No internet-connected system can promise perfect security.

## Children
Bounty Servant is a developer tool, not designed for children.

## Changes and contact
This policy may change as the project evolves. Review the repository's Security policy for private vulnerability reporting. Publish an appropriate operator contact before offering a paid hosted service.
