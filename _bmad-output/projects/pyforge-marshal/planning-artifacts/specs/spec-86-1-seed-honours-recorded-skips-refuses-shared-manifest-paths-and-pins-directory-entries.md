---
title: "86.1: Seed honours recorded skips, refuses shared manifest paths, and pins directory entries"
type: 'fix'
created: '2026-10-03'
status: 'in-review'
review_loop_iteration: 0
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
