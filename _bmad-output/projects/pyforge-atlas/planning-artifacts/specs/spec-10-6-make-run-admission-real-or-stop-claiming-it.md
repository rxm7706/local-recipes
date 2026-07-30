---
title: 'Make run admission real, or stop claiming it'
type: 'feature'
created: '2026-07-29'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false  # discharged 2026-07-30 by review pass 5 (independent, adversarial-mutation lens): 8 mutants over pass 4's surfaces, 7 caught, 1 survived (release()'s malformed-ticket padding — a third vacuity) and is now fixed by a new test; mutation score 8/8, kedro-test 902 passed. 0 behavioural defects, so the find-rate pass 4 wanted to see fall has fallen. DW-AD23-3 independently corroborated and left open.
context: []
warnings: ['oversized']
baseline_revision: '56739413c2d9da27e87ec6e03a94eb571852ff76'
final_revision: '6c5569bf5f766a4a1ff738f959379582773e3cef'
---

<intent-contract>

## Intent

**Problem:** `ARCHITECTURE-SPINE.md` AD-23 and `orchestration/definitions.py:22` asserted
"a dataset has one writing run at a time — run admission serializes on the target dataset
set". Nothing implements it (`AUD-ATLAS-046`). The `in_process` Dagster executor in
`conf/base/dagster.yml` serializes ops *within* one run and gives no cross-run or
cross-process admission at all; there is no lock or queue anywhere in the package. Two
MCP `run_*` triggers, or an MCP trigger racing a `kedro run`, can interleave writes to the
same Parquet file today. I1 retracted the claim and DEMOTED AD-23; this story builds the
property so the claim can be restored truthfully.

**Approach:** A new `pyforge.atlas.admission` module and a `RunAdmissionHooks` hook
registered in `settings.HOOKS`, so every entry point that goes through `KedroSession.run`
(CLI, the 7 MCP `run_*` tools, and Dagster once DW-C1-1 lands) inherits admission from the
one place validation and lineage already ride. `before_pipeline_run` takes one OS file
lock (`filelock`) per dataset in `pipeline.all_outputs()`, in sorted order; both
`after_pipeline_run` and `on_pipeline_error` release. Default is reject-fast with a typed
error; a bounded wait is opt-in. On green, AD-23 is re-promoted to its full form and every
surviving "not implemented" retraction is corrected.

## Boundaries & Constraints

**Always:**
- **D1 — mechanism is `filelock`.** Present in the `pyforge-atlas` env today (3.32.0,
  conda-forge) but only TRANSITIVELY, via `dagster` and `ibis-framework-core`. Per the
  package's own AUD-ATLAS-010 doctrine ("an undeclared module-level import is a runtime
  dependency whether or not the manifest says so"), it MUST be declared in BOTH
  `pyproject.toml` `[project].dependencies` and the member `pixi.toml`
  `[package.run-dependencies]`, floor `>=3.32.0`. No new package enters the env; only the
  manifests learn the truth.
- **D2 — placement is a Kedro hook in `settings.HOOKS`.** Acquire in
  `before_pipeline_run`; release in BOTH `after_pipeline_run` AND `on_pipeline_error`.
- **D3 — reject, do not queue, by default.** A typed error naming the conflicting
  dataset(s), the holding run id, the holder PID, and the hold start time. A blocking wait
  is opt-in only, with a finite timeout enforced as a single deadline across all locks.
- **D4 — granularity is the pipeline's declared OUTPUT dataset set**, one lock per
  dataset, acquired in sorted name order. Disjoint output sets run concurrently.
- **D5 — stale locks are reclaimable.** A holder record whose PID is no longer alive never
  wedges the factory; the reclaim is recorded, not silent.
- **D6 — build it.** On a green gate, re-promote AD-23 to its full form and correct every
  surviving artifact that still says admission is not implemented.
- Admission logic lives in `admission.py` only. `mcp/tools.py` is NOT edited by this story.
- Existing conventions are matched: kedro objects annotated `Any` (no kedro type imports in
  hook signatures), `from __future__ import annotations`, module-level
  `logger = logging.getLogger(__name__)`, plain `def test_*` functions (the suite has zero
  `class Test*`), docstrings citing the story/AD/AC ids.
- The hook must survive `copy.deepcopy` (kedro-dagster's `KedroProjectTranslator`
  deep-copies `settings.HOOKS` at `to_dagster()` time) and pickling (multiprocess runners),
  with per-run state reset — the same contract `AtlasObservabilityHooks` already honors.

**Block If:**
- `filelock` cannot be declared without a dependency conflict in the member manifests, or
  declaring it forces a solve that removes/downgrades another declared dependency.
- The two-process gate cannot be made to reject a same-set contender for a reason that is
  not a test-harness defect (i.e. the mechanism itself does not hold across processes).

**Never:**
- Never a single global lock — that would serialize genuinely unrelated pipelines
  (`seed_gaps` vs `vulnerability`) and overclaim beyond AD-23's per-dataset-set rule.
- Never a DB lock (DuckDB here is in-memory — there is no persistent store to lock) and
  never the Dagster `QueuedRunCoordinator` as the v1 answer (it governs only daemon-routed
  runs; MCP calls `KedroSession.run` directly and would stay unguarded).
- Never put admission *logic* in `mcp/`, in `orchestration/definitions.py` (its lines 22-30
  docstring correction is the ONLY permitted edit there), or in a node body.
- Never satisfy the gate with a thread, a mock, or a monkeypatched lock: the defect is
  cross-process, so the proof must be cross-process.
- Never record the absence as a non-goal — the D6 escape hatch is closed.
- Do NOT change `mcp/tools.py` or `tests/mcp/test_no_business_logic_in_tool_bodies.py`
  (no new `ALLOWED_CALL_ROOTS` entry is needed — the hook seam bypasses that gate entirely).
- Do not weaken or edit `_bmad-output/.../sprint-status.yaml`; the orchestrator owns it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Uncontended run | No lock files held; pipeline outputs `{a, b}` | Locks taken in order `a`, `b`; holder record written per lock; run proceeds; both released after | No error expected |
| Same-set contender (the gate) | Process A holds `{a, b}`; process B requests `{a, b}` | B is rejected immediately | `RunAdmissionRejected` naming `a` (first conflict in sorted order), A's run id, PID, hold start |
| Disjoint contender (the gate) | Process A holds `{a, b}`; process B requests `{c}` | B is admitted and runs concurrently | No error expected |
| Partial overlap | A holds `{b}`; B requests `{a, b}` | B acquires `a`, hits `b`, releases `a`, rejects | `RunAdmissionRejected` for `b`; `a` is provably free afterwards |
| Holder killed (`SIGKILL`) | A acquired `{a}` then was `SIGKILL`ed; holder record survives with a dead PID | B acquires `a`, proceeds, and records the reclaim (`logger.warning` + `ticket.reclaimed`) | No error expected |
| Opt-in wait, holder releases in time | `runtime_params={"admission_wait_seconds": 5}`; holder releases at 0.2s | B blocks, then is admitted | No error expected |
| Opt-in wait, deadline expires | `admission_wait_seconds=0.3`; holder never releases | B is rejected when the deadline passes | `RunAdmissionRejected`, same fields |
| Invalid wait value | `admission_wait_seconds="soon"` / `-1` / `inf` | Run refuses to start | `AdmissionConfigError` naming the bad value; never silently falls back to reject-fast or to an unbounded wait |
| Pipeline with no outputs | `pipeline.all_outputs()` is empty | Admitted, no lock files created, release is a no-op | No error expected |
| Corrupt / missing holder record | Lock is held but the sidecar JSON is absent or unparseable | Still rejected; the unknown fields report as `None` | `RunAdmissionRejected` with `holder_run_id=None` etc. — never a `JSONDecodeError` |
| Release without acquire | `after_pipeline_run` for a run id with no ticket | No-op | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py` (**NEW**) — the whole
  mechanism. Public surface: `AdmissionConfigError`, `RunAdmissionRejected` (fields
  `datasets: tuple[str, ...]`, `conflicting: str`, `holder_run_id: str | None`,
  `holder_pid: int | None`, `held_since: float | None`), `AdmissionTicket` (dataclass:
  `run_id`, `datasets: tuple[str, ...]`, `reclaimed: tuple[str, ...]`, plus the held
  `filelock.FileLock` handles), `default_lock_root()`, `acquire(datasets, *, run_id,
  lock_root=None, wait_seconds=0.0) -> AdmissionTicket`, `release(ticket)`, and
  `RunAdmissionHooks`. Module docstring states the story/AD ids AND the single-machine
  boundary (§ Design Notes). Imports: stdlib + `filelock` + `from kedro.framework.hooks
  import hook_impl` only — no `pandas`, no `dashboard.*`, no `dagster` (the file is scanned
  by `tests/catalog/test_no_inline_io.py`; `filelock` is on neither denylist, `subprocess`
  is on the IO denylist so the lock must never shell out).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py` — line 33
  `HOOKS = (ProjectHooks(), AtlasObservabilityHooks(), DataValidationHooks())` gains
  `RunAdmissionHooks()` as the fourth member, with the import added beside the other three
  and the same "declared ONCE so every entry point inherits it" comment style.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py` —
  lines 22-30: replace the retraction ("It is **NOT** cross-run admission … Do not rely on
  single-writer safety here.") with the true statement: the `in_process` executor still
  only serializes ops within a run, AND cross-run admission is now enforced upstream of it
  by `admission.RunAdmissionHooks` in `settings.HOOKS`, so it covers Dagster, CLI and MCP
  alike. Nothing else in this 739-line module changes.
- `src/shared/packages/pyforge-atlas/pyproject.toml` — add `"filelock>=3.32.0",` to
  `[project].dependencies` inside the AUD-ATLAS-010 block, with the inline rationale
  comment the neighbours carry.
- `src/shared/packages/pyforge-atlas/pixi.toml` — add `filelock = ">=3.32.0"` to
  `[package.run-dependencies]`, same block, byte-for-byte in step with pyproject.
- `src/shared/packages/pyforge-atlas/tests/test_admission.py` (**NEW**) — root-level test
  module, mirroring `tests/test_hooks.py` sitting beside `hooks.py`. Holds the single-process
  unit tests AND the two-process gate. Second process is spawned with
  `subprocess.Popen([sys.executable, "-c", _CHILD_PROGRAM, ...])`; `subprocess` is banned
  only inside `src/pyforge/atlas/**`, and `tests/catalog/test_credential_scoping.py:105`
  is the in-suite precedent for using it in tests.
  **[review pass 1, bad_spec fix — the gap that let the CWD bug ship green]** Every test in
  the first implementation injected `lock_root=tmp_path`, so nothing ever exercised
  `default_lock_root()` against reality, and the one test named for it asserted a hardcoded
  `Path("data")/".locks"` instead of comparing it to a catalog-resolved path. Required:
  (a) a test that runs from a CWD *other than* the project root (`monkeypatch.chdir`) and
  asserts `default_lock_root()` is under the same root a real catalog entry's `filepath`
  resolves to — bootstrap a session the way `tests/orchestration/conftest.py` does and read
  `catalog["core_feedstock_health"]._describe()["filepath"]`; (b) a test asserting an
  ABSOLUTE `PYFORGE_ATLAS_DATA_ROOT` is honored verbatim; (c) a test that drives the shipped
  wiring — the real `settings.HOOKS` through kedro's real `_create_hook_manager()`, with NO
  injected `lock_root` — and proves the lock landed under the project-anchored default.
  **[review pass 1, patch]** The harness must not be able to HANG an unattended run:
  `_verdict` must read the child's line under a timeout (and fail loudly on expiry), and the
  child's `stderr` must not be left undrained while the parent blocks on `stdout` (a child
  that writes >64 KiB of kedro/rich logging would deadlock both). Prefer merging the child's
  stderr into stdout or draining it on a thread; a hung gate is worse than a red one.
- `src/shared/packages/pyforge-atlas/conf/base/dagster.yml` — add a comment recording that
  the `in_process` executor is load-bearing for admission on the Dagster plane (a
  multiprocess executor would exit the hook op's subprocess and drop the lock before the
  first node runs). Config only; no key changes.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py` — besides registering the
  hook: line 19's Story E2 comment still says C1's translator "runs each node through
  `KedroSession.run` (settings hooks included)". That is the SAME false claim this story
  corrects in `definitions.py`, in the same file the story edits. Correct it too.
- `pixi.lock` (repo root) — adding a member `[package.run-dependencies]` entry changes the
  source package's content hash and `depends` list, so the committed lock goes stale.
  Regenerate and commit it (`pixi lock`), then re-run the gates with `--frozen`. Also check
  whether `environment.yaml` changes (`pixi project export conda-environment -e build`); if
  it does, commit that too — the repo's env-sync CI gate is ungated by the `maintenance`
  label.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
  — line 196: drop the `**DEMOTED 2026-07-27 …**` block and restore the full-form rule
  (exact restore text in Design Notes). The AD-13 entry at 132-136 is the format exemplar.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md`
  — lines 252-262: the kernel's "One execution plane" constraint still says
  "**Run admission is NOT implemented**"; correct it to describe what now ships.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md` — line 601 (Story C1
  Invariants): un-strike the `~~run admission serializes per dataset set~~` clause and
  point it at this story instead of at the retraction.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-c1-integrate-kedro-dagster-for-scheduling-execution.md`
  — lines 44 AND 66 carry the same retracted string (body + "Planning metadata" mirror of
  epics.md:601). Both must change, identically.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md`
  — line 64 still asserts admission as shipped AND attributes the mechanics to Dagster
  ("the queue/reject mechanics are Dagster-owned (C1/AD-23)"). D1 explicitly rejected the
  Dagster run-queue; re-attribute it to the hook-level file lock.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` —
  `DW-AD23-1` is cited in eight places and **defined in none**. Add it, in the newest entry
  shape (`DW-I4-1` at lines 578-600 is the template: `source_spec` / `origin` / `summary` /
  `resolution` / `status`), immediately after line 600 and before `## 24. Sprint status`,
  with `status: closed` naming this story; bump the frontmatter `entries: 53` to `54`.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/pyproject.toml` + `src/shared/packages/pyforge-atlas/pixi.toml` -- declare `filelock>=3.32.0` in both -- D1 requires `filelock`; AUD-ATLAS-010 doctrine forbids importing it undeclared. Do this FIRST so the import is legal when written.
- [x] `src/pyforge/atlas/admission.py` -- create the module: errors, `AdmissionTicket`, `default_lock_root()`, `acquire()` / `release()`, and `RunAdmissionHooks` with `before_pipeline_run` / `after_pipeline_run` / `on_pipeline_error` / `__deepcopy__` / `__getstate__` / `__setstate__` -- the whole D1-D5 mechanism, in the one module the AD-7 tool gate never inspects and the AD-1 glue ban does not touch.
- [x] `src/pyforge/atlas/settings.py` -- register `RunAdmissionHooks()` as the fourth entry in `HOOKS` -- D2: one registration is what makes CLI, MCP and Dagster all inherit admission.
- [x] `tests/test_admission.py` -- write the two-process gate (same-set rejected, disjoint-set admitted, `SIGKILL`ed-holder reclaimed) plus single-process unit tests for every row of the I/O matrix -- the defect is cross-process, so a single-process test does not discharge the AC.
- [x] `src/pyforge/atlas/orchestration/definitions.py` -- correct the lines 22-30 docstring -- D6: the retraction becomes false the moment the hook lands.
- [x] `.../planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md` -- re-promote AD-23 to full form -- D6, and the only reason AD-23 was demoted is now gone.
- [x] `.../planning-artifacts/specs/spec-pyforge-atlas/SPEC.md` -- correct the kernel's "Run admission is NOT implemented" clause -- leaving it would re-create the exact spec-outruns-code defect AUD-ATLAS-046 raised, with the sign flipped.
- [x] `.../planning-artifacts/epics.md` (line 601) + `.../specs/spec-c1-...md` (lines 44 and 66) -- un-retract the C1 invariant in all three copies -- they mirror one string; fixing one and not the others is how the drift started.
- [x] `.../planning-artifacts/specs/spec-b3-...md` (line 64) -- re-attribute the mechanics from "Dagster-owned" to the hook-level file lock -- D1 rejected the Dagster run-queue; this line is now wrong in its mechanism even though its claim became true.
- [x] `.../planning-artifacts/deferred-work-ledger.md` -- create the missing `DW-AD23-1` entry with `status: closed` AND a `DW-AD23-2` entry for the E2 `run_result` declaration + the `in_process`-executor coupling; sync the frontmatter `entries` count to the actual `## DW-` heading count -- eight artifacts cite an id the ledger never defined; closing a phantom is not closure.
- [x] `src/shared/packages/pyforge-atlas/conf/base/dagster.yml` + `.../src/pyforge/atlas/settings.py` (line 19) -- record the `in_process` coupling; correct the Story E2 comment's `KedroSession.run` claim -- the same untruth this story removes from `definitions.py`, left standing two blocks above the new hook registration.
- [x] `pixi.lock` (+ `environment.yaml` if it changes) -- regenerate after the member-manifest edit -- a stale lock reds any non-`--frozen` run and any lock-freshness CI gate.

**Binding evidence rules (review pass 1):**
- Every count written into a doc or ledger entry must be **re-run, not transcribed** — the
  first pass recorded `kedro-test` as 837 when the tree gave 838. In a story about not
  asserting unverified things, copied evidence is the wrong habit.
- The re-promoted AD-23 text must not say the three planes inherit admission "**identically**".
  Acquisition is identical; release on the Dagster plane is process-local, and `DW-AD23-2` is
  open against it. State the acquisition guarantee precisely and carry the release boundary
  the same way the NFS boundary is carried — AD-23 was demoted for claiming more than shipped,
  and a smaller version of that overclaim is still one.

**Acceptance Criteria:**
- Given `settings.HOOKS`, when the project is configured, then `RunAdmissionHooks` is registered beside `ProjectHooks`, `AtlasObservabilityHooks` and `DataValidationHooks`, and a `copy.deepcopy` of it is still a working hook with empty per-run state.
- Given a real second OS process holding the locks for a pipeline's output set, when a run requests the same set, then it is rejected before any node executes and the error names the conflicting dataset, the holder's run id, PID and hold start time.
- Given that same holding process, when a run requests a disjoint output set, then it is admitted and completes while the first still holds — proving admission is per dataset set, not global.
- Given a run that raises inside the runner, when `on_pipeline_error` fires, then every lock that run held is released and a subsequent same-set run is admitted.
- Given `filelock` is imported at module level in shipped package code, when the manifests are read, then both `pyproject.toml` and the member `pixi.toml` declare it (AUD-ATLAS-010).
- Given the story is green, when `ARCHITECTURE-SPINE.md`, `SPEC.md`, `epics.md:601`, both `spec-c1` copies, `spec-b3:64` and `orchestration/definitions.py` are read, then none of them still claims run admission is unimplemented, and none attributes the mechanism to Dagster's run queue.
- Given `deferred-work-ledger.md`, when `DW-AD23-1` is looked up, then it exists, is closed by this story, and the frontmatter `entries` count matches the number of entries.
- Given a process whose CWD is NOT the Kedro project root, when `default_lock_root()` is resolved, then it is anchored under the same root that a real catalog entry's `filepath` resolves to — so two processes writing one Parquet from different CWDs contend on the same lock file.
- Given an absolute `PYFORGE_ATLAS_DATA_ROOT`, when the lock root is resolved, then it is honored verbatim and the locks move with the store.
- Given the shipped `settings.HOOKS` with NO injected `lock_root`, when a run is admitted through kedro's real hook manager, then the lock file appears under the project-anchored default — i.e. the wiring that actually ships is what the gate exercises.
- Given a `release()` issued from a different thread than the acquirer, when it runs, then the lock is genuinely released (`thread_local=False`) and a subsequent same-set run is admitted.
- Given an `OSError` at any point inside `acquire()`, when it propagates, then no lock taken earlier in that call is left held.
- Given the two-process gate, when a child process hangs or floods stderr, then the test FAILS within a bounded time rather than wedging the suite.

## Spec Change Log

### 2026-07-29 — review pass 1 (bad_spec loopback)

**Triggering finding (high):** the shipped `default_lock_root()` was CWD-relative, while
kedro resolves every catalog `filepath` to an absolute path under the **project root**
(`KedroContext._get_catalog` → `_convert_paths_to_absolute_posix(project_path=…)`).
Demonstrated from `/tmp`: lock root `/tmp/data/.locks`, guarded file
`<project>/data/primary/…parquet`. Two processes writing the same Parquet from different
CWDs would take locks in different directories — **the flagship "MCP trigger racing a
`kedro run`" race the story exists to close was still completely open**, and it is not
hypothetical: the MCP server runs from the repo root while the repo's own pixi tasks set
`cwd = "src/shared/packages/pyforge-atlas"`.

**Root cause was in this spec, not in the code.** Design Notes § "Lock root mirrors
`globals.yml`" asserted a CWD-relative default *because that is how the catalog resolves the
filepaths being guarded*. That premise is false, and the implementation faithfully built what
it said. A second bad_spec compounded it: the spec's test plan never required exercising the
shipped default, so all 35 tests injected `lock_root=tmp_path` and the gate went green over a
mechanism that could not work.

**What was amended (all outside `<intent-contract>`):**
- Design Notes § lock root: replaced wholesale with the project-anchored resolution, the
  measurement that disproves the old premise, and the `run_params["project_path"]` channel.
- Design Notes § Dagster plane: corrected two mechanism claims the first pass got backwards —
  pluggy's missing-arg check is per-IMPL not per-call, and kedro registers `settings.HOOKS`
  in tuple order with LIFO dispatch, so `RunAdmissionHooks` runs **first**. The subset
  `after_pipeline_run` signature is still required, for the corrected reason (running first,
  a full signature would make it the raiser and it would never release).
- Design Notes: added nine binding correctness requirements from review (`thread_local=False`;
  roll back on any exception; `release()` must not abort mid-loop; ticket-key collision guard;
  no unguarded `os.kill` on Windows; no reclaim claim without a PID; keep typed errors typed;
  fix the rejection message's unreachable MCP advice; record the `in_process` coupling).
- Code Map + Tasks: added the three lock-root/wiring tests, the harness anti-hang rules,
  `conf/base/dagster.yml`, the stale Story E2 claim at `settings.py:19`, and `pixi.lock`.
- Tasks: added binding evidence rules (re-run counts, never transcribe; AD-23 must not say
  the planes inherit "identically").
- Acceptance Criteria: seven new Given/When/Then covering the above.

**Known-bad state this avoids:** shipping an admission mechanism that silently does nothing
whenever two writers run from different working directories, while `ARCHITECTURE-SPINE.md`
re-promotes AD-23 to its full form on the strength of it — i.e. re-committing `AUD-ATLAS-046`
(a spine invariant asserting more than the code delivers) in the very story that closes it.

**KEEP — what worked and must survive re-derivation:**
- The module shape: `AdmissionConfigError` / `RunAdmissionRejected` (with `datasets`,
  `conflicting`, `holder_run_id`, `holder_pid`, `held_since`) / `AdmissionTicket` /
  `default_lock_root` / `acquire` / `release` / `RunAdmissionHooks`, in `admission.py`,
  stdlib + `filelock` + `kedro.framework.hooks` only.
- `pipeline.all_outputs()` verbatim with the measured justification (46 outputs, 1
  unregistered, 0 shared across pipelines) — do NOT re-litigate catalog filtering.
- Transcoding strip, `sorted()` acquisition order, ONE shared deadline across all locks,
  partial-acquisition rollback, and the sidecar `<name>.holder.json` design.
- D5 built on the fact that the kernel drops a dead holder's `flock`, with the surviving
  sidecar reclaimed and recorded on `ticket.reclaimed` + a WARNING — never lock-breaking.
- `__deepcopy__` / `__getstate__` / `__setstate__` mirroring `AtlasObservabilityHooks`.
- The two-process gate design: `subprocess.Popen` on `sys.executable`, a real
  `kedro.pipeline.Pipeline` + `DataCatalog` + the real hook in the child, JSON verdicts, and
  a genuine `SIGKILL` for the reclaim case. No threads, no mocks.
- The mutation check (make each process use a per-PID lock path; the same-set and
  wait-deadline tests must go RED) — re-run it, it is what proves the gate is not vacuous.
- `test_the_hooks_are_callable_on_both_the_kedro_and_the_dagster_plane` driving kedro's real
  `_create_hook_manager()` with each plane's argument names.
- Every doc/ledger edit: the AD-23 re-promotion, `SPEC.md`, `epics.md:601`, both `spec-c1`
  copies, `spec-b3:64`, the `definitions.py` docstring, and `DW-AD23-1` — subject to the
  corrections listed above (the "identically" wording, the `DW-AD23-2` mechanism sentence,
  and the re-run gate counts).

## Review Triage Log

### 2026-07-29 — Review pass 1
- intent_gap: 0
- bad_spec: 4: (high 2, medium 2, low 0)
- patch: 14: (high 0, medium 9, low 5)
- defer: 1: (high 0, medium 0, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[bad_spec]` `default_lock_root()` was CWD-relative while kedro anchors catalog filepaths to the project root — the flagship cross-CWD race was unguarded. Root cause: Design Notes asserted the false premise. Spec amended to require project-anchored resolution via `run_params["project_path"]` / a package-derived root; code reverted for re-derivation.
  - `[high]` `[bad_spec]` The test plan never exercised the shipped default (all 35 tests injected `lock_root`), which is why the above shipped green. Spec now requires a cross-CWD lock-root test, an absolute-`PYFORGE_ATLAS_DATA_ROOT` test, and a real-`settings.HOOKS` wiring test.
  - `[medium]` `[bad_spec]` Design Notes stated pluggy's missing-arg check as per-call and left hook ordering vague; both were verified backwards (it is per-impl, and LIFO makes `RunAdmissionHooks` run FIRST). Corrected, along with the reason the subset `after_pipeline_run` signature is required.
  - `[medium]` `[bad_spec]` The AD-23 restore text supplied by Design Notes claims the three planes inherit admission "identically", which the same story's own `DW-AD23-2` contradicts. Spec now forbids that wording and requires the release boundary to be carried like the NFS one.
  - `[medium]` `[patch→spec]` `filelock` defaults to `thread_local=True`; a cross-thread `release()` is a silent no-op that wedges the dataset with an unattributable holder. Now binding: `thread_local=False`.
  - `[medium]` `[patch→spec]` `acquire()` rolled back only on `filelock.Timeout`; any `OSError` stranded every lock already taken, unreleasable. Now binding: roll back on any exception.
  - `[medium]` `[patch→spec]` `release()` aborted mid-loop if one `lock.release()` raised, leaving a partially-released ticket and converting a good run into a failure. Now binding: log and continue.
  - `[medium]` `[patch→spec]` Ticket map keyed on `run_id`, which kedro-dagster reuses across every job — a second run in one process orphans the first ticket or releases the wrong locks. Now binding: guard the collision loudly.
  - `[medium]` `[patch→spec]` `os.kill(pid, 0)` calls `TerminateProcess` on Windows (a declared platform), so the liveness probe kills the process it probes. Now binding: POSIX-gate the probe.
  - `[medium]` `[patch→spec]` `pixi.lock` goes stale once the member manifest declares `filelock`; reproduced as an 89-line rewrite. Now a task, with the `environment.yaml` check.
  - `[medium]` `[patch→spec]` The two-process harness can HANG an unattended run: `readline()` with no timeout and an undrained `stderr` pipe. Now binding: bounded read, no undrained pipe.
  - `[medium]` `[patch→spec]` The rejection message advises `--params admission_wait_seconds=…`, which is unreachable from MCP (all seven tools call `run_pipeline("<name>")` with no params). Now binding: word it honestly for both planes.
  - `[low]` `[patch→spec]` `settings.py:19` still carried the identical false `KedroSession.run` claim this story removes from `definitions.py`. Added as a task.
  - `[low]` `[patch→spec]` `DW-AD23-1` recorded `kedro-test` as 837 when the tree gave 838. Added a binding rule: re-run counts, never transcribe.
  - `[low]` `[patch→spec]` `conf/base/dagster.yml`'s `in_process` executor is load-bearing for Dagster-plane admission and that coupling was undocumented. Added as a task.
  - `[low]` `[patch→spec]` Typed-error leaks: `float()` `OverflowError` on a huge int, `time.gmtime()` on an out-of-range `started_at`, a bare `str` dataset argument locked character-by-character, and `wait_seconds` unvalidated on the empty-output early return. All now binding.
  - `[low]` `[patch→spec]` A holder record with a `run_id` but no usable `pid` was logged as a `SIGKILL` reclaim. Now binding: no reclaim claim without a PID to judge.

### 2026-07-29 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 17: (high 0, medium 9, low 8)
- defer: 0
- reject: 2: (high 0, medium 0, low 2)
- addressed_findings:
  - `[medium]` `[patch]` `acquire()`'s rollback released the k-1 locks but left the holder sidecars it had written. Those records name the rejected run; once its process exits they read as a dead holder, so the NEXT acquirer of each dataset reported a false D5 reclaim + WARNING (a `__default__` run rejected at index 37 would fire it 37 times). Rollback now unlinks them first; pinned by a mutation-verified test.
  - `[medium]` `[patch]` `test_gate_opt_in_wait_admits_when_the_holder_releases_in_time` was vacuous — mutating `wait_seconds` to `0.0` still passed, so half of D3 shipped unproven. Rewritten: the parent holds in-process, the child announces readiness, must stay silent for a blocked window, and is admitted only after the release. Verified RED under the same mutation.
  - `[medium]` `[patch]` `filelock` silently rewrites its own class to `SoftFileLock` when `flock` returns `ENOSYS` (a relocated store on a FUSE/9p mount is a supported override) — which would void the "the kernel drops its flock" premise D5 rests on. Now `fallback_to_soft=False`, so it fails loudly instead of degrading quietly.
  - `[medium]` `[patch]` `_release_for` popped the ticket stack LIFO, and its comment justified that with a non-sequitur (set-disjointness says nothing about which ticket belongs to the finishing pipeline). Under one shared `run_id` the first-started run finishing first would have released a live run's locks. Now paired by dataset set; the comment says why, and says not to "simplify" it back.
  - `[medium]` `[patch]` `_PROJECT_ROOT` derived the root from `__file__` with no self-check, unlike `mcp/session.py` which asserts on the identical derivation — installed from the built `.conda`, `parents[3]` lands in `site-packages` and admission would guard the wrong tree. Now validated against `conf/base/catalog.yml`, raising rather than guessing.
  - `[medium]` `[patch]` A relative or empty `project_path` (a Dagster resource-config override, or a direct caller) would have quietly restored the CWD-anchoring that caused the pass-1 revert. Relative now raises `AdmissionConfigError`; empty falls back to the validated derived root.
  - `[medium]` `[patch]` "queued" overclaimed: `filelock` polls with no ordering or fairness, so a waiter can lose to a later arrival. Corrected to bounded retry-to-a-deadline in `ARCHITECTURE-SPINE.md`, `SPEC.md`, `spec-b3`, and `definitions.py` — aspirational vocabulary is the exact defect this story exists to purge.
  - `[medium]` `[patch]` A third boundary — kedro calls `before_pipeline_run` outside its `try` and admission is dispatched first, so a later before-hook that raises strands the locks until process exit (a wedge for the long-lived MCP server) — was recorded only in the source docstring while the spine, `SPEC.md` and `DW-AD23-2` each listed two. Now carried in all three.
  - `[medium]` `[patch]` The audit spec that RAISED `AUD-ATLAS-046` (`pyforge-marshal`) still recorded it as `KEEP_DEFER — admission not started`, contradicting the freshly promoted spine and inviting a future sweep to re-open shipped work. Marked fixed against its own exit criteria, with the history left intact.
  - `[low]` `[patch]` `_read_holder` leaked `OverflowError` on a JSON *integer* wider than float range, contradicting its own "never turns a clean rejection into a crash" contract (the existing test used `1e300`, which parses as a float and took the passing branch).
  - `[low]` `[patch]` Docs described the locked set as the "declared OUTPUT dataset set" while the code takes `all_outputs()` — a deliberate superset. Code and docs now agree, and name the future condition under which narrowing becomes necessary.
  - `[low]` `[patch]` The ticket registry kept one dead `run_id` key per run — unbounded growth in a long-lived MCP server. Empty stacks are now popped.
  - `[low]` `[patch]` Whitespace-only `PYFORGE_ATLAS_LOCK_ROOT` / `PYFORGE_ATLAS_DATA_ROOT` would have created a directory literally named spaces; now stripped and treated as unset.
  - `[low]` `[patch]` `DW-AD23-2` cited "~12 positional call sites"; the counted value is 10. Corrected — this story's own binding rule is that numbers are re-run, not transcribed.
  - `[low]` `[patch]` `DW-AD23-1`'s gate evidence was re-stamped from the pass-1 figures to the re-run values (874/19, 71 admission tests).
  - `[low]` `[patch]` Test hygiene: the POSIX-gate tests monkeypatched `admission.os` — which IS the stdlib module — mutating `os.name`/`os.kill` process-wide. Added a module-level `_IS_POSIX` indirection and repointed the tests at it.
  - `[low]` `[patch]` Test hygiene: the wiring test left a permanent `data/.locks/admission_wiring_probe.lock` in the real project tree (filelock never unlinks), making it non-hermetic across runs; it now cleans up in a `finally`. Also removed an unused `caplog` fixture.
  - rejected: promoting this story spec into `planning-artifacts/specs/` and adding the PR's `maintenance` label — both real repo conventions, but post-merge orchestrator duties, not defects in this diff.

### 2026-07-29 — Review pass 3 (follow-up review, triggered by pass 2's `followup_review_recommended`)

- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 0, medium 6, low 7)
- defer: 1: (high 0, medium 1, low 0)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` **"`RunAdmissionHooks` runs FIRST" was false in the shipped environment.** The spine, `SPEC.md`, `settings.py` and the module docstring all derived it from "appended last + pluggy LIFO" — but `KedroSession.__init__` registers `settings.HOOKS` and THEN `_register_hooks_entry_points(...)`, so an installed plugin registers later and therefore dispatches EARLIER. Measured on a real session: kedro-viz's `PipelineRunStatusHook` (installed in this env) preceded admission on all three of `before_pipeline_run` / `after_pipeline_run` / `on_pipeline_error`. Because kedro calls `after_pipeline_run` outside its `try` as well, a raising plugin after-hook would have stranded every lock with no error hook to compensate — a release-side stranding mode absent from all three carried boundary lists. Fixed by making the claim TRUE rather than by softening it: `@hook_impl(tryfirst=True)` on all three hooks (verified to beat a later-registered plain `@hook_impl`), with the mechanism recorded in `admission.py`, `settings.py`, the spine, `SPEC.md` and `DW-AD23-2`.
  - `[medium]` `[patch]` The test meant to gate that ordering asserted `settings.HOOKS[-1] is RunAdmissionHooks` — tuple position, not dispatch order — which is why the finding above shipped invisibly. Replaced with `test_admission_is_dispatched_first_on_a_real_session_not_merely_last_in_the_tuple`, reading `get_hookimpls()` off a real `KedroSession`; verified RED with the markers removed.
  - `[medium]` `[patch]` **`test_the_opt_in_wait_is_one_deadline_shared_across_all_locks` was vacuous** — the same defect class pass 2 removed from the wait gate. Holding `{a,b,c}` and requesting `{a,b,c}` means the contender times out on the first sorted lock and never reaches a second; measured, a per-lock-deadline mutant finished in 0.504s against the shipped 0.505s and cleared the same `< 1.4` bar. The "ONE shared deadline" property is asserted in `admission.py`, `SPEC.md` and the ledger and was entirely unproven. Rewritten to hold `a` and `b` as separate tickets and free `a` mid-budget so the contender must reach `b`; verified RED under the per-lock mutant.
  - `[medium]` `[patch]` `_release_for`'s no-match fallback released `stack[-1]` — the bare LIFO pop the comment five lines above it forbids by name, and which `test_tickets_pair_by_dataset_set_...` exists to prove wrong. With two runs outstanding under one `run_id` it frees a run that is still writing. Now: more than one ticket and no match ⇒ release NOTHING and log at ERROR (process exit still frees them, and no second writer is admitted meanwhile); exactly one ticket ⇒ release it, there being no ambiguity to protect against.
  - `[medium]` `[patch]` `_pid_alive` leaked `OverflowError` on a sidecar pid wider than a C int (`os.kill(10**20, 0)` raises it; neither `OSError` nor `ValueError`). Worse than the sibling `held_since` cases: it fires on the SUCCESS path, after the lock is taken, so a garbage record left by anything else turned a successful admission into an untyped crash. Also: a pid `<= 0` read as a live holder (`os.kill(0, 0)` signals this process's group, `os.kill(-1, 0)` every signalable process), so a record naming no process at all was never reclaimable.
  - `[medium]` `[patch]` A relative `lock_root` passed to `acquire()` or `RunAdmissionHooks()` silently re-anchored the locks to the CWD — the exact defect pass 1 reverted the entire implementation for, reachable through the one input door `_resolve_base`'s guard did not cover. Now refused with `AdmissionConfigError`, matching the `project_path` guard.
  - `[medium]` `[patch]` A FAILED Dagster run releases nothing in-process: kedro-dagster skips the after-op and fires `on_pipeline_error` from a `@dg.run_failure_sensor` executing in the DAEMON process, where `_tickets` is empty. Safe today only because Dagster runs workers as separate processes — the same shape of undeclared coupling as `in_process`, and absent from `DW-AD23-2`'s three residuals. Added as residual (4), and carried in the spine and `SPEC.md`.
  - `[low]` `[patch]` `acquire()` appended to `written` only AFTER `_write_holder` returned, but `Path.write_text` truncates on open — so an `OSError` mid-write (the ENOSPC case the rollback exists for) left a torn sidecar that rollback would not unlink.
  - `[low]` `[patch]` `release()` unlinked the sidecar BEFORE releasing, so a `release()` that raised left the flock held with its record already gone — `run None (pid None)`, unattributable and unreclaimable, the state correctness requirement 1 exists to prevent. Reversed: unlink only after a confirmed release. The opposite window (a free lock still advertising a holder) is self-correcting, since the next acquirer takes the lock first and finds a live pid.
  - `[low]` `[patch]` `test_locks_never_silently_downgrade_to_a_soft_lock` asserted `isinstance(lock, filelock.UnixFileLock)` unconditionally, reddening on `win-64` — a declared platform the module POSIX-gates `_pid_alive` for. Made platform-conditional; the invariant ("a kernel lock, not filelock's marker-file emulation") is unchanged.
  - `[low]` `[patch]` The rejection message claimed "an MCP `run_*` trigger has no params channel". True of the seven FastMCP wrappers, false of the function that raises it: `mcp.tools.run_pipeline(name, extra_params=...)` reaches `runtime_params` through `KedroSession.create`. Reworded to name the real channel and scope the caveat to the wrappers.
  - `[low]` `[patch]` `default_lock_root`'s docstring claimed its `.strip()` "matches `settings._env_or`"; `_env_or` passes any truthy value through unstripped. The stripping is still right — it is now documented as a deliberate divergence rather than as a mirror it is not.
  - `[low]` `[patch]` Test hygiene: the headline wait test's closing `admitted_at > released_at > spawned_at + _BLOCKED_WINDOW` was true by construction (`released_at` is sampled after a mandatory blocking poll) and read as corroboration it did not supply — replaced; `assert early is None` now also asserts the child is still ALIVE, so a child that crashed after the handshake fails there rather than 45s later as an unrelated-looking timeout; and the child-reap loop no longer aborts on one `TimeoutExpired`, stranding the remaining children.
  - deferred (1): run admission is writer-writer exclusion only, and the concurrency it deliberately permits is reader-writer unsafe — `pandas.ParquetDataset.save` truncates in place, and the 7 pipelines carry 12 cross-pipeline write→read edges, so a run admitted for having a disjoint OUTPUT set can read a half-written Parquet. Pre-existing, and strictly improved by this story, but newly over-assumable now that per-dataset-set granularity is documented as a feature. Closing it needs atomic dataset writes or read-locks — wider than an admission story.
  - rejected (4): rewriting `sprint-change-proposal-2026-07-27.md` and `.memlog.md` (the spec names both as historical/append-only records of what was believed at the time), and `spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md` (a self-described derived archive, not a canonical copy); and validating that an explicitly-supplied ABSOLUTE `project_path` is a Kedro root — the `__file__`-derived fallback is checked precisely because nobody chose it, whereas an explicit argument is the caller's choice to make.
### 2026-07-29 — Review pass 4 (follow-up review, triggered by pass 3's `followup_review_recommended`)

- intent_gap: 0
- bad_spec: 0
- patch: 18: (high 0, medium 7, low 11)
- defer: 1: (high 0, medium 0, low 1)
- reject: 5: (high 0, medium 1, low 4)
- addressed_findings:
  - `[medium]` `[patch]` **`after_pipeline_run` / `on_pipeline_error` declared `catalog` (and `error`) they never read** — re-creating, on the RELEASE path, the exact `HookCallError` exposure the subset-signature comment claims to have eliminated. pluggy's missing-arg check is per-IMPL, so every declared argument is one a caller must supply; and under `tryfirst` admission is asked FIRST, so it is the raiser and nothing downstream can compensate. Reproduced: `after_pipeline_run(run_params=…, pipeline=…, run_result={})` with no `catalog` → `HookCallError` from admission's own impl, ticket still outstanding, flock still held — for the long-lived MCP server, until restart. All three hooks now declare exactly `(run_params, pipeline)`; pinned by a signature assertion plus real-hook-manager calls that omit `catalog`/`error`. Mutation-verified RED.
  - `[medium]` `[patch]` **`release()` deleted the SUCCESSOR's holder record.** Pass 3 reversed the order to unlink after releasing; a contender can win the flock and write its own sidecar inside that gap, and the departing run then unlinks the LIVE holder's file. Reproduced deterministically: run B admitted, record present, A's unlink → `run None (pid None)`. Costs the rejection diagnostics the AC demands and kills the D5 reclaim WARNING if B is later `SIGKILL`ed. Now unlinks BEFORE releasing (nobody else can be the holder while we hold it) and re-writes the record if the release did not actually let go — closing both windows rather than trading one for the other. Pinned by an ordering spy; mutation-verified RED.
  - `[medium]` `[patch]` **`_release_for` with `pipeline=None` fell through to the bare LIFO pop it forbids by name.** Pass 3's ambiguity guard covered the no-MATCH case only. Measured: `{x}` and `{y}` outstanding under one `run_id`, `_release_for(rp, None)` freed `y` — a run that is still writing. Same rule now applies to the no-pipeline case: release NOTHING, log at ERROR. Mutation-verified RED.
  - `[medium]` `[patch]` **`_release_for` could raise out of `after_pipeline_run`**, contradicting `release()`'s "never raises, never fails a good run" contract: `_lock_names(pipeline.all_outputs())` sat outside every guard, and kedro calls `after_pipeline_run` OUTSIDE its `try`. An `AdmissionConfigError` or `AttributeError` there failed a run whose nodes had all succeeded AND stranded the ticket. Now guarded, falling back to the single-ticket rule.
  - `[medium]` `[patch]` **`default_lock_root` resolved the project root BEFORE reading the env**, so an absolute `PYFORGE_ATLAS_LOCK_ROOT` could not rescue a non-editable install — while `_resolve_base`'s own error advertises exactly that remedy. Reproduced. The env is now read first; an absolute value needs no anchor. Mutation-verified RED.
  - `[medium]` `[patch]` **`test_the_in_process_executor_coupling_is_recorded_in_dagster_yml` guarded the comment, not the coupling** — it asserted only that the strings `admission` and `in_process` appear, and both live inside the warning comment. Flipping `jobs.__default__.executor` to `multiprocess`, the one change that whole block forbids and the one that silently voids admission on the Dagster plane, passed green. Now parses the YAML and asserts every job's executor. Mutation-verified RED.
  - `[medium]` `[patch]` **`test_gate_opt_in_wait_rejects_when_the_deadline_expires` was vacuous** — it asserted only the rejection fields, so a mutant ignoring `wait_seconds` entirely produced identical results. Third instance of this defect class in three passes. Now asserts the deadline was actually waited out. Mutation-verified RED.
  - `[low]` `[patch]` `_write_holder` used `Path.write_text` (`O_TRUNC`), authoring the very "torn sidecar" state `_read_holder` and `RunAdmissionRejected` go to such lengths to survive — and doing so in the window right after the flock is taken, i.e. exactly when a contender is reading. Measured: a read in that window degrades every field to `None`. Now temp file + `os.replace`; pinned by an already-open reader that must still see the whole previous record. Mutation-verified RED.
  - `[low]` `[patch]` A dataset name containing a path separator or a `..` segment escaped the lock root: measured, `acquire(["../escaped"], lock_root=R)` created the lock OUTSIDE `R`, where nothing anchored to `R` ever contends with it — admission silently off for that dataset. Now refused with `AdmissionConfigError`. Mutation-verified RED (5 cases).
  - `[low]` `[patch]` `__deepcopy__`'s justification ("C1's `KedroProjectTranslator` DEEP-COPIES `settings.HOOKS` at `to_dagster()` build time") is false for the installed kedro-dagster 0.7.x: `translator.py:253,262` pass the hook manager BY REFERENCE and the only `deepcopy` in the package is in `datasets/partitioned_dataset.py`. The contract is worth keeping as defence; the unmeasured mechanism claim is not — in a story whose thesis is that. Restated in `admission.py` and in the test docstring.
  - `[low]` `[patch]` `tests/test_admission.py` still carried "Because admission is registered LAST it is dispatched FIRST" — the precise claim pass 3 measured wrong and corrected in the spine, `SPEC.md`, `settings.py`, `admission.py` and `DW-AD23-2`, left standing in the very file whose new test exists to distinguish the two.
  - `[low]` `[patch]` A rejected run emitted no observability at all: `tryfirst` means no observability hook has run, and kedro fires no error hook for a raise in `before_pipeline_run`, so an admission conflict in the unattended factory left only a traceback. Now logged at WARNING before the raise.
  - `[low]` `[patch]` The boundary list said "only exceptions from `runner.run` reach `on_pipeline_error`" — imprecise: kedro catches `Exception`, so a `KeyboardInterrupt`/`SystemExit` out of the runner fires NEITHER hook. Sharpened in `admission.py`, the spine, `SPEC.md` and `DW-AD23-2`(3).
  - `[low]` `[patch]` The lock store lives inside the tree it guards (`<data_root>/.locks`), so `rm -rf data/` — a routine "force a rebuild" — unlinks the inode a live holder's flock belongs to and lets the next acquirer create a fresh file at the same path: two writers, silently. Undocumented anywhere. Now carried in the module boundary list, the spine and `SPEC.md`, with the `PYFORGE_ATLAS_LOCK_ROOT` mitigation named.
  - `[low]` `[patch]` `DW-AD23-2`'s summary opened "**Two** coupled residuals" while enumerating four (pass 3 added the fourth), and its title scoped the entry to the Dagster plane although residual (3) affects the MCP server today — inviting exactly the mis-scoping that drops it. Both corrected. Only the two ledger entries THIS diff created were touched; no pre-existing entry's status or resolution was altered.
  - `[low]` `[patch]` `DW-AD23-1`'s gate evidence re-stamped from the pass-3 figures to the pass-4 re-run (901/19, 98 admission tests) — this story's own binding rule is that counts are re-run, never transcribed.
  - `[low]` `[patch]` Coverage gaps in code this story added: `_resolve_base`'s site-packages guard (the sole protection against anchoring the locks to the wrong tree — the defect pass 1 reverted the whole implementation for) and `_lock_names`'s non-iterable branch were both untested. Tests added.
  - `[low]` `[patch]` Flake risk: the shared-deadline test's upper bound left ~150 ms of slack on a 1 s budget on an unattended, possibly loaded runner. The property is a ratio, so both terms were tripled — identical discrimination, 3× the margin. Test hygiene: a misplaced `# noqa: BLE001` on an `except OSError`, and a docstring that described the pre-pass-4 release ordering.
  - deferred (1): `observability.py` states in three places that the translator deep-copies the settings hooks — measured false against the installed kedro-dagster — and its lazy-`TracerProvider` design at `:188-195` exists specifically to satisfy that build. Pre-existing and E2-owned; surfaced only because the new hook copied the claim verbatim.
  - rejected (5): PID recycling defeating `_pid_alive` (real, but the consequence is one missing WARNING and the fix needs boot-relative process start times — complexity against Simplicity First); no upper bound on `admission_wait_seconds` (`1e12` is finite and is the caller's explicit choice, which is what the validator exists to honour); the spine "already-running pipeline" phrasing (the same sentence states the dataset-set rule first); "harmless for a CLI run" allegedly understating false-corpse noise (a run that died holding IS a corpse — D5 firing is correct behaviour, not noise); and `zip(strict=True)` in `release()` (it would introduce a raise path into a function contractually forbidden to raise — handled instead by logging the mismatch and releasing every lock the ticket carries).


## Design Notes

**Why `all_outputs()` verbatim, with no catalog filtering — measured, not assumed.**
`pipeline.all_outputs()` (kedro 1.5.0, `kedro/pipeline/pipeline.py:397`) returns every
output including in-run intermediates; `outputs()` (`:424`) drops intermediates and would
under-lock catalog-registered intermediates that really are written to Parquet. So
`all_outputs()` is the right call. The obvious next worry — that unregistered
(`MemoryDataset`) names would cause false conflicts between genuinely disjoint pipelines —
was measured against the live project rather than guessed:

```
core: 10 outputs, 0 unregistered      seed_gaps: 4, 0
vcs_health: 8, 0                      universal_sbom: 4, 0
pypi_intelligence: 10, 1 (pypi_conda_mapping_base)   vulnerability: 9, 0
derived_artifacts: 1, 0        catalog.yml: 86 entries; NO name is shared by two pipelines
```

One unregistered name exists, in one pipeline, shared with nothing. Filtering by catalog
membership would add a `catalog.get()` call with an instantiation side effect and
dataset-factory-pattern subtleties to prevent a collision that cannot currently occur.
Rejected as speculative (Simplicity First). Transcoded names (`ds@pandas`) are stripped to
their base name for lock identity — there are none today, but two transcoded views of one
file are one file, and `name.split("@", 1)[0]` is the one-line version of the same
correction kedro's own `_remove_intermediates` makes. Hooks receive the FILTERED pipeline
(`session.py:372-380`), so `--to-nodes`/`--tags` narrowing is already reflected; note that
`--only-missing-outputs` is applied inside the runner, so `all_outputs()` can over-lock
there — over-locking is the safe direction.

**Lock root is PROJECT-ANCHORED, never CWD-relative.** This is the correction from review
pass 1 and the single most important rule in this spec — a CWD-relative lock root silently
voids the entire story. Kedro does **not** resolve catalog filepaths against the CWD:
`KedroContext._get_catalog` calls `_convert_paths_to_absolute_posix(project_path=...)`, so
every `filepath` in `catalog.yml` becomes absolute under the Kedro **project root**.
Measured from `/tmp`:

```
CWD          : /tmp
catalog path : <worktree>/src/shared/packages/pyforge-atlas/data/primary/core_feedstock_health/…parquet
```

So the lock must be anchored the same way, or two processes that write the *same* Parquet
take locks in *different* directories and neither sees the other. That is not hypothetical
here: the MCP server runs from wherever Claude Code launched it (repo root), while the
repo's own pixi tasks set `cwd = "src/shared/packages/pyforge-atlas"` because "kedro CLI
needs the project cwd" — i.e. the flagship "MCP trigger racing a `kedro run`" race would
have stayed completely unguarded. Required resolution, mirroring kedro's own semantics:

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]   # src/pyforge/atlas/ -> project root

def default_lock_root(project_path: Any = None) -> Path:
    base = Path(project_path) if project_path is not None else _PROJECT_ROOT
    env = os.environ.get("PYFORGE_ATLAS_LOCK_ROOT") or os.environ.get(
        "PYFORGE_ATLAS_DATA_ROOT", "data"
    )
    root = Path(env)
    return (root if root.is_absolute() else base / root) / ".locks"
```

`before_pipeline_run` passes `run_params["project_path"]` (kedro supplies it in
`record_data`) when present, falling back to `_PROJECT_ROOT`. An absolute
`PYFORGE_ATLAS_DATA_ROOT` is honored as-is — that is the documented way to relocate the
store, and relocating it relocates the locks with it. Do NOT import
`dashboard/data.py::default_data_root()` to get this: it would drag `pandas` and
`semantic.models` (which hard-imports `boring_semantic_layer`) into a module loaded on every
`settings` import. The small duplication is intentional; the CWD-relative *semantics* were
the bug, not the duplication. Side benefit: the member `.gitignore` already has `data/**`,
so project-anchored lock files land gitignored, where a CWD-relative root left an untracked
`data/.locks/` tree at the repo root that the root `.gitignore` does not cover.

**`filelock` semantics, verified live in this env (3.32.0):** `filelock.FileLock` resolves to
`filelock._unix.UnixFileLock` (`fcntl.flock`). Two *distinct* `FileLock` objects on one path
inside ONE process still conflict (separate open file descriptions), so same-process double
admission is rejected too — verified. And because `flock` is owned by the open file
description, the kernel releases it when the holder dies. **That is what makes D5 nearly
free:** a `SIGKILL`ed run does not wedge anything; the only stale artifact is the sidecar
holder record. So `acquire()` writes `<lock_root>/<dataset>.holder.json`
(`{"run_id", "pid", "started_at"}`) after taking `<lock_root>/<dataset>.lock`, and if a
pre-existing holder record is found whose PID is not alive (`os.kill(pid, 0)` →
`ProcessLookupError`; any other `OSError` is treated as *alive*, the conservative direction),
the reclaim is recorded on `ticket.reclaimed` and logged at WARNING. Do not implement
D5 as "break someone else's lock" — that would be a correctness hole, and it is not what the
AC asks for.

**Rollback on partial acquisition is mandatory.** Locks are taken in `sorted()` order (D4's
deadlock avoidance); if the k-th conflicts, the k-1 already held MUST be released before the
`RunAdmissionRejected` propagates, or a rejected run leaves a trail of held locks. The
opt-in wait is a single deadline shared across all locks — `deadline = monotonic() +
wait_seconds`, each `acquire(timeout=max(0, deadline - monotonic()))` — not `wait_seconds`
per lock, which would silently multiply the caller's stated budget by the dataset count.

**Where the wait is turned on.** `settings.HOOKS` constructs the hook with no arguments, so
the live channel is `run_params["runtime_params"]` — `kedro run --params
admission_wait_seconds=30`, or `tools.run_pipeline(..., extra_params={...})`. A
constructor kwarg (`wait_seconds`) exists for direct testing. `run_params` in kedro 1.5.0
carries `run_id` (there is **no** `session_id` and **no** `pipeline_name` key —
`observability.py:304` gets this wrong and its fixture hides it; do not copy that), plus
`runtime_params`, `pipeline_names`, `env`, `project_path`. Source:
`kedro/framework/session/session.py:382-399`.

**Known boundary, write it down:** `before_pipeline_run` is called OUTSIDE the try in
`session.py:427-429` — `on_pipeline_error` only fires for exceptions raised by
`runner.run`. So if a hook ordered after ours raises in `before_pipeline_run`, kedro fires
no error hook and our locks are held until the process exits. Today the only other
`before_pipeline_run` implementation is `AtlasObservabilityHooks`, whose emission paths are
fail-safe, and a process exit releases the flocks regardless. Record this in the module
docstring; do not "fix" it by releasing other runs' tickets, which would be wrong under a
concurrently-serving MCP process.

**The AD-23 restore text.** The clause removed on 2026-07-27 is preserved verbatim at
`sprint-change-proposal-2026-07-27.md:109-111`; restore it and append the mechanism plus the
boundary, keeping the three-bullet `**Binds:** / **Prevents:** / **Rule:**` shape (AD-13,
lines 132-136, is the exemplar):

> A dataset has **one writing run at a time**: run admission serializes on the target
> dataset set, so a concurrent trigger of an already-running pipeline is rejected — or, with
> an explicitly requested bounded wait, queued — never interleaved. Enforced by one OS file
> lock per output dataset in a `settings.HOOKS` hook (`admission.py`), so CLI, MCP trigger
> and Dagster job inherit it identically. **Boundary:** file locks are single-machine; NFS
> `flock` is unreliable, so a multi-machine atlas re-opens the mechanism choice.

**Dagster's run-queue is not wasted.** Once DW-C1-1's daemon lands, `QueuedRunCoordinator`
remains a complementary nicety for Dagster-originated runs; the hook-level lock stays the
actual safety property because it is the only one covering MCP and CLI. Say so in the
`definitions.py` docstring rather than deleting the topic.

**Two-process test shape.** The child is a `sys.executable -c` program that builds a real
`kedro.pipeline.Pipeline` from dataset names on argv, instantiates `RunAdmissionHooks(lock_root=...)`,
calls `before_pipeline_run` with a real `DataCatalog({})`, and prints a JSON verdict —
real objects, no mocks, and the hook path itself is what is exercised. `tests/dashboard/test_dashboard_e2e.py:75-88`
is the in-suite precedent for spawning and reaping a real process (it uses
`multiprocessing.Process`; `subprocess` is preferred here because "a real second OS process"
must be unambiguous and the child must not inherit the parent's `FileLock` file
descriptors). Verify early that a bare `python -c "import pyforge.atlas.admission"` works in
this env — the package is conda-installed into `pyforge-atlas`, so it should, and the whole
gate depends on it.

**The Dagster plane does NOT ride `KedroSession.run` — and pluggy's ordering is what saves
us.** kedro-dagster calls `Node.run(inputs)` directly and invokes the hooks itself, firing
`before_pipeline_run` from a dedicated `before_pipeline_run_hook_<job>` op
(`kedro_dagster/pipelines.py:253-265`). One hook registration still covers all three planes,
because admission rides the HOOK MANAGER, not the session — but say that, don't say
`KedroSession.run`. Three facts, all measured (review pass 1 corrected the first two, which
an earlier pass had stated backwards):

- **Kedro registers `settings.HOOKS` in tuple order and pluggy dispatches LIFO.** Verified.
  `RunAdmissionHooks` is appended last, so it runs **first** — every other hook's
  `before_pipeline_run` executes *after* the locks are taken, in the region kedro leaves
  outside its `try`. That makes the "a later hook raises and strands our locks" boundary
  concrete rather than hypothetical, and the "process exit releases them" mitigation is void
  for the long-lived MCP server. Write the boundary down honestly; do NOT try to fix it by
  releasing other runs' tickets (wrong under a concurrently-serving process).
- **pluggy's missing-argument check is per-IMPL, not per-call.** Verified: with a
  subset-signature impl registered last and a full-signature impl registered first, calling
  `after_pipeline_run(run_results=None, ...)` runs the subset impl and *then* raises
  `HookCallError` from the other. So `RunAdmissionHooks.after_pipeline_run` must declare only
  the subset it reads (`run_params`, `pipeline`, `catalog`) — not because a full signature
  would break other hooks, but because running FIRST it would be **the raiser itself and
  would never release**. Pin it with a test that drives kedro's real `_create_hook_manager()`
  with each plane's argument names.
- `AtlasObservabilityHooks.after_pipeline_run` declares the same unused `run_result`, so the
  Dagster after-op still fails there — after our release has already run. NOT fixed here
  (E2-owned, ~12 positional call sites in `tests/observability/`). Record it as `DW-AD23-2`,
  and state its mechanism correctly in that entry.

**Correctness requirements found by review pass 1 — every one is binding.** They are cheap,
and each closes a way the mechanism fails silently rather than loudly:

1. **`filelock.FileLock(..., thread_local=False)`.** The default is thread-local: a
   `release()` from a different thread than the acquirer is a silent no-op *after* the handle
   has been popped and the sidecar unlinked — the flock is then held for the process lifetime
   with the holder reporting `run None (pid None)`, unreclaimable. Reproduced.
2. **Roll back on ANY exception, not just `filelock.Timeout`.** Wrap the per-name body so an
   `OSError` from `mkdir` / `acquire` / `_write_holder` (ENOSPC, EACCES, EROFS) releases the
   k-1 locks already held before propagating. Today the *expected* failure rolls back and the
   *unexpected* one — the one with no recovery path — does not.
3. **`release()` must not abort mid-loop.** If `lock.release(force=True)` raises, log and
   continue to the remaining locks; never leave a partially-released ticket, and never
   convert a successful run into a failure from `after_pipeline_run`.
4. **Guard the ticket key.** kedro-dagster reuses ONE `run_id` (the build-time session id) for
   every job, so a second `before_pipeline_run` in one process would overwrite the first
   ticket and orphan its locks — or worse, let run A's after-hook release run B's locks. Make
   a collision loud (log + refuse to overwrite), don't let it corrupt the registry.
5. **Do not use `os.kill(pid, 0)` unguarded.** On Windows — a declared platform in the root
   `pixi.toml` — `os.kill` calls `TerminateProcess`, so the liveness *probe kills the process*.
   Gate the POSIX probe on `os.name == "posix"`; elsewhere treat a holder record as alive
   (the conservative direction, and the kernel still frees the flock on death).
6. **Only claim a reclaim when there is a PID to judge.** A holder record carrying a `run_id`
   but no usable `pid` must not be logged as a `SIGKILL` reclaim.
7. **Typed errors stay typed.** `float()` on a huge int raises `OverflowError`, and
   `time.gmtime()` on an out-of-range `started_at` raises `OverflowError`/`OSError` — catch
   both so a bad wait value yields `AdmissionConfigError` and a torn sidecar still yields a
   readable `RunAdmissionRejected`. Reject a bare `str`/`bytes` dataset argument explicitly
   instead of locking it character by character. Validate `wait_seconds` **before** the
   empty-set early return, so the check does not depend on which path you enter.
8. **Fix the rejection message.** It currently tells an operator to
   `--params admission_wait_seconds=…`, which is unreachable from MCP: all seven FastMCP
   tools call `tools.run_pipeline("<name>")` with no params, and `server.py`/`tools.py` are
   out of scope for this story. Word the message for both planes honestly (CLI `--params`;
   from MCP, retry when the holder finishes).
9. **Note the `in_process` coupling.** Acquisition happens inside the
   `before_pipeline_run_hook_<job>` **op**; under a multiprocess Dagster executor that op's
   subprocess exits immediately and the kernel drops the lock before the first node runs.
   It is safe today only because `conf/base/dagster.yml` declares `in_process`. Say so in
   `dagster.yml` and in `DW-AD23-2`, so DW-C1-1's bring-up does not silently void admission
   by reaching for a real executor.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas kedro-test` -- expected: all tests pass, including
  the new `tests/test_admission.py`. Baseline before this story is **803 passed / 19
  skipped** (Story I4/10.5 final); zero regressions, and the new file adds the
  two-process gate. Use `--frozen`: this story edits the member `pixi.toml`, so a
  non-frozen invocation will re-solve and rebuild the source package. Confirm the baseline
  count by running this ONCE before writing any code.
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` -- expected: still 47/47 green
  (no `catalog.yml` changes in this story).
- `pixi run --frozen -e pyforge-atlas dagster-dryrun` -- expected: still green. This story
  edits `orchestration/definitions.py` (docstring only) and adds a hook that
  `KedroProjectTranslator` will deep-copy at `to_dagster()` time, so this gate is the
  deepcopy-safety proof on the Dagster plane.
- `pixi run --frozen -e pyforge-atlas python -c "import pyforge.atlas.admission"` --
  expected: clean import, proving the module is importable from a bare interpreter (the
  two-process gate depends on it).

**Manual checks (if no CLI):**
- After the manifest edit, confirm `filelock` still resolves at `>=3.32.0` and that no other
  declared dependency was downgraded or dropped (`pixi list -e pyforge-atlas | grep -E
  'filelock|dagster|ibis'`).
- Grep the seven doc/spec targets for the retraction strings (`NOT cross-run admission`,
  `Run admission is NOT implemented`, `~~run admission serializes`, `Dagster-owned`) and
  confirm zero surviving hits outside the historical/append-only files
  (`sprint-change-proposal-2026-07-27.md`, `*.memlog.md`, `reviews/`), which are records of
  what was believed at the time and must NOT be rewritten.



## Auto Run Result

Status: `done` (review pass 4 — follow-up review; 0 intent_gap, 0 bad_spec, no loopback).

**Change under review.** Story 10.6 makes AD-23's "a dataset has one writing run at a time"
real: `pyforge.atlas.admission` takes one `filelock` OS file lock per dataset in
`pipeline.all_outputs()`, in sorted order, from a `RunAdmissionHooks` registered once in
`settings.HOOKS`, and releases in both `after_pipeline_run` and `on_pipeline_error`.
Reject-fast by default with a typed `RunAdmissionRejected`; a bounded wait is opt-in and
enforced as ONE deadline across all locks. Pass 4 changed no design decision — it repaired
seven behaviour-level defects on the acquire/release paths and removed two more vacuous
tests.

**Files changed this pass** (5; nothing else in the working tree):

- `src/pyforge/atlas/admission.py` — hook signatures narrowed to `(run_params, pipeline)` on
  all three hooks; `release()` unlinks before dropping the flock and restores the record on a
  failed release; `_write_holder` is atomic; `_lock_names` refuses unsafe lock identities;
  `default_lock_root` reads the env before resolving the project root; `_release_for` guards
  both `all_outputs()` and the no-pipeline ambiguity; a rejection is logged; four boundary
  corrections in the module docstring.
- `tests/test_admission.py` — 13 new tests (98 total in the file, from 85); the dagster.yml
  and deadline-expiry tests rewritten from vacuous to mutation-verified; direct hook call
  sites updated to the narrowed signatures; three stale docstrings corrected.
- `.../ARCHITECTURE-SPINE.md` + `.../spec-pyforge-atlas/SPEC.md` — AD-23's boundary list gains
  the non-`Exception` runner-exit window and the lock-store-deletion hazard ("Three boundaries
  stand" → four).
- `.../deferred-work-ledger.md` — `DW-AD23-2`'s "Two coupled residuals" corrected to four and
  its title de-scoped from Dagster-only; residual (3) sharpened; `DW-AD23-1`'s gate evidence
  re-stamped from the re-run.

**Review findings.** 18 patches applied (7 medium, 11 low), 1 deferred, 5 rejected, 0
bad_spec, 0 intent_gap. Full detail in `## Review Triage Log` § *Review pass 4*.

**Verification** (all re-run against this tree, not transcribed):

- `pixi run --frozen -e pyforge-atlas kedro-test` → **901 passed / 19 skipped** (pass 3: 888/19;
  story baseline 803/19). `tests/test_admission.py` alone: **98 passed**.
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` → **47 passed**.
- `pixi run --frozen -e pyforge-atlas dagster-dryrun` → **58 passed**.
- `pixi run --frozen -e pyforge-atlas python -c "import pyforge.atlas.admission"` → clean.
- **Mutation checks, 8 of 8 RED** — release-order reversed, `write_text` restored, `wait_seconds`
  ignored, executor swapped to `multiprocess`, no-pipeline LIFO pop restored, `catalog`
  re-declared, safe-name guard removed, base-before-env restored. Every new assertion bites.
- Retraction-string grep over the seven doc targets: zero surviving hits outside the
  historical/append-only files (the one `Dagster-owned` hit is `spec-b3:64`'s corrected
  "are **NOT** Dagster-owned").
- Empirical re-verification of each reviewer claim before acting: the `HookCallError` strand,
  the successor-record deletion, the `pipeline=None` LIFO pop, the absolute-`LOCK_ROOT`
  deadlock, the `../escaped` lock-root escape and the torn-read window were each reproduced in
  the live env; five further claims were reproduced-but-rejected as noise (see the triage log).

**Residual risks.**

1. Pass 4 reversed `release()`'s unlink/release ordering that pass 3 had itself reversed. The
   new form is strictly better (it can only ever remove OUR record, and repairs the one state
   it risks), and it is pinned by an ordering test — but this is the second time this
   five-line loop has changed, on the path that frees locks.
2. Narrowing all three hook signatures changes what kedro, kedro-dagster and every installed
   plugin must supply for admission to run. Both real callers pass a superset today (verified
   in the installed `kedro_dagster` 0.7.x), and `dagster-dryrun` is green, but the Dagster
   plane is exercised by a dry run, not by a live daemon.
3. `DW-AD23-2` remains open with four residuals; residual (4) — a failed Dagster run releasing
   nothing in-process — is still unproven either way, since no live Dagster daemon exists yet
   (`DW-C1-1`).
4. The deferred reader-writer gap (pass 3) and the deferred `observability.py` deepcopy premise
   (this pass) both remain open in `implementation-artifacts/deferred-work.md`.

### 2026-07-30 — Review pass 5 (the owed independent follow-up, triggered by pass 4's `followup_review_recommended`)

**Lens: adversarial mutation of the pass-4 surfaces.** Pass 4's flag said the problem
precisely — *"7 medium patches on the acquire/RELEASE paths … No independent reviewer has
seen any of it"* — and three prior passes had already read this file and still left two
vacuous tests behind. So this pass did not re-read for opinions; it asked the suite to
prove it constrains each patched surface, by breaking that surface and requiring a failure.

**Method.** Eight mutants injected one at a time into `admission.py`, each reverting a
specific pass-4 decision, with `tests/test_admission.py` (98 tests) as the oracle and the
file restored from a pristine copy between runs.

| # | Surface (pass-4 change) | Mutation | Result |
|---|---|---|---|
| M1 | `_write_holder` became atomic | revert to `write_text` (no temp + `os.replace`) | **caught** |
| M2 | `release()` unlink/release order (reversed a 2nd time) | back to release-then-unlink | **caught** |
| M3 | `release()` re-writes the record when release fails | drop the repair | **caught** |
| M4 | `release()` pads `names` for a malformed ticket | drop the padding | **SURVIVED** |
| M5 | `_release_one` never raises | let a stuck handle propagate | **caught** (2 tests) |
| M6a | `default_lock_root` env precedence | swap `DATA_ROOT` ahead of `LOCK_ROOT` | **caught** |
| M6b | `default_lock_root` strips whitespace-only env | drop `.strip()` | **caught** |
| M6c | `default_lock_root` honors an absolute override | drop the `is_absolute()` branch | **caught** |

**One finding — a third vacuity, now closed.** `release()` pads `names` with `None` when a
ticket carries fewer dataset names than locks, because `zip()` would otherwise truncate and
**leak the tail locks for the life of the process** — the unreclaimable state correctness
requirement 1 exists to prevent. Deleting that line left all 98 tests green: no test ever
constructed a malformed ticket, so neither the tail-release guarantee nor the `logger.error`
the code's own comment promises was verified. Closed by
`test_release_frees_the_tail_when_a_ticket_has_fewer_names_than_locks`, which asserts both
locks end free and the error is logged. Re-injecting M4 now fails it, so the mutation score
is **8/8**. Gates after: `kedro-test` **902 passed / 19 skipped** (was 901).

**Independent corroboration of `DW-AD23-3`.** Reading `default_lock_root` for M6 confirmed
the deferral is real and correctly characterized: the resolution chain ends in the literal
default `"data"`, so with neither env var set the store is `<project_root>/data/.locks` —
inside the tree the locks guard. The docstring argues (convincingly) for anchoring to the
project root rather than the CWD, and that argument is sound and well-tested (M6a–M6c all
caught); it is the *default value*, not the anchoring, that is hazardous. `DW-AD23-3` stays
open, unchanged, with its severity intact.

**Scope, stated honestly.** This was a mutation pass over the surfaces pass 4 changed, not a
fresh full reading of the module. It is a deliberately different lens from passes 1–4 (which
were readings), and its value is that it cannot be satisfied by a plausible-looking test — but
it does not cover code pass 4 did not touch.

**Flag cleared.** `followup_review_recommended` → `false`. The rate of new findings has
fallen the way pass 4 asked to see before converging: pass 4 produced 7 medium behavioural
patches plus 2 vacuous tests; this pass produced **0 behavioural defects and 1 vacuity**,
which is fixed rather than deferred. `DW-I5-1` (the pass this discharges) is satisfied.

## Post-closeout — `DW-AD23-3` fixed 2026-07-30

Recorded here because this spec is the deferral's `source_spec` and two paragraphs above
still say it stays open — they are the review-pass-5 record and are left as written. It no
longer does.

The default lock store is now the data tree's **sibling** `<data_root>.locks` rather than its
child `<data_root>/.locks`, so `rm -rf data/` cannot delete a lock file out from under a live
holder, and a `PYFORGE_ATLAS_LOCK_ROOT` resolving inside the data root is refused before any
lock is taken. Pass 5's separation held up exactly as it called it: the **anchoring** argument
needed no change at all — every project-anchored property it defends is untouched, and the
`_resolve_base` / read-env-before-anchor ordering is preserved so the absolute-override escape
hatch stays reachable in an installed layout. Only the default **value** moved.

What the fix does not do, stated so the boundary is not lost: unlinking a lock file still
admits a second writer, because `flock` belongs to the inode. That is unfixable by placement
and is now pinned as a characterization test rather than left in prose. Full record, including
why the store stays derived from the data root instead of pinned to the project, is in the
`DW-AD23-3` ledger entry. Gate: `kedro-test` **911 passed / 19 skipped** (was 903, the count
after 10.5's pass-5 fix — +8, exactly the new cases); `kedro-catalog-check` 47;
`dagster-dryrun` 58.
