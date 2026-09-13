---
title: 'Portal and Marshal inherit default recall'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Lock portal and Marshal recall argv to inherit CAP-4. Add a Cursor rule
that points at the AGENTS session path.

## Boundaries & Constraints

**Always:** no `--kind` on those argv builders.

**Never:** portal redesign; `pyforge.scribe` import from django-scribe.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — argv locks + `.cursor/rules/scribe-recall.mdc`.
