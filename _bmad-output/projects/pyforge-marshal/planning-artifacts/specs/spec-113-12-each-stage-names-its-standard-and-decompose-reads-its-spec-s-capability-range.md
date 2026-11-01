---
title: "113.12: each stage names its standard, and decompose reads its Spec's capability range"
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
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - .claude/skills/bmad-spec/assets/spec-template.md
  - .claude/skills/bmad-build-auto/spec-template.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
---

<intent-contract>

## Intent

**Problem:** the goldfish context rule never separates target from context, decompose never sees the Spec it
decomposes, and the reviewer roster, stage groups and standards exist only in code. Line numbers are at `03a7aff5d9`.

- `default_standards` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:249-254`) gives mint,
  decompose and rules only `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`. A decompose reviewer reads
  `epics.md`, the station Dream, `CHAIN-STANDARD.md` and a glossary when one exists, never the `SPEC.md` whose CAP range
  the stories claim (EGM audit MAR-E2). Mint never receives the `bmad-spec` template, though CAP-299 names "the
  five-field shape" (MAR-M-C2, MAR-D-R1).
- The code already exempts the target from the context rule (`context_violations`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:238-255`), gives the repo-rules targets
  `AGENTS.md` and `CHAIN-STANDARD.md` the Dream `docs/dreams/one-chain-per-station.md` plus marshal's glossary, gives a
  station `SKILL.md` its whole station Dream (`cli/challenge.py:268-270`, `:486-495`), and omits a missing
  `glossary.md` (six of eight stations have none). CAP-299 still says "exactly four paths" and "never `AGENTS.md`", and
  no memlog line records the exemption (MAR-M-Z2, MAR-D-R4).
- dcc71b22c0 settled the per-stage reviewer groups (`DEFAULT_REVIEWERS`, `core/challenge.py:36-42`), never spawns
  `egm:egm-synthesizer` (absent from `REVIEWER_PERSONAS`, `:29-31`; the orchestrator session assembles `report.json`)
  and chose the default standards. CAP-298 and CAP-299 still name the synthesizer, "as the stage selects" and an unnamed
  "five-field shape" (cluster MAR-CL1: MAR-M-Z1, MAR-D-C2, MAR-D-R1, MAR-M-C2). The Epic 113 story text is corrected by
  append-only notes at mint (Stories 113.1 and 113.2); the code, re-derive and Dream steps of MAR-CL1 ride this story.

**Approach:**
- **The standards.** `default_standards("decompose")` returns `CHAIN-STANDARD.md` and the station `SPEC.md`
  (`spec_path(root, slug)`); `default_standards("mint")` adds `.claude/skills/bmad-spec/assets/spec-template.md` (the
  five-field shape), for mint only and never for decompose. Readiness keeps
  `.claude/skills/bmad-build-auto/spec-template.md`, drift the station `SPEC.md`, rules `CHAIN-STANDARD.md`.
- **The contract follows the code.** The memlog events for every finding above are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`). Re-derive CAP-298, CAP-299 and CAP-301 with `bmad-spec` (`BMAD_ACTIVE_PROJECT=pyforge-marshal`,
  `PYTHONPATH=$PWD/_bmad/scripts`):
  - CAP-298 lists five reviewer agents and no synthesizer, and names the orchestrator session as the report assembler.
  - CAP-299 gets a five-stage table (reviewers, standards) that cites `DEFAULT_REVIEWERS` and `default_standards` as
    fallbacks a `[challenge]` block overrides, reconciled with its intent "nothing about the challenger lives in code";
    the context rule binds context and never the target; a repo-rules target takes `docs/dreams/one-chain-per-station.md`
    plus marshal's glossary, and a station `SKILL.md` target its whole station Dream; the glossary is "`glossary.md` when
    present"; `--target` is optional with `--epic` and `--audit`.
  - CAP-301's drift success form gains `--project`, which `_bmad/custom/bmad-retrospective.toml` already passes.
- **The Dream.** `docs/dreams/pyforge-marshal.md` § *Realization log* gains dated lines: the synthesizer was dropped and
  the orchestrator took its role (beside the 2026-11-01 audit entry; the operator's table at `:13766` untouched), and
  the goldfish-context bullet (`:13780-13785`) as built, the bullet's own text left as written.
- Then the cascade re-stamp (`updated:` on `prds/prd-pyforge-marshal-2026-07-25/prd.md`,
  `architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md` and `epics.md`), `git add`, and
  `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-marshal` (plus each
  co-governor the detector names).
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the verb stays behind `pyforge.marshal.egm_challenge`.

Ledger key: `113-12-each-stage-names-its-standard-and-decompose-reads-its-spec-s-capability-range`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the block, its stage groups, standards and the goldfish context rule.
- **CAP-298** (FR-240) and **CAP-301** (FR-243): re-derived text only (the roster; the drift success form).
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL2: MAR-M-Z2, MAR-D-R4, MAR-E2; cluster MAR-CL1: MAR-M-Z1, MAR-D-C2, MAR-D-R1, MAR-M-C2; MAR-E2 and
  MAR-M-Z2 contested and settled in the cluster).

## Acceptance Criteria

- **AC1 — Decompose reads its Spec.** `default_standards(root, slug, "decompose")` returns `CHAIN-STANDARD.md` and
  `spec_path(root, slug)`, and a decompose run's context carries the station `SPEC.md`
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — Mint reads the template.** `default_standards(root, slug, "mint")` returns `CHAIN-STANDARD.md` and
  `.claude/skills/bmad-spec/assets/spec-template.md`; decompose never carries the template.
- **AC3 — The other stages are unchanged.** Readiness, drift and rules return what they return today; one test pins all
  five stages.
- **AC4 — The contract.** CAP-298, CAP-299 and CAP-301 read as the Approach states, re-derived by `bmad-spec` (both
  self-validate passes logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC5 — The Dream.** The Realization log carries the two dated lines; no existing Dream bullet or table changes;
  `dream-chain-check` and `dreams-hygiene-check` exit 0.
- **AC6 — Mutation.** Dropping `spec_path` from decompose's standards fails AC1's test. Restore it.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Keep `DEFAULT_REVIEWERS` and `default_standards` as fallbacks a `[challenge]` block overrides.

**Ask first:**
- Any change to a stage's reviewer group, or passing the whole `SPEC.md` where a CAP-range slice would do (the selector
  is Story 113.14's).

**Never:**
- Never pass `AGENTS.md`, `CLAUDE.md`, a memlog or session text as context; never hand-edit `SPEC.md`; never rewrite a
  Dream bullet.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL2,
  MAR-CL1).
- Epic: Epic 113.
- Ledger key: `113-12-each-stage-names-its-standard-and-decompose-reads-its-spec-s-capability-range`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`, the re-derived `SPEC.md` and
  `docs/dreams/pyforge-marshal.md` (Realization log lines only); within `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-guild dream-chain-check` and `pixi run --frozen -e pyforge-guild dreams-hygiene-check` — expected: exit 0.

## Auto Run Result

Status: in-review (2026-11-01). The code meets AC1, AC2, AC3, AC5, AC6 and AC7. AC4 belongs to the re-derive phase:
the `bmad-spec` re-derive of CAP-298, CAP-299 and CAP-301, the cascade re-stamp and the scoped stamp are the session
owner's. The memlog events the re-derive reads are on `spec-pyforge-marshal` (from commit `7dde4a0202`, plus the two
this story appended).

**What changed.**

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`: new
  `SPEC_TEMPLATE_RELPATH = ".claude/skills/bmad-spec/assets/spec-template.md"` (the five-field shape).
  `default_standards` now gives each stage its own standard:
  - mint: `CHAIN-STANDARD.md` and the bmad-spec template (mint only);
  - decompose: `CHAIN-STANDARD.md` and `spec_path(root, slug)`, the station `SPEC.md`;
  - readiness, drift and rules: unchanged.
  It is still the fallback that a `[challenge]` `standards` entry overrides in `build_context`. The whole `SPEC.md` is
  passed because no CAP-range slicer exists; that selector is Story 113.14's.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`: the `render_prompt` docstring said
  "the four context paths". It now says "the target and its context paths". This is a docstring change only; the
  prompt text is unchanged.
- `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`:
  - the `repo` fixture writes the bmad-spec template, since a missing standard refuses the run;
  - `test_each_stage_names_its_own_default_standard` pins all five stages (AC1-AC3);
  - `test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template` checks a decompose run's prompt: the
    station `SPEC.md` is under `standard(s)` and the template is absent. A mint run's standards carry the template
    (AC1, AC2);
  - `test_a_challenge_block_standard_overrides_the_default` checks the fallback Boundary.
  - `test_a_partly_errored_audit_is_unevaluable` (Story 113.8) used to fail atlas's session by matching its
    `SPEC.md` path. That path is now also decompose's standard, so the test matches atlas's `epics.md` (the decompose
    target alone) and expects the one `pyforge-atlas decompose` error. Its intent is unchanged.
- `docs/dreams/pyforge-marshal.md`: two dated Realization-log lines were appended after the 2026-11-01 audit entry:
  "(the synthesizer)" and "(goldfish context as built)". No existing bullet or table changed (AC5).
- Memlog: `spec-pyforge-marshal` gains two events: the surface reconcile naming the four paths, and the new
  CAP-299 stage-standard behaviour for the re-derive.

**Commands run (exit codes read from `$?`).**

- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`
  exited 0 (62 passed).
- AC6 mutation: `default_standards("decompose")` was edited to drop `spec_path`. The `-k "standard or decompose"` slice
  then exited 1, failing `test_each_stage_names_its_own_default_standard` and
  `test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template`. The file was restored from a scratch copy
  and the restore confirmed with `grep`.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exited 0 (13656 passed, 15 skipped; then 34 passed,
  4 skipped).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exited 0. It judged no module, because the change
  is uncommitted and the gate diffs `origin/main..HEAD`. The suite's coverage JSON reads `cli/challenge.py` at 85.0%
  and `core/challenge.py` at 95.1%, both above the 80% floor.
- `ruff check` and `ruff format --check` over the three changed Python files both exited 0. They used
  pyforge-guild's ruff, run from both the repo root and the package directory.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.marshal`, run from the package directory, exited 0 (217
  files). This is marshal's slice of `lint-types`; the full `lint-types` was not run.
- `pixi run --frozen -e pyforge-guild dream-chain-check` exited 0; `pixi run --frozen -e pyforge-guild
  dreams-hygiene-check` exited 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` exited 0 before any stamp, because the memlog moved. The
  scoped stamp is still the session owner's after the re-derive.

### Fix round 1 — 2026-11-01

Status: blocked. AC4 is closed except for the `SPEC.md` render and the two self-validate passes that follow it. The
same holds for Stories 113.8, 113.10 and 113.11. Earlier in this session the auto-mode classifier refused the
script-render route (`[Auto-Mode Bypass]`, Story 113.8's fix), and this round's brief forbids a `SPEC.md` write, so
this round did not attempt it. The route needs the operator's go-ahead (the PR #1605 precedent). No code changed in
this round.

- **AC4, the re-derive (`bmad-spec`, headless).**
  - The memlog decision is on `spec-pyforge-marshal/.memlog.md`: `(decision) Re-derive 2026-11-01 (marshal Story
    113.12; EGM audit MAR-M-Z2, MAR-D-R4, MAR-E2 of cluster MAR-CL2 and MAR-D-R1, MAR-M-C2 of cluster MAR-CL1)`. It
    reads the Story 113.12 behaviour event and the Dream's two 2026-11-01 realization lines.
  - CAP-298 needs no further render. After `render_113_11.py` it lists the five reviewer agents and never
    `egm:egm-synthesizer`, and it names the one orchestrating session as the report's assembler. `render_113_12.py`
    refuses to run unless that text is present.
  - CAP-299 success:
    - the goldfish context rule binds the context and never the target;
    - the context is the run station Spec's `glossary.md` when present and the `--project` station's whole Dream.
      In the `--audit` sweep, a repo-rules target takes `docs/dreams/one-chain-per-station.md` with marshal's
      glossary, and a station skill takes its whole station Dream. This answers the review's non-blocking note on
      the ad hoc `rules` case;
    - a five-stage table gives each stage's reviewers and standard. `DEFAULT_REVIEWERS` and `default_standards` are
      named as fallbacks that a block entry overrides, which keeps the intent "nothing about the challenger lives in
      code";
    - `--target` is optional, and unread, with `--epic` and `--audit`.
  - CAP-301 success: the drift form is `marshal factory challenge --project <station> --stage drift --epic <n>`.
  - The kernel holds the table as one inline clause, so each capability field stays one line.
  - The anchor-asserting render script is
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/render_113_12.py`.
    It takes the `SPEC.md` path as its argument, and `--dry-run` checks without writing. It changes 5 lines: the
    frontmatter `updated:` note, the CAP-299 definition and success lines, and the CAP-301 definition and success
    lines.
  - The script asserts:
    - every needle occurs once, and the undo returns the original byte for byte;
    - the CAP definition count (303) and the line count (1388) are unchanged;
    - no stale clause remains (the cited Dream entry, the unnamed five-field shape, the `--project`-less drift form,
      the synthesizer in the roster).
  - It must run **after** `render_113_8.py`, `render_113_10.py` and `render_113_11.py`. It overlaps none of their
    needles.
  - On scratch copies in
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/r11312/`:
    - the chain 8 → 10 → 11 reproduces 113.11's `chain.md` byte for byte;
    - this script's dry run, then its write, exit 0;
    - a second run exits 1, and a run on the unrendered `SPEC.md` exits 1, both as expected;
    - the live `SPEC.md` is untouched (`cmp`).
  - **Not done:** writing `SPEC.md` and logging the two self-validate passes.
- **AC4, the cascade.**
  - PRD (`prds/prd-pyforge-marshal-2026-07-25/prd.md`): the FR-241 body says the context rule never binds the target,
    names the glossary when present and the Dream the target takes, and names the code defaults as fallbacks. The
    FR-243 body names `--project`. § 51 is added with the five-stage table, and the `updated:` note is prefixed. No
    FR is added or renumbered, and no arrow moves.
  - Spine: § *Currency reconciliation — 2026-11-01 (Story 113.12)* records readings on AD-4, AD-10/AD-50 and AD-19,
    and the `updated:` note is prefixed. No AD is added, amended or removed.
  - `epics.md`: the `updated:` note is prefixed; no epic or story moves.
  - None of the three is on marshal's spec surface (`spec-surface-check` 0), so no surface-reconcile event is needed.
- **Dream.** The review's non-blocking note was that the "goldfish context as built" line made the repo-rules Dream
  look universal. That line, written by this story, now says the repo-rules Dream applies in the `--audit` sweep and
  that an ad hoc run takes its `--project` station's Dream. `docs/dreams/pyforge-marshal.md` is already named in this
  story's surface reconcile. No existing bullet or table changed.
- Commands, exit codes read from `$?`:
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 0 (13666 passed, 15 skipped; 34 passed, 4 skipped).
  - `pixi run --frozen -e pyforge-marshal python -m pytest
    src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`: 0 (72 passed).
  - `pyforge-marshal-coverage-gate`: 0. It judged no module, because the change is uncommitted.
  - `lint-types`: 1. Its only non-ok leg is pyforge-doctor's ruff import order in
    `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file. pyforge-marshal is ok.
    `lint_types.py mypy`: 0, with pyforge-marshal ok.
  - `spec-surface-check`: 0. Its one warning is steward's `spec-pyforge-unifying-strategy`.
  - `dream-chain-check` 0, `dreams-hygiene-check` 0, `chain-completeness-check` 0, `fr-without-cap-check` 0,
    `ad-citation-check` 0, `deferred-work-check` 0.
  - `chain_currency_sweep_check.py --json --project pyforge-marshal`: 0, so marshal is current. The repo-wide
    `chain-currency-sweep-check` exits 1 on the seven other stations' staleness checkpoints, which are other agents'
    work; it reads marshal as `current`.
- **To unblock (session owner, under the operator-approved render route):**
  1. Run `render_113_8.py`, then `render_113_10.py`, then `render_113_11.py`, then `render_113_12.py`, on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md`.
  2. Append the two self-validate events with `uv run _bmad/scripts/memlog.py append --workspace
     _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal --type event --text "…"`:
     - Pass 1 (coherence): "bmad-spec self-validate 2026-11-01, Pass 1 (coherence) on the Story 113.12 re-derive of
       CAP-299 and CAP-301: PASS. Both capabilities keep their id, title, intent and provenance, extended with the
       findings. CAP-299's success stays testable against the shipped tree: test_each_stage_names_its_own_default_standard
       pins the standards, DEFAULT_REVIEWERS states the reviewer groups, test_a_challenge_block_standard_overrides_the_default
       pins the fallback, and context_violations holds the target-versus-context rule. Its intent 'nothing about the
       challenger lives in code' holds, because the code carries only fallbacks a block overrides. CAP-301's success
       names the --project form that bmad-retrospective.toml passes. CAP-298 already reads as built after the Story
       113.11 render. No CAP minted (303 definitions), no Constraint moved. SPEC.md script-rendered by
       render_113_12.py (needles asserted once, undo byte-equal, 5 lines changed, 1388 lines)."
     - Pass 2 (preservation): "bmad-spec self-validate 2026-11-01, Pass 2 (preservation) on the Story 113.12
       re-derive: PASS. Every load-bearing claim of the Story 113.12 behaviour event and of the Dream's 2026-11-01
       (the synthesizer) and (goldfish context as built) lines landed in SPEC.md: the context rule binds the context
       and never the target; glossary.md when present; the Dream each target takes; the five stages' reviewer groups
       and standards as overridable fallbacks; --target optional with --epic and --audit; the drift form with
       --project. The Story 113.8, 113.10 and 113.11 renders' text is kept. Wrapper-only content dropped: the story
       spec's line numbers and its ledger key."
  3. `git add`, then run the scoped stamp `--spec pyforge-marshal/spec-pyforge-marshal`.
  4. Return this story to `in-review`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL2: MAR-M-Z2, MAR-D-R4,
  MAR-E2; with the code, re-derive and Dream steps of cluster MAR-CL1) at the operator's ruling of 2026-11-01 (implement
  in the Story 113.7 landing PR). The Story 113.1 and 113.2 text is corrected by append-only notes at mint. `type: fix`,
  no flag, no CAP.

## Review Triage Log

- 2026-11-01 — reviewer: independent session. I did not write this code. I judged `git diff HEAD` of the story's
  files against this spec, not against the Auto Run Result. **Verdict: fail**; status is back to `in-progress`.
  - Read:
    - `cli/challenge.py`: `SPEC_TEMPLATE_RELPATH` and `default_standards`, and `build_context`, where a `[challenge]`
      `standards` entry still wins.
    - `core/challenge.py`: the `render_prompt` docstring.
    - The tests, the two Dream lines, and the existence of both template files.
  - AC1 holds. Decompose returns `CHAIN-STANDARD.md` and `spec_path(root, slug)`, and a decompose run's prompt lists
    the station `SPEC.md` under its standards.
  - AC2 holds. Mint returns `CHAIN-STANDARD.md` and `.claude/skills/bmad-spec/assets/spec-template.md`; decompose's
    prompt never carries the template.
  - AC3 holds. `test_each_stage_names_its_own_default_standard` pins all five stages, and readiness, drift and rules
    are unchanged.
  - AC5 holds. The diff to `docs/dreams/pyforge-marshal.md` is only the two appended Realization-log lines, after the
    2026-11-01 audit entry, and no existing bullet or table moved. `dream-chain-check` and `dreams-hygiene-check` exit 0.
  - AC6 holds, re-observed. With `spec_path` dropped from decompose, the run exits 1;
    `test_each_stage_names_its_own_default_standard` and
    `test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template` failed.
  - AC7 holds. The suite is green (see the shared evidence).
  - The Boundaries hold: the defaults stay fallbacks (`test_a_challenge_block_standard_overrides_the_default`), and no
    reviewer group changed. The whole `SPEC.md` is what AC1 prescribes, since no slicer exists before Story 113.14.
  - Shared evidence (one run covers all five Epic 113 fix stories; every verdict read from `$?`):
    `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13666 passed, 15 skipped; 34 passed,
    4 skipped). The challenge, harness, status, watch and dispatch unit files exit 0 (730 passed). ruff check and
    ruff format --check over the 14 changed marshal files (package config, package cwd) exit 0 and 0.
    `lint_types.py ruff-format` exit 0 and `lint_types.py mypy` exit 0, with marshal ok in both. `lint-types` exit 1;
    its only finding is pyforge-doctor's `tests/unit/test_sources_pages_liveness.py` import order, which is another
    station's in-flight file. `pyforge-marshal-coverage-gate` exit 0 but judged nothing, because the change is
    uncommitted. `coverage_gates_ci.py --paths-file` over the 8 touched marshal `src` modules (`--suites unit`) exit 0,
    with every module at or above 80%. `spec-surface-check` 0, `chain-completeness-check` 0, `deferred-work-check` 0,
    `dream-chain-check` 0, `dreams-hygiene-check` 0, `fr-without-cap-check` 0. `chain-currency-sweep-check` exit 1:
    a staleness checkpoint fails on all eight stations, marshal included. `spec-pyforge-marshal/SPEC.md` and the
    marshal PRD have no diff against HEAD. The memlog's newest self-validate entries are the 2026-11-01 amendment's
    pass 1 and pass 2, which predate these stories' events.
  - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`. The import path was
    confirmed and the unmutated scratch baseline exits 0 (157 passed). Each mutant was restored from the live file,
    and the live tree was never touched.
  - A guard plugin on `PosixProcess.run` covered the whole unit and meta suite: no challenge test reached a real
    `claude --version`. The only hits were the pre-existing `test_harness_bmadloop_probe.py` cases, which stub
    `subprocess.run`.
  - Failures:
    1. AC4 is not met. CAP-298, CAP-299 and CAP-301 are not re-derived: `SPEC.md` has no diff, CAP-298 still lists
       `egm:egm-synthesizer`, no self-validate pass is logged for this story, and `chain-currency-sweep-check` exits 1.
       No code change is needed. A re-derive with both passes logged, then marshal's cascade re-stamp, closes it;
       return the story to `in-review` after that.
  - Not blocking: the goldfish-context Dream line says a repo-rules target takes
    `docs/dreams/one-chain-per-station.md`. That is true for `--audit`. An ad hoc `--stage rules --target AGENTS.md`
    gets the `--project` station's Dream (`build_context` falls back to `dream_path`). The CAP-299 re-derive should
    word that precisely.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`), the rendered `SPEC.md` and the Dream against this spec, not against the Auto Run Result or
  the fix rounds. **Verdict: pass**; status set to `done`.
  - AC1 holds. Decompose returns `CHAIN-STANDARD.md` and `spec_path(root, slug)`.
    `test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template` passes.
  - AC2 holds. Mint returns `CHAIN-STANDARD.md` and `.claude/skills/bmad-spec/assets/spec-template.md`, and
    decompose never carries the template.
  - AC3 holds. `test_each_stage_names_its_own_default_standard` pins all five stages.
  - AC4 holds (this review's re-check of the first review's failure):
    - CAP-298 lists the five reviewer agents, never `egm:egm-synthesizer`, and names the one orchestrating session as
      the report's assembler.
    - CAP-299:
      - its stage table matches `DEFAULT_REVIEWERS` and `default_standards` entry for entry, and names both as
        fallbacks a block's `reviewers` or `standards` entry overrides;
      - the goldfish context rule binds the context and never the target;
      - in the `--audit` sweep a repo-rules target takes `docs/dreams/one-chain-per-station.md` with marshal's
        glossary, and a station skill takes its whole station Dream; an ad hoc run takes its `--project` station's
        Dream, which answers the first review's note;
      - the glossary is `glossary.md` when present;
      - `--target` is optional, and unread, with `--epic` and `--audit`.
      This matches `audit_plan`, `build_context` and `_run`.
    - CAP-301's drift form names `--project`.
    - The memlog carries the Story 113.12 behaviour event and its `(decision) Re-derive 2026-11-01 (marshal Story
      113.12 ...)`. The CAP-299 and CAP-301 definition lines name Story 113.12. The self-validate pair is logged.
      `spec-surface-check` 0, `chain-completeness-check` 0, chain-currency for marshal 0.
  - AC5 holds. The Dream's diff against `origin/main` adds lines only (0 removed), including the two dated
    realization lines. `dream-chain-check` 0, `dreams-hygiene-check` 0.
  - AC6 holds, re-observed. With `spec_path` dropped from decompose, the run exits 1;
    `test_each_stage_names_its_own_default_standard` and
    `test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template` failed.
  - AC7 holds. The suite exits 0.
  - Not blocking, but fix before landing: CAP-299's aside "six of eight stations having none" is stale on this
    branch. Commit f742908321 adds `glossary.md` to atlas, doctor, herald, steward and warden, so only scribe's Spec
    lacks one. The behaviour ("when present") is stated correctly. Correct the count with a memlog decision and a
    re-derive. The Dream line carries the same count but is dated as built, so it may stand.
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
