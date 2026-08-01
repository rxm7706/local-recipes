# Narration script — PyForge Atlas

> Extracted from `PyForge Atlas.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 21 scenes.

## Scene 01 — Cover

One line: cf_atlas is the intelligence layer of an AI-assisted conda-forge packaging factory. This deck is the migration plan — a 10k-LOC orchestrator becoming declarative dataflow so an agent workforce can maintain it.

## Scene 02 — Act I — From monolith to DAG

Act I frames the problem and the paradigm: what the legacy orchestrator costs, and what declarative dataflow replaces it with.

## Scene 03 — The problem

The legacy orchestrator ships — but the cost is chronic. Agents cannot safely extend a 10k-line procedural monolith. That is the load-bearing justification for the whole migration.

## Scene 04 — Before and after

Same factory, re-shaped: pipes-and-filters over a declared Data Catalog. Pure nodes, catalog-owned IO, per-node timeouts. The six layers below map every concern to one place.

## Scene 05 — Seven domain pipelines

The 23 phases become nodes in exactly seven fixed pipelines. Producer owns the dataset — no two pipelines write one artifact. New signals join their assigned pipeline, never a new ad-hoc one.

## Scene 06 — Act II — Node-shaped & agent-maintainable

Act II: why the node shape matters. Adding a node inherits all the machinery; what the migration buys; and the verify-first gate that keeps it honest.

## Scene 07 — Add phase 24 without hand-wiring

This is the load-bearing journey UJ-5. Declare, write the node, contract it — everything else is inherited. The new signals B8-B10 land through exactly this path with zero hand-written checkpoint code.

## Scene 08 — What the migration buys

The honest wins: incremental re-materialization (not cold-start speed), a DuckDB query surface, a universe SBOM, and agent-legible feeds. Feeds beat pages.

## Scene 09 — The verify-first gate

The frozen exit-code convention and the four-axis ComplianceReport, plus the six deterministic gates that are each a wave's first deliverable. Gates are never weakened to raise the autonomy share.

## Scene 10 — Act III — An agent workforce builds it

Act III: who runs it, the graduated-autonomy execution model, the eight-wave plan, and which read surface answers which question.

## Scene 11 — Who runs it

Four consumers: the operator, CFE authoring agents, BMAD execution agents, and CI. Internal and non-commercial — adoption means operator plus agent usage across a 19,726-feedstock population.

## Scene 12 — Graduated autonomy

The execution model: 6 attended wave-boundary events, 4 dev-auto, 11 loop at per-story-spec approval, 11 loop at per-epic. ~21 of 32 are loop-drivable — but gates are never weakened to raise that share.

## Scene 13 — Eight waves, 32 stories

Wave 0 builds the SKF skill; A the scaffold; B the node ports plus parity plus new signals; C orchestration; D the read surface; E agent plane; F DuckDB consolidation; G portability; H the AI factory. Legacy retires only after B4 parity.

## Scene 14 — Which surface, when

The BSL is the single semantic interface — every read surface consumes it, never raw SQL. Vizro pages, Vizro-AI, MCP tools, A2A, and three CLI-first exceptions. Public page breadth stays at one factory-status page.

## Scene 15 — Act IV — New signals

Act IV: the three committed new signal sources — Basilisk, velocity, migration readiness — and the open questions gated by wave.

## Scene 16 — Three new signals

Basilisk matches by package name, not the OSV tag, and fix_available is tri-state. Velocity restricts to releases under 90 days and computes against first availability. Readiness partitions by upstream category lists — new migrations need no code change.

## Scene 17 — Open questions, gated

Six open questions, each adopted at its spec default now and re-checked at its gating wave. None block earlier work. Q5 was resolved into the AI-factory scope.

## Scene 18 — Act V — The read surface inverts

Act V: on top of the DAG, five surfaces — and the pyforge family relationship. Close on the real deliverable.

## Scene 19 — Five surfaces

Semantic read via BSL, the agent plane over MCP/A2A, WASM portability, the Wave-H AI factory, and quality/lineage via pandera plus OpenLineage/OTel.

## Scene 20 — The pyforge family

Two workspace members in one pyforge namespace. Atlas provides the data; warden uses it. Exactly one optional code edge; zero cycles; both install and run independently.

## Scene 21 — Never hand-wire story 33

Close: the real deliverable is not speed — the cold rebuild is network-bound. It is a DAG an autonomous agent can extend without hand-wiring a single checkpoint.
