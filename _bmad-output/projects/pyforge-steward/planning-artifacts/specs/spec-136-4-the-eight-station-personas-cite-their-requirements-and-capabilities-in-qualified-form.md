---
title: '136.4: The eight station personas cite their requirements and capabilities in qualified form'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 136-4-the-eight-station-personas-cite-their-requirements-and-capabilities-in-qualified-form
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.claude/skills/bmad-agent-*/SKILL.md'
  - '.claude/skills/bmad-agent-*/customize.toml'
  - 'src/shared/packages/pyforge-*/tests/meta/test_station_persona.py'
  - 'src/shared/packages/pyforge-*/tests/meta/test_skf_skill_and_persona.py'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_steward_persona.py'
  - 'src/shared/packages/pyforge-*/tests/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-cutover-2026-11-10-10`. The eight `bmad-agent-<station>` personas cite `FR-13`, `FR-11`, `CAP-15` and `CAP-16` bare. They are canopy:FR-13, canopy:FR-11, spec-pyforge-unifying-strategy:CAP-15 and spec-pyforge-unifying-strategy:CAP-16; a station's own PRD and Spec number their own FR-13 and CAP-15. Persona contract tests in each station's suite pin the wording.

**Approach:** Qualify the four ids in the eight `SKILL.md` files and their `customize.toml`, and in whatever template or generator writes a persona if one exists, then move the persona contract tests of each suite to the qualified wording in the same change. Change nothing else a persona says. The compiled `pyforge-<station>` skills are not edited by hand: where one cites the bare form it is left for its own regeneration and named in the story's change log.

Ledger key: `136-4-the-eight-station-personas-cite-their-requirements-and-capabilities-in-qualified-form`.

### Living CAP citations

- spec-pyforge-unifying-strategy CAP-16 (every station can be addressed as a persona) and CAP-15 (realized, no text change); CHAIN-STANDARD section 0 (the `canopy:` prefix); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a compiled `pyforge-<station>` skill.
- Never change what a persona may do.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-10` reports that all eight station personas cite `FR-13`, `FR-11`, `CAP-15` and `CAP-16` unqualified and that each suite's persona test pins the wording
**When** the four ids are qualified in the eight personas, their `customize.toml` and the template, and each suite's persona test asserts the qualified form
**Then** no persona `SKILL.md` or `customize.toml` cites one of the four ids bare, every persona contract test passes, and a test fails when a persona cites one bare again
**And** no other persona line changes, no compiled `pyforge-<station>` skill is hand-edited, and the row reads resolved

- **AC1 — No bare id is left in a persona.** Expected: prints 0.

  ```bash
  grep -h -o -w -E '.{0,34}(FR-13|FR-11|CAP-15|CAP-16)' .claude/skills/bmad-agent-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/SKILL.md .claude/skills/bmad-agent-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/customize.toml | grep -c -v -E '(canopy:|spec-pyforge-unifying-strategy:)(FR-13|FR-11|CAP-15|CAP-16)$'
  ```

- **AC2 — The persona tests of the Guild stations hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py src/shared/packages/pyforge-steward/tests/meta/test_steward_persona.py src/shared/packages/pyforge-doctor/tests/meta/test_station_persona.py src/shared/packages/pyforge-marshal/tests/meta/test_station_persona.py src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py -q --import-mode=importlib
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-unifying-strategy CAP-16 (every station can be addressed as a persona) and CAP-15 (realized, no text change); CHAIN-STANDARD section 0 (the `canopy:` prefix); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-4-the-eight-station-personas-cite-their-requirements-and-capabilities-in-qualified-form`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-10`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: reproduced on the unchanged tree: AC1's command printed 146 (146 bare citations of the four ids across the sixteen persona files; `bmad-agent-mason/customize.toml` cites none, `bmad-agent-mason/SKILL.md` one), and nine persona test modules pinned the heading `Allowed actions (CAP-16)`.
- 2026-11-25: no persona template or generator exists (searched `scripts/`, `_bmad/`, `src/`, `.claude/scripts/` for the persona wording); the sixteen files are hand-kept, so there was none to change.
- 2026-11-25: implemented. The four ids are qualified in fifteen persona files (118 lines, id tokens only; `canopy:FR-13`, `canopy:FR-11`, `spec-pyforge-unifying-strategy:CAP-15`, `spec-pyforge-unifying-strategy:CAP-16`). The nine persona test modules (steward's two, doctor, marshal, scribe, warden `test_station_persona.py`; atlas and herald `test_skf_skill_and_persona.py`; mason `test_persona_consults_cfe.py`) pin the qualified heading. `pyforge-steward/tests/meta/test_steward_persona.py` gains `test_every_station_persona_cites_the_four_ids_in_qualified_form` over all eight personas, with two tests of its matcher. The tests' own docstrings and error messages still say the ids bare; they are not persona wording and were left.
- 2026-11-25: AC1 prints 0 (the pipeline's exit code is 1, because `grep -c` exits 1 on a count of 0). AC2 as written exits 2 before and after this change: pytest's default import mode refuses four files named `test_station_persona.py` in one invocation ("import file mismatch"). The same five modules pass run one per invocation (14, 20, 15, 13, 14 passed) and together with `--import-mode=importlib` (76 passed, exit 0). The AC's command needs that flag or one invocation per module; not edited here.
- 2026-11-25: also green, each by exit code: herald and mason persona modules (`-e pyforge-guild`), atlas (`-e pyforge-atlas`), warden (`-e pyforge-warden`), `governance-currency`. `lint-types` exits 1 on one leg only, mypy over `pyforge-atlas` (`src/pyforge/atlas/observability.py:419`, a file another change in this worktree is editing, outside this story's surface); every ruff and ruff-format leg, over all nine test modules this story touches, is ok. Re-run it once that file settles.
- 2026-11-25: compiled station skills and briefs that still cite one of the four ids bare, left for their own regeneration: `.claude/skills/pyforge-{atlas,doctor,herald,marshal,scribe,warden}/skill-brief.yaml`; `pyforge-atlas/0.1.0`, `pyforge-doctor/{0.1.0,0.1.1,0.1.2}`, `pyforge-marshal/{0.1.0,0.1.1}`, `pyforge-warden/0.1.0` (each `<version>/pyforge-<station>/SKILL.md`).
- 2026-11-25: not done by this implementer, left to the landing: the memlog surface reconciles and scoped stamps, the deferred-work row `DW-steward-cutover-2026-11-10-10`, and the ledger.
- 2026-11-25: session lead: AC2 gains `--import-mode=importlib`, since pytest refuses four modules of one basename in one run otherwise; AC1's count is the verdict (`grep -c` exits 1 on a count of 0). The comment the story added to `test_steward_persona.py` named two of the ids bare and reddened steward's `test_cap_citations.py`; reworded, that module exits 0.
