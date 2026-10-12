---
title: '91.1: The stations index lists each station portal as mounted or absent, and why'
type: 'feature'
created: '2026-10-11'
status: 'in-review'
baseline_revision: 'e4ab638bb6276c27466ec0e7c85d55745dec08d7'
review_loop_iteration: 0
followup_review_recommended: false
review_loop_iteration: 1
landing_review: 'required'
flag:
  key: pyforge.steward.stations_index
  provider: openfeature-file
  default: {production: off, staging: off, dev: on}
  scope: global
  fallback: "today's answer: /stations/ falls through to the host's Wagtail catch-all (404 where no page has that slug), byte-identical for every client and method"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-1-the-platform-host-boots-without-herald-and-says-why.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-18-a-re-dispatched-send-back-waits-for-its-landing-review.md
  - docs/reference/story-spec-flag-block.md
  - src/platform/config/urls.py
  - src/platform/config/optional_components.py
  - src/platform/config/station_api.py
  - src/platform/config/asgi.py
  - src/platform/config/settings/base.py
  - src/shared/packages/django-pyforge/src/django_pyforge/urls.py
  - src/shared/packages/django-pyforge/src/django_pyforge/discovery.py
  - src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py
  - src/shared/packages/django-pyforge/src/django_pyforge/access.py
  - src/shared/packages/django-pyforge/src/django_pyforge/roles.py
  - src/shared/packages/django-pyforge/src/django_pyforge/flags.py
  - src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
  - src/platform/tests/test_host_boots_without_herald.py
  - src/platform/tests/test_station_portal_shells.py
  - src/platform/tests/test_openfeature_file_flags.py
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py
  - docs/tutorials/local-platform-development.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the platform host has no page that says which station portals it runs or why one is missing, and
`/stations/` answers 404.

- **Where the host mounts portals** (on `origin/main` `baf4779b6d`, 2026-10-11):
  - `src/platform/config/urls.py:40` includes `django_pyforge.urls` under `stations/`.
  - `django_pyforge/urls.py:14`-`:17` mounts one `<station_name>/` include per `PortalConfig` that
    `iter_portal_configs()` finds (`discovery.py:12`-`:16`). Nothing is mounted at the prefix itself.
  - So `/stations/` falls to the Lane 1 catch-all (`config/urls.py:142`-`:145`). Wagtail's `serve` raises a bare
    `Http404` when no page has that slug.
- **The baseline,** measured 2026-10-11 for herald Story 37.1 on a fresh test database with an anonymous client
  (`platform-ci-test`, herald present): `/` 200, `/stations/` 404, `/stations/herald/` 403, `/stations/warden/` 403,
  `/cms/` 302.
- **Why a station is missing is recorded, but nobody browsing can see it.**
  - Story 87.1's `config.optional_components.import_optional` (`:28`-`:48`) records `herald is not installed on this
    host: No module named '<name>'` when `config.station_api` seeds herald v1 at import (`station_api.py:125`-`:135`,
    `:186`-`:188`). `absent_reason()` (`:51`-`:53`) returns that string.
  - Its only reader is the station-API 404 in `config/asgi.py:142`-`:147`.
  - Only `config.asgi` imports `config.station_api` (`:56`-`:57`). A process that never imported `config.asgi`, such
    as the Django test client or `manage.py`, holds no record at all.
- **Who may see a portal.**
  - `require_station_role` (`django_pyforge/access.py:15`-`:27`) answers `HttpResponseForbidden()` (403, empty body)
    when the request's IdP roles (`roles_from_request`, `roles.py:200`) lack the station.
  - `pyforge:admin` reaches every known slug (`roles.py:132`-`:135`).
  - The chrome's switcher lists only the portals `is_switcher_tile` admits (`context_processors.py:19`-`:23`): the
    request reaches the station, and its work class is not 01 or 02.
- **The herald gate.** Herald Story 37.1 (`37-1-the-herald-portal-loads-without-herald-and-says-why`, minted
  2026-10-11, landed on `main` 2026-10-11 as PR #2134) keeps every Django page from answering 500 on a host without `pyforge-herald`. Until
  it lands, every Django page on such a host is a 500, this one included.

**The ruling (2026-10-11).**

- Asked "Keep 37.1 as written (`/` answers 200, `/stations/` gives its with-herald answer, never a 5xx)? And do you
  want a stations index page as its own steward story?", the operator chose, verbatim label "Keep 37.1; mint steward
  index (Recommended)":

  > "37.1 ships as staged. Also mint a steward feature story, behind a flag and dark in production first:
  > `/stations/` lists each station portal as mounted or absent with its 87.1 reason. Queued after 37.1."

- The operator then confirmed:

  > "lets do this - If you want /stations/ to answer 200, do it as a separate steward story: a stations index page. It
  > would list every station portal and show each one as mounted or absent with its reason, reusing steward 87.1's
  > absent-reason record. That gives operators one place to see what the host is running and why something is
  > missing. The catch: it's a new feature, so it needs a flag (dark in production at first), a Dream entry and its
  > own review. It isn't needed to fix any bug."

**Approach:**

- **Where it lives.** A host view in `src/platform/config/stations_index.py` (new). One
  `path("stations/", …, name="stations-index")` in `config/urls.py` routes to it, placed just before the `stations/`
  include. Its template, `src/platform/platformapp/templates/stations/index.html` (new), extends the chrome's
  `django_pyforge/base.html`. It lives in the host, not in django-pyforge, for three reasons:
  - with the flag OFF, the view hands the request to the host's own catch-all, `wagtail.views.serve(request,
    "stations/")`, so the answer is today's in every case, including a page published at that slug. django-pyforge
    does not depend on Wagtail, and this story adds no dependency;
  - it reads Story 87.1's record from `config.optional_components`, the host's own module;
  - `django_pyforge` stays untouched, so steward Story 74.1's rule that the chrome never imports `config` holds with no
    new settings seam.
- **The flag comes first.** The view reads `pyforge.steward.stations_index` with
  `django_pyforge.flags.evaluate_boolean(key, default=False)` on every request, before anything else. OFF, or a
  provider that is not ready, returns the catch-all's answer. There is no role check, no method check, no new import
  and no log.
- **Who sees what (flag ON).**
  - The roles are `roles_from_request(request)`. A request with no station role, anonymous included, gets the 403
    `require_station_role` gives (empty body).
  - Any other request gets 200, with one row per discovered portal that `is_switcher_tile` admits for those roles,
    ordered by `station_name`.
  - A method other than GET or HEAD gets what the same method gets on `/stations/warden/` (405, from `require_GET`).
- **Mounted or absent.**
  - On its first ON request the view loads `config.station_api` by module name (`importlib.import_module`). It never
    loads it at import of `config.urls` or of its own module. So the station API's import-time seed has run, and 87.1
    has recorded any absent station, whatever entry point the process used.
  - A row whose `absent_reason(station_name)` is set reads absent, shows exactly that string and has no link.
  - Every other row reads mounted and links to `/stations/<station_name>/`.
  - Only the recorded string is shown: never 87.1's remedy, an exception, a traceback or a path.
- **Read-only.** No model, migration, form or write. No new dependency, setting or environment variable.
- **The flag.** It is registered in the four places `docs/reference/story-spec-flag-block.md` § *Registering a flag*
  names: dev ON, staging and production OFF, so production stays dark first, as the ruling asks.
- **The docs.** The local-platform tutorial's line that lists the portals names the index and its flag.

Ledger key: `91-1-the-stations-index-lists-each-station-portal-as-mounted-or-absent-and-why`.
Type / Effort / Deps: feature / S / — (cross-station gate: herald 37.1, held as this story's `blocked` ledger row).

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-3** (Eight portals, one session). The index is the host's one view of the
  Lane 2 portals. It reads discovery, so adding or removing a portal still changes no host code outside that portal's
  own registration, as CAP-3's success clause requires. No roster is written.
- **CAP-10** (Failure is contained). The absence Story 87.1 contains becomes visible. Nothing new is skipped.
- **CAP-12** (Access is revocable). Who sees a row comes from the request's IdP roles, as for every portal page.
- **CAP-13** (Behaviour flips without a redeploy). The flag is read per request from the one tree (canopy:AD-11).
- **pap:AD-2.** `src/platform/` never imports `pyforge.*`.
- **No CAP is minted,** and no `SPEC.md` text changes. The story is `type: feature`, a new page, so it carries a flag
  under `spec-feature-flag-governance` Q1, and none of the `flag-exempt` values fits.
- **Origin.** The steward Dream's 2026-10-11 (stations index) entry.

## Acceptance Criteria

- **AC1 — the gate.** Given this story is dispatched, When its preflight reads the tree, Then herald Story 37.1 is
  `done` on `main`. Both tests hold:
  - herald's ledger row `37-1-the-herald-portal-loads-without-herald-and-says-why` reads `done`;
  - its landing is an ancestor of `origin/main` (`git merge-base --is-ancestor <37.1 landing> origin/main` exits 0).

  Otherwise the story stops and changes nothing.
- **AC2 — with the flag OFF, nothing changes.** Given the flag OFF, Then:
  - for an anonymous client and for a `pyforge:admin` session, `GET /stations/` and `OPTIONS /stations/` answer a
    status, `Content-Type` and body byte-identical to the same request against a URLconf equal to
    `config.urls.urlpatterns` minus the `stations-index` pattern (`override_settings(ROOT_URLCONF=…)`);
  - this holds on a fresh test database (404), and with a Wagtail page published at slug `stations` under the default
    site's root page (that page's answer);
  - in a fresh interpreter, after `django.setup()` and one flag-OFF `GET /stations/`, `config.station_api` is not in
    `sys.modules`, and no record is logged on 87.1's `config.optional_components` logger.
- **AC3 — who may see it.** Given the flag ON, herald present (`platform-ci-test`), and the Django test client, Then:
  - anonymous `GET /stations/` answers 403 with the body anonymous `GET /stations/warden/` gets (empty);
  - a session whose group claim carries no station role (only `pyforge:tenant:t1`) gets 403;
  - a session with only `pyforge:station:herald` gets 200 and exactly one row: herald, mounted, linking
    `/stations/herald/`;
  - a `pyforge:admin` session gets 200 and exactly the rows `is_switcher_tile` admits for its
    `roles_from_request(request)`, ordered by `station_name`. Each of the eight stations in
    `django_pyforge.events.constants.STATION_TOKENS` is among them, mounted, with its link, and `infra-probe` (work
    class 01) is not;
  - `POST /stations/` for that admin session answers the status `POST /stations/warden/` gets for it (405).
- **AC4 — an absent station reads absent, with 87.1's reason.** Given AC1, and a fresh interpreter whose meta-path
  finder refuses `pyforge.herald` and every `pyforge.herald.*` (Story 87.1's finder), run from `src/platform/` with
  `DJANGO_SETTINGS_MODULE=config.settings.test` against the parent's pytest-django test database, the flag ON, a
  `pyforge:admin` session through the Django test client, and `config.asgi` never imported, Then:
  - `GET /stations/` answers 200, and no response in this child is a 5xx;
  - the herald row reads absent and carries, as text, exactly the string
    `config.optional_components.absent_reason("herald")` returns in that process afterwards, which names `herald` and
    `pyforge.herald`. The row has no link to `/stations/herald/`;
  - every other row reads mounted, with its link;
  - after two `GET /stations/` requests, the child's combined stdout and stderr carry 87.1's reason record exactly
    once;
  - in AC3's herald-present cases, no row reads absent and `absent_reason("herald")` is `None`.
- **AC5 — nothing leaks.** No response body in ACs 2 to 4 contains:
  - 87.1's remedy text (`Install pyforge-herald on this host to enable herald routes.`);
  - the word `Traceback`;
  - `sys.prefix`, or `str(settings.BASE_DIR)`.

  AC3's 403s carry an empty body.
- **AC6 — read-only, with no new dependency.**
  - During a flag-ON request, `django.test.utils.CaptureQueriesContext` records no `INSERT`, `UPDATE` or `DELETE`.
  - The story's diff touches no `pixi.toml`, `pixi.lock`, `environment.yaml`, `pyproject.toml` or `migrations/` path.
  - `python manage.py makemigrations --check --dry-run` exits 0 in `platform-ci-test`.
- **AC7 — the import boundary is pinned where the gate runs.** Given `pixi run --frozen -e pyforge-steward
  pyforge-steward-test`, Then:
  - it includes a new meta-test, `src/shared/packages/pyforge-steward/tests/meta/test_stations_index_boundaries.py`,
    which reads `src/platform/config/stations_index.py` and `src/platform/config/urls.py` with `ast` and never imports
    them;
  - the meta-test fails if either file imports any of these at module scope (including inside a module-level `if`,
    `try` or `with`): `pyforge` or a `pyforge.*` module; a station portal package (the module names in
    `config/settings/base.py`'s `_STATION_PORTAL_PACKAGES`, read with `ast`); or `config.station_api`;
  - it passes on the finished tree;
  - `test_object_store_seam_boundaries.py` passes unedited: there is no new `pyforge.*` importer under
    `src/platform/`, and `django_pyforge` still imports no `config`.
- **AC8 — the flag is registered, and both states are tested.**
  - `pyforge.steward.stations_index` is in `src/platform/config/flags.json` (metadata owner `steward`, story the ledger
    key, created `2026-10-11`) and in `src/platform/config/flag-overlays.json` (`dev` on, `staging` off, `production`
    off).
  - It is in `src/shared/packages/pyforge-core/tests/unit/test_flags.py` and in
    `src/platform/tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`).
  - `src/platform/tests/test_stations_index.py` writes one flagd tree with the key `"on"` and one with it `"off"`
    through the FILE provider, and asserts AC3's 200 and AC2's answer respectively.
  - `flag-gate-check` exits 0, and `flag-gate-check -- --spec <this spec>` returns `pass`.
  - `docs/governance/flag-inventory/` is regenerated by `flag-inventory` only.
- **AC9 — mutations fail the tests.** Each of these is expected to fail a named test, and each is restored
  afterwards:
  - checking the roles or the method before the flag fails AC2's anonymous or `OPTIONS` case;
  - answering OFF with a bare `Http404` instead of the catch-all fails AC2's published-page case;
  - answering 200 to a request with no station role fails AC3;
  - reading `absent_reason` without loading `config.station_api` fails AC4 (herald reads mounted);
  - loading `config.station_api` at module scope fails AC7 and AC2's `sys.modules` check;
  - rendering the remedy or the exception text fails AC5.
- **AC10 — the docs name it.** `docs/tutorials/local-platform-development.md`, where it lists the station portals
  (`:59` on `baf4779b6d`), names the index at `http://localhost:8000/stations/`, its flag, and that dev has it ON.
  `pixi run -e pyforge-guild docs-currency-check` exits 0.
- **AC11 — reconcile, review, land.**
  - Every Spec `pixi run -e pyforge-guild spec-surface-check` names gets a dated memlog entry naming its paths and the
    reason, and a scoped stamp (`--spec <project>/<spec>`, after `git add`, from a clean tree). The check exits 0. The
    detector decides the set. On `baf4779b6d` the baseline names `spec-pyforge-unifying-strategy` for
    `src/platform/config/`, `platformapp/templates/` and `src/platform/tests/`, `spec-pyforge-steward` for
    `src/platform/tests/` and steward's package, `spec-pyforge-doctor` for the tutorial, and `spec-pyforge-core` and
    `spec-pyforge-marshal` for `test_flags.py`.
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test` passes. `pixi run -e pyforge-guild platform-ci-local --
    --test` and `pixi run --frozen -e pyforge-guild lint-types` exit 0.
  - The PR carries the `maintenance` label.
  - The landing stops at a draft PR (`landing_review: 'required'`, dispatched with `--hold-landing`) until an
    independent review against this spec passes.
  - On landing, the ledger key becomes `done` through the Tier-3 feed and `sprint-ledger-sync`.

## Boundaries & Constraints

**Always:**
- Check the gate (AC1) before touching any file.
- Change only these paths:
  - `src/platform/config/stations_index.py` (new) and `src/platform/config/urls.py` (one `path` and its import);
  - `src/platform/platformapp/templates/stations/index.html` (new);
  - `src/platform/config/flags.json` and `src/platform/config/flag-overlays.json`, for the flag;
  - `src/platform/tests/test_stations_index.py` (new), and `src/platform/tests/test_openfeature_file_flags.py`
    (`_SHIPPED_BOOLEANS` only);
  - `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, for the flag only;
  - `src/shared/packages/pyforge-steward/tests/meta/test_stations_index_boundaries.py` (new);
  - `docs/tutorials/local-platform-development.md`, the one line of AC10;
  - `docs/governance/flag-inventory/`, through `flag-inventory` only;
  - the memlogs of the Specs `spec-surface-check` names, and `scripts/.spec-surface-baseline.json`.
- Read the flag first, on every request. Load `config.station_api` only inside the ON branch.
- Take the rows from `iter_portal_configs()`, who sees them from `roles_from_request` and `is_switcher_tile`, and the
  reasons from `config.optional_components.absent_reason`.
- Run every pixi task from the repo root, and read every verdict from its exit code, never through a pipe.

**Never:**
- Never write `import pyforge` or `from pyforge` anywhere under `src/platform/`, comments included.
- Never edit `src/shared/packages/django-pyforge/**`, any station portal package, `config/optional_components.py`,
  `config/station_api.py`, `config/asgi.py` or `config/settings/**`.
- Never keep a list of stations in the host. The rows come from discovery.
- Never show a row for a station the request cannot reach, and never answer 200 to a request with no station role.
- Never show 87.1's remedy, an exception, a traceback or a filesystem path.
- Never change `/stations/<name>/`, any portal's answer, the switcher, or 87.1's record or log.
- Never add a model, migration, dependency, setting or environment variable.
- Never turn the flag ON in staging or production.
- Never hand-edit `SPEC.md`, the PRD, the spine or `sprint-status-ledger.yaml`. Never edit herald's code, specs or
  ledger.

## I/O & Edge-Case Matrix

| Flag | Request | State | Expected output | Error handling |
|------|---------|-------|-----------------|----------------|
| OFF | any client, `GET` or `OPTIONS /stations/` | no page at slug `stations` | today's 404 from the catch-all, byte-identical | nothing new imported or logged |
| OFF | any client | a Wagtail page published at `stations` | that page's answer, byte-identical | none |
| not ready | any client | provider not ready | read as OFF (`default=False`) | none |
| ON | anonymous | — | 403, empty body, as `/stations/warden/` | none |
| ON | session with no station role | — | 403, empty body | none |
| ON | `pyforge:station:herald` only | herald present | 200; one row, herald mounted, link `/stations/herald/` | none |
| ON | `pyforge:admin` | herald present | 200; every switcher tile, by station name, all mounted | none |
| ON | `pyforge:admin` | herald absent (after 37.1) | 200; herald absent with 87.1's reason and no link; the rest mounted | 87.1's WARNING once per process |
| ON | `POST /stations/` | any role | what `POST /stations/warden/` gets (405) | none |
| ON | `pyforge:admin` | herald installed, one of its own dependencies missing | the import error propagates, as 87.1 does for the host | not swallowed: only a missing component is skipped |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-unifying-strategy` CAP-3 (the portals), with CAP-10 (the absent reason),
  CAP-12 (who sees a row) and CAP-13 (the flag). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (stations index) entry.
- Architecture: pap:AD-2 and canopy:AD-11, unchanged.
- Epic: Epic 91 (new). Epic 87 holds fixes that let the host boot without an optional engine, and this is a feature
  page, so it opens its own epic. `epic-91` and `epic-91-retrospective` are minted with it.
- Ledger key: `91-1-the-stations-index-lists-each-station-portal-as-mounted-or-absent-and-why`.
- Ledger status at mint: `blocked`. It is a cross-station gate: herald Story 37.1
  (`37-1-the-herald-portal-loads-without-herald-and-says-why`) must be `done` on `main` first. The operator
  pre-authorised the queue ("Queued after 37.1"), and flips the key to `backlog` and this spec to `ready-for-dev` once
  37.1 is `done` on `main`.
- Deps: — (cross-station, see above). Marshal's `Deps:` parser is station-local, so the gate is this ledger row.
- Landing: held for an independent review by marshal Story 83.18's mechanism (`landing_review: 'required'` above, and
  `--hold-landing` at dispatch), released only after that review passes.
- Precedent: Story 87.1's absent-reason record and its meta-path finder. Story 85.5 is a flagged feature minted
  `blocked` on another station's story.
- Spec: the `spec-pyforge-unifying-strategy` memlog records the ruling, the confirming text, the design decisions and
  this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."91"` (added with this mint) holds every path in the Always list.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, with the AC7 meta-test (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0, including `src/platform/tests/test_stations_index.py` and the unedited `src/platform/tests/test_station_portal_shells.py` and `src/platform/tests/test_host_boots_without_herald.py`.
- `src/platform/tests/test_stations_index.py` — the two-state flag test for `pyforge.steward.stations_index`: one flagd tree `"on"`, one `"off"` (AC8).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `pixi run --frozen -e pyforge-guild flag-gate-check -- --spec <this spec>` — expected: exit 0 and `pass`.
- `pixi run -e pyforge-guild docs-currency-check` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The six mutations of AC9 — expected: each fails its named test.
- `git diff origin/main...HEAD -- src/platform` searched for `import pyforge` and `from pyforge` — expected: no match; `git diff origin/main...HEAD -- src/shared/packages/django-pyforge` — expected: empty.
- AC11: the run's journal holds a `dispatch-land` verdict `held-for-review`, and the PR stays a draft until the independent review's passing entry is recorded in this spec's Review Triage Log.

## Spec Change Log

- 2026-10-11: minted from the operator's ruling "Keep 37.1; mint steward index (Recommended)" and the confirming text
  that asks for a flag, a Dream entry and its own review. `type: feature` behind `pyforge.steward.stations_index` (dev
  ON; staging and production OFF). Minted `blocked` on herald Story 37.1, with `landing_review: 'required'`.

## Review Triage Log

### 2026-10-11 — Verify-fix completion (implementer)

Implementer session on 850a1fda6c: 00281fa91b, which holds the killed verify-fix turn's edits, merged with origin/main. One file changed, `src/platform/tests/test_stations_index.py`. The view, template, URLconf, flag files and every other path are untouched.

- **Root cause.** `test_flag_on_herald_absent_lists_reason_once` asserted that 87.1's remedy text is absent from the child's whole combined stdout and stderr. The host log carries that text by design, on two records:
  - 87.1's own WARNING on `config.optional_components`, since `import_optional` logs `"%s %s", reason, remedy`;
  - herald 37.1's WARNING on `django_herald_portal`.

  AC5 forbids the remedy in response bodies only, and Boundaries forbid changing 87.1's record or log. So the assertion contradicted the spec, and the implementation was right. The child also never checked AC5 on any response body.
- **Why it surfaced now.** Herald 37.1 was already in this story's base (e4ab638bb6), and the origin/main merge brought nothing under `src/platform/`. The test never passed in this form: the dispatch's verify stopped at the Ruff step (I001) before the full suite ran.
- **AC4 and AC5: `test_flag_on_herald_absent_lists_reason_once` (`:451`).**
  - The child (`_build_herald_absent_index_child`, `:368`) now only gathers facts. It makes two admin GETs, then prints one marker line holding both statuses, both bodies, `absent_reason("herald")`, and whether `config.asgi` was imported.
  - The fix turn's half-done edits are gone: the `html` and `re` imports, the regex over `<tbody>`, the in-process log handler, and an unused `json` import. Every child import is now used.
  - The parent asserts each of these:
    - `config.asgi` was never imported (AC4's precondition);
    - the statuses are `[200, 200]`;
    - the reason names `herald` and `pyforge.herald`;
    - AC5 holds on both bodies (`:495`): no remedy, no `Traceback`, no `sys.prefix`, no `BASE_DIR`;
    - herald's row is exactly herald / absent / the reason / no link (`:500`);
    - every other row reads mounted with its own link, and the seven other `STATION_TOKENS` are among them;
    - the combined output carries exactly one JSON record on logger `config.optional_components` whose event holds the reason (`:515`).
  - That last count is 87.1's record, counted by logger name. Herald's portal record is neither counted nor forbidden.
  - The child env pins the existing settings `DJANGO_LOG_FORMAT=json` and `DJANGO_LOG_LEVEL=WARNING`, so each record is one parseable line whatever the caller's env.
- **AC3: row order (`test_flag_on_admin_lists_switcher_tiles`, `:273`).**
  - The fix turn's `re.findall(r"<tr>\s*<td>([^<]+)</td>", …)` read only the first cell and checked no state or link. It broke on a `<tr>` attribute, and on a reformatted cell because it captured the whitespace.
  - Rows now come from `_index_rows` (`:136`), a stdlib `HTMLParser` over `<tbody>`. It returns each cell's text with entities decoded and the edges stripped, plus the row's link targets.
  - The test asserts `listed == expected_names` (`:292`): exactly the rows `is_switcher_tile` admits for the admin's `roles_from_request`, in sorted `station_name` order. It also asserts that `STATION_TOKENS` is a subset of `listed`, that `infra-probe` is not in it, and that every row is `mounted` with exactly `(/stations/<name>/,)`.
  - These row checks replace the body-wide `count("mounted")` and `in body` checks.
- **Mutations.** Each was applied to `config/stations_index.py` or `templates/stations/index.html`, then restored byte-identical (sha256 checked) with HEAD still at 850a1fda6c:

  | Mutation | Test that fails |
  |---|---|
  | reason rendered twice | `test_flag_on_herald_absent_lists_reason_once`, the herald-row check (`:500`) |
  | reason omitted (`<td></td>`) | same test, `:500` |
  | remedy rendered after the reason | same test, the AC5 check (`:495`) |
  | `importlib.import_module("config.station_api")` removed | same test (the reason is `None`) |
  | the view logs the reason on `config.optional_components` on every request | same test, the record count (`:515`) |
  | rows sorted in reverse | `test_flag_on_admin_lists_switcher_tiles` (`:292`) |
- **Not changed.**
  - `spec-surface-check` named no drift: both governing memlogs have already moved and name this file. So there is no memlog entry and no stamp.
  - The frontmatter's duplicate `review_loop_iteration` key is the harness's shape across the estate and is left as written.
- **Gates, all run after the last source edit:**
  - `pyforge-steward-test`: 0 (2320 passed, 3 skipped);
  - `lint-types`: 0;
  - `platform-ci-local -- --test`: 0 (7 of 7 steps; full suite 1222 passed, 13 skipped);
  - `spec-surface-check`: 0, also re-run after this entry;
  - `detectors-ci`: 0;
  - `flag-gate-check`: 0, and `flag-gate-check -- --spec <this spec>` returns `pass`;
  - the test file alone, against a private PostgreSQL: 14 passed.

Status stays `in-review`, and the landing stays held for the independent review.

### 2026-10-11 — Review pass
- verdicts: 12 findings — high 0, medium 1, low 0, false 0, maybe-false 0, reject 11
- findings:
  - `[medium]` `[patch]` Admin stations index row order was not asserted — extended `test_flag_on_admin_lists_switcher_tiles` with monotonic `body.index(name)` over sorted `expected_names`.
  - `[reject]` `[defer]` Template lacks operator intro copy — AC does not require prose beyond table; out of intent scope.
  - `[reject]` `[defer]` Tutorial omits 403 access rules — AC10 names URL, flag, and dev ON only.
  - `[reject]` `[defer]` Tutorial omits “and why” phrasing — sufficient for AC10 line scope.
  - `[reject]` `[defer]` “Detail” column legend — cosmetic; no AC.
  - `[reject]` `[defer]` Empty rows table state — no role admits zero switcher tiles for admin in practice.
  - `[reject]` `[defer]` Estate overview not updated — not in story Always list.
  - `[reject]` `[defer]` Flag cleanup_by empty — matches existing steward flags pattern; Q4 cleanup is operational follow-up.
  - `[reject]` `[defer]` Spec frontmatter missing updated date — planning hygiene only.
  - `[reject]` `[defer]` No in-product link to index — not in AC.
  - `[reject]` `[defer]` Flag-inventory regen includes unrelated rows — flag-inventory task regenerates all station reports at current SHA.
  - `[reject]` `[defer]` Diff includes baseline hash churn outside 91.1 paths — scoped stamps touch co-governor surfaces only.

## Auto Run Result

Status: in-review (landing held)

Summary: Host `/stations/` index behind `pyforge.steward.stations_index` lists switcher-visible portals as mounted (link) or absent (87.1 reason). Flag OFF delegates to Wagtail unchanged.

Files: `config/stations_index.py`, `config/urls.py`, template, flags + overlays, platform and steward tests, tutorial, flag-inventory regen, spec-surface memlogs and baseline stamps.

Review: 1 medium patch (row-order test); 11 deferred/rejected doc/UX items outside AC.

Follow-up review recommended: false

Verification: `platform-ci-local --test` PASS; `pyforge-steward-test` 2321 passed; `lint-types` PASS; `flag-gate-check` ok; `python scripts/spec_surface_reconcile.py` exit 0; `spec-surface-check` ok; AC1 37.1 merge on `origin/main` verified.

Residual: Independent landing review required (`landing_review: required`); draft PR only.
