---
title: '82.3: A landing claims only committed promotions, rejects a malformed merge template, and stamps only reconciled drift'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Four landing and ledger writes claim more than they did. Re-verified at HEAD a7cdb91fe4:

- `cli/deploy.py::run_promote`: the copy loop appends each key to `promoted` (`:957`) before the batched
  `vcs.commit_paths` (`:980`); when that raises, the `except VcsCommandError` (`:981-988`) adds an `MRS-DEPLOY-003` but
  removes no key, so `data["promoted"]` and `promoted_count` (`:1091-1092`) publish an uncommitted copy as a durable
  promotion (DW-5-9-2).
- `core/policy.py::_valid_merge_subject_template` (`:1317-1320`) accepts any non-empty `str`; a template without exactly one
  `{key}` composes cleanly, then `core/identity.py::_split_template` (`:224-234`) raises a bare `ValueError` out of
  `marshal land` (`cli/land.py:970`) and `land-story` (`cli/deploy.py:2125`), both unguarded (DW-5-10-1).
- `dispatch_land.py::_reconcile_spec_surface_drift` (`:258`) reads the spec-surface verdict once (`:329`), memlogs and
  scoped-stamps the specs it names (`:521-525`), commits and pushes (`:551-556`), and returns. Doctor's verdict keeps one
  row per path (`pyforge-doctor/src/pyforge/doctor/sources/chain.py:2083-2088`, sorted by rank then spec name, `rows[0]`),
  so for a station `src/` edit only `spec-pyforge-core` is named and the station's own spec stays drifted on `main` until a
  later pass (DW-FU-53-2-3).
- `scripts/spec_surface_check.py --write-baseline --spec NAME` merges `current[name]` (`:233`), every file NAME's surface
  matches, so an unnarrated drifted file under a broad glob is absorbed as reconciled with no trace. The companion half of
  that entry, the unlocked read-modify-write, is already fixed (the flock at `:187-206`) (DW-9-1-1).

**Approach:**

- `run_promote` reports only committed keys under `promoted`; a failed commit's keys are named in its `MRS-DEPLOY-003`
  finding instead.
- `_valid_merge_subject_template` rejects a template without exactly one `{key}`, so composition reports the layer's
  rejected value with `MRS-POLICY-002` (what `_merge_field` already raises for a rejected value, `core/policy.py:2151-2160`)
  and falls back to the default template; no landing path can reach `_split_template`'s `ValueError`.
- The landing reconcile re-reads the verdict after each stamp and reconciles any further spec that names one of the
  branch's own paths, bounded by the number of specs governing those paths; drift on own paths that survives the bound is
  refused with `MRS-DISP-048`; it then commits and pushes once.
- The scoped stamp refuses, exit non-zero and baseline untouched, when NAME has a path that differs from its baseline entry
  and NAME's memlog does not name; the refusal lists each path and the explicit form that accepts it (a repeatable flag,
  such as `--accept PATH`). A spec with no baseline entry stamps as today; an unscoped stamp is unchanged.
- The stamp's tests live in the marshal package and load the script by path (the
  `tests/meta/test_fleet_picture_*.py` precedent), so the station's own suite runs them.

Ledger key: `82-3-a-landing-claims-only-committed-promotions-rejects-a-malformed-merge-template-and-stamps-only-reconciled-drift`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-4 (a spec counts as promoted only once its bytes are reachable from a ref) with Story 5.9
  (FR-186); CAP-9 with Story 5.10 (FR-187; AD-24); CAP-261 (b) with Story 53.2; CAP-235 (`--write-baseline --spec`
  settles one spec without accepting other drift). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a promote batch whose `commit_paths` raises after every copy succeeded When the envelope is built Then `promoted` is empty, `promoted_count` is 0 and the `MRS-DEPLOY-003` finding names each uncommitted key
- Given a policy layer setting `merge_subject_template` to a string with no `{key}`, or two When the policy composes Then the value is rejected with `MRS-POLICY-002` and the default template applies, and `marshal land` and `land-story` raise no `ValueError`
- Given a branch whose station-`src/` edit drifts both `spec-pyforge-core` and the station's own spec When the landing reconcile runs Then both specs get a memlog entry and a scoped stamp before the merge
- Given own-path drift that remains after the reconcile's bound When the landing runs Then it refuses with `MRS-DISP-048`
- Given a spec with a drifted path its memlog does not name When `spec_surface_check.py --write-baseline --spec NAME` runs Then it exits non-zero, lists the path, and leaves `.spec-surface-baseline.json` byte-identical
- Given the same path accepted explicitly, or named in the memlog When the stamp runs Then it stamps NAME as today
- Given each of the four fixes reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Doctor's verdict stays read-only from marshal (`gather_spec_surface` is read install-free, never modified).
The stamp keeps its flock. A partial promotion is reported as partial, never as complete. Close DW-5-9-2, DW-FU-53-2-3,
DW-5-10-1 and DW-9-1-1 in `deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this
story).

**Never:** Do not edit `pyforge-doctor`'s `sources/chain.py`. Do not change the unscoped `--write-baseline` behaviour. Do
not let the landing reconcile stamp a spec whose drift names a path the branch did not touch (the foreign-drift refusal
stays). Do not change the copy step or the ledger-advance rollback in `deploy.py`.

</intent-contract>

## Binding

Parent: Stories 5.9, 5.10 and 53.2, `spec-pyforge-marshal` CAP-4, CAP-9, CAP-261 (b) and CAP-235; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-3-a-landing-claims-only-committed-promotions-rejects-a-malformed-merge-template-and-stamps-only-reconciled-drift`.
Ledger status at mint: `backlog`.
Deps: —.
Policy: `[epic_surfaces]` `"82"` adds `scripts/spec_surface_check.py` to the station-wide surface.
Closes: DW-5-9-2, DW-FU-53-2-3, DW-5-10-1, DW-9-1-1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
