#!/usr/bin/env python3
"""Optionally send a compact Bounty Servant report to Telegram."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPORT_PATH = Path("reports/latest.json")
MAX_ITEMS = 5

def build_message(payload: dict) -> str:
    candidates = payload.get("candidates", [])
    lines = [
        "🤖 Bounty Servant daily radar",
        f"Candidates discovered: {payload.get('candidate_count', len(candidates))}",
        f"Queries with no results/errors: {payload.get('empty_or_failed_queries', 0)} / {payload.get('query_count', 0)}",
        "",
    ]
    if not candidates:
        lines.append("No candidates surfaced today. Check the Actions run for API/rate-limit details.")
        return "\n".join(lines)
    for index, item in enumerate(candidates[:MAX_ITEMS], start=1):
        title = (item.get("title") or "Untitled issue").replace("\n", " ").strip()
        if len(title) > 110:
            title = title[:107] + "..."
        reward = item.get("reward_evidence") or "amount unverified"
        lines.extend([
            f"{index}. {title}",
            f"Score: {item.get('score', 0)} | Reward: {reward}",
            f"Status: {item.get('reward_status', 'Needs review')}",
            item.get("url", ""),
        ])
        flags = item.get("flags") or []
        if flags:
            lines.append("⚠️ " + "; ".join(flags[:2]))
        lines.append("")
    lines.extend([
        "Verify the issue and latest comments before starting. A detected amount is not a payment guarantee.",
        "Full report: open the latest GitHub Actions run and its artifact.",
    ])
    return "\n".join(lines)

def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram not configured; skipping notification.")
        return 0
    if not REPORT_PATH.exists():
        print("No report JSON found; skipping notification.")
        return 0
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read report: {exc}", file=sys.stderr)
        return 1
    body = json.dumps({
        "chat_id": chat_id,
        "text": build_message(payload),
        "disable_web_page_preview": True,
    }).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Bounty-Servant/0.3"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            print("Telegram rejected the notification.", file=sys.stderr)
            return 1
        print("Telegram notification sent.")
        return 0
    except HTTPError as exc:
        print(f"Telegram API HTTP {exc.code}; check the bot token and chat ID.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Telegram notification failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
