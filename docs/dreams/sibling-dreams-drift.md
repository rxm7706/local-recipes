---
title: Sibling dreams directories don't drift silently
type: dream
owner: doctor
status: specified   # 2026-08-22 — spec-sibling-dreams-drift, decomposed into the station backlog same day
---

# Sibling dreams directories don't drift silently

## The Dream

A sibling PyForge instantiation exists (OpenTeams-WFT-CDO
mgmt-wf-python-modernization) sharing this repo's Dream-first convention:
13 of its 15 dreams have local counterparts (8 byte-identical filenames),
independently evolving, with station ownership already diverging (their
deck work = scribe; ours = herald). Nothing detects the drift. The dream:
an ambient doctor finding — a periodic shared-title diff naming dreams that
exist in both trees with diverging content/status/owner, warn-only,
fail-open when the sibling is unreachable.

## Constraints / Non-goals

Read-only, never a sync engine (reconciliation is human, per-dream);
the sibling is private — access via the operator's token, degrade silently
without it; no content is copied across (their prose is unlicensed).
Kin: `bmad-method-version-drift` (the ambient-signal shape),
the 2026-08-22 intake report (the demonstrated drift).

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-sibling-dreams-drift` derived under pyforge-doctor and decomposed into the station backlog
  the same day (`a20192dd84`). Spec status `ready`.
