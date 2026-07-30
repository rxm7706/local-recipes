# pyforge-atlas — planning artifacts

BMAD Tier-2 output for this project, and the repo's **reference layout** for what a complete
planning-artifacts tree looks like under bmad-method ≥ 6.10 with bmad-loop.

Status: **shipped** — 32 of 32 stories across Waves 0 and A–H, merged through PRs #69–#102
(2026-07-17/18). These artifacts describe what Atlas *is*, in the present tense, not a plan for
building it.

## Layout

```
planning-artifacts/
├── specs/
│   ├── spec-pyforge-atlas/          # the Spec kernel + its peer companions
│   │   ├── SPEC.md                  #   the contract: Why / Capabilities / Constraints / Non-goals
│   │   ├── signals.md               #   companion: 23 ported phases → nodes, the 3 additive riders
│   │   ├── catalog-contract.md      #   companion: 7 pipelines × 86 datasets, TTLs, identity
│   │   ├── degradation-contract.md  #   companion: the 3 markers, the exit projection
│   │   └── gate-contract.md         #   companion: the 7 gates
│   ├── spec-upstream-discovery/     # a second Spec kernel — trending / org-audit ingestion
│   └── spec-<story>.md × 32         # per-story specs (tracked, durable — never Tier-3)
├── prds/prd-pyforge-atlas-2026-07-17/
│   ├── prd.md, addendum.md, .memlog.md, review-*.md, validation-report.{md,html}
├── architecture/architecture-pyforge-atlas-2026-07-17/
│   ├── ARCHITECTURE-SPINE.md, .memlog.md, reviews/
├── briefs/brief-pyforge-atlas-2026-07-25/brief.md
├── research/                        # domain + technical currency research
├── retros/                          # 8 per-epic retros + SYNTHESIS.md
├── epics.md                         # 9 epics / 32 stories, each with its delivery record
├── deferred-work-ledger.md          # all 52 deferrals, tracked (Tier-3 copy was truncated)
└── *-2026-07-17.md                  # readiness, groundtruth, closeout, sprint-change proposal
```

## The kernel/companion split

The **kernel** (`SPEC.md`) states each contract once, compressed. A **companion** holds the
table that contract compresses. The rule for deciding where something goes:

> If a normative claim in the kernel cannot be reviewed or refuted without an enumeration,
> that enumeration is a companion — a contract, not documentation.

Concretely: "TTLs are declared per dataset, never a global constant" is unverifiable without the
TTL table, so the table is `catalog-contract.md`. "Gates are never weakened" is unenforceable
against an unenumerated set, so the set is `gate-contract.md`.

Kernel Constraints cross-reference their companion inline (*"Full projection:
`degradation-contract.md`."*). Frontmatter keeps the two roles distinct:

- `companions:` — **peer contracts** in this directory. Normative. Part of the contract.
- `sources:` — dreams, the legacy intake spec, the planning chain (PRD / spine / epics),
  briefs, research. Traceability; consult for narrative rationale the contract omits.

This split is grafted from `pyforge-warden`, which established the pattern
(`verdict-contract.md` / `axes.md` / `extraction-contract.md`).

## Story specs are durable

Per-story specs live here, **tracked**, not in gitignored `implementation-artifacts/`. In a
spec-driven build the spec *is* the contract, so it must survive worktree teardown and exist in
every clone. See `specs/README.md` for this project's per-story provenance — 12 are full
original dev specs; 20 were rebuilt, because waves B9–H4 ran through an in-session agent loop
that never emitted story files.

Each rebuilt spec carries a `## Delivery Record` derived exactly from its merged PR (`gh`), and
says plainly that no original existed. Nothing in them is invented.

**All 32 carry uniform `status: shipped` YAML frontmatter** (operator decision 2026-07-27,
`AUD-ATLAS-045`; applied 2026-07-28).

This reverses an earlier convention recorded here, and the trade is worth stating rather than
quietly overwriting. The 12 recovered originals never had frontmatter — the `bmad-create-story`
outputs they are didn't emit any — so this section previously argued that normalizing them
"costs more in provenance than it buys in uniformity." The operator chose uniformity: one
status field, queryable across the whole set, is worth more than byte-faithfulness to the
recovered bytes.

**What that costs, precisely.** The 12 are no longer byte-identical to what was recovered.
Their **bodies still are**: the added block sits above the `<!-- RECOVERED … -->` banner,
nothing below it was touched, and each added block says so in a `frontmatter_note`. So the
provenance claim survives — narrowed from "this file is the recovered original" to "this file's
body is the recovered original."

**Verify by class, not uniformly.** Frontmatter must parse on all 32; the `<!-- RECOVERED -->`
banner must survive on the 12. Both are checked — 32/32 and 12/12 as of 2026-07-28.

## Regenerating

Read `../../../CLAUDE.md` § *Keeping BMAD artifacts in sync* first. Address this project by
**physical path** (`_bmad-output/projects/pyforge-atlas/…`) or `BMAD_ACTIVE_PROJECT=pyforge-atlas`
— never let a parallel agent touch `scripts/bmad-switch`, which is per-working-tree global state.
