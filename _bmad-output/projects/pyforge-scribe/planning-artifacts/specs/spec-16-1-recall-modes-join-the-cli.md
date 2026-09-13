---
title: 'Recall modes join the CLI'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Add `--mode planning|memory|code` as exclusive kind bags. Default
recall stays the CAP-4 bag. Internal lexical/semantic `mode=` is
unchanged.

## Boundaries & Constraints

**Always:** exclusive with `--kind`; unknown mode exits 2.

**Never:** portal argv change; semantic as default.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 16.1 / `spec-scribe-recall-modes` CAP-1.
- **2026-09-13:** implemented — `--mode` bags; exclusive with `--kind`.
