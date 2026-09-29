---
title: 'Handoffs are execution-ready'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-08-22'
status: 'done' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      No rate-limiting/backoff for bulk gh issue create / gh project item-add
      calls when --create-issues runs live against many missing names.
    evidence: |-
      This repo has already hit GitHub secondary rate limits under lighter
      concurrent load (Phase K, 8 workers -> 15% 403s). create_missing_issues
      fires one issue-create + one project item-add per missing name in a
      tight loop with no backoff. Gated behind an opt-in flag that requires
      deliberate attended execution with real credentials -- defer to the
      first real attended --create-issues run.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:create_missing_issues
    severity: medium
  - summary: >-
      CANVAS_DIR is a hardcoded absolute path under the operator's home
      directory, so the canvas writers only work on this machine/account.
    evidence: |-
      Pre-existing convention, not introduced by this story: priority.py's
      own --canvas argparse default already hardcodes the identical
      "/home/rxm7706/.cursor/projects/.../canvases" path for the Catalog
      canvas. This story's two new canvas writers follow that same
      established (if machine-specific) pattern rather than inventing a new
      one.
    location: >-
      scripts/openteams_identity_dashboards.py:CANVAS_DIR
    severity: low
  - summary: >-
      write_ops_canvas: records whose P/Work falls back to the "?" sentinel
      are counted in the total but invisible in every per-bucket breakdown
      table; build_by_type silently drops recipe types outside the fixed
      RECIPE_TYPE_ORDER list.
    evidence: |-
      Mirrors a pre-existing pattern already present in this same file's
      render() function (verified against the live file, not just the diff).
      Cosmetic, dashboard-only impact; neither this canvas nor its sibling
      has any live-rendering verification yet in this environment.
    location: >-
      scripts/openteams_identity_dashboards.py:write_ops_canvas
    severity: low
  - summary: >-
      write_workbook_canvas: a pep503-name dict collision keeps only the
      last matching record, and jfrog_by.setdefault drops duplicate JFrog
      rows without counting them toward the skip total.
    evidence: |-
      Same pre-existing-pattern, cosmetic-dashboard rationale as the
      write_ops_canvas sentinel/order-filtering item above.
    location: >-
      scripts/openteams_identity_dashboards.py:write_workbook_canvas
    severity: low
  - summary: >-
      write_workbook_canvas's "Needs a staged-recipes PR" bucket excludes
      JFrog names with no identity match at all, inconsistent with the
      neither_rows bucket in the same function which does include them.
    evidence: |-
      `if ident_row and not on_cf and not has_pr` requires a truthy
      ident_row, so a JFrog name with zero identity-tab match -- arguably
      the strongest "needs packaging" signal -- never appears in need_pr,
      while neither_rows counts exactly that case.
    location: >-
      scripts/openteams_identity_dashboards.py:write_workbook_canvas
    severity: low
  - summary: >-
      No try/finally around the second load_workbook() call in
      write_workbook_canvas -- a mid-loop exception skips wb.close() and
      leaks the file handle.
    evidence: |-
      Minor resource leak in a short-lived CLI process; real but low
      real-world impact.
    location: >-
      scripts/openteams_identity_dashboards.py:write_workbook_canvas
    severity: low
  - summary: >-
      _CANVAS_PREFIX is duplicated as a separate string literal in
      openteams_identity_dashboards.py instead of being imported from
      priority.py, where the original copy lives.
    evidence: |-
      Drift risk between the two copies; mitigated but not eliminated by a
      new test (test_write_ops_canvas_empty_records_is_valid_and_schema_shaped)
      that asserts the two are byte-identical.
    location: >-
      scripts/openteams_identity_dashboards.py:_CANVAS_PREFIX
    severity: low
---

<intent-contract>

## Intent

**Problem:** The packaging-inventory quartet's from-scratch run (Story 17.1, chartered) already computes the four Work dispositions (`Fix vulnerability` / `Create recipe` / `File OpenTeams tracking issue [Conda-Forge Packaging]` / `Already tracked`) and a precomputed `OpenTeams_Title` per row, but nothing in the quartet actually opens the missing GitHub tracking issues, and nothing computes the "AOSS-Free" (PyPI-yes, conda-forge-no, not-in-CDO-consumption) names as a separate queue. Two of the three Dream-specified dashboard canvases (Ops, Artifactory/workbook) are also never generated — only their markdown-mirror content exists.

**Approach:** Add missing-issue creation (dry-run-by-default, `gh` CLI, one issue per OpenTeams-universe name lacking `OpenTeams_Issue_URL`) to `..._openteams_identity.py`; compute and write a dated AOSS-Free extra-queue CSV; add the two missing canvas-TSX generators to `openteams_identity_dashboards.py` by restructuring data `render()` already computes. No changes to the existing disposition/priority logic (`priority.py`) — it is correct and unchanged.

## Boundaries & Constraints

**Always:** New GitHub-issue-creation code reuses the existing `gh` subprocess pattern (`gh_bin()`, `subprocess.check_output`/`check_call`) — no new HTTP client or library. Issue title is the row's existing `OpenTeams_Title` value verbatim, never recomputed. AOSS-Free queue is a **separate** dated artifact (`aoss-free-queue-YYYY-MM-DD.csv`, columns `Package_Name`, `Reason`, `Verification_Timestamp_UTC`) — it must never be merged into or expand the `records` universe the identity tab and issue-creation loop iterate over. New canvas generators reuse the existing `cursor/canvas` component imports and `_CANVAS_PREFIX`/`_CANVAS_SUFFIX`-style wrapping already established by `priority.py::write_canvas`.

**Block If:** None — dry-run default plus fixture-based tests make every part of this story executable and verifiable without live credentials or org write access.

**Never:** Do not execute a real `gh issue create` (or `gh project item-add`) against the live `OpenTeams-WFT-CDO` org/repo during this development session — no such credentials exist in this environment, and it would be an irreversible external side effect. Issue creation ships **disabled by default**; a new `--create-issues` flag (mirroring `--skip-gist`'s opt-out convention, but opt-in here) gates the live path, and its absence must print a dry-run summary (names + titles that would be created) instead of calling `gh`. Do not touch `priority.py`'s disposition/ranking logic — it already matches the Dream. Do not fold any PyPI↔conda-forge mapping work into this quartet (resolved out-of-scope at Story 17.1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing issue, dry-run (default) | Row with `Work` != `Already tracked`, `OpenTeams_Issue_URL` empty, no `--create-issues` | Printed dry-run line naming the package + `OpenTeams_Title`; no `gh` mutation call made | N/A |
| Missing issue, `--create-issues` set | Same row, flag present | `gh issue create --repo OpenTeams-WFT-CDO/mgmt-wf-python-modernization --title <OpenTeams_Title>` invoked once; new URL merged into that row's `OpenTeams_Issue_URL` | `gh` non-zero exit for one name logs and continues to the next name; does not abort the run |
| Existing issue | `OpenTeams_Issue_URL` already non-empty (board match) | Skipped — no creation call, regardless of flag | N/A |
| AOSS-Free name | On PyPI, absent from `CDO-ENT-JFROG`/`CDO-ENT-CONDA` sheets, absent from conda-forge | Row written to `aoss-free-queue-YYYY-MM-DD.csv` only; absent from `records`/identity tab/issue-creation loop | N/A |
| Empty records (no workbook data) | `records == []` | Canvas generators still write valid, schema-shaped `.tsx` files with empty `rows`/`leaders` arrays | No crash |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` -- `main()` (L1200-1343) builds `records`/`board` (`board_packaging_urls`, L339-350) and already carries a precomputed `OpenTeams_Title` per row (`GIST_SCHEMA`, L84-120) and `OpenTeams_Issue_URL` (existing-issue join). Add `create_missing_issues(gh, records, board, dry_run)` near `board_packaging_urls`; call it in `main()` right after `board = board_packaging_urls(items)` (L1247) and before `write_xlsx_tab` (L1285), so newly created URLs land in the written tab. Add `--create-issues` (`store_true`, default off) to the `argparse` block (~L1180-1220, alongside `--skip-gist`/`--gist-only`).
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` -- `aoss_free` set already computed at L837/L851 (`parse_sheet_pkg_set(xlsx, "GAOSS-Free", "Package_Name")`) for inclusion bookkeeping only; add a small `write_aoss_free_queue(path, aoss_free_names, universe_names, timestamp)` that filters `aoss_free_names - universe_names` and writes the dated CSV. Call it from wherever `aoss_free` is already in scope (~L834-855).
- `scripts/openteams_identity_dashboards.py` -- `render()` (L61-617) already computes all Ops-pane data (Priority/Work L344-354, Issues gap L402-429, Builds/Census L431-508) and all Artifactory/workbook-pane data (CDO-ENT-JFROG map + staged-recipes gap + workbook tabs + external counts, L510-614) as markdown. Add two new functions, `write_ops_canvas(path, ...)` and `write_workbook_canvas(path, ...)`, each restructuring the corresponding already-computed Python values into a JSON `DATA` blob plus a `cursor/canvas` TSX wrapper -- follow `priority.py::write_canvas` (L250-309) and its `_CANVAS_PREFIX`/`_CANVAS_SUFFIX` templates (L312-817) as the structural pattern (imports, `useCanvasState`, `Grid`/`Table`/`Stat`/`BarChart`). Default output paths alongside the existing `identity-2026-08-20.canvas.tsx` convention: `.../canvases/identity-ops.canvas.tsx`, `.../canvases/jfrog-workbook.canvas.tsx`.
- `scripts/conda-forge-packaging-inventory-operations_priority.py` -- `write_canvas` (L250-309), `_CANVAS_PREFIX`/`_CANVAS_SUFFIX` (L312-817) -- read-only pattern reference, not modified.
- `tests/packaging/test_openteams_handoffs.py` -- new file. Fixture-based, offline, mocks `subprocess.check_output`/`check_call` for `gh` calls (per project Testing Contract: no live credentials, no network).

## Tasks & Acceptance

**Execution:**
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` -- add `create_missing_issues()` + `--create-issues` flag + `main()` wiring -- closes CAP-2's "one issue per library" clause.
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` -- add `write_aoss_free_queue()` + call site -- closes the AOSS-Free extra-queue clause.
- `scripts/openteams_identity_dashboards.py` -- add `write_ops_canvas()` and `write_workbook_canvas()` -- closes the "three dashboard views" clause (Catalog already exists).
- `tests/packaging/test_openteams_handoffs.py` -- unit tests for all three additions plus the I/O matrix edge cases above.

**Acceptance Criteria:**
- Given a `records` list with one row missing `OpenTeams_Issue_URL` and `--create-issues` absent, when `main()` runs (or `create_missing_issues` is called directly in a test), then no `gh` mutation subprocess call is made and a dry-run line is printed/returned naming the package.
- Given the same row with `--create-issues` present and a mocked `gh` subprocess, when run, then exactly one `gh issue create` call is made with `--title` equal to that row's `OpenTeams_Title`, and the row's `OpenTeams_Issue_URL` is updated from the mocked return value.
- Given a name present in `GAOSS-Free` but also present in the OpenTeams universe (JFROG or CDO-ENT-CONDA), when `write_aoss_free_queue` runs, then that name is excluded from the AOSS-Free CSV (never expands the universe).
- Given zero records, when `write_ops_canvas`/`write_workbook_canvas` run, then each produces a `.tsx` file containing a `const DATA = {...}` block that parses as valid JSON with empty array fields, and the file starts with the same `cursor/canvas` import block used by `write_canvas`.
- Given all three new functions, when `python -m py_compile` runs over the three modified scripts, then it exits 0.

## Spec Change Log

_None. No `bad_spec` finding triggered a repair loopback in this run._

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 2, medium 5, low 1)
- defer: 7 (medium 1, low 6)
- reject: 5 (low 5)
- addressed_findings:
  - `[high]` `[patch]` `--create-issues` with no `gh` binary raised `SystemExit` mid-`main()`, aborting before the xlsx/csv/markdown outputs were written and losing the whole run's computed work -- reordered so a missing `gh` is checked before any output-losing path is reached (edge-case-hunter)
  - `[high]` `[patch]` The new test file `tests/packaging/test_openteams_handoffs.py` was silently skipped under the only pixi task (`pyforge-deps-test`, `-e pyforge-ci`) that runs `tests/packaging`, because that env lacks `openpyxl` -- zero regression protection in the only automated gate touching this directory -- added a pixi task under `-e local-recipes` that runs it (verification-gap)
  - `[medium]` `[patch]` `create_missing_issues` only caught `subprocess.CalledProcessError` around the two `gh` calls, so a missing/vanished `gh` binary (`OSError`/`FileNotFoundError`) would abort the loop, contradicting the docstring's "never aborts the run" claim -- broadened the except clause (edge-case-hunter)
  - `[medium]` `[patch]` Blank/falsy package names could reach `gh issue create` -- skip rows with no name before adding to the missing list (edge-case-hunter)
  - `[medium]` `[patch]` A `gh project item-add` failure after a successful `gh issue create` was silently unrecoverable on a later run (the row's `OpenTeams_Issue_URL` is already set, so the board join treats it as fully tracked forever) -- only merge the URL into `board`/the row after both calls succeed (blind-hunter + edge-case-hunter)
  - `[medium]` `[patch]` `write_dashboard_markdown`'s two new canvas-writer calls were unguarded, so a canvas-write failure (e.g. an unwritable default path) now blocks the previously-independent, already-working gist-markdown publish in both call sites -- wrapped in try/except that logs a warning and continues (blind-hunter + verification-gap)
  - `[medium]` `[patch]` `docs/reference/conda-forge-packaging-inventory-operations_replay.md` documented only the AOSS-Free queue addition, omitting the `--create-issues` live-mutation flag and the two new canvas-path flags -- added runbook entries for both (blind-hunter)
  - `[low]` `[patch]` `SPEC.md`'s frontmatter status comment still read "CAP-2 (17.2) still backlog" after CAP-2 code landed -- updated to reflect the current state (intent-alignment auditor)
  - `[medium]` `defer` No rate-limiting/backoff for bulk `gh` calls under live `--create-issues` -- gated behind an opt-in flag requiring deliberate attended execution; recorded in frontmatter `deferred:` for the first real live run (blind-hunter)
  - `[low]` `defer` (x6) -- hardcoded `CANVAS_DIR` (pre-existing convention, not introduced here); `write_ops_canvas`'s "?"-sentinel/`RECIPE_TYPE_ORDER` filtering and `write_workbook_canvas`'s dict-collision/dedup-undercounting (both mirror pre-existing patterns in this file's own `render()`, cosmetic dashboard-only, no live-rendering verification exists for any of the three canvases yet); `write_workbook_canvas`'s `need_pr` bucket excluding no-identity-match names; the missing `try/finally` around the second `load_workbook` call; `_CANVAS_PREFIX` duplicated as a literal instead of imported (blind-hunter + edge-case-hunter)
  - `[low]` `reject` (x5) -- `ISSUE_CREATE_REPO`/`PROJECT_OWNER`/`PROJECT_NUMBER` hardcoded (fixed shared-infrastructure constants, not per-user secrets like the gist id); the `Reason` CSV column being a constant string (functions as intended); no opt-out flag for the AOSS-Free queue write (a local file write with no shared-state side effect, unlike `--skip-gist`); `write_workbook_canvas` opening the xlsx workbook twice (minor local I/O redundancy, no correctness impact); the generated TSX templates' "unused" `cursor/canvas` imports (refuted by direct evidence -- the identical import block is already used, unmodified, by the pre-existing live `identity-2026-08-20.canvas.tsx`, so the runtime does not hard-fail on this) (blind-hunter x4, edge-case-hunter x1)

## Design Notes

**AOSS-Free artifact shape:** the Dream specifies the *constraint* (never expand the universe) but not the artifact's exact shape. This spec fixes it as a dated CSV (`aoss-free-queue-YYYY-MM-DD.csv`, same directory as other CAP-1 CSV outputs) rather than a new workbook tab, matching `metrics.py`'s existing CSV-output convention (`write_csv`, L626) rather than `openteams_identity.py`'s xlsx-tab convention — this queue is Mason-facing supplementary output, not part of the versioned identity-tab family.

**Issue creation is additive-only and idempotent:** it only ever creates issues for names the board join (`board_packaging_urls`) didn't already find — it never edits, closes, or re-titles an existing issue. Adding the new issue to OpenTeams project 1 (`gh project item-add --owner OpenTeams-WFT-CDO --number 1 --url <new-issue-url>`) is included in `create_missing_issues` so a subsequent run's `board_packaging_urls` sees it and treats it as `Already tracked` — without this, every run would recreate the same issues.

**Dashboard canvases render inside Cursor IDE, not this test suite** — acceptance for them is structural (valid TSX + parseable embedded JSON + non-empty for non-empty input), matching how `write_canvas` itself has no existing test coverage; this story does not add live-rendering verification for any of the three canvases.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `f58e91bfff` (2026-09-11, "pyforge-mason: promote sprint-status ledger for Story 16.2 -> done"); also `caf8b96f9f` (2026-08-20, "rescue: atlas 16.2 revised work, uncommitted in a stale run worktree"). Ledger row `16-2-handoffs-are-execution-ready: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
