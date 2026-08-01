<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.9: Packaging, distribution, and version reporting'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: 'e3ec7d7a6418aa25186b2d36f1779cf869d04f71'
final_revision: '5718ea775e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pyforge-marshal`'s conda/wheel packaging already declares `bmad-loop` as a pinned run dependency and passes AD-3's import-linter contracts, but `marshal --version` still reports only Marshal's own hand-synced literal, `marshal preflight`'s harness-version check blocks on ANY deviation from the exact pinned range with no warn-only tier, the declared-range logic lives in `cli/init.py` instead of the harness seam FR-52 says must declare it, and the `pyforge-marshal` pixi environment has never resolved (or been smoke-tested) on osx-arm64 or explicitly declared Windows as WSL-first.

**Approach:** Extend `marshal --version` to also resolve and print the harness's version (bypassing the envelope, matching the existing doctor-mirrored precedent), relocate the harness-version-range logic into `adapters/harness_bmadloop.py` and graduate it into two tiers (same-major-out-of-range warns without blocking; undeterminable-or-different-major blocks preflight), and round out packaging with an osx-arm64 build+smoke path and an explicit WSL-first Windows declaration.

## Boundaries & Constraints

**Always:**
- `marshal --version` (still bypassing the envelope/finding machinery, per the module's own existing precedent -- mirrors `pyforge-doctor`) prints Marshal's own version (unchanged `__version__` literal) AND the resolved harness version (or a clear "not determined" state), still exits `EXIT_OK` in every case -- `--version` never blocks, it only informs.
- The harness-version-range constants (`_HARNESS_MIN_VERSION`, `_HARNESS_MAX_MINOR_EXCLUSIVE`, `_HARNESS_VERSION_RANGE_TEXT`) and the parsing/range functions move from `cli/init.py` into `adapters/harness_bmadloop.py` (FR-52: "the seam declares the harness version range it supports") -- `cli/init.py` imports them from there instead of defining its own copies. A new `harness_version_is_major_mismatch(text: str | None) -> bool` function lives alongside them: `True` for `None`/unparseable input or a parsed major-version component that differs from `_HARNESS_MIN_VERSION[0]`; `False` for any other determinable version (even one outside the declared minor range).
- `run_preflight`'s harness-version check graduates: `harness_version is None` or `harness_version_is_major_mismatch(harness_version)` -> `MRS-PREFLIGHT-002` (`Verdict.ERROR`, blocking, unchanged tier); a determinable, same-major version that fails `harness_version_in_range` -> the new `MRS-PREFLIGHT-011` (`Verdict.WARN`, non-blocking -- exits via the existing WARN->0 lattice mapping) instead. Both codes' messages name the actual version and the declared range; findings already render with their severity tag (`_render_text_preflight`), which IS the "prominent warning" FR-57 asks for -- no new rendering mechanism needed.
- `--version`'s own output prints the same kind of prominent warning line whenever the harness is undeterminable or outside the declared range (both tiers) -- it never blocks (it isn't a gate), it only surfaces the same fact preflight would enforce.
- `pyforge-marshal`'s pixi feature gains a smoke task (name mirrors `pyforge-marshal-build-conda`/`-build-dist`: `pyforge-marshal-smoke`) that proves FR-56's "installing it yields a working `marshal --help` with the harness resolvable" against the SAME `pyforge-marshal` pixi-build-python-installed environment (no separate throwaway env -- that environment already installs the real built conda artifact plus its pinned `bmad-loop` run-dependency).
- `pixi.lock` is regenerated so the `pyforge-marshal` environment resolves for `osx-arm64-min` (today it resolves only `linux-64`/`win-64` -- confirmed empirically, not merely undeclared) in addition to the existing platforms; build/smoke task descriptions and the package README name linux-64 and osx-arm64 as the supported build/smoke targets and state Windows is WSL-first (a documentation-level declaration, not a platform-list removal -- see Never).
- Per the repo's own PR-gate convention (root `CLAUDE.md`): since this story edits `pixi.toml`, `environment.yaml` is regenerated (`pixi project export conda-environment -e build > environment.yaml`) before the change is considered complete.

**Block If:**
- `pixi lock`/`pixi install -e pyforge-marshal` cannot resolve `osx-arm64-min` for the `pyforge-marshal` environment due to a genuine, non-trivial dependency conflict (e.g. a pinned transitive dependency ships no `osx-arm64-min`-compatible build on `conda-forge`/`SelfExplainML`) -- HALT naming the specific unresolvable package rather than loosening pins or dropping dependencies unilaterally.

**Never:**
- Never remove `win-64` from `[feature.pyforge-marshal]`'s resolved platforms -- it already resolves today (confirmed in `pixi.lock`) and no evidence gathered during planning shows removing it is required beyond the documentation-level WSL-first statement; that is a larger, separate decision this story does not need to make.
- Never touch `__version__`'s hand-synced-literal mechanism in `cli/main.py` (its existing safety-net test) -- out of this story's surface; only the harness-version reporting alongside it is new.
- Never implement the run journal or a "both versions appear in the journal" write -- `core/journal.py` does not exist yet (Epic 3, Stories 3.1/3.2). Log this as deferred work rather than fabricating a journal write path two epics early.
- Never touch `pyproject.toml`'s dependency list or `[tool.importlinter]` contracts -- both already declare `bmad-loop>=0.9.0,<0.10` as a run dependency and the AD-3/AD-4 contracts correctly (verified during planning); nothing there needs to change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `marshal --version`, harness in range | `bmad-loop --version` resolves to `0.9.3` | Prints Marshal's version and `bmad-loop 0.9.3`, no warning line, exit 0 | n/a |
| `marshal --version`, harness minor-out-of-range | resolves to `0.10.2` | Prints both versions plus a prominent warning naming the range, exit 0 | n/a |
| `marshal --version`, harness undeterminable | binary absent or `--version` fails | Prints Marshal's version and a "harness not determined" line plus the same warning, exit 0 | n/a |
| `marshal preflight`, harness minor-out-of-range | e.g. `0.10.2` | `MRS-PREFLIGHT-011` (`warn`), all other checks proceed normally, exit 0 if nothing else fails | n/a |
| `marshal preflight`, harness major mismatch | e.g. `2.0.0` or unparseable | `MRS-PREFLIGHT-002` (`error`), blocking, exit non-zero | n/a |
| `marshal preflight`, harness undeterminable | binary present, `--version` fails | `MRS-PREFLIGHT-002` (`error`), unchanged from today | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT: gains the relocated `_HARNESS_MIN_VERSION`/`_HARNESS_MAX_MINOR_EXCLUSIVE`/`_HARNESS_VERSION_RANGE_TEXT` constants and `harness_version_tuple`/`harness_version_in_range` (moved from `cli/init.py`, same behavior) plus the new `harness_version_is_major_mismatch`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py` -- EDIT: drop the local range constants/functions (import from `adapters/harness_bmadloop.py` instead); graduate `run_preflight`'s harness-version block to emit `MRS-PREFLIGHT-002` (major mismatch/undeterminable) vs the new `MRS-PREFLIGHT-011` (minor mismatch, warn).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py` -- EDIT: `--version` resolves and prints the harness version via `adapters.harness_bmadloop.BmadLoopHarness` (module-level reference, monkeypatchable in tests) plus the prominent-warning line when out of range/undeterminable; `__version__`'s own mechanism is untouched.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` -- EDIT: register `MRS-PREFLIGHT-011`, extend the module docstring's Story 1.7 paragraph noting the graduated tiers.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- EDIT: classify `MRS-PREFLIGHT-011` as `Verdict.WARN`, extend the module docstring correspondingly.
- `src/shared/packages/pyforge-marshal/README.md` -- EDIT: add a short Platforms note (linux-64/osx-arm64 build+smoke targets, Windows WSL-first) and the new `pyforge-marshal-smoke` command line.
- `pixi.toml` (root) -- EDIT: add `[feature.pyforge-marshal.tasks.pyforge-marshal-smoke]` (`marshal --help && marshal --version`); extend the existing build/test task descriptions to name linux-64/osx-arm64; add a comment declaring the Windows-WSL-first stance.
- `pixi.lock` (root) -- EDIT (regenerated): `pyforge-marshal` environment gains an `osx-arm64-min` (`osx-arm64` subdir) resolution alongside its existing `linux-64`/`win-64` entries.
- `environment.yaml` (root) -- EDIT (regenerated): `pixi project export conda-environment -e build > environment.yaml`, per the repo's own PR-gate convention for any `pixi.toml` change.
- `tests/unit/test_cli.py` -- EXTEND: cover `--version`'s harness-version reporting across in-range/minor-mismatch/major-mismatch/undeterminable, via a monkeypatched harness.
- `tests/unit/test_init.py` -- EXTEND/UPDATE: rewrite the existing `0.10.2` outside-range test to expect `MRS-PREFLIGHT-011`/`warn`/exit 0; add a genuine major-mismatch test expecting `MRS-PREFLIGHT-002`; extend `test_preflight_finding_codes_classify_as_documented` to assert `MRS-PREFLIGHT-011` classifies `Verdict.WARN`.
- `tests/unit/test_findings.py` -- EDIT: add `MRS-PREFLIGHT-011` to the hardcoded `REGISTERED_CODES` equality assertion.
- `tests/unit/test_harness_bmadloop_preflight.py` -- EXTEND: unit-test the relocated `harness_version_tuple`/`harness_version_in_range`/new `harness_version_is_major_mismatch` directly at their new home.

## Tasks & Acceptance

**Execution:**
- [x] `adapters/harness_bmadloop.py` -- relocate range constants/functions from `cli/init.py`, add `harness_version_is_major_mismatch`
- [x] `cli/init.py` -- import the relocated functions; graduate the preflight harness-version block into the two-tier `MRS-PREFLIGHT-002`/`MRS-PREFLIGHT-011` split
- [x] `cli/main.py` -- `--version` resolves and prints the harness version plus a prominent out-of-range/undeterminable warning
- [x] `core/findings.py`, `core/verdict.py` -- register + classify `MRS-PREFLIGHT-011`
- [x] `pixi.toml` (root) -- add `pyforge-marshal-smoke`, extend build/test task descriptions, declare the Windows-WSL-first stance
- [x] Verify `pyforge-marshal` resolves `osx-arm64-min` -- already true (`pixi.lock`'s `p1:` alias = `osx-arm64`; a literal `osx-arm64:` grep is a false negative against pixi's lock-v7 aliasing); no `pixi.lock`/`environment.yaml` change needed
- [x] `README.md` -- add the Platforms note + the new smoke command
- [x] Update/extend the six listed test files per the Code Map

**Acceptance Criteria:**
- Given the package source, when the conda artifact is built via `pyforge-marshal-build-conda` and installed into the `pyforge-marshal` pixi environment, then `pyforge-marshal-smoke` runs `marshal --help` successfully with the harness resolvable
- Given a resolvable, same-major, out-of-declared-minor-range harness version, when `marshal preflight` runs, then it reports `MRS-PREFLIGHT-011` at `warn` severity and does not block (exit 0 absent other findings)
- Given an undeterminable or different-major harness version, when `marshal preflight` runs, then it reports `MRS-PREFLIGHT-002` at `error` severity and blocks (non-zero exit)
- Given any harness state, when `marshal --version` runs, then it prints both Marshal's version and the resolved (or "not determined") harness version and always exits 0
- Given `pixi.lock` is regenerated, then the `pyforge-marshal` environment resolves for both `linux-64` and `osx-arm64-min`
- Given `pixi.toml` changed, then `environment.yaml` is regenerated and committed alongside it

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 1, low 4)
- defer: 1: (low 1)
- reject: 3: (low 3)
- addressed_findings:
  - `[high]` `[patch]` Switching `--version` from argparse's built-in `action="version"` to a plain `store_true` flag checked after `parse_args()` returned broke the universal "`--version` always wins" convention: `marshal --version init` (missing `init`'s required `slug`) and `marshal --version --bogus` both started exiting `2` with a usage error instead of printing the version, since a `store_true` flag is only inspected after the ENTIRE argv has been validated. Independently caught by both Blind Hunter and Edge Case Hunter, and reproduced live. Fixed with a custom `_VersionAction(argparse.Action)` (`nargs=0`) that fires the instant `--version` is consumed during parsing and calls `parser.exit()` itself -- the same mechanism the built-in version/help actions use -- restoring the short-circuit while still computing the harness-inclusive text dynamically. Tests: `test_version_wins_over_a_subcommand_missing_its_required_argument`, `test_version_wins_over_an_unrecognized_trailing_flag`.
  - `[medium]` `[patch]` The new `pyforge-marshal-smoke` pixi task chained `marshal --help && marshal --version`, but `--version` always exits 0 regardless of harness state (informational, never a gate per this story's own Boundaries) -- so the task's stated purpose ("proves the harness is resolvable") was never actually enforced by its own exit code; it would report success even against a completely unresolvable `bmad-loop`. Changed the task's `cmd` to grep `--version`'s output for a real `bmad-loop <version>` line (`marshal --version | tee /dev/stderr | grep -qE '^bmad-loop [0-9]'`), giving the smoke gate genuine pass/fail signal without changing `--version`'s own never-blocks contract. Verified live against the installed artifact.
  - `[low]` `[patch]` `adapters/harness_bmadloop.py`'s new module docstring and `harness_version_tuple`'s own docstring both claimed `cli/main.py` calls `harness_version_is_major_mismatch`/`harness_version_tuple` directly -- it doesn't; `cli/main.py` only imports `harness_version_in_range` (and, for the unparseable-vs-out-of-range distinction added in this same pass, `harness_version_tuple`, but not `harness_version_is_major_mismatch`, which stays `run_preflight`'s alone). Corrected both docstrings to name the actual caller of each function precisely.
  - `[low]` `[patch]` `run_preflight`'s harness-version check read `if harness_version is None or harness_version_is_major_mismatch(harness_version):` -- redundant, since `harness_version_is_major_mismatch(None)` already returns `True` by its own implementation. Simplified to `if harness_version_is_major_mismatch(harness_version):` (behavior unchanged, confirmed by the full suite still passing).
  - `[low]` `[patch]` `HARNESS_VERSION_RANGE_TEXT` kept its private, underscored name (`_HARNESS_VERSION_RANGE_TEXT`) despite being imported cross-module into both `cli/init.py` and `cli/main.py` -- inconsistent with `harness_version_tuple`/`harness_version_in_range`, both explicitly made public in this same relocation for the identical reason. Renamed to public `HARNESS_VERSION_RANGE_TEXT` across all three files (`_HARNESS_MIN_VERSION`/`_HARNESS_MAX_MINOR_EXCLUSIVE` correctly stay private -- neither is imported elsewhere).
  - `[low]` `[patch]` `cli/main.py`'s `_version_text()` printed "is outside the supported range" for a harness version that could not be PARSED at all (e.g. `"dev"`), conflating "unparseable" with "numerically outside the declared range" -- the exact wording precision this story's graduated-tier work was meant to sharpen. Added a `harness_version_tuple(...) is None` check ahead of the range check so the warning names the actual problem ("could not be parsed" vs "is outside the supported range"). Test: `test_version_harness_unparseable_shows_could_not_be_parsed_warning` (rewritten from the prior pass's looser assertion).
- deferred: 1 -- `src/shared/packages/pyforge-marshal/README.md`'s top "Status" blurb ("build skeleton (Story 1.1) ... No real command exists yet") has been stale since Story 1.4 shipped real subcommands; pre-existing across five prior stories, not caused by this one, and a full README rewrite was outside this story's declared surface. Logged to `deferred-work.md`.
- rejected as already-adjudicated or expected feature behavior, not defects: FR-57's "both versions appear in the journal for every run" is silently unimplemented -- correct and intentional, per this spec's own `Never` boundary and Design Notes (`core/journal.py` doesn't exist until Epic 3's Story 3.1/3.2); `--version` now shells out to `bmad-loop --version` (up to a 5s timeout) instead of returning instantly -- inherent to the feature this story was asked to build (report the resolved harness version), not a regression, and the timeout is the same one `run_preflight` already uses; NFR-13's Windows-WSL-first declaration is prose-only (a `pixi.toml` comment + README section) rather than an enforced platform-list removal -- a deliberate, reasoned trade-off already stated in this spec's own `Never` boundary (removing `win-64` from resolution was explicitly out of scope without further evidence it's required).

### 2026-07-31 — Follow-up review pass (independent, post-done)
- intent_gap: 0
- bad_spec: 0
- patch: 10: (medium 1, low 9)
- defer: 0
- reject: 7: (low 7)
- addressed_findings:
  - `[medium]` `[patch]` The relocated harness-range constants (`_HARNESS_MIN_VERSION`/`_HARNESS_MAX_MINOR_EXCLUSIVE`/`HARNESS_VERSION_RANGE_TEXT`) had no sync test against the `bmad-loop>=0.9.0,<0.10` pin in `pyproject.toml` they exist to mirror -- a pin bump would leave preflight blocking (or wrongly passing) the exact harness version the package itself installs, with every test green. This was ALREADY a Story-1.7 deferred-work ledger entry, parked there because fixing it needed "a deliberate design choice about where the ONE source of truth should live" -- which Story 1.9 made (FR-52: the seam declares the range), so the guard became a straightforward patch: added `test_harness_range_constants_match_pyproject_dependency_pin` to `tests/meta/test_manifest_sync.py` (pins pyproject's spec == `HARNESS_VERSION_RANGE_TEXT` == the two tuple constants; pixi.toml is covered transitively by the existing cross-check). The pre-existing ledger entry was left untouched for the orchestrator to disposition.
  - `[low]` `[patch]` `run_preflight`'s `MRS-PREFLIGHT-002` message still committed the exact conflation the prior pass fixed in `--version`: `'dev'`/undetermined reported as "outside the supported range". Split the message three ways (could not be determined / could not be parsed / different major version), imported `harness_version_tuple` into `cli/init.py`, renamed the misnamed `test_preflight_harness_version_unparseable_reports_finding` (it fed `None`, i.e. undetermined) to `..._undetermined_...` with a wording assertion, and added a genuine unparseable-string (`"dev"`) preflight test asserting "could not be parsed" and blocking.
  - `[low]` `[patch]` The spec's own Never boundary and Design Notes promised a deferred-work ledger entry ("Story 3.1's journal writer must record {marshal_version, harness_version} per run once it exists") -- but no such entry was ever appended; the FR-57 journal clause had no trace outside this spec. Appended the promised entry to `deferred-work.md` as a NEW entry.
  - `[low]` `[patch]` `README.md`'s lean-environment dependency list omitted `bmad-loop` -- contradicting the smoke task added three lines above it (whose grep depends on exactly that package) and shipping as the package's long description. Added it to the run-dependencies parenthetical.
  - `[low]` `[patch]` The two new always-wins `--version` tests (and three pre-existing `--version` tests this story's change newly exposed) shelled out to the REAL `bmad-loop --version` in the fast tier, violating the package's own slow-marker convention and making assertions PATH-dependent. Added an autouse `_default_fake_harness` fixture to `test_cli.py` (default in-range fake; per-test `_patch_harness_version` overrides still win).
  - `[low]` `[patch]` Nothing test-pinned the line-anchored `^bmad-loop <digit>` output shape `pyforge-marshal-smoke`'s grep consumes -- a `_version_text` reformat would green every unit test and break the FR-56 smoke gate elsewhere. Added a `re.MULTILINE` line-anchored assertion naming the cross-artifact contract.
  - `[low]` `[patch]` `harness_bmadloop.py`'s module docstring claimed `HARNESS_VERSION_RANGE_TEXT` is imported "transitively through" `harness_version_in_range` -- false (both callers import the constant directly; constants are never available through a function import). Corrected; also restored `import tomllib` into `cli/init.py`'s stdlib import block (the dev pass had orphaned it into its own paragraph, where it read as third-party).
  - `[low]` `[patch]` `harness_version_tuple` crashed with an uncaught `ValueError` on Unicode digit characters (`"²"`: `str.isdigit()` accepts what `int()` rejects -- reproduced live), escaping the frozen exit-code domain from both `--version` and preflight for input the function does not control. Replaced `char.isdigit()` with an ASCII-only `"0" <= char <= "9"` guard + two tests.
  - `[low]` `[patch]` With write-through stdout (tty, `python -u`) a broken pipe surfaces at `_VersionAction`'s `print()` itself -- before `parser.exit()` -- and the resulting `OSError` escaped `main()`'s SystemExit/KeyboardInterrupt-only catch, violating its never-raises contract. Wrapped the print with the same `_suppress_downstream_pipe_close()` suppression `_drain_stdout` already uses for the block-buffered case.
  - `[low]` `[patch]` The "always wins, regardless of what else is on the line" docstring claim overstated `_VersionAction`'s scope: `marshal init --version` is (and was, under the built-in action) the subparser's usage error, since `--version` is root-parser-only -- unlike `--help`, which argparse auto-registers per subparser. Narrowed both docstrings to state the actual scope.
- rejected as already-adjudicated, already-ledgered, or noise: the stale README "Status" blurb (already deferred to the ledger by the prior pass -- duplicating entries is forbidden); native-win-64 smoke ergonomics, raised independently by both hunters (the spec's own Never boundary adjudicates WSL-first as documentation-level, no platform-list change); the "same-major warn tier is vacuous for a 0.x harness" design critique and its below-floor variant (a 0.8.x harness now warns instead of blocking -- both are exactly the graduated split this spec's intent contract and PRD FR-57's own wording mandate: same-major + out-of-range = warn, single possible reading); the smoke not consuming `dist-conda/`'s file (the spec's Always boundary explicitly sanctions smoking the pixi-installed environment); pre-release/PEP 440 divergence in the tuple parser (relocated "same behavior" per the spec's explicit instruction; pre-existing 1.7 semantics); and the `str`-vs-`str | None` signature asymmetry between `harness_version_in_range` and `harness_version_is_major_mismatch` (speculative future-caller hazard; the annotations declare the contract and every real call site guards).

## Design Notes

**Why a two-tier split instead of the current binary block.** PRD FR-57's own wording ("...and is a blocking preflight finding when the mismatch is major") is graduated, not binary -- today's code blocks on ANY deviation from `>=0.9.0,<0.10`. The chosen split (major-version-component differs, or undeterminable -> blocking; same-major-different-minor -> warn) is standard semver reasoning, deterministic, and reuses the version tuples already being parsed -- no fuzzy "adjacent minor" heuristic invented.

**Why relocate the range constants into the seam.** FR-52 states the seam "declares the harness version range it supports" -- today that lives in `cli/init.py`, a caller of the seam, not the seam itself. Moving it satisfies the FR literally and gives `cli/main.py`'s new `--version` behavior one shared source of truth instead of a second copy.

**Why the journal half of FR-57 is deferred, not implemented.** `core/journal.py` doesn't exist -- it's Epic 3's Story 3.1/3.2 (confirmed: `supervisor/__init__.py` is a 5-line reserved stub). Mirrors Story 1.8's own precedent for AD-29 (a documented no-op extension point rather than building two epics early): log a deferred-work entry that Story 3.1's journal writer must record `{marshal_version, harness_version}` per run once it exists.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all unit + meta tests pass, including the new/updated version and preflight-tier tests
- `pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: AD-3/AD-4 contracts still pass (relocation doesn't introduce a new `bmad_loop` reference outside the seam)
- `pixi run -e pyforge-marshal marshal --version` -- expected: prints both Marshal's and the harness's version, exit 0
- `pixi run -e pyforge-marshal pyforge-marshal-build` -- expected: conda + wheel/sdist both build from the same source tree
- `pixi run -e pyforge-marshal pyforge-marshal-smoke` -- expected: `marshal --help`/`--version` succeed against the installed artifact
- `pixi lock` -- expected: `pyforge-marshal` environment gains an `osx-arm64-min` resolution
- `pixi project export conda-environment -e build > environment.yaml` -- expected: file updates cleanly, no manual edits needed

## Auto Run Result

Status: done (follow-up review pass, 2026-07-31 -- fresh independent review of the already-`done` story per the orchestrator's re-review request).

**Summary of implemented change (this pass):** no intent-level or spec-level defects survived; two independent review subagents (adversarial + edge-case) produced 17 deduplicated findings, of which 10 were patched, 0 deferred as new code work, and 7 rejected as already-adjudicated/already-ledgered/noise. The patches harden the Story 1.9 surface without changing any tier, exit code, or API: a meta-test now pins the relocated harness-range constants to `pyproject.toml`'s `bmad-loop` pin (closing the substance of a Story-1.7 ledger entry the orchestrator still owns); `MRS-PREFLIGHT-002`'s message gained the same undetermined/unparseable/major-mismatch wording precision `--version` got last pass; `harness_version_tuple` no longer crashes on non-ASCII Unicode digits; `_VersionAction` no longer lets a write-through broken-pipe `OSError` escape `main()`'s never-raises contract; every `--version` unit test is now hermetic (autouse fake harness); the `^bmad-loop <ver>` line shape the smoke grep consumes is test-pinned; and the README/docstring inaccuracies (missing `bmad-loop` in the lean-env list, false "transitively through" import claim, overstated "always wins" scope) are corrected. The spec-promised FR-57 journal deferred-work ledger entry, which had never actually been appended, now exists.

**Files changed (commit `5718ea775e`):**
- `adapters/harness_bmadloop.py` -- ASCII-only digit guard in `harness_version_tuple`; module-docstring import-topology correction
- `cli/init.py` -- three-way `MRS-PREFLIGHT-002` message wording; `harness_version_tuple` import; `import tomllib` restored to the stdlib block
- `cli/main.py` -- `OSError` guard around `_VersionAction`'s print; "always wins" docstring scope narrowed (module + class)
- `README.md` -- `bmad-loop` added to the lean-environment dependency list
- `tests/meta/test_manifest_sync.py` -- new `test_harness_range_constants_match_pyproject_dependency_pin`
- `tests/unit/test_cli.py` -- autouse `_default_fake_harness` fixture; line-anchored smoke-contract assertion
- `tests/unit/test_harness_bmadloop_preflight.py` -- non-ASCII-digit tests
- `tests/unit/test_init.py` -- undetermined-test rename + wording assertion; new unparseable-string (`"dev"`) preflight test
- `deferred-work.md` (ledger, NEW entry only) -- the FR-57 journal-versions deferral Story 1.9's spec had promised

**Review findings breakdown:** patch 10 (medium 1, low 9) -- all fixed; defer 0 new (one NEW ledger entry appended as a patch action, existing entries untouched); reject 7 (details in the 2026-07-31 follow-up triage-log entry above).

**Follow-up review recommendation:** false -- every patch is a localized, low-consequence hardening (wording, docs, test hermeticity, two exotic-input crash guards, one meta-test); no API/behavior-tier/security/data impact, and the prior pass's six fixes all held up under two fresh adversarial reads.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 785 passed, 8 slow deselected; `lint-imports --config .../pyproject.toml --no-cache` -- AD-3/AD-4 both KEPT (42 files, 103 dependencies); live `pixi run --frozen -e pyforge-marshal marshal --version` -- prints `marshal 0.1.0` + `bmad-loop 0.9.0`, exit 0; live `pyforge-marshal-smoke` -- passes against the installed artifact. `pixi.toml` untouched this pass, so no `environment.yaml` regeneration was owed.

**Residual risks:** the graduated warn tier's semantics for a 0.x harness (same-major-but-out-of-range warns rather than blocks, including below-floor 0.8.x) are exactly what the intent contract and PRD FR-57 mandate, but both hunters independently flagged the design tension -- if bmad-loop 0.10 ships breaking renames, preflight will warn, not block; any revisit is a product/spec decision, not a code defect. The smoke task proves the pixi-installed package, not the literal `dist-conda/` file (spec-sanctioned). The stale README "Status" blurb remains ledgered for a future documentation pass.

