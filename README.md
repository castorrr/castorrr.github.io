# Castor Troy Ricafort — Portfolio

A single-page, **AI-native** developer portfolio. Pure static HTML/CSS/JS —
no framework, no build step — with a "terminal noir" theme: dark UI, a
Claude-coral accent, and a hero that's a **Claude Code terminal** which boots
on view and reveals an interactive Pokémon-style battle — Castor (a pixel-art
trainer) vs. Clawd, the Claude Code robot mascot — fought over the
**context window**, not HP.

## Structure

```
yort-portfolio/
├── index.html        One scrollable page: Hero · Claude Stats · About · Stack · Experience · Projects · Contact
├── css/
│   └── styles.css    The whole theme (CSS variables at the top control everything)
├── js/
│   └── main.js       Nav toggle · scrollspy · scroll-reveal · the typing terminal
├── data/
│   └── claude-activity.json   Day-level Claude Code usage counts + token totals (auto-updated daily)
├── scripts/
│   ├── update-claude-activity.py          Rebuilds data/claude-activity.json from local logs
│   ├── test_update_claude_activity.py     Its unit tests (python3 scripts/test_update_claude_activity.py)
│   └── install-claude-activity-timer.sh   One-time systemd user-timer setup (run after merge)
└── assets/
    ├── resume.pdf    Linked by the "Résumé" buttons
    ├── icons/        Brand SVGs for the stack/toolbelt (Devicon + Simple Icons)
    └── images/
        ├── clawd.png    Clawd — the Claude Code robot mascot (battle opponent)
        └── pokemon.png  Castor as a pixel-art trainer (battle player)
```

The nav links are **in-page anchors** (`#about`, `#stack`, …) — clicking one
smooth-scrolls to that section, and the active section highlights as you scroll.

## Run it locally

It's just files — open `index.html`, or serve it (recommended, matches production):

```bash
python3 -m http.server 8000     # then visit http://localhost:8000
```

## Customize

- **Colors / theme** — every color is a CSS variable in `:root` at the top of
  `css/styles.css`. Change `--coral` to re-accent the whole site; `--bg` for the
  background.
- **The battle banter** — edit the `MOVES` object in `js/main.js` to change what
  each move says (and `runCommand` for the optional command line).
- **Content** — all real content lives in `index.html` (bio, stack, experience,
  projects, contact). Update the social URLs and email there.
- **Avatars / résumé** — swap `assets/images/pokemon.png` (player),
  `assets/images/clawd.png` (opponent), and `assets/resume.pdf`. New combatant
  art on a solid background should have that background keyed out to transparency
  first so it sits cleanly on the dark arena.

- **Tech icons** — brand SVGs live in `assets/icons/` (Devicon + Simple Icons).
  Add one and reference it with `<img class="ti" src="assets/icons/NAME.svg" alt="">`.

### About the battle scene

The hero is a **Claude Code terminal** that "boots" on view (`$ claude` →
welcome → ready) and then reveals a Pokémon-style battle inside it. The boot/
reveal lives in `js/main.js` (`bootIntro()` toggles the `.booting` class on
`#term-battle`).

- **Clawd** (the opponent) and **Castor** (the player) are both real pixel-art
  images — `assets/images/clawd.png` (the Claude Code robot mascot) and
  `assets/images/pokemon.png` (Castor as a trainer). Both were delivered on a
  solid background that was keyed out to transparency so they composite cleanly
  onto the arena. Swap either file to re-skin a combatant.
- Instead of HP and pokéballs, each fighter has a **context-window / token
  meter**. A move *burns tokens* — the bar drains, a floating `−38K` rises off
  the sprite, and the `200K / 200K tokens` readout ticks down. When a side's
  context fills up (hits `0` remaining) it runs **`/compact`** and the tokens
  are freed again — the in-universe way Claude "always wins the argument."
  Tune the costs in the `MOVES` table and `CTX_MAX` in `js/main.js`.

The **Experience** section reuses the same `.term` window component as a
terminal session, and `.prompt-echo` lines (`❯ …`) thread the terminal theme
through About, Stack, and Projects.

## Claude activity data

The `#claude-stats` section (and the live hero stat strip) render
`data/claude-activity.json` — a ledger of my Claude Code usage maintained by
`scripts/update-claude-activity.py` on a daily systemd user timer. Each day
holds `{"m": messages, "s": sessions, "t": toolCalls, "tok": tokens}` (`tok`
appears once stats-cache has computed that day — typically all but the most
recent day or two); `tok` and `totals.tokens` are summed per day across
models from Claude Code's own `~/.claude/stats-cache.json`
(`dailyModelTokens`), which covers the full history and isn't subject to
transcript pruning — so the first run after deploy backfills tokens for all
historic days automatically. If stats-cache is missing or unreadable the
run simply proceeds without a token merge; existing `tok` values are never
wiped. The hero strip ships with baked floor-rounded fallbacks (`72K+` /
`92M+` / `20d+`) that JS swaps for exact values when the JSON loads.
**Privacy:** only day-level aggregate counts (messages, sessions, tool
calls, tokens per day) are ever published. No prompts, no conversation
content, no project names, and no credentials leave my machine.

**Setup** (one-time, run only after this feature is merged to `main`):

```bash
bash scripts/install-claude-activity-timer.sh
```

This clones a dedicated copy of the repo to
`~/.local/share/claude-activity/repo` (kept separate from your working clone
so the scheduled job always runs merged `main`, not whatever's checked out
locally) and installs a systemd user timer that runs the update script daily
at 21:00.

Because the timer is `Persistent=true`, a run missed while the machine is
off/asleep fires at the next boot or resume — often before the network is up,
which used to make the opening `git pull` fail and abort the whole run. Two
guards prevent that now: the service waits (best effort, up to 5 min) for
`github.com` to resolve before starting, and the script retries each network
git op and, if the pull still fails, writes and commits the ledger locally
anyway — the next successful run pushes the stranded commit. A transient
network blip therefore no longer costs a day of data.

The update script itself does a `git pull --rebase` in that clone at the
start of every run — but since it's already loaded into memory by the time
that pull happens, the first run after merging changes to
`scripts/update-claude-activity.py` still executes the *previous* script
version; the pull only readies the clone for the run after that. So after
merging a script change, run
`git -C ~/.local/share/claude-activity/repo pull --rebase` once yourself
(before the next scheduled tick) to make the very next run pick up the new
code.

**Check it ran:**

```bash
systemctl --user list-timers claude-activity.timer --no-pager  # last/next run time
systemctl --user status claude-activity.service                # last result
journalctl --user -u claude-activity.service --since today      # full output
git -C ~/.local/share/claude-activity/repo log --oneline -5     # commits it pushed
```

**Stop it:**

```bash
systemctl --user disable --now claude-activity.timer
```

## Deploy

Static, so hosting is free: **GitHub Pages** (push + enable Pages on `main`),
or drag the folder into **Netlify / Vercel**. Relative paths mean it works at
any URL with zero config.
