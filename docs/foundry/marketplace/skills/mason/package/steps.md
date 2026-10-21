# Steps — @mason/package

Run these from the project you want to build. Verified 2026-10-21.
The 2026-10-20 paper skill card is sample data and is not this runbook.

## 1. See the station command

When `pyforge-mason` is on your `PATH`:

```bash
pyforge mason package build . --target library
```

That build uploads nothing. `--target library` is the v1 target.

**Unpublished.** `pyforge-mason` 0.1.0 and `pyforge-core` returned HTTP 404
on PyPI, conda-forge, and SelfExplainML on 2026-10-21.

## 2. Build a wheel and sdist with the engine the station calls

From the project directory:

```bash
pyproject-build --no-isolation
```

That is the argv in `engines/pep517.py`. The same file says the console
script is `python -m build --no-isolation --outdir dist`. Verified:
`build` 1.6.1.

## 3. Optional conda artifact

```bash
pixi build --output-dir dist
```

That is `engines/pixi.py`'s build argv (`pixi build --output-dir`). Verified:
`pixi` 0.82.0. This is not a pixi environment run.

## 4. Do not upload in the pilot

`pyforge mason package ship --to pypi-test` is a dry run until `--yes`.
The upload binaries exist (`twine` 7.0.0, `pixi upload prefix --channel`).
Do not run them from these steps. `pypi` publishes permanently.

## 5. Stop

A conda-forge recipe is a different skill. Do not open a feedstock from here.
