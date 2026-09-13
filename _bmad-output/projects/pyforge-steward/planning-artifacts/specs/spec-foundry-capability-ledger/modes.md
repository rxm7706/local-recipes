---
companion-of: spec-foundry-capability-ledger
updated: "2026-09-13"
---

# Capability modes

**fcl:CAP-1.** One mode per capability. Never `move`. This table is
the strangler **routing** map, not a git-sync map.

| Mode | Meaning |
|---|---|
| `rebuild` | B must re-derive from Frame/Spec; A is oracle until `verified-in-foundry` |
| `retire` | Must not appear on B; A may keep history |
| `A-only` | Allowed on A; must carry an expiry (story or date) |
| `B-only` | Named on a Spec before `done` |

`A-only` expiry is a story id or `YYYY-MM-DD`. `B-only` cites the Spec
id that named the behavior.

44.1’s move-list stays `blocked`. This companion does not reopen it.

`verified-in-foundry` is a **claim on a rebuild row**, not a fifth
mode. It requires a case-list id (`fnr:CAP-1` / 54.1 list).
