---
title: 'Story 9.2: Repo inventory walker and artifact classification'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '95f1db76aa7682c9365576fdf8cd92ae9918ecc8'
final_revision: '8a2fcdb7971c2b48be886f3c92e2d40405205e99'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 9's detect stage has a manifest loader (S-7.4), a region parser (S-8.2), and a
findings model (S-9.1), but nothing yet answers "what does this manifest entry actually look
like in the target repo right now" -- the fact every later plan/finding/hash story needs.

**Approach:** Add `seed/detect/inventory.py`: a pure `classify(manifest, repo_root) -> Inventory`
that walks the target repo once (pruning `.git`/`node_modules`/`.pixi` and root-`.gitignore`
matches), then classifies each manifest entry as `absent` / `present-conformant` /
`present-divergent` / `present-legacy` using only structural signals available today --
file/dir presence, and for `hybrid-managed-region` entries, whether S-8.2's `parse_regions`
finds every declared region.

## Boundaries & Constraints

**Always:**
- `ArtifactState(StrEnum)` defines all four epics-AC members verbatim: `ABSENT = "absent"`,
  `PRESENT_CONFORMANT = "present-conformant"`, `PRESENT_DIVERGENT = "present-divergent"`,
  `PRESENT_LEGACY = "present-legacy"` -- kebab-case wire values, matching `ArtifactClass`/
  `FindingType`'s established convention. All four are declared now even though this story's own
  logic never emits `PRESENT_LEGACY` (see Never) -- S-9.3/S-9.4 build against the same enum
  rather than redefining it (mirrors S-9.1's own "type exists before every member has a real call
  site" precedent).
- `Classification` (`@dataclass(frozen=True)`: `entry_id: str`, `state: ArtifactState`) and
  `Inventory` (`@dataclass(frozen=True)`: `repo_root: Path`, `tree: frozenset[str]`,
  `classifications: tuple[Classification, ...]`) are the module's public shape. `tree` is every
  walked, non-excluded regular file's path, POSIX-separated and relative to `repo_root`. This is
  the "walked once, cached" structure the epics AC requires: `classify()` performs exactly one
  walk per call, and a caller (a later verb) invokes it once and reuses the returned `Inventory`
  for both plan building and finding emission.
- Walk exclusions, applied while walking (pruned, never descended into): a directory named
  `.git`, `node_modules`, or `.pixi` at any depth, plus every path matched by the **repo-root**
  `.gitignore` (hand-rolled `gitwildmatch`-subset matcher -- see Never for the exact grammar
  scope; no new dependency, matching `model/version.py`'s explicit "no SemVer library" precedent
  for the identical class of decision).
- An artifact's own declared `entry.path` is **always** checked directly against the live
  filesystem regardless of the exclusion rules above (the epics AC's "unless an artifact
  explicitly targets them" carve-out) -- exclusions only shrink `Inventory.tree`, they never hide
  a manifest-named path from classification.
- Classification rules, per `entry.artifact_class`:
  - `REFERENCED`: always `PRESENT_CONFORMANT` -- per `model/artifact.py`'s own
    `CLASS_BEHAVIOR["referenced"]`, it is "not materialized," so there is nothing in the repo
    tree for this walker to inspect; FR-95 checks the dependency floor elsewhere (`marshal seed
    update`), not here.
  - Any other class: `ABSENT` iff `repo_root / entry.path` does not exist.
  - `HYBRID_MANAGED_REGION`, path exists: read the file as UTF-8 and run S-8.2's
    `parse_regions(text, entry.format)`. `PRESENT_CONFORMANT` iff every `entry.regions[].name` is
    found among the returned spans. `PRESENT_DIVERGENT` if any declared region is missing, the
    path exists but is not a regular file, the read is not valid UTF-8, or `parse_regions` raises
    `RegionParseError`/`MarkerError` -- all four are "present but not what the manifest expects,"
    matching the PRD's own J2 worked example ("`CLAUDE.md` -- will insert a managed region at an
    anchor").
  - Every other present class (`copied-managed`, `copied-seeded`, `generated-derived`):
    `PRESENT_CONFORMANT` -- content-hash divergence is S-9.3's own layer (Deps: S-9.2), not
    checked here.
- `classify()` performs reads only: no writes, no subprocess, no network -- verified by running
  it against a `tmp_path` fixture `chmod`-ed to `0o555` (this package's established
  write-blocking-fixture idiom, matching S-8.2/S-9.1's own purity tests).

**Block If:** None -- the epics AC, FR-80, P-03, and the PRD's own J2 worked example fully
specify the four-state classification; no decision here requires human input.

**Never:**
- No content-hash comparison anywhere in this module (P-07: hash guards belong to detect's
  *hashing* layer, S-9.3, never earlier) -- a present whole-file artifact is always optimistically
  `PRESENT_CONFORMANT` here, regardless of its actual byte content.
- No `legacy_of` handling -- `PRESENT_LEGACY` is a declared enum member with no producing code
  path in this story. Per the epic's own Cross-Story-Dependencies note, "Story 9.4 extends 9.2's
  classifier with the legacy-successor manifest field"; adding that branch now would pre-empt
  9.4's own Surface (`seed/detect/inventory.py`, `seed/detect/findings.py`).
- No `.marshal/seed-state.yml` read of any kind -- this story has no state-store dependency
  (Deps: S-7.4, S-8.2, S-9.1 only); "detect works on a repo missing `.marshal/` entirely" holds
  vacuously because detect never looks for it.
- No `Finding` construction or emission -- this module returns classifications only; translating
  them into `Finding`s is a later story's job.
- No nested, per-directory `.gitignore` files -- V1 consults the repo-root `.gitignore` only.
  Real git's negation semantics interacting with nested-file precedence is out of this story's
  bounded scope; a target repo's root `.gitignore` is the common case this package's own repo
  (and the PRD's worked examples) exercise.
- No `pathspec`, `git ls-files`, or any subprocess/adapter import -- `detect` sits below
  `adapters/` in the module-dependency chain (architecture § Module dependency rules: `detect`
  reaches only `model`/`state`/`regions`/`engine`/`derive`), so this module stays stdlib-only,
  matching every sibling `detect/`/`regions/`/`model/` module in this package.
- No directory-shaped whole-file artifacts get special walking logic beyond `Path.exists()` --
  a present directory is present; nothing in this story's own AC asks for recursive content
  comparison of a directory artifact (S-9.3 is file/region-body hashing, not directory diffing).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Absent whole-file | `copied-managed` entry, path missing | `ABSENT` | No error |
| Present whole-file | `copied-seeded` entry, path exists | `PRESENT_CONFORMANT` | No error |
| Referenced | `referenced` entry, any repo state | `PRESENT_CONFORMANT` | No error |
| Hybrid, file absent | `hybrid-managed-region` entry, path missing | `ABSENT` | No error |
| Hybrid, region found | file exists, declared region present via `parse_regions` | `PRESENT_CONFORMANT` | No error |
| Hybrid, region missing | file exists, declared region absent from `parse_regions` result | `PRESENT_DIVERGENT` | No error |
| Hybrid, multi-region partial | 2 declared regions, only 1 found | `PRESENT_DIVERGENT` | No error |
| Hybrid, malformed markers | file exists, `parse_regions` raises `RegionParseError` | `PRESENT_DIVERGENT` | No error (caught, not propagated) |
| Hybrid, path is a directory | `entry.path` resolves to a dir, not a file | `PRESENT_DIVERGENT` | No error |
| Hybrid, non-UTF-8 content | file exists, invalid UTF-8 bytes | `PRESENT_DIVERGENT` | No error (caught, not propagated) |
| Excluded-dir carve-out | entry path under a gitignored dir | classified by real presence, not forced `ABSENT` | No error |
| Tree exclusion | unnamed file under `.git`/`node_modules`/`.pixi` | absent from `Inventory.tree` | No error |
| Gitignore negation | `.gitignore` has `*.log` then `!keep.log` | `keep.log` present in `tree`, other `*.log` excluded | No error |
| Nested gitignore not consulted | a subdirectory's own `.gitignore` ignores `x`, root does not | `x` still present in `tree` | No error |
| Purity | `classify()` against a `0o555` tmp_path tree | returns normally, no write attempted | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` -- NEW,
  this story's Surface: `ArtifactState`, `Classification`, `Inventory`, `classify`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- NEW, covers
  the I/O Matrix.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- reference
  only: `Manifest`, `ManifestEntry`, `ArtifactClass` consumed as input.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- reference
  only: `parse_regions`, `RegionParseError` consumed for hybrid classification.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- reference
  only: `MarkerError`, `RegionFormat` propagate/consume unchanged.

## Tasks & Acceptance

**Execution:**
- [x] `seed/detect/inventory.py` -- add `ArtifactState(StrEnum)` (4 members), `Classification` and
  `Inventory` frozen dataclasses -- the classification output shape S-9.3/9.4/9.5/9.6 consume.
- [x] same file -- add a private hand-rolled gitignore matcher (root-`.gitignore` only: comments,
  blank lines, `!` negation, trailing-`/` dir-only, leading-`/` anchoring, `*`/`?`/`**` glob
  translation) and `_walk_tree(repo_root) -> frozenset[str]`, pruning `.git`/`node_modules`/
  `.pixi` by name at any depth plus gitignore matches.
- [x] same file -- add `classify(manifest, repo_root) -> Inventory`: per-entry dispatch on
  `artifact_class` per the Always rules above, using `_walk_tree`'s result plus a direct
  `entry.path` existence check for the explicit-target carve-out.
- [x] `tests/unit/test_seed_detect_inventory.py` -- cover every I/O Matrix row plus the purity
  (`chmod 0o555`) assertion.

**Acceptance Criteria:**
- Given a manifest and a target repo, when `classify` runs, then every entry is classified
  `absent`, `present-conformant`, `present-divergent`, or `present-legacy`.
- Given a `tmp_path` repo tree with all permissions removed, when `classify` runs against it,
  then it completes without raising a permission error and performs no write.
- Given a repo with `.git/`, `node_modules/`, `.pixi/`, or a root-`.gitignore`-matched path not
  named by any manifest entry, when `classify` runs, then `Inventory.tree` excludes it.
- Given a manifest entry whose own `path` falls inside an otherwise-excluded directory, when
  `classify` runs, then that entry is still classified by its real on-disk state.
- Given a manifest with zero entries, when `classify` runs on any repo, then it returns an
  `Inventory` with an empty `classifications` tuple and no error.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 3, medium 2, low 3)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter (confirmed live): a legally-constructible
    `hybrid-managed-region` entry declaring `format: slashstar` reached
    `markers.parse_marker_line`'s bare `NotImplementedError`, uncaught by
    `_classify_hybrid`'s `(RegionParseError, MarkerError)` except clause --
    crashed `classify()` for the ENTIRE manifest on one reserved-format
    entry instead of degrading that one entry to `present-divergent` like
    every sibling error path. Added `NotImplementedError` to the caught
    tuple, plus a regression test.
  - `[high]` `[patch]` Blind Hunter (confirmed live, read a real file
    outside the target repo): `repo_root / entry.path` silently discards
    `repo_root` when `entry.path` is absolute (documented `pathlib`
    behavior), and `ManifestEntry.__post_init__` does not reject an
    absolute or `../`-traversing path -- `classify()` could read an
    arbitrary host path instead of anything under the target repo. Added
    `_resolve_within_repo`, which resolves and contains the path, treating
    an escape as `absent`, never dereferenced; two regression tests
    (absolute and traversal).
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently,
    confirmed live): `_classify_hybrid`'s `target.read_text(...)` only
    caught `UnicodeDecodeError`, so a present-but-unreadable file
    (permission bits, a race after `is_file()`) raised `OSError`/
    `PermissionError` uncaught -- inconsistent with the sibling
    `_load_gitignore_rules` read's own `(OSError, UnicodeDecodeError)`
    handling. Matched it; added a `chmod 0o000` regression test.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently,
    confirmed live): a trailing `**` gitignore segment (`build/**` -- a
    common real-world idiom, and the exact shape this repo's own root
    `.gitignore` uses in `!src/**/packages/*/**`) compiled to a regex
    requiring the matched string to end in a literal `/`, which no walked
    file path ever carries -- silently matched nothing at all.
    `_translate_pattern_to_regex` now special-cases a trailing `**` as an
    unconditional `.*`, distinct from a leading/middle `**`'s optional
    `(?:.*/)?`; added a regression test.
  - `[medium]` `[patch]` Blind Hunter (confirmed live): anchoring checked
    only for a LEADING `/`, but real gitignore anchors on ANY `/` before
    the pattern's end -- this repo's own `.idea/**/workspace.xml` pattern
    incorrectly matched at any depth (`sub/.idea/workspace.xml`), which a
    root `.gitignore` would never exclude in real git. Changed to
    `anchored = "/" in pattern_body`; added a regression test. (Fixing this
    surfaced one NEW ruff finding, `FURB188`, from the resulting
    conditional-slice shape -- fixed in the same pass with
    `str.removeprefix()`.)
  - `[low]` `[patch]` Blind Hunter: the other half of `_classify_hybrid`'s
    except clause, `MarkerError`, had zero test coverage (only
    `RegionParseError` was exercised). Added a regression test using a
    line with a malformed sha field.
  - `[low]` `[patch]` Blind Hunter: the "`.git`/`node_modules`/`.pixi`
    pruned at any depth" claim was untested beyond depth 1. Added a
    parametrized test nesting each excluded dir two levels deep.
  - `[low]` `[patch]` Blind Hunter: `Inventory`'s hashability was untested,
    asymmetric with `Classification`'s own hashability test. Added
    `test_inventory_is_hashable`.

### 2026-08-13 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 0, low 4)
- defer: 0
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter (confirmed live against this repo's
    own root `.gitignore`): `_translate_segment_to_regex`'s blanket
    `re.escape` never translated a gitignore bracket expression (`[abc]`,
    `[a-z]`, `[!abc]`/`[^abc]` negated) into a regex character class --
    this repo's own `.gitignore` uses bracket expressions extensively
    (`*.py[cod]`, `[Dd]ebug/`, `[Ww][Ii][Nn]32/`, dozens more), and every
    one of those patterns silently matched nothing at all
    (`_translate_pattern_to_regex('*.py[cod]', anchored=False)` did not
    match `foo.pyc`), so real gitignore-excluded paths leaked into
    `Inventory.tree`. Rewrote `_translate_segment_to_regex` as a
    character-by-character translator with bracket-class support;
    re-verified live against this repo's actual `.gitignore` post-fix.
    Added regression tests for a plain and a negated bracket class.
  - `[low]` `[patch]` Blind Hunter: `_resolve_within_repo` re-resolved
    `repo_root.resolve()` on every manifest entry instead of once per
    `classify()` call, against the module's own "walk once, cache it"
    ethos. Hoisted to `classify()`, threaded through as `resolved_root`.
  - `[low]` `[patch]` Blind Hunter: no test proved a whole-file class
    (`copied-managed`) pointed at a directory is `present-conformant` (the
    module docstring's own claim, previously proven only for the
    hybrid-managed-region case). Added
    `test_whole_file_entry_whose_path_is_a_directory_is_present_conformant`.
  - `[low]` `[patch]` Blind Hunter: no test proved a symlink inside
    `repo_root` pointing outside it hits the same `_resolve_within_repo`
    containment guard as a hand-crafted absolute/`../` manifest path (a
    more realistic real-world escape vector; already correctly handled by
    `Path.resolve()`'s own symlink-following, but untested). Added
    `test_entry_path_through_a_symlink_escaping_repo_root_is_absent`.
  - `[low]` `[patch]` Blind Hunter: no test proved a `.gitignore`
    containing only comments/blank lines degrades to "nothing excluded"
    (a different code branch than a missing `.gitignore`: the read
    succeeds but every line is filtered out). Added
    `test_gitignore_with_only_comments_and_blank_lines_excludes_nothing`.
  - `[reject]` Edge Case Hunter: `entry.format is None` reaching
    `_classify_hybrid`'s `assert` -- verified against
    `model/manifest.py:331-332`, `ManifestEntry.__post_init__`
    unconditionally raises `ValueError` for any hybrid-managed-region
    entry with a falsy `format`, at every construction site; the assert is
    the same established type-narrowing convention already used at
    `cli/init.py:887`. Unreachable.
  - `[reject]` Blind Hunter: `_classify_hybrid` on a hybrid entry with zero
    declared `regions` as vacuously `present-conformant` -- verified
    against `model/manifest.py:345-346`, `ManifestEntry.__post_init__`
    requires at least one region for every hybrid-managed-region entry.
    Unreachable.
  - `[reject]` Edge Case Hunter: `os.walk`'s default `onerror=None`
    silently skips a permission-denied subdirectory during the walk --
    real, but consistent with this module's own established
    graceful-degradation posture for every other unreadable input (e.g.
    `_load_gitignore_rules`), and nothing downstream consumes
    `Inventory.tree` yet to be affected by it.
  - `[reject]` Blind Hunter: `ArtifactState.PRESENT_LEGACY` has zero
    producing call sites in this story -- already explicitly justified in
    the module docstring, matches `FindingType`'s own established
    precedent, and is spec-mandated (`<intent-contract>` Always bullet).
  - `[reject]` Blind Hunter: the module docstring cites architecture/PRD
    IDs and the memlog entry cites verification numbers not independently
    checkable from the diff alone -- documentation/log prose, not a code
    defect.
  - `[reject]` Blind Hunter + Edge Case Hunter (4 gitignore-grammar edge
    cases, deduplicated to one line): backslash-escaped `#`/`!`/mid-pattern
    special characters, a malformed `foo**bar` double-star segment (real
    git itself declares this undefined), leading-whitespace-only trimming,
    and a double-leading-slash `//foo` pattern -- grepped this repo's own
    `.gitignore` for all four shapes (zero matches); unproven/hypothetical
    against a hand-rolled matcher the module's own docstring already
    scopes as a bounded "subset," not full gitwildmatch fidelity.

## Design Notes

**Why classification does not read `.marshal/seed-state.yml`.** The epics AC's "detect works on
a repo missing `.marshal/` entirely" reads, on first sight, as if detect must handle a *present*
state file too -- but this story's own `**Deps:**` line (S-7.4, S-8.2, S-9.1) names no
state-store story, and architecture's directory tree still shows `state/store.py` unbuilt. The
requirement holds vacuously: detect that never looks for `.marshal/` trivially "works" on a repo
that lacks it. S-9.3's own AC (the one story that actually reasons about "absent from state") is
where a real state input enters the pipeline.

**Why hybrid divergence is structural, not hash-based, in this story.** The PRD's J2 walkthrough
names `CLAUDE.md` as `present-divergent` with the resolution "will insert a managed region at an
anchor" -- i.e. the file exists but the *region itself* is missing, discoverable purely from
`parse_regions`'s return value, with no byte-content comparison at all. That is exactly the
signal S-8.2 already provides, and exactly why 9.2 depends on S-8.2 rather than only S-7.4.

**Why the gitignore matcher is hand-rolled instead of a new `pathspec` dependency.** Directly
mirrors `model/version.py`'s own documented precedent: "pulling in a real SemVer package for ~80
lines of grammar is exactly the kind of speculative dependency Simplicity First forbids." A
root-only `gitwildmatch` subset (no nested-file precedence to get right) is comparably bounded,
and `detect`'s own layering rule already forbids the one dependency-free alternative
(shelling out to `git`, which lives in `adapters/vcs_git.py`, unreachable from `detect`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new test file.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect 0 broken contracts.
- `python scripts/spec_surface_reconcile.py` -- expect `OK` after the memlog entry lands.

## Auto Run Result

Status: `done`

**Summary.** Added `seed/detect/inventory.py`: a pure `classify(manifest, repo_root) -> Inventory`
that walks the target repo once (pruning `.git`/`node_modules`/`.pixi` at any depth plus a
hand-rolled root-`.gitignore` matcher, no new dependency) and classifies every manifest entry
structurally -- `absent`/`present-conformant`/`present-divergent`/`present-legacy` (the last
declared, not yet produced -- S-9.4's job). Hybrid-managed-region entries classify via S-8.2's
`parse_regions`; every other present class is optimistically conformant (content-hash divergence
is S-9.3's layer). Two independent review passes (Blind Hunter + Edge Case Hunter each, no shared
context between reviewers or across passes) found and this run fixed 13 real defects total across
both passes, 4 of them crash/security/correctness-relevant, all confirmed live before being
patched; 10 further findings in the second pass verified against actual code invariants and
rejected as unreachable, out-of-scope, or unproven against this repo's own `.gitignore`.

**Files changed (this pass):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` --
  `_translate_segment_to_regex` rewritten to support gitignore bracket character classes
  (`[abc]`, `[!abc]`/`[^abc]`); `_resolve_within_repo`/`_classify_entry`/`classify` now thread a
  single `repo_root.resolve()` instead of re-resolving per manifest entry.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- 5 new
  regression tests (bracket class, negated bracket class, directory-as-whole-file-target,
  symlink escape, comments/blanks-only `.gitignore`); 45 total in the file.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- spec-surface reconciliation entry for this pass.
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to `spec-pyforge-marshal` only.

**Review findings breakdown (this pass):** 5 patched (1 high, 0 medium, 4 low), 0 deferred, 10
rejected. Highlight: a blanket `re.escape` in the gitignore matcher never translated a bracket
character class into a regex character class -- confirmed live against this repo's own root
`.gitignore`, which uses bracket expressions extensively (`*.py[cod]`, `[Dd]ebug/`,
`[Ww][Ii][Nn]32/`, dozens more); every one of those patterns silently excluded nothing, so real
gitignore-excluded paths leaked into `Inventory.tree`. The 10 rejections include 2 findings
disproved against actual construction-time invariants in `model/manifest.py` (a hybrid entry can
never have `format=None` or zero `regions` -- `__post_init__` forbids both unconditionally) and 4
gitignore-grammar edge cases grepped against this repo's real `.gitignore` and found unproven.
Full rationale in the Review Triage Log above and the memlog's own follow-up "Review pass" note.

**Follow-up review recommended: false.** This pass's fixes are small, localized to the same two
files as the prior pass, and independently re-verified against this repo's own live `.gitignore`
data rather than hypothetical input. Combined with the prior pass's already-thorough two-reviewer
coverage, a third independent pass is unlikely to surface further issues of consequence.

**Verification performed:** `pyforge-marshal-test` 3741 passed (9 slow deselected, up from 3736
pre-pass); `ruff check` clean on both changed files, package-wide count unchanged at 186
pre-existing; `pyright` unchanged (`inventory.py` zero, test file's 5 pre-existing
`reportMissingImports` errors, package total 592 same as pre-pass); `lint-imports` clean (3
contracts kept, 0 broken); `python scripts/spec_surface_reconcile.py` reports `OK` after the
memlog entry and baseline re-stamp.

**Residual risks:** The hand-rolled gitignore matcher remains a deliberately bounded "subset" (no
backslash-escape support, no nested `.gitignore`, undefined behavior for malformed `**`
mid-segment usage) -- all explicitly out of this story's declared V1 scope and unproven against
any real target repo encountered so far. `Inventory.tree` still silently under-reports under a
permission-denied subdirectory (`os.walk`'s own default), consistent with every other unreadable
input in this module but not yet exercised by any downstream consumer.

**Verification performed:** `pyforge-marshal-test` 3736 passed (9 slow deselected); `ruff check`
clean on both new files, package-wide count unchanged (186, pre-existing); `pyright` unchanged
(`inventory.py` zero errors; the test file's 5 errors are the same pre-existing
`reportMissingImports` category every sibling test file carries); `lint-imports` 3 contracts kept,
0 broken; `spec_surface_reconcile.py` reports `OK`. All four commands re-run and independently
confirmed after the review-pass patches, not just after the initial implementation.

**Residual risks:** the gitignore matcher is intentionally V1-scoped to the repo-root
`.gitignore` only (no nested per-directory files, an explicit Never boundary) -- correct for
every fixture this story tests, but a real target repo with meaningful nested `.gitignore`
content will under-exclude until a later story extends it. `PRESENT_LEGACY` has no producing code
path yet (by design, S-9.4's job) and non-hybrid present artifacts are optimistically
`present-conformant` with no hash check yet (by design, S-9.3's job) -- both are stated
boundaries, not gaps discovered late.
