---
title: 'Adopt the frame-spec v0.3 working draft'
type: 'docs'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 53.2 adopted a private v0.2 four-field preflight because
`openteams-ai/frame-spec` had no LICENSE. B never received Frames. The
plot was to start B from the spec repo.

**Approach:** Consume the v0.3 working draft (#28) and Apache-2.0 now.
Plant the nine Frames on B. Adjust when the draft freezes.

## Boundaries & Constraints

**Always:**
- `type: frame [0.3]`; keep `name` / `inherits` aliases.
- `license: https://www.apache.org/licenses/LICENSE-2.0`

**Never:**
- Never open a second LICENSE PR on frame-spec (#28 already adds it).
- Never bind CI to unmerged `validate_frame.py` until #29 lands.

</intent-contract>

## Acceptance Criteria

1. Nine A Frames use `frame [0.3]` + Apache-2.0 IRI + `identifier`.
2. B has the same nine files under `docs/foundry/frames/`.
3. Preflight accepts any `type` whose first word is `frame`.
4. Comment on frame-spec#28 records the adoption.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `53-5-adopt-the-frame-spec-v0-3-working-draft: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
