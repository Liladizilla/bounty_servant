#!/usr/bin/env python3
"""Bounty Servant: discover, score, and flag GitHub bounty candidates."""

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
STALE_AFTER_DAYS = 90

SEARCH_QUERIES = [
    'is:issue is:open bounty',
    'is:issue is:open label:bounty',
    'is:issue is:open reward',
    'is:issue is:open "paid issue"',
    'is:issue is:open "cash bounty"',
    'is:issue is:open "up for grabs"',
    'is:issue is:open "bounty available"',
    'is:issue is:open "reward available"',
    'is:issue is:open "good first issue" bounty',
    'is:issue is:open algora bounty',
    'is:issue is:open onlydust bounty',
    'is:issue is:open gitcoin bounty',
    'is:issue is:open polar bounty',
    'is:issue is:open "paid contribution"',
]

MONEY_PATTERNS = [
    re.compile(r"(?i)(?:\bUSD\s*|\bUS\$\s*|\$\s*)\d[\d,]*(?:\.\d{1,2})?"),
    re.compile(r"(?i)\b\d[\d,]*(?:\.\d{1,2})?\s*(?:USD|USDC|USDT|RTC|ETH|BTC|SOL|XMR|DOGE)\b"),
    re.compile(r"(?i)\b(?:reward|bounty|prize)\s*(?:amount|of|:|=)\s*(?:USD\s*|US\$\s*|\$\s*)\d[\d,]*(?:\.\d{1,2})?"),
]
BOUNTY_WORDS = re.compile(r"(?i)\b(bounty|bounties|reward|paid issue|cash prize|prize money|paid task|paid contribution)\b")
PAYMENT_WORDS = re.compile(r"(?i)\b(pay|paid|payment|reward|bounty|cash|USDC|USDT|ETH|BTC|prize)\b")
CLAIMED_PATTERNS = [
    re.compile(r"(?i)\b(bounty|reward)\s+(has been\s+)?(claimed|paid out|paid)\b"),
    re.compile(r"(?i)\b(already paid|payment sent|reward sent|bounty claimed|claimed by @[\w-]+)\b"),
    re.compile(r"(?i)\b(issue|task)\s+(is\s+)?(completed and paid|already completed)\b"),
]
RISK_PATTERNS = [
    re.compile(r"(?i)\b(pay (?:an? )?upfront fee|upfront payment required|pay to apply)\b"),
    re.compile(r"(?i)\b(send|share|provide)\s+(?:your )?(?:private key|seed phrase|password)\b"),
]


def extract_reward(text: str) -> str | None:
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(0).strip()
    return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def classify_reward(title: str, body: str, labels: list[str]) -> tuple[str, str | None]:
    combined = f"{title or ''}\n{body or ''}"
    amount = extract_reward(combined)
    label_text = " ".join(labels).lower()
    if amount:
        return "Amount detected; verify the offer and terms", amount
    if BOUNTY_WORDS.search(combined) or any(
        word in label_text for word in ("bounty", "paid", "reward", "cash")
    ):
        return "Potential bounty; amount unverified", None
    return "Needs manual verification", None


def status_flags(issue: dict, combined: str) -> list[str]:
    flags = []
    updated = parse_datetime(issue.get("updated_at"))
    if updated:
        age_days = max(0, (datetime.now(timezone.utc) - updated).days)
        if age_days > STALE_AFTER_DAYS:
            flags.append(f"Stale: not updated for {age_days} days")
    if any(pattern.search(combined) for pattern in CLAIMED_PATTERNS):
        flags.append("Possible claimed/paid signal: inspect latest comments")
    if any(pattern.search(combined) for pattern in RISK_PATTERNS):
        flags.append("Risk signal: never pay upfront or share secrets")
    return flags


def score_issue(issue: dict) -> tuple[int, str, str | None, list[str]]:
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    labels = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in issue.get("labels", [])
    ]
    combined = f"{title}\n{body}"
    status, amount = classify_reward(title, body, labels)
    flags = status_flags(issue, combined)
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
        elif age_days <= STALE_AFTER_DAYS:
            score += 1
        else:
            score -= 4

    comments = int(issue.get("comments") or 0)
    if comments <= 5:
        score += 2
    elif comments <= 15:
        score += 1

    if any("Possible claimed/paid" in flag for flag in flags):
        score -= 5
    if any("Risk signal" in flag for flag in flags):
        score -= 10

    return max(0, score), status, amount, flags


def github_search(query: str, token: str | None) -> list[dict]:
    params = urlencode({"q": query, "per_page": MAX_PER_QUERY, "sort": "updated", "order": "desc"})
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Bounty-Servant/0.2",
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
            print(f"GitHub API HTTP {exc.code} for {query!r}: {detail}", file=sys.stderr)
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
    score, status, amount, flags = score_issue(issue)
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
        "flags": flags,
        "excerpt": body[:360] + ("…" if len(body) > 360 else ""),
    }


def build_report(issues: list[dict], generated_at: datetime, query_count: int, failed_queries: int) -> str:
    lines = [
        "# Bounty Servant: Daily Radar",
        "",
        f"Generated: **{generated_at.strftime('%Y-%m-%d %H:%M UTC')}**",
        "",
        f"- Unique candidates: **{len(issues)}**",
        f"- Search queries: **{query_count}**",
        f"- Empty/failed queries: **{failed_queries}**",
        "",
        "> A detected amount is not proof of a payable bounty. Open the issue, read its latest comments and terms, and verify the reward is still available before doing work.",
        "",
    ]
    if not issues:
        lines.extend([
            "No candidates were returned by the configured searches.",
            "",
            "This can mean no matches were found or that an API/search request was limited. Check the workflow logs before concluding there are no bounties.",
        ])
        return "\n".join(lines) + "\n"

    for index, issue in enumerate(issues[:MAX_REPORT_ITEMS], start=1):
        labels = ", ".join(issue["labels"][:8]) or "none listed"
        flags = "; ".join(issue["flags"]) if issue["flags"] else "No automated warning detected"
        lines.extend([
            f"## {index}. {issue['title']}",
            "",
            f"- **Score:** {issue['score']} (heuristic ranking, not probability of payment)",
            f"- **Repository:** {issue['repository'] or 'unknown'}",
            f"- **Reward status:** {issue['reward_status']}",
            f"- **Reward evidence:** {issue['reward_evidence'] or 'No explicit amount detected'}",
            f"- **Warnings:** {flags}",
            f"- **Last updated:** {issue['updated_at'] or 'unknown'}",
            f"- **Comments:** {issue['comments']}",
            f"- **Labels:** {labels}",
            f"- **Issue:** {issue['url']}",
            "",
            f"> {issue['excerpt'] or 'No issue description was provided.'}",
            "",
        ])
    if len(issues) > MAX_REPORT_ITEMS:
        lines.extend([f"_Showing the top {MAX_REPORT_ITEMS} of {len(issues)} candidates._", ""])
    lines.extend([
        "## External bounty boards to check",
        "",
        "These are source links for manual verification, not live API integrations. Platform APIs and access rules change; verify each site's current status before relying on it.",
        "",
        "- [Algora](https://algora.io/)",
        "- [OnlyDust](https://www.onlydust.com/)",
        "- [Gitcoin](https://gitcoin.co/)",
        "- [Polar](https://polar.sh/)",
        "",
        "## Verification checklist",
        "",
        "1. Read the original issue and newest comments.",
        "2. Confirm the bounty is open, unclaimed, and backed by clear payout terms.",
        "3. Check eligibility, acceptance criteria, deadline, and payout method.",
        "4. Never pay an upfront fee or disclose passwords, private keys, or seed phrases.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    unique: dict[int | str, dict] = {}
    empty_or_failed = 0

    for query in SEARCH_QUERIES:
        results = github_search(query, token)
        if not results:
            empty_or_failed += 1
        for issue in results:
            if "pull_request" in issue:
                continue
            issue_id = issue.get("id") or issue.get("html_url")
            if issue_id is not None:
                unique[issue_id] = issue

    ranked = [compact_issue(issue) for issue in unique.values()]
    ranked.sort(
        key=lambda item: (item["score"], item["updated_at"], -item["comments"]),
        reverse=True,
    )

    now = datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"bounties-{now:%Y-%m-%d}.md"
    latest_path = OUTPUT_DIR / "latest.md"
    json_path = OUTPUT_DIR / "latest.json"
    report = build_report(ranked, now, len(SEARCH_QUERIES), empty_or_failed)

    report_path.write_text(report, encoding="utf-8")
    latest_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps({
            "generated_at": now.isoformat(),
            "query_count": len(SEARCH_QUERIES),
            "empty_or_failed_queries": empty_or_failed,
            "candidate_count": len(ranked),
            "candidates": ranked,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Found {len(ranked)} unique issue candidates.")
    print(f"Empty/failed queries: {empty_or_failed}/{len(SEARCH_QUERIES)}")
    print(f"Report: {report_path}")
    print(f"JSON:   {json_path}")
    print("\n" + report[:5000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
