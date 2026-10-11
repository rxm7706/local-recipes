---
title: "16.5: Warden inventories the items of the operator-designated GitHub Projects"
type: 'feature'
created: '2026-10-11'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet.py
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
flag:
  key: pyforge.warden.fleet_project_items
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "no project-item inventory exists; the project-items action is listed as disabled and refuses"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Minted 2026-10-11 from the operator's rulings of that date** (the `spec-pyforge-warden` memlog records them verbatim,
with the target's names redacted). The operator chose the widest scope for the fleet inventory: "All [the
organisation's] repos plus the items of [the two projects]; widest scope, needs the project-item extension too."
Story 16.1 inventories the repos; this story is the project-item extension. The same rulings bind it:
- **Host:** github.com.
- **Naming:** tracked files never name the organisation, its repositories or its projects, and say "the
  operator-designated projects".
- **Credential:** the operator's existing `gh` login, read at run time; no token is copied anywhere.

**Problem:** The operator tracks the fleet's work in GitHub Projects (v2) of the operator-designated organisation.
Warden's inventory (Story 16.1) lists repos only, so nothing in the estate can read what those projects hold: which
issues, pull requests and draft items they track, in what state, under which status.

**Approach:** In `django_warden_fabric`, beside Story 16.1's listing:
- **Config.** The project numbers come from the same gitignored config as 16.1, `.warden/fleet-target.toml`
  (`[github] projects = [...]`, beside `organisation`).
- **Client.** A GraphQL client sends `POST https://api.github.com/graphql` with a read-only `query` document only. It
  takes the token from 16.1's credential provider (`gh auth token --hostname github.com`, once per task, held in
  memory only). For each project it pages `organization(login:) { projectV2(number:) { items(first: 100, after:) } }`
  until `pageInfo.hasNextPage` is false.
- **Fields.** Each item records:
  - its node id;
  - content type (`ISSUE`, `PULL_REQUEST`, `DRAFT_ISSUE` or `REDACTED`);
  - title;
  - state (issue or PR state; none for a draft);
  - repository full name (none for a draft);
  - the value of the project's single-select field named `Status` (none when unset);
  - `updatedAt`.
- **Task.** A keys-not-blobs Celery task writes one JSON export at `WARDEN_FLEET_PROJECT_ITEMS_PATH`, default
  `.warden/fleet-project-items.json` (gitignored by 16.1's `.warden/` line). It writes atomically (a temporary file in
  the same directory, then a rename), so a failed run leaves no partial export.
- **No model, no migration.** The export is this inventory's one face; a later story adds rows if a reader needs
  them.
- **Action.** A portal action and a `warden_fleet_project_items` management command, on one code path, read the flag
  through `pyforge.core.flags.read_boolean`. OFF, the action is listed as disabled and refuses.

Ledger key: `16-5-warden-inventories-the-items-of-the-operator-designated-github-projects`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-16.1.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43): the inventory is published as data other stations read, never through an
  import. This is the project-item extension the operator's 2026-10-11 option text names. CAP-26's `SPEC.md` text still
  says "a GitHub Enterprise organisation" and "GHE credentials come from Steward (steward Story 75.1)". For this story
  and Story 16.1 the 2026-10-11 decision entries in the Spec memlog govern where the two differ, until `bmad-spec`
  re-derives `SPEC.md`. CAP-16 (the service skeleton, keys-not-blobs).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture organisation `example-org` with two fixture projects behind the injectable GraphQL client, holding
  an issue, a pull request, a draft item and a redacted item, When the task runs, Then the export lists each item once.
  Each entry carries its project number, content type, title, state, repository full name, `Status` value and
  updated-at; a draft has no repository or state, and a redacted item has its type only
- Given a project whose items span three pages, When the task runs, Then every page is read by following
  `pageInfo.endCursor` until `hasNextPage` is false
- Given the same projects listed twice, When the task runs again, Then the export holds each item once, rewritten whole
  and never appended
- Given the run against the fixture with a recording client, When every request is inspected, Then each is a `POST` to
  `/graphql` whose document is a single `query` operation. A test drives a `mutation` and a `subscription` document
  through the default client and asserts each is refused before a socket opens
- Given a GraphQL response with an `errors` array, a `projectV2` of `null` (an unknown number or no access), or an HTTP
  5xx or rate-limit reply, When the task runs, Then it fails with a typed error naming the config key `projects` and the
  failing entry's position. No token appears in it, and no partial export is written
- Given no `gh` binary, a `gh` with no github.com login, or a config with no `projects`, When the task runs, Then it
  fails with a typed error naming what is missing, and writes no export
- Given a fake credential provider that returns a sentinel token, When a run ends in success and when it ends in
  failure, Then the sentinel appears in no log record, Celery message, error text or export
- Given the Celery message, When it is inspected, Then it carries ids only (keys-not-blobs): no token, no
  `Authorization` header and no item data
- Given the default export path `.warden/fleet-project-items.json`, When `git check-ignore` is asked, Then it is
  ignored (a test pins it), and the leak-guard test of Story 16.1 covers this story's files and fixtures
- Given the operator's `gh` login and the gitignored config, When the operator (or the dispatch, reading through that
  login) runs it live, Then the export lands only under the gitignored path, `git status --porcelain` is the same
  before and after the run, and no mutation reaches GitHub
- Given the flag OFF, When the operator opens the portal or runs the management command, Then the action is listed as
  disabled and refuses (the command exits 2, warden's usage code)

## Boundaries & Constraints

**Always:**
- Live in `django-warden`; the `pyforge.warden` scan process gains no socket.
- Reuse Story 16.1's credential provider and config reader; never a second credential path.
- Send `query` operations only, as `POST /graphql`.
- Use fictional fixtures only (`example-org`, invented project numbers, titles and repo names).
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree
  (canopy:AD-11). Add the key to `src/platform/config/flags.json` (default OFF) and its overlay rows. The portal view
  runs inside the host, where `pyforge` may be absent; there, and only there, it evaluates the same key through
  `django_pyforge.flags`.
- Reconcile every Spec `spec-surface-check` names for the touched paths; scoped stamps only.

**Never:**
- Send a `mutation` or a `subscription`, or call a REST write endpoint.
- Name the operator-designated organisation, its repositories, its projects or their real project numbers in a
  tracked file, a test, a fixture, a commit message or a PR body. Never commit the config or the export.
- Copy the token into `steward keys`, an env file or any other file.
- Reach GitHub, or run `gh`, from the test suite.
- Add a model, a migration, a webhook, a FastAPI or SQLAlchemy service, or a gitgres store.
- Edit a project, an item or a field value.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| two projects | fixture `example-org`, mixed item types | one export, each item once with its project number | — |
| three pages | `hasNextPage` true twice | every page read | — |
| re-run | same projects | export rewritten whole | — |
| draft item | `DRAFT_ISSUE` | no repository, no state | — |
| redacted item | `REDACTED` | type only | — |
| no `Status` | field unset | `Status` empty | — |
| unknown project | `projectV2: null` | no export | typed error naming `projects` and the position |
| GraphQL `errors` | partial data | no export | typed error, no token in it |
| mutation document | through the client | refused before a socket opens | typed refusal |
| no login | `gh auth token` exits non-zero | no export | typed error naming the github.com login |
| flag OFF | key off | action disabled | refuses, exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43); the 2026-10-11 memlog decisions govern its host and
credential wording for this story.
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-10-11 — Ruled: the fleet is an operator-designated github.com organisation, read through the operator's `gh` login, and never named in a tracked file*.
Ledger key: `16-5-warden-inventories-the-items-of-the-operator-designated-github-projects`.
Ledger status at mint: `backlog`.
Deps: S-16.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass. The `django-warden` tests live under
  `src/platform/tests/` (`src/platform/tests/test_warden_fleet_project_items.py`).
- `pixi run -e pyforge-guild python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-5-warden-inventories-the-items-of-the-operator-designated-github-projects.md`
  — expected: `pass`.
- `git check-ignore -q .warden/fleet-project-items.json` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

**Manual checks:**
- Flag ON/OFF: `src/platform/tests/test_warden_fleet_project_items.py` writes the trees with
  `pyforge.testing_kit.flags.flagd_tree` and parametrizes with `flag_states` over `pyforge.warden.fleet_project_items`.
  ON runs the listing; OFF lists the action as disabled and refuses with exit 2.
- Live run, by the operator or by the dispatch reading through the operator's `gh` login (never a token pasted
  anywhere): with the gitignored config in place, run `warden_fleet_project_items`. Expected: the export lands under
  `.warden/`, `git status --porcelain` is identical before and after, and nothing from the run is staged. If `gh` has no
  github.com login, lacks `read:project`, or the config has no `projects`, stop and report.

## Spec Change Log

- 2026-10-11: minted `ready-for-dev` (ledger `backlog`, Deps S-16.1) from the operator's rulings of that date, which
  chose "Whole org + 2 projects". Bound to CAP-26 (FR-43). The flag is `pyforge.warden.fleet_project_items`.

## Review Triage Log

- No review yet (minted 2026-10-11). Implementation and review stay separate.
