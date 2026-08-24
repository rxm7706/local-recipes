---
title: 'provision --module <name>'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md']
warnings: ['oversized']
baseline_revision: '86d9c5b740956335ad8cf32e88e8636b2e78ca09'
final_revision: '222feeea270c3943ca8f9d77f2143cb91e1b1c4e'
---

<intent-contract>

## Intent

**Problem:** `bmad-builder` (BMB) is already a pixi dependency but was never taken through its own `bmad-bmb-setup` skill, so `_bmad/config.yaml` never gets a `bmb` section and there is no reproducible, one-command way to fix that on a fresh clone or brownfield target — the same gap that left Skill Forge hand-installed via a now-lost driver script.

**Approach:** Add `steward provision --module <name>` (new flag on the existing `provision` duty, `provision.py`/`cli.py`) that drives a registered module's own non-interactive setup-skill scripts as subprocesses and reports the result; Story 6.1 registers exactly one backend, `bmb`, chosen because it already has a genuine, non-interactive, git-discoverable script chain (unlike Skill Forge, whose `install` has no non-interactive flag as of v1.0.0). An unrecognized name reports the supported set instead of a raw tool error.

## Boundaries & Constraints

**Always:**
- Every `--module` action is a thin subprocess wrap of that module's own installed setup-skill scripts (`merge-config.py`, `merge-help-csv.py` under `.pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup/`) — Steward assembles their documented CLI arguments from `module.yaml`'s own declared variable defaults, never reimplements their merge/anti-zombie logic.
- An unrecognized `--module` name never reaches a subprocess call; it returns `DutyResult(ok=False, ...)` naming the supported set.
- Every `--module` error path (unknown name, missing backend, subprocess failure) reuses `ProvisionDuty`'s existing `except subprocess.CalledProcessError` / `except (RuntimeError, FileNotFoundError, ...)` boundary and `_render_error`, so `--json` is honored on failure exactly like every other flag.

**Block If:** None identified — the module set (`bmb` only), flag value (`bmb`, matching the module's own `code`), and the `--legacy-dir`/`cleanup-legacy.py` exclusion are all resolved below with evidence, not left open.

**Never:**
- Does not pass `--legacy-dir` to `merge-config.py`/`merge-help-csv.py`, and does not invoke `cleanup-legacy.py` at all. Verified in this repo's actual `_bmad/`: `_bmad/core/config.yaml` exists (legacy config for a *different*, already-governance-owned module), but no `_bmad/bmb/` legacy directory exists — BMB was only ever pixi-installed, never run through any per-module legacy flow. Passing `--legacy-dir` would (a) pull `_bmad/core/config.yaml`'s values in as fallback "core" answers this story deliberately never collects, and (b) both `merge-config.py` and `cleanup-legacy.py` unconditionally delete/target `{legacy-dir}/core/...` as part of their own cleanup — `_bmad/core/**` is installer/governance-owned (out of scope per the dedicated SPEC's constraints) and there is nothing legitimate for `bmb` to migrate from anyway.
- Does not register Skill Forge (or any module besides `bmb`) — its `bmad-module-skill-forge install` has no non-interactive CLI flag (v1.0.0 `STABILITY.md`), so wrapping it needs a new, committed headless Node driver, a materially different and larger piece of work. Deferred, not silently dropped.
- Does not collect or write core config values (`user_name`, `output_folder`, etc.) — `module.yaml` only declares module-scoped defaults, and SKILL.md's own "only if no core keys exist yet" rule needs conditional prompting this headless path doesn't do. An absent `"core"` key in the answers JSON is a no-op `merge-config.py` already supports.
- Does not copy any BMB skill files into `.claude/skills/` — none of BMB's own setup-skill scripts do this either; it is not part of "the module's own installer" being wrapped here (AD-1), and Story 6.1's own AC only requires "invoked as a subprocess and the result reported."
- Story 6.2 (filesystem-derived `--list-modules`) and Story 6.3 (deep "exited 0 but left the module unimportable" verification) are separate stories — this one reports exactly what its two subprocess calls each report.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `--module bmb`, `bmad-builder` pixi dep installed, no prior `bmb` section | `merge-config.py` then `merge-help-csv.py` each run once via `uv run`; `_bmad/config.yaml` gains a `bmb` section, `_bmad/module-help.csv` gains its rows; configured output dirs created; `DutyResult(ok=True, ...)` | No error expected |
| Unknown module name | `--module nope` | `DutyResult(ok=False, ...)` naming `nope` and the supported set (`bmb`) | `subprocess.run` never called |
| Backend not installed | `--module bmb`, the setup-skill dir absent under `.pixi/envs/local-recipes/...` | `DutyResult(ok=False, ...)` naming the missing path + `pixi install -e local-recipes` fix | `FileNotFoundError`, caught at `ProvisionDuty`'s existing boundary |
| A script exits non-zero | e.g. `merge-config.py` fails | `DutyResult(ok=False, ...)` with that command + its stderr, `EXIT_FAILED` via `cli.main()` | `subprocess.CalledProcessError`, caught at the existing boundary, honors `--json` |
| `--module bmb --json` | flag combo | Machine-readable JSON: each script's own parsed stdout, keyed by step | Same JSON shape on any failure path |
| Re-run against an already-provisioned module | `--module bmb` a second time | Idempotent: anti-zombie merge replaces the `bmb` section/rows; no error | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- add the module registry, `provision_module()`, and `_run_module()`; wire into `ProvisionDuty.run()`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `--module NAME` to `_add_provision_subparsers`
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py` -- new, mirrors `test_provision_env.py`'s shape (monkeypatched `subprocess.run` + `repo_root`)
- `.pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup/{assets/module.yaml,scripts/merge-config.py,scripts/merge-help-csv.py}` -- read-only reference: the real backend being wrapped, not modified

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- add `_SUPPORTED_MODULES = {"bmb": Path(".pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup")}` and `provision_module(name, *, cwd) -> dict[str, object]`: resolve the skill dir (raise `FileNotFoundError` if absent), `yaml.safe_load` its `assets/module.yaml` (PyYAML is already a project dependency), build `{"module": {key: var["default"] for each top-level entry that is a dict with a "default" field}}` into a temp JSON file, then `subprocess.run(["uv", "run", str(script), *args], check=True, capture_output=True, text=True)` for `merge-config.py` (`--config-path _bmad/config.yaml --user-config-path _bmad/config.user.yaml --module-yaml ... --answers <tmp>`, no `--legacy-dir`) followed by `merge-help-csv.py` (`--target _bmad/module-help.csv --source .../assets/module-help.csv`, no `--legacy-dir`/`--module-code`), parsing each script's JSON stdout
- [x] `provision.py` -- add a helper that `mkdir -p`s any `module.yaml` variable whose `result` template resolves to a `{project-root}`-prefixed path (same template substitution `merge-config.py`'s own `apply_result_templates` uses, read-only reuse of the same file — SKILL.md names this a caller responsibility, not something any script does)
- [x] `provision.py` -- add `_run_module(ns)`: unknown name -> `DutyResult(ok=False, ...)` naming the supported set without calling `provision_module`; known name -> call it, format success text or `--json` per `ns.json`; wire into `ProvisionDuty.run()` as the new first precedence check (mirrors the existing pattern of each new story's flag landing at the top); update the class docstring's precedence line and `_PROVISION_HELP`
- [x] `cli.py` -- add `provision_parser.add_argument("--module", metavar="NAME", help="BMAD module to provision (supported: bmb)")`; update `_add_provision_subparsers`'s docstring (currently says "Epic 3, all four stories")
- [x] `tests/conformance/test_provision_module.py` -- cover every I/O Matrix row: unknown-name (assert `calls == []`), missing-backend-dir, the two-script success sequence (assert exact `argv` per call via monkeypatched `subprocess.run` + `repo_root`, and assert no call's `argv` contains `cleanup-legacy.py` or `--legacy-dir` -- the AC 5 regression guard), a failing script surfacing as `EXIT_FAILED` through `main()`, and `--json` on both the success and unknown-name paths

**Acceptance Criteria:**
- Given the module name `bmb`, when `steward provision --module bmb` runs, then `merge-config.py` and `merge-help-csv.py` are each invoked exactly once via `uv run` with no `--legacy-dir`, and `DutyResult(ok=True, ...)` is returned when both exit 0
- Given an unsupported module name, when `steward provision --module <name>` runs, then the result names the supported set (`bmb`) and no subprocess is invoked
- Given either script exits non-zero, when `steward provision --module bmb` runs, then the result is `ok=False` with that script's own stderr surfaced verbatim, and `cli.main()` exits `EXIT_FAILED`
- Given `bmad-builder`'s pixi dependency is not installed (the setup-skill directory is absent), when `steward provision --module bmb` runs, then the result names the missing path and the `pixi install -e local-recipes` fix, never a raw traceback
- Given `cleanup-legacy.py` is never invoked for `bmb`, when `steward provision --module bmb` runs, then `_bmad/core/config.yaml` is left untouched (regression guard for the collateral-deletion risk this spec identified)

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 0, medium 3, low 8)
- defer: 1
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` Malformed/non-dict `module.yaml` crashed with an uncaught `AttributeError` past the AD-8 duty-failure boundary — added an explicit `isinstance` check raising `RuntimeError`, and widened `ProvisionDuty.run()`'s except tuple with `yaml.YAMLError`.
  - `[medium]` `[patch]` A wrapped script exiting 0 with unparseable stdout crashed with an uncaught `json.JSONDecodeError` — wrapped both `json.loads` calls, raising a clear `RuntimeError`.
  - `[medium]` `[patch]` `--module`'s CLI help text hardcoded `"supported: bmb"` instead of deriving from the module registry (this repo has standing team memory about exactly this "derive, don't declare" anti-pattern recurring) — added cross-reference comments at both definition sites; rejected an import-based derivation because it would break `cli.py`'s existing lazy per-duty-module import architecture (`resolve_duty` is the one place that imports duty modules).
  - `[low]` `[patch]` `--module ""` silently fell through to the bare-`provision` success summary instead of being reported as unsupported (empty string is falsy) — dispatch check changed from a truthiness check to `is not None`.
  - `[low]` `[patch]` `provision_module()` called directly with an unregistered name raised an undocumented `KeyError` instead of the documented `FileNotFoundError` — added an explicit membership guard at the top of the function.
  - `[low]` `[patch]` No validation that `_SUPPORTED_MODULES`'s registered key matches the module's own declared `code:` field — added a `RuntimeError` guard comparing them.
  - `[low]` `[patch]` A YAML-native non-string default (e.g. an unquoted date scalar) would crash `json.dumps` uncaught while writing the answers file — added `default=str`.
  - `[low]` `[patch]` A plain file occupying a configured output-dir path raised an uncaught `FileExistsError` past the AD-8 boundary — wrapped the `mkdir` call, raises a clear `RuntimeError`.
  - `[low]` `[patch]` The non-`--json` success summary omitted `output_dirs_created`, which the `--json` summary reports — the text summary now names created directories too.
  - `[low]` `[patch]` `_materialize_module_output_dirs`'s `{value}`-substitution branch was untested (dead for the real `bmb` module.yaml today, but a real reachable code path) — added a dedicated unit test with a synthetic module.yaml.
  - `[low]` `[patch]` The new precedence test built its `argparse.Namespace` inline instead of via the file's own shared `_full_namespace` helper — switched to the helper for consistency.

Rejected (verified, not fixed): core-config values forfeited by skipping `--legacy-dir` (already an explicit, justified Never-bullet in this spec's intent-contract, not a new gap); no full real-backend integration test (already explicitly deferred to this spec's own "Manual checks"); hardcoded `local-recipes` pixi env name (matches this file's own existing precedent, nothing speculative); less-friendly message for a missing `module.yaml` vs. a missing skill dir (still caught at the existing boundary, cosmetic only); the "runs twice" test's narrowly-scoped idempotency claim (its docstring already accurately scopes what it proves); a `{project-root}/../..` path-traversal concern in a module.yaml default (rejected as security theater — the wrapped module already executes with full subprocess trust under AD-1, so this alone doesn't change the threat model); a wrapped script exiting 0 while its own JSON reports `"status": "error"` (verified against the real `merge-config.py`/`merge-help-csv.py` source: every `"status": "error"` emission is unconditionally paired with `sys.exit(1)`, so this scenario cannot occur with the real backend — only the test's own mocked fixtures allowed it).

Deferred: `_run_env`'s/`_run_runner`'s own unknown-value error paths (bad `--env` name, unknown `--runner` value) don't honor `--json` on error — pre-existing (Stories 3.1/3.2), not caused by this story, surfaced incidentally by contrast with `--module`'s own `--json`-aware error path. Logged to `deferred-work.md`.

## Design Notes

**Why `uv run <script>` and not bare `python3`:** each script is a PEP 723 single-file script (`dependencies = ["pyyaml"]`); `uv run` is this repo's own established convention for these (e.g. `.claude/skills/shared/scripts/skf-preflight.py`'s own header), and it works regardless of which pixi environment `steward` runs under — confirmed via `pixi.toml` that steward's own `pyforge-steward` environment is `no-default-feature` and does **not** include `bmad-builder`/PyYAML at all; only the separate `local-recipes` (default-feature) environment does. This assumes `uv` itself is on PATH, the same class of assumption `materialize_environment` already makes about bare `pixi`.

**Why `cleanup-legacy.py` is excluded (the load-bearing finding of this spec):** its own logic hardcodes `dirs_to_remove = [module_code, "core"]` regardless of what actually needs migrating. In this repo, `_bmad/core/` genuinely exists (holding `config.yaml`/`module-help.csv` for a different, already-installed module's legacy state) while `_bmad/bmb/` does not. Running `cleanup-legacy.py --module-code bmb` would find `_bmad/core/` present, find no `SKILL.md` inside it (so the `--skills-dir` safety check silently skips verification for that directory rather than blocking), and `shutil.rmtree` it — deleting a file this SPEC's own constraints call installer/governance-owned. Skipping the script entirely is correct here, not a corner cut: there is no genuine `_bmad/bmb/` legacy directory for it to migrate in the first place.

**Why `bmb` is the flag value, not `bmad-builder`:** matches the module's own `code: bmb` field in `module.yaml`, the same vocabulary `merge-help-csv.py --module-code`/`cleanup-legacy.py --module-code` already use.

## Verification

**Commands:**
- `cd src/shared/packages/pyforge-steward && python3 -m pytest tests/conformance/test_provision_module.py -q` -- new tests pass
- `cd src/shared/packages/pyforge-steward && python3 -m pytest tests -q` -- full existing suite stays green

**Manual checks (real backend, no mocks):**
- From repo root, with `local-recipes` on PATH: `pixi run -e pyforge-steward steward provision --module bmb`, then inspect `_bmad/config.yaml` for a new `bmb:` section, `_bmad/module-help.csv` for new rows, and confirm `_bmad/core/config.yaml` is unchanged (mtime/content) before and after.

## Auto Run Result

- **Summary:** `steward provision --module <name>` added as the new top-precedence
  `provision` flag; `bmb` registered as the sole backend (`_SUPPORTED_MODULES`),
  driving BMB's own `bmad-bmb-setup` scripts (`merge-config.py`, `merge-help-csv.py`)
  as `uv run` subprocesses (AD-1). Deliberately excludes `--legacy-dir` and never
  invokes `cleanup-legacy.py` -- this repo's real `_bmad/core/config.yaml` belongs to
  a different, already-governance-owned module that `cleanup-legacy.py`'s hardcoded
  `[module_code, "core"]` removal list would `shutil.rmtree`. An unrecognized
  `--module` name is reported directly, never reaching a subprocess call. Review
  pass on 2026-08-09 found 11 patch findings (0 high, 3 medium, 8 low), all fixed;
  1 pre-existing item deferred (`_run_env`/`_run_runner` not honoring `--json` on
  error, Stories 3.1/3.2, unrelated to this story); 7 findings rejected as verified
  non-issues. Landed in commit `30c30cdae5` (dev attempt 1).
- **Repair pass (dev attempt 2):** dev attempt 1's own deterministic verify passed
  (`pixi run --frozen -e pyforge-steward pyforge-steward-test`) but the repo-wide
  `python scripts/spec_surface_check.py` gate (wired into this station's verify
  commands by marshal 13.7 specifically to catch this) failed with 4 findings: the
  spec-scoped `pyforge-steward/spec-bmad-module-provisioning` Spec governs
  `provision.py` directly, and the project-level `pyforge-steward/spec-pyforge-steward`
  Spec governs the whole package (so it also governs `provision.py`, plus `cli.py`
  and the new `test_provision_module.py`) -- neither Spec's `.memlog.md` named the
  Story 6.1 changes. Reconciled by appending one `(change)` entry to each Spec's
  `.memlog.md`, naming every governed path this story touched, per S-13.2's
  per-file reconciliation rule. Deliberately did **not** run `--write-baseline`
  (unlike Story 5.2's own repair pass, which did): `harness_bmadloop.py`'s
  `_SURFACE_RECONCILE_COMMAND` comment and `spec-surface-drift-reconciliation`'s
  CAP-7 both state the loop/producer must never stamp its own baseline -- that is
  exactly the laundering S-13.2 exists to end -- and the detector's own per-file
  logic (S-13.2) already clears a named path via the memlog move alone, with no
  baseline stamp required. Verified this by running the detector both before and
  after the memlog edit (findings present, then absent) with the baseline file
  untouched throughout. No code change, no `<intent-contract>` change. Landed in
  commit `222feeea`.
- **Files changed (repair pass):**
  - `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/.memlog.md`
    -- new `(change)` entry naming `provision.py`'s Story 6.1 changes.
  - `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
    -- new `(change)` entry naming `cli.py`, `provision.py`, and
    `test_provision_module.py`'s Story 6.1 changes.
  - `scripts/.spec-surface-baseline.json` -- untouched (see above).
- **Review findings breakdown:** unchanged from dev attempt 1's pass (11 patch, 1
  defer, 7 reject -- see `## Review Triage Log` above); the repair pass touched only
  spec-governance bookkeeping, not application code, so no new adversarial review
  was run against it.
- **Follow-up review recommendation:** `false` -- bookkeeping-only reconciliation, no
  behavior change; matches dev attempt 1's own judgment (11 low/medium-severity
  patches, all localized, no behavior/API/security/data-model impact).
- **Verification performed:** `pixi run --frozen -e pyforge-steward pyforge-steward-test`
  -- 231 passed. `python scripts/spec_surface_check.py` -- exit 0, "OK: every tracked
  file governed or allowlisted; no drift."
- **Residual risks:** the spec's own "Manual checks" (real `bmb` backend, no mocks)
  were not run in this unattended session -- consistent with the spec marking them
  manual rather than a gating verification command. `ARCHITECTURE-SPINE.md`'s AD-5
  text still names only pixi and the retired `bmad-loop-worktree` wrap and does not
  yet mention the new BMB-subprocess target this story adds; noted in
  `spec-pyforge-steward`'s memlog as a documented gap, not a contradiction, since
  `--module`'s intent and constraints live in the dedicated
  `spec-bmad-module-provisioning` Spec.

