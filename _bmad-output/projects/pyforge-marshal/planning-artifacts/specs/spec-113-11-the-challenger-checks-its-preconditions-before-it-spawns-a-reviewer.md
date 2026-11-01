---
title: "113.11: the challenger checks its preconditions before it spawns a reviewer"
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
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
---

<intent-contract>

## Intent

**Problem:** the challenger's preconditions sit in memlog deviations, not in the Spec, and one of them is checked
nowhere. Line numbers are at `03a7aff5d9`.

- Memlog deviations (1)-(5) of 2026-11-01 record the mechanism as built: the `[challenge].plugin_version` pin (default
  `0.1.0`, checked against `~/.claude/plugins/installed_plugins.json` and the cache `plugin.json`), one synchronous claude
  session from the packaged profile that orchestrates the Agent-tool spawns (reviewers on `model: inherit` under its
  `--model`, its own `--settings` Read rules on the plugin cache), the switch matrix, and plugin-absent dispatch. CAP-298
  still cites a `.claude/settings.json` pin, and the `core/challenge.py` module docstring (`:4-5`) repeats it (EGM audit
  MAR-M-Z6, MAR-M-D3, MAR-M-C3, MAR-D-C4).
- `omitClaudeMd` needs Claude Code 2.1.271 or later; nothing states or checks that floor (MAR-M-Z6).
- How the six `egm_*` switches, `[challenge].enabled` and `stages` combine is in code only; `resolve` also needs
  `egm_challenge`, which CAP-303 does not say (MAR-M-C4).
- No test composes a `[challenge]` block at the repo-default layer (MAR-D-R6).
- The Assumption at `SPEC.md:1294` claims the Agent tool's `model` override applies to plugin agents (the code passes
  `--model` instead) and a steward refresh verb re-verifies the pin (a deferred steward Kinship, memlog decision).
- CAP-302's success line and FR-244 (`prds/prd-pyforge-marshal-2026-07-25/prd.md:3597`) name
  `.claude/skills/pyforge-<station>/SKILL.md`, a path SKF never writes; the code reads
  `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` first (`station_skill_path`,
  `cli/challenge.py:234-243`) (cluster MAR-CL10: MAR-E1, MAR-D-C1).
- The Dream lists story specs in the audit at `docs/dreams/pyforge-marshal.md:13740` and leaves them out at `:13799`;
  the operator ruled on 2026-11-01 that `--audit` leaves story specs to the readiness stage.

**Approach:**
- **The floor, checked.** `plugin_refusal`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:172`) runs `claude --version` through the
  existing seam and refuses a version below 2.1.271, or one it cannot read, with the usage code before any spawn,
  journaled like the other refusals.
- **The stale docstring.** The `core/challenge.py` module docstring names `[challenge].plugin_version`.
- **The repo-default layer.** A test in `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`
  composes `policy.compose(repo_defaults={"challenge": BLOCK})` and asserts `REPO_DEFAULTS` provenance without reading
  a file (a live-tree read would need `_bmad-output/policy-defaults.toml` in the station-tests trigger map; 113.2 AC7).
- **The contract follows the code.** The memlog events for every finding above are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`), with the operator's decisions. Re-derive with `bmad-spec`:
  - CAP-298: the pin is `[challenge].plugin_version`; the mechanism is one synchronous claude session from the packaged
    profile that orchestrates the Agent-tool spawns, reviewers inherit its `--model` through `model: inherit`, and its
    own `--settings` carries the plugin-cache Read rules; Claude Code >= 2.1.271 is refused below.
  - CAP-299: `plugin_version` joins the block's key list; the switch matrix (ad hoc: `egm_challenge`,
    `egm_policy_block` and an enabled block; drift adds `egm_retro_drift`; audit adds `egm_audit`; resolve:
    `egm_challenge` and `egm_resolve_bridge`; readiness: `egm_challenge`, `egm_dispatch_readiness`, `egm_policy_block`,
    an enabled block and `readiness` in `stages`; `stages` gates only the dispatch hook).
  - CAP-300: a plugin absent or refused lets dispatch proceed with an `MRS-DISP-067` WARN (113.3 AC4, AC6).
  - CAP-302: `--audit` leaves story specs to the readiness stage, and a rules target is
    `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` (SKF-compiled from `skill-brief.yaml`, never
    hand-edited; `station_skill_path`'s flat fallback stays as tolerance). FR-244's text in the PRD is fixed in the
    same cascade re-stamp. `AGENTS.md:39` belongs to the scribe rules-slice story, not here.
  - The Assumption at `SPEC.md:1294` names Claude Code >= 2.1.271, drops the Agent-tool `model`-override claim, and
    records the pin refresh as the deferred steward Kinship.
  Then the cascade re-stamp (`updated:` on the PRD, the architecture spine and `epics.md`), `git add`, and the scoped
  stamp for every Spec `spec-surface-check` names.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the verb stays behind `pyforge.marshal.egm_challenge`.

Ledger key: `113-11-the-challenger-checks-its-preconditions-before-it-spawns-a-reviewer`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-298** (FR-240): the verb, its pin and its refusals.
- **CAP-299** (FR-241): the block's keys and the switch coupling.
- **CAP-300** (FR-242) and **CAP-302** (FR-244): re-derived text only (plugin-absent dispatch; the audit's scope and
  rules-target path).
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL6: MAR-M-Z6, MAR-M-D3, MAR-M-C3, MAR-M-C4, MAR-D-C4, MAR-D-R6; the re-derive of cluster MAR-CL10:
  MAR-E1, MAR-D-C1); the operator's ruling of 2026-11-01 on the audit's story-spec scope.

## Acceptance Criteria

- **AC1 — The floor.** With `claude --version` stubbed to `2.1.270`, an unreadable version, and `2.1.271`, the verb
  refuses with the usage code before any spawn (journaled) in the first two cases and proceeds in the third
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — The docstring.** `core/challenge.py` names `[challenge].plugin_version` and no `.claude/settings.json` pin.
- **AC3 — The repo-default layer.** A test composes a `[challenge]` block at `repo_defaults` and asserts its
  `REPO_DEFAULTS` provenance, with no file read.
- **AC4 — The contract.** CAP-298, CAP-299, CAP-300, CAP-302 and the Assumption read as the Approach states, re-derived
  by `bmad-spec` (both self-validate passes logged); FR-244 names the `active/` skill path; `spec-surface-check`,
  `chain-currency-sweep-check`, `chain-completeness-check` and `fr-without-cap-check` exit 0.
- **AC5 — Mutation.** Removing the version comparison fails AC1's `2.1.270` case. Restore it.
- **AC6 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Read the version through a seam the tests stub; never shell to `claude` from a unit test.

**Ask first:**
- Raising the floor above 2.1.271, or refusing on a version string the parser cannot read in a way other than the usage
  code.

**Never:**
- Never hand-edit `SPEC.md`, a compiled station `SKILL.md` or `AGENTS.md`; never mint a new exit code.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-298 (FR-240).
- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-298 and CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL6,
  MAR-CL10).
- Epic: Epic 113.
- Ledger key: `113-11-the-challenger-checks-its-preconditions-before-it-spawns-a-reviewer`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`, the re-derived `SPEC.md` and
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md` (FR-244); within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0 after the cascade re-stamp.

## Auto Run Result

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL6: MAR-M-Z6, MAR-M-D3,
  MAR-M-C3, MAR-M-C4, MAR-D-C4, MAR-D-R6; the CAP-302 re-derive of cluster MAR-CL10: MAR-E1, MAR-D-C1) and the
  operator's ruling of 2026-11-01 (story specs stay out of `--audit`; implement in the Story 113.7 landing PR). The
  Story 113.1 Given's stale pin text is corrected by an append-only note at mint. `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
