---
title: SKF domain skill and BMAD persona for marshal
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Marshal has no station-owned SKF skill or bmad-agent-marshal.

**Approach:** SKF from src/shared/packages/pyforge-marshal/ if missing. Persona uses only pyforge marshal … and POST /stations/marshal/mcp. Do not implement bmad-loop → supervisor ingest. No CFE replace. No CLAUDE/AGENTS export.

## Acceptance Criteria

- Given steward 29 proved the shape, when this story completes, then .claude/skills/pyforge-marshal/ exists with provenance.
- Given bmad-agent-marshal, when it completes a station task, then only grammar + MCP appear.
- Given this PR, when reviewed, then no bmad-loop ingest wire is added.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger key `27-1-skf-skill-and-persona-for-marshal`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B loop-home list. Supervisor ingest. Epic 22 factory dispatch. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-marshal/`
- `.claude/skills/bmad-agent-marshal/`
- `src/shared/packages/pyforge-marshal/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 27.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` ingest-guard treated prohibition language as a wire; context-snippet now says Do not implement, test accepts forbid phrasing
  - `[low]` `[patch]` CLAUDE.md / AGENTS.md / CFE now asserted unchanged vs origin/main

## Auto Run Result

Status: done

Summary: SKF content skill `pyforge-marshal` compiled from `src/shared/packages/pyforge-marshal/` with provenance. BMAD launcher `bmad-agent-marshal` consults that skill and may only emit `pyforge marshal …` and `POST /stations/marshal/mcp`. Golden status transcript plus contract tests fail on filesystem or ad-hoc HTTP freelance. No bmad-loop ingest. CFE / CLAUDE.md / AGENTS.md unchanged. No `pyforge.*` under `src/platform/`.

Files:
- `.claude/skills/pyforge-marshal/` — SKF brief, versioned package, `active` pointer
- `.claude/skills/bmad-agent-marshal/` — launcher SKILL.md, customize.toml, golden transcript
- `tests/meta/test_skf_domain_skill.py` + `test_station_persona.py` — station AC gates
- `planning-artifacts/specs/spec-27-1-….md` — tracked story spec

Review: 2 low patches applied; follow-up score 2 → false.

Verification: 19 passed (`test_skf_domain_skill` + `test_station_persona`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
