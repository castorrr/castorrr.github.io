# Expandable Project Cards + Doxie — Design Spec

**Date:** 2026-07-11
**Status:** Awaiting review
**Scope:** Projects section of the portfolio (`index.html`, `css/styles.css`, `js/main.js`)

## 1. Goal

Two improvements to the projects section:

1. **Expandable projects** — each card opens a richer detail view: longer write-up,
   highlights, links, and (when available) screenshots.
2. **Add Doxie** — a third project card for the AI-driven documentation CLI
   (hackathon build, public repo + live landing page).

Constraints (standing, from project memory):

- Keep the **terminal-noir** theme — new UI should look like it belongs in the
  existing terminal world, not bolted on.
- **No build step, no frameworks** — vanilla HTML/CSS/JS only.
- **Mobile is the primary viewport** — the detail view must be great at 320–430 px
  before it's judged at desktop widths.
- Images: **build the support now, add real pictures later.** Nothing may look
  broken while a project has no images.

## 2. Approaches considered

### A. Per-project native `<dialog>` styled as a terminal window — **chosen**

Clicking a card opens a modal that looks like another terminal window
(reusing the existing `.term` / `.term-bar` chrome — traffic-light dots, title
bar). Each project ships its own `<dialog>` element in the HTML.

- **Pros:** Strongly on-theme ("opening a file" — `cat tambal-pd.md`). Native
  `<dialog>.showModal()` gives Esc-to-close, focus containment, focus restore to
  the opener, and `::backdrop` for free — minimal JS (~30 lines). Content lives in
  HTML like the rest of the site (hand-authorable, no data layer). Plenty of room
  for images. No regression without JS: cards render exactly as today.
- **Cons:** Terminal-chrome markup is repeated per project (3× — acceptable).

### B. Single shared dialog + `<template>` per card

One `<dialog>` in the DOM; JS clones each card's `<template>` into it on open.

- **Pros:** No repeated chrome markup.
- **Cons:** More JS (clone, inject, title swap), harder to reason about, and
  `aria-labelledby` wiring gets dynamic. Saves ~40 lines of HTML at the cost of
  fragility. Not worth it at 3 projects.

### C. Inline accordion expansion

The card grows in place to reveal details.

- **Pros:** No overlay logic; natural on mobile's single column.
- **Cons:** In the desktop multi-column grid, an expanding card stretches its row
  neighbors or must jump to full width — both feel janky. Cramped for image
  galleries. Rejected (and the user picked the modal in brainstorming).

## 3. Design

### 3.1 Card changes (`index.html`)

Each `.card` gains:

- `data-modal="<dialog-id>"` on the `<article>` — JS makes the whole card
  clickable (`cursor: pointer`).
- An explicit affordance/footer that is a **real `<button>`** (the keyboard-
  accessible path), styled as a prompt line in mono font:

```html
<button class="card-open" aria-haspopup="dialog" aria-controls="modal-tambal">
  <span class="ps">❯</span> cat tambal-pd.md
</button>
```

Per-card affordance text: `cat tambal-pd.md`, `cat school-admin.md`,
`cat doxie.md`.

The section's prompt-echo comment changes from `# a couple of favorites` to
`# a few favorites` (there are three now).

### 3.2 New Doxie card

Third `<article class="card reveal">` in `.project-grid`:

- **role:** `Creator · Hackathon Build`
- **h3:** `Doxie`
- **kind:** `CLI · AI-Native Documentation`
- **summary:** "Ship code and docs in one go — a TypeScript CLI that scaffolds an
  AI-driven documentation workflow into any repo. One `doxie init` installs
  Claude Code slash commands, doc templates, and runtime scripts, so docs are
  generated and kept current alongside the code."
- **ctags:** `TypeScript` `Node.js` `Claude Code` `CLI`

Grid impact: `.project-grid` already uses
`repeat(auto-fit, minmax(min(100%, 20rem), 1fr))`, so three cards render 3-up on
wide screens, 2+1 at medium widths, and stacked on mobile. No CSS change needed;
the lone third card at 2-column widths is acceptable.

### 3.3 Modal markup (one `<dialog>` per project, placed after `.project-grid`)

```html
<dialog class="term pmodal" id="modal-tambal" aria-labelledby="modal-tambal-title">
  <div class="term-bar">
    <div class="dots">
      <button class="dot r" data-close aria-label="Close project details"></button>
      <span class="dot y"></span><span class="dot g"></span>
    </div>
    <span class="t-title">~/projects/tambal-pd.md</span>
    <span class="t-state">[esc] close</span>
  </div>
  <div class="pmodal-body">
    <p class="prompt-echo"><span class="ps">❯</span> cat tambal-pd.md</p>
    <header class="pmodal-head">
      <span class="role">Lead Software &amp; Firmware Developer</span>
      <h3 id="modal-tambal-title">TAMBAL-PD</h3>
      <span class="kind">IoT · Smart Medicine Management</span>
    </header>

    <h4 class="md-h"><span>##</span> Overview</h4>
    <p>…</p>

    <h4 class="md-h"><span>##</span> Highlights</h4>
    <ul class="hl"> <li>…</li> </ul>

    <!-- Screenshots: uncomment when images land in assets/images/projects/
    <h4 class="md-h"><span>##</span> Screenshots</h4>
    <div class="shots">
      <figure>
        <img src="assets/images/projects/tambal-1.webp" alt="…" loading="lazy" width="1280" height="720">
        <figcaption>…</figcaption>
      </figure>
    </div>
    -->

    <div class="ctags"><span>Flutter</span> … </div>
    <div class="plinks">
      <a class="social-link" href="…" target="_blank" rel="noopener">GitHub ↗</a>
    </div>
  </div>
</dialog>
```

Structure notes:

- `.md-h` renders section headers like Markdown in a terminal pager — coral `##`
  prefix, mono font.
- `.hl` bullets reuse the `▸` treatment from `.entry li`.
- `.shots` is the image-gallery slot: a responsive grid of `<figure>` elements.
  **It only exists in a dialog's markup when that project has images**; a
  commented example lives in each dialog so adding pictures later is
  paste-and-uncomment. `loading="lazy"` + explicit `width`/`height` (no layout
  shift). Images live in a new `assets/images/projects/` directory.
- `.plinks` holds external links, reusing the existing `.social-link` style.

### 3.4 Modal content (copy drafts)

All facts below come from the current site copy and the Doxie README — nothing
invented. Enrich with anecdotes/numbers later if desired.

**TAMBAL-PD** (`~/projects/tambal-pd.md`)

- *Overview:* "TAMBAL-PD pairs a cross-platform Flutter app with a custom
  ESP32-based smart medicine dispenser. Caregivers schedule medications in the
  app; the dispenser authenticates residents with biometrics and dispenses the
  right dose at the right time, with everything synced through Firebase."
- *Highlights:*
  - Custom ESP32 firmware (Arduino C++) driving the dispensing hardware and the
    biometric module
  - Real-time sync between device, app, and cloud via Firebase
  - Deployed in an elderly-care facility — improved medication adherence for 30
    residents
  - Led both the software and firmware sides of the build
- *Tags:* Flutter · Firebase · ESP32 · Arduino C++
- *Links:* GitHub ↗ → `https://github.com/castorrr/tambal`

**Sisters of Mary — School Admin** (`~/projects/school-admin.md`)

- *Overview:* "An operations and records platform for the Sisters of Mary
  schools, serving 5,000+ students per campus. Built on Spring Boot with REST
  APIs over PostgreSQL: enrollment workflows, student records, and role-based
  access control, deployed for reliable multi-campus use."
- *Highlights:*
  - Designed and built the backend — REST APIs on Spring Boot over PostgreSQL
  - Enrollment workflows and student records at 5,000+ students per campus
  - Role-based access control for staff across campuses
- *Tags:* Spring Boot · PostgreSQL · REST · RBAC
- *Links:* Live site ↗ → `https://smsgirlstown.online/`

**Doxie** (`~/projects/doxie.md`)

- *Overview:* "Ship code and docs in one go. Doxie is a TypeScript CLI that
  scaffolds an AI-driven documentation workflow into any repo — so docs are
  generated by AI right where the code changes, instead of rotting in a wiki."
- *Highlights:*
  - `doxie init` scaffolds `doxie-docs/`, `.doxie/scripts/`, and
    `.claude/commands/doxie/` into a target repo — safe to re-run, `--force` to
    refresh templates
  - Template-driven: drop a Markdown prompt or TypeScript script under
    `templates/` and it ships — no code changes needed
  - Slash commands run inside Claude Code; scripts run via `tsx`, no build step
  - Hackathon build with a live landing page
- *Tags:* TypeScript · Node.js · Claude Code · CLI
- *Links:* Site ↗ → `https://castorrr.github.io/doxie/` · GitHub ↗ →
  `https://github.com/castorrr/doxie`

### 3.5 CSS additions (`css/styles.css`, ~90 lines, new "Project modals" block)

- `dialog.pmodal`:
  - `width: min(100% - 1.5rem, 44rem)`; `max-height: min(88dvh, 100dvh - 2rem)`;
    `margin: auto`; `padding: 0`; border/background/shadow come from the
    existing `.term` class.
  - `dialog.pmodal[open] { display: flex; flex-direction: column; }` — the
    `.term-bar` stays fixed while `.pmodal-body { overflow-y: auto; }` scrolls.
- `dialog.pmodal::backdrop { background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); }`
- Open animation: fade + slight scale-up via `@starting-style`; fully disabled
  under `@media (prefers-reduced-motion: reduce)`.
- `html.modal-open { overflow: hidden; }` — body scroll lock while a dialog is
  open.
- `.card[data-modal] { cursor: pointer; }`
- `.card-open`: mono prompt-line button — transparent background, no border,
  `padding-top: 1.1rem`, faint text with coral `❯`; on card hover / button
  focus-visible it brightens to coral. Focus ring via `outline` for
  `:focus-visible`.
- `.pmodal-head` mirrors the card header type styles (`.role`, `h3`, `.kind`
  already cascade — only spacing needed).
- `.md-h`: mono, small-caps-ish sizing; coral `##` in the inner `<span>`.
- `.hl li`: `▸` bullets (same pattern as `.entry li`).
- `.shots { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); gap: 0.75rem; }`
  with `img { width: 100%; height: auto; border: 1px solid var(--line); border-radius: 8px; }`
  and mono, faint `figcaption`. (Note the `min(100%, …)` floor — the known
  intrinsic-sizing trap.)
- `.plinks { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 1.5rem; }`

Mobile (≤ ~480 px): the same rules already yield a near-full-screen sheet
(`width: min(100% - 1.5rem, …)`); no separate breakpoint expected, verify at
320 px.

### 3.6 JS additions (`js/main.js`, ~30 lines, new "Project modals" block)

Follows the file's existing style (var, IIFE section, feature-detection):

```js
/* ---- Project modals -------------------------------------- */
document.querySelectorAll(".card[data-modal]").forEach(function (card) {
  var dlg = document.getElementById(card.getAttribute("data-modal"));
  if (!dlg || typeof dlg.showModal !== "function") return;
  card.addEventListener("click", function (e) {
    if (e.target.closest("a")) return;        // let real links act normally
    if (!dlg.open) {
      dlg.showModal();
      document.documentElement.classList.add("modal-open");
    }
  });
  dlg.addEventListener("click", function (e) {
    // backdrop click (target is the dialog itself) or the red dot
    if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
  });
  dlg.addEventListener("close", function () {
    document.documentElement.classList.remove("modal-open");
  });
});
```

Behavior summary:

- **Open:** click/tap anywhere on the card, or Tab to the `.card-open` button
  and press Enter/Space (button click bubbles to the card handler).
- **Close:** Esc (native), backdrop click, or the red traffic-light dot (a real
  button with `aria-label`).
- **Focus:** `showModal()` moves focus into the dialog (first focusable = the
  close dot) and restores it to the opener on close — native behavior, no JS.
- **No JS / old browser:** `data-modal` is inert, `showModal` feature-check
  bails out; cards render exactly as today.

### 3.7 Accessibility checklist

- Dialogs: `aria-labelledby` → project `<h3>`; opener buttons:
  `aria-haspopup="dialog"` + `aria-controls`.
- Close dot: real `<button>` with `aria-label="Close project details"`; the
  `[esc] close` hint in the title bar is visual reinforcement, not the only cue.
- All gallery images require meaningful `alt` text when added.
- Scroll containment: only `.pmodal-body` scrolls; page scroll locked while
  open.
- Reduced motion: no open/close animation.

### 3.8 Out of scope (possible later passes)

- Lightbox / zoom on gallery images (modal-in-modal — skipped deliberately).
- Hero-terminal tie-in (e.g. `cat doxie.md` in the command line opening the
  modal).
- Deep links (`#project=doxie` opening a modal on load).
- Real screenshots — Castor adds files to `assets/images/projects/` and
  uncomments the `.shots` block per project.

## 4. File change summary

| File | Change |
| --- | --- |
| `index.html` | Doxie card; `data-modal` + `.card-open` on all 3 cards; 3 `<dialog>` blocks; tweak `ls` comment |
| `css/styles.css` | New "Project modals" block (~90 lines) |
| `js/main.js` | New "Project modals" block (~30 lines) |
| `assets/images/projects/` | New empty directory (with `.gitkeep`) for future screenshots |

## 5. Validation plan

1. Serve locally: `python3 -m http.server`.
2. Playwright with system Chrome (`channel: 'chrome'`) — screenshots at 320,
   375, 768, 1024, 1440 px: grid layout with 3 cards; each modal open state.
3. Interaction checks: open via click and via keyboard; close via Esc, backdrop,
   red dot; focus returns to the card button; background doesn't scroll while
   open; no horizontal overflow at 320 px.
4. Reduced-motion check (`prefers-reduced-motion: reduce` emulation): no
   animations, everything still opens/closes.
5. Temporarily drop a test image into one `.shots` block to verify the gallery
   grid, then remove it (support ships, pictures come later).
