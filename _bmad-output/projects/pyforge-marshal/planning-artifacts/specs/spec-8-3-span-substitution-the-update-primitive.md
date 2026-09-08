---
title: 'Story 8.3: Span substitution — the update primitive'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '49debfce5b'
final_revision: 'f19ba4d2e5'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
difficulty: 'heavy'
---

<intent-contract>

## Intent

**Problem:** Story 8.2 shipped `parse_regions` (locates a managed region's exact byte spans) and
Story 7.3 shipped `fs.replace_span` (the guarded, atomic byte-span writer), but nothing yet
combines them into "replace a region's body with new content" — the one write path the whole
epic exists to make safe. Without it, `marshal seed update`'s core verb has no primitive to call.

**Approach:** Add `seed/regions/apply.py`: `substitute_region(text, path, region, new_body, *,
model_version, expected_sha, fmt, repo_root, never_write)` — a single guarded write that replaces
BOTH the begin marker line (re-rendered with the new `model_version`/sha) and the body in one
`fs.replace_span()` call (never two), so a crash mid-write can never leave a region with a new
body but a stale marker (or vice versa) — the exact "half-merged" state AR-1/NFR-R1 forbid.

## Boundaries & Constraints

**Always:**
- `substitute_region(text: str, path: Path, region: RegionSpan, new_body: str, *, model_version:
  ModelVersion, expected_sha: str, fmt: RegionFormat, repo_root: Path, never_write: NeverWrite) ->
  None`. `text` is the SAME text the caller already parsed `region` out of via `parse_regions`
  (read with `newline=""` — see the Never bullet below); this function does no I/O of its own to
  locate the region, only to write the substitution via `fs.replace_span`.
- Raises `RegionShaMismatchError` (this module's own type, `PyforgeError` + `ValueError`, matching
  `MarkerError`/`RegionParseError`'s shape) BEFORE any write when `region.sha != expected_sha` —
  the AC's belt-and-braces assertion; the primary guard is the caller's own fresh detect pass
  (P-07), this is defense-in-depth only.
- Computes the new sha via `markers.region_sha(new_body)` and renders the new begin marker line
  via `markers.render_begin(fmt, region.name, model_version, new_sha)` — never accepts a
  caller-supplied sha for the NEW marker (only `expected_sha`, for the OLD one, is caller input).
- Builds ONE combined replacement spanning `region.begin_span[0]` through `region.body_span[1]`:
  the new begin-marker-line bytes, then the ORIGINAL terminator bytes between the begin line and
  the body (`text.encode("utf-8")[region.begin_span[1]:region.body_span[0]]` — 1–2 bytes, `\n` or
  `\r\n`, sliced verbatim so line-ending style is preserved without re-deriving it), then
  `new_body.encode("utf-8")`. Writes this ONE combined payload through exactly one
  `fs.replace_span(path, region.begin_span[0], region.body_span[1], combined, repo_root=...,
  never_write=...)` call — never two separate calls (the epic's own core invariant: a crash
  between two writes would leave a genuinely half-merged region, which the whole architecture
  exists to make unrepresentable). Since `begin_span` precedes `body_span` in file order, nothing
  about this combined range depends on any byte outside it, and everything outside it (per
  `fs.replace_span`'s own contract) stays byte-identical — including the file's own trailing
  content, which is how "the file's original trailing-newline state is preserved" holds for free.
- `new_body` may contain literal conflict-marker-shaped text (`<<<<<<<`, `=======`, `>>>>>>>`)
  and it is written exactly as given — pure byte concatenation has no notion of "special" text.

**Block If:** None — the epics AC (combined-span construction, sha guard, marker re-rendering)
plus S-8.2/S-7.2/S-7.3's already-shipped primitives fully specify this story; no decision here
requires human input.

**Never:**
- No file I/O of its own — `text` is caller-supplied (already read the same way `parse_regions`
  requires: `path.read_text(encoding="utf-8", newline="")`, NOT plain `read_text()`, whose default
  universal-newline translation would silently convert `\r\n` to `\n` on read and desync `region`'s
  byte offsets from the file's real on-disk bytes before `fs.replace_span` ever gets a chance to
  read them fresh — this module documents the requirement, it does not enforce it, since it never
  reads a file itself).
- No re-parsing or re-validating `region` against a fresh read of `path` — `fs.replace_span`'s own
  offsets are trusted to apply against whatever `path` currently holds, exactly like the parser
  trusts a single fresh `parse_regions` pass (P-07's detect-owns-the-guard discipline); closing the
  read-then-write race fully is out of this story's scope (mirrors S-7.3's own accepted,
  documented TOCTOU limitation).
- No anchor resolution or region insertion — S-8.4's surface, for a region that does not exist yet.
- No marker deletion / opt-out handling — S-8.5's surface.
- Never calls `Path.write_text`, `open(..., "w")`, or any write primitive other than
  `fs.replace_span` (P-01) — this module must not reimplement atomic writes locally (Epic 8
  context, Technical Decisions).
- No idempotence/no-op short-circuit (e.g. skipping the write when `new_body` already matches) —
  AD-60 defines idempotence as PLAN-emptiness; deciding whether to call this function at all is
  the plan layer's job (a future story), not this primitive's.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ordinary substitution | A file with one clean region, new body text, matching `expected_sha` | begin marker's sha/model-version updated, body replaced, every byte outside the combined span byte-identical | No error |
| Prefix/suffix preservation | Content before `begin_span` and after `body_span` (incl. the `end` marker line and anything after it) | byte-for-byte identical to the original | No error |
| Sha mismatch | `expected_sha` does not equal `region.sha` | -- | `RegionShaMismatchError`; file untouched |
| Conflict-marker-shaped new body | `new_body` literally contains `` <<<<<<< HEAD\n=======\n>>>>>>> branch `` | written to disk verbatim, no error, no special-casing | No error |
| CRLF file | Same "ordinary substitution" scenario but every line ends `\r\n` | the untouched terminator between the (new) begin line and the (new) body is `\r\n`, matching the original; every other CRLF elsewhere in the file is unaffected (outside the span) | No error |
| model_version-only change (body text unchanged) | `new_body == ` the old body's text, but a different `model_version` | new sha still computed from `new_body` (unchanged, since body text is unchanged) and written; the begin marker's model-version changes even though the sha does not | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/apply.py` -- NEW, this
  story's Surface: `RegionShaMismatchError`, `substitute_region`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- REFERENCE
  ONLY (Story 8.2, already shipped): `RegionSpan`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- REFERENCE
  ONLY (Story 8.1, already shipped): `render_begin`, `region_sha`, `RegionFormat`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/version.py` -- REFERENCE
  ONLY: `ModelVersion`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- REFERENCE ONLY (Story
  7.3, already shipped): `replace_span`, `NeverWrite`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` -- NEW, covers
  every I/O Matrix row.

## Tasks & Acceptance

**Execution:**
- [x] `seed/regions/apply.py` -- add `RegionShaMismatchError(PyforgeError, ValueError)` -- the
  belt-and-braces sha-guard's error type, matching `MarkerError`/`RegionParseError`'s shape
- [x] same file -- add `substitute_region(text, path, region, new_body, *, model_version,
  expected_sha, fmt, repo_root, never_write) -> None`: raise on sha mismatch, compute the new
  sha, render the new begin marker line, slice the original terminator bytes, build the combined
  payload, and write it via exactly one `fs.replace_span` call
- [x] `tests/unit/test_seed_regions_apply.py` -- cover every I/O Matrix row, including a direct
  byte-for-byte comparison of every region of the file OUTSIDE the combined span (proving the
  prefix/suffix preservation claim, not just the substituted content), and asserting
  `fs.replace_span` is called exactly once (not twice) per substitution

**Acceptance Criteria:**
- Given a file with a managed region and new body content, when `substitute_region` runs, then
  only the bytes between `region.begin_span[0]` and `region.body_span[1]` change; every byte
  outside that combined span is identical (asserted by comparing the prefix and suffix
  byte-for-byte).
- Given the same call, when it completes, then the begin marker's `model-version` and `sha` are
  updated to the new values (the sha freshly computed from `new_body`, not caller-supplied).
- Given the same call, then it writes through `fs.replace_span()` -- never `Path.write_text` --
  and does so exactly once, never as two separate writes.
- Given `new_body` that deliberately contains `<<<<<<<`, `=======`, or `>>>>>>>`-shaped text, when
  `substitute_region` runs, then that text is written to disk literally, unmodified.
- Given a file with CRLF line endings, when `substitute_region` runs, then the terminator between
  the rewritten begin marker line and the rewritten body is the same CRLF the original file used.
- Given `expected_sha` that does not match `region.sha`, when `substitute_region` runs, then it
  raises `RegionShaMismatchError` before writing anything, and the file is left untouched.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 3, low 3)
- defer: 0
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): reusing a `RegionSpan`'s
    offsets from ONE `parse_regions` pass across a SECOND `substitute_region` call against the
    same file (e.g. substituting region A then region B, both parsed together) silently corrupts
    region B once A's new body has a different length -- B's stale offsets no longer point at B.
    Confirmed real by direct test construction. The intent-contract's `substitute_region(...) ->
    None` signature is frozen (a return-value change would need a full `bad_spec` spec amendment,
    disproportionate to this finding), so this is fixed via clear documentation (a new module
    docstring section explaining the hazard and citing the epic's own already-established P-07
    discipline -- "detect fresh, apply one, re-detect" -- as the correct, pre-existing pattern,
    not a new requirement) plus two tests: one proving the hazard is real, one proving the safe
    re-parse-between-calls pattern avoids it.
  - `[medium]` `[patch]` Edge Case Hunter: `region.begin_span[1] > region.body_span[0]` (a
    malformed, only-possible-via-hand-construction `RegionSpan`) let a negative-length slice
    silently return `b""` instead of raising, concatenating the new begin line directly onto the
    new body with no terminator and no error. Added an upfront `ValueError`, plus a test
    hand-constructing exactly this malformation and asserting the file stays untouched.
  - `[medium]` `[patch]` Blind Hunter: `RegionShaMismatchError`'s message omitted the file path,
    making a batch/multi-file caller's failure unattributable from the exception message alone.
    Added the path; added a test asserting the path, region name, and both sha values all appear
    in the message (previously only `pytest.raises(RegionShaMismatchError)` was asserted, with no
    message-content coverage at all).
  - `[medium]` `[patch]` Blind Hunter: no test exercised a REAL, non-empty `never_write` guard
    actually blocking a write end-to-end -- every existing test passed `NeverWrite(())`. Added one
    proving `NeverWriteViolation` propagates through `substitute_region` unchanged and the file
    stays untouched.
  - `[low]` `[patch]` Blind Hunter: coverage was asymmetric between the two "only one field
    changes" cases -- a model-version-only test existed but no mirror test for body-only change
    (sha updates, model-version stays fixed). Added one.
  - `[reject]` Blind Hunter: `fmt` is never validated against the format `region` was actually
    parsed with. Matches this whole module group's already-established, deliberate convention
    (`parse.py`/`markers.py`'s own Always bullets: `fmt` is the caller's declared value, passed
    straight through, never sniffed or cross-checked against content) -- not a gap introduced
    here, and `RegionSpan` has no `fmt` field to check against even if this module wanted to.
  - `[reject]` Blind Hunter: no monotonicity check preventing a caller from passing a
    `model_version` OLDER than `region.model_version` (a silent "downgrade"). Real in principle,
    but deciding what version a caller SHOULD write is a policy decision for a higher layer (the
    orchestrator that knows what model version it currently runs), not this primitive's -- the
    epics AC never names this as a constraint, and imposing one here would be inventing scope.
  - `[reject]` Blind Hunter: `test_fs_replace_span_is_called_exactly_once_per_substitution`'s
    exact-payload assertion uses the `\n`-terminator default rather than also covering CRLF.
    Not a coverage gap overall -- CRLF payload construction is already covered by a separate,
    dedicated test (`test_crlf_terminator_is_preserved_verbatim`); one test per concern is the
    established style, not a defect.
  - `[reject]` Blind Hunter: the module docstring's Design Notes discuss "one write vs. two" and
    "copy vs. derive the terminator" at length while a genuinely riskier interaction (sequential
    same-file calls) went undiscussed. Addressed directly above (the high-severity patch) rather
    than rejected outright, but the specific framing -- that the existing Design Notes are
    themselves a defect for defending "uncontested" decisions -- is not: those decisions are the
    story's own two core acceptance criteria, and explaining acceptance-criteria-driven design
    choices is exactly what Design Notes are for.
  - `[reject]` Blind Hunter: docstrings cite sibling-module conventions (`test_seed_fs.py`'s
    monkeypatch precedent, `MarkerError`/`RegionParseError`'s exception shape) not verifiable from
    this diff alone. Both were independently read and confirmed earlier in this same session
    before this story's spec was even drafted -- citing an established, verified convention by
    name is this codebase's normal style, not an unverifiable claim.

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 11
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `new_body` is typed `str` but was never validated before
    `.encode("utf-8")`, so a caller accidentally passing `bytes` (plausible, since this module's
    own dependency `fs.replace_span` takes `new_body: bytes` one layer down) degraded to a bare,
    contextless `AttributeError` instead of a named, attributable error. `fs.replace_span` itself
    already upfront-validates its own `bytes` argument this exact way (a documented Story 7.3
    review finding) -- this patch mirrors that established, one-layer-up precedent: added an
    upfront `TypeError` check in `substitute_region`, a docstring paragraph explaining it, and a
    test (`test_new_body_that_is_bytes_not_str_raises_type_error_before_any_write`) proving it
    fires before any write and leaves the file untouched.
  - `[low]` `[patch]` Blind Hunter: `test_a_real_non_empty_never_write_guard_blocks_the_write_end_to_end`
    imported `NeverWriteViolation` locally inside the test function rather than alongside the
    file's other top-level imports, unlike every other import in the file. Moved to the top-level
    import line.
  - `[reject]` Blind Hunter + Edge Case Hunter (independently, both re-raising the same root
    cause): the `expected_sha` guard cannot catch a stale-offset `RegionSpan` whose `sha` still
    matches (only the byte offsets are wrong), and `fmt` is never cross-checked against the format
    `region` was actually parsed with. Both are exact rediscoveries of findings already triaged in
    the 2026-08-14 pass above (the stale-offset hazard as `[high] [patch]`, resolved via
    documentation + two proof tests because the intent-contract's frozen `-> None` signature rules
    out a runtime-detectable fix; the `fmt`-trust question as `[reject]`, matching this module
    group's already-established convention of trusting caller-declared `fmt` without cross-
    checking it against content, mirrored in `parse.py`/`markers.py`). No new information in
    either rediscovery; the prior pass's reasoning and resolution stand unchanged.
  - `[reject]` Blind Hunter: nothing ties `text` to `path` (a caller could pass mismatched
    `text`/`path`). Already covered by the intent-contract's own `Never` boundary: "No file I/O of
    its own... this module documents the requirement, it does not enforce it, since it never reads
    a file itself" -- a deliberate, already-decided scope boundary, not a gap.
  - `[reject]` Blind Hunter: no protection against `new_body` itself containing region-marker-
    shaped text, which could confuse a later `parse_regions` pass. The intent-contract's `Always`
    boundary already states the general principle in full: "pure byte concatenation has no notion
    of 'special' text" -- the conflict-marker example it names is an instance of that same
    deliberate, blanket design decision, not an exhaustive list of covered cases.
  - `[reject]` Blind Hunter: zero test coverage for `RegionFormat.HASH` (every test uses
    `RegionFormat.HTML`). `substitute_region` treats `fmt` as an opaque pass-through with no
    format-specific branching of its own (it calls `markers.render_begin(fmt, ...)` uniformly);
    format-specific rendering behavior is already covered by Story 8.1's own `markers.py` test
    suite. Re-testing it here would exercise no code path unique to this module, matching this
    story's own established one-test-per-concern style.
  - `[reject]` Blind Hunter: the sha-mismatch tests use a hardcoded `"deadbeef"` rather than a
    "realistic" drifted-but-real sha. Both fire the identical `region.sha != expected_sha` branch
    regardless of whether the mismatched value looks like a real sha -- no additional code path
    would be covered, a cosmetic realism preference only.
  - `[reject]` Blind Hunter: `text.encode("utf-8")` re-encodes the whole file once per
    `substitute_region` call, called out as wasteful by analogy to `parse.py`'s own "avoid
    quadratic re-encoding" discipline. `parse.py`'s discipline is about avoiding a re-encode
    PER LINE inside a scan loop (which would be quadratic); this is one encode per call (linear,
    not quadratic) -- a different situation the cited precedent doesn't actually apply to, and no
    AC or NFR in this story's scope names a performance requirement.
  - `[reject]` Blind Hunter: no test covers an empty `new_body`. The concatenation logic has no
    branch that treats body length or emptiness specially; every existing test already exercises
    the same code path an empty-body test would, so this adds no incremental coverage.
  - `[reject]` Blind Hunter: no test pins which error wins when both the sha-mismatch and
    malformed-span conditions hold simultaneously. Both are validation errors with no documented
    caller-visible ordering contract in the intent-contract; a cosmetic test-coverage nitpick with
    no behavior at stake.
  - `[reject]` Edge Case Hunter: the malformed-span guard only checks
    `region.begin_span[1] > region.body_span[0]`, not that `region.body_span[1] >=
    region.begin_span[0]`, so a differently-malformed hand-constructed `RegionSpan` (e.g.
    `begin_span=(100,110), body_span=(115,50)`) could reach `fs.replace_span` with an inverted
    `[100, 50)` span. Verified against `fs.replace_span`'s own source
    (`src/.../seed/fs.py:271`): it independently enforces `0 <= start <= end <= len(original)` and
    raises `ValueError` before any write for exactly this case. The file stays untouched and an
    error is still raised -- just by the already-existing, already-tested guard one layer down,
    matching this module group's own belt-and-braces layering (this module's own sha-mismatch
    guard is documented as "defense-in-depth" over the caller's fresh-detect-pass guarantee, the
    same relationship `fs.replace_span`'s span check has to this one). Not a real corruption path.
  - `[reject]` Edge Case Hunter: `text.encode("utf-8")` / `new_body.encode("utf-8")` are unguarded
    against a lone-surrogate string raising a bare `UnicodeEncodeError`. No code anywhere in this
    epic's chain (`parse.py`, `markers.py`, `fs.py`, or this module's own docstring) uses
    `errors="surrogateescape"` or otherwise documents producing or accepting non-well-formed
    Unicode; the established precondition throughout is ordinary UTF-8 text. An exceedingly
    unlikely, out-of-precedent input, not named by any AC.

## Design Notes

**Why one combined `fs.replace_span` call, not two.** `begin_span` and `body_span` are two
distinct, non-adjacent-in-content byte ranges (a marker-line terminator sits between them), so a
naive implementation might replace each independently. But `begin_span` always precedes
`body_span` in file order, so replacing the body alone would never invalidate the begin marker's
own offsets — making TWO separate atomic writes technically *possible*. It is still wrong: a
process crash (or any interruption) between the two writes would leave a file with a NEW body but
a STALE begin marker (or vice versa) on disk — a real, observable, on-disk half-merged state,
which is exactly what AR-1 and this epic's Never-boundary on producing conflict-marker-shaped
corruption exist to make structurally impossible. One combined span, one atomic
temp-file-then-rename, means the file is either the old region or the new one, in its entirety,
never a hybrid of both — matching `fs.write`'s own atomicity guarantee for content writes,
extended here to a region substitution's own dual-part payload (marker + body).

**Why the terminator is sliced from `text`, not re-derived.** `parse.py`'s own Design Notes
already establish `body_span` as starting immediately after the begin line's terminator. Rather
than guessing the line-ending style (`\n` vs `\r\n`) from context, slicing
`text.encode("utf-8")[begin_span[1]:body_span[0]]` reads the ACTUAL 1–2 terminator bytes the file
already has and reuses them verbatim — the same "never re-derive what you can read" discipline
`parse.py` itself follows for CRLF/LF parity.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new `test_seed_regions_apply.py`.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (`regions` importing `fs`/`model` is a downward, allowed edge).

## Auto Run Result

Status: done

Summary: implemented `seed/regions/apply.py` -- `substitute_region`, the primitive that combines
Story 8.2's parser and Story 7.3's guarded writer into "replace a region's begin marker and body
in one atomic write." Two review passes now. The first (2026-08-14) converged on a real,
high-severity finding (stale multi-region offsets), fixed via documentation + two proof tests,
plus a defensive malformed-span guard, a message improvement, and coverage additions. A follow-up
fresh review pass (2026-08-13, this pass) re-ran Blind Hunter + Edge Case Hunter against the same
diff from scratch; most findings were rediscoveries of the first pass's already-decided
conclusions or false alarms (one verified against `fs.replace_span`'s own source to confirm its
existing guard already catches the scenario). Two small, genuine gaps survived: `new_body` had no
upfront type validation (mirroring `fs.replace_span`'s own established precedent one layer down),
and a test had a local import that belonged at file scope.

Files changed (this pass, on top of the already-landed first-pass code):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/apply.py` -- added an
  upfront `TypeError` check when `new_body` is not `str`, plus a docstring paragraph explaining it.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` -- added
  `test_new_body_that_is_bytes_not_str_raises_type_error_before_any_write`; moved
  `NeverWriteViolation` from a local test-function import to the file's top-level imports.

Review findings breakdown (this pass): 2 patch (0 high, 0 medium, 2 low -- both applied), 0 defer,
11 reject (two are exact rediscoveries of findings the first pass already triaged and resolved;
one was verified false by reading `fs.replace_span`'s own source -- its independent
`0 <= start <= end <= len(original)` check already catches the scenario one layer down; the rest
are either already covered by the intent-contract's own explicit boundaries, redundant coverage
of already-tested sibling-module behavior, or cosmetic/no-new-code-path nitpicks). See Review
Triage Log above (both dated entries) for full reasoning.

Follow-up review recommended: **false**. This pass's two fixes are a defensive type-validation
addition (mirroring an established precedent) and a test-file import-placement nit -- neither
touches the core byte-splice-and-write algorithm, which two independent review passes have now
left unchanged.

Verification performed (this pass):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -- -k regions_apply` -- 15 passed (up
  from 14), full suite `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3806 passed,
  9 deselected.
- `pixi run -e local-recipes ruff check` scoped to both changed files -- `All checks passed!`.
- `pixi run -e local-recipes pyright` scoped to `regions/apply.py` -- `0 errors, 0 warnings, 0
  informations`.
- `pixi run --frozen -e pyforge-marshal lint-imports --config .../pyproject.toml --no-cache` --
  `Contracts: 3 kept, 0 broken`.
- The Edge Case Hunter's "malformed-span guard incomplete" claim was checked against
  `fs.replace_span`'s actual source (`seed/fs.py:271`) before triage, confirming its own
  `0 <= start <= end <= len(original)` check already rejects the scenario -- not asserted from
  memory.

Residual risks: none blocking. Two independent adversarial review passes have now run against
this module; both real findings across both passes are fixed and regression-tested. A future
`verbs/update.py` orchestrator (S-8.4 onward) inherits a module docstring that already states the
correct multi-region usage pattern, and `substitute_region` now rejects a caller's `bytes`/`str`
mixup with the same clarity `fs.replace_span` already does one layer down.
