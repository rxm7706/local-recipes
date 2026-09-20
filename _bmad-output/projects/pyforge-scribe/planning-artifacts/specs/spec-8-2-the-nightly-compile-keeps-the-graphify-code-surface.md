---
title: 'The nightly compile keeps the graphify code surface'
type: 'feature'
created: '2026-09-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scribe graph compile` is a full rebuild. The graphify ingest that
writes `code:` nodes is an opt-in extra (`SCRIBE_GRAPHIFY_EXTRA`) plus the
explicit `scribe index build` verb. The 02:30 trigger runs the lean compile, so
every scheduled night drops whatever index build wrote. Separately, live
graphifyy exposes `extract` as a package submodule after `collect_files`
loads `graphify.extract` — `graphify.extract(...)` raises `TypeError`, so
the official index-build path cannot run against the package this estate
installs. The lean `pyforge-scribe` pixi env also omits `graphifyy`, so
`scribe index build` exits 2 there.

**Approach:** Unwrap graphifyy's shadowed public names in the Story 6.1
adapter (`module.<name>` when the attribute is not callable). Declare
`graphifyy` on the `pyforge-scribe` pixi feature (same pattern as
`cocoindex`). Have the Story 8.1 trigger set `SCRIBE_GRAPHIFY_EXTRA=1` when
the operator has not set it, so one nightly rebuild keeps `code:` nodes.
Interactive `scribe graph compile` stays off-by-default (AD-6).

## Boundaries & Constraints

**Always:**
- Code nodes write through `open_graph_store` — never a parallel store.
- The third-party `graphify` import stays lazy and inside
  `extras/graphify.py`.
- Unset `SCRIBE_GRAPHIFY_EXTRA` on an interactive compile still skips the
  extra.
- An explicit `SCRIBE_GRAPHIFY_EXTRA=0` on the trigger process is left
  alone.
- Compile degrades to a warning when ingest fails; it never fails the
  scheduled run red.
- `scribe index build` still exits 2 if graphifyy is absent.

**Never:**
- Never a GitHub Actions workflow (Epic 8 HARD boundary).
- Never a foundry-root `graphify-out/` product dir.
- Never a required post-compile `index build` hop — compile-with-extra-on
  is the one persist path.
- Never turn every interactive `scribe graph compile` into a graphify
  ingest.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live graphifyy after `collect_files` | `graphify.extract` is the submodule, not the function | `ingest_repo` calls `extract.extract` and writes `code:` nodes | No `TypeError` |
| Official `scribe index build` in `pyforge-scribe` env | `graphifyy` declared on the feature | Exits 0; upserts `code:` nodes through the persist port | Exit 2 only if the package is still absent |
| Nightly trigger, extra unset | `SCRIBE_GRAPHIFY_EXTRA` missing | Trigger exports `1`, then `scribe graph compile --nightly`; store keeps `code:` nodes | Ingest failure → compile warning, exit 0 from extra path |
| Nightly trigger, extra explicitly off | `SCRIBE_GRAPHIFY_EXTRA=0` | Left at `0`; compile skips graphify | Unchanged AD-6 |
| Interactive compile, extra unset | Operator runs `scribe graph compile` | Zero graphify `code:` nodes | Identical to Story 6.1 AC1 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py` —
  `_graphify_api()` unwraps submodule-shadowed callables; `_build_graph` and
  `build_graph_report` use it
- `scripts/scribe_nightly_trigger.py` — `setdefault("SCRIBE_GRAPHIFY_EXTRA", "1")`
  after the PostgreSQL preflight, before `_COMPILE_CMD`
- `pixi.toml` `[feature.pyforge-scribe.dependencies]` — `graphifyy >=0.9.51`
- `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` § *Installing the
  nightly trigger* — document the extra default
- `src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py` —
  submodule-shadow fixture
- `tests/scripts/test_scribe_nightly_trigger.py` — extra default / preserve-off

## Tasks & Acceptance

**Execution:**
- feature: unwrap `graphify.extract` (and sibling public names) when the
  attribute is a submodule
- feature: declare `graphifyy` on the `pyforge-scribe` pixi feature
- feature: nightly trigger enables `SCRIBE_GRAPHIFY_EXTRA` when unset
- test: adapter + trigger unit coverage for the two new behaviors
- docs: runbook notes the nightly extra default

**Acceptance Criteria:**
- Given live graphifyy exposes `extract` as a package submodule after
  `collect_files`, when `scribe index build` or a compile with the extra on
  calls `ingest_repo`, then ingest uses the callable and writes `code:`
  nodes through `open_graph_store`.
- And the nightly trigger sets `SCRIBE_GRAPHIFY_EXTRA=1` when the operator
  has not set the variable; an explicit `0` stays off.
- And the `pyforge-scribe` pixi feature declares `graphifyy` so that env can
  import `graphify` (lazy, adapter-only); a missing or failing extra still
  degrades on compile and never fails the scheduled run red.
- And an interactive `scribe graph compile` with the extra unset is
  unchanged — zero code nodes from graphify.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py tests/scripts/test_scribe_nightly_trigger.py src/shared/packages/pyforge-scribe/tests/unit/test_compile.py -k 'graphify or nightly or extra' -q` — expected: focused suite green
- `pixi run --frozen -e pyforge-scribe scribe index build` — expected: exits 0; `code:` nodes in `.claude/data/pyforge-scribe/graph.json`
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-nightly-compile` — expected: compile keeps `kind=code` nodes

## Spec Change Log

- **2026-09-13:** minted from `spec-scribe-graphify-nightly-currency` CAP-1/CAP-2
  and `epics.md` Story 8.2. Implementation landed in the same session as the
  story mint (adapter unwrap, pixi dep, trigger `setdefault`). Sprint tracking
  regenerated with `sprint_plan.py generate` (21 stories, 8 epics, `in_sync`);
  ledger synced via `sprint-ledger-sync --project scribe`. Live
  `scribe index build` in `pyforge-scribe` env wrote 37464 `code:` nodes.
  Follow-on `pyforge-scribe-nightly-compile` exited 0: compiled 37834
  nodes, 0 invalidated, 1003 stale — 37464 still `kind=code`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `0addcaba50` (2026-08-15, "doctor: land Story 8.2 -- sprint ledger, dashboard, epics outcome, spec promotion"); also `8fce539e45` (2026-08-15, "doctor: Story 8.2 -- mint_id_for_entry picks the next free suffix per station"); also `55c0e5eb21` (2026-08-13, "Story 8.2 review pass 2: fix fence-priority error dropping an unrelated open region, close"). Ledger row `8-2-the-nightly-compile-keeps-the-graphify-code-surface: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-8-2-minting-picks-the-next-free-suffix-per-station-convention.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `8-2-the-nightly-compile-keeps-the-graphify-code-surface: done`).
- `## Auto Run Result` reconstructed from git (none survived).
