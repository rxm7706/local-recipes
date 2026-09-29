# Transports and vendors (companion)

Load-bearing tables for `spec-work-passports-dated-extracts`. The kernel cites
this file; do not duplicate the rows in SPEC.md.

## File transports (how a drop arrives)

Config names which transports are active. Every transport writes the same
loader (batch sha + waybill). A new transport is a plugin.

| Transport | What it does | v1 default |
|---|---|---|
| app upload | file into the existing Postgres app / steward duty | on |
| shared folder | drop the same file into the same loader | off |
| email | mailbox parser into the same loader | off |

v1 does not require a mailbox parser. Email is an empty slot until enabled.

## Vendors

| Setting | v1 |
|---|---|
| `vendor_id` on inbound rows | present |
| vendors operated | one |
| second vendor | config later; no second standup pane until on |

## Missing-passport window

| Window | Behavior |
|---|---|
| first 14 days (config) | mint a passport; row stays in quarantine until a human links |
| after that | do not mint; quarantine as "no passport" until a human overrides |

Never match by title.

## Glass extras

| Extra | v1 |
|---|---|
| mailed/export of last waybill (CSV or markdown) | plugin, available |
| Herald standup slide | later empty slot |
