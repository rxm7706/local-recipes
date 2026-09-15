---
spec: build-league-scorecard
status: ready
created: "2026-08-25"
updated: "2026-09-15"
owner-dream: docs/dreams/build-league-scorecard.md
surface: []
companions:
  - measure-catalog.md
sources:
  - ../../../../../../docs/dreams/build-league-scorecard.md
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-15 from
> `docs/dreams/build-league-scorecard.md` § *Operator rulings (accepted
> 2026-09-15)* and this folder's `.memlog.md`. CAP-1 is the published
> configurable catalog. CAP-4 is a later empty slot (no dashboard).

# SPEC — Build League and Balanced Product Scorecard

## Why

The estate must optimize to **published** measures (Unifying Strategy Q5).
WFT named the faces; the operator selected eight already-counted signals
and required them to be switchable. Unpublished metrics must not steer
work. Owner: **steward**.

## Capabilities

- **CAP-1 — published measure catalog.**
  - **intent:** an operator-authored set covering human, agent, and team,
    consistent with Q1–Q4, written as named rows with state `on` / `off` /
    `archived`.
  - **success:** the eight first-cut ids are in `measure-catalog.md` and
    cited from the Unifying Strategy Dream. No consumer invents a
    substitute. First cut: all eight `on`.

- **CAP-2 — add, switch, and archive sources.**
  - **intent:** a new already-counted source is a new row; a dead source is
    archived (id reserved). Switching a row does not rewrite the catalog
    product.
  - **success:** a new row starts `off`; flipping `on` / `off` / `archived`
    is config. Archived ids are never reused for a different signal.

- **CAP-3 — consumers cite `on` rows only.**
  - **intent:** Herald, Atlas, Marshal, and Doctor (and Hub Outcome Guards
    later) read this catalog; they do not mint stealth metrics.
  - **success:** citing `off` or `archived` — or an id not in the catalog —
    is a refuse, not a silent fallback.

- **CAP-4 — scorecard board / league table.** *(Later; empty in v1.)*
  - **intent:** a board is not a Canopy CAP and is not this first epic.
  - **success:** the slot exists; v1 does not implement a UI.

## Constraints

- Never invent metrics, weights, or a composite league score.
- Never score 01/02 work against five-tier completeness.
- Never treat a Jira key as a quality signal.
- Never a scorecard UI in `spec-pyforge-unifying-strategy`. CAP-18 is hooks.
- Do not flip Epic 44 `blocked` keys. A-only.

## Non-goals

- A dashboard in this epic.
- Replacing Warden as the PR quality gate (Q8).
- Implementing Hub Outcome Guards on this Spec.

## Success signal

Operators and stations can name each published measure, its state, and
refuse unpublished ones. New sources add; old ones archive.

## Assumptions

- Steward Epic 62 is the dispatch home (62.1–62.3).
- The eight ids name signals the estate already counts; this Spec does not
  invent their formulas.
