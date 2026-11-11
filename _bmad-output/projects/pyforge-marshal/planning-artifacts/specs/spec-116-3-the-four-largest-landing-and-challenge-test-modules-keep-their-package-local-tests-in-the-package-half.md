---
title: "116.3: The four largest landing and challenge test modules keep their package-local tests in the package half"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '116.3'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marking the four largest candidate modules whole would move about 420 tests out of the package half for the few that read the tree: `test_dispatch_landing.py` (137), `test_dispatch_land_heal.py` (132), `test_factory_challenge.py` (79) and `test_dispatch_verify_fix.py` (72).

**Approach:** Each of the four splits: its reading tests move to a `*_live_tree.py` sibling. `test_dispatch_landing.py` is rewritten by Story 115.2 first (its Doctor fakes), hence the order through Story 116.2. A fixture literal that names a tracked path is rewritten as a path join or a made-up name when it only names a fixture (steward's `scan_strings` reads a bare three-segment literal of a tracked path as a read; doctor Story 58.1's practice); a test whose literal cannot change moves to the live sibling with its reason in this spec. Shared helpers go to a private module under `tests/unit/` only when both files need them.

Ledger key: `116-3-the-four-largest-landing-and-challenge-test-modules-keep-their-package-local-tests-in-the-package-half`. Type / Effort / Deps: chore / L / S-116.2.

## Boundaries & Constraints

**Always:**
- None of the four is marked `live_tree`; each sibling is.

**Never:**
- Never delete, skip or re-mark a test to make a half pass.

## Acceptance Criteria

- **AC1 — Each of the four keeps its package-local tests unmarked and has a marked live sibling only if it read the tree.**

  ```bash
  for m in src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py; do ! grep -q '^pytestmark = .*live_tree' $m || exit 1; s=${m%.py}_live_tree.py; test ! -e $s || grep -q '^pytestmark = pytest.mark.live_tree' $s || exit 1; done
  ```

  Expected: exit 0.

- **AC2 — Steward's derivation finds no outside read in marshal's package half.**

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -k 'package_half_reads_nothing'
  ```

  Expected: exit 0, with the `[marshal]` case among the passed.

- **AC3 — The partition and the 90% floor still hold.**

  ```bash
  python3 -c "import subprocess,re,sys;n=lambda m:int(re.search(r'(\d+)(?:/\d+)? tests? collected',subprocess.run(['pixi','run','--frozen','-e','pyforge-marshal','pytest','src/shared/packages/pyforge-marshal/tests','--collect-only','-q','-p','no:cacheprovider','-m',m],capture_output=True,text=True).stdout).group(1));a=n('not slow and not live_tree');b=n('live_tree and not slow');c=n('not slow');print(a,b,c,round(a/c,3));sys.exit(0 if a+b==c and b>0 and a>=0.9*c else 1)"
  ```

  Expected: exit 0.

- **AC4 — No test was lost.**

  ```bash
  python3 -c "import subprocess,re,pathlib,sys;rx=re.compile(r'^\s*(?:async )?def test_',re.M);h=sum(len(rx.findall(p.read_text())) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('*.py'));fs=[f for f in subprocess.run(['git','ls-tree','-r','--name-only','origin/main','src/shared/packages/pyforge-marshal/tests'],capture_output=True,text=True).stdout.split() if f.endswith('.py')];b=sum(len(rx.findall(subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True).stdout)) for f in fs);print(b,h);sys.exit(0 if h>=b else 1)"
  ```

  Expected: exit 0.

- **AC5 — Both halves pass, selected by marker.**

  ```bash
  pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta -q -m 'not slow and not live_tree' && pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src:scripts pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta src/shared/packages/pyforge-marshal/tests/integration -q -m 'live_tree and not slow'
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1). FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.3: The four largest landing and challenge test modules keep their package-local tests in the package half`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Cross-station: steward:S-124.1 adds the task halves after the last marking story; doctor:S-58.1 is the precedent for rewriting fixture literals.

## Split record (written at build)

Built 2026-11-11 on `cutover-readiness-2026-11-10` (base `e779f64d01`). All paths are under
`src/shared/packages/pyforge-marshal/tests/unit/`.

**How the reading tests were found.** Two sources, which agree. Steward's derivation (`Scanner` in
`test_station_tests_trigger_map.py`), run over each module and attributed to the top-level definition that causes
each read, named the static reads. Story 116.2's whole-package off-tree run (the package copied into an empty git
repository, `PYTHONPATH` on the copy's `src`) named 32 failures in these four modules. Those 32 tests read the tree at
run time; all 32 moved and no other test did. The derivation sees only the first test that calls a reading helper
(it caches each inlined call), so the off-tree run is the full list.

**What moved.** Each sibling carries `pytestmark = pytest.mark.live_tree` and finds the root with `_repo_root()`
(`Path(__file__).resolve().parents[6]`) when a test runs, never at import. A missing file fails the test; none skips.
Helpers only the moved tests use moved with them. Helpers both files use stay in the module, and the sibling imports
them by name, as Story 116.2's siblings do. No private support module was needed.

| Module | Tests before | Stay | Moved to `*_live_tree.py` | What the moved tests read |
|---|---|---|---|---|
| `test_dispatch_landing.py` | 141 | 138 | 3 | `scripts/spec_surface_check.py` (patched to the fixture's root) and `_bmad/scripts/memlog.py` (copied) build the co-governor fixture repository |
| `test_dispatch_land_heal.py` | 132 | 125 | 7 (12 cases) | pyforge-marshal's `deferred-work-ledger.md` and `.claude/memory/MEMORY.md`, each the union base |
| `test_factory_challenge.py` | 79 | 74 | 5 | `.claude/settings.json`, `_bmad/custom/bmad-retrospective.toml`, and every station's tracked `marshal-policy.toml` with the repo default, which `compose_effective` and `conventional_project_policy_path` resolve from the root |
| `test_dispatch_verify_fix.py` | 72 | 67 | 5 (12 cases) | `docs/how-to/troubleshoot-bmad-agent-loops.md` (read from the cwd, as before), and the root handed to `load_profiles` for the `_bmad-output/harness-profiles/cursor.toml` overlay |

The moved tests, by sibling:

- `test_dispatch_landing_live_tree.py`: `test_reconcile_spec_surface_drift_reconciles_co_governor_doctor_cleared_by_overlap_tolerance`,
  `test_reconcile_spec_surface_drift_without_stamp_refusal_expansion_leaves_co_governor_unnamed`,
  `test_own_path_stamp_refusals_names_co_governor_when_station_memlog_cleared_doctor_verdict`. The module used to
  find the root at import (`_REPO_ROOT_FOR_STAMP`, `_STAMP_SCRIPT`); the sibling finds it in the helper.
- `test_dispatch_land_heal_live_tree.py`: `test_union_deferred_work_texts_live_marshal_ledger_mixed_formats`,
  `test_union_deferred_work_texts_refuses_legacy_entry_edit_on_live_ledger`,
  `test_union_team_memory_index_texts_live_memory_md_parallel_appends` (3 cases),
  `test_union_team_memory_index_texts_unchanged_returns_main_bytes`, `test_branch_preamble_append_is_kept`,
  `test_union_team_memory_index_texts_branch_lines_in_two_sections`,
  `test_union_team_memory_index_texts_keeps_non_newline_line_separators` (4 cases).
- `test_factory_challenge_live_tree.py`: `test_the_repo_pins_and_enables_the_plugin`,
  `test_a_sonnet_renders_on_all_eight_live_stations`, `test_the_catalog_sonnet_is_an_id_claude_launches`,
  `test_the_documented_example_renders_and_marshal_s_frontier_model_refuses_on_marshal`,
  `test_the_retrospective_override_names_the_drift_verb`.
- `test_dispatch_verify_fix_live_tree.py`: `test_troubleshoot_doc_names_fix_turn_gates`,
  `test_no_shipped_fix_template_carries_a_prompt_on_argv` (6 cases), `test_cursor_declares_no_resume_template`,
  `test_the_fix_turn_launch_feeds_the_prompt_on_stdin_from_a_private_file` (3 cases),
  `test_the_prompt_file_is_rewritten_0600_when_it_already_exists`. Each of the last four takes its profile from
  `_fix_profiles()`, which loads the repository overlay; the module used to find that root at import (`_REPO_ROOT`).

No test moved for a literal alone, so no reason for one is owed here.

**Literal joins (package half).** In the four modules every remaining path literal that names a tracked file is
joined from its segments (`"/".join((...))`), with one comment after the imports saying so. Each names a fixture
path in a temp repository or a fake (conflict paths, the flag-registry quartet, the ledger and memlog paths, the
spec workspaces under the fixture `repo`) or a value the code under test prints (the Doctor bootstrap's path, the
memlog command, the flag checklist). The values are unchanged. 16 in `test_dispatch_landing.py`, 30 in
`test_dispatch_land_heal.py`, 4 in `test_factory_challenge.py` and 1 in `test_dispatch_verify_fix.py`.

**Evidence at build.**

- The derivation over marshal's unmarked modules (the package half; the new siblings added to its file list, since
  they are untracked until the wave commit) finds no read and no hand-off: `reads == {}`, `handoffs == []`.
  Before this story it named these four modules and the hand-off `test_dispatch_verify_fix.py`.
- Off-tree: the four modules and their siblings, copied with the whole package into an empty git repository and run
  with `-m 'not slow and not live_tree'`, give 578 passed and 32 deselected; the siblings import there. The same
  copy with `-m 'live_tree and not slow'` fails all 32 moved tests, none skipped.
- Collected (AC3): 13820 in the package half, 442 in the live half, 14262 in all; the package half keeps 96.9%.
  Story 116.2 left 13852 and 410. Test functions (AC4): 8279 on this branch, 8188 on `origin/main`.

**For steward S-124.2 (`ROOT_HANDOFF_INPUTS`).** The live half's hand-off files now include
`unit/test_dispatch_verify_fix_live_tree.py` (the `HARNESS_PROFILES` group), in place of
`unit/test_dispatch_verify_fix.py`, which hands nothing now. The live half's derived hand-offs are 17 files: Story
116.2's 16 and this one. Steward's `test_root_handoffs_are_declared_exactly` was already red on this branch before
this story (51 items across stations); the re-key is S-124.2's.

**AC2 at build.** `test_the_package_half_reads_nothing_outside_its_package` is parametrized over the stations whose
workflow has a `<s>_live` job, which marshal does not have until steward S-124.1 and S-124.2 add it. So no `[marshal]`
case exists yet, and the command's two cases, `[doctor]` and `[steward]`, fail on reads in those packages
(`pyforge-doctor/tests/unit/test_sources_writer_lock.py`; steward's `test_cutover_ledger.py`,
`test_cutover_ledger_check.py`, `test_portability.py` and others), committed by other stories of this branch. The
derivation above is the `[marshal]` case's assertion, run by hand; AC2 is judged once S-124.2 lands.

**Outside this story's files.** None is edited here. The closer (Story 116.5) or each file's owner can re-point them.

- `spec-pyforge-marshal/SPEC.md`, CAP-299's success, names
  `test_the_documented_example_renders_and_marshal_s_frontier_model_refuses_on_marshal` under
  `tests/unit/test_factory_challenge.py`, and CAP-301's success names
  `test_the_retrospective_override_names_the_drift_verb` there. Both now sit in `test_factory_challenge_live_tree.py`,
  and once S-124.1 lands they run under the live task, not `pyforge-marshal-test`, which both successes name.
- Name only, history: `specs/spec-83-13-the-landing-heal-keeps-the-team-memory-index-s-blank-lines.md` (76-82) and
  the append-only `spec-pyforge-marshal/.memlog.md` (1734, 2272, 2274, 2285, 2292, 2374) name moved tests of
  `test_dispatch_land_heal.py` and `test_factory_challenge.py`. No tracked file cites a node id into the four modules.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
