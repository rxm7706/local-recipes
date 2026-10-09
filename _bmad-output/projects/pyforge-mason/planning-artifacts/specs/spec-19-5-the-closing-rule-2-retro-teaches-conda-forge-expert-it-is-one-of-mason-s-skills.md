---
title: "19.5: The closing Rule-2 retro teaches conda-forge-expert it is one of Mason's skills"
type: 'retro'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '21141248ca34e25bfa366ffd403644639831a108'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-15-2-rule-2-retro-for-story-13-2-lands-in-the-cfe-skill.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Epic 19 is a conda-forge effort — it gives Mason its own skills and moves two feedstock campaigns out of
`docs/how-to/` — and every conda-forge effort closes with a retro that edits `conda-forge-expert` and its `CHANGELOG.md`
with a semver bump (CLAUDE.md Rule 2; FR-47; the operator's ruling of 2026-09-28 restates it). CFE itself does not yet know
it is one of Mason's skills: a recipe task that starts in CFE has no pointer to Mason's grammar or to the campaign skills,
and CFE's `guides/feedstock-platform-expansion.md` does not name the skill that now parameterizes it.

**Approach:** run the retrospective over Epic 19 (Stories 19.1–19.4) against the CFE skill, with `conda-forge-expert`
invoked first, and land its findings in one `retro(cfe): …` commit that touches only the CFE surface:
- `.claude/skills/conda-forge-expert/SKILL.md` gains a short pointer: Mason's station skill `pyforge-mason` routes recipe
  work here; `mason-package` and `mason-environment` cover the crafts Mason builds natively; the feedstock campaigns run
  as `mason-feedstock-platform-expansion` and `mason-feedstock-failure-remediation`. No gotcha or procedure moves out of CFE.
- `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md` names `mason-feedstock-platform-expansion` as
  its parameterized runner.
- `CHANGELOG.md` gains a dated entry at the next minor version naming Epic 19 — and says existing guidance held for
  anything else the retro checked; `MANIFEST.yaml` and `config/skill-config.yaml` carry the version;
  `config/failure-catalog.yaml` is regenerated only if the generator says it must be.

Ledger key: `19-5-the-closing-rule-2-retro-teaches-conda-forge-expert-it-is-one-of-mason-s-skills`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: retro / S / S-19.4.

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (FR-51); CAP-26 (the self-improvement loop); FR-47 (the closing Rule-2 retrospective); AD-15.

## Acceptance Criteria

- Given Epic 19's four stories on `main` When the retro commit lands Then its subject starts `retro(cfe):`, it touches only `.claude/skills/conda-forge-expert/**` (and the CFE surface's generated catalog, if regenerated), and `CHANGELOG.md` gains a dated entry whose version is one minor above the prior one
- Given CFE's `SKILL.md` and `guides/feedstock-platform-expansion.md` When they are read Then they name the five Mason skills by path and hold every gotcha and procedure they held before
- Given `test_persona_consults_cfe.py`'s sanctioned-retro check When the mason suite runs Then the CFE edit is sanctioned (its commit moves `CHANGELOG.md`)
- Given the CFE suite When it runs Then it passes

## Boundaries & Constraints

**Always:**
- One dedicated `retro(cfe):` commit, never bundled with a mason `src/` change (mason CAP-7's governance check).
- A retro with no other finding still writes its CHANGELOG entry.

**Never:**
- Do not demote CFE, move a gotcha out of it, or mark it superseded; do not SKF-compile or version-nest it.
- Do not touch `src/shared/packages/pyforge-mason/**` or any Mason skill in the retro commit.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no new finding | retro finds nothing else | a "guidance held" CHANGELOG entry, still a minor bump | — |
| catalog | a gotcha title moved | `failure-catalog.yaml` regenerated in the same commit | `failure-catalog-check` fails otherwise |
| bundled commit | retro edits + mason `src/` | refused by review | mason governance meta-test fails |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-29 (FR-51).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them*.
Ledger key: `19-5-the-closing-rule-2-retro-teaches-conda-forge-expert-it-is-one-of-mason-s-skills`.
Ledger status at mint: `backlog`.
Deps: S-19.4.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; the sanctioned-retro check runs inside it).

**Manual checks:**
- `pixi run -e local-recipes test-ci` — expected: pass (the CFE suite).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (the CFE changelog sentinel, failure catalog and rebuild guard run inside it).

## Review Triage Log
