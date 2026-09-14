---
spec: work-passports-dated-extracts
status: draft   # 2026-09-14 — seeded so the Dream's chain link is durable (dream-chain INV-1).
                # Six open questions remain; egg CAPs are candidates until those clear.
                # Per docs/dreams/README.md:71-78 a `draft` Spec establishes the CHAIN, not the
                # CONTRACT — the owning Dream therefore stays `dreamt`.
created: "2026-09-14"
updated: "2026-09-14"
owner-dream: docs/dreams/work-passports-dated-extracts.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/work-passports-dated-extracts.md
  - ../../../../../../_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/brainstorm-intent.md
open_questions:
  - extract-transport-email-share-or-app-upload
  - larva-trigger-n-drop-nights-or-date
  - missing-passport-mint-or-reject-after-week-two
  - second-vendor-in-v1
  - outbound-signer-role
  - standup-glass-if-app-refused
---

> **Seed Spec — the chain, not the contract.** Derived 2026-09-14 from
> `docs/dreams/work-passports-dated-extracts.md` and the brainstorm intent.
> It exists so `dream-chain` INV-1 has a durable link. **Egg capabilities are
> candidates until the open questions close.** Nothing downstream may bind a
> story that answers those questions by inference.

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

## Capabilities — candidates; egg is the intended first cut

- **CAP-1 — extract corridor.**
  - *intent:* inbound vendor extract and outbound filtered extract load
    idempotently (batch sha + waybill). File/email/share/app-upload are
    transports, not extra products.
  - *success:* re-dropping last week's file does not clone passports; an
    auditor can name the batch that created a stamp.
- **CAP-2 — work passport and frozen core schema.**
  - *intent:* UUID is identity; Jira keys and GitHub numbers are nicknames;
    `vendor_id` on inbound rows. Extra columns optional; unknown ignored.
  - *success:* two extracts cannot merge by title; high-value first links
    can require two humans.
- **CAP-3 — as-of glass (standup and shipped).**
  - *intent:* vendor data on the existing Postgres app is dated; empty
    on-time file fails; late drop leaves yesterday stale; before first
    waybill the vendor pane is unborn.
  - *success:* testers see shipped-from-last-inbound; standup cites a
    waybill. *(Open: mailed query / Herald if the app is refused.)*
- **CAP-4 — outbound slice gate.**
  - *intent:* default deny, named slice, signer. No whole-Jira dump. No
    BMAD factory work unless vendor-shared.
  - *success:* an unsigned or over-cap file does not leave; they load what
    we sent — we do not PAT into their org.
- **CAP-5 — quarantine (no auto-link).**
  - *intent:* unlinked inbound rows wait for a human.
  - *success:* no title-match endpoint exists.
- **CAP-6 — live collectors for boards we already own** *(larva; contingent).*
  - *intent:* Jira and Internal GH we can log into feed stamps; never the
    vendor private project.
  - *success:* Epic 8 / `steward sync` runs only on an allowed-pair list
    inside our walls.
- **CAP-7 — BMAD projection onto Internal GH** *(larva; contingent).*
  - *intent:* ledger remains source; GH cards say projected.
  - *success:* factory stories do not ride outbound unless vendor-shared.

## Constraints

- Postgres app is the join store, not a tracker.
- No Unito/Exalate. No fabricate. Extract is not live.
- Do not reopen Epic 8 as this product. Do not flip Epic 44 `blocked` keys.
- A-only.

## Non-goals

- Inventory/analytics UI in the egg (history may feed them later).
- Replacing Jira or GitHub as the place people act.
- Foundry-product work on B.

## Success signal

The internal agile team can run standup and testing from **our live boards
plus the last dated extracts**, with no credential that opens the vendor
private GitHub, and with outbound limited to a signed slice they load.

## Open Questions

Carried from the Dream § *Open questions for the Spec*. Nothing
downstream may bind until they are answered.
