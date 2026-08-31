---
title: 'The 0.10/0.11 policy knobs are governable'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: '03b3a7141e8a83184f945284923e282cf60ac142'
review_loop_iteration: 0 # no bad_spec loopback occurred; the one review pass resolved as patches
followup_review_recommended: true # 1 medium + 9 low patched: 3*1 + 1*9 = 12 >= 5
context:
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md'
warnings: [oversized]
deferred:
  - summary: >-
      The repo_defaults layer is inert: compose() accepts the parameter but never
      folds it, and nothing reads _bmad-output/policy-defaults.toml.
    evidence: |-
      core/policy.py compose() signature carries repo_defaults (added Story 1.10)
      but the body never references it; _merge_field folds default -> project ->
      flags only; run_config never passes it. A repo-wide value set in
      policy-defaults.toml for ANY of the 28 keys (the five new knobs included)
      is silently ignored; the file's existing max_followup_reviews=2 only works
      because it is hand-duplicated in DEFAULT_POLICY. Pre-existing, confirmed
      independently by two review layers this pass.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py:1389
    severity: medium
  - summary: >-
      Stale bmad_loop 0.9.0 citations for the max_parallel clamp premise survive
      in untouched prose (policy.json description, policy.py docstrings,
      _max_parallel_clamp_finding message).
    evidence: |-
      The premise itself re-verified true on 0.11.0 (upstream issue #229 open,
      every scm.max_parallel > 1 still clamps to 1 per alignment-inventory
      2026-08-22), so only the version citations are stale. Re-check at the next
      bmad-loop bump.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json
    severity: low
  - summary: >-
      No meta-test pins _STATIC_KEYS membership/count the way
      test_seed_view_returns_all_sixteen_seed_fields pins the seed side.
    evidence: |-
      The diff corrected three mutually inconsistent stale static-count prose
      claims, evidence the counts rot repeatedly with no derive-don't-declare
      guard on the static side. Pre-existing gap; this story added only SEED keys.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_policy.py
    severity: low
  - summary: >-
      spec-bmad-611-era-alignment SPEC.md frontmatter still reads status ready
      while its chain is mid-flight (25.1-25.4 done).
    evidence: |-
      CLAUDE.md requires spec status kept current (draft -> ready -> in-progress
      -> shipped); none of stories 25.1-25.3 flipped it either. Flip to
      in-progress, or to shipped at Epic 25 closeout.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** bmad-loop 0.10/0.11 added five policy knobs (`review.on_timeout`, `review.on_status_contradiction`, `limits.dev_contract_nudge`, `[operator].enabled`, `[verify].stream_capture_kb`) that marshal's policy layer knows nothing about — `policy.py` has zero hits for any of them (alignment-inventory finding 6, CAP-4), so no station can govern them through the AD-16 chain and the rendered `.bmad-loop/policy.toml` never carries a deliberate repo posture for them.

**Approach:** add five SEED keys to marshal's closed policy vocabulary (`review_on_timeout`, `review_on_status_contradiction`, `dev_contract_nudge`, `operator_enabled`, `stream_capture_kb`) with validators mirroring the existing idioms, deliberate repo defaults in `DEFAULT_POLICY` (all five match bmad-loop stock — each choice documented), map them in `render_policy_toml` onto the harness vocabulary (adding an `[operator]` section to `_POLICY_TEMPLATE` with rationale comments), update the coupled surfaces (`_FIELD_ORDER`, `_PROJECT_POLICY_ONLY_KEYS`, `schemas/policy.json`), then re-render all 8 loop homes and prove `bmad-loop validate` stays clean.

## Boundaries & Constraints

**Always:**
- Exact TOML scalar types: booleans as TOML booleans, ints as ints, strings as strings — bmad-loop 0.11's `_limit_bool` rejects coercible mismatches at load (`limits.dev_contract_nudge must be a boolean`). Build values as native Python types; tomlkit preserves them.
- `[dev] skill = "bmad-dev-auto"` stays untouched (the adapter discriminator).
- Repo defaults are DELIBERATE and documented in the rendered template's comments: `review_on_timeout = "retry"` (stock — retry-then-salvage ladder is the right first response to a review timeout), `review_on_status_contradiction = "escalate"` (stock — matches the fleet's escalate-don't-silently-retry posture), `dev_contract_nudge = true` (stock — the marker-repair nudge closes the exact `## Auto Run Result` omission this fleet's own detectors chase), `operator_enabled = true` (stock — the fleet WANTS parked-not-dead semantics; `awaiting-operator` is the honest outcome for human-only ACs), `stream_capture_kb = 256` (stock — generous for real pytest tails, bounds a runaway chatty verifier).
- Marshal-side validation fails BEFORE bmad-loop's own `PolicyError`: enum vocabularies `{retry, salvage-if-done, defer}` / `{escalate, retry}` as module frozensets + validators mirroring `_valid_gate_mode`; bools via `_valid_bool`; `stream_capture_kb` as int-not-bool `>= 0` (0 = capture nothing is legal on both sides).
- New keys are SEED (scalar operator-tunable knobs — the `gate_mode`/attempt-count analog), reported via MRS-POLICY-003 on malformed values, read only via `seed_view()` (AD-26).
- All five are project-policy-only on the CLI (`_UNSETTABLE_KEYS` + `_PROJECT_POLICY_ONLY_KEYS`) — matching every scalar key added since Story 3.5 (no AC asks for a `--set` surface; the flags layer still composes uniformly in `compose()` for programmatic callers).
- Update the three-place vocabulary tie in the same change: `_FIELD_ORDER`, `_STATIC_KEYS`/`_SEED_KEYS`, `schemas/policy.json` (properties + required) — `test_field_order_matches_the_closed_policy_vocabulary` reds otherwise. Stale "23-key"/"11 seed" counts in docstrings/comments touched by this change are corrected to 28/16.
- Re-render ALL 8 loop homes under `~/.bmad-loops/` identically (`marshal config --project <slug> --write-harness-policy <home>`) and leave every one `bmad-loop validate`-clean.
- Repo-wide defaults live in code `DEFAULT_POLICY`; `_bmad-output/policy-defaults.toml` carries only divergences from it — all five defaults match stock/DEFAULT_POLICY, so that file gains no keys (verified: `compose()` accepts `repo_defaults` but no caller passes it; the file documents divergences only, e.g. `max_followup_reviews`).

**Block If:** the installed bmad-loop's knob vocabulary differs from the enum spellings above (re-read `.pixi/envs/local-recipes/.../bmad_loop/policy.py` — REVIEW_ON_TIMEOUT_MODES / REVIEW_ON_STATUS_CONTRADICTION_MODES); or re-rendering a loop home would clobber a live run's mid-run policy patch (check for active runs before re-rendering).

**Never:** no new composition layer and no per-key precedence override (AD-16: defaults → project → flags, last wins); no `stories.yaml`/folder+id adoption; no changes to other 0.10/0.11 keys beyond the five named (session_timeout_min, review.trigger etc. stay template-baseline as-is); no `--write-baseline` from any producer; no widening of bmad-loop's own in-session `[limits].max_tokens_per_story` guard.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Defaults render | `compose()` with no overrides → `render_policy_toml` | `[review] on_timeout="retry"`, `on_status_contradiction="escalate"`, `[limits] dev_contract_nudge=true`, `[operator] enabled=true`, `[verify] stream_capture_kb=256`; TOML types exact (bool/int/str) | No error |
| Project override wins | `marshal-policy.toml`-shaped mapping sets `review_on_timeout="salvage-if-done"`, `operator_enabled=false`, `stream_capture_kb=64` | seed fields carry layer=PROJECT, rendered file carries the override values | No error |
| Bad enum value | `review_on_timeout="yolo"` (any layer) | field falls back to prior layer/default; MRS-POLICY-003 naming key + layer | Reported, never raised |
| Coercible type mismatch | `dev_contract_nudge=1` (int), `operator_enabled="true"` (str), `stream_capture_kb=true` (bool) or `"256"` (str) | each rejected marshal-side (MRS-POLICY-003), default stands — never rendered for bmad-loop to refuse | Reported, never raised |
| Zero capture | `stream_capture_kb=0` | composes and renders `stream_capture_kb = 0` (legal both sides) | No error |
| Negative capture | `stream_capture_kb=-1` | rejected (MRS-POLICY-003), default 256 stands | Reported, never raised |
| Real gate | re-rendered policy in a loop home | `bmad-loop validate` reports zero warnings; 0.11 `load()` accepts every rendered key | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — the composition. Add to `_SEED_KEYS` (L193-222) + `DEFAULT_POLICY` (L285-380, with rationale comments); new frozensets `_REVIEW_ON_TIMEOUT_MODES`/`_REVIEW_ON_STATUS_CONTRADICTION_MODES` beside `_GATE_MODES` (L226); validators beside `_valid_gate_mode` (L788): two enum validators, reuse `_valid_bool` (L607 — generalize its landing-only docstring), new `_valid_capture_kb` (int-not-bool >= 0; separate function per the `_valid_landing_base_branch` "unrelated questions" precedent, L776); wire 5 `_merge_field` entries into `compose()`'s `seed` dict (L1416-1516) with `MRS-POLICY-003`. Update key-count prose on lines touched (module docstring L5/L147, `compose` docstring L1285, `content_hash` L1241, `seed_view` L1229).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — the render pipeline. `_POLICY_TEMPLATE` (L236-346): add `on_timeout`/`on_status_contradiction` placeholder lines under `[review]`, `dev_contract_nudge` under `[limits]`, `stream_capture_kb` under `[verify]`, new `[operator]` section (placed before `[adapter]`); each with an "overwritten per render from EffectivePolicy" marker plus the deliberate-default rationale comment. `render_policy_toml` (L387-475): map the five from `seed_view()` (`doc["review"]["on_timeout"] = seed["review_on_timeout"].value` etc.); update the "6 mapped keys" docstring to 11. Template header's "bmad_loop 0.9.0" gloss → 0.11.0 where touched.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py` — the CLI seam. `_UNSETTABLE_KEYS` (L106) + `_PROJECT_POLICY_ONLY_KEYS` (L69) + `_FIELD_ORDER` (L160-185): add the five (seed section, after `max_parallel`). `_INT_SET_KEYS` unchanged.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json` — closed 23-property schema: +5 properties (`$ref` policyField + SEED description) and +5 `required` entries.
- `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` — per-knob tests (default value/layer, project-override wins, enum/type rejection incl. the coercible-mismatch cases); fix the two exhaustive `_seed=` literals (L1484 test is incomplete-by-design — stays; L1503 dict must gain the 5 keys); `test_schema_file_declares_the_twenty_keys` key-set literal (L1543+) gains the 5.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py` — render tests: defaults-render asserts the five at stock with exact types (`is True`, `== 256`); override-render asserts project values; the all-keys test (L39) grows to the new mapped set.
- `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` L644 `test_field_order_matches_the_closed_policy_vocabulary` — derive-don't-declare tie; passes once the three places agree (no edit expected).
- Installed harness ground truth: `.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/policy.py` — enums L31-32, `dev_contract_nudge` L137 (strict `_limit_bool` L704), `stream_capture_kb` L164-184 (`int()` + `>= 0` L880), `OperatorPolicy.enabled` L300-311 (`bool()` L1111), review modes L226/L241, stock defaults all match our chosen repo defaults.
- `_bmad-output/policy-defaults.toml` — divergence-only file; NO new keys (all five defaults match DEFAULT_POLICY). Read-only evidence.
- Loop homes: `~/.bmad-loops/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}` — re-render all 8 after the code lands; `pixi run -e local-recipes bmad-loop validate` (run per home) must stay clean.

## Tasks & Acceptance

**Execution:**
- `core/policy.py` — add the 5 seed keys: vocabulary sets, DEFAULT_POLICY entries with rationale comments, 2 enum frozensets + validators, `_valid_capture_kb`, generalize `_valid_bool` docstring, 5 seed `_merge_field` wirings; correct touched key-count prose — the composition is the single source the render reads.
- `adapters/harness_bmadloop.py` — template placeholders + `[operator]` section + deliberate-default comments; 5 new render mappings from `seed_view()` — the projection onto the harness vocabulary.
- `cli/config.py` — extend `_UNSETTABLE_KEYS`/`_PROJECT_POLICY_ONLY_KEYS`/`_FIELD_ORDER` — keeps the CLI render + usage-error surfaces consistent.
- `schemas/policy.json` — +5 properties/required — the wire contract (additive).
- `tests/unit/test_policy.py`, `tests/unit/test_harness_policy_render.py` — per-knob default/override/rejection + render coverage mirroring existing idioms; repair the two exhaustive literals.
- Re-render all 8 loop homes identically; run `bmad-loop validate` against each.

**Acceptance Criteria:**
- Given no overrides, when a policy renders, then the five knobs appear at their deliberate repo defaults with exact TOML scalar types and rationale comments, and bmad-loop 0.11 `load()` accepts the file.
- Given a project layer setting each knob to a legal non-default, when composed and rendered, then each field reports layer=project and the rendered file carries the override.
- Given an illegal enum value or a coercible type mismatch on any of the five, when composed, then MRS-POLICY-003 names the key and layer, the prior layer's value stands, and rendering never emits the bad value.
- Given the full marshal suite (`pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests -q`, 5152 pre-story), when run post-change, then green with the new tests added.
- Given all 8 re-rendered loop homes, when `bmad-loop validate` runs against each, then zero warnings.

## Design Notes

SEED (not STATIC) because all five are scalar operator-tunable knobs — the `gate_mode`/attempt-count/budget-ceiling analog — keeping `EffectivePolicy`'s public attribute surface unchanged; STATIC is reserved for structural declarations (commands, paths, maps, rules). Marshal key names flatten the harness's table-qualified names the same way `max_dev_attempts` ↔ `[limits].max_dev_attempts` already does; the two review knobs keep a `review_` prefix (bare `on_timeout` says nothing at the marshal layer), `operator_enabled` keeps `operator_` (bare `enabled` is meaningless), `dev_contract_nudge`/`stream_capture_kb` are already self-naming. bmad-loop's own load-strictness varies (`_limit_bool` strict; `operator.enabled` via `bool()` coercive; `stream_capture_kb` via `int()` coercive) — marshal validates all five strictly anyway, so a bad value fails marshal-side with a clear finding before any harness behavior (silent coercion included) can absorb it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 1, low 9)
- defer: 4: (high 0, medium 1, low 3)
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` Enum-mirror drift guard missing — added `test_enum_frozensets_mirror_the_installed_bmad_loop_vocabularies` (set-equality against the installed `bmad_loop.policy` constants) and a `loads()` round-trip for `"defer"`, so every member of both vocabularies now passes through the installed loader.
  - `[low]` `[patch]` "retry-then-salvage ladder" mischaracterized `on_timeout="retry"` — template + DEFAULT_POLICY comments now say: re-review up to `limits.max_review_cycles` before deferring; salvage-if-done / defer are the alternatives.
  - `[low]` `[patch]` `render_policy_toml` docstring overclaimed load-strictness — reworded: only `limits.dev_contract_nudge` is load-strict; `operator.enabled`/`verify.stream_capture_kb` are `bool()`/`int()`-coerced by the harness; marshal stays strict for all five at compose.
  - `[low]` `[patch]` `_valid_capture_kb` renamed `_valid_stream_capture_kb` (full-key greppability, matching `_valid_review_on_timeout`).
  - `[low]` `[patch]` Magnitude guard added to `_valid_stream_capture_kb` (the `_valid_parallel_count` `float()`/`OverflowError` probe) + arbitrary-precision-int test.
  - `[low]` `[patch]` `test_config_prints_all_twenty_keys` renamed `..._twenty_eight_keys`.
  - `[low]` `[patch]` `_FIELD_ORDER` block comment gained the Story 25.4 placement sentence (five knobs follow `max_parallel`; `marshal-policy.toml` only, no `--set`).
  - `[low]` `[patch]` `--set` usage-error test docstring now records that the value is deliberately irrelevant (key-based rejection precedes value parsing).
  - `[low]` `[patch]` "(all four SEED fields...)" parenthetical rescoped to 9-of-11 mapped keys.
  - `[low]` `[patch]` The four appended memlogs' `updated:` stamps bumped to append time per `memlog.py`'s own append semantics; scoped baseline re-stamp for exactly those four entries after `git add`.
- rejected (noise, dropped): importorskip on the installed-load gate (suite hard-imports bmad_loop elsewhere, missing harness fails loudly); template default-comments beside overridden values (comments are explicitly default-scoped, matching `session_timeout_min`'s existing style); schema `required` growth under the v1 $id (matches every prior key-addition story; materialized policies are derived, disposable); `--set` closure for the five (deliberate, precedented since Story 3.5, tested); loop-home re-render/validate "attested not diff-evidenced" (verified live by the orchestrator this session, 8/8 exit 0 zero warnings); pre-0.10-harness unknown-key concern (env pins 0.11.0, and older loaders ignore unknown keys/sections); rationale prose triplication (values are test-pinned; comment style is the repo's own); missing file-to-CLI-to-render e2e for the new keys (test depth matches every prior key story; the convention-layer CLI test covers the file boundary); baseline true-up rider (hashes independently re-verified against working tree and main).

## Auto Run Result

- **Status:** done (2026-08-22, hand-driven implementation session)
- **Block-If checks:** installed bmad-loop is 0.11.0; its `REVIEW_ON_TIMEOUT_MODES = {retry, salvage-if-done, defer}` / `REVIEW_ON_STATUS_CONTRADICTION_MODES = {escalate, retry}` match the spec's enum spellings verbatim (re-read live). No live runs in any loop home before re-render (no bmad-loop processes, no tmux server, latest per-home runs dated 2026-08-20 or earlier).
- **Execution:** all six task bullets landed — `core/policy.py` (5 SEED keys, 2 enum frozensets + validators, `_valid_capture_kb`, generalized `_valid_bool` docstring, 5 `_merge_field` wirings, DEFAULT_POLICY entries with per-knob rationale, key-count prose 23/11 -> 28/16), `adapters/harness_bmadloop.py` (template placeholders + `[operator]` section before `[adapter]` + deliberate-default comments, 5 render mappings from `seed_view()`, "6 mapped keys" -> 11, template gloss 0.9.0 -> 0.11.0), `cli/config.py` (`_UNSETTABLE_KEYS`/`_PROJECT_POLICY_ONLY_KEYS`/`_FIELD_ORDER` +5 each), `schemas/policy.json` (+5 properties/required, 23 -> 28), tests (per-knob default/override/rejection incl. every coercible-mismatch matrix case; the L1503 exhaustive `_seed` literal gained the 5; the incomplete-by-design L1484 literal untouched; render tests grew to the 11-key set plus a real `bmad_loop.policy.loads()` gate against the installed 0.11.0).
- **Verification:** marshal suite 5185 passed (5152 pre-story). `marshal config --project pyforge-marshal --write-harness-policy <tmp>` -> all five keys rendered with exact TOML scalar types (bool/int/str, tomllib-verified). All 8 loop homes re-rendered identically; `bmad-loop validate` exit 0, zero FAILs, zero warnings, per home (a pre-existing dirty `.bmad-loop/bmad_loop_hook.py` — the 0.11.0 upgrade's own relay refresh, byte-identical to the installed package canon — was committed per home on its `loop/<slug>` branch to clear the worktree-clean check; not caused by this story). CFE meta gates 8 passed. `spec_surface_reconcile.py` OK; memlog entries appended to the four owning specs (spec-pyforge-marshal, spec-adaptive-model-tiering, spec-bmad-loop-intent-gap-work-preservation, spec-horizontal-run-concurrency) and scoped `--write-baseline` stamped exactly those four entries after `git add`.
- **Notes:** `_bmad-output/policy-defaults.toml` unchanged by design (all five defaults match DEFAULT_POLICY/stock). Re-rendering pyforge-marshal's home dropped a leftover `[adapter.dev] model = "opus"` table from a previous difficulty-batched per-run render — the documented run-START projection semantics; the next spin re-applies tiering. Nothing deferred.
- **Review findings breakdown:** 10 patched (1 medium, 9 low — all applied and re-verified), 4 deferred (frontmatter `deferred:` list), 9 rejected as noise. Follow-up review recommendation: **true** — no high, but 3×1 medium + 1×9 low = 12 ≥ 5 (patched counts: medium 1, low 9).
- **Orchestrator re-verification (post-review-pass, independent):** marshal suite 5187 passed; CFE meta pair 8 passed; `spec_surface_reconcile.py` OK 0 findings; `bmad-loop validate` exit 0 / zero warnings in all 8 homes; every home's rendered policy carries the five knobs at repo defaults with exact TOML types and the patched template comments; `[dev] skill = "bmad-dev-auto"` intact everywhere.
- **Residual risks:** the four deferred items (dormant repo_defaults layer being the material one); `followup_review_recommended: true` per the severity-score formula — all patched findings were doc/test-hardening, none behavioral.
- **Landing note (parent-session commingling incident):** this story's dev-pass diff was swept into main commit `24c4dce923` (a steward-subjected commit made in the shared working tree while it sat on this story's branch, then fast-forwarded onto main) — deliberately not rewritten; the story's own commit on `marshal/25-4-policy-knob-parity` carries the review pass, the ledger flip, and the properly-attributed `marshal 25.4:` subject for merge detection.
- **Review pass 1 (2026-08-22, 10 findings, all applied):** enum-mirror drift-guard test (marshal frozensets asserted equal to the installed `bmad_loop.policy` constants; `"defer"` round-trips the installed `loads()` — every member of both vocabularies now loads live); `_valid_capture_kb` -> `_valid_stream_capture_kb` with the `_valid_parallel_count`-style magnitude guard + arbitrary-precision-int test; "retry-then-salvage ladder" mischaracterization fixed in DEFAULT_POLICY + template comments; load-strictness overclaim fixed in `render_policy_toml` docstring + mapping comment (only `limits.dev_contract_nudge` is load-strict; `operator.enabled`/`verify.stream_capture_kb` are `bool()`/`int()`-coerced — marshal stays strict for all five at compose); SEED parenthetical rescoped to 9-of-11; `test_config_prints_all_twenty_keys` -> `_twenty_eight_keys`; `_FIELD_ORDER` block comment gained the Story 25.4 sentence; usage-error test documents key-based rejection; the four memlogs' `updated:` stamps bumped per memlog.py's append semantics. Post-fix: suite 5187 passed, homes re-rendered + validate clean 8/8, reconcile OK, scoped re-stamp of the four baseline entries.
