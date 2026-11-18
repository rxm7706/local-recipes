---
sources:
  - docs/governance/preserve-purge-list.json
  - docs/governance/rulesets/protected-refs.json
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - scripts/legacy_preserve_promote.py
verified: 2026-11-18
---

# Purge preserved refs

Operator-runbook for removing `preserve/` or `archive/` tags from `origin` after a committed manifest change. A dispatched agent session never performs these steps.

:::caution[Not yet exercised]
Nothing in this repository shows this runbook run end to end. `docs/governance/preserve-purge-list.json` has been empty since it was created, so no purge has gone through it. Treat the first real purge as the proof run, and correct this page from what it shows.
:::

## Normal purge

1. Decide what is purged: the commit shas, the paths, or both. The protected namespaces are the `protected_refs` list in `docs/governance/guild-roster.json`.
2. Add each sha to `commit_shas` and each path to `paths` in `docs/governance/preserve-purge-list.json`, and land that change through its own PR before you delete anything. This file is the record the tooling reads: once it is on `main`, the content gate refuses any tag that descends from a listed sha or touches a listed path, so the purged content cannot be pushed back. A change to the list is the operator's decision; an agent asks first. You may also capture the decision in team memory (`pixi run -e pyforge-guild scribe capture --type project --text "…"`), but no tool reads that entry.
3. Delete tags on `origin` with an explicit refspec per tag (never `git push --tags`).
4. Request a GitHub cache purge when purged blobs must leave the public cache.

## Secret-incident fast path

When a preserve tag on `origin` must come down immediately:

1. Temporarily adjust the repository ruleset that blocks tag deletion (operator only). Its tracked copy is `docs/governance/rulesets/protected-refs.json`.
2. Delete the tag with one explicit refspec.
3. File the GitHub cache purge request.
4. Restore the ruleset and append the incident to team memory via `scribe capture`.

The content gate (`marshal preserve push`, or `scripts/legacy_preserve_promote.py --push-reviewed` for reviewed legacy twins) judges only the objects a push would send — not blobs already reachable on `origin` through `refs/heads/*` or `refs/tags/*`. It refuses tags that descend from purge-listed shas, touch purge-listed paths, fail the secret scan, exceed the per-file size cap (5 MB by default), or when `origin` cannot be read (`unreadable-remote`). A purge list that is missing or cannot be parsed also keeps the tag local (`purge-list-unreadable`). `marshal preserve` sits behind the flag `pyforge.marshal.preserve_refs`, which is off by default.
