---
title: '63.3: One deny list, one hook — the Guild session guardrails are enforced, not asserted'
type: 'feature'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo

**Approach:** the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never denies anything not on the list (the list is closed; adding to it is a governance act on `guild-roster.json`)

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md` (CHAIN-STANDARD §5).
- This file is the tracked dispatch target for `marshal factory dispatch` / `resolve_story_spec_path`.

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo | the command or path matches a `session_denials` entry: `pixi run -e local-recipes <guild task>` (the `guild-tasks` set… | the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the same script serves both harnesses; harnesses without a verified deny surface (Gemini CLI, Copilot CLI, Devin) are named as instruction-only in `AGENTS.md`, not silently assumed covered | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `docs/governance/guild-roster.json` (a new closed `session_denials` list, the ONE declared source), `.claude/hooks/pre-shell.py` (new; registered `PreToolUse` on `Bash` and on `Edit`/`Write` in `.claude/settings.json`, `permissionDecision: deny` + reason), `.cursor/hooks.json` (new, force-tracked; `beforeShellExecution` deny — Cursor has no before-edit deny, so file rules there are `afterFileEdit` warn), tests under `tests/` for the script (the hook is repo-level, not a station package).
Ledger key: `63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-63.1 • **FR/AD:** spec-pyforge-steward CAP-5; marshal-token-economy:CAP-20 (silent saves; the front door)
**Surface:** `docs/governance/guild-roster.json` (a new closed `session_denials` list, the ONE declared source), `.claude/hooks/pre-shell.py` (new; registered `PreToolUse` on `Bash` and on `Edit`/`Write` in `.claude/settings.json`, `permissionDecision: deny` + reason), `.cursor/hooks.json` (new, force-tracked; `beforeShellExecution` deny — Cursor has no before-edit deny, so file rules there are `afterFileEdit` warn), tests under `tests/` for the script (the hook is repo-level, not a station package).
**Given** an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo
**When** the command or path matches a `session_denials` entry: `pixi run -e local-recipes <guild task>` (the `guild-tasks` set read from `pixi.toml`, never a copy); `pip install` / `uv pip install` / `conda install` / `npx <x>` except `npx skills add`; `pixi add` / `pixi update`; `scripts/bmad-switch` when a worktree or `BMAD_ACTIVE_PROJECT` is present; `git commit` on `main` or in the primary checkout, or with `Co-Authored-By` / AI attribution; `gh pr merge --squash`; `gh pr create` without `--repo rxm7706/local-recipes`; `uv run` with cwd ≠ repo root; `spec_surface_check.py --write-baseline` without `--spec`; a direct write to `SPEC.md`, `sprint-status-ledger.yaml`, or a tracked path under `implementation-artifacts/`
**Then** the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never denies anything not on the list (the list is closed; adding to it is a governance act on `guild-roster.json`)
**And** the same script serves both harnesses; harnesses without a verified deny surface (Gemini CLI, Copilot CLI, Devin) are named as instruction-only in `AGENTS.md`, not silently assumed covered
**Status:** backlog

