# pyforge-atlas — story specs (tracked, durable)

Same spec-durability remediation as pyforge-warden (see the repo-wide convention in
`CLAUDE.md` § *Spec-driven layout* → "Story specs are durable (tracked), NOT Tier-3").
Story specs are the per-story intent contract; they must survive worktree teardown and
live in every clone. This directory (`planning-artifacts/specs/`, Tier-2, **git-tracked**)
is that durable home. The pre-existing `spec-pyforge-atlas/` subdir is the Dream-level
**Spec** (SPEC.md + memlog); the `spec-<story>.md` files here are the per-story
specs.

## Provenance of the set (final, 2026-07-25)

The 32 tracked specs fall into two classes — and the split is not "how much survived,"
it is **how each story was originally built**:

| Class | Count | Stories | What the tracked spec is |
|---|---|---|---|
| **Full original dev spec** | 12 | Waves 0 / A / B1–B8 (0.1, A1–A3, B1–B8) | The REAL story file, incl. `## Dev Notes` / `## Dev Agent Record` / `## Review Triage Log`. These waves were built with **`bmad-create-story`**, so per-story files existed; recovered verbatim from the operator's consolidated dump. Header carries a `<!-- RECOVERED … -->` note. |
| **Contract + reconstructed narrative** | 20 | B9, B10, C1–C2, D1–D3, E1–E2, F1–F4, G1–G3, H1–H4 | **No original ever existed.** These waves ran through the migration's **in-session agent loop**, which never emitted a story file. The tracked spec = Intent + ACs **verbatim from `epics.md`** + a dev narrative reconstructed from the merged record (PR body + `main` commits). |

### The 20 were never lost — they never existed as files

Earlier notes in this repo framed the 20 as "lost to the 2026-07-19 truncation." **That was
wrong**, and is corrected here. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`, branch
`claude/cfe-atlas-kedro-analysis-vgrol9`, which built all 32 stories in PRs #70–#102) confirmed
exhaustively: `bmad-create-story` was run **only** for waves 0/A/B1–B8; waves B9→H4 were
implemented directly by an in-session loop (draft → 2 in-loop reviews → 1 independent fresh-eyes
review → verify → PR → self-merge) that wrote no per-story spec. No such file exists in
`implementation-artifacts/`, `.bmad-loop/runs/` (which never existed for atlas), any git worktree,
git history, or on disk. **There is nothing to recover — only to honestly reconstruct.**

### Two independent reconstructions of the 20 (both evidence-based; nothing invented)

1. **In each tracked spec** (this dir) — the `## Dev narrative — recovered from the merged record`
   section: the story's PR body (#82–#102, the real dev summary) + its `main` commit log (the
   review-fix commits are the review-triage trail for B10 / E1 / F3 / G2).
2. **`../../spec-archive/`** (the operator's web-session archive) — the richer BMAD-story-format
   reconstruction: `retro-story-files/<epic>-<story>-<id>.md` (Story / AC / Tasks / Dev Notes /
   Dev Agent Record / File List / Review Triage Log, built from the agent-loop transcripts), plus
   `ATLAS-B9-H4-SPECS-WITH-PR-EVIDENCE.md`, `ATLAS-BMAD-SPECS-CONSOLIDATED.md` (the dump the 12 were
   recovered from), the effort run-log, and the reproducible build scripts. Each spec here
   cross-links its retro file. See the archive's own `README.md` for its honesty caveats.

## How each class was recovered

- **The 12 full originals** — from `ATLAS-BMAD-SPECS-CONSOLIDATED.md` (operator-provided, session
  `01FYyQvBJuXwySiaMUUYCqBZ`; tracked in `../../spec-archive/`). The only source that preserved
  them: atlas dev sessions ran on `claude.ai/code` (web), so their transcripts are not in the local
  `~/.claude/projects/` store, and no run-worktree snapshots or git history held them either
  (confirmed by a full scan of 448 local transcripts, all refs, reflog, 123 dangling objects, and
  the parked fork). The local `claude --from-pr` resume path was also tried and **does not** hydrate
  a web session's transcript (it spawns fresh local sessions) — retrieval of anything web-only is
  web-UI-only.
- **The 20 reconstructions** — from `epics.md` (Intent + ACs) + the merged PRs/commits, cross-checked
  against the web-session archive. Verbatim originals do not exist to recover.

Migration is COMPLETE (32/32, PRs #58–#105 merged to `main`).
