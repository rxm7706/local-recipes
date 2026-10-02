---
title: '82.12: Seed apply binds a plan to its repository, refuses a directory target with a remedy, and honours a skip on a hand-edit'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'c34cbda1919e96c2a9691404e0e794672d8b90b9'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
warnings: [oversized]
deferred:
  - summary: >-
      An `update --skip` that moves a migration's action into `plan.skipped` still records that migration in
      `migrations_applied`, so the skipped artifact is never migrated and the migration is not offered again.
    evidence: |-
      Read at `verbs/update.py::_build_state_after_apply`: `newly_applied` is every chain migration's `to_version`, and the
      state is written whenever `plan.actions` is non-empty, with no look at `plan.skipped`. Since this story,
      `run_update` runs `apply_skips` over the merged plan, so an operator `--skip` can reach a migration action. The
      module already treats the default-skipped migration-offered `copied-seeded` entries (in `plan.skipped`, no action)
      as consumed once offered, so whether an explicit `--skip` should leave the migration unrecorded (re-offered next
      run), refuse a skip that names a migration-claimed artifact, or be accepted as consumed like the offers is a
      semantics question, not a verified defect. Marked unverified. What would settle it: an operator ruling on that
      semantics, then a test that skips one migration action, applies another, and reads `migrations_applied` back.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:955
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three seed apply checks protect less than they claim. Re-verified at HEAD a7cdb91fe4:

- `seed/plan/types.py::RepoFingerprint` (`:220`) carries `git_head`, `dirty` and `artifact_hashes`, nothing naming the
  repository. For a non-git target `seed/plan/build.py::_git_head` and `_repo_is_dirty` (`:482-505`) degrade to the same
  `None` / `True` everywhere, so a plan built against directory A applies to directory B with zero drift from
  `fingerprint_drift` (`:681`) whenever B's actioned artifacts hash the same, most easily two empty greenfield directories
  (DW-10-3-7).
- Rung 5 of `seed/verbs/preconditions.py::check_preconditions` (`:651-671`) `lstat`s each target and refuses only a symlink;
  an existing directory falls through every rung, and apply then fails in `os.replace(tmp, target)` with an untyped
  `IsADirectoryError` outside the `SeedError` taxonomy, where every other refusal is a `PreconditionFailure` with exit 3 and
  a remedy (DW-10-4-5).
- `seed/verbs/skips.py::managed_after_skips` (`:359-385`) filters managed records by `plan.skipped`, which only an artifact
  with an action can enter (`apply_skips`, `:250-325`). A hand-edited `copied-managed` file classifies
  `PRESENT_CONFORMANT` and never gets an action, so `--skip <its path>` is a silent no-op and rung 6's only remaining
  override is `--force`, which discards every hand-edit. It is live now: `seed/verbs/adopt.py:1011` uses the helper, and
  `seed/verbs/update.py:1060` passes managed records to `check_preconditions` with no skip filter at all (DW-10-4-4).

**Approach:**

- `RepoFingerprint` gains the repository's identity (its resolved root, and its git common directory when it has one),
  recorded at plan build and serialized in `plan.json`; `fingerprint_drift` reports a mismatch against the apply target,
  and a `plan.json` without the field is refused with a re-plan remedy.
- Rung 5's `lstat` also refuses an existing directory at an action's target: a `PreconditionFailure` naming the target with
  a remedy (remove or rename the directory, or `--skip` the artifact), inside the existing six-rung order.
- `managed_after_skips` also drops managed records whose path matches a skip pattern the operator passed, so the skip
  reaches a file that never had an action; `adopt` and `update` both apply it before rung 6.

Ledger key: `82-12-seed-apply-binds-a-plan-to-its-repository-refuses-a-directory-target-with-a-remedy-and-honours-a-skip-on-a-hand-edit`.
Type / Effort / Deps: fix / M / 82.11.

### Living CAP citations

- `spec-pyforge-marshal` CAP-12 (adopt reviews exactly what will change) and CAP-15 (update without touching team work),
  with Story 9.6 (the repo fingerprint and `plan.json`), Story 10.3 (FR-83; P-04, P-07; AD-57) and Story 10.4 (FR-85,
  FR-86, FR-87). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a plan built against an empty non-git directory A When it is applied to an empty non-git directory B Then `fingerprint_drift` names the repository mismatch and apply refuses
- Given a `plan.json` written before the repository field existed When apply reads it Then it refuses with a remedy to re-plan
- Given an action whose target path is an existing directory When `check_preconditions` runs Then it raises a `PreconditionFailure` with a non-blank remedy and exit code 3, and no write is attempted
- Given a hand-edited `copied-managed` file and `--skip` naming its path When `adopt` or `update` runs Then rung 6 does not refuse it and the edit is kept, without `--force`
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Every refusal is a `PreconditionFailure` with a remedy. Rung 6 still checks every managed record a skip does
not name. Close DW-10-3-7, DW-10-4-5 and DW-10-4-4 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not add a seventh rung or reorder the ladder. Do not weaken `--force`'s meaning. Do not touch the never-write
matching or manifest path validation (Story 82.11's surface) or opt-out handling (Story 82.13's).

</intent-contract>

## Code Map

Paths below are under `src/shared/packages/pyforge-marshal/`; `seed/` is `src/pyforge/marshal/seed/`.

- `seed/plan/types.py:219-279` -- `RepoFingerprint`: add `repo_root: str` and `git_common_dir: str | None` (required, no default, like its siblings), both in `to_json_dict`/`from_json_dict`. `from_json_dict` has no PreconditionFailure today; `_require_key` raises `ValueError`.
- `seed/plan/build.py:481-505` -- `_git_head`/`_repo_is_dirty`: add the identity probe beside them; `:671-677` is the one producer; `:680-852` `fingerprint_drift` gains the identity comparison; `:877` `load_plan` has no production caller (adopt/update only write `plan.json`).
- `seed/apply/run.py:364-378` -- turns any drift line into the `stale-plan` `PreconditionFailure`; unchanged, so identity drift refuses apply for free.
- `seed/verbs/preconditions.py:616-652` -- rung 5 `lstat` loop; add the `S_ISDIR` refusal there (no seventh rung). Module docstring still says rung 5 refuses only a symlink.
- `seed/verbs/skips.py:344-386` -- `managed_after_skips` + `_HasArtifactId`; reuse `first_match`, `_normalize_relative_posix`, `_require_patterns` from the same file. `apply_skips` (`:333`) uses `dataclasses.replace`, so new fingerprint fields survive it.
- `seed/verbs/adopt.py:1025` and `seed/verbs/update.py:1078-1090` -- call sites. `--skip` is declared only on the adopt subparser of `cli/seed.py` (`adopt_parser.add_argument("--skip", ..., action="append")`); `update_parser` (same file), the CLI wrapper `run_update` (`cli/seed.py:794`) and the verb `run_update` (`update.py:956`) take none. `epics.md` Story 82.12 requires the exemption "in `adopt` and `update` alike", and "no flag" in this epic means no feature flag (`epics.md` Epic 82 intro; Story 82.1 cites `spec-feature-flag-governance` Q1), not "no CLI option": `update` gains `--skip`. `apply_skips` (`skips.py`) works on any `Plan` and carries `plan.skipped` through, so it applies to update's merged plan as it does to adopt's; `_render_update_plan_text` already renders a user-pattern skip as `matched --skip`.
- `seed/migrate/registry.py:170-177`, `seed/plan/build.py` `load_plan` docstring, `seed/plan/types.py` opening docstring, `seed/verbs/preconditions.py` (module docstring ~79-90, `check_preconditions` docstring ~505-514, and the rung-3 repo-root comment ~572-581), `seed/verbs/update.py` comment at the `managed_after_skips` call -- text that the change makes stale or inaccurate (review pass 1).
- Tests: `tests/unit/test_seed_{plan_types,plan_build,apply_run,verbs_preconditions,verbs_skips,verbs_update,verbs_adopt,cli_seed_update}.py` and `tests/meta/test_sc08_never_write_update_proof.py`; about 25 direct `RepoFingerprint(...)` constructions need the two new fields.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md:1220,1313,1328` -- DW-10-3-7, DW-10-4-4, DW-10-4-5 rows to close.

## Tasks & Acceptance

**Execution:**
- `seed/plan/types.py` -- add the two fields and their codec; a fingerprint dict with the three legacy keys and no `repo_root` raises `PreconditionFailure` (`stale-plan`, remedy: re-run the plan), any other malformed shape stays `ValueError` -- the rest of `from_json_dict` is untouched.
- `seed/plan/build.py` -- `_repo_identity(process, repo_root)` (resolved root; `git rev-parse --git-common-dir` resolved against the root, `None` on non-zero exit); `build_plan` records it; `fingerprint_drift` reports a root or common-dir mismatch first, before `git_head`; update its docstring.
- `seed/verbs/preconditions.py` -- in rung 5, `S_ISDIR(mode)` raises `PreconditionFailure` `directory-target` naming the action, path and a remedy (remove or rename the directory, or `--skip` the artifact); update the module docstring.
- `seed/verbs/skips.py` -- `managed_after_skips(managed, plan, patterns=())` also drops a record whose normalized `path` matches a pattern; the Protocol gains `path`; docstrings say the helper takes patterns because a hand-edited managed file never has an action.
- `seed/verbs/adopt.py` -- pass `skip` to the helper.
- `cli/seed.py` and `seed/verbs/update.py` -- `update` gains `--skip GLOB` (repeatable, `action="append"`, help text as adopt's) and `run_update(..., skip: Sequence[str] = ())`; after `_merge_plan_sources`, `plan = apply_skips(plan, skip)` so a skipped artifact's wholesale-regenerate action moves to `plan.skipped` and is never applied, and the managed records go through `managed_after_skips(records, plan, skip)` before rung 6. `--force` keeps its meaning; a blank or bare-string pattern is the existing `UsageError`. `update` does not write the pattern into `state.skips` (state carries it unchanged, as today; nothing reads it back).
- Stale text the change leaves behind (review pass 1): the `registry.py` placeholder example gains the two required fields; the `load_plan` and `types.py` docstrings say a pre-82.12 fingerprint raises `PreconditionFailure` and that a fingerprint names its repository; the `preconditions.py` module and `check_preconditions` docstrings tell a caller to pass the operator's skip patterns to `managed_after_skips` as well as the plan; the rung-3 repo-root comment notes that rung 5 would also refuse a directory but rung 3 names the root first; the `fingerprint_drift` docstring says identity is listed first in the returned lines (it does not short-circuit); the `update.py` comment says a record whose entry was retired or reclassified has no wholesale action (so rung 6 can still refuse it) instead of claiming an action for every record.
- the tests above -- update direct constructions; add one test per AC, each failing when its fix is reverted; plus pins for review pass 1: `dry_run=True` and `force=True` do not bypass `directory-target`; identity when `repo_root` is a subdirectory of a git working tree; a plan built before `git init` is drift against the same directory after it; `update --skip` through argv (parser accepts it, passes it to `run_update`, `update` text output lists the skipped artifact) and through `run_update` (hand-edited managed file kept byte-for-byte, no refusal, no `--force`; an unnamed hand-edit still refuses).
- `deferred-work-ledger.md` -- close the three rows (`status: closed`, `resolved:` line naming Story 82.12; the DW-10-4-4 line says `update` takes the pattern through its new `--skip`).
- `spec-pyforge-marshal` and `spec-pyforge-core` `.memlog.md` -- name every changed governed path, `cli/seed.py` and its test included (`python _bmad/scripts/memlog.py append`, never `--write-baseline`).

**Acceptance Criteria:**
- Given a plan built in empty non-git directory A, when `run_apply` targets empty non-git directory B, then `fingerprint_drift` names the repository mismatch and apply raises `stale-plan` before any write.
- Given a plan whose repo is moved or replaced by another clone, when it is applied, then the git common directory differs and apply refuses.
- Given a `plan.json` whose fingerprint lacks `repo_root`, when `Plan.from_json_dict`/`load_plan` reads it, then it raises `PreconditionFailure` with a re-plan remedy; a plan round-trips unchanged.
- Given an action whose target is an existing directory, when `check_preconditions` runs, then it raises `PreconditionFailure` (`directory-target`, exit 3, non-blank remedy) and nothing is written; a symlink still reports `symlink-target`.
- Given a hand-edited managed file with no action and `--skip <its path>`, when `run_adopt` runs without `--force`, then rung 6 does not refuse and the file is unchanged; a second hand-edited file the pattern does not name still refuses.
- Given a hand-edited managed file that update would regenerate and `update --run --skip <its path>`, then rung 6 does not refuse, the file is not rewritten (its action is in `plan.skipped`), and a second hand-edited file the pattern does not name still refuses.
- Given `run_update` with a managed record for an artifact in `plan.skipped` (a migration-offered `copied-seeded` entry), then rung 6 is not asked about it.

## Spec Change Log

### 2026-10-02 — review pass 1 (bad_spec, iteration 1)

- **Triggering finding:** Blind Hunter, Edge Case Hunter and Intent Alignment Auditor each found, independently, that `update` was given no `--skip`, so the criterion "`--skip <pattern>` matching a hand-edited managed file exempts it from rung 6 in `adopt` and `update` alike" (`epics.md` Story 82.12) was delivered for `adopt` only. Verified: the `update` subparser in `cli/seed.py` declares no `--skip`, `run_update` takes no `skip`, and the first-pass Design Note justified this as "a flag is out of scope".
- **Root cause:** the Design Note, the Code Map line and the Tasks line (all outside the `<intent-contract>`) read "no flag" in the contract's CAP line as "no CLI option". In this epic "no flag" means no feature flag (`epics.md` Epic 82 intro; Story 82.1 cites `spec-feature-flag-governance` Q1).
- **Amended:** Code Map (the `--skip` line, a new stale-text line, the test list), Tasks (a `cli/seed.py` + `update.py` task for `update --skip`, a stale-text task, extra test pins, the memlog task), the acceptance bullet for `update`, and the `update` Design Note. The `<intent-contract>` is unchanged.
- **Known-bad state avoided:** dropping a hand-edited file's record from rung 6 on `update` without moving its wholesale-regenerate action into `plan.skipped` would let `update` overwrite the edit with no `--force`. Both halves ship together.
- **KEEP (worked in pass 1, must survive re-derivation):**
  - `RepoFingerprint` gains required `repo_root: str` and `git_common_dir: str | None`, serialized in `plan.json`; `plan/build.py::_repo_identity` resolves the root and resolves `git rev-parse --git-common-dir` against it (`None` on a non-zero exit); `fingerprint_drift` reports root, then common-dir, then `git_head`/`dirty`/hashes.
  - A fingerprint with the three legacy keys and no `repo_root` raises `PreconditionFailure` `stale-plan` (re-plan remedy) from `RepoFingerprint.from_json_dict`; any other malformed shape stays `ValueError`.
  - Rung 5 refuses `S_ISDIR` as `directory-target` inside the same rung, after the `S_ISLNK` branch; no seventh rung.
  - `managed_after_skips(managed, plan, patterns=())` matches a record's normalized `path` with `first_match` and validates patterns with `_require_patterns`; `adopt` passes `skip`.
  - The tests added in pass 1: apply A-to-B refusal, drift ordering, symlinked-alias-of-same-root is not drift, two worktrees of one clone agree and two clones differ, legacy-fingerprint refusal and round trip, directory/empty-directory/symlink-to-directory/`--skip`/rung-order pins, `managed_after_skips` pattern and normalization pins, the `run_adopt` two-hand-edits pins, the `run_update` plan-skipped pins.
  - Mutation evidence: revert each fix in turn and run its new test; the pass-1 implementation recorded that every one failed.

## Design Notes

- **Why `update` needs both halves of a skip.** Its wholesale-regenerate pass emits an action for every managed `copied-managed`, `generated-derived` and `hybrid-managed-region` record, so dropping a hand-edited file's record from rung 6 without also moving that file's action into `plan.skipped` would let `update` overwrite the edit with no `--force` -- worse than the refusal. `apply_skips` moves the action; `managed_after_skips` drops the record by id (for the moved action) and by path (for a record no action exists for). A record whose entry was retired or reclassified has no wholesale action, so only the path match can reach it. This replaces the first-pass design note that left `update` without a pattern: that note read "no flag" in the contract's CAP line as "no CLI option", but it means no feature flag, and `epics.md` requires the exemption in `adopt` and `update` alike.
- **Identity is compared, not hashed into `dirty`.** Both fields are resolved paths, compared as strings; moving a repo is drift and takes a re-plan. A common directory is `None` outside git, so for a non-git target the root alone separates A from B.

## Binding

Parent: Stories 9.6, 10.3 and 10.4, `spec-pyforge-marshal` CAP-12 and CAP-15; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-12-seed-apply-binds-a-plan-to-its-repository-refuses-a-directory-target-with-a-remedy-and-honours-a-skip-on-a-hand-edit`.
Ledger status at mint: `backlog`.
Deps: 82.11 (both edit `seed/verbs/preconditions.py`).
Closes: DW-10-3-7, DW-10-4-5, DW-10-4-4.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 26 findings — high 0, medium 3, low 18, false 5, maybe-false 0
- Layers: Blind Hunter (13), Edge Case Hunter (7), Verification Gap (0 gaps, 2 other findings), Intent Alignment Auditor (4 divergences extracted from its descriptive report). Routing: one `bad_spec` group (3 members), so every `patch` row below is moot for this pass and is folded into the amended Tasks so the re-derivation carries it.
- findings:
  - Blind Hunter
    - `[low]` `[patch]` `migrate/registry.py` docstring still gives `RepoFingerprint(git_head=None, dirty=True, artifact_hashes=())` as a valid placeholder — verified at `registry.py:174-177`: the call now raises `TypeError` (two required fields). Folded into Tasks (stale text).
    - `[low]` `[patch]` `load_plan` / `types.py` docstrings do not say a pre-82.12 fingerprint raises `PreconditionFailure` and that a fingerprint names its repository — verified: only the `types.py` module paragraph was amended. Folded into Tasks (stale text).
    - `[low]` `[patch]` the rung-3 repo-root comment in `preconditions.py` says the root "is not a symlink (rung 5 clears)"; rung 5 now also refuses a directory — verified; rung 3's loop runs to completion before rung 5, so the named refusal is still `target-is-repo-root`, only the comment is dated. Folded into Tasks (stale text).
    - `[low]` `[patch]` `fingerprint_drift` docstring says identity is checked "before anything about its contents is weighed" but the function does not short-circuit — verified at `build.py` (all drift lines are appended). Reword to "listed first". Folded into Tasks (stale text).
    - `[low]` `[reject]` a skip honoured on a hand-edited managed file is invisible in the plan text and JSON, and a mistyped pattern still no-ops — real, but consistent with the existing contract (`apply_skips`: "a pattern matching nothing is not an error"), the operator typed the pattern, and showing it needs a new `Plan` field or renderer, which is more than a direct correction.
    - `[low]` `[patch]` the new `dry_run` / `force` claims for `directory-target` have no test — the code is correct (rung 5 is gated by neither) but nothing pins it, and `force` not bypassing it is a boundary of the contract. Folded into Tasks (test pins).
    - `[low]` `[patch]` identity edge cases untested (`repo_root` a subdirectory of a working tree; a plan built before `git init` applied after) — the code resolves `--git-common-dir` against the `cwd` it ran in, so `../.git` resolves correctly, but no test says so. The sub-claim that `_fresh_plan` breaks in a linked worktree is `false`: it is used only with `tmp_path` repositories and the worktree cases compare against git directly in `test_seed_plan_build.py`. Folded into Tasks (test pins).
    - `[false]` `[reject]` the wire format has no version marker and the legacy heuristic can mislabel a plan — the legacy shape needs all three legacy keys and no `repo_root`, a plan with other defects also needs a re-plan, and `RepoFingerprint(` is constructed in `src/` only by `build_plan` (Verification Gap layer checked this), so no external construction breaks.
    - `[low]` `[reject]` the absolute `repo_root` in `plan.json` leaks a host path and makes the file location-specific — the intent says to record the resolved root in `plan.json`; the file is `.marshal/plan.json`, covered by the packaged `.gitignore` region; the `RepoFingerprint` docstring already says a moved repo takes a re-plan.
    - `[false]` `[reject]` `managed_after_skips` matches the record's `path` while `apply_skips` matches the action's `target_path`, so a pattern could drop the rung 6 guard for an artifact still written — an action writes only at its own `target_path`; a record whose path differs from every action target is never written by this run, and where they are equal both filters match the same pattern.
    - `[false]` `[reject]` the spec's Review Triage Log, Spec Change Log and verification record are empty — those sections are written by this step, and the finding's fix is to edit this build's spec.
    - `[medium]` `[bad_spec]` the `update` half of the skip criterion was narrowed without being logged, and DW-10-4-4 is closed although `update` still has no pattern exemption — verified against `epics.md` ("in `adopt` and `update` alike") and the `update` subparser. Amendment: `update` gains `--skip`; see the Spec Change Log. Grouped with the two other members of this root cause.
    - `[false]` `[reject]` surface stamping is left pending, so `spec-surface-check` stays red — `python scripts/spec_surface_reconcile.py` exits 0 ("no drift") on this tree, and this run is forbidden from passing `--write-baseline`.
  - Edge Case Hunter
    - `[low]` `[reject]` a repo path with non-UTF-8 bytes puts surrogates in `repo_root`, and `write_plan` raises a raw `UnicodeEncodeError` — real but rare on a manifest-driven tool; a guard adds a new branch and a new typed failure, more than a direct correction.
    - `[low]` `[reject]` a pattern-exempted record appears nowhere in the output — same finding and same reason as the Blind Hunter visibility row.
    - `[low]` `[reject]` the `directory-target` remedy offers `--skip` where `init` has no such option — the existing `symlink-target` and `target-escapes-repo` remedies make the same offer to every verb, the first half of the remedy works everywhere, and `update` gains `--skip` in this pass.
    - `[low]` `[patch]` `load_plan` docstring says only `ValueError` — same as the Blind Hunter docstring row. Folded into Tasks (stale text).
    - `[low]` `[patch]` `registry.py` placeholder docstring — same as the Blind Hunter row. Folded into Tasks (stale text).
    - `[medium]` `[bad_spec]` the acceptance criterion's `update` half is unmet — `update` has no `--skip`, so the criterion cannot be exercised on it. Same root cause as the Blind Hunter row; one amendment.
    - `[low]` `[patch]` the `update.py` comment says the wholesale pass emits an action for every managed record, but `_wholesale_regenerate_actions` skips a record whose entry is retired, reclassified, escaping or migration-claimed — verified; the comment is wrong in those cases (the pre-existing behaviour that rung 6 can still refuse such a record is unchanged, and the path match in the amended design now reaches it). Folded into Tasks (stale text).
  - Verification Gap
    - `[low]` `[patch]` the `preconditions.py` module docstring and the `check_preconditions` docstring still tell a caller to filter with `managed_after_skips(managed, plan)` and say nothing can tell a record was skipped — verified; a caller following that text misses the pattern argument and meets DW-10-4-4 again. Folded into Tasks (stale text).
    - `[low]` `[patch]` `registry.py` stale constructor — same as the Blind Hunter row. Folded into Tasks (stale text).
  - Intent Alignment Auditor
    - `[medium]` `[bad_spec]` the diff implements the `update` half of the skip criterion only as a plan-skipped filter, which `update` cannot reach with a hand-edited file — the clearest divergence between the criterion's surface and the diff's; same root cause as the two rows above.
    - `[low]` `[reject]` the first two criteria are exercised through library seams (`run_apply` with a `_fresh_plan` fixture, `load_plan`) and no verb-level or CLI-level test — the verbs never load a `plan.json`, so `run_apply` is the surface the criterion names; the producer half (`build_plan` records identity) has its own tests in `test_seed_plan_build.py`, and `run_apply` calls `fingerprint_drift` unchanged.
    - `[low]` `[reject]` the directory-target criterion is tested at `check_preconditions` and not through a full verb — the ladder is the surface the criterion names; a real plan reaches rung 5 with a directory target through `update`'s wholesale action on a path the operator replaced with a directory, which the unit test models.
    - `[false]` `[reject]` the mutation criterion has no evidence in the patch — a revert-and-run property cannot appear in a diff; the pass-1 implementation reported running each revert, and the Verification Gap layer read each new test and found it would fail. Not independently re-run in this pass; the re-derivation records it again.

### 2026-10-02 — Review pass (after the bad_spec re-derivation)
- verdicts: 30 findings — high 0, medium 2, low 22, false 4, maybe-false 2
- Layers: Blind Hunter (13), Edge Case Hunter (7), Verification Gap (3: one gap, two other findings), Intent Alignment Auditor (7 divergences extracted from its descriptive report). Routing: no `intent_gap`, no `bad_spec`; one grouped `patch` entry per fix below, applied by re-engaging the implementation subagent; one `defer` group (2 members); the rest rejected.
- findings:
  - Blind Hunter
    - `[low]` `[patch]` test `test_a_directory_target_is_reported_by_rung_5_not_a_later_action_s_rung_3` is named the opposite of what it asserts — verified (it asserts `target-escapes-repo` wins). Fixed: renamed to `test_a_directory_target_does_not_pre_empt_a_later_actions_escaping_path`, docstring corrected, assertions unchanged.
    - `[low]` `[patch]` private Protocol `_HasArtifactId` now requires `artifact_id` and `path` — verified; two references only. Fixed: renamed `_ManagedLike` at the class and the `_RecordT` bound.
    - `[low]` `[patch]` `managed_after_skips` docstring says "Pure and total" but raises `UsageError` for a bare-string or blank pattern even when `managed` is empty — verified. Fixed: the sentence now says it is pure, reads no disk, and raises `UsageError`.
    - `[low]` `[reject]` `patterns=()` keeps the silent no-op reachable for a future caller that passes only `(managed, plan)` — both production callers pass patterns and are pinned by behaviour tests; the plan-only form is a valid use (migration-offered skips) and the signature is what the Tasks specify, so the fix means editing this build's spec and every plan-only test call.
    - `[low]` `[reject]` `update --skip` is per-invocation and nothing says so — `state.skips` is written by `adopt` and read by nothing in `src/` (pre-existing, outside this story), `run_update`'s docstring states the behaviour, and the help text mirrors `adopt`'s, which is equally per-run; honouring `state.skips` is more than a direct correction.
    - `[low]` `[patch]` the directory refusal lives only in `check_preconditions`, and the DW-10-4-5 `resolved:` line says "apply no longer reaches `os.replace(tmp, directory)`" — verified the line overclaims; the intent places the fix in rung 5 and forbids a seventh rung. Fixed: the ledger line now says every verb (`init`, `adopt`, `update`) runs the ladder before `run_apply`, and that `run_apply` and `fs.write` are unchanged, so `run_apply` called alone on a directory target fails as before.
    - `[medium]` `[patch]` no test reads the state after a run that skips a hand-edited managed file AND applies something else, so a carry-over regression would turn `--skip` into "protect it once" — grouped with the Verification Gap row. Fixed: one mixed-run test per verb (`test_skip_of_a_hand_edit_in_a_run_that_applies_something_else_keeps_the_state_record` in `test_seed_verbs_update.py` and `test_seed_verbs_adopt.py`): the skipped file's bytes are unchanged, its state record keeps the original `body_sha`, and a follow-up run without `--skip` and without `--force` raises `managed-content-modified`.
    - `[low]` `[reject]` carried: a skip honoured on a hand-edited managed file is invisible in the plan text and JSON, and a mistyped pattern still no-ops — real, but consistent with `apply_skips` ("a pattern matching nothing is not an error"), and showing it needs a new `Plan` field or renderer.
    - `[low]` `[reject]` carried: `from_json_dict` now raises a `SeedError` where its documented contract was `ValueError`, and `load_plan` has no caller in `src/` — the contract text was amended in the `types.py` and `load_plan` docstrings in this story, and no caller catches `ValueError` around it.
    - `[low]` `[patch]` the `spec-pyforge-core` 82.12 memlog line is a word-for-word copy of the marshal one, lacks the "(co-governor, …)" opening and "Marshal-local; no kernel surface changes", and both 82.12 lines end with a stray " ." before "No baseline stamped." — verified (the two last lines were identical). Fixed: the core line is rewritten in place as a co-governor reconcile in the shape of the 82.11 ones, still naming every changed path in full; the stray " ." is gone from both; no other memlog line touched, no baseline stamped.
    - `[low]` `[reject]` the `stale-plan` remedy is generic ("re-run the plan against the current repo state") for a plan applied to the wrong directory — the remedy is correct for that case (re-plan for the target), and tailoring it by the first drift line adds a branch to `run_apply`, which this story does not edit.
    - `[low]` `[reject]` about 25 `RepoFingerprint(...)` test sites repeat one literal; a shared factory would help — a test-structure preference with no defect behind it, and a factory is a refactor of unrelated tests.
    - `[low]` `[patch]` the extended `RepoFingerprint` sentence in the `types.py` module docstring is 135 columns against 120 elsewhere, and other edited paragraphs wrap raggedly — verified (`awk 'length>120'` showed line 14). Fixed: the edited paragraphs in `types.py`, `preconditions.py` and the `cli/seed.py` module docstring are rewrapped (wrapping only, checked word for word); no source line this story added exceeds 120 columns. The docstring-pinning test the same row names is sibling-consistent (`test_the_module_docstring_points_a_caller_at_the_skip_seam` does the same) and stays.
  - Edge Case Hunter
    - `[maybe-false]` `[defer]` if true it would be medium: an `update --skip` that moves a migration's action into `plan.skipped` still records that migration in `migrations_applied` — verified by reading `_build_state_after_apply` (it records every chain migration's `to_version` and never looks at `plan.skipped`), but whether that is a defect or the same "offered once, consumed" treatment the module gives default-skipped migration-offered `copied-seeded` entries is a semantics question this story cannot settle. Deferred, unverified; see `deferred:` and `DW-marshal-82-12`.
    - `[low]` `[reject]` `skip` could be a one-shot iterable consumed by `apply_skips` before `managed_after_skips` — `skip` is typed `Sequence[str]`, the CLI passes a tuple, and `run_adopt` already iterates `skip` a second time after `apply_skips` (state write), so a re-iterable is the established contract.
    - `[low]` `[reject]` `adopt --skip` is recorded in `state.skips`, a later `update` without `--skip` does not honour it — same as the Blind Hunter row: `state.skips` is read by nothing, the later run refuses at rung 6 (fail-safe) rather than overwriting, and `--force` keeps its meaning.
    - `[low]` `[reject]` carried: `plan.json` now embeds absolute host paths — the intent says to record the resolved root in `plan.json`; the file is `.marshal/plan.json`, which the packaged `.gitignore` region covers, and a moved repo taking a re-plan is documented on `RepoFingerprint`.
    - `[false]` `[reject]` a plan built for one clone and applied to a clone re-created at the same path passes the identity check — the intent defines identity as the resolved root plus the git common directory, so the same path is the same identity by definition; `git_head`, `dirty` and every artifact hash are still compared, so a clone with different content still refuses.
    - `[false]` `[reject]` carried: a fingerprint lacking `repo_root` plus another key raises `ValueError` without the re-plan remedy — only the exact legacy shape is a stale plan; a fingerprint missing anything else is malformed, and `test_a_fingerprint_missing_other_keys_besides_the_repository_field_stays_a_value_error` pins that.
    - `[low]` `[patch]` the DW-10-4-5 ledger claim "apply no longer reaches `os.replace(tmp, directory)`" holds only after the ladder ran — same root as the Blind Hunter row; one fix (the ledger `resolved:` line, above).
  - Verification Gap
    - `[medium]` `[patch]` a skipped hand-edited record surviving a partial `adopt` / `update` apply is not verified — pre-verified by that layer; grouped with the Blind Hunter row; one fix (the two mixed-run tests, above).
    - `[maybe-false]` `[defer]` if true it would be medium: `migrations_applied` records a migration although `update --skip` moved its action into `plan.skipped` — same group as the Edge Case Hunter row above (one deferral).
    - `[low]` `[reject]` carried: `plan.json` serializes absolute paths and becomes host-specific — same reason as the Edge Case Hunter row; no golden file or schema pins it.
  - Intent Alignment Auditor
    - `[low]` `[reject]` carried: the first two criteria are enforced at library seams (`fingerprint_drift`, `run_apply`, `load_plan`) because no shipped verb loads a `plan.json` or applies one plan to another directory — the criteria's own wording names those seams; the producer half (`build_plan` records identity) has its own tests.
    - `[low]` `[reject]` the legacy-plan refusal sits in the data-type module and keys on the exact legacy shape; an old-shape in-memory `Plan` is a `TypeError` — required fields are the contract (no default, like their siblings), the `types.py` and `load_plan` docstrings now say so, and a hand-built old-shape `Plan` is not a path any producer takes.
    - `[false]` `[reject]` `update --skip` is new surface wider than the intent's wording — no bad outcome: `epics.md` Story 82.12 requires the exemption "in `adopt` and `update` alike", the criterion cannot be met without it, and the first pass recorded the amendment in the Spec Change Log.
    - `[low]` `[reject]` the DW-10-4-4 premise holds differently per verb (`adopt`: no action, the pattern branch reaches it; `update`: a wholesale action, `apply_skips` protects it) and `update` does not persist the pattern — descriptive, and the per-verb split is exactly what the amended Design Note says; persistence is the Blind Hunter `state.skips` row.
    - `[low]` `[reject]` carried: the directory-target criterion is exercised at `check_preconditions` with a hand-built plan, not through a verb — the ladder is the surface the criterion names, and `update`'s wholesale action is the production route to it.
    - `[low]` `[reject]` "no write attempted" for a directory target is shown only by inspecting the directory afterwards — `check_preconditions` is read-only by construction (its module docstring: "performs no write of any kind"), and the test asserts the directory's contents are untouched.
    - `[false]` `[reject]` carried: the mutation criterion has no evidence in the patch — a revert-and-run property cannot appear in a diff. This pass's implementation subagent reverted nine fixes on a scratch copy and recorded each new test failing (identity comparison, legacy refusal, `directory-target`, the pattern match, `apply_skips` in `update`, the pattern argument in `update` and in `adopt`, the CLI hand-off, the `--skip` option); the Verification Gap layer read each new test and found it would fail without its fix.

## Auto Run Result

Status: done

**Summary of the implemented change.** Three seed apply checks now protect what they claimed to.
- **Repository identity (DW-10-3-7).** `RepoFingerprint` records the repository it was built for: `repo_root` (the resolved root) and `git_common_dir` (the resolved `git rev-parse --git-common-dir`, `None` outside git), both serialized in `plan.json`. `fingerprint_drift` lists a root or common-dir mismatch first, so a plan built for one empty non-git directory is `stale-plan` against another and `run_apply` refuses it before any write. A fingerprint with the three legacy keys and no `repo_root` raises `PreconditionFailure` (`stale-plan`, exit 3, re-plan remedy) when `Plan.from_json_dict` / `load_plan` reads it; any other malformed shape stays `ValueError`.
- **Directory target (DW-10-4-5).** Rung 5 also refuses an existing directory at an action's target as `PreconditionFailure` `directory-target` (exit 3, remedy: remove or rename it, or `--skip` the artifact), after the `symlink-target` branch and inside the same six rungs. Neither `dry_run` nor `force` bypasses it.
- **Skip on a hand-edit (DW-10-4-4).** `managed_after_skips(managed, plan, patterns=())` also drops a managed record whose normalized path matches a skip pattern. `adopt` passes its `--skip` patterns. `update` gains `--skip GLOB` (repeatable) and `run_update(skip=...)`: `apply_skips` moves a matching wholesale-regenerate action into `plan.skipped` so it is never applied, and the helper drops the record by id and by path, so rung 6 is not asked about it and the edit is kept without `--force`. A hand-edit the pattern does not name is still refused, and `--force` keeps its meaning.

**Files changed** (all under `src/shared/packages/pyforge-marshal/` unless noted).
- `src/pyforge/marshal/seed/plan/types.py` -- `RepoFingerprint` gains the two identity fields, their codec and the legacy-plan refusal.
- `src/pyforge/marshal/seed/plan/build.py` -- `_repo_identity`, recorded by `build_plan` and compared first by `fingerprint_drift`; `load_plan` docstring.
- `src/pyforge/marshal/seed/verbs/preconditions.py` -- the rung-5 `directory-target` refusal and the docstrings that name it and the pattern argument.
- `src/pyforge/marshal/seed/verbs/skips.py` -- `managed_after_skips` takes patterns; the private protocol is `_ManagedLike`.
- `src/pyforge/marshal/seed/verbs/adopt.py`, `src/pyforge/marshal/seed/verbs/update.py`, `src/pyforge/marshal/cli/seed.py` -- the skip wiring and `update --skip`.
- `src/pyforge/marshal/seed/migrate/registry.py` -- a docstring example that no longer constructed.
- `tests/unit/test_seed_{plan_types,plan_build,apply_run,verbs_preconditions,verbs_skips,verbs_adopt,verbs_update,cli_seed_update,migrate_registry}.py` and `tests/meta/test_sc08_never_write_update_proof.py` -- about 25 constructions gain the two fields, plus a test per criterion and per review pin.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-10-3-7, DW-10-4-4 and DW-10-4-5 closed with `resolved:` lines naming this story; `DW-marshal-82-12` ingested from this spec's `deferred:`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `.../spec-pyforge-core/.memlog.md` -- each names every changed governed path; no baseline stamped.

**Review findings.** Two passes.
- Pass 1: 26 findings, three of one root cause routed `bad_spec` (`update` was given no `--skip`; "no flag" had been read as "no CLI option"). The spec was amended outside the intent contract, the code was reverted and re-derived. The other pass-1 patch rows were folded into the amended Tasks.
- Pass 2: 30 findings after the re-derivation: no `bad_spec` or `intent_gap`. **Patches applied: 7 entries** covering 9 rows -- the mixed-run state-carry-over tests (one medium entry, found by two layers), the inverted test name, the `_HasArtifactId` rename, the "Pure and total" docstring, the overclaiming DW-10-4-5 line (found by two layers), the core memlog co-governor entry and stray token, and the docstring wrapping. **Deferred: 1 entry** (2 rows, `maybe-false`, medium if true, unverified): `update --skip` of a migration-claimed artifact still records the migration in `migrations_applied`; location `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:955`; tracked as `DW-marshal-82-12`. **Rejected: 19 rows**, each with its reason in the Review Triage Log (`patterns` default kept, `state.skips` unread by `adopt` too, visibility of a pattern-only skip, host paths in `plan.json`, library-seam surface for the first two criteria, and the four `false` rows).

**Follow-up review recommendation.** `followup_review_recommended: false`. Pass 2 patched no `high` entry and one `medium` entry (fewer than two), and the patches were tests, names, wrapping and text, none changing behaviour.

**Verification performed**, against HEAD `b9a84576a1` with a clean tree, every verdict read from an exit code written to a file.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 10677 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `python scripts/spec_surface_reconcile.py` -- exit 0 ("every tracked file governed or allowlisted; no drift"); `pixi run --frozen -e pyforge-guild spec-surface-check` -- exit 0; no `--write-baseline` run.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0 (ruff, ruff format, mypy over the ten packages).
- `deferred-work-check` first exited 2 (`spec-frontmatter-only-deferral`: the new `deferred:` entry had no ledger twin); `scripts/deferred_work_intake.py --fix --project marshal` ingested it as `DW-marshal-82-12`.
- Mutation: the implementation subagent reverted each fix in turn on a scratch copy of the package (the harness auto-checkpoints the worktree, so a mutation in place is not private) and recorded at least one new test failing for each; not independently re-run by the reviewer, whose Verification Gap layer read each test instead.

**Residual risks.**
- `run_apply` called alone on a directory target still raises the untyped `IsADirectoryError`; every verb runs the ladder first, and the intent confines the fix to rung 5.
- `update --skip` is per run: nothing reads `state.skips` (as for `adopt` today), so a later `update` without `--skip` refuses the hand-edit at rung 6 rather than remembering the skip.
- A pattern-only exemption (a skipped record with no action) leaves no line in the plan text or JSON, and a mistyped pattern still does nothing.
- `plan.json` now carries absolute host paths; it lives under `.marshal/`, covered by the packaged `.gitignore` region.
- The deferred `migrations_applied` question above.
- Not run: the full `pr-preflight` and the per-station coverage gate in this pass (the implementation subagent reported running the coverage gate on the first re-derivation, all seven touched modules at or above 80%; the reviewer did not re-run it); `dispatch/*` branches are supervisor-gated and skip the pre-push preflight.
