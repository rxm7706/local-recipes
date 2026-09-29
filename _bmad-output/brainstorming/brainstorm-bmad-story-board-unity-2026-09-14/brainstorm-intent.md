---
title: Work passports and dated extracts
status: ready-for-dream
created: 2026-09-14
source: brainstorm-bmad-story-board-unity-2026-09-14
---

# Intent

The internal agile team should **see every piece of work they are allowed to see** — internal Jira (Kanban + quarterly), Internal GitHub Projects (our issues + later BMAD projections), External GitHub Projects (vendor-facing book), and the **last extracts** that cross the wall — without anyone logging into a board they are forbidden to open.

Vendor can extract and send. We can send a **filtered** extract they load into their GitHub. That corridor is the product. Live PATs into their org are not.

Postgres (the app we already have) is the **join store**, not a fifth Kanban.

## Must (egg)

- Inbound + outbound extract loaders (file/email/share). Idempotent. Batch sha + waybill.
- Frozen tiny core schema; extra columns optional; unknown ignored.
- Passport UUID; Jira keys and GH numbers are nicknames. `vendor_id` on inbound rows.
- Vendor glass is **as-of** (their clock + received clock). Empty on-time file = failed drop. Late drop = stale yesterday, not blank.
- Outbound: default deny, named slice, signer. No whole-Jira dump. No BMAD factory work unless vendor-shared.
- No title-match. Unlinked inbound goes to quarantine.
- No fabricate. No Unito/Exalate. Epic 8 / steward sync only on **allowed pairs inside our walls**.

## Should

- Two views on the existing app: `standup`, `shipped`.
- Quarantine Hour (human link). Drop Night ritual.

## Could (larva / later)

- Live collectors for Jira + Internal GH we already own.
- Internal GH as fridge (projected columns). BMAD ledger → GH cards labeled projected.
- Inventory/analytics on extract **history**. Herald weekly book.

## Won't this time

- Live sync or PAT into the vendor private GitHub.
- A fourth tracker in the app.
- Treating a daily extract as live.

## Kinship

Sibling Dream to `docs/dreams/jira-github-projects-sync.md`. That engine stays an adapter for pairs we can both see. Do not reopen Epic 8 as this product.

## HMW (kept)

How might the internal agile team see every piece of work that already lives on internal Jira, the internal GitHub Project, and the external vendor GitHub Project, without anyone needing access to a board they are forbidden to open?

**Drunk line:** they mail a dated list, you mail a dated list; the database is where the lists sit so you stop losing them.
