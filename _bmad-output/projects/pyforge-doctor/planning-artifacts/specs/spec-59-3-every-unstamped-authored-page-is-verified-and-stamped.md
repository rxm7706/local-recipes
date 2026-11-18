---
title: '59.3: Every unstamped authored page is verified and stamped'
type: 'chore'
created: '2026-11-17'
status: 'done'
story: 59-3-every-unstamped-authored-page-is-verified-and-stamped
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # documentation pages only; no runtime path (roster list)
surface:
  - 'docs/how-to/**'
  - 'docs/reference/**'
  - 'docs/explanation/**'
  - 'docs/tutorials/**'
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

**Problem:** Two thirds of the authored shelf has never been checked by anything. The detector skips a page with no stamp, so green said nothing about them.

**Approach:** Fan out by quadrant. Each page: verification pass against the tree, fix, stamp narrow. A page whose currency another detector owns declares `checked_by:` instead.

Ledger key: `59-3-every-unstamped-authored-page-is-verified-and-stamped`.
Type / Effort / Deps: chore / L / —.

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

**Given** 38 of the 57 authored pages in `docs/map.yaml` carry neither `sources:` nor `verified:`, and `docs-currency` skips a page without them; the oldest was last edited 2026-09-07
**When** each page gets the full verification pass and one of three outcomes: verified and stamped with a narrow `sources:` list; made a generated page (Story 59.1's `github-workflows.md`); or `checked_by:` its own detector (`docs/reference/library-llms-full.md`, `llms-full-check`)
**Then** every `kind: authored` page in `docs/map.yaml` carries `verified:` and a non-empty `sources:` whose every path exists, or a `checked_by:` naming a pixi task; `docs/reference/agent-instruction-notes.md` keeps its historical sections and its headings
**And** what could not be executed here (a cluster, a credential, a paid service) is listed in the PR body as not verified, never stamped as if it were

- **AC1 — Every authored page is stamped or declares its detector.** Expected: prints 0.

  ```bash
  python3 scripts/docs_map_render.py --help >/dev/null; pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency --json > /tmp/dc.json; python3 -c "import json;d=json.load(open('/tmp/dc.json'));f=d['findings'] if isinstance(d,dict) else d;print(sum(1 for x in f if x.get('check')=='docs-currency-authored-unstamped'))"
  ```

- **AC2 — The governance reader of the test charter still resolves every name.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild governance-currency
  ```

- **AC3 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-3-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-3-every-unstamped-authored-page-is-verified-and-stamped` (`backlog`).
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
