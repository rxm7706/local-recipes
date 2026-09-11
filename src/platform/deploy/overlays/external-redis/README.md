# External Redis overlay (Story 51.2)

**Prerequisite:** an Enterprise Managed Redis (or equivalent) endpoint reachable
from the platform namespace, plus a pre-created `existingSecret` carrying
`REDIS_PASSWORD` (same contract as the self-hosted default — see
`../README.md`).

Additive values overlay for the **core** chart when Redis is consumed, not
self-hosted (AD-1 datastores exception, CAP-3). With `redis.external.enabled:
true`, the chart deploys zero in-cluster Redis workloads
(`redis-deployment.yaml`, `redis-service.yaml`, `redis-broker-pvc.yaml`) and
platform pods take `REDIS_BROKER_URL`, `REDIS_CACHE_URL`, and `REDIS_URL`
from the overlay's URL fields instead of in-cluster Service DNS.

```sh
# Core chart with external Redis (release name "platform" matches the
# documented vanilla-K8s install in ../README.md):
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    -f src/platform/deploy/overlays/external-redis/values.yaml
```

Edit `values.yaml` in this directory before install: replace the
`enterprise-redis-*.example.com` placeholders with the operator's broker and
cache endpoints. A single shared endpoint is valid — set both `brokerUrl` and
`cacheUrl` to the same URL.

With the overlay **not** applied, or with `redis.external.enabled: false`,
the self-hosted Redis default is unchanged (byte-identical `helm template`
output).

See `../README.md` for the Secret contract and `test_chart_invariants.py`
for automated proofs.
