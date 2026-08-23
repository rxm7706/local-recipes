---
title: 'Story 10.3: The drift surfaces ambiently, never gates'
type: 'feature'
created: '2026-08-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'e49be50e3f9281654e6fff32677d9ca2ba29a09c'
final_revision: '73790c3afa'
---

<intent-contract>

## Intent

**Problem:** Story 10.1/10.2 shipped `bmad_method.gather()`'s two Findings (CAP-1 declared-vs-
installed, CAP-2 installed-vs-upstream-latest), but nothing calls it except the standalone
`bmad-method-version-drift-check` pixi task -- neither `doctor check`'s own CLI report nor
`fleet-picture`'s ATTENTION block (the two surfaces CAP-3's own success signal names) shows it, so
the exact "undetected until an operator happened to ask" blind spot this epic exists to close is
still live for anyone who doesn't remember that one pixi task.

**Approach:** Wire `Source.BMAD_METHOD_VERSION_DRIFT` into both surfaces without touching
`bmad_method.py`'s own gather logic: (1) a new opt-in `doctor check --bmad-core` category (mirrors
`--durability`'s whole-category shape) so the Finding is reachable through Doctor's own CLI/JSON
report; (2) a new subprocess-based probe in `scripts/fleet_picture.py`'s ATTENTION block that runs
`python -m pyforge.doctor.sources bmad-method-version-drift --json` and names any `warn` Finding
under `watch`.

## Boundaries & Constraints

**Always:**
- `--bmad-core` is whole-category only (no per-check NAME), dispatches straight to
  `bmad_method.gather(target)`, and is registered in `_CATEGORY_SOURCE["bmad-core"] =
  Source.BMAD_METHOD_VERSION_DRIFT` so `--scope {repo,runtime,all}` and the "explicit flag
  contradicts --scope" usage-error path (`_validate_scope_against_explicit_categories`) both cover
  it automatically -- the same mechanism `--durability` already uses.
- `--bmad-core` is NEVER included in `doctor check`'s zero-flag default run (the `if not
  run_engines and not run_env and not run_durability:` branch) -- CAP-2's own live npm-registry
  fetch (`_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0`, un-mockable, network-variable) would put NFR-4's
  hard 5-second pre-flight budget (`test_check_speed_budget.py`, ~2x headroom today, measures real
  wall-clock with no network calls in it) at direct, non-deterministic risk -- exactly the tension
  `sources/__init__.py`'s own REGISTRY comment already flags as unresolved. Keeping the category
  strictly opt-in leaves that existing budget test's guarantee completely untouched.
- `scripts/fleet_picture.py`'s new probe is a small, separately-callable function (mirrors
  `loop_home_staleness()`'s own extracted, parameterized, testable shape, not an inline-only block)
  that shells out via `sys.executable -m pyforge.doctor.sources bmad-method-version-drift --json`
  (the SAME environment fleet_picture.py itself already runs in -- the sibling
  `bmad-method-version-drift-check` pixi task lives in the same `local-recipes` feature) and
  returns only the `status == "warn"` findings; the call site in `main()` wraps it in the same
  `try/except Exception: watch.append(...)` idiom every other ATTENTION probe in this file uses
  (PR-list, baseline-drift-check, loop-home-staleness).
- The subprocess's exit code is NEVER used to detect drift (`exit_code_for` maps a WARN finding to
  `0`, same as OK -- unlike `bmad_loop_baseline_drift_check.py`'s own `returncode == 1` convention)
  -- only the parsed `--json` array's per-Finding `"status"` field decides.
- Surfaced findings land in `watch`, not `needs` -- informational/ambient, mirrors the existing
  "blocked story" precedent (`if blkd: watch.append(...)`), never an urgent "waiting on you" item.
- Touch up the two stale "once Story 10.3 wires it in" / "Story 10.3's job" comments
  (`sources/bmad_method.py`, `sources/__init__.py`) now that both are true, plus a one-line
  `models.py` docstring touch-up naming where the Source now surfaces -- keeps each module's own
  "why this exists" narrative accurate, matching every prior story's own docstring-touch-up
  convention in this epic.

**Block If:** (none -- Epic 10's own framing already clears 10.1/10.3 to dispatch without 10.2; no
unattended-unsafe decision remains beyond the NFR-4 placement call already resolved above)

**Never:**
- Never changes `bmad_method.py`'s own `gather`/`_gather`/`_fetch_latest_upstream_version` --
  Story 10.1/10.2's own territory, already shipped and reviewed; this story only adds CALLERS.
- Never adds `--bmad-core` to `doctor monitor`'s `--watch` axis system -- that system
  (`sources/atlas.py`) is architecturally scoped to fleet/maintainer-wide cf_atlas signals
  dispatched through ONE module (`atlas.gather(axis, ...)`); `BMAD_METHOD_VERSION_DRIFT` is a
  single-repo-scoped fact with no maintainer/package dimension, the same reason
  `MARSHAL_DURABILITY` (its closest precedent) is a `check` category, not a `monitor` axis.
- Never imports `pyforge.doctor` directly into `scripts/fleet_picture.py` -- every existing
  cross-package signal in that file already goes through `subprocess` (`marshal status`,
  `bmad_loop_baseline_drift_check.py`), not a direct import.
- Never persists or caches the fetched drift state anywhere new -- `fleet_picture.py`'s probe
  re-runs the gather every invocation, the same no-persistence discipline `bmad_method.py` itself
  already documents.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `doctor check` with no flags | today's real repo state | exactly engines+env+durability run; bmad-core does NOT run | No error; unchanged from today |
| `doctor check --bmad-core` | today's real drift (installed behind both floor and upstream) | 2 WARN findings, `source=bmad-method-version-drift`, in both text and `--json` render | No error |
| `doctor check --bmad-core --scope runtime` | scope mismatch (bmad-core is `scope="repo"`) | usage error, exit 2, mirrors `--durability --scope runtime` | argparse `.error()` |
| `doctor check --bmad-core --scope repo` | matches | runs normally | No error |
| `fleet_picture.py` `main()`, real drift present | `bmad_method.gather()` returns 1-2 WARN findings | ATTENTION `watch` gains one line per WARN finding naming the drift | No error |
| `fleet_picture.py` `main()`, no drift | both findings OK, or CAP-2's fetch failed (1 OK finding only) | no bmad-method line added to `watch` | No error |
| `fleet_picture.py` `main()`, `pyforge.doctor` unavailable / subprocess fails / malformed JSON | any failure mode | one `watch` line: "could not check bmad-method core version drift"; script still exits 0 | Caught by `except Exception` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- add `--bmad-core` flag,
  `_CATEGORY_SOURCE["bmad-core"]`, `_gather_bmad_core`, wire into `_run_check` (opt-in only, never
  in the default trio), import `bmad_method` from `.sources`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- touch up the
  `BMAD_METHOD_VERSION_DRIFT` registry comment ("Story 10.3's job" -> now dispatched).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- touch up the
  `_UPSTREAM_FETCH_TIMEOUT_SECONDS` comment ("once Story 10.3 wires it in" -> now true).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- one-line touch-up to the
  `BMAD_METHOD_VERSION_DRIFT` docstring naming where it's now surfaced.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` -- new `--bmad-core` test
  section mirroring the `--durability` section (findings reach both renders, default run excludes
  it, `--scope` usage error).
- `scripts/fleet_picture.py` -- add `bmad_core_drift_findings(repo=REPO, timeout=15)`, call it from
  `main()`'s ATTENTION block.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py` -- NEW,
  mirrors `test_fleet_picture_loop_home_staleness.py`'s `_load_fleet_picture()` harness;
  monkeypatches `subprocess.run` to cover the I/O matrix's fleet-picture rows.

## Tasks & Acceptance

**Execution:**
- [x] `__main__.py` -- add `--bmad-core` argparse flag + help text naming the NFR-4/opt-in
  rationale.
- [x] `__main__.py` -- add `"bmad-core": Source.BMAD_METHOD_VERSION_DRIFT` to `_CATEGORY_SOURCE`.
- [x] `__main__.py` -- add `_gather_bmad_core(target)` (mirrors `_gather_durability`'s shape)
  calling `bmad_method.gather(target)`.
- [x] `__main__.py` -- extend `_run_check`: compute `run_bmad_core = args.bmad_core` OUTSIDE the
  "no flags -> all on" branch; extend `_validate_scope_against_explicit_categories`'s `explicit`
  tuple.
- [x] `sources/__init__.py` -- update the `BMAD_METHOD_VERSION_DRIFT` REGISTRY comment.
- [x] `sources/bmad_method.py` -- update the `_UPSTREAM_FETCH_TIMEOUT_SECONDS` comment.
- [x] `models.py` -- one-line docstring touch-up.
- [x] `tests/unit/test_cli_check.py` -- new `--bmad-core` test section covering the I/O matrix.
- [x] `scripts/fleet_picture.py` -- add `bmad_core_drift_findings` + wire into `main()`'s ATTENTION
  block.
- [x] `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py` -- NEW
  test file.

**Acceptance Criteria:**
- Given today's real repo state (installed `bmad-method` behind both the declared floor and
  upstream), when `doctor check --bmad-core` runs, then both Findings appear in text and `--json`
  output, and `doctor check` (no flags) still excludes them entirely.
- Given the same real state, when `fleet_picture.py`'s `main()` runs, then its printed ATTENTION
  block's `watch` section names the drift, and the script still exits 0.
- Given `pyforge.doctor` unavailable or the subprocess call fails for any reason, when
  `fleet_picture.py`'s `main()` runs, then it degrades to one "could not check" `watch` line and
  never raises.
- Given the full `pyforge-doctor` test suite, when it runs after this change, then every
  pre-existing test (including `test_check_speed_budget.py`'s NFR-4 benchmark) still passes
  unmodified.

## Spec Change Log

(none -- no bad_spec loopback occurred in this story's review pass)

## Review Triage Log

### 2026-08-20 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 3: (low 3)
- reject: 4: (low 4)
- addressed_findings:
  - `[medium]` `[patch]` `fleet_picture.py`'s new ATTENTION line rendered a subprocess-sourced `Finding.message` raw, with no newline-stripping or length cap, unlike this same file's own `escalation_reason` precedent (`.split(chr(10))[0][:110]`) and `__main__.py`'s own `_single_line()` renderer for the identical risk class -- a multi-line message (e.g. from `degrade_on_exception`'s exception-repr wrapper on a multi-line `yaml.YAMLError`/`tomllib.TOMLDecodeError`) would have rendered as extra, indistinguishable bullet lines. Fixed with the same split/truncate guard, and folded in `finding["check"]` as a distinguishing tag (was previously discarded, hardcoded to a generic "bmad-method:" prefix) so CAP-1 (`bmad-method-version-drift`) and CAP-2 (`bmad-method-upstream-drift`) lines are self-labeled when both fire at once (verified live against this repo's own real current drift).
  - `[low]` `[patch]` `--bmad-core`'s own `--help` text didn't call out that its registered `scope="repo"` (the classification meaning "runs anywhere, CI/air-gapped-safe" everywhere else in this codebase) does NOT hold for this one category -- CAP-2 makes a live npm-registry call regardless. Extended the help text inline naming the exception and pointing at the pre-existing `sources/__init__.py` REGISTRY comment that already names the same tension.
  - `[low]` `[defer]` `DW-FU-10-3` -- `fleet_picture.py`'s `subprocess.run(..., check=True)` wrapper would swallow a hypothetical future FAIL finding from `bmad_method.gather()` into a generic "could not check" line, disagreeing with `doctor check --bmad-core`'s own faithful FAIL render for the same data; not live today (the source's own docstring promises never-FAIL, untested), out of this story's scope to fix (would require either a `bmad_method.py` test or a Never-boundary-violating rework of that module).
  - `[low]` `[defer]` `DW-FU-10-3-2` -- `--bmad-core`'s registered `scope="repo"` still doesn't guarantee no network I/O (pre-existing Story 10.2 tension, now concretely reachable and tested via `--bmad-core --scope repo`); the help-text patch above makes it discoverable, but the underlying scope classification itself is unchanged and out of this story's Boundaries to restructure.
  - `[low]` `[defer]` `DW-FU-10-3-3` -- `scripts/fleet_picture.py` has no end-to-end test of `main()`'s ATTENTION-block composition for ANY of its probes (PR-list, baseline-drift-check, loop-home-staleness, and now bmad-method drift), only the extracted helper functions in isolation; a pre-existing whole-file test-strategy gap surfaced incidentally, not unique to or fully closable by this one story.
  - Rejected (noise / matches explicit spec design / re-litigates an already-justified tradeoff): `run_bmad_core = run_bmad_core and _category_in_scope(...)` called "dead code" since an explicit `--bmad-core` with a mismatched scope already errors in `_validate_scope_against_explicit_categories` before `_run_check` runs -- true, but harmless (never flips a value, ever) and kept for structural consistency with the other three categories' identical line, a legitimate defense-in-depth choice, not a defect; two separate near-identical ATTENTION lines when CAP-1 and CAP-2 both WARN at once -- this is literally the spec's own I/O matrix ("one line per WARN finding"), not a deviation; the added live npm-registry call to every `fleet-picture` invocation "contradicts" a throttling preference -- directly conflicts with this story's own explicit, reasoned Boundaries decision against caching/persisting the fetched state (mirrors `bmad_method.py`'s own no-persistence discipline), not a gap; "ambient" framing is weaker than implied since the zero-flag default `doctor check` still shows nothing -- re-litigates the NFR-4-driven opt-in design decision already extensively justified in this spec's own Boundaries and Design Notes, not a new finding.

### 2026-08-20 — Repair pass (spec-surface-reconcile drift)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (low 4)
- defer: 0
- reject: 10: (low 10)
- addressed_findings:
  - `[low]` `[patch]` The prior landing (commit `1882877b91`) left `scripts/spec_surface_reconcile.py`
    red: the umbrella `pyforge-doctor/spec-pyforge-doctor` Spec's `.memlog.md` had not recorded this
    story's five governed-file changes (`__main__.py`, `models.py`, `sources/__init__.py`,
    `sources/bmad_method.py`, `tests/unit/test_cli_check.py`). Fixed by appending a narrative entry
    naming all five paths (mirroring the immediately-preceding Story 10.2 entry's own shape) and
    re-stamping the baseline scoped to that one spec (`--write-baseline --spec
    pyforge-doctor/spec-pyforge-doctor`) -- the established, ~16-times-precedented reconciliation
    procedure this umbrella spec's own memlog already documents for exactly this class of gap
    (the "S-13.7 gap"). Not a code change; no production behavior touched by this fix.
  - `[low]` `[patch]` A fresh Blind Hunter + Edge Case Hunter pass over the full story diff (per
    step-04's own construction, diffed since `baseline_revision`) caught that the repair's own
    first-draft memlog entry mis-cited `scripts/fleet_picture.py`'s governance
    (`spec-regenerable-factory`, a spec whose baseline entry actually tracks four unrelated
    detector scripts and never mentions `fleet_picture.py`). Corrected to the true reason:
    allowlisted in `scripts/spec_surface_allowlist.txt` (line 37) as operator tooling, never
    governed by any spec's `surface:`.
  - `[low]` `[patch]` `--bmad-core`'s `--help` text carried internal review-thread jargon ("NFR-4",
    "review finding", "sources/__init__.py's own REGISTRY comment") that adds no value for an end
    user reading `--help`. Trimmed to keep the substantive warning (the live npm-registry call,
    and that `--scope repo` does not mean network-free for this one category) while dropping the
    internal citations; confirmed via grep that no test asserts on the removed substrings.
  - `[low]` `[patch]` `bmad_core_drift_findings()`'s own unit tests (`test_fleet_picture_
    bmad_core_drift.py`) covered single-warn, no-warn, and both failure paths, but never the
    two-finding-at-once case its own inline comment explicitly calls out ("CAP-1/CAP-2 can both
    warn at once") -- which is this repo's REAL current state, confirmed live via `pixi run -e
    local-recipes fleet-picture` before writing the test. Added
    `test_both_cap1_and_cap2_warn_simultaneously`; also added a one-line comment on
    `bmad_core_drift_findings`'s `timeout=15` explaining the 3x margin over the inner
    `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0` bound (interpreter startup + import overhead), a
    separate low finding from the same pass.
  - Rejected (duplicate of an already-deferred finding, verified-safe-by-design, or verified false
    by live evidence): the `--scope repo` doesn't-guarantee-no-network-I/O tension and the missing
    end-to-end `main()` ATTENTION-block test are the SAME two items already deferred in the prior
    review pass as `DW-FU-10-3-2`/`DW-FU-10-3-3` -- re-deferring would duplicate the ledger; a claim
    that no test proves the real subprocess call resolves was settled by running the real thing --
    `pixi run -e local-recipes fleet-picture` and `pixi run -e local-recipes python -m
    pyforge.doctor.__main__ check --bmad-core`, both rc=0 against this repo's actual, un-mocked
    live drift, printing correctly labeled `bmad-method-version-drift`/`bmad-method-upstream-drift`
    lines in both surfaces exactly as the story's own Acceptance Criteria require; two findings
    proposing extra defensive code for a `None`-valued `Finding.message` and a malformed
    non-list JSON shape were rejected because `pyforge.doctor.models.Finding.message: str` already
    makes the first case structurally unreachable from this source, and both cases are already
    caught by the SAME whole-probe `try/except Exception` idiom `main()` uses for every ATTENTION
    probe in this file, degrading to the one generic "could not check" line the story's own I/O
    matrix already specifies for "any failure mode" -- the documented contract working as designed,
    not a gap; a claim that `finding.get("check", "bmad-method")`'s fallback names a nonexistent
    check was rejected on the same structural-guarantee grounds (`Finding.check` is a non-optional
    field); a test-name nitpick, a diff-scope observation about the deferred-work ledger not being
    part of the diff, and a claim that placing the new meta-test under
    `.claude/skills/conda-forge-expert/tests/meta/` triggers CLAUDE.md's CFE-skill-invocation rule
    were all rejected as noise -- the last one specifically because that directory already holds
    `test_fleet_picture_loop_home_staleness.py`, an established, unrelated precedent for exactly
    this kind of cross-station meta test having nothing to do with conda-forge recipe work.

## Design Notes

`--bmad-core` deliberately breaks from `--durability`'s "always in the default trio" precedent for
one narrow, well-evidenced reason: `MARSHAL_DURABILITY`'s own gather reads only tracked
files/git history (no network), so its default-on inclusion costs nothing against NFR-4;
`BMAD_METHOD_VERSION_DRIFT`'s CAP-2 half performs a real, un-mockable npm HTTP call whose own
module docstring already assumed (prematurely, before this story existed) that it would run
"every `doctor check`/`monitor` invocation." Keeping it opt-in is the surgical fix:
`test_check_speed_budget.py` calls `main(["check", str(_REPO_ROOT)])` with zero flags, so its ~2x
headroom stays exactly as measured today, and `fleet-picture`'s ATTENTION block becomes the
genuinely zero-effort ambient surface the epic's own title promises -- an operator running the
fleet status they already check regularly sees the drift without ever passing `--bmad-core` by
hand.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py -v` --
  expected: all pass, including the NFR-4 benchmark unaffected.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green, same
  baseline count as Story 10.2's own run plus this story's new tests.
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py -v` --
  expected: all pass.
- `pixi run -e local-recipes python -m pyforge.doctor.__main__ check --bmad-core` -- expected:
  today's live drift (2 WARN findings) prints.
- `pixi run -e local-recipes fleet-picture` -- expected: ATTENTION block's `watch` section names
  the live bmad-method drift.

## Auto Run Result

**Summary:** Story 10.3 itself (commit `1882877b91`) landed complete in a prior session: a new
opt-in `doctor check --bmad-core` category and a `fleet_picture.py` ATTENTION probe, both wiring
Story 10.1/10.2's `bmad_method.gather()` into the two consumer surfaces the epic's own success
signal names. That session's deterministic verification (`python
scripts/spec_surface_reconcile.py`) failed post-landing: the umbrella `pyforge-doctor/
spec-pyforge-doctor` Spec's `.memlog.md` had not recorded the story's five governed-file changes.
This session repaired that gap and, in the review pass the repair itself triggered, patched four
further low-severity findings. No change to this spec's `<intent-contract>`; no production
behavior changed beyond a CLI `--help` text trim.

**Files changed this session** (commit `73790c3afa`, on top of `1882877b91`):
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` --
  two new entries naming Story 10.3's governed-file changes and this repair's own follow-up patches
  (the spec-surface reconciliation itself).
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to `pyforge-doctor/spec-pyforge-doctor`
  only (verified: exactly that one key's file hashes + memlog hash changed, twice).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- `--bmad-core` `--help`
  text trimmed to drop internal review-thread citations, substantive content kept.
- `scripts/fleet_picture.py` -- one-line comment explaining `bmad_core_drift_findings`'s
  `timeout=15` margin over the inner 5.0s upstream-fetch bound.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py` -- one new
  test, `test_both_cap1_and_cap2_warn_simultaneously`.

**Review findings breakdown (this session's pass):** 4 patched (all low: a mis-cited governance
claim in this repair's own first draft, the help-text trim, the timeout comment, the missing
dual-warn test), 0 deferred (two candidates were duplicates of the prior pass's `DW-FU-10-3-2`/
`DW-FU-10-3-3` and were not re-deferred), 10 rejected (duplicates of already-deferred items,
findings settled false by live evidence, or findings already covered by an existing safety net --
full triage in the Review Triage Log entry above).

**Follow-up review recommendation:** `false` -- four localized, low-consequence fixes, no
behavior/API/security/data impact.

**Verification performed:** `spec_surface_reconcile.py` exits 0 (was exit 1, 5 findings).
`pyforge-doctor-test`: 1054 passed, 2 skipped (unchanged by this session's patches -- neither
touched a file that suite collects). `test_cli_check.py` + `test_check_speed_budget.py`: 42 passed.
`test_fleet_picture_bmad_core_drift.py`: 6 passed (was 5, +1 this session). Live, un-mocked:
`pixi run -e local-recipes python -m pyforge.doctor.__main__ check --bmad-core` (rc=0, 2 WARN
findings) and `pixi run -e local-recipes fleet-picture` (rc=0, ATTENTION block names both live
findings under distinct `check` tags) both match the spec's own Acceptance Criteria exactly against
this repo's real current drift state. `doctor check` with no flags confirmed to still exclude
`bmad-core` entirely.

**Residual risks:** None new from this session. Three low findings remain deferred from the prior
review pass (`DW-FU-10-3`, `DW-FU-10-3-2`, `DW-FU-10-3-3`, all pre-existing/out-of-scope tensions
named in the Review Triage Log above) -- unchanged and not touched by this repair.

