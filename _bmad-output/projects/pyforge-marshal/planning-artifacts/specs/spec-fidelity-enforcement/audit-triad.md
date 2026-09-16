# The audit triad

## Marshal builds · Doctor judges · Scribe records

One separation of powers, not three roles. The Charter's chain reads
forward as authorization (Marshal, named outright by the Execution
Doctrine) and backward as audit — a direction that has never had an
accountable station, though Scribe was chartered for exactly it: capture
the decision, keep the graph, answer from memory. Extends the discipline
Charter §5 already applies — *the hand that builds is never the gate that
judges* — one step further: **the hand that judges is never the sole
keeper of the judgement.** Two stations can collude by accident; three
cannot lose the evidence quietly.

Conformance rows 7–9 (story spec tracked, delivery record, durable ledger)
are reclassified under this triad from three separate bookkeeping checks
into **one record trace accountable to Scribe**, even where Marshal builds
the detector (CAP-2/CAP-3) that feeds it.

## Scribe records events, not outcomes

A record written *by the verdict* is worthless for audit — skipping the
verdict then also erases the evidence that it was skipped. The record must
be written by **the act**, so the three cases a naive design silently drops
are exactly the three CAP-6 captures:

1. **The judging run that never happened.** A gate not run appears in the
   record as *not run*, never as absence.
2. **The override.** Who bypassed which gate, on what authority, for which
   artifact. An override is legitimate; an *unrecorded* override is the
   failure. Standing overrides count too — the fleet runs
   `gates.mode = "none"`, and no durable artifact records which stories
   shipped under it.
3. **The act that produced nothing.** Crashes, timeouts, abandoned
   branches, dialogs nobody answered.

Governing rule: **an absent record and a clean record must never look the
same.**

## The four incidents that motivate CAP-6

Concrete, not speculative — all within one 48-hour window:

- A story sat **74 minutes** on a consent dialog while `status` read
  `dev-running`, because the dialog reached the tmux pane and never the log.
- Two dev sessions died mid-thinking with **no error text**.
- Three stories were marked `done` by a DEV pass that a failed review never
  overturned.
- **1,102 lines** survived only as a dangling commit, one `git gc` from
  gone.

One shape across all four: the system did something and nothing durable
recorded it.

## Who did what, when, how, and why

A record with no actor is a log, not an audit trail. At least two actor
classes exist here, and the same act means different things depending on
which performed it:

> A human editing a spec directly is **governance**. An agent editing a
> spec directly is **drift**.

That asymmetry is the Charter's own: a human governs *intent* while agents
deliver, so a human override is legitimate governance and an agent override
is a gate failure. Five fields, none optional:

| Field | Content |
|---|---|
| **who** | actor class (human · agent) and identity — station/model/session for an agent, the operator for a human |
| **what** | the act and the artifact it touched |
| **when** | timestamp, ordered against the run |
| **how** | the means — skill, tool, command; loop-driven, interactive, or a direct edit outside the harness |
| **why** | the authority — story key, Spec capability, or the stated justification for an override |

**None of the five survives durably today.** `git blame` attributes to the
*committer*, not the actor — an agent-written commit and a human-written
commit both read the same author. Provenance belongs in Scribe's structured
record, not a commit trailer (see `SPEC.md` → Non-goals).

## The substrate already exists in three places, unjoined

| Piece | Where it already is | What it lacks |
|---|---|---|
| the event stream | `journal.jsonl` — already emits `{ts, kind, run_id, story_key, adapter_dev, adapter_review}` | actor class and authority fields; and it is Tier-3 (`.gitignore:750`) |
| the query engine | `duckdb >=1.5.5` in `pixi.toml`; atlas already ships a DuckDB-WASM read surface | nothing — the pattern is proven in-repo |
| the capture seam | `pyforge-scribe`: `capture.py`, `models.py`, `promote.py` | built for curated decisions, not runtime events |

So CAP-6 is not "build observability." It is: join three things that
already exist, add the two missing fields, and make the result outlive the
worktree.

## Two modes, one record

Scribe's record spans a **curated** mode (its existing charter — decisions,
ADRs, the knowledge graph, *why* the system is the way it is) and a
**runtime** mode (telemetry — an event stream, queried rather than read,
answering *what the system actually does*). Inclusive, not either/or; they
join at *why*, which is the difference between an audit trail and a log.
Telemetry is the only layer in the fidelity stack that states what *was*
rather than what *should be* — every other layer (Dream, Spec, chain, story
spec, code) is declarative. A fidelity stack with no observation plane can
only ever check documents against documents.
