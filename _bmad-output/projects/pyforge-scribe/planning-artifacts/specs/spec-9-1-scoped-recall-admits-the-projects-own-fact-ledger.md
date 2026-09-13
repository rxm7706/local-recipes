---
title: 'Scoped recall admits the project''s own fact ledger'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

`--scope <slug>` admits exactly one extra citation shape:
`presentations/<slug>/facts.yaml`. Marshal retrieve does not change argv.

## Boundaries & Constraints

**Always:** identity slug; planning-tree prefix still required for everything else.

**Never:** all of `presentations/`; nested `facts.yaml`; a `--facts` flag; alias table.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `_citation_in_scope` admits
  `presentations/<scope>/facts.yaml` only. Marshal `--scope` argv unchanged.
