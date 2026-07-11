# Claude stats restructure — surface the graph, add tokens, fix desktop cramping

**Date:** 2026-07-12
**Status:** Draft — awaiting review

## Problems

1. **The contribution graph is buried.** `#claude-stats` is the 4th section
   (hero → about → stack → stats). It's the strongest evidence for the
   "ships at AI speed" pitch, but a visitor has to scroll past two full
   sections to see it.
2. **No token usage stat.** The card shows sessions / messages / active days /
   longest streak, but not tokens — the most AI-native number of all.
3. **The graph is cramped on desktop.** Cells are fixed at 11px and the graph
   is `width: max-content`. With only ~19 weeks of history the whole heatmap
   is ~300px wide, hugging the left edge of a card that's ~1150px wide
   (`--container: 78rem`). The right two-thirds of the card is dead space.

## Goals

- Claude usage numbers visible **on first paint**, on both mobile and desktop.
- The full heatmap reachable within one small scroll.
- A lifetime **tokens** stat, updated by the same daily pipeline.
- The heatmap fills its card gracefully at any history length (19 weeks now,
  clamped 53-week rolling year later) and any viewport (320–1440px).

## Non-goals

- No framework, no build step, no redesign of the hero battle scene
  (terminal-noir theme stays; see project constraints).
- No cost/pricing estimates derived from tokens.
- No per-model token breakdown in the UI (data stays aggregated per day).

## Current state (for orientation)

- `index.html` — sections: hero, about, stack, claude-stats, experience,
  projects, contact. Hero has a `.hero-stats` strip with three static
  impact stats (5,000+ students, 95%+ accuracy, 3+ yrs).
- `js/main.js` — stats IIFE lazily fetches `data/claude-activity.json` via
  IntersectionObserver, renders 4 stat tiles + heatmap; hides the section on
  any failure.
- `css/styles.css` — `.cs-graph` grid, fixed `11px` cells / `3px` gap,
  `.cs-scroll` provides horizontal overflow.
- `scripts/update-claude-activity.py` — systemd timer scans
  `~/.claude/projects` transcripts into a day ledger
  (`{"m": messages, "s": sessions, "t": toolCalls}` per day), seeded history
  from `~/.claude/stats-cache.json` through `seededThrough` (2026-06-10),
  commits + pushes. Transcripts are pruned after ~30 days, hence the
  horizon guard.
- Tests: `scripts/test_update_claude_activity.py` (unittest, good coverage of
  scan/upsert/seed/git).

## Design

### 1. Restructure the opening

**Chosen approach — hybrid: live hero stats + section promoted to slot 2.**

- **Move `#claude-stats` to directly after the hero**, before `#about`. The
  narrative becomes: pitch ("ships at AI speed") → proof (live usage data) →
  who I am → stack → experience. Nav link order updates to match document
  order: `stats · about · stack · experience · projects · contact`.
- **The hero `.hero-stats` strip becomes live Claude stats** — the three
  flashiest numbers: **messages** (`72,219`), **tokens** (`92.9M`), and
  **longest streak** (`20d`). Same markup/CSS as today, so no layout change.
- **Baked fallback values.** The HTML ships with floor-rounded static values
  with a `+` suffix (`72K+`, `92M+`, `20d+`) so the strip is meaningful even
  if JS or the fetch fails, and rounded-down numbers can never go stale-wrong
  (usage only grows). When the JSON loads, JS swaps in exact live values.
- **Eager fetch.** The JSON is ~7KB; fetch it on script start instead of
  waiting for the IntersectionObserver, and render both the hero strip and
  the stats card from the same response. The IO-based lazy load is removed
  (it bought nothing once the data feeds the hero).
- **The three impact stats relocate to the About side card** as new `k/v`
  rows (existing `.row` pattern, zero new CSS), e.g.
  `Impact → 5,000+ students served/campus · 95%+ pipeline accuracy`. They
  keep their credibility value without competing with the AI-native pitch.

*Alternatives considered:*
- *Move the section up only* — cheapest, but nothing is visible on first
  paint; the graph still loses to the fold on most screens.
- *Embed the heatmap inside the hero* — genuinely above the fold on desktop,
  but the hero already carries the battle terminal; on mobile it would push
  CTAs far down. Rejected as busier and worse on the primary (mobile)
  viewport, where the hero-strip numbers are already the first content.

### 2. Token usage stat

**Data source (chosen): `~/.claude/stats-cache.json` → `dailyModelTokens`.**
Claude Code maintains this itself: one entry per day,
`{date, tokensByModel: {model: tokens}}`, covering the **entire history**
(2026-03-03 → present, not subject to the ~30-day transcript pruning).
Summed across models and days it currently totals **≈92.9M tokens**. This is
Claude Code's own headline token metric (≈ real input+output work, not
inflated by cache reads).

*Alternatives considered:*
- *Transcript `message.usage` sums* — only ~30 days of history survives
  pruning, and its numbers don't reconcile exactly with stats-cache
  (sidechain/dedup differences), so mixing the two across the seed boundary
  would silently blend two metrics. Rejected.
- *Total tokens processed incl. cache reads* — billions (1.9B in the last
  30 days alone), flashy but misleading and impossible to reconstruct for
  pruned history. Rejected.

**Pipeline changes (`scripts/update-claude-activity.py`):**

- Each run loads stats-cache (path is already the `--stats-cache` flag),
  builds `{date: sum(tokensByModel.values())}`, and **merges it as a new
  optional `tok` field into existing ledger days** in a separate
  `merge_tokens()` step:
  - Token merge is **exempt from the `seededThrough` and horizon guards** —
    the source covers full history and never regresses from pruning. This
    also means the first run after deploy backfills `tok` for all historic
    days automatically; no one-time flag needed.
  - Only merges into **days that already exist in the ledger** (stats-cache
    has ~2 token-only dates with no counted messages; creating them would
    corrupt the `activeDays` semantics for a <1% token undercount).
  - A missing/unreadable stats-cache, or a day absent from it, leaves any
    existing `tok` untouched — token data can be added or corrected, never
    silently wiped.
- `upsert_days()` currently replaces day dicts wholesale and detects change
  via dict equality. It must now **preserve an existing `tok`** when
  replacing a day's scanned counts, and change detection must also fire on
  token-only changes so those runs still commit.
- `recompute_totals()` adds `"tokens": sum(tok over days)`.
- Ledger stays `version: 1` — `tok`/`totals.tokens` are optional additive
  fields; the frontend feature-detects them.

**Frontend:**

- The stats card grows a 5th tile: `sessions · messages · tokens ·
  active days · longest streak`. The existing flex-wrap row handles five.
- Tokens display abbreviated (`92.9M`; `1.2B` when it gets there) via a small
  compact-number formatter; messages keep exact comma formatting.
- If `totals.tokens` is absent (stale cached JSON), the tokens tile and the
  hero token stat keep their baked/hidden fallbacks — nothing breaks.
- Cell tooltips append `· N tokens` for days that have `tok`.

### 3. De-cramp the desktop graph

**Chosen approach: responsive cell size with a cap, centered graph.**

- JS already knows the week count at render time; it sets it as a custom
  property (`--cs-weeks`) on the graph.
- CSS computes the cell size to fill the card:
  `--cell: clamp(11px, <available width − day-labels − gaps> / var(--cs-weeks), 16px)`
  using a container query unit on `.cs-scroll` (`container-type:
  inline-size`), with a plain `11px` fallback where container queries are
  unsupported. All fixed `11px` occurrences (`.cs-cells` rows/columns,
  `.cs-months` pitch, `.cs-daylabels` rows, `.cs-cell` box) switch to
  `var(--cell)`; the 3px gap stays fixed.
- `.cs-graph` gets `margin-inline: auto` so that when the cap (16px) leaves
  spare width, the graph sits centered instead of left-hugging.
- Behavior across history/viewport:
  - **Today, desktop (~19 weeks):** cells hit the 16px cap, graph ~centered,
    card no longer looks empty.
  - **Later (53-week rolling year), desktop:** cells shrink toward 11–13px
    and the graph naturally fills the full card width.
  - **Mobile:** computed size clamps at the 11px minimum, the graph
    overflows into `.cs-scroll` exactly as today (auto-scrolled to the most
    recent weeks). The known intrinsic-sizing traps are untouched —
    `.cs-scroll` keeps `overflow-x: auto; min-width: 0`.

*Alternatives considered:*
- *Center-only* — trivial but the graph stays tiny; rejected.
- *Bigger fixed cells* — breaks once history approaches 53 weeks; rejected.
- *Two-column card (stats left, graph right)* — fragile as the graph widens
  week by week; rejected.

## Error handling summary

| Failure | Behavior |
|---|---|
| JSON fetch fails / invalid | Stats section hides (existing behavior); hero strip keeps baked `72K+ / 92M+ / 20d+` values |
| `totals.tokens` missing (old cached JSON) | Tokens tile hidden; hero token stat keeps baked value |
| stats-cache missing/unreadable on the machine | Run proceeds without token merge; existing `tok` values retained |
| Container queries unsupported | Cells fall back to fixed 11px + scroll (today's behavior) |

## Testing & verification

- **Pipeline:** extend `scripts/test_update_claude_activity.py`:
  token merge into existing days only; seeded days do get `tok`; upsert
  preserves `tok`; token-only change triggers a write/commit; missing
  stats-cache leaves `tok` intact; totals include tokens; second run is a
  byte-identical no-op.
- **Frontend:** serve locally (`python3 -m http.server`) and screenshot at
  320 / 768 / 1024 / 1440px: no horizontal page overflow, graph fills card
  on desktop, hero strip shows exact values after load. Block the JSON
  request to verify the baked-fallback path. Verify tooltips include tokens.
- **Docs:** update README's stats section for the `tok` field, `totals.tokens`,
  and the stats-cache read.

## File change map

| File | Change |
|---|---|
| `index.html` | Move `#claude-stats` after hero; reorder nav; hero strip → baked Claude stats (ids for JS swap); add 5th tile; About side card gains impact rows |
| `js/main.js` | Eager fetch; render hero strip + card from one response; compact formatter; set `--cs-weeks`; token tooltip; drop IO lazy-load |
| `css/styles.css` | `--cell` sizing via container query + fallback; `var(--cell)` in the five fixed-11px spots; center `.cs-graph` |
| `scripts/update-claude-activity.py` | `merge_tokens()`; `tok`-preserving upsert + change detection; `totals.tokens` |
| `scripts/test_update_claude_activity.py` | New token tests; adjust upsert tests |
| `README.md` | Document `tok` / `totals.tokens` / stats-cache source |
