---
title: SKF domain skill and BMAD persona for steward
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
review_loop_iteration: 0
followup_review_recommended: false
deferred: []
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Steward 29 proved SKF+persona on scribe. Steward itself still lacks pyforge-steward skill and bmad-agent-steward.

**Approach:** SKF from src/shared/packages/pyforge-steward/ with provenance. Persona consults that skill; only pyforge steward … and POST /stations/steward/mcp. Do not replace CFE. Do not hand-edit CLAUDE.md/AGENTS.md. Prefer skip skf-export-skill in this PR (serialize export after Wave A merges). If export is required to close an AC, rebase onto latest main last and use only skf-export-skill.

## Acceptance Criteria

- Given 29.1/29.2 proved the shape, when this story completes, then .claude/skills/pyforge-steward/ exists with provenance.
- Given bmad-agent-steward, when it completes a station task, then only grammar + MCP appear.
- Given conda-forge-expert, when this PR lands, then it is not replaced.
- Given CLAUDE.md/AGENTS.md, when this PR lands, then they are either unchanged or only skf-export-skill managed sections (no hand edits).
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Ledger key `33-1-skf-skill-and-persona-for-steward`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B provision-list. Reminting Canopy 18–30. CFE replace. Hand-editing CLAUDE/AGENTS.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-steward/`
- `.claude/skills/bmad-agent-steward/`
- `src/shared/packages/pyforge-steward/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 33.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

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
  - `[low]` `[patch]` platform/Wave-B guards now include untracked files (`git ls-files --others`) so the AC holds before the first commit

## Auto Run Result

Status: done

Summary: SKF Quick-tier content skill `pyforge-steward` compiled from `src/shared/packages/pyforge-steward/` with provenance and an `active` pointer. BMAD launcher `bmad-agent-steward` consults that skill and may only emit FR-13 `pyforge steward …` and FR-11 `POST /stations/steward/mcp`. Export skipped (CLAUDE.md/AGENTS.md unchanged). CFE untouched. No `pyforge.*` under `src/platform/`. Story 33.2 not started.

Files:
- `.claude/skills/pyforge-steward/` — brief, version-nested package, provenance, `active` symlink
- `.claude/skills/bmad-agent-steward/` — launcher SKILL.md, customize.toml, golden provision-list transcript
- `tests/meta/test_skf_steward_skill.py` / `test_steward_persona.py` — canopy:FR-37/canopy:FR-38 station-owned gates
- `planning-artifacts/specs/spec-33-1-….md` — tracked story spec

Review: 1 low patch applied; follow-up score 1 → false.

Verification: 18 passed (`test_skf_steward_skill` + `test_steward_persona`); SKF frontmatter/output PASS; `git diff origin/main -- src/platform` empty of pyforge imports.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
