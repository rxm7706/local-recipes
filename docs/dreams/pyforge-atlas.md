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
- **2026-10-26 (every pre-rule runtime capability sits behind a kill switch) — Found:** the flag inventory (doctor Story 34.4, regenerated on the fixed join) reads 3 atlas capabilities minted before the rule date as reachable at runtime with no flag; the operator ruled on 2026-09-28 that every capability ships behind a flag, with one retrofit flag per capability defaulting ON (Q6), and no station had minted its retrofit. **Ruled** (2026-10-26, operator: the CAP-7 retrofit sheet approved as recommended, R1–R8 — flag the unflagged runtime rows only, one key per CAP, an invariant's switch makes the dependent verb refuse, the 90-day clock stands and each station mints its retirement story now). **For atlas:** 2 keys `pyforge.atlas.<capability>` ON in dev, staging and production with their clocks from 2026-10-26, each read through `pyforge.core.flags` at its verb or behaviour site with one two-state test; a flag-off verb stays listed and refuses with the usage code 2 (Q3); no exit code changes. Epic 42 / Stories 42.1–42.3, built in the one-PR retrofit effort; Story 42.4 (the retirement, due 2027-01-24) minted backlog; no atlas CAP minted.
- **2026-11-01 (the EGM fleet audit) — Found:** the one-time fresh-context audit (marshal Story 113.7,
  spec-pyforge-marshal:CAP-302) read CAP-64..CAP-69 and Epics 34-37: 30 findings, 23 accepted, 6 rejected, 1
  deferred; residue `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`.
  Most accepted findings are Spec text the later stories outgrew; the CAPs re-derive in the 113.7 PR. Fixed in
  the same PR: Story 34.14 (a plain run on a fresh data root exits 0, CAP-64), Story 34.15 (the three core
  sources keep last-good when the network is refused, CAP-64) and Story 35.5 (the legacy VCS branch honours the
  credentialed switch, CAP-65). **Ruled** (operator, 2026-11-01): CAP-64's parity tolerance is a per-row floor,
  the story-close measurement against the same-day legacy figure, recorded in the Spec's `live-sources.md`
  companion; this amends the 2026-10-18 entry's "recorded per story". Also realized since that entry: Story 36.1
  (the Basilisk population runs, CAP-66). The 2026-10-18 probe found the advisory endpoints answer 401
  (`www-authenticate: Bearer`), so the advisory drivers send a token from `PYFORGE_ATLAS_BASILISK_TOKEN` only
  under the credentialed opt-in, and the advisories stay stale until the operator adds one (`DW-atlas-36-1-1`).
  Still open: CAP-68's missing steward export owner, deferred with a steward deferred-work row.

## 2026-10-26 — An enterprise Artifactory mirror's own download telemetry joins the universe picture (folded from artifactory-download-intelligence)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/artifactory-download-intelligence.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/artifactory-download-intelligence.md`.*

## An enterprise Artifactory mirror's own download telemetry joins the universe picture

### The Dream

Atlas already answers "what does the PyPI/conda-forge universe look like" — enumeration,
enrichment, cross-ecosystem mapping, download counts — at universe scale, from public sources
(the PyPI Simple index, BigQuery's public download dataset, parselmouth's compressed mapping).
What it cannot answer is the narrower, org-specific question a platform engineer with their own
Artifactory mirror actually wants: "what is THIS ORGANIZATION actually pulling, from ITS OWN
repository, and which of those pulls have no public counterpart at all" — because that requires
querying a specific Artifactory instance's AQL API, which atlas has never had a reason to do
(atlas's download signal is BigQuery's public dataset, not any one org's private pull telemetry).
This Dream is that missing join: enrich atlas's already-universe-scale picture with one
organization's own Artifactory download reality, and flag whatever in that reality has no public
PyPI presence at all — the one thing a universe-scale public crawl can never see on its own.

### What it looks like when real

- An Artifactory AQL query resolves virtual-repo topology to backing repositories and aggregates
  downloads by package name and version — the one genuinely new capability, since nothing in
  atlas's existing pipeline talks to any org's private Artifactory instance for this purpose.
- Every result is enriched through atlas's EXISTING machinery, not a second parallel enrichment
  path: PyPI metadata via atlas's own PyPI-facing phases, conda-forge cross-referencing via the
  SAME parselmouth mapping atlas's Phase C/C.5 already consumes.
- A package pulled from Artifactory with no PyPI presence at all is flagged internal/private —
  the one thing atlas's universe-scale crawl structurally cannot see (it only knows what's public).
- Output composes with atlas's existing surfaces (its own DB, `export-purls`-shaped output) rather
  than inventing a second, disconnected report format; an Excel governance view can be a rendering
  of the same underlying data atlas already tracks, not a separate pipeline.

### What is real

The overlap with atlas's existing `pypi_intelligence` pipeline (`src/pyforge/atlas/pipelines/pypi_intelligence/`)
is substantially larger than the source dream's own framing suggests — checked directly against
`nodes.py`, not assumed:

- **Phase D** already enumerates the full PyPI universe from the Simple index.
- **Phase H** already fetches current PyPI versions, serial-gated for efficiency (never-fetched /
  serial-moved / 30-day safety re-check eligibility).
- **Phase O** already snapshots PyPI serials on a 90-day rolling window, deriving an activity band
  from the deltas.
- **Phase P** already fetches monthly PyPI download counts — via BigQuery's public dataset, under
  a documented two-layer cost gate — the same *kind* of signal the source dream wants, from a
  different (public, not org-private) source.
- **Phase C / Phase C.5** already join PyPI↔conda-forge identity via the SAME parselmouth
  `compressed_mapping.json` the source dream names, extended with source-URL-derived matches
  beyond parselmouth's own coverage.
- **Phase R** already enriches with deterministic packaging-shape classification.
- Disk-based response caching, credential precedence (CLI → env → NETRC), and enterprise
  SSL/certificate support already exist repo-wide via `_http.py`'s truststore + JFrog/GitHub/.netrc
  auth chain, used by every atlas phase that makes a network call.

Genuinely missing: any code path that queries a SPECIFIC org's Artifactory AQL API for ITS OWN
download telemetry (atlas's Phase P is public-BigQuery-sourced, not any one org's private
Artifactory), and the internal/private-package flag this telemetry alone can produce (public-only
crawls have no way to see a package that was never public in the first place).

### Constraints

- **Enrich atlas's existing pipeline; do not fork a second one.** A result from this Dream's
  Artifactory query joins the SAME identity space (`Phase C`'s mapping, `Phase D`'s enumeration)
  atlas already maintains — it does not stand up a parallel PyPI-metadata or conda-forge-crossref
  path that could drift from the one atlas already has.
- **Enterprise credentials route through `_http.py`'s existing auth chain** — no second,
  bespoke Artifactory credential-resolution path.

### Non-goals

- **Not conda-forge download statistics** — the source dream's own v1 scope excludes this too;
  carried over unchanged.
- **Not npm download statistics** — same, carried over unchanged.
- **Not a web dashboard** — output composes with atlas's existing surfaces; a UI, if ever wanted,
  is a separate decision.
- **Not deciding which specific Artifactory instance this targets** — like
  [[package-inventory-eligibility]]'s own deferred Artifactory adapter, this presupposes a real
  target environment that hasn't been named yet; this Dream captures the CAPABILITY, not a
  commitment to a specific enterprise deployment.

### Full feature audit against `python-supply-lens`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| Artifactory AQL querying (virtual-repo resolution, download aggregation) | **Included, new** | The genuine gap — nothing in atlas talks to a private Artifactory instance today. |
| PyPI metadata enrichment (latest version, project URLs, GitHub link) | **Reused, already exists** | Atlas's Phase D/H/O already do this at universe scale; this Dream joins into it rather than re-fetching independently. |
| Conda-forge cross-referencing via parselmouth | **Reused, already exists** | Atlas's Phase C/C.5 already consume the identical `compressed_mapping.json`, extended beyond it with source-URL matching. |
| Internal/private package detection | **Included, new** | The one signal a universe-scale public crawl structurally cannot produce alone — genuinely needs the Artifactory-side telemetry this Dream adds. |
| Disk-based response caching (configurable TTL, force-refresh, cache-only) | **Reused, already exists** | Every atlas phase making a network call already caches; a new Artifactory adapter should follow the same convention, not invent a second caching layer. |
| Dual Excel + JSON output | **Reconsidered** | JSON: atlas already has structured output surfaces this should compose with rather than duplicate. Excel: no current atlas output targets Excel — if wanted, it is a rendering of atlas's existing data, decided at Spec time, not a second pipeline. |
| Credential management (CLI → env → NETRC, bearer token, enterprise SSL) | **Reused, already exists** | `_http.py`'s truststore + JFrog/GitHub/.netrc chain already provides this repo-wide. |
| Observability (structured logging, run manifests, package-level traceability, degraded-but-usable execution) | **Reused, already exists** | Atlas's own Kedro-pipeline logging and phase-level manifests already cover this; a new phase inherits it rather than reimplementing. |

### Kinships

[[pyforge-atlas]] (the estate this extends — Phase C/C.5/D/H/O/P/R are all direct prior art) ·
[[package-inventory-eligibility]] (the sibling Warden dream with the same deferred
"which specific Artifactory instance" open question — captured independently, not because the two
dreams should merge: one is estate-wide PyPI/conda-forge intelligence, the other is enterprise
eligibility provenance)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Substantially re-scoped from the source's own framing after checking atlas's actual
  `pypi_intelligence` pipeline directly (`nodes.py`'s Phase C/C.5/D/H/O/P/R) rather than assuming
  the source dream's premise that this capability doesn't exist yet — it mostly does, at greater
  scale than the source dream's own v1. Renamed from `python-supply-lens` to reflect the narrowed
  scope: only the Artifactory-telemetry join and the internal/private-package flag it enables are
  genuinely new; everything else the source dream described is already atlas's, checked line by
  line against real code rather than trusted from the source's own "What it owns" list.
- **2026-08-14** — Spec authored (spec-artifactory-download-intelligence, pyforge-atlas) per
  operator decision: mock-first injectable — no named instance; AQL adapter + internal/private
  flag join Phase C's identity space through _http.py's auth chain, mock-verified; live wiring
  stays a later attended step.

- **2026-09-09** — Fleet readiness pass (operator batch § 2.1, row atlas-B3). **Excel governance
  rendering is DECLINED permanently** and recorded as a Non-goal; the Spec's first open question
  closes. It was already a Non-goal in the Spec's own text, this Dream's own feature audit called
  Excel "Reconsidered", and the station has since shipped Stories 23-8 (workbook-free metrics
  universe) and 23-9 (quartet workbook retirement) with
  `scripts/tests/test_quartet_no_xlsx_surface.py` asserting zero workbook surface — keeping the
  question open would have contradicted a passing test. The second question ("which live
  Artifactory instance, and when") is not a gap at all: it restates the Spec's own binding
  Non-goal, so it is recorded as a deferred operator event. With both retired, the Spec is
  recommended `ready` → **`shipped`**: Stories 15-1/15-2/15-3 are `done`,
  `artifactory/aql_adapter.py`'s `_unconfigured_transport` refuses exactly as CAP-1 requires, and
  the Spec's own success signal is explicitly the mock-verified run — which is met. This Dream
  stays `specified`; the live bring-up remains outside the Spec.

## 2026-10-26 — Expand the Atlas Kedro catalog so live indexes match the packaging inventory (folded from atlas-kedro-catalog-expansion)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/atlas-kedro-catalog-expansion.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/atlas-kedro-catalog-expansion.md`.*

## Expand the Atlas Kedro catalog — self-contained, inventory-aligned

### The Dream

[[pyforge-atlas]] already runs a declarative Kedro catalog — conda-forge backbone,
PyPI intelligence, vulnerability overlays, VCS health, discovery tracks. The
[[conda-forge-packaging-inventory-operations]] dream runs a **separate** quartet
(live-endpoint verification + priority + OpenTeams handoff). Both need the **same
live indexes** for verification (PyPI yes/no, conda-forge yes/no, cross-channel
presence, Basilisk catalog, AOSS lists, Anaconda defaults). Today those indexes
are duplicated, partially implemented, or only reachable through one toolchain.
**The Excel workbook is out of scope for this dream** — catalog entries are live
fetches with AD-13 last-good Parquet; inventory orchestration consumes those outputs.

The dream has **four closure tracks**:

1. **Catalog completeness (Epic 21)** — one catalog surface: every live source the inventory
   dream depends on is declared in `conf/base/catalog.yml`, fetched at the **dataset**
   layer (AD-2 — nodes stay pure), routed through `${globals:…}` override points
   (AD-13), and materialized as Parquet the BSL, dashboard, and inventory quarter
   can all read. No second HTTP client in scripts for **public index verification**.

2. **Kedro self-containment (Epic 21)** — pyforge-atlas can run its **own** bootstrap chain
   (external-refresh stores + seven pipelines) on a **dedicated data root**, without
   requiring a prior legacy `bootstrap-data` run or reading `cf_atlas.db` at
   dataset load time. Legacy `cf_atlas` and conda-forge-expert **keep working in
   parallel** — this dream does not retire them; it removes the *dependency* so
   Kedro is not a passenger on the legacy store.

3. **Identity pipeline in Atlas (Epic 21 Phase D)** — re-implement the inventory quartet's PURL
   Associator join, OpenTeams project 1 board ingest, and identity gist publish
   as catalog sources + derived nodes in **`upstream_discovery`** (extended, not a
   9th pipeline). Inventory scripts become thin orchestrators over Parquet exports,
   not parallel HTTP/GraphQL clients.

4. **Complete export + zero deferred (Epic 23 / CAP-8)** — Tier 3 OS indexes, enterprise
   JFROG telemetry, priority assignment, deliverable A, and gist/dashboard aggregates
   all land as Kedro Parquet; **`identity_complete_export.parquet`** is the single
   canonical surface. See `complete-export-contract.md` — enterprise builds
   **`enterprise_jfrog_consumption.parquet`** (§1) to close the dream.

The 2026-08-29 admin bootstrap proved the **combined** path works (legacy store +
seven Kedro pipelines). Steady-state for Kedro is: catalog-owned fetch, one env-var
block, one atlas data root — with optional SQLite seed only as a documented
migration bridge, not the only path.

### From training wheels to self-contained (Kedro only)

Today’s Kedro coupling (documented after the bootstrap session):

| Training wheel | What it does today | Steady-state replacement |
|----------------|-------------------|-------------------------|
| `cf_atlas.db` seeds | `pypi_json_raw`, GitHub/VCS/registry datasets read SQLite at `load()` when live fetch is off | Upstream Parquet from prior pipeline outputs, or live fetch in the dataset |
| `globals.yml` defaults | `vdb_store`, `osv_offline_store`, `pypi_conda_map` default to `.claude/data/conda-forge-expert/…` | `${paths.data_root}/stores/…` under `PYFORGE_ATLAS_DATA_ROOT` |
| Legacy bootstrap prerequisite | Operators run `bootstrap-data` before Kedro chain | Kedro bootstrap runs B5 external-refresh + pipelines on its own data root |

Legacy `bootstrap-data`, `cf_atlas.db`, and conda-forge-expert atlas CLIs **remain
valid** — they are out of scope for this dream.

### The unified Kedro data plane

One atlas root — env-var overridable, gitignored, never committed:

```
${PYFORGE_ATLAS_DATA_ROOT}/     # default: forge-data/atlas/ or member data/
├── raw/                        # Kedro catalog layers (HTTP → Parquet)
├── primary/
├── derived/
├── stores/
│   ├── vdb/                    # VDBStoreDataset (B5 external-refresh)
│   ├── osv/                    # OSVOfflineStoreDataset
│   └── pypi_conda_map.json     # mapping cache
└── seeds/                      # air-gap fallbacks only (small, tracked where needed)
```

Sibling `data.locks/` (run-admission) stays **outside** the data tree (AD-23 /
DW-AD23-3).

Legacy `.claude/data/conda-forge-expert/` may still exist on the same machine for
recipe work — Kedro simply does not *require* it.

### Phased journey (for `bmad-spec` decomposition)

#### Phase A — Relocate defaults (mechanical)

- Point `conf/base/globals.yml` `paths.vdb_store`, `osv_offline_store`,
  `pypi_conda_map` at `${paths.data_root}/stores/…`, not `.claude/data/…`.
- Document one operator env block; add a Kedro bootstrap entrypoint (pixi task or
  `pyforge-atlas bootstrap`) that runs B5 external-refresh + pipeline chain in
  dependency order.

#### Phase B — Replace SQLite seeds (core)

For each `seed_*_from_cf_atlas()` / `_cf_atlas_db_path()` call site, pick one:

- **Upstream Parquet** — read a catalog dataset another pipeline already wrote.
- **Live fetch** — dataset-owned HTTP (KEV/EPSS/CWE pattern).
- **Credentialed opt-in** — GitHub GraphQL, BigQuery Phase P (`PYPI_JSON_LIVE_FANOUT`, etc.).
- **External-refresh** — vdb, OSV, mapping (already cataloged).

Degrade per AD-13 (last-good + staleness marker), never silent fallback to SQLite.
Add a catalog gate: production dataset code must not default to
`.claude/data/conda-forge-expert/cf_atlas.db`.

#### Phase C — Catalog expansion (Tier 1–3 below)

Fill fetch gaps so inventory verification and factory channels use **live catalog
outputs only** (no spreadsheet tabs as index sources).

#### Phase D — Identity join in `upstream_discovery` (PURL Associator + OpenTeams + gist)

- **Source datasets:** `purl_associator_mappings_raw` (prefix-dev
  `mappings-index.json` + optional full bundle / per-package shards; AD-13
  last-good); `openteams_project_1_board_raw` (credentialed GitHub GraphQL —
  full project 1, **not** the OSS-milestone slice; same query shape as today's
  `fetch_project_issues`).
- **Derived node(s):** join inventory universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`
  from catalog Parquet) with associator index (`lookup_assoc` PEP 503 keys +
  `-`/`.`/`_` alias fallbacks); fallback to inventory-derived PURLs when
  unmapped (`PyPI_PURL` + `git_purl(Source_Repository_URL)`); board-only extras
  for packaging issues not in inventory. Output columns match today's
  `GIST_SCHEMA` / identity tab contract (`identity_source`, `associator_key`,
  `associator_status`, `primary_purl`, `primary_type`, `alternative_purls`,
  `cpes`, `conda_purl`, `source_repository_url`, `OpenTeams_Issue_URL`, …).
- **Overlay inputs (read Parquet or small tracked seeds):** feedstock-outputs map,
  staged-recipes PR map, `recipes/` local build overlay — same semantics as
  `attach_packaging_urls` / `overlay_live_local`.
- **Export target:** `identity_gist_publish` — credentialed dataset or post-pipeline
  actuator editing the pinned secret gist in place (`OPENTEAMS_IDENTITY_GIST_ID`;
  never committed): `mgmt-wf-python-modernization-identity.md` +
  `mgmt-wf-python-modernization-dashboards.md`. Ranking columns (`P`, `Score`,
  `Work`) are merged at publish time from the inventory priority pass — the join
  logic lives in Atlas; the ranking rules stay in `priority.py` until a later dream
  moves them.

### What it looks like when real

- **Cross-channel presence is complete for the factory's channels**, not just
  bioconda / pytorch / nvidia / robostack: **SelfExplainML** joins Phase Q-style
  bulk repodata (`in_selfexplainml` beside the existing four BOOLs).
- **Basilisk is two catalog entries, one override**: vuln advisories
  (`vulnerability_basilisk_*`, already shipped) **and** the **package catalog**
  (`GET /v1/packages`) — the dream's Basilisk tab and the HTML SPA are never
  the only source of truth.
- **Anaconda defaults are first-class**: `repo.anaconda.com/pkgs/main/channeldata.json`
  and the **Anaconda Distribution 2026.x** release list are cataloged beside
  conda-forge `core_channeldata_raw`.
- **Google AOSS free and premium** Python supported-package lists are catalog
  raw sources; premium ⊃ free; the **AOSS-Free Mason queue** (PyPI-yes,
  conda-forge-no, not in CDO consumption) derives from catalog Parquet, not a
  one-off script parse.
- **Discovery signals share the catalog**: maintainer feedstocks from
  [rxm7706/about](https://github.com/rxm7706/about), live curated-org sweeps,
  and Basilisk/AOSS frames land in **`upstream_discovery`** (or a sibling
  **`discovery`** pipeline) — not ad-hoc fetches inside
  `conda-forge-packaging-inventory-operations_metrics.py`.
- **Inventory quartet thins to orchestration**: priority / Score / Work assignment
  (`priority.py`) and enterprise-only consumption overlays (CDO JFROG fields)
  stay in the quartet for now. **Identity** (PURL Associator join, OpenTeams board
  ingest, gist publish, three dashboard canvases) **moves to Atlas Phase D**.
  **Live verification** (PyPI, conda-forge, Basilisk, AOSS, Anaconda,
  cross-channel, VCS URLs) **reads Kedro Parquet** via `--live-catalog`.
- **`kedro-catalog-check` and parity discipline stay green**: new entries get
  typed datasets (never bare `api.APIDataset` returning `Response` objects);
  new-signal datasets follow AD-14 (explicit parity scope for additive signals).
- **A fresh clone** runs the documented Kedro bootstrap, materializes Tier-1 +
  core pipeline outputs under `PYFORGE_ATLAS_DATA_ROOT`, and passes
  `parity-diff` / `bsl-metric-check` **without** `CF_ATLAS_DB` set.

### Sources to catalog (priority order)

#### Tier 1 — explicit gaps from the 2026-08-29 bootstrap resume

| Source | Endpoint / pattern | Target pipeline | Notes |
|--------|-------------------|-----------------|-------|
| SelfExplainML channel | `conda.anaconda.org/SelfExplainML/.../repodata.json` | `pypi_intelligence` | Factory channel; extend `CrossChannelRepodataDataset` |
| Anaconda main | `repo.anaconda.com/pkgs/main/channeldata.json` | `core` or `pypi_intelligence` | Same parser family as `core_channeldata_raw` |
| Basilisk package catalog | `GET {BASILISK_BASE_URL}/v1/packages` | `upstream_discovery` or new `discovery` | Distinct from `vulnerability_basilisk_*` |
| Google AOSS free | supported-packages doc (Python) | `discovery` | Git-tracked fallback seed for air-gap |
| Google AOSS premium | premium doc or Wayback snapshot | `discovery` | Set-diff vs free in node |
| Anaconda Distribution 2026.x | release-doc package list | `core` or `discovery` | Version the fetcher; brittle HTML |

Cross-channel **bioconda / pytorch / nvidia / robostack** already flows through
`pypi_cross_channel_repodata_raw` — Tier 1 here is **hardening** (subdir +
`repodata.json` fallback, tests, offline last-good), not a new source.

#### Tier 0 — already cataloged; inventory-critical (harden + document)

These exist in `catalog.yml` today but must be **live-first** after Phase B and
named in the `--live-catalog` contract:

| Source | Catalog entry | Inventory use |
|--------|---------------|---------------|
| conda-forge channeldata | `core_channeldata_raw` | `CondaForge_Verified` (~tens of thousands of packages; tens = fetch bug) |
| PyPI simple index | `pypi_simple_index_raw` | `PyPI_Verified` |
| PyPI project JSON | `pypi_json_raw` | `PyPI_Verified`, `Source_Repository_URL` via `project_urls` |
| Parselmouth mapping | `pypi_conda_map_store` | CondaForge Yes when PyPI name ≠ conda name |
| conda-forge channeldata URLs | `core_*` derived | `dev_url` / git-like `home` for VCS derivation |
| PURL Associator index | `purl_associator_mappings_raw` | `primary_purl`, `alternative_purls`, `cpes`, `associator_*` |
| OpenTeams project 1 board | `openteams_project_1_board_raw` | `OpenTeams_Issue_URL`, board-only identity rows, P1–P3 preservation inputs |

#### Tier 2 — inventory live-index alignment

| Source | Role |
|--------|------|
| `rxm7706/about` maintained feedstocks | Maintainer/co-maintainer universe (`CDO-ENT-CONDA` semantics live) |
| Curated org repo sweeps | Live org pages: Apache, Django, LF AI & Data, NumFOCUS, Jazzband, FINOS, PSF, PyPA, Trendshift, Google, Microsoft, Kedro, BMAD (+ configurable list in `curated_groups.json` as air-gap seed only) |
| Artifactory / CDO consumption | [[artifactory-download-intelligence]] live endpoint for JFROG universe names (enterprise fields stay in inventory scripts) |
| `conda-forge.org/packages` (optional) | Feedstock/metadata URL enrichment for identity handoff — catalog or documented inventory overlay |

#### Tier 3 — bulk-index stretch (Epic 23.1; deferred from Epic 21 v1)

homebrew · nixpkgs · spack · debian · fedora bulk indexes — same dataset-owned
fan-out pattern as Phase Q. See `complete-export-contract.md` §3.3.

### Inventory verification matrix (`--live-catalog`)

Maps [[conda-forge-packaging-inventory-operations]] live checks to catalog outputs.
The metrics runner reads Parquet under `PYFORGE_ATLAS_DATA_ROOT`; no duplicate HTTP
clients for these signals.

| Inventory field / rule | Kedro source (dataset or derived Parquet) |
|------------------------|-------------------------------------------|
| `PyPI_Verified` | `pypi_simple_index_raw` + `pypi_json_raw` |
| `CondaForge_Verified` | `core_channeldata_raw` + `pypi_conda_mapping` (Parselmouth) |
| `Source_Repository_URL` | channeldata git-like URLs + PyPI JSON `project_urls` / VCS pipeline |
| Basilisk membership | Tier 1 `basilisk_packages_raw` |
| AOSS free / premium membership | Tier 1 AOSS datasets (premium ⊃ free) |
| Anaconda main / Dist membership | Tier 1 Anaconda datasets |
| Cross-channel BOOLs (factory) | `pypi_cross_channel_flags` (+ SelfExplainML Tier 1) |
| `identity_source` / `primary_purl` / `conda_purl` | Phase D `identity_packages_primary` (+ associator join) |
| `OpenTeams_Issue_URL` | `openteams_project_1_board_raw` joined in Phase D |
| `Conda-Forge_FeedStock_URL` / metadata / staged PR / local build | Phase D overlays (feedstock map, staged PRs, `recipes/`) |
| `Packaging_Candidate_Status` taxonomy | **Epic 23.4** derived node — not a catalog fetch in Epic 21 |
| `P1`–`P10`, Score, Work | **Epic 23.3** Kedro priority node → **23.5** complete export |

**Scale sanity gates** (fetch bugs, not soft passes): conda-forge channeldata row
count on the order of **~30k+**; Basilisk package catalog **non-zero** when API
healthy; PyPI simple index non-empty. Catalog tests or bootstrap smoke assert
order-of-magnitude floors per index.

### Stays in the inventory quartet until Epic 23 (then thin actuators only)

- Priority / Score / Work assignment (`priority.py`) — **Epic 23.3** ports to Kedro
- Three dashboard canvases — **Epic 22** Vizro parity; data from **23.5** complete export
- Deliverable A 14-column shape — **Epic 23.4** `inventory_verified_packages.parquet`
- Enterprise JFROG consumption evidence — **Epic 23.2** `enterprise_jfrog_consumption.parquet`
- **Excel workbook parse** — explicitly out of scope forever; not a catalog input

### Catalog export targets (not fetch sources)

| Target | Contract |
|--------|----------|
| Identity gist | Edit pinned secret gist in place; markdown from BSL (Epic 23.6) over **23.5** complete export |
| Identity tab CSV/Parquet | **`identity_complete_export.parquet`** — full GIST_SCHEMA + handoff |
| Enterprise handoff | **`enterprise_jfrog_consumption.parquet`** — see `complete-export-contract.md` §1 |
| Deliverable A | **`inventory_verified_packages.parquet`** — 14 columns (Epic 23.4) |

### SQLite seeds to replace (explicit checklist for spec)

Dataset modules that must lose `_cf_atlas_db_path()` / `seed_*_from_cf_atlas`
defaults for Kedro self-containment:

- `pypi_json_raw` / `PyPIJsonFanOutDataset`
- `pypi_simple_index_raw` / `PyPISimpleIndexDataset` (if seeded)
- `GitHubRequestDataset` / `vcs_github_api_raw`
- GitLab, Codeberg, registry upstream seeds (`vcs_sources.py`)
- Parselmouth mapping (`ParselmouthMappingDataset` / `pypi_conda_map_store`)

Each entry in `catalog.yml` documents: **live fetch** | **upstream Parquet** |
**external-refresh** | **tracked seed** | **credentialed opt-in**.

### Architecture constraints (non-negotiable)

- **Dataset-owned IO** — fetch, parse, rate-limit, and fallback live in
  `pyforge.atlas.datasets.*`; nodes are `DataFrame → DataFrame` (A2 law).
- **One override point per host** — new channels use `{CHANNEL}_BASE_URL` env
  normalization; Basilisk reuses `BASILISK_BASE_URL` for both packages and vulns.
- **Bootstrap seed is transitional** — post-2026-08-29 SQLite seeding is a
  documented migration bridge only; steady-state catalog entries fetch or read
  upstream Parquet. When live fetch is opt-in (GitHub GraphQL, BigQuery Phase P),
  catalog metadata says so.
- **One Kedro data root** — `PYFORGE_ATLAS_DATA_ROOT` owns Parquet **and** external
  stores (vdb, OSV, mapping); no hardcoded `.claude/data/` defaults in shipped
  catalog paths after Phase A.
- **Legacy coexistence** — `bootstrap-data` and `cf_atlas.db` are **not** in scope
  for removal; this dream only removes Kedro's *requirement* on them.
- **Do not fold inventory ranking during Epic 21** — Epic **23.3** ports `priority.py` rules.
- **Do not duplicate enterprise consumption fields during Epic 21** — Epic **23.2** owns
  `enterprise_jfrog_consumption.parquet`; Tier 2 (21.5) supplies universe **names** only as bridge.
- **Index scale gates** — each public index catalog entry documents an expected
  order-of-magnitude row count; sub-threshold loads fail smoke tests loudly.

### Non-goals

- Replacing the inventory-operations quartet with Kedro nodes in one PR.
- Re-implementing OpenTeams **issue creation** (`--create-issues`) inside Atlas —
  board ingest yes; gh issue create + project add stays inventory until asked.
- Retiring legacy `cf_atlas`, `bootstrap-data`, or conda-forge-expert atlas CLIs.
- Running `universal_sbom` in the default bootstrap chain (entry-scoped; requires
  `sbom_intake_path`).
- Ingesting or mirroring the inventory **Excel workbook** as a catalog source.

### Spec-ready resolutions (2026-08-29)

Decisions locked before `bmad-spec` (`spec-atlas-kedro-catalog-expansion`):

| # | Question | Resolution |
|---|----------|------------|
| 1 | Spec shape | **One spec** + companions (tier matrix, identity contract, verification matrix, diagrams) |
| 2 | Phase D placement | **Extend `upstream_discovery`** — identity join + gist export nodes land there (not a 9th pipeline) |
| 3 | Tier 3 bulk indexes | **Epic 21 v1 non-goal** → **Epic 23.1** (CAP-8 closure) |
| 4 | Discovery vs pypi_intelligence for Tier 1 | **Split:** factory/cross-channel + assurance lists → extend `pypi_intelligence` / `core`; Basilisk/AOSS/about/curated → `upstream_discovery` |
| 5 | SelfExplainML subdirs | **Both** `noarch` and `linux-64` |
| 6 | AOSS premium | **Live doc** primary; Wayback snapshot as AD-13 last-good / air-gap seed |
| 7 | Anaconda Dist 2026.x | **Mechanical HTML extractor** + tracked seed fallback + scale gate |
| 8 | Quartet `--live-catalog` | **Direct Parquet reads** — no compatibility JSON shim |
| 9 | `PYFORGE_ATLAS_DATA_ROOT` default | Member **`src/shared/packages/pyforge-atlas/data/`**; env override documented |
| 10 | Kedro bootstrap surface | **Pixi task** `pyforge-atlas-bootstrap` (+ documented env block; CLI subcommand optional later) |
| 11 | Associator bundle depth | **`mappings-index.json` required**; per-package shards fetched on demand for `alternative_purls` / `cpes`; full `mappings.json` as opt-in air-gap seed |
| 12 | Gist publish | **Atlas export Parquet** + thin inventory wrapper (`--gist-only` reads export, merges ranking from `priority.py`, calls `gh gist edit`) |
| 13 | Epic 17 supersession | **`spec-conda-forge-packaging-inventory-operations` § Constraints** (purl-associator stays in quartet) **superseded** — associator join + board ingest + gist actuator fold into Atlas per this spec |
| 14 | Operator Vizro (optional 21.9) | Three BSL pages: `bootstrap-index-health`, `identity-export-snapshot`, `live-catalog-coverage` |
| 15 | Kedro-Viz CI (optional 21.10) | Extend `kedro-viz-publish.yml` paths: `catalog.yml`, `globals.yml`, `datasets/**` |
| 16 | Vizro canvas parity (Epic 22 / CAP-7) | Parallel replacement for three `.canvas.tsx` views — ranking/enterprise/gist/UX bridge until Epic 23 |
| 17 | Complete export (Epic 23 / CAP-8) | `identity_complete_export.parquet` + `enterprise_jfrog_consumption.parquet`; zero deferred data slices |

### Epic 22 — Vizro parity with identity canvases (CAP-7)

Vizro **can** become the parallel browser replacement for the three Cursor Canvas
identity views. Epic 21 scoped the **data plane** first; Epic 22 scopes **operator
UI parity**.

**North star:** `identity-catalog`, `identity-ops`, `identity-workbook` Vizro
pages match catalog / ops / workbook canvases; canvases stay on `both` until
Story 22.5 parity gate, then optional deprecation (22.6).

**Deferred (explicit, not blockers):**

| Slice | Deferred content |
|-------|------------------|
| Ranking feed | Quartet writes `identity_ranked_export.parquet` after `priority.py` (22.1) — not Kedro |
| Enterprise workbook | JFROG telemetry Parquet for `identity-workbook` (22.4 shell without it) |
| Gist handoff | CAP-7d — gist markdown from BSL instead of dual logic in dashboards script |
| UX port | Search/filter/four-pane fidelity after numeric parity (22.2–22.3) |
| Canvas removal | 22.6 only after 22.5 green |

Spec companion: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md`.

### Epic 23 — Complete export, zero deferred (CAP-8)

Closes the dream with **no data slices left in `scripts/`**.

**North star:** one canonical Parquet:

```
${PYFORGE_ATLAS_DATA_ROOT}/derived/identity_complete_export.parquet
```

**Enterprise build target** (what Artifactory / CDO must supply — Story 23.2):

```
${PYFORGE_ATLAS_DATA_ROOT}/derived/enterprise_jfrog_consumption.parquet
```

Required columns: `core_python_package_name`, `platform_env_count`,
`internal_app_count`, `artifactory_downloads`, `artifactory_version_count`,
`risk_level`, `vuln_status`, `internal_component_count`, `internal_lob_count`
(+ audit-only `packaging_tier`, never used for P). Full contract:
`complete-export-contract.md` §1.

| Story | Closes |
|-------|--------|
| 23.1 | Tier 3 OS bulk indexes |
| 23.2 | **Enterprise JFROG telemetry Parquet** |
| 23.3 | Priority rules in Kedro (`inventory_priority_assignments`) |
| 23.4 | Deliverable A + `Packaging_Candidate_Status` |
| 23.5 | **`identity_complete_export.parquet`** (supersedes quartet ranked export) |
| 23.6 | BSL gist/dashboard aggregates (CAP-8d) |
| 23.7 | E2E zero-deferred gate — quartet data logic retired |

Epic 22 steady state: Vizro reads **23.5** complete export (22.1 quartet bridge until then).

Spec companion: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md`.

### Open questions (remaining for `bmad-spec` only if implementation surprises)

1. **CDO-ENT-JFROG live fetch** — does Tier 2 `artifactory_downloads` supply universe **names** only, with telemetry columns still inventory-only? (Recommended: yes.)
2. **`conda-forge.org/packages` scrape** — v1 catalog dataset vs Phase D overlay reading `core_feedstock_attribution` only? (Recommended: derive from existing feedstock Parquet first; scrape optional stretch.)

### Kinships

[[pyforge-atlas]] · [[conda-forge-packaging-inventory-operations]] ·
[[upstream-discovery]] · [[artifactory-download-intelligence]] ·
[[packaging-factory]] · [[enterprise-airgap]] · [[developer-machine-bootstrap]]

**Planning bindings:** Story B5 (external-refresh stores), `catalog-contract.md`
(86 datasets / TTLs), 2026-08-29 bootstrap session (reference combined run).

### Success signal

**Epic 21 (data plane):** `pixi run -e pyforge-atlas pyforge-atlas --pipeline __default__`
(or documented Kedro bootstrap) materializes Tier-0/1 live indexes; inventory
`conda-forge-packaging-inventory-operations_metrics.py --live-catalog` produces
matching verification columns from Parquet alone. Phase D identity export passes
associator/board join parity. No `CF_ATLAS_DB` on the Kedro path;
`parity-diff` / `bsl-metric-check` pass.

**Epic 23 (dream fully closed):** additionally `enterprise_jfrog_consumption.parquet`
and `identity_complete_export.parquet` exist; priority + candidate status + gist
markdown parity on frozen fixture; Epic 22 Vizro reads complete export only;
quartet scripts are thin actuators (gist edit, optional `--create-issues`) with
no verification/ranking merge logic. Excel workbook never required.

### Realization log

- **2026-08-29** — Seeded (`78ccbe4468`, the atlas bootstrap-chain fix) and specified the same day:
  `spec-atlas-kedro-catalog-expansion` under pyforge-atlas (status `ready`) with the Epics 21–23
  planning chain (`9a0cb475f9`).

- **2026-09-09** — Fleet readiness pass (operator batch § 2.2, row atlas-B5). The Spec moves
  `ready` → **`shipped`**: Epics 21, 22 and 23 are 100% `done`, CAP-1..CAP-8 are decomposed,
  landed and gated, and both declared open questions were answered by delivery (Story 21.5's
  `project_artifactory_names` names-only projection; `core_feedstock_attribution` proving
  sufficient so the conda-forge.org/packages scrape stays deferred). **This Dream deliberately
  HOLDS at `specified`.** CAP-8's closure claim is that `identity_complete_export.parquet` and
  `enterprise_jfrog_consumption.parquet` are the canonical surface — and the catalog *declares*
  both (`conf/base/catalog.yml:987-989`, `:1301-1303`), which is a contract, not data. Atlas
  Story 25.2 ("Materialize CAP-8's canonical Parquets — one recorded run", ledger `blocked`)
  is the unblock; it needs the attended, credentialed Artifactory path that
  [[conda-forge-packaging-inventory-operations]] also waits on. This Dream moves to `realized`
  in the same commit that records that run. Splitting Spec-status from Dream-status is the shape
  [[wagtail-corporate-brain]] already uses; moving both together would set the precedent that a
  data Dream is `realized` before any data exists.

## 2026-10-26 — A query against the atlas DB becomes an interactive dashboard, no SPA framework (folded from atlas-query-dashboards)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/atlas-query-dashboards.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/atlas-query-dashboards.md`.*

## A query against the atlas DB becomes an interactive dashboard, no SPA framework

### The Dream

`cf_atlas.db` (DuckDB) already holds 16 schema versions' worth of real analytical data —
staleness, feedstock health, PyPI intelligence, universe SBOM inventory — queryable today only
through CLI tools (`staleness-report`, `feedstock-health`, `whodepends`, etc.) or hand-written SQL
against the database file directly. This Dream is the gap between "I can query it" and "I can
hand someone an interactive, filterable, drillable view of the answer" — a Panel/Bokeh widget
embedded in a lightweight server, server-rendered and WebSocket-driven, never a React/Vue SPA —
matching this repo's own established no-SPA convention (Steward's dashboard app is server-rendered
Django; Herald's Guildhall board is vanilla JS).

### What it looks like when real

- A DuckDB query against `cf_atlas.db` renders as a Tabulator grid, a chart, or a pivot table —
  static queries as HTML fragments needing no WebSocket; genuinely interactive ones (filter,
  drill, re-sort live) running Bokeh's WebSocket protocol through whatever ASGI host is already in
  play, the same server-driven shape `data-visualization-dashboards`'s WF source describes for
  Django Channels, adapted to this repo's own hosting choices rather than assuming Django
  specifically.
- Widget TYPES are pluggable, not hard-coded to the source dream's own SQL-Explorer-specific set —
  this repo has no SQL Explorer dependency to abstract away in the first place, since the query
  surface here is atlas's own DuckDB file, not a third-party query tool's saved-query registry.
- No new client-side JavaScript framework — Bokeh/Panel's own server-side rendering is the whole
  point of the "Django, no React" shape both this Dream and its WF source were reaching for.

### What is real

`cf_atlas.db` (DuckDB `>=1.5.5`, per `pyforge-atlas`'s own `pixi.toml`) is real, live, and already
the target of the 11 CLI query tools listed in this repo's own skill reference
(`detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`,
`cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`,
`scan-project`) — every one of them is, structurally, "a DuckDB query rendered as text"; this
Dream is the same queries rendered as an interactive widget instead. ~~Nothing
Panel/Bokeh/Channels-shaped exists in this repo yet — this is a genuinely new presentation layer,
not a port of anything already built.~~ *(Written 2026-08-14; **superseded 2026-09-09**, fleet
readiness pass. Bokeh-shaped code DID come to exist: Epic 14 built `pyforge/atlas/views/`, a
complete static-fragment + Bokeh-WebSocket runtime over six of these CLIs, and all four of its
stories read `done`. **Nothing ever called it** — no CLI verb, no pixi task, no ASGI mount, no
importer outside its own unit tests — and it reached `cf_atlas.db` through a bridge whose own
docstring records that its dynamic-import shape keeps the DuckDB-singularity gate green while the
loaded script imports `sqlite3` (`views/cli_bridge.py:11-17`). The operator retired it on
2026-09-09 (decision batch § 2.3 C1; atlas Story 25.1 deletes the package). The struck sentence is
kept as the record of where this Dream started — see § Realization log.)*

A related, larger finding surfaced while investigating this Dream: atlas already has a REAL,
tested (against an in-memory mock, network-injectable) client for an EXTERNAL Wagtail/Django CMS
— `factory/lasuite.py`'s `LaSuiteClient`/`WikiSyncer`, built for Story H3, pushing the
Karpathy-wiki's report pages to a "Corporate Brain" CMS. Standing up the live server side is
`DW-H3` (atlas's own deferred-work ledger) — explicitly deferred as an ATTENDED bring-up (an
operator decision, not a code gap), not speculative. If that server is ever stood up, THIS
Dream's Panel/Bokeh widgets are exactly the kind of thing the source `data-visualization-dashboards`
dream describes embedding inside a Wagtail `BokehPanelPage` — a real Kinship, but this Dream does
not depend on DW-H3 being resolved; a Panel/Bokeh dashboard needs an ASGI host, not specifically a
CMS.

### Constraints

- **Query `cf_atlas.db` directly — no second data layer.** This Dream visualizes what atlas
  already computes; it does not compute anything new or maintain a parallel query surface.
- **No SPA framework.** Server-rendered/WebSocket-driven only, matching this repo's established
  convention across every existing dashboard surface.

### Non-goals

- **Not a notebook-style coding environment** — read-only visualization of existing queries, per
  the source dream's own v1 scope, carried over unchanged.
- **Not real-time streaming** — queries run on demand.
- **Not a drag-and-drop dashboard builder** — a curated set of views, not a general BI tool.
- **Not deciding whether the Wagtail CMS (DW-H3) gets built** — that is atlas's own already-deferred,
  attended decision; this Dream neither depends on nor blocks it.

### Full feature audit against `data-visualization-dashboards`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| SQL Explorer query → Panel/Bokeh widget | **Reframed** | No SQL Explorer dependency exists here to abstract; the equivalent query surface is `cf_atlas.db` directly, already queried by 11 existing CLI tools. |
| Static query → HTML fragment (no WebSocket) | **Included** | Directly transferable — the simplest, lowest-risk rendering mode. |
| Interactive Panel app → Bokeh WebSocket via Channels, same OIDC session | **Included, host-agnostic** | The WebSocket-driven interactivity is kept; "via Django Channels specifically" is loosened to "via whatever ASGI host is in play," since this repo has no existing Django+Channels deployment this Dream should presuppose (unlike the WF source, which already has one). |
| JWT-based WebSocket session auth bridged to Django cookies | **Omitted, no target session system** | This repo has no existing web-session auth system a dashboard would bridge into yet — Steward's own dashboard (Story 9.1+) has its own, narrower identity-at-the-boundary model; if this Dream is ever realized against that surface, session bridging is a Spec-time decision, not assumed here. |
| Custom staticfiles finder for Bokeh/Panel extension assets | **Included, deferred detail** | Real implementation detail, not a scoping decision — carried forward as a "when built" concern, not resolved here. |
| CDN-URL rewriting for airgapped environments | **Included, high relevance** | This repo already has real air-gap/enterprise-routing concerns (`[[enterprise-airgap]]`, `_http.py`'s truststore chain) — this is one of the more DIRECTLY applicable pieces of the source dream, not a WF-specific artifact. |
| Pluggable widget types | **Included, reframed** | Kept as a design principle, but not scoped to the source's specific widget catalog (Tabulator/Perspective/PGWalker) — which widgets matter here is a Spec-time question against atlas's own query shapes. |

### Kinships

[[pyforge-atlas]] (the estate; `cf_atlas.db` is the data source) · [[enterprise-airgap]] (the
CDN-rewriting concern is directly relevant to this repo's own already-real air-gap posture) ·
[[artifactory-download-intelligence]] (a sibling atlas Dream captured in the same investigation;
its output could plausibly become one of this Dream's dashboards, not a dependency) ·
[[wagtail-corporate-brain]] (the dream this one's investigation surfaced — a real, evidence-backed
CMS destination this Dream's widgets could embed inside if that Dream's own narrow scope is ever
realized, not a dependency)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Reframed from "Django+Channels+SQL-Explorer" (the source's own stack) to "no SPA, host-agnostic"
  since this repo has neither Django+Channels nor SQL Explorer deployed anywhere yet — the actual
  transferable idea is "server-rendered interactive widgets over an existing query surface," and
  `cf_atlas.db` is that surface. Investigation surfaced a larger, unrelated finding along the way:
  atlas already has a tested client (`factory/lasuite.py`) for an external Wagtail CMS, with the
  server-side bring-up explicitly deferred as `DW-H3` — real, not speculative, and directly
  relevant to re-scoping [[wagtail-corporate-brain]] far more favorably than this batch's
  first-pass tiering had it.
- **2026-08-14** — Spec authored (spec-atlas-query-dashboards, pyforge-atlas) by the 2026-08-14 dream-backlog audit: curated CLI-mirroring view catalog, static-fragment mode first, Bokeh-WebSocket interactivity behind a pluggable widget registry, ASGI-host-agnostic, air-gap CDN rewriting from day one.

- **2026-09-09** — **Fleet readiness pass, then RETIRED (operator batch § 2.3 C1).** Verified
  against live code at `fe4025ea90`. Epic 14 (CAP-1..4) and Epic 20 (CAP-5..7) all read `done`;
  `DESIGN.md`/`EXPERIENCE.md` exist; DW-D2-1 and DW-D2-2 are closed. But CAP-1..4's own runtime,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/`, has **no importer outside its own
  unit tests** — no CLI verb, no pixi task, no ASGI mount, even though `views/__init__.py:10-13`
  describes `asgi.py::app` as a mount target. It also reads the legacy SQLite `cf_atlas.db`
  through `views/cli_bridge.py`, whose docstring (`:11-17`) records that its dynamic-import shape
  keeps the F1 DuckDB-singularity gate green while the loaded script imports `sqlite3` — a
  private, non-BSL read against the Unifying ruling "no private DuckDB … BSL is the
  dashboard/agent SQL contract" (`pyforge-unifying-strategy.md:400`), and against
  `spec-pyforge-atlas`'s own Non-goal "Continued SQLite". Built, merged, off — the
  marshal-token-economy shape. **Operator decision 2026-09-09: RETIRE.** The estate's real Lane-3
  surface is the Vizro board over the D1 BSL seam (`dashboard/app.py`, gated by
  `dashboard-dryrun`, served by `pixi run -e local-recipes dashboard-serve`). Atlas Story 25.1
  deletes the package and its tests; the widget-registry idea survives only if a Vizro page asks
  for it. The declared open question about session bridging dies with the module (the estate
  already forbids mounting an analytics runtime on the identity-bearing host —
  `src/platform/tests/test_host_board_row_isolation.py:26`). The Spec stays `in-progress` until
  25.1 lands and then reads `shipped` on the strength of CAP-5..CAP-7, which are real, live and
  exercised. Status here moves `specified` → `archived` (`archived-reason: retired`).

## 2026-10-26 — Build a conda-forge packaging inventory from scratch as a continuous intake engine (folded from conda-forge-packaging-inventory-operations)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/conda-forge-packaging-inventory-operations.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/conda-forge-packaging-inventory-operations.md`.*

## Build a conda-forge packaging inventory from scratch as a continuous intake engine

### The Dream

A repeatable intake engine that starts from raw sources and rebuilds the packaging
inventory end to end: normalize identity, verify PyPI and conda-forge, assign
priority and provenance, and hand execution-ready queues to conda-forge workflows
and OpenTeams. Never consume a previous consolidated inventory as input.

It binds Master Prompt v3.0 (*Consolidated Verified Package Inventory
Specification*) and runs through the existing quartet — runner, prompt, config,
replay — not a second toolchain.

### What it looks like when real

- A from-scratch run in a clean workspace regenerates the full inventory from the
  workbook, live indexes, and curated feeds.
- Every package has one PEP 503 identity, source provenance, and a timestamped
  verify decision. Ranking stays inspectable: proposed `P1`–`P10`, a
  1–100 use `Score`, and a work label (not A/B/C).
- `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` is the OpenTeams universe: one issue titled
  `[Conda-Forge Packaging] {name}` per library, plus a dated handoff tab Mason
  can consume (`Fix vulnerability` / `Create recipe` /
  `File OpenTeams tracking issue [Conda-Forge Packaging]` /
  `Already tracked`).
- Google AOSS Free names that are on PyPI, not on conda-forge, and not in CDO
  consumption are an extra Mason queue. They do not expand the OpenTeams universe.
- Identity rows (PURLs, issue URL, feedstock, metadata, staged-recipes PR, local
  recipe, live CFE `Local_Build_Status`) are a **dated** workbook tab
  (`identity-YYYY-MM-DD`) and a pinned secret gist. New snapshots get a new
  dated tab; do not overwrite an older identity tab. The gist id is never in
  git (`OPENTEAMS_IDENTITY_GIST_ID` or gitignored local env).
- Three dashboard views exist for the live identity tab (catalog, ops, Artifactory
  / workbook). Humans read them beside the chat; machines read the same numbers
  from gist YAML + GFM. A run that ranks identity is not done until those three
  views and the gist companion are rebuilt.
- Drift is visible: net-new names, status flips, stale sources.

### Sources

Primary workbook: `docs/Analysis_Dataset-2026-08-12.xlsx` (local, gitignored;
do not commit). Parse every source tab.
Live collection endpoints are primary; workbook tabs are the offline fallback.

**Must-include (100% of parseable names in the final inventory):**

- `CDO-ENT-JFROG` — CDO JFrog / Artifactory consumption inventory (`name`).
- `CDO-ENT-CONDA` — CDO enterprise conda-forge feedstocks (`Package_Name`,
  `Role` = Maintainer / Co-Maintainer, `Feedstock`). Live list:
  [rxm7706/about](https://github.com/rxm7706/about).

**Other source tabs:** `GAOSS-Free`, `GAOSS-Premium`, `Anaconda-Main`,
`Conda-Forge`, `Basilisk`, `Anaaconda-Dist` (Anaconda Distribution 2026.x),
`OpenTeams`, `10kOpen`, `10kClosed`.

- `10kOpen` is a clone of `CDO-ENT-JFROG`. Do not double-count it.
- `10kOpen` / `10kClosed` are name lists only (`Package_Name`,
  `Source_Organization`, `Primary_Domain`). Derive PyPI, conda-forge, and source
  repo from live indexes, never from leftover hint columns.
- `GAOSS-Free` ⊂ `GAOSS-Premium`. Free-tier Python is Google-assured and an extra
  packaging queue when missing from conda-forge and from CDO consumption.

**Do not ingest** these output snapshot tabs (`OUTPUT_TABS`):

| Tab | What it is |
|---|---|
| `verified-all-packages` | Full inventory (deliverable A; 14 columns) |
| `inventory-2026-08-12` | OpenTeams universe handoff (14 + 8 columns) |
| `identity-2026-08-12` | Frozen identity snapshot. Do not overwrite. |
| `identity-YYYY-MM-DD` | Dated identity output (live: `identity-2026-08-20`). Never ingest. |

Refresh those tabs from a run. Do not keep repo-root CSVs as the stored copy.

**OpenTeams tracker.** Live board is org project 1, **full** `[Conda-Forge
Packaging]` titles (no OSS-milestone slice). View for humans:
https://github.com/orgs/OpenTeams-WFT-CDO/projects/1/views/6?sliceBy%5Bvalue%5D=OSS+Enhancements+%28Conda+Forge%2C+Pixi%2C+ect%29
Workbook `OpenTeams` is the offline snapshot of the full board. Optional `.tsv`
only if the tab is absent. CVE titles (`CVE-… | pkg`) are a different tracker
and do not count.

**External endpoints:**

1. Anaconda Distribution 2026.x —
   [release docs](https://www.anaconda.com/docs/getting-started/anaconda/release/2026.x)
2. Anaconda main — [anaconda.org/channels/main](https://anaconda.org/channels/main)
   (`https://repo.anaconda.com/pkgs/main/channeldata.json`)
3. conda-forge —
   [anaconda.org/channels/conda-forge](https://anaconda.org/channels/conda-forge)
   (`https://conda.anaconda.org/conda-forge/channeldata.json`)
4. Basilisk `view=all` — [basilisk.prefix.dev](https://basilisk.prefix.dev/?view=all)
   ([API](https://prefix-dev.github.io/basilisk/docs/api/); prefer
   `GET https://api.basilisk.prefix.dev/v1/packages`, not the HTML SPA)
5. Google AOSS free Python —
   [supported packages](https://docs.cloud.google.com/assured-open-source-software/docs/supported-packages#python)
6. Google AOSS premium Python —
   [Wayback snapshot](https://web.archive.org/web/20260419090548/https://docs.cloud.google.com/security-command-center/docs/aoss-supported-packages-premium#python)
7. Maintained + co-maintained feedstocks —
   [rxm7706/about](https://github.com/rxm7706/about)
8. Curated groups — live org URL, then workbook
   `10kClosed.Source_Organization`, then
   `conf/conda-forge-packaging-inventory-operations_curated_groups.json` (sample fallback, not membership
   of record). Starting URLs: Apache, Django, LF AI & Data, NumFOCUS, Jazzband,
   FINOS, PSF ([about](https://github.com/rxm7706/about) goal 3), plus PyPA,
   Trendshift, Google, Microsoft, Kedro, BMAD org pages. Org homepages and GitHub
   repo lists are membership starting points, not “ingest every repo as a package.”

A fetch that is an order of magnitude off (Basilisk 0 from HTML, conda-forge
tens instead of tens of thousands) is a fetch bug.

### Build surface

| Path | Role |
|---|---|
| `scripts/conda-forge-packaging-inventory-operations_metrics.py` | Inventory runner |
| `scripts/conda-forge-packaging-inventory-operations_priority.py` | Proposed `P`, `Score`, `Work` on a dated identity tab (`--tab`); optional inventory sync (`--skip-inventory-sync` to leave `Priority_Bucket` alone); writes the catalog canvas (`--canvas`) |
| `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` | Prompt the runner must obey |
| `conf/conda-forge-packaging-inventory-operations_curated_groups.json` | Curated-group sample fallback |
| `docs/reference/conda-forge-packaging-inventory-operations_replay.md` | Replay / sync contract |
| `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` | Identity tab (`--tab-out identity-YYYY-MM-DD`) + gist publish (`--gist-only` after a priority pass) |
| `scripts/openteams_identity_dashboards.py` | Gist companion markdown for the three dashboard views |
| `conf/conda-forge-packaging-inventory-operations.local.env.example` | Template for the gitignored gist id |

A rule, source, column, or metric change updates runner + prompt + replay in the
same commit. Identity-column changes update
`conda-forge-packaging-inventory-operations_openteams_identity.py`. Priority /
work-label / bucket-rule changes update
`conda-forge-packaging-inventory-operations_priority.py` **and** the three
dashboard views **and** `openteams_identity_dashboards.py` (gist YAML `rule` /
`meaning` must stay byte-identical to the priority script). Do not overwrite
`docs/reference/conda-forge-packaging-inventory-operations_prompt.md`
unless that is the task.

**From scratch:** empty outputs; ingest the workbook + live endpoints + curated
JSON; write new tabs / optional CSV / Markdown / stdout. Do not read a prior
consolidated inventory CSV or Markdown as seed or oracle.

### Ingestion and identity

- Extract package-name columns (`name`, `Package_Name`, `raw_names`, `Item`,
  `package`, equivalents).
- OpenTeams titles: **(a)** text after `|` split on comma (CVE tracker; does not
  count toward 1:1); **(b)** `[Conda-Forge Packaging] {name}` — one name per
  issue; **(c)** ignore other titles.
- Strip issue numbers, brackets, version constraints, extras, whitespace.
- Dedup is PEP 503 only (lowercase; `_` and `.` → `-`). It must not drop a
  JFROG or CONDA library.
- `CDO-ENT-JFROG` keeps consumption evidence on the record for priority/handoff
  (`risk_level`, `vuln_status`, `platform_env_count`, `internal_app_count`,
  `internal_component_count`, `internal_lob_count`, `artifactory_downloads`,
  `artifactory_version_count`). Those fields do not become columns of
  deliverable A. Ignore JFROG `packaging_tier` — recalculate `P` here.
- From about (or `CDO-ENT-CONDA`): convert `conda-forge/<pkg>-feedstock` to
  `<pkg>`; `Repository_Source` = `Conda Enterprise Core`; `Role` = Maintainer
  or Co-Maintainer.
- Track overlapping curated-group attributions explicitly.
- Drop a `10kClosed` / `10kOpen` name from deliverable A only when
  `PyPI_Verified=No` **and** no derived VCS URL **and** the name is not on
  JFROG or CONDA. `10kOpen` names already enter via JFROG.

### Verification and PURLs

Offline-safe: skip + last-good + documented fallback when unreachable.

- `PyPI_Verified` via PyPI simple and/or `https://pypi.org/pypi/{package}/json`.
  Fast-mode must not treat conda-forge presence as PyPI Yes.
- `CondaForge_Verified` via conda-forge `channeldata.json` plus Parselmouth
  (`compressed_mapping.json`) so a PyPI name that maps to a different conda
  name still counts as Yes.
- `Source_Repository_URL` — upstream VCS, never feedstock, never `pypi.org` /
  `anaconda.org`. Order: (1) channeldata `dev_url` / git-like `home` /
  `source_url`; (2) PyPI JSON `project_urls` then git-host `home_page`. Accept
  GitHub, GitLab, Bitbucket, Codeberg, and other published VCS hosts. `N/A`
  only when neither publisher lists a VCS URL. Do not skip PyPI JSON for
  PyPI-verified names that are not on conda-forge.

| Status | Rule |
|---|---|
| `Already Packaged` | PyPI Yes AND conda-forge Yes |
| `High Priority Candidate` | PyPI Yes AND conda-forge No AND P1–P8 |
| `Low Priority Candidate` | PyPI Yes AND conda-forge No AND P9 or P10 |
| `Conda-Forge Only` | PyPI No AND conda-forge Yes |
| `Not on PyPI` | PyPI No AND conda-forge No |

OpenTeams-universe `Priority_Bucket` is the proposed `P` from the priority pass
(below). Do not keep the old default (`P4` if on `CDO-ENT-CONDA`, else `P9`).
The floor is `P10` (not `P0`).

### Priority, work, and score

Assigned by `scripts/conda-forge-packaging-inventory-operations_priority.py` onto
the live dated identity tab (`--tab identity-2026-08-20`; default still
`identity-2026-08-12`). Do not overwrite a frozen older identity tab. Inventory
`Priority_Bucket` / `OpenTeams_Batch` sync is optional (`--skip-inventory-sync`
when the live identity is ahead of inventory). Board packaging issues with
existing **P2** or **P3** are not overwritten. Current-version vulnerabilities
become **P1** (`Fix vulnerability`) even if they also need an issue. JFROG
`packaging_tier` is ignored. There is no `P0`.

**Work** (`OpenTeams_Batch` / identity `Work`) is what Mason does, not A/B/C:

| Work | Was | Meaning |
|---|---|---|
| `Fix vulnerability` | (new) | Current-version HIGH / `affected_latest`. Wins over recipe/issue/tracked. |
| `Create recipe` | A | JFROG consumed, not on conda-forge (`JFROG_NEW`). |
| `File OpenTeams tracking issue [Conda-Forge Packaging]` | B / C | Already on conda-forge, no OpenTeams tracking issue yet (`JFROG_ON_CF` or `CONDA_ONLY`). |
| `Already tracked` | TRACKED | `[Conda-Forge Packaging] {name}` issue already exists. |

`OpenTeams_Cohort` stays `JFROG_NEW` / `JFROG_ON_CF` / `CONDA_ONLY`. Components
and LOBs never appear without apps, so they do not get their own `P` lane.

**Proposed `P`** (highest first):

| P | Rule |
|---|---|
| **P1** | Current-version vulnerability (`risk_level=HIGH` or `vuln_status=affected_latest`). Existing OpenTeams board P1 also stays here. |
| **P2** | Existing OpenTeams board P2. Not overwritten. |
| **P3** | Existing OpenTeams board P3. Not overwritten. |
| **P4** | `platform_env_count` > 0. |
| **P5** | `internal_app_count` > 0, no platform. |
| **P6** | 100+ Artifactory downloads **or** 100+ Artifactory versions, and not already P1–P5. |
| **P7** | 10+ downloads **or** 10+ versions, below the P6 floor. |
| **P8** | Leftover `Create recipe` (below the P7 floor). |
| **P9** | Leftover `File OpenTeams tracking issue [Conda-Forge Packaging]` for `JFROG_ON_CF`. |
| **P10** | Leftover `File OpenTeams tracking issue [Conda-Forge Packaging]` for `CONDA_ONLY`, plus leftover `Already tracked`. |

Each row carries `Priority_Bucket_Description` with that rule in prose.

**Score** (1–100, percentile of the use formula; work type does not inflate it):

```text
100×platforms + 10×apps + 3×components + 2×LOBs
+ log10(1+downloads) + log10(1+Artifactory versions)
```

Within a `P`, sort `Fix vulnerability` then `Create recipe` then already-tracked
then issue work, then by Score descending.

When the matching verify flag is No, emit `N/A`:

- `PyPI_PURL` — `pkg:pypi/{name}`
- `PyPI_Package_URL` — `https://pypi.org/project/{name}/`
- `Conda-forge_PURL` — `pkg:conda/{name}?channel=conda-forge`
- `Conda-Forge_Package_URL` — `https://anaconda.org/conda-forge/{name}/`
- `Conda-Forge_FeedStock_URL` — prefer CONDA tab slug or Parselmouth conda name,
  else `https://github.com/conda-forge/{name}-feedstock`

### Deliverables

Google Shared Drive for humans; workbook tabs for the local source of record.

**A. Full inventory** — tab `verified-all-packages` (optional CSV export). Exactly
these 14 columns, in order:

1. `Repository_Source`
2. `Role`
3. `Package_Input_Name`
4. `Core_Python_Package_Name`
5. `PyPI_Verified`
6. `CondaForge_Verified`
7. `Priority_Bucket`
8. `Packaging_Candidate_Status`
9. `PyPI_PURL`
10. `PyPI_Package_URL`
11. `Conda-forge_PURL`
12. `Conda-Forge_Package_URL`
13. `Conda-Forge_FeedStock_URL`
14. `Verification_Timestamp_UTC`

**OpenTeams handoff** — tab `inventory-2026-08-12`. Same 14 columns, then:

15. `OpenTeams_Title` — `[Conda-Forge Packaging] {name}`
16. `OpenTeams_Cohort` — `JFROG_NEW` / `JFROG_ON_CF` / `CONDA_ONLY`
17. `OpenTeams_Batch` — work label (`Fix vulnerability` / `Create recipe` /
    `File OpenTeams tracking issue [Conda-Forge Packaging]` /
    `Already tracked`; was A / B / C / TRACKED)
18. `OpenTeams_Labels`
19. `OpenTeams_Milestone` — `OSS Enhancements (Conda Forge, Pixi, ect)`
20. `OpenTeams_Coverage` — `Have_Issue` / `Missing_Issue`
21. `OpenTeams_Issue_URL`
22. `Source_Repository_URL`

`Priority_Bucket` (column 7) is the proposed `P` from the priority pass.
`Priority_Bucket_Description` is appended after the handoff columns so Mason
can read the rule without opening identity.

One row per unique name in parseable JFROG ∪ CONDA. Labels always include
`Conda Forge Packaging` and `No WF org info`; add `WF List 2` if in JFROG;
add `Packaging: New package` if not on conda-forge.

**Identity** — dated tab `identity-YYYY-MM-DD` (live: `identity-2026-08-20`;
frozen: `identity-2026-08-12`). Pass `--tab-out` so a new snapshot does not
overwrite an older one. Identity URLs come from
`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`
(one row per universe name plus **board-only** `[Conda-Forge Packaging]` extras
from the full OpenTeams project 1 join — no milestone slice). Prefer PURL
Associator (`--refresh-associator`) when the conda name exists; otherwise mint
from `PyPI_PURL` + `Source_Repository_URL`. Overlay live `Local_Recipes_URL` and
`Local_Build_Status` from `recipes/` at write and at gist publish. Then the
priority pass (`--tab` matching `--tab-out`) writes ranking columns **first**:

1. `P`
2. `Rank`
3. `Score`
4. `Package`
5. `Work`
6. `Platforms`
7. `Apps`
8. `Downloads`
9. `Versions`
10. `Vuln`
11. `Core_Python_Package_Name` (primary key)
12. `OpenTeams_Title`
13. `identity_source`
14. `associator_key`
15. `associator_status`
16. `primary_purl`
17. `primary_type`
18. `alternative_purls`
19. `cpes`
20. `conda_purl`
21. `source_repository_url`
22. `OpenTeams_Issue_URL`
23. `Conda-Forge_FeedStock_URL`
24. `Conda-Forge_Metadata_URL`
25. `Staged_Recipes_PR_URL`
26. `Local_Recipes_URL`
27. `Local_Build_Status` (`success` / `failed` / `build-clean-test-blocked` / `not-attempted`; blank if no CFE stamp)
28. `Verification_Timestamp_UTC`
29. `Priority_Bucket_Description`
30. `Priority_Source`
31. `Priority_Reason`
32. `JFROG_risk_level`
33. `JFROG_latest_vuln_count`
34. `internal_component_count`
35. `internal_lob_count`

A full identity regen wipes ranking columns. After identity regen, re-run the
priority pass on **that** dated tab, rebuild the three dashboard views, then
publish the gist with **`--gist-only --tab-out <that-tab>`** (reads the current
tab; does not regenerate). Do not run a full identity regen solely to refresh
the gist. Do not overwrite `identity-2026-08-12` to refresh `identity-2026-08-20`.

Feedstock + metadata from [conda-forge.org/packages](https://conda-forge.org/packages/);
staged-recipes PR from
[conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes/pulls?q=is%3Apr);
local recipe from
[rxm7706/local-recipes/recipes](https://github.com/rxm7706/local-recipes/tree/main/recipes).
Blank means missing.

After every inventory rerun: regenerate identity onto a **new** dated tab if the
previous snapshot must be kept, run the priority pass, rebuild the three
dashboard views, then **edit in place** the pinned secret gist files
`mgmt-wf-python-modernization-identity.md` (row catalog) and
`mgmt-wf-python-modernization-dashboards.md` (the three views as GFM + YAML)
with `--gist-only --tab-out <live-tab>`. The gist id comes from
`OPENTEAMS_IDENTITY_GIST_ID`,
`conf/conda-forge-packaging-inventory-operations.local.env` (gitignored; copy
the tracked `.example`), or `--gist-id`. Do not create a new gist. Do not
commit the id. `--skip-gist` is offline tests, or when no id is configured.
The catalog file carries the same 35 identity columns (ranking first), including live `Local_Recipes_URL` and `Local_Build_Status` overlaid from `recipes/` at publish time. Frontmatter also splits those stamps by priority (`local_build_by_p`), recipe type (`local_build_by_type`: `noarch-python` / `noarch-generic` / `compiled` / `arch` / `none`), and successful builds (`local_build_success_by_p_type`). The dashboards file must include machine YAML `priority_buckets` / `work_labels` (each with `n` + `rule` / `meaning`) and human tables with those same rules — a count-only P table is not enough.

**Three dashboard views** (required; a ranked identity tab without them is
incomplete). Cursor canvases beside the chat are the interactive rendering;
gist `mgmt-wf-python-modernization-dashboards.md` is the portable copy of the
ops + Artifactory/workbook views; gist `mgmt-wf-python-modernization-identity.md`
is the portable copy of the catalog. Rebuild all three after every priority
pass.

| View | Canvas (Cursor) | What it shows |
|---|---|---|
| **Catalog** | `identity-2026-08-20.canvas.tsx` | Searchable row browser: every live identity package with `P`, `Work`, `Score`, use signals. Written by `priority.py --canvas`. |
| **Ops** | `identity-ops.canvas.tsx` | Four panes: **Priority** (P1–P10 + work, with rules), **Issues** (packaging-issue gap), **Builds** (CFE stamp by P × noarch/other), **Census** (feedstock / staged-recipes / local build cube). |
| **Artifactory / workbook** | `jfrog-workbook.canvas.tsx` | Five panes: **Map** (CDO-ENT-JFROG → PyPI / conda-forge), **Staged gap** (need staged-recipes PR), **Board gap** (PyPI-only names still missing a packaging issue), **Workbook** (all tabs), **External** (live index counts vs workbook). |

Canvas files live in the Cursor workspace `canvases/` directory (IDE-owned, not
git). Do not spawn extra canvases for slices of these three. Do not keep a
duplicate of the catalog under another name. Bucket **Rule** / work **Meaning**
on the ops Priority pane and in gist YAML must match
`PRIORITY_DESC` / work labels in `priority.py`.

**B. Markdown** `cdao_consolidated_inventory_verified_all_packages.md` — totals,
status breakdown, per-tab and per-source inclusion matrices (100% where
required), overlaps, OpenTeams parse summary, OpenTeams 1:1 coverage (have /
missing / surplus), net-new vs live feeds.

**C.** `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` — self-contained re-run prompt.

**D. Stdout**

```text
=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS ===

Total final unique packages processed: <number>
Count not on conda-forge: <number>
Count from analysis-dataset portion not on conda-forge: <number>
Count parsed from OpenTeams-style portion:
  - rows used by rule (a): <number>
  - rows used by rule (b): <number>
  - rows ignored by rule (c): <number>
  - unique packages extracted from that portion: <number>
```

**E. Quality gates**

1. Deliverable A has exactly those 14 columns in order. The handoff tab keeps
   them first, then the 8 OpenTeams columns, then `Priority_Bucket_Description`.
2. `Core_Python_Package_Name` is unique.
3. Markdown includes every required section.
4. Inclusion matrices match totals. JFROG, CONDA, `GAOSS-Free`, and
   `GAOSS-Premium` are 100% of parseable names. `10kClosed` is not a 100%
   inclusion tab.
5. Stdout numbers match the outputs.
6. Markdown reports OpenTeams 1:1 coverage. 100% have-issue is the **goal**,
   not a pass/fail of the inventory rebuild.
7. Handoff `Source_Repository_URL` is filled from channeldata **and** PyPI JSON.
   Skipping PyPI JSON for names not on conda-forge fails the gate.
8. Identity ranking columns `P`, `Rank`, `Score`, `Work` are filled. `P` uses
   `P1`–`P10` (no `P0`). `OpenTeams_Batch` is a work label, not
   A/B/C/TRACKED. Leftover file-issue work is one label:
   `File OpenTeams tracking issue [Conda-Forge Packaging]`.
9. The three dashboard views exist for the live identity tab (catalog, ops,
   Artifactory/workbook). Gist dashboards YAML `priority_buckets` / `work_labels`
   carry `n` plus the rule/meaning. Count-only P tables fail the gate.
10. Gist publish edits **both** files in place (`…-identity.md` and
    `…-dashboards.md`). No new gist. Frozen `identity-2026-08-12` is untouched.

### Constraints

- One package, one PEP 503 name, unless an alias is explicit.
- Provenance end to end; no priority without evidence.
- Same raw inputs and versions produce the same results from an empty output dir.
- Offline-safe from repo-tracked inputs plus declared refresh sources.
- Handoff is consumable by existing conda-forge / Mason workflows.
- Do not rename or reorder deliverable A's 14 columns. The handoff tab may only
  append after them.
- Dropping 10k junk must not remove a JFROG or CONDA name.
- Do not overwrite OpenTeams board P2/P3 on packaging issues.
- Do not use JFROG `packaging_tier` as proposed `P`.
- Do not invent `P0`. Floor is `P10`.
- Do not overwrite a frozen dated identity tab (`identity-2026-08-12`) when
  building a newer snapshot.
- Do not join OpenTeams on the OSS-milestone slice; packaging-issue match is
  every `[Conda-Forge Packaging] {name}` title on project 1.
- Do not skip the three dashboard views after a priority pass.
- Do not commit `OPENTEAMS_IDENTITY_GIST_ID` or create a new identity gist.

### Non-goals

- Not replacing conda-forge-expert recipe authoring, build, or submit.
- Not a real-time web service; batch refresh is enough.
- Not an opaque rank: `Score` is the documented use formula; `P` is the
  documented hierarchy; `Work` is the documented Mason action.
- Not pushing proposed `P` onto the OpenTeams board until asked.
- Not bootstrapping from a prior consolidated inventory.
- Not a second runner beside the v3 quartet.
- Not extra canvases beyond the three views (no per-slice duplicates of catalog
  / ops / Artifactory-workbook).

### Kinships

[[packaging-factory]] · [[upstream-discovery]] · [[pyforge-atlas]] · [[pyforge-mason]]

### Realization log

- **2026-08-16** — Seeded (`0f0b75232e`).
- **2026-08-22** — `spec-conda-forge-packaging-inventory-operations` derived under pyforge-atlas and
  decomposed into the station backlog (`a20192dd84`). The Spec now reads `in-progress`: CAP-1
  (Story 17.1) chartered; CAP-2 (Story 17.2) code landed, live-execution verification deferred
  pending an attended, credentialed run.

## 2026-10-26 — A normalized data model and REST API pattern, waiting for a PyForge-native subject (folded from enterprise-data-models-and-apis)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/enterprise-data-models-and-apis.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/enterprise-data-models-and-apis.md`.*

## A normalized data model and REST API pattern, waiting for a PyForge-native subject

### The Dream

The source dream's actual subject — Data Center Entry application-survey data and Technology
Business Management cost-allocation data, normalized across BEAMS/ADS/ITM/BPPA source systems
into a three-tier raw/conformed/curated model, served via JSON:API — has no PyForge analog. This
repo tracks conda-forge feedstocks, PyPI packages, and BMAD fleet state, not enterprise
application inventories or IT cost allocation. What's genuinely reusable is not the domain, it's
the *pattern*: a three-tier normalization discipline plus a DRF-JSON:API-with-audit-history
serving shape, captured here as infrastructure waiting for a subject this repo actually has, not
as a commitment to build anything against DCE/TBM's own domain.

### What it looks like when real

Deliberately left thin — this Dream captures a REUSABLE PATTERN, not a scoped feature, because no
PyForge-native subject has been identified yet that needs it:

- IF a future PyForge capability needs multi-source data normalized into one queryable model with
  full change history (`django-simple-history`-style audit trail) and served as a REST API, this
  Dream is where that pattern's design notes would live — three-tier raw/conformed/curated
  staging, JSON:API response shape, group-based domain permissions.
- The closest current PyForge candidate is atlas's own `cf_atlas.db` — already multi-source
  (PyPI, conda-forge, CVE feeds, GitHub), already normalized into one queryable shape — but atlas
  solves this today with DuckDB + Kedro pipelines, not Django + DRF, and nothing currently asks
  for a REST API surface over it. [[atlas-query-dashboards]] is the nearer, better-evidenced need
  (visualize what's already there) versus this Dream's speculative "expose it over JSON:API."

### What is real

Nothing. This is the most purely speculative Dream in this batch — no PyForge subsystem currently
lacks a normalized model + REST API to the degree that building one would close an observed gap.
Captured for completeness of the source catalog's audit trail, not because investigation found a
real local need.

### Constraints

- **Not to be built against any subject until one is named.** This Dream should not advance past
  `dreamt` without a concrete PyForge-native domain to normalize — building the pattern in the
  abstract, with no real data to validate it against, would violate this repo's own "nothing
  speculative" principle.

### Non-goals

- **Not the DCE/TBM domain itself** — application-survey and cost-allocation data have no
  PyForge equivalent and are explicitly out of scope, not merely deferred.
- **Not GraphQL or gRPC** — JSON:API only, carried from the source dream unchanged (moot until a
  subject exists, but recorded for parity).
- **Not real-time data streaming** — batch/on-demand only, carried unchanged.

### Full feature audit against `enterprise-data-models-and-apis`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| Three-tier raw/conformed/curated model | **Pattern retained, domain dropped** | The staging discipline is reusable; the DCE/TBM domain it stages is not. |
| DCE application-survey models (27 model classes) | **Omitted, no PyForge analog** | No equivalent enterprise application-survey concept exists here. |
| TBM cost-allocation models (TBM v4.0 taxonomy) | **Omitted, no PyForge analog** | No equivalent IT cost-allocation concept exists here. |
| Django + DRF + JSON:API pattern | **Pattern retained** | Reusable infrastructure shape, independent of the domain it originally served. |
| `django-simple-history` audit trail | **Pattern retained** | Same — a generically useful pattern once ANY Django-backed model exists in this repo (none currently do outside Steward's dashboard). |
| `django-import-export` bulk admin import | **Omitted, no target data** | Nothing to bulk-import without a domain to import into. |
| Custom JSON:API bulk-array parser | **Omitted, no target data** | Same reasoning. |
| Group-based domain permissions | **Pattern retained** | Reusable once a real model exists to permission. |
| `transaction.atomic()` bulk updates | **Omitted, implementation detail** | Not a scoping decision — standard Django practice, assumed if this is ever built, not worth a dedicated line item. |

### Kinships

[[atlas-query-dashboards]] (the better-evidenced near-neighbor — visualizing what atlas already
has, versus this Dream's speculative "build a new normalized model with no named subject") ·
[[pyforge-atlas]] (nominal owner, by the source dream's own label; genuinely unclaimed until a
subject exists)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  flagged from the start as the weakest-evidenced Tier-3 candidate. Investigation confirmed no
  PyForge subsystem has an unmet need this pattern would close; kept only as a documented,
  intentionally-thin placeholder distinguishing "the pattern is reusable" from "this domain is
  reusable" — the latter is not. Should not be advanced without a concrete subject named first.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  enterprise-data-models-and-apis.md):** the source pattern is already the disconnected-friendly
  shape, worth recording so it survives intact if a subject is ever named: data enters as batch
  file drops (18 `django-import-export` CSV/XLSX resource classes loaded via admin and management
  commands; real-time streaming is an explicit non-goal), the Django ORM is the query engine (no
  external ETL service), and the JSON:API surface serves consumers inside the perimeter only.
  A PyForge realization must keep that: the full dependency set (Django, DRF,
  `djangorestframework-jsonapi`, `django-simple-history`, `django-import-export`) resolves from
  Artifactory-mirrored conda/PyPI indexes only (this repo's pixi channels are already swappable
  to internal mirrors); it deploys per today's K8s/OCP+PostgreSQL+Redis decision — image pulled
  from an internal registry, PostgreSQL in-cluster; DB credentials and any group-sync
  configuration reach the process via env/secret-mount only, composing with `_http.py`'s
  runtime-driven enterprise posture (env vars only, never committed config); and admin/browsable-
  API static assets serve WhiteNoise/`collectstatic`-style with zero CDN references — the same
  concern spec-atlas-query-dashboards CAP-4 makes contractual for dashboard surfaces.

- **2026-09-09** — Fleet readiness pass; status corrected `specified` → **`dreamt`** (operator
  batch § 2.2, row atlas-B4). § What is real still reads "Nothing", correctly — no PyForge
  subsystem has surfaced a need for this pattern. `docs/dreams/README.md` § status is explicit
  that "`specified` requires a Spec at `ready` or beyond"; `spec-enterprise-data-models-and-apis`
  is `extension-point`, an explicit park with **zero stories minted** — neither `ready` nor
  beyond. This Dream's own Constraint says the same thing in its own words: it "should not
  advance past `dreamt` without a concrete PyForge-native domain to normalize". The Spec keeps
  `status: extension-point`, unchanged, with its trigger intact; it reverts to `specified` the
  moment a subject is named and the Spec reaches `ready`.
  **The 2026-08-22 extension-point reframe stands, recorded here verbatim now that it no longer
  rides on the `status:` line:** *"reframed as an EXTENSION-POINT (operator): the fleet ships the
  socket/contract; the capability develops separately (incl. air-gapped) — see the spec's
  Extension contract section."* That reframe is sound and the seam is real — but the socket it
  names is steward's shipped AD-17 pluggable-app registry (`config/engine_patterns.py`), which
  belongs to steward, not to this Dream. Under the realization gate this Dream still has nothing
  of its own to exercise. Nearest-need note unchanged: [[atlas-query-dashboards]] remains the
  better-evidenced neighbour (itself retired the same day, batch C1).
  Cross-station residue for steward: `docs/dreams/README.md` should name `extension-point` as a
  recognised parked-Spec state that does NOT satisfy `specified`, and carry this row's corrected
  status.

## 2026-10-26 — Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration (folded from kedro-org-tooling-adoption)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/kedro-org-tooling-adoption.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/kedro-org-tooling-adoption.md`.*

## Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration

### The Dream

Kedro is used exclusively (`pyforge-atlas`'s own pipeline stack) but three of the Kedro
organization's own tools that would strengthen how that pipeline gets built and shown are
adopted nowhere: [`kedro-skills`](https://github.com/kedro-org/kedro-skills) (distributes
Kedro-editing AI guidance into `.claude/skills/`/`AGENTS.md`/`.cursor/rules/`),
[`publish-kedro-viz`](https://github.com/kedro-org/publish-kedro-viz) (a GitHub Action that
auto-builds and deploys Kedro-Viz to GitHub Pages on push), and
[`vscode-kedro`](https://github.com/kedro-org/vscode-kedro) (a VS Code extension: pipeline
navigation, dataset/param autocomplete, catalog validation, embedded Kedro-Viz, node
debugging).

A fourth, [`kedro-mcp`](https://github.com/kedro-org/kedro-mcp), was checked and found
already resolved — pinned (`pixi.toml`), genuinely wired into `pyforge.atlas.mcp.server`,
with its own `test_kedro_mcp_absent.py` graceful-degrade test, per a deliberate 2026-07-16
domain-research decision ("wrapped where its guidance scope helps, never load-bearing," FR-7).
Not part of this Dream's scope.

**Owner is `atlas`, not `steward`, deliberately** — investigated directly, not assumed.
The *mechanism* each of the remaining three needs already belongs to Steward:
`kedro-skills` needs the exact provisioning duty [[bmad-module-provisioning]] just proposed
(install a third-party AI-skill package non-interactively, reproducibly); `publish-kedro-viz`
needs exactly the shape `steward deploy dashboard` (Epic 2) already ships — build an
artifact, commit/push it to a GitHub-Pages-published location. But *which* Kedro skills are
actually correct against this repo's real pipelines, whether the viz's default output even
matches what atlas's own DAG looks like, and whether the IDE integration is worth adopting
given this repo is agent-edited far more than hand-edited — those are judgment calls only
the station that owns the Kedro pipelines can make. Per [[unity-data-stack]]'s own precedent
(Atlas owns that Dream without it shipping as `pyforge-atlas`), owning is the accountable
post, not a claim on the product.

### What it looks like when real

- `kedro-skills install <skill-id>` has been run against `pyforge-atlas`'s own Kedro project,
  the generated `.claude/skills/`/`.agents/skills/`/`AGENTS.md` content reviewed for
  accuracy against the real pipeline (not installed blind), and provisioned reproducibly —
  via [[bmad-module-provisioning]]'s own mechanism once it ships, or by hand if that Dream
  hasn't landed yet, but never by an undiscoverable one-off driver script (the same anti-
  pattern [[bmad-module-provisioning]] itself was captured to close).
- `publish-kedro-viz` runs in CI on every push touching `pyforge-atlas`'s pipeline code,
  publishing a live, always-current DAG view to GitHub Pages — replacing (or standing
  alongside) the existing MANUAL capture tasks (`kedro-viz-proto`, `capture-kedro-viz-proto`
  → static PNGs/HTML gallery), the same way `docs/dashboard/` is already auto-published
  rather than hand-regenerated.
- A documented, explicit decision exists on `vscode-kedro` — adopted (with a
  `.vscode/extensions.json` recommendation) or explicitly deferred with a stated reason
  (e.g. "this repo's Kedro code is edited almost exclusively by agents, not humans in VS
  Code") — not silently never-considered the way all three were before this Dream.

### What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured the moment the gap was
found (alongside the [[bmad-module-provisioning]] gap, same investigation) — the next step
is a Spec (`bmad-spec`), not code. `kedro-mcp`'s own already-resolved status (see above) is
recorded here so a future pass doesn't re-open a question already answered.

### Constraints

- **Wait for [[bmad-module-provisioning]] where the mechanism overlaps.** `kedro-skills`
  provisioning should not hand-roll a second one-off installer script while that Dream's own
  reproducible-provisioning mechanism is in flight — if it lands first, use it; if this Dream
  moves first, its own provisioning story should be written so `bmad-module-provisioning`
  can adopt it as a precedent, not a competing implementation.
- **Review before installing.** `kedro-skills`' generated guidance must be checked against
  `pyforge-atlas`'s real pipeline shape before being committed — it is AI guidance content,
  not a mechanical install-and-forget dependency.

### Non-goals

- Not re-evaluating `kedro-mcp` — already resolved, already wired, already deliberately
  scoped (FR-7, "wrapped, never load-bearing").
- Not deciding `vscode-kedro` in advance — this Dream requires the decision be made and
  recorded, not any particular outcome.

### Kinships

[[pyforge-atlas]] (the pipeline this tooling serves) · [[pyforge-steward]] (the provisioning/
deployment mechanisms this Dream's execution leans on) · [[bmad-module-provisioning]] (the
sibling gap found in the same investigation; `kedro-skills`' own provisioning is a direct
instance of that Dream's own problem statement).

### Realization log

- **2026-08-07** — Dream captured. Surfaced when the user asked why `kedro-mcp`,
  `kedro-skills`, `vscode-kedro`, and `publish-kedro-viz` weren't in use despite Kedro being
  the exclusive data-pipeline stack. Investigation found `kedro-mcp` already resolved (pinned,
  wired, deliberately scoped by 2026-07-16 domain research) and the other three genuinely
  absent everywhere. User asked for holistic ownership reasoning rather than a default pick;
  resolved as owner `atlas` (the domain knowledge these tools need is Atlas's own) with
  Steward named as the mechanism dependency for two of the three (provisioning, deployment)
  rather than the owner.

- **2026-08-10** — Realized, recorded by the fleet audit (Phase 2b): atlas Epic 12
  (12-1 kedro-skills audit-then-adopt, 12-2 publish-the-real-DAG continuously,
  12-3 the vscode-kedro verdict) shipped its decomposition and the Spec moved
  `draft → shipped` in the Phase 2 landing; the surviving open questions ride the
  Phase 3 atlas chain.

- **2026-09-09** — Fleet readiness pass. `realized` (Dream) and `shipped` (Spec) both **hold** —
  all three dispositions were re-verified as artifacts on disk: `kedro-skills-audit-report.md`
  (Cap 1), `.github/workflows/kedro-viz-publish.yml` (Cap 2), and `.vscode/extensions.json`
  alongside `vscode-kedro-decision.md` (Cap 3). One serialization defect recorded for the Spec's
  next re-derivation (readiness finding D-6): the four entries under the Spec's
  `open_questions:` key are all declared RESOLVED by the YAML comment directly above them, so any
  tool reading the machine key sees four open questions on a `shipped` Spec. They move verbatim
  under `resolved_questions:`, leaving `open_questions: []`. No content change — the resolutions
  were real.

## 2026-10-26 — Microsoft org sweep — audit one upstream org, package what is missing (folded from microsoft-org-sweep)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/microsoft-org-sweep.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/microsoft-org-sweep.md`.*

## Microsoft org sweep — the org-scale packaging audit

### The Dream

Take a single high-value upstream org — `github.com/microsoft/*` — walk every
repo it publishes, and answer one question exhaustively: **what is missing from
conda-forge that ought to be there?** Not a hand-picked wishlist; a systematic
sweep, tiered by demand, packaged in waves.

### Why it was archived

**Absorbed, not abandoned.** The sweep was the *manual* instance of a pattern
that wanted to be an engine: discovery of packaging gaps at upstream scale. It
folded into [[upstream-discovery]] as **Track B** of the trendshift effort
(`docs/specs/trendshift-conda-forge.md` — the June 2026 org audit, ~10–14
recipes across 3 waves), where Track A builds the cf_atlas **Phase T** trending
discovery engine that generalizes it. The scope survives; only the org-specific
framing retired.

### Kinships

[[upstream-discovery]] (absorbed it) · [[packaging-factory]] (the practice that
would have executed it) · [[pyforge-atlas]] (the discovery engine).

### Realization log

- **2026-06** — org audit scoped, ~10–14 recipes identified across 3 waves.
- **2026-07-25** — **ARCHIVED (absorbed)** into trendshift Track B during the
  Dream-lifecycle reconciliation; formerly a hardcoded console entry with no
  Dream file behind it.

## 2026-10-26 — Dream — PyForge Atlas Intelligence Platform (folded from pyforge-atlas-intelligence-platform)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/pyforge-atlas-intelligence-platform.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-atlas-intelligence-platform.md`.*

> **Superseded.** This Dream restates scope already fully realized by
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) (status: realized) and its shipped
> 38-story, 11-wave chain (Waves 0, A–H, I). Its "Realization" list maps directly onto
> already-shipped waves: Discovery Engine → Wave B/H (pipeline porting, factory personas);
> Schema Evolution → the schema v29→v30 work Wave I's post-audit truth-up already covers;
> Phase Orchestrator (Kedro/Dagster) → Wave C ("Integrate kedro-dagster for scheduling +
> execution"); DuckDB Analytics → Wave F, story F1, verbatim ("DuckDB consolidation + prove
> the cold-start claim"); air-gap capability → already implemented repo-wide via the
> `<HOST>_BASE_URL` redirect pattern documented in `project-context.md`. Its own
> "Acceptance" criteria ("all 15 phases ported," "schema v29→v30 migration tested,"
> "dashboards consuming cf_atlas data live") describe work that is already done — Atlas is
> 100% code-complete (38/38 stories, 930 real tests, retro delivered). Created 2026-08-02
> in the same bulk commit already found this session to contain fabricated content (a false
> migration note, boilerplate test-architecture docs, and two other duplicate dreams —
> Marshal's loop-orchestrator, Mason's recipe-validator — retired the same way). Retired
> same day rather than spec'd as new work. See `spec-pyforge-atlas-intelligence-platform`
> for the retirement record.

## PyForge Atlas — Intelligence Platform

### Vision

**Atlas** is the intelligence backbone of the PyForge factory — a Kedro/Dagster/DuckDB data pipeline that orchestrates discovery, analysis, and decision-support across the conda-forge ecosystem. It transforms raw package metadata into actionable intelligence: trending candidates, adoption signals, version velocity, security posture, and dependency completeness.

**The ask**: Build a deterministic, horizontally-scalable, air-gap-capable intelligence layer that makes every decision in the factory data-driven, observable, and auditable.

### Problem

- **Raw metadata is useless without context.** PyPI releases 500+ packages/day; conda-forge ingests them. Without structured discovery and ranking, operators drown in noise.
- **Decisions are scattered across tools.** Adoption heuristics live in one CLI, schema decisions in another, phase logic in a third. No single source of truth for "what we know about this ecosystem."
- **Phase logic is fragile.** 15 phases (B → N) orchestrate the pipeline. Each has rate limits, dependencies, and state management. One failure cascades; one wrong decision blocks the whole run.
- **Air-gap deployments are an afterthought.** Real enterprises can't phone home. Atlas must work offline: bundled schemas, cached feeds, deterministic reproducibility.

### Realization

**Atlas** delivers:

1. **Discovery Engine** — Trending-candidate classifier with 8 signals (GitHub trends, PyPI velocity, conda adoption, maintenance age, community size, license stance, platform coverage, ecosystem maturity). One query → ranked recommendations.

2. **Schema Evolution Layer** — 16 versions of the cf_atlas schema, each with backward-compatible views. Phase outputs declare their schema; validation happens on ingest. No silent schema mismatches.

3. **Phase Orchestrator** — Kedro/Dagster combo: Kedro for task graphs (deterministic, cached, reproducible), Dagster for scheduling and observability. Every phase produces a catalog entry; every output is versioned and validated.

4. **DuckDB Analytics** — Parquet-backed cold storage for billions of rows; DuckDB for OLAP queries in tests and dashboards. No PostgreSQL required; works offline.

5. **Determinism Contract** — Same inputs → byte-identical output, always. No timestamps in the logic path, no random walks, no "good enough" approximations. Operators trust the data.

### Success Criteria

- ✅ **Completeness**: Every phase in the original cf_atlas pipeline ported to Kedro nodes
- ✅ **Velocity**: Phase runs complete in <5 min (single-box) or <30 min (multi-worker)
- ✅ **Reliability**: 99.9% uptime for the discovery engine; 0 silent schema mismatches
- ✅ **Observability**: Every decision logged, every phase run recorded, every finding attributed
- ✅ **Air-gap**: Deployable to air-gapped environments with bundled schemas and no external API calls
- ✅ **Testability**: 15+ pipeline stages each with UT + IT + E2E coverage; determinism verified in CI

### Acceptance

Atlas is done when:
1. All 15 phases ported and passing locally
2. Schema v29 → v30 migration tested end-to-end
3. Discovery engine deployed to staging and ranking real packages
4. Dashboards consuming cf_atlas data live and accurate
5. Air-gap deployment tested in isolated network (no internet access)

## 2026-10-26 — Unity Data Stack — the enterprise innersource platform (folded from unity-data-stack)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/unity-data-stack.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/unity-data-stack.md`.*

> **Superseded and fully consolidated.** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names Unity Data Stack as a separate, substantial initiative
> that Atlas's project tree hosts — **not** a capability of Atlas's own
> `cf_atlas` pipeline (`spec-pyforge-atlas`'s own CAP-1..CAP-17 are
> untouched) and **not** a duplicate of anything Atlas already builds. This
> started 2026-08-02 as a dream-level-only consolidation, then was
> **upgraded the same day to a full chain consolidation by explicit user
> decision**, overriding this repo's default dream-level-only convention:
> Unity's own contract (9 capabilities, FR-1–60) is no longer a standalone
> Spec — it was folded verbatim into `spec-pyforge-atlas/SPEC.md` as
> `## Satellite: Unity Data Stack`, with its capabilities renumbered
> `CAP-18`..`CAP-26`; its PRD was folded into
> `prds/prd-pyforge-atlas-2026-07-17/prd.md`; its Architecture spine was
> folded into `architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
> with its invariants renumbered `AD-24`..`AD-46`. The original standalone
> documents were **not deleted** — they were moved intact to
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/{briefs/brief-unity-data-stack-2026-07-25,prds/prd-unity-data-stack-2026-07-25,architecture/architecture-unity-data-stack-2026-07-25,specs/spec-unity-data-stack}/`.
> It is also still **not** "the work is done" — epics/stories are
> deliberately not yet decomposed (planning ran to PRD + Architecture depth
> only) and no code has been written; the platform remains
> planning-complete and unscheduled.

## Unity Data Stack — a python-first innersource delivery model

### The Dream

An opinionated **shared monorepo for the enterprise**: teams co-contribute
reusable templates, plugins, libraries, components, services, dashboards,
reports, and applications on one python-first engineering platform — the
**Inner-Source Model**: open-source culture and practices *inside* the
enterprise. Chosen standards, shared toolchain, faster delivery, consistency by
construction. Where [[pyforge-charter|pyforge-genesis]] installs the *operating model*, Unity
Data Stack is the *platform* an enterprise runs on it.

### What exists (stranded across three gists, now snapshot in `docs/intake/gists/`)

- **The Constitution** (`spec-kit/`, 37 KB) — the spec-kit-format founding
  document: preamble, principles, standards for the innersource monorepo.
- **The working root** (`unity-data-stack-pixi-toml/`, 100 KB) — a complete
  pixi monorepo workspace config: per-package environments, unified
  test/lint/check-all tasks matching CI.
- **The toolchain spec** (`bmad-method-spec-enterprise-monorepo…/`, 12 KB) —
  Pixi orchestrator root + PDM/pip-tools (PEP 751) compiler +
  `pylock.toml` universal secure lockfile, with an agent role matrix
  (Architect/Developer/DevOps/Security/Compliance) that prefigures the crew.
- Cameo: the "Unity Knowledge Stack" infographic in the [[sentinel]] Design
  session (2026-04-18).

### Kinships

[[pyforge-charter|pyforge-genesis]] (the installer would bootstrap Unity instances) ·
[[pyforge-warden]] (the Security/Compliance agents of the toolchain spec) ·
[[enterprise-airgap]] (the deployment posture) · [[packaging-factory]]
(conda-native package supply).

### Realization log

- **2026-01 → 05** — constitution, pixi root, and toolchain spec authored as
  gists; never landed in a repo.
- **2026-07-23** — rediscovered in the gist audit; Dream seeded.

## 2026-10-26 — Upstream discovery — package it before it's asked for (folded from upstream-discovery)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/upstream-discovery.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/upstream-discovery.md`.*

> **Superseded (narrative only).** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names Upstream Discovery as a separate initiative that
> Atlas's project tree hosts — **not** a capability of Atlas's own `cf_atlas`
> pipeline (`spec-pyforge-atlas`'s Capabilities are untouched) and **not** a
> duplicate of anything Atlas already builds (it is a candidate-sourcing
> layer that would feed [[packaging-factory]], distinct from Atlas's
> intelligence signals). This is a dream-level consolidation only: the
> project's own contract — 5 capabilities, re-grounded in Atlas's shipped
> Kedro dataflow after the legacy phase-based design was superseded by the
> migration — still lives at `spec-upstream-discovery/SPEC.md`; it is not
> touched by this consolidation. It is honestly the earliest-stage of
> Atlas's three satellites and **not** "the work is done": the Spec itself is
> `status: draft`, with no PRD, no Architecture, and zero implementation —
> six open questions remain, including which of Atlas's 7 closed pipelines
> should host it. Archived 2026-08-02 as the narrative entry point only; its
> Spec continues independently.

## Upstream discovery — sense what the world is building

### The Dream

The factory should not wait for requests. It should **sense** what the
ecosystem is adopting — GitHub trending, org releases, momentum signals — and
carry the worthy candidates into conda-forge *before* anyone files an issue.
Discovery becomes a pipeline phase, not a hobby: signals in, tiered candidates
out, recipes drafted while the hype is still warm.

### What it looks like when real

- **cf_atlas Phase T**: the GitHub-trending discovery engine (schema v29→v30),
  a tiered packaging classifier, and the `trending-candidates` CLI/MCP tool.
- **Org audit track**: systematic sweeps of high-yield orgs (the June 2026
  `github.com/microsoft/*` audit: ~10–14 recipes across 3 waves).
- Candidates flow straight into [[packaging-factory]] campaign machinery, with
  [[pyforge-doctor]]-grade health screens (abandonment, license) up front.

### What is real

- The spec is authored, validated, and committed:
  `docs/specs/trendshift-conda-forge.md` (ready — resume at Wave A; first batch
  seeded by `cli-anything-hub`). Zero implementation yet.

### Realization log

- **2026-06-20** — trendshift spec authored (Track B absorbed the microsoft
  audit).
- **2026-07-23** — Dream retro-seeded. Post-migration note: Phase T should be
  born as a **Kedro node** in the new [[pyforge-atlas]] dataflow, not a legacy
  phase.

## 2026-10-26 — The "Corporate Brain" CMS atlas's own WikiSyncer has been waiting to push to (folded from wagtail-corporate-brain)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/wagtail-corporate-brain.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/wagtail-corporate-brain.md`.*

## The "Corporate Brain" CMS atlas's own WikiSyncer has been waiting to push to

### The Dream

This is not the speculative dream it first appeared to be. Atlas already has a real, tested,
network-injectable CLIENT for an external Wagtail/Django CMS — `factory/lasuite.py`'s
`LaSuiteClient` (create/update/get/list over the Wagtail REST shape) and `WikiSyncer` (idempotent,
content-digest-keyed push of the Karpathy-wiki's report pages), built for Story H3, verified
end-to-end against an in-memory mock with zero network. `resolve_lasuite_config` already defines
the exact contract a live server needs to satisfy: a base URL and an API token, both required or
the client degrades cleanly rather than pushing at a half-configured endpoint. What's missing is
entirely on the SERVER side — an actual running Wagtail instance to receive these pushes — which
this repo's own deferred-work ledger already names and scopes as `DW-H3`, explicitly an ATTENDED
bring-up (an operator's own infrastructure decision, not a code gap this Dream can close by
itself).

### What it looks like when real

Two genuinely different scopes, deliberately kept separate:

- **The narrow, well-evidenced scope**: a minimal live Wagtail/La Suite server satisfying
  `LaSuiteClient`'s already-defined REST contract, with a real httpx-backed opener injected in
  place of the mock — closing DW-H3 exactly as atlas's own deferred-work ledger already frames it.
  This alone would let the Karpathy-wiki's report pages actually reach a real "Corporate Brain"
  destination for the first time.
- **The much larger, genuinely speculative scope**: the source dream's full feature set — four
  custom Wagtail apps (branded reusable tables, interactive charts, brand color picker,
  heading-anchor blocks), OIDC-authenticated multi-author publishing, DRF APIs, embedded
  Panel/Bokeh dashboards (composing with [[atlas-query-dashboards]] if both existed) — none of
  which has a named PyForge audience of non-developer human authors. This repo's own content is
  authored by AI agents editing markdown/code directly; nothing currently needs a WYSIWYG
  publishing workflow.

### What is real

`DW-H3` (`pyforge-atlas`'s own deferred-work ledger): "the live La Suite/Wagtail SERVER +
credential + httpx opener bring-up (ATTENDED) — DEFERRED." Its own text confirms the client half
is complete and tested; only the operator decision to actually stand up a server remains open.
This Dream does not make that decision — it documents the shape it would take if made, and draws
the line between "close DW-H3" (real, scoped, evidenced) and "build a general enterprise CMS"
(speculative, no named audience).

### Constraints

- **Does not decide DW-H3's own attended bring-up.** That remains an operator decision outside
  this Dream's scope, exactly as atlas's own deferred-work ledger already frames it.
- **The narrow scope (closing DW-H3) and the broad scope (a full CMS) must not be conflated.**
  A future Spec against the narrow scope should not silently absorb the broad one's much larger
  surface without a separate, explicit decision.

### Non-goals

- **Not a general enterprise content-authoring platform** for non-developer human authors — no
  such audience has been named in this repo.
- **Not headless/API-only mode** — moot until the broader scope is ever justified.
- **Not multi-site/multi-tenant** — same.

### Full feature audit against `wagtail-cms-content-platform`

| Source feature | Disposition | Why |
|---|---|---|
| A live Wagtail/Django server satisfying `LaSuiteClient`'s REST contract | **Included, closes DW-H3** | The one piece with real, already-built, already-tested client-side evidence — the genuine gap. |
| `wagtailsite` app (base models, DSS models, snippets, hooks, endpoints) | **Omitted, scope depends on decision** | Belongs to the broad-scope decision, not the narrow DW-H3-closing one. |
| `wagtailtables` (branded reusable tables, Handsontable/TipTap editors) | **Omitted, no named author audience** | No non-developer content authors exist to use this. |
| `wagtailcharts` (10 chart types via Chart.js) | **Omitted, overlaps [[atlas-query-dashboards]]** | If interactive charts are ever needed, that Dream's Panel/Bokeh approach is the better-evidenced path, not a Wagtail-block reimplementation. |
| `wagtailcolorpicker` (brand color picker for rich text) | **Omitted, no named author audience** | Same reasoning as `wagtailtables`. |
| OIDC + django-allauth, group RBAC | **Omitted, no target authentication system** | No PyForge-native identity system this would integrate with yet. |
| DRF APIs alongside the CMS | **Omitted, speculative** | No named consumer. |
| `BokehPanelPage` (embed Panel dashboards in CMS pages) | **Omitted, contingent on both the broad CMS scope AND [[atlas-query-dashboards]]** | Real idea, but stacks two unproven dependencies. |

### Kinships

[[pyforge-atlas]] (the estate; DW-H3 lives in its own deferred-work ledger, Story H3 built the
client) · [[atlas-query-dashboards]] (the better-evidenced path to interactive charts/dashboards,
should the need arise, rather than Wagtail-specific blocks) · [[artifactory-download-intelligence]]
(a sibling atlas Dream from the same investigation, unrelated in subject but same "checked real
code before drafting" discipline)

### Realization log

- **2026-08-14** — Dream substantially re-scoped from the source catalog's original "weakest fit"
  tiering. Initial pass (before this batch's deeper investigation) rated this the lowest-priority
  dream of fifteen, reasoning "no non-developer publishing workflow exists to serve." Investigating
  [[atlas-query-dashboards]] surfaced `factory/lasuite.py`'s real, tested `LaSuiteClient`/`WikiSyncer`
  and `DW-H3`'s own deferred-work entry — the CLIENT side of exactly this capability already exists
  and is waiting on a server. Re-titled and re-scoped to distinguish that real, narrow,
  evidence-backed piece (closing DW-H3) from the much larger, still-genuinely-speculative full CMS
  feature set the source dream describes — the original "weakest fit" verdict was wrong for the
  narrow scope, right for the broad one.
- **2026-08-14** — Spec authored (spec-wagtail-corporate-brain, pyforge-atlas) per operator
  decision: spec-first, bring-up later — narrow scope only (live instance satisfying
  LaSuiteClient's existing contract, real httpx opener, round-trip/idempotency verified); the
  attended DW-H3 bring-up is scheduled separately; broad CMS scope stays excluded per the dream's
  own Constraint.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  wagtail-cms-content-platform.md):** the source platform runs entirely inside a private network,
  and the narrow DW-H3 instance must too. (1) Whichever way the spec's substrate open question
  resolves, installs come from mirrors only: conda-forge `wagtail` + `django-lasuite` resolved
  through an Artifactory-mirrored conda channel (this repo's pixi channels are already swappable
  to internal mirrors), or a container image pulled from an internal registry per today's
  K8s/OCP+PostgreSQL+Redis decision — never Docker Hub, never public PyPI at deploy time.
  (2) All static assets self-hosted: the source serves its CSS from app `static/` dirs
  (`custom.css`, `wagtail_admin.css`) and injects all editor JS (Draftail color picker,
  Handsontable/TipTap/Chart.js StructBlockAdapter media, Bokeh `render_embed()` resource tags)
  from local media — the live instance serves Wagtail admin + site assets
  WhiteNoise/`collectstatic`-style with zero CDN references, the exact concern
  spec-atlas-query-dashboards CAP-4 just made contractual for Panel/Bokeh; any future
  broad-scope chart/table blocks inherit that CAP-4 vendoring precedent rather than re-deriving
  it. (3) Credentials stay env-only: `LASUITE_BASE_URL`/`LASUITE_API_TOKEN` already resolve only
  from env (spec AD-2) — in-cluster that means secret-mounted env vars, matching `_http.py`'s
  truststore + JFrog/GitHub/.netrc chain (env vars only, never committed config); the httpx
  opener trusts the internal CA the same truststore-driven way. (4) The source's production auth
  is an internal OIDC IdP (form login only in DEBUG) — moot for the narrow Bearer-token scope,
  but any separately-decided broad scope inherits "internal IdP, no external auth callbacks."

- **2026-09-09** — Fleet readiness pass (operator batch § 2.3, C16 / row atlas-B6). **DW-H1's
  object-storage half is re-pointed off MinIO** onto the infra-kinds answer — an RWX volume, and
  for a multi-node target the storage class that provides it. `pyforge-unifying-strategy.md:406-408`
  is unambiguous and was re-affirmed on 2026-09-05: "No MinIO as a fourth core kind … Lane 1 media
  is RWX, and a multi-node target names its RWX-capable storage class" — and Wagtail *is* Lane 1,
  exactly the case that ruling anticipates. `spec-wagtail-corporate-brain/SPEC.md:24`, `:135` and
  `:137` re-render accordingly. The Never is **not** re-opened and no scoped exemption is granted;
  DW-H1 itself stays `open` and ATTENDED — only the storage kind it names is corrected. Neither
  this Dream's status nor the Spec's changes: the readiness pass re-confirmed this pair as an
  exemplar (Epic 16 `done`, DW-H3 still `open`, and the Spec correctly refusing to read `shipped`
  on paper alone, exactly as its own Success signal demands).

## 2026-10-26 — WASM Data Stack (folded from wasm-analytics-stack)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 44.1). The body below is `docs/dreams/wasm-analytics-stack.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/wasm-analytics-stack.md`.*

> **Superseded and fully consolidated.** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names the Wasm Analytics Stack as a separate, substantial
> initiative that Atlas's project tree hosts — **not** a capability of
> Atlas's own `cf_atlas` pipeline (`spec-pyforge-atlas`'s own CAP-1..CAP-17
> are untouched) and **not** a duplicate of anything Atlas already builds
> (Atlas's own G1 Pyodide/DuckDB-WASM compilation is a kinship this project
> reuses for its own out-of-scope v2 dashboard, not the same project). This
> started 2026-08-02 as a dream-level-only consolidation, then was
> **upgraded the same day to a full chain consolidation by explicit user
> decision**, overriding this repo's default dream-level-only convention:
> this project's own contract (5 capabilities, FR-1–17, honestly narrowed
> from its founding gist's broader claim) is no longer a standalone Spec —
> it was folded verbatim into `spec-pyforge-atlas/SPEC.md` as
> `## Satellite: Wasm Analytics Stack`, with its capabilities renumbered
> `CAP-27`..`CAP-31`; its PRD was folded into
> `prds/prd-pyforge-atlas-2026-07-17/prd.md`; its Architecture spine was
> folded into `architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
> with its invariants renumbered `AD-47`..`AD-56`. The original standalone
> documents were **not deleted** — they were moved intact to
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/{briefs/brief-wasm-analytics-stack-2026-07-25,prds/prd-wasm-analytics-stack-2026-07-25,architecture/architecture-wasm-analytics-stack-2026-07-25,specs/spec-wasm-analytics-stack}/`.
> It is also still **not** "the work is done" — epics/stories are
> deliberately not yet decomposed (planning ran to PRD + Architecture depth
> only) and no code has been written; the project remains planning-complete
> and unscheduled.

## Wasm-first analytics — sandboxed pipelines for the hardened enterprise

### The Dream

A modern analytical data stack whose logic runs as **Python-compiled WASI
components** — sandboxed, portable, high-performance — deployable on Red Hat
OpenShift under **Restricted SCC** (non-root UID 1001, read-only rootfs):
ingestion via **dlt** (Excel → FastAPI in the seed use-case), transformation via
**dbt**, native **OTel tracing + OpenLineage provenance**, one **Pixi** toolchain
bridging local dev, Podman "digital twins," and production OCP.

### Kinships

- [[sentinel]]'s WASM branch (ADR-037/038/039) dreamed the adapters; this stack
  is the analytics-shaped application of them.
- [[pyforge-atlas]] shipped the sibling proof (G1: the intelligence layer
  compiled to Pyodide/DuckDB-WASM).
- [[enterprise-airgap]] + [[presenton-pixi-image]] share the OCP-hardened,
  regulated-enterprise posture; [[unity-data-stack]] is the platform it would
  live on.

### What exists

- The architecture README (`wasm-first-analytical-data-stack-ocp-ready/` gist,
  2026-04-19 — same weekend as Sentinel v2.1).

### Realization log

- **2026-04-19** — architecture authored (gist); never landed.
- **2026-07-23** — Dream seeded from the gist audit.
