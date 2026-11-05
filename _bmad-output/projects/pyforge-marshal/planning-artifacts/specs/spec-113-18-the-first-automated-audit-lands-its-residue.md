---
title: "113.18: The first automated audit lands its residue"
type: 'docs'
created: '2026-11-05'
status: 'done'
baseline_revision: '836a2ee286'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-113-7-the-first-fleet-audit-runs-and-lands-its-residue.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The first `marshal factory challenge --audit` ran on 2026-11-05 on `claude-sonnet-5-5`: 26 runs, 1,057 findings
(139 high, 680 medium, 238 low), 2 h 44 min, $45.11 at catalog rates. Its reports sit in gitignored Tier 3, and CAP-302 says a
report file alone is never the residue.

**Approach:** Nine Sonnet agents verified the 139 high findings against `main` at `836a2ee286`, and five more tried to overturn
the 73 rejections and ran a consequence check on the 22 accepts that change code, a test, a Spec, a story spec or a ledger. The
triage recommended 53 accepts, 68 rejections and 18 deferrals, and the operator ruled "Accept all 53". This story lands that
result as Story 113.7 landed the audit of 2026-11-01: one research file per station, one memlog event per accepted finding, a
re-derive where the contract changes, and the cascade. The accepted fixes to skills and recipes are parked on their own stories,
because a recompile pass and a recipe campaign are separate work.

Ledger key: `113-18-the-first-automated-audit-lands-its-residue`. Type / Effort / Deps: docs / M / Story 113.17.

### Living CAP citations

- **CAP-302** — one audit sweep says where the fleet stands; this story is the durable residue of its first automated run.
- **CAP-303** — an accepted finding travels the chain's only write path; the events go through `memlog.py` by hand, as Story 113.7's did.

## Acceptance Criteria

- **AC1 — The run is recorded.** The Tier-3 reports are under `_bmad-output/projects/pyforge-marshal/implementation-artifacts/egm/audit-2026-11-05/` in the primary checkout, with the triage in `triage-2026-11-05.md`; the marshal Dream's Realization log records the date and the headline counts.
- **AC2 — The residue.** Eight `research/egm-audit-2026-11-05.md` files, each with every high finding's decision, reason and carrier, the headline counts, and a count of the findings not triaged. Marshal's also carries the rules stage, the fleet totals and the three findings the triage added.
- **AC3 — The memlogs.** One `EGM audit 2026-11-05 finding <ID> accepted` event per accepted finding on its owning Spec, 53 in all, and the operator's ruling on marshal's memlog.
- **AC4 — The re-derives.** CAP-70, CAP-71 and CAP-72 (atlas), CAP-93 (doctor), CAP-35 (mason), CAP-32 (scribe) and CAP-26 with the Leak guard glossary line (warden) are re-derived from memlog capability entries, script-rendered, with both self-validate passes logged.
- **AC5 — The rules.** `AGENTS.md` carries RUL-A-F1 and RUL-A-F2, and RUL-A-F3 waits for the next `bmad-project-context` refresh on `DW-scribe-egm-2026-11-05-3`; `CHAIN-STANDARD.md` carries RUL-C-F3, RUL-C-F4 and RUL-C-F7; `docs/dreams/one-chain-per-station.md` carries RUL-C-F1.
- **AC6 — The notes.** Dated notes land on marshal Stories 113.1, 113.2, 113.4, 113.5 and 113.6, mason Stories 25.1, 25.2, 25.17 and 25.18 and warden Stories 16.2 and 16.4. Story 118.3's text takes STW-D-F6 and STW-M-F2, and its status does not move.
- **AC7 — What is parked has an owner.** Stories 113.19, 25.19 and 29.5 sit at `backlog` with tracked specs; each deferred finding is on a deferred-work row or names its story; the MCP runner decision is an operator-owned row.
- **AC8 — The gates.** `chain-completeness-check`, `dream-chain-check`, `deferred-work-check`, `ledger-regression-check`, `story-status-check` and `spec-surface-check` exit 0, and `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` exits 0.

## Boundaries & Constraints

- The 680 medium and 238 low findings are not triaged. The residue counts them as not triaged, never as rejected. Their text stays in the Tier-3 markers.
- The first-pass brief told verifiers that reviewer severity runs loud, and all 139 highs fell to medium or low. The residue says so.
- 446 findings came from the 12 runs that read an unrelated Dream entry. Only the high ones were corrected by hand.
- RUL-A-F3 is accepted and not applied. Its line sits in the `bmad:context` block, which only a refresh may change, and a refresh re-verifies the whole block.

**Never:**
- Never hand-edit a `SPEC.md`; never write a ledger directly; never accept a finding without the operator's word; never recompile a skill here; never move Story 118.3's status; never write a `cfe-local-build-*` field by hand.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-302

- Dream: `docs/dreams/pyforge-marshal.md` § *2026-11-01 — A stranger reads the chain*, Realization log.
- Epic: Epic 113.

## Verification

- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `git grep -c 'EGM audit 2026-11-05 finding' -- '*.memlog.md'` — expected: 53 lines in all across the owning Specs.

## Spec Change Log

- 2026-11-05: minted and landed in one PR on the operator's rulings of 2026-11-05.
- 2026-11-05: an independent review on the diff found 1 high, 9 medium and 12 low. All are fixed here. The high: CAP-26's first re-derive licensed what the leak guard forbids. RUL-A-F3's first form was a hand edit of the `bmad:context` block, so it is undone and parked. The review also widened Story 25.19 to both tracks and added `--rebuild`, moved STW-R-F2 and STW-R-F3 from Story 29.5 to Story 118.3, and narrowed the atlas and scribe re-derives to what the code does.
