---
title: "113.10: the challenge session carries no house context, checked at runtime"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
---

<intent-contract>

## Intent

**Problem:** reviewer isolation rests on the plugin adapters' frontmatter alone. Line numbers are at `03a7aff5d9`.

- `widen_settings` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py:50-67`)
  starts from `claude.toml`'s settings, so the challenge session loads user-scope hooks (a `SubagentStart` hook's
  payload and `gitStatus` reached an `omitClaudeMd` reviewer during the audit), the `claude-md-and-agents-md`
  `instructionFiles` plugin config, `CLAUDE.md` and `AGENTS.md` (EGM audit MAR-M-D2, MAR-E3).
- The session's `--settings` denies `Bash`, `Edit` and `Write` (except one run-folder `Write` rule) but carries no `Read`
  deny for `AGENTS.md`, `CLAUDE.md`, a memlog or `.claude/memory/`, so the goldfish rule holds only as a prompt
  instruction. `SPEC.md:1204` already settles that context isolation is not filesystem isolation; this story closes the
  context half at runtime.
- The orchestrator session that writes `report.json` loads `CLAUDE.md` (memlog, 2026-11-01), and CAP-299's "receives
  exactly" overstates what a reviewer gets. The synthesizer half of MAR-M-D2 is Story 113.12's.

**Approach:**
- **Hooks off.** `widen_settings` sets `disableAllHooks: true` in the challenge `--settings` (or the argv limits
  `--setting-sources` so user-scope hooks never load). `Bash`, `Edit` and `Write` stay denied except the run-folder
  `Write` rule, so turning hooks off removes no guard; a test pins the deny list.
- **No instruction files.** The challenge settings strip the `instructionFiles` (`claude-md-and-agents-md`) plugin
  config and add `Read` deny rules for `AGENTS.md`, `CLAUDE.md`, `**/.memlog.md` and `.claude/memory/**`, with the
  target excepted (a rules-stage target may be `AGENTS.md`).
- **Outside the repo.** The session launches from a cwd outside the repo (the run folder under Tier 3, or a temp dir),
  and the challenge `--settings` carries `enabledPlugins` `{"egm@egm": true}` so the plugin is enabled there;
  `plugin_refusal` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:172`) checks the same
  scope the session uses.
- **The contract follows the code.** The memlog events for MAR-M-D2 and MAR-E3 are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`). Re-derive CAP-299 with `bmad-spec`: "receives exactly" means the adapter frontmatter plus the
  session's own settings; name what still reaches a reviewer (managed policies) and whether the orchestrator loads
  `CLAUDE.md` after this story. Then the cascade re-stamp and the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the session launches only while
  `pyforge.marshal.egm_challenge` is on.

Ledger key: `113-10-the-challenge-session-carries-no-house-context-checked-at-runtime`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the goldfish context rule; a reviewer never receives `AGENTS.md`,
  `CLAUDE.md`, a memlog, a URL or session text.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL7; findings MAR-M-D2, MAR-E3).

## Acceptance Criteria

- **AC1 — Hooks off.** The rendered challenge `--settings` sets `disableAllHooks: true` (or the argv limits
  `--setting-sources` to exclude user scope); a test in
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py` pins it.
- **AC2 — The Read denies.** The settings deny `Read` on `AGENTS.md`, `CLAUDE.md`, `**/.memlog.md` and
  `.claude/memory/**`, carry no `instructionFiles` plugin config, and except the target when the target is one of those
  paths; tests pin the list and the exception.
- **AC3 — The guards stay.** `Bash`, `Edit` and `Write` are denied except the run-folder `Write` rule, with hooks off.
- **AC4 — The plugin scope.** The session's cwd is outside the repo, its `--settings` carries `enabledPlugins`
  `{"egm@egm": true}`, and `plugin_refusal` refuses when that scope does not enable the plugin.
- **AC5 — The contract.** CAP-299 is re-derived by `bmad-spec` (both self-validate passes logged);
  `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC6 — Mutation.** Removing `disableAllHooks` (or the setting-sources limit) fails AC1's test; removing the
  `AGENTS.md` deny fails AC2's. Restore each.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Change only the challenge session's own settings and cwd; never `claude.toml`'s shared dispatch argv.

**Ask first:**
- If `disableAllHooks` would also disable a managed-policy hook the operator relies on, which form (hooks off or
  setting-sources) to use.

**Never:**
- Never widen a reviewer's tools beyond `Read`, `Grep` and `Glob`; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

**Residual risk:**
- Managed (enterprise) policy settings still load; the re-derived CAP-299 names them as what still reaches a reviewer.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL7).
- Epic: Epic 113.
- Ledger key: `113-10-the-challenge-session-carries-no-house-context-checked-at-runtime`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py` and the re-derived `SPEC.md`; within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL7: MAR-M-D2, MAR-E3; the
  contested MAR-M-D2 settled in the cluster) at the operator's ruling of 2026-11-01 (implement in the Story 113.7
  landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
