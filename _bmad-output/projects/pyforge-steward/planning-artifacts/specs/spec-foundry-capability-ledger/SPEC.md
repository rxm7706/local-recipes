---
fold-exemption: different-lifecycle
spec: foundry-capability-ledger
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/foundry-capability-ledger.md
extends: spec-foundry-regenerate-not-fold
surface: []
companions:
  - modes.md
  - extract.md
sources:
  - ../../../../../../docs/dreams/foundry-capability-ledger.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from
> `docs/dreams/foundry-capability-ledger.md` and `.memlog.md`. Cite
> this file's ids as `fcl:CAP-1..3`. Decomposed as steward **Epic 55**.
> Does not flip 44.1 or any Epic 44 `blocked` key.

# SPEC — Foundry capability ledger

## Why

**A pain to solve and a mandate to meet.** PIN plus policy does not
prove every live capability was rebuilt, retired, or scheduled.
Unclassified `CAP-N` and undated `A-only` rows are invisible until
Launch claims `verified-in-foundry`. The check must stay cheap: an
ID/heading extract, not a SPEC novel and not a 20k truncate.

## Capabilities

- **CAP-1 — Tracked ledger.**
  - **intent:** The operator can classify every live capability as
    `rebuild`, `retire`, `A-only`, or `B-only` in one tracked file.
  - **success:** `docs/foundry/capability-ledger.yaml` exists; every
    extracted `CAP-N` has a mode; `A-only` has an expiry; there is no
    `move` key; 44.1 stays `blocked`.

- **CAP-2 — Extract detector.**
  - **intent:** `detectors-ci` can refuse unclassified or undated
    rows using a CAP heading extract, not wholesale SPEC bodies.
  - **success:** Unclassified `CAP-N` is HARD; `A-only` without
    expiry is HARD; paths/Specs after the PIN SHA that lack a row
    are `--append` until classified; the gather path does not use
    `_node_from_text_file` / a 20k prefix of `SPEC.md`. Companion
    `extract.md` is the inventory contract.

- **CAP-3 — Case-list join.**
  - **intent:** A `verified-in-foundry` claim is meaningless without
    a named case.
  - **success:** A ledger row that claims `verified-in-foundry`
    without a case-list id is HARD; 54.1’s list is the join key;
    Frame preflight is not a substitute.

## Constraints

- **Strangler fig, not a mirror branch.** The facade is the public CLI
  (and later `cutover_root`). Each `rebuild` row is a new vine on B
  from Frame + Spec. A long-lived B branch that mirrors A is out of
  contract. Two trunks; PIN + behavior compare (`ab-sync.md`).
- Inventory is extract-only (`extract.md`). Do not ingest Why or
  prose bodies.
- Modes are exactly the four in `modes.md`. No `move`.
- Do not flip Epic 44 `blocked` keys, including 44.1.
- Do not rsync `_bmad-output` or `src/shared/packages` onto foundry.
- Public CLI verbs stay. `pyforge.cutover_root` stays
  `local-recipes` until the kernel list is green.
- Never commit on the shared checkout; never `scripts/bmad-switch`
  from a parallel agent.

## Non-goals

- Implementing 44.1’s move-list or unblocking it.
- Folding packages via 44.4 / apply phase 1a.
- Compiling SPEC novels into Scribe recall (Scribe already forbids
  that; this detector does not reopen it).
- Effect-has-a-caller (`capability-effect-check`) — destiny, not
  callers.
- A `steward ab` CLI (still optional after 54.1).
- A long-lived B branch that mirrors A's tree.
- Adding `fnr:CAP-6` by hand-editing `spec-foundry-regenerate-not-fold`
  `SPEC.md` — this sibling Spec is the ledger contract.

## Success signal

`detectors-ci` is red on an unclassified `CAP-N` or an `A-only` row
with no expiry, and green when the yaml matches the extract. A
`verified-in-foundry` claim without a case-list id is red.

## Assumptions

- Scribe 13.1 / 14.1 already prove extract-not-truncate on this
  estate; reuse the shape, do not vendor cocoindex.
- 54.1’s case-list is the join surface even if that Story is still
  in progress when this Spec lands.
