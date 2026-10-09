#!/usr/bin/env python3
"""Maintain a compact, idempotent daily history of measured bounty-ledger metrics."""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TZ = ZoneInfo("Africa/Nairobi")
HISTORY_PATH = ROOT / "data" / "metrics-history.json"
LEDGER_PATH = ROOT / "data" / "ledger.json"


def make_snapshot(ledger: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(LOCAL_TZ)
    records = list((ledger.get("opportunities") or {}).values())
    verification = {"verified_paid_candidate": 0, "needs_manual_review": 0, "not_verified": 0}
    statuses = {name: 0 for name in ("discovered", "investigating", "proposal_ready", "submitted", "accepted", "paid")}
    scores = []
    new_today = 0
    for item in records:
        state = item.get("verification", "not_verified")
        verification[state] = verification.get(state, 0) + 1
        status = item.get("status", "discovered")
        statuses[status] = statuses.get(status, 0) + 1
        try:
            scores.append(float(item.get("last_score", 0)))
        except (TypeError, ValueError):
            scores.append(0.0)
        first_seen = item.get("first_seen")
        if first_seen:
            try:
                parsed = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed.astimezone(LOCAL_TZ).date() == local_now.date():
                    new_today += 1
            except (TypeError, ValueError):
                pass
    bins = {"0_4": 0, "5_9": 0, "10_14": 0, "15_19": 0, "20_plus": 0}
    for score in scores:
        key = "0_4" if score < 5 else "5_9" if score < 10 else "10_14" if score < 15 else "15_19" if score < 20 else "20_plus"
        bins[key] += 1
    return {
        "date": local_now.date().isoformat(),
        "updated_at": now.astimezone(timezone.utc).isoformat(),
        "tracked_opportunities": len(records),
        "new_first_seen_today": new_today,
        "verification_counts": verification,
        "status_counts": statuses,
        "score_distribution": bins,
        "average_score": round(statistics.fmean(scores), 2) if scores else 0,
        "median_score": statistics.median(scores) if scores else 0,
    }


def update_history(ledger: dict, history: dict | None = None, now: datetime | None = None) -> dict:
    history = history or {"schema_version": 1, "snapshots": []}
    snapshots = [s for s in history.get("snapshots", []) if isinstance(s, dict) and s.get("date")]
    snapshot = make_snapshot(ledger, now)
    by_date = {s["date"]: s for s in snapshots}
    by_date[snapshot["date"]] = snapshot  # repeated runs on the same local day update, not duplicate
    ordered = [by_date[key] for key in sorted(by_date)][-365:]
    return {"schema_version": 1, "updated_at": snapshot["updated_at"], "snapshots": ordered}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    history = json.loads(args.history.read_text(encoding="utf-8")) if args.history.exists() else None
    updated = update_history(ledger, history)
    args.history.parent.mkdir(parents=True, exist_ok=True)
    args.history.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = updated["snapshots"][-1]
    print(f"Saved metrics snapshot {latest['date']}: {latest['tracked_opportunities']} tracked issues")


if __name__ == "__main__":
    main()
