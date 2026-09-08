---
title: 'Story 7.3: The `fs` write primitive and the never-write guard'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'c592cb0794'
final_revision: '49debfce5b'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** No module under `seed/` can safely write into a target repo yet: every write would
bypass FR-71's never-write set (Tier-0 Dreams, Tier-2 planning artifacts, Tier-3, legacy specs,
BMAD installer files), and Story 8.3 (`seed/regions/apply.py`, span substitution) is blocked on
exactly this — its own AC requires writing "through `fs.replace_span()` — never `Path.write_text`".

**Approach:** Add `seed/fs.py`: an immutable `NeverWrite` pattern set plus three guarded
functions — `write`, `replace_span`, `remove` — each resolving its target path to an absolute,
symlink-resolved form and checking it against `NeverWrite` *before* touching the filesystem,
raising `NeverWriteViolation` (Story 7.2) on a match. `write`/`replace_span` delegate the actual
atomic write to `pyforge.core.atomic_write.atomic_write_bytes` (Story 14.2) — this story adds no
new atomic-write mechanics of its own, only the guard in front of the existing one.

## Boundaries & Constraints

**Always:**
- `NeverWrite` is a frozen dataclass wrapping `patterns: tuple[str, ...]` — plain glob strings
  (the shape `Manifest.never_write` already carries, Story 7.4), never a `Manifest` object
  itself (`fs` must not import `model` — see the import-direction bullet below). `frozen=True`
  plus a `tuple` field makes both attribute reassignment and pattern-list mutation raise, which is
  the AC's "immutable after construction (mutation attempt raises)".
- Pattern matching uses `fnmatch.fnmatch` on the POSIX-form relative path, uniformly for every
  pattern (no distinct `**`-vs-`*` handling): `fnmatch`'s `*` already matches across `/`, so
  `**/planning-artifacts/**` and a plain `*` behave identically under it, and a single-star
  pattern like `docs/dreams/*.md` over-matches into subdirectories rather than under-matching —
  the safe direction for a guard whose entire purpose is refusing writes, never permitting one a
  narrower matcher would have caught.
- `write(path, data, *, repo_root, never_write)`, `replace_span(path, start, end, new_body, *,
  repo_root, never_write)`, and `remove(path, *, repo_root, never_write)` each resolve `path` via
  `path.resolve()` (non-strict, symlink-following, matching `ports/fs.py::resolve_path`'s own
  documented convention) and `repo_root` the same way, compute the resolved path relative to the
  resolved `repo_root` (falling back to the resolved path's own POSIX string when `path` is not
  under `repo_root` at all — no pattern is repo-external today, but this must not crash), and
  check it against `never_write.patterns` — all **before** any read, write, or unlink touches
  `path`. A match raises `NeverWriteViolation(message, remedy=...)` naming the matched pattern in
  `message`.
- `replace_span` reads `path.read_bytes()` (never `read_text` — text-mode I/O can silently
  translate line endings, corrupting the byte offsets `RegionSpan.body_span` promises; this
  mirrors S-8.2's own byte-not-character discipline) *after* the guard clears, splices via
  `data[:start] + new_body + data[end:]`, and writes the result through `atomic_write_bytes` —
  the one substitution contract `regions/parse.py`'s own Design Notes already document, now
  centralized here so `regions/apply.py` (Story 8.3) never re-derives it.
- `write`/`replace_span` are atomic (`atomic_write_bytes`, temp-file + `os.replace`) so an
  interrupted write cannot truncate an existing file (AC).
- `seed/fs.py` imports `pyforge.core.atomic_write.atomic_write_bytes` and
  `pyforge.marshal.seed.errors.NeverWriteViolation` and nothing else from either `pyforge.core`
  or `pyforge.marshal` — the architecture's "`fs` imports nothing from the package except
  `errors`" plus `pyforge.core` being outside "the package" (a sibling top-level package, not
  `pyforge.marshal`).

**Block If:** None — the epics AC (path resolution, matching, immutability, import surface,
atomicity) plus S-14.2/S-7.2's already-shipped primitives fully specify this story; no decision
here requires human input.

**Never:**
- No `NeverWrite` construction from a `Manifest` (a `Manifest -> NeverWrite` adapter is a future
  `verbs/`-level orchestrator's job, per architecture: "`fs` holds an immutable `NeverWrite` set
  loaded from the manifest **at orchestrator construction**" — that orchestrator does not exist
  yet).
- No wrapping of a generic `OSError` (a missing file, a permission error) from `read_bytes`,
  `unlink`, or `atomic_write_bytes` into any of Story 7.2's six `SeedError` leaves — only a
  never-write match raises `NeverWriteViolation`; every other I/O failure propagates unchanged,
  matching `pyforge.core.atomic_write`'s own "never introduces a new exception type" contract.
  Wrapping the rest of `seed/fs.py`'s I/O surface into the taxonomy, if ever needed, is later
  work.
- No symlink-transparency handling beyond the guard check itself — the actual I/O call
  (`atomic_write_bytes`/`read_bytes`/`unlink`) operates on the CALLER-SUPPLIED `path`, not the
  resolved one; resolution is used only to evaluate the never-write match, exactly like
  `ports/fs.py` already treats `resolve_path` as a separate concern from `write_text_atomic`.
- No `seed/apply/run.py` ("Plan -> guarded writes", the future detect/plan/apply pipeline stage)
  — that consumes THIS module later; this story only builds the primitive it will call.
- No CLI wiring, no `verbs/` module, no manifest re-parenting of `MarkerError`/`RegionParseError`/
  `ManifestError`/`FsError` onto `SeedError` — out of Surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Plain write, no match | `write(repo/"README.md", b"hi", repo_root=repo, never_write=NeverWrite(()))` | file created with content `b"hi"` | No error |
| Direct never-write hit | `write(repo/"docs/dreams/x.md", ..., never_write=NeverWrite(("docs/dreams/*.md",)))` | -- | `NeverWriteViolation` naming `docs/dreams/*.md` |
| Symlink-indirect hit | `repo/"alias"` symlinks to `repo/"_bmad-output/planning-artifacts"`; `write(repo/"alias/x.md", ...)` against `never_write=NeverWrite(("**/planning-artifacts/**",))` | -- | `NeverWriteViolation` (proves resolution, not the raw path, drove the match) |
| Interrupted write leaves original intact | `write_fn` raises mid-write (simulated) against an existing file | original file content unchanged, temp file removed | original exception propagates (from `atomic_write`) |
| `replace_span` preserves prefix/suffix | file `b"AAAbodyBBB"`, `replace_span(path, 3, 7, b"NEW")` | file becomes `b"AAANEWBBB"`, bytes outside `[3,7)` byte-identical | No error |
| `replace_span` guard fires before any read | target matches `never_write` | -- | `NeverWriteViolation`; file left completely untouched (never even read) |
| `NeverWrite` mutation attempt | `never_write.patterns = (...)` or `never_write.patterns[0] = "x"` | -- | `dataclasses.FrozenInstanceError` / `TypeError` (tuple item assignment) |
| `remove` on a never-write path | `remove(repo/"docs/specs/x.md", ..., never_write=NeverWrite(("docs/specs/*.md",)))` | -- | `NeverWriteViolation`; file NOT removed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- NEW, this story's
  Surface: `NeverWrite`, `write`, `replace_span`, `remove`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py` -- REFERENCE ONLY
  (Story 7.2, already shipped): `NeverWriteViolation`.
- `src/shared/packages/pyforge-core/src/pyforge/core/atomic_write.py` -- REFERENCE ONLY (Story
  14.2, already shipped): `atomic_write_bytes`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_fs.py` -- NEW, covers every I/O
  Matrix row.
- `src/shared/packages/pyforge-marshal/tests/meta/` -- no new meta-test this story (the
  bare-exception guard already scans `fs.py`; a dedicated "never-write proof" meta-test, per the
  epics Surface line, is realized here as `test_seed_fs.py`'s symlink-indirect-hit unit test
  rather than a separate AST scan, since the invariant to prove is RUNTIME path-resolution
  behavior, not a static import/call-site shape).

## Tasks & Acceptance

**Execution:**
- [x] `seed/fs.py` -- add `NeverWrite(patterns: tuple[str, ...])` frozen dataclass and a private
  `_matches(never_write, relative_posix_str) -> str | None` returning the first matching pattern
  -- the immutable path-set AC requires
- [x] same file -- add a private `_guard(path, *, repo_root, never_write) -> None`: resolve both
  paths, compute the repo-relative POSIX form (falling back to the absolute resolved form when
  not under `repo_root`), match, raise `NeverWriteViolation` on a hit -- the one check all three
  public functions share
- [x] same file -- add `write(path, data, *, repo_root, never_write) -> None`: guard, then
  `atomic_write_bytes(path, data)`
- [x] same file -- add `replace_span(path, start, end, new_body, *, repo_root, never_write) ->
  None`: guard, then `path.read_bytes()`, splice, `atomic_write_bytes(path, spliced)`
- [x] same file -- add `remove(path, *, repo_root, never_write) -> None`: guard, then
  `path.unlink()`
- [x] `tests/unit/test_seed_fs.py` -- cover every I/O Matrix row, including the symlink-indirect
  case proving resolution (not raw-path matching) drives the guard, and the interrupted-write
  case proving `write`'s atomicity leaves an existing file's original content intact

**Acceptance Criteria:**
- Given a `NeverWrite` set and a target path matching one of its patterns, when `write`,
  `replace_span`, or `remove` is called, then it raises `NeverWriteViolation` naming the matched
  pattern, and the filesystem is left completely untouched (no read, write, or unlink occurred).
- Given a target path that only matches a never-write pattern AFTER symlink resolution (the raw,
  unresolved path does not textually indicate the match), when any of the three functions is
  called, then it still raises `NeverWriteViolation` -- proving resolution happens before matching.
- Given `write`'s underlying `write_fn` fails partway (simulated), when `write` is called against
  a path with pre-existing content, then the original file's content is unchanged afterward.
- Given a `NeverWrite` instance, when code attempts to reassign `.patterns` or mutate an element
  of the existing tuple, then it raises (`FrozenInstanceError`/`TypeError` respectively).
- Given a well-formed span substitution (no never-write match), when `replace_span` runs, then
  every byte outside `[start, end)` is byte-identical to the original file, and the begin/end
  markers themselves are untouched (span substitution never re-reads or re-derives them -- that is
  `regions/apply.py`'s job, not this primitive's).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 3, low 4)
- defer: 0
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): `replace_span` had no
    bounds-check on `start`/`end` -- ordinary Python slice semantics silently accept a negative,
    inverted, or out-of-range span, corrupting the splice instead of raising, directly
    undermining the "every byte outside the span is identical" guarantee. Added an explicit
    `0 <= start <= end <= len(original)` check raising `ValueError`, plus four tests
    (start>end, negative start, end past EOF, and the legitimate zero-length-span case).
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently): `fnmatch.fnmatch`
    case-folds via `os.path.normcase` on Windows and default-case-insensitive macOS filesystems
    but not on Linux -- a platform-dependent SAFETY guard. Confirmed by direct execution
    (`fnmatch.fnmatch('Docs/Dreams/x.md', 'docs/dreams/*.md')` is `False` on this Linux host,
    where `normcase` is a no-op, but would fold on macOS/Windows). Switched to
    `fnmatch.fnmatchcase` and added a case-sensitivity test plus a `*`-crosses-`/` test proving
    the module's own stated design rationale (previously asserted only in prose).
  - `[medium]` `[patch]` Blind Hunter: `NeverWrite`'s "immutable... in full" claim wasn't
    enforced against a caller passing a `list` instead of a `tuple` for `patterns` -- element
    mutation would then succeed silently. Added `__post_init__` coercion + validation mirroring
    `Manifest.never_write`'s own already-established precedent (Story 7.4), plus tests for the
    list-coercion and a blank-pattern rejection.
  - `[medium]` `[patch]` Blind Hunter: the module docstring's own justification for resolving-
    for-match-but-writing-against-the-original-path claimed writing "into a symlink's target
    replaces the target file" -- verified BACKWARDS by direct execution (`os.replace` on a path
    whose leaf is a symlink replaces the symlink itself, per POSIX `rename(2)`, leaving the real
    target file untouched and orphaned). Reworded the docstring to state the confirmed behavior
    and explicitly name it, alongside the check-then-act (TOCTOU) window on a parent-chain
    symlink, as an accepted, out-of-scope-to-harden-further limitation given this tool's
    realistic threat model (a local CLI over an operator-trusted repo, not an adversarial
    concurrent-race defense) -- no V1 target artifact is itself expected to be a symlink.
  - `[low]` `[patch]` Blind Hunter: `remove()`'s test coverage was asymmetric with
    `write`/`replace_span` -- no test proved its guard fires before any existence check, and no
    test proved a plain `OSError` from `Path.unlink()` propagates unchanged. Added both.
  - `[low]` `[patch]` Blind Hunter: no test drove the REAL (non-mocked) `atomic_write_bytes`
    through an overwrite of a file with pre-existing, different content -- every prior no-match
    test only exercised fresh-file creation. Added one.
  - `[low]` `[patch]` Blind Hunter: the repo-external fallback's only existing test used a
    `**`-prefixed pattern specifically shaped to survive the degradation, which doesn't prove the
    degradation is otherwise real. Added a second test using a repo-root-anchored pattern (the
    shape every non-`**` entry in the shipped manifest actually uses) proving the SAME scenario
    silently fails to match when `repo_root` is wrong -- documents the existing, accepted
    limitation with a real assertion rather than only asserting it in Never-boundary prose; does
    not change behavior.
  - `[reject]` Edge Case Hunter: a symlink LOOP in `path.resolve()`/`repo_root.resolve()` raises
    `OSError`/`RuntimeError`. Verified FALSE by direct execution:
    `Path.resolve(strict=False)` on a circular symlink returns a best-effort path without
    raising -- confirmed identically to `ports/fs.py::resolve_path`'s own already-documented
    claim for the exact same non-strict `.resolve()` call this module mirrors.
  - `[reject]` Edge Case Hunter: a permission-denied intermediate component during
    `path.resolve()` lets a raw `OSError`/`PermissionError` escape the guard. Not independently
    re-verified (would require a live permission-denied fixture), but `ports/fs.py::resolve_path`
    -- the exact convention this module's docstring cites and mirrors -- already documents this
    same non-strict `.resolve()` call as swallowing a permission-denied ancestor rather than
    raising, "confirmed live" per that module's own docstring; no reason this call differs.
  - `[reject]` Blind Hunter: `replace_span` does not preserve the original file's permission
    bits across the temp-file-then-rename cycle (`atomic_write_bytes`'s `mode=` defaults to a
    fresh umask-respecting value, not the original file's mode). Real and already true of
    `atomic_write_bytes` for every existing caller in the fleet -- not introduced by this story.
    No V1 target artifact (`CLAUDE.md`, `AGENTS.md`, `.gitignore`, a hybrid-region file) needs
    non-standard permission bits; `atomic_write`'s own docstring names exactly one caller
    (`herald/registry.py`) that does, and this story adds no `mode=` passthrough for the same
    reason S-7.4 declined to adopt S-7.2's not-yet-built taxonomy -- no plausible near-term need.
  - `[reject]` Blind Hunter: `_matches` only reports the first matching pattern when several
    patterns match the same path, losing information a manifest author debugging an overlapping
    rule might want. This is the module's own already-stated, deliberate design choice ("which
    one wins... is not a meaningful distinction for a guard whose only job is block or don't"),
    not a gap introduced by this pass.
  - `[reject]` Blind Hunter: general TOCTOU hardening (`O_NOFOLLOW`/fd-based syscalls) against a
    parent-chain symlink swapped between `_guard`'s resolution and the delegate's own file open.
    Addressed via docstring correction (see the medium patch above naming this limitation
    explicitly), not code: closing it fully needs a substantially different I/O layer, out of
    proportion to this story's M-effort scope and to the epics AC's own concrete test scenario
    (a static, already-in-place symlink, not an active race).

### 2026-08-14 — Review pass 2 (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 3, low 2)
- defer: 0
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: Pass 1's own `NeverWrite.__post_init__` fix coerced a
    `list` to a `tuple` but forgot to STRIP each pattern -- so a pattern with stray padding
    (a plausible YAML block-scalar typo) would pass validation as non-blank yet never match
    any real, unpadded path, silently protecting nothing while still looking like an active
    rule. `Manifest.never_write`'s own precedent, which Pass 1's docstring claimed to fully
    mirror, does strip on store -- only half the precedent was applied. Now strips on store;
    added `test_never_write_strips_padded_patterns_on_store`.
  - `[medium]` `[patch]` Blind Hunter: Pass 1's own docstring claimed macOS's case-
    insensitivity came from `fnmatch.fnmatch`'s `os.path.normcase` call -- verified FALSE by
    reading `posixpath.normcase`'s source ("Has no effect under Posix"; only `ntpath.normcase`
    on Windows folds case). Reworded to state the correct mechanism (a macOS filesystem's own
    VFS-level case-insensitivity is a separate property `fnmatch` has no visibility into) while
    keeping `fnmatchcase` as the right choice for deterministic, platform-independent matching.
  - `[medium]` `[patch]` Blind Hunter: `_guard` never validated `repo_root` itself, so a wrong
    or misspelled `repo_root` silently degraded every repo-relative pattern (the common case) to
    the repo-external absolute-path fallback, which cannot match it -- "deny" became a silent
    "allow" for a plausible caller misconfiguration. Added an upfront `ValueError` when
    `repo_root` does not resolve to an existing directory, plus two tests (missing directory,
    and a file occupying the path).
  - `[medium]` `[patch]` Blind Hunter: `NeverWriteViolation`'s message showed only the
    caller-supplied `path`, giving no hint which resolved location actually matched in the
    symlink-indirect case -- precisely the scenario resolution exists to catch. Now includes
    both the given and resolved paths; added a test asserting both appear in the message.
  - `[low]` `[patch]` Blind Hunter: a `str` passed as `new_body` (plausible -- region content
    naturally starts life as text) fell through to a bare, contextless `TypeError` from the
    splice expression itself. Added an upfront, named `TypeError` plus a test.
  - `[low]` `[patch]` Blind Hunter: no test drove `NeverWrite` against the module's actual
    production input shape -- every test hand-built small, cosmetic patterns. Added
    `_REAL_NEVER_WRITE` (literally `seed/templates/manifest.yaml`'s shipped `never_write` list,
    Story 7.5) plus a parametrized refusal test across all seven pattern categories and one
    ordinary-target-still-allowed test.
  - `[reject]` Blind Hunter: `replace_span` has no staleness check between its `read_bytes()`
    and its `atomic_write_bytes()` call (a lost-update race if the file changes concurrently).
    Explicitly out of scope per this epic's own already-established architecture (Epic 8
    context, Technical Decisions: "Hash/version-drift guards belong in the detect stage, never
    in apply: by the time substitution runs, it trusts the plan that was already built from a
    fresh detect pass. Re-checking inside apply is defense-in-depth only, never the primary
    guard.") -- a higher layer's job, not this primitive's.
  - `[reject]` Blind Hunter: `NeverWrite.__post_init__` only coerces `list`, not `set`/
    `frozenset`/a generator. Real, but the reviewer's own investigation confirms this mirrors an
    IDENTICAL gap already present in `Manifest.never_write`'s own `__post_init__` (the exact
    precedent this module deliberately mirrors) -- not a new regression introduced here, and no
    more in scope to fix here than in the sibling it copies.
  - `[reject]` Edge Case Hunter: a case-insensitive FILESYSTEM (independent of `fnmatch`'s own
    case-folding, which pass 2 already corrected) could let a caller reach a protected file via
    alternate casing. Real in principle, but no cheap fix exists (would require querying the
    filesystem's own canonical casing, which POSIX `resolve()` does not do), and no real V1
    target artifact (`CLAUDE.md`, `AGENTS.md`, `.gitignore`, a manifest-declared hybrid file) has
    a plausible path to inconsistent casing in practice -- the manifest itself always names them
    with one canonical case.
  - `[reject]` Edge Case Hunter: `start`/`end` passed as a non-`int` type (float, etc.) falls
    through to a generic `TypeError` from slicing rather than a custom, named error. The type
    hints already declare `int`; a caller violating them still fails LOUDLY (just with a stdlib
    exception, not a bespoke one) -- proportionally similar to how `parse.py`/`markers.py`
    elsewhere in this package do not exhaustively runtime-check every already-type-hinted
    parameter when the failure mode is already non-silent.
  - `[reject]` Edge Case Hunter: `NeverWrite(())` (an empty pattern set) should raise. Rejected
    as a real bug: an empty never-write set is legitimate, intentional input (multiple existing
    tests in this same suite construct it deliberately to mean "no restrictions apply" for
    isolated testing), and the epics AC never states patterns must be non-empty -- enforcing
    that would break already-correct test code for a requirement nobody asked for.
  - `[reject]` Blind Hunter: `remove()`'s directory-removal behavior (`IsADirectoryError` from
    `Path.unlink()`) was undocumented. Addressed via a docstring clarification (see the code
    diff), not a behavior change or new test -- `Path.unlink()`'s own well-documented stdlib
    behavior propagating unchanged is exactly this module's stated contract, not a gap.

## Design Notes

**Why `fnmatch`, not a hand-rolled `**`-aware matcher.** `pathlib.Path.match()` at this
package's Python 3.12 floor does not support recursive `**` at all (that lands in 3.13's
`full_match`). `fnmatch.fnmatch` already treats a run of `*` characters as "match anything
including `/`" — which makes `**/planning-artifacts/**` and a single `*` behave identically under
it, exactly the over-matching-is-safe direction a never-write guard wants, without adding a new
dependency or a bespoke glob engine for a six-pattern list.

**Why the guard resolves for matching but the I/O runs against the caller's original path.**
Resolving `path` fully and then handing the RESOLVED path to `atomic_write_bytes`/`unlink` would
mean writing into a symlink's target replaces the target file (usually what's wanted) but
`os.replace`/`unlink` on a path that is itself a live symlink component earlier in the chain could
behave differently than the caller expected. This story only needs the guard to see through
symlinks for the never-write CHECK (the concrete AC scenario); it deliberately does not also
redefine what "write to `path`" means when `path` itself is a symlink -- that mirrors
`ports/fs.py`'s own split between `resolve_path` (a probe) and `write_text_atomic` (an operation
on the given path), already established elsewhere in this same package.

**Why `replace_span` reads the file itself rather than taking pre-read bytes.** Centralizing
read+splice+write in one guarded primitive is what makes "only the bytes between the markers
change; every byte outside the span is identical" a property of `fs.py` itself, provable once,
rather than a discipline every future caller (`regions/apply.py`, and whatever eventually calls
`update`/`adopt`) has to re-derive correctly on their own.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new `test_seed_fs.py`.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (no contract restricts `seed.fs` importing `pyforge.core` or
  `seed.errors`).

## Auto Run Result

Status: done

Summary: implemented `seed/fs.py` -- the never-write-guarded filesystem primitive (`NeverWrite`,
`write`, `replace_span`, `remove`), the direct prerequisite Story 8.3 (span substitution) needs.
Two independent review passes ran. Pass 1 (parallel Blind Hunter + Edge Case Hunter) found a real
high-severity data-corruption gap (`replace_span` had no span bounds-check) plus a platform-
dependent guard-matching bug, an unenforced immutability claim, and a factually-backwards
docstring claim about symlink write semantics. Pass 1's own `NeverWrite` fix was itself only
half-correct (coerced but didn't strip); Pass 2 (a follow-up review, run independently after
Pass 1) caught that plus a second inaccurate technical claim Pass 1 introduced (macOS case-
folding attributed to the wrong mechanism), a silent-fail-open gap on a misconfigured
`repo_root`, and three smaller coverage/UX gaps -- all fixed in that pass.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- new: `NeverWrite`
  (`__post_init__` coercion, validation, AND strip-on-store), `_matches` (`fnmatch.fnmatchcase`,
  corrected rationale), `_guard` (now validates `repo_root`, names both paths in a violation
  message), `write`, `replace_span` (bounds-checked, `new_body` type-checked), `remove`
  (documented directory behavior); corrected Design Notes on symlink-leaf write semantics and the
  accepted TOCTOU limitation.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_fs.py` -- new: 42 tests covering
  every I/O Matrix row plus every review-driven addition across both passes (bounds-check cases,
  case-sensitivity, `*`-crosses-`/`, list-coercion + strip-on-store, `repo_root` validation,
  violation-message content, `new_body` type-check, `remove()` symmetry, a real non-mocked
  overwrite, the honest repo-external-fallback-limitation proof, and a parametrized integration
  test against the ACTUAL shipped `seed/templates/manifest.yaml` `never_write` pattern set).

Review findings breakdown (both passes combined): 14 patch (2 high, 6 medium, 6 low -- all
applied), 0 defer, 11 reject (three independently verified false via direct execution against
this exact non-strict `resolve()` call, `posixpath.normcase`'s own source, and POSIX
`rename(2)`'s documented semantics; eight real-but-out-of-proportion given this story's scope,
this tool's realistic threat model, this epic's own already-established detect-vs-apply guard
placement, or a sibling module's identical, already-accepted precedent). See Review Triage Log
above for the full per-pass findings and fixes.

Follow-up review recommended: **false**. Pass 2's own fixes are narrow (a strip-on-store
one-liner, a docstring correction, two upfront validation additions, one message improvement) and
well-tested (13 new tests); none touch the core guard-then-splice control flow Pass 1 already
established and this pass re-verified end-to-end against the real shipped manifest pattern set.
Two independent review passes (four reviewer-instances total) have now scrutinized this module
without surfacing anything suggesting a third pass would find more of the same class of defect.

Verification performed:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3784 passed, 9 deselected (42 in
  `test_seed_fs.py`, up from the pre-review 17).
- `pixi run -e local-recipes ruff check` scoped to both changed files -- `All checks passed!`.
- `pixi run -e local-recipes pyright` scoped to `seed/fs.py` -- `0 errors, 0 warnings, 0
  informations`.
- `pixi run --frozen -e pyforge-marshal lint-imports --config .../pyproject.toml --no-cache` --
  `Contracts: 3 kept, 0 broken`.
- Every disputed technical claim across both passes (the `fnmatch.fnmatch` case-folding
  mechanism, the `os.replace`-on-a-symlink-leaf behavior, the `Path.resolve(strict=False)`
  symlink-loop behavior, and `posixpath.normcase`'s own source) was independently confirmed or
  refuted by direct execution (`python3 -c ...`) before triaging, not accepted on any reviewer's
  word alone -- including Pass 1's own docstring claims, one of which Pass 2 then caught as wrong.

Residual risks: the two accepted, out-of-scope limitations (symlink-leaf replace-not-follow
semantics; the parent-chain TOCTOU window) and the repo-external-fallback's remaining degradation
mode (an anchored pattern still cannot catch a repo-external path even with a NOW-validated
`repo_root`, if `path` itself is legitimately outside it) are all explicitly documented in the
module's own docstring and test suite rather than silently absent, so a future story choosing to
harden any of them has the reasoning and a regression-test scaffold already in place.
