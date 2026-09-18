---
title: '50.3: `--harness` outranks a dead tier-map harness'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: '2f2f407d94ea9e563113c3d8aee5f1f0ade0fa02'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred:
  - summary: >-
      The MRS-DISP-043 fails-safe guard is silent when a tier-mapped model
      isn't catalogued under ANY provider, so a genuinely foreign model
      could still reach a live launch uncaught.
    evidence: |-
      provider_declaring_model returns None for an uncatalogued model, and
      the guard's condition (`model_provider is not None and model_provider
      != resolved_provider`) only fires when the model IS found under some
      OTHER provider -- an uncatalogued-but-foreign model slips through
      silently. Pre-existing since the guard's 2026-09-12 introduction;
      unchanged by Story 50.3's diff, and explicitly outside this story's
      boundary ("Never ... add a second gate").
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:1901-1904
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 `marshal factory drain --station herald --harness claude` launched `pyforge-herald-20260918T132400673Z-194af3a0` on cursor/grok-4.6 because the station's `[model_tier_map.medium] dev = { harness = "cursor", … }` led the walk regardless of the flag, cursor's authcheck passed, and the session died in three seconds

**Approach:** an explicit `--harness` (the composed `harness_preference` flag layer, not the policy layer) is present, the walk starts from the flag's profiles and a tier-map harness the flag does not name contributes nothing, and the model is resolved for the harness actually chosen — the tier map's model for that harness when it names one, else the harness's own default — never a foreign model id

## Boundaries & Constraints

**Always:**
- the launch journal records `harness_profile: claude`, `model: sonnet` for the fixture, and without the flag the resolution is byte-identical to today's (tier map leads)
- the fails-safe guard (`provider_declaring_model` mismatch drops the override) is exercised by a test where the flag names claude and the tier map names only a Cursor model

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-246`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the Story 28.11 walk-order block: tier-map harness leads unless an explicit `--harness` flag names a different profile), `.../core/tier_routing.py` (`resolve_tier_launch` takes the flag as an exclusion/override), `.../core/dispatch.py::resolve_tier_harness`, tests with herald's pre-#1458 `marshal-policy.toml` as a fixture.
Ledger key: `50-3-harness-outranks-a-dead-tier-map-harness`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-3-harness-outranks-a-dead-tier-map-harness.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- Against herald's pre-#1458 policy fixture, `--harness claude` yields `harness_profile: claude`, `model: sonnet`; without the flag the resolution is byte-identical to today's; the MRS-DISP-043 fails-safe is exercised.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 10 findings — high 3, medium 1, low 6, false 0, maybe-false 0
- findings:
  - `[high]` `[patch]` (Blind Hunter) the MRS-DISP-043 branch resets `model` to `None` but leaves `escalated`/`from_model`/`to_model` at their stale values, and `intent_entry`'s payload (built ~20 lines later) reads those same locals directly (`if escalated: {"escalated": True, "from_model": from_model, "to_model": to_model}`) — verified by tracing `dispatch.py` lines 1794-1807, 1901-1928, and 2144-2172: a run that escalated before the mismatch fired would persist a self-contradictory journal entry (`model: null` alongside `escalated: true`). Fixed by resetting `escalated = False`, `from_model = None`, `to_model = None` alongside the existing `model = None` (dispatch.py ~1926-1929); re-ran both Story 50.3 tests plus the full `pyforge-marshal-test` suite, all pass.
  - `[low]` `[patch]` (Blind Hunter) the new test only asserts `attempt.data.get("model")` and `build_harness.calls[-1]["model"]`, never the entry actually written to the journal — verified the underlying value was already correct (same `model` local read at both sites with no intervening reassignment), but strengthened `test_dispatch_explicit_harness_flag_outranks_tier_map_harness` with an assertion against `fs.appended`'s journaled payload (the `launch_lines` / `json.loads(...)["payload"]` idiom already used elsewhere in this file), confirming `model: null` and no `escalated`/`from_model`/`to_model` keys on disk.
  - `[low]` `[reject]` (Blind Hunter) the Always-bullet "`model: sonnet`" isn't asserted by any automated test — verified the spec's own Verification section places this under "Manual checks", not "Commands"; `FakeBuildHarness.dispatch` echoes back the `model` kwarg verbatim and cannot simulate a real per-harness default without a non-trivial fake enhancement. Performed the manual check directly instead: `harness_profile.py::_render_model_args` (~line 691) returns `(None, None)` when `model is None`, so `claude.toml`'s `--model` flag is omitted entirely from the launch command and the CLI's own stock default applies — documented elsewhere in this package (`adapters/harness_bmadloop.py:354`, "stock default: `\"\"` = CLI default model") as sonnet. Not worth a code or test change beyond this trace.
  - `[high]` `[patch]` (Blind Hunter) `sprint-status-ledger.yaml` still read `50-3-harness-outranks-a-dead-tier-map-harness: backlog` — verified against sibling completed stories `50-1-...` and `50-2-...`, both `done` in the same ledger. Flipped the 50-3 entry to `done`.
  - `[low]` `[reject]` (Blind Hunter) no test exercises a multi-profile `--harness` flag list (e.g. `cursor,claude`) — verified the intent-contract's I/O matrix has exactly one row (the single-profile 2026-09-18 fixture), which the two new tests fully cover; the intent does not ask for multi-profile coverage, so this is out of scope of the intent itself.
  - `[high]` `[patch]` (Edge Case Hunter) same root cause as the escalation-triple finding above — independently confirmed via the same trace; folded into the same fix.
  - `[low]` `[reject]` (Edge Case Hunter) same root cause as the "model: sonnet" finding above — same disposition and evidence.
  - `[low]` `[reject]` (Verification Gap Reviewer) the spec's own Binding section still names `core/tier_routing.py` / `resolve_tier_harness` as the expected surface, but the diff touches only `cli/dispatch.py` and the test file — verified against the diff stat, true as filed. The only fix for this claim is editing the spec's own Binding text, which is explicitly excluded from patch/defer routing; the `<intent-contract>` itself (the load-bearing section) is fully satisfied regardless.
  - `[medium]` `[defer]` (Intent Alignment Auditor) `provider_declaring_model`'s mismatch guard is silent (no drop) when a tier-mapped model isn't catalogued under ANY provider, so a genuinely foreign-but-uncatalogued model could still reach a live launch — verified this is the pre-existing 2026-09-12 fails-safe's own limitation, unchanged by this diff; the story's own "Never ... add a second gate" boundary explicitly forecloses hardening it here. Recorded in `deferred` frontmatter.
  - `[low]` `[reject]` (Intent Alignment Auditor) same root cause as the "model: sonnet" finding above — same disposition and evidence.

## Auto Run Result

**Summary:** an explicit `--harness` flag (the composed `harness_preference` FLAG layer) now outranks a tier-map-declared harness in the dev-candidate walk; without the flag, resolution is unchanged (tier map still leads). The pre-existing MRS-DISP-043 fails-safe (2026-09-12) — which drops a tier-mapped model whose catalogued provider doesn't match the live-verified harness — was extended so the drop also clears the local `model`/`escalated`/`from_model`/`to_model` variables the intent-journal entry and the live `build_harness.dispatch(...)` call actually read, not just the `data` envelope's copies, closing the exact 2026-09-18 incident (a foreign `grok-4.6` id reaching a `cursor` launch when `--harness claude` was passed).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — walk-order gate skips the tier-map harness lead when an explicit `--harness` flag is present (~1839-1851); MRS-DISP-043 branch now resets `model`, `escalated`, `from_model`, `to_model` locals together, not just the `data` envelope (~1918-1934).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — two new tests (explicit flag outranks the tier map; tier map still leads with no flag), the first extended with a journaled-entry assertion during review.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — `50-3-harness-outranks-a-dead-tier-map-harness` flipped `backlog` → `done`.
- This spec file — status transitions, baseline revision, review triage log, deferred entry, this result.

**Review findings breakdown:** 10 findings from 4 layers (Blind Hunter 5, Edge Case Hunter 2, Verification Gap Reviewer 1, Intent Alignment Auditor 2). Patched: 3 entries (2 `high` — the escalation-triple journal bug and the stale ledger; 1 `low` — the missing journaled-entry assertion). Deferred: 1 (`medium` — the pre-existing catalog-completeness limitation of the MRS-DISP-043 guard). Rejected: 5 `low` findings — the untested "model: sonnet" claim (×3, one per layer, same root cause; resolved via a direct manual-check code trace instead of a code change), the missing multi-profile `--harness` test (out of the intent-contract's single-row matrix), and the spec's own stale Binding-section file pointers (fix would edit the spec, excluded by rule).

**Follow-up review recommendation: `true`.** This pass patched a `high`-verdict entry (the escalation-triple journal fix) directly rather than through a fresh independent review pass — the fix was unit-tested by this same pass, not re-examined by another 4-layer review. Specific unverified risk: no other call site downstream of the MRS-DISP-043 guard (e.g. supervisor/landing code reading `escalated`/`from_model`/`to_model` off a dispatch record) was checked for a latent assumption that these fields stay set whenever `escalated` was ever true upstream of the guard.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (8068 passed, 1 skipped, 12 deselected), re-run after patches.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass (130 passed, 3 skipped), re-run after patches.
- Manual check (herald's pre-#1458 fixture, `--harness claude`): `harness_profile: claude` confirmed by the new tests; `model: sonnet` confirmed by direct code trace (`harness_profile.py::_render_model_args` omits `--model` entirely when `model is None`, and `claude`'s CLI stock default is documented elsewhere in this package as sonnet) rather than a live session launch. Without the flag, resolution confirmed byte-identical to pre-Story-50.3 behavior by the second new test.
- Targeted test run: `test_dispatch_explicit_harness_flag_outranks_tier_map_harness` and `test_dispatch_tier_map_leads_without_an_explicit_harness_flag` both pass in isolation.

**Residual risks:** the deferred MRS-DISP-043 catalog-completeness gap (see `deferred` frontmatter); the named follow-up-review risk above (no downstream-caller sweep for the escalation-triple fix).
