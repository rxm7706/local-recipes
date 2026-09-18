---
title: '46.4: Wire auto resolves against the declared wrapper'
type: 'feature'
created: '2026-09-18'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an operator, I want `_bmad-output/policy-defaults.toml` to carry the repo-default `[context]` block with wire declared `enabled = "auto"` — a tri-state resolving against the running harness profile's declared `[wrapper]`, So that both engines gain the harness-agnostic layers by default and wire turns on exactly where the harness can take it, with zero per-station config.

**Approach:** `core/policy.py` (tri-state schema + resolution), the harness-profile `[wrapper]` declaration read, and `policy-defaults.toml`. Per-station `marshal-policy.toml` becomes force-override only.

Ledger key: `46-4-wire-auto-resolves-against-the-declared-wrapper`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-193 (fold remint of `spec-marshal-token-economy` CAP-20; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-193` ← `spec-marshal-token-economy CAP-20`.

## Acceptance Criteria

- Given a fresh loop home with zero station config When a dispatch or spin launches Then the harness-agnostic layers journal as on (repo default) and wire is on iff the profile declares a `[wrapper]` And on Cursor the wire layer is a clean skip — never a journaled wrap it cannot perform (28.29) And wrapper declared but binary missing stays a WARN (`MRS-DISP-033` class), never silent

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a fresh loop home with zero station config | a dispatch or spin launches | the harness-agnostic layers journal as on (repo default) and wire is on iff the  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
