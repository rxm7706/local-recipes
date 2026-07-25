---
title: 'Story F4 (7.4): Dependency-hygiene node + unified CI policy gate'
type: 'feature'
status: 'regenerated'
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

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #95: story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18/10)

## Summary

**Closes Wave F.** Adds the deptry dependency-hygiene node + the converged **four-axis policy gate** as the Universal SBOM pipeline's **terminal** stage — one schema-validated `ComplianceReport` + one frozen exit code replace CLI scraping.

- **Schema BY IMPORT, never vendored (AD-12, the correct-course rule):** validates against `pyforge.warden.models.ComplianceReport` imported **lazily** via the `pyforge-atlas[gate]` extra. Absent the extra, the gate node fails with an explicit `GateDependencyMissing` install hint while the atlas package + every **other** pipeline import and run unaffected (independence — proven with warden blocked). No vendored `ComplianceReport`/`Status`/verdict anywhere.
- **Exit codes sole-owned by warden's `verdict.exit_code_for`** (0 clean / 1 policy-fail / 2 error) — never a hand-rolled literal or `sys.exit`; the inventory-match one-release window **remaps** warden's frozen output (1↔2), never re-derives it.
- **Four-axis assembly:** hygiene + security populated; license/currency from atlas-native data or `not-applicable`. Source-less inputs → `not-applicable`, **never failure** (FR-16). **Single producer** of the `ComplianceReport` (AD-12).
- A policy breach **halts** with F2's `DataContractViolation` + an E1 A2A alert — identical failure semantics to an FR-10 violation.

## Review fixes (both in-loop reviewers)

- The WARN branch no longer `min()`s over an **empty sequence** when the security axis carries only warden's `indeterminate:*` ids (MUST-FIX crash) — it drives the WARN off the smallest real finding id (exit 0, no false halt).
- An out-of-vocab severity tier (e.g. `"important"`) degrades to `unknown` instead of crashing `SeverityTier()`.
- A whitespace-only `build_stamp` uses `.strip()` so it falls back to `"unknown-build"` instead of masking the breach with a stamp `ValueError`.

## Tests

`682 passed` (+22 new).

### Commits on `main`

- `8052a9857e` story(F4): dependency-hygiene node + unified CI policy gate (FR-16/18/10)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

