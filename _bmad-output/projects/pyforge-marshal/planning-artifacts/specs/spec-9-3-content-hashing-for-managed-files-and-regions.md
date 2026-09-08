---
title: 'Story 9.3: Content hashing for managed files and regions'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '8a2fcdb7971c2b48be886f3c92e2d40405205e99'
final_revision: '1d078897800b6d6346363148b17d290997cd1f84'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 9's detect stage classifies artifacts structurally (S-9.2) but never compares
actual content against what state recorded, so a hand-edited managed file or region is
indistinguishable from an untouched one -- FR-86's refusal has no signal to refuse on.

**Approach:** Add `seed/detect/hashes.py`: one line-ending-normalizing content-hash function
shared by both whole-file and region-body hashing, plus two comparison functions that turn a
mismatch (or an unrecorded-but-present artifact) into a HARD `Finding`.

## Boundaries & Constraints

**Always:**
- One hash algorithm covers both whole files and region bodies: sha256 over
  line-ending-normalized (CRLF and lone CR both collapse to LF) UTF-8 bytes, truncated to 8
  lowercase hex characters -- the same shape as `regions.markers.region_sha`, defined locally
  rather than delegating to it because `region_sha` hashes its argument raw, with no
  normalization (S-8.1's own scope never reasoned about CRLF).
- Region hashing operates on `RegionSpan.body_span` bytes only --
  `text.encode("utf-8")[start:end].decode("utf-8")`, the exact slice operation S-8.3's
  substitution performs and `test_seed_regions_parse.py`'s own `_slice` helper proves -- never
  the marker lines, never the rest of the file.
- `check_managed_file`/`check_managed_region` return `Finding | None`: `None` when the computed
  hash equals `recorded_sha`; a HARD `managed-file-modified` / `managed-region-modified`
  `Finding` (via `Finding.new`) for any mismatch, INCLUDING `recorded_sha is None` (present on
  disk but never recorded in state -- "adopted out-of-band", FR-86's own "not silently accepted"
  case).
- This module performs no I/O: every function takes already-read text (`str`) and an
  already-parsed `RegionSpan`/`recorded_sha` -- reading the file and resolving the target path
  stay the caller's job (mirrors S-9.1/S-9.2's own purity).

**Block If:** None -- FR-106/FR-86/P-07 and S-8.1/S-8.2's existing shapes (`region_sha`'s
algorithm, `RegionSpan.body_span`'s byte-offset contract) fully specify the hashing/comparison
behavior; nothing here requires human input.

**Never:**
- No `.marshal/seed-state.yml` read -- `state/store.py` does not exist yet (a later epic);
  `recorded_sha` is always a caller-supplied parameter, never read from disk here (mirrors
  S-9.2's own "no state-store dependency" precedent).
- No `ArtifactState`/`Classification` construction or `inventory.py` import -- hashing is
  orthogonal to structural classification (S-9.2's own layer); this story only adds the
  hash-comparison primitive a later story (S-9.6) wires in.
- No `generated-derived` staleness checking -- that is `derived-stale`, a different
  `FindingType` and a different mechanism (recomputation, not a recorded-hash comparison), out
  of this story's "managed files and regions" scope.
- No hash comparison anywhere under `seed/apply/` (P-07) -- asserted by a meta-test scanning
  `apply/` for an import of this module or of `hashlib` directly.
- No re-implementation of `region_sha`'s algorithm shape at a *different* truncation length or
  digest -- 8-hex-sha256 stays the one convention (AD-58's `body_sha` field name implies one
  hash format across whole files and region bodies).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| File hash matches | current text hashes to `recorded_sha` | `check_managed_file` returns `None` | No error |
| File hash mismatches | current text hashes to a different value | HARD `managed-file-modified` Finding naming `path` | No error |
| File adopted out-of-band | `recorded_sha=None`, file present | HARD `managed-file-modified` Finding (not silently accepted) | No error |
| CRLF checkout, same content | text uses `\r\n`; `recorded_sha` computed from the `\n`-authored original | `check_managed_file` returns `None` (no false positive) | No error |
| Region hash matches | region body hashes to `recorded_sha` | `check_managed_region` returns `None` | No error |
| Region hash mismatches | region body content changed | HARD `managed-region-modified` Finding naming `path` and region | No error |
| Region adopted out-of-band | `recorded_sha=None`, region present | HARD `managed-region-modified` Finding | No error |
| Content outside the region changed | body unchanged, surrounding file text edited | `check_managed_region` still returns `None` (body-only hashing) | No error |
| Empty region body | `body_span` start == end (adjacent markers) | Hashes the empty string deterministically, no crash | No error |
| Multi-byte UTF-8 in body | body contains non-ASCII characters near marker boundaries | `region_body_text` slices/decodes correctly | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/hashes.py` -- NEW, this
  story's Surface: `normalize_line_endings`, `hash_content`, `region_body_text`,
  `check_managed_file`, `check_managed_region`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_hashes.py` -- NEW, covers the
  I/O Matrix.
- `src/shared/packages/pyforge-marshal/tests/meta/test_p07_no_hash_comparison_in_apply.py` --
  NEW, AST-scan meta-test asserting `seed/apply/` never imports this module or `hashlib`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py` -- reference
  only: `Finding`, `FindingType`, `Severity` consumed for the two check functions' return value.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/parse.py` -- reference
  only: `RegionSpan` consumed for `region_body_text`/`check_managed_region`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- reference
  only: `region_sha`'s algorithm shape (sha256 truncated 8-hex) is matched, not imported.
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad19_no_adapter_branch.py` -- reference
  only: the AST-scan-plus-self-test technique the new meta-test mirrors.

## Tasks & Acceptance

**Execution:**
- [x] `seed/detect/hashes.py` -- add `normalize_line_endings(text)` and `hash_content(text)` (8-hex
  sha256 over normalized UTF-8 bytes) -- the one hash algorithm both whole-file and
  region-body hashing share.
- [x] same file -- add `region_body_text(text, span) -> str`, extracting `span.body_span` bytes
  via the S-8.2-proven UTF-8 byte-slice.
- [x] same file -- add `check_managed_file(path, current_text, recorded_sha) -> Finding | None`
  and `check_managed_region(path, text, span, recorded_sha) -> Finding | None`, both returning
  a HARD Finding on mismatch or when `recorded_sha is None`.
- [x] `tests/unit/test_seed_detect_hashes.py` -- cover every I/O Matrix row.
- [x] `tests/meta/test_p07_no_hash_comparison_in_apply.py` -- AST-scan `seed/apply/` for an
  import of `detect.hashes` or of `hashlib`; self-test with a synthetic violation (mirrors
  `test_ad19_no_adapter_branch.py`'s own technique).

**Acceptance Criteria:**
- Given a managed file or managed region whose current content hash matches its recorded body
  sha, when checked, then no `Finding` is returned.
- Given a mismatch (including an unrecorded/`None` sha for a present artifact), when checked,
  then a HARD `managed-file-modified` or `managed-region-modified` `Finding` is returned naming
  the artifact's path.
- Given identical content checked out with CRLF vs LF line endings, when hashed, then both hash
  to the same value.
- Given a region body unchanged but content outside the region edited, when the region is
  checked, then the result is unaffected (body-only hashing).
- Given `seed/apply/`'s source, when the P-07 meta-test scans it, then it contains no import of
  this module or of `hashlib`.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass (fresh pass, spec status was `done`)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 0
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: `test_p07_no_hash_comparison_in_apply.py`'s
    `_hash_import_violations` flagged an import nested inside `if TYPE_CHECKING:` as a P-07
    violation even though it never executes at runtime. Added `_is_type_checking_test` plus a
    `check`/`visit` split that skips only the `if` body (never its `else:` branch, proven by a new
    regression test).
  - `[medium]` `[patch]` Edge Case Hunter: the same detector's `ImportFrom` branch only matched an
    alias literally named `hashes`, so `from ..detect import *` (whose alias name is `"*"`)
    bypassed the guard entirely. Widened the match to `alias.name in ("hashes", "*")`; added a
    regression test. Combined the resulting `if`/`elif` into one `if` (a `SIM114` ruff finding the
    edit introduced) to hold ruff at its existing 187-error baseline instead of adding a fourth
    instance of a new category.
  - `[low]` `[patch]` Blind Hunter: no test routed an empty artifact through the full
    `check_managed_file` path (only `hash_content("")` and the region-body case were covered in
    isolation). Added `test_check_managed_file_on_empty_content_does_not_crash`.
  - `[low]` `[patch]` Blind Hunter: the `hash_content`/`region_sha` parity test exercised only the
    CRLF normalization case, not the lone-CR case. Extended it to assert both.
  - `[low]` `[patch]` Blind Hunter: `test_check_managed_region_returns_hard_finding_on_mismatch`
    asserted a loose `"tiers" in finding.message` substring, which would pass even if unrelated
    formatting regressed. Tightened to `finding.message.startswith("AGENTS.md#tiers: ")`.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter (recurrence): `region_body_text`'s unguarded
    `UnicodeDecodeError` on a `text`/`span` pair that don't correspond -- re-verified, not assumed:
    still caller-precondition misuse with no real call site before S-9.6, exactly the same finding
    the prior review pass already triaged and rejected on scope grounds.
  - `[low]` `[reject]` Edge Case Hunter (x2) + Blind Hunter (recurrence): unnormalized/unvalidated
    `recorded_sha` comparison (exact case-sensitive match; an empty string routes to the ordinary-
    mismatch wording rather than the "adopted out-of-band" wording) -- still the deliberate
    strict-equality convention `_SHA_PATTERN`/`region_sha` establish throughout this package;
    loosening it would mask the state-corruption signal `DW-FU-9-3` already names. Same family as
    the prior pass's rejected shape-validation finding.
  - `[low]` `[reject]` Blind Hunter (recurrence): the AST guard cannot catch a dynamic
    `importlib.import_module(...)` reach -- an explicitly pre-declared, accepted bound stated in
    the meta-test's own docstring, identical to the prior pass's rejection of the same finding.
  - `[low]` `[reject]` Blind Hunter: the 8-hex-sha256 (32-bit) truncation is a collision risk for a
    "deliberate actor" -- rejected: this story's own spec explicitly forbids re-implementing
    `region_sha`'s shape at a different truncation length or digest (AD-58's one-`body_sha`-
    convention predates this story), and the real consumer is accidental-hand-edit drift detection
    in local developer tooling, not an adversarial security boundary.
  - `[low]` `[reject]` Blind Hunter: cross-module documentation claims (about `regions.parse`,
    S-8.2, S-8.3) are unverifiable from this diff alone -- not a code defect, an artifact of the
    reviewing subagent's own diff-only information asymmetry (disregarded per this workflow's own
    triage rule that reviewer context limits don't set findings).
  - `[low]` `[reject]` Blind Hunter: the "independent, no-shared-context" two-reviewer process is a
    bare self-attestation with no verifiable artifact -- meta-commentary about the review process
    itself, not a code defect.
  - `[low]` `[reject]` Blind Hunter: `FindingType.MANAGED_FILE_MODIFIED`/`MANAGED_REGION_MODIFIED`
    aren't defined anywhere in this diff -- verified, not a defect: both are pre-existing members
    in `detect/findings.py` from story 9.1 (out of this diff's scope, confirmed by grep), not an
    undefined-symbol bug.
  - `[low]` `[reject]` Blind Hunter: `normalize_line_endings` unconditionally rewrites literal `\r`
    bytes with no opt-out -- inherited, not invented, from `regions.parse`'s own established
    universal-newline convention (cited in `hashes.py`'s own docstring); this module's target files
    (markdown/config) make embedded literal-CR-as-content implausible.
  - `[low]` `[reject]` Blind Hunter: `recorded_sha`'s own provenance is trusted unconditionally
    (hand-editable alongside the body) -- same family as the sha-comparison finding above and the
    prior pass's rejected shape-validation finding; state provenance is `state/store.py`'s future
    job (`DW-FU-9-3`), out of this pure-comparison module's scope by design.
  - `[low]` `[reject]` Edge Case Hunter: the finding message `f"{path}#{span.name}: ..."` is
    ambiguous if `path` itself contains `#` -- cosmetic free-text only; `Finding.path` already
    carries the unambiguous structured value, matching the prior pass's own rejected
    message-redundancy finding.

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, confirmed live):
    `test_p07_no_hash_comparison_in_apply.py`'s `_hash_import_violations` used a bare
    `module.endswith("detect.hashes")` for the `ast.ImportFrom` case with no `.` package-boundary
    check, so an unrelated module merely ending in those characters (e.g.
    `mypkg.underdetect.hashes`) would false-positive as a P-07 violation. Added
    `_ends_with_dotted_segment` and routed all three violation checks through it; added a
    regression test for the previously-vulnerable shape.
  - `[low]` `[patch]` Blind Hunter: `check_managed_file`/`check_managed_region` duplicated an
    identical five-line mismatch-detail-building block. Extracted `_hash_mismatch_detail`.
  - `[low]` `[patch]` Blind Hunter: nothing documented why `check_managed_region` compares against
    `recorded_sha` and never `span.sha` (the region's own begin-marker-declared value), risking a
    future "simplification" reintroducing a self-referential-forgery bypass. Added a design-note
    paragraph to the docstring.
  - `[low]` `[defer]` Blind Hunter: neither check function validates `recorded_sha`'s shape
    (8 lowercase hex), so a corrupted/malformed state value reports identically to a genuine
    hand-edit rather than routing to `FindingType.STATE_INVALID`. Deferred as `DW-FU-9-3`
    (`state/store.py`, the module that would own shape validation per FR-104, does not exist yet).
  - `[reject]` Blind Hunter: `region_body_text` re-encodes the whole `text` argument on every call
    rather than once per multi-region document -- a real but negligible micro-optimization; this
    module's pure, stateless, per-call function shape is the spec's own explicit design (Always:
    "every function takes already-read text"), not a defect.
  - `[reject]` Blind Hunter: `Finding.message` repeats `path` a second time even though
    `Finding.path` already carries it -- flagged by the reviewer itself as "not incorrect," purely
    cosmetic.
  - `[reject]` Blind Hunter: the P-07 meta-test's real-code parametrization covers only
    `seed/apply/__init__.py` (empty), so its only current proof of life is its own synthetic
    self-tests -- expected and by design for a forward-declared guard added ahead of the code it
    will eventually police (mirrors this same epic's own "enum member before a real call site"
    precedent, e.g. S-9.1's `PRESENT_LEGACY`).
  - `[reject]` Edge Case Hunter: `region_body_text` given a `text`/`span` pair that do not
    correspond (span parsed from different text) could byte-slice out of range or decode invalid
    UTF-8 -- a caller-precondition violation with no real call site yet (S-9.6 is the first
    future consumer); consistent with this package's established "trust an already-parsed input"
    convention.
  - `[reject]` Edge Case Hunter (x2): recommended case/whitespace-tolerant comparison for
    `recorded_sha` -- rejected because every real sha producer in this system (`hash_content`,
    `region_sha`) already only emits lowercase 8-hex, matching `_SHA_PATTERN`'s established
    strict-equality convention throughout this package; loosening comparison here would mask
    exactly the state-corruption signal `DW-FU-9-3` (above) names.
  - `[reject]` Edge Case Hunter: the AST guard cannot catch a dynamic `importlib.import_module(...)`
    reach into `hashlib`/`detect.hashes` -- an explicitly pre-declared, accepted bound already
    stated in the meta-test's own docstring ("best-effort STATIC check... an indirect reach is out
    of scope"), matching the same accepted limitation in this package's other AST-scan meta-tests
    (e.g. `test_ad19_no_adapter_branch.py`).

## Design Notes

**Why `hash_content` does not call `markers.region_sha` directly.** `region_sha(body)` hashes its
argument raw (`sha256(body.encode("utf-8")).hexdigest()[:8]`), with no line-ending normalization
-- correct for S-8.1's own scope (a parser reporting a *declared* sha as-is), but wrong for this
story's CRLF requirement (FR-106): a caller on a CRLF checkout would compute a different hash for
byte-identical logical content, exactly the false positive the epics AC forbids. `hash_content`
therefore normalizes first, then applies the identical sha256-truncated-to-8-hex shape --
matching `region_sha`'s output format (so a state file's `body_sha` field is one convention
either way) without depending on a function whose contract excludes normalization.

**Why `recorded_sha=None` is always a mismatch, never a pass-through.** The naive shape ("no
recorded value means nothing to compare, so accept") is exactly what FR-86's "not silently
accepted" line forbids: an artifact adopted outside Genesis (copied in by hand, or the state
entry lost) is structurally indistinguishable from a legitimately-managed one once it exists on
disk, and treating it as conformant would let hand-authored content pass permanently under the
tool's own attestation.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the two new test files.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect 0 broken contracts.
- `python scripts/spec_surface_reconcile.py` -- expect `OK` after the memlog entry lands.

## Auto Run Result

Status: `done`

**Summary.** Added `seed/detect/hashes.py`: one line-ending-normalizing sha256-truncated-8-hex
content-hash function (`hash_content`) shared by both whole-file and region-body hashing, plus
`check_managed_file`/`check_managed_region` -- pure comparison functions returning `Finding | None`,
emitting a HARD `managed-file-modified`/`managed-region-modified` `Finding` on any mismatch,
including an unrecorded (`None`) state value ("adopted out-of-band," never a silent pass-through,
per FR-86). Region hashing operates on `RegionSpan.body_span` only (S-8.2's byte-offset contract),
never `span.sha` (the region's own editor-controlled begin-marker field, which would be a
self-referential-forgery bypass if used as the comparison target instead of the out-of-band
`recorded_sha`). The module performs zero I/O and has no dependency on the not-yet-built
`state/store.py` -- `recorded_sha` is always a caller-supplied parameter, consistent with S-9.2's
own precedent for this epic's pure detect layer. Across two rounds of independent review (Blind
Hunter + Edge Case Hunter, no shared context each time -- the second round a fresh pass triggered
after this spec's status had already reached `done`), 8 real issues were found and patched (0
high, 2 medium, 6 low), 1 forward-looking design question was deferred, and 16 findings were
rejected as out-of-scope, already-accepted bounds, recurrences of an already-rejected finding, or
non-issues on inspection. `hashes.py` itself has carried zero behavior changes since the first
round's patches -- every fix in the second round landed in the two test files.

**Files changed (cumulative across both rounds):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/hashes.py` -- NEW:
  `normalize_line_endings`, `hash_content`, `region_body_text`, `_hash_mismatch_detail`,
  `check_managed_file`, `check_managed_region`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_hashes.py` -- NEW, 25 tests
  covering every I/O & Edge-Case Matrix row (24 from round 1, +1 new in round 2; round 2 also
  extended 2 existing tests' assertions in place rather than adding new test functions).
- `src/shared/packages/pyforge-marshal/tests/meta/test_p07_no_hash_comparison_in_apply.py` -- NEW,
  AST-scan meta-test (P-07) asserting `seed/apply/` never imports `detect.hashes`/`hashlib`
  (including a wildcard `import *` and skipping `TYPE_CHECKING`-guarded imports), 17 self-tests.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- three spec-surface reconciliation entries (initial landing + two review-pass patches).
- `scripts/.spec-surface-baseline.json` -- re-stamped three times, scoped to this spec only.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- one entry, `DW-FU-9-3` (from round 1;
  round 2 raised no new deferrals).

**Review findings breakdown, round 1:** 3 patched (0 high, 1 medium, 2 low): a real false-positive
bug in the new meta-test's own detector (an unrelated module merely ending in `detect.hashes`
characters with no package-boundary check would have false-flagged as a P-07 violation), a
duplicated mismatch-message block extracted to a shared helper, and a missing design-note
explaining why `span.sha` is deliberately never the comparison target. 1 deferred (`DW-FU-9-3`:
whether a shape-invalid `recorded_sha` should route to `STATE_INVALID` instead of a
content-mismatch finding -- genuinely blocked on a future `state/store.py` story that doesn't
exist yet). 6 rejected: a negligible micro-optimization, a cosmetic message redundancy, two
pre-declared-and-accepted static-analysis bounds, and two comparison-strictness suggestions that
would mask the exact corruption signal the deferred entry names.

**Review findings breakdown, round 2 (fresh pass, triggered because this spec's status had
reached `done`):** 5 patched (0 high, 2 medium, 3 low): two real P-07 meta-test detector gaps --
a `TYPE_CHECKING`-guarded import false-positive, and a wildcard `from ..detect import *` bypass
the alias-name-only check missed entirely -- plus three small test-precision additions (an
end-to-end empty-content case for `check_managed_file`, a lone-CR case added to the
`hash_content`/`region_sha` parity test, and a loose substring assertion tightened to a full
prefix match). 10 rejected, re-verified rather than assumed: 3 were exact recurrences of round 1's
own rejected findings (the `region_body_text` caller-precondition `UnicodeDecodeError`, the
`recorded_sha` comparison-strictness suggestion, the dynamic-import evasion bound), and 7 were new
this round -- a 32-bit-truncation collision-risk concern this story's own spec explicitly forbids
changing, an inherited-not-invented CRLF-normalization convention, a `recorded_sha` provenance
concern in the same rejected family as the comparison-strictness finding, a cosmetic
message-ambiguity nitpick, and three findings that were about the *review process itself* (diff-only
information asymmetry, self-attested independence, an enum-definition question resolved by
grepping the pre-existing source) rather than the code.

**Follow-up review recommended: false.** Round 2's fixes are small, localized to the same two test
files round 1 already touched, and low-consequence (two detector-precision fixes in a meta-test
and three test-assertion additions) -- no behavior change to the shipped `hashes.py` hashing or
comparison logic in either round.

**Verification performed (round 2, independently re-run):** `pyforge-marshal-test` 3789 passed (9
slow deselected, +5 from round 1's 3784: 3 `TYPE_CHECKING`-guard cases, 1 wildcard-import case, 1
empty-file end-to-end case). `ruff check` unchanged at 187 errors package-wide (a `SIM114` this
round's own edit introduced was fixed inline rather than shipped as a new finding). `pyright`
unchanged at 598 package-wide; zero in `hashes.py` (untouched this round). `lint-imports` clean (3
contracts kept, 0 broken). `python scripts/spec_surface_reconcile.py` reports `OK` after this
round's memlog entry and baseline re-stamp.

**Residual risks:** unchanged from round 1 -- `DW-FU-9-3` remains open for whichever future story
builds `state/store.py`. `region_body_text` still re-encodes the whole file per call rather than
caching across multiple regions in one document (accepted micro-optimization gap, not a
correctness issue). The P-07 meta-test's only real-code coverage today is `seed/apply/__init__.py`
(empty) -- it exercises real violations only once `apply/` gains real modules, by design.

**Verification performed:** `pyforge-marshal-test` 3784 passed (9 slow deselected, +1 for the new
regression test); `ruff check` unchanged at 187 package-wide (same pre-existing `I001` category,
zero new findings); `pyright` unchanged at 598 package-wide (zero in `hashes.py`; the meta-test's
one `reportMissingImports` is the same pre-existing category every sibling meta-test carries);
`lint-imports` clean (3 contracts kept, 0 broken); `python scripts/spec_surface_reconcile.py`
reports `OK` after both memlog entries and baseline re-stamps. All commands independently re-run
and confirmed by the orchestrating session, not only reported by the implementing subagent.

**Residual risks:** `DW-FU-9-3` (above) is a real, open design question for whichever future story
builds `state/store.py`. `region_body_text` re-encodes the whole file per call rather than caching
across multiple regions in one document -- a stated, accepted micro-optimization gap, not a
correctness issue, given this module's target files (markdown/config, not large binaries). The
P-07 meta-test's only real-code coverage today is `seed/apply/__init__.py` (empty) -- it will not
exercise a genuine violation until `apply/` gains real modules, by design (a forward-declared guard
ahead of the code it will police).
