---
companion-of: spec-foundry-capability-ledger
updated: "2026-11-11"
---

# CAP extract — trunc-avoiding inventory

**fcl:CAP-2.** The detector’s input is an extract, not a document. This
file is the inventory contract both extractors follow: steward's ledger
generator (`steward cutover plan`, Story 121.1) and doctor's
`capability-ledger` source (`spec-pyforge-doctor:CAP-95`, doctor Story
56.2). The rows it yields take the shape of `modes.md` § Schema v1.

Scribe already split two failure modes:

- `_node_from_text_file` keeps the first 20k characters. On a large
  `SPEC.md` that is usually Why + Constraints; Capabilities are dropped.
- Planning pointers and the library catalog keep **IDs and headings**
  and refuse the body (`spec-scribe-planning-pointers`,
  `spec-scribe-named-docs`).

This Spec uses the second flow.

## Scope

A Spec is in the inventory when its `SPEC.md` sits at

- `_bmad-output/projects/<project>/planning-artifacts/specs/spec-<slug>/SPEC.md`, or
- `docs/governance/spec-<slug>/SPEC.md`,

and is live: its frontmatter `status:` reads `ready` or `in-progress` (a
trailing `# comment` is ignored, so `status: ready   # note` is `ready`).

Nothing under `archive/` is read, whatever its status. A capability of an
archived Spec has no row (`modes.md` rule 4); the folded station row is the
single record.

## What is taken

For each live Spec, in file order:

1. Take each capability heading line (§ Heading forms).
2. Take the first `**intent:**` and `**success:**` lines after it, before
   the next heading, and the marker on the heading line (`modes.md`
   § Marker tokens).
3. Prefix with the Spec id and path.

Do **not** store the Why, Non-goals, Assumptions, or any unique body
sentence that is not intent/success.

## Heading forms

A heading line opens, after optional indentation and one `-` or `*`
bullet, with a bold capability number. Three forms:

| Form | Example |
|---|---|
| `**CAP-n — title**` | `- **CAP-1 — Tracked ledger.** (shipped …)` |
| `**CAP-n**` | `- **CAP-n** — title`, the title outside the bold |
| `**pap:CAP-n — title**` | `- **pap:CAP-1 — The host renders from the accelerator shape.**` |

The dash may be an em dash, an en dash or a hyphen.

Normalisation, the same in both extractors (doctor's `extract_caps`): the
heading is the title inside the bold, or for `**CAP-n**` the text after the
dash; strip surrounding whitespace, then a trailing `.`, then a trailing
`*`, then whitespace again. The marker and anything after the bold
(`← spec-… CAP-n`, `(shipped …)`) are not part of the heading. A ledger
row's `heading` equals this string, and a row whose heading differs from
its Spec's title is a FAIL (`fcl:CAP-2`).

## Id rule

- `fnd:CAP-n` for `spec-python-foundry-cutover`, `fnr:CAP-n` for
  `spec-foundry-regenerate-not-fold` and `fcl:CAP-n` for
  `spec-foundry-capability-ledger`, the three cutover Specs.
- `pap:CAP-n` for a heading written with the `pap:` prefix (the six host
  capabilities `spec-pyforge-unifying-strategy` carries as
  `**pap:CAP-n — title**`).
- `<slug>:CAP-n` otherwise, where `<slug>` is the Spec folder name without
  `spec-` (the frontmatter `spec:` where one is set; the two agree on every
  live Spec): `pyforge-atlas:CAP-68`, `pyforge-unifying-strategy:CAP-1` (the
  Unifying Spec's unprefixed CAP-1 to CAP-20), `one-chain-per-station:CAP-5`.

There is no other short prefix: `hub:` and `pgs:` named Specs that are
archived. A row's `spec` is the `<slug>` whatever its id's prefix.

## Station rule

A row's `station` is the BMAD project that holds the Spec folder: the
`<project>` of `_bmad-output/projects/<project>/…`, in its long form
(`pyforge-<station>`). So the kernel rows (`spec-pyforge-core`,
`spec-pyforge-testing-charter`) read `station: pyforge-marshal`, where their
chain lives under the one-chain rule, not the package's own name.

A Spec under `docs/governance/` is held by no BMAD project; its rows read
`station: governance`.

## Append

New files after the PIN SHA that are not yet in
`capability-ledger.yaml` are `--append` candidates, classified from
this extract, not from a 20k slice.
