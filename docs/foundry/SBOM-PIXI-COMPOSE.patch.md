# SBOM pixi compose — PR #1564 only (`sbom/pyforge-foundry-full-compose`)

## `pyforge-foundry-full` (Phase 1 + 1b full platform stack)

```toml
pyforge-foundry-full = { features = [
  "python",
  "pyforge-guild",
  "guild-tasks",
  "pyforge-core",
  "pyforge-testing-kit",
  "pyforge-marshal",
  "pyforge-steward",
  "pyforge-atlas",
  "pyforge-warden",
  "pyforge-doctor",
  "pyforge-mason",
  "pyforge-herald",
  "pyforge-scribe",
  "build",
  "grayskull",
  "crm",
  "conda-smithy",
  "platform-dev",
  "python-agent-platform",
  "platform-object-storage",
], no-default-feature = true }
```

- **Phase 1:** `build`, `grayskull`, `crm`, `conda-smithy`
- **Phase 1b:** `platform-dev` + `python-agent-platform` + `platform-object-storage` — Redis, Postgres+pgvector, Silo, **and** Langflow/dashboard local bring-up
- **Also:** `pnpm = ">=12.4.1"` on `feature.python.dependencies` (or `pyforge-guild`) — not a new feature
- **Inclusion:** packages used by PyForge code/operators (e.g. atlas `vizro`/`dagster`) come via their station/platform features — do **not** compose fat `local-recipes` for that
- **Never:** fat `local-recipes` feature, `desktop-lab`, or side PRs — edit #1564 only

## Guard

Do not replace `pixi.toml` with a path stub. Restore from `main` if corrupted; edit the env line / pnpm pin only.
