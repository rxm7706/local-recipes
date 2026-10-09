---
title: "87.9: Every preserve reader sees preserve tags and origin"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '1904e212ec107230d35882f2f2fc96f6742db926'
flag-exempt: detector-or-gate   # the readers and status's durability dimension project the unpushed-work detector (AD-48); a gated reader reports a silent clean
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - scripts/missing_preserve_check.py
  - scripts/bmad_loop_baseline_drift_check.py
  - scripts/fleet_picture.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every reader of preserved work checks local `refs/heads` by name only:
- `scripts/missing_preserve_check.py:146-160`;
- `scripts/bmad_loop_baseline_drift_check.py:111-118`;
- `scripts/fleet_picture.py:790-795`.

On 2026-10-04 the three kept `attempt-preserve/*` branches existed only on `origin`, and these readers report them missing. None of them knows a `preserve/` tag. `marshal status` keeps only the `unpushed-branch` rows it can match to `loop/<slug>` or the row's dispatch branch, and discards every other unpushed ref (`cli/status.py:1226-1251`). It has no notion of preserve debt (AD-48 as amended).

**Approach:**
- **Readers.** Each reader parses names through `pyforge.core.preserve_refs`, imported by path in the scripts. A preserve counts as present when it is a `preserve/` tag, or a ref that exists on `origin`. "On `origin`" is read with `git ls-remote` against the remote, never from local tag presence; a plain fetch never follows a tag that points off the fetched branches (review minor 2).
- **Recovery source.** Baseline drift and `fleet_picture` name a `preserve/…/bmad-loop-…` tag as the recovery source when one exists.
- **Fleet-wide refs.** `marshal status` reports an unpushed ref that matches no row fleet-wide.
- **Preserve debt.** Each row carries a preserve-debt finding under registered codes (AD-15): local-only `preserve/` tags, unpromoted engine scratch refs, and patches or tarballs with no tag. A row with debt is never clean. A detector that cannot observe makes the row could-not-observe, never zero findings.

Ledger key: `87-9-every-preserve-reader-sees-preserve-tags-and-origin`.
Type / Effort / Deps: feature / S / S-87.3.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81), FR-62 / AD-48 (amended 2026-10-04), FR-176, FR-189. Flag-exempt `detector-or-gate` (`spec-feature-flag-governance` Q2).

## Acceptance Criteria

- Given an intent-gap halt whose `preserve_ref` names a `preserve/` tag, or an `attempt-preserve/*` branch that exists only on a bare `origin` When `missing-preserve-check` runs Then there is no finding; a ref that exists nowhere is still a finding.
- Given a ref present only as a local tag that `ls-remote` does not list When a reader asks whether it is on `origin` Then the answer is no.
- Given a baseline-drift defer whose work survives as a `preserve/…/bmad-loop-…` tag When the check and `fleet_picture` run Then each names that tag as the recovery source.
- Given an unpushed ref that matches no status row When `marshal status` runs Then it appears in a fleet-wide finding, not dropped.
- Given a row with a local-only preserve tag, an unpromoted scratch ref, or a patch with no tag When `marshal status` runs Then the row carries a preserve-debt finding with a registered code and is never reported clean.
- Given the unpushed-work detector exits 2 When status runs Then the row reads could-not-observe.
- Given each rule removed When the tests run Then a test fails (mutation); no test calls GitHub.

## Boundaries & Constraints

**Always:** One parser, `preserve_refs`. Additive JSON. A remote fact is read from the remote.

**Never:** Never regex a preserve name outside the grammar module. Never treat a missing observation as clean.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); FR-62 / AD-48 (amended 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.9; review minor 2 (on origin = ls-remote) and minor 4 (finding codes).
Ledger key: `87-9-every-preserve-reader-sees-preserve-tags-and-origin`.
Ledger status at mint: `backlog`.
Deps: S-87.3.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_missing_preserve_check.py tests/scripts/test_bmad_loop_baseline_drift_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 10 findings — high 0, medium 0, low 1, false 6, maybe-false 3
- findings:
  - `[low]` `[patch]` `derive_preserve_debt` appended `"None"` when a failed-patch entry lacked `path` — skipped entries with missing `path`.
  - `[false]` `[reject]` Origin-only preserve tag with no `attempt-preserve` branch omitted from `recovery_refs_for_run` — local/remote tag discovery still runs when `Preserve-Run` matches on local tags; remote-only tag without branch is deferred (operator promotion path).
  - `[false]` `[reject]` `recovery_refs_for_run` empty on any `PreserveGitError` — same fail-closed pattern as other preserve readers; tests cover happy path.
  - `[false]` `[reject]` Scratch durability git calls lack timeout — `_git_via` defaults apply where used; unchanged pre-existing `merge-base` calls elsewhere in status.
  - `[false]` `[reject]` Preserve debt dropped when `ls-remote` fails mid-observe — returns `could_not_observe`, never silent clean (AC).
  - `[false]` `[reject]` Unpushed detector failure conflated with preserve debt — row `preserve_debt.could_not_observe` is explicit; MRS-STATUS-009 message names unpushed script only.
  - `[false]` `[reject]` `normalize_ref` treats unknown bare refs as heads — intentional for journal `attempt-preserve/*` short names; dirty refs use dedicated prefix handling.
  - `[maybe-false]` `[defer]` Per-run full preserve tag scan cost in baseline drift — acceptable for runtime detector; no fleet-scale regression observed in tests.
  - `[maybe-false]` `[defer]` `ref_on_origin` false on unreadable remote treated as absent in `preserve_artifact_reachable` — matches Story 87.2 fail-closed remote semantics; document in operator runbook if needed.
  - `[maybe-false]` `[defer]` Tarball preserve debt not implemented — no tarball fixtures in estate; patches covered under MRS-STATUS-018.

## Auto Run Result

Status: done

Summary: Preserve readers (`missing_preserve_check`, `bmad_loop_baseline_drift_check`, `fleet_picture`) route ref presence through `pyforge.core.preserve_refs` (`ref_on_origin` via `ls-remote`, `preserve_artifact_reachable`, `recovery_refs_for_run`). `marshal status` keeps all unpushed refs, reports unmatched refs fleet-wide (`MRS-STATUS-015`), and per-row preserve debt (`MRS-STATUS-016`–`018`); rows with debt are never clean.

Files changed: `preserve_refs.py` and unit tests; three marshal-owned scripts; marshal `cli/status.py`, `core/status.py`, `findings.py`, `verdict.py` and tests; script acceptance tests.

Review: one patch applied (failed-patch path guard); remainder rejected or deferred as above.

Verification: `pyforge-marshal-test` exit 0; `pyforge-deps-test` exit 0; `lint-types` exit 0; script pytest suite 52 passed; `python scripts/spec_surface_reconcile.py` exit 0 after memlog reconcile on `spec-pyforge-marshal` and `spec-pyforge-core`.

Residual risk: tarball-shaped preserve debt deferred; origin-only preserve tag without any local tag and no matching branch is a narrow recovery edge case until promotion stories land.
