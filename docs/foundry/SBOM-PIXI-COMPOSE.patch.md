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
  "platform-dev",
  "platform-dev",
  "platform-object-storage",
], no-default-feature = true }
```

**Phase 1 target:** BoM (`build`/`grayskull`/`crm`/`conda-smithy`) + platform (`platform-dev`/`python-agent-platform`/`platform-object-storage`) + `pnpm`.

**Landed now:** as above — `conda-smithy` and `python-agent-platform` omitted until union solves (see `pyforge-foundry-full-sbom.md` gaps).

**Also landed:** `pnpm = ">=12.4.1"` on `feature.python.dependencies`; `postgresql = ">=18.3,<19"` on `platform-dev` / `python-agent-platform` (libpq 18 / psycopg).

**Never:** fat `local-recipes` feature, `desktop-lab`, or side PRs — edit #1564 only.

## Guard

Do not replace `pixi.toml` with a path stub. Restore from `main` if corrupted; edit the env line / pins only.
