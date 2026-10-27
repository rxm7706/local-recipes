---
title: 'Dispatch tier-routing resolver fails safe, and fleet-wide defaults stop pointing at a dead harness'
type: 'bugfix'
created: '2026-09-12'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/dispatch-tier-routing-fails-safe.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dispatch-tier-routing-fails-safe/SPEC.md
warnings: []
deferred: []
declared_low_risk: false
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `resolve_tier_launch`/`render_policy_toml` can silently produce a hybrid,
broken launch: a real adapter binary paired with another provider's model string it was
never meant to receive. Confirmed live 2026-09-12 (three identical silent dispatch
failures for pyforge-marshal Story 28.29): `model_tier_map.heavy.dev = "composer-2.5-fast"`
(a Cursor-only model, all eight stations) has no `harness` key, and this fleet's own
`harness_preference` (`cursor`-only) has no bmad-loop counterpart, so `render_policy_toml`
falls back to the template's `claude` adapter for `[adapter].name` while still writing
the Cursor model into `[adapter.dev].model`. `claude --model composer-2.5-fast` crashes
instantly (0 tokens); tmux's `pipe-pane` races the dying window (documented, tolerated,
non-fatal), so bmad-loop reports the story merely "deferred" with no signal that the
cause was a policy misconfiguration.

**Approach:** (1) `render_policy_toml` now cross-checks each tier-mapped stage's model
against the declared `model_cost_catalog` (`provider_declaring_model`, new in
`model_cost.py`); when the catalog names a provider that differs from the REAL, final
`[adapter].name` this render resolves to, the stage override is skipped — the stage
keeps the baseline model instead. (2) `resolve_stage_candidate` no longer fabricates an
answer ("never block — fall back to the first declared candidate") when nothing passes
`availability_fn`; it returns `None`, which `resolve_tier_launch`'s existing
`if resolved is None: continue` already treats as "no override for this stage." (3)
Fleet-wide, all eight stations' `model_tier_map.{heavy,medium,easy}.{dev,review}` values
reverted from Cursor's `composer-2.5`/`composer-2.5-fast` to `sonnet`/`opus` — the SAME
models the plain baseline already uses — since Cursor is independently, permanently
confirmed dead for headless dispatch (`spec-28-29-wire-is-dead-for-cursor-specifically-...`,
shipped 2026-09-10).

## Boundaries & Constraints

**Always:** Never touch `model_cost_catalog`'s pricing display or the `context.*`
compression layers. Any FUTURE `model_tier_map` entry naming a model from a
non-default-adapter provider must use the explicit `{harness, model}` inline-table form
(already supported by `parse_stage_entry`) — the bare-string shorthand is reserved for
models belonging to the base `[adapter].name`'s own provider.

**Never:** Make a Copilot (or any other harness) adoption decision here — that stays a
separate, explicit operator call. Retroactively audit historical dispatches that may
have silently hit this bug before now.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CROSS_PROVIDER_MISMATCH | `model_tier_map` stage model catalogued under a provider ≠ the resolved adapter's own | Stage override skipped; baseline `[adapter]`/`[adapter.review]` model kept | N/A |
| SAME_PROVIDER_MATCH | `model_tier_map` stage model catalogued under the SAME provider as the resolved adapter | Override applies as before | N/A |
| UNCATALOGUED_MODEL | Stage model absent from `model_cost_catalog` entirely (e.g. `sonnet`, `opus`) | Override applies unconditionally — absence is not itself suspicious | N/A |
| ALL_CANDIDATES_UNAVAILABLE | Every declared stage candidate fails `availability_fn` | `resolve_stage_candidate` returns `None`; stage falls through, no override written | N/A |

</frozen-after-approval>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py` —
  `resolve_stage_candidate`: removed the "never block, fall back to first declared
  candidate" tail; returns `None` when nothing passes `availability_fn`. No other change
  here — the `_available` closure inside `resolve_tier_launch` was tried-and-reverted
  (see Design Notes) since `harness_preference` for this fleet is `("cursor",)` alone,
  making `preference[0]` useless as a "real default adapter" reference point.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py` — new
  `provider_declaring_model(catalog, model) -> str | None`: reverse lookup over the
  declared catalog (which provider, if any, names this exact model).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` —
  `render_policy_toml`'s `if stage_models:` block: after `doc["adapter"]["name"]` is
  fully resolved (explicit `adapter` arg, tier-resolved, harness_preference-derived, or
  template baseline — all prior logic unchanged), each stage's model is checked via
  `provider_declaring_model` against `adapter_provider(str(doc["adapter"]["name"]))`
  before being written; a mismatch skips that stage's override.
- 8× `_bmad-output/projects/<station>/planning-artifacts/marshal-policy.toml` (marshal,
  herald, doctor, scribe, atlas, mason, warden, steward) — `model_tier_map.{heavy,
  medium,easy}.{dev,review}` values reverted `composer-2.5`/`composer-2.5-fast` →
  `opus`/`sonnet`, with a dated rationale comment above `[model_tier_map.heavy]`. Only
  `pyforge-marshal`'s file also declares a `model_cost_catalog` block (7 others don't) —
  restored its `[model_cost_catalog.providers.cursor.models."composer-2.5[-fast]"]`
  table headers after an in-flight `sed` mistakenly renamed them too (see Implementation
  Notes) — those pricing entries are untouched data, not part of this fix's scope.

## Tasks & Acceptance

**Execution:**
- [x] `core/tier_routing.py` — `resolve_stage_candidate` returns `None` instead of a
  fabricated fallback — closes the path that let an unverified candidate reach launch.
- [x] `core/model_cost.py` — add `provider_declaring_model` reverse-lookup helper.
- [x] `adapters/harness_bmadloop.py` — `render_policy_toml` skips a stage override whose
  model's catalogued provider mismatches the resolved `[adapter].name`.
- [x] 8× `marshal-policy.toml` — revert `model_tier_map` dev/review values to the plain
  baseline (sonnet/opus) fleet-wide; restore the one file's cost-catalog headers touched
  by mistake.
- [x] `tests/unit/test_tier_routing.py` — 2 new tests: `resolve_stage_candidate` returns
  `None` for dev and for review when nothing is available.
- [x] `tests/unit/test_harness_policy_render.py` — 2 new tests: a cross-provider stage
  model is skipped; a same-provider stage model still applies.
- [x] `tests/unit/test_dispatch_retry.py` / `tests/unit/test_spin.py` — updated 2
  pre-existing tests that hard-asserted `composer-2.5-fast`/`composer-2.5` as the
  "working" tier-map values; they now assert `sonnet`/`opus`, with a dated note
  explaining the revert.
- [x] `cli/dispatch.py` — the SAME provider-mismatch guard for the `dispatch` engine,
  applied once the live binary+authcheck walk's real `resolution.profile` is known; a
  mismatch drops the model override (new `MRS-DISP-043`, WARN) rather than launch a
  live-verified harness with a model it was never meant to receive.
- [x] `core/findings.py` / `core/verdict.py` — register `MRS-DISP-043` (WARN).
- [x] `tests/unit/test_findings.py` — add `MRS-DISP-043` to the registered-codes fixture.
- [x] `tests/unit/test_dispatch.py` — new
  `test_dispatch_drops_a_tier_mapped_model_catalogued_under_a_different_provider`.

**Acceptance Criteria:**
- Given `model_tier_map.heavy` declares `dev = "composer-2.5-fast"` with no explicit
  harness, when `render_policy_toml(effective, difficulty="heavy")` runs against this
  fleet's real `harness_preference` (`cursor`-only, no bmad-loop counterpart), then no
  `[adapter.dev]` table is written and `doc["adapter"]["model"]` stays the template
  baseline (`sonnet`) — reproduced via direct execution against the live
  `pyforge-marshal` policy both before (bug present) and after (fixed) the change.
- Given a `model_tier_map` stage candidate whose model IS catalogued under the same
  provider as the resolved adapter, when rendered, then the override still applies
  unchanged.
- Given all 8 stations' `marshal-policy.toml`, when parsed, then `model_tier_map`'s
  dev/review values equal the plain `[adapter]`/`[adapter.review]` baseline
  (`sonnet`/`opus`) for every difficulty tier.

## Implementation Notes

- First attempt at the resolver fix added the provider cross-check inside
  `resolve_tier_launch`'s `_available` closure, comparing against
  `_provider_for_harness(preference[0])`. Direct re-execution of the exact bug-finding
  probe showed **no change** — root cause: `policy.harness_preference.value ==
  ("cursor",)` for this fleet (confirmed via `_compose_spin_policy`), a single-entry
  tuple with no bmad-loop counterpart at all, so `preference[0]` IS "cursor" itself —
  comparing the Cursor model against "cursor"'s own provider always matches, catching
  nothing. `EffectivePolicy` has no field exposing `[adapter].name`/`.model` (17 STATIC
  fields, none of them adapter-shaped) — the REAL fallback to `claude` happens entirely
  inside `render_policy_toml` via the parsed `_POLICY_TEMPLATE`. Reverted the
  `tier_routing.py` closure change; moved the check to `render_policy_toml`, the one
  place that actually knows the FINAL resolved adapter name (`doc["adapter"]["name"]`,
  read AFTER all of Story 22.8's own resolution logic already ran).
- Applying `sed 's/"composer-2\.5"/"opus"/g'` fleet-wide accidentally renamed
  `pyforge-marshal`'s `[model_cost_catalog.providers.cursor.models."composer-2.5[-fast]"]`
  **table headers** too (a `"composer-2.5"` string match with no context awareness that
  it was a key, not a tier-map value) — caught by grepping for the catalog section
  immediately after, reverted with two targeted, unambiguous table-header-only `sed`
  substitutions, re-verified clean.
- **Closed same day, on operator request.** `marshal factory dispatch`'s own
  `resolve_dispatch_model_with_retry_escalation` reads
  `resolve_tier_launch(...).resolved_models["dev"]` directly and did NOT go through
  `render_policy_toml`'s guard — `cli/dispatch.py`'s surrounding harness-walk already
  does a LIVE binary+authcheck preflight per candidate (Story 22.8, hardened 2026-08-27
  after real cursor-auth-wall incidents), but that walk determines the REAL harness
  (`resolution.profile`) only AFTER the model was already resolved, so the model and the
  live-verified harness could still diverge. Added the same `provider_declaring_model`
  cross-check right after `data["harness_profile"] = resolution.profile` (the dispatch
  engine's own "real, final adapter" moment, the counterpart to
  `render_policy_toml`'s `doc["adapter"]["name"]`): a mismatch drops `data["model"]` to
  `None` (and clears any `escalated`/`from_model`/`to_model`/`resolved_models["dev"]`
  the mismatch produced), letting the harness's own default apply, and records
  `MRS-DISP-043` (WARN — registered in `core/findings.py` + `core/verdict.py`) so the
  correction is never silent. New regression test:
  `test_dispatch_drops_a_tier_mapped_model_catalogued_under_a_different_provider` in
  `tests/unit/test_dispatch.py`. Both engines (`spin` and `dispatch`) now carry the
  identical guarantee.

## Spec Change Log

## Review Triage Log

## Design Notes

The two rejected/reverted design paths, for the next person who reaches for them:
1. **Inferring "the default provider" from `harness_preference[0]`** — wrong whenever
   `harness_preference` itself has no bmad-loop counterpart (this fleet's actual state).
2. **A full model-registry / per-adapter allowlist** — the generically "complete"
   solution, but explicitly out of scope (Constraint: never touch `model_cost_catalog`'s
   pricing shape) and unnecessary: the EXISTING declared cost catalog already records
   "which provider claims this model" for every model anyone bothered to catalog for
   pricing purposes, which is precisely the set of models a tier-map author would ever
   plausibly cross-reference. Reusing it for a safety cross-check (not a live dispatch
   gate, not a pricing decision) stays inside its documented "advisory" role.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_tier_routing.py src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py -q` — expected: all passed (77 passed)
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py::test_dispatch_drops_a_tier_mapped_model_catalogued_under_a_different_provider -v` — expected: PASSED
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green (7920 passed, 1 skipped, 12 deselected)
- Direct re-execution of the original bug-finding probe (`resolve_tier_launch(policy, "heavy")` + `render_policy_toml(...)` against the live `pyforge-marshal` policy for heavy/medium/easy) — expected: no `[adapter.dev]`/`[adapter.review]` override differing from the template baseline; confirmed.
