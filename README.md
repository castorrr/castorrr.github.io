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
├── index.html        One scrollable page: Hero · About · Stack · Experience · Projects · Contact
├── css/
│   └── styles.css    The whole theme (CSS variables at the top control everything)
├── js/
│   └── main.js       Nav toggle · scrollspy · scroll-reveal · the typing terminal
├── data/
│   └── claude-activity.json   Day-level Claude Code usage counts (auto-updated daily)
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

The `#claude-stats` section renders `data/claude-activity.json` — a ledger of
my Claude Code usage maintained by `scripts/update-claude-activity.py` on a
daily systemd user timer. **Privacy:** only day-level aggregate counts
(messages, sessions, tool calls per day) are ever published. No prompts, no
conversation content, no project names, and no credentials leave my machine.

## Deploy

Static, so hosting is free: **GitHub Pages** (push + enable Pages on `main`),
or drag the folder into **Netlify / Vercel**. Relative paths mean it works at
any URL with zero config.
