---
title: "52.1: Herald's live-tree readers carry the live_tree marker"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate   # test markers and a marker registration, as doctor Story 55.4 and steward Story 117.4
difficulty: medium
story: '52.1'
spec: pyforge-herald
surface:
  - src/shared/packages/pyforge-herald/pyproject.toml
  - src/shared/packages/pyforge-herald/tests/integration/test_pptx_native_render.py
  - src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py
  - src/shared/packages/pyforge-herald/tests/meta/test_built_site_tests_install_first.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_lockfiles_current.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_qa_pixi_task.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_registry_sections.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_store_import_boundary.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_sync_all_pixi_task.py
  - src/shared/packages/pyforge-herald/tests/meta/test_deck_working_set.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site_imports_tracked.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py
  - src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py
  - src/shared/packages/pyforge-herald/tests/meta/test_dossier_golden.py
  - src/shared/packages/pyforge-herald/tests/meta/test_herald_pages_model.py
  - src/shared/packages/pyforge-herald/tests/meta/test_marketplace_mount.py
  - src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pages_site_url.py
  - src/shared/packages/pyforge-herald/tests/meta/test_portal_deck_status.py
  - src/shared/packages/pyforge-herald/tests/meta/test_portal_herald_guard.py
  - src/shared/packages/pyforge-herald/tests/meta/test_portal_import_boundary.py
  - src/shared/packages/pyforge-herald/tests/meta/test_pptx_native_live_decks.py
  - src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py
  - src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py
  - src/shared/packages/pyforge-herald/tests/meta/test_skf_skill_and_persona.py
  - src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py
  - src/shared/packages/pyforge-herald/tests/meta/test_twins_zero_origin.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_import_boundary.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_steward_schema_contract.py
  - src/shared/packages/pyforge-herald/tests/unit/test_ci_surfaces_tile_flag_states.py
  - src/shared/packages/pyforge-herald/tests/unit/test_cli_epic6.py
  - src/shared/packages/pyforge-herald/tests/unit/test_cli_watch.py
  - src/shared/packages/pyforge-herald/tests/unit/test_deck_status.py
  - src/shared/packages/pyforge-herald/tests/unit/test_docs_site_nav.py
  - src/shared/packages/pyforge-herald/tests/unit/test_docs_site_shelf_loader.py
  - src/shared/packages/pyforge-herald/tests/unit/test_dossier_structure.py
  - src/shared/packages/pyforge-herald/tests/unit/test_pptx_native.py
  - src/shared/packages/pyforge-herald/tests/unit/test_pptx_native_flag.py
  - src/shared/packages/pyforge-herald/tests/unit/test_status_pages_flag_states.py
  - src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py
  - src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - src/shared/packages/pyforge-herald/pyproject.toml
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Herald's tests bind to A's tree with no way to run the half that does not. The cutover readiness audit
found 46 of herald's 98 test files reading the live tree, and the `live_tree` split exists for steward and doctor
only (audit cross-cutting fault 4; SHOULD: tests as oracle).

**Approach:** A relay of `spec-pyforge-steward:CAP-175` (operator ruling D4 of 2026-10-27; the `live_tree` convention
of steward Story 117.4), with no herald CAP and no FR, as doctor Story 55.4. The change is test markers and one marker
registration; no test logic changes.

- **Marking.** Each module in `surface:` gets `pytestmark = pytest.mark.live_tree` at module level. Five of them
  already assign `pytestmark` (`tests/meta/test_dossier_golden.py`, `test_pages_artifact.py`,
  `test_herald_pages_model.py`, `test_marketplace_mount.py`, `tests/unit/test_docs_site_nav.py`); those become a
  list, which steward's `_live_tree_marked` reads. The package's two other `pytestmark` modules
  (`test_live_design_spike.py`, `test_webhook_live_smoke.py`) are opt-in live tests, not readers, and are not touched.
- **Registration.** `pyproject.toml`'s `[tool.pytest.ini_options] markers` gains the sentence steward and doctor use.
- **Which modules.** The surface is the 34 modules steward's static scanner names, plus five it misses: three import
  `tests/meta/pages_astro.py` from `tests/unit`, and two climb to the repository root. The off-tree run (AC4) is the
  arbiter. Any further module it names joins this story, except `tests/unit/test_local_ship.py` (Story 52.2), which
  must stay a package-half module.
- **Order.** This story runs first in the unit. Stories 50.3, 51.1 and 51.2 depend on it because their new or edited
  test modules use the marker it registers. Herald sets no `--strict-markers`, so the dependency is about one owner
  for the registration and the shared test files, not about a failing run.
- **The split itself** belongs to steward-station: the two pixi task halves (steward:S-124.1), the live-half CI job
  (steward:S-124.2) and `herald_live` in the trigger map. Until it lands, the marker selects nothing, and
  `pyforge-herald-test` collects as before.
- **One allowed logic edit, only on request.** `tests/meta/test_skf_skill_and_persona.py:384-395` judges the whole
  branch diff against `origin/main`. It fails on any changed path under `src/shared/packages/django-herald/` outside
  its marker tuple, and it asserts the sentence 'Lane 1 CMS stays steward' in the bmad-agent-herald persona. Both
  files are steward-station's in this PR. If steward-station asks, this story adds the named path to
  `_DJANGO_HERALD_DECK_EXPORT_MARKERS` with a dated comment; the persona assertion stays.

Ledger key: `52-1-herald-s-live-tree-readers-carry-the-live-tree-marker`.
Type / Effort / Deps: chore (`flag-exempt: detector-or-gate`) / M / —.

## Boundaries & Constraints

**Always:**
- Mark at module level, and turn an existing `pytestmark` into a list rather than replacing it.
- Treat the off-tree run as the arbiter of what is a live-tree reader.

**Never:**
- Never change test logic, except the one named edit, and only on request.
- Never mark `tests/unit/test_local_ship.py`.
- Never write the pixi task halves, the CI job or the trigger map (steward-station's), and never write the Spec or
  the memlog (Story 50.2 writes herald's reconcile line for these 43 files, one literal path each).

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — Every reader is marked.** Every herald test module with a derived outside read or root handoff is marked,
  by steward's own static scanner. Expected: exit 0, printing `[]` (the scanner names 34 modules on 2026-11-10).

```bash
pixi run -q -e pyforge-steward python - <<'EOF'
import subprocess,sys
sys.path.insert(0,'src/shared/packages/pyforge-steward/tests/meta')
import test_station_tests_trigger_map as tm
pkg='src/shared/packages/pyforge-herald'
bad=[]
for f in subprocess.check_output(['git','ls-files',pkg+'/tests'],text=True).split():
    if not f.rsplit('/',1)[1].startswith('test_'): continue
    s=tm.Scanner(pkg); s.scan(f)
    if (s.reads or s.handoffs) and not tm._live_tree_marked(f): bad.append(f)
print(bad); sys.exit(1 if bad else 0)
EOF
```

- **AC2 — The marker is registered.**
  `grep -c 'live_tree:' src/shared/packages/pyforge-herald/pyproject.toml`. Expected: prints `1`.
- **AC3 — The two halves collect what the task collected.** Run collect-only over `tests/unit` and `tests/meta` three
  times: with `-m 'not slow'`, with `-m 'live_tree and not slow'` and with `-m 'not live_tree and not slow'`, each
  under `pixi run -q -e pyforge-herald python -m pytest … --collect-only | tail -1`. Expected: three
  "N tests collected" lines, the second and third N summing to the first. This is a count read, not a verdict.
- **AC4 — The package half passes off the tree.** On a tree that holds only the three packages (the property B
  needs), the package half passes, named file by file. Expected: exit 0. The run passes the unmarked modules as
  arguments and uses no `-m 'not live_tree'`: `-m` deselects after collection, and
  `tests/meta/test_portal_herald_guard.py` and `test_preflight_pages_lane.py` fail at import there (exit 2). A module
  that fails in this run is a live-tree reader and takes the marker. The env's `bin` goes on `PATH` before the run, as
  pixi activation puts it there on B: `tests/unit/test_sync_all.py`'s `_run_bounded` tests spawn a bare `python`, and
  that needs the interpreter on `PATH`, not the live tree (amended 2026-11-11, Spec Change Log).

```bash
T=$(mktemp -d) && git archive HEAD src/shared/packages/pyforge-herald src/shared/packages/pyforge-core src/shared/packages/pyforge-testing-kit | tar -x -C "$T" && PY=$(pixi run -q -e pyforge-herald python -c 'import sys;print(sys.executable)') && (cd "$T" && FILES=$(grep -L 'pytest\.mark\.live_tree' src/shared/packages/pyforge-herald/tests/unit/test_*.py src/shared/packages/pyforge-herald/tests/meta/test_*.py) && export PYTHONPATH=src/shared/packages/pyforge-herald/src:src/shared/packages/pyforge-core/src:src/shared/packages/pyforge-testing-kit/src && export PATH="$(dirname "$PY"):$PATH" && env -u PYFORGE_FLAGS_PATH "$PY" -c "import pyforge.herald as h,sys; sys.exit(0 if h.__file__.startswith('$T') else 'pyforge.herald resolved outside the archive: '+h.__file__)" && env -u PYFORGE_FLAGS_PATH "$PY" -m pytest $FILES -q -m 'not slow' -p no:cacheprovider)
```

- **AC5 — The suite is unchanged where it runs today.**
  `pixi run -e pyforge-herald pyforge-herald-test && pixi run -e pyforge-guild lint-types`. Expected: exit 0.
- **AC6 — Post-condition, run by steward:S-124.2.**
  `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`.
  Expected: exit 0 once steward:S-124.2 has landed. Herald is unsplit there until steward-station's half lands, and
  marking alone changes nothing it reads.

</intent-contract>

## Binding

- No herald CAP or FR. A relay of `spec-pyforge-steward:CAP-175` (the `live_tree` convention of steward Story 117.4),
  as doctor Story 55.4.
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry.
- Epic 52. Ledger key `52-1-herald-s-live-tree-readers-carry-the-live-tree-marker`.
- Cross-station: steward:S-124.1 (the two task halves) and steward:S-124.2 (the live-half CI job and the trigger map)
  follow this story; neither gates it.
- Findings closed: SHOULD: tests as oracle (no `live_tree` split). `DW-herald-52-1-1` and `DW-herald-52-1-2` are this
  story's planned deferrals, and Story 50.2 writes them.

## Spec Change Log

- 2026-11-10: minted (backlog) from the station Dream's 2026-11-10 (cutover readiness) entry.
- 2026-11-11 (build review, round 2): AC4 amended. The command puts the env's `bin` on `PATH` before pytest
  (`export PATH="$(dirname "$PY"):$PATH"`). It ran `"$PY"` outside pixi activation, so three `_run_bounded` tests in
  `tests/unit/test_sync_all.py` could not find a bare `python` on a host with none on `PATH`. That is an interpreter
  lookup, not a live-tree read, and B runs its package half under pixi activation. The module stays unmarked and keeps
  its 54 tests in the package half. `surface:` gains three modules that the off-tree run named, as the Approach
  allows: `tests/meta/test_deck_store_import_boundary.py`, `tests/unit/test_cli_epic6.py` and
  `tests/unit/test_cli_watch.py`. That makes 43 files. The Planned deferral section gains `DW-herald-52-1-2`.
  `plan.json`'s AC4 command (Tier 3) still has the pre-amendment form; this spec is the source of record.

## Planned deferral (written at build)

The rows below are not in the deferred-work ledger yet. Story 50.2 writes each to
`planning-artifacts/deferred-work-ledger.md` and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-52-1-1`** (medium, open; location `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md`): Herald has no oracle on B: there is no src/packages/pyforge-herald there and no herald row in the case list. A side: seven package-half case rows are requested of control-plane (case-list.md). B side: it waits on the re-pin, because B is not re-pinned until the core, steward and marshal Specs pass a truth sweep (ruling 1 of 2026-11-10). The python-foundry repository is out of scope for every unit of this change.
- **`DW-herald-52-1-2`** (low, open; location `src/shared/packages/pyforge-herald/tests/unit/test_cli_epic6.py`, with `test_cli_watch.py` beside it; added 2026-11-11 by the round 2 build review): Two whole modules sit in the live-tree half because of two tests: 31 of the 32 tests in `test_cli_epic6.py` and 8 of the 9 in `test_cli_watch.py` are pure CLI-dispatcher tests that B's package half loses. The two that need it are `test_cli_epic6::test_json_flag_renders_error_as_json_on_stderr` and `test_cli_watch::test_deck_watch_success_returns_0_and_prints_nothing_to_stderr`. Off the tree they fail on the 'no flag tree' WARN that `pyforge.core.flags` writes to stderr, because the flag tree is found by climbing to `src/platform/config/flags.json`. Fix: pin a fixture flag tree for those two tests (`pyforge.testing_kit.flags.flagd_tree` or `PYFORGE_FLAGS_PATH`), then drop both modules' `live_tree` marker, so they return to the package half. A herald story owns the fix, because it is a test-logic change and Story 52.1 forbids those.

## Review findings (build, round 1, 2026-11-11)

An independent review failed the first build attempt. This section lists each finding and what this round did about
it. The reviewer's facts were re-checked in this round and hold. The marked set is unchanged: 43 files, the 40 in
`surface:` and the three named in finding 2.

1. **Major. Where:** the AC4 command, and `tests/unit/test_sync_all.py:1098-1125`, which is outside `surface:`.
   **Problem:** AC4 as written exits 1 on a host with no `python` on PATH. It runs `"$PY"` outside pixi
   activation, and three `_run_bounded` tests spawn a bare `python` (`[Errno 2] No such file or directory:
   'python'`). AC4's own rule would mark the module, but it does not read the live tree. It fails the same way in the
   live tree without activation, and the off-tree run passes once the env's `bin` is on PATH (1509 passed, 5
   skipped). **This round:** the module is not marked, because marking it would take all 54 of its tests out of B's
   package half. Two fixes exist, and neither belongs to this story. Amending AC4, with its Spec Change Log line, is
   outside the body sections this round may edit. Routing `python` to `sys.executable` is a logic change, in a file
   this story does not own. The gate or the operator chooses one of them:
   (a) amend AC4 to `export PATH="$(dirname "$PY"):$PATH"` before the pytest call, and add a dated Spec Change Log
   line that records the deviation; or
   (b) give a herald story or DW row of its own the job of routing `python` to `sys.executable` in
   `test_sync_all.py`.
   Until one of them lands, AC4 reads red on exactly these three tests, and on nothing else.
2. **Minor. Where:** `tests/meta/test_deck_store_import_boundary.py`, `tests/unit/test_cli_epic6.py` and
   `tests/unit/test_cli_watch.py`, together with `surface:` and Story 50.2's reconcile line.
   **Problem:** the three modules are marked but are outside `surface:` and `files_owned`. Each fails off-tree when
   unmarked. `test_deck_store_import_boundary` raises `StopIteration` at import, from its climb to the root. One test
   in each of the other two fails on the 'no flag tree' WARN that `pyforge.core.flags` writes to stderr. AC4 is the
   arbiter, so they join this story, and no other story owns them. `surface:` and Story 50.2's reconcile line
   ("for these 40 files") do not name them yet.
   **This round:** no change. The gate commits all 43 files. Story 50.2 writes one literal-path reconcile entry per
   moved file, 43 in all. Whoever owns the frontmatter adds the three paths to `surface:`.
3. **Minor. Where:** `tests/unit/test_cli_epic6.py` (32 tests) and `tests/unit/test_cli_watch.py` (9 tests).
   **Problem:** marking is module-level, so 39 pure CLI-dispatcher tests move to the live-tree half because of 2
   tests that depend on the flag tree. B's package half loses those 39. No AC breaks, but the move works against the
   'tests as oracle' finding.
   **This round:** no change, because a logic edit is forbidden here. Follow-up, for Story 50.2 or a later herald
   story: a DW row to pin a fixture flag tree for those two tests (`pyforge.testing_kit.flags.flagd_tree` or
   `PYFORGE_FLAGS_PATH`), so both modules can return to the package half.
4. **Minor. Where:** AC6, steward's `tests/meta/test_station_tests_trigger_map.py`.
   **Problem:** AC6 is red with 4 failures. All four come from marshal modules that another unit's in-flight work
   touched, and none involves herald.
   **This round:** no change. AC6 is steward:S-124.2's post-condition, and that story or the marshal unit resolves
   the failures before AC6 is judged.

## Review findings (build, round 2, 2026-11-11)

The independent review failed round 1 again. The reviewer's facts were re-checked and hold. This round fixes the
major and the first two minors in this spec. The fourth minor needs nothing from this story. The marked set is
unchanged: 42 test modules and `pyproject.toml`, 43 files in all.

1. **Major. Where:** the AC4 command, and `tests/unit/test_sync_all.py:1098-1125`, which is outside `surface:`.
   **Problem:** round 1's major was still open. AC4 runs `"$PY"` outside pixi activation, so on a host with no
   `python` on `PATH` it exits 1: 3 failed, 1506 passed and 5 skipped. All three failures are `_run_bounded` tests
   that spawn a bare `python`. No named story carried the deferral, and AC4's own rule was applied unevenly: three
   modules outside `surface:` were marked, but `test_sync_all` was not, and no deviation was recorded.
   **This round:** fixed by the reviewer's option (a). AC4 now runs `export PATH="$(dirname "$PY"):$PATH"` before
   the pytest call, its prose says why, and the Spec Change Log line of 2026-11-11 records the amendment.
   `test_sync_all.py` stays unmarked, because it reads no tree. Marking it would take its 54 tests out of B's package
   half. The amended AC4 was re-run as a working-tree twin, because HEAD does not hold the edits. Before the run, `command -v python`
   found none on `PATH`. Result: exit 0, 1509 passed and 5 skipped, over 56 unmarked modules. `plan.json`'s AC4
   (Tier 3, not this story's file) still has the pre-amendment command. A literal re-run of that form exits 1 on this
   host for the reason above. This spec is the source of record.
2. **Minor. Where:** the frontmatter `surface:`, `plan.json`'s `files_owned`, and the reconcile line ("these 40
   files").
   **Problem:** `tests/meta/test_deck_store_import_boundary.py`, `tests/unit/test_cli_epic6.py` and
   `tests/unit/test_cli_watch.py` are marked but were in neither `surface:` nor `files_owned`.
   **This round:** fixed in this spec. `surface:` gains the three paths, so it now names exactly the 43 herald
   files the diff changes, checked against `git diff --name-only`. The Boundaries line reads "these 43 files, one
   literal path each". The `files_owned` list in `plan.json` is Tier 3 and not this story's to edit. Story 50.2's
   reconcile writes one literal-path entry per moved file, 43 in all.
3. **Minor. Where:** `tests/unit/test_cli_epic6.py` (32 tests) and `tests/unit/test_cli_watch.py` (9 tests).
   **Problem:** 39 pure CLI-dispatcher tests leave B's package half because of 2 flag-tree tests, and only prose
   tracked the follow-up.
   **This round:** tracked as the planned deferral `DW-herald-52-1-2` (low) in § Planned deferral, which Story 50.2
   writes to the ledger with this spec's `deferred:` entry. The Binding line names both rows. The fix itself is a
   test-logic edit, which this story forbids, so a herald story owns it. Spec-50-2's explicit id list (its (i) and
   its ledger-grep AC) names `DW-herald-52-1-1` but not `-2` yet. That spec is Story 50.2's to amend.
4. **Minor. Where:** AC6, steward's `tests/meta/test_station_tests_trigger_map.py`.
   **Problem:** AC6 exits 1, with 4 failed and 47 passed. All four are marshal: `test_dispatch_landing.py` reads
   `pyforge-doctor/src`, and `ROOT_HANDOFF_INPUTS` names `test_chain_regen.py` and `test_dispatch_verification.py`.
   None involves herald.
   **This round:** no change, and the reviewer agrees. AC6 is steward:S-124.2's post-condition. Re-run this round:
   still 4 failed and 47 passed, all marshal.
