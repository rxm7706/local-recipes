---
title: '23.1: The SKF managed block lives in `AGENTS.md` only'
type: 'config'
created: '2026-09-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - .claude/skills/skf-export-skill/assets/managed-section-format.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_bmad/skf/config.yaml` lists `ides: [claude-code, other]`; `skf-export-skill` maps `claude-code` to `CLAUDE.md` and `other` to `AGENTS.md`, so its 54-line managed block is in both. Claude Code loads both files every session (`instructionFiles=claude-md-and-agents-md`), so every session pays for the block twice.

**Approach:** Set `ides: [other]` so the export targets `AGENTS.md` only, and remove the block from `CLAUDE.md` so the export's orphan check finds nothing. Move the one line only `CLAUDE.md`'s copy carried into the notes file.

## Boundaries & Constraints

**Always:**
- `skills_output_folder` and `snippet_skill_root_override` stay `.claude/skills`; snippet `root:` paths keep pointing at the real skill directories.
- `AGENTS.md`'s SKF block is unchanged; its content is `skf-export-skill`'s.
- `CLAUDE.md` keeps its bare `@AGENTS.md` import.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then a scoped `--write-baseline --spec` per named Spec; re-run the check and read its exit code.

**Never:**
- Do not hand-edit the SKF block in `AGENTS.md`.
- Do not change `skills_output_folder`, `snippet_skill_root_override` or `forge_data_folder`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| managed-section check, `CLAUDE.md` | `skf-rebuild-managed-sections.py CLAUDE.md check` | `has_managed_section: false` | fail loud |
| managed-section check, `AGENTS.md` | `skf-rebuild-managed-sections.py AGENTS.md check` | `has_managed_section: true`, `markers_valid: true` | fail loud |
| next export | `ides: [other]` | targets `AGENTS.md` only; no orphaned-context prompt | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-27`.
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-26 — The instruction surface loads once, and says what runs it*.
Ledger key: `23-1-the-skf-managed-block-lives-in-agents-md-only`.
Ledger status at mint: `backlog`.

## Epic excerpt

**Type:** config • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-27
**Surface:** `_bmad/skf/config.yaml` (`ides`, and its comment); `CLAUDE.md` (the SKF block removed); `docs/reference/agent-instruction-notes.md` (the one line only `CLAUDE.md`'s copy carried, moved verbatim).
**Given** `_bmad/skf/config.yaml` lists `ides: [claude-code, other]`, which `skf-export-skill` maps to `CLAUDE.md` and `AGENTS.md`, and Claude Code loads both files every session under `instructionFiles=claude-md-and-agents-md`
**When** this story lands
**Then** `ides` is `[other]`, so the export targets `AGENTS.md` only; `CLAUDE.md` has no `<!-- SKF:BEGIN` / `<!-- SKF:END -->` markers, so the export's orphan check has nothing to ask about; `AGENTS.md`'s SKF block is unchanged; the line only `CLAUDE.md`'s copy carried (Mason has no SKF skill) lands in the notes file, its rule already in `AGENTS.md` § Policy
**And** `skf-rebuild-managed-sections.py <file> check` reports `CLAUDE.md` without a managed section and `AGENTS.md` with valid markers; the seven station SKF meta-tests and scribe's parity tests pass; `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `python .claude/skills/shared/scripts/skf-rebuild-managed-sections.py CLAUDE.md check` — expected: `has_managed_section: false`.
- `python .claude/skills/shared/scripts/skf-rebuild-managed-sections.py AGENTS.md check` — expected: `has_managed_section: true`, `markers_valid: true`.

**Manual checks:**
- The seven station SKF meta-tests (`test_skf_*` under atlas, doctor, herald, marshal, steward, warden, scribe) pass.

## Outcome

Done 2026-09-26, in an interactive session.

- `_bmad/skf/config.yaml`: `ides` changed from `[claude-code, other]` to `[other]`, and the comment says why and asks for a re-apply after an installer regeneration. `skills_output_folder` and `snippet_skill_root_override` are unchanged.
- `CLAUDE.md` dropped its SKF block, 124 → 66 lines. A guarded script removed it:
  - It asserted that every other line of the block is already in `AGENTS.md`'s copy.
  - One line was not: "Mason is the eighth PyForge Guild station but deliberately has no SKF skill". It moved verbatim to `docs/reference/agent-instruction-notes.md`; its rule stands in `AGENTS.md` § Policy.
  - The `governance-currency:ignore` marker that wrapped that line was dropped with it, since the notes file is not a governed document.
- `skf-rebuild-managed-sections.py` reports `CLAUDE.md` with no managed section, and `AGENTS.md` with valid markers (52 lines).
- Every station's SKF meta-tests pass in its own environment: atlas 16, herald 16, marshal 7, steward 20 (with the adoption register), warden 6, doctor 6, scribe 39 (with the parity and navigation tests). CFE's retired-ID test passes (9).
- `governance-currency` and `bmad-drift-check` exit 0; `bmad-drift-check` reports no `spec-unindexed` finding. `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`: 398 passed, 11 skipped.
- An `_bmad` installer regeneration can reset `ides`; the config comment records the re-apply.
- The operator noted on 2026-09-26 that the Mason line itself should eventually change: Mason should have its own skills, with conda-forge-expert one of them. That restructure is out of scope here; it is captured in team memory for a Dream entry on Mason's chain.
