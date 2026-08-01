<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'CLI noun-verb structure and global flags'
type: 'feature'
created: '2026-07-30'
status: done
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
final_revision: 'a3f03f199addebe25f70e884555c3fd3620a4cf9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 1.1's dispatcher is a flat, single-level stub: each noun prints "not implemented
yet" and exits `0`, there is no `doctor` command, and there are no global flags — nothing exercises
the noun→verb hierarchy, the `flag → environment → default` precedence AD-13 requires, or the
dependency-direction guard (AD-2) later stories depend on.

**Approach:** Replace the flat parser with a two-level noun→verb argparse tree (verbs added later;
none exist yet), add a top-level `doctor` leaf, wire the five global flags (`--cfe-root`,
`--cfe-python`, `--format`, `--verbose`, `--quiet`) onto every level via a shared parent parser, and
add a `flag → environment → default` resolver applied uniformly. A bare noun with no verb now prints
that noun's own help **to stderr** and exits non-zero, replacing Story 1.1's `exit 0` stub for that case.

> **Contract amended 2026-07-30 (operator-confirmed intent gap).** The I/O matrix's "Bare noun, no
> verb" row previously said **stdout**. It is **stderr**. This is a usage error — it exits
> `EXIT_USAGE` (2) — and the same command's sibling usage-error path (`mason recipe sometypo`, an
> unrecognized verb) already writes to stderr at that same exit code via argparse's own handler, so
> the contract had two exit-2 paths disagreeing on stream. It also contradicted this spec's own
> loaded context: *"every diagnostic, progress line, and log record goes to stderr."*
>
> Scope of the amendment is narrow: **the usage-error path only.** A true bare top-level invocation
> (`mason` with no noun at all) returns `EXIT_OK` and correctly stays on **stdout** — that is help
> output, not a diagnostic, and it is unchanged.
>
> The dev session implemented the row faithfully as written (`ns._noun_parser.print_help()` →
> stdout, then `return EXIT_USAGE`) and the adversarial review caught the contract itself being
> wrong. Because the defect sat inside `<intent-contract>` rather than in implementation guidance,
> the harness routed it as `intent_gap` and refused to let the agent amend its own contract without
> human confirmation. That confirmation is this note.

## Boundaries & Constraints

**Always:** argparse is the sole CLI-parsing library (existing meta test stays green). All five
global flags are optional everywhere; none required for any command to run. Resolution is uniformly
`flag → environment → default`; no `mason.toml`, no Mason-specific `pyproject.toml` key. `main()`
stays sole owner of the exit code, parser construction inside its `try`. `doctor` is listed
top-level alongside the three nouns in `--help` (OQ-A4: top-level). A new meta test statically
confirms (AST, not string matching — Story 1.1's retro finding) that no `.py` file under
`src/pyforge/mason/` other than `cli.py`, `cfe.py`, or `engines/*.py` imports `subprocess`.

**Block If:** none identified — epics.md's Story 1.2 AC plus AD-2/AD-13 fully specify this work.

**Never:** implement actual verb logic (verbs stay unregistered — later epics populate them).
Implement the CFE-root resolution *chain* (upward walk, Story 1.5) — `--cfe-root`/`--cfe-python` are
accepted+resolved, not consumed. Add `--cfe-timeout` (Story 1.10). Wire real logging/verbosity
(Story 1.10) — `--verbose`/`--quiet` accepted+resolved, not consumed. Implement `doctor`'s real
diagnosis (Story 1.8) — stub only. Implement the `mason package --ship <targets>` bare-noun
exception (FR-30) — `package` has no verbs yet. Edit anything under
`.claude/skills/conda-forge-expert/**` (AD-15).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Help surface | `argv=["--help"]` | lists `recipe`, `package`, `environment`, `doctor`, `--version`, five global flags | `SystemExit(0)` |
| Bare noun, no verb | `argv=["recipe"]` (also `package`, `environment`) | prints that noun's own help to **stderr** | exit `EXIT_USAGE` (2) |
| `doctor` invoked | `argv=["doctor"]` | dispatches, no verb required (stub message, per 1.1's pattern) | exit `EXIT_OK` (0) |
| Global flag before/after noun | `["--format","json","recipe"]` or `["recipe","--format","json"]` | flag parses at either position; bare-noun handling still applies | exit 2 |
| Env fallback | `MASON_FORMAT=json` env, no `--format` | resolved format == `"json"` | n/a |
| Flag overrides env | `MASON_FORMAT=json` env + `--format text` | resolved format == `"text"` | n/a |
| Neither set | no flag, no env | resolved format falls back to `"text"` | n/a |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/cli.py` -- flat Story 1.1 dispatcher; becomes noun→verb tree + shared global-flags parser + resolver functions.
- `tests/unit/test_cli.py` -- `test_all_three_verb_groups_are_declared` must change (bare noun no longer `EXIT_OK`); add tests for `--help`, `doctor`, flags, resolver precedence.
- `tests/meta/test_namespace_is_implicit.py` -- existing meta test; unaffected, stays green.
- `tests/meta/test_dependency_direction.py` -- new: AD-2 static subprocess-import guard.

## Tasks & Acceptance

**Execution:**
- [x] `cli.py` -- add a shared `add_help=False` parent parser declaring the five global flags, plus `_resolve_str`/`_resolve_bool` precedence helpers over `os.environ` -- AD-13.
- [x] `cli.py` -- rebuild `build_parser()`: top-level subparsers (`recipe`, `package`, `environment`, `doctor`) each inheriting the global-flags parent; `recipe`/`package`/`environment` each get a nested (currently empty) verb-level subparsers object, remembered via `set_defaults(_noun_parser=...)` -- FR-30, FR-35.
- [x] `cli.py` -- update `main()`: top-level bare invocation unchanged (`EXIT_OK` + help); a noun with no verb prints `ns._noun_parser.print_help()` and returns `EXIT_USAGE`; `doctor` and any noun-with-verb fall through to the existing stub -- FR-30's bare-noun rule.
- [x] `tests/unit/test_cli.py` -- rewrite `test_all_three_verb_groups_are_declared` for `EXIT_USAGE` + verb-help text; add `--help`/`doctor`/flag-acceptance/resolver-precedence tests -- pins the AD-13/FR-30 contract.
- [x] `tests/meta/test_dependency_direction.py` (new) -- AST scan asserting no `.py` file under `src/pyforge/mason/` other than `cli.py`, `cfe.py`, or `engines/*.py` contains an `import subprocess` node -- AD-2, vacuous-but-real today (mirrors `test_namespace_is_implicit.py`'s pinning pattern).

**Acceptance Criteria:**
- Given the installed CLI, when `mason --help` runs, then `recipe`, `package`, `environment`, and `doctor` are all listed.
- Given AD-2, when the CLI module and package tree are inspected, then argparse is the only parsing library (existing test) and no module outside `cli.py`/`cfe.py`/`engines/*` imports `subprocess` (new test).
- Given AD-13, when a global setting is resolved, then precedence is `flag → environment → default` uniformly, and no `mason.toml`/Mason `pyproject.toml` key is ever read.

## Spec Change Log

- 2026-07-30 — (Re)implemented from scratch against the amended (stderr) contract. The prior
  session's work described by the Tasks checkboxes and Review Triage Log below never landed on
  disk (`git log` showed only Story 1.1 had touched `cli.py`; the working tree was clean at that
  commit). This pass builds `cli.py`'s noun -> verb tree, the `_resolve_str`/`_resolve_bool`
  helpers, `tests/unit/test_cli.py`, and the new `tests/meta/test_dependency_direction.py` fresh,
  incorporating the prior review's six patch findings directly (whitespace-stripping in
  `_resolve_str`; accurate single-generic-loop docstring; full-resolved-path allowlist comparison;
  `tmp_path` regression fixtures for the AD-2 guard; clean non-UTF-8 failure; `doctor --help`
  coverage). Full suite green: 39 passed (`pixi run -e pyforge-mason pyforge-mason-test`).
  Deviation found and fixed during implementation: a global flag given *before* the noun (e.g.
  `mason --format json recipe`) was silently clobbered back to `None` by the noun subparser's own
  default, because `_SubParsersAction.__call__` parses each noun's remaining tokens into a fresh
  namespace and unconditionally copies its attributes onto the parent. Fixed by giving all five
  global flags `default=argparse.SUPPRESS` instead of `None`, so a noun subparser only contributes
  an attribute when the flag actually appears among its own tokens — this is what makes the I/O
  matrix's "before/after" row true in practice, not just in the parents=[...] wiring alone.

## Review Triage Log

### 2026-07-30 — Review pass (3)
- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium: 1, low: 6)
- defer: 0
- reject: 16
- addressed_findings:
  - `[medium]` `[patch]` The AD-2 guard's real-tree test had no scan-root existence check — if the
    package layout ever moved, `rglob` over the stale `PKG_ROOT` would yield zero files and the
    guard would pass vacuously forever (found independently by both reviewers). Added
    `assert PKG_ROOT.is_dir()` with an actionable message inside
    `test_no_subprocess_import_outside_the_allowlist`.
  - `[low]` `[patch]` `_resolve_str` returned a padded *flag* value raw (`"  /x  "` → `"  /x  "`)
    while the *env* path returned `raw.strip()` — the same intra-function asymmetry family pass 2
    fixed for whitespace-only values, one case over. Now strips the returned value uniformly at
    both steps; docstring updated; two regression tests added (padded flag, padded env).
  - `[low]` `[patch]` `main()` read `ns.verb` directly, but `doctor`'s namespace carries no `verb`
    attribute at all — only the branch ordering (doctor checked first) prevented an
    AttributeError → EXIT_INTERNAL, and nothing marked that ordering as load-bearing, in a module
    whose own docstring mandates `getattr` for exactly this hazard class. Changed to
    `getattr(ns, "verb", None)` and commented why the doctor branch must stay first regardless
    (verb-less `doctor` is a complete command, not a usage error).
  - `[low]` `[patch]` The inline comment at the verb-level `add_subparsers()` call said later
    stories "call `.add_parser(...)` on this same subparsers object" while the return value is
    discarded on that very line — stale relative to pass 2's docstring fix, which established the
    real mechanism (edit `build_parser()`, capture the return value). Reworded the comment to
    match the docstring.
  - `[low]` `[patch]` `test_unrecognized_verb_is_a_native_argparse_usage_error` asserted merely
    `err != ""`, which any stderr noise would satisfy without proving invalid-choice fired.
    Strengthened to assert the offending token (`sometypo`) appears in the diagnostic.
  - `[low]` `[patch]` No acceptance test covered `--verbose`/`--quiet` at either position, though
    the spec's own task line calls for flag-acceptance tests and the other three flags had them.
    Added a parametrized `test_global_boolean_flags_accepted_at_either_position`.
  - `[low]` `[patch]` `read_text` raising `OSError` (broken symlink, permissions) escaped as a raw
    traceback — the third member of the exact family passes 1–2 patched (UnicodeDecodeError, then
    SyntaxError) under the same stated design goal ("a raw traceback is not an actionable test
    failure"). Added an `except OSError` handler with the same AssertionError pattern and a
    broken-symlink regression test.

**Rejected findings (16 — mostly re-findings of items already rejected in passes 1–2, plus a few
new speculative items; dropped silently per instructions, listed here only for this pass's audit
trail):** resolvers uncalled from `main()`/help "selling env vars as live" (rejected in both prior
passes — matches Design Notes verbatim); env values bypassing `--format`'s `choices` (rejected
twice — Story 1.4's consumption site); no `--no-verbose`/`--no-quiet` negation ("one-way ratchet",
same family as the unreachable explicit-`False` branch rejected in pass 2 — Story 1.10 scope);
`--verbose --quiet` mutual exclusion (rejected twice — Story 1.10); `_FALSY_ENV_VALUES` omitting
`off`/`n`/`f` (rejected in pass 1 — Design Notes define the set verbatim); duplicate flag before
and after the noun with noun-side winning (rejected in pass 2 — universal last-flag-wins CLI
semantics); the `{}` metavar in noun help (rejected in pass 2 — argparse's own rendering of the
spec-mandated empty verb level); the `return EXIT_OK  # pragma: no cover` landing spot as a
"silent-success default" (unreachable by construction — argparse rejects any verb token before
`ns.verb` can be truthy; the later story that registers a verb necessarily lands its dispatch and
tests there); AD-2 bypass via `importlib`/`__import__`/`os.system` (rejected twice — Story
2.1/AD-4's comprehensive process-spawn guarding); non-recursive `engines/` allowlist (rejected
twice — architecture shows a flat `engines/`); `_noun_parser` live-parser-in-namespace and the
missing-`set_defaults`-on-a-future-noun hazard (rejected twice); unknown noun `mason bogus`
untested (argparse-native invalid-choice, same rationale as pass 1's wrong-verb rejection);
flags-only invocation (`mason --format json`) untested (marginal — the bare-invocation path it
lands on is covered); `mason recipe --version` exiting 2 (`--version` is not one of the five
global flags; the spec never asks it to float); `_ENV_*` constants "structurally unbound" to their
flags / registry suggestion (speculative gold-plating — Story 1.4+ wires consumption); relative
`from .subprocess import x` falsely flagged (fantastical trigger — a local module shadowing stdlib
`subprocess` inside this package would deserve the failure anyway).

### 2026-07-30 — Review pass (2)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium: 1, low: 3)
- defer: 0
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` `_find_subprocess_importers` left `ast.parse()`'s `SyntaxError`
    uncaught while the line above it already turned a `UnicodeDecodeError` into a clean
    `AssertionError` for the identical reason ("a raw traceback is not an actionable test
    failure") — a valid-UTF-8 but syntactically-broken `.py` file would defeat that stated
    design goal. Wrapped `ast.parse()` in the same try/except pattern; added a
    `test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback` regression fixture.
  - `[low]` `[patch]` `test_global_string_flags_accepted_at_either_position` asserted only
    `ns.noun`, never the flag's own resolved value — a regression that silently dropped
    `--cfe-root`/`--cfe-python`'s value while still parsing the noun correctly would have
    passed. Added `getattr(ns, attr) == "/tmp/x"` assertions for both positions.
  - `[low]` `[patch]` `_resolve_str` returned a whitespace-only *flag* value verbatim while the
    *environment* path already fell through past whitespace-only values to the next step in the
    chain — an inconsistency within the same function for the same input shape. Rewrote to strip
    and fall through uniformly at both the flag and environment steps; added two regression tests
    (whitespace flag falls through to env; whitespace flag + whitespace env falls back to
    default).
  - `[low]` `[patch]` The module docstring's "single generic loop builds all three verb-bearing
    nouns" claim didn't scope itself against the `doctor` block built immediately after that loop
    outside it, and implied a future story could reach in from outside `build_parser()` to extend
    a stored subparsers object — verified empirically that argparse raises `ValueError: cannot
    have multiple subparser arguments` on a second `add_subparsers()` call, so that extension path
    doesn't exist. Reworded to scope the "single generic loop" claim to the three verb-bearing
    nouns, note `doctor`'s separate construction is by design (OQ-A4), and state the real
    extension mechanism (edit `build_parser()` directly, capture the return value locally).

**Rejected findings (14 — noise/out-of-scope/speculative/already spec-sanctioned or previously
rejected, dropped silently per instructions, listed here only for this pass's audit trail):**
`--verbose`/`--quiet` gaining `MASON_VERBOSE`/`MASON_QUIET` env-var forms read as contradicting
`ARCHITECTURE-SPINE.md`'s Logging convention row ("never a value from the environment") — verified
against the same table: the very next row states config precedence is "flag → environment →
default, uniformly (AD-13)," so the Logging row's phrase reads as restating AD-14/epic-context's
"no log record ever contains an environment-variable *value*" (credential blindness), not a ban on
an env override for verbosity; this story's Design Notes explicitly name `MASON_VERBOSE`/
`MASON_QUIET` as the env vars, so the implementation matches its own loaded spec. The flag→env→
default resolvers being uncalled from `main()`/`build_parser()` (matches Design Notes verbatim,
already rejected last pass under the same rationale). The empty `{}` shown under `mason recipe
--help`'s positional arguments — verified this is argparse's own default rendering for a
subparsers object with zero registered choices (identical output with no explicit `metavar` at
all), an unavoidable, self-resolving artifact of the spec's explicit "currently empty" verb-level
subparsers requirement, not a coding mistake. `_noun_parser` embedding a live `ArgumentParser` in
the `Namespace` (already rejected last pass, unchanged rationale). `doctor_parser`'s
`_noun_parser` default going unread this story (harmless, uniform-by-design across all four
nouns — the actual inconsistency would be treating one noun differently). `doctor` stubbing to
`EXIT_OK` while a bare noun-without-verb now exits `EXIT_USAGE` framed as an asymmetry — it is the
literal, deliberate contract: the I/O matrix mandates `EXIT_OK` for a complete verb-less command
(`doctor`) and `EXIT_USAGE` for an incomplete one (bare `recipe`/`package`/`environment`), two
different scenarios by design. `_resolve_bool`'s unreachable explicit-`False`-overrides-env branch
(matches Design Notes — nothing consumes `--verbose`/`--quiet` this story, no negation flag
exists, zero current consequence). `EXIT_USAGE`/`EXIT_INTERNAL` living in `cli.py` instead of
AD-7's future `exit_codes.py` (pre-existing since Story 1.1, explicitly Story 1.3's job per the
epic's own sequencing, not a new problem this story introduces). `mason doctor`'s scope vs. the
separate `pyforge.doctor` sibling package (speculative naming-coincidence; `mason doctor` is an
already-architected FR-34 capability, unrelated in scope). A duplicate global flag given both
before and after the noun with different values, noun-side winning (standard, universal
argparse/CLI "last flag wins" semantics, true even without subparsers — not a defect). No
`choices` validation on an out-of-choices `MASON_FORMAT` env value (already rejected last pass —
belongs to Story 1.4's consumption site). No test for `--quiet`+`--verbose` mutual exclusion
(already rejected last pass — Story 1.10's behavioral scope). The subprocess-import guard being
bypassable via `importlib`/`__import__` (already rejected last pass — comprehensive process-spawn
guarding is Story 2.1's job). The `engines/`-allowlist's non-recursive `glob` vs. the scanner's
`rglob` (already rejected last pass — speculative, architecture shows a flat `engines/`).

### 2026-07-30 — Review pass
- intent_gap: 1 (high: 1)
- bad_spec: 0
- patch: 6 (medium: 3, low: 3)
- defer: 0
- reject: 10
- addressed_findings:
  - none

**Intent-gap finding (root cause inside `<intent-contract>` — see HALT report for the recommended
resolution):** the I/O & Edge-Case Matrix's "Bare noun, no verb" row states the noun's help prints to
**stdout** while returning `EXIT_USAGE` (2). Empirically verified that argparse's own built-in
usage-error path for the same command (e.g. `mason recipe sometypo`, an unrecognized verb) writes to
**stderr** at the same exit code — the two exit-2 paths in the same command disagree on stream. This
contradicts the stream-discipline principle carried by this spec's loaded `context:` (epic-1-context.md's
"every diagnostic, progress line, and log record goes to stderr") and argparse's own convention. Because
the specific wrong value lives inside the `<intent-contract>` block (the I/O matrix is part of the
contract, not implementation guidance), this is routed as `intent_gap` rather than `bad_spec` per the
step-04 branch rule, even though a clear recommended fix exists (see HALT report) — the contract itself
requires the human owner's confirmation before this file is amended.

**Patch findings (6, moot this pass per cascading order — will be re-triaged after the intent-contract
resolves):** (1) `_resolve_str` should strip whitespace-only env values, matching `_resolve_bool`'s
existing handling; (2) the module docstring's "one builder function per noun" claim over-describes the
actual single generic loop; (3) `test_dependency_direction.py`'s allowlist should compare full resolved
paths, not bare filenames, so a same-named file elsewhere in the tree isn't wrongly exempted; (4) that
test should gain a `tmp_path`-based regression fixture proving its detection logic actually fires on a
violation and correctly permits an allowed file; (5) that test's file read should fail cleanly on a
non-UTF-8 file instead of an unhandled traceback; (6) the noun-level-help test should also cover
`doctor --help`, not just `recipe --help`.

**Rejected findings (10 — noise/out-of-scope/speculative/already spec-sanctioned, dropped silently
per instructions, listed here only for this pass's audit trail):** `_resolve_str`/`_resolve_bool`
being uncalled from `main()` this story (matches Design Notes, intentional); no validation of an
out-of-choices `MASON_FORMAT` env value (validation belongs to the Story 1.4 consumption site, nothing
consumes it yet); `_resolve_bool` accepting any non-falsy string as true, e.g. a "flase" typo (matches
the spec-defined falsy set verbatim, zero current consequence); `set_defaults(_noun_parser=...)`
embedding a live `ArgumentParser` in the `Namespace` (hypothetical future `vars(ns)` misuse, mitigated
by the leading-underscore convention); no test for `--quiet`+`--verbose` interaction (Story 1.10's
behavioral scope, both flags are independently correct and unconsumed here); the `engines/`-allowlist
only covering one directory level (speculative — the architecture spine's structural seed shows a flat
`engines/` with no planned subpackages); the untested wrong-verb case `mason recipe sometypo`
(empirically verified to already produce the correct argparse-native stderr+exit-2 behavior); the
bare-`mason`-vs-bare-noun exit-code asymmetry lacking an explicit written rule (intentional,
FR-30-mandated, already commented in code); `_FALSY_ENV_VALUES` omitting spellings like "off"/"n"
(spec-defined set verbatim, speculative gold-plating); and `os.system`/`os.popen`/dynamic-import
bypassing the AD-2 subprocess-*import* guard (out of this story's literal AC scope — "no module
imports subprocess" — comprehensive process-spawn guarding is AD-4/Story 2.1's job once `cfe.py` is
actually built).

## Design Notes

`main()` doesn't yet act on resolved flag values — nothing consumes them this story (`--format` →
`render.py`, Story 1.4; `--cfe-root`/`--cfe-python` → resolution chain, Stories 1.5–1.6;
`--verbose`/`--quiet` → logging, Story 1.10). Precedence is proven by unit-testing `_resolve_str`/
`_resolve_bool` directly. Env var names: `MASON_CFE_ROOT`, `MASON_CFE_PYTHON`, `MASON_FORMAT`,
`MASON_VERBOSE`, `MASON_QUIET` (falsy: absent/`""`/`"0"`/`"false"`/`"no"`, case-insensitive).

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green.

## Auto Run Result

**Status:** done (follow-up review pass 3 on a `done` spec, invoked by the orchestrator).

**Summary:** Fresh adversarial + edge-case review of the Story 1.2 change (baseline `e868b607a1` →
`bb58827034`). No intent gaps, no spec defects, no loopback. Seven patch findings fixed in place
(1 medium, 6 low); sixteen findings rejected, most as re-findings of items already triaged out in
passes 1–2. Zero findings deferred — nothing pre-existing surfaced, so the deferred-work ledger
was not touched.

**Files changed this pass (commit `a3f03f19`):**
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py` — `_resolve_str` now strips the
  returned value uniformly at the flag and env steps; `main()` reads `verb` via
  `getattr(ns, "verb", None)` with the doctor-branch ordering documented; stale verb-registration
  comment aligned with the module docstring.
- `src/shared/packages/pyforge-mason/tests/meta/test_dependency_direction.py` — scan-root
  existence assertion (anti-vacuity); `OSError` handled like the existing decode/parse failures;
  broken-symlink regression test.
- `src/shared/packages/pyforge-mason/tests/unit/test_cli.py` — unrecognized-verb assertion
  strengthened to pin the diagnostic; `--verbose`/`--quiet` either-position acceptance test;
  padded-flag and padded-env stripping regression tests.

**Review findings breakdown:** patch 7 (medium 1, low 6) — all fixed; defer 0; reject 16 (audit
trail in the pass-3 triage log entry above).

**Follow-up review recommendation:** false. The fixes are localized and low-consequence — four are
test-only, two are comments/docstrings, and the two behavioral touches (`.strip()` on an
unconsumed resolver's return value; `getattr` hardening on an already-correct branch order) change
nothing any current consumer observes. Pass 3 findings converged to nits; a fourth pass is not
warranted.

**Verification:** `pixi run -e pyforge-mason pyforge-mason-test` → 47 passed (was 42 at
`bb58827034`; +5 tests from this pass). Meta test `test_namespace_is_implicit.py` untouched and
green within that run.

**Residual risks:** the five global flags are accepted and resolvable but deliberately unconsumed
until Stories 1.4–1.10 (spec-sanctioned); the `{}` verb metavar renders in noun help until the
first real verb lands (argparse-native, spec-sanctioned); the AD-2 guard covers the
`import subprocess` form only — comprehensive process-spawn guarding is Story 2.1/AD-4's scope.

