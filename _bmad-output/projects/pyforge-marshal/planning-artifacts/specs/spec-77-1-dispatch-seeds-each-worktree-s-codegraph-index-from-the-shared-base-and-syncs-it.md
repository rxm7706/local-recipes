---
title: "77.1: Dispatch seeds each worktree's codegraph index from the shared base and syncs it"
type: 'fix'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context_bootstrap.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/benchmarks/structure-graph-dispatch-28-31.json
  - archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-34-dispatch-structure-graph-shared-index-provisioning.md
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
  - _bmad-output/policy-defaults.toml
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** marshal's token economy has three layers that should apply to every dispatch session. On 2026-09-29, two
of them worked:
- **`wire` works.** `headroom wrap claude` runs on a per-worktree port, and the dispatch journal reads
  `wire.applied: true`. One stopped session had saved 15.7% of its tokens in five minutes.
- **`output` works.** `_seed_dispatch_output_layer` deploys the caveman skill into every worktree.
- **`structure-graph` does not.** The layer is enabled for every station by `_bmad-output/policy-defaults.toml`
  (`[context."structure-graph"] enabled = true`, since Epic 55), and nothing on the dispatch path realizes it:
  - `codegraph` is not in the `pyforge-guild` environment that dispatch runs in. `pixi.toml` carries
    `codegraph >=1.6.0` only in `feature.local-recipes`'s linux-64 table.
  - The primary checkout has no `.codegraph/`.
  - `cli/dispatch.py` names codegraph only in a docstring.

  `bmad-build-auto`'s `step-01-clarify-and-route.md` already prefers `.codegraph/codegraph.db` when it exists in the
  worktree (Story 28.33), so a dispatch session never gets the navigation savings the layer exists for.

Story 28.31's spike measured the choice (`benchmarks/structure-graph-dispatch-28-31.json`, recommendation
`share-repo-level-index`): about 19 s and 222 MiB for `codegraph init -y` per worktree, about 4 s for `codegraph sync -q`
from a shared base, against about 52k tokens of unaided navigation. Its follow-on draft (archived `spec-28-34-…`,
`DW-FU-28-31-1`) was never minted. The operator ruled on 2026-09-29 that all three layers must be working before the
next fleet drain.

**Approach:**
1. **Environment.** Add `codegraph = ">=1.6.0"` to `[feature.pyforge-guild.target.linux-64.dependencies]`, beside
   `caveman-installer`, from conda-forge with no channel pin. Then run `pixi lock` and regenerate `environment.yaml`
   (`pixi project export conda-environment -e build > environment.yaml`).
2. **Dispatch.** Add a `_seed_dispatch_structure_graph(fs, process, worktree, repo_root, context_payload)` step to
   `dispatch_once`, beside `_seed_dispatch_output_layer`. When `[context."structure-graph"]` resolves enabled:
   - **Base present.** Copy `<primary>/.codegraph/` into `<worktree>/.codegraph/`. Copy, never symlink: `sync` writes
     the index, and the primary must stay unwritten. Then run `build_codegraph_index(worktree, stale=True, ...)`
     (`codegraph sync -q`, the kit's sync ceiling).
   - **No base index.** Run `build_codegraph_index(worktree, stale=False, ...)` (`codegraph init -y`, the kit's init
     ceiling), and emit a WARN that names `pixi run -e pyforge-guild marshal context bootstrap` as the fix.
   - **No `codegraph` on PATH, or any failure.** Emit a WARN naming the cause. The session runs without an index.
   - **Layer off.** Do nothing (byte-identical to today).
3. **Journal.** The `dispatch-launch` journal entry carries `structure_graph`: `applied`, `mode` (`sync` / `init` /
   `skipped`), `reason` and `seconds`, beside `wire`.
4. **Findings.** New WARN codes take the next free `MRS-DISP-*` numbers, registered in `core/findings.py` and
   `core/verdict.py` (WARN never changes the exit code).

Ledger key: `77-1-dispatch-seeds-each-worktree-s-codegraph-index-from-the-shared-base-and-syncs-it`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-282 (FR-229); AD-75 (dispatch is a governed verb); AD-20 (process injected: codegraph runs
  through `ProcessPort`); AD-21 (reconcile, then act: a present index is synced, never rebuilt).
- Story 28.31 (the spike and its recommendation), Story 28.33 (step 01 reads the worktree index), Epic 55 (the layer
  switched on fleet-wide), CAP-192 (`marshal context bootstrap` builds the substrate's base index).
- `spec-feature-flag-governance` Q1: a `fix` needs no flag. The layer's switch is `[context."structure-graph"].enabled`.
- Closes `DW-FU-28-31-1` when it lands.

## Acceptance Criteria

- Given the layer is enabled and a base `.codegraph/codegraph.db` exists in the repository root When `dispatch_once`
  provisions a worktree Then the fake `ProcessPort` records `codegraph sync -q` run in the worktree and never
  `codegraph init -y`, and the journal reads `structure_graph.mode: sync`, `applied: true`
- Given the layer is enabled and no base index exists When `dispatch_once` provisions a worktree Then `codegraph init -y`
  runs in the worktree, a WARN names `marshal context bootstrap`, and the journal reads `mode: init`
- Given `codegraph` is not on PATH When `dispatch_once` provisions a worktree Then a WARN names the missing binary, the
  journal reads `mode: skipped` with that reason, and the dispatch proceeds
- Given the layer resolves off When `dispatch_once` provisions a worktree Then nothing is copied or run, and the journal
  reads `applied: false`
- Given a provisioning run When it completes Then no file under the primary checkout's `.codegraph/` has changed
  (mtime and size)
- Given a real `codegraph` on PATH (integration test; skipped with a reason where the binary is absent) When a worktree
  is seeded from a base built in a sibling directory and synced Then `codegraph context "<a symbol in the worktree>"`
  returns a path inside the worktree
- Given the Guild environment When `pixi run -e pyforge-guild codegraph --version` runs Then it resolves, and
  `environment.yaml` has been regenerated
- Given the station suite When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and
  `pixi run --frozen -e pyforge-ci pyforge-deps-test` run Then both exit 0

## Tasks

1. Read `cli/dispatch.py` (`dispatch_once`, `_seed_dispatch_output_layer`, the `dispatch-launch` journal payload and its
   `wire` entry), `seed/verbs/kit.py` (`build_codegraph_index` and its pinned ceilings), and `cli/context_bootstrap.py`.
2. Edit `pixi.toml`, run `pixi lock`, and regenerate `environment.yaml`. Confirm `pixi run -e pyforge-guild codegraph
   --version`.
3. Implement `_seed_dispatch_structure_graph` and wire it into `dispatch_once` and the journal. Register the WARN codes.
4. Add unit tests for every outcome, using a fake `ProcessPort` and `FsPort`, and one integration test gated on the
   binary.
5. `pixi.toml` changed, so run `pixi run -e pyforge-guild pyforge-station-tests` as well as the station's
   `verify_commands`. Read each exit code.
6. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped `--write-baseline --spec` for
   each.
7. After landing, run `pixi run -e pyforge-guild marshal context bootstrap` on the primary checkout, then confirm
   `.codegraph/codegraph.db` exists. Record the next dispatch's `structure_graph` journal payload in this spec's Run
   results.

## Boundaries & Constraints

**Always:**
- Degrade, never block. Every failure is a named WARN, and the dispatch proceeds.
- Copy the base index; never link it. Sync writes the index.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not write any file in the primary checkout from `dispatch_once` (Story 64.1).
- Do not commit an index. `.codegraph/` stays gitignored, which it already is (`**/.codegraph/`).
- Do not change `bmad-build-auto`'s skill files or the harness profiles.
- Do not add a `pixi.toml` channel pin: the packages are on conda-forge.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| base present | primary `.codegraph/codegraph.db` | copy + `sync -q` in the worktree; `mode: sync` | a sync failure falls back to `init` once, with a WARN |
| no base | primary has no `.codegraph/` | `init -y` in the worktree; `mode: init` | WARN names `marshal context bootstrap` |
| no binary | `codegraph` not on PATH | `mode: skipped`; the session runs without an index | WARN names the binary |
| layer off | `[context."structure-graph"].enabled = false` | nothing copied or run; `applied: false` | — |
| root-bound index | the copied index answers only for the primary's paths after sync | fall back to `init -y` in the worktree | WARN; recorded so the shared base can be re-scoped |
| worktree already indexed | a re-dispatch reuses a worktree holding `.codegraph/` | `sync -q` only; no copy over it | — |
| timeout | sync or init past the kit's ceiling | `mode: skipped`, reason `timeout` | WARN; the dispatch proceeds |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-282 (FR-229).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-29 — Proposed: every dispatch session opens on the
shared codegraph index*.
Ledger key: `77-1-dispatch-seeds-each-worktree-s-codegraph-index-from-the-shared-base-and-syncs-it`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1); the layer's switch is `[context."structure-graph"]`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; `pixi.toml`
  changed).

**Manual checks:**
- `pixi run -e pyforge-guild codegraph --version` — resolves.
- `pixi run -e pyforge-guild pyforge-station-tests` — pass (`pixi.toml` changed).
- `git diff --exit-code environment.yaml` after regenerating it — matches the committed file.
- After landing: `pixi run -e pyforge-guild marshal context bootstrap` on the primary checkout, then a dispatch whose
  `dispatch-launch` journal reads `structure_graph.mode: sync`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Run results

Not started.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
