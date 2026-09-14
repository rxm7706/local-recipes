---
title: They mail a dated list; we mail a dated list
type: dream
owner: steward
status: dreamt
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

- Transport of the file (email, share, app upload) — not the corridor itself.
- When larva starts (N Drop Nights vs a date).
- After week two, reject inbound rows with no passport vs keep minting.
- Second vendor in v1 (`vendor_id` is already implied) vs later.
- Named outbound signer role.
- If standup will not open the app: same table → mailed query vs Herald slide.

## Realization log

- **2026-09-14** — Captured from operator topology + `bmad-brainstorming`
  (facilitator → ideate-for-me → converge MoSCoW). Owner **steward** (estate
  join, existing app, kinship to Epic 8). Chain Spec seeded `draft` the same
  day so dream-chain INV-1 holds; Dream stays `dreamt` until that Spec is
  `ready`.
