---
title: Sentinel — the AI Software Factory (the ancestor)
type: dream
status: seeded
---

# Sentinel — the graph is the product

## The Dream

The ancestor dream (2026-04-18/19, predating the pyforge model): **Sentinel,
the AI Software Factory.** Its diagnosis — an engineer touches six tools in the
first hour; the knowledge the team runs on (the *why* of code X, rejected
tradeoffs, the 3am runbook) is scattered and lossy; AI without the graph
hallucinates; knowledge-base products sell a better editor when the bottleneck
is the round-trip. Its thesis, four properties:

1. **The graph is the product** — every artifact a node, every reference an
   edge, compiled nightly from the tools the team already uses.
2. **The floor is agentic** — five specialist agents (Analyst, Architect,
   Developer, QA, PO), each owning one shift.
3. **The audit is the contract** — every LLM call an OTel GenAI span, every
   data move an OpenLineage event, every story closed with cited evidence.
4. An **all-local / WASM / air-gapped branch** — the factory where the internet
   isn't.

## What exists (stranded in Design, to be repatriated)

Design project *"LLM Knowledge Bases"* (`fca0375d-…`): Build-Spec **v2.1**
(764 lines, BMAD-METHOD v6.3.x, "Ready for Implementation", Apache-2.0 license
bar), engineering + stakeholder decks, five airgap/WASM audits, the LLM
Knowledge Bases deck (origin: a 2026-04-18 essay on LLM-powered personal
knowledge bases), and an **unshipped `COMMIT_MSG.txt` + `PR_BODY.md`** — the
effort was ready and never landed. Repatriation via the bridge is the first
realization step.

## Lineage — what the descendants took

- Five agents → the six-persona **[[ecosystem-crew]]**.
- §19 Kedro · §20 Dagster · §27 BSL · §24 OTel/OpenLineage · §26 La Suite →
  **[[pyforge-atlas]]**'s shipped stack, to the letter.
- Audit-as-contract → **[[pyforge-warden]]** + [[pyforge-marshal]]'s gates.
- §40 Airgap Bundle · license bar · WASM branch → **[[enterprise-airgap]]**.
- The knowledge problem, first organ → **[[team-memory]]**.
- Its design-tokens pipeline (Figma↔JSON↔POTX) → **[[modernist-identity]]** /
  **[[deckcraft]]**.

**The unbuilt core**: the team knowledge graph compiled nightly from real tools.
That remains this Dream's open claim.

## Realization log

- **2026-04-18/19** — essay → decks → Build-Spec v2.1; never landed in a repo.
- **2026-07-23** — rediscovered during the Design-workspace audit; Dream seeded;
  descendants credited; repatriation pending.
