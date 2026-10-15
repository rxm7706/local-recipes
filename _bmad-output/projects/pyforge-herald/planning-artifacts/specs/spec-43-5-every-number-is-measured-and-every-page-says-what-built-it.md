---
title: '43.5: Every number is measured, and every page says what built it'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
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

## Verification run (2026-10-15)

On `f8d99e0c84` plus this change (lane A of the one-PR Pages redesign); every verdict read from the exit code.

- `pixi run --frozen -e pyforge-herald python -m pytest .../tests/unit/test_verify_claims_emit.py .../tests/meta/test_dossier_golden.py -q`
  -- exit 0, 20 passed (AC5, AC6 on a fixture tree; the golden blocks unchanged).
- The Pages test files (`test_pages_artifact.py`, `test_herald_pages_parity.py`, `test_agent_surface_and_changes.py`,
  `test_docsite_zero_origin.py`, `test_docs_site_validators.py`, `test_docs_site_imports_tracked.py`,
  `test_pages_site_url.py`, `test_docsite_build.py`, the two flag-state files, the golden and the emit tests) -- exit
  0, 384 passed, none skipped (docs-site installed). The new built tests: AC1-AC5 over a fixture tree with known line
  counts under CI's environment (`test_43_5_ac1_to_ac5_...`), `local build` without one, and the build refusing a
  section without `measured:` and a `check: moons` (each naming the section and key).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- exit 0, 2174 passed, 5 skipped (the live Design and
  webhook smokes).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 2809 passed, 3 failed: all three in
  `test_station_tests_trigger_map.py`, which read the new emit test's `cwd=REPO_ROOT` as a repository-root handoff; the
  test now runs the script on its fixture only, and the trigger map re-run alone exits 0 (45 passed). Steward's
  `tests/unit/test_pages.py` -- exit 0, 10 passed (the new tree-hash case among them).
- `pixi run --frozen -e site pages-check`: both flags off -- exit 0; both flags on with the 42.1 and 43.6 fixtures in
  `docsite/content/` (removed after) and `GITHUB_SHA=0123456789abcdef GITHUB_RUN_ID=1` -- exit 0 (the new built-from
  check over every page, the status pages' Jinja line among them; parity over 10 families and 30 twins); the CAP-56
  host (`https://pages.example.test/local-recipes`, both flags on, no CI variables) -- exit 0, every page `local build`.
- AC4's command: after that flag-on `pages-build`, `grep -c 0123456 docs-site/build/site/herald/dossier/index.html` --
  1. AC5: `PYFORGE_PAGES_ONE_GENERATOR=1 pixi run --frozen -e site site-verify` over the built page -- exit 0, "All
  checked claims match the source tree"; with the flag unset it compares the YAML's typed values as before -- exit 1, 1
  claim (steward's test lines, 49,783 typed against 53,284).
- AC7: the Jinja build with the flag off (`docsite/build.py --out`), before and after this change -- `diff -r` exit 0
  over 141 files; the Astro build with the flag off against `f8d99e0c84`'s (`git archive`, the same `node_modules`) --
  `diff -r` exit 0 over 177 files.
- The carry-in: two flag-on builds differing only in `GITHUB_RUN_ID` and `PAGES_BUILT_AT` differ in 115 HTML files'
  bytes (the line) and hash the same under steward's `tree_hash`; the Pagefind index does not change
  (`data-pagefind-ignore`).
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0. `pixi run --frozen -e site docs-site-validate` -- exit 0.
- Browser (headless Chromium through the `pyforge-herald` env's Playwright, the CAP-56 artifact under
  `/local-recipes/`): the dossier's atlas section reads "measured on 2026-10-14" under its head and `34,220` / "Lines ·
  133 files" (the measured values); the dossier, a docs page and `/status/` each end with the built-from line in the
  theme's mono gray; no console error.
- Mutations (each a test): the fixture's typed values differ from its counts and the page shows the counts; a section
  without `measured:` and an unknown key fail the build; no `GITHUB_SHA` reads `local build`; a page showing a typed
  value makes the compare exit 1.
- Not run here: the memlog reconcile, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating session
  runs them once for the branch).

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

- 2026-10-15: implemented (lane A of the one-PR Pages redesign); status `in-review`. Deviations and readings, each for
  the reviewer and the operator to keep or overturn:
  - **The typed values stay in `dossier.yml`** (the Approach said the `check:` stats lose them): AC7 holds the Jinja
    dossier byte-identical with the flag off, and the Jinja path renders the typed values. The Astro path ignores them
    (AC1; the spec's own mutation types a wrong value and expects the measured one), and they leave with the Jinja
    path in Story 43.7. The YAML gains only keys: `measured: '2026-10-14'` on all twelve sections -- the date the
    file's header and summary give for the last re-verification against the tree (a human dates a section anew when
    they re-read it) -- and `check: fleet_src_lines` on the hero's "Lines of source", so the hero's total, which the
    compare already checks by its label, is measured too.
  - **A `src_lines` stat's label shows the measured file count** ("Lines · 133 files"): the compare checks the label's
    number of files as a claim of its own, so a page with a measured value and a typed file count would still drift.
  - **The emit shape** (AC6): `{check key: {section id: {"value": shown, "files": n}}}` -- `files` on `src_lines` only,
    `fleet` the hero's entry; values formatted as the dossier writes them (`34,220`, `py3.14`, `~264K`). The hero's
    total sums the station sections, as the compare does. An unknown key, or a section whose package is missing,
    exits 2 naming it (`ValueError` in `emit()`); `--root` measures another tree (the tests' fixtures).
  - **The loader runs the measurer** (`execFileSync` of `verify_claims.py --emit -`, `$PYTHON` else `python` on `PATH`
    with PyYAML, as the `site` env provides), so every build path -- `pages-build`, a direct `astro build`, the tests
    -- measures, and the measurer stays the one measurement. It reads the dossier and measures the tree at
    `HERALD_PAGES_REPO_ROOT` when set (a fixture), as the herald-pages loader does.
  - **The dossier schema is now applied** (`parseData` in the object loader): before this story the collection's
    schema -- the `title`, the block-type allow-list -- never ran, since an object loader validates only through
    `parseData`; the `measured:` refusal names the section (AC3), and the block types are checked as their comment
    claimed.
  - **AC5 without editing the workflow** (Boundaries: `pages.yml` is steward's): with the flag on, the compare reads the
    stats the built dossier shows (`docs-site/build/site/herald/dossier/index.html`, which `pages-check` writes before
    the `site-verify` step runs; `--page` names another) -- the comparison logic is unchanged, only the values' source
    is the page, so the advisory judges what readers see; a page whose stats do not line up with the YAML's, or no
    built page, exits 2 naming it. Flag off, it compares the YAML as before.
  - **The footer** is one element, `<p class="built-from" data-pages-built-from data-pagefind-ignore>`, plain text
    (`src/lib/built-from.ts`): "Built from <sha7> · <YYYY-MM-DD HH:MM> UTC · run <id>" (the run part only when
    `GITHUB_RUN_ID` is set), else `local build`. The time is `PAGES_BUILT_AT`, which the assembler sets once per build
    so every page and both generators agree (AC4's "a build time in the environment"); a direct build without it uses
    the build's own clock. Where it renders: the docs pages through a Starlight `Footer` override registered only
    with the flag on (Starlight's footer, then the line); the herald layouts and the reader pages below the page; the
    Jinja `/status/` and `/status/ci/` pages inside their footer, through `docsite/tools/status_pages.built_from_html`,
    the Python twin until Story 43.7 moves those pages (a test holds the two equal byte for byte). Not on a twin or the
    Kedro-Viz / Vizro mounts (Never), the CAP-47 artifact build (`herald/artifact/`), a redirect stub or Pagefind.
    `pages-check` (flag on) now refuses a page with no line or two, or two pages naming different builds
    (`assemble_pages._check_built_from`). Styled once in `theme.css` (`.built-from`: the mono face, `gray-3`, 5.25:1).
  - **Carry-in, cross-station (steward):** the line must not redeploy every build. `pyforge.steward.pages.tree_hash`
    now reads each `.html` file with the `data-pages-built-from` element's text dropped (the element still counts),
    replacing `HASH_EXCLUDE_RELATIVE`'s note that the footer's paths would join it -- the line is on every page, not at
    a path. A rebuild of an unmoved tree therefore hashes the same and deploys nothing, and Story 102.3's 24-hour
    liveness rule keeps the live build honest; a content change still moves the hash. Steward's
    `tests/unit/test_pages.py` gains the case; `scripts/pages_build_stamp.py` is unchanged. Recorded here as the
    carry-in it is; steward's spine already describes the hash "with the built-from footer excluded".
  - **`/status/`'s snapshot line is measured data** (the carry-in's question): `generated_at` is HEAD's commit time,
    the moment the ledger counts were read, so it changes exactly when the counts may -- with a commit -- and stays in
    the hash. The footer's commit, time and run id are build provenance and do not.
  - **Smaller:** `verify_claims.py`'s `--format github` annotations named `docdocsite/content/dossier.yml`; fixed to
    `docsite/content/dossier.yml`. `pages_astro.fixture_tree` gains a package per station with known counts
    (`station_packages`), and `astro_build` drops `GITHUB_SHA`, `GITHUB_RUN_ID` and `PAGES_BUILT_AT` unless a test
    passes them, so a build under CI renders as a local one. `verify_claims.py` grows from 237 to 338 lines, which
    Story 43.7's 300-line budget for `docs-site/**/*.py` has to account for when it moves the script.
- 2026-10-14: specced at mint from Epic 43's Story 43.5 text, `spec-pyforge-herald` CAP-61, FR-12.5 and the Dream's
  2026-10-13 entry (M3), against `verify_claims.py` and `dossier.yml` as they stand on 2026-10-14 (the `--json` compare
  output exists; `--emit` does not).
