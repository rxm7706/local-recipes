---
title: Cluster requires mcp-host
type: feature
created: '2026-08-26'
status: ready
updated: '2026-08-26'
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

- [ ] Helm `required` / `fail` on empty `mcpHost.image.repository`.
- [ ] Test: no `mcpHost.enabled`; existing mcp-host chart ACs still green.
- [ ] Django system check for production/cluster only.
- [ ] `cluster-bringup.md` (and overlay comment) names mcp-host as required.
- [ ] Ledger `35-1-cluster-requires-mcp-host` → `review` then `done` via
      `sprint-ledger-sync`.

## Design notes

- Chart already always emits the Deployment (slice 1). This story is
  **omission fail-loud**, not a new sidecar.
- Profile detector must not treat `DEBUG=True` laptop as cluster.
- Reuse `test_chart_invariants.py` and `test_mcp_host_sidecar.py`.

## Verification

`pixi run -e local-recipes` / platform-ci-test on the new chart + check tests.
Host import-linter still green. Do not require a 12.7 Route/SCC re-prove.
