---
title: "Platform image moves to Python 3.14"
type: "feature"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "637f4158"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-43-5-one-interpreter-story.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-13-1-langflow-base-onnxruntime-pin-admits-python-3-14.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-13-2-dbgpt-client-sqlalchemy-cap-admits-python-3-14.md"
  - "pixi.toml"
  - "pixi.lock"
  - "environment.yaml"
  - "src/platform/Containerfile"
  - "src/platform/compose/dbgpt/Containerfile"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py"
warnings:
  - "pixi.toml changes regenerate environment.yaml on the same PR (CLAUDE.md PR gate 2, ungated by the maintenance label)."
  - "Sixteen pixi-version sites are registry-enforced (`pixi-version-check`); this story changes python pins, not pixi pins — do not touch the registry."
deferred:
  - "Retiring the mcp-host ImportError skip (spec-mcp-era-isolation slice 3) — still blocked by langflow's `mcp <2` pin, unchanged by this story."
---

<intent-contract>

## Intent

**Problem:** After Mason 13.1 and 13.2 land on conda-forge, nothing in the repo
consumes them: `python-agent-platform` and `dbgpt-sidecar` still pin `3.12.*`, so
the laptop and the cluster keep running different interpreters and Atlas/Doctor
remain un-importable in the platform image.

**Approach:** Flip `[feature.python-agent-platform.dependencies]` and
`[feature.dbgpt-sidecar.dependencies]` to `python = "3.14.*"`, re-lock, regenerate
`environment.yaml`, rebuild both images, and prove parity: the platform image
imports `pyforge.atlas` and `pyforge.doctor`, the Langflow mount boots, DB-GPT's
sidecar answers, and `platform-ci` is green on both engines. The `mcp-host`
sidecar stays (MCP-SDK isolation, 43.5).

## Acceptance Criteria

- Given `pixi.toml`, when read, then no feature pins `python = "3.12.*"`; the
  line-140 comment ("env-scoped ONLY … rest of the repo stays on 3.14") is rewritten
  to state one interpreter.
- Given `pixi lock`, when run, then `python-agent-platform` and `dbgpt-sidecar`
  resolve on `3.14.*` with `langflow-base` from the Mason-13.1 build and
  `dbgpt-client` from the Mason-13.2 build; `environment.yaml` is regenerated in the
  same commit.
- Given the platform image, when `python -c "import pyforge.atlas, pyforge.doctor"`
  runs inside it, then it succeeds, and `_log_import_skip` no longer fires for the
  interpreter reason (it may still fire for the `mcp` 2.x reason — that is 43.5's AD).
- Given `platform-ci`, when it runs on the branch, then the container, air-gap-parity
  and both-engines jobs are green; the Langflow `/health` and DB-GPT sidecar REST
  round-trips pass on 3.14.
- Given `pixi run -e local-recipes pixi-version-check`, when run, then it is
  unchanged and green (no pixi version site touched).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-6-platform-image-moves-to-python-3-14`. Regenerate
`environment.yaml`. Consume Mason's feedstock builds; never vendor or patch a
recipe here.

**Block If:** Mason 13.1 or 13.2 is not `done`; implementation would pin a
pre-release, add a channel, or loosen a pin locally to make the solve pass.

**Never:** A second lockfile for the platform. Deleting `mcp-host`.

</intent-contract>

## Tasks

- [ ] `pixi.toml` python pins + comment; `pixi lock`; `environment.yaml`.
- [ ] Containerfiles: no change expected; verify builder stage pulls the 3.14 env.
- [ ] Parity proof: image import test for atlas/doctor; CI green.
- [ ] Dream sizing/Multi-Python references updated to the measured matrix (43.5 generator).
- [ ] Ledger `43-6-platform-image-moves-to-python-3-14` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi install --frozen -e python-agent-platform` and `-e dbgpt-sidecar`; `.github/workflows/platform-ci.yml` jobs; `pixi run -e local-recipes pixi-version-check`.
