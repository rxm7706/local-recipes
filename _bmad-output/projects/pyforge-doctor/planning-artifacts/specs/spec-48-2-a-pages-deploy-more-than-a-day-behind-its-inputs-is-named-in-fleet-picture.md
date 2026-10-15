---
title: '48.2: A Pages deploy more than a day behind its inputs is named in fleet-picture'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
baseline_revision: 'e134549afcbdcc5b55b35f291464ac60d6685243'
flag-exempt: detector-or-gate   # a check that judges; gating it off would bring back the silent-off surface it names, the 2026-10-06 deploy (spec-feature-flag-governance Q2; bmad-spec ruling 2026-10-14, memlog)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/dashboard.yml
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  - scripts/fleet_picture.py
  - tests/scripts/test_fleet_picture_ci_pauses.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Pages deploy sat in `waiting` from 2026-10-06 to 2026-10-12, with 199 cancelled runs queued behind it,
and nothing reported it (`brainstorm-intent.md`, the finding; the herald Dream's 2026-10-13 lead entry). Steward's
`ci status --json` now names that class from GitHub's side (`docs/governance/ci-surfaces.yaml`, row `dashboard.deploy`,
`stuck_rules.deploy_waiting_hours: 24`), relayed by Story 45.1's `ci-pause-stuck` (CAP-89), but only for a signed-in
reader with `pyforge.steward.ci_pause_control` on; an unauthenticated session, or the flag off in staging and production,
reads `ci-pause-unobserved`. The site itself says when it was last deployed: the live root answers every request with a
`last-modified` header (measured 2026-10-14 16:41 UTC with one `curl -sI https://rxm7706.github.io/local-recipes/`:
`HTTP/2 200`, `server: GitHub.com`, `last-modified: Wed, 14 Oct 2026 15:46:03 GMT`). The repository says when its
published inputs last changed. Nothing compares the two.

**Approach:** one new Doctor source, `pages-liveness`, in the shape of `sources/ci_pause_drift.py` and
`sources/sibling_dreams.py` (a live read, warn-only, an explicit "could not read" finding instead of silence), and one
`fleet-picture` ATTENTION probe in the shape of `ci_pause_drift_findings`.

- **Model.** `Source.PAGES_LIVENESS = "pages-liveness"` in `models.py` (AD-3: the closed taxonomy extended); a
  `REGISTRY` entry with `scope="runtime"`, `subject_station="herald"` (the site and `dashboard.yml` are herald's today;
  the label follows the duct to steward on M2's reconcile), `owning_station="doctor"`; a `DISPATCH` entry in
  `sources/__main__.py`.
- **The live side.** `PAGES_ROOT_URL = "https://rxm7706.github.io/local-recipes/"`, a module constant. One
  `urllib.request.Request(PAGES_ROOT_URL, method="HEAD")` with a 10-second timeout and a `User-Agent` naming the source;
  when HEAD answers outside 2xx (a 405 included) one GET follows, with the same timeout, body unread. The `last-modified`
  header is parsed with `email.utils.parsedate_to_datetime` into an aware UTC datetime. `urllib` is not a subprocess, so
  the sole-subprocess meta-test still names `cli_bridge` alone; the `urlopen` callable is a module attribute so tests
  replace it.
- **The local side.** `PUBLISHED_INPUTS = ("docs/tutorials", "docs/how-to", "docs/reference", "docs/explanation",
  "docs/index.md", "docs/404.md", "docs/map.yaml", "docs/dashboard", "docs-site", "docsite", "presentations")`, the
  herald Dream's M1 list (the workflow itself is excluded: a workflow edit deploys nothing new). The source calls
  `cli_bridge.run_git(target, ["log", "-1", "--format=%H %cI", "refs/remotes/origin/main", "--", *PUBLISHED_INPUTS])`
  (AD-5; CAP-85's full-refname rule, never a bare `main`) and parses the sha and the committer date. No fetch: the
  source is read-only and its one network call is the HTTP request; a stale remote-tracking ref can only make the site
  read fresher than it is, never staler, and every row names the commit date so the base is visible.
- **The rule.** `STALE_AFTER = timedelta(hours=24)`, the registry's `deploy_waiting_hours` figure. `lag = commit_date -
  last_modified`. When `lag > STALE_AFTER` (strictly; a lag of exactly 24 hours is not stale) the source yields one
  `pages-liveness-stale` WARN naming the URL, `last_modified`, the commit sha and date, and the lag in whole hours;
  otherwise one OK finding naming the URL, `last_modified` and the commit date. A negative lag (the site newer than the
  commit, the normal case) is the OK row.
- **Unavailable.** A `URLError` or `socket.timeout`, a response outside 2xx on both requests, a 2xx without
  `last-modified`, a header `parsedate_to_datetime` rejects, a `CliBridgeError` from `run_git` (no
  `refs/remotes/origin/main`, no git, a timeout) or an empty `git log` (no commit touched the inputs) each yield exactly
  one `pages-liveness-unavailable` WARN naming the cause (the HTTP status or exception class and message, or the git
  error's first line), and no OK finding. Never a FAIL (AD-2), never a crash (`degrade_on_exception`, as every source).
- **fleet-picture.** `pages_liveness_findings()` runs `python -m pyforge.doctor.sources pages-liveness --json` with the
  same subprocess discipline as `ci_pause_drift_findings` (60-second timeout) and returns the WARN findings; `main()`
  appends one `watch` line per finding (`<check>: <first line of message, 110 chars>`) and `could not check Pages
  liveness` when the probe raises, beside the CI-pauses probe.
- **Fixtures.** `src/shared/packages/pyforge-doctor/tests/fixtures/pages_liveness/` holds one JSON file per case:
  the response status and headers for HEAD and (where it runs) GET, and the `git log` line; the 2026-10-06 replay
  carries `last-modified: Tue, 06 Oct 2026 03:12:00 GMT` and the input commit `2026-10-08T15:30:00-05:00` (the day herald
  Story 27.2 moved the dossier under `/herald/`, a published-input change the stuck deploy never published).

Ledger key: `48-2-a-pages-deploy-more-than-a-day-behind-its-inputs-is-named-in-fleet-picture`.
Type / Effort / Deps: feature / S / none.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-91** (FR-24): this story builds the whole capability. Beside CAP-89 (the same incident
  class from GitHub's side) and CAP-71 (`sibling-dreams-drift`: a live, unauthenticated, warn-only read with an explicit
  unreachable finding); the fleet view of CAP-2 and CAP-6.
- **AD-2** (warn never changes the exit code), **AD-3** (closed `Source` enum, extended), **AD-5** (the one subprocess
  site; `run_git` already exists, so AD-12 is not invoked), **NFR-1** (read-only: no fetch, no write), **NFR-4** (not in
  `doctor check`'s default set, so the speed budget does not move). AD-11 does not bind it: it relays a public fact
  about the deploy and the repository's own history, not a station's self-report. **CAP-85** (FR-18): the full
  refname.
- **`pyforge-steward:CAP-166`**: the registry's `deploy_waiting_hours: 24` is the figure this source agrees with; the
  source never reads the registry or steward's report.
- **Flag:** `flag-exempt: detector-or-gate` (bmad-spec ruling 2026-10-14, memlog). The source only judges; gating it off
  would reproduce the silent-off surface it exists to name.
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-13 entry (one registry orders the whole
  site, and a stale site tells on itself); the herald Dream's 2026-10-13 lead entry; the intent doc's M1 ("a scheduled
  liveness probe (live root last-modified vs latest docs commit) as a doctor advisory") and the design-thinking doc's
  Success Metrics row (`last-modified` within 24 h of the last publish-input commit: "unmeasured; once 6 days stale" →
  "measured daily (doctor advisory)").

## Acceptance Criteria

- **AC1 — Fresh and within a day.** With `urlopen` and `run_git` replaced by fixture readers, a site whose
  `last-modified` is after the input commit, and one whose commit is 23 hours newer than `last-modified`, each yield
  exactly one OK finding naming the URL, `last_modified` and the commit date, and no WARN.
- **AC2 — Stale.** A commit 25 hours newer than `last-modified` yields exactly one `pages-liveness-stale` WARN whose
  message names the URL, both timestamps, the sha and `25 hours`; a commit exactly 24 hours newer yields the OK row.
- **AC3 — The replay.** The 2026-10-06 fixture yields one `pages-liveness-stale` WARN naming a lag of at least 24 hours
  (the fixture's own figure, asserted exactly).
- **AC4 — HEAD then GET.** HEAD 405 then GET 200 with the header yields the normal verdict and exactly two requests;
  HEAD 200 with the header yields it with exactly one request; HEAD 404 then GET 404, and HEAD 503 then GET 503, each
  yield one `pages-liveness-unavailable` WARN naming the status and no OK.
- **AC5 — Never a false clean.** A `URLError`, a `socket.timeout`, a 200 without `last-modified`, a `last-modified` of
  `not a date`, a `CliBridgeError` from `run_git` and an empty `git log` line each yield exactly one
  `pages-liveness-unavailable` WARN naming the cause, and no OK finding.
- **AC6 — Warn never moves the exit code.** `python -m pyforge.doctor.sources pages-liveness --json` exits 0 on every
  fixture above, the unavailable ones included, prints a JSON list of findings, and every finding's status is `warn`
  except the OK row.
- **AC7 — Wired.** `Source.PAGES_LIVENESS`, its `REGISTRY` row (`runtime`, subject `herald`, owner `doctor`) and its
  `DISPATCH` row exist and the existing dispatch and registry tests cover them; `fleet-picture` prints one watch line
  per WARN from a stubbed probe and `could not check Pages liveness` when the probe raises
  (`tests/scripts/test_fleet_picture_pages_liveness.py`, in the shape of `test_fleet_picture_ci_pauses.py`).
- **AC8 — Boundaries hold.** `test_cli_bridge_sole_subprocess.py` stays green (the source imports no `subprocess`); the
  git argv names `refs/remotes/origin/main` and no test finds a bare `main` or `origin/main` in it (CAP-85's meta test);
  no test opens a socket (`urlopen` is replaced in every test; a guard test patches `socket.socket` to raise); no `gh`,
  no GitHub API URL and no token appear in the module.
- **AC9 — Mutations.** Each fails a named test: a finding emitted as `fail`; a lag of exactly 24 hours reported stale;
  an unreadable site returned as the OK row; a bare `main` in the git argv; GET skipped after a non-2xx HEAD.
- **AC10 — The suites.** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` exits 0; `doctor check --list` and
  the speed-budget test are unchanged; `detectors-ci` exits 0 (the source is not in it).

## Boundaries & Constraints

- Read-only (NFR-1): one HTTP request (two when HEAD is refused) to the public root, one `git log`; no fetch, no `gh`,
  no GitHub API, no token, no write.
- The subprocess call lives in `cli_bridge` only (AD-5); the source module imports no `subprocess`. `urllib.request` is
  the HTTP client; no new dependency (check `docs/reference/library-llms-full.md` before importing anything else).
- Not added to `doctor check`'s default set, `monitor --fleet`'s axes, `scripts/detectors.py` or `detectors-ci`; no
  pixi task (it runs through the sources dispatcher, as `ci-pause-drift` and `sibling-dreams-drift` do), so
  `pixi.toml`, `environment.yaml` and the generated reference pages do not move.
- No steward file changes: the registry's `deploy_waiting_hours` is the figure the constant matches, not a file the
  source reads.
- `doctor check`'s findings, exit code and speed-budget test are unchanged.
- The URL and the pathspec list are module constants; neither is read from an environment variable or a flag (the
  second host is Spec open question 1).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| HEAD 200, `last-modified` 2026-10-14T15:46Z, commit 2026-10-14T14:00Z | one OK finding, one request |
| HEAD 200, commit 23 h newer than `last-modified` | one OK finding |
| HEAD 200, commit exactly 24 h newer | one OK finding (strict comparison) |
| HEAD 200, commit 25 h newer | one `pages-liveness-stale` WARN, `25 hours` |
| the 2026-10-06 replay | one `pages-liveness-stale` WARN, lag ≥ 24 h |
| HEAD 405, GET 200 with the header | the normal verdict, two requests |
| HEAD 404, GET 404 | one `pages-liveness-unavailable` WARN naming 404 |
| HEAD 503, GET 503 | one `pages-liveness-unavailable` WARN naming 503 |
| `URLError(gaierror)` (offline) | one `pages-liveness-unavailable` WARN naming the error |
| `socket.timeout` | one `pages-liveness-unavailable` WARN naming the timeout |
| 200 with no `last-modified` | one `pages-liveness-unavailable` WARN naming the missing header |
| `last-modified: not a date` | one `pages-liveness-unavailable` WARN naming the header |
| `run_git` raises `CliBridgeError` | one `pages-liveness-unavailable` WARN naming the git error |
| `git log` prints nothing | one `pages-liveness-unavailable` WARN (no input commit on the ref) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-91 (FR-24), minted 2026-10-14; beside CAP-89 and CAP-71.
- Architecture: AD-2, AD-3, AD-5 as written; AD-11 does not bind (see the spine's § Currency reconciliation —
  2026-10-14 (Pages site)).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-13 entry (one registry orders the whole site,
  and a stale site tells on itself).
- Epic: Epic 48 (new), Story 48.2. `epic-48` and `epic-48-retrospective` are minted with Story 48.1.
- Ledger key: `48-2-a-pages-deploy-more-than-a-day-behind-its-inputs-is-named-in-fleet-picture`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 48.1 and this story share Epic 48 and no file; either lands first.
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"` (added with this mint). `scripts/fleet_picture.py` is
  allowlisted in `scripts/spec_surface_allowlist.txt` and named in `spec-pyforge-marshal`'s surface; reconcile every
  Spec `spec-surface-check` names, as Story 45.1 did (`spec-pyforge-doctor`, co-governor `spec-pyforge-core`,
  `spec-pyforge-marshal`).
- `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Minted 2026-10-14 in one chain commit.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-91 (FR-24), beside CAP-89 and
CAP-71; AD-2, AD-3, AD-5, CAP-85 • `flag-exempt: detector-or-gate`

**Given** the live Pages root answers with a `last-modified` header, `dashboard.yml` fires on every push to `main` with
no path filter, the registry's `dashboard.deploy` row sets `deploy_waiting_hours: 24`, and nothing compares the site
with its inputs
**When** `python -m pyforge.doctor.sources pages-liveness` or `fleet-picture` runs
**Then** one HTTP request (HEAD, then GET when HEAD is not 2xx) and one `git log` on `refs/remotes/origin/main` over the
eleven published-input pathspecs yield one `pages-liveness-stale` WARN when the commit is more than 24 hours newer than
`last-modified`, else one OK row; anything the source cannot read is one `pages-liveness-unavailable` WARN and no OK
**And** the recorded fixtures each yield the stated verdict with no socket opened, `fleet-picture` shows one line per
WARN and the degrade line when the probe raises, the sole-subprocess meta-test still names `cli_bridge` alone, and
`pyforge-doctor-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with AC1–AC6, AC8 and AC9's tests (the
  station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py -q` — expected: pass (AC1–AC6, AC8, AC9).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py -q` — expected: pass (AC7, AC8).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_pages_liveness.py -q` — expected: pass (AC7's `fleet-picture` half).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: pass (the Detectors workflow's scripts lane).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0 (the source is not in it; nothing it judges moves).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 (`flag-exempt: detector-or-gate` is on the roster's closed list).
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The five mutations of AC9 — expected: each fails its named test. Restore each.

**Operator, after landing (a live, unauthenticated read):**
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources pages-liveness` — expected: exit 0 and one OK
  row naming the live `last-modified` and the latest published-input commit on `refs/remotes/origin/main` (after a
  `git fetch origin`); then `python scripts/fleet_picture.py` shows no Pages line under ATTENTION. Unplug the network
  and run it again: one `pages-liveness-unavailable` line, never a clean fleet.

## Named, not fixed here

- **The second host.** CAP-56's `pyforge.herald.pages_host` names a GitHub Enterprise Pages host; whether this source
  probes it too, reading the host from the same flag herald's build reads, is Spec open question 1. The URL stays a
  constant until the operator decides.
- **The published-inputs list and the workflow's filter.** `dashboard.yml` carries no `paths:` filter today; herald's
  M1 story adds one and steward's `pages.yml` (Epic 102) carries it in M2. A doctor meta-test pinning
  `PUBLISHED_INPUTS` to that filter, reading the workflow as data, is Spec open question 2.
- **A schedule.** `fleet-picture`'s cadence is the operator's; a scheduled probe is outward work.
- **The lag's cause.** This source says the site is behind; CAP-89's `ci-pause-stuck` and steward's `ci status` say
  why from GitHub's side. The two are read together in `fleet-picture`'s ATTENTION block.
- **The identical-build case** (added 2026-10-15 by the independent review). `pages.yml` deploys only when the built
  tree's hash differs from the live `build.json` (steward 102.2), so a published-input commit whose build is
  byte-identical to the live tree (a comment-only edit to `docs/map.yaml`) is not deployed, `last-modified` stays at
  the earlier deploy, and this rule would read `pages-liveness-stale` a day later with nothing stuck. Today herald's
  build stamp (`Built <date> · <sha7>`) makes every new commit's tree hash differently, so it does not occur. Steward
  102.3's `decide_deploy` daily refresh keeps it from occurring once the hash stops seeing the stamp: it deploys an
  identical tree when the live `built_at` is more than 24 hours old and the commit differs from the live
  `built_from`, so the lag this rule reads cannot pass 24 hours on a healthy duct. Not this source's to fix.

## Spec Change Log

- 2026-10-14: minted with CAP-91 / FR-24 and Epic 48 from the Dream's 2026-10-13 entry, the herald lead entry (M1's
  liveness probe), the intent doc and the design-thinking doc's Success Metrics row. `type: feature`,
  `flag-exempt: detector-or-gate` by `bmad-spec` ruling (memlog 2026-10-14). The live `last-modified` header was
  measured on 2026-10-14 before the mint; the 2026-10-06 replay's timestamps are the fixture's, chosen inside the
  incident window, not recovered from GitHub.
- 2026-10-15 (independent review, iteration 1 fixes):
  - argv adds `--first-parent`: the landing commit's date is when main's inputs changed. Without it, history
    simplification answered with a commit from the merged branch, dated up to 7 hours (and, for a long branch, days)
    before its landing, which reads the site fresher than it is (finding 1). The argv still names
    `refs/remotes/origin/main` and fetches nothing (AC8).
  - The stale message leads with the lag and both dates and names the commit and the URL last, so `fleet-picture`'s
    110-character ATTENTION line keeps the evidence (finding 5). A lag that is not a whole number of hours reads
    "more than N hours", so a stale lag never prints as the 24-hour threshold itself (finding 4). `last-modified`
    prints as `YYYY-MM-DDTHH:MM:SSZ` in the message and the evidence.
  - An `HTTPError` (the response to a HEAD answered outside 2xx) is closed explicitly (finding 6).
  - The deploy workflow is now `pages.yml` (steward 102.1 / 102.2), whose `paths:` filter is `PUBLISHED_INPUTS`
    plus the workflow file itself and, since steward 102.4's review, the build's own tooling (`scripts/pages_*.py`
    and steward's `src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py`). *(Corrected 2026-10-15 at the
    lane merge; this line first said "exactly `PUBLISHED_INPUTS` plus the workflow file".)* `PUBLISHED_INPUTS` stays
    as it is: build tooling, like the workflow file, is not a published input, so its commit date says nothing about
    whether the published content is behind the live site; a tooling change that does change the built tree deploys
    through the tree-hash compare and moves `last-modified` itself. The Intent, the Epic excerpt's Given and "Named,
    not fixed here" item 2 above still describe `dashboard.yml` firing on every push with no filter; they are kept as
    minted. Spec open question 2 (a doctor meta-test pinning `PUBLISHED_INPUTS` to that filter) is now cheap
    (finding 7); that meta-test must exclude the workflow file and the build-tooling paths from the comparison.
  - The rule never consults the clock (finding 3): `DW-doctor-48-2-1` in the doctor deferred-work ledger, for a
    `bmad-spec` change to CAP-91. The identical-build case (the builder's open question) is a "Named, not fixed here"
    line above (finding 2).
- 2026-10-15 (M2's reconcile, with herald 42.3 + steward 102.5): the `REGISTRY` row's `subject_station` moves from
  `herald` to `steward`, as the Intent's Model bullet foresaw ("the label follows the duct to steward on M2's
  reconcile"): steward owns the deploy duct (`pages.yml`) since M2, and that pair closes M2. AC7's "subject `herald`" and
  the Auto Run Result's wording record the row as first landed.
- 2026-10-15 (same pass): steward's station-tests trigger map reads this story's pinned `PUBLISHED_INPUTS` strings as
  reads, so `.github/workflows/pyforge-station-tests.yml`'s doctor job now also fires on `docs/index.md`,
  `docs/404.md` and `docs/map.yaml`. It was red at `73ae4f1180`.

## Auto Run Result

Status: in-review

Summary: New Doctor source `pages-liveness` (`sources/pages_liveness.py`): `Source.PAGES_LIVENESS`, a `REGISTRY` row
(`runtime`, subject `herald`, owner `doctor`), a `DISPATCH` row and the report schema's `source` enum (additive). One
`git log -1 --format=%H %cI refs/remotes/origin/main -- <the eleven published inputs>` through `cli_bridge.run_git`,
then one HEAD to the Pages root (one GET when HEAD is not 2xx, body unread, 10 s timeout, `User-Agent:
pyforge-doctor-pages-liveness`); a commit more than 24 hours newer than `last-modified` is one `pages-liveness-stale`
WARN, otherwise one `pages-liveness` OK row; every unreadable side is one `pages-liveness-unavailable` WARN carrying
`evidence.unevaluable: true`, and `degrade_on_exception` reports any unforeseen raise under that same check.
`scripts/fleet_picture.py` gains `pages_liveness_findings()` (60 s, `check=True`, WARN rows only) and one ATTENTION
watch line per WARN beside the CI-pauses probe, `could not check Pages liveness` when the probe raises.

Files changed:
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py` (new), `models.py`,
  `sources/__init__.py` (registry row; the sibling-dreams comment split by the 45.1 row moved back onto its row),
  `sources/__main__.py`, `data/report-schema.json`
- `tests/unit/test_sources_pages_liveness.py` (new), `tests/fixtures/pages_liveness/*.json` (14 new), and the
  wiring tables in `test_sources_dispatch.py`, `test_sources_registry.py`, `test_models.py`,
  `tests/meta/test_source_independence.py`
- `scripts/fleet_picture.py`, `tests/scripts/test_fleet_picture_pages_liveness.py` (new)

Verification: `pyforge-doctor-test` exit 0 (3776 passed, 1 skipped; speed budget 4 passed);
`test_sources_pages_liveness.py` 75 passed; dispatch + sole-subprocess + registry + models + source-independence +
full-refname meta 288 passed; `test_fleet_picture_pages_liveness.py` (guild) passed; `pyforge-doctor-scripts-test`
(pyforge-ci) exit 0; `pyforge-doctor-aggregate-scripts-test` exit 0; `lint-types` exit 0; `flag-gate-check` exit 0;
`doctor check --list` lists no new row. The five AC9 mutations each fail their named test (the bare-`main` one also
fails `tests/meta/test_refs_are_full_refnames.py`). Unit coverage: `pages_liveness.py` 100%. `detectors-ci` reds only
on `spec-surface` drift under `spec-pyforge-doctor`, the surface reconcile and scoped stamp still to run.

Decisions inside the contract: the git read runs first, so a git failure or an empty log is one unavailable WARN with
no HTTP request; a transport failure (URLError, timeout, dropped connection) on HEAD is unavailable without a GET
(only an HTTP status outside 2xx earns the GET); a `last-modified` without a zone reads as UTC; a git line whose date
does not parse or carries no zone is unavailable.

The builder's open question (a byte-identical build is never deployed under steward 102.2) was ruled by the
independent review, 2026-10-15: accept, recorded as "Named, not fixed here" (the identical-build case); its fixes are
in the Spec Change Log.

followup_review_recommended: false
