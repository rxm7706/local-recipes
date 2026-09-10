---
title: '`CONSTITUTIVE` is derived from the roster, not hardcoded beside it'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: 'eb339e189e2e10e5d001d91ca25775a205ec34e9'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `chain.py:96` hardcodes `CONSTITUTIVE = frozenset({"pyforge-charter"})`
while the same module already resolves statuses, types, and stations from
`docs/governance/guild-roster.json` through `_load_dream_roster` (`:838-852`), and the
roster carries the authoritative `guild_dreams` list. `CONSTITUTIVE` is the last
unguarded mirror of a constitutional constant that the roster consolidation was
introduced to eliminate — a second constant beside the roster's own list, changeable
independently of it.

**Approach:** Derive `CONSTITUTIVE` from the roster's `guild_dreams` key the same way
the other three constants (statuses, types, stations) are already derived, rather than
declaring it as a separate hardcoded literal. The gate at `:634` is unchanged in
behavior for today's single-entry roster. A roster carrying a second `guild_dreams`
entry is honored without a code edit. An unreadable or absent roster degrades to
today's value (`{"pyforge-charter"}`) with a named warn, rather than silently
producing an empty set.

## Boundaries & Constraints

**Always:**
- `CONSTITUTIVE` is derived from the roster's `guild_dreams` key, using the same
  `_load_dream_roster` mechanism the other three constants already use.
- The gate at `chain.py:634` is unchanged in behavior for today's single-entry roster
  (`{"pyforge-charter"}`).
- A roster carrying a second (or more) `guild_dreams` entry is honored without any
  further code edit.
- An unreadable or absent roster degrades to today's hardcoded value
  (`{"pyforge-charter"}`) with a **named warn**, never a silent empty set.

**Never:**
- Never leave `CONSTITUTIVE` as an independently-declared literal beside the roster —
  it must be derived, not declared, matching the "derive, don't declare" rule the
  roster consolidation exists to enforce.
- Never let a roster read failure produce an empty `CONSTITUTIVE` set silently — that
  would make the constitutive gate vanish without any signal.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Today's roster (single entry) | `guild-roster.json` `guild_dreams: ["pyforge-charter"]` | `CONSTITUTIVE == {"pyforge-charter"}`, gate at `:634` behaves identically to today | n/a |
| Roster gains a second entry | `guild_dreams` carries two slugs | Both are honored as constitutive, no code edit needed | n/a |
| Roster unreadable/absent | `guild-roster.json` missing or malformed | Degrades to `{"pyforge-charter"}` | Named warn, not silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `CONSTITUTIVE` (`:96`), the gate at `:634`, and `_load_dream_roster` (`:838-852`).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain.py` — tests for the derived constant and the degrade-on-unreadable-roster path.

## Tasks & Acceptance

**Execution:**
- `fix` — replace the hardcoded `CONSTITUTIVE = frozenset({"pyforge-charter"})` literal with a value derived from the roster's `guild_dreams` key via `_load_dream_roster`, mirroring the other three derived constants.
- `feature` — add the named-warn degrade path for an unreadable/absent roster, falling back to `{"pyforge-charter"}`.
- `feature` — add/extend tests covering today's single-entry roster (behavior-identical gate), a roster with a second entry (honored without code change), and the degrade path.

**Acceptance Criteria:**
- Given `chain.py:96` hardcodes `CONSTITUTIVE` while the module already resolves statuses, types, and stations from the roster, when `CONSTITUTIVE` is derived from that roster key the way the other three constants are, then the last unguarded mirror of a constitutional constant is gone.
- The gate at `:634` is unchanged in behavior for today's single-entry roster.
- A roster carrying a second `guild_dreams` entry is honored without a code edit.
- An unreadable/absent roster degrades to today's value with a named warn rather than an empty set.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 3, maybe-false 0
- findings:
  - `[low]` `[reject]` Duplicate `_write_roster` helper in `test_sources_chain.py` and `test_sources_chain_dream_chain.py` — cosmetic duplication only; extracting a shared fixture module adds scope beyond this story.
  - `[false]` `[reject]` `_CONSTITUTIVE_FALLBACK` is still a hardcoded frozenset beside the roster — spec explicitly requires degrade-to-`{"pyforge-charter"}` on roster failure; this is the documented fallback, not a parallel source of truth.
  - `[false]` `[reject]` Constitutive roster warn is skipped when no guild-owned dreams are collected — without guild-owned dreams the INV-2a gate is vacuous; warn fires whenever the gate is evaluated and the roster is unreadable (verified by new tests).
  - `[false]` `[reject]` Verification gap for live-repo `gather_dream_chain` without tmp roster — production repo always ships `docs/governance/guild-roster.json`; tmp tests cover degrade path explicitly.

## Auto Run Result

Status: done

**Summary:** Replaced module-level `CONSTITUTIVE` with roster-derived `_load_constitutive()`, extended `_load_dream_roster()` to parse `guild_dreams`, and added unit tests for single-entry roster, second entry, and degrade-with-named-warn paths.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — derive constitutive slugs from roster; named WARN + fallback on failure
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain.py` — Story 21.4 matrix tests (new)
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` — roster fixture for guild governance collection test
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-21-4-constitutive-is-derived-from-the-roster-not-hardcoded-beside-it.md` — build-auto metadata

**Review:** 0 patches applied; 0 deferred; 4 findings rejected (see triage log).

**Follow-up review recommendation:** false

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1555 passed, 1 skipped.

**Residual risks:** `_CONSTITUTIVE_FALLBACK` must stay aligned with the Charter's documented single-entry roster if that value ever changes; that is intentional degrade behavior, not drift.

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
