---
title: SKF domain skill and BMAD persona for herald
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
review_loop_iteration: 0
followup_review_recommended: false
deferred: []
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Herald has no station-owned SKF skill or bmad-agent-herald.

**Approach:** SKF from src/shared/packages/pyforge-herald/ if missing. Persona uses only pyforge herald … and POST /stations/herald/mcp. Lane 1 CMS stays steward. No CFE replace. No CLAUDE/AGENTS export.

## Acceptance Criteria

- Given steward 29 proved the shape, when this story completes, then .claude/skills/pyforge-herald/ exists with provenance.
- Given bmad-agent-herald, when it completes a station task, then only grammar + MCP appear in the transcript.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-herald/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-herald` only — never `scripts/bmad-switch`. Ledger key `17-1-skf-skill-and-persona-for-herald`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B deck-status portal. Absorbing Lane 1 CMS. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-herald/`
- `.claude/skills/bmad-agent-herald/`
- `src/shared/packages/pyforge-herald/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 17.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` `test_context_files_not_hand_edited` now also asserts `git diff origin/main` is empty for CLAUDE.md and AGENTS.md

## Auto Run Result

Status: done

Summary: SKF Quick skill `.claude/skills/pyforge-herald/` compiled from `src/shared/packages/pyforge-herald/` with provenance. BMAD launcher `bmad-agent-herald` consults that skill and may only emit `pyforge herald …` and `POST /stations/herald/mcp`. Golden deck-status transcript plus station-owned contract tests fail on filesystem or ad-hoc HTTP freelance. Persona is not SKF-compiled. CFE untouched. No `pyforge.*` under `src/platform/`. Lane 1 CMS stays steward. 17.2 not started.

Files:
- `.claude/skills/pyforge-herald/` — version-nested SKF content skill + brief + `active` pointer
- `.claude/skills/bmad-agent-herald/` — launcher SKILL.md, customize.toml, golden transcript
- `src/shared/packages/pyforge-herald/tests/meta/test_skf_skill_and_persona.py` — station AC gates
- `planning-artifacts/specs/spec-17-1-….md` — tracked story spec

Review: 1 low patch applied; follow-up score 1 → false.

Verification: 16 passed (`test_skf_skill_and_persona`); SKF frontmatter/output PASS; platform/CFE/CLAUDE/AGENTS diffs empty.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
