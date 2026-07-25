# pyforge-atlas — story specs (tracked, durable)

Same spec-durability remediation as pyforge-warden (see the repo-wide convention in
`CLAUDE.md` § *Spec-driven layout* → "Story specs are durable (tracked), NOT Tier-3").
Story specs are the per-story intent contract; they must survive worktree teardown and
live in every clone. This directory (`planning-artifacts/specs/`, Tier-2, **git-tracked**)
is that durable home. The pre-existing `spec-pyforge-atlas/` subdir is the Dream-level
bmad-spec **kernel** (SPEC.md + memlog); the `spec-<story>.md` files here are the per-story
specs.

## Provenance of the recovered set (2026-07-25)

Atlas was **more degraded than warden**: by 2026-07-25 only **2 of 32 story specs survived
intact** (0.1, B1); the rest were 0-byte husks or gone entirely, and — unlike warden — **no
run-worktree snapshots survived** to recover originals from. The compounding cause was the
2026-07-19 truncation incident (reconciled 2026-07-23) on top of the Tier-3 gitignored
paper-trail gap. What saved the contract: the tracked `epics.md` (72 KB) retained every
story's Intent + Acceptance Criteria.

| Provenance | Count | What it is |
|---|---|---|
| **original (survived intact)** | 2 | the real spec (0.1 generate-legacy-skill, B1 conda-backbone-nodes); header carries a `<!-- RECOVERED … -->` note |
| **regenerated contract-spec** | 30 | authoritative Intent + Acceptance Criteria lifted **verbatim** from `epics.md` + a realized-in pointer; original dev-notes / review-triage-log unrecoverable; marked `status: regenerated` |

**The contract is intact for all 32 stories** (Wave 0, A–H). Fidelity is honestly thinner
than warden's set because atlas kept fewer originals — the regenerated specs carry the same
binding ACs the migration was built against (from `epics.md`), but not the per-story
implementation narrative. Ground truth for what shipped is the merged PRs **#58–#105**; the
migration is COMPLETE (32/32, shipped 2026-07-18).

## Regenerating / re-recovering

- **Regen from planning:** `epics.md` → per-story `### Story <ID> (<epic.story>): <title>` section (Intent + ACs).
- **Recover an original:** search `**/.bmad-loop/runs/*/worktrees/*/**/pyforge-atlas/implementation-artifacts/*.md` (none survived as of 2026-07-25).
