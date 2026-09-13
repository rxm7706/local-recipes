---
companion-of: spec-foundry-regenerate-not-fold
updated: "2026-09-13"
---

# Dual-root A/B — contract shared, behavior compared

**fnr:CAP-5.** One starting contract. A/B the behavior. Do not drag
local-recipes comments, PRDs, epics, or package trees into foundry.

## Roles

| Layer | A `rxm7706/local-recipes` | B `rxm7706/python-foundry` |
|---|---|---|
| Dream + Frame + Spec five-fields | Mirror + SHA pin after B is writer | **Writer** once the 48h kit exists |
| This Spec (seed) | Writer until the kit lands on B | Then pin |
| PRD / ARCH / epics / sprint / stories | Historical archive. Do not copy. | Slim foundry chain only. New numbers OK; cite the same `CAP-N`. |
| Code | Brownfield control. Oracle. | `src/packages/` treatment. Born, not folded. |
| Factory / CFE / recipes | Invent here until a foundry CFE exists | Factory island only; CFE resolve may stay on A |

Never author the same Dream in both repos. The follower is a pin, not a fork.

## Pin

On the follower, one tracked file (foundry: `docs/foundry/PIN.md` after 54.5):

```
contract: <repo>@<sha>
dream: <path>
frame: <path>
spec: <path>
```

A Dream/Frame/Spec edit on the writer opens a pin-bump PR on the follower
the same day (docs only).

## Compare (per Story that ships on B)

Shared **case list** (CAP-1 list; first stub lands with 54.5). Run the same
argv on A and on B.

| Result | Meaning |
|---|---|
| `pass` | Both match the Spec success line |
| `A-only` | Legacy still does it; Spec marks later-cap — allowed |
| `B-only` | New behavior; Spec must name it before `done` |
| `diverge` | Both run, contract differs — **blocks** `verified-in-foundry` |

Compare exit code, stdout contract, MCP shape. Not file trees. Not
comments. Frame preflight is not this test.

## Do not

- `rsync` `_bmad-output` or `src/shared/packages`
- Merge epics across roots
- A third git root
- Treat `pyforge.cutover_root` as the A/B harness (it stays
  `local-recipes` until the kernel passes the shared list)

## 48h vs kernel

54.5 lands this protocol + `PIN.md` + a short case-list stub **on B**.
54.1 grows the list. 54.2–54.4 must record an A/B row before `done`.
A `steward ab` CLI can wait until the list is larger than a stub.
