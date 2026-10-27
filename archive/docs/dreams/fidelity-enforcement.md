---
title: Fidelity enforcement — a contract is only a contract if something fails against it
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Superseded 2026-08-02 (dream consolidation).** The Marshal-owned slice is fully
> decomposed into `spec-pyforge-marshal` and the real PRD as FR-64 (a gate evaluation binds
> to the tracked spec's Success signal) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). The Doctor- and Scribe-owned
> slices of this same Dream (CAP-9 install-the-judge, CAP-6 actor-attributed event record)
> were explicitly out of scope for Marshal's PRD per the 2026-08-01 operator-scoping
> decision and remain those stations' own open items, not absorbed here. See
> `spec-fidelity-enforcement` for the retirement record.

# Fidelity enforcement — a contract is only a contract if something fails against it

## The Dream

Every tier boundary in the factory carries a **gate that fires in both
directions**. Not a convention, not a runbook line, not a rule an agent is
trusted to remember at 4am — a thing that goes red.

The factory already believes this in one place. Charter §7 was amended on
2026-07-28 so the Guildhall **refuses to publish** a row with no owner:
*visibility without consequence is decoration.* That sentence is not about
consoles. It is the general law of this system, discovered locally and never
generalized. Fidelity enforcement is that law applied to every boundary the
Dream→Code chain crosses:

> A contract that nothing can fail against is a plan.

The dream is a factory where **no tier boundary is held by attention** —
where the answer to "does the code still satisfy the contract it was built
from?" is an exit code, in both directions, at every layer, and the honest
answer when a boundary is ungated is that it says so out loud rather than
looking clean.

## Why now — the hole we can measure

`EXEMPLAR-STANDARD.md` states **ten** conformance requirements.
`dream_chain_check.py` enforces **INV-0…INV-3**, covering the ownership
through-line, the Dream→Spec link, and the sharded build tree. Rows **7, 8, 9
and 10** — per-story specs tracked, delivery records, the deferred-work
ledger, the layout README — are written down and enforced by nothing.

Row 7 is the one with a body count. Story specs are drafted by bmad-loop into
gitignored Tier-3 and become durable only if a human promotes them after
merge. At Dream-seed time: 125 stories done fleet-wide, 73 story specs
tracked — a gap of **~52**, and *approximately* is the point: nothing derives
that number, so this Dream cannot state it exactly without violating
`EXEMPLAR-STANDARD`'s own provenance rule 3, *derive counts; do not restate
them*.

Hand-repair does not hold. Warden and Atlas are the two stations whose story
specs were reconstructed by hand after real losses, and both have **drifted
again since** because the repair added artifacts and never added a gate. Six
stations were never repaired at all.

## The fidelity stack

Eight boundaries, most declarative-only and unchecked in the reverse
direction. Full table, the source-essay disposition, and the audit-triad's
substrate mapping: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement/fidelity-stack.md`.

One property is easy to miss: **every layer is declarative.** Each states
what *should* be true, so each check compares a document to a document. What
actually happened at runtime — did the gate fire, was it skipped, who
overrode it — appears nowhere, because the factory has no observation plane.
That absence is Scribe's leg of the audit triad below, and it is why the
stack cannot currently close its own reverse direction.

## Three ideas from the provoking essay

Dispositioned in full, with the source's two blind spots, in the Spec's
`fidelity-stack.md` companion. Summary:

1. **The Spec is a layer in the fidelity stack — held, extended.** The
   Charter already says the PRD→architecture→epics chain is the Spec's
   *decomposition*, not a substitute for it. But the layering is asserted,
   not measured — INV-3 checks only the chain's *shape*. **Adds:** the
   Spec↔chain reverse gate (`EXEMPLAR-STANDARD` rows 5–6).
2. **The privileged layer fallacy — rejected in half, and the half
   matters.** Authorization stays privileged, permanently (an unattended
   factory needs something to hold intent still). Origination is not
   privileged, and never was — `bmad-drift-check`'s `surface-changed`
   reconciliation already does the essay's reverse check. **Adds:** a
   recorded fixed point per reconciliation.
3. **The resolution trap — the real gap, and it is ours specifically.** The
   spec→code gap is deliberately wide; the story spec is the factory's
   gap-narrowing device, and it is precisely the layer with no gate.
   **Adds:** Marshal builds · Doctor judges · Scribe records — INV-4,
   automatic Tier-2 promotion, and the reverse gate binding a spec's Success
   signal to the verify command that gated it.

## The audit triad — Marshal builds · Doctor judges · Scribe records

The Charter's chain reads forward as authorization (Marshal, named outright)
and backward as audit — a direction that has never had an accountable
station, though Scribe was chartered for exactly it. Extends §5's *the hand
that builds is never the gate that judges* one step further: **the hand that
judges is never the sole keeper of the judgement.**

Full definition, the five-field who/what/when/how/why event record, the four
concrete 48-hour incidents that motivate it, and the substrate mapping
(`journal.jsonl` / DuckDB / `pyforge-scribe`'s capture seam):
`.../spec-fidelity-enforcement/audit-triad.md`. Governing rule, stated here
because it is the thesis in one sentence:

> **An absent record and a clean record must never look the same.**

## What is real

Nine detectors run today: `bmad-drift-check`, `spec_surface_check`,
`dream_chain_check`, `deferred_work_check`, `dashboard_drift_check`,
`story_status_check`, `loop_stall_check`, `llms_full_check`,
`unpushed_work_check`. **The wiring, once the sharpest finding in this
Dream, shipped 2026-07-31**: `.github/workflows/detectors.yml` runs a
derived registry (`scripts/detectors.py`) on every PR and push, advisory
(findings warn, do not block). First run reconciled the concrete cost of
having had no trigger at all: the `spec_surface_check` drift PR #170
introduced and merged unnoticed.

## The frontier

The full, current capability list — with intent/success criteria, what has
shipped, and what is still open — is the Spec, not this Dream:
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement/SPEC.md`.
In order, cheapest first: wire the detectors (**shipped**) → INV-4 (a
shipped story has a tracked spec) → automatic Tier-2 promotion → reverse
gates binding a spec's Success signal to its verify command → the record
rows get a station (Scribe, rows 7–9 as one trace) → the actor-attributed
event record → the ungated boundary declares itself → the fixed point
declared per change → **install the judge** — the control that makes every
other gate on this list trustworthy, and the only one currently held by
prose (Doctor over Marshal, ratified 2026-07-28, unenforced).

**Landing a gate on a factory that already violates it** — the baseline/
ratchet/grandfathering-expires migration doctrine for switching on INV-4
without redding the whole fleet — is in the Spec's
`migration-and-invariants.md` companion, borrowed from
[[pyforge-warden]]'s precedent.

## How we will know it worked

`regenerable-factory` has the regeneration drill. This Dream's equivalent:

> **Delete a tracked story spec at random, and CI names it — by story key, to
> the accountable station — within one run. Then do the same to a verdict:
> skip a gate, and the record shows a skip rather than a silence.**

Two deletions, because the Dream has two halves: the first proves the
declarative gates close, the second proves the observation plane exists —
and it is the one the factory would fail today.

## What this is not

[[regenerable-factory]] asks *does every line of code have a contract it can
be rebuilt from* — coverage, forward. Fidelity enforcement asks *does
anything go red when a contract and its artifact disagree* — enforcement,
both ways. They share a detector surface and must not share a scope.

## The Charter amendment it drives

Lexicon **§2 The Spec** defines the unit of contract but never says what
makes one binding. §7 already contains the missing sentence, scoped to the
Guildhall; the amendment generalizes it: a Spec is the unit of contract
**because something fails against it**.

A second clause, because the first is unsafe without it: per the 2026-07-28
ratification Marshal owns the detectors and the loop, so **Doctor holds the
verdict on Marshal's own rows** — an assumption this Dream depends on, not a
property it inherits (see *install the judge*, above).

A third clause — **the audit triad**: a Charter that names who builds and
who judges but not who *records* cannot deliver the backward trace it
already promises. **Scribe records events, not outcomes** — a record written
*by the verdict* is worthless for audit, because skipping the verdict then
also erases the evidence that it was skipped.

**Today none of the audit triad's five fields survives durably, and one is
deliberately erased.** `git blame` attributes to the *committer*, not the
actor. This repo's no-AI-attribution convention stays — the remedy is not to
restore a commit trailer, it is that provenance belongs in Scribe's
structured record (see `audit-triad.md`).

## Provenance

Provoked by an external essay on spec-driven development, read 2026-07-31.
Its argument, paraphrased: a specification earns the name only when
something can fail against it automatically on every change — otherwise it
is a prompt with ambitions. *(Paraphrased deliberately; the source is not
named here, at the operator's decision.)* Its fidelity-stack framing names
the layered-compression model this Dream borrows; § *Three ideas from the
provoking essay* is the authoritative record of what was adopted, adapted,
and refused.

One structural limit of the source, recorded because it is the reason this
Dream is **Charter-bound rather than merely a detector backlog**: its model
is artifact-centric and has no vocabulary for *who may weaken a gate* — that
question is not a refinement of the source's framework, it is the part an
autonomous factory cannot run without, because a system that can edit its
own gates has no gates.

## Kinships

The audit triad, in order: [[pyforge-marshal]] (builds — owns the loop that
must promote and the detectors) · [[pyforge-doctor]] (judges — holds the
verdict on Marshal's row) · [[pyforge-scribe]] (records — the record that
dies on teardown is the disease it was chartered to cure).

Then: [[regenerable-factory]] (coverage, to this Dream's enforcement) ·
[[team-memory]] (the durable trace Scribe's leg resolves to) ·
[[pyforge-warden]] (never-false-green, applied to our own board) ·
[[factory-console]] (§7, where this law was first discovered) ·
[[pyforge-charter]].

## Realization log

- **2026-07-31** — Dream seeded (operator call). Owner **marshal** by the
  cross-cutting-practice precedent; scope set to the **full fidelity
  stack**, not the story-spec row alone. Measured at seeding: 125 stories
  done, 73 story specs tracked, conformance rows 7–10 enforced by nothing.
- **2026-07-31** — **the audit triad named** (operator call): *Marshal
  builds · Doctor judges · **Scribe records***. Recorded as a Dream-level
  decision because it is larger than this Dream — the Charter's chain reads
  backward as audit and that direction has never had an accountable
  station.
- **2026-07-31** — **Scribe's leg scoped to events, not outcomes** (operator
  call): the record captures *everything an agent makes or does*, governed
  by *an absent record and a clean record must never look the same*.
  Extended the same day to actor attribution (who · what · when · how ·
  why).
- **2026-07-31** — **Scribe's record declared inclusive of runtime
  telemetry** (operator call): queried observability answering *what the
  system actually does*, alongside the curated knowledge graph answering
  *why*.
- **2026-07-31** — **independent review before commit.** Fixed three
  defects (a pronoun, a flat-restated count, an orphaned amendment clause).
  Added a migration doctrine and a success signal. Resolved the citation
  question by paraphrasing rather than quoting the source unattributed.
- **2026-07-31** — **the detectors themselves are untriggered** (found
  during the same review). No CI job or git hook invoked any of the eight
  then-existing detectors — the Dream's own thesis one level lower down.
  *Wire the eight* became the first frontier item, ahead of INV-4.
- **2026-07-31** — **the trigger shipped, advisory** (operator decision).
  Nine detectors now run on every PR and push via
  `.github/workflows/detectors.yml` and a derived registry
  (`scripts/detectors.py`). Findings warn, they do not block. Reconciled in
  the same change: the `spec_surface_check` drift PR #170 introduced and
  merged unnoticed.
- **2026-07-31** — **six invariants recorded for the trigger**, after the
  design was worked out conversationally and would otherwise have survived
  only in a session transcript. Three detectors found red on `main` at the
  time: `spec-surface-check` (broken by PR #170 itself), `dashboard-drift-
  check` (transiently), `dream_chain_check`'s INV-1 (expected until the Spec
  existed).
- **2026-08-01** — **Spec derived** (`bmad-spec`, operator-directed housekeeping
  session): `spec-fidelity-enforcement` — 9 capabilities (CAP-1 wiring
  shipped; CAP-2..9 open), 3 companions (`fidelity-stack.md`,
  `audit-triad.md`, `migration-and-invariants.md`). This Dream trimmed in
  the same session from ~652 to its current length, per the deferral
  recorded in the prior entry — mechanism detail (the fidelity-stack table,
  the disposition table, the audit-triad schema/incidents/substrate table,
  the six trigger invariants, the migration doctrine) moved to the Spec's
  companions rather than living in both places. `dream_chain_check`'s INV-1
  against marshal closed as part of the same pass (all 4 marshal-owned
  Dreams — durable-runs, fidelity-enforcement, one-front-door,
  pr-lifecycle — now have Specs).
