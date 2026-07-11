# Investigation: Claude Contribution Graph for the Portfolio

**Date:** 2026-07-11
**Status:** For review — no implementation yet
**Goal:** Show a GitHub-style contribution heatmap of my Claude Code activity on the portfolio (castorrr.github.io), refreshed daily.

---

## TL;DR / Recommendation

All the data we need already exists on this machine. Claude Code keeps an internal
`~/.claude/stats-cache.json` whose `dailyActivity` array is *literally* contribution-graph
data — `{date, messageCount, sessionCount, toolCallCount}` per day, going back to my first
session on **2026-03-03**. Raw session transcripts provide ground truth for the last 30 days
(they are auto-pruned after that), and `history.jsonl` keeps prompt-level history with
project paths for the full period.

**Recommended approach (Approach A below):** a small local aggregation script, run daily by
a systemd user timer, that maintains a cumulative `data/claude-activity.json` ledger in this
repo — seeded once from `stats-cache.json`, updated from transcripts going forward — and
commits + pushes it when it changes. GitHub Pages redeploys automatically, and a new
"claude stats" section on the site renders the heatmap client-side with vanilla JS/CSS
(no build step, matching the site's constraints).

There is **no viable official API** for this: the Anthropic Claude Code Analytics API is
org-admin-only and not available to individual Max subscribers, and the `/stats` command in
Claude Code renders an interactive dashboard with no JSON export.

---

## 1. What we're building

A GitHub-style activity heatmap ("green squares"), but for Claude Code usage:

- One cell per day, color intensity = activity level (metric TBD — see Open Questions).
- Fits the site's existing terminal-noir aesthetic — e.g. framed as a terminal block with a
  `❯ claude stats --graph` prompt echo, coral-scale cells instead of GitHub green.
- Bonus data available at no extra cost: hour-of-day histogram ("when I pair with Claude"),
  total sessions/messages, per-model token split, streaks.

Verified headline numbers as of today (from the cache): **964 sessions, 68,626 messages
since 2026-03-03**, and e.g. 1.7M tokens with `claude-fable-5` on a single day (Jul 3).
This section will not look empty.

---

## 2. Findings: available data sources

### 2.1 `~/.claude/stats-cache.json` — the gem ✅ (verified locally)

The cache behind Claude Code's own `/stats` dashboard (introduced v2.0.64). Format
(`version: 4`, undocumented/internal):

| Field | Contents |
|---|---|
| `dailyActivity` | `[{date, messageCount, sessionCount, toolCallCount}]` — 89 active days, 2026-03-03 → 2026-07-03 |
| `dailyModelTokens` | per-day `tokensByModel` breakdown |
| `modelUsage` | cumulative input/output/cache tokens per model |
| `totalSessions` / `totalMessages` | 964 / 68,626 |
| `hourCounts` | activity histogram by hour of day (peak: 9am, 144) |
| `firstSessionDate` | 2026-03-03T13:37:24Z |
| `lastComputedDate` | 2026-07-03 — **a week stale** |

Two critical properties, both verified:

1. **It survives transcript pruning.** 69 of its 89 days predate the oldest transcript still
   on disk. It is the *only* local source of aggregate history older than 30 days.
2. **It goes stale.** It recomputes only when the `/stats` UI is opened — it was 8 days
   behind despite daily usage. A pipeline cannot rely on it for *fresh* data, only for
   *historical seed* data.

### 2.2 Raw transcripts `~/.claude/projects/<project>/<session>.jsonl` ✅ (verified locally)

- One JSONL per session (444 main-session files + subagent files, 919 total right now).
  Every message entry has `timestamp` (UTC ISO), `type` (`user`/`assistant`), `sessionId`,
  `isSidechain`, `cwd`, `gitBranch`, etc.
- **Pruned after 30 days** (`cleanupPeriodDays`, default 30 — docs confirm; the oldest file
  on disk today is dated exactly 30 days ago). Official docs explicitly call the format
  internal: *"scripts that parse these files directly can break on any release."*
- Ground truth for the trailing 30-day window; scriptable with a few lines of Python.

### 2.3 `~/.claude/history.jsonl` ✅ (verified locally)

Prompt-level history: `{display, timestamp(ms), project, sessionId}`. 5,164 entries covering
**2026-03-03 → today with no pruning observed**. Uniquely, it has the **project path** for
the full period — the only full-history source that can split work vs. personal usage
(top projects are all `work-synacy/*`; personal is the minority). Coarser than transcripts
(user prompts only, no assistant/tool counts).

### 2.4 Official commands & APIs ❌ (researched, not viable)

| Option | Verdict |
|---|---|
| `/stats` in Claude Code | Interactive dashboard + shareable image only; no JSON output; no headless CLI subcommand exists (`claude --help` confirms) |
| Claude Code Analytics API (`/v1/organizations/usage_report/claude_code`) | Real and rich (sessions/day, LoC, commits, tokens per user-day) but requires an **org Admin API key**; individual Pro/Max subscribers can't query their own usage |
| Usage & Cost API | API-key orgs only; message-level, not Claude-Code-session-level |

### 2.5 OpenTelemetry ⚠️ (possible, overkill)

`CLAUDE_CODE_ENABLE_TELEMETRY=1` + OTLP exporter emits `claude_code.session.count`,
`token.usage`, `lines_of_code.count`, etc. Forward-only (no history), and requires running a
local collector 24/7. Not worth the infrastructure for one heatmap.

### 2.6 Community tools 📦 (validation of the approach, not a dependency)

`ccusage` (npm), `cc-time`, `cc-heatmap`, `tokscale` all parse the same
`~/.claude/projects/` transcripts — confirming the transcript-scanning approach is
well-trodden. None of them solves publication/daily-refresh for a static site, and none
preserves history past the 30-day pruning without their own ledger, so we'd still write the
same ~50-line script. Not worth adding a dependency.

### 2.7 Hooks ⚠️ (optional complement)

`SessionStart` / `UserPromptSubmit` / `Stop` hooks fire reliably and could increment a local
daily counter in real time. Caveats: concurrent sessions racing on one counter file,
`SessionEnd` not firing on crashes, and it only captures activity *from now on*. Since
transcripts already cover a 30-day trailing window, hooks add complexity without adding
data. **Skip for v1**; reconsider only if we ever want same-minute freshness.

---

## 3. The counting-rules problem (important)

A naive scan of transcripts does **not** reproduce the cache's numbers for overlapping days:

| date | raw scan msgs | cache msgs | raw sessions | cache sessions |
|---|---|---|---|---|
| 2026-06-30 | 1,472 | 2,906 | 22 | 38 |
| 2026-07-01 | 2,949 | 2,563 | 38 | 21 |
| 2026-07-02 | 760 | 961 | 16 | 16 |
| 2026-07-03 | 760 | 2,080 | 11 | 20 |

Likely causes: timezone bucketing (transcript timestamps are UTC; my day is UTC+8),
sidechain/subagent inclusion, what counts as a "message", and whether a session is counted
on its start day vs. every active day. Claude's exact rules are internal.

**Implication:** don't chase parity. Pick *our own* deterministic counting rule (proposal:
main-chain `user` + `assistant` messages, bucketed to Asia/Manila days, sessions counted on
each day they were active), apply it consistently going forward, and accept that the
seeded pre-June history (from the cache) was counted slightly differently. For a heatmap,
relative intensity is what matters; a one-line footnote on the site can note the
methodology. The intensity scale should use percentiles/buckets rather than absolute
thresholds, which also absorbs the seed-vs-ongoing difference.

---

## 4. Approaches considered

### Approach A — Ledger in repo + local daily timer (recommended)

```
┌────────────────────── this machine (daily systemd user timer) ─────────────────────┐
│ aggregate.py:                                                                      │
│   1. read data/claude-activity.json (cumulative ledger, committed in repo)         │
│   2. scan ~/.claude/projects/*.jsonl → per-day counts for trailing 30-day window   │
│   3. upsert those days into ledger (idempotent; old days never touched)            │
│   4. if changed: git commit + push (existing github-personal SSH alias)            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    → GitHub Pages auto-redeploys (~1 min)
                    → site fetches data/claude-activity.json (same-origin, no CORS)
                    → vanilla JS renders heatmap
```

One-time seeding: import `stats-cache.json`'s `dailyActivity` for 2026-03-03 → cutoff, then
the script owns everything after. The ledger is append-only and lives in git, so history can
never be silently lost again — the 30-day pruning stops mattering entirely.

- **Pros:** zero new infrastructure, zero runtime dependencies, no secrets (SSH key already
  set up), data is versioned, site fetch is same-origin, survives format changes (script
  fails loudly, ledger untouched), tolerates up to ~29 days of the machine being off
  (`Persistent=true` catch-up + 30-day transcript window).
- **Cons:** requires this machine to be on sometime during the day; one small commit per
  active day in the portfolio repo's history.

### Approach B — Same ledger, published out-of-repo (variant of A)

Push the JSON to a Gist or a dedicated `data` branch instead of `main`; site fetches the raw
URL. Avoids daily commits in `main`'s history. Costs: a PAT to manage (Gist), or
`raw.githubusercontent.com` caching (up to 5 min CDN cache, fine for daily data) and CORS
verification. Also: daily commits to any repo will paint *GitHub's* contribution graph green
too — either a fun meta-joke or noise, depending on taste (see Open Questions). Gist commits
don't count toward the GitHub graph; repo commits do.

### Approach C — Hook-driven live counters

`UserPromptSubmit`/`Stop` hooks increment `~/.claude/daily-activity.json` in real time; the
timer just publishes. Real-time freshness nobody will notice on a daily-refresh graph, plus
concurrency and crash-gap issues. **Rejected for v1** — transcripts already cover the window.

### Approach D — OpenTelemetry collector

Correct enterprise answer, wrong personal-portfolio answer. Always-on collector, no
backfill, new infra. **Rejected.**

### Approach E — Anthropic Analytics API

Would be the cleanest source (`num_sessions`, LoC, commits per day) but is org-admin-only.
**Not available** to an individual Max subscription. Re-check if Anthropic ever ships a
personal usage API.

---

## 5. Frontend integration (Approach A assumed)

The site is a single `index.html` + `css/styles.css` + `js/main.js`, no build step
(hard constraint). Integration is one new section + one fetch:

- **Placement:** new section between **Stack** and **Experience** (it's evidence for the
  "AI-native toolbelt" claim), or inside Stack itself. Framed like the existing `.term`
  components: title bar, `❯ claude stats --graph` prompt echo, then the graph.
- **Rendering:** ~53×7 CSS grid of cells (or one inline SVG) from the fetched JSON.
  5-step intensity scale derived from `--coral` (#d97757) over `--bg-2`, matching how GitHub
  scales green. Tooltips via `title` attr or a tiny custom tooltip; month labels on top,
  weekday labels left, GitHub-style.
- **Numbers row:** total sessions / messages / active days / longest streak as `.stat`
  blocks (component already exists in the hero).
- **Mobile:** the full 12-month grid is ~700px wide minimum — put it in an
  `overflow-x: auto` scroller with the *most recent* weeks scrolled into view, or show
  fewer months under a breakpoint. ⚠️ Known trap in this codebase (see memory): CSS grid
  intrinsic sizing — the scroll container needs `min-width: 0` on the grid ancestor path.
- **Progressive enhancement:** if `fetch` fails or the JSON is missing/stale, hide the
  section or show `stats unavailable — claude is sleeping` in terminal style. Never a
  broken layout. Show "last updated <date>" from the JSON's `generatedAt`.
- **Respect `prefers-reduced-motion`** like the rest of `main.js` (no cell-by-cell
  entrance animation in that case).

### Proposed data schema (`data/claude-activity.json`)

```json
{
  "version": 1,
  "generatedAt": "2026-07-11T18:30:00+08:00",
  "timezone": "Asia/Manila",
  "firstDate": "2026-03-03",
  "totals": { "sessions": 964, "messages": 68626, "toolCalls": 12345, "activeDays": 97 },
  "hourCounts": { "0": 33, "9": 144 },
  "days": {
    "2026-03-03": { "m": 99, "s": 4, "t": 17 },
    "2026-07-11": { "m": 981, "s": 13, "t": 210 }
  },
  "seededThrough": "2026-06-10"
}
```

Compact keys keep the file small (~100 active days ≈ a few KB). `seededThrough` marks the
methodology boundary from §3. Only aggregates are published — no project names, no prompts.

---

## 6. Problems & risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Undocumented formats** — transcripts and stats-cache are internal; any Claude Code release can change them | Medium | Ledger is the source of truth; scanner validates expected fields and fails loudly *without* touching the ledger; seed from cache happens exactly once |
| 2 | **30-day transcript pruning** — history silently deleted | High (already happening) | This is the core reason for the cumulative ledger; after seeding, nothing depends on data older than the scan window. Optionally raise `cleanupPeriodDays` as belt-and-braces |
| 3 | **stats-cache staleness** (verified: 8 days behind) | Low | Used only for the one-time seed, never for freshness |
| 4 | **Machine off / laptop asleep at timer time** | Medium | systemd user timer with `Persistent=true` runs on next boot; 30-day transcript window means up to ~29 days of downtime lose nothing |
| 5 | **Timezone bucketing** — transcripts are UTC, my days are UTC+8 | Low | Bucket explicitly to Asia/Manila in the scanner; record `timezone` in the JSON |
| 6 | **Counting-rule mismatch** seed vs. ongoing (§3) | Low | Percentile-based color buckets; footnote on site |
| 7 | **Privacy** — usage includes work (Synacy) sessions; transcripts contain confidential content | Medium | Publish day-level aggregate *counts only*. Decide whether work activity should count at all (see Open Questions); `history.jsonl` enables a personal-only filter for the full period, transcripts (`cwd`) for the recent window |
| 8 | **Multi-machine usage** — only this machine's activity is captured | Low today | Acceptable; if a second machine appears, its ledger entries can be merged (upsert by date+source) |
| 9 | **Daily commits pollute repo history & GitHub graph** | Cosmetic | Accept (it's on-brand), or Approach B (gist/data branch), or squash periodically |
| 10 | **GitHub Pages deploy latency & caching** | Trivial | ~1 min build; fetch with `cache: "no-cache"` or a `?v=` stamp from a meta tag |
| 11 | **Git push failure** (auth, network, diverged branch) | Low | Script does `pull --rebase` first, logs failures; next day's run self-heals since upserts are idempotent |

---

## 7. Open questions for you

1. **Which metric drives cell color?** Messages/day (my recommendation — closest analog to
   commits, richest signal), sessions/day, tool calls/day, or tokens/day. Tooltip can show
   all of them regardless.
2. **Include work usage?** All activity (fuller graph, ~4× the volume, nothing sensitive is
   published either way) vs. personal-projects only (purer "my own time" story, sparser
   graph). Splitting is feasible for the whole timeline via `history.jsonl`, but then
   message counts have to come from prompts only for the pre-June seed — or the graph starts
   in June. **My take: include everything for v1**; it's a usage graph, not a code
   disclosure.
3. **Publish channel:** commit into `main` (Approach A, simplest, zero secrets) vs.
   gist/data branch (Approach B, clean history)? A also gives you real GitHub-graph greens
   from the automation — decide if that's a feature or a bug.
4. **Placement:** its own section after Stack (`#claude-stats` in the nav) vs. embedded
   inside the Stack section?
5. **Extras for v1:** hour-of-day punch card? streak counter? per-model token split? Or keep
   v1 to the heatmap + totals row (my recommendation) and iterate?

---

## 8. Suggested next steps

1. You review this doc and answer §7 (or just bless the recommendations).
2. Design pass: section layout, cell sizing, color ramp, mobile behavior.
3. Build the aggregation script + seed the ledger; verify counts eyeball-sane.
4. Build the frontend section against the real seeded JSON.
5. Install the systemd user timer; watch it run for a couple of days before merging.
