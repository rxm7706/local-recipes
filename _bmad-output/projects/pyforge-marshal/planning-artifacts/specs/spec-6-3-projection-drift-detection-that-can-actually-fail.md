---
title: 'Projection drift detection that can actually fail'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-2-skill-tree-projection.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.2 merged'
---

<intent-contract>

## Intent

**Problem:** Story 6.2's `marshal adapters sync` projects the canonical `.claude/skills` tree
into every OTHER tree a configured adapter declares via ONE directory symlink per distinct
tree (AD-36's `{"posix": "symlink"}` mechanism table). That mechanism's own module docstring
already names the property this story exploits: "a directory symlink cannot drift in CONTENT
(only in TARGET)." Nothing today VERIFIES that a projected tree's symlink still points where
it should -- an operator (or another tool) could repoint it, delete it, or replace it with real
content between `sync` runs, and nothing would notice until something downstream silently read
stale or missing skills. FR-42/AD-36 require a drift check that is MECHANISM-SPECIFIC and
GENUINELY FALSIFIABLE: for the symlink mechanism this project ships, that check is LINK-TARGET
IDENTITY (does the live symlink still resolve to canonical?), never a content diff (a directory
symlink has no content of its own to diff -- Story 6.2's own Boundaries & Constraints already
forbids per-skill link/copy tracking, and this story does not relitigate that).

**Approach:** a new, pure `core/conformance.py` (AD-4: no `os`/`subprocess`/`time`/adapters
import) declares a small, closed status vocabulary -- `"link-target-confirmed"` (the one
PASSING outcome, reachable only when a live symlink's target string genuinely equals the
canonical-relative path `sync` would compute) plus three DRIFT outcomes, `"added"` (desired by
a configured adapter, never yet projected), `"removed"` (was tracked/live and is no longer),
and `"modified"` (present but the identity check fails -- retargeted, or real content in the
way). This is the resolved reading of the AC's generic "added, removed and modified skills per
adapter tree" wording for a project whose ONLY declared mechanism operates at TREE granularity,
never per-skill (see Design Notes -- a genuine interpretive call, recorded rather than left
implicit). A `MECHANISM_CHECKERS` table (mirroring `skill_projection.
PROJECTION_MECHANISM_BY_PLATFORM`'s own declared-not-branched shape) maps `"symlink"` to the
one identity-checking function this story ships; a mechanism string with NO entry there --
including `None`, the "no declared mechanism for this platform" case -- NEVER reaches the
checker at all: every tree in scope for it is instead reported `unevaluated_trees`, and the
caller emits `Verdict.UNEVALUABLE` (never a fabricated pass, never `not-applicable`, which the
closed 6-member lattice has no member for -- AD-31). `cli/adapters.py` gains the I/O boundary:
a new `gather_conformance_findings(home, *, fs, harness)` helper (read-only -- no
`repoint_symlink_atomic`/`remove_symlink`/manifest-write call anywhere in it) that reuses
Story 6.2's own `plan_projection` to compute the CURRENT desired-tree set and reads each
in-scope tree's live symlink state, plus a new standalone `marshal adapters conform <slug>`
verb (the `conform` slot the Consistency Conventions table already reserved:
`adapters <sub>: sync|probe|conform|matrix|check`) that wraps it in the usual envelope. The SAME
helper is called from `cli/init.py::run_preflight` (a local, function-scoped import to avoid a
module-load-time circular dependency -- `cli/adapters.py` already imports `_home_path` FROM
`cli/init.py` at module level, mirroring `cli/deploy.py`'s own identical local-import
precedent for the same reason) as one more preflight step, satisfying "it runs as part of
preflight whenever a non-default adapter is configured" structurally: the helper's own output
is empty/no-finding whenever no configured adapter's declared tree differs from canonical (the
literal meaning of "no non-default adapter is configured" -- Story 6.2's own resolved reading
of "configured adapters" carries over unchanged, see Design Notes), so preflight always CALLS
the check but it only ever produces visible output when there is something to check.

## Boundaries & Constraints

**Always:**
- **The passing outcome (`"link-target-confirmed"`) is returned if and only if a live symlink's
  raw target string equals the canonical-relative target `sync` would compute for that tree.**
  Every other live state (absent, a real file/directory, a symlink pointing elsewhere) returns
  a drift outcome instead -- there is no code path that returns the passing outcome
  unconditionally (enforced by a new meta-test, see Code Map).
- **A mechanism string with no registered checker -- including `None` -- NEVER produces the
  passing outcome for any tree, ever, regardless of what the live filesystem state would
  otherwise show.** Every tree that would have been checked under that mechanism is instead
  named in `unevaluated_trees` and surfaces as a registered `Verdict.UNEVALUABLE` finding.
  This is the AC's own "never reports clean for a check that cannot fail" rule, made
  structural rather than a convention a future call site could quietly violate (enforced by
  the same new meta-test).
- **`not-applicable` is never emitted anywhere in this module or its callers** -- confirmed
  directly against `core/verdict.py`'s own closed `LATTICE_ORDER` (six members: `error`,
  `gate-failed`, `scope-violation`, `unevaluable`, `warn`, `clean`; no `not-applicable` member
  exists, verified by reading the module before writing this spec) and asserted literally by
  the new meta-test against `core/conformance.py`'s own closed status vocabulary.
- **The check is READ-ONLY.** `gather_conformance_findings` calls only `fs.is_dir`,
  `fs.exists`, `fs.read_symlink_target`, `fs.resolve_path`, `fs.read_text` (via the SAME
  `_read_manifest` helper `run_adapters_sync` already uses) -- never
  `repoint_symlink_atomic`, `remove_symlink`, `ensure_dir`, or `write_text_atomic`. Detecting
  drift never repairs it; `marshal adapters sync` remains the only mutating verb.
- **Drift detection reuses Story 6.2's own `plan_projection` to compute the CURRENT desired-
  tree set** (never a second, parallel notion of "configured adapters") -- the same plural
  reading ("every profile `bmad_loop.adapters.profile.load_profiles` resolves for the
  project") Story 6.2's Design Notes already resolved and recorded. This story does not
  relitigate that reading; it consumes `plan_projection`'s output unchanged.
- **`marshal preflight` calls the SAME `gather_conformance_findings` helper the standalone
  `adapters conform` verb calls** -- one implementation, two call sites, per this story's own
  "not a wholly separate command" instruction. `cli/init.py` never re-implements any part of
  the identity check itself.

**Never:**
- No per-skill content diff of what is INSIDE a projected tree -- Story 6.2's Boundaries &
  Constraints already forbid per-skill symlinks/copies; a content-diffing drift check would
  need exactly the mechanism this project deliberately does not ship. The symlink mechanism's
  own identity check operates at TREE granularity only.
- No new dispatch on `os.name`/`sys.platform` anywhere outside `core/skill_projection.py`
  (AD-36, already enforced by Story 6.2's own `tests/meta/test_ad36_projection_mechanism_table.py`,
  unaffected by this story -- `core/conformance.py` never reads platform directly; it receives
  `plan.platform_mechanism`, already resolved, from its caller).
- No mutation of any kind from either call site (`adapters conform` or `preflight`) -- a
  drift finding is reported, never auto-repaired; the operator's own next step is
  `marshal adapters sync`, named in every drift finding's own message.
- No new registered code invents a softer tier than the codebase's own established
  precedent for "a real, attempted check found a real problem" (`Verdict.ERROR`, matching
  `MRS-ADP-003/006/008` and `MRS-CHECK-002/003`'s identical reasoning) -- drift is a real,
  determinate fact about the live filesystem, not an internal Marshal operation failure and
  not a softer "reported, never blocks" paper-trail gap.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A projected tree's live symlink target still equals canonical | Converged | `status == "link-target-confirmed"` for that tree; no finding | No finding |
| A configured (non-default) adapter's declared tree has never been synced | Never projected | `status == "added"`; the tree names a real, unsynced gap | Registered finding (`MRS-CONFORM-001`, ERROR) |
| A previously-projected tree's manifest entry exists but nothing is at its path any more | Deleted out-of-band | `status == "removed"` | Registered finding (`MRS-CONFORM-001`, ERROR) |
| A tree the manifest tracked, still live and still resolving to canonical, but no adapter declares it any more | Stale, not yet cleaned up | `status == "removed"` (converges via `marshal adapters sync`, never this check) | Registered finding (`MRS-CONFORM-001`, ERROR) |
| A projected tree's symlink has been hand-repointed elsewhere | Retargeted | `status == "modified"` | Registered finding (`MRS-CONFORM-001`, ERROR) |
| A projected tree's path now holds a real file/directory instead of a symlink | Structural conflict | `status == "modified"` | Registered finding (`MRS-CONFORM-001`, ERROR) |
| The resolved platform has no declared mechanism-table row (`plan.platform_mechanism is None`) | Unsupported platform | Zero trees checked; every desired tree named in `unevaluated_trees`; no passing outcome anywhere | Registered finding (`MRS-ADP-005` reused, UNEVALUABLE) |
| A mechanism string IS declared in `skill_projection`'s own table but has no registered checker in THIS module (defensive: a future platform row added there before a checker exists here) | Unimplemented mechanism | Same as above -- `unevaluated_trees`, never a fabricated pass | Registered finding (`MRS-ADP-005` reused, UNEVALUABLE) |
| No configured adapter's declared tree differs from canonical | Nothing to check | `checks == []`, `unevaluated_trees == []`; no finding at all | No finding |
| `HarnessPort.adapter_skill_trees` fails | Cannot enumerate configured adapters | No check performed at all this run (mirrors `sync`'s identical early return) | Registered finding (`MRS-ADP-004` reused, UNEVALUABLE) |
| The canonical `.claude/skills` tree does not exist | Missing precondition | The identity check still proceeds (string comparison needs no real canonical content -- mirrors `sync`'s own non-blocking stale-removal precedent) | Registered finding (`MRS-ADP-003` reused, ERROR) |
| The skill-projection manifest is malformed JSON | Corrupt bookkeeping | Treated as "nothing previously tracked" (mirrors `_read_manifest`'s existing degrade) -- a tree only reachable via manifest tracking (e.g. a `"removed"` case with no live symlink either) is invisible this run | Registered finding (`MRS-ADP-009` reused, WARN) |
| An adapter-declared `skill_tree` resolves outside the loop home | Untrusted overlay value | That tree is skipped from the check entirely (mirrors `sync`'s own confinement refusal) | Registered finding (`MRS-ADP-011` reused, WARN) |
| `marshal preflight` runs against a loop home where every configured adapter already matches canonical | Nothing to check | `data.projection_conformance` reports empty `checks`/`unevaluated_trees`; preflight's own verdict is unaffected by this step | No finding |
| An unresolvable/malformed project slug (`adapters conform` only) | Precondition | No filesystem/harness touch at all | Registered finding (`MRS-ADP-001` reused, ERROR), mirrors `sync` |
| The named loop home is not provisioned (`adapters conform` only) | Precondition | No filesystem/harness touch at all | Registered finding (`MRS-ADP-002` reused, ERROR), mirrors `sync` |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/conformance.py` -- NEW, pure (AD-4). `TreeLiveState` (frozen
  dataclass: `tree`, `adapters: tuple[str, ...]`, `desired: bool`, `previously_projected:
  bool`, `live_target: str | None`, `live_exists: bool`, `expected_target: str`) -- every
  field already read by the caller, nothing read here. `TreeConformance` (frozen dataclass:
  `tree`, `adapters`, `status`, `detail`). `ConformanceReport` (frozen dataclass: `mechanism:
  str | None`, `checks: tuple[TreeConformance, ...]`, `unevaluated_trees: tuple[str, ...]`).
  Status constants `STATUS_LINK_TARGET_CONFIRMED = "link-target-confirmed"`,
  `STATUS_ADDED = "added"`, `STATUS_REMOVED = "removed"`, `STATUS_MODIFIED = "modified"`, plus
  `ALL_STATUSES` (frozenset of all four) for the meta-test's literal
  `"not-applicable" not in ALL_STATUSES` assertion. `_check_symlink_identity(state) ->
  TreeConformance` -- the one mechanism-specific checker this story ships; raises `ValueError`
  if given a `state` that is neither `desired` nor `previously_projected` (a caller-contract
  violation, never silently absorbed into a passing outcome). `MECHANISM_CHECKERS: Mapping[str,
  Callable[[TreeLiveState], TreeConformance]] = {"symlink": _check_symlink_identity}` -- the
  ONE declared table (AD-36's own shape, mirrored). `evaluate_conformance(live_states, *,
  mechanism, unevaluated_trees=()) -> ConformanceReport` -- the total entry point: if
  `mechanism` has no entry in `MECHANISM_CHECKERS` (including `None`), returns EVERY tree
  (both the explicit `unevaluated_trees` argument and every `live_states` tree) folded into
  `ConformanceReport.unevaluated_trees`, `checks=()`; otherwise runs each state through the
  registered checker.
- `src/pyforge/marshal/cli/adapters.py` -- EDIT. New `_confine_skill_trees(skill_trees, home,
  home_resolved, fs) -> tuple[dict[str, str], list[Finding]]` -- extracts `run_adapters_sync`'s
  existing inline confinement-safety loop (MRS-ADP-011) verbatim, so `gather_conformance_findings`
  reuses it instead of a second copy. New `gather_conformance_findings(home, *, fs, harness) ->
  tuple[dict[str, object], list[Finding]]` -- the read-only I/O boundary: canonical-presence
  check (MRS-ADP-003, non-blocking) -> `harness.adapter_skill_trees` (MRS-ADP-004, blocking) ->
  `_confine_skill_trees` (MRS-ADP-011) -> manifest read (`_read_manifest`, MRS-ADP-009) ->
  `core.skill_projection.plan_projection` (reused unchanged) -> per-tree live-state read
  (`fs.read_symlink_target`/`fs.exists`) for every tree in `{t.tree for t in plan.to_project} |
  previously_projected` -> `core.conformance.evaluate_conformance` -> `MRS-ADP-005` (reused)
  if `unevaluated_trees` is non-empty, `MRS-CONFORM-001` if any check's status is not
  `STATUS_LINK_TARGET_CONFIRMED`. New `add_adapters_subparser` nested action `conform`
  (`marshal adapters conform <slug> [--format]`) -> `run_adapters_conform(args, *, fs=None,
  harness=None, context=None)`: the SAME slug/home preconditions `run_adapters_sync` already
  checks (reusing `MRS-ADP-001`/`002` verbatim -- AD-31's own `MRS-DEPLOY-003` precedent for
  "same code, same tier, a second call site") -> `gather_conformance_findings` -> envelope
  emit. `_emit` gains a `command: str = "adapters sync"` and `renderer: Callable[[dict[str,
  object], tuple[Finding, ...]], str] = _render_text` keyword pair (both defaulted, so
  `run_adapters_sync`'s existing two call sites are unchanged) so `run_adapters_conform` can
  route through the same envelope-build/print/exit plumbing with its own renderer. New
  `_render_text_conform(data, findings) -> str` -- the `--format text` projection for
  `data.checks`/`data.unevaluated_trees`, mirroring `_render_text`'s own shape.
- `src/pyforge/marshal/cli/init.py` -- EDIT. `run_preflight` gains one more step, immediately
  before `return _emit_preflight(...)`: a LOCAL `from .adapters import gather_conformance_findings`
  (avoids the module-level circular import `cli/adapters.py`'s own `from .init import
  _home_path` would otherwise create -- mirrors `cli/deploy.py`'s identical local-import
  precedent, see that module for the existing convention), then
  `conform_data, conform_findings = gather_conformance_findings(home, fs=fs, harness=harness)`,
  `data["projection_conformance"] = conform_data`, `findings.extend(conform_findings)`. This is
  the AC's "runs as part of preflight whenever a non-default adapter is configured" clause --
  see Design Notes for why this is implemented as an unconditional call whose OWN output is
  empty when nothing is desired, rather than a separate "is a non-default adapter configured"
  pre-check.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register ONE new code, `MRS-CONFORM-001`
  (drift detected -- added/removed/modified, folded into one code per the `MRS-GATE-001`/
  `MRS-DEPLOY-003` "one code, several triggering shapes, same tier" precedent). `MRS-ADP-001/
  002/003/004/005/009/011` are REUSED verbatim from Story 6.2, not re-registered (same codes,
  new call sites).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Classify `MRS-CONFORM-001` at
  `Verdict.ERROR` (see Design Notes for the tier rationale) and add a docstring paragraph
  narrating Story 6.3's reuse of the six `MRS-ADP-*` codes plus the one new code.
- `tests/meta/test_ad31_conformance_check_can_genuinely_fail.py` -- NEW. The AC's own "reporting
  clean for a check that cannot fail is a meta-test failure" made real: (1) parametrized proof
  that `_check_symlink_identity`/`evaluate_conformance` return `STATUS_LINK_TARGET_CONFIRMED`
  if and only if `desired` is true AND `live_target == expected_target` -- every other
  combination in a full `itertools.product` sweep over `{desired, previously_projected,
  live_target-matches, live_target-wrong, live_exists-as-conflict, live-absent}` returns a
  DRIFT status, never confirmed; (2) proof that `evaluate_conformance` called with `mechanism=
  None`, or any synthetic mechanism string absent from `MECHANISM_CHECKERS`, NEVER returns a
  confirmed status for ANY input, including a `live_states` list that would otherwise pass --
  the "cannot fail" case is structurally incapable of reporting clean; (3) a literal
  `"not-applicable" not in core.conformance.ALL_STATUSES` assertion, plus confirmation that
  `core.verdict.LATTICE_ORDER` (imported directly) has no `not-applicable` member either.
- `tests/unit/test_conformance.py` -- NEW. `TreeLiveState`/`TreeConformance`/
  `evaluate_conformance` matrix (pure): confirmed, added, removed (both the "deleted
  out-of-band" and "stale, no longer desired" shapes), modified (retargeted and conflict
  shapes), unevaluated (no mechanism, unknown mechanism), the `ValueError` for a
  neither-desired-nor-tracked state.
- `tests/unit/test_adapters_cli.py` -- EDIT. `gather_conformance_findings`/`run_adapters_conform`
  matrix reusing the existing `FakeFs`/`FakeHarness` doubles: first-check confirmed (after a
  prior sync), added (never synced), removed (deleted out-of-band and stale-not-desired),
  modified (retargeted and conflict), canonical missing (non-blocking), adapter-enumeration
  failure, unsupported platform, malformed manifest, confinement refusal, malformed slug, home
  not provisioned, `--format text` rendering.
- `tests/unit/test_cli.py` -- EDIT (only if a preflight-integration test double needs a new
  `adapter_skill_trees` stub -- existing preflight tests' `FakeHarness`-equivalent doubles are
  audited during implementation; extended only if they do not already implement the method).
- `tests/unit/test_findings.py` -- EDIT. `REGISTERED_CODES` snapshot gains `MRS-CONFORM-001`.
- `tests/unit/test_verdict.py` -- EDIT, only if this suite maintains its own literal code-tier
  table separate from `core/verdict.py` (audited during implementation).

## Design Notes

- **Why "added/removed/modified" resolves to TREE granularity, never per-skill.** The AC's own
  text borrows generic file-diff vocabulary ("added, removed and modified skills per adapter
  tree") that would suit a content-diffing mechanism enumerating individual skill files. Story
  6.2 already forbids that mechanism outright ("No per-skill symlinks or file copies... would
  reintroduce exactly the per-entry drift AD-36's link-target-identity check exists to avoid
  needing to check" -- that story's own words, naming THIS story by implication). The only
  mechanism this project ships operates on whole directory trees; this story's own AC text
  (bullet 2) confirms the resolution directly: "a link-based projection asserts LINK-TARGET
  IDENTITY... and emits NO content-drift finding at all." "Skills" in the AC's phrasing is read
  as loose shorthand for "what a projected tree is supposed to deliver," not a literal
  per-skill-file report -- a genuine interpretive call, recorded here rather than left implicit
  (Think Before Coding).
- **Why "runs as part of preflight" is an unconditional call whose output degrades to empty,
  not a separate "is a non-default adapter configured" gate.** The AC's phrasing is singular
  ("a non-default adapter") where Story 6.2's own "configured adapters" reading is plural (the
  full `load_profiles` registry, not the one active `[adapter].name`). Introducing a SECOND,
  narrower "is THE active adapter non-default" predicate would silently diverge from Story
  6.2's own established reading and require a new helper this story would need to justify
  separately. Instead, `gather_conformance_findings` is called unconditionally from
  `run_preflight`, and its own behavior is ALREADY conditional on the identical plural
  "configured adapters" notion `plan_projection` already encodes: when every configured
  adapter's declared tree equals canonical, `plan.to_project` is empty, `live_states` is
  empty, and the function returns `checks=[]`/`unevaluated_trees=[]` with no finding at all --
  observably indistinguishable from "the check did not run" from the operator's perspective,
  while staying implemented as a single, unconditional call site that never needs to guess
  what "non-default" means as a separate predicate. This is a genuine, stated interpretive
  call (Think Before Coding) rather than a silent guess.
- **Why the Surface named by the epics doc (`cli/adapters.py`, `core/conformance.py`) omits
  `cli/init.py`, and this spec adds it anyway.** The "runs as part of preflight" clause is only
  satisfiable by touching `cli/init.py::run_preflight` somewhere -- Story 6.2's own Surface
  line named only `cli/adapters.py` too, yet its actual Code Map touched nine files plus tests;
  every prior story's epics-doc Surface line is a coarse pointer, not an exhaustive file list.
  Wiring the check as an ADDITIONAL preflight step (never a wholly separate command) is the
  literal instruction this story was given; `cli/init.py` is touched minimally -- four new
  lines immediately before the existing final `return`, no restructuring of anything else in
  that function.
- **Why the local import in `cli/init.py`, not a module-level one.** `cli/adapters.py` already
  imports `_home_path` FROM `cli/init.py` at module load time (Story 6.2). A module-level
  `from .adapters import gather_conformance_findings` in `cli/init.py` would make the two
  modules import each other at load time -- an immediate `ImportError`. `cli/deploy.py`
  already carries the identical local-import pattern for the identical reason (`from .init
  import _home_path` inside several of its own functions, with an explanatory comment at each
  site) -- this story reuses that established convention rather than inventing a new one or
  restructuring the module graph.
- **Why `MRS-ADP-001/002/003/004/005/009/011` are reused rather than re-registered under
  `MRS-CONFORM-*`.** `adapters conform` shares the IDENTICAL preconditions `adapters sync`
  already has codes for (malformed slug, home not provisioned, canonical missing, adapter
  enumeration failure, unsupported platform, malformed manifest, an unsafe declared tree) --
  the same real-world condition, evaluated the same way, at the same lattice tier, from a
  second call site within the SAME `adapters` command group. `MRS-DEPLOY-003` already
  establishes this codebase's own precedent for exactly this shape ("AD-31 forbids
  classifying the SAME code two different ways depending on which of its two emit sites
  fired, so both fold into this one rung"). Minting seven near-duplicate codes that would
  classify identically would be needless duplication for an Effort: S story with a real,
  usable precedent already on file.
- **Why `MRS-CONFORM-001` classifies `Verdict.ERROR`, not `Verdict.GATE_FAILED` or
  `Verdict.WARN`.** `Verdict.GATE_FAILED` is reserved (per `core/verdict.py`'s own docstring)
  for "a configured verify command ran and failed" -- a PROJECT's own declared check, not
  Marshal's own infrastructure. Drift in a projected skill tree is closer to `MRS-ADP-003`'s
  own "a real operation this run needed was blocked" and `MRS-CHECK-002`'s own "a detector
  reported real findings" -- both `Verdict.ERROR`. `Verdict.WARN` is this codebase's own
  reserved tier for "a safe refusal" (`MRS-ADP-007`) or "a paper-trail gap that never blocks an
  otherwise-viable operation" (`MRS-ADP-009/010`, `MRS-SPIN-015`) -- drift is neither: it is a
  positive, confirmed statement that an adapter's own projected tree no longer matches
  canonical, exactly the "real gap found" shape every `MRS-PREFLIGHT-*` code already uses
  `Verdict.ERROR` for.
- **Why the passing status is named `"link-target-confirmed"`, not `"clean"`.** `Verdict.CLEAN`
  is the lattice's own reserved vocabulary (`core/verdict.py`, AD-7/AD-31), computed by
  `compute_verdict` over emitted findings -- never assigned directly by any other module.
  Naming this module's own per-tree passing outcome `"clean"` would read as if
  `core/conformance.py` were making a lattice-level claim it has no authority to make (AD-31:
  "no other module assigns a verdict directly"). `"link-target-confirmed"` names exactly what
  was checked, matching the AC's own "asserts LINK-TARGET IDENTITY" wording.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **2865 passed** (2823 baseline
  from S-6.2 + 42 new/updated: `core/conformance.py`'s own 11 unit tests, the new meta-test's
  6, `gather_conformance_findings`/`run_adapters_conform`'s 16 new `test_adapters_cli.py`
  cases, plus the `REGISTERED_CODES` snapshot addition and the two `FakeHarness`/
  `_RecordingHarness` doubles extended for `adapter_skill_trees`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed (confirmed identical on
  `main` before this story via `git stash`): the accepted `pyforge-steward`
  (`_http` module-alias gap, `age` conda-only run-dep) and `pyforge-doctor` (`mcp` dependency
  gap) baseline, unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- AD-3, AD-4, AD-9 all KEPT (87 files, 481 dependencies analyzed).

## Review Triage Log

No adversarial review pass was run for this session (single-agent implementation, no
Blind Hunter/Edge Case Hunter fan-out requested). Two design gaps were caught and fixed
during self-implementation before the verification run, both surfaced by the FULL test
suite rather than a separate review pass:

- Two existing `HarnessPort` test doubles (`tests/meta/test_ad11_write_boundary.py::
  _RecordingHarness`, `tests/unit/test_init.py::FakeHarness`) predate Story 6.3's new
  `adapter_skill_trees` call from `run_preflight`'s own additional step and did not implement
  it -- `pyforge-marshal-test` caught the resulting `AttributeError` immediately. Both doubles
  now implement it (empty by default -- no configured adapter differs from canonical -- so
  every pre-existing preflight test stays converged with no new write surface or finding).
- `gather_conformance_findings`'s own `fs.resolve_path(home)` call (needed to confine
  adapter-declared `skill_tree` values, mirroring `run_adapters_sync`'s identical, ALSO
  unguarded call) was originally unguarded; `test_init.py::
  test_preflight_main_checked_out_once_resolve_path_failure_reports_finding` (which sets a
  blanket `fail_resolve_path` on its `FakeFs` double) surfaced an uncaught `FsError` crashing
  `run_preflight` entirely instead of degrading to a finding. Wrapped in `try`/`except FsError`,
  reusing `MRS-ADP-004`'s tier (`Verdict.UNEVALUABLE`) with an adapted message; `run_adapters_
  sync`'s own identical unguarded call is a pre-existing, out-of-scope gap this story does not
  touch (not reachable by any of its own tests, and not named by this story's AC).

**Follow-up review recommendation: false** -- no design questions remain open; both fixes
above are narrow, test-driven corrections to newly-added code, not new open questions.

## Review Triage Log

### 2026-08-07 -- Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 2)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter) **`gather_conformance_findings`'s per-tree `fs.read_symlink_
    target(tree_path)` call was unguarded** -- distinct from the implementer's own self-review fix
    above, which caught the SAME class of gap at `fs.resolve_path(home)` (the confinement step) but
    not this one, inside the live-state-gathering loop. Unlike every other `FsError`-raising call
    in this module, this one had no `try`/`except`; `LocalFs.read_symlink_target` explicitly
    documents a real `PermissionError`-from-an-unsearchable-ancestor failure mode on this package's
    own Python 3.12 floor. Since this function now runs UNCONDITIONALLY as part of `marshal
    preflight` (this story's own AC), an uncaught `FsError` here would crash the entire preflight
    command with a raw traceback -- directly defeating the "runs unconditionally, never crashes"
    design goal. Fixed: wrapped per-tree (mirrors `MRS-ADP-006`/`008`'s own "one tree's failure
    never aborts another's" isolation), registering a new code `MRS-ADP-012` (`Verdict.ERROR`) and
    adding the tree to `unevaluated_trees` rather than letting the exception propagate. New test:
    `test_conform_unreadable_symlink_state_degrades_to_a_finding_never_crashes`.
  - `high` `patch` (Edge Case Hunter) **The unsupported-platform branch under-reported which trees
    were unevaluated.** `plan.unsupported_trees` (`core/skill_projection.py`'s own contract) is
    scoped to only the CURRENTLY DESIRED tree set -- a tree that is previously-projected (tracked in
    the manifest) but no longer desired by any configured adapter (e.g. a deconfigured adapter)
    would silently vanish from both the `MRS-ADP-005` finding and `data["unevaluated_trees"]`,
    reporting structurally identical to "nothing to check" (`checks: []`, `unevaluated_trees: []`)
    even though a real, previously-projected tree's live symlink state was never read or compared
    -- precisely the "clean for a check that structurally cannot fail" shape this whole story exists
    to forbid, reached via a real path the implementer's own test suite did not cover. Fixed: the
    unsupported-platform branch now reports against `all_trees` (desired UNION previously-projected)
    rather than `plan.unsupported_trees` alone -- which itself required reconstructing the true
    desired-tree set as `set(desired_adapters_by_tree) | set(plan.unsupported_trees)`, since
    `plan.to_project` (the source `desired_adapters_by_tree` was built from) comes back EMPTY
    whenever the mechanism is unsupported (`plan_projection`'s own contract: `to_project` and
    `unsupported_trees` are mutually exclusive). New test:
    `test_conform_unsupported_platform_still_reports_a_previously_projected_only_tree`.

**Follow-up review recommendation: false** -- both findings are isolated to the same function's
own per-tree read loop and platform-unsupported branch, each covered by a dedicated new test
proving the fix; no new design questions opened.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-marshal
pyforge-marshal-test` -- **2867 passed**; `pixi run --frozen -e pyforge-ci pyforge-deps-test` --
3 failed, all pre-existing accepted baseline (2 `pyforge-steward`, 1 `pyforge-doctor` `mcp` gap
from Story 2.1 -- confirmed identical on `main` via `git stash`, not introduced by this story);
`lint-imports` -- AD-3/AD-4/AD-9 all KEPT (87 files, 481 dependencies analyzed).

</intent-contract>
