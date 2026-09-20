---
sources:
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py
  - pixi.toml
verified: 2026-09-20
---

# PyForge Station Cheat Sheet

This reference matrix provides a quick lookup for New Developers and Station Operators regarding the 8 primary PyForge stations, their operational domains, and their standard CLI entry points.

Run commands from the `pyforge-guild` environment (the session default), which carries `doctor`, `marshal`, `scribe` and `steward` and the `pyforge <station> <noun> <verb>` router over them. `herald`, `mason`, `warden` and `pyforge-atlas` are installed only in their own `pyforge-<station>` environments, so those rows use `pixi run -e pyforge-<station> …`. Every verb below is taken from the CLI's own `--help`.

| Station | Environment | Primary Responsibility | Common CLI Duties |
|---------|-------------|------------------------|-------------------|
| **Atlas** | `pyforge-atlas` | Kedro/DuckDB data pipelines over the conda-forge and PyPI universes, and the fleet dashboard. | `pyforge-atlas` (a Kedro run: `--from-nodes`, `--to-outputs`, …); pixi tasks `pyforge-atlas-bootstrap`, `pyforge-atlas-test`. The CFE atlas CLIs (`build-cf-atlas`, `query-cf-atlas`, `detail-cf-atlas`) are `local-recipes` tasks, not this package. |
| **Doctor** | `pyforge-guild` | System diagnostics, fleet-pulse monitoring, and the detector sources behind `detectors-ci`. Advisory — never a second PR gate. | `doctor check`, `doctor monitor --fleet`, `doctor diagnose --target <t>`, `doctor backlog-intake`, `doctor flags`; per-source `python -m pyforge.doctor.sources <name>` |
| **Herald** | `pyforge-herald` | Dream-to-deck bridge (Claude Design decks) plus progress, success-claim and notice moments. | `herald deck seed <slug>` / `pull` / `status` / `watch`, `herald progress`, `herald success publish <claim>`, `herald notice`, `herald scheduler run` |
| **Marshal** | `pyforge-guild` | BMAD-loop dispatch/loop supervisor: launch, watch, land and retire story sessions. | `marshal factory dispatch <slug> <key>`, `marshal factory drain --mode <m>`, `marshal factory spin`, `marshal status`, `marshal watch`, `marshal land <slug>`, `marshal retire`, `marshal refresh`, `marshal check` |
| **Mason** | `pyforge-mason` | Build engineering: conda recipe authoring/validation/builds (wrapping `conda-forge-expert`), package shipping, environment resolution. | `mason recipe new` / `validate` / `build` / `diagnose` / `optimize` / `scan` / `submit` / `update`, `mason package`, `mason environment`, `mason doctor` |
| **Scribe** | `pyforge-guild` | Team memory (`.claude/memory/`), the compiled knowledge graph, and grounded recall. | `scribe capture --type <t> --text "…"`, `scribe capture --promote`, `scribe recall "<query>"`, `scribe graph compile` (extras: `-e pyforge-scribe`), `scribe index` |
| **Steward** | `pyforge-guild` | Provisioning, credential lifecycle, platform deployment, workspace worktrees, budgets, suite upgrades. | `steward keys list` / `encrypt` / `rotate` / `audit`, `steward workspace start <slug>` / `ls` / `status` / `clean`, `steward deploy`, `steward provision`, `steward init`, `steward validate-fast`, `steward sync`, `steward upgrade`, `steward suite` |
| **Warden** | `pyforge-warden` | Dependency hygiene + vulnerability scanning with one schema-validated `ComplianceReport` and the one strict exit-code gate. | `warden scan <dir>` (the only verb) |

## Universal Station Invariants

When developing against any of these stations, be aware of the following universal rules:
1. **Tests:** Station-specific tests live in `src/shared/packages/pyforge-<station>/tests/{unit,meta,integration,fixtures}/` (every station has `unit/` and `meta/`; only some have `integration/`). Run them with `pixi run -e pyforge-<station> pyforge-<station>-test`, or all stations at once with `pixi run -e pyforge-guild pyforge-station-tests`.
2. **Dashboard Isolation:** Django lives only behind the `[dashboard]` extra in `src/shared/packages/pyforge-<station>/src/pyforge/<station>/dashboard/` (steward and atlas ship one today). The core station logic must never import Django at the module level, and the base package must run its CLI without the extra installed.
3. **Verdict Projection:** A station that projects an exit-code verdict implements a `verdict.py` module and ships a frozen JSON schema for its report — doctor's `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` and warden's `src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json` are the two today.
