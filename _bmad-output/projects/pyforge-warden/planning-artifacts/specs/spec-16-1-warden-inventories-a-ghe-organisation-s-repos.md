---
title: "16.1: Warden inventories an operator-designated GitHub organisation's repos"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: 'e0d12c1d4ec1d22ec49fd0d6f72e12025462900f'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/django-warden/src/django_warden_fabric/models.py
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet.py
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py
  - src/platform/db/README.md
flag:
  key: pyforge.warden.fleet_inventory
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "no fleet inventory exists; the inventory action is listed as disabled and refuses"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Re-scoped 2026-10-11 (operator rulings; the `spec-pyforge-warden` memlog records them verbatim, with the target's
names redacted).** The inventory reads an operator-designated organisation on github.com, not a GitHub Enterprise host.
github.com is now the designated host, not a stand-in. The rulings supersede the 2026-10-10 condition "It does not
improvise a host, a token, a github.com stand-in or a mock presented as live" in its host clause only; its other
clauses still hold (below). Three rulings:
- **Scope:** every repo of the operator-designated github.com organisation. The items of its operator-designated
  GitHub Projects are Story 16.5 (Deps S-16.1), which reads the same config and the same credential.
- **Naming:** this repository is public. No tracked file names the organisation, its repositories or its projects:
  not this spec, a memlog, a test, a fixture, a doc, a log left in the repo, a commit message or a PR body. They say
  "the operator-designated github.com organisation". The names live only in a gitignored local config, the export is
  gitignored and never committed, and tests use fictional fixtures (organisation `example-org`).
- **Credential:** the live run reads through the operator's existing `gh` login at run time. The operator named its
  scopes as `repo`, `read:org` and `read:project`. No token is copied into `steward keys`, an env file or any other
  file.

**What the re-scope changes.**
- **Host.** The GitHub REST API at `https://api.github.com`: `GET /orgs/{org}/repos?type=all&per_page=100`, following
  the `Link: rel="next"` header until no next page remains.
- **Target.** The organisation name comes from a gitignored local config, `.warden/fleet-target.toml`
  (`[github] organisation = "..."`; Story 16.5 reads `projects` from the same file). `WARDEN_FLEET_TARGET_CONFIG`
  overrides the path. This story adds `.warden/` to `.gitignore` in the same change, before anything is written there.
- **Credential seam.** It fits warden's injectable-client design, the actuator's `resolve_forge` → `GitHubForgeClient`
  pair (`actuator.py:325`, `:351`):
  - A credential provider runs `gh auth token --hostname github.com` once per inventory task, in the worker. It
    passes an argv list with no shell, captures stdout, and never logs it.
  - It hands the token to a stdlib-`urllib` listing client, which holds it in memory for that run only.
  - Both are injectable, so the suite injects a fake provider and a fixture client, and never runs `gh` or opens a
    socket.
  - Calling `gh api` once per page was the alternative. It was not chosen because pagination and the GET-only check
    then stay warden's own code, testable against a fixture client.
- **Read-only by construction.** GitHub's classic `repo` scope is not read-only, so the client enforces it. It issues
  `GET` only, and refuses any other method before a socket opens.
- **Steward Story 75.1 is no longer this story's credential path.** This story does not need
  `steward keys exec --scope ghe-fleet-read` (`GH_HOST`, `GH_ENTERPRISE_TOKEN`). 75.1's code stays on main and nothing
  here removes it, so a later GitHub Enterprise target can still use it.
- **Export.** One JSON document at `WARDEN_FLEET_INVENTORY_PATH`, default `.warden/fleet-inventory.json` (gitignored).

**The 2026-10-10 conditions, re-read under the rulings.**
- A live run needs the operator's own read credential: still holds, and it is now the operator's `gh` login. If
  `gh` has no github.com login, or the config is absent, the dispatch stops and reports. It does not improvise an
  organisation, a token or a mock presented as live. github.com as the host is no longer an improvisation.
- The build and its suite need no live host: still holds. The ACs run against a fictional fixture organisation behind
  the injectable client.
- The dispatch never writes to any repository outside `rxm7706/local-recipes`, and steward Story 85.8's outward guard
  (PR #2021) stays on: still holds. The inventory writes nothing to GitHub at all.

**History (kept for the record; superseded where the re-scope above says so).**
- *Minted `blocked` 2026-09-28* on steward Story 75.1 (the GHE host credentials).
- *Gate cleared 2026-10-10.* 75.1 is `done` on main (PR #1664, merge `b106386842`, an ancestor of `origin/main`). The
  operator ruled "yes flip the six cleared stories and dispatch them"; the key moved `blocked -> backlog` through a
  worktree-local Tier-3 feed and `sprint-ledger-sync --project warden --allow-regression`.
- *Since minting (re-read 2026-10-10; Story 16.2 landed first, PR #1974, merge `868eb82717`).* These notes still hold:
  - **`FleetRepo` already exists** at `django_warden_fabric/models.py:54`, with this story's fields (organisation,
    full name, default branch, clone URL, archived, last-seen) and the unique (organisation, full name) constraint. It
    shipped in `migrations/0002_fleet_run.py`, covered by changeset 22
    (`python-agent-platform-22-warden-fabric-0002-fleet-run.sql`, `sqlmigrate-map.yaml:28`). This story adds a
    migration and its covering changeset only if it changes the model (the next number is `0004`).
  - **`fleet.py` exists** with 16.2's clone helpers. This story adds the organisation listing and the credential
    provider to it.
  - **A reader of the export already exists** (atlas Story 25.2, PR #1882). `parse_fleet_inventory`
    (`pyforge-atlas/src/pyforge/atlas/orchestration/fleet_inventory_sensor.py:50`) reads
    `{"repos": [{"full_name": ..., "head_sha": ...}]}` and treats a repo without `head_sha` as malformed. This story's
    AC lists full name, default branch and clone URL, with no head SHA. Whether the export also carries each default
    branch's head SHA is still an open question for the operator; the 2026-10-11 rulings did not answer it. The
    dispatch builds the AC as written, reports the mismatch, and does not change atlas's parser.
  - **The flag reader and fixture are in place:** `pyforge.core.flags.read_boolean` (steward 75.1) and
    `pyforge.testing_kit.flags` (marshal Story 74.1).
  - The 2026-10-10 note "How 75.1 delivers the credential" is superseded by the credential seam above.

**Problem:** Warden scans one repo per invocation and has no notion of a fleet. The operator ruled on 2026-09-28 that
Warden scans the fleet, lifting the Non-goal "Fleet aggregation". A fleet run's first need is the list of repos, and
other stations need it too (Atlas's dependency history, `spec-pyforge-atlas:CAP-61`). On 2026-10-11 the operator
designated the fleet: a github.com organisation, named only in a gitignored config.

**Approach:** In `django_warden_fabric` (spine § Currency reconciliation — 2026-09-28, Decision 2), `fleet.py` gains
two seams:
- the credential provider above;
- a listing client that pages `GET /orgs/{org}/repos` (GET only).

A keys-not-blobs Celery task:
1. reads the organisation from the gitignored config;
2. takes the credential once;
3. upserts `FleetRepo` rows idempotently;
4. writes the inventory as one JSON document at `WARDEN_FLEET_INVENTORY_PATH`, atomically (a temporary file in the
   same directory, then a rename), so a failed run leaves no partial export.

The export is the only face other stations read; nobody imports `django_warden_fabric` or `pyforge.warden` for it.
The inventory action is a portal button and a `warden_fleet_inventory` management command on one code path. It reads
the flag through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); OFF, it is listed as disabled and
refuses.

Ledger key: `16-1-warden-inventories-a-ghe-organisation-s-repos` (kept on the 2026-10-11 re-scope; the key is an
identifier, and its `ghe` is historical).
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / — (steward Story 75.1 no longer required, 2026-10-11).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) and CAP-16 (the service skeleton, keys-not-blobs). CAP-26's `SPEC.md` text
  still says "a GitHub Enterprise organisation" and "GHE credentials come from Steward (steward Story 75.1)". For this
  story and Story 16.5 the 2026-10-11 decision entries in the Spec memlog govern where the two differ, until `bmad-spec`
  re-derives `SPEC.md`.
- `spec-pyforge-atlas:CAP-61` (reads the export); `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture organisation `example-org` of three repos behind the injectable listing client, When the inventory
  task runs, Then three `FleetRepo` rows exist and the export lists the same three repos with full name, default
  branch and clone URL
- Given the same organisation listed twice, When the task runs again, Then the rows are updated in place, not
  duplicated, and the export is rewritten whole
- Given a paginated listing, When it spans pages through `Link: rel="next"`, Then every page is read
- Given the Celery message, When it is inspected, Then it carries only ids and the organisation name (keys-not-blobs),
  never a token or an `Authorization` header
- Given no `gh` binary, a `gh` with no github.com login, or a missing config or a config with no `organisation`, When
  the task runs, Then it fails with a typed error. The error names what is missing: the binary, the login, or the
  config path and key. It never echoes a token, and no partial export is written
- Given the inventory run against the fixture with a recording client, When every request is inspected, Then each is a
  `GET`. A test drives a `POST`, `PUT`, `PATCH` and `DELETE` through the default client and asserts each is refused
  before a socket opens
- Given a fake credential provider that returns a sentinel token, When a run ends in success and when it ends in
  failure, Then the sentinel appears in no log record, Celery message, model field, error text or export
- Given the default config path `.warden/fleet-target.toml` and the default export path `.warden/fleet-inventory.json`,
  When `git check-ignore` is asked about each, Then both are ignored (a test pins it)
- Given the gitignored config present locally, When the leak-guard test runs, Then it finds neither the
  `organisation` value nor any term in its optional `leak_guard_terms` list in the tracked files of the paths the fleet
  stories write: `_bmad-output/projects/pyforge-warden/`, `src/shared/packages/django-warden/`,
  `src/shared/packages/pyforge-warden/`, `src/platform/`, `docs/dreams/pyforge-warden.md` and `.gitignore`. The test
  matches case-insensitively on a fixed string, and skips, naming why, when the config is absent (CI)
- Given the operator's `gh` login and the gitignored config, When the operator (or the dispatch, reading through that
  login) runs the inventory live, Then the export lands only under the gitignored path, `git status --porcelain` is the
  same before and after the run, and no write request reaches GitHub
- Given the flag OFF, When the operator opens the portal or runs the management command, Then the action is listed as
  disabled and refuses (the command exits 2, warden's usage code)

## Boundaries & Constraints

**Always:**
- Live in `django-warden`; the `pyforge.warden` scan process gains no socket.
- Take the credential at run time from the operator's `gh` login through the injectable provider, and hold it in
  memory for that run only. Never write it to an env file, a model field, a flag, the Celery message, the export, a
  log line or error text.
- Read the organisation only from the gitignored config. Add `.warden/` to `.gitignore` in this story's change,
  before any file is written there.
- Issue `GET` requests only, against the GitHub REST API.
- Use fictional fixtures only (`example-org`, invented repo names).
- Change the model only if the fields above need it; then ship the migration (`0004`) with its covering Liquibase
  changeset, and `platform-ci-local -- --test` green.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree
  (canopy:AD-11). Add the key to `src/platform/config/flags.json` (default OFF) and its overlay rows. The portal view
  runs inside the host, where `pyforge` may be absent; there, and only there, it evaluates the same key through
  `django_pyforge.flags`, the Guild's other sanctioned reader.
- Reconcile every Spec `spec-surface-check` names for the touched paths (`django-warden` and `src/platform/` are
  co-governed by steward's `spec-pyforge-unifying-strategy`); scoped stamps only.

**Never:**
- Clone or scan here (Story 16.2).
- Call any method but `GET`, or any GitHub write endpoint.
- Name the operator-designated organisation, its repositories or its projects in a tracked file, a test, a fixture, a
  commit message or a PR body. Never commit the config or the export.
- Copy the token into `steward keys`, an env file or any other file.
- Reach GitHub, or run `gh`, from the test suite.
- Add a webhook, a FastAPI or SQLAlchemy service, or a gitgres store.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| three repos | fixture `example-org` | three rows, three-entry export | — |
| re-run | same org | rows updated, no duplicates, export rewritten | — |
| two pages | `Link: rel="next"` on page 1 | both pages read | — |
| archived repo | `archived: true` | row kept, flagged archived | — |
| no `gh` | binary absent | no export | typed error naming `gh` |
| no login | `gh auth token` exits non-zero | no export | typed error naming the github.com login |
| no config | `.warden/fleet-target.toml` absent | no export | typed error naming the path and `organisation` |
| non-GET | a `POST` through the client | refused before a socket opens | typed refusal |
| API 5xx or rate limit | listing fails | no partial export | job `failed` with the error, no token in it |
| flag OFF | key off | action disabled | refuses, exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43); the 2026-10-11 memlog decisions govern its host and
credential wording for this story.
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet* and *2026-10-11 — Ruled: the fleet is an operator-designated github.com organisation, read through the operator's `gh` login, and never named in a tracked file*.
Ledger key: `16-1-warden-inventories-a-ghe-organisation-s-repos`.
Ledger status at mint: `blocked` — until steward Story 75.1 (GHE host credentials) is `done`; the operator flips the row. Flipped `blocked` → `backlog` 2026-10-10 by the operator's ruling (75.1 `done`), through the Tier-3 feed and `sprint-ledger-sync --project warden --allow-regression`. Re-scoped 2026-10-11 by the operator's rulings; key and status unchanged.
Deps: — (steward Story 75.1 no longer required, 2026-10-11).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass. The `django-warden` tests live under
  `src/platform/tests/` (`src/platform/tests/test_warden_fleet_inventory.py`); a covering changeset passes
  `sqlmigrate-extraction` if the model changed.
- `pixi run -e pyforge-guild python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md`
  — expected: `pass`.
- `git check-ignore -q .warden/fleet-target.toml` — expected: exit 0.
- `git check-ignore -q .warden/fleet-inventory.json` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

**Manual checks:**
- Flag ON/OFF: `src/platform/tests/test_warden_fleet_inventory.py` writes the trees with
  `pyforge.testing_kit.flags.flagd_tree` and parametrizes with `flag_states` over `pyforge.warden.fleet_inventory`. ON
  runs the inventory; OFF lists the action as disabled and refuses with exit 2.
- Live run, by the operator or by the dispatch reading through the operator's `gh` login (never a token pasted
  anywhere): with the gitignored config in place, run `warden_fleet_inventory`. Expected: the export lands under
  `.warden/`, `git status --porcelain` is identical before and after, and nothing from the run is staged. If `gh` has no
  github.com login or the config is absent, stop and report.

## Named, not fixed here

- **A live fleet run (Story 16.2, done) and an approved proposal (Story 16.3, done) need a credential decision of
  their own.** 16.2 clones with the credential its worker's environment carries, and 16.3 opens through the actuator's
  forge credential. The 2026-10-11 rulings cover this read-only inventory and 16.5's project items only. Cloning the
  designated organisation's private repos, or opening any PR there, is not ruled.
- **Atlas's `head_sha`** (above): an open operator question.

## Spec Change Log

- 2026-09-28: minted `blocked` on steward Story 75.1 (GHE host credentials).
- 2026-09-28: amended — the flag reader is `pyforge.core.flags.read_boolean` (steward Story 75.1's contract).
- 2026-10-10: gate cleared; `ready-for-dev`; ledger `blocked -> backlog` by operator ruling. The operator's
  conditions were recorded, and the notes re-read against Stories 16.2 and 75.1 and atlas 25.2. No AC changed.
- 2026-10-11: re-scoped by the operator's rulings. The host is an operator-designated github.com organisation
  (superseding the 2026-10-10 "no github.com stand-in" clause). The credential is the operator's `gh` login at run
  time; steward 75.1's `keys exec` path is no longer required. Tracked files never name the target, and the config and
  export are gitignored.
  - Title changed; key, status, type, effort and flag unchanged; Deps no longer names 75.1.
  - ACs rewritten: the fixture organisation is `example-org`; the missing-credential AC now covers `gh` and the config.
  - ACs added: GET-only, token never persisted, gitignored paths, leak guard, live run.
  - The items of the operator-designated GitHub Projects split out to Story 16.5.
- 2026-10-11: placement deviation recorded (review iteration 1, M3). The Approach puts both seams in `fleet.py`; the
  build put the GET-only listing client in `pyforge.warden.fleet_github_rest` (the platform's
  `test_portal_raw_http_to_a_service_is_review_blocking` refuses raw HTTP imports in `django_warden_fabric`), and the
  credential provider, config reader, export writer and sync in `django_warden_fabric.fleet_inventory`; `fleet.py`
  keeps only the flag key. The client owns the repo, skipped-entry and listing types; the fabric reads them
  structurally, so the portal still imports without `pyforge`. The export gains an additive `skipped` list (each
  listing entry not inventoried, with its reason); atlas reads only `repos`. Default `.warden/` paths resolve from the
  checkout root, not the cwd. No AC changed.

## Review Triage Log

### 2026-10-11 — Independent review, iteration 2: sent back (1 major, 5 minor)

Fresh separate agent, review of `git diff origin/main...HEAD` at cd7f627c51. Every iteration-1 item (F1-F5, M1-M9, X1-X3) is closed: 18 client mutations and 24 of 26 platform mutations caught. Confidentiality holds (only fictional identifiers; nothing under `.warden/` read; no network, no `gh`). Gates: `pyforge-warden-test` 0 (2323 passed), `lint-types` 0, `spec-surface-check` 0, `detectors-ci` 0, `platform-ci-local -- --test` 0 (1236 passed, 14 skipped), flag gate `--spec` 0.

- `[major]` `[patch]` N1 (security, AC7) `fleet_github_rest.py:221-232` `_get_json` catches only `HTTPError`/`URLError`. urllib's `do_open` wraps only `h.request()`, so errors from `h.getresponse()` (read timeout, `RemoteDisconnected`, `ConnectionResetError`, SSL errors) and from `response.read()` (`IncompleteRead`, timeout) escape untyped, and their traceback keeps `do_open`'s `headers` local holding the bearer token; the task's `except` (`tasks.py:145`) misses them. Proven offline in eager mode with the production JSON renderer: the sentinel token appears in the `django.request` and `django_structlog` error lines, and in the DEBUG 500 body. Fix: catch `(OSError, http.client.HTTPException, ValueError)` around open and read, re-raise as the typed client error `from None`; unit and platform tests for a read timeout, a reset during `getresponse` and `IncompleteRead` during `read`, each asserting a typed error and no token in rendered locals, logs or the DEBUG 500 body.
- `[minor]` `[patch]` N2 `fleet_inventory.py:147-155` deleting `timeout=` from `_run_gh`'s `subprocess.run` survives (the conftest guard always replaces `_run_gh`); test the real `_run_gh` against a harmless sleeper with a tiny timeout.
- `[minor]` `[patch]` N3 `src/platform/conftest.py:89-93` removing the teardown `pytest.fail` survives; pin the "swallowed refusal still fails" claim (pytester or equivalent).
- `[minor]` `[patch]` N4 `fleet_inventory.py:309-312` `scrub_token_from_text` has no callers; remove it.
- `[minor]` `[patch]` N5 `fleet_inventory.py:132-133` a non-list `leak_guard_terms` (e.g. a bare string) is silently ignored; raise the config error instead.
- `[minor]` `[patch]` N6a `views.py:212` returns `str(exc)` with the absolute config path to portal users as a 400; return a fixed message and log the detail.
- `[minor]` `[defer]` N6b `persist_fleet_repos` never retires rows for repos deleted or renamed upstream, and Story 16.2 clones those rows. Retirement semantics are a behaviour change for 16.2's fleet run; recorded as a warden deferred-work row, not fixed here.
- Info N7: the Auto Run Result section still describes the first pass (refresh it); the task lazy-imports `pyforge.warden.fleet_github_rest` (recorded in the Spec Change Log); one branch commit subject begins "Story 16.1:" (harmless: every other station's 16.1 key is already `done`).

Send-back: N1-N6a in one pass, N6b as a deferred-work row; a fresh independent review (iteration 3) gates the landing.

### 2026-10-11 — Fix pass for iteration 1 (implementer)

Implementer pass on the send-back below; not a review verdict (iteration 2 judges it). Fictional identifiers only
(`example-org`, `evil.example`); no network, no `gh`, no `.warden/` read. Mutation proof for each fix: reverted in
place, the named test(s) went red, the fix restored byte-identical (checked with `cmp`), the test(s) green again.
Below, `R` is `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`, `U` is `src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py`, `P` is `src/platform/tests/test_warden_fleet_inventory.py` and `F` is `django_warden_fabric/fleet_inventory.py`.

- F1: Authorization is `add_unredirected_header` (`R:217`); `_ApiHostRedirectHandler` (`R:125-147`) refuses any
  redirect off `https://api.github.com` (http downgrade, other host or port, userinfo) before it is followed, and
  re-attaches the token only on a same-origin redirect; the `Link: rel="next"` URL (`R:208-210`) and every request
  URL (`R:214-215`) must pass `is_api_url` (`R:82`), else `OffApiHostRefusedError`; the client refuses a second
  redirect handler (`R:165`). Tests `U:202-272` drive the real opener through stub urllib handlers that record each
  request it really sends. Mutations: `add_header` -> 2 red; opener without the redirect pin -> 4 red (off-host,
  http-downgrade, other-port, userinfo); next-link and request-URL checks removed -> 3 red.
- F2: `P:77-84` scans `src/shared/packages/pyforge-warden` and the whole `django-warden` package;
  `test_leak_guard_scan_roots_exist` (`P:579`) asserts every root exists and lists tracked files; the guard reads its
  target through `resolve_fleet_target_config_path()` (honours `WARDEN_FLEET_TARGET_CONFIG`) and reports paths only,
  never a term (`P:541-576`); `test_leak_guard_finds_a_planted_term` (`P:606`) proves it is not vacuous. Live path:
  `F:61-85` anchors the default `.warden/` paths to the checkout root (nearest `.git` above the module), not the cwd,
  so `manage.py` run from `src/platform` reads the root config; pinned by
  `test_default_paths_anchor_to_the_checkout_root` (`P:523`, run from a foreign cwd). Mutations: old root -> red;
  cwd-relative default -> red; env override ignored -> 2 red.
- F3: the method is read off the request the opener really sends: `test_every_outgoing_request_is_a_get` (`U:176`)
  and `test_real_client_run_is_get_only_and_never_persists_the_token` (`P:629`: the real task and the real client over
  a stub transport). The fixture client no longer records a method (`_FixtureListingClient`, `P:116`, records the
  organisation asked). Mutation: `method="POST"` (`R:216`) -> unit and platform red.
- F4: the real client's HTTPError and URLError paths run through stub handlers with the sentinel token (`U:322-366`;
  `test_real_client_failure_never_carries_the_token`, `P:666`, http-error and url-error): the sentinel is absent from
  `str`, `repr`, the shown exception chain, frame locals, captured logs, rows and the (absent) export. Mutations: token
  in the HTTP message -> unit and platform red; token in the URL message -> unit and platform red.
- X1 (found while proving F4; AC7): the platform's JSON log renderer (`config/observability/logging.py`, structlog
  `dict_tracebacks`) prints every traceback frame's locals, so a failed run would have logged the token twice: the
  task's `token` local, and, through the `from exc` chain, urllib's `do_open` `headers` local (Authorization). Fixed:
  urllib errors re-raise `from None` (`R:224-232`), the task holds no token local (`tasks.py:143`), the provider drops
  `gh`'s result before any raise (`F:183-185`), the client's `repr` is redacted (`R:172`). Tests:
  `test_connection_failure_log_lines_never_carry_the_token` (`P:711`: real `do_open`, connect refused, the production
  renderer), `test_connection_failure_in_urllib_never_renders_the_token` (`U:343`, with a control showing the
  suppressed urllib error does hold the token), `test_missing_gh_login` (`P:421`). Mutations: task `token` local ->
  red; `from exc` kept -> unit 2 red and platform red; `completed` kept -> red.
- X2 (pre-existing on the branch, `pr-preflight` red): a `P` docstring line ("must not import" + "pyforge.*", at
  HEAD `:332`) tripped scribe's `test_src_platform_has_no_pyforge_import` diff-text guard; reworded. X3: this pass's
  first `P` imported `http.client` and `urllib.request`, which doctor's
  `test_story_does_not_add_pyforge_under_src_platform` refuses under `src/platform`; `P` now patches the stdlib by
  dotted name and types the request through a local Protocol. All 22 `src/platform` diff-guard meta tests pass.
- F5: the `[maybe-false]` `[defer]` bullet below now cites `spec-pyforge-atlas:CAP-61`; `ad-citation-check` 0.
- M1: one `git check-ignore -q` per path in Verification. M2: `pyforge/warden/__init__.py` back to `__version__` only
  (identical to `main`; nothing imported the constant). M3: Spec Change Log entry (2026-10-11, placement deviation).
  M4: `ListedRepo` is defined once (`R:50`) and the fabric reads it structurally (`F:191-221`, Protocols); the
  in-task adapter is gone (`tasks.py:137-148`); `FLEET_INVENTORY_FLAG` lives only in `fleet.py:17`;
  `RecordingOrgReposClient` left production code. M5: `gh auth token` runs through one seam, `_run_gh` (`F:147`), with
  `timeout=` (default 30 s, `F:31`); a timeout is `GhTimeoutError` raised `from None` (`F:50`, `F:180-182`); tests with
  a fake runner (`P:445`, `P:454`). M6: an entry missing `full_name`, `default_branch` or `clone_url`, with a
  non-boolean `archived`, or not an object is never defaulted or dropped: it lands in `OrgReposListing.skipped` with
  page, position and reason (`R:58-73`, `R:107-122`), is never upserted, is named under the export's additive
  `skipped` list (`F:224-244`) and counted in a warning (`F:296`); tests `U:394-417`, `P:331`. M7:
  `src/platform/conftest.py:64-93` autouse `real_gh_attempts` makes `_run_gh` refuse and fails the test at teardown
  even when the refusal was swallowed; `test_guard_refuses_the_real_gh_runner` (`P:469`). M8:
  `test_leak_guard_skips_when_config_absent` (`P:598`) asserts the guard returns no terms and names the absent path.
  M9: `atomic_write_json` (`F:247-262`) writes a `mkstemp` file beside the export, renames it and unlinks it on any
  failure; `.warden/` ignores the temp name (`P:508`); tests `P:881`, `P:891`.
- Gates on the final tree (exit codes read from files): `pixi run -e pyforge-warden pyforge-warden-test` 0 (2323
  passed); `pixi run -e pyforge-guild lint-types` 0; `pixi run -e pyforge-guild platform-ci-local -- --test` 0 (seven
  steps PASS; 1236 passed, 14 skipped; the known redis-eviction flake did not fire);
  `pixi run -e pyforge-guild spec-surface-check` 0 (names no Spec as drifted, so no stamp was taken; memlog events
  naming each moved path were appended to `spec-pyforge-warden`, `spec-pyforge-core` and
  `spec-pyforge-unifying-strategy`); `pixi run -e pyforge-guild detectors-ci` 0 (45 pass);
  `pixi run -e pyforge-guild pr-preflight -- --keep-going` 1, 34 of 36 lanes ok. The two red lanes are not this
  diff's: `pyforge-atlas-test`, 2 setup errors in `test_read_only_live_attach.py` (its fixture Postgres runs once
  `platform-dev` is installed in the worktree, and its Unix socket path under the preflight basetemp is over
  PostgreSQL's 107-byte limit; the same file passes with a short basetemp, 7 passed); `pyforge-marshal-test`,
  `test_check_under_nfr_p1_budget` (7.5 s over a 5 s budget under 16 parallel lanes) and
  `test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns` (refused only inside preflight; both pass
  alone, and `pixi run -e pyforge-marshal pyforge-marshal-test` exits 0, 12427 passed).
- Not fixed here: nothing from the send-back. Still open (operator): the export's `head_sha` for
  `spec-pyforge-atlas:CAP-61`, and a live run with the operator's `gh` login.

### 2026-10-11 — Independent review, iteration 1: sent back (5 major, 9 minor)

Separate agent, fresh review of `git diff origin/main...HEAD` against this spec and the 2026-10-11 decisions on `spec-pyforge-warden`; mutations in a scratch copy, no network. Confidentiality holds: no real organisation, repository or project name in the diff, the 25 commit messages or the PR #2131 body (checked separately); every identifier is fictional; `.warden/` is ignored for the config, the export, the temp file and `src/platform/.warden/`; no live run happened (no `.warden/` anywhere, no GitHub call journaled); the only `gh` call is `gh auth token --hostname github.com` as an argv list. ACs 1-5, 8 and 11 pass (each mutation caught); AC10 correctly not run. Gates: `pyforge-warden-test` 0 (2310), `lint-types` 0, `spec-surface-check` 0, `flag-gate-check` 0, `platform-ci-local -- --test` 0 (1225); `detectors-ci` 1 (F5).

- `[major]` `[patch]` F1 (security) the bearer token reaches any host on a redirect or a cross-host pagination link: `fleet_github_rest.py:81` `build_opener()` keeps urllib's default redirect handler, `:110` `add_header("Authorization", ...)` is copied onto the redirected request, `:105` follows the `Link` next URL with no scheme/host check. Proven offline: a 302 to `http://evil.example` and a cross-host `Link` next both received the token (the first downgraded to http). Fix: `add_unredirected_header` for Authorization; refuse any redirect whose target is not `https://api.github.com`; refuse a next URL unless it is https on the API host; stub-handler tests for both.
- `[major]` `[patch]` F2 (AC9) the leak guard misses pyforge-warden and never runs in the platform harness: `src/platform/tests/test_warden_fleet_inventory.py:52` scans `_REPO_ROOT / "shared/packages/pyforge-warden"` (does not exist; should be `_SRC_ROOT / ...`); `:203`/`:208` check the relative `.warden/fleet-target.toml`, but the platform suite's cwd is `src/platform`, so a repo-root config makes the guard skip, and `WARDEN_FLEET_TARGET_CONFIG` is ignored; a live `manage.py` from `src/platform` has the same cwd problem. Fix: correct the root, anchor default paths to the repo root, assert every scan root exists.
- `[major]` `[patch]` F3 (AC6) "every request is a GET" is never checked on the real request path: `RecordingOrgReposClient` hard-codes `"GET"` into its record (`django_warden_fabric/fleet_inventory.py:162`); changing `fleet_github_rest.py:109` to `method="POST"` keeps every test green. (The refusal of POST/PUT/PATCH/DELETE before a socket opens holds and is caught.) Fix: a test that captures the method of the actual outgoing request.
- `[major]` `[patch]` F4 (AC7) the sentinel test never runs the real client's error paths: putting the token into `GitHubRestOrgReposClient`'s HTTPError message survives every test. Fix: drive the real client's HTTP-error and URL-error paths with a stub handler and assert the sentinel token is absent from `str(exc)`, `repr`, logs and the export.
- `[major]` `[patch]` F5 (merge gate) `detectors-ci` 1: `ad_citation_check` flags an unqualified atlas capability citation in this spec's Review Triage Log; qualify it as `spec-pyforge-atlas:CAP-61`. The branch is behind origin/main (herald 36.1's merge); merge main and re-run.
- `[minor]` M1 the Verification command `git check-ignore -q <two paths>` exits 128 (`-q` takes one path); split it. M2 `pyforge/warden/__init__.py:14-15` `fleet_inventory = "..."` constant is unnecessary, contradicts the skill's "`__init__` exports only `__version__`" and takes a submodule's name; remove it. M3 record the placement deviation (client in `pyforge.warden.fleet_github_rest`, seams in `fleet_inventory.py`) in the Spec Change Log. M4 dedupe `ListedRepo`, the in-task adapter class and `FLEET_INVENTORY_FLAG`. M5 `fleet_inventory.py:136` `gh auth token` needs a timeout. M6 `fleet_github_rest.py:55-66`: a missing `default_branch` silently becomes `"main"` and entries missing name/clone URL drop silently — record or refuse them. M7 add a conftest guard so no test can invoke the real `gh` provider under eager Celery. M8 `test_leak_guard_skips_when_config_absent` asserts nothing. M9 the export temp file has a fixed name; use a unique temp name.
- Info: I1 no inventory job row (failure shows only as Celery task state); I2 frontmatter read `done` while the PR was held; I3 baseline stamps equal origin/main's, nothing laundered.

Send-back: F1-F5 required; M1-M9 in the same pass. A fresh independent review (iteration 2) gates the landing.

### 2026-10-11 — Review pass
- verdicts: 18 findings — high 3, medium 5, low 4, false 4, maybe-false 2
- findings:
  - `[high]` `[patch]` `RecordingOrgReposClient` required `calls` without default — TypeError in platform inventory tests — added `field(default_factory=list)`.
  - `[high]` `[patch]` urllib in `django_warden_fabric` tripped `test_portal_raw_http_to_a_service_is_review_blocking` — moved GET client to `pyforge.warden.fleet_github_rest`, task lazy-import + adapter.
  - `[high]` `[patch]` leak-guard roots used `parents[2]` (src/) not repo root — fixed `_SRC_ROOT` / `_REPO_ROOT` / `_FABRIC_ROOT` in platform tests.
  - `[medium]` `[patch]` portal flag OFF not verified over HTTP; chrome always enabled — disabled button + message; POST 403 tests added.
  - `[medium]` `[patch]` missing archived field and recording-client GET assertions — extended `test_inventory_three_repos`.
  - `[medium]` `[patch]` platform tests imported `pyforge` at module level — meta guard failed; moved REST unit tests to `pyforge-warden/tests/unit/test_fleet_github_rest.py`.
  - `[medium]` `[patch]` `platform-ci-test` env lacked `pyforge-warden` for eager Celery task — pixi path dep added (memlog on unifying-strategy).
  - `[medium]` `[patch]` task-level missing-`gh` path untested — `test_task_missing_gh_binary_leaves_no_export` added.
  - `[low]` `[reject]` duplicate `FLEET_INVENTORY_FLAG` strings — intentional django vs station constant; no user harm.
  - `[low]` `[reject]` hard-coded HTMX URL in chrome — matches existing audit form pattern in same template.
  - `[low]` `[reject]` `scrub_token_from_text` unused — no demonstrated leak path in this diff.
  - `[low]` `[reject]` Celery org not re-read from config in worker — spec AC keys-not-blobs allows org in message; command loads config at enqueue.
  - `[false]` `[reject]` leak-guard never scans on CI — AC explicitly skips when gitignored config absent.
  - `[false]` `[reject]` `pyforge.core` `test_flags.py` must list new flag — flag_gate_check passed; not a platform import surface requirement.
  - `[false]` `[reject]` seams must live in `fleet.py` — memlog documents `fleet_inventory.py`; flag constant in `fleet.py`.
  - `[false]` `[reject]` verification must use `flagd_tree` in platform tests — platform forbids `pyforge.testing_kit` imports; equivalent `_flag_tree` fixtures used.
  - `[maybe-false]` `[defer]` export lacks `head_sha` for `spec-pyforge-atlas:CAP-61` — severity medium (unverified); open operator question in spec Named section; location: `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`.
  - `[maybe-false]` `[defer]` live leak-guard never runs in CI without operator config — real if operator commits forbidden strings; AC allows skip; location: `src/platform/tests/test_warden_fleet_inventory.py`.

## Auto Run Result

- **Summary:** Fleet inventory for an operator-designated github.com org: gitignored TOML + JSON export, `gh auth token` in the Celery worker only, GET-only listing via `pyforge.warden.fleet_github_rest`, feature flag `pyforge.warden.fleet_inventory`, portal HTMX + management command, fixture org `example-org` in tests.
- **Files changed:** `django_warden_fabric` (fleet inventory sync, tasks, views, chrome template, command); `pyforge/warden/fleet_github_rest.py`; platform flags/tests; `.gitignore`; `pixi.toml` (`platform-ci-test` + `pyforge-warden`); memlogs on warden, unifying-strategy, core, feature-flag-governance, pages specs.
- **Review:** 8 patches applied from triage; 4 false/reject; 2 deferred (`head_sha` contract, CI leak-guard scope).
- **Follow-up review recommended:** `false`
- **Verification:** `pyforge-warden-test` 2299 passed; `platform-ci-local -- --test` PASS; `flag_gate_check.py --spec` pass; `spec_surface_reconcile.py` OK; `git check-ignore` on default `.warden/` paths OK. Live inventory with operator `gh` login not run (operator-owned).
- **Residual risks:** Atlas export shape vs `head_sha` (deferred); leak-guard runs only when local gitignored config exists; operator must configure `.warden/fleet-target.toml` and github.com `gh` login for live runs.
