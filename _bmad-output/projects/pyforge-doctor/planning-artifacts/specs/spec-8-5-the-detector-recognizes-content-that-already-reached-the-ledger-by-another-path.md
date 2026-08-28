---
title: 'Story 8.5: The detector recognizes content that already reached the ledger by another path'
type: 'bug'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      The normalized-summary exemption could in principle mask two genuinely distinct findings
      that happen to share byte-identical normalized `summary:` text.
    evidence: |-
      Review-pass finding (2026-08-28): acknowledged as the same accepted tradeoff the write-
      side `deferred_work_promote.py` guard it mirrors already makes -- confirmed byte-identical
      `_normalize_summary` logic between the two files. Not a new defect this story introduces;
      full fuzzy/near-duplicate matching is explicitly out of scope, same rationale as the
      original write-side guard.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
      (_tier3_entry_already_promoted)
    severity: low
baseline_revision: 'f244a36cb519c9e2b4f0edb693436c66ec8f6d69'
---

<intent-contract>

## Intent

**Problem:** A fleet-wide hygiene sweep (2026-08-28) re-ran `deferred-work-check` and found 117
standing `tier3-only-deferral`/`tier3-entry-unidentified` findings across doctor/marshal/mason/
scribe/steward/atlas. Investigating pyforge-atlas's own findings confirmed a real, live
ID-vs-content mismatch: a Tier-3 entry's content can already have reached the tracked ledger by
some OTHER path (a prior `--fix` run, a hand-edit, the CAP-8 spec-frontmatter bridge) under a
DIFFERENT, independently-minted id — the id/position-based comparison alone cannot see this and
wrongly flags the entry as missing. Two concrete confirmed cases:

1. pyforge-atlas's own Tier-3 line 7: `summary:` text byte-identical to its own tracked
   `DW-A1-6`, under a completely different id.
2. pyforge-atlas's own `DW-10`: no `summary:` field at all (a bmad-loop harvest-damping entry,
   CAP-8's own shape), but its `origin: spec-deferred 8b4c28559f93` marker already appears in
   the tracked ledger — promoted via the spec-frontmatter path under yet another different id.

`scripts/deferred_work_promote.py`'s own `_validate_batch` write-side collision guard already
defends against case 1 (a normalized-summary match) when actually WRITING a promotion; the
detector had no read-side analogue. Case 2 mirrors CAP-8's own already-shipped
`frontmatter_deferral_in_tracked` needle-search convention exactly — no new mechanism invented
either way.

**Approach:** Add `_tracked_summaries` (collects every normalized `summary:` text already in the
tracked ledger, via the existing `classify_tier3_entries` — which already reads either a Tier-3
or a tracked-ledger file) and `_tier3_entry_already_promoted` (checks a flagged entry against
both signals: normalized-summary membership, or its `origin: spec-deferred <fingerprint>` marker
present as a substring of the tracked ledger's raw text). Wire both into the existing
`tier3-entry-unidentified` and `tier3-only-deferral` flagging loops as an exemption.

**Explicitly bounded, not a full-backlog claim:** this closes the ID-vs-content-mismatch class
specifically — 6 of 117 findings on the live repo, all in pyforge-atlas, confirmed via `git
stash` A/B testing. The remaining ~111 are NOT asserted to be false positives by this story —
Epic 8's own closing note already scoped the full 300+-entry fleet-wide backlog promotion, and
`DW-FU-8-4`'s collision-abort redesign, as deliberate future work, not something this story
silently leaves incomplete.

## Acceptance Criteria

- **Given** a Tier-3 entry whose normalized `summary:` text already appears in the tracked
  ledger under a different id **Then** it is not flagged, on both the `tier3-only-deferral` and
  `tier3-entry-unidentified` paths.
- **Given** a Tier-3 entry with no `summary:` field but a matching `origin: spec-deferred
  <fingerprint>` marker already in the tracked ledger **Then** it is not flagged.
- **Given** a Tier-3 entry with a genuinely DIFFERENT summary or fingerprint **Then** it is still
  flagged exactly as before — pinned by dedicated negative tests.
- **Given** the live repo **Then** the finding count drops from 117 to 111 (6 genuine false
  positives closed, all pyforge-atlas) — not to 0; this story does not claim to resolve the
  remaining backlog.

## Boundaries & Constraints

**Always:**
- Both exemption signals mirror ALREADY-SHIPPED logic exactly (`deferred_work_promote.py`'s
  `_validate_batch` for the summary check, `frontmatter_deferral_in_tracked` for the fingerprint
  check) — no new duplicate-detection design invented.
- `_normalize_summary` is duplicated locally (the mutation script `deferred_work_promote.py`
  cannot be imported into the installed `pyforge-doctor` package — a repo-level script importing
  INTO a package's read-only source is backwards), matching this module's own existing
  duplication precedent (`sources/marshal.py`'s `_GITHUB_MERGE_SUBJECT_RE`).
- Hoist the pre-existing `tracked_text` read earlier in `_check_project_deferred_work` so the new
  fingerprint check and the pre-existing spec-frontmatter check share one read, not two.
- Add regression tests pinning both signals, both positive and negative cases.

**Never:**
- Never claim or attempt to resolve the full 111-finding remainder — that is Epic 8's own
  already-scoped future work (the first real fleet-wide `--fix` run, `DW-FU-8-4`'s redesign).
- Never touch `scripts/deferred_work_promote.py` or `deferred_work_intake.py` — this story is
  read-side (detector) only.
- Never weaken the id/position-based checks themselves — the exemption is additive, applied only
  to entries that would otherwise be flagged.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Matching summary, different id | Tier-3 `summary:` byte-identical to a tracked entry's | Not flagged | — |
| Different summary, both present | Genuinely different `summary:` text on both sides | Still flagged | never silently suppressed |
| Matching fingerprint, no summary | Tier-3 `origin: spec-deferred X`, tracked carries the same `X` | Not flagged | — |
| Different fingerprint | Tier-3 `origin: spec-deferred X`, tracked carries only `Y` | Still flagged | — |
| Anonymous (position-based) entry, matching summary | Same exemption on the `tier3-entry-unidentified` path | Not flagged | shares one helper with the id-based path |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` —
  `_normalize_summary`, `_tracked_summaries`, `_TIER3_ORIGIN_FINGERPRINT_RE`,
  `_tier3_entry_already_promoted` (new); `_check_project_deferred_work` (hoists `tracked_text`,
  wires the new exemption into both flagging loops, removes the now-duplicate later
  `tracked_text` read).
- `scripts/deferred_work_promote.py` (read-only reference) — `_normalize_summary`'s original,
  `_validate_batch`'s own collision-guard rationale, mirrored exactly.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py`'s own
  `frontmatter_deferral_in_tracked`/`HARVEST_ORIGIN` (read-only reference) — the fingerprint
  needle-search convention, mirrored exactly.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — 5 new
  tests: summary-match positive/negative, fingerprint-match positive/negative, and the anonymous
  (position-based) path sharing the same exemption.

## Review Triage Log

### 2026-08-28 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 2, low 1)
- defer: 1 (high 0, medium 0, low 1)
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` `_TIER3_ORIGIN_FINGERPRINT_RE` captured the fingerprint as bare `\S+`,
    unlike the module's own sibling `_ORIGIN_LINE_RE` (`[0-9a-f]{12}`). A malformed/truncated
    origin field (never minted by this repo's own tooling, but possible on a hand-edited entry)
    could prefix-match an unrelated, longer token elsewhere in the tracked ledger's raw text.
    Fixed: bounded to the same `[0-9a-f]{12}\b` shape.
  - `[medium]` `[patch]` The fingerprint check matched only the origin needle, not the
    `source_spec:` cross-check `frontmatter_deferral_in_tracked` (the function it claims to
    mirror "exactly") actually requires. Since a fingerprint is a 48-bit hash of `(summary,
    location)`, two genuinely distinct findings sharing identical summary+location text (e.g.
    copy-pasted boilerplate) could collide and produce a false exemption the real function
    would have caught. Fixed: extracted the shared basename-matching logic into
    `_source_spec_cited_in` (used by both `frontmatter_deferral_in_tracked` and the new
    exemption), and the fingerprint check now requires both signals, exactly mirroring the
    pattern it claims to reuse.
  - `[low]` `[patch]` `classify_tier3_entries(t3_path)` was called twice (once per lookup dict),
    costing ~4% on the already-tight `test_doctor_check_completes_within_the_five_second_budget`
    (5.37-5.54s before this diff → 5.61-5.70s after, measured across 3 iterations each side).
    Fixed: parsed once, split into both dicts from the one result.
  - `[low]` `[defer]` The normalized-summary exemption could in principle mask two genuinely
    distinct findings that happen to share byte-identical normalized text — acknowledged as the
    same accepted tradeoff the write-side `deferred_work_promote.py` guard it mirrors already
    makes (confirmed byte-identical `_normalize_summary` logic between the two files by the
    review pass), not a new defect this story introduces.
- Independently reconfirmed, no discrepancy found: 117→111 finding count (delta 6, all
  pyforge-atlas) re-derived via `git stash` A/B; all 88 unit tests pass, with both exemption
  signals individually mutation-tested (disabling each in turn fails exactly its own dedicated
  tests, nothing else); full suite 1302 passed / 3 failed, all 3 confirmed pre-existing via
  `git stash`; the `tracked_text` hoist confirmed to change no behavior for the pre-existing
  spec-frontmatter check it now shares a read with.

## Auto Run Result

Status: done

**Summary:** Closed a real, live-confirmed ID-vs-content mismatch class in `deferred-work-check`
(doctor's own detector for the Tier-3-vs-tracked-ledger deferred-work backlog): a Tier-3 entry
whose content already reached the tracked ledger by some OTHER path (a prior promotion run, a
hand-edit, the CAP-8 spec-frontmatter bridge) under a DIFFERENT, independently-minted id was
wrongly flagged as missing. Two exemption signals, both mirroring already-shipped logic exactly
rather than inventing anything new: a normalized-summary match (mirrors
`deferred_work_promote.py`'s own write-side `_validate_batch` collision guard) and an
`origin: spec-deferred <fingerprint>` + `source_spec:` cross-check (mirrors
`frontmatter_deferral_in_tracked` exactly, after the review pass added the cross-check this
story's first draft was missing). Confirmed live: pyforge-atlas's own Tier-3 line 7 (summary
byte-identical to tracked `DW-A1-6`) and `DW-10` (fingerprint-matched, promoted via the
spec-frontmatter path) both stop being flagged. **Explicitly bounded:** closes 6 of 117 live
findings, all pyforge-atlas; the remaining ~111 are Epic 8's own already-scoped, deliberately-
deferred future work (the first real fleet-wide `--fix` run, blocked on `DW-FU-8-4`'s own
collision-abort redesign), not something this story silently leaves incomplete.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — the fix:
  `_normalize_summary`, `_tracked_summaries`, `_source_spec_cited_in` (extracted, shared with
  `frontmatter_deferral_in_tracked`), `_TIER3_ORIGIN_FINGERPRINT_RE`,
  `_tier3_entry_already_promoted`; `_check_project_deferred_work` hoists `tracked_text`, wires
  the exemption into both flagging loops, parses `t3_path` once instead of twice.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — 5 new
  tests: summary-match positive/negative, fingerprint-match positive/negative, and the anonymous
  (position-based) path sharing the same exemption.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`
  — new CAP-11.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md` — new Story 8.5.
- This spec file (new).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` — ledger
  key added (dispatcher finalize, flipped to `done` alongside this file's own `status` field).

**Review findings breakdown:** 3 `patch` (2 medium, 1 low) — the fingerprint regex bound, the
missing `source_spec` cross-check, and the redundant parse; all fixed. 1 `defer` (low) — the
summary-match exemption's inherent, already-accepted collision tradeoff. 0 `reject`.

**Follow-up review recommendation:** `true`. 2 medium patches cross the numeric threshold this
campaign's sibling stories use (`3*0 + 1*(2+1) = 3`... below 5 on the raw score, but this
touches a detector every station's backlog visibility depends on, and the fix's own value (6 of
117) is modest enough that a second look once the remaining ~111 get real triage attention is
worth keeping open).

**Verification performed:**
- `python -m pyforge.doctor.sources deferred-work` on the live repo — 117 findings → 111, before
  and after, independently re-confirmed by the review pass via `git stash`. Re-confirmed again
  after the review-pass patches: still 111 (the tightened source_spec cross-check did not lose
  the real fix — both live atlas examples happen to already carry a matching `source_spec`).
- `pixi run --frozen -e pyforge-doctor pytest tests/unit/test_sources_chain_deferred_work.py`
  — 88 passed (83 pre-existing + 5 new).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1302 passed, 3 failed, all 3
  confirmed pre-existing via `git stash`, both before and after the review-pass patches.
- Both exemption signals independently mutation-tested by the review pass (disabling each in
  turn fails exactly its own dedicated tests).
- `git diff --stat -- src/shared/packages/pyforge-core src/shared/packages/pyforge-marshal` --
  not applicable to this story's own surface (doctor-only); no changes outside
  `pyforge-doctor`'s own package confirmed via `git status --porcelain`.

**Residual risks:** The ~111 remaining `deferred-work-check` findings are NOT resolved by this
story and are not claimed to be. Per Epic 8's own closing note, the full fleet-wide backlog
promotion (`deferred_work_promote.py --fix` run for real against all 8 projects) and
`DW-FU-8-4`'s collision-abort redesign are both deliberate, already-scoped future work — this
story's own scope is the narrower ID-vs-content-mismatch class in the DETECTOR specifically.
Landing (git commit beyond this session's working tree, the ledger flip for key
`8-5-the-detector-recognizes-content-that-already-reached-the-ledger-by-another-path`, and the
`maintenance` PR label) is the dispatcher's, matching every other story landed this session.
