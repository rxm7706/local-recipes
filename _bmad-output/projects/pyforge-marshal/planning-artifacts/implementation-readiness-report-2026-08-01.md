---
stepsCompleted: [1]
project: pyforge-marshal
scope: spec-pyforge-marshal chain (marshal CLI) — re-run of the 2026-07-25 gate
---

# Implementation Readiness Assessment Report

**Date:** 2026-08-01
**Project:** pyforge-marshal (Marshal CLI chain)

## Step 1 — Document Discovery

**Scope note:** `{planning_artifacts}` (the repo-root symlink) currently resolves to
`pyforge-atlas`, not `pyforge-marshal`. All discovery below used the **physical
path** `_bmad-output/projects/pyforge-marshal/planning-artifacts/` directly, per
this repo's parallel-agent / physical-path convention.

### Documents in scope

| Type | File | Status |
|---|---|---|
| Dream (Tier 0) | `docs/dreams/pyforge-marshal.md` | realized |
| Spec (kernel) | `specs/spec-pyforge-marshal/SPEC.md` + `glossary.md` (companion) | re-rendered 2026-08-01, 9 CAPs |
| Brief | `product-brief-pyforge-marshal.md` | updated 2026-08-01 |
| PRD | `prds/prd-pyforge-marshal-2026-07-25/prd.md` | final, updated 2026-08-01, 60 FRs / 14 NFRs / 10 C |
| Architecture | `architecture/architecture-pyforge-marshal-2026-07-25/architecture.md` | updated 2026-08-01, 45 ADs |
| Epics & Stories | `epics.md` | updated 2026-08-01, 6 epics / 45 stories |
| UX | — | correctly absent; Marshal is a deterministic CLI, no UX artifact declared anywhere upstream |

Selection basis: `SPEC.md` frontmatter's own `companions:` list names these exact
paths as the adopted chain — not inferred, read directly from the contract.

### CRITICAL — cross-project contamination in the search glob (resolved, not a real duplicate)

A naive `*prd*.md` / `*architecture*.md` glob over
`_bmad-output/projects/pyforge-marshal/planning-artifacts/` returns 8 extra
files that are **not pyforge-marshal documents**:

`PRD.md`, `architecture.md`, `architecture-bmad-infra.md`,
`architecture-cf-atlas.md`, `architecture-conda-forge-expert.md`,
`architecture-mcp-server.md`, `integration-architecture.md`,
`validation-report-PRD.md`

Frontmatter on every one reads `project_name: local-recipes` — these are the
**repo-level `local-recipes` BMAD chain** (PRD v1.7.0, architecture v1.1.0, the
4-part architecture shards, the CFE/cf_atlas/MCP integration doc), physically
stranded inside `pyforge-marshal`'s tree. No `_bmad-output/projects/local-recipes/`
directory exists, confirming these are not a legitimate second copy of anything
— they are orphaned from a past symlink desync (the same class of near-miss
CLAUDE.md's multi-project section documents: the `planning_artifacts` symlink
pointed at `pyforge-marshal` at some point while a `local-recipes`-scoped skill
run wrote through it).

**Excluded from this assessment.** Flagged here as a housekeeping finding for a
separate cleanup pass (relocate or delete) — out of scope for a marshal-chain
readiness gate and not blocking.

### Sibling artifacts present, correctly out of scope

`prds/prd-genesis-installer-2026-07-25/prd.md`,
`architecture/architecture-genesis-installer-2026-07-25/architecture.md`,
`epics-genesis-installer.md`, `epics-regenerable-factory.md` — legitimate
pyforge-marshal-project artifacts for the genesis-installer fold and the
regenerable-factory effort, co-located by design (multi-effort project
convention). Not part of the marshal-CLI SPEC's own surface; excluded from
FR/AD/story traceability below, noted only where the fold decision touches
Marshal's own non-goals (§8 IDE-exclusion annotation, epics.md installer-fold
references).

### No duplicates within the marshal-CLI chain itself

Each of the 5 in-scope documents exists in exactly one form (no sharded index.md
variants). Proceeding to Step 2.

## Step 2 — PRD Analysis

PRD loaded and read completely: `prds/prd-pyforge-marshal-2026-07-25/prd.md`
(878 lines, `status: final`, `updated: 2026-08-01`).

### Functional Requirements Extracted

**§7.1 Loop homes and isolation (FR-1..FR-8):**
- FR-1: Provision a loop home — one command creates an isolated loop home for a project slug.
- FR-2: Per-worktree active-project state — each home's marker + planning symlinks are independent.
- FR-3: Single-sourced Tier-3 store — `implementation-artifacts` resolves to one canonical directory.
- FR-4: Isolation verification — assert N≥2 homes are genuinely isolated.
- FR-5: Preflight — verifies the run can start rather than discovering it cannot at minute 90.
- FR-6: Teardown — remove a loop home cleanly.
- FR-7: Adapter config seeding — gitignored adapter config a fresh worktree lacks is seeded.
- FR-8: Enumerate loop homes — list all homes with resolved active project.

**§7.2 Run supervision (FR-9..FR-18):**
- FR-9: Detached launch by default.
- FR-10: Scoped launch — story, epic, count, or whole feed.
- FR-11: Supervisor attaches to every run for its lifetime.
- FR-12: Idle-strand detection — before any token/time cap.
- FR-13: Budget ceilings — token + wall-clock, named stop. *(Re-scoped 2026-08-01: external, un-disableable enforcement; upstream v0.9.0's in-session guards credited, not duplicated.)*
- FR-14: Heaviest-story budget advisory.
- FR-15: Escalation surfacing.
- FR-16: Deferral capture.
- FR-17: Resume — after a human resolves the blocking condition. *(Extended 2026-08-01 — AD-45: resume journal entry records a reference to the resolving decision/artifact.)*
- FR-18: Run journal — durable, append-only, Marshal-owned.

**§7.3 Gates and verification (FR-19..FR-27):**
- FR-19: Standalone gate evaluation — no run in flight.
- FR-20: Project-scoped verify commands.
- FR-21: Deterministic, no-LLM gates.
- FR-22: Frozen-surface scope check.
- FR-23: Doc-only story classification.
- FR-24: Gate mode ladder, labelled with autonomy level.
- FR-25: Gate evidence record.
- FR-26: Never false-green.
- FR-27: Review-cap landing path.

**§7.4 Landing and paper trail (FR-28..FR-35, FR-59, FR-60):**
- FR-28: Batch pull request.
- FR-29: Repository-hygiene preflight.
- FR-30: Automatic story-spec promotion.
- FR-31: Spec-recovery assistance.
- FR-32: Merge-subject conformance.
- FR-33: Sprint and console feed refresh.
- FR-34: Deploy is idempotent and re-runnable.
- FR-35: No AI attribution in emitted artifacts.
- **FR-59** *(added 2026-08-01 — CAP-9)*: Landing rules are declared policy — required checks, merge strategy, labels (incl. this repo's `maintenance` label + ungated env-sync), branch retirement, resync compose with per-key provenance.
- **FR-60** *(added 2026-08-01 — CAP-9)*: `marshal land` — a passed-gate story/wave lands without a human driving the sequence; idempotent, re-entrant, teardown-grade refusals, per-landing journal verdict.

**§7.5 Fleet visibility (FR-36..FR-40):**
- FR-36: Fleet view — every home + state, one command.
- FR-37: Per-run detail.
- FR-38: Escalation queue, surfaced first.
- FR-39: Ledger-versus-git reconciliation.
- FR-40: Stable machine-readable status contract.

**§7.6 Adapter portability (FR-41..FR-48):**
- FR-41: Skill-tree projection.
- FR-42: Projection drift detection.
- FR-43: Adapter probe.
- FR-44: Conformance smoke.
- FR-45: Conformance matrix, keyed by host.
- FR-46: Entry-file family drift check.
- FR-47: First-run acknowledgement per adapter.
- FR-48: Adapter selection is project-scoped.

**§7.7 Policy composition (FR-49..FR-54):**
- FR-49: Layered policy composition, ordered precedence.
- FR-50: Project-scoped policy without hand-editing.
- FR-51: Per-story model tiering.
- FR-52: Single harness seam.
- FR-53: Policy validation before launch.
- FR-54: Configuration is inspectable, provenance shown.

**§7.8 Packaging and distribution (FR-55..FR-58):**
- FR-55: Package identity and layout.
- FR-56: Conda and wheel artifacts.
- FR-57: Version and capability reporting (Marshal + harness).
- FR-58: Upstream contribution register. *(Updated 2026-08-01: non-POSIX-multiplexer entry closed as delivered — upstream v0.9.0 shipped a Windows psmux backend.)*

**Total FRs: 60** (FR-1..FR-58 + FR-59, FR-60; no gaps, no reused numbers, IDs stable per SPEC.md's CAP-N discipline).

### Non-Functional Requirements Extracted

- NFR-1 — Determinism: every decision path deterministic, LLM-free.
- NFR-2 — Offline by default: no silent network use.
- NFR-3 — Never false-green: unevaluable ≠ pass.
- NFR-4 — Supervisor independence: observes from outside the session, cannot be disabled/silenced/misled.
- NFR-5 — Structural over conversational governance.
- NFR-6 — No destructive default: no force-push, teardown refuses on unmerged work.
- NFR-7 — Idempotence: init/deploy/adapters-sync/policy composition converge on re-run.
- NFR-8 — Durable, self-owned evidence: survives teardown, no vendor-retention dependency.
- NFR-9 — Harness contract tests: CI-run, fail loudly on upstream drift.
- NFR-10 — Lean dependencies: conda-forge-available, harness not vendored.
- NFR-11 — Secret hygiene: redaction by construction.
- NFR-12 — Machine-readable everything: versioned schema per human output.
- NFR-13 — Platform targets: linux-64 + osx-arm64 v1, Windows WSL-only.
- NFR-14 — Performance envelope: init/status seconds; supervisor poll ≤ prompt-cache TTL.

**Total NFRs: 14.**

### Additional Requirements — Constraints (C-1..C-10)

- C-1: no merge without green verify + scope check (FR-26).
- C-2: escalations pause, never self-resolve.
- C-3: Marshal writes only within the loop home, canonical Tier-3, and explicitly-promoted targets — never a shared cross-project file. *(Governs AD-42, AD-45's "pull, never push" design.)*
- C-4: `main` never checked out in a second working tree; publish by push or batch PR.
- C-5: allowlist, never denylist.
- C-6: every run has a ceiling; no unbounded mode.
- C-7: model tiering is policy, not a hand edit.
- C-8: external harness, declared + enforced supported range (FR-57).
- C-9: depends on BMAD Method artifact conventions for the story feed.
- C-10: a worktree is not a sandbox — process/network isolation is explicitly not provided.

**Total Constraints: 10.**

### PRD Completeness Assessment

The PRD is internally coherent and current. Every FR carries a stated
requirement, a Consequences block, and (where load-bearing) a Grounding note
citing the incident or evidence that motivated it — the discipline the brief's
"honest moat" section claims is upheld in the PRD's own text. The 2026-08-01
additions (FR-59/60) follow the same shape as the other 58 and are traceable to
a named operator ruling (`docs/dreams/pr-lifecycle.md`), not invented. Two
non-blocking observations carried to Step 5 (cross-document consistency):
FR-59/FR-60 are numbered out of the §7.4 sequence (appended after FR-35 rather
than renumbered) — intentional per this repo's stable-ID discipline (SPEC.md
CAP-N convention forbids renumbering), but worth a one-line note in the PRD
itself if not already present. C-3's "never a shared cross-project file" is the
same invariant AD-45 cites for the pull-only escalation design — confirmed
consistent, not contradictory.

## Step 3 — Epic Coverage Validation

`epics.md` loaded completely (6 epics, 45 stories). Coverage extracted two ways
and cross-checked: (a) the file's own FR-group headers (§ "Epic List" preamble)
declare which FR ranges belong to which epic; (b) every individual story's
`**FR/AD:**` line was parsed programmatically and mapped FR-by-FR to its
covering stories — the second method is the ground truth below, since (a) is
declarative and (b) is what a story actually implements.

### Coverage Matrix (full — all 60 FRs)

| FR | PRD requirement | Epic · Story coverage | Status |
|---|---|---|---|
| FR-1 | Provision a loop home | 1.1, 1.4, 2.1 | ✓ |
| FR-2 | Per-worktree active-project state | 1.4, 2.1, 4.4 | ✓ |
| FR-3 | Single-sourced Tier-3 store | 1.5, 2.2, 2.3 | ✓ |
| FR-4 | Isolation verification | 1.6, 3.4, 3.5 | ✓ |
| FR-5 | Preflight | 1.7, 2.3, 2.5, 3.4, 6.9 | ✓ |
| FR-6 | Teardown | 1.8, 4.2, 4.8 | ✓ |
| FR-7 | Adapter config seeding | 1.4, 1.7, 4.6, 4.8 | ✓ |
| FR-8 | Enumerate loop homes | 1.6, 2.6, 3.1 | ✓ |
| FR-9 | Detached launch by default | 3.3, 6.4 | ✓ |
| FR-10 | Scoped launch | 1.1, 1.9, 3.3 | ✓ |
| FR-11 | Supervisor attaches to every run | 2.6, 3.4, 4.4, 6.4 | ✓ |
| FR-12 | Idle-strand detection | 1.1, 1.2, 3.5, 5.2, 5.4 | ✓ |
| FR-13 | Budget ceilings | 1.9, 3.6 | ✓ |
| FR-14 | Heaviest-story budget advisory | 3.6, 5.1 | ✓ |
| FR-15 | Escalation surfacing | 3.7 | ✓ |
| FR-16 | Deferral capture | 3.7 | ✓ |
| FR-17 | Resume | 3.7 | ✓ |
| FR-18 | Run journal | 3.1, 3.2 | ✓ |
| FR-19 | Standalone gate evaluation | 2.1 | ✓ |
| FR-20 | Project-scoped verify commands | 2.1 | ✓ |
| FR-21 | Deterministic, no-LLM gates | 2.1 | ✓ |
| FR-22 | Frozen-surface scope check | 2.3 | ✓ |
| FR-23 | Doc-only story classification | 2.4 | ✓ |
| FR-24 | Gate mode ladder | 2.5 | ✓ |
| FR-25 | Gate evidence record | 2.6 | ✓ |
| FR-26 | Never false-green | 2.2 | ✓ |
| FR-27 | Review-cap landing path | 4.3 | ✓ |
| FR-28 | Batch pull request | 4.4 | ✓ |
| FR-29 | Repository-hygiene preflight | 4.4 | ✓ |
| FR-30 | Automatic story-spec promotion | 4.1 | ✓ |
| FR-31 | Spec-recovery assistance | 4.2 | ✓ |
| FR-32 | Merge-subject conformance | 1.2, 4.3 | ✓ |
| FR-33 | Sprint and console feed refresh | 4.5, 4.9 | ✓ |
| FR-34 | Deploy idempotent and re-runnable | 4.6 | ✓ |
| FR-35 | No AI attribution | 4.4 | ✓ |
| FR-36 | Fleet view | 5.1 | ✓ |
| FR-37 | Per-run detail | 5.2 | ✓ |
| FR-38 | Escalation queue | 5.3 | ✓ |
| FR-39 | Ledger-versus-git reconciliation | 5.4 | ✓ |
| FR-40 | Stable machine-readable status contract | 5.4 | ✓ |
| FR-41 | Skill-tree projection | 6.2 | ✓ |
| FR-42 | Projection drift detection | 6.3 | ✓ |
| FR-43 | Adapter probe | 6.4 | ✓ |
| FR-44 | Conformance smoke | 6.5 | ✓ |
| FR-45 | Conformance matrix | 6.6 | ✓ |
| FR-46 | Entry-file family drift check | 6.7 | ✓ |
| FR-47 | First-run acknowledgement per adapter | 1.7 | ✓ |
| FR-48 | Adapter selection is project-scoped | 6.1 | ✓ |
| FR-49 | Layered policy composition | 1.3, 1.10, 6.9 | ✓ |
| FR-50 | Project-scoped policy, no hand-editing | 1.3, 1.10 | ✓ |
| FR-51 | Per-story model tiering | 1.10, 6.1 | ✓ |
| FR-52 | Single harness seam | 3.3 | ✓ |
| FR-53 | Policy validation | 1.3 | ✓ |
| FR-54 | Configuration is inspectable | 1.3 | ✓ |
| FR-55 | Package identity and layout | 1.1, 1.9 | ✓ |
| FR-56 | Conda and wheel artifacts | 1.9 | ✓ |
| FR-57 | Version and capability reporting | 1.1, 1.9 | ✓ |
| FR-58 | Upstream contribution register | 6.8 | ✓ |
| **FR-59** | Landing rules are declared policy *(2026-08-01)* | 4.7 | ✓ |
| **FR-60** | `marshal land` *(2026-08-01)* | 4.8 | ✓ |

### Missing Requirements

**None.** All 60 FRs (including the two 2026-08-01 additions) trace to at least
one story; FR-15/16/17 and FR-19/20/21 each concentrate in one tight story,
which is a design choice (small cohesive stories), not a gap.

One **borderline** item, not a missing FR but worth a naming note: FR-52
(single harness seam) is covered by **Story 3.3** ("Detached launch with
scoped story selection") rather than by a dedicated architecture-conformance
story — the constraint is enforced by an import-linter test threaded through
3.3's acceptance criteria per AD-3. Confirmed present, not absent; flagged for
Step 5 cross-document consistency only if the enforcement mechanism's naming
diverges from what AD-3 promises.

### Coverage Statistics

- Total PRD FRs: **60**
- FRs covered in epics: **60**
- Coverage percentage: **100%**

## Step 4 — UX Alignment

### UX Document Status

**Not found** — confirmed in Step 1's discovery (no `*ux*.md` or `*ux*/index.md`
under the physical `pyforge-marshal` path).

### Is UX implied?

**No.** Marshal is a deterministic CLI, stated explicitly and repeatedly in its
own contract: NFR-1 (no model call anywhere in Marshal's own code), NFR-12
(machine-readable everything — every human-facing output is CLI text plus a
versioned schema, not a rendered UI), and the §8 Non-Goals list "no IDE
extension, no chat participant, no marketplace artifact" and "no HTTP proxy."
Every feature (§7.1–7.8) is an operator-invoked command; the SPEC's own UJ
journeys (`marshal init`, `factory spin`, `gate evaluate`, `land`) are terminal
sessions, not screens. The brief's "explicit non-user" section names IDE-chat
users out of scope for exactly this reason.

### Alignment Issues

None — there is nothing to align against.

### Warnings

None. UX absence is a correct, deliberate scope decision, not a gap.

## Step 5 — Epic Quality Review

Applied without compromise, per the step's mandate. All 45 stories parsed
programmatically (not sampled) for dependency-graph and structural checks;
every epic's Goal statement read for user-value framing.

### A. User Value Focus — 6/6 epics pass

| Epic | Title | Goal framing |
|---|---|---|
| 1 | Provisioned, verified loop homes | "the operator can stand up..." — user outcome |
| 2 | Gates you can run | "the operator can... ask 'would this pass?'" — user outcome |
| 3 | Supervised unattended runs | "the operator can launch... and walk away" — user outcome |
| 4 | Landing with a durable paper trail | "the operator can close a wave in one command" — user outcome |
| 5 | Fleet visibility | "the operator gets one view" — user outcome |
| 6 | Portability proven | "the operator can run the method on another agent" — user outcome |

No technical-milestone epics ("Database setup", "API development",
"Infrastructure"). Every goal names what the **operator** — Marshal's actual
user — can now do, matching the brief's own "who this serves" framing.

### B. Epic Independence — 🔴 one CRITICAL violation found (pre-existing, not introduced this week)

The literal rule ("Epic N cannot require Epic N+1") is written for
user-facing product epics; a supervisor/CLI product has *some* legitimate
sequential infrastructure dependency between epics (Epic 3's supervisor
needs Epic 1's loop homes to supervise). That alone is not a violation — the
graph-level check below is the actual test: **does any epic depend on a
strictly LATER epic**, which is always a violation regardless of product
shape.

Programmatic dependency-graph walk over every story's `**Deps:**` line found
**one**:

**🔴 CRITICAL — Story 2.3 depends on Story 3.2 (Epic 2 → Epic 3, forward reference).**
`Story 2.3: Frozen-surface scope check, narrowing only` declares
`**Deps:** S-1.2, S-2.2, **S-3.2**`. Epic 2 cannot complete without a story
from Epic 3 — the textbook violation this step's rubric names by exact
example ("Epic 2 requires Epic 3 features to function").

**Disposition: pre-existing and already self-documented, not introduced by
this week's edits.** The story itself carries a dated note: *"Dependency
corrected 2026-07-30 (F-9)... the alternative — moving the fold into Epic 2
— was rejected because S-3.2 also owns run-state derivation that Epic 3
needs, and splitting it would give the fold two homes. Epic 2 therefore
completes after S-3.2 lands; the epic boundary is a value boundary, not a
scheduling barrier."* This is a **deliberate, adjudicated tradeoff** (finding
F-9, resolved 2026-07-30), not an oversight — but the rubric's rule is
absolute, so it is reported here as CRITICAL per this step's own "no
compromise" mandate, carried forward as a known-and-accepted deviation
rather than something Step 6 should treat as new-and-blocking.

**No other epic-level violations.** Full epic→epic dependency set: E2→{E1,
**E3**}, E3→{E1}, E4→{E1,E2,E3}, E5→{E1,E3,E4}, E6→{E1,E2} — every other
edge points strictly backward.

### C. Story-level dependency check — clean

All 45 stories' `Deps:` lines resolve to a strictly earlier `(epic, story)`
key **except** the one violation above. No self-references, no circular
references, no dependency on an unnumbered/nonexistent story.

**The four 2026-08-01 stories, individually checked (no new violations):**
- 4.7 (`landing rules as declared policy`): Deps `S-1.3` — earlier epic. Clean.
- 4.8 (`marshal land`): Deps `S-4.4, S-4.7` — same epic, both earlier. Clean.
- 4.9 (`derived surfaces regenerate on main`): Deps `S-4.5, S-4.8` — same epic, both earlier. Clean.
- 6.9 (`tool-surface rendering`): Deps `S-1.7, S-6.1` — earlier epics. Clean.

### D. Acceptance Criteria Review — sample + full check on new stories

All four new stories use proper Given/When/Then BDD structure, cover both a
happy path and at least one refusal/error path, and each AC names a
measurable outcome (a registered finding code, a journal field, an exit
behavior) rather than a vague assertion. Spot-checked against Epic 1–3's
established house style (e.g. Story 1.8's teardown refusal shape, which 4.8
explicitly mirrors) — consistent voice and rigor, no regression.

No vague criteria ("user can login"-class issues) found in the four new
stories or in the 10-row Epic-1 through Epic-6 sample re-read for this pass.

### E. Special Implementation Checks

- **Starter template:** N/A — greenfield CLI package, no scaffolding template
  declared in architecture; Story 1.1 ("package spine...") correctly serves
  the starter-template role architecture doesn't otherwise require.
- **Greenfield indicators:** present — Story 1.1 establishes the package
  spine, verdict lattice, findings registry, and meta-tests before any
  feature story; CI/environment setup is FR-55/56 (Epic 1 packaging).
- **Database/entity creation timing:** N/A — Marshal has no database; the
  closest analogue (journal schema, policy schema) is introduced exactly at
  first use (Story 3.1/1.3 respectively), not batched upfront. Compliant with
  the spirit of the check.

### Best Practices Compliance Checklist (per-epic)

| | E1 | E2 | E3 | E4 | E5 | E6 |
|---|---|---|---|---|---|---|
| Delivers user value | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Functions independently | ✓ | 🔴 (needs E3/S-3.2) | ✓ | ✓ | ✓ | ✓ |
| Stories appropriately sized | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| No forward dependencies | ✓ | 🔴 (2.3→3.2) | ✓ | ✓ | ✓ | ✓ |
| Entities created when needed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Clear acceptance criteria | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Traceable to FRs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Summary of Findings by Severity

**🔴 Critical:** 1 — Story 2.3 → Story 3.2 forward dependency (Epic 2 cannot
complete before Epic 3's journal fold lands). Pre-existing, dated,
self-documented, adjudicated (F-9, 2026-07-30); not introduced by this
week's changes. Not re-litigated here; carried to Step 6 as a **known,
accepted** epic-boundary exception, not a fresh blocker.

**🟠 Major:** 0.

**🟡 Minor:** 1 — FR-52 (single harness seam) is enforced inside Story 3.3's
acceptance criteria rather than a dedicated architecture-conformance story;
confirmed present (see Step 3), naming-only observation.

## Summary and Recommendations

### Overall Readiness Status

**READY WITH CONDITIONS** — not a clean READY, not BLOCKED. Direct verdict,
per this step's mandate not to soften: the chain is coherent, FR coverage is
complete, and none of this week's edits introduced a contradiction — but two
open findings from the prior adversarial gate gate specific *upcoming* Epic 2
stories by name, and one CRITICAL epic-independence violation exists (found
fresh this pass, but pre-existing and already adjudicated).

### Verification against the five re-adjudication questions this pass was asked

- **(a) Every FR traces to a capability and an AD** — verified. All 60 FRs map
  to a §7.x feature group, and every feature group has an AD row in the
  Capability → Architecture Map (including the new FR-59/60 row → AD-40/42).
- **(b) Every AD traces to a PRD constraint or ratified decision** — verified,
  with one honest caveat: **AD-41 and AD-44 currently have no dedicated FR or
  story**, by design — AD-41 (sequence-on-verdicts) states its own route-verb
  surface belongs to the *future* `spec-one-front-door` chain, and AD-44
  (install-time site materialization) is explicitly installer-scope
  (Epics 10–12, the sibling `epics-genesis-installer.md`, not this chain).
  Their absence from the coverage matrix is correct, not a gap — recorded
  here so it is not mistaken for one on a future pass.
- **(c) Every Epic-4/6 story's Deps line resolves to a real prior story** —
  verified for all four new stories (4.7, 4.8, 4.9, 6.9); see Step 5.C.
- **(d) F-2/F-3/F-5/F-6/F-4 are correctly still open, correctly assigned** —
  **verified true.** Nothing in this week's PRD/architecture/epics edits
  touches Epic 2's or Epic 3's implementation (both are still `backlog`), so
  none of the five could have been resolved by this pass, and the addendum's
  epic-head assignments still hold. Sharpened here: **F-3 and F-5 gate
  specific stories, not just "the epic head" in the abstract** — Story 2.1
  (standalone gate evaluation) cannot ship its frozen-set behavior without
  F-3's resolution, and Story 2.3/2.5 need F-5's mid-run-freeze-writer
  decision. F-2 and F-6 are Epic 3 concerns (the journal fold, S-3.1/S-3.2).
  F-4 (trust model) is explicitly *carried, not resolved* by AD-45 and must
  land before Story 3.7's escalation surface ships for real.
- **(e) No contradiction introduced across the five artifacts this week** —
  verified. Cross-read SPEC CAP-9 ↔ PRD FR-59/60 ↔ architecture AD-40/AD-42
  ↔ epics 4.7/4.8/4.9, and AD-43 ↔ epics 6.9 (both independently marked
  post-MVP) — consistent throughout. No FR, AD, or story asserts something
  another artifact denies.

### Critical Issues Requiring Immediate Action

**🔴 Story 2.3 → Story 3.2 forward dependency (Epic 2 → Epic 3).** Not new,
not silently accepted either: this is a rubric-level Critical Violation
(Epic 2 cannot complete independently of Epic 3) that the epics document
itself names, dates, and defends (F-9, 2026-07-30) rather than hides. Two
honest paths forward, neither exercised by this pass because both are product
decisions:
1. **Accept as-is** (recommended, matching the existing note) — the epic
   boundary is explicitly declared "a value boundary, not a scheduling
   barrier" here; Epic 1 already proved sequential-but-interleaved delivery
   works operationally (10/10 shipped). Formalize by adding one sentence to
   §5 of the architecture doc naming this as a deliberate, accepted exception
   to strict epic independence — so a future reader doesn't have to
   rediscover the rationale from one story's inline note.
2. **Split S-3.2's journal fold** so its run-state-derivation half moves to
   Epic 2 — explicitly rejected once already (would give the fold two
   homes); re-opening it is not recommended absent new evidence.

### Recommended Next Steps

1. **Before Story 2.1 or 2.3 begins implementation:** resolve F-3 (which
   journal a standalone evaluation folds) and F-5 (mid-run freeze writer in
   `none`/`per-epic` gate modes) — both are named, unresolved design
   questions blocking those two stories specifically, not abstractly.
2. **Before Story 3.1/3.2 begins implementation:** resolve F-2 (replace the
   blanket unevaluability quarantine with scoped unevaluability) and F-6
   (composite journal id or declared lock for the two-writer append case).
3. **Before Story 3.7 ships for real:** declare the trust model F-4 asks
   for — state plainly whether the governed session is trusted (making the
   attribution guarantee advisory) or specify what makes attribution
   unforgeable. AD-45 carries this forward; it does not answer it.
4. **Optional, low-cost:** add one sentence to the architecture doc's §5
   formalizing the Story 2.3 epic-boundary exception (see Critical Issues,
   path 1) so the rationale survives independent of one story's inline note.
5. **Housekeeping, non-blocking:** relocate or delete the 8 stray
   `local-recipes`-scoped files found in Step 1, sitting inside
   `pyforge-marshal`'s planning-artifacts tree from a historical symlink
   desync.

### Final Note

This assessment found **1 pre-existing Critical** (adjudicated, not
newly-introduced), **0 Major**, **2 Minor** (FR-52 naming, 8 stray files),
across the 6-step gate. **The chain accurately reflects the 2026-07-31/08-01
rulings with zero introduced contradictions**, and **100% of the PRD's 60 FRs
trace to a real story**. Epics 4 and 6 (this week's additions) are cleanly
implementable now. Epics 2 and 3 are readable and consistent but each carry
named open design questions (F-2/3/4/5/6) that must be answered — not
merely acknowledged — at specific stories before those stories ship. This is
not a blanket gate; it is READY to keep moving, with four named decisions to
make before the next two epics reach implementation.

---

**Assessor:** bmad-check-implementation-readiness (autonomous re-run)
**Date:** 2026-08-01
**Supersedes:** nothing — this is additive to `implementation-readiness-report.md`
(the 2026-07-25 gate + its 2026-08-01 addendum), which remains the record of
the original BLOCKED-ON verdict and F-1's resolution.

Implementation Readiness complete.
