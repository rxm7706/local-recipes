---
spec: pixi-container-image
status: ready
owner-dream: docs/dreams/pixi-container-image.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/pixi-container-image.md
---

# SPEC — One pixi base-layer discipline across the repo's Containerfiles

## Why
The Dream's premise went stale in the good direction: the repo now ships
THREE Containerfiles (root, `src/platform/`, `compose/dbgpt/`) — the
trigger fired. All three already use `ghcr.io/prefix-dev/pixi` base tags
(pixi-version registry sites 14–16), which IS the shared-base-layer pattern;
what remains is making the discipline uniform and auditable.

## Capabilities
- **CAP-1 — the standardized discipline.** One documented base-layer
  convention across all three Containerfiles: registry-pinned base tag
  (already enforced), multi-stage pixi-materialization shape, and the
  credential rule the Dream names as the piece worth retaining regardless —
  build-time secrets ONLY via `--mount=type=secret`, never a layer or ENV —
  verified by a test greping all Containerfiles for the anti-patterns.
  *Success:* the convention doc exists; the guard test reds on a planted
  ENV-credential or unpinned base.

## Constraints
No new base image is BUILT (the official pixi image serves); the pixi
version registry stays the tag authority; a shipped repo-own base image
remains out of scope until ≥2 Containerfiles diverge for real reasons.

## Non-goals
Multi-arch; publishing a base image; touching recipe-build docker isolation
(a different concern the Dream explicitly separates).

## Success signal
Three Containerfiles, one convention, one guard test — and the Dream's
stale premise corrected in place.
