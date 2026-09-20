---
title: SKF skill ownership and BMAD persona for scribe
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Steward 29 compiled pyforge-scribe + bmad-agent-scribe. Scribe must own remaining gaps so Path B is not steward-only leftover.

**Approach:** If .claude/skills/pyforge-scribe/ already matches 29.1 provenance, skip recompile. Confirm bmad-agent-scribe uses only pyforge scribe … and POST /stations/scribe/mcp. Move or add station-owned tests under pyforge-scribe if they still live only under steward. Do not rewrite a working skill.

## Acceptance Criteria

- Given steward 29.1 may already have compiled pyforge-scribe, when this story completes, then the skill exists under .claude/skills/ with scribe package provenance (skip recompile if identical).
- Given bmad-agent-scribe, when inspected, then it uses only pyforge scribe … and POST /stations/scribe/mcp.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged unless a skip-recompile no-op commit still lands the spec + ownership tests.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger key `5-1-skf-skill-and-persona-for-scribe`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Unnecessary SKF recompile. Wave B recall portal. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-scribe/` — may already exist
- `.claude/skills/bmad-agent-scribe/` — may already exist
- steward spec-29-1 / spec-29-2 — compare before rewriting

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 5.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9da49578fa` (2026-08-26, "Merge pull request #833 from rxm7706/scribe/5-1-skill-ownership"). Ledger row `5-1-skf-skill-ownership-and-bmad-persona-for-scribe: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-5-1-skf-skill-and-persona-for-scribe.md`, `src/shared/packages/pyforge-scribe/tests/meta/test_skf_skill_ownership.py`, `src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-progress` → `done` (ledger row `5-1-skf-skill-ownership-and-bmad-persona-for-scribe: done`).
- `## Auto Run Result` reconstructed from git (none survived).
