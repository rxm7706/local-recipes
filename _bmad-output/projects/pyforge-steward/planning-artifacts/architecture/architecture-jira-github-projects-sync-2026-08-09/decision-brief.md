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
with trigger=`webhook` — true Mode A, real-time, zero infrastructure.** Mode B stays opt-in.

### Why this reads as a reversal in the memlog

The first cut of this architecture defaulted the trigger to `schedule`, on the reading that
batch latency was acceptable and webhooks were therefore complexity nobody had asked for.
That was **reversed on explicit instruction**: near-real-time is wanted.

The decoupling survived the reversal, and it is worth keeping for two reasons that have
nothing to do with which default won. It is what lets **Mode B run scheduled** — the axis has
to exist for Mode B to be describable at all — and it is what lets a deployment **fall back to
a schedule** for recovery without a second implementation (see AD-9).

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

**Q3 — which mode?** Both. Default: serverless transport, **webhook trigger — true Mode A, real-time**. Mode B opt-in. *(Operator decision 2026-08-09; reversed the same day from an initial `schedule` default, on explicit instruction that near-real-time is wanted.)*

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

## What this does *not* decide

Deliberately left to the stories or to first use: the schedule interval, where Mode B's
PostgreSQL would run (nobody has opted in — deciding hosting for a mode with no user is
speculative), which fields sync beyond status/assignee/link, and whether Jira pushes or the
schedule pulls both sides.

## Status

Epic 8's five stories remain **blocked** in the ledger. Unblocking them is a separate operator
call after this architecture is reviewed — the architecture answers the questions, it does not
authorise the build.
