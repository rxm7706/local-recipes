---
title: "19.6: Mason's skill meta-tests scan every skill file, G-id and CLI verb"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-19-1-mason-s-station-skill-is-skf-compiled-exported-and-consulted-by-the-persona.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-19-4-the-two-feedstock-campaigns-become-mason-skills.md
  - src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py
  - src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py
  - src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py
  - .claude/skills/conda-forge-expert/SKILL.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-29 says no Mason skill restates a CFE gotcha, that each campaign how-to and its legacy stub point at
its skill, and that the station skill documents the whole `mason` grammar. Only part of that is checked:

- `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` reads the four hand-authored `SKILL.md` files,
  and only for a `### G<n>.` heading. It never reads their `references/*.md` (where the campaign skills' worked
  examples cite gotchas in prose) or the station skill under `.claude/skills/pyforge-mason/active/pyforge-mason/`, and
  it never checks that a cited G-id exists in CFE.
- Nothing asserts that `docs/how-to/feedstock-platform-expansion.md`, `docs/how-to/feedstock-failure-remediation.md`
  and their archived stubs (`archive/docs/specs/feedstock-platform-expansion.md`,
  `archive/docs/specs/feedstock-failure-remediation.md`) link their skill.
- Nothing compares the station skill against the verbs `build_parser()` registers.
- `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py:401-402` pins the literals
  `[SKF Skills]|8 skills|0 stack` and `[pyforge-mason v0.1.0]`, so a ninth SKF skill or a re-export at a new version
  fails a mason test for a change that is not Mason's.

Every one of these holds at `03a7aff5d9` (probed 2026-11-01: no `### G<n>.` heading and no dangling G-id in any
of the eight `*.md` files; all four pointers link their skill; all 12 verbs appear in the station `SKILL.md`). The
gap is that nothing reds a regression.

Found by the EGM fleet audit of 2026-11-01 (marshal Story 113.7): **MAS-M-Z4** (the "no restated gotcha" rule is
checked by one heading regex over four files) and **MAS-M-D5** (CAP-29's clauses are not machine-checkable, and the
`8 skills` literal is fragile), cluster `mason-c06-skill-metatests`. Residue:
`_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** widen the mason meta-tests to the whole skill tier, tests only.

- **Restated gotcha.** A restated gotcha is a `### G<n>.` heading or copied fix text. A G-id cited with a one-line gist
  is a pointer and passes (so `.claude/skills/mason-feedstock-failure-remediation/references/worked-examples.md:40-48`
  stays as it is).
- **Dangling G-id.** Every G-id a Mason skill cites resolves to a `### G<n>.` heading in
  `.claude/skills/conda-forge-expert/SKILL.md`.
- **Pointers.** Each how-to and its archived stub links its skill.
- **Grammar.** Every verb `build_parser()` registers appears in the station `SKILL.md`. If one ever does not, the skill
  is regenerated with `skf-update-skill` from `.claude/skills/pyforge-mason/skill-brief.yaml`, never hand-edited.
- **SKF block.** The persona test requires a `[pyforge-mason v` entry, not a literal count or version. `AGENTS.md`'s SKF
  block is `skf-export-skill`'s to write and this story does not touch it.
- **Notes.** `docs/reference/agent-instruction-notes.md` names `pyforge-mason` as an SKF skill; the old deletion clause
  becomes this positive check.

CAP-29's success is re-derived to name these checks by `bmad-spec` in the landing PR (cluster `mason-c01`'s run); that
re-derive is not this story's, and this story mints no CAP.

Ledger key: `19-6-mason-s-skill-meta-tests-scan-every-skill-file-g-id-and-cli-verb`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.
Mode: in the EGM landing PR (marshal Story 113.7).

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (Mason has its own skills, and `conda-forge-expert` is one of them), FR-51: "no Mason
  skill restates a CFE gotcha or recipe workflow"; the how-to and its stub point at the skill; the station skill
  documents the `mason` grammar.
- No new CAP. `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag.
- canopy:AD-17: the station skill is SKF-compiled; its text moves only through SKF.

## Acceptance Criteria

1. **Every skill file is read.** Given every `*.md` under `.claude/skills/mason-package/`,
   `.claude/skills/mason-environment/`, `.claude/skills/mason-feedstock-platform-expansion/`,
   `.claude/skills/mason-feedstock-failure-remediation/` and `.claude/skills/pyforge-mason/active/pyforge-mason/`, When
   `test_mason_skills.py` runs, Then a `### G<n>.` heading in any of them fails the test, naming the file and line.
2. **No dangling G-id.** Given the same files, When the test runs, Then every `G<n>` they cite has a `### G<n>.` heading
   in `.claude/skills/conda-forge-expert/SKILL.md`; a cited G-id without one fails the test, naming it.
3. **Not vacuous.** A planted `### G<n>.` heading and a planted dangling G-id, each in a `references/` file under
   `tmp_path`, fail the checks; a G-id cited with a one-line gist passes.
4. **Pointers.** `docs/how-to/feedstock-platform-expansion.md`, `docs/how-to/feedstock-failure-remediation.md`,
   `archive/docs/specs/feedstock-platform-expansion.md` and `archive/docs/specs/feedstock-failure-remediation.md` each
   link `.claude/skills/<their skill>/SKILL.md`; a test asserts all four.
5. **Grammar coverage.** `test_skf_mason_skill.py` asserts every verb `build_parser()` registers under `recipe`,
   `package` and `environment` (12 at `03a7aff5d9`) appears in
   `.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md`; a planted missing verb fails it.
6. **No fragile literal.** `test_persona_consults_cfe.py` requires a `[pyforge-mason v` entry rooted at
   `.claude/skills/pyforge-mason/` in `AGENTS.md`'s SKF block, not `8 skills` or `v0.1.0`.
7. **Notes check.** A test asserts `docs/reference/agent-instruction-notes.md` names `pyforge-mason` as an SKF skill.
8. **Green.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes, and every new check passes on the live
   tree at the branch head.

## Boundaries & Constraints

**Always:**

- Read every verdict from the exit code, never through a pipe.
- Keep the existing checks (each skill exists, names its verbs, links CFE; CFE is hand-authored and not
  version-nested) as they are.

**Never:**

- Hand-edit `.claude/skills/pyforge-mason/**` or `AGENTS.md`'s SKF block; regenerate through `skf-update-skill` /
  `skf-export-skill` if a check finds a real gap.
- Rewrite a gotcha pointer that carries a one-line gist, or move any CFE gotcha.
- Touch any CFE-surface path, so there is no `retro(cfe):` commit; hand-edit any `SPEC.md` or
  `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| heading in a reference file | `### G95.` in `references/worked-examples.md` | test fails, names file and line | — |
| dangling G-id | `G999` cited, no `### G999.` in CFE | test fails, names `G999` | — |
| pointer with gist | `G95 (BCTB block, see CFE)` | passes | — |
| how-to loses its link | pointer line removed | test fails, names the how-to | — |
| verb missing from the station skill | a parser verb absent from `SKILL.md` | test fails, names the verb | regenerate via SKF |
| ninth SKF skill exported | `9 skills` in the block | persona test passes | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-mason` CAP-29 (Mason has its own skills, and `conda-forge-expert` is one of them),
  FR-51. A fix, no new CAP.

Parent: CAP-29

- Dream: `docs/dreams/pyforge-mason.md` § Realization log, the 2026-11-01 entry (the EGM fleet audit).
- Audit findings carried: MAS-M-Z4, MAS-M-D5 (cluster `mason-c06-skill-metatests`); residue
  `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 19 (Mason has its own skills), done; a new not-done story reopens it (doctor Story 41.5).
- Ledger key: `19-6-mason-s-skill-meta-tests-scan-every-skill-file-g-id-and-cli-verb`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py`,
  `src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py`,
  `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py`; `.claude/skills/pyforge-mason/**` only
  through `skf-update-skill` if a verb is missing.
- Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
- Minted 2026-11-01 by marshal Story 113.7's landing PR, on the operator's acceptance of the audit's recommendations.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py -q`
  — expected: pass, with the new checks among them.

**Manual checks:**

- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after scoped stamps of `spec-pyforge-mason` and
  every co-governor it names.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), findings MAS-M-Z4 and MAS-M-D5, cluster
  `mason-c06-skill-metatests`; fix under `spec-pyforge-mason` CAP-29, no new CAP, no flag.

## Review Triage Log

- (none yet)
