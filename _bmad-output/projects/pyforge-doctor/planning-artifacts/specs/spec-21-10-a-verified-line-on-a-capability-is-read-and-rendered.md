---
title: 'A `verified:` line on a capability is read and rendered'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The Unifying Strategy's 2026-09-09 review asked for a "realized versus
verified" column and nothing produces one — a capability's evidence, if anyone ever
actually looked, lives only in prose in a research file, which no detector reads and
which goes stale between passes.

**Approach:** A CAP may carry `verified: <date> — <what was exercised, where>` on the
capability itself in `SPEC.md`. The check (in the same new source module introduced
by Story 21.9) renders that line beside the capability, reports a
`shipped`/`realized` capability that carries **no** `verified:` line, and stays silent
for a capability that carries a current one. The check **never authors one itself**
(read-only, NFR-1) — the column is produced mechanically from `SPEC.md` rather than
hand-maintained in a research file that goes stale between passes.

## Boundaries & Constraints

**Always:**
- A CAP's `verified:` line, when present, is read directly from `SPEC.md` and
  rendered beside the capability in the report.
- A `shipped`/`realized` capability with no `verified:` line produces a finding.
- A capability that already carries a current `verified:` line stays silent (no
  finding).
- The check is strictly read-only — it never writes, authors, or proposes a
  `verified:` line itself (NFR-1).

**Never:**
- The check never mutates `SPEC.md` or any other tracked file.
- The "realized versus verified" column is never hand-maintained in a separate
  research file — it must be produced mechanically from `SPEC.md`'s own content.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CAP with a `verified:` line | `SPEC.md` capability carries `verified: <date> — <what/where>` | The line is rendered beside the capability; no finding | n/a |
| `shipped`/`realized` CAP with no `verified:` line | Capability status is `shipped` or `realized`, no `verified:` present | Finding reported | n/a |
| Non-terminal CAP with no `verified:` line | Capability not yet `shipped`/`realized` | No finding (verification not expected yet) | n/a |
| Attempted self-authoring | Any code path that might write a `verified:` line | Never occurs — read-only by construction | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` — the same new source module introduced by Story 21.9 (`spec-capability-effect-check`'s home).
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests for `verified:` line reading/rendering and the missing-line finding.

## Tasks & Acceptance

**Execution:**
- `feature` — extend the Story 21.9 source module to parse an optional `verified: <date> — <what was exercised, where>` line per capability in `SPEC.md`.
- `feature` — render the `verified:` line beside its capability when present.
- `feature` — report a finding for a `shipped`/`realized` capability carrying no `verified:` line; stay silent when a current line is present.
- `feature` — add unit tests covering: present line (rendered, silent), missing line on a terminal-status CAP (finding), missing line on a non-terminal CAP (no finding).

**Acceptance Criteria:**
- Given the Unifying Strategy's 2026-09-09 review asked for a "realized versus verified" column and nothing produces one, so a capability's evidence — if anyone ever looked — lives in prose no detector reads, when a CAP may carry `verified: <date> — <what was exercised, where>` on the capability itself in `SPEC.md`, then the check renders that line beside the capability.
- The check reports a `shipped`/`realized` capability that carries none.
- The check stays silent for a capability with a current line.
- The check never authors one itself (read-only, NFR-1) — the column is produced mechanically from `SPEC.md` rather than hand-maintained in a research file that goes stale between passes.

## Spec Change Log

## Review Triage Log
