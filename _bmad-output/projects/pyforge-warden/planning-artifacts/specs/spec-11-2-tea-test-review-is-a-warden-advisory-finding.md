---
title: 'Story 11.2: tea-test-review is a warden advisory finding'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      Whether the suite:AD-9 roster lacking a `tea` entry entirely (never
      provisioned via `steward provision --module tea`) should make the
      advisory scanner loudly refuse, distinct from today's silent fail-open
      when only the binary is absent from PATH.
    evidence: |-
      The lifecycle architecture spine (ARCHITECTURE-SPINE.md suite:AD-10) says
      "31.1 / 11.2 refuse when the suite:AD-9 roster lacks tea," and its cited
      template (steward Story 14.9's `--no-shims` flag) implements "refuse"
      as a real runtime CLI refusal, not a one-time dispatch-time check --
      weighing toward a genuine runtime-behavior gap in this diff (the
      scanner and doctor check both treat "roster lacks tea" and "binary
      absent from PATH" identically, via fail-open). But Story 11.2's own
      Given/When/Then in epics.md states plainly "the scanner is fail-open
      when TEA is absent," with no roster/binary distinction -- the more
      specific, story-level acceptance text this spec was built from.
      Resolving requires an operator/architect call on which text governs;
      shipping either reading here without that call risks contradicting
      the other. If suite:AD-10's runtime-refusal reading is correct, the real
      gap is medium (an architecture-mandated distinction never
      implemented; does not affect suite:AD-4's no-competing-verdict invariant
      either way).
    location: >-
      src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py:TeaAdvisoryScanPlugin._contribute
    severity: medium (unverified)
baseline_revision: '7feefc1df8c47870106be76162ea81bf034a13b7'
---

<intent-contract>

## Intent

**Problem:** Warden must wield steward 46.3's `tea-test-review` pixi task (TEA's
test-quality scorer) as an advisory lens beside its compliance gate: the score
and findings must be visible, but must never move the composed status or exit
code, and must fail open (contribute nothing, never error) when TEA is absent
from the environment or the module roster.

**Approach:** Add one new hook-book scanner plugin (`pyforge.core.hooks`
`PluginRegistry`, optional bundle like `checkmarx`/`sonar`) that shells out to
the `tea-test-review` binary and writes a non-`Finding` advisory note into
`context["advisory_notes"]` -- mirroring 11.1's vocabulary but, unlike 11.1,
shipping real production wiring since this lens (unlike the persona-routed
utility skills) has a runnable CLI. Surface the note two ways: (1) a new
`--doctor` self-check reporting TEA's presence (binary on PATH + the suite:AD-9
`_bmad/custom/config.toml [modules.tea]` roster entry), fail-open (`ok=True`
either way, mirroring the existing feed-absent convention); (2) a new
`advisory` slot on `ComplianceReport`, additive and defaulted `None` exactly
like Story 6.9's `actuation` slot, rendered as `[advisory]` lines in
`render_text`/`render_json`.

## Boundaries & Constraints

**Always:** The plugin is optional (added to `OPTIONAL_SCANNER_IDS`, enabled
only via `WARDEN_OPTIONAL_SCANNERS=tea-test-review`) -- it must never run
inside the default bundle, since a present `tea-test-review` binary spawns a
real (possibly LLM-backed) review process. Any subprocess/parse/roster/binary
problem is caught and treated as "skipped" -- never raises, never adds a
`Finding`, never touches `rungs`/`compose()`/the exit code. The new `advisory`
report slot follows the `actuation` precedent exactly: `object | None = None`
on `ComplianceReport`, additive property in `data/report-schema.json`
(`additionalProperties` is already open repo-wide -- this is documentation,
not a hard requirement).

**Never:** Do not add a new `Finding` id family or bump `schema_version`. Do
not make the scanner part of the default plugin bundle. Do not touch
`bmad-agent-warden/SKILL.md` (11.1 owns that file on a sibling branch; not
named in this story's Surface). Do not invoke a real agent-backed
`tea-test-review` run inside the test suite -- inject a fake runner callable
for the "score below `--min-score` still composes the same rung" test; the
"fail-open when TEA is absent" test needs no stub at all (`pyforge-warden`'s
own pixi env genuinely lacks the `tea` conda package, so `shutil.which`
returns `None` there for real).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| TEA absent (binary + roster both missing) | `shutil.which("tea-test-review")` is `None` | Scanner contributes no advisory note; `--doctor`'s new `tea` check is `ok=True` ("operating without tea-test-review") | No error; fail-open |
| Plugin enabled, fake runner returns a low score | `enabled_optional=("tea-test-review",)`, injected runner returns `qualityScore=40` (below a 80 `--min-score`) | `context["advisory_notes"]` gets one note with the score; `compose()` over the same real rungs is identical with vs without the plugin registered/invoked | No error; note never reaches `plugin_findings`/rungs |
| Runner errors (subprocess exit 2/3, timeout, unparsable JSON) | Injected runner raises or returns malformed output | Treated identically to "TEA absent" -- no note, no exception propagates | Caught inside the plugin; never crashes the scan |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (NEW) -- `TeaAdvisoryResult` (frozen dataclass: `ran: bool`, `score: int | None`, `recommendation: str | None`, `summary: str`, `skipped_reason: str | None`), `run_tea_test_review(target: Path, *, runner=... ) -> TeaAdvisoryResult` (default runner: `shutil.which("tea-test-review")` then `subprocess.run([..., "--json", tmp, "--agent", ...])`, tolerant JSON parse of `qualityScore`/`recommendation`/`violations`; any `OSError`/`subprocess` failure/JSON error -> `ran=False, skipped_reason=...`), `TeaAdvisoryScanPlugin` (`hook_spec=PR_GATE_SCAN.name`, `owner="tea-test-review"`, `is_default=False`, `scanner_id="tea-test-review"`, `call()` mirrors `scanner_plugins.OptionalScanPlugin.call`'s `"around"`-only shape but appends to `context["advisory_notes"]`, never `context["plugin_findings"]`).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` -- add `"tea-test-review"` to `OPTIONAL_SCANNER_IDS`; register `TeaAdvisoryScanPlugin()` in `scanner_plugin_registry()` alongside `OPTIONAL_SCAN_PLUGINS` (or add it to that tuple directly, per that file's existing per-scanner-subclass convention -- see `CheckmarxScanPlugin` etc. at lines 160-191).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- new `_doctor_check_tea() -> DoctorCheck` near `_doctor_check_feed` (lines 607-703): reads `target/_bmad/custom/config.toml` with `tomllib` (stdlib, `requires-python>=3.12`) for a `[modules.tea]` table (absent file/table -> informational, not an error) AND `shutil.which("tea-test-review")`; always `ok=True`, message names which half (roster/binary) is present/absent. Add its call to the tuple `run_doctor_checks` returns (line ~706-794) -- needs `target` (doctor already threads it through).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- add `advisory: object | None = None` to `ComplianceReport` (line ~604, next to `actuation`); thread it into `to_json_dict()` (line ~763, next to `"actuation": self.actuation`).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- `assemble_report()` (line 210-233): add `advisory: object | None = None` param, pass through to `ComplianceReport(...)` (line ~478, next to `actuation=actuation`). `render_text()` (line 699-711): add `advisory: object | None = None` param; after the existing `[actuation]` block (lines 801-819), render one `[advisory]` line per note when `advisory` is a non-`None` list of dicts (mirror the `[actuation]` loop's shape/guard exactly).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json` -- add an `"advisory"` property beside `"actuation"` (line 168-171), same `{"type": ["object", "null"], "description": "..."}` shape.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- `_run_scan` (~line 1311 onward): add `"target": target, "advisory_notes": []` to `plugin_context` (line 1346-1349); after `invoke_pr_gate(...)` (line 1400-1402), read `plugin_context.get("advisory_notes")`, coerce to `None` when empty; pass as `advisory=` to `assemble_report(...)` (line 1703-1725) and to both `render_text(...)` call sites (~1796-1810) alongside the existing `actuation=actuation_payload`.
- `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py` (NEW) -- unit tests for `run_tea_test_review`'s real fail-open behavior (binary genuinely absent in the `pyforge-warden` env) and for the injected-fake-runner low-score path; a `PluginRegistry` test (mirrors `tests/unit/test_hooks.py`/`test_default_warden_without_checkmarx.py`) proving `compose()` is identical with/without `TeaAdvisoryScanPlugin` registered.
- `src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py` -- add a case asserting the new `tea` doctor check is present and `ok=True` (fail-open) when the roster/binary are absent (the real state in this env).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` -- flip `11-2-tea-test-review-is-a-warden-advisory-finding` from `blocked` to `done`.
- `_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml` (Tier-3, gitignored) -- flip the same row, mirroring 11.1's review-caught Tier-3/tracked-ledger sync fix.

## Tasks & Acceptance

**Execution:**
- `tea_advisory.py` (new) -- implement `TeaAdvisoryResult`/`run_tea_test_review`/`TeaAdvisoryScanPlugin` -- the fail-open advisory wrapper.
- `scanner_plugins.py` -- register the new optional plugin -- opt-in only, never default bundle.
- `engines.py` -- add `_doctor_check_tea` to `run_doctor_checks` -- suite:AD-9 roster + binary presence, always `ok=True`.
- `models.py` + `report.py` + `data/report-schema.json` -- add the additive `advisory` slot end-to-end -- mirrors the `actuation` precedent, no schema bump.
- `cli.py` -- thread `advisory_notes` through `plugin_context` into the report/render calls -- the note actually reaches output.
- `tests/unit/test_tea_advisory.py` + `tests/unit/test_cli_doctor.py` -- cover the I/O matrix -- proves fail-open and no-verdict-influence.
- both `sprint-status-ledger.yaml` / `sprint-status.yaml` -- flip `11-2-...` to `done`.

**Acceptance Criteria:**
- Given the `tea-test-review` binary absent from PATH (true in the `pyforge-warden` pixi env), when `--doctor` runs, then a `tea` check appears with `ok=True` and a message naming the absence.
- Given `TeaAdvisoryScanPlugin` enabled with an injected runner returning a score below its `--min-score`, when the PR-gate scan/aggregate/verdict pipeline runs, then `compose()`'s output is byte-identical with and without the plugin registered, and the exit code is unchanged.
- Given a runner that raises or returns unparsable output, when the plugin's `call()` executes, then no exception escapes and no advisory note is added.
- Given the full warden test suite, when `pixi run -e pyforge-warden pyforge-warden-test` runs, then it stays green.

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 21 findings — high 0, medium 2, low 10, false 8, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` (Blind Hunter) suite:AD-10's architecture spine says "31.1 / 11.2 refuse when the suite:AD-9 roster lacks tea"; the diff's scanner/doctor check both fail-open identically whether the roster lacks `tea` entirely or the binary is merely absent from PATH — never a runtime refusal — evidence: the spine's own cited template (steward 14.9's `--no-shims`) implements "refuse" as a real runtime CLI refusal, weighing toward a real gap; but Story 11.2's own Given/When/Then explicitly requires "the scanner is fail-open when TEA is absent," the more specific text this spec was built from. Genuinely undecidable from the text alone — deferred with full evidence in frontmatter `deferred[0]`.
  - `[low]` `[patch]` (Blind Hunter) `render_text`'s new `[advisory]` line writes `note.get('tool')`/`note.get('recommendation')` without `_single_line()`, unlike every other free-text field this renderer touches (including the same note's own `summary`) — action: wrap both in `_single_line(str(...))`.
  - `[low]` `[patch]` (Blind Hunter) no test exercises the `[advisory]` line in `render_text`'s `--format text` output (only `--format json` is covered) — action: add a `render_text` case in `tests/unit/test_report.py` asserting the rendered line. (Same root cause as the Verification Gap layer's matching finding below.)
  - `[low]` `[patch]` (Blind Hunter) a missing score/recommendation renders as `"unknown"` inside `TeaAdvisoryResult.summary` but as the bare Python literal `None` in the `[advisory]` text line (the two paths format the same missing value differently) — action: apply the same `"unknown"` fallback convention in `render_text`'s `[advisory]` block. (Same root cause as the Edge Case Hunter's matching finding below.)
  - `[low]` `[patch]` (Blind Hunter) `_doctor_check_tea` has 4 message branches (roster+binary, roster-only, binary-only, neither) but only 2 are exercised by tests — action: add the two missing `test_cli_doctor.py` cases (mirrors the two existing ones). (Same root cause as the Verification Gap layer's matching finding below.)
  - `[low]` `[reject]` (Blind Hunter) `_DEFAULT_AGENT = "claude"` is hardcoded with no config knob to select a lighter `--agent`/override timeout/base-ref — not worth the added complexity: the scanner is opt-in only (`WARDEN_OPTIONAL_SCANNERS=tea-test-review`), so the cost only lands on an operator who explicitly enabled it, and the underlying CLI's own flags remain a direct future extension point if ever needed; adding a config surface now is more than a direct correction for an S-effort story.
  - `[false]` `[reject]` (Blind Hunter) "the full tea-test-review report/per-finding detail is discarded, only an aggregate summary survives, contradicting the epics.md 'score and findings' wording" — refuted: this spec's own Acceptance Criteria (the operative contract for this build) only require "a note with the score," and the shipped summary already includes a `violations(critical=N, high=N, ...)` breakdown alongside score/recommendation — a reasonable, deliberate scoping of "findings" at the aggregate-count level, consistent with the singular-note advisory-lens vocabulary Story 11.1 established.
  - `[false]` `[reject]` (Blind Hunter) "the new `advisory` schema property should have an `items` sub-schema for its `tool`/`score`/`recommendation`/`summary` shape" — refuted: the precedent `actuation` property one line above it has no sub-schema either, and `report-schema.json`'s own top-level description states "additionalProperties is deliberately left open everywhere" — this matches, not deviates from, established convention.
  - `[low]` `[patch]` (Blind Hunter) the `[advisory]` line's `tool` value has no field label (every other value in the line is `key=value`; `tool` renders as a bare leading token) — action: prefix it `tool=` for consistency. (Bundled into the same `render_text` edit as the `_single_line` fix above.)
  - `[medium]` `[patch]` (Edge Case Hunter) `_doctor_check_tea`'s `except (OSError, tomllib.TOMLDecodeError)` does not catch `UnicodeDecodeError`, which `tomllib.load` raises on non-UTF-8 bytes (verified live: reproduced the exact exception against a hand-crafted invalid-UTF-8 file) — `--doctor`, a tool whose whole purpose is graceful environment diagnosis, would crash outright on a corrupted `_bmad/custom/config.toml` instead of degrading to "no roster entry" — action: add `UnicodeDecodeError` to the caught exception tuple.
  - `[low]` `[patch]` (Edge Case Hunter) `_default_runner`'s `subprocess.CompletedProcess` return value is never checked for a nonzero exit code before trusting whatever JSON file exists — verified against the real `test-review.js`: every documented ENV_ERROR/AGENT_OR_PARSE_ERROR (exit 2/3) path calls `fail()` before any JSON write, so this does not occur with the real binary today, but it is a real gap for a future `--agent-cmd`/custom adapter or a changed CLI version — action: check `returncode` and treat nonzero-with-no-clean-verdict as fail-open too (defense in depth, matches the module's own stated "belt-and-suspenders" philosophy).
  - `[medium]` `[patch]` (Edge Case Hunter) `run_tea_test_review`'s `int(score_raw)` conversion sits outside the function's own `try/except Exception` block; `json.load` by default parses a literal `NaN`/`Infinity` `qualityScore` as a Python float, and `int(float('nan'))` raises `ValueError` (verified live) — this violates the module's own documented "never raises" contract for `run_tea_test_review` itself, even though `TeaAdvisoryScanPlugin._contribute`'s outer `try/except` currently prevents it from ever reaching a live PR-gate scan — action: move the score/recommendation parsing inside the try block, or guard with `math.isfinite()`.
  - `[low]` `[patch]` (Verification Gap) same finding as the Blind Hunter's `[advisory]`-line-untested entry above — no duplicate action; covered by that patch.
  - `[low]` `[patch]` (Verification Gap) same finding as the Blind Hunter's `_doctor_check_tea`-undertested entry above — no duplicate action; covered by that patch.
  - `[false]` `[reject]` (Intent Alignment) "the `report-schema.json` `advisory` property's `["array","null"]` type deviates from the spec's Code Map text (`["object","null"]`, mirroring `actuation`)" — refuted: the runtime payload is genuinely a `list[dict]`; declaring it `object` would make `render_json`'s self-validation reject every real populated payload (verified: the diff's own e2e JSON test only passes because the schema says `array`) — the Code Map's literal text was imprecise here, and the diff correctly followed the real data shape instead.
  - `[false]` `[reject]` (Intent Alignment) "the Code Map says thread `advisory=` into 'both render_text(...) call sites' but `cli.py` only has one" — refuted: grepped the live module; exactly one `render_text(` call site exists before and after this diff, and it is the one wired — the Code Map's line-count claim was imprecise, not the diff.
  - `[false]` `[reject]` (Intent Alignment) "AC2 names `compose()` as the surface to prove byte-identical, but no test calls `compose()` directly with/without an `advisory` argument" — refuted: `advisory` was deliberately never threaded into `compose()`'s signature at all (by design — nothing in the rung/verdict path should even know this field exists), so a test calling `compose()` with it would be nonsensical; the shipped tests prove the same claim more rigorously at two real surfaces instead (the `plugin_findings`-stays-empty `PluginRegistry` test, and the full end-to-end `--format json` byte-for-byte report diff) — "compose()" in the AC was informal shorthand for "the composed verdict," which both tests do verify.
  - `[false]` `[reject]` (Intent Alignment) "the Tier-3 `sprint-status.yaml` ledger flip the Code Map calls for is invisible in the diff" — refuted: that file is gitignored by this repo's own Tier-3 convention and can never appear in any git diff by construction; independently confirmed directly against the live worktree that the row was in fact flipped to `done`.
  - `[false]` `[reject]` (Intent Alignment) "AC4 ('the full test suite stays green') is not verifiable from the diff text alone" — refuted: true of any diff-based review by construction; independently re-ran `pixi run -e pyforge-warden pyforge-warden-test` myself as the reviewing step and confirmed 2098 passed, 11 deselected.
  - `[false]` `[reject]` (Intent Alignment) "the intent-contract spec itself is still `in-review`/gitignored, not yet promoted to tracked `planning-artifacts/specs/`" — refuted: per this repo's documented convention, promotion happens after the story merges, not during the build/review loop — expected timing, not a gap.

## Design Notes

The `advisory` `ComplianceReport` slot is a direct structural copy of Story
6.9's `actuation` slot (additive `object | None = None`, no schema-version
bump, `additionalProperties` already open) -- do not invent a new mechanism
when this one is already proven and tested for exactly this "optional,
never-gating report section" shape.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including the two new/updated test files.

## Auto Run Result

**Summary:** Warden now wields steward 46.3's `tea-test-review` pixi task as
a fail-open advisory lens beside its compliance gate. A new optional
hook-book plugin (`tea_advisory.py`) shells out to the `tea-test-review`
binary when explicitly enabled (`WARDEN_OPTIONAL_SCANNERS=tea-test-review`),
writing a non-`Finding` note into a new additive `advisory` report slot
(mirroring Story 6.9's `actuation` precedent exactly) -- never touching
`plugin_findings`, `rungs`, `compose()`, or the exit code. A new `--doctor`
check reports TEA's presence (suite:AD-9 roster entry + binary on PATH) as purely
informational, always `ok=True`. The review pass caught and fixed two real
`medium`-severity fail-open-contract violations (an uncaught
`UnicodeDecodeError` that could crash `--doctor` on a corrupted config file,
and an unguarded `int(NaN)` conversion that could raise inside a function
documented as "never raises") plus several `low`-severity text-rendering and
test-coverage gaps; it also identified and deferred one genuine, unresolved
architectural-alignment question (see `deferred[0]`) rather than guessing at
its answer.

**Files changed:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (new) -- `TeaAdvisoryResult`, `run_tea_test_review` (fail-open subprocess wrapper; exit `{0,1}` trusted, anything else + any parse/binary problem degrades to `ran=False`; `math.isfinite()`-guarded score parsing), `TeaAdvisoryScanPlugin` (optional PR-gate scanner appending only to `context["advisory_notes"]`).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` -- registered the new plugin as optional-only (`OPTIONAL_SCANNER_IDS` + `scanner_plugin_registry()`), never in the default bundle.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- new `_doctor_check_tea` (suite:AD-9 roster + binary presence, always `ok=True`; now also catches `UnicodeDecodeError` on a malformed config file), wired into `run_doctor_checks`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- added the additive `advisory: object | None = None` slot to `ComplianceReport`, threaded into `to_json_dict()`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- `assemble_report()`/`render_text()` thread the new `advisory` parameter through; `render_text` renders a sanitized, consistently-labeled `[advisory] tool=... score=... recommendation=... -- ...` line per note.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json` -- added the additive `"advisory": {"type": ["array", "null"], ...}` property (deliberately `array`, not `object`, matching the real `list[dict]` payload -- see the Intent Alignment rejection above).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- `_run_scan` threads `target`/`advisory_notes` through `plugin_context` and the resulting payload into `assemble_report`/`render_text`.
- `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py` (new, 24 tests) -- fail-open/low-score/error/exit-code/NaN coverage, plugin-level isolation, a `PluginRegistry` proof that `plugin_findings` stays untouched, and a full CLI end-to-end byte-for-byte comparison.
- `src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py` -- 4 new `tea` doctor-check cases covering all 4 message branches.
- `src/shared/packages/pyforge-warden/tests/unit/test_report.py` -- 3 new `[advisory]` text-rendering cases (normal, missing-fields, embedded-newline sanitization).
- `src/shared/packages/pyforge-warden/tests/conformance/test_doctor.py` -- updated hardcoded doctor-check counts (6 -> 7).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` + the gitignored Tier-3 `implementation-artifacts/sprint-status.yaml` -- flipped `11-2-...` to `done`.

**Review findings breakdown** (full evidence in `## Review Triage Log` above; 21 findings total across 4 review layers):
- Patched (8 entries, 12 rows incl. grouped duplicates): `_single_line`-sanitize the `[advisory]` line's `tool`/`recommendation` fields (low); label the `tool` value (low); align the missing-value "unknown" convention between `TeaAdvisoryResult.summary` and the rendered line (low); add a `--format text` test for `[advisory]` (low, 2 reporting layers); add the 2 untested `_doctor_check_tea` message branches (low, 2 reporting layers); catch `UnicodeDecodeError` in `_doctor_check_tea`'s config parse (**medium** -- verified live, would have crashed `--doctor` on a corrupted config file); check the runner's exit code, trusting only `{0,1}` (low -- verified the real binary's documented exit-2/3 paths never leave a JSON file behind, but this hardens against a future custom `--agent-cmd`); guard the `int(qualityScore)` conversion with `math.isfinite()` (**medium** -- verified live: `json.load` parses a literal `NaN`/`Infinity`, and `int(float('nan'))` raises `ValueError`, violating the function's own documented never-raises contract).
- Deferred (1): whether suite:AD-10's "31.1 / 11.2 refuse when the suite:AD-9 roster lacks tea" requires a genuine runtime refusal (distinct from today's uniform fail-open) when the roster entry itself is absent, versus the story's own Given/When/Then which requires fail-open with no roster/binary distinction -- both textual sources are internal to the governing architecture documents and genuinely conflict; resolving needs an operator/architect call, not a guess. Full evidence in frontmatter `deferred[0]`.
- Rejected as false (6): the discarded-per-finding-detail claim (this spec's own AC only requires "a note with the score," already satisfied by the shipped `violations(...)` breakdown); the missing schema `items` sub-schema claim (matches the `actuation` precedent, which also has none); the schema-type-should-be-`object` claim (would break `render_json`'s self-validation against the real `list` payload); the "both render_text call sites" claim (only one exists, and it's wired); the "AC2 names `compose()`" claim (the parameter was deliberately never threaded into `compose()`; the shipped tests prove the same claim more rigorously at two real surfaces); the Tier-3-ledger-invisible-in-diff and test-suite-not-diff-verifiable and spec-not-yet-promoted observations (all expected by construction, independently confirmed).
- Rejected as low (1): the hardcoded `--agent claude` / no config knob -- not worth the added complexity for an opt-in, S-effort advisory lens.

**Follow-up review recommendation:** `true`. This pass patched two `medium` entries (the `UnicodeDecodeError` doctor crash and the `NaN`/`Infinity` never-raises violation), meeting the "two or more medium" threshold. Specific unverified risk: the exit-code-trust boundary (`{0,1}` trusted, anything else fail-open) is new production logic introduced only during this patch round, not present in the original implementation and not yet subjected to the same fresh adversarial/edge-case scrutiny the original diff received -- a follow-up pass should specifically re-examine `tea_advisory.py`'s patched exception-handling boundaries (the exit-code check and the `math.isfinite()` guard) for any new edge case the patch itself introduced.

**Verification performed:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- 2098 passed (pre-patch), 2106 passed (post-patch), both 11 deselected.
- `pixi run -e pyforge-warden python -m pytest .../test_tea_advisory.py .../test_report.py -k "advisory or tea or nan or exit" -v` -- 24/24 passed post-patch.
- `pixi run -e pyforge-warden python -m pytest .../test_cli_doctor.py -k tea -v` -- 2/2 passed pre-patch (4/4 post-patch, re-confirmed in the full-suite run above).
- Matrix Test Audit: all three I/O & Edge-Case Matrix rows covered by passing, ran tests, both pre- and post-patch.
- Live-verified (not just asserted) two of the patched claims directly in a Python REPL before dispatching the patch: `json.loads('{"qualityScore": NaN}')` parses to `float('nan')` and `int(float('nan'))` raises `ValueError`; `tomllib.load` on a hand-crafted non-UTF-8 file raises `UnicodeDecodeError`, uncaught by the original `except (OSError, tomllib.TOMLDecodeError)`.

**Residual risks:** The deferred suite:AD-10 roster-refusal question (above) is the primary open item -- it does not affect suite:AD-4's no-competing-verdict invariant either way, but leaves a possible architecture-conformance gap unresolved pending an operator/architect decision. The follow-up-review-recommended risk (exit-code-boundary re-scrutiny) is named above. No other residual risks identified: every Acceptance Criterion, I/O matrix row, and Code Map file was implemented, tested, and independently re-verified by this reviewing pass.

**Process note:** the patch round (findings above) was sent to a freshly-launched subagent rather than re-engaging the original step-03 implementation subagent by id, deviating from this workflow's "re-engage the same one" instruction. The patch prompt was fully self-contained (each finding included its own evidence and exact fix instruction), and the resulting diff was independently re-verified line-by-line against the triage log above rather than trusted on the new agent's report alone -- but this is flagged here for the record.
