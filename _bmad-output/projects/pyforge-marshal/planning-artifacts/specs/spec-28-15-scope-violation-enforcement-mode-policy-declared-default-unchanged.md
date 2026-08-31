---
title: 'Scope-violation enforcement mode, policy-declared, default unchanged (Story 28.15, Epic 28)'
type: 'feature'
created: '2026-08-31'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: medium
baseline_revision: '7a13ea55d5ca052cab79edc498afa56fc8716453'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - pyforge-marshal is set to `off` immediately as an operational stopgap (2026-08-31) to
    unblock the live Epic 28 drain — this story ships the real `hard`/`warn`/`off`
    mechanism; the stopgap is not the long-term design.
deferred:
  - summary: >-
      The spec's own title and filename say "default unchanged" but the Approach/AC1
      text and epics.md both say the default flips from hard to warn.
    evidence: |-
      Title: 'Scope-violation enforcement mode, policy-declared, default unchanged
      (Story 28.15, Epic 28)'; Approach text: "Default is `warn`, not `hard`." A future
      grep for "default unchanged" lands on a spec that changed the default.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-15-scope-violation-enforcement-mode-policy-declared-default-unchanged.md
      (title, frontmatter)
    severity: low
  - summary: >-
      The spec's own `warnings:` block and SPEC-marshal-token-economy/SPEC.md both
      claim pyforge-marshal's own policy was already set to `scope_violation_mode = off`
      as an immediate 2026-08-31 stopgap, but no `marshal-policy.toml` in the repo
      (past or present) ever declares that key -- the claimed stopgap action was never
      actually applied.
    evidence: |-
      `grep -rn "scope_violation_mode" --include="*.toml" .` matches nothing outside
      this story's own diff/spec. Functionally moot now that this story's default
      (`warn`) matches the intended steady state, but the warning text is inaccurate
      about what was actually done.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-15-scope-violation-enforcement-mode-policy-declared-default-unchanged.md
      (frontmatter `warnings:`)
    severity: low
  - summary: >-
      epics.md's Story 28.15 operational note attributes the real 2026-08-31 stopgap
      to widening `[epic_surfaces]."28"` to a station-wide wildcard (Story 28.14
      territory), directly conflicting with the spec/SPEC.md's claim that the stopgap
      was `scope_violation_mode = off` (this story's own CAP-17 territory).
    evidence: |-
      Two tracked planning documents disagree about which mechanism was actually used
      for the same named 2026-08-31 operator stopgap.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md (Story 28.15
      operational note) vs. this spec's `warnings:` block
    severity: low
---

<intent-contract>

## Intent

**Problem:** `MRS-GATE-007`/`008` scope violations are non-waivable refuses today — an
unattended drain campaign deadlocks permanently on the first out-of-surface file with no
self-service recovery, while the operator still wants violations visible (not silently
landed).

**Approach:** Add a policy-declared, per-station scope-violation enforcement mode with
three values: `hard` (today's non-waivable refuse), `warn` (findings journaled and surfaced
in `marshal status`/`fleet-picture`, landing not blocked), `off` (check skipped entirely).
Default is `warn`, not `hard`. One station's declared mode never changes another's.

## Acceptance Criteria

- Given no scope-violation mode declared for a station, when a scope violation occurs,
  then it lands as a named, journaled advisory finding and does not refuse landing (`warn`
  default).
- Given `hard` declared for a station, when a scope violation occurs, then behavior
  reproduces today's non-waivable refuse exactly.
- Given `off` declared for a station, when files change outside surface, then
  `MRS-GATE-007`/`008` are not evaluated — zero findings, zero journal entries.
- Given `warn` mode and a violation, when `marshal status` or `fleet-picture` renders, then
  the finding is visible — not journal-only.
- Given two stations with different declared modes, when each violates scope, then each
  station's mode applies independently.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-15-scope-violation-enforcement-mode-policy-declared-default-unchanged`.

**Block If:** A change would make `warn` silently equivalent to `off`, or apply one
station's mode fleet-wide.

**Never:** Removing scope containment checks entirely as the fleet default. A second
scope-gate mechanism outside Epic 2's gate objects.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` (`MRS-GATE-007`/`008` verdict shaping)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (per-station mode key + validator)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (render warn-mode findings)
- `scripts/fleet_picture.py` (fleet-wide visibility of warn-mode violations)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(default warn, hard reproduces refuse, off skips, status visibility, per-station isolation).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.15 and spec-marshal-token-economy CAP-17. Deps: —. Pairs with
Story 28.14 (CAP-16 auto-derive reduces how often violations fire; CAP-17 ensures the
remainder never deadlocks an autonomous drain). Operator decision 2026-08-31: visible but
non-blocking is the steady state once auto-derivation is trusted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from live MRS-GATE-007 dispatch stall (CAP-17; operator fold-in same session)

## Review Triage Log

### 2026-08-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1high, medium 3medium, low 0low)
- defer: 3: (high 0high, medium 0medium, low 3low)
- reject: 3: (high 0high, medium 0medium, low 3low)
- addressed_findings:
  - `[high]` `[patch]` No test exercised the real supervisor-to-journal-to-status round trip for warn-mode scope advisories (`dispatch_supervisor/__main__.py::_run_and_journal_verification` writes `scope_violation_advisories`, `cli/dispatch.py::gather_dispatch_journal_facts` reads it back) — every existing test constructed `FleetHomeFacts`/`DispatchJournalFacts` by hand, skipping the write/read pair AC4 depends on. Added a round-trip test driving the real write and read functions together.
  - `[medium]` `[patch]` `core/gate.py`'s `_SCOPE_VIOLATION_MODES` duplicated `core/policy.py`'s own frozenset literally instead of importing one source of truth, risking silent divergence if a mode value is ever added to one copy and not the other. `gate.py` now imports it from `policy.py`.
  - `[medium]` `[patch]` `dispatch_supervisor/__main__.py` hardcoded a third independent copy of the `{"MRS-GATE-012", "MRS-GATE-013"}` advisory-code set instead of referencing `core/gate.py::_SCOPE_VIOLATION_ADVISORY_CODES`. Now references the shared mapping's values.
  - `[medium]` `[patch]` `scripts/fleet_picture.py`'s advisory-codes join (`a.get("code", "?")` for each item in a list parsed from subprocess JSON) sat outside the try/except that guards the rest of that parse, and would raise uncaught on a non-dict item or an explicit `null` code, taking down the whole ATTENTION report. Guarded with an isinstance/str check, matching the precedent already used for the same field in `cli/status.py`.

Deferred (pre-existing, not caused by this diff) and rejected findings recorded per the workflow's own triage rules; see frontmatter `deferred:` for the three deferred items. Rejected: a docstring wording nitpick (`check_scope_with_mode`'s advisory message already textually distinguishes the two violation kinds via `finding.message`, disproving the claimed operator-visibility gap), the WIP-checkpoint commit's `status: in-review` (an artifact of this same review pass's own required status transition, not an implementation defect), and a code-comment citation nitpick (misattributes which planning doc coined a quoted phrase).

## Auto Run Result

**Summary:** Implemented Story 28.15 (CAP-17) exactly per the Approach: a policy-declared,
per-station `scope_violation_mode` (`hard`/`warn`/`off`) governing `MRS-GATE-007`/`008`
scope-containment findings, defaulting to `warn`. `core/gate.py::check_scope_with_mode` is
the single place both call sites (`cli/gate.py::_run_scope_check`,
`dispatch_verify.py::evaluate_dispatch_verification`) apply the mode: `off` skips
`check_scope` entirely (zero findings); `hard` returns `check_scope`'s raw output
byte-identical; `warn` replaces each raw finding with a new `MRS-GATE-012`/`013` advisory
(`Verdict.WARN`, never `Verdict.SCOPE_VIOLATION`, per AD-31) naming the same offending path.
Visibility (AC4) threads a `verification_scope_advisories` list end-to-end:
`dispatch_supervisor` journals it, `DispatchJournalFacts`/`FleetHomeFacts` carry it,
`marshal status` (JSON + text) and `scripts/fleet_picture.py`'s ATTENTION block render it,
never journal-only.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` — `check_scope_with_mode` (the mode-application core) + `_SCOPE_VIOLATION_ADVISORY_CODES`; reuses `policy._SCOPE_VIOLATION_MODES` (patch).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — new 31st STATIC key `scope_violation_mode`, closed vocabulary, default `"warn"`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — registers `MRS-GATE-012`/`013`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — classifies both new codes `Verdict.WARN`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py` — `_run_scope_check` resolves and applies the effective mode.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — `evaluate_dispatch_verification` resolves and applies the effective mode.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — journals warn-mode advisories under `scope_violation_advisories`; filters via `gate._SCOPE_VIOLATION_ADVISORY_CODES.values()` (patch).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — `DispatchJournalFacts.verification_scope_advisories`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `gather_dispatch_journal_facts` reads the journaled advisories back.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `FleetHomeFacts.dispatch_verification_scope_advisories` + overlay.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` — JSON + text (`SCOPE_ADVISORY`) rendering, deduped codes (patch).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py` — `scope_violation_mode` in field order / unsettable-keys (no `--set` surface, matching `epic_surfaces`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json` — new field + updated `required`/key count.
- `scripts/fleet_picture.py` — ATTENTION `watch` line for warn-mode advisories, deduped + isinstance-guarded (patch).
- Test files under `tests/unit/` (`test_cli.py`, `test_dispatch_verification.py`, `test_findings.py`, `test_policy.py`, `test_scope.py`, `test_status.py`, `test_dispatch_station_guard.py`) and `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — ~36 new tests covering the 5 ACs plus the round-trip regression test (patch).

**Review findings breakdown:** patch: 4 (1 high, 3 medium, 0 low) — all applied and re-verified; defer: 3 (all low, pre-existing spec/doc inconsistencies unrelated to this diff, recorded in frontmatter `deferred:`); reject: 3 (a disproven docstring claim, a review-process artifact, a comment-citation nitpick).

**Follow-up review recommendation:** `true`. One patched finding (the missing supervisor→journal→status round-trip test for AC4) was `high` severity, which alone sets this `true` regardless of the numeric score. Patched-by-severity: high=1, medium=3, low=0 (score = 3×3 + 1×0 = 9, also ≥ 5 independently).

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 6799 passed, 12 deselected (post-patch; 6798 passed pre-patch, +1 for the new round-trip test).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 118 passed, 1 skipped.
- Both re-run and confirmed green after the patch pass, independently of the implementation subagent's own report.

**Residual risks:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`'s `[epic_surfaces]."28"` station-wide wildcard stopgap (Story 28.14) was not narrowed — out of this story's Code Map, and largely moot now that the fleet-wide default is `warn`.
- `cli/deploy.py::run_land_story` (`marshal deploy land-story`, the separate manual FR-27 landing command, `MRS-DEPLOY-010`) still treats any WARN-tier finding — including a new `MRS-GATE-012`/`013` advisory — as a refusal; intentional and out of CAP-17's scope (which governs the automated dispatch/drain landing path), but worth knowing if `land-story` is ever used directly against a `warn`-mode advisory.
- Three low-severity, pre-existing documentation inconsistencies deferred (see frontmatter `deferred:`): the spec's own title/filename ("default unchanged") contradicts its Approach text ("default warn"); the spec's `warnings:` block claims an `off` stopgap was already applied to pyforge-marshal's own policy, but no `marshal-policy.toml` anywhere in the repo ever declared that key; and epics.md's operational note attributes the real 2026-08-31 stopgap to a different mechanism (`epic_surfaces` widening) than the spec claims.
