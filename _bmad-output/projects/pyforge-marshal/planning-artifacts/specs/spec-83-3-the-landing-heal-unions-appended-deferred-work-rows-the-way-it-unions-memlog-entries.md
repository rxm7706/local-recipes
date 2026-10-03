---
title: '83.3: The landing heal unions appended deferred-work rows the way it unions memlog entries'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
baseline_revision: '786b1c9676baf940bb880bf6cccc85cc1bdd445b'
---

<intent-contract>

## Intent

**Problem:** The landing heal (CAP-283, Story 78.1) resolves merge conflicts mechanically only for append-only memlogs and sprint ledgers but refuses deferred-work-ledger.md (MRS-DISP-038). When parallel stories each append `### DW-` rows to the station's deferred-work-ledger.md, the second landing always refuses: on 2026-10-02 82.9 refused against 82.10 on that file alone and required manual resolution.

**Approach:** Extend mechanical conflict resolution to include deferred-work-ledger.md. Add a `union_deferred_work_texts` function that resolves conflicts when both sides only appended whole entries after the merge base. The union contains base text, then main's entries, then branch's entries, preventing duplication while preserving order.

## Boundaries & Constraints

**Always:** Only resolve station's own deferred-work-ledger.md when changes are pure appends of complete entries. Reject any edit to existing entries or changes to other project's ledgers.

**Never:** Never resolve from conflict markers, never drop or duplicate entries, never touch another project's ledger, never resolve partial entry edits.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Both sides append new DW entries | Base + main entries + branch entries | Union with base, main's, then branch's entries | None - successful union |
| One side edits existing entry | Base with modified existing entry | No union - refuse resolution | Return None, escalate path |
| Different projects' ledgers | Conflict in other project's ledger | No union - refuse resolution | Return None, escalate path |
| No deferred work ledger changes | No conflicts in deferred ledgers | Normal flow | None - no special handling |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` -- Contains `is_mechanical_conflict_path` that needs to recognize deferred-work-ledger.md and `union_memlog_texts` as reference implementation
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py` -- Contains `_resolve_mechanical_conflicts` that needs to handle deferred work ledger conflicts similar to memlogs
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py` -- Contains tests for `union_memlog_texts` that need parallel tests for deferred work union function
- `_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md` -- Target files that use `### DW-` entry format with metadata fields

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` -- Add `union_deferred_work_texts` function following memlog union pattern but for DW entry format
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` -- Update `is_mechanical_conflict_path` to recognize deferred-work-ledger.md paths  
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py` -- Update `_resolve_mechanical_conflicts` to handle deferred work ledger conflicts using the new union function
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py` -- Add comprehensive tests for deferred work union scenarios including success and failure cases

**Acceptance Criteria:**
- Given both sides appended whole DW entries after the same point of the station's own ledger, when the heal runs, then the ledger holds base, main's entries, then branch's entries, each whole, and the landing merges
- Given either side edited an existing entry, when the heal runs, then it refuses (MRS-DISP-038)
- Given the conflict is in another project's ledger, when the heal runs, then it refuses
- Given the ledger rule removed, when its new test runs, then it fails (mutation test)

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)  
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0

## Design Notes

Deferred work entries follow a specific structure:
- Header: `### DW-{ID}: {TITLE}`
- Metadata fields: `origin:`, `source_spec:`, `severity:`, `reason:`, `status:`
- Verification lines: `verified: {timestamp} — {verdict} — {evidence}`

The union function should treat each complete `### DW-` section as an atomic unit, similar to how `union_memlog_texts` treats memlog entries as lines. Key differences:
- DW entries span multiple lines vs single-line memlog entries
- Need to parse entry boundaries by `### DW-` headers
- Preserve complete entries including all metadata and verification lines

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 9 findings — high 1, medium 2, low 4, false 1, maybe-false 0
- findings:
  - `medium` `patch` Missing edge case handling for malformed DW entries — Added validation guards for entry structure in parsing functions
  - `false` `reject` Inconsistent error handling for deferred work paths — VCS operations already handle missing files correctly through existing error paths
  - `low` `reject` Missing validation for DW entry ID uniqueness — Not required by intent and would add significant complexity for edge case not affecting core functionality
  - `low` `reject` Incomplete test coverage for complex frontmatter scenarios — Follows existing memlog test patterns and covers intent requirements adequately  
  - `medium` `patch` Missing boundary validation for entry content — Same as first finding, consolidated into entry structure validation
  - `low` `reject` Lack of handling for trailing whitespace variations — Edge case not handled by existing memlog logic either, consistent with codebase patterns
  - `low` `reject` Missing documentation for union algorithm's ordering guarantees — Intent specifies ordering clearly enough, implementation follows it correctly
  - `high` `patch` Deduplication logic flaw with set-based removal — Set.discard can drop legitimate duplicate entries that should be preserved in union
  - `low` `defer` Intent alignment gaps in implementation details — Implementation makes reasonable decisions beyond intent scope, documentation for future spec improvements
