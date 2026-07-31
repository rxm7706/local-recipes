---
title: Fidelity enforcement — a contract is only a contract if something fails against it
type: dream
owner: marshal
status: dreamt
---

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
ledger, the layout README — are written down and enforced by nothing. All
eight detector scripts were checked; the only matches are comments.

Row 7 is the one with a body count. Story specs are drafted by bmad-loop into
gitignored Tier-3 and become durable only if a human promotes them after
merge. Across the fleet today: **125 stories done, 73 story specs tracked.**
The gap is **~52** — and *approximately* is the point. Nothing derives that
number, so this Dream cannot state it exactly without violating
`EXEMPLAR-STANDARD`'s own provenance rule 3, *derive counts; do not restate
them*. A Dream that has to hand-count its own evidence is the argument.

The sharper evidence is that **hand-repair does not hold.** Warden and Atlas
are the two stations whose story specs were reconstructed by hand after real
losses — warden lost 13 of 31 to worktree teardown, atlas has 2 of 32
originals left. Both were repaired. Both have **drifted again since**
(warden 31 tracked against 43 done; atlas 36 against 57), because the repair
added artifacts and never added a gate. Six stations were never repaired at
all: mason and steward hold **zero** story specs against 4 and 3 shipped.

## The fidelity stack — the boundaries, and what holds each today

| Boundary | Held by | Reverse check |
|---|---|---|
| Dream → Spec | `dream_chain_check` INV-0/INV-1 | ✅ green today |
| Spec → owning project | INV-2 | ✅ |
| Spec → planning chain | INV-3 (shape only) | ❌ shape is not content |
| Spec ↔ governed surface | `spec_surface_check`, `bmad-drift-check` | ⚠️ forward only |
| **Story spec → shipped story** | **nothing** | **nothing** |
| Shipped story → delivery record | nothing (row 8) | nothing |
| Run → durable ledger | nothing (row 9) | nothing |
| Charter → everything below it | prose | nothing |

The bottom half of that table is the work.

One property of the whole table is easy to miss: **every layer in it is
declarative.** Each states what *should* be true, so each check compares a
document to a document. What actually happened at runtime — did the gate fire,
was it skipped, who overrode it — appears nowhere, because the factory has no
observation plane. That absence is Scribe's leg of the triad below, and it is
why the stack cannot currently close its own reverse direction.

## Mapping the source concepts

Three ideas from the provoking essay, each dispositioned: the factory either
**already holds it**, or **adds it** — named station, named mechanism. Nothing
is left as agreement-in-principle.

### 1. The Spec is a layer in the fidelity stack — **HELD, extended**

The essay's stack (vision → spec → architecture → schema → code → build → runtime)
makes the Spec *one layer among many*, each compressing the one beneath, and
warns that a spec as detailed as its code has defeated itself.

The Charter already says this and says it harder. §2: *"the chain (PRD →
architecture → epics) is the Spec's **decomposition**, not a substitute for
it."* And where the source gives only a direction — *be coarser* — the
kernel/companion rule gives the cut line: **companions hold tables, the kernel
holds the compressed normative sentence, and a companion that argues rather
than enumerates has drifted into being a second kernel.** That is the
compression rule with a testable edge.

**But the layering is asserted, not measured.** INV-3 checks the *shape* of the
chain — that `prds/`, `architecture/`, `epics.md` exist in the 6.10 form. It
does not check that a PRD decomposes *this* Spec, or that a companion is still
reachable from the kernel claim it supports. Shape is not content.

> **Adds — Marshal.** The Spec↔chain reverse gate: every kernel Constraint that
> compresses an enumeration must resolve to a live companion, and every chain
> artifact must name the Spec it decomposes. `EXEMPLAR-STANDARD` rows 5 and 6
> already state both rules; neither has a detector. Extends
> `dream_chain_check` rather than adding a ninth script.

### 2. The privileged layer fallacy — **REJECTED IN HALF, and the half matters**

The essay rejects the doctrine that change must originate at the spec layer, and
prescribes choosing a fixed point *per change, not forever*.

The factory splits that single question into two, and answers them oppositely:

- **Authorization is privileged, permanently.** Nothing ships that is not
  authorized from Tier 0 — Dream-first is mandatory and always-on, and the
  Charter's chain reads forward as authorization. This is not adopted from
  the source and will not be. Its model assumes a human holds intent between layers;
  ours assumes bmad-loop is writing code unattended at 4am, where a floating
  fixed point means **nothing** holds intent still. `EXEMPLAR-STANDARD` already
  litigated the tasteful version and rejected it: *judgement calls drift, and
  the drift is invisible.*
- **Origination is not privileged, and never was.** A legitimate change may
  begin in the code and the contract catches up. This the factory already does:
  `bmad-drift-check` fires `surface-changed` on an out-of-band edit, and the
  reconciler skills re-ground the artifacts. The essay's reverse check — the half
  most teams skip — has been running here for months.

So the fallacy is real and we are not committing it; what looks like a
privileged layer is a privileged *authorization*, which is a different claim.

**What is genuinely missing is the declared fixed point itself.** When code and
contract disagree today, some agent silently decides which one was right. That
decision is load-bearing and unrecorded.

> **Adds — Marshal.** A recorded fixed point per reconciliation: which layer
> owned truth for this change, and why. Rides the existing memlog convention
> (append-only, re-rendered, never hand-patched), so a later reader can
> adjudicate rather than argue.

### 3. The resolution trap — **THE REAL GAP, and it is ours specifically**

The essay's argument, paraphrased: wide fidelity gaps harbor risk and narrow ones
enable trustworthy translation — and the spec→code gap is precisely where an LLM
sits, a non-deterministic translator filling a large gap with plausible judgment.

The factory's spec→code gap is **deliberately wide**. The Spec is five fields.
We do not narrow it, and we should not: over-specification is the failure mode
the essay itself names, and Charter §5 already proved the more important property —
when dev sessions died mid-story, *the beings were literally killed and the
stations held*. Our answer to non-determinism is not a repeatable translator but
a **disposable** one, backed by independent verdicts: the hand that builds is
never the gate that judges.

**That bet is currently unpaid at the widest gap in the system.** The story spec
*is* the factory's gap-narrowing device — the intermediate layer that turns one
enormous spec→code jump into two reviewable ones. It is precisely the layer with
no gate, and ~52 of them are missing. A lost story spec is not a bookkeeping
failure; it is the resolution trap arriving exactly where the theory predicts,
at the layer whose whole job was to keep the gap crossable.

> **Adds — Marshal builds · Doctor judges · Scribe records.** INV-4 (`done` ⇒
> tracked spec), automatic Tier-2 promotion in the loop, and the reverse gate
> binding each spec's Success signal to the verify command that gated it.
> Marshal owns the loop and the detector; per the 2026-07-28 ratification
> **Doctor holds the verdict on Marshal's own rows**, and marshal carries the
> largest row-7 debt of the six unrepaired stations — it may not re-threshold
> the check that measures it. **Scribe owns the record** the other two produce:
> a verdict nobody can retrieve six months later is not auditable, and the ~52
> lost story specs are that failure already realized — *knowledge is lossy; the
> graph is there; nobody writes it down* is the disease Scribe was chartered to
> cure.

### Disposition summary

| Concept | Status | Station | Mechanism |
|---|---|---|---|
| Spec as a stack layer | held; measurement missing | Marshal | Spec↔chain reverse gate (rows 5–6) |
| Privileged layer fallacy | rejected for authorization, already honoured for origination | Marshal | recorded fixed point per reconciliation |
| Resolution trap | **open at the widest gap** | Marshal builds · **Doctor judges** · **Scribe records** | INV-4 + auto-promotion + Success↔verify binding |
| *(the source's blind spot)* who may weaken a gate | **ratified, unenforced** | Doctor over Marshal | install the judge — approval marker, or package separation |
| *(the source's blind spot)* who can still read the verdict later | **unowned** | **Scribe** | rows 7–9 as one trace + the actor-attributed event record (who · what · when · how · why) |

The last two rows are not among the three ideas; they are the questions the
source's model cannot ask, because an artifact-centric framework has no station
to attach them to. They sit in this table because every row above them depends
on the answers, and today one answer is prose and the other is nobody.

## What is real

Eight detectors already run red on drift — `bmad-drift-check`,
`spec_surface_check`, `dream_chain_check`, `deferred_work_check`,
`dashboard_drift_check`, `story_status_check`, `loop_stall_check`,
`llms_full_check`. **Five of the eight shipped in the last three days**, which
is the encouraging half of the story: this factory *does* build gates once it
can see the hole. The machinery and the taste are present.

**The wiring is not, and this is the sharpest finding in the Dream.** Searched
exhaustively during review: **no workflow in `.github/` invokes any of the eight,
and no git hook does either.** `EXEMPLAR-STANDARD` says of the newest one that it
*"exits non-zero so it gates CI"* — it gates nothing, because nothing runs it.
Every detector in this factory is executed **by hand, by whoever remembers**.

That is the thesis in its purest form, one level beneath where this Dream started
looking. The conformance rows were unenforced because no detector covered them;
the detectors are unenforced because no trigger covers *them*. A gate nobody
invokes is exactly the artifact this Dream is named after — a rule that cannot
fail against anything, wearing the costume of one. It also explains the drift
pattern honestly: the eight run green in this repo not because drift is rare, but
because they run on the days somebody thinks to run them.

So the missing thing is not only coverage and direction. It is **the trigger** —
and that is the cheapest item on the frontier by a wide margin.

Seeding this Dream demonstrated the machinery on the spot: it moved
`dream_chain_check` from clean to **one open INV-1 finding against marshal** —
the contract that does not yet exist, named by a gate, on the accountability
row that owns it. That is the whole thesis executing on the document that
proposes it.

## The frontier

- **Wire the eight that already exist.** Before a ninth detector is written, the
  existing eight need a trigger — a CI job on every PR and push, and the honest
  admission on the board that until it exists their green means "last time a
  human ran them." Cheapest item here and the highest ratio of safety to work; it
  is also a precondition for every other item, since a new gate inherits the same
  nothing.
- **INV-4 — a shipped story has a tracked spec.** Story `done` in the ledger ⇒
  `specs/spec-<key>.md` on `main`. Mechanically checkable today; closes row 7;
  its absence has already cost real artifacts twice.
- **Promotion becomes automatic.** The loop's completion path writes Tier-2
  directly. A rule that requires a human to remember something after a merge is
  not enforcement — the ~52-story gap is the proof. The detector becomes the
  backstop, not the mechanism.
- **Reverse gates, not just forward ones.** A promoted story spec is currently a
  tracked file nothing ever fails against again. Bind each spec's Success signal
  to the verify command that gated it, so a later change that deletes the test
  is visible as a contract breach rather than a passing suite.
- **The record rows get a station.** Rows 7, 8 and 9 — story spec tracked,
  delivery record, durable ledger — are not three bookkeeping chores; they are
  one trace, and **Scribe is accountable for its completeness** even where
  Marshal builds the detector. Row 10 (layout README) rides along. Assigning
  them by craft rather than by which script happens to check them is what stops
  the record being everyone's job and therefore nobody's — which is exactly how
  ~52 story specs went missing while every gate stayed green.
- **The actor-attributed event record** — Scribe's leg, built at the seam where
  acts happen rather than where verdicts land, so a skipped gate and an override
  are recorded as loudly as a pass. Five fields, none optional: **who** (human or
  agent, and which), **what**, **when**, **how** (skill, tool, harness or direct
  edit), **why** (story, capability, or override justification). Durable by
  construction: today the only place `gates.mode` is captured per run is a
  `state.json` under `.gitignore:750`, so the fleet's entire unattended history
  is one worktree teardown from unauditable. **Not a new subsystem** — the event
  stream (`journal.jsonl`), the query engine (DuckDB, already proven by atlas's
  WASM read surface) and the capture seam (`pyforge-scribe/capture.py`) all
  exist and have simply never been joined.
- **The ungated boundary declares itself.** Where a tier genuinely has no gate,
  the detector reports it as *ungated* rather than passing in silence. A green
  board that only means "we didn't look here" is the false-green doctrine
  failing at the meta level.
- **The fixed point, declared per change.** Which layer owns truth for a given
  change is a decision the factory currently makes implicitly. Make it explicit
  and recorded, so "the code moved and the spec didn't" can be adjudicated
  instead of argued.
- **Install the judge.** *The control that makes every other gate on this list
  trustworthy, and the only one currently held by prose.* Charter §5 ratified on
  2026-07-28 that Marshal may not weaken, re-threshold or disable a check that
  judges Marshal — and nothing enforces it. The sole owner-scoped conformance
  code in the repo is `dream_chain_check.py`'s scoreboard, which *groups*
  findings by owner; it does not defend the separation. The consequence is
  concrete and lands on this Dream's own first deliverable: **INV-4 is a check
  Marshal builds, that measures Marshal's largest debt** — 6 of its 7 done
  stories carry no tracked spec. Marshal would ship the detector, set its
  threshold, and be its own biggest finding. That is the §7 inversion — a
  governance fault shipping while a cosmetic one blocks — reappearing one layer
  up. Two closures, cheapest first: **(a)** a check that fires when a threshold,
  skip-list or disable flag in a Marshal-owned detector moves without a
  Doctor-side approval marker; **(b)** structurally, the checks that judge
  Marshal live in Doctor's package with no Marshal write path. Until one ships,
  every verdict below it is self-graded.

### Invariants for the trigger

Recorded here rather than in a plan, because they are the parts that do not
regenerate: the detector inventory, the run timings and the repo/runtime split
are all derivable from the tree at any moment, and were derived to reach these.
The choices are not.

1. **One derived registry, never a second list.** Enumerating detectors by hand
   is what produced the present state — **eight scripts on disk, seven pixi
   tasks, three rows on the board, zero in CI**, with the newest detector
   missing from two of the three. A hand-written list omits exactly the newest
   thing. The registry is derived, and it **fails on its own gaps**: a detector
   script with no declaration, or a declared detector with no task, is a
   finding. `generate.py` already derives a task's command from `pixi.toml`
   *"never declared twice"*; the list above it is hand-typed, and that is the
   whole bug.
2. **Each detector declares its own scope.** `repo` reads tracked files only and
   can run anywhere; `runtime` observes host state — Tier-3 feeds, tmux,
   `~/.bmad-loops` — and cannot run in CI at all. This is not a limitation to
   work around: it is the missing observation plane showing up as a deployment
   constraint. **The runtime detectors are the ones with nowhere to run.**
3. **A detector that cannot run reports `unknown`, never green.** Already the
   board's behaviour — *the strip never claims green it did not measure* — and
   promoted here to a rule binding every consumer of the registry.
4. **Advisory locally and in CI; the fleet is where it must bind.** *(Amended
   2026-07-31 — operator decision. The original read "blocking in CI and in the
   fleet".)* A local hook is per-clone, untracked and bypassable, so it was never
   a gate. CI is now **also advisory** by choice: findings surface as warning
   annotations and never block a merge. Recorded as an amendment rather than
   quietly implemented, because it is a real concession against this Dream's own
   thesis — by the test in its first line, an advisory check is a plan. What it
   buys is that the suite runs *at all*, on every PR, which is a large step from
   nothing; what it costs is that a red detector can still be merged past, which
   is exactly how PR #170 landed a `spec_surface_check` break. **The fleet's
   `[verify]` set therefore carries the whole binding weight** — and until it is
   wired, nothing in this factory can fail on a detector finding.
5. **Never a blocking `pre-commit`.** Every worktree — loop homes and per-story
   worktrees alike — resolves to the *same* `.git/hooks`. A blocking pre-commit
   fires inside unattended dev sessions that cannot interpret a detector
   failure, and would convert one red check into fleet-wide story loss.
   `pre-push` is the local seam.
6. **The fleet is the load-bearing consumer, not CI.** Most code here is written
   by bmad-loop, not by a human at a terminal and not in a pull request. Until
   the repo-scope detectors are in the harness `[verify]` set, the trigger
   covers the least of the three places work happens.

## Landing a gate on a factory that already violates it

Every gate on that list fails on contact with the existing estate. INV-4 switched
on today reds CI against ~52 shipped stories and blocks the whole fleet — which
is not a reason to soften it, but is a reason the Dream is unfinished without a
migration doctrine. [[pyforge-warden]] already solved this shape once, treating
*baseline and grandfathering* as a first-class v1 concern rather than an
afterthought, and the same three rules apply here:

- **Baseline the debt, never the rule.** Record the ~52 as a dated,
  enumerated exemption list — not a lowered threshold. A threshold that moves is
  a rule nobody can appeal to afterwards; an exemption list is a backlog with an
  end.
- **The exemption list may only shrink.** Ratchet, checked. Anything not on the
  baseline fails from day one, so the gate is real for all *new* work
  immediately — which is where the leak actually is.
- **Grandfathering expires, and says when.** An exemption with no end date is a
  permanent hole wearing a temporary name. Charter §7 gated hard from day one on
  the reasoning that *a grace period on the critical path is how drift becomes
  permanent*; the record trace is on that path.

The honest consequence: fidelity enforcement lands **green on a factory that is
still ~52 specs in debt**, and says so on the board rather than hiding it — which
is the *ungated boundary declares itself* rule turned on our own migration.

## How we will know it worked

`regenerable-factory` has the regeneration drill. This Dream's equivalent, and
its success signal:

> **Delete a tracked story spec at random, and CI names it — by story key, to the
> accountable station — within one run. Then do the same to a verdict: skip a
> gate, and the record shows a skip rather than a silence.**

Two deletions, because the Dream has two halves. The first proves the declarative
gates close. The second proves the observation plane exists — and it is the one
the factory would fail today, which is why it is the signal worth stating.

## What this is not

[[regenerable-factory]] asks *does every line of code have a contract it can be
rebuilt from* — coverage, forward. Fidelity enforcement asks *does anything go red
when a contract and its artifact disagree* — enforcement, both ways. One noun,
one job: the first builds the chain, the second is why the chain holds. They
share a detector surface and must not share a scope.

## The Charter amendment it drives

Lexicon **§2 The Spec** defines the unit of contract but never says what makes
one binding. §7 already contains the missing sentence, scoped to the Guildhall.
The amendment generalizes it: a Spec is the unit of contract **because
something fails against it**, and an unenforced contract is a plan wearing a
contract's name. This is a codification, not an import — the factory has been
acting on this rule since the `check_render.js` inversion was corrected; it has
simply never been written where it binds everything.

**A second clause, because the first is unsafe without it.** Per the 2026-07-28
ratification Marshal owns the detectors and the loop, so **Doctor holds the
verdict on Marshal's own rows** — marshal carries the largest row-7 debt of the
six unrepaired stations, and may not re-threshold the check that measures it.
**That separation is today ratified and unenforced** (see § The frontier,
*install the judge*): it is an assumption this Dream depends on, not a property
it inherits. Amending §2 to require that contracts be enforceable, while the rule
governing *who may weaken an enforcement* remains prose, would generalize the
letter of §7 and leave its lesson behind.

**A third clause — the audit triad**, set out below, because a Charter that names
who builds and who judges but not who *records* cannot deliver the backward trace
it already promises.

### The audit triad — **Marshal builds · Doctor judges · Scribe records**

The Charter says the chain reads both ways: **forward as authorization**,
**backward as audit**. The forward direction has an owner — the Execution
Doctrine names Marshal outright. The verdict got one on 2026-07-28, when Doctor
was given Marshal's conformance row. **The backward direction has never had
one.** Scribe is chartered for precisely it — *capture the decision, keep the
graph, answer from memory* — and was never wired into the enforcement model.

That omission has a cost already on the books. A verdict nobody can retrieve six
months later is not auditable, and the backward trace the Charter promises —
*Guildhall → verdict → Smith → Guild → Spec → Charter* — is only traversable if
something durable holds each hop. Fifty-odd story specs are missing from that
trace right now. Every gate stayed green throughout, because the gates check
whether work *happened*, and nobody was accountable for whether it stayed
**findable**.

So the triad, and it is one separation of powers rather than three roles:
**Marshal builds** (execution), **Doctor judges** (verdict), **Scribe records**
(audit). It is the same discipline §5 already applies — *the hand that builds is
never the gate that judges* — carried one step further: **the hand that judges
is never the sole keeper of the judgement.** Two stations can collude by
accident; three cannot lose the evidence quietly.

**Scribe records events, not outcomes.** This is the whole load of the third
leg, and it is easy to build wrong. A record written *by the verdict* is
worthless for audit, because skipping the verdict then also erases the evidence
that it was skipped. The record must be written by **the act** — everything an
agent makes or does — so the three cases a naive design silently drops are
exactly the three it captures:

1. **The judging run that never happened.** A gate not run must appear in the
   record as *not run*, never as absence. An unrecorded skip and a clean pass
   are the same shape, and telling them apart afterwards is impossible.
2. **The override.** Who bypassed which gate, on what authority, for which
   artifact. An override is a legitimate act; an *unrecorded* override is the
   failure. Standing overrides count: the fleet runs `gates.mode = "none"`, and
   no durable artifact records that any given story shipped under it.
3. **The act that produced nothing.** Crashes, timeouts, abandoned branches,
   dialogs nobody answered. Work that failed to happen is evidence.

The governing rule, which is the never-false-green doctrine moved up one layer:

> **An absent record and a clean record must never look the same.**

This is not speculative; it is the last 48 hours. A story sat **74 minutes** on
a consent dialog while `status` read `dev-running`, because the dialog reached
the tmux pane and never the log. Two dev sessions died mid-thinking with **no
error text**. Three stories were marked `done` by a DEV pass that a failed
review never overturned. And 1,102 lines survived only as a **dangling commit**,
one `git gc` from gone. Four incidents, one shape: *the system did something and
nothing durable recorded it.*

Durability is half the requirement and currently the missing half. The run
record — `journal.jsonl`, `events`, the `state.json` policy snapshot that is the
only place `gates.mode` is captured per run — lives under `.bmad-loop/runs/`,
which is **gitignored** (`.gitignore:750`). It is Tier-3: it dies with the loop
home. Scribe's leg is not satisfied by writing more; it is satisfied when what
is written **outlives the worktree that wrote it**.

### Who did what, when, how, and why

A record with no actor is a log, not an audit trail. There are **at least two
classes of actor** in this factory — the **human** and the **agent** — and the
same act means different things depending on which one performed it:

> A human editing a spec directly is **governance**. An agent editing a spec
> directly is **drift**.

That asymmetry is the Charter's own: the mission says the human governs *intent*
while agents deliver, so a human override is the legitimate exercise of
governance and an agent override is a gate failure. A record that cannot tell
them apart cannot distinguish the system working from the system escaping. Five
fields, and none is optional:

| | |
|---|---|
| **who** | actor **class** (human · agent) and identity — for an agent: station, model, session; for a human: the operator |
| **what** | the act and the artifact it touched |
| **when** | timestamp, ordered against the run |
| **how** | the means — which skill, tool or command; loop-driven, interactive, or a direct edit outside the harness |
| **why** | the authority — story key, Spec capability, or the stated justification for an override |

**Today none of the five survives durably, and one is deliberately erased.**
`git blame` attributes to the *committer*, not the actor: an agent-written commit
and a human-written commit both read `rxm7706`. This repo's own convention
removes AI attribution from commit messages and PR bodies — which was the right
call for the wrong artifact. Commit trailers were never the correct home for
provenance; they put a structured fact into prose, where it is noise to every
reader and queryable by none. **The remedy is not to restore the trailer.** It is
that provenance belongs in Scribe's record, where it is structured, queryable,
and out of the commit message entirely.

This Dream is its own witness. Its § Provenance was hand-edited by the operator;
the rest was drafted by an agent. Nothing in the file, the diff, or the eventual
commit will say so. A future reader cannot tell which sentences carry human
authority and which carry an agent's — in a document whose entire subject is
knowing that.

### The record is inclusive of runtime telemetry

Scribe's record spans two modes, and the second is the one this factory does not
have. The **curated** mode is Scribe's existing charter — decisions, ADRs, the
knowledge graph, *why* the system is the way it is. The **runtime** mode is
telemetry: an event stream, **queried** rather than read, answering *what the
system actually does*. Inclusive, not either/or — and they join at *why*, which
is the difference between an audit trail and a log.

The distinction is load-bearing because of where it sits in the stack. **Every
other layer is declarative** — Dream, Spec, chain, story spec, code all state
what *should* be. Telemetry is the only layer that states what **was**. So the
reverse direction this whole Dream is about ultimately terminates in observation,
not in another document: you can diff a spec against a spec statically, but *did
the gate actually fire · did an agent actually do this · was it skipped · who
overrode it* are answerable only empirically. **A fidelity stack with no
observation plane can only ever check documents against documents.**

That also fixes the artifact. Telemetry is not markdown. It is structured
events with a query surface and a retention policy — which is why "Scribe writes
it down" was always an under-specification of the third leg.

**The substrate already exists in three places and has never been joined:**

| Piece | Where it already is | What it lacks |
|---|---|---|
| the event stream | `journal.jsonl` — already emits `{ts, kind, run_id, story_key, adapter_dev, adapter_review}` | actor **class** and **authority**; and it is Tier-3 (`.gitignore:750`) |
| the query engine | `duckdb >=1.5.5` in `pixi.toml`; atlas already ships a **DuckDB-WASM read surface** | nothing — the pattern is proven in-repo |
| the capture seam | `pyforge-scribe`: `capture.py`, `models.py`, `promote.py` | built for curated decisions, not runtime events |

So the ask is not "build observability." It is: **join three things that exist,
add the two missing fields, and make the result outlive the worktree.** That is a
markedly smaller frontier than it first reads as — and the reason it has not
happened is the one this Dream keeps finding, that nothing fails when it doesn't.

## Provenance

Provoked by an external essay on spec-driven development, read 2026-07-31. Its
argument, paraphrased: a specification earns the name only when something can
fail against it automatically on every change — otherwise it is a prompt with
ambitions. *(Paraphrased deliberately. The source is not named here, at the
operator's decision, and quoting an identifiable author verbatim while withholding
attribution is worse than either naming them or restating the idea in our own
words. The idea is what this Dream uses; the sentence belongs to whoever wrote
it.)* Its fidelity-stack framing names the layered-compression model this Dream
borrows;
§ *Mapping the source concepts* dispositions the three ideas taken from it, and
is the authoritative record of what was adopted, adapted, and refused.

One structural limit of the source, recorded because it is the reason this
Dream is **Charter-bound rather than merely a detector backlog**: its model is
artifact-centric and has no vocabulary for *who may weaken a gate*. That
question — answered here by Charter §5, and by Doctor holding the verdict on
Marshal's rows — is not a refinement of the source's framework. It is the part
an autonomous factory cannot run without, because a system that can edit its
own gates has no gates.

## Kinships

The audit triad, in order: [[pyforge-marshal]] (builds — owns the loop that must
promote and the detectors) · [[pyforge-doctor]] (judges — holds the verdict on
Marshal's row) · [[pyforge-scribe]] (records — the record that dies on teardown
is the disease it was chartered to cure).

Then: [[regenerable-factory]] (coverage, to this Dream's enforcement) ·
[[team-memory]] (the durable trace Scribe's leg resolves to) · [[pyforge-warden]]
(never-false-green, applied to our own board) · [[factory-console]] (§7, where
this law was first discovered) · [[pyforge-charter]].

## Realization log

- **2026-07-31** — Dream seeded (operator call). Owner **marshal** by the
  cross-cutting-practice precedent ([[agent-tool-surface]],
  [[agent-portability]], [[agentic-sdlc-autonomy]]); scope set to the **full
  fidelity stack** — every tier boundary gated bidirectionally, not the
  story-spec row alone. Measured at seeding: 125 stories done, 73 story specs
  tracked, conformance rows 7–10 enforced by nothing.
- **2026-07-31** — **the audit triad named** (operator call): *Marshal builds ·
  Doctor judges · **Scribe records***. Recorded as a Dream-level decision because
  it is larger than this Dream: the Charter's chain reads backward as audit and
  that direction has never had an accountable station, though Scribe was
  chartered for it. Extends §5's *the hand that builds is never the gate that
  judges* with **the hand that judges is never the sole keeper of the
  judgement**. Consequence for scope: conformance rows 7–9 are reclassified from
  three bookkeeping checks into **one record trace accountable to Scribe**, even
  where Marshal builds the detector. Should be carried into Charter §5 by
  amendment, not left resident in a Dream.
- **2026-07-31** — **Scribe's leg scoped to events, not outcomes** (operator
  call): the record captures *everything an agent makes or does*, so a judging
  run that never happened and an override that did are both recorded — governed
  by *an absent record and a clean record must never look the same*. Extended
  the same day to **actor attribution**: at least two classes act here, human and
  agent, and the record must carry **who · what · when · how · why**, because a
  human editing a spec directly is governance while an agent doing it is drift.
  Verified at the time of the decision: the run record (`journal.jsonl`,
  `events`, the `state.json` holding the only per-run `gates.mode`) is Tier-3
  under `.gitignore:750`, and `git blame` attributes to the committer, so **none
  of the five fields survives durably today**.
- **2026-07-31** — **Scribe's record declared inclusive of runtime telemetry**
  (operator call): queried observability answering *what the system actually
  does*, alongside — not instead of — the curated knowledge graph answering
  *why*. Reclassifies the third leg from a document tier to an **observation
  plane**, which is the only non-declarative layer in the fidelity stack and
  therefore the only place its reverse direction can terminate. Survey at the
  time of the decision: the substrate exists unjoined — `journal.jsonl` already
  emits typed events, `duckdb >=1.5.5` is in `pixi.toml` with atlas's DuckDB-WASM
  read surface as the proven pattern, and `pyforge-scribe` already has a capture
  seam built for decisions rather than events.
- **2026-07-31** — **independent review before commit.** Fixed three defects: a
  pronoun surviving de-identification, a count stated flatly four times after the
  text argued it could only be approximate (now `~52` throughout), and an
  amendment clause orphaned from the section it modified. Added the two missing
  contracts a reviewer would ask for and `bmad-spec` will require: a **migration
  doctrine** (baseline the debt not the rule; ratchet-only; grandfathering
  expires) and a **success signal** (delete a story spec and a verdict; CI must
  name both). Resolved the citation question by **paraphrasing** the source's
  argument rather than quoting it unattributed. *Deferred:* this file is ~3.5×
  the longest peer Dream and holds mechanism detail belonging in the Spec — the
  trim happens once `bmad-spec` gives that detail somewhere to land, so nothing
  is dropped before it has a home.
- **2026-07-31** — **the detectors themselves are untriggered** (found during the
  same review, and it corrects a claim made earlier in the session). An
  exhaustive search of `.github/` and the git hooks found **no automatic invoker
  for any of the eight** — so committing this Dream does *not* red CI on its
  INV-1 finding, because no CI job would see it. `EXEMPLAR-STANDARD`'s "exits
  non-zero so it gates CI" describes an intent, not a wiring. Recorded rather
  than quietly fixed: it is the Dream's own thesis one level lower down — the
  conformance rows are unenforced because no detector covers them, and the
  detectors are unenforced because no trigger covers the detectors. *Wire the
  eight* is now the first frontier item, ahead of INV-4.
- **2026-07-31** — **the trigger shipped, advisory** (operator decision). Nine
  detectors now run on every PR and push to `main` via
  `.github/workflows/detectors.yml`, discovered by a derived registry
  (`scripts/detectors.py`) that fails on its own gaps. **Findings warn, they do
  not block** — invariant 4 amended accordingly. First CI run proved the
  plumbing: all seven repo-scope detectors executed on bare python in 25s,
  including the headless-Chrome layout gate, and reported the one true open
  finding. Reconciled in the same change: the `spec_surface_check` drift that
  PR #170 introduced and merged unnoticed, which is the concrete cost of having
  had no trigger at all.
- **2026-07-31** — **six invariants recorded for the trigger** (§ The frontier),
  after the design for it was worked out conversationally and would otherwise
  have survived only in a session transcript — the precise failure this Dream
  is about, committed by the Dream's own author. Only the non-derivable
  decisions are recorded; the inventory, timings and repo/runtime split
  regenerate from the tree. Measured while deriving them: **8 detector scripts,
  7 pixi tasks, 3 board rows, 0 in CI**, all eight running in 0.4–0.9s
  (~4.2s total, so cost is not what kept them untriggered). Also found: three
  detectors are **red on `main` right now** — `spec-surface-check` broken by
  PR #170 itself (touched `docs/dreams/README.md`, governed by
  `spec-pyforge-genesis`, without moving its memlog) and merged green because
  nothing ran it; `dashboard-drift-check` transiently, against the live run;
  `dream_chain_check`'s INV-1, expected until the Spec exists.
