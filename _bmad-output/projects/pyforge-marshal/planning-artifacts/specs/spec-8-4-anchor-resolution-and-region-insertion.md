---
title: 'Story 8.4: Anchor resolution and region insertion'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'f19ba4d2e559bcb289f94a54b9804476b3b94fe0'
final_revision: 'ad2608e4b5e475fa6b39ce4499b3e91f6d5bf776'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
difficulty: 'heavy'
---

<intent-contract>

## Intent

**Problem:** Stories 8.2/8.3 can locate and replace an EXISTING region, but nothing yet puts a
region into a file that has never had one -- `marshal seed adopt`'s core "gain the model
content" verb has no primitive for the absent case (epics AC S-8.4).

**Approach:** Add `resolve_anchor` to `parse.py` (pure, byte-offset anchor resolution reusing
the module's own fence-awareness) and `insert_region` to `apply.py` (the write path: calls
`resolve_anchor`, then writes through `fs`), mirroring how S-8.3 combined S-8.2's parser with
S-7.3's writer.

## Boundaries & Constraints

**Always:**
- `resolve_anchor(text: str, fmt: RegionFormat, anchor: tuple[str, ...]) -> AnchorResolution`
  (new frozen dataclass: `offset: int`, `matched: str | None`) in `parse.py`. Tries each literal
  in `anchor` IN ORDER against every line's content (fence-skipped exactly like `parse_regions`'s
  own `fence_aware` gate, reusing its private `_iter_lines`/`_fence_delimiter`/`_closes_fence`).
  The FIRST anchor string with ANY matching line (`content.startswith(anchor_text)`) wins --
  order is a PREFERENCE fallback, not a file-position search -- and `offset` is that line's own
  `line_end` (right after its terminator). The literal sentinel `"<top>"` never searches file
  content: it always resolves, to the byte offset right after a YAML frontmatter block (first
  line exactly `---`, next line exactly `---`, mirroring `core/spec_surface.py`'s established
  convention, reimplemented locally) or to `0` when no such block exists. When nothing in
  `anchor` matches (including no `<top>` present), `matched=None` and `offset=len(text.encode())`
  (EOF, append fallback).
- `insert_region(text: str | None, path: Path, name: str, anchor: tuple[str, ...], body: str, *,
  model_version: ModelVersion, fmt: RegionFormat, repo_root: Path, never_write: fs.NeverWrite) ->
  InsertionResult` (new frozen dataclass: `outcome: InsertionOutcome` (`StrEnum`: `INSERTED`,
  `ALREADY_PRESENT`), `matched: str | None`) in `apply.py`. When `text is not None` (file
  exists): runs `parse_regions(text, fmt)` first -- if `name` is already among the returned
  spans, returns `InsertionResult(ALREADY_PRESENT, matched=None)`, untouched, no write.
  Otherwise calls `resolve_anchor`, renders begin/end marker lines via
  `markers.render_begin`/`render_end` (sha from `markers.region_sha(body)`), writes ONE combined
  payload through exactly one `fs.replace_span(path, offset, offset, payload, ...)` call -- a
  zero-width span, the SAME shared write primitive S-8.3 uses (epic rule: "all writes go through
  the one shared primitive") -- and returns `InsertionResult(INSERTED,
  matched=resolution.matched)`, carrying forward the SAME `matched` `resolve_anchor` already
  computed rather than discarding it. A matched-anchor insertion has no leading blank line; the
  append-fallback (`matched is None`) payload is preceded by one blank line (`"\n"`). When `text
  is None` (file absent): skips detection/resolution and writes the payload -- the rendered
  region alone, nothing else -- via `fs.write(path, payload, ...)` (no existing span to splice
  into), returning `InsertionResult(INSERTED, matched=None)` (no anchor concept applies).
- Every newly rendered marker/body line ends in `"\n"` regardless of the surrounding file's own
  line-ending convention -- this module never re-derives ambient CRLF for BRAND NEW bytes it is
  writing (S-8.3's CRLF guarantee is about existing bytes being replaced, not new ones inserted).
- `body`'s trailing-newline responsibility mirrors `substitute_region`'s `new_body` contract
  (S-8.3): if `body` does not itself end in `"\n"`, the rendered end-marker line glues onto
  body's own last line -- this primitive does not append one for the caller.

**Block If:** None -- epics AC plus the already-shipped S-8.2/S-8.3 primitives fully specify
this story; no decision here requires human input.

**Never:**
- No plan-artifact construction or serialization (`.marshal/plan.json`, AD-57) -- Epic 9's
  surface. This story only returns which anchor matched (or `None` for the append fallback) so
  a future plan layer can name it, satisfying the AC's "the chosen anchor... is named in the
  plan" one level down.
- No import of `model.manifest`'s `Region`/`ManifestEntry` types -- `manifest.py` already
  imports FROM `regions.markers`, so importing manifest types back into `regions/` would create
  a package cycle. `insert_region`/`resolve_anchor` take plain `name`/`anchor` params, matching
  `substitute_region`'s own dependence on `model.version` only, never `model.manifest`.
- No marker-deletion / opt-out handling (S-8.5's surface).
- Never calls `Path.write_text`/`open(..., "w")` -- only `fs.replace_span`/`fs.write` (P-01).
- No re-verification that `text is None` truly means `path` is absent, or that non-`None` `text`
  is fresh -- trusts the caller exactly like `substitute_region` trusts its own `text`/`region`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First anchor matches | A line starts with `anchor[0]` | Insert immediately after that line; `matched == anchor[0]` | No error |
| Earlier anchor absent, later matches | `anchor[0]` absent, `anchor[1]` present | Insert after `anchor[1]`'s line; `anchor[0]` is ignored entirely (order = preference, not position) | No error |
| No anchor matches, no `<top>` | None of `anchor` found in the file | Region appended at EOF, preceded by a blank line; `matched is None` | No error |
| `<top>` with frontmatter | Text starts with a `---`...`---` block | Insertion immediately after the closing `---` line | No error |
| `<top>` without frontmatter | Text does not start with `---` | Insertion at byte 0 | No error |
| Anchor text only inside a fence | The one line starting with `anchor[i]` sits inside a fenced block (html fmt) | That line is skipped; resolution falls through to the next anchor or the append fallback | No error |
| Region already present | `parse_regions(text, fmt)` already returns a span named `name` | No write attempted | Returns `ALREADY_PRESENT` |
| File absent | `text is None` | New file created via `fs.write`, containing only the rendered region | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- MODIFY: add
  `AnchorResolution` and `resolve_anchor`, reusing existing private fence/line-iteration helpers.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/apply.py` -- MODIFY: add
  `InsertionOutcome`, `InsertionResult`, and `insert_region`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- REFERENCE
  ONLY (Story 8.1): `render_begin`, `render_end`, `region_sha`, `RegionFormat`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` (existing) --
  REFERENCE for `parse_regions`, `RegionSpan` (used by `insert_region`'s already-present check).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- REFERENCE ONLY (Story
  7.3): `replace_span`, `write`, `NeverWrite`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/version.py` -- REFERENCE
  ONLY: `ModelVersion`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` -- MODIFY: add
  `resolve_anchor` coverage for every I/O Matrix row involving anchor resolution.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` -- MODIFY: add
  `insert_region` coverage for every I/O Matrix row involving the write path.

## Tasks & Acceptance

**Execution:**
- [x] `seed/regions/parse.py` -- add `AnchorResolution` (frozen dataclass: `offset: int`,
  `matched: str | None`) and `resolve_anchor(text, fmt, anchor) -> AnchorResolution`: ordered
  literal-prefix search with fence-awareness, `<top>` frontmatter sentinel, EOF fallback.
- [x] `seed/regions/apply.py` -- add `InsertionOutcome` (`StrEnum`: `INSERTED`,
  `ALREADY_PRESENT`), `InsertionResult` (frozen dataclass: `outcome`, `matched: str | None`), and
  `insert_region(text, path, name, anchor, body, *, model_version, fmt, repo_root, never_write)
  -> InsertionResult`: already-present short-circuit, anchor-resolved splice via `fs.replace_span`
  (zero-width span, carrying the resolved `matched` forward), absent-file create via `fs.write`.
- [x] `tests/unit/test_seed_regions_parse.py` -- cover every `resolve_anchor` I/O Matrix row,
  including the anchor-order-is-preference case and both `<top>` cases.
- [x] `tests/unit/test_seed_regions_apply.py` -- cover every `insert_region` I/O Matrix row,
  including already-present idempotence and absent-file creation, asserting `fs.replace_span`/
  `fs.write` is called exactly once per insertion (never both, never zero on the write paths).

**Acceptance Criteria:**
- Given a hybrid artifact with an ordered `anchor[]` and the region absent, when `insert_region`
  runs, then insertion occurs immediately after the first matching anchor line.
- Given no anchor matches, then the region is appended at end of file preceded by a blank line.
- Given an anchor-shaped line inside a fenced code block, then it is never treated as a match.
- Given the special anchor `<top>`, then insertion occurs after any YAML frontmatter block, or
  at byte 0 when there is none.
- Given a file that already has the region, when `insert_region` runs, then it is a no-op that
  returns `ALREADY_PRESENT`.
- Given an absent file, when `insert_region` runs, then it is created containing only the
  rendered region.
- Given any successful insertion, then the resolved anchor (or `None` for the append fallback)
  is returned so a future plan layer can surface it.

## Spec Change Log

- 2026-08-13 (step-03, pre-review): `insert_region`'s return type was widened from a bare
  `InsertionOutcome` to a new `InsertionResult(outcome, matched)` dataclass. The initial draft's
  Boundaries section specified only `-> InsertionOutcome`, but this section's own last
  Acceptance Criterion ("the resolved anchor... is returned so a future plan layer can surface
  it") required the `matched` value `resolve_anchor` already computes to actually be returned,
  not discarded. Caught during step-03's own Tasks & Acceptance verification, before any review
  pass. KEEP: the rest of the design (zero-width-span reuse, already-present short-circuit,
  anchor-order-is-preference) is unaffected and should survive unchanged.

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 1, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `resolve_anchor`'s literal-prefix match has no awareness of already-parsed region spans, so
    an anchor's text appearing as ordinary content inside an UNRELATED existing region's body
    would splice a brand-new region's markers into the middle of that region -- the exact
    nested/overlapping corruption AR-1 forbids, just discovered one write later, on disk.
    Confirmed real by direct test construction. Fixed: `insert_region` now raises a new
    `AnchorInsideExistingRegionError` before any write when the resolved offset falls strictly
    inside an already-existing region's own span, reusing the `existing` list it already computed
    for its own already-present check (no extra parse cost). Two new tests: the collision case,
    and the boundary case (an anchor immediately before/after an existing region, which must
    still be allowed).
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (three symptoms of one root cause):
    the EOF-fallback's naive `f"\n{payload}"` prefix produces ZERO visible blank lines when
    `text` has no trailing newline (contradicting the documented/AC-mandated "preceded by a
    blank line"), TWO blank lines when `text` already ends in one, and a spurious leading blank
    line for a genuinely-empty (0-byte) existing file. Fixed: new `_eof_append_prefix(text)`
    helper computes the correct prefix from `text`'s own trailing bytes (never adding when
    `text` is empty, matching the absent-file path's "region alone, nothing else" contract).
    Three new tests, one per symptom.
  - `[low]` `[patch]` Blind Hunter: `resolve_anchor` silently treated an unterminated fenced
    code block as "everything after it is fence-interior, no match", unlike `parse_regions`'s
    hard `RegionParseError` for the identical condition -- currently masked in `insert_region`
    only because it always calls `parse_regions` first (which already raises), but
    `resolve_anchor` is independently public. Fixed: `resolve_anchor` now raises the same
    `RegionParseError`, mirroring `parse_regions`'s own message shape. One new test.
  - `[low]` `[patch]` Blind Hunter: the module docstring's claim that `insert_region` "imports
    `model.manifest`'s types nowhere" was asserted only in prose, with nothing to catch a future
    regression. Fixed: added a new `lint-imports` contract forbidding
    `pyforge.marshal.seed.regions -> pyforge.marshal.seed.model.manifest`, matching this repo's
    own established "meta-test over docstring-only claims" convention (AD-61's `fs.py`
    precedent). A lighter-weight companion meta-test (`test_regions_no_manifest_import.py`) owns
    the new contract's shape assertion, mirroring AD-3/AD-4's own (not AD-9's heavier
    dynamic-import-evasion-scanning) precedent, since this is a layering-cleanliness concern, not
    a security boundary. Bumped `test_ad3_ad4_import_linter.py`'s total-contract-count guard
    3 -> 4.
  - `[reject]` Blind Hunter: matched-anchor insertions get no blank line on either side while the
    EOF-fallback gets exactly one, with (per the finding) no stated justification. This IS the
    literal epics AC: "insertion occurs immediately after the first matching anchor line" (no
    gap) vs. "when no anchor matches... appended at end of file preceded by a blank line" --
    not an oversight, a directly-specified requirement.
  - `[reject]` Blind Hunter: `insert_region`'s own write path is only exercised with
    `RegionFormat.HTML`; HASH/SLASHSTAR are untested for the primitive itself. Exact rediscovery
    of a finding Story 8.3's own review already triaged and rejected for `substitute_region`
    (`fmt` is passed straight through to `render_begin`/`render_end`/`region_sha` with no
    format-specific branching in this module's own logic; format-specific rendering is already
    covered by Story 8.1's `markers.py` suite) -- the identical reasoning applies here unchanged.
  - `[reject]` Blind Hunter: no CRLF test for `resolve_anchor`/`insert_region`. Both share the
    EXISTING, already CRLF-tested `_iter_lines` machinery (`parse_regions`'s own suite proves
    CRLF/LF/CR parity for that shared primitive) and add no NEW terminator-sensitive logic of
    their own -- they only consume the `line_end` offsets `_iter_lines` already produces. A
    dedicated CRLF test would exercise no code path not already covered, matching the "redundant
    coverage of already-tested sibling-module behavior" rejection pattern from Story 8.3's own
    review.
  - `[reject]` Blind Hunter + Edge Case Hunter (independently, same root cause): the
    already-present check's `parse_regions(text, fmt)` call lets ANY structural defect anywhere
    in the file -- not just something related to the region being inserted -- block the
    insertion. This is the epic's own established fail-safe posture (AR-1/P-07: "trusts the plan
    that was already built from a fresh detect pass", fail closed on ambiguity), the same
    relationship `substitute_region`'s sha-mismatch guard already has to a malformed caller
    input -- not an oversight.
  - `[reject]` Blind Hunter: `InsertionResult.matched` is `None` for two different situations
    (already-present vs. EOF-fallback-after-resolution). Already explicitly documented in the
    dataclass's own docstring, and the `outcome` field sitting right beside `matched` is exactly
    the tag a caller checks first to disambiguate -- an intentional sum-type-like shape, not a
    footgun.
  - `[reject]` Blind Hunter: the already-present check is name-only, not content-verifying, so a
    caller's differently-intended new body is silently discarded when a same-named region
    already exists. This is precisely what this story's own AC (and the epics AC it traces to)
    requires, unconditionally: "inserting into a file that already has the region is a no-op
    that reports already-present" -- not a gap, the specified behavior.
  - `[reject]` Blind Hunter: no shared-fixture parity test proves `_frontmatter_end` (this
    module) and `core/spec_surface.py::parse_declared_surface` (the convention it mirrors) agree
    on the same inputs. Both are already independently, fully tested against their OWN specified
    behavior; a cross-module coincidence test would assert an implementation detail neither this
    story's AC nor the Design Notes' stated rationale (deliberately NOT sharing code, to keep
    `regions/` dependency-light) requires to hold.
  - `[reject]` Edge Case Hunter: an anchor tuple containing an empty string `""` matches every
    non-fenced line trivially via `str.startswith("")`. The ONLY real production path for
    constructing an anchor tuple (`model.manifest.Region.__post_init__`) already rejects blank
    anchor strings before `resolve_anchor`/`insert_region` ever see one; a caller hand-constructing
    a malformed tuple to bypass that model-layer guard is the same class of "hand-constructed
    malformed input" Story 8.3's own review already declined to re-validate at this primitive
    layer (established convention: trust caller-supplied, model-validated shapes).

### 2026-08-13 — Follow-up review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 1, low 2)
- defer: 0
- reject: 7
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `_eof_append_prefix`'s fixed `"\n\n"` suffix check never recognized a CRLF file's own
    trailing blank line (`"...\r\n\r\n"`), so a CRLF file already ending in a blank line got a
    SECOND, LF-only blank line stacked on top -- violating the function's own documented "never
    two" guarantee and mixing line-ending styles in the output. Confirmed by direct execution.
    Fixed: new `_strip_one_terminator` helper detects a trailing blank line by stripping line
    terminators (`\r\n`, `\n`, `\r`) one at a time rather than a fixed LF-only suffix check --
    terminator-agnostic detection, while the separator itself (once judged needed) stays plain
    `"\n"`/`"\n\n"` per the module's existing "brand-new bytes never re-derive ambient CRLF"
    convention. Two new tests (single CRLF terminator, already-blank CRLF ending).
  - `[medium]` `[patch]` Edge Case Hunter: `resolve_anchor` had no guard for
    `RegionFormat.SLASHSTAR`, unlike `parse_regions`'s own eager `parse_marker_line(fmt, "")`
    validation -- silently ran ordinary, non-fence-aware matching for a reserved, unimplemented
    format instead of raising. Masked in `insert_region` only because it always calls
    `parse_regions` first (which already raises for this same `fmt`), but `resolve_anchor` is
    independently public -- the exact same category of gap the FIRST review pass already fixed
    once for the unterminated-fence case. Fixed: `resolve_anchor` now calls
    `parse_marker_line(fmt, "")` eagerly, mirroring `parse_regions`'s own validation trick
    exactly. One new test.
  - `[low]` `[patch]` Blind Hunter: a stale comment in `test_ad3_ad4_import_linter.py` (left
    over from the first pass's 3->4 contract-count rename) still read "The '3 kept' contract
    COUNT is separately enforced by test_pyproject_declares_exactly_three_contracts" -- both the
    count and the function name it pointed to were wrong. Fixed: updated to "4 kept" /
    `test_pyproject_declares_exactly_four_contracts`.
  - `[low]` `[patch]` Blind Hunter (two findings, one root cause): (1) two insertions anchored to
    the same still-present anchor place the second BEFORE the first (nearest-anchor-first, not
    accumulating in call order) with no documentation or test: (2) the module's own "stale
    offsets across repeated calls" hazard paragraph (documented for `substitute_region`) was
    never restated for `insert_region`. Confirmed by direct execution that (1) reproduces even
    with a correct re-detect-between-calls pattern -- it is the literal, spec-mandated
    consequence of "insertion occurs immediately after the first matching anchor line" applied
    twice, not a stale-offset hazard. Fixed: added a module-docstring paragraph documenting this,
    mirroring the existing "Substituting more than one region" precedent's shape. One new
    regression test proving the documented order.
  - `[reject]` Blind Hunter: `test_ad3_ad4_import_linter.py` and the new
    `test_regions_no_manifest_import.py` each independently shell out to `lint-imports` and
    assert the same `0 broken` regex. Deliberate, already-stated design: the new file's own
    docstring says it "Mirrors `test_ad3_ad4_import_linter.py`'s own approach" -- each meta-test
    file independently proving the FULL `lint-imports` run passes (not just its own contract) is
    a test-isolation tradeoff already established by this file's own existing pattern, not a new
    problem this story introduced.
  - `[reject]` Blind Hunter: `anchor` is accepted with no validation (a blank string matches
    every line via `str.startswith("")`). Exact rediscovery of a finding the FIRST review pass
    already rejected for the identical reason: the only real production path
    (`model.manifest.Region.__post_init__`) already rejects blank anchor strings before
    `resolve_anchor`/`insert_region` ever see one (established convention: trust caller-supplied,
    model-validated shapes).
  - `[reject]` Blind Hunter: `anchor` is silently ignored on the absent-file (`text is None`)
    path, yet the signature still requires every caller to supply one. This is precisely what
    this story's own intent-contract states: "When `text is None` (file absent): skips
    detection/resolution... (no anchor concept applies)" -- documented, spec-mandated behavior,
    not a gap.
  - `[reject]` Blind Hunter: up to three full passes over `text` per `insert_region` call
    (`parse_regions`, `resolve_anchor`'s own scan, and `_frontmatter_end`'s scan when `<top>` is
    reached). A constant-factor efficiency observation, not the quadratic-per-line re-encoding
    the module's own stated complexity concern is about; fixing it would require a
    cross-function refactor beyond "trivially fixable without human input," and nothing in this
    repo's usage (small config/doc files) suggests it is a real bottleneck.
  - `[reject]` Blind Hunter: no shared-fixture parity test proves `_frontmatter_end` (this
    module) and `core/spec_surface.py::parse_declared_surface` agree on the same inputs. Exact
    rediscovery of a finding the FIRST review pass already rejected for the identical reason:
    both are independently, fully tested against their own specified behavior; a cross-module
    coincidence test would assert an implementation detail neither this story's AC nor the
    Design Notes' stated rationale (deliberately not sharing code) requires to hold.
  - `[reject]` Blind Hunter: `InsertionResult.matched is None` is ambiguous across THREE
    situations now (already-present, EOF-fallback, absent-file-create) without also checking
    `outcome`. Extends a finding the FIRST review pass already rejected for two of the three
    situations: already explicitly documented in the dataclass's own docstring, and `outcome`
    sitting right beside `matched` is exactly the tag a caller checks first to disambiguate -- the
    same reasoning applies unchanged to the third situation.
  - `[reject]` Blind Hunter: the new import-linter contract's justifying `pyproject.toml` comment
    says the docstring assertion it points to "already" exists, as if it predates the contract,
    when both were authored together in the same diff. A rhetorical nitpick about phrasing with
    no functional or clarity consequence -- the statement is accurate regardless of authorship
    order (the docstring paragraph does exist in the same file, so the contract does give it
    teeth).

## Design Notes

**Anchor order is a preference fallback, not a file-position search.** AD-56's own example --
`["## The tiers", "# CLAUDE.md", "<top>"]` -- only makes sense this way: `<top>` structurally
sits at the very start of any file, so if matching were "first line in file order across all
anchors," `<top>` would always win regardless of its position in the list, defeating the whole
point of listing it last as a guaranteed-fallback. Trying each anchor in turn and stopping at
the first one with any match at all is the only reading under which declaring a MORE preferred,
possibly-absent anchor before a guaranteed one is meaningful.

**`<top>`'s frontmatter detection is reimplemented locally, not imported.** `core/spec_surface.py`
already parses the identical `---`/`---` convention, but it lives in `pyforge.marshal.core` --
importing it here would add `regions`'s first dependency on that package for ~10 lines of
well-established, easily-mirrored logic. `regions/` is deliberately dependency-light (only
`model.version` today); duplicating the short, stable convention keeps that true.

**Insertion reuses `fs.replace_span` via a zero-width span.** `fs.replace_span(path, offset,
offset, payload, ...)` satisfies its own `0 <= start <= end <= len(original)` contract with
`start == end`, so insertion needs no new primitive in `fs.py` -- it is "substitution of an
empty span," using the exact write path S-8.3 already proved safe.

**Why `insert_region` (not a future plan layer) owns the already-present check.**
`substitute_region` (S-8.3) explicitly defers idempotence to a future plan layer (AD-60), since
its caller already knows the region exists from its own fresh detect pass. `insert_region`'s own
epics AC states the opposite for THIS primitive: "inserting into a file that already has the
region is a no-op that reports already-present" is named as this function's own behavior, not a
future layer's -- so, unlike S-8.3, the already-present check lives here.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the extended `test_seed_regions_parse.py`/`test_seed_regions_apply.py`.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (no new edge from `regions` to `model.manifest` or `marshal.core`).

## Auto Run Result

Status: done

Summary: implemented `resolve_anchor` (`seed/regions/parse.py`) and `insert_region`
(`seed/regions/apply.py`) -- the primitive that puts a managed region into a file that has never
had one, at a declared anchor (ordered preference list, fence-aware, `<top>` frontmatter
sentinel) or appended at EOF, with an already-present idempotence check. Two review passes: the
first found and fixed a real region-corruption hazard plus three smaller gaps; this follow-up
pass (triggered by the first pass's own `followup_review_recommended: true`) found and fixed a
real CRLF blank-line corruption bug plus three smaller gaps. Nothing in either pass required a
spec amendment or code re-derivation.

**Follow-up pass note:** this pass's worktree branch had been reset to an ancestor commit by the
run's own attempt-2 re-arm, losing the first pass's already-committed, already-verified work
(commits for Stories 8.1-8.4) from the active ref -- though every commit remained fully intact
and reachable via `attempt-preserve/20260813-094919-bfcb-95ea70c9` (a strict fast-forward
ancestor of `26102ea12c`, confirmed via `git merge-base --is-ancestor`). Recovered
non-destructively via `git merge --ff-only` to the preserved commit (which equalled the prior
pass's own recorded `final_revision` exactly) before any review work began -- no commits lost, no
re-implementation, nothing to reconcile.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- added
  `AnchorResolution`, `resolve_anchor`, `_frontmatter_end`; `resolve_anchor` now raises
  `RegionParseError` on an unterminated fence (review fix).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/apply.py` -- added
  `InsertionOutcome`, `InsertionResult`, `insert_region`, `_render_region`; review fixes added
  `AnchorInsideExistingRegionError` (corruption guard) and `_eof_append_prefix` (correct
  blank-line logic); `insert_region`'s return type was widened from a bare `InsertionOutcome` to
  `InsertionResult` during step-03's own Tasks & Acceptance verification (before any review
  pass) so the resolved anchor is actually returned, per this spec's own last AC.
- `src/shared/packages/pyforge-marshal/pyproject.toml` -- added a 4th import-linter contract
  forbidding `regions -> model.manifest` (review fix).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` -- 16 new tests:
  every `resolve_anchor` I/O Matrix row plus the unterminated-fence review fix.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` -- 18 new tests:
  every `insert_region` I/O Matrix row plus the corruption-guard and blank-line review fixes.
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` -- bumped the
  total-contract-count guard 3 -> 4.
- `src/shared/packages/pyforge-marshal/tests/meta/test_regions_no_manifest_import.py` -- NEW,
  owns the 4th contract's own shape assertion (lighter-weight than AD-9's precedent -- see that
  file's own docstring for why).

**Follow-up pass files changed (2026-08-13):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/apply.py` -- added
  `_strip_one_terminator`; `_eof_append_prefix` rewritten to detect an existing trailing blank
  line in a terminator-agnostic way (CRLF fix); module docstring gained a paragraph documenting
  repeated-insertion-at-the-same-anchor ordering.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` --
  `resolve_anchor` now calls `parse_marker_line(fmt, "")` eagerly (SLASHSTAR guard fix),
  mirroring `parse_regions`'s own validation.
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` -- fixed a
  stale "3 kept" / old-test-name comment left over from the first pass's rename.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` -- 3 new tests: two
  CRLF EOF-append cases, one repeated-same-anchor ordering regression test.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` -- 1 new test: the
  SLASHSTAR guard.

Review findings breakdown -- first pass: 4 patch (1 high, 1 medium, 2 low -- all applied), 0
defer, 8 reject. Follow-up pass: 4 patch (1 high, 1 medium, 2 low -- all applied), 0 defer, 7
reject (matched against established precedent: AC-literal requirements, the FIRST pass's own
prior review rejections re-applied where the identical finding recurred, or
already-explicitly-documented deliberate design). See Review Triage Log above for full reasoning
per finding, both passes.

Follow-up review recommended: **false**. This pass's fixes are narrower in blast radius than the
first pass's: the CRLF fix is confined to one already-isolated helper (`_eof_append_prefix`,
used only by the EOF-append subpath, not the matched-anchor path) with 2 new regression tests;
the SLASHSTAR guard is a single eager-validation line mirroring an already-established pattern in
the SAME file; the remaining two patches are pure documentation/comment fixes with zero behavior
change. No new exception type was introduced on the primary write path (unlike the first pass's
`AnchorInsideExistingRegionError`), and every fix is covered by a new, passing regression test.

Verification performed (follow-up pass, 2026-08-13):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3845 passed, 9 deselected (full
  suite, including this pass's 4 new tests).
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- 186 errors,
  identical to the stated baseline (exact match, zero new categories).
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- 596 errors, verified
  identical to a sibling untouched worktree's count for the SAME whole-package scope (a
  pre-existing, worktree-independent gap: pyright cannot resolve `pyforge.marshal.*` absolute
  imports from files under `tests/`, outside the package's own `src/` root, in this env,
  regardless of story) -- no growth. Rescoped to the prior pass's own file set (both changed
  source files plus the new meta-test file, none of which sit outside `src/` or import
  `pyforge.marshal`) -- `0 errors, 0 warnings, 0 informations`, matching the prior pass exactly.
- `pixi run --frozen -e pyforge-marshal lint-imports --config .../pyproject.toml --no-cache` --
  `Contracts: 4 kept, 0 broken`.
- Both adversarial review subagents (Blind Hunter, Edge Case Hunter) ran independently, without
  shared context, against the full diff since `baseline_revision` (both passes' changes
  combined, per this workflow's own diff-construction rule).

Residual risks: none blocking. Same first-pass residuals stand (`AnchorInsideExistingRegionError`
scope, future `verbs/adopt` inheriting `InsertionResult`). New from this pass: the CRLF fix
covers `\r\n`/`\n`/`\r` terminators individually but not an INTERNALLY MIXED file (e.g. some
lines CRLF, others LF) -- `_strip_one_terminator` only inspects the file's own trailing bytes, so
a mixed-terminator file's blank-line detection follows whatever terminator its LAST line
happens to use, which is the same "trust the file's own ambient convention, don't normalize it"
posture this module already takes everywhere else (never attempts CRLF/LF reconciliation across a
whole file), not a new gap this fix introduces.
