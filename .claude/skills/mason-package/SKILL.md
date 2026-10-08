---
name: mason-package
description: >
  Hand-authored operating procedure for Mason's native package craft: build
  wheel, sdist, and conda artifacts from one manifest, then ship to PyPI,
  TestPyPI, a conda channel, or conda-forge. Use when driving pyforge mason
  package build or pyforge mason package ship (not recipe work — that stays in
  conda-forge-expert). Read pyforge-mason for the full station grammar.
---

# mason-package

Mason's **package** noun is built natively (not wrapped from conda-forge-expert).
This skill walks the dual-ship motion: one build, then one or more ship targets,
with a per-target receipt. Grammar is always **`pyforge mason …`** from the repo root.

For every other Mason noun (`recipe`, `environment`, `doctor`), read
[pyforge-mason](../pyforge-mason/active/pyforge-mason/SKILL.md)
(`.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md`).

## Build — `pyforge mason package build`

Build distributable artifacts from a project directory (its own `pyproject.toml` /
`pixi.toml`). v1 scope: **`--target library`** only.

```bash
pyforge mason package build PROJECT_PATH --target library
```

- Produces **wheel**, **sdist**, and **`.conda`** paths in the command output.
- **Uploads nothing** — build is strictly local artifact generation.
- Does **not** require conda-forge-expert or a resolved CFE root.

Optional: `--format json` for a single JSON document on stdout (see pyforge-mason).

## Ship — `pyforge mason package ship`

Ship from the **current working directory** as the project root (there is no separate
project-path flag on ship). Targets are a comma-separated list on **`--to`**.

```bash
# Dry run (default): prints the plan, ships nothing
pyforge mason package ship --to pypi-test,channel:mychannel

# Real ship after reviewing the plan
pyforge mason package ship --to pypi-test,pypi --yes
```

Bare-noun alias (the one documented exception):  
`pyforge mason package --ship TARGETS` behaves like `package ship --to TARGETS`.

### Ship targets (exact vocabulary)

| Target | Meaning |
|---|---|
| `pypi-test` | TestPyPI rehearsal upload (same credential names as PyPI; not irreversible) |
| `pypi` | Production PyPI upload (**irreversible** once published) |
| `channel:<name>` | Upload the built `.conda` to a named pixi channel |
| `conda-forge` | Open (or report) a **staged-recipes** PR for a recipe under the CFE tree |

Invalid tokens fail the **whole command** before any target runs.

### Dry run, `--yes`, and credentials

- **Default is dry run** — without **`--yes`**, Mason builds (when needed for the plan),
  prints what would happen, and **does not upload**.
- **`--yes`** confirms a real ship for the named targets.
- **`TWINE_USERNAME`** and **`TWINE_PASSWORD`** must be present (non-empty) in the
  environment **before** PyPI or TestPyPI builds run; missing credentials fail that
  target with a clear error, not mid-upload.
- One target's failure does **not** stop the others in the same invocation.

### TestPyPI gate before PyPI (`pypi-test` + `pypi`)

When **`pypi`** appears in the same `--to` list as **`pypi-test`**, Mason runs the
**first** `pypi-test` target **once**, ahead of the rest, and **gates** every `pypi`
target on that rehearsal reaching a **terminal** success state. If rehearsal fails,
is pending, or was not attempted, **`pypi` is not uploaded** — the receipt names the
gate and the rehearsal state.

Recommended flow:

1. `pyforge mason package build PROJECT_PATH`
2. `pyforge mason package ship --to pypi-test` (dry run, then `--yes` for rehearsal)
3. `pyforge mason package ship --to pypi-test,pypi --yes` only after rehearsal is green

You can request `pypi-test` alone without gating anything.

### `conda-forge` target — link CFE, do not restate recipe procedure

The **`conda-forge`** target ships **recipe source** via Mason's recipe port (not the
`.conda` binary from package build). Recipe authoring, validation, pins, selectors, and
submission mechanics live only in **conda-forge-expert** — link it, never copy gotchas
or submission steps here.

Read
[conda-forge-expert](../conda-forge-expert/SKILL.md)
(`.claude/skills/conda-forge-expert/SKILL.md`) for everything about the recipe and its
submission.

For **`conda-forge`** only, pass **`--recipe-path`** to the recipe directory under
`<cfe-root>/recipes/<name>/`. A repeat ship while a PR is already open reports
**pending** with the existing reference (no second PR).

### Optional flags shared with ship

- **`--target library`** — what to build when a target needs artifacts (default).
- **`--recipe-path PATH`** — recipe directory for `conda-forge` only; ignored for other targets.

## Receipt and exit codes

Ship output lists **one result per target** (state, message, reference when present).
Exit code is **non-zero if any target failed**; dry-run plans still exit 0 when Mason
ran successfully. See pyforge-mason for the full exit-code table.

## What this skill is not

- Not SKF-compiled — do not nest under `pyforge-mason/`.
- Not a substitute for **conda-forge-expert** on recipe questions.
- Does not promise behavior Mason's CLI lacks today — when in doubt, read
  `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py` and `package.py`.
