---
title: 'Story 9.1: The five hygiene finding classes get testable definitions'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'ee01d715073d32b14759521b1465c00c36b4375e'
final_revision: '405a4dd8b6544011ddacd412816e7b0bfec8659e'
---

<intent-contract>

## Intent

**Problem:** The `bmad-output-hygiene` sweep's five finding classes (dead
test scaffolding, hollow `sprint-status.yaml`, orphan files, README
placeholders, stale Dream statuses) exist only as an ad-hoc, hand-executed
precedent across commits `bfa9fd68`/`1567a478`/`5c5e3727`/`22da995c`/`f7654a4c`
— no written definition states what makes an artifact an instance of each
class. Story 9.2 cannot build a reproducible fleet-wide sweep against an
undefined boundary, and CAP-8's own success bar ("reproduces warden's own 5
finding classes as a fixture") has nothing pinned to reproduce against.

**Approach:** Add a pure, dependency-free `hygiene_definitions` module to
`pyforge.doctor` with one predicate per class, each derived from — and cited
against — the real commit that fixed it, plus fixture-based unit tests
proving each predicate correctly classifies real positive instances (still
on disk under `archive/_bmad-output/projects/...`, since this repo's
archive-don't-delete convention means nothing was deleted) and real/synthetic
negative instances it must not flag.

## Boundaries & Constraints

**Always:**
- Five pure functions, one per class, in a new
  `pyforge/doctor/hygiene_definitions.py` — no filesystem/network I/O of
  their own; every input signal (file content, parsed YAML, booleans) is
  passed in by the caller, so Story 9.2's gather can supply the evidence
  once and call these as the classification layer.
- Each predicate's docstring states, in prose, what makes an artifact an
  instance and what explicitly does not, citing the grounding commit SHA.
- Each predicate is proven in `tests/unit/test_hygiene_definitions.py`
  against at least one real positive fixture and at least one real or
  clearly-labeled-synthetic negative fixture (see I/O matrix).
- The module stays **outside** `pyforge/doctor/sources/` — that package's
  own `test_every_real_sources_file_is_mapped_by_at_least_one_source` meta
  test requires every file there to back a registered `Source`; registering
  one is Story 9.2's wiring job, not this definition-only story's.

**Block If:** any of the five cited commit SHAs does not exist, or its
content contradicts this spec's Design Notes summary of it — the AC's own
grounding source would then be unverifiable and must not be guessed at.

**Never:** no `Source`/`SourceRegistration`/CLI wiring; no repo-wide scan of
all 8 stations; no `--fix`/archive/mutation action (Stories 9.2/9.3). If a
6th distinct hygiene pattern surfaces incidentally while building fixtures,
record it as an observation in Design Notes rather than inventing a 6th
predicate — the epic names exactly five. No new read-only-guard test needed:
`tests/meta/test_read_only_guard.py` already scans every module under
`pyforge.doctor`, including this new one.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dead scaffolding, positive | relpaths under `archive/_bmad-output/projects/pyforge-doctor/tests/` (on disk today: `conftest.py`, seven `__init__.py`-only subpackages, zero `test_*.py`) | `is_dead_test_scaffolding(...)` → `True` | none |
| Dead scaffolding, negative | relpaths under this repo's own `src/shared/packages/pyforge-doctor/tests/` (real `test_*.py` files present, e.g. `unit/test_read_only_guard.py`) | → `False` | none |
| Hollow sprint-status, positive | parsed YAML from `archive/_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status.yaml` (on disk: `completion_percentage: 0%`, `epics: []`, `stories: []`) | `is_hollow_sprint_status(...)` → `True` | none |
| Hollow sprint-status, negative | parsed YAML from the live `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` (real per-story `done`/`in-progress` entries) | → `False` | none |
| README placeholder, positive | literal string `"doctor is a [role] station in the PyForge factory, responsible for [responsibilities]."` (verbatim, `5c5e3727^:_bmad-output/projects/pyforge-doctor/README.md`) | `is_readme_placeholder(...)` → `True` | none |
| README placeholder, negative | this repo's current, live `_bmad-output/projects/pyforge-doctor/README.md` content (real per-station role prose, post-fix) | → `False` | none |
| Stale Dream status, positive | `dream_status="specified"`, `all_station_stories_done=True` (doctor's real state at `bfa9fd68^`: 16/16 stories done, status still `specified`) | `is_stale_dream_status(...)` → `True` | none |
| Stale Dream status, negative (already correct) | `dream_status="realized"`, `all_station_stories_done=True` (atlas's real pre-fix state — never flagged regardless of completion) | → `False` | none |
| Stale Dream status, negative (genuinely mid-flight) | `dream_status="specified"`, `all_station_stories_done=False` (synthetic — logical negation, not a shape edge case) | → `False` | none |
| Orphan file, positive (self-marked shape) | `relpath="RESUME-EPIC-10.md"`, `has_inbound_references=False` (real content on disk at `archive/_bmad-output/projects/pyforge-atlas/RESUME-EPIC-10.md`) | `is_orphan_file(...)` → `True` | none |
| Orphan file, positive (no closure banner, still ad hoc + unreferenced) | `relpath="planning-artifacts/intake-video-scripts-manticore-2026-07-31.md"`, `has_inbound_references=False` (real content on disk at `archive/_bmad-output/projects/pyforge-herald/...`; proves the definition does NOT require a literal "closed" banner, since this fixture has none) | → `True` | none |
| Orphan file, negative (conventional name, unreferenced) | `relpath="planning-artifacts/epics.md"`, `has_inbound_references=False` | → `False` (conventional names are found by directory convention, not inbound reference, so absence of a reference alone is never sufficient) | none |
| Orphan file, negative (non-conventional but referenced) | `relpath="planning-artifacts/NOTES-random.md"`, `has_inbound_references=True` (synthetic) | → `False` | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py` -- NEW. `HygieneFindingKind` (str enum, 5 members) + the 5 predicates below.
- `src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py` -- NEW. One fixture-pair test per I/O matrix row, citing source (on-disk path or commit SHA) in a comment above each fixture.

## Tasks & Acceptance

**Execution:**
- [x] `hygiene_definitions.py` -- add `HygieneFindingKind` enum (`DEAD_TEST_SCAFFOLDING`, `HOLLOW_SPRINT_STATUS`, `ORPHAN_FILE`, `README_PLACEHOLDER`, `STALE_DREAM_STATUS`) -- names the closed set of 5 classes the epic pins.
- [x] `hygiene_definitions.py` -- add `is_dead_test_scaffolding(test_relpaths: Iterable[str]) -> bool` -- `True` iff none of the given relative paths match Python's `test_*.py` discovery glob (only `__init__.py`/`conftest.py`-shaped scaffold present). Docstring cites `22da995c`.
- [x] `hygiene_definitions.py` -- add `is_hollow_sprint_status(parsed_yaml: dict) -> bool` -- `True` iff `parsed_yaml.get("epics") == []` and `parsed_yaml.get("stories") == []` and `parsed_yaml.get("summary", {}).get("completion_percentage") in (0, "0%")`. Docstring cites `f7654a4c` (CAP-2).
- [x] `hygiene_definitions.py` -- add `is_readme_placeholder(content: str) -> bool` -- `True` iff `content` contains the literal substring `[role]` or `[responsibilities]`. Docstring cites `5c5e3727` (CAP-4) and explicitly notes the byte-identical-stub variant CAP-4 also rewrote is OUT of this predicate's scope (CAP-4's own stated success criterion covers only the literal bracket token).
- [x] `hygiene_definitions.py` -- add `is_stale_dream_status(dream_status: str, all_station_stories_done: bool) -> bool` -- `True` iff `dream_status == "specified" and all_station_stories_done`. Docstring cites `bfa9fd68`.
- [x] `hygiene_definitions.py` -- add `is_orphan_file(relpath: str, has_inbound_references: bool) -> bool` -- `True` iff `has_inbound_references` is `False` AND `relpath`'s filename/subdirectory does not match this project's own observed conventional planning-artifact shape (`README.md`, `PROJECTS.md`, `epics.md`, `epics-with-stories.md`, `test-architecture.md`, `sprint-status-ledger.yaml`, `deferred-work-ledger.md`, `marshal-policy.toml`, `implementation-readiness-report-*.md`, `.bmad-config*.toml`, or anything under `prds/`, `architecture/`, `briefs/`, `research/`, `retros/`, `specs/`). Docstring cites `f7654a4c` (CAP-5) for both real fixtures and states plainly that a self-declared "closed" banner is NOT required (the second real fixture has none).
- [x] `tests/unit/test_hygiene_definitions.py` -- one test per I/O matrix row (the table itself has 13 rows, not the 12 this checklist line originally said -- see Auto Run Result), reading real on-disk fixtures where the row cites a path, inlining literal fixture text where the row cites a commit SHA (no `git show` subprocess calls at test time).

**Acceptance Criteria:**
- Given the module as written, when each of the 5 predicates runs against its cited real positive fixture, then it returns `True`.
- Given the module as written, when each predicate runs against its cited real or synthetic negative fixture, then it returns `False`.
- Given `pyforge.doctor`'s existing `tests/meta/test_read_only_guard.py`, when it runs after this change, then `hygiene_definitions.py` is included in its scan and reports zero write call sites (no new guard needed — proves the module needs no exemption).
- Given `pyforge.doctor.sources`'s existing `test_every_real_sources_file_is_mapped_by_at_least_one_source`, when it runs after this change, then it still passes (proves `hygiene_definitions.py` was correctly placed outside `sources/`).

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 4, low 1)
- defer: 0
- reject: 10 (low 10)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter found `is_dead_test_scaffolding`'s docstring overclaims modeling "pytest's own" default discovery glob (pytest's real default also matches `*_test.py`, not just `test_*.py`) and leaves empty-iterable behavior unstated. Fixed: docstring reworded to describe only what the predicate actually checks, grounded in the real fixtures (all of which use `test_*.py` exclusively) — no behavior change, since no real fixture anywhere in this repo uses `*_test.py`.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause) found `is_hollow_sprint_status` raises `AttributeError` on `parsed_yaml=None` (a real `yaml.safe_load` outcome for an empty/whitespace-only file) or when `summary:` is present with a `None` value (`dict.get`'s default only covers an absent key, not a present-but-`None` one). Fixed: both guarded to return `False` rather than crash.
  - `[medium]` `[patch]` Blind Hunter found no test exercises a 2-of-3 partial-match case (a mutation from `and` to `or`, or a dropped clause, would pass undetected) or the numeric-`0` branch of `completion_percentage`'s `in (0, "0%")` check for `is_hollow_sprint_status`. Fixed: added both tests.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found the `_CONVENTIONAL_DIRECTORIES` branch and the `_CONVENTIONAL_FILENAME_GLOBS` branch of `is_orphan_file` were never exercised by any test — real classification logic with zero coverage in a story whose entire purpose is fixture-proven precision. Fixed: added a directory-branch test (`specs/foo.md` → `False`) and a glob-branch test (`implementation-readiness-report-2026-08-15.md` → `False`).
  - `[medium]` `[patch]` Blind Hunter found `_CONVENTIONAL_DIRECTORIES` matches ANY ancestor path component with no anchor to a station's project root, so an unrelated file anywhere under a directory literally named e.g. `specs`/`research` would be silently exempted from orphan detection regardless of whether it is really a BMAD planning artifact. Fixed: docstring now states the precondition explicitly — `relpath` must already be relative to a station's `_bmad-output/projects/<slug>/` root, never repo-root-relative — so Story 9.2's gather cannot misuse it.
  - `[low]` `[reject]` Blind Hunter found `_require_repo_root()`'s `parents[6]` depth assumption could resolve to the wrong ancestor if this test file is ever relocated. Rejected, not deferred: this is a pre-existing idiom shared verbatim by 5 other sibling test files in this same package (`test_check_speed_budget.py`, `test_checks_env_hygiene.py`, `test_sources_board_dashboard_drift.py`, `test_sources_board_check_layout.py`, `test_sources_chain_deferred_work.py`), already using the guarded (try/except `IndexError`) variant one of those siblings' own history shows was already hardened once before — an already-accepted, low-probability convention, not a new or actionable risk this story introduced.
  - `[low]` `[reject]` Blind Hunter found `fnmatch.fnmatch` is case-sensitive on POSIX but case-insensitive on Windows. Rejected: this factory's entire deployment target is Linux/pixi CI; no cross-platform requirement exists anywhere in this codebase's conventions.
  - `[low]` `[reject]` Blind Hunter found `is_readme_placeholder` would false-positive on prose merely discussing the literal `[role]` token (e.g. this module's own docstring) and has no case-insensitivity. Rejected: the predicate is only ever called against station README content, never against this module's own source; no real fixture across any of the 9 stations shows case variance.
  - `[low]` `[reject]` Blind Hunter found inconsistent fixture-existence-guarding style across the new tests (some assert `.is_file()` first, others don't). Rejected: an unguarded missing fixture already raises a clear, path-naming `FileNotFoundError` either way — not a silent or confusing failure.
  - `[low]` `[reject]` Blind Hunter found `HygieneFindingKind`'s five members have no test asserting correspondence to the five `is_*` predicate names. Rejected: the enum has zero programmatic coupling to the predicates in this definition-only story (Story 9.2 is their first consumer); a correspondence test today would just restate two independently hand-typed literals.
  - `[low]` `[reject]` Blind Hunter found the docstring's claim about CAP-4's "byte-identical-stub variant" is unverifiable from this diff alone. Rejected: the claim is accurate per this story's own research (`git show 5c5e3727`, the 6 identical 3-line `planning-artifacts/README.md` stubs) — correctly scoped as historical citation, not a behavior this predicate claims to test.
  - `[low]` `[reject]` Edge Case Hunter found an empty `relpath` (`""`) classifies `is_orphan_file` as `True`. Rejected: no real caller (Story 9.2's future repo walk) would ever pass a degenerate empty path; not worth defensive code against an input that cannot occur.
  - `[low]` `[reject]` Edge Case Hunter found `epics`/`stories` keys being entirely absent (vs. explicit `[]`) is an untested implicit branch for `is_hollow_sprint_status`. Rejected: already handled correctly (`dict.get` on a missing key returns `None`, and `None == []` is `False`) — a coverage note, not a defect.

## Design Notes

**Division of labor with Story 9.2.** These predicates take pre-computed
signals (`has_inbound_references`, `all_station_stories_done`, parsed YAML)
rather than doing repo-wide gathering themselves. Computing "does anything
else in the repo reference this path" or "are all of a station's stories
done" requires scanning far beyond one artifact — that's Story 9.2's gather
implementation. This story's job is only the classification boundary: given
the evidence, is this an instance of the class or not.

**Orphan file's conventional-name set is grounded in this project's own
`planning-artifacts/` listing** (`ls _bmad-output/projects/pyforge-doctor/planning-artifacts/`,
2026-08-15): `architecture/`, `briefs/`, `deferred-work-ledger.md`,
`epics.md`, `epics-with-stories.md`, `implementation-readiness-report-*.md`,
`marshal-policy.toml`, `prds/`, `README.md`, `research/`, `retros/`,
`specs/`, `sprint-status-ledger.yaml`, `test-architecture.md` — plus the
fleet-wide `PROJECTS.md`. A file matching none of these shapes is a
candidate; `has_inbound_references=False` confirms it.

**The "self-marked closed" framing in `f7654a4c`'s own commit message is
looser than the mechanical predicate below it.** `RESUME-EPIC-10.md`
literally banners "✅ CLOSED"; the herald intake file has no such banner at
all (verified: `grep -in "closed\|retired" archive/.../intake-video-scripts-manticore-2026-07-31.md`
returns nothing) — its own signal is only "Status: bmad-spec INPUT, not a
Spec... Preserved near-verbatim," i.e. a one-time consumed draft. Since
`is_orphan_file` must classify both real fixtures correctly, it does NOT
require a closure banner — only non-conventional-name + zero inbound
references. This is a deliberate, evidence-driven narrowing versus the
commit message's own paraphrase, not an oversight.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Added `pyforge/doctor/hygiene_definitions.py`, a new,
dependency-free module sibling to `models.py`/`verdict.py`/`prescribe.py`
(outside `sources/` per the Spec's own Boundaries), defining
`HygieneFindingKind` (the closed 5-member enum) and five pure predicates —
`is_dead_test_scaffolding`, `is_hollow_sprint_status`, `is_readme_placeholder`,
`is_stale_dream_status`, `is_orphan_file` — each taking only caller-supplied
evidence (relpaths, parsed YAML, strings, booleans) and each docstring-cited
against the real commit that first fixed a live instance of the class it
names. All five cited SHAs (`bfa9fd68`, `1567a478`, `5c5e3727`, `22da995c`,
`f7654a4c`) were verified to exist and match the Spec's Design Notes summary
before writing any code (`git cat-file -e` + `git show` against the two
commit-cited literal fixtures — the pre-fix README stub and doctor's own
Dream frontmatter at `bfa9fd68^` — both matched verbatim).

One correction to the Spec's own bookkeeping: the I/O & Edge-Case Matrix
table actually has **13 rows**, not the "12" the Tasks checklist's last line
originally said (2 dead-scaffolding + 2 hollow-sprint-status + 2
README-placeholder + 3 stale-Dream-status + 4 orphan-file = 13). The table
itself is the authoritative, read-only part of the intent-contract, so all
13 rows got their own test rather than 12; the checklist line has been
corrected in place to note the discrepancy instead of silently under-testing.

`is_orphan_file`'s conventional-name/directory set was implemented exactly
as the Spec's Design Notes list it (8 exact filenames, 2 filename globs, 6
conventional directory names), and both real orphan fixtures
(`RESUME-EPIC-10.md`'s self-marked "✅ CLOSED" shape and the herald intake
draft's bannerless shape) classify `True` under the same mechanical rule —
confirming the Design Notes' claim that a closure banner is not required.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py` -- NEW. `HygieneFindingKind` + the 5 predicates. Post-review: `is_hollow_sprint_status` guards `None`/non-dict input and a `None`-valued `summary:` key instead of raising; `is_dead_test_scaffolding`'s docstring no longer overclaims modeling pytest's full default discovery; `is_orphan_file`'s docstring states its `relpath`-must-be-station-relative precondition explicitly.
- `src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py` -- NEW. 20 tests: the original 14 (1 per I/O matrix row + 1 pinning the closed 5-member enum) plus 6 added during review (partial-match and numeric-`0` cases + `None`/null-summary crash guards for `is_hollow_sprint_status`; the previously-uncovered conventional-directory and conventional-filename-glob branches of `is_orphan_file`).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated): 0 intent_gap, 0 bad_spec, 5 patch (0 high / 4 medium / 1 low, all applied and re-verified), 0 defer, 10 reject (noise or already-correct behavior, see Review Triage Log for the full per-finding rationale). No loopback needed -- every real finding was a direct, spec-consistent patch.

**Verification performed:**
- `pixi run -e pyforge-doctor pytest tests/unit/test_hygiene_definitions.py -v` (post-patch) -> **20 passed**.
- `pixi run -e pyforge-doctor pyforge-doctor-test` (full suite, post-patch) -> **929 passed, 2 skipped** (same 2 pre-existing/unrelated skips: `playwright` not installed in this env; a gitignored Tier-3 `deferred-work.md` absent in this worktree).
- `ruff check src/pyforge/doctor/hygiene_definitions.py tests/unit/test_hygiene_definitions.py` (run from the package root) -> **all checks passed**.

**Residual risks:** none identified for this definition-only story. The five
predicates have zero production callers yet (Story 9.2 is their first
consumer) -- the same accepted shape Story 8.1's `classify_tier3_entries`
carried into 8.2/8.3. `is_orphan_file`'s conventional-directory/filename set
is a hand-maintained list grounded in a dated `ls` snapshot (2026-08-15,
recorded in both the Spec's Design Notes and this module's own comments);
Story 9.2's gather implementation should keep it in sync if
`planning-artifacts/`'s own shape grows a new conventional file family, and
must pass `is_orphan_file` a station-relative `relpath` per its now-explicit
precondition.

**Manual checks (if no CLI):** none needed -- the pixi test task exercises
every new test directly.
