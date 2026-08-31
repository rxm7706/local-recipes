---
title: 'A source registry Doctor owns'
type: 'feature'
created: '2026-08-08'
status: 'done'
baseline_revision: 'cbd965110b4b804fe9e75d40e6e1420fe0ee903a'
final_revision: '3bb4ecdb9154eb295ac02c9d00fb2644ef9cd5c4'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-6-context.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pyforge.doctor.sources.__init__` is empty, so nothing declares which
station's artifact each `Source` judges or which station owns/implements it — the
fleet's detector-ownership audit (Charter §6 / INV-4) has no place to land, and
`scripts/detectors.py`'s file-scanning discovery cannot see a source that already
lives inside Doctor's own package.

**Approach:** Give Doctor an explicit, validated registry (scope + subject station +
owning station per `Source` member) that fails at construction when a subject or
owner is missing, covering today's 9 sources; extend `scripts/detectors.py`'s
enumeration to also read from it.

## Boundaries & Constraints

**Always:**
- The registry lives in `pyforge.doctor.sources` (the currently-empty
  `sources/__init__.py`). Each entry is validated at construction: a falsy
  `subject_station` or `owning_station`, or a `scope` outside `{"repo", "runtime"}`,
  raises `ValueError` immediately — never a default or placeholder value.
- The registry covers every current `Source` member (all 9 in `models.py`). A test
  enforces exact set-equality, in both directions, between `Source`'s members and
  the registry's declared sources — a `Source` with no registry entry, or a registry
  entry with no matching `Source`, fails that test.
- `scripts/detectors.py` gains visibility into Doctor-owned sources by importing
  `pyforge.doctor.sources` directly (never AST-scanning Doctor's installed package)
  and degrades to reporting none — not crashing, not raising a registry finding —
  when the package isn't importable in the active environment.
- `models.py` changes only `Source`'s docstring, pointing at the new registry;
  enum membership is unchanged by this story.

**Block If:** none — this is a pure additive mechanism with no destructive or
ambiguous choice that needs human sign-off.

**Never:**
- Add any of the 10 not-yet-implemented detector identities (`ledger_regression`,
  `story_status`, `chain_completeness`, `dashboard_drift`, `check_layout`,
  `dream_chain`, `spec_surface`, `forward_dependency`, `deferred_work`,
  `bmad_drift`) to `Source` in this story — they land with their own `gather()` in
  Stories 6.4–6.9, each responsible for registering its own entry.
- Change `scripts/detectors.py`'s AST-scan, `run_one`, or exit-code semantics for
  existing `scripts/*_check.py` / `docs/dashboard/check_*.py` files.
- Import anything from a `scripts/*.py` module (e.g. `bmad_drift_check.STATIONS`)
  into `pyforge.doctor` — station names here are Doctor's own literals; unifying
  them with the script-side `STATIONS` tuple is Story 6.8's scope.
- Touch `checks/registry.py`, any `sources/*.py` `gather()` implementation, or the
  `check`/`monitor`/`diagnose` CLI verbs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Well-formed entry | `SourceRegistration(source=Source.MARSHAL_DURABILITY, scope="repo", subject_station="marshal", owning_station="doctor")` | Constructs; appears in `list_sources()` | No error expected |
| Missing subject | `subject_station=""` (or `None`) | Raises `ValueError` at construction | Fail loud, no default |
| Missing owner | `owning_station=""` (or `None`) | Raises `ValueError` at construction | Fail loud, no default |
| Invalid scope | `scope="hostile"` | Raises `ValueError` at construction | Fail loud |
| Registry ↔ enum coherence | A `Source` member with no `REGISTRY` entry (simulated) | Coherence test fails | Test failure surfaces the gap, never a silent pass |
| `scripts/detectors.py`, package present | `pyforge.doctor` importable in the active env | `--list`/`--json` output includes a `doctor_sources` row per `REGISTRY` entry (scope/subject/owner) | No error expected |
| `scripts/detectors.py`, package absent | `pyforge.doctor` not importable in the active env | `doctor_sources` is an empty list | No crash, no registry finding |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` --
  currently empty; becomes the registry this story builds.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `Source`
  StrEnum (9 members today); docstring gains a pointer to the new registry, no
  member changes.
- `scripts/detectors.py` -- repo-root fleet detector CLI; its `discover()`/`--list`
  gains a Doctor-registry-backed section alongside the existing file scan.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` --
  pattern reference only (frozen-dataclass catalog + `list_*` accessor +
  "every X has exactly one Y" coherence test via
  `test_every_cataloged_category_is_dispatchable_by_gather_one`). Not modified.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` --
  docstring-style reference for how a source module states its independence
  rationale. Not modified.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` --
  add a frozen `SourceRegistration` dataclass (`source: Source`, `scope: str`,
  `subject_station: str`, `owning_station: str`) whose `__post_init__` raises
  `ValueError` when `subject_station`/`owning_station` is falsy or `scope` is not
  `"repo"`/`"runtime"`; populate `REGISTRY: tuple[SourceRegistration, ...]` for all
  9 current `Source` members; add `list_sources() -> tuple[SourceRegistration, ...]`
  -- gives Doctor an explicit, validated place to declare who owns and who is
  judged by every source.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add one
  docstring line under `Source` pointing at `doctor.sources.REGISTRY` as where each
  member's scope/subject/owner is now declared -- keeps the taxonomy's own
  documentation from going stale the moment the registry exists.
- [x] `scripts/detectors.py` -- add a `_doctor_sources() -> list[dict]` helper that
  imports `pyforge.doctor.sources` inside a `try/except ImportError` (returns `[]`
  on failure) and maps `list_sources()` into row dicts carrying `scope`,
  `subject_station`, `owning_station`; include the result under a new
  `doctor_sources` key in `--list --json` output and a matching section in the
  human-readable `--list` -- closes the blind spot where a source already living
  inside Doctor's package (e.g. `marshal-durability`) is invisible to the fleet's
  one detector-discovery tool.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py`
  (new) -- unit tests for `SourceRegistration` validation (empty subject raises,
  empty owner raises, bad scope raises) and a coherence test asserting
  `{m.value for m in Source}` and `{r.source.value for r in REGISTRY}` are
  set-equal -- proves "no default" and "every source enumerable" together, and
  becomes the tripwire that forces every future `Source` addition to register.
- [x] `tests/scripts/test_detectors_doctor_sources.py` (new, repo-root) -- tests
  `_doctor_sources()`'s two branches: package importable (rows come back with
  scope/subject/owner, one per current `Source` member) and package not importable
  (simulated import failure returns `[]`, no exception) -- proves the merge
  degrades rather than crashes when `pyforge-doctor` isn't installed in the
  running env.

**Acceptance Criteria:**
- Given the current 9 `Source` members, when `sources.REGISTRY` is built, then
  every member has exactly one entry with a non-empty `subject_station` and
  `owning_station` and a `scope` of `"repo"` or `"runtime"`.
- Given a `SourceRegistration` constructed with an empty `subject_station`, when
  construction runs, then it raises `ValueError` immediately rather than storing
  an empty or default value.
- Given `Source` and `sources.REGISTRY`, when their declared source sets are
  compared, then they are identical in both directions.
- Given `pyforge.doctor` is importable, when `python scripts/detectors.py --list
  --json` runs, then its output includes a `doctor_sources` entry for every
  `REGISTRY` row, each carrying `scope`, `subject_station`, and `owning_station`.
- Given `pyforge.doctor` is NOT importable in the active environment, when
  `python scripts/detectors.py --list` runs, then it completes with an empty
  `doctor_sources` section rather than raising or reporting a registry finding.
- Given this story lands, when `doctor check` is measured, then it remains within
  its 5.0s SM-C1 budget (this story adds no new gather to any CLI verb).

## Spec Change Log

## Review Triage Log

### 2026-08-08 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 3, low 5)
- defer: 1 (high 0, medium 1, low 0)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` `scripts/detectors.py`'s `--list`/`--json` gave no way to
    tell "zero Doctor sources" from "`pyforge.doctor` isn't importable here" —
    the common case in the default `local-recipes` env and the `detectors.yml`
    CI workflow (verified: neither installs `pyforge-doctor`). Added a
    `doctor_sources_available` boolean to both output modes.
  - `[medium]` `[patch]` `SourceRegistration.__post_init__` never validated
    `source` is actually a `Source` member (mirrors `models.Finding`'s own
    coercion pattern, which this dataclass otherwise imitates). Added an
    `isinstance` check so a bad `source` fails at the same construction site
    instead of a confusing `AttributeError` downstream.
  - `[medium]` `[patch]` The new `tests/scripts/test_detectors_doctor_sources.py`
    had no pixi task, unlike `tests/packaging`'s `pyforge-deps-test` precedent —
    nothing in the repo's automation would ever run it again. Added
    `pyforge-doctor-scripts-test` under `feature.pyforge-ci`.
  - `[low]` `[patch]` `__post_init__`'s emptiness check accepted a
    whitespace-only `subject_station`/`owning_station` (e.g. `" "`) as
    "declared," contradicting the AC's "no default" intent. Added `.strip()`.
  - `[low]` `[patch]` No public `to_json_dict()` on `SourceRegistration`, unlike
    every other data shape in `models.py`; `scripts/detectors.py` hand-rebuilt
    the same four-field dict. Added the method, used it from `detectors.py`.
  - `[low]` `[patch]` The module docstring in `sources/__init__.py` and the
    docstring on `scripts/detectors.py::_doctor_sources` overclaimed parity with
    `discover()`'s "unknown, never green" discipline; the two are not actually
    parallel (discover() surfaces a loud finding + exit 1, `_doctor_sources`
    was silent + exit 0 before the availability-flag patch above). Reworded
    both to state the actual, intentionally different behavior.
  - `[low]` `[patch]` No test exercised the human-readable `--list` print loop
    for the new section, only the private `_doctor_sources()` helper. Added a
    subprocess-based smoke test asserting the section and its fields appear.
  - `[low]` `[patch]` `epics.md` still showed Story 6.2 as `backlog` with no
    outcome, unlike Story 6.1's dated Outcome note in the same file, and
    `sprint-status.yaml` still had `6-2-a-source-registry-doctor-owns: backlog`.
    Updated both to `done` once verification passed.
  - `[medium]` `[defer]` `Source.BEHIND_UPSTREAM` has no backing `gather()`
    implementation anywhere in `pyforge.doctor` — `atlas.py`'s `_VALID_AXES` is
    only `{staleness, cve, abandonment, adoption}`; `abandonment` produces
    `FEEDSTOCK_HEALTH` + `RELEASE_CADENCE`, and nothing produces
    `BEHIND_UPSTREAM`. Pre-existing since whichever Epic 2 story introduced the
    enum member; surfaced incidentally by this story's coherence test, which
    now makes a concrete claim about a Source no code path ever emits. Logged
    to the deferred-work ledger, not fixed here (out of this story's surface).
  - `[reject]` "discovery no longer depends on AST-scanning" isn't advanced for
    the 10 audit-motivated detectors (`ledger_regression_check` etc.) — correct
    per this story's explicit, documented scope (Deps: S-6.1 only; 6.4-6.9 own
    the actual migrations, per their own surface lines and this spec's Design
    Notes).
  - `[reject]` Two unlinked `{"repo","runtime"}` scope-set definitions
    (`scripts/detectors.py::SCOPES` vs `sources/__init__.py::_VALID_SCOPES`) —
    the correct consequence of this story's own "never import `scripts/*.py`
    into `pyforge.doctor`" boundary, not a defect.
  - `[reject]` Hardcoded `:<8` column width in the new print loop — matches the
    same file's pre-existing `d['name']:22` convention two lines above; not a
    new anti-pattern.
  - `[reject]` No coupling test forcing a future `REGISTRY` entry to have a
    real `gather()` dispatch (unlike `checks/registry.py`'s explicit warning) —
    legitimate for Stories 6.4+ (each owns its own registration + dispatch);
    all 9 of this story's own entries are already backed except the
    pre-existing BEHIND_UPSTREAM gap (see defer above).
  - `[reject]` Possible future overlap between `discover()`'s AST-scanned
    detectors and `sources.REGISTRY` once a script's logic moves into Doctor —
    zero overlap exists today (verified: no current `REGISTRY` entry
    corresponds to any `scripts/*_check.py` file); a Story 6.9 transition
    concern, already flagged in this spec's Design Notes.

## Design Notes

This story is the registry MECHANISM only. It does not move any
`scripts/*_check.py` detector's logic into `pyforge.doctor.sources`, and it does
not add the 10 not-yet-implemented `Source` identities Stories 6.4–6.9 land
(`ledger_regression`, `story_status`, …). Each of those stories adds its own new
`Source` member alongside its own `gather()` implementation and registers it; the
coherence test built here turns forgetting that registration into a test failure
instead of a silent gap — mirroring `checks/registry.py`'s existing "every
cataloged category is dispatchable by `gather_one`" tripwire
(`tests/unit/test_checks_registry.py::test_every_cataloged_category_is_dispatchable_by_gather_one`).

Subject/owner assignment for the 9 existing sources (all `owning_station="doctor"`,
all `scope="repo"` — none of today's 9 read host/tmux state):
- `warden-doctor` → subject `"warden"` (relays warden's own environment
  self-report; not a judgment of an artifact — AD-11's existing exception,
  unaffected by this story).
- `staleness-report`, `cve-watcher`, `behind-upstream`, `feedstock-health`,
  `release-cadence`, `adoption` → subject `"atlas"` (all read `cf_atlas.db` /
  Atlas's own intelligence layer).
- `env-hygiene` → subject `"doctor"` (Doctor's own repo-wide environment/
  credential scan; no other station's artifact is being judged).
- `marshal-durability` → subject `"marshal"` (Epic 5's already-shipped
  §6-compliant verdict).

`scripts/detectors.py` keeps two independent discovery paths side by side rather
than unifying them into one shape: file-scanned entries (`path`, runnable via
`run_one`) and Doctor-registry entries (declarative only — invoking a Doctor-owned
check still goes through `doctor check`/`monitor`/`diagnose`, not a bare script
path). Unifying execution is out of scope here; Story 6.9 re-points pixi tasks at
Doctor once each migrated detector's `scripts/*_check.py` shim retires.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Built Doctor's own source registry: `sources/__init__.py` (was
empty) now holds a validated `SourceRegistration` frozen dataclass and a
`REGISTRY` tuple declaring scope/subject-station/owning-station for all 9
current `Source` members, failing loud at construction on an empty/whitespace
subject or owner, an invalid scope, or a non-`Source` value. A coherence test
enforces exact set-equality between `Source` and `REGISTRY` in both
directions. `scripts/detectors.py` gained a `_doctor_sources()` helper that
reads this registry directly (never AST-scanning Doctor's package) and
reports a `doctor_sources_available` flag alongside the rows, so "zero
sources" is never confused with "the package isn't importable here" — the
common case in the default `local-recipes` env and the `detectors.yml` CI
workflow, neither of which installs `pyforge-doctor`.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` —
  the registry mechanism (new).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — one
  docstring line pointing `Source` at the new registry.
- `scripts/detectors.py` — `_doctor_sources()` + `doctor_sources_available`
  wired into both `--list` output modes.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py`
  (new) — 13 tests: construction validation, coherence, `to_json_dict()`.
- `tests/scripts/test_detectors_doctor_sources.py` (new) — 4 tests: both
  `_doctor_sources()` branches plus both `--list` output modes end-to-end.
- `pixi.toml` — new `pyforge-doctor-scripts-test` task under `feature.pyforge-ci`
  (stdlib-only, mirrors `pyforge-deps-test`'s precedent for `tests/packaging`).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md` — Story
  6.2 marked `done` with a dated Outcome note (mirrors Story 6.1's shape).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
  — promoted via `scripts/promote_sprint_status.py --project doctor` (never
  hand-edited directly; the file is generated).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated):
0 intent_gap, 0 bad_spec, 8 patch (0 high / 3 medium / 5 low — all applied),
1 defer (medium — logged to `deferred-work.md`), 5 reject (noise or
out-of-scope for this story, each with a documented reason in the Review
Triage Log above). No loopback was needed.

**Follow-up review recommendation:** `false`. All 8 patches were mechanical,
landed inside this story's own narrow surface (no external API, no security
or data-model surface), and were independently re-verified by a full test
suite rerun after every patch (435 `pyforge-doctor` tests, 4 new
`pyforge-ci`-scoped tests, both governance checks —
`ledger_regression_check.py` and `story_status_check.py` — green).

**Verification performed:** full `pyforge-doctor-test` suite (435 passed);
new `pyforge-doctor-scripts-test` task (4 passed, stdlib-only, lean
`pyforge-ci` env); live CLI checks in both `pyforge-doctor` env (9
`doctor_sources` rows, `available: true`) and `local-recipes` env (`available:
false`, empty rows, no crash, exit 0); `pyforge-deps-test` confirmed
unaffected (3 pre-existing failures, unrelated to this story's internal-only
import, byte-identical test file to baseline); `environment.yaml` re-export
diffed identical (the `pixi.toml` change only touched a task in a feature
outside the `build` environment's composition).

**Residual risks:** `Source.BEHIND_UPSTREAM` has no backing `gather()`
anywhere in `pyforge.doctor` (pre-existing Epic 2 gap, logged to
`deferred-work.md`, not fixed here). Stories 6.4–6.9 still own all the actual
detector migrations — this story is the registry mechanism only, by design.
