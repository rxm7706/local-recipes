---
doc_type: retrospective
project: pyforge-atlas
title: Station retro — the turn-on window (2026-08-26 → 2026-09-14)
date: 2026-09-14
updated: "2026-09-14"
scope: everything landed in src/shared/packages/pyforge-atlas since the last retro
  (retro-pyforge-atlas-2026-08-26) — Epics 20-24 closing out, Epic 25 opening, and
  the fleet-consistency work that crossed this station
basis: "git log --since=2026-08-26 -- src/shared/packages/pyforge-atlas;
  planning-artifacts/sprint-status-ledger.yaml (tracked twin, read-only);
  planning-artifacts/epics.md (Epics 20-25);
  planning-artifacts/specs/spec-pyforge-atlas/{SPEC.md,.memlog.md};
  live source reads: src/pyforge/atlas/mcp/parity.py, tools/live_artifactory_transport.py,
  src/pyforge/atlas/dashboard/app.py, pyforge-core src/pyforge/core/dispatch.py:28-30;
  _bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md"
trigger: "chain-currency sweep — chain-audit-checkpoint-staleness fired code (2026-09-10)
  newer than retro (2026-08-26) on the pyforge-atlas chain"
---

# Retro — pyforge-atlas, 2026-08-26 → 2026-09-14

The 2026-08-26 retro closed the post-migration growth window and named nine
carried open items. This one closes a different kind of window: **the station
stopped adding capability and started turning on what it had already built.**
Epics 20–24 all reached `done`; Epic 25 — the realization-gate effect epic — is
the only one still open, and the single story still outstanding in it is the one
that needs a human with credentials.

## What shipped (evidence-based, from the ledger and the merge log)

- **Epic 20 — the query plane meets the query surfaces: `done`, 5/5.** One boot
  script raises both plane faces (20.1), face parity became part of done (20.2),
  the dashboard stores derive from a named `semantic_packages` pipeline rather
  than ad-hoc reads (20.3, `dc1d7bc1d6`), the CIS two-spine specs exist (20.4),
  and the remaining nineteen Vizro pages landed (20.5). `PAGE_INVENTORY` in
  `dashboard/app.py` now holds **34** `PageDef` entries — verified live this
  pass, matching Story 25.1's stated target.
- **Epic 21 — Kedro catalog expansion: `done`, 10/10.** The data plane became
  self-contained: data defaults relocated plus `pyforge-atlas-bootstrap`
  (`c4aeaace30`), `cf_atlas.db` seeds removed from production datasets
  (`f20492af73`), Tier 0/1/2 catalog sources (`ee4d43222f`, `d13fb96d4a`), the
  identity join and export Parquet, the quartet thin-out, and an end-to-end
  verification gate closing the epic (`40d75846de`).
- **Epics 22, 23, 24: `done`.** Vizro parity with the identity canvases (6/6,
  including the canvas-deprecation switch), the complete inventory export with
  zero deferred (9/9), and the `mcp-builder`-wielded MCP face (1/1).
- **Epic 25 — turn on what is built: 3 of 4.** Story 25.1 **retired the second
  Lane-3 runtime**: `src/pyforge/atlas/views/` is gone (only a stale
  `__pycache__` remains on disk) and a repo-wide `atlas.views` grep returns
  nothing — verified live this pass. Story 25.3 gave atlas its own **CLI⇄tool
  parity gate**: `src/pyforge/atlas/mcp/parity.py` plus
  `tests/meta/test_cli_tool_parity.py` now exist, and `pyforge-core`'s
  `PREPARATORY_UNINTROSPECTABLE["atlas"]` was **re-pointed** at
  `spec-25-3-…` rather than left dangling (`core/dispatch.py:28-30`, read live).
  Story 25.4 landed `tools/live_artifactory_transport.py` (`52ebe88a18`) —
  deliberately outside `src/pyforge/atlas/`, where `test_no_inline_io.py`'s
  `IO_DENYLIST` bans the HTTP imports it needs.
- **Fleet-consistency work that crossed this station.** One test-suite
  vocabulary across all eight stations (`aec4c74f6e`, `9080195184`), the 23
  whole-branch diff-guard bodies consolidated onto `branch_diff_guard`
  (`c9bcbaf516`), the project-context surface following BMAD 6.12 (`c0e4931e0c`
  + its follow-up review fix `cc5a85981f`), and `IdentityGistError` gaining the
  `PyforgeError` base under `pyforge-core`'s sole-ownership rule
  (`58ba8011f4`).
- **Three real defects found and fixed, none of them feature work.** The
  dashboard e2e fixture slept 3s instead of waiting for the port
  (`4de8dc1b62`); identity-catalog parity was order-dependent (`e4a3887030`);
  `vuln_kev_affecting_current` was not scoped to the current version
  (`cc41bc8489`, closing `DW-B2-3`).

## What held

- **The IO-denylist invariant held under pressure and shaped a design.** Story
  25.4 needed a real HTTP transport, and rather than weaken
  `test_no_inline_io.py`'s `IO_DENYLIST`, the factory was placed in `tools/`
  outside the governed package. The gate moved the code; the code did not move
  the gate.
- **Deleting beat deprecating.** 25.1 removed a whole runtime plus its test
  directory plus the assertions that existed only to fence it. The supersession
  was *recorded* in `spec-atlas-query-dashboards` (CAP-1..CAP-4 superseded) as
  well as performed — the pattern the 2026-08-26 retro asked for.
- **"Blocked" stayed honest.** Story 25.2 needs an attended, credentialed
  Artifactory run and is still `blocked` in the ledger. Nothing was fabricated
  to reach a green; 25.4 was minted instead to remove the one *technical*
  obstacle so the remaining obstacle is purely the human event.
- **Cross-station boundaries held in both directions.** 25.3 extended marshal's
  parity *primitive* over atlas without widening its scope to the 46
  conda-forge-expert MCP tools (mason's, per decision batch § 2.3 C10), and
  without minting an atlas story for steward's half.

## What changed course

- **The station's centre of gravity moved from "build" to "have effect."** The
  realization gate's question — *does it have a caller outside its own test
  file?* (steward Story 49.2) — is what produced Epic 25, and it is what
  retired `views/`. Capability that nothing called was treated as debt, not as
  an asset awaiting demand. That is a change from the 2026-08-26 posture, where
  `DW-D2-1`/`DW-D2-2` were parked as "demand-driven."
- **The MCP face acquired a contract gate before it acquired more tools.** 24.1
  adopted `mcp-builder` under a hard boundary (generated tools call
  `pyforge atlas …` verbs only); 25.3 then made drift in either direction a
  test failure. Gate first, surface second.

## Strategy convergence

Nothing in this window contradicts the Unifying Strategy's position that Atlas
is the fleet's single data platform (canopy AD-21, one Kedro home). What this
window adds is that the position is now **enforced rather than asserted**: the
second Lane-3 runtime is deleted rather than deprecated, the query-plane faces
have a parity gate, and the MCP face has a CLI⇄tool parity gate of its own.
The honest residue is unchanged from 2026-08-26 and is *ordering*, not
direction — the estate-facing plane is serving reads while the legacy
orchestrator still serves the factory's daily intelligence reads, and the
retirement chain still has no forcing function.

## Open items (carried, verified against the ledger — not new)

1. **Story 25.2 — the attended, credentialed Artifactory run.** `blocked`.
   Every technical precondition is now met (25.4 shipped the transport); the
   remaining precondition is an operator with credentials and an afternoon.
   `DW-FU-23-5` and `DW-D2-3`'s data-present visual pass both close with it.
2. **Cluster A — the retirement chain** (`DW-B4-3` → `DW-B4-1` → `DW-B4-2`),
   with its integration rider: re-back `conda_forge_server.py`'s atlas tools
   with Kedro/DuckDB reads, or retirement breaks Doctor. **Still no owner** —
   carried unchanged from the 2026-08-26 retro.
3. **Cluster B — Dagster bring-up** (`DW-C1-1`). Unchanged: sensors ship
   `default_status=STOPPED` by design until an attended event.
4. **Phase-P cost-gate routing** (`DW-B2-4`/`DW-B4-4`) — still to land before
   any credentialed Phase-P run.
5. **`DW-H3`/`DW-H1`** — the attended La Suite production bring-up.
6. **`DW-F1-1`** — the F1 cold/warm benchmark.
7. **Scribe dual-write retirement** — still a future decision, not this
   window's.

`DW-B2-3` (item in the 2026-08-26 list's Cluster D) is **closed** this window
by `cc41bc8489`.

## Rule 2 note (CLAUDE.md § BMAD ↔ conda-forge-expert)

This window did no conda-forge recipe work: no file under `recipes/`,
`.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/` or
`.claude/data/conda-forge-expert/` was touched by an atlas story. The
`conda_forge_server.py` reference in open item 2 is a *carried dependency*, not
work done here. Rule 2's CFE-skill retro is therefore not triggered by this
retro.
