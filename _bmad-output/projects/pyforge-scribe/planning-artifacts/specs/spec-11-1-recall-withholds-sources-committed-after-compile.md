---
title: 'Recall withholds sources committed after compile'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Persist `compiled_at` on the flat-file store. Recall treats a post-compile
source commit as stale without rebuilding the graph.

## Boundaries & Constraints

**Always:** selection-time git compare; commit/transcript exempt.

**Never:** Protocol change; recompile-on-recall; PG/plane schema this story.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `compiled_at` on the flat-file store;
  recall-time `source_committed_after` at selection.
