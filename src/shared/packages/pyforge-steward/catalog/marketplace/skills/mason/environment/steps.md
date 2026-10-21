# Steps — @mason/environment

Run these from the project you want to lock. Verified 2026-10-21 against
the commands that exist in this repo. Versions below are what that check
printed.

## 1. See the station command

When `pyforge-mason` is on your `PATH`:

```bash
pyforge mason environment --help
```

That help lists `lock` and `check`. `lock` requires `--output`. `check`
requires `--lockfile`.

**Unpublished.** `pyforge-mason` 0.1.0 and `pyforge-core` returned HTTP 404
on PyPI, conda-forge, and the SelfExplainML channel on 2026-10-21. Until
those packages are published, step 1 does not run on a teammate machine.

## 2. Lock with the engine the station calls

This is the argv `conda-lock lock` in `engines/condalock.py` (binary
`conda-lock`, then `lock`, then `-f` per manifest, then `--lockfile`).
Verified: `conda-lock, version 4.0.2`.

```bash
conda-lock lock -f pyproject.toml --lockfile conda-lock.yml
```

Add one `-p` per platform only when you need to name them, for example
`-p linux-64 -p osx-arm64`.

## 3. Check

```bash
pyforge mason environment check --lockfile conda-lock.yml
```

A non-zero exit means the lockfile is stale or conda-lock failed. This
command depends on the unpublished `pyforge-mason` package. There is no
separate published command that performs the station's temporary-copy
check safely.

## 4. Stop

If the work becomes a conda-forge recipe, stop and use the
conda-forge-expert procedure. Do not invent a recipe from this skill.
