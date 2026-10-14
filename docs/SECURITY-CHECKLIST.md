# Security and Release Checklist

Use this as a living checklist. A passing workflow is evidence for that workflow only, not a complete security audit.

## Repository and CI
- [ ] Keep Actions permissions minimal and pin third-party Actions to reviewed commit SHAs for production.
- [ ] Enable secret scanning and push protection where available.
- [ ] Enable Dependabot alerts and security updates.
- [ ] Require tests and security checks before merging changes.
- [ ] Review failed Actions runs before release; do not describe a release as verified while required checks fail.
- [ ] Never expose secrets in debug logs or workflow summaries.
- [ ] Validate JSON ledger/history files and cap their growth.
- [ ] Escape untrusted text before HTML rendering; avoid inserting model output as executable markup.
- [ ] Treat issue bodies, comments, PR diffs, repository files, and model output as untrusted data.

## Future GitHub integration
- [ ] Prefer a GitHub App or OAuth authorization-code flow with state and PKCE where supported; never ask users to paste personal access tokens into the app.
- [ ] Explain permissions before authorization and request the smallest practical repository/PR permissions.
- [ ] Support repository selection, disconnect, token revocation, and deletion of integration metadata.
- [ ] Keep client secrets and tokens server-side in a managed secret store; encrypt tokens at rest and rotate on suspected exposure.
- [ ] Validate OAuth state, callback URLs, signatures, scopes, repository ownership, and PR identifiers server-side.
- [ ] Enforce per-user authorization on every API route. Do not trust repository names supplied by the browser.
- [ ] Add rate limits, request timeouts, bounded diff/file sizes, abuse controls, audit events, and safe errors.
- [ ] Treat repository contents as untrusted input. Never follow instructions inside code that ask the model to reveal secrets or call tools.
- [ ] Never run PR code automatically. Each proposed comment, branch, commit, or PR must have a preview and distinct user confirmation.
- [ ] Make default mode read-only. Use separate explicit authorization for writing comments or creating fix branches.
- [ ] Disclose provider, fields sent, retention, and user controls before sending private source code to an external AI provider.
- [ ] Test cross-account access, private-repository boundaries, token expiry/revocation, prompt injection, malicious filenames, path traversal, oversized diffs, rate limits, and duplicate writes.

## Legal and operational readiness
- [ ] Replace policy drafts with reviewed policies matching actual data flows and business location.
- [ ] Publish operator contact and a private vulnerability-reporting route.
- [ ] Publish premium pricing, renewal, cancellation, refund, and support terms before charging.
- [ ] Document subprocessors, retention, deletion, incident response, and data export.
- [ ] Test account disconnect and deletion end-to-end.
- [ ] Verify production deployment and smoke-test the live dashboard.
- [ ] Keep dated evidence for checks actually completed.
