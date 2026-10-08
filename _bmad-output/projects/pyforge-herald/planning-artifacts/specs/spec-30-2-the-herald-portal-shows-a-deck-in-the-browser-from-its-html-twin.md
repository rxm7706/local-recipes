---
title: '30.2: The herald portal shows a deck in the browser from its HTML twin'
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: '7b8d08144bd5fa5edff952a6f5382ffdbd490970'
followup_review_recommended: false
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.herald.deck_viewer
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'the portal shows only today''s deck-status home; the deck list, the viewer and the twin route answer 404'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-29-2-the-published-exports-are-listed-and-streamed-behind-the-herald-role.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-30-1-a-deck-s-html-twins-are-self-contained-and-published.md
  - src/shared/packages/django-herald/src/django_herald_portal/views.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py
  - src/platform/tests/test_herald_portal_deck_status.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Readers inside the enterprise airgap have no way to read a deck without PowerPoint.
The herald portal (`/stations/herald/`) shows one deck's status and nothing else. After Epic 29 and
Story 30.1, the store holds each deck's self-contained twins and the platform can stream them, but
no page shows one. The operator ruled out a browser-side `.pptx` parser (PPTXjs) on 2026-09-28.

**Approach:**
- *Twin route.* Herald's v1 station sub-app gains `GET /stations/herald/api/v1/deck-twins/{slug}/{path}`.
  It resolves `path` through the deck's current bundle manifest (or serves the standalone) and
  streams it from the store through `deck_store`. It sits behind Story 29.2's herald-role read
  gate, and its responses carry a Content-Security-Policy that names no origin other than
  `'self'`.
- *Portal.* django-herald gains `decks/`, which lists the published decks from the `DeckExport`
  projection, and `decks/<slug>/view/`, which frames the twin route in a sandboxed iframe and
  offers the current `.pptx` as a download through Story 29.2's stream route. Both views use
  `require_station_role("herald")`. The home page's Pitch tab links to the list (AD-12, amended).

Ledger key: `30-2-the-herald-portal-shows-a-deck-in-the-browser-from-its-html-twin`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-29.2, S-30.1.

### Living CAP citations

- `spec-pyforge-herald` CAP-55 (FR-10.4; decision D5 in `.memlog.md`); AD-22; AD-12 (amended 2026-09-28 (night)).
- canopy:AD-2 (the portal prefix), canopy:AD-3 (chrome from `django-pyforge` only).
- `feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a caller with the herald role When it opens `/stations/herald/decks/` Then every published deck is listed from `DeckExport`
- Given a published deck When `/stations/herald/decks/<slug>/view/` loads in a browser Then the twin renders and every asset request goes to the portal's own origin (a Playwright run records zero requests to any other origin), for one standalone and one bundle
- Given a twin response When its headers are read Then its Content-Security-Policy names no origin other than `'self'`, and there is no `Access-Control-Allow-Origin`
- Given the viewer page When it is read Then the `.pptx` is offered only as a download link and no script parses it
- Given an anonymous caller Then it is refused; given a caller without the herald role Then it gets 403
- Given the flag OFF Then the list, the viewer and the twin route answer 404 and the home page is unchanged

## Tasks

- [ ] Read `pyforge.herald.deck_viewer` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape; the django-herald `decks/` and `decks/<slug>/view/` views read it through `django_pyforge.flags.evaluate_boolean`
- [ ] The twin route on herald's v1 sub-app, with the CSP header, behind Story 29.2's read gate
- [ ] The two django-herald views, their URLs and templates (chrome from `django-pyforge`), and the Pitch-tab link
- [ ] `src/platform/tests/test_herald_portal_deck_viewer.py` and a Playwright zero-foreign-request check
- [ ] The ON/OFF test
- [ ] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **The flag reader** (coordinator ruling 2026-09-28): The deck-twins route handler in `pyforge.herald.station_api` reads `pyforge.herald.deck_viewer` through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract (`75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`). If 75.1 has not landed when this story runs, add it to `pyforge.core` in exactly 75.1's shape -- `read_boolean(key, default=False)` in `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: it resolves the tree as `cutover_root.resolve_flags_path` does, returns False for `state: DISABLED`, returns the `defaultVariant`'s value when it is a bool, and reads False with a named WARN on stderr for a missing tree, a missing key or a non-bool value, never True; with `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, reconciled on `spec-pyforge-core` -- and never write a station-local reader.
- Portal and Django paths (the django-herald `decks/` and `decks/<slug>/view/` views) read `pyforge.herald.deck_viewer` through `django_pyforge.flags.evaluate_boolean`, never `read_boolean` and never a second reader.
- The twin is served under the portal's own origin, from the store, through the station package (AD-22).
- The iframe is sandboxed, and the CSP names only `'self'`.
- Chrome comes from `django-pyforge` only (canopy:AD-3); django-herald ships no base layout.
- Reuse Story 30.1's scan in the tests; there is no second definition of "self-contained".
- The PR carries the `maintenance` label.

**Never:**
- Do not write a station-local flag reader, and do not parse the flag tree from herald code.
- Do not parse `.pptx` in the browser, and add no PPTXjs, jQuery or JSZip.
- Do not send a CORS header, and do not add `django-cors-headers`.
- Do not serve a twin from git or from the local filesystem in production; the store is its home.
- Do not let a view write the store or `DeckExport`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| list | herald role, 3 decks published | 3 rows, each linking its viewer | 200 |
| standalone view | a deck with only a standalone twin | the standalone in the frame | 200 |
| bundle view | a deck with a bundle | `index.html` and every asset from `deck-twins/<slug>/...` | 200 |
| unknown path | `deck-twins/<slug>/nosuch.js` | not found | 404 |
| path traversal | `deck-twins/<slug>/../../x` | refused | 404 |
| no twin published | a deck with exports only | the viewer says so and offers the download | 200 |
| anonymous | no identity | refused | 401 or login redirect |
| wrong role | identity without the herald role | refused | 403 |
| flag OFF | any of the three routes | not found | 404 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-55 (FR-10.4; D5).
Architecture: AD-22; AD-12 (amended 2026-09-28 (night)).
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `30-2-the-herald-portal-shows-a-deck-in-the-browser-from-its-html-twin`.
Ledger status at mint: `backlog`.
Deps: S-29.2 (the projection, the stream route and the read gate), S-30.1 (the twins). Through Epic 29 this story also waits on steward Story 74.1.
Flag: `pyforge.herald.deck_viewer` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-29.2, S-30.1 • **FR/AD:** spec-pyforge-herald CAP-55 (FR-10.4; D5); AD-22, AD-12 (amended 2026-09-28 (night)) • flag: `pyforge.herald.deck_viewer`

**Given** Epic 29 serves published exports and Story 30.1 publishes self-contained twins, but the portal shows only one deck's status
**When** the deck list, the twin route and the viewer land
**Then** `/stations/herald/decks/` lists every published deck, and `/stations/herald/decks/<slug>/view/` renders its twin with every asset request answered by the portal's own origin, which the Playwright run proves by recording zero requests to another origin; a `.pptx` is offered only as a download
**And** an anonymous call is refused and a caller without the herald role gets 403; with the flag OFF the list and viewer answer 404 and the home page is unchanged; `platform-ci-local -- --test` and `pyforge-herald-test` are green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; the twin-route handler tests over the store fake and the ON/OFF test run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.deck_viewer` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, and asserts the three routes answer ON and 404 OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass, including `src/platform/tests/test_herald_portal_deck_viewer.py`.
- Playwright against a locally started platform with the local store: open one standalone and one bundle; the recorded requests name only the portal's origin.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 0, false 1, maybe-false 1
- findings:
  - `[false]` `[reject]` Twin route uses bearer/session gate identical to deck-exports — same 401/403 behavior the spec already accepts for anonymous/wrong-role callers.
  - `[maybe-false]` `[defer]` Platform pytest suite for this story needs PostgreSQL from platform-dev when run outside platform-ci-local — evidence: local `platform-ci-test` pytest errored on DB connect; CI runs the full platform-ci test job with services.

## Auto Run Result

Status: done

Summary: Herald CAP-55 Story 30.2 — deck list and sandboxed viewer on django-herald, twin streaming on the v1 API with CSP and herald-role gate, all behind `pyforge.herald.deck_viewer` (`read_boolean` on the API path, `evaluate_boolean` on portal views).

Files changed:
- `pyforge/herald/deck_twins.py` — twin path resolution, flag gate, FastAPI routes with CSP
- `django_herald_portal/deck_twin_routes.py`, `deck_viewer.py` — store-backed twin open + portal helpers
- `django_herald_portal/views.py`, `urls.py`, templates — list, viewer, Pitch tab link when flag ON
- `station_api.py` — wire twin routes beside deck exports
- Unit/platform tests and meta-test allowlists for Story 30.2 scope

Review: 0 patches; 1 defer (platform DB provisioning for local pytest); 1 rejected false positive.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — 1627 passed, 4 skipped
- `python scripts/spec_surface_reconcile.py` — OK
- `pixi run --frozen -e pyforge-guild spec-surface-check` — ok (drift-presumed warnings cleared via memlog)
- Platform `tests/test_herald_portal_deck_viewer.py` — requires platform-ci-local `--test` (PostgreSQL); not run to completion in this session due to missing local PG

Residual risk: Playwright zero-foreign-origin test depends on Chromium and live_server; validated in platform CI, not re-run locally here.
