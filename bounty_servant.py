#!/usr/bin/env python3
"""Bounty Servant: discover, verify, score, and track paid GitHub work.

The default mode is deliberately dry-run: it discovers and verifies candidates,
records them in a durable ledger, and prepares (but does not execute) comments,
branches, code changes, or pull requests.
"""
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

API_ROOT = "https://api.github.com"
SEARCH_URL = f"{API_ROOT}/search/issues"
OUTPUT_DIR = Path("reports")
LEDGER_PATH = Path("data/ledger.json")
MAX_PER_QUERY = 100
MAX_REPORT_ITEMS = 50
MAX_VERIFY_ITEMS = 20
STALE_AFTER_DAYS = 90
DRY_RUN = os.environ.get("BOUNTY_SERVANT_DRY_RUN", "true").lower() not in {"0", "false", "no"}
SEARCH_QUERIES = [
    "is:issue is:open bounty", "is:issue is:open label:bounty",
    "is:issue is:open reward", 'is:issue is:open "paid issue"',
    'is:issue is:open "cash bounty"', 'is:issue is:open "up for grabs"',
    'is:issue is:open "bounty available"', 'is:issue is:open "reward available"',
    'is:issue is:open "good first issue" bounty', "is:issue is:open algora bounty",
    "is:issue is:open onlydust bounty", "is:issue is:open gitcoin bounty",
    "is:issue is:open polar bounty", 'is:issue is:open "paid contribution"',
]
MONEY_PATTERNS = [
    re.compile(r"(?i)(?:\bUSD\s*|\bUS\$\s*|\$\s*)\d[\d,]*(?:\.\d{1,2})?"),
    re.compile(r"(?i)\b\d[\d,]*(?:\.\d{1,2})?\s*(?:USD|USDC|USDT|RTC|ETH|BTC|SOL|XMR|DOGE)\b"),
    re.compile(r"(?i)\b(?:reward|bounty|prize)\s*(?:amount|of|:|=)\s*(?:USD\s*|US\$\s*|\$\s*)\d[\d,]*(?:\.\d{1,2})?"),
]
BOUNTY_WORDS = re.compile(r"(?i)\b(bounty|bounties|reward|paid issue|cash prize|prize money|paid task|paid contribution)\b")
PAYMENT_WORDS = re.compile(r"(?i)\b(pay|paid|payment|reward|bounty|cash|USDC|USDT|ETH|BTC|prize|merge)\b")
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

def has_positive_reward(amount: str | None) -> bool:
    if not amount:
        return False
    numbers = re.findall(r"\d+(?:\.\d+)?", amount.replace(",", ""))
    return bool(numbers) and float(numbers[0]) > 0

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
    if BOUNTY_WORDS.search(combined) or any(word in label_text for word in ("bounty", "paid", "reward", "cash")):
        return "Potential bounty; amount unverified", None
    return "Needs manual verification", None

def status_flags(issue: dict, combined: str) -> list[str]:
    flags: list[str] = []
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
    title, body = issue.get("title") or "", issue.get("body") or ""
    labels = [item.get("name", "") if isinstance(item, dict) else str(item) for item in issue.get("labels", [])]
    combined = f"{title}\n{body}"
    status, amount = classify_reward(title, body, labels)
    flags = status_flags(issue, combined)
    score = 0
    if BOUNTY_WORDS.search(combined): score += 3
    if amount: score += 8
    elif PAYMENT_WORDS.search(combined): score += 2
    if any(word in " ".join(labels).lower() for word in ("bounty", "paid", "reward", "cash")): score += 4
    if any(word in " ".join(labels).lower() for word in ("help wanted", "good first issue")): score += 1
    updated = parse_datetime(issue.get("updated_at"))
    if updated:
        age_days = max(0, (datetime.now(timezone.utc) - updated).days)
        score += 3 if age_days <= 14 else 2 if age_days <= 30 else 1 if age_days <= STALE_AFTER_DAYS else -4
    comments = int(issue.get("comments") or 0)
    score += 2 if comments <= 5 else 1 if comments <= 15 else 0
    if any("Possible claimed/paid" in flag for flag in flags): score -= 5
    if any("Risk signal" in flag for flag in flags): score -= 10
    return max(0, score), status, amount, flags

def api_json(path: str, token: str | None) -> dict | list | None:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Bounty-Servant/0.4"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_ROOT}{path}", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (403, 429) and attempt < 2:
                time.sleep(2 ** (attempt + 1)); continue
            print(f"GitHub API HTTP {exc.code} for {path}", file=sys.stderr); return None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < 2: time.sleep(2 ** (attempt + 1)); continue
            print(f"GitHub API error for {path}: {exc}", file=sys.stderr); return None
    return None

def github_search(query: str, token: str | None) -> list[dict] | None:
    """Return matching issues, or None when the API request failed."""
    payload = api_json("/search/issues?" + urlencode({"q": query, "per_page": MAX_PER_QUERY, "sort": "updated", "order": "desc"}), token)
    if not isinstance(payload, dict):
        return None
    items = payload.get("items", [])
    return items if isinstance(items, list) else None

def verify_issue(issue: dict, token: str | None) -> dict:
    url = issue.get("html_url") or issue.get("url", "")
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
    if not match: return {"verification": "unavailable", "verification_reason": "Unrecognized issue URL"}
    repo, number = match.groups()
    detail = api_json(f"/repos/{repo}/issues/{number}", token)
    comments = api_json(f"/repos/{repo}/issues/{number}/comments?per_page=100", token)
    if not isinstance(detail, dict): return {"verification": "unavailable", "verification_reason": "Issue details unavailable"}
    comment_text = "\n".join((item.get("body") or "") for item in comments) if isinstance(comments, list) else ""
    combined = f"{detail.get('title', '')}\n{detail.get('body', '')}\n{comment_text}"
    flags = status_flags(detail, combined)
    amount = extract_reward(combined)
    open_issue = detail.get("state") == "open"
    risk = any(flag.startswith("Risk signal") for flag in flags)
    claimed = any("claimed/paid" in flag for flag in flags)
    verified = open_issue and has_positive_reward(amount) and not risk and not claimed
    return {
        "verification": "verified_paid_candidate" if verified else "needs_manual_review",
        "verification_reason": "Open issue with explicit payout evidence and no automated claim/risk signal" if verified else "Open/amount/claim/risk terms require manual confirmation",
        "issue_state": detail.get("state"), "comment_count_verified": len(comments) if isinstance(comments, list) else None,
        "latest_comment_excerpt": re.sub(r"\s+", " ", comment_text).strip()[-500:], "verified_reward_evidence": amount,
        "verified_flags": flags,
    }

def compact_issue(issue: dict) -> dict:
    labels = [item.get("name", "") if isinstance(item, dict) else str(item) for item in issue.get("labels", [])]
    score, status, amount, flags = score_issue(issue)
    body = re.sub(r"\s+", " ", issue.get("body") or "").strip()
    return {"id": issue.get("id"), "title": issue.get("title") or "(untitled issue)", "repository": (issue.get("repository_url") or "").replace(f"{API_ROOT}/repos/", ""), "url": issue.get("html_url", ""), "state": issue.get("state", "open"), "updated_at": issue.get("updated_at", ""), "created_at": issue.get("created_at", ""), "comments": int(issue.get("comments") or 0), "labels": labels, "score": score, "reward_status": status, "reward_evidence": amount, "flags": flags, "excerpt": body[:360] + ("…" if len(body) > 360 else "")}

def load_ledger() -> dict:
    if not LEDGER_PATH.exists(): return {"schema_version": 1, "updated_at": None, "opportunities": {}}
    try:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"schema_version": 1, "opportunities": {}}
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "opportunities": {}}

def update_ledger(ledger: dict, candidates: list[dict], now: datetime) -> None:
    opportunities = ledger.setdefault("opportunities", {})
    for item in candidates:
        key = item["url"] or str(item.get("id"))
        old = opportunities.get(key, {})
        opportunities[key] = {**old, "first_seen": old.get("first_seen", now.isoformat()), "last_seen": now.isoformat(), "repository": item["repository"], "issue_url": item["url"], "title": item["title"], "last_score": item["score"], "last_reward_evidence": item["reward_evidence"], "verification": item.get("verification", "not_verified"), "comment_url": old.get("comment_url"), "branch_name": old.get("branch_name"), "pr_url": old.get("pr_url"), "status": old.get("status", "discovered")}
    ledger["updated_at"] = now.isoformat()
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def build_report(issues: list[dict], generated_at: datetime, query_count: int, empty_queries: int, failed_queries: int, verified_count: int) -> str:
    lines = ["# Bounty Servant: Daily Radar", "", f"Generated: **{generated_at.strftime('%Y-%m-%d %H:%M UTC')}**", "", f"- Unique candidates: **{len(issues)}**", f"- Verified paid candidates (automated pre-check): **{verified_count}**", f"- Search queries: **{query_count}**", f"- Queries with no matches: **{empty_queries}**",
        f"- Failed searches/API requests: **{failed_queries}**", "", "> Dry-run mode is active. No issue comments, claims, branches, pushes, code changes, or pull requests were performed.", "> An automated verification is a shortlist signal, not proof of funding or payment.", ""]
    if not issues: lines += ["No candidates were returned by the configured searches.", ""]; return "\n".join(lines)
    for index, issue in enumerate(issues[:MAX_REPORT_ITEMS], 1):
        flags = "; ".join(issue["flags"]) if issue["flags"] else "No automated warning detected"
        lines += [f"## {index}. {issue['title']}", "", f"- **Score:** {issue['score']} (heuristic ranking, not probability of payment)", f"- **Repository:** {issue['repository'] or 'unknown'}", f"- **Verification:** {issue.get('verification', 'not verified')} — {issue.get('verification_reason', 'not checked')}", f"- **Reward evidence:** {issue.get('verified_reward_evidence') or issue['reward_evidence'] or 'No explicit amount detected'}", f"- **Warnings:** {flags}", f"- **Last updated:** {issue['updated_at'] or 'unknown'}", f"- **Comments:** {issue.get('comment_count_verified', issue['comments'])}", f"- **Issue:** {issue['url']}", "", f"> {issue['excerpt'] or 'No issue description was provided.'}", ""]
    lines += ["## Next action plan (dry run)", "", "For each verified candidate, the next run may prepare a maintainer comment and implementation branch after a human review of the full issue, repository license, contribution guide, and payout terms. No external action is executed while dry-run mode is enabled.", "", "## Verification checklist", "", "1. Read the original issue and newest comments.\n2. Confirm the bounty is open, independent contributions are allowed, and payout terms are documented.\n3. Check acceptance criteria, deadline, license, and payment conditions.\n4. Never pay an upfront fee or disclose passwords, private keys, or seed phrases.", ""]
    return "\n".join(lines)

def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    unique: dict[int | str, dict] = {}; empty_queries = 0; failed_queries = 0
    for query in SEARCH_QUERIES:
        results = github_search(query, token)
        if results is None:
            failed_queries += 1
            continue
        if not results: empty_queries += 1
        for issue in results:
            if "pull_request" not in issue:
                key = issue.get("id") or issue.get("html_url")
                if key is not None: unique[key] = issue
    ranked = [compact_issue(issue) for issue in unique.values()]
    ranked.sort(key=lambda item: (item["score"], item["updated_at"], -item["comments"]), reverse=True)
    for item in ranked[:MAX_VERIFY_ITEMS]: item.update(verify_issue(item, token))
    verified_count = sum(item.get("verification") == "verified_paid_candidate" for item in ranked)
    now = datetime.now(timezone.utc); ledger = load_ledger(); update_ledger(ledger, ranked, now)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(ranked, now, len(SEARCH_QUERIES), empty_queries, failed_queries, verified_count)
    (OUTPUT_DIR / f"bounties-{now:%Y-%m-%d}.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "latest.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "latest.json").write_text(json.dumps({"generated_at": now.isoformat(), "dry_run": DRY_RUN, "query_count": len(SEARCH_QUERIES), "empty_or_failed_queries": empty_or_failed, "candidate_count": len(ranked), "verified_paid_candidate_count": verified_count, "candidates": ranked}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Found {len(ranked)} unique issue candidates; verified pre-checks: {verified_count}.")
    print(f"Dry-run: {DRY_RUN}; empty/failed queries: {empty_or_failed}/{len(SEARCH_QUERIES)}")
    print(f"Report: reports/latest.md; Ledger: {LEDGER_PATH}")
    print("\n" + report[:5000])
    return 0

if __name__ == "__main__": raise SystemExit(main())
