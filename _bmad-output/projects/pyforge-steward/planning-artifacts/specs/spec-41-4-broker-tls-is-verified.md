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

`src/platform/tests/test_startup_required_settings.py` + a new settings test; `pixi run -e python-agent-platform`.

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

**Bundle resolution is truststore-first by path.** redis-py wants
`ssl_ca_certs` as a *file path*, not a Python trust object, so the `truststore`
library cannot stand in (it is also absent from the `python-agent-platform`
env). `ssl.get_default_verify_paths().cafile` is exactly the OS tier the
enterprise-CA convention targets — `SSL_CERT_FILE` when set to a real file,
otherwise OpenSSL's compiled-in default — and `COMPONENT_BROKER_CA_BUNDLE` is
the explicit second tier. A configured path that is not a readable file is
skipped rather than trusted, so a typo degrades to "no bundle", which is itself
a deployed refusal. Nothing resolves over the network (pap:CAP-6).

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

**Live verification** (`platform-ci-test` env, from this worktree):

- `tests/test_broker_tls_verified.py` — 22 passed. Three of them are real child
  processes: a settings probe under `config.settings.production` +
  `rediss://` reporting `ssl_cert_reqs=2 (CERT_REQUIRED)` with `ssl_ca_certs`
  at the bundle and `CELERY_REDIS_BACKEND_USE_SSL == CELERY_BROKER_USE_SSL`
  (AC1); `manage.py check` exiting non-zero naming
  `COMPONENT_BROKER_SSL_CERT_REQS` (AC2), with a same-env control that exits 0;
  and `config.settings.local` under `COMPONENT_RUNTIME=local` composing
  `ssl_cert_reqs=0 (CERT_NONE)` with no bundle (AC3).
- Whole platform suite: **398 passed**, 40 skipped, 6 failed, 120 errors —
  byte-identical failure/error set to the pre-change baseline measured by
  stashing this diff (376 passed there; the delta is exactly these 22 tests).
  The 120 errors are "no PostgreSQL on `/tmp/.s.PGSQL.5432`"; the 6 failures
  are the pre-existing openfeature/dbgpt/cloudevents/restarts/supervisor set.
- `ruff check` on every touched file: clean (repo-wide `ruff check .` is
  pre-existing red at 116, none of them in these files).
- `tests/meta/test_no_pyforge_import.py` (real `lint-imports`): passed — the new
  `config.broker_tls` module keeps the host↔factory boundary.
- `mypy` could not run at all: `Error constructing plugin instance of
  NewSemanalDjangoPlugin` / `INTERNAL ERROR`, django-stubs vs mypy 2.3.1. It
  fails before analysing any file, on a clean tree too — recorded as deferred,
  not caused here.

**Not done, deliberately.** The Helm chart is untouched: it wires `redis://`,
and the OS trust-store tier needs no chart key. Wiring
`COMPONENT_BROKER_CA_BUNDLE` / a `rediss://` broker into `values.yaml` belongs
with whichever story turns broker TLS on in-cluster.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
