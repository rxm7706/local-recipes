#!/usr/bin/env node
/**
 * Guildhall render check — execute the dashboard's own JavaScript against the
 * live data.js and fail on any runtime error.
 *
 * WHY THIS EXISTS. On 2026-07-26 the board rendered In Build, Realized and
 * Archived as empty for hours. The cause was a derived `timing` object emitted
 * without `perStory`, and a `velocity` without `foot`: the render does
 *
 *     p.timing && p.timing.perStory[key]
 *     v.foot.map(...)
 *
 * so a PARTIAL object passes the truthiness guard and then throws a TypeError,
 * which aborts the entire inline script — everything below the throw simply
 * never renders.
 *
 * Nothing caught it. All three standing detectors were green and the 1013-test
 * meta suite passed, because none of them execute the dashboard's JavaScript.
 * The operator found it.
 *
 * This harness closes that gap: it stubs just enough DOM for the script to run,
 * evals it against the real data.js, and exits non-zero on any throw. It does
 * not assert what the page looks like — only that the code completes, which is
 * the failure mode that actually bit.
 *
 * Usage:  node docs/dashboard/check_render.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const DATA = path.join(ROOT, 'docs', 'dashboard', 'data.js');
const HTML = path.join(ROOT, 'docs', 'dashboard', 'index.html');

// Minimal DOM. Every node is inert; we care that the script RUNS, not that it
// paints. Anything the script reaches for must exist, or we would report a stub
// gap as a dashboard bug.
const node = () => ({
  innerHTML: '', textContent: '', hidden: false, style: {},
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  setAttribute() {}, getAttribute: () => null, removeAttribute() {},
  appendChild() {}, addEventListener() {}, remove() {},
  querySelector: () => node(), querySelectorAll: () => [],
});

// Nodes are cached BY ID so the stub has identity: `getElementById(x)` twice must return
// the same object, or nothing the script writes can ever be observed. It previously minted
// a fresh node per call, which is why this check could only ever assert "did not throw" —
// and "did not throw" is not "did render". A renderer skipped by a truthiness guard, or
// aimed at a typo'd id, leaves an empty div and exits 0.
const _byId = new Map();

global.document = {
  getElementById: (id) => {
    if (!_byId.has(id)) _byId.set(id, node());
    return _byId.get(id);
  },
  querySelector: () => node(),
  querySelectorAll: () => [],
  createElement: () => node(),
  documentElement: node(),
  body: node(),
  addEventListener() {},
};
global.window = {};
global.location = { hash: '' };
// The board self-refreshes; a live timer would hang this check forever.
global.setInterval = () => 0;
global.setTimeout = () => 0;

eval(fs.readFileSync(DATA, 'utf8'));
if (!global.window.DASHBOARD_DATA) {
  console.error('FAIL: data.js did not define window.DASHBOARD_DATA');
  process.exit(1);
}

const html = fs.readFileSync(HTML, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (!scripts.length) {
  console.error('FAIL: no inline <script> found in index.html');
  process.exit(1);
}

try {
  eval(scripts[scripts.length - 1]);
} catch (e) {
  console.error(`FAIL: dashboard script threw ${e.constructor.name}: ${e.message}`);
  const frame = (e.stack || '').split('\n')[1];
  if (frame) console.error(frame.trim());
  console.error(
    '\nA throw here blanks every section BELOW the error, not just the one at ' +
    'fault. The usual cause is a derived object that satisfies a truthiness ' +
    'guard but omits a field the render then indexes — emit the contract in ' +
    'full, or emit nothing.');
  process.exit(1);
}

const d = global.window.DASHBOARD_DATA;
const lines = Object.keys(d.projects || {}).length;

// "It did not throw" is not "it rendered". A section whose renderer is skipped by a
// truthiness guard — a missing key, an empty array, a typo'd id — leaves an EMPTY div and
// exits 0, which is the silent-blank failure this detector exists to catch. Assert that the
// sections carrying data actually produced output.
const populated = [
  ['fleetrows', (d.fleet && d.fleet.rows || []).length],
  ['openrows', (d.openwork && d.openwork.projects || []).length],
  ['archrows', (d.archived || []).length],
];
const blank = populated.filter(([id, n]) => n > 0 &&
  !(document.getElementById(id) && (document.getElementById(id).innerHTML || '').trim()));
if (blank.length) {
  for (const [id, n] of blank) {
    console.error(`FAIL: #${id} rendered EMPTY while its data carries ${n} row(s) — ` +
      'the renderer was skipped, not the data missing.');
  }
  process.exit(1);
}

console.log(
  `OK: dashboard script ran clean — ${lines} lines, ` +
  `${(d.dreams || []).length} dreams, ${(d.archived || []).length} archived, ` +
  `${(d.fleet && d.fleet.rows || []).length} chains, ` +
  `${(d.openwork || {}).open || 0} open-work items.`);
