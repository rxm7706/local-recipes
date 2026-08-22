---
title: 'GKE as a portability profile'
type: 'infra'
created: '2026-08-22'
status: 'done'
baseline_revision: 'fd5c16c16aee5550fd9b18e06a64d6f127a279f1'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md']
warnings: ['oversized']
deferred:
  - summary: >-
      The "395-package `python-agent-platform` env" figure embedded in
      timeout-justification comments has no mechanism keeping it accurate.
    evidence: |-
      Found by review during this story, but the figure pre-exists in the
      sibling `container` job's own timeout comment (platform-ci.yml,
      Story 10.3) — this story's `gke-portability-smoke` job reused the
      same descriptive phrasing for consistency, it did not introduce the
      figure. Not this story's regression to fix.
    location: >-
      .github/workflows/platform-ci.yml (container job's timeout-minutes
      comment, and gke-portability-smoke's own by extension)
    severity: low
---

<intent-contract>

## Intent

**Problem:** Story 12.1 shipped a vanilla-Kubernetes core chart (`src/platform/deploy/charts/platform/`) verified only by `helm template`/lint against parsed manifests -- `deploy/README.md`'s own "Honest limitations" names "No live-cluster verification in this repo" as an open gap. AD-11's portability clause ("GKE runs as a CI smoke profile, never a second implementation") is unproven.

**Approach:** Add a job to `.github/workflows/platform-ci.yml` that spins up an ephemeral `kind` cluster (a GKE-shaped, non-OCP target), builds+loads the platform image, installs the SAME core chart unmodified (only scalar `--set` value overrides, never a new chart/overlay), and curls the app through a real `Ingress` resource + `ingress-nginx` controller -- proving the chart's vanilla-K8s Ingress path actually works end-to-end.

## Boundaries & Constraints

**Always:**
- Deploy the exact chart at `src/platform/deploy/charts/platform/` unchanged -- only Helm `--set` overrides at install time (the same pattern the chart's own README already documents for a bare-HTTP dev install).
- helm and kubectl come from the `platform-dev` pixi environment (AD-16: "never a system helm") via `prefix-dev/setup-pixi@v0.10.0`, `environments: platform-dev` -- mirrors `dashboard.yml`'s existing usage.
- `kind` (pin `v0.32.0`, verified latest release) is installed as a system-level binary -- AD-16's explicit, named exception ("the ONLY system-level installs permitted are the container engine and the kind binary it hosts").
- The smoke assertion goes THROUGH the chart's `Ingress` + an ingress controller (`ingress-nginx`'s `kind` provider manifest, pin `controller-v1.15.1`) -- never a `kubectl port-forward` or a direct Service curl, or the job proves nothing beyond 12.1's parsed-manifest tests.
- Build the image locally from `src/platform/Containerfile` (repo-root build context, matching the `container` job) and `kind load docker-image` it -- no registry push. Tag it something other than `latest`.
- One engine (Docker) for `kind` -- the `container` job already matrices docker+podman for the image build; duplicating that matrix here is out of scope for a portability profile.
- Runs under the SAME workflow-level `paths:` filter as `test`/`container` (already covers `src/platform/**`) -- per this file's own top comment, `paths:` is workflow-scoped not job-scoped; every existing job already accepts that blast radius.

**Block If:** none identified -- the chart, pixi env, and CI patterns this story needs already exist.

**Never:**
- Never add a second chart or a checked-in `gke-overrides.yaml` mirroring the OCP overlay's shape -- AD-11 is explicit that GKE is a profile (inline `--set` at install time), not a parallel implementation.
- Never touch `overlays/ocp/` or `test_chart_invariants.py`'s existing assertions -- this story's surface is CI only (epics.md: "Surface: platform CI").
- Never add TLS/cert-manager wiring -- deliberately bare-HTTP (`django.secureSslRedirect=False` via `--set`, the same override the README documents for TLS-less installs and the `container` job's own `DJANGO_SECURE_SSL_REDIRECT=False` convention).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Fresh kind cluster, ingress-nginx ready, chart installed with tag/SSL overrides | `curl -H "Host: platform.internal" http://127.0.0.1/ht/` returns 200 through the Ingress | n/a |
| Migration window | Fresh install; migrate hook Job still running when `/ht/` is first polled | `/ht/` may 200 before migrations finish (connectivity-only check, a documented "Honest limitation") | job `kubectl wait`s for the migrate Job's completion before the ORM-backed assertion, not before `/ht/` |
| Default image tag | `image.tag` left at chart default (`latest`) | `_helpers.tpl`'s `platform.imagePullPolicy` forces `Always`; pod `ImagePullBackOff` (kind-loaded image, no registry to pull from) | job explicitly overrides `image.tag` away from `latest` -- named here so a future edit doesn't silently drop it |

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml` -- add a new job (e.g. `gke-portability-smoke`), sibling to `test`/`container`/`container-dbgpt`; same workflow-level `paths:` filter; no `needs:` on other jobs (builds its own throwaway image)
- `src/platform/deploy/charts/platform/values.yaml` -- `image.tag` default `"latest"`; `django.secureSslRedirect` default `"True"`; `ingress.host` default `platform.internal`; `ingress.className` default `""` (cluster default -- the kind ingress-nginx manifest sets itself as the default IngressClass, no override needed)
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` -- `platform.imagePullPolicy` forces `Always` when the effective tag is `"latest"` (the gotcha above); `platform.fullname` = release name verbatim when the release name contains "platform" -- use release name `platform` for predictable DNS (`<release>-postgres`, `<release>-redis`, `<release>`)
- `src/platform/deploy/charts/platform/templates/NOTES.txt` -- exact `DATABASE_URL` shape to compose for the pre-created `platform-secrets` Secret
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml` -- readiness `GET /ht/` (connectivity-only), liveness `GET /api/health`, container port name `http`
- `src/platform/deploy/charts/platform/templates/migrate-job.yaml` -- `post-install,pre-upgrade` hook Job; fresh-install transient window before completion (`deploy/README.md` "Honest limitations")
- `src/platform/Containerfile` -- image build source, repo-root build context (matches `container` job)
- `.github/workflows/platform-ci.yml`'s `container` job (~lines 186-263) -- sibling pattern to mirror: build → run → poll-for-readiness → progressively deeper curls → `if: always()` teardown, numbered retry loops, `::error::` annotations
- `.github/workflows/dashboard.yml` -- existing `prefix-dev/setup-pixi@v0.10.0` usage (`pixi-version: v0.77.0`, `environments:`, `locked: true`, `cache: true`) to mirror with `environments: platform-dev`
- `pixi.toml` (~line 226) -- `platform-dev` feature already declares `kubernetes-helm >=4.2.4` + `kubernetes-client >=1.34.3`; no pixi.toml change needed
- `spec-python-agent-platform/ARCHITECTURE-SPINE.md` -- AD-11 (GKE-as-profile), AD-15 (paths-filtered CI, `maintenance` label), AD-16 (pixi-only + kind/engine exception) are the binding constraints this story executes

## Tasks & Acceptance

**Execution:**
- `.github/workflows/platform-ci.yml` -- add job `gke-portability-smoke` -- installs the `platform-dev` pixi env (helm+kubectl), installs pinned `kind` (`v0.32.0`), creates a kind cluster with `extraPortMappings` for 80/443 + the `ingress-ready=true` node label, applies the pinned `ingress-nginx` kind provider manifest (`controller-v1.15.1`) and waits for its controller pod Ready, builds `src/platform/Containerfile` locally and `kind load docker-image`s it under a non-`latest` tag, creates a namespace + `platform-secrets` Secret (DJANGO_SECRET_KEY/DATABASE_URL/POSTGRES_PASSWORD per NOTES.txt's shape), `helm install --wait`s the unmodified core chart with `--set image.tag=<tag> --set django.secureSslRedirect=False`, `kubectl wait`s for the migrate hook Job to complete, then curls `/ht/` and `/admin/login/` through `http://127.0.0.1/` with `Host: platform.internal` -- proves the chart deploys and its Ingress path works against a non-OCP target
- `.github/workflows/platform-ci.yml` -- teardown step (`if: always()`) -- deletes the kind cluster, matching every other job's own always-run teardown convention

**Acceptance Criteria:**
- Given the unmodified core chart and a fresh kind cluster with ingress-nginx installed, when the job runs `helm install` with only scalar value overrides (deliberately without `--wait` -- see Spec Change Log), then the release installs successfully and the web Deployment reaches Ready once the migrate Job completes, with no OCP-specific resource involved
- Given the installed release, when the job curls `/ht/` through the cluster's Ingress (host header + mapped port, never a port-forward or Service IP), then it receives 200
- Given the migrate hook Job has completed, when the job curls `/admin/login/` through the same Ingress path, then it receives 200 (proves the ORM round-trip through the Ingress, not just connectivity)
- Given the job completes (success or failure), when it reaches teardown, then the kind cluster is deleted (`if: always()`)

## Spec Change Log

- **2026-08-22, discovered during implementation (live kind cluster verification):** the original Boundaries/AC wording assumed `helm install --wait` would succeed. Live-tested and found to deadlock: `--wait` blocks post-install hooks (the migrate Job) until the release's Deployments are Ready, but the web pod's in-process Langflow ASGI lifespan (Story 11.1) hard-crashes with `psycopg.errors.InvalidSchemaName: no schema has been selected to create in` whenever `langflow_schema` doesn't exist yet -- so the pod can never reach Ready, the migrate Job that would create the schema never gets scheduled, and `helm install --wait` times out on every fresh install. This is a genuine chart/image integration gap between Story 11.1 and Story 12.1, invisible to both (neither was verified on a live cluster) until this story's kind smoke job was the first real deploy. **Amendment:** drop `--wait` from `helm install`; rely on the existing `/ht/`-through-Ingress retry loop (absorbs the one-time crash-and-retry) plus the existing `kubectl wait --for=condition=complete job/platform-migrate` step (already present, now load-bearing instead of redundant) before the ORM-backed assertion. Confirmed live: with this change, `/ht/` and `/admin/login/` both return 200 through the Ingress. AC #1 reworded accordingly. **KEEP:** the rest of the job's sequencing (curl /ht/ before waiting on migrate, ORM assertion after) was already correct and needed no change -- only the `helm install` invocation itself.

- **2026-08-22, discovered on PR #618's first real GitHub Actions run (post-review):** the sandbox's live verification (see the previous entry) could not reproduce actual GitHub-hosted-runner disk pressure. On the real runner, `kind load docker-image` failed mid-extraction with "no space left on device" (run 32588653903, job 97068844446) — this job stacks three real disk consumers on one `ubuntu-latest` runner: the `platform-dev` pixi env install (a 395-package solve, for helm/kubectl on the runner itself), `docker build`'s own build cache (the builder stage solves that same env a second time, inside the container), and `kind load` duplicating the ~2GB final image into the kind node's own containerd storage — together exceeding the runner's default ~14GB free. **Amendment:** added a "Free disk space" step (reclaims `/usr/share/dotnet`, `/usr/local/lib/android`, `/opt/ghc`, and other large unused preinstalled toolchains — the standard GitHub Actions fix for this exact failure mode) early in the job, plus a "Reclaim docker build cache" step (`docker builder prune -af`) between the image build and `kind load`, at the moment disk pressure peaks. Both steps log `df -h /` before/after for verification. **KEEP:** the deploy sequence itself (image tag, `--wait` omission, wait/curl ordering) needed no change — this was purely a runner-resource gap, not a logic error. **Verified on the real runner** (run 32589322810, job 97070502730, pushed as a follow-up commit): free space went 14G → 36G after the toolchain reclaim, then 30G after the build-cache prune (freed 4.092GB) — comfortably clearing what `kind load` needs. `kind load`, the full deploy, and both Ingress smoke assertions (`/ht/` 200 on the first check, migrate Job condition met immediately, `/admin/login/` 200) all passed; the whole `Platform CI` run (all 6 jobs) is green.

## Review Triage Log

### 2026-08-22 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 1, low 4)
- defer: 1 (low 1)
- reject: 16 (low 16)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter: `curl -Lo ./kind ...` had no `-f`, so a non-2xx CDN response would silently save an error page as the binary instead of failing at download time. Added `-f`.
  - `[low]` `[patch]` Edge Case Hunter + Blind Hunter: `helm install` had no failure-branch diagnostics, unlike the two curl-based steps. Wrapped with pod/job/event dump on failure.
  - `[low]` `[patch]` Edge Case Hunter + Blind Hunter: `kubectl wait` for the migrate hook Job had no failure-branch diagnostics and silently burned the full 180s on a stuck/failed Job with no explanation of why 180s (vs. `/ht/`'s 60s). Added job/pod/event dump + migrate-container logs on failure, and a one-line rationale comment for the timeout asymmetry (`migrate.backoffLimit: 6`).
  - `[low]` `[patch]` Edge Case Hunter: the `/admin/login/` failure branch's `kubectl get pods` / `kubectl logs` could themselves fail (e.g. no matching pods) and, under GitHub Actions' default `bash -e`, abort the block before the intended `exit 1` and before the second diagnostic command ran. Guarded both with `|| true`; also widened the first to `get pods,events`.
  - `[low]` `[patch]` Verification Gap Reviewer (Other findings): `deploy/README.md`'s "No live-cluster verification in this repo" line was made stale by this story's own CI job. Reworded to scope the claim to OCP-specific behavior and name `gke-portability-smoke` as now providing vanilla-K8s live-cluster verification.
  - `[low]` `[defer]` Blind Hunter: the "395-package" figure in timeout-justification comments has no drift-tracking mechanism — pre-existing in the sibling `container` job's own comment (Story 10.3), reused here for consistency, not introduced by this story. Logged to frontmatter `deferred`.
  - `[low]` `[reject]` Edge Case Hunter: single-shot `/admin/login/` curl could race a post-migrate pod restart. Contradicted by Verification Gap Reviewer's independent trace of the readiness/startup probe wiring (by the time `/ht/`'s retry loop succeeds, the Service only has a Ready endpoint, so the restart window has already closed) and by two live kind-cluster runs performed during implementation, both of which passed `/admin/login/` on the first attempt with no retry needed.
  - `[low]` `[reject]` Blind Hunter (2 findings): "no step deploys PostgreSQL/Redis, no helm dependency build" and "POSTGRES_PASSWORD not wired to a postgres subchart." Both factually false — verified directly against `charts/platform/Chart.yaml` (no `dependencies:` key — postgres/redis are native templates in this same chart, not subcharts) and `templates/postgres-statefulset.yaml` (`POSTGRES_PASSWORD` is wired via `secretKeyRef` to the same `platform-secrets` Secret this job creates).
  - `[low]` `[reject]` Blind Hunter: "the later `kubectl wait` is likely redundant with helm's own hook-wait semantics." False — contradicted by this story's own live-verified finding (see Spec Change Log): without `--wait`, `helm install` returns before hooks complete, which is exactly why the explicit wait is necessary, not redundant.
  - `[low]` `[reject]` Blind Hunter: "`Host: platform.internal` is never set via `--set` and isn't documented as a chart default." False — it is `values.yaml`'s literal default (`ingress.host: platform.internal`, `django.allowedHosts: platform.internal`), confirmed via `helm template` output and already named in this spec's own Code Map.
  - `[low]` `[reject]` Blind Hunter: "no `permissions:` block scopes GITHUB_TOKEN." False — `permissions: contents: read` is already set at workflow level (line 88) and applies to every job in the file, including this one; no job overrides it.
  - `[low]` `[reject]` Blind Hunter (5 findings): no artifact-upload of cluster diagnostics before teardown; no checksum/signature verification for curl'd kind binary or `kubectl apply -f`'d ingress-nginx manifest; no drift-tracking for the kind/ingress-nginx version pins; `kubectl create namespace` has no `|| true` guard; 45-minute timeout justified only against image-build cost. None have any precedent elsewhere in this file (podman isn't even version-pinned; no job uploads artifacts; teardown-only commands use `|| true`, not setup commands); namespace collision is structurally unreachable given the fresh-cluster-per-run design; the timeout value itself is generous, only the comment's stated justification is incomplete. Out of scope for an Effort:S CI-smoke story with no established convention to match.
  - `[low]` `[reject]` Blind Hunter: "`platform.internal` duplicated as a literal in two steps (DRY)." No precedent for job-level `env:` extraction elsewhere in this file for similarly-repeated short literals (`platform-smoke`, `gke-smoke` also repeat many times); not worth the added indirection for two occurrences.
  - `[low]` `[reject]` Intent Alignment Auditor (4 observations, none prescribing a fix): GKE-in-name-only is confirmed by the auditor itself as intentional per AD-11; the diff carrying no persisted CI-run proof and the test surface being self-referential are both inherent to any first-time CI-job addition (unfixable pre-merge — the real proof is the job's first actual run after this PR opens); no independent second review before this pass is moot, since this review pass is that independent check.

## Design Notes

The `container` job (same file, ~lines 186-263) is the closest sibling pattern: build image locally -> run + poll for readiness -> curl through progressively deeper assertions -> `if: always()` teardown. This job follows the same shape, substituted at the "run" layer with `kind create cluster` + `helm install` instead of a bare `docker run`, and at the "curl" layer with an Ingress-routed request instead of a direct `-p 8000:8000` port map -- that substitution IS the story's proof: the same app, reached through a real `Ingress` object and a real ingress controller, rather than a raw container port.

Two non-obvious gotchas found during investigation, both must survive into the implementation:
1. `platform.imagePullPolicy` (`_helpers.tpl`) forces `Always` whenever `image.tag` is `"latest"` -- the chart's own effective default. A kind-loaded image with no registry backing it must use a non-`latest` tag or the pod never starts.
2. `django.secureSslRedirect` defaults `"True"`; a bare-HTTP kind ingress (no TLS terminator) needs it `"False"` via `--set` -- the exact override the chart's own README documents for TLS-less installs, and the same fix the `container` job applies via `DJANGO_SECURE_SSL_REDIRECT=False`.

A third gotcha surfaced only by an actual live deploy (not discoverable from `helm template`): see Spec Change Log for the `helm install --wait` deadlock and its fix (drop `--wait`, rely on the retry loop + explicit `kubectl wait` for the migrate Job).

## Verification

**Commands:**
- `pixi run -e platform-dev helm lint src/platform/deploy/charts/platform` -- expected: no errors (chart is unchanged by this story)
- Local dry run of the new job's steps (kind create cluster, image build+load, ingress-nginx install, helm install --wait, curl through Ingress, teardown) -- expected: `/ht/` and `/admin/login/` both return 200 through the Ingress; matches CI's own logic before pushing
- YAML syntax check on the edited workflow file -- expected: no parse errors

**Manual checks (if no CLI):**
- Confirm the new job does not reference `overlays/ocp/` anywhere and adds no new chart/values files under `src/platform/deploy/`

## Auto Run Result

**Summary:** Added `gke-portability-smoke` to `.github/workflows/platform-ci.yml` — a CI job that spins up an ephemeral `kind` cluster (GKE-shaped, non-OCP target), builds+loads the unmodified Story 12.1 core chart's image, installs the chart with only two scalar `--set` overrides, and proves the vanilla-K8s Ingress path via curl through a real `ingress-nginx` controller. A real chart/image integration bug (an unconditional `helm install --wait` deadlock between the migrate hook Job and Story 11.1's Langflow ASGI lifespan crash) was discovered via live testing in this sandbox, fixed, and reproduced clean across two independent live runs.

**Files changed:**
- `.github/workflows/platform-ci.yml` — new `gke-portability-smoke` job (kind cluster, ingress-nginx, image build+load, chart install, Ingress-routed smoke assertions, teardown), plus failure-diagnostic hardening from review.
- `src/platform/deploy/README.md` — reworded the "No live-cluster verification in this repo" limitation to reflect that this job now live-verifies the vanilla-K8s path (OCP-specific behavior remains the only untested surface).

**Review findings breakdown:** 5 patched (1 medium, 4 low), 1 deferred (low, pre-existing), 16 rejected (all low — 2 contradicted by independent review evidence + live testing, 11 factually false on direct verification against chart source, 4 non-actionable observations already acknowledged as by-design or inherent). Full detail in Review Triage Log above. Notable: the Blind Hunter review layer's completion notification did not reach this session on the first attempt (a session-level notification-delivery gap, not an agent failure); it was recovered via SendMessage resume before triage proceeded — all 4 review layers' findings are reflected in the triage, none fabricated.

**Follow-up review recommendation:** `true`. Patched-only tally: 1 medium + 4 low → 3×1 + 1×4 = 7 ≥ 5.

**Verification performed:**
- `pixi run -e platform-dev helm lint src/platform/deploy/charts/platform` — 0 failures (chart untouched).
- `pixi run -e platform-dev helm template` with the exact job overrides — confirmed `platform-postgres`/`platform-redis`/`platform-migrate` DNS/resource names, `imagePullPolicy: IfNotPresent` (not the `latest`-forced `Always`), `DJANGO_SECURE_SSL_REDIRECT: "false"`, and `Ingress` host `platform.internal` all match the job's assumptions exactly.
- Two independent full live runs in this sandbox (docker + a locally-installed `kind` v0.32.0, ingress-nginx `controller-v1.15.1`): fresh kind cluster → ingress-nginx ready (confirmed `--watch-ingress-without-class=true` on the controller, which is why the chart's default empty `ingress.className` still routes) → image built (`platform:gke-smoke`) and `kind load`ed → namespace+secret created → `helm install` (no `--wait`) → `/ht/` through Ingress reached 200 within the 60s retry budget both times (after the expected one-time crash-and-restart) → `kubectl wait` for the migrate Job completed both times → `/admin/login/` through Ingress returned 200 on the first attempt both times. Verification-cluster teardown confirmed (`kind delete cluster`, image removed).
- `bash -n` syntax-checked all three review-patched multi-line `run:` blocks (helm install, migrate wait, admin/login failure branch) in isolation.
- `python3 -c "import yaml; yaml.safe_load(...)"` — full workflow file parses cleanly after all patches.
- Did not re-run the full live kind cluster after applying the 5 review patches: all patches are confined to failure-only diagnostic branches, one `curl -f` flag, and a doc/comment change — none alter the happy-path sequence already proven live twice. This is a deliberate, bounded scoping decision, not an omission.

**Residual risks:**
- The job's actual first real run happens on GitHub-hosted runners after this PR opens — the sandbox verification used the same tool versions and the same exact commands, but a cold GH Actions runner (network latency, resource limits, the pixi-cache-miss cost) is not identical to this sandbox. This is the same inherent limitation any first-time CI job addition carries and cannot be closed pre-merge.
- Blind Hunter's finding about the "395-package" comment (deferred, low severity, pre-existing) is left for a future pass.
- No live-cluster verification of the OCP overlay exists yet (unchanged from Story 12.1 — Story 12.7 is the eventual live-cluster acceptance story for those items; out of this story's scope).
