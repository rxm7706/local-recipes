---
title: 'Story 1.2: Story identity, merge-subject rendering, and feed completeness'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'b54ad6691d311c16b52db73afb7b0f23ee2dcbfa'
final_revision: '9518cdd808c9d773a08df8ce857b3c77f1b77baa'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Nothing yet owns the story-key format. Left to individual call sites, the loop, the journal, the spec archive, the merge subject and the dashboard would each format `<epic>.<seq>` differently — the documented incident this guards against is the harness's own parser silently dropping letter-suffixed keys (`2-6a`) and halving the actionable feed.

**Approach:** Add `core/identity.py`: a `StoryKey` value type, one `normalize()` that parses any of the four external forms (feed key, filename slug, branch segment, merge subject) into it, one render function per external form, a template-driven merge-subject render/parse pair (AD-24), and `resolve_feed()` for AD-38's completeness guarantee. This is the first story to give `core/findings.py`/`core/verdict.py` a real caller, so it also adds the two real finding codes those registries need.

## Boundaries & Constraints

**Always:**
- `core/identity.py` stays pure — no `subprocess`/`os`/`time`/`adapters` imports (AD-4); only intra-`core` imports (`.model`, `.findings`).
- `StoryKey` is a frozen, orderable dataclass: `epic: int`, `seq: int`, `suffix: str = ""` (single lowercase letter or empty — `"6.1a" < "6.1b"`, and both sort after `"6.1"`). A suffix is normalized to lowercase, never dropped (closes the harness incident; confirmed live: `bmad-loop run --story` accepts `E-S`/`E.S` with an optional split suffix, e.g. `2-6a`).
- `normalize(raw: str) -> StoryKey` is the **sole** parser: strips surrounding whitespace, matches a leading `<epic>[.-]<seq><suffix>?` token (either separator accepted on input), and ignores any trailing text after it — so it accepts a bare feed key (`"1.2"`), a filename-slug/branch-segment token (`"1-2-story-identity-..."`), or a merge-subject's extracted key substring, uniformly. Non-conforming input raises `MalformedStoryKeyError` (never silently coerced or truncated) — registers as `MRS-IDENT-001`.
- Exactly one render function per external form — `render_feed_key` (dot form, e.g. `"6.1a"`), `render_filename_slug`, `render_branch_segment` (both hyphen form, e.g. `"6-1a"` — kept as two distinct functions per AD-23 even though today's output coincides, so the two consumers can't silently diverge later without a code change in exactly one place). None of the three takes or invents descriptive title text — that's the caller's concern, not identity's.
- `render_merge_subject(key, template)` / `parse_merge_subject(subject, template)` are the one render/parse pair for AD-24: `template` is a plain string containing exactly one `{key}` placeholder (any other placeholders, e.g. a run id or target branch, are the caller's job to resolve first); render substitutes the hyphen form in; parse inverts it via the template's fixed literal prefix/suffix and re-normalizes the extracted middle. A subject that doesn't fit the template's literal shape raises `MergeSubjectConformanceError` (`MRS-IDENT-002`) — deploy (a later story) will use the same function to check conformance, never a second regex.
- `resolve_feed(raw_keys) -> FeedResolution` reports `total = len(raw_keys)` (the raw pre-parse count, per F-13's fix — never the post-parse count, which would let a silently-dropped suffix report a false "18 of 18"), `resolved` (normalized keys, in order), `unresolved` (the raw strings that failed), and `findings` (one `MRS-IDENT-001` `Finding`, severity `error`, per unresolved raw key, `path` set to that raw string) so a caller can feed them straight into `verdict.compute_verdict`.
- `MRS-IDENT-001`/`MRS-IDENT-002` are added to `findings.REGISTERED_CODES` and classified `Verdict.UNEVALUABLE` in `verdict._CLASSIFY_TABLE` — both registries' first real entries; append-only, nothing existing removed.
- A meta-test asserts no module other than `core/identity.py` string-formats a story key inline (an f-string or `.format()` call whose literal template joins exactly two placeholders with `.`/`-`), proven non-vacuous against a synthetic violation, mirroring `tests/meta/test_ad7_verdict_sole_ownership.py`'s technique.

**Block If:** None identified — the two architecture gaps below (F-12/F-13, both pre-existing HIGH findings in `reviews/review-ad25-39-adversarial-2026-07-25.md`, neither a CRITICAL blocker) are resolved by grounding in the harness's live `--story` documentation and epics.md's own already-correct text, per Design Notes.

**Never:**
- Do not wire a CLI command, touch `cli/`, or invoke `core/policy.py` (doesn't exist yet — the merge-subject *template value* is a future policy concern; this story only owns the render/parse *mechanism*, taking the template as a plain argument).
- Do not model run ids, branch prefixes, PR targets, or actual git operations — those are Stories 1.4/3.x/4.3's surface.
- Do not invent a repo-wide `MarshalError` exception hierarchy (Consistency Conventions names one; Story 1.1 didn't create it either) — mirror the existing `UnregisteredFindingCodeError(ValueError)` precedent instead.
- Do not attempt to parse epic-only or `*-retrospective` sprint-status pseudo-entries — `normalize()` handles story keys only.
- Do not add a new test dependency (e.g. `hypothesis`) for the round-trip property test — parametrize over a curated key/template matrix instead, matching every sibling test file's existing style.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dot feed key | `"6.1a"` | `StoryKey(epic=6, seq=1, suffix="a")` | none |
| Hyphen key + trailing slug | `"1-2-story-identity-merge-subject-rendering-and-feed-completeness"` | `StoryKey(epic=1, seq=2, suffix="")` | none |
| Uppercase suffix | `"2-6A"` | `StoryKey(epic=2, seq=6, suffix="a")` (lowercased) | none |
| Surrounding whitespace | `"  1.2  "` | `StoryKey(epic=1, seq=2)` | none |
| No separator between key and trailing text | `"1-23extra"` | -- | raises `MalformedStoryKeyError` (`MRS-IDENT-001`) |
| Not a key at all | `"story-identity"` | -- | raises `MalformedStoryKeyError` |
| Ordering | `StoryKey(6,1)`, `StoryKey(6,1,"a")`, `StoryKey(6,1,"b")` | `6.1 < 6.1a < 6.1b` | none |
| Merge-subject round-trip | `render_merge_subject(k, "Merge {key} into main")` then `parse_merge_subject(subject, same_template)` | returns `k` | none |
| Non-conforming merge subject | `parse_merge_subject("totally different text", "Merge {key} into main")` | -- | raises `MergeSubjectConformanceError` (`MRS-IDENT-002`) |
| Feed resolution, partial failure | `resolve_feed(["1.1", "not-a-key", "1.2"])` | `total=3`, `resolved=(1.1, 1.2)`, `unresolved=("not-a-key",)`, one `MRS-IDENT-001` finding naming it | none — reported, not raised |
| Feed resolution, all resolve | `resolve_feed(["1.1", "1.2"])` | `total=2`, `resolved` has 2 entries, `findings=()` | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/identity.py` -- NEW, this story's entire deliverable
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` -- add the two real codes (first real caller; currently `REGISTERED_CODES = frozenset()`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- add the two `_CLASSIFY_TABLE` entries (currently empty)
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` -- `test_registered_codes_starts_empty` must be updated; it hard-asserts `== frozenset()`, which the above breaks
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad7_verdict_sole_ownership.py` -- READ-ONLY style reference for the new meta-test's AST-scan technique
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/reviews/review-ad25-39-adversarial-2026-07-25.md` -- READ-ONLY; F-12/F-13 are the two architecture gaps this story's Design Notes resolve

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/marshal/core/identity.py` -- `StoryKey` (frozen, `order=True`, fields `epic:int, seq:int, suffix:str=""`) with canonical `__str__` (dot form); `MalformedStoryKeyError`, `MergeSubjectConformanceError` (both `ValueError` subclasses); `normalize()`; `render_feed_key`/`render_filename_slug`/`render_branch_segment`/`render_merge_subject`; `parse_merge_subject`; `FeedResolution` (frozen dataclass: `resolved`, `unresolved`, `total`, `findings`) + `resolve_feed()` -- the whole AD-23/AD-24/AD-38 surface
- [x] `src/pyforge/marshal/core/findings.py` -- add `"MRS-IDENT-001"`, `"MRS-IDENT-002"` to `REGISTERED_CODES` -- the first real registrations
- [x] `src/pyforge/marshal/core/verdict.py` -- add both codes to `_CLASSIFY_TABLE` -> `Verdict.UNEVALUABLE` -- the first real classifications
- [x] `tests/unit/test_identity.py` -- NEW: `normalize()` across every I/O-matrix scenario; each render function's output shape; the merge-subject round-trip parametrized over multiple `StoryKey` shapes (no suffix / with suffix / multi-digit) x multiple templates; `resolve_feed()` partial/complete resolution; total-ordering assertions
- [x] `tests/meta/test_ad23_inline_key_format_guard.py` -- NEW: AST-scan every installed module except `identity.py` for an f-string/`.format()` literal template joining exactly two placeholders with a bare `.`/`-`; parametrized per-module like the AD-7 guard; a synthetic-violation unit proves the detector fires (non-vacuous); a positive assertion that `identity.py` itself defines all 4 render functions plus `normalize`
- [x] `tests/unit/test_findings.py` -- update `test_registered_codes_starts_empty` to assert `REGISTERED_CODES == frozenset({"MRS-IDENT-001", "MRS-IDENT-002"})` with a comment noting this module is no longer hypothetically-empty

**Acceptance Criteria:**
- Given any of the four external forms (feed key, filename slug, branch segment, an already-extracted merge-subject key substring), when `normalize()` runs, then it returns the same canonical `StoryKey` whenever the leading key token is equivalent, suffix preserved and case-normalized
- Given a `StoryKey`, when each of the four render functions runs, then no two are the same function object and each produces its documented external-form shape
- Given any `StoryKey` and any single-placeholder template, when `parse_merge_subject(render_merge_subject(key, template), template)` runs, then the result equals `key`
- Given a raw reference list with at least one malformed entry, when `resolve_feed()` runs, then `total` equals the input length, every malformed entry is named in both `unresolved` and `findings`, and `verdict.compute_verdict(result.findings)` is `Verdict.UNEVALUABLE` (non-zero exit)
- Given the installed package, when the AD-23 meta-test runs, then it passes for real code and its synthetic-violation probe still fires

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 1, medium 2, low 4)
- defer: 1 (medium)
- reject: 8 (all low)
- addressed_findings:
  - `[high]` `[patch]` `core/identity.py` `normalize()` crashed with a raw `AttributeError` on a non-`str` `raw` (a real YAML footgun: an unquoted `1.2:` feed key parses as the float `1.2`), directly violating `resolve_feed`'s own "malformed entries are reported, never raised" contract — one bad-typed entry aborted resolution of the entire feed. Added a `str` guard raising `MalformedStoryKeyError`; `resolve_feed`'s per-entry loop now repr's a non-`str` raw value for `unresolved`/`Finding.path` (a bare pass-through would have re-crashed inside `Finding.__post_init__`'s own `path must be a str or None` check). Verified live before and after.
  - `[medium]` `[patch]` `parse_merge_subject` raised `MergeSubjectConformanceError` (registers as `MRS-IDENT-002`) but nothing in the diff ever constructed a `Finding` with that code — the registry entry was dead, contradicting this exact package's own Story-1.1-established convention ("do not register a code with no real caller"). The exception now carries a `.finding` attribute (a real `MRS-IDENT-002` `Finding`), closing the gap; a test confirms it classifies `Verdict.UNEVALUABLE`.
  - `[medium]` `[patch]` `StoryKey` had no `__post_init__`, unlike `model.py`'s `Finding`/`Envelope` (this package's own established validation convention) — direct construction (bypassing `normalize()`) silently accepted e.g. `StoryKey(-1, 999, "ZZ")`. Added validation (non-negative `epic`/`seq`; `suffix` is `""` or a single lowercase letter) plus 5 parametrized regression tests.
  - `[low]` `[patch]` `_split_template`/`parse_merge_subject` didn't guard non-`str` `template`/`subject`, so a non-`str` value raised a raw `AttributeError` instead of the documented, wrapped `MergeSubjectConformanceError` — contradicting the docstring's "wraps every failure mode" claim. Added guards; 3 new tests.
  - `[low]` `[patch]` `test_registered_codes_starts_empty`'s name asserted the opposite of its own body (which now checks the registry is non-empty) — a bare test-name-only failure listing would read backwards. Renamed to `test_registered_codes_contains_the_real_codes`.
  - `[low]` `[patch]` The module's own headline motivating scenario — a letter-suffixed key (harness's documented `2-6a`) combined with trailing descriptive slug text in the same token — was never tested; the two existing cases test suffix-without-slug and slug-without-suffix separately. Added `test_normalize_glued_suffix_with_trailing_slug`.
  - `[low]` `[patch]` The multi-failure `resolve_feed` test only asserted counts, not that each unresolved entry and its `Finding` name the same raw key by position — a scrambled-attribution regression would have passed. Added `test_resolve_feed_multi_failure_per_item_attribution`.
  - `defer` (medium): `architecture-pyforge-marshal-2026-07-25/architecture.md`'s AD-23 rule text still literally says the key is "purely numeric on both parts," unamended and directly contradicting AD-38 — a pre-existing planning-artifact defect (review finding F-12, already known before this story), outside this story's surface. Ledger entry appended.
  - `reject` (8, out of scope or already correct per spec): `parse_merge_subject` collapsing a broken-template failure and a non-conforming-subject failure into one exception type (matches the spec's own explicit design); asymmetric exception types between `render_merge_subject` (bare `ValueError`) and `parse_merge_subject` (`MergeSubjectConformanceError`) for a malformed template (both are `ValueError` subclasses; matches the spec's literal wording; not worth added complexity for a caller that doesn't exist yet); AD-38's "resolved N of M" phrasing not literally rendered as text anywhere (this is the CLI/display layer's job, explicitly out of this story's Never bullets — `FeedResolution`'s structured data is the correct `core` representation); `Finding.path` reused for an arbitrary story-reference string rather than a literal filesystem path (the schema doesn't constrain `path`'s semantics; a reasonable reuse of the existing `Finding` shape); the suffix's single-letter cap with no 27th-sub-story overflow story (matches the spec and the harness's own documented convention; zero real evidence this is ever needed); the AD-23 AST guard's undocumented blind spot for `%`-style string formatting (matches the AD-7 guard's own precedent of documented, non-exhaustive best-effort bounds; zero use of `%`-formatting anywhere in this codebase's actual style); a hyphen-separated suffix shape (`"6-1-a"`) being treated as ordinary discarded trailing text rather than a suffix (no documented convention supports this alternate, unglued spelling — inventing support would itself be a form of guessing intent, which AD-23 forbids; the one documented convention, the glued form `2-6a`, is tested and correct); `resolve_feed`'s `total = len(raw_keys)` assuming a sized `Sequence` rather than any `Iterable` (matches its own type hint; trusting type contracts at a function boundary matches this codebase's existing sibling style).

### 2026-07-30 — Review pass (independent follow-up on the `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 3, low 6)
- defer: 0
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `resolve_feed("1.2")` — a bare `str` satisfies `Sequence[str]` — shredded into per-character garbage (`total=3`, three bogus `MRS-IDENT-001` findings for `'1'`, `'.'`, `'2'`), violating this package's own convention: `model.py`'s `Envelope.__post_init__` explicitly guards `assumptions` against this exact bare-str footgun. Added an `isinstance` guard raising `TypeError`; test pins it.
  - `[medium]` `[patch]` `FeedResolution` had no `__post_init__` — direct construction (bypassing `resolve_feed()`) could fabricate the false "N of M" completeness attestation AD-38 exists to prevent (`FeedResolution(resolved=(), unresolved=(), total=5, findings=())` constructed cleanly). Both reviewers flagged it; inconsistent with this spec's own prior-pass rationale for adding `StoryKey.__post_init__`. Added the two completeness-arithmetic checks (`total == len(resolved)+len(unresolved)`; one finding per unresolved entry) + 2 parametrized tests.
  - `[medium]` `[patch]` The render functions were the one unguarded door: `render_feed_key("6-1A")` silently echoed the un-normalized string as if canonical (bare `str(key)` — the exact silent coercion the module exists to prevent), and the hyphen renderers crashed with a raw `AttributeError`. Added `_require_story_key` (a `TypeError` guard) to `render_feed_key` and `_hyphen_form` (covers slug/branch/merge-subject); 3 parametrized tests.
  - `[low]` `[patch]` `StoryKey.__post_init__`'s suffix check used `islower()`/`isalpha()` — Unicode-wide, so `StoryKey(1, 2, "ß")` constructed while the error message promised "a-z", minting a key `normalize()` can never round-trip. Replaced with an explicit ASCII `"a" <= suffix <= "z"` range; `"ß"` added to the invalid-construction parametrize.
  - `[low]` `[patch]` The AD-23 guard's stated Bounds omitted its most likely real evasion: identity's own canonical render bodies are THREE-placeholder f-strings (`f"{epic}-{seq}{suffix}"`), invisible to the exactly-two-placeholder detector — so the `EXCEPT identity.py` carve-out is currently unexercised (the detector finds zero violations in identity.py itself) and the guard's aliveness proof is synthetic-only, weaker than the AD-7 guard's fires-on-its-own-target proof it claims to mirror. Bounds paragraph now states all of this plainly. Detector behavior unchanged (its exactly-two-placeholder shape is spec-pinned).
  - `[low]` `[patch]` A non-str feed entry's diagnostic displayed `repr(1.2)` — the quoteless, perfectly-valid-looking `1.2` — so the finding claimed a well-formed key failed to resolve, discarding the one fact explaining it. The message now appends the type name (`(float)`), matching `normalize()`'s own non-str message; `unresolved`/`path` keep the bare repr as the entry's identifier.
  - `[low]` `[patch]` `resolve_feed([])`'s clean 0-of-0 was accidental (untested, undocumented) — the ultimate silently-shortened feed would read as success. Pinned with a test + a docstring sentence assigning empty-feed policy to the caller (the loop's completeness gate), not identity.
  - `[low]` `[patch]` `test_verdict.py`/`test_model.py` module docstrings still asserted the retired "starts empty" registry/table contract this story's own diff removed — updated only in `findings.py`/`verdict.py`/`test_findings.py`. Refreshed both to the Story-1.2 wording.
  - `[low]` `[patch]` The non-str feed fixture `resolve_feed(["1.1", 1.2, "1.3"])` lacked the `# type: ignore` its sibling `normalize(1.2)` tests carry. Added.
  - `reject` (8, all low): dotted/detached trailing tokens (`"6.1.a"`, `"1.2.3"`, `"2-6-a"`) silently discarded rather than rejected (the spec's Always bullet pins "ignores any trailing text after it" with a single reading, the I/O matrix pins glued-text-only rejection, and the prior pass's recorded rejection already blessed discard for the detached-letter shape — reversing it would overturn a recorded triage decision on unchanged facts); `MergeSubjectConformanceError.finding` as a structural `__init__` arg (single controlled raise site, tested; prior pass's own "not worth added complexity for a caller that doesn't exist yet" rationale); `MalformedStoryKeyError` not carrying a `.finding` (same rationale — `MRS-IDENT-001` has a real construction site in `resolve_feed`; a direct-`normalize()` consumer wanting findings is a future story's additive change); duplicate/aliased raw keys (`"1.1"`/`"1-1"`/`"01.1"`) collapsing to one canonical key with no dedup finding (outside the spec's `FeedResolution` contract; feed sources key stories uniquely by construction; canonical collapse is normalization working); `test_render_functions_are_four_distinct_callables` as unfalsifiable noise (it is the literal implementation of a spec AC — "no two are the same function object"); iterator/generator input to `resolve_feed` breaking `len()` (identical to the prior pass's recorded rejection: trusting the `Sequence` type contract matches sibling style); no waiver mechanism for future legitimate dotted two-placeholder f-strings (speculative complexity; deal with the first real false positive when it exists); the `%`-formatting detector blind spot (identical to the prior pass's recorded rejection — documented best-effort bounds per the AD-7 precedent).

## Design Notes

**Resolving F-12/F-13 (architecture review gaps, both HIGH, not CRITICAL, left open in the 2026-07-25 adversarial pass).** AD-23's rule text still says the key is "purely numeric on both parts," unamended, while AD-38 (added same day) says suffixes are preserved. The review calls out that epics.md's own Story 1.2 AC already has it right ("preserved and normalized") and that the harness's live `--story` flag documents accepting a split suffix (`2-6a`) — so numeric-only would reject input the very harness Marshal wraps accepts. This spec follows epics.md + AD-38 (suffix preserved, lowercased) and treats AD-23's stale sentence as superseded, the same way Story 1.1 recorded assumptions where its own source documents underspecified something. F-13's fix (`M` = pre-parse raw count, not post-parse) is applied directly in `resolve_feed`'s `total` field — the alternative (counting successfully-parsed keys as the denominator) would let a future suffix-dropping bug report a false "N of N", exactly reproducing the incident AD-38 exists to prevent.

**Why `findings.py`/`verdict.py` are in this story's surface despite epics.md naming only `core/identity.py`.** Both modules' own shipped docstrings say `REGISTERED_CODES`/`_CLASSIFY_TABLE` start empty "no command in this story emits a real finding... later stories append real codes here as they gain a real caller" — this is that story. Appending two entries to each is additive and narrowly scoped to identity's own two failure modes; it is the anticipated growth path, not scope creep.

**Merge-subject template mechanism.** The one concrete real-world shape on record (`architecture-bmad-infra.md`, current dashboard-parsed convention) is `Merge bmad-loop/<run-id>/<X-Y>-<slug> into <target>`. Story 1.2 doesn't yet have run ids, branch composition, or policy (Stories 1.3/3.x/4.3), so `render_merge_subject`/`parse_merge_subject` only own the `{key}` substitution point; a caller pre-resolves every other placeholder before calling either function. Parsing is exact positional slicing on the template's fixed literal prefix/suffix around the one placeholder (not a general regex) — unambiguous regardless of what the substituted key segment itself contains.

**Why two finding codes, not one.** `MRS-IDENT-001` (malformed key) and `MRS-IDENT-002` (non-conforming merge subject) are semantically distinct per AD-24's own framing ("deploy reports any merge... whose subject does not conform" is a named, separate concept from an arbitrary bad reference) — giving Story 4.3 a precise code to filter deploy-time conformance reports on without re-deriving it from a message string.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite passes, including the new identity unit tests and the AD-23 meta-test
- `pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: `2 kept, 0 broken` (unchanged; identity.py adds no new cross-boundary import)

## Auto Run Result

**Run 2026-07-30 (follow-up review pass on the `done` spec; `review_loop_iteration` reset to 0 by routing).**

**Summary:** Independent double review (Blind Hunter + Edge Case Hunter, no shared context) of the full Story 1.2 diff (`b54ad6691d..00aaeaa1bd`). No intent gaps, no spec deviations. Nine patches applied — all defensive input-boundary hardening and documentation honesty in `core/identity.py` and its tests; no behavior changed for any documented input. Committed as `9518cdd808`.

**Files changed this pass:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/identity.py` — bare-str feed guard, `FeedResolution.__post_init__` completeness arithmetic, render-function type guards, ASCII-range suffix validation, typed non-str diagnostics, empty-feed docstring
- `src/shared/packages/pyforge-marshal/tests/unit/test_identity.py` — 8 new regression tests pinning every patched behavior; `type: ignore` consistency
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad23_inline_key_format_guard.py` — Bounds paragraph now states the three-placeholder blind spot and the synthetic-only aliveness asymmetry vs AD-7
- `src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py`, `tests/unit/test_model.py` — stale "starts empty" registry docstrings refreshed to Story-1.2 state

**Review findings breakdown:** 26 raw findings from the two reviewers → deduplicated and triaged: 9 patched (3 medium, 6 low), 0 deferred (no new ledger entries; existing ledger untouched per orchestrator instruction), 8 rejected (each with recorded rationale in the triage log; three were re-submissions of findings this spec's prior pass already rejected on recorded grounds).

**Verification:** `pixi run -e pyforge-marshal pyforge-marshal-test` → **241 passed** (233 pre-pass + 8 new). `pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` → **2 kept, 0 broken**.

**Follow-up review recommendation:** false — every patch is a localized misuse-path guard or docs fix, pinned by its own test, with no change to documented-input behavior, no API/security/data impact, and both reviewers independently converged on the same small cluster; a third pass would re-tread recorded rejections.

**Residual risks:** `normalize()` discards separator-detached trailing tokens by design (`"6.1.a"` → `6.1`) — spec-pinned, twice-triaged; if a future feed source can emit dotted-tail keys, that story must add its own conformance check. The AD-23 meta-guard remains best-effort static analysis with stated bounds (three-placeholder and `%`-formatting shapes out of scope). The architecture doc's stale AD-23 "purely numeric" sentence remains a pre-existing planning-artifact defect, already on the deferred-work ledger from the prior pass.

