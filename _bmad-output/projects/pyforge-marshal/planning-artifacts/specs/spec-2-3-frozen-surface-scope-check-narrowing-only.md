---
title: 'Frozen-surface scope check, narrowing only'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'fbccf6ee0dbeb9a8701fc53ae2350d801808d44d'
---

<intent-contract>

## Intent

**Problem:** nothing today stops a producer story from silently amending a contract another story froze, or from widening the allowlist it is judged against. `frozen_surfaces` exists as a policy seed key, but no code reads it against real changed files; `AD-27`'s `policy_surface ∩ spec_surface` combinator has no `policy_surface` to intersect against at all — the 14-key policy vocabulary has no per-epic writable-surface declaration; and `--scope-check` is a documented-but-unimplemented flag on `marshal gate evaluate` (`cli/gate.py`'s own module docstring names it as "not implemented here").

**Approach:** (1) add a 15th, STATIC policy key `epic_surfaces: Mapping[str, tuple[str, ...]]` (per-epic path-glob allowlist, keyed by epic number as a string) — the operator's architectural decision, since AD-27's own text names the policy surface as "for its epic"; (2) a minimal, dependency-free parser reading a new `surface:` frontmatter field from a story's tracked spec file (`planning-artifacts/specs/spec-<key>.md`) — a flow-sequence of glob strings, no new YAML dependency; (3) a new `VcsPort.changed_files` primitive returning every path a story's worktree touched (committed diff vs base, plus uncommitted/untracked); (4) `core/gate.py::check_scope` — the pure `policy_surface ∩ spec_surface` combinator plus frozen-surface violation detection, both fed by real inputs; (5) `--scope-check` wired into `marshal gate evaluate`.

## Boundaries & Constraints

**Always:**
- `epic_surfaces` is a **STATIC** key (`_STATIC_KEYS`, not `_SEED_KEYS`) — it is project/policy-declared and never narrowed at runtime by a journal entry, unlike `frozen_surfaces`. Shape: `Mapping[str, tuple[str, ...]]`, keyed by epic number as a string (`"2"`, `"3"`) to match this project's own epic-numbering convention (`AD-23`'s `<epic>.<seq>` story-key format uses the same numeric epic identity). Validator mirrors `_valid_model_tier_map`'s existing shape-checking pattern (reject non-mapping, reject non-string keys, reject non-tuple-of-string values) — reuse the pattern, do not invent a second one. `DEFAULT_POLICY["epic_surfaces"] = {}`.
- The story-spec `surface:` field is parsed with a **minimal, dependency-free** frontmatter reader — no `pyyaml` (absent from this package's dependencies today; adding it for one list field is disproportionate). Support exactly the flow-sequence form on one line: `surface: ["glob1", "glob2"]`, parsed via `ast.literal_eval` on the bracketed portion after the `surface:` key (stdlib only, safe against arbitrary code execution since `literal_eval` only accepts Python literals). A missing `surface:` key returns `None` (not an empty tuple) — "no declared surface" and "declared empty surface" are different facts and must not collapse.
- `core/gate.py::compute_effective_surface(policy_surface: tuple[str, ...], spec_surface: tuple[str, ...] | None) -> tuple[str, ...]` is **pure**, no I/O. When `spec_surface` is `None` (no story spec, or no `surface:` field), the effective surface is `policy_surface` unchanged (AD-27's narrowing rule has nothing to narrow against). When `spec_surface` is present, the effective surface is **the intersection of the glob-matched path sets**, never a union, never `spec_surface` alone — a meta-test (mirroring AD-27's own text: "a meta-test asserts no other combinator is used") asserts the implementation is literally `set(a) & set(b)` over resolved paths, not any other combinator.
- `core/gate.py::check_scope(effective_surface, frozen_paths, changed_files) -> tuple[Finding, ...]` is pure. Two independent finding classes, both possible in one call: (a) a changed path not matched by any glob in `effective_surface` — one `Finding` per offending path, naming the path; (b) a changed path matched by any glob in `frozen_paths` — one `Finding` per offending path, naming **both the path and the story key that froze it** (per epics.md's own AC: "a change to a frozen file is a hard failure naming the file and the story that froze it") — this requires `frozen_paths` to carry provenance, not a bare path tuple; see the next bullet.
- The **frozen set is produced by the journal fold**, with policy's `frozen_surfaces` supplying only the **initial** seed (AD-26). Since `core/journal.py::FoldResult` has no frozen-surfaces accessor yet (Story 3.1's own "pure mechanism, zero real caller" precedent — no kind-specific accessor exists there today), add one: a new `observation` journal kind `"freeze-declared"` (payload: `path`, `story_key` — the declaring story, per AD-27's "a story may declare a freeze, because a freeze is a narrowing") and `"freeze-removed"` (payload: `path` — policy-or-operator-only per AD-27's asymmetry table, enforced at the call site that would emit it, not inside the pure fold). `FoldResult.live_frozen_surfaces(seed: tuple[str, ...]) -> tuple[FrozenPath, ...]` (new frozen dataclass `FrozenPath(path: str, story_key: str | None)` — `story_key` is `None` for a policy-seeded entry, the declaring story's key for a journal-declared one) folds `seed` plus every `"freeze-declared"` observation minus every `"freeze-removed"` observation, in journal order. **Reading the live set from `EffectivePolicy` directly (rather than through this fold) fails a meta-test** (epics.md's own AC, verbatim) — mirrors the existing `seed_view()` pattern's own "whitelisted accessor and nothing else" discipline from AD-26.
- `VcsPort.changed_files(repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]` — repo-relative POSIX paths, the **union** of (a) `git diff --name-only <base>...HEAD` (committed changes since the merge-base, three-dot per this repo's own `is_branch_merged` merge-base convention) and (b) `git status --porcelain` in `worktree_path` (uncommitted/untracked — a story's changes are not necessarily committed yet at gate-evaluation time). Read-only; raises `VcsCommandError` on any git failure, matching every other `VcsPort` method.
- `--scope-check` on `marshal gate evaluate`: when no `--run` is supplied (policy-seed-only scope, AD-26's F-3), the frozen set folds the seed alone (`FoldResult.live_frozen_surfaces` called with an empty synthetic fold, or the seed-only path already established by AD-26 F-3's own resolution for this exact command) — matches the existing `data["scope"] == "policy-seed-only"` convention verbatim, no new scope value invented. When `--run <id>` is supplied, real `core.journal.fold` now exists (Story 3.2 shipped) — swap the existing `MRS-GATE-005` stub branch for a real fold call, per `cli/gate.py`'s own docstring: "A future story swaps this stub branch for a real `core.journal.fold` call."

**Never:**
- No new YAML dependency (`pyyaml`, `ruamel.yaml`) for the `surface:` field parser.
- No union combinator anywhere in the effective-surface computation — intersection only (AD-27, and this story's own meta-test enforcing it).
- Freeze removal and gate-mode changes are never emitted by this story's own code from an agent-writable artifact — `"freeze-removed"` is a fold-side query capability only; no CLI action in this story writes one (that is a future story's concern, per AD-27's own asymmetry table: "freeze removal... policy, or an operator-attributed entry").
- Do not touch `core/spec_binding.py` — that module does not exist yet and is Story 2.7's own Surface, not this story's.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No spec-declared surface | `spec_surface is None` | Effective surface = policy surface, unchanged | No error |
| Spec surface narrower than policy surface | Both present, `spec_surface` globs a subset | Effective surface = intersection (narrower than either alone in path-count terms) | No error |
| Spec surface wider than policy surface | `spec_surface` declares a path outside `policy_surface` | That path is NOT admitted into the effective surface (never an expansion) — a hard finding if the story then changes a file there | No error, one `Finding` naming the path |
| Changed file matches a frozen path | `changed_files` includes a path in `live_frozen_surfaces` | Hard failure `Finding` naming the path AND the freezing story's key (or `None` for a policy-seeded freeze) | No error |
| Changed file outside effective surface, not frozen | Path matched by neither `effective_surface` nor `frozen_paths` | Hard failure `Finding` naming the path | No error |
| Live frozen set read attempt bypassing the fold | Code reads `EffectivePolicy.frozen_surfaces` directly where a live/run-scoped answer is needed | Meta-test failure (AD-26) | Build-time, not runtime |
| `--scope-check`, no `--run` | Policy-seed-only scope (AD-26/F-3) | Frozen set = seed only; `data["scope"] == "policy-seed-only"` unchanged | No error |
| `--scope-check --run <id>` | Real journal exists for the run | Frozen set = seed + journal-observed freeze-declared/removed, via `FoldResult.live_frozen_surfaces` | `MRS-GATE-005` retired for this path; journal-read failure degrades per `core.journal.fold`'s own existing quarantine/unevaluable semantics |
| `changed_files` on a clean worktree, no commits ahead | `base` == `HEAD` | Empty tuple | No error |
| `changed_files` git failure | No such `base` ref, corrupted repo | Raises `VcsCommandError` | Caller's responsibility, matches every other `VcsPort` method |
| A doc-only story (Story 2.4's own classification) | No source change at all | `changed_files` returns empty; scope check trivially passes (no changed path to violate anything) | No error — consistent with Story 2.4's own "doc-only" AC, not re-implemented here |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/policy.py` — EDIT. Add `epic_surfaces` to `_STATIC_KEYS`; `DEFAULT_POLICY["epic_surfaces"] = {}`; `_valid_epic_surfaces` validator (mirrors `_valid_model_tier_map`'s shape-checking); wire into `compose()`'s static-key block alongside `verify_commands`/`merge_subject_template`/`model_tier_map`.
- `src/pyforge/marshal/core/spec_surface.py` — NEW. `parse_declared_surface(text: str) -> tuple[str, ...] | None` — the minimal `ast.literal_eval`-based `surface:` frontmatter reader. Pure parsing over an already-read string (AD-4: `core/**` performs no I/O, no `pathlib` I/O methods — confirmed against AD-4's literal text, not assumed). `cli/gate.py` reads the spec file's bytes (the impure edge) and passes the text in.
- `src/pyforge/marshal/core/gate.py` — EDIT. `compute_effective_surface`, `check_scope`, both pure, both per the Boundaries section above.
- `src/pyforge/marshal/core/journal.py` — EDIT. New `FrozenPath` frozen dataclass; `FoldResult.live_frozen_surfaces(seed: tuple[str, ...]) -> tuple[FrozenPath, ...]`; register `"freeze-declared"`/`"freeze-removed"` as recognized observation kinds (check `Phase`/kind-registration conventions already established in this file before inventing a new registration mechanism).
- `src/pyforge/marshal/ports/vcs.py` — EDIT. `VcsPort.changed_files(repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]`.
- `src/pyforge/marshal/adapters/vcs_git.py` — EDIT. Implement `changed_files`: `git diff --name-only <base>...HEAD` union `git status --porcelain` parse, repo-relative POSIX paths, dedup.
- `src/pyforge/marshal/cli/gate.py` — EDIT. `--scope-check` flag on the `evaluate` action; wire `parse_declared_surface` (spec lookup by story key, if `--story` or equivalent is available on this command — check existing argv shape before assuming), `changed_files`, `compute_effective_surface`, `check_scope`; swap the `MRS-GATE-005` `--run` stub for a real `core.journal.fold` call now that Story 3.2 has shipped it.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New codes for: changed-path-outside-surface, changed-path-frozen (both hard/ERROR per epics.md's "hard finding"/"hard failure" wording).
- `src/shared/packages/pyforge-marshal/tests/unit/test_scope.py` — NEW (named explicitly in epics.md's own **Surface:** field for this story). `compute_effective_surface`/`check_scope` transition matrix, the intersection-only meta-test, the AD-26 direct-read-fails-a-meta-test guard.
- `tests/unit/test_spec_surface.py` — NEW. `parse_declared_surface` parsing matrix (present, absent, malformed).
- `tests/unit/test_vcs_git.py` — EDIT. `changed_files` against a real temp git repo.
- `tests/unit/test_gate.py`, `tests/unit/test_journal.py` — EDIT. Wiring + `live_frozen_surfaces` fold tests.

## Tasks & Acceptance

**Execution:**
- [x] `core/policy.py` — `epic_surfaces` static key, validator, `compose()` wiring.
- [x] `core/spec_surface.py` — `parse_declared_surface`.
- [x] `core/gate.py` — `compute_effective_surface`, `check_scope`.
- [x] `core/journal.py` — `FrozenPath`, `FoldResult.live_frozen_surfaces`, freeze-kind registration.
- [x] `ports/vcs.py` + `adapters/vcs_git.py` — `changed_files`.
- [x] `cli/gate.py` — `--scope-check` wiring; retire the `MRS-GATE-005` `--run` stub for a real fold call.
- [x] `core/findings.py` / `core/verdict.py` — register the new hard-finding codes (three, not two — see Spec Change Log #3).
- [x] Unit tests for every new/edited module, including the full I/O matrix above and the AD-27 intersection-only meta-test.
- [x] `deferred-work.md` — log any scope narrowed during implementation (none — no scope was narrowed; see Spec Change Log for the additions beyond the Code Map's literal text instead).

**Acceptance Criteria:**
*(Story 2.3's ACs from `epics.md`, preserved as the contract of record.)*
- Given a story spec declaring a surface, and a project policy declaring the epic's surface, when the scope check runs, then the effective surface is computed as `policy_surface ∩ spec_surface`, and a meta-test asserts no other combinator is used (AD-27)
- And a spec-declared path outside the policy surface is a hard finding — a machine-drafted spec can only narrow, never widen, the allowlist it is judged against
- And a change to a frozen file is a hard failure naming the file and the story that froze it
- And a change outside the effective surface is a failure naming every offending path
- And the frozen set is produced by the journal fold over freeze declarations, with policy supplying only the initial set — reading the live set from `EffectivePolicy` fails a meta-test (AD-26)
- And freeze declarations, freeze removals, and gate-mode changes are never sourced from an agent-writable artifact (AD-27)

## Design Notes

**Why `epic_surfaces` is a new STATIC policy key, not derived from convention.** AD-27's own text says "for its epic" — a per-epic allowlist, not a whole-project one. The alternative (deriving "policy surface" from the project's writable-path convention, no new key) was considered and explicitly rejected: it can't express per-epic narrowing at all, and AD-27's worked example ("Story 6.1 amended a schema and froze three files") only makes sense against a surface finer than "the whole project." This was confirmed as an operator decision before implementation began (this story's own genesis) rather than assumed silently.

**Why the frozen-set fold needs a new dataclass (`FrozenPath`) instead of a bare `tuple[str, ...]`.** epics.md's own AC requires naming "the story that froze it" in the failure — a bare path tuple cannot carry that provenance. Bare `frozen_surfaces` (the policy seed) has no natural story-key owner (it's project-declared, not story-declared), hence `story_key: str | None` on the dataclass rather than a required field.

**Why `changed_files` unions committed-diff and working-tree-dirty, not either alone.** A story spec's own file (this very file) sits in Tier-3 scratch and may not be committed at all when a gate runs mid-development; a committed-diff-only check would miss it entirely and let scope violations slip through the exact window (uncommitted, mid-story) that matters most for FR-22's own "cannot silently amend" guarantee.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold, especially AD-4 (`core/**` holds no `subprocess`/`os`/`time`/`adapters` import) given `core/spec_surface.py`'s file-reading question flagged in its own Code Map entry.

**Manual checks (if no CLI):**
- Seed a `marshal-policy.toml` with `frozen_surfaces` naming a real file and `epic_surfaces` naming this epic's own surface; run `marshal gate evaluate --scope-check` against a worktree with an uncommitted change to the frozen file; confirm a hard failure naming the file.

## Spec Change Log

**1. Code Map inaccuracy (`cli/gate.py`'s argv shape) — a `--story` flag was added, not merely wired.** The Code Map said "wire `parse_declared_surface` (spec lookup by story key, if `--story` or equivalent is available on this command — check existing argv shape before assuming)". Checked live: `evaluate` had no `--story` (or `--epic`) flag at all before this story — only `--project`/`--run`/`--format`. `--scope-check` needs a story key for two independent reasons (selecting `epic_surfaces[str(epic)]`, and locating the story's own tracked spec file), so a `--story KEY` flag was added, required in effect (checked in `run_evaluate`, not via argparse's own required-group machinery — matching this module's existing pattern of reporting a missing precondition as a registered `Finding` rather than a usage error).

**2. Code Map inaccuracy (no `--home` flag needed) — `_home_path` resolves the loop home from the slug alone.** The intent-contract's own Design Notes discuss `changed_files` needing a worktree path, but the Code Map never says how `cli/gate.py` obtains one. Investigated live: `cli/init.py::_home_path(slug)` (already imported by `cli/spin.py`) derives a project's loop home deterministically from its slug alone (`BMAD_LOOP_HOME_ROOT` env override, else `~/.bmad-loops/<slug>`) — no git lookup, no new CLI flag needed. `--scope-check` and `--run`'s own run-directory resolution (`cli/spin.py::_run_dir`) both reuse this existing helper instead of inventing a `--home PATH` flag the rest of this package's CLI surface has no precedent for.

**3. Three new finding codes were registered, not the two the Code Map's own Code Map-entry prose named.** `core/findings.py`'s Code Map bullet said "New codes for: changed-path-outside-surface, changed-path-frozen" — `MRS-GATE-007`/`MRS-GATE-008`, both landed as specified, both the table's first `Verdict.SCOPE_VIOLATION` classifications. A third, `MRS-GATE-009` (`Verdict.UNEVALUABLE`), was added for "`--scope-check` was requested but could not be evaluated at all" (no resolvable active project, no `--story`, an unresolvable story key, or a `VcsPort.changed_files` failure) — AD-8 ("unevaluable is failure") requires this be a registered, reported condition rather than a silent no-op or a usage error, and no existing code covers it. `MRS-GATE-005` itself was **reused, not replaced**: its registered meaning is broadened from "no run-journal fold exists yet" (Story 3.2 not shipped) to "the requested run-scoped fold could not be produced" (no resolvable loop home, no such run directory, or an unreadable journal) — the same caller-facing shape and the same `Verdict.UNEVALUABLE` classification, so no new code was needed for that path.

**4. Two files outside the Code Map's own list required edits: `cli/config.py` and `schemas/policy.json`.** Adding `epic_surfaces` as a 15th, STATIC policy key (per the Boundaries & Constraints' own explicit instruction) has two structural consequences the Code Map doesn't mention, both caught by the existing "derive, don't declare" tripwire test `tests/unit/test_cli.py::test_field_order_matches_the_closed_policy_vocabulary`: (a) `cli/config.py::_FIELD_ORDER` (the render order `marshal config` prints every key in) and `_UNSETTABLE_KEYS` (the fields `--set` cannot express — `epic_surfaces` is a 5th mapping-typed field alongside `verify_commands`/`worktree_seed_paths`/`model_tier_map`/`frozen_surfaces`) both needed the new key added; (b) `schemas/policy.json` (the materialized-artifact/wire-shape schema `additionalProperties: false`-gates) needed a new `epic_surfaces` property plus its own `required` entry. Neither module is `core/**` (AD-4 is unaffected) and neither is named in this story's Code Map, but both are load-bearing for `epic_surfaces` to actually surface through `marshal config`/`--materialize` the same way every other STATIC key already does — landing the policy-vocabulary change without them would have shipped a key `compose()` accepts but `marshal config`/the materialized artifact silently omit.

**5. `core/journal.py`'s "freeze-kind registration" is a pair of documented string constants, not a closed-vocabulary enum.** The Code Map says "register `"freeze-declared"`/`"freeze-removed"` as recognized observation kinds (check `Phase`/kind-registration conventions already established in this file before inventing a new registration mechanism)". Checked live: `JournalEntry.kind` is `Any non-blank str` — this module keeps no closed kind-registry/enum anywhere (the module's own docstring lists "9 illustrative kinds" as examples, never enforced). "Registration" here is therefore the same convention every other kind already gets: two documented module-level string constants (`KIND_FREEZE_DECLARED`, `KIND_FREEZE_REMOVED`), consumed by the new `FoldResult.live_frozen_surfaces` and available to a future writer — no enum/registry mechanism was invented, since none exists to extend.

</intent-contract>

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 10 (high 3, medium 5, low 2)
- defer: 4
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **`parse_declared_surface` silently WIDENED the effective surface for a multi-line YAML `surface:` block.** Only the one-line flow-sequence form (`surface: ["a", "b"]`) was recognized; a `surface:` key present with a multi-line YAML block value (`surface:` alone, then `- "glob"` lines) fell through to "no `surface:` key found" and returned `None` — indistinguishable from an absent declaration, which callers treat as "use the policy surface unnarrowed". A spec author who (reasonably) wrote multi-line YAML got silently widened back to the full policy surface instead of narrowed or rejected — the exact AD-27 violation this whole feature exists to prevent. Fixed: a new `SurfaceParseError` exception, raised when `surface:` is present with no inline value (or only a trailing comment), distinct from both "absent" (`None`) and "malformed inline value" (also `None`, unchanged). `cli/gate.py::_run_scope_check` now catches it and reports `MRS-GATE-009` (extending that code's existing "could not evaluate at all" meaning) instead of silently proceeding unnarrowed. New tests: `test_multiline_block_surface_raises_surface_parse_error_not_none` + 2 siblings in `test_spec_surface.py`, `test_gate_evaluate_scope_check_multiline_surface_block_reports_mrs_gate_009` in `test_cli.py`.
  - `[high]` `[patch]` **`changed_files`'s `git status --porcelain` call omitted `--untracked-files=all`, collapsing a wholly-new untracked directory into one bare `dir/` line.** Git's default `--untracked-files=normal` reports a new directory as a single porcelain entry rather than enumerating its files; `check_scope` then evaluated that directory-shaped path against file-shaped globs (e.g. `recipes/newthing/*.yaml`), which never match a directory — silently breaking both the allowlist check and frozen-path protection for every file inside a brand-new untracked directory. Fixed: added `--untracked-files=all` to the `git status --porcelain` invocation. New test: `test_changed_files_an_untracked_directory_reports_each_file_individually`.
  - `[high]` `[patch]` **Neither git invocation in `changed_files` disabled path quoting, so a non-ASCII path came back C-escaped and never matched its own glob.** `core.quotePath` defaults to `true`; a path like `café.txt` round-trips as `"caf\303\251.txt"` instead of the literal UTF-8 path, silently breaking scope/frozen-path checking for it. Fixed: added `-c core.quotePath=false` to both the `git diff` and `git status --porcelain` invocations. New test: `test_changed_files_a_non_ascii_path_round_trips_literally`.
  - `[medium]` `[patch]` **`git diff --name-only` ran with no rename detection, so a committed rename reported BOTH the stale old path and the new path as separate "changed" entries.** Only the `git status --porcelain` branch already stripped the old half of an uncommitted rename via its own `" -> "` handling; a committed rename had no equivalent. Fixed: switched to `git diff --name-status -M ...` (rename detection plus a status prefix that distinguishes a rename/copy pair from an ordinary add/modify/delete), keeping only the new path for an `R`/`C`-prefixed entry. New test: `test_changed_files_a_committed_rename_reports_only_the_new_path`.
  - `[medium]` `[patch]` **`_find_spec_text` caught only `OSError` around the spec file read, so a non-UTF-8 spec file crashed `marshal gate evaluate --scope-check` with a raw traceback** instead of degrading to "no spec text found" the way every other best-effort read in this module does. Fixed: broadened the except clause to `(OSError, UnicodeDecodeError)`. New test: `test_find_spec_text_degrades_to_none_on_a_non_utf8_spec_file`.
  - `[medium]` `[patch]` **`cli/gate.py`'s module docstring and `core/findings.py`'s `MRS-GATE-009` description both claimed an unresolvable `--story` value produces `MRS-GATE-009`, but the actual code path produces the existing `MRS-IDENT-001`** (confirmed by the diff's own `test_gate_evaluate_scope_check_unresolved_story_reports_mrs_ident_001`). Fixed both docstrings to describe the actual, test-pinned behavior rather than changing the behavior to match the prose.
  - `[medium]` `[patch]` **The AD-27 meta-test proving `compute_effective_surface` uses only set-intersection scanned only `BinOp` nodes (`|`/`-`), missing a rewrite using `.union(...)`/`.difference(...)` method calls,** which would achieve the same silent widening while sailing past the guard undetected. Fixed: the meta-test now also scans for `ast.Call` nodes invoking `union`/`difference`/`symmetric_difference`/`update`/`difference_update` anywhere in the function body, alongside the existing operator scan. New tests: strengthened `test_meta_compute_effective_surface_uses_only_set_intersection` + a new `test_meta_guard_method_scan_detects_a_synthetic_union_call` proving the new clause actually fires.
  - `[medium]` `[patch]` **`_valid_epic_surfaces` never checked that an `epic_surfaces` key is numeric,** so a typo'd key like `"epic-2"` composed successfully with no diagnostic and could never match any real epic (`str(story_key.epic)` is always plain digits) — a permanently dead, silently-inert allowlist entry. Fixed: added a `key.isdigit()` check, reporting the same `MRS-POLICY-002` code every other malformed `epic_surfaces` value already uses. New test: `test_epic_surfaces_rejects_non_numeric_epic_key`.
  - `[low]` `[patch]` **`test_gate_evaluate_scope_check_without_active_project_reports_mrs_gate_009` asserted only `exit_code == 1`,** unlike its sibling tests, so it would pass for any unrelated failure producing the same exit code. Fixed: added the same `MRS-GATE-009 in codes` assertion its siblings already make.
  - `[low]` `[patch]` **No test pinned "`epic_surfaces` left at its default `{}` plus `--scope-check`" — plausibly-correct-but-unproven deny-by-default behavior** (an unconfigured epic makes `compute_effective_surface` always empty, so every changed file is flagged `MRS-GATE-007`). Fixed: added `test_gate_evaluate_scope_check_unconfigured_epic_flags_every_changed_file` pinning the exact behavior, so a future accidental "skip the check when unconfigured" change is caught as a regression.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` **D1** -- `changed_files`'s base branch is hardcoded to `"main"` with no `--base`/override flag; a real portability limitation for any project whose landing branch isn't `main`, not blocking for this repo.
  - `[low]` **D2** -- `_find_spec_text`'s multi-match tie-break (lexicographically-first) has no relationship to recency or supersession; needs a real design decision (mtime? AD-23's ordered-suffix convention?) before fixing.
  - `[low]` **D3** -- `changed_files` runs its two git invocations non-atomically against the same worktree, with no snapshot/lock between them; low practical risk given this CLI's synchronous single-invocation usage model.
  - `[low]` **D4** -- `--story` supplied without `--scope-check` is silently accepted and has no effect, with no warning that the flag did nothing.

## Suggested Review Order

**Pure combinator core (AD-27)**

- Entry point: the intersection-only combinator (`policy_surface ∩ spec_surface`) — read this first to see AD-27's own rule made literal.
  [`gate.py:309`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py#L309)

- Frozen-path + outside-surface violation detection, both feeding the same `Finding` list.
  [`gate.py:341`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py#L341)

- The AD-27 meta-test itself, and P7's widened AST guard against `.union()`/`.difference()` method-call escape hatches.
  [`test_scope.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_scope.py#L1)

**Story-spec `surface:` parsing — the P1 fix**

- `parse_declared_surface` and the new `SurfaceParseError` — a multi-line YAML block now fails loud instead of silently widening the surface back to policy-only.
  [`spec_surface.py:57`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_surface.py#L57)

- `_find_spec_text`'s spec-file lookup, and the P5 `UnicodeDecodeError` fix.
  [`gate.py:433`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py#L433)

**Frozen-set journal fold (AD-26)**

- `FrozenPath` (carries the freezing story's key, not just a bare path) and `live_frozen_surfaces` — the ONLY legal read of the live frozen set.
  [`journal.py:514`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py#L514)

**New policy key: `epic_surfaces`**

- `_valid_epic_surfaces`, including the P8 numeric-epic-key guard.
  [`policy.py:417`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py#L417)

**Git primitive: `changed_files` — P2/P3/P4 fixes**

- Port contract.
  [`vcs.py:158`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py#L158)

- Implementation: `--untracked-files=all` (P2), `-c core.quotePath=false` (P3), rename-aware `--name-status -M` (P4).
  [`vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L1)

**CLI wiring**

- `--scope-check`/`--story` orchestration, the P1 `SurfaceParseError` catch, and the real `core.journal.fold` call retiring the old stub.
  [`gate.py:468`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py#L468)

- New/corrected finding codes, including the P6 `MRS-GATE-009` prose fix.
  [`findings.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py#L1)

**Tests (peripherals)**

- End-to-end `--scope-check` CLI tests, including P9/P10.
  [`test_cli.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_cli.py#L1)

- `changed_files` against a real temp git repo, including the P2/P3/P4 regression tests.
  [`test_vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py#L1)

- `epic_surfaces` validator tests.
  [`test_policy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_policy.py#L1)

- `live_frozen_surfaces` fold tests.
  [`test_journal.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_journal.py#L1)

- `parse_declared_surface` parsing matrix.
  [`test_spec_surface.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_spec_surface.py#L1)
