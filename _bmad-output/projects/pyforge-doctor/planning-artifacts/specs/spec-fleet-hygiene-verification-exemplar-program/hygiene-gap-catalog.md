# The six-category hygiene/verification/exemplar catalog

Condensed from `docs/dreams/fleet-hygiene-verification-exemplar-program.md`. Full prose and case studies live in that Dream file; this companion preserves the structure and status so downstream readers don't have to re-derive it.

**Exemplar is the load-bearing concept, not one category among six.** `_bmad-output/EXEMPLAR-STANDARD.md` designates `pyforge-atlas` as the exemplar for the whole planning-artifact shape and states the invariants that define "done and clean," structurally, fleet-wide. Categories 1–4 and 6 measure conformance *to* an exemplar (or flag that none has been designated yet); Category 5 is what defines the target itself.

## How to use this catalog

When a review pass, an audit, or a fresh "nothing actually checks for X" finding shows up, check it against this catalog before treating it as new. There are exactly three possible answers:

1. **Already cataloged and specced or shipped.** The finding matches a named item below whose `Status:` tag reads `specced` or `shipped` — cite that item's owning spec/epic/story and stop; no new scope is needed. (A `specced` tag means work is already scheduled, not already done — check whether the owning story has landed before treating the gap as closed.)
2. **Cataloged but not yet built.** The finding matches a named item tagged `Status: cataloged` — a known, open gap with no owning spec/story yet. Scope it into a new Spec if it's now worth building, or leave it open, but don't re-discover it as novel.
3. **Genuinely new.** The finding matches nothing below — add it as a new item under the relevant category, or a new `## Category 7 — <name>` (numbered sequentially past the highest existing category) if none fits, with `Status: cataloged — open, unscoped`, so the next reader doesn't repeat this search.

If a finding only partially overlaps a cataloged item, or spans more than one, note the partial/multi-item match explicitly in your citation rather than forcing it into a single bucket — cite each matching item by its own `Status:` tag instead of picking one arbitrarily.

Whenever an item's real-world state changes (a Spec gets written for it, a story lands, or a shipped fix gets reverted), flip its `Status:` tag in place — `cataloged → specced → shipped`, or `shipped → cataloged (reopened, see citation)` on a regression — update the evidence citation, and date-stamp the change. If the same item is cross-referenced from more than one category (as Category 2/3's deferred-work-resolution entries are), update every copy together so they don't drift apart.

**Worked example.** A fresh audit reports: "`chain-completeness`'s INV-A check uses a bare substring test and misses partial decomposition." Scanning Category 1 first: it already names this exact defect as `DW-CHAIN-COMPLETENESS-1`. When Story 12.3 was still open, this line's `Status:` tag read `specced — this Spec's CAP-3, doctor Epic 12 Story 12.3, not yet landed` — that was answer 1, already known and already owned by a story, no new Spec or catalog entry needed, just point the finding at Epic 12 Story 12.3. (Story 12.3 has since landed — see Category 1's own tag below, now `shipped` — which is itself the maintenance discipline this section asks for: the tag moved in place rather than this example going stale silently.)

## Category 1 — Mechanically gated today
`python -m pyforge.doctor.sources`'s 10 subcommands are the fleet's real always-on floor. Tonight's audit proved a mechanical detector can still have a real blind spot: `deferred-work`'s `tier3-only-deferral` finding (id-diff-based, misses headerless entries) (Status: shipped — spec-deferred-work-visibility CAP-4, doctor Epic 8 Story 8.1, done; verified 2026-08-21) and `chain-completeness`'s INV-A (bare substring test, misses partial decomposition — `DW-CHAIN-COMPLETENESS-1`, **this Spec's CAP-3**) (Status: shipped — this Spec's CAP-3, doctor Epic 12 Story 12.3, done; verified 2026-08-21). Each detector deserves the same scrutiny on its own schedule, not just when challenged.

## Category 2 — Already has its own Dream
- Deferred-work promotion → `deferred-work-audit-completeness.md`, folded into `spec-deferred-work-visibility` CAP-4..7. (Status: shipped — spec-deferred-work-visibility CAP-4..7, doctor Epic 8 Stories 8.1-8.4, done; verified 2026-08-21)
- Deferred-work resolution → `deferred-work-resolution-sweep.md`, this session's sibling Spec. (Status: shipped — spec-deferred-work-resolution-sweep CAP-1..7, doctor Epic 11 Stories 11.1-11.7, done; verified 2026-08-21)
- `engine.pid` liveness footgun → `bmad-loop-liveness-footgun.md` (marshal-owned, unspecced). (Status: cataloged — open, unscoped, marshal-owned; verified 2026-08-21)

## Category 3 — Done once by hand, never systematized
- `bmad-output-hygiene` sweep (5 CAPs, run once against warden only) → generalized as `spec-deferred-work-visibility` CAP-8/9 (Epic 9, Story 9.2/9.3). (Status: shipped — spec-deferred-work-visibility CAP-8/9, doctor Epic 9 Stories 9.2/9.3, done; verified 2026-08-21)
- Repo-wide audit remediation waves (`AUD-CFE-*`, PRs #131/#133-138) — fixed once, methodology never turned into a repeatable check. **Open question, not scoped here.** (Status: cataloged — open, unscoped; verified 2026-08-21)
- Deferred-work resolution campaign — see Category 2. (Status: shipped — spec-deferred-work-resolution-sweep CAP-1..7, doctor Epic 11 Stories 11.1-11.7, done; verified 2026-08-21)
- Loop-home branch staleness → `spec-deferred-work-visibility` CAP-10 (Epic 9, Story 9.4). (Status: shipped — doctor Epic 9 Story 9.4, done; verified 2026-08-21)

## Category 4 — Dashboard / fleet health metrics
- Deferred-work verification staleness % → sibling Spec's CAP-7. (Status: shipped — spec-deferred-work-resolution-sweep CAP-7, doctor Epic 11 Story 11.7, done; verified 2026-08-21)
- Loop-home branch staleness → Epic 9 CAP-10. (Status: shipped — doctor Epic 9 Story 9.4, done; verified 2026-08-21)
- `dream-chain` gap count in the ambient report → **this Spec's CAP-4.** (Status: specced — doctor Epic 12 Story 12.4, backlog, not yet landed; verified 2026-08-21)
- GuildHall Fleet Status Dashboard as the human-facing mirror — which new signals belong there too is an open question, not scoped here. (Status: cataloged — open, unscoped; verified 2026-08-21)

## Category 5 — Exemplar / golden-standard references
`EXEMPLAR-STANDARD.md` is the primary, structured answer to "what does done-and-clean mean" — five binding invariants (INV-0..INV-5), a conformance table, its own detector (`dream_chain_check.py`). **Its conformance table is stale on exactly the row this session's work touched** (DW-ledger column shows only atlas ✅; 7 other projects now have real ledgers) — **this Spec's CAP-2**, flagged in the source Dream as the most concrete, ready-now item in the whole catalog. (Status: shipped — doctor Epic 12 Story 12.2, done; verified 2026-08-21)

Narrower, purely-manual exemplars with no mechanical backing (not scoped by this Spec — see Open Questions):
- Six-act deck framework (canonical template for all 21 station decks). (Status: cataloged — open, unscoped; verified 2026-08-21)
- Warden-standalone as the infographic exemplar (Design `100ca8cc`). (Status: cataloged — open, unscoped; verified 2026-08-21)
- "Full depth + acts for ALL Herald work" — the exemplar sets a floor, never a target to economize against. (Status: cataloged — open, unscoped; verified 2026-08-21)
- Recipe-domain exemplars inside `conda-forge-expert` (canonical npm pattern, v0↔v1 about-field mapping). (Status: cataloged — open, unscoped; verified 2026-08-21)
- CFE's `add-recipe-<name>` branch-naming convention (drift found once, 2026-06-10, easy to silently reintroduce). (Status: cataloged — open, unscoped; verified 2026-08-21)

*(The two data points below are reference narrative about how an exemplar graduates, not themselves a catalog item — no `Status:` tag; exempt from the lookup protocol above.)*

**Two data points on what "graduating" an exemplar looks like**, worth studying as the aspirational end-state:
1. **Bake into the generator.** The universal `conda-forge.yml` pre-seed started hand-maintained, got a per-setting applicability audit (G83), and is now auto-emitted by the recipe generator itself — nothing left for an author to forget.
2. **Repeatable apply-script.** Herald's TEA+Playwright test-architecture was designated the fleet's canonical reference (2026-08-02) and the rollout actually happened — all 8 stations carry a real `test-architecture.md` today, independently confirmed by the `bmad-output-hygiene` sweep.

Which shape fits each remaining manual exemplar is an open question, decided per-exemplar when sized — not assumed to be one-size-fits-all.

## Category 6 — Named ledger/artifact machinery bugs
- `normalize_deferred_ledgers.py`'s heading-less-entry blind spot — shared root cause with Category 2's two deferred-work Dreams. (Status: shipped — spec-deferred-work-visibility CAP-4, doctor Epic 8 Story 8.1, done; verified 2026-08-21)
- `warden DW-1-4-1` — still needs splitting into two ids (named 2026-07-30, never done; not scoped by this Spec, see its Non-goals). (Status: cataloged — open, unscoped; verified 2026-08-21)
- `spec_surface_check.py --write-baseline`'s unlocked read-modify-write race (`DW-13-5-2`) → **this Spec's CAP-5.** (Status: specced — doctor Epic 12 Story 12.5, backlog, not yet landed; verified 2026-08-21)
