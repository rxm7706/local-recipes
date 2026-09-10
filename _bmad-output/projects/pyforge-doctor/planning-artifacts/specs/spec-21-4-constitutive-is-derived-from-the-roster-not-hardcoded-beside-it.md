---
title: '`CONSTITUTIVE` is derived from the roster, not hardcoded beside it'
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

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
