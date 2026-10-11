---
title: "16.1: Warden inventories an operator-designated GitHub organisation's repos"
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: 'e0d12c1d4ec1d22ec49fd0d6f72e12025462900f'
review_loop_iteration: 0
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
- `git check-ignore -q .warden/fleet-target.toml .warden/fleet-inventory.json` — expected: exit 0.
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

## Review Triage Log

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
  - `[maybe-false]` `[defer]` export lacks `head_sha` for atlas CAP-61 — severity medium (unverified); open operator question in spec Named section; location: `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`.
  - `[maybe-false]` `[defer]` live leak-guard never runs in CI without operator config — real if operator commits forbidden strings; AC allows skip; location: `src/platform/tests/test_warden_fleet_inventory.py`.

## Auto Run Result

- **Summary:** Fleet inventory for an operator-designated github.com org: gitignored TOML + JSON export, `gh auth token` in the Celery worker only, GET-only listing via `pyforge.warden.fleet_github_rest`, feature flag `pyforge.warden.fleet_inventory`, portal HTMX + management command, fixture org `example-org` in tests.
- **Files changed:** `django_warden_fabric` (fleet inventory sync, tasks, views, chrome template, command); `pyforge/warden/fleet_github_rest.py`; platform flags/tests; `.gitignore`; `pixi.toml` (`platform-ci-test` + `pyforge-warden`); memlogs on warden, unifying-strategy, core, feature-flag-governance, pages specs.
- **Review:** 8 patches applied from triage; 4 false/reject; 2 deferred (`head_sha` contract, CI leak-guard scope).
- **Follow-up review recommended:** `false`
- **Verification:** `pyforge-warden-test` 2299 passed; `platform-ci-local -- --test` PASS; `flag_gate_check.py --spec` pass; `spec_surface_reconcile.py` OK; `git check-ignore` on default `.warden/` paths OK. Live inventory with operator `gh` login not run (operator-owned).
- **Residual risks:** Atlas export shape vs `head_sha` (deferred); leak-guard runs only when local gitignored config exists; operator must configure `.warden/fleet-target.toml` and github.com `gh` login for live runs.
