---
spec: sibling-dreams-drift
status: ready
owner-dream: docs/dreams/sibling-dreams-drift.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/sibling-dreams-drift.md
open_questions: []
---

# SPEC — Sibling dreams directories don't drift silently

## Why
A sibling PyForge instantiation (OpenTeams mgmt-wf) shares this repo's
Dream convention — 13/15 dreams have local counterparts, independently
evolving, owners already diverging. Nothing detects it.

## Capabilities
- **CAP-1 — the drift check.** A doctor source diffs shared dream titles
  (local docs/dreams vs the sibling's, via the operator's token): diverging
  status/owner/content-hash per shared title, warn-only, fail-open when
  unreachable; surfaces in the doctor report + fleet-picture ATTENTION.
  *Success:* a fixture of the demonstrated 2026-08-22 state names the
  divergences; offline yields no finding and no error.

## Constraints
Read-only, never a sync engine (reconciliation is human, per-dream); no
sibling content stored beyond titles/hashes (their prose is unlicensed);
degrades silently without the token.

## Non-goals
Bidirectional sync; importing dreams; watching any repo beyond the one
named sibling (a registry can come later if a third instantiation appears).

## Success signal
The ATTENTION block ambiently names sibling-diverged dreams the way it names
version drift — and goes quiet when the trees agree.
