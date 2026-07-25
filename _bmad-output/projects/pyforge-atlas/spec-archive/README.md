# pyforge-atlas — spec archive

A single-location collection of **every BMAD spec used to build pyforge-atlas**,
plus retro-reconstructions for the stories that were never written as files.
Assembled 2026-07-25 from real sources only.

## Contents

| File | What it is | Sourcing |
|---|---|---|
| `ATLAS-BMAD-SPECS-CONSOLIDATED.md` | Every spec for the whole effort in one file: Tier-1 intake spec + all Tier-2 planning specs (PRD, architecture spine, epics, readiness gate, …) + the Tier-3 story files that exist (waves 0/A/B1–B8) + appendix. | Verbatim concatenation of the tracked planning artifacts + local story files. |
| `ATLAS-B9-H4-EPICS-DEFINITIONS.md` | The 20 B9→H4 stories, verbatim `epics.md` definition + `deferred-work.md` entries each. | Verbatim from planning artifacts. |
| `ATLAS-B9-H4-SPECS-WITH-PR-EVIDENCE.md` | Same 20 stories + implementation evidence: merged PR #, real commit subjects/bodies. | epics.md + git commits. |
| `ATLAS_SPECS_REMAINING_20.md` | The 20 B9→H4 **retro-reconstructed story files**, wrapped `===BEGIN <ID>===` / `===END <ID>===`. | Retro-reconstruction (see caveat). |
| `retro-story-files/*.md` | The same 20 retro story files, one per file, in BMAD story-file template format. | Retro-reconstruction. |
| `pyforge-atlas-effort-run-log.md` | Reconstructed narrative of how the effort actually ran (not a bmad-loop journal). | Reconstructed from git history + transcripts. |
| `_build-scripts/*.py` | The assembler/extractor/generator scripts that produced the above, for reproducibility. | — |

## ⚠️ Critical honesty caveats

1. **The B9→H4 story files are RETRO-RECONSTRUCTED, not recovered originals.**
   Waves B9→H4 shipped through the **in-session agent loop**, which never emitted
   story files. `bmad-create-story` was only ever run for waves 0/A/B1–B8.
   Confirmed exhaustively: no such files exist in `implementation-artifacts/`, in
   `.bmad-loop/runs/` (which never existed), in any git worktree, in git history,
   or anywhere on disk. The `ATLAS_SPECS_REMAINING_20.md` / `retro-story-files/`
   content is reconstructed **only from real evidence** — verbatim `epics.md`,
   `deferred-work.md`, and the actual merged commits/diffs — and every such file
   is marked `Status: done (retro-reconstructed …)` with a banner. **Nothing was
   invented.** These are honest reconstructions, not the original dev-run outputs
   (which never existed).

2. **Tier boundary:** `implementation-artifacts/` is gitignored Tier-3 by repo
   convention. `ATLAS-BMAD-SPECS-CONSOLIDATED.md` (and the retro files) inline
   Tier-3 content into this tracked archive. This is a deliberate, user-requested
   consolidation — it does not live under `implementation-artifacts/`, so it does
   not trip the `bmad-drift-check` HARD `tracked-impl-artifact` finding, but be
   aware it duplicates local-only content into git.

3. **Cross-session:** the tracked Tier-2 planning artifacts already capture
   cross-session committed work. Anything authored in another session and never
   committed is not reachable and is not included here.

## Canonical sources (edit these, not the archive)

- Intake spec: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`
- Planning artifacts: `_bmad-output/projects/pyforge-atlas/planning-artifacts/`
- Story files (0/A/B1–B8): `_bmad-output/projects/pyforge-atlas/implementation-artifacts/`

This archive is a derived snapshot; regenerate with the `_build-scripts/`.
