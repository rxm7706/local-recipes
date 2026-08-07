<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-07 -->
---
title: 'Story 1.6: The operator can ask "is anything host-unscoped right now?" and get a real answer'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 1.2 built the drift-detection primitive (`scan_source`/`scan_file`) and Story 1.3 built the plaintext-secret-scan primitive (`scan_file_for_secrets`/`scan_directory_for_secrets`) — both proven at the primitive level, but neither reachable from the CLI. There is no way for the operator (or an automated dogfood check) to actually ask "is anything host-unscoped right now?" without writing a Python one-liner.

**Approach:** Wire `steward keys audit --drift [--path <file>]` onto Story 1.2's `scan_file`, defaulting `--path` to `locate_http_module()` — the ONE delegate chokepoint this epic's drift scan was ever built to check (per AD-2/"not a general-purpose static-analysis framework"), with `--path` existing only so a test (or an operator) can point the same scan at a fixture. Also wires `steward keys audit --secrets <path>` onto Story 1.3's `scan_file_for_secrets`/`scan_directory_for_secrets` (dispatches on whether `<path>` is a file or directory) — fulfilling Story 1.3's own spec's explicit forward commitment ("Story 1.6 exposes both this module's findings — `DriftFinding` and `PlaintextSecretFinding` — through one CLI verb"). Both flags share one `keys audit` verb and can be combined in a single invocation; `DutyResult.ok` is `False` whenever either scan reports a finding, so an automated dogfood check gets a real exit code, not just text. Finally, `pyforge-steward-dogfood`'s pixi task is extended to also run `steward keys audit --drift`, so this audit is (per the epic's own "dogfooding is structural" architecture principle) exercised against this repo's own live state on every dogfood run, not just against synthetic fixtures.

## Boundaries & Constraints

**Always:**
- `--drift`'s default scan target is `locate_http_module()` (the SAME marker-walk `keys.py` already uses to find its delegate) — never an arbitrary directory walk. `--path` overrides it, used by this story's own tests to point at the Story-1.2 fixture; it is not a general-purpose "scan any Python file" feature (AD-2/Never: not a pluggable static-analysis framework).
- `--secrets <path>` dispatches on `Path(path).is_dir()`: a directory goes through `scan_directory_for_secrets`, a file through `scan_file_for_secrets` — reusing Story 1.3's primitives verbatim, no new scan logic.
- `--drift` and `--secrets` are independent, combinable flags on the SAME `audit` verb (Story 1.3's spec explicitly commits to "one CLI verb" for both finding types) — never two separate verbs.
- `DutyResult.ok` is `False` if EITHER scan (whichever ran) reports at least one finding, `True` only if every scan that ran reported clean — the whole point of a dogfood-gate is a real exit code, not text the operator has to read.
- Every finding is rendered with enough context to locate the offending code path: `DriftFinding`'s existing `function:line` + `message`, `PlaintextSecretFinding`'s existing `path:line` + `pattern_name` + `message` — both dataclasses already carry this; `audit` adds no new fields, only formats the existing ones.
- `pyforge-steward-dogfood`'s pixi task command is extended (not replaced) to also run `steward keys audit --drift`, so `--version` and the audit both gate the same dogfood run.
- Bare `steward keys audit` (neither `--drift` nor `--secrets`) degrades to `DutyResult(ok=True, ...)` naming the available flags (AD-7 — never crashes on a missing mode), matching the existing bare-verb precedent for `keys` itself.

**Block If:** none — self-contained CLI + library work, no ambiguous external decision points.

**Never:**
- No general-purpose static-analysis framework, no scan of an arbitrary directory tree for `DriftFinding`s — `--drift` always targets exactly one file (the delegate, or a test-supplied override), never a `rglob`. This is the same restraint Story 1.2's own spec already committed to; `audit` does not loosen it.
- No auto-population of `observed`-provenance inventory entries from `--drift`/`--secrets` findings. This IS suggested by the epic-1-context.md cross-story-dependency note ("Story 1.6 populates observed-credential entries"), but epics-with-stories.md's own Given/When/Then AC blocks for this story test only the two scans' pass/fail reporting — neither mentions writing to the inventory. Inventing an env-var-name-to-observed-entry heuristic with no AC to validate it against would be speculative surface (Simplicity First); recorded as a deferred-work item + this story's own explicit judgment call (Design Notes) rather than silently guessed at.
- No new finding types, no merging `DriftFinding`/`PlaintextSecretFinding` into one shape — Story 1.3's spec already established they must stay distinct; `audit`'s combined output labels each line's origin (`[drift]`/`[secrets]`) precisely so a caller parsing text output can still tell them apart.
- No revocation, no rotation triggered by an audit finding — Stories 1.4/1.7 are separate, deliberate operator actions; `audit` only ever reports.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--drift` against the real, fixed `_http.py` | No `--path` override | Reports clean; `DutyResult(ok=True, ...)` | No error expected |
| `--drift` against the Story 1.2 fixture | `--path` pointing at `ungated_jfrog_auth.py` | Exactly the one known finding, function/line identifiable; `DutyResult(ok=False, ...)` | No error expected (a finding is not a crash) |
| `--drift --path` a nonexistent file | A path that doesn't exist | Clear failure, not a traceback | `OSError`/`FileNotFoundError` at the primitive → `DutyResult(ok=False, ...)` via CLI |
| `--drift --path` malformed Python | Invalid syntax | Clear failure, not a traceback | `SyntaxError` at the primitive → `DutyResult(ok=False, ...)` via CLI |
| `--secrets <dir>` clean | A directory with no secret-shaped content | Reports clean; `DutyResult(ok=True, ...)` | No error expected |
| `--secrets <dir>` with a planted secret-shaped fixture | A directory containing one matching file | One `PlaintextSecretFinding` reported with path/line/pattern name; `DutyResult(ok=False, ...)` | No error expected |
| `--secrets <file>` (not a directory) | A single file path | `scan_file_for_secrets` runs directly (not the directory walk) | No error expected |
| Both flags together, both clean | `--drift --secrets <clean dir>` | Both scans run; combined output; `DutyResult(ok=True, ...)` | No error expected |
| Both flags together, one dirty | `--drift` clean, `--secrets` dirty (or vice versa) | Combined output shows both results; `DutyResult(ok=False, ...)` — one dirty scan fails the whole audit | No error expected |
| Neither flag given | Bare `steward keys audit` | Names the available flags; `DutyResult(ok=True, ...)` | No error expected |
| Dogfood task | `pixi run -e pyforge-steward pyforge-steward-dogfood` against this repo's current state | Exits 0 | No error expected — this repo's own `_http.py` is already fixed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `audit`, dispatching `--drift`/`--secrets` onto `scan_file`/`scan_file_for_secrets`/`scan_directory_for_secrets`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `keys audit [--drift] [--path <file>] [--secrets <path>]` subparser; extend `_KEYS_VERBS`/`_HELP["keys"]`
- `src/shared/packages/pyforge-steward/pixi.toml` (repo root) -- extend `[feature.pyforge-steward.tasks.pyforge-steward-dogfood]`'s `cmd` to also run `steward keys audit --drift`
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_audit_cli.py` -- NEW: covers the I/O matrix at the CLI level (`main(["keys", "audit", ...])`)
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_audit_drift.py` -- READ-ONLY reference: the already-proven `DriftFinding` primitive behavior this story wires, unchanged
- `src/shared/packages/pyforge-steward/tests/conformance/fixtures/ungated_jfrog_auth.py` -- READ-ONLY reference: the `--path` override target for this story's CLI-level drift test
- `src/shared/packages/pyforge-steward/tests/conformance/fixtures/plaintext_secret_candidate/leaked_key.txt` -- READ-ONLY reference: the `--secrets` fixture target

## Tasks & Acceptance

**Execution:**
- [x] `keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `audit`; both `--drift` and `--secrets` combinable, `ok=False` if either scan finds anything, clear per-finding-type message prefixes (`[drift]`/`[secrets]`)
- [x] `cli.py` -- add `keys audit --drift [--path <file>] --secrets <path>` subparser (both flags optional, at least a documented "no mode" degrade if neither given)
- [x] `pixi.toml` (root) -- extend `pyforge-steward-dogfood`'s `cmd` to also run `steward keys audit --drift`
- [x] `tests/conformance/test_keys_audit_cli.py` -- cover every I/O matrix row

**Acceptance Criteria:**
- Given Story 1.2's detection primitive, when `steward keys audit --drift` is run against this actual repo, then it reports clean against the current, already-fixed `_http.py`, and run with `--path` pointing at a deliberately reintroduced fixture of the historical unconditional-injection pattern, it reports exactly that finding, named clearly enough to locate the offending code path.
- Given this audit is also this duty's dogfooding target, when `steward keys audit --drift` is included in the package's own `-dogfood` pixi task, then the dogfood task exits 0 against the current repo state.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (adversarial re-read of the diff before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 1
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` The first draft's `audit` verb caught `SyntaxError`/`OSError` from the `--drift` scan but not from `--secrets` (a nonexistent `--secrets` path raised `NotADirectoryError`/`FileNotFoundError` uncaught, escaping to `cli.main()`'s generic handler as `EXIT_INTERNAL` with a raw traceback) — inconsistent with `--drift`'s own clean-failure handling and with `rotate`'s established "bad input is a duty failure, not a crash" boundary (AD-8). Patched: `OSError` (parent of both) now caught for both flags uniformly, reported as `DutyResult(ok=False, ...)`. Regression test added (`test_secrets_flag_against_a_nonexistent_path_is_a_clean_failure`).
  - `[low]` `[defer]` `--secrets`'s directory-walk (`scan_directory_for_secrets`) still has the pre-existing, already-ledgered "no `.git`/`.pixi` exclusion" and "no size cap" deferred items from Story 1.3 — this story does not point `--secrets` at the real repo root by default (unlike `--drift`, which does default there), so those two ledger items remain exactly as scoped, not newly triggered by this story. Not re-appended; the existing ledger entries already cover this.

## Design Notes

**Why `--drift` has no default directory-walk mode, but `--secrets` takes an explicit required path:** the two primitives have fundamentally different scopes by design (Story 1.2/1.3's own restraint) — `DriftFinding` detection targets exactly ONE known chokepoint file (`_http.py`), so "the repo" and "that one file" are the same default; `PlaintextSecretFinding` detection is inherently about "did anyone commit something secret-shaped anywhere in this tree," so it has no single natural default target and must be told where to look. Giving `--secrets` a default of "the whole repo" would silently walk `.git`/`.pixi` (the already-ledgered Story 1.3 deferred item) every time the dogfood task ran — deliberately not done until that item is addressed.

**Why observed-entry auto-population is deferred, not implemented:** epic-1-context.md's Cross-Story Dependencies section names it, but the authoritative AC source for this story (epics-with-stories.md's own Given/When/Then blocks, per this session's own instructions to read that file for each story's ACs) tests only pass/fail reporting for both scans — never an inventory write. Implementing an unwritten heuristic (which env vars map to which "observed" scope name, at what confidence) would be exactly the kind of speculative surface Simplicity First forbids. Recorded as a deferred-work item so Story 1.7 (or a future Epic-1 hardening pass) can pick it up with its own AC, rather than silently baked into this story's untested code.

**Why `--secrets` accepts a file OR a directory, dispatching internally:** mirrors `scan_file_for_secrets`/`scan_directory_for_secrets`'s own existing split (Story 1.3) — an operator pointing `audit --secrets` at one suspicious file shouldn't have to wrap it in a directory first.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1-1.5's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys audit --drift` -- expected: `keys audit: [drift] clean: <path to _http.py>`, exit 0
- `pixi run -e pyforge-steward pyforge-steward-dogfood` -- expected: exits 0

**Results (2026-08-07):** all green — see the consolidated Verification note after Story 1.7.

</intent-contract>
