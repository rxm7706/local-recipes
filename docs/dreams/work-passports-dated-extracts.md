---
title: They mail a dated list; we mail a dated list
type: dream
owner: steward
status: specified
---

# They mail a dated list; we mail a dated list

> **Seed Dream.** Operator 2026-09-14: BMAD stories, GitHub Projects, Jira, and
> Postgres as one working system — **sibling** to [[jira-github-projects-sync]],
> not a reopen of steward Epic 8. Converged in
> `_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/`
> (`bmad-brainstorming`, then intent). Scribe recall that day
> (`scribe recall "work passport extract corridor Jira GitHub Postgres dream"
> --mode planning`) → **no grounded answer**.

## The Dream

The internal agile team **sees every piece of work they are allowed to see**
without anyone logging into a board they are forbidden to open.

Work already lives in more than one room: **internal enterprise Jira** (Kanban
and quarterly planning), **Internal GitHub Projects** (our issues; later, BMAD
epics and stories as fridge magnets), **External GitHub Projects** (the vendor
book we are allowed to share a surface for). The vendor cannot sit in our Jira
or our GitHub. We cannot sit in their private GitHub. They **can** extract and
send a file. We **can** send a filtered extract they load into their GitHub.

The product is that **corridor** — two dated lists, a **work passport** (a UUID
we mint; Jira keys and GitHub numbers are nicknames), and the **Postgres app we
already have** as the join store. It is not a fifth Kanban. It is not a live
sync into their org.

> How might the internal agile team see every piece of work that already lives
> on internal Jira, the internal GitHub Project, and the external vendor GitHub
> Project, without anyone needing access to a board they are forbidden to open?

## What it looks like when real

- Standup cites a **waybill** ("as of drop N"), not "any updates from the vendor?"
- Testers pull a **shipped** shelf from the last inbound extract, not from a
  hunt in a private repo.
- Findings leave in a **signed outbound slice** the vendor can load — not a
  dump of our Jira, not factory BMAD work unless marked vendor-shared.
- Vendor status on the glass is **as-of** (their clock and our received clock).
  An empty on-time file is a failed drop. A late drop leaves yesterday visible
  and stale, not a blank book. Before the first waybill, the vendor pane is
  **unborn**, not empty.
- Unlinked inbound rows sit in **quarantine**. Humans link; the system does not
  guess by title.
- Security can show **no PAT** that opens their org or writes ours on their
  behalf.
- BMAD ledger stays the factory source. Internal GH cards, when they exist,
  say **projected**.

## What is real

- Mandated surfaces: internal Jira, Internal GitHub Projects for our issues,
  External GitHub Projects for vendor-facing issues, the existing Postgres
  application.
- Extract both ways is operator-confirmed (2026-09-14). The air-gap is **no
  live login**, not no data.
- [[jira-github-projects-sync]] / steward Epic 8 is **specified** and `done` on
  the ledger — bidirectional sync for an **external pair we can both see**.
  `steward sync reconcile` and the 12.8 `github_metrics` dlt load stay
  **adapters**, never this product, and must not be aimed at the vendor private
  project.
- Brainstorm memlog + intent:
  `_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/`.

## Constraints

- Postgres is a constraint, not a design choice for v1 storage.
- No third-party sync SaaS (Unito, Exalate).
- No live GitHub credential into the vendor private project; they load our
  extract.
- No fourth tracker in the app.
- Do not treat a daily extract as live.
- Do not fabricate vendor rows to hide holes.
- Do not flip Epic 44 `blocked` keys. A-only.

## Non-goals

- Reopening Epic 8 as "BMAD + Jira + GitHub + Postgres."
- Inventory/analytics UI in the egg (history can feed them later).
- Replacing Jira or GitHub as where people **act**.
- Foundry-product Dream on B.

## Egg, then larva

**Egg:** inbound + outbound loaders, frozen tiny schema, passport UUID,
waybill + as-of, two views on the existing app (`standup`, `shipped`),
quarantine, signed outbound slice.

**Larva (later):** live collectors for Jira and Internal GH we already own;
Internal GH as fridge; BMAD projection; Herald book; inventory on extract
history. Epic 8 only on an **allowed-pair** list **inside our walls**.

## Open questions for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below. They bind the
Spec re-derive. The Dream is `specified` only after that Spec is `ready`.

1. **Transport** — email, share folder, or app upload?
2. **Larva trigger** — after N Drop Nights, or a date / explicit start?
3. **Missing passport after week two** — keep minting, or reject?
4. **Second vendor in v1** — operate two, or schema-ready only?
5. **Outbound signer** — named role, or implicit operator?
6. **Standup glass if the app is refused** — mailed query, or Herald slide?

## Operator rulings (accepted 2026-09-15)

Operator approved the session plan. **Egg** is this first cut. **Larva** is
later. **Waybill** = which drop and which clocks. **Passport** = the UUID we
mint. Do not treat steward Epic 8 as this product.

1. **Default transport is upload into the existing app.** Email and a shared
   folder are extra transports that drop the same file into the same loader.
   v1 does not require a mailbox parser. Tables: Spec companion
   `transports-and-vendors.md`.

2. **Larva does not start automatically.** Not after N Drop Nights. CAP-6
   and CAP-7 stay later empty slots. Live collectors start when the operator
   flips a date or an explicit "start larva" story.

3. **First two weeks (config; default 14 days): mint a passport and
   quarantine until a human links nicknames.** After that, do not mint. The
   row stays in quarantine as "no passport" until a human overrides. Never
   match by title.

4. **Schema has `vendor_id` from day one. v1 runs one vendor.** A second
   vendor is config, not a rewrite. No second standup pane until turned on.

5. **Named role: outbound signer.** A person or GitHub team on the existing
   app, recorded on the waybill. Default: the steward operator running Drop
   Night. Unsigned or over-broad files do not leave.

6. **App views `standup` and `shipped` are the product.** A mailed/export
   of the same table (CSV or markdown of the last waybill) is a plugin so
   standup can run from a file. A Herald slide is a later empty slot, not
   required for egg.

Do not flip Epic 44 `blocked` keys. Do not aim Epic 8 or `steward sync` at
the vendor private project.

## Realization log

- **2026-09-14** — Captured from operator topology + `bmad-brainstorming`
  (facilitator → ideate-for-me → converge MoSCoW). Owner **steward** (estate
  join, existing app, kinship to Epic 8). Chain Spec seeded `draft` the same
  day so dream-chain INV-1 holds; Dream stays `dreamt` until that Spec is
  `ready`.
- **2026-09-15** — Operator approved Q1–6 (upload default; email/share
  plugins; larva not auto; mint-then-reject after two weeks; one vendor
  operated, `vendor_id` ready; named outbound signer; mailed query plugin;
  Herald later). Spec `ready`. Steward Epic **61** (61.1–61.5 `backlog`)
  is the marshal dispatch home. Dream `dreamt` → `specified`.
