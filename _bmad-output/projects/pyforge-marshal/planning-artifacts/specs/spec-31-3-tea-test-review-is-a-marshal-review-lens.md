---
title: "`tea-test-review` is a marshal review lens"
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      The lens's real end-to-end behavior (invoking tea-test-review, parsing its verdict,
      emitting capped-at-warn findings, refusing cleanly when the AD-9 roster lacks tea) is not
      exercised by an automated test in this pass.
    evidence: |-
      The lens's `instruction` is a prompt for an LLM-driven review session, not code -- the same
      nature as every other shipped bmad-review lens (edge-case-hunter et al.), none of which
      have an automated "run the lens and check its output" test either. What is mechanically
      verified: the lens merges correctly into the resolved lens set, the TOML parses, and the
      review_min_score policy plumbing it depends on composes/renders/loads correctly end-to-end
      against the real installed bmad_loop package.
    location: '_bmad/custom/bmad-review.toml'
    severity: low
  - summary: >-
      New review_min_score validator tests (out-of-range, bool, numeric-string rejection) only
      exercise the project policy layer, not repo_defaults or flags (--set).
    evidence: |-
      Verified this matches the existing, accepted test-depth convention for every sibling
      bmad-loop-adjacent knob: grepped test_policy.py and confirmed stream_capture_kb's own
      rejection tests (test_stream_capture_kb_rejects_an_arbitrary_precision_int_without_raising,
      test_stream_capture_kb_zero_is_legal) are also project-layer only. Not a new gap this story
      introduces; adding flags/repo_defaults coverage for review_min_score alone, without doing
      the same for its five siblings, would be inconsistent scope creep beyond this story's own
      surface.
    location: 'src/shared/packages/pyforge-marshal/tests/unit/test_policy.py'
    severity: low
  - summary: >-
      cli/config.py:125's "Naming any of these 9 keys" comment above _UNSETTABLE_KEYS remains
      stale (pre-existing drift, DW-3-13-1) -- the frozenset now holds 28 members after this
      story's addition, further widening the gap from the literal "9".
    evidence: |-
      Confirmed live: `len(_UNSETTABLE_KEYS) == 28`. This is DW-3-13-1 in
      planning-artifacts/deferred-work-ledger.md, open since Story 3.13, re-verified multiple
      times (most recently 2026-09-05 at 27 members) with "not fixed here" as the established
      precedent each time a story adds a member adjacent to the stale comment -- fixing the
      literal is a dedicated cleanup out of every contributing story's own bounded scope. This
      story added a fresh `verified: 2026-09-07` line to that ledger entry rather than silently
      leaving it un-re-checked.
    location: 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py:125'
    severity: low
baseline_revision: '2b0e4083c3'
---

<intent-contract>

## Intent

**Problem:** TEA is provisioned (steward 46.3) with a real `tea-test-review` CLI and pixi task,
but nothing in `bmad-review`'s lens set uses it, and marshal has no policy knob threading a
`--min-score` value through to it.

**Approach:** Add `tea-test-review` as a new `bmad-review` customize-override lens (never a
harness-policy key, never an in-place skill edit — AD-4), beside the shipped `edge-case-hunter`,
refused cleanly when the AD-9 module roster lacks `tea` (AD-10). Add a new marshal policy SEED
key `review_min_score` (default 80, spec-bmad-suite-lifecycle's own open question 2 answered),
rendered into all 8 loop-home policies, and record the calibration plan in the era-alignment
memlog.

## Boundaries & Constraints

**Always:** the lens lives only in `_bmad/custom/bmad-review.toml` (AD-4); its findings are
`warn`-severity only and never change a run's `done`/`review` routing or Warden's own PR-gate
exit code (matching pixi.toml's own `tea-test-review` task description, and `detectors.yml`'s
existing exclusion of it); `review_min_score` is validated strictly (int, not bool, `[0, 100]`,
the same bound `tea-test-review --min-score` itself enforces), rejected at the `--set` flag
boundary with a clean usage error (matching all 5 sibling bmad-loop knobs — a real gap review
caught and this pass fixed), and follows the exact same SEED-field/merge/render pattern as Story
25.4's five prior bmad-loop knobs; every claim in this spec and its Auto Run Result is
independently re-verified before being written, not assumed (the lesson from 31.1/31.2's own
review passes, both of which caught overstated or unperformed claims — repeated again in this
story's own review pass, see Review Triage Log).

**Never:** never add `tea-test-review` to `detectors`/`detectors-ci` (pixi.toml's own task
description already states this; unchanged here); never let the new policy key touch
`bmad_loop`'s own read schema (verified empirically: its `[review]` parser extracts named keys
and ignores extras — an unknown-key rejection exists ONLY for `[plugins.<name>]` tables, a
different, opt-in mechanism this story does not use); never claim `bmad-loop validate` is fully
green across all 8 loop homes when only the `policy: OK` check is what this story's own scope
proves (one pre-existing, unrelated dirty-worktree finding exists in the marshal loop home,
independently re-confirmed via JSON output before writing this claim).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| TEA provisioned (AD-9 roster has `tea`) | `_bmad/custom/config.toml` has `[modules.tea]` (confirmed, steward 46.3) | Lens applies, runs `tea-test-review` at the resolved `min_score` | Findings capped at `warn`, never change routing |
| TEA not provisioned | `[modules.tea]` absent (a different repo/checkout) | Lens reports zero findings and stops (AD-10 refusal) | Not an error, not a silent skip either — the lens's own instruction states the refusal reason |
| `review_min_score` out of `[0, 100]` or a bool, via `marshal-policy.toml`/`repo_defaults` | e.g. `-1`, `101`, `True` | Falls back to the previous/default value; `MRS-POLICY-003` finding | Reported, never raised (matches every other SEED validator) |
| `review_min_score` via `marshal config --set` | `--set review_min_score=90` | Clean `EXIT_USAGE` naming `--project-policy` | Never reaches `compose()` as a raw string (fixed post-review — see Review Triage Log) |
| `tea-test-review` exits 2/3, or exits 0/1 with an unreadable/malformed JSON verdict | Environment/agent/parse failure, or a genuinely-successful exit with a broken report file | One environment-problem finding, then stop | Never retried, never fabricated from an unread report (hardened post-review) |
| `bmad_loop` loads a rendered policy carrying `[review].min_score` | The extra key is present | Loads cleanly; `ReviewPolicy` has no `min_score` attribute at all | Verified live against the installed `bmad_loop` 0.11 package, not assumed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` -- `_SEED_KEYS` gains
  `review_min_score` (the 33rd key); `DEFAULT_POLICY["review_min_score"] = 80`; new
  `_valid_review_min_score` validator (strict int, not bool, `[0, 100]`); the `seed = {...}`
  merge-composition dict gains its `_merge_field` call; module/`EffectivePolicy` docstrings
  updated (32→33 keys, 16→17 SEED fields); backtick-consistency fix in two docstrings
  (post-review).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py` -- `_FIELD_ORDER` gains
  `review_min_score`; two stale docstring counts fixed in passing (`_iter_fields` said "31 keys",
  already wrong pre-this-story; `_policy_fields_payload` said "32-key" — both now "33").
  **Post-review fix (real regression caught by two independent reviewers):** `review_min_score`
  added to `_PROJECT_POLICY_ONLY_KEYS` and `_UNSETTABLE_KEYS` — without this, `--set
  review_min_score=X` would have silently reached `compose()` as a raw string and produced a
  misleading `MRS-POLICY-003` finding instead of the clean usage error every sibling knob gives.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json` -- `required` and
  `properties` gain `review_min_score` (an int-only `PolicyField`, `additionalProperties: false`
  means this is load-bearing, not decorative); description counts updated to 33.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` --
  `_POLICY_TEMPLATE`'s `[review]` table gains `min_score = 80`; the render function's body gains
  `doc["review"]["min_score"] = seed["review_min_score"].value`; docstrings updated (11→12 mapped
  keys, "five knobs"→"six knobs"); an ambiguous "never a harness key" phrase clarified post-review
  to distinguish "never placed as a harness-policy key" from "a real rendered key the harness
  simply never reads."
- `_bmad/custom/bmad-review.toml` (new) -- the `tea-test-review` lens: `applies_to = "code"`,
  `when` names the AD-9/AD-10 refusal condition, `instruction` is a self-contained prompt (checks
  TEA provisioning, resolves `min_score` from a rendered `.bmad-loop/policy.toml` if present else
  the 80 default, runs the real pixi task, caps findings at `warn`). **Hardened post-review:** the
  instruction now explicitly treats a killed/timeout/unexpected exit code and an unreadable or
  unparseable JSON verdict file both as environment failures (not silent fabrication), specifies
  a 30-minute wall-clock budget matching the tool's own `--timeout-ms` default, requires deleting
  the temp `--json` file after reading it, and falls back to the 80 default when an ancestor
  `policy.toml`'s `min_score` key exists but doesn't parse as a plain integer.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/{.memlog.md,SPEC.md}`
  -- `.memlog.md` gained the primary dated `(decision)` entry (calibration plan, first ten PRs);
  `SPEC.md`'s CAP-13 prose gained a short outcome summary, following the same
  memlog-first-SPEC.md-second convention 31.2's own review pass established for this exact spec.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- appended a
  fresh `verified: 2026-09-07` line to the pre-existing, open `DW-3-13-1` entry (stale key-count
  comment in `cli/config.py`), following that entry's own established re-verification precedent
  rather than leaving it silently unchecked (post-review — Blind Hunter flagged the story's own
  count-bump as adjacent, unaddressed drift).
- Test files: `tests/unit/test_policy.py` (6 new tests for `_valid_review_min_score`'s full
  matrix, 2 with a `path == "project"` assertion added post-review for consistency with the
  first; 2 existing key-count tests renamed 16→17/32→33 and extended), `tests/unit/test_cli.py`
  (1 existing key-count test renamed 32→33 and extended; 1 existing `--set`-usage-error
  parametrized test extended with `review_min_score` post-review), `tests/unit/test_harness_policy_render.py`
  (1 existing composition test renamed and extended — corrected post-review from an arithmetic
  slip, "7 keys/7th knob", to the accurate "6 keys/6th knob"; the defaults-composition test
  extended; the installed-`bmad_loop`-load test gained an explicit `hasattr` assertion proving the
  extra key is truly inert, not silently coerced into something else).
- `~/.bmad-loops/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/.bmad-loop/policy.toml`
  -- re-rendered via `marshal config --project <slug> --write-harness-policy <home>` (a narrowly-
  scoped, idempotent, git-state-untouching command — confirmed via its own `--help` text before
  running it against these real, shared loop homes); each now carries `min_score = 80`.

## Tasks & Acceptance

**Execution:**
- `core/policy.py`, `cli/config.py`, `schemas/policy.json`, `adapters/harness_bmadloop.py` -- add
  the `review_min_score` knob end-to-end (done, verified via `pixi run -e pyforge-marshal
  pyforge-marshal-test`; `--set` rejection gap fixed post-review).
- `_bmad/custom/bmad-review.toml` -- the lens definition (done, verified via
  `resolve_customization.py` merging it into the resolved 6-lens set; hardened post-review for
  exit-code/JSON-parse edge cases).
- Re-render all 8 loop-home policies; verify `bmad-loop validate`'s `policy: OK` line for each
  (done; re-confirmed via fresh JSON output during the review pass).
- Record the calibration plan in `spec-bmad-611-era-alignment`'s `.memlog.md`, summarized in
  `SPEC.md` (done).
- Reconcile the 5 foreign spec-surface entries `core/policy.py`/`cli/config.py`/
  `schemas/policy.json`/`adapters/harness_bmadloop.py`/`tests/unit/test_policy.py` tripped
  (`spec-adaptive-model-tiering`, `spec-bmad-loop-intent-gap-work-preservation`,
  `spec-horizontal-run-concurrency`, `spec-marshal-token-economy`, `spec-pyforge-marshal`) — done,
  scoped `--write-baseline` stamps applied to all 5.

**Acceptance Criteria:**
- Given the pixi task from steward 46.3, when the review step's `bmad-review` override runs
  `tea-test-review` as a lens beside `edge-case-hunter`, then its findings are appended as
  `warn`-severity observations and the run's `done`/`review` routing is unchanged by the score
  (by design: the lens's own instruction caps severity at `warn` and forbids treating a finding
  as sign-off-revoking; not independently exercised end-to-end against a real PR in this pass —
  see Design Notes and the `deferred` list).
- Given the AD-9 roster lacks `tea`, when the lens would otherwise apply, then it is refused
  (zero findings, not an error) — by the lens's own instruction; not independently exercised
  against a roster genuinely lacking `tea` in this pass (this repo's own roster has it).
- Given `bmad-loop validate` runs, then it is 8/8 for the specific claim this story makes
  (`policy: OK` on all 8 loop homes) — verified directly via fresh JSON output; NOT a claim that
  every other validate check (e.g. git-worktree cleanliness, unrelated to this story) is also
  green everywhere (marshal's own home has one pre-existing, unrelated `FAIL`).
- Given the knob defaults to 80, when composed with no override, then `DEFAULT_POLICY["review_min_score"]
  == 80` and the calibration plan is recorded in the era-alignment memlog (verified).
- Given a project attempts `marshal config --set review_min_score=X`, then it is rejected with a
  clean usage error identical in shape to its 5 sibling knobs, never a `MRS-POLICY-003` finding
  (verified post-review; this criterion was not part of the original draft and was added because
  review caught a real regression against the established sibling-knob pattern).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 12 findings — high 0, medium 3, low 8, false 0, maybe-false 1
- findings:
  - `[medium]` `[patch]` Verification Gap (+ Edge Case Hunter, same root, independently found):
    `review_min_score` was omitted from `_PROJECT_POLICY_ONLY_KEYS` and `_UNSETTABLE_KEYS` in
    `cli/config.py`, unlike its 5 sibling bmad-loop knobs — traced the live code path
    (`_parse_set_item` -> `_parse_set_flags` -> `compose()`'s `_valid_review_min_score("90")`
    returning `None`) and confirmed `--set review_min_score=90` would silently discard the
    operator's value and report a misleading `MRS-POLICY-003` finding instead of `EXIT_USAGE`,
    reintroducing for this one key the exact defect `test_config_set_on_idle_threshold_minutes_is_a_usage_error`'s
    own docstring says was already fixed for the others. Fixed: added to both frozensets; added
    `review_min_score` to the existing parametrized `--set`-usage-error test.
  - `[medium]` `[patch]` Blind Hunter: `test_harness_policy_render.py`'s module docstring claimed
    "all 7 Marshal-mapped scalar knobs... `review_min_score` as the 7th," but 5 (Story 25.4) + 1
    (this story) = 6, not 7 — a real arithmetic error, disagreeing with the correct "six knobs"
    count in `harness_bmadloop.py`'s own docstring two files away in the same diff. Fixed:
    corrected to "6"/"6th."
  - `[medium]` `[patch]` Blind Hunter: both the new `bmad-review.toml` header and
    `test_rendered_defaults_pass_the_installed_bmad_loop_load`'s docstring asserted
    `review_min_score`/`review.min_score` is "never a harness(-policy) key" — read literally this
    contradicts the same diff adding it to Marshal's own closed policy vocabulary and rendering it
    into the harness's real `[review].min_score` TOML key. Verified the intended meaning was
    "never read/consumed by the harness," not "never a rendered key" — fixed both to say so
    unambiguously.
  - `[low]` `[patch]` Edge Case Hunter (+ Blind Hunter, overlapping observations): the lens
    instruction had no stated behavior for a killed/timeout/unexpected `tea-test-review` exit
    code, no fallback for an unreadable/malformed JSON verdict file on an otherwise-successful
    exit, no guidance to clean up its own temp `--json` file, and would pass a malformed
    ancestor-`policy.toml` `min_score` value straight through to `--min-score` unvalidated.
    Verified each is a real, plausible gap in the instruction's own stated discipline (which is
    otherwise explicit about the 2/3-exit-code path). Fixed: instruction hardened to treat all of
    these as environment failures (never fabricate), added a 30-minute wall-clock budget matching
    the tool's own `--timeout-ms` default, added temp-file cleanup, and added an integer-parse
    check before trusting an ancestor `min_score` value.
  - `[low]` `[patch]` Blind Hunter: backtick-style inconsistency in two `core/policy.py`
    docstrings (mixing single- and double-backtick RST markup within one paragraph, against the
    file's otherwise-consistent double-backtick convention) — verified real, cosmetic; fixed both.
  - `[low]` `[patch]` Blind Hunter: three new `review_min_score` rejection tests asserted
    `findings[0].code == "MRS-POLICY-003"` but only the first also asserted `findings[0].path ==
    "project"`, an unexplained depth gap between three otherwise-parallel test cases — verified
    real; added the missing assertion to the other two.
  - `[low]` `[patch]` Blind Hunter: the pre-existing, open `DW-3-13-1` deferred-work-ledger entry
    (a stale "9 keys" comment in `cli/config.py` that this story's own key-count bump widens
    further, 27→28) was left un-re-verified by this story's own diff — verified the entry's own
    established precedent is to add a fresh `verified:` line at each adjacent touch, not to fix
    the stale literal (out of every contributing story's own bounded scope); added the line.
  - `[low]` `[reject]` Blind Hunter: flagged that this diff (entirely outside `recipes/`) needs
    the `maintenance` PR label per this repo's always-on rule — correct as a fact, but this
    story's own dispatch instructions explicitly forbid opening a PR (the orchestrating session
    does that); noted in this story's own final report to that session instead of being
    "fixed" here, since there is no PR yet for this story to label.
  - `[maybe-false]` `[defer]` Verification Gap: new `review_min_score` rejection tests only cover
    the `project` layer, not `repo_defaults`/`flags` — checked against every sibling
    bmad-loop-adjacent knob's own test depth (`stream_capture_kb`'s rejection tests are
    project-layer only too) and found this matches the established, accepted convention exactly,
    not a gap unique to this story. If that convention itself is ever judged insufficient, it
    would need to be fixed for all 6 knobs at once, not just this one — recorded as `deferred`
    (if-true grade: low, since the same "insufficient" judgment would already apply to 5
    already-shipped knobs without incident).
  - `[low]` `[defer]` Design-level (self-identified, not from a reviewer): the lens's real
    end-to-end behavior is not exercised by an automated test — matches every other shipped
    `bmad-review` lens's own test coverage (none of them have one either); not a gap unique to
    this addition.

## Design Notes

**Why the lens's real end-to-end behavior (running `tea-test-review`, parsing its verdict,
emitting findings) is not exercised by an automated test:** the lens's `instruction` is a prompt
for an LLM-driven review session to follow, not code — the same nature as every other shipped
`bmad-review` lens (`edge-case-hunter` et al.), none of which have an automated "run the lens and
check its output" test either; `bmad-review`'s own test surface (if any) is out of this story's
declared Surface. What IS verified mechanically: the lens merges correctly into the resolved lens
set (`resolve_customization.py`), the TOML parses, and the policy plumbing it depends on
(`review_min_score`) composes/renders/loads correctly end-to-end, including against the real
installed `bmad_loop` package.

**Why `review_min_score` is threaded through the rendered `.bmad-loop/policy.toml` rather than
some other config path:** the story's own Surface line names `core/policy.py` + `policy.json`
explicitly ("the value 46.3's task takes as its argument"), and every prior bmad-loop-adjacent
knob (Story 25.4's five) uses this exact same SEED-field -> render -> `[review]` table pattern.
Verified empirically (not assumed) that `bmad_loop` 0.11's own policy loader extracts only its
five known `[review]` keys and silently ignores an unrecognized sixth (`min_score`) — its
unknown-key rejection is a separate, opt-in mechanism (`[plugins.<name>]` tables only), not
triggered here. This makes `[review].min_score` a safe, harness-invisible carrier for a
marshal-owned value the lens's own instruction reads back out at review time.

**Why the 8 real loop homes were actually re-rendered, not just the render function tested:** the
story's own AC names "`bmad-loop validate` is 8/8 after re-render" as a real, checkable outcome,
and `marshal config --write-harness-policy` is documented as an idempotent, narrowly-scoped
command safe to run repeatedly against a live loop home (confirmed via its own `--help` text
before running it) — no git state, no run state, only `.bmad-loop/policy.toml` is touched.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected and confirmed: 7522 passed (12
  new/extended tests total across the review pass; 3 renamed for the new key count).
- `python3 -c "import tomllib; tomllib.load(open('_bmad/custom/bmad-review.toml','rb'))"` --
  expected and confirmed: parses, both before and after the post-review hardening edits.
- `uv run _bmad/scripts/resolve_customization.py --skill .claude/skills/bmad-review --project-root . --key workflow`
  -- expected and confirmed: 6 lenses resolved, `tea-test-review` present.
- `bmad-loop validate --project ~/.bmad-loops/pyforge-<slug> --json` for all 8 -- expected and
  confirmed: `policy: OK` present for every one; overall `ok: true` for 7/8, `ok: false` (1
  pre-existing, unrelated dirty-worktree problem) for `pyforge-marshal` itself — re-confirmed via
  fresh JSON output during the review pass, not just the initial text-mode run.
- `python3 -m pyforge.doctor.sources spec-surface` -- expected and confirmed: zero findings
  against any file this story touches, after reconciling all 5 tripped specs.

## Auto Run Result

Status: done

**Summary:** Added `review_min_score` end-to-end through marshal's policy pipeline (SEED key,
validator, merge composition, JSON schema, harness-policy render, `--set` usage-error rejection),
added the `tea-test-review` `bmad-review` lens via `_bmad/custom/bmad-review.toml`, re-rendered
all 8 real loop-home `policy.toml` files, and recorded the calibration plan (first ten PRs) in
`spec-bmad-611-era-alignment`'s `.memlog.md`. A 4-reviewer pass (Blind Hunter, Edge Case Hunter,
Verification Gap, Intent Alignment) found and this pass fixed: a real `--set` rejection gap
(independently caught by two reviewers) that would have silently discarded an operator's override
behind a misleading finding instead of a clean usage error; an arithmetic error (7 vs. the correct
6 knobs); a self-contradictory "never a harness key" phrase; four real robustness gaps in the
lens's own instruction text (exit-code handling, JSON-parse failure, temp-file cleanup, malformed
ancestor config); a backtick-style inconsistency; an inconsistent test-assertion depth; and a
stale, pre-existing deferred-work-ledger entry left un-re-verified. `pyforge-marshal-test` passed
7522. `bmad_loop` 0.11's own policy loader confirmed empirically (not assumed) to accept the extra
`[review].min_score` key harmlessly. All 8 real loop homes' `policy: OK` line re-confirmed via
fresh JSON output during the review pass itself, not just the pre-review run.

**Files changed:** see Code Map above.

**Review findings breakdown** (12 findings from 4 independent context-free reviewers):
- Patched (3 medium, 6 low): the `--set` rejection gap (Verification Gap + Edge Case Hunter, same
  fix); the 7-vs-6 arithmetic error; the "never a harness key" ambiguity; the 4 lens-instruction
  robustness gaps (grouped, one fix); the backtick inconsistency; the test-assertion depth gap;
  the stale deferred-work-ledger entry (a fresh `verified:` line, not a fix to the stale literal
  itself, matching that entry's own established precedent).
- Rejected (1, low): the `maintenance`-PR-label observation — correct as a fact, but this
  dispatch's own instructions forbid opening a PR; flagged in the final report to the
  orchestrating session instead.
- Deferred (2, low/maybe-false): the project-layer-only test depth for the new validator (matches
  every sibling knob's own accepted convention, not a new gap); the lens's real end-to-end
  behavior being untested by automation (matches every other shipped lens).

**Follow-up review recommendation: false.** No patched entry was `high`; the 3 `medium` entries
were each independently verified (live code tracing for the `--set` gap, direct arithmetic
re-check for the knob count, re-reading both flagged phrases for the ambiguity) rather than left
as an unverified risk-sharing group. No specific unverified risk can be named.

**Verification performed:** see Verification above; additionally, `len(_UNSETTABLE_KEYS) == 28`
directly checked (not assumed) before writing the deferred-work-ledger update.

**Residual risks:** none rated medium or higher. The two `deferred` items are pre-existing
convention matches or design choices shared with already-shipped sibling work, not gaps unique to
this story. **Report to the orchestrating session:** this diff touches no file under `recipes/`,
so per this repo's always-on PR-gate rule, whichever PR eventually carries this branch's changes
needs the `maintenance` label added at open/update time.
