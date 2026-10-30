---
title: '109.1: The reset marketplace has a product brief'
type: 'docs'
created: '2026-10-21'
status: 'done'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 3
followup_review_recommended: false
context:
  - archive/docs/dreams/self-hosted-bmad-marketplace.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/design-thinking-2026-10-20.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/bmad-marketplace-dream-reset.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-10-20 session re-decided the marketplace, and the archived seed plus Epic 60 do not say so. A teammate-facing product needs a brief in the station's brief format before the skeleton is the only statement of what the product is.

**Approach:** Write `briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md` with the brief template's sections (Executive Summary, The Problem, The Solution, What Makes This Different, Who This Serves, Success Criteria, Scope, Vision) plus `assumptions[]` and `open_questions[]`. Link the session folder. Do not un-archive the seed Dream.

## Acceptance criteria

1. The brief exists at the path above and contains each template section named in the approach.
2. It states the four jobs, the skill-folder install into `.agents/skills/` and `.claude/skills/`, the pilot audience (Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), and no AI tool yet), that Claude Code's documented skill path is `.claude/skills/` and Devin's is `.agents/skills/`, steward as owner, and Stories 109.4 and 109.5 as not built.
3. It records the session success signal (a teammate other than rxm7706 contributes a skill, and a different teammate installs and uses it), states that concepts A–F were all selected, and points at the verbatim session folder. It does not add a Dream under `docs/dreams/`.
4. The brief's memlog exists and was appended with `memlog.py`.

## Boundaries

- No code, no flag, no `SPEC.md` capability beyond the CAP-169 line this epic's chain commit adds.
- No new Dream file.

</intent-contract>

## Verification

**Commands:**

- `test -f _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md` — expected: exit 0.
- `test -f _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/.memlog.md` — expected: exit 0.

**Manual checks:**

- Read the brief against `design-thinking-2026-10-20.md`. The success signal and the selected concepts match that record.

## Review (loop 1)

2026-10-29, independent (a fresh subagent; the brief and its memlog against this spec, the verbatim session, P4, the
station Dream, SPEC.md CAP-169..CAP-173, Epic 109, the brief template and Round 0's record; not the author's summary).
Verdict **FAIL** on rows 1 and 2. AC1–AC4 met: both Verification commands exit 0, the eight template sections are in
template order with `assumptions[]` and `open_questions[]`, the manual check matches the session's success signal and
concepts, and no commit that touched the brief added a Dream. Boundaries held.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | brief § The Problem | Says the estate `mason environment`, `mason package` and `warden scan` skills assume `pixi run -e`; at `53aed16fe1` only warden's does | Only warden's runs `pixi run -e pyforge-warden`; all three assume an estate install from the local-recipes root and link estate paths |
| 2 | yes | § The Solution, § Success Criteria, A1 | `prototypes/p4-wizard-of-oz-pilot.md`, `registry/estate.yaml` and `design-thinking-bmad-marketplace-2026-10-20/` resolve from no base the brief names | Repository-root paths |
| 3 | no | § Executive Summary, § Scope | "109.4 and 109.5 are backlog" is stale for 109.5 (in-progress since 2026-10-29); 109.5 records Round 0 and the pilot before any automation; 109.6 is not mentioned | A dated currency section |
| 4 | no | § Executive Summary, § Who This Serves, § Scope | The two generated plugin manifests (Claude since 2026-10-21, Codex since 2026-10-28) are not in In now and are a deviation from P4's manifest gate; Round 0 moved "uncertain" and "the copy is the install" | Name them, record the deviation, add Round 0's result, dated |
| 5 | no | § Who This Serves, § Success Criteria | The session's per-teammate find → install → use metric, the per-tool folder metric, interventions trending down, and the stop rule are missing | Restore them |
| 6 | no | § Scope, `open_questions[]` | Every pilot needs an unpublished package, so the primary signal cannot be reached; the session and P4 publish one listing to Artifactory; the brief does not say | An open question |
| 7 | no | § Executive Summary, § Success Criteria | "All of A–F as one slice", but the built slice does not touch D or E's search; two of P4's gates (search/MCP, manifests) are missing | Say which concepts the slice touches; list all of P4's gates |
| 8 | no | § Success Criteria | "Three pull requests that caught a real problem" misstates P4 ("≥3 PRs and they caught at least one real problem") | P4's wording |
| 9 | no | A5 | Points at an open question that does not exist; Gemini Code Assist outside agent mode is the live case | An open question for it |
| 10 | no | A1; `.memlog.md` | A1 does not say the 2026-10-21 monorepo decision overrides the session; that decision has no memlog line | Amend A1; a `decision` entry |
| 11 | no | frontmatter | `status: draft` while the brief is the contract for Epic 109 | `ready` when 109.1 closes |

## Fixes (loop 1)

All eleven rows landed the same day, recorded in the brief's memlog with `memlog.py` (a backfilled `decision` entry for the
2026-10-21 host decision, and an `event` for this pass). Rows 1, 2 and 5–10 are corrections in place: only warden's estate
skill runs `pixi run -e`; repository-root paths; the slice touches A, B, C and F, with D and E's search waiting on P4; the
session's pilot metrics and stop rule; P4's lint gate in P4's words with its search/MCP and manifest gates; A1 names the
override; OQ6 (who publishes which `pyforge-*` package) and OQ7 (Gemini Code Assist outside agent mode). Rows 3 and 4 are
dated drift, so they go in a new § Currency reconciliation — 2026-10-29 (the founding steward brief's form) rather than
rewriting the dated text: story status, Round 0's Claude Code leg, and the two manifests as a recorded deviation from
P4. Row 11: `status: ready`, `updated: 2026-10-29`. A verification pass follows.

## Review (loop 2, verification)

2026-10-29, a fresh subagent that judged each loop-1 row from the brief before reading § Fixes. All eleven loop-1 rows
closed; both Verification commands exit 0; AC1–AC4 and the Boundaries hold; the Currency section's placement after
`open_questions[]` matches the founding steward brief. Verdict **FAIL** on four rows, all in the loop-1 fix text.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | OQ6 | "No teammate can finish a real task" contradicts the runbooks: the mason engine steps run today, and the primary signal is a contributed skill | Only the station commands need the unpublished packages |
| 2 | yes | § Executive Summary | "D waits on P4's per-tool-manifest gate" overstates P4, which gates only adapters; D's agent-as-skill seed is optional and ungated | Split D's adapters from its agent-as-skill listing |
| 3 | yes | § Currency reconciliation | The list of in-place corrections omits Who This Serves' Round 0 and pilot split and A5's pointer to OQ7, so "everything above is dated 2026-10-28 except" is untrue | Complete the list; a memlog entry naming them |
| 4 | yes | § Success Criteria | `site/index.html` does not resolve from the repository root (pre-existing, same class as loop-1 row 2) | `docs/foundry/marketplace/site/index.html` |
| 5 | no (conditional) | § Currency reconciliation; frontmatter | "109.1 is done" and `status: ready` while the ledger says in-progress | Promote 109.1 in the landing change |
| 6 | no | § Currency reconciliation, Round 0 bullet | "Not both" reads as a Round 0 result; Round 0 did not test side by side | Mark it as the 109.6 cards' advice |
| 7 | no | § Currency reconciliation | "Its two other gates" reads as if P4 has three | Name the two gates the brief lacked |
| 8 | no | brief memlog, loop-1 entry | "A, B, C, F built" says more than the brief's "touches" | A correcting entry |
| 9 | no | `epics.md` Story 109.2 Given | Repeats the estate `pixi run -e` claim loop-1 row 1 corrected | Same wording as the brief |

## Fixes (loop 2)

All nine rows landed the same day. OQ6's premise follows the runbooks; D's adapters wait on P4's manifest and adapter gate
and its agent-as-skill listing is out of the slice; the site index path is repository-root; the Currency section lists
every in-place correction and names the two P4 gates the brief lacked; "109.1 closes with this review (done in the same
change)", and this change promotes 109.1 to `done` in this spec, `epics.md` and the ledger; the side-by-side advice is
marked as the 109.6 cards'; one memlog `event` names the loop-2 corrections and corrects the loop-1 entry; Story 109.2's
Given in `epics.md` uses the brief's wording. A third pass verifies the loop-2 rows only.

## Review (loop 3, verification)

2026-10-29, a fresh subagent, the last pass. Eight of nine loop-2 rows closed; the Currency list now names every
changed body line; statuses agree (109.1 `done` in this spec, `epics.md` and the ledger; the brief `status: ready`); every
backticked path resolves; both Verification commands exit 0; AC1–AC4 and the Boundaries hold. Verdict **FAIL** on one row
in the loop-2 fix text.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | OQ6 | "A contributed code-backed skill would hit the same wall" is untrue in general: a code-backed skill whose package is published runs | "A contributed skill that needs an unpublished `pyforge-*` package"; widen the question to "a contribution that needs no unpublished package" |
| 2 | no | OQ6 | "Only the engine steps run" leaves out step 0 | Name step 0 |
| 3 | no | § Currency reconciliation | `status: ready` is the one change above it the list does not name | Name it |
| 4 | no | `docs/dreams/pyforge-steward.md`, the 2026-10-28 entry | The parenthetical reads as the whole list of corrections | "among them" |
| 5 | no | this spec's frontmatter | `followup_review_recommended: true` beside `status: done` | `false` |

## Fixes (loop 3)

All five rows landed the same day in the reviewer's own wording, and the brief's memlog names them. No further loop: each
fix is the text the verification asked for, word for word, and no other sentence changed. `followup_review_recommended`
is `false`; 109.1 is `done`.

