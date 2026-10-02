---
title: '82.12: Seed apply binds a plan to its repository, refuses a directory target with a remedy, and honours a skip on a hand-edit'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: 'c34cbda1919e96c2a9691404e0e794672d8b90b9'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
warnings: [oversized]
deferred: []
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
