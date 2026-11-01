---
title: "13.2: A TEA skip on a missing ref reaches the report"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-13-1-the-tea-advisory-diffs-from-the-remote-tracking-ref.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-11-2-tea-test-review-is-a-warden-advisory-finding.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-23's success line checks only the argv (`--base refs/remotes/origin/main`), not the effect. When that
ref does not exist, TEA's `tea-test-review` exits 2 (ENV_ERROR); `run_tea_test_review` records
`tea-test-review exited 2 -- verdict not trusted` as the result's `skipped_reason`, and then
`TeaAdvisoryScanPlugin._contribute` drops it at its `if not result.ran: return` (`src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py`, about
:350-351 at `03a7aff5d9`). A report from a scan whose TEA run skipped therefore looks exactly like a report from a scan
with TEA never enabled. EGM audit 2026-11-01 finding WAR-M-Z6 (a Nit; the gap check narrowed it to CAP-23), accepted
by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** In `_contribute`, a result with `ran=False` and a `skipped_reason` from a run that started (the binary was
found: a non-0/1 exit, an unparsable or non-object verdict, or TEA's own skip) appends one advisory record to
`context["advisory_notes"]`: the tool id, `skipped: true` and the reason, with no score and no recommendation. The
`TeaAdvisoryResult` shape and the runner are unchanged. An absent binary keeps Story 9.3's omit-not-error, and
`TeaRosterMissingError` stays loud. Story 11.2's I/O matrix decided that runner errors leave no note
(`spec-11-2-tea-test-review-is-a-warden-advisory-finding.md`, the "Runner errors" row); this story supersedes that row
for an enabled run that started and skipped, through a memlog decision. Story 11.2 is done and is not edited.

Ledger key: `13-2-a-tea-skip-on-a-missing-ref-reaches-the-report`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-23 — the TEA advisory reviews the diff from the remote-tracking ref. A `fix`, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- **AC1 — A skip reaches the report.** Given `WARDEN_OPTIONAL_SCANNERS=tea-test-review`, a suite:AD-9 roster with `tea`, and
  an injected runner that exits 2, When `warden scan` runs, Then the report's `advisory` carries exactly one
  `tea-test-review` record with `skipped: true` and the reason `tea-test-review exited 2 -- verdict not trusted`, and no
  score or recommendation.
- **AC2 — Not enabled stays silent.** Given TEA not in `WARDEN_OPTIONAL_SCANNERS`, When `warden scan` runs, Then the
  report carries no TEA record.
- **AC3 — Advisory only.** Given the AC1 run, When its status and exit code are compared with the same run with TEA
  disabled, Then they are equal; the record never reaches `plugin_findings`, a rung or the exit code.
- **AC4 — The other paths hold.** Given the binary absent from `PATH`, Then no record is written (Story 9.3); given a
  roster without `tea`, Then `TeaRosterMissingError` is still recorded as a `CONFIG_VALIDATION` error.
- **AC5 — The contract follows.** A memlog decision on `spec-pyforge-warden` records the superseded Story 11.2 row, and
  CAP-23's success line names the effect (a skip reaches the report) through a `bmad-spec` re-derive, never a hand edit.
- **AC6 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** keep the TEA advisory advisory: a record in `advisory`, never a finding, a rung or the exit code. Pin each
path with a test that fails without the change (mutation: restore the bare `return`, and AC1 goes red).

**Never:** change TEA's upstream default or its exit-code semantics; run the real agent-backed review in the suite;
hand-edit `SPEC.md`; edit Story 11.2's or Story 13.1's text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| missing base ref | runner exits 2 | one skip record with the reason | fail-open; no exception |
| TEA reports nothing to review | JSON `skipped: true` | one skip record with TEA's reason | — |
| binary absent | roster has `tea`, no binary | no record (Story 9.3) | unchanged |
| roster lacks `tea` | — | `TeaRosterMissingError` | unchanged, loud |
| TEA not enabled | — | no record | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-23 — the TEA advisory reviews the diff from the remote-tracking ref; a
  fix, no new CAP.

Parent: CAP-23

- EGM audit finding carried: WAR-M-Z6 (accepted 2026-11-01; one memlog event on `spec-pyforge-warden/.memlog.md`);
  residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 13 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `13-2-a-tea-skip-on-a-missing-ref-reaches-the-report`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py`, `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py -q` — expected: pass, including the new skip,
  not-enabled and status-equality tests.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): finding WAR-M-Z6, accepted by the
  operator, narrowed by the gap check to CAP-23; mode in-PR.

## Review Triage Log

- (none yet)
