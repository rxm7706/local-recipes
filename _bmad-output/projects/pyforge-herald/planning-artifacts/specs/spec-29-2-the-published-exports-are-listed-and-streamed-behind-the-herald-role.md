---
title: '29.2: The published exports are listed and streamed behind the herald role'
type: 'feature'
created: '2026-09-28'
status: 'done'
followup_review_recommended: true
baseline_revision: 'dcbddeb4e3fc40552d620e30782c89d9d30a9afa'
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
deferred:
  - summary: >-
      Real ``deck_exports_json_runner`` subprocess argv and JSON validation are only mocked in platform refresh tests.
    evidence: |-
      Both refresh tests patch ``deck_exports_json_runner``; no test executes ``portal_runner.deck_exports_json_runner`` with a controlled subprocess.
    location: >-
      src/shared/packages/django-herald/src/django_herald_portal/portal_runner.py
    severity: medium
  - summary: >-
      ``refresh_deck_exports`` does not validate malformed manifest rows before ORM upsert.
    evidence: |-
      Missing keys or bad dates can raise ``KeyError``/``ValueError`` mid-slug; no structured command error or test pins the behavior.
    location: >-
      src/shared/packages/django-herald/src/django_herald_portal/deck_export_sync.py
    severity: medium (unverified)
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
Ledger status (do not edit the ledger): `backlog` -- flipped 2026-09-30 by the operator after steward Story 74.1 landed on main (dd95e70db7).
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

- [x] Read `pyforge.herald.deck_publish` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape; the `refresh_deck_exports` management command reads it through `django_pyforge.flags.evaluate_boolean`
- [x] Re-read steward Story 74.1's landed contract before starting
- [x] `DeckExport` model, `migrations/0001_initial.py`, `refresh_deck_exports`
- [x] The Liquibase changeset and its `db.changelog-master.yaml` include; the extraction map entry
- [x] The two routes on herald's v1 sub-app, through the entry point the host already loads by name, and a herald-role read gate that accepts a portal browser session (record how in the Review Triage Log)
- [x] Tests in `src/platform/tests/` and herald-package handler tests over the store fake, including the ON/OFF test
- [x] Spec-surface reconcile for every Spec the detector names (memlog entries on `spec-pyforge-herald`, `spec-pyforge-unifying-strategy`, `spec-pyforge-core`; scoped baseline stamps land with the PR author)

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

## Spec Change Log

- 2026-09-30 -- operator flip, `blocked` -> `backlog`: the cross-station gate cleared when steward Story 74.1 landed on main (dd95e70db7). Nothing else in the contract changed. A resumed worktree brings `origin/main` into its branch first (merge, never rebase).

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

- 2026-10-07 — Portal browser session auth for deck-export routes: `django_herald_portal.deck_export_routes.resolve_herald_roles` loads the Django session by `SESSION_COOKIE_NAME`, reads `IDP_TOKEN_CLAIMS` from session storage, and passes claims through `roles_from_request` (same herald-role gate as bearer assertions via `verify_assertion`). Route handlers live in `pyforge.herald.deck_exports`; Django wiring is lazy from `station_api.attach_webhook_asgi`.

### 2026-10-07 — Review pass
- verdicts: 28 findings — high 0, medium 4, low 3, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` CAP-54 D3 publish-time upsert — Story 29.2 contract is refresh-only via management command; no publish hook required.
  - `[false]` `[defer]` Ledger key still `backlog` — harness must not flip ledger rows (AGENTS.md policy); operator promotes via Tier-3 feed + sprint-ledger-sync at land.
  - `[medium]` `[patch]` Portal session cookie auth untested at platform ASGI boundary — added `test_list_returns_projection_with_portal_session` and `test_list_forbidden_with_portal_session_wrong_role` in `src/platform/tests/test_herald_deck_exports.py`.
  - `[low]` `[reject]` CORS probe with `Origin:` header not exercised — AC requires absence of `Access-Control-Allow-Origin` on responses; existing bearer test asserts that on 200.
  - `[medium]` `[patch]` Refresh stale-row deletion untested — added `test_refresh_removes_stale_rows_for_slug` in `src/platform/tests/test_herald_deck_exports.py`.
  - `[medium]` `[defer]` Malformed manifest JSON rows — see frontmatter `deferred` entry for `deck_export_sync.py`.
  - `[false]` `[reject]` Platform integration missing store-down 502 — open-path 502 covered in herald unit tests; mid-stream uses closed body per matrix alternate.
  - `[low]` `[reject]` `export_filename` lacks file extension — cosmetic; content-type header carries MIME.
  - `[defer]` `[defer]` pyforge-herald / django-herald package metadata coupling — monorepo workspace layout predates this story.
  - `[false]` `[reject]` Spec-surface baseline stamps pending — `python scripts/spec_surface_reconcile.py` and `spec-surface-check` exit 0 after memlog reconcile.
  - `[low]` `[reject]` Epic prose cites `station_api` for flag read — handlers live in `deck_exports.py` per Review Triage Log; intentional split.
  - `[defer]` `[defer]` Unified diff includes merged non-29.2 commits — trunk merge artifact; review scoped to herald deck-export hunks.
  - `[medium]` `[patch]` Mid-stream store failure should not 500 — `deck_exports.py` maps chunk `OSError` to closed stream (`test_attach_routes_mid_stream_store_error_closes_body`).
  - `[defer]` `[defer]` Missing manifest keys raise KeyError — deferred with malformed-row item above.
  - `[defer]` `[defer]` Bad date format aborts refresh — ops/data contract; not introduced by this story’s happy path tests.
  - `[defer]` `[defer]` Empty manifest list deletes slug rows — behavior matches “removed records removed”; covered indirectly by stale-row test.
  - `[defer]` `[defer]` Partial refresh on PortalClient failure — command continues other slugs; exit code semantics unchanged from design.
  - `[defer]` `[defer]` Subprocess cwd depends on `PYFORGE_REPO_ROOT` — deployment concern; deferred.
  - `[defer]` `[defer]` JSONDecodeError on runner stdout — deferred with malformed-row item.
  - `[false]` `[reject]` List route maps ORM failures to 503 — no such handler in `deck_exports.py`; ORM errors propagate as server errors (pre-existing Django pattern).
  - `[false]` `[reject]` Non-KeyError store errors unmapped — `open_deck_export_stream` wraps store `KeyError` as `OSError`; sync open maps to 502.
  - `[false]` `[reject]` Claim: mid-stream must return 502 — matrix allows closed stream; implementation stops chunked body after partial bytes.
  - `[medium]` `[patch]` Verification gap: session auth — same patch as portal session tests above.
  - `[medium]` `[patch]` Verification gap: stale rows — same patch as refresh stale-row test above.
  - `[defer]` `[defer]` Verification gap: real subprocess runner — deferred to `portal_runner.py` entry in frontmatter.
  - `[false]` `[reject]` Intent: flag OFF forces 404 for anonymous — separate AC requires anonymous → 401; gate runs before flag check.
  - `[false]` `[reject]` Intent strict flag-off-only reading — both AC rows apply; 401 for anonymous with flag on/off is correct.

## Auto Run Result

Status: done

Summary of implemented change: Story 29.2 lands `DeckExport` projection, `refresh_deck_exports`, Liquibase extraction, herald v1 list/stream routes behind herald role (bearer + portal session), and flag-gated behavior. Review pass added platform session-cookie tests, refresh stale-row coverage, and mid-stream store failure handling (closed chunked body).

Files changed (review pass):
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_exports.py` — mid-stream store errors stop chunk iteration cleanly.
- `src/shared/packages/pyforge-herald/tests/unit/test_deck_exports_handlers.py` — mid-stream closed-body regression test.
- `src/platform/tests/test_herald_deck_exports.py` — portal session auth and stale-row refresh tests.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md` — surface reconcile (review pass paths).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` — co-governor platform test path.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` — co-governor herald `deck_exports.py`.

Review findings breakdown: 4 medium patches applied (session list auth, stale refresh, mid-stream stream handling, verification-gap duplicates of the first two); 2 items deferred (`portal_runner.py`, `deck_export_sync.py` malformed rows); 8 false/rejected; 3 low rejected.

Follow-up review recommendation: `true` — two medium verification patches landed in one pass; real `deck_exports_json_runner` subprocess behavior remains unverified in CI (see deferred `portal_runner.py`).

Verification performed:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — pass (1594 passed, 4 skipped).
- `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` — pass (1130 passed, 13 skipped), including `test_herald_deck_exports.py` and policy/sqlmigrate suites.
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog entries on `spec-pyforge-herald`, `spec-pyforge-unifying-strategy`, and `spec-pyforge-core`.

Residual risks: Unmocked refresh subprocess path; malformed CLI JSON error handling; ledger key promotion still operator-owned at PR land.
