---
title: "86.1: Seed honours recorded skips, refuses shared manifest paths, and pins directory entries"
type: 'fix'
created: '2026-10-03'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred:
  - summary: >-
      A directory entry's create-if-missing half is pinned but not materialized: an ABSENT trailing-`/` entry still
      gets an ordinary creation action, and every commit dispatcher (adopt, init, update) treats it as a file.
    evidence: |-
      Story 86.1 pinned the semantics (`ManifestEntry.is_directory`, `model.artifact.DIRECTORY_BEHAVIOR`) and stopped
      every path that touched an EXISTING directory (update's wholesale pass, rung 6 in adopt and update, adopt's
      first claim). Creating an absent one is adopt's documented known limitation (2): `fs` has no guarded
      directory-creation primitive, and the commit dispatchers look for staged file bytes at the target, so applying
      such an action fails rather than creating the directory (not run; read from `_staged_bytes_for` in
      verbs/adopt.py and verbs/update.py). A fix needs a never-write-guarded
      mkdir in `fs`, a directory branch in the three commit dispatchers, and apply rollback for a created directory
      (DW-10-3-3 tracks that a rolled-back apply never removes a directory it created) -- a multi-module change
      outside this story's three rulings.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py:176
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three seed rules the operator ruled to fix (2026-10-03): adopt writes `state.skips` but neither adopt nor update reads it back (PRD FR-87 says recorded skips are honoured); two non-`referenced` manifest entries may declare the same path with overlapping `applies_to`/`since`-`until` windows; and a trailing-`/` directory entry has no defined semantics where its subtree holds entries of other classes (for example `dreams-dir` over never-write `docs/dreams/*.md`).

**Approach:** Apply the recorded `state.skips` with the run's `--skip` patterns on adopt and update; make `load_manifest` refuse two non-`referenced` entries sharing a path with overlapping windows; pin a directory entry as create-if-missing whose child entries' classes win beneath it.

Ledger key: `86-1-seed-honours-recorded-skips-refuses-shared-manifest-paths-and-pins-directory-entries`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an artifact skipped at adopt When a later update or re-adopt runs Then it stays skipped
- Given two non-referenced entries with the same path and overlapping windows When the manifest loads Then it refuses naming both ids; the shipped manifest still loads clean
- Given `dreams-dir` and `project-subtree` When update runs Then their starter files and never-write children are left as their own classes dictate
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-11-4`, `DW-FU-7-4-4`, `DW-FU-7-5-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep `referenced` entries (path `n/a`) out of the uniqueness check. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never relax the never-write guard.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-11-4` — seed adopt and seed update apply the recorded state.skips together with the run's --skip patterns (apply_skips and managed_after_skips), pinned by a test where an adopt-time skip survives a later update and re-adopt.
- `DW-FU-7-4-4` — load_manifest refuses two non-referenced entries with the same path whose applies_to and since/until windows overlap; add tests for the AGENTS.md double-owner repro and for the shipped manifest loading clean.
- `DW-FU-7-5-2` — Pin directory-entry semantics (a trailing-/ entry is create-if-missing; child entries' classes win beneath it) in artifact.py/manifest.py and add an update test proving dreams-dir and project-subtree leave starter-dream and project-config untouched.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-1-seed-honours-recorded-skips-refuses-shared-manifest-paths-and-pins-directory-entries`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-04 — Build complete (hand-built, branch `land/pyforge-marshal-86-1`); ready for an independent review.
  Each AC carries a test that fails with its rule removed (13 mutants, all killed, run on a scratch copy of the
  package). The three deferred-work rows are closed in the ledger with `resolution:` and `verified:` lines.
- 2026-10-04 — Landing review: **SEND BACK** (one MEDIUM, three LOW; the reviewer's probes and a 16-mutant run on a
  scratch copy of the package, two of them surviving). Fixed on the same branch:
  - **MEDIUM-1 — AC1's update-side rung 6 was unpinned.** Mutant M3u (update hands `skip`, not `skip_patterns`, to
    `managed_after_skips`, `seed/verbs/update.py:1362`) survived: no update test had a record with no update action
    whose path only a *recorded* pattern names. Fix: `test_a_recorded_skip_keeps_a_record_with_no_update_action_away_from_rung_6`
    (`tests/unit/test_seed_verbs_update.py`) — recorded `skips=("S.md",)`, a `copied-seeded` record at `S.md` with a
    stale `body_sha`, the file hand-edited; `run_update(run=True)` must not raise. Under M3u it refuses
    `managed-content-modified`; the reviewer's `probe_m3u.py` reports both of its cases OK on the fixed tree and
    REFUSED under M3u.
  - **LOW-2 — the reversed overlap boundary was untested.** Mutant M7 (`first.since <= second.until`,
    `seed/model/manifest.py`) survived. Fix: `test_disjoint_windows_may_share_a_path[successor-declared-first]`
    (`since: "2.0.0"` declared before `until: "2.0.0"`).
  - **LOW-3 — the one-owner rule compared raw path strings,** so `./AGENTS.md` beside `AGENTS.md`, or `docs//x`
    beside `docs/x`, loaded as two owners of one file. Fix: `_require_repo_relative_path` (`seed/model/manifest.py`)
    now refuses a `.` segment and an empty segment in either separator dialect, keeping the single trailing `/` of a
    directory entry; `load_manifest` prefixes the entry id. Tests:
    `test_a_dot_or_empty_path_segment_raises_manifest_error_naming_the_entry_id` (7 cases),
    `test_a_second_spelling_of_an_owned_path_cannot_reach_the_one_owner_rule` (2 cases),
    `test_dot_names_and_a_single_trailing_slash_keep_loading`. No shipped manifest path carries either form.
  - **LOW-4 — a behavioural leg was dropped** from adopt's
    `test_skip_of_a_hand_edit_in_a_run_that_applies_something_else_keeps_the_state_record`. Restored: with
    `state.skips` cleared, the same re-adopt refuses `managed-content-modified` naming `a:`.
  - **DW-marshal-86-1** (ledger evidence extended): masked today by adopt's known limitation (1) — a real apply
    against the packaged manifest fails first at the Copier boundary (`TemplateBoundaryError`,
    `seed/engine/copier.py:336-337`); owner DW-10-3-3 (guarded mkdir plus directory rollback).
  - **Mutants after the fixes:** 19 of 19 killed — the reviewer's 16 (M1–M14 with M3a/M3u and M7/M7b; M3u and M7
    now killed by the tests above) plus three for LOW-3 (M15 `.` segment allowed, M16 empty segment allowed, M17
    trailing `/` not exempted).
  - **Note for Story 70.1:** the one-owner rule runs at load on *unrendered* paths, so two entries that differ only
    in `{{ slug }}` and render to one path are not compared. 70.1's renderer (`render_slug_paths`) must re-run
    `_refuse_shared_paths` on the rendered entries, or validate the slug so no rendering can collide, and switch
    the test helper `_shipped_entries_for_slug` (`tests/unit/test_seed_verbs_update.py`) from its hand-rolled
    `str.replace` to that renderer.
- 2026-10-04, post-landing re-review of the send-back fix (a22a7dd4c3): it found one regression that had reached main with #1818. The LOW-3 one-spelling refusal broke `tests/unit/test_seed_verbs_check.py::test_referenced_entries_are_never_reported_absent`, whose `referenced` entry path is a URL (`//` reads as an empty segment). Hotfix: `_require_repo_relative_path(..., one_spelling=...)` applies the `.` / empty-segment refusal only to non-`referenced` entries, the same exclusion the one-owner rule makes; the absolute and `..` refusals still apply to every entry. Tests: `test_a_referenced_entry_keeps_any_spelling_of_its_path` (url, dot, empty) and `test_a_referenced_entry_still_refuses_a_parent_segment`. Every `test_seed_*` file passes (1936). The rest of the re-review held: MEDIUM-1 and LOW-2/3/4 fixed, mutants M3u, M7 and M15–M17 killed.
