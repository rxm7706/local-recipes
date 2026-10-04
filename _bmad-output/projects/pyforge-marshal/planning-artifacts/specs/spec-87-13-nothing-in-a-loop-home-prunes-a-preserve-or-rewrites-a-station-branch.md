---
title: "87.13: Nothing in a loop home prunes a preserve or rewrites a station branch"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - scripts/fleet-poll-hourly.sh
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two loop-home paths discard or rewrite work.
- **The prune.** Marshal renders `preserve_keep = 20` (`adapters/harness_bmadloop.py:392`). At every run start bmad-loop prunes `attempt-preserve/*` and `refs/attempt-preserve-dirty/*` down to the newest 20, whatever their names (`BL/verify.py:5805-5826`). Refs are shared across worktrees, so the prune runs against the primary clone, and any preserve not yet promoted (Story 87.4) can be deleted. Upstream documents `keep <= 0` as "never prune" (`BL/policy.py:543-549`).
- **The fleet poll.** `scripts/fleet-poll-hourly.sh` runs `git pull --rebase --autostash origin main` inside each loop home. That rewrites `loop/<slug>` and leaves the pre-rebase commits dangling, against AD-46's "never a rewrite". Each tick it also pushes the shared local `main` from every home, with errors swallowed (review minor 14; research § 9).

**Approach:**
- **Render.** Render `preserve_keep = 0`, unflagged (operator ruling 2026-10-04, review minor 6 and Q15). Pin it with an AD-78 vocabulary test against the installed package.
- **Poll.** The fleet poll fast-forwards a loop branch only (`merge --ff-only`) and never rebases. It pushes only the home's own station branch, and only as a fast-forward. It never pushes `main`. A diverged branch is reported in the poll log, not rewritten.

Ledger key: `87-13-nothing-in-a-loop-home-prunes-a-preserve-or-rewrites-a-station-branch`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- AD-46 (stage-bound push, never a rewrite), AD-78 (the harness era is pinned by installed-package tests), and `spec-pyforge-marshal` CAP-287 / AD-81 (upstream scratch is promoted, never pruned first). A defect of shipped behaviour, so it is a `fix` with no flag.

## Acceptance Criteria

- Given a rendered loop-home policy When `bmad-loop validate` reads it Then `[scm] preserve_keep = 0` with zero warnings.
- Given the installed `bmad_loop` When the AD-78 pin test runs Then it fails if the package's own policy contract stops treating `0` as "never prune".
- Given a loop home whose `loop/<slug>` is behind `origin/main` When the poll's sync runs Then it fast-forwards; given one that has diverged Then nothing is rewritten and the divergence is logged.
- Given any home When the poll's sync runs Then it never runs `pull --rebase` and never pushes `main`; it pushes the station branch only as a fast-forward.
- Given each rule removed When the tests run Then a test fails (mutation); the poll test uses real git repositories and a bare remote.

## Boundaries & Constraints

**Always:** Render through the one harness seam (AD-3). Real git in tests.

**Never:** Never patch or rename bmad-loop (AD-2). Never force-push or rebase a station branch. Never push `main` from a loop home.

</intent-contract>

## Binding

Parent: AD-46, AD-78; `spec-pyforge-marshal` CAP-287 / AD-81.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: review minor 6 and Q15 (`preserve_keep = 0` now, unflagged), minor 14 and research § 9 (the fleet poll).
Ledger key: `87-13-nothing-in-a-loop-home-prunes-a-preserve-or-rewrites-a-station-branch`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The harness pin tests: `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop*.py`.
- The fleet-poll test under `tests/scripts/` — expected: pass; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
