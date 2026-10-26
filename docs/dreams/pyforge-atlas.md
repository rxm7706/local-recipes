---
title: Atlas — the map that maintains itself
type: dream
owner: atlas
status: specified
---
# Atlas — the intelligence layer an agent workforce can maintain

## The Dream

Chart the dependencies, map the world, define the floor — and make the map
maintainable by agents, not heroes. The legacy `cf_atlas` orchestrator was a
~10,000-line hand-rolled monolith: 23 phases whose data lineage lived in one
developer's head, each hand-rolling its own checkpointing and backoff, a
coarse 1800-second timeout able to silently drop a phase and still score the
run green. The dream was its rebirth as declarative dataflow — a DAG small
enough, pure enough, and contract-guarded enough that an autonomous agent can
add phase 24 by writing a node and declaring its datasets, inheriting
checkpointing, TTL, validation, lineage, and scheduling for free.

## What is real

- **Kedro + Dagster + DuckDB migration SHIPPED, 38/38 stories, 100%
  code-complete** — Waves 0 + A–H (32 stories, PRs #58–#105, 2026-07-17/18)
  plus Epic 10's post-audit truth-up (Stories I0–I5, through PR #132,
  2026-07-29). 930 real collected tests across 78 pytest files
  (`src/shared/packages/pyforge-atlas/tests/`), documented story-by-story in
  `test-architecture.md` (2026-08-02). *(The "38/38" is correct and stays —
  it describes **the migration**, which is what this bullet is about. Read
  as a station total it is fourteen epics and ~56 stories behind; see the next
  bullet.)*
- **The station has grown well past the migration** *(added 2026-09-09, fleet
  readiness pass)*: **94 story keys across 24 epics**
  (`planning-artifacts/sprint-status-ledger.yaml`; 142 ledger rows once the
  epic and retrospective rows are counted), adding the query-plane faces
  (Epic 20), catalog expansion and self-containment (21), Vizro identity
  parity (22), the complete zero-deferred export (23), the MCP face (24) and
  the realization-gate effect stories (25).
- Boring Semantic Layer models, a Vizro dashboard — ~~8 pages + factory-status
  live; the full 28-CLI page inventory is deliberately deferred, `DW-D2-1`~~
  *(written 2026-08-02; **superseded 2026-09-09**, fleet readiness pass: the
  full inventory shipped via Stories 20.5 and 21.9, `DW-D2-1` reads
  `status: closed`, and `dashboard/app.py`'s `PAGE_INVENTORY` now carries 34
  page definitions — gated by `dashboard-dryrun`, served by `pixi run -e
  local-recipes dashboard-serve`. The struck text is kept as the record of
  what was true when this Dream was last re-grounded — see § Realization
  log.)* —
  Vizro-AI as an MCP-exposed NL interface, A2A agent-to-agent interfaces,
  OpenLineage + OTel tracing, DuckDB VSS, a Pyodide/DuckDB-WASM no-backend
  build (G1), Dagster sensors (dry-run proven; live daemon bring-up is an
  attended operational event, not code debt — see § Remaining), and Wave H's
  Karpathy-wiki agno compile/lint/Q&A crews.
- The intelligence signals that feed [[packaging-factory]]: staleness,
  feedstock-health, CVE watch, conda-native vulnerability advisories
  (Basilisk, via prefix.dev), release cadence, adoption stage, packaging
  velocity, migration readiness.
- Every one of the 11 epics/waves carries its own retrospective — the last
  two (Wave H's epic-format retro, Wave I's post-audit retro) were written
  2026-08-02, closing a "code newer than retro" currency gap that had been
  this chain's last dashboard finding.
- **2026-08-02 exemplar closure**: retired a duplicate dream
  (`pyforge-atlas-intelligence-platform.md`, whose entire "Realization" list
  restated already-shipped waves), corrected CAP-8/Story-D2/Epic-5 language
  that hadn't caught up with the 2026-08-01 dashboard-page scope correction,
  and wrote the two missing retros above. Result: 0 dream-chain-check
  findings, 0 dashboard currency findings, 0 gaps — clean for the first time
  this session.

## Lineage

Atlas's stack directly descends from [[sentinel]] (§19 Kedro · §20 Dagster ·
§27 BSL · §24 OTel/OpenLineage · §26 La Suite) — the ancestor dreamed the
stack, Atlas built it against the conda-forge domain. It also realized two
2026-04-25 roadmap wishes: the unified DAG orchestrator and the interactive
dashboard.

## The estate Atlas hosts

Atlas's project directory (`_bmad-output/projects/pyforge-atlas/`) is also
the planning home for three separate, substantial initiatives. None is a
capability of Atlas's own `cf_atlas` pipeline — `spec-pyforge-atlas`'s own
CAP-1..CAP-17 (the shipped migration) are untouched by any of the three.
**Update (2026-08-02):** two of the three — Unity Data Stack and Wasm
Analytics Stack — had their own separate Spec/PRD/Architecture chains until
an explicit user decision this same day overrode this repo's default
dream-level-only consolidation convention: their full chains were folded
into Atlas's own single brief/PRD/Architecture/Spec as `## Satellite:`
sections (capabilities renumbered `CAP-18`..`CAP-31`, architecture
invariants renumbered `AD-24`..`AD-56`), and their standalone planning
folders moved intact to
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/{briefs,prds,architecture,specs}/`
(not deleted — see those paths for the original standalone documents).
Upstream-discovery, the third initiative below, remains genuinely untouched.

- **[[unity-data-stack]]** — an enterprise Python-first, air-gap-first
  innersource monorepo platform: one workspace lock across native and PyPI
  dependencies, domain-owned data products in a Raw → Curated → Consumption
  layering (one reference domain, `customer`), a named trusted-committer
  contribution model, a machine-classified governance Constitution, a
  single `check-all` quality gate mirroring CI, and compliance delivered by
  integrating `pyforge-warden` rather than reimplementing it. Seeded
  2026-07-23 from three stranded gists; planned to Spec → PRD → Architecture
  depth by 2026-07-25, then folded into Atlas's own chain 2026-08-02 (see
  above). No epics/stories and no code yet — planning-complete, unscheduled.
- **[[wasm-analytics-stack]]** — a WASI Preview 2-sandboxed Excel-upload
  validation step ahead of a `dlt` → `dbt-duckdb` pipeline, natively traced
  end-to-end (one W3C trace ID, OTel + OpenLineage to Marquez) rather than
  bolted on, for OpenShift Restricted SCC. Its sandbox claim is proven, not
  asserted: a non-hollow isolation-verification gate mechanically fails if
  the component's declared capability surface is ever widened without a
  matching WIT change. Same depth as Unity: seeded 2026-07-23, Spec → PRD →
  Architecture by 2026-07-25, then folded into Atlas's own chain 2026-08-02
  (see above), honestly narrowed in-Spec from its founding gist's broader
  claim (DuckDB itself has no WASI build). No epics/stories, no code —
  planning-complete, unscheduled. A v2 dashboard onto its Gold tables would
  reuse Atlas's own G1 DuckDB-WASM/Pyodide pattern rather than reinvent it.
- **[[upstream-discovery]]** — sense GitHub-trending momentum and
  high-yield org releases, and carry worthy candidates into conda-forge
  before anyone files an issue. Re-grounded 2026-07-25 in Atlas's shipped
  Kedro dataflow after the legacy phase-based design
  (`docs/specs/trendshift-conda-forge.md`) was superseded by the migration.
  Earliest-stage of the three: a Spec only (`status: draft`,
  `specs/spec-upstream-discovery/SPEC.md`), no PRD, no Architecture, zero
  implementation — six open questions remain, including which of Atlas's 7
  closed pipelines should host it.

## Remaining

- Three ATTENDED boundary events, not code debt — each deferred to an
  operator-present event rather than a story: the credentialed legacy-parity
  sign-off and retirement (`DW-B4-2`), the F1 cold/warm benchmark
  (`DW-F1-1`), and bringing the Dagster daemon live (`DW-C1-1`, `DW-G3`,
  `DW-H4`). Tracked in `deferred-work-ledger.md`.
- The full 28-CLI dashboard-page inventory beyond the 8 shipped + factory
  status — `DW-D2-1`.

## Realization log

- **2026-06-20 → 07-16** — spec authored and analyzed (v5.6).
- **2026-07-17 → 07-18** — planned and BUILT via bmad-loop; Waves 0 + A–H
  shipped (32 stories, PRs #58–#105).
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-atlas/`;
  the three satellite dreams below seeded from the gist audit, `owner: atlas`.
- **2026-07-23 (gist audit)** — grounding: the Ecosystem Health Report v2
  (Basilisk §6) is atlas-intelligence output; LF AI & Data landscape kept as
  reference.
- **2026-07-25** — `unity-data-stack` and `wasm-analytics-stack` planned to
  PRD + Architecture depth; `upstream-discovery`'s Spec authored, superseding
  the legacy trendshift phase design.
- **2026-07-29** — Epic 10 (post-audit truth-up, Stories I0–I5) shipped via
  PR #132; 38/38 stories done.
- **2026-08-02** — exemplar closure: retired the duplicate
  `pyforge-atlas-intelligence-platform.md` dream, corrected stale CAP-8
  claims, wrote the two missing per-wave retros — 0 dream-chain-check
  findings, 0 dashboard currency findings, 0 gaps.
- **2026-08-02 (this pass)** — dream-level consolidation: folded the three
  satellites' narrative into § The estate Atlas hosts above. Each satellite
  dream now carries a superseding blockquote and `status: archived` /
  `archived-reason: absorbed`.
- **2026-08-02 (same day, explicit user override)** — full chain
  consolidation for two of the three: Unity Data Stack's and Wasm Analytics
  Stack's own Spec/PRD/Architecture were folded into Atlas's single
  brief/PRD/architecture/Spec (capabilities renumbered `CAP-18`..`CAP-31`,
  architecture invariants renumbered `AD-24`..`AD-56`); their standalone
  planning folders moved intact to `archive/` under this project's
  `planning-artifacts/` tree, not deleted. This supersedes the same-day
  dream-level-only note above for these two — upstream-discovery's own
  chain remains untouched and continues independently.
- **2026-08-02 (Dream-coverage audit, this pass)** — audited the just-merged
  brief/PRD/architecture/Spec chain against this Dream for content with
  execution weight (epics/sprint-status/code) or genuine unscheduled intent
  that this Dream didn't yet name, per the repo's Dream-first convention.
  Checked all 17 primary CAPs/23 ADs plus all 14 satellite CAPs
  (`CAP-18`..`CAP-31`) against `epics.md`, `sprint-status.yaml`, and
  `src/shared/packages/pyforge-atlas/` (grep for `unity`, `wasi`,
  `componentize-py`, `wasmtime`, `basilisk`): confirmed zero epics/stories/
  code for both satellites (matches this Dream's own "no epics/stories, no
  code" claim exactly) and confirmed one primary-chain shipped signal —
  Basilisk, the conda-native vulnerability source (FR-19/CAP-14, Story B8,
  `datasets/basilisk.py`) — was real but under-named here (only an unrelated
  "Basilisk §6" report-section reference existed); named it explicitly
  above. Enriched both satellite bullets with capabilities their full
  fold-in carries but this Dream's prior one-paragraph summaries didn't
  (Unity: air-gap-first, domain data products, trusted-committer model,
  unified `check-all` gate; Wasm: native OTel/OpenLineage tracing to
  Marquez, the non-hollow isolation-verification gate) — all judged genuine,
  researched, unscheduled scope, not speculative or superseded, so **no
  pruning**: nothing was cut from the merged brief/PRD/architecture/Spec.

- **2026-09-09** — Fleet readiness pass, verified against live code at `fe4025ea90`. `realized`
  **re-confirmed under the exercised gate** — the Kedro pipelines, the MCP face, the BSL models
  and the Vizro board all run. Two body claims are behind the station and are corrected here
  rather than silently: (1) "38/38 stories, 100%" (§ What is real) is a correct historical
  statement about the **Kedro/Dagster/DuckDB migration only** — the station now carries **94 story
  keys across 24 epics** (`planning-artifacts/sprint-status-ledger.yaml`; 142 ledger rows once
  the epic and retrospective rows are counted — a distinction worth keeping, since the readiness
  pass and the decision batch both quote the row count as a story count), adding the
  query-plane faces (20), catalog expansion and self-containment (21), Vizro identity parity (22),
  the complete zero-deferred export (23) and the MCP face (24); (2) "a Vizro dashboard (8 pages +
  factory-status live; the full 28-CLI page inventory is deliberately deferred, `DW-D2-1`)" is
  **stale** — `DW-D2-1` reads `status: closed`, the inventory shipped via Stories 20.5 and 21.9,
  and `dashboard/app.py`'s `PAGE_INVENTORY` now carries 34 page definitions, gated by
  `dashboard-dryrun` and served by `pixi run -e local-recipes dashboard-serve`. One unreached
  surface was found on a sibling Dream and retired the same day — see [[atlas-query-dashboards]].
  Cross-station residue for steward: `docs/dreams/README.md` still describes this Dream as
  "waves 0–H shipped, PRs #58–#105", accurate for the migration and roughly 99 stories and 14
  epics behind the station.
- **2026-09-28 (night) — Proposed: Atlas keeps each scanned repo's dependency history, so a fix
  knows when a dependency arrived and which other repos carry it.** Source: the Warden Dream's
  entry of the same day. That is the security-scanning intake, archived at
  `archive/docs/intake/system_architecture_specification.md`, whose Phase 2 persists a
  `dependency_graphs` table per repo and commit.
  **What exists:** Atlas's datasets cover all of conda-forge: `core_dependencies`, the `sbom_*`
  entry pipeline and the OSV offline store. Nothing holds one repo's manifests across its
  commits, and nothing holds a fleet of enterprise repos.
  **The tool:** `git-pkgs` (MIT; v0.20.0, 2026-09-04) walks a repo's history into SQLite
  (`git pkgs init`). Two caveats:
  - It installs git hooks by default.
  - Its `manifests` parser has no `pixi.toml` / `pixi.lock` support (upstream issue #79), and
    pixi is the estate's main format.
  **What it looks like when real:**
  - A Kedro dataset per repo, built from `git pkgs init --no-hooks` output, or from an estate
    pixi parser where git-pkgs has none.
  - The datasets join to Warden's fleet inventory.
  - A poll-cursor sensor drives the refresh, in the `orchestration/event_source.py` pattern, with
    no webhook.
  - Warden's actuator and fleet scan read the history. Atlas never publishes a verdict.
  **Constraints:**
  - The data belongs in Atlas and the verdict in Warden (atlas domain research, 2026-07-25).
  - No hook is written into any scanned repo.
  - `git-pkgs` arrives as a conda package ([[pyforge-mason]], same day).
  - The capability carries a flag block ([[feature-flag-governance]], same day).
  - This station's PRD and spine are dated 2026-09-20, so the CAP mint reconciles both in the same
    PR.
  **Kinships:** [[pyforge-warden]] and [[pyforge-mason]] (same day). Owner: atlas.
  → `spec-pyforge-atlas` CAP-61 / Epic 25 / Stories 25.1–25.2 (FR-69; 25.1 `blocked` on mason
  Story 21.1), specced 2026-09-28; the PRD and spine were reconciled in the same change.
  **Amended 2026-09-28 (spec pass):** AD-4 grep-gates any `sqlite3` import and the no-inline-IO gate
  any `subprocess` import under `src/pyforge/atlas`, so git-pkgs' SQLite is read through DuckDB (or
  its JSON output) and deleted, and `git` / `git pkgs` run through `pyforge.core.process`.
- **2026-09-29 — Recorded, not specced: Atlas computes the definition-of-done verdict for the
  PyPI-to-conda-forge campaign.** Source: a read of `OpenTeams-WFT-CDO/pypi-to-conda-forge`
  (`0456572`, pushed 2026-09-24; the operator owns the org). This is the last unfolded item of
  `archive/docs/intake/external-repos-analysis-2026-08-22/report.md`. That repo files one tracking issue per
  package (1,000 filed against `openteams-ai/mgmt-wf-python-modernization`, about 3,650 to go), and
  `file_issues.py` ticks four definition-of-done boxes from live data:
  1. the package is on conda-forge, and its PyPI-to-conda mapping is correct;
  2. it is at the latest upstream version, with every required version and LTS branch present;
  3. it is `noarch`, or built for linux-64, osx-arm64 and win-64;
  4. its purl-associator mapping is correct.
  **What exists:** Atlas already has every input: feedstock presence and the parselmouth mapping,
  `latest_conda_version` from the `main` label's `current_repodata.json`, per-platform coverage, and
  the purl exports. It already reads that project board (`datasets/identity_sources.py`,
  `openteams_project_1_board_raw`). Two of the repo's heuristics are already here: builds marked
  broken are skipped, because the `main` label excludes them, and `conda_source_registry` records
  whether a feedstock builds from PyPI. What is missing is the combined per-package verdict, and the
  check that every required version is present, which `current_repodata.json` cannot answer because
  it holds only the latest.
  **What it looks like when real:** Atlas computes the four boxes per package, so the campaign's issue
  filer reads one verdict instead of recomputing it in a second repository.
  **Operator ruling (2026-09-29):** keep it, and don't build it yet. No CAP is minted until the operator
  wants it built. **Kinships:** [[pyforge-mason]] (the `auto-recipe` ruling of the same day). Owner:
  atlas.
- **2026-10-03 (Phase 4+5) — Ruled: atlas's open medium and low deferrals are fixed.** The operator ruled that
  Phase 4 (open medium deferrals) and Phase 5 (open low deferrals) of the deferral burn-down run together, now, on the
  idle station lanes; the same day the operator asked for fewer, larger stories, at most about 30 rows each, split by
  package area. A parser over atlas's tracked `deferred-work-ledger.md` counts 36 open medium and 60 open
  low rows (114 unrated open rows are outside the ruling).
  **What it looks like when fixed:** each of the 96 rows reads `closed`, with a `resolution:` naming its story and a
  `verified:` line citing the `path:line` it fixed. The inventory exports refuse a hollow verification set and the
  quartet scripts fail loud; the data plane honours `PYFORGE_ATLAS_DATA_ROOT`, degrades offline and fetches what it
  claims; the read surfaces render what DESIGN.md specifies and are proven on fixture data; the planning record matches
  the tree, and the eight follow-up reviews atlas owes have run.
  **Constraints:**
  - `fix` stories: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
  - Each defect is pinned by a test that fails without its fix.
  - A row whose code a later story removed (Story 23.9 thinned the quartet) is re-located and fixed where the behaviour
    went; it closes on citation alone only when the behaviour is gone.
  - NFR-1 holds: every gate stays fixture-based and non-credentialed.
  Owner `spec-pyforge-atlas`. → Epic 27 / Stories 27.1–27.4, specced 2026-10-03.
- **2026-10-04 — Found: the distribution-breakdown facet filter renders an empty container.** Story 27.3's
  `test_declared_controls_render_against_real_rows` fails intermittently: `#distribution-breakdown--filter-facet`
  renders as an empty 0×0 `div` with no children while the chart beside it renders. It failed in CI on #1836 and
  #1838, and locally on every run after one early pass; neither a longer wait nor a `spawn` start method helped, so
  the defect is in the filter build, not the test. #1842 quarantined the test with a non-strict `xfail` and recorded
  `DW-atlas-27-3-1`.
  **What it looks like when fixed:** the page builds its declared facet control from the rows it shows, on every build
  and page load; the `xfail` is gone and the row is closed.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
  - It goes into Epic 27 and reopens it (operator ruling 2026-10-04: a fix joins its own epic and reopens it, never a
    new epic; doctor Story 41.5 lets `ledger-regression` accept the reopen).
  - The root cause is pinned by a test that needs no browser; waits and retries are not a fix.
  - NFR-1 holds: the proof stays fixture-based.
  Owner `spec-pyforge-atlas`. → Story 27.5, specced 2026-10-04.
- **2026-10-11 (live-attach fixture socket path) — Found: the live-attach fixture Postgres cannot start under a long
  pytest basetemp.** `fixture_postgres` in `tests/unit/test_read_only_live_attach.py` (:88-:209) starts a throwaway
  PostgreSQL with `-k '<tmp_path>/pgsock'`. PostgreSQL refuses a Unix socket path over 107 bytes (the AF_UNIX limit);
  with no socket it exits `FATAL: could not create any Unix-domain sockets`, so `pg_ctl start` fails and the two
  fixture-backed tests (`test_federated_read_across_two_schemas`, `test_write_through_attach_is_refused`) error at
  setup. pr-preflight runs each lane under its own long `--basetemp`, which crosses the limit.
  **Evidence:**
  - Warden 16.1's fix pass ran `pixi run -e pyforge-guild pr-preflight -- --keep-going` on 2026-10-11, and the
    `pyforge-atlas-test` lane went red with these two setup errors.
  - Reproduced on `2b5e0d649b` with a 214-byte basetemp and platform-dev's PostgreSQL 17.11: "5 passed, 2 errors".
    The server log reads `Unix-domain socket path ".../pgsock/.s.PGSQL.<port>" is too long (maximum 107 bytes)`. With
    a short basetemp the file passes 7 of 7.
  - It surfaced only now because the fixture skips in a fresh worktree, which has no `initdb`/`pg_ctl` until an env
    carrying PostgreSQL is installed there.
  - The fixture talks to Postgres only over TCP: the DSN, `pg_isready` and `psql` all use `127.0.0.1`. A scratch
    copy that starts the server with `-c unix_socket_directories=''` in place of `-k` passed 7 of 7 under the same
    basetemp, and its server log shows only the IPv4 listener.
  **What it looks like when fixed:** the fixture opens no Unix socket. Both tests pass under any basetemp when
  PostgreSQL binaries are present, and still skip cleanly when they are not.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1). Test-only: one file changes, and no
    skip or `xfail` is added.
  - A new epic. No atlas epic owns the test: steward Story 34.1 shipped it under `spec-pyforge-unifying-strategy`
    CAP-19 (canopy:FR-46, read-only live attach), and atlas deliberately mints none of that CAP's stories.
  - NFR-1 holds: the fixture stays local and non-credentialed.
  The operator asked for it directly in session: "Do this task here: Fix atlas live-attach test socket path
  overflow". **Kinships:** [[pyforge-steward]] (Story 34.1 shipped the test; pr-preflight's per-lane basetemp).
  Owner `spec-pyforge-atlas` (CAP-6, the one engine the attach joins). → Epic 28 / Story 28.1, specced 2026-10-11.

- **2026-10-13 (range-test recorder race) — Found: the static-host Range proof can read its own request log before the
  server thread has written it.** `test_count_star_reads_footer_only_over_range` in
  `tests/integration/publish/test_emit_range.py` failed in the `pyforge-atlas-test` lane of a pre-push `pr-preflight`
  run on 2026-10-13 with `assert (200 not in [] and 206 in [])`: the query returned the right count, but the
  `_RangeServer` had recorded no request. The same file passed alone and under `-n auto --dist loadgroup` (12 passed,
  three runs), and CI passed `atlas-test` on PR #2186 the same hour.
  **Evidence:**
  - The handler appends to `codes`, `ranges`, `range_spans` and `bytes_served` only after `self.wfile.write(data)`.
    The client can finish the query, and the test can assert, before the server thread runs those appends. The
    `count(*)` test makes exactly one Range request, so it is the one test whose list can be wholly empty.
  - A scratch harness that delays the handler 0.5 s after each body write reproduces it every run: the log reads `[]`
    right after the query and `[206]` one second later.
  - A first hypothesis, DuckDB's external file cache answering a reused port's URL, was tested and ruled out: that
    cache belongs to one database instance, and fresh connections on a reused port each issued their own Range request.
  **What it looks like when fixed:** the handler records each response before it writes any of it, so the log is
  complete by the time the client can read the response. The test keeps every assertion and gains a regression case
  that delays the write and still sees the request.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1). Test-only: one file changes, and no
    skip, `xfail`, retry or sleep-and-hope is added (AD-11: gates are never weakened).
  - A new epic: Epic 8, which shipped the Range proof (Story 8.2, the static web host), is done.
  The operator asked for it directly in session: "Do this task here: Fix flaky atlas range-read test under xdist".
  **Kinships:** [[pyforge-steward]] (the pre-push preflight lane that surfaced it). Owner `spec-pyforge-atlas` (CAP-16,
  the read surface runs with no backend at all). → Epic 29 / Story 29.1, specced 2026-10-13.
- **2026-10-14 (foundry-full mypy) — Found: Atlas fails mypy wherever its real libraries are installed, and no lane
  runs mypy there.** `sbom-laptop-gate` runs `lint-types` inside `pyforge-foundry-full`, which installs Atlas's real
  runtime libraries (Vizro and Dash, Dagster, Kedro, OpenLineage, Bokeh, BeautifulSoup, DuckDB). There mypy checks
  Atlas against their real types and fails. `pyforge-guild`, where the CI `lint-types` lane and `pr-preflight` run mypy,
  installs none of them, so mypy reads every one as `Any` and stays green. Steward Story 100.7 recorded the debt as
  `DW-atlas-steward-100-7-1`.
  **Evidence:**
  - At `846d8383f5`, in a fresh worktree, `pixi run --frozen -e pyforge-foundry-full lint-types` exits 1 at its mypy
    leg. Atlas reports `Found 72 errors in 8 files (checked 130 source files)`. The other nine `pyforge-*` packages pass,
    and so do ruff and `ruff format`. The same mypy (2.4.0, the lock's) over `pyforge-guild` reports no issues.
  - By file: `dashboard/app.py` 59 (54 `call-arg`, 4 `arg-type`, 1 `operator`), `views/widgets.py` 4 `attr-defined`,
    `datasets/upstream_discovery.py` 2, `orchestration/definitions.py` 2, `query_plane_vectors.py` 2, and one each in
    `mcp/session.py`, `observability.py` and `rag/store.py`. The DW row's per-file counts summed to 79, and it named
    FastHTML; the `Nav` in question is Dash's `html.Nav`.
  - All 54 `call-arg` errors read "Missing named argument" on a Vizro model. Vizro declares those defaults inside
    `Annotated[..., Field(default=...)]`, which mypy cannot see. The pydantic mypy plugin, tried in a scratch config,
    clears 10 of the 54 (`Card.href`, `AgGrid.footer`) and one `arg-type`, and leaves 44. Passing the defaults
    explicitly would change `model_fields_set`, which Vizro reads: an explicit `Action.inputs` puts an action on Vizro's
    deprecated legacy path.
  - One error is a real defect. `observability.py` emits OpenLineage's `outputStatistics` facet under `facets`. It is
    an `OutputDatasetFacet`, which openlineage-python 1.53.0 takes under `outputFacets`, so a strict consumer never sees
    the row count where the spec puts it. Four test assertions pin the wrong key.
  - On a scratch copy every other error takes a typed fix. Fixing the Bokeh imports exposes one more, which also takes a
    typed fix. With those fixes and one per-module override (`call-arg` on `pyforge.atlas.dashboard.app`), mypy reports
    no issues in either environment. The unit suite then fails the same environment-bound tests it fails on an
    untouched copy, and no others, once the four assertions read `outputFacets`.
  - No workflow runs mypy in `pyforge-foundry-full`. `lint-types.yml` runs only `pixi run --frozen -e pyforge-guild
    lint-types`, and no workflow runs `sbom-laptop-gate`.
  - Atlas's touched-module coverage floor is 80% unit. Three of the modules involved sit below it today:
    `mcp/session.py` 75.0%, `rag/store.py` 35.1% and `query_plane_vectors.py` 30.9%. The vector tests skip unless the
    DuckDB `vss` extension is provisioned, and the gate's runner does not provision it.
  **What it looks like when fixed:** `mypy -p pyforge.atlas` reports no issues against the real libraries. The CI
  `lint-types` job and `pr-preflight` both run the existing `mypy` task in `pyforge-foundry-full`, so the same drift
  reds the next PR that adds it instead of waiting for the laptop gate.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1), and no `SPEC.md` change.
  - Typed call sites first. An override only where mypy cannot type the call, per module and per error code (the
    2026-09-20 baseline rule), never `ignore_errors`. No inline `# type: ignore`: with `warn_unused_ignores` on, one that
    `pyforge-foundry-full` needs is an `unused-ignore` error in `pyforge-guild`.
  - The lane is the existing `mypy` task in another environment. No new script and no dependency change.
  - `.github/workflows/lint-types.yml` is `spec-pyforge-steward`'s, and the lane list in `pixi.toml` is
    `spec-pyforge-steward:CAP-159`'s, so the implementation reconciles their governors.
  The operator approved it on 2026-10-14: "chain the three DWs". **Kinships:** [[pyforge-steward]] (the lint/types
  gate, `spec-pyforge-steward:CAP-153`; `pr-preflight`; `sbom-laptop-gate`, `fnd:CAP-13`). Owner `spec-pyforge-atlas`
  (CAP-20, one command runs every check CI runs; AD-32). → Epic 31 / Story 31.1, specced 2026-10-14 (minted as
  30.1, renumbered the same day: the Pages redesign chain took Epic 30).

- **2026-10-13 (the DAG export reaches Pages as an artifact) — Ruled: Kedro-Viz stays on Pages through an artifact
  handoff; the committed export retires; Vizro boards follow as static exports.** Operator ruling 2026-10-13, from the
  herald Dream's same-day entry *the Pages deployment, redesigned*. Measured that day: `docs/dashboard/kedro-viz/`
  (11 MB, 215 tracked files) was last written 2026-08-15; `kedro-viz-publish.yml` has been `disabled_manually` since
  2026-08-24 with no recorded reason (steward's CI-pause plan, G12); 23 first-parent merges since then touched the
  paths that workflow watches (pipelines, `catalog.yml`, `globals.yml`, datasets), so the published graph lags its DAG
  by two months; the publish build took 92 to 137 s per run. CAP-41 ("publish stays in sync", shipped) does not hold
  while the producer is paused and the export is bytes in git. **What it looks like when real:** the producer
  workflow is re-enabled through `ci resume` once steward Story 99.3 gives it a `PAUSE_*` gate, keeps its path
  filter, runs `viz-publish-stage` and uploads the export as the workflow artifact `kedro-viz-export` (90-day
  retention) instead of committing; `docs/dashboard/kedro-viz/` leaves git; the Pages build downloads the newest
  successful artifact and skips the mount, hiding the tile, when none exists; `/dashboard/kedro-viz/` keeps its URL
  and shows the export's commit and date. A later story publishes Vizro boards under `/dashboard/vizro/` as offline
  exports of the BSL-driven dashboard object (`dashboard-dryrun` already builds it without a server), with plotly.js
  vendored into the artifact: the intake workaround's `include_plotlyjs='cdn'` is a third-party load AD-21 forbids.
  **Constraints:** no server and no live data on Pages (the placement rule on the herald Dream); the live Vizro server
  stays Lane 1; `conf/local/credentials.yml` stays stubbed in the producer as today; AD-1 import boundaries hold.
  **Kinships:** [[pyforge-herald]] (the site), [[pyforge-steward]] (`pages.yml`, `ci resume`, the registry row).
  Owner `spec-pyforge-atlas` (CAP-41 amended); → `bmad-spec` after herald's, one M2 story for the handoff, one later
  story for Vizro. → CAP-62, CAP-63 / FR-70, FR-71 / Epic 30 / Stories 30.1–30.2, specced 2026-10-14.

- **2026-10-17 (kedro-viz-publish's stub credentials drifted) — Found: the producer cannot build the DAG export in CI,
  and its build task reports the failure as a success.** The operator lifted every CI pause on 2026-10-16 (PR #2247),
  which re-enabled `kedro-viz-publish.yml` after two months disabled by hand. Story 30.1 names the step after that:
  dispatch the workflow once and confirm the `kedro-viz-export` artifact. That run, `39002722593` on `990d796c7f`,
  failed in its `publish` job and uploaded no `kedro-viz-export`; the `vizro` job passed.
  **Evidence:**
  - `kedro viz build` logged `ERROR: Failed to build/deploy Kedro-Viz : "Unable to find credentials 'gitlab_token'
    ..."`. The next command, `normalize_viz_build.py`, raised `build does not exist -- run the viz-build pixi task
    first`, and the job failed on that line, one step after the cause.
  - The workflow writes its own stub `conf/local/credentials.yml` with two keys, `bigquery_adc` and `github_token`
    (`kedro-viz-publish.yml:122`-`:141` at `17670a0580`). `conf/base/catalog.yml` names eight. Story 27.2
    (`99af53f690`, 2026-10-04) added `gitlab_token`, `codeberg_token`, `npm_token`, `crates_token`, `rubygems_token`
    and `nuget_token` while the workflow was disabled, and updated `tools/bootstrap.py`'s stub, the second copy, but
    not the workflow's. The workflow's comment says its shapes mirror `tests/catalog/conftest.py`, which moved to
    `tests/unit/catalog/` on 2026-09-07.
  - kedro-viz 12.5.0's `create_shareableviz_process` catches every exception, prints it and returns
    (`kedro_viz/launchers/cli/utils.py:97`-`:98`), so `kedro viz build` exits 0 on a failed build. `viz-build` reads
    green, and the `depends-on` meant to stop a failed build from staging never fires.
  - Reproduced on a scratch copy of `17670a0580`: with no credentials file, and with the workflow's two-key stub (the
    two keys the operator's own local file carries too), `viz-build` exits 0, writes no `build/`, and names the first
    missing key. With `tools/bootstrap.py`'s eight-key stub it builds in 8.7 s. An all-`{}` stub and an all-pair stub
    both build, so the workflow comment's claim that `APIDataset`-family entries need an auth pair does not hold:
    viz only introspects the DAG.
  - Found by the story's independent review (`f52936ff75`): past the build, the job's flag step runs
    `print_viz_export_flag.py` in `-e pyforge-guild`, which cannot import `pyforge.atlas` (`ModuleNotFoundError`,
    exit 1; `enabled=true` in `-e pyforge-atlas`), so the upload would still not run. Latent since Story 30.1: no run
    had reached the step. Folded into the same story by orchestrator ruling.
  **What it looks like when fixed:** the workflow writes its stub from the one source `tools/bootstrap.py` holds, a
  test fails the day the catalog names a key that source lacks, `viz-build` exits non-zero when `kedro viz build`
  writes no build, and every atlas tool the workflow runs runs in `-e pyforge-atlas`. The next dispatched run uploads
  `kedro-viz-export`.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
  - The stub writer never overwrites a file that holds anything, and no credential, token or secret enters the
    workflow (AD-11).
  - The `vizro` job, the upload step, the artifact's name and retention, the flag gate (beyond its step's
    environment) and the CI-pause `if:` fragments do not change.
  - A new epic: Epic 30, which shipped the producer, is done.
  **Kinships:** [[pyforge-steward]] (the CI resume; `pages.yml`, whose Story 102.4 AC7 waits on the artifact,
  `DW-steward-102-4-1`). Owner `spec-pyforge-atlas` (CAP-62, the DAG export reaches Pages as a workflow artifact).
  → Epic 32 / Story 32.1, specced 2026-10-17.

- **2026-10-18 (the atlas CLI has no verbs) — Found: `pyforge atlas run --pipeline core`, the command atlas's skill,
  persona and parity gate all name, fails, and the one form that works reads the wrong project from the repo root.**
  The operator asked for a data refresh on 2026-10-17 and ran the skill's quick-start command from the repo root.
  **Evidence:**
  - `pixi run -e pyforge-atlas pyforge atlas run` exits 2 with `Error: Got unexpected extra argument (run)`;
    `pyforge atlas catalog list` exits 2 with `Got unexpected extra arguments (catalog list)`.
  - `pyforge.atlas.__main__.main` hands every argument to Kedro's `find_run_command`, which returns the `run` command
    itself, not Kedro's project command group. So the binary IS `run`: `ipython` and `package` are unreachable, and
    a bare `pyforge atlas` starts a whole-DAG run.
  - Four contracts say otherwise. The SKF skill `.claude/skills/pyforge-atlas` (Quick Start, Common Workflows, CLI)
    and the `bmad-agent-atlas` persona's RUN menu name `pyforge atlas run --pipeline <name>`. The FR-155 parity gate
    (`mcp/parity.py`, Story 24.3) derives its verbs from `kedro.framework.cli.project.project_group` (`ipython`,
    `package`, `run`), and `mcp/tools.py`'s `TOOL_SPECS` declares each `run_*_pipeline` tool's CLI as
    `["run", "--pipeline", <name>]`. The gate checks a verb exists in that group, never that the binary reaches it,
    so it has passed since 2026-09-10 while the binary reached none of them.
  - From the repo root, where the skill and canopy FR-13 say to run it, Kedro's `KedroSession.create` finds no
    `[tool.kedro]` project (`find_kedro_project` returns `None`) and falls back to the cwd: the repo root's own
    `conf/` (one `knowledge.yml`), not atlas's catalog. Every real run today goes through a pixi task whose `cwd` is
    the member dir. The MCP face already pins it (`mcp/session.py`'s `PROJECT_ROOT`, `bootstrap_project`). Measured
    2026-10-17 23:04, the operator's own bare `pyforge atlas` from the repo root: `MissingConfigException: Given
    configuration path either does not exist or is not a valid directory: <repo>/conf/local`, before any node ran.
    An older root-relative write survives as the gitignored `<repo>/data/raw/` (atlas staleness sidecars for
    `vulnerability_basilisk_raw`, `vulnerability_basilisk_detail_raw` and `vcs_migration_detail_raw`, dated
    2026-08-29).
  - Kedro 1.6.0 deprecates `--pipeline` in favour of `--pipelines` (a `KedroDeprecationWarning` on every use).
  **What it looks like when fixed:** `pyforge atlas run --pipelines core` runs atlas's `core` from any cwd against
  atlas's own `conf/`, the same project root the MCP face uses; `pyforge atlas ipython` and `pyforge atlas package`
  reach Kedro's commands; a bare `pyforge atlas` prints the verbs instead of running the DAG; a test fails the day a
  verb the parity gate counts is unreachable through the binary; the skill, the persona and `TOOL_SPECS` name the
  grammar the binary accepts, with `--pipelines`; listing datasets points at the MCP `list_atlas_datasets` tool.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
  - Kedro's routing is not reimplemented: the binary dispatches to Kedro's own `project_group`, the group the parity
    gate already reads (Story 24.3's boundary).
  - `--version` stays a first-token-only intercept that loads no Kedro (Story 7.1).
  - A new epic: the epics that shipped the CLI, the skill and the parity gate are done.
  **Kinships:** [[pyforge-steward]] (canopy FR-13, `pyforge <station> …` reaches the station binary unchanged;
  `pyforge-core` dispatch). Owner `spec-pyforge-atlas` (CAP-9, agents trigger and read the pipeline natively).
  → Epic 33 / Story 33.1, specced 2026-10-18.

- **2026-10-18 (atlas fills its own data) — Ruled: a plain `pyforge atlas run` fills every dataset a public source
  can fill, and the credentialed ones fill when the operator opts in; the VCS and registry fetches cover the whole
  conda-forge universe.** Operator rulings 2026-10-18 (AskUserQuestion, verbatim choices): "Wire the fetchers now";
  "In-package, public live (Recommended)"; "Full universe (Recommended)"; extras "Phase P via ClickHouse, Basilisk
  vulns, OpenTeams identity sources, Estate-source producer"; "Kedro first, legacy after".
  **Evidence:** the full unattended refresh of 2026-10-17 23:08 (`pyforge-atlas-bootstrap`, 76 nodes, exit 0 in
  121 s) left 40 of the 57 Parquet datasets on disk at 0 rows, among them every download table, `core_feedstock_health`,
  `core_dependencies`, `pypi_conda_mapping`, `pypi_current_versions`, every `vcs_*` primary, every vulnerability
  rollup and `identity_packages_primary`. The filled ones are package enumeration (34,666), the PyPI universe
  (916,440), EPSS (390,724), KEV, CWE and cross-channel flags. The legacy admin refresh the same night filled the same
  tables in `cf_atlas.db`. Root causes, read in code:
  - **R1, the cf-graph source moved.** `regro/cf-graph-countyfair` now redirects to `conda-forge/conda-forge-bot-data`,
    whose tarball has no `node_attrs/`, `pr_info/` or `version_pr_info/`; cf-scripts' settings put them in
    `conda-forge/conda-forge-bot-data-node_attrs`, `-pr_info` and `-version_pr_info`, sharded five directories deep
    (`get_sharded_path`). Atlas's `CfGraphTarballDataset` and the legacy Phases E, J and M read nothing (legacy, this
    run: E enriched 0 rows, J left `dependencies` at 0 rows, M updated 0).
  - **R2, the download sources are stubs.** `AnacondaDownloadsDataset.load()` and `S3DownloadStatsDataset.load()`
    return empty frames by design; `fetch_one` ignores its request key without a fetcher.
  - **R3, the Phase C mapping is circular.** `pypi_parselmouth_mapping_raw` reads the file only
    `export_pypi_conda_map` writes, from the mapping it should produce, so a fresh root never fills it, and every
    PyPI-keyed dataset downstream stays empty.
  - **R4, external-refresh stores have no refresher.** The vdb and OSV stores, the five OS-distro stores, trending,
    about-maintainers, the purl associator, the OpenTeams board and staged-recipes PRs are constructed with no
    `refresher`/`fetcher`, by the AD-13 "default `None` is offline" design; DW-B5-2 put the injection in a Dagster
    resource at the attended C1 bring-up, which has not happened.
  - **R5-R9.** Artifactory is off by default (`virtual_repos: []`; Story 24.2 stays `blocked`); the Basilisk and
    migration datasets have no driver node; `pypi_endoflife_raw` and `seed_spdx_upstream_list_raw` return a
    `requests.Response` the seed-gap nodes cannot read; the VCS batches derive from `identity_packages_primary`, the
    OpenTeams subset, which is empty; the GitHub query asks only for health, never releases or tags, and the
    `github_token` dict cannot authenticate `APIDataset`; Phase P ports only BigQuery, which the operator ruled off.
  **What it looks like when real:** on a fresh data root, `pyforge-atlas-bootstrap` followed by `pyforge atlas run`
  fills every dataset a public endpoint serves, and each one's row count sits within a stated tolerance of the legacy
  `cf_atlas.db` table it ports (recorded per story); with the operator's credentialed opt-in, the GitHub-backed VCS
  health, upstream versions, OpenTeams identity sources and the Basilisk population fill too. An unreachable endpoint
  still keeps last-good and marks stale (AD-13). The Vizro boards read populated stores.
  **Constraints:**
  - Public sources go live in-package by composing `kedro_datasets.api.APIDataset` (the Story 21.2 precedent) or
    `pyforge.core.process` for a subprocess; the no-inline-IO denylist does not change.
  - Credentialed calls run only when the operator opts in for that run (AD-11: attended-only); no gate or loop path
    makes one.
  - The VCS and registry population is the full actionable universe, as legacy's Phases K, L and N select it.
  - Phase P ports legacy's free ClickHouse source; BigQuery stays off.
  - The legacy cf-graph fix follows as its own conda-forge-expert story under mason's chain, after this effort.
  **Kinships:** [[pyforge-mason]] (the legacy `conda_forge_atlas.py` port target, R1's second half),
  [[pyforge-steward]] (`query_plane_estate_source`, declared by steward Story 34.2 and produced by nothing),
  [[pyforge-herald]] (the boards and decks that read these stores). Owner `spec-pyforge-atlas`; → `bmad-spec`.
- **2026-10-19 (the Vizro boards read what the pipelines write) — Found: with Epics 34-36 filling the stores, the
  Vizro boards still render honest-empty, on Pages and locally.** Operator rulings 2026-10-18, on "all links are still
  broken": "CI builds data first (Recommended)" and "Here, after Epic 34"; 2026-10-19 (AskUserQuestion, verbatim
  choices): "Data-first + 10 rewires (Recommended)", "Public-only Pages (Recommended)", "Weekly + on push
  (Recommended)".
  **Evidence:** a read-only audit of the 34 pages `build_dashboard` builds, 2026-10-19:
  - **The Pages export has no data.** `kedro-viz-publish.yml`'s `vizro` job checks out the repo and runs
    `vizro-static-export`: no atlas run, no data artifact, no data root.
  - **The dashboard reads another data root.** `dashboard.data.default_data_root()` walks up to `.git` and resolves
    `<repo>/data`, which holds only `raw/`; Kedro, run from the member, writes `src/shared/packages/pyforge-atlas/data`.
    A full local run is invisible to the boards unless `PYFORGE_ATLAS_DATA_ROOT` is set.
  - **20 of the 27 board paths are no catalog entry's `filepath`.** 12 boards are wired right and need data only; 10
    need their path or a projection changed (the four seed-gap boards read `primary/<x>_gap/` while `seed_gaps`
    writes `derived/seed_gaps_<x>_report/`; version-downloads, distribution-breakdown, behind-upstream, whodepends,
    live-catalog-coverage, universe-sbom); 6 need a node that does not exist (cve-watcher history, release cadence,
    find-alternative, export-purls, mapping-gap, bootstrap-index-health); 6 show an on-demand result (scan-project,
    env-inspect, inventory-match, add-handoff, library-futures, recommend-2027) and stay empty by design until a user
    runs the tool.
  - A path changed alone raises `AttributeError` in the loader (`_bsl_query_or_empty` catches only `TypeError`), so
    each rewire changes the semantic model's expressions too.
  **What it looks like when real:** locally, a `pyforge atlas run` followed by `dashboard-dryrun` shows the 12 wired
  boards and the 10 rewired ones with rows; on Pages, a weekly (and on-push) job builds the public atlas data first,
  then exports the boards, so the same 22 boards carry public data; the identity boards, whose rows come only from a
  credentialed or internal run, show their honest-empty notice on Pages. The 6 new-node boards are backlog stories.
  **Constraints:**
  - The Pages job runs public sources only (AD-11): no secret, no `PYFORGE_ATLAS_CREDENTIALED`, BigQuery off.
  - A board's dimension names stay (the dryrun and provenance tests pin them); only paths and expressions change.
  - The export never publishes a board that declares an access column (`sld:AD-10`, CAP-63's refusal).
  **Kinships:** [[pyforge-herald]] (the Pages mount at `/dashboard/vizro/`), [[pyforge-steward]] (the Pages consumer
  of the artifact, steward 102.4). Owner `spec-pyforge-atlas` (CAP-63 amended; a new CAP for the board wiring);
  → `bmad-spec`.
- **2026-10-22 (filled boards still read "Data gap")** — **Found: every board note says "Data gap", including on boards
  that now hold data.** After Story 37.4, the Pages export shows 21 of 34 boards with data. Behind-upstream lists 95
  rows under a note that opens "**Data gap:** Wired to `build_behind_upstream_model`…". `dashboard/app.py` labels every
  `PageDef.note` that way in `_legibility_card` and in the identity-workbook page. Most notes now describe how a
  board's data is wired, not what is missing. Only three cases are gaps: a shell page with no data function, the
  identity workbook's `gap_message`, and a page whose own dataset is unavailable (its AD-17 stamp says so). **What it
  looks like when fixed:** a note on a page with a data function and an available dataset reads "**About this board:**";
  "**Data gap:**" stays for those three cases. The static export still drops the live-scan note whichever label it
  carries. **Constraints:** a fix under CAP-63 / CAP-69, with no CAP and no flag; the label only, no board's data or
  note text changes. Owner `spec-pyforge-atlas`. → Epic 37 / Story 37.11, specced 2026-10-22.
- **2026-10-24 (the semantic store has its upload times and archived flag)** — **Found: three boards read
  "unknown" or empty because `semantic_packages` holds no upload time and no archived flag.** It declares
  `latest_conda_upload`, `latest_upload_age_days`, `releases_30d` and `total_versions` NULL ("D2 wires the inputs"),
  so the adoption-stage board reads `unknown` for every package and find-alternative ranks every candidate as fresh
  (DW-atlas-37-6-2). Its `feedstock_archived` joins only the GitHub archive query, empty on a public run, so it marks
  none of the 828 packages attributed to an archived feedstock (DW-atlas-37-7-2). Version-downloads' `upload_date` is
  null too. Story 37.6 now streams every version's upload times out of the full repodata, and the cf-graph carries the
  archived flag. **What it looks like when fixed:**
  - `semantic_packages` fills the four columns as legacy does: the upload time of the latest version's newest build,
    its age, the versions released in 30 days, and the version count;
  - `feedstock_archived` adds the cf-graph flag through attribution;
  - version-downloads shows each version's upload date.

  **Constraints:**
  - the boards' dimension names stay;
  - no core output changes;
  - the version-downloads path moves behind `pyforge.atlas.board_projections`, like Epic 37's boards.

  Owner `spec-pyforge-atlas` (CAP-69, no new CAP). → Epic 38 / Story 38.1, specced 2026-10-24.
- **2026-10-24 (one vulnerability feed down stops the whole build)** — **Found: when cwe.mitre.org does not answer,
  no Pages data build finishes.** `vulnerability_feeds.py`'s `CisaKevDataset`, `EpssFeedDataset` and
  `CweCatalogDataset` load through `APIDataset` with no fallback, so a connection failure raises `DatasetError` out
  of the catalog and stops the run. kedro-viz-publish's Vizro job failed on five consecutive merges to main on
  2026-10-23 with `vulnerability_cwe_catalog_raw: Failed to connect to the remote server` (a connect timeout; runs
  39908595513, 39931632612, 39941141589, 40018149689, 40027620039), and Pages kept its last export each time
  (DW-atlas-38-1-1). The three feeds also send no timeout, and requests reads `~/.netrc` for their hosts. **What it
  looks like when fixed:**
  - each feed keeps its last good frame under the entry's own path in the data root;
  - a failed fetch, an HTTP error or a body that does not parse to rows serves that copy (or, on a fresh root, the
    empty frame of the feed's columns) under the AD-13 staleness marker, and the run goes on;
  - the bootstrap-index-health board reads each feed's marker: `stale` with the reason while a copy exists, `missing`
    with the same reason on a fresh root.

  **Constraints:**
  - a fix under CAP-64, with no new CAP and no flag: the feeds fetch on every load, as they do today;
  - no test reaches the network, and no run sets `PYFORGE_ATLAS_CREDENTIALED`;
  - the vulnerability nodes and their outputs do not change.

  Owner `spec-pyforge-atlas` (CAP-64, no new CAP). → Epic 34 / Story 34.12, specced 2026-10-24.
- **2026-10-24 (on Pages, last-good has nothing to keep)** — **Found: Story 34.12's fallback cannot help the build
  that needed it.** A feed that cannot be reached now serves its last good copy, but the kedro-viz-publish `vizro`
  job starts every run from a fresh checkout: the data root (`src/shared/packages/pyforge-atlas/data`) is empty, so
  there is no copy. An outage of a public source on Pages still publishes that source's table empty under its
  marker, and the bootstrap-index-health board reads `missing` (Story 34.12's residual risk). The same holds for
  every public store that keeps a last-good copy: the `raw/` copies, the download and upload aggregates, the
  discovery indexes and the OSV store. **What it looks like when fixed:**
  - the job restores the previous run's last-good copies before it builds, and saves this run's after a build
    that succeeds;
  - an outage of a public source on Pages serves the previous copy under its marker, so the board reads `stale`
    with the reason, and provenance reports the copy's age;
  - a store inside its refresh cadence, or one whose host says it has not changed, is not fetched again, as on a
    workstation.

  **Constraints:**
  - a fix under CAP-63 (the Pages job, amended 2026-10-19) and CAP-64 (AD-13 last-good), with no new CAP and no
    flag;
  - what persists is what a dataset reads back as its own previous copy: `raw/` and the stores, where each keeps
    its last-good copy, and the vulnerability snapshot history the cve-watcher diffs; never the 9.6 GB
    vulnerability database store, and no other output-layer file, so a stopped node's table in `intermediate/`,
    `primary/` or `derived/` cannot hide behind last week's file;
  - the copies are kept in the repository's Actions cache; they reach the weekly run only once the operator raises
    the cache limit (operator ruling 2026-10-24, "Cache + raise limit"; DW-atlas-37-12-1);
  - the job stays public-only (no secret, no token, no `PYFORGE_ATLAS_CREDENTIALED`; AD-11), and a failed build
    still fails the job.

  Owner `spec-pyforge-atlas` (CAP-63, CAP-64, no new CAP). → Epic 37 / Story 37.12, specced 2026-10-24.
- **2026-10-24 (an earlier run's cve-watcher diff reads as current)** — **Found: on Pages, a run whose vulnerability
  database build fails publishes the previous run's cve-watcher diff under a fresh stamp.** Story 37.12 keeps the
  vulnerability snapshot history between Pages runs, but never `stores/vdb`, which every run rebuilds. When that build
  fails, `vulnerability_package_rollup` is empty, `SnapshotHistoryDataset.save` appends nothing, and
  `diff_vulnerability_snapshots` diffs the same two snapshots as the run before. The board shows no snapshot date, and
  its AD-17 stamp is the diff file's mtime, so the old diff reads as current with no marker (DW-atlas-37-12-3, Story
  37.12 review 4). **What it looks like when fixed:**
  - a save that appends no snapshot (an empty frame, or a store that cannot be read) leaves the AD-13 staleness marker
    beside the snapshot store, and the next save that appends one removes it;
  - the cve-watcher's AD-17 stamp is its latest snapshot's time (or the diff file's, if that is older), not the time
    the diff file was last rewritten; while the store carries the marker, the stamp line says the diff is stale and
    why;
  - with no snapshot store, the board reads as a data gap, not as an empty table stamped now;
  - the bootstrap-index-health board reads the snapshot store's marker as `stale`, as it reads every other store's.

  **Constraints:**
  - a fix under CAP-69 (the boards no pipeline feeds) and CAP-64 (AD-13 markers), with no new CAP and no flag; the
    board change stays behind `pyforge.atlas.board_projections`, as Story 37.5's board does;
  - the diff's rows and columns do not change: an earlier diff keeps its rows, now dated by its own snapshot;
  - no other board's stamp changes.

  Owner `spec-pyforge-atlas` (CAP-69, CAP-64, no new CAP). → Epic 37 / Story 37.13, specced 2026-10-24.
- **2026-10-24 (the distribution-breakdown grid wait under load)** — **Found: the declared-controls e2e test fails
  under parallel load while the page is healthy.** `test_declared_controls_render_against_real_rows` red the
  `pyforge-atlas-test` lane of a full-scope `pr-preflight` on 2026-10-24 (Story 37.13, PR #2300) with
  `Locator expected to contain text 'linux-64'` on `#distribution-breakdown--grid`: the grid was still
  `data-dash-is-loading="true"`, then empty, when Playwright's 5 s default ran out. The suite took 3:57 there against
  about 44 s alone; the test passed the run before and three times alone. It failed the same way in Story 31.1's
  preflight on 2026-10-15 (`DW-atlas-retro-2026-10-15-1`).
  **Evidence:**
  - Vizro builds every AgGrid as an empty placeholder and fills it from the page's `on_page_load` callback; the
    browser then applies that output and loads dash-ag-grid's lazy grid chunk (`async-community.js`) before the grid
    mounts. The facet filter (static since Story 27.5) and the chart's container render from the layout, so the
    test's three 15 s waits did not wait for that callback, and the grid assertion alone carried it under the 5 s
    default.
  - Reproduced under load: 32 copies of the real test body on 16 xdist workers beside 48 busy-loop processes failed
    4 of 24 copies that got a server, with the same message and the same `data-dash-is-loading`-then-empty call log
    (4 of 31 beside 32 busy loops; 4 of 25 beside 48 again after a host reboot).
  - Timed in the page (a `MutationObserver`) under that load: the filter, its dropdown and the chart were visible
    before the grid mounted in every copy; the grid mounted up to 20.8 s after navigation and up to 16.9 s after the
    chart, with the `linux-64` row within 1 ms of the mount. The `on_page_load` request took at most 1.9 s there, so
    most of the time is the busy browser, not the Vizro server.
  - A first fix, a 15 s mount wait after the chart, still failed 3 of 24 copies in one counted batch, on the
    dropdown's own 15 s wait: under load every step can take longer than 15 s, so budgets per step do not fit.
  - The file's two other grid tests (the navigation walk and the grounded pages) check grids filled the same way
    under the same 5 s default; their pages draw no chart and render sooner, and under the same load they failed 0 of
    30 copies, so the exposure there is real but did not reproduce.
  **What it looks like when fixed:** right after the page opens, the test waits up to 60 s for the AG Grid to mount
  inside `#distribution-breakdown--grid`, the element drawn last, with the budget the suite gives a loaded host (the
  fixture's server bind, the WASM smoke); then it checks the filter, its dropdown, the chart and the row as before.
  Every other grid check in the file waits for its grid's mount the same way, through one helper. Under the same
  load no copy fails its assertions (setup errors, the fixture's server not binding within 60 s at that synthetic
  load, are counted apart), and a fixture root without the `linux-64` row still fails on the row, with the grid's
  actual text.
  **Constraints:**
  - A `fix` story: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1). Test-only: the e2e file's grid checks
    change, and no skip, `xfail`, retry or rerun is added (AD-11: gates are never weakened); every assertion stays.
  - It goes into Epic 27, which owns this test (Stories 27.3 and 27.5), and reopens it until it lands.
  **Kinships:** [[pyforge-steward]] (the pre-push preflight lane that surfaced it). Owner `spec-pyforge-atlas` (CAP-8,
  the read surface). → Epic 27 / Story 27.6, specced 2026-10-24.
- **2026-10-25 (the PRD's FR arrows were counted, not traced)** — **Found: most of the atlas PRD's `FR-n ← CAP-m`
  arrows name the wrong capability.** The 2026-09-17 one-chain fold (`86d1cdf3ee`) appended an arrow to every FR
  heading by counting: FR-1..FR-22 read CAP-1..CAP-22, and FR-61..FR-68 read CAP-1..CAP-8. The PRD's own
  `## Fold provenance (2026-09-17)` says so ("Kernel FR-1..FR-22 ← CAP-1..CAP-22"). Only FR-3, FR-8, FR-12 and FR-13
  landed on the right capability. FR-1 (catalog-declared IO) cites CAP-1 (the DAG is the orchestrator); FR-10 and
  FR-11 are swapped; FR-19..FR-21, the three new signals, cite the Unity satellite's CAP-19..CAP-21; FR-64..FR-68 cite
  kernel CAP-4..CAP-8, while their own capabilities are CAP-53..CAP-57. A fleet audit the same day, after marshal
  Story 105.1 fixed the same defect on marshal's PRD (PR #2314), found atlas the worst case. Doctor's `fr-without-cap`
  checks only that a cited CAP exists, and atlas FR-1..FR-68 are in `docs/governance/fr-baseline.json`, so nothing
  noticed. **What it looks like when fixed:** every arrow names the capability that realizes the requirement, traced
  from evidence, not position: the FR title against the CAP title, the CAP's full success text from before the fold
  (`86d1cdf3ee^`, because the station Spec cut each bullet to its first line), and the `← spec-<old> CAP-k` provenance.
  Three requirements have no capability. FR-61 and FR-63 come from `spec-kedro-org-tooling-adoption`'s plain-list
  "Capability 1" and "Capability 3", which the fold never minted; FR-15 (Pixi-first, conda-forge-only) comes from a
  Spec constraint. They keep their arrows until the operator picks a source.
  **Constraints:**
  - a chore under `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-3 (the station fold procedure),
    with no CAP, no flag, no `SPEC.md` change and no detector change;
  - only arrow text moves: no FR number, title or body;
  - the Unity and Wasm satellite FRs, whose ids collide with the kernel's, are a separate decision (a renumbering, as
    Story 39.2, only on an operator ruling).

  Operator rulings 2026-10-25 (AskUserQuestion, verbatim choices): "Approve as proposed (Recommended)" (the 23-heading
  table), "Drop the arrow (Recommended)" (the `### FR-61..FR-68 delivered` summary heading), "Append a correction
  (Recommended)" (the fold-provenance line). Owner `spec-pyforge-atlas`. → Epic 39 / Story 39.1, specced 2026-10-25.
- **2026-10-25 (the nixpkgs store decodes brotli by luck)** — **Found: atlas imports brotli without declaring it.**
  The nixpkgs Tier-3 index is `packages.json.br`, and `datasets/tier3_sources.py` decodes it through a guarded
  `importlib.import_module("brotli")` (`_brotli_decompress`, `NixpkgsPackagesDataset._frame`). The atlas env has the
  module only because conda-forge's `urllib3` depends on `brotli-python`; PyPI's `urllib3` makes brotli an extra, so
  a pip install of pyforge-atlas has none and the store marks itself stale (`DW-atlas-34-5-1`, Story 34.5's review).
  The 2026-10-25 atlas retro lists it as candidate fix 2. **What it looks like when fixed:** both manifests declare it
  at the floor the env already resolves, `brotli>=1.2` in `pyproject.toml` and `brotli-python = ">=1.2"` in the
  package `pixi.toml`, as the `filelock` and `numpy` lines are declared; `pixi.lock` records the same string, so a
  fresh pixi reads the lock as current; the dependency-parity test maps the PyPI name to the conda name, and the
  library catalog lists it. **Constraints:**
  - a fix under CAP-64 (Story 34.5's nixpkgs source), with no CAP and no flag; no new package enters the env;
  - the import stays guarded, so a missing module still reads `stale` rather than raising.

  Operator ruling 2026-10-25 (AskUserQuestion, verbatim choice): "brotli + brotli-python (Recommended)". Owner
  `spec-pyforge-atlas` (CAP-64, no new CAP). → Epic 34 / Story 34.13, specced 2026-10-25.
- **2026-10-25 (twelve pipelines, eight triggers)** — **Found: the spine and the MCP face still count the pipelines
  the station had before Stories 19.3 and 37.10.** `register_pipelines()` registers twelve pipelines, eleven of them in
  `__default__` (`catalog_index` runs after a build). AD-3's 2026-08-26 amendment names the sealed seven plus three
  as-built packages and says its rule "holds across all ten"; `semantic_packages` (Story 19.3) and `catalog_index`
  (Story 37.10) were never written in. The MCP face calls its eight-name trigger set (`PIPELINE_NAMES`) "the registered
  pipelines": the `list_atlas_pipelines` tool's served description (`mcp/server.py`), `TOOL_SPECS`, a docstring and a
  comment in `mcp/tools.py`, the audit test's docstring and the station skill. The retro recorded both as divergences
  (Finding 7, candidate fixes 4 and 5). **What it looks like when fixed:** AD-3's amendment, edited in place as its
  earlier amendments were, names all twelve and says which run in `__default__`; every MCP text names its eight as
  the MCP-triggerable pipelines, and the four CLI-only pipelines stay CLI-only by design. **Constraints:**
  - a fix under CAP-9 (agents trigger and read the pipeline natively), with no CAP and no flag;
  - wording only: no pipeline, tool, trigger set or registry changes; no test assertion changes;
  - the sealed seven stay sealed (AD-3's rule is unchanged; only its enumeration grows).

  Owner `spec-pyforge-atlas` (CAP-9, AD-3, no new CAP). → Epic 33 / Story 33.2, specced 2026-10-25.
- **2026-10-25 (FR-15, FR-61 and FR-63 had no capability to name)** — **Ruled: restore two capabilities, and let FR-15
  cite its constraint.** Story 39.1 left three FRs on the fold's counted arrows and opened `DW-atlas-39-1`. FR-61
  (kedro-skills audit-then-adopt) and FR-63 (a recorded vscode-kedro verdict) come from
  `spec-kedro-org-tooling-adoption`, which listed its capabilities as a plain numbered list; the 2026-09-17 fold minted
  CAPs only from `CAP-n` lines, so Capabilities 1 and 3 were dropped while atlas Stories 11.1 and 11.3, which delivered
  them, stay done. FR-15 (Pixi-first, conda-forge-only) derives from the Spec's Constraints, not from any capability.
  **What it looks like when fixed:** `spec-pyforge-atlas` declares the two as shipped CAP-70 and CAP-71, with that Spec
  as their provenance; FR-61 and FR-63 cite them; FR-15's arrow names the constraint "Conda-forge-only, pixi-managed,
  py3.14-floored provisioning". **Constraints:** a chore under `spec-one-chain-per-station` CAP-5 and CAP-3; two CAPs
  restored, rendered into `SPEC.md` by script from the memlog decision; no flag; no FR text change; the satellite FR
  series untouched. Operator rulings, 2026-10-25: "Restore 2 atlas CAPs (Recommended)" and "Cite the constraint
  (Recommended)". Owner `spec-pyforge-atlas`. → Epic 40 / Story 40.1, specced 2026-10-25.

## 2026-09-17 — One-chain fold (atlas, CAP-3)

Atlas rebases to one Dream, one Spec, one PRD, one spine, one epic chain.
Topic Dreams are archived in place with `Consolidated into [[pyforge-atlas]]`
banners. Station Spec `spec-pyforge-atlas` is `ready`. Epic 12–25 rekey to
11–24 to close the missing Epic 11 gap. Done rows keep status; `25-2` stays
`blocked` as `24-2`.

Folded topic Dreams: [[artifactory-download-intelligence]], [[atlas-kedro-catalog-expansion]], [[atlas-query-dashboards]], [[conda-forge-packaging-inventory-operations]], [[enterprise-data-models-and-apis]], [[kedro-org-tooling-adoption]], [[microsoft-org-sweep]], [[pyforge-atlas-intelligence-platform]], [[unity-data-stack]], [[upstream-discovery]], [[wagtail-corporate-brain]], [[wasm-analytics-stack]].
- **2026-10-26 (every requirement derives from a capability) — Found:** FR-15 cited a Spec Constraint, not a capability (the 2026-10-25 ruling for Story 40.1); the 2026-09-17 fold cut 86 of the Spec's intent and success bullets at their first line; none of the ten NFR lines cites anything; the Unity and Wasm satellite PRDs reuse the kernel's FR ids (39 duplicates) and carry no arrows. **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it"): a requirement cites one or more defined capabilities and nothing else — `spec-one-chain-per-station` CAP-5 as amended, CHAIN-STANDARD § 12. **For atlas:** CAP-72 is minted from the Constraint "Conda-forge-only, pixi-managed, py3.14-floored provisioning" (ruling (b)) and FR-15 cites it; AD-16 names the Constraint; the cut bullets are restored by script from `86d1cdf3ee^` with every id stable; the satellite renumber (ruling (d)) and the NFR backfill (ruling (c)) are minted `backlog` as Stories 41.2 and 41.3 so the detector's baseline has an owner for every atlas row it still carries. Epic 41 / Story 41.1, built in the one-PR effort with the other seven stations; CAP-72 routes `rebuild` (ruling (e)).
