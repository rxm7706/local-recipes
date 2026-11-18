---
sources:
  - scripts/platform_ci_test_requirements_check.py
  - src/platform/Containerfile
  - .github/workflows/platform-ci.yml
verified: 2026-11-17
---

# Platform Python dependencies — pixi is the sole authority

The former `base.txt` / `production.txt` / `local.txt` install chains in the
platform host's `requirements/` directory were retired by steward Story 16.1 (CAP-5 of
`spec-platform-fifteen-factors`, a Spec since archived). That directory no longer exists.

| Need | Use |
|------|-----|
| Platform CI `test` job | `[feature.platform-ci-test]` / env `platform-ci-test` in repo-root `pixi.toml` |
| Local platform host + engines | env `platform-dev` (composes `python-agent-platform` + `platform-dev`) |
| Container image (same env as host) | `[feature.python-agent-platform.dependencies]` |

Do **not** reintroduce `*.txt` requirement files there as an install source.
`pixi run -e pyforge-guild platform-ci-test-requirements-check` fails if they return.
