# pyforge-warden — story specs (tracked, durable)

**Why this directory exists.** Story specs are the per-story intent contract in a
spec-driven build. They were originally written to Tier-3 `implementation-artifacts/`
(gitignored) and were **destroyed on bmad-loop worktree teardown** — by 2026-07-25,
of 31 story specs only 10 survived intact, 8 were 0-byte husks, and 13 were gone
entirely (Epics 3 & 4 lost their whole spec set). For a spec-driven autonomous product
the spec *is* the contract, so specs must be **durable and in every clone**. This
directory (`planning-artifacts/specs/`, Tier-2, **git-tracked**) is that durable home.

## Convention (going forward)

**Story specs are tracked here.** After a bmad-loop story merges, promote its spec from
the run's `implementation-artifacts/` into this directory and commit it. The gitignored
`implementation-artifacts/` remains the runtime scratch location; the tracked copy here
is the source of record. This closes the recurring paper-trail loss (the long-standing
`action_items` entry).

## Provenance of the recovered set (2026-07-25)

Every story 1.1–6.10 now has a spec here. Fidelity varies by how it was recovered — each
file states its own provenance in its header:

| Provenance | Count | What it is |
|---|---|---|
| **original (survived intact)** | 10 | the real spec, never lost (1-5, 1-6, 2-6, 5-1, 5-2, 6-3, 6-5, 6-6, 6-7, 6-8) |
| **original (recovered from a run worktree)** | 8 | recovered from a surviving bmad-loop worktree snapshot; header `<!-- RECOVERED … run worktree -->` (1-1, 1-2, 1-3, 1-4, 1-7, 2-2, 6-2, 6-10) |
| **original (recovered from session transcript)** | 13 | recovered verbatim from the `Write`/`Edit` tool-calls in the **Claude Code session transcripts** (`~/.claude/projects/*.jsonl`); header `<!-- RECOVERED … session transcript -->` (1-8, 1-9, 2-1, 2-3, 2-4, 2-5, 3-1, 3-2, 3-3, 4-1, 6-1, 6-4, 6-9) |

**All 31 warden story specs are the REAL originals — zero regenerations remain.** The
transcript recovery (2026-07-25) closed the last gap: the bmad-loop dev sessions' `Write`
calls that created each spec survive in the local session transcripts, so the original
intent-contracts came back verbatim. Of the 13 transcript-recovered, **5 include the full
dev/review triage log** (their final full-rewrite Write was captured); the other 8 are the
dev's spec draft (intent + boundaries + I/O matrix + code map) — their late review-triage-log
was likely appended by a later `Edit` and would need a Write+Edit replay to reassemble.

## Recovery sources (in order of fidelity)

1. **Session transcripts** (`~/.claude/projects/**/*.jsonl`) — the richest source: they hold the
   `Write`/`Edit` tool-calls that created every spec, so the original content (often incl. the
   dev/review narrative) is recoverable verbatim. Scan each `.jsonl` for `tool_use` blocks named
   `Write`/`Edit` whose `input.file_path` matches the spec; take the largest `content` (or replay
   Write+Edits in timestamp order for the exact final state). This is how the 13 were recovered.
2. **Run worktree snapshots** — `**/.bmad-loop/runs/*/worktrees/*/**/implementation-artifacts/spec-<X-Y>-*.md`; largest surviving copy is richest.
3. **`epics.md` regeneration** — last resort: per-story Intent + ACs only (the contract, not the narrative).

> Note (atlas): the same transcript recovery was attempted for pyforge-atlas but its dev-session
> transcripts are **not** in the local `~/.claude/projects/` store, so atlas kept only 2 originals
> + 30 `epics.md` contract-specs. See that project's `specs/README.md`.
