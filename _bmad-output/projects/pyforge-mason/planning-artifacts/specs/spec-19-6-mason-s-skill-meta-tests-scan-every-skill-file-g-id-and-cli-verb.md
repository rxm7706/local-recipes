---
title: "19.6: Mason's skill meta-tests scan every skill file, G-id and CLI verb"
type: 'fix'
created: '2026-11-01'
status: 'done'
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

Status: done

Summary: implemented 2026-11-01 in the EGM landing worktree (branch `egm-audit-2026-11`), tests only plus one
two-token pointer repair; nothing committed.

**What changed**

- `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` (AC1-AC4): `mason_skill_files()` reads every
  `*.md` under the four hand-authored skills (with `references/`) and
  `.claude/skills/pyforge-mason/active/pyforge-mason/`. `skill_file_violations()` reds three things, each naming the
  file (and line for a heading or a G-id): a gotcha heading at any level (`#{1,6} G<n>[a-z]?.`); a cited G-id (a
  `G31–G34` range expands, and a letter suffix such as `G8b` is its own id, never `G8`) with no `### G<n>.` heading in
  `.claude/skills/conda-forge-expert/SKILL.md`; and a CFE `**Fix**` prose sentence of 60 or more characters copied
  verbatim, which is the spec's "copied fix text" (fenced code is skipped, and a shorter gist passes).
  `test_skill_tier_scan_is_not_vacuous` plants each one in a `references/worked-examples.md` under `tmp_path`, and
  checks that `- **G95** (BCTB block, see CFE) — …` passes. `pointer_violation()` requires a Markdown link to
  `.claude/skills/<skill>/SKILL.md` in both how-tos and both `archive/docs/specs/` stubs. The test is parametrised
  over the four files, and a stripped copy proves the check reds. The Story 19.2 checks are unchanged.
- `src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py` (AC5): `registered_verbs(build_parser())`
  walks the argparse tree. All 12 `recipe`/`package`/`environment` verbs must appear as `"<noun> <verb>"` in the
  station `SKILL.md`, and the failure message names `skf-update-skill` from `skill-brief.yaml` as the remedy. A
  `planted-verb` added to the live parser reds the check.
- `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` (AC6, AC7): `skf_block_violations()`
  checks for a `[SKF Skills]|<n> skills|<n> stack` header, a `|[pyforge-mason v…]|root: .claude/skills/pyforge-mason/`
  entry and a `|[<station> v` entry for each of the other seven stations. It pins no count and no version (the old
  `|[<station> v0.1.0]|` loop had the same problem as the mason literal, so it was loosened too). A 9-skill block with
  mason at `v0.2.0` passes, and a block without the mason entry fails. `notes_name_mason_as_skf_skill()` requires
  `` `pyforge-mason` `` in `docs/reference/agent-instruction-notes.md` § *SKF skills block*, and fails when that name
  is replaced.
- `.claude/skills/mason-feedstock-platform-expansion/SKILL.md` (lines 286 and 522): **one deviation, for review.**
  The spec's probe said no G-id dangles. The new AC2 check found that `G8b` does: CFE has never had a `### G8b.`
  heading (`git log -S` traces it to the CFE v8.23.0 guide, where it meant step 8's `get_build_summary`
  false-negative caveat), and the old probe read `G8b` as `G8`. Both citations now read `G85` ("A native
  `trigger_build` reports 'No build summary found' even on SUCCESS — confirm from the `.conda` artifact"), the gotcha
  their gist describes. The gist text is unchanged and the pointer stays a pointer. I read the boundary "never rewrite
  a gotcha pointer that carries a one-line gist" as protecting gist pointers from the restatement rule, not as
  forbidding the repair of a dangling id. If the reviewer reads it literally, the alternative is to block the story
  on AC2/AC8. The same dangling `G8b` remains at `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md:295,543`.
  That is CFE surface, outside this story's boundary, and needs a `retro(cfe):` follow-up.
- Spec memlog: two events. The first is the surface reconcile naming the three test paths and the skill file. The
  second states CAP-29's new success behaviour for `mason-c01`'s `bmad-spec` re-derive.

**Not touched:** `.claude/skills/pyforge-mason/**` (all 12 verbs are already present, so no SKF regeneration was
needed), `AGENTS.md`, any CFE path, any `SPEC.md` or ledger.

**Commands run (exit codes)**

- Before the G8b repair: `pixi run --frozen -e pyforge-mason pytest …/tests/meta/test_mason_skills.py -q` gave exit 1
  (the new dangling-G-id check named `G8b` at `mason-feedstock-platform-expansion/SKILL.md:286`). After the repair it
  passes.
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py -q`
  exited 0 (39 passed).
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` exited 0 (1656 + 2 + 12 passed, about 25 s, full suite).
- `ruff check` exited 0 and `ruff format --check` exited 0 on the three test files. Both ran from the package dir with
  `.pixi/envs/pyforge-guild/bin/ruff`, because the `ruff` task is not defined in `pyforge-mason`. One import-order
  fix was applied by `ruff check --fix`.
- `mypy -p pyforge.mason` from the package dir (the lint-types slice, `pyforge-guild` mypy) exited 0. Tests are
  outside lint-types' mypy scope.
- Not run here (the session owner's landing steps): full-scope `pr-preflight`, `spec-surface-check`, and the scoped
  stamps.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), findings MAS-M-Z4 and MAS-M-D5, cluster
  `mason-c06-skill-metatests`; fix under `spec-pyforge-mason` CAP-29, no new CAP, no flag.
- 2026-11-01 (dev): the dangling-G-id check (AC2) found that `G8b` is cited by
  `.claude/skills/mason-feedstock-platform-expansion/SKILL.md`, contradicting the Intent's "no dangling G-id" probe.
  The two citations were repointed to `G85`, keeping the gist. The CFE guide's own `G8b` is left for a CFE retro.

## Review Triage Log

### 2026-11-01 — Review pass (reviewer: independent session)

- Verdict: **pass**. Every AC holds, with evidence observed in this review. Failures: none. One deviation is accepted
  (see the first item under "Deviation and observations").
- What was checked (every verdict read from the exit code):
  - AC 1: `mason_skill_files()` was probed on the live tree. It scans 8 files: the four hand-authored `SKILL.md`, both
    `references/worked-examples.md`, and the station skill's `SKILL.md` and `context-snippet.md` (through
    `active/`). A planted `## G1.` heading in a `references/` file under tmp is reported with its file and line, so
    any heading level is caught.
  - AC 2: run against HEAD's `.claude/skills/mason-feedstock-platform-expansion/SKILL.md`,
    `skill_file_violations` reports `SKILL.md:286: cites G8b, which has no '### G8b.' heading`. The check is real,
    and it would have failed the tree before the repair. CFE defines 123 G-ids, including G85; it does not define
    G8b.
  - AC 3: `test_skill_tier_scan_is_not_vacuous` plants a heading, a dangling `G999`, a `G8b` suffix and a copied
    G85 fix sentence, each in a `references/` file under `tmp_path`. Each one fails the check. The pointer
    `**G95** (BCTB block, see CFE)` passes.
  - AC 4: `test_campaign_how_to_and_stub_link_their_skill` covers both how-tos and both `archive/docs/specs/`
    stubs, and passes. The stripped-copy test proves that the check reds when the link is removed.
  - AC 5: `registered_verbs(build_parser())` returns 12 pairs. All 12 appear in the station `SKILL.md`. A planted
    `recipe planted-verb` is reported as missing.
  - AC 6: `skf_block_violations` returns `[]` on the live `AGENTS.md` block. It also returns `[]` for a 9-skill block
    with mason at `v0.2.0`. When the mason entry is removed, it names the missing entry. The literals `8 skills` and
    `v0.1.0` are gone.
  - AC 7: `notes_name_mason_as_skf_skill` holds on the live notes and fails when `` `pyforge-mason` `` is replaced.
  - AC 8: the three meta files exit 0 (39 passed), and `pyforge-mason-test` exits 0 (1656 + 2 + 12 passed).
  - Always boundary: the Story 19.2 checks in `test_mason_skills.py` are unchanged, because the diff only adds.
  - Lint and checks: `ruff check` and `ruff format --check` on the three test files (package config) exit 0.
    `spec-surface-check` (read-only) exit 0. `docs-skills-catalog -- --check` exit 0, so the skill edit leaves the
    catalog current.
  - Nothing else runs these test files: no pixi task, workflow or script other than the mason suite.
  - `.claude/skills/pyforge-mason/**`, `AGENTS.md` and every CFE-surface path are untouched. `.claude/skills/mason-*`
    is not CFE surface (`scripts/mason_cfe_surface_check.py`).
- Deviation and observations:
  - **Accepted: `G8b` became `G85` in `.claude/skills/mason-feedstock-platform-expansion/SKILL.md:286,522`.** This
    file is outside the story's Surface, and "tests only" did not foresee it. The Intent's probe was wrong: it read
    `G8b` as `G8`. As a result, AC 2 and AC 8 could not both hold without this repair. The Never clause ("Rewrite a
    gotcha pointer that carries a one-line gist") is read here as a ban on rewriting gist pointers to satisfy the
    restatement rule. The repair stays inside that reading:
    - the gist text is unchanged, and the line is still a pointer;
    - the id now resolves to the gotcha its gist describes, since CFE G85's Symptom and Fix are the native
      `get_build_summary` "status: unknown" false negative, confirmed from the `.conda` artifact;
    - the change is recorded in the Spec Change Log and the memlog;
    - the file is in no Spec's surface (baseline count 0);
    - no CFE gotcha moved.
  - Follow-up for the session owner (named blocker: this story's Never clause on CFE surface):
    `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md:295,543` still cites the dangling `G8b`.
    It needs a CFE-skill change with a `retro(cfe):` commit and a CHANGELOG entry. Record it as a deferred-work row,
    so that it does not live only in this spec.
  - Observation, not a failure: `pointer_violation` matches a link whose *text* names
    `.claude/skills/<skill>/SKILL.md`. Its target is not checked: the live links point at the skill directory on
    GitHub. This matches the live convention, but a wrong target with the right text would pass.
  - Not run here: the full-scope `pr-preflight` (a manual check). Other agents are editing other stations in this
    worktree, and the one-preflight-per-machine rule applies. It stays with the session owner, together with the
    scoped stamps and the ledger promotion.

## Dev Notes

- Review follow-up 2026-11-01 (station-tests routing): steward's trigger map
  (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`) derives five reads this story's
  tests added, and `mason_paths` in `.github/workflows/pyforge-station-tests.yml` carried none of them:
  `archive/docs/specs/feedstock-failure-remediation.md`, `archive/docs/specs/feedstock-platform-expansion.md`,
  `docs/how-to/feedstock-failure-remediation.md` and `docs/how-to/feedstock-platform-expansion.md` (`CAMPAIGN_POINTERS`
  in `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py`), and
  `docs/reference/agent-instruction-notes.md` (`NOTES_MD` in
  `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py`). The array now carries all five, so an
  edit to any of them runs `mason-test`. The tests and their assertions are unchanged; the meta-test exits 0.
