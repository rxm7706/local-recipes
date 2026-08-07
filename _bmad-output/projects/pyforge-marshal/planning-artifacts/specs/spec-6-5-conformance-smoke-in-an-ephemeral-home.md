---
title: 'Conformance smoke in an ephemeral home'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-4-adapter-probe-with-a-machine-scoped-record.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-1-profile-driven-adapter-selection-project-scoped.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.4 (merged)'
---

<intent-contract>

## Intent

**Problem:** Stories 6.1-6.4 resolve/select/project/verify/probe an adapter's
DECLARATIVE support, but nothing has ever driven a REAL story end to end
through a REAL adapter binary -- "it works here" is still an assumption, not
an observation. FR-44 requires `marshal adapters smoke` to drive a canonical,
adapter-agnostic smoke story through the full `spec read -> change -> verify
-> commit` lifecycle inside a throwaway, `ephemeral: true` loop home that is
structurally exempt from AD-29's promotion-reachability predicate (AD-37) and
leaves no residue, reporting `pass | fail | unavailable` with the failing
stage named.

**Approach:** `HarnessPort` (`ports/harness.py`) gains one new value type,
`SmokeRunResult` (mirroring `AdapterProbe`/`UsageSnapshot`'s own "facts the
caller could not have known in advance" convention), and one new method,
`run_smoke(project, *, adapter_name, story, timeout_s, log_path) ->
SmokeRunResult` -- reusing the EXISTING `_get_profile` seam (raises
`HarnessError` for an unknown adapter or an unimportable `bmad_loop`,
identical to `adapter_probe`/`adapter_binary`), then a SINGLE bounded
`bmad-loop run --story <story> --max-stories 1` subprocess call (the SAME
`_run_argv` builder `spin`/`run_foreground` already share), redirected to
`log_path` and bounded by `timeout_s` (there is no Marshal supervisor
watching an unattended ephemeral run, unlike `marshal factory spin`'s own
sidecar) -- an absent binary short-circuits to no subprocess at all
(`binary_present=False`), mirroring `adapter_probe`'s identical "an absent
binary is not an error" convention. `render_policy_toml`/`write_policy_toml`
(Story 1.10, already shipped) gain one new keyword parameter, `adapter: str |
None = None` -- when given, sets `[adapter].name` in the rendered policy
(today hardcoded `"claude"` in `_POLICY_TEMPLATE`, confirmed live: no
existing seam lets a caller choose a DIFFERENT configured adapter at all, an
ungapped fact this story is the first to need), mirroring the EXISTING
`difficulty` parameter's own "additive, backward-compatible keyword" shape.

`core/conformance.py` (already this epic's home for adapter-facts status
vocabulary) gains a THIRD, independent closed status pair --
`STATUS_SMOKE_PASS`/`STATUS_SMOKE_FAIL`/`STATUS_SMOKE_UNAVAILABLE` -- plus a
four-member closed stage vocabulary (`STAGE_READ`/`STAGE_CHANGE`/
`STAGE_VERIFY`/`STAGE_COMMIT`, the AC's own "spec read -> change -> verify ->
commit" lifecycle) and a pure `evaluate_smoke(facts: SmokeFacts) ->
SmokeReport` classifier (no I/O, mirrors `evaluate_conformance`'s own "the
I/O boundary gathers facts, this module only classifies" split). Classifies
from four already-gathered booleans/facts (`binary_present`, `file_changed`,
`commit_made`, `launched`) in strict lifecycle order -- `commit_made` is the
ONE passing condition (all four stages completed); short of that, the
EARLIEST stage lacking positive evidence is named the failing one. This is a
genuine, stated fidelity limit (see Design Notes): Marshal cannot observe
"read" or "verify" succeeding or failing from OUTSIDE the adapter's own
session (bmad-loop's own dev-session internals are not a surface this
package wraps), so the classifier infers the failing stage from the
OBSERVABLE boundary facts a git worktree and a known target file expose,
never from adapter-internal introspection.

`cli/adapters.py` gains the new standalone action `marshal adapters smoke
--adapter <name> [--timeout-seconds N] [--format]` (the `smoke`... action
this file's own module docstring reserves the CONCEPT of via "later Epic-6
stories' own additions to this SAME nested parser" -- `run_adapters_smoke`
takes NO project slug, unlike `sync`/`conform`/`probe`: FR-44's own "it works
here" is a MACHINE-and-adapter fact, independent of any one project, exactly
the framing AD-37's own machine-scoped write target already establishes for
probe records). `run_adapters_smoke`: `--adapter` non-blank
(`MRS-SMOKE-005`, checked before any I/O) -> resolve `repo_root`
(`VcsPort.repo_common_root`) -> provision a FRESH, randomly-suffixed
ephemeral home (`_smoke-<adapter>-<8 hex chars>`, under the SAME
`_loop_home_root()` `cli/init.py` already exports) via `VcsPort.add_worktree`
off `main` -> write a NEW sibling marker file, `<home>/.marshal-ephemeral`
(AD-37's "a flag only this command may set" -- no other command in this
package's own source tree ever writes this filename; see Design Notes for
why it is a SIBLING marker file, never a new field folded into the
BMAD-owned `.active-project` marker `cli/init.py::run_init` already
manages) -> materialize a self-contained synthetic BMAD scaffold ENTIRELY
INSIDE the ephemeral home (a real `_bmad-output/implementation-artifacts`
directory -- never a symlink, mirroring `tests/integration/
test_init_worktree.py::_seed_bmad_config_and_sprint_status`'s own established
fixture shape for the identical "marshal init deliberately does not create
the top-level compatibility symlink" gap -- carrying a one-story
`sprint-status.yaml` and a Marshal-authored, adapter-agnostic
`spec-1-1-marshal-conformance-smoke.md`, plus an empty `_bmad-output/
planning-artifacts` directory) -> render+write `.bmad-loop/policy.toml` with
`[adapter].name` forced to the requested `--adapter` (the new
`write_policy_toml(..., adapter=adapter_name)` parameter) -> read
`VcsPort.worktree_head_sha` (Story 4.4, already shipped) as the PRE-run
baseline -> `harness.run_smoke(...)`, bounded by `--timeout-seconds`
(default 900s) -> gather post-run facts (`SMOKE.md`'s content changed;
`worktree_head_sha` advanced past the baseline) -> `core.conformance.
evaluate_smoke` -> `MRS-SMOKE-003` (ERROR, naming the failing stage) if and
only if `status == "fail"` -- `"unavailable"` registers NO finding and exits
0, mirroring `adapters probe`'s own AD-31 "read-only reporting surface, never
a run precondition" precedent -> write the smoke's own RESULT RECORD (never
the ephemeral home itself, which is about to be deleted) to AD-37's single
declared machine-scoped path, a SECOND filename alongside
`adapter-probes.json`/`adapter-acknowledgements.json`
(`adapter-smoke.json`, same "one file, one collection, keyed by adapter
name" shape, same `acquire_advisory_lock`/`release_advisory_lock` guard
Story 6.4's own review pass added for the identical concurrent-write hazard)
-> teardown, ALWAYS attempted in a `finally` regardless of the smoke's own
outcome: unconditional `VcsPort.remove_worktree(..., force=True)` +
`delete_branch(..., force=True)` -- see Design Notes for why this is a
DELIBERATELY simpler, unconditional path, never a call into `cli/init.py::
run_teardown` -- any cleanup failure registers `MRS-SMOKE-004` (WARN, never
overriding the smoke's own already-computed pass/fail/unavailable verdict --
AD-31's "the context lives in the code": a cleanup failure is a different
fact from the smoke's own result).

## Boundaries & Constraints

**Always:**
- **`HarnessPort.run_smoke` never raises for anything except an unknown
  `adapter_name` or an unimportable `bmad_loop`** (`_get_profile`'s existing
  contract, reused verbatim) -- an absent binary, a launch failure, a
  non-zero exit, or a bounded timeout all degrade onto `SmokeRunResult`'s own
  fields, mirroring `adapter_probe`'s identical "never raises for a
  subprocess-flakiness class of failure" convention.
- **An absent adapter binary short-circuits to NO subprocess call at all**
  (`binary_present=False`, `launched=False`) -- mirrors `adapter_probe`'s
  identical short-circuit for the identical reason (never attempt a
  subprocess against a binary that is not on `PATH`).
- **`[adapter].name` is forced via the NEW `render_policy_toml`/
  `write_policy_toml` `adapter=` parameter, never by hand-patching the
  rendered TOML text a second way** -- one seam, `adapters/
  harness_bmadloop.py`, renders every field of this file (AD-3/AD-10/AD-35
  unchanged).
- **The ephemeral home's `.marshal-ephemeral` marker is written ONLY by
  `run_adapters_smoke`'s own provisioning code** -- no other command in this
  package's source tree ever references this filename (grepped before
  writing this spec: zero hits outside this story's own new code) -- the
  AC's own "a flag only this command may set" is satisfied structurally,
  not by a runtime permission check.
- **Teardown is UNCONDITIONAL and ALWAYS attempted**, in a `finally` block,
  regardless of whether the smoke itself passed, failed, or the adapter was
  unavailable, or whether provisioning itself partially failed after the
  worktree was created -- "leaves no residue" is a per-invocation guarantee,
  never contingent on the smoke's own outcome.
- **The smoke's own RESULT RECORD is written to AD-37's single declared
  machine-scoped path** (`_machine_state_dir() / "adapter-smoke.json"`,
  reusing the EXISTING `_machine_state_dir` helper `cli/init.py` already
  exports and `adapter-probes.json` already established the "one file, one
  collection, advisory-locked" shape for) -- NEVER into any project's own
  artifacts, and never into the ephemeral home itself (which is deleted
  before this command returns).
- **`run_adapters_smoke` reuses `VcsPort.worktree_head_sha` (Story 4.4) for
  its pre/post commit-advancement check** -- never a second git-facts
  mechanism (AD-33: git is the sole authority for repository facts).
- **`"unavailable"` registers NO finding and exits 0** -- the SAME AD-31
  "read-only reporting surface" tier `adapters probe` already established for
  the identical real-world fact ("this adapter's binary is not on this
  host") from a different, non-run-dependent call site.

**Never:**
- **No call into `cli/init.py::run_teardown`.** That command's refusal
  machinery (dirty-working-tree check, `is_branch_merged`, the AD-29
  unreachable-promotion check) exists to protect REAL work a real project
  might still need promoted -- an ephemeral home's own commits were NEVER
  meant to be promoted anywhere (AD-37's own "produces no promotable artifact
  by construction"), so applying that refusal-capable machinery here would
  either be permanently vacuous (the ephemeral branch is never merged into
  `main`, so `is_branch_merged` would refuse EVERY smoke run without
  `--force`) or actively wrong (dressing up an intentionally-throwaway
  branch's removal as though it needed the same safety net as a real
  story's). Teardown here is a DELIBERATELY simpler, unconditional
  `remove_worktree(force=True)` + `delete_branch(force=True)` pair -- a
  genuine, stated design decision (see Design Notes), not an oversight.
- **No modification of `cli/init.py`.** This story's own Surface line names
  only `cli/adapters.py`/`core/conformance.py`; every home-path/marker
  primitive this story needs (`_loop_home_root`, `_machine_state_dir`)
  already exists there and is imported, mirroring this file's own EXISTING
  `from .init import _home_path, _machine_state_dir` precedent.
- **No dispatch on adapter name anywhere in the new code** (AD-19) --
  `run_smoke` reads everything it needs from the resolved `CLIProfile` plus
  one generic subprocess primitive (`bmad-loop run --story ... --max-stories
  1`), exactly like `adapter_probe`'s own two generic primitives.
- **No reuse of any REAL project's own `_bmad-output/projects/<slug>/`
  tree.** The synthetic BMAD scaffold this story writes is entirely
  self-contained inside the ephemeral home's own worktree -- never touching
  this repo's own active-project marker/symlink pair, never touching any
  real project's Tier-3 store.
- **No second redaction vocabulary.** The smoke's own machine-scoped record
  routes through the SAME `core.egress.to_redacted` serializer `adapter-
  probes.json` already established -- no new regex, no new secret-key list.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A named adapter's binary is present, the smoke story completes (a commit lands) | Ordinary success | `status == "pass"`, `failing_stage: null` | No finding |
| A named adapter's binary is absent from `PATH` | Not installed on this host | `status == "unavailable"`, no subprocess attempted | No finding; exits 0 |
| The harness launches but produces no file change and no commit | Adapter never engaged the story | `status == "fail"`, `failing_stage == "read"` | Registered finding (`MRS-SMOKE-003`, ERROR) |
| A file change lands but no commit ever appears | Verify (or the commit step itself) never completed | `status == "fail"`, `failing_stage == "verify"` | Registered finding (`MRS-SMOKE-003`, ERROR) |
| The bounded subprocess call times out before returning | Adapter session hung/unresponsive | `status == "fail"`, `failing_stage` per whatever facts were observable at the deadline; `detail` names the timeout explicitly | Registered finding (`MRS-SMOKE-003`, ERROR) |
| The `--adapter` name is unknown to `bmad_loop`'s own profile registry, or `bmad_loop` itself is not importable | Configuration/install error | `HarnessError` from `run_smoke` (via `_get_profile`) | Registered finding (`MRS-SMOKE-001`, UNEVALUABLE); ephemeral home still torn down |
| `--adapter` is omitted or blank | Missing required identifier | No filesystem/git/harness touch at all | Registered finding (`MRS-SMOKE-005`, UNEVALUABLE) |
| Ephemeral-home provisioning itself fails (`git worktree add` fails) | Git/filesystem failure | No smoke attempted | Registered finding (`MRS-SMOKE-002`, ERROR) |
| The smoke ran (pass, fail, or unavailable) but teardown (`remove_worktree`/`delete_branch`) fails | Residual worktree/branch left behind | The smoke's own already-computed status/finding is UNCHANGED | Registered finding (`MRS-SMOKE-004`, WARN) -- never overrides the smoke's own verdict |
| Writing the machine-scoped smoke record fails (unwritable `MARSHAL_STATE_HOME`, disk full, or the advisory lock cannot be acquired) | I/O failure | The envelope still reports the observed `data.smoke` (the OBSERVATION succeeded even if the WRITE did not) | Registered finding (`MRS-SMOKE-006`, ERROR) |
| A pre-existing `adapter-smoke.json` is malformed JSON | Corrupt bookkeeping | Treated as an empty collection (mirrors `_read_probe_state`'s own degrade); this smoke's own entry still writes | Registered finding (`MRS-SMOKE-007`, WARN) |
| Two smoke runs of different adapters, same machine, same day | Ordinary repeated use | Each write MERGES into the same `adapter-smoke.json`, keyed by adapter name | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/harness.py` -- EDIT. New frozen dataclass
  `SmokeRunResult` (`adapter: str`, `binary: str`, `binary_present: bool`,
  `launched: bool`, `returncode: int | None`, `timed_out: bool`), mirroring
  `AdapterProbe`'s own "facts the caller could not have known in advance"
  convention. New `HarnessPort.run_smoke(project, *, adapter_name, story,
  timeout_s, log_path) -> SmokeRunResult`, docstring mirroring
  `adapter_probe`'s exact raise-contract.
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT. New module
  constant `_SMOKE_DEFAULT_TIMEOUT_S = 900.0`. `render_policy_toml`/
  `write_policy_toml` each gain one new keyword parameter, `adapter: str |
  None = None` -- when given, `doc["adapter"]["name"] = adapter` (applied
  independently of the existing `difficulty` tiering, which touches
  `[adapter.<stage>].model` sub-tables, never `[adapter].name`). New
  `BmadLoopHarness.run_smoke`: resolves the profile via the EXISTING
  `self._get_profile(adapter_name, project)` (unchanged, reused verbatim);
  `binary_present = self.binary_present(profile.binary)`; if absent, returns
  immediately with `launched=False`, `returncode=None`, `timed_out=False`
  (capabilities/subprocess never touched); if present, ONE
  `subprocess.run(self._run_argv(epic=None, story=story, max_count=1), cwd=
  project, stdout=log_file, stderr=log_file, timeout=timeout_s)` call
  (mirrors `spin`'s own log-redirection recipe, but bounded and synchronous
  rather than detached), catching `subprocess.TimeoutExpired` (`timed_out=
  True`) and `OSError` (`launched=False`) as the two non-raising degrades;
  a clean return normalizes the return code via the EXISTING
  `_normalize_returncode` static method.
- `src/pyforge/marshal/core/conformance.py` -- EDIT. New status constants
  `STATUS_SMOKE_PASS = "pass"`, `STATUS_SMOKE_FAIL = "fail"`,
  `STATUS_SMOKE_UNAVAILABLE = "unavailable"` (a THIRD, independent closed
  pair -- never merged into `ALL_STATUSES` or Story 6.4's own
  `STATUS_AVAILABLE`/`STATUS_UNAVAILABLE`, even though the string literal
  `"unavailable"` happens to coincide -- AD-31's "never conflated, never
  sharing a constant" is about the CONSTANT/classification, not about
  coincidental string equality between two independently-declared
  vocabularies). New stage constants `STAGE_READ`/`STAGE_CHANGE`/
  `STAGE_VERIFY`/`STAGE_COMMIT` (`"read"`/`"change"`/`"verify"`/`"commit"`)
  plus `SMOKE_STAGES` (the ordered tuple). New frozen dataclasses
  `SmokeFacts` (`binary_present: bool`, `launched: bool`, `timed_out: bool`,
  `file_changed: bool`, `commit_made: bool`, `returncode: int | None`) and
  `SmokeReport` (`status: str`, `failing_stage: str | None`, `detail: str`).
  New pure `evaluate_smoke(facts: SmokeFacts) -> SmokeReport`: `not
  binary_present` -> `STATUS_SMOKE_UNAVAILABLE`/`None`; `commit_made` ->
  `STATUS_SMOKE_PASS`/`None`; `file_changed` (but no commit) ->
  `STATUS_SMOKE_FAIL`/`STAGE_VERIFY`; `launched` (but no file change) ->
  `STATUS_SMOKE_FAIL`/`STAGE_CHANGE`; otherwise (never launched despite a
  present binary -- a launch-time `OSError`) -> `STATUS_SMOKE_FAIL`/
  `STAGE_READ`. `detail` always names `timed_out`/`returncode` when either
  is informative. New pure `build_smoke_record(adapter: str, report:
  SmokeReport, *, binary: str, binary_present: bool) -> dict[str, object]`,
  mirroring `build_probe_record`'s own "the caller already gathered every
  fact, this function only shapes" convention.
- `src/pyforge/marshal/cli/adapters.py` -- EDIT. Module-level `from .init
  import _home_path, _loop_home_root, _machine_state_dir` (extends the
  existing import statement -- same direction, no new circular-import risk).
  Module-level `from ..adapters.vcs_git import GitVcs`, `from ..ports.vcs
  import VcsPort`. New constants `_SMOKE_STATE_FILENAME = "adapter-smoke.
  json"`, `_SMOKE_LOCK_TIMEOUT_S = 5.0`, `_SMOKE_MARKER_FILENAME =
  ".marshal-ephemeral"`, `_SMOKE_TARGET_FILENAME = "SMOKE.md"`, the
  Marshal-authored canonical smoke story's frontmatter-free markdown body
  (a module constant, adapter-agnostic: "append a fixed marker line to
  SMOKE.md, verify it is present via `grep`, commit"), and the synthetic
  `sprint-status.yaml` content (one story, key `1-1-marshal-conformance-
  smoke`, status `ready-for-dev`). New `add_adapters_subparser` nested
  action `smoke` (`marshal adapters smoke --adapter <name> [--timeout-
  seconds N] [--format]` -- no `slug` positional, unlike `sync`/`conform`/
  `probe`). New `_render_text_smoke(data, findings) -> str` mirroring
  `_render_text_probe`'s own shape. New `_provision_smoke_home(vcs, fs,
  repo_root, adapter_name) -> Path` (worktree + marker + scaffold + policy,
  raising a typed exception the caller converts to `MRS-SMOKE-002`). New
  `_teardown_smoke_home(vcs, repo_root, home, branch) -> str | None`
  (unconditional force-remove, returning an error message or `None`). New
  `run_adapters_smoke(args, *, fs=None, harness=None, vcs=None, record=None,
  context=None)`: `--adapter` non-blank (`MRS-SMOKE-005`) -> resolve
  `repo_root` (`MRS-SMOKE-002` on `VcsCommandError`) -> provision (try/
  except, `MRS-SMOKE-002`) -> pre-run `worktree_head_sha` -> `harness.
  run_smoke(...)` wrapped in `try`/`except HarnessError` (`MRS-SMOKE-001`)
  -> gather post-run facts (`SMOKE.md` content, post-run `worktree_head_
  sha`) -> `core.conformance.evaluate_smoke` -> `MRS-SMOKE-003` if
  `status == "fail"` -> `build_smoke_record` -> read-merge-write
  `adapter-smoke.json` under the SAME advisory-lock discipline `run_
  adapters_probe` already established (`MRS-SMOKE-006`/`007` mirroring
  `MRS-ADP-015`/`016` verbatim) -> teardown in a `finally` (`MRS-SMOKE-004`
  on failure, never overriding the already-built findings list) -> `_emit`
  with `command="adapters smoke"`, `renderer=_render_text_smoke`.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register seven new codes:
  `MRS-SMOKE-001` (`run_smoke` raised `HarnessError`), `MRS-SMOKE-002`
  (ephemeral-home provisioning failed), `MRS-SMOKE-003` (smoke status is
  `"fail"`, naming the failing stage), `MRS-SMOKE-004` (teardown failed --
  residue left behind), `MRS-SMOKE-005` (missing/blank `--adapter`),
  `MRS-SMOKE-006` (writing the machine-scoped smoke record failed),
  `MRS-SMOKE-007` (a pre-existing `adapter-smoke.json` was malformed JSON).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. `MRS-SMOKE-001`/`005` ->
  `Verdict.UNEVALUABLE` (mirrors `MRS-ADP-014`/`013`'s own tiers verbatim).
  `MRS-SMOKE-002`/`003`/`006` -> `Verdict.ERROR` (mirrors `MRS-ADP-002`/
  `MRS-CONFORM-001`/`MRS-ADP-015`'s own "a real operation was attempted and
  failed, or real drift/failure was detected" tier). `MRS-SMOKE-004`/`007`
  -> `Verdict.WARN` (mirrors `MRS-ADP-009`'s own "degrades, never blocks,
  the primary observation already succeeded" tier).
- `tests/unit/test_harness_bmadloop_smoke.py` -- NEW. `run_smoke` matrix:
  binary present + story completes (commit) -> `launched=True`,
  `returncode` normalized; binary absent -> no subprocess call at all
  (asserted via a spy `subprocess.run`); `subprocess.TimeoutExpired` ->
  `timed_out=True`; launch-time `OSError` -> `launched=False`; unknown
  adapter / unimportable `bmad_loop` -> `HarnessError`. `render_policy_
  toml`/`write_policy_toml`'s new `adapter=` parameter: sets `[adapter].
  name`; omitted keeps the template's baseline `"claude"`; composes cleanly
  alongside an existing `difficulty=` tiering call.
- `tests/unit/test_conformance.py` -- EDIT. `evaluate_smoke` matrix: all
  four terminal shapes (`pass`, `fail`/`verify`, `fail`/`change`,
  `fail`/`read`, `unavailable`), `timed_out`/`returncode` reflected in
  `detail`. `build_smoke_record` shape matrix. `STATUS_SMOKE_*`/
  `STAGE_*` never appear in `ALL_STATUSES` (Story 6.3's own vocabulary
  stays closed and unchanged) or in Story 6.4's `STATUS_AVAILABLE`/
  `STATUS_UNAVAILABLE` pair.
- `tests/unit/test_adapters_cli.py` -- EDIT. `run_adapters_smoke` matrix
  reusing the existing `FakeFs`/`FakeHarness` doubles (extended with
  `run_smoke`) plus a new `FakeVcs` double mirroring `test_init.py`'s own
  shape: pass, fail (each failing stage), unavailable (no finding, exit 0),
  unknown adapter, missing `--adapter`, worktree-provisioning failure,
  teardown failure (smoke's own verdict unchanged, `MRS-SMOKE-004`
  registered alongside it), write failure, pre-existing malformed
  `adapter-smoke.json` (merge preserves other adapters' entries),
  `--format text` rendering, and a round-trip proving the WRITTEN file's
  bytes are the `to_redacted` output. A dedicated test asserts teardown is
  attempted (mocked `remove_worktree`/`delete_branch` calls observed) on
  EVERY terminal path, including the `HarnessError`/provisioning-failure
  paths.
- `tests/meta/test_ad11_write_boundary.py` -- EDIT (audited during
  implementation; the new `adapter-smoke.json` write target sits under the
  SAME machine-scoped base `adapter-probes.json`/`adapter-acknowledgements.
  json` already use -- extended only if that test currently hardcodes
  filenames rather than the shared base directory).

## Design Notes

- **Why the smoke's own classifier cannot distinguish "read" from "verify"
  failing with full fidelity.** Marshal wraps `bmad-loop run` as an opaque
  subprocess (AD-3) and never introspects the adapter's own dev-session
  internals (which turn/tool-call corresponds to "reading the spec" versus
  "writing the change" versus "running verify") -- that fidelity would
  require parsing bmad-loop's own per-task `state.json` phase transitions or
  the adapter's own transcript, neither of which this package's existing
  `HarnessPort` surface exposes at that granularity (`RunStatusSnapshot`
  covers PAUSE/DEFERRED states for a LIVE, journal-tracked Marshal run --
  this story's own ephemeral smoke is neither). The four-stage
  classification is therefore inferred from the OUTERMOST observable
  boundary: did a file change, did a commit land. This is a genuine,
  recorded fidelity limit, not an oversight -- a future story wanting
  finer-grained stage attribution would need to widen `HarnessPort` (a
  `run_status_snapshot`-style read against the smoke's own ephemeral run) or
  parse bmad-loop's own state file directly, neither of which this story's
  own Effort/scope affords.
- **Why teardown never calls `cli/init.py::run_teardown`.** That command's
  entire refusal apparatus (dirty check, `is_branch_merged`, AD-29
  reachability) exists to protect a REAL story's real, promotable work --
  applying it to an ephemeral home would be either permanently vacuous (the
  smoke branch is by construction never merged to `main`, so `is_branch_
  merged` would refuse every single smoke run) or a confusing, redundant
  safety net over content that was never meant to survive this command's own
  return. AD-37 already resolves the correct posture: an ephemeral home
  "produces no promotable artifact by construction" -- unconditional force
  removal is the direct expression of that, not a workaround for it.
- **Why the ephemeral marker is a sibling file, not a new field on the
  BMAD-owned `.active-project` marker.** The smoke's own scaffold is NOT a
  real BMAD project registered under `_bmad-output/projects/<slug>/` in the
  main checkout at all (unlike every `marshal init`-provisioned home) --
  writing an `ephemeral` field into `.active-project` would imply this is an
  ordinary BMAD active-project marker with one extra property, when
  structurally it is a wholly separate, self-contained scaffold `cli/init.
  py::run_init`'s own marker/symlink/backlink convergence logic never
  touches. A sibling file at the home's own root keeps the two concepts
  visibly distinct and keeps `cli/init.py` genuinely untouched by this
  story (this story's own Surface line).
- **Why the smoke story's spec/feed live INSIDE the ephemeral worktree
  itself, never under this repo's own `_bmad-output/projects/`.** Two
  options were considered (per this story's own research prompt): a tracked
  fixture project under `_bmad-output/projects/<reserved-slug>/`, or a
  synthetic scaffold materialized fresh at ephemeral-home-creation time.
  The tracked-fixture route was rejected: `_bmad-output/projects/*/
  implementation-artifacts` is UNCONDITIONALLY gitignored (verified live,
  `.gitignore`), so a story's own `sprint-status.yaml` for any reserved
  slug could never be a tracked, reviewable artifact anyway -- the smoke's
  own canonical story CONTENT is instead a plain Marshal-owned Python
  constant in `cli/adapters.py` (reviewable in the exact same PR diff a
  tracked fixture file would be, without inventing a permanently-`git init`
  BMAD sub-project this repo's own tooling has no other reason to know
  about), and the scaffold materializing it is regenerated fresh, byte-
  identically, on every smoke run.
- **Why `bmadconfig.load_paths`/`sprintstatus.load` resolve correctly
  against a synthetic scaffold with no top-level `_bmad-output/
  implementation-artifacts` compatibility symlink.** Confirmed live against
  the installed `bmad_loop` 0.9.0: `bmadconfig.load_paths(project)`
  templates `{project-root}` as the literal `project` argument (never the
  MAIN checkout's root), so `implementation_artifacts` resolves to
  `<ephemeral-home>/_bmad-output/implementation-artifacts` -- a plain,
  ordinary path inside the worktree that this story creates directly as a
  REAL directory (never a symlink), exactly the same fixture shape `tests/
  integration/test_init_worktree.py::_seed_bmad_config_and_sprint_status`
  already established for the identical, already-documented gap ("`marshal
  init` deliberately does not create the top-level compatibility symlink").
- **Why `[adapter].name` needed a NEW `render_policy_toml`/
  `write_policy_toml` parameter rather than a hand-patched TOML string.**
  Confirmed live: `render_policy_toml` NEVER derives `[adapter].name` from
  `EffectivePolicy` at all -- it is a hardcoded template baseline
  (`"claude"`), an ungapped fact this codebase has not needed to close until
  this story (every prior story's own adapter resolution reads WHATEVER
  the rendered policy already names, never chooses a different one). AD-3
  confines every `bmad_loop`-adjacent write to `adapters/harness_bmadloop.
  py` -- a second, `cli/adapters.py`-local TOML-patching routine would
  duplicate that seam's one job. The new keyword mirrors the EXISTING
  `difficulty` parameter's own precedent exactly (additive, optional,
  backward-compatible; every existing caller that never passes it is
  byte-identically unaffected).
- **Why the smoke's own result record is written to the MACHINE-scoped
  path, never the tracked conformance matrix.** AD-37's own text is
  explicit: "Raw probe records stay machine-scoped -- they are transient
  host facts, not a claim." A single smoke RUN is exactly that class of
  transient host fact (Story 6.6's own later scope, "accumulated probe and
  smoke results," is what turns repeated observations into the TRACKED,
  per-host matrix `planning-artifacts/conformance/matrix/<hostname>.md` --
  this story writes one of the raw ingredients that later accumulation
  reads, never the tracked artifact itself).

## Verification

- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (the FULL suite, including `@pytest.mark.slow` integration tests) -- **2949 passed** (2948 baseline from S-6.4 + a net 46 new: 11 `HarnessPort.run_smoke` unit tests + 4 `render_policy_toml`/`write_policy_toml` `adapter=` tests (`test_harness_bmadloop_smoke.py`), 9 `evaluate_smoke`/`build_smoke_record` tests (`test_conformance.py`), 17 `run_adapters_smoke` tests (`test_adapters_cli.py`), plus the `REGISTERED_CODES` snapshot addition (`test_findings.py`)).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing accepted baseline (2 `pyforge-steward` -- `_http` module-alias gap, `age` conda-only run-dep; 1 `pyforge-doctor` -- `mcp` dependency gap), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- AD-3, AD-4, AD-9 all KEPT (87 files, 487 dependencies analyzed).
- **Live verification (real, not faked):** `marshal adapters smoke --adapter codex` and `--adapter copilot` (both genuinely absent from this host's `PATH`) were run against the REAL `pyforge-marshal` pixi environment end to end -- a real `git worktree add` off `main`, real scaffold/policy writes, real `HarnessPort.run_smoke` invocation (which correctly short-circuited on the absent binary, no subprocess launched), `status: "unavailable"`, exit 0, zero findings, the machine-scoped `~/.local/state/pyforge-marshal/adapter-smoke.json` record written correctly, and confirmed via `git worktree list`/`git branch --list` that the worktree and branch were fully removed -- **no residue**. The missing-`--adapter` and unknown-adapter-name paths were also run live (both safe, no subprocess risk) and behaved as specified (`MRS-SMOKE-005`/`MRS-SMOKE-001`, exit 1, teardown still ran in both cases).
- **NOT exercised live:** a full end-to-end run against a REAL, PRESENT adapter binary (this host does have `claude` on `PATH`) was deliberately NOT attempted -- that would launch a real, authenticated, potentially multi-minute `bmad-loop run` dev+review session from inside this already-running Claude Code agent turn (cost, hang risk, and an unverified recursion/session-nesting hazard). The `pass`/`fail` classification paths (`STAGE_VERIFY`/`STAGE_CHANGE`/`STAGE_READ`) are verified only against `FakeHarness`/`FakeSmokeVcs` doubles, never a real adapter session. See Design Notes' own "fidelity limit" paragraph and this session's own report for the full reasoning.

## Review Triage Log

No adversarial review pass was requested for this session (single-agent implementation, mirrors Story 6.3/6.4's own precedent for when one is not requested). One real correctness bug was caught and fixed during self-implementation, surfaced by writing a dedicated regression test rather than a separate review pass:

- **Residue leak on a partial provisioning failure.** The original `_provision_smoke_home` performed BOTH the git worktree creation AND the scaffold materialization (marker/sprint-status/spec/policy writes) inside one function, wrapped in one `try`/`except _SmokeProvisionError` at the call site that `return`ed immediately on failure -- BEFORE the `try`/`finally` that runs teardown was ever entered. A scaffold-write failure occurring AFTER the worktree already existed (e.g. a disk-full mid-scaffold) would therefore leak the worktree and branch, directly contradicting the AC's own "the ephemeral home leaves no residue afterwards." Fixed by splitting provisioning into `_add_smoke_worktree` (if this raises, nothing was created, safe to return without teardown) and `_materialize_smoke_scaffold` (run INSIDE the `try`/`finally` that always tears down, once the worktree is known to exist). New regression test: `test_smoke_scaffold_materialization_failure_after_worktree_created_still_tears_down`.
- A separate, smaller self-caught issue: the initial `slug = f"_smoke-{safe_adapter}-{secrets.token_hex(4)}"` f-string tripped `tests/meta/test_ad23_inline_key_format_guard.py` (AD-23's "no module outside `core/identity.py` inline-formats a story-key-shaped two-placeholder-plus-separator literal" AST guard) -- a false positive for a non-story-key slug, but the guard is a blunt structural pattern match with no semantic awareness. Fixed by plain string concatenation instead of an f-string with exactly two placeholders separated by a bare `-`.

**Follow-up review recommendation: false** -- both fixes are narrow and each covered by a dedicated new/adjusted test; the one open, genuinely unresolved item is the "not exercised against a real, present adapter" scope boundary named in Verification above, which is a deliberate, documented decision rather than an open defect.

### 2026-08-07 — Adversarial review pass (Blind Hunter + Edge Case Hunter)

A parallel adversarial review was run against this story's diff after all, dispatched with the diff file path only, no shared context. Both agents were framed with worktree-safety-focused scrutiny given `_add_smoke_worktree`/`_teardown_smoke_home`'s git-operation surface. Three real, confirmed findings, all now fixed:

- **Worktree leak on provisioning timeout (Blind Hunter).** `GitVcs.add_worktree`'s own docstring documents that a `TimeoutExpired` can leave a REGISTERED, partial worktree/branch behind even though it raises `VcsCommandError` -- ordinarily left as-is by design for an operator to inspect (the general `git worktree`-touching convention elsewhere in this codebase), but an ephemeral smoke home specifically promises to leave NO residue (AD-37). `_add_smoke_worktree`'s own docstring claimed "if THIS raises, no worktree/branch was ever created" -- true for an ordinary failure, false for the timeout path. Fixed: `_add_smoke_worktree` now calls `_teardown_smoke_home` best-effort before re-raising `_SmokeProvisionError`, restoring the "nothing created" invariant on every failure path, not just the ordinary one. New test: `test_smoke_add_worktree_failure_attempts_best_effort_teardown`.
- **False-FAIL on a transient pre-run `worktree_head_sha` failure (Edge Case Hunter).** A single transient read failure of the pre-run HEAD sha used to permanently pin `pre_sha` to `None` for the rest of the run, which makes `commit_made` unconditionally `False` below regardless of what the harness actually did -- misreporting a genuine PASS as FAIL. Fixed: the pre-run read is now retried once before degrading to the existing WARN-and-continue behavior. New test: `test_smoke_transient_pre_sha_read_failure_is_retried_and_still_detects_a_commit`.
- **PASS misclassification ignoring `returncode`/`file_changed` (Edge Case Hunter).** `evaluate_smoke` treated `commit_made` alone as sufficient for `STATUS_SMOKE_PASS` -- a non-zero `bmad-loop` exit code alongside a commit that still landed, OR a commit that never touched the smoke's own target file (`SMOKE.md`), both misreported PASS. Fixed: PASS now requires `commit_made` AND `file_changed` AND a clean `returncode` (`0`/`None`) together; a commit lacking that full corroboration reports FAIL at a new `STAGE_COMMIT` failing stage instead of silently passing. New tests: `test_evaluate_smoke_nonzero_returncode_with_commit_is_not_a_pass` (renamed from the old `..._folds_into_detail_on_pass`, which encoded the buggy behavior), `test_evaluate_smoke_commit_without_file_change_is_not_a_pass`. Six pre-existing CLI-level tests that asserted a `pass` verdict from a `FakeFs()` with no seeded `SMOKE.md` content (relying on the same bug) were updated to seed the marker file via a new `_pass_fs(tmp_path)` helper, matching genuine full-corroboration PASS semantics rather than changing their assertions to `fail`.

**Re-verification (2026-08-07, after all three patches):** `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (full suite, including `@pytest.mark.slow`) -- **2952 passed** (2949 baseline + 3 net new: 2 new regression tests in `test_adapters_cli.py`, 1 new + 1 renamed in `test_conformance.py`).

**Follow-up review recommendation (updated): false** -- all three findings are narrow, each covered by a dedicated regression test, and the full suite (including slow/integration tests) is green.

</intent-contract>
