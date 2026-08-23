---
title: 'The verify_scope primitive'
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'PR #691 / 54425c84f4'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: e922ab953b2f
followup_review_recommended: true
deferred:
  - summary: >-
      Until 20.7, cli/init.py and scripts/bmad-switch still ship divergent
      slug-parse / desync bodies alongside pyforge.marshal.scope.
    evidence: |-
      CAP-1 ships the sole new primitive but intentionally leaves legacy
      guards in place; never-two-parallel-copies is satisfied for the new
      module, with body retirement deferred to CAP-2.
    location: >-
      cli/init.py:_slug_from_symlink_target; scripts/bmad-switch:desync_warning
    severity: medium
  - summary: >-
      MRS-INIT-003 today inspects only planning-artifacts; verify_scope
      requires both artifact symlinks — 20.7 must absorb the widening.
    evidence: |-
      Blind-hunter / design note: semantic widening when CAP-2 replaces the
      guard with verify_scope.
    location: >-
      cli/init.py:MRS-INIT-003 vs pyforge.marshal.scope.verify_scope
    severity: low
---

<intent-contract>

## Intent

**Problem:** FR-190 CAP-1 (`spec-bmad-switch-scope-enforcement`): callers need one cheap primitive that detects active-project marker/symlink drift (DW-1-4-2 blind spots) without inferred agreement. Story 20.7 will hard-wire guards; this story only ships the shared primitive.

**Approach:** Implement `verify_scope(root, expected_slug)` as one shared module. Placement (import path vs Genesis COPIED-MANAGED copy) is this story's design decision under never-two-parallel-copies — document it. Three file reads + string compares; no subprocess. Do not implement 20.7 guard hard-fail wiring yet.

## Acceptance Criteria

- Marker + both symlinks all at slug B → `verify_scope(root, "A")` returns `ScopeDrift` naming found-vs-expected.
- Unrecognized symlink-target shape → drift reporting `"unrecognized"` (never inferred agreement).
- All three agree on expected slug → returns `None`.
- No subprocess; cheap enough for a write-skill preflight.
- Single module home documented; no second parallel copy.
- Does not implement 20.7–20.10 (guards still soft/legacy until 20.7).

## Boundaries & Constraints

**Never:** Two parallel copies of the primitive. Never implement 20.7 hard-fail wiring in this story. Never change `scripts/bmad-switch` behavior beyond exporting/consuming the new primitive if needed for tests. Finalize marshal ledger only. Do not touch steward 16-3 / PR #688.

</intent-contract>

## Design Notes

### never-two-parallel-copies — placement decision

**Chosen home:** `pyforge.marshal.scope`
(`src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py`)

| Option | Verdict |
|--------|---------|
| Import path under `pyforge.marshal` (this choice) | **Selected.** One module both 20.7 callers can import; monorepo already installs `pyforge-marshal` via pixi. |
| Under `pyforge.marshal.core` | **Rejected.** AD-4 forbids I/O in `core/**`; this primitive is three filesystem reads. |
| Genesis COPIED-MANAGED twin checked into this repo | **Rejected for CAP-1.** Would be a second body unless mechanically generated; violates never-two-parallel-copies *here*. Body is stdlib-only so Genesis *may* later deliver this single file alongside `bmad-switch` without forking — delivery is not a second source in this repo. |
| Standalone under `scripts/` only | **Rejected.** `cli/init.py` would either path-hack or reimplement; recreates the divergent-pair failure mode. |

**Rationale:** CAP-2 (story 20.7) must retire both `scripts/bmad-switch` and `cli/init.py` MRS-INIT-003 bodies by importing **this** module. Import-path keeps a single source of truth; stdlib-only (`dataclasses` + `pathlib`) keeps the door open for Genesis delivery without a marshal dependency in foreign checkouts — without shipping two copies today.

**Out of scope (20.7):** Do not replace `desync_warning` / MRS-INIT-003 hard-fail behavior yet. DW-1-4-2 stays open until 20.7 closes it.

## Code Map

| Path | Role |
|------|------|
| `src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py` | **Sole** `verify_scope` + `ScopeDrift` + `UNRECOGNIZED` implementation |
| `src/shared/packages/pyforge-marshal/tests/unit/test_verify_scope.py` | Agree / A-vs-B / unrecognized / missing / no-subprocess AST matrix |
| `scripts/bmad-switch` (`desync_warning`, `read_link_slugs`) | Legacy soft guard — **unchanged** this story |
| `…/cli/init.py` (`_slug_from_symlink_target`, MRS-INIT-003) | Legacy hard guard — **unchanged** this story |
| deferred-work-ledger `DW-1-4-2` | Reference only; closeout is 20.7 |

## Tasks

- [x] Add `pyforge.marshal.scope` with `verify_scope` / `ScopeDrift` / `"unrecognized"` fail-closed parsing
- [x] Document never-two-parallel-copies placement (module docstring + this Design Notes)
- [x] Unit tests: agree → `None`; B-vs-A → `ScopeDrift`; unrecognized shapes → `"unrecognized"`
- [x] Run unit tests (pass)
- [x] Review patches: UNRECOGNIZED expected-slug false-pass; UnicodeDecodeError; is_symlink OSError; `.`/`..` slugs
- [ ] ~~Wire `bmad-switch --current` / MRS-INIT-003~~ → story 20.7
- [ ] ~~Close DW-1-4-2~~ → story 20.7

## Verification

- Unit matrix: agree→None; A-vs-B→ScopeDrift; unrecognized→`"unrecognized"`
- No subprocess in implementation (AST import/attr scan in `test_verify_scope.py`)
- Related marshal tests green; CI detectors/linter/named-module-gates as applicable

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 2, low 4)
- defer: 2: (high 0, medium 1, low 1)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[high]` `[patch]` `expected_slug == "unrecognized"` false-pass on missing triangle — refuse UNRECOGNIZED as successful expected
  - `[medium]` `[patch]` catch `UnicodeDecodeError` on marker read → UNRECOGNIZED
  - `[medium]` `[patch]` wrap `path.is_symlink()` OSError → UNRECOGNIZED
  - `[low]` `[patch]` reject `.` / `..` symlink slug segments
  - `[low]` `[patch]` tests: empty marker, non-symlink occupant, non-UTF-8 marker, expected-token collision
  - `[low]` `[patch]` record placement decision on parent CAP Spec (open_questions → decisions)

## Auto Run Result

Status: done

Summary: Shipped sole `pyforge.marshal.scope.verify_scope` / `ScopeDrift` primitive (CAP-1). Placement = import path under `pyforge.marshal` (not `core/`, not Genesis twin, not `scripts/`-only). Review patches closed fail-closed edge cases. Guards and DW-1-4-2 remain for 20.7.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py` — sole primitive
- `src/shared/packages/pyforge-marshal/tests/unit/test_verify_scope.py` — unit matrix (14 tests)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-20-6-the-verify-scope-primitive.md` — design notes + triage
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-switch-scope-enforcement/SPEC.md` — placement decision recorded

Review findings: 7 patches applied; 2 deferred (legacy parallel bodies until 20.7; planning-only vs both-links widening); 6 rejected (noise / overkill / by-design).

Follow-up review recommendation: true (patched high=1; score N/A once high present).

Verification: `pixi run -e pyforge-marshal pytest …/test_verify_scope.py -q` → 14 passed.

Residual risks: legacy guards still soft until 20.7; DW-1-4-2 still open.
