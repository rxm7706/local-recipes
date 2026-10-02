---
title: '82.9: VCS commit text is declared egress and gate evaluate writes a redacted gate record'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '785fff8eb841d85a64b155f12a5e8b5686719fc5'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
warnings:
  - oversized
deferred:
  - summary: >-
      The gate record under-describes the evaluation it is evidence for: it carries no overall verdict or finding codes, so an unevaluable or errored evaluation writes a record indistinguishable from a clean one with no commands; it records HEAD only for a tree that may be dirty; and its scope-check verdict is gathered from the loop home while its tree revision is the repository root's.
    evidence: |-
      Verified by the Blind Hunter, Edge Case Hunter and Verification Gap layers at cli/gate.py (_write_gate_record, _run_scope_check): schemas/gate-record.json is Story 2.6's frozen shape (additionalProperties false, five required keys), a --run record carries commands [] by design, and the scope check reads _home_path(slug) while worktree_head_sha reads repo_root() (Story 82.1's anchor). Adding verdict, finding_codes or a dirty flag is a new public contract the intent never asked for.
    location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/gate-record.json
    severity: medium
  - summary: >-
      Merge-commit text still reaches git as a bare str on the non-egress VcsPort: merge_branch takes subject str and passes it to git merge -m.
    evidence: |-
      ports/vcs.py merge_branch(repo_root, branch, *, into, subject) and its adapter in adapters/vcs_git.py. The subject is rendered by core.identity.render_merge_subject from the policy template, never from session text, and the intent names exactly three commit-writing methods, so Story 82.9 leaves it; AD-34 still names commit text as egress, so it belongs on CommitPort with a Redacted subject.
    location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
    severity: low
  - summary: >-
      The governed spec, architecture spine and PRD still name VcsPort for the three moved commit methods and do not list CommitPort among the AD-34 egress ports.
    evidence: |-
      SPEC.md, ARCHITECTURE-SPINE.md (AD-34 registry text) and the PRD name VcsPort.merge_ref_resolving and VcsPort.commit_paths_onto_remote_tip; a SPEC.md is re-derived with bmad-spec, never hand-edited, so the prose fix is a spine amendment plus a re-derive, not part of this code story.
    location: _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
    severity: low
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
- `P/cli/deploy.py:2115` -- `land-story`'s in-process gate re-run, `evaluate_gate(gate_args, process=process, vcs=vcs, fs=fs)` with `gate_args = Namespace(project=slug, run_id=None, scope_check=True, story=str(story_key))`: the one other caller of `evaluate_gate`; F-25 names it the sole gate evidence for hand landings. `T/unit/test_deploy.py:1243` `_fake_evaluate_gate(args, *, process, vcs, fs)` stands in for it in about ten tests.
- Commit-writing call sites (14; `message` becomes `Redacted`): `cli/deploy.py:993,3976`; `cli/land.py:1255,1545`; `core/worktree_checkpoint.py:58`; `dispatch_land.py:573,636`; `dispatch_land_finalize/__main__.py:402,726`; `dispatch_land_heal.py:258`; `dispatch_supervisor/__main__.py:173,766,839,908`.
- Guards that name these methods: `T/meta/test_ad34_egress_registry_completeness.py` (guard 1 needs the registry entry; guard 2 flags `str`, `str | None`, `Any`, unannotated; containers pass), `T/meta/test_local_branch_refs_are_full_refnames.py:48-96` (`_REVISION_ARGS`, `_NAME_ARGS`, `_NOT_A_REF` name the three methods and their `ref`/`remote`/`message`), `T/meta/test_remote_refs_are_full_refnames.py`, `T/meta/test_ad11_write_boundary.py:150`.
- Fakes defining the three methods (take `Redacted` now): `T/unit/test_land.py`, `test_dispatch_landing.py`, `test_dispatch_supervisor_blocked_halt.py`, `test_dispatch_supervisor_main_loop.py`, `test_deploy.py`, `test_init.py`, `test_dispatch_land_finalize.py`, `test_dispatch_land_heal.py`, `test_supervisor.py`; real-git coverage in `T/unit/test_vcs_git.py` (`:1235-1280`, `:1890-1970`, `:1993-2090`), `test_refs.py:138`, `test_local_branch_refs.py:164`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- `DW-FU-2-6-2` `:2969`, `DW-FU-2-6-4` `:2997`: close both.

## Tasks & Acceptance

**Execution:**
- `P/core/egress.py` -- add `GATE_RECORD_FILENAME = "gate-record.json"` beside `build_gate_record`; give `build_gate_record` an optional `run_id` (omitted from the dict when `None`); add `to_redacted_text(text: str) -> Redacted`, the plain-text sibling of `to_redacted` over the same `_redact_string`; register `"CommitPort": True`; rewrite the `VcsPort` registry comment -- non-egress because its reads and ref operations carry no session text -- and drop "self-evidently non-egress" -- the commit text is why a second port exists. The comment names `merge_branch`'s `subject` (rendered from the policy template, never session text) as the one commit-text parameter that stays a bare `str` on `VcsPort`, recorded `deferred`; it never claims `VcsPort` carries no commit text.
- `P/ports/commit.py` (new) -- `VcsRef` (frozen dataclass, non-empty `str` `value`, the `ForgeRef` shape) and `CommitPort` with the three methods moved verbatim from `VcsPort`: `message: Redacted`, `ref`/`remote: VcsRef`, `preflight_skip_reason: Redacted | None`; `writes` and `resolutions` stay containers (file bodies are repository content, not commit text). No parameter is `str`, `str | None`, `Any` or unannotated.
- `P/ports/vcs.py` -- delete the three methods and their prose; rewrite the docstring: `VcsPort` keeps reads and ref operations (and `push`/`fetch`, which move git objects the callers already hold), commit text goes through `CommitPort`, and `merge_branch`'s policy-rendered `subject` is the named exception that stays here (deferred); stop claiming nothing leaves the repository, and never claim `VcsPort` carries no commit text.
- `P/adapters/vcs_git.py` -- `GitVcs` implements both ports; each commit method rejects a non-`Redacted` message and a non-`VcsRef` ref with `TypeError` (type only, never the value -- the `LocalFs` rule), then unwraps `.text`/`.value`; `commit_paths_onto_remote_tip` hands its `Redacted` straight to `commit_paths`, and the local that holds a `Redacted` is not named `commit_text`.
- Every call site in the Code Map -- wrap each message and skip reason with `to_redacted_text(...)`, each ref/remote with `VcsRef(...)`; retype the committing callers' `vcs` annotation to a name that is both ports (`Protocol` composed outside `ports/`, e.g. `core/commit_vcs.py` `CommittingVcs(VcsPort, CommitPort, Protocol)`), following the chain up as far as `pixi run -e pyforge-guild lint-types` demands; do not thread a second parameter.
- `P/schemas/gate-record.json` -- additive optional `run_id` (non-empty string); `T/unit/test_egress.py` pins it both ways.
- `P/core/findings.py`, `P/core/verdict.py`, `T/unit/test_findings.py`, `T/unit/test_verdict.py` -- `MRS-GATE-017` (WARN: no gate record written, reason named), classified `Verdict.WARN`, registered; a test pins the classification.
- `P/cli/gate.py` -- `evaluate_gate(..., record: RecordPort | None = None, clock: ClockPort | None = None)`: with `--story` resolved and both ports given, after the verdict is computed build the record (`commands` from `data["commands"]`; `scope_check_verdict` = `compute_verdict` over the scope findings when the scope check ran, else `None`; `tree_revision` = `vcs.worktree_head_sha(root)`; `timestamp` from `clock.now()` as `%Y-%m-%dT%H:%M:%SZ`; `run_id` when `--run` was given), then `record.write_redacted_atomic(<dir>/GATE_RECORD_FILENAME, to_redacted(...))`. Directory: `<run_dir>/gate-records/<story slug>/` when the run resolved, else `<tier-3>/sessions/<minted session id>/gate-records/<story slug>/`, minted with `mint_run_id`; a loop home whose tier-3 path is not a directory, an unreadable tree revision, a `FsError` or a `TypeError` is one `MRS-GATE-017` WARN with `data["gate_record"] = {"written": false, ...}`. The verdict is computed before that finding is appended and never recomputed; `data["gate_record"] = {"written": true, "path": ..., "namespace": "run"|"session", "run_id": ...}` otherwise, and `_render_text` projects it. One helper in `cli/gate.py` (e.g. `_default_record_port(fs)`) returns `fs` when it is a `LocalFs` and `None` otherwise; `run_evaluate` and `land-story` both resolve `record` through it and `clock` to `SystemClock()`, so an injected fake `fs` writes nothing and no caller spells the check twice.
- `P/cli/deploy.py` -- `land-story`'s in-process re-run (`:2115`) passes `record` and `clock` resolved the same way, with `run_id=None` still in `gate_args` (a `--run` would route the fold branch), so its record is a run-less session record. The landing's own verdict and exit code never read the record: `data["gate_record"]` carries the outcome, and `MRS-GATE-017` is not extended into `land-story`'s own `findings`. `T/unit/test_deploy.py`'s `_fake_evaluate_gate` accepts the two new keyword arguments, and one `land-story` test proves a provisioned loop home gets the record under `sessions/` while an unprovisioned one leaves the landing's verdict and exit code unchanged.
- `T/unit/test_gate_record.py` -- the recorded `scope_check_verdict` is pinned beyond the clean case: a hard-mode scope violation (a changed file outside `epic_surfaces`) records `scope-violation`, a scope check that fails with `MRS-GATE-009` records `unevaluable`, a check skipped with no finding records `None`, and the existing clean case asserts `== "clean"`, not `in {"clean", "warn"}`. One test drives `marshal gate evaluate --story` through `run_evaluate` (or `main([...])`) with a real `LocalFs`, a loop home under `tmp_path` and a fake process and VCS, and reads the record back from disk, so the wiring in `run_evaluate` is observed at the command, not only at `evaluate_gate`.
- `T/unit/conftest.py` (or the gate test modules that call `run_evaluate`/`evaluate_gate` with a default `LocalFs`) -- an autouse fixture pins `BMAD_LOOP_HOME_ROOT` (`ENV_LOOP_HOME_ROOT`) to a directory under `tmp_path`, so no test can write under the real `~/.bmad-loops`; a test double without `worktree_head_sha` then never reaches `_write_gate_record`.
- `T/meta/test_gate_record_write_path.py` (new) -- AST scan over the package: no module other than `core/egress.py` spells `"gate-record.json"`; any call that passes `GATE_RECORD_FILENAME` (or a name bound from it) to a writer other than `write_redacted_atomic` fails; a synthetic `FsPort.write_text_atomic(dir / GATE_RECORD_FILENAME, ...)` source is proven to fail, and the real tree to pass. The writer set names every `FsPort` write that takes a path -- `write_text_atomic`, `append_line`, `open_append`, `append_held`, `copy_file`, `repoint_symlink_atomic` -- and the `os`/`pathlib` link and symlink calls (`symlink`, `symlink_to`, `link`, `hardlink_to`), and a second synthetic source (`fs.append_line(dir / GATE_RECORD_FILENAME, ...)`) is proven to fail.
- `T/meta/test_local_branch_refs_are_full_refnames.py`, `test_remote_refs_are_full_refnames.py`, `test_ad11_write_boundary.py` and the fakes in `T/unit/` -- the scanners unwrap `VcsRef(<expr>)` to `<expr>` and read the commit methods from `CommitPort`; fakes accept `Redacted`, and assertions read `.text`.
- `T/unit/test_vcs_git.py`, `T/unit/test_gate.py` (or the existing gate test module) -- real-git proof that a `ghp_`-shaped token in a message is stored as `***REDACTED***`; a bare `str` message raises `TypeError` for each of the three methods; the gate record in a run directory, in `sessions/` (with and without `run_id`), the no-loop-home WARN with the verdict and exit code unchanged, and the record validating against `schemas/gate-record.json`.
- `P/core/findings.py`, `P/core/verdict.py`, `P/cli/checkpoint.py`, `T/unit/test_checkpoint_cli.py` -- `cli/checkpoint.py` is touched by the `vcs` retyping and builds `MRS-CHK-001/002/003` that Story 34.2 never registered, so every failure path of `marshal factory checkpoint` raised `UnregisteredFindingCodeError`: register the three as `Verdict.ERROR` and cover each branch of the command so the touched-module coverage floor holds.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- `DW-FU-2-6-2` and `DW-FU-2-6-4` to `status: closed` with `resolved:` naming Story 82.9; the `DW-FU-2-6-4` line names `merge_branch`'s `subject` as the one commit-text parameter still a bare `str` on `VcsPort`, carried as a deferral.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and each co-governor `spec-surface` names -- append the surface-reconcile entry naming every governed path changed (`python _bmad/scripts/memlog.py append ...`); never `--write-baseline`.

**Acceptance Criteria:**
- Given the egress registry, when the AD-34 meta-test runs, then `CommitPort` is classified egress, no method of it accepts a bare `str`, and `VcsPort` still classifies non-egress.
- Given each of the three commit methods called with a bare `str` message, when it runs, then it raises `TypeError` and no commit is made.
- Given a commit message holding a `ghp_`-shaped token, when `to_redacted_text` wraps it and `GitVcs` commits, then `git log` shows `***REDACTED***` and no token.
- Given `gate evaluate --story <key> --run <id>` with a resolvable run, when it runs, then `<run_dir>/gate-records/<slug>/gate-record.json` validates against the schema and `data["gate_record"]["path"]` names it.
- Given `--story` and no `--run` with a provisioned loop home, when it runs, then the record lands under `<tier-3>/sessions/`; given `--run` that does not resolve, then it lands there with `run_id` set.
- Given no loop home, when it runs, then exactly one `MRS-GATE-017` WARN is in the envelope and the verdict and exit code equal those of the same run with the record port absent.
- Given `marshal deploy land-story`'s in-process gate re-run with a provisioned loop home, when it runs, then a session-namespace record for that story is written and `data["gate_record"]` names it; given no loop home, then the landing's verdict and exit code equal those of the same run with the record port absent.
- Given a call site writing `GATE_RECORD_FILENAME` through any `FsPort` writer (`write_text_atomic`, `append_line`, ...), when the meta-test runs, then it fails; given either fix reverted, its new test fails.

## Spec Change Log

### 2026-10-02 -- review loopback 1 (bad_spec)

- **Triggering finding:** the Intent Alignment layer found that `evaluate_gate` writes nothing by default and that `marshal deploy land-story`, its only other caller, writes no record; the plan had deferred that wiring on its own scope line. The intent names `evaluate_gate` and F-25, which exists for the hand-landing re-run, and nothing in the intent excludes `land-story`, so the plan drew the line where the intent did not.
- **Amended (outside the intent-contract):** the Tasks wire `land-story` through one shared record-port helper in `cli/gate.py` and keep its record out of its own verdict; the plan-era `deferred:` item about `land-story` is removed (it is now implemented) and three review deferrals replace it; the Code Map counts 14 call sites and lists `cli/deploy.py:2115`; the Tasks fold in the verified patch findings (scope-verdict tests and a command-level test, a wider writer set in the write-path meta-test, test isolation from the real loop home, the `VcsPort` wording and the `commit_text` rename, and the `MRS-CHK-001/002/003` registration and its tests); a `land-story` acceptance criterion is added.
- **Known-bad state avoided:** a gate record that exists only when `marshal gate evaluate` is run by hand, leaving the hand-landing evidence F-25 was written for unrecorded; a meta-test that lets `fs.append_line(dir / GATE_RECORD_FILENAME, ...)` bypass the redacting writer; tests that can write into the operator's real `~/.bmad-loops`.
- **KEEP (re-derive these as the first attempt had them):** `CommitPort` and `VcsRef` in `ports/commit.py`, classified `True`, with the three methods moved verbatim; `to_redacted_text` over the same `_redact_string`; `GitVcs` serving both ports with type-only `TypeError` guards; `CommittingVcs(VcsPort, CommitPort, Protocol)` in `core/commit_vcs.py`, outside `ports/`; `GATE_RECORD_FILENAME` and the optional `run_id` in `build_gate_record` and the schema; `evaluate_gate(..., record=None, clock=None)` with the `<run_dir>/gate-records/<story slug>/` and `<tier-3>/sessions/<id>/gate-records/<story slug>/` destinations; `MRS-GATE-017` as a WARN appended after the verdict is computed and never recomputed; the registry, local-branch-refs and remote-refs meta-test updates, the `test_commit_text_is_redacted_at_every_call_site.py` scan, the real-git redaction and `TypeError` tests, and the mutation checks (including the clean-gate test that catches a verdict recomputed after the record write). A reference derivation is saved at `_bmad-output/projects/pyforge-marshal/implementation-artifacts/82-9-attempt-1.patch` (Tier 3, untracked; the diff of the first attempt against the baseline, code and planning edits both): read it and reuse what is correct instead of re-inventing it.
- **Correction, same loopback (found by the re-derivation):** the amended Tasks said a scope check failing with `MRS-GATE-009` records `error`. `MRS-GATE-009` classifies `Verdict.UNEVALUABLE` (`core/verdict.py`), and the Tasks' own rule is `compute_verdict` over the scope findings, so the record carries `unevaluable`; the Tasks now say so. The earlier line stands as written above, as the log is append-only.

## Design Notes

- **Plain-text redaction.** `to_redacted` is Mapping-only and emits JSON, so a commit message cannot go through it unchanged. `to_redacted_text` lives in `core/egress.py`, calls the same `_redact_string`, and is the only text path: still one redactor, and `_TOKEN_SHAPE_PATTERNS` stays private. The `Redacted(f"...")` literals in `dispatch_land.py` (`_dispatch_pr_title`/`_dispatch_pr_body`) wrap slugs and keys, not session text, and are out of this story.
- **Why callers keep one `vcs`.** `GitVcs` serves both ports, as `LocalFs` serves `FsPort` and `RecordPort`, but a second parameter would reach about 25 signatures and every test that passes a fake positionally. The composed `Protocol` lives outside `ports/` on purpose: the AD-34 registry scans `ports/` and a composed class there would need an entry and would hide `VcsPort`'s `str` parameters behind an imported base.
- **Record destination and clobber.** One file name, one directory per story, so two stories evaluated in one run never overwrite each other and the record stays "retrievable per story" (FR-25). With `--run`, `data["commands"]` is `[]` (that branch folds a journal and runs nothing), so a run-scoped record carries `commands: []`; it is still the evidence the evaluation produced. Re-evaluating one story in one run overwrites that story's record: the latest evaluation is the record "retrievable per story".
- **`evaluate_gate` is the one writer.** The intent names `evaluate_gate`, and `land-story` is its only other caller, so both callers wire the ports through one helper; a record written for a hand landing is the F-25 evidence the spine says is otherwise missing. `land-story` stays run-less (`run_id=None`), so no `--run` fold is triggered.
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

### 2026-10-02 — Review pass
- verdicts: 39 findings — high 0, medium 11, low 22, false 6, maybe-false 0
- findings:
  - `[low]` `[defer]` Blind Hunter: `VcsPort.merge_branch(..., subject: str)` still passes a bare `str` to `git merge -m` while the new docs say `VcsPort` carries only reads and ref operations — real, but pre-existing and outside the three methods the intent names; the subject is policy-rendered, never session text. Deferred (merge_branch entry); the amended Tasks make the docstring, registry comment and `DW-FU-2-6-4` resolved line name it as the exception.
  - `[medium]` `[defer]` Blind Hunter: the gate record carries no overall verdict or finding codes, so an unevaluable evaluation looks like a clean one with no commands — real; the record's shape is Story 2.6's frozen schema and the intent fixes its contents, so adding fields is a new contract. Deferred (gate-record entry).
  - `[medium]` `[defer]` Blind Hunter: `tree_revision` is `worktree_head_sha` only, for a tree that may be dirty — real; the intent names exactly that fact. Deferred (gate-record entry).
  - `[low]` `[reject]` Blind Hunter: stdout/stderr are stored unbounded and every run-less evaluation mints a `sessions/<id>/` directory that nothing prunes — typical verify output is kilobytes, Tier 3 is local and untracked, `runs/` has no retention policy either, and a cap would silently truncate evidence; the fix is a new policy, not a correction.
  - `[false]` `[reject]` Blind Hunter: `DW-FU-2-6-2` closed too early — the intent's Always clause orders both rows closed when the story lands, and the loopback now also wires the `land-story` caller.
  - `[low]` `[reject]` Blind Hunter: production behaviour gated on `isinstance(fs, LocalFs)` — the production path (`main` passing no `fs`) always gets `LocalFs`; the check exists to keep injected test doubles hermetic, and the amended Tasks move it into one shared helper.
  - `[medium]` `[patch]` Blind Hunter: about 35 existing `run_evaluate` tests use a default `LocalFs` and most do not pin `BMAD_LOOP_HOME_ROOT`, so a provisioned real `~/.bmad-loops/<slug>` would receive records and a double lacking `worktree_head_sha` would raise `AttributeError` — verified (`test_cli.py` pins it in three tests); folded into the amended Tasks (autouse fixture), the code is re-derived.
  - `[low]` `[reject]` Blind Hunter: the broad `except (OSError, TypeError, ValueError)` reports only the type name — the intent says a failed write is one WARN with the verdict standing, and the type-only reason is deliberate so no record content reaches a message; a writer regression still shows as a WARN on every run.
  - `[false]` `[reject]` Blind Hunter: `to_redacted_text` is the shape half only and the bound is unstated — `to_redacted_text`'s own docstring says it calls the shape redactor, `Redacted`'s says it is "a type boundary, not a mechanism", and the key-name half has no meaning for free text with no keys.
  - `[low]` `[reject]` Blind Hunter: `VcsRef` validates nothing, so a `-`-prefixed remote could read as an option — it follows the `ForgeRef` precedent, every caller passes a constant or a policy branch name, and the same unvalidated `str` was the parameter type before; a guard no caller can trip.
  - `[low]` `[reject]` Blind Hunter: the Code Map says 15 call sites and lists 14, and the meta-test asserts `>= 14` — the count was a planning miscount; the fix edits the spec's own count, which this loopback corrects anyway.
  - `[false]` `[reject]` Blind Hunter: the Spec Change Log is empty — it is populated by a `bad_spec` loopback, and this one just wrote its entry.
  - `[false]` `[reject]` Blind Hunter: the `MRS-CHK-001/002/003` fix has no DW row or Story note — the defect is fixed in this diff (healed tissue), so a deferred row would record nothing open; the memlog names it and the amended Tasks list it.
  - `[low]` `[defer]` Blind Hunter: the governed `SPEC.md`, the architecture spine and the PRD still name `VcsPort` for the moved methods — real, but the fix is a spine amendment plus a `bmad-spec` re-derive (a `SPEC.md` is never hand-edited), not part of this code story. Deferred (governed-docs entry).
  - `[low]` `[reject]` Blind Hunter: a naive `clock.now()` is stamped `Z` unconverted — `ClockPort.now` is documented timezone-aware UTC and only a test double breaks it.
  - `[low]` `[reject]` Blind Hunter: `cli/gate.py` imports three private helpers from `cli/spin.py` and the session id is random — `_run_dir` was already imported from `cli/spin.py` the same way, and the tests pin the prefix.
  - `[low]` `[reject]` Blind Hunter: `_unwrap_vcs_ref` handles only the positional `VcsRef(<expr>)` — a test-scan helper no caller or test spells with `value=`.
  - `[low]` `[patch]` Blind Hunter: `commit_text` holds a `Redacted` in `commit_paths_onto_remote_tip` — misleading beside the `.text` unwraps; the amended Tasks name the rename, folded into the re-derivation.
  - `[false]` `[reject]` Edge Case Hunter: `_home_path`/`mint_run_id` can raise outside any `try`, replacing the exit code with a traceback — `_home_path(project_slug)` is already called unguarded on the same `--story` path by `_gather_review_depth` (`cli/gate.py:714`) before any record work, `fs.is_dir` is guarded, and `mint_run_id` cannot fail for a slug already validated.
  - `[low]` `[reject]` Edge Case Hunter: a `--run ../../x` value now becomes a write target — the argument is the operator's own, the traversal on read is Story 2.3's, and a write needs a directory that already holds a readable `journal.jsonl`.
  - `[medium]` `[defer]` Edge Case Hunter: a record written for an unevaluable or errored evaluation is indistinguishable from a clean one — same root cause as the verdict-less record above; deferred with it.
  - `[medium]` `[defer]` Edge Case Hunter: `tree_revision` is read after the commands ran and from HEAD only — same root cause as the HEAD-only finding above; deferred with it.
  - `[low]` `[defer]` Edge Case Hunter: the scope verdict is gathered from the loop home while the commands and revision are the repository root's — the gate's repository anchor is Story 82.1's surface, which the intent forbids changing; deferred with the gate-record entry.
  - `[low]` `[reject]` Edge Case Hunter: re-evaluating one story in one run overwrites its record — latest evaluation per story per run is the "retrievable per story" semantic (Design Notes); a per-evaluation path would change the layout the ACs name.
  - `[low]` `[reject]` Edge Case Hunter: stdout/stderr unbounded — same as the Blind Hunter row above.
  - `[low]` `[reject]` Edge Case Hunter: a naive clock datetime is stamped `Z` — same as the Blind Hunter row above.
  - `[false]` `[reject]` Edge Case Hunter: the `MRS-GATE-017` WARN appended after the verdict leaves a `clean` envelope carrying a warning — the intent's own AC is "one WARN says no record was written and the verdict and exit code are unchanged", and the AD-39 consistency meta-test passes.
  - `[low]` `[defer]` Edge Case Hunter: `merge_branch`'s bare-`str` subject on `VcsPort` — same as the first row; deferred with it.
  - `[medium]` `[patch]` Edge Case Hunter: the write-path meta-test's writer set (`write*` plus a fixed list) misses `FsPort.append_line`, `open_append`, `append_held`, `repoint_symlink_atomic` and the link calls, so `fs.append_line(dir / GATE_RECORD_FILENAME, ...)` passes the guard that closes DW-FU-2-6-4 — verified against `_WRITER_NAMES`; folded into the amended Tasks (wider set, second synthetic source).
  - `[medium]` `[patch]` Verification Gap: the recorded `scope_check_verdict` is pinned only for the clean case, so a constant `"clean"` passes every test (pre-verified by that layer) — folded into the amended Tasks (violation, error and skipped cases, an exact `== "clean"`).
  - `[medium]` `[patch]` Verification Gap (other): the same test-isolation hazard as above — about 20 `--story` tests in `test_cli.py` can write into a real loop home; same fix.
  - `[low]` `[reject]` Verification Gap (other): the `--run` record is pinned as `commands: []` — the Design Notes state that branch runs no command; the test records the designed behaviour.
  - `[medium]` `[bad_spec]` Intent Alignment: `evaluate_gate` writes nothing by default and its only other caller, `marshal deploy land-story`'s in-process re-run, writes no record, so the F-25 hand-landing evidence stays unrecorded; the plan deferred it, but the intent names `evaluate_gate` and F-25 and does not exclude the caller — the spec drew the line where the intent did not. Amendment: the Tasks wire `land-story` through a shared helper and add an acceptance criterion; the plan-era deferral is removed.
  - `[medium]` `[patch]` Intent Alignment: no new test goes through `run_evaluate`/`main` to a record on disk; the tests call `evaluate_gate` with explicit ports, so the `run_evaluate` wiring is observed only through the two no-loop-home expectations — folded into the amended Tasks (one command-level test with a real `LocalFs`).
  - `[low]` `[reject]` Intent Alignment: the record lands in `<run_dir>/gate-records/<slug>/`, not directly "in that run's directory", and a run-scoped record has no commands — a subdirectory is in that run's directory, and the empty commands are the Design Notes' stated behaviour.
  - `[low]` `[reject]` Intent Alignment: commit-text coverage is an AST scan of call sites and `Redacted(text=raw)` stays a public constructor — `Redacted` is documented as a type boundary, not a mechanism; the scan covers every call-expression shape the callers use.
  - `[medium]` `[patch]` Intent Alignment: the write-path meta-test is a name-based source scan and proves nothing about the payload — same root cause as the writer-set finding above; one fix covers both.
  - `[low]` `[reject]` Intent Alignment: the half of F-25 that makes a run's fold include run-bound session records is absent — the intent's Approach scopes the write path and `run_id` on the record; the fold is a journal feature it never asks for, and `journal.py`'s docstring now says so.
  - `[low]` `[reject]` Intent Alignment: changes outside the intent's surfaces (`MRS-CHK-001/002/003`, `test_checkpoint_cli.py`) — `cli/checkpoint.py` is touched by the `vcs` retyping and its codes were unregistered, a broken window in code the diff touches; kept and written into the amended Tasks.

### 2026-10-02 — Review pass 2 (after loopback 1)
- verdicts: 36 findings — high 0, medium 3, low 30, false 3, maybe-false 0
- findings:
  - `[medium]` `[defer]` `carried` Blind Hunter: `tree_revision` names the repository root's HEAD only, while the scope verdict reads the loop home, and the evaluated tree may be dirty — same claim and location as pass 1's HEAD-only and root-versus-home rows; the deferral stands (gate-record entry, `DW-marshal-82-9`); the anchor is Story 82.1's surface, which the intent forbids changing.
  - `[medium]` `[defer]` `carried` Blind Hunter: the record carries no overall verdict or finding codes, so an errored evaluation looks like a vacuous pass — carried from pass 1; the reviewer notes the story adds `run_id` to the same frozen schema, but `run_id` is named by the intent ("carrying `run_id` when bound") while a verdict is not.
  - `[low]` `[reject]` Blind Hunter: a hand landing's records are never bound to a run and `sessions/` has no fold, so they are write-only; the landing's journal entry does not name the record path — the fold half of F-25 is a journal feature the intent's Approach never asks for (pass 1 row, `carried`); the landing reports the path in `data["gate_record"]`, and a journal field for it is new surface beyond the intent.
  - `[false]` `[reject]` `carried` Blind Hunter: the envelope contradicts itself, `verdict: clean` beside a WARN finding — the intent's own AC is "one WARN says no record was written and the verdict and exit code are unchanged", and the AD-39 consistency test passes.
  - `[low]` `[reject]` `carried` Blind Hunter: several paths drop the record without a WARN (a non-`LocalFs` `fs`, a missing port, an unresolvable `--story`) — injected doubles must stay hermetic, and the production path always supplies the ports; `_default_record_port` is now the one place the type check is spelled.
  - `[low]` `[reject]` Blind Hunter: `land-story` filters `MRS-GATE-017` out of its own findings, so a landing whose evidence write failed exits clean — deliberate and written into the spec: the outcome is in `data["gate_record"]` and a text line, and the intent forbids a record write from touching the exit code.
  - `[low]` `[reject]` `carried` Blind Hunter: the two namespaces are unbounded, re-evaluation replaces a run's record, and stdout and stderr are stored whole — pass 1 rows; a retention or size policy is new, and the Design Notes state the per-run replace as the "retrievable per story" semantic.
  - `[low]` `[reject]` `carried` Blind Hunter: `VcsRef` validates only non-emptiness, so a `-`-prefixed value could reach `git push` as an option — the `ForgeRef` precedent, and every caller passes a constant or a policy branch name.
  - `[low]` `[reject]` `carried` Blind Hunter: the meta-tests are name-based (`Redacted(text=raw)` passes the write-path scan), `writes` and `resolutions` sit outside the guard, the census is a `>= 14` floor — `Redacted` is documented as a type boundary, the spec keeps file bodies as containers, and the sibling scan rejects a hand-wrapped `Redacted` at every commit call site.
  - `[low]` `[defer]` `carried` Blind Hunter: `DW-FU-2-6-4` is closed while `merge_branch`'s bare-`str` subject remains on `VcsPort` — carried; the intent names three methods and orders both rows closed, and the residual is a named deferral (`DW-marshal-82-9-2`).
  - `[low]` `[reject]` `carried` Blind Hunter: the naive-datetime branch in `_write_gate_record` stamps `Z` on a local time and is untested — `ClockPort.now` is documented timezone-aware UTC; the branch only converts an aware value.
  - `[low]` `[reject]` Blind Hunter: no test shows a failing verify command (`gate-failed`) producing a record — the record builder does not branch on a command's exit code, and `test_egress.py` already ties every `classify_outcome` shape to `build_gate_record` and the schema.
  - `[low]` `[patch]` Blind Hunter: `test_dispatch_supervisor_main_loop.py`'s `FakeVcs.commit_paths_onto_remote_tip` still annotates `preflight_skip_reason: str | None` while its body reads `.text` — real and cosmetic; fixed (see the Verification Gap row, same root cause).
  - `[low]` `[reject]` Blind Hunter: `tests/unit/conftest.py` uses `ENV_LOOP_HOME_ROOT` while `test_deploy._land_world` and `test_gate_record.world` spell `"BMAD_LOOP_HOME_ROOT"` — both name the same variable, the value is pinned by the test that sets it, and the spelling in older test modules predates this story.
  - `[low]` `[reject]` Blind Hunter: `gate evaluate --story` now writes under the loop home or the run directory with no opt-out flag — the intent's Approach says it writes; an opt-out flag is new public surface.
  - `[low]` `[reject]` Blind Hunter: the new data key, `MRS-GATE-017` and the side effect appear in no CLI reference or skill — checked: no document or skill names `MRS-GATE-015`/`016` or the gate `data` keys, so there is nothing to keep in step; the `--story` help string carries the behaviour.
  - `[low]` `[patch]` Blind Hunter: the schema's root `description` lists what a record holds but not the optional `run_id` — real; fixed (one clause added to that description, nothing else in the schema).
  - `[low]` `[reject]` Edge Case Hunter: the loop home's Tier-3 path is only checked with `fs.is_dir`, so a real directory there (not the canonical backlink) would receive a record that `init` later refuses — a real non-empty directory there is already the `MRS-INIT-005` refusal state, and `cli/spin.py` writes run journals beneath the same path the same way.
  - `[false]` `[reject]` `carried` Edge Case Hunter: `clock.now`, `_home_path`, `mint_run_id` or `worktree_head_sha` raising outside the caught types escapes with a traceback — `_home_path` is already called unguarded on this path by `_gather_review_depth`, `ClockPort.now` never raises, `mint_run_id` cannot fail for a slug already validated, and `GitVcs` wraps git failures in `VcsCommandError`.
  - `[low]` `[reject]` `carried` Edge Case Hunter: a `--run` value with path separators or `..` is joined into the run directory, which is now a write destination — the value is the operator's own command-line argument and the read-side traversal is Story 2.3's; a write needs a directory that already holds a readable `journal.jsonl`.
  - `[medium]` `[defer]` `carried` Edge Case Hunter: the tree revision is read after the verify commands and from HEAD only — same root cause as the first row; deferred with it.
  - `[low]` `[reject]` `carried` Edge Case Hunter: a hand-wrapped `Redacted(text=raw)` passes the write-path meta-test, so the record can reach disk unredacted — `Redacted` is a type boundary by design; the intent's mechanism is a scan for the writer, which a test proves for every `FsPort` writer and the link calls.
  - `[low]` `[reject]` Edge Case Hunter: the write-path scan tracks single string constants and same-module bindings, so `"gate-" + "record.json"` or a path passed through a parameter evades it — a deliberate evasion rather than an accidental regression, and every real call site uses `GATE_RECORD_FILENAME`; the scan's bound is the usual one for an AST guard in this suite.
  - `[low]` `[patch]` Verification Gap (other): the same stale `str | None` annotation on the supervisor main-loop fake — fixed with the Blind Hunter row above; the layer found no verification gap in the diff and ran the new and changed suites green.
  - `[low]` `[reject]` `carried` Intent Alignment: the adapter stores `.text` verbatim, so redaction exists only where a caller wraps — the intent's Approach is the type boundary plus "every caller wraps its message", which is what is built and scanned.
  - `[low]` `[reject]` `carried` Intent Alignment: the real-git redaction tests apply `to_redacted_text` themselves and only the checkpoint call site is driven end to end, the rest by the AST scan — the scan and the per-site unit fakes pin the argument shape at every site, and the mutation checks removed each wrap in turn.
  - `[low]` `[defer]` `carried` Intent Alignment: `merge_branch`'s `subject` is commit text on the non-egress port and `DW-FU-2-6-4` is `closed` — same root cause as the `DW-FU-2-6-4` row above.
  - `[false]` `[reject]` Intent Alignment: the wrapper is `to_redacted_text`, not the `to_redacted` the intent names — `to_redacted` accepts only a `Mapping` and emits JSON, so it cannot wrap a commit message; the Design Notes record the plain-text sibling over the same redactor.
  - `[low]` `[reject]` `carried` Intent Alignment: `evaluate_gate` is an inert default and the behaviour lives at its two callers, only for a real `LocalFs` — the injected-double design is stated in the spec; both callers now resolve the ports through one helper.
  - `[low]` `[reject]` `carried` Intent Alignment: an unresolvable `--story` or a non-`LocalFs` `fs` produces no `gate_record` key and no WARN — the intent's WARN is for "no destination (no loop home) or a failed write", and a record is only attempted for a resolved story.
  - `[low]` `[reject]` `carried` Intent Alignment: the unit tests call `evaluate_gate` with explicit ports, the command-level tests go through `run_evaluate` and cover only the run-less path, so the `--run` criterion is observed at `evaluate_gate` — `run_evaluate` is the command's handler after argument parsing, one test reads a record back from disk through it, and the `--run` branch shares the same `_write_gate_record`.
  - `[low]` `[reject]` `carried` Intent Alignment: a `--run` record carries `commands: []` — the Design Notes state that branch runs no command.
  - `[low]` `[reject]` `carried` Intent Alignment: the destination is nested (`gate-records/<slug>/`) and under Tier-3 rather than directly in the run directory or the home — a subdirectory is "in that run's directory", and `sessions/` lives under the same Tier-3 root as `runs/`.
  - `[low]` `[defer]` `carried` Intent Alignment: the scope verdict reads the loop home while the tree revision reads the repository root, and the diff records this itself — same root cause as the first row; deferred with it.
  - `[low]` `[reject]` Intent Alignment: the `FsPort`-bypass criterion is proven by synthetic source strings and a clean real tree, since no real violating call site exists — that is how the intent's "meta-test fails" criterion can be shown at all, and the second synthetic source covers `append_line`.
  - `[low]` `[reject]` `carried` Intent Alignment: changes beyond the intent's named surfaces (`land-story` wiring, `MRS-CHK-001/002/003`, the autouse conftest, `describe_gate_record`) — each is written into the amended Tasks as outside the intent-contract, and the `MRS-CHK` codes were a broken window in a file the diff touches.

### 2026-10-02 — Landing refused on a merge conflict with Story 82.10 (operator fix)
- PR #1744 conflicted with `main` after Story 82.10 landed in the same parallel wave (MRS-DISP-038): both stories appended `deferred-work-ledger.md` rows at the same spot, and both appended to the `spec-pyforge-core` and `spec-pyforge-marshal` memlogs. The landing heal unions only memlogs, so the ledger refused it.
  - `[medium]` `[patch]` Ledger resolved keeping both blocks: DW-marshal-82-9, -82-9-2 and -82-9-3, then DW-marshal-82-10, each with its own `severity`/`promoted`/`status` tail (git had folded the identical tails out of the hunk). Memlogs unioned; every entry from both sides kept. `cli/dispatch.py` auto-merged with 82.10's change. `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (10548 passed); pyforge-core's suite exit 0 (2164 passed); `pixi run --frozen -e pyforge-guild lint-types` exit 0.

## Auto Run Result

Status: done
Blocking condition: none

### Summary of the implemented change

Commit text is now declared egress, and `marshal gate evaluate --story` writes a redacted gate record. Two review passes ran; pass 1 sent the story back once for a `bad_spec` (the `land-story` caller was left out), and pass 2 found only two cosmetic patches.

- **Commit text (DW-FU-2-6-4).** The three commit-writing methods (`commit_paths`, `merge_ref_resolving`, `commit_paths_onto_remote_tip`) moved from `VcsPort` onto a new egress `CommitPort` (`EGRESS_PORTS["CommitPort"] = True`). The message and the preflight skip reason are `Redacted`; `ref` and `remote` are `VcsRef`. `GitVcs` serves both ports and raises `TypeError` for a bare `str` before any git call. `to_redacted_text` is the plain-text sibling of `to_redacted` over the same `_redact_string`. All 14 call sites wrap their text, and callers keep one `vcs` parameter through `CommittingVcs(VcsPort, CommitPort, Protocol)` in `core/commit_vcs.py`.
- **Gate record (DW-FU-2-6-2).** `evaluate_gate(..., record=None, clock=None)` builds the record from facts it already holds and writes it through `RecordPort.write_redacted_atomic` of `to_redacted(...)` into `<run_dir>/gate-records/<story slug>/` when `--run` resolves, else `<tier-3>/sessions/<minted id>/gate-records/<story slug>/` (with `run_id` when one was given). `data["gate_record"]` names the outcome. A record that cannot be written is one `MRS-GATE-017` WARN appended after the verdict is computed, so the verdict and exit code never move. `marshal deploy land-story`'s in-process gate re-run writes a run-less session record through the same helper (`_default_record_port`) and keeps `MRS-GATE-017` out of its own findings.
- **Write-path guard.** `GATE_RECORD_FILENAME` is spelled once, in `core/egress.py`; `tests/meta/test_gate_record_write_path.py` fails any other module that spells it and any `FsPort` writer or link call handed it.
- **Ledger.** `DW-FU-2-6-2` and `DW-FU-2-6-4` are `closed` with `resolved:` lines; three open rows (`DW-marshal-82-9`, `-2`, `-3`) carry the review deferrals.

### Files changed

Code under `src/shared/packages/pyforge-marshal/src/pyforge/marshal/`:
- `ports/commit.py` (new) -- `CommitPort` and `VcsRef`; `core/commit_vcs.py` (new) -- `CommittingVcs`; `ports/vcs.py` -- the three methods removed, docstring rewritten.
- `core/egress.py` -- `CommitPort` registered, `to_redacted_text`, `GATE_RECORD_FILENAME`, optional `run_id` in `build_gate_record`; `schemas/gate-record.json` -- optional `run_id`.
- `adapters/vcs_git.py` -- `GitVcs` implements both ports with type-only `TypeError` guards.
- `cli/gate.py` -- the record write, `_default_record_port`, `describe_gate_record`; `cli/deploy.py` -- `land-story` re-run writes a session record.
- `core/findings.py`, `core/verdict.py` -- `MRS-GATE-017` (WARN) and `MRS-CHK-001/002/003` (ERROR, Story 34.2 had built them unregistered); `cli/checkpoint.py`, `cli/land.py`, `cli/dispatch.py`, `core/worktree_checkpoint.py`, `dispatch_land.py`, `dispatch_land_finalize/__main__.py`, `dispatch_land_heal.py`, `dispatch_supervisor/__main__.py`, `supervisor/__main__.py` -- messages wrapped, `vcs` retyped; `adapters/forge_gh.py`, `core/journal.py`, `core/promotion.py`, `core/status.py` -- docstring references only.

Tests under `src/shared/packages/pyforge-marshal/tests/`: new `meta/test_commit_text_is_redacted_at_every_call_site.py`, `meta/test_gate_record_write_path.py`, `unit/test_gate_record.py`, `unit/test_checkpoint_cli.py`, `unit/conftest.py` (pins the loop-home root under `tmp_path`); updated the AD-34, local-branch-refs and AD-11 meta-tests, `test_vcs_git.py`, `test_deploy.py`, `test_egress.py`, `test_findings.py`, `test_verdict.py`, `test_cli.py` and the fakes in the other unit modules.

Planning: `deferred-work-ledger.md` (two closures, three new rows), the `.memlog.md` of `spec-pyforge-marshal` and `spec-pyforge-core` (surface-reconcile entries naming every governed path changed), and this spec.

### Review findings breakdown

- **Pass 1 (39 findings):** 1 `bad_spec` (the `land-story` caller), 7 patches, 8 deferred, 23 rejected. The `bad_spec` and the verified patches were folded into the spec, the code was reverted and re-derived.
- **Pass 2 (36 findings, 22 carried from pass 1):** 3 patch rows for 2 fixes (a stale `str | None` annotation on a test fake, reported twice, and the schema's root `description` missing `run_id`), both low and both applied; 6 deferred (all already covered by the three `deferred:` entries); 27 rejected, each with its reason in the Review Triage Log. No `high`, no `intent_gap`, no second `bad_spec`.
- **Deferred (frontmatter and ledger):** the gate record's missing verdict and finding codes, HEAD-only revision and loop-home versus repository-root mismatch; `merge_branch`'s policy-rendered `subject` still a bare `str` on `VcsPort`; the governed `SPEC.md`, spine and PRD prose that still name `VcsPort` for the moved methods.

### Follow-up review recommendation

`followup_review_recommended: false`. This pass patched 2 entries, both `low`; no `high`, and fewer than two `medium`.

### Verification performed

All exit codes read directly, never through a pipe:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 10539 passed, 1 skipped, 14 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `python scripts/spec_surface_reconcile.py` -- exit 0, no drift; no baseline stamped.
- `lint-types`, `deferred-work-check`, `story-status-check`, `spec-surface-check` (all `pyforge-guild`) -- exit 0 each, re-run after the last patch. `chain-completeness-check` and `pyforge-marshal-coverage-gate` (18 touched modules at or above 80%) were exit 0 on the re-derived tree before the two cosmetic patches.
- The implementer ran 12 mutants (a revert of each fix, plus the scope verdict, record-port wiring and filter, and call-site wrapping); all were killed.

### Residual risks

- `pr-preflight`, the full `detectors-ci` lane and the `-m slow` suites were not run; no push was made.
- The spec-surface baselines are not stamped; whoever lands this stamps scoped, after `git add`, from a clean tree.
- `pyforge-steward`'s `track.py` reads `<run_dir>/gate-record.json`, but records land at `<run_dir>/gate-records/<story slug>/gate-record.json`. It degrades to "absent"; a follow-up should point it at the new path.
- Two `-m slow` tests (`test_init_worktree.py::test_preflight_end_to_end_converges_seeds_and_acknowledges` and `test_local_recipes_empty_plan.py::test_local_recipes_adopt_dry_run_yields_empty_plan_excluding_deferred`) failed in the first derivation on a `bmad-loop` version string and a seed-symlink precondition; they look environmental but were not confirmed on a clean baseline.
- The harness auto-checkpoints the worktree, so the `wip:` history on this branch contains transient mutated states from the mutation checks; the final tree is correct.
