---
title: '21.10: The registry sees all fourteen decks'
type: 'fix'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 20.13 registered the ten PyForge decks and left the four chain decks unlinked; registry.read cannot parse deckcraft's 24-line body.

**Approach:** Re-register each through registry.register with history under ### Provenance and re-run the bootstrap. herald deck status --repo-root . reports all fourteen decks linked. A fresh clone reproduces it from READMEs. agentic-sdlc is left to Story 23.2. Dispatch this only after the four Claude Design pushes (21.6–21.9).

## Boundaries & Constraints

**Always:**
- herald deck status reports all fourteen decks linked with project ids.
- A fresh clone reproduces the registry from READMEs alone.

**Never:**
- Do not declare agentic-sdlc unlinked by design — Story 23.2 owns that register.
- Do not mark this story done before the four Design pushes exist to register.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| after register | herald deck status --repo-root . | fourteen linked | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-deck-family-lockstep CAP-4`.
Surface: presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/README.md; .herald/bridge-state.json bootstrap..
Ledger key: `21-10-the-registry-sees-all-fourteen-decks`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-21-10-the-registry-sees-all-fourteen-decks.md`.
