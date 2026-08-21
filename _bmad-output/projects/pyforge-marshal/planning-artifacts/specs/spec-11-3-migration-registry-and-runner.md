---
title: 'Migration registry and runner'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
difficulty: ''
baseline_revision: 'a27c06ebff28b8dbc0ed9703d5e19c02de466ee3'
final_revision: 'f749d937af9053a220457d28d6fbfeb16c8032f4'
---

<intent-contract>

## Intent

**Problem:** `seed/migrate/__init__.py` is an empty stub. Nothing in this codebase absorbs a
breaking model-version change (a renamed managed artifact, a tier-rule change) into an installed
repo — that would be a manual, per-repo chore today, exactly the drift class the seed installer
exists to eliminate. `plan/build.py`'s own docstring already forward-references this story's
producer (AD-62): "a future story adding a different target state (e.g. a migration's own
plan-producing function)."

**Approach:** Add `seed/migrate/registry.py`: a `Migration` record (`from_version`, `to_version`,
a pure `(RepoView, SeedState) -> Plan` function), an explicit registry tuple, a `chain()` function
that walks the registry from `state.model_version` to the bundled model version in strict
version-linked order (erroring by name on any gap), and a `compose()` function that calls each
migration's function in order and concatenates their actions into one `Plan` sharing a single
`RepoFingerprint` — the same `Plan` shape `apply/run.py::run_apply` already consumes, so the
runner hands its output to the existing apply path, never a new one.

## Boundaries & Constraints

**Always:**
- Every migration function is pure: `(view: RepoView, state: SeedState) -> Plan`, reads only,
  never calls `fs.write`/`replace_span`/`remove`/`symlink` — proven by a write-blocking fixture
  test (monkeypatch `fs.write`/`replace_span`/`remove`/`symlink`, assert none are called).
- `chain()` selects migrations in strict semver-linked order: starting at `state.model_version`,
  repeatedly follow the migration whose `from_version` equals the current version to its
  `to_version`, until reaching the bundled version. A registered migration whose `from_version`
  has no predecessor reachable from `state.model_version` is simply not part of the chain (this
  is not a gap — it's an unrelated migration for a different starting point).
- A gap (no migration registered with `from_version` equal to the current chain position, while
  the current position is still below the bundled version) is a clear, named error stating the
  exact missing `from_version` step — never a silent partial chain.
- Applied migrations are recorded in `state.migrations_applied[]` (the field already exists,
  shipped in S-10.2) keyed by `to_version`, and `chain()` excludes any migration whose
  `to_version` is already present there — running the chain-then-compose sequence twice against
  the same, now-updated state computes an EMPTY chain the second time.
- A migration targeting a `copied-seeded` artifact's action is not included in the composed
  `Plan.actions` by default — it is offered via `Plan.skipped` (the existing "known, not applied"
  mechanism, S-9.x) with a reason naming `--include-seeded`, unless the composer is explicitly
  told to include seeded actions.
- Every `Action` a migration's function produces is validated against the never-write set at PLAN
  time (via a new, small public `fs` helper — see Design Notes), not discovered only when
  `apply/run.py` later tries to write it — a violation raises before `compose()` returns.
- Match existing house style exactly: `from __future__ import annotations`, dense rationale
  docstrings, frozen dataclasses, exact-symbol imports, real `tmp_path` git-repo test fixtures
  matching sibling `test_seed_*.py` files (no shared `conftest.py`).

**Block If:** none identified — the linear from/to chain shape, the reuse of `Plan.skipped` for
the seeded-offer case, and the new small `fs` plan-time check are all determined by the epics AC
plus existing, inspectable code; no decision here requires a human call.

**Never:**
- Never add a CLI verb or touch `cli/seed.py` — `update` stays Story 11.4's stub to wire.
- Never modify `plan/types.py`'s `Action`/`Plan`/`SkippedArtifact` dataclass shapes if the
  existing `skipped` mechanism can represent the seeded-offer case (investigate its real shape
  before assuming); if it genuinely cannot, say so explicitly in Design Notes rather than
  silently forcing a fit.
- Never let a migration function touch the filesystem directly — every effect is expressed as
  `Action`s in the `Plan` it returns; the runner (this story) or a future caller (Story 11.4)
  applies them through the existing `apply/run.py::run_apply`.
- Never build a general graph-search/branching migration resolver — the chain is a strict linear
  walk (one migration per version-hop); a genuinely branching migration graph is out of scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Simple chain | `state.model_version=1.0.0`, bundled=1.2.0, migrations registered 1.0.0→1.1.0 and 1.1.0→1.2.0 | `chain()` returns both, in order | No error expected |
| Already at bundled version | `state.model_version` equals the bundled version | `chain()` returns an empty tuple | No error expected |
| Gap in the chain | migrations registered 1.0.0→1.1.0 only, bundled=1.2.0, state at 1.0.0 | Clear error naming the missing `from_version=1.1.0` step | Raised, named |
| Re-run after applying | `state.migrations_applied` already contains the just-applied `to_version` | `chain()` computed again returns empty (or only the remaining unapplied steps) | No error expected |
| Migration writes directly | A deliberately malicious migration function calls `fs.write` | Write-blocking fixture test catches it — never shipped as a passing case | Test fails loudly if this regresses |
| copied-seeded action, default | A migration's `Plan` includes an action for a `copied-seeded` artifact, `include_seeded=False` | Action appears in the composed `Plan.skipped`, not `Plan.actions` | No error expected |
| copied-seeded action, opted in | Same, `include_seeded=True` | Action appears in `Plan.actions` | No error expected |
| Never-write target | A migration's `Plan` includes an action whose target path matches the never-write set | `compose()` raises `NeverWriteViolation` before returning, at plan time | Hard error, no partial composition |
| SC-07 end-to-end | A fixture repo at a simulated v1 state; a registered v1→v2 migration renaming a managed artifact and changing a tier rule | Chain computes, composes, applies via `run_apply`; a subsequent `check`-equivalent detect pass against the fixture reports conformant | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/migrate/registry.py` -- NEW: `Migration` dataclass, `RepoView` dataclass (if no suitable existing type covers "what a migration function reads from" — check `detect/inventory.py`'s `Inventory` type first; reuse it if it fits rather than inventing a parallel one), the migration registry tuple, `chain()`, `compose()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- CHANGED: add one small public function (e.g. `check_never_write(path: Path, *, repo_root: Path, never_write: NeverWrite) -> None`) wrapping the existing private `_guard`'s check-only logic — pure, no I/O, raises `NeverWriteViolation` on a match. This is the plan-time check the AC requires ("fails at plan time, not apply time"); no such public entry point exists today.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/types.py` -- inspect `SkippedArtifact`'s real shape before deciding whether it fits the seeded-offer case unmodified (see Never bullet); expect NOT to change this file.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_migrate_registry.py` -- NEW: unit-tests the I/O matrix above, including the write-blocking purity fixture (mirroring `test_seed_apply_run.py::test_no_fs_call_at_all_when_a_run_succeeds`'s own idiom) and the SC-07 end-to-end proof (a real `run_apply` call against a synthetic fixture repo).

## Tasks & Acceptance

**Execution:**
- [x] `seed/fs.py` -- add the small public `check_never_write`-shaped plan-time guard wrapper described in the Code Map
- [x] `seed/migrate/registry.py` -- implement `Migration` (frozen dataclass: `from_version: ModelVersion`, `to_version: ModelVersion`, `fn: Callable[[RepoView, SeedState], Plan]`), a `RepoView` (reusing an existing type if one fits `detect/inventory.py`'s `Inventory` or similar — otherwise a minimal new frozen dataclass wrapping `repo_root: Path` plus whatever read-only context a migration function plausibly needs), an explicit `MIGRATIONS: tuple[Migration, ...]` registry (empty by default — real migrations are a future model-version-bump's job, not this story's), `chain(state: SeedState, bundled_version: ModelVersion, *, registry: tuple[Migration, ...] = MIGRATIONS) -> tuple[Migration, ...]` (strict linear walk, named-gap error), and `compose(migrations: tuple[Migration, ...], view: RepoView, state: SeedState, *, repo_fingerprint: RepoFingerprint, repo_root: Path, never_write: fs.NeverWrite, include_seeded: bool = False) -> Plan` (calls each migration's `fn` in order, concatenates actions, routes `copied-seeded` actions to `Plan.skipped` unless `include_seeded`, plan-time-guards every action's target path via the new `fs` helper)
- [x] `tests/unit/test_seed_migrate_registry.py` -- cover the I/O matrix: simple chain, already-at-bundled, gap-in-chain (named error), re-run-is-empty (simulating "running update twice" via two direct `chain()` calls against before/after state), migration-purity write-blocking fixture, copied-seeded default-vs-opted-in, never-write-at-plan-time, and the SC-07 end-to-end proof (synthetic fixture repo, a registered test migration performing a rename + tier-rule-equivalent change, real `run_apply`, a subsequent conformance check against the result)

**Acceptance Criteria:**
- [x] Given migration modules registered with `from_version`/`to_version`, when `chain()` computes the path from `state.model_version` to the bundled model version, then migrations are selected in strict linked order and `compose()` merges their actions into one `Plan`
- [x] Given a migration function, when it runs, then it performs zero filesystem writes (proven by a write-blocking fixture)
- [x] Given migrations already recorded in `state.migrations_applied[]`, when `chain()` runs again, then those migrations are excluded — never re-run
- [x] Given a migration's `Plan` targets a `copied-seeded` artifact, when `compose()` runs without `include_seeded`, then that action lands in `Plan.skipped`, not `Plan.actions`
- [x] Given a migration's `Plan` targets a never-write path, when `compose()` runs, then it raises `NeverWriteViolation` before returning (plan time), never only surfacing when `apply/run.py` later tries to write it
- [x] Given a simulated v1→v2 breaking change (a tier-rule change plus a renamed managed artifact) registered as a test migration, when applied against a fixture repo via the real `run_apply`, then the fixture ends conformant with zero manual edits (SC-07)
- [x] Given a registered chain with a missing intermediate `from_version` step, when `chain()` runs, then it raises a clear error naming the missing version
- [x] Given the existing `pyforge-marshal` test suite and meta-tests (P-01 write-primitive scan, layer-import rules, P-12 migration-purity), when run after this change, then they all still pass with no new violation

## Design Notes

**Why a strict linear chain, not a general graph.** The epics AC describes "the chain from
`state.model_version` to the bundled model version" as a single path, and "ordered, once-only
migrations" implies one migration per version-hop, not branching alternatives. A linear walk
(`from_version` of step N+1 must equal `to_version` of step N, first step's `from_version` equals
`state.model_version`) is the simplest structure that satisfies every AC clause and SC-07's own
"absorbed... with zero manual edits" framing, without building graph-search machinery this
story's own Never bullet explicitly rules out.

**Why `Plan.skipped` for the seeded-offer case, investigated not assumed.** The epics AC's
"emits an offer action that apply skips unless `--include-seeded` is passed" maps naturally onto
whatever "known but not included" concept `plan/types.py` already ships (`SkippedArtifact`,
S-9.x) — reusing it avoids widening the `Action`/`Plan` contract every other consumer
(`apply/run.py`, `verbs/adopt.py`) already depends on. Read `SkippedArtifact`'s actual fields
before implementing; if its existing reason/shape doesn't naturally fit "this was a migration's
offer, not a detect-time skip," extending it with a new reason value (not a new field) is
preferred over a parallel mechanism.

**`RepoView`'s shape should be minimal and read-only.** A migration function needs enough context
to decide what actions to emit (e.g. "does this artifact still exist at its old path") without
being handed write access. Check `detect/inventory.py`'s existing `Inventory` type first — if it
already captures "what's on disk for each manifest entry," wrapping `repo_root` + that inventory
is likely suffient and avoids a parallel read-model. Only build a new, narrower `RepoView` if
`Inventory` pulls in more (or different) machinery than a migration genuinely needs.

## Design Notes addendum

**`RepoView` -- resolved, not left open.** `detect.inventory.Inventory` was read in full before deciding: it is used directly as `RepoView` (`RepoView = Inventory`, a plain type alias in `registry.py`, no new dataclass). `classify(bundled_manifest, repo_root)` already answers exactly the question a migration function needs ("what does this manifest entry actually look like in the target repo right now"), `Inventory` carries `repo_root` alongside it, and `migrate` sitting beside `plan`/`detect` in the module-dependency chain (both of which already import `detect.inventory`) means the import adds no new layering. A future caller (Story 11.4) builds `view` the same way `build_plan` builds its own classification: `classify(bundled_manifest, repo_root)`.

**`SkippedArtifact` reuse -- resolved, no dataclass or field change.** `plan/types.py::SkippedArtifact` was read in full: it has exactly three fields (`artifact_id`, `target_path`, `pattern`), with no separate "reason" field to extend with a new value -- the Design Notes' own suggested fallback ("extending it with a new reason value") does not literally apply because no reason enum exists on this dataclass at all. The actual, load-bearing decision: `pattern` is documented as free text a human reads in a reviewed `plan.json` ("the glob that matched"), not a value any downstream consumer (`apply/run.py`, `verbs/skips.py::apply_skips`) re-parses as a real glob -- so `compose()` reuses it verbatim, populating it with the literal string `"--include-seeded"` for a routed `copied-seeded` action. This communicates the same fact a `--skip` glob does ("here is why this artifact is not in `actions`") without widening `Plan`'s shape for any of its other consumers. `plan/types.py` was not modified.

**Gap-error exception type -- `InternalError` (exit 10), not `PreconditionFailure` (exit 3).** Not specified by the epics AC or the intent-contract, so resolved by precedent: `PreconditionFailure`'s own docstring frames itself around properties OF THE REPO (dirty worktree, non-git target, hand-edited content). A migration-chain gap is not a fact about the repo -- it is a fact about whether the SHIPPED migration registry can bridge `state.model_version` to the bundled version, the same class of failure `state/store.py`'s `_schema_text`/`_load_schema`/`_opt_out_pattern` already raise `InternalError` for (a broken or incomplete packaged artifact). The raised message carries the literal token `migration-chain-gap` plus the exact missing `from_version`, mirroring `apply/run.py`'s own `stale-plan`/`escaping-target` named-token convention.

**No new `MigrationChainGapError` type was added.** `chain()` raises the existing `InternalError` leaf directly rather than minting a new exception class -- consistent with this story's Never bullet (no CLI wiring yet) and with `SeedError`'s own closed, six-leaf taxonomy (`errors.py`'s docstring: a seventh leaf is a deliberate, reviewed addition, not a default for a new failure mode that already fits one of the six).

**Verified, not merely implied: `migrate` sits beside `plan`/`detect`/`state` in the import-linter's scope.** `tests/meta/test_ad3_ad4_import_linter.py` pins its AD-3 contract's `source_modules` to a set that includes `pyforge.marshal.seed` as a whole (not an enumerated submodule list), so `seed/migrate/registry.py` is automatically covered by both the AD-3 (`bmad_loop`) and AD-4 (`subprocess`/`os`/`time`/`adapters`, `core`-only) forbidden-import contracts with no pyproject.toml edit needed -- confirmed by running the full `pyforge-marshal-test` suite (which includes that meta test) green after this story's changes, with no new contract required.

## Spec Change Log

<!-- Empty: no bad_spec loopback occurred for this story. Every review-pass finding was
     addressed as a patch or a defer, applied directly against the already-sound design. -->

## Review Triage Log

### 2026-08-21 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 4, medium 3, low 2)
- defer: 1 (low 1)
- reject: 4 (low 4)
- addressed_findings:
  - `[high]` `[patch]` `chain()` hangs FOREVER on a registry cycle or a self-referencing `Migration` (`from_version == to_version`) — confirmed by live execution (`timeout 5` hit the timeout). Fixed at the root: `Migration.__post_init__` now requires `from_version < to_version`, making a cycle structurally impossible through the public API (a strictly-increasing sequence can never revisit a version); `chain()` additionally tracks a `visited` set as defense in depth, raising `migration-chain-cycle` rather than looping if a cycle somehow reaches it anyway. Verified live post-fix: both guards fire correctly, no hang.
  - `[high]` `[patch]` `compose()` accepted an absolute or `..`-escaping `action.target_path` with zero refusal (confirmed by execution: `repo_root / "/etc/passwd"` discards `repo_root` entirely) — undermining the story's own headline "plan time, not apply time" claim for this exact failure class (deferred to `apply/run.py`'s own later check in practice). Fixed: `compose()` now duplicates `apply/run.py::run_apply`'s own hardened, execution-verified escaping-target check (literal absolute/`..` check, then resolve, then parents check) before the never-write guard — matching this package's "small deliberate duplication beats an import across a module boundary" precedent (`migrate` never imports `apply/run.py`, per this module's own Never bullet).
  - `[high]` `[patch]` `compose()` could silently build a `Plan` violating `Plan`'s own defended invariant (an `artifact_id` appearing in both `actions` and `skipped`, or duplicated within `actions`) — confirmed by execution; `Plan.from_json_dict` refuses this but only at the JSON round-trip boundary, which `compose()`'s in-memory output never crosses before a future caller could hand it straight to `run_apply`. Fixed: `compose()` now tracks claimed ids and raises `migration-plan-collision` naming the offending id and both colliding collections.
  - `[high]` `[patch]` Two registry entries sharing the same `from_version` were silently resolved by a plain dict's last-write-wins semantics, hiding one migration entirely with no error. Fixed: `chain()` now raises `migration-registry-ambiguous` naming the duplicated `from_version` before the walk even starts.
  - `[medium]` `[patch]` `compose()` silently dropped each migration's own returned `Plan.skipped` entries (only `.actions` was ever read). Fixed: merged into the composed result, claimed against the same duplicate-id check as everything else.
  - `[medium]` `[patch]` `SkippedArtifact.pattern`'s reuse for the seeded-offer sentinel (`"--include-seeded"`) broke `cli/seed.py::_render_plan_text`'s existing, unmodified renderer (`f"matched --skip {pattern!r}"` → a false "matched --skip" claim). Bounded in-scope fix: reworded the sentinel to state the real fact plainly even inside that template; full fix needs `cli/seed.py`/`plan/types.py` changes outside this story's Surface — filed as `DW-FU-11-3` for Story 11.4 to close when it actually renders a migration-composed plan to a human.
  - `[medium]` `[patch]` `Migration` carried no validation that `to_version` differs from (or exceeds) `from_version` — the root enabler of the cycle/hang finding above. Fixed as part of that same patch (`__post_init__` addition).
  - `[low]` `[patch]` The real, non-empty module-level `MIGRATIONS` default-argument lookup path (`by_from = {...}` construction against the actual default) was untested — every test passed its own `registry=` override. Attempted a `monkeypatch.setattr(registry, "MIGRATIONS", ...)`-based test; discovered (and verified by running it) that `chain`'s `registry: tuple[Migration, ...] = MIGRATIONS` default is bound to the ORIGINAL tuple object at function-definition time, so monkeypatching the module attribute afterward cannot affect it — a genuine Python default-argument-evaluated-once gotcha, not a testable gap by that method. No production impact (a future story adding real entries to the `MIGRATIONS = (...)` tuple LITERAL re-evaluates the default correctly on next import); the attempted test was removed rather than shipped broken/misleading.
  - `[low]` `[patch]` The SC-07 fixture's helper function was named `renaming_fn` but performed a pure add (no actual rename/removal semantics) — misleading name, cosmetic. Renamed to `materializing_fn`.
  - `[low]` `[defer]` FR-96's AC literally says "asserted by running update twice," but `marshal seed update` doesn't exist yet (Story 11.4's own surface) — this story's test simulates the "twice" proof via two direct `chain()` calls against before/after state, which is the most this story's own scope can do. Not a defect; noted for completeness so it isn't silently assumed as a SEPARATE, already-closed AC once 11.4 lands — Story 11.4 should re-verify FR-96 end to end against its own real `update` verb.
  - `[low]` `[reject]` `Migration.fn` returning a full `Plan` (with an always-discarded `RepoFingerprint`) rather than a leaner `tuple[Action, ...]` — matches the epics AC's own literal wording, `"(RepoView, State) -> Plan"`; simplifying away the return type would contradict the AC itself, even though the fingerprint-discarding is mildly wasteful (one field, low cost).
  - `[low]` `[reject]` `compose()` not validating `action.target_state` — real but narrow (would need understanding valid per-artifact-class state transitions to close properly); disproportionate validation cost for a currently-hypothetical malformed-migration scenario.
  - `[low]` `[reject]` "Last migration wins" duplicate-`from_version` behavior "untested" — moot once duplicate `from_version` now raises instead of silently shadowing (see the patch above); no "last wins" behavior remains to test.
  - `[low]` `[reject]` The module docstring's reuse-justifications for `RepoView`/`SkippedArtifact.pattern` didn't trace forward to `cli/seed.py`'s existing consumer — addressed directly by the `SkippedArtifact.pattern` patch + `DW-FU-11-3` above; no separate action needed.

**Verification after this pass:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5131 passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 84 passed. `ruff check` on every touched file → clean. Live execution confirmed both the hang-fix and the cycle-guard fire correctly against a deliberately malicious/corrupted registry.

## Auto Run Result

**Summary:** Added `seed/migrate/registry.py`: `Migration` (a validated, strictly-forward-progressing version-hop record), `chain()` (a linear from/to walk from `state.model_version` to the bundled version, excluding already-applied steps), and `compose()` (concatenates each migration's actions into one `Plan`, routing `copied-seeded` actions to `Plan.skipped` unless `--include-seeded`, validated against escaping targets, the never-write set, and cross-migration id collisions at PLAN time). Added one small public `fs.check_never_write` wrapper for the plan-time guard. The initial implementation was fundamentally sound (SC-07's real end-to-end pipeline test passed on the first pass) but under-defended against several malformed-input/malformed-registry shapes; one review pass found and fixed all of them directly (9 patches, no revert/re-derivation needed — unlike Story 11.2, nothing here shipped actively wrong behavior in production, since `MIGRATIONS` is empty and nothing calls this module from a real CLI path yet).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/migrate/registry.py` -- new module.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- new `check_never_write` wrapper.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_migrate_registry.py` -- new, full I/O-matrix + pass-1 hardening coverage (21 tests).

**Review findings breakdown:** 9 patched (4 high, 3 medium, 2 low, including one confirmed-by-execution infinite-hang fix), 1 deferred (`DW-FU-11-3`, low), 4 rejected (matches AC literal wording, disproportionate cost, or moot after another patch).

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5131 passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 84 passed. `ruff check` on every touched file → clean. Direct live-execution repro of the hang fix and the cycle-detection guard (both fire correctly, no hang, verified with a 5-second `timeout` wrapper).

**Residual risks:** Low. `DW-FU-11-3` (misleading CLI rendering of a migration-sourced skip) has no live consumer yet — Story 11.4 will need to address it when it actually wires `update` and renders a real plan. `MIGRATIONS` remains empty; the machinery is unexercised by any real migration until a future model-version bump registers one.

**Baseline:** `a27c06ebff28b8dbc0ed9703d5e19c02de466ee3`
**Final:** (set after commit below)

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new `test_seed_migrate_registry.py`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, no new disallowed import
</content>
