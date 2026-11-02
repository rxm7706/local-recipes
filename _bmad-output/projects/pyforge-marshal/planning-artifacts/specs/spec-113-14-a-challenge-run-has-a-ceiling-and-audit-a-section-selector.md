---
title: "113.14: a challenge run has a ceiling, and --audit a section selector"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
---

<intent-contract>

## Intent

**Problem:** a challenge run has no configured ceiling on time or size. Line numbers are at `03a7aff5d9`.

- The only bound is `_DEFAULT_TIMEOUT_S = 3600.0`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py:31`, read at `:120`). The
  Constraint "every hard limit is expressed as configuration" (`SPEC.md:1161`) forbids a hard-coded limit, and the
  dispatch readiness hook, synchronous by CAP-300's choice, waits on it for up to an hour before launch (EGM audit
  MAR-M-D6).
- Targets and the Dream context are whole files with no selector. `audit_plan`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:484-498`) hands reviewers whole `SPEC.md`
  and `epics.md` files and the whole Dream; marshal's `epics.md` alone is 1,030,449 bytes, more than one reviewer's
  context, so an automated sweep cannot review it (MAR-E4). The 2026-11-01 audit ran by hand on slices for this reason.

**Approach (operator ruling 2026-11-01: `--audit` reviews each station's newest CAP slice and its epic range; story specs
are left to the readiness stage; L effort, parked at backlog):**
- **The ceiling.** `[challenge].timeout_s`, a per-stage map with a short `readiness` default, joins
  `CHALLENGE_BLOCK_KEYS` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:69-71`) and
  `ChallengeConfig`; `ClaudeChallengeRunner` reads it in place of `_DEFAULT_TIMEOUT_S`. A turn cap joins the challenge
  argv if the claude profile supports one. A run past its timeout is unevaluable (exit 1), never a hang.
- **The selector.** A section selector (a Dream heading, a CAP range or an epic range) extracts a slice into a Tier-3
  target the way `write_drift_target` does, for `--target` and for the Dream context path.
- **The audit plan.** `audit_plan` reviews each station's newest CAP slice (mint) and the epic range that decomposes it
  (decompose) across the whole fleet, as ruled; story specs stay with the readiness stage.
- **The contract follows the code.** The memlog events for MAR-M-D6 and MAR-E4 and the operator's decision are already on
  `spec-pyforge-marshal` (commit `7dde4a0202`). Re-derive CAP-298, CAP-299 and CAP-302 with `bmad-spec` to name the
  ceiling and the selector, anchored on CAP-299's intent ("nothing about the challenger lives in code") and on
  `SPEC.md:1159` and `:1161`; CAP-300 records that the synchronous readiness wait is bounded by `timeout_s`. Then the
  cascade re-stamp and the scoped stamp.
- **After this story.** The first automated `marshal factory challenge --audit` runs only after this story lands
  (operator ruling 2026-11-01).
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the block is read only while
  `pyforge.marshal.egm_policy_block` is on, and `--audit` stays behind `pyforge.marshal.egm_audit`.

Ledger key: `113-14-a-challenge-run-has-a-ceiling-and-audit-a-section-selector`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-298** (FR-240): every challenge run; its ceiling.
- **CAP-299** (FR-241): the `[challenge]` block gains `timeout_s`.
- **CAP-302** (FR-244): the audit sweep's plan and selector.
- **CAP-300** (FR-242): re-derived text only (the bounded readiness wait).
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL9: MAR-M-D6, MAR-E4); the operator's ruling of 2026-11-01 on the audit scope.

## Acceptance Criteria

- **AC1 — The ceiling is configuration.** A `[challenge]` block with `timeout_s` validates and composes; the runner's
  timeout for a stage is the block's value, else the per-stage default (a short `readiness` default); no literal
  `3600` remains in `adapters/challenge_harness.py`
  (`src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py`).
- **AC2 — A timeout is unevaluable.** A stubbed session that outlives its timeout is killed and the verb exits 1 with
  outcome `error`; in dispatch the readiness hook reports `MRS-DISP-067` and the launch proceeds.
- **AC3 — The selector.** A Dream heading, a CAP range (`CAP-298..CAP-303`) and an epic range each slice into a Tier-3
  target file holding exactly that section, for `--target` and for the Dream context
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC4 — The audit plan.** On a fixture fleet, `audit_plan` targets each station's newest CAP slice and its epic range,
  never a whole `SPEC.md`, `epics.md` or Dream, and no story spec.
- **AC5 — The contract.** CAP-298, CAP-299, CAP-300 and CAP-302 read as the Approach states, re-derived by `bmad-spec`
  (both self-validate passes logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check`
  exit 0.
- **AC6 — Mutation.** Restoring the literal 3600 timeout fails AC1's test; returning whole files from `audit_plan` fails
  AC4's. Restore each.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Write slices only under Tier 3 (`implementation-artifacts/egm/`); pass them as absolute paths.

**Ask first:**
- The default per-stage timeouts, and how "newest CAP slice" is chosen when a station's newest Dream entry spans more
  than one Spec.

**Never:**
- Never let a challenge block a dispatch past its configured ceiling; never review a story spec in `--audit`; never
  hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-298 (FR-240).
- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).
- Parent capability: `spec-pyforge-marshal` CAP-302 (FR-244).

Parent: `spec-pyforge-marshal` CAP-298, CAP-299 and CAP-302 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL9).
- Epic: Epic 113.
- Ledger key: `113-14-a-challenge-run-has-a-ceiling-and-audit-a-section-selector`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` and the re-derived `SPEC.md`; within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); parked at `backlog` outside the Story 113.7 landing PR
  (operator ruling 2026-11-01: L effort).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: backlog

Summary: not yet dispatched; parked at backlog by the operator's ruling of 2026-11-01.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL9: MAR-M-D6, MAR-E4)
  and the operator's ruling of 2026-11-01 (`--audit` scope is each station's newest CAP slice and its epic range; story
  specs left to readiness; L effort, parked at backlog). `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
