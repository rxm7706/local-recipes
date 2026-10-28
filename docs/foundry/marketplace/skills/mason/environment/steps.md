# Steps — @mason/environment

Run these from the project you want to lock. Verified 2026-10-21 against the
engine module `pyforge.mason.engines.condalock` and the tools on the verifying
host. Each version below is what that tool's `--version` printed on that host
on 2026-10-21.

**Before you start.** `pyforge-mason` 0.1.0 and `pyforge-core` returned HTTP
404 on PyPI, conda-forge, and the SelfExplainML channel on 2026-10-21. Steps 1
and 3 wait on those packages and do not run on a teammate machine until they
are published. Steps 0 and 2 run today.

## 0. Install the published tools

- `conda-lock` 4.0.2: `pip install conda-lock` (PyPI `conda-lock`) or
  `conda install -c conda-forge conda-lock`.

Check: `conda-lock --version` prints `conda-lock, version 4.0.2` or newer.

## 1. See the station command (waits on `pyforge-mason`)

When `pyforge-mason` is on your `PATH`:

```bash
pyforge mason environment --help
```

That help lists `lock` and `check`. `lock` requires `--output`. `check`
requires `--lockfile`.

## 2. Lock with the engine the station calls

```bash
conda-lock lock -f pyproject.toml --lockfile conda-lock.yml
```

This is the argv `pyforge.mason.engines.condalock` assembles: the binary
`conda-lock`, then `lock`, then one `-f` per manifest, then `--lockfile`.
The station discovers manifests in this order: `pyproject.toml`,
`environment.yml`, each `requirements*.txt`, `pixi.toml`. Substitute the
manifests your project holds; `conda-lock` exits non-zero on a file that is
not there:

- `pyproject.toml` only: the command as written.
- `environment.yml` only: `conda-lock lock -f environment.yml --lockfile conda-lock.yml`.
- `pyproject.toml` and `environment.yml`: `conda-lock lock -f pyproject.toml -f environment.yml --lockfile conda-lock.yml`.
- a `requirements.txt` or `pixi.toml` beside them: one more `-f <file>` each,
  in the discovery order above.

Add one `-p` per platform only when you need to name them, for example
`-p linux-64 -p osx-arm64`.

## 3. Check (waits on `pyforge-mason`)

```bash
pyforge mason environment check --lockfile conda-lock.yml
```

A non-zero exit means the lockfile is stale or conda-lock failed. The station
check runs `conda-lock lock --check-input-hash` against a
temporary copy of the lockfile, not against the lockfile in place. There is
no separate published command that performs the station's temporary-copy
check safely.

## 4. Stop

If the work becomes a conda-forge recipe, stop and use the
conda-forge-expert procedure. Do not invent a recipe from this skill.
