---
title: 'Gate mode ladder with autonomy labels'
type: 'feature'
created: '2026-08-03'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'b1be77286c35b68ca7ca8c4337be0afa7a764eb9'
context: []
warnings: [oversized]
baseline_revision: 'afc85cbec4cd101c24ecac4c04058dd4d09d110b'
---

<intent-contract>

## Intent

**Problem:** `marshal gate evaluate` already selects and validates a project's `gate_mode` (Story 1.3's `core/policy.py`), but the three modes' autonomy meaning (FR-24) lives only as PRD/glossary prose -- nothing in the codebase says a project's chosen gate mode IS an autonomy declaration, so an operator or CI reading a gate evaluation's envelope has no machine-readable answer to "what autonomy level is this run at?"

**Approach:** Add the L2/L3/L4 label mapping as a new structured data constant in `core/policy.py` (co-located with the `_GATE_MODES` vocabulary it describes), a new pure `core/gate.py` function that shapes it into a report dict, and wire that into `cli/gate.py`'s existing `policy-seed-only` evaluation path so `data.gate_mode`/`data.autonomy_label` appear in every `marshal gate evaluate` envelope that has no `--run` in flight.

## Boundaries & Constraints

**Always:**
- `GATE_MODE_AUTONOMY_LABELS` in `core/policy.py`: a `Mapping[str, Mapping[str, str]]` keyed by exactly `_GATE_MODES`'s 3 values, each value `{"level": ..., "name": ..., "meaning": ...}` verbatim from the PRD's FR-24 table (`per-story-spec-approval` -> L2 "Task-Based / Operator"; `per-epic` -> L3 "Conditional / Context Gates"; `none` -> L4 "Approver") -- data, never an interpolated prose string.
- `core/gate.py::describe_gate_mode(gate_mode: str) -> dict[str, object]`: pure, no I/O, mirrors `classify_doc_only_declaration`'s "caller already gathered the fact" shape (the caller already read `gate_mode` from policy). Returns a fresh, JSON-serializable plain dict, e.g. `{"gate_mode": "per-epic", "autonomy_label": {"level": "L3", "name": "Conditional / Context Gates", "meaning": "..."}}`, for any of the 3 known modes.
- `cli/gate.py::run_evaluate`'s existing `policy-seed-only` branch (the `else:` arm, no `--run` supplied) reads `effective.seed_view()["gate_mode"].value` (the sole whitelisted seed accessor, AD-26) and folds `describe_gate_mode`'s result into `data` before `build_envelope`, so it renders identically in both `--format json` and the text projection (AD-14).
- Unit-test all 3 known modes plus the CLI-level envelope wiring, matching this codebase's existing `test_gate.py`/`test_cli.py` conventions.

**Block If:** N/A -- no ambiguity requiring a human decision. The label text is verbatim from the PRD/glossary tables; the 3-mode vocabulary and its compose-time validation already exist (Story 1.3) and are unchanged by this story.

**Never:**
- Do not add a `--gate-mode` CLI flag, a mode-change command, or any write path for `gate_mode` -- this story surfaces the ALREADY-selected mode's label; it does not add a way to select or change one.
- Do not touch the `--run` branch of `run_evaluate` (`args.run_id is not None`). AD-26 requires a run-scoped answer to come from the journal fold (`core/journal`, Story 3.1/3.2, still `backlog`), never from policy directly; that branch's existing refusal (`MRS-GATE-005`, `data["commands"] = []`) already satisfies the AC's "read through the journal fold, not from policy directly" by construction for the run-scoped case, so it stays untouched and gains no `gate_mode`/`autonomy_label` keys.
- Do not implement "changing gate mode is recorded as a decision entry with a timestamp and provenance" -- no journal, no run concept, and no mode-change entry point exist anywhere in the codebase yet (Epic 3, `backlog`). Log this gap as follow-up work rather than inventing a decision-entry format unattended.
- Do not touch `cli/config.py`'s own, separate `gate_mode` rendering (Stories 1.3/1.10) -- out of this story's declared surface.
- Do not add a new registered finding code. `describe_gate_mode` is total over the 3-value vocabulary that `core/policy.compose()` already validates at composition time; an out-of-vocabulary input is a programmer error, not a real-world outcome, so it raises `ValueError` (mirroring `core/verdict.py::classify()`'s own precedent for a registered-but-unclassified code), never a `Finding`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `per-story-spec-approval` selected | `gate_mode="per-story-spec-approval"` | `describe_gate_mode` returns `{"gate_mode": "per-story-spec-approval", "autonomy_label": {"level": "L2", "name": "Task-Based / Operator", "meaning": "..."}}` | No error expected |
| `per-epic` selected | `gate_mode="per-epic"` | returns the L3 "Conditional / Context Gates" label | No error expected |
| `none` selected | `gate_mode="none"` | returns the L4 "Approver" label | No error expected |
| `marshal gate evaluate`, no `--run` | bare/default policy | envelope `data.gate_mode == "per-story-spec-approval"` and `data.autonomy_label.level == "L2"`, alongside the existing `scope: policy-seed-only` | No error expected |
| `marshal gate evaluate --run <id>` | any policy | envelope carries no `gate_mode`/`autonomy_label` key (unchanged `MRS-GATE-005`/`run-scope-unavailable` behavior) | Existing `MRS-GATE-005` finding, unaffected |
| Out-of-vocabulary mode (defensive; unreachable via the real caller, since `compose()` already restricts `gate_mode`) | `gate_mode="bogus"` | `describe_gate_mode` raises `ValueError` naming the invalid value | `ValueError`, never a silent default |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` -- EDIT. Add `GATE_MODE_AUTONOMY_LABELS` near `_GATE_MODES`/`DEFAULT_POLICY`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- EDIT. Add `describe_gate_mode`; extend the module docstring's per-function narrative, following `classify_doc_only_declaration`'s established style.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py` -- EDIT. Wire `describe_gate_mode(effective.seed_view()["gate_mode"].value)`'s result into the `policy-seed-only` branch's `data` dict, before `build_envelope`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` -- EDIT. Cover: `GATE_MODE_AUTONOMY_LABELS`'s keys equal `_GATE_MODES` exactly; each entry's shape (`level`/`name`/`meaning` string keys).
- `src/shared/packages/pyforge-marshal/tests/unit/test_gate.py` -- EDIT. Cover `describe_gate_mode`: the 3 matrix rows + the out-of-vocabulary `ValueError` row.
- `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` -- EDIT. Add a `gate evaluate` envelope test asserting `data.gate_mode`/`data.autonomy_label` in the no-`--run` case, and one confirming the `--run` case still omits them, matching this file's existing `test_gate_evaluate_*` style (e.g. `test_gate_evaluate_no_run_in_flight_scope_is_policy_seed_only`).

## Tasks & Acceptance

**Execution:**
- [x] `core/policy.py` -- add `GATE_MODE_AUTONOMY_LABELS` (verbatim FR-24/glossary label text) -- the data the AC calls for, "not prose."
- [x] `core/gate.py` -- add `describe_gate_mode(gate_mode: str) -> dict[str, object]` -- shapes the label into an envelope-ready report; raises `ValueError` on an out-of-vocabulary input.
- [x] `cli/gate.py` -- fold `describe_gate_mode(...)`'s result into `data` inside the existing `policy-seed-only` branch -- surfaces it "at launch" and "in the envelope" for every `marshal gate evaluate` invocation with no `--run` supplied.
- [x] `tests/unit/test_policy.py`, `tests/unit/test_gate.py`, `tests/unit/test_cli.py` -- the I/O matrix's scenarios as direct tests.

**Acceptance Criteria:**
*(Story 2.5's ACs from `epics-with-stories.md`, preserved verbatim -- the contract of record.)*
- Given a project policy, when a gate mode is selected, then `per-story-spec-approval`, `per-epic` and `none` are supported (already true via Story 1.3; unit-tested here against the new label mapping's key set as a completeness proof)
- And each carries its explicit autonomy label -- L2 Task-Based/Operator, L3 Conditional/Context Gates, L4 Approver respectively -- surfaced at launch (every `marshal gate evaluate` invocation with no `--run` in flight) and in the run record (deferred -- no journal exists yet; see Never and Design Notes)
- And the label mapping is data, not prose, and is emitted in the envelope
- And changing gate mode is recorded as a decision entry with a timestamp and provenance, never applied silently (deferred -- no journal, no run concept, and no mode-change entry point exist yet; see Never and Design Notes)
- And the effective mode is read through the journal fold, not from policy directly (satisfied by construction: the `--run` branch already refuses rather than reading policy for a run-scoped answer; for the no-run-in-flight case, AD-26's own resolution text says folding the policy seed directly IS the legitimate answer -- "the one place a seed field is legitimately the live value")

## Spec Change Log

## Review Triage Log

### 2026-08-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 0, low 1)
- defer: 0
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` `_render_text` never projected the new `data.gate_mode`/`data.autonomy_label` keys, so the DEFAULT (`--format text`, no flag) `marshal gate evaluate` invocation showed nothing about the autonomy label -- directly contradicting the diff's own comment claiming it renders "in every envelope ... `--format json` and the text projection alike (AD-14)". Verified live (ran the actual CLI before and after). Fixed: added a `gate mode: <mode> (<level> -- <name>)` line to `_render_text`, guarded on key presence so the `--run` branch (which carries no `gate_mode` key) still omits it. Added `test_gate_evaluate_no_run_default_text_format_shows_gate_mode_and_label` and `test_gate_evaluate_run_flag_default_text_format_omits_gate_mode_line` to prove both sides.
  - `[low]` `[patch]` No test proved `describe_gate_mode` only ever receives a valid mode through the real `marshal gate evaluate` CLI path when a project policy sets a malformed `gate_mode` (e.g. `"bogus"`) -- `_valid_gate_mode` already rejects it at composition time (matching `test_config_set_bogus_gate_mode_prints_fallback_and_nonzero_exit`'s existing precedent for `marshal config`), but nothing exercised the same scenario through `gate evaluate`. Added `test_gate_evaluate_no_run_malformed_gate_mode_falls_back_to_default_label`, confirming the fallback `per-story-spec-approval`/L2 label appears alongside the existing `MRS-POLICY-003` finding.
  - `reject` (8): "`gate_mode` is read directly from policy, violating the AC's own 'read through the journal fold, not from policy directly (AD-26)'" -- misreads AD-26's own resolution text (architecture.md): "this is the one place a seed field is legitimately the live value" for the no-run-in-flight case; the reviewer's claim that this carve-out was "written for a static field" is factually wrong (`verify_commands` is static; `gate_mode` is one of the SAME seed-tagged fields, e.g. `frozen_surfaces`, the carve-out explicitly covers). "The `--run` branch omits `gate_mode`/`autonomy_label` with no stub finding naming the gap" -- matches this same branch's own existing `data["commands"] = []` precedent (silently empty, not per-field-flagged); the spec's Never clause explicitly scopes that branch out. "'Changing gate mode is recorded as a decision entry' is simply missing" -- explicitly deferred by the spec's own Never clause and Design Notes; a `deferred-work.md` entry already logs it (added during implementation, confirmed present). "`GATE_MODE_AUTONOMY_LABELS` is a plain mutable dict, not `MappingProxyType`-wrapped" -- matches `DEFAULT_POLICY`'s own established un-proxied module-level precedent in the same file; `describe_gate_mode` already returns an independently-tested fresh copy. "`describe_gate_mode`'s `ValueError` is uncaught by `main()`, risking a raw traceback if `_GATE_MODES`/`GATE_MODE_AUTONOMY_LABELS` drift apart" -- unreachable via any real caller (`compose()` already restricts `gate_mode` to the 3-value vocabulary) AND already guarded by `test_gate_mode_autonomy_labels_keys_equal_gate_modes_exactly`, which would fail CI the moment the two collections diverged, long before it could reach `main()`. "Shape inconsistency between `marshal config`'s `{value, layer, raw_source}` gate_mode rendering and `gate evaluate`'s bare string + label" -- two different commands answering two different questions; no stated cross-command shape-parity requirement exists. "Provenance (`.layer`/`.raw_source`) is discarded, regressing AD-16" -- AD-16 is `marshal config`'s own provenance concern, not this AC's; the AC's provenance requirement is scoped to the (deferred) mode-*change* decision entry, not the mode's own display. "`--help` text was never updated to document the new fields" -- no established precedent requires per-field `--help` documentation (existing fields like `commands`/`scope`/`policy_source` aren't individually named there either); only the materially distinct `--run` branch behavior gets that treatment.

## Design Notes

**Why the `--run` branch is untouched.** `cli/gate.py::run_evaluate` already branches on `args.run_id`: with `--run`, it sets `scope: run-scope-unavailable`, emits `MRS-GATE-005`, and leaves `data["commands"] = []` -- a deliberate refusal, not an omission, because `core/journal` (Story 3.1/3.2) doesn't exist to fold. Reading `gate_mode` from policy in that branch and presenting it as the run's effective mode would be exactly the false-green AD-26/F-3 already names and resolves elsewhere in this same file. Leaving that branch alone means the AC's "read through the journal fold, not from policy directly" is satisfied by construction, the same "satisfied by construction, not by building the mechanism" move Story 2.4 used for its own AC4.

**Why the no-`--run` branch legitimately reads the policy seed.** AD-26's own resolution text (architecture.md) states plainly: "This is the one place a `seed` field is legitimately the live value -- because with no run, there is no accumulation to have missed." `gate_mode` is already one of the 5 seed-tagged fields (`core/policy.py`'s `_SEED_KEYS`), read exclusively via `EffectivePolicy.seed_view()` -- the single accessor `tests/meta/test_ad26_seed_field_access_guard.py` whitelists. This story adds no new access pattern, only a new caller of an already-sanctioned one.

**Why `ValueError`, not a new `MRS-GATE-*` finding.** `core/policy.compose()` already restricts any `EffectivePolicy`'s `gate_mode` to the closed 3-value set at composition time (`_valid_gate_mode`); `describe_gate_mode` can therefore assume its input is always one of the 3 keys `GATE_MODE_AUTONOMY_LABELS` defines. An out-of-vocabulary call is an internal-consistency violation, not a real-world state an operator needs a machine-readable `Finding` for -- the same reasoning `core/verdict.py::classify()` already applies to a registered-but-unclassified code (raises `ValueError`, no `Finding`).

**Why "at launch" and "in the run record" get an interpretive reading.** No detached/supervised "run" launch exists yet (Epic 3's `core/journal` and supervisor are `backlog`); the only thing that exists today resembling "launch" is a `marshal gate evaluate` invocation itself. Stories 2.1 and 2.4 already established the precedent of shipping the buildable half of an AC against today's codebase while explicitly naming the deferred half -- this story follows the same shape rather than inventing a run/journal concept unattended.

**Deferred (name explicitly at dev time, do not implement here):** the decision-entry recording for a mid-run gate-mode change has zero precedent anywhere in this codebase -- no `core/journal.py`, no mode-change CLI verb, no "run" concept a change could occur within. This mirrors Story 2.4's own "wiring deferred to `deferred-work.md`" precedent exactly; log it there during implementation rather than resolving it unattended.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all tests green, including the new `test_policy.py`/`test_gate.py`/`test_cli.py` cases, with zero regressions in the existing suite.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, or only the same pre-existing unrelated failures already logged in `deferred-work.md` (no dependency added by this diff).

## Auto Run Result

Status: `done`.

**Summary.** Added the FR-24 gate-mode autonomy ladder: `core/policy.py::GATE_MODE_AUTONOMY_LABELS` (a new structured data constant mapping each of the 3 already-existing `_GATE_MODES` values to its verbatim L2/L3/L4 PRD label), `core/gate.py::describe_gate_mode` (a new pure function shaping an already-selected mode into an envelope-ready report, raising `ValueError` -- never a `Finding` -- for an out-of-vocabulary input), and `cli/gate.py::run_evaluate` wiring that folds the result into `data["gate_mode"]`/`data["autonomy_label"]` inside the existing `policy-seed-only` (no-`--run`) branch only, before `build_envelope`. The `--run` branch is untouched by design: per AD-26, a run-scoped answer must come from the (not-yet-existing) journal fold, never from policy directly, and that branch's existing `MRS-GATE-005` refusal already satisfies that AC clause by construction. "Changing gate mode is recorded as a decision entry with a timestamp and provenance" is explicitly out of scope -- no `core/journal`, no mode-change entry point, and no "run" concept exist anywhere in the package yet (Epic 3, `backlog`) -- and is logged in `deferred-work.md`, mirroring Story 2.4's identical precedent.

**Files changed:**
- `src/pyforge/marshal/core/policy.py` -- added `GATE_MODE_AUTONOMY_LABELS`, co-located with `_GATE_MODES`.
- `src/pyforge/marshal/core/gate.py` -- added `describe_gate_mode`; extended the module docstring.
- `src/pyforge/marshal/cli/gate.py` -- wired `describe_gate_mode`'s result into `data` in the `policy-seed-only` branch; extended `_render_text` to project `gate_mode`/`autonomy_label` into the default text output (review-pass fix, see below).
- `tests/unit/test_policy.py` -- 3 new tests covering the label mapping's key-set completeness, entry shape, and verbatim FR-24 text.
- `tests/unit/test_gate.py` -- 5 new tests covering `describe_gate_mode` for all 3 modes, return-value freshness, and the out-of-vocabulary `ValueError`.
- `tests/unit/test_cli.py` -- 5 new/extended tests covering the JSON envelope (default + project-overridden mode), the `--run` branch's continued omission, the text-format projection (review-pass fix), and a malformed-policy-value fallback (review-pass fix).
- `_bmad-output/implementation-artifacts/deferred-work.md` (gitignored) -- new entry logging the spec's own named deferred gap (mid-run decision-entry recording).

**Review findings breakdown:** 2 patches applied (1 high, 1 low), 0 deferred from this review pass, 8 rejected (verified against AD-26's own text, existing `DEFAULT_POLICY`/`--run`-branch precedent, and this AC's actual scope -- full detail in the Review Triage Log above). No intent gaps, no bad-spec loopbacks.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **931 passed, 8 deselected**, zero regressions (baseline 928 from the implementing subagent's pass; +3 from the review-pass patch). Independently re-run after every patch, not just trusted from a subagent's report.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- **58 passed, 2 failed**, confirmed identical to the same two pre-existing `pyforge-steward` dependency-declaration failures already logged in `deferred-work.md` (unrelated -- this diff touches only `pyforge-marshal`'s own files, no dependency added).
- Manually ran `marshal gate evaluate` (default text format) before and after the review-pass fix to directly observe the defect and its resolution, not just infer it from a diff read.
- Diff independently re-read file-by-file against the spec's Code Map and Never clause; confirmed no file outside the sanctioned list was touched.

**Residual risks:**
- The mid-run gate-mode-change decision-entry recording remains fully unbuilt (see the `deferred-work.md` entry) -- Epic 3's `core/journal` is a hard prerequisite, and no story before it can close this AC clause.
- `marshal gate evaluate --run <id>` still reports the whole run-scoped question as unavailable (`MRS-GATE-005`, pre-existing from Story 2.1) rather than answering it from a journal fold -- unchanged by this story, tracked against Story 3.2.
