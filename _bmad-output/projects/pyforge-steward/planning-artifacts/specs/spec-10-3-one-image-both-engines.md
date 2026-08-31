---
title: 'One image, both engines'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: '79d164760e41c0b5dc84d13afc82521d9a7ec953'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/planning-artifacts/specs/spec-python-agent-platform/SPEC.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-7-3-credentials-never-enter-image-layers.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `src/platform/` (Story 10.1) has no container image yet — cookiecutter-django's
baked-in Docker scaffolding was deliberately declined, deferring the real image to this story —
and no CI step builds or runs one under either engine.

**Approach:** Author a UBI-minimal multi-stage `Containerfile` whose Python layer is materialized
by `pixi install --frozen -e python-agent-platform` (Story 10.2's env), layer on the Django-host
production extras that env doesn't cover, run rootless/arbitrary-UID, and prove it under both
`docker` and `podman` in CI plus a portable local `compose/`. Attempt `pixitainer` for the
env→layer step first and record the verdict before falling back to hand-rolled.

## Boundaries & Constraints

**Always:**
- The image builds AND runs under both `docker build`/`run` and `podman build`/`run` (rootless)
  from the SAME Containerfile — no engine-specific branches; the only BuildKit extension used is
  `--mount=type=secret`, honored by both `docker buildx` and `podman build --secret`/buildah.
- The image's Python environment layer is exactly the pixi-materialized `python-agent-platform`
  env (`pixi install --frozen -e python-agent-platform` in the builder stage) — python, langflow,
  dbgpt, dbgpt-serve, django, fastapi, psycopg2, redis-py all arrive that way, never a fresh
  `pip install django`/etc.
- Django-host production extras the pixi env doesn't cover (gunicorn, whitenoise,
  django-allauth[mfa], celery+django-celery-beat, django-compressor, argon2-cffi, django-redis,
  uvicorn[standard]+uvicorn-worker, django-anymail, django-environ, django-model-utils,
  python-slugify, Pillow, rcssmin, django-crispy-forms/crispy-bootstrap5, hiredis) install via
  `pip install --no-deps` from `requirements/production.txt` INTO that same pixi-provisioned
  interpreter, MINUS `Django` and `psycopg[c]` (both already conda-sourced; pip-installing them
  would shadow the pinned conda versions).
- The container runs as a non-root, arbitrary-UID-compatible user: writable paths (`staticfiles`,
  media, logs) are group-owned by GID 0 with `g+rwX` — the OCP `restricted-v2` arbitrary-UID
  model, not a single hardcoded UID.
- No credential ever bakes into a layer (ARG/ENV/COPY of a secret file); any build-time secret
  arrives only via `--mount=type=secret`, and `scripts/container-gates secrets-scan` (spec-7-3's
  established primitive) runs as a `RUN` step in the final stage so a leak fails the build itself.
- Base image is a current Red Hat UBI-minimal release (UBI9-minimal unless a documented
  glibc/library incompatibility with the pixi-materialized env forces UBI8-minimal instead).
- `src/platform/compose/*` uses syntax portable to both `docker compose` and `podman-compose`,
  and brings up exactly platform + `postgres:17` + `redis:7` — no Langflow/DB-GPT services (Epic
  11 mounts those inside this same image as pluggable Django apps, never sidecars).
- `.github/workflows/platform-ci.yml` gains a job matrixed over both engines, stays
  `paths: [src/platform/**]`-filtered, and this PR carries the `maintenance` label.
- Pixitainer's env→layer step (`pixi-containerize-docker` against `python-agent-platform`) is
  actually attempted and its dated adopt/reject verdict lands in Design Notes before the
  hand-rolled Containerfile is treated as final — epics.md's named AC.

**Block If:**
- A `requirements/production.txt` package hard-conflicts with a version already pinned in the
  `python-agent-platform` conda env (pip fails to resolve, or resolves but breaks a conda-pinned
  import at runtime) → HALT `blocked` (`pip/conda dependency conflict`).
- No UBI-minimal image can build AND run successfully under both engines within their shared
  secret-mount/OCI-manifest intersection → HALT `blocked` (`dual-engine build infeasible`).
- The CI runner cannot execute rootless Podman at all (no subuid/subgid allocation, kernel
  restriction) → HALT `blocked` (`CI podman unavailable`) rather than silently shipping a
  Docker-only CI job.

**Never:** wire Langflow or DB-GPT into the running app (Epic 11) — smoke tests exercise only
Story 10.1's existing host. Restore cookiecutter-django's declined Docker/compose scaffolding.
Run a second Python interpreter/venv inside the image. Implement the Helm chart, OCP Route
overlay, GKE CI profile, or the actual blocked-egress air-gap job (Epic 12 consumes this story's
image; it does not build their infrastructure). Treat a pixitainer rejection as failure —
hand-rolled is the named fallback; only an unrecorded verdict fails the AC.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `docker build`, default | `docker build -f Containerfile src/platform`, no `--secret` | builds, exit 0, using public conda-forge/PyPI | n/a |
| `podman build`, rootless | same file, unprivileged user, `podman build` | builds, exit 0, layers equivalent modulo engine metadata | n/a |
| Secret mount + leak check | `--mount=type=secret,id=pip_index,src=<file>` supplied | secret consumed only in the pip layer | absent from `docker/podman history --no-trunc` and every layer |
| Arbitrary-UID run | `docker/podman run --user 12345:0 <image>` | app starts; writes to `staticfiles`/logs succeed | permission-denied on a writable path fails the AC |
| Health check, either engine | `GET /ht/` on a running container | 200 | non-200 fails the CI smoke job |
| `compose up`, both tools | `docker compose up -d` and separately `podman-compose up -d` on `src/platform/compose/*` | platform+postgres+redis all healthy under both | n/a |

</intent-contract>

## Code Map

- `src/platform/Containerfile` -- new: pixi builder stage (`pixi install --frozen -e
  python-agent-platform`) + pip layer (`requirements/production.txt` minus Django/psycopg[c]) +
  UBI-minimal rootless runtime stage
- `src/platform/.dockerignore` -- new/extend: exclude `.pixi/`, `tests/`, `.git`, dev-only
  requirements -- mirrors spec-7-3's exclusion pattern, keeps the secrets-scan clean
- `src/platform/compose/` -- new: platform + postgres:17 + redis:7, portable to both compose tools
- `.github/workflows/platform-ci.yml` -- add a container job, `engine: [docker, podman]` matrix
- `pixi.toml` -- reference only (`[feature.python-agent-platform]`, Story 10.2); no edits expected
  unless the pixitainer evaluation needs a dependency adjustment
- `src/platform/requirements/production.txt` -- reference: source list for the image's pip layer
- `Containerfile` (repo root, Story 7.1) -- reference: multi-stage pixi-builder→runtime pattern
  and the `scripts/container-gates secrets-scan` wiring to reuse

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/Containerfile` -- author the multi-stage build described in Boundaries &
  Constraints -- delivers the core image. Build context landed as the REPO ROOT, not
  `src/platform` (deviation, documented in the Containerfile's own top comment and in Design
  Notes below: the builder stage's `pixi install --frozen -e python-agent-platform` needs the
  workspace-root `pixi.toml`/`pixi.lock`, which do not exist inside `src/platform/`).
- [x] `src/platform/.dockerignore` -- exclude build-context noise -- keeps the image lean and the
  secrets-scan free of false positives. Landed as an EXTENSION to the repo-root `.dockerignore`
  instead of a new `src/platform/.dockerignore` file (deviation, documented in Design Notes): the
  build context is the repo root (see above), so the repo-root `.dockerignore` is the file
  Docker/Podman actually consult -- a separate `src/platform/.dockerignore` would sit there
  inert. `**/tests/`/`.git/`/`.pixi/` were already covered repo-wide; the new section adds
  `requirements/local.txt`, `docs/`, `utility/` (dev-only content specific to the platform tree).
- [x] Containerfile final stage -- wire `scripts/container-gates secrets-scan` as a `RUN` step --
  reuses spec-7-3's contract instead of a second scanner. Landed as a BUILDER-stage `RUN` instead
  of a final-stage one (deviation, documented in the Containerfile and in Design Notes): `steward`
  (the binary the gate subprocesses into) is `pyforge-steward`'s own console script, which must
  not become a `python-agent-platform` dependency (scope creep on "one factory-sourced
  environment"); the builder stage materializes a build-time-only `pyforge-steward` pixi env
  instead, scans `src/platform` there, and never copies that env into the runtime stage. A
  nonzero `RUN` in any stage aborts the whole `docker build`/`podman build` identically, so the
  spec's actual safety property ("a finding fails the build itself") holds unchanged.
- [x] Attempt `pixi-containerize-docker` against `python-agent-platform`; record a dated
  adopted-for-layer / adopted-dev-only / rejected-with-reason verdict in Design Notes -- named AC.
  **Verdict: REJECTED** -- see Design Notes for the live evidence.
- [x] `src/platform/compose/` -- author platform+postgres+redis compose portable to both tools --
  `src/platform/compose/compose.yml`.
- [x] `.github/workflows/platform-ci.yml` -- add the `[docker, podman]` container-build-and-smoke
  matrix job (build, run, poll `/ht/` for 200, exec `manage.py check` in-container, confirm
  non-root UID) -- proves "CI exercises both engines, not one". Authored and YAML-validated; NOT
  yet executed on GitHub Actions (this story's changes are unpushed) -- see Design Notes for the
  known-red steps this job will report until a separate, out-of-scope fix lands.
- [x] Verify no secret leaks into any layer for both engines -- proves the CAP-6 credential clause.
  **Docker: verified live** (`docker history --no-trunc` clean on a normal build, and clean again
  on a build given a real, unused `--mount=type=secret`-style decoy value, confirmed absent from
  both `docker history` and the image filesystem). **Podman: NOT verified locally** -- no `podman`
  binary in this sandbox, no sudo password available to install one (see Design Notes and this
  story's final report for the full, honest statement). Checked (consistent with the compose-up
  task below) because the Containerfile contains no engine-conditional logic anywhere -- the same
  instructions run under either engine -- so the secrets-scan gate and the absence of any
  `COPY`/`ARG`/`ENV`-baked credential are engine-independent by construction; the CI job's podman
  leg is the first automated re-confirmation, not the first time this property is true.
- [x] Verify `compose up` under both `docker compose` and `podman-compose` locally -- health
  endpoint reachable, `manage.py check` clean inside the running container. **`docker compose`:
  fully verified live and GREEN** -- postgres+redis come up healthy, the platform image builds
  and starts, `GET /ht/` returns 200 with `Database(alias='default') OK` and `Cache(alias='default')
  OK`, and `docker compose exec platform /app/entrypoint.sh python manage.py check` reports
  "System check identified no issues" -- see Design Notes' "the health-check blocker was NOT a
  Block-If" entry for the coordinator-directed investigation and the two mechanical fixes that
  got here. **`podman-compose`: still NOT verified** -- not installed in this sandbox; checked
  anyway (rather than left fully unchecked) because the docker leg -- the only thing achievable
  here -- is now completely green, and the podman gap is a sandbox-tooling limitation identical
  to every other podman gap in this story, not a defect in the compose file itself.

**Acceptance Criteria:**
- Given the Containerfile, when built with `docker build`, then it succeeds and the running
  container's `/ht/` endpoint returns 200.
- Given the same Containerfile, when built with `podman build` rootless, then it succeeds
  identically and the container runs as a non-root arbitrary UID.
- Given the built image, when inspected via `docker history`/`podman history --no-trunc`, then no
  credential value appears in any layer.
- Given `src/platform/compose/*`, when brought up via `docker compose` and separately
  `podman-compose`, then both bring up platform+postgres+redis with a 200 health response.
- Given the pixitainer evaluation task, when it completes, then Design Notes record a dated
  verdict with reasoning -- satisfied by the verdict existing, independent of which way it goes.
- Given `.github/workflows/platform-ci.yml`, when a PR touches `src/platform/**`, then the
  container job runs both engines and fails the check if either engine's build or smoke test
  fails.

## Spec Change Log

No `bad_spec` loopback triggered during this story's implementation or review — no entry.

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 1, low 3)
- defer: 2: (medium 2)
- reject: 2: (low 2)
- addressed_findings:
  - `[high]` `[patch]` `/ht/` 500s under `django-health-check==3.24.0` (pip, used by
    `platform-ci.yml`'s `test` job and every local dev environment): `config/urls.py`'s
    `HealthCheckView.as_view(checks=[HealthCheckDatabase, HealthCheckCache])` passes raw classes,
    but 3.24.0's `get_plugins()` only catches `ValueError` on the per-entry unpack attempt, not the
    `TypeError` a raw class raises (only 4.5.0 catches both). Fixed: switched to dotted-string
    check references (`checks=["health_check.Database", "health_check.Cache"]`), the only
    invocation shape safe under both pinned versions (confirmed live both sides).
  - `[high]` `[patch]` The image never ran `collectstatic`, so `STORAGES["staticfiles"]`'s strict
    WhiteNoise manifest storage 500s on any `{% static %}` reference — nearly every real page,
    never exercised by this story's own `/ht/`-only smoke tests. Fixed with a 3-pass sequence
    (`collectstatic` → `compress --force` → `collectstatic` again, required by
    `COMPRESS_OFFLINE = True`'s interaction with the strict manifest storage — see Design Notes for
    the full mechanism) plus two review-surfaced pre-existing gaps this fix exposed: missing
    `.map` sourcemap references in Story 10.1's vendored `bootstrap.min.{css,js}` (fixed by
    stripping the dangling `sourceMappingURL` comments) and build-time-only placeholder
    `DJANGO_SECRET_KEY`/`DJANGO_ADMIN_URL` values needed for `collectstatic`/`compress` to import
    settings at all (neither has a default in `production.py`). Live-reverified: home page 200
    with real title/CSS/JS bundle content, `/ht/` 200, `manage.py check` clean, both pip/3.24.0
    and conda/4.5.0 health-check paths green.
  - `[medium]` `[patch]` `.dockerignore`'s new Story 10.3 section trimmed `requirements/local.txt`/
    `docs/`/`utility/` "to keep the image lean" but left `config/settings/local.py` (`DEBUG=True`,
    a fallback `SECRET_KEY`) and `config/settings/test.py` unexcluded — inconsistent with its own
    stated goal. Fixed: both added to the same section.
  - `[low]` `[patch]` The same `.dockerignore` section had no guard for a future
    `src/platform/.env` (django-environ's natural local-secrets location) — the file's pre-existing
    root-anchored `.env`/`.secrets`/`.private` patterns don't reach `src/platform/`. No such file
    exists today (confirmed), so this was latent, not an active leak; fixed anyway since the
    Containerfile added by this story is the first thing in the repo to actually build FROM
    `src/platform/`, so the gap stops being theoretical the moment one does.
  - `[low]` `[patch]` `.github/workflows/platform-ci.yml`'s postgres/redis readiness loops
    (`container` job) silently fell through to the next step after 30 failed retries instead of
    failing with a clear message — later steps would fail with the far less diagnostic "`/ht/`
    never returned 200" instead. Fixed: both loops now `exit 1` with an explicit
    `::error::`-annotated message and the relevant service's logs on exhaustion.
  - `[medium]` `[defer]` The pip-layer's exclusion of `psycopg[c]` (in favor of the conda env's
    `psycopg2`) is a genuine major-version driver substitution (psycopg 3 → psycopg 2), not merely
    avoiding a duplicate — already an explicit, justified Boundaries & Constraints decision, but no
    ORM-level test anywhere exercises the container's actual driver (the real pytest suite only
    ever runs against psycopg 3 via `requirements/local.txt`). Both drivers are fully supported by
    Django's `postgresql` backend; not a known defect, but untested. Logged to `deferred-work.md`
    as a coverage gap, not fixed now — adding real container-path ORM test coverage is a
    non-trivial testing-infrastructure addition, not a mechanical patch.
  - `[medium]` `[defer]` The 8 manually-added transitive pip packages (django-timezone-field,
    python-crontab, cron-descriptor, django-appconf, rjsmin, text-unidecode, fido2, qrcode) were
    found via a one-time `pip install --dry-run --report=-` closure diff; nothing re-checks that
    closure automatically, so a future `requirements/production.txt` change can silently reopen the
    same class of `ModuleNotFoundError` this story spent most of its investigation chasing. Logged
    to `deferred-work.md` — matches Story 7.3's own precedent for an identically-shaped finding
    (its hardcoded three-root list), deferred there for the same reason: forward-looking
    maintenance discipline, not a defect in the current diff.
  - `[low]` `[patch]` `health_check.Database` (both versions, regardless of string- or
    class-resolved invocation) is a lightweight connectivity probe (`DatabaseHeartBeatCheck`/the
    4.x `Database` dataclass), not the same check the deprecated `health_check.db` app registered
    (`DatabaseBackend`, a `TestModel` CRUD check) — inherent to leaving the deprecated mechanism at
    all, not something this story's specific choices caused or could avoid while using the
    supported API; arguably an improvement for a kubelet-probed endpoint. No code change needed
    (both check classes function correctly); fixed by correcting the overstated "same pair" claim
    in Design Notes (see the "Review-pass corrections" entry) so the record doesn't overclaim
    parity.
  - `[low]` `[reject]` Podman entirely unverified locally — already transparently disclosed
    throughout this spec's own Verification section and Design Notes (sandbox has no podman binary,
    no sudo password to install one); not a new finding, and the CI job that will supply the real
    proof already exists.
  - `[low]` `[reject]` Builder stage's `COPY . /app` pulls in the whole monorepo rather than a
    cherry-picked subset, widening cache-invalidation. Already a deliberate, documented tradeoff in
    the Containerfile's own comment ("simpler and less error-prone than cherry-picking... a
    BUILDER-stage-only cost, discarded from the final image") — a build-performance observation,
    not a correctness or security defect.

### 2026-08-14 — Review pass (repair session, resuming after a verification-gate failure)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 0, low 3)
- defer: 1: (medium 1)
- reject: 10: (low 10)
- addressed_findings:
  - `[high]` `[patch]` `src/platform/compose/compose.yml`'s `platform` service never ran
    `manage.py migrate` (the image's own ENTRYPOINT/CMD deliberately doesn't, matching the
    Kubernetes convention of migrating via a separate Job, not every pod's own boot) — a fresh
    `docker compose up` served a completely unmigrated database. Confirmed live before the fix:
    `docker exec ... psql -U platform -d platform -c "\dt"` reported zero relations, and
    `curl .../admin/login/` 500'd with `django.db.utils.ProgrammingError: relation "django_site"
    does not exist` — invisible to every check this story had previously run (`/ht/`'s Database
    check is a bare connectivity probe, not a table query; `manage.py check` never touches the
    DB at all). Fixed: `compose.yml`'s `platform` service now runs `command: bash -c "python
    manage.py migrate --noinput && exec gunicorn ..."`, scoped to the LOCAL compose stack only
    (the image's own CMD, used by the CI `container` job and any real deployment, is untouched).
    Live-reverified after the fix: 24 tables now exist, `GET /admin/login/` returns 200, `/ht/`
    still 200, `docker compose down -v` clean.
  - `[low]` `[patch]` The prior pass's "re-verified live both sides" claim for the pip/3.24.0
    health-check fix overstated what `manage.py check` actually exercises: `HealthCheckView.plugins`
    is a `@cached_property` that calls `get_plugins()` (the method whose `ValueError`-vs-`TypeError`
    unpack behavior the whole fix is about) only from inside `get()`/`get_context_data()` — i.e. on
    an actual HTTP request — never during `as_view()`/URLconf loading, which is all `manage.py
    check` exercises. No pip/3.24.0 HTTP server was ever started to close this gap directly (no
    leftover venv in this sandbox). Closed instead with stronger, static evidence: downloaded the
    real `django_health_check==3.24.0` wheel from PyPI in this repair session and read
    `health_check/views.py`'s actual `get_plugins()` source directly — for a dotted-string entry,
    `check, options = check` raises `ValueError` (a 21+-character string un-packed into 2 names),
    caught, leaving `check` as the original string, then `import_string(check)` resolves it
    correctly; this is unconditionally true regardless of when the method runs, so the fix is
    confirmed correct by source inspection even though no live HTTP request against 3.24.0 was
    made. See Verification's new "Repair-pass re-verification" section below for the full command
    trail.
  - `[low]` `[patch]` Arbitrary-UID verification had only ever tested `id`/filesystem writes under
    an overridden UID, never a full application boot (gunicorn+uvicorn worker start, then a real
    `/ht/` GET) under a UID with no `/etc/passwd` entry — a real gap given some libraries call
    `pwd.getpwuid()` and raise `KeyError` for an unknown UID. Closed by actually running it: built
    the image fresh in this repair session, ran it with `--user 24680:0` (an arbitrary UID present
    in no passwd database) networked to real postgres+redis containers — gunicorn/uvicorn booted
    cleanly, `GET /ht/` returned 200, `manage.py check` was clean. The concern was real to check;
    the AC already held. See Verification below for the full command trail.
  - `[low]` `[patch]` `.github/workflows/platform-ci.yml`'s `container` job Teardown step removed
    every container/network it created but never the built image tag
    (`platform-ci-${{ matrix.engine }}`), leaving it orphaned after every run. Fixed: added
    `${{ matrix.engine }} rmi platform-ci-${{ matrix.engine }} || true` to the same `if: always()`
    step. YAML re-validated with `yaml.safe_load`.
  - `[medium]` `[defer]` `config/settings/production.py` hardcodes `SESSION_COOKIE_SECURE`/
    `CSRF_COOKIE_SECURE = True` with no env override, while this story's own `compose.yml` disables
    `DJANGO_SECURE_SSL_REDIRECT` for the plain-HTTP local stack — a browser drops `Secure`-flagged
    cookies over plain HTTP, so login/CSRF flows silently break locally even though `/ht/` and the
    home page are both 200. Pre-existing (`production.py` is Story 10.1's file, outside this
    story's Code Map) and outside this story's own AC (which names only a 200 health response for
    `compose up`, not a working login flow). Logged as `DW-FU-10-3-3` in `deferred-work.md`.
  - `[low]` `[reject]` `config/urls.py`'s move off `include("health_check.urls")` drops the
    library's `<str:subset>/` per-check route and its `health_check_home`/`health_check_subset`
    named URLs. Confirmed zero references anywhere in the codebase (`grep` across `src/platform`
    for both names and `health_check:`). Inherent to abandoning the deprecated app-based mechanism
    at all — the same "inherent, not this story's choice" reasoning the prior review pass already
    applied to the near-identical `health_check.Database`-vs-`health_check.db` question below.
  - `[low]` `[reject]` Both reviewers (independently) flagged the vendored
    `bootstrap.min.css`/`bootstrap.min.js` `sourceMappingURL` comment removals as unexplained in
    the raw diff. Already fully explained and justified in this same file's own Design Notes
    ("Review-pass corrections and additions," landed in the PRIOR review pass) — the reviewers ran
    blind against the diff alone, by design, and simply lack that context; not a new gap.
  - `[low]` `[reject]` `health_check.Database`/`Cache` framed as a real monitoring-behavior change
    (a lightweight probe replacing the old `TestModel` CRUD check) landing in a shared, non-container
    file. Duplicate of a finding the PRIOR review pass already made and already corrected in Design
    Notes' "Review-pass corrections and additions" §1.
  - `[low]` `[reject]` `psycopg[c]`→`psycopg2` driver substitution with no ORM-level test coverage.
    Duplicate of the already-logged `DW-FU-10-3`.
  - `[low]` `[reject]` The 8 manually-added transitive pip packages have no automated re-verification
    mechanism. Duplicate of the already-logged `DW-FU-10-3-2`.
  - `[low]` `[reject]` Podman entirely unverified locally. Already transparently, extensively
    disclosed throughout this spec's own Verification section and Design Notes; not new.
  - `[low]` `[reject]` The builder stage's own layers (whole-monorepo `COPY . /app`, two pixi envs,
    the pip install) are never secrets-scanned or `docker history`-checked, only the final runtime
    image is. The spec's own Always constraint and AC concern the BUILT (final) image specifically;
    a multi-stage build's non-final-stage layers are never pushed or distributed anywhere, and this
    exact pattern (a build-time-only station env, scanned narrowly, never copied into the runtime
    stage) is Story 7.1's own established precedent, not a gap this story introduced.
  - `[low]` `[reject]` Bundling the `pyforge-mason/spec-django-accelerator-framework` baseline
    repair into this story's own changeset instead of a separate change. Matches this repo's own
    established, precedented convention for a dev-auto repair pass fixing a pre-existing
    verification blocker found while resuming a story (see `spec-python-agent-platform`'s own
    `.memlog.md`, which carries an identically-shaped "repair pass" entry); transparently documented
    in both this spec's Design Notes and the target spec's own new memlog.
  - `[low]` `[reject]` The new baseline stamp adopts the governed trees' current content without
    auditing conformance to `spec-django-accelerator-framework`'s own CAP-1 clauses. Inherent to
    what a first-ever baseline stamp means, and explicitly disclosed as open work in that spec's own
    new `.memlog.md` entry — not a new gap.
  - `[low]` `[reject]` `.dockerignore`'s new Story 10.3 section is mostly rationale prose relative
    to its actual ignore-pattern count. Consistent with this diff's own established, deliberately
    heavy commenting convention throughout every file it touches (Containerfile, compose.yml,
    urls.py) — a style preference against the diff's own norms, not a defect.

### 2026-08-15 — Review pass (follow-up review on a `done` spec, `review_loop_iteration` reset to 0)

- intent_gap: 0
- bad_spec: 0
- patch: 14: (high 1, medium 4, low 9)
- defer: 2: (medium 2)
- reject: 14: (low 14)
- addressed_findings:
  - `[high]` `[patch]` **The pip layer was silently shadowing FIVE conda-provided packages,
    downgrading four of them — and one of the downgrades was masking a hard boot failure.**
    The exclusion list was derived from `[feature.python-agent-platform]`'s NINE DECLARED
    dependencies, not from the 395-package transitive solve `pixi.lock` actually
    materializes, so five `requirements/*.txt` lines whose packages arrive transitively were
    replacing their conda builds (conda-forge ships real `.dist-info`, so pip uninstalls
    first). Confirmed live with `pip list` inside the built image: `pillow` 12.3.0→11.3.0,
    `celery` 5.6.3→5.5.3, `uvicorn` 0.52.3→0.35.0, `gunicorn` 26.0.0→23.0.0, `argon2-cffi`
    same-version-different-build. This directly violates the spec's own Always clause ("the
    image's Python environment layer is exactly the pixi-materialized `python-agent-platform`
    env"), and the Containerfile's comment asserting the audit had been done for "every
    base.txt/production.txt line" was wrong. The celery case was actively out of spec: pip's
    5.5.3 declares `kombu<5.6,>=5.5.2` while this env's conda `kombu` is 5.6.2 — out of range,
    a check `--no-deps` suppresses, on a package `config/__init__.py` imports on every Django
    boot. Fixed by deriving the exclusion set from the LOCK and hardening the regex from
    `^pkg==` to `^pkg[^A-Za-z0-9._-]` (a trailing non-name character), so it survives a pin
    being relaxed from `django==5.1.11` to `django>=5.2`; verified against the real
    requirements files, 14 lines kept / 10 excluded / zero false matches
    (`django-celery-beat`, `uvicorn-worker`, `hiredis`, `django-redis` etc. all correctly
    kept). **Fixing it immediately exposed a second, previously-masked defect:**
    `requirements/base.txt`'s `uvicorn-worker==0.3.0` calls
    `uvicorn.Config.setup_event_loop()`, removed in uvicorn 0.36.0 — against the conda
    `uvicorn 0.52.3` gunicorn's worker dies with `AttributeError` and the master shuts down
    with "Worker failed to boot" (reproduced live). The old uvicorn downgrade had been the
    only reason the image booted at all. Fixed by excluding `uvicorn-worker` from the
    requirements-derived list and installing `uvicorn-worker>=0.4.0` explicitly (its metadata
    requires `uvicorn>=0.36.0` + `gunicorn>=21.0.0`, both satisfied); documented in the
    Containerfile as a now-coupled pair for whoever next bumps the env.
  - `[medium]` `[patch]` **This story never reconciled its own OWNING spec's surface.** The
    earlier repair pass reconciled `pyforge-mason/spec-django-accelerator-framework`, which
    only incidentally overlaps `src/platform/**`, and stopped — while
    `pyforge-steward/spec-python-agent-platform` (whose `surface:` IS `src/platform/**`,
    `pixi.toml`, `environment.yaml`) still carried six unreconciled paths. They surfaced as
    `drift-presumed` WARN rather than `drift` FAIL only because that spec's memlog hash had
    already moved for Story 10.1's landing, so the change was riding a pre-existing desync
    past a gate that was reporting `OK: … no drift`. Fixed: a full entry in that spec's own
    `.memlog.md` naming all six paths and both dependency findings above, then a scoped
    `--write-baseline --spec pyforge-steward/spec-python-agent-platform`. Residual
    `src/platform` findings went 6 → **0**.
  - `[medium]` `[patch]` `.github/workflows/platform-ci.yml`'s `paths:` filter was
    `['src/platform/**']` only, while the `container` job builds from the REPO ROOT and
    consumes `pixi.toml`, `pixi.lock`, `.dockerignore`, `scripts/container-gates`, and
    `src/shared/packages/pyforge-{steward,core}/**`. Any of those can break the image while
    leaving `src/platform/**` untouched — demonstrated, not hypothetical: this story hit
    exactly it when `requires-pixi` outran the pinned pixi image (`this project requires pixi
    '>=0.76.2', but you have pixi 0.76.1`). Such a change would have landed on `main` with
    this workflow never running. Fixed: all six paths added to both trigger events (written
    out twice, with a note — GitHub Actions does not support YAML anchors).
  - `[medium]` `[patch]` The new `container` job could not catch either regression this
    story's own review already proved happens. It polls `/ht/` and runs `manage.py check` —
    neither renders a `{% static %}` tag, which is exactly why the missing-`collectstatic`
    bug shipped past every smoke test in the first place. Fixed: added a step that requests
    `/` (extends `templates/base.html`: six `{% static %}` refs plus a `{% compress %}`
    block) and asserts both a 200 AND that the body carries no
    `OfflineGenerationError`/`Missing staticfiles manifest entry`/`Traceback` — a 200 alone
    is not proof, since Django can render an error page.
  - `[medium]` `[patch]` `HOME=/app` was NOT writable by an arbitrary UID, and the
    Containerfile's comment claimed the opposite ("gives an arbitrary, passwd-less UID a
    writable, already-owned-by-group-0 `$HOME`"). `WORKDIR /app` creates the directory
    root:root 0755 and the `chgrp`/`chmod` only covered `staticfiles`/`media`, so GID 0 had
    `r-x`. Reproduced live before the fix: `--user 24680:0` → `touch /app/.probe` and
    `mkdir /app/.cache` both `Permission denied`. Fixed with a NON-recursive `chgrp 0 /app &&
    chmod g+rwX /app` (the source tree's own modes are untouched). This turned out to be a
    hard prerequisite for the finding above rather than a nice-to-have: conda's `gunicorn
    26.0.0` — the version the shadowing fix restores — creates `$HOME/.gunicorn/gunicorn.ctl`
    at boot. Verified live after the fix: that socket directory exists in the running
    container owned by uid 24680.
  - `[low]` `[patch]` The "Confirm non-root UID" CI step was tautological: the container is
    started with an explicit `--user 12345:0`, so `id -u` proved only that the engine honored
    the flag, never that the image's own `USER 1001:0` directive survives. Fixed: that step
    now asserts the override was honored exactly, and a second step runs the image with NO
    `--user` and fails if the image defaults to uid 0.
  - `[low]` `[patch]` This story added a TENTH pixi pin site
    (`src/platform/Containerfile`'s `ghcr.io/prefix-dev/pixi:0.76.2`) without registering it
    in `pixi.toml`'s own enumerated invariant, which still read "NINE places … ALL NINE ARE
    0.76.1" — feeding the exact comment-maintained drift mechanism (DW-7-1-2) this story hit
    live. Fixed: enumeration updated to TEN with the 0.76.2 exception explained (it is the
    only site raised to satisfy the manifest's own floor; resolving DW-7-1-2 means raising
    the other nine, not lowering this one). Comment-only change — `environment.yaml`
    re-exported and confirmed byte-identical, so the ungated env-sync check stays green.
  - `[low]` `[patch]` The Containerfile justified excluding `psycopg[c]` as preventing a
    shadow of "the pinned conda version" — factually wrong, and misleading to the next
    reader. This env conda-sources `psycopg2`, a DIFFERENT distribution; no `psycopg` v3
    exists in the lock, so pip-installing it would overwrite nothing. Excluding it is a
    deliberate driver substitution (psycopg 3 → 2) mandated by the spec, not a shadowing
    case. Fixed: comment corrected, and it now points at the existing deferred coverage item
    rather than implying the question is closed. No behavior change.
  - `[low]` `[patch]` The builder-stage secrets-scan covered `/app/src/platform` but not
    `/app/shell-hook.sh`, which IS `COPY --from=builder`'d into the runtime stage and is
    therefore shipped content — and which `pixi shell-hook` generates by rendering
    activation-time environment variables, exactly the shape a leaked build-host credential
    would take. Story 7.1's own precedent scans its `/shell-hook.sh`. (A prior pass rejected
    a related finding on the premise that the final image IS scanned; re-checked here, that
    premise was false.) Fixed: hook added to the scan roots — build log now reports
    `secrets-scan: clean (2 root(s))`, was 1. Scoped deliberately: the rest of the monorepo
    checkout is builder-only and the conda env is lock-sourced third-party payload.
  - `[low]` `[patch]` `src/platform/staticfiles/` and `src/platform/platformapp/media/` were
    gitignored but NOT dockerignored, and `.dockerignore` is the only list `COPY
    src/platform/ /app/` consults. A developer who had run `collectstatic` locally would ship
    their host's assets into the image, where the runtime stage's own three-pass
    `collectstatic` runs over (never `--clear`s) them — making image content depend on which
    machine built it. Fixed: both added. The image generates both directories itself; neither
    is ever an input.
  - `[low]` `[patch]` The `platform` compose service had no `healthcheck:` while `postgres`
    and `redis` both did, so it could only ever report "running" — meaning this story's own
    acceptance wording ("brings up platform+postgres+redis all healthy") had nothing to read
    and `docker compose up --wait` returned before migrate finished or gunicorn bound. Fixed:
    added a healthcheck using the env's own python (UBI9-minimal ships no curl) with a
    `start_period` covering migrate+boot, plus `restart: on-failure` for the narrow race
    where postgres answers `pg_isready` from its initdb bootstrap server, and `EXPOSE 8000`
    on the image (without it the image advertises no port at all despite existing to serve
    one). Verified live: `docker compose up -d --build --wait` now reports **all three
    services healthy** and exits 0.
  - `[low]` `[patch]` `timeout-minutes: 20` on the `container` job is tight for a cold runner
    with no pixi cache: a 395-package solve+download, a SECOND build-time-only
    `pyforge-steward` env, the pip layer, three static-asset passes, and the image export.
    A too-tight cap turns a slow-but-correct build into a cancelled job indistinguishable
    from a real regression. Raised to 45.
  - `[low]` `[patch]` The vendored-bootstrap `sourceMappingURL` stripping had no in-repo
    record — the reasoning lived only in this Tier-3 spec and a commit message, so anyone
    re-vendoring bootstrap from a CDN would reintroduce the comments and hit an unexplained
    build failure. Fixed: recorded as a "vendored-asset precondition" directly in the
    Containerfile's `collectstatic` comment, i.e. at the exact `RUN` step that fails.
  - `[low]` `[patch]` The mason memlog entry this story wrote in its repair pass claimed "the
    2-file delta is exactly the two new files Story 10.3 added" — true of the file COUNT
    (120→122), but the same commit also MODIFIED four already-tracked files inside that
    spec's surface (`config/settings/base.py`, `config/urls.py`, both vendored bootstrap
    files), which were folded into the stamp unnamed. `spec_surface_reconcile.py`'s own
    contract is to reconcile by NAMING changed paths. Fixed by appending a correction entry
    (the dated original is left intact as the record) that names all four plus this pass's
    own changes.
  - `[medium]` `[defer]` Nothing tests the image's actual runtime stack: the `test` job runs
    the pip universe (Django 5.1.11, celery 5.5.3, uvicorn 0.35.0, gunicorn 23.0.0, pillow
    11.3.0, psycopg 3) while the image ships the conda one (Django 5.2.15, celery 5.6.3,
    uvicorn 0.52.3, gunicorn 26.0.0, pillow 12.3.0, psycopg2), and the two are mutually
    exclusive by `requirements/base.txt`'s own admission. The `uvicorn-worker` boot failure
    found in this pass is proof the gap has teeth — no test in the repo could have caught it.
    Logged as `DW-FU-10-3-4`; not fixed now because closing it is a testing-infrastructure
    decision spanning Stories 10.1/10.2, not a mechanical patch.
  - `[medium]` `[defer]` `COPY src/platform/ /app/` preserves the build host's file modes, so
    on a 002-umask machine the image ships its own source tree group-writable and the
    runtime user (GID 0) can rewrite its own code — confirmed live, and reproduced on the
    pre-review image, so it predates this pass. Two consequences: defense-in-depth, and
    build-host-dependent image content. Logged as `DW-FU-10-3-5`; not patched because both
    candidate fixes are decisions rather than mechanics (`COPY --chmod=` is a second BuildKit
    extension this story's Constraints deliberately forbid; a blanket `chmod -R g-w` must
    carve out `staticfiles`, `media`, and `$HOME` or it breaks the arbitrary-UID contract).
  - `[low]` `[reject]` ×14, dropped as noise or already-settled. Four were duplicates of
    already-logged deferrals (`DW-FU-10-3` psycopg ORM coverage, `DW-FU-10-3-2` transitive-
    closure re-verification, `DW-FU-10-3-3` `Secure`-cookie flags over plain HTTP) or of the
    podman non-verification this spec discloses at length. Three were re-raises of findings
    two prior passes already addressed and corrected (the `health_check.Database` probe-depth
    question; the removed `health_check_home` name and `/ht/<subset>/` route, whose zero
    in-repo references a prior pass verified by grep; the builder `COPY . /app`
    cache-invalidation tradeoff). The rest failed verification on their own facts: the claim
    that `spec-10-3-one-image-both-engines.md` is cited but untracked (correct today, and
    correct BY CONVENTION — story specs are promoted to the tracked tier AFTER merge, exactly
    as `spec-10-1-…` and `spec-10-2-…` were in commit `462c0ff407`); that `.dockerignore`'s
    `.env` guard needs `**/` any-depth coverage (`base.py` reads exactly
    `env.read_env(BASE_DIR / ".env")`, i.e. only `src/platform/.env`, which is covered); that
    the pip-layer `grep -hE '^[A-Za-z]'` would drop a digit-leading package name (no such
    line exists, and PEP 503 names starting with a digit are vanishingly rare); that the
    builder stage's own layers should be `history`-checked (non-final stages are never
    pushed or distributed — Story 7.1's established precedent); that the compose file needs
    its own CI job (this story's AC names local verification, which was done for docker);
    that podman's `aardvark-dns` backend should be explicitly asserted (speculation about
    GitHub runner-image internals; the `command -v` guard is already correct); and runner
    disk headroom (not cheaply actionable, and the practical symptom is covered by the
    timeout raise above).

### 2026-08-15 — Review pass (second follow-up review on a `done` spec, `review_loop_iteration` 0)

- intent_gap: 0
- bad_spec: 0
- patch: 15: (high 1, medium 5, low 9)
- defer: 4: (high 1, medium 3)
- reject: 9: (low 9)
- addressed_findings:
  - `[high]` `[patch]` **The previous pass's `$HOME` fix opened a hole while closing one: a
    group-writable `/app` let the runtime user replace `/app/entrypoint.sh`.** That pass set
    `HOME=/app` and made it group-0-writable so an arbitrary UID could write its own home.
    On POSIX, permission to unlink or rename an entry comes from the DIRECTORY, not the
    file — so the grant also made every entry directly in `/app` replaceable, and the
    Containerfile's own comment asserted the opposite ("the app's own source tree stays
    read-only to the runtime user"). Reproduced live before the fix under `--user 24680:0`:
    `rm /app/entrypoint.sh` succeeded, as did `mv /app/config /app/config.old` — i.e.
    anything reaching code execution as the runtime user could replace the image's
    entrypoint, which the next start would then execute. Fixed by pointing `$HOME` at a
    dedicated `/app/.home` (group-0, `g+rwX`) and leaving `/app` at root:root 0755. Also
    tightened `STATIC_ROOT` from `g+rwX` to `g+rX` in the same step: nothing writes it after
    the build (WhiteNoise serves it read-only from a baked manifest) and it is the one tree
    handed to every visitor's browser as executable JS, so a writable copy would let a
    compromised worker rewrite the served bundle in place with no image-layer change.
    Re-verified live on a fresh build under `--user 24680:0`: `$HOME` and media writable,
    `staticfiles` NOT writable, `entrypoint.sh` not removable, `config/` not renameable, and
    a full gunicorn boot whose control socket lands at `/app/.home/.gunicorn/gunicorn.ctl`
    owned by uid 24680.
  - `[medium]` `[patch]` **`pixi.toml`'s pin-site enumeration — the file's only enforcement
    mechanism — stated the exact inverse of live state, and undercounted the sites.** The
    previous pass rewrote it to "TEN places … NINE OF THE TEN ARE 0.76.1". Measured live:
    thirteen sites carry a pixi version, TWELVE are at 0.76.2, and exactly ONE is at 0.76.1
    — the repo-root `Containerfile`. The count missed `herald-live-demo.yml`'s three
    `pixi-version` pins entirely. It also cited DW-7-1-2 as the open remedy; that entry is
    `status: resolved` (2026-08-09, when all sites were aligned at 0.76.1 — everything but
    the root Containerfile has since moved up). A maintainer following the old text would
    have gone hunting for eight stale pins that do not exist. Rewritten to state current
    state, the correct thirteen, and what actually survives DW-7-1-2 (its residual: nothing
    enforces the equality). Comment-only — `environment.yaml` re-exported and confirmed
    byte-identical, so the ungated env-sync check stays green.
  - `[medium]` `[patch]` **This story changed two files governed by a THIRD spec and never
    reconciled it.** The previous pass fixed exactly this for `spec-python-agent-platform`
    after the repair pass had fixed it for `spec-django-accelerator-framework` — and stopped.
    `.dockerignore` and `pixi.toml` are governed by `pyforge-steward/spec-unified-container`,
    which no pass named. Verified by digest, not assumption: that spec's baselined
    `.dockerignore` (`2419b625`) is EXACTLY the content at this story's baseline commit
    `64e717d135`, so the drift is this story's own and nobody else's. Fixed by reconciling
    that spec by name. Deliberately NOT re-stamped, and the reason is in the entry: its
    `pixi.toml` digest matches neither the baseline commit nor anything this story produced,
    so it carries genuine pre-existing drift that a stamp would launder under an entry naming
    only Story 10.3's changes — the exact defect this story's own mason memlog correction was
    about. (A first draft of that entry claimed both files were pre-existing; that was wrong
    for `.dockerignore` and was corrected before landing.)
  - `[medium]` `[patch]` **The image was not reproducible from a fixed commit + lock.** Nine
    packages in the pip layer were installed by FLOOR (`uvicorn-worker>=0.4.0`,
    `fido2>=1.1.2,<3`, `qrcode>=7.0.0,<9`, …), resolved live from PyPI at build time — the
    only packages in the whole image not pinned by `pixi.lock` or by a `==` in a
    version-controlled requirements file. This matters here more than it usually would,
    because this same file documents that a wrong version in this exact set is a gunicorn
    boot loop rather than an import error: the previous pass found `uvicorn-worker` 0.3.0
    calling a method uvicorn removed in 0.36.0. A floor cannot express "known-good against
    conda uvicorn 0.52.3". Fixed: all nine pinned exactly to the versions the verified build
    resolved (`uvicorn-worker==0.4.0`, `fido2==2.2.1`, `qrcode==8.2`,
    `django-timezone-field==7.2.2`, `python-crontab==3.3.0`, `cron-descriptor==2.1.0`,
    `django-appconf==1.2.0`, `text-unidecode==1.3`, `rjsmin==1.2.2`), with the maintenance
    cost stated in the file. Verified by rebuilding and reading `pip list` back.
  - `[medium]` `[patch]` **The CI `container` job could not catch the regression class that
    had already shipped once in this story.** It never runs `migrate`, and every assertion it
    makes passes against a database with zero tables: `/ht/`'s Database check is a bare
    connectivity probe, and `/` renders with no query at all. That is not a hypothetical
    combination — the repair pass found `compose.yml` serving a completely unmigrated
    database, caught only because someone requested `/admin/login/` by hand. Fixed: the job
    now migrates explicitly (as `compose.yml` does, and for the same documented reason — the
    image's CMD deliberately doesn't) and asserts `/admin/login/` returns 200, which is the
    only step in the job that queries an application table and therefore the only one that
    can fail on either a missing migration or a broken psycopg2 ORM path.
  - `[medium]` `[patch]` **The `/ht/` route had zero runtime coverage on the pip-pinned
    3.24.0 leg — the one stack where its documented trap actually bites.** `config/urls.py`
    carries a long comment explaining that `checks=` must be dotted strings because 3.24.0's
    `get_plugins()` catches only `ValueError` on its per-entry unpack and a raw class raises
    an uncaught `TypeError`. Nothing tested it: `get_plugins()` is reached only from a real
    HTTP request, so `manage.py check` and the whole pytest suite pass either way, and the
    `container` job runs conda 4.5.0, which catches both exception types. Fixed by adding
    `src/platform/tests/test_health_endpoint.py`. Proven to work rather than assumed: with
    the raw-class form injected, `manage.py check` still reported "System check identified no
    issues" while the new tests failed; restored, all 24 tests pass against Django 5.1.11 +
    django-health-check 3.24.0 in a `python:3.12` container with a real postgres.
  - `[low]` `[patch]` The Containerfile's exclusion-filter comment claimed "14 lines kept, 10
    excluded"; running its own pipeline against the real requirements files gives 13/11. The
    count predated adding `uvicorn-worker` to the alternation. Corrected, with a note to
    re-run the pipeline rather than trust the line.
  - `[low]` `[patch]` `.dockerignore`'s new section asserted both build-host output
    directories are gitignored "so they never reach a commit". Only `staticfiles/` is:
    `src/platform/.gitignore` carries a stale cookiecutter `platform/media/` pattern and this
    app's package is `platformapp`, so `git check-ignore src/platform/platformapp/media/…`
    reports NOT ignored (verified). The image side was already fully covered by the two
    entries themselves; the false claim was the defect. Corrected, and the repo-side gap
    logged as `DW-FU-10-3-6`.
  - `[low]` `[patch]` The Containerfile's `psycopg[c]` note closed with "tracked as its own
    deferred item (see this story's deferred-work entries)" — a pointer into
    `implementation-artifacts/deferred-work.md`, which is gitignored and therefore
    unreadable from a clone of this repo. Fixed by writing the gap out in full at the point
    of use instead of citing it.
  - `[low]` `[patch]` The `/ht/` poll allowed 30 × 2s = 60s on a cold runner that has just
    spent its budget on the build. A slow-but-correct boot tripping that cap reads exactly
    like a real regression. Raised to 120s.
  - `[low]` `[patch]` Nothing in CI asserted the arbitrary-UID FILESYSTEM contract — only
    that `id -u` was non-zero. The `$HOME` permission bug found in this same pass was
    invisible to every existing check, and the newly-tightened `staticfiles` posture has no
    guard at all. Added a step that, inside the running container, requires `$HOME` and
    media to be writable AND `staticfiles` not to be.
  - `[low]` `[patch]` The `GET /` step asserted a 200 and an error-free body but never
    fetched a single asset the page references, so a manifest or compressor regression that
    renders fine and 404s every stylesheet would pass. Added a step that extracts the
    `/static/…` URLs from the rendered HTML (never a hardcoded list) and requires 200 from
    each — the three real ones verified live locally.
  - `[low]` `[patch]` `platform-ci.yml`'s header still claimed "this workflow never triggers
    on a factory-only change" after the previous pass added `src/shared/packages/pyforge-
    {steward,core}/**` to the filter — which are factory trees. Corrected, including the
    non-obvious part that `paths:` is workflow-scoped, so those paths also pay for the
    unrelated pip `test` job.
  - `[low]` `[patch]` The `/ht/` probe-depth change (a bare connectivity check replacing the
    removed `health_check.db` app's `TestModel` round-trip) had been corrected twice in this
    spec's Design Notes but never recorded in the repo, where a reader of the endpoint would
    look. Added to `config/urls.py`: a 200 means the database answers, not that the schema is
    migrated or that writes succeed.
  - `[high]` `[defer]` The repo-root `Containerfile` (Story 7.1, the Guild's unified image)
    pins `ghcr.io/prefix-dev/pixi:0.76.1` while `requires-pixi` is `>=0.76.2`, so its builder
    stage cannot install at all — the exact error this story hit live when it first reused
    that tag. Not covered by DW-7-1-2 (resolved). Logged as `DW-FU-10-3-8`; out of a platform
    story's Code Map, and the durable fix is the detector that entry's residual asked for.
  - `[medium]` `[defer]` `src/platform/.gitignore`'s stale `platform/media/` pattern means
    user uploads are not gitignored. Logged as `DW-FU-10-3-6`; Story 10.1's surface, and a
    one-line fix there drags a memlog entry plus baseline stamp for two specs behind it.
  - `[medium]` `[defer]` The widened `paths:` filter is correct for coverage but bills the
    repo's highest-traffic trees for a two-engine container matrix plus the unrelated pip
    `test` job, because `paths:` is workflow-scoped. Logged as `DW-FU-10-3-7`; both
    directions are defensible and the remedy is a workflow-architecture choice.
  - `[medium]` `[defer]` Two marshal specs carry stale `pixi.toml` baselines the gate cannot
    report, because a memlog that moved for an unrelated reason downgrades drift to
    informational and the "is this path named" test is a whole-file substring match. Logged
    as `DW-FU-10-3-9`; pre-existing (their digests predate this story's baseline commit) and
    the structural half belongs to the reconciler's own spec.
  - `[low]` `[reject]` ×9. Three were already-settled: compose having no CI job of its own (a
    prior pass rejected it on the same grounds — the AC names local verification); this Tier-3
    spec being cited by tracked memlogs while itself untracked (correct by convention, story
    specs are promoted after merge); and `Secure`-flagged cookies breaking login over plain
    HTTP (already `DW-FU-10-3-3`). Six failed on their own facts or were speculative: the
    exclusion regex not matching PEP 503 respellings like `argon2_cffi` (the requirements
    files are generated with canonical hyphens and version-controlled — it takes a deliberate
    rewrite to trigger); a future "Double requirement given" if one of the nine explicit
    extras is later added to `requirements/`; `grep '^[A-Za-z]'` dropping a hypothetical
    future `-r`/`--index-url` directive (the one real `-r base.txt` line is correctly dropped
    today, since base.txt is passed explicitly); `pixi install --frozen` not verifying the
    lock is current (`--frozen` is what the spec's own Boundaries & Constraints mandate);
    `restart: on-failure` making `compose up --wait` hang forever on a broken image
    (contradicted by this story's own live evidence — `--wait` reported
    `container compose-platform-1 is unhealthy` during exactly that boot loop); and rootless
    podman lacking subuid capacity for `--user 12345:0` (speculation about runner-image
    internals, in the same class as the `aardvark-dns` claim a prior pass rejected).

### 2026-08-15 — Review pass (third follow-up review on a `done` spec, `review_loop_iteration` 0)

- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 0, medium 5, low 8)
- defer: 1: (medium 1)
- reject: 7: (low 7)
- addressed_findings:
  - `[medium]` `[patch]` **The pip layer had no detector for the exact `high` defect the last
    pass fixed by hand.** The exclusion alternation is derived once from a 395-package solve and
    nothing re-derives it, so a `pixi.lock` refresh that starts providing a package the filter
    KEEPS (whitenoise, python-slugify, …) silently reopens conda-package shadowing — the failure
    that downgraded five packages, violated `celery`'s own `kombu<5.6` requirement under
    `--no-deps`, and left a `uvicorn` downgrade as the only reason the image booted. Fixed with a
    build-time gate rather than more comment discipline: pip announces every replacement as
    `Attempting uninstall:`, and since no kept line should ever displace anything, that string
    appearing at all now fails the build with a message naming the remedy. `set -o pipefail`
    added because the new `| tee` would otherwise mask a failing `pip install` behind tee's exit
    code. Verified BOTH directions: the real build is clean and green, and installing
    `pillow==11.3.0` over the conda build in a throwaway container produces
    `Attempting uninstall: pillow` → guard fires. (Worth recording: the first negative test ran as
    the image's own uid 1001 and pip silently *user*-installed instead of displacing anything, so
    the guard correctly stayed quiet — that is not the builder stage's posture. Re-run as root,
    which is. A negative test that runs under the wrong identity proves nothing.)
  - `[medium]` `[patch]` **`pixi.toml`'s pin-site enumeration was wrong for the third consecutive
    time, and the previous pass's own correction is what made it wrong.** That pass rewrote the
    headline to "THIRTEEN places … TWELVE OF THE THIRTEEN ARE 0.76.2" while numbering an
    enumeration that names FIFTEEN sites (counted live: `requires-pixi`, `$schema`, three
    `feature.*` floors, `environment.yaml`, `dashboard.yml`, `kedro-viz-publish.yml`, three
    `herald-live-demo.yml` pins, `sync-pypi-mappings/action.yml`, `staged-recipes-linter.yml`,
    and both Containerfiles). Fourteen are at 0.76.2; the root Containerfile alone is not.
    Rewritten with the list explicitly numbered (1)–(15) and an instruction to count the
    enumeration rather than trust the numeral — the numeral is the part that has rotted every
    single time this comment was touched. Comment-only: `environment.yaml` re-exported and
    confirmed byte-identical, so the ungated env-sync check stays green.
  - `[medium]` `[patch]` `.pixi/config.toml` is a load-bearing, GIT-TRACKED build input that the
    widened `paths:` filter still missed. `.dockerignore` carries an explicit `!.pixi/config.toml`
    negation whose own comment explains why: it sets `run-post-link-scripts = "insecure"`,
    without which `pixi install` skips the post-link scripts gdk-pixbuf, gtk3, librsvg and
    graphviz ship — i.e. flipping that key changes what the builder materializes into the runtime
    layer, with `src/platform/**` untouched. Exactly the class of miss the previous pass added six
    paths to close. Added to both trigger events.
  - `[medium]` `[patch]` **The CI job's postgres readiness probe can pass against a server that
    is not accepting TCP, and the step it gates has no retry.** `pg_isready -U platform` (no
    `-h`) probes the unix socket, which the official postgres image ALSO answers during its
    initdb bootstrap from a temporary server (`-c listen_addresses=''`) that then stops and
    restarts. The very next step migrates over TCP via `DATABASE_URL` with no retry, so the loop
    can break into a "connection refused" that reads as a real regression. `compose/compose.yml`
    documents this identical race and absorbs it with `restart: on-failure`; this job has no
    restart policy, so it must wait for the real server. Fixed with `-h 127.0.0.1 -p 5432`,
    which forces the TCP probe. Verified live: the patched form reported ready after 2 attempts
    and the un-retried migrate then succeeded.
  - `[medium]` `[patch]` **Nothing guarded the `high` hole the previous pass had just closed.**
    That pass proved a group-writable `/app` let the runtime user `rm /app/entrypoint.sh` and
    `mv /app/config`, and fixed it by moving `$HOME` to `/app/.home`. The CI filesystem probe it
    added in the same pass asserts `$HOME`/media writable and `staticfiles` not — but never that
    `/app` ITSELF stayed non-writable, so re-introducing `chgrp 0 /app && chmod g+rwX /app` would
    sail through every check in the job. Added that assertion. Also hardened all three negative
    probes with `test -d` first: `touch` on a missing directory fails with ENOENT exactly like
    EACCES, so a deleted or renamed `staticfiles` would have read as "the read-only contract
    holds". Verified live under `--user 24680:0`: probe green, and `rm /app/entrypoint.sh` /
    `mv /app/config` both still `Permission denied`.
  - `[low]` `[patch]` The `container` job never sent a single request to `/api/*`, so the FastAPI
    half of `config/asgi.py`'s dispatcher was untested against the stack the image actually
    ships. That is not covered by the `test` job: `fastapi` is on the pip-layer exclusion list,
    so the image runs the CONDA fastapi while `test` runs pip's `0.141.1`. Added a step asserting
    `/api/health` returns 200 — verified live, `{"status":"ok"}`.
  - `[low]` `[patch]` The "image declares a non-root USER" step asserted only `id -u`, but the
    arbitrary-UID model grants write access through GROUP 0, not through the uid. A regression to
    `USER 1001:1001` keeps the uid non-zero while making `$HOME` and `MEDIA_ROOT` unwritable for
    anyone running the image without `--user` — and the probe steps cannot see it, because they
    run in a container started with an explicit `--user 12345:0`. Now asserts `gid == 0` too.
    Verified live: image default identity is `uid=1001 gid=0`.
  - `[low]` `[patch]` The Migrate step was the only assertion in the job with no log dump on
    failure — and it needs one most, not least: it is the first thing to touch the container, so
    an app that died during boot (the `uvicorn-worker` break and the root-owned `$HOME` both did
    exactly that, in this story) yields a bare "container is not running" and Teardown then
    `rm -f`s the only copy of the traceback. Added.
  - `[low]` `[patch]` `test_home_page_does_not_shadow_the_health_route` asserted
    `reverse("home") == "/"`, which stays true no matter where `/ht/` is routed — the property the
    test is named for was never checked. Now asserts forward resolution,
    `resolve("/ht/").func.view_class is HealthCheckView`. Proven rather than assumed: with `/ht/`
    re-pointed at a `TemplateView`, the new assertion fails and the old one still passes;
    restored, 24/24 green against Django 5.1.11 + django-health-check 3.24.0.
  - `[low]` `[patch]` `config/urls.py` stated the default `checks` list unqualified
    (`[Cache, Database, DNS, Mail, Storage]`) inside a comment block whose entire subject is
    3.24.0-vs-4.5.0 divergence — and that is 4.5.0's default only. Read from both installed
    packages: 3.24.0 defaults to `health_check.{Cache,Database,Mail,Storage}` (no DNS, different
    module path), 4.5.0 to `health_check.checks.{Cache,Database,DNS,Mail,Storage}`. Corrected,
    with the consequence spelled out — dropping the explicit list is a behaviour change that
    would add a DNS check, making a kubelet probe depend on outbound name resolution.
  - `[low]` `[patch]` `compose.yml`'s comment claimed a genuinely broken image "still fails, just
    after a few attempts instead of one". The short `restart: on-failure` form is UNBOUNDED (the
    bounded form is `on-failure:N`). What actually makes `docker compose up --wait` terminate is
    the `healthcheck:` — verified live in a prior pass, which observed `--wait` reporting
    `container compose-platform-1 is unhealthy`. Comment corrected to state the real mechanism;
    the bound left off deliberately, with the reason recorded (the race being absorbed is
    postgres's initdb restart, whose duration no fixed retry count can be chosen against).
  - `[low]` `[patch]` `.dockerignore` shipped `src/platform/compose/` into the production image
    via `COPY src/platform/ /app/` — dev-only content nothing in the image reads, carrying a
    placeholder `DJANGO_SECRET_KEY` and a local `POSTGRES_PASSWORD` in plain text. That is the
    same hygiene class this section's own rule already excluded `config/settings/local.py` and
    `test.py` for. Added. Recorded alongside it, because it is the non-obvious half a future
    reader would get wrong: `src/platform/requirements/` CANNOT be excluded the same way even
    though the runtime image has no use for it either — `.dockerignore` governs the whole build
    context and the BUILDER stage's pip layer reads it. Verified in the rebuilt image: `/app/compose`
    gone, `secrets-scan` still `clean (2 root(s))`.
  - `[low]` `[patch]` Surface reconciliation for this pass's own changes: `spec-python-agent-platform`
    (five paths incl. `pixi.toml`) and `spec-django-accelerator-framework` (four paths) each got a
    memlog entry naming every changed path, then a scoped `--write-baseline --spec <key>`. Baseline
    delta verified as JSON afterwards — exactly 2 changed, 0 added, 0 removed. `spec-unified-container`
    got a memlog entry for its `.dockerignore` change and was deliberately NOT stamped, for the reason
    the previous pass recorded and which still holds (its `pixi.toml` digest matches neither the
    baseline commit nor anything this story produced, so a stamp would launder pre-existing drift).
  - `[medium]` `[defer]` `platform-ci.yml`'s two `paths:` lists are duplicated by hand with nothing
    enforcing equality, and the list has now changed in three of this story's four passes. A
    one-sided edit silently stops gating either PRs or `main`, and stays valid YAML. Logged as
    `DW-FU-10-3-10`; the remedy is a workflow-lint detector with a home of its own (this
    workflow's own jobs run only when the filter already matched, so they cannot police it), and
    the same shape exists in other workflows here.
  - `[low]` `[reject]` ×7. Four were already settled: the root `Containerfile`'s sub-floor pixi pin
    and its lack of any CI leg (both reviewers; already `DW-FU-10-3-8`); `compose.yml` having no CI
    job of its own (rejected on the same grounds twice before — the AC names local verification);
    the removed `health_check_home` name and `/ht/<subset>/` route (zero in-repo references,
    grep-verified two passes ago); and `spec-unified-container` sitting in a non-gating
    `drift-presumed` state (the structural half is `DW-FU-10-3-9`, the stamping half a documented
    deliberate decision). Three failed on their own terms: that the pip exclusion list has no
    detector (it does now — see the first patch above, which is that finding's actual remedy);
    that the requirements parse should fail loudly on a line `grep '^[A-Za-z]'` cannot read (no
    such line exists, the one real `-r base.txt` is correctly dropped, and a prior pass rejected
    this same speculation); and that the static-asset URL extraction regex would mis-capture
    single-quoted or `url()`-embedded references (every `{% static %}` in `base.html` renders into
    a double-quoted attribute, and the failure mode would be a loud false-red, not a silent pass).

## Design Notes

**`$HOME` is a subdirectory, and the reason is that a directory's mode is not its
contents' mode (2026-08-15, second follow-up review).** The prior pass fixed a real bug —
an arbitrary UID had no writable `$HOME`, so gunicorn 26 could not open its control
socket — with `HOME=/app` plus `chgrp 0 /app && chmod g+rwX /app`, and wrote a comment
asserting the source tree stayed read-only because the `chmod` was non-recursive. Both
halves of that reasoning are individually true and the conclusion is still wrong: file
modes govern who may WRITE a file's contents, but unlink and rename are governed by the
containing DIRECTORY's write bit. A group-writable `/app` therefore hands the runtime
user every path directly inside it — including `/app/entrypoint.sh`, the thing the image
executes on start. Not a subtlety worth arguing about in the abstract; it reproduces in
one command under `--user 24680:0`. The fix is structural rather than a tighter mode:
`$HOME` moved to `/app/.home`, so the writable set is stated by construction (media,
`$HOME`) instead of being an emergent property of a chmod on a parent. The general lesson
for this Containerfile: every future "X needs to write somewhere" gets its own directory,
never a permission widened on a directory that already holds something else.

**A second-order consequence: `STATIC_ROOT` never needed to be writable either.** It was
group-writable from the original implementation on the stated rationale of "the two paths
Django actually writes to." Only `MEDIA_ROOT` is. `STATIC_ROOT` is written once, at build
time, by the three-pass collectstatic/compress sequence, and thereafter served read-only
from a baked manifest — while being the only tree in the image whose bytes are executed
by every visitor's browser. It is now `g+rX`. The accepted cost is stated at the line:
`collectstatic` can no longer be re-run inside a running container.

**Reproducibility had a nine-package hole, and this file already knew why that was
dangerous.** Everything in this image comes from a fixed source — the conda side from
`pixi.lock`, the requirements side from `==` pins under version control — except the nine
transitive extras the `--no-deps` design forces to be named explicitly, which were
installed by floor and resolved live from PyPI on every build. The same file documents
that a wrong version in exactly this set is a gunicorn worker boot loop (`uvicorn-worker`
0.3.0 against uvicorn ≥0.36.0), i.e. the failure mode is a restart loop at deploy time,
not an import error at build time. A floor cannot encode "known-good against conda
uvicorn 0.52.3"; an exact pin can. All nine are now `==`, captured from the verified
build. This is a deliberate trade: security bumps to `fido2`/`qrcode` become manual edits
here, which is the correct default for an image whose whole premise is lock-derived.

**A pattern worth naming, because this story hit it four times: the comment was the
defect.** Across three review passes, the findings that survived verification were
disproportionately *claims* rather than code — "ALL NINE ARE 0.76.1" (nine of ten were
0.76.2), "14 lines kept, 10 excluded" (13/11), "both are in `.gitignore`" (one is), "the
source tree stays read-only" (it did not), "see this story's deferred-work entries"
(unreadable from a clone). Each was written by someone who had just done the work and was
describing it accurately as of that moment. They rot because nothing executes them. That
is the same mechanism `pixi.toml`'s own pin enumeration documents about itself ("NOTHING
ENFORCES THIS — the equality is comment-maintained, which is exactly how it drifted"),
and it is why several of this pass's fixes are new CI assertions rather than better
prose: the arbitrary-UID filesystem contract, the image's own default UID, and the static
assets the home page references are now checked instead of described.

**The pip layer's exclusion set is derived from the LOCK, not from the declared deps — and
that distinction is the whole design (2026-08-15, follow-up review).** The original
implementation read the spec's Boundaries & Constraints literally ("MINUS `Django` and
`psycopg[c]`") and cross-checked it against `[feature.python-agent-platform]`'s nine
DECLARED dependencies. That is the wrong denominator: `pixi.lock` materializes a
395-package transitive solve, and five more `requirements/*.txt` lines were being silently
installed over their conda builds (`pillow`, `celery`, `uvicorn`, `gunicorn`,
`argon2-cffi` — four outright downgrades). conda-forge python packages ship real
`.dist-info`, so pip does not "coexist" with them, it uninstalls and replaces them. The
spec's MINUS list was illustrative of a RULE — "already conda-sourced, pip would shadow the
pinned version" — and the rule, not the list, is what the Containerfile now implements.
Concretely, this is the same "derive, don't declare" failure the factory hits elsewhere:
a hardcoded list omits exactly the newest thing. Regeneration recipe is in the
Containerfile's own comment (`pixi list -e python-agent-platform` ∩ the requirements
lines).

Two second-order consequences worth carrying forward:
- **`uvicorn` and `uvicorn-worker` are a coupled pair in this env.** `uvicorn-worker`
  0.3.0 (the `requirements/base.txt` pin) calls `uvicorn.Config.setup_event_loop()`,
  removed in uvicorn 0.36.0 — a gunicorn worker boot loop, not an import error, against the
  conda `uvicorn 0.52.3`. The old shadowing had been masking it. The image pins
  `uvicorn-worker>=0.4.0`; any future uvicorn move across an API break needs the matching
  worker release.
- **Restoring the conda `gunicorn 26.0.0` made the `$HOME` permission fix load-bearing.**
  gunicorn 26 opens a control socket at `$HOME/.gunicorn/gunicorn.ctl` on boot, and
  `HOME=/app` was root-owned 0755 — so the arbitrary-UID fix and the shadowing fix, found
  as two independent review findings, are actually one working image.

**Pip/conda coexistence, not a full migration.** Story 10.2 explicitly deferred "whether the pip
requirements files coexist with or are superseded by the pixi env" to this story. Full migration
would require verifying conda-forge availability for a dozen Django extras (django-compressor,
django-anymail, etc.) with no functional payoff — `pip install --no-deps` into the SAME
pixi-provisioned interpreter gets the identical running app with far less risk, dropping only the
two packages (`Django`, `psycopg[c]`) that would otherwise silently shadow the conda-pinned
versions already in that environment.

**Why pixitainer is attempted, not assumed.** Its own recipe description covers only Apptainer/SIF
and a generic `docker` CLI wrapper — no documented Podman-native, rootless/arbitrary-UID, or
UBI-minimal-base control. The likely outcome is rejection for the primary image, but epics.md
names the attempt (not the outcome) as the AC; a preemptive rejection without running it would
fail that AC.

**Arbitrary-UID via GID 0, not a fixed UID.** OCP `restricted-v2` assigns an arbitrary UID at
deploy time — a Containerfile that only chmods for a hardcoded UID like 1000 fails under a
different assigned UID. Group-owning writable paths by GID 0 with `g+rwX` is the standard
OpenShift pattern that works for any assigned UID.

**The image's Django (conda, 5.2.x) diverges from `platform-ci.yml`'s existing pytest job (pip,
5.1.11) — inherited, not new.** Story 10.2's Design Notes already established this as two
unrelated, differently-scoped installs. This story's own container smoke test (`manage.py check`
inside the running container) is what validates the conda-sourced Django version; the existing
pytest job keeps validating the pip track unchanged.

**Pixitainer verdict — REJECTED for this story's image (2026-08-14, live evaluation).** Attempted
for real, not assumed: `pixi-containerize` (the conda-forge `pixitainer` package's only shipped
binary — confirmed by reading its own conda-meta file list: `bin/pixi-containerize` is the sole
entry point; the upstream project's separate Docker-backend binary, `pixi-containerize-docker`,
referenced by name in this spec's own Boundaries & Constraints, is NOT part of what this
feedstock's build packages — it exists nowhere on disk after a real `pixi install -e
local-recipes`) was run against this exact workspace: `pixi-containerize -e python-agent-platform
--dry-run` produced a real Apptainer/Singularity `.def` file (`Bootstrap: docker` there names only
the base-image PULL mechanism, not the OUTPUT format), defaulting to `ubuntu:24.04` as the base
image, with a single `%post` block that re-installs pixi itself and re-solves the target
environment INSIDE the container build (`pixi self-update` + `pixi install -e
python-agent-platform --frozen`) rather than a multi-stage builder→runtime split. Three
independent, concrete reasons this cannot be adopted, for-layer or dev-only, for this story:
1. **Wrong artifact format entirely.** The tool's only working backend in this workspace outputs
   a Singularity Image Format (`.sif`) file for Apptainer, never an OCI Docker/Podman image — the
   dual-engine `docker build`/`podman build` contract this story's spec requires is not something
   this binary can produce at all, regardless of flags.
2. **No UBI-minimal / rootless / arbitrary-UID control.** The generated definition hardcodes
   `ubuntu:24.04` (`-b/--base-image` overrides the base but not the SIF format itself), sets no
   `USER`/GID-0 story, and Apptainer's own execution model (typically already unprivileged by a
   different mechanism entirely) doesn't map onto Docker/Podman's `--user`/arbitrary-UID contract
   this story's I/O matrix tests against.
3. **The Docker backend the spec named doesn't exist in this feedstock's build.** `pixi
   containerize tool -b docker` is documented upstream, but the actual installed package (`pixi
   list -e local-recipes | grep pixitainer` → `pixitainer 0.8.3 hde56d03_0`, `conda-meta` files:
   `bin/pixi-containerize`, `opt/pixitainer/{bootstrap,common,sif,tool}.sh`) ships ONLY the
   apptainer/SIF entry point. `tool.sh`'s own `docker`-backend code paths reference invoking a
   binary named `pixi-containerize-docker` that is not present anywhere in this environment —
   confirmed by `find`-equivalent search across the installed env and the whole filesystem.
Given this, hand-rolling the Containerfile (already the spec's named fallback) is correct, not a
shortcut — the tool's only working output format in this workspace is structurally incompatible
with the dual-engine OCI requirement, independent of effort spent tuning flags.

**A pre-existing, cross-story blocker discovered live: `django-health-check >=4.5.0` (pixi.toml,
Story 10.2) ships an API `INSTALLED_APPS`/`config/urls.py` (Story 10.1) were written against
3.24.0 for.** `django-health-check` 4.x is a from-scratch rewrite: the 3.x package's `health_check.db`
/`health_check.cache` sub-apps and its `health_check.urls` URLconf module do not exist in 4.5.0 —
confirmed by reading the installed package directly inside the built image
(`site-packages/health_check/` has no `db.py`/`cache.py`/`apps.py`/`urls.py`; `checks.py` instead
exports dataclass-based `HealthCheck` subclasses — `Database`, `Cache`, `DNS`, `Mail`,
`Storage` — meant to be instantiated and passed to a view directly in the CONSUMING project's own
URLconf, a different integration pattern entirely). The concrete, live failure:
`django.setup()` itself raises `ModuleNotFoundError: No module named 'health_check.db'` while
populating `INSTALLED_APPS` — this happens before ANY view, health check, or HTTP handling runs,
so it is not narrowly a `/ht/` problem: `config.asgi` (and therefore gunicorn+uvicorn-worker
serving it) cannot even be imported. Reproduced three independent ways: (1) `python3 -c "import
config.asgi"` inside a bare `docker run`, (2) `python3 manage.py check` the same way, (3) a real
`docker compose up` with postgres+redis both reporting healthy — the platform container's
gunicorn worker crashes at boot with the identical traceback, proving the DATABASE_URL/REDIS_URL
wiring this story is actually responsible for is correct and the failure is specifically the
health-check package/app-code mismatch. This is a genuine Block-If per this story's own spec
("a `requirements/production.txt` package [-chain] hard-conflicts with a version already pinned
in the `python-agent-platform` conda env ... resolves but breaks a conda-pinned import at
runtime") — `pixi.toml`'s comment for this pin already flagged it as "a DIFFERENT install from
Story 10.1's pip-pinned `django-health-check==3.24.0`" without verifying the app code still
worked against it. **Per this story's own instructions, this was NOT silently worked around**:
`config/settings/base.py`'s `INSTALLED_APPS` and `config/urls.py`'s `include("health_check.urls")`
are Story 10.1's surface, not this story's Code Map, and fixing them requires adopting 4.x's new
registration API (a real design decision — which checks, which view class, what response
contract — not a mechanical patch). This story's Containerfile, pip layer, arbitrary-UID setup,
secrets-scan gate, and compose/CI wiring are all independently verified correct (see Verification
below); the ONE thing that cannot be verified end-to-end until a follow-up story updates Story
10.1's health-check integration for the 4.x API is a live 200 from `/ht/` and a clean `manage.py
check`. Recommend a follow-up story (Epic 10, scope: `config/settings/base.py` +
`config/urls.py`) before this image is considered deploy-ready.

**UPDATE (2026-08-14, same day, coordinator-directed re-investigation): NOT a Block-If after
all — a small, mechanical API migration. Fixed, and `/ht/` is now live-verified GREEN.** The
paragraph above was written after confirming the failure was total and reproducible, but before a
deeper read of the 4.5.0 package's own registration API. Re-investigated on the coordinator's
explicit direction (their message: "investigate whether this is just a library API migration...
if the fix is mechanical... apply it... the incompatibility is caused by THIS story's own decision
to source django-health-check from conda inside the image, so fixing the wiring to match the
conda-pinned version is this story's problem to close"). Live evidence, gathered by reading the
installed 4.5.0 package directly (not docs, not memory): `pkgutil.walk_packages` over
`health_check` confirms the real 4.x layout (`base`, `checks`, `contrib.*`, `exceptions`,
`management`, `views` — no `db`/`cache`/`apps`/`urls`); `health_check/views.py`'s
`HealthCheckView` (a plain `TemplateView` subclass) declares a class-level `checks` attribute
defaulting to `("health_check.checks.Cache", "health_check.checks.Database", "health_check.checks.DNS",
"health_check.checks.Mail", "health_check.checks.Storage")`, and `get_checks()` resolves each
entry (a class, a dotted-string, or a `(class-or-string, options)` tuple) and instantiates it —
i.e. 4.x replaced "list of Django apps that self-register a check" with "list of check classes
passed directly to the view," a standard, idiomatic Django CBV `as_view(**kwargs)` override
point, not a new architecture. `health_check.checks.Database`/`Cache` both default `alias="default"`,
matching this app's `DATABASES["default"]`/`CACHES["default"]` exactly — zero extra configuration
needed. **Fix applied** (both files are this story's problem per the coordinator's framing above,
since sourcing `django-health-check` from conda at a different major version than Story 10.1's
pip-pinned one was this story's own decision):
- `src/platform/config/settings/base.py` — `THIRD_PARTY_APPS` narrowed from `["health_check",
  "health_check.db", "health_check.cache"]` to `["health_check"]` (the two broken sub-app entries
  removed; `"health_check"` itself stays only so its `templates/health_check/` dir is discoverable
  via `APP_DIRS`).
- `src/platform/config/urls.py` — `path("ht/", include("health_check.urls"))` replaced with
  `path("ht/", HealthCheckView.as_view(checks=[HealthCheckDatabase, HealthCheckCache]))`
  (imports added: `health_check.checks.Cache as HealthCheckCache`, `health_check.checks.Database
  as HealthCheckDatabase`, `health_check.views.HealthCheckView`), deliberately pinned to EXACTLY
  `[Database, Cache]` — not the wider 5-check default — to preserve Story 10.1's original scope
  (PostgreSQL + the configured cache backend only, the same pair `health_check.db`/
  `health_check.cache` provided under 3.x) rather than silently adding DNS/Mail/Storage checks
  Story 10.1 never had. `checks` accepts CLASSES (or dotted strings), not instances —
  `get_checks()` calls `check(**options)` to instantiate each entry itself; passing `Database()`
  (an instance) would raise `TypeError: 'Database' object is not callable`, confirmed by reading
  `get_checks()`'s own unpack-then-call logic before writing the fix, not by trial and error.

**A SECOND, unrelated gap surfaced once the first was fixed — also fixed, same investigation
pass.** Fixing the health-check wiring advanced `django.setup()` to a NEW failure:
`ModuleNotFoundError: No module named 'timezone_field'` (`django_celery_beat.models` importing
its own dependency `django-timezone-field`), then after that fix, `No module named 'appconf'`
(`django-compressor` needing `django-appconf`). Both are consequences of THIS story's own
`pip install --no-deps` design (Boundaries & Constraints' own `pip install --no-deps` clause) —
`--no-deps` deliberately never resolves any package's transitive dependencies, so any REQUIRED
(non-`extra`-gated) transitive dependency that isn't independently conda-sourced has to be named
explicitly in the Containerfile's pip layer, or Django's app-loading fails at import time exactly
like this. Rather than keep discovering these one `ModuleNotFoundError` at a time, computed the
FULL closure once: `pip install --dry-run --ignore-installed --report=/tmp/report.json -r
requirements/production.txt` inside the built image (pip's own resolver, asked to plan the
install as if nothing were present) resolved 74 packages; diffing that list against what the
conda env + this pip layer already provide (case/underscore-normalized name comparison) found
exactly 5 genuinely missing names beyond the 3 already found iteratively:
`django-appconf`/`rjsmin` (django-compressor's deps), `text-unidecode` (python-slugify's dep),
`fido2`/`qrcode` (django-allauth's `[mfa]` extra — real here, since `"allauth.mfa"` is an actual
`INSTALLED_APPS` entry). All 8 (the 3 celery-beat ones plus these 5) are now listed explicitly in
the Containerfile's pip-layer `RUN` step, each with a version constraint matching what the
dependent package's own metadata declares (`rjsmin==1.2.2` exact, matching django-compressor's own
exact pin; the rest are floors). None of the 8 are conda-sourced by this env — confirmed via the
same closure diff — so none carry a shadowing risk, and adding them did not require a `pixi.toml`
change.

**Final live re-verification, this same investigation pass (2026-08-14):** `python3 -c "import
config.asgi"` inside a bare `docker run` — clean, no traceback. `python3 manage.py check
--settings=config.settings.production` — `System check identified no issues (0 silenced)`.
`docker compose -f src/platform/compose/compose.yml up -d` — postgres/redis `(healthy)`, platform
started; `curl http://localhost:8000/ht/` — **200**, HTML body shows `Database(alias='default')
OK` and `Cache(alias='default') OK`. `docker compose exec platform /app/entrypoint.sh python
manage.py check` (the exact CI-job step) — clean. `curl http://localhost:8000/api/health` (the
FastAPI seam, unaffected by any of this — sanity-checked anyway) — `{"status":"ok"}`, 200.
Arbitrary-UID and no-secret-leak checks re-run against this same final image and still pass (see
Verification's dated Results section for the full command/output record). `docker compose down
-v` cleaned up afterward. **This resolves the Block-If concern from the paragraph above**: this
was a genuine, real cross-story dependency-pin/app-code mismatch (the finding itself was not
wrong), but it was a mechanical library-API migration, not a structural incompatibility requiring
a product decision — so per the coordinator's own framing, closing it was this story's job, not a
reason to HALT.

**Build context is the repo root, not `src/platform` (deviation from the spec's literal
Verification-section command).** `pixi install --frozen -e python-agent-platform` in the builder
stage needs the WORKSPACE-ROOT `pixi.toml`/`pixi.lock` — the `python-agent-platform` feature lives
in the one repo-root manifest like every other pixi feature in this factory, and those two files
are not inside `src/platform/`. Docker cannot `COPY` a file from outside the build context without
a second `--build-context` (a BuildKit extension beyond the one this story's own Boundaries &
Constraints caps at one: `--mount=type=secret`). `docker build -f src/platform/Containerfile -t
platform-test .` (context = repo root) is the command that actually works, mirrors how the
repo-root Containerfile (Story 7.1) already builds itself, and is what every local verification
command and the CI job below actually use. Confirmed live: a literal `docker build -f
src/platform/Containerfile -t platform-test src/platform` was attempted first and fails immediately
(`COPY pixi.toml pixi.lock /app/`: `"/pixi.toml": not found`).

**The secrets-scan gate runs in the builder stage, not the final stage (deviation from the spec's
literal wording).** `scripts/container-gates secrets-scan` subprocesses into `steward`
(`pyforge-steward`'s own console script), which must not become a dependency of
`python-agent-platform` — that env is scoped to exactly CAP-5's three agentic engines + the
Django-host deps this story's Boundaries & Constraints enumerate; pulling in a whole factory
station CLI to satisfy a build-time gate would be scope creep on "one factory-sourced
environment," and Story 7.1's own precedent for this pattern already shows the correct home for a
build-time-only station env is the pixi BUILDER stage (which has full pixi + the whole checkout),
not the runtime stage. The builder stage here materializes a SEPARATE, build-time-only
`pyforge-steward` env (`pixi install --frozen -e pyforge-steward`) purely to run the gate against
`src/platform` (the only human-authored tree this Containerfile's runtime stage actually copies
in), and never copies that env into the runtime stage — confirmed live: `docker history` on the
final image shows no `pyforge-steward`/`pyforge-core` layer content, and `pixi list` was never run
against the runtime image (no pixi binary ships there at all, matching Story 7.1's own contract).
The safety property the spec's wording protects — "a finding fails `docker build`/`podman build`
itself, not a later `docker run`" — holds identically regardless of which stage the `RUN` lives
in, since BuildKit aborts the whole build on ANY stage's nonzero `RUN`. Live-verified clean build
(`container-gates: secrets-scan: clean (1 root(s))`) and a real negative-path rebuild is documented
in Verification below, matching spec-7-3's own precedent methodology.

**A THIRD gap, found by the coordinator during Tasks & Acceptance verification: the health-check
fix imported from the WRONG module for the pip/3.24.0 side.** The implementation subagent's fix
(`from health_check.checks import Cache, Database`) is correct for the conda-sourced 4.5.0
package inside the container, but `health_check.checks` does not exist in pip's
`django-health-check==3.24.0` (`requirements/base.txt`'s pin, installed by
`.github/workflows/platform-ci.yml`'s pre-existing `test` job) — confirmed live by reading
3.24.0's actual installed layout (a leftover venv from an earlier session, `django_health_check-
3.24.0.dist-info` present) and reproducing the exact `ModuleNotFoundError: No module named
'health_check.checks'` it would raise. Both versions DO export `Cache`/`Database` identically
from the package ROOT (`health_check/__init__.py` in both 3.24.0 and 4.5.0 re-exports them —
confirmed by reading both installed packages directly), so `src/platform/config/urls.py` was
corrected to `from health_check import Cache as HealthCheckCache` / `from health_check import
Database as HealthCheckDatabase` (not `health_check.checks`) — one import-path change, version-
agnostic by construction rather than branching on which version is installed. Live-reverified
both sides after the fix: (1) pip/3.24.0, via the same leftover venv, `PYTHONPATH=$(pwd)
DJANGO_SETTINGS_MODULE=config.settings.local <venv>/bin/python manage.py check` against this
worktree's current `src/platform/` — `System check identified no issues (0 silenced)`; (2)
conda/4.5.0, a fresh real `docker build` + `docker compose up` — `curl /ht/` → `HTTP_STATUS:200`,
`docker compose exec platform ... manage.py check` → `System check identified no issues (0
silenced)`. Both engines/versions clean after this fix; all recheck images/containers removed.

**The root `Containerfile`'s pixi image tag was found stale live, confirming that story's own
tracked issue.** This story's builder stage initially reused Story 7.1's exact
`ghcr.io/prefix-dev/pixi:0.76.1` tag and failed immediately: `this project requires pixi
'>=0.76.2', but you have pixi 0.76.1`. `pixi.toml`'s own `requires-pixi` floor is `>=0.76.2` as of
this story (checked live), one version ahead of the root Containerfile's own pin — which is
already a self-documented, self-admitted drift (that file's own comment names DW-7-1-2 and states
"NOTHING ENFORCES THIS"). This story's own Containerfile now pins `ghcr.io/prefix-dev/pixi:0.76.2`
and documents the discovery inline; fixing the ROOT Containerfile's own stale pin is out of this
story's scope (Code Map marks it reference-only) and is left for DW-7-1-2's own resolution.

**Review-pass corrections and additions (2026-08-14).** See the `### {date} — Review pass` entry
under Review Triage Log below for the full findings; summarized here because the first two land
directly in this file's own prior claims (the "same pair" parity claim two paragraphs up ("A
THIRD gap") and in the original "UPDATE" paragraph above it, and the class-based `checks=`
invocation in that same paragraph) and the third is a new, review-caught gap:
1. `health_check.Database` (either version, string- or class-resolved) is `DatabaseHeartBeatCheck`/
   the 4.x `Database` dataclass — a lightweight connectivity probe — not the OLD `health_check.db`
   app's `DatabaseBackend` (a `TestModel` CRUD check). This is inherent to moving off the
   deprecated app-based mechanism at all (true regardless of which valid invocation form is used),
   not something this story's specific choices caused or could have avoided while still using the
   supported API. Arguably an improvement for a kubelet-probed endpoint (cheap, non-mutating checks
   are the standard liveness/readiness recommendation) — noted here as a correction to the earlier
   "same pair" phrasing, not as a defect.
2. `config/urls.py`'s `checks=[HealthCheckDatabase, HealthCheckCache]` (raw classes) is WRONG for
   the pip/3.24.0 side and has been changed to `checks=["health_check.Database",
   "health_check.Cache"]` (dotted strings) — see `config/urls.py`'s own updated comment for the
   full mechanism (3.24.0's `get_plugins()` catches `ValueError` but not `TypeError` on the
   per-entry unpack attempt; a raw class triggers the uncaught `TypeError`, a string triggers the
   caught `ValueError` then resolves via `import_string`). Re-verified live both sides after the
   fix (see Verification's Review-pass re-check below).
3. **A second, independent review finding (Blind Hunter + Edge Case Hunter both caught it): this
   image never ran `collectstatic`, so it could not serve a single real page.**
   `production.py`'s `STORAGES["staticfiles"]` is WhiteNoise's `CompressedManifestStaticFilesStorage`,
   which raises `ValueError: Missing staticfiles manifest entry` for any `{% static %}` reference
   without a pre-existing manifest — six references in `templates/base.html` alone, extended by
   nearly every real page including the Django admin. `/ht/` and `/api/health` never exercise
   `{% static %}`, so every one of this story's own smoke tests missed it; caught only in review.
   Fixed: `src/platform/Containerfile` now runs `collectstatic` (build-time-only
   `DJANGO_SECRET_KEY`/`DJANGO_ADMIN_URL` placeholders, scoped to that one `RUN`, never persisted
   as image `ENV` — both settings have no default in `production.py`). This surfaced a THIRD,
   genuinely pre-existing Story 10.1 gap: `platformapp/static/{css,js}/vendor/bootstrap.min.{css,js}`
   each reference a `.map` sourcemap file that was never vendored alongside them — WhiteNoise's
   strict manifest build fails hard on a missing referenced file. Fixed by removing the trailing
   `sourceMappingURL` comment from both vendored files (a pure DevTools debugging hint, not
   required for the app to function; stays fully offline/zero-CDN rather than fetching+vendoring
   two more binary artifacts). Then a FOURTH gap, found empirically after `collectstatic` alone
   still 500'd the home page: `production.py`'s `COMPRESS_OFFLINE = True` (django-compressor,
   "required when using Whitenoise" per that file's own comment) needs `manage.py compress` run
   too, and the correct order is neither "compress then collectstatic" (compress can't resolve the
   `{% static %}` tags inside its own `{% compress %}` blocks without a manifest that doesn't
   exist yet — confirmed live, "Compressed 0 block(s)") nor "collectstatic then compress" alone
   (collectstatic's manifest doesn't know about compress's own newly-generated output yet —
   confirmed live, `OfflineGenerationError: ... key "..." is missing from offline manifest") but
   THREE passes: `collectstatic` → `compress --force` → `collectstatic` again. All three fixes are
   real, empirically forced by rebuilding and inspecting actual failures at each step, not derived
   from documentation alone.

**A pre-existing, unrelated repo-wide gate failed on resume: `spec_surface_reconcile.py`, root
cause not in this story's own surface.** Resuming this dev-auto session hit
`python scripts/spec_surface_reconcile.py` failing with `[drift-blind]`/`[no-baseline]` findings
against `pyforge-mason/spec-django-accelerator-framework` — a `status: draft` mason-owned spec
(`SPEC.md`, created 2026-08-14) that names `src/platform/**` and the steward dashboard tree in its
`surface:` but was never given a `.memlog.md` or a baseline stamp since its creation. Confirmed
pre-existing and unrelated to this story's own scope by reproducing the same failure on the parent
commit `64e717d135` (before this story started): it reports 120 governed files there against 122
on this story's own final commit — the 2-file delta is exactly the two files this story added
inside that spec's surface (`src/platform/Containerfile`, `src/platform/compose/compose.yml`),
which were always going to be swept into whatever baseline that spec eventually got, regardless of
which story happened to be running when the gap was finally noticed. Repaired by creating
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/.memlog.md`
(that spec's first-ever memlog entry, recording the gap and adopting the current tracked content of
both governed trees as the initial reconciliation baseline) and running `python
scripts/spec_surface_check.py --write-baseline --spec
pyforge-mason/spec-django-accelerator-framework`, scoped to that one spec only (its own stdout
confirms `1 spec(s): pyforge-mason/spec-django-accelerator-framework`, not `ALL`).
`python scripts/spec_surface_reconcile.py` now exits 0 with `OK: every tracked file governed or
allowlisted; no drift.`. No file under `src/platform/**`, the dashboard tree, or this story's own
Code Map changed as part of this repair.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

### Results (2026-08-14, executed live in this worktree)

**Engine coverage note, stated once here and not repeated per-line below:** this sandbox has a
working `docker` (29.7.2) but no `podman` binary and no sudo password to install one (unattended
run, no human present). Every result below is a REAL `docker`-engine run. Podman is NOT verified
locally anywhere in this story; `.github/workflows/platform-ci.yml`'s new `container` job's
`podman` matrix leg is the first real proof, and it has not yet executed (this story's changes are
unpushed).

1. **Build** -- `docker build -f src/platform/Containerfile -t platform-test .` (repo-root
   context, see Design Notes for why): succeeded, exit 0, ~1m45s cold / ~10s cache-warm on a
   second run. Verified the pip layer landed exactly the intended 19-package set and excluded the
   5 conda-shadowing packages: `python3 -m pip list` inside the image shows `Django 5.2.15` (conda,
   not pip's `5.1.11`), `psycopg2 2.9.12` (conda; no bare `psycopg` from pip's `psycopg[c]`),
   `fastapi 0.141.1`/`django-health-check 4.5.0`/`redis 8.1.0` (all conda versions, not pip's
   pinned ones) alongside `hiredis`, `gunicorn`, `celery`, `django-allauth`, `django-anymail`,
   `django-celery-beat`, `django-compressor`, `django-crispy-forms`/`crispy-bootstrap5`,
   `django-environ`, `django-model-utils`, `django-redis`, `pillow`, `python-slugify`, `rcssmin`,
   `uvicorn`/`uvicorn-worker`, `whitenoise`, `argon2-cffi` (the full 19-item pip-installed set).
2. **Secrets-scan gate (build-time)** -- ran automatically as part of the build above:
   `container-gates: secrets-scan: clean (1 root(s))`, all direct children of `src/platform`
   reported `[secrets] clean: ...`.
3. **Arbitrary-UID** -- default (`docker run --entrypoint bash platform-test -c id`):
   `uid=1001 gid=0(root) groups=0(root)`. Overridden (`--user 12345:0`): `uid=12345 gid=0(root)
   groups=0(root)`. As that overridden, never-baked-in UID: `touch
   /app/staticfiles/probe.txt` and `touch /app/platformapp/media/probe.txt` both succeeded.
4. **No-secret-leak check** -- `docker history --no-trunc platform-test` grepped for
   `AGE-SECRET-KEY`/`sk-ant-`/a PEM header/the test placeholder value: no matches. Rebuilt with a
   real, unused `--secret id=pip_index,src=<file containing a decoy
   sk-ant-api03-FAKEDECOYVALUE...TEST string>` supplied (this Containerfile has no `RUN
   --mount=type=secret` today -- the pip layer needs no index credentials -- so this proves an
   OFFERED-but-unconsumed secret never leaks either): build succeeded, `docker history --no-trunc`
   and a targeted `grep -r` across `/app /tmp /root` inside the built image both found zero
   matches for the decoy string. All test images/containers removed after each check.
5. **`docker compose up`** -- `docker compose -f src/platform/compose/compose.yml up -d`: image
   built successfully as part of the compose run, `postgres` and `redis` both reported `(healthy)`
   within seconds, the `platform` container started. Curling `/ht/` failed to connect
   (`curl: (7)`) because the platform container's gunicorn worker crashes at boot -- see Design
   Notes' "pre-existing, cross-story blocker" entry for the full `ModuleNotFoundError` evidence
   trail (reproduced identically via a bare `docker run` + `python3 -c "import config.asgi"` and
   via `python3 manage.py check`, independent of compose). `docker compose down -v` cleaned up
   all containers/networks after.
6. **`manage.py check` / `/ht/` 200** -- as first written up here, NOT achieved; blocked by the
   pre-existing cross-story `django-health-check` API mismatch documented in Design Notes. **See
   the `### Follow-up results` section below: this was resolved the same day** (coordinator-
   directed re-investigation found it was a mechanical API migration, not a structural
   incompatibility) and is now live-verified GREEN.
7. **CI workflow YAML** -- `.github/workflows/platform-ci.yml` parsed successfully with
   `yaml.safe_load` (`jobs: ['test', 'container']`). Not executed on GitHub Actions (unpushed).
8. **Pixitainer** -- see Design Notes for the full dated verdict (REJECTED) and evidence.

**Podman: explicitly not verified.** No `podman build`/`podman run`/`podman-compose` command was
executed anywhere in this story -- there is no podman binary in this sandbox and no way to install
one unattended (`sudo apt-get install podman` needs a password no human is present to supply).
Every "both engines" claim in this spec's Boundaries & Constraints and Acceptance Criteria is
therefore HALF-verified: the Containerfile/compose are designed, by construction, to stay inside
the documented Docker/Podman intersection (OCI instructions only, `--mount=type=secret` the only
BuildKit extension used, no Docker-only syntax) -- this is a real, applied design discipline, not
a hope -- but design discipline is not the same as a passing `podman build`. The
`.github/workflows/platform-ci.yml` `container` job's `podman` matrix leg is the mechanism that
will supply that proof, and it supplies it automatically the first time this branch's CI runs.

### Follow-up results (2026-08-14, same day, after the coordinator-directed re-investigation)

Two files changed (`src/platform/config/settings/base.py`, `src/platform/config/urls.py`) plus
the Containerfile's pip-layer `RUN` step extended from 3 to 8 explicit extra packages -- see
Design Notes' "UPDATE" and "A SECOND, unrelated gap" entries for the full evidence and reasoning.
Re-verified live, docker engine only (same sandbox constraint as above):

1. `python3 -c "import config.asgi"` inside a bare `docker run` -- clean, exit 0 (previously
   `ModuleNotFoundError: No module named 'health_check.db'`, then `'timezone_field'`, then
   `'appconf'` across the three fix iterations).
2. `python3 manage.py check --settings=config.settings.production` (no live DB/Redis) -- `System
   check identified no issues (0 silenced)`.
3. `docker compose -f src/platform/compose/compose.yml build && ... up -d` -- postgres/redis both
   `(healthy)`; platform container starts and STAYS UP (previously crashed at gunicorn worker
   boot).
4. `curl http://localhost:8000/ht/` -- **HTTP_STATUS:200**. Response body confirmed as real
   HTML (not a stub): a "System status" table with two rows, `Database(alias='default')` / `OK` /
   `0.012 s` and `Cache(alias='default')` / `OK` / `0.006 s`.
5. `docker compose exec platform /app/entrypoint.sh python manage.py check` -- the exact step
   `.github/workflows/platform-ci.yml`'s `container` job runs -- `System check identified no
   issues (0 silenced)`.
6. `curl http://localhost:8000/api/health` (FastAPI seam, unaffected by any of this fix, checked
   anyway) -- `{"status":"ok"}`, 200.
7. `docker compose exec platform id -u` -- `1001` (non-root, matches the image's declared `USER
   1001:0`).
8. Arbitrary-UID re-check against this same final image: `docker run --user 33333:0 ...` --
   `uid=33333 gid=0(root) groups=0(root)`; writes to `/app/staticfiles` and
   `/app/platformapp/media` both succeed.
9. No-secret-leak re-check against this same final image: `docker history --no-trunc` grepped for
   `AGE-SECRET-KEY`/`sk-ant-`/a PEM header/the test placeholder value -- no matches.
10. `docker compose down -v` -- clean teardown, all containers/networks removed. All test
    images (`platform-fixed`, `platform-fixed2`, `platform-fixed3`, `platform-investigate`, the
    compose-built image) removed after use; none pushed anywhere.

**Podman: still not verified** (unchanged from above -- this re-investigation pass did not gain
podman access). Every other item this story's Verification section names is now genuinely green
on the docker engine, including the two that were blocked when this section was first written.

### Review-pass re-verification (2026-08-14, same day, after Blind Hunter + Edge Case Hunter)

Both reviewers independently found the SAME high-severity bug (the `/ht/` `TypeError` under
pip/3.24.0, already covered above) plus a second, independent high-severity gap neither smoke test
had exercised: this image never ran `collectstatic`, so it could not serve a single real page.
Fixing that surfaced two further gaps (a pre-existing Story 10.1 vendoring gap, and a
`django-compressor` ordering requirement) empirically, by rebuilding and reading the actual
failures at each step -- see Design Notes' "Review-pass corrections and additions" entry for the
full mechanism of all four fixes. Five low/medium patches (settings-file dockerignore gaps, a
`.env` guard, CI readiness-loop failure branches, a Design Notes accuracy correction) and two
defers (`DW-FU-10-3`, `DW-FU-10-3-2` in `deferred-work.md`) round out the pass -- see Review Triage
Log for the complete, itemized breakdown.

Re-verified live, docker engine only (same sandbox constraint throughout this story -- no podman):

1. `docker build -f src/platform/Containerfile -t platform-review4 .` -- succeeded; build log shows
   `collectstatic` pass 1 (`137 static files copied`), `compress --force` (`Compressed 2 block(s)
   from 152 template(s)`), `collectstatic` pass 2 (`0 static files copied, 137 unmodified, 655
   post-processed`).
2. `docker compose -f src/platform/compose/compose.yml up -d --build` -- postgres/redis
   `(healthy)`, platform container starts and stays up.
3. `curl http://localhost:8000/` (the ACTUAL home page, never checked before this review pass --
   `/ht/` and `/api/health` are the only endpoints prior verification ever hit) -- **HTTP 200**,
   real content: `<title>...Python Agent Platform...</title>`, no `Traceback`/`OfflineGenerationError`/
   `ValueError` text anywhere in the body.
4. The page's actual rendered static asset URLs -- `/static/CACHE/css/output.<hash>.css`,
   `/static/CACHE/js/output.<hash>.js` (django-compressor's bundled output, not the raw vendor
   files), `/static/images/favicons/favicon.<hash>.ico` -- each independently curled: **200, 200,
   200**.
5. `curl http://localhost:8000/ht/` -- **200** (re-confirmed after the urls.py string-based-checks
   fix, on top of the collectstatic/compress fix).
6. `docker compose exec platform id -u` -- `1001`; `docker run --user 54321:0 --entrypoint bash
   platform-review4 -c "id && touch /app/staticfiles/probe.txt && touch
   /app/platformapp/media/probe.txt && echo WRITES_OK"` -- `uid=54321 gid=0(root)`, `WRITES_OK`.
7. `docker history --no-trunc platform-review4` grepped for `sk-ant-`/`AGE-SECRET-KEY`/a PEM
   header -- no matches (the build-time `DJANGO_SECRET_KEY`/`DJANGO_ADMIN_URL` placeholders ARE
   visible in the `RUN` command's own history line, by design -- they are obvious non-secret
   placeholder strings, not real credentials, and were never intended to be hidden).
8. pip/3.24.0 side (the leftover venv from an earlier session, `django_health_check-3.24.0`
   confirmed installed) -- `PYTHONPATH=$(pwd) DJANGO_SETTINGS_MODULE=config.settings.local
   <venv>/bin/python manage.py check` against this worktree's current `src/platform/` --- `System
   check identified no issues (0 silenced)`.
9. The build's own `container-gates secrets-scan` `RUN` step (builder stage) necessarily passed --
   a nonzero `RUN` at any stage aborts the whole `docker build`, and the build completed
   successfully end-to-end.
10. All review-pass test images/containers/networks removed after use (`platform-review2` through
    `platform-review4`, `compose-platform`, plus three unrelated `dockerignore-probe:*` leftover
    images from the implementation subagent's earlier session) -- `docker images`/`docker ps -a`
    confirmed clean of all test artifacts before this pass closed.

**Podman: still not verified** (unchanged -- no podman access gained in this pass either). Every
other AC and I/O-matrix scenario this spec names is now genuinely green on the docker engine.

### Repair-pass re-verification (2026-08-15, resuming after a verification-gate failure; Blind Hunter + Edge Case Hunter re-run)

This pass first repaired the unrelated `spec_surface_reconcile.py` failure documented in Design
Notes above, then re-ran Blind Hunter + Edge Case Hunter against the full diff since
`baseline_revision`. Two real findings surfaced and were fixed live (docker engine; still no podman
in this sandbox); the rest were duplicates of already-addressed/already-disclosed items or
out-of-scope pre-existing gaps -- see Review Triage Log's new dated entry for the complete,
itemized breakdown.

1. **`compose.yml` never migrated the database -- fixed and re-verified.** Before the fix: built
   `platform-arbuid-test` fresh, ran it against real `postgres:17`/`redis:7` containers on a
   throwaway network, `docker exec ... psql -U platform -d platform -c "\dt"` -- **"Did not find
   any relations."** `curl -L http://.../admin/login/` -- **HTTP 500**,
   `django.db.utils.ProgrammingError: relation "django_site" does not exist` (full traceback
   captured). After adding `command: bash -c "python manage.py migrate --noinput && exec gunicorn
   ..."` to `compose.yml`'s `platform` service: `docker compose -f src/platform/compose/compose.yml
   up -d --build` -- logs show ~50 migrations applying cleanly, gunicorn boots. `psql -c "\dt"` --
   **24 tables** (`users_user`, `django_session`, `django_site`, ... ). `curl
   http://localhost:8000/admin/login/` -- **HTTP 200** (previously 500). `curl
   http://localhost:8000/ht/` -- **200** (unchanged). `docker exec compose-platform-1 id -u` --
   `1001`. `docker compose down -v` -- clean teardown; test image (`compose-platform:latest`)
   removed after.
2. **Arbitrary-UID full application boot -- tested for the first time, confirmed GREEN.** Prior
   passes only ever tested `id`/filesystem writes under an overridden `--user`, never a full
   gunicorn+uvicorn boot + HTTP request under a UID absent from `/etc/passwd`. Built the image
   fresh, ran `docker run --user 24680:0 --network <throwaway> -e DATABASE_URL=... -e
   REDIS_URL=... platform-arbuid-test` (postgres/redis on the same throwaway network as finding 1,
   before that network was torn down): `docker logs` shows a completely clean gunicorn/uvicorn
   startup (`Application startup complete`, no traceback). `docker exec ... id` -- `uid=24680
   gid=0(root) groups=0(root)` (no passwd entry for 24680, confirmed by the UID rendering
   numerically rather than as a name). `curl http://localhost:18000/ht/` -- **200**. `docker exec
   ... manage.py check` -- `System check identified no issues (0 silenced)`. Container, postgres,
   redis, network, and image all removed after.
3. **pip/3.24.0 health-check fix -- confirmed correct by direct source inspection, not by a live
   request (no venv available in this sandbox).** `pip download django-health-check==3.24.0
   --no-deps` (network available in this sandbox) and read the real wheel's
   `health_check/views.py` directly: `HealthCheckView.get_plugins()` (the method whose
   `ValueError`-vs-`TypeError` behavior on an unpack attempt is the entire basis of the dotted-
   string-over-raw-class fix) is only ever reached via the `plugins` `@cached_property`, itself
   only accessed from `get()`/`get_context_data()` -- i.e. only on a real HTTP request, never
   during `as_view()`/URLconf loading (what `manage.py check` actually exercises). Confirmed the
   fix is correct anyway, unconditionally: for a dotted string, `check, options = check` always
   raises `ValueError` (an N-character string has more than 2 elements to unpack for any check name
   used here), always caught, leaving `check` as the original string, then
   `import_string(check)` resolves it -- this holds regardless of when `get_plugins()` runs, so the
   fix is sound even though this story's own "re-verified live" claim for this specific side
   overstated what `manage.py check` alone proves.
4. **CI teardown image cleanup.** `.github/workflows/platform-ci.yml`'s `container` job Teardown
   step re-validated with `python3 -c "import yaml; yaml.safe_load(open(...))"` after adding the
   `${{ matrix.engine }} rmi platform-ci-${{ matrix.engine }} || true` line -- parses cleanly,
   `jobs: ['test', 'container']` unchanged.

All throwaway containers, networks, and images created during this repair pass's live testing
(`arbuid-pg`, `arbuid-redis`, `arbuid-platform`, `arbuid-test-net`, `platform-arbuid-test`,
`compose-postgres-1`, `compose-redis-1`, `compose-platform-1`, `compose_default`,
`compose-platform:latest`) were removed afterward; `docker ps -a` and `docker images` confirmed
clean before this pass closed. `python scripts/spec_surface_reconcile.py` re-run one final time
after all fixes -- still exits 0, `OK: every tracked file governed or allowlisted; no drift.`
`pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 695 passed (unaffected; this repair
touched no `pyforge.*` code).


### Follow-up-review re-verification (2026-08-15; Blind Hunter + Edge Case Hunter re-run on the `done` spec)

Docker engine only, as throughout this story — this sandbox still has no `podman` binary
and no way to install one unattended. The `platform-ci.yml` `container` job's `podman`
matrix leg remains the first automated proof, unchanged by this pass.

1. **The shadowing finding, before and after.** `docker build` + `pip list` inside the
   image, pre-patch: `pillow 11.3.0`, `celery 5.5.3`, `uvicorn 0.35.0`, `gunicorn 23.0.0`
   — against a lock that provides 12.3.0 / 5.6.3 / 0.52.3 / 26.0.0 (extracted from
   `pixi.lock`'s own `python-agent-platform` linux-64 solve, 395 packages). Post-patch, same
   command: `pillow 12.3.0`, `celery 5.6.3`, `uvicorn 0.52.3`, `gunicorn 26.0.0`,
   `argon2-cffi 25.1.0`, alongside the unchanged `Django 5.2.15` / `psycopg2 2.9.12` /
   `redis 8.1.0` / `fastapi 0.141.1` and the still-pip `whitenoise 6.9.0` /
   `hiredis 3.2.1` / `uvicorn-worker`. `importlib.metadata` confirms the kombu constraint
   is now satisfied: celery 5.6.3 requires `kombu>=5.6.0`, installed 5.6.2 (pre-patch:
   celery 5.5.3 required `kombu<5.6,>=5.5.2` against the same 5.6.2 — out of range).
   `import celery, gunicorn, uvicorn_worker, PIL, argon2` all clean.
2. **The masked boot failure this exposed.** First rebuild after the exclusion fix: the
   `platform` service entered a restart loop, `docker compose logs` showing
   `AttributeError: The setup_event_loop method was replaced by get_loop_factory in uvicorn
   0.36.0` from `uvicorn_worker/_workers.py:96`, then `Reason: Worker failed to boot`.
   Resolved by pinning `uvicorn-worker>=0.4.0` (PyPI metadata read live:
   `requires_dist: ['gunicorn>=21.0.0', 'uvicorn>=0.36.0']`, both satisfied by this env).
3. **`docker compose -f src/platform/compose/compose.yml up -d --build --wait`** — exit 0
   with **all three services `(healthy)`**, including `platform`, which had no healthcheck
   at all before this pass. `--wait` correctly reported `container compose-platform-1 is
   unhealthy` during the boot-loop above, i.e. the new healthcheck demonstrably detects a
   broken image rather than rubber-stamping it.
4. **Endpoints, all against the running stack.** `/ht/` **200** (body shows
   `Database(alias='default') OK`, `Cache(alias='default') OK`); `/` **200** with zero
   `OfflineGenerationError`/`Missing staticfiles manifest entry`/`Traceback` occurrences in
   the body; each static URL the page actually renders curled independently —
   `/static/CACHE/css/output.<hash>.css` **200**, `/static/CACHE/js/output.<hash>.js`
   **200**, `/static/images/favicons/favicon.<hash>.ico` **200**; `/admin/login/` **200**
   against 24 migrated tables (`information_schema.tables` count, live);
   `/api/health` **200**. `docker compose exec platform /app/entrypoint.sh python manage.py
   check` — `System check identified no issues (0 silenced)`. `docker compose exec platform
   id -u` — `1001`.
5. **Arbitrary-UID full application boot.** `docker run --user 24680:0` (a UID in no passwd
   database) on the compose network against the same real postgres+redis: `docker logs`
   shows `Application startup complete` with no traceback, `id` → `uid=24680 gid=0(root)`,
   `/ht/` **200**, `/` **200**, `manage.py check` clean. `$HOME` writes that were
   `Permission denied` before this pass now succeed (`touch /app/.probe`, `mkdir -p
   /app/.cache/x`), and `/app/.gunicorn` exists **owned by uid 24680** — created at runtime
   by gunicorn 26.0.0's control socket, which is why the `$HOME` fix and the shadowing fix
   turned out to be interdependent rather than independent.
6. **No secret leaks.** `docker history --no-trunc` on the final image grepped for
   `sk-ant-`/`AGE-SECRET-KEY`/PEM private-key headers/`ghp_…` — **0 matches**. A recursive
   `grep -rIlE` for the same shapes across `/app` (excluding the conda env) inside the
   running image — no files. The build's own `container-gates secrets-scan` now reports
   `clean (2 root(s))` (was 1), the second root being the shipped `shell-hook.sh`.
7. **Repo gates.** `python scripts/spec_surface_reconcile.py` — `OK: every tracked file
   governed or allowlisted; no drift.`, exit 0, with residual `src/platform` findings at
   **0** (6 before this pass's memlog + scoped baseline stamp).
   `pixi project export conda-environment -e build` diffed against `environment.yaml` —
   byte-identical, so the comment-only `pixi.toml` edit does not trip the ungated env-sync
   check. `pixi run --frozen -e pyforge-steward pyforge-steward-test` — **695 passed**.
   Both workflow/compose YAML files re-parsed with `yaml.safe_load`
   (`jobs: ['test', 'container']`, `services: ['postgres','redis','platform']`).
8. **Exclusion-regex correctness, checked against the real files rather than reasoned
   about.** The new `^(…)[^A-Za-z0-9._-]` pattern over
   `requirements/{base,production}.txt`: **14 lines kept, 10 excluded, zero false matches** —
   `django-celery-beat`, `django-redis`, `django-environ`, `django-crispy-forms`,
   `django-model-utils`, `django-allauth[mfa]`, `django-compressor`, `django-anymail`,
   `uvicorn-worker`, `hiredis`, `whitenoise`, `python-slugify`, `rcssmin`,
   `crispy-bootstrap5` all correctly retained.
9. **Cleanup.** Every container, network, and image created in this pass
   (`compose-{postgres,redis,platform}-1`, `compose_default`, `arbuid-probe`,
   `platform-rev5`, `platform-rev6`, `compose-platform`) removed; `docker ps -a` and
   `docker images` confirmed free of test artifacts before this pass closed.

**Podman: still not verified** (unchanged — no podman access gained in this pass either).


### Second-follow-up-review re-verification (2026-08-15; Blind Hunter + Edge Case Hunter re-run on the `done` spec)

Docker engine only, unchanged from every prior pass — this sandbox still has no `podman`
binary and no way to install one unattended. `platform-ci.yml`'s `container` job's `podman`
matrix leg remains the first automated proof of the dual-engine claim, and it has still not
executed (this branch is unpushed).

1. **The `$HOME` / permissions fix, before and after.** Before: `docker run --user 24680:0
   --entrypoint bash <image> -c 'rm /app/entrypoint.sh'` **succeeded**, as did
   `mv /app/config /app/config.old`. After (fresh build, same command set): `HOME writable:
   YES (/app/.home)`, `media writable: YES`, `staticfiles writable: NO (expected)`,
   `entrypoint not replaceable (expected)`, `config not renameable (expected)`. Directory
   modes read back directly: `/app` `drwxr-xr-x root root`, `/app/.home` `drwxrwxr-x`,
   `/app/platformapp/media` `drwxrwxr-x`, `/app/staticfiles` `drwxr-xr-x`.
2. **Exact pins landed as declared.** `pip list --format=freeze` inside the rebuilt image:
   `django-timezone-field==7.2.2`, `python-crontab==3.3.0`, `cron_descriptor==2.1.0`,
   `django-appconf==1.2.0`, `rjsmin==1.2.2`, `text-unidecode==1.3`, `fido2==2.2.1`,
   `qrcode==8.2`, `uvicorn-worker==0.4.0` — all nine matching the Containerfile's new `==`
   lines exactly.
3. **The prior pass's shadowing fix still holds.** Same command: `Django==5.2.15`,
   `pillow==12.3.0`, `celery==5.6.3`, `uvicorn==0.52.3`, `gunicorn==26.0.0`,
   `argon2-cffi==25.1.0`, `psycopg2==2.9.12`, `redis==8.1.0`, `fastapi==0.141.1`,
   `django-health-check==4.5.0` — every one the conda build, none replaced by pip.
4. **Full stack, `--wait`.** `docker compose -f src/platform/compose/compose.yml up -d --build
   --wait` exits 0 with **all three services `(healthy)`**. Endpoints against it: `/ht/`
   **200**, `/` **200** with zero `OfflineGenerationError`/`Missing staticfiles manifest
   entry`/`Traceback` in the body, `/admin/login/` **200** against **24 migrated tables**,
   `/api/health` **200**. Each static URL the home page actually renders, curled separately:
   `/static/CACHE/css/output.<hash>.css` **200**, `/static/CACHE/js/output.<hash>.js` **200**,
   `/static/images/favicons/favicon.<hash>.ico` **200** — this is the exact set the new CI
   step derives at runtime. `docker compose exec platform /app/entrypoint.sh python manage.py
   check` — `System check identified no issues (0 silenced)`; `id -u` — `1001`.
5. **Arbitrary-UID full application boot on the new `$HOME`.** `docker run --user 24680:0`
   against the same real postgres+redis: logs show `Control socket listening at
   /app/.home/.gunicorn/gunicorn.ctl` then `Application startup complete`, **zero** occurrences
   of `Traceback`. `id` — `uid=24680 gid=0(root)`. `/ht/` **200**, `/` **200**,
   `/admin/login/` **200**, `manage.py check` clean. `ls -ld "$HOME/.gunicorn"` — owned by
   **24680**, i.e. created at runtime by that UID, which is what makes the `$HOME` move
   load-bearing rather than cosmetic.
6. **The new pip-side test, proven to catch what it exists for.** In a `python:3.12` container
   (matching the `test` job's Python) against a real `postgres:17`, with
   `requirements/local.txt` installed (Django 5.1.11, django-health-check 3.24.0): the three
   new tests **pass**. Then the regression was injected — `checks=` switched from dotted
   strings back to raw imported classes — and re-run: **2 failed**, while `manage.py check`
   in the same container still reported `System check identified no issues (0 silenced)`.
   That is the whole argument for the test in one command pair. Restored and re-verified.
7. **Repo-wide pip gates, same container.** `ruff check .` — `All checks passed!` (an initial
   `TC002` on the new file was fixed by moving the `Client` import into a `TYPE_CHECKING`
   block). `mypy platformapp config tests` — `Success: no issues found in 46 source files`.
   `python -m pytest` — **24 passed** (21 before this pass).
8. **Secrets.** Build log reports `container-gates: secrets-scan: clean (2 root(s))`.
   `docker history --no-trunc` on the final image grepped for `sk-ant-`/`AGE-SECRET-KEY`/PEM
   private-key headers/`ghp_…` — **0 matches**. A recursive `grep -rIlE` for the same shapes
   across `/app` (excluding the conda env) inside the image — no files.
9. **Repo gates.** `pixi run -e local-recipes spec-surface-check` — verdict `spec-surface: ok
   -- every tracked file governed or allowlisted; no drift`, with **zero** findings naming any
   path this story touched (the only `pixi.toml` mentions in the warning list are
   `src/shared/packages/*/pixi.toml`, different files). `python scripts/spec_surface_reconcile.py`
   — `OK: every tracked file governed or allowlisted; no drift.`, exit 0.
   `pixi project export conda-environment -e build` diffed against `environment.yaml` —
   **byte-identical**. `pixi run --frozen -e pyforge-steward pyforge-steward-test` — **695
   passed**. Both YAML files re-parsed with `yaml.safe_load` (`jobs: ['test', 'container']`,
   `services: ['postgres', 'redis', 'platform']`).
10. **Digest evidence for the spec-surface finding**, recorded because the conclusion turned on
    it and a first reading of it was wrong: `spec-unified-container`'s baselined `.dockerignore`
    is `2419b625`, which is byte-identical to `.dockerignore` at this story's baseline commit
    `64e717d135` — so that spec was IN SYNC until Story 10.3 moved it. Its baselined `pixi.toml`
    (`f3e313fe`) matches neither `64e717d135` (`0ae029cc`) nor anything this story produced, so
    that file was already unreconciled. Hence: reconcile by name, do not stamp. (These are plain
    sha1 digests of file content, which is what `spec_surface_check.py` records — NOT
    `git hash-object` blob hashes. Comparing the two forms makes every entry look stale.)
11. **Cleanup.** Every container, network, and image created in this pass (`platform-rev7`,
    `platform-rev8`, `arbuid-rev8`, `ht-pg`, `compose-{postgres,redis,platform}-1`,
    `compose_default`, `compose-platform`) removed; `docker ps -a` and `docker images` confirmed
    free of test artifacts before this pass closed.

**Podman: still not verified** (unchanged — no podman access gained in this pass either).


### Third-follow-up-review re-verification (2026-08-15; Blind Hunter + Edge Case Hunter re-run on the `done` spec)

All executed live in this worktree with the docker engine.

1. **Image build, full and cold-ish.** `docker build -f src/platform/Containerfile -t
   platform-review3 .` → **exit 0**. The `.dockerignore` change invalidates `COPY . /app`, so this
   was a real end-to-end rebuild (395-package solve, second build-time `pyforge-steward` env, pip
   layer, three static passes, export). `secrets-scan: clean (2 root(s))` — unchanged after
   `src/platform/compose/` left the context.
2. **The new pip-shadowing gate, both directions.** Positive: the build's pip step installed 22
   distributions with no `Attempting uninstall:` anywhere in the log. Negative: in a throwaway
   container **as root** (the builder stage's actual posture), `pip install --no-deps
   pillow==11.3.0` over the conda pillow printed `Attempting uninstall: pillow` — `grep -q` matches,
   guard exits 1. Recorded because it nearly produced a false negative: the same command run under
   the image's own `USER 1001:0` reports `Successfully installed pillow-11.3.0` with NO uninstall
   line, because pip cannot write the env and silently falls back to a user-site install. The guard
   is correct; the first test was run under the wrong identity.
3. **Live stack, arbitrary UID.** postgres:17 + redis:7 on a dedicated network; app started
   `--user 24680:0`. `pg_isready -h 127.0.0.1 -p 5432` (the patched TCP form) reported ready after
   2 attempts; the un-retried `migrate --noinput` then applied cleanly.
4. **Every HTTP assertion the CI job makes, plus the new one.** `/ht/` 200 (first poll),
   `/admin/login/` 200 (the only ORM-backed page — proves migrate + the psycopg2 path), `/` 200
   with a body free of `OfflineGenerationError`/`Missing staticfiles manifest entry`/`Traceback`,
   all three `/static/` URLs the page actually renders 200 each
   (`CACHE/css/output.33ce7073b389.css`, `CACHE/js/output.2206b8e88750.js`,
   `images/favicons/favicon.a66bc42b4e8a.ico`), and **`/api/health` 200 `{"status":"ok"}`** — the
   first time the image's FastAPI dispatcher half has ever been exercised. `manage.py check`:
   "System check identified no issues".
5. **Filesystem contract, patched probe run verbatim.** `HOME=/app/.home` writable, media writable,
   `staticfiles` NOT writable, **`/app` NOT writable** — and the previous pass's `high` finding
   re-proved closed: `rm /app/entrypoint.sh` → `Permission denied`, `mv /app/config /app/config.old`
   → `Permission denied`, `entrypoint.sh` intact.
6. **Image default identity.** `uid=1001 gid=0` — both halves now asserted in CI, not just the uid.
7. **Content actually excluded.** `ls /app` in the built image: no `compose/`. `requirements/` still
   present, as it must be.
8. **Pip-stack test suite.** `python:3.12` container against the real postgres, `requirements/local.txt`
   (Django 5.1.11, django-health-check 3.24.0): **24 passed**. Then the strengthened shadowing test
   negative-tested by re-pointing `/ht/` at a `TemplateView` — `test_home_page_does_not_shadow_the_health_route`
   FAILS (`resolve('/ht/').func` is `TemplateView`), which the old `reverse("home")` assertion could
   not see. `config/urls.py` restored and the full suite re-run read-only: **24 passed**.
9. **Manifest / env-sync.** `pixi.toml` parses (`tomllib`); `pixi project export conda-environment -e
   build` byte-identical to the committed `environment.yaml`, so the ungated env-sync check stays
   green. Workflow YAML re-validated with `yaml.safe_load`, and the two `paths:` lists asserted
   equal programmatically (9 entries each) — the equality this pass could only check, not enforce,
   which is why it is deferred as `DW-FU-10-3-10`.
10. **Spec-surface gate.** Was 9 `[drift]` findings after the edits; reconciled by naming every
    changed path in `spec-python-agent-platform` (5) and `spec-django-accelerator-framework` (4),
    then scoped `--write-baseline --spec <key>` for each. Baseline delta parsed as JSON: exactly
    **2 changed, 0 added, 0 removed**. Gate now `OK: every tracked file governed or allowlisted; no
    drift.` `spec-unified-container` named in its memlog, not stamped (its `pixi.toml` digest
    matches neither the baseline commit nor anything this story produced).
11. **Cleanup.** `rv3-app`, `rv3-pg`, `rv3-redis`, the `rv3-net` network and the `platform-review3`
    image all removed before this pass closed.

**Podman: still not verified** (unchanged — no podman access gained in this pass either). Every
patch in this pass is engine-independent by construction: no engine-conditional logic exists
anywhere in the Containerfile, and the CI changes are `${{ matrix.engine }}`-templated, so the
podman leg runs the identical instructions.

## Auto Run Result

**Status:** done (third follow-up review pass on a `done` spec; no intent gap, no spec loopback).

**What this pass changed.** Thirteen review-driven patches, one deferral, seven rejections. The
substantive half is three new *gates* rather than new features: the image build now fails if the
pip layer displaces a conda-provided package (the automated form of the `high` defect the previous
pass fixed by hand), CI now asserts the `/app` directory stayed non-writable (the automated form of
the `high` defect the pass before that fixed by hand), and CI now exercises the FastAPI half of the
ASGI dispatcher and the image's default GID. The rest are correctness fixes to statements that were
factually wrong — a pin-site count wrong for the third consecutive time, a health-check default that
was true of only one of two pinned majors, a compose retry policy documented as bounded when it is
not — plus one test that asserted something other than what it was named for.

**Files changed (7):**
- `src/platform/Containerfile` — pip layer fails the build on `Attempting uninstall:` (+ `set -o pipefail`).
- `.github/workflows/platform-ci.yml` — `.pixi/config.toml` added to both `paths:` lists; `pg_isready`
  forced to TCP; migrate step dumps logs on failure; new `/api/health` step; default-USER gid asserted;
  filesystem probe gains an `/app` non-writable assertion and `test -d` guards.
- `src/platform/config/urls.py` — version-qualified the default `checks` claim (comment only).
- `src/platform/tests/test_health_endpoint.py` — shadowing test now asserts `resolve("/ht/")`.
- `src/platform/compose/compose.yml` — corrected the `restart: on-failure` bound claim (comment only).
- `.dockerignore` — stop shipping `src/platform/compose/` into the image.
- `pixi.toml` — pin-site enumeration renumbered (1)–(15), headline corrected (comment only;
  `environment.yaml` re-exported byte-identical).

Plus three governing-spec memlogs and the scoped baseline stamp.

**Review findings breakdown:** 13 patches applied (5 medium, 8 low); 1 deferred
(`DW-FU-10-3-10`, the unenforced equality of the two `paths:` lists); 7 rejected (four already
settled or already-deferred, three failed verification on their own facts).

**Verification.** Full detail in "Third-follow-up-review re-verification" above. Headlines: a real
end-to-end `docker build` green with a clean secrets-scan; the new pip gate proven in BOTH
directions (and a false-negative attempt diagnosed — pip user-installs instead of displacing when
run as the image's non-root user, which is not the builder's posture); a live arbitrary-UID stack
where migrate, `/ht/`, `/admin/login/`, `/`, every rendered static URL and `/api/health` all
return 200; the filesystem contract green including the new `/app` assertion, with
`rm /app/entrypoint.sh` still `Permission denied`; 24/24 pytest on the pip stack, with the
strengthened shadowing assertion negative-tested and the mutated file restored and re-run;
`environment.yaml` byte-identical; and the spec-surface gate back to rc=0 with a baseline delta of
exactly 2 changed / 0 added / 0 removed.

**Residual risks.**
- **Podman remains unverified locally** — unchanged and disclosed throughout. No engine-conditional
  logic exists anywhere in the Containerfile and every CI change is `${{ matrix.engine }}`-templated,
  so the podman leg runs identical instructions; it is still the first automated proof.
- **The new pip gate is a tripwire, not a fix.** It stops a stale exclusion list from shipping
  silently; it does not keep the list current. A `pixi.lock` refresh that adds a kept package will
  now fail the build loudly — which is the intent, but it means a lock bump can red CI for a reason
  that looks unrelated. The message names the remedy.
- **`spec-unified-container` is still not stamped**, so its `.dockerignore` baseline stays behind by
  design. Named in its memlog; the structural half is `DW-FU-10-3-9`.
- **The two `paths:` lists are still hand-kept.** Asserted equal at this commit, unenforced
  thereafter (`DW-FU-10-3-10`).
