/* ============================================================
   Castor Troy Ricafort — portfolio interactions (no deps)
   - Mobile nav toggle · scrollspy · scroll-reveal · footer year
   - Interactive "Pokémon battle vs. Claude" with clickable moves
     and an OPTIONAL command line (recruiters can ignore it)
   ============================================================ */

(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Mobile nav toggle ---------------------------------- */
  var toggle = document.querySelector(".nav-toggle");
  var navLinks = document.querySelector(".nav-links");
  if (toggle && navLinks) {
    var closeNav = function () {
      navLinks.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    };
    toggle.addEventListener("click", function () {
      var open = navLinks.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    navLinks.addEventListener("click", function (e) {
      if (e.target.closest(".nav-link")) closeNav();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && navLinks.classList.contains("open")) {
        closeNav();
        toggle.focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (navLinks.classList.contains("open") && !e.target.closest(".site-header")) closeNav();
    });
  }

  /* ---- Scrollspy ------------------------------------------ */
  var spySections = Array.prototype.slice.call(document.querySelectorAll("section[id]"));
  var linkFor = {};
  document.querySelectorAll(".nav-link").forEach(function (a) {
    var id = (a.getAttribute("href") || "").replace("#", "");
    if (id) linkFor[id] = a;
  });
  if ("IntersectionObserver" in window && spySections.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var link = linkFor[entry.target.id];
        if (link && entry.isIntersecting) {
          Object.keys(linkFor).forEach(function (k) { linkFor[k].classList.remove("active"); });
          link.classList.add("active");
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px", threshold: 0 });
    spySections.forEach(function (s) { spy.observe(s); });
  }

  /* ---- Scroll-reveal -------------------------------------- */
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length && !reduceMotion) {
    var revObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("is-visible"); revObs.unobserve(entry.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (el) { revObs.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* ---- Footer year ---------------------------------------- */
  var yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ========================================================
     Battle vs. Claude — the meter is the CONTEXT WINDOW.
     Each exchange burns tokens; when a side's context fills
     up (hits 0 remaining) it runs /compact and frees it again.
     ======================================================== */
  var log = document.getElementById("battle-log");
  var term = document.getElementById("term-battle");
  var heroEl = document.getElementById("hero");
  var foeEl = document.getElementById("foe");

  // Reveal the battle (used by the boot sequence, and by any early interaction).
  function revealBattle() { if (term) term.classList.remove("booting"); }

  // Each move burns tokens from Clawd (foe) and a little from Castor (me),
  // measured in K. lines: dialog, each { c: css-class, t: text }.
  var MOVES = {
    argue: { foe: 38, me: 16, lines: [
      { c: "me", t: "Castor used ARGUE! 💢" },
      { c: "cl", t: "Claude: your function is 200 lines long." },
      { c: "me", t: "Castor: but it WORKS." },
      { c: "cl", t: "Claude: …it is still 200 lines long." }
    ]},
    ship: { foe: 30, me: 12, lines: [
      { c: "me", t: "Castor used SHIP IT! 🚀" },
      { c: "cl", t: "Claude: I added 14 tests first." },
      { c: "me", t: "Castor: I said ship, not—" },
      { c: "cl", t: "Claude: Shipping. With tests. ✓" },
      { c: "eff", t: "It's super effective!" }
    ]},
    refactor: { foe: 46, me: 18, lines: [
      { c: "me", t: "Castor used REFACTOR! 🔧" },
      { c: "cl", t: "Claude rewrote the entire module." },
      { c: "me", t: "Castor: I only changed one line…" },
      { c: "cl", t: "Claude: You're welcome." }
    ]},
    who: { foe: 12, me: 6, lines: [
      { c: "me", t: "Castor used INTRODUCE! 👤" },
      { c: "", t: "Castor Troy — AI-native software engineer @ Synacy." },
      { c: "", t: "Full-stack: Spring Boot · Angular · AWS. IoT on the side." },
      { c: "", t: "Top Computer Engineering grad, CIT-U 2025." },
      { c: "cl", t: "Claude: …okay, that part is all true." }
    ]}
  };

  // Cancellable typewriter. Returns nothing; calls done() when finished.
  var typeToken = 0;
  function typeSequence(lines, done, opts) {
    if (!log) return;
    var myToken = ++typeToken;
    if (!(opts && opts.append)) log.innerHTML = "";
    if (reduceMotion) {
      lines.forEach(function (seg) {
        var s = document.createElement("span");
        s.className = "ln " + (seg.c || "");
        s.textContent = seg.t;
        log.appendChild(s);
      });
      if (done) done();
      return;
    }
    var li = 0;
    (function nextLine() {
      if (myToken !== typeToken) return;
      if (li >= lines.length) { if (done) done(); return; }
      var seg = lines[li];
      var span = document.createElement("span");
      span.className = "ln " + (seg.c || "");
      log.appendChild(span);
      var ci = 0, txt = seg.t;
      (function nextChar() {
        if (myToken !== typeToken) return;
        if (ci >= txt.length) { li++; setTimeout(nextLine, 360); return; }
        span.textContent += txt.charAt(ci++);
        setTimeout(nextChar, 14 + Math.random() * 32);
      })();
    })();
  }

  /* ---- Context-window (token) meters ---------------------- */
  var CTX_MAX = 200;                          // 200K-token context window
  var ctx = { foe: CTX_MAX, hero: CTX_MAX };  // tokens REMAINING (in K)
  var compacting = { foe: false, hero: false };
  var SIDE = {
    foe:  { el: foeEl,  bar: document.getElementById("foe-ctx"),  num: document.getElementById("foe-tok"),  name: "Clawd"  },
    hero: { el: heroEl, bar: document.getElementById("hero-ctx"), num: document.getElementById("hero-tok"), name: "Castor" }
  };

  function renderCtx(side) {
    var s = SIDE[side], left = Math.max(0, ctx[side]);
    if (s.bar) s.bar.style.width = Math.max(0, Math.min(100, left / CTX_MAX * 100)) + "%";
    if (s.num) s.num.textContent = left + "K";
  }
  renderCtx("foe"); renderCtx("hero");

  function appendLog(cls, text) {
    if (!log) return;
    var s = document.createElement("span");
    s.className = "ln " + (cls || "");
    s.textContent = text;
    log.appendChild(s);
  }

  function lunge() {
    if (!heroEl || reduceMotion) return;
    heroEl.classList.remove("attacking");
    void heroEl.offsetWidth; // restart animation
    heroEl.classList.add("attacking");
    setTimeout(function () { heroEl.classList.remove("attacking"); }, 520);
  }
  function hurt(side) {
    var el = SIDE[side].el;
    if (!el || reduceMotion) return;
    el.classList.remove("hurt");
    void el.offsetWidth;
    el.classList.add("hurt");
    setTimeout(function () { el.classList.remove("hurt"); }, 460);
  }
  // floating "−38K" combat text over a sprite
  function floatDmg(side, costK, mini) {
    var s = SIDE[side];
    if (!s.el || reduceMotion) return;
    var stage = s.el.querySelector(".stage");
    if (!stage) return;
    var f = document.createElement("span");
    f.className = "dmg-float" + (mini ? " mini" : "");
    f.textContent = "−" + costK + "K";
    stage.appendChild(f);
    setTimeout(function () { if (f.parentNode) f.parentNode.removeChild(f); }, 1100);
  }

  // context fills up → run /compact → tokens freed again (the replenish)
  function compact(side) {
    if (compacting[side]) return;
    compacting[side] = true;
    var s = SIDE[side];
    appendLog("sys", "✻ " + s.name + ": context window full — running /compact …");
    setTimeout(function () {
      ctx[side] = CTX_MAX;
      renderCtx(side);
      appendLog("eff", "✓ compacted · " + CTX_MAX + "K tokens free again");
      // Claude "always wins the argument" — now by compacting it away.
      if (side === "foe" && Math.random() < 0.6) {
        appendLog("cl", "Claude: I compacted the whole argument away. You were saying?");
      }
      compacting[side] = false;
    }, 820);
  }

  // burn `costK` tokens from a side: show damage, drain the bar, compact at 0
  function applyHit(side, costK, mini) {
    if (!costK) return;
    hurt(side);
    floatDmg(side, costK, mini);
    ctx[side] -= costK;
    if (ctx[side] <= 0) {
      ctx[side] = 0;
      renderCtx(side);
      setTimeout(function () { compact(side); }, 900);
    } else {
      renderCtx(side);
    }
  }

  function tokenLine(m) {
    var parts = [];
    if (m.foe) parts.push("Clawd −" + m.foe + "K");
    if (m.me)  parts.push("Castor −" + m.me + "K");
    return "✻ ctx burned — " + parts.join("  ·  ");
  }

  function playMove(key) {
    var move = MOVES[key];
    if (!move) return;
    revealBattle();
    var lines = move.lines.slice();
    if (move.foe || move.me) {
      lunge();
      setTimeout(function () {
        applyHit("foe", move.foe || 0, false);
        applyHit("hero", move.me || 0, true);
      }, 240);
      lines.push({ c: "eff", t: tokenLine(move) });
    }
    typeSequence(lines);
  }

  document.querySelectorAll(".move").forEach(function (btn) {
    btn.addEventListener("click", function () { playMove(btn.getAttribute("data-move")); });
  });

  /* ---- Optional command line ------------------------------ */
  var SECTION_CMDS = { about: "about", whoami: "about", projects: "projects", work: "projects",
    experience: "experience", skills: "stack", stack: "stack", tools: "stack", contact: "contact" };

  function scrollToId(id) {
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }

  function runCommand(raw) {
    var cmd = (raw || "").trim().toLowerCase();
    if (!cmd) return;
    revealBattle();

    if (cmd === "help") {
      typeSequence([
        { c: "sys", t: "Commands: about · projects · experience · skills · contact · resume · clear" },
        { c: "sys", t: "…or just tap a move button above ↑ (totally optional)" }
      ]);
      return;
    }
    if (cmd === "clear") { if (log) log.innerHTML = ""; return; }
    if (cmd === "ls") {
      typeSequence([{ c: "sys", t: "about/  projects/  experience/  stack/  contact/  resume.pdf" }]);
      return;
    }
    if (cmd === "resume" || cmd === "cv") {
      typeSequence([{ c: "sys", t: "Opening résumé…" }]);
      window.open("assets/resume.pdf", "_blank", "noopener");
      return;
    }
    if (cmd === "who" || cmd === "whoami") { playMove("who"); scrollToId("about"); return; }
    if (cmd === "claude") { typeSequence([{ c: "cl", t: "Claude is already arguing with you. ↑" }]); return; }
    if (cmd === "pokemon" || cmd === "pokémon") { typeSequence([{ c: "sys", t: "Castor Troy wants to battle! Pick a move ↑" }]); return; }
    if (cmd === "sudo") { typeSequence([{ c: "sys", t: "nice try 😏" }]); return; }

    if (SECTION_CMDS.hasOwnProperty(cmd)) {
      var id = SECTION_CMDS[cmd];
      typeSequence([{ c: "sys", t: "→ jumping to " + id + "…" }]);
      scrollToId(id);
      return;
    }
    typeSequence([
      { c: "sys", t: 'command not found: ' + cmd },
      { c: "sys", t: "type 'help' — or just tap a move ↑" }
    ]);
  }

  var cmdForm = document.getElementById("cmd-form");
  var cmdInput = document.getElementById("cmd-input");
  if (cmdForm && cmdInput) {
    cmdForm.addEventListener("submit", function (e) {
      e.preventDefault();
      runCommand(cmdInput.value);
      cmdInput.value = "";
    });
  }

  /* ---- "Open" the terminal, boot Claude Code, then battle -- */
  var BOOT = [
    { c: "sys", t: "$ claude" },
    { c: "cl",  t: "✻ Welcome to Claude Code!" },
    { c: "sys", t: "  · loading ~/castor-troy …" },
    { c: "sys", t: "  · model claude-opus-4 · ready ✓" }
  ];
  var INTRO = [
    { c: "sys", t: "✻ A wild CLAWD appeared!" },
    { c: "sys", t: "Pick a move ↑ — or type a command below." }
  ];
  function bootIntro() {
    if (reduceMotion) { revealBattle(); typeSequence(INTRO); return; }
    typeSequence(BOOT, function () {
      revealBattle();                                   // arena + moves slide in
      setTimeout(function () { typeSequence(INTRO); }, 560);
    });
  }
  if (log) {
    if ("IntersectionObserver" in window && !reduceMotion) {
      var started = false;
      var io = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting && !started) { started = true; bootIntro(); io.disconnect(); }
      }, { threshold: 0.3 });
      io.observe(term || log);
    } else {
      bootIntro();
    }
  }
})();

/* ============================================================
   Claude stats — contribution heatmap
   Fetches data/claude-activity.json when the section approaches
   (same IntersectionObserver pattern as the battle boot). On any
   failure the whole section hides — never a broken layout.
   ============================================================ */
(function () {
  "use strict";

  var section = document.getElementById("claude-stats");
  if (!section || !window.fetch) return;

  var DAY = 86400000;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function hideSection() {
    section.hidden = true;
    var link = document.querySelector('.nav-link[href="#claude-stats"]');
    if (link && link.closest("li")) link.closest("li").hidden = true;
  }

  // All date math in UTC ms so the graph reflects the ledger's Manila days
  // regardless of the viewer's timezone.
  function dayMs(iso) { return Date.parse(iso + "T00:00:00Z"); }
  function isoDate(ms) { return new Date(ms).toISOString().slice(0, 10); }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }

  function quartiles(values) {
    var sorted = values.slice().sort(function (a, b) { return a - b; });
    function q(p) { return sorted[Math.floor((sorted.length - 1) * p)]; }
    return [q(0.25), q(0.5), q(0.75)];
  }

  function bucket(m, qs) {
    if (!m) return 0;
    if (m <= qs[0]) return 1;
    if (m <= qs[1]) return 2;
    if (m <= qs[2]) return 3;
    return 4;
  }

  function longestStreak(sortedDates) {
    var max = 0, run = 0, prev = NaN;
    sortedDates.forEach(function (d) {
      var ms = dayMs(d);
      run = (ms - prev === DAY) ? run + 1 : 1;
      if (run > max) max = run;
      prev = ms;
    });
    return max;
  }

  function render(data) {
    if (!data || !data.days || !data.firstDate || !data.generatedAt ||
        !data.totals) { hideSection(); return; }
    var days = data.days;
    var dates = Object.keys(days).sort();
    if (!dates.length) { hideSection(); return; }

    document.getElementById("cs-sessions").textContent = fmt(data.totals.sessions || 0);
    document.getElementById("cs-messages").textContent = fmt(data.totals.messages || 0);
    document.getElementById("cs-active").textContent = fmt(data.totals.activeDays || dates.length);
    document.getElementById("cs-streak").textContent = longestStreak(dates) + "d";

    // grid runs from the Sunday on/before firstDate through "today" (the
    // ledger's own generatedAt date — not the viewer's clock)
    var today = data.generatedAt.slice(0, 10);
    var start = dayMs(data.firstDate);
    start -= new Date(start).getUTCDay() * DAY;
    var end = dayMs(today);
    // once history exceeds 12 months, clamp to a 53-column rolling year
    var minStart = end - 52 * 7 * DAY;
    if (start < minStart) {
      start = minStart - new Date(minStart).getUTCDay() * DAY;
    }

    var qs = quartiles(dates.map(function (d) { return days[d].m; })
                            .filter(function (m) { return m > 0; }));

    var cells = document.getElementById("cs-cells");
    var monthsRow = document.getElementById("cs-months");
    var week = 0, lastMonth = -1;
    for (var ms = start; ms <= end; ms += 7 * DAY, week++) {
      var sunday = new Date(ms);
      if (sunday.getUTCMonth() !== lastMonth) {
        lastMonth = sunday.getUTCMonth();
        var label = document.createElement("span");
        label.textContent = MONTHS[lastMonth];
        label.style.gridColumn = String(week + 1);
        monthsRow.appendChild(label);
      }
      for (var row = 0; row < 7; row++) {
        var cellMs = ms + row * DAY;
        var date = isoDate(cellMs);
        var cell = document.createElement("span");
        if (cellMs > end || date < data.firstDate) {
          cell.className = "cs-cell empty";
        } else {
          var entry = days[date];
          var m = entry ? entry.m : 0;
          cell.className = "cs-cell l" + bucket(m, qs);
          var d = new Date(cellMs);
          cell.title = MONTHS[d.getUTCMonth()] + " " + d.getUTCDate() +
            " · " + fmt(m) + " messages" +
            " · " + fmt(entry ? entry.s : 0) + " sessions" +
            " · " + fmt(entry ? entry.t : 0) + " tool calls";
        }
        cells.appendChild(cell);
      }
    }

    document.getElementById("cs-updated").textContent =
      "last updated " + today + " · all data since " + data.firstDate;

    // most recent weeks in view first (matters on mobile)
    var scroller = section.querySelector(".cs-scroll");
    if (scroller) scroller.scrollLeft = scroller.scrollWidth;
  }

  function load() {
    fetch("data/claude-activity.json", { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(render)
      .catch(hideSection);
  }

  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) { io.disconnect(); load(); }
    }, { rootMargin: "300px 0px" });
    io.observe(section);
  } else {
    load();
  }
})();
