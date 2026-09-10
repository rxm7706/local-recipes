---
title: "Story 48.11: The platform image can import the warden engine it calls"
type: story
created: 2026-09-10
baseline_revision: 0c75d60935d60a30448aee10f62079411ad98348
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - pixi.toml
  - environment.yaml
warnings: []
deferred: []
declared_low_risk: true
---

# Story 48.11: The platform image can import the warden engine it calls

<intent-contract>

## Intent

**Problem:** `django_warden_fabric/tasks.py:97-102` lazy-imports `pyforge.warden.cli` for compliance jobs, but `[feature.python-agent-platform.dependencies]` installs only `pyforge-steward` as a path dep — so the platform image fails every warden job at import time with `ModuleNotFoundError`.

**Approach:** Add `pyforge-warden` as a path dependency of the platform feature (same shape as the existing `pyforge-steward` line), regenerate `environment.yaml`, and add a platform policy test that asserts the manifest pin and that `import pyforge.warden.cli` resolves in the `python-agent-platform` pixi environment.

## Boundaries & Constraints

**Always:** Path dep uses `{ path = "src/shared/packages/pyforge-warden" }` beside the steward line in `[feature.python-agent-platform.dependencies]`. Regenerate `environment.yaml` via `pixi project export conda-environment -e build > environment.yaml`. PR carries the `maintenance` label (operator action at PR open).

**Never:** No change to `django_warden_fabric/tasks.py` lazy-import boundary. No hand-edit of `sprint-status-ledger.yaml`. Do not add warden to `platform-ci-test` (that env is intentionally lean; the image env is `python-agent-platform`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MANIFEST_PIN | `pixi.toml` `[feature.python-agent-platform.dependencies]` | `pyforge-warden` path dep present next to `pyforge-steward` | Policy test fails on regression |
| LOCK_RESOLVES | `pixi.lock` `environments.python-agent-platform` | `conda_source: pyforge-warden[…]` entry for the env | Policy test greps lock block |
| IMPORT_ORACLE | `pixi run -e python-agent-platform python -c "import pyforge.warden.cli"` | exit 0 | Subprocess test surfaces ModuleNotFoundError |

</intent-contract>

## Code Map

- `pixi.toml:226` — existing `pyforge-steward` path dep in `[feature.python-agent-platform.dependencies]`; add `pyforge-warden` on the next line with Story 48.11 comment (warden-B7 / fleet readiness C7)
- `pixi.lock` — regenerate after manifest change (`pixi lock` or install that updates lock)
- `environment.yaml` — regenerate ungated sync export from build env
- `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py:97-102` — READ-ONLY: lazy `from pyforge.warden.cli import main` is the consumer this story unblocks
- `src/platform/tests/policy/test_warden_platform_env_import.py` — NEW: manifest + lock + subprocess import oracle (marshal-policy.toml Epic 48.11 surface)

## Tasks & Acceptance

**Execution:**
- `pixi.toml` — add `pyforge-warden` path dep to `[feature.python-agent-platform.dependencies]`
- `pixi.lock` — update lock after dep add
- `environment.yaml` — regenerate from build env export
- `src/platform/tests/policy/test_warden_platform_env_import.py` — platform-env import policy test

**Acceptance Criteria:**
- Given `tasks.py:97-102` lazy-imports `pyforge.warden.cli` and the platform image installs `python-agent-platform`, when `pyforge-warden` is added as a path dependency and `environment.yaml` is regenerated, then `python -c "import pyforge.warden.cli"` resolves inside the platform environment and a test asserts it
- Given a PR touching paths outside `recipes/`, when opened, then it carries the `maintenance` label and the regenerated `environment.yaml`

## Verification

**Commands:**
- `pixi run -e platform-ci-test pytest src/platform/tests/policy/test_warden_platform_env_import.py -q` — expected: all tests pass
- `pixi run -e python-agent-platform python -c "import pyforge.warden.cli"` — expected: exit 0

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — small declared-low-risk diff; self-review only)

## Auto Run Result

Status: done

**Summary:** Added `pyforge-warden` as a path dependency of `[feature.python-agent-platform.dependencies]`, regenerated `pixi.lock` and `environment.yaml`, and added a platform policy test suite asserting the manifest pin, lock resolution, and live `import pyforge.warden.cli` in the platform pixi environment.

**Files changed:**
- `pixi.toml` — `pyforge-warden` path dep on `python-agent-platform`
- `pixi.lock` — lock updated for platform + platform-dev envs
- `environment.yaml` — regenerated build-env export (ungated sync check)
- `src/platform/tests/policy/test_warden_platform_env_import.py` — manifest, lock, and import oracle
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-48-11-*.md` — story spec
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` — 48-11 → done

**Review:** No patch findings; declared low-risk single-story scope.

**Follow-up review recommended:** false

**Verification:**
- `pixi run -e python-agent-platform python -c "import pyforge.warden.cli"` — exit 0
- `pixi run -e platform-ci-test pytest src/platform/tests/policy/test_warden_platform_env_import.py -q` — 3 passed

**Residual risks:** PR opener must add the `maintenance` label (paths outside `recipes/`). Import subprocess test requires `python-agent-platform` env installed where policy tests run.
