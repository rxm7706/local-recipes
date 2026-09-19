---
title: '23.6: MAP names publish roots; do not mint an empty vizro/ tree'
type: 'fix'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '1a0857aa9be731c5868e3f1f76bcb2b46d621a43'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
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
  - `[medium]` `[patch]` Blind Hunter: the new `docs/MAP.md`/`docs/dashboard/README.md` prose claims "one subfolder per published dashboard board" / "today only `kedro-viz/`… publishes" but omits the PyForge dossier/infographic site (`docsite/build.py` + `.github/workflows/dashboard.yml`) that publishes directly into the *root* of `docs/dashboard/` (`index.html`, `dossier/`, `infographics/`, `decks/`, `artifact/`, per `.gitignore`'s own "shared publish root" note) — not in a subfolder at all. Verified by reading `docsite/build.py::build()` (writes `out_dir/index.html`, `out_dir/dossier/`, etc. directly) and `dashboard.yml`. Action: clarify the new prose to name the root-level PyForge site alongside the "one subfolder per board" rule so it isn't misread as universal.
  - `[low]` `[patch]` Blind Hunter: `docs/dashboard/README.md`'s new cross-reference reads "(see `docs/MAP.md` § Outside this map)" but the actual heading is `## Outside this map (untouched)` — evidence: `grep` confirms the heading text; fix is a direct one-word addition.
  - `[low]` `[defer]` Blind Hunter: `spec-pyforge-doctor/SPEC.md`'s `CAP-53` annotation still reads `← spec-docs-shelf-alignment CAP-6 (ready 2026-09-17)` even as the story spec moves to `in-review` — evidence: confirmed pre-existing and systemic, not caused by this diff — every sibling CAP-48..54 annotation in the same block carries the identical stale `(ready 2026-09-17)` marker, including CAP-50 whose story (23.3) is already `done`; this diff doesn't touch `SPEC.md` and fixing the pattern is a separate, repo-wide reconciliation.
  - `[medium]` `[defer]` Blind Hunter: sibling story 23.5's three status trackers disagree (`spec-23-5-…md` still `status: 'ready'` with no `baseline_revision`; `epics.md`'s `### Story 23.5` still `backlog`; `sprint-status-ledger.yaml`'s `23-5-…` key already `done`) — evidence: real, but about a different story entirely, outside this spec's declared Surface (`docs/MAP.md`, `docs/dashboard/README.md`); this diff's herald memlog entry only reconciles spec-surface hashes for 23.5's already-landed citation fix, it does not and should not touch 23.5's own status fields.
  - `[false]` `[reject]` Intent Alignment Auditor: the spec's cited `## Verification` command (`pyforge-doctor-test`) doesn't itself assert the new prose content or the absence of `docs/dashboard/vizro/` — checked: the intent-contract's own Approach scopes this story to stating the convention in docs only (no enforcement mechanism), and a dedicated follow-on story already exists for automated enforcement (`spec-23-7-a-new-doctor-source-flags-leftover-shelf-occupancy.md`, same CAP-6/CAP-7 family, "a new warn-only… source compares leftover-shelf paths to the MAP allow-list") — matches this repo's own established split-convention pattern (state-the-rule story, then a separate detect-violations story) confirmed on the identical spec-23-3 precedent — no bad outcome for this story.

