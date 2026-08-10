---
title: A deferral that nobody can see is a deferral that never happened
type: dream
owner: doctor
status: dreamt
---

# A deferral that nobody can see is a deferral that never happened

## The Dream

`deferred_work_check` exists to guarantee one thing: that work a review pass chose to defer
reaches a **tracked, durable ledger** instead of dying in a gitignored Tier-3 file that no
clone will ever have. It reports `OK: every Tier-3 deferral has a tracked twin` and exits 0.

It cannot see **470 of them**.

The dream is that the guarantee is real — that "every deferral has a tracked twin" means every
deferral, not every deferral that happens to carry an id.

## What is real

**The measurement, taken with the detector's own parser** (`_anonymous()`, 2026-08-10) — not a
grep, because a grep over `source_spec:` bullets overcounts by including the fields inside
identified entries:

| station | ID'd | anonymous |
|---|---|---|
| marshal | 12 | 202 |
| doctor | 4 | 72 |
| steward | 1 | 56 |
| atlas | 12 | 54 |
| warden | 2 | 41 |
| herald | 1 | 26 |
| mason | 1 | 13 |
| scribe | 0 | 6 |
| **total** | **33** | **470** |

**The mechanism.** `_DW_RE` (`scripts/deferred_work_check.py:71`) harvests `DW-*` ids from the
Tier-3 file and the tracked ledger and compares those two **sets**. `bmad-dev-auto`'s mandated
defer format (`.claude/skills/bmad-dev-auto/step-04-review.md`) writes bare `- source_spec:`
bullets with **no id at all**. Anonymous entries therefore appear in neither set and are never
compared; the identified ones all do have twins, so the comparison passes and the detector
reports success.

**Proven by execution, not inference** — the finding came from story 4-14's own review pass,
which recorded the commands: `grep -c 'spec-4-14-…'` on Tier-3 returns 11, `grep -c '4-14'` on
the tracked ledger returns 0, and `deferred_work_check.py` nonetheless prints `OK` and exits 0.

**Half the machinery already exists, and is already hardened.** `_anonymous()` parses exactly
this shape, and its docstring records this same vacuity class being caught once before and
fixed by mutation testing — *"an earlier version latched `seen_id` true until the next heading,
which made it unable to see an anonymous entry in any file that had at least one id… proved by
mutation: deleting an id heading did not red the detector."* It is called on the **tracked**
ledger only, never on the Tier-3 file.

**A grandfathering precedent exists in-house.** `spec-pyforge-warden` already ships
baseline-and-grandfathering for exactly this shape of problem: a real gate that would otherwise
red on a large pre-existing backlog.

## What it looks like when real

- A review pass defers something and the entry carries an identity from birth, under the
  station's own convention — `DW-FU-<story>` for doctor/atlas/marshal/warden, `DW-<story>-<n>`
  for mason. The convention is the station's, not a fleet-wide imposition.
- `deferred_work_check` sees anonymous Tier-3 entries and says so.
- The 470 that already exist do not red every landing pass on day one. They are baselined, and
  the gate bites on what is **new**.
- The count of invisible deferrals goes to zero and stays there, because nothing new can be
  created without an id.

## The shape of the answer

Both sides move, in order. **Neither alone is sufficient, and the ordering is not arbitrary:**

1. **The emitter first.** `bmad-dev-auto` writes ids. This stops producing invisible entries
   and reds nothing.
2. **The detector second, with a baseline.** `_anonymous()` is called on the Tier-3 file too,
   the existing 470 are grandfathered, and the gate applies to new entries.

Detector-first would turn one green check into **470 findings overnight**. Every landing pass
would fail, and the realistic outcome is that the finding gets suppressed — strictly worse than
today, because then it is suppressed *and* invisible. Emitter-only stops the bleeding but
leaves all 470 permanently unseeable.

## The ordering constraint that decides where the code goes

**`scripts/deferred_work_check.py` is one of the eight shims doctor story 6-9 deletes.** Its
logic moves into `pyforge.doctor.sources`' `REGISTRY`. Confirmed against 6-9's branch:
`D scripts/deferred_work_check.py`.

So a fix written against the shim is **work thrown away**. The detector half belongs in
Doctor's `sources/`, which places it after — or deliberately alongside — the 6-9 rewiring the
operator has chosen to land on purpose rather than as a side effect.

## Why this is not just a fix

It is cross-station (all eight ledgers), it changes a skill file every future story uses, it
needs a grandfathering decision, and it has a hard ordering dependency on another story's
landing. That is a contract, not a patch.

## Open questions

- **Who owns which half?** The detector half looks like Doctor's — Epic 6 has spent six stories
  re-homing exactly these verdicts. The emitter half looks like Marshal's — it owns loop
  orchestration and the `bmad-dev-auto` skill. Splitting one effort across two stations needs
  deciding rather than assuming.
- **Are all 470 worth keeping?** They accumulated unseen. Some may be stale, duplicated, or
  already resolved. Grandfathering them wholesale preserves noise as well as signal; triage may
  be cheaper than it looks, or may be a second effort.
- **Does the emitter assign ids, or does promotion?** Ids could be minted by `bmad-dev-auto` at
  defer time, or by the promotion step that moves an entry into the tracked ledger. The first
  makes Tier-3 self-describing; the second keeps id-minting in one place. Marshal Story 4.13
  already automated the promotion step, which argues for the second — but 4.13 promotes by id,
  so it inherits the same blind spot.
- **Should the tracked ledger's own anonymous entries red too?** `_anonymous()` already reports
  them there. If Tier-3 gains the same check, the two sides should agree on severity.

## Non-goals

- **Not a rewrite of the deferral format.** The existing entries carry real content; only
  identity is missing.
- **Not a change to what gets deferred.** Review passes decide that; this is about durability
  of the record, not the decision.
- **Not a fleet-wide id convention.** Stations already differ (`DW-FU-<story>` vs
  `DW-<story>-<n>`) and that difference is deliberate. Whatever ships must respect the
  station's own precedent.
- **Not coupled to landing 6-9.** The ordering constraint is real, but this Dream does not
  force that landing's timing.

## Realization log

- **2026-08-10** — Seeded from a finding in marshal story 4-14's review pass, which proved the
  blind spot by execution rather than inference. Measured fleet-wide with the detector's own
  `_anonymous()` parser (470 anonymous vs 33 identified) after an initial grep estimate was
  identified as an upper bound and discarded. Operator asked for the Dream explicitly, on the
  grounds that repo tooling deserves a chain rather than a patch smuggled into a landing pass.
