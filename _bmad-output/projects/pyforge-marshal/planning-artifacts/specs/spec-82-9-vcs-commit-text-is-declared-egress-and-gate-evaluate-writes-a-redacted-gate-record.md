---
title: '82.9: VCS commit text is declared egress and gate evaluate writes a redacted gate record'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: 'd016f196bf14e259ff8bd819eb3d504998f94dee'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
warnings:
  - oversized
deferred:
  - summary: "`marshal deploy land-story` re-runs the full gate in-process (`evaluate_gate`) and still writes no gate record; F-25 names that re-run as the sole evidence for hand landings. This story wires `marshal gate evaluate` only (its ACs), and `evaluate_gate` takes its record and clock ports optionally so the land-story caller can opt in."
    evidence: "`cli/deploy.py:2115` calls `evaluate_gate(gate_args, process=process, vcs=vcs, fs=fs)` with no record port; `tests/unit/test_deploy.py:1243` `_fake_evaluate_gate` pins that call shape in about ten tests."
    location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** AD-34's egress boundary and FR-25's gate evidence are both incomplete. Re-verified at HEAD a7cdb91fe4:

- `core/egress.py::EGRESS_PORTS` (`:193-209`) classifies `"VcsPort": False` on the rationale that nothing leaves the local
  repository, but AD-34 names "VCS commit and PR text" as egress. `VcsPort` now writes commit text as a bare `str`:
  `commit_paths(..., message: str)` (`ports/vcs.py:368`), `merge_ref_resolving(..., message: str)` (`:490`) and
  `commit_paths_onto_remote_tip` (`:539`). The AD-34 meta-test
  (`tests/meta/test_ad34_egress_registry_completeness.py`) checks bare-`str` parameters only on ports classified egress, so
  an unredacted credential can reach a commit message with no test failing. `LocalFs` also serves both
  `RecordPort.write_redacted_atomic` and `FsPort.write_text_atomic` on the same sink, so a gate record could be written
  unredacted in one line (DW-FU-2-6-4).
- `build_gate_record` (`core/egress.py:504`) has no caller anywhere: `marshal gate evaluate` prints its envelope and writes no
  durable record. Both blockers DW-FU-2-6-2 named are gone (`VcsPort.worktree_head_sha`, `ports/vcs.py:432`, gives the tree
  revision; Story 2.3's scope check has shipped), yet the wiring was never done. The spine places gate records "under the
  loop home's run directory" and gives run-less evaluations the AD-25 `sessions/` namespace (F-25), which
  `core/journal.py:57` records as unimplemented.

**Approach:**

- The three commit-writing methods move onto their own port classified `True` in `EGRESS_PORTS`, taking the message as
  `Redacted` and every other text parameter as a typed reference (the `ForgeRef` precedent, `ports/forge.py:63`);
  `VcsPort` keeps its read and ref operations, stays non-egress, and its docstring stops claiming nothing leaves the repo;
  `GitVcs` implements both; every caller wraps its message with `to_redacted`. The existing meta-test then covers commit
  text unchanged.
- The gate record's file name is one constant beside `build_gate_record`; a meta-test fails any call site that writes it
  through anything but `RecordPort.write_redacted_atomic`.
- `evaluate_gate`, given `--story`, builds the record from facts it already holds (the commands and exit codes, the scope
  verdict, `worktree_head_sha` of the evaluated root, a UTC timestamp) and writes it into the `--run` directory when one
  resolves, else into the project loop home's `sessions/` namespace, carrying `run_id` when bound; `data` names the
  path. No destination (no loop home) or a failed write is one WARN and the verdict stands.

Ledger key: `82-9-vcs-commit-text-is-declared-egress-and-gate-evaluate-writes-a-redacted-gate-record`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-3 (gates you can run) with Story 2.6 (FR-25; NFR-8, NFR-11; AD-34) and AD-25 (F-25,
  session-namespace gate records). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given the egress registry When the AD-34 meta-test runs Then the port carrying commit text is classified egress and none of its methods accepts a bare-`str` message
- Given a commit-writing call site handed a message containing a token-shaped credential When the commit is made Then the stored message carries the redacted form
- Given `marshal gate evaluate --story <key> --run <id>` with a resolvable run When the gate runs Then a schema-valid gate record (`schemas/gate-record.json`) with the commands, exit codes, scope verdict, tree revision and timestamp is written in that run's directory and named in `data`
- Given `gate evaluate --story <key>` with no `--run` and a provisioned loop home When the gate runs Then the record lands in the home's `sessions/` namespace
- Given no loop home When the gate runs Then one WARN says no record was written and the verdict and exit code are unchanged
- Given a call site writing the gate-record file through `FsPort` When the meta-test runs Then it fails
- Given either fix reverted When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** One redacting serializer (`core/egress.py`); no call site redacts on its own. The gate verdict never depends on
the record write. Close DW-FU-2-6-4 and DW-FU-2-6-2 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not classify `FsPort` as egress (its general writes are not records). Do not change the gate's repository
anchor (Story 82.1's surface). Do not let a gate record write change the exit-code domain.

</intent-contract>

## Code Map

Package root `P` = `src/shared/packages/pyforge-marshal/src/pyforge/marshal`; tests `T` = `src/shared/packages/pyforge-marshal/tests`. Anchors verified at HEAD `4893823a8a`.

- `P/core/egress.py` -- `EGRESS_PORTS` `:193-210` (`"VcsPort": False` `:197`); `Redacted` `:214`; `to_redacted` `:312` (Mapping-only, JSON output); `_redact_string` `:245` (the one shape redactor); `build_gate_record` `:504` (no caller, no `run_id`); the registry comment `:174-192` names `VcsPort` self-evidently non-egress.
- `P/ports/vcs.py` -- the three commit writers: `commit_paths` `:368`, `merge_ref_resolving` `:490`, `commit_paths_onto_remote_tip` `:539`; module docstring `:1-6` ("Not an egress port: nothing here ever leaves the local git repository") and the `commit_paths` prose `:77-85`; `worktree_head_sha` `:432` (tree revision).
- `P/ports/forge.py` -- `ForgeRef` `:63`: the typed-reference precedent (frozen dataclass, non-empty `value`); `create_pr(title: Redacted, body: Redacted)`. `P/ports/record.py:25` `RecordPort.write_redacted_atomic`.
- `P/adapters/vcs_git.py` -- `GitVcs` `:211`; `commit_paths` `:840`, `merge_ref_resolving` `:1185`, `commit_paths_onto_remote_tip` `:1354` (calls `self.commit_paths` `:1432`); `worktree_head_sha` `:1081`.
- `P/adapters/fs_local.py` -- `LocalFs` `:118` serves `FsPort.write_text_atomic` `:140` and `RecordPort.write_redacted_atomic` `:265` on one sink (DW-FU-2-6-4); its `TypeError` guards are the runtime precedent for the adapter's `Redacted` check.
- `P/cli/gate.py` -- `evaluate_gate` `:713` (the `--run` fold `:859-889`, `run_dir` `:868`, scope check `:1009`, verdict `:1083`), `run_evaluate` `:1087`, `_render_text` `:1135`; the `--run` branch reports `data["commands"] = []`. Helpers to reuse: `cli/init.py` `_loop_home_root` `:359`, `_home_path` `:373`; `cli/spin.py` `_run_dir` `:1008`, `_format_utc_compact` `:981`, `_random_token`; `core/journal.py` `mint_run_id` `:180`; `ports/clock.py` `ClockPort.now`; `adapters/clock_system.py`.
- `P/schemas/gate-record.json` -- `additionalProperties: false`, five required keys, no `run_id`. `T/unit/test_egress.py` pins the schema and `build_gate_record` together.
- `P/core/findings.py` `REGISTERED_CODES` (`MRS-GATE-016` at `:1947`), `P/core/verdict.py` `_CLASSIFY_TABLE` (`:1253`), `T/unit/test_findings.py` `:419`, `T/unit/test_verdict.py`: the four places a new code lands (the 82.1 landing, `6d4de8e4845`, is the template).
- Commit-writing call sites (15; `message` becomes `Redacted`): `cli/deploy.py:993,3976`; `cli/land.py:1255,1545`; `core/worktree_checkpoint.py:58`; `dispatch_land.py:573,636`; `dispatch_land_finalize/__main__.py:402,726`; `dispatch_land_heal.py:258`; `dispatch_supervisor/__main__.py:173,766,839,908`.
- Guards that name these methods: `T/meta/test_ad34_egress_registry_completeness.py` (guard 1 needs the registry entry; guard 2 flags `str`, `str | None`, `Any`, unannotated; containers pass), `T/meta/test_local_branch_refs_are_full_refnames.py:48-96` (`_REVISION_ARGS`, `_NAME_ARGS`, `_NOT_A_REF` name the three methods and their `ref`/`remote`/`message`), `T/meta/test_remote_refs_are_full_refnames.py`, `T/meta/test_ad11_write_boundary.py:150`.
- Fakes defining the three methods (take `Redacted` now): `T/unit/test_land.py`, `test_dispatch_landing.py`, `test_dispatch_supervisor_blocked_halt.py`, `test_dispatch_supervisor_main_loop.py`, `test_deploy.py`, `test_init.py`, `test_dispatch_land_finalize.py`, `test_dispatch_land_heal.py`, `test_supervisor.py`; real-git coverage in `T/unit/test_vcs_git.py` (`:1235-1280`, `:1890-1970`, `:1993-2090`), `test_refs.py:138`, `test_local_branch_refs.py:164`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- `DW-FU-2-6-2` `:2969`, `DW-FU-2-6-4` `:2997`: close both.

## Tasks & Acceptance

**Execution:**
- `P/core/egress.py` -- add `GATE_RECORD_FILENAME = "gate-record.json"` beside `build_gate_record`; give `build_gate_record` an optional `run_id` (omitted from the dict when `None`); add `to_redacted_text(text: str) -> Redacted`, the plain-text sibling of `to_redacted` over the same `_redact_string`; register `"CommitPort": True`; rewrite the `VcsPort` registry comment -- non-egress because it now carries only reads and ref operations -- and drop "self-evidently non-egress" -- the commit text is why a second port exists.
- `P/ports/commit.py` (new) -- `VcsRef` (frozen dataclass, non-empty `str` `value`, the `ForgeRef` shape) and `CommitPort` with the three methods moved verbatim from `VcsPort`: `message: Redacted`, `ref`/`remote: VcsRef`, `preflight_skip_reason: Redacted | None`; `writes` and `resolutions` stay containers (file bodies are repository content, not commit text). No parameter is `str`, `str | None`, `Any` or unannotated.
- `P/ports/vcs.py` -- delete the three methods and their prose; rewrite the docstring: `VcsPort` reads and ref operations (and `push`/`fetch`, which move git objects the callers already hold), and commit text goes through `CommitPort`; stop claiming nothing leaves the repository.
- `P/adapters/vcs_git.py` -- `GitVcs` implements both ports; each commit method rejects a non-`Redacted` message and a non-`VcsRef` ref with `TypeError` (type only, never the value -- the `LocalFs` rule), then unwraps `.text`/`.value`; `commit_paths_onto_remote_tip` hands its `Redacted` straight to `commit_paths`.
- Every call site in the Code Map -- wrap each message and skip reason with `to_redacted_text(...)`, each ref/remote with `VcsRef(...)`; retype the committing callers' `vcs` annotation to a name that is both ports (`Protocol` composed outside `ports/`, e.g. `core/commit_vcs.py` `CommittingVcs(VcsPort, CommitPort, Protocol)`), following the chain up as far as `pixi run -e pyforge-guild lint-types` demands; do not thread a second parameter.
- `P/schemas/gate-record.json` -- additive optional `run_id` (non-empty string); `T/unit/test_egress.py` pins it both ways.
- `P/core/findings.py`, `P/core/verdict.py`, `T/unit/test_findings.py`, `T/unit/test_verdict.py` -- `MRS-GATE-017` (WARN: no gate record written, reason named), classified `Verdict.WARN`, registered; a test pins the classification.
- `P/cli/gate.py` -- `evaluate_gate(..., record: RecordPort | None = None, clock: ClockPort | None = None)`: with `--story` resolved and both ports given, after the verdict is computed build the record (`commands` from `data["commands"]`; `scope_check_verdict` = `compute_verdict` over the scope findings when the scope check ran, else `None`; `tree_revision` = `vcs.worktree_head_sha(root)`; `timestamp` from `clock.now()` as `%Y-%m-%dT%H:%M:%SZ`; `run_id` when `--run` was given), then `record.write_redacted_atomic(<dir>/GATE_RECORD_FILENAME, to_redacted(...))`. Directory: `<run_dir>/gate-records/<story slug>/` when the run resolved, else `<tier-3>/sessions/<minted session id>/gate-records/<story slug>/`, minted with `mint_run_id`; a loop home whose tier-3 path is not a directory, an unreadable tree revision, a `FsError` or a `TypeError` is one `MRS-GATE-017` WARN with `data["gate_record"] = {"written": false, ...}`. The verdict is computed before that finding is appended and never recomputed; `data["gate_record"] = {"written": true, "path": ..., "namespace": "run"|"session", "run_id": ...}` otherwise, and `_render_text` projects it. `run_evaluate` resolves `record` to `fs` only when `fs` is a `LocalFs`, and `clock` to `SystemClock()`, so an injected fake `fs` writes nothing.
- `T/meta/test_gate_record_write_path.py` (new) -- AST scan over the package: no module other than `core/egress.py` spells `"gate-record.json"`; any call that passes `GATE_RECORD_FILENAME` (or a name bound from it) to a writer other than `write_redacted_atomic` fails; a synthetic `FsPort.write_text_atomic(dir / GATE_RECORD_FILENAME, ...)` source is proven to fail, and the real tree to pass.
- `T/meta/test_local_branch_refs_are_full_refnames.py`, `test_remote_refs_are_full_refnames.py`, `test_ad11_write_boundary.py` and the fakes in `T/unit/` -- the scanners unwrap `VcsRef(<expr>)` to `<expr>` and read the commit methods from `CommitPort`; fakes accept `Redacted`, and assertions read `.text`.
- `T/unit/test_vcs_git.py`, `T/unit/test_gate.py` (or the existing gate test module) -- real-git proof that a `ghp_`-shaped token in a message is stored as `***REDACTED***`; a bare `str` message raises `TypeError` for each of the three methods; the gate record in a run directory, in `sessions/` (with and without `run_id`), the no-loop-home WARN with the verdict and exit code unchanged, and the record validating against `schemas/gate-record.json`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- `DW-FU-2-6-2` and `DW-FU-2-6-4` to `status: closed` with `resolved:` naming Story 82.9.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and each co-governor `spec-surface` names -- append the surface-reconcile entry naming every governed path changed (`python _bmad/scripts/memlog.py append ...`); never `--write-baseline`.

**Acceptance Criteria:**
- Given the egress registry, when the AD-34 meta-test runs, then `CommitPort` is classified egress, no method of it accepts a bare `str`, and `VcsPort` still classifies non-egress.
- Given each of the three commit methods called with a bare `str` message, when it runs, then it raises `TypeError` and no commit is made.
- Given a commit message holding a `ghp_`-shaped token, when `to_redacted_text` wraps it and `GitVcs` commits, then `git log` shows `***REDACTED***` and no token.
- Given `gate evaluate --story <key> --run <id>` with a resolvable run, when it runs, then `<run_dir>/gate-records/<slug>/gate-record.json` validates against the schema and `data["gate_record"]["path"]` names it.
- Given `--story` and no `--run` with a provisioned loop home, when it runs, then the record lands under `<tier-3>/sessions/`; given `--run` that does not resolve, then it lands there with `run_id` set.
- Given no loop home, when it runs, then exactly one `MRS-GATE-017` WARN is in the envelope and the verdict and exit code equal those of the same run with the record port absent.
- Given a call site writing `GATE_RECORD_FILENAME` through `FsPort`, when the meta-test runs, then it fails; given either fix reverted, its new test fails.

## Spec Change Log

## Design Notes

- **Plain-text redaction.** `to_redacted` is Mapping-only and emits JSON, so a commit message cannot go through it unchanged. `to_redacted_text` lives in `core/egress.py`, calls the same `_redact_string`, and is the only text path: still one redactor, and `_TOKEN_SHAPE_PATTERNS` stays private. The `Redacted(f"...")` literals in `dispatch_land.py` (`_dispatch_pr_title`/`_dispatch_pr_body`) wrap slugs and keys, not session text, and are out of this story.
- **Why callers keep one `vcs`.** `GitVcs` serves both ports, as `LocalFs` serves `FsPort` and `RecordPort`, but a second parameter would reach about 25 signatures and every test that passes a fake positionally. The composed `Protocol` lives outside `ports/` on purpose: the AD-34 registry scans `ports/` and a composed class there would need an entry and would hide `VcsPort`'s `str` parameters behind an imported base.
- **Record destination and clobber.** One file name, one directory per story, so two stories evaluated in one run never overwrite each other and the record stays "retrievable per story" (FR-25). With `--run`, `data["commands"]` is `[]` (that branch folds a journal and runs nothing), so a run-scoped record carries `commands: []`; it is still the evidence the evaluation produced.
- **Verdict independence.** `MRS-GATE-017` classifies `warn`, but `evaluate_gate` appends it after `compute_verdict` ran over the gate's own findings; a clean gate with a failed record write stays `clean`, exit 0. If the AD-39 consistency test objects, the test is narrowed to name this one finding -- the verdict is not recomputed.

## Binding

Parent: Story 2.6, `spec-pyforge-marshal` CAP-3; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-9-vcs-commit-text-is-declared-egress-and-gate-evaluate-writes-a-redacted-gate-record`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-2-6-4, DW-FU-2-6-2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
