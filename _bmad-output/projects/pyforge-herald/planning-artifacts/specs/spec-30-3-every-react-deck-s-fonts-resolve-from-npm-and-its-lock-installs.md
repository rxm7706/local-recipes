---
title: "30.3: Every React deck's fonts resolve from npm and its lock installs"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '846d8383f5b4a1f86cbb09f6fd8ae8616b34950f'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-30-1-a-deck-s-html-twins-are-self-contained-and-published.md
  - presentations/pyforge-atlas/package.json
  - presentations/pyforge-atlas/src/main.jsx
  - presentations/pyforge-atlas/src/index.css
  - presentations/agentic-sdlc/package.json
  - docsite/assets/fonts/fonts.css
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/twins.py
  - src/shared/packages/pyforge-herald/tests/meta/test_twins_zero_origin.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** no React deck under `presentations/` installs from its lock or builds from the registry alone, so
herald's `deck pull` prover can never pass. Line numbers and counts are at `846d8383f5`.

- **The phantom package.** Story 30.1 (`697c985d25`, 2026-10-08) vendored the decks' fonts by adding
  `@fontsource/archivo` and `@fontsource/archivo-expanded` (`^5.2.5`) to 13 decks' `package.json` (`:16-:17`) and
  nine `import '@fontsource/…/*.css'` lines to each `src/main.jsx` (`:5-:13`). `@fontsource/archivo-expanded` does
  not exist on npm: `npm view` and `npm install` answer `E404 Not Found - GET
  https://registry.npmjs.org/@fontsource%2farchivo-expanded`. The real packages are `@fontsource/archivo` and
  `@fontsource-variable/archivo`, both at 5.3.0 on 2026-10-14.
- **No lock moved.** None of the 14 `package-lock.json` files carries a `@fontsource` entry, agentic-sdlc's included,
  whose three font packages (`space-grotesk`, `ibm-plex-sans`, `ibm-plex-mono`) are real. So `npm ci` refuses every
  deck: E404 in the 13 Archivo decks, `EUSAGE … package.json and package-lock.json … are not in sync` in
  agentic-sdlc. pyforge-warden also declares `@fontsource/ibm-plex-mono`, which exists and is also missing from its
  lock.
- **The prover.** `deck_pipeline.NpmLocalProver` (`:112-:135`) runs `npm run extract` then `npm run build` in the
  deck folder. A build in a `node_modules` that predates 30.1 fails with
  `Rollup failed to resolve import "@fontsource/archivo/400.css"`; a fresh clone cannot install at all. So no deck
  could record a bridge etag until the operator unblocked it on 2026-10-14 with a local, untracked `node_modules`
  shim (its `package.json` says `LOCAL UNTRACKED SHIM`).
- **Why nothing caught it.** Story 30.1's `tests/meta/test_twins_zero_origin.py` scans each deck's source
  `index.html` and the standalone twins; it never installs or builds, so it stayed green. No test reads a lock.
- **The face itself.** Archivo Expanded is the 125% width of the variable Archivo. `docsite/assets/fonts/fonts.css`
  `:147-:154` already declares `'Archivo Expanded'` that way (`font-weight: 700 900; font-stretch: 125%`, the
  `wdth` face from `@fontsource-variable/archivo@5.2.6`, Story 31.3). The decks' slide fragments name
  `'Archivo Expanded'` as a family and nothing else.

**Evidence, measured on 2026-10-14 at `846d8383f5` on this host (node 25.7.0, npm 11.10.1):**
- `npm view @fontsource/archivo-expanded version` → E404; `@fontsource-variable/archivo`, `@fontsource/archivo`,
  `@fontsource/ibm-plex-mono` → 5.3.0.
- HEAD's `package.json` + `package-lock.json` copied to scratch directories: `npm ci` exit 1 in pyforge-atlas (E404)
  and in agentic-sdlc (EUSAGE); `npm install --package-lock-only` exit 1 in pyforge-atlas (E404).
- `grep -c fontsource presentations/*/package-lock.json` → 0 in all 14.
- With the fix applied and no shim present: `npm install`, `npm ci` and `npm run build` exit 0 in all 14 decks; the
  built deckcraft bundle emits `assets/archivo-latin-wdth-normal-DY7AcnAa.woff2` and
  `font-family:Archivo Expanded;…font-weight:700 900;font-stretch:125%;…format("woff2-variations")`;
  `twins.scan_tree(dist)` returns no finding for pyforge-atlas and agentic-sdlc.

**Approach:**
- **Depend on the published face.** Each Archivo deck's `package.json` replaces
  `"@fontsource/archivo-expanded": "^5.2.5"` with `"@fontsource-variable/archivo": "^5.2.5"`, one line, keeping
  `@fontsource/archivo` and pyforge-warden's `@fontsource/ibm-plex-mono`. agentic-sdlc's manifest is untouched.
- **Drop the dead imports.** Each Archivo deck's `src/main.jsx` loses its three
  `import '@fontsource/archivo-expanded/{700,800,900}.css';` lines and keeps the six `@fontsource/archivo/*.css`
  imports (pyforge-warden's `ibm-plex-mono` and agentic-sdlc's imports stay).
- **Declare the face once.** Each Archivo deck's `src/index.css` is prepended with the one `@font-face` the docsite
  proved: `font-family: 'Archivo Expanded'; font-style: normal; font-weight: 700 900; font-stretch: 125%;
  font-display: swap; src: url('@fontsource-variable/archivo/files/archivo-latin-wdth-normal.woff2')
  format('woff2-variations')`. Vite resolves the bare specifier from `node_modules` and emits the file as a hashed
  asset beside the bundle's CSS; `base: './'` keeps it relative.
- **Regenerate every lock from the registry.** With no shim present (`rm -rf node_modules/@fontsource/archivo-expanded`
  first), `npm install --no-audit --no-fund` in each of the 14 decks rewrites `package-lock.json`; `npm ci` and
  `npm run build` then prove it. The lock gains the font packages at 5.3.0; the only other change is npm 11 writing
  no `libc` array on the esbuild/rollup platform packages, and no resolved version moves.
- **A test that reads the lock.** `src/shared/packages/pyforge-herald/tests/meta/test_deck_lockfiles_current.py`
  (new), offline and stdlib-only, parametrised over `presentations/*/package.json`: every name under
  `dependencies` and `devDependencies` has a `node_modules/<name>` entry in the lock's `packages` map, and the lock
  root (`packages[""]`) carries the same `dependencies` and `devDependencies` as the manifest. Three `tmp_path`
  cases pin the shape: a stale lock names each missing dependency and the root mismatch; a missing lock is one
  finding; a current pair has none.
- **Unchanged:** every deck's content, slides, weights, `index.html` and `vite.config.js`; agentic-sdlc's sources;
  the prover, the scan and `deck_publish`; `dist/` and `node_modules/` stay untracked, and no font binary is tracked.

**Rejected:**
- **Tracking the shim, or a font binary, in the deck.** AD-4 and Epic 30's boundary: vendored fonts come from npm
  packages resolved at build time, and no font binary is tracked.
- **A static Archivo Expanded package.** None is published; the variable face is the only registry source, as the
  docsite found on 2026-10-08 (Story 31.3).
- **A vite alias or a local package for the face.** One `@font-face` in the deck's own stylesheet is the smallest
  change, mirrors `fonts.css`, and needs no build configuration.
- **Keeping `@fontsource/archivo-expanded` in the manifest with an override.** npm cannot resolve a name the registry
  does not hold; an override cannot invent it.

Ledger key: `30-3-every-react-deck-s-fonts-resolve-from-npm-and-its-lock-installs`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-55 (FR-10.3; D5): a deck's HTML twins are self-contained and
  published. Story 30.1 vendored the 14 React decks' fonts and built the twin publisher; Story 30.2 shows a twin in
  the portal. This story fixes the dependency 30.1 declared and the locks it left behind. It mints no CAP and changes
  no `SPEC.md`.
- **Governance.** `scripts/.spec-surface-baseline.json` names `spec-pyforge-herald` and `spec-modernist-identity` as
  the governors of `presentations/*/package.json`, `package-lock.json`, `src/main.jsx` and `src/index.css`, and
  `spec-pyforge-herald` as the governor of the herald package's `tests/meta/`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. Story 30.1 vendored the deck sources'
  fonts outside `pyforge.herald.deck_viewer`, which gates only whether `herald deck publish` builds and uploads twins;
  that gate is unchanged.
- **Architecture.** AD-22 (the twins are served under the portal's own origin); AD-4 (`dist/` stays gitignored).
- **Origin.** `docs/dreams/pyforge-herald.md` Realization log, 2026-10-14 (archivo-expanded).

## Acceptance Criteria

Every criterion runs real `npm` against the real registry or reads the real tree. None needs a browser, a store or the
portal.

- **AC1 — The registry resolves every dependency.** **Given** a deck with no `node_modules` (and no shim), **When**
  `npm install --no-audit --no-fund` runs in it, **Then** it exits 0 and writes a `package-lock.json` whose `packages`
  map holds `node_modules/<name>` for every name in the manifest's `dependencies` and `devDependencies`.
  `@fontsource/archivo-expanded` appears in no `package.json`, no `src/main.jsx` and no lock.
- **AC2 — `npm ci` and the build pass in all 14 decks.** `npm ci --no-audit --no-fund` then `npm run build` exit 0 in
  each of the 14 `presentations/*/` directories that hold a `package.json`, agentic-sdlc included.
- **AC3 — The face is in the bundle, and the bundle names no other origin.** In each Archivo deck's `dist/`, the
  emitted CSS declares `font-family:Archivo Expanded` with `font-weight:700 900` and `font-stretch:125%` and its
  `src` is a relative `archivo-latin-wdth-normal-*.woff2` that exists under `dist/assets/`;
  `pyforge.herald.twins.scan_tree(dist)` returns an empty list.
- **AC4 — The lock test.** `tests/meta/test_deck_lockfiles_current.py` has one case per
  `presentations/*/package.json` (14 at `846d8383f5`) plus the three `tmp_path` cases. Run against the 14 manifests
  and locks of `846d8383f5`, every deck case fails naming each dependency with no lock entry and the root mismatch;
  on the story's tree all pass. The test imports nothing from the network and nothing outside the stdlib and
  `pytest`.
- **AC5 — Nothing else moves.** Per Archivo deck, `git diff --numstat` shows `package.json` 1/1, `src/main.jsx` 0/3
  and `src/index.css` 10/0; agentic-sdlc changes only its lock; no `index.html`, `vite.config.js`, slide, fragment
  or font binary changes; `node_modules/` and `dist/` stay ignored by each deck's `.gitignore`.
- **AC6 — Docs name no phantom.** `docs/how-to/presentation-deck.md` and `.claude/skills/pyforge-herald/active/SKILL.md`
  contain no `archivo-expanded` package reference (neither does at `846d8383f5`; the check is the grep).
- **AC7 — Green, and reconciled.** `pixi run --frozen -e pyforge-herald pyforge-herald-test` exits 0 (it runs the
  lock test and `test_twins_zero_origin.py`); `tests/scripts/test_deck_export.py` exits 0; the `spec-pyforge-herald`
  and `spec-modernist-identity` memlogs each get a surface-reconcile entry naming the changed governed paths and this
  story, every Spec `spec-surface-check` names is stamped scoped, and `spec-surface-check` exits 0.

## Tasks

- [x] Replace the phantom dependency with `@fontsource-variable/archivo` in the 13 Archivo decks' `package.json`
- [x] Delete the three `archivo-expanded` imports from each Archivo deck's `src/main.jsx`
- [x] Prepend the `'Archivo Expanded'` `@font-face` to each Archivo deck's `src/index.css`
- [x] Remove any local shim, then `npm install`, `npm ci` and `npm run build` in all 14 decks, recording each exit code
- [x] `tests/meta/test_deck_lockfiles_current.py`: the per-deck live-tree cases and the three `tmp_path` cases; prove it
      fails on `846d8383f5`'s locks
- [x] Scan one built `dist/` with `twins.scan_tree`; grep the how-to and the SKILL for `archivo-expanded`
- [x] Surface reconcile on every Spec `spec-surface-check` names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- Take Archivo Expanded from `@fontsource-variable/archivo` at `font-stretch: 125%`, the declaration
  `docsite/assets/fonts/fonts.css` carries; keep `@fontsource/archivo` for the static weights.
- Regenerate every lock from the registry with no shim present; prove each deck with `npm ci` then `npm run build`.
- Keep each deck's `package.json` diff to the one dependency line; keep its content, weights and `index.html` as they
  are.
- Reconcile every governed path the change touches on the memlog of each Spec that governs it, then stamp those
  Specs scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never track `node_modules/`, `dist/`, a shim or a font binary.
- Never hand-edit a `package-lock.json`; npm writes it.
- Never change a deck's slides, fragments, weights, `index.html` or `vite.config.js`, or agentic-sdlc's sources.
- Never touch `pixi.toml`, `pixi.lock`, the prover, the scan, `deck_publish`, a `SPEC.md` or `sprint-status-ledger.yaml`.

**Residual risk:**
- The lock test proves the lock resolves the manifest, not that the registry still serves every entry; `npm ci` in
  the prover and in the build keep proving that.
- npm's lock format follows the installing npm; a later npm may rewrite fields (as 11.10 dropped `libc`) without a
  dependency moving. The test compares names and the root, never formatting.
- `woff2-variations` is understood by every current browser; a reader on a browser that ignores the format hint falls
  back to the static Archivo weights, never to a remote origin.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After |
|---|---|---|
| `npm install` in an Archivo deck with no `node_modules` | exit 1, E404 `@fontsource/archivo-expanded` | exit 0, lock written |
| `npm ci` in an Archivo deck | exit 1, E404 | exit 0 |
| `npm ci` in agentic-sdlc | exit 1, EUSAGE (lock out of sync) | exit 0 |
| `npm run build` in a `node_modules` that predates 30.1 | `Rollup failed to resolve import "@fontsource/archivo/400.css"` | exit 0; `archivo-latin-wdth-normal-*.woff2` emitted |
| `NpmLocalProver.prove(deck)` | raises on `build` | passes; a bridge etag can be recorded |
| slide text in `'Archivo Expanded'` | the family is never loaded; browser fallback | the `wdth` face at 125% width, weights 700-900 |
| `twins.scan_tree(dist)` | no bundle to scan | no finding |
| a dependency added to a manifest without `npm install` | unnoticed | that deck's lock-test case fails, naming it |
| a deck without `package-lock.json` | unnoticed | one finding, `no package-lock.json beside package.json` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-55 (FR-10.3; D5), realized by Stories 30.1 and 30.2. No CAP is
  minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-14 (archivo-expanded) entry.
- Epic: Epic 30. It is `done`, and the operator's rule of 2026-10-04 puts a fix-forward story under the epic it belongs
  to, never a new one; `epic-30` re-opens `done → in-progress` with this not-done story (doctor Story 41.5's reopen
  rule), the one move `ledger-regression-check` excuses.
- Ledger key: `30-3-every-react-deck-s-fonts-resolve-from-npm-and-its-lock-installs`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Flag: none (a fix, `spec-feature-flag-governance` Q1).
- Spec: the `spec-pyforge-herald` memlog records the evidence and design, this mint, and the surface reconcile.
- Surface: `marshal-policy.toml` `[epic_surfaces]."30"` (extended with this mint) covers `presentations/**`, the
  herald package, `docs/how-to/presentation-deck.md`, `tests/scripts/test_deck_export.py` and every Spec memlog.
- Minted 2026-10-14 in one chain-and-code change.

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-55 (FR-10.3; Story 30.1,
`697c985d25`); AD-22; AD-4 • Dream 2026-10-14 (archivo-expanded) • **Flag:** none

**Given** `846d8383f5`. Thirteen decks declare `@fontsource/archivo-expanded`, which the registry does not hold, and
none of the 14 `package-lock.json` files carries a `@fontsource` entry, so `npm ci` exits 1 in every deck and a build
in a `node_modules` that predates Story 30.1 fails with `Rollup failed to resolve import "@fontsource/archivo/400.css"`;
`NpmLocalProver` cannot pass and no deck records a bridge etag
**When** each Archivo deck depends on `@fontsource-variable/archivo` in place of the phantom package, drops the three
`archivo-expanded` imports, declares `'Archivo Expanded'` once in `src/index.css` as the variable face at
`font-stretch: 125%`, and every lock is regenerated from the registry with no local shim
**Then** `npm ci --no-audit --no-fund` and `npm run build` exit 0 in all 14 decks; a built bundle carries
`archivo-latin-wdth-normal-*.woff2` and a `@font-face` for `Archivo Expanded` with `font-stretch:125%`, and
`pyforge.herald.twins.scan_tree` finds no other origin in it
**And** `tests/meta/test_deck_lockfiles_current.py` reads every `presentations/*/package.json` against its lock
offline and fails a deck whose lock lacks a declared dependency; `pyforge-herald-test` is green, every Spec
`spec-surface-check` names is reconciled and stamped scoped, and `dist/`, `node_modules/` and every font binary stay
untracked

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: exit 0. This is the station's
  `verify_commands` (MRS-GATE-010 binding); it runs `tests/meta/test_deck_lockfiles_current.py` and
  `tests/meta/test_twins_zero_origin.py`.

**Run before the push (not dispatch gates):**
- Per deck, from `presentations/<deck>/`, with the shim gone (`rm -rf node_modules/@fontsource/archivo-expanded`):
  `npm install --no-audit --no-fund`, then `npm ci --no-audit --no-fund`, then `npm run build` — expected: exit 0,
  0, 0 for each of the 14 decks (AC1, AC2).
- `grep -rl "archivo-expanded" presentations/*/package.json presentations/*/src/main.jsx presentations/*/package-lock.json docs/how-to/presentation-deck.md .claude/skills/pyforge-herald/active/SKILL.md` — expected: no file (AC1, AC6).
- `grep -o 'font-family:Archivo Expanded[^}]*}' presentations/deckcraft/dist/assets/*.css` and
  `ls presentations/deckcraft/dist/assets/archivo-latin-wdth-normal-*.woff2` — expected: one declaration with
  `font-weight:700 900;font-stretch:125%` and one file (AC3).
- `pixi run --frozen -e pyforge-herald python -c "from pathlib import Path; from pyforge.herald import twins; print(twins.scan_tree(Path('presentations/pyforge-atlas/dist')))"` — expected: `[]` (AC3).
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_deck_lockfiles_current.py -q -p no:cacheprovider` — expected: exit 0, 18 passed (AC4). The negative proof: copy the 14 `package.json` and `package-lock.json` files of `846d8383f5` into a scratch `presentations/` tree and call `lockfile_findings` on each deck — expected: findings for 14/14.
- `git diff --numstat presentations/` — expected: `package.json` 1/1 for the 13 Archivo decks, `src/main.jsx` 0/3, `src/index.css` 10/0, and a `package-lock.json` for each of the 14; nothing else (AC5).
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_deck_export.py -q -p no:cacheprovider` — expected: exit 0 (AC7).
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC7).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-14 — Review pass (hand-landed; reviewer separate from the implementing agent)

Diff read against this spec and Story 30.1's. Findings: none blocking. Checked: the 13 `package.json`
swaps are exactly one dependency line each; the three `archivo-expanded` imports are gone from each
`src/main.jsx` and nothing else moved there; the `@font-face` block matches `docsite/assets/fonts/fonts.css:147-154`
(weight 700 900, stretch 125%, `woff2-variations`); the 14 regenerated locks add only the fontsource packages
(plus npm 11 dropping `libc` arrays, no resolved version moved); `npm ci` and `npm run build` exit 0 in all 14
decks; `twins.scan_tree` finds nothing in a built `dist/`; the new meta-test fails on `846d8383f5`'s locks and passes
here. Verdict: accepted; status moved to done at landing, ledger row promoted by `dispatch_land_finalize`.

## Spec Change Log

- 2026-10-14: minted from the Dream's 2026-10-14 (archivo-expanded) entry, the defect verified that day on
  `846d8383f5`. `type: fix`, no flag, no CAP. Bound to `spec-pyforge-herald` CAP-55 through Story 30.1. The chain and
  the code land in one change; review runs separately (AGENTS.md guideline 8).
