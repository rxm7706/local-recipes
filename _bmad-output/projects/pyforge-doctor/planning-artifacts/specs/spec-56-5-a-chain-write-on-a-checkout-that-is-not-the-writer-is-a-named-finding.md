---
title: '56.5: A chain write on a checkout that is not the writer is a named finding'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
story: 56-5-a-chain-write-on-a-checkout-that-is-not-the-writer-is-a-named-finding
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/writer_lock.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py'
  - 'scripts/detectors.py'
  - 'tests/scripts/test_detectors_doctor_sources.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_unmeasured.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_models.py'
  - 'docs/reference/detectors.md'
  - 'docs/map.yaml'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Inbound from control-plane (steward Story 121.4; operator ruling 2 of 2026-11-10: `pyforge.cutover_root` means the writer lock and the root of record; spec-python-foundry-cutover:CAP-8 names a guard on chain writes as the flag's first consumer). The session hook sees only one harness's Edit and Write; a detector in `detectors-ci` judges the branch for every harness.

**Approach:** A new repo-scope source, the branch half of the guard. The glob matcher is `chain.py`'s existing `_glob_to_re` (the spec-surface one); the denial's `paths` is the one declared list both halves read. Doctor binds to marshal Story 117.2's published `root_of_record(path) -> RootOfRecord(root, forge_slug, source)` and reads `roots.this` itself, as the hook does. The flag is read at the merge base, never at HEAD, so the PR that carries the flip passes the merge bar.

Ledger key: `56-5-a-chain-write-on-a-checkout-that-is-not-the-writer-is-a-named-finding`.
Type / Effort / Deps: feature / M / S-56.3, S-56.4; cross-station: marshal:S-117.2, steward:S-121.4.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-100** — a chain write off the writer is named (minted 2026-11-10).
- **`spec-python-foundry-cutover:CAP-8`** — the chain-write guard; the session hook (steward Story 121.4) is its other half.
- **`spec-pyforge-core:CAP-13`** — `root_of_record()`, the root of record this source reads.

## Boundaries & Constraints

**Always:**
- Read the roster and the flag files as data; import no station (AD-1, AD-11); every git read through `cli_bridge.run_git` (AD-5).
- Treat a `default` answer from `root_of_record()` as cannot-evaluate, never as proof that this checkout is the writer.

**Never:**
- Never decide when the flag flips (the operator flips it by hand once the Launch slice is proven); never read the flag at HEAD.
- Never add the `writer-lock-check` pixi task here: it is steward-station Story 124.1's.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — Every rule has its case, in the package half.** Expected: exit 0, 8 selected (flip_branch_is_ok: local-recipes at the merge base, foundry at HEAD, the Realization-log stamp changed, one OK); the FAIL's evidence names the path, the root of record and this root.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py -q -m 'not live_tree' -p no:cacheprovider -k 'writer_is_ok or flip_branch_is_ok or flipped_chain_path_fails or flipped_other_path_is_ok or no_roots_is_unevaluable or no_denial_entry_is_unevaluable or bad_flag_tree_is_unevaluable or origin_main_unresolvable_is_unevaluable'
  ```

- **AC2 — The module runs in the package half (no live_tree mark in any form).** Expected: exit 1 (no match).

  ```bash
  git grep --untracked -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py
  ```

- **AC3 — Registered as a repo-scope doctor source in detectors-ci.** Expected: prints `repo`, exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/detectors.py --list --json > "${TMPDIR:-/tmp}/doctor-list.json"; python3 -c "import json,os;d=json.load(open(os.environ.get('TMPDIR','/tmp')+'/doctor-list.json'))['doctor_sources'];s=[x for x in d if x['source']=='writer-lock'];print(s[0]['scope'] if s else None);raise SystemExit(0 if s and s[0]['scope']=='repo' else 1)"
  ```

- **AC4 — The aggregate and the empty-tree partition include it.** Expected: exit 0; writer-lock is in the unmeasured set over an empty tree (no roster).

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test && pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_unmeasured.py -q -p no:cacheprovider
  ```

- **AC5 — Story branch: the source runs on this tree.** Expected: exit 0 (before control-plane 121.4 adds `roots` and the denial entry: one cannot-evaluate WARN).

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources writer-lock
  ```

- **AC6 — Integration (after core-kit Story 117.2, control-plane Story 121.4): this checkout is the writer.** Expected: exit 0; stdout contains `is the writer`.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources writer-lock
  ```

- **AC7 — The generated detector page lists it.** Expected: exit 0; prints 1 or more.

  ```bash
  pixi run --frozen -e pyforge-guild docs-detectors -- --check && grep -c writer-lock docs/reference/detectors.md
  ```

- **AC8 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-56-5-*.md)"
  ```

- **AC9 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-100 (minted 2026-11-10); FR-32 ← CAP-100.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 56, minted with this story.
- Ledger key: `56-5-a-chain-write-on-a-checkout-that-is-not-the-writer-is-a-named-finding` (`backlog`).
- Deps: S-56.3, S-56.4; cross-station: marshal:S-117.2, steward:S-121.4.
- Surface: `marshal-policy.toml` `[epic_surfaces]."56"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- New detector for an inbound ruling-2 request; the code it guards exists (the session half, steward Story 121.4).
- Registration: `Source.WRITER_LOCK`, a REGISTRY row (scope repo, owning station doctor), DISPATCH, `("writer-lock", "writer-lock-check")` in `_DOCTOR_SOURCE_TASKS`; the pixi task is steward-station Story 124.1's, so until it lands the registry test that every row has a task is red on the branch. Acceptance runs the source module directly.
- Regenerate `docs/reference/detectors.md` with `pixi run --frozen -e pyforge-guild docs-detectors` once: that write also advances the `stamp:` of the `reference/detectors.md` entry in `docs/map.yaml` (herald's file; shared request); `docs/map.yaml` is on doctor's Spec surface, and its reconcile line is Story 57.3's (with 58.4 for later edits).
- On A the source reads writer until the flip. This is the branch half steward Story 121.4 no longer defers (DW-steward-121-5 is not written).
- Cross-station deps: marshal:S-117.2 (root_of_record), steward:S-121.4 (roster `roots` and the denial entry).
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt. Each finding, and what this round did with it:

1. **Blocker — `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` (the finding `source` enum) and `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` (`SOURCE_MODULE`).** AC9 was red, and this story's own change caused it. Adding `Source.WRITER_LOCK` broke three doctor tests: `test_models.py::test_schema_source_enum_matches_the_source_taxonomy_exactly` (the schema enum had no `"writer-lock"`), and `test_source_independence.py::test_every_in_scope_source_is_mapped_to_exactly_one_file` and `::test_every_real_sources_file_is_mapped_by_at_least_one_source` (`SOURCE_MODULE` had no `writer_lock.py` row). Neither file is in this story's `files_owned` or `surface:`, and no story in the plan owns either. **Fixed:** the additive patch was applied. It appends `"writer-lock"` as the last value of the schema's `source` enum. No value was removed or reordered, so the frozen-schema rule (additive changes only) holds and the `$id` is unchanged. It also adds `Source.WRITER_LOCK: "writer_lock.py",  # Story 56.5 (spec-pyforge-doctor CAP-100)` to `SOURCE_MODULE`. Re-run this round: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` exits 0 (2691 passed), and `pyforge-doctor-live-test` exits 0 (1431 + 4 passed). **Orchestrator action still open:** extend this story's `files_owned` (`plan.json`) and this spec's `surface:` with the two paths, so that the wave gate commits them. This round edits neither list: `surface:` is frontmatter, and `files_owned` is the plan's own field.
2. **Minor — `writer_lock.py` `_copy_out`.** The two temporary flag copies are written with `os.open`/`os.fdopen`. The static NFR-1 scan in `tests/meta/test_read_only_guard.py` does not see that form, so this is the first doctor write site the guard cannot see, and no list records it as sanctioned. The behaviour is within NFR-1: the write lands in a `tempfile.TemporaryDirectory` that is removed when the read returns, and `spec-pyforge-doctor:CAP-100`'s intent requires that copy. `pyforge.core.cutover_root.root_of_record` accepts only a path, so the copy cannot be dropped. **No code change, as the reviewer says.** Teaching the guard is a change to `test_read_only_guard.py`, which is outside this story's files. It is recorded under *Planned deferral* below, and the station closer writes the ledger row.
3. **Minor — AC2's oracle.** `git grep -n live_tree -- <file>` exits 1 on any untracked file, because `git grep` searches only tracked files. Until the wave gate commits the new test module, AC2 therefore passes whatever the file contains. **Oracle corrected** (ORACLE RULE): AC2 here and `plan.json` `stories[56.5].acceptance[1].command` both changed from `git grep -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py` to `git grep --untracked -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py`. Why: `--untracked` searches the tracked and untracked files under the pathspec, so the check proves the same property before and after the commit. Nothing is weakened: the expectation (exit 1, no match), the pattern and the path are unchanged. Re-run this round: the new command exits 1. A positive control, `git grep --untracked -n "def test" -- <same file>`, matches 16 lines, so the search does read the untracked file.

## Planned deferral (written at build)

The station closer writes a ledger row for each item below. This story adds no `deferred:` frontmatter entry.

- **The NFR-1 read-only guard cannot see `writer_lock.py`'s tempfile-scoped write.** `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` scans for `open(..., "w")`, `Path.write_text` and similar calls. `sources/writer_lock.py` `_copy_out` writes the two merge-base flag files into a `tempfile.TemporaryDirectory` through `os.open`/`os.fdopen`, which the scan does not match. Today the write is sanctioned: `spec-pyforge-doctor:CAP-100` names the temporary-directory copy, and `root_of_record` accepts only a path. But a later write placed beside it would pass the guard silently. Fix, in the guard's own file: either accept a write only under a `tempfile.TemporaryDirectory` it can see, or add `sources/writer_lock.py` to `_EXEMPT_RELATIVE_PATHS` as a named, bounded exemption, the way `fleet_surface.py` and `actuators/flag_kill_switch.py` are, with a test that the module writes only under a temporary directory. The guard should also learn the `os.open` write form. Owner: spec-pyforge-doctor (NFR-1, `spec-pyforge-doctor:CAP-96`'s two sanctioned writes). Blocker for this story: the file is outside `files_owned`.
