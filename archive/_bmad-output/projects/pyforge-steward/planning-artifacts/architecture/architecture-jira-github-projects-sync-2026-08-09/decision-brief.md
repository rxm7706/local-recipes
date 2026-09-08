# Two boards, one truth — the decisions, in plain terms

Companion to `ARCHITECTURE-SPINE.md`. The spine is the build contract; this explains what was
decided and what each choice costs, for anyone approving or operating it rather than building it.

---

## The problem the labels created

The intake document offers two architectures:

| | Mode A | Mode B |
|---|---|---|
| **Best for** | real-time updates, **zero hosting cost**, serverless | **scheduled batch**, audit trails, reporting |
| **Runs on** | GitHub Actions + Jira Automations | `dlt` + PostgreSQL |

The operator's requirement was *"batch cadence is fine, and I want no database and no
infrastructure."*

**That combination is in neither mode.** Zero-infrastructure sits in Mode A; batch cadence sits
in Mode B. Taking either label at face value would have forced a false trade — accept real-time
complexity you don't need, or accept a PostgreSQL instance you explicitly excluded.

## The resolution: separate the trigger from the transport

The two modes actually differ along **two independent axes** that the labels fused:

- **Transport** — how state is stored and moved (serverless fields, or a data hub)
- **Trigger** — what starts a run (a webhook, a schedule, or a human)

Once separated, the requirement stops being a trade. **The default is transport=serverless
with trigger=`schedule` — zero infrastructure, batch cadence — and `trigger=webhook` is a
fully supported opt-in** for adopters willing to run a receiver. Mode B stays opt-in too.

### Why this reads as two reversals in the memlog, and why the second one is different

The first cut defaulted the trigger to `schedule`, on the reading that batch latency was
acceptable and webhooks were complexity nobody had asked for. That was **reversed on explicit
instruction**: near-real-time is wanted.

It was then **reversed back**, and this time not on preference but on fact. Steward story 8-1's
dev session refused to build, raising an `intent_gap`, and verification against GitHub's own
documentation proved the webhook default was **not merely expensive but impossible as
written**: there is no `project_v2_item` / `projects_v2_item` event that can appear in a
workflow's `on:` block. The webhook is real, but it reaches a workflow only through an
**external receiver** — a GitHub App with org-level Projects read access, or a webhook
endpoint — which must then call `repository_dispatch`.

So `webhook`-by-default did not mean "real-time at zero infrastructure." It meant **every
adopter must host and credential a receiver** — precisely the cost the zero-infrastructure
floor existed to avoid. Near-real-time is not withdrawn; it is opt-in, and the Jira→GitHub
direction already used `repository_dispatch` correctly all along.

The decoupling survived both reversals, and it is worth keeping for two reasons that have
nothing to do with which default won. It is what lets **Mode B run scheduled** — the axis has
to exist for Mode B to be describable at all — and it is what lets a deployment **fall back to
a schedule** for recovery without a second implementation (see AD-9). It is also why this
correction moved **one value**, not a design.

### What the reversal costs, honestly

Webhook delivery is **at-least-once and unordered**. Choosing real-time reintroduces three
problems a schedule does not have: the same delivery can arrive twice, deliveries can arrive
out of order, and one can be dropped entirely.

These are handled by design rather than by defensive code in each story (AD-9). The engine
treats a webhook as *"this item may have changed"* — a wake-up, never a value source — and
re-reads both boards before converging. A duplicate delivery therefore changes nothing, a late
delivery about a superseded value converges to the current one, and a dropped delivery is
recovered by running the same code path on a schedule.

That is why the paradigm stayed a **reconciler** rather than becoming a propagation pipeline.
Propagation is fewer API calls per event, but it makes correctness depend on delivery order and
turns idempotence into dedupe state — which, under AD-2's no-sidecar-store rule, has nowhere
to live.

## What each choice costs

**Staying on the default** costs you no latency — that was the point of the reversal — but it
does cost you history: there is no queryable record of past syncs, because the systems hold
current state only. It also puts you on webhook delivery semantics, with the three
consequences described above.

**Opting into Mode B** costs you a PostgreSQL instance to host, back up, and secure. It buys
queryable sync history, uniform handling of arbitrary custom fields, and per-field sync
direction.

Migration is deliberately cheap: both transports implement the **same logical control plane**,
so a board synced under the default can move to Mode B without re-linking a single item. That
is the point of AD-3, and it is the invariant most likely to be eroded by a well-meaning
shortcut.

## The three questions the Spec left open

**Q3 — which mode?** Both. Default: serverless transport, **`schedule` trigger** — zero
infrastructure, batch cadence. `trigger=webhook` and Mode B are both opt-in. *(Operator decision
2026-08-09, then reversed to `webhook` on instruction that near-real-time was wanted, then
reversed back the same day when story 8-1 proved a webhook default cannot be zero-infrastructure
— see "Why this reads as two reversals" above.)*

**Q2 — which board wins a simultaneous conflicting edit?** **GitHub, per-field overridable.**

The tempting answer is last-writer-wins by timestamp. It was rejected because it makes
correctness depend on comparing clocks across two vendors' APIs — neither guarantees that, and
Jira Automation timestamps and GitHub webhook timestamps are not commensurable. A rule that is
*usually* right is untestable; a deterministic one is. GitHub is the default authority because
that is where the work happens and where this repo's build line already reads.

**Q4 — Mode B's schema shape?** **Normalized, with the three-table control plane.**

The flat single-table alternative's only advantage was a simpler diff view — and that advantage
now belongs to the default transport. A flat table cannot express per-field sync direction or
value translation, which are precisely the capabilities you would be paying Mode B's
infrastructure to get. If the flat view is all you need, that is a signal to stay on the
default rather than a reason to simplify Mode B.

## One defect you should know about before approving

GitHub's `updateProjectV2ItemFieldValue` updates the underlying data correctly but **can fail to
refresh the board view's grouping index**. A card moves logically while appearing stuck in its
old column until someone drags it.

This affects **both** modes — it is a vendor issue, not an architecture one. Data is never
wrong; the display can lag. Implementers must not treat a stale view as a failed write, and
should re-verify against GitHub's issue tracker at implementation time rather than assuming it
still reproduces.

## The mechanism that had to be replaced (amended 2026-08-10)

The first version of the loop guard asked *"has this item been touched since I last synced it?"*
by comparing the item's own last-modified time against a marker the engine wrote onto **that same
item**.

That cannot work, and not because of a tuning mistake. **Writing the marker is itself a
modification of the item**, so the item's last-modified time always ends up newer than the marker
the engine just wrote. Every reconcile after the very first one therefore concluded "both boards
changed", handed the item to the conflict rule, and let GitHub-wins quietly overwrite real
Jira-side edits.

A 30-second tolerance was tried. It does not help: both values are timestamps the *vendor*
recorded, not clocks that keep ticking, so the gap never closes. The misclassification is
permanent, not a window.

Story 8-1 found this over three review passes, **refused to ship it**, reverted its own work
rather than leave a half-fix in place, and stopped for this decision. That was the right call —
the flaw was in the contract it was building against, not in its code.

### What replaces it

**Compare values, not clocks.** The engine remembers the value each field was last synced to.
"Did this side change?" becomes "is it different from what I last recorded?"

The self-interference simply disappears: writing the bookkeeping field does not change the
*status* value, so the signal the guard reads is untouched by the write that broke the old one.

Two things get better as a side effect, and they are worth more than the fix itself:

- **A real conflict becomes detectable for the first time.** With a shared baseline, "both sides
  moved away from the same starting point" is a fact you can observe. The conflict rule was
  always written against that precondition; nothing before could actually supply it.
- **"No echo" becomes provable rather than timed.** After one propagation both boards match the
  baseline, so every later pass is a no-op no matter when it runs. That is what the success
  criterion asks you to demonstrate.

### What it costs

The engine stores a small map of last-synced values per item instead of a single timestamp.
Under the default transport that is one more bookkeeping field per side — no new infrastructure,
and the same place the design already keeps its state. If a board ever outgrows the vendor's
field-size limit, that is the documented signal to move to Mode B, not a reason to bolt on a
sidecar store.

### The other two options, and why not

Two alternatives were on the table.

**Per-field change signals** — ask each vendor "which *field* changed?" instead of "did the item
change?". Not wrong, and it survives as an optional speed-up, but it is not a peer of the chosen
fix: it makes the signal sharper, while the value comparison changes what the signal *is* and
removes the failure entirely. It also leans on a capability the two vendors expose very
differently — a property of GitHub's field objects, but only reconstructable from Jira's paginated
change history. Values, by contrast, are returned by both.

**Document a bounded data-loss window** and give the operator a "converged / may be pending"
indicator. Rejected twice over: the spec makes zero-loop non-negotiable and requires you to
*prove* it on demand, and the premise is false anyway — the loss is permanent, not bounded, so
there is no window to honestly document.

## What this does *not* decide

Deliberately left to the stories or to first use: the schedule interval, where Mode B's
PostgreSQL would run (nobody has opted in — deciding hosting for a mode with no user is
speculative), which fields sync beyond status/assignee/link, and whether Jira pushes or the
schedule pulls both sides.

## Status

Epic 8's five stories remain **unbuilt** — 8-1 back to `backlog` (PR #389), 8-2 through 8-5
blocked. Unblocking them is a separate operator call after this architecture is reviewed; the
architecture answers the questions, it does not authorise the build.

One thing must happen before 8-1 re-runs, and it is not optional: **story 8-1's intent contract
names the broken mechanism literally** ("compares each side's `updated_at` against its own
recorded sync point"). That contract has to be re-issued from AD-5's amendment. A dev session
cannot amend it locally, which is exactly why 8-1 halted instead of attempting a fourth repair —
re-running it against the old contract would rebuild the same defect.
