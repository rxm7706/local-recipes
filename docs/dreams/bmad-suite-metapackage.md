---
title: One conda metapackage installs the whole SelfExplainML bmad-suite at latest
type: dream
owner: steward
status: dreamt
parent: docs/dreams/bmad-suite-channel-product.md
---

# The bmad-suite metapackage

## The Dream

An operator who wants **every** SelfExplainML channel product — all 13 packages from
`install-matrix.md` — should be able to run one install:

```bash
pixi add bmad-suite   # or: conda install -c SelfExplainML bmad-suite
```

and get a coherent, version-locked bundle whose own version records **when the suite was
refreshed**, with each member pinned to the **latest upstream release** appropriate to that
member's registry class (GitHub tag, npm, PyPI — never a stale npm stub for GitHub-canonical
packages).

Today the channel sells 13 individual recipes; `pixi.toml` carries 11+ separate pins; drift
between members is invisible until a human compares the channel listing to GitHub. The
metapackage is the **product boundary** — the thing that says "this fleet snapshot is
2026.9.1" while member recipes continue to bump independently.

## Grounding

- **Channel catalog (2026-09-01):** 13 packages on SelfExplainML — `bmad-method` plus 12
  suite members including `mybmad-dashboard` (bmad-ui only today).
- **Doctor gap (same session):** ambient drift watches pixi `bmad-*` keys and npm-first;
  misses `mybmad-dashboard` and under-reports GitHub-primary packages (builder, CIS).
- **Existing machinery:** per-member `recipes/<name>/recipe.yaml` with
  `cfe-upstream-registry` + `cfe-upstream-name`; steward `suite pipeline-truth`; CFE autotick
  per recipe — no batch "refresh the whole suite" artifact.

## What it looks like when real

- `recipes/bmad-suite/recipe.yaml` — **noarch metapackage** (`requirements.run` lists every
  member at `>=` the resolved upstream version; no sources of its own).
- `recipes/bmad-suite/suite-members.yaml` — canonical 13-name manifest (single source for
  doctor Story 19.1 watched set and metapackage generation).
- `pixi run -e local-recipes generate-bmad-suite` (or steward duty) — resolves upstream latest
  per member via registry class, writes/updates the metapackage pin block and CalVer
  `context.version`, never hand-edits 13 lines.
- Channel publishes `bmad-suite` alongside members; optional `pixi.toml` feature
  `bmad-suite-full` replaces the long pin block for operators who want the bundle.

## Non-goals

- Replacing individual member recipes (they stay the unit of autotick/build/publish).
- conda-forge submission of the metapackage (SelfExplainML-only, like the other 12).
- Wiring modules (`steward provision --module`) — the metapackage is install-only; provisioning
  stays CAP-3.

## Success signal

`conda install -c SelfExplainML bmad-suite` pulls all 13 members at versions that match
`steward suite pipeline-truth --json` upstream-latest column; doctor's suite drift is quiet
after a metapackage refresh PR merges; the manifest and metapackage version bump in one
reviewable commit.
