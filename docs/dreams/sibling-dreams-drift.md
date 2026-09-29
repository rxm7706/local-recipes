---
title: Sibling dreams directories don't drift silently
type: dream
owner: doctor
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-doctor]]** on 2026-09-17 (one-chain-per-station doctor fold).

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
- **2026-09-09** — Still `specified`, and deliberately not `realized`. Story 16.1 is `done`,
  but the capability it shipped cannot fire against the live estate: the detector joins the
  two trees on frontmatter `title:` (`sibling_dreams.py:118`, `:155`, `:189`), and measured
  live this day with the operator's token the trees share **0 titles and 8 filenames** — the
  overlap this Dream itself named ("8 byte-identical filenames", above). The three sampled
  shared filenames all carry real divergence (`developer-machine-bootstrap.md`: local
  `specified` vs sibling `dreamt`), so the signal exists and the key does not reach it.
  `spec-sibling-dreams-drift` moves `ready` → `in-progress` with the re-key on filename
  (title demoted to a reported axis) and an explicit `sibling-dreams-unreachable` finding in
  place of today's silent `return ()` — so "could not look" stops rendering as "looked and
  agreed". Recorded in the fleet-readiness decision batch of 2026-09-09 (row doctor-B4).
