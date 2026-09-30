---
title: "77.1: Dispatch seeds each worktree's codegraph index from the shared base and syncs it"
type: 'fix'
created: '2026-09-29'
status: 'in-review'
baseline_revision: '20dde557f4ea8ab580327d341077c2cf0d30bcff'
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
warnings:
  - oversized
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

## Code Map

All marshal paths are under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/cli/dispatch.py` -- `_seed_dispatch_output_layer` (~L492) is the sibling to mirror: never raises, layer off returns `None`, an unavailable instrument becomes a named WARN. `context_payload` is resolved ~L1905 and `data["wire"]` is seeded off-shape ~L1917 so every envelope carries it. The provisioning call site is ~L2153 (after `_seed_dispatch_worktree_scope`, before `spec_path` relocation). The wire disposition is echoed and journaled ~L2387-2413: `data["wire"]` plus the `"wire"` key of the `dispatch-launch` OUTCOME payload. `structure_graph` goes beside each of these three sites. The file uses Python 3.14 bare `except A, B:`; match it.
- `src/pyforge/marshal/seed/verbs/kit.py` -- `build_codegraph_index(repo_root, *, stale, process)` (~L223) is the one builder: `stale=True` runs `codegraph sync -q`, `stale=False` runs `codegraph init -y`; ceilings `SYNC_TIMEOUT_S` 300 and `INDEX_TIMEOUT_S` 900. It returns `None` or a reason string (it swallows `ProcessError`, so a timeout arrives as `command timed out after ...`). Reuse; do not fork.
- `src/pyforge/marshal/seed/model/kit.py` -- `KitItemId.CODEGRAPH_INDEX`, `CODEGRAPH_INDEX_RELPATH` (`.codegraph/codegraph.db`), layer `structure-graph`, `probe_binary` `codegraph`.
- `src/pyforge/marshal/seed/detect/kit.py` -- `probe_instrument(item)` (binary on PATH via `shutil.which`, reason names the binary) and `layer_enabled(context_layers, layer)` (tri-state safe: an unresolved `"auto"` reads OFF). Use both; the output-layer sibling's `layer.get("enabled")` is truthy on `"auto"`.
- `src/pyforge/marshal/ports/fs.py` / `adapters/fs_local.py` -- `FsPort.copy_file` copies real bytes (`shutil.copy2`); there is no tree copy or listing. Enumerate `<primary>/.codegraph/` read-only with `Path` and copy per file. Adding a port method is out of scope (it would touch every FsPort fake and `tests/meta/test_ad11_write_boundary.py`).
- `src/pyforge/marshal/core/harness_profile.py` -- `WireWrap.journal_payload()` (~L299) is the payload shape to mirror: off is `applied=False, reason=None`, degraded carries a reason.
- `src/pyforge/marshal/core/findings.py` (~L1823, `MRS-DISP-051` block) and `src/pyforge/marshal/core/verdict.py` (~L1186) -- the two registries; new codes go in both as `Verdict.WARN`. `MRS-DISP-050` (Story 65.2) and `MRS-DISP-052` (Story 74.2) are claimed by backlog specs and absent from source; this story takes `MRS-DISP-053` and `MRS-DISP-054`.
- `src/pyforge/marshal/cli/context_bootstrap.py` -- builds the substrate base index (`_rebuild` calls `build_codegraph_index(root, stale=False, ...)`); read-only reference. The WARN message names its command.
- `tests/unit/test_dispatch_output_layer.py` -- the test shape to follow (fake `FsPort`, `monkeypatch` at the `dispatch_module` call site). `tests/unit/test_dispatch.py` holds the `dispatch_once` fakes; existing exact-payload assertions gain a `structure_graph` key.
- `pixi.toml` (~L899-902) -- `[feature.pyforge-guild.target.linux-64.dependencies]`, beside `caveman-installer`. The `codegraph` pin already exists in `feature.local-recipes`'s linux-64 table (~L2330). `_bmad-output/policy-defaults.toml` L69 -- `[context."structure-graph"] enabled = true`.
- Shell note: this run's `PIXI_PROJECT_MANIFEST` names the primary checkout's `pixi.toml`. Every pixi command that edits or locks must run with `--manifest-path <worktree>/pixi.toml` (or the variable unset) so nothing writes to the primary.

## Tasks & Acceptance

The contract's `## Tasks` and `## Acceptance Criteria` stand as written. The execution order, one file per task:

**Execution:**
- `pixi.toml` -- add `codegraph = ">=1.6.0"` to `[feature.pyforge-guild.target.linux-64.dependencies]` beside `caveman-installer`, no channel pin; then `pixi lock` and regenerate `environment.yaml`, both with the worktree manifest -- Task 2
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `.../core/verdict.py` -- register `MRS-DISP-053` (no base index or sync fell back to init) and `MRS-DISP-054` (session runs without an index) as WARN -- Task 3
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- add `StructureGraphSeed` and `_seed_dispatch_structure_graph`; call it at the provisioning site; seed `data["structure_graph"]` off-shape beside `data["wire"]`; add `structure_graph` to the OUTCOME payload -- Task 3
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_structure_graph.py` -- every I/O-matrix row against a fake `FsPort`/`ProcessPort`, the primary-unchanged snapshot, and a `dispatch_once`-level journal assertion -- Task 4
- `src/shared/packages/pyforge-marshal/tests/integration/test_dispatch_structure_graph_real.py` -- the real-binary seed-and-sync test, skipped with a reason when `codegraph` is absent -- Task 4
- Existing `dispatch_once` tests that pin an exact OUTCOME payload -- add the `structure_graph` key -- Task 4
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and each co-governor `spec-surface-check` names -- append a surface-reconcile entry per changed governed path -- Task 6

## Design Notes

- **Two contract steps are not this run's.** Task 6's scoped `--write-baseline --spec` stamp is not run: this dispatch forbids `--write-baseline` (a producer that stamps its own baseline launders drift), so the run reconciles by memlog only and the landing owns the stamp. Task 7 writes the primary checkout, which a dispatch never does, so it is a post-landing operator step.
- **One dataclass, one payload spelling.** `StructureGraphSeed(applied, mode, reason, seconds, findings)` is frozen and has `journal_payload()` (`applied`, `mode`, `reason`, `seconds`), the way `WireWrap` does. The function returns it; `dispatch_once` puts `journal_payload()` on `data` and on the OUTCOME entry. The off shape is `applied=False, mode="skipped", reason=None, seconds=0.0` and has no finding.
- **Order inside the function.** (1) layer off -> off shape. (2) `probe_instrument` unavailable -> `skipped`, reason from the probe, WARN `MRS-DISP-054`; nothing is copied. (3) worktree already holds `.codegraph/codegraph.db` -> `sync -q` only. (4) base present -> copy files, then `sync -q`. (5) no base -> `init -y` plus WARN `MRS-DISP-053` naming `pixi run -e pyforge-guild marshal context bootstrap`.
- **Failure ladder.** A non-timeout `sync` failure falls back to `init -y` once, with a WARN `MRS-DISP-053` carrying the sync reason; the mode that finally applied is what is journaled. A reason containing `timed out` on either verb ends in `skipped`, reason `timeout`, WARN `MRS-DISP-054`, with no init fallback (init's 900 s ceiling must not stack on a timed-out sync). A copy failure ends in `skipped` with the OS reason, WARN `MRS-DISP-054`. The function never raises.
  *(Amended 2026-09-29 by the implementation, measured against the real binary:)* `codegraph init -y` over an existing `.codegraph/` exits 0 having done nothing ("Already initialized", even over a corrupt db), so the `sync` -> `init` fallback first clears the index this run copied, and any build is followed by a check that `.codegraph/codegraph.db` exists before `applied` is journaled. A re-dispatched worktree's own index is never cleared: its failed `sync` ends in `skipped` (WARN `MRS-DISP-054`) with no `init`. Any `skipped` ending leaves no index this run created behind, so a session never opens on a half-copied or half-built db (step 01 prefers the file whenever it exists).
- **Copy, never link, never touch the primary.** Only regular files under the base `.codegraph/` are copied (symlinks are skipped); sqlite sidecar files (`-wal`, `-shm`) travel with the db because the whole directory is enumerated. The primary is only read; a test snapshots each file's mtime and size before and after.
- **`seconds`** is `time.monotonic()` around copy plus build, rounded to two decimals.
- **Root-bound row.** The 28.31 benchmark timed `sync` from a base but never checked which paths a synced worktree index answers with. The binary is not installed here until Task 2 lands. Decision rule, fixed now: after Task 2, seed a worktree from a base built in a sibling directory and run `codegraph context` there. If it answers with worktree paths, the matrix row is unreachable and Design Notes records the measurement, with no runtime probe. If it answers with the base's paths, the sync path is unsound: `dispatch` falls back to `init -y` after the copy, with the WARN, and the integration test pins that behavior.
  *Measured 2026-09-29 (`codegraph` 1.6.0, `pixi run -e pyforge-guild`):* an index built in one directory, copied into a sibling and synced answers with the sibling's files. The db stores no absolute path (no `nodes`/`files` column matches the directory), `codegraph context` reports paths relative to the project root, and a symbol added only in the worktree is found there and not in the base. The row is therefore unreachable and there is no runtime probe; `tests/integration/test_dispatch_structure_graph_real.py` pins the claim against the real binary so a release that changes it fails a test.
## Spec Change Log

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

Implemented 2026-09-29 by dispatch `pyforge-marshal/77.1`. Everything below was read from an exit code.

- `pixi.toml`: `codegraph = ">=1.6.0"` in `[feature.pyforge-guild.target.linux-64.dependencies]` (conda-forge, no channel pin); `pixi lock` (worktree manifest) added `codegraph 1.6.0` to `pyforge-guild`, `pyforge-foundry-full` and `pyforge-foundry-full-stack` and moved their nodejs to the 24.x build codegraph requires. `environment.yaml` regenerated with `pixi project export conda-environment -e build`: byte-identical (the `build` environment does not carry codegraph). `pixi run -e pyforge-guild codegraph --version` -> `1.6.0`.
- `cli/dispatch.py`: `StructureGraphSeed`, `_seed_dispatch_structure_graph` (called beside `_seed_dispatch_output_layer`), `data["structure_graph"]` seeded off-shape beside `data["wire"]`, `structure_graph` on the `dispatch-launch` OUTCOME payload. `core/findings.py` + `core/verdict.py`: `MRS-DISP-053`, `MRS-DISP-054` as WARN.
- Tests: `tests/unit/test_dispatch_structure_graph.py` (30, every matrix row, the primary-unchanged snapshot, `dispatch_once` journal and envelope), `tests/integration/test_dispatch_structure_graph_real.py` (4, real binary; skipped with a reason in `pyforge-marshal`, passing in `pyforge-guild`), `tests/unit/test_findings.py` (registry pin). Four mutations (no clearing before the fallback, init after a sync timeout, init instead of sync with a base, journal key dropped) each fail the suite.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -> exit 0 (8935 passed, 5 skipped). `pixi run --frozen -e pyforge-ci pyforge-deps-test` -> exit 0 (130 passed, 3 skipped). `pixi run -e pyforge-guild lint-types` -> exit 0. `pixi run -e pyforge-guild pyforge-station-tests` -> exit 0 (`pixi.toml` changed; every station suite green). `pixi run -e pyforge-guild spec-surface-check` -> exit 0 after the memlog reconcile on `spec-pyforge-marshal`.
- Not done, by design: the scoped `--write-baseline --spec pyforge-marshal/spec-pyforge-marshal` stamp (a dispatch never stamps its own baseline; the landing owns it) and Task 7 (`marshal context bootstrap` on the primary checkout, then record the next dispatch's `structure_graph` payload here).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
