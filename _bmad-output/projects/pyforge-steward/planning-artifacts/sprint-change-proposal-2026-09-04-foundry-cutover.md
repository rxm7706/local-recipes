---
title: Sprint Change Proposal — cutover to python-foundry (solutioning iteration 1)
date: 2026-09-04
project: pyforge-steward
chain: spec-python-foundry-cutover (extends spec-pyforge-unifying-strategy)
status: draft — solutioning iteration 1; operator review pending. No story leaves ledger `blocked` until the operator flips it.
trigger: docs/dreams/pyforge-unifying-strategy.md § "Cutover to python-foundry" (2026-09-04) — the 40→43 + Mason 13 gate closed 2026-09-03 with nothing downstream of it; red-team MEDIUM band DW-RT-2026-09-02-1..9 all open, R-17 is Phases 1–3
mode: batch
scope: major — new chain artifacts (Spec, spine, epic), no code
operator: Rxm7706
follows: sprint-change-proposal-2026-09-02-red-team-high.md
phase: BMAD Phase 3 (Solutioning) — Phase 4 deliberately not entered
---

# Sprint Change Proposal — cutover to `python-foundry` (solutioning iteration 1)

## 1. Issue summary

The Dream names `python-foundry` as the lasting git root and `factory/` as the recipe
island. The gate it set on that cutover (Epics 40 → 41 → 42 → 43, Mason 13.1 / 13.2)
closed 2026-09-03 — "Then cutover Phase 1 may start" — yet nothing existed downstream:
the Phase 0–6 table sat only in the archive under "Historical — do not build", the Spec
had no cutover capability, `epics.md` ended at 43, and no ledger key named Phase 0.
Meanwhile the review's MEDIUM band ("before cutover Phase 1") was entirely open, and its
R-17 *is* Phases 1–3.

Operator direction (2026-09-04): the plan lives in the Dream; the work is **analysis and
planning — solutioning — reviewed and refined multiple times before implementation**.

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | None; trigger is the closed gate plus the Dream's own commitment. |
| 1.2 | Problem type | Done | *Missing architecture* (no contract for a committed move) and *strategic decision* (repo shape). |
| 1.3 | Evidence | Done | Three explorations 2026-09-04: ledgers, `epics.md`, Spec, archive lines 375–444, `gh repo view` (no foundry), 268 worktrees, 7,855 recipe dirs, 103 `src/shared/packages` sites in `pixi.toml`. |
| 2.1 | Current epics completable | Done | Epics 1–43 unchanged, all `done`. |
| 2.2 | Epic-level change | Done | **Add Epic 44** (ten stories) as a solutioning decomposition. |
| 2.3 | Remaining epics | Done | None open. 44.x deps are within-epic; Mason gates on 44.6 / 44.9 are ledger state. |
| 2.4 | New epics needed | Done | One. R-18..R-22 are an **Epic 45 candidate**, not minted. |
| 2.5 | Order | Done | 44.1 ∥ 44.2 → operator flips 44.3 → 44.4 → 44.5 → 44.6 ∥ 44.7 → 44.8 → operator flips 44.9 → operator flips 44.10. **Nothing dispatches until the operator flips a story.** |
| 3.1 | PRD | Done | No FR change; § 14 dated paragraph. The cutover is layout, not product scope. |
| 3.2 | Architecture | Done | New spine `architecture-python-foundry-cutover-2026-09-04` (`fnd:AD-1..16`, `status: draft`, iteration 1, gate PASS-WITH-FIXES applied) inheriting canopy AD-1..23 and `pap:AD-1..17` read-only; no conflict found. Reviewer gate (lint + rubric walker + reality-check + adversarial-pairs, `reviews/`): **PASS-WITH-FIXES** — 3+1+4 CRITICAL findings, all applied as AD-2/3/4/5/6/7/8 tightenings and new AD-13..16; nine open questions carried |
| 3.3 | UI/UX | N/A | No UI. |
| 3.4 | Other artifacts | Done | Dream § Cutover + Grounding + Realization; Spec `spec-python-foundry-cutover` (+ `cutover.md`, spine adopted as companion); `marshal-policy.toml` `[epic_surfaces] "44"`; deferred-work ledger dispositions; specs README. |
| 4.1 | Direct adjustment | Viable | Additive; no code. |
| 4.2 | Rollback | Not viable | Nothing to revert. |
| 4.3 | MVP review | Not viable | Scope unchanged; the lasting repo's shape is. |
| 4.4 | Path | Done | **Direct adjustment, held at Phase 3.** |
| 6.3 | Approval | Action-needed | Operator reviews iteration 1; approval is per story via the ledger flip (`fnd:AD-9`). |
| 6.4 | Ledger | Done | Ten keys `blocked`; `epic-44` `backlog`; retrospective `optional`; `# stories: 251`. Tier-3 feed repaired first (`--repair-feed`, 57 keys). |

## 3. Recommended approach

**Direct adjustment, scope major, held at Phase 3.** One epic, ten stories, every one
`blocked`. The operator iterates on three artifacts — Spec, spine, epic — and flips stories
to `backlog` only when an iteration closes. Outward stories (44.3 GitHub repo, 44.9
conda-forge PRs, 44.10 disable Azure + archive) additionally need explicit confirmation at
dispatch (`fnd:AD-9`). Story specs are not drafted before a flip.

| Phase | Story | Governed by | Gate |
|---|---|---|---|
| — | 44.1 move-list manifest | fnd:AD-1, AD-2 | — |
| — | 44.2 document fixes (R-23/24/25 + Python-floor pins) | Spec Constraints | — |
| 0 | 44.3 open the foundry | fnd:AD-1, AD-3, AD-8, AD-9 | **outward** |
| 1a | 44.4 fold the packages | fnd:AD-2, AD-6, AD-7 | deps 44.1, 44.3 |
| 1b | 44.5 move the estate | fnd:AD-2, AD-5, AD-12 | deps 44.4 |
| 2 | 44.6 CFE comes home | fnd:AD-4, AD-5 | **Mason** (Rules 1 + 2) |
| 3 | 44.7 factory island (R-17) | fnd:AD-3, AD-4, AD-8 | deps 44.3 |
| 4 | 44.8 working set | fnd:AD-2, AD-10 | deps 44.7 |
| 5 | 44.9 Mason → conda-forge | fnd:AD-4, AD-9, AD-11 | **outward + Mason** |
| 6 | 44.10 archive local-recipes | fnd:AD-1, AD-8, AD-9, AD-11 | **outward, irreversible** |

**Decisions taken by the operator (2026-09-04):** fresh empty repo (history stays in the
archive at a pinned SHA); fold docs / carry ops for R-18..R-25; the plan lives in the Dream.

**Effort / risk.** S+S+M+L+L+M+L+M+M+M. Risk concentrated in 44.4 (≈100 path rewrites),
44.5 (adapter symlinks; Windows open question), 44.6 (CFE resolution chain). Each carries
its fail-without test in the epic's ACs; the spine's open questions must be answered before
44.3 / 44.5 dispatch.

**Why solutioning is held.** Five open questions bend ADs (`windows-symlink-adapters`,
`runtime-state-home`, `loop-home-cutover-timing`, `planning-history-scope`,
`actions-minutes`), and the spine was drafted on the Fast path with `[ASSUMPTION]` tags. The
readiness gate (`bmad-sprint-planning`) is the Phase 3 → 4 boundary and is **deliberately not
run** in this iteration.

## 4. Detailed change proposals

- **Dream** — § *Cutover to `python-foundry`* (build target, promoted out of the archive),
  Grounding bullet, "How to read" list, Solutioning-first paragraph, Realization entry;
  archive pointer.
- **Spec (new)** — `specs/spec-python-foundry-cutover/` (`SPEC.md`, `cutover.md`,
  `.memlog.md`): CAP-1..7 one per phase, `extends:` the Canopy chain, `surface: []`,
  spine adopted as companion, open question `actions-minutes`.
- **Architecture (new)** — `architecture/architecture-python-foundry-cutover-2026-09-04/`
  (`ARCHITECTURE-SPINE.md`, `.memlog.md`, `reviews/`): paradigm strangler-fig repository
  cutover; `fnd:AD-1..16`; five open questions; reviewer gate outputs under `reviews/`.
- **Epics** — Epic 44 appended before the currency note; ten `### Story` headings with
  Given/When/Then ACs; `inputDocuments` extended; dated addendum.
- **Ledger** — ten `blocked` keys, `epic-44`, retrospective; Tier-3 feed written then
  `sprint-ledger-sync --project steward` (tracked twin regenerated, header true).
- **Deferred-work ledger** — `DW-RT-2026-09-02-1` promoted → 44.7; `-7/-8/-9` promoted →
  44.2; `-2..-6` carried with a dated disposition (Epic 45 candidate); new
  `DW-CC-2026-09-04-1` (worktree residue → 44.10).
- **Marshal policy** — `[epic_surfaces] "44"` declared (34 globs) so MRS-GATE-012 is
  satisfied whenever the operator flips a story.
- **PRD § 14** — dated paragraph. **Specs README** — Dream-level Spec listed.
- **Not produced on purpose:** story specs `spec-44-*.md`; a readiness report; any
  `backlog` row; any change under `src/`, `pixi.toml`, `.github/`, or `recipes/`.

## 5. Implementation handoff

**Scope: Major — replan artifacts, no implementation.** Route to the operator as
Product Manager / Architect for the review loop.

| Role | Responsibility |
|---|---|
| Operator (Rxm7706) | Review iteration 1: answer or defer the five open questions; correct `[ASSUMPTION]` tags in the spine; accept or reshape the ten stories; then flip stories to `backlog` one at a time. |
| Steward (owner) | Owns the Spec, spine and epic; re-derives via `bmad-spec` (update) and `bmad-architecture` (update, keep AD ids) on each iteration. |
| Mason | 44.6 and 44.9 under Rule 1 / Rule 2 when flipped. |
| Marshal | Never auto-flips a `blocked` key; dispatches only flipped stories, in the stated order. |
| Doctor | `chain-completeness`, `dream-chain`, `dreams-hygiene`, `deferred-work`, `ledger-regression` stay green through every iteration. |

**How to iterate (each round).** Edit the Dream section if the intent changes → append to
the Spec memlog and re-render `SPEC.md` (`bmad-spec` update, the single writer) → append to
the spine memlog and re-distill (`bmad-architecture` update; amend Rules in place, add
`fnd:AD-13+`, never renumber) → adjust Epic 44's stories in `epics.md` (keep numeric ids;
INV-B) → run the five detectors above → commit. Optionally run the facilitated
`bmad-create-epics-and-stories` dialogue against the Spec + spine to re-cut the stories.
When a story is ready: flip its ledger key to `backlog`, run `story-status-check`, and only
then let `bmad-build` draft its story spec.

**Success criteria for this iteration.** Detectors green; Epic 44 visible in
`fleet-picture` with 10 `blocked` / 0 `backlog`; no repo, PR, or file move exists yet.

## 6. Applied

- `docs/dreams/pyforge-unifying-strategy.md` (+ archive pointer)
- `specs/spec-python-foundry-cutover/{SPEC.md,cutover.md,.memlog.md}`; `specs/README.md`
- `architecture/architecture-python-foundry-cutover-2026-09-04/{ARCHITECTURE-SPINE.md,.memlog.md,reviews/*}`
- `epics.md` Epic 44 + addendum; `sprint-status-ledger.yaml` (10 + 2 keys)
- `deferred-work-ledger.md` dispositions + `DW-CC-2026-09-04-1`
- `marshal-policy.toml` `"44"`; `prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md` § 14
- this proposal
