---
title: "Broker TLS is verified"
type: "fix"
created: "2026-09-02"
status: "in-review"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "7841e5c84e9b348737f2de84cc0f66fcb2a442f2"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/config/settings/base.py"
  - "src/platform/config/startup/stage_one.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}` whenever the broker URL
is `rediss://`. Under an enterprise TLS mandate this looks encrypted and is
MITM-able. Red-team **X-2**, directive **R-14**.

**Approach:** `ssl_cert_reqs = CERT_REQUIRED` with `ssl_ca_certs` from the corporate bundle
(`truststore` / `SSL_CERT_FILE`) for both the Celery broker and the result
backend; `CERT_NONE` is permitted only under `COMPONENT_RUNTIME=local` and the
production settings check refuses it.

## Acceptance Criteria

- Given production settings and a `rediss://` broker, when loaded, then `ssl_cert_reqs` is `CERT_REQUIRED` and `ssl_ca_certs` points at the configured bundle.
- Given `COMPONENT_RUNTIME` unset (deployed) and `CERT_NONE` requested via env, when `manage.py check` runs, then stage-1 refuses.
- Given the laptop profile, when loaded, then `CERT_NONE` still works for a self-signed local Redis.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `41-4-broker-tls-is-verified`. Host never imports `pyforge.*`. Truststore first; explicit bundle path second; never `verify=False` semantics in a deployed profile.

**Block If:** Implementation would add a flag that re-enables `CERT_NONE` in production.

**Never:** `CERT_NONE` outside `COMPONENT_RUNTIME=local`.

</intent-contract>

## Tasks

- [x] Settings change + stage-1 check
- [x] Tests: production/local matrix
- [x] Ledger `41-4-broker-tls-is-verified` → `review`; **`done` is the landing step's** (the Tier-3 feed `sprint-ledger-sync` promotes from does not exist in a dispatch worktree, so the tracked twin carries the row directly).

## Verification

`src/platform/tests/test_broker_tls_verified.py` (new) +
`src/platform/tests/test_startup_required_settings.py`, from `src/platform`:

```
pixi run --frozen -e platform-ci-test python -m pytest tests/test_startup_required_settings.py tests/test_broker_tls_verified.py -q
```

The env is `platform-ci-test`, not `python-agent-platform`: `pixi.toml` declares
it the sole authority for Platform CI's `test` job, and it is the only env
carrying `pytest-django` — `python-agent-platform` cannot collect this suite at
all (`unrecognized arguments: --ds=config.settings.test`).

## Dev Notes

**2026-09-02 — implemented.** The TLS posture moved out of a settings one-liner
into `config/broker_tls.py`, the single declaration site for both
`CELERY_BROKER_USE_SSL` and `CELERY_REDIS_BACKEND_USE_SSL` (base settings
already aliases the second to the first, so the result backend is covered by
construction). `COMPONENT_BROKER_SSL_CERT_REQS` is the whole policy surface and
recognises exactly two values, `required` (default) and `none`; there is no
third, weaker rung, and `optional` is refused by name rather than silently
accepted as "nearly required".

**Composition fails closed, the refusal is the operator-facing half.**
`resolve_cert_reqs()` emits `CERT_NONE` only for a process that is explicitly
`COMPONENT_RUNTIME=local` *and* asked for it; a deployed component that asks
still composes `CERT_REQUIRED`. So the stage-1 refusal
(`refuse_unverified_broker_tls`) is not the only thing standing between
production and an unverified broker — it is what makes the misconfiguration
loud instead of silently corrected. That ordering also matters for the Block-If:
there is no flag that re-enables `CERT_NONE` in production, because the flag
that exists is ignored there.

**Trust resolution is truststore-first by path, and both halves count.**
redis-py wants paths, not a Python trust object, so the `truststore` library
cannot stand in (it is also absent from the `python-agent-platform` env).
`ssl.get_default_verify_paths()` is exactly the OS tier the enterprise-CA
convention targets — `SSL_CERT_FILE` / `SSL_CERT_DIR` when set to real paths,
otherwise OpenSSL's compiled-in defaults — and `COMPONENT_BROKER_CA_BUNDLE` is
the explicit second tier. `capath` is not optional: an
`update-ca-certificates`-style install populates a hashed directory and many
hosts ship no concatenated `cert.pem`, so a cafile-only resolver would refuse a
component whose operator installed the corporate CA correctly. A configured
path that is missing *or unreadable* is skipped rather than trusted, so a typo
or a permission mistake degrades to "no trust source", which is itself a
deployed refusal rather than a first-connect failure. Nothing resolves over the
network (pap:CAP-6).

**AC2 could not be met without fixing a pre-existing swallow.** `manage.py
check` answered `System check identified no issues` and exited **0** for a
deployed component with no `DJANGO_SECRET_KEY` — the shipped CAP-3 refusal that
has been in the tree since steward 16.2. Root cause is not Django's
`ManagementUtility`: it is `DjangoInstrumentor().instrument()`, which reads
`settings.MIDDLEWARE` inside `try/except ImproperlyConfigured` and answers a
failure by calling `settings.configure()`, pinning Django's empty defaults for
the rest of the process. Every entrypoint (`manage.py`, `wsgi`, `asgi`, the
Celery app) calls `configure_observability()` before touching settings, so
every one of them demoted stage 1 to a debug log and booted with zero apps and
zero middleware. Fixed at the one shared function —
`configure_observability()` now calls `load_django_settings()` between
`read_dot_env()` and `configure_telemetry()`. In a healthy process this is a
no-op (the instrumentor would have imported the same module microseconds
later); in a refusing one it restores fail-fast at all four entrypoints.
`test_required_settings_refusal_also_reaches_the_exit_code` guards the
`DJANGO_SECRET_KEY` family too, since the fix is shared.

**2026-09-02 — review pass, 11 findings applied.** All eleven were accepted; none
were rejected. The four that changed behaviour rather than wording:

- **`capath` joined the OS tier** (`resolve_ca_trust()` returns a `CaTrust`
  carrying `cafile` and/or `capath`, rendered as `ssl_ca_certs` /
  `ssl_ca_path`). Verified against the installed stack before writing it:
  redis-py 8.1.0 declares `ssl_ca_path` and feeds it to
  `SSLContext.load_verify_locations(capath=…)` (`redis/connection.py:2082`,
  `:2195`); kombu 5.6.2 merges the whole `broker_use_ssl` mapping verbatim
  (`connparams.update(conninfo.ssl)`, `kombu/transport/redis.py:1209`); celery
  5.6.3's Redis result backend does the same for `redis_backend_use_ssl`
  (`celery/backends/redis.py:275`) and never strips unknown keys — its
  `ssl_param_keys` list only governs URL-query decoding. So the kwarg is emitted,
  not merely tolerated, and `test_redis_py_accepts_the_kwargs_we_compose`
  constructs a real `SSLConnection` from the composed mapping to keep it true.
- **Stage 1 reads the composed `CELERY_BROKER_URL`** off the settings module it
  is handed, falling back to the environment only when absent. Confirmed the
  attribute is present at the call site (production.py's `from .base import *`
  re-exports it; printed live from `sys.modules['config.settings.production']`).
  `run_stage_one` no longer discards its argument — the `_STAGE_ONE` tuple went
  with it, since two explicit calls read better than a registry.
- **The `rediss://` scheme match is case-insensitive.** `REDISS://` is legal URL
  syntax and urlparse, kombu and celery all normalise it to the `rediss`
  transport — verified live, and with the old comparison kombu itself logged
  *"Secure redis scheme specified (rediss) with no ssl options, defaulting to
  insecure SSL behaviour"*. That was the story's own hole, reachable by
  capitalisation.
- **Composition maps through `CERT_REQS_BY_NAME`'s values** instead of
  hardcoding both outcomes, and stage 1's deployed refusal branches on the
  verify *mode* rather than the policy name — so a weaker rung added to the
  table later cannot become deployable by omission
  (`test_stage_one_refuses_any_policy_weaker_than_required` pins it).

Also: an unrecognised policy is now named on a laptop too (there is no stage 1
there, so `…=nonee` used to upgrade silently and break the self-signed-Redis
workflow). It raises from `resolve_cert_reqs()` **only when local**, which
keeps stage 1's own "unrecognised policy" refusal reachable rather than
pre-empted at settings import —
`test_deployed_unrecognised_policy_still_reaches_stage_one` guards exactly that.
The local naming is scoped to TLS brokers, deliberately asymmetric with stage 1:
a `redis://localhost` laptop must not be blocked from booting over a value that
has no effect there.

The source-substring entrypoint test is gone, replaced by parametrised real
child processes for `manage.py`, `wsgi` and `celery_app` — refusal *and*
boots-fine control for each. That is the assertion that actually fails if an
entrypoint drops its `configure_observability()` call. `config.asgi` is excluded
because it imports `langflow_integration`, which needs the
`python-agent-platform` env. The base-settings source test went too: three
child-process probes already assert the composed values in all three profiles.
Child envs now also neutralise `DJANGO_READ_DOT_ENV_FILE`, `SSL_CERT_DIR` and
`COMPONENT_PROCESS`, so a developer `.env` cannot re-supply a broker URL or
`COMPONENT_RUNTIME` and make a control pass for the wrong reason.

**Live verification** (`platform-ci-test` env, from this worktree):

- The spec's own verify command, run verbatim:
  `pixi run --frozen -e platform-ci-test python -m pytest
  tests/test_startup_required_settings.py tests/test_broker_tls_verified.py -q`
  → **67 passed**.
- `tests/test_broker_tls_verified.py` — 44 tests. Real child processes cover:
  production + `rediss://` reporting `ssl_cert_reqs=2 (CERT_REQUIRED)` with
  `ssl_ca_certs` at the bundle and `CELERY_REDIS_BACKEND_USE_SSL ==
  CELERY_BROKER_USE_SSL` (AC1); the same for the `REDIS_URL`-only shape
  `compose.yml` actually uses; all three entrypoints refusing and all three
  booting (AC2); and `config.settings.local` composing `ssl_cert_reqs=0
  (CERT_NONE)` with no trust source (AC3).
- Whole platform suite: **420 passed**, 40 skipped, 6 failed, 120 errors —
  failure/error set byte-identical to the pre-change baseline measured by
  stashing the diff (376 passed there; the delta is exactly these 44 tests).
  The 120 errors are "no PostgreSQL on `/tmp/.s.PGSQL.5432`"; the 6 failures
  are the pre-existing openfeature/dbgpt/cloudevents/restarts/supervisor set.
- `ruff check` on every touched file: clean (repo-wide `ruff check .` is
  pre-existing red at exactly 116 before and after, none in these files).
- `tests/meta/test_no_pyforge_import.py` (real `lint-imports`): passed — the new
  `config.broker_tls` module keeps the host↔factory boundary.
- `mypy` could not run at all: `Error constructing plugin instance of
  NewSemanalDjangoPlugin` / `INTERNAL ERROR`, django-stubs vs mypy 2.3.1. It
  fails before analysing any file, on a clean tree too — recorded as deferred,
  not caused here.

**Not done, deliberately.** The Helm chart is untouched: it wires `redis://`,
and the OS trust-store tier needs no chart key. Wiring
`COMPONENT_BROKER_CA_BUNDLE` / a `rediss://` broker into `values.yaml` belongs
with whichever story turns broker TLS on in-cluster. The reachability
consequence of the contractual "truststore first, explicit bundle second"
ordering — an explicit `COMPONENT_BROKER_CA_BUNDLE` cannot override a resolving
OS trust store — is deferred separately, not patched here.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
