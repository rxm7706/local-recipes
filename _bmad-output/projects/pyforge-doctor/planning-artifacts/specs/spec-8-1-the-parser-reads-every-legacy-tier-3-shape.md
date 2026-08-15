---
title: 'Story 8.1: The parser reads every legacy Tier-3 shape'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '00db418fd1b5013bc77cd70f6708a1a5ec57cddd'
final_revision: '6eb25f292e99adf48ec19a3ce992c7696bcc3f20'
---

<intent-contract>

## Intent

**Problem:** `_anonymous()` (`chain.py:1366`) only answers "is this line
anonymous" for the detector's own count — it cannot classify an entry's
*shape* or extract its content, which Story 8.2/8.3 need to mint an id and
promote the entry verbatim. Worse, `_anonymous()` itself mishandles a
class of live entries: a `### DW-<n>: <title>` header whose own body uses
plain (non-bulleted) `origin:`/`source_spec:`/`severity:`/`status:` keys
never satisfies `_ANON_RE` (`^-\s+source_spec:`), so `_anonymous()`'s
in-entry/field-taken state never advances past that header — and the state
machine then wrongly treats the *next*, topically unrelated, headerless
`- source_spec:` bullet anywhere later in the file as "already claimed" by
that header, silently dropping a real orphan from the anonymous count.
Verified live across all 8 projects: 29 such headers exist, 21 of them
swallow a real, unrelated orphan this way (marshal 9/9, atlas 3/3, doctor
4/5, herald 2/3, mason 2/3, steward 1/4).

**Approach:** Add a new, additive classifier — `classify_tier3_entries(path)`
in `chain.py`, beside `_anonymous()`/`_entries()`/`_ids()` — that walks a
Tier-3 file once and returns one `LegacyEntry` per real entry, each carrying
its shape, its id (if any), and its full field text (for 8.3's verbatim
promotion). Do not modify `_anonymous()`, `_entries()`, or `_ids()`, and do
not change `gather_deferred_work`'s existing findings — this story is purely
additive, feeding 8.2/8.3, not a detector-behavior change.

## Boundaries & Constraints

**Always:** Classify every entry into exactly one of four `Tier3Shape`
values — `IDENTIFIED_BULLETED` (`### DW-<id>:` header + immediate bulleted
`- source_spec:`, CAP-1's current shape), `IDENTIFIED_PLAIN` (`### DW-<n>:`
header + plain non-bulleted `source_spec:`/etc. keys — the
"review-budget-followup" shape), `LEGACY_FLAT` (a headerless
`- source_spec:` bullet — no owning `##`/`###` DW- heading anywhere above
it), `LEGACY_HEADER` (a non-DW `## Deferred [from:]...` heading immediately
owning a bulleted `- source_spec:` field). A bullet with no `source_spec:`
field at all (freeform prose, e.g. warden's plain markdown bullets) is not
an entry — skip it, it was never a target of any version of this tooling.
`IDENTIFIED_*` entries carry their real id; `LEGACY_*` entries carry
`id=None`. Zero false-orphan (an `IDENTIFIED_*` entry misread as `LEGACY_*`)
and zero false-owned (a real `LEGACY_*` orphan misread as belonging to an
unrelated header) — pin every shape, plus the `IDENTIFIED_PLAIN`
next-bullet-swallow case, with a fixture built from real excerpts (cite the
source file + line range in the test, per this repo's existing convention).
`summary:`/`evidence:` field extraction must capture wrapped continuation
lines (observed live in herald), not just the first physical line.

**Block If:** a 5th distinct structural shape is found live during
implementation that isn't one of the four above (none was found across all
8 projects in this session's verification pass, but re-check).

**Never:** touch `_anonymous()`, `_entries()`, `_ids()`, or
`gather_deferred_work`'s findings output — this story changes no existing
`doctor check`/`deferred-work-check` behavior or finding counts.
`_anonymous()`'s own `IDENTIFIED_PLAIN` swallow-bug stays live in the
detector after this story (out of scope — log it as a deferred-work entry,
do not fix `_anonymous()` itself). No minting, no promotion, no file
writes — that's 8.2/8.3.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CAP-1 shape | `### DW-FU-6-1:` + `- source_spec:` | `IDENTIFIED_BULLETED`, id=`DW-FU-6-1` | none |
| Follow-up shape | `### DW-1:` + plain `source_spec:` key | `IDENTIFIED_PLAIN`, id=`DW-1` | none |
| Headerless bullet | `- source_spec:` with no heading above | `LEGACY_FLAT`, id=`None` | none |
| Old-header bullet | `## Deferred from: ... (date)` + `- source_spec:` | `LEGACY_HEADER`, id=`None` | none |
| Old-header freeform | `## Deferred from: ...` + plain prose bullet | not returned (not an entry) | none |
| Bullet after `IDENTIFIED_PLAIN` header | marshal-shape DW-1 header, then an unrelated later `- source_spec:` bullet | the later bullet still returns `LEGACY_FLAT`, id=`None` (NOT swallowed) | none |
| Empty/missing file | no Tier-3 file | `()` | none, no raise |
| Non-UTF-8 bytes | malformed encoding | decodes via existing `errors="replace"` convention | none, no raise |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add `Tier3Shape` (str enum) + `LegacyEntry` (frozen dataclass: `shape`, `id: str | None`, `start_line`, `end_line`, `fields: dict[str, str]`) and `classify_tier3_entries(path) -> tuple[LegacyEntry, ...]`, placed beside `_anonymous()`/`_entries()`/`_ids()` under the existing `gather_deferred_work` banner.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- new fixture-based tests for `classify_tier3_entries`, built from real excerpts.

## Tasks & Acceptance

**Execution:**
- [x] `chain.py` -- add `Tier3Shape`, `LegacyEntry`, a header classifier (recognize `IDENTIFIED_BULLETED` vs `IDENTIFIED_PLAIN` by whether the header's own field block ever produces a matching `- source_spec:` bullet before the next heading/EOF, vs a plain `source_spec:` key) and `classify_tier3_entries` reusing `_ENTRY_RE`/`_ANON_RE` line-scanning but tracking full entry spans and field text, never re-deriving `_anonymous()`'s own counting logic -- gives 8.2/8.3 a single, correct read of any Tier-3 file's entries.
- [x] `chain.py` -- field-value extraction must join wrapped continuation lines for `summary:`/`evidence:` (a line is a continuation iff it is non-blank, not itself a new `- <key>:` bullet, and not a heading) -- matches herald's real multi-line fields.
- [x] `tests/unit/test_sources_chain_deferred_work.py` -- fixtures built verbatim from: atlas `deferred-work.md` lines 1-16 (`LEGACY_FLAT`), warden lines 1-20 + one `## Deferred from:`-with-bulleted-field excerpt (`LEGACY_HEADER`, both the shaped and the freeform-skip case), a `### DW-FU-6-1:`-style excerpt already in doctor's own tracked ledger (`IDENTIFIED_BULLETED`), marshal lines 47-58 (`IDENTIFIED_PLAIN` header at DW-1 + the swallowed-in-`_anonymous()`-but-must-NOT-be-swallowed-here bullet at line 54) -- proves the exact fleet-wide bug this story exists to not repeat.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append one new entry (via the emitter convention, with an id) recording `_anonymous()`'s live `IDENTIFIED_PLAIN` swallow-bug (21 real victims fleet-wide) as a known, out-of-scope defect in the existing detector, for a future story to consider. Live-measured via `classify_tier3_entries` itself at landing time: 25/38 (not 21/29) -- see the minted entry `DW-FU-8-1`'s own evidence for the reconciliation.

**Acceptance Criteria:**
- Given the real marshal Tier-3 file, when `classify_tier3_entries` runs, then the bullet at line 54 (and the analogous bullet after each of DW-2/3/4/5/6/7/8/9) classifies as `LEGACY_FLAT` with `id=None`, never as owned by the preceding `IDENTIFIED_PLAIN` header.
- Given a fixture combining all four shapes plus one freeform-prose bullet, when classified, then each shape returns its correct `Tier3Shape` and id-or-None, and the freeform bullet is absent from the result.
- Given a `LEGACY_FLAT`/`LEGACY_HEADER` entry whose `summary:` wraps two physical lines, when classified, then `fields["summary"]` contains the joined text, not just the first line.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 2, medium 2, low 9)
- defer: 0
- reject: 1 (low 1)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found wrapped-continuation joining treats ANY indented `word:`-shaped line as a new field start, not just a real `- <key>:` bullet -- silently truncates/misattributes `summary`/`evidence` text. Confirmed against 5 real entries across 4 tracked ledgers (atlas `DW-AD23-2`/`DW-AD23-3`, doctor `DW-CHAIN-COMPLETENESS-1`, herald `DW-13-6-1`/`DW-14-3-1`). Directly contradicts this story's own AC (continuation rule: stop only on a new `- <key>:` bullet or a heading, never on a bare `word:` line). Fix: correct `_CONT_KEY_RE`'s stop condition to match the AC's literal rule.
  - `[high]` `[patch]` Blind Hunter found a false-orphan misclassification when non-blank, non-field content (e.g. an `<!-- id assigned ... -->` HTML comment, a real live convention from the 2026-07-30 verification campaign) sits between an identified header and its own field block -- the header gives up after one line, and its real content is then read as a separate, unrelated `LEGACY_FLAT` orphan. Confirmed live in marshal's tracked, git-committed ledger at `## DW-1-2-1` and `## DW-1-10-7`. Fix: widen the header's own field-search window to scan forward (skipping blank/non-field lines) up to the next heading, not just the next line.
  - `[medium]` `[patch]` Edge Case Hunter found a bulleted identified-header field block whose first key is not `source_spec:` may silently drop its content. Fix: generalize field-block consumption to any bulleted `key:` field, not just `source_spec:`.
  - `[medium]` `[patch]` Blind Hunter found `_LEGACY_HEADER_RE` misses the live `## Deferred: <title> (<date>)` spelling (no "from") -- confirmed live at warden's tracked ledger line 488, currently inert (owns no bulleted content today) but a real counter-example to "no 5th shape found." Fix: broaden the regex to accept both spellings.
  - `[low]` `[patch]` Blind Hunter found the module banner comment still cites the pre-correction `_anonymous()` swallow estimate (29/21) instead of the corrected live measurement (38/25) this story's own `DW-FU-8-1` entry recorded. Fixed: comment updated.
  - `[low]` `[patch]` Blind Hunter found `Tier3Shape`/`LegacyEntry`/`classify_tier3_entries` missing from `chain.py`'s `__all__`, breaking the module's established convention for its `gather_*`-adjacent public surface. Fixed: added.
  - `[low]` `[patch]` Edge Case Hunter found a TOCTOU gap -- `classify_tier3_entries` checks `_is_file(path)` then calls `path.read_text()` unguarded, so a file deleted in between raises, contradicting the module's "never raises" convention. Fixed: wrapped in try/except mirroring `_anonymous()`'s own pattern.
  - `[low]` `[patch]` Edge Case Hunter found the new live-marshal-file smoke test can raise an unguarded `IndexError` instead of a clear assertion failure as the ledger grows. Fixed: explicit bounds check with `pytest.fail`.
  - `[low]` `[patch]` Blind Hunter found `_consume_bulleted_field_block`/`_consume_plain_field_block` both inline `re.match(r"^-\s", line)` instead of sharing one named pattern, unlike every other regex in this addition. Fixed: extracted a shared constant.
  - `[low]` `[patch]` Blind Hunter found dead code in `_consume_plain_field_block` (an `elif current_key is not None` branch that can never see `current_key is None`, since the function is only entered after the caller already confirmed a match). Fixed: simplified.
  - `[low]` `[patch]` Blind Hunter found an unedited self-correction left in a test docstring ("...no -- ``IDENTIFIED_PLAIN``..."). Fixed: cleaned up wording.
  - `[low]` `[patch]` Blind Hunter found `IDENTIFIED_PLAIN`'s docstring undersells its dominant real shape (pure freeform prose, `fields={}` -- 28/38 live entries, 100% of atlas's) as if the plain-key "review-budget-followup" shape were the common case. Fixed: docstring corrected to name the freeform case as dominant.
  - `[low]` `[patch]` Blind Hunter found the docstring's claim of reusing `_ANON_RE`'s pattern is false -- `_SOURCE_SPEC_BULLET_RE` hand-duplicates the same prefix text with no shared source, so the two can drift. Fixed: `_SOURCE_SPEC_BULLET_RE` now derives its prefix from `_ANON_RE.pattern`.
  - `[low]` `[reject]` Edge Case Hunter found `_ENTRY_RE`'s `#{2,4}` heading-level range would miss a DW- header written with 1 or 5-6 `#` chars. Rejected: mirrors the already-shipped, already-accepted `_ENTRY_RE` limitation verbatim (this story reuses that convention deliberately); no live counter-example exists anywhere in the fleet's 8 Tier-3/tracked files despite exhaustive verification.

## Design Notes

The epics.md AC text describes shape 4 as "a headed entry with more than
one `- source_spec:` bullet stacked under it." Live verification (this
session, all 8 projects) found the real mechanics are narrower and
different: the header itself (`IDENTIFIED_PLAIN`) has *zero* bulleted
fields of its own, and the bug is that `_anonymous()`'s state machine
attributes the *next unrelated* headerless bullet to it. Ground this
story's fixtures in the verified live mechanics, not the epics.md
paraphrase — the acceptance bar (CAP-4: "classifies every entry correctly")
is about real data, and no genuine one-header/multiple-related-bullets shape
was found anywhere in the fleet's 8 Tier-3 files.

Mutation (minting/promotion) is out of this story per the Spec's own
constraint and per Epic 8's context doc: Doctor's `sources/` package is
read-only by construction (a meta-test enforces this). `classify_tier3_entries`
must stay a pure read function with no side effects, so Story 8.3's future
`--fix` script (standalone, mirroring `spec_surface_check.py`) can safely
import or duplicate it without inheriting a write site.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: all pass, including new `classify_tier3_entries` fixture tests.
- `python -c "from pyforge.doctor.sources.chain import classify_tier3_entries; ..."` against the real marshal `deferred-work.md` -- expected: line 54 (and the other 8 analogous lines) classify `LEGACY_FLAT`/`id=None`.

## Auto Run Result

**Summary.** Added `classify_tier3_entries(path) -> tuple[LegacyEntry, ...]`
to `chain.py`, a new additive classifier that reads any Tier-3 deferred-work
file and returns one `LegacyEntry` per real entry (shape, id-or-None, full
field text), distinguishing the four live shapes proven to exist fleet-wide:
`IDENTIFIED_BULLETED` (CAP-1 current shape), `IDENTIFIED_PLAIN` (the
plain-key "review-budget-followup" shape, whose dominant real form is
actually pure freeform prose with no key:value structure at all),
`LEGACY_FLAT` (headerless bulleted orphan), `LEGACY_HEADER` (old non-DW
`## Deferred [from:]` heading). `_anonymous()`/`_entries()`/`_ids()` and
`gather_deferred_work`'s existing findings are untouched — confirmed
byte-identical detector output before/after. A real, live bug in
`_anonymous()` (a `### DW-<n>:` plain-key header silently swallows the next
unrelated headerless bullet into its own id) was discovered, measured
(corrected to 38 headers / 25 swallowed victims fleet-wide, superseding the
Design Notes' earlier 29/21 estimate), and logged as `DW-FU-8-1` rather than
fixed — out of this story's scope per the Spec's own "do not rewrite
`_anonymous()`" constraint.

Adversarial review (Blind Hunter + Edge Case Hunter) caught two real,
live-data-confirmed HIGH-severity bugs in the classifier itself before this
story shipped: a continuation-line joiner that misread ordinary prose
colons ("Not fixed here: ...") as new field boundaries, silently truncating
`summary`/`evidence` text (confirmed corrupting 5 real entries across 4
projects' tracked ledgers); and a false-orphan misclassification when a
real, live convention (an `<!-- id assigned ... -->` HTML comment from the
2026-07-30 verification campaign) sits between a header and its own field
block (confirmed live in marshal's committed tracked ledger, `DW-1-2-1` and
`DW-1-10-7`). Both are fixed and re-verified against the exact real entries
that exposed them, with new regression fixtures built from those real
excerpts.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `Tier3Shape`, `LegacyEntry`, `classify_tier3_entries` and its helpers; added to `__all__`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- 12 new tests: 4 shape fixtures (real excerpts), the marshal `IDENTIFIED_PLAIN`-swallow regression proof, the live-file all-9-headers smoke check, a wrapped-continuation fixture, a combined-4-shapes-plus-freeform fixture, two edge-case tests (missing file, non-UTF-8), plus the two post-review regression fixtures (continuation-join real-excerpt case, interposed-comment real-excerpt case).
- `_bmad-output/projects/pyforge-doctor/implementation-artifacts/deferred-work.md` -- 1 new entry (`DW-FU-8-1`, the `_anonymous()` swallow-bug, out of scope for this story).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated): 0 intent_gap, 0 bad_spec, 13 patch (2 high / 2 medium / 9 low, all applied and re-verified), 0 defer, 1 reject (a heading-level-range edge case mirroring an already-accepted existing-code limitation with no live counter-example). No loopback needed -- both high findings were resolvable as direct patches against a sufficiently clear spec, not spec-level gaps.

**Follow-up review recommendation:** `true`. Two of the 13 patches were real, live-data-confirmed correctness bugs in a brand-new core algorithm that Stories 8.2/8.3 will directly build on for id minting and verbatim promotion -- volume (13) and consequence (silent content corruption; false-orphan misclassification) both clear the bar for an independent follow-up pass before 8.2 starts.

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test` -> 870 passed, 2 skipped (both pre-existing/expected). Detector-unchanged: `python -m pyforge.doctor.sources deferred-work --json` byte-identical before/after (git-stash diff). `ruff check` on both touched files: one new finding introduced during the patch pass was itself fixed; remaining findings are pre-existing (verified against the pre-Story-8.1 baseline) and outside this story's 13 approved patches -- left untouched per Surgical Changes.

**Residual risks:** `classify_tier3_entries` has zero production callers yet (Story 8.2/8.3 are its first consumers) -- same accepted shape as Story 6.3's `degrade_on_exception` precedent. The `_anonymous()` swallow-bug (`DW-FU-8-1`) remains live in the shipped detector; a future story must decide whether to fix it. `_KNOWN_FIELD_KEYS`' vocabulary-gated continuation-join fix is closed-world -- a legitimate new field key introduced by a future emitter change would need adding to that set, a maintenance coupling worth naming for 8.2/8.3's authors.

**Manual checks (if no CLI):**
- Confirm `pixi run -e local-recipes deferred-work-check` (or the doctor check equivalent) reports identical findings before and after this change -- this story must not alter existing detector output.
