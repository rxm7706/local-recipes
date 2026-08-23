---
title: Apply is deliberate, branched, and never clobbers custom
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 60726a8fad3fd33e6211c787667cdf2cf0a6227c
deferred: []
---

<intent-contract>

## Intent

**Problem:** After CAP-1's report-only pre-flight (Story 14.1), there is still no deliberate apply path that snapshots/branches first and never clobbers `_bmad/custom/**` (`spec-bmad-method-core-upgrade` CAP-2).

**Approach:** Given a clean tree and a CAP-1 report, the steward upgrade wrapper snapshots/branches first, runs `bmad-method install --action update -y` non-interactively (installer remains the only writer of `_bmad/bmm/**` / `_bmad/core/**`), refuses to start when legacy-name customization files would halt the shims, and lands the installer diff for review — never applied blind. `_bmad/custom/**` is byte-identical afterward or the run reports why not.

## Acceptance Criteria

- Apply path requires a clean tree and consumes CAP-1 report input (or equivalent pre-flight gate).
- Snapshots/branches before invoking the installer.
- Runs `bmad-method install --action update -y` non-interactively; steward never reimplements writing `_bmad/bmm/**` or `_bmad/core/**`.
- Refuses to start when legacy-name customization files would halt shims (names them).
- Lands installer diff for review — never applied blind to the working tree without a branch/review surface.
- `_bmad/custom/**` is byte-identical after the run, or the run reports why not.

## Boundaries & Constraints

**Never:** Implement CAP-3 re-apply of clobbered custom (Story 14.3), CAP-4 pin fan-out, or CAP-5 verification gate. Never call `scripts/bmad-switch`. Never silently overwrite `_bmad/custom/**`. Foreign-station pin sites are reported, never edited.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — CAP-2 `apply_bmad_core_upgrade` + custom fingerprint / branch helpers extending 14.1
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--apply` / `--branch` / `--installer` on `upgrade bmad-core`
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — branch-first, refuse-legacy, custom preservation / clobber report
- Parent: `spec-bmad-method-core-upgrade/SPEC.md` CAP-2 + `failure-modes.md`

## Design Notes

**CLI surface:** `steward upgrade bmad-core --target X.Y.Z --apply` extends the 14.1 verb rather than adding a sibling. Default (no `--apply`) remains report-only. CAP-1 is consumed in-process as the apply gate (equivalent to requiring a prior report).

**Review surface:** apply creates `steward/bmad-core-upgrade-<target>` (or `--branch`), runs the installer, and leaves the installer working-tree diff on that branch for human review — never auto-merges, never writes `_bmad/bmm/**` / `_bmad/core/**` itself.

**Custom check:** sha256 per file under `_bmad/custom/**` before vs after; byte-identical → ok; otherwise `ok=False` with named paths (CAP-3 re-apply is out of scope).

## Verification

- `pixi run --frozen -e pyforge-steward pytest` targeting upgrade-apply tests
- Fixture proves refuse-on-legacy-custom and custom preservation

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 2, low 1)
- defer: 0
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` branch existence check used `rev-parse` (could match non-heads) — switched to `show-ref --verify refs/heads/<branch>`
  - `[medium]` `[patch]` missing CLI dirty-tree refuse test — added `test_cli_apply_refuses_dirty_tree`
  - `[low]` `[patch]` removed unused `skip_clean_check` escape hatch that could bypass the AC

## Auto Run Result

Status: done

Summary: Extended `steward upgrade bmad-core` with CAP-2 `--apply`: clean-tree gate, in-process CAP-1 preflight (refuse on legacy-name custom with named paths), create review branch first, invoke `bmad-method install --action update -y` (installer sole writer of `_bmad/bmm/**`/`_bmad/core/**`), leave installer diff on the branch for review, and prove `_bmad/custom/**` byte-identical or report why not.

Files changed:
- `upgrade.py` — apply engine, custom fingerprint, review-branch helpers
- `cli.py` — `--apply` / `--branch` / `--installer`
- `tests/unit/test_upgrade_apply.py` — branch-first / refuse-legacy / custom preserve / clobber / dirty-tree
- this spec — status done + triage/result

Review findings: 3 patches applied; 0 deferred; 4 rejected (subagent-unavailable process note; symlink-in-custom edge; auto-commit of installer diff as optional UX; CAP-3 territory).

Follow-up review recommendation: true (patched medium=2, low=1; score `3×2+1=7` ≥ 5).

Verification: `pixi run --frozen -e pyforge-steward pytest` on upgrade apply + full steward suite after patches.

Residual risks: real `bmad-method` must be on PATH for live apply (tests inject `--installer` / runner); CAP-3 still owns re-applying clobbered resolve_config layers.
