---
title: '83.3: The landing heal unions appended deferred-work rows the way it unions memlog entries'
type: 'fix'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
declared_low_risk: false
baseline_revision: '495f1fbd1f561eedc2250b34ae6279328f1034f9'
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

**Added 2026-10-03:**
- Given the live `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` as base with one whole row appended on each side, when the union runs, then the result holds every base entry byte for byte plus both new rows (entry count = base + 2), in a test that reads a copy of the real ledger's mixed formats.

**Added 2026-10-03 (later):**
- Given the live ledger as base, main changing one legacy `## DW-` entry's `status:` line and appending a row, and the branch appending a row, when the union runs, then it returns `None` (the heal escalates; nothing is dropped).
- Given main appended `[A]` and the branch appended `[A, B]`, when the union runs, then the result is base, `A`, `B`, each once, separated from the entry before it by exactly one blank line (asserted on exact bytes).

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

## Spec Change Log

- 2026-10-03 — sent back by the operator session after the landing was refused (findings below). One acceptance criterion added: the union is proved on the live ledger, not only on fixtures. Status back to `ready-for-dev`.
- 2026-10-03 (later) — sent back a second time (findings below). Two acceptance criteria added: legacy `## DW-` entries are compared, and an entry both sides appended appears once with the ledger's blank-line separator. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 (later) — Landing review (operator session) — sent back again
- Dispatch run `pyforge-marshal-20261003T133852198Z-8c6f8963` refused at verification: MRS-GATE-018. The pre-verification deferred-work intake (Story 83.2) refused this spec's `deferred:` entry because it had no resolvable `location:`. The entry recorded no defect, so the operator session removed it. Never write a `deferred:` entry without a repo file path in `location:`.
- `high` `patch` **Data loss in the preamble.** The marshal ledger holds legacy entries headed `## DW-1-1-1 — …` (about 16 KB of them) before the first `### DW-` header. `_opaque_dw_blocks` treats all of that text as a preamble. `union_deferred_work_texts` never compares the preamble and always renders the base's copy. So when main edits a legacy entry (probe: `status: open` changed to `closed` at offset 10221 of the live ledger) and both sides append a row, the union succeeds and main's edit is silently lost. Fix: split entries on every `## DW-` and `### DW-` header. Require the text before the first entry to be unchanged on both sides, or return `None`.
- `high` `patch` **Duplicate entry.** When both sides append the same block and the branch appends another, `branch_only` is computed but the whole branch tail is appended. Probe: base + main `[A]` + branch `[A, B]` renders `A, A, B`. Fix: append only the `branch_only` blocks.
- `medium` `patch` **Separator lost.** The base is `rstrip`ped and the next block starts with one newline. Probe on the live ledger: `status: closed\n### DW-probe-a`, with no blank line between entries. Fix: join appended blocks with the ledger's blank-line separator, and assert exact bytes in the live-ledger test.

### 2026-10-03 — Review pass (bmad-build-auto)
### 2026-10-03 — Review pass (bmad-build-auto)
- verdicts: 3 findings — high 1, medium 1, low 1, false 0, maybe-false 0
- findings:
  - `high` `patch` Data loss from `_validate_dw_entry` filtering — Removed validation; `_opaque_dw_blocks` keeps every `### DW-` section byte-identical; live ledger probe holds 482+2 entries.
  - `medium` `patch` Re-render changed untouched entry bytes — Union now keeps merge-base text verbatim and appends tails via `_append_tail_after_shared_blocks`.
  - `low` `patch` Inline `Counter` import — Already at module level; no change required.

### 2026-10-03 — Landing review (operator session) — sent back
- Dispatch run `pyforge-marshal-20261003T010512467Z-a81a3eac` refused at verification: MRS-GATE-001, `lint-types` exited 1 — `W293` whitespace and `ruff format` in `core/dispatch_landing.py` (fixed on this branch by the operator session) and two mypy `var-annotated` errors (`current_entry_lines`, lines ~302 and ~349; still open).
- `high` `patch` **Data loss.** `_extract_base_and_entries` drops every `### DW-` entry that `_validate_dw_entry` rejects (no `origin:` and `status:` lines at column 0), and `union_deferred_work_texts` renders only the kept entries. The ledger carries two entry formats (for example `DW-FU-1-1` uses `origin:`/`status:` lines; `DW-FU-2-1` uses a `- source_spec:` list with an indented `status:`). Probe on the live marshal ledger with one row appended on each side: 482 entries in, 207 kept, the union renders 209 of the expected 484, so one heal would delete 275 rows. Never filter entries: treat every `### DW-` block as opaque text, compare blocks byte for byte, and refuse (return `None`) on anything that is not a pure append of whole blocks.
- `medium` `patch` The rendered union re-joins every block with a single blank line and strips trailing blank lines, so untouched entries change bytes. Preserve the base's text verbatim and append only the new blocks.
- `low` `patch` `from collections import Counter` inside `union_deferred_work_texts`; import at module level.

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
  - `high` `patch` Deduplication logic flaw with set-based removal — Fixed with counter-based deduplication to preserve legitimate duplicate entries
  - `low` `defer` Intent alignment gaps in implementation details — Implementation makes reasonable decisions beyond intent scope, documentation for future spec improvements

## Auto Run Result

**Summary**: Repaired `union_deferred_work_texts` so every `### DW-` block stays opaque (no validation filtering), the merge-base ledger is preserved verbatim, and appended tails keep original separators — fixing the 2026-10-03 send-back data-loss and re-render bugs. Added a live `deferred-work-ledger.md` union probe and mutation partner test.

**Files Changed**:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` — Opaque block split/union; append tails after shared blocks
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py` — Live ledger mixed-format union test; mutation partner; import order

**Review Findings**: 2026-10-03 operator send-back items treated as patches applied in this pass (opaque blocks, verbatim base, module-level `Counter` already present). No new review-layer findings this pass; prior deferred frontmatter item retained.

**Follow-up Review Recommendation**: false

**Verification Performed**:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass
- `pixi run --frozen -e pyforge-guild lint-types` — pass
- `python scripts/spec_surface_reconcile.py` — pass (memlog reconcile on `spec-pyforge-marshal/.memlog.md`)

**Residual Risks**: None identified for landing heal on append-only deferred-work ledgers.
