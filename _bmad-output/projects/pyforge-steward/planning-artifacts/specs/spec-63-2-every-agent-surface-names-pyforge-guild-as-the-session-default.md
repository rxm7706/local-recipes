---
title: '63.2: Every agent surface names `pyforge-guild` as the session default'
type: 'docs'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every document tells an agent `pixi run -e local-recipes …` for planning work

**Approach:** the planning/detector invocations read `-e pyforge-guild`; recipe invocations still read `-e local-recipes`; scribe recall still reads `-e pyforge-scribe`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-2-every-agent-surface-names-pyforge-guild-as-the-session-default.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| every document tells an agent `pixi run -e local-recipes …` for planning work | this story lands | the planning/detector invocations read `-e pyforge-guild`; recipe invocations still read `-e local-recipes`; scribe recall still reads `-e pyforge-scribe` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `governance-currency`, `general-docs-consistency-check` and `llms-full-check` are green | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `AGENTS.md` (`bmad:context` block via `bmad-project-context`), `CLAUDE.md`, `.cursor/rules/*.mdc`, `.claude/skills/pyforge-*/SKILL.md`, `.cursor/one-chain-folds/README.md` briefs, the Cursor cloud-environment install command, `docs/reference/library-llms-full.md` env-membership rows (`llms-full-check` green).
Ledger key: `63-2-every-agent-surface-names-pyforge-guild-as-the-session-default`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-2-every-agent-surface-names-pyforge-guild-as-the-session-default.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** S-63.1 • **FR/AD:** spec-pyforge-steward CAP-5
**Surface:** `AGENTS.md` (`bmad:context` block via `bmad-project-context`), `CLAUDE.md`, `.cursor/rules/*.mdc`, `.claude/skills/pyforge-*/SKILL.md`, `.cursor/one-chain-folds/README.md` briefs, the Cursor cloud-environment install command, `docs/reference/library-llms-full.md` env-membership rows (`llms-full-check` green).
**Given** every document tells an agent `pixi run -e local-recipes …` for planning work
**When** this story lands
**Then** the planning/detector invocations read `-e pyforge-guild`; recipe invocations still read `-e local-recipes`; scribe recall still reads `-e pyforge-scribe`
**And** `governance-currency`, `general-docs-consistency-check` and `llms-full-check` are green
**Status:** backlog

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `8a6aefcd60` (2026-09-16, "steward 63.2 + mint 63.3/63.4: every agent surface names pyforge-guild; default is its alias"). Ledger row `63-2-every-agent-surface-names-pyforge-guild-as-the-session-default: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/hooks/session-start.sh`, `.cursor/environment.json`, `.github/workflows/copilot-setup-steps.yml`, `AGENTS.md`, `CLAUDE.md`, `_bmad-output/PROJECTS.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/README.md`, `docs/reference/README.md`, `docs/reference/library-llms-full.md` (+3 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
