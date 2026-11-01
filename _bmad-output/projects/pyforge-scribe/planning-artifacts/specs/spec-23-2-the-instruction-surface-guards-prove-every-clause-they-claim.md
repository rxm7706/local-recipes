---
title: '23.2: The instruction-surface guards prove every clause they claim'
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-19-3-the-instruction-surface-is-version-aware-claude-code-s-built-in-agents-md-mod.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-20-1-the-parity-meta-test-reds-a-todo-inside-the-managed-block.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-23-1-the-skf-managed-block-lives-in-agents-md-only.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
  - scripts/claude_instruction_mode_check.py
  - .claude/settings.json
  - _bmad/skf/config.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three capabilities claim states that no lasting test holds. Each gap below is a test that passes
without the state it names. All were found at `03a7aff5d9`.

- **CAP-27, the 2026-09-26 end state (cluster SCR-2).** Stories 21.2 and 23.1 checked three things once: `CLAUDE.md`
  carries no SKF block, `_bmad/skf/config.yaml` `ides` is `[other]`, and `AGENTS.md` says `detectors-ci` and
  `pr-preflight` run `governance-currency`. The memlog (:126) decided no new CAP but named no check, so a hand SKF
  reinstall would regress unseen. One evidence correction: skf 3.0 still lists `claude-code` in
  `platform-codes.yaml`. The two mitigations are steward's `config_paths` restore
  (`data/bmad_core_releases/6.12.2.yaml`:119-127) and `ides: [other]`. Mason's `test_persona_consults_cfe.py`:388-398
  already asserts that `AGENTS.md` carries the SKF block, so that is not re-asserted here. Finding SCR-M-C1's first
  half is refuted: CAP-29's source is the Dream's Realization-log bullet at `docs/dreams/pyforge-scribe.md`:197-216.
- **CAP-29, the runtime check (cluster SCR-3).** `test_runtime_mode_check_is_registered_and_silent_without_claude`
  passes a missing `--claude` path, which takes the exit-2 could-not-run branch. The no-binary branch
  (`scripts/claude_instruction_mode_check.py`:92-95) prints an ok line instead of staying silent, and neither warn
  branch (runtime below 2.1.277, unpinned mode) runs end to end. `.claude/settings.json` `customInstructions` lists
  five of `AGENTS.md`'s eight principles. Operator ruling 2026-11-01: it stays as a one-sentence pointer to
  `AGENTS.md` § *Behavioural guidelines (every harness)*, and its runtime effect is recorded as unverified.
- **CAP-29, the normalised duplicate guard (cluster SCR-4).** `test_per_tool_file_repeats_no_agents_md_section` is
  parametrized over `POINTER_FILES + tuple(CURSOR_RULES)` (parity :34-40, :130), never `CLAUDE.md`, the file whose
  duplicate motivated CAP-29. Only the normaliser is tested (:203), never the guard path with a planted duplicate.
- **CAP-30, the aspiration guard (cluster SCR-5).** `_ASPIRATION` (parity :284) has `FIXME:` and "not (yet) landed"
  branches, but `test_aspiration_guard_reads_only_between_the_markers` (:305-312) plants only `TODO:`. A mutation that
  drops either branch survives. Story 23.1's "(Mason has no SKF skill)" is a dated record, and
  `docs/reference/agent-instruction-notes.md`:150-157 already records the 2026-09-28 reversal, so nothing changes
  there.
- **CAP-32 against the managed block (SCR-D-R6, narrowed).** The `bmad:context` block types two counts the estate
  catalog derives: "13 members" (`AGENTS.md`:48) and "16 skf ones" (:75). Marshal Story 113.7's
  `bmad-project-context` refresh drops them. This story adds the guard that keeps them out.

EGM audit 2026-11-01 findings carried: SCR-M-Z2, SCR-M-D1, SCR-M-C1, SCR-M-D2, SCR-D-C4, SCR-D-C3, SCR-D-C7, SCR-D-R6
(clusters SCR-2, SCR-3, SCR-4, SCR-5). Research:
`_bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** All the work is in the parity meta-test, plus one print and one settings sentence:

1. Add three asserts. `CLAUDE.md` contains no `<!-- SKF:BEGIN`. `_bmad/skf/config.yaml` `ides` equals `['other']`.
   The `AGENTS.md` line about `governance-currency` (Pre-PR item 10) names `detectors-ci` and `pr-preflight`.
2. Write a stub `claude`: an executable script in `tmp_path` with a `sys.executable` shebang, `chmod +x`. Run the
   check with `PATH` set to `tmp_path` only. Cases: absent gives exit 0 and empty stdout; 2.1.276 gives exit 1;
   2.1.300 with unpinned settings gives exit 1; 2.1.300 pinned gives exit 0. Rename the missing `--claude` case to a
   could-not-run test that asserts exit 2.
3. First confirm that `scripts/detectors.py`'s runtime-scope runner treats empty stdout as ok. If it does, remove the
   ok print in the no-binary branch and keep exit 0. The docstring (:23), the `pixi.toml` task description (:1444),
   CAP-29's success and Story 19.3's criterion already say "silent", so none of them needs an edit, and `pixi.toml`
   and `environment.yaml` stay untouched. If the runner does not, keep the print and amend CAP-29's "silent" to
   "exit 0, ok line" through the memlog.
4. Move the H2 intersection into a helper. Parametrize only the duplicate guard over
   `POINTER_FILES + tuple(CURSOR_RULES) + ("CLAUDE.md",)`. Keep `CLAUDE.md` out of `POINTER_FILES`, so the 60-line
   thin rule, which CAP-27 does not set for `CLAUDE.md`, never reaches it. Add a planted self-test: the helper flags
   `## Behavioral Guidelines` against `## Behavioural guidelines (every harness)`. Confirm today's `CLAUDE.md` H2s do
   not collide.
5. Extend the aspiration self-test. Plant `FIXME:`, "not yet landed" and "not landed" lines between the markers and
   assert each is reported. Plant one outside the markers and assert it is ignored.
6. Add an assert that the `bmad:context` block types no suite-member or skill-family count. Fixtures plant
   "13 members" and "16 skf ones" and must red.
7. Reword `customInstructions` to one sentence pointing at `AGENTS.md` § *Behavioural guidelines (every harness)*,
   with no list. `test_project_settings_custom_instructions_point_at_agents_md` (:228) still passes.
8. Append a `spec-pyforge-scribe` memlog event naming these asserts and amending CAP-27's success. Then run
   `bmad-spec` to re-derive CAP-27, and CAP-29 too if step 3 amends "silent". Log both self-validate passes.
   `.claude/**` is allowlisted for the spec surface, but the `customInstructions` change still gets a memlog line
   because CAP-29 names it.

Ledger key: `23-2-the-instruction-surface-guards-prove-every-clause-they-claim`.
Type / Effort / Deps: fix / M / — (same PR: marshal Story 113.7's `bmad-project-context` refresh, for the
typed-count assert).

### Living CAP citations

- `spec-pyforge-scribe` CAP-27 (FR-16): the session contract reaches every harness from one file. This story adds the
  lasting check of the 2026-09-26 end state. No new CAP.
- `spec-pyforge-scribe` CAP-29: the parity meta-test reds a normalised duplicate; the runtime check warns on drift and
  is silent without `claude`; `customInstructions` points at `AGENTS.md`.
- `spec-pyforge-scribe` CAP-30: the meta-test reds a `TODO:` / `FIXME:` / "not yet landed" line inside the markers.
- `spec-pyforge-scribe` CAP-32: `AGENTS.md` states nothing the catalog derives.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- AC1: Given `CLAUDE.md` gains a `<!-- SKF:BEGIN` marker, or `_bmad/skf/config.yaml` `ides` gains `claude-code`, or
  the `AGENTS.md` `governance-currency` line drops `detectors-ci` or `pr-preflight` When the parity test runs Then it
  fails naming the broken clause; the live tree passes.
- AC2: Given no `claude` on `PATH` When `scripts/claude_instruction_mode_check.py` runs Then it exits 0 with empty
  stdout (or, if the runtime-scope runner needs a line, exits 0 with the ok line, and CAP-29 says so through the
  memlog).
- AC3: Given a stub `claude` reporting 2.1.276 When the check runs Then it exits 1. Given 2.1.300 with settings whose
  `instructionFiles` is not `claude-md-and-agents-md` When it runs Then it exits 1. Given 2.1.300 with the pinned mode
  When it runs Then it exits 0.
- AC4: Given `--claude` names a path that does not exist When the check runs Then it exits 2, and the test's name says
  could-not-run.
- AC5: Given a planted `## Behavioral Guidelines` H2 against `AGENTS.md`'s `## Behavioural guidelines (every harness)`
  When the duplicate-H2 helper runs Then it reports the pair; the guard reads `CLAUDE.md`, `POINTER_FILES` and every
  `.cursor/rules/*.mdc`, and today's tree passes; `CLAUDE.md` is not subject to the 60-line rule.
- AC6: Given `FIXME:`, "not yet landed" and "not landed" lines planted between the `bmad:context` markers When the
  aspiration guard runs Then each is reported; given one planted outside the markers Then it is ignored.
- AC7: Given "13 members" or "16 skf ones" planted inside the `bmad:context` block When the typed-count assert runs Then
  it fails; after marshal Story 113.7's refresh the live block passes.
- AC8: Given `.claude/settings.json` When it is read Then `customInstructions` is one sentence pointing at `AGENTS.md`
  § *Behavioural guidelines (every harness)*, with no list of principles, and
  `test_project_settings_custom_instructions_point_at_agents_md` passes.
- AC9: Given any one new assert When its guarded state is broken Then the test fails (mutation); the station SKF marker
  checks (`test_skf_domain_skill.py` / `test_skf_domain_skills.py`) still pass.
- AC10: Given this story lands When `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` runs Then it exits 0, and
  the `spec-pyforge-scribe` memlog carries the event naming the asserts and the CAP-27 re-derive with both
  self-validate passes logged.

## Boundaries & Constraints

**Always:**
- Keep each new assert compatible with the station SKF marker checks, which only test that markers are well formed.
- Reconcile every Spec `spec-surface-check` names: the memlog entry first, then `git add`, then one scoped
  `--write-baseline --spec <project>/<spec>` per Spec.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never re-assert that `AGENTS.md` carries the SKF block; mason's `test_persona_consults_cfe.py` holds it.
- Never add `CLAUDE.md` to `POINTER_FILES`.
- Never edit `AGENTS.md`'s `bmad:context` block or its SKF block by hand. The counts leave through marshal Story
  113.7's `bmad-project-context` refresh.
- Never write `_bmad/skf/config.yaml`; this story only reads it.
- Never edit `pixi.toml` or `environment.yaml`.
- Never hand-edit `SPEC.md` (memlog event, then `bmad-spec`) or `sprint-status-ledger.yaml`; never run a bare
  `spec_surface_check.py --write-baseline`.
- Never reword Story 19.3's, 20.1's or 23.1's criteria in `epics.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no `claude` | `PATH` = empty `tmp_path` | exit 0, empty stdout | ok line only if the runner needs it |
| old runtime | stub prints 2.1.276 | exit 1 (warn) | — |
| unpinned mode | stub 2.1.300, settings without the pinned mode | exit 1 (warn) | — |
| pinned | stub 2.1.300, pinned settings | exit 0 | — |
| bad `--claude` | path does not exist | exit 2 (could-not-run) | — |
| planted duplicate | `## Behavioral Guidelines` | reported | — |
| planted aspiration | `FIXME:`, "not yet landed", "not landed" inside the markers | each reported | outside: ignored |
| typed count | "13 members", "16 skf ones" inside the block | reported | — |

</intent-contract>

## Binding

Parent: `spec-pyforge-scribe` CAP-27 (FR-16), CAP-29 and CAP-30; a `fix`, so no new CAP.
Parent capability:
- `spec-pyforge-scribe` CAP-27 — the session contract reaches every harness from one file (PRD FR-16 ← CAP-27).
- `spec-pyforge-scribe` CAP-29 — the instruction surface is version-aware, not version-dependent.
- `spec-pyforge-scribe` CAP-30 — the managed instruction block carries no aspiration.
Dream: `docs/dreams/pyforge-scribe.md` (the 2026-09-20, 2026-09-26 and 2026-09-29 entries; the 2026-11-01 EGM audit
residue).
Ledger key: `23-2-the-instruction-surface-guards-prove-every-clause-they-claim`.
Ledger status at mint: `backlog`.
Deps: — (same PR: marshal Story 113.7's `bmad-project-context` refresh, for the typed-count assert).
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).
EGM audit findings: SCR-M-Z2, SCR-M-D1, SCR-M-C1, SCR-M-D2, SCR-D-C4, SCR-D-C3, SCR-D-C7, SCR-D-R6.
Surface: `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`, `scripts/claude_instruction_mode_check.py` (the no-binary branch), `.claude/settings.json` (`customInstructions`), `_bmad/skf/config.yaml` (read, never written).

## Epic excerpt

**Type:** fix • **Effort:** M • **FR/AD:** spec-pyforge-scribe CAP-27 (FR-16), CAP-29 and CAP-30; a fix, no new CAP.
See `epics.md` § Story 23.2 for the full Given / When / Then / And.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`
  — expected: pass (red on each planted case first, per AC9).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-mason python -m pytest src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py`
  — expected: pass (the `AGENTS.md` SKF block assert this story does not duplicate).
- `pixi run -e pyforge-guild claude-instruction-mode-check` — expected: exit 0 on a host with no `claude`, or on a
  current, pinned runtime.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

**Manual checks:**
- `python scripts/detectors.py --scope runtime --list` — expected: lists `claude_instruction_mode_check`; read how the
  runner treats empty stdout before step 3 drops the print.

## Spec Change Log

- 2026-11-01 — minted `backlog` from the EGM fleet audit (marshal Story 113.7; operator triage 2026-11-01, including
  the `customInstructions` ruling).

## Auto Run Result

Status: in-review

### What changed

- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`:
  - AC1 / CAP-27: `_skf_end_state_breaks` + `test_the_2026_09_26_skf_end_state_holds` check three clauses. `CLAUDE.md`
    has no `<!-- SKF:BEGIN`. `_bmad/skf/config.yaml` `ides` (read with `yaml.safe_load`, never written) equals
    `['other']`. AGENTS.md's Pre-PR item 10 `governance-currency` bullet, with its continuation lines joined by
    `_governance_currency_bullet`, names `` `detectors-ci` `` and `` `pr-preflight` ``.
    `test_skf_end_state_guard_names_each_broken_clause` has four ids. Each one breaks one clause on the live inputs
    and asserts that exactly that clause is reported. The test does not re-assert that AGENTS.md carries the SKF
    block, because mason holds that check.
  - AC2–AC4 / CAP-29: `_stub_claude` writes an executable `claude` with a `sys.executable` shebang into `tmp_path`.
    `_run_mode_check` runs the script with `PATH` set to that one directory and a tmp `--settings` file.
    - `test_runtime_mode_check_is_silent_without_claude_on_path`: exit 0, `stdout == ""`.
    - `test_runtime_mode_check_branches_with_a_stub_claude[old-runtime-warns]`: 2.1.276 with pinned settings exits 1.
    - `[unpinned-mode-warns]`: 2.1.300 with `{}` exits 1.
    - `[pinned-current-ok]`: 2.1.300 with pinned settings exits 0.
    - `test_runtime_mode_check_could_not_run_on_a_missing_claude_path`: exit 2, `could-not-run`.
    The old `..._registered_and_silent_without_claude` test is now `test_runtime_mode_check_is_registered`. It keeps
    only the registration and `configured_mode` asserts. The stub tests skip on win32 because the stub is a shebang
    script.
  - AC5 / CAP-29: the H2 intersection moves into `_duplicate_h2`. The guard is parametrized over
    `DUPLICATE_GUARD_FILES` (`POINTER_FILES` + every `.cursor/rules/*.mdc` + `CLAUDE.md`, deduplicated, so
    `specs.mdc` no longer runs twice). `CLAUDE.md` is not in `POINTER_FILES`, so the 60-line rule never reaches it.
    `test_duplicate_guard_reports_a_planted_normalised_duplicate_in_claude_md` checks three things. Live `CLAUDE.md`
    has no collision, since its H2s are Interactive session path, Where moved sections went and Team Memory. A
    planted `## Behavioral Guidelines` is reported against the live AGENTS.md. `CLAUDE.md` is outside
    `POINTER_FILES`.
  - AC6 / CAP-30: `test_aspiration_guard_reports_every_branch_inside_and_ignores_it_outside[fixme|not-yet-landed|not-landed]`.
  - AC7 / CAP-32: `_TYPED_COUNT` and `test_managed_block_types_no_suite_member_or_skill_family_count` pass on the live
    block. The refresh in `db3a81aede` already dropped the counts. `test_typed_count_guard_reports_a_planted_count_inside_the_block[13-members|16-skf-ones]`
    reds a count inside the markers and ignores the same line outside them.
  - AC8: `test_project_settings_custom_instructions_point_at_agents_md` now requires exactly one entry, one sentence
    with no `:` list, the section name, and none of the bolded principle names it parses from AGENTS.md's section
    (8 today).
- `scripts/claude_instruction_mode_check.py`: the no-binary branch no longer prints and still exits 0 (AC2). Before
  the change I confirmed that `scripts/detectors.py` `run_one` maps rc 0 to `pass` whatever stdout says, and empty
  stdout gives `summary: ""`. The docstring, the `pixi.toml` task text, CAP-29 and Story 19.3 already said
  "silent", so `pixi.toml` and `environment.yaml` are untouched. Fixed in the touched file: `subprocess.run(...,
  check=False)` (PLW1510) and mode 100755 to match its shebang (EXE001). The file was also ruff-formatted, so
  `ruff format --check` on it is green. That is formatting only, about 30 lines, with no behaviour change.
- `.claude/settings.json`: `customInstructions` is now the single sentence "Follow the behavioural guidelines in
  AGENTS.md § Behavioural guidelines (every harness)." (operator ruling 2026-11-01; the ruling records its runtime
  effect as unverified in this Spec's memlog.)
- `spec-pyforge-scribe` memlog: one surface-reconcile event naming all three paths, and one CAP-27 success event
  naming the end-state asserts. CAP-29 is not amended because "silent" now holds as written.

### Commands run (exit codes)

- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`
  — 0 (49 passed).
- AC9 mutation probes on scratch copies of the test file. Each copy points at the worktree root and has one change;
  the tracked files are untouched. Every probe exited 1, and only the guarding test(s) failed:
  - old script with the ok print → the silent test failed.
  - HEAD `.claude/settings.json` → the customInstructions test failed.
  - `03a7aff5d9` AGENTS.md (block still typing "13 members" / "16 skf ones") → the typed-count test failed and named
    both lines.
  - `FIXME` branch dropped from `_ASPIRATION` → `[fixme]` failed.
  - not-(yet-)landed branch dropped → `[not-yet-landed]` and `[not-landed]` failed.
  - `CLAUDE.md` dropped from `DUPLICATE_GUARD_FILES` → the planted duplicate self-test failed.
  - each `_skf_end_state_breaks` clause disabled in turn → its own mutation id failed.
  - typed-count match disabled → both planted ids failed.
- `pixi run --frozen -e pyforge-mason python -m pytest src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` — 0 (19 passed).
- Station SKF marker checks (AC9): doctor, marshal and warden `tests/meta/test_skf_domain_skill.py` — 0, 0, 0 (6, 8,
  6 passed). steward `tests/meta/test_skf_domain_skills.py` — 0 (6 passed).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_detectors_task_match.py` — 0 (36 passed).
- `pixi run -e pyforge-guild claude-instruction-mode-check` — 0 (`ok -- Claude Code 2.1.314 with
  instructionFiles=claude-md-and-agents-md` on this host). With `--settings /nonexistent/x.json` — 1 (warn).
- `pixi run --frozen -e pyforge-guild python scripts/detectors.py --scope runtime --list` — 0; lists
  `claude_instruction_mode_check task=claude-instruction-mode-check`.
- `pixi run -e pyforge-guild governance-currency` — 0.
- `pixi run -e pyforge-scribe-pg scribe-pg-up` — 0. Then `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 0
  (451 passed, 12 skipped; the full suite).
- `.pixi/envs/pyforge-guild/bin/ruff check` and `ruff format --check` on the test file and on
  `scripts/claude_instruction_mode_check.py` — 0, 0, 0, 0. The scribe lint-types ruff slice (`ruff check src tests` and
  `ruff format --check src tests` from the package dir) — 0, 0. mypy is not affected, because `lint-types` runs
  `mypy -p pyforge.scribe` and only `tests/` changed in the package.
- `pixi run -e pyforge-guild spec-surface-check` — 0 (read-only; no stamp written).

### Left for the session owner

- The CAP-27 re-derive through `bmad-spec` and its two self-validate passes (AC10's memlog half) belong to the
  re-derive phase, which reads the CAP-27 success event appended here.
- Co-governor reconciles and the scoped `--write-baseline` stamps (spec-surface-check is green on this tree).
- Same PR as marshal Story 113.7's `bmad-project-context` refresh (`db3a81aede`), which the typed-count assert needs.

## Review Triage Log

### 2026-11-01 — Independent review (reviewer: independent session) — FAIL (back to in-progress)

Judged against this spec's ACs and Boundaries from `git diff HEAD` of the parity meta-test,
`scripts/claude_instruction_mode_check.py` and `.claude/settings.json`, not the implementer's summary. Every verdict
read from the exit code.

Checked and holding:
- AC1 — `test_the_2026_09_26_skf_end_state_holds` passes on the live tree; `test_skf_end_state_guard_names_each_broken_clause`
  (4 ids) reds exactly the broken clause.
- AC2 — no-binary branch prints nothing, exit 0; `scripts/detectors.py` `run_one` maps rc 0 to `pass` whatever stdout
  says, so CAP-29's "silent" stands. `test_runtime_mode_check_is_silent_without_claude_on_path` pins it.
- AC3 / AC4 — stub-`claude` tests: 2.1.276 → 1, 2.1.300 unpinned → 1, 2.1.300 pinned → 0; missing `--claude` → 2
  (`…could_not_run_on_a_missing_claude_path`). `pixi run -e pyforge-guild claude-instruction-mode-check` exit 0 on this
  host; `detectors.py --scope runtime --list` exit 0 and lists it; `tests/scripts/test_detectors_task_match.py` exit 0.
- AC5 — `_duplicate_h2` + `DUPLICATE_GUARD_FILES` read `CLAUDE.md`, `POINTER_FILES` and every `.cursor/rules/*.mdc`;
  `CLAUDE.md` is not in `POINTER_FILES`; the planted `## Behavioral Guidelines` is reported.
- AC6 — FIXME:, "not yet landed", "not landed" each reported inside the markers, ignored outside.
- AC7 — typed-count assert passes on the live block (113.7's refresh in `db3a81aede`) and reds both planted counts.
- AC8 — `customInstructions` is the one sentence pointing at `AGENTS.md § Behavioural guidelines (every harness)`.
- AC9 — mutations re-observed on scratch copies of the test (tracked files untouched), each exit 1 with only the
  guarding test red: HEAD script with the ok print; HEAD `settings.json`; `03a7aff5d9` AGENTS.md (typed counts);
  FIXME branch dropped; not-(yet-)landed branch dropped; `CLAUDE.md` dropped from the guard files; each SKF end-state
  clause disabled; typed-count match disabled. Station SKF marker checks: doctor/marshal/warden
  `test_skf_domain_skill.py` and steward `test_skf_domain_skills.py` exit 0; mason `test_persona_consults_cfe.py` exit 0.
- AC10 (first half) — `pyforge-scribe-test` exit 0 (460 passed, 12 skipped); memlog carries the surface-reconcile event
  naming the asserts and a CAP-27 success event.
- Ruff check / format --check on the test (package config) and on the script: 0 each. governance-currency exit 0,
  spec-surface-check exit 0. `.claude/settings.json` diff is the one `customInstructions` line.

Failures:
1. AC10 (second half) not met: there is no CAP-27 `bmad-spec` re-derive and no self-validate Pass 1 / Pass 2 logged in
   `spec-pyforge-scribe/.memlog.md` for this story, and `spec-pyforge-scribe/SPEC.md` is unchanged in the worktree.
   Approach step 8 and AC10 put the re-derive in this story; the Auto Run Result defers it to an unnamed "re-derive
   phase". Close it by running `bmad-spec` on the CAP-27 success event and logging both self-validate passes, then
   return the story to `in-review`.

Non-blocking observations:
- The parity module imports `yaml` at module level, but PyYAML is not a declared dependency of `pyforge-scribe` or of
  `feature.pyforge-scribe`; it arrives only transitively (cocoindex → watchdog → pyyaml, `pixi tree --invert`). If that
  chain moves, the whole module fails to collect. A regex read of `ides` would avoid the dependency.
- `scripts/claude_instruction_mode_check.py` was reformatted to ruff's default 88 columns (no root ruff config); style
  only, no behaviour change.

### 2026-11-01 — Independent review, second review (reviewer: independent session) — PASS (done)

Judged against this spec's ACs and Boundaries on the committed tree at `812d776dba` (worktree clean), not the
implementer's summary or the first review. Every verdict read from the exit code, never through a pipe. Each mutation
probe ran on a scratch copy of the parity test, with `ROOT`, `SCRIPT`, `AGENTS` or the settings path pointed at the
mutated input. No tracked file was touched.

- AC1 — holds. `test_the_2026_09_26_skf_end_state_holds` passes on the live tree, and
  `test_skf_end_state_guard_names_each_broken_clause` (4 ids) reports exactly the broken clause. Disabling the `ides`
  clause makes `[ides-claude-code]` fail (probe exit 1, 1 failed).
- AC2 — holds. The no-binary branch returns 0 and prints nothing. `scripts/detectors.py` `run_one` maps rc 0 to `pass`
  whatever stdout says (`{0: "pass", 1: "FINDINGS"}`), so CAP-29's "silent" stands. With the ok print restored in a
  copy of the script, `test_runtime_mode_check_is_silent_without_claude_on_path` fails (exit 1).
- AC3 / AC4 — hold. The stub-`claude` cases are `old-runtime-warns` (2.1.276, rc 1), `unpinned-mode-warns`
  (2.1.300, rc 1) and `pinned-current-ok` (2.1.300, rc 0). `test_runtime_mode_check_could_not_run_on_a_missing_claude_path`
  asserts rc 2 and `could-not-run`. `pixi run -e pyforge-guild claude-instruction-mode-check` exits 0 on this host
  (2.1.314, pinned). `detectors.py --scope runtime --list` exits 0 and lists the check.
- AC5 — holds. `DUPLICATE_GUARD_FILES` = `POINTER_FILES` + every `.cursor/rules/*.mdc` + `CLAUDE.md`, and `CLAUDE.md`
  is not in `POINTER_FILES`. With `CLAUDE.md` dropped from the guard files, the planted-duplicate self-test fails
  (exit 1).
- AC6 — holds. Dropping the FIXME branch fails `[fixme]`; dropping the not-(yet-)landed branch fails `[not-yet-landed]`
  and `[not-landed]` (exit 1 each).
- AC7 — holds. The live block passes. Against `03a7aff5d9`'s `AGENTS.md`, only
  `test_managed_block_types_no_suite_member_or_skill_family_count` fails. With the match disabled, both planted ids
  fail.
- AC8 — holds. `customInstructions` is `["Follow the behavioural guidelines in AGENTS.md § Behavioural guidelines (every
  harness)."]`. With `03a7aff5d9`'s `settings.json`, `test_project_settings_custom_instructions_point_at_agents_md`
  fails.
- AC9 — holds. Each probe above failed with only its guarding test red, and the unmutated copy passes (49 passed). The
  station SKF marker checks exit 0: doctor, marshal and warden `test_skf_domain_skill.py` (6, 8 and 6 passed) and
  steward `test_skf_domain_skills.py` (6 passed). Mason's `test_persona_consults_cfe.py` exits 0 (19 passed).
- AC10 — holds, which closes the first review's failure.
  - `pixi run -e pyforge-scribe-pg scribe-pg-up` exits 0. `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`
    then exits 0 (460 passed, 12 skipped), and the parity test alone exits 0 (49 passed).
  - The memlog carries the surface-reconcile event that names the asserts and the CAP-27 success event (Story 23.2),
    then the `(capability)` CAP-27 entry that cites "Story 23.2's CAP-27 success event, the re-derive its AC10 names".
  - Two self-validate events are logged after it: Pass 1 (coherence) and Pass 2 (preservation). These are the two
    passes `bmad-spec` § Self-Validate requires, each recorded as an `--type event`.
  - `SPEC.md` was re-derived in `812d776dba`. CAP-27's intent and success are byte-identical to the memlog capability
    entry, as are CAP-29's and CAP-30's success. The file grows by one line (the `glossary.md` companion), as Pass 2
    states.
  - CAP-27's success names what 23.2 built: the three end-state clauses, `test_the_2026_09_26_skf_end_state_holds`,
    `test_skf_end_state_guard_names_each_broken_clause`, and mason's SKF-block assert left unrepeated. Every test
    function CAP-27, CAP-29 and CAP-30 name exists in the parity module.
- Station-tests routing (Dev Notes) — holds. `.github/workflows/pyforge-station-tests.yml`:384 routes
  `_bmad/skf/config.yaml` to the scribe job. `pixi run --frozen -e pyforge-steward pytest
  src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` exits 0 (51 passed).
- Verification — `governance-currency` exits 0, `spec-surface-check` exits 0 ("no drift"), and `story-status-check`
  exits 0 before this status edit.

Failures: none.

Carried, non-blocking:
- The first review's PyYAML observation still stands. The parity module imports `yaml` at module level, and PyYAML is
  still declared neither in `feature.pyforge-scribe.dependencies` nor in the scribe `pyproject.toml`.
- The ledger row `23-2-…` is still `backlog`. Promote it through the Tier-3 feed, then
  `sprint-ledger-sync -- --project pyforge-scribe`, then `story-status-check`.

## Dev Notes

- Review follow-up 2026-11-01 (station-tests routing): `SKF_CONFIG` in
  `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` reads `_bmad/skf/config.yaml`,
  which steward's trigger map (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`)
  derives as a scribe read, and `scribe_paths` in `.github/workflows/pyforge-station-tests.yml` did not carry it. It
  does now, so an edit there runs `scribe-test`. The test and its assertions are unchanged; the meta-test and
  `test_instruction_surface_parity.py` exit 0.

- Review follow-up 2026-11-01 (second review, non-blocking note): `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` no longer imports PyYAML, which no scribe manifest declares (it reached the env only through cocoindex -> watchdog); `_top_level_list` reads the top-level `ides` list of `_bmad/skf/config.yaml` with the stdlib (block and flow forms, comments, absent key). Checked: the parity file 49 passed; the live value is [`other`]; an `ides: [claude-code]` input still breaks the end-state check; ruff clean.
