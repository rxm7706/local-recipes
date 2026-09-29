---
title: 'PyForge Marshal poster rebuilt to the standard from its ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: b5fe5e46fccc229038514b13140fe1c90aa658c4
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** `presentations/pyforge-marshal/project/PyForge Marshal Infographic standalone.html`
was the family's first six-act poster (91,340 B / 19 sections / 6 acts / 3 SVG, rebuilt
2026-07-31) but every stat it printed was a July claim — `bmad-method 6.10.0`, `bmad-loop 0.9.0`,
"128/333 fleet-wide", "Marshal Epic 1 · 10/10", per-station chips `4/27 · 4/48 · 5/18 · 2/13 ·
3/26 · 57/57 · 43/43`, "785 fast tests", and a stack table of eight module versions with no
source. `deck-facts pyforge-marshal --check` reported 18 unmarked tokens and `facts 3/21`.
Meanwhile Epics 2–36 shipped, the CLI grew to 52 verbs (dispatch, drain, land, the seed, the
token economy), and the run-state publisher Dream was seeded.

**Approach:** Keep the arc and the 19-section order; re-derive every count, version, status and
date from `presentations/pyforge-marshal/facts.yaml` (refreshed on the branch point, once with
`--with-tests` to mint `tests_collected`), wrapping each as `<span data-fact="<row>">literal</span>`
where the literal is the row's `value` or a `shown_as` string. Refresh the narrative to the live
fleet (dispatch / land / drain / token economy / run-state publisher), raise the poster to the
standard's floors (added a fourth inline SVG — the dispatch→land flow — and a sixth table — the
per-station proof table), keep the page self-contained (Modernist tokens inlined, no `<x-dc>`,
no `support.js`, no scripts, no raster, Google Fonts the only remote resource), render headless
and review the PNG, record the README ledger entry.

## Boundaries & Constraints

**Always:**
- Facts come only from `facts.yaml` rows or the tracked station sources named in the story;
  never a prior poster, never memory. A fact with no row is dropped, not guessed.
- Bare integers and status words that are facts are marked too (the sweep does not see them).
- Versions print only from rows (`bmad_core_version`, `bmad_loop_version`, `cfe_skill_version`,
  `package_version`); two-part versions are never printed.
- Dates print only from `dream_log_*`, `tree_commit_date`, `poster_last_commit_date`.
- Other stations' progress prints only from `<station>_stories_done_total` /
  `<station>_epics_done_total`.
- Only this deck's folder plus this story spec change; physical paths; no `bmad-switch`.

**Never:**
- Never hand-edit `facts.yaml`; never restrict size at authoring time; never edit the Spec
  folder, `pixi.toml`, `docs/`, the sprint ledgers or `scripts/.spec-surface-baseline.json`.
- Never push to Design in this slice (etag `PENDING-PUSH`, operator pushes after review).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Facts check | `deck-facts pyforge-marshal --check` | `0 unmarked, 0 mismatch, 0 drifted, 0 unshown` | `tests_collected` reports `unsourced` on a check run without `--with-tests` — expected, advisory |
| Floors | `stat`, `<section`, `ACT I..VI`, `<svg`, `<table` counts | ≥ 90 KB, ≥ 18 numbered sections, exactly 6 acts, ≥ 3 SVG, ≥ 3 tables | a floor miss means the poster is not marked current |
| Render | Playwright Chromium, 1240 px, full page | PNG with no clipped / overlapping / blank region; page height recorded | fix and re-render (two defects found and fixed: inline-flex tag spacing, an over-long SVG caption) |
| Stack table module versions | BMB / TEA / CIS / SKF / pyforge-core | version column shows `—` | no row → not printed |
| Old numerals with no row | "10 detectors", "51 skills", "8 concurrent homes", "785 tests" | dropped or reworded without a numeral; tests replaced by the `tests_collected` row | — |
| Re-derivation | tracked ledger moves | the advisory check names this poster and the stale row | exit 0 always |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-implemented 2026-09-13 in worktree `lr-wa-marshal` on branch
`herald/20-6-pyforge-marshal-poster` from `origin/main` `b5fe5e46fc`. Facts refreshed with
`pixi run -e local-recipes deck-facts pyforge-marshal --with-tests` (48 rows). Poster authored
repo-side in four parts and assembled; checked, measured, rendered, reviewed as eight 2100 px
slices; two render defects fixed and re-verified; README ledger appended.

**Acceptance Criteria:**
- `deck-facts pyforge-marshal --check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unshown`
  (achieved: `facts 128/128`, the single `unsourced` is the `--with-tests`-only row).
- Floors met: 112,843 B ≥ 90,000 · 19 numbered sections ≥ 18 · 6 acts · 4 SVG ≥ 3 · 6 tables ≥ 3 ·
  eight full cast cards · creed band close.
- Self-contained: no `<x-dc>`, no `support.js`, no `<script>`, no `<img>`; only the Google Fonts
  `<link>` is remote.
- Headless render at 1240 px: page 16,427 px, reviewed, no clipped or blank region.
- README carries `## Ledger — 2026-09-13 standard rebuild (Story 20.6)` with the measured values,
  `PENDING-PUSH` etag, render date + height, and "standalone ahead".
- PR touches only `presentations/pyforge-marshal/**` and this spec, carries `maintenance`.

## Auto Run Result

**Summary:** Poster re-derived from its ledger to the standard. Measured: **112,843 B · 19 sections
(21 `<section` incl. doctrine + creed) · 6 acts · 4 SVG · 6 tables · facts 128/128 · page 16,427 px**.
`--check` summary: `pyforge-marshal: 0 unmarked, 0 mismatch, 0 drifted, 1 unsourced, 0 unshown;
facts 128/128` (`unsourced` = `tests_collected`, derived only under `--with-tests`).

**Ledger sequencing:** `poster_last_commit_date` is *this* poster's own last commit, so it was
written as the landing date and `facts.yaml` was re-derived (`--with-tests`) on the clean tree of
the poster's commit and landed as a follow-up commit — the 20.2 convention (each sibling ledger's
`tree:` is its parent commit). The prior rebuild's date is cited through `dream_log_2026-07-31`.

**Dropped for lack of a fact row:** per-module versions of bmad-builder, TEA, CIS, skill-forge,
pyforge-core / pyforge-testing-kit (column shows `—`); the "10 detectors", "51 skills", "16 skf
skills", "16 mc-* skills", "21 labs skills" counts; "8 concurrent homes" (now "one home per
station"); "785 fast tests + 8 slow" (replaced by `tests_collected` 7932); `bmad-dashboard`,
`bmad-manticore`, `bmad-labs-skills`, `bmad-utility-skills`, `bmad-module-template` rows (no
tracked source verified them installed at this version; manticore stays a prose mention from the
README). The BMAD-team card swaps the retired Paige (tech-writer) for Murat (TEA), per the installed
skill set.

**Verification:** `deck-facts --check` as above; floor script over the file; Playwright render +
eight-slice visual review (defects fixed: `.tag` `inline-flex` → `inline-block` restored the
whitespace around marked spans; two SVG captions shortened to fit their boxes);
`spec-surface-check` run before commit (verdict recorded in the PR body).
