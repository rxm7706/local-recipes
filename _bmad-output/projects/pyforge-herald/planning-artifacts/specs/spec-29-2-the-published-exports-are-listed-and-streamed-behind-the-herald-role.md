---
title: '29.2: The published exports are listed and streamed behind the herald role'
type: 'feature'
created: '2026-09-28'
status: 'blocked'
blocking_condition: 'blocked until steward Story 74.1 (the object-storage seam''s first-consumer contract) has landed on main; the operator flips the ledger key, never a session'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.herald.deck_publish
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'the deck-exports routes answer 404 as if unregistered, and refresh_deck_exports writes nothing; the portal home is unchanged'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-29-1-herald-deck-publish-puts-each-current-export-in-the-object-store.md
  - src/platform/config/station_api.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py
  - src/shared/packages/django-herald/src/django_herald_portal/views.py
  - src/platform/tests/policy/test_sqlmigrate_extraction.py
  - src/platform/tests/policy/test_liquibase_ddl_governance.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Story 29.1, each current export and its manifest sit in the object store, but
nothing in the platform can list them or serve one. The intake proposed a Django view with a
hard-coded CORS origin streaming bytes out of PostgreSQL; the operator rejected both. The portals
require OIDC and a station role, and station routes live under `/stations/herald/api/v1/`.

**Approach:**
- django-herald gains a `DeckExport` model (slug, topic, kind, export date, size, content type,
  sha256, source commit, published at): a projection of the publish records (canopy:AD-18), with
  no binary field. A `refresh_deck_exports` management command upserts it from
  `herald deck exports --json`, invoked through the portal's `PortalClient` (the pattern
  `chrome_home` uses for `deck status`). No portal request writes it (D3).
- Its migration gets one namespaced Liquibase changeset under
  `src/platform/db/changelog/changes/`, at the id the sqlmigrate extraction map assigns. That is
  the next free `python-agent-platform:<seq>` (the warden-fabric precedent), unless this story
  registers django-herald as its own distribution in the map, as pyforge-scribe did (canopy:AD-9;
  the D3 precision on the Spec memlog).
- Herald's v1 station sub-app gains `GET /stations/herald/api/v1/deck-exports` (the records, from
  the manifests) and `GET /stations/herald/api/v1/deck-exports/{sha256}` (the bytes, streamed in
  bounded chunks from the store through `pyforge.herald.deck_store`, with the record's content
  type and a `Content-Disposition` filename). Both require an identity carrying the herald station
  role, and neither sends a CORS header (D4).

Ledger key: `29-2-the-published-exports-are-listed-and-streamed-behind-the-herald-role`.
Ledger status (do not edit the ledger): `blocked`, until steward Story 74.1 lands; the operator flips it.
Type / Effort / Deps: feature / M / S-29.1.

### Living CAP citations

- `spec-pyforge-herald` CAP-54 (FR-10.2; decisions D3, D4 and the D3 precision in `.memlog.md`); AD-22; AD-16's public-read clause does not extend to these routes.
- canopy:AD-2 (`/stations/<name>/`), canopy:AD-9 (Liquibase), canopy:AD-18 (projections), pap:AD-2 (the import boundary).
- `feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given published exports When `refresh_deck_exports` runs Then `DeckExport` holds one row per record and the model has no binary field
- Given a caller with the herald role When it calls the list route Then it gets the records as JSON
- Given a caller with the herald role When it calls the stream route with a published sha256 Then the bytes stream in bounded chunks with the record's content type and filename
- Given an anonymous caller When it calls either route Then it gets 401; given a caller without the herald role Then 403; given an unknown sha256 Then 404
- Given any response from these routes When its headers are read Then none is `Access-Control-Allow-Origin`
- Given the migration When the platform policy tests run Then `test_sqlmigrate_extraction.py` and `test_liquibase_ddl_governance.py` pass
- Given the flag OFF When either route is called Then it answers 404, and `refresh_deck_exports` writes nothing

## Tasks

- [ ] Read `pyforge.herald.deck_publish` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape; the `refresh_deck_exports` management command reads it through `django_pyforge.flags.evaluate_boolean`
- [ ] Re-read steward Story 74.1's landed contract before starting
- [ ] `DeckExport` model, `migrations/0001_initial.py`, `refresh_deck_exports`
- [ ] The Liquibase changeset and its `db.changelog-master.yaml` include; the extraction map entry
- [ ] The two routes on herald's v1 sub-app, through the entry point the host already loads by name, and a herald-role read gate that accepts a portal browser session (record how in the Review Triage Log)
- [ ] Tests in `src/platform/tests/` and herald-package handler tests over the store fake, including the ON/OFF test
- [ ] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **The flag reader** (coordinator ruling 2026-09-28): The deck-exports route handlers in `pyforge.herald.station_api` read `pyforge.herald.deck_publish` through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract (`75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`). If 75.1 has not landed when this story runs, add it to `pyforge.core` in exactly 75.1's shape -- `read_boolean(key, default=False)` in `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: it resolves the tree as `cutover_root.resolve_flags_path` does, returns False for `state: DISABLED`, returns the `defaultVariant`'s value when it is a bool, and reads False with a named WARN on stderr for a missing tree, a missing key or a non-bool value, never True; with `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, reconciled on `spec-pyforge-core` -- and never write a station-local reader.
- Portal and Django paths (the `refresh_deck_exports` management command) read `pyforge.herald.deck_publish` through `django_pyforge.flags.evaluate_boolean`, never `read_boolean` and never a second reader.
- **Blocked until steward Story 74.1 has landed; the operator flips it.** Do not start this story while 74.1 is unlanded.
- Stream in bounded chunks; nothing reads a whole object into memory or a model field.
- The routes stay under `/stations/herald/api/v1/`, and the host keeps loading `pyforge.herald.station_api` by name (`src/platform/config/station_api.py:122`). A host edit, if one is needed, loads by name the same way and is reconciled with the Spec that governs that file.
- Reconcile every Spec `spec-surface-check` names (`spec-pyforge-herald`, plus the co-governors of `src/platform/` and `django-herald`), then stamp each scoped with `--spec`.
- The PR carries the `maintenance` label.

**Never:**
- Do not write a station-local flag reader, and do not parse the flag tree from herald code.
- Do not add a `BinaryField`, `BYTEA` or any bytes column.
- Do not add `django-cors-headers` or any `Access-Control-*` header.
- Do not let a portal request write `DeckExport` or the store.
- Do not add a `pyforge.*` import under `src/platform/`, or a `django` import in the base herald package.
- Do not create a fifth PostgreSQL schema or raise the PostgreSQL pin (fnd:CAP-12).
- Do not flip this story's ledger key, or any other `blocked` key; do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| list | herald role, 2 published decks | JSON records for both | 200 |
| stream | herald role, known sha256 | chunked body, record's content type, filename | 200 |
| unknown key | herald role, sha256 not in any record | not found | 404 |
| anonymous | no identity | refused | 401 |
| wrong role | identity without the herald role | refused | 403 |
| CORS probe | `Origin: https://pages.example` header | no `Access-Control-Allow-Origin` in the response | — |
| store down | the store refuses mid-stream | the stream ends with an error, nothing cached | 502 or a closed stream, logged |
| refresh | manifest changed | rows upserted to match; removed records removed | exit 0 |
| flag OFF | any call | not found; refresh writes nothing | 404 |
| 74.1 absent | dispatched before 74.1 landed | refused: the ledger key is `blocked` | operator gate |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-54 (FR-10.2; D3, D4).
Architecture: AD-22.
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `29-2-the-published-exports-are-listed-and-streamed-behind-the-herald-role`.
Ledger status at mint: `blocked`, until steward Story 74.1 has landed; the operator flips it.
Deps: S-29.1. Cross-station gate: steward Story 74.1.
Flag: `pyforge.herald.deck_publish` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-29.1 • **FR/AD:** spec-pyforge-herald CAP-54 (FR-10.2; D3, D4); AD-22 • cross-project gate: steward Story 74.1 must have landed first — the ledger key is minted `blocked` and the operator flips it • flag: `pyforge.herald.deck_publish`

**Given** Story 29.1 publishes exports and their manifest to the store, and nothing in the platform can list or serve them
**When** the projection, its changeset and the two routes land
**Then** `refresh_deck_exports` fills `DeckExport` from the manifest and the model has no binary field; the list route returns the records; the stream route streams the bytes in bounded chunks with the record's content type; an anonymous call gets 401, a caller without the herald role 403, and an unknown sha256 404; no response carries `Access-Control-Allow-Origin`
**And** `test_sqlmigrate_extraction.py` and `test_liquibase_ddl_governance.py` stay green; no `pyforge.*` import appears under `src/platform/`; with the flag OFF both routes answer 404; `platform-ci-local -- --test` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; the herald-side handler tests over the store fake and the ON/OFF test run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.deck_publish` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, and asserts the routes answer ON and 404 OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass, including `src/platform/tests/test_herald_deck_exports.py`, `tests/policy/test_sqlmigrate_extraction.py` and `tests/policy/test_liquibase_ddl_governance.py`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log
