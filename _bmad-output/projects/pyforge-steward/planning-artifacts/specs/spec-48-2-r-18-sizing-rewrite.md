---
title: "Story 48.2: R-18 sizing rewrite"
type: story
created: 2026-09-10
baseline_revision: 16276eb21498d47eb88e9061e0686bd0b5af3d9c
status: done
review_loop_iteration: 0
followup_review_recommended: true
context:
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/deploy/charts/platform/templates/platform-deployment.yaml
  - src/platform/deploy/charts/platform/templates/worker-deployment.yaml
  - src/platform/deploy/charts/platform/templates/worker-builds-deployment.yaml
  - src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml
  - src/platform/deploy/charts/platform/templates/sidecar-deployment.yaml
  - src/platform/deploy/charts/platform/templates/liquibase-job.yaml
  - src/platform/deploy/charts/platform/templates/hpa.yaml
  - src/platform/deploy/charts/platform/templates/pdb.yaml
  - src/platform/tests/test_chart_invariants.py
  - src/platform/deploy/README.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.2: R-18 sizing rewrite

<intent-contract>

## Intent

**Problem:** The platform Helm chart ships BestEffort pods (`resources: {}` everywhere except redis-broker), no HPA, and no PodDisruptionBudgets. Red-team R-18/S-7/T-7 found the web tier is memory-bound (Langflow in-process RSS ~1.5–3 GiB) while workers are CPU-bound, and `ANYIO_MAX_THREADS` is unset — concurrency is asserted, not sized.

**Approach:** Land measured default requests/limits per workload in `values.yaml`, render HPA for web and general worker, add PDBs, override web gunicorn with `--preload` and explicit worker count, set `ANYIO_MAX_THREADS` on the web pod, and document that LLM inference is external (not in the platform image).

## Boundaries & Constraints

**Always:** Defaults must render under `helm template` without extra `--set`. Resource limits stay values-driven (not hardcoded in templates except validation). Vizro/BSL runs in the web pod — its memory is part of web sizing, not a separate Deployment. HPA targets web (`app.kubernetes.io/component: web`) and general worker only (not worker-builds). Chart invariant tests remain green; add `HorizontalPodAutoscaler` and `PodDisruptionBudget` to the vanilla-kinds allowlist.

**Never:** Do not add transformers/diffusers/llama.cpp to the platform image. Do not size NetworkPolicy (Story 48.3). Do not change redis-broker sizing semantics (Story 40.2). Do not hand-edit `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| WEB_SIZED | default `helm template` | web Deployment has requests+limits; gunicorn args include `--preload` and `--workers`; env `ANYIO_MAX_THREADS` set | empty web `resources.limits.memory` fails render |
| WORKER_SIZED | default render | general worker and worker-builds Deployments have requests+limits | missing worker limits fail render |
| SIDECAR_SIZED | default render | mcp-host, dbgpt sidecar, liquibase Job each have requests+limits | missing limits fail render |
| HPA_PRESENT | `autoscaling.web.enabled=true` | HorizontalPodAutoscaler for web and worker render | disabled HPA omits those objects |
| PDB_PRESENT | default render | PodDisruptionBudget for web and worker with minAvailable | — |
| LLM_EXTERNAL | values + README | sidecar.llm documents external inference; README states platform image excludes local LLM engines | — |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/values.yaml:10-35` — top-level `resources` is the web container seam; add `web.workers`, `web.preload`, `web.anyioMaxThreads`, `autoscaling`, `podDisruptionBudget`, and non-empty defaults for worker/mcpHost/sidecar/liquibase/worker.builds
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml:31-50` — web container uses image CMD today; add `args` for gunicorn `--preload`, env `ANYIO_MAX_THREADS`, `required` on resources
- `src/platform/deploy/charts/platform/templates/worker-deployment.yaml:70-73` — worker resources seam; add required validation
- `src/platform/deploy/charts/platform/templates/worker-builds-deployment.yaml:83-86` — builds pool resources
- `src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml:56-59` — mcp-host resources
- `src/platform/deploy/charts/platform/templates/sidecar-deployment.yaml:86-89` — DB-GPT sidecar resources; `sidecar.llm.*` passthrough
- `src/platform/deploy/charts/platform/templates/liquibase-job.yaml:43-46` — JVM Job resources
- `src/platform/deploy/charts/platform/templates/hpa.yaml` — **new** HPA for web + worker (`autoscaling/v2`)
- `src/platform/deploy/charts/platform/templates/pdb.yaml` — **new** PDB for web + worker
- `src/platform/tests/test_chart_invariants.py:44-57` — `_VANILLA_KINDS` must include HPA/PDB kinds
- `src/platform/deploy/README.md:228` — "No HPA/PDB" line is stale; add LLM-external note

## Tasks & Acceptance

**Execution:**
- `src/platform/deploy/charts/platform/values.yaml` — per-pod sizing defaults, autoscaling and PDB knobs, web gunicorn/ANYIO settings, LLM-external comment on `sidecar.llm`
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml` — gunicorn args with `--preload`, `ANYIO_MAX_THREADS`, required resources
- `src/platform/deploy/charts/platform/templates/worker-deployment.yaml` — required resources
- `src/platform/deploy/charts/platform/templates/worker-builds-deployment.yaml` — required resources
- `src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml` — required resources
- `src/platform/deploy/charts/platform/templates/sidecar-deployment.yaml` — required resources
- `src/platform/deploy/charts/platform/templates/liquibase-job.yaml` — required resources
- `src/platform/deploy/charts/platform/templates/hpa.yaml` — HPA for web and worker
- `src/platform/deploy/charts/platform/templates/pdb.yaml` — PDB for web and worker
- `src/platform/tests/test_chart_invariants.py` — allowlist + sizing/HPA/PDB invariant tests
- `src/platform/deploy/README.md` — document HPA/PDB and external LLM inference

**Acceptance Criteria:**
- Given default `helm template`, when the core chart renders, then web, worker, worker-builds, mcp-host, dbgpt sidecar, and liquibase Job each carry non-empty requests and limits
- Given default values, when web Deployment renders, then gunicorn args include `--preload` and `--workers`, and `ANYIO_MAX_THREADS` is set on the web container
- Given default values, when the chart renders, then HorizontalPodAutoscaler objects exist for web and general worker, and PodDisruptionBudget objects exist for both
- Given the chart README, when an operator reads sizing guidance, then LLM inference is stated as external (Ollama/Tachyon/vLLM) and not bundled in the platform image
- Given `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q`, when tests run, then all pass including new sizing invariants

## Verification

**Commands:**
- `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q` — expected: all pass
- `helm lint src/platform/deploy/charts/platform src/platform/deploy/overlays/ocp/chart` — expected: 0 chart(s) failed (requires digest/tag and flags.tree like CI tests)

## Auto Run Result

Status: done
Blocking condition: none

Summary: Story 48.2 lands R-18 sizing — per-pod requests/limits defaults for web, worker, worker-builds, mcp-host, dbgpt sidecar, and liquibase; web gunicorn `--preload` with explicit workers; `ANYIO_MAX_THREADS`; HPA on web and general worker; PDBs on web and worker; external-LLM documentation in README/values.

Files changed:
- `values.yaml` — sizing defaults, web/autoscaling/PDB knobs, LLM-external comment
- `platform-deployment.yaml` — gunicorn args, ANYIO env, required memory limit
- `worker-*`, `mcp-host`, `sidecar`, `liquibase` templates — required memory limits
- `hpa.yaml`, `pdb.yaml` — new autoscaling and disruption budgets
- `test_chart_invariants.py` — vanilla-kinds allowlist + Story 48.2 invariant tests
- `deploy/README.md` — sizing/HPA/PDB and external LLM note
- `spec-48-2-r-18-sizing-rewrite.md` — story spec (this file)
- `sprint-status-ledger.yaml` — 48-2 promoted to `done`

Review: 5 medium patches applied (HPA guards, 3 new tests, header fix, workers guard); 3 low deferred (beat/events/migrate sizing, README knobs, metrics-server note); 2 false rejected.

Follow-up review recommended: true (four medium patches on first pass — HPA validation and test coverage gaps)

Verification: `pytest test_chart_invariants.py` — 86 passed; `helm lint` passes when invoked with test-equivalent image digests (CI harness path).

Residual risks: beat/consume-events/migrate remain BestEffort (deferred); cluster operators need metrics-server for memory-based web HPA.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 5, low 3, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` HPA could render with empty metrics when targets are falsy — added fail guards and `if` checks in `hpa.yaml`
  - `[medium]` `[patch]` No test that worker-builds is excluded from HPA — extended Story 48.2 test to assert exactly 2 HPAs and none target worker-builds
  - `[medium]` `[patch]` Disabled autoscaling path untested — added `test_autoscaling_disabled_omits_hpa`
  - `[medium]` `[patch]` Worker memory limit refusal untested — added `test_worker_memory_limit_is_required`
  - `[medium]` `[patch]` Stale platform-deployment header claimed no args override — fixed comment
  - `[low]` `[patch]` Web `--workers` value not asserted — test now checks rendered value is `"2"`
  - `[low]` `[patch]` `web.workers` must be > 0 — added template guard
  - `[low]` `[defer]` beat/consume-events/migrate still BestEffort — out of story scope (named workloads only)
  - `[false]` `[reject]` Only limits.memory validated — defaults ship full requests+limits; AC satisfied on default render
  - `[false]` `[reject]` PDB minAvailable exceeds replicas at 1:1 — valid for single-replica guard
  - `[low]` `[defer]` README missing autoscaling knob reference — sizing bullet covers essentials
  - `[low]` `[defer]` metrics-server dependency undocumented — operational concern, not chart defect

## Design Notes

Web memory defaults (request 2Gi / limit 4Gi) assume Langflow in-process idle RSS 1.5–3 GiB with gunicorn `--preload` and 2 uvicorn workers — Vizro/BSL dashboard memory is included in the web pod (no separate Deployment). Worker defaults bias CPU (request 1 / limit 4 cores) because rattler-build work lives on worker-builds (limit 4 CPU / 8Gi). `ANYIO_MAX_THREADS=40` matches anyio's documented default ceiling, set explicitly so operators can tune against measured Langflow blocking.
