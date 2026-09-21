# SBOM pixi compose — PR #1564 only (`sbom/pyforge-foundry-full-compose`)

## `pyforge-foundry-full` (Phase 1 — BoM + platform; landed solvable set)

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
  "platform-object-storage",
], no-default-feature = true }
```

**Phase 1 target:** BoM (`build`/`grayskull`/`crm`/`conda-smithy`) + platform (`platform-dev`/`python-agent-platform`/`platform-object-storage`) + `pnpm`.

**Landed now:** as above — `conda-smithy`, `platform-dev`, and `python-agent-platform` omitted.  `platform-dev` is omitted because the estate PostgreSQL pin is major 17 (`>=17.11,<18`) and composing it pulls `libpq 18` via `psycopg`, breaking the union solve; do not bump the PostgreSQL major to force the compose.  See `pyforge-foundry-full-sbom.md` for remaining gaps.

**Also landed:** `pnpm = ">=12.4.1"` on `feature.python.dependencies`; `postgresql` pins restored to `>=17.11,<18` on `platform-dev` / `python-agent-platform`.

**Never:** fat `local-recipes` feature, `desktop-lab`, or side PRs — edit #1564 only.

## Guard

Do not replace `pixi.toml` with a path stub. Restore from `main` if corrupted; edit the env line / pins only.
