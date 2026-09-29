---
sources:
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cli.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - pixi.toml
verified: 2026-09-20
---

# Station CLI Operations

Every station in the PyForge Estate is accessed via a unified CLI adapter rather than invoking station packages directly. The host never imports `pyforge.*` logic for execution; everything routes through the CLI.

## The Unified Command Grammar

The basic structure of a PyForge CLI command is:
```bash
pyforge <station> <noun> <verb> [options]
```

`pyforge` (`src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py`) is dispatch only: it maps the station token to that distribution's own console script (`steward`, `marshal`, `scribe`, `doctor`, …) and forwards the remaining arguments. Calling the station script directly (`steward workspace start …`) is the same command.

Run station commands from the `pyforge-guild` environment — the session default for every agent and harness. It carries `doctor`, `marshal`, `scribe` and `steward`; `pyforge --help` there lists exactly those four stations. `herald`, `mason`, `warden` and `pyforge-atlas` are installed only in their own `pyforge-<station>` environments. `local-recipes` (10 GB) is Mason's recipe-factory environment and includes every Guild task, so it also works, but it is not the default.

### Example: Invoking the Steward
The Steward station handles workspace provisioning and credential lifecycle. To start a new scratch workspace:
```bash
pixi run -e pyforge-guild pyforge steward workspace start <slug>
```

To list known credential identities (never a secret value):
```bash
pixi run -e pyforge-guild pyforge steward keys list
```

## Discovering Capabilities

Each station defines its own duties (subcommands). To see what a station can do, run its root help command:

```bash
pixi run -e pyforge-guild pyforge <station> --help        # doctor, marshal, scribe, steward
pixi run -e pyforge-<station> <station> --help            # herald, mason, warden
```

For example, `pixi run -e pyforge-mason mason --help` lists `recipe` (new / validate / build / diagnose / optimize / scan / submit / update, wrapping `conda-forge-expert`), `package`, `environment` and `doctor`.

## Scribe Data Recall

The Scribe station maintains team memory (`.claude/memory/`) and its compiled knowledge graph. It is frequently accessed by developers and agents to recall context. Since scribe Story 19.2 the core `scribe` package is in `pyforge-guild`, so capture and recall run from the session default; only `scribe graph compile` with its heavy extras (graphifyy, cocoindex, psycopg) needs `-e pyforge-scribe`.

To retrieve a team decision or fact (the answer always carries a resolvable citation, or reports no grounded coverage — it never invents one):
```bash
pixi run -e pyforge-guild scribe recall "<query>" --mode planning
```
*(`--mode` names a candidate bag: `planning` (docs + memlogs), `memory`, or `code`; `--scope <slug>` restricts to one project's planning tree; `--kind` is the finer-grained alternative, exclusive with `--mode`.)*

To record a decision:
```bash
pixi run -e pyforge-guild scribe capture --type <feedback|project|reference> --text "..."
```

## Adding New CLI Duties

If you are a developer adding a new capability to a station:
1. Implement the logic in `src/shared/packages/pyforge-<station>/src/pyforge/<station>/`.
2. Register the duty in that package's `cli.py` (for marshal, the `cli/` package).
3. Update the station's own CLI tests — steward's `tests/unit/test_cli.py`, for instance, asserts the exact `DUTIES` tuple, so a new duty that is not added there fails CI.
