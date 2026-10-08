---
title: "30.1: A deck's HTML twins are self-contained and published"
type: 'feature'
created: '2026-09-28'
status: 'ready-for-dev'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.herald.deck_viewer
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'herald deck publish publishes the tracked exports only, exactly as Story 29.1 left it, and no twin is built or uploaded'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-29-1-herald-deck-publish-puts-each-current-export-in-the-object-store.md
  - scripts/deck_export.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py
  - presentations/pyforge-herald/index.html
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The operator ruled on 2026-09-28 that the viewer shows Herald's decks through their
HTML twins: the standalone Marp HTML (`src/marp/<slug>-infographic-standalone-<date>.html`) and the
React/JSX deck's built bundle (`presentations/<slug>/dist/`, gitignored). Inside the airgap a twin
must load nothing from another origin, and today most do. Measured on 2026-09-28 (`cfae04e14b`):
- 2 of the 15 current standalone twins load from another origin.
  `agentic-sdlc-infographic-standalone-2026-07-23.html` loads fonts.googleapis.com, and
  `pyforge-warden-infographic-standalone-2026-09-15.html` loads twemoji SVGs from cdn.jsdelivr.net.
- All 14 React decks' `index.html` load Google Fonts from fonts.googleapis.com and
  fonts.gstatic.com.
- No bundle is ever built for a reader. `deck_qa.py` builds one only to screenshot it.

**Approach:**
- *Vendor.* The 14 React decks take their fonts from npm font packages (for example
  `@fontsource/archivo`) resolved at build time, and set `base: './'` so a bundle resolves under
  any prefix. The two failing standalones are re-exported through `deck-export <slug> html` with
  the reference vendored: agentic-sdlc's Google Fonts import, and pyforge-warden's twemoji images
  (inlined, or Marp's emoji image conversion turned off). Story 28.2's writer retires each
  predecessor.
- *Scan.* `pyforge.herald.twins` holds the one zero-origin scan: every `src`, `href`, `url()` and
  `@import` that names an origin is a finding, and plain `<a href>` navigation is allowed.
- *Publish.* With `pyforge.herald.deck_viewer` ON, `herald deck publish` also builds each React
  bundle (`npm ci`, then `vite build` in the deck folder) and puts the twins in the store through
  `deck_store`. A standalone is one sha256 object. A bundle is one object per file plus a bundle
  manifest mapping each relative path to its key. Both are recorded in the deck's manifest.
  Publish refuses a twin that fails the scan, naming the file and the origin (D5).

Ledger key: `30-1-a-deck-s-html-twins-are-self-contained-and-published`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-28.2, S-29.1.

### Living CAP citations

- `spec-pyforge-herald` CAP-55 (FR-10.3; decision D5 in `.memlog.md`); AD-22; CAP-53 (a re-export retires its predecessor); AD-4 (`dist/` stays gitignored).
- `feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given the story's tree When `tests/meta/test_twins_zero_origin.py` runs Then every current standalone twin and every React deck's `index.html` has zero references to another origin
- Given a built bundle When the scan runs over `dist/` Then it finds no reference to another origin
- Given a planted twin that loads `https://fonts.googleapis.com/...` When publish runs Then it exits non-zero naming the file and the origin, and uploads nothing for that twin
- Given the flag ON When `herald deck publish <slug>` runs Then the deck's twins are in the store and its manifest records them, a bundle with a path-to-key manifest
- Given the flag OFF When `herald deck publish <slug>` runs Then no twin is built or uploaded and the output equals Story 29.1's
- Given plain `<a href="https://...">` navigation links When the scan runs Then they are not findings

## Tasks

- [ ] Read `pyforge.herald.deck_viewer` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape
- [ ] Vendor fonts in the 14 React decks (`index.html`, `package.json`, `vite.config.js`); set `base: './'`
- [ ] Re-export the agentic-sdlc and pyforge-warden standalones with the reference vendored (extend `scripts/deck_export.py` only if needed)
- [ ] `twins.py`: the scan, the React build, the bundle manifest
- [ ] `deck_publish.py`: twin publishing behind the flag, and the refusal
- [ ] `src/platform/config/flags.json`: `pyforge.herald.deck_viewer`, `defaultVariant` off
- [ ] Tests, including the live-tree meta-test and the ON/OFF test
- [ ] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **The flag reader** (coordinator ruling 2026-09-28): `herald deck publish` (whether it builds and uploads twins) reads `pyforge.herald.deck_viewer` through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract (`75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`). If 75.1 has not landed when this story runs, add it to `pyforge.core` in exactly 75.1's shape -- `read_boolean(key, default=False)` in `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: it resolves the tree as `cutover_root.resolve_flags_path` does, returns False for `state: DISABLED`, returns the `defaultVariant`'s value when it is a bool, and reads False with a named WARN on stderr for a missing tree, a missing key or a non-bool value, never True; with `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, reconciled on `spec-pyforge-core` -- and never write a station-local reader.
- The scan is the one definition of "self-contained"; the portal (30.2) and the tests reuse it.
- Fonts come from npm packages resolved at build time, through the same registry path as vite itself; no network at view time.
- A re-exported standalone goes through `deck-export` and CAP-53's one-version rule, never a hand edit of a dated file.
- Warden scans the vendored JavaScript like any other dependency; add no second verdict.
- The PR carries the `maintenance` label.

**Never:**
- Do not write a station-local flag reader, and do not parse the flag tree from herald code.
- Do not track `dist/`, `node_modules/` or a font binary.
- Do not parse `.pptx` in the browser, and add no PPTXjs, jQuery or JSZip.
- Do not publish a twin that fails the scan, or loosen the scan to let one through.
- Do not change a deck's content or design; only where its fonts and images load from.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean standalone | no external reference | published as one object | exit 0 |
| font import | `@import url(https://fonts.googleapis.com/...)` | finding naming the file and fonts.googleapis.com | publish exits 1 |
| image | `<img src="https://cdn.jsdelivr.net/...">` | finding | publish exits 1 |
| navigation link | `<a href="https://github.com/...">` | not a finding | — |
| data URI | `url(data:font/woff2;base64,...)` | not a finding | — |
| bundle | `dist/` with `index.html` and `assets/*` | one object per file plus a path-to-key manifest | exit 0 |
| build fails | `vite build` exits non-zero | named error; nothing uploaded for the deck's bundle | exit 1 |
| no React sources | a deck without `package.json` | the standalone only | exit 0 |
| flag OFF | any | no twin built or uploaded | as Story 29.1 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-55 (FR-10.3; D5).
Architecture: AD-22.
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `30-1-a-deck-s-html-twins-are-self-contained-and-published`.
Ledger status at mint: `backlog`.
Deps: S-28.2 (a re-export retires its predecessor), S-29.1 (the store port and the publish verb). Through S-29.1 this story also waits on steward Story 74.1.
Flag: `pyforge.herald.deck_viewer` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-28.2, S-29.1 • **FR/AD:** spec-pyforge-herald CAP-55 (FR-10.3; D5); AD-22 • flag: `pyforge.herald.deck_viewer`

**Given** 2 of 15 current standalone twins and all 14 React decks load from another origin, and no bundle is ever built for a reader
**When** the fonts and images are vendored and the twin publisher lands
**Then** the zero-origin scan passes on every current standalone, every deck's source `index.html` and a built bundle; publish refuses a planted twin that names another origin, naming the file and the origin, and exits non-zero
**And** with the flag ON, `herald deck publish <slug>` puts the twins in the store and records them in the manifest; with it OFF, publish behaves exactly as Story 29.1 left it; `pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; the zero-origin meta-test over the live tree, the twin unit tests and the ON/OFF test run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.deck_viewer` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, and asserts publish uploads twins ON and none OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- Build one React deck (`npm ci && npm run build` in `presentations/pyforge-herald/`), open `dist/index.html` from a browser with no route to the internet, and confirm the fonts render.
- `pixi run -e site site-check` — expected: exit 0 (the re-exported standalones still publish on the family pages).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log
