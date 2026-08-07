---
title: 'Partition findings by actionability'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-1-1-package-scaffold-frozen-finding-doctorreport-contract-exit-code-module.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py',
]
warnings: []
baseline_revision: 'HEAD at Story 3.1 start (after Epic 2 landed)'
---

<intent-contract>

## Intent

**Problem:** `doctor diagnose --prescribe` needs to sort every gathered Finding into `actionable`/`blocked`/`accepted-risk` (FR-6) so an operator sees a worklist, not an undifferentiated dump — and a Finding with no available fix must stay visible as `blocked`, never silently dropped or presented as if today's action item.

**Approach:** `pyforge.doctor.prescribe.partition(findings) -> tuple[PartitionedFinding, ...]` — a pure function (AD-4) classifying every `Finding` by inspecting only its own `status`/`evidence`. `Partition` (the closed 3-member enum) was already frozen in Story 1.1's `models.py`; this story is the first to actually populate it.

Since NO current Source producer (WARDEN_DOCTOR, STALENESS_REPORT, CVE_WATCHER, FEEDSTOCK_HEALTH, RELEASE_CADENCE, ENV_HYGIENE) carries a "is a fix available" or "has this been waived" signal in its evidence today, `partition` reads two forward-compatible evidence hooks (`fix_available`/`block_reason`, `waived`/`waived_reason`) that no producer sets yet — directly testable with synthetic `Finding` fixtures, live the moment a future producer starts setting them, and naturally realize the AC's own "none yet waived" framing (a realistic mix of TODAY's real Findings never populates `ACCEPTED_RISK`, proven by a dedicated test).

## Boundaries & Constraints

**Always:**
- `partition()` classifies EVERY `Finding` passed to it — the returned tuple's length always equals the input's length (Story 3.1 AC1's own "total count across all three partitions equals the count of Findings gathered").
- A `BLOCKED` `PartitionedFinding` always carries a non-empty, human-readable `reason` (Story 3.1 AC2) — never omitted from the returned structure.
- `doctor.prescribe`'s entire import surface stays `{__future__, dataclasses, collections.abc, pyforge.doctor.models}` — zero subprocess, zero MCP import (AD-4), enforced by a new meta-test mirroring `test_sources_warden_no_subprocess.py`'s AST-scan idiom.
- Classification precedence is fixed and total: waived → `ACCEPTED_RISK`; else `status is OK` → `ACTIONABLE`; else `fix_available is False` → `BLOCKED`; else → `ACTIONABLE`. Every `Finding` matches exactly one branch.
- Input order is preserved in the output tuple.

**Never:**
- Never call `atlas.gather`/`warden.gather`/any subprocess or MCP client from `prescribe.py` — it consumes an already-gathered `list[Finding]` only.
- Never drop a Finding from the output — a `Finding` this function cannot confidently classify still lands in `ACTIONABLE` (the safe default: "treat as if actionable" rather than silently vanishing).
- Never treat an `OK` Finding as `BLOCKED`/`ACCEPTED_RISK` — those categories require an unresolved problem; a clean Finding is trivially "nothing to do," which this module models as a degenerate `ACTIONABLE` case (see Design Notes for why, not `OK`'s own fourth bucket — `Partition` stays the frozen 3-member enum Story 1.1 declared).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mixed realistic batch (some fixable, one unfixed CVE, none waived) | `evidence={"fix_available": False}` on one Finding | Exactly one `BLOCKED`, rest `ACTIONABLE`, zero `ACCEPTED_RISK`; total == input count | No error |
| `evidence={"fix_available": False, "block_reason": "..."}` | Custom block reason | `BLOCKED` with that exact reason | No error |
| `evidence={"fix_available": False}`, no `block_reason` | Default reason | `BLOCKED`, reason = "no fix version published" | No error |
| `evidence={"waived": True, "waived_reason": "..."}` | Waived | `ACCEPTED_RISK` with that reason | No error |
| `evidence={"waived": True, "fix_available": False}` | Both hooks set | `ACCEPTED_RISK` wins (waived checked first) | No error |
| `status is DoctorStatus.OK` | Clean Finding | `ACTIONABLE`, reason names "no remediation needed" | No error |
| Ordinary WARN/FAIL, no hooks | Typical live data | `ACTIONABLE`, generic "remediation path exists" reason | No error |
| Empty input | `partition([])` | `()` | No error |
| Order | N Findings in | Same order out | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` — NEW. `PartitionedFinding` (frozen dataclass: `finding`, `partition`, `reason`), `partition(findings) -> tuple[PartitionedFinding, ...]`. Module docstring frames all three Epic 3 stages (3.1/3.2/3.3 land in this same file, per its own forward-looking docstring) since they share one AD-4 purity boundary and one meta-test.
- `src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py` — NEW. AST-scan guard: no `subprocess`/`mcp` import or call site, closed import allowlist. Non-vacuous (fires on synthetic violations), mirrors `test_sources_warden_no_subprocess.py`'s structure.
- `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_partition.py` — NEW. Full I/O matrix (12 tests): total-count invariant, blocked reason (default + custom), waived precedence, OK-finding handling, the "none yet waived" realistic-mix proof, empty input, order preservation, dataclass shape.

## Design Notes

**Why an `OK` Finding is `ACTIONABLE` rather than excluded from partitioning entirely:** Story 3.1 AC1's literal wording ("every Finding appears in exactly one of actionable/blocked/accepted-risk... total count across all three partitions equals the count of Findings gathered") reads over the FULL Finding list `diagnose --prescribe` gathers, which includes healthy `OK` Findings (e.g. a passing engine check). Two readings were possible: (a) `partition()` only ever receives the WARN/FAIL subset (the CLI layer pre-filters), or (b) `partition()` classifies whatever it's given, including `OK`. Resolved in favor of (b): it is the more defensive contract (never assumes what the caller passes), it satisfies the AC's literal wording without a caller-side pre-filter convention that would need its own documentation, and it degrades gracefully — an `OK` Finding sorting into `ACTIONABLE` with a "clean" reason is harmless (Story 3.2's rank() naturally sorts it last, since its severity contributes nothing to the ranking key — see Story 3.2's own spec).

**Why `fix_available`/`waived` are evidence hooks rather than a lookup:** AD-4 requires `doctor.prescribe` to make zero external calls — it cannot query a waiver database or a vulnerability-fix registry that doesn't exist yet in this codebase. Modeling both as evidence keys keeps `partition()` pure while giving a future Source producer (or a future waiver-recording story) a well-known place to put that signal; until one exists, both branches are provably reachable (via unit tests) but never fire on real gathered data — which is exactly what the AC's own fixture describes ("none yet waived").

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_partition.py -q`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **297 passed** (275 baseline from Story 2.3 + 22 new tests: 12 unit + 10 meta).
- Isolated run: 22 passed.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0

Checked specifically for: exception handling (none needed — `partition()` has no failure mode; `evidence.get(...)` on a `dict` never raises, and `Finding.__post_init__` already guarantees `evidence` is always a real dict, never `None`); silent failures (every Finding lands in a bucket, verified by the total-count test); docstring-vs-behavior drift (re-read the module docstring's classification-order claim against `_partition_one`'s actual `if`/`elif` chain — matches exactly, first-match-wins as documented). No MCP/CLI equivalence concern applies to this story (AD-4 has none by design). No resource leaks (no I/O at all).

**Follow-up review recommendation: false** -- no findings.

</intent-contract>
