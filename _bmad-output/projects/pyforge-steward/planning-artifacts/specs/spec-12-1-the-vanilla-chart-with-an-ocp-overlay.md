---
title: 'The vanilla chart with an OCP overlay'
type: 'infra'
created: '2026-08-21'
status: 'in-review'
baseline_revision: '3783e63bc5b70a2806be2e432a6fd1784a219105'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md', '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The platform image (Story 10.3) proves the OCP `restricted-v2` contract and the compose stack (10.3/10.5/11.3) proves local wiring, but nothing can deploy the platform onto Kubernetes — CAP-6/AD-11's "vanilla core chart + thin OCP Route overlay" exists only as an architecture decision.

**Approach:** A Helm core chart under `src/platform/deploy/charts/platform/` holding only plain Kubernetes resources (Deployment/Service/Ingress, StatefulSet for PostgreSQL, a migrate hook Job, ServiceAccount), a thin OCP overlay under `src/platform/deploy/overlays/ocp/` (a Route-only chart + core-chart value overrides), and a pytest module that parses `helm template` output and asserts the AC's invariants — with guard-removed companions per the 9.6 discipline.

## Boundaries & Constraints

**Always:** Nothing OCP-specific in the core chart — no `route.openshift.io`/OpenShift kinds or apiVersions anywhere in it (AD-11); Route lives only in the overlay. Platform-image pods (web, worker, migrate) carry the `restricted-v2` contract hardcoded in templates: `runAsNonRoot: true`, NO `runAsUser` anywhere in those pod specs (OCP assigns an arbitrary UID; the image's own `USER 1001:0` covers vanilla K8s), `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`. Namespace inventory is exactly PostgreSQL + Redis + the platform image (AD-1; story AC) — the epics.md 12.1 text, unchanged by the 2026-08-21 sprint-change proposal, is the binding contract. Credentials only by reference to a pre-created K8s Secret (AD-12): the chart never renders a Secret and values carry no credential defaults. Image references fully parameterized (registry-relocatable, CAP-6). helm/kubectl come from the `platform-dev` pixi env (AD-16), and Helm 4.x CLI compat is verified live, not assumed. Migrate runs as a `post-install,pre-upgrade` hook Job, never in the image CMD (Containerfile contract: concurrent replicas must not race migrations).

**Block If:** the AC's restricted-v2 fields cannot be expressed without an OCP-specific resource in the core chart; or the invariant tests cannot be made to fail (vacuous assertions — a spec-level defect).

**Never:** No DB-GPT sidecar in the chart — the sprint-change proposal explicitly deferred extending 12.1/12.3's inventory ("no story text changes proposed yet; revisit at Epic 12 kickoff"); adding it would contradict this story's AC. No GKE/kind CI profile (Story 12.2) and no air-gap check (12.3). No live-cluster deploy claim — no cluster exists here (AD-16 Tier 3 is attended-only); say so in Verification. Never commit pixi/lock/manifest changes, push, open PRs, or touch sprint ledgers. No speculative extras (no HPA/PDB/NetworkPolicy/media PVC).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Core chart renders vanilla | `helm template` core chart, default values | Only plain kinds (Deployment/StatefulSet/Service/Ingress/Job/ServiceAccount); zero OpenShift kinds/apiVersions | N/A |
| OCP overlay renders thin | `helm template` overlay chart | Exactly Route resource(s), nothing else | N/A |
| restricted-v2 on platform pods | Rendered web/worker/migrate pod specs | runAsNonRoot, no runAsUser, RuntimeDefault seccomp, no privilege escalation, drop ALL — on every container | N/A |
| Namespace inventory | All rendered workload pod specs | Exactly three images: postgres, redis, platform | N/A |
| Guard removed (9.6) | Synthetic pod spec with `runAsUser` / doc set containing a Route fed to the same helpers | Helpers raise `AssertionError` | Proves the real checks can fail |
| helm absent (pip-only CI lane) | `test` job, no helm on PATH | helm-dependent tests skip naming the missing capability; dict-fed companions still run | Never a silent pass |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/` -- NEW core chart (Chart.yaml, values.yaml, .helmignore, templates/)
- `src/platform/deploy/overlays/ocp/` -- NEW thin overlay: `chart/` (Route-only chart) + `core-overrides.yaml` (values for the core chart on OCP: null data-service UIDs, ingress off)
- `src/platform/deploy/README.md` -- NEW install/usage doc incl. required Secret keys and honest OCP notes
- `src/platform/tests/test_chart_invariants.py` -- NEW invariant suite (parses `helm template` output)
- `.dockerignore` -- extend the Story 10.3 platform section: `src/platform/deploy/` is deploy-time-only, same rule as `compose/`
- `src/platform/Containerfile` -- read-only image contract: entrypoint sourcing, `/app/.home` HOME, `USER 1001:0`, port 8000, gunicorn CMD without migrate
- `src/platform/compose/compose.yml` -- read-only env-wiring reference (DATABASE_URL/REDIS_URL/DJANGO_* surface, worker command, migrate-before-serve rationale)
- `src/platform/config/urls.py` + `config/fastapi_app.py` -- read-only probe contract: `/ht/` = DB+cache readiness, `/api/health` = unconditional liveness

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/deploy/charts/platform/{Chart.yaml,values.yaml,.helmignore,templates/_helpers.tpl,templates/NOTES.txt,templates/serviceaccount.yaml}` -- scaffold core chart; values: image (registry-relocatable), replicaCount, existingSecret name (keys `DJANGO_SECRET_KEY`/`DATABASE_URL`/`POSTGRES_PASSWORD`), django (allowedHosts/adminUrl/secureSslRedirect), service, ingress, worker, migrate, postgres (image/auth/persistence/uid), redis (image/uid); restricted-v2 blocks live in `_helpers.tpl`, not values
- [x] `src/platform/deploy/charts/platform/templates/{platform-deployment.yaml,platform-service.yaml,worker-deployment.yaml,migrate-job.yaml,ingress.yaml}` -- platform workloads: gunicorn web Deployment (probes: liveness `/api/health`, readiness `/ht/`, both with `Host` + `X-Forwarded-Proto: https` httpHeaders per `SECURE_PROXY_SSL_HEADER`), Celery worker Deployment (`celery -A config worker -l info`, no probes — no HTTP surface), migrate hook Job (`manage.py migrate --noinput`, `post-install,pre-upgrade`, OnFailure restart + backoffLimit absorbing the postgres-boot race compose documents), networking.k8s.io/v1 Ingress (values-gated)
- [x] `src/platform/deploy/charts/platform/templates/{postgres-statefulset.yaml,postgres-service.yaml,redis-deployment.yaml,redis-service.yaml}` -- data services: postgres:17 StatefulSet + volumeClaimTemplate (PGDATA subdir) + pg_isready probes, redis:7 Deployment (emptyDir, redis-cli ping probes); restricted fields fixed, only runAsUser/fsGroup values-driven (official images' UID 999 on vanilla; nulled by the OCP overrides so the SCC assigns them)
- [x] `src/platform/deploy/overlays/ocp/{chart/Chart.yaml,chart/values.yaml,chart/templates/route.yaml,core-overrides.yaml,README.md}` -- thin overlay: `route.openshift.io/v1` Route pointing at the core Service (name/port + TLS values), plus core-chart overrides for OCP
- [x] `src/platform/deploy/README.md` -- install commands (pixi-provisioned helm), pre-created Secret contract, vanilla-vs-OCP flows, honest limits (no cluster verification; official postgres/redis images may need image overrides under restricted-v2 — documented, not solved here)
- [x] `src/platform/tests/test_chart_invariants.py` -- parse `helm template` (helm-gated skip naming the capability, 11.4 convention; `yaml` imported post-gate so the pip-only lane collects clean) and assert every I/O-Matrix invariant via shared helpers; dict-fed guard-removed companions run ungated; ruff/mypy-clean under the platform gates
- [x] `.dockerignore` -- add `src/platform/deploy/` to the Story 10.3 section with a one-line rationale

**Acceptance Criteria:**
- Given the `platform-dev` env's Helm 4.x, when `helm lint` runs on the core and overlay charts, then both pass (verifies AD-16 CLI compat live)
- Given default values, when the core chart renders, then it contains zero OCP-specific kinds/apiVersions, and the Route renders only from the overlay chart
- Given rendered web/worker/migrate pod specs, when inspected, then each satisfies restricted-v2 (runAsNonRoot, no fixed UID anywhere, RuntimeDefault seccomp, allowPrivilegeEscalation false, drop ALL) and the whole render references exactly the postgres, redis, and platform images
- Given the invariant helpers, when fed synthetic violating manifests, then they raise — the suite can fail (9.6)
- Given the pip-only CI lane (no helm), when the suite collects, then helm-dependent tests skip with a capability-naming reason and companions still run

## Spec Change Log

## Review Triage Log

## Design Notes

Two charts, not one values-gated template: a `route.enabled` flag would put OCP content inside the core chart, violating the AC's "nothing in the core chart is OCP-specific" literally, and kind-allowlist tests would need carve-outs. The overlay chart is installed beside the core release; `core-overrides.yaml` is the other half of "overlay" — the value deltas OCP needs from the same core chart.

restricted-v2 blocks are template-fixed rather than values-driven: the AC makes them an invariant, and a values knob would be an invitation to regress them silently; the data services get the narrowest values seam (runAsUser/fsGroup only) because the official postgres/redis images need a numeric non-root UID for vanilla K8s `runAsNonRoot` kubelet verification, while OCP forbids fixing one.

The DB-GPT sidecar (AD-6 bounded exception, PVC + singleton) is deliberately absent: the 2026-08-21 sprint-change proposal flagged Epic 12's sidecar coverage "for awareness — no story text changes proposed yet", and this story's AC inventory stayed "PostgreSQL, Redis and the platform image". Its chart membership is Epic-12 follow-up work (12.3 parity or a correct-course pass), not silent scope growth here.

`DATABASE_URL` comes whole from the operator's Secret (not composed in templates): composing user:pass@host in a template would force the chart to read the password value, and AD-12 keeps secret material out of render paths entirely. NOTES.txt prints the expected service DNS names so the operator can build it.

**Dev Notes -- implementation, 2026-08-21 (Story 12.1):** built exactly the two-chart shape: core chart `src/platform/deploy/charts/platform/` (Chart.yaml apiVersion v2; values.yaml with image/existingSecret/django/service/ingress/worker/migrate/postgres/redis and no speculative knobs; `_helpers.tpl` carrying fullname/labels/imageRef plus the HARDCODED restricted-v2 pod+container blocks and the shared `platform.djangoEnv`; templates for web Deployment w/ `/api/health` liveness + `/ht/` readiness probes both sending `Host: <first allowed host>` + `X-Forwarded-Proto: https` httpHeaders, worker Deployment (`celery -A config worker -l info` as `args` through the image ENTRYPOINT, no probes), migrate hook Job (`post-install,pre-upgrade`, before-hook-creation, OnFailure + backoffLimit 6, `python manage.py migrate --noinput` as `args`), values-gated networking.k8s.io/v1 Ingress, postgres:17 StatefulSet (volumeClaimTemplate `data`, PGDATA subdir, pg_isready exec probes, restricted fields fixed + ONLY runAsUser/fsGroup values-driven at 999), redis:7 Deployment (emptyDir /data, redis-cli ping probes, runAsUser 999 seam), Services, one ServiceAccount, NOTES.txt printing the Secret contract + service DNS names + the two-flow hint) and the thin overlay `src/platform/deploy/overlays/ocp/` (`chart/` = `platform-ocp`, sole template a `route.openshift.io/v1` Route with values-documented service-name coupling + edge-TLS defaults; sibling `core-overrides.yaml` = ingress off + postgres/redis UIDs nulled; READMEs at `deploy/` and `overlays/ocp/`). `.dockerignore` gained `src/platform/deploy/` in the Story 10.3 section. Verification, all real: `pixi run -e platform-dev helm lint <core> <overlay>` -> "2 chart(s) linted, 0 chart(s) failed" (Helm v4.2.4+conda-forge, AD-16 CLI compat live); `helm template test-release <core>` -> renders, `grep -c openshift.io` = 0, kinds = 3 Deployment / 1 Ingress / 1 Job / 3 Service / 1 ServiceAccount / 1 StatefulSet; `helm template <core> -f core-overrides.yaml` -> renders, zero `kind: Ingress`, zero runAsUser FIELDS (the two remaining grep hits are template comments; the parsed-YAML test asserts zero keys); `helm template test-route <overlay>` -> exactly one document, `kind: Route` / `apiVersion: route.openshift.io/v1`. Test module `tests/test_chart_invariants.py`: 6 helm-gated real proofs (lint, vanilla-kinds allowlist + no-openshift-apiVersion, Route-only overlay, restricted-v2 over web/worker/migrate incl. proving the hook Job renders, exact three-image AD-1 inventory DERIVED from values.yaml, overrides render = no Ingress + no runAsUser anywhere w/ postgres+redis presence anti-vacuity) + 4 ungated pure-dict guard-removed companions -- helm-present run **10 passed in 0.42s**; helm-stripped-PATH run (same interpreter) **4 passed + 6 skipped**, every skip reason verbatim "helm not on PATH (AD-16: provided by the platform-dev pixi env) -- chart render/lint tests need it"; helm-present/yaml-absent (ImportError shim shadowing PyYAML) **5 passed + 5 skipped** with reason "PyYAML not installed (pip-only CI lane) -- chart render tests parse `helm template` output with it" (the shim provokes a PytestDeprecationWarning about found-but-failing import; a genuinely absent PyYAML raises ModuleNotFoundError and skips warning-free). Whole-suite coexistence: `pytest --collect-only -q` from `src/platform` collects **59 tests** (49 pre-existing + 10 new); the full live `pytest -v` was NOT run -- the 11.4 isolation suite needs live Tier-1 Postgres/Redis, explicitly out of this story's scope. Live red/green (9.6): temp `runAsUser: 1001` in the web Deployment template -> `test_platform_image_pod_specs_satisfy_restricted_v2` FAILED `AssertionError: web: runAsUser fixed inside a restricted-v2 pod spec at ['securityContext.runAsUser']` -> reverted -> 1 passed; temp Route template planted in the core chart -> `test_core_chart_default_render_is_vanilla_kubernetes_only` FAILED `AssertionError: non-vanilla documents in the core render (kind, apiVersion): [('Route', 'route.openshift.io/v1')]` -> removed -> full module 10 passed. Gates: `ruff check` clean + `ruff format --check` clean (one initial reformat applied); `mypy platformapp config tests` INTERNAL-ERRORed in the conda env exactly as 11.4 documented (mypy 1.17.0 following imports into the env's langchain), so the 11.4 fallback was replicated -- mypy from a scratch pip venv built from `requirements/local.txt` (the CI-faithful surface): **"Success: no issues found in 51 source files"** (50 + this module). Ephemeral deps (`pip install --no-deps`, pinned, into the worktree's platform-dev env; NOTHING committed -- no pixi.toml/pixi.lock/environment.yaml/requirements change, zero conda-package displacements observed): pytest 8.4.1, pluggy 1.6.0, iniconfig 2.1.0, pytest-django 4.11.1, django-environ 0.12.0, factory-boy 3.3.2, faker 37.5.3, django-crispy-forms 2.4, crispy-bootstrap5 2025.6, django-allauth 65.10.0, fido2 2.2.1, qrcode 8.2, django-compressor 4.5.1, rjsmin 1.2.2, django-appconf 1.2.0, rcssmin 1.1.2, django-redis 6.0.0, django-model-utils 5.0.0, django-celery-beat 2.8.1, django-timezone-field 7.2.2, python-crontab 3.3.0, cron-descriptor 2.1.0, whitenoise 6.9.0, python-slugify 8.0.4, text-unidecode 1.3, hiredis 3.2.1, ruff 0.12.5, mypy 1.17.0, mypy-extensions 1.1.0, django-stubs 5.2.2, django-stubs-ext 5.2.2, types-PyYAML 6.0.12.20250516, pathspec 0.12.1 (+ the scratchpad mypy venv from local.txt). Honest gaps: NO live-cluster verification of any kind (AD-16 Tier 3 is attended-only -- Route admission, SCC enforcement, PVC binding, and the official postgres/redis images' behavior under an SCC-assigned arbitrary UID are all UNVERIFIED here; the deploy README documents the possible need for UID-agnostic data-service image overrides on hardened OCP); the full live pytest run over all of src/platform was not executed (collection-only proof, see above); `helm lint`/`helm template` validate template mechanics, not cluster admission.

## Verification

**Commands:**
- `pixi run -e platform-dev helm lint src/platform/deploy/charts/platform src/platform/deploy/overlays/ocp/chart` -- expected: 0 chart(s) failed
- `pixi run -e platform-dev helm template test-release src/platform/deploy/charts/platform` -- expected: renders; no `route.openshift.io` anywhere in output
- `pixi run -e platform-dev helm template test-release src/platform/deploy/charts/platform -f src/platform/deploy/overlays/ocp/core-overrides.yaml` -- expected: renders; no Ingress; no runAsUser on data services
- `pixi run -e platform-dev helm template test-route src/platform/deploy/overlays/ocp/chart` -- expected: exactly Route resource(s)
- `cd src/platform && pytest -v tests/test_chart_invariants.py` (with helm on PATH via the platform-dev env) -- expected: all pass; without helm: helm-gated tests skip naming the capability, companions pass
- `cd src/platform && ruff check tests/test_chart_invariants.py && ruff format --check tests/test_chart_invariants.py && mypy platformapp config tests` -- expected: clean

**Manual checks (if no CLI):**
- A real cluster deploy (OCP Route admission, SCC enforcement) is AD-16 Tier 3 — attended-only and OUT OF REACH here; this story verifies by lint + render + parsed-manifest invariants and says so honestly. Live red/green: temporarily violate an invariant in a scratch render (e.g. add `runAsUser` to the web pod) and watch the real test go RED, then restore GREEN; evidence in Dev Notes.
