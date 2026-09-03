---
title: "Broker TLS is verified"
type: "fix"
created: "2026-09-02"
status: "done"
followup_review_recommended: true
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
      scripts/.spec-surface-baseline.json needs a scoped stamp for the changed and
      new config/** files.
    evidence: |-
      The baseline hashes src/platform/config/** per file under the
      pyforge-mason/spec-django-accelerator-framework entry; settings/base.py,
      startup/stage_one.py, startup/__init__.py, observability/__init__.py, manage.py
      and settings/production.py all changed, and config/broker_tls.py is new with no
      entry at all, so spec-surface-check will report surface-changed. Left to the
      dedicated fleet reconciliation pass (a scoped stamp from a clean tree, never a
      bare --write-baseline), matching what stories 41.1, 41.2 and 41.3 did.
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
    `os.environ`, which disagrees with django-environ's `FileAwareMapping`
    (`REDIS_BROKER_URL_FILE` secret-mount precedence) and on empty values. It now
    reads the composed `CELERY_BROKER_URL` off the `settings_module` it was already
    handed and discarding; env is the fallback only.
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
  `broker_use_ssl`, `is_tls_broker`).
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
- `src/platform/manage.py` — entrypoint wiring for the observability ordering.
- `src/platform/tests/test_broker_tls_verified.py` — new; 44 tests, including real
  child processes for all three ACs and for each entrypoint.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  — `41-4-broker-tls-is-verified: backlog → review`.

### Review findings breakdown

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

`true`. Patched findings by severity: high 0, medium 5, low 6. Score =
3 × 5 + 1 × 6 = **21**, which is ≥ 5.

### Verification performed

- Spec's `## Verification` command, run verbatim from `src/platform` after the patch
  pass: `pixi run --frozen -e platform-ci-test python -m pytest
  tests/test_startup_required_settings.py tests/test_broker_tls_verified.py -q` →
  **67 passed**. (Pre-patch it was 45 passed on the same two files.)
- Full platform suite: 420 passed, 40 skipped, 6 failed, 120 errors — failure and
  error sets byte-identical to the pre-change baseline measured by stashing the diff.
  The 120 errors are "no PostgreSQL socket"; the 6 failures are the pre-existing
  openfeature / dbgpt / cloudevents / restarts / supervisor set.
- `ruff check` clean on every touched file (repo-wide count unchanged at exactly 116,
  none in these files); `lint-imports` reports 0 broken, so the host↔factory boundary
  holds and the new module imports only stdlib plus `config.locality`.
- Frontmatter re-parsed as YAML after the `deferred` append: one list, 7 well-formed
  items.
- No I/O & Edge-Case Matrix in the intent contract, so the matrix test audit did not
  apply.

### Residual risks

- The three ACs are met at the composed-settings and process-exit surfaces, but no
  deployed component exercises the new code path yet — the chart wires `redis://`.
  This story makes TLS honest when used; turning it on in-cluster is separate.
- `config.asgi` is the one entrypoint without a real child-process boot test; it
  imports `langflow_integration`, which needs the `python-agent-platform` env.
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
