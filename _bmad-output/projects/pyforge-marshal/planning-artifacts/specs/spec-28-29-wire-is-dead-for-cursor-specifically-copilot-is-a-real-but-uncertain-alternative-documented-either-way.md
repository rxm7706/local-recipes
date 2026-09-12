---
title: 'Wire is dead for cursor specifically — copilot is a real but uncertain alternative, documented either way'
type: 'docs'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `resolve_wire_wrap` reports the same generic `"harness profile 'cursor' declares no [wrapper]"` message for every unwrapped profile, which reads as an oversight for `cursor` specifically — an operator would reasonably expect a `[wrapper]` section could just be added. Live-verified 2026-09-10 (`headroom wrap cursor --help`): headroom's cursor support is Cursor-IDE-only — it prints proxy base URLs for a human to paste into Cursor's Settings UI ("Manual setup" in headroom's own compatibility table), never an env-var-driven headless wrap. Marshal's dispatch fleet launches the headless `cursor-agent` CLI detached with no GUI at all — there is no reachable path, full stop, not a configuration gap.

**Approach:** Name the real, permanent cause explicitly in `resolve_wire_wrap`'s reason for `profile.name == "cursor"` specifically, and annotate `cursor.toml`'s own `[wrapper]`-absence with a comment citing this finding, so a future harness-profile author does not attempt to add one. Record `copilot` as the one other genuinely headless wrap target among marshal's five harness profiles (`headroom wrap copilot` starts a real proxy + launches, no GUI dependency) as a documented operator decision point — not silently pursued (the wrap-composition logic assumes claude's simple argv-prefix shape and copilot's BYOK routing flags would need real adaptation) or silently dropped (`copilot.toml`'s own `notes` already record a live 2026-08-27 quota failure on this machine — switching is a different spend to manage, not a free lunch).

## Boundaries & Constraints

**Always:** Every other unwrapped profile keeps the exact original generic message, byte-for-byte — this is additive for `cursor` only. State the copilot alternative as a recorded decision point, not this story's own call.

**Never:** Attempt to make copilot marshal's default harness in this story — that is a separate, larger, human-authorized effort given the wrap-composition rework and quota uncertainty. Silently drop the copilot finding — it must be documented, not just implicitly ruled out.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CURSOR_WIRE_ENABLED | `wire` layer on, `cursor` profile | `wire.reason` names the structural cause explicitly | N/A |
| OTHER_PROFILE_UNWRAPPED | `wire` layer on, any non-cursor profile with no `[wrapper]` | Original generic message, unchanged | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` — `resolve_wire_wrap`'s `wrapper is None` branch, cursor-specific detail
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml` — new comment citing this story

## Tasks & Acceptance

**Execution:**
- `core/harness_profile.py` — cursor-specific reason branch — docs
- `cursor.toml` — annotating comment — docs
- `tests/unit/test_harness_profile.py` — 1 new test proving the cursor-specific message

**Acceptance Criteria:**
- Given a station whose `harness_preference` resolves to `cursor`, when a dispatch session launches, then `wire.reason` names the structural cause explicitly rather than the generic message
- Given `cursor.toml`, when read, then its `[wrapper]`-absence carries a comment citing this story
- Given the copilot alternative, when documented, then it is recorded as an operator decision point (quota history + wrap-composition rework cost named), never silently pursued or silently dropped

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** `wire.reason` now names cursor's real, permanent, live-verified cause instead of the generic "declares no [wrapper]" wording; every other profile's message is unchanged. `cursor.toml` carries a comment recording both the cause and the copilot alternative's real cost/risk, so a future harness-profile author (or operator considering the switch) does not have to re-derive either finding from scratch.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` — cursor-specific `wire.reason` branch
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml` — annotating comment
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py` — 1 new test
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — 28-29 → done

**Review:** Implementation verified directly against the spec's own I/O matrix; no separate review-loop pass for this docs-scoped fix.

**Verification:** `pyforge-marshal-test` → 7704 passed (combined with 28.30's changes; both landed together).

**Residual risks:** None for the documentation itself. The copilot alternative remains genuinely unimplemented and unscheduled — this story deliberately stops at "recorded, evidence-based, operator decision point," not a go/no-go call or a follow-on story filing (the operator has not asked for one).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py -v` — expected: 89 passed
