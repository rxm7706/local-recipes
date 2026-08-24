---
title: 'The channel:<name> ship target'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: 'b7a9b78a539b2afc37b551065362c65063b64fd3'
final_revision: '907cc97ece8895e671e8dd56a2efb88787fd1182'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/engines/twine.py'
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/engines/pixi.py'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `package.py::parse_ship_targets`/`plan_ship` (Story 3.3) already recognize
`channel:<name>` and can dry-run-describe it, but nothing actually uploads a built `.conda`
artifact to a named private conda channel yet -- an enterprise user with a private channel has no
way to ship there (FR-16 channel form).

**Approach:** Add `engines/pixi.py::upload()` (a new `pixi upload prefix --channel <name>
<conda_path>` adapter, resolving epic OQ-E2 in favour of the `prefix` pixi-upload subcommand -- its
single `--channel <name>` value is the only one of pixi's upload subcommands that maps 1:1 onto
the vocabulary's bare `channel:<name>` string without inventing unspecified owner/URL/bucket
syntax) and `package.py::ship_channel()`, mirroring Story 3.4's `ship_pypi()` shape exactly: check
`PREFIX_API_KEY` presence in `environ` before calling `build()`, reuse `build()` unconditionally,
then map the upload's returncode to a `TERMINAL`/`FAILED` `ShipTargetResult`.

## Boundaries & Constraints

**Always:**
- `ship_channel` checks `PREFIX_API_KEY` presence in `environ` FIRST, before `build()` is ever
  called (AD-14, mirrors `ship_pypi`'s identical precondition-first structure); only presence is
  checked -- the value is never read into a variable used for anything else, logged, or stored on
  the returned object.
- `engines.pixi.upload()` calls `require_engine("pixi")` before any subprocess spawns, then runs
  `["pixi", "upload", "prefix", "--channel", channel_name, conda_path]` -- the pixi CLI's own clap
  parser requires the `prefix` subcommand and its `--channel` flag BEFORE the trailing
  `[PACKAGE_FILES]...` positional (re-verified live, 2026-08-13, review pass: `pixi upload
  <file> prefix --channel <name>` -- the file positioned before the subcommand -- fails with clap's
  own `error: unexpected argument '--channel' found` before ever reaching `prefix`, while `pixi
  upload prefix --channel <name> <file>` reaches the tool's real credential check) -- with no
  `--api-key` flag and no `env=` override -- `pixi` itself reads `PREFIX_API_KEY` from its inherited environment
  automatically (live-verified: `pixi upload prefix --help` documents `--api-key` as `[env:
  PREFIX_API_KEY=]`), the same env-inheritance-only credential path AD-14/`twine.py` already
  establish.
- `engines.pixi.upload()` captures the child's stdout AND stderr merged into ONE field via
  `stderr=subprocess.STDOUT` (deliberate deviation from `twine.py`'s/`pixi.py::build()`'s own
  `stderr=None` convention) -- live-verified against the installed `pixi 0.76.2` binary: a
  missing-credential failure (`pixi upload prefix --channel x nonexistent.conda`) prints its
  ENTIRE diagnostic ("Error: no prefix.dev API key provided...") to stderr and writes NOTHING to
  stdout, the opposite of `twine`'s own stdout-only diagnostics; `stderr=None` here would silently
  produce an empty `message` on every real-world channel-upload failure.
- A nonzero `pixi upload` returncode is DATA on the returned `ShipTargetResult` (`state=FAILED`),
  never raised (AD-4) -- mirrors `ship_pypi`'s identical nonzero-upload handling. This resolves the
  story AC's "becomes a typed error and a `failed` target result" wording as: the failure is
  represented through Mason's typed-message-shape convention (the wrapped tool's own diagnostic
  text, verbatim, AD-1) inside a `FAILED` result, not as a raised exception -- raising here would
  break the AC's own "without affecting other targets" clause for a future multi-target caller
  (Story 3.9), mirroring how `ship_pypi`'s own upload-rejection path already stays data, never
  raised.
- `ShipTargetResult.target` is `f"channel:{channel_name}"` (matches `plan_ship`'s own canonical
  reconstruction); on a `TERMINAL` result, `reference` is the bare `channel_name` -- not a
  constructed URL (see Never).
- `build()` (FR-15) is reused unconditionally, never duplicated; when `build_result.conda_path` is
  `None` (the `.conda` engine failed or produced nothing), `ship_channel` returns a `FAILED` result
  directly with `message=build_result.pixi_stdout`, without calling `engines.pixi.upload()`.
- No `cfe` reference anywhere in the new code (AD-6) -- `ship_channel` succeeds with the CFE root
  entirely absent, matching `ship_pypi`'s precedent and `tests/meta/test_capability_tiers.py`'s
  existing (unmodified) AST guard over `package.py`.
- Two new `MasonError` subclasses, `ShipChannelCredentialMissingError`
  (`ship:channel-credential-missing`) and `ShipChannelUploadTimeoutError`
  (`ship:channel-upload-timeout`), each its OWN class
  (not a reuse of `ShipCredentialMissingError`/`ShipUploadTimeoutError`) because those two classes
  hardcode "PyPI" into their message text -- reusing them for a channel failure would print a
  factually wrong message.

**Block If:** none -- OQ-E2 is resolved by this spec's own investigation (live `pixi --help`
inspection); no further human decision is needed.

**Never:**
- Never pass an explicit `--api-key` flag or read `PREFIX_API_KEY`'s VALUE into a variable, and
  never rely on `pixi auth login`'s stored keychain/auth-file as a credential source Mason itself
  depends on -- AD-14's credential-blindness model is env-var-presence-only.
- Never wire the `anaconda`/`artifactory`/`quetz`/`cloudsmith`/`s3` pixi-upload subcommands in v1 --
  `channel:<name>`'s single bare name has no vocabulary for the owner/URL/bucket fields those
  subcommands require.
- Never parse `pixi upload`'s captured output for a URL/reference (unlike `twine`'s `"View at:"`
  scan) -- the success-path output shape was not live-verified (doing so needs a real API key,
  channel, and network access), so a parsed-but-unverified format must not be invented; `reference`
  is deterministically the input `channel_name` instead.
- Never add `--skip-existing`/`--force`/idempotent-retry handling (Story 3.7's scope, mirrors
  `ship_pypi`'s identical exclusion).
- Never modify `plan_ship`/`parse_ship_targets` (Story 3.3 already handles `CHANNEL` correctly) or
  add any CLI (`--ship`/`--to`) wiring (Story 3.9's scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `PREFIX_API_KEY` set, `.conda` built, `pixi upload` returns 0 | `ShipTargetResult(target="channel:<name>", state=TERMINAL, reference="<name>")` | No error |
| Missing credential | `PREFIX_API_KEY` absent/empty in `environ` | Raises before `build()`/`upload()` are ever called | `ShipChannelCredentialMissingError` |
| No `.conda` artifact | `build_result.conda_path is None` | `state=FAILED`, `reference=None`, `message=build_result.pixi_stdout`; `pixi.upload` never called | No exception |
| Channel rejects upload | `pixi upload` returns nonzero | `state=FAILED`, `reference=None`, `message=`merged stdout+stderr | No exception; other targets in a future multi-target call are unaffected |
| `pixi` absent from `PATH` | -- | Propagates uncaught from `build()` or `upload()` | `EngineAbsentError` |
| Upload exceeds timeout | -- | Raised from `engines.pixi.upload()` | `ShipChannelUploadTimeoutError` |
| No CFE installation anywhere | `pixi`/`build` present, no CFE root | Succeeds; `package.py` carries no `cfe` reference | No error |

</intent-contract>

## Code Map

- `src/pyforge/mason/engines/pixi.py` -- add `PixiUploadResult` (frozen dataclass: `returncode`,
  `stdout`) and `upload(conda_path: str, channel: str, *, timeout: float | None = None) ->
  PixiUploadResult`, mirroring `engines/twine.py::upload()`'s gate/timeout/argv shape
  (`require_engine` first, list argv, no `env=`), but with `stderr=subprocess.STDOUT` (see Always
  boundary).
- `src/pyforge/mason/errors.py` -- add `ShipChannelCredentialMissingError(missing: Sequence[str])`
  and `ShipChannelUploadTimeoutError(timeout: float)`, each mirroring `ShipCredentialMissingError`/
  `ShipUploadTimeoutError`'s exact shape (validation rigor, `__reduce__`) with channel-specific
  message text and identifiers.
- `src/pyforge/mason/package.py` -- add `ship_channel(project_path: str, channel_name: str, *,
  environ: Mapping[str, str], target: str = "library") -> ShipTargetResult`, mirroring
  `ship_pypi`'s structure.
- `tests/unit/test_engines_pixi.py` -- extend with `upload()` coverage mirroring
  `test_engines_twine.py`'s ten-test pattern (probe delegation, engine-absence gate, argv shape,
  default/explicit timeout, `TimeoutExpired` translation, merged-stream capture on success and
  failure).
- `tests/unit/test_errors.py` -- extend with both new classes (identifier, message content,
  `__reduce__` round-trip, empty/malformed-`missing` rejection).
- `tests/unit/test_package.py` -- extend with `ship_channel` coverage mirroring `ship_pypi`'s
  pattern (missing-credential-raises-before-build, happy path, no-artifact-built, upload-failure,
  structural-error propagation) plus a case asserting the channel-rejection path returns data, not
  a raised exception.

## Tasks & Acceptance

**Execution:**
- [x] `errors.py` -- add `ShipChannelCredentialMissingError(missing: Sequence[str])`: identifier
  `ship:channel-credential-missing`, message names every entry in `missing` and states it applies
  to the channel upload; raises `ValueError` on an empty or malformed `missing` (mirrors
  `ShipCredentialMissingError`'s validation rigor); `missing` stored as a `tuple`; `__reduce__`
  returning `(self.__class__, (self.missing,))`.
- [x] `errors.py` -- add `ShipChannelUploadTimeoutError(timeout: float)`: identifier
  `ship:channel-upload-timeout`, message names `timeout` and states no per-upload timeout override
  exists in v1
  (mirrors `ShipUploadTimeoutError`'s exact shape); `__reduce__` returning `(self.__class__,
  (self.timeout,))`.
- [x] `engines/pixi.py` -- add `_PIXI_UPLOAD_TIMEOUT_SECONDS = 300.0` (mirrors `twine.py`'s own
  300s network-upload allowance); `PixiUploadResult` frozen dataclass; `upload(conda_path: str,
  channel: str, *, timeout: float | None = None) -> PixiUploadResult` -- `require_engine("pixi")`
  first; `subprocess.run(["pixi", "upload", "prefix", "--channel", channel, conda_path],
  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
  timeout=resolved_timeout, check=False)`; translate `subprocess.TimeoutExpired` to
  `ShipChannelUploadTimeoutError(timeout=resolved_timeout)`; return `PixiUploadResult(returncode,
  stdout)` with no further parsing.
- [x] `package.py` -- add `_REQUIRED_SHIP_CHANNEL_CREDENTIALS = ("PREFIX_API_KEY",)` and
  `ship_channel(project_path: str, channel_name: str, *, environ: Mapping[str, str], target: str =
  "library") -> ShipTargetResult`: check `PREFIX_API_KEY` presence in `environ` first, raising
  `ShipChannelCredentialMissingError` if absent/empty; else call `build(project_path,
  target=target)`; canonical target string is `f"{_CHANNEL_PREFIX}{channel_name}"`; if
  `build_result.conda_path` is `None`, return `FAILED` with `message=build_result.pixi_stdout`
  without calling `pixi.upload`; else call `pixi.upload(build_result.conda_path, channel_name)` and
  map its `returncode` to `TERMINAL` (`reference=channel_name`) / `FAILED` (`reference=None`), both
  with `message=upload_result.stdout`.
- [x] `tests/unit/test_engines_pixi.py` -- `upload()`: `probe()` delegation (already covered,
  unchanged); engine-absence gate (no subprocess spawned); invocation shape (argv, `stdout=PIPE`,
  `stderr=STDOUT`, no `env=` kwarg, `timeout` default/override); `TimeoutExpired` ->
  `ShipChannelUploadTimeoutError`; a merged-stream failure (stderr-only diagnostic text) lands in
  `PixiUploadResult.stdout`; zero-returncode success returns `PixiUploadResult(returncode=0, ...)`
  with no reference/URL field to assert (none exists).
- [x] `tests/unit/test_errors.py` -- both new classes: identifier, message content, `__reduce__`
  round-trip (deepcopy/pickle), empty-`missing`/non-str-`missing`-item rejection for
  `ShipChannelCredentialMissingError`.
- [x] `tests/unit/test_package.py` -- `ship_channel`: missing-credential case raises before
  `build`/`pixi.upload` are called (mock both, assert not called); happy path (mocked `build`/
  `upload`, correct `ShipTargetResult` with `target="channel:<name>"`, `state=TERMINAL`,
  `reference=<name>`); build-produced-no-conda path (`FAILED`, `pixi.upload` not called); upload-
  failure path (`FAILED`, `reference=None`, `pixi.upload` was called -- proving the rejection is
  data, not a raised exception, and a second call for a different target would be unaffected);
  `EngineAbsentError`/`PackageVersionMismatchError`/`PackageProjectPathError` from `build()`
  propagate un-caught; default `target="library"`.

**Acceptance Criteria:**
- Given the `channel:<name>` target with a valid `PREFIX_API_KEY` and a built `.conda` artifact,
  when `ship_channel` executes, then `engines.pixi.upload` is called with the built `conda_path` and
  the channel name, and the result is a `ShipTargetResult` with `state=TERMINAL`,
  `target="channel:<name>"`, and `reference=<name>`.
- Given missing `PREFIX_API_KEY`, when `ship_channel` is called, then
  `ShipChannelCredentialMissingError` is raised before `build()` or `engines.pixi.upload()` are
  ever called.
- Given credentials present, when `ship_channel` runs, then no credential value is read into any
  variable beyond the presence check, stored on the returned object, or passed as an explicit `env=`
  override -- the subprocess inherits it via the normal, un-mutated process environment.
- Given no CFE installation anywhere, when `ship_channel` runs (with `pixi`/`build` present), then
  it succeeds -- `package.py` carries no `cfe` reference of any kind.
- Given a channel that rejects the upload, when `ship_channel` processes the nonzero result, then it
  returns a `FAILED` `ShipTargetResult` without raising, so a caller shipping to other targets in
  the same invocation is unaffected by this one's failure.

## Spec Change Log

### 2026-08-13 — review pass 1, bad_spec repair
- **Triggering finding:** the spec's own `argv` construction for `engines.pixi.upload()` --
  originally `["pixi", "upload", conda_path, "prefix", "--channel", channel_name]` (file
  positioned BEFORE the `prefix` subcommand token), asserted in the Intent's Approach line, the
  Always boundary, and the Tasks & Acceptance execution item -- is factually wrong. Re-verified
  live (2026-08-13) against the installed `pixi 0.76.2`: `pixi upload <file> prefix --channel
  <name>` fails immediately with clap's own `error: unexpected argument '--channel' found` (the
  file is greedily consumed as a second package-file positional, so `prefix` never registers as
  the subcommand); the CORRECT order, which the spec's own Design Notes section had already
  (correctly) quoted as a repro command without the Always-boundary/Tasks text matching it, is
  `pixi upload prefix --channel <name> <file>` -- subcommand and flags first, the
  `[PACKAGE_FILES]...` positional last, per `pixi upload prefix --help`'s own `Usage:` line. The
  wrong order made `ship_channel()`/`engines.pixi.upload()` completely non-functional against the
  real tool -- every invocation would exit 2 on a CLI parse error before ever attempting an
  upload, so none of Story 3.5's acceptance criteria were reachable in production as first
  implemented. Caught by an independent adversarial review pass that live-tested the exact argv
  the code constructed.
- **What was amended:** corrected the argv token order to `["pixi", "upload", "prefix",
  "--channel", channel, conda_path]` everywhere it was asserted (Intent Approach line, Always
  boundary bullet, Tasks & Acceptance execution item), and added an explicit re-verification note
  to the Always boundary bullet recording both the failing and passing live transcripts so this
  exact class of error is falsifiable on inspection, not just asserted.
- **Known-bad state avoided:** a spec that reads as fully "live-verified" (and even quotes a
  correct repro command in its own Design Notes) while embedding an untested, wrong argv
  construction in the sections that actually drive implementation (Always boundary, Tasks) -- the
  prior pass's implementation subagent, and its own tests, faithfully reproduced and then locked
  in the wrong order because nothing in the spec or the test suite exercised the real CLI's
  parsing rules.
- **KEEP instructions (verified correct in the reverted implementation, must survive
  re-derivation unchanged):** the overall `ship_channel()` control flow (credential-presence
  check before `build()`, unconditional `build()` reuse, `FAILED` short-circuit on
  `conda_path is None`, `TERMINAL`/`FAILED` mapping on `upload()`'s returncode as DATA never
  raised); `PixiUploadResult`'s two-field shape (`returncode`, `stdout`) with NO `url`/`reference`
  field; `stderr=subprocess.STDOUT` merged-stream capture (independently correct and unaffected
  by the argv bug); no `--api-key` flag and no `env=` override; the two new dedicated error
  classes (`ShipChannelCredentialMissingError`, `ShipChannelUploadTimeoutError`) rather than
  reusing the PyPI-worded ones; `reference` on success being the bare `channel_name`, never a
  constructed URL; the test suite's overall breadth and structure (only the hardcoded argv
  assertion inside `test_upload_invokes_pixi_upload_prefix_with_the_documented_argv` needs its
  expected list corrected to match, everything else in that test file, `test_errors.py`'s two new
  suites, and `test_package.py`'s `ship_channel` suite was sound and should be re-derived
  identically).

## Review Triage Log

### 2026-08-13 — Review pass 1
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 2: (high 0, medium 0, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[bad_spec]` `engines.pixi.upload()`'s constructed `argv` placed the `.conda` file
    path BEFORE the `prefix` subcommand token, which the real `pixi 0.76.2` CLI rejects with a
    clap parse error (`unexpected argument '--channel' found`) before ever reaching the upload
    logic -- confirmed by live-testing both orders against the installed binary. Root cause was in
    the spec itself (the Intent Approach line, Always boundary, and Tasks & Acceptance all
    asserted the wrong order, despite the spec's own Design Notes quoting a correctly-ordered
    repro command elsewhere) -- see `## Spec Change Log` for the full repair. Code reverted; step-03
    will re-derive from the corrected spec.
- **Other findings, not actioned this pass** (bad_spec present, so patch/defer/reject processing
  -- including minting any deferred-work-ledger entry -- is moot per this workflow's cascading
  rule; every finding below is recorded here only, to be re-triaged fresh on the next review pass
  after re-implementation):
  - `[low]` `[defer]` `engines.pixi.upload()` builds `argv` with `conda_path`/`channel` as bare
    positional/flag values, with nothing to stop a `channel_name` starting with `-`/`--` from
    being misparsed as a flag by pixi's own clap-based CLI instead of the intended `--channel`
    value (Edge Case Hunter finding).
  - `[low]` `[patch]` `models.py::ShipTargetResult`'s docstring still reads "a URL, PR number, or
    branch URL" and was not updated for the new bare-channel-name `reference` shape this story
    introduces.
  - `[low]` `[patch]` `engines.pixi.upload()` catches `subprocess.TimeoutExpired` but not `OSError`
    -- `engines.pixi.build()` in the same file DOES catch `OSError` (translating it to
    `PackageProjectPathError`) for the analogous TOCTOU race between `require_engine`'s probe and
    the actual spawn; `upload()` has no equivalent, so a raw `OSError` could escape as a
    non-`MasonError`.
  - `[low]` `[reject]` `ship_channel()`'s success `reference` merely echoes the caller-supplied
    `channel_name` rather than surfacing new information from the upload itself -- matches this
    spec's own Design Notes, which deliberately rejected parsing an unverified output format
    rather than inventing one.
  - `[low]` `[reject]` `ship_channel()` performs no validation of `channel_name` itself -- matches
    established precedent: `parse_ship_targets()` owns that validation at the parse boundary, and
    no ship-target function in this codebase (`ship_pypi` included) re-validates its own
    already-parsed inputs.
  - `[low]` `[reject]` the `PREFIX_API_KEY`-presence precondition is stricter than `pixi upload
    prefix` itself (which also accepts `pixi auth login`'s stored keychain/auth-file) -- matches
    this spec's own explicit Never boundary: Mason's credential-blindness model (AD-14) is
    deliberately env-var-presence-only, not a general "would the tool succeed?" oracle.
  - `[low]` `[reject]` `build()` unconditionally builds both the wheel/sdist and the `.conda`
    package even for a channel-only ship, so a missing `build`-engine dependency can block an
    otherwise-ready channel ship -- this is the exact, already-tracked `DW-3-4-1` (Story 3.4's
    ledger), not a new finding; root-caused in Story 3.2's `build()`, out of this story's scope.
  - `[low]` `[reject]` the merged `stdout`+`stderr` capture is not scrubbed for any secret `pixi`
    might echo into its own diagnostic text -- matches `twine.py::upload()`'s identical
    unscrubbed-capture precedent; no live evidence either tool ever echoes a credential value.
  - `[low]` `[reject]` `_PIXI_UPLOAD_TIMEOUT_SECONDS = 300.0` is an unmeasured, copy-pasted
    allowance from `twine.py` -- matches `twine.py`'s own identically unmeasured 300s rationale;
    no new rigor gap introduced by this story.
  - `[low]` `[reject]` the two new error classes near-duplicate their PyPI siblings instead of a
    single parameterized class -- matches this codebase's consistent, deliberate one-class-per-
    condition convention (every class in `errors.py` is dedicated, none are generic/parameterized).
  - `[low]` `[reject]` `subprocess.TimeoutExpired`'s partial captured output is discarded when
    translating to `ShipChannelUploadTimeoutError` -- matches `engines.twine.upload`'s and
    `engines.pixi.build`'s own identical pre-existing handling; not a gap this story introduces.
  - `[low]` `[reject]` a "nothing built" `FAILED` result can carry `pixi_stdout` text that reads
    as a successful build -- matches `ship_pypi()`'s own identical pre-existing pattern
    (`pep517_stdout` under the same condition); not novel to this diff.
  - `[low]` `[reject]` `engines.pixi.upload()` performs no type/emptiness validation on its own
    parameters -- matches every other engine adapter in this codebase (`pep517.build`,
    `pixi.build`, `twine.upload`), none of which self-validate; the caller's responsibility by
    established convention.

### 2026-08-13 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 2: (high 0, medium 0, low 2)
- reject: 8: (high 0, medium 0, low 8)
- **Note:** the argv-order fix (pass 1's `bad_spec` repair) was independently re-verified live
  against the installed `pixi 0.76.2` binary by both reviewers this pass -- confirmed genuinely
  fixed. Not a new finding, not counted below.
- addressed_findings:
  - `[low]` `[patch]` `models.py::ShipTargetResult`'s docstring still read "a URL, PR number, or
    branch URL" with no mention of the new bare-channel-name `reference` shape this story
    introduces -- fixed: added "or channel path" plus a pointer to `engines.pixi`'s own module
    docstring for why no URL is parsed.
  - `[low]` `[patch]` `engines.pixi.upload()` caught `subprocess.TimeoutExpired` but not `OSError`
    -- unlike `engines.pixi.build()` in the same file, which translates an `OSError` from its own
    `cwd=project_path` spawn to `PackageProjectPathError`. `upload()` passes no `cwd=`, so the only
    realistic `OSError` cause is `pixi` itself vanishing/losing exec permission between
    `require_engine`'s probe and this call's separate spawn -- the same condition `require_engine`
    itself raises `EngineAbsentError` for. Fixed: added `except OSError: raise
    EngineAbsentError(name, name) from None`, plus
    `test_upload_translates_oserror_to_engine_absent_error` mirroring `build()`'s own
    `test_build_translates_oserror_from_a_bad_cwd_to_package_project_path_error` pattern.
  - `[low]` `[patch]` PRD `OQ-2`, architecture spine `OQ-A2`, and epics `OQ-E2` all still read as
    open questions ("`pixi publish` or `anaconda upload`?") despite this story's own spec having
    resolved the choice via live investigation -- none carried a `RESOLVED` annotation matching the
    repo's own precedent (`OQ-E5`). Fixed: all three now read `RESOLVED 2026-08-13`, citing this
    story's spec and summarizing the `prefix`-subcommand reasoning.
- **Deferred** (both minted against the tracked station `pyforge-mason`, base id `DW-3-5`; full
  entries in `deferred-work.md`):
  - `[low]` `[defer]` **`DW-3-5-1`** -- `engines.pixi.upload()`'s argv has no `--` separator, so a
    `channel_name` starting with `-`/`--` is misparsed by pixi's own clap CLI instead of reaching
    `--channel` (live-verified this pass: `pixi upload prefix --channel -evil fake.conda` fails
    with clap's own `unexpected argument '-e' found`). Not blocking: no CLI wiring exists yet
    (Story 3.9's scope) to reach this path in v1.
  - `[low]` `[defer]` **`DW-3-5-2`** -- `engines.pixi.upload()` sets no `stdin=subprocess.DEVNULL`,
    unlike `twine.py`'s documented interactivity defense against a spawned child blocking on a
    stdin prompt for the full timeout window. Unverified whether `pixi upload prefix` ever actually
    prompts (would require reproducing a real upload collision); risk is real by analogy, not by
    direct reproduction.
- **Other findings, rejected** (all low severity, each matching an established precedent already
  documented in this spec, this story's own code, or a sibling story's code):
  - `[low]` `[reject]` the credential-presence gate (`PREFIX_API_KEY`) is stricter than `pixi
    upload prefix` itself, which also accepts `pixi auth login`'s stored keychain/auth-file --
    matches this spec's own explicit Never boundary (AD-14 credential-blindness is deliberately
    env-var-presence-only).
  - `[low]` `[reject]` no opt-in/`shutil.which`-gated integration test exists to catch a future real
    `pixi` CLI release silently reordering/renaming `upload prefix`'s own arguments -- matches
    AD-16's established exemption and every sibling engine adapter's identical mocked-only test
    convention.
  - `[low]` `[reject]` the success-path `reference` (`channel_name`) conveys no new information
    beyond what the caller already supplied -- matches this spec's own Design Notes, which
    deliberately rejected inventing an unverified URL format instead.
  - `[low]` `[reject]` `ShipChannelCredentialMissingError`'s validation logic is a near-verbatim
    copy of `ShipCredentialMissingError`'s (~15 lines) rather than a shared helper -- matches this
    codebase's consistent one-class-per-condition convention (no error class in `errors.py` shares
    validation logic via a helper; each is independently written and independently tested).
  - `[low]` `[reject]` the "live-verified" missing-credential diagnostic quoted in the module
    docstring is a close paraphrase, not a verbatim reproduction, of the reviewer's own live output
    -- cosmetic; "live-verified" is used throughout this codebase to mean "tested against the real
    tool," never a verbatim-quote contract, and the merged-stream design tolerates any stderr text
    regardless.
  - `[low]` `[reject]` `build()` unconditionally builds both the wheel/sdist and the `.conda`
    package even for a channel-only ship -- the exact, already-tracked `DW-3-4-1` (Story 3.4's
    ledger); not a new finding.
  - `[low]` `[reject]` `resolved_timeout` guards only `None`, not `0`/negative -- matches the
    identical unguarded pattern already present in `engines.pep517.build`, `engines.pixi.build`,
    and `engines.twine.upload`; not novel to this diff.
  - `[low]` `[reject]` `ship_channel()`'s `environ.get(name, "").strip()` would raise a raw
    `AttributeError` if a caller passed `environ[name] = None` -- matches Story 3.4's own
    identically-shaped `ship_pypi()` pattern, explicitly reviewed and rejected there ("no current
    caller passes anything but a `str`... this story adds no CLI wiring at all"); the identical
    reasoning applies here since `ship_channel` also has no CLI wiring yet.

## Design Notes

**Why `prefix`, not `anaconda`/`artifactory` (OQ-E2):** live `pixi upload --help`/`pixi upload
prefix --help` inspection (pixi 0.76.2, matching the pinned `>=0.76.2,<0.77` range) shows `prefix`
is the only subcommand whose destination is a single `--channel <CHANNEL>` value -- `anaconda`
additionally requires `--owner`, and `artifactory` requires `--url`; neither maps cleanly onto a
bare `channel:<name>` token without inventing a syntax the vocabulary (Story 3.3) does not have.
`pixi publish` (the other candidate the epic's market research named) was ruled out separately: it
BUILDS a package from a workspace manifest rather than uploading an already-built file, which
would duplicate `build()` (FR-15) instead of reusing it.

**Why stdout+stderr are merged:** a live repro (`pixi upload prefix --channel x
nonexistent.conda` with no `PREFIX_API_KEY` set) wrote its entire error text to stderr and nothing
to stdout:
```
$ pixi upload prefix --channel test-channel /nonexistent-file.conda
stdout: (empty)
stderr: Error:   x no prefix.dev API key provided and none found in keychain
```
Keeping `engines.pixi.upload()`'s result to one text field (matching `TwineUploadResult`/
`PixiBuildResult`'s own single-`stdout`-field shape) requires merging streams at the subprocess
boundary (`stderr=subprocess.STDOUT`) rather than adding a second field no sibling adapter has.

**Why `reference` is the bare channel name, not a URL:** `twine.upload`'s `reference` is a URL
scraped from a verified, live-observed `"View at:"` stdout block. No equivalent live-verified
success-path output exists for `pixi upload prefix` (exercising it needs a real API key, channel,
and network access, out of reach during spec authoring) -- inventing a `https://prefix.dev/...`
URL format here would be a guess presented as fact. `channel_name` is the one value guaranteed
correct.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: all unit + meta tests pass (default
  `-m "not slow"` loop); no real `pixi upload` network call occurs anywhere in this suite (all
  `subprocess.run` calls mocked, matching `test_engines_twine.py`/`test_engines_pixi.py`'s own
  convention).

## Auto Run Result

Status: done

**Summary:** Implemented and reviewed in the prior session (commit `719abc8d23`, two review passes:
pass 1 found and repaired a `bad_spec` argv-order defect, pass 2 found and fixed 3 low patches). That
session's own bmad-loop landing gate (`scripts/spec_surface_reconcile.py`, the S-13.7 spec-surface
drift check) then failed deterministic verification because the story commit landed with no matching
entry in the owning Spec's `.memlog.md` (`_bmad-output/projects/pyforge-mason/planning-artifacts/
specs/spec-pyforge-mason/.memlog.md`) -- a recurring, previously-documented pattern for this Spec (see
that memlog's S-3.1/S-3.2/S-3.3/S-3.4 entries), not a defect in the story's code or intent contract.
This resume repaired it by reconciling: named the seven changed paths in `.memlog.md` and re-stamped
the drift baseline (`python scripts/spec_surface_check.py --write-baseline --spec
pyforge-mason/spec-pyforge-mason`), matching the exact procedure every prior mason story in this Spec
used. No production or test code changed in this pass, and `<intent-contract>` was not touched.

**Files changed (this repair pass only):**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` -- new
  `(change)`/`(event)` entries naming Story 3.5's seven governed paths.
- `scripts/.spec-surface-baseline.json` -- re-stamped for `pyforge-mason/spec-pyforge-mason` only
  (scoped `--spec`, no other Spec's pending drift accepted).

**Review findings (from the prior session's two passes, unchanged by this repair):** 1 bad_spec
(pass 1, repaired -- argv order), 3 patch (pass 2, low, fixed), 2 deferred (`DW-3-5-1`, `DW-3-5-2`,
low), 18 rejected across both passes. See `## Review Triage Log` and `## Spec Change Log`.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0 (`OK: every tracked file governed or
  allowlisted; no drift`); previously failed with 7 gating `[drift]` findings against this Spec.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1163 passed, 1 deselected. No regression.
- Reconciliation commit `907cc97ece` on top of the story commit `719abc8d23`, both on
  `bmad-loop/20260813-145934-3eb0/3-5-the-channel-name-ship-target`. Not pushed.

**Residual risks:** None new. `DW-3-5-1` (no `--` separator ahead of `channel_name`/`conda_path`,
misparsed by pixi's clap CLI if either starts with `-`/`--`) and `DW-3-5-2` (no
`stdin=subprocess.DEVNULL` isolation) remain open on the deferred-work ledger; neither is reachable
in v1 since no CLI wiring exists yet (Story 3.9's scope).

