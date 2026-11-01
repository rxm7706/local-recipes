---
title: "113.12: each stage names its standard, and decompose reads its Spec's capability range"
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
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - .claude/skills/bmad-spec/assets/spec-template.md
  - .claude/skills/bmad-build-auto/spec-template.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
---

<intent-contract>

## Intent

**Problem:** the goldfish context rule never separates target from context, decompose never sees the Spec it
decomposes, and the reviewer roster, stage groups and standards exist only in code. Line numbers are at `03a7aff5d9`.

- `default_standards` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:249-254`) gives mint,
  decompose and rules only `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`. A decompose reviewer reads
  `epics.md`, the station Dream, `CHAIN-STANDARD.md` and a glossary when one exists, never the `SPEC.md` whose CAP range
  the stories claim (EGM audit MAR-E2). Mint never receives the `bmad-spec` template, though CAP-299 names "the
  five-field shape" (MAR-M-C2, MAR-D-R1).
- The code already exempts the target from the context rule (`context_violations`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:238-255`), gives the repo-rules targets
  `AGENTS.md` and `CHAIN-STANDARD.md` the Dream `docs/dreams/one-chain-per-station.md` plus marshal's glossary, gives a
  station `SKILL.md` its whole station Dream (`cli/challenge.py:268-270`, `:486-495`), and omits a missing
  `glossary.md` (six of eight stations have none). CAP-299 still says "exactly four paths" and "never `AGENTS.md`", and
  no memlog line records the exemption (MAR-M-Z2, MAR-D-R4).
- dcc71b22c0 settled the per-stage reviewer groups (`DEFAULT_REVIEWERS`, `core/challenge.py:36-42`), never spawns
  `egm:egm-synthesizer` (absent from `REVIEWER_PERSONAS`, `:29-31`; the orchestrator session assembles `report.json`)
  and chose the default standards. CAP-298 and CAP-299 still name the synthesizer, "as the stage selects" and an unnamed
  "five-field shape" (cluster MAR-CL1: MAR-M-Z1, MAR-D-C2, MAR-D-R1, MAR-M-C2). The Epic 113 story text is corrected by
  append-only notes at mint (Stories 113.1 and 113.2); the code, re-derive and Dream steps of MAR-CL1 ride this story.

**Approach:**
- **The standards.** `default_standards("decompose")` returns `CHAIN-STANDARD.md` and the station `SPEC.md`
  (`spec_path(root, slug)`); `default_standards("mint")` adds `.claude/skills/bmad-spec/assets/spec-template.md` (the
  five-field shape), for mint only and never for decompose. Readiness keeps
  `.claude/skills/bmad-build-auto/spec-template.md`, drift the station `SPEC.md`, rules `CHAIN-STANDARD.md`.
- **The contract follows the code.** The memlog events for every finding above are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`). Re-derive CAP-298, CAP-299 and CAP-301 with `bmad-spec` (`BMAD_ACTIVE_PROJECT=pyforge-marshal`,
  `PYTHONPATH=$PWD/_bmad/scripts`):
  - CAP-298 lists five reviewer agents and no synthesizer, and names the orchestrator session as the report assembler.
  - CAP-299 gets a five-stage table (reviewers, standards) that cites `DEFAULT_REVIEWERS` and `default_standards` as
    fallbacks a `[challenge]` block overrides, reconciled with its intent "nothing about the challenger lives in code";
    the context rule binds context and never the target; a repo-rules target takes `docs/dreams/one-chain-per-station.md`
    plus marshal's glossary, and a station `SKILL.md` target its whole station Dream; the glossary is "`glossary.md` when
    present"; `--target` is optional with `--epic` and `--audit`.
  - CAP-301's drift success form gains `--project`, which `_bmad/custom/bmad-retrospective.toml` already passes.
- **The Dream.** `docs/dreams/pyforge-marshal.md` § *Realization log* gains dated lines: the synthesizer was dropped and
  the orchestrator took its role (beside the 2026-11-01 audit entry; the operator's table at `:13766` untouched), and
  the goldfish-context bullet (`:13780-13785`) as built, the bullet's own text left as written.
- Then the cascade re-stamp (`updated:` on `prds/prd-pyforge-marshal-2026-07-25/prd.md`,
  `architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md` and `epics.md`), `git add`, and
  `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-marshal` (plus each
  co-governor the detector names).
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the verb stays behind `pyforge.marshal.egm_challenge`.

Ledger key: `113-12-each-stage-names-its-standard-and-decompose-reads-its-spec-s-capability-range`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the block, its stage groups, standards and the goldfish context rule.
- **CAP-298** (FR-240) and **CAP-301** (FR-243): re-derived text only (the roster; the drift success form).
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL2: MAR-M-Z2, MAR-D-R4, MAR-E2; cluster MAR-CL1: MAR-M-Z1, MAR-D-C2, MAR-D-R1, MAR-M-C2; MAR-E2 and
  MAR-M-Z2 contested and settled in the cluster).

## Acceptance Criteria

- **AC1 — Decompose reads its Spec.** `default_standards(root, slug, "decompose")` returns `CHAIN-STANDARD.md` and
  `spec_path(root, slug)`, and a decompose run's context carries the station `SPEC.md`
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — Mint reads the template.** `default_standards(root, slug, "mint")` returns `CHAIN-STANDARD.md` and
  `.claude/skills/bmad-spec/assets/spec-template.md`; decompose never carries the template.
- **AC3 — The other stages are unchanged.** Readiness, drift and rules return what they return today; one test pins all
  five stages.
- **AC4 — The contract.** CAP-298, CAP-299 and CAP-301 read as the Approach states, re-derived by `bmad-spec` (both
  self-validate passes logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC5 — The Dream.** The Realization log carries the two dated lines; no existing Dream bullet or table changes;
  `dream-chain-check` and `dreams-hygiene-check` exit 0.
- **AC6 — Mutation.** Dropping `spec_path` from decompose's standards fails AC1's test. Restore it.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Keep `DEFAULT_REVIEWERS` and `default_standards` as fallbacks a `[challenge]` block overrides.

**Ask first:**
- Any change to a stage's reviewer group, or passing the whole `SPEC.md` where a CAP-range slice would do (the selector
  is Story 113.14's).

**Never:**
- Never pass `AGENTS.md`, `CLAUDE.md`, a memlog or session text as context; never hand-edit `SPEC.md`; never rewrite a
  Dream bullet.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL2,
  MAR-CL1).
- Epic: Epic 113.
- Ledger key: `113-12-each-stage-names-its-standard-and-decompose-reads-its-spec-s-capability-range`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`, the re-derived `SPEC.md` and
  `docs/dreams/pyforge-marshal.md` (Realization log lines only); within `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-guild dream-chain-check` and `pixi run --frozen -e pyforge-guild dreams-hygiene-check` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL2: MAR-M-Z2, MAR-D-R4,
  MAR-E2; with the code, re-derive and Dream steps of cluster MAR-CL1) at the operator's ruling of 2026-11-01 (implement
  in the Story 113.7 landing PR). The Story 113.1 and 113.2 text is corrected by append-only notes at mint. `type: fix`,
  no flag, no CAP.

## Review Triage Log

- (none yet)
