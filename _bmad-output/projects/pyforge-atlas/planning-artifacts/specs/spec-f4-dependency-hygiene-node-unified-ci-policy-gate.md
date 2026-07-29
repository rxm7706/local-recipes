---
title: 'Story F4 (7.4): Dependency-hygiene node + unified CI policy gate'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #95 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/7-4-f4.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
- [x] a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
- [x] the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
- [x] the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
- [x] the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #95). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**This is the story where Atlas stops judging and starts deferring to Warden.** Two nodes in
the `universal_sbom` terminal stage converge what used to be CLI-text scraping into **one
schema-validated `ComplianceReport` and one frozen exit code**.

**Warden's schema is imported, never vendored.** The report is validated against
`pyforge.warden`'s schema through the optional `[gate]` extra, so drift between the two
packages is impossible by construction. Exit codes are **sole-owned by
`pyforge.warden.verdict`**: no module here maps a status to an exit code, and every exit
code is produced by `verdict.exit_code_for` rather than a bare `int` or
`sys.exit(<literal>)`.

**Absent extra degrades precisely.** Without `[gate]` installed, **only the gate node fails**,
with an explicit install hint — every other pipeline still runs. A missing optional
dependency does not take the DAG down with it.

**Source-less intake is `not-applicable`, never a failure.** A bare manifest, lockfile, or
SBOM with no accompanying source tree cannot have dependency hygiene assessed, so the node
says exactly that. This is the kernel's marker discipline in practice: *nothing existed to
assess* is not the same as *we failed*.

**deptry runs in Warden's process boundary, not ours.** Execution is delegated to
`pyforge.warden`'s `DeptryEngine` — that package's sole subprocess site. This module never
spawns a subprocess itself, which keeps the "one module alone spawns subprocesses" property
true across the package boundary rather than only within each package.

**One terminal producer (AD-12).** Exactly one node assembles the four-axis report — hygiene
from the deptry node, security from the atlas-native path — and on a policy breach it
**halts Dagster by reusing F2's `DataContractViolation`**. Reusing the halting mechanism
rather than inventing a second one is why there is a single failure semantics across
validation and policy.

**A deprecation window, handled honestly.** `inventory_match_exit_code` **remaps** Warden's
frozen output for the legacy inverted `inventory-match` enum, gated behind
`INVENTORY_MATCH_LEGACY_EXIT` for one release. It is explicitly a remap of the frozen
contract's output — not a second exit-code authority.

**Default policy is strict.** `max_critical=0` is the shipped default, per spec.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-F4]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-F4]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#95** — story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18/10) |
| Merged | 2026-07-18 |
| Diff | 9 files, +886 / -12 |
| Test files touched | 6 |

**Commits**

- `fd8e1c9` story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18…

**File list** *(exact, from the merged diff)*

```
  461 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py
  364 +     0 -  src/shared/packages/pyforge-atlas/tests/policy_gate/test_policy_gate.py
   20 +     2 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/pipeline.py
   12 +     8 -  src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py
   17 +     0 -  src/shared/packages/pyforge-atlas/conf/base/catalog.yml
    8 +     0 -  src/shared/packages/pyforge-atlas/tests/policy_gate/fixtures/unused_dep_project/pyproject.toml
    2 +     2 -  src/shared/packages/pyforge-atlas/tests/catalog/conftest.py
    2 +     0 -  src/shared/packages/pyforge-atlas/tests/policy_gate/fixtures/unused_dep_project/pkg/__init__.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/policy_gate/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `fd8e1c9`** — story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18/10)
  - Closes Wave F. Adds the deptry dependency-hygiene node + the converged four-axis
  - policy gate as the Universal SBOM pipeline's TERMINAL stage — one
  - schema-validated ComplianceReport + one frozen exit code replace CLI scraping.
  - - SCHEMA BY IMPORT, never vendored (AD-12, the correct-course rule): the gate
  - validates against pyforge.warden.models.ComplianceReport imported LAZILY via
  - the pyforge-atlas[gate] extra. Absent the extra, the gate node fails with an
  - explicit GateDependencyMissing install hint while the atlas package + every
  - OTHER pipeline import and run unaffected (independence — proven with warden
  - blocked). No vendored ComplianceReport/Status/verdict anywhere.
  - - EXIT CODES sole-owned by warden's verdict.exit_code_for (0 clean / 1
  - policy-fail / 2 error) — never a hand-rolled literal or sys.exit; the
  - inventory-match one-release window (INVENTORY_MATCH_LEGACY_EXIT) REMAPS
  - warden's frozen output (1<->2), never re-derives it.
  - - Four-axis assembly: hygiene + security populated; license/currency from
  - atlas-native data or not-applicable. Source-less inputs -> not-applicable,
  - NEVER failure (FR-16). SINGLE producer of the ComplianceReport (AD-12).
  - - A policy breach halts with F2's DataContractViolation + an E1 A2A alert —
  - identical failure semantics to an FR-10 violation.
  - Reviewer fixes (both in-loop reviewers): the WARN branch no longer min()s over
  - an empty sequence when the security axis carries only warden's indeterminate:*
  - ids (MUST-FIX crash) — it drives the WARN off the smallest real finding id; an
  - out-of-vocab severity tier degrades to 'unknown' instead of crashing
  - SeverityTier(); a whitespace-only build_stamp uses .strip() so it falls back to
  - 'unknown-build' instead of masking the breach with a stamp ValueError. 682
  - passed (+22).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#95`.

<!-- end retro story -->

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #95: story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18/10)
