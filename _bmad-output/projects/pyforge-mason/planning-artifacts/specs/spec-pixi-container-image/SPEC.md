---
spec: pixi-container-image
status: shipped
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
  convention across **every tracked Containerfile — four today, enumerated by
  GLOB, never a hard-coded list** (restated 2026-09-09): registry-pinned base
  tag (already enforced), multi-stage pixi-materialization shape, and the
  credential rule the Dream names as the piece worth retaining regardless —
  build-time secrets ONLY via `--mount=type=secret`, never a layer or ENV —
  verified by a test greping all Containerfiles for the anti-patterns.
  *Success:* the convention doc exists; the guard test reds on a planted
  ENV-credential or unpinned base, **and the file list it checks is derived
  from the tracked tree, so a newly added Containerfile is governed on arrival.**
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD df260ed9ea: `docs/reference/container-base-layer-convention.md` exists (5830 bytes); `pixi run -e pyforge-ci python -m pytest tests/packaging/test_containerfile_base_layer_convention.py -q` — 25/25 passing, including `test_discover_containerfiles_finds_all_four` (asserts `>= 4`, non-vacuous) and `test_discovery_is_not_vacuous`; all 4 tracked Containerfiles confirmed present on disk (`./Containerfile`, `src/platform/Containerfile`, `src/platform/compose/mcp-host/Containerfile`, `src/platform/compose/dbgpt/Containerfile`); file-list discovery reads `git ls-files` for `Containerfile*`, not a hard-coded tuple (Story 16.4's residual, confirmed resolved).

## Constraints
No new base image is BUILT (the official pixi image serves); the pixi
version registry stays the tag authority; a shipped repo-own base image
remains out of scope until ≥2 Containerfiles diverge for real reasons —
**four now exist and none diverges** (2026-09-09), so the exclusion stands.

**The Containerfile set is enumerated by glob, never by a hard-coded list.**
The convention guard (`tests/packaging/test_containerfile_base_layer_convention.py`)
derives its file list from git-tracked ``Containerfile*`` paths (Story 16.4), so
all four — including `src/platform/compose/mcp-host/Containerfile`
(`spec-mcp-era-isolation` slice 1) — are swept by the `FROM` and `ENV` checks.

## Non-goals
Multi-arch; publishing a base image; touching recipe-build docker isolation
(a different concern the Dream explicitly separates).

## Success signal
Every tracked Containerfile, one convention, one guard test — and the Dream's
stale premise corrected in place.

**Shipped (2026-09-09).** CAP-1 is live: the base-layer convention is documented
and guarded by `tests/packaging/test_containerfile_base_layer_convention.py`, and
every shipped Containerfile follows it (registry-pinned base tag, multi-stage pixi
materialization, no ENV-declared credential).

**One residual, vesselled: mason Story 16.4 — "the Containerfile convention guard
derives its file list."** Replace the hard-coded `CONTAINERFILES` tuple (three
literals at `test_containerfile_base_layer_convention.py:50-52`) with a derivation
over the tracked tree; appending a fourth literal returns the same defect one file
later. Its acceptance criteria require proof the derivation actually FINDS the files
(a count or explicit membership assertion, so an empty glob cannot pass vacuously)
plus a planted-violation check against the previously-omitted file. **Homed on Epic
16, not Epic 8** — this Spec's subject epic is Epic 8 (Story 8.1), but `epic-8` reads
`done` in the tracked ledger and hanging a backlog story off it would flip that
rollup and misreport a completed epic fleet-wide. Recorded so the subject-vs-home
split is not later read as a mis-file.
