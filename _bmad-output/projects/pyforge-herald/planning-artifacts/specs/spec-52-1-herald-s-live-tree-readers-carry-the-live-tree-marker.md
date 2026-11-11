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
  the memlog (Story 50.2 writes herald's reconcile line for these 40 files).

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
  that fails in this run is a live-tree reader and takes the marker.

```bash
T=$(mktemp -d) && git archive HEAD src/shared/packages/pyforge-herald src/shared/packages/pyforge-core src/shared/packages/pyforge-testing-kit | tar -x -C "$T" && PY=$(pixi run -q -e pyforge-herald python -c 'import sys;print(sys.executable)') && (cd "$T" && FILES=$(grep -L 'pytest\.mark\.live_tree' src/shared/packages/pyforge-herald/tests/unit/test_*.py src/shared/packages/pyforge-herald/tests/meta/test_*.py) && export PYTHONPATH=src/shared/packages/pyforge-herald/src:src/shared/packages/pyforge-core/src:src/shared/packages/pyforge-testing-kit/src && env -u PYFORGE_FLAGS_PATH "$PY" -c "import pyforge.herald as h,sys; sys.exit(0 if h.__file__.startswith('$T') else 'pyforge.herald resolved outside the archive: '+h.__file__)" && env -u PYFORGE_FLAGS_PATH "$PY" -m pytest $FILES -q -m 'not slow' -p no:cacheprovider)
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
- Findings closed: SHOULD: tests as oracle (no `live_tree` split). `DW-herald-52-1-1` is this story's planned
  deferral, and Story 50.2 writes it.

## Spec Change Log

- 2026-11-10: minted (backlog) from the station Dream's 2026-11-10 (cutover readiness) entry.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet. Story 50.2 writes it to
`planning-artifacts/deferred-work-ledger.md` and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-52-1-1`** (medium, open; location `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md`): Herald has no oracle on B: there is no src/packages/pyforge-herald there and no herald row in the case list. A side: seven package-half case rows are requested of control-plane (case-list.md). B side: it waits on the re-pin, because B is not re-pinned until the core, steward and marshal Specs pass a truth sweep (ruling 1 of 2026-11-10). The python-foundry repository is out of scope for every unit of this change.
