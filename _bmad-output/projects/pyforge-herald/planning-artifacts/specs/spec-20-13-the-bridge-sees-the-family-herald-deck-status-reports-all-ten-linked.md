---
title: 'The bridge sees the family — `herald deck status` reports all ten linked'
type: 'fix'
created: '2026-09-13'
status: 'done'
baseline_revision: a3bec555fb
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** `herald deck status --repo-root .` reported every deck `linked: false`. Two causes,
both real: no `.herald/bridge-state.json` existed (it is gitignored, so no clone has one), and every
deck README's `## Design project` section predated the canonical two-line shape `registry.read`
parses (DW-1-5-1) — so even the bootstrap fallback could not read them. The bridge could not see the
family it had just published.

**Approach:** Re-register all ten PyForge deck sections through `registry.register` (the module that
owns that span), preserve the two decks' genuine history under a new `### Provenance` sub-heading,
bootstrap the state file from those READMEs, and document the bootstrap so a fresh clone reproduces
it.

## Boundaries & Constraints

**Always:**
- `registry.register` writes the span; the canonical body is exactly two lines and the `file_url`
  names the deck's **prototype** `.dc.html`, the field the section round-trips.
- History the rewrite displaces moves to `### Provenance` immediately below — which also bounds the
  machine-owned span for every future `register`. Only atlas (seeded late) and warden (renamed from
  "Python deptry OSV scanner") had any; the other eight bodies were boilerplate the canonical
  section states exactly.
- The bootstrap reads the READMEs, never the other way round: they are the durable record and
  `.herald/bridge-state.json` is the gitignored operational half.
- `registry.read` must round-trip every one of the ten after the rewrite.

**Never:**
- Never invent a third registry; never write a project id the README does not carry.
- Never link the chain decks (agentic-sdlc, deckcraft, presenton-pixi-image, unity-data-stack,
  wasm-analytics-stack) — they stay unlinked by design.
- Never touch an artifact-map or sync-ledger sub-section.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ten registered | the ten PyForge READMEs | `registry.read` returns the right project for each | — |
| Status after bootstrap | `.herald/bridge-state.json` present | 10 of 15 decks `linked`, each with its id | — |
| Chain deck | `deckcraft` README, malformed section | reported unlinked, never guessed | `registry.read` raises; the bootstrap skips it |
| Fresh clone | no state file | the documented bootstrap rebuilds it from the READMEs | — |
| History | atlas / warden prose | preserved verbatim under `### Provenance` | — |

</intent-contract>

## Tasks & Acceptance

**Execution:**
- `presentations/pyforge-*/README.md` (×10) -- re-register the section; add `### Provenance` where history existed.
- `.herald/bridge-state.json` -- bootstrapped (gitignored, not committed).
- `docs/specs/presentation-deck.md` -- the registry contract and the bootstrap recipe.
- `spec-deck-family-currency/.memlog.md` -- the landing event naming every governed file.

**Acceptance Criteria:**
- Given the ten registered READMEs, when `herald deck status --repo-root .` runs, then exactly the
  ten PyForge decks report `linked: true` with their project ids.
- Given a deleted state file, when the documented bootstrap runs, then the same answer returns.

## Auto Run Result

**Summary:** All ten sections re-registered through `registry.register`, pointing at each deck's
prototype `.dc.html`; atlas and warden keep their history under `### Provenance`; the state file is
bootstrapped from the READMEs and the recipe is documented.

**Verification:** `registry.read` round-trips all ten (10 distinct project ids). `herald deck status
--repo-root .` reports **10 of 15 linked** — the ten PyForge decks with their ids, the five chain
decks unlinked as designed; `stale_mirror` false everywhere. Before this story: 0 of 15.

**Residual risks:** the state file is gitignored, so every clone runs the bootstrap once; the chain
decks' sections stay malformed until their own wave re-registers them.
