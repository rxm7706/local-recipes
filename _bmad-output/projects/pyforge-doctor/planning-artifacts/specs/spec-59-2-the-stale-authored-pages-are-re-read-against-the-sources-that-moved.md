---
title: '59.2: The stale authored pages are re-read against the sources that moved'
type: 'chore'
created: '2026-11-17'
status: 'ready-for-dev'
story: 59-2-the-stale-authored-pages-are-re-read-against-the-sources-that-moved
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # documentation pages only; no runtime path (roster list)
surface:
  - 'docs/tutorials/local-platform-development.md'
  - 'docs/how-to/**'
  - 'docs/reference/agent-memory-lifecycle.md'
  - 'docs/explanation/**'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/MAP.md
  - docs/_STYLE_GUIDE.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A stamp that warns for three weeks is not a stamp. Seventeen pages have sources that moved after `verified:` and nobody re-read them.

**Approach:** For each page, read what changed in each moved source since `verified:`, run the full verification pass (commands, paths, flags, counts, links), fix the page, narrow `sources:`, and re-stamp.

Ledger key: `59-2-the-stale-authored-pages-are-re-read-against-the-sources-that-moved`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** — documentation currency; amended 2026-11-17: every authored page is stamped or declares its detector, the currency classes fail, the workflow inventory is generated, package-level pages fold into the quadrants.

## Boundaries & Constraints

**Always:**
- Check every command, path, flag, count and link in a page against the tree before its stamp moves; keep `sources:` narrow (the file a page restates, not a hub file).
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a generated page, the generated section of `docs/MAP.md`, a compiled station skill, a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never run a bare `spec_surface_check.py --write-baseline`; Story 59.8 stamps each governing Spec scoped, once, last.
- Never move a station's code, CLI or capability to make a page true: fix the page.

## Acceptance Criteria

**Given** 17 of the 19 stamped authored pages warn `docs-currency-authored-stale` (16 verified 2026-10-24, one 2026-10-25; `pixi.toml` is a moved source on 7), and `docs/how-to/pause-ci.md` cites a path that no longer exists
**When** each page is re-read against the diff of every moved source since its `verified:` date, every command, path, flag and count in it is checked against the tree, its `sources:` list is narrowed to the files it restates, and `verified:` reads 2026-11-17
**Then** `docs-currency` names none of the 19 pages; no page cites a hub file (`pixi.toml`, `AGENTS.md`) it does not restate; the dead reference in `pause-ci.md` resolves or is reworded
**And** the pass goes through `bmad-os-diataxis` and `docs/_STYLE_GUIDE.md`; no page is restructured for its own sake

- **AC1 — No stamped page is stale or dead-referenced.** Expected: prints 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency --json > /tmp/dc.json; python3 -c "import json;d=json.load(open('/tmp/dc.json'));f=d['findings'] if isinstance(d,dict) else d;print(sum(1 for x in f if x.get('check')=='docs-currency-authored-stale'))"
  ```

- **AC2 — The dead reference is gone.** Expected: prints 0.

  ```bash
  grep -c 'docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md' docs/how-to/pause-ci.md
  ```

- **AC3 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-2-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-2-the-stale-authored-pages-are-re-read-against-the-sources-that-moved` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."59"`.
- Minted 2026-11-17 in the chain commit of the integration branch `docs-full-refresh-2026-11-17`, the first commit of the branch.

## Notes

- One integration branch and one PR carry Stories 59.1 to 59.8 (operator ruling 2026-11-17). Stories 59.1 to 59.6 run in parallel on disjoint files; 59.7 lands on a tree its source already reads green; 59.8 runs last.
- Measured at main `33c96fd0bb`: 57 authored pages, 19 stamped, 17 of those stale, 38 unstamped; 6 generated; 7 pointers.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the full documentation refresh) and the operator's ruling of 2026-11-17.
