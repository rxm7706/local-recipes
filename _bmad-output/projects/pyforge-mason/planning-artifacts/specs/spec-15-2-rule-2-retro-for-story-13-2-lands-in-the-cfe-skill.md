---
title: 'Rule-2 retro for Story 13.2 lands in the CFE skill'
type: 'chore'
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

**Problem:** Story 13.2 (the `dbgpt-client` `sqlalchemy` upper-bound cap admitting Python 3.14)
shipped with its CLAUDE.md Rule-2 CFE retro **deferred** (tracked as `DW-13-2-1`) — mason's own
meta-test `test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested` fails
whenever `SKILL.md`/`CHANGELOG.md` change on a mason story branch, so the retro could not land
in-story. The 2026-09-08 re-verification confirmed it is **still unwritten**: the G26 extension
that did land (`SKILL.md:2454`) carries **Story 13.1's** `langflow-base` case study, not 13.2's,
and no 13.2 entry exists anywhere in `CHANGELOG.md` through v8.90.1. Per CLAUDE.md Rule 2, a
conda-forge effort is not "done" until its retro lands — this one has now been unwritten across
four CFE releases.

**Approach:** Run the retro against Story 13.2's actual evidence — the `dbgpt-client`
`sqlalchemy >=2.0.25,<2.0.29` cap, why the recipe run-dep loosen alone was insufficient, and which
upstream files the source patch had to touch for the wheel METADATA to agree (the G26 mechanism)
— and land it as a **maintenance PR on the CFE surface**, outside any mason story branch, so the
mason meta-test is satisfied by construction rather than worked around.

## Boundaries & Constraints

**Always:**
- Run this story through `conda-forge-expert` (CLAUDE.md Rule 1) — the whole story is CFE-surface
  work.
- Land the retro as a maintenance PR on the CFE surface, outside any mason story branch, so
  `test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested` is satisfied
  by construction.
- `CHANGELOG.md` carries a dated entry naming Story 13.2; `SKILL.md`'s G26 gains the
  `dbgpt-client` case study, distinct from 13.1's.
- Bump the skill version per semver: PATCH for a case-study/clarification, MINOR if a new gotcha
  or section falls out of this retro.
- `MANIFEST.yaml` + `config/skill-config.yaml` must agree with `SKILL.md`'s frontmatter `version:`
  — they have drifted apart before (v8.90.0 fixed exactly that).
- Regenerate `config/failure-catalog.yaml` if any gotcha text moved
  (`tests/meta/test_failure_catalog_freshness.py` guards it).
- Close `DW-13-2-1` with a dated resolution note, not another "verified: still-open" line.
- Mirror obligation (ratified OQ5 constraint / CAP-3 clause (b)): if this retro touches any script
  mirrored into a compiled slice, byte-re-port it and advance that slice's `brief_mirrored_through`
  in the same PR; verify whether a re-port is needed rather than assuming none, and keep
  `cfe-rebuild-guard-check` clean either way.

**Never:**
- Do not land the retro edit inside a mason story branch — that is precisely the condition this
  story exists to route around.
- Do not leave `DW-13-2-1` open with a repeated "still-open" verification line.
- This story **is** the Rule-2 retro; it does not spawn a further one (Rule 1/2 note in the epic).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Retro lands as maintenance PR | CFE skill files edited outside any mason story branch | `test_conda_forge_expert_not_replaced_or_skf_nested` is never triggered by this change (satisfied by construction) | N/A |
| G26 gains the 13.2 case study | `dbgpt-client` `sqlalchemy >=2.0.25,<2.0.29` cap evidence, upstream patch detail | `SKILL.md`'s G26 section gains a case study distinct from 13.1's `langflow-base` entry | N/A |
| Skill version bump | Retro is a case-study/clarification only, vs. a new gotcha/section falling out | PATCH bump in the former case; MINOR bump in the latter | `MANIFEST.yaml`/`skill-config.yaml`/`SKILL.md` frontmatter disagreement is a defect this story must avoid reintroducing (v8.90.0 precedent) |
| Failure catalog regeneration | Gotcha text moved during the retro edit | `config/failure-catalog.yaml` regenerated | `tests/meta/test_failure_catalog_freshness.py` reds if stale |
| `DW-13-2-1` closure | Ledger entry currently open (`severity: medium`, "still-open" history) | Dated resolution note added, entry closed | N/A |
| Mirror obligation | Retro touches a script mirrored into a compiled slice (`cfe-recipe-generation` / `cfe-recipe-lifecycle`) | Byte-re-port performed, `brief_mirrored_through` advanced, same PR | `pixi run -e local-recipes cfe-rebuild-guard-check` reds if left undone; a docs-only retro needs no re-port but that must be verified, not assumed |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/SKILL.md` — G26 section (currently ~line 2454, carrying
  Story 13.1's `langflow-base` case study) gains a second, distinct case study for Story 13.2's
  `dbgpt-client` `sqlalchemy` cap.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — new dated version entry naming Story 13.2
  (current head is v8.90.1).
- `.claude/skills/conda-forge-expert/MANIFEST.yaml`, `.claude/skills/conda-forge-expert/config/skill-config.yaml`
  — version bump to match `SKILL.md`'s frontmatter `version:` field.
- `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` — regenerate if any gotcha text
  moved as part of this retro.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` — close
  `DW-13-2-1` (currently ~line 1415) with a dated resolution note.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  (read/verify) — advance `brief_mirrored_through` for the affected compiled slice if the retro
  touches a mirrored script.
- `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` (read-only
  reference) — the meta-test whose in-story constraint motivates the maintenance-PR route.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-13-2-dbgpt-client-sqlalchemy-cap-admits-python-3-14.md`
  (read-only reference) — source evidence for the retro's technical content.

## Tasks & Acceptance

**Execution:**
- `[docs]` Write the G26 case-study addition to `SKILL.md` covering the `dbgpt-client` `sqlalchemy`
  cap mechanism, distinct from the existing 13.1 `langflow-base` entry.
- `[docs]` Add the dated `CHANGELOG.md` entry naming Story 13.2.
- `[chore]` Bump `MANIFEST.yaml` + `config/skill-config.yaml` version to match `SKILL.md`'s
  frontmatter, per the semver rule (PATCH vs. MINOR per whether a new gotcha/section fell out).
- `[chore]` Regenerate `config/failure-catalog.yaml` if any gotcha text moved.
- `[docs]` Close `DW-13-2-1` in `deferred-work-ledger.md` with a dated resolution note.
- `[chore]` Verify (and if needed perform) the mirror obligation: byte-re-port any touched script
  into its compiled slice, advance `brief_mirrored_through`, and confirm
  `cfe-rebuild-guard-check` stays clean.

**Acceptance Criteria:**
- Given Story 13.2 shipped with its Rule-2 CFE retro deferred (mason's own meta-test
  `test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested` fails when
  `SKILL.md`/`CHANGELOG.md` change on a story branch) and the 2026-09-08 re-verification confirmed
  it is still unwritten — the G26 extension that did land (`SKILL.md:2454`) carries Story 13.1's
  `langflow-base` case study, not 13.2's, and no 13.2 entry exists anywhere in `CHANGELOG.md`
  through v8.90.1.
- When the retro runs against Story 13.2's actual evidence — the `dbgpt-client` `sqlalchemy
  >=2.0.25,<2.0.29` cap, why the recipe run-dep loosen alone was insufficient, and which upstream
  files the source patch had to touch for the wheel METADATA to agree (the G26 mechanism) — and
  lands as a maintenance PR on the CFE surface, outside any mason story branch, so the meta-test is
  satisfied by construction.
- Then `CHANGELOG.md` carries a dated entry naming Story 13.2, `SKILL.md`'s G26 gains the
  `dbgpt-client` case study distinct from 13.1's, the skill version is bumped per semver (PATCH
  for a case-study/clarification, MINOR if a new gotcha or section falls out), `MANIFEST.yaml` +
  `config/skill-config.yaml` agree with `SKILL.md`'s frontmatter `version:` (they have drifted
  apart before — v8.90.0 fixed exactly that), `config/failure-catalog.yaml` is regenerated if any
  gotcha text moved (`tests/meta/test_failure_catalog_freshness.py` guards it), and `DW-13-2-1` is
  closed with a dated resolution note rather than another "verified: still-open" line.
- Rule 1/2: the whole story is CFE-surface work — it runs through `conda-forge-expert`, and it
  **is** the Rule-2 retro, so it does not spawn a further one.
- Mirror obligation: per the ratified OQ5 constraint / CAP-3 clause (b), if this retro touches any
  script mirrored into a compiled slice, byte-re-port it and advance that slice's
  `brief_mirrored_through` in the same PR; a docs-only retro needs no re-port, but verify that
  rather than assuming it, and keep `cfe-rebuild-guard-check` clean either way.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live across doctor's own Epic 21 backlog this session.

## Review Triage Log
