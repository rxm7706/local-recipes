---
title: 'Story 17.2 — Every local recipe carries its internal metadata, stripped on push'
type: 'docs'
created: '2026-09-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Strip-on-push half of CAP-2 was not independently re-checked against a
      real published feedstock file on the 2026-09-11 realization-gate pass.
    evidence: >-
      Spec verified: line (git `0cf57f3389` SPEC.md) and epics.md Story 17.2
      Status: meta-test 6/6 including the cfe-conda-name duplicate-key guard;
      absence of cfe-* on a live published feedstock rests on SKILL.md step 8b
      / G60 / G62 and prior worked examples.
    location: .claude/skills/conda-forge-expert/SKILL.md (step 8b, G60, G62)
    severity: medium
declared_low_risk: true
updated: '2026-09-18'
---

<intent-contract>

## Intent

**Problem:** The factory needs local-only provenance (`extra: cfe-*`, `# CFE metadata`
/ `# CFE comments` blocks) without leaking those fields into conda-forge. CAP-2 was
in force but undecomposed as a Story.

**Approach:** Retroactively record the practice: every local recipe carries the
`cfe-*` block (identity, cached decisions, build record, cf-status). SKILL.md
step 8b strips it before push (G60/G62). A duplicate-key guard (`cfe-conda-name`)
keeps the block parseable. No new implementation.

## Boundaries & Constraints

**Always:**
- Every local recipe carries `cfe-*` internal metadata.
- Strip removes exactly `extra.cfe-*` keys and the two bottom `# CFE …` blocks —
  never the schema header or `context:` (G60).
- Strip is verified on the pushed artifact, not assumed (G62).
- Duplicate `cfe-conda-name` keys fail the parse audit (PyYAML silently keeps the
  last key; rattler-build's strict parser rejects them).
- Volatile atlas metrics are never cached in `cfe-*` fields.

**Never:**
- Never ship `cfe-*` keys or `# CFE` blocks in a feedstock / staged-recipes PR.
- Never mint `.claude/skills/pyforge-mason/`.
- Never edit `recipes/**` as part of this promotion.
- Never hand-edit `sprint-status-ledger.yaml`.
- Never treat the 2026-09-11 meta-test pass as independent proof of strip-on-push.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Local recipe | `recipes/<name>/recipe.yaml` | `extra.cfe-*` present for identity / decisions / build record | Missing block is a factory-tooling gap, not an upstream defect |
| Step 8b strip | Recipe copied to fork / staged-recipes | `cfe-*` and `# CFE` blocks absent; `schema_version` + `context:` survive | G60 over-strip is a render-fatal defect |
| Duplicate `cfe-conda-name` | Fold-then-restamp corruption | Parse audit reds | Do not land |
| Published feedstock re-check | Realization-gate 2026-09-11 | Meta-test half PASS; strip half not re-fetched | Residue stays on the Spec, not resolved here |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/SKILL.md` — `cfe-*` field contract, step 8b strip, G60, G62.
- `.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py` — parse + `cfe-conda-name` duplicate-key guard.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship/` — CAP-2 (folded pointer; body in git `0cf57f3389`).

## Tasks & Acceptance

**Execution:**
- `docs` — bind CAP-2 to Story 17.2 (already in `epics.md`).
- `docs` — this file is the tracked story-spec promotion.

**Acceptance Criteria:**
- Given `extra: cfe-*` is local-only internal metadata, when this practice is in force, then every local recipe carries it and SKILL.md step 8b strips it before push.
- And a duplicate-key guard (`cfe-conda-name`) keeps the block parseable.
- Status: done — re-verified 2026-09-11 (meta-test half): parse audit including the duplicate-key guard 6/6 passing. Residue recorded on the Spec: strip-on-push was not independently re-checked against a real published feedstock file that pass.

## Spec Change Log

- 2026-09-18: Promoted tracked `spec-<ledger-key>.md` from `epics.md` + CAP-2 verified line. No new implementation.

## Review Triage Log

None — retroactive contract-spec. CAP-2 strip residue carried as `deferred` above.

## Design Notes

Deps: S-17.1. Rules 1/2 apply because this is CFE-surface metadata, but this
promotion does not run a Rule-2 retro — the practice already lives in SKILL.md.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py -q` — expected: pass.

**Landing evidence:**
- Epic mint `92c419b052` (2026-09-14).
- CAP-2 verified line at HEAD `b36c8be118` (2026-09-11).

## Auto Run Result

Status: done

**Summary:** Practice already in force. This file is the missing tracked story spec
for ledger key `17-2-every-local-recipe-carries-its-internal-metadata-stripped-on-push`.
