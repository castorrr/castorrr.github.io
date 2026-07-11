#!/usr/bin/env python3
"""Maintain data/claude-activity.json — a day-level ledger of Claude Code usage.

Privacy: this script reads ONLY local Claude Code usage metadata (message /
session / tool-call counts per day) from ~/.claude. No prompts, no conversation
content, no project names, and no credentials are read, stored, or published.
The output is aggregate day-level counts only.

Modes:
  (default)   scan transcripts, upsert recent days, commit + push if changed
  --seed      one-time import of pre-transcript history from stats-cache.json
  --dry-run   print the would-be day counts; write and commit nothing
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

MANILA = ZoneInfo("Asia/Manila")
DEFAULT_REPO = Path.home() / ".local/share/claude-activity/repo"
DEFAULT_PROJECTS = Path.home() / ".claude/projects"
DEFAULT_STATS_CACHE = Path.home() / ".claude/stats-cache.json"
LEDGER_REL = Path("data/claude-activity.json")

# ---- scanning ---------------------------------------------------------------

def scan_session_lines(lines):
    """Count one session file's lines into {"YYYY-MM-DD": {"m": int, "t": int}}.

    A message is a line whose type is user/assistant with isSidechain falsy,
    bucketed to Asia/Manila by its timestamp. A tool call is a tool_use content
    block inside a counted assistant message. Malformed lines are skipped.
    """
    days = {}
    for raw in lines:
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entry, dict) or entry.get("type") not in ("user", "assistant"):
            continue
        if entry.get("isSidechain"):
            continue
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        date = ts.astimezone(MANILA).date().isoformat()
        day = days.setdefault(date, {"m": 0, "t": 0})
        day["m"] += 1
        if entry["type"] == "assistant":
            message = entry.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                day["t"] += sum(
                    1 for block in content
                    if isinstance(block, dict) and block.get("type") == "tool_use"
                )
    return days


def scan_projects(projects_dir):
    """Scan all top-level session transcripts into {"date": {"m", "s", "t"}}.

    A session counts once per day it has >=1 message. Subagent transcripts sit
    one directory deeper than <project>/<session>.jsonl, so this glob skips them.
    """
    days = defaultdict(lambda: {"m": 0, "s": 0, "t": 0})
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                session_days = scan_session_lines(fh)
        except OSError as exc:
            print(f"skipping {path}: {exc}", file=sys.stderr)
            continue
        for date, counts in session_days.items():
            days[date]["m"] += counts["m"]
            days[date]["t"] += counts["t"]
            days[date]["s"] += 1
    return dict(days)


# ---- ledger -----------------------------------------------------------------

def new_ledger():
    return {
        "version": 1,
        "generatedAt": None,
        "timezone": "Asia/Manila",
        "firstDate": None,
        "seededThrough": None,
        "totals": {},
        "days": {},
    }


def load_ledger(path):
    if not path.exists():
        return new_ledger()
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def upsert_days(ledger, scanned):
    """Replace ledger days with scanned values. Never touch dates <= seededThrough.

    Returns True if any day actually changed (idempotent re-runs return False).
    """
    seeded_through = ledger.get("seededThrough") or ""
    changed = False
    for date, counts in scanned.items():
        if date <= seeded_through:
            continue
        if ledger["days"].get(date) != counts:
            ledger["days"][date] = counts
            changed = True
    return changed


def recompute_totals(ledger):
    days = ledger["days"]
    ledger["totals"] = {
        "sessions": sum(d["s"] for d in days.values()),
        "messages": sum(d["m"] for d in days.values()),
        "toolCalls": sum(d["t"] for d in days.values()),
        "activeDays": len(days),
    }
    ledger["firstDate"] = min(days) if days else None


def write_ledger(path, ledger):
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["days"] = dict(sorted(ledger["days"].items()))
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


# ---- entry point ------------------------------------------------------------

def seed_ledger(ledger, cache, seeded_through):  # implemented in Task 4
    raise SystemExit("--seed not implemented yet")


def run_git(repo, *args):  # implemented in Task 5
    raise SystemExit("git integration not implemented yet")


def sync_git(repo, max_date):  # implemented in Task 5
    raise SystemExit("git integration not implemented yet")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true",
                        help="one-time import of history from stats-cache.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="print would-be day counts; write and commit nothing")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO,
                        help="portfolio clone whose ledger is written/committed")
    parser.add_argument("--no-git", action="store_true",
                        help="skip git pull/commit/push (local write only)")
    parser.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--stats-cache", type=Path, default=DEFAULT_STATS_CACHE)
    args = parser.parse_args(argv)

    use_git = not args.no_git and not args.dry_run
    if use_git:
        run_git(args.repo, "pull", "--rebase")

    scanned = scan_projects(args.projects_dir)
    if not scanned:
        raise SystemExit(f"no transcripts found under {args.projects_dir}")

    if args.dry_run:
        for date in sorted(scanned):
            c = scanned[date]
            print(f"{date}  m={c['m']:>6}  s={c['s']:>4}  t={c['t']:>6}")
        print(f"{len(scanned)} day(s) scanned; nothing written (--dry-run)")
        return 0

    ledger_path = args.repo / LEDGER_REL
    ledger = load_ledger(ledger_path)

    if args.seed:
        boundary = (datetime.fromisoformat(min(scanned)).date()
                    - timedelta(days=1)).isoformat()
        with open(args.stats_cache, encoding="utf-8") as fh:
            cache = json.load(fh)
        seed_ledger(ledger, cache, boundary)
        print(f"seeded {boundary} and earlier from {args.stats_cache}")

    changed = upsert_days(ledger, scanned)
    if not changed and not args.seed:
        print("no change; ledger untouched")
        if use_git:
            sync_git(args.repo, max(scanned))  # still push a stranded commit
        return 0

    recompute_totals(ledger)
    ledger["generatedAt"] = datetime.now(MANILA).isoformat(timespec="seconds")
    write_ledger(ledger_path, ledger)
    print(f"wrote {ledger_path} through {max(scanned)}")
    if use_git:
        sync_git(args.repo, max(scanned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
