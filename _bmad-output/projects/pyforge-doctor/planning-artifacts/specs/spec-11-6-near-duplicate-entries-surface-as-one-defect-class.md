---
title: 'Story 11.6: Near-duplicate entries surface as one defect class'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '7105c7910319f41a43a8491b1c036a799a24964c'
final_revision: 'b184a605b407a9c98f414e11b4aa076ae70fc44c'
---

<intent-contract>

## Intent

**Problem:** The real 2026-07-30 campaign found one root defect (`bmad-ui` losing its local
`./build_artifacts` channel) independently hit and fixed three separate times across three
different projects' ledgers — two of the three entries still read `open`, because nothing
connected them; each sat alone as an unremarkable, independent, low-priority "already fixed?"
line. The sweep (Stories 11.1–11.5) already selects, filters, and verifies entries one at a time,
but nothing looks ACROSS entries for the same shared defect.

**Approach:** Add a read-only post-processing pass over the already-gathered
`due-for-verification` items: two or more entries in DIFFERENT projects that name the same
backtick-quoted code path/symbol token, or carry normalized-identical claim text, are grouped
into one additive `due-for-verification-cluster` Finding — never a fuzzy/semantic match, the same
narrow, non-fuzzy, exact-normalized-equality proxy `apply_verification_verdicts.py`'s own
anti-restatement check already established for exactly this kind of judgment-adjacent text
comparison.

## Boundaries & Constraints

**Always:**
- Stay pure/read-only (`tests/meta/test_read_only_guard.py`); never import another station's
  package (`tests/meta/test_source_independence.py`).
- Additive only: never mutate, remove, or reshape any existing `due-for-verification`/
  `due-for-verification-unevaluable` item — no regression in Stories 11.1–11.5's existing tests.
- A cluster requires members from at least two DIFFERENT projects (CAP-6's own wording,
  "across different projects") — a shared token/text within one project's own ledger never
  clusters.
- Isolate the whole correlation pass in one try/except: a problem reading any project's ledger
  during this pass degrades to "no clusters found" (never crashes or discards the
  already-computed per-entry findings) — mirrors the review-driven fix already applied to
  `_known_project_code_roots` in Story 11.5.
- Reuse `_entry_named_paths`'s existing backtick-quoted-token extraction unmodified for the
  file/symbol channel; duplicate (never import) `apply_verification_verdicts.py`'s own
  `_entry_spans`/`_FIELD_RE` field-line SHAPE for a new, narrower claim-text extractor
  (`summary:`, falling back to `reason:` for the flat shape) — matching that module's own
  documented cross-boundary convention.

**Block If:** none identified. The Spec (`SPEC.md` CAP-6) gives no clustering algorithm or
similarity threshold, but this is a normal implementation-scoping gap, not a genuine ambiguity:
`apply_verification_verdicts.py`'s own `_normalize` (casefold + whitespace-collapse, EXACT
equality only, explicitly never fuzzy — see its own docstring) is direct, on-point, already-shipped
precedent for the identical kind of text comparison this story needs, so exact-normalized-equality
is the one reasonable reading, not a fantasized one.

**Never:**
- Never implement fuzzy/semantic text similarity (edit distance, token-overlap scoring, or any
  threshold-based match) — normalized EXACT equality only, per the precedent above.
- Never compare on the `evidence:` field — only `summary:`/`reason:` (the entry's own CLAIM, not
  its proof-of-verification text).
- Never reuse `_entry_unused_symbol_claims` — that is Story 11.3's own narrow bare-identifier
  claim shape; this story's file/symbol channel reuses only `_entry_named_paths`.
- Never build a new `Source`, dispatch entry, or `Finding`/model change — a cluster is a new,
  additive `check` value under the existing `Source.DUE_FOR_VERIFICATION`, the same pattern
  `due-for-verification-unevaluable` already established.
- Never merge overlapping clusters (a pair matching on both path AND text) into one combined
  group — each matching channel emits its own independent cluster item; out of scope for this
  story's narrow, mechanical shape.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real precedent shape | 3 due entries, one per project (A, B, C), each citing the identical backtick-quoted path token | One `due-for-verification-cluster` Finding, `matched_on: "path"`, 3 members | No error — happy path |
| Same-project duplicate | 2 due entries in the SAME project citing the identical path token | No cluster emitted (fewer than 2 distinct projects) | No error |
| Near-identical claim text | 2 due entries in different projects with normalized-identical `summary:` (or `reason:`) text | One cluster Finding, `matched_on: "summary"`, 2 members | No error |
| No shared signal | Due entries in different projects with distinct paths and distinct text | No cluster emitted | No error |
| Unreadable ledger during correlation | A project referenced by a due item becomes unreadable when this pass re-reads it | Correlation degrades to zero clusters; every already-computed per-entry Finding is unaffected | No error — isolated, never propagates |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add
  `_entry_claim_text(path) -> dict[str, str]` (new claim-text extractor, duplicated in shape from
  `apply_verification_verdicts.py`'s `_entry_spans`/`_FIELD_RE`), `_normalize_claim(text) -> str`
  (mirrors `apply_verification_verdicts.py`'s `_normalize`), and
  `_correlate_due_for_verification(target, items) -> list[dict]` (the try/except-wrapped
  correlation pass, reusing `_entry_named_paths` unmodified for the path/symbol channel); call it
  once at the end of `_due_for_verification_findings`, extending `findings` with its result before
  returning; add a `due-for-verification-cluster` branch to `_due_for_verification_message`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  extend with the I/O matrix's five scenarios above, plus a public-API test that the cluster
  Finding survives `gather_due_for_verification`'s wrap with `check ==
  "due-for-verification-cluster"` and `evidence` carrying `matched_on`/`matched_value`/`members`.

## Tasks & Acceptance

**Execution:**
- [x] `chain.py` -- add `_entry_claim_text` -- `{id: claim_text}` per tracked ledger, preferring
  `summary:` then `reason:`, first-found wins, entries with neither omitted
- [x] `chain.py` -- add `_normalize_claim` -- casefold + whitespace-collapse, mirroring
  `apply_verification_verdicts.py`'s own `_normalize`
- [x] `chain.py` -- add `_correlate_due_for_verification` -- groups `due-for-verification` items
  (never `-unevaluable`) sharing a path/symbol token or normalized-identical claim text across
  ≥2 distinct projects into `due-for-verification-cluster` items; whole pass wrapped in
  try/except degrading to `[]`
- [x] `chain.py` -- wire the correlation pass into `_due_for_verification_findings` and add the
  new kind's branch to `_due_for_verification_message`
- [x] `test_sources_chain_due_for_verification.py` -- unit-test the I/O matrix's five scenarios

**Acceptance Criteria:**
- Given the real precedent shape (one shared code path cited by due entries in 3 different
  projects), when `gather_due_for_verification` runs, then exactly one
  `due-for-verification-cluster` Finding is produced naming all 3 members.
- Given two due entries sharing a path token within the SAME project, when the sweep runs, then
  no cluster is produced for that pair.
- Given two due entries in different projects with normalized-identical claim text, when the
  sweep runs, then one cluster Finding is produced with `matched_on: "summary"`.
- Given a project's ledger becomes unreadable specifically during the correlation pass, when the
  sweep runs, then every other project's already-computed Finding is still returned and
  clustering degrades to zero clusters rather than raising.
- Given the existing 11.1–11.5 test suite, when it runs after this change, then every existing
  test still passes unmodified.

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium 2, low 5)
- defer: 0
- reject: 4 (low 4)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter + Blind Hunter independently converged on the same root
    cause: `_entry_named_paths`/`_entry_claim_text` return `{id: ...}` dicts keyed by id, so a
    ledger with a duplicate, invariant-violating id (two physical entries sharing one `DW-` id --
    a class this exact file already documents for `_check_project_due_for_verification`'s own
    per-entry attachments) collapses to the last occurrence's data, and every `it` sharing that
    id would list the same (project, id) pair as a member more than once. Fixed: `members` is now
    deduplicated by `(project, id)` before a cluster is emitted, and the residual limitation
    (positional-correctness is NOT restored, only member double-counting is bounded) is documented
    directly in `_correlate_due_for_verification`'s own docstring. New test:
    `test_duplicate_id_within_one_ledger_never_double_counts_a_member`.
  - `[medium]` `[patch]` Blind Hunter: `matched_value` for the `"summary"` channel was the
    NORMALIZED (casefolded/whitespace-collapsed) grouping key, directly contradicting
    `_normalize_claim`'s own docstring ("used ONLY for the cross-project comparison, never
    surfaced as anything a human would read") -- and that mangled value flows straight into
    `Finding.evidence`, a human/agent-facing surface. Fixed: `matched_value` now holds the
    representative member's ORIGINAL claim text (tracked via a new `text_display` dict, first-seen
    wins), with the normalized form used only internally as the grouping key. New tests:
    `test_matched_value_is_never_the_normalized_grouping_key`, plus an added assertion on the
    existing summary-cluster test pinning the exact original-text value.
  - `[low]` `[patch]` Blind Hunter: paired with the fix above -- the summary channel's WARN
    message said only "normalized-identical claim text" with no hint of what matched, asymmetric
    with the path channel's inline token. Fixed: the message now shows a truncated (80-char)
    excerpt of the real `matched_value` for both channels, quoted for the summary case.
  - `[low]` `[patch]` Blind Hunter: the `reason:`-only flat-shape fallback (an explicit Tasks &
    Acceptance item) had zero test coverage. Added
    `test_reason_only_flat_shape_entries_cluster_on_reason_text`.
  - `[low]` `[patch]` Blind Hunter: the summary-present-but-empty -> falls back to `reason:`
    precedence was unverified by any test (only documented in prose). Confirmed the existing
    `fields.get("summary") or fields.get("reason")` behavior is correct as written (an empty
    summary must never become a match key -- that would spuriously cluster every blank-summary
    entry together) and locked it in with `test_empty_summary_field_falls_back_to_reason`.
  - `[low]` `[patch]` Blind Hunter: the docstring's own "2-in-A + 1-in-B -> one 3-member cluster"
    claim had no test exercising mixed same-project/cross-project membership. Added
    `test_two_in_one_project_plus_one_in_another_form_a_three_member_cluster`.
  - `[low]` `[patch]` Blind Hunter: the "never merge overlapping clusters" hard Boundary (a pair
    matching on both path AND text) had no regression test at all. Added
    `test_dual_match_on_path_and_text_never_merges_into_one_cluster`.
  - `[low]` `[reject]` Blind Hunter: redundant, uncached re-parsing of each project's ledger --
    `_check_project_due_for_verification` already computed `_entry_named_paths` for the per-entry
    pass, and the correlation pass re-reads independently. Rejected on the same factual grounds as
    Story 11.5's equivalent finding: this repo's real fleet size is 8 projects (confirmed via
    `ls _bmad-output/projects/`), so re-reading ~8 small markdown files twice more is genuinely
    negligible, and threading the already-computed data through would require a larger, less
    surgical signature change to `_check_project_due_for_verification` -- exactly the kind of
    change Story 11.5's own review already established should be avoided to protect its existing
    monkeypatch-based isolation test.
  - `[low]` `[reject]` Blind Hunter: an unacknowledged TOCTOU window between the per-project pass
    and the correlation pass's independent re-read. Rejected: this is the same accepted,
    non-transactional-consistency property already present throughout `_due_for_verification_findings`
    (rejected for the identical reason in Story 11.5's review) -- the consequence here is a
    silently-missing signal (`.get(id, [])` returning empty), never corruption or a crash.
  - `[low]` `[reject]` Blind Hunter: `_entry_claim_text`'s internal `"reason"` field-name and the
    unrelated per-item `item["reason"]` evidence key ("never-verified"/"stale") share a bare word
    in the same module. Rejected: purely lexical, no actual variable/scope collision (two
    entirely separate dicts that never interact) -- a cosmetic grep-ambiguity nit, not a
    functional risk.
  - `[low]` `[reject]` Blind Hunter: one flaky/unreadable project during correlation zeroes out
    every cluster fleet-wide, a large blast radius for a single bad read. Rejected: this is the
    Boundaries' own explicit, deliberate, already-justified design decision (blanket try/except
    over per-key isolation, because a partial cross-project index risks a cluster missing a
    member or a real cluster going unreported) -- Blind Hunter's own finding text acknowledges
    "this is spec-mandated behavior, not a bug."

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green
  (pre-existing flaky `test_check_speed_budget.py` timing test aside, unrelated to this change)
- `pixi run -e pyforge-doctor ruff check src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- expected: zero NEW findings (this file already carries 7 pre-existing
  errors on main, unrelated to this story; confirm via `git stash` against the pre-change
  baseline that the count and locations are unchanged)

## Auto Run Result

Status: done

**Summary.** Added a read-only post-processing pass to `chain.py`: `_entry_claim_text` (claim-text
extractor duplicated in shape from `apply_verification_verdicts.py`'s `_entry_spans`/`_FIELD_RE`),
`_normalize_claim` (mirrors that module's own `_normalize`), and `_correlate_due_for_verification`
(the correlation pass itself). Wired once into `_due_for_verification_findings` after the
per-project loop. Two or more `due-for-verification` items across DIFFERENT projects sharing a
backtick-quoted path/symbol token, or normalized-identical `summary:`/`reason:` claim text, now
surface as one additive `due-for-verification-cluster` Finding — reproducing the real 2026-07-30
precedent (`bmad-ui`'s `./build_artifacts` channel, hit 3x across 3 projects) end to end in a new
test.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- new
  `_CLAIM_FIELD_RE`/`_entry_claim_text`/`_normalize_claim`/`_correlate_due_for_verification`; one
  call site in `_due_for_verification_findings`; a new branch in `_due_for_verification_message`.
  Review added: per-`(project, id)` member deduplication and a documented residual
  duplicate-id-ledger limitation; `matched_value` now holds original (never normalized) claim
  text; the WARN message shows a real excerpt for both channels.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  12 new tests (6 from implementation + 6 added in review) covering the full I/O matrix, the
  original-text `matched_value` guarantee, the `reason:`-fallback and empty-summary-precedence
  paths, the mixed-membership 3-cluster shape, the dual-channel never-merges boundary, and the
  duplicate-id member-dedup fix.

**Review findings breakdown:** 7 patched (2 medium, 5 low -- see Review Triage Log for full
detail), 4 rejected as pre-existing/already-accepted-tradeoff/cosmetic, 0 deferred, 0 intent gaps,
0 bad-spec loopbacks.

**Follow-up review recommendation:** false -- both medium fixes are narrow, well-precedented
corrections (member dedup mirrors an established file convention; original-text `matched_value`
restores the already-written docstring's own promise) each directly proven by a new test; the
five low fixes are test-coverage additions locking in already-correct behavior, plus one message
readability improvement. Narrow, verified, not broad enough to warrant an independent second pass.

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 1075
passed, 2 skipped (pre-existing flaky speed-budget test unaffected). `ruff check` on both touched
files -- 7 pre-existing findings, 0 new (confirmed against the pre-change baseline via
`git stash`). `pytest tests/meta/test_read_only_guard.py tests/meta/test_source_independence.py`
-- 68 passed, confirming the new code stays pure read-only and imports no other station's
package.

**Residual risks:** the duplicate-id-ledger limitation is bounded (never double-counts a member)
but not fully positionally correct — documented explicitly in `_correlate_due_for_verification`'s
own docstring as an accepted, narrow gap for an already-malformed, advisory-only data state.
