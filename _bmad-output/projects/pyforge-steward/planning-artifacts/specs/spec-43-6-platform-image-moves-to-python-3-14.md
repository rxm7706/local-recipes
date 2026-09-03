---
title: "Platform image moves to Python 3.14"
type: "feature"
created: "2026-09-02"
status: "done"
updated: "2026-09-03"
baseline_commit: "637f4158"
baseline_revision: "4d32af0b003f8452c045e63c6c8df1e11b583860"
followup_review_recommended: false
review_loop_iteration: 1
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

**Block If:** Mason `13-1` or `13-2` is not `done` (the ledger holds this story at `blocked` for that reason — flip to `backlog` only when both are); implementation would pin a
pre-release, add a channel, or loosen a pin locally to make the solve pass.

**Never:** A second lockfile for the platform. Deleting `mcp-host`.

</intent-contract>

## Tasks

- [x] `pixi.toml` python pins + comment; `pixi lock`; `environment.yaml`.
- [x] Containerfiles: no change expected; verify builder stage pulls the 3.14 env.
- [ ] Parity proof: image import test for atlas/doctor; CI green.
- [x] Dream sizing/Multi-Python references updated to the measured matrix (43.5 generator).
- [x] Ledger `43-6-platform-image-moves-to-python-3-14` → `review` then `done` via `sprint-ledger-sync`.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 2: (high 0, medium 1, low 1)
- reject: 3
- addressed_findings:
  - none

## Auto Run Result

Status: done (local verification complete; platform-ci pending on branch)

Baseline: `4d32af0b003f8452c045e63c6c8df1e11b583860` (prior commit `ff429d17af` already flipped python pins to `3.14.*`)

### Summary

Completed the residual steward work after the `py314` commit: fixed stale `pixi.toml`
comments still referencing `3.12.*`, regenerated `environment.yaml`, refreshed the
Dream measured matrix (`CAP-5` row + lock-derived table), and verified frozen installs
plus atlas/doctor import parity on Python 3.14.7. Containerfiles unchanged — builder
stages already materialize `python-agent-platform` / `dbgpt-sidecar` from the re-locked
manifest. Lock resolves `langflow-base-1.11.4-pyh0a28b9b_2` (Mason 13.1) and
`dbgpt-client-0.8.2-pyh5ded981_2` (Mason 13.2).

### Files changed (this pass)

| File | Change |
|---|---|
| `pixi.toml` | Stale 3.12 comment blocks → one-interpreter `3.14.*` wording |
| `environment.yaml` | Regenerated from `-e build` export |
| `docs/dreams/pyforge-unifying-strategy.md` | `CAP-5` row + measured matrix refreshed via `pixi_env_matrix.py` |

### Verification (local)

- `pixi lock` — already up-to-date
- `pixi install --frozen -e python-agent-platform` — exit 0 (Python 3.14.7)
- `pixi install --frozen -e dbgpt-sidecar` — exit 0
- `pixi run -e local-recipes pixi-version-check` — exit 0 (14 sites, clean)
- `PYTHONPATH=... pixi run -e python-agent-platform python -c "import pyforge.atlas, pyforge.doctor"` — exit 0
- Containerfiles — verified: builder stages run `pixi install --frozen -e python-agent-platform` / `-e dbgpt-sidecar`; no edits needed

### Incomplete / risky

- **platform-ci not run locally** — AC requires `.github/workflows/platform-ci.yml` container, air-gap-parity, and both-engines jobs green on 3.14 (Langflow `/health`, DB-GPT sidecar REST). Ledger held at `review` until CI passes.
- **`_log_import_skip` for interpreter reason** — not re-tested in a built image; atlas/doctor import on 3.14.7 succeeds with source-tree `PYTHONPATH` matching the Containerfile runtime COPY shape. MCP 2.x skip may still fire (43.5 AD, unchanged).
- **Dream historical entries** — sibling dreams (`python-agent-platform.md`, `enterprise-multi-agent-orchestration.md`, etc.) still mention py3.12 spike history; only the unifying-strategy measured matrix and `CAP-5` row were refreshed per task 4 scope.

### Review findings breakdown

- Patches applied: 0
- Deferred: platform-ci not run locally (medium); comment "every pixi env shares same floor" slightly overstates (pyforge-mason/testing-kit still resolve 3.12 without explicit pins — low, out of story scope)
- Rejected: .idea/*.iml noise on branch from unrelated commit; redundant re-verification of already-green lock; historical dream sibling files outside task-4 scope

### Follow-up review recommendation

`followup_review_recommended: false` — patched counts (high 0, medium 0, low 0); score 0.

## Verification

`pixi install --frozen -e python-agent-platform` and `-e dbgpt-sidecar`; `.github/workflows/platform-ci.yml` jobs; `pixi run -e local-recipes pixi-version-check`.
