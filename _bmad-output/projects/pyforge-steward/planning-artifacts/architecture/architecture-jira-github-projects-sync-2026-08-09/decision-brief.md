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

Mode A is webhook-triggered *by choice*, not by necessity. The same GitHub Actions workflow
runs under `on: schedule` instead of `on: project_v2_item`. That yields **batch cadence at zero
infrastructure** — the thing that appeared unavailable — and drops every webhook edge case
(delivery retries, replay, out-of-order events) as a bonus.

**Default: serverless transport, scheduled trigger. Mode B: opt-in, for when you want more.**

## What each choice costs

**Staying on the default** costs you latency (changes propagate on the next scheduled run, not
in seconds) and history (there is no queryable record of past syncs — the systems hold current
state only).

**Opting into Mode B** costs you a PostgreSQL instance to host, back up, and secure. It buys
queryable sync history, uniform handling of arbitrary custom fields, and per-field sync
direction.

Migration is deliberately cheap: both transports implement the **same logical control plane**,
so a board synced under the default can move to Mode B without re-linking a single item. That
is the point of AD-3, and it is the invariant most likely to be eroded by a well-meaning
shortcut.

## The three questions the Spec left open

**Q3 — which mode?** Both, with the default above. *(Operator decision, 2026-08-09.)*

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
