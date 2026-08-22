# OCP overlay (Story 12.1)

The thin OpenShift face of the platform core chart (AD-11), in two halves:

- **`core-overrides.yaml`** — value deltas for the **core** chart on OCP:
  `ingress.enabled: false` (the edge is a Route, not an Ingress) and the
  data services' `runAsUser`/`fsGroup` nulled so the `restricted-v2` SCC
  assigns arbitrary UIDs instead of the vanilla-K8s numeric pins.
- **`chart/`** — the `platform-ocp` chart, whose only template is a
  `route.openshift.io/v1` Route pointing at the core release's web
  Service. Installed **beside** the core release as its own release.

```sh
# 1. Core chart with the OCP overrides (release name "platform" so the
#    web Service renders as "platform" -- the overlay's default target):
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    -f src/platform/deploy/overlays/ocp/core-overrides.yaml

# 2. The Route overlay beside it:
pixi run -e platform-dev helm install platform-ocp src/platform/deploy/overlays/ocp/chart
```

`route.service.name` **must match the core release's rendered web Service
name** (the core chart's fullname: the release name itself when it
contains "platform", else `<release>-platform`). Set it explicitly for any
other release name:
`--set route.service.name=<rendered-service-name>`.

TLS defaults to edge termination with an HTTP→HTTPS redirect; the app
still enforces https itself via `SECURE_PROXY_SSL_HEADER` trusting the
router's `X-Forwarded-Proto`.

See `../README.md` for the Secret contract, prerequisites, and honest
limitations (no live-cluster verification in this repo).
