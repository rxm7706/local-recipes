---
title: '23.2: The instruction-surface guards prove every clause they claim'
type: 'fix'
created: '2026-11-01'
status: 'backlog'
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

Status: backlog
