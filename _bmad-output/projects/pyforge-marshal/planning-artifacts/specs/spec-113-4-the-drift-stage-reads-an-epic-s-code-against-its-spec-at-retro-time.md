---
title: "113.4: the drift stage reads an epic's code against its Spec at retro time"
type: 'feature'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_retro_drift
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "bmad-retrospective activates as before with no drift report; --stage drift refuses with the usage code"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - .claude/skills/bmad-retrospective/customize.toml
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
---

<intent-contract>

## Intent

**Problem:** `spec-surface` sees path and hash drift; `bmad-drift` sees the marshal planning docs. Nothing reads an epic's code against its story specs and its Spec's success lines for drift of meaning, and a retro's drift findings come from the implementer's summary.

**Approach:**
- `marshal factory challenge --stage drift --epic <n>` runs the `codebase-details` and `zoom-out` personas over the epic's story specs and the `src/` paths they name (the story specs' `Surface:` lines and `[epic_surfaces]`), and writes the report under Tier 3.
- `.claude/skills/bmad-retrospective/customize.toml` gains an activation step naming that verb, so a retro on a marshal epic cites the report as an input; the skill is customized through `bmad-customize`, never edited in place.
- The report is advisory; `spec-surface` and `bmad-drift` are unchanged.

Ledger key: `113-4-the-drift-stage-reads-an-epic-s-code-against-its-spec-at-retro-time`.
Type / Effort / Deps: feature / M / 113.1, 113.2.

### Living CAP citations

- **CAP-301** — the capability this story realizes.
- **CAP-298** / **CAP-299** — the verb and the block (Stories 113.1, 113.2).
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3, Q4, Q6.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_retro_drift` is in `flags.json` (`defaultVariant: off`) and `flag-overlays.json` (`off` everywhere) with the clock fields; `test_flags.py` and `flag-inventory` name it against CAP-301.
- **AC2 — ON.** With the key on, `--stage drift --epic <n>` resolves the epic's story specs and their named `src/` paths, spawns the two personas with those absolute paths, writes the report under Tier 3 and exits 0.
- **AC3 — The retro reads it.** `bmad-retrospective`'s customization names the verb as an activation step; a retro on a marshal epic cites the report path as an input.
- **AC4 — OFF.** With the key off `--stage drift` refuses with the usage code and the retro activation is unchanged.
- **AC5 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`), with the harness session stubbed.
- **AC6 — Unchanged detectors.** `spec-surface-check` and `bmad-drift-check` are byte-identical in behaviour; the report never enters a verdict.

## Boundaries & Constraints

**Always:**
- Resolve the epic's surface from the story specs and the policy, never from a guess; pass absolute paths.

**Never:**
- Never edit `bmad-retrospective`'s `SKILL.md` in place (the installer owns it); never make the report a gate; never write a ledger.

</intent-contract>

## Binding

- Parent capability: CAP-301.

Parent: CAP-301

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-4-the-drift-stage-reads-an-epic-s-code-against-its-spec-at-retro-time`.
- Deps: 113.1, 113.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.

**Run before the push:**
- Two-state flag coverage: `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — `@flag_states("pyforge.marshal.egm_retro_drift")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); operator answer 3 (all five stages in v1) binds here.

## Review Triage Log

- (none yet)
