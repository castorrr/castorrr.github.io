# Spec: Claude Contribution Graph

**Date:** 2026-07-11
**Status:** Draft — awaiting review
**Precursor:** [Investigation doc](../../investigations/2026-07-11-claude-contribution-graph.md) (data sources, approach comparison, ToS check)

## Overview

A GitHub-style contribution heatmap of my Claude Code activity, shown as a new section on
the portfolio (castorrr.github.io), covering everything since my first session on
2026-03-03 and refreshed daily by a local systemd user timer.

## Locked decisions

| Decision | Choice |
|---|---|
| Cell-color metric | **Messages per day** (tooltip shows sessions + tool calls too) |
| Scope | **All activity** (work + personal); only day-level counts published |
| Publish channel | **Commit `data/claude-activity.json` to `main`**; site fetches same-origin |
| V1 scope | **Heatmap + totals/streak stats row** (punch card, model split deferred) |
| Placement | Own section `#claude-stats` between Stack and Experience, `stats` nav link |
| Refresh | Daily systemd user timer, 21:00 local, `Persistent=true` |
| Timezone | All day-bucketing in **Asia/Manila (UTC+8)** |

## Non-goals (v1)

- Hour-of-day punch card, per-model token split, streak *calendar* (only a longest-streak number).
- Real-time/hook-based updates; anything more frequent than daily.
- Multi-machine merging (schema allows it later; not built now).
- Reproducing Claude's internal `/stats` numbers exactly (see counting rules).

## Architecture

```
one-time                daily (systemd user timer, 21:00 or next login)
┌───────────────┐       ┌─────────────────────────────────────────────┐
│ seed ledger   │       │ scripts/update-claude-activity.py           │
│ from          │       │  1. read ledger from dedicated clone        │
│ stats-cache   │──────▶│  2. scan ~/.claude/projects/*/*.jsonl       │
│ .json         │       │  3. upsert recent days into ledger          │
└───────────────┘       │  4. commit + push iff changed               │
                        └──────────────────┬──────────────────────────┘
                                           ▼
                     GitHub Pages redeploys main (~1 min)
                                           ▼
                     index.html fetches data/claude-activity.json
                                           ▼
                     js/main.js renders heatmap + stats row
```

## Component 1 — Data file: `data/claude-activity.json`

Committed to the repo; the single source of truth for both history and the frontend.

```json
{
  "version": 1,
  "generatedAt": "2026-07-11T21:00:03+08:00",
  "timezone": "Asia/Manila",
  "firstDate": "2026-03-03",
  "seededThrough": "2026-06-10",
  "totals": { "sessions": 964, "messages": 68626, "toolCalls": 11525, "activeDays": 97 },
  "days": {
    "2026-03-03": { "m": 99, "s": 4, "t": 17 },
    "2026-07-11": { "m": 981, "s": 13, "t": 210 }
  }
}
```

- `days` keys are `YYYY-MM-DD` (Asia/Manila); values: `m` messages, `s` sessions, `t` tool calls.
- `totals` are recomputed from `days` on every write (not incremented).
- `seededThrough` marks the methodology boundary: dates ≤ it came from `stats-cache.json`,
  dates after it from transcript scans.
- Days with zero activity are omitted.
- Contract: the frontend must tolerate unknown extra fields (future versions add, never rename).

## Component 2 — Aggregation script: `scripts/update-claude-activity.py`

Python 3, stdlib only, ~150 lines. Two modes:

**`--seed` (run once, manually):** imports `~/.claude/stats-cache.json` → `dailyActivity`
entries for every date older than the oldest transcript on disk, records that boundary as
`seededThrough`, then falls through to a normal run. Refuses to run if the ledger already
has a `seededThrough` (seeding is not repeatable).

**Normal run (the timer):**

1. `git -C <clone> pull --rebase` in a **dedicated clone** (`~/.local/share/claude-activity/repo`,
   `main` checked out, created by the install script). Never touches my dev working copy —
   my checked-out feature branches and dirty trees can't collide with automation.
2. Scan `~/.claude/projects/*/*.jsonl` (top level only — subagent subdirectories excluded).
   Counting rules, applied identically every run:
   - **message** = a line with `type` `user` or `assistant` and `isSidechain` falsy, bucketed
     to Asia/Manila by its `timestamp`.
   - **session** = a session file is counted once per day it has ≥1 such message (active-day
     attribution).
   - **tool call** = a `tool_use` content block inside a counted assistant message.
   - Malformed lines are skipped silently; a file that fails wholesale is logged and skipped.
3. Upsert every scanned day into `days` — scanned values *replace* stored values for those
   dates (idempotent; a partial "today" gets corrected by tomorrow's run). Dates ≤
   `seededThrough` are never modified.
4. Recompute `totals`, stamp `generatedAt`, write atomically (tmp file + `os.replace`).
5. If `git status` shows a change: commit
   (`chore: update claude activity through YYYY-MM-DD`) and push.

**Failure behavior:** any unexpected exception → non-zero exit, ledger untouched, error in
the systemd journal. Push failures are logged and abandoned — the next run redoes the same
upsert and self-heals. No retries, no partial writes.

**`--dry-run` flag:** scans and prints the would-be day counts, writes and commits nothing.
Used for testing on the feature branch before anything is merged.

## Component 3 — Scheduling: systemd user units

`claude-activity.service` (Type=oneshot, runs the script) + `claude-activity.timer`
(`OnCalendar=*-*-* 21:00`, `Persistent=true`). Behavior: runs at 21:00 if the machine is
up, otherwise within ~1 minute of next login. Multiple catch-up runs are harmless.

Unit files are generated by `scripts/install-claude-activity-timer.sh` (idempotent), which
also creates the dedicated clone. The units themselves live in
`~/.config/systemd/user/` — outside the repo; the install script is the source of truth.
`ExecStart` runs the script *from the dedicated clone* (so automation always executes the
`main` version of itself), which means the timer can only be installed after the feature
merges to `main`.

## Component 4 — Frontend section

**Markup (`index.html`):** new `<section class="section" id="claude-stats">` between Stack
and Experience; `stats` link added to `.nav-links` (mobile nav is a vertical dropdown — one
more item is safe). Inside, reusing existing components:

- `.prompt-echo`: `❯ claude stats --graph`
- A `.term`-styled card containing the heatmap
- A `.hero-stats`-style row: **total sessions · total messages · active days · longest streak**
- Footer line inside the card: `last updated 2026-07-11 · all data since 2026-03-03`

**Rendering (`js/main.js`, appended IIFE section, no dependencies):**

- `fetch("data/claude-activity.json", { cache: "no-cache" })` on section approach
  (IntersectionObserver, same pattern as the battle boot). On any failure: the section gets
  `hidden` — never a broken layout.
- Heatmap = one CSS grid, `grid-auto-flow: column`, 7 rows, one column per week from
  `firstDate`'s week through the current week (~19 columns now, growing to a 53-column
  rolling year once history exceeds 12 months). Cells are `<span>`s with a `title` tooltip:
  `"Jul 11 · 981 messages · 13 sessions · 210 tool calls"`.
- **Color scale:** 5 buckets on `m`. Zero/no entry → `--bg-3`-level cell; nonzero days split
  by quartiles of all nonzero `m` values (computed client-side), mapped to a 4-step coral
  ramp derived from `--coral` (#d97757). Percentile bucketing absorbs the seed-vs-scan
  counting seam and outlier days.
- Month labels above, `Mon/Wed/Fri` labels left, GitHub-style.
- Longest streak computed client-side from consecutive dates in `days`.
- `prefers-reduced-motion`: no entrance animation; otherwise cells fade in with the
  existing `.reveal` treatment (whole card, not per-cell).

**Mobile (`css/styles.css`):** the grid has a fixed intrinsic width (cell 11px + 3px gap);
it lives in an `overflow-x: auto` wrapper that is scrolled to the right (most recent weeks)
on load. Known trap in this codebase: every grid/flex ancestor on the path needs
`min-width: 0` so the scroller, not the page, absorbs the overflow.

## Privacy & compliance guardrail

Only day-level aggregate counts are ever written to the repo — no project names, prompts,
or content. `scripts/update-claude-activity.py` carries a header comment and the repo
README gains a line stating exactly that (per investigation §6.1).

## Testing & verification

- **Script:** counting logic isolated as a pure function (`lines → {date: counts}`) with a
  handful of unit tests (timezone boundary at UTC 16:00 = local midnight, sidechain
  exclusion, malformed line, session active-day attribution). Run twice back-to-back →
  second run must be a no-op (no commit).
- **Seed sanity:** after seeding, spot-check 3 dates against `stats-cache.json` and 3
  post-seed dates against an independent manual scan.
- **Frontend:** local preview server; verify desktop + 375px mobile (scroller, no page
  overflow), dark cells/tooltips, fetch-failure fallback (rename the JSON), reduced-motion.
- **End-to-end (post-merge):** `systemctl --user start claude-activity.service` manually →
  observe commit on `main` → Pages deploy → live fetch. Then let the timer run unattended
  for 2 days before calling it done.

## Rollout order

1. Aggregation script + tests on the feature branch; `--seed` run; commit seeded
   `data/claude-activity.json`. Verify with `--dry-run` that repeat scans are stable.
2. Frontend section built against the real seeded data; verify desktop + mobile locally.
3. PR `feature/claude-contribution-graph` → `main`, merge. Automation has not run yet —
   no conflict is possible with the seeded data file.
4. Run `scripts/install-claude-activity-timer.sh` (creates the dedicated `main` clone +
   units), trigger one manual service run end-to-end, then observe two unattended daily
   runs.
