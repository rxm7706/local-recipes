# The fidelity stack

## What holds each boundary today

| Boundary | Held by | Reverse check |
|---|---|---|
| Dream → Spec | `dream_chain_check` INV-0/INV-1 | ✅ green today |
| Spec → owning project | INV-2 | ✅ |
| Spec → planning chain | INV-3 (shape only) | ❌ shape is not content (CAP-5) |
| Spec ↔ governed surface | `spec_surface_check`, `bmad-drift-check` | ⚠️ forward only |
| **Story spec → shipped story** | **nothing** | **nothing** (CAP-2, CAP-3) |
| Shipped story → delivery record | nothing (row 8) | nothing |
| Run → durable ledger | nothing (row 9) | nothing |
| Charter → everything below it | prose | nothing (CAP-9) |

Every layer in this table is declarative — each compares a document to a
document. What actually happened at runtime (did the gate fire, was it
skipped, who overrode it) appears nowhere, because the factory has no
observation plane. That absence is CAP-6's gap, and it is why the stack
cannot currently close its own reverse direction.

## Disposition of the three source-essay concepts

Three ideas from the provoking essay (see `SPEC.md` → `sources:`), each
dispositioned as *already held* or *added*, plus the two questions the
essay's artifact-centric model has no vocabulary to ask.

| Concept | Status | Station | Mechanism |
|---|---|---|---|
| Spec as a stack layer | held; measurement missing | Marshal | CAP-5 |
| Privileged layer fallacy | rejected for authorization, already honoured for origination | Marshal | CAP-8 |
| Resolution trap | open at the widest gap | Marshal builds · Doctor judges · Scribe records | CAP-2 + CAP-3 + CAP-4 |
| *(blind spot)* who may weaken a gate | ratified, unenforced | Doctor over Marshal | CAP-9 |
| *(blind spot)* who can still read the verdict later | unowned | Scribe | CAP-6 |

**Spec as a stack layer.** The Charter already frames the PRD→architecture→
epics chain as the Spec's decomposition, not a substitute for it, and the
kernel/companion rule gives a testable cut line: companions hold tables, the
kernel holds the compressed normative sentence, and a companion that argues
rather than enumerates has drifted into being a second kernel. INV-3 checks
only that the chain has the right shape (`prds/`, `architecture/`,
`epics.md` exist in the sharded form) — not that a PRD actually decomposes
*this* Spec, or that a companion is still reachable from the kernel claim it
supports. CAP-5 closes that gap.

**The privileged layer fallacy, split in two.** The essay rejects a fixed
originating layer and prescribes choosing one per change. The factory splits
that into two different questions and answers them oppositely: authorization
is privileged, permanently (Dream-first is mandatory and always-on — an
unattended factory writing code at 4am needs something to hold intent still,
so a floating fixed point is unsafe); origination is not privileged, and
never was (`bmad-drift-check` already fires `surface-changed` on an
out-of-band edit and reconciles it — the essay's reverse check has been
running here for months). What is genuinely missing is CAP-8: a recorded
fixed point per reconciliation, so the decision of which layer owned truth
for a given change is adjudicable rather than argued.

**The resolution trap, and it is ours specifically.** The spec→code gap is
deliberately wide by design (the Spec is five fields; over-specification is
the failure mode the essay itself names). The story spec is the factory's
gap-narrowing device — the intermediate layer that turns one large
spec→code jump into two reviewable ones — and it is precisely the layer with
no gate. A lost story spec is not bookkeeping; it is the resolution trap
arriving exactly where the theory predicts, at the layer whose job was to
keep the gap crossable. CAP-2/CAP-3/CAP-4 close it; Doctor and Scribe are
named co-owners because Marshal builds the detector but may not also be the
sole judge of its own largest debt (CAP-9) or the sole keeper of the
resulting record (CAP-6).
