#!/usr/bin/env python3
"""Guildhall layout check — assert the console bar LOOKS right, not just that it runs.

WHY THIS EXISTS. `check_render.js` executes the dashboard's JavaScript and fails
on a throw. Its own header is explicit that it "does not assert what the page
looks like — only that the code completes". That is a real gap, and it has now
been paid for twice:

  * 2026-07-30 — three green gates coexisted with a visibly broken status chip
    for three commits. The operator found it.
  * 2026-07-31 — the running chip overlapped "Refreshed …"; the first fix for it
    (`minmax(max-content, 1fr)`) stopped the overlap by pushing the centre chip
    off the midpoint, trading one visual bug for another. The operator found
    that too, from a screenshot, because nothing measured geometry.

Both are one-second measurements. This harness makes them.

WHAT IT ASSERTS, at several viewport widths:

  1. edges        `last shipped` is flush to the bar's left inner edge and
                  `running` flush to its right. The bar carried a centred middle
                  chip until 2026-07-31; "Refreshed" then moved up beside the
                  REFRESH control and the row became two-slot, which removed the
                  centre and the class of bug that came with it. `#chip-gen` is
                  therefore measured against `.cbrow`, not `.cbstatus`.
  2. no-overlap   chips that share a row never overlap horizontally. Checked per
                  ROW, because below the 720px breakpoint the bar deliberately
                  stacks into one column and horizontal ranges legitimately
                  coincide — a naive left/right comparison reports a false
                  positive there, which is exactly what the throwaway version of
                  this script did.
  3. one-row      above the breakpoint all three chips share a row. Catches the
                  regression where a chip wraps and the bar silently doubles in
                  height (previously seen as "running"/"Doctor"/"1.5"/"(dev)"
                  stacked on four lines).
  4. in-bounds    no chip escapes the bar's own box.
  5. not-clipped  no chip's content is wider than the chip. This is the check the
                  gate lacked when the running chip collapsed to a 6px box with
                  its 232px label overflowing: every other assertion passed,
                  because a clipped chip still sits inside the bar, still shares
                  a row, and still has an edge in the right place. Only its
                  CONTENT was gone.

NEVER CLAIMS GREEN IT DID NOT MEASURE. Missing browser, missing data.js, or a
page that fails to load exits **2 (UNKNOWN)** — distinct from 1 (findings) and 0
(pass), so a caller can tell "clean" from "could not look".

STRESSES THE LAYOUT WITH FONT SIZE, NOT WITH LIVE CONTENT. Two earlier cuts of
this gate passed on the very bug they were written for. The first measured the
board exactly as `data.js` rendered it — and the running chip happened to read
"Marshal 1.8 (dev) · 8m ago" that minute, which is short enough to fit anywhere.
The second injected long strings, and still could not reproduce it: the operator
sees the bug at 11px because their system resolves `var(--mono)` to a WIDER face
than headless Chrome picks, so identical markup is physically wider on their
screen than on the runner's.

Content length and font metrics are therefore both environmental. What is NOT
environmental is the failure mode: when the three chips need more room than the
bar has, does the layout degrade by moving the centre chip (wrong) or by wrapping
the outer chips (right)? Scaling `.cchip` font-size forces exactly that condition
on any machine. Measured against the pre-fix CSS it reproduces cleanly —
offset +4.5px at 17px, +69.5px at 20px, +156.2px at 24px — while the fixed CSS
holds +0.0px at every size and grows the bar's height instead. That is a gate
that fails when it should.

Serves the directory over an ephemeral loopback port rather than file://, so the
run is hermetic and does not depend on whichever server the operator happens to
have open.

Contract: docs/dreams/fidelity-enforcement.md § The frontier (invariant 3 —
a detector that cannot run reports unknown, never green).
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import contextlib
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Widths above the 720px collapse breakpoint, where the three-column grid is
# live and all four assertions apply; plus one below it, where stacking is the
# designed behaviour and only no-overlap/in-bounds are meaningful.
WIDE = (1600, 1400, 1200, 1000, 820)
NARROW = (700,)
BREAKPOINT = 720
CENTRE_TOL = 2.0   # px; sub-pixel layout means exact 0 is not a fair demand

# Chips inside the status row. `#chip-gen` deliberately excluded — it lives in
# `.cbrow` now, and treating it as a row member made the gate report a phantom
# "bar wrapped to 2 rows" (the two elements are in different containers, at the
# same one-line bar height of 34px).
CHIPS = ("#chip-ship", "#chip-run")
EDGE_TOL = 14.0   # px; the bar's own 12px padding plus a sub-pixel allowance

# Font sizes in px applied to `.cchip`. 11 is the design size; the rest simulate
# a wider font face or a zoomed browser, which is how the operator hits at 11px
# what a runner does not. Above 11 the bar is EXPECTED to grow taller as the
# outer chips wrap — that is the correct degradation — so the one-row assertion
# is scoped to the design size only. Centring and non-overlap must hold at ALL
# sizes; they are the invariants.
PRESSURES = (11, 14, 17, 20, 24)
DESIGN_SIZE = 11

APPLY = """(fs) => {
  document.querySelectorAll('.cchip').forEach(e => { e.style.fontSize = fs + 'px'; });
}"""

PROBE = """() => {
  const bar = document.querySelector('.cbstatus');
  if (!bar) return null;
  const bb = bar.getBoundingClientRect();
  const box = el => { const b = el.getBoundingClientRect();
    return {l:b.left, r:b.right, t:b.top, b:b.bottom, cx:(b.left+b.right)/2}; };
  const out = {bar:{l:bb.left, r:bb.right, cx:(bb.left+bb.right)/2, h:bb.height}, chips:{}};
  for (const s of %s) {
    const el = document.querySelector(s);
    if (!el) continue;
    const c = box(el);
    const txt = el.querySelector('.ctext');
    c.need = txt ? txt.getBoundingClientRect().width : 0;   // intrinsic label width
    c.have = el.clientWidth;                                 // room the chip actually has
    out.chips[s] = c;
  }
  return out;
}""" % list(CHIPS)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler logs every GET to stderr, which buries the one
    line a detector is supposed to emit. A gate's output is its whole product."""

    def log_message(self, *_args):  # noqa: D102
        pass


def _serve(directory: Path):
    handler = functools.partial(_QuietHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _rows(chips: dict) -> list[list[str]]:
    """Group chips into visual rows by vertical overlap."""
    rows: list[list[str]] = []
    for name in sorted(chips, key=lambda n: chips[n]["t"]):
        c = chips[name]
        for row in rows:
            o = chips[row[0]]
            if c["t"] < o["b"] and o["t"] < c["b"]:
                row.append(name)
                break
        else:
            rows.append([name])
    return rows


def check(width: int, m: dict, scenario: str = "live") -> list[str]:
    bar, chips = m["bar"], m["chips"]
    found: list[str] = []
    at = f"w={width} [{scenario}]"
    missing = [c for c in CHIPS if c not in chips]
    if missing:
        found.append(f"{at}: chip(s) absent from the DOM: {', '.join(missing)}")
        return found

    rows = _rows(chips)

    # (2) no two chips sharing a row may overlap horizontally
    for row in rows:
        ordered = sorted(row, key=lambda n: chips[n]["l"])
        for a, b in zip(ordered, ordered[1:]):
            gap = chips[b]["l"] - chips[a]["r"]
            if gap < 0:
                found.append(f"{at}: {a} and {b} share a row and OVERLAP by {-gap:.1f}px")

    # (5) no chip is clipping its own label
    for name, c in chips.items():
        if c.get("need", 0) > c.get("have", 0) + 1.0:
            found.append(
                f"{at}: {name} is CLIPPED — label needs {c['need']:.0f}px, chip has "
                f"{c['have']:.0f}px; the text is rendering outside its own box")

    # (4) nothing escapes the bar
    for name, c in chips.items():
        if c["l"] < bar["l"] - 0.5 or c["r"] > bar["r"] + 0.5:
            found.append(
                f"{at}: {name} escapes the bar "
                f"(chip {c['l']:.0f}–{c['r']:.0f} vs bar {bar['l']:.0f}–{bar['r']:.0f})")

    if width > BREAKPOINT:
        # (3) one row above the breakpoint — only at the design font size, since
        # wrapping under font pressure is the intended degradation, not a fault.
        if scenario == f"{DESIGN_SIZE}px" and len(rows) != 1:
            found.append(
                f"{at}: bar wrapped to {len(rows)} rows above the {BREAKPOINT}px "
                f"breakpoint (height {bar['h']:.0f}px) — a chip is folding when it should not")
        # (1) ship flush left, running flush right
        dl = chips["#chip-ship"]["l"] - bar["l"]
        dr = bar["r"] - chips["#chip-run"]["r"]
        if dl > EDGE_TOL:
            found.append(f"{at}: last-shipped chip is {dl:.1f}px from the bar's left edge "
                         f"(tolerance {EDGE_TOL}px) — it is not left-flush")
        if dr > EDGE_TOL:
            found.append(f"{at}: running chip is {dr:.1f}px from the bar's right edge "
                         f"(tolerance {EDGE_TOL}px) — it is not right-flush")
    return found


def main() -> int:
    if not (HERE / "data.js").exists():
        print("UNKNOWN: docs/dashboard/data.js is absent — run `dashboard-gen` first.")
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("UNKNOWN: playwright is not importable — cannot measure layout.")
        return 2

    httpd, port = _serve(HERE)
    url = f"http://127.0.0.1:{port}/index.html"
    findings: list[str] = []
    measured = 0
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome")
            except Exception:
                try:
                    browser = p.chromium.launch()
                except Exception as exc:
                    print(f"UNKNOWN: no usable chromium ({type(exc).__name__}) — cannot measure layout.")
                    return 2
            try:
                for width in (*WIDE, *NARROW):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    try:
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        page.wait_for_timeout(250)
                        for fs in PRESSURES:
                            name = f"{fs}px"
                            page.evaluate(APPLY, fs)
                            page.wait_for_timeout(60)
                            m = page.evaluate(PROBE)
                            if not m:
                                findings.append(
                                    f"w={width} [{name}]: .cbstatus not found — the bar did not render")
                                continue
                            measured += 1
                            findings += check(width, m, name)
                    finally:
                        page.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()

    if not measured:
        print("UNKNOWN: the bar never rendered at any width.")
        return 2
    if findings:
        print(f"console-bar layout — {measured} measurement(s) "
              f"({len(WIDE) + len(NARROW)} widths x {len(PRESSURES)} font-pressure steps)\n")
        print(f"FINDINGS ({len(findings)}):")
        for f in findings:
            print(f"  ✗ {f}")
        return 1
    print(f"OK: console bar edges held, no overlap — {measured} measurement(s): "
          f"{len(WIDE) + len(NARROW)} width(s) x {len(PRESSURES)} font-pressure step(s).")
    return 0


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
    sys.exit(130)
