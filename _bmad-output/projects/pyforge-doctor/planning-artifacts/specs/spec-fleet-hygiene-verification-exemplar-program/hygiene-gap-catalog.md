# The six-category hygiene/verification/exemplar catalog

Condensed from `docs/dreams/fleet-hygiene-verification-exemplar-program.md`. Full prose and case studies live in that Dream file; this companion preserves the structure and status so downstream readers don't have to re-derive it.

**Exemplar is the load-bearing concept, not one category among six.** `_bmad-output/EXEMPLAR-STANDARD.md` designates `pyforge-atlas` as the exemplar for the whole planning-artifact shape and states the invariants that define "done and clean," structurally, fleet-wide. Categories 1–4 and 6 measure conformance *to* an exemplar (or flag that none has been designated yet); Category 5 is what defines the target itself.

## Category 1 — Mechanically gated today
`python -m pyforge.doctor.sources`'s 10 subcommands are the fleet's real always-on floor. Tonight's audit proved a mechanical detector can still have a real blind spot: `deferred-work`'s `tier3-only-deferral` finding (id-diff-based, misses headerless entries) and `chain-completeness`'s INV-A (bare substring test, misses partial decomposition — `DW-CHAIN-COMPLETENESS-1`, **this Spec's CAP-3**). Each detector deserves the same scrutiny on its own schedule, not just when challenged.

## Category 2 — Already has its own Dream
- Deferred-work promotion → `deferred-work-audit-completeness.md`, folded into `spec-deferred-work-visibility` CAP-4..7.
- Deferred-work resolution → `deferred-work-resolution-sweep.md`, this session's sibling Spec.
- `engine.pid` liveness footgun → `bmad-loop-liveness-footgun.md` (marshal-owned, unspecced).

## Category 3 — Done once by hand, never systematized
- `bmad-output-hygiene` sweep (5 CAPs, run once against warden only) → generalized as `spec-deferred-work-visibility` CAP-8/9 (Epic 9, Story 9.2/9.3).
- Repo-wide audit remediation waves (`AUD-CFE-*`, PRs #131/#133-138) — fixed once, methodology never turned into a repeatable check. **Open question, not scoped here.**
- Deferred-work resolution campaign — see Category 2.
- Loop-home branch staleness → `spec-deferred-work-visibility` CAP-10 (Epic 9, Story 9.4).

## Category 4 — Dashboard / fleet health metrics
- Deferred-work verification staleness % → sibling Spec's CAP-7.
- Loop-home branch staleness → Epic 9 CAP-10.
- `dream-chain` gap count in the ambient report → **this Spec's CAP-4.**
- GuildHall Fleet Status Dashboard as the human-facing mirror — which new signals belong there too is an open question, not scoped here.

## Category 5 — Exemplar / golden-standard references
`EXEMPLAR-STANDARD.md` is the primary, structured answer to "what does done-and-clean mean" — five binding invariants (INV-0..INV-5), a conformance table, its own detector (`dream_chain_check.py`). **Its conformance table is stale on exactly the row this session's work touched** (DW-ledger column shows only atlas ✅; 7 other projects now have real ledgers) — **this Spec's CAP-2**, flagged in the source Dream as the most concrete, ready-now item in the whole catalog.

Narrower, purely-manual exemplars with no mechanical backing (not scoped by this Spec — see Open Questions):
- Six-act deck framework (canonical template for all 21 station decks).
- Warden-standalone as the infographic exemplar (Design `100ca8cc`).
- "Full depth + acts for ALL Herald work" — the exemplar sets a floor, never a target to economize against.
- Recipe-domain exemplars inside `conda-forge-expert` (canonical npm pattern, v0↔v1 about-field mapping).
- CFE's `add-recipe-<name>` branch-naming convention (drift found once, 2026-06-10, easy to silently reintroduce).

**Two data points on what "graduating" an exemplar looks like**, worth studying as the aspirational end-state:
1. **Bake into the generator.** The universal `conda-forge.yml` pre-seed started hand-maintained, got a per-setting applicability audit (G83), and is now auto-emitted by the recipe generator itself — nothing left for an author to forget.
2. **Repeatable apply-script.** Herald's TEA+Playwright test-architecture was designated the fleet's canonical reference (2026-08-02) and the rollout actually happened — all 8 stations carry a real `test-architecture.md` today, independently confirmed by the `bmad-output-hygiene` sweep.

Which shape fits each remaining manual exemplar is an open question, decided per-exemplar when sized — not assumed to be one-size-fits-all.

## Category 6 — Named ledger/artifact machinery bugs
- `normalize_deferred_ledgers.py`'s heading-less-entry blind spot — shared root cause with Category 2's two deferred-work Dreams.
- `warden DW-1-4-1` — still needs splitting into two ids (named 2026-07-30, never done; not scoped by this Spec, see its Non-goals).
- `spec_surface_check.py --write-baseline`'s unlocked read-modify-write race (`DW-13-5-2`) → **this Spec's CAP-5.**
