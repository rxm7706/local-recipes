---
companion-of: spec-foundry-capability-ledger
updated: "2026-09-13"
---

# CAP extract — trunc-avoiding inventory

**fcl:CAP-2.** The detector’s input is an extract, not a document.

Scribe already split two failure modes:

- `_node_from_text_file` keeps the first 20k characters. On a large
  `SPEC.md` that is usually Why + Constraints; Capabilities are dropped.
- Planning pointers and the library catalog keep **IDs and headings**
  and refuse the body (`spec-scribe-planning-pointers`,
  `spec-scribe-named-docs`).

This Spec uses the second flow.

For each `planning-artifacts/specs/spec-*/SPEC.md` with status
`ready` or `in-progress`:

1. Take `**CAP-N**` (or `CAP-N —`) headings in order.
2. Take the following `intent` and `success` lines only.
3. Prefix with the Spec id and path.

Do **not** store the Why, Non-goals, Assumptions, or any unique body
sentence that is not intent/success.

New files after the PIN SHA that are not yet in
`capability-ledger.yaml` are `--append` candidates, classified from
this extract, not from a 20k slice.
