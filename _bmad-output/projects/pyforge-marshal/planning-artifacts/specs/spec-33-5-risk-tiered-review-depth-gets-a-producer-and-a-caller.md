---
title: 'Risk-tiered review depth gets a producer and a caller'
type: 'feature'
created: '2026-09-09'
status: 'done'
baseline_revision: '78fc2be72b980c64725efdb6764e1f74e57d7e32'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - ../../../../../../.claude/skills/pyforge-marshal/SKILL.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 2.8 shipped `classify_review_tier` and `resolve_review_cycles` in
`core/gate.py`, but they have zero callers outside unit tests. There is no producer for
`declared_low_risk`, no `VcsPort.changed_files` gather on the gate path, and
`marshal gate evaluate` never classifies review depth — every story still pays the same
review-cycle ceiling.

**Approach:** Add a story-spec frontmatter key `declared_low_risk` (default `false` in
templates), a pure parser mirroring the existing frontmatter readers, and wire
`cli/gate.py` so a resolved `--story` reads the declaration, gathers `changed_files`
via `VcsPort`, calls `classify_review_tier` → `resolve_review_cycles`, and records the
tier plus tier-adjusted `max_review_cycles` in the gate envelope.

## Boundaries & Constraints

**Always:** The independent reviewer never runs zero cycles — `resolve_review_cycles`
floors at 1. `max_followup_reviews` is untouched (CAP-3 / DW-AD23-3). Classification
facts and the resolved cycle allowance appear in the gate envelope whenever `--story`
resolves. Absent `declared_low_risk` frontmatter means `false`.

**Never:** No third tier, no CLI flag alternative, no change to `max_followup_reviews`,
no harness/spin policy render changes in this story (gate evidence only). Do not read
spec frontmatter inside `core/gate.py` (AD-4).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Declared low-risk, small diff | `declared_low_risk: true`, ≤3 changed files | `review_depth.tier == "low"`, resolved cycles `1` when default is `3` | No error |
| Declared low-risk, wide diff | `declared_low_risk: true`, >3 changed files | `tier == "standard"`, resolved cycles equal default | No error |
| Undeclared, any diff | no key / `false` | `tier == "standard"` | No error |
| VCS unavailable | `changed_files` gather fails | `review_depth.checked == false` with reason; no crash | Optional MRS-GATE-009 only when scope-check also needs files |
| Multi-line block form | `declared_low_risk:` YAML block | Parser raises `LowRiskParseError`; gate reports skip reason | Finding-free skip with reason in envelope |

</intent-contract>

## Code Map

- `core/gate.py:724-795` — existing `classify_review_tier` / `resolve_review_cycles` (do not change semantics)
- `core/spec_low_risk.py` — NEW: `parse_declared_low_risk` (mirror `spec_difficulty.py` bool scalar discipline)
- `cli/gate.py` — wire review-depth gather after story/spec resolution; add `data["review_depth"]`; extend `_render_text`
- `ports/vcs.py` / `adapters/vcs_git.py` — existing `changed_files` (read-only reuse)
- `.claude/skills/bmad-build-auto/spec-template.md` — add `declared_low_risk: false`
- `tests/unit/test_spec_low_risk.py` — parser matrix
- `tests/unit/test_cli.py` — gate evaluate integration proving low vs standard resolved cycles

## Tasks & Acceptance

**Execution:**
- `core/spec_low_risk.py` — implement `parse_declared_low_risk` and `LowRiskParseError`
- `cli/gate.py` — gather declaration + `changed_files`, call tier functions, populate `review_depth`
- `.claude/skills/bmad-build-auto/spec-template.md` — add `declared_low_risk: false` with comment
- `tests/unit/test_spec_low_risk.py` — parser I/O matrix
- `tests/unit/test_cli.py` — two gate tests: low-tier resolved cycles `<` standard on same policy default

**Acceptance Criteria:**
- Given a tracked spec with `declared_low_risk: true` and at most three changed files, when `marshal gate evaluate --story <key>` runs, then `data.review_depth.max_review_cycles` is strictly less than `data.review_depth.default_max_review_cycles` and at least 1
- Given the same repo with `declared_low_risk: false` or a wide diff, when gate evaluate runs for that story, then `review_depth.tier` is `"standard"` and resolved cycles equal the policy default
- Given no `--story`, when gate evaluate runs, then `review_depth` is absent from the envelope
- Given the bmad-build-auto spec template, when a new story spec is drafted, then `declared_low_risk: false` is present in frontmatter

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Harness/spin not wired — spec Never clause scopes gate evidence only; AC satisfied via envelope
  - `[false]` `[reject]` bmad-spec template unchanged — stories-schema documents the key; bmad-build-auto template is the producer
  - `[low]` `[patch]` Untracked new modules omitted from first diff — spec_low_risk.py and test_spec_low_risk.py included before HALT
  - `[false]` `[reject]` Missing integration with render_policy_toml — explicitly out of scope per intent-contract Never

## Auto Run Result

**Summary:** Added `declared_low_risk` story-spec frontmatter (template + parser), wired
`cli/gate.py` to gather `changed_files` and call `classify_review_tier` →
`resolve_review_cycles`, and record `review_depth` in the gate envelope. Tests prove low-tier
stories resolve fewer review cycles than standard-tier on the same policy default.

**Files changed:**
- `core/spec_low_risk.py` — `parse_declared_low_risk` producer
- `cli/gate.py` — `_gather_review_depth` + envelope/text render
- `.claude/skills/bmad-build-auto/spec-template.md` — default `declared_low_risk: false`
- `.claude/skills/bmad-spec/assets/stories-schema.md` — documents the key for materialized stories
- `tests/unit/test_spec_low_risk.py`, `tests/unit/test_cli.py` — parser + gate integration

**Verification:** `pyforge-marshal-test` — 7586 passed (full suite green).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -- tests/unit/test_spec_low_risk.py tests/unit/test_gate.py tests/unit/test_cli.py -k "review_depth or declared_low_risk or classify_review_tier or resolve_review_cycles"` — expected: all selected tests pass
