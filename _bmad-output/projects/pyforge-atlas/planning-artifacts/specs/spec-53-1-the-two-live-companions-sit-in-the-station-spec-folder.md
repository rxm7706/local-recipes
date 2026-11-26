---
title: '53.1: The two live companions sit in the station Spec folder'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 53-1-the-two-live-companions-sit-in-the-station-spec-folder
spec: spec-pyforge-atlas
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - 'archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/**'
  - 'src/shared/packages/pyforge-atlas/**'
  - 'docs/**'
  - 'scripts/.spec-surface-baseline.json'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-atlas-46-1-6`. Story 45.1 archived the absorbed Spec folders with every companion. CAP-43 reads `complete-export-contract.md` and CAP-54 and CAP-55 read `tier-taxonomy.md`, so both are live contracts that sit under `archive/`; Story 46.2 cited them by their archive path as the interim.

**Approach:** `git mv` the two files into `specs/spec-pyforge-atlas/`, add them to the Spec's `companions:` and re-point the cites of CAP-43, CAP-54 and CAP-55 through the memlog and a `bmad-spec` render (never a hand edit of `SPEC.md`), and re-point every other tracked reference to either archive path (code comments, tests, docs). Leave a one-line pointer in the archived folder only if a detector needs the path to resolve. `org-audit-precedent.md`, `kedro-skills-audit-report.md` and `vscode-kedro-decision.md` are records and stay archived.

Ledger key: `53-1-the-two-live-companions-sit-in-the-station-spec-folder`.

### Living CAP citations

- spec-pyforge-atlas CAP-43, CAP-54 and CAP-55 (each reads one of the two companions; the cite paths move through the memlog, no capability text change); CHAIN-STANDARD section 11 item 2 (a live companion is carried into the station Spec folder); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit `SPEC.md`.
- Never move the three record companions.
- Never change a line of either companion's text.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-atlas-46-1-6` reports that `tier-taxonomy.md` and `complete-export-contract.md` are read by live capabilities and sit under `archive/`
**When** both are moved into `specs/spec-pyforge-atlas/`, listed in `companions:`, and every reference is re-pointed
**Then** `git ls-files` lists both under `specs/spec-pyforge-atlas/` only, the Spec's `companions:` names them, CAP-43, CAP-54 and CAP-55 cite the new paths, and no tracked file outside `archive/` and the memlogs names either archive path
**And** the three record companions stay archived, the docs link gate and `spec-surface-check` pass, and the row reads resolved

- **AC1 — Both companions sit in the station Spec folder.** Expected: prints 2.

  ```bash
  git ls-files '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/tier-taxonomy.md' '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/complete-export-contract.md' | wc -l
  ```

- **AC2 — Neither is left under archive.** Expected: exit 1 (no line matches).

  ```bash
  git ls-files archive | grep -E 'spec-upstream-discovery/tier-taxonomy.md|spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-43, CAP-54 and CAP-55 (each reads one of the two companions; the cite paths move through the memlog, no capability text change); CHAIN-STANDARD section 11 item 2 (a live companion is carried into the station Spec folder); no AD moves.
- Dream: `docs/dreams/pyforge-atlas.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 53, minted with this story.
- Ledger key: `53-1-the-two-live-companions-sit-in-the-station-spec-folder`.
- Deferred-work row: `DW-atlas-46-1-6`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.

- 2026-11-25: reproduction on the unchanged tree: AC2's grep exits 0 and lists both files under `archive/`; `specs/spec-pyforge-atlas/` holds neither.
- 2026-11-25: change: `git mv` of `tier-taxonomy.md` (from `spec-upstream-discovery/`) and `complete-export-contract.md` (from `spec-atlas-kedro-catalog-expansion/`) into `specs/spec-pyforge-atlas/`; both are 100% renames, no line of either changed, and neither holds a relative link. No tracked file outside `SPEC.md`, the memlogs, `epics.md`, `marshal-policy.toml`, `archive/` and this story spec names either archive path, so no other reference moved: the package, `docs/` and `.claude/` cite both files by bare name. Left for the session lead, through the memlog and a render: `SPEC.md` `companions:` (lines 82-91, two entries to add) and the cites at lines 305 (CAP-43), 341 (CAP-54) and 344 (CAP-55). Not in this story's surface and left as they are: `marshal-policy.toml` lines 559-560 (this story's own epic surface) and the pre-archive path (`…/specs/spec-atlas-kedro-catalog-expansion/…`, `…/specs/spec-upstream-discovery/…`, no `archive/`) in `docs/dreams/pyforge-atlas.md` line 1454 and in the frontmatter of story specs 12-2 to 12-5, 20-5, 21-1 and 22-1 to 22-9.
- 2026-11-25: AC1 prints 2 (exit 0); AC2 exit 1 (no line matches, as expected). The three record companions are untouched. The docs link gate and `spec-surface-check` are the session lead's, after the render and the scoped stamp.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff), its findings applied; the deferred-work row or rows are closed in their ledgers by the session lead, and the full local `pr-preflight` gates the PR that lands it (branch `named-blocker-rows-2026-11-25`).
