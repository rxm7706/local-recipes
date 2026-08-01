# Narration script — Unity Data Stack

> Extracted from `Unity Data Stack.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 10 scenes.

## Scene 01 — Cover

Unity Data Stack is the Inner-Source Model made concrete: one opinionated, conda-native, air-gap-first, spec-governed monorepo where teams co-contribute templates, libraries, services and Data Products on a single python-first toolchain. Standards chosen once and machine-enforced, not written on a wiki page. Planning ran to PRD plus architecture depth: 9 capabilities, 60 functional requirements, 23 architecture decisions.

## Scene 02 — Act I — Six problems, solved once

Act I: the value is not the monorepo. It is that six problems get solved once instead of once per team — and the organization stops paying for the difference forever, in onboarding time, duplicated internal libraries, audits measured in weeks, and the quiet conclusion that sharing code across teams is more trouble than it is worth.

## Scene 03 — Two clocks

Why now is load-bearing for two independent reasons. The regulatory clock: the EU Cyber Resilience Act entered into force 2024-12-10; vulnerability-reporting obligations begin 2026-09-11 and main obligations 2027-12-11 — know what you ship, continuously, becomes a dated legal duty. The artifact decay clock: three substantial intake artifacts authored January to May 2026 were never landed and have measurably drifted — the pinned workspace manager blocks installation outright, and the Python baseline has expired underneath the document.

## Scene 04 — The Constitution is the spine

The Constitution, v1.2.0, ratified 2025-11-20, is not background reading — it is the requirement spine. Every functional requirement traces to an Article or to that Article's explicit disposition. Article XI is not carried in v1 at all: it is guidance with no platform mechanism, and a candidate for demotion to a guide. Eight amendments are required before re-ratification, including correcting MCP to Model Context Protocol and naming whose approval Article VIII demands.

## Scene 05 — Act II — One authoritative lock

Act II: the toolchain. A pixi orchestrator root produces one workspace lock covering conda and PyPI packages together; the PEP 751 pylock.toml export and the offline bundle are derived from it and drift-checked against one pinned commit SHA. This is the feature the intake set got most wrong, and the correction is load-bearing.

## Scene 06 — The command that does not exist

The honest finding, and the deck's sharpest slide. The intake toolchain spec's flagship lock-generation command uses a flag that does not exist: pdm export has no --override-platform. Platform targeting lives on pdm lock --platform. Compounding it, PEP 751 itself does not guarantee multi-platform lockfiles — it uses environment markers, not a cross-compilation guarantee — so the Cryptographic Predictability outcome the intake spec promised had no verified mechanism at all. This is the empirical grounding for AD-2 and AD-3: one authoritative lock, and coverage proven by materialization rather than inferred from a format claim.

## Scene 07 — Governed, not imposed

The largest gap the research found, from two independent angles. The Constitution declares itself uniformly immutable and non-negotiable, which collapses federated governance into central imposition; AD-8 splits every mandate into Platform Invariant or Domain Default, machine-readably, with overrides requiring a linked decision record. And the social layer was essentially unspecified: the Constitution requires at least one human approval and never says whose. FR-33 names the Trusted Committer per package. The counter-metric matters as much as the metric — if cross-team contribution rises while internal forks do not fall, the metric is not measuring what it claims.

## Scene 08 — Three planes, one paradigm

Declarative Reconciliation is the platform's single paradigm: every plane declares a desired state and materializes it; nothing is mutated in place. A materialized thing is disposable and re-derivable, a change is made to the declaration, and drift between the two is a defect with a detector. AD-17 then requires every plane to resolve to exactly one accountable station of the PyForge Guild — and the intake role matrix's five roles map onto the eight Smiths with three stations left unmapped, all of them feedback-loop roles: communication, diagnostics and memory.

## Scene 09 — Compliance is a build artifact

Compliance is a build artifact, not an activity — and it is largely integration work. Every deployable artifact carries a versioned SBOM generated from the built artifact with populated dependency edges, not from a lock; a flat inventory answers do we ship X but not what reaches X. Every artifact carries a provenance attestation, SLSA Build L1 mandatory and L2 the goal; an unattested artifact cannot be promoted to any Stage whose policy requires approval. And the compliance gate itself is PyForge Warden, consumed as a CLI in its own lean isolated Environment — never imported as a library, never invoked only in CI — with the gate's exit code derived from the report file.

## Scene 10 — The measured promise

Close on the success signal, and on what this project is. Onboarding under an hour in single-digit commands, using only written documentation. Cross-team reuse trending up while the internal-fork counter-signal does not rise in step — if it stays near zero, the platform has failed at its premise regardless of technical quality. One hundred per cent of declared platforms materializing every Environment, online and offline. Compliance latency in minutes, ahead of the CRA date. And the honest statement of depth: this project's planning ran to PRD and architecture only. There are no epics and no stories — they decompose fresh when the Dream is scheduled.
