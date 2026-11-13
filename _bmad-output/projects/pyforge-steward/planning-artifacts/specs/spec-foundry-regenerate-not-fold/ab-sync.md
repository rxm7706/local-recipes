---
companion-of: spec-foundry-regenerate-not-fold
updated: "2026-11-11"
---

# Dual-root A/B — contract shared, behavior compared

**fnr:CAP-5.** One starting contract, written on A until the flip. A/B the
behavior. Do not drag local-recipes comments, PRDs, epics, or package trees
into foundry.

## Roles

A writes every Dream, Frame, Spec and the capability ledger until the
`pyforge.cutover_root` flip; B reads A at the SHA in its
`docs/foundry/PIN.md` and writes none of them. The flip hands the writer
lock to B (`fnd:CAP-8`; operator ruling 1 of 2026-11-10).

| Layer | A `rxm7706/local-recipes` | B `rxm7706/python-foundry` |
|---|---|---|
| Dream, Frame, Spec and the capability ledger | **Writer** until the flip | Reads A at the SHA in its `docs/foundry/PIN.md` and writes none of them; takes the writer lock at the flip |
| The seed: Dream plus memlog (`archive/**/.memlog.md` included, no backfill) | Writes it until the flip | Re-derives each Spec from it; a Frame is a pointer to it, not a seed |
| PRD / ARCH / epics / sprint / stories | Historical archive. Do not copy. | Slim foundry chain only. New numbers OK; cite the same `CAP-N`. |
| Code | Brownfield control. Oracle. | `src/packages/` treatment. Born, not folded. The three kernel leaves are a prototype at A's PR #1344, not re-pinned until the core, steward and marshal Specs pass a truth sweep. |
| Factory / CFE / recipes | Invent here until a foundry CFE exists | Factory island only; CFE resolve may stay on A |

Never author the same Dream in both repos. B is the follower until the
flip: a pin, not a fork.

## Pin

On the follower, one tracked file (foundry: `docs/foundry/PIN.md` since
54.5):

```
contract: <repo>@<sha>
dream: <path>
frame: <path>
spec: <path>
```

B stays pinned at A's PR #1344 until the core, steward and marshal Specs
pass a truth sweep (operator ruling 1). From then on, a Dream, Frame, Spec
or ledger edit on the writer opens a pin-bump PR on the follower the same
day (docs only).

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
- Treat `pyforge.cutover_root` as the A/B harness. It is the writer lock
  and the root of record, and it stays `local-recipes` until the operator
  flips it by hand, with no loop running, once the Launch slice is proven:
  B lands one story on itself through its own dispatch and its own
  detectors, and every Launch row of the case list reads
  `verified-in-foundry`. Nothing flips it automatically.

## 48h vs kernel

54.5 lands this protocol + `PIN.md` + a short case-list stub **on B**.
54.1 grows the list. 54.2–54.4 must record an A/B row before `done`.
A `steward ab` CLI can wait until the list is larger than a stub.
