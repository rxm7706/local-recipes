---
title: '43.4: Fonts and theme come from one design system'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'the Jinja path serves its own stylesheet and the vendored woff2 files exactly as it does today'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-31-3-the-public-pages-build-loads-no-third-party-resource-from-herald-s-own-pages.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - docsite/assets/_dossier.css
  - docsite/assets/_site-chrome.css
  - docsite/assets/fonts
  - docsite/build.py
  - docs-site/package.json
  - docs-site/package-lock.json
  - docs-site/astro.config.mjs
  - docs-site/README.md
  - src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-08 Google Fonts loaded on 45 pages of the artifact; Story 31.3 fixed it by vendoring 25
`woff2` files under `docsite/assets/fonts/` with a hand-written sha256 table, so no herald page loads Google Fonts. The
herald pages carry their own stylesheets (`docsite/assets/_dossier.css`, `_site-chrome.css`) beside Starlight's, so a
reader moving between the docs and the dossier sees two typographies, two colour systems and a dark mode that only the
docs have. The brainstorm named the Google Fonts incident and the dossier-numbers drift as one class, "a check nobody
reads", and the cure as structural: fonts through npm, a CSP meta.

**Approach:** one typography, one colour system and one dark mode across every prefix, with no hand-vendored font file.

- **Fonts through `@fontsource`.** `docs-site/package.json` gains `@fontsource/big-shoulders-display`,
  `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`, `@fontsource/archivo` and `@fontsource-variable/archivo`;
  the herald pages import the faces they use and Astro bundles them into the artifact, on the configured origin.
- **One stylesheet.** A shared stylesheet under `docs-site/src/` maps the dossier's tokens (the custom properties
  `_dossier.css` and `_site-chrome.css` define) onto Starlight's theme variables, with a dark block under Starlight's
  `[data-theme='dark']` selector, so the herald pages follow the toggle the docs header already has and read as one
  place with the shelf.
- **Parity with the Jinja path.** The `font-family` the dossier's headings and body resolve to on the Astro path equals
  the Jinja path's (the declarations in `_dossier.css` for the same selectors).
- **What stays and what leaves.** The five vendored upstream files keep their recorded hashes (`docs-site/README.md`).
  `docsite/assets/fonts/` and its sha256 table serve the Jinja path until Story 43.7 retires both; from this story the
  Astro path references nothing under `docsite/assets/`.
- **The origin rule.** No font loads from another origin; Story 43.3's origin check and CSP meta judge the fonts as
  they judge everything else.

Ledger key: `43-4-fonts-and-theme-come-from-one-design-system`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / 43.1.

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.4): fonts through `@fontsource`; one theme across every prefix. On AD-21
  (zero third-party origins; the five vendored files hash-pinned) and the Story 31.3 vendoring it replaces (CAP-56's
  no-third-party rule as built).
- **AD-23**: a stylesheet and font imports under `docs-site/src/`, no copy step.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("fonts through `@fontsource`");
  `brainstorm-intent.md` § *The finding* (the 2026-10-08 Google Fonts incident) and § M3 ("Starlight theme tokens on
  every page"); design-thinking § *Target information architecture* ("one footer, one theme") and § *Success Metrics*
  (third-party origins: 0, structural: `@fontsource`, CSP meta).

## Acceptance Criteria

- **AC1 — Faces from the bundle.** Given the flag on, When the site builds, Then every `@font-face` the herald pages
  load names a `src` under the artifact's own `_astro/` (or configured assets) path, and `package.json` lists the five
  `@fontsource` packages with `package-lock.json` resolved.
- **AC2 — Same families.** A test reads the `font-family` declarations for the dossier's heading and body selectors in
  the Astro stylesheet and in `docsite/assets/_dossier.css` and finds them equal.
- **AC3 — Dark mode.** The shared stylesheet defines the dossier tokens under the light root and again under
  `[data-theme='dark']`, and the two blocks differ; a herald page built with the flag on carries no inline theme of
  its own.
- **AC4 — No vendored font on the Astro path.** `grep -rn "assets/fonts" docs-site/src` finds nothing, and no herald
  page built with the flag on references a `.woff2` under `herald/assets/`.
- **AC5 — The origin rule.** `pages-check`'s origin check finds no font loaded from another origin; a planted
  `fonts.googleapis.com` stylesheet link on a herald page makes it exit 1.
- **AC6 — The five files.** The hash test over the five vendored upstream files (`.nvmrc`, `scripts/fix-doc-links.js`,
  `scripts/validate-doc-links.js`, `scripts/validate-sidebar-order.js`, `src/lib/site-url.mjs`) passes against
  `docs-site/README.md`'s table.
- **AC7 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Load every font from the artifact's own origin (AD-21); `@fontsource` through `package.json`, never a URL.
- Map onto Starlight's theme variables; never a second toggle, a second theme store or a herald-only dark mode.
- Keep `package-lock.json` resolved and committed with `package.json`; `npm ci` is what `test_docs_site.py` pins.
- Keep the five vendored files byte-identical (AD-21 rule 5).
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not delete `docsite/assets/fonts/` or its sha256 table here (Story 43.7); the Jinja path still serves them.
- Do not add a font the dossier does not use, or change the families the dossier's headings and body use.
- Do not edit Starlight's own stylesheets or the vendored validators.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on | herald pages | fonts from the bundle, one stylesheet, dark block present | exit 0 |
| flag off | herald pages | today's `_dossier.css`, `_site-chrome.css` and vendored woff2 | exit 0 |
| docs page | any | unchanged Starlight theme; fonts unaffected | exit 0 |
| planted Google Fonts link | a herald page | — | `pages-check` exit 1 |
| second host | CAP-56 fixture | font `src` under that origin | exit 0 |
| `package.json` without the lock refreshed | regression | — | `npm ci` fails in the build |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.4), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14) on AD-21 (zero third-party origins; rule 5).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.4.
- Ledger key: `43-4-fonts-and-theme-come-from-one-design-system`.
- Ledger status at mint: `backlog`.
- Deps: Story 43.1 (the Astro dossier page the stylesheet themes). `marshal factory dispatch` stamps
  `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** 43.1 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.4), on AD-21 (zero third-party origins) and the Story 31.3 vendoring it replaces
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** Story 31.3 vendored 25 `woff2` files with a hand-written sha256 table so no herald page loads Google Fonts,
and the herald pages carry their own stylesheet beside Starlight's
**When** the site builds with the flag on
**Then** every herald page loads its faces from `@fontsource` imports bundled by Astro, the computed `font-family` of
the dossier's headings and body match the Jinja path's, dark mode follows Starlight's theme toggle on herald pages, and
the origin check finds no font loaded from another origin
**And** the five vendored upstream files are byte-identical to their recorded hashes; `pages-check` and
`pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py -q` — expected: pass (AC2–AC6).
- `pixi run --frozen -e site pages-check` with the flag on and off — expected: exit 0 both times (AC1, AC7).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- A screenshot of `/herald/dossier/` and a docs page from the built artifact in light and in dark mode (herald's browser check), showing one typography.

**Mutations (each restored afterwards):**
- Change the body `font-family` on the Astro path only — expected: AC2's test fails.
- Remove the `[data-theme='dark']` block — expected: AC3's test fails.
- Plant a `fonts.googleapis.com` link — expected: `pages-check` exits 1.

## Named, not fixed here

- **The retirement** of `docsite/assets/fonts/`, the sha256 table and `_dossier.css` / `_site-chrome.css` with the
  Jinja path: Story 43.7 (CAP-61's success: "no `.woff2` file or sha256 row remains under `docsite/`").
- **The CSP meta** and the under-40-line origin check: Story 43.3.
- **The design system's name and token set** beyond the dossier's (a site-wide palette for `/status/` and `/changes/`):
  Stories 42.1 and 43.6 use the shared stylesheet as this story leaves it.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 43's Story 43.4 text, `spec-pyforge-herald` CAP-61, FR-12.4 and the Dream's
  2026-10-13 entry (M3), against `docsite/assets/` and `docs-site/package.json` as they stand on 2026-10-14. The five
  `@fontsource` package names are Epic 43's.
