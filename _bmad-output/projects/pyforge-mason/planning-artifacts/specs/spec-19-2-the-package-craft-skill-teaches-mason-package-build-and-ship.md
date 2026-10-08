---
title: "19.2: The package craft skill teaches mason package build and ship"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '8a2da2c010aec6578d6b6546a321affac249bb1d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-19-1-mason-s-station-skill-is-skf-compiled-exported-and-consulted-by-the-persona.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `mason package build` and `mason package ship` are the craft Mason built natively because nothing existed to
wrap (CAP-3): one manifest to wheel, sdist and conda artifact, then one pass to PyPI, a conda channel and conda-forge,
with a receipt that says which targets are done and which are queued. How to drive it — the target vocabulary, the
dry-run default, the TestPyPI rehearsal that gates the irreversible PyPI publish, the credential check before anything is
built — lives only in the PRD and the CLI's help. The operator ruled on 2026-09-28 that it becomes a Mason skill
(`spec-pyforge-mason` CAP-29, question 2b).

**Approach:** author `.claude/skills/mason-package/SKILL.md` (and `references/` only if the body needs it) with
bmad-builder's `bmad-workflow-builder` — bmad-builder is wielded by mason for skill authoring (adoption register row 7).
It is a hand-authored operating-procedure skill (canopy:AD-17's exception kind), not SKF output. The skill walks:
`pyforge mason package build` (artifacts from one manifest, paths reported, nothing uploaded), then
`pyforge mason package ship --to <targets>` over the four targets `pypi-test`, `pypi`, `channel:<name>` and `conda-forge`
— dry-run by default and `--yes` to confirm; a `pypi-test` target requested with `pypi` runs first and gates it (FR-50);
a missing credential is found before any artifact is built; one target's failure never stops the others; a repeat
conda-forge ship reports `pending` with the open PR. The `conda-forge` target goes through the recipe port, so the skill
links `.claude/skills/conda-forge-expert/SKILL.md` for everything about the recipe and its submission and restates none of
it. It links the station skill `pyforge-mason` (Story 19.1) for the full grammar.

A new mason meta-test, `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py`, reads a declared table of
Mason's hand-authored skills (this story adds `mason-package`; 19.3 and 19.4 extend it) and asserts for each: the
`SKILL.md` exists with `name:` and `description:` frontmatter, names the `mason` verbs it teaches, links
`.claude/skills/conda-forge-expert/`, and carries no CFE gotcha heading (a line matching `^### G\d+\.`, the form of
`conda-forge-expert/SKILL.md`'s gotchas); a planted gotcha heading in a temporary copy proves the check is not vacuous.
`docs/reference/skills-catalog.md` is regenerated and `docs/reference/agent-instruction-notes.md` § *Skill Reference*
gains one row.

Ledger key: `19-2-the-package-craft-skill-teaches-mason-package-build-and-ship`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-19.1.

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (FR-51); CAP-3 (the dual-ship motion); FR-50 (rehearsal before an irreversible publish); AD-1; canopy:AD-17.

## Acceptance Criteria

- Given `.claude/skills/mason-package/SKILL.md` When it is read Then its frontmatter carries `name: mason-package` and a `description:`, and its body names `pyforge mason package build`, `pyforge mason package ship`, the four targets, `--yes`, and the `pypi-test` gate before `pypi`
- Given the `conda-forge` target When the skill describes it Then it links `.claude/skills/conda-forge-expert/SKILL.md` and restates no recipe or submission procedure
- Given `test_mason_skills.py` When it runs Then it passes for `mason-package`, and fails on a temporary copy with a planted `### G99. …` heading
- Given `docs/reference/skills-catalog.md` When `docs-skills-catalog -- --check` runs Then it exits 0

## Boundaries & Constraints

**Always:**
- Grammar is written `pyforge mason …`; the skill documents what the CLI does today (read `cli.py` and `package.py`), and
  a behaviour the CLI lacks is not promised.
- Recipe and submission knowledge stays in CFE and is linked, never copied.

**Never:**
- Do not change Mason's code (`src/shared/packages/pyforge-mason/src/**`) or the CFE surface (AD-15).
- Do not SKF-compile this skill or nest it under `.claude/skills/pyforge-mason/` (the SKF package is Story 19.1's).
- Do not run a real `ship` (no upload, no PR) to write the skill.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| skill read | `mason-package/SKILL.md` | verbs, targets, `--yes`, rehearsal gate | missing item fails the meta-test |
| gotcha copied | a `### G<n>.` heading in the skill | meta-test fails naming the file and line | — |
| no CFE link | skill lacks `.claude/skills/conda-forge-expert/` | meta-test fails | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-29 (FR-51).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them*.
Ledger key: `19-2-the-package-craft-skill-teaches-mason-package-build-and-ship`.
Ledger status at mint: `backlog`.
Deps: S-19.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; `test_mason_skills.py` runs inside it).

**Manual checks:**
- `pixi run -e pyforge-guild docs-skills-catalog -- --check` — expected: exit 0 after regeneration.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.

## Review Triage Log
