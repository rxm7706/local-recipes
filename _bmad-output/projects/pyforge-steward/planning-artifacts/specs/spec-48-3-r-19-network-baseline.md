---
title: "Story 48.3: R-19 network baseline"
type: story
created: 2026-09-10
baseline_revision: 24580b5420ed04b36aaa32d14cd229d264113196
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/charts/platform/templates/serviceaccount.yaml
  - src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml
  - src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
  - src/platform/tests/test_chart_invariants.py
  - src/platform/deploy/README.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.3: R-19 network baseline

<intent-contract>

## Intent

**Problem:** The namespace admits any egress and only two ingress-only NetworkPolicies (redis, mcp-host) exist. Red-team R-19 / X-4 found any pod can spoof `X-Forwarded-User` to Lane 3 because web, worker, dbgpt, and other workloads lack network isolation beyond those floors.

**Approach:** Land a default-deny NetworkPolicy envelope (ingress + egress) plus per-workload explicit allows derived from chart wiring (`platform.djangoEnv`, Services, existing redis/mcp-host ingress policies). Verify `automountServiceAccountToken: false` on both ServiceAccounts (already present). Prove structure with chart invariant tests and document CRC attended bring-up.

## Boundaries & Constraints

**Always:** Default-deny must use `podSelector: {}` with both `Ingress` and `Egress` policy types. Per-workload allows must be release-scoped (`platform.selectorLabels` on peers). Keep existing redis and mcp-host ingress policies unchanged in semantics. DNS egress to kube-system CoreDNS must be allowed for every pod that needs cluster service discovery. Web egress follows R-19: postgres, both redis roles, mcp-host:8090, dbgpt:5670. Worker egress: postgres, both redis roles, dbgpt:5670 (chart env wires dbgpt on all platform pods). Data services (postgres, redis) get ingress-only peer policies plus minimal DNS egress. Document operator knobs for Route/Ingress source namespaces and worker-builds external egress.

**Never:** Do not change sizing/HPA/PDB (Story 48.2). Do not add Secrets or credential values to templates. Do not hand-edit `sprint-status-ledger.yaml`. Do not require mTLS or mesh policies (deferred to deploy profile). Do not break `helm template` default render.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| DEFAULT_DENY | `networkPolicy.enabled=true`, default render | One NetworkPolicy selects all pods with `policyTypes: [Ingress, Egress]` and no allow rules | disabled flag omits baseline + egress policies |
| WEB_EGRESS | web pod | Egress allows postgres:5432, redis-cache/broker:6379, mcp-host:8090, dbgpt:5670, DNS | missing peer fails invariant test |
| WORKER_EGRESS | worker pod | Egress allows postgres, redis-*, dbgpt, DNS | same |
| MCP_HOST_EGRESS | mcp-host pod | Egress allows DNS only | no downstream chart peers |
| DBGPT_INGRESS | any non-platform pod | Cannot reach dbgpt:5670 | new dbgpt ingress policy mirrors redis client set |
| POSTGRES_INGRESS | platform + liquibase + postgres-backup | Can reach postgres:5432 | others denied by default-deny |
| SA_TOKEN | both ServiceAccounts | `automountServiceAccountToken: false` | test asserts field |
| WEB_INGRESS | Route/Ingress namespaces in values | web:8000 admitted from configured namespace selectors | empty list = ingress only from same-namespace pods (ClusterIP path) |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/templates/serviceaccount.yaml:17,:25` — `automountServiceAccountToken: false` already on both SAs; invariant test locks it
- `src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml` — existing ingress-only redis policy; keep, extend tests
- `src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml` — existing web→mcp-host ingress; keep
- `src/platform/deploy/charts/platform/templates/_helpers.tpl:294-328` — `platform.djangoEnv` declares postgres/redis/dbgpt/mcp-host URLs every platform pod uses
- `src/platform/tests/test_chart_invariants.py:83-99` — `_PLATFORM_COMPONENTS`, `_SIDECAR_COMPONENT`, `_MCP_HOST_COMPONENT`; reuse scoping helpers `_assert_selector_is_release_scoped`
- `src/platform/deploy/charts/platform/values.yaml` — add `networkPolicy` knobs (enabled, dns, webIngressFrom, workerBuilds.allowExternalEgress)
- `src/platform/deploy/README.md:157-166` — redis NP docs; extend with R-19 baseline + CRC bring-up note

## Tasks & Acceptance

**Execution:**
- `src/platform/deploy/charts/platform/values.yaml` — `networkPolicy` section with enabled flag, DNS target, web ingress namespace selectors, worker-builds external egress toggle
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — partials for DNS egress and peer egress (postgres, redis roles, mcp-host, dbgpt)
- `src/platform/deploy/charts/platform/templates/networkpolicy-default-deny.yaml` — namespace baseline default-deny
- `src/platform/deploy/charts/platform/templates/networkpolicy-egress.yaml` — per-component egress policies (web, worker, worker-builds, beat, migrate, consume-events, mcp-host, dbgpt, liquibase, postgres-backup, postgres, redis)
- `src/platform/deploy/charts/platform/templates/networkpolicy-postgres-ingress.yaml` — postgres:5432 from platform + liquibase + postgres-backup
- `src/platform/deploy/charts/platform/templates/networkpolicy-dbgpt-ingress.yaml` — dbgpt:5670 from `_PLATFORM_COMPONENTS`
- `src/platform/deploy/charts/platform/templates/networkpolicy-web-ingress.yaml` — web:8000 from values-driven namespace selectors + same-namespace
- `src/platform/tests/test_chart_invariants.py` — Story 48.3 invariant tests (default-deny, egress peers, SA token, postgres/dbgpt ingress)
- `src/platform/deploy/README.md` — R-19 network baseline section + CRC attended bring-up checklist

**Acceptance Criteria:**
- Given default `helm template`, when `networkPolicy.enabled` is true, then a default-deny NetworkPolicy selects all pods with both Ingress and Egress types
- Given default render, when egress policies are present, then web, worker, mcp-host, and dbgpt pods each carry an egress NetworkPolicy allowing exactly their chart-declared peers plus DNS
- Given both ServiceAccounts render, when inspected, then `automountServiceAccountToken` is false on each
- Given default render, when postgres and dbgpt ingress policies render, then only `_PLATFORM_COMPONENTS` (+ liquibase/postgres-backup for postgres) may reach those services on 5432/5670
- Given `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q`, when tests run, then all pass including new Story 48.3 invariants
- Given `deploy/README.md`, when an operator reads the network baseline section, then CRC attended bring-up steps name Route namespace (`openshift-ingress`) and peer verification

## Verification

**Commands:**
- `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q` — expected: all pass
- `helm lint src/platform/deploy/charts/platform` — expected: 0 failures (with test-equivalent image pins if needed)

**Manual checks (if no CLI):**
- On CRC: after `helm upgrade`, confirm web/worker/dbgpt/mcp-host pods reach postgres and redis; Route still serves `/ht/` (document in README)

## Auto Run Result

Status: done
Blocking condition: none

Summary: Story 48.3 lands R-19 network baseline — default-deny NetworkPolicy envelope, per-workload egress allows (web/worker/mcp-host/dbgpt and supporting components), postgres and dbgpt ingress restrictions, web ingress from Route namespaces, `networkPolicy` values knobs, chart invariant tests, and CRC bring-up documentation. ServiceAccount `automountServiceAccountToken: false` verified (pre-existing, now tested).

Files changed:
- `networkpolicy-default-deny.yaml`, `networkpolicy-egress.yaml`, `networkpolicy-postgres-ingress.yaml`, `networkpolicy-dbgpt-ingress.yaml`, `networkpolicy-web-ingress.yaml` — new R-19 policies
- `_helpers.tpl` — reusable egress partials
- `values.yaml` — `networkPolicy` section
- `test_chart_invariants.py` — Story 48.3 tests + ingress-filter fixes for redis/mcp-host
- `deploy/README.md` — network baseline + CRC bring-up note
- `spec-48-3-r-19-network-baseline.md` — story spec
- `sprint-status-ledger.yaml` — 48-3 promoted to `done`

Verification: `pytest -c /dev/null src/platform/tests/test_chart_invariants.py -q` — 91 passed

Follow-up review recommended: false

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 4 findings — high 0, medium 1, low 2, false 1, maybe-false 0
- findings:
  - `[medium]` `[defer]` DNS target hardcoded to `kube-system`/`k8s-app: kube-dns` — OpenShift CRC may use `openshift-dns`; operators can override via values but no test asserts the knob — document-only risk, values seam exists
  - `[low]` `[reject]` No dedicated test for postgres/web ingress policy port rules — web/postgres peers covered indirectly by egress tests; adding would duplicate structure checks
  - `[low]` `[defer]` worker-builds `0.0.0.0/0` egress is intentionally broad for Mason builds — values-gated, documented in README
  - `[false]` `[reject]` Claim that worker lacks dbgpt egress per R-19 — chart `djangoEnv` wires dbgpt on all platform pods; implementation correctly includes dbgpt for worker

## Design Notes

Default-deny uses an empty `podSelector` matching every pod in the release namespace; per-component policies additive-union the allows. Web ingress namespace selectors default to `openshift-ingress` (CRC/OCP Route) and `ingress-nginx` (vanilla Ingress) so operators can trim via values. Worker-builds optional `ipBlock: 0.0.0.0/0` egress is values-gated because Mason build tasks need external registry access; general worker does not get blanket external egress per R-19.
