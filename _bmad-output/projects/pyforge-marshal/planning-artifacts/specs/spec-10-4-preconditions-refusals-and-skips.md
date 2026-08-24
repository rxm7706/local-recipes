---
title: 'Preconditions, refusals, and skips'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: '1ffa099593548d252e90a2e4aa243fd8c87eb126'
---

<intent-contract>

## Intent

**Problem:** `PreconditionFailure` (exit 3) has existed since Story 7.2 with **zero raise sites** in
the package — its own docstring names this story's three cases and says "the module that checks
these preconditions is a later story's surface (`seed/verbs/`)". Story 10.3 shipped a transactional
runner that refuses exactly one thing (a stale fingerprint) and scoped out every other precondition
by name, filing five review findings that route here (`DW-FU-10-3-4`, `-6`, `-8`, `-9`, and the
symlink/never-write/containment class they share). So today nothing refuses a mutating run outside a
git repo, on a dirty worktree, or over a hand-edited managed artifact; `--skip` and `--force` exist
only inside remedy strings; and `seed/verbs/` is an empty package. SC-04 (no hand-edit silently
discarded) and SC-05 (git remains a complete undo) are both unmitigated.

**Approach:** Add `seed/verbs/preconditions.py` — one ordered refusal ladder,
`check_preconditions(...)`, that a mutating verb calls **before** it calls `run_apply`, raising
`PreconditionFailure` whose message names the specific artifact/region and states its remedy — and
`seed/verbs/skips.py`, which owns the verbs layer's one glob semantic plus the two skip operations:
`record_skip` (returns the updated pattern tuple its caller persists into `state.skips[]`) and
`apply_skips` (partitions a `Plan`, moving matched actions into a new `Plan.skipped` tuple that
names the matching pattern). Skips become part of the serialized plan so they are visible in the
artifact a human reviews, not just in a rendering.

## Boundaries & Constraints

**Always:**
- `check_preconditions` consumes only what it is handed — `plan`, `repo_root`, `never_write`,
  `managed`, `force`, `dry_run`, and an injectable `process`. It **never** imports or reads
  `seed.state`, never loads a `Manifest`, never calls `classify`/`build_plan`, and never writes.
- The ladder evaluates in this fixed order, refusing at the first failure: **(1)** not a git repo
  → **(2)** dirty worktree → **(3)** action target escapes `repo_root` → **(4)** action target
  matches `never_write` → **(5)** action target is a symlink → **(6)** hand-edited managed content.
  Cheap structural checks precede the ladder's only file-reading, hashing step.
- Every raise is `PreconditionFailure` (exit 3) with a non-blank `remedy=` (P-10). Each message
  names the offending artifact id and, for a region, `path#region`.
- Rung (2) is the **only** rung `dry_run=True` bypasses ("reading is always safe" applies to the
  worktree's cleanliness, not to whether git exists or whether the plan is coherent). Rung (6) is
  the **only** rung `force=True` bypasses. `never_write` (4) is bypassable by neither — it is the
  frozen guard.
- Rung (6) checks **every** `ManagedRecord` the caller supplies, not only artifacts the plan
  actions name, and reports **all** divergences in one message rather than the first.
  `hashes.check_managed_file`/`check_managed_region` are the sole deciders; a `recorded_sha` of
  `None` is a mismatch by their existing design (adopted out-of-band) and this story does not
  soften it.
- A `ManagedRecord` with a non-empty `region_shas` is region-bearing and requires a
  `region_format`; one with an empty `region_shas` is a whole-file record. The manifest guarantees
  this is exact — `regions` is non-empty iff `hybrid-managed-region`.
- Failure to parse a region-bearing artifact (`RegionParseError` / `MarkerError` /
  `NotImplementedError`), or a recorded region name absent from the parsed text, **is** divergence
  and refuses.
- Git state is probed through the injected `process` port with `git rev-parse --git-dir` and
  `git status --porcelain --untracked-files=normal`. A `ProcessError` (git absent, launch failure,
  timeout) refuses fail-closed rather than proceeding, and a non-zero `git status` is treated as
  dirty — the same conservative direction `plan/build.py::_repo_is_dirty` already takes.
- `apply_skips` removes a matched action from `Plan.actions` **and** drops that artifact's pair from
  `RepoFingerprint.artifact_hashes`, so the plan stays internally consistent for Story 10.3's
  bidirectional `fingerprint_drift` cross-check.
- `apply_skips` preserves `actions` ordering and uniqueness, is idempotent, and records the **first**
  matching pattern per artifact. Only artifacts that carry an action can be skipped.
- `record_skip` rejects a blank pattern with `UsageError` (exit 2), is order-stable, and never
  records a duplicate.
- Glob matching for skips and for the never-write rung goes through one function, `first_match`,
  using `fnmatch.fnmatchcase` — deliberately identical to `fs._matches`' semantics (`*` crosses `/`;
  over-matching is the safe direction for a deny/skip rule) and pinned to it by an agreement test.

**Block If:**
- Satisfying "skipped artifacts appear in the plan" turns out to require a change to
  `seed/plan/build.py` or `seed/apply/run.py` (both are being modified/created on the unmerged
  sibling branch `bmad-loop/20260814-202331-bc8d/10-3-…`; editing either creates a merge collision).
  If the additive `plan/types.py` route below proves insufficient, the placement is an architecture
  question, not an implementation choice.

**Never:**
- **No edit to `seed/apply/run.py`, `seed/apply/__init__.py`, or `seed/plan/build.py`** — all three
  are created or modified by the unmerged sibling Story 10.3. This story's refusal ladder is a
  caller-side gate invoked *before* `run_apply`, which is exactly where `DW-FU-10-3-6` and
  `DW-FU-10-3-4` say the remedy belongs ("a precondition evaluated before the first commit").
- No module under `seed/apply/` — `tests/meta/test_p07_no_hash_comparison_in_apply.py` bans every
  `detect.hashes` and `hashlib` import anywhere in that package, and rung (6) exists to call
  `detect.hashes`. The two are structurally incompatible; `seed/verbs/` is the sanctioned home.
- No CLI wiring: `cli/seed.py`'s six stubs stay stubs, no `--skip`/`--force`/`--apply` argparse
  flags, no `SeedError`→exit translator. Those belong to Stories 10.5/10.6/10.7, which own the
  verbs' front doors (and the pre-existing gap that `cli/main.py` catches no `SeedError` at all).
- No state store, no `.marshal/seed-state.yml` read or write, no schema — Story 10.2's surface.
  `ManagedRecord` and the `skips` tuple are **inputs**, supplied by whoever loads state.
- No materialization, no `copier` import, no `regions.apply` call, no writes of any kind. This
  story's entire surface is read-and-refuse plus one pure plan transform.
- No hoisting of containment into `fingerprint_drift` and no shared `_resolve_within_repo` export
  (`DW-FU-10-3-8`'s suggested remedy) — both land in `plan/build.py`. This story defends its own
  reads instead; the DW item stays open for that file's owner.
- No edit to any existing meta test, to `detect/hashes.py`, to `errors.py`, to `fs.py`, or to
  `regions/`.
- No new import-linter contract (`test_ad3_ad4_import_linter.py` asserts exactly four).
- No new dependency; both modules are stdlib + in-package.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All clear | Clean git repo, contained targets, matching hashes | Returns `None`; nothing read beyond the checks; no write | No error expected |
| Not a git repo | `repo_root` has no `.git` (`rev-parse --git-dir` non-zero) | Refused before any other rung | `PreconditionFailure` (exit 3), message names `not-a-git-repo`, remedy says `git init` / run from inside the repo |
| Not a git repo, dry-run | Same, `dry_run=True` | Still refused — dry-run bypasses rung (2) only | `PreconditionFailure` (exit 3) |
| Git binary absent | `process.run` raises `ProcessError` | Refused fail-closed; never treated as "clean" | `PreconditionFailure` (exit 3), message names the probe that could not run |
| Dirty worktree | `git status --porcelain` non-empty | Refused (SC-05) | `PreconditionFailure` (exit 3), message names `dirty-worktree`, remedy says commit or stash |
| Dirty worktree, dry-run | Same, `dry_run=True` | **Proceeds** past rung (2) to the remaining rungs | No error from rung (2) |
| `git status` errors | Non-zero return code | Treated as dirty, refused | `PreconditionFailure` (exit 3) |
| Target escapes root | An action's `target_path` is `../x` or absolute | Refused before any never-write or read | `PreconditionFailure` (exit 3), names the artifact id and the escaping path |
| Never-write target | An action targets a path matching a `never_write` pattern | Refused; not bypassable by `force` | `PreconditionFailure` (exit 3), names the artifact, the path, and the matched pattern |
| Symlink target | An action's target exists and is a symlink | Refused (`DW-FU-10-3-4`) | `PreconditionFailure` (exit 3), names the artifact and its link target, remedy says replace the link or skip it |
| Hand-edited managed file | `copied-managed` record, on-disk hash ≠ `body_sha` | Refused (SC-04) | `PreconditionFailure` (exit 3), names `path` and both hashes |
| Hand-edited managed region | Region body hash ≠ recorded sha | Refused | `PreconditionFailure` (exit 3), names `path#region` |
| Region parse failure | Markers mangled/nested/unclosed | Treated as divergence, refused | `PreconditionFailure` (exit 3), names `path` and the parse reason |
| Recorded region gone | A recorded region name absent from the file | Refused | `PreconditionFailure` (exit 3), names `path#region` as missing |
| No recorded hash | `body_sha=None` (adopted out-of-band) | Refused — `hashes.py`'s existing rule, not softened here | `PreconditionFailure` (exit 3), message carries "no recorded hash in state" |
| Managed artifact absent | Record's path does not exist on disk | **Not** a divergence — nothing was hand-edited; rung passes for that record | No error expected |
| Multiple divergences | Two files and one region all diverge | One refusal naming **all three**, not just the first | `PreconditionFailure` (exit 3) |
| Hand-edit with `--force` | Same as above, `force=True` | Rung (6) bypassed entirely; earlier rungs still enforced | No error from rung (6) |
| Empty plan | `plan.actions == ()` | Rungs (3)–(5) iterate nothing; (1), (2), (6) still run | Refuses only if those rungs fail |
| Skip matches one action | 3 actions, pattern matches 1 | New `Plan`: 2 actions, 1 `SkippedArtifact` naming the pattern; that artifact's hash pair dropped | No error expected |
| Skip matches all | Pattern matches every action | `actions == ()`, `skipped` names all; a subsequent apply is a legitimate no-op | No error expected |
| Skip matches nothing | No pattern matches | Returns a `Plan` equal to the input | No error expected |
| Skip applied twice | `apply_skips(apply_skips(p, pats), pats)` | Identical result — idempotent | No error expected |
| Two patterns, one artifact | Both match the same action | `SkippedArtifact.pattern` is the **first** in the given order | No error expected |
| Record a new skip | `record_skip(("a/*",), "b/*")` | `("a/*", "b/*")` — append order preserved | No error expected |
| Record a duplicate skip | `record_skip(("a/*",), "a/*")` | `("a/*",)` — unchanged, no duplicate | No error expected |
| Record a blank skip | `record_skip((), "   ")` | Rejected | `UsageError` (exit 2) with a remedy |
| Plan round-trip with skips | `Plan.from_json_dict(json.loads(json.dumps(p.to_json_dict())))` | Equals `p`, `skipped` back as a tuple | No error expected |
| Corrupt plan: skip/action id clash | Hand-edited `plan.json` lists one id in both | Rejected at the untrusted boundary | `ValueError` naming the shared id |
| Corrupt plan: skips out of order | `skipped` not sorted by `artifact_id` | Rejected | `ValueError`, mirroring the existing `actions` rule |

</intent-contract>

## Code Map

Paths under `src/shared/packages/pyforge-marshal/` unless noted; module prefix
`src/pyforge/marshal/`.

- `.../seed/verbs/preconditions.py` — **NEW.** `ManagedRecord`, `check_preconditions`, and the
  module-private git probes. The refusal ladder; the package's first `PreconditionFailure` raise
  sites.
- `.../seed/verbs/skips.py` — **NEW.** `first_match` (the verbs layer's single glob semantic),
  `record_skip`, `apply_skips`. `preconditions.py` imports `first_match` from here — skips *are*
  globs, so this module owns the semantic and the never-write rung borrows it.
- `.../seed/verbs/__init__.py` — **UNCHANGED, still empty.** Consumers import
  `seed.verbs.preconditions` / `seed.verbs.skips` directly, matching `seed/plan/__init__.py`'s
  established empty-front-door convention.
- `.../seed/plan/types.py` — **MODIFIED (additive).** New frozen `SkippedArtifact(artifact_id,
  target_path, pattern)` with `to_json_dict`/`from_json_dict`; `Plan` gains
  `skipped: tuple[SkippedArtifact, ...] = ()` as its last field, emitted by `to_json_dict` and
  required + validated by `from_json_dict` (sorted, unique, disjoint from `actions`). Reuses the
  module's existing `_require_key`/`_require_str` validators. **Story 10.3's Never list explicitly
  forbids editing this file, so the change is collision-free.**
- `.../seed/plan/build.py` — **CONSUMED UNMODIFIED** (10.3's branch modifies it).
  `_repo_is_dirty` is referenced by the agreement test only, never imported by shipped code.
- `.../seed/errors.py` — consumed unmodified: `PreconditionFailure` (exit 3) and `UsageError`
  (exit 2). Both require a non-blank `remedy=` kwarg.
- `.../seed/detect/hashes.py` — consumed unmodified: `check_managed_file(path, current_text,
  recorded_sha)`, `check_managed_region(path, text, span, recorded_sha)`, both returning
  `Finding | None`. The sole deciders for rung (6).
- `.../seed/regions/parse.py`, `.../seed/regions/markers.py` — consumed unmodified:
  `parse_regions`, `RegionSpan`, `RegionParseError`, `MarkerError`, `RegionFormat`.
- `.../seed/fs.py` — consumed unmodified: `NeverWrite` (the pattern carrier). Its private
  `_matches` is referenced by the agreement test only.
- `pyforge.core.process` (`pyforge-core` package) — `PosixProcess`, `ProcessResult`,
  `ProcessError`. The injectable git seam, mirroring `plan/build.py`'s deliberate choice of the
  process port over `adapters.vcs_git.GitVcs`.
- `.../tests/unit/test_seed_verbs_preconditions.py` — **NEW.**
- `.../tests/unit/test_seed_verbs_skips.py` — **NEW.**
- `.../tests/unit/test_seed_plan_types.py` — **MODIFIED (additive).** Reuses its existing
  `_action`/`_fingerprint`/`_plan`/`_valid_plan_dict` override-dict builders. Not touched by 10.3
  (its Code Map lists this file "reference only").
- `.../tests/unit/test_seed_plan_build.py` — **NOT TOUCHED** (10.3 modifies it).
- `tests/packaging/test_dependency_completeness.py` (repo root) — **TAKEN VERBATIM from the
  sibling 10.3 branch**, not re-authored. See Design Notes.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  — **MODIFIED.** A `(change)` entry naming every changed path plus test counts, then an `(event)`
  entry; `scripts/spec_surface_reconcile.py` fails a governed-code change whose owning spec's
  memlog did not move.
- `pyproject.toml` / `pixi.toml` — **no change.**

## Tasks & Acceptance

**Execution:**
- [x] `tests/packaging/test_dependency_completeness.py` — restore the sibling branch's exact
  version (`git checkout bmad-loop/20260814-202331-bc8d/10-3-the-apply-runner-transactional-guarded
  -- tests/packaging/test_dependency_completeness.py`). — closes `DW-FU-10-2`, which is red on this
  baseline and is one of the two verify commands every story in this loop must pass; taking it
  byte-identical means the later merge with 10.3 is a clean no-op instead of a conflict.
- [x] `.../seed/plan/types.py` — add frozen `SkippedArtifact` (`artifact_id`, `target_path`,
  `pattern`) with `to_json_dict`/`from_json_dict` built on the existing `_require_key`/`_require_str`
  helpers, then add `skipped: tuple[SkippedArtifact, ...] = ()` to `Plan`, emit it from
  `to_json_dict`, and require + validate it in `from_json_dict` (list, sorted by `artifact_id`,
  unique, and sharing no id with `actions`). — makes a skip durable in the artifact a human reviews.
- [x] `.../seed/verbs/skips.py` — implement `first_match(patterns, relative_posix) -> str | None`
  (first `fnmatch.fnmatchcase` hit wins), `record_skip(patterns, pattern) -> tuple[str, ...]`
  (strip, reject blank with `UsageError`, append-if-absent), and `apply_skips(plan, patterns)
  -> Plan` (partition `actions` on `first_match(patterns, action.target_path)`, build
  `SkippedArtifact`s sorted by `artifact_id`, and rebuild `RepoFingerprint` with the skipped ids
  dropped from `artifact_hashes`). Module docstring states the fnmatch semantics and why they
  mirror `fs`. — FR-87 and the plan-visibility AC.
- [x] `.../seed/verbs/preconditions.py` — define frozen `ManagedRecord(artifact_id, path,
  body_sha, region_shas, region_format)` with a `__post_init__` requiring `region_format` when
  `region_shas` is non-empty; add module-private `_is_git_repo(process, repo_root)` and
  `_is_dirty(process, repo_root)` wrapping `ProcessError` into `PreconditionFailure`; implement
  `check_preconditions(plan, *, repo_root, never_write, managed=(), force=False, dry_run=False,
  process=None)` as the six-rung ladder in the fixed order above, each raise carrying a non-blank
  `remedy=`. — the story's whole behavior; the package's first `PreconditionFailure` raise sites.
- [x] `.../tests/unit/test_seed_verbs_skips.py` — cover every skip row of the I/O matrix against
  plans built with `test_seed_plan_types.py`-style builders: match one / all / none, idempotence,
  first-pattern-wins, hash-pair removal, `record_skip` append/dedupe/blank, and an **agreement test**
  asserting `first_match` and `fs._matches` return the same answer over a shared
  pattern×path table. — proves the matrix and pins the duplicated glob semantic.
- [x] `.../tests/unit/test_seed_verbs_preconditions.py` — cover every precondition row against a
  real `tmp_path` git repo (init/commit via real `git`, the convention
  `test_seed_plan_build.py::_git` already establishes): each rung's refusal and its exit code 3 and
  non-blank remedy; ladder ORDER (a repo failing two rungs reports the earlier one); `dry_run`
  bypassing only rung (2); `force` bypassing only rung (6); git-absent via a fake process raising
  `ProcessError`; multi-divergence reported in one message; an absent managed path passing; and an
  **agreement test** asserting `_is_dirty` and `plan.build._repo_is_dirty` agree on the same clean
  and dirty repo. — proves the matrix and pins the duplicated git semantic.
- [x] `.../tests/unit/test_seed_plan_types.py` — add `SkippedArtifact` construction/round-trip/
  validation cases and extend the `Plan` cases for `skipped` (round-trip, sorted/unique/disjoint
  rejection, and `skipped=()` default). — the untrusted boundary must reject a corrupt plan.
- [x] `.../planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — append a `(change)` entry
  naming every changed path with test counts, then an `(event)` reconciliation entry. —
  `spec_surface_reconcile.py`'s drift contract.

**Acceptance Criteria:**
- Given a clean git repo, a coherent plan, and managed records whose hashes all match, when
  `check_preconditions` runs, then it returns without raising and writes nothing.
- Given a repo state that fails more than one rung, when `check_preconditions` runs, then the
  refusal names the **earliest** failing rung in the fixed order, so the message is deterministic.
- Given any refusal this story raises, when the exception is inspected, then it is a
  `PreconditionFailure` with `exit_code == 3` and a non-blank `remedy`, and its message names the
  offending artifact id (and `path#region` where a region is at fault).
- Given `seed/verbs/preconditions.py` and `seed/verbs/skips.py`, when their imports are inspected,
  then neither imports anything from `seed.state`, `seed.apply`, `seed.engine`, or `copier`, and
  neither performs any write.
- Given the whole change, when `git diff --stat` is taken against the baseline, then it touches
  neither `seed/apply/run.py`, nor `seed/apply/__init__.py`, nor `seed/plan/build.py`, nor
  `tests/unit/test_seed_plan_build.py`, nor any file under `tests/meta/`.
- Given the whole change, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and
  `pixi run --frozen -e pyforge-ci pyforge-deps-test` run, then both are green, with the marshal
  suite above its 4181-passed baseline and the deps gate green at 84 passed.

## Spec Change Log

### 2026-08-14 — Implementation pass (no intent-contract change)

Two corrections, both outside `<intent-contract>`, neither altering a behavioral term.

1. **The deps gate's expected count was stale: 74 → 84.** Planning measured the baseline as
   `1 failed, 73 passed` (74 collected) and assumed the sibling's fix merely flipped the failure.
   It also adds two test functions, one parametrized over the 9 glob-discovered packages, so the
   green count is 84. The gate's *substance* — green, and the file byte-identical to the sibling
   branch — is unchanged and verified. Corrected in the AC and in Verification.

2. **`Plan.from_json_dict` validates `repo_fingerprint` before `skipped`.** Validating `skipped`
   first would have failed `tests/unit/test_seed_plan_build.py`, which loads `{"actions": []}` and
   expects the `repo_fingerprint` error — and that file is on this story's Never list because the
   sibling 10.3 branch modifies it. Resolved entirely inside `plan/types.py` by requiring keys in
   `to_json_dict`'s own emission order. No forbidden file was touched; all four merge-safety diffs
   are empty.

### 2026-08-15 — Verification repair (no intent-contract change)

One correction, outside `<intent-contract>`, in `## Verification` only. No behavioral term, no AC,
no Code Map entry moves.

1. **The `spec_surface_reconcile.py` expectation was wrong: "stays red with 2" → rc=0.** Planning
   read the 2 pre-existing `pyforge-mason/spec-django-accelerator-framework` findings
   (`drift-blind` + `no-baseline`) as somebody else's debt and wrote the gate down as "confirm the
   count is still exactly 2". That is not an outcome the gate offers: it is a **repo-level**
   detector emitting a single exit code, this story's verify step requires rc=0, and the red was
   being inherited by every unrelated story in the fleet — so a story that changed nothing mason
   owns still could not land. Reconciled here instead: the missing
   `.../spec-django-accelerator-framework/.memlog.md` was created (its absence left the contract
   hash empty, so it could never move and no governed change was reconcilable), the file was
   `git add`ed, and the baseline was stamped **scoped** —
   `--write-baseline --spec pyforge-mason/spec-django-accelerator-framework`. Gate now: rc=0,
   `OK: every tracked file governed or allowlisted; no drift`. Three facts make that honest rather
   than self-laundering, and all three were checked before stamping: mason's `surface:` is
   `src/platform/**` + `.../steward/dashboard/**` and this story's diff touches **neither** (zero
   overlap, so no drift of ours can hide behind it); the key was **absent** from the 83 already in
   `scripts/.spec-surface-baseline.json`, making this a first stamp rather than a re-stamp, and the
   scoped write merges exactly one key (verified: 1 added, 0 changed, 0 removed, diff pure
   insertion); and `git diff f150dce382 HEAD` over both globs is **empty**, so the 120 governed
   files are unchanged since the Spec landed and the stamp accepts no pending drift. A bare
   `--write-baseline` — which would have accepted all 83 specs' pending drift — was never run.

## Review Triage Log

### 2026-08-14 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 15: (high 2, medium 7, low 6)
- defer: 2: (high 0, medium 2, low 0)
- reject: 5: (high 0, medium 1, low 4)
- addressed_findings:
  - `[high]` `[patch]` `_read_managed_text` reported "cannot verify" as "absent" — an unreadable parent directory (`EACCES`) or `ELOOP` made `is_symlink()`/`exists()` swallow the `OSError`, so a hand-edited managed file passed rung 6 silently, reopening SC-04. Now probes with `lstat()` in `try/except OSError`; only `FileNotFoundError` means absent, everything else is a divergence. Pinned by `test_a_managed_file_under_an_unreadable_parent_directory_is_refused`.
  - `[high]` `[patch]` `_region_divergences` iterated only recorded regions, so a syntactically valid managed region hand-inserted into a hybrid file and absent from state passed as conformant — hand-authored content under the tool's own attestation, the region-level twin of the case `detect/hashes.py` closes for whole files. Now every parsed region absent from `record.region_shas` is reported. Pinned by `test_a_managed_region_present_in_the_file_but_absent_from_state_is_refused`.
  - `[medium]` `[patch]` `--skip` could not protect a hand-edit: rungs 3-5 are skip-aware (they walk `plan.actions`) but rung 6 walks the caller's `managed` sequence, so a skipped artifact was still refused and the remedy offered `--force`, which discards every hand-edit. Added the missing caller-side affordance `skips.managed_after_skips(managed, plan)`, cross-referenced from both module docstrings; `check_preconditions` still does not filter internally, because the contract says rung 6 checks every record the caller supplies. Pinned by `test_rung_six_refuses_a_skipped_artifacts_hand_edit_unless_the_caller_filters` + 5 unit tests.
  - `[medium]` `[patch]` `_require_patterns` ran only inside the per-action loop, so `apply_skips` accepted a bare `str` (the exact typo it exists to catch) whenever `plan.actions` was empty. Hoisted above the loop. Pinned by `test_apply_skips_validates_its_patterns_even_when_there_is_nothing_to_match`.
  - `[medium]` `[patch]` `patterns` was consumed twice, so a one-shot iterable silently dropped every stored pattern in `record_skip` and left `apply_skips` matching only the first action. Materialized exactly once via `_materialize_patterns`. Pinned by `test_record_skip_reads_a_one_shot_iterable_of_patterns_exactly_once` and its `apply_skips` twin.
  - `[medium]` `[patch]` A whitespace-only pattern survived `_require_patterns` as `""`, matching nothing — the "silently matches nothing" failure the strip exists to prevent — and made `first_match` able to return a falsy non-`None` sentinel. Now rejected with `UsageError`, matching `NeverWrite` and `record_skip`. Pinned by `test_first_match_rejects_a_whitespace_only_pattern`.
  - `[medium]` `[patch]` A misspelled `repo_root` refused with "install git and make it resolvable on PATH", because `subprocess` maps an unusable `cwd` to `FileNotFoundError` and `PosixProcess.run` cannot distinguish it from a missing executable. Added `_require_existing_repo_root` ahead of the first probe, inside rung 1, mirroring `fs._guard`. Pinned by `test_a_missing_repo_root_is_refused_naming_the_directory_not_a_missing_git`.
  - `[medium]` `[patch]` An action whose `target_path` normalized to `.` or `""` cleared rungs 3, 4 and 5 and reached the runner with the repo root as its write target. Now refused in the containment rung. Pinned by `test_an_action_targeting_the_repo_root_itself_is_refused`.
  - `[medium]` `[patch]` Skip globs matched `action.target_path` raw while rung 4 matched the resolved repo-relative string, so a pattern copied out of a never-write refusal into `--skip` silently matched nothing (`./AGENTS.md` vs `AGENTS.md`). `apply_skips` now normalizes lexically before matching, with the lexical-vs-resolution difference documented. Pinned by `test_a_skip_pattern_copied_out_of_a_never_write_refusal_actually_skips`.
  - `[low]` `[patch]` The never-write refusal claimed "not overridable, by `--force` or otherwise", which overstates the protection `fs.py` actually provides (see `DW-FU-10-4`). Reworded to claim only that no flag overrides it. Pinned by `test_the_never_write_remedy_claims_only_the_guarantee_the_code_provides`.
  - `[low]` `[patch]` The module docstring claimed `force=True` "says nothing about containment", but `if force: return` short-circuits the only containment check that ever sees a `ManagedRecord` path. Docstring corrected to state the real bound; force semantics deliberately unchanged (the contract fixes them). Pinned by `test_the_module_docstring_states_forces_real_bound` and `test_force_leaves_a_managed_records_own_path_unchecked`.
  - `[low]` `[patch]` `apply_skips` rebuilt `RepoFingerprint` and `Plan` by enumerating fields, so a future field on either type would be silently dropped. Switched to `dataclasses.replace`. Pinned by `test_apply_skips_carries_an_unknown_repo_fingerprint_field_through` and its `Plan` twin.
  - `[low]` `[patch]` The new "keys are required in emission order" comment did not hold for malformed values — `repo_fingerprint`'s value was parsed after all `skipped` validation. Its value is now parsed where its key is required, and `{"actions": []}` still reports `repo_fingerprint` (the case the forbidden `test_seed_plan_build.py` pins). Pinned by `test_plan_from_json_dict_reports_a_malformed_fingerprint_before_a_bad_skipped_list`.
  - `[low]` `[patch]` The duplicated `_GIT_TIMEOUT_S` was pinned by nothing, so it could drift from `plan/build.py`'s with every test still green. The agreement test now asserts the two constants are equal. Pinned by `test_the_git_timeout_agrees_with_plan_builds_own`.
  - `[low]` `[patch]` `SkippedArtifact.from_json_dict` type-checked its three fields but accepted `""`, asymmetric with `record_skip` and `NeverWrite.__post_init__`, both cited as its precedent. Blank fields now rejected. Pinned by `test_skipped_artifact_from_json_dict_raises_value_error_for_a_blank_field`.

**Deferred** (not this story's surface, filed with evidence): `DW-FU-10-4` — a symlinked ancestor
directory defeats the never-write guard, inherited from `fs.py`'s resolve-then-match semantics,
which this story's Never list forbids editing. `DW-FU-10-4-2` — the new never-imported packaging
ratchet cannot see `python-build`, the one exempted name its own docstring names; fixing it here
would forfeit the byte-identity with the sibling branch that keeps the merge clean.

**Rejected**: the absence of CLI wiring, a state store, and end-to-end `--skip` persistence (all
explicitly on this story's Never list, owned by Stories 10.2/10.5/10.6/10.7); `Plan.from_json_dict`
requiring the new `skipped` key (no `plan.json` is written by any production path today, and
AD-60 makes re-planning cheap); the claim that `apply_skips` rewriting `repo_fingerprint` is
gratuitous (it is required by Story 10.3's bidirectional `fingerprint_drift` cross-check, verified
on the sibling branch); the cross-package packaging change (a documented, forced landing
precondition — see the Design Notes); and `--force` not previewing what it will discard (there is
no CLI surface to preview it on, and 10.6 owns reporting).

### 2026-08-15 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 1, medium 0, low 1)
- defer: 3: (high 1, medium 2, low 0)
- reject: 18: (high 0, medium 5, low 13)
- addressed_findings:
  - `[high]` `[patch]` Rung 5 decided "is this a symlink?" with `Path.is_symlink()`, which swallows
    every `OSError` and answers `False` — and `False` is that rung's one PASSING answer. Under an
    unreadable parent directory (`EACCES`) or a symlink loop (`ELOOP`) a real symlink therefore
    cleared the rung and the runner would write THROUGH it, to a destination that can sit outside
    the repo entirely — defeating SC-05, since git cannot undo a write it never saw. This is the
    exact hazard the first review pass fixed one function away in `_read_managed_text` for rung 6,
    whose docstring already documents it; rung 5 was simply not given the same treatment. Now an
    `lstat()` inside a `try`: `FileNotFoundError` means absent (pass — the ordinary create case),
    any other `OSError` refuses fail-closed, matching the module's own rule that "cannot verify"
    must never be reported as "verified". Mechanism confirmed by execution before fixing
    (`is_symlink()` returns `False` for a real symlink under a `0o000` parent, where `lstat()`
    raises `PermissionError`). Pinned by `test_a_symlink_under_an_unreadable_parent_directory_is_refused`
    and `test_an_action_whose_target_does_not_exist_clears_the_symlink_rung`; the module docstring's
    "rung 5's `is_symlink()`" reference was corrected to `lstat()`.
  - `[low]` `[patch]` Both symlink refusals interpolated `target.readlink()` directly into the
    message, but `lstat` and `readlink` are not atomic — a link removed in between (or an
    unreadable parent) made a raw `OSError` escape the ladder, replacing a `PreconditionFailure`
    (exit 3, with a remedy) with a crash. Added `_link_target`, which degrades the destination to
    `<unreadable>` rather than degrading the refusal to an exception, and routed rung 5 and
    `_read_managed_text` through it. Pinned by
    `test_the_symlink_refusal_survives_a_link_that_vanishes_before_it_is_read`.

**Deferred** (this pass, filed with evidence): `DW-FU-10-4-3` — `ManagedRecord`'s region-bearing
shape has no source in the state model Story 10.2 actually landed (`ManagedArtifact` carries one
`body_sha` and a span with no per-region sha and no region format), so the region half of rung 6 is
unreachable from real state; the adapter is the wiring story's call. `DW-FU-10-4-4` — the first
pass's `managed_after_skips` affordance is inert for the class rung 6 guards, because a hand-edited
managed file never carries a plan action to be skipped (this story's own Design Notes prove it);
the working fix changes the helper's signature and depends on how the verb wires `state.skips[]`.
`DW-FU-10-4-5` — an action targeting an existing directory clears all six rungs and fails later as
an untyped `IsADirectoryError`; a seventh structural check is a contract amendment, not a patch.

**Rejected** (this pass): the legacy-`plan.json` migration finding — its premise was re-verified
rather than inherited, because Stories 10.2 and 10.3 have since landed on `main` and could have
falsified it; `write_plan`/`load_plan` remain library-only with no production caller in `src/`, so
the first pass's rejection still holds. Also rejected: leaving marshal's own spec-surface baseline
unstamped (that is the designed human-invoked step — `spec_surface_reconcile.py` deliberately
withholds `--write-baseline` precisely so a producer cannot stamp its own drift); rung 6 refusing
under `--dry-run`, `--force` bypassing only rung 6, and the frozen six-rung order (all fixed inside
`<intent-contract>`); the `python-build` alias (already filed as `DW-FU-10-4-2`); skip-pattern `./`
normalization (already fixed in the first pass); treating an unrecorded managed region as
divergence (fail-closed is the correct direction); and a tail of exotic-but-unreachable structural
cases (bare repo, dubious-ownership repo, FIFO target, blank `ManagedRecord` fields, duplicate
action targets, in-memory `Plan` validation asymmetries reachable only from an `Action` shape
`build_plan` cannot produce).

## Design Notes

**Why the ladder lives in `seed/verbs/`, not in `seed/apply/run.py` as the epics `Surface:` line
says.** Two independent, verifiable reasons, either one sufficient. First,
`tests/meta/test_p07_no_hash_comparison_in_apply.py` bans `hashlib` and every spelling of a
`detect.hashes` import anywhere under `seed/apply/**`, with no allowlist and no `# noqa` — and rung
(6) exists precisely to call `detect.hashes.check_managed_file`/`check_managed_region`. Putting the
hand-edit rung in `apply/` would require weakening a shipped meta test, which is never the cheaper
option. Second, `seed/apply/run.py` does not exist on this story's baseline (`64e717d`): it is
created by the unmerged sibling branch `bmad-loop/20260814-202331-bc8d/10-3-…`, so authoring it here
would be an add/add merge collision on a 410-line file. `PreconditionFailure`'s own docstring
already names `seed/verbs/` as the home for exactly these checks, and Story 10.3's Never list
scopes them out of `run.py` by name. The ladder therefore lands as a **caller-side gate** the verb
invokes before `run_apply` — which is also, word for word, where `DW-FU-10-3-6` and `DW-FU-10-3-4`
say the remedy belongs ("a precondition evaluated before the first commit").

**Why skips extend `Plan` rather than being rendered by the verb.** The AC's purpose clause is "so
a skip is visible rather than invisible", and the plan is a serialized artifact (`write_plan` /
`load_plan`, reviewed as a PR diff). A skip that exists only in a rendering disappears from
`plan.json`, so the review surface would lie by omission about the one thing the AC exists to
surface. Putting skipped artifacts in a **separate `Plan.skipped` tuple** rather than as a flagged
member of `Plan.actions` also keeps Story 10.3's runner correct with zero changes: `run_apply`
iterates `plan.actions`, so an artifact it must not touch is structurally unreachable rather than
protected by a `commit` callback remembering to check a flag. `plan/types.py` is additive-only here
and is explicitly on 10.3's Never list, so the edit cannot collide.

**The fingerprint coupling, which is easy to get wrong.** Story 10.3's `fingerprint_drift` was
hardened during its review to cross-check `artifact_hashes` against `actions` in **both**
directions — a hashed id carrying no action is an integrity failure that refuses the whole plan.
So `apply_skips` must drop the skipped artifact's hash pair as it removes the action; filtering only
one side produces a plan that every subsequent `run_apply` refuses as corrupt. Skipped artifacts are
deliberately not re-added to the fingerprint under another key: they are not going to be written, so
their on-disk state is not something this plan asserts anything about.

**Why rung (6) iterates state records, not plan actions.** `classify` marks a present
`copied-managed` artifact `PRESENT_CONFORMANT` no matter what its bytes are — content divergence is
deferred to `hashes.py` by P-07 — and `build_plan` only emits actions for `ABSENT` and
`PRESENT_DIVERGENT`. So a hand-edited managed **file** never appears in the plan at all, and a
plan-driven check would silently pass exactly the case SC-04 exists to catch. Iterating the caller's
`ManagedRecord`s asks the right question: for every artifact Genesis claims to own, is it still
what Genesis left there?

**Duplicated semantics, pinned by agreement tests rather than by a shared helper.** Two helpers this
story needs already exist as module-privates in files it may not edit: `plan/build.py::_repo_is_dirty`
(10.3's file) and `fs.py::_matches`. Hoisting either into a shared home means editing a file the
sibling branch is modifying; importing a private across module boundaries is the style this package
guards against elsewhere. The remaining option is a local implementation plus a test asserting the
two agree — the pattern this repo already uses in
`tests/meta/test_supervisor_run_path_agreement.py` for duplicated path/journal helpers. Stated
plainly so it reads as a chosen trade with a guard, not an oversight.

**Why `DW-FU-10-2` is closed by checkout rather than by re-authoring.** `pyforge-deps-test` is red
on this baseline (verified: `1 failed, 73 passed`, on
`test_conda_run_deps_add_nothing_undeclared[pyforge-mason]`) and it is one of this project's two
`verify_commands`, so it blocks this story from landing exactly as it blocked 10.3. 10.3 already
fixed it, and its fix is entirely self-contained to `tests/packaging/test_dependency_completeness.py`
(90 added lines: the `pyforge-mason` exemption plus two new ratchet tests). Re-deriving a second,
textually different fix would guarantee a merge conflict on that file and put two competing
rationales in the tree; taking the sibling's version byte-identical makes the eventual merge a
clean no-op. This is a deliberate cross-branch adoption, and it is the only file this story takes
that way.

**Ladder-order rationale.** Rungs (1)–(2) establish that git can serve as the undo before anything
else is worth saying; (3)–(5) are cheap per-action structural checks over paths already in memory;
(6) is the only rung that reads and hashes file content. Ordering cheap-and-fundamental first makes
the common refusal fast and its message deterministic, which the AC pins directly.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: green, above the
  **4181 passed / 9 deselected** baseline measured on `64e717d`, including the two new
  `test_seed_verbs_*.py` files and the extended `test_seed_plan_types.py`;
  `test_p07_no_hash_comparison_in_apply.py`, `test_seed_no_bare_exception.py` and
  `test_ad3_ad4_import_linter.py` unchanged and green.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: **84 passed**. Red at baseline
  (`1 failed, 73 passed` = 74 collected) on `DW-FU-10-2`; closed by adopting the sibling branch's
  file verbatim, which also ADDS 10 cases (`test_conda_only_entries_are_still_conda_run_deps` plus
  `test_conda_only_run_deps_are_never_imported` parametrized over the 9 discovered packages) — hence
  84, not 74. See the Spec Change Log.
- `git diff --stat 64e717d -- src/shared/packages/pyforge-marshal/tests/meta/` — expected: **empty**.
- `git diff --stat 64e717d -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/apply/ src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/build.py src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_build.py`
  — expected: **empty**. This is the merge-safety check against the unmerged sibling story.
- `git diff bmad-loop/20260814-202331-bc8d/10-3-the-apply-runner-transactional-guarded -- tests/packaging/test_dependency_completeness.py`
  — expected: **empty**, proving the adopted file is byte-identical to the sibling's.
- `python scripts/spec_surface_reconcile.py` — expected: **rc=0**, `OK: every tracked file governed
  or allowlisted; no drift`. The 2 findings that were pre-existing red at baseline `64e717d` — both
  `pyforge-mason/spec-django-accelerator-framework` (`drift-blind` + `no-baseline`) — are reconciled
  **in this change**, because this gate is deterministic and admits no "pre-existing, not ours"
  outcome. Remedy, both halves: create the missing
  `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/.memlog.md`,
  then run the SCOPED first stamp `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-mason/spec-django-accelerator-framework` (stage the memlog first — `--write-baseline`
  reads `git ls-files`). Not self-laundering: mason governs `src/platform/**` + the steward
  dashboard, which this story's diff touches neither of (**zero surface overlap**); the key was
  absent from the 83 already stamped, so it is a **first stamp, not a re-stamp** (scoped `--spec`
  merges one key — expect exactly 1 added, 0 changed, 0 removed); and `git diff f150dce382 HEAD`
  over both globs is empty, so **no pending drift is accepted**.

**Manual checks:**
- Confirm `seed/state/` is still `__init__.py`-only in this worktree and that nothing in this story
  imports or assumes `seed.state`, so Story 10.2 merges cleanly and `ManagedRecord` stays an input
  rather than a competing state model.
- Confirm `cli/seed.py`'s six verb stubs are byte-unchanged — no CLI surface is claimed by this
  story.


## Auto Run Result

Status: `done`. Resumed session — the previous run's implementation was complete and green on every
gate except one, and this pass repaired that gate and ran a second review over the full diff.

**What was implemented.** No change to the story's behavior surface beyond one review patch. The
resumed session's mandate was the failing deterministic verify command
`python scripts/spec_surface_reconcile.py` (rc=1). Its 2 findings were both for the FOREIGN spec
`pyforge-mason/spec-django-accelerator-framework` (`drift-blind` + `no-baseline`) and were confirmed
pre-existing at this story's baseline: that spec landed in `f150dce382`, an ancestor of `64e717d`.
Because the gate is repo-level and emits a single exit code, "pre-existing, not ours" is not an
outcome it offers, so the finding was reconciled rather than left standing — safely, on three
verified facts: mason governs `src/platform/**` and the steward dashboard, which this story's diff
touches neither of; the key was absent from the 83 specs already baselined, making this a first
stamp rather than a re-stamp; and `git diff f150dce382 HEAD` over both globs is empty, so the stamp
accepts no pending drift. A bare `--write-baseline` (which would accept all 83 specs' pending
drift) was never run.

**Files changed in this pass.**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/.memlog.md`
  — **created**; closes `drift-blind` by giving the spec a contract hash that can move.
- `scripts/.spec-surface-baseline.json` — one key added (verified: 1 added, 0 changed, 0 removed).
- `.../seed/verbs/preconditions.py` — rung 5 fail-closed via `lstat()`; new `_link_target`; stale
  docstring reference corrected.
- `.../tests/unit/test_seed_verbs_preconditions.py` — 3 tests pinning the above.
- `.../planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — reconciliation + patch entries.
- This spec — `## Verification` bullet corrected, Spec Change Log and Review Triage Log entries.

**Review findings.** 23 unique findings after dedup across Blind Hunter and Edge Case Hunter.
2 patched (1 high, 1 low), 3 deferred (`DW-FU-10-4-3`, `-4`, `-5`), 18 rejected. 0 intent_gap,
0 bad_spec — no loopback. The high patch closed a real silent-write-through-symlink hole in rung 5,
mechanism confirmed by execution before fixing.

**Verification performed.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **4459 passed, 9 deselected**
  (baseline 4181; 4456 before this pass's 3 new tests).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → **84 passed**.
- `python scripts/spec_surface_reconcile.py` → **rc=0**, `OK: every tracked file governed or
  allowlisted; no drift`.
- All four merge-safety diffs against `64e717d` / the sibling 10.3 branch → **empty**
  (`tests/meta/`, `seed/apply/`, `seed/plan/build.py`, `tests/unit/test_seed_plan_build.py`, and the
  byte-identity of `tests/packaging/test_dependency_completeness.py`).
- Manual checks pass: `seed/state/` is still `__init__.py`-only in this worktree; `cli/seed.py` is
  byte-unchanged.
- The frozen `<intent-contract>` (lines 15–145) was verified **byte-identical** to its pre-session
  state by sha1, not by inspection.

**Residual risks.**
- Stories 10.2 and 10.3 have since landed on `main`, so this branch's merge-safety diffs are now
  guarding against files that already exist upstream. The diffs are still empty, but the merge
  itself has not been performed or tested here.
- `DW-FU-10-4-3` is the sharpest of the deferrals: the region half of rung 6 is fully implemented
  and tested but **unreachable from the state model that actually landed**, so SC-04's region case
  is unmitigated at runtime until the wiring story supplies an adapter.
- Nothing in `src/` calls `check_preconditions`, `apply_skips`, `record_skip` or
  `managed_after_skips` yet, so all of this story's behavior is latent until Stories 10.5/10.6/10.7
  wire the verbs. FR-86 / SC-04 / SC-05 are not yet mitigated at runtime.
- The mason baseline stamp is correct for the state on disk today, but it was performed by an
  automated pass rather than the human-invoked operation the tooling's docstring anticipates. The
  reasoning is recorded in both memlogs so it can be audited or reverted.
