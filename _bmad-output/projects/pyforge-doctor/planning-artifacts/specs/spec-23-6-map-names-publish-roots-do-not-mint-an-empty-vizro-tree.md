---
title: '23.6: MAP names publish roots; do not mint an empty vizro/ tree'
type: 'fix'
created: '2026-09-16'
status: 'done'
baseline_revision: '1a0857aa9be731c5868e3f1f76bcb2b46d621a43'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      This story's own tracking artifacts (sprint-status-ledger.yaml key
      23-6-…, epics.md's Story 23.6 section) still read backlog even as the
      spec advances through in-review to done.
    evidence: |-
      Real desync, but ledger/epics promotion is a distinct post-merge step
      (sprint-ledger-sync) that this build-auto workflow does not perform —
      it happens at landing time per this repo's own established convention
      (see git log: "marshal: promote sprint-status ledger ... -> done"
      commits following each merge).
    location: >-
      planning-artifacts/sprint-status-ledger.yaml,
      planning-artifacts/epics.md (Story 23.6)
    severity: medium
  - summary: >-
      spec-pyforge-doctor/SPEC.md's CAP-53 annotation still reads
      "(ready 2026-09-17)" even as the underlying story spec advances.
    evidence: |-
      Confirmed pre-existing and systemic, not caused by this diff: every
      sibling CAP-48..54 annotation in the same block carries the identical
      stale "(ready 2026-09-17)" marker, including CAP-50 whose story (23.3)
      is already done. This diff doesn't touch SPEC.md; fixing the pattern
      is a separate, repo-wide reconciliation across all seven CAPs.
    location: >-
      _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md:222
    severity: low
  - summary: >-
      Sibling story 23.5's three status trackers disagree with each other
      (spec still 'ready', epics.md still backlog, ledger already done).
    evidence: |-
      Real, but about a different story entirely and outside this spec's
      declared Surface (docs/MAP.md, docs/dashboard/README.md). This diff's
      herald memlog entry only reconciles spec-surface hashes for 23.5's
      already-landed citation fix; it does not and should not touch 23.5's
      own status fields.
    location: >-
      _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-23-5-archive-citations-for-the-five-already-moved-_bmad-output-files.md
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** docs/dashboard/kedro-viz/ is a generated Pages upload root and Vizro is a different product.

**Approach:** MAP and the dashboard README state one subfolder per board. kedro-viz is not renamed. docs/dashboard/vizro/ does not exist unless a later publish story created it.

## Boundaries & Constraints

**Always:**
- kedro-viz keeps its name.
- No empty docs/dashboard/vizro/ tree is minted.

**Never:**
- Do not rename kedro-viz.
- Do not mint an empty vizro/ directory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MAP after story | docs/MAP.md | one subfolder per board; no vizro/ invent | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-6`.
Surface: docs/MAP.md, docs/dashboard/README.md..
Ledger key: `23-6-map-names-publish-roots-do-not-mint-an-empty-vizro-tree`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-6-map-names-publish-roots-do-not-mint-an-empty-vizro-tree.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 6 findings — high 0, medium 3, low 2, false 1, maybe-false 0
- findings:
  - `[medium]` `[defer]` Blind Hunter: this story's own tracking artifacts (`sprint-status-ledger.yaml` key `23-6-…`, `epics.md`'s `### Story 23.6`) still read `backlog` while the spec advances to `in-review`/`done` — evidence: real desync, but ledger/epics promotion is a distinct post-merge step (`sprint-ledger-sync`) this build-auto workflow does not perform; not this story's diff to fix.
  - `[medium]` `[patch]` Blind Hunter: the new `docs/MAP.md`/`docs/dashboard/README.md` prose claims "one subfolder per published dashboard board" / "today only `kedro-viz/`… publishes" but omits the PyForge dossier/infographic site (`docsite/build.py` + `.github/workflows/dashboard.yml`) that publishes directly into the *root* of `docs/dashboard/` (`index.html`, `dossier/`, `infographics/`, `decks/`, `artifact/`, per `.gitignore`'s own "shared publish root" note) — not in a subfolder at all. Verified by reading `docsite/build.py::build()` (writes `out_dir/index.html`, `out_dir/dossier/`, etc. directly) and `dashboard.yml`. Fix applied: `docs/MAP.md`'s new row and `docs/dashboard/README.md`'s new paragraph each gained a clause naming the PyForge dossier/infographic site as the one exception that publishes directly at the root rather than its own subfolder; "today only `kedro-viz/`… publishes" reworded to "…publishes **as a subfolder**".
  - `[low]` `[patch]` Blind Hunter: `docs/dashboard/README.md`'s new cross-reference reads "(see `docs/MAP.md` § Outside this map)" but the actual heading is `## Outside this map (untouched)` — evidence: `grep` confirms the heading text; fix is a direct one-word addition. Fix applied: citation corrected to "§ Outside this map (untouched)".
  - `[low]` `[defer]` Blind Hunter: `spec-pyforge-doctor/SPEC.md`'s `CAP-53` annotation still reads `← spec-docs-shelf-alignment CAP-6 (ready 2026-09-17)` even as the story spec moves to `in-review` — evidence: confirmed pre-existing and systemic, not caused by this diff — every sibling CAP-48..54 annotation in the same block carries the identical stale `(ready 2026-09-17)` marker, including CAP-50 whose story (23.3) is already `done`; this diff doesn't touch `SPEC.md` and fixing the pattern is a separate, repo-wide reconciliation.
  - `[medium]` `[defer]` Blind Hunter: sibling story 23.5's three status trackers disagree (`spec-23-5-…md` still `status: 'ready'` with no `baseline_revision`; `epics.md`'s `### Story 23.5` still `backlog`; `sprint-status-ledger.yaml`'s `23-5-…` key already `done`) — evidence: real, but about a different story entirely, outside this spec's declared Surface (`docs/MAP.md`, `docs/dashboard/README.md`); this diff's herald memlog entry only reconciles spec-surface hashes for 23.5's already-landed citation fix, it does not and should not touch 23.5's own status fields.
  - `[false]` `[reject]` Intent Alignment Auditor: the spec's cited `## Verification` command (`pyforge-doctor-test`) doesn't itself assert the new prose content or the absence of `docs/dashboard/vizro/` — checked: the intent-contract's own Approach scopes this story to stating the convention in docs only (no enforcement mechanism), and a dedicated follow-on story already exists for automated enforcement (`spec-23-7-a-new-doctor-source-flags-leftover-shelf-occupancy.md`, same CAP-6/CAP-7 family, "a new warn-only… source compares leftover-shelf paths to the MAP allow-list") — matches this repo's own established split-convention pattern (state-the-rule story, then a separate detect-violations story) confirmed on the identical spec-23-3 precedent — no bad outcome for this story.

## Auto Run Result

**Summary:** `docs/MAP.md` and `docs/dashboard/README.md` now state the "one subfolder per published dashboard board" publish-root convention explicitly: `kedro-viz/` keeps its name as the only board currently publishing in its own subfolder, the PyForge dossier/infographic site is named as the one exception publishing directly at the `docs/dashboard/` root, and Vizro is called out as a separate product for which no subfolder is minted ahead of an actual publish. No `docs/dashboard/vizro/` directory exists in the working tree; `kedro-viz/` was not renamed.

**Files changed:**
- `docs/MAP.md` — new "Publish roots (generated)" row in the "Outside this map" table.
- `docs/dashboard/README.md` — rewritten to state the convention, the PyForge-dossier root-level exception, and the Vizro no-empty-mint rule.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — surface reconcile entry for `docs/MAP.md`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile entry for `docs/dashboard/README.md` (co-governed).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md` — surface reconcile entry for a pre-existing, already-landed drift found during this pass: sibling story 23.5's `presentations/six-quarter-roadmap/project/github.md` citation fix had never been stamped against `spec-pyforge-herald`'s baseline; content unchanged by this diff, only the baseline hash reconciled.
- `scripts/.spec-surface-baseline.json` — hash stamps updated for the four files above.

**Review findings breakdown (6 total across 4 layers: Blind Hunter 5, Edge Case Hunter 0, Verification Gap Reviewer 0, Intent Alignment Auditor 1):**
- 2 `patch` (1 medium, 1 low): the new prose's "one subfolder per board" framing omitted the PyForge dossier/infographic site, which publishes directly at the `docs/dashboard/` root rather than a subfolder (verified against `docsite/build.py`, `dashboard.yml`, `.gitignore`) — clarified in both files; a citation in `docs/dashboard/README.md` dropped "(untouched)" from the `docs/MAP.md` heading it points to — corrected. Both re-verified: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` green after the patch.
- 3 `defer` (2 medium, 1 low): this story's own ledger/epics.md rows still read `backlog` (post-merge sync, not this workflow's step); `spec-pyforge-doctor/SPEC.md`'s CAP-53 annotation is stale but identically so across all seven sibling CAP-48..54 entries, a pre-existing systemic pattern; sibling story 23.5's three status trackers disagree with each other, which is real but entirely outside this story's declared Surface. See `deferred:` frontmatter for full evidence.
- 1 `reject` (false): Intent Alignment Auditor's observation that `pyforge-doctor-test` doesn't itself verify the new prose or the absence of `docs/dashboard/vizro/` — the intent-contract scopes this story to documentation only, and a dedicated follow-on enforcement story (23.7, same CAP family) already exists, matching this repo's established split-convention pattern.

**Follow-up review recommendation: `false`** (this pass patched 1 medium + 1 low; the mechanical rule requires either a patched `high` or two-or-more patched `medium` entries, neither of which occurred).

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1785 passed, 1 skipped, exit 0 (run both before and after the two patches). `test -d docs/dashboard/vizro` — absent. `git log` — `kedro-viz/` not renamed. Matrix row ("MAP after story") confirmed by direct inspection of the rendered `docs/MAP.md`/`docs/dashboard/README.md` text, consistent with this repo's established precedent for docs-only fix stories in the same epic (e.g. spec-23-3's Auto Run Result).

**Residual risks:** none rated `medium`+ remain unaddressed within this story's Surface. The three deferred items (ledger/epics sync for 23.6 and 23.5, and the systemic stale-CAP-annotation pattern in `spec-pyforge-doctor/SPEC.md`) are recorded in `deferred:` frontmatter for a future reconciliation pass; none is load-bearing for this story's own acceptance criteria.

