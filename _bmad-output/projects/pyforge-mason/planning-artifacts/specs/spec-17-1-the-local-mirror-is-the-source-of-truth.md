---
title: 'Story 17.1 — The local mirror is the source of truth'
type: 'docs'
created: '2026-09-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: true
updated: '2026-09-18'
---

<intent-contract>

## Intent

**Problem:** `spec-fleet-stewardship` CAP-1 (local-mirror-first) was in force as a
practice but had no numbered Story, so `chain-completeness`'s delivered-Spec arm
treated the shipped Spec as undecomposed. Recipe work could still be imagined as
happening first on a feedstock.

**Approach:** Retroactively record the already-in-force practice: edit
`recipes/<feedstock>/` first, verify with a real local build, then push. The
repo-wide `test_recipe_yaml_parse_audit.py` keeps the mirror machine-checkable.
This story documents a continuous practice; it does not add a new implementation.

## Boundaries & Constraints

**Always:**
- Local mirror is edited first, built locally, then pushed to fork/feedstock
  (auto-memory `feedback_local_mirror_first_then_verify_then_push`).
- Every `recipes/<name>/` is a faithful, buildable mirror (recipe + conda-forge.yml
  + patches + LICENSE sidecars).
- The parse audit
  (`.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py`)
  stays green.
- `surface-drift: exempt` on `recipes/**` — per-recipe governance is the CFE
  workflow, not spec re-derivation.
- CLAUDE.md Rules 1 and 2 apply to every campaign wave that touches recipes.

**Never:**
- Never push an unproven change to a feedstock or staged-recipes.
- Never author a new file under `docs/specs/` (legacy Tier 1).
- Never mint `.claude/skills/pyforge-mason/`.
- Never hand-edit `sprint-status-ledger.yaml`.
- Never add a new story or change Epic 17's existing keys.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Recipe change | Maintainer needs a feedstock edit | Edit `recipes/<name>/` first; local build green; then push | Unproven push is out of contract |
| Parse audit | Every `recipes/*/recipe.yaml` | `yaml.safe_load` + `cfe-conda-name` duplicate-key + stray-`[]` + unquoted-`#` checks pass | Fail the meta-test, do not land |
| Continuous practice | Commits keep touching `recipes/` | CAP-1 remains exercised; not a one-shot feature | Dormancy of campaigns is Epic 17.3, not this story |
| Surface-drift | Recipe files change constantly | Coverage-only; drift exemption printed, never silent | Do not stamp `recipes/**` into a spec-surface files map |

</intent-contract>

## Code Map

- `recipes/**` — product line (`surface-drift: exempt`); read-only for this promotion.
- `.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py` — G92/G98 parse + duplicate-key audit.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship/` — owning Spec (folded pointer; CAP-1 text in git history `0cf57f3389` and `.memlog.md`).
- `docs/dreams/fleet-stewardship.md` — archived practice Dream (folded into the mason station Dream).

## Tasks & Acceptance

**Execution:**
- `docs` — bind `spec-fleet-stewardship` CAP-1 to Story 17.1 in `epics.md` (already landed 2026-09-14).
- `docs` — this file is the tracked story-spec promotion of that already-done row.

**Acceptance Criteria:**
- Given recipe work could be done directly on a feedstock, when this practice is in force, then the local mirror is edited first, verified with a real build, and only then pushed.
- And the parse audit holds the mirror machine-checkable.
- Status: done — re-verified 2026-09-11 at `b36c8be118`: 72 commits touched `recipes/` since 2026-08-10; `test_recipe_yaml_parse_audit.py` 6/6 passing.

## Spec Change Log

- 2026-09-18: Promoted tracked `spec-<ledger-key>.md` from `epics.md` + CAP-1 verified line. No new implementation.

## Review Triage Log

None — retroactive contract-spec for a `done` practice story. No new code review loop.

## Design Notes

Epic 17 is explicitly retroactive: the three CAPs were re-verified PASS on 2026-09-11
and the stories were minted 2026-09-14 (`92c419b052`) so the shipped Spec would
appear decomposed. Unlike mason's other epics this Spec governs a continuous
practice over `recipes/**`.

Greenfield note (consult at steward S-44.8, not here): after foundry cutover most
of `recipes/**` archives with local-recipes. This story does not change that.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py -q` — expected: pass (6 tests at the 2026-09-11 stamp).

**Landing evidence:**
- Epic mint `92c419b052` (2026-09-14).
- CAP-1 verified line at HEAD `b36c8be118` (2026-09-11).

## Auto Run Result

Status: done

**Summary:** Practice already in force. This file is the missing tracked story spec
for ledger key `17-1-the-local-mirror-is-the-source-of-truth`.
