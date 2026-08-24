---
title: Code-status preservation
type: feature
created: '2026-08-23'
status: in-progress
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 12be18be5a65bf2f4f9a1af2b3ab9442e039dd26
---

<intent-contract>

## Intent

**Problem:** `marshal planning chain-regenerate` (21.2) can rewrite epics/stories and wipe recorded done/in-progress/backlog status — CAP-2 requires regeneration never clobber Code implementation status (FR-192; spec-fleet-chain-completeness).

**Approach:** Before regenerating epics/stories, snapshot each story's development status from the sprint ledger / epics.md; after phase 6, re-apply preserved statuses onto regenerated story keys (match by stable story id). Default `preserve_code_status=true`; opt-out only via explicit flag. Deps: 21.2 done (PR #707). Do not implement orphan apply (21.4) or CAP-5 param polish (21.5) beyond the preserve flag.

## Acceptance Criteria

- Re-running chain-regenerate on a partially-implemented project leaves every story's done/in-progress/backlog status byte-identical to pre-run values for matching story keys.
- New stories introduced by regen start as backlog; retired keys are not resurrected as done.
- `preserve_code_status` defaults true; when false, documented opt-out (tests cover both).
- Preservation runs after epics generation and before orphan report; never auto-commit.
- Does not implement Stories 21.4–21.5 beyond the preserve flag.

## Boundaries & Constraints

**Never:** Invent status for unmatched keys. Never auto-commit. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-2)
- Extends: `core/chain_regen.py`, sprint ledger / epics status surfaces
- Tests: preserve round-trip; opt-out; new keys → backlog

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Fixture: pre-seeded done stories survive Full and Minimal regen

## Auto Run Result

Status: in-progress

Summary: Implemented CAP-2 code-status preservation for \`marshal planning chain-regenerate\`: snapshot ledger statuses before the chain, persist \`code-status-snapshot.yaml\` for resume safety, re-apply after the epics phase (before orphan report) by stable story id. New keys → backlog; retired keys not resurrected; \`preserve_code_status\` defaults true with \`--no-preserve-code-status\` opt-out. Never auto-commits.

Verification: \`pixi run -e pyforge-marshal pyforge-marshal-test\` → 6268 passed, 12 deselected.
