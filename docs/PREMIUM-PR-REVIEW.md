# Premium Feature: Pull Request Review and Fix Assistant

## Goal
Let a user connect their own GitHub account manually, select a repository and open pull request, receive actionable code-review findings, understand how to fix each issue, draft a patch, and optionally publish a comment or fix branch only after explicit confirmation.

This document is a product specification. It does not claim the integration or premium billing is implemented.

## User journey
1. The user selects Connect GitHub and is sent to GitHub's official authorization or installation screen.
2. The user reviews requested permissions and authorizes access. Bounty Servant never asks the user to paste a personal access token.
3. The user chooses which repositories the integration may access, then selects an open PR.
4. The service loads PR metadata, changed filenames, patches, and relevant discussion using only authorized GitHub APIs.
5. The analysis page shows findings grouped by severity, confidence, affected file/line, evidence from the diff, impact, and step-by-step fix instructions.
6. The user opens a proposed patch in a diff preview, edits it if needed, and reviews tests or validation steps.
7. Separate explicit actions let the user copy a fix, publish a review comment, or create a new fix branch and pull request. No comment, commit, push, approval, or merge happens automatically.
8. The user can disconnect GitHub and request deletion of stored integration metadata and analysis history.

## Permissions and authorization
- Use a GitHub App with read-only repository contents and pull-request metadata/review permissions for analysis where practical.
- Request write permissions only when the user enables a specific write action. Keep comment/review and contents write access as narrow as the GitHub permission model allows.
- Never request organization-wide access when repository selection is sufficient.
- Validate the authenticated user, installation, repository, PR number, head SHA, and permission scope on the server for every request.
- Do not rely on frontend checks to enforce access.
- Provide a visible connected account, granted access scope, repository selection, last-use timestamp, and disconnect control.

## Analysis contract
Each finding should contain:
- title and severity (critical, high, medium, low, or informational)
- confidence and rationale
- file path and changed-line range when the API supplies valid positions
- evidence snippet with minimal necessary source context
- likely impact and why it matters
- concrete remediation steps
- suggested patch, if safe and sufficiently supported
- tests to add or run and limitations

Avoid fabricated line numbers, unverified vulnerability claims, and unsupported claims that code is safe. State when context is insufficient. Distinguish bugs from style preferences. Avoid reproducing secrets found in source; redact them and recommend rotation.

## Patch workflow
- Generate a patch as a proposal, never execute code from the PR.
- Validate paths are relative, remain inside the repository, and contain no traversal segments or unsafe symlinks.
- Bind a proposed patch to the PR head SHA analyzed. If the head changes, invalidate the patch and require re-analysis.
- Show the complete diff and test plan before any write.
- Require fresh user confirmation for each external write. A comment and a branch/PR are separate permissions and separate confirmations.
- Prefer a new branch and draft PR over modifying the user's existing PR branch.
- Never merge, approve, request changes, or push without a separate deliberate action.
- Make writes idempotent where possible and verify resulting GitHub state.

## AI and privacy
- Treat PR descriptions, code comments, test output, and repository files as untrusted input, not instructions. The model must not follow prompt-injection instructions embedded in source code.
- Never pass tokens, environment secrets, or unrelated repository files to the model.
- Before analysis, disclose which code/diff data will be sent to the configured AI provider and link that provider's privacy and retention terms.
- Offer a local/private provider option if feasible and a no-external-AI mode.
- Minimize data sent, bound file and diff sizes, log metadata rather than source code, and set documented retention/deletion rules.
- Do not train on customer code without separate, explicit opt-in consent.

## Abuse prevention and reliability
- Rate-limit analysis and writes per user and installation.
- Bound file count, patch size, runtime, retries, and provider spend.
- Validate webhooks and verify signatures if webhooks are added.
- Store auditable records of authorization, analysis, user confirmations, and write results without logging credentials or unnecessary source code.
- Fail closed if authorization, permission, PR head SHA, or provider policy cannot be verified.

## Premium entitlement
The server, not the browser, must verify active premium entitlement before paid analysis or paid write features. Keep billing webhooks authenticated and idempotent. Never trust a client-supplied premium flag. Show pricing, renewal, cancellation, refund, and usage limits before purchase.

## Acceptance criteria
- Users can connect and disconnect their own GitHub account.
- Users cannot access repositories outside granted permissions.
- PR review is read-only by default and returns evidence-based findings.
- Each finding explains the issue, impact, steps to fix, and suggested tests.
- Patch previews are bound to the analyzed head SHA.
- No comment, code write, branch, PR, approval, or merge occurs without explicit confirmation.
- Secret redaction, prompt-injection handling, size limits, rate limits, and access-control tests pass.
- Premium entitlement is enforced server-side and billing behavior is tested.
- Privacy and terms pages accurately reflect deployed data flows before public launch.

## Implementation sequence
1. Register and configure a GitHub App; implement OAuth/install callback with CSRF/state protection.
2. Add server-side encrypted token storage, session binding, repository selection, and disconnect.
3. Implement read-only PR listing, changed-file retrieval, and diff limits.
4. Build structured analysis and finding UI with evidence and fix instructions.
5. Add patch proposal, validation, preview, and tests.
6. Add explicitly confirmed comment publishing.
7. Add explicitly confirmed fix-branch/draft-PR creation.
8. Wire premium entitlement and usage limits; verify billing and legal disclosures.
9. Run authorization, security, privacy, and end-to-end tests before release.
