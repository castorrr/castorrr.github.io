# Expandable Project Cards + Doxie — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each project card a terminal-window detail modal (native `<dialog>`), add a third card for Doxie, and add live/thesis status badges — per the approved spec at `docs/superpowers/specs/2026-07-11-expandable-projects-design.md`.

**Architecture:** Pure static site. Each of the 3 project cards gets a `data-modal` attribute pointing at its own `<dialog class="term pmodal">` element that reuses the existing terminal chrome. ~30 lines of vanilla JS wire click-to-open and three close paths (Esc, backdrop, red dot); native `showModal()` provides focus trap/restore. No data layer, no templates, no dependencies.

**Tech Stack:** Vanilla HTML/CSS/JS. Verification via `python3 -m http.server` + a throwaway Playwright harness (system Chrome, `channel: 'chrome'`) that lives **outside the repo** and is never committed.

## Global Constraints

Copied from the spec + project memory — every task implicitly includes these:

- **Terminal-noir theme** — new UI must reuse the existing terminal chrome (`.term`, `.term-bar`, `.dots`, `.dot r/y/g`, `.prompt-echo`, coral `❯`), not look bolted on.
- **No build step, no frameworks** — vanilla HTML/CSS/JS only. Nothing gets added to the repo except the four files in the spec's change summary. The Playwright harness lives in `/tmp/pmodal-verify`, outside the repo.
- **Mobile is the primary viewport** — verify at **320 px** before judging desktop. Known trap: grid `minmax()` floors must be wrapped `min(100%, …)` or tracks exceed tiny viewports.
- **Images: support now, pictures later.** No project has images yet. The `.shots` gallery markup ships **commented out** in every dialog; nothing may look broken without images.
- **JS style of `js/main.js`:** `var` (no `let`/`const`), function expressions, section banners like `/* ---- Name ------- */`, feature-detection guards, everything inside the existing IIFE.
- **CSS style of `css/styles.css`:** use existing custom properties (`--coral`, `--green`, `--line`, `--line-2`, `--text-faint`, `--text-soft`, `--font-mono`, `--radius-sm`, `--dur`, `--ease`); section banners like `/* ---- Name ------------------- */`; the global reduced-motion block at the end of the file already kills all animations/transitions — do **not** add per-feature reduced-motion rules.
- **Copy is verbatim from spec §3.4** — no invented facts, no invented links.
- **Commit style:** imperative, capitalized subject, no `feat:` prefixes (matches repo history, e.g. "Move mobile burger to right edge of header"). End every commit message with the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.
- **Out of scope (do not build):** lightbox/zoom on images, hero-terminal `cat doxie.md` tie-in, deep links (`#project=doxie`), real screenshots.

## File Structure

| File | Responsibility |
| --- | --- |
| `index.html` | Projects section only: 3 cards (with `data-modal`, `.card-top` badge row, `.card-open` button), 3 `<dialog>` blocks after `.project-grid`, one comment tweak |
| `css/styles.css` | Two touch points: (a) extend 5 card-typography selectors to also cover `.pmodal`, plus new card-affordance rules, inside the existing `/* ---- Projects */` block; (b) a new `/* ---- Project modals */` block between Projects and Contact |
| `js/main.js` | One new `/* ---- Project modals */` section (~20 lines) inserted after the Footer-year section, inside the existing IIFE |
| `assets/images/projects/.gitkeep` | New empty directory for future screenshots |

**Key existing code you'll build on (do not modify except where a task says so):**

- `.term` / `.term-bar` chrome: `css/styles.css:333-380`. Note `.term-bar .dot` is element-agnostic (styles `<button class="dot">` too), but a `<button>` keeps its UA border/padding — the modal CSS resets that.
- `pulse` keyframes: `css/styles.css:376-380` — reused by the status badge dot.
- Card typography is **scoped under `.card`** (`css/styles.css:758-773`) — the spec assumes `.role`/`h3`/`.kind`/`.ctags` "already cascade" into the modal, but they don't; Task 2 extends those selectors.
- `.entry li` `▸` bullets pattern: `css/styles.css:732-736` — mirrored by `.hl li`.
- `.prompt-echo` (unscoped, works inside dialogs as-is): `css/styles.css:684-691`.
- Global `:focus-visible` coral outline: `css/styles.css:72-76` — covers the new buttons for free.
- Global reduced-motion kill-switch: `css/styles.css:958-966`.
- `.mono` utility class exists: `css/styles.css:173`.

## ID / class contract (used across tasks)

| Name | Meaning |
| --- | --- |
| `data-modal="modal-tambal" / "modal-school" / "modal-doxie"` | On each `<article class="card">`; value = id of its dialog |
| `#modal-tambal`, `#modal-school`, `#modal-doxie` | The three `<dialog class="term pmodal">` elements |
| `#modal-tambal-title` etc. | `<h3>` inside each dialog; target of that dialog's `aria-labelledby` |
| `button.card-open[aria-haspopup="dialog"][aria-controls="<dialog-id>"]` | Keyboard-accessible opener inside each card |
| `button.dot.r[data-close]` | Red traffic-light dot inside each dialog's `.term-bar`; JS closes on it |
| `html.modal-open` | Set while any dialog is open; CSS locks page scroll |

---

### Task 1: Cards — Doxie card, status badges, open affordances (HTML + CSS)

**Files:**
- Modify: `index.html:343-367` (Projects section: prompt-echo comment + the two existing cards + new third card)
- Modify: `css/styles.css` — append to the `/* ---- Projects */` block (after line 773, before `/* ---- Contact */` at line 775)

**Interfaces:**
- Consumes: existing `.card`, `.role`, `.kind`, `.ctags`, `.reveal`, `.ps` classes; `pulse` keyframes; `--coral`/`--green`/`--font-mono`/`--dur`/`--ease` tokens.
- Produces: `data-modal` attributes and `aria-controls` values `modal-tambal`/`modal-school`/`modal-doxie` (Task 2's dialogs must use exactly these ids); the `.card-top` + `.status status--live|--thesis` markup pattern (Task 2 mirrors it inside `.pmodal-head`); `.card-open` button pattern (Task 3 relies on its click bubbling to the card).

- [ ] **Step 1: Set up the verification harness (one-time, outside the repo)**

The harness directory is `/tmp/pmodal-verify` (fixed path so every later shell finds it). System Chrome is at `/usr/bin/google-chrome`, so Playwright needs no browser download.

Run:
```bash
mkdir -p /tmp/pmodal-verify/shots && cd /tmp/pmodal-verify && npm init -y >/dev/null 2>&1 && npm i playwright >/dev/null 2>&1 && node -e "require('playwright'); console.log('playwright ok')"
```
Expected: `playwright ok`

Then start the static server as a **background** task from the repo root (the worktree you're editing):
```bash
python3 -m http.server 8123
```
Verify it's up:
```bash
curl -sI http://localhost:8123/ | head -1
```
Expected: `HTTP/1.0 200 OK`

- [ ] **Step 2: Write the failing check script**

Create `/tmp/pmodal-verify/check-cards.js`:

```js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto("http://localhost:8123/", { waitUntil: "networkidle" });
  const assert = (cond, msg) => { if (!cond) throw new Error(msg); };

  const cards = page.locator(".project-grid .card");
  assert((await cards.count()) === 3, "expected 3 project cards, got " + (await cards.count()));

  const titles = (await page.locator(".project-grid .card h3").allTextContents()).map((t) => t.trim());
  assert(
    JSON.stringify(titles) === JSON.stringify(["TAMBAL-PD", "Sisters of Mary — School Admin", "Doxie"]),
    "unexpected card titles: " + JSON.stringify(titles)
  );

  assert((await page.locator(".card .status--thesis").count()) === 1, "expected 1 thesis badge");
  assert((await page.locator(".card .status--live").count()) === 2, "expected 2 live badges");
  assert((await page.locator(".card .status--live .dotpulse").count()) === 2, "live badges need pulse dots");
  assert((await page.locator(".card .status--thesis .dotpulse").count()) === 0, "thesis badge must have no dot");

  const opens = await page.locator(".card button.card-open").allTextContents();
  assert(opens.length === 3, "expected 3 .card-open buttons, got " + opens.length);
  assert(opens[0].includes("cat tambal-pd.md"), "tambal affordance text wrong: " + opens[0]);
  assert(opens[1].includes("cat school-admin.md"), "school affordance text wrong: " + opens[1]);
  assert(opens[2].includes("cat doxie.md"), "doxie affordance text wrong: " + opens[2]);

  for (const id of ["modal-tambal", "modal-school", "modal-doxie"]) {
    assert((await page.locator('.card[data-modal="' + id + '"]').count()) === 1, "missing card[data-modal=" + id + "]");
    assert((await page.locator('button.card-open[aria-controls="' + id + '"]').count()) === 1, "missing aria-controls=" + id);
  }

  const echo = await page.locator("#projects .prompt-echo").textContent();
  assert(echo.includes("# a few favorites"), "ls comment not updated: " + echo);

  // status chip must sit on the same row as the role (baseline flex row)
  const sameRow = await page.evaluate(() => {
    const top = document.querySelector(".card .card-top");
    return getComputedStyle(top).display === "flex" && getComputedStyle(top).justifyContent === "space-between";
  });
  assert(sameRow, ".card-top must be a space-between flex row");

  console.log("PASS check-cards");
  await browser.close();
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
```

- [ ] **Step 3: Run it to verify it fails**

Run: `node /tmp/pmodal-verify/check-cards.js`
Expected: `FAIL: expected 3 project cards, got 2`

- [ ] **Step 4: Edit the Projects section in `index.html`**

At `index.html:343`, change the prompt-echo comment (`a couple` → `a few`):

```html
        <p class="prompt-echo reveal" style="margin-bottom:2.5rem"><span class="ps">❯</span> ls -la ~/projects <span class="c"># a few favorites</span></p>
```

Replace the entire `.project-grid` div (`index.html:344-367`) with (keeps the existing summary copy verbatim; adds `data-modal`, `.card-top` rows, badges, `.card-open` buttons, and the Doxie card):

```html
        <div class="project-grid">
          <article class="card reveal" data-modal="modal-tambal">
            <div class="card-top">
              <span class="role">Lead Software &amp; Firmware Developer</span>
              <span class="status status--thesis">thesis</span>
            </div>
            <h3>TAMBAL-PD</h3>
            <span class="kind">IoT · Smart Medicine Management</span>
            <p>
              A Flutter + Firebase app paired with a custom ESP32 smart medicine dispenser —
              biometric authentication, automated dispensing, and cloud sync. Deployed in an
              elderly-care facility, improving medication adherence for 30 residents.
            </p>
            <div class="ctags"><span>Flutter</span><span>Firebase</span><span>ESP32</span><span>Arduino C++</span></div>
            <button class="card-open" aria-haspopup="dialog" aria-controls="modal-tambal">
              <span class="ps">❯</span> cat tambal-pd.md
            </button>
          </article>
          <article class="card reveal" data-modal="modal-school">
            <div class="card-top">
              <span class="role">Lead Backend Developer</span>
              <span class="status status--live"><i class="dotpulse"></i>live</span>
            </div>
            <h3>Sisters of Mary — School Admin</h3>
            <span class="kind">Web · 5,000+ students / campus</span>
            <p>
              A school operations &amp; records platform built on Spring Boot: enrollment
              workflows, student records, and role-based access. REST APIs over PostgreSQL,
              deployed for reliable multi-campus access.
            </p>
            <div class="ctags"><span>Spring Boot</span><span>PostgreSQL</span><span>REST</span><span>RBAC</span></div>
            <button class="card-open" aria-haspopup="dialog" aria-controls="modal-school">
              <span class="ps">❯</span> cat school-admin.md
            </button>
          </article>
          <article class="card reveal" data-modal="modal-doxie">
            <div class="card-top">
              <span class="role">Creator</span>
              <span class="status status--live"><i class="dotpulse"></i>live</span>
            </div>
            <h3>Doxie</h3>
            <span class="kind">CLI · AI-Native Documentation</span>
            <p>
              Ship code and docs in one go — a TypeScript CLI that scaffolds an AI-driven
              documentation workflow into any repo. One <span class="mono">doxie init</span>
              installs Claude Code slash commands, doc templates, and runtime scripts, so
              docs are generated and kept current alongside the code.
            </p>
            <div class="ctags"><span>TypeScript</span><span>Node.js</span><span>Claude Code</span><span>CLI</span></div>
            <button class="card-open" aria-haspopup="dialog" aria-controls="modal-doxie">
              <span class="ps">❯</span> cat doxie.md
            </button>
          </article>
        </div>
```

- [ ] **Step 5: Add the card CSS**

In `css/styles.css`, directly after the `.card .ctags span { … }` rule closes (line 773) and before the `/* ---- Contact */` banner (line 775), insert:

```css
/* clickable cards: status badge row + prompt-line open affordance */
.card[data-modal] { cursor: pointer; }
.card-top {
  display: flex; align-items: baseline;
  justify-content: space-between; gap: 0.75rem;
}
.status {
  display: inline-flex; align-items: center; gap: 0.45rem;
  flex: none;
  font-family: var(--font-mono); font-size: 0.7rem;
  text-transform: uppercase; letter-spacing: 0.08em;
}
.status--live { color: var(--green); }
.status--thesis { color: var(--coral); }
.status .dotpulse {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor;
  animation: pulse 2.2s infinite;
}
.card-open {
  background: none; border: 0;
  padding: 1.1rem 0 0;
  text-align: left; cursor: pointer;
  font-family: var(--font-mono); font-size: 0.8rem;
  color: var(--text-faint);
  transition: color var(--dur) var(--ease);
}
.card-open .ps { color: var(--coral); margin-right: 0.55rem; }
.card:hover .card-open,
.card-open:focus-visible { color: var(--coral); }
```

Notes on why this shape:
- `.status .dotpulse` gets its own size/background rule because the existing dot is scoped `.term-bar .dotpulse` (`css/styles.css:370-375`); only the `pulse` keyframes are shared. `background: currentColor` keeps the dot green inside `.status--live` with no extra rule. The global reduced-motion block already suppresses the animation.
- `.card-open` is a flex child of the column-flex `.card`, so it stretches full width (good touch target); `text-align: left` counters the button UA centering. Focus ring comes from the global `:focus-visible` rule — do not add one.
- `.card-top` replaces the bare `.role` span as the card's first row; `.card h3` margin (`0.5rem 0 0.15rem`) already provides spacing below it.

- [ ] **Step 6: Run the check to verify it passes**

Run: `node /tmp/pmodal-verify/check-cards.js`
Expected: `PASS check-cards`

- [ ] **Step 7: Eyeball it (mobile first)**

```bash
cd /tmp/pmodal-verify && node -e "
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const w of [320, 1440]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    await p.goto('http://localhost:8123/#projects', { waitUntil: 'networkidle' });
    await p.waitForTimeout(800);
    await p.screenshot({ path: 'shots/task1-cards-' + w + '.png' });
    await p.close();
  }
  await b.close();
})();"
```

Read `/tmp/pmodal-verify/shots/task1-cards-320.png` and `task1-cards-1440.png`. Confirm: three cards; badge sits right of the role on the same line (thesis = coral on TAMBAL-PD, live = green on the other two); each card ends with a faint mono `❯ cat …` line; nothing overflows at 320 px.

- [ ] **Step 8: Commit**

```bash
git add index.html css/styles.css
git commit -m "$(cat <<'EOF'
Add Doxie card, status badges, and open affordances to project cards

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Project detail modals — markup + CSS (no behavior yet)

**Files:**
- Modify: `index.html` — insert three `<dialog>` blocks after the closing `</div>` of `.project-grid`, before the `</div>` that closes `.container` in the Projects section
- Modify: `css/styles.css:758-773` — extend five card-typography selectors to also match `.pmodal`
- Modify: `css/styles.css` — new `/* ---- Project modals */` block between the Projects block (incl. Task 1's additions) and `/* ---- Contact */`
- Create: `assets/images/projects/.gitkeep` (empty file; reserves the future screenshots directory)

**Interfaces:**
- Consumes: dialog ids `modal-tambal`/`modal-school`/`modal-doxie` promised by Task 1's `data-modal` values; existing `.term`, `.term-bar`, `.prompt-echo`, `.social-link` styles; `.card-top`/`.status` pattern from Task 1.
- Produces: three `<dialog class="term pmodal" id="modal-*">` elements each containing exactly one `button.dot.r[data-close]`; the `html.modal-open { overflow: hidden; }` rule. Task 3's JS depends on: the ids, `[data-close]`, and the `modal-open` class name.

- [ ] **Step 1: Write the failing check script**

Create `/tmp/pmodal-verify/check-modals.js`:

```js
const { chromium } = require("playwright");

const MODALS = {
  "modal-tambal": { title: "~/projects/tambal-pd.md", h3: "TAMBAL-PD", links: 1 },
  "modal-school": { title: "~/projects/school-admin.md", h3: "Sisters of Mary — School Admin", links: 1 },
  "modal-doxie": { title: "~/projects/doxie.md", h3: "Doxie", links: 2 },
};

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 320, height: 700 } });
  await page.goto("http://localhost:8123/", { waitUntil: "networkidle" });
  const assert = (cond, msg) => { if (!cond) throw new Error(msg); };

  for (const [id, exp] of Object.entries(MODALS)) {
    const exists = await page.evaluate((id) => !!document.getElementById(id), id);
    assert(exists, "missing <dialog id=" + id + ">");

    await page.evaluate((id) => document.getElementById(id).showModal(), id);
    const dlg = page.locator("#" + id);
    await dlg.waitFor({ state: "visible" });

    assert((await dlg.locator(".t-title").textContent()).trim() === exp.title, id + ": wrong title-bar text");
    assert((await dlg.locator(".t-state").textContent()).includes("[esc] close"), id + ": missing [esc] close hint");
    assert((await dlg.locator("h3").textContent()).trim() === exp.h3, id + ": wrong heading");
    assert((await dlg.getAttribute("aria-labelledby")) === id + "-title", id + ": aria-labelledby must be " + id + "-title");
    assert((await dlg.locator("h3").getAttribute("id")) === id + "-title", id + ": h3 id must be " + id + "-title");
    assert((await dlg.locator('button.dot.r[data-close][aria-label="Close project details"]').count()) === 1, id + ": close dot");
    assert((await dlg.locator(".card-top .status").count()) === 1, id + ": status badge must be mirrored in the modal head");
    assert((await dlg.locator(".md-h").count()) === 2, id + ": expected exactly Overview + Highlights headers (screenshots stay commented)");
    assert((await dlg.locator(".hl li").count()) >= 3, id + ": highlights list too short");
    assert((await dlg.locator(".plinks a.social-link").count()) === exp.links, id + ": wrong link count");
    assert((await dlg.locator(".shots").count()) === 0, id + ": .shots must not render while there are no images");

    const fits = await page.evaluate((id) => {
      const r = document.getElementById(id).getBoundingClientRect();
      return r.width <= window.innerWidth && r.height <= window.innerHeight;
    }, id);
    assert(fits, id + ": dialog overflows the 320px viewport");

    const bodyScrolls = await page.evaluate((id) => {
      const d = document.getElementById(id);
      return getComputedStyle(d.querySelector(".pmodal-body")).overflowY === "auto" && getComputedStyle(d).display === "flex";
    }, id);
    assert(bodyScrolls, id + ": term-bar must stay fixed while .pmodal-body scrolls");

    const noPageOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    assert(noPageOverflow, id + ": horizontal page overflow at 320px");

    await page.screenshot({ path: "shots/" + id + "-320.png" });
    await page.evaluate((id) => document.getElementById(id).close(), id);
  }

  console.log("PASS check-modals");
  await browser.close();
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node /tmp/pmodal-verify/check-modals.js`
Expected: `FAIL: missing <dialog id=modal-tambal>`

- [ ] **Step 3: Add the three dialogs to `index.html`**

Insert directly after the closing `</div>` of `.project-grid` (still inside the section's `.container` div). All copy is verbatim from spec §3.4.

```html
        <!-- Project detail modals — one terminal window per project.
             Screenshots: each dialog carries a commented .shots block;
             drop images into assets/images/projects/ and uncomment. -->
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
              <div class="card-top">
                <span class="role">Lead Software &amp; Firmware Developer</span>
                <span class="status status--thesis">thesis</span>
              </div>
              <h3 id="modal-tambal-title">TAMBAL-PD</h3>
              <span class="kind">IoT · Smart Medicine Management</span>
            </header>

            <h4 class="md-h"><span>##</span> Overview</h4>
            <p>
              TAMBAL-PD pairs a cross-platform Flutter app with a custom ESP32-based smart
              medicine dispenser. Caregivers schedule medications in the app; the dispenser
              authenticates residents with biometrics and dispenses the right dose at the
              right time, with everything synced through Firebase.
            </p>

            <h4 class="md-h"><span>##</span> Highlights</h4>
            <ul class="hl">
              <li>Custom ESP32 firmware (Arduino C++) driving the dispensing hardware and the biometric module</li>
              <li>Real-time sync between device, app, and cloud via Firebase</li>
              <li>Deployed in an elderly-care facility — improved medication adherence for 30 residents</li>
              <li>Led both the software and firmware sides of the build</li>
              <li>Computer Engineering thesis project (CIT-U)</li>
            </ul>

            <!-- Screenshots: uncomment when images land in assets/images/projects/
            <h4 class="md-h"><span>##</span> Screenshots</h4>
            <div class="shots">
              <figure>
                <img src="assets/images/projects/tambal-1.webp" alt="" loading="lazy" width="1280" height="720">
                <figcaption></figcaption>
              </figure>
            </div>
            -->

            <div class="ctags"><span>Flutter</span><span>Firebase</span><span>ESP32</span><span>Arduino C++</span></div>
            <div class="plinks">
              <a class="social-link" href="https://github.com/castorrr/tambal" target="_blank" rel="noopener">GitHub ↗</a>
            </div>
          </div>
        </dialog>

        <dialog class="term pmodal" id="modal-school" aria-labelledby="modal-school-title">
          <div class="term-bar">
            <div class="dots">
              <button class="dot r" data-close aria-label="Close project details"></button>
              <span class="dot y"></span><span class="dot g"></span>
            </div>
            <span class="t-title">~/projects/school-admin.md</span>
            <span class="t-state">[esc] close</span>
          </div>
          <div class="pmodal-body">
            <p class="prompt-echo"><span class="ps">❯</span> cat school-admin.md</p>
            <header class="pmodal-head">
              <div class="card-top">
                <span class="role">Lead Backend Developer</span>
                <span class="status status--live"><i class="dotpulse"></i>live</span>
              </div>
              <h3 id="modal-school-title">Sisters of Mary — School Admin</h3>
              <span class="kind">Web · 5,000+ students / campus</span>
            </header>

            <h4 class="md-h"><span>##</span> Overview</h4>
            <p>
              An operations and records platform for the Sisters of Mary schools, serving
              5,000+ students per campus. Built on Spring Boot with REST APIs over
              PostgreSQL: enrollment workflows, student records, and role-based access
              control, deployed for reliable multi-campus use.
            </p>

            <h4 class="md-h"><span>##</span> Highlights</h4>
            <ul class="hl">
              <li>Designed and built the backend — REST APIs on Spring Boot over PostgreSQL</li>
              <li>Enrollment workflows and student records at 5,000+ students per campus</li>
              <li>Role-based access control for staff across campuses</li>
            </ul>

            <!-- Screenshots: uncomment when images land in assets/images/projects/
            <h4 class="md-h"><span>##</span> Screenshots</h4>
            <div class="shots">
              <figure>
                <img src="assets/images/projects/school-admin-1.webp" alt="" loading="lazy" width="1280" height="720">
                <figcaption></figcaption>
              </figure>
            </div>
            -->

            <div class="ctags"><span>Spring Boot</span><span>PostgreSQL</span><span>REST</span><span>RBAC</span></div>
            <div class="plinks">
              <a class="social-link" href="https://smsgirlstown.online/" target="_blank" rel="noopener">Live site ↗</a>
            </div>
          </div>
        </dialog>

        <dialog class="term pmodal" id="modal-doxie" aria-labelledby="modal-doxie-title">
          <div class="term-bar">
            <div class="dots">
              <button class="dot r" data-close aria-label="Close project details"></button>
              <span class="dot y"></span><span class="dot g"></span>
            </div>
            <span class="t-title">~/projects/doxie.md</span>
            <span class="t-state">[esc] close</span>
          </div>
          <div class="pmodal-body">
            <p class="prompt-echo"><span class="ps">❯</span> cat doxie.md</p>
            <header class="pmodal-head">
              <div class="card-top">
                <span class="role">Creator</span>
                <span class="status status--live"><i class="dotpulse"></i>live</span>
              </div>
              <h3 id="modal-doxie-title">Doxie</h3>
              <span class="kind">CLI · AI-Native Documentation</span>
            </header>

            <h4 class="md-h"><span>##</span> Overview</h4>
            <p>
              Ship code and docs in one go. Doxie is a TypeScript CLI that scaffolds an
              AI-driven documentation workflow into any repo — so docs are generated by AI
              right where the code changes, instead of rotting in a wiki.
            </p>

            <h4 class="md-h"><span>##</span> Highlights</h4>
            <ul class="hl">
              <li><span class="mono">doxie init</span> scaffolds <span class="mono">doxie-docs/</span>, <span class="mono">.doxie/scripts/</span>, and <span class="mono">.claude/commands/doxie/</span> into a target repo — safe to re-run, <span class="mono">--force</span> to refresh templates</li>
              <li>Template-driven: drop a Markdown prompt or TypeScript script under <span class="mono">templates/</span> and it ships — no code changes needed</li>
              <li>Slash commands run inside Claude Code; scripts run via <span class="mono">tsx</span>, no build step</li>
              <li>Live landing page and public repo</li>
            </ul>

            <!-- Screenshots: uncomment when images land in assets/images/projects/
            <h4 class="md-h"><span>##</span> Screenshots</h4>
            <div class="shots">
              <figure>
                <img src="assets/images/projects/doxie-1.webp" alt="" loading="lazy" width="1280" height="720">
                <figcaption></figcaption>
              </figure>
            </div>
            -->

            <div class="ctags"><span>TypeScript</span><span>Node.js</span><span>Claude Code</span><span>CLI</span></div>
            <div class="plinks">
              <a class="social-link" href="https://castorrr.github.io/doxie/" target="_blank" rel="noopener">Site ↗</a>
              <a class="social-link" href="https://github.com/castorrr/doxie" target="_blank" rel="noopener">GitHub ↗</a>
            </div>
          </div>
        </dialog>
```

(The commented `.shots` examples have empty `alt`/`figcaption` on purpose — real text gets written when real images land; spec §3.7 requires meaningful alt text *when added*.)

- [ ] **Step 4: Extend the card typography selectors in `css/styles.css`**

The modal head reuses `.role`/`h3`/`.kind`/`.ctags`, but those rules are scoped under `.card` (`css/styles.css:758-773`). Widen exactly these five selectors (rule bodies unchanged):

| Before | After |
| --- | --- |
| `.card .role {` | `.card .role, .pmodal .role {` |
| `.card h3 {` | `.card h3, .pmodal h3 {` |
| `.card .kind {` | `.card .kind, .pmodal .kind {` |
| `.card .ctags {` | `.card .ctags, .pmodal .ctags {` |
| `.card .ctags span {` | `.card .ctags span, .pmodal .ctags span {` |

- [ ] **Step 5: Add the "Project modals" CSS block**

Insert between the end of the Projects block (after Task 1's `.card-open` rules) and the `/* ---- Contact */` banner:

```css
/* ---- Project modals ---------------------------------------- */
/* Each project's detail view is a native <dialog> dressed as another
   terminal window (.term chrome). showModal() gives Esc, focus trap,
   and ::backdrop for free — see the "Project modals" block in main.js. */
dialog.pmodal {
  width: min(100% - 1.5rem, 44rem);
  max-height: min(88dvh, 100dvh - 2rem);
  margin: auto;
  padding: 0;
  color: var(--text); /* dialog UA default is CanvasText (black) */
}
dialog.pmodal[open] {
  display: flex; flex-direction: column;
  opacity: 1; transform: scale(1);
  transition: opacity 0.22s var(--ease), transform 0.22s var(--ease);
}
@starting-style {
  dialog.pmodal[open] { opacity: 0; transform: scale(0.97); }
}
dialog.pmodal::backdrop {
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
}
html.modal-open { overflow: hidden; } /* page scroll lock while a dialog is open */

.pmodal .term-bar { flex: none; }
.pmodal .term-bar button.dot { border: 0; padding: 0; cursor: pointer; } /* strip <button> UA chrome off the red dot */
.pmodal-body {
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: clamp(1.25rem, 4.5vw, 2.25rem);
}
.pmodal-body .prompt-echo { margin-bottom: 1.5rem; }
.pmodal-body > p { color: var(--text-soft); font-size: 0.95rem; }

/* section headers, rendered like Markdown in a terminal pager */
.md-h {
  margin: 1.9rem 0 0.65rem;
  font-family: var(--font-mono);
  font-size: 0.8rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text);
}
.md-h span { color: var(--coral); margin-right: 0.5rem; }

/* highlights — same ▸ treatment as .entry li */
.hl { display: grid; gap: 0.5rem; }
.hl li {
  position: relative; padding-left: 1.25rem;
  color: var(--text-soft); font-size: 0.95rem;
}
.hl li::before { content: "▸"; position: absolute; left: 0; color: var(--coral); }

/* screenshot gallery — markup stays commented out until images exist */
.shots {
  display: grid;
  /* min(100%,…) keeps the track floor from exceeding tiny viewports */
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  gap: 0.75rem;
}
.shots img {
  width: 100%; height: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.shots figcaption {
  font-family: var(--font-mono); font-size: 0.72rem;
  color: var(--text-faint);
  margin-top: 0.4rem;
}

.plinks { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 1.5rem; }
```

Do **not** add reduced-motion rules: the global block at `css/styles.css:958-966` already forces `transition-duration: 0.001ms` on everything, which disables the open animation, and neutralizes the badge pulse.

- [ ] **Step 6: Create the images directory**

```bash
mkdir -p assets/images/projects && touch assets/images/projects/.gitkeep
```

- [ ] **Step 7: Run the check to verify it passes**

Run: `node /tmp/pmodal-verify/check-modals.js`
Expected: `PASS check-modals`

- [ ] **Step 8: Eyeball the three modals**

Read `/tmp/pmodal-verify/shots/modal-tambal-320.png`, `modal-school-320.png`, `modal-doxie-320.png`. Confirm each looks like a terminal window: title bar with dots + `~/projects/….md` + `[esc] close`; `❯ cat …` prompt echo; role/badge/title head; coral `##` section headers; `▸` bullets; tag chips; pill links. No layout breakage where the commented screenshots block sits.

- [ ] **Step 9: Commit**

```bash
git add index.html css/styles.css assets/images/projects/.gitkeep
git commit -m "$(cat <<'EOF'
Add per-project detail modals styled as terminal windows

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Wire the modals — open/close behavior (JS)

**Files:**
- Modify: `js/main.js` — insert a new section after the `/* ---- Footer year */` block (after line 74, before the battle comment block at line 76)

**Interfaces:**
- Consumes: `.card[data-modal]` attributes (Task 1); `<dialog id>` elements with `[data-close]` buttons (Task 2); `html.modal-open` scroll-lock rule (Task 2).
- Produces: the complete user-facing behavior. No later task consumes JS symbols.

- [ ] **Step 1: Write the failing check script**

Create `/tmp/pmodal-verify/check-interactions.js`:

```js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto("http://localhost:8123/", { waitUntil: "networkidle" });
  const assert = (cond, msg) => { if (!cond) throw new Error(msg); };
  const isOpen = (id) => page.evaluate((id) => document.getElementById(id).open, id);
  const hasLock = () => page.evaluate(() => document.documentElement.classList.contains("modal-open"));

  // 1. click anywhere on the card → opens + scroll lock
  const tambal = page.locator('.card[data-modal="modal-tambal"]');
  await tambal.scrollIntoViewIfNeeded();
  await tambal.click({ position: { x: 20, y: 20 } });
  assert(await isOpen("modal-tambal"), "card click should open its dialog");
  assert(await hasLock(), "html.modal-open missing while dialog is open");

  // 2. Esc → closes + releases the lock
  await page.keyboard.press("Escape");
  assert(!(await isOpen("modal-tambal")), "Esc should close the dialog");
  assert(!(await hasLock()), "html.modal-open should be removed on close");

  // 3. keyboard path: focus .card-open, Enter opens, Esc restores focus to the opener
  await page.locator('button[aria-controls="modal-school"]').focus();
  await page.keyboard.press("Enter");
  assert(await isOpen("modal-school"), "Enter on .card-open should open the dialog");
  await page.keyboard.press("Escape");
  const restored = await page.evaluate(
    () => document.activeElement === document.querySelector('button[aria-controls="modal-school"]')
  );
  assert(restored, "focus should return to the opener button after close");

  // 4. red traffic-light dot closes
  const doxie = page.locator('.card[data-modal="modal-doxie"]');
  await doxie.scrollIntoViewIfNeeded();
  await doxie.click({ position: { x: 20, y: 20 } });
  assert(await isOpen("modal-doxie"), "doxie card click should open its dialog");
  await page.locator("#modal-doxie [data-close]").click();
  assert(!(await isOpen("modal-doxie")), "red dot should close the dialog");
  assert(!(await hasLock()), "lock should release after red-dot close");

  // 5. backdrop click closes (top-left corner is outside the centered dialog)
  await tambal.scrollIntoViewIfNeeded();
  await tambal.click({ position: { x: 20, y: 20 } });
  assert(await isOpen("modal-tambal"), "reopen for backdrop test");
  await page.mouse.click(4, 4);
  assert(!(await isOpen("modal-tambal")), "backdrop click should close the dialog");

  // 6. links inside a modal are real links (card handler must not swallow them)
  await doxie.click({ position: { x: 20, y: 20 } });
  const href = await page.locator("#modal-doxie .plinks a").first().getAttribute("href");
  assert(href === "https://castorrr.github.io/doxie/", "doxie first link href wrong: " + href);
  await page.keyboard.press("Escape");

  console.log("PASS check-interactions");
  await browser.close();
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node /tmp/pmodal-verify/check-interactions.js`
Expected: `FAIL: card click should open its dialog`

- [ ] **Step 3: Add the JS**

In `js/main.js`, insert after the Footer-year section (line 74) and before the battle banner comment (line 76) — inside the existing IIFE, matching its `var`/function-expression style:

```js
  /* ---- Project modals -------------------------------------- */
  document.querySelectorAll(".card[data-modal]").forEach(function (card) {
    var dlg = document.getElementById(card.getAttribute("data-modal"));
    if (!dlg || typeof dlg.showModal !== "function") return; // no dialog support → cards stay static
    card.addEventListener("click", function (e) {
      if (e.target.closest("a")) return; // let real links act normally
      if (!dlg.open) {
        dlg.showModal();
        document.documentElement.classList.add("modal-open");
      }
    });
    dlg.addEventListener("click", function (e) {
      // backdrop click (target is the dialog itself) or the red traffic-light dot
      if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
    });
    dlg.addEventListener("close", function () {
      document.documentElement.classList.remove("modal-open");
    });
  });
```

Why the scroll-lock cleanup lives on the `close` event: Esc triggers the dialog's native `cancel`→`close` sequence without going through our click handlers, so `close` is the single reliable place to release the lock for all three close paths.

- [ ] **Step 4: Run the check to verify it passes**

Run: `node /tmp/pmodal-verify/check-interactions.js`
Expected: `PASS check-interactions`

- [ ] **Step 5: Re-run the earlier checks (regression)**

Run: `node /tmp/pmodal-verify/check-cards.js && node /tmp/pmodal-verify/check-modals.js`
Expected: `PASS check-cards` then `PASS check-modals`

- [ ] **Step 6: Commit**

```bash
git add js/main.js
git commit -m "$(cat <<'EOF'
Wire project cards to their detail modals

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Full validation pass (spec §5)

**Files:**
- No planned source changes. If a check exposes a defect, fix it in `index.html` / `css/styles.css` / `js/main.js` and commit the fix separately (imperative subject describing the fix).

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: evidence (screenshots + PASS output) that the spec's validation plan holds.

- [ ] **Step 1: Write the final validation script**

Create `/tmp/pmodal-verify/check-final.js`:

```js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const assert = (cond, msg) => { if (!cond) throw new Error(msg); };

  // 1. grid + every modal at the five spec widths; no horizontal overflow anywhere
  for (const w of [320, 375, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width: w, height: 900 } });
    await page.goto("http://localhost:8123/#projects", { waitUntil: "networkidle" });
    await page.waitForTimeout(800); // let reveals settle
    const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    assert(noOverflow, "horizontal overflow at " + w + "px");
    await page.screenshot({ path: "shots/final-grid-" + w + ".png" });
    for (const id of ["modal-tambal", "modal-school", "modal-doxie"]) {
      await page.evaluate((id) => document.getElementById(id).showModal(), id);
      const fits = await page.evaluate((id) => {
        const r = document.getElementById(id).getBoundingClientRect();
        return r.width <= window.innerWidth && r.height <= window.innerHeight;
      }, id);
      assert(fits, id + " overflows viewport at " + w + "px");
      await page.screenshot({ path: "shots/final-" + id + "-" + w + ".png" });
      await page.evaluate((id) => document.getElementById(id).close(), id);
    }
    await page.close();
  }

  // 2. reduced motion: everything still opens and closes
  const rm = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await rm.emulateMedia({ reducedMotion: "reduce" });
  await rm.goto("http://localhost:8123/", { waitUntil: "networkidle" });
  await rm.locator('.card[data-modal="modal-tambal"]').click({ position: { x: 20, y: 20 } });
  assert(await rm.evaluate(() => document.getElementById("modal-tambal").open), "reduced-motion: open failed");
  await rm.keyboard.press("Escape");
  assert(await rm.evaluate(() => !document.getElementById("modal-tambal").open), "reduced-motion: close failed");
  await rm.close();

  // 3. background scroll lock: page must not scroll while a modal is open
  const sl = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await sl.goto("http://localhost:8123/#projects", { waitUntil: "networkidle" });
  await sl.locator('.card[data-modal="modal-tambal"]').click({ position: { x: 20, y: 20 } });
  const before = await sl.evaluate(() => window.scrollY);
  await sl.mouse.wheel(0, 600);
  await sl.waitForTimeout(300);
  const after = await sl.evaluate(() => window.scrollY);
  assert(before === after, "page scrolled behind an open modal (" + before + " → " + after + ")");
  await sl.close();

  // 4. gallery support: inject the (normally commented) .shots block with real
  //    images and verify the grid renders inside the dialog — proves the CSS
  //    ships working even though no project has pictures yet.
  const g = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await g.goto("http://localhost:8123/", { waitUntil: "networkidle" });
  await g.evaluate(() => {
    const html =
      '<h4 class="md-h"><span>##</span> Screenshots</h4>' +
      '<div class="shots">' +
      '<figure><img src="assets/images/clawd.png" alt="test" width="1280" height="720"><figcaption>test caption</figcaption></figure>' +
      '<figure><img src="assets/images/pokemon.png" alt="test two" width="1280" height="720"><figcaption>test caption two</figcaption></figure>' +
      "</div>";
    document.querySelector("#modal-tambal .pmodal-body .ctags").insertAdjacentHTML("beforebegin", html);
    document.getElementById("modal-tambal").showModal();
  });
  await g.waitForTimeout(400);
  const galleryOk = await g.evaluate(() => {
    const dlg = document.getElementById("modal-tambal");
    const imgs = dlg.querySelectorAll(".shots img");
    return (
      imgs.length === 2 &&
      [...imgs].every((i) => i.clientWidth > 0 && i.clientWidth <= dlg.clientWidth) &&
      dlg.getBoundingClientRect().width <= window.innerWidth
    );
  });
  assert(galleryOk, "gallery grid broken inside the dialog at 375px");
  await g.screenshot({ path: "shots/final-gallery-375.png" });
  await g.close();

  console.log("PASS check-final");
  await browser.close();
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
```

(Step 4 injects the gallery into the live DOM instead of temporarily editing committed HTML — same coverage as the spec's "drop a test image in, then remove it", with no risk of the test image or uncommented markup leaking into a commit.)

- [ ] **Step 2: Run it**

Run: `node /tmp/pmodal-verify/check-final.js`
Expected: `PASS check-final`

If it fails: fix the defect in the source files, re-run **all four** check scripts, and commit the fix with an imperative subject (e.g. "Fix modal overflow at 320px") plus the Co-Authored-By trailer.

- [ ] **Step 3: Visual review of the evidence**

Read and confirm, at minimum:
- `shots/final-grid-320.png` — cards stacked, badges aligned, no overflow
- `shots/final-grid-768.png` — 2+1 layout, lone third card looks intentional
- `shots/final-grid-1440.png` — 3-up layout
- `shots/final-modal-doxie-320.png` and `shots/final-modal-tambal-1440.png` — near-full-screen sheet on mobile, centered 44rem terminal on desktop
- `shots/final-gallery-375.png` — injected gallery renders as a clean grid

- [ ] **Step 4: Final regression + working-tree check**

```bash
node /tmp/pmodal-verify/check-cards.js && node /tmp/pmodal-verify/check-modals.js && node /tmp/pmodal-verify/check-interactions.js && git status --short
```
Expected: three PASS lines and an **empty** `git status` (everything committed; harness and screenshots live outside the repo). Stop the background HTTP server when done.

---

## Spec coverage map (self-review)

| Spec section | Where |
| --- | --- |
| §3.1 card changes (data-modal, .card-open, .card-top badges, comment tweak) | Task 1 |
| §3.2 Doxie card | Task 1 |
| §3.3 modal markup (3 dialogs, chrome, commented .shots) | Task 2 |
| §3.4 modal copy (verbatim) | Task 2 Step 3 |
| §3.5 CSS (~90 lines: pmodal, backdrop, animation, scroll lock, md-h, hl, shots, plinks, status, card-open) | Task 1 Step 5 + Task 2 Steps 4–5 |
| §3.6 JS (~20 lines, feature-detected) | Task 3 |
| §3.7 accessibility checklist | markup in Tasks 1–2; behavior verified in Task 3 (focus restore, Esc, labelled close dot) |
| §3.8 out of scope | Global Constraints — explicitly excluded |
| §4 file change summary (4 files) | Tasks 1–3 + `.gitkeep` in Task 2 Step 6 |
| §5 validation plan | Task 4 (widths, interactions, reduced motion, gallery test, overflow) |

Known deliberate deviation from the spec: the spec claims card typography styles "already cascade" into the modal — they're actually scoped under `.card`, so Task 2 Step 4 widens five selectors. Same intent, working mechanics.
