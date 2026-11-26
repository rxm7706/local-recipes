---
title: '55.1: The dossier is rewritten from a fresh read of the source, to one outline, with no history'
type: 'docs'
created: '2026-11-26'
status: 'done'
story: 55-1-the-dossier-is-rewritten-from-a-fresh-read-of-the-source-to-one-outline-with-no-history
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'docs-site/src/content/dossier/dossier.yml'
  - 'docs-site/src/content/ci-status.json'
  - 'docs-site/scripts/verify_claims.py'
  - 'docs-site/README.md'
  - 'src/shared/packages/pyforge-herald/tests/**'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The dossier's stats bands are counted at build, and its prose is not held to anything. About sixty lines tell of earlier reads of the source ("since the last pass", a README since corrected), counts typed into sentences have drifted from the tree, one note points at a page that does not exist, and notes marked "not verified" have stood since September. A reader cannot tell which sentence is today's.

**Approach:** Read each station and the kernel again from source on one day, and write every section but the A→B control plane from that read. Each station section opens with a plain account of what the station is for (the page is also a newcomer's introduction) and then follows one outline: Commands, MCP face, State, Relationships, Held by tests. The cross-fleet section leaves the page. The measurer gains `stories_open` (open over blocked stories, from the tracked ledger), shown in each station band in place of the Python floor. The CI-surfaces snapshot is taken again. Tests hold the shape: the section list, the outline, the closed list of earlier-read phrases, no comma-grouped figure in running text, and `stories_open` in every station band.

Ledger key: `55-1-the-dossier-is-rewritten-from-a-fresh-read-of-the-source-to-one-outline-with-no-history`.

### Living CAP citations

- spec-pyforge-herald CAP-64 (minted 2026-11-26); FR-12.6 ← CAP-64.
- spec-pyforge-herald CAP-46 (amended 2026-11-26); FR-12.5 ← CAP-61, CAP-46.
- No AD moves (pyforge-herald:AD-23 holds).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the A→B section's and § 10's `asserts:` resolving true; keep the eyebrow, estate, verified and footer dates equal.
- State a fact only where the source read of 2026-11-26 confirmed it; put what it could not confirm in the section's closing note.

**Never:**
- Never loosen `test_dossier_cutover_claims.py`.
- Never type a count into running text that the build does not measure.
- Never fix a convention gap in another station's code here; each is that station's chain.

## Acceptance Criteria

**Given** the dossier's station sections and its cross-fleet section tell of earlier reads of the source, type counts the build does not measure, and carry notes left unverified
**When** each station and the kernel is read again from source, each station section is written to the one outline, the cross-fleet section is removed, the measurer gains `stories_open`, and the CI-surfaces snapshot is taken again
**Then** the dossier's sections are the A→B cutover, the shared spine, the eight stations and § 10; no block names an earlier read; no running text types a comma-grouped figure; every station stats band shows stories open over blocked, counted from its ledger
**And** the control-plane `asserts:` still resolve true, and the site builds

- **AC1 — Herald's live-tree half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

- **AC2 — The measurer counts `stories_open`.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py -q
  ```

- **AC3 — The site builds and checks.** Expected: exit 0.

  ```bash
  pixi run --frozen -e site pages-check
  ```

</intent-contract>

## Source read (2026-11-26, main `c5fbba0bb4`)

Ten read-only passes, one per station, one for `pyforge-core` and `pyforge-testing-kit`, one across the fleet. Each audited the existing section claim by claim and returned current facts with a path for each. Parsers were read, not run (marshal's was enumerated by importing it in memory). What the read corrected, beyond removing history:

- **Atlas:** all twelve pipelines are registered (the page said three were not); no Atlas code reads `cf_atlas.db` (the page said the dashboard did); the dashboard's status page reads Atlas's own Tier-3 feed.
- **Doctor:** the quoted description was a misquote; `check` also runs durability by default; many more than six modules judge Marshal; package-watch data comes through the conda-forge-expert tooling, not `pyforge.atlas`.
- **Herald:** not every write handler passes the role gate (no `deck` verb does); the portal has more than a status page.
- **Marshal:** the MCP server is on the official `mcp` SDK, not FastMCP; "six dedicated modules" matched nothing in source; no standalone Marshal dossier exists.
- **Mason:** the wrappers are not one-to-one; `dist/` artifacts are not in the tree; the `engines/gh.py` docstring is the stale half of the noted discrepancy.
- **Scribe:** one storage backend per owner (the page gave Steward two); `--semantic` finds nothing on the default store.
- **Steward:** `/console/` is platform-host code and does not call `ledger-query`; Steward wraps no Doctor fleet-scan output.
- **Warden:** `clean` outranks `not-applicable`; five stub scanners, not four; the fix-PR actuator is not the only forge egress (the fleet modules call GitHub too); `AD-n` tags do appear.
- **Kernel:** Herald imports `dispatch_exit_code`, not `Lattice`; Doctor's exceptions do not inherit `PyforgeError`; the testing kit is not a leaf.

## Deferred

- The open convention gaps the removed cross-fleet section listed (hook-plugin naming, exit-code domains for mason, steward, herald, scribe and atlas, CLI shape, MCP placement, fleet-status sources, the `doctor` name collision) are not carried on the page any more. Fixing them is each owning station's chain, by operator ruling of 2026-11-26 ("rederive the open convention gaps and fix them all").
- Stale docstrings the read found in other stations' source: mason `engines/gh.py` and `models.py` (`ShipState`), scribe `__init__.py` and `compile.py`, atlas `admission.py`, steward `interfaces.py`, herald `auth.py` (a refusal message naming a command that does not exist).

## Review (2026-11-26)

Independent review by two fresh reviewers running `bmad-review`, neither given the implementer's reasoning: one checked every factual claim in the shared-spine and station sections against source, one read the page as a newcomer and as the operator. Verdict of the second: partly met, with three named changes. Accepted and applied: flag defaults stated per environment (herald and warden flags are off in the tree and on in the development overlay); marshal's state-changing MCP tools named; the atlas quote given in full; mason's subprocess and stdout rules stated as the tests state them; doctor's detectors run in-process; steward's exit 2 and exit 3 told apart; the summary says what PyForge is; a glossary opens the A→B section, which states each fact once under one Operator watch block; commands for marshal and steward are tables; every Commands heading ends with exit codes; notes about stale docstrings in other stations left the page (listed under Deferred). Not applied: moving the package quotes below the ledes (they are attributed and verbatim), and cutting the kernel table to six rows (it is the reference a reader of a station's Relationships needs). The count rule was narrowed on the Spec memlog the same day: lines, files, stories and epics are never typed; another count stands only beside the things it counts.
