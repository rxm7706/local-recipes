---
title: "72.2: Mason's five-tier skill cell requires its station skill and conda-forge-expert"
type: 'fix'
created: '2026-09-28'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-19-1-mason-s-station-skill-is-skf-compiled-exported-and-consulted-by-the-persona.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `five_tier.detect_tiers` counts a station's `skill` cell present when `.claude/skills/pyforge-<station>/` holds a
`SKILL.md` — except Mason's, which it counts present when `.claude/skills/conda-forge-expert/SKILL.md` exists
(`src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py:104-106`, "Mason 11.1: CFE is the domain skill. Do
not require pyforge-mason/"; the `DECLARED_COMPLETE` comment at `:25-27` says the same). The operator ruled on 2026-09-28
that Mason has its own skills and CFE is one of them, and that the five-tier check requires both (`spec-pyforge-mason`
CAP-29, question 4).

**Approach:** in `detect_tiers`, Mason's `skill` cell is the general rule **and** CFE: present only when
`.claude/skills/pyforge-mason/` holds a `SKILL.md` and `.claude/skills/conda-forge-expert/SKILL.md` exists. The carve-out
comment and the `DECLARED_COMPLETE` comment are replaced by one that cites the ruling and CAP-160. In
`tests/meta/test_five_tier_check.py`, `test_live_roster_is_five_tier_complete`'s docstring ("Mason's skill is CFE") is
corrected, and two fixture tests are added — a tree holding only `conda-forge-expert/SKILL.md` and a tree holding only
`pyforge-mason/…/SKILL.md` each read Mason's cell missing, and `check` fails naming `skill`.

**Blocked until mason Story 19.1 has landed; the operator flips it.** Before `.claude/skills/pyforge-mason/` is on `main`,
the new rule reads Mason's cell missing and the live roster test reds. The ledger key is minted `blocked` because
marshal's `Deps:` parser is station-local, so a cross-station precondition has to be a ledger gate (AGENTS.md § Known
pitfalls; herald 27.5 is the precedent). Do not start this story while 19.1 is unlanded.

**Unblocked 2026-10-10.** The operator ruled "lets look at each one of these and see if we can get them moving and
complete them" (spec memlog). Mason Story 19.1 is `done` in mason's ledger, and its skill is on `main` (`6d5e84cb6b`) at
`.claude/skills/pyforge-mason/0.1.0/pyforge-mason/SKILL.md`. The path in the epic's Given,
`.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md`, does not exist: there is no `active/` twin. So the AC's
rule, "`.claude/skills/pyforge-mason/` holds a `SKILL.md`", matches at any depth under that directory, which is what
`detect_tiers`' general rule already does (`skill_root.rglob("SKILL.md")`, `five_tier.py:103`). Do not add a fixed
`active/` or `0.1.0/` path; the first fixture's AC below already uses the versioned path.

Ledger key: `72-2-mason-s-five-tier-skill-cell-requires-its-station-skill-and-conda-forge-expert`.
Ledger status (do not edit the ledger): `backlog` (flipped from `blocked` on 2026-10-10 by the operator's ruling).
Type / Effort / Deps: fix / S / — (cross-station gate above).

### Living CAP citations

- `spec-pyforge-steward` CAP-160 (FR-33); canopy:AD-14 (five-tier completeness); canopy:AD-17 (SKF station skills; CFE the hand-authored exception); Kinship `spec-pyforge-mason:CAP-29`.

## Acceptance Criteria

- Given the live tree with mason Story 19.1 landed When `five_tier.report` runs Then Mason's `skill` cell is present and the roster reads 40/40 with no failure
- Given a fixture tree with `.claude/skills/conda-forge-expert/SKILL.md` and no `.claude/skills/pyforge-mason/` When `detect_tiers(root, "mason")` runs Then `skill` is `False`, and `check` with Mason declared complete fails naming `skill`
- Given a fixture tree with `.claude/skills/pyforge-mason/0.1.0/pyforge-mason/SKILL.md` and no CFE When `detect_tiers(root, "mason")` runs Then `skill` is `False`
- Given any other station When `detect_tiers` runs Then its `skill` cell follows the unchanged `pyforge-<station>/` rule
- Given `five_tier.py` When it is read Then no comment says Mason's skill cell is CFE alone or "do not require pyforge-mason/"

## Boundaries & Constraints

**Always:**
- Keep `conda-forge-expert` a required half of Mason's cell — CFE is never dropped from the check.
- Co-governors: steward's `src/` is also governed by `spec-pyforge-core`. Add a memlog entry on every Spec
  `spec-surface-check` names, `git add`, one scoped stamp per named Spec from a clean tree, re-check and read the exit
  code; run the chain-currency sweep for each project whose memlog moved.

**Never:**
- Do not start before mason Story 19.1 is on `main`; do not flip this story's ledger key, or any other `blocked` key.
- Do not create `.claude/skills/pyforge-mason/` here — it is mason's (Story 19.1).
- Do not change `TIERS`, `STATIONS`, `DENOMINATOR` or `DECLARED_COMPLETE`'s membership.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| both skills | live tree after 19.1 | Mason `skill` present; 40/40 | — |
| CFE only | fixture | Mason `skill` missing; `check` fails naming `skill` | `FiveTierCompleteError` |
| station skill only | fixture | Mason `skill` missing | as above |
| other station | e.g. steward | unchanged rule | — |
| 19.1 absent | dispatched too early | refused: the ledger key is `blocked` | operator gate |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-160 (FR-33).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 — Proposed: Mason's skill cell is two skills, and the Guild environment answers `pyforge mason`*.
Ledger key: `72-2-mason-s-five-tier-skill-cell-requires-its-station-skill-and-conda-forge-expert`.
Ledger status at mint: `blocked`, until mason Story 19.1 has landed; the operator flips it. Flipped `blocked` → `backlog` 2026-10-10 by the operator's ruling (19.1 `done`), through the Tier-3 feed and `sprint-ledger-sync --project steward --allow-regression`.
Deps: — . Cross-station gate: mason Story 19.1 (`spec-pyforge-mason:CAP-29`).
Minted 2026-09-28 so `marshal factory dispatch` can resolve this spec once the operator unblocks it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; `test_five_tier_check.py` runs inside it).

**Manual checks:**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the co-governor reconcile.

## Spec Change Log

- 2026-10-10: unblocked (mason 19.1 `done`); status `blocked` → `ready-for-dev`; the `blocking_condition` field is removed; the
  Given's `active/` path is noted as absent and the `SKILL.md` rule as recursive. No acceptance criterion changed.

## Review Triage Log
