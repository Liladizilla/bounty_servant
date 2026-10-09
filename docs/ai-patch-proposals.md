# AI-assisted bounty patch proposals

This optional workflow is a **manual, review-only stage** beside the daily bounty radar.

## Run it

1. Merge the feature branch after reviewing pull request checks.
2. Open **Actions → Prepare Bounty Patch Proposal → Run workflow** on the default branch.
3. Enter a public GitHub issue URL, for example `https://github.com/OWNER/REPO/issues/123`.
4. Download the generated `bounty-patch-proposal` artifact.
5. Review the Markdown report, JSON metadata, and unified diff. Test any patch in an isolated checkout before using it.

## API key

The workflow accepts the existing `GEMINI` repository secret or `GEMINI_API_KEY`. The key is passed only through the Actions environment and is not stored in source code. Free-tier providers can impose changing quotas and rate limits.

## Safety boundaries

The proposer reads public issue and repository context, then writes a patch proposal artifact. It does not:

- Execute code from the target repository.
- Apply the generated patch or run the target project's tests.
- Comment on issues, claim bounties, create branches in target repositories, push commits, or open pull requests.
- Modify Git metadata, CI workflow files, or likely credential files in the generated patch.

Issue bodies, comments, and source files are untrusted input. Model-generated patches are untrusted output. Review and test every proposal before applying it.

The workflow is intentionally manual. Automated external actions should be added only after independent validation and explicit approval gates.
