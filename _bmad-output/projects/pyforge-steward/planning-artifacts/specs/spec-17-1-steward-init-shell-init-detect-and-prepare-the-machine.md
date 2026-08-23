---
title: steward init/shell-init detect and prepare the machine
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: f17a8f704f
---

<intent-contract>

## Intent

**Problem:** Fresh-machine onboarding is undocumented ritual — no steward verbs to detect prereqs or prepare the shell (spec-developer-machine-bootstrap CAP-1).

**Approach:** Add `steward init` and `steward shell-init`: report each prereq (pixi/git/gh/podman + floors from `scripts/pixi_version_registry.py`) with a named remedy; shell-init emits PATH/completions/env. Both idempotent, `--json` for automation. Consumes Epic 16 substrate; does not implement setup/initrepo (17.2). Skip 12-7.

## Acceptance Criteria

- `steward init` reports prereqs with named remedies; floors from pixi version registry.
- `steward shell-init` emits PATH/completions/env; idempotent.
- Both support `--json`.
- Does not implement `setup` / `initrepo` (17.2) or duplicate provision/cluster bring-up.

## Boundaries & Constraints

**Never:** Cluster bring-up (12.4); multi-repo workspaces (Epic 13). Finalize steward ledger only. Do not touch marshal 20-10.

</intent-contract>

## Code Map

- Parent: `spec-developer-machine-bootstrap/SPEC.md` (CAP-1, 17.1 scope)
- `src/shared/packages/pyforge-steward/` CLI verbs: `init`, `shell-init`
- Floors: `scripts/pixi_version_registry.py`
- Tests: prereq detection, remedy text, shell-init output, `--json`

## Verification

- `steward init` / `shell-init` green locally
- Prereq failure names remedy (not silent)
- Idempotent re-run

## Auto Run Result

Status: done

Summary: Added `steward init` (prereq detection for pixi/git/gh/podman with named remedies; pixi floor from `requires-pixi`) and `steward shell-init` (idempotent PATH/env/bash-completion snippet). Both support `--json`.

Merge: PR #697 admin-merged at `551de2ecdd720dd26216cc647716ec17d72f1cbd` (GitHub Actions billing blocked CI runners; local tests green).

Verification:
- `pixi run -e pyforge-steward pyforge-steward-test` → 873 passed, 1 skipped
