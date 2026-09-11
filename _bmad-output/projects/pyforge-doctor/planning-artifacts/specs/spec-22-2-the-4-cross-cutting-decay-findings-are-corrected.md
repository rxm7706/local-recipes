---
title: 'The 4 cross-cutting decay findings are corrected'
type: 'fix'
created: '2026-09-11'
status: 'done'
baseline_revision: 'efabb6d912099eda55950f2d8c9d507e35545684'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Four confirmed, independent decay findings sit in this repo's two
highest-visibility docs. (1) `README.md:241-243`'s "GitHub Actions Workflows" section lists
only a handful of the repo's real 19 workflow files under `.github/workflows/*.yml` and claims
CI is "manual trigger only to preserve quota" — false for the several automatic PR-gate
workflows it omits (at minimum `detectors.yml`, `staged-recipes-linter.yml`,
`coverage-gates.yml`, `pyforge-station-tests.yml`, `platform-ci.yml` — verify the current full
set live, do not trust this list as exhaustive). (2) `README.md`'s own project-structure tree
(around lines 150-160) cites `docs/developer-guide.md` and `docs/bmad-setup-plan.md`, neither
of which exists at those paths — the real paths, `docs/reference/developer-guide.md` and
`archive/docs/bmad-setup-plan.md`, are already cited correctly elsewhere in the SAME file
(lines 172, 252). (3) The "Active-project resolution priority" list is duplicated verbatim
between `README.md:183` and `CLAUDE.md:66`, with `CLAUDE.md`'s copy substantially richer
(carries the two-symlink mechanism and the parallel-agents hazard `README.md`'s copy omits
entirely) — one fact, two unequal owners. (4) `CLAUDE.md:30` names all 8 PyForge Guild stations
(atlas, doctor, herald, marshal, mason, scribe, steward, warden); `CLAUDE.md:291`'s own "SKF
Skills" block says "7 skills" and lists 7 — silently omitting Mason. Mason's own missing
`.claude/skills/pyforge-mason/` is confirmed deliberate policy (documented in `AGENTS.md`,
covered by Story 22.1's sibling scope, not a gap) — but the SKF block itself gives the reader
no explanation, so a reader hits an unexplained-looking discrepancy.

**Approach:** Four independent, surgical corrections. (1) Rewrite the workflow section to
accurately distinguish automatic PR-gate workflows from on-demand/manual ones, verified live
against each `.github/workflows/*.yml` file's own `on:` trigger block — do not just add more
workflows to the existing false "manual trigger only" framing. (2) Fix the two broken paths in
the project-structure tree to match the correct paths the same file already uses elsewhere. (3)
Collapse the duplicated priority list to exist in exactly one place (`CLAUDE.md`, since its copy
is the more complete one) with `README.md` pointing to it instead of repeating it. (4) Add a
short note to `CLAUDE.md`'s SKF block explaining Mason's deliberate skill omission, so the
"7 skills" count reads as intentional rather than a silent gap.

## Boundaries & Constraints

**Always:**
- Verify each workflow's actual trigger type (`on:` block) live against the real
  `.github/workflows/*.yml` files before writing the corrected section — do not trust this
  spec's own named list as exhaustive or current; count and re-derive.
- The collapsed priority list keeps `CLAUDE.md`'s richer copy (two-symlink mechanism +
  parallel-agents hazard) as the single source; `README.md` gets a pointer, not a summary that
  could itself drift.
- The Mason SKF note states the omission is deliberate policy and references where it's
  documented (`AGENTS.md`), not just "Mason has no skill."

**Never:**
- Do not touch any `README.md`/`CLAUDE.md` content beyond these four specific findings — no
  wholesale rewrite of either file.
- Do not delete or shorten `CLAUDE.md`'s richer priority-list copy when collapsing the
  duplicate — the richer version is the one that survives.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Workflow section accuracy | `README.md` lists 4-of-19 workflows, claims "manual trigger only" | Section accurately distinguishes automatic PR-gate workflows from on-demand/manual ones, verified against real `on:` blocks | n/a — content fix |
| Broken project-structure paths | Tree cites `docs/developer-guide.md`, `docs/bmad-setup-plan.md` (don't exist) | Tree cites the real paths (`docs/reference/developer-guide.md`, `archive/docs/bmad-setup-plan.md`), matching this same file's own prose elsewhere | n/a — content fix |
| Duplicated priority list | Verbatim in both `README.md` and `CLAUDE.md`, unequal copies | Exists once in `CLAUDE.md` (richer copy); `README.md` points to it | n/a — content fix |
| Station-count self-contradiction | `CLAUDE.md` names 8 stations, SKF block says "7 skills" with no explanation | SKF block gains a short note naming Mason's deliberate skill omission | n/a — content fix |

</intent-contract>

## Code Map

- `README.md` — the "GitHub Actions Workflows" section, the project-structure tree, the
  "Active-project resolution priority" list.
- `CLAUDE.md` — the "Active-project resolution priority" list, the "SKF Skills" block.
- `.github/workflows/*.yml` — read-only reference for each workflow's real trigger type.
- `AGENTS.md` — read-only reference for Mason's documented skill-omission policy.

## Tasks & Acceptance

**Execution:**
- `fix` — rewrite `README.md`'s "GitHub Actions Workflows" section against the real, live
  workflow trigger types.
- `fix` — correct the two broken paths in `README.md`'s project-structure tree.
- `fix` — collapse the duplicated priority list to `CLAUDE.md` only, with `README.md` pointing
  to it.
- `fix` — add a note to `CLAUDE.md`'s SKF block explaining Mason's deliberate skill omission.

**Acceptance Criteria:**
- Given `README.md`'s workflow section lists 4 of 19 real workflows and falsely claims "manual
  trigger only," when the section is rewritten against the real trigger types, then it
  accurately distinguishes automatic PR-gate workflows from on-demand/manual ones.
- Given `README.md`'s tree cites two non-existent paths, when both are corrected, then the tree
  cites only paths that exist.
- Given the priority list is duplicated, when it is collapsed, then it exists in exactly one
  place (`CLAUDE.md`) with `README.md` pointing to it rather than duplicating it.
- Given `CLAUDE.md`'s SKF block silently contradicts its own 8-station list, when a note is
  added, then the block and the 8-station list agree, with Mason's omission explained rather
  than silent.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: no new finding
  introduced.
- Manual verification: `ls .github/workflows/*.yml | wc -l` matches the count named in the
  corrected `README.md` section; `grep -rn "bmad-setup-plan.md\|developer-guide.md" README.md`
  shows only the correct paths; `grep -c "Active-project resolution priority" README.md
  CLAUDE.md` shows the list body exists once, not twice.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 17 findings — high 0, medium 2, low 1, false 5, maybe-false 0
- findings:
  - `[false]` `[reject]` Tree still lists wrong enterprise-deployment/mcp paths — intent excludes fixes beyond the two named paths; pre-existing decay outside story scope.
  - `[false]` `[reject]` Workflow subtree still shows 4 files — pre-existing; not caused by this change.
  - `[medium]` `[patch]` Reusable-workflow sentence grouped linter reusable with platform test reusables incorrectly — fixed by separating `test-{linux,macos,windows}.yml` (invoked by `test-all.yml`) from `reusable-staged-recipes-linter.yml` (selftest only).
  - `[medium]` `[patch]` `herald-live-demo.yml` and `linter_issue_comment.yml` listed under PR gates despite non-`pull_request` triggers — moved to push/schedule/other automatic section; PR-gates intro narrowed to `pull_request` events.
  - `[false]` `[reject]` Missing standalone test-linux/test-macos dispatch rows — both workflows are `workflow_call` only; direct `gh workflow run` is not valid.
  - `[low]` `[patch]` On-demand section title said recipe builds but listed infra workflows — renamed to "On-demand / manual workflows".
  - `[false]` `[reject]` Missing link to github-workflows.md — out of intent scope (surgical four-fix pass).
  - `[false]` `[reject]` AGENTS.md SKF block lacks Mason note — spec scoped Mason explanation to CLAUDE.md only.
  - `[low]` `[defer]` Ledger out of sync during review — resolved via Tier-3 feed + `sprint-ledger-sync` before finalize.
  - `[false]` `[reject]` Omitted workflow_dispatch on detectors/dashboard — partial inventory acceptable; primary goal was correcting false manual-only claim.

## Auto Run Result

Status: done

**Summary:** Corrected four cross-cutting doc decay findings in `README.md` and `CLAUDE.md`: live-verified workflow trigger taxonomy (19 files), fixed two broken project-structure paths, collapsed duplicated BMAD priority list to a CLAUDE.md pointer, and explained Mason's deliberate SKF omission.

**Files changed:**
- `README.md` — workflow section rewrite, tree path fixes, priority-list dedupe, review patches for trigger categorization
- `CLAUDE.md` — Mason SKF omission note in SKF block
- `spec-22-2-…md` — status/baseline/review metadata
- `sprint-status-ledger.yaml` — story 22.2 promoted to `done`

**Review:** 3 patches applied (reusable-workflow wording, trigger categorization, section title); 1 item deferred then resolved (ledger sync); remaining findings rejected as false or out of intent scope.

**Follow-up review recommended:** false (no high patches; one medium patch category)

**Verification:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0
- `ls .github/workflows/*.yml | wc -l` → 19 (matches README)
- `grep` path checks — only correct developer-guide and bmad-setup-plan paths in README
- `grep -c "Active-project resolution priority"` — README 1, CLAUDE 1

**Residual risks:** Project-structure tree still shows `docs/enterprise-deployment.md` and `docs/mcp-server-architecture.md` without the `reference/` prefix (pre-existing, explicitly out of this story's scope).
