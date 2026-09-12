---
title: 'CAP-3 attended CRC verification, 2026-09-12'
type: 'verification'
created: '2026-09-12'
updated: '2026-09-12'
status: 'complete'
cluster: 'CRC 2.63.0 / OpenShift 4.22.7 (apps-crc.testing)'
---

# CAP-3 — attended CRC verification, 2026-09-12

Host: same workstation as Story 12.7's own record. `crc config set memory 24576 cpus 8` (default 10.5GB/4
CPU was insufficient for the CURRENT chart's full pod count — beat, consume-events-doctor/mason,
worker-builds, mcp-host, keycloak all added since the original 17-day-old install) then
`crc stop && crc start -p ~/.config/openshift/pull-secret.json`. Reused the existing `platform`
namespace and release from Story 12.7's own bring-up rather than a fresh install.

Image path: `podman build -f src/platform/Containerfile` + `src/platform/compose/mcp-host/Containerfile`
→ push to the **CRC internal registry only** (`default-route-openshift-image-registry.apps-crc.testing/
platform/{platform,platform-mcp-host}:crc-202609120933`). No public registry push.

Helm: `helm upgrade platform src/platform/deploy/charts/platform -f overlays/ocp/core-overrides.yaml
--force-conflicts` (prior manual `oc set image`/`oc patch` history on this release required
`--force-conflicts` for server-side-apply field-manager conflicts). `networkPolicy.enabled: true`
(chart default) is live for the first time on this release — Story 12.7's own run never exercised it.

## Proofs (given `networkPolicy.enabled: true` live on a real OpenShift cluster)

| Item | Result | Evidence |
|------|--------|----------|
| **Egress default-deny is real** | **PASS** | `curl -m 5 https://pypi.org` from inside the `web` pod: `curl: (28) Operation timed out`, exit 28. |
| **Zero hostPath** | **PASS** | `oc get pods -n platform -o json` parsed for `spec.volumes[].hostPath` across every pod: 0 matches. |
| **`/runs/` renders from `RunState`** | **PASS** | `curl https://platform.apps-crc.testing/runs/` → 200, empty-state HTML (`<li class="empty">none</li>`), matching `test_front_door_queries_supervisor.py`'s own contract. |
| **Platform image boots** | **PASS (after fix)** | First boot crashed `ModuleNotFoundError: pyforge.herald` (Containerfile gap, landed PR #1278) — never caught because no prior exercise did a real container boot since Herald Epic 19.1. |
| **DNS reachable with policies active** | **PASS (after two fixes)** | The chart's DNS-egress rule had two independent bugs — a `podLabels` map that deep-merged with the vanilla default instead of replacing it, and the wrong port (53 instead of OpenShift's real 5353). Both fixed in PR #1279. Confirmed live: `kubernetes.default.svc.cluster.local` resolves from inside a pod after both fixes. |
| **Real Authorization Code + PKCE login against deployed Keycloak** | **PASS** | Full flow driven by hand (GET auth endpoint → parse real Keycloak login form → POST credentials for a real realm user `marshal-operator` in group `/pyforge:station:marshal` → capture `code` from the 302 redirect → exchange for a token at the real token endpoint). Resulting JWT: `aud: [platform-web, account]`, `groups: [pyforge:station:marshal]`, correctly signed RS256. |
| **`verify_idp_bearer()` accepts the real bearer** | **PASS (after fix)** | Bundled OIDC profile's JWKS URL used `http://` for its in-cluster Keycloak call; `django_pyforge`'s verifier rejected any non-`https`/`file` scheme, so the bundled profile had never been able to verify anything since its own introduction. Fixed narrowly (PR #1280): `http://` allowed only for a `.svc`/`.svc.cluster.local` host. Confirmed live: `verify_idp_bearer(<real bearer>)` called directly returns the correct `sub`/`roles`. |
| **Real assertion mint via HTTP (`/assertion/mint/`)** | **PASS (after fix)** | Root cause of the earlier "refused" mystery: `PYFORGE_ASSERTION_PRIVATE_KEY`/`PUBLIC_KEY` were never wired from `existingSecret` into any platform pod's env (documented as consumed, never templated) — `mint_assertion()` raised `AssertionRefusedError`, caught by the same except clause as a genuinely bad bearer, producing an identical `{"error": "refused"}` 401. Fixed: PR #1282. Confirmed live on the chart-native (Helm-tracked) redeploy: a fresh PKCE bearer mints a real signed assertion, HTTP 200. |
| **Live run appears on `/runs/`, timing survives teardown** | **PASS (after two more fixes)** | Fixed the mcp-host sidecar (never hosted any station's real MCP tools -- landed as `spec-mcp-host-real-station-tools` CAP-1, no longer draft) and a client/server wire-contract mismatch in the publish/heartbeat tools. `HostPublisher.publish()`/`.heartbeat()`/`.complete()` driven from a real workstation-side Python process against the live cluster: `publish_loop_run` returns a real handle, `heartbeat_loop_run` and `complete_loop_run` both succeed, the process exits, and a completely separate `curl` call to `/runs/` afterward shows `<li data-run-id="dbba4820-..." data-duration-ms="1057">marshal 1057ms</li>` under "Completed timing" -- the run's timing, queried from a client that has no relationship to the process that published it. |

## Findings (not silent notes)

1. **Platform image never actually booted since Herald Epic 19.1.** `config/station_api.py` imports `pyforge.herald.station_api` at ASGI load time; the image's own `python-agent-platform` pixi env never declared `pyforge-herald`, and the Containerfile's per-station raw-`COPY` list never gained a line for it. Fixed: PR #1278.
2. **OCP DNS-egress NetworkPolicy override was a silent no-op.** Story 33.13's own `networkPolicy.dns.podLabels` values override was a map; Helm deep-merges nested maps across `-f` files instead of replacing them, so the chart default's `k8s-app: kube-dns` key survived alongside the OCP override's key, producing an AND-matched `podSelector` neither system's real DNS pods satisfy. Fixed: PR #1279 (podLabels → scalar `podLabelKey`/`podLabelValue`).
3. **OCP DNS-egress NetworkPolicy also named the wrong port.** `openshift-dns`'s own built-in `dns-default` NetworkPolicy has no ingress allow for port 53 from other namespaces at all — only 5353 (the Service's port 53 DNATs to pod `targetPort` 5353). Predates Story 33.13. Fixed: PR #1279 (same PR as finding 2, one combined DNS fix).
4. **Bundled OIDC profile's JWKS URL scheme was categorically rejected.** `django_pyforge.assertion.identity`/`jwks` only allowed `https`/`file` JWKS URL schemes; the bundled profile's in-cluster Keycloak call is legitimately `http://` (same-namespace Service, no TLS configured). Fixed: PR #1280 (narrow allowance for `.svc`/`.svc.cluster.local` hosts only — never widens what a BYO/external issuer can get away with).
5. **Postgres image swap needed a collation refresh.** Switching `postgres:17` → `pgvector/pgvector:pg17` (needed for a pre-existing, unrelated `pyforge-scribe` Liquibase migration requiring the `vector` extension) triggered glibc collation-version warnings on `platform`, `postgres`, and `template1`. Resolved with `ALTER DATABASE ... REFRESH COLLATION VERSION` on each — not landed as a chart change; this is an operational step for anyone doing the same base-image swap, not a code defect.
6. **`KEYCLOAK_ADMIN_PASSWORD` was never in `platform-secrets`.** The bundled Keycloak Deployment requires it; the existing Secret (created before the bundled profile was ever exercised) didn't have the key. Added directly to this cluster's Secret (disposable local-cluster credential, not tracked anywhere).
7. **No Route exists for Keycloak.** Only the web service has a Route in `overlays/ocp/chart`. Created `platform-keycloak` (host `platform-keycloak-platform.apps-crc.testing`) and `platform-keycloak-authhost` (host `auth.platform.internal`, matching the chart's own hardcoded `KC_HOSTNAME`/issuer value) by hand for this exercise — not landed as a chart addition; a future story would need to decide whether Keycloak gets a permanent Route or a different exposure story.
8. **Chart's bundled realm has no CLI-loopback-capable client.** `platform-web` (the chart-templated realm's only client) only allows redirect URIs under `.Values.ingress.host` (`platform.internal`), not `http://127.0.0.1:*` — it's shaped for browser-based web login, not `pyforge login --pkce`'s loopback pattern. Created a `pyforge-cli` client by hand via `kcadm.sh` for this exercise (mirroring Story 33.14's own compose-realm client exactly) — not landed as a chart addition. A future story should decide whether this belongs in `keycloak-realm-configmap.yaml` permanently.
9. **CRC's default resource preset (10.5GB/4 CPU) is now too small for this chart.** The chart has grown substantially since Story 12.7's original install (beat, two consume-events workers, worker-builds, mcp-host, and now Keycloak). Bumped to 24GB/8 CPU for this exercise; not a code change, but worth recording as a fact for the next attempt.
10. **`PYFORGE_ASSERTION_PRIVATE_KEY`/`PUBLIC_KEY` were never wired into the chart's pod env at all.** `values.yaml` documented them as consumed `existingSecret` keys; no template referenced them. Fixed: PR #1282 (`optional: true` `secretKeyRef` entries in `platform.djangoEnv`, plus a render-through-Helm regression test).
11. **The mcp-host sidecar had never hosted any station's real MCP tools.** Tracing WHY a real, correctly-signed, correctly-minted assertion still could not publish a run: `POST /stations/marshal/mcp` `publish_loop_run` returned `Unknown tool: publish_loop_run` from the real `mcp` library's own tool manager. `platform.djangoEnv` unconditionally sets `MCP_HOST_SIDECAR_BASE_URL`, so `dispatch_station_mcp` proxies *every* station's MCP call to the sidecar; the sidecar (`mcp_host/app.py`) built each station's app with a generic one-tool identity stub (`station_face()`), never `django_marshal_portal.mcp_asgi`'s real held-loop tools. Confirmed the web pod's own interpreter still cannot import `mcp.server.mcpserver` (the sidecar is the only place a real per-station app could run) and that no existing spec covered wiring it up (`spec-mcp-era-isolation`'s own slice 2/3 sequence covers unrelated problems). Seeded as `docs/dreams/mcp-host-real-station-tools.md`, derived to `spec-mcp-host-real-station-tools`, then **implemented in this same pass** rather than left parked: a minimal Django settings module (`src/platform/mcp_host/settings.py` — `django_pyforge` + `django_marshal_portal` only, no Langflow, no Redis client) plus a new `pixi.toml` `[feature.mcp-host]` dependency set (django, psycopg, django-environ, pyjwt, cryptography); `mcp_host/app.py` now discovers real per-station apps through the SAME `django_pyforge.mcp_http.iter_station_mcp_apps()` seam the web pod uses in-process, falling back to the identity stub for every other station (CAP-2's compatibility guarantee, covered by a mocked-`django.setup()`-failure unit test); the Containerfile copies `django_marshal_portal` in; the chart gained `platform.mcpHostEnv` (`DJANGO_SECRET_KEY`/`DATABASE_URL` required, `PYFORGE_ASSERTION_PUBLIC_KEY` optional) and egress-to-postgres (mcp-host was DNS-only before) plus a postgres-ingress allow entry. Landed: PR #1285.
12. **`HostPublisher`'s wire shape didn't match the real tool's schema — a second bug the first one had always hidden.** Once finding 11 made `publish_loop_run`/`heartbeat_loop_run` reachable at all, both immediately failed schema validation: `Field required ... payload`. The MCP SDK turns a `**payload: Any` parameter into a REQUIRED, separately-named `payload` field on the generated tool schema, not "arbitrary extra keys allowed" — so the real tool contract is `{"assertion": ..., "payload": {...}}`, a nested object, while `HostPublisher.publish()`/`.heartbeat()` sent the record fields flattened at the top level. This bug could not have been caught before finding 11 shipped, because the tool was never reachable to validate against. Fixed both sides for clarity: the server tools (`django_marshal_portal/mcp_asgi.py`) now declare `payload: dict[str, Any] | None = None` explicitly instead of `**payload: Any`; the client (`publisher_host.py`) nests `_record_to_payload(record)`/`shape_heartbeat(handle)`'s extra content under an explicit `"payload"` key. `complete_loop_run` was already correct (its parameters are named explicitly, no `**kwargs`). Landed: PR #1285 (same PR as finding 11 — one coherent fix, discovered and closed in the same live-verification pass).

## Contingency ladder (postgres/redis)

**None used for redis.** For postgres, swapped the base image (finding 5) to get `pgvector` — not a
SCC/UID fallback, a genuinely different, unrelated pre-existing gap (the chart's default `postgres:17`
image has never had `pgvector` for `pyforge-scribe`'s own migration).

## What is claimed

- `networkPolicy.enabled: true` (default-deny + explicit per-component allows) live on a real OpenShift
  cluster for the first time, with a demonstrated, real egress failure (`curl` to `pypi.org` times out).
- Zero `hostPath` volumes across every running pod.
- `/runs/` renders correctly from `RunState` through the real Route.
- A complete, real Authorization Code + PKCE login against a deployed Keycloak, producing a
  correctly-signed, correct-claims bearer.
- `django_pyforge.assertion.identity.verify_idp_bearer()` — called directly with that real bearer —
  correctly verifies it and returns the right subject and `pyforge:station:marshal` role.
- Seven genuine, previously-undiscovered bugs found and fixed, each independently verified via
  `pixi run -e local-recipes platform-ci-local -- --test` (landed PRs #1278, #1279, #1280, #1282,
  #1285) plus the full `pyforge-marshal` unit suite (7,915 passed).
- A real host assertion minted via HTTP (`/assertion/mint/`) from a real IdP bearer, end to end,
  on the chart-native (Helm-tracked, no ad-hoc patches) redeployed pod.
- **A live run, published from a real workstation-side `HostPublisher` process against the deployed
  cluster, appearing on `/runs/`, with its timing queryable from a completely separate process after
  the publishing process has exited.** `publish_loop_run` → real handle; `heartbeat_loop_run` →
  success; `complete_loop_run` → success; the Python process exits; a fresh, unrelated `curl` call
  to `/runs/` shows the run under "Completed timing" with its real duration. This is CAP-3's own
  success criterion, met in full.
- `spec-mcp-host-real-station-tools` CAP-1 and CAP-2 both proven live: marshal's real tools are
  reachable through the sidecar, and every other station (verified: `atlas`) still gets the
  identity-stub fallback unchanged.

## What is not claimed

- Any chart changes for findings 6-8 (Keycloak Secret key, Keycloak Route, `pyforge-cli` realm
  client) — all three were done by hand on this disposable cluster for the exercise, not landed to
  the tracked chart. A future story should decide which (if any) become permanent chart features.
- Real DB-GPT sidecar health (unrelated CrashLoopBackOff observed throughout; not investigated,
  matches Story 12.7's own precedent of treating the sidecar as out of scope for this record).
- Enterprise Managed OCP namespace — not exercised, as CAP-17's own `verified:` wording already states.

## Commands used (no secrets)

```text
crc stop && crc config set memory 24576 && crc config set cpus 8 && crc start -p ~/.config/openshift/pull-secret.json
podman build -f src/platform/Containerfile -t platform:local .
podman build -f src/platform/compose/mcp-host/Containerfile -t platform-mcp-host:local .
podman push default-route-openshift-image-registry.apps-crc.testing/platform/platform:crc-202609120933 --tls-verify=false
podman push default-route-openshift-image-registry.apps-crc.testing/platform/platform-mcp-host:crc-202609120933 --tls-verify=false
helm upgrade platform src/platform/deploy/charts/platform -f overlays/ocp/core-overrides.yaml \
  --set postgres.image.repository=pgvector/pgvector --set postgres.image.tag=pg17 --force-conflicts --timeout 8m
oc exec platform-postgres-0 -- curl -m 5 -o /dev/null -w 'HTTP_CODE:%{http_code}' https://pypi.org
oc get pods -n platform -o json  # parsed for spec.volumes[].hostPath
curl -sk https://platform.apps-crc.testing/runs/
# real Authorization Code + PKCE flow: auth endpoint GET -> Keycloak login form POST -> code exchange -> POST /assertion/mint/
# real live run, driven from a workstation-side Python process against the deployed cluster:
#   HostPublisher(base_url="https://platform.apps-crc.testing", bearer_file=...).publish(record)
#   .heartbeat(handle); .complete(handle, status="succeeded", result={...})
# then, from a separate process, after the publishing process exited:
#   curl -sk https://platform.apps-crc.testing/runs/   # -> "Completed timing" lists the run
```

## Verification

**Commands:**
- `pixi run -e local-recipes platform-ci-local -- --test` — full PASS (915 passed), covers all
  landed fixes' own regression tests.
- `pixi run -e pyforge-marshal pyforge-marshal-test` — full PASS (7,915 passed, 1 skipped), covers
  the `HostPublisher` wire-shape fix (finding 12).
