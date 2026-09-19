---
title: '51.5: MRS-DISP-043 speaks for an uncatalogued model'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      The spin-engine sibling guard in `adapters/harness_bmadloop.py::render_policy_toml`
      was not widened alongside this story's dispatch-engine guard, so a genuinely
      foreign or mistyped tier-mapped model can still reach a live spin-engine launch
      unwarned.
    evidence: |-
      Both the Edge Case Hunter and the Verification Gap Reviewer independently
      flagged this in the 2026-09-19 review pass. Confirmed unchanged by this diff
      (not in Story 51.5's declared Surface: `cli/dispatch.py`,
      `core/model_cost.py::provider_declaring_model`, `core/findings.py` /
      `core/verdict.py`, tests). The gap is identical in shape to how the dispatch
      guard read before this story, so it pre-dates this change rather than being
      caused by it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py::render_policy_toml
    severity: medium
declared_low_risk: false
baseline_revision: '66463b49860151f0a7ff4d0756cf679be95fe3a0'
---

<intent-contract>

## Intent

**Problem:** the guard's condition (`model_provider is not None and model_provider != resolved_provider`) only fires when the model IS found under some OTHER provider, and `provider_declaring_model` returns `None` both for a foreign id and — by documented design — for `sonnet` / `opus` on claude

**Approach:** the predicate distinguishes "uncatalogued and not the chosen harness's own id" from "the harness's own default"

## Boundaries & Constraints

**Always:**
- a fixture tier map naming an id no provider declares raises MRS-DISP-043 before launch, `sonnet` on claude is byte-identical (no finding), and the cross-provider case is unchanged
- removing the uncatalogued branch silences the fixture (mutation test); no second gate

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-253`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the guard at the `provider_declaring_model` / `resolved_provider` comparison), `.../core/model_cost.py::provider_declaring_model` (or a sibling predicate that knows the harness's own default/alias set), `.../core/findings.py` / `.../core/verdict.py` only if the finding text changes, tests.
Ledger key: `51-5-mrs-disp-043-speaks-for-an-uncatalogued-model`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-5-mrs-disp-043-speaks-for-an-uncatalogued-model.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.5 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 13 findings — high 2, medium 2, low 8, false 1, maybe-false 0
- findings:
  - `[high]` `[patch]` Blind Hunter: the widened guard misfires on every station whose policy declares no `model_cost_catalog` at all (not just a catalog that omits the model), dropping a correctly tier-mapped, correctly resolved model — verified live against pyforge-atlas/-mason/-scribe/-warden's real `marshal-policy.toml` (all declare `harness_preference = ["cursor"]` + real cursor models in `model_tier_map`, none declares `model_cost_catalog`); `provider_declaring_model` returns `None` unconditionally when `catalog_declared(catalog)` is false. Fixed: `cli/dispatch.py`'s `model_uncatalogued` now also requires `catalog_declared(catalog)`; added regression test `test_dispatch_tier_mapped_model_with_no_declared_catalog_at_all_is_preserved` reproducing the exact atlas shape.
  - `[low]` `[patch]` Blind Hunter: CAP-253's own mint memlog entry (`spec-pyforge-marshal/.memlog.md:1398`) names only `sonnet`/`opus` as the exempt harness-default set; shipped code exempts `sonnet`/`opus`/`haiku` with no contract text updated to match — FR-205's actual normative text ("harness's own default/alias ids") is generic enough to already cover `haiku`, so this is real but cosmetic. Fixed as part of the docstring correction below (memlog itself is append-only/historical, not amended).
  - `[low]` `[patch]` Blind Hunter: `HARNESS_DEFAULT_MODEL_IDS`'s comment cites `provider_declaring_model`'s docstring as the source of the sonnet/opus/haiku set, but that docstring (until this pass) only named `sonnet`/`opus`. Fixed: `core/model_cost.py::provider_declaring_model` docstring now names all three, cross-referencing `HARNESS_DEFAULT_MODEL_IDS`.
  - `[low]` `[false]` Blind Hunter: `is_harness_default_model` is harness-agnostic (flat allowlist, no `resolution.profile` check) and could misclassify a future harness with a differently-scoped native default id. Every currently configured harness profile (`data/harness_profiles/*.toml`) either passes `sonnet`/`opus`/`haiku` through verbatim or maps them, so no live harness config reaches the described misclassification today; the fix (threading harness identity through the predicate) would add a parameter and branches for a situation the program cannot currently reach — rejected as speculative, not a demonstrated defect.
  - `[low]` `[patch]` Blind Hunter: no test exercises `haiku` specifically, the third `HARNESS_DEFAULT_MODEL_IDS` member — only `sonnet` was covered. Fixed: added `test_dispatch_tier_mapped_haiku_on_claude_is_byte_identical`, parallel to the existing sonnet test.
  - `[low]` `[patch]` Blind Hunter: the new no-provider test asserted only finding count/severity, never `.message`, and the WARN message text was identical for "no catalog at all" and "catalog declared but model missing" — ambiguous between two distinct root causes. Resolved as a side effect of the `catalog_declared` fix above (the branch now only fires for the latter case); tightened the message wording ("despite a declared cost catalog") and added `.message` content assertions to the existing test.
  - `[medium]` `[defer]` Edge Case Hunter: the sibling guard in `adapters/harness_bmadloop.py::render_policy_toml` (spin engine) was not widened alongside this story's dispatch-engine guard, so a genuinely foreign/mistyped model can still reach a live spin-engine launch unwarned. Confirmed unchanged by this diff and not in this story's declared Surface; the gap is identical in shape to how the dispatch guard read before Story 51.5, so it pre-dates this change rather than being caused by it — deferred, not patched.
  - `[high]` `[patch]` Verification Gap Reviewer: same root cause as the first Blind Hunter finding above — pre-verified via a live `dispatch_once` run against the atlas-shaped fixture (cursor harness + cursor model, no catalog), confirming the model override was dropped and a spurious MRS-DISP-043 WARN raised for a correctly configured dispatch. Same fix as above.
  - `[medium]` `[defer]` Verification Gap Reviewer (Other findings): same spin-engine gap as the Edge Case Hunter finding above — same route.
  - `[low]` `[reject]` Intent Alignment Auditor: intent's phrase "the harness's own default" is ambiguous between a harness-scoped reading (Reading B) and the harness-agnostic reading the diff implements (Reading A); no live harness profile makes the two readings diverge today — same reasoning and disposition as the `is_harness_default_model` finding above.
  - `[low]` `[patch]` Intent Alignment Auditor: the `haiku` addition is sourced from `claude.toml`'s own comment rather than from the Problem statement or `provider_declaring_model`'s (pre-fix) docstring, which named only sonnet/opus — same root cause as the docstring-staleness finding above, same fix.
  - `[low]` `[reject]` Intent Alignment Auditor: the spec's I/O & Edge-Case Matrix row is generic boilerplate ("the named fixture" / "the Then holds") rather than a concrete worked scenario. Pre-existing in `<intent-contract>` as minted, and any fix would mean editing this build's own spec's intent-contract — rejected per the rule against fixes that edit this build's spec.
  - `[false]` `[reject]` Intent Alignment Auditor: reported a `test_ZZZ_TEMP_repro_cursor_model_no_catalog` scratch function (print-only, no assertions) present in the working tree from a commit made during this review. Verified via `git log`: it was added in `30970024a0` and removed again in the very next checkpoint commit `179413598f`, before this triage began — `git grep` confirms it is absent from the current tree. Disproven; nothing to clean up.
