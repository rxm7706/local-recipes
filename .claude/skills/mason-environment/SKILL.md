---
name: mason-environment
description: >
  Hand-authored operating procedure for Mason's native environment craft:
  resolve mixed conda and pip manifests into one lockfile, then verify the
  lockfile has not gone stale. Use when driving pyforge mason environment
  lock or pyforge mason environment check (not recipe work — that stays in
  conda-forge-expert). Read pyforge-mason for the full station grammar.
---

# mason-environment

Mason's **environment** noun is built natively (not wrapped from conda-forge-expert).
This skill walks dependency binding: one lock, then a CI-style stale check.
Grammar is always **`pyforge mason …`** from the repo root.

These verbs do **not** require conda-forge-expert or a resolved CFE root.

For every other Mason noun (`recipe`, `package`, `doctor`), read
[pyforge-mason](../pyforge-mason/active/pyforge-mason/SKILL.md)
(`.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md`).

## Manifest discovery and explicit paths

Both verbs accept zero or more **`MANIFEST_PATH`** positionals
(`pyproject.toml`, `environment.yml`, `requirements*.txt`, `pixi.toml`).

- **Omit all positionals** — Mason discovers manifests in the **current working
  directory only** (no upward walk, no recursion). Discovered paths are printed
  on stderr as `discovered manifests: …` before solving or checking.
- **Give one or more paths** — discovery is **skipped entirely**; only those
  manifests are used.

## Lock — `pyforge mason environment lock`

Write a new lockfile by delegating resolution to the **conda-lock** engine.
Mason does **not** implement its own resolution rules — platform lists,
solver behavior, and lockfile format are the engine's alone.

```bash
pyforge mason environment lock --output conda-lock.yml
pyforge mason environment lock pyproject.toml --output locks/py314.lock \
  --platform linux-64,osx-arm64
```

Required:

- **`--output` / `-o PATH`** — where to write the lockfile.

Optional:

- **`--platform PLATFORMS`** — comma-separated platforms (e.g.
  `linux-64,osx-arm64`). Empty tokens are dropped. **When omitted**, Mason
  passes no platform list and **conda-lock applies its own default**; the
  command output and JSON envelope include the engine's **`engine_name`**
  and **`engine_version`**, and the lockfile carries provenance the format
  allows (FR-29).

- **`--format json`** — single JSON document on stdout (see pyforge-mason).

Non-zero **conda-lock** exit codes surface as a failed process exit; the
envelope still reports `status: ok` with the return code in the payload (AD-4).

## Check — `pyforge mason environment check`

Verify an **existing** lockfile against the manifests; **nothing is written**
to the lockfile path.

```bash
pyforge mason environment check --lockfile conda-lock.yml
pyforge mason environment check --lockfile locks/py314.lock \
  --platform linux-64,osx-arm64 --format json
```

Required:

- **`--lockfile` / `-l PATH`** — existing lockfile to verify (not an output path).

Manifest rules match **lock** above (discovery vs explicit paths).

Optional **`--platform`** — use the **same** platforms the lock was created with;
omitting it delegates to conda-lock's default, which can report a narrower
lockfile as stale.

Exit code is **non-zero** when the lockfile is **stale** or when conda-lock
failed during the check. Use **`--format json`** in CI for a machine-readable
`stale` field plus engine provenance.

## Recipe work stays in CFE

If dependency work turns into **recipe** authoring, validation, or submission,
read
[conda-forge-expert](../conda-forge-expert/SKILL.md)
(`.claude/skills/conda-forge-expert/SKILL.md`) — do not copy CFE gotchas here.

## What this skill is not

- Not SKF-compiled — do not nest under `pyforge-mason/`.
- Not a substitute for **conda-forge-expert** on recipe questions.
- Does not state Mason-side resolution policy beyond "the engine decides."
- When in doubt, read
  `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py` and
  `environment.py`.
