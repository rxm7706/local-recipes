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
| **original (recovered from a run worktree)** | 8 | the real spec, recovered from a surviving bmad-loop worktree snapshot; header carries a `<!-- RECOVERED … -->` note (1-1, 1-2, 1-3, 1-4, 1-7, 2-2, 6-2, 6-10) |
| **regenerated contract-spec** | 13 | the authoritative Intent + Acceptance Criteria lifted **verbatim** from the tracked `epics.md` (the source the original was derived from) + a realized-in pointer; the original dev-notes / review-triage-log were not recoverable. Marked `status: regenerated`. |

**The contract is intact for all 31 stories** — the regenerated ones carry the same
Given/When/Then acceptance criteria + FR/NFR mappings the originals were built against
(from `epics.md`); only the per-story implementation narrative is thinner where the
original file was unrecoverable. Behaviour is verified by the current green suite on `main`.

## Regenerating / re-recovering

- **Regen from planning:** `epics.md` → per-story Intent + ACs (see the regen used here).
- **Recover an original:** search `**/.bmad-loop/runs/*/worktrees/*/**/implementation-artifacts/spec-<X-Y>-*.md` across the main repo and any loop home; the largest surviving copy is the richest.
