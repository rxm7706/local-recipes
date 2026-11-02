# Glossary — Atlas

Companion to `SPEC.md` (added 2026-11-01, EGM fleet audit ATL-M-C6). Pointer-only: one line per station term, each
naming where the term is defined, or defining it in one line where nothing else does. Fleet terms (station, `CAP-n`,
`FR-n`, `AD-n` and its prefixes, A and B, CFE, twin, the tiers, Path B, Lane 1) are defined in
`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 0. The station's other companions keep their own
terms: `signals.md` (the legacy phases and their nodes), `degradation-contract.md` (the markers), `gate-contract.md`
(the gates), `catalog-contract.md` and `catalog-sources.md` (the datasets and their tiers), `live-sources.md` (each
live source, its floor and its owning CAP). `AD-n` without a prefix is an atlas spine decision
(`architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`).

## Legacy and parity (CAP-64..CAP-68)

- **legacy, `CFA`** — `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`, the monolith atlas ports; `signals.md`, the paragraph above its phase table.
- **`cf_atlas.db`** — legacy's SQLite database, the same-day parity oracle each `live-sources.md` row compares against.
- **phase letters (B, C, E, E.5, F, G, H, J, K, L, M, N, P, …)** — legacy `CFA`'s phases; `signals.md` maps each to its node, `live-sources.md` names the phase each source feeds.
- **R1** — the cf-graph source move (`regro/cf-graph-countyfair` now redirects to `conda-forge/conda-forge-bot-data`) that left legacy Phases E, J and M reading 0 rows; the Dream's 2026-10-18 entry, item R1.
- **floor** — the per-row figure a live source is held to; `live-sources.md`, its **Floor** column and opening paragraph.
- **last-good, `stale`** — `degradation-contract.md` (the `stale` marker, and the rule that a skipped node keeps the last-good dataset intact).

## Sources and fetches (CAP-64..CAP-68)

- **split graph repos** — the conda-forge bot's `conda-forge-bot-data-node_attrs`, `-pr_info` and `-version_pr_info` repositories, sharded paths, that replaced the single cf-graph tarball; CAP-64's intent, Story 34.3.
- **refresher** — the fetch a store dataset owns and runs from its own `save` when a node's `RefreshRequest` says the store is due; `datasets/refresh.py` (`RefreshRequest`).
- **driver node** — a pipeline node whose output is the trigger a dataset's `save` acts on, so the node stays pure and the fetch stays in the dataset; Story 34.8 (migration status), Story 36.1 (the Basilisk triggers).
- **vdb** — AppThreat's vulnerability database, built in the `vuln-db` pixi env and refreshed into `vulnerability_vdb_store`; Story 34.7.
- **AOSS** — Google's Assured Open Source Software; atlas reads its premium Python list into `discovery_aoss_premium_python_raw`; Story 34.6.
- **Basilisk** — prefix.dev's vulnerability API at `api.basilisk.prefix.dev`, undocumented; `/v1/packages` answers unauthenticated, the advisory endpoints need a bearer token; CAP-66 and the 2026-10-18 ruling on its open question.
- **actionable universe** — the conda-forge packages the VCS and registry batches draw from; CAP-65's intent, and legacy's `v_actionable_packages` scope (`signals.md`, Phase B).
- **`identity_source`** — the column of `identity_packages_primary` naming a row's source; its values are listed in `live-sources.md` (the identity row).
- **`DW-B5-2`** — the deferred-work row for injecting concrete refreshers through Dagster resources, which CAP-64 supersedes for public sources; `deferred-work-ledger.md` § DW-B5-2.

## Runs (CAP-64..CAP-69)

- **plain run** — `pyforge atlas run` with no `--pipelines`; what it holds: CAP-64's intent (Story 34.14).
- **public run** — a run with no `PYFORGE_ATLAS_CREDENTIALED` and BigQuery off, as the Pages job runs; AD-11 and CAP-63's 2026-10-19 amendment.
- **the opt-in, the credentialed switch** — `PYFORGE_ATLAS_CREDENTIALED=1`, set by the operator for one run; the Constraint *Public sources live by default; credentials only on the operator's opt-in*.
- **the member** — `src/shared/packages/pyforge-atlas`, the Kedro project `pyforge atlas run` runs in; CAP-69's intent.

## Boards (CAP-63, CAP-69)

- **wired, rewired and new-node boards** — the three groups CAP-69's success lists by page id (the Dream's 2026-10-19 entry, *Evidence*).
- **on-demand board** — a board that shows a tool's result and stays empty until a user runs the tool; CAP-69's intent and success name the six.
- **honest-empty** — a board that renders an empty table under a note saying why, never placeholder rows; the word as the Dream's 2026-10-19 entry and CAP-69 use it.
- **board projections** — the flag `pyforge.atlas.board_projections`, under which the projected boards read the datasets the pipelines write; CAP-69's intent.
