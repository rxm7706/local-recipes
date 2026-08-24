---
title: 'Story 8.2: Region parser — span discovery, nesting rejection, fence awareness'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '7f51bc983846d6cdccd315ccf689496d4745c3b7'
final_revision: '55c0e5eb218df2a086277cf2b4070f536f43a6c9'
---

<intent-contract>

## Intent

**Problem:** Story 8.1 shipped the marker grammar (`seed/regions/markers.py`: render/parse ONE
line at a time), but nothing yet scans a whole file to locate managed-region spans, and AR-1
(region corruption) plus the K-01 kill criterion make this the highest-risk unbuilt piece of the
product — substitution (S-8.3) cannot exist without a provably correct span to operate on.

**Approach:** Add `seed/regions/parse.py`: a pure `parse_regions(text, fmt)` function that
walks a file's lines with `markers.parse_marker_line`, tracks at most one open region at a time
(so any second `begin` before its `end` is rejected — the single check FR-113 uses for BOTH
"nested" and "overlapping"), skips marker-looking lines inside a fenced code block when
`fmt is RegionFormat.HTML`, and returns one `RegionSpan` per region with byte offsets into the
UTF-8 encoding of `text`.

## Boundaries & Constraints

**Always:**
- `parse_regions(text: str, fmt: RegionFormat) -> tuple[RegionSpan, ...]` is pure — no I/O, no
  subprocess, no clock (P-03) — a caller reads the file itself and passes the text in.
- Spans are **byte** offsets into `text.encode("utf-8")`, not character offsets (P-06 — S-8.3's
  substitution operates on raw bytes). Compute them incrementally while walking
  `text.splitlines(keepends=True)`; never re-encode a growing prefix per line.
- `RegionFormat` is the caller's declared value, passed straight through to
  `markers.parse_marker_line` — never sniffed (same discipline as S-8.1).
- One check catches BOTH "nested" and "overlapping" (FR-113 names them as one rule): a `begin`
  marker encountered while a region is already open is a hard `RegionParseError` naming both
  region names (the one still open and the new one) — regardless of whether the new region's
  `end` would have appeared before or after the open one's `end`.
- An unterminated `begin` (EOF reached with a region still open) is a hard `RegionParseError`
  naming the unterminated region.
- A `begin` whose region name was already used by an earlier, already-**closed** region in the
  same file is a hard `RegionParseError` naming the duplicate name.
- An `end` marker whose region name does not match the currently open region — including a
  stray `end` with nothing open — is a hard `RegionParseError` naming the mismatch.
- Fence-awareness applies only when `fmt is RegionFormat.HTML` (the format registered for
  `.md`): while inside a fenced code block (a line, after stripping ≤3 leading spaces, that
  starts with a run of 3+ `` ` `` or 3+ `~`, closed by a same-character run of ≥ the opening
  run's length), every line is ordinary content — `parse_marker_line` is never called on it, so
  a marker-looking string inside a fence can never open, close, or corrupt parser state.
- CRLF and LF parse identically: use `str.splitlines()`'s own universal line-boundary handling
  (LF, CRLF, and lone CR all become one boundary) to derive the line content passed to
  `parse_marker_line` — never a manual `.rstrip("\r")` special case.
- A `MarkerError` raised by `markers.parse_marker_line` (a line that carries the
  `marshal-seed:` tag but is grammatically malformed) propagates unchanged — this module never
  re-implements or wraps line-level grammar checking.
- Regions are returned in file order (the order their `begin` marker appears).

**Block If:** None — FR-113/AD-53/P-06 plus this epic's own AC fully specify nesting,
duplicate-name, and fence-awareness behavior; no decision here requires human input.

**Never:**
- Perform span substitution, call `fs.replace_span()`, or write anything — S-8.3.
- Resolve anchors, insert a region, or define the `<top>` sentinel — S-8.4.
- Recompute or validate a region's declared `sha` against its actual body content — that
  comparison belongs to a later (detect) stage per P-07; this module reports the declared `sha`
  from the `begin` marker as-is, unchecked.
- Implement marker deletion / opt-out state — S-8.5.
- Implement `RegionFormat.SLASHSTAR` support — `markers.parse_marker_line` already raises
  `NotImplementedError` for it; this module does not catch or special-case that.
- Read a file from disk — the caller (a future detect-stage story) owns I/O; this module only
  ever sees `text: str` already in memory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No regions | text with zero markers | `()` | No error |
| One clean region | `begin region=a` … body … `end region=a` | one `RegionSpan` naming `a`, correct body/marker byte-spans | No error |
| Two sibling regions | `begin a` … `end a` … `begin b` … `end b` | two `RegionSpan`s, in file order | No error |
| Nested | `begin a`, `begin b`, `end b`, `end a` | n/a | `RegionParseError` naming `a` and `b` |
| Overlapping (interleaved) | `begin a`, `begin b`, `end a`, `end b` | n/a | `RegionParseError` naming `a` and `b` |
| Unterminated begin | `begin a` with no matching `end` before EOF | n/a | `RegionParseError` naming `a` |
| Duplicate region name | `begin a` … `end a` … `begin a` … `end a` again | n/a | `RegionParseError` naming `a` |
| Mismatched / stray end | `begin a` … `end b`, or a bare `end a` with nothing open | n/a | `RegionParseError` |
| Marker inside a fence | a markdown fence (`` ``` `` or `~~~`) whose body contains a literal `<!-- marshal-seed:begin ... -->` line | the fenced marker is ignored entirely (not opened, not an error) | No error |
| CRLF file | the "one clean region" scenario with every line ending `\r\n` | identical `RegionSpan` (byte offsets into the CRLF-encoded text) as the LF case | No error |
| Malformed marker line | a line carrying `marshal-seed:` but violating the exact grammar (e.g. bad sha) | n/a | `MarkerError` (from `markers.py`, propagated unchanged) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- NEW, this
  story's Surface: `RegionSpan` (frozen dataclass), `RegionParseError`, `parse_regions`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- REFERENCE
  ONLY (Story 8.1, already shipped): `parse_marker_line`, `BeginMarker`, `EndMarker`,
  `MarkerError`, `RegionFormat`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/version.py` -- REFERENCE
  ONLY: `ModelVersion`, used as `RegionSpan.model_version`'s type.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` -- NEW, covers
  every I/O Matrix row.

## Tasks & Acceptance

**Execution:**
- [x] `seed/regions/parse.py` -- add `RegionParseError(PyforgeError, ValueError)` (Story 14.3
  convention, matching `MarkerError`'s shape) -- the region-structure error type
- [x] same file -- add `RegionSpan` frozen dataclass: `name: str`, `model_version: ModelVersion`,
  `sha: str`, `body_span: tuple[int, int]`, `begin_span: tuple[int, int]`,
  `end_span: tuple[int, int]` -- the per-region return shape the AC requires
- [x] same file -- add a private fence-toggle helper (`` ` `` or `~` run of length ≥3, ≤3 leading
  spaces stripped first) used only when `fmt is RegionFormat.HTML` -- fence-awareness AC
- [x] same file -- add `parse_regions(text, fmt) -> tuple[RegionSpan, ...]`: walk
  `text.splitlines(keepends=True)` tracking a running byte offset, skip fenced lines, call
  `markers.parse_marker_line` on every other line's line-terminator-stripped content, maintain
  at most one open region, and raise `RegionParseError` for nesting/overlap, unterminated begin,
  duplicate name, and end-marker mismatch per the Always bullets above
- [x] `tests/unit/test_seed_regions_parse.py` -- cover every I/O Matrix row, plus the body-span
  byte-offset proof (a region whose body contains multi-byte UTF-8 content, asserting
  `text.encode("utf-8")[start:end]` reconstructs the exact body) and the zero-length-body case
  (`begin`/`end` on adjacent lines)

**Acceptance Criteria:**
- Given a file with zero or more well-formed managed regions, when `parse_regions` runs, then it
  returns one `RegionSpan` per region, in file order, each carrying the region's name,
  model-version, declared sha, body byte-span, and both marker byte-spans.
- Given a `begin` marker encountered while a region is already open, when `parse_regions` runs,
  then it raises `RegionParseError` naming both region names, whether the markers are properly
  nested or interleaved.
- Given an unterminated `begin` marker, when `parse_regions` reaches end of text, then it raises
  `RegionParseError` naming the unterminated region.
- Given two `begin`/`end` pairs sharing one region name in the same file, when `parse_regions`
  runs, then it raises `RegionParseError` naming the duplicate.
- Given a fenced code block in a markdown (`RegionFormat.HTML`) file containing a
  marker-shaped line, when `parse_regions` runs, then that line is never treated as a marker —
  no region opens, closes, or errors because of it.
- Given the same well-formed file with LF line endings and with CRLF line endings, when
  `parse_regions` runs on each, then both produce the same region names, model-versions, and
  shas (byte spans differing only by each CRLF's extra byte per line, as expected).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 2, medium 0, low 2)
- defer: 0
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): an unclosed fenced code
    block running to end-of-text silently swallowed every region after it (fenced content is
    never scanned for markers), returning `()` instead of raising — confirmed by direct
    execution before fixing. Now a hard `RegionParseError` naming the line the fence opened on.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): `_fence_delimiter`
    accepted a closing-fence line with trailing content after the backtick/tilde run (e.g.
    `` ``` still open ``), closing the fence early per CommonMark's actual rule (a closer may be
    followed only by whitespace) — the AR-1 corruption case from the opposite direction: a real
    marker meant to stay inert inside the fence gets parsed as live. Confirmed by direct
    execution before fixing. Added `_closes_fence` (character + run-length + trailing-whitespace
    check), used only for the already-open-fence branch; `_fence_delimiter` keeps its
    opener-detection role, with its docstring narrowed to say so.
  - `[low]` `[patch]` Both reviewers: `parse_regions("", RegionFormat.SLASHSTAR)` (and any
    unregistered `fmt` on empty text) returned `()` / raised nothing instead of propagating
    `NotImplementedError`/`MarkerError`, because the loop only ever reaches
    `parse_marker_line` on a line that looks like a marker — never on zero lines. Added an eager
    `parse_marker_line(fmt, "")` probe at the top of `parse_regions`, side-effect-free for every
    registered format.
  - `[low]` `[patch]` Blind Hunter: no test exercised a document mixing line-ending styles
    (CRLF then LF in one file) — the per-line byte-accounting design already handled this
    correctly, so this added coverage rather than fixing a defect.
  - findings rejected: (1) `str.splitlines()`'s line-boundary set is wider than the module's
    docstring states (also splits on VT/FF/NEL/LS/PS) — real, but an unavoidable consequence of
    this story's own spec-mandated `Always` bullet to use `splitlines()` for CRLF parity, and
    those control characters do not occur in this epic's real target file types
    (`.md`/`.gitignore`/`.toml`/`.yml`/`.yaml`/shell); (2) a lone-surrogate `UnicodeEncodeError`
    escaping unguarded — requires text a caller could only produce via
    `errors="surrogateescape"` decoding, out of this pure module's P-03 scope (the caller owns
    how `text: str` was produced); (3) the raise-order precedence between "nesting" and
    "duplicate name" when both technically apply is untested — not a bug, an unstated but
    reasonable and stable implementation detail; (4) fence-awareness's reliance on `RegionFormat`
    being a `StrEnum` is unasserted locally — true but hypothetical, no plausible path to it
    changing within this story's scope.

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: when an unclosed fence AND an entirely unrelated,
    independently-unterminated `begin` (opened and never closed before the fence ever appeared)
    were both true at end-of-text, the fence error was raised alone — silently dropping the fact
    that a real region was also still open, forcing a fix-and-rerun cycle to discover the second
    problem. Confirmed by direct execution before fixing. The fence error message now names the
    open region too when one is present; added a regression test plus a sibling test proving the
    message stays fence-only when no region is open.
  - `[low]` `[patch]` Blind Hunter: no test exercised two fenced blocks in one file (the first
    closed cleanly, a second, later one left open) to confirm `fence_lineno` tracks the CURRENT
    fence rather than stale state from the first — the logic was already correct by inspection, so
    this added coverage rather than fixing a defect.
  - findings rejected: (1) & (2) both reviewers independently re-raised this spec's own first
    review pass's already-rejected finding that `str.splitlines()`'s line-boundary set is wider
    than CRLF/LF/CR (also VT/FF/NEL/LS/PS) — the prior pass's reasoning (spec-mandated
    `splitlines()` use for CRLF parity; those control characters do not occur in this epic's real
    target file types) still holds, rejected again for the same reason; (3) Edge Case Hunter: no
    explicit `isinstance(marker, EndMarker)` guard in the dispatch after the `BeginMarker` check —
    verified as a false positive: `markers.parse_marker_line` is declared
    `-> BeginMarker | EndMarker | None`, a closed union this module's own `pyright` gate already
    proves exhaustive; a hypothetical future third marker kind would be a breaking change to
    `markers.py` (Story 8.1, REFERENCE ONLY), out of this story's scope; (4) Blind Hunter: the
    eager `parse_marker_line(fmt, "")` probe leans on an unstated implementation detail of
    `markers.py` (that no registered delimiter prefix matches the empty string) — true, but a
    property of a sibling module this story does not own, not a defect here; (5) Blind Hunter:
    fence-awareness applies only to `RegionFormat.HTML`, leaving `hash`-format artifacts without
    equivalent protection — this is the intent-contract's own explicit, deliberate scope ("Fence
    awareness applies only when `fmt is RegionFormat.HTML`"), not a gap; (6) & (7) Blind Hunter:
    two micro-optimizations (`_iter_lines` double-encoding the same leading bytes; `fmt` re-coerced
    per marker-looking line inside `parse_marker_line`) — real but immaterial at this module's
    target file sizes (single markdown/config artifacts, not bulk data), no correctness impact;
    (8) Blind Hunter: this spec's own first review pass's already-rejected finding that the
    nesting-vs-duplicate-name raise-order is untested — rejected again for the same reason (an
    unstated but reasonable, stable implementation detail); (9) Blind Hunter: no test asserts
    `RegionSpan`/`_OpenRegion`'s `frozen=True` immutability is enforced — that would test Python's
    own `dataclasses` module, not this module's logic; (10) Blind Hunter: error messages carry a
    bare line number with no file identity — consistent with this module's own Never-section scope
    (it never reads a file or receives a path; a batch-scanning caller owns enriching messages with
    file context).

  Also reconciled `spec-pyforge-marshal`'s `.memlog.md`: `python scripts/
  spec_surface_reconcile.py` flagged `parse.py` and its test as added-but-ungoverned (the prior
  pass's own "no memlog update needed" claim did not hold once the drift baseline was
  re-evaluated) — appended a "Surface reconcile ... story 8-2 landing" entry naming both files and
  re-stamped the baseline (`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`); no
  code change from this repair, matching the precedent set by story 8-1's own repair-pass entry in
  the same memlog.

## Design Notes

**Byte-span semantics.** `begin_span`/`end_span` cover exactly the marker LINE's bytes,
excluding its own line terminator. `body_span` covers every byte strictly between the two
marker lines — i.e. it starts immediately after the `begin` line's terminator and ends exactly
where the `end` line's bytes start, so it includes any interior newlines but excludes both
marker lines themselves. For:

```
<!-- marshal-seed:begin region=x model-version=1.0.0 sha=deadbeef -->
line1
<!-- marshal-seed:end region=x -->
```

`body_span` is the byte range of `"line1\n"`, and reconstructing the file is
`text_bytes[:body_span[0]] + new_body + text_bytes[body_span[1]:]` — this is the contract S-8.3
substitutes against.

**Why one check for nested AND overlapping.** FR-113/AD-53 name "nested or overlapping regions"
as a single hard-error rule, and structurally there is no way to reach an interleaved
`begin A, begin B, end A, end B` sequence without first passing through the state "a `begin`
arrived while a region is still open" (at `begin B`) — the exact same state a properly-nested
`begin A, begin B, end B, end A` sequence reaches. Tracking a single `open_region | None` (not a
stack) is therefore sufficient: nesting is rejected as a category, not merely non-well-formed
nesting, so no lookahead or stack is needed to tell the two shapes apart.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new `test_seed_regions_parse.py`.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (no contract restricts `seed.regions` importing within itself).

## Auto Run Result

Status: done

Summary: implemented `seed/regions/parse.py` -- a pure `parse_regions(text, fmt)` that scans a
whole file for managed-region spans, rejecting nested/overlapping regions, unterminated begins,
duplicate names, and mismatched/stray ends, while skipping marker-shaped lines inside a markdown
fenced code block. Two independent review passes ran against this story. Pass 1 (parallel Blind
Hunter + Edge Case Hunter) surfaced two real high-severity bugs in the fence state machine -- both
directly in AR-1's blast radius, the region-corruption risk this whole epic exists to contain --
fixed in that pass, plus two low-severity edge-case gaps closed defensively. Pass 2 (a follow-up
review, run independently after Pass 1) surfaced one real medium-severity bug -- an unclosed fence
at end-of-text could silently drop the fact that an unrelated region was also still open -- fixed
in that pass, plus one low-severity coverage addition; two of Pass 2's findings were re-discoveries
of Pass 1's own already-rejected findings, rejected again for the same reasoning.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- new:
  `RegionParseError`, `RegionSpan`, `_OpenRegion`, `_fence_delimiter`/`_closes_fence`,
  `parse_regions`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` -- new, 46 tests
  covering the full I/O & Edge-Case Matrix plus both passes' review-driven additions.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- Pass 2 repair: appended a "Surface reconcile ... story 8-2 landing" entry naming both new
  files as governed (Pass 1's own "no memlog update needed" claim did not survive re-evaluation of
  the drift baseline); no code change from this repair.
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to `spec-pyforge-marshal` only.
- This spec file -- tasks checked off, Review Triage Log and this result updated across both
  passes.

Review findings breakdown (both passes combined): 6 patch (2 high, 1 medium, 3 low -- all
applied), 0 defer, 13 reject (all independently verified as either pre-existing spec-mandated
tradeoffs, false positives disproven by the sibling module's own type signature, or out of this
pure module's scope). See Review Triage Log above for the full per-pass findings and fixes.

Follow-up review recommended: **false**. Pass 2's fixes are narrow and well-tested: a one-line
error-message augmentation (guarded by a new test proving both the with-region and without-region
message shapes) plus a pure test-coverage addition -- neither touches the fence state machine's
actual parsing control flow, which Pass 1's follow-up request specifically targeted and which
subsequent scrutiny (both reviewers, independently) did not find further defects in.

Verification performed:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3667 passed, 9 deselected (46 of
  them in `test_seed_regions_parse.py`, up from the pre-review-pass 38).
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- 186 errors,
  byte-identical to the pre-change baseline; both new files individually clean.
- `pixi run -e local-recipes pyright` scoped to both new files -- `parse.py`: 0 errors; the test
  file's 3 `reportMissingImports` are the same pre-existing env-artifact category every test file
  in this package already carries under the `local-recipes` env (pyforge isn't installed there).
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- 3 contracts kept, 0 broken.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 74 passed.
- `python3 scripts/spec_surface_reconcile.py` -- `OK: every tracked file governed or allowlisted;
  no drift.` (rc=0) after the Pass 2 memlog repair + baseline re-stamp.
- All three review-flagged bugs (2 from Pass 1, 1 from Pass 2) reproduced by direct execution
  before their fixes and confirmed absent after.

Residual risks: the 13 rejected findings across both passes are recorded above with their
reasoning in case a future story's real-world usage proves one of them wrong (in particular, the
`splitlines()` boundary-set breadth and the raise-order precedence are cheap to revisit if
S-8.3/S-8.4 ever surface a concrete failure). No open acceptance-criterion gaps.

Out-of-band note: this story's completed work (commit `accc097e6a`) was briefly lost from this
run's branch between Pass 1 and Pass 2 -- an out-of-band `git reset` (apparent side effect of
sibling story 8-1's orchestrator-level baseline-mismatch defer reaching this worktree) moved HEAD
back to pre-epic-8 trunk. The work survived intact on the run's own `attempt-preserve` safety-net
branch and was restored by a clean fast-forward (verified: the reset point was an ancestor of the
preserved commit, so nothing was overwritten) before Pass 2's diff was constructed. No code or
spec content was lost; noted here for fleet-visibility only.
