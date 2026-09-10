---
title: "Story 48.5: R-21 observability contract"
type: story
created: 2026-09-10
baseline_revision: 98ad1696e79dfcc530a8d74734f5e95f995300ca
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/platform/config/observability/
  - src/platform/deploy/charts/platform/
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.5: R-21 observability contract

<intent-contract>

## Intent

**Problem:** Red-team A-7 and B-5 found OTel traces and structlog exist but no SLO contract, no alert rules, and no metrics pipeline for Doctor's flag kill-switch — the Dream's "auto-rollback within 10 s" cannot fire because flags are a FILE resolver with no write path and no anomaly metrics.

**Approach:** Ship a machine-readable SLO contract (four signals: `/ht/` availability, MCP p99, Celery queue age, event-stream lag), expose Prometheus metrics for each signal on the web pod, render vanilla-Kubernetes alert rules from the chart as a ConfigMap (not a PrometheusRule CRD), and add a Doctor actuator that disables a named flag in the flags tree and increments a kill-switch counter metric.

## Boundaries & Constraints

**Always:** AD-11 vanilla-K8s core chart — alert rules land in a ConfigMap consumed by cluster Prometheus, never as a PrometheusRule CRD in the core chart. Metric names in the SLO contract must match the Prometheus series the app exports and the chart rules reference. The `/metrics` scrape path is unauthenticated like `/ht/` (kubelet/internal scrape only). Doctor's kill-switch is opt-in via explicit CLI (`doctor flags kill-switch --flag KEY --reason TEXT`); it never runs during ordinary `check`/`monitor`. Flag writes patch the local FILE tree only; production ConfigMap patch is documented, not automated in-cluster.

**Never:** Do not add Redis-backed flag resolver (deferred). Do not implement full auto-rollback evaluator (needs R-21 metrics first; semantic breaker stays deferred per spec-42-2). Do not change network policies (48.3) or sizing (48.2). Do not hand-edit `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HT_SLO_PASS | GET `/ht/` returns 200 within 500ms | `pyforge_health_check_success_total` increments; latency histogram observes ≤0.5s | Non-200 increments failure counter |
| MCP_P99 | POST `/stations/<name>/mcp` completes | `pyforge_mcp_request_duration_seconds` histogram observes duration | Errors still observe duration |
| QUEUE_AGE | Celery broker has pending tasks | `pyforge_celery_queue_oldest_age_seconds` gauge updated on probe | Redis unreachable → gauge not updated, probe logs warning |
| EVENT_LAG | Consumer group has pending entries | `pyforge_event_stream_lag_seconds` gauge reflects oldest pending idle | Missing stream → gauge 0 |
| FLAG_KILL | `doctor flags kill-switch --flag pyforge.three_surfaces --reason test` | Flag state → DISABLED in flags file; `pyforge_doctor_flag_kill_switch_total` increments | Missing flags path → exit 1 with message |
| CHART_RULES | `helm template` with defaults | ConfigMap `platform-observability-alerts` renders with four alert rules referencing contract metric names | `observability.enabled=false` omits ConfigMap |

</intent-contract>

## Code Map

- `src/platform/config/observability/slo-contract.yaml` — canonical SLO targets and metric name bindings (R-21)
- `src/platform/config/observability/metrics.py` — Prometheus registry, histograms/gauges/counters for four signals
- `src/platform/config/observability/__init__.py` — wire `configure_metrics()` into `configure_observability()`
- `src/platform/config/observability/middleware.py` — `/ht/` latency + success/failure counters
- `src/platform/config/urls.py` — expose `/metrics` (django-prometheus pattern or WSGI view)
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` — observe MCP dispatch duration
- `src/shared/packages/django-pyforge/src/django_pyforge/events/probes.py` — event lag gauge helper (new)
- `src/shared/packages/django-pyforge/src/django_pyforge/celery_probes.py` — queue age gauge helper (new)
- `src/platform/deploy/charts/platform/templates/observability-configmap.yaml` — alert rules ConfigMap
- `src/platform/deploy/charts/platform/values.yaml` — `observability.enabled`, SLO threshold overrides
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml` — prometheus scrape annotation on web pod
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/flag_kill_switch.py` — FILE write + metric increment
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — `flags kill-switch` subcommand
- `src/platform/tests/test_observability_contract.py` — SLO contract + metrics endpoint tests
- `src/platform/tests/test_chart_invariants.py` — Story 48.5 helm invariant tests
- `src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py` — actuator unit tests
- `pixi.toml` — add `prometheus_client` to `[feature.python-agent-platform.dependencies]`

## Tasks & Acceptance

**Execution:**
- `pixi.toml` — add `prometheus_client >=0.22.0` to python-agent-platform feature — metrics export dependency
- `src/platform/config/observability/slo-contract.yaml` — four SLO entries with targets and metric names
- `src/platform/config/observability/metrics.py` — register Prometheus metrics matching contract
- `src/platform/config/observability/middleware.py` — health-check observability middleware
- `src/platform/config/observability/__init__.py` — call `configure_metrics()` from `configure_observability()`
- `src/platform/config/urls.py` — add `/metrics` route
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` — wrap dispatch with duration observation
- `src/shared/packages/django-pyforge/src/django_pyforge/events/probes.py` — event lag probe function
- `src/shared/packages/django-pyforge/src/django_pyforge/celery_probes.py` — queue age probe function
- `src/platform/deploy/charts/platform/values.yaml` — observability section with enabled flag and thresholds
- `src/platform/deploy/charts/platform/templates/observability-configmap.yaml` — Prometheus alert rules as ConfigMap data
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml` — scrape annotation when observability enabled
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/flag_kill_switch.py` — kill-switch write path
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — `flags kill-switch` CLI
- `src/platform/tests/test_observability_contract.py` — contract parse + metrics smoke tests
- `src/platform/tests/test_chart_invariants.py` — Story 48.5 render/guard tests
- `src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py` — actuator tests

**Acceptance Criteria:**
- Given `slo-contract.yaml`, when parsed, then it declares SLO targets for `/ht/`, MCP p99, queue age, and event lag with matching Prometheus metric names
- Given a running web process with metrics enabled, when GET `/metrics`, then output includes the four contract metric families
- Given `helm template` with default values, when rendered, then ConfigMap `platform-observability-alerts` contains alert rules for all four SLO signals
- Given `doctor flags kill-switch --flag pyforge.three_surfaces --reason test`, when run against a temp flags file, then the flag state is DISABLED and kill-switch counter increments
- Given `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q -k story_48_5`, when tests run, then Story 48.5 invariants pass

## Verification

**Commands:**
- `pixi run -e platform-dev pytest -c /dev/null src/platform/tests/test_observability_contract.py -q` — expected: pass
- `pixi run -e platform-dev pytest -c /dev/null src/platform/tests/test_chart_invariants.py -q -k story_48_5` — expected: pass
- `pixi run -e pyforge-doctor pyforge-doctor-test -- -q -k flag_kill_switch` — expected: pass

**Manual checks (if no CLI):**
- `helm template` output includes observability ConfigMap with four alert rule groups

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[reject]` Doctor and platform both register `pyforge_doctor_flag_kill_switch_total` — acceptable; doctor CLI runs out-of-process and platform `/metrics` is the scrape surface

## Design Notes

Alert rules use ConfigMap (vanilla K8s) because `_VANILLA_KINDS` forbids PrometheusRule in the core chart. Cluster operators mount the ConfigMap into their Prometheus rule loader or use it as documentation until an overlay adds CRDs. Queue/event lag gauges refresh via a lightweight Celery beat task or management-command hook called from existing beat schedule — prefer extending beat rather than a new Deployment.

## Auto Run Result

Status: done
Blocking condition: none

Summary: Story 48.5 lands R-21 observability contract — machine-readable SLO contract YAML, Prometheus metrics for `/ht/`, MCP p99, Celery queue age, and event-stream lag, `/metrics` scrape endpoint, vanilla-K8s alert rules ConfigMap, beat probe task, and Doctor `flags kill-switch` actuator with metric increment.

Files changed:
- `src/platform/config/observability/*` — SLO contract, metrics, middleware, `/metrics` view
- `src/shared/packages/django-pyforge/...` — MCP timing, queue/event probes, observability hooks, beat probe task
- `src/platform/deploy/charts/platform/*` — observability ConfigMap + scrape annotations
- `src/shared/packages/pyforge-doctor/...` — flag kill-switch actuator + CLI
- Tests for contract, chart invariants, and doctor actuator
- `pixi.toml` / `pixi.lock` — `prometheus_client` dependency

Verification:
- `PYTHONPATH=src/platform:... pytest src/platform/tests/test_observability_contract.py` — 4 passed
- `pytest src/platform/tests/test_chart_invariants.py -k "story_48_5 or observability_disabled"` — 2 passed
- `pytest src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py` — 4 passed

Follow-up review recommended: false
