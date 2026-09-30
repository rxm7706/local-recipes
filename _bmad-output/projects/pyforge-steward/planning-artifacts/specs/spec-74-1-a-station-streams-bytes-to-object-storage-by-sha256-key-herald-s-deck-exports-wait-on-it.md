---
title: "74.1: A station streams bytes to object storage by sha256 key — herald's deck exports wait on it"
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: 73dca4a27565789905adcaf19aa223dfef9038b4
review_loop_iteration: 0
followup_review_recommended: true
flag:
  key: pyforge.steward.object_store_consumer
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need Guild CAP-5 (steward Epic 76); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: put_stream and open_stream raise ObjectStoreDisabled; a consumer keeps its exports in git only, as today
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/platform/config/object_storage.py
  - src/platform/tests/test_object_storage_client.py
  - src/shared/packages/django-pyforge/src/django_pyforge/flags.py
warnings: [oversized]
deferred:
  - summary: >-
      src/platform/ingest/github_projects still imports pyforge.steward.keys and .sync, a live breach of "src/platform
      never imports pyforge.*"; the new meta-test enforces the rule tree-wide with a closed, exact allowlist of those four files.
    evidence: |-
      pixi.toml [feature.platform-ci-test.dependencies] already names it "the live pap:AD-2 breach". Relocating the Story 12.8 dlt
      lane out of the host is its own effort (its pixi tasks, ruff per-file ignores and Postgres sink move with it), not this
      story's Surface. The allowlist is exact: a listed file that stops importing pyforge.* fails the test until it is removed
      from the list, so the list can only shrink, and any new importer reds.
    location: >-
      src/platform/ingest/github_projects/pipeline.py
    severity: medium
  - summary: >-
      On real S3 a head_object on an absent key answers 403 rather than 404 when the credential lacks s3:ListBucket, so a
      Put/Get-only credential would fail every first put_stream with the client's AccessDenied instead of uploading.
    evidence: |-
      Unverified. The spec's Design Notes propagate every non-404 client error on purpose (a permission error must never read
      as absent), so the module does what the contract says. What would settle it: the policy of the credential that Story 74.2's
      chart mounts (canopy:AD-19). If it lacks s3:ListBucket, either grant it or decide in that story how a 403 on head is read.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/object_store.py
    severity: medium (unverified)
  - summary: >-
      The silo-backed round-trip tests skip in Platform CI and in platform-ci-local, because neither lane installs the
      platform-object-storage environment, so only a local run exercises the real store.
    evidence: |-
      .github/workflows/platform-ci.yml runs the platform-ci-test environment only, and scripts/platform-ci-local.sh ensure_envs
      provisions platform-ci-test, platform-dev and pyforge-warden. The same skip-in-CI pattern already holds for CAP-97's own
      src/platform/tests/test_object_storage_client.py. This story added silo-free tests that pin the sha256, the dedup skip and
      the bounded reads, so the contract no longer depends on the silo for those. Wiring the environment into the lane is a CI
      change outside this story's Surface.
    location: >-
      .github/workflows/platform-ci.yml
    severity: medium
  - summary: >-
      pixi.toml:226 still says of boto3 "no consumer wired in yet", which is false now that django_pyforge.object_store consumes
      the seam.
    evidence: |-
      Cosmetic; the text is a comment, and docs/reference/library-llms-full.md does not embed it (checked). pixi.toml is governed by
      eight specs' surfaces, and a pixi.toml change fires pyforge-station-tests across every station suite and eight memlog
      reconciles, which is out of proportion to a comment. Batch it with the next pixi.toml change (Story 74.2).
    location: >-
      pixi.toml
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `src/platform/config/object_storage.py` (Story 50.3, CAP-97) resolves one boto3 S3 client from
`OBJECT_STORAGE_ENDPOINT_URL` / `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` and says "No existing feature is
wired to consume this seam yet". No bucket or prefix setting exists, nothing puts or reads an object, and no portal can
reach the seam: every `django-<station>` package reaches the host only through `django_pyforge.*` (access, portals,
supervisor, flags), never through the host's `config` package. Herald needs to keep each current deck export in the store
(the operator ruled on 2026-09-28 that Herald's exports are the seam's first consumer and that bytes never go in
PostgreSQL). Herald's Stories 29.1 and 29.2 are minted `blocked` on this story in herald's ledger.

**Approach:** add `django_pyforge.object_store`, the one contract a portal (or the station API it serves under
`/stations/<name>/api/v1/`) uses:

- `put_stream(fileobj, *, content_type) -> StoredObject` reads the caller's stream in fixed chunks into a
  `tempfile.SpooledTemporaryFile` with a bounded in-memory threshold while updating a `hashlib.sha256`, then uploads the
  spooled file with the client's managed transfer (`upload_fileobj`) under `<prefix>/sha256/<hex>` unless a `head_object`
  finds that key already there (content-addressed: identical bytes land once). It returns `StoredObject(key, sha256, size,
  content_type)`.
- `open_stream(key) -> Iterator[bytes]` yields `get_object(...)["Body"]` in chunks, ready for a Django
  `StreamingHttpResponse`; `stat(key)` returns size and content type from `head_object`.
- Keys are validated before any client call: exactly `sha256/<64 lowercase hex>` below the configured prefix, so no
  caller-supplied path reaches the store.
- The client is CAP-97's factory, named by a new setting `OBJECT_STORAGE_CLIENT_FACTORY`
  (default `"config.object_storage.object_storage_client"`) and resolved with `django.utils.module_loading.import_string`:
  the chrome never builds a second S3 client (AD-1) and never imports the host's `config` package.
- `OBJECT_STORAGE_BUCKET` and `OBJECT_STORAGE_PREFIX` join `config/settings/base.py`, read from the environment like the
  three existing settings, with no default; an unset one raises `ImproperlyConfigured` naming it.
- The flag `pyforge.steward.object_store_consumer` enters `src/platform/config/flags.json` with variants `on` / `off` and
  `defaultVariant: off`, and is evaluated with `django_pyforge.flags.evaluate_boolean` (the sanctioned reader); OFF, both
  calls raise `ObjectStoreDisabled` before touching the client.
- No presigned URLs in v1: a portal streams every byte behind OIDC and the station role, so the store needs no endpoint a
  browser can reach.
- `config/object_storage.py`'s docstring stops saying nothing consumes the seam and names this contract.

Ledger key: `74-1-a-station-streams-bytes-to-object-storage-by-sha256-key-herald-s-deck-exports-wait-on-it`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-163 (FR-36; extends CAP-94..97); AD-1 (wrap, never reimplement); canopy:AD-19 (secret
  references); canopy:AD-9 (a consumer's metadata table is its own, in `public`, on its own chain).
- `spec-feature-flag-governance` CAP-1 (the flag block), Q3–Q5.
- Kinship: herald Stories 29.1 / 29.2 (herald's chain, `blocked` on this story); Story 74.2 (the chart's bucket, prefix and
  egress); Epic 76 (per-environment flag values).

## Acceptance Criteria

- Given a real ephemeral `silo` (CAP-97's pattern) and a stream larger than the spool threshold When `put_stream` runs Then it returns the sha256 the test computed independently, the object sits at `<prefix>/sha256/<hex>`, and the process never held the whole payload in one buffer (the test reads through a chunk-counting stream)
- Given the same bytes put twice When the second `put_stream` runs Then no upload call is made and the same `StoredObject` comes back
- Given a stored key When `open_stream` runs Then it yields the same bytes in more than one chunk, and `stat` returns their size and content type
- Given a key that is not `sha256/<64 lowercase hex>` (uppercase, short, `../`, an absolute path) When `open_stream` or `stat` runs Then it raises before any client call
- Given `OBJECT_STORAGE_BUCKET` or `OBJECT_STORAGE_PREFIX` unset When either call runs Then it raises `ImproperlyConfigured` naming that setting
- Given two flagd trees, one with `pyforge.steward.object_store_consumer` on and one off When each call runs Then ON behaves as above and OFF raises `ObjectStoreDisabled` with no client call
- Given the repo When the steward meta-test runs Then it reds any module under `src/platform/` that imports `pyforge.*` and any module under `django_pyforge` that imports `config` or `config.*`
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Stream: never `read()` a whole object, never store bytes in a model field or in PostgreSQL.
- Reach the client only through the settings-named factory; credentials stay the three secret references the chart
  already mounts (canopy:AD-19).
- Keep the store consumed: no object-store server in the platform image or the chart; local runs use CAP-96's
  `platform-object-storage` feature and its `silo`.
- Reconcile every Spec `spec-surface-check` names for the touched paths (`spec-pyforge-steward` and
  `spec-pyforge-unifying-strategy` govern `django-pyforge` and `src/platform`), then stamp each scoped with `--spec`.

**Never:**
- Do not add presigned URLs, a metadata table, a Liquibase changeset or a `herald` verb — the table and the verb are
  herald's (Stories 29.1 / 29.2).
- Do not import `pyforge.*` from `src/platform/`, or `config` from `django_pyforge`.
- Do not add a new process, a new pixi environment or a PostgreSQL pin move (fnd:CAP-12).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`; do not flip herald's `blocked` rows.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| first put | new bytes, flag ON | uploaded at `<prefix>/sha256/<hex>`, `StoredObject` returned | — |
| repeat put | same bytes | no upload, same `StoredObject` | — |
| large put | stream above the spool threshold | spooled to disk, hashed while read | bounded memory |
| get | stored key | chunks of the same bytes | — |
| bad key | `SHA256/…`, short hex, `../x` | refused before the client | `ValueError` |
| unset setting | no bucket or prefix | — | `ImproperlyConfigured` naming it |
| flag OFF | either call | nothing reaches the client | `ObjectStoreDisabled` |
| store down | endpoint unreachable | — | the client's error propagates, named, never swallowed |

</intent-contract>

## Code Map

- `src/platform/config/object_storage.py` -- CAP-97's factory `object_storage_client()` (:67) is the one client the seam resolves; only the docstring's "No existing feature is wired to consume this seam yet" (:19-20) changes.
- `src/platform/config/settings/base.py:417-427` -- the object-storage settings block (`env(..., default=None)` x3); the two new settings and the factory path join it.
- `src/platform/config/flags.json` -- the one flagd tree; three flags today, each `{state, variants, defaultVariant}`; the new key joins with `defaultVariant: off`.
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` -- `evaluate_boolean(key, default)` (:118) is the sanctioned reader (openfeature imported lazily; no provider configured means the default, so OFF fails closed); `configure_file_provider` (:75) and `wait_until_ready` (:93, keyed on `FLAG_KEY = pyforge.three_surfaces`, so a test tree must carry that key too or the provider never reads ready); `apps.py:22-25` configures the provider from the environment at host start.
- `src/shared/packages/django-pyforge/src/django_pyforge/object_store.py` -- new; no boto3/botocore/config import (the factory is reached by `import_string`, a missing key is recognised by duck-typing the client error's `.response`).
- `src/platform/tests/test_object_storage_client.py:33-34,56-104,126` -- CAP-97's pattern to copy: `REPO_ROOT`/`_SILO_BINARY`, the ephemeral `local_silo` fixture (skip when the env is absent), the `settings` fixture, the unconfigured-raises test.
- `src/platform/tests/test_openfeature_file_flags.py:73-85,210-218` -- the flagd-tree writer and `configure_file_provider(tmp path)` pattern for the ON and OFF trees.
- `src/platform/ingest/github_projects/{graphql,pipeline,source,test_github_metrics_dlt}.py` -- read-only evidence: the four existing `src/platform` importers of `pyforge.steward.*` (`pixi.toml:409` calls it "the live pap:AD-2 breach"); the meta-test allowlists exactly these (see `deferred`).
- `src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py` -- the AST-scan and repo-root-discovery style for a steward meta-test; `pixi.toml:602-604` `pyforge-steward-test` runs `pytest src/shared/packages/pyforge-steward/tests -q`, so the new meta-test runs there.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/object_store.py` -- new module: `StoredObject`, `ObjectStoreDisabled`, `put_stream`, `open_stream`, `stat`, setting-name constants, `SPOOL_MAX_BYTES` / `CHUNK_BYTES` -- the one contract a portal or station API uses
- `src/platform/config/settings/base.py` -- add `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_PREFIX` (`env(..., default=None)`) and `OBJECT_STORAGE_CLIENT_FACTORY` (plain string, `config.object_storage.object_storage_client`) -- the seam's configuration, secrets untouched
- `src/platform/config/flags.json` -- add `pyforge.steward.object_store_consumer`, variants `on`/`off`, `defaultVariant: off` -- the flag block of the story spec
- `src/platform/config/object_storage.py` -- docstring names `django_pyforge.object_store` as the consumer; no code change
- `src/platform/tests/test_object_store_seam.py` -- new: silo round trip (large put, repeat put, get/stat), key refusal, unset settings, ON/OFF trees, no-client-call proofs -- the I/O matrix and the ACs
- `src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py` -- new: AST scan for `pyforge.*` under `src/platform/` (closed allowlist) and `config`/`config.*` under `django_pyforge`, plus mutation proofs on tmp trees -- the two import rules, in the station's own suite
- `.memlog.md` of every Spec `spec-surface` names for the touched paths -- append the surface reconcile line -- Boundaries: reconcile, never stamp alone

**Acceptance Criteria:**
- Given the intent contract's eight ACs, when `python -m pytest` runs the new seam test in the platform env against a real `silo` and `pyforge-steward-test` runs the meta-test, then both pass and no test skips for the story's own subject.
- Given the I/O matrix, when the seam test runs, then each row (first put, repeat put, large put, get, bad key, unset setting, flag OFF, store down) has a test that fails if the row's behaviour is removed.

## Spec Change Log

## Source

Contract authored from `docs/dreams/pyforge-steward.md`'s 2026-09-28 (night) Realization-log entry *Proposed: the
object-storage seam gets its first consumer, Herald's deck exports*, the Herald Dream's entry of the same night, and
`spec-pyforge-steward` CAP-163 with its 2026-09-28 (night) direction entry in the Spec's `.memlog.md`.

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-163 (FR-36).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 (night) — Proposed: the object-storage seam gets its first consumer, Herald's deck exports*.
Ledger key: `74-1-a-station-streams-bytes-to-object-storage-by-sha256-key-herald-s-deck-exports-wait-on-it`.
Ledger status at mint: `backlog`.
Deps: —. Herald Stories 29.1 and 29.2 wait on this story as `blocked` rows in herald's ledger.

## Design Notes

- `StoredObject.key` is prefix-relative (`sha256/<hex>`); the object sits at `<prefix>/sha256/<hex>`. A consumer stores the relative key, so a per-environment prefix (Story 74.2) never invalidates its rows. `stat` returns the same dataclass, its `sha256` read back from the key.
- Check order in every call: flag (`ObjectStoreDisabled`) -> key shape (`ValueError`, pure) -> settings (`ImproperlyConfigured` naming the setting) -> factory client. `put_stream` resolves settings and the client before it reads the stream, so a misconfigured host refuses before consuming the payload.
- `put_stream` hashes and spools in `CHUNK_BYTES` reads (`SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES)`), then `head_object`; present means no upload and the stored content type comes back, absent means `upload_fileobj(spool, bucket, key, ExtraArgs={"ContentType": ...})`. Only a 404-shaped client error (`.response` Error.Code `404`/`NoSuchKey`/`NotFound`, or HTTP 404) means absent; every other error propagates unchanged.
- `open_stream` calls `get_object` eagerly (a missing key raises at the call, before a view builds its `StreamingHttpResponse`) and returns a generator over `Body.iter_chunks(CHUNK_BYTES)` that closes the body when exhausted or closed.
- The flag is read with `evaluate_boolean(FLAG_KEY, default=False)`; an unconfigured provider therefore reads OFF. Tests write two flagd trees, each carrying `pyforge.three_surfaces` as well so `wait_until_ready` returns.
- The meta-test's allowlist names the four `ingest/github_projects` files and asserts each still imports `pyforge.*`, so the list shrinks and never silently outlives its reason.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- ON/OFF: the seam test writes two flagd trees (flag on, flag off), the way `src/platform/tests/test_openfeature_file_flags.py`
  does, and runs both states (until the testing-kit fixture of `spec-feature-flag-governance` CAP-4 lands).
- `pixi install -e platform-object-storage`, then `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: the new
  seam test runs against a real `silo` and passes; a skip for a missing environment is not a pass for this story.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log

### 2026-09-29 — Review pass
- verdicts: 39 findings — high 0, medium 7, low 21, false 10, maybe-false 1
- findings:
  - `[false]` `[reject]` Intent-alignment: ACs 1-6 are verified in the platform environment, which AC 8's `pyforge-steward-test` does not run — the story's own Tasks & Acceptance AC names the platform-env seam test against a real silo, and both ran and passed (73 passed, 0 skipped; steward suite exit 0).
  - `[false]` `[reject]` Intent-alignment: AC 7 says "any module" but the meta-test allowlists four files — the allowlist is settled by the Design Notes and the spec's own `deferred:` entry, and a no-exception guard would red at once on the four real importers in `src/platform/ingest/github_projects` (an AST scan confirmed exactly those four).
  - `[false]` `[reject]` Intent-alignment: "unset" also refuses empty, whitespace and slash-only values — a stricter refusal of a value that is unusable anyway; no bad outcome.
  - `[false]` `[reject]` Intent-alignment: the intent says OFF fails "both calls" but three are gated — the Design Notes gate every call, and gating `stat` too is the consistent reading.
  - `[low]` `[patch]` Intent-alignment: a repeat put with a different content type is not exercised — same root cause as the verification-gap finding on the stored content type; patched with the test that puts identical bytes under two content types.
  - `[false]` `[reject]` Intent-alignment: the scoped baseline stamp absorbed Story 75.1's drift — moot: this run must not pass `--write-baseline`, so the subagent's stamps were reverted to the `baseline_revision` file, and `spec_surface_reconcile.py` and `spec-surface-check` both pass on the memlog reconciles alone.
  - `[false]` `[reject]` Intent-alignment: the diff adds a deferred-work ledger row and flips the spec status — the `deferred-work` detector requires the tracked twin of a `deferred:` entry, and the status flip is the workflow's own.
  - `[medium]` `[patch]` Blind Hunter: `open_stream` returns a synchronous iterator, and the platform serves ASGI (`gunicorn config.asgi:application` with `UvicornWorker`), where Django 5.2.17 buffers a sync iterator with `sync_to_async(list)` — verified in Django's `StreamingHttpResponse.__aiter__`; the docstring called it "ready for a StreamingHttpResponse". Patched by stating the caveat in the docstrings (an async view must offload each chunk to a thread); no API change, since the contract fixes `Iterator[bytes]`.
  - `[medium]` `[patch]` Blind Hunter: an unstarted generator never runs its `finally`, so a body closed or dropped before the first `next()` leaked its pooled connection — real (Python semantics; the old test only closed after `next()`). Patched: `_chunks` replaced by the `_BodyChunks` iterator class whose `close()` closes the body once whether or not iteration started, with a close-before-first-read test.
  - `[low]` `[reject]` Blind Hunter: the dedup path trusts whatever `ContentLength` sits at the key — an S3 PUT (including a completed multipart upload) is atomic, so a truncated object under a sha256 key can only come from a write outside this module; the guard adds a branch for a state not shown reachable.
  - `[low]` `[patch]` Blind Hunter: the docstring says "bounded temporary file" though only memory is bounded — patched with the docstring correction (disk holds the whole payload; the caller enforces any upload limit), together with the ASGI caveat above.
  - `[low]` `[reject]` Blind Hunter: a missing key surfaces as a raw `ClientError` and a consumer must duck-type a 404 — the I/O matrix ("the client's error propagates, named, never swallowed") and the Design Notes prescribe it, a test pins it, and an `ObjectNotFound` type would edit the contract.
  - `[false]` `[reject]` Blind Hunter: `open_stream` returns only bytes, so a view needs `stat` and can race a change between the two calls — the key is the sha256 of the content, so the object cannot change between the calls, and the two-call shape is the spec's API.
  - `[low]` `[reject]` Blind Hunter: bucket and prefix normalisation is inconsistent (a space is not stripped) — an operator typo in an environment value, loud when it fails; the fix adds validation for a case the chart does not produce.
  - `[low]` `[reject]` Blind Hunter: `content_type` is unvalidated — the parameter is a required keyword-only `str`, and a bad value fails loudly in the client; the fix adds a guard.
  - `[low]` `[patch]` Blind Hunter: the meta-test sees import statements only and a dynamic `import_module("pyforge...")` would pass — patched with a sentence in its module docstring that dynamic loads (the sanctioned ones in `config/asgi.py` and `config/station_api.py`) are out of scope; extending the scan would need an allowlist for those two.
  - `[low]` `[reject]` Blind Hunter: the allowlist has no owner story or expiry — this restates the spec's own `deferred:` entry, recorded as `DW-steward-74-1`; no new harm.
  - `[low]` `[reject]` Blind Hunter: the AST scan is brittle (a `SyntaxError`, a coding cookie, magic file-count sentinels) — an unparseable file fails the test loudly, not silently, and the sentinels guard against scanning nothing.
  - `[medium]` `[defer]` Blind Hunter: the silo-backed tests never run in CI — real (`platform-ci.yml` runs `platform-ci-test` only, and `platform-ci-local.sh` does not install `platform-object-storage`), but the same pattern already holds for CAP-97's `test_object_storage_client.py`; the regression cover for this story's logic is the silo-free tests added under the verification-gap finding, and wiring the environment into the lane is deferred.
  - `[false]` `[reject]` Blind Hunter: the flag carries no ownership metadata — the flag block (key, default, fallback, cleanup) lives in this spec's frontmatter, and the other three entries in `flags.json` carry only `state`, `variants` and `defaultVariant`.
  - `[low]` `[reject]` Blind Hunter: the new environment variables are undocumented in compose and the chart — the chart is Story 74.2's, the flag is OFF everywhere, and the `ImproperlyConfigured` message names the setting and where it is read.
  - `[false]` `[reject]` Blind Hunter: the baseline hunk moves files this story did not touch — moot, the stamp was reverted (see the intent-alignment row).
  - `[low]` `[reject]` Blind Hunter: test hygiene nits (a parametrised JSON re-read, a `SimpleNamespace` replacing `tempfile`) — cosmetic; no one meets them in everyday use.
  - `[medium]` `[patch]` Edge Case Hunter: the generator leak on an unstarted `open_stream` iterator — same root cause and fix as the Blind Hunter row.
  - `[maybe-false]` `[defer]` Edge Case Hunter: on real S3 `head_object` on an absent key answers 403 without `s3:ListBucket`, failing every first put for a Put/Get-only credential — the Design Notes propagate non-404 errors on purpose, so it is loud rather than silent; what would settle it is the policy of the credential Story 74.2's chart mounts. Recorded as medium if true, unverified.
  - `[low]` `[reject]` Edge Case Hunter: `read()` returning `None` or `CHUNK_BYTES <= 0` truncates the payload — `CHUNK_BYTES` is a module constant, and `None` only comes from a non-blocking raw stream, not from a Django uploaded file; the guard adds a branch.
  - `[low]` `[reject]` Edge Case Hunter: an existing object with a different `ContentLength` is trusted — same as the Blind Hunter row.
  - `[low]` `[reject]` Edge Case Hunter: two concurrent identical puts both upload — an idempotent overwrite of identical bytes; the redundant write is negligible, and `IfNoneMatch` is not portable across the S3-compatible stores.
  - `[low]` `[reject]` Edge Case Hunter: an empty or non-`str` `content_type` fails only after the stream is spooled — same as the Blind Hunter row.
  - `[low]` `[reject]` Edge Case Hunter: bucket or prefix with surrounding spaces or slashes — same as the Blind Hunter row.
  - `[low]` `[reject]` Edge Case Hunter: a non-callable client factory raises a bare `TypeError` that does not name the setting — a developer-set setting, immediately visible; the guard adds a branch.
  - `[low]` `[reject]` Edge Case Hunter: the dedup path and `stat` fall back differently when a stored object has no `ContentType` — objects this module writes always carry one, so only a foreign write reaches it.
  - `[low]` `[patch]` Edge Case Hunter: a dynamic `pyforge.*` load in `src/platform` passes the meta-test — same root cause and docstring patch as the Blind Hunter row.
  - `[false]` `[reject]` Edge Case Hunter: the seam test leaves `PYFORGE_FLAGS_PATH` pinned to a temp tree — nothing in `src/platform` reads that path after the tests (`resolve_flags_path` has no caller there), and the existing `test_openfeature_file_flags.py` has the identical side effect.
  - `[medium]` `[defer]` Edge Case Hunter: the story's "no test skips" criterion is met only locally because CI takes the silo skip branch — same as the Blind Hunter row; deferred with it.
  - `[medium]` `[patch]` Verification Gap: the tests that pin `put_stream`'s sha256, dedup skip and bounded reads all need silo, so in a lane without it three mutations survive (drop `digest.update`, `if existing is not None` to `if False`, `fileobj.read(CHUNK_BYTES)` to `fileobj.read()`) — the fake-client tests were read and confirmed to be blind to all three. Patched with silo-free tests for each.
  - `[low]` `[patch]` Verification Gap: the "stored content type comes back" rule on a repeat put is unpinned (a mutation left all 69 tests green) — patched with the two-content-type test.
  - `[medium]` `[patch]` Verification Gap: the "no boto3 / botocore import" boundary is claimed as test-pinned but is not, and django-pyforge declares neither dependency — verified against its `pyproject.toml`. Patched with a meta-test rule and a tmp-tree mutation proof.
  - `[low]` `[defer]` Verification Gap (other finding): the `pixi.toml:226` comment still says "no consumer wired in yet" — true and stale, but a `pixi.toml` edit needs eight spec reconciles and `pyforge-station-tests` across every station suite; deferred to batch with the next `pixi.toml` change.

## Auto Run Result

Status: done

### Summary of the implemented change

`django_pyforge.object_store` is the one contract a station portal uses to reach CAP-97's S3 seam: `put_stream` hashes the caller's stream while spooling it in fixed chunks to a `SpooledTemporaryFile` and uploads it under `<prefix>/sha256/<hex>` unless `head_object` already finds it; `open_stream` yields the object in chunks and `stat` returns its size and content type. Keys are checked as `sha256/<64 lowercase hex>` before any client call. The client comes from the setting-named factory through `import_string`, so the chrome never imports the host's `config`. `OBJECT_STORAGE_BUCKET` and `OBJECT_STORAGE_PREFIX` (no default, `ImproperlyConfigured` naming the one unset) and `OBJECT_STORAGE_CLIENT_FACTORY` join `config/settings/base.py`. The flag `pyforge.steward.object_store_consumer` ships `defaultVariant: off` in `config/flags.json` and is read with `evaluate_boolean(default=False)`, so OFF and an unconfigured provider both raise `ObjectStoreDisabled` before the client is touched. No presigned URLs.

### Files changed

- `src/shared/packages/django-pyforge/src/django_pyforge/object_store.py` — new: `StoredObject`, `ObjectStoreDisabled`, `put_stream`, `open_stream`, `stat`, the `_BodyChunks` iterator, setting-name constants and `SPOOL_MAX_BYTES` / `CHUNK_BYTES`.
- `src/platform/config/settings/base.py` — the three new settings; the secret references are untouched.
- `src/platform/config/flags.json` — the new flag, default off.
- `src/platform/config/object_storage.py` — docstring only: names the consumer.
- `src/platform/tests/test_object_store_seam.py` — new: the I/O matrix and the ACs against a real ephemeral silo and two flagd trees, plus silo-free fake-client tests for the sha256, the dedup skip, the bounded reads, the stored content type and the iterator close.
- `src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py` — new: the AST guards (`pyforge.*` under `src/platform` with the closed four-file allowlist, `config` under `django_pyforge`, `boto3` / `botocore` in `object_store.py`) with tmp-tree mutation proofs.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` and `.../spec-pyforge-unifying-strategy/.memlog.md` — the surface reconcile lines naming every governed path changed.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — `DW-steward-74-1` and `DW-steward-74-1-2` to `-4`, the twins of this spec's four `deferred:` entries.
- This story spec — the run's write-back.

### Review findings breakdown

39 findings: high 0, medium 7, low 21, false 10, maybe-false 1. Routing: 10 rows patched (6 entries), 4 rows deferred (3 new `deferred:` entries), 25 rejected. Patched counts by verdict: medium 5 rows in 4 entries, low 5 rows in 2 entries.

Patches applied:
- An unstarted `open_stream` generator leaked its body: replaced by the `_BodyChunks` iterator class, with a close-before-first-read test (medium).
- The ASGI buffering of a sync iterator and the "bounded temporary file" wording: docstrings now say so (medium; low).
- The silo-free regression gap on the sha256, dedup and bounded reads: fake-client tests added, each killing the mutation the reviewer found (medium).
- The unpinned `boto3` / `botocore` boundary: a meta-test rule and mutation proof added (medium).
- The unpinned stored content type on a repeat put: a two-content-type test (low).
- The import-only scan not naming its limit: a docstring sentence (low).

Deferred (each has a `location:` path and a tracked twin):
- `DW-steward-74-1-2` — `head_object` answers 403 without `s3:ListBucket` on real S3 (medium, unverified; settled by Story 74.2's credential).
- `DW-steward-74-1-3` — the silo-backed tests skip in Platform CI and `platform-ci-local` (medium; the same pattern already holds for CAP-97's test).
- `DW-steward-74-1-4` — the stale `pixi.toml:226` comment (low; a `pixi.toml` edit costs eight spec reconciles and every station suite).

Rejected, each with its reason in the Review Triage Log above: the four intent-alignment divergences that are settled by the spec (runner split, the four-file allowlist, "unset" scope, "both calls"); the stamp-width and baseline-hunk findings (moot, the stamp was reverted); the ledger row and status flip (required by the detector and the workflow); the dedup-trusts-`ContentLength`, concurrent-put, `read()`-returns-`None`, non-callable-factory, dedup-versus-`stat` content-type, content-type-validation and bucket/prefix-whitespace findings (states not shown reachable; each fix adds a guard); the raw-`ClientError` finding (the contract prescribes it and the fix edits it); the two-call `stat` race (the key is content-addressed and immutable); the allowlist-has-no-owner finding (restates `DW-steward-74-1`); the AST-brittleness and test-hygiene nits; the undocumented-variables finding (the chart is Story 74.2's); the flag-metadata finding (it lives in the spec frontmatter); and the `PYFORGE_FLAGS_PATH` leak (nothing reads it, and the existing flag test does the same).

### Follow-up review recommendation

`followup_review_recommended: true`: this first pass patched four medium entries. The named unverified risk is `_BodyChunks`, a new iterator class that replaced a generator: its close, exhaustion, error and idempotence semantics are tested against a fake body and a real silo, but never behind a real Django `StreamingHttpResponse` served by this platform's uvicorn worker, and the ASGI caveat in the `open_stream` docstring rests on Django 5.2.17's `StreamingHttpResponse.__aiter__` source, not on a test.

### Verification performed

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 1852 passed, 2 skipped; the story's own meta-test alone: 10 passed, none skipped.
- The seam test in the `platform-ci-test` environment against a real ephemeral silo — 73 passed, 0 skipped.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — exit 0; system checks, ruff, ruff format, mypy, the policy suite, sqlmigrate extraction and the full pytest suite all PASS.
- `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` — both exit 0, with no baseline stamp.
- I/O matrix audit: each of the eight rows (first put, repeat put, large put, get, bad key, unset setting, flag OFF, store down) has a covering test that ran and passed; the subagent also killed 16 hand-made mutations of `object_store.py`, and eight more after the review fixes.
- `pixi run -e pyforge-guild detectors-ci` — exit 1 on two findings, neither from this diff (see the residual risks).

### Residual risks

- `detectors-ci` reds on `ledger-direction` for `pyforge-marshal/77-1`: `main` landed that story after this branch point and this branch's marshal ledger predates it, so the finding clears when the branch merges with `main`; this diff touches no ledger.
- `detectors-ci` reds on `bmad_estate_check` (`skills` section) in this dispatch worktree only: the dispatch seeds a gitignored `.claude/skills/caveman/` (131 skill directories on disk, 130 tracked) that `main`'s catalog does not list; this diff touches no skill file, and regenerating the catalog here would commit an entry for a gitignored skill.
- The story's Boundaries say to stamp each Spec scoped with `--spec`, but this run's instruction forbids `--write-baseline`; the implementation subagent stamped twice, and both stamps were restored from `baseline_revision`. The surface guards pass on the memlog reconciles alone; a scoped stamp is left to whoever lands the story.
- The silo round trips are proven locally only (`DW-steward-74-1-3`); a consumer on real S3 may meet the 403 case (`DW-steward-74-1-2`).
- Herald's Stories 29.1 and 29.2 must handle the raw `ClientError` a missing key raises, and must offload chunks to a thread under ASGI; neither is a seam defect, both are in the docstrings now.
- `.pixi/envs/` in this worktree now holds `platform-ci-test`, `platform-dev`, `platform-object-storage`, `pyforge-steward` and `pyforge-warden` (gitignored).
