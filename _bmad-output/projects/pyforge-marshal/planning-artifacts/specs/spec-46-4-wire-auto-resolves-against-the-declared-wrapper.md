---
title: 'Wire auto resolves against the declared wrapper'
type: 'feature'
created: '2026-09-18'
status: 'done'
baseline_revision: '84dda5b0733a3c7cbc37887982e18c640ebdc582'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `[context.wire]`'s `enabled` key is a plain `bool` today, so every station must hand-declare it (only pyforge-marshal's own `marshal-policy.toml` currently does, leaving wire off fleet-wide) and there is no way for a repo default to say "on when the harness can, off when it can't" without per-harness config.

**Approach:** Give `enabled` a third state, `"auto"`, validated only for the `wire` layer; add a repo-default `[context]` block in `policy-defaults.toml` (the 4 harness-agnostic layers `enabled = true`, `[context.wire] enabled = "auto"`); resolve `"auto"` at the point each call site already has the concrete harness profile in hand (never earlier, and never by force-coercing `"auto"` to `bool`) against whether that profile declares a `[wrapper]`; and trim pyforge-marshal's own `marshal-policy.toml` `[context]` block to nothing, since a station file must now only carry explicit force-overrides.

## Boundaries & Constraints

**Always:**
- `enabled = "auto"` is valid only for the `wire` layer; the other 4 `CONTEXT_LAYER_NAMES` keep the existing strict-`bool`-only posture.
- The tri-state collapses to a concrete `bool` only where the resolver already has the actual harness profile (never inside `policy.py::resolve_context_layers`, which composes before any profile is chosen — see Code Map for why).
- No `[wrapper]` on the resolved profile → `"auto"` resolves to `False`, a clean, silent skip (`WireWrap(applied=False, reason=None)`) — never a journaled attempt, matching Story 28.29's Cursor precedent.
- `[wrapper]` declared but its binary does not resolve on PATH → stays a WARN (`MRS-DISP-033`-class `WireWrap(applied=False, reason=<non-empty>)`), regardless of whether `enabled` got there via `"auto"` or an explicit `true`. This path is already correct and untouched.
- A station's `marshal-policy.toml` `[context]` block, if present at all, is a force-override only (explicit `true`/`false` per layer) — never a re-declaration of the repo-default shape.

**Never:**
- Do not touch `sprint-status-ledger.yaml` or mint a new story key.
- Do not run `scripts/bmad-switch`; this spec and its code changes are pinned to physical `_bmad-output/projects/pyforge-marshal/` paths.
- Do not flip the parent Dream to `realized`.
- Do not build the "unsupported vs. degraded" journal-taxonomy split described in the epic context's Technical Decisions — that is Story 46.5's surface (it depends on this story existing first), not this one's. This story's only journal-visible change is that a wrapperless profile under `auto` now produces the SAME clean `WireWrap(applied=False, reason=None)` shape the code already produces for `enabled=false` today — no new finding code, no new journal field.
- Do not touch `render_policy_toml`'s (`adapters/harness_bmadloop.py`) writing of the (currently inert, undocumented-as-consumed) `[context]` table into the rendered bmad-loop `policy.toml` beyond what naturally follows from `resolve_context_layers`'s changed wire-entry shape — that table is explicitly documented as unread by bmad-loop today (CAP-2 territory), out of scope here.
- Do not trim the other 7 stations' `marshal-policy.toml` `[context]` blocks — none of them declare `[context.wire]` (only pyforge-marshal's does), so none of them force-override the new `auto` default; leaving their existing 4-layer declarations in place is redundant with the new repo default but not a behavior conflict, and touching 7 unrelated files is out of scope for a surgical change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh loop home, zero station config, Claude profile | repo defaults only; resolved profile declares `[wrapper]` (`claude.toml`) | `output`/`structure-graph`/`derived-context`/`planning-graph` journal `enabled=true`; wire resolves `enabled=True` → `WireWrap.applied=True` (binary present) | No error expected |
| Same, but Cursor profile | repo defaults only; resolved profile declares no `[wrapper]` (`cursor.toml`, Story 28.29) | Wire resolves `enabled=False` → `WireWrap(applied=False, reason=None)`, a clean skip, never journaled as an attempted wrap | No error expected |
| Wrapper declared but binary missing | Claude profile, `[wrapper].binary="headroom"` not on PATH, wire `auto` (or explicit `true`) | `WireWrap(applied=False, reason=<non-empty>)` — a WARN (`MRS-DISP-033`-class), never silent | Existing degraded path, unchanged by this story |
| Station force-overrides wire off | station `marshal-policy.toml` declares `[context.wire] enabled = false`, profile has `[wrapper]` | Wire resolves `enabled=False` → clean skip — the explicit override wins over the profile fact | No error expected |
| Station force-overrides wire on, no wrapper | station declares `[context.wire] enabled = true`, profile has no `[wrapper]` | Wire resolves `enabled=True` against a `None` wrapper → existing degraded/WARN path (unchanged code) | WARN, not silent |
| Malformed `[context.wire]` value | `enabled = "always"` (any string other than `"auto"`) | `_valid_context_block` rejects the whole field for that layer (existing "one bad entry poisons the layer" contract) | Field excluded, not an exception |
| `attempt_spin_wire_layer` / `spin.py` fallback with no resolvable marshal profile for the adapter | `wire_layer["enabled"] == "auto"`, `PROFILE_BY_BMADLOOP_ADAPTER` has no entry for the adapter (or the packaged profile itself is missing, or no adapter name resolves at all) | `"auto"` resolves to `False` (no profile ⇒ no `[wrapper]` fact ⇒ clean skip) — not a WARN | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py:936-988` (`_valid_context_block`) — the `enabled` gate at `975-977` (`enabled = settings.get("enabled"); if not isinstance(enabled, bool): return None`) rejects everything non-`bool` today. Widen only for `layer_name == "wire"` to also accept the literal string `"auto"`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py:1868-1907` (`resolve_context_layers`) — the single composition site both `cli/dispatch.py::dispatch_once` and `adapters/harness_bmadloop.py::render_policy_toml` call. Currently line `"enabled": bool(layer_declared.get("enabled", False))` force-coerces every layer's value — `bool("auto")` is `True`, which would silently destroy the tri-state before it ever reaches a profile-aware resolver. Fix: for the `wire` layer only, pass the raw declared value through unresolved (`"auto"`, `True`, or `False`, defaulting to `False` when the layer is absent) instead of coercing; the other 4 layers keep the existing `bool(...)` coercion (harmless — validation already guarantees a real `bool` for them). This function runs at policy-composition time, **before** any harness profile is chosen (`cli/dispatch.py` resolves `resolution.profile` later, after a live binary+authcheck walk over `harness_preference`) — this is why the tri-state must NOT be finalized here.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py:733-836` (`resolve_wire_wrap(profile, *, wire_layer, home, wrapper_binary_path)`) — the function every call site (`cli/dispatch.py`, `adapters/harness_bmadloop.py::attempt_spin_wire_layer`) already calls **after** the concrete `profile` is known. Line `761`: `enabled = bool((wire_layer or {}).get("enabled", False))`. This is the correct, single place to finalize the tri-state: replace with a call to the new `resolve_wire_enabled` helper (below), passing `wrapper_declared=profile.wrapper is not None`. Every branch below this line (lines 762-835: disabled/off, wrapper-is-None degraded with the Story 28.29 Cursor-specific reason text, not-reversible degraded, binary-not-on-PATH degraded/WARN, applied) is unchanged — they already implement every AC in this story once `enabled` is correct.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` (new, near `WireWrap`/`resolve_wire_wrap`) — add a small pure helper:
  ```python
  def resolve_wire_enabled(raw: object, *, wrapper_declared: bool) -> bool:
      """Tri-state wire-layer enable resolution (Story 46.4): the literal
      ``"auto"`` resolves against whether the harness profile declares a
      ``[wrapper]``; any other declared value is a force-override, coerced
      to ``bool`` exactly as before."""
      if raw == "auto":
          return wrapper_declared
      return bool(raw)
  ```
  Used by `resolve_wire_wrap` and by the two other call sites below that run the same "is wire enabled" check before a profile/wrapper fact is even reachable.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py:163-179,184-195` (`attempt_spin_wire_layer`) — two early-exit branches (`profile_stem is None`; `profile is None`) each do `enabled = bool((wire_layer or {}).get("enabled", False))` **before** any profile/wrapper fact exists. Replace both with `resolve_wire_enabled(..., wrapper_declared=False)` (no profile ⇒ no `[wrapper]` fact ⇒ `"auto"` must resolve off, not misread as an explicit `true`). The main path (line `205`, which already calls `resolve_wire_wrap` once a profile IS found) needs no change.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py:1237` — a third, independent `enabled = bool(wire_layer["enabled"])` fallback for the case where no `adapter_name` resolves at all (same "no profile ⇒ no wrapper fact" shape as above). Replace with `resolve_wire_enabled(wire_layer["enabled"], wrapper_declared=False)`.
- `_bmad-output/policy-defaults.toml` — currently has no `[context]` block at all (confirmed by direct read). Add:
  ```toml
  [context.output]
  enabled = true

  [context."structure-graph"]
  enabled = true

  [context."derived-context"]
  enabled = true

  [context."planning-graph"]
  enabled = true

  [context.wire]
  enabled = "auto"
  ```
  mirroring the quoting convention already used for hyphenated TOML keys in the station files (`[context."structure-graph"]`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:~330-370` — remove the entire `[context.wire]`/`[context.output]`/`[context."structure-graph"]`/`[context."derived-context"]`/`[context."planning-graph"]` block and its Story 33.2 comment. Per `core/policy.py::_merge_field`'s wholesale-per-field (not deep-merge) composition, a station file that declares ANY part of `context` replaces the repo default's entire `context` value for that station — so pyforge-marshal's own file must now declare nothing there to actually inherit the new repo-default shape (including the new `auto` wire behavior). This is the concrete meaning of "per-station `marshal-policy.toml` becomes force-override only."
- `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` — extend `_valid_context_block` coverage: `"auto"` accepted for `wire`, rejected for the other 4 layers; extend `resolve_context_layers` coverage: wire's raw tri-state value passes through unresolved (not coerced to `bool`) while the other 4 layers still resolve to `bool`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py:267-283` (`test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch`) — reads the REAL tracked `marshal-policy.toml` for `pyforge-marshal` via `_compose_policy("pyforge-marshal")` and currently asserts all 5 layers resolve `{"enabled": True, "aggressiveness": "medium"}`. Once the station file's `[context]` block is removed, `wire`'s value comes from repo-defaults' `"auto"` and passes through `resolve_context_layers` unresolved (no profile in scope at this composition point) — update this one assertion to `resolved["wire"] == {"enabled": "auto", "aggressiveness": "medium"}`, keep the other 4 layers' assertion unchanged (still `True`, now sourced from repo-defaults instead of the station file).
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py` — add coverage for `resolve_wire_enabled` (auto+wrapper→True, auto+no-wrapper→False, explicit-true+no-wrapper→True unchanged) and for `resolve_wire_wrap` under `enabled="auto"` against both a `claude`-shaped profile (wrapper declared) and a `cursor`-shaped profile (no wrapper, clean skip).

## Tasks & Acceptance

**Execution:**
- `core/policy.py` -- widen `_valid_context_block`'s `enabled` check to accept `"auto"` when `layer_name == "wire"` -- lets the repo default declare the tri-state without loosening validation for the other 4 layers.
- `core/policy.py` -- change `resolve_context_layers`'s wire-layer entry to pass the raw declared value through instead of force-coercing to `bool` -- preserves the tri-state past the one composition site that runs before a profile is known.
- `core/harness_profile.py` -- add `resolve_wire_enabled(raw, *, wrapper_declared)` and use it inside `resolve_wire_wrap` in place of the current `bool(...)` line -- the single point where the tri-state becomes a concrete launch decision, at the point the profile is actually known.
- `adapters/harness_bmadloop.py` -- use `resolve_wire_enabled(..., wrapper_declared=False)` in `attempt_spin_wire_layer`'s two no-profile early-exit branches -- keeps `auto` from being misread as an explicit `true` when there is no profile to check for a `[wrapper]`.
- `cli/spin.py` -- same substitution in the no-adapter-resolved fallback branch around line 1230.
- `_bmad-output/policy-defaults.toml` -- add the `[context]` block (4 layers `true`, wire `"auto"`) -- makes the harness-agnostic layers and the tri-state the actual repo default.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` -- remove its `[context]` block entirely -- the station stops re-declaring the shape repo-defaults now owns, becoming force-override-only per the story's Surface.
- `tests/unit/test_policy.py`, `tests/unit/test_harness_profile.py` -- cover the I/O matrix above.
- `tests/unit/test_dispatch.py` -- update `test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch`'s wire-layer assertion from `{"enabled": True, ...}` to `{"enabled": "auto", ...}` now that the station file no longer force-declares it.

**Acceptance Criteria:**
- Given a fresh loop home with zero station config, when a dispatch or spin launches, then the harness-agnostic layers (`output`, `structure-graph`, `derived-context`, `planning-graph`) journal as on, and wire is on iff the resolved harness profile declares a `[wrapper]`.
- Given the resolved profile is Cursor's (no `[wrapper]`), when wire is `"auto"`, then the launch takes a clean skip — `WireWrap(applied=False, reason=None)` — never a journaled wrap attempt.
- Given a profile that declares `[wrapper]` but whose binary does not resolve on PATH, when wire is `"auto"` or explicit `true`, then the result stays a WARN-class `WireWrap(applied=False, reason=<non-empty>)`, never silent.
- Given a station `marshal-policy.toml` with no `[context]` block at all, when policy composes, then it inherits the repo-default `[context]` block unchanged (proving the station file is no longer required to hand-declare the 5 layers).

## Design Notes

The tri-state must be resolved in `core/harness_profile.py`, not `core/policy.py::resolve_context_layers`, because `resolve_context_layers` runs at policy-composition time in `cli/dispatch.py::dispatch_once` before `resolution.profile` is chosen (a live binary+authcheck walk over `harness_preference` that happens later). Reordering `dispatch_once`/`spin.py`/`render_policy_toml` to resolve the profile earlier would be a much larger, riskier change for no benefit, since `resolve_wire_wrap` (and its two sibling early-exit call sites) already run at exactly the right point — after the profile is known — at every call site that matters. Centralizing the actual bool-collapse in one small `resolve_wire_enabled` helper, reused by all three sites that currently duplicate the `bool((wire_layer or {}).get("enabled", False))` pattern, keeps the fix to one new function plus three one-line call-site substitutions.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new/updated `test_policy.py` and `test_harness_profile.py` coverage.
- `pixi run -e pyforge-guild pr-preflight` -- expected: clean before push (this branch's changes are confined to `src/` and `_bmad-output/`, outside `recipes/`, so the `maintenance` label applies at PR time per CLAUDE.md; `pixi.toml` itself is untouched by this story, so the environment-sync gate does not apply).

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 11 findings — high 4, medium 2, low 4, false 1, maybe-false 0
- findings:
  - `[high]` `[patch]` (Blind Hunter) `_spawn_supervisor_sidecar` (`cli/spin.py`) re-derived wire's enabled state via a fresh `harness_profile.resolve_wire_enabled(wire_layer["enabled"], wrapper_declared=False)` instead of reusing the already-resolved `wire_payload` computed earlier in the same function — under the new repo-default `"auto"`, this silently stopped writing `compression-ladder.json` (CAP-8/Story 28.6) for every launch where wire genuinely applies. — Verified by reading `_spawn_supervisor_sidecar` directly: `wrapper_declared=False` is only correct at a call site with no profile in scope, but this call site sits right after `wire_payload` was already resolved against the real profile a few lines above. Fixed by gating on `wire_payload.get("applied")` instead.
  - `[high]` `[patch]` (Edge Case Hunter) same root cause, filed from the wrapper-declared-but-`"auto"`-resolves-applied angle — the sidecar write silently regresses exactly the launches this story means to turn ON. — Carried by the group; same fix.
  - `[high]` `[patch]` (Verification Gap Reviewer) same root cause, filed against the untested `_spawn_supervisor_sidecar` gate — no test exercised the sidecar-write path under `"auto"` resolving to applied. — Carried by the group; same fix (no new test added for the sidecar write itself — out of this pass's minimal-fix scope, noted as a residual risk below).
  - `[high]` `[patch]` (Intent Alignment Auditor) same root cause, filed as a direct violation of the spec's own Intent ("wire turns on exactly where the harness can take it") since the sidecar stopped tracking wire's real disposition. — Carried by the group; same fix. Applying the fix surfaced a second, self-inflicted defect: the sidecar's `aggressiveness` field read from the now-removed local `wire_layer`, which was only bound on one of the function's two paths, producing `UnboundLocalError` on the common path (82 of 7972 tests failed). Fixed by sourcing `aggressiveness` from `wire_payload` too, which is defined on every path; full suite re-run confirmed 0 regressions.
  - `[medium]` `[patch]` (Verification Gap Reviewer) `attempt_spin_wire_layer`'s second fallback branch (`profile_stem` resolves via `PROFILE_BY_BMADLOOP_ADAPTER` but `load_packaged_profiles()` lacks that stem) had zero test coverage of the new `"auto"` tri-state, though the code itself was already correct. — Verified via `grep -rn "attempt_spin_wire_layer" tests/unit/*.py` (one call site only) and a direct read of the function. Added `test_attempt_spin_wire_layer_auto_with_unresolvable_packaged_profile_is_a_clean_skip`, monkeypatching `load_packaged_profiles` to `dict`.
  - `[medium]` `[patch]` (reviewer finding) `seed/detect/kit.py::layer_enabled` has no harness-profile seam to resolve `"auto"` against, so `bool("auto")` is unconditionally `True` — under the new repo-default, `marshal seed check`/`kit` now always probes wire (a misleading UNAVAILABLE diagnostic) for all 8 stations, including harnesses with no `[wrapper]` at all (e.g. Cursor), where it previously -- and should still -- read off. — Verified by tracing `kit_checks` → `seed/verbs/check.py` (no `harness_profile`/`adapter_name`/`resolve_wire_wrap` reference anywhere in that chain, confirmed by grep). Fixed by treating an unresolved string value as OFF, matching the function's own pre-existing "ambiguous reads as off" docstring contract; added `test_unresolved_auto_reads_as_off`.
  - `[false]` `[reject]` (reviewer finding) `cli/spin.py`'s `MRS-SPIN-017` finding-gate (`bool(context_layers[harness_profile.WIRE_LAYER_NAME]["enabled"])`) also raw-coerces `"auto"`, claimed as a second instance of the same coercion bug as the CAP-8 finding above. — Refuted: this line is reached only when `wire_payload.get("applied") is False and reason` is truthy, and `WireWrap.reason` is non-`None` only in degraded cases that themselves only occur when the real resolved `enabled` was already `True` (traced through `resolve_wire_wrap`'s branches) — so `bool("auto")`'s coercion can never diverge from the real resolution at this specific call site.
  - `[low]` `[patch]` (reviewer finding) `_bmad-output/policy-defaults.toml` lost its trailing newline after the story's `[context]` block was appended. — Verified via `tail -c 30 policy-defaults.toml | xxd` (ended `...61 7574 6f22`, no `0a`). Appended a trailing `\n`.
  - `[low]` `[patch]` (reviewer finding) `test_spin_states_the_wire_layer_disposition_on_every_run` was rewritten from an exact-dict match (including `store_dir`) to three cherry-picked field assertions, dropping `store_dir` coverage entirely for the new `applied=True` case. — Verified against the diff hunk (old body asserted `envelope["data"]["wire"] == {...}` incl. `"store_dir": None`). Restored `assert envelope["data"]["wire"]["store_dir"] is not None` (the packaged `claude` profile declares `store_env`, so `store_dir` is genuinely non-`None` once `applied=True`).
  - `[low]` `[reject]` (reviewer finding) `render_policy_toml` now persists the literal string `"auto"` into the rendered bmad-loop `policy.toml` `[context]` table, which no code path reads back. — Not a defect: the spec's own Never section explicitly excludes touching `render_policy_toml`'s writing of that table "beyond what naturally follows from `resolve_context_layers`'s changed wire-entry shape" — the string landing there is exactly that natural, expected follow-on, not a gap.
  - `[low]` `[reject]` (reviewer finding) `sprint-status-ledger.yaml` was not updated to reflect this story's status. — Not this story's problem: the spec's Never section explicitly excludes touching `sprint-status-ledger.yaml` or minting a new story key for this run.

## Auto Run Result

**Summary:** `[context.wire]`'s `enabled` key gained a third state, `"auto"`, which resolves at the point each call site already has the concrete harness profile in hand against whether that profile declares a `[wrapper]`. `_bmad-output/policy-defaults.toml` now carries a repo-default `[context]` block (the 4 harness-agnostic layers `enabled = true`, `[context.wire] enabled = "auto"`), and pyforge-marshal's own `marshal-policy.toml` `[context]` block was trimmed to nothing, becoming force-override-only like every other station's file.

**Files changed:**
- `_bmad-output/policy-defaults.toml` — added the repo-default `[context]` block (4 layers `true`, wire `"auto"`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — removed its own `[context]` block entirely.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — `_valid_context_block` accepts `"auto"` for the `wire` layer only; `resolve_context_layers` passes wire's raw declared value through unresolved instead of coercing to `bool`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` — added `resolve_wire_enabled(raw, *, wrapper_declared)`; `resolve_wire_wrap` now calls it instead of a blind `bool(...)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — `attempt_spin_wire_layer`'s two no-profile early-exit branches use `resolve_wire_enabled(..., wrapper_declared=False)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` — the no-adapter-resolved fallback uses `resolve_wire_enabled(...)`; `_spawn_supervisor_sidecar`'s CAP-8 compression-ladder gate now reads `wire_payload.get("applied")`/`wire_payload["aggressiveness"]` (review-pass fix, see Triage Log).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py` — `layer_enabled` treats an unresolved string (`"auto"`) as OFF (review-pass fix).
- `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` — `"auto"` accepted for `wire`, rejected for the other 4 layers; `resolve_context_layers` passthrough coverage.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py` — new coverage for `resolve_wire_enabled` and `resolve_wire_wrap` under `"auto"`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — updated the real-repo composed-policy assertion for `wire` from `{"enabled": True, ...}` to `{"enabled": "auto", ...}`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_wire.py` — two new tests covering `attempt_spin_wire_layer`'s no-resolvable-profile and no-packaged-profile fallback branches under `"auto"`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py` — new coverage for `layer_enabled`'s unresolved-`"auto"`-reads-as-off fix (review-pass fix).
- `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` — updated the wire-disposition assertion for the new repo-default-applies case; restored a `store_dir` assertion (review-pass fix); declared wire explicitly off in the oversized-preview test to keep it deterministic (review-pass fix).
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad11_write_boundary.py` — declared wire explicitly off in the write-boundary guard test to keep its fixed write count deterministic (review-pass fix).

**Review findings breakdown:**
- Patched (6 entries, 9 member rows): CAP-8 sidecar regression (high, 4 rows, one per converging layer); `attempt_spin_wire_layer` second-branch test gap (medium); `kit.py::layer_enabled` auto-as-always-on (medium); missing trailing newline in `policy-defaults.toml` (low); dropped `store_dir` test assertion (low).
- Rejected (3 entries): `spin.py:1256`'s `MRS-SPIN-017` gate coercion — false, refuted via `WireWrap`'s reason-only-when-enabled invariant; `render_policy_toml` persisting `"auto"` as a string — explicitly permitted by the spec's own Never section; `sprint-status-ledger.yaml` drift — explicitly excluded by the spec's own Never section.
- Deferred: none.

**Follow-up review recommendation:** `true`. This pass patched one `high`-verdict entry (the CAP-8 compression-ladder sidecar gate) — per the first-pass rule, any patched `high` entry triggers a recommendation regardless of the other patched counts (1 high, 2 medium, 2 low). Named unverified risk: the `_spawn_supervisor_sidecar` fix (gating the CAP-8 sidecar write on `wire_payload.get("applied")` and reading `aggressiveness` from `wire_payload` instead of the removed local `wire_layer`) was authored and self-verified within this same pass, not confirmed by an independent review layer, and no new test exercises the sidecar-write path itself under a genuinely-applied `"auto"` resolution (existing coverage is all `FakeFs`/monkeypatched). A follow-up pass should add or run an integration-level check of `marshal factory spin` with a real resolvable wrapper binary and confirm `compression-ladder.json` is actually written with the expected `aggressiveness` value.

**Verification performed:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — 7974 passed, 1 skipped, 12 deselected, EXIT:0 (final run, after all patches).
- Intermediate run after the first patch batch surfaced 82 failures (`UnboundLocalError: local variable 'wire_layer' referenced before assignment`) — self-inflicted by the CAP-8 fix removing `wire_layer`'s only unconditional binding; fixed and re-verified down to 2 failures, then 0.
- `pr-preflight`'s `spec-surface`/detector findings were reconciled earlier in this run as entirely foreign/pre-existing (predate `baseline_revision`, branch diff never touches the flagged paths) — see earlier session history; not re-verified in this pass since no new commits touch those paths.

**Residual risks:**
- The CAP-8 sidecar-write fix itself is unverified by an integration-level test (see follow-up recommendation above) — the risk that a real `marshal factory spin` launch with wire genuinely applied still fails to produce `compression-ladder.json` for some reason not exercised by the unit-level `FakeFs` coverage.
- `render_policy_toml` now writes the literal string `"auto"` into the rendered `[context]` table for the `wire` layer specifically (the other 4 layers still resolve to `bool`) — accepted as in-scope-permitted per the Never section, but any future code that reads that table back (none does today) must handle the tri-state, not just `bool`.
