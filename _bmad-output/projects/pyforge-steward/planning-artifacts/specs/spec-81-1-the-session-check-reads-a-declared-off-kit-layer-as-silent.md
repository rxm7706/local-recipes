---
title: "81.1: The session check reads a declared-off kit layer as silent"
type: 'fix'
created: '2026-10-01'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-steward/tests/unit/test_session.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** every `marshal factory dispatch` journals MRS-DISP-049: steward's session check reports `token-kit`
non-ok because the kit item `ccr-store` reads `layer-off`. Marshal's kit contract makes `ok` and `layer-off` its two
silent outcomes (`seed/detect/kit.py::KitStatus`: "`OFF` and `OK` are the two silent outcomes (no finding)"), and the
session check's own design says finding (3) reuses marshal's verdict. `session.py::_seed_kit_findings` instead fails
any status other than `ok`, as CAP-162's success line (Story 73.1) recorded. The false warning on every launch hides
the real ones the same finding carries.

**Approach:**

- `_SILENT_KIT_STATUSES = frozenset({"ok", "layer-off"})` in `session.py`, with a comment citing marshal's contract.
  `token-kit` fails only on an item whose status is not in it; its ok detail names every item with its real status.
- `codegraph-index` follows the same rule; a `layer-off` entry reads ok with the detail
  `codegraph-index: layer-off -- <marshal's detail>`.
- An unknown status is not silent, so it still fails (fail closed).

Ledger key: `81-1-the-session-check-reads-a-declared-off-kit-layer-as-silent`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- CAP-162 (Story 73.1), amended 2026-10-01: a defect of its per-item rule, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a kit whose only non-`ok` item is `ccr-store: layer-off` When `_seed_kit_findings` runs Then `token-kit` is ok with the detail `caveman-skill: ok; ccr-store: layer-off; codegraph-index: ok` and `codegraph-index` is ok
- Given a `codegraph-index` entry at `layer-off` When `_seed_kit_findings` runs Then both findings are ok and the `codegraph-index` detail names `layer-off`
- Given one item at `missing`, `stale`, `instrument-unavailable` or `no-such-status`, or a status that is not a string (a list, a dict, `None`, a number) When `_seed_kit_findings` runs Then both findings fail, naming that status, and nothing raises
- Given the recorded 2026-09-28 document (`missing` / `layer-off` / `missing`) When it is read Then `token-kit` names the two `missing` items and not `ccr-store`

## Boundaries & Constraints

**Always:**
- Steward shells `marshal seed check --json`; it never imports `pyforge.marshal`.
- An unknown status, or one that is not a string, fails closed.

**Never:**
- Do not change what `marshal seed check` reports.
- Do not silence `stale`, `missing` or `instrument-unavailable`.

</intent-contract>

## Binding

Parent capabilities: CAP-162 (amended 2026-10-01; defect of Story 73.1's per-item rule, no new CAP). FR-35.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 (later) entry.
Ledger key: `81-1-the-session-check-reads-a-declared-off-kit-layer-as-silent`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix the false `token-kit` warning now, not in the deferral burn-down's Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild steward session check --json` in a dispatch worktree — expected: no `token-kit`
  finding naming `ccr-store: layer-off`.

## Review Triage Log

Review 1 (2026-10-01): an independent read-only reviewer read the diff against this spec, CAP-162 and marshal's
`seed/detect/kit.py`. It confirmed the premise (`KitStatus` OFF and OK raise no finding; the wire layer defaults to
`"auto"`, which `layer_enabled` reads as off) and that no consumer of the session check depends on `layer-off` being
non-ok. No high findings; all six fixed in this change:

- `[medium]` `[patch]` CAP-162's amended success line named the 2026-09-28 statuses (`instrument-unavailable`), not the
  recorded document's (`missing` / `layer-off` / `missing`, Story 73.1's recorded deviation). Fixed: memlog entry, then
  the render route.
- `[low]` `[patch]` A status that is not a string (a list, a dict) raised `TypeError` out of the set lookup, which the
  `AttributeError` guard did not catch. Fixed: `_kit_status_is_silent` fails closed on any non-string; parametrized test.
- `[low]` `[patch]` The Dream entry and an earlier memlog line blamed marshal 80.1 for the warning; 80.1 did not touch
  MRS-DISP-049. Fixed in the Dream; the memlog is corrected by an appended entry.
- `[low]` `[patch]` "declared-off, not missing" was attributed to `KitStatus` (it is kit.py's module docstring), and two
  texts called the wire layer "declared off" when it is `"auto"` read as off. Fixed in session.py, CAP-162, the epic
  and the AC1 test docstring.
- `[low]` `[patch]` AC4 was asserted against a value derived from the fixture. Fixed: a literal assertion.
- `[low]` `[patch]` Pre-existing: a non-ok `codegraph-index` with no detail ended in a stray `--`. Fixed.

## Auto Run Result

Hand-built in an interactive session on the operator's ruling of 2026-10-01 (fix it now). Verification:

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py -q`
  — exit 0: 62 passed, 2 skipped (the two that need the `marshal` CLI or doctor installed).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — run by `pr-preflight` on push.
