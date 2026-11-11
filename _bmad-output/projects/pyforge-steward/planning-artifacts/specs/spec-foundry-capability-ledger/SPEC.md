---
fold-exemption: different-lifecycle
spec: foundry-capability-ledger
status: ready
created: "2026-09-13"
updated: "2026-11-11"
owner-dream: docs/dreams/foundry-capability-ledger.md
extends: spec-foundry-regenerate-not-fold
surface: []
companions:
  - modes.md
  - extract.md
  - remode-2026-11-10.md
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

- **CAP-1 — Tracked ledger.** (shipped 2026-11-10, Stories 55.1, 121.1, 121.3, 121.6 and 121.7)
  - **intent:** The operator can classify every live capability as
    `rebuild`, `retire`, `A-only`, or `B-only` in one tracked file, each
    mode by a written rule.
  - **success:** `docs/foundry/capability-ledger.yaml` follows schema
    `pyforge.capability-ledger/v1` (`modes.md` § Schema v1): derived
    fields id, spec, station, heading, path; decided fields mode, expiry,
    state, launch, depends_on (optional), frozen_paths, case_id,
    pending_on, defaulted, note; a `cells:` list classifies what has no
    Spec yet (conda-forge-expert). Every extracted `CAP-N` of a live Spec,
    `docs/governance/spec-*/SPEC.md` and prefixed headings included, has a
    row; no row sits on an archived Spec; `A-only` has an expiry; there is
    no `move` key. Every mode follows `modes.md` § The rules of
    2026-11-10: a capability never built is `B-only` when a live `blocked`
    or `backlog` Story carries it and `retire` when none does; `pending`
    is only a row waiting on a named operator question (`pending_on`).
    `steward cutover plan --check` (`cutover_ledger_check.py`) refuses a
    row that contradicts its Spec's marker, a `pending` row with no
    question and a `rebuild` row nothing built, and
    `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q`
    exits 0. Story 44.1 is retired.

- **CAP-2 — Extract detector.** (shipped 2026-11-10, Story 55.2, doctor Story 56.2 and Story 121.6)
  - **intent:** `detectors-ci` can refuse unclassified or undated
    rows using a CAP heading extract, not wholesale SPEC bodies.
  - **success:** Unclassified `CAP-N` is HARD; `A-only` without
    expiry is HARD; a row with no live capability, a heading that differs
    from the Spec title, a row on an archived Spec and an unknown mode or
    state are HARD (`spec-pyforge-doctor:CAP-95`); paths/Specs after the
    PIN SHA that lack a row are `--append` until classified; the gather
    path does not use `_node_from_text_file` / a 20k prefix of `SPEC.md`.
    Companion `extract.md` is the inventory contract: the scope (live
    Specs under `planning-artifacts/specs` and `docs/governance`, never
    `archive/`), the heading forms and their normalisation, the id rule
    and the station rule. An `A-only` expiry is judged when it arrives: a
    date 30 days ahead is a WARN, one day past a FAIL, a done Story a FAIL
    and an unresolved key a FAIL (doctor's `capability-ledger` source);
    the `flip` form is judged by `steward cutover plan --check`, which
    reads the root of record.
    `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py -q`
    and
    `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -k flip_expiry`
    each exit 0.

- **CAP-3 — Case-list join.** (shipped 2026-09-13, Story 55.3)
  - **intent:** A `verified-in-foundry` claim is meaningless without
    a named case.
  - **success:** A ledger row that claims `verified-in-foundry`
    without a case-list id is HARD; 54.1’s list is the join key;
    Frame preflight is not a substitute.

## Constraints

- **Strangler fig, not a mirror branch.** The facade is the public CLI;
  routing per capability is the ledger row, never the
  `pyforge.cutover_root` flag (`fnd:CAP-8`). Each `rebuild` row is a new
  vine on B, re-derived from the Dream plus its memlog (a Frame is a
  pointer to them, not a seed). A long-lived B branch that mirrors A is
  out of contract. Two trunks; PIN + behavior compare (`ab-sync.md`).
- Inventory is extract-only (`extract.md`). Do not ingest Why or
  prose bodies.
- Modes are the four destinations in `modes.md` § Schema v1 plus
  `pending`, a placeholder on a named operator question that B never
  acts on. No `move`.
- Do not flip Epic 44 `blocked` keys, including 44.1.
- Do not rsync `_bmad-output` or `src/shared/packages` onto foundry.
- Public CLI verbs stay. `pyforge.cutover_root` stays `local-recipes`
  until the operator flips it by hand, with no loop running, once the
  Launch slice is proven; nothing flips it automatically.
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
