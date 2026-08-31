---
title: 'Auto-derived effective surface, no manual per-story widening'
type: 'feature'
created: '2026-08-31'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      compute_effective_surface's literal-string-set intersection silently defeats the
      auto-derived glob-form default whenever a story's own spec declares a `surface:`
      field with literal file paths.
    evidence: |-
      Every populated `surface:` field found in this repo's own tracked specs (e.g.
      spec-marshal-token-economy/SPEC.md, spec-risk-tiered-review-depth/SPEC.md,
      spec-fleet-status-supervisor-fallback/SPEC.md) uses exact literal file paths, never
      glob syntax. `compute_effective_surface` does `set(policy_surface) & set(spec_surface)`
      -- exact string-set intersection, not glob-vs-literal matching -- so a glob-only
      policy_surface (declared OR auto-derived) never intersects with a literal-path
      spec_surface, and `effective_surface` comes out empty, meaning MRS-GATE-007 fires for
      every changed file regardless of the new fallback. This is a pre-existing property of
      the AD-27 combinator (Story 2.3), unchanged and out of scope for this story to fix
      (it would require modifying compute_effective_surface's intersection-only body, which
      this story's own boundaries and meta-test explicitly forbid touching) -- confirmed
      identical behavior already existed for any hand-declared glob-only `[epic_surfaces]`
      entry before this story. Severity raised medium -> high on review pass 2 (Blind
      Hunter): every populated `surface:` field found in this repo's tracked specs uses
      literal paths, so this is the COMMON case a real story hits, not a rare edge case --
      it likely nullifies the "no manual per-story widening" promise for any story that also
      declares its own `surface:` field.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py::compute_effective_surface
    severity: high
  - summary: >-
      default_epic_surface(project_slug) assumes a src/shared/packages/<slug>/ package tree
      exists; for a BMAD project without that convention the derived default silently
      collapses to near-empty with no diagnostic.
    evidence: |-
      The function is a pure string-interpolation with no existence check by design (matches
      the FR-50 precedent). For a project_slug that isn't one of the 8 PyForge Guild
      stations, the package-tree and artifact-tree globs simply never match any real file,
      leaving only the 5 bookkeeping paths as the effective default -- not a regression (it
      is never worse than the pre-story deny-all), but the story's stated benefit does not
      materialize for such a project, silently. Review pass 2 (Blind Hunter): a future fix
      shape could mirror MRS-GATE-004's precedent (a WARN advisory finding for an analogous
      "nothing meaningfully configured" state) rather than staying silent.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py::default_epic_surface
    severity: low
  - summary: >-
      evaluate_dispatch_verification's project_slug parameter has no shape validation before
      flowing into the auto-derived default, unlike cli/gate.py's _run_scope_check which
      validates first.
    evidence: |-
      cli/gate.py:546 guards `if not project_slug or not policy._is_valid_project_slug(...)`
      before ever reaching the scope-check logic. dispatch_verify.py::evaluate_dispatch_verification
      has no equivalent guard, but this is a pre-existing trust-boundary characteristic, not
      newly introduced: the same unvalidated project_slug already flows into
      compose_dispatch_policy's own path construction in the caller
      (dispatch_supervisor/__main__.py::_run_and_journal_verification), upstream of this
      story's change, with identical exposure.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py::evaluate_dispatch_verification
    severity: low
  - summary: >-
      pyforge-marshal's own live "22"/"28" [epic_surfaces] stopgap entries are intentionally
      left in place by this story (per its own Never boundary and the epics.md operational
      note), but no deferred-work-ledger entry tracks that follow-up removal yet.
    evidence: |-
      epics.md's own operational note for Epic 28 says the "28" stopgap is replaced by a
      LATER story's work, not this one, and this spec's Never section explicitly defers
      stopgap removal as separate follow-up work -- both are grounded in the intent itself,
      not an out-of-scope call this spec invented. The gap is purely that nothing in this
      diff creates a trackable ledger entry for the follow-up removal, so it risks being
      forgotten.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:107
    severity: low
  - summary: >-
      dispatch_verify.py's scope_check JSON payload never exposes policy_surface (only
      effective_surface/changed_files/violations), unlike cli/gate.py's payload -- a
      pre-existing reporting-shape asymmetry that review pass 2 found newly more meaningful
      now that declared vs. auto-derived policy_surface values can differ materially.
    evidence: |-
      dispatch_verify.py::evaluate_dispatch_verification's data["scope_check"] dict (around
      line 213) was already missing a policy_surface key before this story; this story does
      not change that dict's shape, only the value flowing into effective_surface. In the
      common case (no spec surface: field) effective_surface equals policy_surface, so an
      operator can usually still infer the resolved surface from the existing field -- this
      is an observability nicety, not a correctness gap, so left as pre-existing.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py::evaluate_dispatch_verification
    severity: low
baseline_revision: '3bc9a072c6943cbf6594f5d961a9f87c2e6e93de'
---

<intent-contract>

## Intent

**Problem:** `MRS-GATE-007` denies every changed file whenever a station has no `[epic_surfaces]` entry declared for the active epic, forcing operators to hand-widen the policy TOML per story just to let legitimate within-station work land (the live 2026-08-31 `"28"` station-wide-wildcard stopgap in `pyforge-marshal`'s own `marshal-policy.toml` exists only because of this toil).

**Approach:** Add a pure, `project_slug`-derived default policy surface (the station's own package tree, its planning/implementation-artifact trees, and the shared bookkeeping paths every hand-authored entry already repeats) that the two scope-check call sites fall back to ONLY when no `[epic_surfaces]` entry is declared for the epic; an existing declared entry is never touched, widened, or merged with the default.

## Boundaries & Constraints

**Always:**
- The auto-derived default is substituted only when `effective.epic_surfaces.value.get(str(epic))` returns `None` (no key declared). `_valid_epic_surfaces` never produces an empty-tuple value, so `None` unambiguously means "nothing declared."
- `core/gate.py::compute_effective_surface`'s body, and its AST meta-test enforcing intersection-only (`tests/unit/test_scope.py`), stay byte-for-byte unmodified — the fallback resolves `policy_surface` BEFORE it reaches that combinator, never inside it.
- The default is a pure function of `project_slug` alone (no filesystem I/O, no existence check) — mirrors `core/policy.py::_base_worktree_seed_paths`'s precedent (FR-50): generated, never a hardcoded project name.
- Both call sites — `cli/gate.py`'s `_run_scope_check` and `dispatch_verify.py`'s `evaluate_dispatch_verification` — share one function; no duplicated literal path list.

**Block If:** none — investigation resolved the two open design questions (see Design Notes).

**Never:**
- Never widen or merge with an already-declared `[epic_surfaces]` entry — declared always wins outright, exactly as today (AD-27 asymmetry).
- Never touch `MRS-GATE-008`/frozen-surface handling, `spec_surface` resolution (`core/spec_surface.py`), or CAP-17's enforcement-mode work (Story 28.15) — out of scope.
- Never remove the `"28"` stopgap wildcard from `marshal-policy.toml` in this story — the operational note in epics.md says 28.14 ships the mechanism the stopgap will later be replaced by; removing the stopgap is a separate follow-up, not this story's AC.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No entry, in-station file | epic has no `[epic_surfaces]` key; changed file under `src/shared/packages/<slug>/**` | `MRS-GATE-007` does not fire for that path | No error |
| No entry, bookkeeping path | changed file is `pixi.toml`, `.gitignore`, `pixi.lock`, `environment.yaml`, or `scripts/.spec-surface-baseline.json` | `MRS-GATE-007` does not fire | No error |
| No entry, cross-station file | same zero-entry state; changed file under a DIFFERENT station's package tree or any other repo path | `MRS-GATE-007` fires | No error |
| Declared entry present | `[epic_surfaces]."<epic>"` has an explicit (narrower) list | Behavior identical to today — declared list used; auto-derived default never consulted | No error |
| spec_surface narrows further | policy_surface (declared or auto-derived) intersected with a story spec's `surface:` field | Intersection unaffected by this story — still `compute_effective_surface`'s unchanged `set & set` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py:347` -- add `_COMMON_BOOKKEEPING_PATHS` constant + `default_epic_surface(project_slug: str) -> tuple[str, ...]` pure function (package tree + `planning-artifacts/specs/**` [NARROWED, review pass 1 -- not the full `planning-artifacts/**` tree] + `implementation-artifacts/**` unscoped + bookkeeping) directly above `compute_effective_surface`; same module already owns the AD-27 surface domain.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` (same file, review pass 1) -- ALSO add `resolve_policy_surface(epic_surfaces: Mapping[str, tuple[str, ...]], epic: int, project_slug: str) -> tuple[str, ...]`: returns the declared entry outright when present, else `default_epic_surface(project_slug)`. This is the single home for the "declared wins, else fallback" branching -- both call sites call this, not just the literal default tuple.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py:596` -- `policy_surface = effective.epic_surfaces.value.get(str(story_key.epic), ())` is the deny-all default to replace with `policy_surface = gate.resolve_policy_surface(effective.epic_surfaces.value, story_key.epic, project_slug)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py:181` -- identical `.get(str(story_key.epic), ())` call inside `evaluate_dispatch_verification`; same `gate.resolve_policy_surface(...)` call, not a re-implemented `None`-check.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py:1365` -- `_base_worktree_seed_paths(project_slug)` is the precedent to mirror (pure, slug-generated, no hardcoded names); not itself modified.
- `src/shared/packages/pyforge-marshal/tests/unit/test_scope.py` -- AD-27 surface-domain test home; add `default_epic_surface` AND `resolve_policy_surface` unit tests here.
- `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py:2034-2061` -- `test_gate_evaluate_scope_check_unconfigured_epic_flags_every_changed_file` pins today's deny-all `policy_surface == []`; must update to the new auto-derived value plus two new sibling cases (see Tasks).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py:144-172` -- `test_evaluate_dispatch_verification_runs_gates_not_self_report` already uses `project_slug="pyforge-marshal"` with a changed file inside `src/shared/packages/pyforge-marshal/**` and zero declared `epic_surfaces`, but never asserts `MRS-GATE-007`'s absence; extend it. ALSO (review pass 1) add two DEDICATED new tests at this call site (outside-default-still-denied, declared-entry-still-wins) mirroring the `test_cli.py` coverage -- do not rely on one incidental assertion alone.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:107` -- the `"28"` station-wide-wildcard stopgap this story's mechanism replaces (not removed by this story — see Never).

## Tasks & Acceptance

**Execution:**
- `core/gate.py` -- add `_COMMON_BOOKKEEPING_PATHS = (".gitignore", "pixi.toml", "pixi.lock", "environment.yaml", "scripts/.spec-surface-baseline.json")` and `default_epic_surface(project_slug)` returning the station's `src/shared/packages/{slug}/**`, `_bmad-output/projects/{slug}/planning-artifacts/specs/**` (NARROWED, review pass 1), `_bmad-output/projects/{slug}/implementation-artifacts/**`, plus the bookkeeping tuple.
- `core/gate.py` (review pass 1) -- ALSO add `resolve_policy_surface(epic_surfaces, epic, project_slug)`: `declared = epic_surfaces.get(str(epic))`; return `declared` if not `None`, else `default_epic_surface(project_slug)`. Single canonical home for BOTH the path list and the "declared wins" branching.
- `cli/gate.py:596` -- replace the `.get(..., ())` line with `policy_surface = gate.resolve_policy_surface(effective.epic_surfaces.value, story_key.epic, project_slug)`.
- `dispatch_verify.py:181` -- same one-line call at this second call site.
- `tests/unit/test_scope.py` -- add tests asserting `default_epic_surface`'s exact returned tuple for a sample slug (now `.../planning-artifacts/specs/**`, not the full tree) and that it depends on nothing but the slug argument; add tests for `resolve_policy_surface` covering both branches (declared value returned outright; `None` falls back to `default_epic_surface`).
- `tests/unit/test_cli.py` -- update the existing unconfigured-epic test's docstring and its `policy_surface`/`effective_surface` assertions to the new (narrowed) auto-derived tuple for slug `"acme"` (the existing changed path `"recipes/anything/recipe.yaml"` still falls outside the derived default, so `MRS-GATE-007` still fires there); add one new test where the changed file matches the auto-derived default (e.g. `"pixi.toml"`) with zero declared entries and `MRS-GATE-007` does NOT fire; add one new test confirming a DECLARED narrower `[epic_surfaces]` entry still behaves exactly as today (default never consulted even though it would have permitted the same file).
- `tests/unit/test_dispatch_verification.py` -- extend `test_evaluate_dispatch_verification_runs_gates_not_self_report` with an explicit assertion that no finding in `envelope.findings` carries code `"MRS-GATE-007"`. ALSO (review pass 1) add two NEW dedicated tests calling `evaluate_dispatch_verification` directly: one with zero declared `epic_surfaces` and a changed file OUTSIDE the auto-derived default (assert `MRS-GATE-007` present); one with a DECLARED `[epic_surfaces]` entry and a changed file the auto-derived default would have permitted but the declared entry does not (assert `MRS-GATE-007` present, i.e. declared wins outright). ALSO add one test (either `test_cli.py` or `test_dispatch_verification.py`) with a changed file under `implementation-artifacts/**` and zero declared entries, asserting `MRS-GATE-007` absent -- the `implementation-artifacts/**` default component must be proven end-to-end, not just pinned as a tuple value in `test_scope.py`.

**Acceptance Criteria:**
- Given a station with zero `[epic_surfaces]` entry for the active epic, when a changed file sits under that station's own package tree, its `planning-artifacts/specs/**` or `implementation-artifacts/**` trees, or one of the five bookkeeping paths, then `MRS-GATE-007` does not fire for that path, in both `marshal gate evaluate --scope-check` and dispatch-time verification.
- Given the same zero-entry state, when a changed file sits under a different station's package tree, under `planning-artifacts/` but OUTSIDE `planning-artifacts/specs/**` (e.g. `marshal-policy.toml`, `epics.md`), or any other unlisted repo path, then `MRS-GATE-007` still fires for that path.
- Given a project with an existing `[epic_surfaces]."<epic>"` entry, when scope check runs, then behavior is unchanged from today — the auto-derived default is never consulted or merged in, at BOTH call sites.
- Given the AD-27 meta-test guarding `compute_effective_surface`'s intersection-only body, when this story's changes land, then that meta-test still passes unmodified.

## Spec Change Log

### 2026-08-31 — bad_spec amendment (review pass 1)

**Triggering findings:** four independent review layers converged on: (1) the Design Notes' choice to auto-derive the FULL `planning-artifacts/**` tree is broader than the only concrete precedent in this repo — `marshal-policy.toml`'s own `"22"`/`"28"` `[epic_surfaces]` entries scope planning-artifact access to `planning-artifacts/specs/**` specifically, while granting `implementation-artifacts/**` unscoped. The full-tree default lets an unconfigured epic silently edit its own project's governance files (`marshal-policy.toml` itself, `epics.md`, `PRD.md`, `sprint-status-ledger.yaml`) with zero operator opt-in. (2) `dispatch_verify.py`'s copy of the declared-vs-default fallback had no dedicated test proving a file outside the default still fails there, or that a declared entry still wins there — both already pinned for `cli/gate.py`'s copy. (3) No end-to-end test exercised the `implementation-artifacts/**` default component through either call site. (4) The "declared wins outright, else fall back to the default" branching was duplicated verbatim across both call sites, not just the literal path tuple. (5) `default_epic_surface`'s docstring inaccurately claimed `_valid_epic_surfaces` never yields an empty tuple.

**What was amended:** Design Notes' resolution of "what the default covers" narrowed from the full `planning-artifacts/**` tree to `planning-artifacts/specs/**` (implementation-artifacts stays full-tree, matching the precedent's own asymmetric scoping). Code Map and Tasks amended to: extract the "declared wins, else fallback" branching into one shared `core/gate.py::resolve_policy_surface` function (not just the literal `default_epic_surface` tuple) so both call sites share the single copy; add dedicated `evaluate_dispatch_verification`-level tests for outside-default-still-denied and declared-entry-still-wins; add one scope-check-level test with a changed file under `implementation-artifacts/**`; correct the docstring's factual claim about `_valid_epic_surfaces` during re-derivation.

**Known-bad state avoided:** an unconfigured epic silently gaining write access to its own project's policy/governance files via the "safe default"; a regression on the `dispatch_verify.py` fallback path shipping undetected since only `cli/gate.py`'s copy had dedicated coverage; the `implementation-artifacts/**` component of the default never being proven to actually suppress `MRS-GATE-007` end-to-end; future drift between the two call sites' copies of the same safety-relevant branching logic.

**KEEP instructions (preserve on re-derivation):** the overall mechanism shape — a pure, `project_slug`-derived `core/gate.py` function, consulted only when `effective.epic_surfaces.value.get(str(epic))` returns `None` — is correct and must survive unchanged. `_COMMON_BOOKKEEPING_PATHS` (the 5 literal paths) is correct and unchanged. The `src/shared/packages/{slug}/**` package-tree component is correct and unchanged. The `implementation-artifacts/**` full-tree component is correct and unchanged — only `planning-artifacts` narrows to its `specs/**` subtree. `compute_effective_surface`, `check_scope`, and `core/spec_surface.py` stay untouched, exactly as before. The existing test files' patterns (`_write_epic_surfaces_policy`, `_FakeVcs`, `FakeProcess`, the three new `test_cli.py` cases' scenarios, the three new `test_scope.py` cases) are the right shape — extend and adjust their expected values, don't discard the approach.

## Review Triage Log

### 2026-08-31 — Review pass
- intent_gap: 0
- bad_spec: 5: (high 2, medium 2, low 1)
- patch: 0
- defer: 4: (high 0, medium 1, low 3)
- reject: 2: (low 2)
- addressed_findings:
  - `[high]` `[bad_spec]` Auto-derived default granted the full `planning-artifacts/**` tree (governance files incl. `marshal-policy.toml`/`epics.md`/`PRD.md`) instead of matching the live precedent's `planning-artifacts/specs/**` scoping — amended Design Notes/Code Map/Tasks to narrow it.
  - `[high]` `[bad_spec]` `dispatch_verify.py`'s fallback copy had no dedicated outside-default/declared-wins tests, unlike `cli/gate.py`'s copy — amended Tasks to require them at that call site directly.
  - `[medium]` `[bad_spec]` No end-to-end test proved the `implementation-artifacts/**` default component actually suppresses `MRS-GATE-007` — amended Tasks to add one.
  - `[medium]` `[bad_spec]` Declared-vs-default branching (not just the path list) was duplicated verbatim across both call sites — amended Code Map/Tasks to extract one shared resolver function.
  - `[low]` `[bad_spec]` `default_epic_surface`'s docstring inaccurately claimed `_valid_epic_surfaces` never yields an empty tuple — amended for correction on re-derivation.

### 2026-08-31 — Review pass (pass 2, post re-derivation)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 2, low 2)
- defer: 0 (severity of one existing deferred item raised medium -> high; one existing deferred item's evidence extended; one new deferred item added — no new triage-category defer this pass, only frontmatter updates to already-deferred items)
- reject: 6: (low 6)
- addressed_findings:
  - `[low]` `[patch]` `test_default_epic_surface_does_not_grant_the_full_planning_artifacts_tree`'s second assertion was vacuous (wrong suffix pattern, never matched either the correct or regressed value) — removed; the first assertion already does the real check.
  - `[low]` `[patch]` `default_epic_surface`'s docstring overstated that both call sites validate `project_slug` upfront — corrected to note only `cli/gate.py` does.
  - `[high]` `[patch]` No end-to-end test proved the exact pass-1 regression stays fixed (a `planning-artifacts/` path outside `specs/**`, e.g. `marshal-policy.toml`, must still trip `MRS-GATE-007`) — added `test_gate_evaluate_scope_check_unconfigured_epic_denies_planning_artifacts_outside_specs`.
  - `[medium]` `[patch]` No test proved the AC's own "different station's package tree" negative-case example — added `test_gate_evaluate_scope_check_unconfigured_epic_denies_a_different_stations_package_tree`.
  - `[medium]` `[patch]` `dispatch_verify.py`'s tests never varied `project_slug`, so a hardcoded-literal regression would ship undetected — added `test_evaluate_dispatch_verification_threads_the_real_project_slug_into_the_resolver` using a different slug.

## Design Notes

Three design questions had no single unambiguous answer in the epics.md AC text alone and were resolved from corroborating sources rather than left open:

- **What the default covers (AMENDED, review pass 1).** `epics.md`'s AC prose names only "the station's own package tree and the common bookkeeping paths." `SPEC.md`'s CAP-16 intent additionally includes "its planning/implementation-artifact trees" — but the ONLY concrete precedent for how wide that should be, `marshal-policy.toml`'s own live `"22"`/`"28"` `[epic_surfaces]` entries, scopes planning-artifact access to `planning-artifacts/specs/**` specifically (plus a short explicit file list for exceptions like the policy file itself), while granting `implementation-artifacts/**` unscoped. A first draft of this spec granted the FULL `planning-artifacts/**` tree, which review found lets an unconfigured epic silently edit its own project's governance files (`marshal-policy.toml`, `epics.md`, `PRD.md`, `sprint-status-ledger.yaml`, gate reports) with zero operator opt-in — broader than the precedent it claimed to follow. **Corrected:** the default covers `_bmad-output/projects/{slug}/planning-artifacts/specs/**` (not the full `planning-artifacts/**` tree) plus `_bmad-output/projects/{slug}/implementation-artifacts/**` (unscoped, matching the precedent) plus the package tree and bookkeeping paths.
- **Where the fallback lives.** `core/policy.py::compose()` has no epic number to key against, so the default cannot be baked into `EffectivePolicy.epic_surfaces` itself the way `_base_worktree_seed_paths` feeds `worktree_seed_paths`. The fallback is therefore a plain function in `core/gate.py` (the AD-27 surface domain), called from both impure call sites after `compose()` returns — not a change to policy composition.
- **One shared resolver, not just one shared path list (AMENDED, review pass 1).** The "declared value wins outright, else fall back to the auto-derived default" branching is itself safety-relevant (it is what preserves AD-27's asymmetry), so it belongs in `core/gate.py` as its own function — e.g. `resolve_policy_surface(epic_surfaces: Mapping[str, tuple[str, ...]], epic: int, project_slug: str) -> tuple[str, ...]` — called identically by both `cli/gate.py::_run_scope_check` and `dispatch_verify.py::evaluate_dispatch_verification`, rather than each call site re-implementing the `None`-check itself around a shared `default_epic_surface`.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including the new/updated cases in `test_scope.py`, `test_cli.py`, and `test_dispatch_verification.py`.

## Auto Run Result

**Summary:** `policy_surface` resolution now auto-derives a safe per-station default (package tree + `planning-artifacts/specs/**` + `implementation-artifacts/**` + 5 bookkeeping paths) at both scope-check call sites whenever an epic has no `[epic_surfaces]` entry declared, via a single shared `core/gate.py::resolve_policy_surface` resolver. A declared entry, even an empty one, is always used outright and never merged with or widened by the default. Went through one bad_spec loopback (review pass 1): the first implementation auto-derived the FULL `planning-artifacts/**` tree, which review found broader than the only concrete repo precedent and let an unconfigured epic silently touch its own project's governance files; the spec was amended and code re-derived to narrow to `planning-artifacts/specs/**`. A second review pass (pass 2) found and fixed 5 smaller patch-level gaps in the re-derived code/tests.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- added `_COMMON_BOOKKEEPING_PATHS`, `default_epic_surface(project_slug)`, `resolve_policy_surface(epic_surfaces, epic, project_slug)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py` -- `_run_scope_check` calls `gate.resolve_policy_surface(...)` instead of the old deny-all `.get(..., ())`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- `evaluate_dispatch_verification` calls the same shared resolver.
- `src/shared/packages/pyforge-marshal/tests/unit/test_scope.py` -- unit tests for `default_epic_surface`/`resolve_policy_surface`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` -- updated the deny-all pin to the new default; added permits-a-bookkeeping-path, permits-implementation-artifacts, declared-wins, denies-planning-artifacts-outside-specs, and denies-a-different-stations-package-tree tests.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` -- extended the existing gates-not-self-report test with an `MRS-GATE-007`-absent assertion; added outside-default-denied, declared-wins, and slug-threading tests.
- This spec file itself (bad_spec amendment + two review-triage-log entries + deferred-work catalog).

**Review findings breakdown:**
- Review pass 1: 5 bad_spec (amended spec, reverted+re-derived code), 4 defer (recorded in frontmatter `deferred:`), 2 reject.
- Review pass 2: 5 patch (all applied — 1 high, 2 medium, 2 low), 0 defer as a fresh triage category (one existing deferred item's severity raised medium->high, one extended, one new deferred item added as frontmatter-only updates), 6 reject.
- Total across both passes: 0 intent_gap, 5 bad_spec (resolved via loopback), 5 patch (applied), 5 deferred items recorded in frontmatter, 8 rejected as noise/duplicate/out-of-workflow-scope.

**Follow-up review recommendation:** `true`. This pass's patch findings: 1 high, 2 medium, 2 low -- a high-severity patched finding alone triggers `true` (also exceeds the `3*medium + 1*low >= 5` threshold: 3*2+1*2=8).

**Verification performed:** `pixi run -e pyforge-marshal pyforge-marshal-test` run independently by the orchestrating session (not just self-reported by the implementation subagent) after both the initial implementation and the pass-2 patch round: 6768 passed, 12 deselected (`@pytest.mark.slow`), 0 failures. Matrix Test Audit: all 5 I/O-matrix rows plus the amended implementation-artifacts requirement covered by passing, non-skipped tests. Diffs for every changed file were read and manually cross-checked against the spec's Code Map/Tasks after each round, not just trusted from subagent self-reports.

**Residual risks:** 5 items recorded in frontmatter `deferred:` — (1, high) `compute_effective_surface`'s literal-string intersection likely defeats the auto-derived default whenever a story's own spec declares a `surface:` field (every populated example in this repo uses literal paths); (2, low) the default silently collapses to near-empty for a non-PyForge-Guild project slug with no diagnostic; (3, low) `dispatch_verify.py`'s `project_slug` has no shape validation before flowing into the resolver (pre-existing trust boundary); (4, low) the live `"22"`/`"28"` `[epic_surfaces]` stopgap entries are intentionally left in place with no deferred-work-ledger entry tracking their eventual removal; (5, low) `dispatch_verify.py`'s JSON payload doesn't expose `policy_surface` separately from `effective_surface`, a minor operator-observability gap. None block this story's own AC.
