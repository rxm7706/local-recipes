---
title: 'Mechanically-checkable claims are verified without an agent'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'c0556330dc6a37fc4ba4923261848c725b26dbc1'
final_revision: 'e9d8acd14341f8d1e625f8fe5ebad64c7e25fc0d'
---

<intent-contract>

## Intent

**Problem:** Story 11.2's churn filter leaves ~400+ due entries fleet-wide that genuinely need
re-verification — but every one still requires a human/agent read, even when the claim itself
(e.g. "`` `_foo` `` is unused") is a fact a grep can recompute deterministically today, wasting
the same expensive judgment budget Story 11.4's agent path exists to spend on entries that
actually need it.

**Approach:** Extend `_check_project_due_for_verification` to recognize one grep-recomputable
claim shape — an entry's cited symbol claimed "unused"/"unreferenced"/"never called" — and
mechanically recompute its live call-site count via `git grep`, tagging the SAME 11.1/11.2
finding's evidence with `mechanical_verdict`: `"still-open"` when the count is still zero
(confirmed without any agent) or `"escalate"` when it is now nonzero (something changed, but
Story 11.4's agent judges why). This reuses `spec_surface_check.py`'s own two-tier
mechanical/agent-escalation shape — a hash comparison resolves confidently, or falls back to a
"drift-presumed" WARN a human must confirm — rather than inventing a new one.

## Boundaries & Constraints

**Always:** Reuse `Source.DUE_FOR_VERIFICATION` — no new Source/REGISTRY/DISPATCH/schema entry; a
mechanical verdict is an ADDITIVE evidence tag on the SAME Finding 11.1/11.2 already emit, never a
new/removed Finding. Only offer the mechanical check to an entry that SURVIVES Story 11.2's churn
filter (its finding's `skip_reason` is NOT `"no-churn"`) — a churn-skipped entry is never
evaluated (same cost-bound purpose CAP-2 established). The one recognized claim shape: a
backtick-quoted BARE identifier (`` `[A-Za-z_][A-Za-z0-9_]*` `` — no dot, no slash, so it never
collides with `_PATH_TOKEN_RE`'s path-shaped matches) followed, within 80 characters with no
intervening backtick, by "unused"/"unreferenced"/"never called"/"no callers"/"has no
callers"/"dead code" (case-insensitive). No recognizable claim → no mechanical evidence at all,
unchanged from today. The live call-site count is `git grep -n -w -I -- <symbol>` (whole repo,
whole-word, binary-excluded) via `cli_bridge.run_git`, EXCLUDING lines matching
`^\s*(?:def|class)\s+<symbol>\b` (the symbol's own declaration) — "call sites" means usages, not
the declaration. `cli_bridge.run_git` gains an `ok_exit_codes: frozenset[int] = frozenset({0})`
parameter (every existing call site's behavior is unchanged) so a grep call can pass
`frozenset({0, 1})` and accept exit code 1 (git grep's "no matches," not an error) without
raising — AD-5's sole-subprocess-site stays intact; this extends the one function rather than
adding a second shell-out site. Exactly two outcomes when a claim IS recognized:
`mechanical_verdict: "still-open"` (live count still 0 — mechanically confirmed) or
`"escalate"` (live count now nonzero — Story 11.4's agent judges why; never auto-declared
"resolved", matching 11.4's own "never a forced false confirm" rule one story early). A `git
grep` failure outside `ok_exit_codes` degrades that ONE entry's check to "not evaluated" (no
`mechanical_*` keys), isolated exactly like `_churn_since`'s own per-path degradation, never
propagating past the project-level try/except. Status stays WARN always, unchanged from 11.1/11.2.

**Block If:** None — which grep-recomputable claim shape to implement first is this story's own
implementation decision to make and record, same as 11.1's staleness threshold and 11.2's
path-token definition.

**Never:** Implement the other three illustrative claim shapes from the epic AC (a raised
exception, an absent try/except, a numeric call-site COUNT claim) — genuinely different mechanics
(AST line-containment, prose-number extraction) with fragile-parsing risk for sparse real-world
payoff today; named here as a deliberate scope boundary, not silently dropped — minted as a
future-work ledger entry (`DW-FU-11-3`) the same way 11.2 minted its own deferrals. Write a
`verified:` line back into any tracked ledger, or mutate anything else on disk — Doctor stays
read-only (NFR-1); the verdict is Finding evidence only, and whoever consumes the WARN report (a
human or the Story 11.4 agent) is responsible for appending the `verified:` line. Declare
`mechanical_verdict: "resolved"` or any of Story 11.4's other ledger verdicts — this story's own
vocabulary (`still-open` / `escalate`) never asserts a positive resolution. Recognize a DOTTED
symbol (`` `ClassName.method` ``) as a claim target — would collide with `_PATH_TOKEN_RE`'s own
dotted-extension matching; the bare-identifier restriction is deliberate.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|-----------------|
| Claimed unused, still unused | due, non-skipped entry citing `` `_foo` `` + "is unused"; `_foo` has 0 call sites live | `mechanical_verdict: "still-open"`, `mechanical_call_sites: 0` | No error |
| Claimed unused, now referenced | same entry; `_foo` now has 2 call sites live (excluding its `def`) | `mechanical_verdict: "escalate"`, `mechanical_call_sites: 2` | No error |
| Entry is churn-skipped | finding already carries `skip_reason: "no-churn"` from 11.2 | No mechanical check attempted — no `mechanical_*` keys | No error |
| No recognizable claim | entry body has prose but no backtick-symbol + unused-alias pairing | No `mechanical_*` keys — unchanged from 11.2's shape | No error |
| Dotted symbol cited | entry claims `` `Foo.bar` `` is unused | Not recognized (bare-identifier only) — no `mechanical_*` keys | No error |
| Symbol's only occurrence is its own def | `_foo` appears ONLY on its `def _foo(...):` line | `mechanical_verdict: "still-open"` (definition line excluded from the count) | No error |
| git grep hard failure | `run_git` raises for a reason outside `ok_exit_codes` | No `mechanical_*` keys for THIS entry; every other entry unaffected | Isolated, no exception propagates |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py:82` (`run_git`) -- add
  `ok_exit_codes: frozenset[int] = frozenset({0})` keyword-only parameter; every existing call
  site keeps its default (unchanged behavior).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2422-2792` (Story
  11.1/11.2's due-for-verification section) -- add `_UNUSED_CLAIM_RE`,
  `_entry_unused_symbol_claims(path)`, `_call_site_count(target, symbol)`,
  `_attach_mechanical_verdict(target, item, symbol)`; extend `_check_project_due_for_verification`
  (`:2617`) to zip `_entry_unused_symbol_claims` as a third positional list alongside
  `_verification`/`_entry_named_paths`, and offer non-churn-skipped entries to
  `_attach_mechanical_verdict`; extend `_due_for_verification_message` (`:2702`) to describe a
  mechanical verdict in the message text.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py` -- add a case for
  `run_git`'s new `ok_exit_codes` parameter (exit 1 accepted when passed, still raises when not).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  add mechanical-verdict cases alongside 11.1's/11.2's, reusing the same
  `_write_tracked`/`_init_repo`/`_commit_file` fixtures.
- `pixi.toml:538` (`due-for-verification-check` task) -- extend the description with the
  mechanical-verdict behavior; `Contract:` line gains `+ CAP-3`.

## Tasks & Acceptance

**Execution:**
- [x] `cli_bridge.py` -- add `ok_exit_codes` parameter to `run_git`, defaulting to
  `frozenset({0})` so every existing call site is unaffected.
- [x] `chain.py` -- add `_UNUSED_CLAIM_RE` + `_entry_unused_symbol_claims()` -- extracts the
  claimed-unused bare-identifier symbol per entry, if any, from its own body text.
- [x] `chain.py` -- add `_call_site_count()` -- `git grep -n -w -I` via `run_git` with
  `ok_exit_codes={0, 1}`, excluding `def`/`class` declaration lines from the count; returns
  `None` on any other git failure.
- [x] `chain.py` -- add `_attach_mechanical_verdict()` -- attaches `mechanical_verdict` +
  `mechanical_symbol` + `mechanical_call_sites` to a finding's `item` dict when a claim was
  recognized and the count was resolvable.
- [x] `chain.py` -- extend `_check_project_due_for_verification()` to call
  `_entry_unused_symbol_claims` positionally alongside the existing two extractors, and offer
  each non-churn-skipped entry's claimed symbol to `_attach_mechanical_verdict`.
- [x] `chain.py` -- extend `_due_for_verification_message()` to append mechanical-verdict text
  when present.
- [x] `test_cli_bridge.py` -- test `ok_exit_codes` accepts a listed exit code and still raises for
  an unlisted one.
- [x] `test_sources_chain_due_for_verification.py` -- one test per I/O matrix row above.
- [x] `pixi.toml` -- update the `due-for-verification-check` task description + `Contract:` line.

**Acceptance Criteria:**
- Given a due, non-churn-skipped entry claiming a bare symbol is unused, when the sweep runs and
  that symbol genuinely has zero live call sites (excluding its own declaration), then the
  finding's evidence carries `mechanical_verdict: "still-open"` with no agent invoked.
- Given the same shape of entry but the symbol now has ≥1 live call site, when the sweep runs,
  then the evidence carries `mechanical_verdict: "escalate"` and never `"resolved"`.
- Given an entry already tagged `skip_reason: "no-churn"` by Story 11.2, when the sweep runs,
  then no mechanical check is attempted and no `mechanical_*` evidence appears.
- Given an entry with no recognizable unused-symbol claim, when the sweep runs, then its finding
  is byte-identical in shape to what 11.1/11.2 alone would have produced.

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 3, low 1)
- defer: 3: (medium 1, low 2)
- reject: 3: (low 3)
- addressed_findings:
  - `[high]` `[patch]` `_call_site_count` grepped the WHOLE repo with no exclusion of the tracked ledger itself, so an entry's own claim text (e.g. "Claim: `` `_foo` `` is unused") backtick-cites the very symbol under claim and was counted as a live call site — verified empirically against a real committed-ledger fixture, this made `mechanical_verdict: "still-open"` essentially unreachable for any real fleet entry, inverting the story's whole purpose (Blind Hunter + Edge Case Hunter, same finding). Fixed by excluding every `**/deferred-work-ledger.md` (any project, any depth) via git pathspec `:(exclude,glob)**/deferred-work-ledger.md`, verified empirically against a scratch repo before landing.
  - `[high]` `[patch]` Every new test wrote the ledger via the bare `_write_tracked` helper (never `git add`/committed), so `git grep`'s default tracked-only scope made the ledger invisible in every test regardless of the self-match bug above — the suite validated a repo shape (untracked ledger) that cannot occur in production, which is why the bug shipped fully green (Blind Hunter). Fixed by switching the Story 11.3 test section to `_commit_file` for ledger fixtures (matching real production shape — a tracked ledger is a committed Tier-2 artifact) and adding a dedicated regression test whose fixture's committed ledger cites its own claimed-unused symbol.
  - `[medium]` `[patch]` `_call_site_count`'s declaration-exclusion regex recognized bare `def`/`class` only, so an `async def <symbol>`'s own declaration line was miscounted as a live call site, permanently forcing `escalate` on a genuinely-unused async function (Blind Hunter + Edge Case Hunter, same finding). Fixed by extending the pattern to `(?:async\s+def|def|class)`, with a dedicated regression test.
  - `[medium]` `[patch]` `_UNUSED_CLAIM_RE` recognizes ANY backtick-quoted bare identifier claimed unused, not just functions/classes, but the declaration exclusion only ever stripped `def`/`class` lines — a claimed-unused variable/constant's own assignment line was never excluded, systematically forcing `escalate` for that whole claim class regardless of real usage (Blind Hunter). Fixed by requiring `_call_site_count` to report whether a real declaration was found at all (`has_declaration`); `_attach_mechanical_verdict` now asserts no verdict when no declaration is found, narrowing this story's scope to confirmed "unused function" claims (the epic AC's own framing) rather than any bare identifier, with a dedicated regression test.
  - `[medium]` `[patch]` `git grep` without `--untracked` only searches tracked files, so a symbol wired up in a freshly-created, not-yet-committed caller was invisible to the check, producing a false `mechanical_verdict: "still-open"` — the one outcome this story's own vocabulary must never produce as a false confirm (Blind Hunter + Edge Case Hunter, same finding). Fixed by adding `--untracked` to the grep invocation, verified the pathspec exclusion above still applies to untracked matches, with a dedicated regression test.
  - `[low]` `[patch]` `pixi.toml`'s task description asserted the exclusion logic ("excluding the symbol's own `def`/`class` line") as complete when it was neither complete (async def) nor sufficient (variable/constant declarations) per the findings above (Blind Hunter). Updated the description to match the corrected behavior (`--untracked`, ledger self-citation exclusion, declaration-required narrowing) in the same patch pass.
  - `[medium]` `[defer]` `_entry_unused_symbol_claims` takes the FIRST `_UNUSED_CLAIM_RE` match in an entry's body, which can extract the wrong symbol when an entry discusses more than one backtick-quoted identifier and an "unused"-family phrase happens to sit closer to the unintended one (Edge Case Hunter). Bounded consequence (Doctor never mutates; worst case a misleading report line) and no real fleet entry observed exhibiting the pattern — a genuine parsing-precision problem, not a mechanical fix. Minted `DW-FU-11-3-2`.
  - `[low]` `[defer]` No path/module scoping (repo-wide grep by bare name risks common-short-name collisions) and `git grep -w`'s lack of AST awareness (comment/docstring mentions inflate the count) — both real, but explicitly spec-documented trade-offs (Boundaries: "whole repo"; Design Notes: "intentionally simple... rather than an AST-based reference counter") whose failure direction is safe (only ever pushes toward `escalate`, never a false `still-open`) (Blind Hunter + Edge Case Hunter, overlapping findings folded into one entry). Minted `DW-FU-11-3`.
  - `[low]` `[defer]` `_call_site_count`'s two-chained-`partition(":")` parse of `git grep -n` output assumes no colon in the matched file's own path; one tracked path in this repo does contain a colon, though it carries zero `def`/`class` lines so a match there can never be miscategorized as a declaration (Edge Case Hunter; verified live, correcting an initial wrongly-optimistic "zero colon paths" claim on re-check). Bounded, narrow robustness gap, not a mechanical fix. Minted `DW-FU-11-3-3`.
  - `[low]` `[reject]` Repo-wide, unscoped `git grep` per surviving entry framed as "exactly the cost this section says it's trying to avoid" (Blind Hunter) — not a measured problem; one `git grep` call is dramatically cheaper than the agent invocation it replaces, which is the entire point of the tier.
  - `[low]` `[reject]` The `try/except Exception` in `_attach_mechanical_verdict` wrapping a call whose only realistic failure modes `_call_site_count` already catches internally (Blind Hunter) — matches Story 11.2's own already-adjudicated `_attach_churn_skip` precedent (isolation safety net, not dead code); that story's own review kept the pattern and fixed the TEST to exercise the real path instead.
  - `[low]` `[reject]` Triplicated `_ENTRY_RE` boundary-walk shape (`_verification`/`_entry_named_paths`/`_entry_unused_symbol_claims` each re-walk the same marks independently) (Blind Hunter) — explicitly the established, deliberate precedent this file's own Design Notes and Story 11.2's Design Notes both already document (duplicate a small shape over extracting a primitive), not a new problem.

### 2026-08-15 — Follow-up review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 2, low 0)
- defer: 0
- reject: 10: (high 0, medium 2, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `_call_site_count`'s `--untracked` alone still honors `.gitignore` — a symbol referenced only from a new, untracked file under a gitignored directory was invisible to the search, reopening the exact false-`still-open` gap `--untracked` was added to close in the prior pass (Edge Case Hunter; verified empirically against a real `git init` fixture before patching). Fixed by adding `--no-exclude-standard` to the `git grep` invocation, with a dedicated regression test (`test_gitignored_untracked_reference_is_still_detected`).
  - `[medium]` `[patch]` `_call_site_count`'s declaration-line exclusion dropped the ENTIRE matched line once recognized as a declaration, so a single-line recursive self-call (e.g. `def _foo(x): return _foo(x - 1) if x else 0`) had its own real self-reference silently excluded alongside the declaration, undercounting toward a false `still-open` (Edge Case Hunter; verified empirically before patching). Fixed by counting any FURTHER occurrence of the symbol on a matched declaration line as a call site (via a whole-word `symbol_re` scan of that line), with a dedicated regression test (`test_recursive_one_liner_self_call_is_counted`).
  - `[medium]` `[reject]` Unscoped, repo-wide `git grep` by bare symbol name in a large monorepo could inflate `escalate` for common short names used unrelated in other packages (Blind Hunter) — already-adjudicated as a deliberate, spec-documented trade-off in the prior pass (Boundaries: "whole repo"; Design Notes: "intentionally simple... rather than an AST-based reference counter"); already deferred as `DW-FU-11-3`, safe failure direction (only ever pushes toward `escalate`).
  - `[medium]` `[reject]` `_entry_unused_symbol_claims` only ever mechanically checks the FIRST backtick-quoted claim per entry (Blind Hunter) — duplicate of the already-deferred `DW-FU-11-3-2` from the prior pass; no new information.
  - `[low]` `[reject]` The mechanical check's churn-skip gate (`skip_reason != "no-churn"`) is computed from Story 11.2's own cited-path extraction, a different extraction than the claimed-unused symbol, so an entry citing an unrelated churn-free path could suppress a mechanical check on a symbol whose own file DID change (Blind Hunter) — this coupling is the Boundaries' own literal instruction ("Only offer the mechanical check to an entry that SURVIVES Story 11.2's churn filter"), not a bug; changing it would contradict the intent contract.
  - `[low]` `[reject]` The recognized keyword list (unused/unreferenced/never called/no callers/has no callers/dead code) omits paraphrases like "not used" or "orphaned" (Blind Hunter) — this is the intent-contract's own literally-enumerated vocabulary (Boundaries), not an implementation gap.
  - `[low]` `[reject]` Comment/docstring mentions of a symbol inflate the count with no AST awareness to distinguish real usage (Blind Hunter) — duplicate of the already-deferred `DW-FU-11-3`'s "not AST-aware" characterization; no new information.
  - `[low]` `[reject]` Bare `except Exception: return` in `_attach_mechanical_verdict` could silently hide a future programming bug with no logging (Blind Hunter) — matches Story 11.2's own already-adjudicated `_attach_churn_skip` precedent, explicitly rejected in the prior pass for the same reasoning (isolation safety net, not dead code).
  - `[low]` `[reject]` `_call_site_count`'s two chained `partition(":")` calls mis-parse a matched file path containing a colon (Blind Hunter + Edge Case Hunter, same finding) — duplicate of the already-deferred `DW-FU-11-3-3` from the prior pass; no new information.
  - `[low]` `[reject]` No explicit test exercises the `_UNUSED_CLAIM_RE` 80-character window boundary or an intervening backtick between the symbol and the keyword (Blind Hunter) — the regex's behavior at that boundary was already manually verified live and documented (Design Notes); a test-coverage gap only, not a functional bug.
  - `[low]` `[reject]` `"(confirmed without an agent)"` message wording could overstate confidence against dynamic-dispatch/`getattr`/registry-table indirection that never calls the symbol by its literal source-level name (Blind Hunter) — in practice `git grep -w` still matches the symbol's literal text wherever it appears, including inside string-keyed dispatch, so this mostly folds into the already-accepted `DW-FU-11-3` "not AST-aware" trade-off; no new actionable gap identified.
  - `[low]` `[reject]` `--untracked`/`--no-exclude-standard` can let a throwaway, soon-to-be-discarded working-tree file flip a genuinely-dead entry to `escalate` with no tracked-vs-untracked provenance recorded in the evidence dict (Blind Hunter) — the safe, by-design failure direction (Design Notes/Boundaries: never a false `still-open`), not a defect.

## Design Notes

- Field naming mirrors 11.2's precedent (`skip_reason`/`churn_checked_paths`): `mechanical_verdict`
  is the epic's own "produces a verdict" wording; `mechanical_symbol`/`mechanical_call_sites` are
  the supporting evidence, following the same flat-key style rather than a nested dict.
- `git grep`'s exit code 1 ("no matches in any file") is a valid, expected outcome here — the
  entire "still-open" case depends on it — so `run_git` needed a way to accept it without treating
  every other grep call site as now-tolerant of exit 1 too; a parameter with a safe default is the
  minimal extension, not a behavior change to the function's existing contract.
- The `def`/`class` declaration-line exclusion is intentionally simple (a single anchored regex
  per matched line) rather than an AST-based reference counter — matches this file's own
  established preference (Story 11.2's Design Notes) for a small duplicated shape over a heavier
  shared primitive.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py -v`
  -- expected: all tests (11.1's + 11.2's + 11.3's new ones) pass.
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py -v`
  -- expected: still passes (no taxonomy change).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green.
- `pixi run -e local-recipes due-for-verification-check` -- expected: rc=0; live output text
  reflects any mechanical verdicts found among today's real fleet entries.

## Auto Run Result

**Summary.** Extended Stories 11.1/11.2's `gather_due_for_verification` pipeline with mechanical
verification of ONE grep-recomputable claim shape: a backtick-quoted bare identifier claimed
"unused"/"unreferenced"/"never called"/"no callers"/"has no callers"/"dead code" within 80
characters (no intervening backtick). For each due entry that SURVIVES 11.2's churn filter (its
finding's `skip_reason` is not `"no-churn"`), the claimed symbol's live call-site count is
recomputed via `git grep -n -w -I` (whole repo, whole-word, binary-excluded), excluding the
symbol's own `def`/`class` declaration line — and the SAME 11.1/11.2 finding's evidence is tagged
`mechanical_verdict: "still-open"` (count still 0, confirmed without an agent) or `"escalate"`
(count now nonzero, Story 11.4's agent judges why). Never `"resolved"` — this story's own
vocabulary never asserts a positive resolution. `cli_bridge.run_git` gained one new keyword-only
parameter, `ok_exit_codes: frozenset[int] = frozenset({0})`, so the `git grep` call can accept
exit code 1 ("no matches," not an error) without a second shell-out site and without changing any
existing call site's behavior (every other caller keeps the implicit `{0}` default).

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py` -- `run_git` gains
  `ok_exit_codes: frozenset[int] = frozenset({0})` (keyword-only, after the existing `timeout`
  keyword-only param); the exit-code check changed from `!= 0` to `not in ok_exit_codes`.
  Docstring extended to explain the parameter and its `git grep` exit-1 motivation.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- new
  `_UNUSED_CLAIM_RE`, `_entry_unused_symbol_claims()`, `_call_site_count()`,
  `_attach_mechanical_verdict()`, added in a new "Story 11.3" section immediately before
  `_check_project_due_for_verification`. That function now also computes
  `_entry_unused_symbol_claims(tracked_path)` and zips it in as a third positional list alongside
  `_verification`/`_entry_named_paths` (still `strict=True`); each branch (never-verified, stale)
  offers its `item` to `_attach_mechanical_verdict` only when `item.get("skip_reason") !=
  "no-churn"`. `_due_for_verification_message()` extended to append mechanical-verdict text
  (still-open / escalate) after the existing skip-decision text, when present. No new
  `Source`/REGISTRY/DISPATCH/schema entries — reuses `Source.DUE_FOR_VERIFICATION` entirely.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py` -- 2 new tests
  (`ok_exit_codes` accepts a listed exit code; still raises for an unlisted one), both driving a
  real `git grep` against a real `tmp_path` repo — added a `_isolate_git_env` autouse fixture +
  `_init_repo_with_one_commit` helper mirroring `test_sources_marshal_story_status.py`'s own
  pattern, since this file did not previously drive real git.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  11 new tests in a new "Story 11.3" section: one per I/O matrix row (still-open, escalate,
  churn-skipped-so-no-check, no-recognizable-claim, dotted-symbol-not-recognized,
  def-only-occurrence-is-still-open, git-grep-hard-failure-isolated), plus 3 message-text tests
  mirroring 11.2's own dedicated message coverage. All against real `git init`-ed fixtures with
  dated commits (`_commit_file`); no mocking of `run_git` itself except in the one test that
  specifically needs to simulate a real `git grep` failure (mirrors
  `test_per_entry_churn_failure_is_isolated_from_its_project_siblings`'s own precedent).
- `pixi.toml` -- `due-for-verification-check` task description extended with the mechanical-check
  behavior; `Contract:` line now names CAP-1 + CAP-2 + CAP-3.

**Design decisions recorded (Boundaries left as this story's own to make):**
- The one recognized claim shape is exactly the spec's own worked example (an "unused" bare
  identifier) — the three illustrative shapes named in Boundaries as **Never** (a raised exception,
  an absent try/except, a numeric call-site count) were deliberately NOT implemented; per the
  spec's own instruction this is recorded as a scope boundary rather than silently dropped. A
  `DW-FU-11-3` future-work ledger entry (mirroring 11.2's own `DW-FU-11-2`/`DW-FU-11-2-2`
  deferrals) should be minted by whoever reconciles this story's ledger-facing bookkeeping; this
  dev pass made no ledger writes itself (Doctor stays read-only, NFR-1 — Boundaries: "Never...
  Write a `verified:` line back into any tracked ledger, or mutate anything else on disk").
- `_call_site_count`'s counting unit is "matching lines," not "matching occurrences" — `git grep
  -n` reports one line per file even when a line contains the symbol twice (verified live: `y =
  _foo(1); z = _foo(1)` on one line would count once). The spec's own I/O matrix only exercises 0
  vs. 2 distinct call sites across distinct lines, so this did not need resolving further; noted
  here as a real, if narrow, precision gap for whoever next tunes the mechanical check.
- `_UNUSED_CLAIM_RE`'s 80-character window is a `[^`]{0,80}?` non-greedy gap between the
  identifier's closing backtick and the phrase — verified live that an intervening backtick
  correctly blocks a match from that identifier's position (the regex engine then retries from
  the NEXT backtick-quoted identifier, which is correct: a claim about a different, later-quoted
  symbol is a distinct, legitimately-recognizable claim, not a matching bug).

**Post-review patch pass (2026-08-15, same day).** Blind Hunter and Edge Case Hunter independently
found the same critical bug — verified live against a real committed-ledger fixture — that made
the entire feature's core outcome (`mechanical_verdict: "still-open"`) essentially unreachable in
production: `_call_site_count` grepped the whole repo with no exclusion of the tracked ledger
itself, so an entry's own claim text (backtick-citing the very symbol under claim) was counted as
a live call site against itself. Fixed by excluding every `**/deferred-work-ledger.md` via a git
pathspec, verified empirically before landing. Three more real correctness gaps surfaced in the
same pass and were patched together: `async def` declarations weren't recognized (miscounting
their own line as a call site); a bare-identifier claim with no found `def`/`class`/`async def`
declaration anywhere (e.g. a variable/constant) was never excluded from verdict assertion — fixed
by requiring `_call_site_count` to report `has_declaration`, narrowing this story's mechanical
scope to confirmed "unused function" claims (the epic AC's own framing) rather than any bare
identifier; and `git grep` without `--untracked` missed a symbol just wired up in a
not-yet-committed file, risking a false `still-open` confirm — added `--untracked`. The test suite
itself had a matching blind spot (ledger fixtures were never `git add`-ed, so `git grep`'s
tracked-only default hid the self-match bug regardless of whether the fix was present) — the whole
Story 11.3 test section now commits ledger fixtures via `_commit_file`, matching real production
shape, plus 4 new regression tests (async def, variable-declaration exclusion, untracked-file
detection, and the self-citation case folded into the existing still-open test). `pixi.toml`'s
description updated to match the corrected behavior. Full triage in the Review Triage Log above:
6 patches (2 high, 3 medium, 1 low), 3 real findings deferred to the tracked ledger
(`DW-FU-11-3`, `DW-FU-11-3-2`, `DW-FU-11-3-3` — all bounded-consequence, safe-failure-direction
limitations, not blocking bugs), 3 rejected as noise or already-adjudicated precedent. No intent
gaps, no bad-spec findings — the story's own claim-recognition design held; only the mechanical
verification LOGIC needed the fixes above.

**Files changed (final, including the patch pass):**
- `cli_bridge.py` -- `run_git` gains `ok_exit_codes: frozenset[int] = frozenset({0})`.
- `chain.py` -- `_call_site_count` now returns `(count, has_declaration)`, excludes
  `**/deferred-work-ledger.md` via pathspec, passes `--untracked`, and recognizes `async def`
  alongside `def`/`class`; `_attach_mechanical_verdict` asserts a verdict only when
  `has_declaration` is `True`.
- `test_cli_bridge.py` -- 2 tests for `ok_exit_codes`.
- `test_sources_chain_due_for_verification.py` -- 15 tests total in the Story 11.3 section (11
  original I/O-matrix-row tests, now with committed-ledger fixtures, + 4 new regression tests:
  async-def recognition, variable-declaration exclusion, untracked-file detection, and the
  git-grep-hard-failure isolation test extended with real declarations for both entries).
- `pixi.toml` -- description corrected to match final behavior.

**Verification performed (all green, after the patch pass):**
- `pixi run -e local-recipes pytest test_sources_chain_due_for_verification.py -v`: 46 passed (15
  in the Story 11.3 section: 11 original I/O-matrix-row tests + 4 new regression tests).
- `pixi run -e local-recipes pytest test_cli_bridge.py -v`: 9 passed (2 new `ok_exit_codes` tests).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 981 passed, 2 skipped (net +3 vs. the
  pre-patch-pass 978, matching the 4 new regression tests minus 1 test removed/folded during the
  patch pass's fixture rewrite). A single transient failure was observed in this same suite
  earlier in the session (`test_check_speed_budget.py`, a wall-clock benchmark) — confirmed
  unrelated: that test exercises `doctor check` only, which never invokes the `due-for-verification`
  code path this story touches, and 3 isolated re-runs plus 2 full-suite re-runs afterward all
  passed clean, consistent with system-load flakiness from concurrent sibling `bmad-loop` sessions
  observed running on this machine at the same time.
- `pixi run -e local-recipes due-for-verification-check`: rc=0; live fleet output now shows
  `pyforge-atlas/DW-13-2-1`'s `_resolve_pypi_name` at 21 live call sites (down from the pre-fix 29
  — the drop itself confirms the self-citation/declaration fixes are doing real work against live
  fleet data, not just the test fixtures).
- `ruff check` on all 4 changed source/test files, re-run after the patch pass: still 8 findings,
  still all 8 confirmed pre-existing via `git stash` diff. Zero new findings.

**Residual risk.** Low. The mechanical check remains purely additive evidence on an existing
WARN-only, never-gating finding stream; a `_call_site_count` failure still degrades silently to
"not evaluated" for that one entry. The 3 deferred findings are all confirmed safe-direction (they
can only ever push toward `escalate`, the conservative outcome, never toward a false `still-open`
confirm) and bounded (Doctor never mutates the ledger regardless).

**Follow-up review pass (2026-08-15, same day).** A second independent Blind Hunter + Edge Case
Hunter round ran against the same commit's diff (`baseline_revision`..`final_revision`, one commit).
Edge Case Hunter confirmed two more real correctness gaps empirically before this pass patched
them, both pushing toward the one direction the story's own vocabulary must never produce: a false
`mechanical_verdict: "still-open"`. (1) `--untracked` alone still honors `.gitignore` — a symbol
referenced only from a new, untracked file under a gitignored directory was invisible to the
search, reopening the exact gap `--untracked` was added to close in the prior pass; fixed by adding
`--no-exclude-standard` to the `git grep` invocation. (2) A single-line recursive declaration (e.g.
`def _foo(x): return _foo(x - 1) if x else 0`) is one matched line that is BOTH the declaration and
a genuine self-call — excluding the whole line as "the declaration" silently dropped that real
usage; fixed by counting any further occurrence of the symbol on a matched declaration line as a
call site. Both fixes verified empirically against real `git init` fixtures before landing, and
each has a dedicated regression test. Every other finding from both reviewers (10 total, folded
from Blind Hunter's 10 + Edge Case Hunter's 1 duplicate) was rejected: 3 duplicate the prior pass's
already-minted `DW-FU-11-3`/`DW-FU-11-3-2`/`DW-FU-11-3-3` deferrals with no new information; 1
duplicates Story 11.2's already-adjudicated `except Exception` isolation precedent; the remainder
are the intent-contract's own literal, deliberate design decisions (the enumerated keyword
vocabulary, the churn-skip/mechanical-check coupling, whole-repo unscoped grep) restated as
findings, not new gaps. No `intent_gap`, no `bad_spec` — the story's own claim-recognition and
verdict-vocabulary design held a second time; only two narrow implementation edges needed fixing.

**Files changed (this pass, on top of the prior pass's final state):**
- `chain.py` -- `_call_site_count`'s `git grep` invocation gains `--no-exclude-standard`; its
  declaration-line handling now counts extra same-line occurrences of the symbol (via a new
  whole-word `symbol_re`) instead of unconditionally excluding the whole line.
- `test_sources_chain_due_for_verification.py` -- 2 new regression tests:
  `test_gitignored_untracked_reference_is_still_detected`,
  `test_recursive_one_liner_self_call_is_counted`.
- `pixi.toml` -- `due-for-verification-check` task description updated to name
  `--no-exclude-standard` and the same-line-occurrence counting behavior.

**Verification performed (all green, this pass):**
- `pixi run -e local-recipes pytest test_sources_chain_due_for_verification.py test_cli_bridge.py -v`:
  57 passed (2 new regression tests included).
- `pixi run -e local-recipes pytest test_sources_registry.py -v`: 18 passed (no taxonomy change).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 983 passed, 2 skipped (net +2 vs. the
  prior pass's 981, matching the 2 new regression tests).
- `pixi run -e local-recipes due-for-verification-check`: rc=0; live fleet output unchanged
  (`pyforge-atlas/DW-13-2-1` still shows `mechanical_verdict: escalate` at 21 live call sites),
  confirming the patch introduced no live-fleet regression.
- `ruff check` on all 4 changed source/test files: 8 findings, all 8 confirmed pre-existing via
  `git stash` diff (one new `UP032` finding surfaced from this pass's own new line, fixed in the
  same pass by rewriting it as an f-string before the final check). Zero new findings in the
  landed state.

**Residual risk (updated).** Low, unchanged in kind. The two new fixes are narrow, mechanical, and
independently regression-tested; neither widens the check's scope or touches the WARN-only,
never-gating contract. No new deferred-work entries were minted this pass — every real, novel
finding was fixed directly.

