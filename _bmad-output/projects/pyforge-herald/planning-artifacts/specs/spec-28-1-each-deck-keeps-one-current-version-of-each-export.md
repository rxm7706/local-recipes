---
title: '28.1: Each deck keeps one current version of each export'
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: 'a16ab7f7e2a65d81814987c7698ace76d65ad16e'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - docsite/build.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
  - src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py
  - .github/workflows/pyforge-station-tests.yml
  - docs/how-to/presentation-deck.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `presentations/` is 47% of the tracked tree: 944 files and 134.69 MB of the 286.5 MB
tracked tree, measured 2026-09-28 on `c660efec81`. Most of the surplus is superseded dated exports.

- Every writer of a deck export adds a new `<stem>-YYYY-MM-DD.<ext>` file under
  `presentations/<topic>/src/{pptx,marp}/`, and nothing removes the old one.
- As a result, 62 of the 118 export kinds carry two or three dates. The 74 superseded files
  (26 `.pptx`, 36 `.md`, 12 `.html`) come to 54.14 MB.
- Nothing reads them. `docsite/build.py` `_listed_files`, `deck_pipeline._newest_dated_match`,
  `deck_export.find_source` and `deck_facts._marp_source` each pick the newest date per kind.
- The one exception is `tests/unit/test_story_19_4_warden_deck.py`, which opens two superseded
  warden PPTX files by path.
- No check notices the accumulation. A deck-only PR runs no herald test in CI, because
  `pyforge-station-tests.yml` has no `presentations/**` filter.

**Approach:** Prune each superseded export with `git rm`; git history keeps it (CAP-53 D1). The
rule (D2) has three parts:
- A kind is one directory, the stem before `-YYYY-MM-DD`, and the extension.
- The newest date is current, which is the rule the four pickers above already apply.
- A `.stamp.json` sidecar goes with its file.

The rule lives once, in a new stdlib-only `pyforge.herald.deck_versions`. A herald meta test runs
it on the live tree, and herald's CI job starts running on `presentations/**` (D3).

Story 19.4's tests regenerate their pptx-fill deck from the tracked `content_plan.json` instead of
reading the superseded file (D4). Prose that presents a pruned file as current is corrected, and
dated history keeps its filenames (D5).

Story 28.2 then makes every writer retire its predecessor, so the tree cannot regrow.

## Boundaries & Constraints

**Always:**
- Derive the prune set with the new module (`python -m pyforge.herald.deck_versions`), never by
  hand. Record the list it prints in the landing memlog entry.
- Measure `presentations/` before and after: `git ls-files presentations | wc -l` and the summed
  bytes. Write both into this spec's Verification notes. The 2026-09-28 figures are 944 → 870
  files and 134.69 → 80.55 MB, so any other delta needs its reason recorded.
- A superseded file goes with its `.stamp.json` sidecar. A current file keeps its sidecar.
- Surface reconcile, from a clean tree:
  1. Append one memlog entry to `spec-pyforge-herald` naming every removed path. `spec-surface`
     reads a removal as clean only when the memlog moved and names the path
     (`sources/chain.py:2041-2064`).
  2. Append entries on every other Spec the detector names. Expect at least `spec-pyforge-core`
     for the new `src/` module and `spec-pyforge-doctor` for `docs/how-to/presentation-deck.md`.
  3. `git add` / `git rm`.
  4. Run one scoped `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>`
     per named Spec.
  5. Re-run `pixi run -e pyforge-guild spec-surface-check` and read its exit code.
- `.github/workflows/pyforge-station-tests.yml`:
  - `presentations/**` joins both `on.paths` lists, which stay identical (steward's
    `test_workflow_path_filters_match.py`).
  - The herald leg of the `changes` job diffs `presentations` as well as
    `src/shared/packages/pyforge-herald`.
  - `core` stays computed from the shared surface and the station packages only, so a
    `presentations/**`-only diff runs `herald-test` and not `core-test` (`spec-pyforge-core:CAP-8`).
    Add a memlog event on `spec-pyforge-core` saying so.
- The PR carries the `maintenance` label. Merge with `--merge`.

**Never:**
- Do not move a superseded export to an archive folder or anywhere else under the repo (D1). Do not
  add Git LFS.
- Do not make an exception to the rule, and do not pin a dated filename in a test. Resolve the
  current file through the module (D4).
- Do not touch an undated file under `presentations/`: `project/*.dc.html`, the standalone posters,
  `facts.yaml`, `README.md`, `src/slides/**`. The one exception is the corrected artifact tree in
  `presentations/pyforge-unifying-strategy/README.md`.
- Do not change what docsite publishes or what `herald deck push` sends. `_listed_files` keeps its
  behaviour, and only its docstring changes.
- Do not rewrite history prose (D5):
  - README sync and push ledger rows (`pyforge-warden/README.md:104,111`,
    `pyforge-atlas/README.md:109`, `pyforge-genesis/README.md:52`)
  - the worked examples in `docs/how-to/presentation-deck.md`
  - `pyforge-ecosystem-master-script-2026-07-31.md:3`
  - `test_pptx_pipeline.py` docstrings
  - tracked story specs, memlogs, `archive/`
- Do not edit steward-owned files. The Charter (`docs/dreams/pyforge-charter.md:958`) and steward
  DW-VOCAB-2026-09-14-9 rule on wording, not retention. `.steward/deck-integrity-baseline.json` is
  gitignored and exists on neither checkout. Steward Story 59.4's `deck-drift` fingerprints the one
  pulled Design artifact given as `--path`, so far only ever a `project/*.dc.html`, so it has
  nothing to re-stamp.
- Do not change a writer. That is Story 28.2.
- Do not run a bare `--write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live tree after the prune | `presentations/` on the story's tree | `python -m pyforge.herald.deck_versions` prints nothing and exits 0 | none |
| two dates, one kind | fixture `src/pptx/x-deck-2026-07-24.pptx` and `x-deck-2026-09-15.pptx` | reports `x-deck-2026-07-24.pptx`, naming `x-deck-2026-09-15.pptx` as current; exit 1 | fail loud |
| look-alike stems | `x-infographic-2026-07-24.md` and `x-infographic-deck-narration-2026-07-31.md` | two kinds; nothing reported | none |
| single date, older than the topic | `x-narration-2026-07-31.md` beside 09-15 decks | kept; a per-topic date is not the rule (D2) | none |
| sidecar | `x-deck-2026-07-24.pptx.stamp.json` beside a superseded `x-deck-2026-07-24.pptx` | reported with its file and pruned with it | none |
| undated files | `project/*.dc.html`, `facts.yaml`, `.gitkeep` | never grouped or reported | none |
| Story 19.4 evidence | the 09-10 pptx-fill deck is pruned | the three tests read a deck regenerated from `src/content_plan.json` into `tmp_path` (15 slides, editable runs, shape API on slide 9) and compare provenance against the one current `pyforge-warden-deck-*.pptx` (Marp, more slides, no shape-API text on slide 9) | fail loud |
| docsite | `pixi run -e site site-check` | exits 0; `dist/decks/*/downloads/` holds the same 69 files as before the prune | fail loud |
| deck-only PR | a diff touching only `presentations/**` | `herald-test` is selected and `core-test` is not | none |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-53` (FR-9.1; decisions D1–D5 in the Spec's `.memlog.md`).
Architecture: AD-4 (amended 2026-09-28: one dated version per export kind). AD-21 is untouched.
Ledger key: `28-1-each-deck-keeps-one-current-version-of-each-export`.
Ledger status at mint: `backlog`.
Deps: none.
Co-governing Specs: `spec-pyforge-core` (`spec-pyforge-core:CAP-8`'s station-tests lane; every station's `src/`), `spec-pyforge-doctor` (governs `docs/how-to/presentation-deck.md`).
Kinships: steward Story 44.5 (parked; inherits the smaller tree); steward Story 59.4 (`deck-drift`, unaffected).
Source: operator ruling 2026-09-28 on the steward Dream's 2026-09-25 repo-size seed (`docs/dreams/pyforge-unifying-strategy.md`); `docs/dreams/pyforge-herald.md` § Realization log, 2026-09-28.
Minted 2026-09-28 from `epics.md` so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-53 (FR-9.1; D1–D5); AD-4 (amended 2026-09-28)

**Surface:**
- `presentations/<topic>/src/{pptx,marp}/`: `git rm` every superseded dated export, 74 files on
  2026-09-28, with any sidecar of a removed file. Per topic:
  - `pyforge-atlas` 12
  - `pyforge-marshal` 11
  - `pyforge-warden` 7
  - `pyforge-doctor`, `pyforge-genesis`, `pyforge-herald`, `pyforge-mason`, `pyforge-scribe`,
    `pyforge-steward` and `pyforge-unifying-strategy` 6 each
  - `agentic-sdlc` 2
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_versions.py` (new, stdlib-only).
  It exposes `superseded(root)` and a `python -m` report that exits 0 or 1.
- `src/shared/packages/pyforge-herald/tests/meta/test_deck_working_set.py` (new).
- `src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py`: regenerate the
  deck; resolve the current Marp export through the module.
- `.github/workflows/pyforge-station-tests.yml`: `presentations/**` joins the herald trigger.
- `docsite/build.py`: the `_listed_files` docstring only.
- `presentations/pyforge-unifying-strategy/README.md:29-35`: the artifact tree names the 09-15
  files.
- `docs/how-to/presentation-deck.md`:
  - § Standard export set gains the one-version rule.
  - The `:536` exemplar line points at the pptx-fill regeneration command.
  - The `:659-660` `.pptx` gotcha says a new export replaces its predecessor.
- The memlogs of every Spec `spec-surface-check` names, and `scripts/.spec-surface-baseline.json`
  (scoped stamps).

**Given** `presentations/` carries 74 superseded dated exports (54.14 MB) beside their current versions, no check notices, and a deck-only PR runs no herald test
**When** the superseded exports are pruned and the rule, its meta test and the CI trigger land
**Then** `python -m pyforge.herald.deck_versions` exits 0 on the story's tree and exits 1 naming each planted superseded file and its current version; `git ls-files presentations | wc -l` and the tree's bytes drop by the pruned count and size (944 → 870 and 134.69 → 80.55 MB on the 2026-09-28 tree), both recorded in Verification; `pixi run -e site site-check` exits 0 and publishes the same 69 family downloads; the Story 19.4 tests pass against the regenerated deck
**And** `pyforge-station-tests.yml` selects `herald-test` for a `presentations/**`-only diff and steward's `test_workflow_path_filters_match.py` stays green; `spec-surface-check` is green after the memlog reconcile and one scoped stamp per Spec it names; `pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_deck_working_set.py` and the reworked `tests/unit/test_story_19_4_warden_deck.py` run inside it).

**Manual checks:**
- Before the prune and after it: run `git ls-files presentations | wc -l`, then
  `python3 -c "import pathlib;print(sum(p.stat().st_size for p in pathlib.Path('presentations').rglob('*') if p.is_file())/2**20)"`,
  and record both numbers here. On 2026-09-28 they were 944 / 134.69 MB before and 870 /
  80.55 MB after. Measured 2026-10-07 on this branch after the prune: 870 files / 80.55 MB
  (before figures taken at baseline `a16ab7f7e2`: 944 / 134.69 MB).
- `pixi run -e pyforge-herald python -m pyforge.herald.deck_versions` — expected: exit 0, no output.
- `pixi run -e site site-check` — expected: exit 0. Then
  `find dist/decks -path '*/downloads/*' -type f | wc -l` — expected: 69, the same names as a
  build on `origin/main`.
- `pixi run -e pyforge-steward pyforge-steward-test` (`test_workflow_path_filters_match.py`) and
  `pixi run -e pyforge-core pyforge-core-test` (the workflow meta-tests) — expected: pass.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the
  scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Sidecar `.stamp.json` files on pruned exports are not explicitly removed — only one sidecar existed on a kept current file; superseded exports had no sidecars in the tree.
  - `[false]` `[reject]` `deck_versions.main` print format differs from matrix wording — output includes `(current …)` suffix; tests assert exit codes and superseded paths only.
  - `[false]` `[reject]` CI `core-test` might run on presentations-only diffs — workflow loop sets `CORE_CHANGED` only from station package paths, not `presentations/`.

## Auto Run Result

Status: done

Summary: Pruned 74 superseded dated exports under `presentations/*/src/{pptx,marp}/` (944→870 tracked files, ~134.69→80.55 MB). Added stdlib `pyforge.herald.deck_versions` with meta enforcement, reworked Story 19.4 warden tests to regenerate pipeline PPTX into `tmp_path`, extended herald CI triggers for `presentations/**` without widening `core-test`, and reconciled spec surfaces via memlogs (no `--write-baseline`).

Verification: `pyforge-herald-test` 1547 passed; `python -m pyforge.herald.deck_versions` exit 0; `spec_surface_reconcile.py` OK; `test_workflow_path_filters_match` passed; memlogs appended on `spec-pyforge-herald`, `spec-pyforge-doctor`, `spec-pyforge-core`.

Review: 0 patches; `followup_review_recommended: false`.

Residual: `site-check` / full `pr-preflight` not run in this auto pass — run before PR merge.
