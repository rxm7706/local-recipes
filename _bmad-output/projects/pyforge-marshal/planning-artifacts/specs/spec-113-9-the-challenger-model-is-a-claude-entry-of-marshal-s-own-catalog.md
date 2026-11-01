---
title: "113.9: the challenger model is a Claude entry of marshal's own catalog"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
---

<intent-contract>

## Intent

**Problem:** the challenger's model rule fails outside marshal and lets non-Claude ids through. Line numbers are at
`03a7aff5d9`.

- `_cataloged_models` and `render_refusals`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:172-200`) accept any provider's
  `model_cost_catalog` id, read from the `--project` station's own policy. Only marshal's policy declares a catalog, and
  an empty catalog refuses, so the other seven stations cannot pass the render (EGM audit MAR-M-Z3).
- The challenger always runs on the packaged claude profile, which passes the id verbatim to `claude --model`; a Gemini
  or OpenAI catalog id passes the render and fails at spawn, and no alias (`sonnet`, `opus`, `haiku`, `default`) is
  normalised (MAR-M-D5).
- "The dispatching session's own model" is defined only in code: `session_models`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:152-164`) reads `model_tier_map` and never
  the `[adapter]` and `[adapter.review]` models (MAR-D-C3).
- The `[challenge]` comment example in `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:1014`
  names `claude-fable-5-1`, marshal's frontier dev and review model (`:1058-1059`), so the render refuses its own
  documented example.

**Approach:**
- **One catalog, Claude only (operator ruling 2026-11-01).** The challenger reads marshal's own `model_cost_catalog`
  (from `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`'s composed policy) for every
  `--project`, and `render_refusals` accepts only an id for which `provider_declaring_model(catalog, model)`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py:95`) is `anthropic`, reusing the
  `MRS-DISP-043` precedent. Any other id refuses with the usage code and a reason naming the provider.
- **Aliases.** The id is checked against the claude profile's `[model_list]` aliases
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml:70-76`) and normalised
  before the same-model check, so an alias of a station model is the station model.
- **Session models.** `session_models` adds the station's `[adapter]` and `[adapter.review]` models to its
  `model_tier_map` models. The dispatch readiness hook compares against the run's resolved launch model, which
  `cli/dispatch.py` passes to `readiness_for_dispatch`.
- **The documented example.** The `marshal-policy.toml` comment names `sonnet-5` (an Anthropic catalog entry)
  (amended 2026-11-01: `claude-fable-5-1`, per AC4's amendment). The file
  stays without a `[challenge]` block. It is a governed path: reconcile it on the memlog of every Spec
  `spec-surface-check` names, then stamp each scoped.
- **The contract follows the code.** The memlog events for MAR-M-Z3, MAR-M-D5 and MAR-D-C3 and the operator's decision
  are already on `spec-pyforge-marshal` (commit `7dde4a0202`). Re-derive CAP-299 with `bmad-spec`: the challenger is
  Claude-only on the packaged claude profile (memlog deviation 3), reviewers inherit its `--model`, "session model"
  means the station's `model_tier_map` plus its adapter models, and the repo default never carries `[challenge]`. Then
  the cascade re-stamp and the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the block is read only while
  `pyforge.marshal.egm_policy_block` is on.

Ledger key: `113-9-the-challenger-model-is-a-claude-entry-of-marshal-s-own-catalog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the `[challenge]` block; `model` names a catalog entry and never the
  station's own model.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL5; findings MAR-M-Z3, MAR-M-D5, MAR-D-C3); the operator's ruling of 2026-11-01 on the catalog.

## Acceptance Criteria

- **AC1 — Claude only.** A `[challenge].model` naming a Gemini, OpenAI or Cursor catalog id, or an id absent from
  marshal's catalog, refuses at render with the usage code and a reason; an Anthropic catalog id renders
  (`src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py`).
- **AC2 — Every station.** A `--project` other than `pyforge-marshal` whose own policy declares no catalog renders with
  an Anthropic id from marshal's catalog (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC3 — Never the station's model.** The station's own frontier model, an `[adapter]` or `[adapter.review]` model, and
  an alias that normalises to any of them each refuse; in a dispatch, the run's resolved launch model refuses.
- **AC4 — The example.** The `marshal-policy.toml` comment example names `sonnet-5`, the file carries no `[challenge]`
  block, and `_bmad-output/policy-defaults.toml` carries none. (amended 2026-11-01: session-owner ruling on the Ask-first
  question, under the operator's ruling that the challenger reads marshal's catalog filtered to Anthropic entries and
  is never a station's own model. The example names `claude-fable-5-1`, not `sonnet-5`, which normalises to every
  station's `[adapter].model` `sonnet`. The comment says that a station whose own dev or review model is that entry
  (marshal itself, frontier tier) must name another Anthropic catalog entry. Against the live policies the example
  renders on another station and refuses on marshal with a reason naming the frontier model; that refusal is the
  design working and stays. No catalog entry or price is added
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).)
- **AC5 — The contract.** CAP-299 is re-derived by `bmad-spec` (both self-validate passes logged);
  `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC6 — Mutation.** Dropping the provider filter fails AC1's Gemini case; dropping the adapter models from
  `session_models` fails AC3's. Restore each.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Reuse `provider_declaring_model`; never parse the catalog a second way.
- Keep the challenger on the packaged claude profile.

**Ask first:**
- If alias normalisation makes `sonnet-5` collide with a station's adapter model, which Anthropic catalog entry the
  example names instead. (answered 2026-11-01: `claude-fable-5-1`; see AC4's amendment.)

**Never:**
- Never ship a `[challenge]` block in the repo default or in `marshal-policy.toml`; never fall back to the author's
  model; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL5).
- Epic: Epic 113.
- Ledger key: `113-9-the-challenger-model-is-a-claude-entry-of-marshal-s-own-catalog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, their tests,
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` (comment only) and the re-derived
  `SPEC.md`; within `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: in-review (2026-11-01). The code meets AC1, AC2, AC3, AC4 (as amended 2026-11-01), AC6 and AC7. AC5 belongs
to the session owner's re-derive phase (`bmad-spec`, the cascade re-stamp and the scoped stamp).

**The ruling (2026-11-01).** The session owner answered the Ask-first question below with option 2, under the
operator's ruling that the challenger reads marshal's catalog filtered to Anthropic entries and is never a station's own
model. The refusal on marshal is the design working and stays. AC4's example is `claude-fable-5-1`, and the
`marshal-policy.toml` comment now says that a station whose own dev or review model is that entry (marshal itself,
frontier tier) must name another Anthropic catalog entry. No catalog entry or price is added. The `[challenge]` shape
stays a comment.

**The question (Ask first, triggered; answered above).** With alias normalisation, `sonnet-5` is the same model as
`[adapter].model = "sonnet"`. That `[adapter]` model is the bmad-loop template baseline, so every station renders it.
The documented example therefore refuses on all eight stations. Checked against the real policies:
`model_refusals` with `model = "sonnet-5"` returns "is the dispatching session's own model (sonnet)" for
`pyforge-marshal` and for `pyforge-atlas`. Marshal's catalog has one other Anthropic entry, `claude-fable-5-1`. That is
marshal's `frontier` dev and review model, so it refuses on marshal and renders on the other seven stations. As the
catalog stands, no Anthropic entry renders on marshal. Which Anthropic catalog entry should the example name? Options:

1. Add a new Anthropic catalog entry, with its prices, from a family no station runs (for example a Haiku model), and
   name it in the example.
2. Name `claude-fable-5-1`. It renders on seven stations and refuses on marshal, the file the comment sits in.
3. Narrow the alias rule so a bare `[adapter]` alias does not claim its family's catalog id. `sonnet-5` would then
   render, but a challenger on Sonnet 5 could review work authored by `sonnet`, which is the same model.

Before the ruling `marshal-policy.toml` was unchanged: its comment already named `claude-fable-5-1`. It carries no
`[challenge]` block, and neither does `_bmad-output/policy-defaults.toml`.

**Close-out after the ruling (2026-11-01):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`: the commented `[challenge]` shape keeps
  `model = "claude-fable-5-1"`. Its trailing comment now reads: an anthropic entry of marshal's `model_cost_catalog`,
  read for every station, and never the station's own dev or review model. A station whose own dev or review model is
  that entry (marshal itself, frontier tier) must name another Anthropic catalog entry. The file still declares no
  `[challenge]` table.
- `tests/unit/test_factory_challenge.py`: `test_the_documented_example_renders_off_marshal_and_refuses_on_marshal`
  reads the example's `model` out of the live `marshal-policy.toml` comment and asserts it is `claude-fable-5-1`. It
  checks that neither that file nor the repo default declares `[challenge]`. Against the live composed policies, it
  checks that the example renders on `pyforge-atlas` (no refusals) and that marshal's `frontier` dev and review model is
  the example. It also checks that marshal refuses with exactly one reason:
  `[challenge].model 'claude-fable-5-1' is the dispatching session's own model (claude-fable-5-1)`.
- A live check across all eight stations (`model_refusals` over `compose_effective(long_form(s))`) showed the example
  renders on herald, atlas, warden, mason, doctor, scribe and steward and refuses on marshal only.
- Memlog (`spec-pyforge-marshal/.memlog.md`): one decision entry (the AC4 ruling), one surface-reconcile event naming
  every governed path 113.9 changed, and one event with CAP-299's new model rule.

**What changed** (in the shared landing worktree, not committed):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`: `_cataloged_models` is removed.
  `render_refusals` reads `provider_declaring_model` (reused from `core/model_cost.py`; `MRS-DISP-043` precedent) and
  accepts only `CHALLENGER_PROVIDER` (`ADAPTER_TO_PROVIDER["claude"]`, `anthropic`). An id from another provider
  refuses with a reason naming that provider, and an absent id refuses as before. New `alias_of` and `same_model`
  normalise an alias (the claude profile's `[model_list]` aliases) to its family before the same-model check. The new
  `aliases` keyword defaults to `()`. The same-model reason now names the matching station model.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`: `challenger_catalog` reads marshal's own
  `model_cost_catalog` (`CATALOG_PROJECT = "pyforge-marshal"`, via `compose_effective`) for every `--project`.
  `challenger_aliases` reads the packaged claude profile's `[model_list].aliases`. `adapter_models` reads the
  `[adapter]` and `[adapter.<stage>]` models from `render_policy_toml(effective)`; a policy bmad-loop refuses at load
  names none. `session_models` adds those models and an optional `launch_model`. `model_refusals` is the one call both
  `_run` and `readiness_for_dispatch` make. `readiness_for_dispatch` takes `launch_model`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`: `_readiness_challenge_before_launch`
  takes `launch_model` and passes it through. `dispatch_once` passes the run's resolved launch `model`, after any
  `MRS-DISP-043` drop.
- Tests: `tests/unit/test_challenge_core.py` covers AC1 (Gemini, OpenAI and Cursor entries refuse and name their
  provider; absent ids and aliases refuse; Anthropic entries render), the alias rule (eight pairs) and an alias of a
  station model. `tests/unit/test_factory_challenge.py` covers AC1 through the verb (usage code, no spawn), AC2 (atlas,
  no catalog of its own, renders `claude-fable-5-1` from marshal's catalog), AC3 (the frontier model, `sonnet-5` against
  `[adapter]`, `opus-5` against `[adapter.review]`, with `haiku-5` as the passing control), `session_models` and the
  dispatch hook refusing the launch model. `_effective` gained `catalog`, `tiers` and `slug` keywords, and `_hook` gained
  `launch_model`. `tests/unit/test_dispatch.py` checks that `dispatch_once` hands the hook its resolved launch model.

**Commands** (run from the worktree root; each exit code was read from `$?`):
- `pixi run --frozen -e pyforge-marshal python -m pytest .../test_challenge_core.py .../test_factory_challenge.py
  .../test_dispatch.py::test_dispatch_hands_the_readiness_hook_its_resolved_launch_model`: exit 0, 105 passed.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0. Unit: 13619 passed, 15 skipped. The second
  leg: 34 passed, 4 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`: exit 0, but vacuous. It diffs committed
  `HEAD` against `origin/main` and saw no touched module because nothing is committed. In the unit coverage report
  (`.steward/coverage/marshal-unit.json`), the touched modules sit above the 80% floor: `cli/challenge.py` 84.4%,
  `cli/dispatch.py` 85.7%, `core/challenge.py` 95.0%.
- `ruff check` and `ruff format --check` on the six touched files, run from the package dir with the guild env's ruff
  (the way `scripts/lint_types.py` runs them): exit 0 and exit 0.
- `mypy -p pyforge.marshal`, run from the package dir with the `lint_types` cache dir (guild env): exit 0, no issues in
  217 source files.
- AC6 mutation checks ran on scratch copies of the package placed first on `PYTHONPATH`; the shared tree was never
  mutated. With the provider filter dropped, 6 of the 7 selected tests fail, including AC1's Gemini case (exit 1).
  With the adapter models dropped from `session_models`, AC3's `sonnet-5` and `opus-5` cases and the `session_models`
  test fail (exit 1). The code is unchanged after both checks.

**Commands after the ruling** (2026-11-01, worktree root, each exit code read from `$?`):
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`:
  exit 0, 125 passed.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0. Unit: 13667 passed, 15 skipped. The second leg:
  34 passed, 4 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`: exit 0, still vacuous (nothing committed). The
  unit report has `cli/challenge.py` at 88.2%, `cli/dispatch.py` at 85.7% and `core/challenge.py` at 95.6%.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0. The package-dir `ruff check` and `ruff format --check` on the
  six touched files both exit 0, and `mypy -p pyforge.marshal` exits 0 with no issues in 217 source files.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0, after the memlog surface-reconcile event and before
  any stamp.

**Left to the session owner (AC5).** The `bmad-spec` re-derive of CAP-299 from the 113.9 behaviour event, the cascade
re-stamp and the scoped stamp, then `chain-currency-sweep-check` and `chain-completeness-check`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL5: MAR-M-Z3, MAR-M-D5,
  MAR-D-C3) and the operator's ruling of 2026-11-01 (marshal's own `model_cost_catalog` for every `--project`, filtered
  to Anthropic entries; implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.
- 2026-11-01: implementation blocked on the Ask-first boundary. Alias normalisation makes `sonnet-5` the same model as
  every station's `[adapter].model` (`sonnet`), so the example needs the operator's choice of Anthropic entry
  (§ Auto Run Result).
- 2026-11-01: AC4 amended by the session owner's ruling under the operator's catalog ruling. The example is
  `claude-fable-5-1`, which renders off marshal and refuses on marshal, its frontier model. The comment tells marshal to
  name another Anthropic catalog entry, and no catalog entry is added. A live-policy test pins the example. The memlog
  carries the decision, the surface reconcile and the CAP-299 event. The blocked state is cleared and the status set to
  `in-review`.

## Review Triage Log

- 2026-11-01 (independent reviewer): **pass**, status set to `done`. Read against the ACs and Boundaries,
  not the Auto Run Result. Every exit code below was read from `$?`, from the worktree root.
  - Diff read (`git diff HEAD`): `core/challenge.py` drops `_cataloged_models`. `render_refusals` calls
    `provider_declaring_model` and accepts only `CHALLENGER_PROVIDER` (`ADAPTER_TO_PROVIDER["claude"]`). `alias_of`
    and `same_model` normalise the claude profile's aliases. `cli/challenge.py` has `challenger_catalog`
    (marshal's catalog for every `--project`), `challenger_aliases` (the packaged claude profile's `[model_list]`),
    `adapter_models` (rendered `[adapter]` and `[adapter.<stage>]` models), `session_models(launch_model=)` and the one
    `model_refusals` that `_run` and `readiness_for_dispatch` both call. `dispatch_once` passes `model` to the hook
    after the `MRS-DISP-043` drop. The `marshal-policy.toml` change is comment-only.
  - AC1: met. `test_challenge_core.py` covers Gemini, OpenAI and Cursor ids (each reason names its provider), an
    absent id, a bare alias and the Anthropic entries. `test_factory_challenge.py` covers the verb path (usage code,
    no spawn).
  - AC2: met. `test_another_station_reads_marshal_s_catalog`. A live check of `model_refusals` across all eight
    stations: `claude-fable-5-1` renders on the seven non-marshal stations, whose own policies declare no catalog.
  - AC3: met. The frontier model, `sonnet-5` against `[adapter]` `sonnet`, `opus-5` against `[adapter.review]`
    `opus` and the dispatch launch model each refuse. `haiku-5` is the passing control.
    `test_dispatch_hands_the_readiness_hook_its_resolved_launch_model` covers the dispatch hand-off.
  - AC4 (as amended): met. The comment example is `claude-fable-5-1` with the marshal caveat. `grep` finds no
    `[challenge]` table in `marshal-policy.toml` or `_bmad-output/policy-defaults.toml` (exit 1). The live test and
    the live check agree: the example refuses only on marshal, with the frontier-model reason.
  - AC5: deferred-to-render (the `bmad-spec` re-derive of CAP-299, the cascade re-stamp and the scoped stamp). Before
    any stamp, `pixi run --frozen -e pyforge-guild spec-surface-check` exits 0. Its only output is a warn about
    `spec-pyforge-unifying-strategy`, which is not this story's.
  - AC6: met, re-run by me on scratch copies of the package placed first on `PYTHONPATH`. The shared tree was never
    mutated.
    - Provider filter dropped: exit 1. Six tests fail, including both Gemini cases.
    - Adapter models dropped from `session_models`: exit 1. The `sonnet-5` and `opus-5` AC3 cases and the
      `session_models` test fail.
    - Extra checks: passing `launch_model=None` from `dispatch_once` fails the dispatch hand-off test. Reading the
      station's own catalog fails AC2 and the AC4 live test.
  - AC7: met. `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exits 0: 13667 passed and 15 skipped, then
    34 passed and 4 skipped. The focused run of the two story test files plus the dispatch test exits 0 (126 passed).
  - Gates:
    - `pyforge-marshal-coverage-gate` exits 0, but the result is vacuous because nothing is committed. In the unit
      report, `cli/challenge.py` is at 88.2%, `cli/dispatch.py` at 85.7% and `core/challenge.py` at 95.6%.
    - The package-dir `ruff check` and `ruff format --check` on the six touched files exit 0.
    - `scripts/lint_types.py ruff`, `ruff-format` and `mypy` each exit 0.
  - Boundaries: `provider_declaring_model` is reused, and the catalog is not parsed a second way. The challenger stays
    on the packaged claude profile. No `[challenge]` block ships. There is no author-model fallback: an empty `model`
    refuses at render. No flag was added, and no `SPEC.md` was touched.
  - Failures: none.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`) and the rendered `SPEC.md` against this spec, not against the Auto Run Result. **Verdict:
  pass**; status stays `done`.
  - AC1 holds. `render_refusals` calls `provider_declaring_model` and accepts only `CHALLENGER_PROVIDER`
    (`anthropic`). Another provider's id refuses with a reason naming the provider, and an absent id refuses.
  - AC2 holds. `challenger_catalog` reads marshal's composed catalog for every `--project`, and
    `test_another_station_reads_marshal_s_catalog` passes.
  - AC3 holds. `session_models` adds `adapter_models` and the dispatch `launch_model`. `same_model` normalises the
    claude profile's aliases. `dispatch_once` passes the resolved `model` to the hook.
  - AC4 (as amended) holds. The `marshal-policy.toml` comment example is `claude-fable-5-1` with the marshal caveat.
    `grep -nE '^\[challenge'` over `marshal-policy.toml` and `_bmad-output/policy-defaults.toml` exits 1 (no table).
  - AC5 holds. This AC was deferred to the render at the first review; it is re-checked here.
    - CAP-299 success: `model` names an `anthropic` entry of marshal's own `model_cost_catalog`, read for every
      `--project`, because the challenger always runs on the packaged `claude` profile.
    - The render refuses with the usage code an id another provider declares (the reason names it), an id no entry
      declares, and an id that, aliases normalised through the `claude` profile's `[model_list]`, is a station
      session model: `model_tier_map`, `[adapter]`, `[adapter.review]`, and the dispatch launch model.
    - Neither the repo default nor `marshal-policy.toml` ships a block. The comment's example is stated with its
      marshal refusal.
    - CAP-298 states that the reviewers run on `model: inherit`, so on the session's `--model`, "the challenger
      model of CAP-299".
    - This matches `render_refusals`, `challenger_catalog`, `challenger_aliases`, `adapter_models`, `session_models`
      and `model_refusals`.
    - The memlog carries the Story 113.9 behaviour event, the session-owner AC4 decision, the CAP-299
      `(capability)` entry and the Story 113.7 re-derive decision through Story 113.9. CAP-299's definition line
      names Story 113.9. The self-validate pair is logged, and pass 2 names MAR-M-Z3, MAR-M-D5 and MAR-D-C3.
  - AC6 holds, re-observed:
    - Provider filter dropped: exit 1, 6 failed (the Gemini, OpenAI and Cursor cases in both test files).
    - Adapter models dropped: exit 1, 3 failed (`sonnet-5`, `opus-5` and
      `test_session_models_carry_the_adapter_models_and_the_launch_model`).
  - AC7 holds. The suite exits 0.
  - Not blocking: the same comment block still says "absent means off, exactly as [context]". That is the analogy
    MAR-M-Z3 called false and CAP-299 no longer makes. Drop the clause the next time the comment is touched.
  - Shared evidence (one run covers Stories 113.8-113.13 on committed `HEAD` f742908321; every verdict read from `$?`,
    from the worktree root):
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13667 passed, 15 skipped; 34 passed,
      4 skipped).
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exit 0. The change is committed now, so the
      gate judged `origin/main..HEAD`: "coverage gate OK for pyforge-marshal unit: 8 module(s) ≥ 80%".
    - `chain-completeness-check` 0, `spec-surface-check` 0 (its only warnings are steward's
      `spec-pyforge-unifying-strategy`), `fr-without-cap-check` 0, `deferred-work-check` 0, `dream-chain-check` 0,
      `dreams-hygiene-check` 0, `scripts/chain_currency_sweep_check.py --project pyforge-marshal` 0 (marshal
      `current`).
    - `ad-citation-check` exit 1, on one NEW cap-citation issue outside these six stories:
      `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md:586` (added in
      f742908321 by herald's glossary decision) cites bare `CAP-299`. Qualify it as `spec-pyforge-marshal:CAP-299`
      before the landing PR is pushed. No marshal file is named.
    - The contract, `spec-pyforge-marshal/SPEC.md` (the working tree equals `HEAD`):
      - 303 CAP definitions at `origin/main` and at `HEAD`, with an identical id-and-title list; 1388 lines in both.
        No CAP id changed.
      - The intent and success lines of CAP-298..CAP-303 equal the memlog's six `(capability) ... (amended
        2026-11-01 ...)` entries byte for byte.
      - Each story's `(decision) Re-derive 2026-11-01 (marshal Story 113.n ...)` entry and behaviour event are on the
        memlog. Each changed definition line's provenance names the story.
      - One self-validate pair is logged after the final render: `Self-validate pass 1 (coherence) 2026-11-01, EGM
        audit re-derive` and `Self-validate pass 2 (preservation)`. Pass 1 judges all six CAPs, the four EGM
        Constraints and the EGM Assumption. Pass 2 names the Story 113.8, 113.10, 113.11, 113.12 and 113.13
        re-derives as kept verbatim, and the Story 113.9 findings as landed. The per-story pass texts drafted in the
        fix rounds were not appended separately; this one pair stands for them.
      - The 22 tests the CAP success lines name each exist exactly once in pyforge-marshal's `tests/unit`.
    - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`; the import path was
      confirmed. The unmutated scratch baseline (`test_challenge_core.py`, `test_factory_challenge.py`,
      `test_challenge_harness.py`) exits 0 (158 passed). Each mutant was restored, and `git status` shows the live
      package untouched.
