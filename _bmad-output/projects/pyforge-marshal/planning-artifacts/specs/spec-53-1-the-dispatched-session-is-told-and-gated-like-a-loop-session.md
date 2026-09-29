---
title: '53.1: The dispatched session is told and gated like a loop session'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '1735cf9f13c71e279818146464ff3a167b01d066'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py'
  - '{project-root}/scripts/spec_surface_reconcile.py'
deferred:
  - summary: >-
      reclassify_pre_existing_gate_findings can downgrade a genuine S-13.7
      guard failure (MRS-GATE-001) to a non-blocking MRS-GATE-014 WARN when
      this story's own drift is on a non-.py governed file (invisible to
      extract_failure_paths_from_verify_output's four .py-only patterns)
      and the guard's combined output also names an unrelated, genuinely
      pre-existing drift finding on a .py file elsewhere in the repo -- that
      unrelated .py path is the only one extracted, it falls outside this
      story's blast radius, and the whole finding (including this story's
      real, un-reconciled non-.py drift) is downgraded to WARN.
    evidence: >-
      extract_failure_paths_from_verify_output (core/dispatch_verification.py)
      restricts all four regexes to .py paths; gather_spec_surface's "drift"
      finding detail (pyforge-doctor core/chain.py, _drift_findings) embeds
      the governed path in prose with no extension restriction, so a
      non-.py drift line never matches extraction while a co-occurring .py
      drift line elsewhere does -- reclassify_pre_existing_gate_findings'
      any()-over-extracted-paths check then sees only the unrelated,
      out-of-blast-radius .py path and downgrades. Root cause predates this
      story (extract_failure_paths_from_verify_output's .py-only scope is
      unchanged by this diff); this story is what first routes the S-13.7
      guard's broad, multi-path, mixed-extension output through it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verification.py:81
      (extract_failure_paths_from_verify_output),
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verification.py:175
      (reclassify_pre_existing_gate_findings)
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-20 every dispatched session (doctor 26.1 and 29.1, steward 61.3 and 61.4, marshal 51.11 and 46.7) landed green and left `main` red on `spec-surface` until a human named the changed paths on the owning Spec's memlog and its co-governors. bmad-loop sessions never do this: `harness_bmadloop::render_policy_toml` appends `python scripts/spec_surface_reconcile.py` to every loop's verify commands (the S-13.7 guard, CAP-239), so a loop story cannot go green until the session reconciles. `marshal factory dispatch` has neither half — `dispatch_verify` runs only the station's `verify_commands`, and the `harness_bmadbuild` prompt says nothing about memlogs or about `location:` on deferrals (intake then refuses them by hand later).

**Approach:** the dispatch prompt states the obligation verbatim (name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names; never `--write-baseline`; every `deferred:` entry cites a repo path in `location:`), and the S-13.7 guard is appended to the effective verify commands the session runs — at render, derived from the same constant the loop adapter uses, never declared per project — with `check_spec_binding` treating the derived guard as implicit so no pre-authored tracked spec changes.

## Boundaries & Constraints

**Always:**
- The guard is `python scripts/spec_surface_reconcile.py` — the one command the loop already uses (`harness_bmadloop._SURFACE_RECONCILE_COMMAND`); one constant, two adapters
- `check_spec_binding(declared, verify_commands)` returns `()` for every existing pre-authored spec unchanged — the derived guard is implicit, not a new declaration
- The loop adapter's rendered `policy.toml` is byte-identical after this story
- The prompt text is a tested constant (a test asserts the obligation, the co-governor rule, the `--write-baseline` prohibition and the `location:` rule are all present)

**Never:**
- Do not hand the session `--write-baseline` in any form (S-13.2: a producer that can stamp its own baseline launders drift)
- Do not add the guard to any station's `marshal-policy.toml` or to any tracked spec's `## Verification` (derive, don't declare)
- Do not change what the guard checks — `scripts/spec_surface_reconcile.py` is doctor's read-only verdict, untouched

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| session changes governed files and names them | memlog entries present for every changed path | verification passes | n/a |
| session changes governed files and names none | drift rows for its own paths | the guard fails the session's verification naming the paths; the session fixes it before HALT | n/a |
| session changes no governed file | nothing to name | the guard is silent (CAP-239: silence is not a finding) | n/a |
| pre-authored spec lists only station verify_commands | MRS-GATE-010 binding check | `()` — the derived guard is implicit | n/a |
| deferral without `location:` | the session writes one | the prompt's rule forbids it; the guard's output reports it when it still appears | reported, never silent |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-261` (a).
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` (the prompt constant), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` and `cli/dispatch.py` (the derived guard appended to the effective verify commands), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py::check_spec_binding` (implicit derived guard), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (the shared constant only; rendering unchanged), tests in `tests/unit/`.
Ledger key: `53-1-the-dispatched-session-is-told-and-gated-like-a-loop-session`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file; next marshal slot.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- Dispatch a story that changes a governed file and names nothing: the run's verification fails on the guard's verdict; dispatch one that names its paths: it lands with `spec-surface` green on `main`.

## Review Triage Log

### 2026-09-20 — Review pass

- verdicts: 9 findings — high 0, medium 2, low 3, false 4, maybe-false 0
- `[medium]` `[patch]` `run_verify_commands_only` (dispatch_verify.py, used by `dispatch_land.py`'s merge-tree preview) excluded the S-13.7 guard entirely — its exclusion rationale ("scope/spec-binding/cross-surface layers diff against `base...HEAD` and don't transfer to a merge-tree preview") is specific to git-diff-based layers; `scripts/spec_surface_reconcile.py` is filesystem-state-based (reads whatever tree it runs in against a stored baseline), so the rationale does not cover it, and a merge-tree preview would land without ever checking the guard against the tree it's actually previewing. Fixed: routed through `_verify_commands_with_surface_guard`, docstring corrected, three tests in `test_dispatch_verify_merge_tree.py` updated/added.
- `[low]` `[patch]` `_verify_commands_with_surface_guard`'s dedup used exact string equality (`!=`) while `gate.check_spec_binding`'s own membership test collapses whitespace (`" ".join(command.split())`) — a station-declared guard differing only in spacing would run (and bind) twice instead of deduping. Fixed to mirror `check_spec_binding`'s normalization; added `test_evaluate_dispatch_verification_dedupes_a_guard_declared_with_different_spacing`.
- `[false]` `[reject]` Claim that `cli/dispatch.py`'s two raw `effective_policy.verify_commands.value` reads (feeding `dispatch_re_preflight.verify_commands_fingerprint`/`compute_refuse_predicate`) being un-routed through the guard is a defect — verified: this is a pure SHA256 config-drift-detection hash for re-preflight rate-limit eligibility that never executes or enforces the listed commands; the guard is a constant, unconditionally-appended value, so omitting it from the hash cannot produce an incorrect re-preflight decision.
- `[medium]` `[defer]` `reclassify_pre_existing_gate_findings`'s `.py`-only path extraction can, under a specific confluence (this story's own drift on a non-`.py` governed file co-occurring with an unrelated, genuinely pre-existing `.py` drift finding elsewhere), downgrade a real guard failure to a non-blocking WARN — verified real by tracing `extract_failure_paths_from_verify_output`'s four `.py`-restricted patterns against `gather_spec_surface`'s "drift" finding detail format (an unrestricted-extension prose sentence in `pyforge-doctor/core/chain.py`). Root cause predates this story (the extraction utility's `.py`-only scope is unchanged); this story is what first feeds the guard's broad, mixed-extension output through it. Recorded in `deferred:` above with full evidence and location.
- `[low]` `[reject]` A station with a bare `verify_commands = []` can no longer surface `MRS-GATE-004` ("no commands configured") from `evaluate_dispatch_verification`, since the guard is now unconditionally appended and `commands` can never be empty — verified real but rejected: this exactly mirrors `harness_bmadloop.render_policy_toml`'s pre-existing, undisputed behavior (never checked for emptiness before appending the guard either), which the Always bullet's "one constant, two adapters" parity requirement already sanctions; a correct fix needs a new, independent "no station-specific commands configured" check rather than a direct correction, and a bare empty `verify_commands` is an already-rare degenerate config.
- `[low]` `[reject]` `dispatch_verify.py` reaching into `harness_bmadloop`'s `_SURFACE_RECONCILE_COMMAND` (underscore-prefixed) plus a duplicated filter-then-append idiom in both adapters, instead of a shared helper — verified not an import-linter violation (AD-3's `forbidden_modules = ["bmad_loop"]` only catches direct imports of `bmad_loop` itself with `allow_indirect_imports = true`; `harness_bmadloop` is not forbidden) and the cross-module reuse is exactly what the spec's own Always bullet mandates ("derived from the same constant the loop adapter uses... one constant, two adapters"). The remaining DRY nit is low-severity, unlikely to bite in everyday use, and extracting a shared helper is more than a direct correction given the loop adapter's byte-identical-rendering guarantee.
- `[false]` `[reject]` `test_evaluate_dispatch_verification_dedupes_an_already_declared_guard` only exercises the guard already declared last, not first/middle — verified false: the filter-then-append algorithm removes the guard from wherever it sits and appends it at the end unconditionally, so its position in the source list cannot change the outcome; there is no untested code path, only an untested input arrangement that cannot produce a different result.
- `[false]` `[reject]` No operator-facing way to preview a dispatch station's effective verify-command list (including the guard) before a run, unlike a loop home's inspectable rendered `policy.toml` — verified false: this is an intentional, already-documented design trade-off (`_verify_commands_with_surface_guard`'s own docstring: "this is not a rendered file... it is folded in at USE time"); the Always bullet requires guard-content parity across the two adapters, not preview-mechanism parity.
- `[false]` `[reject]` Intent Alignment terminology divergences (spec's Approach says the guard is applied "at render" vs. the dispatch implementation applying it "at USE time"; R3-vs-R4 enforcement-mechanics phrasing; edge-case row 5's `location:` rule coverage) — verified false: prose imprecision only, no behavioral mismatch against any Always/Never bullet or I/O matrix row; the `location:` rule is covered by the prompt-text test, and the guard's own output behavior is unchanged (Never bullet forbids changing what it checks).

## Auto Run Result

**Summary:** A `marshal factory dispatch` session is now told and gated on the S-13.7 spec-surface-reconcile obligation the same way a `bmad-loop` session already is. The dispatch prompt (`harness_bmadbuild.py`) states the memlog/co-governor/`--write-baseline`/`location:` obligations verbatim, and the effective verify commands a dispatch session actually runs are derived (never declared) with `python scripts/spec_surface_reconcile.py` appended — the same constant (`harness_bmadloop._SURFACE_RECONCILE_COMMAND`) the loop adapter already renders into every loop home's `policy.toml`. `check_spec_binding` treats the derived guard as implicit, so no pre-authored tracked spec needed a `## Verification` edit.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` — adds the `_SPEC_SURFACE_OBLIGATION` prompt constant (imported from the loop adapter's guard constant) and splices it into the dispatch prompt.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — adds `_verify_commands_with_surface_guard` (dedupes then appends the guard, whitespace-normalized like `check_spec_binding`); `evaluate_dispatch_verification` now runs commands through it; `run_verify_commands_only` (the `dispatch_land.py` merge-tree preview) also routed through it (review-pass fix, since the guard is filesystem-state-based and does transfer to a merge-tree preview, unlike the scope/spec-binding/cross-surface layers that function deliberately omits).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` — docstring only: documents `check_spec_binding`'s existing normalization now relied on by the guard's dedup.
- `tests/unit/test_dispatch_verification.py`, `tests/unit/test_dispatch_verify_merge_tree.py`, `tests/unit/test_gate.py`, `tests/unit/test_harness_bmadbuild.py` — new/updated coverage for the prompt constant, guard append/dedup/failure behavior, spec-binding transparency, and the merge-tree preview's guard inclusion.

**Review findings breakdown** (9 findings; see `## Review Triage Log` above for full evidence):
- Patched (2): `run_verify_commands_only` excluding the guard from the merge-tree preview (medium); exact-match (non-whitespace-normalized) dedup in `_verify_commands_with_surface_guard` (low).
- Deferred (1): `reclassify_pre_existing_gate_findings`'s `.py`-only path extraction can mask this story's own non-`.py` drift when an unrelated pre-existing `.py` drift finding co-occurs (medium; root cause pre-exists this story) — recorded in `deferred:` frontmatter.
- Rejected (6, all `false` or `low`): the `cli/dispatch.py` re-preflight fingerprint reads being un-routed through the guard (false — pure drift-detection hash, never executed); lost `MRS-GATE-004` signal for a station with empty `verify_commands` (low — mirrors pre-existing, sanctioned loop-adapter parity behavior); private-constant cross-module reach and a duplicated filter/append idiom (low — the exact pattern the spec's Always bullet mandates, not an import-linter violation); the dedup test's guard-already-last-position coverage gap (false — the algorithm is position-independent); no operator-facing preview of a dispatch station's effective verify commands (false — a documented, intentional design trade-off); Intent Alignment's terminology divergences ("at render" vs "at USE time" wording, R3/R4 phrasing, edge-case row 5 coverage) (false — prose imprecision only, no behavioral mismatch).

**Follow-up review recommendation:** `false`. This pass patched one `medium` and one `low` entry — not two or more `medium`, and no `high` — so the first-pass threshold is not met.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8346 passed, 1 skipped, 12 deselected (re-run after patches; exit 0).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped (re-run after patches; exit 0).
- Manual trace (in lieu of a live dispatch run): confirmed `evaluate_dispatch_verification`'s two real call sites (`cli/dispatch.py`, `dispatch_supervisor/__main__.py`) and `run_verify_commands_only`'s one call site (`dispatch_land.py`) all resolve the guard through the same `_verify_commands_with_surface_guard` function; confirmed the loop adapter's `render_policy_toml` output is byte-identical (untouched by this diff); confirmed `check_spec_binding` returns `()` unchanged for a pre-authored spec that never names the guard (existing + new tests).

**Residual risks:** the deferred `reclassify_pre_existing_gate_findings` gap (above) remains: a dispatch session whose own drift is entirely on non-`.py` governed files, occurring alongside an unrelated pre-existing `.py` drift elsewhere in the repo, could still land with its own drift silently downgraded to WARN. `main`'s own `spec-surface-check` CI gate is an independent backstop that would still catch the residual drift after landing.
