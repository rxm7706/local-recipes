---
title: "Sidecar runtime validation on Python 3.14"
type: "feature"
created: "2026-09-10"
status: "done"
updated: "2026-09-10"
review_loop_iteration: 1
baseline_revision: "d16d0f6a040914b682ceac7e7f5706c2bafedaca"
followup_review_recommended: false
review_loop_iteration: 0
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-43-6-platform-image-moves-to-python-3-14.md"
  - ".github/workflows/platform-ci.yml"
  - "src/platform/compose/dbgpt/Containerfile"
  - "pixi.toml"
warnings:
  - "Celery/Postgres round-trip is explicitly out of scope — owned by Stories 11.2/11.3; the sidecar env carries no celery/redis and this CI job starts no broker."
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Story 43.6 moved the platform and `dbgpt-sidecar` images to Python 3.14,
but `platform-ci`'s `container-dbgpt` job only polled `/api/health` for 200. That
proves liveness, not that DB-GPT's SQLite metadata store was created and migrated or
that the ASGI app serves real routes. Mason `DW-13-2-2` deferred this validation to
43.6; 43.6 closed without it, leaving the work unowned.

**Approach:** Extend `container-dbgpt` (docker AND podman matrix) with two assertions
after the health poll: (1) the SQLite metadata store exists under
`$HOME/.dbgpt/workspace/pilot/meta_data/`, is non-empty, and carries the
`alembic_version` table; (2) `/openapi.json` returns a well-formed schema advertising
at least one route. Do not add Celery/Postgres checks — that surface belongs to Stories
11.2/11.3 and this sidecar cannot satisfy it.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-7-sidecar-runtime-validation-on-python-3-14`. Both assertions run under
docker AND podman. Use container-exec probes that work in the minimal runtime image (no
`find`, no `sqlite3` on PATH — verified live).

**Block If:** Story 43.6 is not `done` (interpreter move must land first).

**Never:** A Celery REST round-trip in this job. Adding celery/redis to the sidecar env.
Assuming migration ran because `/api/health` returned 200.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Healthy boot with migrated store | Container reached `/api/health` 200 on 3.14 | SQLite file under `pilot/meta_data/*.db` exists, size > 0, binary grep finds `alembic_version` | CI step fails with `::error::` naming missing store, empty file, or absent alembic table |
| ASGI serving routes | Container healthy on port 5670 | `GET /openapi.json` succeeds; JSON `paths` has count ≥ 1 | CI fails if zero routes — alive socket but no serving |
| Podman rootless port mapping | `matrix.engine == podman` | Health and API URLs use `podman port` mapped host port, not hardcoded 5670 | Same failure semantics as docker |
| Celery/Postgres wiring | Any | Out of scope — not asserted | Documented in workflow comments; no step added |

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml:770-969` — `container-dbgpt` job: build, health poll, Story 43.7 SQLite + `/openapi.json` steps, arbitrary-UID contract probes, teardown. Lines 857-909 are the story-owned delta (added 2026-09-08, commit `182500bfbd0`).
- `src/platform/compose/dbgpt/Containerfile:136-537` — `$HOME/.dbgpt/workspace/pilot/meta_data/dbgpt.db` path resolution; verbatim Alembic template baked at build time so first boot runs real migration.
- `pixi.toml` — `[feature.dbgpt-sidecar]` env on `python = "3.14.*"` (Story 43.6); no celery/redis packages.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` — `DW-13-2-2` entry re-homed to this story; close when done.

## Tasks & Acceptance

**Execution:**
- `.github/workflows/platform-ci.yml` — confirm Story 43.7 steps present after health poll — implements SQLite store + API round-trip under both engines (already landed `182500bfbd0`; verify, do not duplicate).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-43-7-sidecar-runtime-validation-on-python-3-14.md` — promote to tracked story spec with verification evidence.
- Tier-3 `sprint-status.yaml` feed — set `43-7-sidecar-runtime-validation-on-python-3-14: done`; run `sprint-ledger-sync --project pyforge-steward`.

**Acceptance Criteria:**
- Given the `dbgpt-sidecar` container healthy on 3.14, when `container-dbgpt` runs, then it asserts the SQLite metadata store exists at its in-container path under `$HOME/.dbgpt/workspace`, is non-empty, and carries the `alembic_version` row.
- Given the container is healthy, when the job runs, then it asserts at least one real API round-trip beyond `/api/health` (`/openapi.json` with ≥1 route) returns well-formed content.
- Given the engine matrix, when CI runs, then both assertions execute under docker AND podman.
- Given scope boundaries, when read, then Celery/Postgres validation is explicitly absent and attributed to Stories 11.2/11.3.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - Implementation pre-landed on main (`182500bfbd0`, 2026-09-08). This run adds the tracked story spec, local verification evidence, and ledger closeout only — no code delta to review.

## Auto Run Result

Status: done

### Summary

Closed Story 43.7 after confirming the `container-dbgpt` runtime validation steps
already on main (`182500bfbd0`) satisfy every acceptance criterion. Local docker
verification reproduced both CI assertions: SQLite store at
`/app/.home/.dbgpt/workspace/pilot/meta_data/dbgpt.db` (479232 bytes,
`alembic_version` present) and `/openapi.json` with 288 routes.

### Files changed (this pass)

| File | Change |
|---|---|
| `spec-43-7-sidecar-runtime-validation-on-python-3-14.md` | Tracked story spec authored and closed |
| `sprint-status-ledger.yaml` | `43-7-sidecar-runtime-validation-on-python-3-14` → `done` |

### Verification (local)

- `docker build -f src/platform/compose/dbgpt/Containerfile -t dbgpt-sidecar-local .` — exit 0 (~29s)
- Health poll `/api/health` — 200 in ~7s
- SQLite metadata store probe — exit 0 (`alembic_version` grep matched)
- `/openapi.json` route count — 288 (≥ 1 required)
- `pixi run -e local-recipes story-status-check` — exit 0

### Residual risks

- **platform-ci not re-run in this session** — implementation landed 2026-09-08 with local verification noted in commit message; podman matrix not exercised locally (docker only).

### Follow-up review recommendation

`followup_review_recommended: false` — no patches applied; pre-landed code verified locally.

## Verification

**Commands:**
- `docker build -f src/platform/compose/dbgpt/Containerfile -t dbgpt-sidecar-local .` — expected: exit 0
- Run container, poll `/api/health`, then execute the two CI step scripts verbatim — expected: exit 0
- `pixi run -e local-recipes story-status-check` — expected: exit 0 after ledger sync

**Manual checks (if no CLI):**
- Confirm `.github/workflows/platform-ci.yml` lines 857-909 match the AC wording in epics.md Story 43.7.
