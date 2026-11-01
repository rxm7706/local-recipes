---
title: "113.2: the challenge policy block configures the challenger and absent means off"
type: 'feature'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_policy_block
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "the [challenge] block is ignored at policy composition and factory challenge refuses with the usage code"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/glossary.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - _bmad-output/policy-defaults.toml
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
---

<intent-contract>

## Intent

**Problem:** the operator's first condition is a configuration off-switch: nothing about the challenger may live in code or in a session, and a station must be able to turn it on per stage and off by deleting a block. Story 113.1's built-in default group is a stop-gap, not that switch.

**Approach:**
- The policy schema gains a `[challenge]` table: `enabled` (bool), `stages` (subset of `mint`, `decompose`, `readiness`, `drift`, `rules`), `reviewers` (per stage, persona names from the plugin's registered set), `model` (a `model_cost_catalog` key), `standards` (per stage, repo paths), `artifact_dir` (default `implementation-artifacts/egm`). It composes with the rest of the policy once (AD-10), is materialized and immutable for the run (AD-35), and an absent block or `enabled = false` leaves every stage off and every hook a no-op — exactly as `[context]` behaves at the front door (AD-50).
- The render refuses a `model` equal to the dispatching session's own model (operator answer 1: a different model, never the author's).
- The goldfish context rule is enforced at the spawn: a reviewer receives the target artifact, the station Spec's `glossary.md`, the Dream entry the artifact cites and the stage's standard (`CHAIN-STANDARD.md` plus the five-field shape for a Spec or `epics.md`; the story-spec template for a story spec), as absolute paths, and nothing else; every spawn asserts the adapter's `omitClaudeMd: true` and `tools: [Read, Grep, Glob]`. `structural`, `style` and EGM's own `document_standards/` are refused at render time.
- `_bmad-output/policy-defaults.toml` ships no block (off); `marshal-policy.toml` gains a comment documenting the shape and no block.

Ledger key: `113-2-the-challenge-policy-block-configures-the-challenger-and-absent-means-off`.
Type / Effort / Deps: feature / M / 113.1.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** — the capability this story realizes: the block, absent means off, the different-model refusal, the goldfish context rule.
- **CAP-298** — the verb the block configures (Story 113.1).
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3, Q4, Q6.

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_policy_block` is in `flags.json` (`defaultVariant: off`) and `flag-overlays.json` (`off` everywhere) with the clock fields; `test_flags.py` and `flag-inventory` name it against CAP-299.
- **AC2 — ON.** With the key on, a `[challenge]` block composes, materializes and drives Story 113.1's verb: stages, reviewers, model, standards and artifact folder come from the block; a reviewer spawn carries exactly the four context paths and asserts `omitClaudeMd: true` and the read-only tool list.
- **AC3 — Absent means off.** No block, or `enabled = false`, leaves every stage off and every hook (Stories 113.3–113.5) a no-op; a test pins the no-op against a composed policy without the block.
- **AC4 — Refusals at render.** `model` equal to the dispatching session's model, a `reviewers` entry naming `structural` or `style`, or a `standards` entry under EGM's `document_standards/`, refuses at policy render with the usage code and a reason.
- **AC5 — OFF.** With the key off the block is ignored at composition and `factory challenge` refuses with the usage code.
- **AC6 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`, `test_pyforge_marshal_egm_policy_block`); the same file pins AC3 and AC4.
- **AC7 — Defaults ship off.** `_bmad-output/policy-defaults.toml` carries no `[challenge]` block; `marshal-policy.toml` carries a documenting comment and no block. Checked at review, not by a live-tree test: a marshal test reading `_bmad-output/policy-defaults.toml` would need that path in `pyforge-station-tests.yml`'s marshal filters (steward's trigger-map check, 2026-11-01).

## Boundaries & Constraints

**Always:**
- Compose the block once with the rest of the policy; read it only from the materialized policy at run time.
- Pass context as absolute paths; assert the adapter's isolation on every spawn.

**Never:**
- Never let a block name `AGENTS.md`, `CLAUDE.md`, a memlog or a URL as context; never fall back to the author model; never ship a block in the repo default; never mint a new exit code.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299.

Parent: `spec-pyforge-marshal` CAP-299

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-2-the-challenge-policy-block-configures-the-challenger-and-absent-means-off`.
- Deps: 113.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.

**Run before the push:**
- Two-state flag coverage: `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — `@flag_states("pyforge.marshal.egm_policy_block")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.

## Auto Run Result

Status: done

Summary: built by hand in the single Epic 113 PR (2026-11-01, operator direction: one PR, the 113.1 dispatch stopped before any push); independently reviewed, review findings fixed.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger); operator answers 1 (different model) and 2 (plugin pin) bind here.
- 2026-11-01: built. The block's tests live in `tests/unit/test_factory_challenge.py` beside the verb's (one fixture repo for all six switches) instead of a separate `test_policy_challenge.py`; a model the catalog does not list is refused, including an empty catalog (review nit); `MEMORY.md` and `.claude/memory/` join the forbidden context (review S9); a station with no `glossary.md` yet runs with the glossary left out (review B2).

## Review Triage Log

- 2026-11-01: independent review (fresh subagent, read the diff against this spec) returned FAIL with blockers B1 (two named test files absent) and B2 (the audit refused six stations with no glossary) and should-fix S1-S11; every finding was fixed in the same PR except S7 (`marshal watch` display), recorded as DW-marshal-113-3-1. See the Spec memlog's 2026-11-01 review entry.
