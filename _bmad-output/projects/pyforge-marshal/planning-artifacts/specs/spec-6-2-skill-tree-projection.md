---
title: 'Skill-tree projection'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.1 merged'
---

<intent-contract>

## Intent

**Problem:** this repo's 89 skills live only under `.claude/skills/`; four of six packaged
`bmad-loop` adapter profiles (`codex`, `gemini`, `copilot`, `antigravity`) declare
`skill_tree = ".agents/skills"`, a directory that does not exist -- running the loop on any
of those adapters finds nothing (FR-41's motivating evidence). `cli/adapters.py` does not
exist yet; this story creates it as a new top-level `marshal adapters` command group with
its first verb, `sync` (PRD UJ-5: `marshal adapters sync` projects the skills into the tree
an adapter expects), matching the Consistency Conventions table's already-declared
`adapters <sub>: sync|probe|conform|matrix|check` shape (the other four verbs are later
Epic-6 stories' own scope).

**Approach:** a new, pure `core/skill_projection.py` declares the canonical source tree
(`.claude/skills`, a plain constant -- AD-12's "declared not inferred") and the ONE
`(platform -> mechanism)` table AD-36 requires (`{"posix": "symlink"}`; today's only
supported platforms, linux-64/osx-arm64 per NFR-13, are both POSIX, so the table has one
row, but it is a real, addressable table a future Windows row extends without any caller
changing). A pure `plan_projection` function takes every configured adapter's declared
skill tree (`HarnessPort.adapter_skill_trees`, a new seam method mirroring
`adapter_binary`/`adapter_seed_files` exactly, sourced from `bmad_loop.adapters.profile.
load_profiles` -- every packaged-plus-project-local profile the harness can resolve for
this project, not merely the one loop home's own active adapter, per FR-41's "every tree
my configured adapters read from") plus the platform name and a `previously_projected`
set (read from a new derived-artifact manifest, `.bmad-loop/skill-projection.json`,
gitignored exactly like `.bmad-loop/policy.toml` under AD-12/AD-35's identical precedent)
and returns which distinct trees need projecting and which previously-projected trees are
now stale. `cli/adapters.py::run_adapters_sync` is the I/O boundary: for each desired tree
that differs from canonical, it repoints (or creates) ONE whole-directory symlink at
`<home>/<tree>` targeting `<home>/.claude/skills` via the EXISTING
`FsPort.repoint_symlink_atomic` (no new write mechanism) -- the cheapest possible
mechanism (FR-41), and the one that makes "re-projection after a source change converges"
true for free: a directory symlink cannot itself go stale in CONTENT, only in TARGET (the
exact property AD-36's own Story-6.3 follow-on exploits for its "link-target identity"
drift check). Stale PROJECTED TREES (a tree the manifest records as projected but no
adapter currently declares) are removed via a new `FsPort.remove_symlink` primitive,
added alongside `repoint_symlink_atomic` in `adapters/fs_local.py` -- but only after
verifying, at delete time, that the on-disk symlink still resolves to canonical (never
blind-deleting off manifest content alone, mirroring `repoint_symlink_atomic`'s own
"refuse to clobber a real file/dir" discipline). The mechanism used is reported per tree
in the envelope's `data.projections` (AD-36).

## Boundaries & Constraints

**Always:**
- **The canonical source tree is one declared constant, `.claude/skills`, project-relative
  (AD-12)** -- never inferred from any adapter's own profile (even though the `claude` and
  `opencode-http` profiles happen to declare the same value today); projected trees are
  derived and NEVER edited in place -- every projected tree is exactly one directory
  symlink, never a populated copy a caller could accidentally hand-edit.
- **The `(platform -> mechanism)` table lives in exactly one place, `core/skill_projection.
  py::PROJECTION_MECHANISM_BY_PLATFORM`, with one pure lookup function,
  `mechanism_for_platform`** -- no other module under `cli/`, `core/`, `supervisor/`, or
  `ports/` compares `os.name`/`sys.platform` directly (AD-36), enforced by a new
  AST-scanning meta-test mirroring `tests/meta/test_ad19_no_adapter_branch.py`'s exact
  technique, proven non-vacuous via a synthetic violation. `adapters/` is excluded from the
  scan, mirroring AD-19's own carve-out (this repo already declares
  `adapters/process_posix.py`/`adapters/observer_mux.py` the legitimate POSIX-only seam;
  this story does not relitigate that).
- **"Configured adapters" means every profile `bmad_loop.adapters.profile.load_profiles
  (home)` resolves for the project** -- packaged (six today) plus any project-local
  `.bmad-loop/profiles/*.toml` overlay/addition -- never only the one loop home's own
  active `[adapter].name`. This is the plural reading FR-41's own text and this story's AC
  both use ("configured adapter**s**", "every tree **my** configured adapter**s** read
  from"), and it is what makes the motivating evidence ("four of six... find nothing")
  actually reachable by one `marshal adapters sync` call.
- **One symlink per DISTINCT tree value, never one per adapter** -- four packaged profiles
  share `.agents/skills`; a single repoint there satisfies all four (the cheapest-mechanism
  requirement, FR-41), reported once with every adapter that maps to it named in
  `data.projections[i].adapters`.
- **Re-projection converges and is a no-op when nothing changed (AD-21).** A tree whose
  on-disk symlink target already equals the canonical-relative path is reported
  `"unchanged"` and neither `repoint_symlink_atomic` nor the manifest file is rewritten for
  that tree; the manifest file itself is only rewritten when its computed content actually
  differs from what was read.
- **A stale projected tree is removed only after a live, on-disk verification that it is
  still a Marshal-owned symlink resolving to canonical** -- a manifest entry alone is
  evidence of past intent, never sufficient authority to delete; a mismatch (real
  file/directory, or a symlink repointed elsewhere by hand) is reported as a conflict
  finding and left untouched, never destroyed.
- **A run against an unsupported platform (no table row) takes zero filesystem action** --
  every desired tree that would have needed projection is named in one `UNEVALUABLE`
  finding; stale-entry removal is ALSO skipped that run (conservative: this story does not
  attempt to reason about whether a POSIX-created symlink is safely removable from an
  unsupported-platform process).
- **The manifest (`.bmad-loop/skill-projection.json`) is a derived, gitignored artifact**
  (AD-12/AD-35 precedent) -- a new `.gitignore` entry plus a new meta-test mirroring
  `tests/meta/test_rendered_policy_untracked.py` (untracked + literal `.gitignore` line +
  `git check-ignore` behavioral check) pin both halves.

**Never:**
- No per-skill symlinks or file copies -- the projected tree is exactly one
  directory-level symlink; enumerating and re-linking each of the 89 skills individually
  would be the OPPOSITE of "the cheapest mechanism" FR-41 requires, and would reintroduce
  exactly the per-entry drift AD-36's link-target-identity check exists to avoid needing to
  check.
- No new tiering/dispatch keyed on adapter NAME anywhere outside `adapters/
  harness_bmadloop.py` -- `plan_projection`'s input is already-resolved `{adapter_name:
  skill_tree}` data; it groups by TREE VALUE, never branches on which adapter produced it
  (AD-19, already-enforced by the existing meta-test, unaffected by this story).
- No drift/content-diff detection of what's INSIDE a projected tree -- that is FR-42's
  entirely separate concern (Story 6.3, explicitly deferred: "Epics S-6.2 must drop
  `not-applicable` with it" is 6.3's own text, not this story's).
- No automatic invocation from `marshal init`/`marshal factory spin` -- this story ships
  the standalone `marshal adapters sync <slug>` verb only; wiring it into another verb's
  own flow is a later story's scope (not named by this story's AC).
- Do not touch `core/policy.py` -- no new policy field is added; the adapter set comes
  entirely from the harness's own profile registry (see Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Configured adapters whose skill trees differ from canonical, none projected yet | First `sync` | Each distinct non-canonical tree gets a new directory symlink to canonical; `data.projections[*].action == "created"` | No finding |
| Configured adapters whose skill trees equal canonical (`claude`, `opencode-http`) | Already-satisfied | No filesystem action for those adapters; they never appear in `data.projections` (nothing to project) | No finding |
| `sync` run again with nothing changed since the last run | Converged state | Every desired tree's on-disk symlink target already matches; `action == "unchanged"` for all; manifest file is not rewritten | No finding |
| A profile's declared skill tree changes between runs (e.g. project-local overlay edits it) | Source change | The old tree's manifest entry moves to `to_remove` (verified live, then removed) and the new tree is created; convergence, no leftover stale entry | No finding |
| A previously-projected tree's path now holds a real file/directory instead of a symlink (hand-created) | Structural conflict, create path | Projection for that tree is refused; existing content is left untouched | Registered finding (WARN) |
| A previously-projected tree's symlink now points somewhere OTHER than canonical (hand-repointed) | Structural conflict, remove path | Stale-removal is refused; existing symlink is left untouched, still listed in the manifest so it is re-flagged next run | Registered finding (WARN) |
| The canonical source tree (`<home>/.claude/skills`) does not exist | Missing precondition | No tree is created this run; stale-entry removal still proceeds (safe cleanup does not require canonical to exist) | Registered finding (ERROR) |
| `HarnessPort.adapter_skill_trees` fails (unimportable `bmad_loop`, unreadable profile overlay) | Cannot enumerate configured adapters | No filesystem action at all this run | Registered finding (UNEVALUABLE) |
| The resolved platform has no table row (not POSIX) | Unsupported platform | Zero filesystem action (create AND remove both skipped); every desired tree named | Registered finding (UNEVALUABLE) |
| The manifest file is malformed JSON | Corrupt bookkeeping | Treated as "nothing previously projected" (`previously_projected = {}`); sync still proceeds and overwrites the manifest with fresh, valid content | Registered finding (WARN) |
| A `repoint_symlink_atomic`/`remove_symlink` call fails for one specific tree (permissions, etc.) | Per-tree I/O failure | That tree's action reports `"failed"`; every OTHER tree's projection/removal still proceeds (isolated per tree, never abort-all) | Registered finding (ERROR) |
| The manifest write itself fails after all filesystem projection succeeded | Bookkeeping-only failure | The live symlinks are already correct; only the NEXT run's manifest-diff bookkeeping degrades (re-derives `previously_projected` from an empty/stale manifest, at worst redoing already-idempotent work) | Registered finding (WARN), never blocks |
| An unresolvable/malformed project slug | Precondition | No filesystem/harness touch at all | Registered finding (ERROR), mirrors `MRS-SPIN-001`/`MRS-INIT-001` |
| The named loop home is not provisioned | Precondition | No filesystem/harness touch at all | Registered finding (ERROR), mirrors `MRS-SPIN-002` |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/skill_projection.py` -- NEW, pure (AD-4: no `os`/`subprocess`/
  `time`/adapters import). `CANONICAL_SKILL_TREE_REL = ".claude/skills"`,
  `PROJECTION_MECHANISM_BY_PLATFORM: Mapping[str, str] = {"posix": "symlink"}`,
  `mechanism_for_platform(platform_name: str) -> str | None`, `TreeProjectionAction`
  (frozen dataclass: `tree`, `adapters: tuple[str, ...]`), `ProjectionPlan` (frozen
  dataclass: `canonical`, `platform_mechanism: str | None`, `to_project: tuple[
  TreeProjectionAction, ...]`, `to_remove: tuple[str, ...]`, `unsupported_trees: tuple[
  str, ...]`), `plan_projection(skill_trees_by_adapter, *, canonical=..., 
  previously_projected=frozenset(), platform_name) -> ProjectionPlan`.
- `src/pyforge/marshal/ports/harness.py` -- EDIT. New `HarnessPort.adapter_skill_trees
  (self, project: Path) -> Mapping[str, str]` (adapter name -> declared `skill_tree`,
  project-relative), mirroring `adapter_binary`'s docstring/contract shape (raises
  `HarnessError` for an unimportable `bmad_loop` or an unreadable profile overlay; never
  for an individual unknown adapter name, since there is none here -- it returns every
  NAME the registry itself resolves).
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT. `adapter_skill_trees`
  implementation via `bmad_loop.adapters.profile.load_profiles(project)`, wrapping the
  SAME `(OSError, UnicodeDecodeError, ValueError, TypeError, AttributeError)` guard
  `_get_profile` already uses (review-discovered convention, reused verbatim -- see that
  method's own comments).
- `src/pyforge/marshal/ports/fs.py` / `src/pyforge/marshal/adapters/fs_local.py` -- EDIT.
  New `FsPort.remove_symlink(path: Path) -> bool` / `LocalFs.remove_symlink`: `True` if a
  symlink at `path` was removed, `False` if nothing existed there (safe no-op); raises
  `FsError` if `path` exists and is NOT a symlink (refuse to destroy real content, mirrors
  `repoint_symlink_atomic`'s identical refusal) or on an `OSError` unlink failure.
- `src/pyforge/marshal/cli/adapters.py` -- NEW. `add_adapters_subparser` (new top-level
  `adapters` command, nested `sync` action -- mirrors `cli/spin.py::add_factory_subparser`'s
  nested-action shape; `probe`/`conform`/`matrix`/`check` are later stories' own additions
  to the SAME nested parser). `run_adapters_sync(args, *, fs=None, harness=None,
  context=None)`: slug validation -> `_home_path` resolution (imported from `cli/init.py`,
  no new helper) -> canonical-dir presence check -> `harness.adapter_skill_trees(home)` ->
  manifest read/parse -> `core.skill_projection.plan_projection` -> per-tree
  create/update/unchanged/conflict/removal execution against `FsPort` -> manifest
  write-if-changed -> envelope build/print/exit, mirroring `cli/check.py`'s overall shape
  (isolated-per-item execution, `_render_text_*`/`_emit` split).
- `src/pyforge/marshal/cli/main.py` -- EDIT. Wire `adapters_cli.add_adapters_subparser
  (subparsers)` alongside the other top-level siblings; update the module docstring's
  running command list.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register `MRS-ADP-001`..`MRS-ADP-010`
  (slug shape, home resolution, canonical-tree missing, adapter-enumeration failure,
  unsupported platform, per-tree write failure, structural conflict, per-tree removal
  failure, malformed manifest, manifest write failure).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Classify the ten new codes (see Design
  Notes for the tier rationale per code).
- `.gitignore` -- EDIT. New `.bmad-loop/skill-projection.json` line, grouped with the
  existing `.bmad-loop/policy.toml` derived-artifact entry and comment.
- `tests/meta/test_ad36_projection_mechanism_table.py` -- NEW. AST-scanning meta-test
  mirroring `test_ad19_no_adapter_branch.py`'s technique: no `cli`/`core`(excluding
  `skill_projection.py` itself)/`supervisor`/`ports` module compares `os.name`/
  `sys.platform` directly; non-vacuous via a synthetic violation.
- `tests/meta/test_skill_projection_manifest_untracked.py` -- NEW. Mirrors
  `test_rendered_policy_untracked.py`'s three-part shape for
  `.bmad-loop/skill-projection.json`.
- `tests/unit/test_skill_projection.py` -- NEW. Full `plan_projection`/
  `mechanism_for_platform` matrix (pure).
- `tests/unit/test_adapters_cli.py` -- NEW. `run_adapters_sync` against fake `FsPort`/
  `HarnessPort` doubles: first-sync, no-op re-sync, source change, conflict (create and
  remove paths), missing canonical, adapter-enumeration failure, unsupported platform,
  malformed manifest, per-tree write failure isolation, manifest-write failure.
- `tests/unit/test_harness_bmadloop_preflight.py` -- EDIT (spec originally named
  `test_harness_bmadloop.py`; that file does not exist -- this is the real one already
  covering `adapter_binary`/`adapter_seed_files`/`adapter_first_run_note`). `adapter_skill_trees`
  matrix (real packaged profiles + a project-local overlay fixture + the
  unimportable/unreadable failure paths).
- `tests/unit/test_fs_local.py` -- EDIT. `remove_symlink` matrix (removes a real symlink,
  no-ops on absence, refuses on a real file/dir, surfaces an `OSError` as `FsError`).
- `tests/unit/test_findings.py` -- EDIT. The existing literal `REGISTERED_CODES` snapshot
  test gains the ten new `MRS-ADP-*` codes.
- `tests/unit/test_cli.py` -- EDIT. `test_help_lists_gate_subcommand`'s literal subcommand-
  list token gains `,adapters` (the new top-level sibling).

## Design Notes

- **Why the mechanism table has exactly one row today, and why that is still a real
  table.** NFR-13 scopes installation to linux-64/osx-arm64 (both POSIX); Windows is
  explicitly deferred (architecture.md §"Windows-native operation", "maturity, not
  availability"). `PROJECTION_MECHANISM_BY_PLATFORM` therefore ships `{"posix":
  "symlink"}` alone -- but it is declared DATA, addressed through one pure lookup
  function, so a future Windows row (a junction, or a copy-based fallback) is a one-line
  addition to the dict, never a new `if`/`elif` anywhere a caller lives. This is the
  literal shape AD-36 asks for ("declared in one table with one owner; no module branches
  on platform outside it"), proven by the new AST-scanning meta-test rather than by
  inspection.
- **Why "configured adapters" resolves to `load_profiles`'s full registry, not the one
  active loop-home adapter.** Story 6.1's `[adapter].name` in rendered `policy.toml` is
  "which ONE agent THIS home launches" -- a real, narrower notion, already fully solved.
  This story's own AC text is explicitly plural ("configured adapter**s**", "every tree
  **my** configured adapter**s** read from") and FR-41's motivating evidence counts across
  ALL SIX packaged profiles, not one. `bmad_loop.adapters.profile.load_profiles(project)`
  is the existing, already-shipped enumeration this repo's own `bmad-loop` dependency
  provides for exactly this purpose -- reusing it needs no new policy field and no
  adapter-name branching (the SAME lazy-import seam `_get_profile` already uses). This is
  a genuine interpretive call the AC text does not fully pin down mechanically; it is
  recorded here as the resolved reading rather than left implicit.
- **Why a whole-directory symlink, never per-skill links or a copy.** FR-41 explicitly
  asks for "the cheapest mechanism the adapter and platform support" and AD-36 exists
  BECAUSE a symlink projection cannot drift in content -- only in target. One symlink per
  distinct tree value delivers both properties for free: content changes under
  `.claude/skills/` are visible through every projected tree with zero additional writes
  ("re-projection after a source change converges" is true by construction, not by a
  detection-and-repair loop), and Story 6.3's own link-target-identity drift check (AD-36)
  has exactly one thing to verify per tree.
- **Why a manifest exists at all, given the symlink mechanism is self-converging for
  CONTENT.** The one thing a directory symlink cannot self-converge is its own EXISTENCE
  when it should no longer exist -- if a project-local profile that once needed
  `.other/skills` is removed, nothing about `.claude/skills/`'s own content changes to
  signal that `.other/skills` is now stale. `.bmad-loop/skill-projection.json` (a derived,
  gitignored artifact under the SAME AD-12/AD-35 umbrella `.bmad-loop/policy.toml` already
  established) is the minimum state needed to detect that case, and only that case --
  every other AC ("converges", "no-op when unchanged") is satisfiable by the symlink
  mechanism alone and does not touch the manifest's read path at all.
- **Why removal re-verifies live state rather than trusting the manifest.** The manifest
  records Marshal's own past INTENT, not a guarantee about current reality -- an operator
  or another tool could have replaced a projected symlink with real content, or repointed
  it, between runs. Treating the manifest as sufficient authority to delete would let a
  stale bookkeeping entry destroy content Marshal never actually owns at delete time; the
  live on-disk check is the same "verify before you destroy" discipline
  `repoint_symlink_atomic` already applies to `create`/`update`, extended to `remove`.
- **Finding-code tiers.** `MRS-ADP-001`/`002` (slug shape / home resolution) are ERROR,
  mirroring `MRS-SPIN-001`/`002` exactly -- a real precondition, never attempted.
  `MRS-ADP-003` (canonical tree missing) is ERROR: a real operation this run needed was
  blocked. `MRS-ADP-004` (adapter enumeration failed) and `MRS-ADP-005` (unsupported
  platform) are UNEVALUABLE, mirroring `MRS-SPIN-014`'s "Marshal cannot determine" tier --
  neither is a confirmed failure of an attempted write. `MRS-ADP-006`/`008` (a specific
  tree's create/remove I/O failed) are ERROR: a real, attempted operation failed.
  `MRS-ADP-007` (structural conflict, create or remove path) is WARN: a SAFE refusal, not
  a failure -- mirrors `remove_empty_dir`'s own "declined, not raised" shape for a
  structurally analogous case. `MRS-ADP-009`/`010` (malformed manifest / manifest write
  failure) are WARN, mirroring `MRS-SPIN-015`'s "degrades, never blocks an otherwise-viable
  operation" precedent -- the manifest is bookkeeping for staleness detection, never the
  authority for whether a symlink is correct right now.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **2823 passed** (2712
  pre-Story-6.2 baseline + 111 new/updated: `core/skill_projection.py`'s own 15,
  `cli/adapters.py`'s 15, `adapter_skill_trees`'s 4, `remove_symlink`'s 4, plus the two
  new meta tests' 15 -- see the run's own collected total for the exact split).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 2 failed, both the pre-existing
  accepted `pyforge-steward` baseline (`_http` module-alias gap, `age` conda-only run-dep),
  unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- AD-3, AD-4, AD-9 all KEPT (86 files, 475 dependencies analyzed).

## Review Triage Log

### 2026-08-07 -- Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 2, medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter) **Dangling stale symlinks were silently untracked, never removed.** The stale-removal loop decided "already absent" via `fs.exists(tree_path)`, which FOLLOWS a symlink and reports `False` for a dangling one even though the link itself is present (`is_symlink()` is `True`). Trigger: the canonical `.claude/skills` tree is deleted/renamed while a previously-projected tree is now also stale (no adapter declares it any more) -- the code popped the tree from the manifest and never called `remove_symlink`, leaving a permanently orphaned broken symlink no future run would ever revisit (it was no longer tracked). Fixed: the loop now distinguishes "genuinely nothing at this path" (`read_symlink_target` returns `None`, lstat-based, never follows) from "a live symlink that resolves elsewhere" from "a dangling symlink" (`fs.exists` is `False` but a symlink IS present) -- only the middle case is left untouched (`conflict-kept`); both the canonical-resolving and the dangling cases are now actually removed, since a dangling link cannot be pointing at real content worth preserving. New tests: `test_dangling_stale_symlink_is_removed_not_silently_untracked` (plus a new `FakeFs(dangling=...)` opt-in knob so the fake can express the real-filesystem "link present, target absent" distinction it previously could not).
  - `high` `patch` (Blind Hunter) **Adapter-declared `skill_tree` values were never confined to the loop home.** `home / Path(rel)` for an ABSOLUTE `rel` discards `home` entirely (`Path.__truediv__`'s own documented semantics) -- a project-local `.bmad-loop/profiles/*.toml` overlay (explicitly in scope per `HarnessPort.adapter_skill_trees`'s own contract, untrusted relative to the six packaged profiles) declaring an absolute or `..`-escaping `skill_tree` could make `sync` create/repoint a symlink anywhere the process can write, with none of `MRS-ADP-001`'s slug-shape scrutiny applied to it. Fixed: every declared tree is now confined to the loop home once, immediately after `adapter_skill_trees` returns and before anything reaches `plan_projection` -- an absolute value, or one that resolves outside `home`, is skipped (never aborts the whole run) and named in a new registered finding, `MRS-ADP-011` (WARN, same "skip this one tree" tier as 005/007). New tests: `test_absolute_skill_tree_is_refused_never_projected_outside_home`, `test_escaping_relative_skill_tree_is_refused_never_projected_outside_home`.
  - `medium` `patch` (Edge Case Hunter) A corrupted/malformed `skill-projection.json` manifest degraded to `{"projected": {}}` with no visible consequence named -- if a genuinely stale symlink existed on disk from before the corruption, it would never re-enter `previously_projected`, so `plan.to_remove` never even considers it: an unrecoverable, invisible leak distinct from the dangling-symlink bug above (this one has no live symlink-vs-manifest mismatch to detect at all, since the manifest lost the record entirely). Not fully fixable without inventing a second, riskier "trust the filesystem over the manifest" recovery mechanism -- instead hardened the existing `MRS-ADP-009` finding message to say so explicitly: any stale-tree cleanup this run is skipped and will not self-heal without manual inspection, rather than the previous vaguer "treated as nothing previously projected."

**Follow-up review recommendation: false** -- all three findings are isolated to the manifest/symlink read-decide boundary, the first two each covered by a dedicated new test proving the fix; the third is a documentation/visibility hardening of an already-acknowledged degrade path, not a new design question.

</intent-contract>
