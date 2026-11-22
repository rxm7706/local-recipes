---
title: '130.1: The Pages workflow writes the changes input'
type: 'fix'
created: '2026-11-22'
status: 'done'
story: 130-1-the-pages-workflow-writes-the-changes-input
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/pages_changes.py'
  - '.github/workflows/pages.yml'
  - 'src/shared/packages/pyforge-steward/tests/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `/changes/` and `/changes/rss.xml` have published "the `changes.json` build input is absent" since herald Story 43.6, because no Guild step of `pages.yml` writes the input (`DW-steward-43-6-1`, part 1).

**Approach:** `scripts/pages_changes.py`, beside `scripts/pages_fleet_status.py`: it reads `git log --first-parent` on the built commit for the 30 days before that commit's time and writes `{generated_at, window_days: 30, merges: [{date, station, subject, sha}]}`, the station from `Merge <station>/<E-S> into main` and `other` when the subject has none. `pages.yml` fetches the history the window needs and runs it before `pages-check`. The deferred row records part 1 closed and stays open for the other two inputs.

Ledger key: `130-1-the-pages-workflow-writes-the-changes-input`.

### Living CAP citations

- spec-pyforge-steward CAP-168 (amended 2026-11-22); FR-8 ← CAP-2, CAP-168; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Take `generated_at` and the window from the built commit, so a second run on the same commit writes the same bytes.
- Write only what herald's `parseChanges` accepts (`docs-site/src/lib/agent-surface.ts`).

**Never:**
- Never read the wall clock.
- Never call `gh` or the network from the script.
- Never write `marshal-status.json` or `herald-progress.json` here.

## Acceptance Criteria

**Given** no Guild step of `pages.yml` writes `docs-site/src/content/changes.json`, so `/changes/` and its feed publish "input absent" (`DW-steward-43-6-1`, part 1)
**When** `pages.yml` runs `scripts/pages_changes.py` before `pages-check`, with the history the window needs
**Then** `changes.json` lists the first-parent merges to `main` in the 30 days before the built commit, each with its date, station, subject and commit id, `generated_at` and the window anchored on that commit, in the shape herald's `parseChanges` accepts
**And** a second run on the same commit writes the same bytes, and steward's suite passes with tests that fail by name on a clock-anchored window or a merge off the first-parent line

- **AC1 — Steward's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

- **AC2 — Steward's live-tree half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-168 (amended 2026-11-22); FR-8 ← CAP-2, CAP-168; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-22 entry; operator, 2026-11-22: "Wire Up the input".
- Epic: Epic 130, minted with this story.
- Ledger key: `130-1-the-pages-workflow-writes-the-changes-input` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."130"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## After-landing record (2026-11-22)

Both Pages builds of PR 2378 were cancelled at the job's 20-minute limit. The step first fetched the history with
`--filter=tree:0`; the Astro build that follows runs `git log --name-status` over the docs (Starlight), and on a clone
with no trees that log fetches each tree lazily and does not finish (measured on a simulated CI checkout: 214 lines in
45 s, against all 9,245 in 4 s with trees). The step now fetches with `--filter=blob:none` (about 13 s), and
`test_pages_yml_never_fetches_history_without_trees` holds it. The review's "no later step reads git history" was
wrong: the build does, through Starlight.
