---
title: '53.6: Frame identity is the qualified-ref identifier, not the name'
type: 'docs'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the nine Frames to satisfy frame-spec v0.3 in full — qualified-ref identifiers, prose titles, sequence-shaped repeatables — and the preflight to key off `identifier`

**Approach:** a Hub reader resolves our Frames by the element that carries identity, and the estate stops using one string as both a Frame key and a dist name.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-53-6-frame-identity-is-the-qualified-ref-identifier-not-the-name.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| 53.5 left the nine Frames on `identifier: pyforge-<station>` (a bare `name-ref`), slug `name:` values, and scalar `maintainer`/`inherits` | this story lands | every Frame carries a `qualified-ref` identifier (`pyforge/company`, `pyforge/<station>`) with exactly one `/` and no `@` (v0.3 §4.2.1, §5.3) | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `name` is the Charter's prose form (`PyForge Steward`), since the element profile marks `title` MUST NOT be slug-constrained | n/a |
| And-clause from epics.md | when the story lands | `maintainer` and `inherits` are sequences (§6.2.1 "A writer MUST emit a sequence"), with `owner:` collapsed into the registered `maintainer` | n/a |
| And-clause from epics.md | when the story lands | the aliases `name`/`inherits` are KEPT — §6.2.1 requires them of a Markdown writer; `title`/`composition` belong to the YAML/JSON encodings | n/a |
| And-clause from epics.md | when the story lands | the preflight keys identity off `identifier`, reports a scalar repeatable, and still resolves a `path-ref` parent | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `docs/foundry/frames/**` (9 files),
Ledger key: `53-6-frame-identity-is-the-qualified-ref-identifier-not-the-name`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-53-6-frame-identity-is-the-qualified-ref-identifier-not-the-name.md`.

## Epic excerpt

As a platform operator,
I want the nine Frames to satisfy frame-spec v0.3 in full — qualified-ref
identifiers, prose titles, sequence-shaped repeatables — and the preflight to
key off `identifier`,
So that a Hub reader resolves our Frames by the element that carries identity,
and the estate stops using one string as both a Frame key and a dist name.

**Type:** docs • **Effort:** S • **Deps:** S-53.5 • **FR/AD:** spec-intelligence-hub
CAP-2
**Surface:** `docs/foundry/frames/**` (9 files),
`src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py`,
its unit test, `docs/foundry/frames/README.md`, the `frame-preflight` pixi
task description. Operator ruling 2026-09-14: adopt v0.3 now rather than start
from an outdated version — this overrides `spec-vocabulary-one-name-one-job`'s
Non-goal "chasing frame-spec v0.3 before PR #28 merges", which is amended in
the same change.
**Given** 53.5 left the nine Frames on `identifier: pyforge-<station>` (a bare
`name-ref`), slug `name:` values, and scalar `maintainer`/`inherits`
**When** this story lands
**Then** every Frame carries a `qualified-ref` identifier (`pyforge/company`,
`pyforge/<station>`) with exactly one `/` and no `@` (v0.3 §4.2.1, §5.3)
**And** `name` is the Charter's prose form (`PyForge Steward`), since the
element profile marks `title` MUST NOT be slug-constrained
**And** `maintainer` and `inherits` are sequences (§6.2.1 "A writer MUST emit a
sequence"), with `owner:` collapsed into the registered `maintainer`
**And** the aliases `name`/`inherits` are KEPT — §6.2.1 requires them of a
Markdown writer; `title`/`composition` belong to the YAML/JSON encodings
**And** the preflight keys identity off `identifier`, reports a scalar
repeatable, and still resolves a `path-ref` parent
**Status:** done

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `53-6-frame-identity-is-the-qualified-ref-identifier-not-the-name: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
