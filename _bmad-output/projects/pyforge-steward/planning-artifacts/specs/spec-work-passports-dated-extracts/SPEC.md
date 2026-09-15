---
spec: work-passports-dated-extracts
status: ready
created: "2026-09-14"
updated: "2026-09-15"
owner-dream: docs/dreams/work-passports-dated-extracts.md
surface: []
companions:
  - transports-and-vendors.md
sources:
  - ../../../../../../docs/dreams/work-passports-dated-extracts.md
  - ../../../../../../_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/brainstorm-intent.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-15 from
> `docs/dreams/work-passports-dated-extracts.md` § *Operator rulings (accepted
> 2026-09-15)* and this folder's `.memlog.md`. CAP-1..7 IDs are stable from the
> 2026-09-14 seed (CAP-6 and CAP-7 are later empty slots). Egg is CAP-1..5.

# SPEC — they mail a dated list; we mail a dated list

## Why

The internal agile team must see work that already lives on internal Jira,
Internal GitHub Projects, and the vendor-facing External GitHub Project —
and the last extracts that cross a two-way login ban — without opening a
board they are forbidden to open. Live sync into the vendor private GitHub
is a security incident. A fifth Kanban in Postgres would be a fourth place
to forget the lists. Steward Epic 8 already syncs pairs **both sides can
see**; this Spec is the customs house for the pair **neither side can sit
in**.

Owner: **steward**.

## Capabilities

- **CAP-1 — extract corridor and transports.**
  - **intent:** inbound vendor extract and outbound filtered extract load
    idempotently (batch sha + waybill). Transports are config plugins, not
    extra products.
  - **success:** re-dropping last week's file does not clone passports; an
    auditor can name the batch that created a stamp. Default transport is
    app upload. Email and share-folder drop the same file into the same
    loader. Tables: `transports-and-vendors.md`.

- **CAP-2 — work passport and frozen core schema.**
  - **intent:** UUID is identity; Jira keys and GitHub numbers are nicknames;
    `vendor_id` on inbound rows. Extra columns optional; unknown ignored.
    v1 operates one vendor.
  - **success:** two extracts cannot merge by title; high-value first links
    can require two humans. A second vendor is config, not a schema rewrite.

- **CAP-3 — as-of glass (standup and shipped).**
  - **intent:** vendor data on the existing Postgres app is dated; empty
    on-time file fails; late drop leaves yesterday stale; before first
    waybill the vendor pane is unborn.
  - **success:** testers see shipped-from-last-inbound; standup cites a
    waybill. A mailed/export of the same table is a switchable plugin.
    Herald slide is a later empty slot.

- **CAP-4 — outbound slice gate.**
  - **intent:** default deny, named slice, named outbound-signer role
    (default: steward operator). No whole-Jira dump. No BMAD factory work
    unless vendor-shared.
  - **success:** an unsigned or over-cap file does not leave; they load what
    we sent — we do not PAT into their org. Signer is recorded on the
    waybill.

- **CAP-5 — quarantine (no auto-link).**
  - **intent:** unlinked inbound rows wait for a human. First 14 days
    (config) mint a passport into quarantine; after that, do not mint.
  - **success:** no title-match endpoint exists. After the window, a row
    without a passport stays "no passport" until a human overrides.

- **CAP-6 — live collectors for boards we already own** *(later; empty in v1).*
  - **intent:** Jira and Internal GH we can log into feed stamps; never the
    vendor private project. Starts only on an operator date or explicit
    story — not after N Drop Nights.
  - **success:** the slot exists; v1 does not run collectors. Epic 8 /
    `steward sync` stays an indoor adapter on an allowed-pair list.

- **CAP-7 — BMAD projection onto Internal GH** *(later; empty in v1).*
  - **intent:** ledger remains source; GH cards say projected.
  - **success:** the slot exists; factory stories do not ride outbound
    unless vendor-shared.

## Constraints

- Postgres app is the join store, not a tracker.
- No Unito/Exalate. No fabricate. Extract is not live.
- Do not reopen Epic 8 as this product. Do not flip Epic 44 `blocked` keys.
- A-only.

## Non-goals

- Inventory/analytics UI in the egg (history may feed them later).
- Replacing Jira or GitHub as the place people act.
- Foundry-product work on B.
- Live sync or PAT into the vendor private GitHub.
- Operating a second vendor or requiring a Herald slide in v1.
- Auto-starting larva after N Drop Nights.

## Success signal

The internal agile team can run standup and testing from **our live boards
plus the last dated extracts**, with no credential that opens the vendor
private GitHub, and with outbound limited to a signed slice they load.

## Assumptions

- Steward Epic 61 is the dispatch home (61.1–61.5).
- The existing Postgres application is the join store named in the Dream.
