---
title: 'In-flight story specs join the compile'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Compile `spec-<n>-<m>-*.md` as `doc` when the project's sprint ledger
marks that story in-flight. Frontmatter is not the filter.

## Boundaries & Constraints

**Always:** ledger statuses `ready-for-dev` | `in-progress` | `review`.

**Never:** `done`, `backlog`, folder `SPEC.md` on this surface, frontmatter oracle.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — ledger filter on `spec-<n>-<m>-*.md`.
