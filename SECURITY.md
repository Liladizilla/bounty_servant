# Security Policy

## Supported versions
Security fixes target the latest code on the default branch. This evolving project has no formal response-time SLA.

## Report a vulnerability privately
Do not publish exploitable details in a public issue or pull request. Use GitHub's Security Advisories feature to report privately when available. Otherwise contact the repository owner privately through GitHub and request a secure reporting channel. Do not include secrets or private user data in public reports.

Include the affected component, impact, reproduction steps, and suggested mitigation where possible. Allow reasonable time to investigate before public disclosure.

## Security boundaries
- Bounty amounts and verification labels are untrusted signals, not payout guarantees.
- Keep GitHub, Telegram, and model-provider credentials in environment variables or GitHub Actions secrets. Never commit them.
- Never run code from an issue, pull request, repository, or model output merely because an automated system suggested it.
- The daily radar is dry-run only. It must not submit proposals, comment, push code, create branches in third-party repositories, or open pull requests without a separately designed and explicitly authorized feature.
- Never send secrets to an LLM. Minimize source code sent to external providers and disclose provider data handling before enabling remote analysis.
- Validate and escape untrusted issue titles, bodies, comments, repository names, and model output before rendering or using them in commands.
- Use least-privilege permissions for workflows and integrations.

## Scope and limitations
This policy is not a certification, security audit, warranty, or guarantee that all vulnerabilities will be found. Report only information you are authorized to access.
