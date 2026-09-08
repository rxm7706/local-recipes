---
title: Evergreen Unifying Strategy — ready to implement Epic 34
date: 2026-08-26
status: applied
---

# Sprint change — evergreen chain ready

## Issue

The Dream was rewritten as evergreen (query plane, Kedro/Vizro option, lasuite retracted). SPEC/PRD/epics already had CAP-19 / Epic 34, but the ledger had no `34.*` rows, Scribe still said `GraphStore`, and `django-lasuite` still appeared as host OIDC in the spine.

## Approach

Correct-course in place. Do not mint a sibling spec. Re-derive living contract from the Dream + memlog. First dispatch **34.1**.

## Applied

- SPEC `in-progress` → **`ready`**. Constraints: lasuite never on host; Kedro optional; Vizro Lane 3; store port not GraphStore class.
- PRD What Comes Next points at `spec-34-1-read-only-live-attach.md`.
- Epic 34 copy aligned. Story spec tracked.
- Spine canopy:AD-22 + stack table: lasuite not a Canopy dep.
- `stack.md` already retracted lasuite (prior pass).
- Readiness: `implementation-readiness-report-2026-08-26.md` — **CONCERNS — proceed**.
- Ledger: generate + `sprint-ledger-sync` for `34.1`–`34.5`.

## Handoff

Next session: `bmad-build` on `spec-34-1-read-only-live-attach.md` only. Do not re-dispatch 18–32.
