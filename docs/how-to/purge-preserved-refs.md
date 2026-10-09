# Purge preserved refs

Operator-runbook for removing `preserve/` or `archive/` tags from `origin` after a committed manifest change. A dispatched agent session never performs these steps.

## Normal purge

1. Add rows to `docs/governance/preserve-purge-list.json` (`commit_shas` and/or `paths`) in a dedicated PR with operator approval.
2. Record the purge intent in the steward/marshal protected-ref change log (see `docs/governance/guild-roster.json`).
3. Delete tags on `origin` with an explicit refspec per tag (never `git push --tags`).
4. Request a GitHub cache purge when purged blobs must leave the public cache.

## Secret-incident fast path

When a preserve tag on `origin` must come down immediately:

1. Temporarily adjust the repository ruleset that blocks tag deletion (operator only).
2. Delete the tag with one explicit refspec.
3. File the GitHub cache purge request.
4. Restore the ruleset and append the incident to team memory via `scribe capture`.

The content gate (`marshal preserve push`) refuses new tags that descend from purge-listed shas, carry purge-listed paths, fail the secret scan, or exceed the per-file size cap.
