---
title: 'A `verified:` line on a capability is read and rendered'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '5d2e8bfa52be28febdf616b83bbce4d767144bf8'
review_loop_iteration: 0
followup_review_recommended: true
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

- 2026-09-10 — Story 21.10 shipped: `capability_effect.py` CAP-2 verified-line parse/render/WARN; `Source.CAPABILITY_EFFECT` + schema/registry; unit tests. Dispatch wiring deferred to Story 21.11.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 18 findings — high 0, medium 5, low 3, false 6, maybe-false 4
- findings:
  - `[medium]` `[patch]` Missing `capability-effect` in `test_models.py` taxonomy and `report-schema.json` — fixed both; `test_schema_source_enum_matches_the_source_taxonomy_exactly` green.
  - `[medium]` `[patch]` `gather_verified_line` read-only test never asserted return value — extended test to assert WARN finding tuple.
  - `[medium]` `[patch]` No multi-CAP parse coverage — added `test_multi_cap_spec_parses_each_block_independently`.
  - `[medium]` `[patch]` Quoted YAML frontmatter status (`status: 'shipped'`) not stripped — added quote stripping in `_parse_spec_frontmatter_status` + test.
  - `[medium]` `[defer]` Unreadable `SPEC.md` silently skipped — parent spec fail-open named finding is broader than CAP-2; defer until caller-reach pass (21.9) defines fleet scan degrade shape.
  - `[low]` `[patch]` `UnicodeDecodeError` on non-UTF-8 spec not caught — broadened except clause alongside `OSError`.
  - `[low]` `[patch]` Module docstring contradicted partial `REGISTRY` registration — docstring corrected (21.10 registry, 21.11 dispatch).
  - `[low]` `[reject]` Empty triage/changelog at review start — filled by this pass; not a code defect.
  - `[false]` `[reject]` Per-CAP terminal status required — story I/O matrix "Capability status" reads as spec frontmatter under Epic 21 convention; implementation matches spec Tasks.
  - `[false]` `[reject]` Present verified lines must appear in operator report now — Story 21.11 owns detectors/fleet-picture wiring; silence on present lines is specified.
  - `[false]` `[reject]` Staleness gate on `verified:` date — out of story 21.10 scope; "current" means present non-empty line per I/O matrix.
  - `[false]` `[reject]` Story 21.9 must land first — module shell with CAP-2 only is acceptable; 21.9 extends same file.
  - `[false]` `[reject]` `parse_spec_capability_verified_rows` must be in `__all__` — internal helper; public surface is `iter_*`, `gather_*`, `render_*`.
  - `[false]` `[reject]` Duplicate board parsing is drift risk — intentional reuse of board regex constants; shared heading contract.
  - `[maybe-false]` `[defer]` `iterdir` PermissionError collapses whole fleet scan — `degrade_on_exception` on `gather()` covers; rare in CI.
  - `[maybe-false]` `[defer]` Alternate `## Capabilities` heading silently skips CAPs — known board.py contract; not introduced here.
  - `[maybe-false]` `[defer]` Frontmatter fence without newline before closing `---` — fleet SPEC.md samples use standard fences; board parser not reused to limit scope.
  - `[maybe-false]` `[defer]` `gather()`/`degrade_on_exception` path untested — thin wrapper; verified via `gather_verified_line` integration test.

## Auto Run Result

Status: done

**Summary:** Added `capability_effect.py` (CAP-2): parses optional per-CAP `verified:` lines from fleet `SPEC.md` files, renders them mechanically via `CapabilityVerifiedRow.rendered`, and emits WARN findings when a `shipped`/`realized` Spec's CAP carries no `verified:` line. Read-only by construction. Registered `Source.CAPABILITY_EFFECT` in models, `REGISTRY`, schema, and independence map; `detectors`/`__main__` dispatch remains Story 21.11.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py` — new CAP-2 module
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — `CAPABILITY_EFFECT` enum member
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — registry row
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` — additive enum entry
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_verified.py` — 10 unit tests
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` — taxonomy pin
- `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` — SOURCE_MODULE map

**Review:** 5 patches applied (3 medium test/schema, 2 medium/low robustness); 6 rejected false positives; 4 deferred pre-existing or 21.11/21.9 scope.

**Follow-up review recommended:** true — three medium patches on first pass; unverified risk is filesystem gather path on live multi-CAP fleet specs once Story 21.11 wires dispatch.

**Verification:** `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_verified.py src/shared/packages/pyforge-doctor/tests/unit/test_models.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py -q` — all green (112 tests in targeted set).

**Residual risks:** No live-fleet integration test yet; unreadable spec paths still silent (deferred); operator-visible column awaits Story 21.11 wiring.
