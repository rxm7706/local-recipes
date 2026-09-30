---
title: "76.2: Every flag in the tree carries its owner, story and cleanup clock in flagd metadata"
type: 'feature'
created: '2026-09-28'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: flag-infrastructure
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/tests/test_openfeature_file_flags.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Guild's gate (`spec-feature-flag-governance` CAP-2, doctor's) must red a flag still in the tree 90 days
after it went ON in every environment (Q4), and must name each flag's owner so the owning station files the removal story.
The tree records none of that: `pyforge.three_surfaces` and `pyforge.cutover_root` carry `state`, `variants` and
`defaultVariant` only, so the clock could only be reconstructed from git history, differently by each reader.

**Approach:** every flag in `src/platform/config/flags.json` carries flagd flag-level `metadata` (string values):

- `owner` — the station token (`steward`, `doctor`, …);
- `story` — the ledger key of the story that introduced the flag;
- `created` — `YYYY-MM-DD`, the day the key entered the tree;
- `on_everywhere` — `YYYY-MM-DD`, the day the flag first read ON in every environment's rendered tree (Story 76.1), or `""`
  while it does not; for a flag with no boolean ON variant (`pyforge.cutover_root`) it stays `""`, so no clock runs;
- `cleanup_by` — `on_everywhere` plus 90 days, or `""` when `on_everywhere` is `""`.

`pyforge.core.flags` gains the check, run wherever the tree is composed, each failure a named error: a missing field, a
malformed date, `on_everywhere` set while some environment's rendered value is not ON (or empty while every one is ON), and
`cleanup_by` other than `on_everywhere` + 90 days. The two existing flags get their real dates from the tree's history
(`git log --follow src/platform/config/flags.json`: `pyforge.three_surfaces` entered with Story 26.4 on 2026-08-25,
`7a194d3f57`, reading `on` everywhere, so its `cleanup_by` is 2026-11-23; `pyforge.cutover_root` entered with Story 44.12
on 2026-09-13). `pyforge.three_surfaces`'s clock runs out on 2026-11-23. The operator ruled on 2026-09-28 (night) to
remove it rather than keep it as a kill switch: Story 76.4 (`Deps: S-76.2`) removes it after this story lands. So this
story writes its metadata like any other flag's, and its result names it and its date as owed to Story 76.4. The result
also names every other flag whose `cleanup_by` has passed at landing as owing a removal story or a keep decision from its
owner (Q4); filing either is the owner's act, not this story's.

Ledger key: `76-2-every-flag-in-the-tree-carries-its-owner-story-and-cleanup-clock-in-flagd-metadata`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-76.1.

### Living CAP citations

- `spec-feature-flag-governance` CAP-5 ("each flag carries its owner, story key, created date, ON-everywhere date and
  cleanup date in flagd `metadata`"), Q4 (the 90-day clock); CAP-2 reads what this story writes.
- canopy:AD-11 (amended 2026-09-28; the metadata clause).

## Acceptance Criteria

- Given the tree When it is composed Then every flag carries `owner`, `story`, `created`, `on_everywhere` and `cleanup_by` as strings
- Given a flag missing a field, or with `created: 2026-9-1` When the tree is composed Then a named error names the flag and the field
- Given `on_everywhere` set on a flag some environment renders OFF, or empty on a flag every environment renders ON When the tree is composed Then a named error names the mismatch
- Given `cleanup_by` not equal to `on_everywhere` + 90 days When the tree is composed Then a named error names both dates
- Given `pyforge.cutover_root` (string variants) When the tree is composed Then its `on_everywhere` and `cleanup_by` are empty and no error is raised
- Given the tree with metadata When the host's FILE provider and `pyforge.core.flags.evaluate_boolean` evaluate every key in every environment Then the values equal those before the story
- Given `pyforge.three_surfaces` When its metadata is written Then `on_everywhere` is 2026-08-25 and `cleanup_by` is 2026-11-23, and the story's result names it as removed by Story 76.4 (the operator's 2026-09-28 ruling), which lands after this story
- Given the landing When a flag's `cleanup_by` is before the landing date Then the story's result names it and its owner as owing a removal story or a keep decision (Q4)
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep metadata values primitive (strings) so flagd's schema and the in-process provider accept them.
- Read the dates from the tree's own history; record the commands used in the story's result.
- Reconcile every Spec `spec-surface-check` names, then stamp each scoped with `--spec`.

**Never:**
- Do not remove a flag or file its removal story here; do not implement the Guild's gate (doctor's CAP-2 stories).
- Do not add a metadata field outside the five without a Guild memlog entry (the gate reads exactly these).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| complete | five fields, consistent | composes | — |
| missing field | no `owner` | — | named error |
| bad date | `2026-9-1` | — | named error |
| clock without ON | `on_everywhere` set, production OFF | — | named error |
| ON without clock | ON everywhere, `on_everywhere` empty | — | named error |
| wrong cleanup | `cleanup_by` ≠ +90 days | — | named error |
| string flag | `pyforge.cutover_root` | empty clock | — |
| running clock | `pyforge.three_surfaces`, `cleanup_by` 2026-11-23 | named in the result with its date, as owed to Story 76.4 | — |
| expired clock | `cleanup_by` before landing | named in the result as owing removal or a keep decision | — |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-5 and Q4, and the `spec-pyforge-steward`
memlog note of 2026-09-28 (night) recording Epic 76's shape.

## Binding

Parent Spec capability: `spec-feature-flag-governance` CAP-5 (the Guild's Spec; no station CAP or FR is minted).
Dream: `docs/dreams/feature-flag-governance.md`.
Ledger key: `76-2-every-flag-in-the-tree-carries-its-owner-story-and-cleanup-clock-in-flagd-metadata`.
Ledger status at mint: `backlog`.
Deps: S-76.1 (the rendered per-environment trees the clock is defined over).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q` — expected: pass
  (the metadata check's cases).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `test_openfeature_file_flags.py` passes with the
  metadata-bearing tree.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log

## Auto Run Result

Status: blocked
Blocking condition: spec failed ready-for-development standard (Sufficient) — dependency Story 76.1 has not landed on this base.

Evidence (2026-09-29, `dispatch/pyforge-steward/76.2` at `a468651c83`):

- Ledger row `76-1-the-one-flag-tree-carries-per-environment-values-so-off-in-production-is-a-value` is `backlog`; its PR is open
  (rxm7706/local-recipes#1683, branch `dispatch/pyforge-steward/76.1`, not an ancestor of this `HEAD` per
  `git merge-base --is-ancestor`).
- `src/platform/config/flag-overlays.json` does not exist on this base (`git ls-files | grep flag-overlay` is empty), yet it
  is in this spec's `context:` and defines the per-environment rendered trees `on_everywhere` is measured over.
- `pyforge.core.flags` has no `evaluate_boolean` (only `read_boolean`, `require`, `disabled_help`); AC 6 and the
  "check run wherever the tree is composed" both bind to 76.1's composer. 76.1's diff adds it (`flags.py` +170 lines).
- Building on the unmerged 76.1 branch would stack this story on a moving base (76.1 already carries a follow-up
  commit); the Deps gate is `S-76.1` and it is not met.

Also for the re-plan, once 76.1 lands:

- `src/platform/config/flags.json` now holds three flags, not "the two existing flags": `pyforge.steward.ghe_fleet_credentials`
  (`defaultVariant: off`) needs `owner`/`story`/`created` with an empty clock; read its dates from
  `git log --follow src/platform/config/flags.json` like the others.
- `pyforge.three_surfaces` remains owed to Story 76.4 (`on_everywhere` 2026-08-25, `cleanup_by` 2026-11-23, per the
  operator's 2026-09-28 ruling); no other flag has a passed `cleanup_by` as of this run.

Next: land #1683, then re-dispatch Story 76.2. No source, ledger or `SPEC.md` file was touched; no `deferred:` entry written.
