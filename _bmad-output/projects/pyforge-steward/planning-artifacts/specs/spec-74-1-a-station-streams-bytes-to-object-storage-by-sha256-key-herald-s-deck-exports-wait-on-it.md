---
title: "74.1: A station streams bytes to object storage by sha256 key — herald's deck exports wait on it"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
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
deferred: []
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
