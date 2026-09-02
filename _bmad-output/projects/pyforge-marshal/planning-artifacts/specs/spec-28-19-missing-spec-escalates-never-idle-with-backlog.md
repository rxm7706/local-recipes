---
title: 'Missing-spec escalates, never idle-with-backlog (Story 28.19, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
last_review_pass: 17
difficulty: small
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred:
  - summary: >-
      ATTENTION needs line for missing-spec escalation is not separately unit-tested.
    evidence: |-
      fleet_picture.py ATTENTION block (lines ~788–796) builds the needs string from
      live_row fields; only station_state() remedy projection is pinned in
      test_fleet_picture_missing_spec.py — not the ATTENTION aggregator.
    location: >-
      scripts/fleet_picture.py:788
    severity: medium
  - summary: >-
      Status CLI journal-to-JSON integration for missing-spec escalation is not subprocess-tested.
    evidence: |-
      gather_fleet_missing_spec_escalations and build_fleet_row are unit-tested in
      isolation; no test runs the fleet status sweep with a campaign journal fixture
      and asserts homes[].missing_spec_escalation_glob in JSON output.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py:1525
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Steward 39.4 looked **idle** while remaining=1 because
`MRS-DISP-005` is a refuse, not an escalation. Operators read idle as drained.

**Approach:** v1 does **not** auto-author a stub spec. Preflight refuse for a
missing tracked spec sets `awaiting-operator` (or fleet-picture ATTENTION) and
names the expected `spec-<e>-<n>-*.md` path.

## Acceptance Criteria

- Given a ledger key whose specs glob is empty, when drain preflight refuses,
  then the station is not reported idle while remaining > 0.
- Given that refuse, when `marshal status` / fleet-picture run, then ATTENTION
  (or `awaiting-operator`) names the expected spec path.
- Given this story, when reviewed, then no code writes a new story spec file.

## Boundaries & Constraints

**Never:** Auto-draft specs. `scripts/bmad-switch`. Hide remaining backlog.

Ledger key: `28-19-missing-spec-escalates-never-idle-with-backlog`.

</intent-contract>

## Code Map

- `cli/dispatch.py` — `gather_fleet_missing_spec_escalations()` reads latest fleet-drain campaign journal for active `MRS-DISP-005` blocks with remaining backlog
- `core/dispatch_fleet.py` — `MissingSpecEscalation` dataclass
- `core/status.py` — `_apply_missing_spec_escalation()` overrides idle/stopped/unsupervised/unknown when backlog blocked on missing spec
- `cli/status.py` — threads escalation into `FleetHomeFacts`; text render projects remedy suffix
- `scripts/fleet_picture.py` — state column + ATTENTION names spec glob for MRS-DISP-005 refuse
- Tests: `test_status.py`, `test_dispatch_hotfix.py`, `tests/meta/test_fleet_picture_missing_spec.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass (user dispatch, pass 3)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (high 0, medium 1, low 0)
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto dispatch, pass 5)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (high 0, medium 1, low 0)
- reject: 8
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 11
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 7)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 3
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 8)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 9)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 10)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 11)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 12)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 13)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 14)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 10
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 15)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 5
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 16)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 6
- addressed_findings:
  - none

### 2026-09-01 — Review pass (Cursor bmad-build-auto user dispatch, pass 17)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 2
- addressed_findings:
  - none

## Auto Run Result

Status: done
Blocking condition: commit not performed — user did not request commit; uncommitted changes remain in worktree

### Summary
Story 28.19 (CAP-2): fleet-drain `MRS-DISP-005` refuses with remaining backlog no longer read as idle. Active campaign blocks surface `awaiting-operator` with a remedy naming the expected `spec-<e>-<n>-*.md` glob in `marshal status` and fleet-picture ATTENTION. No code auto-authors story specs.

### Files changed
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `gather_fleet_missing_spec_escalations()` from latest fleet campaign journal
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — `MissingSpecEscalation` dataclass
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `_apply_missing_spec_escalation()` overrides idle/stopped/unsupervised when backlog blocked on missing spec
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` — threads escalation into `FleetHomeFacts` before `build_fleet_row`
- `scripts/fleet_picture.py` — state column + ATTENTION names spec glob for MRS-DISP-005 refuse
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` — missing-spec escalation overrides idle; text remedy projection pin
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py` — `gather_fleet_missing_spec_escalations` integration fixture
- `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_missing_spec.py` — fleet-picture remedy naming pin (marshal meta, not CFE)

### Verification
- Pass 3 (2026-09-01): `BMAD_ACTIVE_PROJECT=pyforge-marshal pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **7375 passed**, 12 deselected (34.32s)
- Targeted: `-k "missing_spec or gather_fleet_missing_spec or test_missing_spec_escalation"` — **10 passed** (2.5s)
- Pass 4 (2026-09-01, Cursor bmad-build-auto): full suite — **7375 passed**, 12 deselected (40.6s); targeted — **10 passed** (1.8s)
- Pass 5 (2026-09-01, Cursor bmad-build-auto): full suite — **7375 passed**, 12 deselected (39.5s); targeted — **10 passed** (1.1s)
- Pass 6 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; prior pass 5 results stand
- Pass 7 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; prior pass 5 results stand
- Pass 8 (2026-09-01, Cursor bmad-build-auto user dispatch): full suite — **7375 passed**, 12 deselected (37.33s); targeted — **10 passed** (2.07s)
- Pass 9 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; pass 8 results stand; code review confirms AC coverage unchanged
- Pass 10 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; pass 8 results stand; static review confirms all three ACs satisfied and no spec-auto-author code paths
- Pass 11 (2026-09-01, Cursor bmad-build-auto user dispatch): full suite — **7375 passed**, 12 deselected (38.44s); targeted — **10 passed** (1.74s)
- Pass 12 (2026-09-01, Cursor bmad-build-auto user dispatch): full suite — **7375 passed**, 12 deselected (38.56s); targeted — **10 passed** (1.08s)
- Pass 13 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; pass 12 results stand; static review confirms all three ACs satisfied
- Pass 14 (2026-09-01, Cursor bmad-build-auto user dispatch): targeted `-k "missing_spec or gather_fleet_missing_spec or test_missing_spec_escalation"` — **10 passed** (1.97s); full suite not re-run this pass
- Pass 15 (2026-09-01, Cursor bmad-build-auto user dispatch): full suite — **7375 passed**, 12 deselected (38.24s); targeted — **10 passed** (2.44s)
- Pass 16 (2026-09-01, Cursor bmad-build-auto user dispatch): full suite — **7375 passed**, 12 deselected (38.87s); targeted — **10 passed** (1.14s)
- Pass 17 (2026-09-01, Cursor bmad-build-auto user dispatch): verification not re-run — shell unavailable in session; pass 16 results stand; static review + Bugbot confirm all three ACs satisfied

### Review findings (pass 17)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 16)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 6 — dispatch-overlay precedence edge case, fleet-campaign-only escalation source, unreadable-spec vs missing-spec gap, multi-story-per-slug break, duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 15)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 5 — dispatch-overlay precedence edge case, fleet-campaign-only escalation source, ledger-backlog drift guard, duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 14)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 10 — standalone-dispatch journal gap, silent gather skips, non-idle override branches untested, ledger/campaign drift, multi-story-per-slug break, `--escalations` filter gap, lexicographic campaign pick, ATTENTION needs line (duplicate deferral), subprocess JSON path (duplicate deferral), gather negative paths (out of scope for v1 CAP-2 idle misread fix)
- Follow-up review recommended: false

### Review findings (pass 13)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 12)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 11)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 10)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 9)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 8)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 2 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 7)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 3 — duplicate deferrals re-surfaced (ATTENTION needs line, subprocess JSON path, explicit no-write guard); out of scope for v1 CAP-2
- Follow-up review recommended: false

### Review findings (pass 6)
- Patches applied: 0
- Deferred: 0 (prior pass deferred items retained in frontmatter)
- Rejected: 11 — dispatch-overlay precedence, silent ledger skip, multi-refuse per slug, lexicographic campaign pick, standalone-dispatch journal gap, CAP-2 Finding emission, sort order, stopped/unsupervised state variants, duplicate deferrals (out of scope for v1 CAP-2 idle misread fix)
- Follow-up review recommended: false

### Review findings (pass 5)
- Patches applied: 0
- Deferred: 2 (`medium` × 2) — ATTENTION `needs` line not separately unit-tested; status CLI journal→JSON integration path not subprocess-tested
- Rejected: 8 — out-of-scope follow-ups (escalations-only view, sort order, skill docs, multi-story per slug, standalone dispatch journal, explicit no-write guard test, Finding emission, latest-campaign-only as spec violation)
- Follow-up review recommended: false (0 patch findings this pass)

### Residual risks
- ATTENTION `needs` line for missing spec is not separately unit-tested; behavior is wired through live-row fields populated by `marshal status`.
- End-to-end path from campaign journal through `marshal status --format json` to fleet-picture ATTENTION relies on unit-tested helpers but lacks one subprocess integration test.
