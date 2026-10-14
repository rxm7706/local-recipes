---
title: '43.5: Every number is measured, and every page says what built it'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
flag:
  key: pyforge.herald.pages_one_generator        # Story 43.1's; shared across Epic 43 (one flag per CAP, Q6), not minted here
  provider: openfeature-file                     # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                  # v1 is global only
  fallback: 'the Jinja dossier shows its hand-typed stat values, no measured-on line and no built-from footer, and site-verify stays the advisory it is today'
  cleanup: retired by Story 43.7 with the Jinja path (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-43-1-astro-renders-the-dossier-from-dossier-yml.md
  - docsite/tools/verify_claims.py
  - docsite/content/dossier.yml
  - docsite/README.md
  - docsite/build.py
  - docs-site/src/content.config.ts
  - docs-site/astro.config.mjs
  - .github/workflows/dashboard.yml
  - src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The dossier states concrete figures (lines of source, file counts, floors, test ratios), and
`docsite/tools/verify_claims.py` compares the hand-typed values of every stat carrying `check:` against the source tree
and reports drift. It is advisory: the deploy runs it as `site-verify` with `continue-on-error: true`, and on
2026-10-13 it reported 17 drifted claims on a run that went green. Nobody reads an advisory annotation on a workflow
that ran about 24 times a day. The dossier's own finding ("every station's own docs undercount its own surface")
applies to the dossier. No page says when its prose was last measured or which commit and run built it, so a stale
site cannot tell on itself.

**Approach:** the measurer becomes a producer, the prose carries its date, and every page carries its provenance.

- **The measurer emits.** `verify_claims.py` gains an `--emit` mode that writes the measured values as JSON (one value
  per `check:` key the dossier uses, `src_lines` among them), and the `dossier` collection's loader (Story 43.1) reads
  that JSON at build so every stat with a `check:` key shows the measurer's value. A stat without `check:` shows its
  typed value. The compare mode stays as it is, so `site-verify` keeps running in CI as the advisory it is (CAP-46), and
  now reports 0 drifted claims on the built page because the page shows what it measured.
- **`dossier.yml` changes shape, not text.** Each section gains a `measured:` date (the day its prose was last checked
  against the tree); the `check:` stats keep their keys and lose their hand-typed values. The page renders "measured on
  <date>" per section from that field.
- **The footer.** A Starlight `Footer` component override, used by the docs pages and the herald pages alike, names the
  first seven characters of `GITHUB_SHA`, the build time and `GITHUB_RUN_ID`, read from the environment at build; with
  none set it says `local build`. The values come from the workflow's own environment, not from a `gh` call.
- **A fixture tree.** The tests measure a fixture package with a known line count and assert the built page renders
  that count; a stat without `check:` renders its typed value unchanged.
- **The flag.** With `pyforge.herald.pages_one_generator` off, the Jinja dossier shows its typed values as today and no
  footer or measured-on line appears; `site-verify` is unchanged.

Ledger key: `43-5-every-number-is-measured-and-every-page-says-what-built-it`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / 43.1.

### Living CAP citations

- **`spec-pyforge-herald` CAP-61** (FR-12.5): computed stats, the measured-on date, the built-from footer. On CAP-44
  (the dossier is the source; the YAML keeps the prose and the keys) and CAP-11 (Moment 2: factory motion is visible —
  a page that says when it was built). CAP-46's rule that `verify_claims.py` stays advisory in the deploy is kept.
- **AD-23**: the measurer is one more producer of data the generator reads.
- **Origin.** Dream `docs/dreams/pyforge-herald.md`, the 2026-10-13 entry, M3 ("every dossier stat with `check:` is
  computed at build and every page carries a built-from footer"); `brainstorm-intent.md` § *The finding* ("17 dossier
  claims drifted, advisory, step green") and § M3; design-thinking § *Success Metrics* (dossier stat claims drifted: 17
  today, 0 computed at build at M3; prose carries "measured on").

## Acceptance Criteria

- **AC1 — Measured values.** Given a fixture tree whose measurer reports a known `src_lines`, flag on, When the site
  builds, Then the built dossier shows that count for the stat with `check: src_lines`, and every stat with a `check:`
  key shows the emitted value for its key.
- **AC2 — Typed values.** Given a stat without `check:`, Then the built page shows its typed value unchanged.
- **AC3 — Measured on.** Given every section of `dossier.yml` carries `measured:`, Then each built section shows
  "measured on <date>" with that date; a section without `measured:` fails the collection's schema naming the section.
- **AC4 — The footer.** Given `GITHUB_SHA`, `GITHUB_RUN_ID` and a build time in the environment, Then every HTML page
  of the artifact (docs and herald) carries a footer naming the first seven characters of the SHA, the time and the run
  id; given none set, the footer says `local build`.
- **AC5 — Zero drift.** `pixi run --frozen -e site site-verify` over the built page reports 0 drifted claims; the task
  keeps exit 1 on drift and stays `continue-on-error` in the deploy (not edited here).
- **AC6 — The shape.** `--emit` writes valid JSON with one key per `check:` key the dossier uses; a `check:` key the
  measurer does not know fails the build naming the key and the section.
- **AC7 — Flag off.** Given the flag off, Then the Jinja dossier is byte-identical to a build without this story and no
  footer line is added to it.
- **AC8 — The gates.** `pixi run --frozen -e site pages-check` exits 0 in both flag states;
  `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green.

## Boundaries & Constraints

**Always:**
- Keep `verify_claims.py` the one measurer (`measure()` and its tolerance); `--emit` adds an output, never a second
  measurement.
- Keep the dossier's prose in `dossier.yml`; this story changes the stats' values and adds `measured:` dates, nothing
  else of the text (CAP-44).
- Read `GITHUB_SHA` and `GITHUB_RUN_ID` from the environment the workflow already provides; call no `gh` and add no
  token.
- Keep `site-verify` advisory in CI (CAP-46); the deploy workflow is steward's and is not edited.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names through its memlog, then stamp scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not let the measurer rewrite `dossier.yml` (editorial changes stay human, as its docstring says).
- Do not add a footer to the twins or the Kedro-Viz bundle (copied, never edited).
- Do not move `verify_claims.py` here (Story 43.7 moves it to `docs-site/scripts/`).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `check: src_lines` | fixture tree, N lines | the page shows N | exit 0 |
| stat without `check:` | typed `~200K` | shown as typed | exit 0 |
| unknown `check:` key | `check: moons` | — | build exit 1, names key and section |
| section without `measured:` | fixture | — | schema refusal naming the section |
| CI environment | `GITHUB_SHA`, `GITHUB_RUN_ID` set | footer with SHA[:7], time, run id | exit 0 |
| local build | none set | footer says `local build` | exit 0 |
| `site-verify` on the built page | flag on | 0 drifted claims | exit 0 |
| flag off | any | Jinja dossier, typed values, no footer | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (FR-12.5), minted 2026-10-14.
- Architecture: AD-23 (adopted 2026-10-14; the measurer as a producer of data).
- Dream: `docs/dreams/pyforge-herald.md` § Realization log, the 2026-10-13 (the Pages deployment, redesigned) entry, M3.
- Epic: Epic 43, Story 43.5.
- Ledger key: `43-5-every-number-is-measured-and-every-page-says-what-built-it`.
- Ledger status at mint: `backlog`.
- Deps: Story 43.1 (the collection and its loader). `marshal factory dispatch` stamps `baseline_revision` with the
  launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`.
- Flag: `pyforge.herald.pages_one_generator` (shared with 43.1; `feature-flag-governance:CAP-1`, Q6).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 43.1 • **FR/AD:** spec-pyforge-herald CAP-61 (FR-12.5), on CAP-44 (the dossier is the source) and CAP-11 (progress visibility)
**Flag:** `pyforge.herald.pages_one_generator` (shared with 43.1)

**Given** `verify_claims.py` compares hand-typed stat values against the tree and reported 17 drifted claims on
2026-10-13 as a `continue-on-error` step nobody reads
**When** the site builds with the flag on
**Then** every stat with a `check:` key shows the measurer's value, a stat without `check:` shows its typed value, each
dossier section shows "measured on <date>" from its `measured:` field, and every page's footer names the first seven
characters of `GITHUB_SHA`, the build time and the run id (or `local build` when unset)
**And** a fixture tree with a known line count renders that count; `site-verify` reports 0 drifted claims on the built
page; `pages-check` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py src/shared/packages/pyforge-herald/tests/meta/test_dossier_golden.py -q` — expected: pass (AC1–AC4, AC6).
- `pixi run --frozen -e site pages-check` with the flag on and off — expected: exit 0 both times (AC7, AC8).
- `pixi run --frozen -e site site-verify` after a flag-on build — expected: 0 drifted claims, exit 0 (AC5).
- `GITHUB_SHA=0123456789abcdef GITHUB_RUN_ID=1 pixi run --frozen -e site pages-build`, then `grep -c 0123456 docs-site/build/site/herald/dossier/index.html` — expected: at least 1 (AC4).
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconcile and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Mutations (each restored afterwards):**
- Type a wrong value into a `check:` stat's fixture — expected: the built page still shows the measured value (AC1), and the typed value is ignored.
- Remove `measured:` from one section — expected: the schema refuses naming the section.
- Unset `GITHUB_SHA` — expected: the footer reads `local build`.

## Named, not fixed here

- **The move** of `verify_claims.py` to `docs-site/scripts/` and the `site-verify` task's retirement: Story 43.7 (the
  measurer's line count is part of AD-23's 300-line budget there).
- **A scheduled refresh** of the artifact render once the stats are computed (the Dream's *refreshed* clause): an
  operator decision; the session-close ritual (Story 41.1) stands until then.
- **A site-health tile** on the dossier (last deploy, run count this month, cancelled streak, export age; the
  brainstorm's M3 idea): not in CAP-61; a later Dream entry if wanted.
- **The 17 drifted claims of 2026-10-13**: corrected by the measured values; the prose around them is editorial and
  gets its `measured:` date when a human re-reads it.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 43's Story 43.5 text, `spec-pyforge-herald` CAP-61, FR-12.5 and the Dream's
  2026-10-13 entry (M3), against `verify_claims.py` and `dossier.yml` as they stand on 2026-10-14 (the `--json` compare
  output exists; `--emit` does not).
