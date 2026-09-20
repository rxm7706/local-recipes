---
title: Cluster requires mcp-host
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 27c4cc64b118f300b4fe0d7bea71cef780d3d693
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/cluster-required.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/retire-skip.md
  - docs/dreams/mcp-era-isolation.md
warnings: []
deferred:
  - slice 3 ImportError skip (retire-skip.md)
  - Epic 34 query plane
---

<intent-contract>

## Intent

**Problem:** Slice 1 shipped the mcp-host bridge, but a cluster install can still
omit a usable sidecar image or leave production without
`MCP_HOST_SIDECAR_BASE_URL`. Host MCP then degrades to the ImportError skip
while the chart looks green.

**Approach:** Fail-loud on the **cluster** path only. Helm must refuse an empty
`mcpHost.image.repository` and must not grow an `enabled` knob. Production /
cluster Django check requires the proxy URL. Bring-up docs name mcp-host as
required. Laptop and `platform-ci-test` keep URL-unset behavior.

## Acceptance Criteria

- Given `helm template` of the platform chart, when `mcpHost.image.repository`
  is empty, then the command fails (non-zero), not a broken image ref.
- Given the chart values schema, when reviewed, then there is no
  `mcpHost.enabled` (a test fails if one is added).
- Given existing helm tests, when they run, then mcp-host Deployment +
  ClusterIP still exist and web/worker still carry
  `MCP_HOST_SIDECAR_BASE_URL` to the internal Service.
- Given production/cluster Django settings, when `manage.py check` runs
  without `MCP_HOST_SIDECAR_BASE_URL`, then the check errors.
- Given the URL unset (laptop / platform-ci-test), when gunicorn starts on
  mcp 1.x, then the ImportError skip still applies (slice 3 not this story).
- Given the URL set and sidecar unreachable, when `POST /stations/atlas/mcp`
  runs, then the host returns 502 and the web process stays up.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `35-1-cluster-requires-mcp-host`. Host never imports `pyforge.*`.

**Block If:** Implementation would lift `python-agent-platform` to mcp 2.x, fold
`mcp-types` / `httpx2` into that env, delete the ImportError skip, add
`mcpHost.enabled`, CrashLoop web when the sidecar is down, or start Epic 34.

**Never:** FastMCP 4 from PyPI. One lockfile for mcp 2 + Langflow. A ninth
station. Remint unifying-strategy architecture.

</intent-contract>

## Tasks

- [x] Helm `required` / `fail` on empty `mcpHost.image.repository`.
- [x] Test: no `mcpHost.enabled`; existing mcp-host chart ACs still green.
- [x] Django system check for production/cluster only.
- [x] `cluster-bringup.md` (and overlay comment) names mcp-host as required.
- [x] Ledger `35-1-cluster-requires-mcp-host` → `review` then `done` via
      `sprint-ledger-sync`.

## Design notes

- Chart already always emits the Deployment (slice 1). This story is
  **omission fail-loud**, not a new sidecar.
- Profile detector must not treat `DEBUG=True` laptop as cluster.
- Reuse `test_chart_invariants.py` and `test_mcp_host_sidecar.py`.

## Verification

`pixi run -e python-agent-platform -- python -m pytest -o addopts= src/platform/tests/test_startup_required_settings.py` (cwd `src/platform`). Helm proofs: `pixi run -e platform-dev -- python -m pytest -o addopts=` the four `test_chart_invariants` mcp-host cases. Host import-linter still green. Do not require a 12.7 Route/SCC re-prove.

## Suggested Review Order

**Helm fail-loud**

- Empty repository refuses the render
  [`mcp-host-deployment.yaml:3`](../../../../../../src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml#L3)

**Deployed boot**

- Production requires the proxy URL; laptop `COMPONENT_RUNTIME=local` skips
  [`stage_one.py:65`](../../../../../../src/platform/config/startup/stage_one.py#L65)

**Docs**

- Overlay inherits mcp-host; bring-up names the Deployment
  [`core-overrides.yaml:12`](../../../../../../src/platform/deploy/overlays/ocp/core-overrides.yaml#L12)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9d3ad9105b` (2026-08-26, "Merge pull request #867 from rxm7706/steward/35-1-cluster-requires-mcp-host"). Ledger row `35-1-cluster-requires-mcp-host: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-35-1-cluster-requires-mcp-host.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/config/startup/stage_one.py`, `src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml`, `src/platform/deploy/charts/platform/values.yaml`, `src/platform/deploy/overlays/ocp/cluster-bringup.md`, `src/platform/deploy/overlays/ocp/core-overrides.yaml`, `src/platform/tests/test_chart_invariants.py`, `src/platform/tests/test_startup_required_settings.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
