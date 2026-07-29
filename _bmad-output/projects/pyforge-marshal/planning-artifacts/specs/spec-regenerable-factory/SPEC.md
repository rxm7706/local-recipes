---
spec: regenerable-factory
status: shipped
owner-dream: docs/dreams/regenerable-factory.md
companions:
  - waves.md
sources:
  - ../../../../../../docs/dreams/regenerable-factory.md
surface:
  # The chain-integrity instruments. Governed here (2026-07-28) because a detector that
  # polices the Dream->Code chain is this practice's own tooling — and three of them sat
  # UNGOVERNED, i.e. the things enforcing the model were outside it.
  - scripts/spec_surface_check.py   # CAP-3 deliverable — SHIPPED (the "does not exist yet" note was stale)
  - scripts/bmad_drift_check.py     # artifact<->factory sync + the `dream-unowned` check the Charter §5 cites
  - scripts/dream_chain_check.py    # INV-0..3: owner-dream links, Dream->Spec coverage, chain location, sharded tree
  - scripts/deferred_work_check.py   # nothing important lives only in gitignored Tier-3 (the loop's own damping valve refiles THERE)
assumptions:
  - Backfilled specs can carry machine-checkable success signals grounded in
    existing behavior (the surfaces already work; the spec states the contract
    they satisfy).
open_questions: []
---

# SPEC — regenerable-factory program

## Why

Doctrine (user decision, 2026-07-23): realized work is not exempt from the
chain. Every realized surface gets Dream → PRD/spec backfilled so the factory
and personas own everything in the repo, any change flows idea → spec → BMAD,
and drift checks bind every file to its contract. The proven local-recipes
sync loop (deterministic detector + BMAD reconciler skills) generalizes
repo-wide. Wave 0 — the multi-loop isolation harness — already shipped
(`spec-multi-loop-isolation`), so this program's loop can run concurrently
with other loops (e.g. Warden 6.3).

## Capabilities

- **CAP-1 — surface-manifest convention.**
  Intent: every SPEC.md declares `surface:` — the repo paths/globs it
  governs; existing kernels (multi-loop-isolation, design-code-bridge) are
  retrofitted.
  Success: the checker (CAP-3) can enumerate every spec's surface; no spec
  without one.

- **CAP-2 — backfill waves.**
  Intent: brownfield-`bmad-spec` each realized Dream per the wave order in
  `waves.md` (pilot first; `bmad-document-project` grounding for the two
  deep surfaces; chain-verify only where chains exist).
  Success: every realized Dream traces to a validated kernel with a surface
  manifest; each wave's spec self-validates with zero unresolved
  contradictions.

- **CAP-3 — repo-wide surface checker.**
  Intent: a deterministic script reporting (a) coverage — every tracked
  source file maps to ≥1 spec surface or an explicit allowlist entry, and
  (b) drift — a governed file changed since its spec's recorded baseline
  without the spec/memlog moving.
  Success: exit 0 on a clean repo, non-zero with named findings otherwise;
  runs as a pixi task and joins the CI detector family.

- **CAP-4 — regeneration drill.**
  Intent: prove regenerability — delete a governed module (pilot:
  `docs/dashboard/generate.py`), rebuild it from its spec alone, pass the
  same verification the original passed.
  Success: one documented drill with a green outcome; the drill procedure
  recorded so it can be repeated on any governed surface.

## Constraints

- The checker is a deterministic harness, not a skill (Marshal doctrine);
  it never false-greens (Warden temperament); the allowlist is explicit and
  logged — no silent exemptions.
- Backfilled specs describe what IS. The program does not rewrite shipped
  code to match aspiration; behavior changes are new stories under the spec.
- Execution is loop-driven on the Wave-0 harness. Waves touching CFE
  territory bind Rule 1 (invoke `conda-forge-expert`) and Rule 2 (closeout
  retro against the skill).

## Non-goals

- Decks for backfilled Dreams (Herald's backlog — a communication decision).
- Upstream bmad-method changes (tracked separately).
- 100% line-level formal verification — the contract is spec-per-surface,
  not proofs.

## Success signal

`spec_surface_check` green over the whole repo (every tracked source file
governed or allowlisted) with all realized Dreams carrying validated kernels;
plus one passed regeneration drill. Program-level: a subsequent behavior
change lands via spec-edit → loop story with the checker staying green.
