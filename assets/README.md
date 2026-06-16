# assets/

Files used by the site:

- **`resume.pdf`** — the CV. The "Résumé" / "Download résumé" buttons in
  `index.html` link to `assets/resume.pdf`. If it's missing, those buttons 404.
- **`icons/`** — brand SVGs for the stack and toolbelt (Devicon + Simple Icons).
  Reference one with `<img class="ti" src="assets/icons/NAME.svg" alt="">`.
- **`images/`** — the two battle sprites:
  - `clawd.png` — Clawd, the Claude Code robot mascot (battle opponent)
  - `pokemon.png` — Castor as a pixel-art trainer (battle player)

  Both were delivered on a solid background that was keyed out to transparency
  so they composite cleanly onto the dark arena. Swap either to re-skin a fighter.
