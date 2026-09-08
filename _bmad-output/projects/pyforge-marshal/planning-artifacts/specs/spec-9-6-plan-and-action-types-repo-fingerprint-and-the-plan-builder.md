---
title: 'Story 9.6: Plan and Action types, repo fingerprint, and the plan builder'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '523e938c79783d06d72030afdb92932d3d02f62f'
final_revision: 'b949353f81'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
difficulty: 'heavy'
---

<intent-contract>

## Intent

**Problem:** Detect (S-9.1--9.5) can classify every manifest entry against a target repo, but
nothing yet turns that classification into the single artifact a human reviews before Genesis
writes anything -- there is no ordered, serializable list of proposed changes with a rationale
and a tamper-evident snapshot of the repo state it was computed against.

**Approach:** Add `Plan`/`Action`/`RepoFingerprint` (`seed/plan/types.py`) plus `build_plan()`
(`seed/plan/build.py`) that maps each non-conformant, non-legacy `Classification` to one
`Action` -- resolving anchors for `hybrid-managed-region` entries and a git-HEAD + dirty +
content-hash `repo_fingerprint` -- and reads/writes it losslessly to `.marshal/plan.json`.

## Boundaries & Constraints

**Always:**
- `build_plan(manifest: Manifest, inventory: Inventory) -> Plan` (`inventory.repo_root` supplies
  the target repo -- no separate `repo_root` parameter).
- One `Action` per `Classification` whose `state` is `ArtifactState.ABSENT` or
  `PRESENT_DIVERGENT`; `PRESENT_CONFORMANT` and `PRESENT_LEGACY` never produce an `Action`
  (AD-59/AD-60 -- a `referenced` entry is always `PRESENT_CONFORMANT` per `classify()`, so it
  never reaches this rule either).
- `Action` fields (P-05 + epics AC, verbatim): `artifact_id: str`, `artifact_class: ArtifactClass`,
  `current_state: ArtifactState`, `target_state: ArtifactState` (always `PRESENT_CONFORMANT` for
  every `Action` this story ever builds -- typed as the full enum, not narrowed, so a future
  target state is not a breaking change), `target_path: str` (`entry.path`, verbatim),
  `chosen_anchor: tuple[tuple[str, str | None], ...]`, `rationale: str`.
- `chosen_anchor`: one `(region_name, matched_anchor)` pair per declared region on a
  `hybrid-managed-region` entry that needs inserting this run (missing when the entry is
  `PRESENT_DIVERGENT`, or every declared region when `ABSENT`) -- `matched_anchor` is
  `AnchorResolution.matched` (`regions/parse.py::resolve_anchor`, `None` = EOF-append fallback).
  Empty tuple `()` for every non-hybrid class and for a hybrid entry needing no insertion. Pairs,
  not a bare positional tuple, so a human reviewing the plan JSON does not have to cross-reference
  the manifest to know which region an anchor belongs to (P-05's own "human reviewing a change"
  framing).
- Anchor resolution reads the target file's CURRENT text (`""` for `ABSENT`) and calls
  `regions.parse.resolve_anchor(text, entry.format, region.anchor)` per missing region; catches
  `RegionParseError`/`MarkerError`/`NotImplementedError` the same way `_classify_hybrid` already
  does, degrading to `chosen_anchor=()` for that entry (never propagating) when the file cannot be
  safely re-parsed.
- `RepoFingerprint` fields: `git_head: str | None` (`git rev-parse HEAD`'s stdout, stripped; `None`
  on a non-zero exit -- no commits yet, or not a git repo), `dirty: bool` (`git status --porcelain
  --untracked-files=normal` producing any output = `True`; a non-zero exit -- can't confirm clean --
  also defaults `True`, the conservative direction), `artifact_hashes: tuple[tuple[str, str], ...]`
  -- one `(artifact_id, detect.hashes.hash_content(current_text))` pair per artifact THIS plan's
  `actions` name (not the whole manifest), sorted by `artifact_id`; `current_text` is `""` for an
  absent or unreadable target (matches the anchor-resolution fallback above).
- Both git calls run via `pyforge.core.process.PosixProcess().run([...], cwd=inventory.repo_root)`
  -- the one sanctioned subprocess seam (Story 14.4), the same package `fs.py` already imports
  `atomic_write_bytes` from (see Design Notes) -- never a raw `subprocess` call, never
  `pyforge.marshal.adapters.vcs_git`.
- `Plan.actions` is a tuple sorted by `artifact_id` (the epics AC's own determinism requirement --
  two `build_plan()` calls against identical repo state produce byte-identical `plan.json`).
- `Plan(actions=(), repo_fingerprint=...)` is a fully valid, constructible, serializable result
  (AD-60) -- no special-casing anywhere in `types.py`/`build.py` for an empty-actions plan.
- Every dataclass (`Action`, `RepoFingerprint`, `Plan`) is `frozen=True`, matching every other
  model type in this package, and defines `to_json_dict(self) -> dict` by hand (never
  `dataclasses.asdict`) plus a `from_json_dict(cls, data: dict) -> Self` classmethod --
  `types.py`'s round-trip loader is this package's first (no prior `from_json_dict` precedent to
  follow beyond `to_json_dict`'s own fixed-key-order convention, `detect/findings.py::Finding`).
- `write_plan(plan: Plan, path: Path) -> None` writes `json.dumps(plan.to_json_dict(), indent=2)`
  via `pyforge.core.atomic_write.atomic_write_bytes`, creating `path.parent` if missing.
  `load_plan(path: Path) -> Plan` reads + `json.loads` + `Plan.from_json_dict`.
  `default_plan_path(repo_root: Path) -> Path` returns `repo_root / ".marshal" / "plan.json"`
  (already covered by the packaged `.gitignore` region's `model-ignores.gitignore.j2` --
  confirmed present, not added by this story).
- `Plan.from_json_dict(json.loads(json.dumps(plan.to_json_dict()))) == plan` holds for every
  `Plan` `build_plan()` can produce, including the empty-actions case.

**Block If:** None. The two implementation decisions this story makes without precedent (which
subprocess seam to call for git; `chosen_anchor`'s pair-tuple shape for multi-region entries) are
each resolved above and justified in Design Notes against existing code, not left open.

**Never:**
- No consumption of `detect.hashes.check_managed_file`/`check_managed_region` -- both require a
  `recorded_sha` from `.marshal/seed-state.yml`, which no story has built yet (`seed/state/` is an
  empty stub). `current_state`/`target_state` are `classify()`'s own STRUCTURAL `ArtifactState`
  values, never a hash-comparison outcome (P-07's boundary; matches `detect/inventory.py`'s own
  Never list).
- No `.marshal/seed-state.yml` read of any kind.
- No CLI wiring: no `--plan-out` flag, no `cli/seed.py` changes. `build_plan`/`write_plan`/
  `load_plan`/`default_plan_path` are library functions only -- a later verb/CLI story wires them.
- No `apply` integration and no fingerprint-based refusal logic ("apply refuses a plan whose
  fingerprint no longer matches," AD-57) -- this story only RECORDS `repo_fingerprint`; checking it
  is a future `apply` story (Epic 10).
- No new import-linter contract for `plan/`'s own import surface -- none is required by this
  story's AC.
- No reconciliation of `coverage_findings()`'s manifest-only view against `Inventory`
  (`DW-FU-9-5`'s open question) -- out of this story's bounded scope, already filed for a future
  architecture-level story.
- No `manifest.never_write` pattern re-matching in the builder beyond the `PRESENT_LEGACY` skip
  `classify()`/`effective_never_write()` already compute -- `fs.py`'s own guard is the
  defense-in-depth backstop at actual write time (a later story); not duplicated here.
- No change to `seed/detect/*.py`, `seed/model/manifest.py`, `seed/regions/*.py`, or `seed/fs.py`
  -- reference only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Absent whole-file entry | `copied-managed` entry, target path missing | one `Action`: `current_state=ABSENT`, `target_state=PRESENT_CONFORMANT`, `chosen_anchor=()`, rationale names materialization | No error |
| Absent hybrid entry, 2 declared regions | `hybrid-managed-region` entry, target file missing | one `Action`: `current_state=ABSENT`, `chosen_anchor` has one pair per declared region, resolved against `""` | No error |
| Present-divergent hybrid, 1 of 2 regions missing | region A found, region B missing | one `Action`: `current_state=PRESENT_DIVERGENT`, `chosen_anchor` has exactly one pair, for region B | No error |
| Present-conformant entry | matches manifest expectations | no `Action` emitted | No error |
| Present-legacy entry | `entry.legacy_of` set, classified `present-legacy` | no `Action` emitted regardless of manifest state | No error |
| Referenced entry | `artifact_class=referenced` | always `present-conformant` per `classify()`; never gets an `Action` | No error |
| Unparseable hybrid file | present-divergent via an unterminated fence (`RegionParseError` at classify time) | `Action` emitted with `current_state=PRESENT_DIVERGENT`, `chosen_anchor=()` (best-effort skipped) | No error (caught, degrades) |
| Empty plan | every entry present-conformant or present-legacy | `Plan(actions=(), repo_fingerprint=...)` -- valid, serializable, round-trips | No error |
| Non-git target repo | `git rev-parse HEAD` exits non-zero | `repo_fingerprint.git_head is None`, `dirty=True` | No error (`PosixProcess` never raises on non-zero exit) |
| Round-trip | any built `Plan` | `Plan.from_json_dict(json.loads(json.dumps(plan.to_json_dict()))) == plan` | No error |
| Malformed `plan.json` | hand-corrupted JSON (missing key, bad enum value) | `load_plan` raises `ValueError` naming the problem | `ValueError` |
| Two runs, same repo state | `build_plan` called twice, nothing changed between | identical `Plan.actions`/`repo_fingerprint.artifact_hashes` tuples (serialized bytes identical) | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/types.py` -- NEW: `Action`,
  `RepoFingerprint`, `Plan` frozen dataclasses + `to_json_dict`/`from_json_dict`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/build.py` -- NEW: `build_plan()`,
  `write_plan()`, `load_plan()`, `default_plan_path()`.
- `.../seed/detect/inventory.py` -- reference only: `Inventory`, `Classification`, `ArtifactState`,
  `effective_never_write()`.
- `.../seed/detect/hashes.py` -- reference only: `hash_content()`.
- `.../seed/model/manifest.py` -- reference only: `Manifest`, `ManifestEntry`, `ArtifactClass`,
  `Region`.
- `.../seed/regions/parse.py` -- reference only: `resolve_anchor()`, `parse_regions()`,
  `RegionParseError`, `AnchorResolution`.
- `.../seed/regions/markers.py` -- reference only: `MarkerError`.
- `pyforge.core.process` -- reference only: `PosixProcess`, `ProcessError` -- new dependency for
  `plan/build.py` (precedented: `fs.py` already imports `pyforge.core.atomic_write`).
- `pyforge.core.atomic_write` -- reference only: `atomic_write_bytes`, reused by `write_plan`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_types.py` -- NEW.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_build.py` -- NEW.

## Tasks & Acceptance

**Execution:**
- [x] `seed/plan/types.py` -- define `Action`/`RepoFingerprint`/`Plan` frozen dataclasses with
  `to_json_dict`/`from_json_dict` -- gives the plan a stable, hand-rolled JSON shape matching
  `Finding.to_json_dict`'s existing convention.
- [x] `seed/plan/build.py` -- `build_plan(manifest, inventory) -> Plan`: map each qualifying
  `Classification` to one `Action`, sorted by `artifact_id`.
- [x] same file -- resolve `chosen_anchor` for `hybrid-managed-region` entries via
  `regions.parse.resolve_anchor`, one pair per currently-missing declared region.
- [x] same file -- compute `repo_fingerprint` via `pyforge.core.process.PosixProcess` (git HEAD +
  dirty) plus `detect.hashes.hash_content()` over each actioned artifact's current text.
- [x] same file -- `write_plan()`/`load_plan()`/`default_plan_path()`: atomic write to
  `.marshal/plan.json` by default, `ValueError` on malformed JSON at load.
- [x] `tests/unit/test_seed_plan_types.py` -- cover every I/O Matrix row for the types (round-trip,
  empty plan, tuple-vs-JSON-array conversion, malformed-JSON `ValueError`).
- [x] `tests/unit/test_seed_plan_build.py` -- cover every I/O Matrix row for the builder, including
  one run against the real packaged `templates/manifest.yaml` + a synthetic target repo (mirrors
  S-9.5's own real-manifest regression-test convention).

**Acceptance Criteria:**
- Given a detect `Inventory` over the real packaged manifest and a repo missing every materialized
  artifact, when `build_plan` runs, then every non-`referenced` entry gets exactly one `Action`
  (`current_state=ABSENT`), ordered by `artifact_id`.
- Given a repo that already conforms to every entry, when `build_plan` runs, then
  `Plan.actions == ()` (AD-60's idempotence signal) and the `Plan` is still a fully valid,
  serializable object.
- Given a `Plan`, when it is written via `write_plan` then read back via `load_plan`, then the
  result is field-for-field identical to the original.
- Given no explicit path, when `write_plan`/`default_plan_path` run, then the file lands at
  `<repo_root>/.marshal/plan.json`.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 2: (high 0, medium 1, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: the story's own core deliverable (`RepoFingerprint`, AD-57)
    had zero test coverage of its positive path -- only "not a git repo" was tested, never a real
    git repo returning a real HEAD sha or `dirty` correctly flipping `True`/`False`. Added three
    tests against a real `git init`-ed `tmp_path` (mirrors `test_vcs_git.py`'s own real-git-repo
    convention): clean HEAD + `dirty=False`, a tracked-file edit flipping `dirty=True`, an
    untracked file flipping `dirty=True`.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same finding):
    `build_plan(manifest, inventory)` raised a bare, unnamed `KeyError` when `inventory` was not
    built from `manifest` (a mismatched-pair caller error), inconsistent with every other
    caller-contract violation in this module raising a named `ValueError`. Added an upfront check
    naming every unknown `entry_id`, plus a regression test.
  - `[low]` `[patch]` Edge Case Hunter: `PosixProcess.run`'s two git calls carried no `timeout_s`
    (defaults to unbounded), so a hung `git` process would block `build_plan` forever. Added
    `_GIT_TIMEOUT_S = 30.0`, matching `adapters/vcs_git.py::_GIT_TIMEOUT_S`'s identical value for
    the identical class of query-style call.
  - `[low]` `[patch]` Blind Hunter: `write_plan`'s `json.dumps` used the stdlib default
    `ensure_ascii=True`, escaping any non-ASCII manifest-derived path/rationale/anchor text to
    `\uXXXX` in `plan.json` -- undercutting P-04's "human reviews this artifact" framing for
    zero benefit (escape sequences round-trip identically either way). Added `ensure_ascii=False`
    plus a regression test.
  - `[low]` `[patch]` Edge Case Hunter: `Plan.from_json_dict` (this module's stated boundary
    against untrusted/hand-corrupted `plan.json` input) never validated the `actions` list's own
    stated invariant -- unique, ascending-by-`artifact_id` order -- so a corrupted file with
    duplicate or out-of-order ids loaded silently. Added two checks (uniqueness, then order) plus
    two regression tests.
  - `[low]` `[patch]` Edge Case Hunter: `load_plan`'s docstring read as promising `ValueError` for
    any failure including a missing/unreadable file, which would contradict `fs.py`'s own
    established "never wraps a generic `OSError`" convention this function actually follows
    (`read_text` failures propagate unchanged). Tightened the docstring's scope to "malformed JSON
    content" and named the file-access exception explicitly; no behavior change.
  - `[defer]` Blind Hunter: `git rev-parse HEAD`/`git status` run with `cwd=repo_root` and no
    `--show-toplevel`-style boundary check -- if `repo_root` is a subdirectory of an ENCLOSING git
    checkout rather than a repo root of its own, both calls report the ancestor repository's
    HEAD/dirty state instead of "not a git repo," mislabeling the fingerprint. Real and
    architecturally significant (a future `apply` story trusts this fingerprint for refusal
    logic, AD-57), but `errors.py` already earmarks "target is not a git repo" as a
    `PreconditionFailure` a later `seed/verbs/` story checks -- the nested-repo variant of that
    same boundary question belongs there, not in this story's plan-building surface. Filed
    `DW-FU-9-6`.
  - `[defer]` Blind Hunter: writing `plan.json` under `repo_root` (a future verb's job, not this
    story's) before the model's own `.gitignore` region has been materialized into the target repo
    would make the freshly-written `plan.json` itself appear as an untracked file, flipping
    `dirty=True` on a subsequent `build_plan` call even though nothing "real" changed. Real, but
    the write-order sequencing between materializing `.gitignore` and writing `plan.json` is a
    future `apply`/verb story's concern (this story's own Never bullet: no `apply` integration).
    Filed `DW-FU-9-6-2`.
  - `[reject]` Blind Hunter: claimed `seed/plan/__init__.py` was missing from the diff. Verified
    false -- it already exists (Story 7.1's pre-existing empty stub, unchanged and correctly absent
    from this diff since this story never touched it).
  - `[reject]` Blind Hunter: a missing `git` executable makes `build_plan` raise an uncaught
    `ProcessError`. The module's own docstring already documents this as a deliberate choice ("a
    host misconfiguration, not an ordinary 'not a git repo' outcome"), and `errors.py` earmarks
    graceful precondition handling for a later `seed/verbs/` story -- not a gap this diff
    introduced.
  - `[reject]` Blind Hunter: `_chosen_anchor` re-parses region structure for a `PRESENT_DIVERGENT`
    hybrid entry even though `classify()` already parsed it once. Architecturally necessary. not
    avoidable within this story's surface -- `Inventory` (reference-only, S-9.2/9.4) does not
    retain parsed spans, so there is nothing to reuse without changing `detect/inventory.py`,
    which this story's Never list explicitly forbids.
  - `[reject]` Blind Hunter: `Action`/`RepoFingerprint`/`Plan` carry no `__post_init__` validation.
    Directly matches this spec's own explicit Always-bullet design choice ("each is a well-typed
    COMPUTED shape... `from_json_dict` is where untrusted input is checked") -- spec-compliant by
    design, not a gap.
  - `[reject]` Blind Hunter: `_rationale`/`_chosen_anchor` branch on `ArtifactState.ABSENT` with an
    implicit "else must be `PRESENT_DIVERGENT`," no defensive `else: raise`. Theoretical --
    `_ACTIONABLE_STATES` is a two-member `frozenset` literal defined a few lines above both
    functions in the same file; matches this package's own repeated precedent (e.g. S-9.5's
    review log) for rejecting same-file, no-real-trigger-path hypotheticals.
  - `[reject]` Blind Hunter: `EXPECTED_NON_REFERENCED_ENTRY_COUNT`/`EXPECTED_HYBRID_REGION_COUNTS`
    hard-code exact counts against the real packaged manifest, "brittle" to a future manifest
    edit. This is the deliberate feature, not a defect -- directly mirrors S-9.5's own
    `EXPECTED_CLASS_COUNTS` convention, whose explicit purpose is forcing a conscious update (CI
    catching drift), not avoiding one.
  - `[reject]` Blind Hunter: `default_plan_path`'s docstring claim that `.marshal/plan.json` is
    already covered by the packaged `.gitignore` region is "unverifiable from the diff alone."
    Independently verified true (`templates/files/model-ignores.gitignore.j2` lists it) during
    this story's own spec-authoring investigation -- a reviewer information-asymmetry artifact,
    not a real defect.
  - `[reject]` Edge Case Hunter: a TOCTOU window between `_current_text`'s file reads and the
    later git HEAD/dirty calls could see an inconsistent, non-atomic view of the repo. Matches
    `fs.py`'s own explicit, already-established threat model ("a local CLI operating on a repo its
    own operator already controls, not a sandbox defending against a co-located adversarial
    process racing the filesystem") -- no real blast radius under this tool's stated threat model.
  - `[reject]` Edge Case Hunter: `entry.format`'s `assert entry.format is not None` narrowing
    would silently pass `None` through if run under `python -O` (asserts stripped). Matches an
    identical, already-accepted pattern in `detect/inventory.py::_classify_hybrid` (same
    assertion, same justification) -- not a new risk this diff introduces, and `-O` is not a mode
    this project runs under anywhere.
  - `[reject]` Edge Case Hunter: duplicate `manifest.entries` ids could make `entries_by_id`'s dict
    comprehension silently drop an earlier entry. Verified already prevented one layer up:
    `Manifest.__post_init__` (`model/manifest.py`) raises `ValueError` on any duplicate entry id
    at construction time -- this module never sees a `Manifest` that could exhibit this.

## Design Notes

**Why `pyforge.core.process.PosixProcess` directly, not `adapters.vcs_git.GitVcs`.**
`GitVcs` is built for bmad-loop worktree provisioning (`ports.vcs.VcsPort`'s much larger surface --
`WorktreeEntry`, worktree creation/teardown); pulling in that whole module for two read-only git
calls would import a different domain's dependency into the seed installer, which sits below
`adapters/` in the architecture's own module-dependency chain (`detect/inventory.py`'s own
docstring: "no subprocess/adapter import ... `detect` sits below `adapters/`"). `pyforge.core`,
by contrast, is already a precedented import for this package's low layers: `fs.py` imports
`pyforge.core.atomic_write.atomic_write_bytes` directly, and its own docstring states its import
surface is "nothing else from either `pyforge.core` or `pyforge.marshal`" -- proving `pyforge.core`
imports are architecturally distinct from, and permitted where, `pyforge.marshal.adapters` imports
are not. `plan/build.py` follows that exact precedent for `pyforge.core.process`.

**Why `chosen_anchor` is `tuple[tuple[str, str | None], ...]`, not a bare `str | None`.**
A `hybrid-managed-region` entry can declare more than one region (the packaged manifest's
`agents-md` entry declares 3; `claude-md` declares 2), and a single scalar anchor field cannot
represent "two regions were both missing, each resolved against a different anchor" without
silently dropping one. Pairing `(region_name, matched_anchor)` keeps the field fully general
(matches `entry.regions`'s own `tuple[Region, ...]` cardinality) and legible to a human reviewing
the plan without cross-referencing the manifest to know which anchor belongs to which region --
directly serving the epics AC's own framing ("As a human reviewing a change before it happens").

**Why `repo_fingerprint.artifact_hashes` only covers actioned artifacts, not the whole manifest.**
AD-57 frames the fingerprint's purpose as letting `apply` "refuse a plan whose fingerprint no
longer matches" -- i.e. detect drift between plan-build time and apply time for exactly the
artifacts THIS plan intends to touch. Hashing all 40+ manifest entries regardless of whether they
have a pending action would not serve that purpose and would make an empty plan's fingerprint
needlessly expensive to compute.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Added `Action`/`RepoFingerprint`/`Plan` frozen dataclasses (`seed/plan/types.py`) with
hand-rolled `to_json_dict`/`from_json_dict` round-trip codecs, and `build_plan()`/`write_plan()`/
`load_plan()`/`default_plan_path()` (`seed/plan/build.py`) that map a `detect.inventory.classify()`
result into the single, reviewable, serializable `Plan` artifact FR-82/P-04/P-05 call for -- one
`Action` per non-conformant, non-legacy manifest entry, with resolved anchors for
`hybrid-managed-region` entries and a git-HEAD + dirty + per-artifact-content-hash
`repo_fingerprint` (AD-57). This worktree recovered nine prerequisite Epic 8/9 stories (marker
grammar, region parsing/substitution/anchoring, findings model, inventory classification, content
hashing, legacy detection, coverage check) from a preserved branch
(`attempt-preserve/20260813-094919-bfcb-523e938c`) via a clean fast-forward merge before this
story's own implementation began -- zero conflicts, zero data loss, no re-implementation.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/types.py` -- NEW: `Action`,
  `RepoFingerprint`, `Plan`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/build.py` -- NEW:
  `build_plan`, `write_plan`, `load_plan`, `default_plan_path`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_types.py` -- NEW: 36 tests.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_build.py` -- NEW: 39 tests
  (including a real-packaged-`manifest.yaml` regression test, mirroring S-9.5's convention).

**Review findings breakdown:** 19 distinct findings after dedup (Blind Hunter + Edge Case Hunter,
parallel, no shared context) -- 7 patches applied (1 medium: the story's own core deliverable,
`RepoFingerprint`, had zero positive-path test coverage -- added three real-git-repo tests; 6 low:
a bare `KeyError` on a manifest/inventory mismatch replaced with a named `ValueError`, an unbounded
git subprocess call given a 30s timeout matching `vcs_git.py`'s own precedent, `write_plan` given
`ensure_ascii=False` for human-readable non-ASCII content, `Plan.from_json_dict` now rejects a
corrupted plan's duplicate/out-of-order `artifact_id` values, `load_plan`'s docstring tightened to
not overpromise `ValueError` for file-access failures), 2 deferred (`DW-FU-9-6`: a nested-target-repo
git boundary gap belonging to a future `seed/verbs/` precondition-check story; `DW-FU-9-6-2`: a
write-order self-referential fragility between materializing `.gitignore` and writing `plan.json`,
belonging to a future `apply`/verb story), 10 rejected (one factually-false claim, several
spec-compliant-by-design findings that directly re-litigated this story's own explicit Always
bullets, and several theoretical no-blast-radius concerns matching this package's own repeatedly
established rejection precedent). 0 intent gaps, 0 bad-spec loopbacks.

**Follow-up review recommendation:** `false`. All 7 patches are small, independently justified
against existing precedent (`vcs_git.py`'s timeout constant, `fs.py`'s error-wrapping convention,
the module's own stated untrusted-data boundary), verified by new passing tests, and do not touch
architecture, security-sensitive logic, or any other story's surface.

**Verification performed:** `pixi run -e pyforge-marshal pyforge-marshal-test` -- 4076 passed, 9
deselected, 0 failures (up from the 4004 pre-implementation baseline: 65 tests from the initial
implementation pass + 7 tests added during the review-patch pass, 72 new tests total, zero
regressions). `ruff check` on all four changed/new files -- 6 remaining findings, all the
pre-existing `TRY004` (ValueError-vs-TypeError) pattern already present and un-remediated
throughout this package's own shipped `seed/` modules, matching this story's own explicit spec
design choice (plain `ValueError` for caller-contract violations, not the `SeedError` taxonomy).
Independently re-verified every `Tasks & Acceptance` checkbox and Acceptance Criterion against the
actual code and a fresh local test run (not just the implementation subagent's own report) before
proceeding to review.

**Residual risks:** None blocking. `DW-FU-9-6` and `DW-FU-9-6-2` are real, out-of-scope
architectural questions correctly belonging to future stories (a `seed/verbs/` precondition check,
and the future `apply` story's write-order sequencing), not defects in this diff.
