---
title: "Broker TLS is verified"
type: "fix"
created: "2026-09-02"
status: "done"
followup_review_recommended: false
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
deferred:
  - summary: >-
      An explicit COMPONENT_BROKER_CA_BUNDLE cannot override a resolving OS trust
      store, so the operator knob is unreachable on any host that ships a default
      CA file.
    evidence: |-
      The intent's "Always" clause mandates "Truststore first; explicit bundle path
      second", so the ordering is contractual and was deliberately not changed here.
      The consequence is that tier 2 is reached only when tier 1 resolves nothing:
      `.pixi/envs/python-agent-platform/ssl/cert.pem` exists, and Containerfile:153
      copies the env to the same absolute prefix, so the compiled-in default resolves
      inside the shipped image. An operator installing a private CA at, say,
      /etc/pki/corp-ca.pem and setting COMPONENT_BROKER_CA_BUNDLE gets the distro
      bundle in ssl_ca_certs instead, and fails verification at first connect. The
      escape hatch under the current ordering is SSL_CERT_FILE / SSL_CERT_DIR.
      Needs a product decision (explicit-wins, or document SSL_CERT_FILE as the knob).
    location: >-
      src/platform/config/broker_tls.py — resolve_ca_trust()
    severity: medium
  - summary: >-
      CHANNEL_LAYERS (channels_redis) and REDIS_CACHE_URL (django-redis) share the
      Redis URL but get none of this TLS posture.
    evidence: |-
      src/platform/config/settings/production.py wires channel_layers_for_broker(
      REDIS_BROKER_URL) and the django-redis cache aliases; both build their own TLS
      context with no COMPONENT_BROKER_CA_BUNDLE and no CERT_NONE opt-out. The intent
      scoped this story to "the Celery broker and the result backend", so this is out
      of scope here, but it means "single declaration site for the broker's TLS
      posture" is true for Celery only.
    location: >-
      src/platform/config/settings/production.py
    severity: medium
  - summary: >-
      The Helm chart still wires plaintext redis://, so no deployed component takes
      the new code path and nothing refuses unencrypted broker traffic.
    evidence: |-
      deploy/charts/platform/templates/_helpers.tpl templates redis:// for
      REDIS_BROKER_URL, REDIS_CACHE_URL and REDIS_URL, with no TLS key and no
      COMPONENT_BROKER_CA_BUNDLE; tests/test_chart_invariants.py is unchanged. This
      story makes TLS honest when it is used; it does not turn it on. Red-team X-2 /
      directive R-14 is only half-discharged until the chart moves to rediss:// and a
      deployed plaintext broker is itself refused.
    location: >-
      deploy/charts/platform/templates/_helpers.tpl
    severity: medium
  - summary: >-
      mypy cannot run at all, so the new modules got no type check.
    evidence: |-
      "Error constructing plugin instance of NewSemanalDjangoPlugin" / INTERNAL ERROR
      (django-stubs vs mypy 2.3.1). It fails before analysing any file, on a clean
      tree too. Platform CI runs `mypy platformapp config tests`, so that step is red
      independently of this story — pre-existing, not caused here.
    location: >-
      src/platform (Platform CI mypy step)
    severity: medium
  - summary: >-
      configure_observability() now materializes Django settings even when OTel is
      disabled, and config/__init__.py imports celery_app at module scope.
    evidence: |-
      The story added load_django_settings() to configure_observability() to repair a
      real swallow (DjangoInstrumentor catching ImproperlyConfigured and calling
      settings.configure()). The call sits ahead of configure_telemetry's
      otel_sdk_is_disabled() early return, so fail-fast is now imposed on a broader
      set of process configurations than the bug required, and importing any config.*
      module pins the settings singleton to whatever DJANGO_SETTINGS_MODULE is set at
      that moment. No in-repo regression observed — the full suite's failure/error set
      is byte-identical to baseline — but the import-time contract is now stricter and
      undocumented.
    location: >-
      src/platform/config/observability/__init__.py
    severity: medium
  - summary: >-
      REDIS_SSL in base settings has no readers anywhere in the tree.
    evidence: |-
      The removed CELERY_BROKER_USE_SSL ternary was its only consumer; a repo-wide
      grep now returns only its own definition. This change kept it alive (rewritten
      through is_tls_broker) rather than removing a public settings name that ops
      tooling might read. Decide whether to drop it or record why it stays.
    location: >-
      src/platform/config/settings/base.py
    severity: low
  - summary: >-
      load_django_settings() makes Django construct its Settings object twice,
      re-entrantly, on every process that imports config.*.
    evidence: |-
      config/__init__.py imports celery_app, whose module scope calls
      configure_observability() -> load_django_settings() -> settings.INSTALLED_APPS.
      That re-enters LazySettings._setup while Django's outer Settings.__init__ is
      still importing config.settings.production (which reaches config/__init__.py
      through `from .base import *`). The inner Settings object is assigned to
      _wrapped and then silently replaced by the outer one; read_dot_env() also runs
      twice. No in-repo regression is observable (the whole-suite failure/error set is
      byte-identical to baseline, 436 passed here vs 420 pre-change with the delta
      exactly this story's tests), but the work is duplicated and the settings module
      is imported while the config package is only partially initialised. The existing
      "materializes settings even when OTel is disabled" entry records the import-time
      contract; it does not record the double construction.
    location: >-
      src/platform/config/observability/__init__.py -- load_django_settings()
    severity: medium
  - summary: >-
      A CA path that is readable but not parseable as PEM passes the boot gate and
      fails at first connect.
    evidence: |-
      resolve_ca_trust() checks existence and permission bits, never content, so an
      empty or truncated corporate bundle resolves as a trust source, stage 1 accepts
      it, and the component boots -- then every broker handshake fails. That inverts
      the property resolve_ca_trust()'s own docstring advertises ("a typo or a
      permission mistake degrades to no trust source -- which stage 1 refuses at boot
      instead of failing at first connect"). A guard would be a throwaway
      SSLContext.load_verify_locations(cafile=...) in a try/except ssl.SSLError; note
      it only helps the cafile half, since capath lookup is lazy by design.
    location: >-
      src/platform/config/broker_tls.py -- resolve_ca_trust()
    severity: medium
  - summary: >-
      config.settings.production with COMPONENT_RUNTIME=local composes CERT_NONE and
      no stage 1 runs to refuse it.
    evidence: |-
      Confirmed live: the production leaf + COMPONENT_RUNTIME=local +
      COMPONENT_BROKER_SSL_CERT_REQS=none + a rediss:// broker loads cleanly and
      composes ssl_cert_reqs=0, because run_stage_one() early-returns on
      is_deployed(). The intent keys the exception to COMPONENT_RUNTIME
      ("CERT_NONE is permitted only under COMPONENT_RUNTIME=local"), so this is
      contract-compliant and was rejected as a finding in the first review pass on
      those grounds; R-14's own wording is "must fail the production settings check",
      which is the leaf, not the marker. Whether the lever should also be refused at
      the production leaf is the product decision left open.
    location: >-
      src/platform/config/startup/stage_one.py -- run_stage_one()
    severity: medium
  - summary: >-
      config.asgi -- the entrypoint the production image actually runs -- is covered
      by nothing in the env CI uses.
    evidence: |-
      Containerfile CMD is `gunicorn config.asgi:application`. The three tests that
      import config.asgi are each gated on pytest.importorskip("langflow"), and
      langflow is in the python-agent-platform feature, not platform-ci-test -- which
      is what Platform CI installs for `python -m pytest`. So they skip in CI. This
      story's entrypoint tests exclude config.asgi for the same reason. The container
      job boots the image with a healthy config, which is a control, not a refusal.
      Needs either a langflow-free import path for the ASGI seam or a container-level
      refusal case.
    location: >-
      src/platform/config/asgi.py
    severity: medium
  - summary: >-
      LANGFLOW_REDIS_URL is a third consumer of the shared Redis URL with no TLS
      posture, alongside CHANNEL_LAYERS and the django-redis caches.
    evidence: |-
      config/settings/base.py does `os.environ["LANGFLOW_REDIS_URL"] =
      env("LANGFLOW_REDIS_URL", default=REDIS_CACHE_URL)`, handing the same URL to a
      third-party service that builds its own client. The existing "CHANNEL_LAYERS and
      REDIS_CACHE_URL share the URL" entry names two consumers; a follow-up scoped
      from it would miss this one.
    location: >-
      src/platform/config/settings/base.py
    severity: low
  - summary: >-
      test_production_leaf_source_wires_stage_one is still a source-substring
      assertion, and the call-position requirement it sits next to is unguarded.
    evidence: |-
      It asserts `"run_stage_one(" in source`, the exact assertion style this story's
      review pass removed from the broker suite, and it passes regardless of where in
      production.py the call sits. Story 41.4 made the position load-bearing: the
      condition reads the composed CELERY_BROKER_URL off the module, so moving the
      call above the Celery block silently reverts stage 1 to the env-derived URL.
      test_run_stage_one_forwards_the_settings_module pins the forwarding; nothing
      pins the ordering.
    location: >-
      src/platform/tests/test_startup_required_settings.py
    severity: low
  - summary: >-
      scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and
      new config/** files.
    evidence: |-
      The baseline hashes src/platform/config/** per file under the
      pyforge-mason/spec-django-accelerator-framework entry; settings/base.py,
      startup/stage_one.py, startup/__init__.py, observability/__init__.py, manage.py
      and settings/production.py all changed, and config/broker_tls.py is new with no
      entry at all, so spec-surface-check will report surface-changed. The follow-up
      review pass also touched deploy/README.md and tests/test_startup_required_settings.py.
      Left to the dedicated fleet reconciliation pass (a scoped stamp from a clean
      tree, never a bare --write-baseline), matching what stories 41.1, 41.2 and 41.3
      did.
    location: >-
      scripts/.spec-surface-baseline.json
    severity: low
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

**2026-09-02 — follow-up review pass, 15 findings applied.** The four that
changed behaviour: the scheme match now strips whitespace as well as folding
case (`" rediss://…"` reaches kombu's `rediss` transport, so matching the raw
string composed no SSL options for it); `ssl_check_hostname` is declared rather
than inherited from redis-py's default; the capath check requires search rather
than read permission, so a hardened `0711` CA directory is no longer refused at
boot; and `COMPONENT_BROKER_CA_BUNDLE` accepts a hashed directory and tolerates
surrounding whitespace, with every rejected path named back to the operator via
`skipped_trust_paths()`.

The rest were coverage and honesty. Three of this story's own guarantees turned
out to be unpinned — provable by mutation, since the suite stayed green with
`run_stage_one`'s argument dropped, with `_readable_dir`'s permission check
deleted, and with `configure_observability()` removed from *both* `wsgi.py` and
`manage.py`. That last one matters most: the previous pass replaced a
source-substring test with child processes precisely to guard it, but
`config/__init__.py` imports `celery_app`, whose module scope calls
`configure_observability()` — so every child produced the refusal regardless of
the entrypoint's own line. Counting calls made *after* that import is what
actually observes it. And the `FileAwareMapping` / `REDIS_BROKER_URL_FILE`
rationale repeated in two docstrings and the first triage log is simply false
here: `base.py` builds `environ.Env()`, so no `_FILE` key is ever read. The
patch it justified stands on the whitespace and empty-value divergence alone.

Finally, the two operator knobs are documented where an operator looks
(`src/platform/deploy/README.md`), including the second-tier caveat that an
explicit `COMPONENT_BROKER_CA_BUNDLE` cannot override a resolving OS trust
store — the deferred item that the contractual ordering makes unavoidable.

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

## Review Triage Log

### 2026-09-02 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 5, low 6)
- defer: 7: (high 0, medium 5, low 2)
- reject: 8: (high 0, medium 1, low 7)
- addressed_findings:
  - `[medium]` `[patch]` `resolve_ca_bundle()` ignored the `capath` half of the OS
    trust store, so a host with a hashed-directory CA install and no concatenated
    `cert.pem` was refused at boot despite a correctly installed corporate CA.
    Replaced by `resolve_ca_trust() -> CaTrust(cafile, capath)`, emitting
    `ssl_ca_path` after verifying redis-py 8.1.0 / kombu 5.6.2 / celery 5.6.3 all
    carry the kwarg through to `load_verify_locations(capath=…)`.
  - `[medium]` `[patch]` Stage 1 validated a broker URL re-derived from raw
    `os.environ`, which can disagree with the composed value on whitespace and on
    empty strings. It now reads the composed `CELERY_BROKER_URL` off the
    `settings_module` it was already handed and discarding; env is the fallback
    only. (**Corrected in the 2026-09-02 follow-up pass:** this entry originally
    also cited django-environ's `FileAwareMapping` / `REDIS_BROKER_URL_FILE`
    secret-mount precedence. That is not true of this codebase — `base.py` builds
    `environ.Env()`, not `environ.FileAwareEnv()`, so no `_FILE` key is ever read.
    The patch stands on the whitespace/empty-value divergence alone.)
  - `[medium]` `[patch]` `is_tls_broker()` was a case-sensitive `startswith`, so a
    legal `REDISS://` URL reached the `rediss` transport with zero ssl kwargs —
    kombu's own "defaulting to insecure SSL behaviour" path. Match is case-blind.
  - `[medium]` `[patch]` `test_entrypoints_load_settings_before_instrumenting`
    asserted a literal source substring and would still pass if `wsgi`, `asgi` or
    `celery_app` dropped its `configure_observability()` call — the exact regression
    it claimed to guard. Replaced with parametrised real child processes (refusal +
    boots-fine control) for `manage.py`, `wsgi` and `celery_app`.
  - `[medium]` `[patch]` Child-process tests were not hermetic: `_child_env()` left
    `DJANGO_READ_DOT_ENV_FILE` in place, so a developer `.env` could re-supply
    `COMPONENT_RUNTIME` or a broker URL and make the "passes" control pass for the
    wrong reason. Added it plus `SSL_CERT_DIR` and `COMPONENT_PROCESS` to one shared
    `CONTROLLED_ENV_KEYS`.
  - `[low]` `[patch]` Trust-path checks were existence-only, so an unreadable path
    was reported as resolved and passed the boot gate. Added `os.access` (`R_OK` for
    files, `R_OK|X_OK` for the capath directory).
  - `[low]` `[patch]` `CERT_REQS_BY_NAME`'s values were never read — composition
    hardcoded both outcomes while stage 1 only membership-tested keys, so a future
    weaker rung would be accepted and silently downgraded. Both now map through the
    table, and the deployed refusal branches on the verify mode.
  - `[low]` `[patch]` An unrecognised `COMPONENT_BROKER_SSL_CERT_REQS` was silent on
    a laptop (no stage 1 runs there), upgrading `…=nonee` to `CERT_REQUIRED` and
    breaking the self-signed-Redis workflow with an opaque TLS error. Now named from
    `resolve_cert_reqs()` when local only, keeping stage 1's deployed refusal
    reachable.
  - `[low]` `[patch]` The `REDIS_URL`-only deployment shape that `compose.yml`
    actually uses had no test — deleting that fallback tier passed the whole suite.
    Added unit, stage-1-visibility and child-process production cases, and fixed the
    no-trust message that named only `REDIS_BROKER_URL`.
  - `[low]` `[patch]` Stale `production.py` call-site comment still described stage 1
    as leaving "the hook for later namespace conditions".
  - `[low]` `[patch]` The `## Verification` section named a test file that does not
    exist and `pixi run -e python-agent-platform`, an env that cannot even collect
    this suite. Updated to the verbatim `platform-ci-test` command actually used.

### 2026-09-02 — Review pass (follow-up)

The single allowed follow-up review of a `done` spec (step-01's
`followup_review_recommended: true` branch, CAP-11). Four layers over the
whole diff since `7841e5c84e`.

- intent_gap: 0
- bad_spec: 0
- patch: 15: (high 0, medium 4, low 11)
- defer: 6: (high 0, medium 5, low 1)
- reject: 7: (high 0, medium 2, low 5)
- addressed_findings:
  - `[medium]` `[patch]` `broker_url_from_settings()` returned the composed URL
    unstripped, so `REDIS_BROKER_URL=" rediss://…"` composed **no** SSL options
    while `urlsplit` (which strips leading spaces before reading the scheme) still
    routed it to kombu's `rediss` transport — encrypted but unauthenticated,
    reachable by a stray ConfigMap space. Verified live that
    `urlsplit(" rediss://…").scheme == "rediss"`. `is_tls_broker()` now strips
    before matching (one site, covers every caller) and the composed URL reaches
    stage 1 stripped.
  - `[medium]` `[patch]` `ssl_check_hostname` was never declared, so "verified"
    rested on redis-py 8.1's default: a certificate any trusted CA issued, for any
    hostname, would have been accepted had that default changed. Now composed
    explicitly, `True` exactly where verification is on — which is also what
    redis-py coerces it to for `CERT_NONE`.
  - `[medium]` `[patch]` Nothing pinned `run_stage_one` **forwarding** its settings
    module: the only case exercising it sets a `none` policy, which raises before
    the URL is read. Proven by mutation — dropping the argument left the suite at
    67 passed while stage 1 silently reverted to the env-derived URL.
    `test_run_stage_one_forwards_the_settings_module` (control + refusal driven
    only by the module's URL) now fails on that mutation.
  - `[medium]` `[patch]` The entrypoint refusal tests could not observe what their
    docstring claimed: `config/__init__.py` imports `celery_app`, which calls
    `configure_observability()` at module scope, so *any* `import config.*`
    produces the refusal. Proven by mutation — deleting the call from both
    `wsgi.py` and `manage.py` left the suite at 67 passed.
    `test_entrypoint_makes_its_own_observability_call` counts calls made after
    that import and fails on it; the older test's docstring now states what it
    actually guards.
  - `[low]` `[patch]` `_readable_dir` demanded `R_OK|X_OK`, but OpenSSL's hashed
    lookup opens `<hash>.<n>` by constructed name and never lists the directory —
    a hardened `0711` CA directory is a correct install and was being refused at
    boot. Now `X_OK` only, with both halves tested (`0711` trusted, `0o000` not).
  - `[low]` `[patch]` The `os.access` check on the capath half was unguarded:
    removing it entirely left the suite at 67 passed (the only chmod test targets a
    file). `test_existing_but_unsearchable_ca_dir_is_not_trusted` is the mirror.
  - `[low]` `[patch]` `COMPONENT_BROKER_CA_BUNDLE` was neither stripped nor allowed
    to be a directory — a trailing newline (how a ConfigMap or here-doc hands over a
    path) or a hashed-directory path silently resolved to no trust, producing a
    refusal telling the operator to set what they had set. Both shapes now accepted,
    value stripped.
  - `[low]` `[patch]` A rejected trust path was never named back: a typo and a
    permissions mistake produced byte-identical output. New `skipped_trust_paths()`
    reports each configured-but-unusable `ENV=path`, appended to
    `no_ca_trust_message()`; OpenSSL's compiled-in defaults are excluded (nobody
    configured them).
  - `[low]` `[patch]` The `FileAwareMapping` / `REDIS_BROKER_URL_FILE` rationale in
    `broker_url_from_settings()`, `refuse_unverified_broker_tls()` and the previous
    pass's triage entry is false here: `base.py` builds `environ.Env()`, not
    `environ.FileAwareEnv()`, so no `_FILE` key is read. Verified live. All three
    rewritten to the divergence that is real (whitespace, empty values, the
    layering chain); the prior triage entry carries a dated correction.
  - `[low]` `[patch]` `pytest.importorskip("redis.connection")` could silently
    delete the only third-party contract test. redis-py is a hard runtime
    dependency of a Celery/Redis deployment — imported directly now, so its absence
    fails loudly.
  - `[low]` `[patch]` The `SSLConnection` constructor test covered only the
    `CERT_REQUIRED` mapping; the `CERT_NONE` one (no CA keys, and the shape that
    interacts with redis-py's `check_hostname` coercion) was compared to a dict
    literal alone. `test_redis_py_accepts_the_unverified_kwargs_too` constructs it
    for real.
  - `[low]` `[patch]` The OS tier's *compiled-in default* — the one the shipped
    image runs on — had no test; every trust case pinned `SSL_CERT_FILE`/`_DIR`.
    `test_openssl_compiled_defaults_are_the_first_tier` covers the unset case
    against `ssl.get_default_verify_paths()` itself.
  - `[low]` `[patch]` `__all__` omitted `BROKER_URL_ENV_VAR` and
    `REDIS_URL_ENV_VAR`, both consumed as public names by the tests and rendered
    into operator-facing text. Added, along with the new `CAFILE_ENV_VAR` /
    `CAPATH_ENV_VAR` / `skipped_trust_paths`.
  - `[low]` `[patch]` `test_startup_required_settings.py` was not isolated after
    `run_stage_one` grew a second condition: its autouse fixture cleared only
    `COMPONENT_RUNTIME`, so its happy paths passed only because the ambient shell
    exported no broker keys. It now clears them too; `CONTROLLED_ENV_KEYS` also
    gained `OTEL_SDK_DISABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT`, which change which
    telemetry path the entrypoint children take.
  - `[low]` `[patch]` The two operator knobs were documented nowhere an operator
    would look — only in docstrings and this spec. `src/platform/deploy/README.md`
    now carries a **Broker TLS** table: both env keys, the second-tier caveat, and
    the remedy for the no-trust boot refusal.
  - `[low]` `[patch]` "Files changed" described `manage.py` as entrypoint wiring
    when its diff is comment-only (the wiring lives inside
    `configure_observability()`). Corrected below.

## Auto Run Result

Status: done
Blocking condition: none

### Summary of implemented change

`CELERY_BROKER_USE_SSL` no longer composes `ssl.CERT_NONE` for every `rediss://`
broker. The TLS posture moved into `src/platform/config/broker_tls.py`, one
declaration site feeding both the Celery broker and the result backend (base
settings already aliases the second to the first). Composition fails closed:
`CERT_NONE` is emitted only for a process that is explicitly
`COMPONENT_RUNTIME=local` *and* asked for it via `COMPONENT_BROKER_SSL_CERT_REQS`,
so a deployed component that asks still composes `CERT_REQUIRED` — the new stage-1
condition `refuse_unverified_broker_tls()` makes that misconfiguration loud rather
than silently corrected. CA trust resolves truststore-first (`SSL_CERT_FILE` /
`SSL_CERT_DIR`, else OpenSSL's defaults), with `COMPONENT_BROKER_CA_BUNDLE` as the
explicit second tier, both checked for readability. AC2 additionally required
repairing a pre-existing swallow: OpenTelemetry's `DjangoInstrumentor` caught
`ImproperlyConfigured` and answered it with `settings.configure()`, so every
entrypoint demoted stage-1 refusals to a debug log and booted with empty defaults —
`configure_observability()` now calls `load_django_settings()` first.

### Files changed

- `src/platform/config/broker_tls.py` — new; the single declaration site for the
  broker's TLS posture (policy names, `resolve_cert_reqs`, `resolve_ca_trust`,
  `broker_use_ssl`, `is_tls_broker`, `skipped_trust_paths`). Composes
  `ssl_check_hostname` explicitly; the scheme match is case- and
  whitespace-blind; the explicit CA knob takes a file or a hashed directory.
- `src/platform/config/startup/stage_one.py` — adds `refuse_unverified_broker_tls()`
  with three named refusals; `run_stage_one` now reads the composed broker URL off
  the settings module instead of discarding it.
- `src/platform/config/settings/base.py` — delegates to the helper; `import ssl` and
  the `CERT_NONE` ternary are gone.
- `src/platform/config/startup/__init__.py` — re-exports the new condition; corrects
  the "no celery refusals here" note.
- `src/platform/config/observability/__init__.py` — `configure_observability()` loads
  Django settings before instrumenting, restoring fail-fast at every entrypoint.
- `src/platform/config/settings/production.py` — stale stage-1 call-site comment.
- `src/platform/manage.py` — comment only, pointing at the observability ordering;
  the wiring itself lives inside `configure_observability()`.
- `src/platform/deploy/README.md` — **Broker TLS** operator section: both env
  knobs, the second-tier caveat, and the remedy for the no-trust boot refusal.
- `src/platform/tests/test_broker_tls_verified.py` — new; 60 tests, including real
  child processes for all three ACs, for each entrypoint's refusal, for each
  entrypoint's own `configure_observability()` call, and for the composed
  `CELERY_BROKER_URL` on the real production leaf.
- `src/platform/tests/test_startup_required_settings.py` — autouse fixture clears
  the broker env keys, so the second stage-1 condition cannot decide its cases.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  — `41-4-broker-tls-is-verified: backlog → review`.

### Review findings breakdown

Two passes ran against this story. The counts below are cumulative; each pass is
itemised separately in the Review Triage Log above.

**Follow-up pass (2026-09-02, the single allowed one for a `done` spec):**

- Patches applied: 15 (4 medium, 11 low). Four were proven necessary by
  mutation — the pre-existing suite stayed at 67 passed with `run_stage_one`'s
  argument dropped, with `_readable_dir`'s `os.access` removed, with
  `configure_observability()` deleted from `wsgi.py` *and* `manage.py`, and the
  whitespace hole was reachable with the shipped code. The new cases fail on all
  four.
- Items deferred: 6 (5 medium, 1 low) — appended to frontmatter `deferred`. The
  substantive ones: `load_django_settings()` constructs Django's `Settings`
  twice, re-entrantly; a readable-but-unparseable CA file still passes the boot
  gate; the production leaf under `COMPONENT_RUNTIME=local` composes `CERT_NONE`
  with no refusal; `config.asgi` — the image's actual entrypoint — is covered by
  nothing in the env CI runs.
- Items rejected: 7. Chiefly — the `followup_review_recommended: false`
  frontmatter "contradicting" the body's computed `true` (that is step-01's
  forced-false rule for a `done` spec, not a defect); `baseline_commit` vs
  `baseline_revision` (distinct fields, epic stamp vs branch base); the
  `Tasks`/ledger/`Auto Run Result` state triple (documented: `done` is the
  landing step's); stage 1 reading `CELERY_BROKER_USE_SSL` directly instead of
  recomputing the policy (no leaf assigns it); a warning for a non-production
  leaf with `COMPONENT_RUNTIME` unset (the three entrypoints `setdefault` it);
  and re-reading AC3 as "the laptop must keep `CERT_NONE` as its *default*"
  (the AC's subject is the `CERT_NONE` mode staying honoured, which it does —
  the opt-in is now documented, which was the real gap). The precedence
  inversion and the plaintext chart were deduplicated against existing
  `deferred` entries rather than re-raised.

**First pass (2026-09-02):**

- Patches applied: 11 (5 medium, 6 low) — all accepted by the implementer, none
  rejected on evidence. Itemised in the Review Triage Log above.
- Items deferred: 7 (5 medium, 2 low) — recorded in frontmatter `deferred`. The
  substantive ones: the contractual truststore-first ordering makes
  `COMPONENT_BROKER_CA_BUNDLE` unreachable on hosts with a default CA file; Channels
  and the django-redis cache share the URL but not the posture; the Helm chart still
  wires plaintext `redis://`, so R-14 is only half-discharged; mypy cannot run at all.
- Items rejected: 8. Chiefly — the recommendation to invert the CA-bundle precedence
  (the intent's "Always" clause mandates truststore first, so it is not an admissible
  scope authority for reversal); a claimed `done → review` ledger regression on story
  41-3 (verified: the branch touched only its own row, `main` moved 41-3 to `done` in
  commit `9a288066f5` after the branch point, and a real merge preserves it);
  `manage.py help` now tracebacking under a refusing deployed config (that is the
  intended CAP-3 fail-fast); the `COMPONENT_RUNTIME=local` lever being settable in a
  production container (pre-existing, and the intent defines locality that way).

### Follow-up review recommendation

`false` — **forced**. This run *was* the single allowed follow-up review of a
`done` spec (step-01's `followup_review_recommended: true` branch), and step-04
requires the flag to be `false` at HALT regardless of score. For the record, the
computation would have said `true`: patched findings high 0, medium 4, low 11,
score = 3 × 4 + 1 × 11 = **23**, which is ≥ 5. The residue is carried by the six
new `deferred` entries, not by another review pass.

### Verification performed

Follow-up pass, all from `src/platform` in the `platform-ci-test` env:

- Spec's `## Verification` command, run verbatim: `pixi run --frozen -e
  platform-ci-test python -m pytest tests/test_startup_required_settings.py
  tests/test_broker_tls_verified.py -q` → **83 passed** (was 67 before this pass;
  45 before the first patch pass).
- **Mutation-verified the four new guards** — each mutation applied, the suite
  run, then the file restored from a byte-copy and confirmed clean against the
  branch:
  - `run_stage_one` calling `refuse_unverified_broker_tls()` with no argument →
    `test_run_stage_one_forwards_the_settings_module` fails.
  - `configure_observability()` deleted from `config/wsgi.py` →
    `test_entrypoint_makes_its_own_observability_call[wsgi]` fails (`CALLS 0`).
  - `_readable_dir` losing its `os.access` check →
    `test_existing_but_unsearchable_ca_dir_is_not_trusted` fails.
  - `is_tls_broker` matching the raw string →
    `test_padded_tls_url_still_composes_ssl_options[leading-space, both]` fails.
  All five expected failures observed, and only those.
- Full platform suite: **436 passed**, 40 skipped, 6 failed, 120 errors — the
  failure and error sets are unchanged from the recorded baseline (420 passed
  there; the delta is exactly this story's 16 new tests). The 120 errors are "no
  PostgreSQL socket"; the 6 failures are the pre-existing openfeature / dbgpt /
  cloudevents / restarts / supervisor set.
- `ruff check` clean on every touched file; repo-wide count unchanged at exactly
  **116**, the pre-existing baseline.
- `tests/meta/test_no_pyforge_import.py` (real `lint-imports`): passed — the
  host↔factory boundary holds.
- Live probes behind the patches, in the same env: `urlsplit(" rediss://…")`
  reports scheme `rediss` (the whitespace hole is real); redis-py 8.1 declares
  `ssl_check_hostname` and coerces it to `False` for `CERT_NONE`;
  `environ.FileAwareEnv` exists but `base.py:44` builds `environ.Env()` (the
  `_FILE` rationale was false).
- Frontmatter re-parsed as YAML after the `deferred` append: one list, 13
  well-formed items (7 prior + 6 new).
- No I/O & Edge-Case Matrix in the intent contract, so the matrix test audit did
  not apply.

### Residual risks

- The three ACs are met at the composed-settings and process-exit surfaces, but no
  deployed component exercises the new code path yet — the chart wires `redis://`.
  This story makes TLS honest when used; turning it on in-cluster is separate.
- `config.asgi` is the one entrypoint without a real child-process boot test; it
  imports `langflow_integration`, which needs the `python-agent-platform` env.
  The follow-up pass established this is worse than it looked — the three tests
  that import `config.asgi` are all `importorskip("langflow")`-gated, so they
  skip in the env CI actually runs, and `config.asgi` is what the image's
  `CMD` executes. Recorded as a `deferred` entry.
- A CA path that is readable but not parseable as PEM still satisfies the boot
  gate and fails at first connect, which is the inverse of what this module
  promises. Deferred rather than patched: the guard only covers the `cafile`
  half (capath lookup is lazy), so it is a partial fix that deserves its own
  decision.
- AC3 is satisfied under the reading that `CERT_NONE` stays *reachable* locally
  (the intent's Approach says "permitted only under `COMPONENT_RUNTIME=local`"), not
  that it stays the local *default*. A laptop pointed at a self-signed `rediss://`
  Redis now needs `COMPONENT_BROKER_SSL_CERT_REQS=none`. Nothing in-repo wires such a
  broker today, so the change is latent.
- Landing notes: this branch touches nothing under `recipes/`, so the PR needs the
  `maintenance` label at open; `pixi.toml` is untouched, so no `environment.yaml`
  regeneration. Merge with `--merge`, not `--squash`, so `main`'s later `41-3: done`
  ledger value survives. `scripts/.spec-surface-baseline.json` will report
  `surface-changed` until the fleet reconciliation pass stamps it (deferred above).
