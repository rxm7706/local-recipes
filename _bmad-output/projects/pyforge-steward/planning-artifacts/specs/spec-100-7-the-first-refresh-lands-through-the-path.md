---
title: '100.7: The first refresh lands through the path'
type: 'chore'
created: '2026-10-13'
status: 'done'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - docs/how-to/refresh-the-estate.md
  - docs/governance/pin-policy.yaml
  - docs/governance/realization-register.yaml
  - pixi.toml
  - environment.yaml
  - docs/reference/library-llms-full.md
  - docs/reference/bmad-estate-llms-full.md
  - scripts/.spec-surface-baseline.json
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-10-13 hand batch sits uncommitted on the operator's working tree on `main` — 158 pin lines,
about 21,000 lock lines, nine losses, 81 catalog drifts, a stale `environment.yaml`, an unapplied BMAD core
(`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 2). It is superseded, not committed (ruling Q9). The path
Stories 100.1–100.6 build has not yet carried a real batch.

**Approach:** Run the path once, for real, in this story's worktree, and land the result as one PR with its
journal. The agent half runs here; the operator finishes on the branch.

- **The run.** `estate plan` (journaled as the plan); `estate refresh` without `--transitive` (the operator may run
  `refresh --transitive` on the branch afterwards, ruling Q3); `estate realize --plan`, then the operator's
  `realize --yes` on the branch for the `operator_gate` rows (`bmad-method`, `bmad-module-skill-forge`,
  `caveman-installer`); `estate reconcile`; `estate verify` (the default tier; `--all` is the operator's call).
- **The evidence.** The journal records every move and every restored loss; the nine loss classes of the hand
  batch yield zero `--diff` findings after the restore; `--fan-out` is green or the PR waits on the station story
  it names; every register probe reads `live` before merge, except the `operator_gate` rows the operator chose to
  leave `stale` — journaled, repeated by the next refresh; `estate status` shows linux-64 as the confirming
  platform and the other two `lock-solved`.
- **The landing.** The PR carries the `maintenance` label (it touches `pixi.toml`); `environment.yaml` and every
  derived surface ride it; the memlog lines and scoped stamps the reconcile wrote ride it; it merges with the
  marshal subject once lock-solved ×3 and this platform's verify are green (ruling Q14).
- **The hand batch.** The operator discards it from their working tree (`git checkout -- pixi.toml pixi.lock` on
  the primary checkout) once this PR has merged; nothing here touches the primary checkout.

Ledger key: `100-7-the-first-refresh-lands-through-the-path`.
Type / Effort / Deps: chore / S / S-100.6.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the first real run; **CAP-5**: the Guild's size recorded against its
  bound; **fnd:CAP-12**: `pyforge-foundry-full` in the verify tier, `sbom-gaps.md` current.
- **Flag:** none — a chore; it runs with Story 100.2's flag on in dev.
- **Origin.** The 2026-10-13 Dream entry; rulings Q3, Q9, Q12, Q14.

## Acceptance Criteria

- **AC1 — Journal.** `.steward/estate-refresh/<date>.json` validates against the schema and carries `plan`,
  `moves`, `losses_restored`, `fan_out`, `realize`, `reconcile` and `verify` blocks with `platform: linux-64`.
- **AC2 — Zero losses.** `pin_policy_check.py --diff <base>` over the landed `pixi.toml` yields zero findings;
  every cap, table and floor the hand batch lost is present at its clause.
- **AC3 — Green derived surfaces.** `llms-full-check`, `bmad-estate-check`, `pixi-version-check`,
  `target-version-check`, `sbom-gaps-check`, `platform-policy-suite-check`, `pin-policy-check`,
  `realization-register-check` and `pixi lock --check` exit 0 on the branch; `environment.yaml` equals the
  exporter's output.
- **AC4 — Verified.** Every default-tier environment installed; every selected lane green or journaled paused;
  every register probe `live` except the journaled `operator_gate` rows; `estate status` reads linux-64 confirmed,
  `osx-arm64` and `win-64` lock-solved.
- **AC5 — Landed.** The PR carries `maintenance`, merges with the marshal subject, and the story spec's Auto Run
  Result cites the journal path, the move count, the loss count restored and the BMAD block.

## Boundaries & Constraints

- Nothing touches the primary checkout or the operator's hand batch.
- `--transitive` and `realize --yes` are the operator's, on the branch, after the dispatched run.
- A red `--fan-out` is not fixed here: the PR waits on the station's story.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| the channel moved since 2026-10-13 and more packages move | journaled; the loss classes are still judged against the policy, not against the hand batch |
| `--fan-out` reds on a station range | the run stops before `reconcile`; the station is named in the journal and the PR body |
| the operator skips `realize --yes` | `bmad-method` row `stale`, journaled; `verify` red on that row is recorded as the operator's accepted gap in the PR body |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-7-the-first-refresh-lands-through-the-path`.
- Ledger status at mint: `backlog`.
- Deps: S-100.6. `marshal factory dispatch` stamps `baseline_revision` with the launch commit (Story 100.1's run did), so no
  hand re-base is needed.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pyforge steward estate status` — expected: exit 0, the run's journal printed (AC1, AC4).
- `pixi run --frozen -e pyforge-guild python scripts/pin_policy_check.py --diff origin/main` — expected: exit 0 (AC2).
- `pixi run --frozen -e pyforge-guild llms-full-check`, `bmad-estate-check`, `pixi-version-check`, `target-version-check`, `sbom-gaps-check`, `platform-policy-suite-check`, `pin-policy-check`, `realization-register-check` — expected: exit 0 each (AC3).
- `pixi lock --check` — expected: exit 0 (AC3, all three platforms).
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` — expected: pass (the shared-surface rule: a `pixi.toml` change runs every station).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-14: unblocked (operator ruling: every held package excluded; the refresh converges past a
  lowered floor). Hand-driven landing. Each defect the run found was fixed on the branch:
  - The pixi 0.8x upgrade JSON shape.
  - Realize steps and probes run in each row's env.
  - Reconcile's no-op seams, and its checks now run in the Guild env.
  - Verify's lanes, env choice, kit rows, installed marker, Guild bound and journal merge.
  - Probes for six register rows and the playwright row.
  - The liquibase floor test and ruff 0.17.0's import order.
  Open follow-ups: DW-steward-100-7-1 and DW-atlas-steward-100-7-1.
- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100. `type: chore`. Widened the same day: `realize --plan` in
  the run, the operator's `realize --yes` and `--transitive` on the branch, the per-platform confirmation.

## Unblock (2026-10-14, hand-driven after MRS-DISP-045)

Operator ruling 2026-10-14: exclude every held package from the upgrade. The blocked run's
two conflicts were lowered floors on unheld packages, so `estate refresh` also converges: a floor
the upgrade lowers resets `pixi.toml`/`pixi.lock` to base, excludes that package and reruns.

- `upgrade_excludes` (`scripts/pin_policy_lib.py`): every hold kind becomes `--exclude`. The
  `openai` and `cron-descriptor` never-move workarounds are dropped.
- `estate refresh`: converged in two rounds, excluding `cron-descriptor` and `openai`. 108
  packages moved, no policy loss restored, `pixi lock` solved on all three platforms, and
  fan-out came back clean. Journal: `.steward/estate-refresh/2026-10-14.json`. The 2026-10-13
  stub journal is removed.
- `_parse_pixi_moves` reads pixi 0.8x `upgrade --json` (`environment` shape); the old parser
  journaled zero moves, so no realize row was ever due.
- `estate realize`: register steps and probes now run inside each row's env (they ran bare
  and crashed on `osv-scanner` and `pre-commit`). The spec-kit probe runs `specify --version`.
  Every non-gated row reads `live`. Operator gates were skipped: `bmad-method` and
  `bmad-module-skill-forge` read `stale`, `caveman-installer` reads `live`.
- `estate reconcile`: derived docs, the library catalog and the bmad-suite pins were regenerated.
- `pin_policy_check.py --diff origin/main` exits 0.

The two stale gated rows were realized afterwards: the operator ran `estate realize --yes`, and
the BMAD rows were then applied through `steward upgrade bmad-core` (see the Auto Run Result of
2026-10-14). `estate refresh --transitive` was not run.

## Auto Run Result (2026-10-14)

Journal: `.steward/estate-refresh/2026-10-14.json`. It carries the `moves`, `converge`,
`losses_restored`, `fan_out`, `realize_due`, `bmad`, `realize`, `reconcile` and `verify` blocks,
with `platform: linux-64` (AC1).

- **Moves:** 308 `(package, env)` moves. The upgrade converged in 2 rounds, excluding
  `cron-descriptor` and `openai`. Losses restored: 0, and `pin_policy_check.py --diff origin/main`
  exits 0 (AC2).
- **BMAD:** core went from 6.12.0 to 6.12.2 and skf from 2.2.0 to 3.0.0. Both were applied by
  `pyforge steward upgrade bmad-core --target 6.12.2 --apply` with the curated catalog
  `bmad_core_releases/6.12.2.yaml`. Local edits to installer-owned files were re-applied three
  ways, so Mason 27.1's skf edits survive. The operator ran `estate realize --yes` first. That
  raw update dropped those edits, so the tree was restored and the catalog apply replaced it.
  `--transitive` was not run.
- **Realize:** every register row reads `live`. `pre-commit` reads `skipped-worktree`
  (`primary_checkout_only`): hooks are shared through the common git dir.
- **Reconcile:** all eight gating checks and both warn checks exit 0 (AC3). `environment.yaml`
  matches the exporter's output.
- **Verify:** run at `ea1ecaa8e9`. linux-64 is `confirmed`; osx-arm64 and win-64 are
  `lock-solved`. 13 default-tier envs installed. The Guild env measures 1871 MB against a
  2048 MB bound.
  - Lanes: 29 of 34 `ok`, 3 `manual` (atlas browser, herald browser, scribe Postgres).
  - Probes: 32 of 34 `live`. `bmad-suite-full` and `platform-dev` were skipped because those
    envs are not installed in the verify worktree.
  - Register tests: 9 of 11 `ok`.
  - The two red lanes and the two red register tests are:
    - `pyforge-steward-test`: the trigger-map meta-test read two literal paths in this story's
      new tests as files the suite opens. Fixed after the run; the full suite passes.
    - `sbom-laptop-gate`: Atlas has 72 mypy errors in `pyforge-foundry-full`. Main's own lock
      shows the same 72. Recorded as `DW-atlas-steward-100-7-1`, owner atlas. This is the one
      accepted AC4 gap.
- **Fixes the run found:** see the Spec Change Log entry of 2026-10-14 and the PR body. They
  touch refresh, realize, reconcile and verify, plus the register probes. They also fix three
  reds the refresh caused: the platform liquibase floor test, ruff 0.17.0's import order, and
  doctor's optional Counter type.

## Auto Run Result (2026-10-13, superseded by the unblock above)

Status: blocked  
Blocking condition: `pin_policy_restore` refuses after `estate refresh` — `pixi lock` cannot solve once policy losses are rewritten (cron-descriptor floor restore vs `django-celery-beat`; earlier openai 3.x vs litellm 1.105). Auto-checkpoint pixi state on the branch was reset to `origin/main` at commit `34a765839f`.

**Agent half (done on `dispatch/pyforge-steward/100.7`):**

- Fixed `scripts/pin_policy_check.py` / `pin_policy_restore.py` to insert `scripts/` on `sys.path` so `estate plan|refresh` can render and diff policy (`80bca4916b`).
- Hardened restore: lowered-floor uses base declaration; channel-table cap loss uses base table; corrected `cap: "<42"` / `"<1.31"` YAML in `docs/governance/pin-policy.yaml`.
- Added `never-move` holds for `openai` (`pyforge-guild`) and `cron-descriptor` (`python-agent-platform`) in pin-policy for solve conflicts found during refresh probes.
- Partial `estate reconcile` output and memlog/scoped stamps live on the branch from checkpoint `9714b363f4` (derived docs + `environment.yaml`); journal stub at `.steward/estate-refresh/2026-10-13.json` is not a complete AC1 run.
- `python scripts/spec_surface_reconcile.py` — OK after memlog entries on `spec-pyforge-steward`, `spec-pyforge-doctor`, `spec-pyforge-marshal`, `spec-pyforge-unifying-strategy`.

**Operator on the branch (required before AC1–AC5):**

1. From a clean tree at `origin/main` pixi (`34a765839f`), run `pixi run -e pyforge-steward pyforge steward estate refresh` (with updated pin-policy), then `realize --yes` for operator-gate rows, `estate reconcile`, `estate verify`.
2. Confirm `pin_policy_check.py --diff origin/main` exit 0 and land one PR with `maintenance`, lock-solved ×3, and marshal merge subject per Q14.
3. Scoped `--write-baseline --spec …` for any new governed paths after the real batch (never a bare global stamp).
