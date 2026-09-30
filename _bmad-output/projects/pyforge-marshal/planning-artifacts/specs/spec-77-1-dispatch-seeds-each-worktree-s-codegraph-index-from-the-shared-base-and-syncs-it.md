---
title: "77.1: Dispatch seeds each worktree's codegraph index from the shared base and syncs it"
type: 'fix'
created: '2026-09-29'
status: 'done'
baseline_revision: '20dde557f4ea8ab580327d341077c2cf0d30bcff'
review_loop_iteration: 0
followup_review_recommended: true
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
deferred:
  - summary: >-
      The four real-binary codegraph integration tests for Story 77.1 run in no automated lane, so a codegraph release that changes the behavior the seed relies on turns nothing red.
    evidence: |-
      `pyforge-marshal-test` runs in the `pyforge-marshal` environment, which does not carry codegraph, so `tests/integration/test_dispatch_structure_graph_real.py` collects and skips there (verified 2026-09-29: 4 skipped, "codegraph is not on PATH"). The same file passes 4 of 4 in `pyforge-guild` (verified the same day), the only environment that gained codegraph, and no `.github/workflows/` file or pixi task names the file or runs marshal tests in that environment. The unit suite pins the seed only against fakes that hard-code three measured facts: a copied index synced in a sibling directory answers for that directory, `codegraph sync` exits non-zero on a damaged copy, and `codegraph init -y` over an existing `.codegraph/` exits 0 having done nothing. The pin is `codegraph >=1.6.0` with no upper bound. Closing it needs a Guild-environment lane (a pixi task wired into `pr-preflight` and CI), which is a new capability that takes a Dream append, a CAP and a Story; the acceptance criterion itself allows the skip where the binary is absent.
    location: >-
      src/shared/packages/pyforge-marshal/tests/integration/test_dispatch_structure_graph_real.py
    severity: medium
  - summary: >-
      Copying the primary checkout's base index file by file while another process writes it can produce a db, -wal and -shm set that do not belong together.
    evidence: |-
      Would settle it: run `_seed_dispatch_structure_graph` against a real base while a loop runs `codegraph sync -q` on that base (or `marshal context bootstrap` rebuilds it), then check whether the worktree's sync exits 0 on an inconsistent copy and whether `codegraph context` then answers wrongly. Today the failure ladder catches only a loud failure (a malformed db makes sync exit non-zero and the seed rebuilds with `init -y`); a torn set that syncs cleanly into a wrong index is not covered. Writers to the primary's `.codegraph/` are the operator-run `marshal context bootstrap` and any codegraph git hook, so the window is rare.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
    severity: medium (unverified)
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

### 2026-09-29 — Review pass
- verdicts: 45 findings — high 0, medium 6, low 27, false 10, maybe-false 2. Counting: the Blind Hunter's 12 bullets carry 22 separate claims, the Edge Case Hunter reported 7 items (one holds two claims, so 8 rows), the Verification Gap Reviewer 2 gaps plus 3 other findings, and the Intent Alignment Auditor 10 divergences; every claim has its own row, and rows in a grouped entry share a route.
- routing: no `intent_gap`, no `bad_spec`. Seven patch entries were applied through the implementation subagent, then re-verified on my side. Two entries were deferred (see the frontmatter `deferred` list). The rest were rejected on the reasons below.
- findings:
  - **Blind Hunter**
  - `[medium]` `[patch]` BH1: a failed or timed-out sync on a re-dispatched worktree that already holds an index says "runs without a codegraph index" while the index stays on disk and step 01 opens on it — verified at `_fail` and the already-indexed branch of `_seed_dispatch_structure_graph`, which both returned `_unseeded(...)` with the no-index tail. Fix applied: `_unseeded(..., index_kept=)`; `_fail` sets it when the worktree held an index that is still on disk, and the already-indexed sync-failure branch now goes through `_fail`; the tail reads "the worktree's existing codegraph index was left in place, unsynced (possibly stale)". The payload is unchanged (`applied: false`, `mode: skipped`, per the matrix). The two existing tests assert the new tail and the absence of the old one, and the no-index timeout test pins the old tail.
  - `[low]` `[reject]` BH2: the `"timed out" in error` test reads free text — a non-timeout failure whose last output line contains that phrase would skip the init fallback and journal `timeout`. Not worth fixing: it needs codegraph's final output line to say it, the effect is a degrade to `skipped` and never a block, and a sound fix needs a typed result from the shared `build_codegraph_index` (public kit surface that `marshal context bootstrap` also calls).
  - `[low]` `[reject]` BH3: `_discard_worktree_index` swallows unlink errors before the fallback `init`. Not worth fixing: it unlinks files this run just created in a directory it owns, an unlink failure there is not a state anyone showed reachable, and the fix adds a branch guarding it.
  - `[maybe-false]` `[defer]` BH4a: a file-by-file copy of a base that is being written could yield a db, -wal and -shm set that do not match. What would settle it: copy while `codegraph sync` runs on the base and see whether the worktree's sync exits 0 on the torn set. If true it is medium; deferred as unverified (grouped with EC1a).
  - `[low]` `[reject]` BH4b: `os.walk` without `onerror` omits an unreadable subdirectory silently. Not worth fixing: `.codegraph/` is written by the same user, the base db's existence is checked before the walk, and the guard would cover an unshown state.
  - `[low]` `[reject]` BH4c: skipped symlinks are not recorded. Cosmetic: skipping them is the specified behavior ("copy, never link") and no operator acts on the list.
  - `[medium]` `[defer]` BH5: the claim that a root-bound copy is unreachable is pinned only by the real-binary test, which skips in `-e pyforge-marshal` — verified: 4 skipped ("codegraph is not on PATH") in that env, 4 passed in `-e pyforge-guild`. Grouped with VG1 and IA3: closing it needs a Guild-environment lane, which is new work that takes its own Story.
  - `[low]` `[reject]` BH6: the integration module probes `codegraph --version` at import with only a return-code check. Not worth fixing: it needs the version call to hang past 60 s or raise, `shutil.which` already proved the file executable, and the fix adds a try/except for an unshown state.
  - `[low]` `[patch]` BH7: the primary-untouched snapshot is taken after a query that opens the primary's db. Fix applied: the `== base_before` assertion now runs before that query and the `== []` assertion stays after it. The reviewer's flake was not observed (34 passed twice); the reorder makes the check pure.
  - `[medium]` `[patch]` BH8: the refusal test asserts nothing — verified: it uses story `77-1-no-such-spec`, which refuses at the spec lookup before the key is seeded, so its `if "structure_graph" in payload["data"]` is false. Grouped with VG2, EC6 and VG4. Fix applied: see VG2.
  - `[low]` `[patch]` BH9: `pixi.lock` moved nodejs 26.10.0 to 24.21.0 in three environments and the pin's comment does not say why — verified: the lock entry for codegraph 1.6.0 depends on `nodejs >=24.21.0,<25.0a0`. Grouped with IA7. Fix applied: one sentence added to the comment on the pin; no dependency change, `pixi.lock` and `environment.yaml` unchanged by it.
  - `[low]` `[reject]` BH10a: MRS-DISP-053 covers two situations. Not worth fixing: the story asks for new WARN codes only ("next free numbers"), and a third code adds a registry entry, a verdict row and a test pin for a distinction the message text already carries.
  - `[low]` `[patch]` BH10b: the no-base message hard-codes "about 19 s and 222 MiB ... about 4 s", copied from `structure-graph-dispatch-28-31.json`. Fix applied: the parenthetical is removed and the `marshal context bootstrap` command stays; no test pinned the figures.
  - `[low]` `[reject]` BH11a: `mode` is a bare `str` with three module constants. Not worth fixing: exact-payload tests fail on a typo, and a `StrEnum` adds a new public type.
  - `[false]` `[reject]` BH11b: the layer-off default `mode: "skipped"` is not distinguishable from a real skip. Refuted: the intent's `mode` vocabulary is `sync|init|skipped` and the layer-off criterion asks only for `applied: false`; `reason: null` with `seconds: 0.0` is the documented off shape, as `WireWrap`'s is.
  - `[false]` `[reject]` BH11c: nothing consumes `structure_graph`. Refuted: the story asks for a recorded fact on the journal entry, not a consumer; no criterion or constraint names one.
  - `[false]` `[reject]` BH11d: `marshal factory spin` worktrees get no seeding. Refuted: the Approach names `dispatch_once` only, the drain hands stories to `dispatch_once`, and a spin run's index comes from the loop-home kit (`seed/verbs/kit.py::_apply_codegraph_index`, Story 28.3).
  - `[low]` `[reject]` BH12a: `_seed_dispatch_structure_graph` is long and `stale` doubles as verb and final mode. No named harm: the verb last run is exactly what the mode and the "exited 0 but ... does not exist" message report, and 30 unit plus 4 real-binary tests pin the ladder; a restructure is churn.
  - `[low]` `[reject]` BH12b: worst case is 300 s of sync plus 900 s of init. Not worth fixing: the ceilings are the kit's constants the intent names, a sync timeout never falls back to init (tested), and a stacked worst case needs a sync that runs to just under its ceiling and then fails.
  - `[low]` `[patch]` BH12c: `_timeout(verb, ceiling)` never uses `verb`. Fix applied: the parameter is dropped and the three call sites updated.
  - `[low]` `[reject]` BH12d: the launch-failure test repeats setup already in `_dispatch_with_layer`. Test tidiness with no behavior at stake; a refactor is more than a correction.
  - `[low]` `[reject]` BH12e: `seconds >= 0.0` cannot fail and rounding is unpinned. Cosmetic: the payload shape is pinned, and a rounding test is new coverage for a display value.
  - **Edge Case Hunter**
  - `[maybe-false]` `[defer]` EC1a: a torn db/-wal/-shm snapshot can sync cleanly into a wrong index. Same claim, evidence and settling check as BH4a; deferred with it.
  - `[low]` `[reject]` EC1b: a vanished sidecar or copy failure should fall through to `init -y`, not skip. Not worth fixing: the intent says any failure is a named WARN and the session runs without an index, the matrix has no init-on-copy-failure row, and it is a degrade only.
  - `[low]` `[reject]` EC2: timeout detection by substring. Same as BH2.
  - `[low]` `[reject]` EC3: cleanup failure before the fallback `init`. Same as BH3.
  - `[low]` `[reject]` EC4: `os.walk` without `onerror`. Same as BH4b.
  - `[low]` `[reject]` EC5: import-time `--version` probe. Same as BH6.
  - `[low]` `[patch]` EC6: the comment says the key is on "every refusal before a worktree exists" — verified: the argument, repo-root, scope and spec-lookup refusals return before the seed. Grouped with VG2. Fix applied: the comment now says every envelope emitted from the policy composition onward.
  - `[low]` `[patch]` EC7: the `StructureGraphSeed` docstring says the off shape is "byte for byte" today's behavior, but the envelope and the OUTCOME entry gain a key. The key is required by the layer-off criterion; the docstring was the only defect. Fix applied: reworded to say nothing was copied or run and no finding is raised, and that the payload still reports `applied: false`.
  - **Verification Gap Reviewer**
  - `[medium]` `[defer]` VG1: the four real-binary tests run in no automated lane (pre-verified; I re-checked: 4 skipped in `-e pyforge-marshal`, no workflow or pixi task names the file). Not patched in this story: a Guild-environment pixi task wired into `pr-preflight` and CI is a new capability that takes a Dream append, a CAP and a Story, and the acceptance criterion itself allows the skip where the binary is absent. Recorded as a deferred item with severity medium.
  - `[medium]` `[patch]` VG2: `test_a_refusal_before_any_worktree_still_states_the_disposition_as_off` cannot fail (pre-verified; I re-read the test). Fix applied: renamed `test_a_refusal_after_the_policy_composes_still_states_the_disposition_as_off`; it writes the spec on disk, enables the layer with a base present, reaches the harness refusal MRS-DISP-003, asserts no worktree was added and no `codegraph` ran, and asserts `data["structure_graph"] == StructureGraphSeed().journal_payload()` unconditionally. I confirmed it can fail: with the two seed lines removed from `dispatch_once` it fails (1 failed) and the file was restored byte-identical.
  - `[low]` `[reject]` VG3: timeout detection by substring. Same as BH2.
  - `[low]` `[patch]` VG4: the comment overclaims "every refusal before a worktree exists". Same defect and fix as EC6.
  - `[false]` `[reject]` VG5: `test_dispatch_landing.py::test_reconcile_spec_surface_drift_degrades_when_doctor_unreachable` failed in a `pyforge-guild` run. Refuted for this change: the sanctioned `pyforge-marshal-test` passes it (exit 0, 8935 passed, twice) and the diff touches nothing it reads; the reviewer ran it in an environment the station suite does not use.
  - **Intent Alignment Auditor**
  - `[false]` `[reject]` IA1: the real primary has no base index, so the first dispatches take the `init` route with a WARN. Refuted as a defect: that is the specified "no base" row, and building the base is Task 7's post-landing operator step, since a dispatch never writes the primary (Story 64.1).
  - `[false]` `[reject]` IA2: the root-bound row has no runtime probe. Refuted: the Design Notes fixed the decision rule before the measurement, the measurement showed the row unreachable, and the real-binary test pins it (4 of 4 pass in the Guild environment).
  - `[medium]` `[defer]` IA3: the real-binary criterion is skipped under the mandated station command. Same defect as VG1 and BH5; deferred with them.
  - `[false]` `[reject]` IA4: "returns a path inside the worktree" is read as a relative path. Refuted: `codegraph context` reports project-root-relative paths; the test joins the path to the worktree, asserts the file exists there, and asserts the worktree-only symbol is absent from the primary's file.
  - `[false]` `[reject]` IA5: `spin` is unchanged. Same as BH11d.
  - `[low]` `[reject]` IA6: timeout detection is a string match. Same as BH2.
  - `[low]` `[patch]` IA7: lock churn beyond codegraph (nodejs 24, re-hashed builds). Same as BH9; the comment now names it.
  - `[false]` `[reject]` IA8: the review diff omitted the spec and the memlog. Refuted: both were left out on purpose — the spec is the claims file and the memlog is the reconcile record — and I read both.
  - `[low]` `[reject]` IA9: the tests declare the layer through the project layer and never read the shipped `[context."structure-graph"] enabled = true`. Not worth fixing: the shipped default is Epic 55's surface and this change does not touch it; a test that reads the shipped file is new coverage of an unchanged surface.
  - `[false]` `[reject]` IA10: `MRS-DISP-052` was left unused. Refuted: `050` and `052` are claimed by the unlanded Stories 65.2 and 74.2 (Code Map), so `053` and `054` are the next free numbers.

## Auto Run Result

Status: done

### Summary of implemented change

`dispatch_once` now gives each new dispatch worktree a codegraph index when `[context."structure-graph"]` resolves enabled. With a base `.codegraph/` on the primary checkout it copies the base file by file (never linked, the primary is only read) and runs `codegraph sync -q` in the worktree; with no base it runs `codegraph init -y` there and raises WARN `MRS-DISP-053` naming `pixi run -e pyforge-guild marshal context bootstrap`; with no `codegraph` binary, a failed step, a failed copy or a timeout it raises WARN `MRS-DISP-054` and the session runs without a new index. A layer that is off copies and runs nothing. The `dispatch-launch` OUTCOME entry and the envelope carry `structure_graph` (`applied`, `mode` `sync|init|skipped`, `reason`, `seconds`) beside `wire`, and `codegraph >=1.6.0` joins the `pyforge-guild` environment.

Two behaviors go beyond the story text, both recorded in Design Notes: `codegraph init -y` over an existing `.codegraph/` exits 0 having done nothing (measured), so the fallback after a failed sync clears the index this run copied first and every build is checked for `.codegraph/codegraph.db`; and the root-bound row was measured unreachable (a synced copy answers with the worktree's own files), so it has no runtime probe and a real-binary test pins the claim.

### Files changed

- `pixi.toml` -- `codegraph = ">=1.6.0"` in `[feature.pyforge-guild.target.linux-64.dependencies]`, conda-forge, no channel pin, with a comment naming the nodejs 24 consequence.
- `pixi.lock` -- regenerated: codegraph 1.6.0 added to `pyforge-guild`, `pyforge-foundry-full` and `pyforge-foundry-full-stack`, with nodejs 24.21.0 there.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `StructureGraphSeed`, `_seed_dispatch_structure_graph`, the wiring beside `_seed_dispatch_output_layer`, the off-shape seed and the OUTCOME payload key.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `.../core/verdict.py` -- `MRS-DISP-053` and `MRS-DISP-054`, WARN.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_structure_graph.py` -- 30 unit tests, every matrix row, the primary-unchanged snapshot, the `dispatch_once` journal and envelope.
- `src/shared/packages/pyforge-marshal/tests/integration/test_dispatch_structure_graph_real.py` -- 4 real-binary tests, skipped with a reason where `codegraph` is absent.
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` -- registry pin for the two codes.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` -- surface-reconcile entry naming every governed path changed.
- This story spec -- Code Map, Design Notes, Run results, triage log, deferred items.

### Review findings

45 findings from four layers: high 0, medium 6, low 27, false 10, maybe-false 2. No `intent_gap`, no `bad_spec`, so no loopback (`review_loop_iteration` stays 0).

- **Patched (7 entries, 11 rows):** medium 2 — the kept-index message for a re-dispatched worktree whose sync fails (BH1), and the vacuous refusal test plus the overclaiming comment (BH8, VG2, EC6, VG4); low 5 — snapshot order in the integration test (BH7), the nodejs note on the pixi pin (BH9, IA7), the stale figures in the no-base message (BH10b), an unused test-helper parameter (BH12c), the "byte for byte" docstring (EC7).
- **Deferred (2 entries, 5 rows), in the frontmatter `deferred` list:** the real-binary tests run in no automated lane (BH5, VG1, IA3; medium; needs its own Story for a Guild-environment lane); a torn copy of a base that is being written (BH4a, EC1a; medium, unverified).
- **Rejected (29 rows):** 10 refuted as false (BH11b, BH11c, BH11d, VG5, IA1, IA2, IA4, IA5, IA8, IA10) and 19 low rows not worth fixing (BH2, BH3, BH4b, BH4c, BH6, BH10a, BH11a, BH12a, BH12b, BH12d, BH12e, EC1b, EC2, EC3, EC4, EC5, VG3, IA6, IA9) — each with its reason in the Review Triage Log above.

### Follow-up review recommendation

`followup_review_recommended: true` (two `medium` entries were patched on a first pass). Specific unverified risk: the re-dispatch failure paths that the patch reshaped — an already-indexed worktree whose sync fails or times out now goes through `_fail` and reports the kept-index message — are pinned only against fakes, because the four real-binary tests run in no automated lane (deferred item 1), and a torn base copy is unmeasured (deferred item 2). Patched counts by verdict: medium 2, low 5.

### Verification performed

Every verdict below was read from an exit code, on the patched tree, by me and not taken from the subagent's report.

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -> exit 0 (8935 passed, 5 skipped, 12 deselected).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -> exit 0 (130 passed, 3 skipped).
- `pixi run -e pyforge-guild pyforge-station-tests` -> exit 0 (every station suite).
- `pixi run -e pyforge-guild pytest` on the new unit and integration files -> exit 0, 34 passed, 0 skipped (the four real-binary tests ran against `codegraph` 1.6.0). In `-e pyforge-marshal` the integration file skips 4 with the reason "codegraph is not on PATH".
- `pixi run -e pyforge-guild codegraph --version` -> exit 0, `1.6.0`.
- `pixi run -e pyforge-guild lint-types` -> exit 0.
- `python scripts/spec_surface_reconcile.py` -> exit 0; `pixi run -e pyforge-guild spec-surface-check` -> exit 0.
- `environment.yaml` regenerated with `pixi project export conda-environment -e build`: identical to the committed file; `git diff` on it against the baseline is empty.
- Matrix Test Audit: every I/O-matrix row has a covering test that ran and passed (30 unit tests plus 4 real-binary tests, 0 skipped in the Guild environment).
- Mutation checks: the implementer's four (no clearing before the fallback, init after a sync timeout, init instead of sync with a base, journal key dropped) each failed the suite; mine — removing the off-shape seed from `dispatch_once` — failed the rewritten refusal test alone, and the file was restored byte-identical.
- The primary checkout, checked at review time: no `.codegraph/` there and `git status` on `main` reads clean.

### Residual risks

- Task 6's scoped stamp (`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`) was not run: this dispatch forbids `--write-baseline`. The memlog reconcile is in place and `spec-surface-check` reads no drift, so the landing owns the stamp.
- Task 7 is a post-landing operator step: `pixi run -e pyforge-guild marshal context bootstrap` on the primary checkout, then record the next dispatch's `structure_graph` payload under Run results. Until then every dispatch builds its own index with `init -y` and raises `MRS-DISP-053`.
- The two deferred items are not yet rows in `deferred-work-ledger.md`; the landing should promote them (`DW-77.1-<n>`).
- `codegraph` refuses Node 25 and 26, and the Guild environment is now capped at nodejs 24; a `codegraph` on a wrong Node degrades to `MRS-DISP-054`, never blocks.
- Codegraph telemetry is on by default (`CODEGRAPH_TELEMETRY=0` turns it off). `ProcessPort.run` takes no environment, so the seed leaves it; that is the operator's call.
- `init` and `sync` run synchronously before the session launches, up to the kit's 900 s and 300 s ceilings; a first dispatch with no base pays about 19 s.
