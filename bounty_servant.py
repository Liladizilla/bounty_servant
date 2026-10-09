#!/usr/bin/env python3
"""Bounty Servant: discover and rank possible paid software issues on GitHub."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.github.com/search/issues"
OUTPUT_DIR = Path("reports")
MAX_PER_QUERY = 100
MAX_REPORT_ITEMS = 50

SEARCH_QUERIES = [
    'is:issue is:open bounty',
    'is:issue is:open reward',
    'is:issue is:open "paid issue"',
    'is:issue is:open "cash bounty"',
    'is:issue is:open "up for grabs"',
    'is:issue is:open bounty "$"',
]

MONEY_PATTERNS = [
    re.compile(r"(?i)(?:\bUSD\s*|\bUS\$\s*|\$\s*)\d[\d,]*(?:\.\d{1,2})?"),
    re.compile(r"(?i)\b\d[\d,]*(?:\.\d{1,2})?\s*(?:USDC|USDT|ETH|BTC)\b"),
    re.compile(r"(?i)\b(?:reward|bounty|prize)\s*(?:amount|of|:|=)\s*\$?\s*\d[\d,]*(?:\.\d{1,2})?"),
]
BOUNTY_WORDS = re.compile(r"(?i)\b(bounty|bounties|reward|paid issue|cash prize|prize money|paid task)\b")
PAYMENT_WORDS = re.compile(r"(?i)\b(pay|paid|payment|reward|bounty|cash|USDC|USDT|ETH|BTC|prize)\b")


def extract_reward(text: str) -> str | None:
    """Return the first matched monetary/payout phrase, if one is present."""
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(0).strip()
    return None


def classify_reward(title: str, body: str, labels: list[str]) -> tuple[str, str | None]:
    """Classify payout evidence conservatively; never treat a label as proof."""
    combined = f"{title or ''}\n{body or ''}"
    amount = extract_reward(combined)
    label_text = " ".join(labels).lower()

    if amount:
        return "Payout evidence found; verify terms", amount

    if BOUNTY_WORDS.search(combined) or any(
        word in label_text for word in ("bounty", "paid", "reward", "cash")
    ):
        return "Potential bounty; payout amount unverified", None

    return "Needs manual verification", None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def score_issue(issue: dict) -> tuple[int, str, str | None]:
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    labels = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in issue.get("labels", [])
    ]
    combined = f"{title}\n{body}"
    status, amount = classify_reward(title, body, labels)
    score = 0

    if BOUNTY_WORDS.search(combined):
        score += 3
    if amount:
        score += 8
    elif PAYMENT_WORDS.search(combined):
        score += 2

    label_text = " ".join(labels).lower()
    if any(word in label_text for word in ("bounty", "paid", "reward", "cash")):
        score += 4
    if "help wanted" in label_text or "good first issue" in label_text:
        score += 1

    updated = parse_datetime(issue.get("updated_at"))
    if updated:
        age_days = max(0, (datetime.now(timezone.utc) - updated).days)
        if age_days <= 14:
            score += 3
        elif age_days <= 30:
            score += 2
        elif age_days <= 90:
            score += 1

    comments = int(issue.get("comments") or 0)
    if comments <= 5:
        score += 2
    elif comments <= 15:
        score += 1

    return score, status, amount


def github_search(query: str, token: str | None) -> list[dict]:
    params = urlencode({"q": query, "per_page": MAX_PER_QUERY, "sort": "updated", "order": "desc"})
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Bounty-Servant/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API_URL}?{params}", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload.get("items", [])
        except HTTPError as exc:
            if exc.code in (403, 429) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            print(f"GitHub API returned HTTP {exc.code} for query {query!r}: {detail}", file=sys.stderr)
            return []
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            print(f"Could not complete query {query!r}: {exc}", file=sys.stderr)
            return []
    return []


def compact_issue(issue: dict) -> dict:
    labels = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in issue.get("labels", [])
    ]
    score, status, amount = score_issue(issue)
    body = re.sub(r"\s+", " ", issue.get("body") or "").strip()
    return {
        "id": issue.get("id"),
        "title": issue.get("title") or "(untitled issue)",
        "repository": (issue.get("repository_url") or "").replace(
            "https://api.github.com/repos/", ""
        ),
        "url": issue.get("html_url", ""),
        "state": issue.get("state", "open"),
        "updated_at": issue.get("updated_at", ""),
        "created_at": issue.get("created_at", ""),
        "comments": int(issue.get("comments") or 0),
        "labels": labels,
        "score": score,
        "reward_status": status,
        "reward_evidence": amount,
        "excerpt": body[:360] + ("…" if len(body) > 360 else ""),
    }


def build_report(issues: list[dict], generated_at: datetime) -> str:
    date_label = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Bounty Servant: Daily Radar",
        "",
        f"Generated: **{date_label}**",
        "",
        f"Candidates found: **{len(issues)}**",
        "",
        "> This is a discovery shortlist, not a guarantee of payment. Verify the original issue, eligibility, payout terms, and whether the bounty is still available before investing time.",
        "",
    ]

    if not issues:
        lines.extend([
            "No candidates were returned by the configured searches in this run.",
            "",
            "This may mean no matching issues were found, or that an API/search request was limited. Check the workflow log before concluding there are no bounties.",
        ])
        return "\n".join(lines) + "\n"

    for index, issue in enumerate(issues[:MAX_REPORT_ITEMS], start=1):
        labels = ", ".join(issue["labels"][:8]) or "none listed"
        lines.extend([
            f"## {index}. {issue['title']}",
            "",
            f"- **Score:** {issue['score']}/23 (heuristic, not a success probability)",
            f"- **Repository:** `{issue['repository'] or 'unknown'}`",
            f"- **Reward status:** {issue['reward_status']}",
            f"- **Reward evidence:** {issue['reward_evidence'] or 'No explicit amount detected'}",
            f"- **Last updated:** {issue['updated_at'] or 'unknown'}",
            f"- **Comments:** {issue['comments']}",
            f"- **Labels:** {labels}",
            f"- **Issue:** {issue['url']}",
            "",
            f"> {(issue['excerpt'] or 'No issue description was provided.')}",
            "",
        ])

    if len(issues) > MAX_REPORT_ITEMS:
        lines.extend([f"_Showing the top {MAX_REPORT_ITEMS} of {len(issues)} candidates._", ""])

    lines.extend([
        "## How to use this list",
        "",
        "1. Open the original issue and read the complete description and comments.",
        "2. Confirm the reward is real, current, and available to you.",
        "3. Check contribution rules, required skills, deadlines, and payout method.",
        "4. Avoid work that requires upfront payment or sharing secrets.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    unique: dict[int | str, dict] = {}
    query_errors = 0

    for query in SEARCH_QUERIES:
        results = github_search(query, token)
        if not results:
            query_errors += 1
        for issue in results:
            # Search/issues can include pull requests; keep issue URLs only.
            if "pull_request" in issue:
                continue
            issue_id = issue.get("id") or issue.get("html_url")
            if issue_id is not None:
                unique[issue_id] = issue

    ranked = [compact_issue(issue) for issue in unique.values()]
    ranked.sort(key=lambda item: (item["score"], item["updated_at"], -item["comments"]), reverse=True)

    now = datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"bounties-{now:%Y-%m-%d}.md"
    latest_path = OUTPUT_DIR / "latest.md"
    json_path = OUTPUT_DIR / "latest.json"
    report = build_report(ranked, now)

    report_path.write_text(report, encoding="utf-8")
    latest_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {"generated_at": now.isoformat(), "query_count": len(SEARCH_QUERIES),
             "empty_or_failed_queries": query_errors, "candidate_count": len(ranked),
             "candidates": ranked},
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"Found {len(ranked)} unique issue candidates.")
    print(f"Report: {report_path}")
    print(f"JSON:   {json_path}")
    print("\n" + report[:5000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
