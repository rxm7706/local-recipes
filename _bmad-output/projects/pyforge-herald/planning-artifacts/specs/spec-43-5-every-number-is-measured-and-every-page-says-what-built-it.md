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
review_loop_iteration: 1
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
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py -q -k 43_5` — expected: pass (AC1–AC6: the emit and compare on a fixture tree, the built dossier and footer over a fixture tree, `pages-check`'s built-from check, the status pages' line and its TypeScript twin; corrected at the review -- `src/shared/packages/pyforge-herald/tests/meta/test_dossier_golden.py` is Story 43.1's block parity and checks none of them; Story 43.7 moved the built-dossier tests from the deleted parity test to the one-generator test named above).
- `pixi run --frozen -e pyforge-herald python -m pytest src/shared/packages/pyforge-herald/tests/meta/test_dossier_golden.py -q` — expected: pass (the dossier's blocks unchanged).
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

- 2026-10-15 (Story 43.7's review): the Verification named the parity test Story 43.7 deleted; it names
  `src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py`, where this story's built-dossier tests moved,
  and gives `test_dossier_golden.py` its repo path.
- 2026-10-15 (independent review, iteration 1: FAIL, 4 should-fix and 7 nits; resolved, with the coordinating
  session's rule that a finding in a file Story 43.7 deletes or ports -- the Jinja templates, `build.py`, the
  assembler -- is fixed where 43.7 leaves the behaviour, carried into its spec, not fixed twice):
  - **Should-fix 1 (steward carry-in), fixed.** `pyforge.steward.pages.BUILT_FROM_TEXT` matches only the exact element
    herald emits and `pages-check` enforces, `<p class="built-from" data-pages-built-from data-pagefind-ignore>[^<]*</p>`:
    a value that mentions the name (`href="#data-pages-built-from"`), a longer name (`data-pages-built-from-x`),
    another attribute order or another tag keeps its text in the hash -- a change there over-deploys, never hides.
    Steward's `test_tree_hash_drops_only_the_exact_built_from_element` covers the five shapes, and the earlier test a
    content change beside the element.
  - **Should-fix 2 (`_BUILT_FROM_EXEMPT` exempts all of `dashboard/`), carried into Story 43.7.** Herald's pipelines
    page `dashboard/index.html` is a Jinja page (`page_pipelines.html.j2`, rendered by `build.py` when the Kedro-Viz
    export is mounted), and both it and `assemble_pages.py`'s check retire with 43.7; narrowing the exemption now
    would red `pages-check` until that page carried the line, which is a template 43.7 deletes. 43.7's spec carries:
    its pipelines page (if it keeps one) carries the line, and its built-from check exempts only the mounted exports
    (`dashboard/kedro-viz/`, `dashboard/vizro/`, any other mounted board), with a test. **Why `herald/artifact/` is
    exempt** (recorded here, as the review asked): it is CAP-47's artifact build, the dossier as one self-contained
    file republished to Claude Design by its ritual (`docsite/README.md`), a deliverable copied out of the site as a
    twin is -- not a page of it -- so a per-build line would change the deliverable on every build.
  - **Should-fix 3 (a wall-clock date stays in the hash), fixed where it lives on.** The Astro herald pages held two:
    the shell's nav stamp ("Built <date> · <commit>") and "Site rebuilt <date>" in the overview, gallery and deck
    footers. Both are gone with the flag on (the only state these pages exist in): the built-from line below each page
    is the one place a build's time and commit appear, and `herald-pages.ts`'s `builtAt()` and the loader's `builtAt`
    field leave with them. `test_43_5_a_build_two_days_later_of_an_unmoved_tree_differs_only_in_the_built_from_line`
    builds the fixture tree twice, the second with node's clock shifted two days, another run id and another
    `PAGES_BUILT_AT`, and finds every file byte-identical once the line's text is dropped (a wall-clock stamp planted
    in the shell fails it: five pages differ). The Jinja `/status/`, `/status/ci/` and pipelines footers keep
    "Site rebuilt <date>" until Story 43.7 ports them; its spec carries the requirement (the line in place of the
    date, and the two-day proof over the whole artifact with the status pages on). Flag off, nothing changes.
  - **Should-fix 4 (two-state coverage), fixed.** `@flag_states("pyforge.herald.pages_one_generator")`:
    `test_43_5_the_build_hands_the_status_pages_the_line_only_with_the_flag_on` runs `build()` with the status pages
    and finds the line exactly when the flag is on; `test_43_5_ac5_with_the_flag_on_site_verify_reads_the_built_page_by_default`
    runs `verify_claims.main()` (which now takes `argv`) without `--page` -- on, exit 2 naming the default built page
    when absent and 0 over a measured one; off, the YAML compare (exit 1 on the fixture's stale values).
  - **Nits.** 5: a reader page's frame is `calc(100vh - 32px - 1.5rem)` and its built-from line a fixed 1.5rem, so the
    page does not scroll (checked in the browser at 1280x900 and 390x844 on an infographic and a deck view:
    `scrollHeight == innerHeight`). 6: both twins accept one `PAGES_BUILT_AT` form, an ISO 8601 date-time with seconds
    and an offset, and refuse a date alone, a naive time or anything else (the TypeScript twin throws, the Python one
    raises); the parity test adds an offset that crosses the UTC date and the three refusals. 7: `assemble()` no longer
    sets `os.environ`; it hands `PAGES_BUILT_AT` to the Astro and the herald builds' environments. 8: the measurer
    runs under `HERALD_PYTHON || 'python'`. 9: "Measured on" is left as AC3 words it (the coordinating session takes
    the wording to the operator). 10: § Verification now credits the AC tests, not the golden; 43.7's spec carries
    `verify_claims.py`'s 338 lines into its budget. 11: `pages.yml`'s push filter (steward's) does not list
    `src/shared/packages/**`, which the measured stats now read, so a commit touching only station code refreshes the
    dossier's numbers at the next six-hourly scheduled build, not on push; named here for steward
    (`pyforge-steward:CAP-168`), no edit made.
  - **Gates (2026-10-15, on `a680b61d54` plus this change).** The Pages, parity, 43.6, zero-origin, validator, imports,
    site-URL, build, flag-state, golden and emit test files -- exit 0, 403 passed, none skipped; the herald suite --
    exit 0, 2193 passed, 5 skipped; the steward suite -- exit 0, 2813 passed, 2 skipped; `lint-types` -- exit 0;
    `pages-check` with both flags off, with both on and the 42.1 and 43.6 fixtures under `GITHUB_SHA` / `GITHUB_RUN_ID`
    (fixtures removed after), and on the CAP-56 host -- exit 0 each.
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
