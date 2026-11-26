---
sources:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/models.py
  - src/shared/packages/django-warden/src/django_warden_fabric/models.py
  - src/shared/packages/django-pyforge/src/django_pyforge/models.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/db.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/state.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/boot.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py
verified: 2026-11-26
---

# Where each station keeps state

Each station stores what its job needs, and the stores differ on purpose: a data station keeps columnar files, a
run supervisor keeps journals, a memory station keeps checked-in text. This page says where each one is, whether it is
a record or can be rebuilt, and what to back up. It does not propose one store for all eight.

Two words used below. A **record** holds something entered or observed once; losing it loses information. A
**derived** store is rebuilt from other inputs by a command, so it is safe to delete.

## By station

| Station | Where | Kind | Rebuilt by, or back up |
|---|---|---|---|
| Atlas | Parquet files under the data root: `PYFORGE_ATLAS_DATA_ROOT`, by default `data/` inside the atlas package directory | Derived | Re-run the pipelines (`pyforge atlas run`). They fetch from upstream sources, so a rebuild costs time and network. |
| Atlas | `atlas.duckdb`, by default `data/plane/atlas.duckdb` inside the atlas package directory; `PYFORGE_ATLAS_DATA_ROOT` does not move it | Derived | Rebuilt from the Parquet store. |
| Atlas | Admission locks in the sibling directory `<data root>.locks` | Neither: a live guard | **Never delete a lock while a run is live.** Removing a held lock lets a second writer start on the same dataset. |
| Doctor | Nothing of its own | — | `monitor --surface PATH` writes a summary to the path you name, and `flags kill-switch` rewrites the flag tree file, which git tracks. |
| Herald | `.herald/herald.db` (SQLite): progress, success claims, the notice index | Record, local to the operator, ignored by git | Back up the file. |
| Herald | Notice bodies under `notices/` | Record | Back up with the repository. |
| Herald | `.herald/bridge-state.json`: each deck's Design project and what was last pulled | Record | Back up; a deck's `README.md` "Design project" section can seed it again. |
| Herald | `.herald/deck-qa/<slug>/` | Derived | `herald deck qa`. |
| Herald | Published decks in the object store | Record | The store's own backup. |
| Marshal | Loop homes under `~/.bmad-loops/<slug>`: a worktree and the rendered policy | Working copy | Recreated by `marshal init`; anything not yet landed is a record. |
| Marshal | Run journals and story files in the project's Tier-3 store, `_bmad-output/projects/<slug>/implementation-artifacts/` in the primary checkout (a loop home reaches it through a link) | Record, ignored by git | Back up that directory in the primary checkout; a copy of a loop home that does not follow links misses it. |
| Marshal | The rendered `policy.toml` in each loop home | Derived | Rendered again by `marshal refresh`, which also brings the loop branch up to date with `main` and pushes it; never edit the file. |
| Marshal | `.marshal/seed-state.yml` and the plan file in a seeded repository | Record | Back up with that repository. |
| Mason | Nothing for the command line | — | The portal's artifact index is derived and rebuilt when the portal starts. |
| Scribe | `.claude/memory/`: one file per entry, and `MEMORY.md` | Record, tracked in git | Git is the backup. |
| Scribe | The compiled graph under `.claude/data/pyforge-scribe/` | Derived, ignored by git | `scribe graph compile` rebuilds it from scratch. |
| Steward | Files under `.steward/` at the repository root: registers, snapshots and logs | Mixed | Snapshots (`ci-status.json`, `ci-vars.json`) are re-read from GitHub by `steward ci status` and `ci vars`. Treat the logs and registers as records. |
| Warden | `[tool.pyforge-warden]` in `pyproject.toml`; the committed waiver file; an optional baseline file | Record, tracked in git | Git is the backup. |
| Warden | The offline vulnerability database and the feed caches, in directories named by environment variables | Derived | The feed refresh scripts under `pyforge-warden/scripts/` and `scripts/platform-provision-osv-offline-db.sh` fetch them again. |

## In the platform host's database

Some state lives in the host's PostgreSQL database rather than beside a station. Back it up as one database.

- Steward's `dashboard` extra: audit entries, work passports, corridor loads, the quarantine shelf.
- Warden's portal: compliance jobs, fleet repositories, runs and scans, and fix proposals.
- The host itself (`django-pyforge`): run state and the handles of started MCP tools.
- Herald's portal: one row per published deck export (the bytes are in the object store).
- Marshal: the run state its supervisor publishes, into the host's run-state table.
- Scribe, only when `PYFORGE_GRAPHSTORE_OWNER` is `steward`: the compiled graph, which is derived.

## Rules that hold across stations

- A derived store is never edited by hand. Change its inputs and rebuild.
- A store that git ignores is local to one machine. Two operators do not share Herald's SQLite file or a loop home.
- Scribe's compiled graph can also be written into Atlas's `atlas.duckdb` (owner `atlas`). Deleting that file then
  removes both Atlas's database and the compiled graph; both are derived.
