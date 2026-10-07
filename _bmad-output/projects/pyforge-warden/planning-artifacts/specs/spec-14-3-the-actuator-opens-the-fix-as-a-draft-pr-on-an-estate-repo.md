---
title: "14.3: The actuator opens the fix as a draft PR on an estate repo"
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: 'b36482389641efd2591a9d5b5c8a883bcafcf746'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-2-the-actuator-edits-the-manifest-and-re-solves-the-lock-in-a-throwaway-copy.md
flag:
  key: pyforge.warden.fix_draft_pr_estate
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the actuator opens today's non-draft PR over an empty tree, with the fix only in its body"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `GitHubForgeClient.open_pull_request` commits the base tree unchanged ("an empty remediation commit … the
actionable content rides in the PR body, not a manifest diff (deferred to v1.x)") and opens a ready-for-review PR on
whatever `GITHUB_REPOSITORY` names. The operator ruled on 2026-09-28 that the finished fix opens as a **draft** PR on the
estate's own repos, `rxm7706/local-recipes` and `rxm7706/python-foundry`.

**Approach:** When Story 14.2 produced a diff and the resolved repo is on the estate allowlist, `open_pull_request`
creates one blob per changed path, a tree on the base tree, and one commit on the `warden/fix/<hash>` branch, then opens
the PR with `draft: true` — all through the Git Data and Pulls endpoints the client already calls, inside the
`_EGRESS_ACTIVE` carve-out. The allowlist is a `[tool.pyforge-warden]` config key whose default is those two repos; a
repo outside it records `skipped` (not an estate repo) and opens nothing. The dedup (`existing_open_pr`, the 422
branch-exists skip) is unchanged. The PR body keeps its advisory citation and adds the target, the candidates tried and
the changed paths.

Ledger key: `14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-14.2.

### Living CAP citations

- `spec-pyforge-warden` CAP-24 (FR-41); CAP-12 (FR-40); CAP-11 (the actuator is the sole egress carve-out).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a Story 14.2 diff and a fixture forge for `rxm7706/local-recipes`, When the actuator runs with `--open-fix-prs`, Then the forge receives one blob per changed path, one tree, one commit on a `warden/fix/` branch, and a pull request with `draft: true`
- Given a repo not on the allowlist, When the actuator runs, Then the outcome is `skipped` with the reason and no forge write happens
- Given an existing open PR or an existing branch for the finding, When the actuator runs, Then the outcome is `skipped` exactly as today
- Given a forge error at any step, When it happens, Then the outcome is `failed` in `actuation`, stderr carries the one-line summary, and the status and exit code are unchanged
- Given the flag OFF, When the actuator runs, Then today's empty-tree PR opens

## Boundaries & Constraints

**Always:**
- Egress only inside `actuator.py` under `_EGRESS_ACTIVE` on the real path; `--fix-prs-dry-run` still opens no socket.
- Credentials from the environment only (`GITHUB_TOKEN` / `GH_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_API_URL`), never a flag.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-warden` and every co-governor `spec-surface-check` names; scoped stamps only.

**Never:**
- Open a PR on a fleet repo from here without an approved proposal (Story 16.3 owns that path).
- Push with `git`; the forge API is the only write path.
- Open a PR on any real repository from the test suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| estate repo + diff | `rxm7706/local-recipes` | draft PR, one commit carrying the diff | — |
| non-estate repo | `acme/app` | `skipped` (not an estate repo) | no forge write |
| no diff (14.2 failed) | — | no PR; 14.2's `failed` stands | — |
| branch exists | 422 on ref create | `skipped`, as today | — |
| forge 5xx | blob create fails | `failed` | never a rung |
| flag OFF | key off | today's empty-tree PR | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-24 (FR-41).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo`.
Ledger status at mint: `backlog`.
Deps: S-14.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fix_draft_pr_estate` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands) against a fixture forge: ON records a draft PR with a non-empty tree, OFF records today's empty-tree PR.
- Attended, operator-run only: one real draft PR on `rxm7706/local-recipes` from a fixture finding, closed afterwards.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — AC and I/O matrix audited against `pyforge-warden-test` and new unit coverage)

## Auto Run Result

Status: done

**Summary:** Story 14.3 wires `pyforge.warden.fix_draft_pr_estate`: on estate repos with a Story 14.2 manifest diff, the actuator opens a **draft** PR whose commit carries Git Data blobs/trees; non-estate repos skip with `not an estate repo`; flag OFF keeps the empty-tree, non-draft PR.

**Files changed:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py` — draft estate path, allowlist skip, enriched PR body
- `src/shared/packages/pyforge-warden/src/pyforge/warden/config.py` — `fix-pr-estate-repos` config key
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — pass allowlist from `EffectiveConfig`
- `src/platform/config/flags.json` / `flag-overlays.json` — register flag (on in dev/staging, off in production)
- `tests/unit/test_actuator_draft_pr_estate.py` — flag, allowlist, blob/draft forge shapes
- Adjusted forge fakes in existing actuator tests

**Review:** No patch/defer items. Matrix rows covered by new/updated unit tests.

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 2204 passed; `python scripts/spec_surface_reconcile.py` — OK after memlog reconciles.

**Residual risks:** Attended real-repo draft PR check remains operator-only per spec. Q4 flag cleanup date not set until flag is ON everywhere per metadata clock rules.
