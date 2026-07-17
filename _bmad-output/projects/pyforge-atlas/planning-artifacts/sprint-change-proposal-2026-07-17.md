# Sprint Change Proposal — pyforge-warden Alignment — 2026-07-17

**Status: APPROVED (owner, attended, in-session) and APPLIED same-day.**
Workflow: `bmad-correct-course` (unattended execution of a pre-approved
change; mode = Batch; PRD/epics/architecture loaded; UX N/A; scope = Minor).

## 1. Issue Summary

Owner directive after Wave 0 closed (Story 0.1 done, Wave A not started):
the pyforge-atlas module/product must be **in line with pyforge-warden's
import statements and packaging**, with the relationship fixed as
**"atlas provides the data, warden uses the data"**, and the two tools
**able to exist independently of each other**.

Discovery context: the architecture spine had *deliberately deferred*
"physical scaffold naming (scaffold root dir, Python package name)" to the
A1 story spec — so this change fills a designated open slot before its
owner story starts. No shipped code is affected (the only Wave-0 code
artifact, `cf-atlas-legacy`, is execution scaffolding outside the product
package).

## 2. Impact Analysis

- **Epic impact**: Epic 2 (Wave A) — A1 gains packaging ACs. Epic 7
  (Wave F) — F4's schema-conformance AC sharpened. No epic added/removed/
  reordered; no story renumbering (spec IDs frozen).
- **Story impact**: A1 (+3 ACs, invariants row), F4 (1 AC rewritten
  stronger). All other stories untouched.
- **Artifact conflicts**: none — the spine's Deferred row anticipated this
  decision; FR-15/FR-18 already accommodate it (no PRD FR text changes).
- **Technical impact**: none yet (A1 unstarted). The readiness verdict
  (READY, 2026-07-17) stands — the gate had classified this naming as
  A1-owned.

## 3. Recommended Approach

**Direct Adjustment** (chosen): fill the deferred slot with the
warden-pattern packaging convention; no rollback, no MVP change.
Effort: planning-artifact edits only. Risk: LOW — one recorded technical
risk (Kedro-project-inside-a-namespace-package) mitigated by an A1 import
smoke + a recorded flat-package fallback. Timeline impact: none.

## 4. Detailed Changes (applied)

### 4.1 Architecture spine (`ARCHITECTURE-SPINE.md`)

1. **Structural Seed**: placeholders resolved —
   `<scaffold-root>` = `src/shared/packages/pyforge-atlas/`;
   `<pkg>` = `pyforge.atlas` namespace package (`src/pyforge/atlas/`).
2. **New consistency-convention row — "Packaging & namespace
   (warden-aligned)"**: workspace member mirroring `pyforge-warden`
   (hatchling; dual conda + wheel/sdist artifacts; dedicated
   `[feature.pyforge-atlas]` env + build tasks); floors differ by design
   (atlas 3.14, warden ≥3.12); shared third-party deps co-resolve at
   workspace level; **one optional code edge** atlas→warden; **zero**
   warden→atlas code edges; both tools independently installable/runnable.
3. **AD-12**: schema-by-import sentence — F4 validates against
   `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra,
   never a vendored copy.
4. **Deferred**: physical-scaffold-naming row marked RESOLVED with pointer
   here.
5. **Decisions & Assumptions**: entry 10 (this correct-course).

### 4.2 Epics (`epics.md`)

- **A1**: +3 ACs (workspace-member scaffold root; `pyforge.atlas`
  namespace package + namespace-Kedro import smoke with flat
  `pyforge_atlas` fallback; `[gate]` extra wiring) + invariants row update;
  starter-template preamble note updated.
- **F4**: schema-conformance AC rewritten to schema-by-import with the
  explicit-failure independence semantics.
- **Decisions**: D-16 (this correct-course + the dependency inventory).

### 4.3 PRD (`prd.md`)

- § 9.13 decision entry (relationship statement, one-optional-dependency
  rule, warden as first-class data consumer). No FR changes.

## 5. Dependency Inventory (the owner's two questions, answered)

**"Other than schema, are there any dependencies?"** — No other *code*
dependencies. The complete inventory:

| Edge | Kind | Mechanism |
|---|---|---|
| atlas → warden | CODE (the only one) | optional extra `pyforge-atlas[gate]`: ComplianceReport schema + validators (+ exit-code constants if warden exports them), consumed only by the F4 terminal-gate node |
| atlas → warden | CONTRACT | frozen exit enum {0,1,2,130} (AD-12) — a convention, not an import |
| warden → atlas | DATA (optional-if-present) | KEV/EPSS refresh stores, Basilisk vulns (B8), release velocity (B9), pypi↔conda mapping — file/DB-level reads; wiring warden's axes to consume them is a **future warden-side story**, never an import |
| both → third-party | SHARED DEPS | `cyclonedx-python-lib`, `jsonschema`, `PyYAML`, `packaging` (Python); `deptry` (conda tool dep) — workspace co-resolution, no coupling |
| warden → osv-scanner | TOOL | warden-only; atlas never invokes osv-scanner (AD-12) |

**"Can the tooling exist independently of each other?"** — **Yes, both
directions, by construction:**
- **warden without atlas**: fully standalone today and forever — zero atlas
  imports; it fetches its own KEV/EPSS; atlas datasets only ever *enhance*
  it when present.
- **atlas without warden**: everything runs except the F4 gate node, which
  requires the `[gate]` extra and fails with a hyper-clear install hint if
  absent (agent-legibility bar, spec § 2.1). The in-repo atlas env installs
  the extra by default, so the repo-scope gate always works here.
- Escape hatch recorded: if either tool ever ships fully outside this
  repo, the schema can be extracted to a `pyforge-schemas` micro-package
  without changing any import sites (warden would re-export) — deliberately
  NOT done now (Simplicity First).

## 6. Implementation Handoff

**Scope: Minor** → Developer agent, folded into the normal flow: the A1
story draft inherits the new ACs from epics.md (no separate work item);
F4 inherits at Wave F. Success criteria: A1's `kedro-test` import smoke
passes on `pyforge.atlas` (or the fallback decision is recorded);
`pixi.toml` gains the `[feature.pyforge-atlas]` wiring mirroring warden's;
F4's fixtures validate via the imported schema module.
