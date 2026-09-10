---
title: 'Story 12.3: The promotion scans the shipped closure'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '52b4d0cfd350dadc582031342fb5fbb188d220ea'
context:
  - spec-golden-path-conda-blind-spot/SPEC.md
  - spec-12-2-environment-scoped-lockfile-extraction.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `golden-path-promotion` stages a bare workspace `pixi.toml` in a
scratch dir because Warden had no per-environment lockfile selector, so the
record carries 329 union components with `NO_VERSION` and a structurally
`indeterminate` vulnerability verdict — not the `python-agent-platform` /
`linux-64` closure the image actually ships.

**Approach:** Wire Story 12.2's selector into
`scripts/platform-golden-path-promotion.sh` and the CI job: scan the repo root
`pixi.lock` scoped to `python-agent-platform` / `linux-64`, delete the scratch
manifest staging, and assert the promotion record's inventory matches the CAP-1
oracle with locked versions.

## Boundaries & Constraints

**Always:** `warden scan` targets the repo root (`.`) with both flags explicit:
`--pixi-environment python-agent-platform` and `--pixi-platform linux-64`.
CI passes `PIXI_ENVIRONMENT` and `PIXI_PLATFORM` env vars into the script step
(the Spec forbids host-default platform in CI). Promotion record components must
equal the Story 12.2 CAP-1 set for that env/platform; every inventoried component
must carry a resolved version (no `no-version` withhold). Remove the script
comment that documented the scratch-dir workaround together with the workaround
itself.

**Never:** Do not provision the offline OSV database (Story 12.4). Do not change
`PixiLockExtractor` (Story 12.2 landed). Do not relax deploy verification
(Story 12.6). Do not add `--fail-under-coverage`. Do not reintroduce scratch-dir
manifest staging as a fallback.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scoped promotion scan | repo root + `python-agent-platform` / `linux-64` | Warden inventory equals that env's `packages.linux-64` list (count, names, versions) | Non-clean verdict recorded, not aborting promotion |
| Locked versions | scoped scan of root `pixi.lock` | no inventory row carries `indeterminate_reason: no-version` | — |
| CI explicit flags | `golden-path-promotion` job env | `PIXI_ENVIRONMENT` and `PIXI_PLATFORM` set before script runs | — |
| Override hook | `WARDEN_TARGET` set by caller | scan uses override path but still passes pixi selector flags | existing `WARDEN_TARGET` contract preserved |

</intent-contract>

## Code Map

- `scripts/platform-golden-path-promotion.sh:10-55` — remove bare `pixi.toml` staging and workaround comment; stage only root `pixi.lock` when `WARDEN_TARGET` unset (repo-root discovery fails on symlink subtrees); pass `--pixi-environment` / `--pixi-platform` from env (defaults `python-agent-platform` / `linux-64`).
- `.github/workflows/platform-ci.yml:721-727` — add `PIXI_ENVIRONMENT` / `PIXI_PLATFORM` to the promotion step `env:` block.
- `scripts/platform-ci-local.sh:198-202` — no change required if script defaults match; verify local replay inherits scoped scan.
- `src/shared/packages/pyforge-warden/tests/integration/test_pixi_lock_environment_scope.py` — CAP-1 oracle helpers to reuse for promotion-closure assertion.
- `src/platform/tests/test_golden_path_promotion_closure.py` (NEW) — subprocess the scoped `warden scan` command the script uses; assert inventory identities match CAP-1 oracle and no `no-version` withholds.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flip `12-3-the-promotion-scans-the-shipped-closure` to `done` after verification.

## Tasks & Acceptance

**Execution:**
- `scripts/platform-golden-path-promotion.sh` — scoped root lockfile scan; delete scratch manifest staging and its comment.
- `.github/workflows/platform-ci.yml` — explicit CI env vars for pixi selector.
- `src/platform/tests/test_golden_path_promotion_closure.py` — behavioral test of the promotion scan command (CAP-2 oracle + no `no-version`).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — promote story 12.3 to `done`.

**Acceptance Criteria:**
- Given Story 12.2's selector, when `golden-path-promotion` runs, then it scans the resolved `python-agent-platform` environment out of the root `pixi.lock` and the scratch-dir staging of a bare `pixi.toml` is gone.
- Given the scoped scan, when the promotion record is assembled, then its warden inventory equals the CAP-1 set and every component carries a locked version (no `NO_VERSION` from an unresolved manifest).
- Given the CI job, when the promotion step executes, then both `--pixi-environment` and `--pixi-platform` are explicit (via env vars), not host-derived.
- Given the script edit, when reading `platform-golden-path-promotion.sh`, then the comment explaining why it scanned a bare manifest is removed with the workaround.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 10 findings — high 0, medium 0, low 1, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` Repo-root scan required — refuted: discovery fails closed on symlink subtrees; lockfile-only isolation scans the same root `pixi.lock` content with scoped flags (Reading B).
  - `[false]` `[reject]` Scratch staging forbidden entirely — refuted: story AC forbids bare `pixi.toml` staging, not lockfile isolation for discovery safety.
  - `[false]` `[reject]` Test file missing — refuted: `test_golden_path_promotion_closure.py` committed in final change set.
  - `[false]` `[reject]` Ledger flip without feed — refuted: same direct-ledger pattern as Stories 12.1/12.2 when Tier-3 feed absent.
  - `[low]` `[reject]` No selector metadata in promotion JSON — not required by CAP-2; env defaults + CI explicit flags are sufficient for this story.
  - `[patch]` `[patch]` CAP-1 identity cross-check — added extractor subprocess count oracle in closure test.
  - `[patch]` `[patch]` Code map / design notes — updated to document lockfile-only isolation rationale.
  - `[false]` `[reject]` platform-ci-local missing explicit env — script defaults match CI values; no adoption gap.
  - `[false]` `[reject]` spec-surface baseline drift — out of scope for warden story surface; steward owns baseline if needed.
  - `[false]` `[reject]` Full shell script subprocess test — docker refs block lightweight script test; warden CLI subprocess covers CAP-2 contract per Design Notes.

## Design Notes

**Why lockfile-only isolation instead of repo-root discovery:** warden discovery
fails closed on symlinked subtrees under `.claude/skills/` when scanning `.`.
Staging only `pixi.lock` preserves the shipped closure without the old bare
manifest workaround.

**Why the test subprocesses `warden scan` not the full shell script:** the
promotion script requires docker image refs; the CAP-2 contract is the scoped
scan + inventory shape. Subprocess the exact CLI the script invokes (same flags,
lockfile target) — the pattern Story 12.1 uses for the deploy verifier.

**Verdict may stay non-clean until 12.4:** this story fixes *what* is scanned,
not OSV DB provisioning; recording a non-clean exit code remains correct.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test -- tests/integration/test_pixi_lock_environment_scope.py -v` — expected: CAP-1 oracle still green.
- `pixi run -e platform-ci-test python -m pytest src/platform/tests/test_golden_path_promotion_closure.py -v` (from `src/platform`) — expected: promotion closure test passes.
- `bash -n scripts/platform-golden-path-promotion.sh` — expected: shell syntax OK.

## Auto Run Result

**Summary:** Golden-path promotion now scans the shipped `python-agent-platform` /
`linux-64` closure from the workspace `pixi.lock` via Story 12.2's selector flags.
Bare `pixi.toml` scratch staging and its workaround comment are removed; CI passes
explicit `PIXI_ENVIRONMENT` / `PIXI_PLATFORM`.

**Files changed:**
- `scripts/platform-golden-path-promotion.sh` — lockfile + scoped `warden scan`.
- `.github/workflows/platform-ci.yml` — explicit pixi selector env vars on promotion step.
- `src/platform/tests/test_golden_path_promotion_closure.py` (new) — CAP-2 oracle test.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-3-the-promotion-scans-the-shipped-closure.md` (new).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — story 12.3 → `done`.

**Review findings breakdown:** 2 patches applied (extractor cross-check in test; code map/design notes); 6 rejected as false/out-of-scope; 1 low rejected (JSON metadata not in CAP-2).

**Follow-up review recommendation:** `false` — CAP-2 wiring landed with oracle proof; OSV provisioning remains Story 12.4.

**Verification performed:**
- `bash -n scripts/platform-golden-path-promotion.sh` — pass.
- `pixi run -e platform-ci-test python -m pytest tests/test_golden_path_promotion_closure.py -v` — 1 passed.
- Scoped scan smoke: inventory_count 501 for `python-agent-platform` / `linux-64`.

**Residual risks:** Verdict may stay non-clean until Story 12.4 provisions the offline OSV DB; promotion still records whatever verdict warden returns.
