---
title: "113.13: resolve writes only marshal's Spec and prints the memlog command for any other"
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
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad/scripts/memlog.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
---

<intent-contract>

## Intent

**Problem:** `marshal factory challenge resolve` writes other stations' memlogs and takes the owner from the report.
Line numbers are at `03a7aff5d9`.

- `run_resolve` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:576-605`) appends one
  `memlog.py` event per accepted finding to whichever Spec the report's `spec_workspace` names (`with_provenance`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:429-446`). That breaks two absolute
  Constraints of the same Spec: Marshal "never edits another project's artifacts" (`SPEC.md:1154`) and "No Marshal code
  path writes into another station's artifacts" (`SPEC.md:1158`) (EGM audit MAR-M-Z5).
- `audit_plan` (`cli/challenge.py:484-498`) runs the `AGENTS.md` and `CHAIN-STANDARD.md` rules targets under
  `pyforge-marshal`, so their findings carry `spec-pyforge-marshal` as owner, and resolve would write them to the wrong
  memlog: `AGENTS.md` is governed by `spec-pyforge-scribe`, `CHAIN-STANDARD.md` by `spec-one-chain-per-station`
  (MAR-M-C5).
- CAP-303's intent names a story-spec-edit route (`SPEC.md:1138`) that no code or check carries.

**Approach (operator ruling 2026-11-01: resolve appends to marshal's Spec and prints the exact `memlog.py` command for
any other owning Spec):**
- **The owner, checked.** `resolve` derives the expected owning Spec from `--project` (or, for a rules target, from the
  per-target owner override below) and refuses with the usage code a report whose `spec_workspace` matches neither, so a
  report can never name its own write target.
- **Marshal writes only marshal.** When the owning Spec is `spec-pyforge-marshal`, `resolve` runs `memlog.py` as today.
  For any other owning Spec it writes nothing there and prints, per accepted finding, the exact command the operator
  runs: `uv run _bmad/scripts/memlog.py append --workspace <spec-folder> --type event --text "<acceptance text>"`. The
  rejected ids and reasons still go back into the report (Tier 3).
- **Rules findings carry their governor.** `audit_plan` gives `AGENTS.md` findings the
  `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe` workspace and `CHAIN-STANDARD.md`
  findings `docs/governance/spec-one-chain-per-station`, through a per-target owner override recorded on the report.
- **The contract follows the code.** The memlog events for MAR-M-Z5 and MAR-M-C5 and the operator's decision are
  already on `spec-pyforge-marshal` (commit `7dde4a0202`). Re-derive CAP-303 with `bmad-spec`: the success line shows
  `--accept ID[:NOTE]`, `--reject ID[:REASON]` and `--type event`; resolve writes only marshal's Spec and prints the
  command for any other; the story-spec-edit route is dropped from the intent or given a check. The ruling keeps
  `SPEC.md:1154` and `:1158` as written, so no named exception and no AD note is needed. Then the cascade re-stamp and
  the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the subverb stays behind
  `pyforge.marshal.egm_resolve_bridge`.

Ledger key: `113-13-resolve-writes-only-marshal-s-spec-and-prints-the-memlog-command-for-any-other`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-303** (FR-245): an accepted finding travels the chain's only write path.
- The Constraints at `SPEC.md:1154` and `:1158` bound it; they are unchanged.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL8: MAR-M-Z5, MAR-M-C5); the operator's ruling of 2026-11-01 on cross-station writes.

## Acceptance Criteria

- **AC1 — The refusal.** `resolve --project pyforge-marshal` on a report whose `spec_workspace` names
  `spec-pyforge-atlas` (and no owner override) refuses with the usage code and writes nothing
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — Marshal's own Spec.** An accepted finding owned by `spec-pyforge-marshal` is appended through `memlog.py`
  exactly as today.
- **AC3 — Any other Spec.** An accepted finding owned by another Spec (a station `--project`, or a rules override) is
  never written; stdout carries one exact `uv run _bmad/scripts/memlog.py append --workspace <spec-folder> --type event
  --text "…"` line per finding, with the workspace and text the finding carries; the memlog stub records no call.
- **AC4 — The overrides.** `audit_plan` gives `AGENTS.md` the `spec-pyforge-scribe` workspace and `CHAIN-STANDARD.md`
  `docs/governance/spec-one-chain-per-station`; a station skill and every mint and decompose target keep their station
  Spec.
- **AC5 — Rejections.** Rejected ids and reasons are written back into the report as today.
- **AC6 — The contract.** CAP-303 reads as the Approach states, re-derived by `bmad-spec` (both self-validate passes
  logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC7 — Mutation.** Letting `resolve` call `memlog.py` for a non-marshal Spec fails AC3's test. Restore it.
- **AC8 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Print a command the operator can paste as is; quote the text so a shell reads it as one argument.

**Ask first:**
- Any write outside `spec-pyforge-marshal`, or a named exception to `SPEC.md:1154` / `:1158`.

**Never:**
- Never write another station's memlog, `SPEC.md`, ledger or story spec; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

**Residual risk:**
- A report written before this story carries no owner override, so a rules finding from it resolves under
  `spec-pyforge-marshal` only if its `spec_workspace` says so; the operator re-runs the target to get the override.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-303 (FR-245).

Parent: `spec-pyforge-marshal` CAP-303 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL8).
- Epic: Epic 113.
- Ledger key: `113-13-resolve-writes-only-marshal-s-spec-and-prints-the-memlog-command-for-any-other`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` and the re-derived `SPEC.md`; within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: done (independent review passed 2026-11-01; see Review Triage Log)
phase: the `bmad-spec` re-derive of CAP-303 (both self-validate passes), the cascade re-stamp and the scoped stamp are
the session owner's. The memlog events the re-derive reads are on `spec-pyforge-marshal` (from commit `7dde4a0202`,
plus the two this story appended). No write outside `spec-pyforge-marshal`; no named exception to `SPEC.md:1154` /
`:1158`.

**What changed.**

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`:
  - new `OWN_PROJECT = "pyforge-marshal"` and `RULES_OWNER_OVERRIDES` (`AGENTS.md` ->
    `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe`, `CHAIN-STANDARD.md` ->
    `docs/governance/spec-one-chain-per-station`);
  - `owner_override(root, stage, target)` (rules stage only) and `owning_spec(...)` (the override, else the station's
    own Spec folder);
  - `audit_plan` now returns `(slug, stage, target, dream, owning Spec folder)`; `run_audit` passes the folder to
    `run_one`, whose new `owner` keyword (default `owning_spec`) is stamped as `spec_workspace` and, when it is not the
    run's own station Spec, recorded as `owner_override` on the report. Ad hoc `--stage rules --target AGENTS.md`
    gets the same override;
  - `resolve` takes `--project` (argparse `SUPPRESS`, so it survives before or after the subverb) and refuses without
    it. `resolve_owner` derives the owning Spec folder from `--project`, or, for a rules report that records an
    override, from `RULES_OWNER_OVERRIDES` (never from the report); the report's `spec_workspace` must name it
    (same path, or one ending in its repo-relative parts, for a report written in another checkout), else
    `ReportError` -> usage code, nothing written. The write and the printed folder are always this root's;
  - `run_resolve` calls `memlog.py` only when the owner is `spec-pyforge-marshal`; for any other owning Spec it prints
    one `uv run _bmad/scripts/memlog.py append --workspace <folder> --type event --text <text>` line per accepted
    finding (text shell-quoted with `shlex.quote`), writes no memlog line, and writes the rejections (and acceptances)
    back into the report;
  - the module docstring and the `resolve` help say so.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`: `ChallengeReport.owner_override`
  (serialised only when set, read back by `parse_report`, carried by `with_provenance` and `resolve`); new pure
  `memlog_command(script=, workspace=, text=)`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`:
  - `test_resolve_refuses_a_report_another_project_owns_and_writes_nothing` (AC1, plus no `--project`);
  - `test_resolve_on_marshal_s_own_spec_runs_memlog_with_the_derived_folder` (AC2; a report from another checkout);
  - `test_resolve_prints_the_memlog_command_for_any_other_spec_and_writes_none` x3 (atlas station, scribe override,
    chain-standard override): memlog stub records no call, one command per accepted finding whose `shlex.split` is
    exactly `[uv, run, _bmad/scripts/memlog.py, append, --workspace, <folder>, --type, event, --text, <text>]` with
    a claim carrying single quotes and `$HOME`; rejection and reason written back (AC3, AC5);
  - `test_a_rules_report_names_only_a_governor_the_code_lists` x2 (no override; an override the code does not list);
  - `test_resolve_takes_project_before_or_after_the_subverb`;
  - `test_audit_plan_gives_each_rules_file_its_governor` and `test_an_audit_rules_report_records_its_governor` (AC4);
  - the two older resolve refusal tests now carry marshal's folder, so they still test the already-resolved and
    unknown-id refusals rather than the new ownership refusal.
- Memlog: `spec-pyforge-marshal` gains two events: the surface reconcile naming the three paths, and the new CAP-303
  behaviour (and the dropped story-spec-edit route) for the re-derive.

**Commands run (exit codes read from `$?`).**

- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py`
  exited 0 (124 passed).
- AC7 mutation, on a scratch copy of the package's `src` put first on `PYTHONPATH` (import path confirmed): the
  marshal-only guard in `run_resolve` replaced with `if False:` (so `memlog.py` runs for every Spec) -> the AC3 slice
  exited 1, all three cases failing `assert calls == []`. A second mutant, `resolve_owner` returning the report's own
  `spec_workspace`, failed four tests (AC1, AC2 and both forged-override cases). The scratch copy was deleted; the
  tracked file was never mutated.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exited 0 (13666 passed, 15 skipped; then 34 passed,
  4 skipped).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exited 0. It judged no module, because the change
  is uncommitted and the gate diffs `origin/main..HEAD`. The suite's coverage JSON reads `cli/challenge.py` at 86.8%
  and `core/challenge.py` at 95.6%, both above the 80% floor.
- `ruff check` and `ruff format --check` over the three changed Python files, run from the package directory with the
  pyforge-marshal env's ruff (the `ruff` pixi task shadows the binary under `pixi run`), both exited 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.marshal`, run from the package directory with pyforge-guild's
  mypy, exited 0 (217 files). This is marshal's slice of `lint-types`; the full `lint-types` was not run.
- `pixi run --frozen -e pyforge-guild spec-surface-check` exited 0 before any stamp (the memlog moved).
- `pixi run --frozen -e pyforge-guild chain-completeness-check` exited 0.
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` exited 1: a staleness-checkpoint fail on all eight
  stations, marshal's included (the memlog moved past the PRD and spine). The cascade re-stamp after the CAP-303
  re-derive is the session owner's (AC6).

### Fix round 1 — 2026-11-01

Status: blocked. The review's one failure, AC6, is closed except for the `SPEC.md` render and the two self-validate
passes that follow it. This is the blocker Stories 113.8, 113.10, 113.11 and 113.12 hit. Earlier in this session the
auto-mode classifier refused the script-render route (`[Auto-Mode Bypass]`, Story 113.8's fix). That route is the only
way a `bmad-spec` render reaches `SPEC.md` under the `pre-shell.py` hook, and it needs the operator's go-ahead (the
PR #1605 precedent). This round did not attempt the write. No code changed.

- **AC6, the re-derive (`bmad-spec`, headless).**
  - The memlog decision is on `spec-pyforge-marshal/.memlog.md`: `(decision) Re-derive 2026-11-01 (marshal Story
    113.13; EGM audit MAR-M-Z5, MAR-M-C5 of cluster MAR-CL8; the operator's ruling of 2026-11-01 on cross-station
    writes)`. It reads the Story 113.13 behaviour event and the operator's ruling.
  - CAP-303 as rendered:
    - Definition line: title and `← Dream entry 2026-11-01` kept. It gains `; EGM audit findings MAR-M-Z5, MAR-M-C5
      and the operator's ruling of 2026-11-01 on cross-station writes (re-derived 2026-11-01, Story 113.13)`.
    - Intent: an accepted finding becomes a memlog line on the Spec that owns it and a re-derive of that Spec. A
      rejected one stays in the report with its reason. Marshal writes no other station's artifacts. The
      story-spec-edit route is gone.
    - Success: `marshal factory challenge resolve --project <station> --report <path> [--accept ID[:NOTE]]...
      [--reject ID[:REASON]]...`, with `--project` required. The owning Spec comes from `--project`, or from the
      code's per-target governor (`AGENTS.md` → `spec-pyforge-scribe`, `CHAIN-STANDARD.md` →
      `docs/governance/spec-one-chain-per-station`). It never comes from the report. A report that names neither is
      refused with the usage code, and nothing is written. Only `spec-pyforge-marshal` gets a `memlog.py`
      `--type event` line. Any other Spec gets the exact shell-quoted `uv run _bmad/scripts/memlog.py append
      --workspace <spec-folder> --type event --text "<acceptance text>"` command, printed. Accepted and rejected ids,
      with their notes and reasons, go back into the report either way. Nothing edits `SPEC.md`, a ledger or a story
      spec. The kill switch is unchanged.
    - The Constraints at `SPEC.md:1154` and `:1158` are unchanged (the script asserts both, once, before and after).
  - The anchor-asserting render script is
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/render_113_13.py`.
    It takes the `SPEC.md` path as its argument; `--dry-run` checks without writing. It changes 4 lines: the
    frontmatter `updated:` note and CAP-303's definition, intent and success lines.
  - The script asserts:
    - every needle occurs once; the intent and success needles are the two lines after CAP-303's definition;
    - the undo returns the original byte for byte;
    - the CAP definition count (303) and the line count (1388) are unchanged;
    - no stale clause remains (`or a story-spec edit`, the `--project`-less form, the unnamed acceptance text).
  - It must run **after** `render_113_8.py`, `render_113_10.py`, `render_113_11.py` and `render_113_12.py`. It refuses
    unless their four `RE-DERIVED` notes are present. None of them touches CAP-303, so no needle overlaps.
  - On scratch copies in
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/r11313/`:
    - the chain 8 → 10 → 11 → 12 from the live `SPEC.md` exits 0 at each step and reproduces 113.12's
      `r11312/chain12.md` byte for byte;
    - this script's dry run exits 0 and leaves the copy unchanged; its write exits 0 (lines 5, 1137, 1138, 1139);
    - a second run exits 1, and a run on the unrendered `SPEC.md` exits 1, both as expected;
    - the live `SPEC.md` is untouched (`cmp`).
  - **Not done:** writing `SPEC.md` and logging the two self-validate passes.
- **AC6, the cascade.** None of these is on marshal's spec surface (`spec-surface-check` 0).
  - PRD (`prds/prd-pyforge-marshal-2026-07-25/prd.md`): the FR-245 body now names `--project`, `ID[:NOTE]`,
    `ID[:REASON]`, `--type event`, the governor rule, marshal-only writes and the printed command. § 52 is added with
    the rules-target governor table, and the `updated:` note is prefixed. No FR is added or renumbered, and no arrow
    moves.
  - Spine: § *Currency reconciliation — 2026-11-01 (Story 113.13)* records readings on AD-11 / AD-45 (C-3), AD-4 and
    AD-7, and the `updated:` note is prefixed. No AD is added, amended or removed.
  - `epics.md`: the `updated:` note is prefixed; no epic or story moves.
- Commands, exit codes read from `$?`:
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 0 (13666 passed, 15 skipped; 34 passed, 4 skipped).
  - `pixi run --frozen -e pyforge-marshal python -m pytest
    src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py
    src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py`: 0 (124 passed).
  - `spec-surface-check` 0 (its one warning is steward's `spec-pyforge-unifying-strategy`), `chain-completeness-check`
    0, `ad-citation-check` 0, `fr-without-cap-check` 0.
  - `chain_currency_sweep_check.py --json --project pyforge-marshal`: 0, so marshal is current after the memlog
    decision and the cascade. The repo-wide `chain-currency-sweep-check` exits 1, but only on the seven other
    stations' staleness checkpoints (atlas, doctor, herald, mason, scribe, steward, warden), which are other agents'
    work. It reads marshal as `current`.
- **To unblock (session owner, under the operator-approved render route):**
  1. Run `render_113_8.py`, `render_113_10.py`, `render_113_11.py`, `render_113_12.py`, then `render_113_13.py`, on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md`.
  2. Append the two self-validate events with `uv run _bmad/scripts/memlog.py append --workspace
     _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal --type event --text "…"`:
     - Pass 1 (coherence): "bmad-spec self-validate 2026-11-01, Pass 1 (coherence) on the Story 113.13 re-derive of
       CAP-303: PASS. CAP-303 keeps its id, title and provenance, extended with MAR-M-Z5, MAR-M-C5 and the operator's
       ruling. Its intent states WHAT (an accepted finding becomes a memlog line on its owning Spec and a re-derive; a
       rejected one stays in the report with its reason; Marshal writes no other station's artifacts) and drops the
       story-spec-edit route, which had no code path and no check. Its success stays testable against the shipped
       tree: test_resolve_refuses_a_report_another_project_owns_and_writes_nothing,
       test_resolve_on_marshal_s_own_spec_runs_memlog_with_the_derived_folder,
       test_resolve_prints_the_memlog_command_for_any_other_spec_and_writes_none (x3),
       test_a_rules_report_names_only_a_governor_the_code_lists, test_resolve_takes_project_before_or_after_the_subverb,
       test_audit_plan_gives_each_rules_file_its_governor and test_an_audit_rules_report_records_its_governor pin it.
       The Constraints 'The loop home is the unit of isolation and the write boundary' and 'Escalation knowledge flows
       by pull, never cross-boundary write' stand as written and hold for resolve with no named exception. No CAP
       minted (303 definitions), no Constraint moved. SPEC.md script-rendered by render_113_13.py (needles asserted
       once, undo byte-equal, 4 lines changed, 1388 lines)."
     - Pass 2 (preservation): "bmad-spec self-validate 2026-11-01, Pass 2 (preservation) on the Story 113.13
       re-derive: PASS. Every load-bearing claim of the Story 113.13 behaviour event and the operator's 2026-11-01
       ruling landed in SPEC.md: --project required, before or after the subverb; the owning Spec from --project or
       the code's per-target governor (AGENTS.md -> spec-pyforge-scribe, CHAIN-STANDARD.md ->
       docs/governance/spec-one-chain-per-station), never from the report; the usage-code refusal that writes nothing;
       --accept ID[:NOTE], --reject ID[:REASON], --type event; marshal's own memlog written and any other Spec's
       printed as the exact shell-quoted memlog.py command; accepted and rejected ids with notes and reasons back in
       the report; the story-spec-edit route dropped; the two write-boundary Constraints unchanged. The Story 113.8,
       113.10, 113.11 and 113.12 renders' text is kept. Wrapper-only content dropped: the story spec's line numbers,
       its ledger key and its residual-risk note on reports written before this story (kept in the story spec)."
  3. `git add`, then run the scoped stamp `--spec pyforge-marshal/spec-pyforge-marshal`.
  4. Return this story to `in-review`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL8: MAR-M-Z5, MAR-M-C5)
  and the operator's ruling of 2026-11-01 (resolve appends to marshal's Spec and prints the exact `memlog.py` command for
  any other owning Spec; implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- 2026-11-01 — reviewer: independent session. I did not write this code. I judged `git diff HEAD` of the story's
  files against this spec, not against the Auto Run Result. **Verdict: fail**; status is back to `in-progress`.
  - Read:
    - `cli/challenge.py`: `OWN_PROJECT`, `RULES_OWNER_OVERRIDES`, `owner_override`, `owning_spec`, the five-tuple
      `audit_plan`, `run_one`'s `owner`, `_names`, `resolve_owner` and `run_resolve`.
    - `core/challenge.py`: `ChallengeReport.owner_override` (written only when set) and `memlog_command`, which
      quotes with `shlex.quote`.
    - The tests.
    - The real `marshal` parser (`cli.main._build_parser`): `--project` given before or after `resolve` survives,
      and absent it is `None`, which the code refuses.
  - AC1 holds. With `--project pyforge-marshal`, an atlas `spec_workspace` returns the usage code. The memlog stub
    records nothing, the report bytes are unchanged and stdout is empty. A missing `--project` is refused the same way.
  - AC2 holds. Marshal's own Spec goes through the `memlog` callable with this root's folder.
  - AC3 holds. For an atlas station, the scribe override and the chain-standard override, the stub records no call.
    Stdout carries one command per accepted finding, and `shlex.split` of each is exactly `uv run
    _bmad/scripts/memlog.py append --workspace <folder> --type event --text <text>`, including a claim with quotes and
    `$HOME`.
  - AC4 holds. `test_audit_plan_gives_each_rules_file_its_governor` and `test_an_audit_rules_report_records_its_governor`.
  - AC5 holds. The rejection and its reason are written back into the report.
  - AC7 holds, re-observed. With the marshal-only guard in `run_resolve` replaced by `if False:`, the run exits 1 and
    all three `test_resolve_prints_the_memlog_command_for_any_other_spec_and_writes_none` cases failed.
  - AC8 holds. The suite is green (see the shared evidence).
  - The Boundaries hold. No write outside `spec-pyforge-marshal` is possible: `--project` other than marshal never
    yields marshal's folder. The printed command pastes as is from the repo root.
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
    1. AC6 is not met. CAP-303 is not re-derived: `SPEC.md` has no diff (the success line still lacks `--project`,
       `ID[:NOTE]` and `--type event`, and the story-spec-edit route is still in the intent). No self-validate pass is
       logged for this story, and `chain-currency-sweep-check` exits 1. No code change is needed. A re-derive with
       both passes logged, then marshal's cascade re-stamp, closes it; return the story to `in-review` after that.
  - Not blocking: whether an override applies is still keyed on the report's own `owner_override` field, though the
    folder always comes from `RULES_OWNER_OVERRIDES`. A rules report with no override field resolves under `--project`,
    which is the Residual risk this spec already accepts.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`) and the rendered `SPEC.md` against this spec, not against the Auto Run Result or the fix
  rounds. **Verdict: pass**; status set to `done`.
  - AC1 holds. `resolve_owner` derives the folder from `--project` and refuses a report whose `spec_workspace` names
    neither it nor a listed governor. A missing `--project` is refused too. The usage code is returned and nothing is
    written (`test_resolve_refuses_a_report_another_project_owns_and_writes_nothing`).
  - AC2 holds. Marshal's own Spec goes through the `memlog` callable
    (`test_resolve_on_marshal_s_own_spec_runs_memlog_with_the_derived_folder`).
  - AC3 holds. For any other owner `run_resolve` prints one `core.memlog_command` line per accepted finding,
    shell-quoted with `shlex.quote`, and records no memlog call.
  - AC4 holds. `audit_plan` gives `AGENTS.md` `spec-pyforge-scribe` and `CHAIN-STANDARD.md`
    `docs/governance/spec-one-chain-per-station` (`test_audit_plan_gives_each_rules_file_its_governor`,
    `test_an_audit_rules_report_records_its_governor`).
  - AC5 holds. Rejections and reasons go back into the report on both paths.
  - AC6 holds (this review's re-check of the first review's failure):
    - CAP-303's intent drops the story-spec-edit route and says Marshal writes no other station's artifacts.
    - Its success shows:
      - `resolve --project <station> --report <path> [--accept ID[:NOTE]]... [--reject ID[:REASON]]...`, with
        `--project` required before or after the subverb;
      - the owning Spec taken from `--project` or the code's per-target governor, never from the report;
      - the refusal that writes nothing;
      - one `memlog.py` `--type event` line on `spec-pyforge-marshal` only;
      - for any other Spec, the printed, shell-quoted `uv run _bmad/scripts/memlog.py append --workspace
        <spec-folder> --type event --text "..."` command;
      - ids, notes and reasons back into the report;
      - the closing re-derive line.
    - This matches `resolve_owner`, `run_resolve`, `memlog_command`, `owner_override` and `audit_plan`.
    - `SPEC.md` lines 1150-1160, which include the Constraints at :1154 and :1158, are identical to `origin/main`.
    - The memlog carries the Story 113.13 behaviour event and its `(decision) Re-derive 2026-11-01 (marshal Story
      113.13 ...)`. CAP-303's definition line names Story 113.13. The self-validate pair is logged.
      `spec-surface-check` 0, `chain-completeness-check` 0, chain-currency for marshal 0.
  - AC7 holds, re-observed. With the marshal-only guard replaced by `if False:`, the run exits 1 and all three
    `test_resolve_prints_the_memlog_command_for_any_other_spec_and_writes_none` cases failed.
  - AC8 holds. The suite exits 0.
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

## Dev Notes

- Review follow-up 2026-11-01 (station-tests routing): `CHAIN_WS` in
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` names the tracked
  `docs/governance/spec-one-chain-per-station`, which steward's trigger map
  (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`) derives as a marshal read, and
  `marshal_paths` in `.github/workflows/pyforge-station-tests.yml` did not carry it. It does now, so an edit there runs
  `marshal-test`. The test and its assertions are unchanged; the meta-test and `test_factory_challenge.py` exit 0.
