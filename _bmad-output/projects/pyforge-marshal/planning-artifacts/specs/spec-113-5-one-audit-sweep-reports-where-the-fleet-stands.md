---
title: "113.5: one audit sweep reports where the fleet stands"
type: 'feature'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_audit
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "marshal factory challenge --audit refuses with the usage code; single-target stages are unaffected"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - AGENTS.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
---

<intent-contract>

## Intent

**Problem:** the operator's third condition is a one-time audit over the existing stations, the repo rules and the current state — where the fleet stands before any new chain is minted. Single-target stages cannot say that; a sweep can.

**Approach:**
- `marshal factory challenge --audit` runs the `rules` stage over `AGENTS.md`, `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` and every `.claude/skills/pyforge-<station>/SKILL.md`, and the `mint` and `decompose` stages over every station's `docs/dreams/pyforge-<station>.md`, `specs/spec-pyforge-<station>/SPEC.md` and `epics.md`, each target with its own goldfish context (CAP-299).
- One fleet report and one report per station land under Tier 3 `implementation-artifacts/egm/audit-<date>/`; the verb exits 0.
- Nothing tracked changes from the sweep. The durable residue — one `planning-artifacts/research/egm-audit-<date>.md` per station and a memlog entry per accepted finding, landed in the PR that acts on them — is Story 113.7's.
- The sweep runs the stations sequentially and the reviewers within a stage in parallel, so the cost is bounded and the journal is readable.

Ledger key: `113-5-one-audit-sweep-reports-where-the-fleet-stands`.
Type / Effort / Deps: feature / M / 113.1, 113.2.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-302** — the capability this story realizes.
- **CAP-298** / **CAP-299** — the verb and the block (Stories 113.1, 113.2).
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3, Q4, Q6.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_audit` is in `flags.json` (`defaultVariant: off`) and `flag-overlays.json` (`off` everywhere) with the clock fields; `test_flags.py` and `flag-inventory` name it against CAP-302.
- **AC2 — ON.** With the key on, `--audit` resolves the rules targets and the eight stations' Dream, Spec and `epics.md`, runs the three stages, writes one fleet report and eight station reports under Tier 3, journals the sweep, and exits 0.
- **AC3 — Nothing tracked moves.** `git status` is clean after a sweep; a test pins it on a fixture fleet.
- **AC4 — OFF.** With the key off `--audit` refuses with the usage code; single-target stages are unaffected.
- **AC5 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`) on a fixture fleet with the harness session stubbed.
- **AC6 — Resumable.** A target whose report already exists under the same `audit-<date>/` is skipped unless `--force`, and the audit journal names each skip; a corrupt existing report is re-run, never a crash.

## Boundaries & Constraints

**Always:**
- Pass each target with its own station glossary and Dream entry; run stations sequentially, reviewers within a stage in parallel.

**Never:**
- Never write under `planning-artifacts/` from the sweep; never make a report a gate; never run `egm-bootstrap`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-302.

Parent: `spec-pyforge-marshal` CAP-302

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-5-one-audit-sweep-reports-where-the-fleet-stands`.
- Deps: 113.1, 113.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.

**Run before the push:**
- Two-state flag coverage: `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — `@flag_states("pyforge.marshal.egm_audit")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: done

Summary: built by hand in the single Epic 113 PR (2026-11-01, operator direction: one PR, the 113.1 dispatch stopped before any push); independently reviewed, review findings fixed.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); the operator's audit condition binds here.
- 2026-11-01: built. The sweep writes one JSON report per target, one Markdown summary per station and `fleet.md`; it is resumable per target (review S8); stations with no `glossary.md` yet (six of eight on 2026-11-01) run with the glossary left out instead of being refused (review B2).
- 2026-11-01: amended in place, append-only (operator ruling 2026-11-01; EGM audit MAR-E1, MAR-D-C1, `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`): SKF compiles each station skill to `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md`, which `station_skill_path` reads first, with the flat path as a fallback (Approach bullet 1 trails it; Story 113.11 re-derives CAP-302 and FR-244); `epics.md` Story 113.5's Then carries the same dated note. No AC body, status or key moved.

## Review Triage Log

- 2026-11-01: independent review (fresh subagent, read the diff against this spec) returned FAIL with blockers B1 (two named test files absent) and B2 (the audit refused six stations with no glossary) and should-fix S1-S11; every finding was fixed in the same PR except S7 (`marshal watch` display), recorded as DW-marshal-113-3-1. See the Spec memlog's 2026-11-01 review entry.
