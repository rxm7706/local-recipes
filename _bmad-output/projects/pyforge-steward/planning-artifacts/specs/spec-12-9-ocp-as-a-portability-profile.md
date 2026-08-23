---
title: 'OCP as a portability profile'
type: 'infra'
created: '2026-08-23'
status: 'ready'
baseline_revision: '64714743fe'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md'
  - '{project-root}/docs/dreams/ocp-as-a-portability-profile.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-2-gke-as-a-portability-profile.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/cluster-bringup-facts.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 12.1 shipped a vanilla core chart plus a thin OCP overlay (`src/platform/deploy/overlays/ocp/`) verified only by `helm template` / invariant tests — `deploy/README.md`'s "Honest limitations" still names "No OCP live-cluster verification in this repo." Story 12.2's `gke-portability-smoke` closed the vanilla-Kubernetes Ingress path on `kind`; AD-11's OCP-first portability clause remains unproven in CI. `kind` cannot substitute: it has no `route.openshift.io/v1` admission and no `restricted-v2` SCC behavior.

**Approach:** Add an optional job to `.github/workflows/platform-ci.yml` (`ocp-portability-smoke`) that starts a real OpenShift API via OpenShift Local (CRC), pushes the shared `build-platform-image` artifact into the cluster internal registry, installs the core chart with `-f overlays/ocp/core-overrides.yaml` plus the `platform-ocp` Route chart, and curls `/ht/` and `/admin/login/` through the Route hostname (router edge TLS) — proving the OCP overlay path end-to-end. Default **off** on PR/push (repo var + workflow_dispatch), same opt-in pattern as `gke-portability-smoke` and `air-gap-parity`.

## Boundaries & Constraints

**Always:**
- Deploy the exact core chart at `src/platform/deploy/charts/platform/` — OCP deltas only via the existing checked-in `src/platform/deploy/overlays/ocp/core-overrides.yaml` and the sibling Route chart at `src/platform/deploy/overlays/ocp/chart/` (AD-11: OCP is an overlay, unlike GKE's inline `--set`-only profile).
- helm, kubectl, and `oc` on the runner: helm/kubectl from the `platform-dev` pixi environment (AD-16) via `prefix-dev/setup-pixi@v0.10.0`, `environments: platform-dev`, `pixi-version: v0.77.0`, `locked: true`, `cache: true` — mirrors `gke-portability-smoke` and `dashboard.yml`.
- CRC / OpenShift Local is a named system-level exception alongside `kind` (AD-16). Pin CRC **2.63.0** bundling OpenShift **4.22.7** — the baseline in `cluster-bringup-facts.md` (Story 12.4 orbit). Do not float `latest` CRC/OCP bundles (known cert/pull-secret flake history on unpinned bundles).
- Image path: load the `platform-ci-image` artifact from `build-platform-image`, retag, and push to the CRC internal registry (`default-route-openshift-image-registry.apps-crc.testing/<project>/…`) using the operator-locked flow documented in `cluster-bringup-facts.md` — chart `image.repository`/`image.tag` seams must point at that ImageStream, not `kind load`.
- Smoke assertions go THROUGH the admitted Route (HTTPS curl to the Route host, e.g. `platform-smoke.apps-crc.testing`) — never `kubectl port-forward`, never a direct Service ClusterIP curl, or the job proves nothing beyond 12.1's parsed-manifest tests.
- Reuse `gke-portability-smoke`'s established deploy sequencing: no `helm install --wait` (Langflow schema / migrate hook deadlock — see spec-12-2 Spec Change Log); explicit `kubectl wait` for `job/platform-migrate` before the ORM-backed `/admin/login/` assertion; `/ht/` retry loop may run before migrate completes (connectivity-only).
- Extend `build-platform-image`'s `if:` gate so it runs when OCP smoke is enabled (same OR as GKE + air-gap). Job `needs: build-platform-image`.
- Opt-in controls: repo variable `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true`; workflow_dispatch boolean `ocp_portability_smoke`; default false on both PR and push.
- Single engine (Docker) for image load/push — `container`'s docker+podman matrix is not duplicated here.
- `CRC_PULL_SECRET` GitHub Actions secret (Red Hat pull secret from console.redhat.com/openshift/create/local) — required for real OpenShift bundles; document in workflow comment, never commit.
- Free disk space step early (same toolchain reclaim list as `gke-portability-smoke`) — CRC preset needs ~35 GiB disk; hosted runners exhaust quickly without reclaim.
- `if: always()` teardown — `crc stop` / cluster delete / namespace cleanup.
- Runs under the same workflow-level `paths:` filter as sibling platform jobs; PR adds `maintenance` label (AD-15).

**Block If:**
- CRC cannot start on the chosen runner class after a good-faith attempt (OpenShift Local docs exclude Ubuntu/Debian for the desktop path; verify `crc-org/crc-github-action@v1` on `ubuntu-latest` in implementation — if it fails, the job MUST document and use a labeled self-hosted runner e.g. `runs-on: [self-hosted, linux, ocp-crc]` rather than silently skipping or faking success).
- `CRC_PULL_SECRET` is absent when the job is enabled — fail fast with a clear annotation naming the required secret.

**Never:**
- Never add OCP kinds or apiVersions to the core chart — Route stays overlay-only (AD-11).
- Never weaken or bypass `test_chart_invariants.py` assertions — this story's surface is CI + deploy README honesty update only.
- Never make the job default-on for PRs — CRC cost/flake belongs behind explicit opt-in (learned from gke/air-gap default-off merge in PR #622).
- Never claim Story 12.7 complete — sidecar (12.5), Redis hardening (12.6), and full attended contingencies stay 12.7's scope.
- Never duplicate the full `spec-local-ocp-hybrid-environment` bring-up doc — consume `cluster-bringup-facts.md`; Story 12.4 lands the human runbook separately.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | CRC Running, image pushed to internal registry, core+overlay installed | `curl -sk https://<route-host>/ht/` returns 200 through the Route; after migrate completes, `/admin/login/` returns 200 | n/a |
| OCP overrides applied | Core installed with `core-overrides.yaml` | Ingress disabled in render; postgres/redis pods have null `runAsUser`/`fsGroup`; web/worker/migrate retain restricted-v2 without fixed UID | job asserts rendered pod specs or live `oc get pod … -o jsonpath` for data pods |
| Migration window | Fresh install; migrate Job still running when `/ht/` first polled | `/ht/` may 200 before migrations finish | ORM assertion gated on `kubectl wait job/platform-migrate` |
| helm --wait deadlock | Same as GKE job | `helm install` without `--wait`; web pod may crash once until `langflow_schema` exists | retry loop on `/ht/`; migrate wait before `/admin/login/` |
| Missing pull secret | Job enabled, secret unset | Job fails at CRC start with explicit error naming `CRC_PULL_SECRET` | fail fast |
| CRC start timeout | Bundle download or `crc start` exceeds job budget | Job fails with `crc`/`oc` diagnostics | `timeout-minutes: 90` minimum; log `crc status`, `oc get co` snippet |
| Data images under SCC | Official postgres:17 / redis:7 with nulled UIDs | Pods reach Running under restricted-v2 | on failure, log SCC events + pod describe; record contingency in job summary (RH/bitnami fallback is 12.7 ladder, not required for first green if official images work on CRC) |

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml` — add job `ocp-portability-smoke`; extend `build-platform-image` `if:`; add workflow_dispatch input `ocp_portability_smoke`; document repo var `PLATFORM_CI_OCP_PORTABILITY_SMOKE` in workflow header comment
- `.github/workflows/platform-ci.yml` `gke-portability-smoke` — sibling pattern for disk reclaim, pixi setup, artifact download, secret creation, helm install sequencing, migrate wait, curl retries, teardown
- `.github/workflows/platform-ci.yml` `build-platform-image` — fan-in target; extend enablement OR for OCP var/input
- `src/platform/deploy/overlays/ocp/core-overrides.yaml` — `ingress.enabled: false`; postgres/redis UID nulls (read-only; job applies with `-f`)
- `src/platform/deploy/overlays/ocp/chart/` — Route-only overlay; default `route.service.name: platform`
- `src/platform/deploy/overlays/ocp/README.md` — two-step install commands the job automates
- `src/platform/deploy/charts/platform/values.yaml` — `image.repository` / `image.tag` / `django.secureSslRedirect` seams; internal-registry repository path at install time
- `src/platform/deploy/README.md` — update "Honest limitations" when job lands (scope OCP-unverified claim narrowly, mirror 12.2 README edit)
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/cluster-bringup-facts.md` — CRC version pins, internal-registry push commands, login flow (copy verbatim into CI steps)
- `spec-python-agent-platform/ARCHITECTURE-SPINE.md` — AD-11, AD-15, AD-16 binding constraints

## Tasks & Acceptance

**Execution:**
- `.github/workflows/platform-ci.yml` — extend `build-platform-image` to run when `PLATFORM_CI_OCP_PORTABILITY_SMOKE` or `ocp_portability_smoke` is true
- `.github/workflows/platform-ci.yml` — add `ocp-portability-smoke` job: checkout → disk reclaim → setup-pixi (`platform-dev`) → CRC start (`crc-org/crc-github-action@v1` or equivalent pinned action, preset `openshift`, cpus 4, memory 10752, disk 35, version 2.63.0, pull-secret from `secrets.CRC_PULL_SECRET`) → download/load/tag/push platform image to internal registry → `oc create namespace platform-smoke` + `platform-secrets` Secret (same key shape as GKE job / NOTES.txt) → `helm install platform … -f overlays/ocp/core-overrides.yaml` with registry image overrides + `django.secureSslRedirect=False` → `helm install platform-ocp …/overlays/ocp/chart` with Route host set → `/ht/` Route curl retry → `kubectl wait job/platform-migrate` → `/admin/login/` Route curl → optional SCC/UID spot-check on postgres pod → teardown
- `src/platform/deploy/README.md` — reword OCP live-cluster limitation to name `ocp-portability-smoke` as the automated proof surface (keep 12.7 contingencies honest)

**Acceptance Criteria:**
- Given CRC Running and the job enabled, when core installs with `core-overrides.yaml` and the Route overlay installs beside it, then a `route.openshift.io/v1` Route exists targeting the core web Service and admits traffic
- Given the installed release, when the job curls `/ht/` through the Route hostname (HTTPS, no port-forward), then it receives 200 within the retry budget
- Given the migrate hook Job has completed, when the job curls `/admin/login/` through the same Route path, then it receives 200
- Given postgres/redis pods are Running, when their securityContext is inspected, then they carry no fixed `runAsUser` (SCC-assigned UID path the overrides enable)
- Given the job is not opted in (default), when Platform CI runs on a PR, then `ocp-portability-smoke` and `build-platform-image` (for OCP-only enablement) are skipped
- Given the job completes (success or failure), when teardown runs, then the CRC instance is stopped/deleted (`if: always()`)

## Design Notes

**Why not kind:** Vanilla Kubernetes cannot validate OpenShift Routes or SCC admission. A fake Route CRD on kind would not exercise the router or SCC webhook behavior 12.1 honestly left unverified.

**Sibling symmetry with 12.2:**

| Layer | GKE (`gke-portability-smoke`) | OCP (`ocp-portability-smoke`) |
|-------|-------------------------------|-------------------------------|
| Cluster | kind + ingress-nginx | CRC / OpenShift Local |
| Chart surface | core only, scalar `--set` | core + `core-overrides.yaml` + Route chart |
| Edge | Ingress + `Host:` header | Route + router TLS |
| Image delivery | `kind load docker-image` | internal registry push |
| Default | off (`PLATFORM_CI_GKE_PORTABILITY_SMOKE`) | off (`PLATFORM_CI_OCP_PORTABILITY_SMOKE`) |

**Operator enablement (post-merge):**

```bash
gh secret set CRC_PULL_SECRET --repo rxm7706/local-recipes < pull-secret.txt
gh variable set PLATFORM_CI_OCP_PORTABILITY_SMOKE --body true --repo rxm7706/local-recipes

gh workflow run platform-ci.yml --ref main \
  -f jobs=all \
  -f ocp_portability_smoke=true \
  -f gke_portability_smoke=false \
  -f air_gap_parity=false
```

**Relationship to Epic 12 extension (12.4–12.8):** Story 12.4 documents attended bring-up; this story automates the deploy/smoke slice for CI. Story 12.7 remains the attended closeout for chart extensions and contingency recording after 12.5–12.6.

## Verification

**Commands (implementation phase):**
- `pixi run -e platform-dev helm lint src/platform/deploy/charts/platform src/platform/deploy/overlays/ocp/chart` — expected: 0 errors
- Local CRC dry run following the job's steps (operator workstation) — expected: Route curls return 200 before CI merge
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/platform-ci.yml'))"` — workflow parses

**Manual checks:**
- Confirm the new job references `overlays/ocp/` but does not edit core chart templates
- Confirm no OCP job runs without `CRC_PULL_SECRET` when enabled
- First green GitHub Actions run on opted-in workflow_dispatch — record run URL in Spec Change Log at implementation time

## Spec Change Log

- **2026-08-23:** Dream + spec authored from operator request to add automated OCP/OpenShift Platform CI (post PR #622 merge). Status `ready`; baseline `64714743fe` (main after steward 12.3 air-gap parity).
