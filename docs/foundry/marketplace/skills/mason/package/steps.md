# Steps — @mason/package

Run these from the project you want to build. Verified 2026-10-21 against the
engine modules `pyforge.mason.engines.pep517` and `pyforge.mason.engines.pixi`
and the tools on the verifying host. Each version below is what that tool's
`--version` printed on that host on 2026-10-21, unless the step says otherwise.

**Before you start.** `pyforge-mason` 0.1.0 and `pyforge-core` returned HTTP
404 on PyPI, conda-forge, and SelfExplainML on 2026-10-21. Steps 1 and 4 wait
on those packages. Steps 0, 2, and 3 run today.

## 0. Install the published tools

- `build` 1.6.1: `pip install build` (PyPI `build`) or
  `conda install -c conda-forge python-build`. It installs the
  `pyproject-build` command.
- Your project's build backend, the package named under
  `[build-system] requires` in `pyproject.toml` (for example `hatchling` or
  `setuptools`), in the same environment. `pyproject-build --no-isolation`
  does not install it and stops with `BackendUnavailable` when it is missing.
- `pixi` 0.81.0 (re-read 2026-10-28), for step 3 only:
  `conda install -c conda-forge pixi`, or the installer at https://pixi.sh.

## 1. See the station command (waits on `pyforge-mason`)

When `pyforge-mason` is on your `PATH`:

```bash
pyforge mason package build . --target library
```

That build uploads nothing. `--target library` is the v1 target.

## 2. Build a wheel and sdist with the engine the station calls

From the project directory:

```bash
pyproject-build --no-isolation
```

That is the argv in `pyforge.mason.engines.pep517`. The same module says the
console script is `python -m build --no-isolation --outdir dist`.

## 3. Optional conda artifact

```bash
pixi build --output-dir dist
```

That is the build argv in `pyforge.mason.engines.pixi`
(`pixi build --output-dir`). This is not a pixi environment run.

## 4. Do not upload in the pilot (waits on `pyforge-mason`)

`pyforge mason package ship --to pypi-test` is a dry run until `--yes`.
After `--yes` the station runs `twine upload --non-interactive
--disable-progress-bar` for a PyPI target (`twine` 7.0.0 was present on the
verifying host) or `pixi upload prefix --channel <name>` for a channel.
Do not run `twine upload` or `pixi upload` from these steps. `pypi`
publishes permanently.

## 5. Stop

A conda-forge recipe is a different skill. Do not open a feedstock from here.
