---
title: 'Record the vscode-kedro verdict'
type: 'feature'
created: '2026-08-09'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/planning-artifacts/specs/spec-kedro-org-tooling-adoption/SPEC.md']
warnings: []
baseline_revision: '9850f743cc63bc60ea40e3db698a6f3069e8eaf5'
final_revision: 'dae8b4ca6a'
---

<intent-contract>

## Intent

**Problem:** Epic 12 (FR-63) requires an explicit, dated adopt/defer decision on `kedro-org/vscode-kedro` — a live, maintained VS Code/Cursor extension (v0.8.0, 21★, pushed today) that Atlas has never evaluated. Silence is not a valid outcome; the epic's Non-goals section is explicit that no particular answer is pre-ordained, only that a recorded decision must exist.

**Approach:** Write a dated decision document recording **defer**, evidenced by two facts verified against this live repo: (1) this repo's Kedro code is authored and maintained ~entirely by bmad-loop agents (38/38 Epic-migration stories), not the interactive human sessions the extension targets; (2) the extension's catalog Schema Validation duplicates work already covered deterministically by the `kedro-catalog-check` pytest gate. As the zero-cost middle ground for the rare human session, also add `.vscode/extensions.json` recommending the extension (`kedro.Kedro`, confirmed from upstream `package.json`) — no installation or further configuration.

## Boundaries & Constraints

**Always:** The decision is dated, states its reason, and is committed at `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/vscode-kedro-decision.md` — alongside the epic's `SPEC.md` and the sibling `kedro-skills-audit-report.md`, where the epic's own "next reader" already looks. "Defer" is a valid, final verdict; it requires no installed extension, only the recorded decision plus the optional recommendation file.

**Block If:** A live re-check of `kedro-org/vscode-kedro` (stars/license/archived/pushed) shows a materially different tool than the 2026-08-08 research assumed (e.g. archived, license change, stated deprecation). Already re-verified live today (2026-08-09 via `gh api`): still Apache-2.0, unarchived, 21★, pushed today. No block triggers.

**Never:** Do not install or configure the vscode-kedro extension itself, or add any settings beyond the one-line recommendation. Do not modify `.vscode/settings.json`. Do not re-open `kedro-mcp` or `kedro-builder` — both are explicit epic Non-goals.

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/vscode-kedro-decision.md` -- NEW: dated decision record fulfilling epic SPEC Capability 3
- `.vscode/extensions.json` -- NEW: one-line `{"recommendations": ["kedro.Kedro"]}` — extension ID confirmed via `kedro-org/vscode-kedro`'s `package.json` (`publisher: kedro`, `name: Kedro`)

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/vscode-kedro-decision.md` -- write dated defer verdict with the two evidenced reasons plus the live re-check facts -- closes FR-63. Verified: `test -f .../vscode-kedro-decision.md` → exit 0; `grep -qi "defer" .../vscode-kedro-decision.md` → exit 0 (verdict stated, with the live `gh api` re-check plus both evidenced reasons).
- [x] `.vscode/extensions.json` -- add `{"recommendations": ["kedro.Kedro"]}` -- the epic's named zero-cost middle ground for a deferral. Verified: `python3 -c "import json; d=json.load(open('.vscode/extensions.json')); assert d=={'recommendations': ['kedro.Kedro']}"` → no error; `git status --porcelain .vscode/settings.json` → no output (untouched).

**Acceptance Criteria:**
- Given the vscode-kedro evaluation, when this story completes, then a dated adopt/defer decision with a stated reason exists at the path above and is committed to version control.
- Given the decision is "defer", when this story completes, then `.vscode/extensions.json` exists with exactly one recommendation, is valid JSON, and no other vscode-kedro installation or configuration exists anywhere in the repo.

## Spec Change Log

(none — no bad_spec loopback occurred)

## Review Triage Log

### 2026-08-09 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 0, medium 0, low 4)
- defer: 0
- reject: 9
- addressed_findings:
  - `[low]` `[patch]` (Blind Hunter) The doc's kedro-mcp contrast misstated history — FR-7 wrapped kedro-mcp non-load-bearing as an architectural decision; dormancy was a later research finding that *vindicated* it, not the original reason. Fixed: reworded the contrast in the "Live re-check" section to state the architectural reason first and dormancy as later vindication.
  - `[low]` `[patch]` (Blind Hunter) "No block condition fires" didn't enumerate which of the intent-contract's three named block conditions were actually checked. Fixed: now states each explicitly (archived: false, license unchanged, no deprecation notice found).
  - `[low]` `[patch]` (Blind Hunter) `.vscode/extensions.json` had no in-repo provenance pointing a future reader at the decision doc explaining why it exists. Fixed: added a JSONC comment (this repo's own `.vscode/settings.json` already uses comments, confirmed live before applying) pointing to `vscode-kedro-decision.md`.
  - `[low]` `[patch]` (Edge Case Hunter, both findings deduped as one fix) The `kedro.Kedro` extension ID was only derived from the source repo's `package.json`, never cross-checked against either live registry it must actually resolve against — material because Cursor resolves `.vscode/extensions.json` via Open VSX, not the VS Code Marketplace, per vscode-kedro's own README. Verified live: Marketplace gallery API and `open-vsx.org/api/kedro/Kedro` both confirm `kedro.Kedro` v0.8.0. Fixed: added this cross-registry confirmation to the decision doc's "Live re-check" section.
- Findings rejected as noise (contradicted by verified facts or by direct precedent from sibling stories 12-1/12-2 in this same epic):
  - sprint-status-ledger.yaml / epics.md / sprint-status.yaml still showing `12-3: backlog` (raised independently by both reviewers) — all three carry "GENERATED — do not hand-edit" headers and are synced by `pixi run -e local-recipes sprint-ledger-sync` from a separate Tier-3 source; confirmed via git history that neither sibling story 12-1 nor 12-2 ever touched these files themselves (12-1's own review explicitly ruled an adjacent finding on the same file "outside this story's Code Map").
  - `.vscode/extensions.json` should also exist inside `src/shared/packages/pyforge-atlas/` for a human opening that subfolder as an isolated workspace — speculative; contradicted by this repo's established single-root-workspace convention (the existing `.vscode/settings.json` already lives only at repo root) and the epic's own explicit "the whole deliverable" (singular file) framing.
  - Decision doc's closing-FR-63 preamble reads as "pre-empting scrutiny" — subjective; the language nearly quotes the epic `SPEC.md`/`epics.md` verbatim ("the decision closes this, not an installation"), it is accurate restatement, not defensive framing.
  - No backlink from `docs/dreams/kedro-org-tooling-adoption.md`, whose `status: dreamt` was not updated — contradicted by direct precedent: neither 12-1 nor 12-2 touched the Dream file or the epic `SPEC.md`'s overall `status` field despite each closing a capability; git history confirms 12-1 only patched a factual figure inside `SPEC.md`, never its status/open_questions.
  - The "38/38" Epic-migration-stories figure is the whole-project stat misapplied to a narrower claim — refuted: `test-architecture.md` itself scopes exactly "38 stories" to "Wave 0, A–H, Epic 10 I0–I5" (the Kedro pipeline build-out), precisely matching the doc's "Epic-migration story" phrasing and citation of `cfe-atlas-datapipeline-kedro-migration.md`; Epic 12 was never included in that count and the doc never claims it was.
  - The cited "47 passing checks" is a moving target (already moved 38→47 once per story 12-1's audit), undermining the redundancy argument — the argument rests on the gate's existence and enforcement, not the specific count; citing the current live number is the correct practice per 12-1's own explicit instruction to do exactly that.
  - No drift guard on the hardcoded extension ID if upstream renames — disproportionate scope for a non-load-bearing recommendation file in an XS deferral story; no established convention in this repo requires drift-checking optional editor recommendations.
  - "Same session, immediately before writing this doc" is an unverifiable process claim — matches this repo's existing, accepted convention for this document class (e.g. `kedro-skills-audit-report.md` cites inline command output dated only by the doc's own frontmatter date, with no deeper provenance).
  - "Re-opening this decision" triggers have no measurable threshold or scheduled check — scope creep beyond an XS deferral story; matches the existing narrative-revisit precedent already accepted for the `kedro-mcp` decision (revisited qualitatively, not on a scheduled trigger).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks:**
- Confirm the decision doc reads as evidence-backed (cites the live `gh api` re-check plus the agent-authorship/gate-duplication reasoning), not a bare assertion.

## Auto Run Result

Status: `done`

**Summary:** Recorded Epic 12's third and final capability (FR-63): an explicit, dated
**defer** verdict on `kedro-org/vscode-kedro`, evidenced by live re-verification (still
active, unarchived, Apache-2.0, v0.8.0, pushed same-day) plus two reasons specific to
this repo (Kedro code is ~entirely agent-authored, not interactively edited; the
extension's flagship catalog-validation feature duplicates the already-enforced
`kedro-catalog-check` gate). Added the zero-cost `.vscode/extensions.json`
recommendation the epic named as the deferral's entire extra deliverable.

**Files changed with one-line descriptions:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/vscode-kedro-decision.md` — NEW: dated defer decision record, closing FR-63.
- `.vscode/extensions.json` — NEW: `{"recommendations": ["kedro.Kedro"]}` with a provenance comment pointing to the decision doc.

**Review findings breakdown:** 4 patches applied (all low severity — corrected a
misstated historical comparison, enumerated the block-condition checks explicitly,
added in-repo provenance to the recommendation file, and added live cross-registry
(Marketplace + Open VSX) confirmation of the extension ID), 0 deferred, 9 rejected
(three tracking-ledger findings collapsed into one and rejected as generated/synced
artifacts outside this story's Code Map — direct precedent from sibling stories 12-1
and 12-2; the rest refuted by verified facts or by direct precedent elsewhere in this
same epic — see Review Triage Log for each).

**Follow-up review recommendation:** `false` — all four patches were low-severity,
localized wording/provenance improvements to a two-file, XS-effort documentation
story; no behavior, security, or data-impact surface exists to warrant independent
follow-up.

**Verification performed:**
- `python3` JSONC-aware parse of `.vscode/extensions.json` confirms exactly `{"recommendations": ["kedro.Kedro"]}`.
- `test -f` confirms the decision doc exists; `grep -qi defer` confirms the verdict is stated.
- `git status --porcelain .vscode/settings.json` — no output (untouched, as required).
- `git status --porcelain` overall — only the two intended new files.
- Live re-verification of `kedro-org/vscode-kedro` via `gh api` (repo + latest release + package.json) and of the extension ID against both the VS Code Marketplace gallery API and `open-vsx.org/api/kedro/Kedro` — all consistent (`kedro.Kedro`, v0.8.0).

**Residual risk:** Low. This is a recorded decision plus a non-executing recommendation
file — no code path, build, or CI behavior depends on it. The only external dependency
(the extension ID staying `kedro.Kedro` on both registries) is unenforced, matching
this repo's convention for optional editor recommendations; the decision doc itself
states how to re-open the decision if circumstances change.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `11-3-record-the-vscode-kedro-verdict-fr-63: done`).
