---
spec: deferred-work-visibility
status: draft
owner-dream: docs/dreams/deferred-work-visibility.md
surface: []          # Governs no files of its own, and that is honest rather than a frontier
                     # claim. Everything this would change is already governed elsewhere:
                     # `.claude/skills/bmad-dev-auto/**` by mason's spec-fleet-stewardship,
                     # `scripts/deferred_work_check.py` and `pyforge/doctor/sources/` by
                     # doctor's own station spec. A glob matching nothing is silent by design.
companions: []
sources:
  - ../../../../../../docs/dreams/deferred-work-visibility.md
open_questions:
  - "Who owns which half? The detector half looks like Doctor's — Epic 6 spent six stories re-homing exactly these verdicts. The emitter half looks like Marshal's — it owns loop orchestration and the `bmad-dev-auto` skill. Splitting one effort across two stations needs deciding rather than assuming."
  - "Are all 470 worth keeping? They accumulated unseen, so some may be stale, duplicated, or already resolved. Grandfathering wholesale preserves noise as well as signal; triage may be cheaper than it looks, or may be a second effort."
  - "Does the emitter assign ids, or does promotion? Minting at defer time makes Tier-3 self-describing; minting at promotion keeps id-generation in one place. Marshal Story 4.13 already automated promotion — which argues for the second, except 4.13 promotes BY ID and so inherits the same blind spot."
  - "Should the tracked ledger's own anonymous entries red at the same severity? `_anonymous()` already reports them there as `ledger-entry-unidentified`. If Tier-3 gains the same check, the two sides should agree on severity rather than drift apart."
---

## Why

`deferred_work_check` exists to guarantee one thing: that work a review pass chose to defer
reaches a **tracked, durable ledger** rather than dying in a gitignored Tier-3 file no clone
will ever have. It reports `OK: every Tier-3 deferral has a tracked twin` and exits 0.

It cannot see **470 of them**.

`_DW_RE` (`scripts/deferred_work_check.py:71`) harvests `DW-*` ids from the Tier-3 file and the
tracked ledger and compares those two **sets**. `bmad-dev-auto`'s mandated defer format
(`.claude/skills/bmad-dev-auto/step-04-review.md`) writes bare `- source_spec:` bullets with
**no id at all**, so anonymous entries land in neither set and are never compared — while the
identified ones all do have twins, so the comparison passes and the detector reports success.

Measured with the detector's own `_anonymous()` parser rather than a grep (a grep over
`source_spec:` bullets overcounts, because identified entries contain that field too):

| marshal | doctor | steward | atlas | warden | herald | mason | scribe | **total** |
|---|---|---|---|---|---|---|---|---|
| 202 | 72 | 56 | 54 | 41 | 26 | 13 | 6 | **470 anonymous / 33 identified** |

The finding came from marshal story 4-14's own review pass and was proven **by execution, not
inference**: `grep -c 'spec-4-14-…'` on Tier-3 returns 11, `grep -c '4-14'` on the tracked
ledger returns 0, and the detector still prints `OK`.

## Capabilities

- **CAP-1 — a deferral carries identity from birth.**
  - **intent:** A review pass that defers something produces an entry bearing an id under the
    **owning station's own convention**, never a fleet-wide imposition.
  - **success:** a newly damped story leaves a Tier-3 entry whose id matches that station's
    existing scheme — `DW-FU-<story>` for doctor/atlas/marshal/warden, `DW-<story>-<n>` for
    mason — and no `bmad-dev-auto` run creates a new anonymous entry.

- **CAP-2 — the detector sees what it claims to check.**
  - **intent:** Anonymous Tier-3 entries are reported rather than silently skipped, so "every
    Tier-3 deferral has a tracked twin" means *every* deferral.
  - **success:** deleting an id heading from a Tier-3 entry **reds** the detector — demonstrated
    by mutation, the same proof standard `_anonymous()`'s own docstring already records for the
    tracked side.

- **CAP-3 — the existing 470 do not red every landing pass on day one.**
  - **intent:** The backlog that accumulated while the detector was blind is baselined, and the
    gate bites on what is **new**.
  - **success:** after the detector learns the anonymous shape, a landing pass is green on an
    unchanged repo, and adding a single anonymous entry reds it.

## Constraints

- **Both sides move, and the order is load-bearing.** Emitter first (`bmad-dev-auto` writes
  ids — stops producing invisible entries, reds nothing), detector second **with a baseline**.
  Detector-first turns one green check into 470 findings overnight; every landing pass fails
  and the realistic outcome is the finding gets suppressed — strictly worse than today, because
  then it is suppressed *and* invisible. Emitter-only stops the bleeding but leaves all 470
  permanently unseeable.
- **Half the machinery already exists and is already hardened — do not rewrite it.**
  `_anonymous()` parses exactly this shape, and its docstring records this same vacuity class
  being caught once before and fixed by mutation testing. It is called on the **tracked** ledger
  only, never on Tier-3. The gap is one call plus a finding kind.
- **Follow the in-house grandfathering precedent.** `spec-pyforge-warden` already ships
  baseline-and-grandfathering for exactly this shape: a real gate that would otherwise red on a
  large pre-existing backlog. Do not invent a second mechanism.
- **The detector half must not be written against the shim.**
  `scripts/deferred_work_check.py` is one of the eight shims doctor story 6-9 **deletes**
  (confirmed on its branch: `D scripts/deferred_work_check.py`); its logic moves into
  `pyforge.doctor.sources`' `REGISTRY`. A fix written against the shim is work thrown away, so
  the detector half belongs in Doctor's `sources/` — after, or deliberately alongside, the 6-9
  rewiring.
- **Station id conventions are deliberate and survive.** doctor/atlas/marshal/warden use
  `DW-FU-<story>`; mason uses `DW-<story>-<n>`. Whatever ships respects each station's own
  precedent rather than normalising them.

## Non-goals

- **Not a rewrite of the deferral format.** The existing entries carry real content; only
  identity is missing.
- **Not a change to what gets deferred.** Review passes decide that. This is about durability
  of the record, not the decision.
- **Not a fleet-wide id convention.** The per-station difference is deliberate.
- **Not coupled to landing 6-9.** The ordering constraint is real, but this Spec does not force
  that landing's timing.
- **Not a triage of the existing 470.** Whether they are all worth keeping is an open question
  above, and possibly its own effort.

## Success signal

A story defers something, and the entry it leaves behind is visible to the detector that exists
to protect it. Deleting that entry's id reds a landing pass. The count of invisible deferrals is
zero and stays zero — not because someone swept the backlog, but because nothing new can be
created without an identity.
