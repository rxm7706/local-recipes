---
title: SKF domain skill and BMAD persona for atlas
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Atlas has no station-owned SKF skill or bmad-agent-atlas. Path B agents freelance the filesystem.

**Approach:** Compile SKF from src/shared/packages/pyforge-atlas/ if missing (shape = steward 29.1). Author bmad-agent-atlas that consults that skill and may only emit pyforge atlas … and POST /stations/atlas/mcp. Do not replace conda-forge-expert. Do not export CLAUDE.md/AGENTS.md (steward 33.1 / coordinator serializes export).

## Acceptance Criteria

- Given steward 29.1 compiled the shape, when this story completes, then .claude/skills/pyforge-atlas/ exists (SKF from src/shared/packages/pyforge-atlas/) with provenance and an active pointer.
- Given bmad-agent-atlas, when it completes a station task, then the transcript uses only consult_content_skill, pyforge atlas …, and POST /stations/atlas/mcp.
- Given conda-forge-expert, when this PR lands, then it is unchanged and is not SKF-regenerated.
- Given CLAUDE.md and AGENTS.md, when this PR lands, then they are unchanged (no hand edit; no skf-export-skill in this story).
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-atlas/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-atlas` only — never `scripts/bmad-switch`. Ledger key `19-1-skf-skill-and-persona-for-atlas`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B portal. DW-H3. Vizro on the host. Copying Canopy 18–30. Replacing CFE. Editing CLAUDE.md/AGENTS.md.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-atlas/` — SKF package
- `.claude/skills/bmad-agent-atlas/` — BMAD persona (pattern: bmad-agent-scribe)
- `src/shared/packages/pyforge-atlas/` — compile source (read-only)
- steward 29.1/29.2 specs — shape reference

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 19.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Auto Run Result

Status: done

Summary: SKF content skill `.claude/skills/pyforge-atlas/` compiled from `src/shared/packages/pyforge-atlas/` (version-nested, `active` pointer, provenance). BMAD launcher `bmad-agent-atlas` consults that skill and may only emit `pyforge atlas …` and `POST /stations/atlas/mcp`. CFE, CLAUDE.md, and AGENTS.md untouched. No `pyforge.*` under `src/platform/`. Story 19.2 not started. Ledger key `19-1-skf-skill-and-persona-for-atlas`.

Files:
- `.claude/skills/pyforge-atlas/` — SKF package + brief
- `.claude/skills/bmad-agent-atlas/` — launcher SKILL.md, customize.toml, golden transcript
- `src/shared/packages/pyforge-atlas/tests/meta/test_skf_skill_and_persona.py` — AC contract
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-19-1-skf-skill-and-persona-for-atlas.md` — tracked story spec

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
