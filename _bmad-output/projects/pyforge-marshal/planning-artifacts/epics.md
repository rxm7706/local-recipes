---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/prd.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/product-brief-pyforge-marshal.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/research/market-agent-orchestration-research-2026-07-25.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/research/domain-agent-portability-and-governance-research-2026-07-25.md"
project_name: pyforge-marshal
epicCount: 48  # 2026-09-18: Epic 50 appended; 48 epic keys in the ledger (48/49 reserved holes). Prior 2026-09-14 (later): Epic 42 decomposes spec-surface-overlap-tolerance, promoted draft->ready the same day once its single open question was answered against chain.py. Prior note: 2026-09-14: retroactive Epics 37-41 minted for five `shipped` Specs that had no epic at all (chain-completeness's new delivered-Spec arm). The 33 here was already stale by three — Epics 34/35/36 never bumped it. This numeral is a dated snapshot; the ledger key count is the enumeration.
storyCount: 300  # 2026-09-18: +5 for Epic 50 (ledger key count, measured with fleet_scan.parse_sprint_status). Prior 2026-09-14 (later): +2 for Epic 42. Prior note: 2026-09-14: 229 live + 21 stories across retroactive Epics 37-41. The 227 here was already stale — Epics 34-36's stories never bumped it. This numeral is a dated snapshot; the ledger key count is the enumeration.
updated: "2026-09-20"   # RE-STAMPED 2026-09-20: fleet consistency pass (story-spec status ↔ ledger, reconstructed run results, epic roll-ups); § Currency reconciliation — 2026-09-20 (fleet consistency pass) appended. Prior 2026-09-20   # Epic 50 appended (spec-pyforge-marshal CAP-244..248, the landing self-drives; 48/49 reserved holes). Prior 2026-09-15: Epic 45 appended (spec-bmad-cursor-interactive-routing CAP-1 closed / CAP-2..4 decompose). Prior 2026-09-14: Epic 43 / Story 43.1; retroactive Epics 37-41; prior stamp 2026-09-09
status: complete
mode: headless
# The single canonical story source for this station: every `### Story` heading here maps
# 1:1 to a sprint-status-ledger.yaml story key. Exactly one `canonical` per station (AD-72).
epics_role: canonical
---

# pyforge-marshal — Epic Breakdown

## Overview

Decomposition of Marshal's PRD (58 FRs / 14 NFRs across 8 features) and architecture spine (39 ADs, hexagonal with an out-of-process supervisor sidecar) into **6 epics and 40 stories**.

Epics are organized by **user value**, not by architectural layer: each one leaves the operator able to do something they could not do before, and none requires a later epic to function. The critical-path story is **S-1.1** (package spine, verdict lattice, findings registry, and the meta-tests that enforce AD-3/AD-4) — every other story's compliance is checked by machinery it establishes.

Effort scale: **XS** (≤4 h), **S** (½–1 day), **M** (1–3 days), **L** (3–5 days). Story IDs are `S-<epic>.<seq>`.

Two conventions carried from the sibling builds:
- Every story declares its **surface** (the files it may touch); the gate intersects that with the epic's policy surface (AD-27).
- Every merged story's spec is promoted into `planning-artifacts/specs/` — from Epic 4 onward Marshal does this itself (FR-30); before that it is a manual step.

---

## Fold provenance (2026-09-16)

Station Spec spec-pyforge-marshal reminted absorbed capabilities as CAP-1..243. Historical stories keep their original epic numbers; this heading is the INV-A citation window for the folded set.

---

## Requirements Inventory

### Functional Requirements

**Loop homes & isolation** — FR-1 provision a loop home · FR-2 per-worktree active-project state · FR-3 single-sourced Tier-3 store · FR-4 isolation verification · FR-5 preflight · FR-6 teardown · FR-7 adapter config seeding · FR-8 enumerate loop homes

**Run supervision** — FR-9 detached launch · FR-10 scoped launch · FR-11 supervisor attaches · FR-12 idle-strand detection · FR-13 budget ceilings · FR-14 heaviest-story advisory · FR-15 escalation surfacing · FR-16 deferral capture · FR-17 resume · FR-18 run journal · *(added 2026-08-01)* FR-61 bounded-loss durability

**Gates & verification** — FR-19 standalone gate evaluation · FR-20 project-scoped verify commands · FR-21 deterministic no-LLM gates · FR-22 frozen-surface scope check · FR-23 doc-only classification · FR-24 gate mode ladder · FR-25 gate evidence record · FR-26 never false-green · FR-27 review-cap landing path · *(added 2026-08-01)* FR-64 gate binds to the spec's Success signal

**Landing & paper trail** — FR-28 batch pull request · FR-29 repository-hygiene preflight · FR-30 automatic story-spec promotion · FR-31 spec-recovery assistance · FR-32 merge-subject conformance · FR-33 sprint & console feed refresh · FR-34 deploy idempotence · FR-35 no AI attribution · *(added 2026-08-01)* FR-59 landing rules as policy · FR-60 `marshal land` · FR-63 fleet-wide branch retirement

**Fleet visibility** — FR-36 fleet view · FR-37 per-run detail · FR-38 escalation queue · FR-39 ledger-vs-git reconciliation · FR-40 stable machine-readable status contract · *(added 2026-08-01)* FR-62 durability as a reported fleet property · FR-65 `marshal check` — the detector registry, context resolved once

**Adapter portability** — FR-41 skill-tree projection · FR-42 projection drift detection · FR-43 adapter probe · FR-44 conformance smoke · FR-45 conformance matrix · FR-46 entry-file family drift check · FR-47 first-run acknowledgement · FR-48 project-scoped adapter selection

**Policy composition** — FR-49 layered composition · FR-50 project-scoped policy · FR-51 per-story model tiering · FR-52 single harness seam · FR-53 policy validation · FR-54 inspectable configuration

**Packaging & distribution** — FR-55 package identity & layout · FR-56 conda and wheel artifacts · FR-57 version & capability reporting · FR-58 upstream contribution register

### Non-Functional Requirements

NFR-1 determinism · NFR-2 offline by default · NFR-3 never false-green · NFR-4 supervisor independence · NFR-5 structural over conversational governance · NFR-6 no destructive default · NFR-7 idempotence · NFR-8 durable self-owned evidence · NFR-9 harness contract tests · NFR-10 lean dependencies · NFR-11 secret hygiene · NFR-12 machine-readable everything · NFR-13 platform targets · NFR-14 performance envelope

### Additional Requirements (architecture-originated)

The reviewer gate on the architecture spine surfaced seven critical divergence classes that became ADs after the PRD was written. They are requirements in their own right and are traced in the coverage map below: **AD-25** Marshal-owned run identity · **AD-26** accumulating state has one producer · **AD-27** allowlists narrow only · **AD-28** addressable journal entries and AD-6×AD-21 precedence · **AD-29** promotion durability · **AD-30** serialized append protocol · **AD-31** closed lattice with owned admission criteria · **AD-32** session data is evidence not control · **AD-33** truth partitioned by domain · **AD-34** redaction at egress ports · **AD-35** write-once materialized policy · **AD-36** declared projection mechanism · **AD-37** machine-scoped write target · **AD-38** feed reports completeness · **AD-39** envelope field relationships.

### UX Design Requirements

None — Marshal is a CLI with no visual surface. Its "UX" is the envelope contract (AD-14, AD-39) and finding codes (AD-15): every human view is a pure projection of machine-readable output, so there is no human-only information and no separate UX artifact.

### FR Coverage Map

| Epic | FRs covered | NFRs / ADs primarily discharged |
|---|---|---|
| **E1** Provisioned, verified loop homes | FR-1..FR-8, FR-49..FR-57 | NFR-1, 7, 10, 12, 13, 14; AD-3, 4, 7, 10, 11, 14, 15, 16, 21, 23, 24, 31, 35, 38, 39 |
| **E2** Gates you can run | FR-19..FR-27 (FR-27 partial), FR-64 | NFR-3, 5, 11; AD-8, 17, 26 (seed), 27, 34, 49 |
| **E3** Supervised unattended runs | FR-9..FR-18, FR-61 | NFR-4, 6, 8, 9; AD-5, 6, 9, 20, 22, 25, 26, 28, 30, 32, 46 |
| **E4** Landing with a durable paper trail | FR-27 (completion), FR-28..FR-35, FR-59, FR-60, FR-63 | NFR-6, 8; AD-12, 13, 21, 24, 28, 29, 33, 40, 42, 47 |
| **E5** Fleet visibility | FR-36..FR-40, FR-62, FR-65 | NFR-12; AD-5, 33, 39, 48, 50 |
| **E6** Portability proven | FR-41..FR-48, FR-58 | NFR-2, 9; AD-19, 31, 34, 36, 37 |

Every FR-1..FR-65 appears exactly once as a primary owner. FR-27 spans E2 (the gate re-run) and E4 (the landing), noted explicitly in both.

---

## Epic List

| Epic | Title | User value delivered | Stories | Effort |
|---|---|---|---|---|
| **E1** | Provisioned, verified loop homes | The operator can create an isolated, policy-composed, preflight-verified place for a loop to run — and prove two of them are isolated | 12 | ~15 days |
| **E2** | Gates you can run | The operator or CI can evaluate the gate standalone and get a verdict that never false-greens | 8 | ~9 days |
| **E3** | Supervised unattended runs | The operator can launch a gated run detached and have it watched — idle strands caught, budgets enforced, escalations surfaced | 13 | ~14 days |
| **E4** | Landing with a durable paper trail | The operator can land a wave and have every merged story's spec survive teardown, automatically | 15 | ~10 days |
| **E5** | Fleet visibility | The operator can see every loop home at once and be told where the ledger and git disagree | 10 | ~5 days |
| **E6** | Portability proven | The operator can run the method on another agent and hold a dated artifact proving it | 9 | ~12 days |
| **E7** | Foundation & the write guard | The seed installer has its module tree, an error taxonomy, and a write primitive nothing can route around | 6 | ~7 days |
| **E8** | The managed-region engine | A team's own file can carry a tool-owned span that upgrades without touching the rest | 5 | ~8 days |
| **E9** | Detect & plan | An operator can see exactly what would change before anything is written | 6 | ~9 days |
| **E10** | Materialize & the core verbs | `marshal seed check` / `adopt` / `init` work, each the previous plus one capability | 7 | ~12 days |
| **E11** | Derive, migrate & update | An installed repo takes a later model version with no hand edits | 6 | ~10 days |
| **E12** | Packaging, oracle & hardening | The installer ships, runs offline, and proves it never writes where it must not | 6 | ~8 days |
| **E13** | Surface drift reconciliation | The spec-surface gate can be cleared honestly, one spec at a time, and its signal trusted | 7 | (shipped) |
| **E14** | The shared floor — pyforge-core | Five primitives written 3-20× become one enforced leaf; 14.1/14.2 gate seed 7.2/7.3 | 4 | (new 2026-08-10) |
| **E15** | Fleet operations run themselves | Loop-home refresh + landing-promotes-ledger stop being hand rituals | 2 | (new 2026-08-10) |
| **E16** | The board derives truth | One slug resolver, derived sources, loud failures | 1 | (new 2026-08-10) |
| **E17** | Instruments verified, chains regenerable | Detector blind spots pinned; chain regeneration one invocation | 4 | (new 2026-08-10) |
| **E18** | The governed tool surface | Marshal's capabilities as typed tools; parity/coverage gated | 2 | (new 2026-08-10) |
| **E19** | The testing charter, enforced | One TEA generator, shared kit, coverage gates | 3 | (new 2026-08-10) |
| **E20** | The loop cannot lose work, and a landing is always recognizable | The operator can trust that a stranded attempt is preserved and loud, a scope drift refuses instead of passing, and every classifier agrees a landed story landed | 10 | (new 2026-08-14) |
| **E21** | The planning chain regenerates itself, and audits whether it's coherent | Chain regeneration becomes one invocation; a coherence verdict reaches the fleet board | 5 | (new 2026-08-15; row added 2026-08-21 — it was missing from this table) |
| **E22** | Single-story dispatch is a marshal verb | The 22-story hand ritual replays as governed machinery: one isolated session per story, judged from git facts, independently verified, landed with the full paper trail | 7 | (new 2026-08-21; 22.7 added 2026-08-27) |
| **E23** | Velocity captures hand-driven work | Every done story with real signal shows a timing mark; wall-clock never masquerades as active-compute | 3 | (new 2026-08-21) |
| **E24** | Liveness is one command | "Is this run alive?" answered by the supported CLI — never by hand-parsing engine.pid | 3 | (new 2026-08-21) |
| **E25** | Aligned to the installed BMAD era | Artifacts, patterns, and marshal surfaces match 6.11/0.11 — retired IDs purged and guarded, every spec folder tool-updatable, the new policy knobs governed and run states named | 7 | (new 2026-08-22) |
| **E29** | Done-spec dispatch does not review-loop | A `done` story cannot spawn confirmatory review commits or another harness session; land or escalate | 2 | (new 2026-09-02; CAP-11) |
| **E33** | Token economy in effect | Every capability marshal has already built is switched on and measured: the loop actually reads less, the review actually runs lighter, the model floor actually rises, a wave actually runs, and run state actually reaches the front door | 10 | (new 2026-09-09; `sprint-change-proposal-2026-09-09-token-economy-enablement.md`) |
| **Total** | | | **162** | **~119 days ≈ 24 weeks single-builder (E1-E12 figure; see note)** |

*Table gap recorded 2026-09-09 (not fixed by this pass): this table stops at **E25**, jumps to **E29**, and now carries **E33** — **E26, E27, E28, E30, E31 and E32 have no row**, though all six exist below with full story bodies and ledger keys. The `### Story` headings and `sprint-status-ledger.yaml` remain the enumeration of record (227 each after Epic 33); this table is a stale summary, and re-deriving it is its own cleanup.*

*Story counts re-verified 2026-08-10 (FR-128..163 decomposition): headings and
`sprint-status-ledger.yaml` story keys agree at **119** (E1-E6 = 60, E7-E12 = 36, E13 = 7,
E14-E19 = 16). The 2026-08-08 note claiming "all three agree at 86" was false when written —
E1/E3/E4/E5 counts and the E13 row were stale in this table while the headings and ledger
already carried the larger truth. **Effort is NOT re-estimated**; E1-E6 figures
still reflect the original per-epic scope and E7-E12 carry the installer's own estimates.
Treat the day figures as understated pending a full re-estimate. **Story 5.8 added
2026-08-11** (FR-181, queued via the Dream/Spec chain, not yet in
`sprint-status-ledger.yaml` — that file is generated by `sprint-ledger-sync` and was
deliberately left untouched by this addition) brought E1-E6 to 61 and the total to 120.
**Stories 3.11-3.13 added 2026-08-11** (FR-182/183/184, queued via the same Dream/Spec chain —
`docs/dreams/adaptive-model-tiering.md` and `docs/dreams/horizontal-run-concurrency.md` — same
"not yet in `sprint-status-ledger.yaml`" caveat) brought E1-E6 to 64 and the total to 123.
**Stories 2.8 and 5.9 added 2026-08-11** (FR-185 review-depth tiering, FR-186 quick-dev
ledger reconciliation — same Dream/Spec-chain convention, same deliberate exclusion from
`sprint-status-ledger.yaml` pending its next sync) bring E2 to 8, E5 to 9, E1-E6 to 65, and
the total to 125. **Story 5.10 added 2026-08-12** (FR-187, `marshal land` detectable-merge-subject
fix, sourced from `spec-marshal-land-merge-subject` — discovered during Story 5.9's own review,
backlog, not a prerequisite for it — same deliberate exclusion from `sprint-status-ledger.yaml`
pending its next sync) brings E5 to 10, E1-E6 to 66, and the total to **126**; the ledger will
re-agree on its next sync. **Epic 20 (Stories 20.1-20.10) added 2026-08-14** (FR-188..FR-191,
decomposing `spec-bmad-loop-baseline-drift`, `spec-bmad-loop-intent-gap-work-preservation`,
`spec-bmad-switch-scope-enforcement`, and `spec-landing-evidence-grammar` — same Dream/Spec-chain
convention, same deliberate exclusion from `sprint-status-ledger.yaml` pending its next sync)
brings the total to **136**. **Epics 22–24 (Stories 22.1–22.6, 23.1–23.3, 24.1–24.3) added
2026-08-21** (FR-193/FR-194/FR-195, decomposing `spec-marshal-single-story-dispatch`,
`spec-dashboard-velocity-captures-hand-driven-work`, and `spec-bmad-loop-liveness-footgun` —
same Dream/Spec-chain convention). Unlike earlier additions, the Tier-3 feed and tracked
ledger were synced in the SAME pass, and this table's Total is re-verified against the
ledger's post-sync story-key count (**155**) rather than the running arithmetic above —
which had drifted twice more since 2026-08-14 (the E21 row was missing from this table
entirely, and post-2026-08-14 story additions such as 10.8 were never folded into the
Total). The numeral rots; the ledger's key count is the enumeration. **Story 22.7 added
2026-08-27** (FR-193 CAP-7 fleet drain — the one CAP the 2026-08-21 decomposition left
uncovered; tracked ledger synced in the same pass, key count now **166**). **Epic 28
(Stories 28.1–28.9) added 2026-08-30** (decomposing `spec-marshal-token-economy`, Dream
`docs/dreams/marshal-token-economy.md` — same Dream/Spec-chain convention, citing the spec's
own CAP-1..CAP-10 rather than minting PRD FRs, per the Epic 26/27 external-spec-cite
precedent; Tier-3 feed and tracked ledger synced in the same pass — the sync's own
`--repair-feed` also restored 5 keys the Tier-3 feed had lost vs the twin (20.11, 22.7–22.10),
so the post-sync ledger-verified story-key count is **179**, matching the heading count; the
2026-08-27 numeral of 166 had already rotted by four before this pass, proving its own point).*

**Epics 7-12 were a separate document until 2026-08-08** (`epics-genesis-installer.md`, now
archived). They were always Marshal's own — the installer's buildable half moved here on
2026-07-28 — but lived in a second file feeding the same ledger, which is the one
inconsistency `epics_role: canonical` now makes impossible to reintroduce silently (AD-72).

**Standalone-ness check.** E1 ships a usable `marshal init` / `config` / `status --homes` with no later epic. E2 ships `marshal gate evaluate` usable by a human or CI with no run in flight. E3 needs E1 and E2 and nothing later. E4 needs E1–E3. E5 needs E3's journal. E6 needs E1 only. No epic requires a later epic to function.

---

## Epic 1: Provisioned, verified loop homes

**Goal:** the operator can stand up an isolated loop home for any project in one idempotent command — with policy composed and inspectable, adapter configs seeded, preflight run, and isolation from every other home provable. Establishes the package spine, the verdict lattice, the findings registry, and the meta-tests that police every later story.

**Critical path: nothing else can be built until S-1.1 lands.**

### Story 1.1: Package spine, verdict lattice, findings registry, and the meta-tests that enforce them

As the Marshal builder,
I want a clean package skeleton whose architectural invariants are machine-enforced from the first commit,
So that every later story is checked by machinery rather than by memory.

**Type:** foundation • **Effort:** M • **Deps:** none • **FR/AD:** FR-55, FR-57, NFR-1, NFR-10, NFR-12; AD-3, AD-4, AD-7, AD-14, AD-15, AD-31, AD-39
**Surface:** `src/shared/packages/pyforge-marshal/**`, root `pixi.toml` (dependency additions only)

**Acceptance Criteria:**

**Given** a clean environment
**When** the package is installed from the repo
**Then** `import pyforge.marshal` succeeds and `marshal --help` and `marshal --version` run
**And** the tree matches the architecture's Structural Seed (`cli/`, `core/`, `ports/`, `adapters/`, `supervisor/`, `schemas/`, `tests/{unit,contract,meta,integration}`), with `pyproject.toml` **and** a member `pixi.toml` per sibling convention
**And** `core/verdict.py` owns the lattice `error > gate-failed > scope-violation > unevaluable > warn > clean`, its exit-code projection, and a total `classify(finding_code) -> lattice_member`; no other module constructs an exit code (AD-7, AD-31)
**And** `core/findings.py` holds a registry of `MRS-<AREA>-<NNN>` codes; emitting an unregistered code fails a test (AD-15)
**And** the envelope `{schema_version, command, status, verdict, data, data_version, findings[], assumptions[]}` is emitted by every command, `status` is derived from `verdict`, and `schema_version` governs envelope keys only while `data_version` comes from a per-command registry (AD-14, AD-39)
**And** `tests/meta` fails the build when: any module outside `adapters/harness_bmadloop.py` references the harness (AD-3, via an import-linter contract with import-linter provisioned in `pixi.toml`); `core/**` imports `subprocess`, `os`, `time`, or `adapters` (AD-4); an exit code is constructed outside `core/verdict.py` (AD-7); or `status`/`verdict`/max-finding-severity are mutually inconsistent (AD-39)
**And** Marshal declares PyYAML, tomlkit, psutil and jsonschema as its **own** direct dependencies rather than inheriting them from the harness, with tomlkit capped `<0.13.3` per the environment

### Story 1.2: Story identity, merge-subject rendering, and feed completeness

As the Marshal builder,
I want one owner for story keys and the merge-subject string,
So that the loop, the journal, the spec archive, the merge subject and the dashboard can never key stories differently.

**Type:** foundation • **Effort:** S • **Deps:** S-1.1 • **FR/AD:** FR-32 (render/parse half), NFR-12; AD-23, AD-24, AD-38
**Surface:** `core/identity.py`, `tests/unit/test_identity.py`

**Acceptance Criteria:**

**Given** any external story reference (feed key, filename slug, branch segment, merge subject)
**When** `core.identity.normalize()` is called
**Then** it returns the canonical key `<epic>.<seq>` with an optional ordered suffix preserved and normalized (AD-38)
**And** one render function exists per external form; no module string-formats a story key inline (asserted by a meta-test)
**And** non-conforming input produces a registered finding, never a silent coercion
**And** resolving a set of story references reports `resolved N of M`, and **`N < M` produces a non-zero verdict naming every unresolved key** — a silently shortened feed is impossible (AD-38)
**And** the merge-subject template is rendered and parsed by the same module, and a round-trip property test proves `parse(render(k)) == k` for every key shape

### Story 1.3: Layered policy composition with provenance and validation

As the operator,
I want to see the effective run policy and where each value came from,
So that project-specific configuration never requires hand-editing a shared file.

**Type:** feature • **Effort:** M • **Deps:** S-1.1 • **FR/AD:** FR-49, FR-50, FR-53, FR-54; AD-10, AD-16, AD-26, AD-35
**Surface:** `core/policy.py`, `cli/config.py`, `schemas/policy.json`, `tests/unit/test_policy.py`

**Acceptance Criteria:**

**Given** Marshal defaults, a project policy layer, and invocation flags
**When** composition runs
**Then** precedence is defaults → project → flags, last wins, with no fourth layer and no per-key reordering (AD-16)
**And** the result is an immutable `EffectivePolicy` value; composition is pure and the same inputs produce the same output (AD-10)
**And** every field carries its winning layer and raw source value, and `marshal config` prints key, effective value, and winning layer, with secrets redacted
**And** **every field is tagged `static` or `seed`**; reading a `seed` field (frozen surfaces, gate mode, attempt counts) outside the journal fold fails a meta-test (AD-26) — **except through `EffectivePolicy.seed_view()`**, the display/validation accessor the meta-test whitelists, which is what lets this story's own `marshal config` AC and FR-53's preflight validation range over every key without contradiction (F-8)
**And** the worktree-seed path list is **generated from the active project**, never literal — switching projects requires no edit to any shared file (FR-50)
**And** unknown keys, unresolvable commands, and out-of-range values are rejected with a registered finding naming the layer that introduced them
**And** the materialized artifact is named by its content hash and never overwritten (AD-35)

### Story 1.10: Render the harness policy from the canonical EffectivePolicy

As the operator,
I want Marshal to **render** `.bmad-loop/policy.toml` from the composed policy rather than anyone hand-editing it,
So that per-project and per-tier settings reach the harness without a shared tracked file bleeding one project's config onto every other.

**Type:** feature • **Effort:** M • **Deps:** S-1.3 • **FR/AD:** FR-49, FR-50, FR-51; AD-10, AD-12, AD-35
**Surface:** `adapters/harness_bmadloop.py`, `tests/unit/test_harness_policy_render.py`, `tests/meta/test_rendered_policy_untracked.py`, `.gitignore`

> **Added 2026-07-25 to close F-1 (CRITICAL).** The review found the composed policy had **no path to the harness at all**: `bmad-loop 0.9.0` hard-codes `POLICY_FILE = .bmad-loop/policy.toml` with no policy-path flag, that file is git-tracked, AD-10 forbade Marshal editing it, and FR-51's tier-batching required exactly that edit. A grep of this file for `policy.toml` returned nothing — S-1.3 materializes an `EffectivePolicy` that nothing conveys to the engine it is composed for.

**Acceptance Criteria:**

**Given** a materialized `EffectivePolicy` (S-1.3) and a loop home
**When** the harness adapter renders
**Then** `.bmad-loop/policy.toml` is written **whole** from that policy — never patched, never merged with an existing file — and is byte-identical for identical input (AD-12 derived-artifact discipline)
**And** the canonical artifact stays content-addressed and write-once; only this projection carries the harness's fixed name (AD-35)

**Given** FR-51 tier-batching
**When** stories are batched by model tier
**Then** each batch renders its own `[adapter.dev].model` — automating the hand-edited `HARD-STORY BATCH PROCEDURE` block that FR-51 cites as its motivating evidence, with no human edit of a shared file

**Given** the rendered file
**When** the repository is inspected
**Then** `.bmad-loop/policy.toml` is **untracked** (`.gitignore`d) and a meta-test asserts `git ls-files` does not list it
**And** a loop home's `git push origin HEAD:main` cannot carry it — closing the live cross-project bleed observed at review time, where `loop-pyforge-herald` held 17+/27− of herald-specific policy on a tracked file shared with every project

**Given** a repo-wide default (e.g. the standing independent-review trigger)
**When** it is changed
**Then** it is expressed in the **tracked canonical policy source**, never by editing the rendered file — and the change reaches every project through re-rendering

> **SEQUENCING (hard).** Untracking must not precede rendering. Until this story lands, `.bmad-loop/policy.toml` stays tracked, because a fresh loop home cloned without it would leave `bmad-loop` with no policy at all. `git rm --cached` is the **last** step of this story, not a preparatory one.

### Story 1.4: Provision a loop home

As the operator,
I want one idempotent command that creates an isolated worktree on `loop/<slug>` with its own active-project state,
So that starting work on a project is a single verified action.

**Type:** feature • **Effort:** M • **Deps:** S-1.1, S-1.3 • **FR/AD:** FR-1, FR-2; NFR-7; AD-11, AD-21
**Surface:** `cli/init.py`, `adapters/vcs_git.py`, `adapters/fs_local.py`, `ports/vcs.py`, `ports/fs.py`

**Acceptance Criteria:**

**Given** a project slug with no existing loop home
**When** `marshal init <slug>` runs
**Then** a git worktree exists at the conventional sibling path on branch `loop/<slug>`
**And** the home carries its own active-project marker and planning-artifact symlinks, independent of every other home and of the main checkout
**And** the marker and the planning symlinks always agree; disagreement is a blocking registered finding, never silently tolerated
**And** the command prints a directly runnable launch line exporting `BMAD_ACTIVE_PROJECT`
**And** re-running against an existing home reports each step `done | skipped | failed`, changes nothing, and exits 0 (AD-21, NFR-7)
**And** Marshal writes only inside the home, the canonical Tier-3 store, declared promotion targets, and the machine-scoped path — a test asserts no write outside those four (AD-11)
**And** `main` is never checked out in a second tree

### Story 1.5: Single-sourced Tier-3 store via backlink

As the operator,
I want a loop home's execution artifacts to resolve to one canonical store,
So that every consumer sees the same path and no migration is ever needed.

**Type:** feature • **Effort:** S • **Deps:** S-1.4 • **FR/AD:** FR-3; AD-11
**Surface:** `cli/init.py`, `adapters/fs_local.py`

**Acceptance Criteria:**

**Given** a fresh loop home where the gitignored Tier-3 target does not exist
**When** provisioning runs
**Then** the home's `implementation-artifacts` realpath equals the main checkout's canonical directory
**And** the canonical directory is created if absent
**And** a **real, non-empty local directory is never replaced** — the command refuses with a registered finding naming the path
**And** the main checkout's own marker and symlinks are unchanged

### Story 1.6: Isolation verification and home enumeration

As the operator,
I want to prove that my loop homes are genuinely isolated,
So that running many projects at once is a checked property rather than a hope.

**Type:** feature • **Effort:** S • **Deps:** S-1.4, S-1.5 • **FR/AD:** FR-4, FR-8
**Surface:** `cli/init.py`, `core/status.py` (homes view only)

**Acceptance Criteria:**

**Given** two or more provisioned loop homes
**When** isolation verification runs across them
**Then** it exits 0 when markers and planning symlinks are independent, Tier-3 realpaths are identical, and the main checkout's active project is untouched
**And** it exits non-zero with a registered finding naming the specific cross-talk on any violation
**And** it accepts **N ≥ 2** homes in one invocation
**And** enumeration lists one row per home — path, branch, active project, desync flag — in both human and envelope form

### Story 1.7: Preflight, adapter config seeding, and first-run acknowledgement

As the operator,
I want to be told a run cannot start *before* I launch it,
So that I never discover a missing prerequisite at minute 90.

**Type:** feature • **Effort:** M • **Deps:** S-1.3, S-1.4 • **FR/AD:** FR-5, FR-7, FR-47; AD-19
**Surface:** `cli/init.py`, `adapters/harness_bmadloop.py`, `ports/harness.py`

**Acceptance Criteria:**

**Given** a provisioned loop home
**When** preflight runs
**Then** it reports harness presence and version, multiplexer backend availability, adapter binary presence, story-feed resolvability and parseability, verify-command resolvability, and that `main` is not checked out twice
**And** each configured adapter's declared seed files are present in the home afterwards, sourced from the harness profile and composed policy — **not** from a hard-coded list (AD-19, FR-7)
**And** each adapter's declared first-run requirement is surfaced as an explicit required human action, and an unacknowledged adapter is a **blocking** finding — because an unanswered first-run dialog is indistinguishable from a session timeout (FR-47)
**And** a sustained-automation caveat is presented once per adapter and the acknowledgement recorded
**And** any blocking finding exits non-zero and names itself; policy validation (S-1.3) runs as part of preflight
**And** preflight completes in under 10 seconds on a warm checkout (NFR-14)

### Story 1.8: Teardown that refuses to destroy work

As the operator,
I want teardown to remove a loop home cleanly and refuse when work would be lost,
So that cleanup is never the thing that costs me a wave.

**Type:** feature • **Effort:** S • **Deps:** S-1.4 • **FR/AD:** FR-6; NFR-6; AD-29 (hook)
**Surface:** `cli/init.py`, `adapters/vcs_git.py`

**Acceptance Criteria:**

**Given** a provisioned loop home
**When** teardown runs
**Then** the worktree and branch are removed and `git worktree list` is clean afterwards
**And** it **refuses** with a registered finding when the home has uncommitted or unmerged work, unless explicitly forced
**And** it never touches the canonical Tier-3 store
**And** a documented extension point exists for the promotion-reachability predicate that Epic 4 wires in (AD-29), and it is a no-op while no promotions exist
**And** no Marshal operation force-updates or force-pushes anything (NFR-6)

### Story 1.9: Packaging, distribution, and version reporting

As the operator,
I want one install command to yield Marshal and its harness together,
So that the wrap decision pays off at the point of use.

**Type:** infra • **Effort:** M • **Deps:** S-1.1 • **FR/AD:** FR-55, FR-56, FR-57; NFR-10, NFR-13; AD-2, AD-3
**Surface:** `src/shared/packages/pyforge-marshal/{pyproject.toml,pixi.toml}`, root `pixi.toml`

**Acceptance Criteria:**

**Given** the package source
**When** the conda artifact is built via pixi-build-python wrapping the hatchling wheel (the sibling path — neither sibling ships through `recipes/`)
**Then** installing it yields a working `marshal --help` with the harness resolvable
**And** the conda recipe declares `bmad-loop >=0.9.0,<0.10` as a **run dependency**, never vendored (AD-2)
**And** wheel and sdist build from the same source tree
**And** `marshal --version` reports Marshal's version **and** the resolved harness version, both of which appear in every run journal
**And** a harness outside the supported range emits a prominent warning, and a major mismatch is a blocking preflight finding
**And** build and smoke targets exist for linux-64 and osx-arm64; Windows is declared WSL-first rather than silently failing (NFR-13)

---

### Story 1.12: A stale loop home cannot be spun *(added 2026-08-09 — FR-180)*

As the operator,
I want preflight to refuse a loop home that is behind `main`,
So that a stale baseline cannot silently switch the surface guard off.

**Type:** feature • **Effort:** S • **Deps:** S-1.11 • **FR/AD:** FR-180

**Why preflight and not the landing.** FR-173 makes a landing leave the home current — but every
landing on 2026-08-09 was done by hand (`gh pr merge`), so that code never ran and eight homes
drifted 33–74 commits behind with nothing reporting it.

**Acceptance Criteria:**

**Given** a provisioned loop home whose HEAD is an ancestor of `origin/main`
**When** `marshal preflight <slug>` runs
**Then** it reports **`MRS-PREFLIGHT-014` at ERROR** and exits non-zero, naming both shas and
printing a remedy that is runnable exactly as shown
**And** a home whose HEAD equals `origin/main` is silent — otherwise every preflight reds and
the gate stops being read
**And** a home merely **AHEAD** (unlanded story merges — the ordinary mid-run state) is **not**
refused
**And** any probe failure yields no finding: a diagnostic must never become a refusal
**And** FR-173's landing resync is amended to **push** the station branch, since provisioning
reads origin and seven homes sat 33–74 commits behind there after their work had landed

### Story 1.11: A loop agent cannot mutate repo-wide git state *(added 2026-08-09 — FR-178)*

As the operator,
I want isolation to cover the shared git directory, not just the working tree,
So that one dev session cannot silently change what every other worktree can see.

**Type:** feature • **Effort:** S • **Deps:** S-1.6 • **FR/AD:** FR-178

**Why now.** Every loop home and per-story worktree resolves `--git-common-dir` to the same
`local-recipes/.git`. Measured 2026-08-09: `/.claude/skills` was re-added to
`.git/info/exclude` **three times**, most recently *while a run was live* — hiding new files
from `git status` and `git add -A` in every worktree simultaneously.

**Acceptance Criteria:**

**Given** a provisioned loop home
**When** `marshal preflight` (or `homes`) runs
**Then** a mutation of the **shared** git directory — `info/exclude` at minimum — is reported
against a recorded baseline, naming the rule and what it hides
**And** the report distinguishes shared-state mutation from ordinary worktree state: FR-8's
isolation check covers worktrees and branches and does **not** see this
**And** the filesystem-walking guard `test_skill_files_tracked.py` is left in place — it walks
the tree instead of asking git, so it is the only signal that survives the rule, and it is what
caught the third recurrence
**And** a test proves the detection on a fixture whose `info/exclude` carries a rule the tracked
tree would otherwise match

## Epic 2: Gates you can run

**Goal:** the gate stops being a configuration line inside somebody else's orchestrator and becomes a first-class object a human or CI can invoke. After this epic the operator can, at any moment, ask "would this pass?" and get a deterministic answer that can never be a false green.

### Story 2.1: Standalone verify-command runner, project-scoped

As the operator or CI,
I want to run this project's gates without a loop in flight,
So that I can check a tree before approving anything.

**Type:** feature • **Effort:** M • **Deps:** S-1.1, S-1.3 • **FR/AD:** FR-19, FR-20, FR-21; NFR-1, NFR-2; AD-4, AD-17, AD-26

> **F-3 resolution threaded in (2026-08-02, drift fix).** The adversarial review (`reviews/review-ad25-39-adversarial-2026-07-25.md`, `verdict: ALL-RESOLVED` 2026-07-30) resolved F-3 into AD-26's Resolution note, but that resolution had not been propagated into this story's own acceptance criteria — a developer reading only this story would not have known evaluation-with-no-run-in-flight folds the policy seed alone, not a run-scoped state. Added below; no other story or document changes.

**Surface:** `core/gate.py`, `cli/gate.py`, `ports/process.py`, `adapters/process_posix.py`

**Acceptance Criteria:**

**Given** a project with configured verify commands
**When** `marshal gate evaluate` runs with no run in flight
**Then** each command runs and pass/fail is reported per command with captured output
**And** verify commands resolve from composed policy scoped to the **active project** — another project's gates are never run (FR-20)
**And** evaluation **never mutates the working tree**
**And** no model call occurs anywhere in the path, and the same tree plus the same commands produce the same verdict (NFR-1, FR-21)
**And** verify commands are an explicit **allowlist**; anything not allowlisted is `unevaluable`, never permitted (AD-17)
**And** the aggregation logic lives in `core/gate.py` as a pure function over exit codes, with all process spawning behind `ProcessPort` (AD-4)
**And** with no run in flight, the evaluation folds **the policy seed alone** and says so: output carries an explicit `scope: policy-seed-only` marker and a `mid-run freezes not visible` note, so it is never mistaken for a run-scoped verdict (AD-26, F-3)
**And** when a run **is** in flight and its id is supplied, the same command folds that run's journal instead and answers the run-scoped question (AD-26, F-3)

### Story 2.2: Verdict aggregation that never false-greens

As the operator,
I want any check that cannot reach a definite pass to be a failure,
So that "could not determine" can never be read as "clean".

**Type:** feature • **Effort:** S • **Deps:** S-2.1 • **FR/AD:** FR-26; NFR-3; AD-8, AD-31
**Surface:** `core/gate.py`, `core/verdict.py`, `tests/unit/test_verdict.py`

**Acceptance Criteria:**

**Given** any combination of check outcomes
**When** the verdict is computed
**Then** it is the maximum over emitted findings' classifications plus the command-declared floor, and no module assigns a verdict directly (AD-31)
**And** a missing verify command, an unreadable spec, or a crashed check produces `unevaluable`, which projects to non-zero and blocks progression
**And** a property test asserts **there exists no input producing `clean` when any check is unevaluable** (AD-8)
**And** the lattice gains no new members
**And** exit codes come solely from `core/verdict.py`, with `130` on interrupt

### Story 2.3: Frozen-surface scope check, narrowing only

As the operator,
I want a story's changed files checked against both its declared surface and every frozen surface,
So that a producer story cannot silently amend a contract another story froze.

**Type:** feature • **Effort:** M • **Deps:** S-1.2, S-2.2, **S-3.2** • **FR/AD:** FR-22; NFR-3, NFR-5; AD-26, AD-27

> **Dependency corrected 2026-07-30 (F-9).** This story's own ACs require the frozen set to be "produced by the journal fold" — and the fold is **S-3.2, in the next epic**. As declared (`S-1.2, S-2.2`) the story was **not implementable in its position**: it depended on a component that did not yet exist. Adding `S-3.2` makes the graph honest. The alternative — moving the fold into Epic 2 — was rejected because S-3.2 also owns run-state derivation that Epic 3 needs, and splitting it would give the fold two homes. Epic 2 therefore completes after S-3.2 lands; the epic boundary is a value boundary, not a scheduling barrier.
**Surface:** `core/gate.py`, `core/policy.py` (seed accessor), `tests/unit/test_scope.py`

**Acceptance Criteria:**

**Given** a story spec declaring a surface, and a project policy declaring the epic's surface
**When** the scope check runs
**Then** the effective surface is computed as **`policy_surface ∩ spec_surface`**, and a meta-test asserts no other combinator is used (AD-27)
**And** a spec-declared path outside the policy surface is a hard finding — **a machine-drafted spec can only narrow, never widen, the allowlist it is judged against**
**And** a change to a frozen file is a hard failure naming the file **and the story that froze it**
**And** a change outside the effective surface is a failure naming every offending path
**And** the frozen set is produced by the journal fold over freeze declarations, with policy supplying only the **initial** set — reading the live set from `EffectivePolicy` fails a meta-test (AD-26)
**And** freeze declarations, freeze removals, and gate-mode changes are never sourced from an agent-writable artifact (AD-27)

### Story 2.4: Doc-only story classification

As the operator,
I want stories that legitimately produce no source change to pass,
So that a design-spike story does not trip a rollback loop.

**Type:** feature • **Effort:** S • **Deps:** S-2.2 • **FR/AD:** FR-23
**Surface:** `core/gate.py`

**Acceptance Criteria:**

**Given** a story whose declared deliverable is a document or decision record
**When** the gate evaluates a worktree with no source change
**Then** it does not fail on "no changes in worktree"
**And** classification is a pure function of the story's declaration, and is recorded in the run record
**And** a story **not** so classified that produces no change still fails, with a distinct registered finding
**And** a doc-only story that nonetheless touches a frozen surface still fails the scope check

### Story 2.5: Gate mode ladder with autonomy labels

As the operator,
I want the run's approval policy to be selectable and labelled with what autonomy level it represents,
So that the gate configuration is itself the autonomy declaration.

**Type:** feature • **Effort:** S • **Deps:** S-1.3, S-2.2 • **FR/AD:** FR-24; NFR-5
**Surface:** `core/policy.py`, `core/gate.py`, `cli/gate.py`

**Acceptance Criteria:**

**Given** a project policy
**When** a gate mode is selected
**Then** `per-story-spec-approval`, `per-epic` and `none` are supported
**And** each carries its explicit autonomy label — L2 Task-Based/Operator, L3 Conditional/Context Gates, L4 Approver respectively — surfaced at launch and in the run record
**And** the label mapping is data, not prose, and is emitted in the envelope
**And** changing gate mode is recorded as a decision entry with a timestamp and provenance, never applied silently
**And** the effective mode is read through the journal fold, not from policy directly (AD-26)

### Story 2.6: Gate evidence record with redaction at egress

As the operator,
I want every gate evaluation to leave a durable, redacted record,
So that I can prove months later what was checked and what it said.

**Type:** feature • **Effort:** M • **Deps:** S-2.2 • **FR/AD:** FR-25; NFR-8, NFR-11; AD-34
**Surface:** `core/egress.py`, `ports/*.py` (egress classification), `adapters/fs_local.py`, `schemas/gate-record.json`

**Acceptance Criteria:**

**Given** a completed gate evaluation
**When** the record is written
**Then** it captures commands run, exit codes, scope-check verdict, tree revision, and a UTC ISO-8601 timestamp
**And** the record is schema-validated and retrievable per story
**And** **every port that emits bytes outside the process is a declared egress port**, routed through the single redacting serializer in `core/egress.py`; egress ports accept only a `Redacted` payload type and a meta-test asserts none accepts a bare string (AD-34)
**And** the egress-port set lives in one code registry, and adding a port without classifying it fails the build
**And** redaction is tested against a fixture of known token shapes and covers policy-declared secret keys
**And** no call site performs its own redaction

---

### Story 2.7: A gate binds to the spec's Success signal *(added 2026-08-01 — FR-64 / AD-49)*

As the operator,
I want gate evaluation to confirm it is still running the verify commands the story's tracked spec named as its Success signal,
So that a test quietly removed after the spec was tracked shows up as a contract breach, not a passing suite.

**Type:** feature • **Effort:** S • **Deps:** S-2.1, S-4.1 • **FR/AD:** FR-64; AD-49, AD-26, AD-31
**Surface:** `core/gate.py`, `core/spec_binding.py`

**Acceptance Criteria:**

**Given** a story with a tracked `specs/spec-<key>.md`
**When** its gate is evaluated
**Then** the verify commands run are confirmed against the ones named in the spec's Success signal
**And** a narrowed or removed verify command since tracking is a registered finding, not a warning folded into an otherwise-green verdict
**Given** a story with no tracked spec to bind against
**When** its gate is evaluated
**Then** the missing binding is reported explicitly as a finding, never evaluated silently against nothing
**And** an untraceable or mismatched binding cannot be waived to green — it participates in the closed admission lattice (AD-31) like every other criterion

---

### Story 2.8: A low-risk story's review runs lighter, never absent *(added 2026-08-11 — FR-185)*

As the operator,
I want a story mechanically classified as low-risk to run review at reduced cost — fewer
cycles, or a cheaper pass — while the independent reviewer still runs on every story with no
exception,
So that an unattended run stops paying full review price for a change that is obviously
mechanical.

**Type:** feature • **Effort:** M • **Deps:** S-2.4 • **FR/AD:** FR-185

**Why now.** `gate_mode = "none"`'s own comment (cloned into all 9 loop homes) already draws
the line — human approval is skippable, the independent reviewer is not — but `max_dev_
attempts`/`max_review_cycles` are flat, repo-wide ceilings (`core/policy.py` `DEFAULT_
POLICY`), identical for a one-line doc fix and a cross-module rewrite. `classify_doc_only_
declaration` (Story 2.4, FR-23) already proves the idiom this needs — a pure function of a
story's own declaration plus an observed fact — but today it feeds only gate pass/fail for
the no-diff case, never review scheduling. Any mechanism reaching toward review depth has to
be checked against `DW-AD23-3` by name first: the upstream `max_followup_reviews` default of
`1` silently damped five real, reviewer-recommended follow-ups across three projects into a
gitignored ledger before the repo-wide value was raised to `2` with the incident documented
inline (`_bmad-output/policy-defaults.toml`). A tightened cap for a low-risk tier must not
reopen that hole.

**Acceptance Criteria:**

**Given** a story's own declaration and its observed diff shape
**When** the story is classified before review runs
**Then** classification is a pure function of already-gathered facts — no I/O, no model call,
no hidden state — mirroring `classify_doc_only_declaration`'s own shape
**And** the classification is recorded in the run record, never a silent choice
**Given** any classified story, regardless of tier
**When** review runs
**Then** the independent reviewer runs unconditionally — the `gate_mode = "none"` human
approval-only boundary is unchanged, and no tier ever causes review to be skipped
**Given** a story classified into a lower-risk tier
**When** its review cycles are bounded
**Then** it may run fewer cycles or a cheaper review pass than the repo-wide default, and a
higher-risk or unclassified story is never granted a *smaller* allowance than today's flat
ceiling
**Given** a reviewer-recommended follow-up on a story at ANY tier, including the lowest
**When** `deferred-work-check` runs
**Then** the follow-up is captured with the same completeness guarantee every tier already
gets — a test reproduces the `DW-AD23-3` shape (a follow-up surfaced under a tightened cap)
and proves it is captured, never silently dropped, for every defined tier
**And** `max_followup_reviews` (or an equivalent cap) is never lowered, for any tier, below
what `deferred-work-check` can still fully capture

---

## Epic 3: Supervised unattended runs

**Reopened 2026-08-09 for S-3.9 + S-3.10.** FR-61's stage-boundary push was verified WORKING in a live run; what failed was its *reporting* — a false `push-failed` on the success path, and a detector comparing branch names instead of tips. The guarantee holds; the claim about it did not.

**Goal:** the operator can launch a gated run and walk away. The supervisor — a separate process the session cannot disable — catches idle strands well before any token cap, enforces budgets over externally-observed quantities, surfaces escalations, and writes a durable journal that survives teardown.

### Story 3.1: Run identity and the journal writer

As the operator,
I want every run to have a Marshal-owned identity and an append-only journal written safely,
So that nine concurrent homes can share one store without braiding their histories together.

**Type:** foundation • **Effort:** M • **Deps:** S-1.1, S-1.5 • **FR/AD:** FR-18; NFR-8; AD-25, AD-28, AD-30
**Surface:** `core/journal.py`, `adapters/fs_local.py`, `schemas/journal.json`

**Acceptance Criteria:**

**Given** any run or session invocation
**When** the identifier is minted
**Then** Marshal mints it **at `intent` time, before any spawn** — globally unique, `<slug>-<utc-compact>-<random>`, sortable chronologically **within a slug** but not across the fleet; fleet-wide chronology sorts on `ts`, never on the id (AD-25)
**And** the harness's own identifier is recorded as `harness_run_id` on the first `outcome` entry and is **never** a key, a path segment, or a grouping field
**And** run directories are created with `mkdir`, which already fails `EEXIST`; a collision is a hard finding, never an append
**And** non-run invocations (standalone gate evaluation, adapter probe) mint into a separate `sessions/` namespace excluded from fleet folds **by construction, not by filtering**
**And** every entry carries `{id, ts, run_id, story?, kind, phase, intent_id?, payload}` where `id` is the composite **`(writer_id, counter)`** — monotonic within a writer, never across the run — and `phase ∈ intent | outcome | observation`, with `intent_id` mandatory on every `outcome` and absent on every `observation` (AD-28)
**And** each append is a single `os.write()` of one complete newline-terminated line on an `O_APPEND|O_CREAT` descriptor, `fsync`ed for `phase: intent`, with no buffered stream held open across appends (AD-30)
**And** payloads over 4 KiB go to a sidecar blob with a reference in the entry
**And** timestamps carry millisecond precision and total order is **`(ts, writer_id, counter)`** — a total order without cross-writer coordination, explicitly **not** a causal order; no consumer may infer causality from adjacency (AD-28)
**And** a concurrency test with a long-lived writer and repeated short-lived writers produces zero malformed lines **and zero duplicate `(writer_id, counter)` pairs** — the malformed-line assertion alone tests atomicity, not identity, and would pass while the id invariant was violated

### Story 3.2: The journal fold — one producer for accumulating run state

As the Marshal builder,
I want all run state derived from one fold over the journal,
So that no two components can disagree about what happened.

**Type:** foundation • **Effort:** M • **Deps:** S-3.1 • **FR/AD:** FR-18; AD-5, AD-26, AD-28, AD-30
**Surface:** `core/journal.py`, `tests/unit/test_fold.py`

**Acceptance Criteria:**

**Given** a journal
**When** the fold runs
**Then** it produces run state — story transitions, gate verdicts, escalations, deferrals, consumption, supervisor actions, frozen surfaces, attempt counts, effective gate mode
**And** these accumulating values have **exactly one producer**: this fold. Any module reading them from `EffectivePolicy` fails a meta-test (AD-26)
**And** `intent`/`outcome` pairing is by `intent_id` **only** — no positional or heuristic pairing exists anywhere (AD-28)
**And** an unparseable line is **quarantined**, surfaced as a registered finding, and makes **its own story key and decision domain `unevaluable`** — records provably unaffected stay evaluable; when the line's `story` or `kind` cannot be recovered the scope widens to the whole run, because unknown blast radius is not a reason to narrow it (AD-30)
**And** a reference to a **missing sidecar blob** is the same class and takes the same treatment — `unevaluable` for that record, never "quarantine and continue"
**And** the fold is a pure function over entries with no I/O (AD-4)
**And** a lone `intent` is reported as open, never inferred closed

### Story 3.3: Detached launch with scoped story selection

As the operator,
I want runs and resumes to detach by default,
So that a foreground timeout can never kill a run mid-review again.

**Type:** feature • **Effort:** M • **Deps:** S-1.7, S-3.1 • **FR/AD:** FR-9, FR-10, FR-52; AD-3, AD-22, AD-38
**Surface:** `cli/spin.py`, `adapters/harness_bmadloop.py`, `ports/harness.py`

**Acceptance Criteria:**

**Given** an approved spec and a provisioned home
**When** `marshal factory spin` runs
**Then** the harness process is detached from the invoking shell's session and lifetime, and the command returns promptly with the Marshal run id (AD-22)
**And** the run survives the caller exiting
**And** foreground execution exists only behind an explicit flag documented as unsafe for resumes, and **nothing in Marshal blocks on a run's completion**
**And** attaching to a live run's session is a separate, non-destructive command
**And** story, epic and max-count selectors are supported and composable
**And** the resolved story list is echoed before launch, recorded in the journal, and reports `resolved N of M` with a non-zero verdict when `N < M` (AD-38)
**And** **all** harness interaction goes through `adapters/harness_bmadloop.py`; the import-linter contract from S-1.1 proves it (FR-52, AD-3)

### Story 3.4: Supervisor process lifecycle

As the operator,
I want a watcher attached to every run that the run itself cannot switch off,
So that supervision is a property of the system, not of the agent's cooperation.

**Type:** feature • **Effort:** M • **Deps:** S-3.1, S-3.3 • **FR/AD:** FR-11; NFR-4, NFR-5; AD-9, AD-20
**Surface:** `supervisor/`, `ports/{process,clock,observer}.py`, `adapters/{process_posix,clock_system,observer_mux}.py`

**Acceptance Criteria:**

**Given** a run started by Marshal
**When** the supervisor attaches
**Then** it runs as a **separate OS process**, parented to neither the agent session nor the invoking shell (AD-9)
**And** it cannot be disabled, silenced, or reconfigured from inside the agent session — a test asserts no control channel exists from session to supervisor
**And** its inputs are externally observable only: multiplexer pane content, file modification times, process liveness, and adapter-written usage files
**And** supervisor liveness is itself journaled; a dead supervisor is a **reported** condition surfaced by `status`, never silence, and degrades the run to unsupervised rather than corrupt
**And** the supervisor is inert on a run it did not start
**And** its only write is the journal
**And** clock, process state and observations reach the decision core as **injected values** (AD-20)

### Story 3.5: Idle-strand detection

As the operator,
I want a session that stopped producing output but did not exit to be caught in minutes, not at a 4M-token cap,
So that the failure that cost three story attempts in one wave cannot recur.

**Type:** feature • **Effort:** L • **Deps:** S-3.4 • **FR/AD:** FR-12; NFR-4; AD-9, AD-20, AD-32
**Surface:** `core/supervise.py`, `supervisor/`, `tests/unit/test_supervise.py`

**Acceptance Criteria:**

**Given** a running session
**When** idleness is evaluated
**Then** it is measured from **observable session output** — pane content and log modification time — never from the agent's self-report
**And** the threshold is configurable with a default of 25 minutes, materially below the session budget
**And** fresh output re-arms the window
**And** on expiry the supervisor takes the configured ladder action — nudge, then stop-and-retry, then defer — with each step journaled `intent` then `outcome` and counted
**And** the decision is a **pure function over a sample sequence**, and every ladder behaviour has a test running in milliseconds against synthetic samples (AD-20)
**And** the supervisor's poll interval is never longer than the active prompt-cache TTL, defaulting to ≤60 seconds (NFR-14)

### Story 3.6: Budget ceilings and the heaviest-story advisory

As the operator,
I want a hard ceiling on every run and a warning before I launch something that will not fit,
So that there is no unbounded mode and no unrecoverable overnight burn.

**Type:** feature • **Effort:** M • **Deps:** S-3.5 • **FR/AD:** FR-13, FR-14; C-6; AD-8, AD-32
**Surface:** `core/supervise.py`, `cli/spin.py`

**Acceptance Criteria:**

**Given** configured per-story and per-run token and wall-clock ceilings
**When** a unit approaches or breaches one
**Then** approaching emits a warning and breaching stops the unit with a **named reason**, never a silent defer
**And** consumption is journaled per story with a cost estimate where the adapter reports one
**And** **every enforcement ceiling is expressed over at least one externally-observed quantity** (wall clock, process liveness, output mtime); session-written usage files are recorded for reporting and cost attribution only (AD-32)
**And** a usage sample older than the idle threshold is `unevaluable`: a registered finding is emitted and the **wall-clock ceiling becomes the binding constraint** — a wedged session's frozen counter can never defeat the ceiling
**And** no ceiling exists that can only be evaluated from session-written data
**And** preflight warns when a selected story is likely to exceed the session budget, comparing the budget against spec size, declared difficulty, and prior attempt history (FR-14)

### Story 3.7: Escalation, deferral, and resume

As the operator,
I want undecidable situations to pause the run and reach me, and resolved ones to resume safely,
So that the agent never guesses at something it cannot safely decide.

**Type:** feature • **Effort:** M • **Deps:** S-3.4, S-3.2 • **FR/AD:** FR-15, FR-16, FR-17; AD-22, AD-28
**Surface:** `core/supervise.py`, `cli/spin.py`, `ports/notify.py`, `adapters/notify_file_desktop.py`

**Acceptance Criteria:**

**Given** an escalation
**When** it is raised
**Then** the run pauses and **no story proceeds past an unresolved escalation**
**And** it is journaled with story key, reason, and the artifact needing a decision
**And** notification fires on at least a durable file marker; desktop notification is best-effort and its failure never blocks
**And** notification content is redacted at capture, before it enters the core, because pane-derived text routinely carries secrets (AD-34)
**Given** a story the loop could not land
**Then** the deferral records story key, reason class, attempt count, and where preserved work lives, and the run continues unless configured otherwise
**Given** a paused run whose blocking condition a human resolved
**When** resume runs
**Then** it is detached on the same terms as launch and re-attaches a supervisor
**And** resuming a run with an unresolved escalation is **refused** with a registered finding
**And** *(added 2026-08-01 — AD-45)* the resume journal entry records a **reference to the resolving decision or artifact**, ingestion-sufficient for the knowledge station's pull (story key, reason, resolution reference, resolver attribution)

---

### Story 3.8: Stage-bound durability, and fleet-launch wiring *(added 2026-08-01 — FR-61 / AD-46)*

As the operator,
I want the supervisor to push a run's work at its own stage boundaries rather than on a timer, with the fallback watcher on by default,
So that worst-case loss is bounded by the run's own structure, and nobody has to remember to start a durability watcher.

**Type:** feature • **Effort:** M • **Deps:** S-3.4, S-3.1 • **FR/AD:** FR-61; AD-46, AD-22, AD-25, AD-40
**Surface:** `supervisor/durability.py`, `core/supervise.py`, `cli/spin.py`

**Acceptance Criteria:**

**Given** a running story
**When** the dev commit lands, the review verdict is recorded, or the story merges
**Then** the supervisor pushes the affected station and per-story branches at that boundary, never on a wall-clock interval alone
**And** push is read-only against working trees and remotes — never a force-push, never a rewrite
**Given** a fleet launch
**When** it starts
**Then** the interval-push watcher (the floor for whatever the stage hooks miss) starts automatically, with no separate manual invocation required
**And** the watcher exits on its own when the fleet does

---

### Story 3.9: A retired story branch is not a push failure

As the operator,
I want the durability signal to stop reporting failure on its own success path,
So that a real durability alarm still means something when it fires.

**Type:** change • **Effort:** S • **Deps:** S-3.8 • **FR/AD:** FR-170; AD-46

**Added 2026-08-09**, reopening a `done` epic. Found by operating FR-61 in a live
9-story run, not by reading it: 6 of 22 `stage-push` records reported `push-failed`
on branches whose work was already safe.

**Acceptance Criteria:**

**Given** a `dev-commit-landed` or `story-merged` boundary whose per-story branch bmad-loop
has already deleted on merge
**When** the supervisor acts on that boundary
**Then** it does **not** attempt the push and does **not** register `MRS-SUPV-008`
**And** it proves the work landed — the story's `commit_sha` from `TaskPhaseSnapshot` is
reachable from the station branch — and journals a benign `retired-merged` outcome
**And** if that `commit_sha` is **not** reachable (or is unknown), a **distinct and louder**
finding is registered: a branch that vanished with unlanded work is real loss and must not
inherit the benign case's silence
**And** `GitVcs.push` is unchanged — raising on "no such branch" is correct, since falling
back would push to a target the caller never named; the defect is the caller asking for a
push it does not need
**And** a test proves both directions: a merged-and-deleted branch produces no finding, and a
deleted branch whose commit is unreachable from the station branch produces the loud one

### Story 3.10: Unpushed work is measured by tip, never by name

As the operator,
I want `unpushed-work-check` to compare tips rather than branch names,
So that a branch whose remote copy is stale stops reporting as safe.

**Type:** change • **Effort:** S • **Deps:** — • **FR/AD:** FR-171

**Added 2026-08-09.** `find_unpushed`'s `if br in remote: continue` asks *"does a remote copy
exist?"* while the detector presents itself as answering *"is the work safe?"*

**Acceptance Criteria:**

**Given** a local branch whose name exists on origin but whose remote tip is behind
**When** `unpushed-work-check` runs
**Then** it is reported as unpushed work, with the count of commits the remote lacks
**And** station branches (`loop/*`) are in scope — they are exactly the long-lived branches
whose name always exists remotely and whose tip silently falls behind between runs
**And** a branch whose remote tip matches, or which is an ancestor of the remote, is still
silent — the fix must not turn every branch into a finding
**And** a regression test replays the live case: `loop/pyforge-doctor` on origin at
`3f43f486c9` with the local branch 8 commits ahead reported clean under the name check, and
reports under the tip check

### Story 3.11: A story's declared difficulty actually picks its model *(added 2026-08-11 — FR-182)*

As the operator,
I want a project's declared model tiers and a story's declared difficulty to actually change
which model runs it,
So that FR-51's tiering mechanism stops being a fully-built, permanently-unused chain.

**Type:** feature • **Effort:** M • **Deps:** S-1.3, S-6.1 • **FR/AD:** FR-182; AD-19
**Surface:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`,
`cli/spin.py`, docs/skill surface for story authoring

**Why now.** Story 6.1 shipped `model_tier_map`'s full consumption chain — `core/spec_difficulty.py`,
`cli/spin.py::_story_declared_difficulty`/`_resolve_governing_difficulty`/`_resolve_model_tiering`,
and `render_policy_toml`'s tier-batching — but grep across every one of the 8 loop-home projects'
`marshal-policy.toml` and every story spec finds zero real `model_tier_map` entries and zero
declared `difficulty:` values. `pyforge-marshal`'s own policy file still carries the placeholder
comment written before Story 6.1 shipped ("Populate when FR-51 tier-batching lands") and was never
revisited once it did.

**Acceptance Criteria:**

**Given** a project's `marshal-policy.toml` declaring a real, non-empty `model_tier_map`
**When** an in-scope story declares a matching `difficulty:` value
**Then** the rendered `policy.toml` differs from the undeclared baseline in exactly the mapped
stages, and the resolution (difficulty, resolved per-stage models) is journaled at launch —
reusing `_resolve_model_tiering`'s existing echo, never a second mechanism
**And** a documented convention exists for how a story acquires a difficulty — authored or
derived — landing wherever stories are authored (the design choice itself is this story's own,
per the Spec's open question)
**And** `pyforge-marshal`'s own `marshal-policy.toml` carries a real `model_tier_map` in place of
the stale placeholder comment, and at least one real story declares a real difficulty end to end
**And** a mismatched or undeclared story within the same batch is still reported via the
existing `batching_report` path, unchanged
**And** a regression test proves a populated-map launch renders a different `policy.toml` than
an empty-map launch for the identical story set

### Story 3.12: A struggling retry runs under a stronger model *(added 2026-08-11 — FR-183)*

As the operator,
I want a story that keeps failing its attempts or review cycles to get a stronger model without
me hand-editing `policy.toml` and relaunching,
So that a story's last, most expensive attempt is not paying the same model cost as its first.

**Type:** feature • **Effort:** L • **Deps:** S-3.11, S-3.6, S-3.7 • **FR/AD:** FR-183; AD-26, AD-28

**Why now.** Neither side of the seam ties attempt count to model selection today: Marshal
resolves a story's tier once per launch, before `bmad-loop run` is ever spawned, and the vendored
`bmad_loop==0.9.0` engine only couples `task.attempt` to a budget check
(`escalation.py:68` `budget_left = task.attempt < policy.limits.max_dev_attempts`) — never to a
model. A story on its last attempt runs exactly as cheap a model as its first, even when the
retry history says otherwise.

**Acceptance Criteria:**

**Given** a story whose attempt or review-cycle count crosses a configured threshold, derived
from the journal fold the run state already accumulates (AD-26) — never a new hand-maintained flag
**When** the story is next dispatched — whether that is a live mid-run intervention or its next
resume through `run_resume`'s own existing re-render (an implementation choice this story
resolves; `run_resume` already re-resolves and re-renders model tiering before relaunching)
**Then** it runs under a model at least as strong as its already-resolved tier — a floor-raise
only, never a downgrade
**And** the escalation is journaled with the same intent/outcome discipline (AD-28) every other
supervisor action already uses, naming the trigger and the resulting model
**And** the escalation is bounded — it does not re-fire without a new trigger, matching C-6's
"every run has a ceiling; there is no unbounded mode"
**And** a story with no declared difficulty and no populated tier map still has a baseline model
to escalate from — this is not a no-op for the majority of stories that remain undeclared
**And** a regression test proves a synthetic struggling story (attempt count over threshold)
resolves to an escalated model, and a fresh story does not

### Story 3.13: The parallel-fan-out clamp is surfaced, not silent *(added 2026-08-11 — FR-184)*

As the operator,
I want to be told when `bmad_loop`'s own unbuilt parallel scheduler silently clamps my request,
So that a `max_parallel > 1` setting fails loud instead of quietly doing nothing.

**Type:** feature • **Effort:** S • **Deps:** S-3.3, S-6.8 • **FR/AD:** FR-184; AD-2, AD-3
**Surface:** `adapters/harness_bmadloop.py`,
`_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json`

**Why now.** Direct read of the vendored `bmad_loop==0.9.0` package confirms `scm.max_parallel`
is an inert stub: `policy.py:448-451` names it "Phase 5 ... not built yet," and `policy.py:815-817,
841-842` clamp any requested value to 1 unconditionally, with no diagnostic surfaced to the
caller. Marshal's own rendered template carries the identical `max_parallel = 1`
(`harness_bmadloop.py:320`) with no explanation. This gap is unregistered — Story 6.8's
`upstream-register.json` tracks 8 other `bmad_loop` gaps, including the adjacent
per-story-model-tiering one, but not this one.

**Acceptance Criteria:**

**Given** a project policy that requests `max_parallel > 1`
**When** policy is composed, rendered, or preflight runs
**Then** a registered finding/advisory names the clamp and its cause — `bmad_loop` 0.9.0's own
unbuilt Phase 5 fan-out — rather than the request silently vanishing
**And** `upstream-register.json` gains a new entry for this gap in the same shape as its
existing 8 entries, surfaced by `marshal upstream`
**And** a written readiness assessment names what Marshal-side machinery (worktree isolation,
the journal's multi-writer design, the supervisor, the landing path) already holds for
N-stories-in-flight and what remains unverified — a scoped starting point for whenever an
upstream scheduler ships, not a promise that one ships from this story
**And** nothing in this story modifies the vendored `bmad_loop` package or claims concurrent
dispatch ships now
**And** a regression test proves the advisory fires for a `max_parallel > 1` policy value and
stays silent at the default of 1

## Epic 4: Landing with a durable paper trail

**Goal:** the operator can close a wave in one command and the paper trail survives by construction. This epic exists because the motivating incident — 13 of 31 story specs lost outright, 8 more reduced to zero-byte husks — was caused by a step a human had to remember.

### Story 4.1: Story-spec promotion with a durability predicate

As the operator,
I want every merged story's spec promoted into tracked artifacts automatically and durably,
So that "promoted" means "will still exist next week", not "a file was written".

**Type:** feature • **Effort:** L • **Deps:** S-3.2 • **FR/AD:** FR-30; SM-3; AD-12, AD-13, AD-29
**Surface:** `cli/deploy.py`, `adapters/vcs_git.py`, `core/journal.py`

**Acceptance Criteria:**

**Given** a merged story with a spec in run scratch
**When** promotion runs
**Then** the spec is copied to the tracked `planning-artifacts/specs/` archive path **and committed by Marshal itself**, in a dedicated commit containing **only** promotion paths — it never commits a pre-existing index (AD-29)
**And** the story is marked `promoted` **only** when its bytes are reachable from a ref that survives the loop home (pushed to the remote, or merged to the integration branch) — a staged file, or a commit only on `loop/<slug>`, is **not** promoted (AD-29)
**And** promotion happens **before** any code path may remove that story's worktree (AD-13)
**And** a merged story with no promotable spec is reported as a paper-trail gap, never passed over silently
**And** zero-byte or truncated specs are detected and reported rather than promoted over a good copy
**And** the canonical archive is authoritative; run scratch is derived and never treated as the source (AD-12)

### Story 4.2: Teardown reachability and spec-recovery assistance

As the operator,
I want teardown to compute durability at teardown time and to help me when a spec is missing,
So that a stale flag can never authorize destroying the last copy.

**Type:** feature • **Effort:** M • **Deps:** S-1.8, S-4.1 • **FR/AD:** FR-6 (completion), FR-31; NFR-6; AD-29
**Surface:** `cli/init.py` (teardown), `cli/deploy.py`, `adapters/vcs_git.py`

**Acceptance Criteria:**

**Given** a loop home with merged stories
**When** teardown runs
**Then** the refusal predicate is **reachability computed at teardown time**, never a journal flag (AD-29)
**And** a forced teardown over an unreachable promotion requires the operator to **name the story keys being abandoned**, and records them
**Given** a story whose spec is missing
**When** recovery assistance runs
**Then** it reports the ordered candidate locations — surviving run-worktree snapshots first, then the epics-derived contract fallback
**And** it **reports, never fabricates**: any regenerated contract-only spec is labelled as such in its own frontmatter

### Story 4.3: Merge-subject conformance and review-cap landing

As the operator,
I want to land a sound-but-unconverged story under the same gates, without hand-typing a magic string,
So that the manual landing path is as governed as the automatic one.

**Type:** feature • **Effort:** M • **Deps:** S-1.2, S-2.3 • **FR/AD:** FR-27, FR-32; AD-24
**Surface:** `cli/deploy.py`, `core/identity.py`, `adapters/vcs_git.py`

**Acceptance Criteria:**

**Given** a named story branch that is sound but did not converge in review
**When** the review-cap landing command runs
**Then** it re-runs the **full** gate — verify commands plus scope check — and lands only on a green result (FR-27)
**And** the merge uses the conventional subject rendered from policy; the operator never hand-types it
**And** the manual landing and its justification are journaled
**And** deploy reports any merge in the wave whose subject does not conform, using the **same parser** that renders it — not a second regex (AD-24)
**And** the subject template lives in policy, not as a literal in code

### Story 4.4: Batch pull request with hygiene preflight

As the operator,
I want one PR for a wave, with mechanical repository gates checked first,
So that landing does not red CI on something a machine could have told me.

**Type:** feature • **Effort:** M • **Deps:** S-3.2 • **FR/AD:** FR-28, FR-29, FR-35; NFR-2, NFR-11; AD-34
**Surface:** `cli/deploy.py`, `ports/forge.py`, `adapters/forge_gh.py`

**Acceptance Criteria:**

**Given** a wave of merged stories
**When** the batch PR is opened
**Then** title and body derive from the merged set and the journal, and the body lists stories with their gate verdicts
**And** it targets the configured base branch and is never opened against an upstream fork's default
**And** existing-PR detection updates rather than duplicating
**And** hygiene preflight reports which project-configured rules apply to the change set and whether each is satisfied, with rules **declared in policy, never hard-coded into Marshal** (FR-29)
**And** an unsatisfied blocking rule exits non-zero with a remediation line
**And** **no AI-attribution or courtesy preamble** appears in any commit, PR body, or comment Marshal emits; attribution is opt-in configuration, default-off (FR-35)
**And** PR text routes through the egress serializer and is redacted (AD-34)
**And** the forge adapter is the only outbound network path; everything else is local (NFR-2)

### Story 4.5: Feed refresh with truth partitioned by domain

As the operator,
I want derived status surfaces refreshed from the right authority,
So that deploy does not write something status immediately flags as wrong.

**Type:** feature • **Effort:** M • **Deps:** S-3.2, S-4.1 • **FR/AD:** FR-33; AD-12, AD-33
**Surface:** `cli/deploy.py`, `core/status.py`

**Acceptance Criteria:**

**Given** a landed wave
**When** feed refresh runs
**Then** **git is the sole authority for repository facts** (merged/not, tree revision, branch existence, commit subject) and **the journal is the sole authority for process facts** (transitions, verdicts, escalations, consumption) (AD-33)
**And** no derived artifact sources a repository fact from the journal or a process fact from git; each derived field declares its canonical domain
**And** a journal claim about a repository fact is stored as `claimed_*` and is only ever an input to a reconciliation finding, never a rendered value
**And** console data regeneration is invoked where configured
**And** discrepancies are **reported, never silently resolved**
**And** regenerating a derived artifact when nothing changed is a **provable no-op** (AD-12)

### Story 4.6: Deploy idempotence and reconciliation of open intents

As the operator,
I want to re-run deploy after a partial failure and have it finish the job,
So that a crash mid-landing is recoverable without guesswork.

**Type:** feature • **Effort:** M • **Deps:** S-4.1, S-4.4 • **FR/AD:** FR-34; NFR-7; AD-6, AD-21, AD-28
**Surface:** `cli/deploy.py`, `core/journal.py`

**Acceptance Criteria:**

**Given** a deploy that failed partway
**When** it is re-run
**Then** each step reports `done | skipped | failed` and already-promoted specs are neither re-promoted nor duplicated
**And** a re-run against a fully converged system produces zero changes and exit 0 (NFR-7)
**Given** a lone `intent` entry from a crash
**When** reconciliation runs
**Then** it is closed **only** by a `reconciliation` outcome carrying observed external evidence — commit sha, worktree absence, PR number — plus the reconciling command (AD-28)
**And** absent evidence the intent stays open and is reported
**And** **reconciliation may observe and close; it may never re-perform an action whose intent is open without evidence the action did not occur** — the explicit AD-6 × AD-21 precedence

---

### Story 4.7: Landing rules as declared policy *(added 2026-08-01 — FR-59 / CAP-9)*

As the operator,
I want the rules a repository demands for landing declared as policy keys with provenance,
So that landing stops being a memorized habit with a good track record.

**Type:** feature • **Effort:** M • **Deps:** S-1.3 • **FR/AD:** FR-59; AD-40, AD-10, AD-16
**Surface:** `core/policy.py`, `core/landing.py`, `schemas/policy.json`

**Acceptance Criteria:**

**Given** a project whose repository demands checks, labels, a merge strategy, and retirement behaviour
**When** policy composes
**Then** the landing surface appears as governed keys with per-key provenance — including repo-specific triggers such as this repository's `maintenance` label and its **ungated** `environment.yaml` sync check
**And** an invalid landing policy is a preflight finding naming the layer that introduced each bad key
**And** the effective landing policy prints with each key's winning layer, secrets redacted

---

### Story 4.8: `marshal land` — the last mile lands itself *(added 2026-08-01 — FR-60 / CAP-9)*

As the operator,
I want a story or wave that passed its gates to land on the integration branch without me driving the sequence,
So that a run that ends with "somebody should open a PR" has actually ended.

**Type:** feature • **Effort:** L • **Deps:** S-4.4, S-4.7 • **FR/AD:** FR-60; AD-40, AD-8, AD-6; NFR-6, NFR-7
**Surface:** `cli/land.py`, `core/landing.py`, `adapters/forge_gh.py`, `core/journal.py`

**Acceptance Criteria:**

**Given** a merged wave and a composed landing policy
**When** `marshal land` runs
**Then** it opens or updates the PR (never duplicates), applies required labels, waits on required checks, merges by the declared strategy, retires the branch, and resyncs
**And** a half-landed story — PR open, checks green, merge never issued — converges on re-run (idempotent and re-entrant)
**Given** a red required check or an unacknowledged advisory finding
**When** landing is attempted
**Then** it refuses with a registered finding in the common envelope — no silent force, exactly teardown's refusal shape
**And** every landing appends a journal verdict: checks required, checks passed, what merged, under whose authority
**And** nothing emitted carries an AI-attribution trailer (FR-35 applies unchanged)

---

### Story 4.9: Derived surfaces regenerate on main; the shared store takes a lock *(added 2026-08-01 — AD-42 / the Q-10 decomposition)*

As the operator,
I want regenerated artifacts re-derived after landing instead of merged from homes, and shared-store appends serialized,
So that two concurrent lines cannot silently last-write-wins each other's ledgers.

**Type:** feature • **Effort:** M • **Deps:** S-4.5, S-4.8 • **FR/AD:** AD-42; C-3, C-4; extends FR-33
**Surface:** `cli/deploy.py`, `cli/land.py`, `adapters/fs_local.py`

**Acceptance Criteria:**

**Given** a landing that changes story state
**When** the sprint and console surfaces refresh
**Then** they are **re-derived on the integration branch after the merge** — a regenerated file is never merged from a loop home
**Given** two concurrent appends to the canonical Tier-3 store
**When** both run
**Then** an advisory file lock (an `FsPort` primitive) serializes them and neither append is lost
**And** the journal's own two-writer protocol is explicitly out of scope here (F-6 owns it) — a test documents the boundary

---

### Story 4.10: Fleet-wide branch retirement *(added 2026-08-01 — FR-63 / AD-47)*

As the operator,
I want Marshal to propose which station and story branches may be released across the whole fleet, proving its case for each,
So that saving work does not leave a permanently growing pile of branches nobody knows when to delete.

**Type:** feature • **Effort:** L • **Deps:** S-3.8, S-4.8 • **FR/AD:** FR-63; AD-47, AD-27; NFR-6
**Surface:** `cli/retire.py`, `core/retire.py`, `adapters/git_local.py`

**Acceptance Criteria:**

**Given** the fleet's accumulated branches
**When** a retirement sweep runs
**Then** a branch is proposed only when three facts are independently provable — content reachable in the integration branch **by patch-id**, its run concluded, its story `done` with a recorded merge sha
**And** the proposal names its evidence (merge sha, patch-id match, concluded run) per branch
**Given** `loop/*` branches or `rescue/*` tags
**When** the sweep runs
**Then** they are never proposed — a structural exclusion, not a policy-configurable one
**Given** a branch the sweep cannot fully prove
**When** it evaluates that branch
**Then** it refuses rather than defaulting to delete
**And** the sweep runs dry-run by default, exactly as teardown does (FR-8)
**And** a branch FR-59/AD-40 already retired at landing time is never re-proposed here — the two mechanisms share evidence but never disagree

---

### Story 4.11: `marshal land` refuses while a run is in flight *(added 2026-08-09 — FR-172)*

As the operator,
I want landing to know whether a run is still using the branch it is about to retire,
So that the last mile cannot destroy a running fleet.

**Type:** change • **Effort:** S • **Deps:** S-4.8 • **FR/AD:** FR-172

**Why now.** `land` resolves its head branch to the loop-home **station branch** and
`landing_branch_retirement` defaults to `True`. Invoked on 2026-08-09 during a live 9-story run
it would have merged and then deleted `loop/pyforge-doctor` — the branch bmad-loop was actively
merging stories into. It was avoided only because a human read `cli/land.py` first.

**Acceptance Criteria:**

**Given** a slug whose supervisor/engine is live (the same liveness `marshal status` reads)
**When** `marshal land <slug>` runs
**Then** it **refuses by name**, identifying the run and the branch it would have retired
**And** the refusal is overridable by an **explicit** flag whose help states what it accepts —
landing mid-run is legitimate between stories; it must never be the silent default
**And** what is refused is the **branch retirement**, not the merge: `--no-retire` style landing
of a wave during a run stays supported
**And** a test proves both directions: live run → refusal, no live run → unchanged behaviour

### Story 4.12: A landing leaves the loop home current with `main` *(added 2026-08-09 — FR-173)*

As the operator,
I want landing to return the station branch to `main`,
So that "resync" means the home is current, not merely that the feed is.

**Type:** change • **Effort:** M • **Deps:** S-4.8 • **FR/AD:** FR-173

**Why now.** `landing_resync` resyncs the **feed**; `landing_resync_commands` is empty by
default. Nothing returns the loop home to `main`, so it drifts from the first merge onward —
measured 5 commits behind minutes after its own stories landed, and 8 PRs behind on origin
between runs, reported clean by every detector.

**Acceptance Criteria:**

**Given** a landing that merged a wave to `main`
**When** the resync step runs
**Then** the station branch is brought current with `main` (fast-forward where possible)
**And** where it cannot be, the reason is reported precisely — never silently left behind
**And** a home with **no live run** is in scope: between-runs is exactly where drift accumulates
unobserved
**And** the resync never rewrites history and never force-pushes
**And** a test covers the fast-forwardable case, the non-fast-forwardable case, and the
live-run case (which must interact correctly with S-4.11's refusal)

### Story 4.13: The loop's deferred work reaches the tracked ledger *(added 2026-08-09 — FR-175)*

As the operator,
I want a follow-up the loop defers to land in the tracked ledger with a non-colliding id,
So that a deferral is a decision of record rather than a note on one disk.

**Type:** change • **Effort:** S • **Deps:** S-4.8 • **FR/AD:** FR-175

**Why now.** Measured 2026-08-09: `DW-1`/`DW-2` were promoted by hand as `DW-FU-1-1`/`DW-FU-1-3`;
**`DW-3`…`DW-7` never were** and stand today as five `tier3-only-deferral` findings. The loop
writes generic `DW-<n>` ids into gitignored Tier-3.

**Acceptance Criteria:**

**Given** a story whose damping cap was spent and which filed a Tier-3 deferral
**When** that story lands
**Then** the deferral is promoted into `planning-artifacts/deferred-work-ledger.md` under the
`DW-<story>-<n>` convention, so the next damped story cannot collide with it
**And** `deferred-work-check` reports **zero** `tier3-only-deferral` findings for that story
**And** the five standing entries (`DW-3`…`DW-7`) are promoted or dispositioned with a reason —
never deleted to clear the count
**And** promotion is idempotent: re-running it does not duplicate an already-promoted entry

### Story 4.14: The failed-story safety net is reported *(added 2026-08-09 — FR-176)*

As the operator,
I want a killed story's preserved patch surfaced,
So that a patch holding unlanded work cannot sit unnoticed on one disk.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** FR-176

**Why now.** A session-timeout kill preserves work at `<run>/failed/<story>/changes.patch` and
**nothing in the repo reads that path**. Measured 2026-08-09: **7 patches, 26 KB–205 KB**, across
five stations. All seven belong to stories that later reached `done` — nothing is lost today,
which is exactly why it went unnoticed.

**Acceptance Criteria:**

**Given** one or more `failed/<story>/changes.patch` files under any loop home
**When** the durability check runs
**Then** each is reported with its story key, size, and whether that story has since landed
**And** a patch whose story is `done` is reported as **spent** — informational, never gating,
since the work demonstrably landed
**And** a patch whose story is **not** `done` is a real finding: pending work on one disk
**And** the check is silent when no such patch exists — an empty safety net is not a finding

### Story 4.15: One pusher, not two *(added 2026-08-09 — FR-177)*

As the operator,
I want `loop_push_watch.py`'s role reconciled with the supervisor that now subsumes it,
So that the durability story has one owner and its documentation is true.

**Type:** change • **Effort:** S • **Deps:** S-3.8 • **FR/AD:** FR-177

**Why now.** FR-61 gave the supervisor its own `boundary: "interval"` push, so during a run the
standalone watcher duplicates it. Its pixi description still calls itself "a STOPGAP — the
durable fix is for the loop to push at its own stage boundaries" — a statement **Marshal made
false when FR-61 shipped**, and the reason an operator on 2026-08-09 concluded nothing was
pushing at all.

**Acceptance Criteria:**

**Given** the supervisor's interval push exists
**When** the watcher's role is decided
**Then** it is either **retired**, or **re-scoped to the one case the supervisor structurally
cannot cover** — a home with no live run — and its pixi description says which
**And** no description anywhere still claims stage-boundary push is unbuilt
**And** if retired, `unpushed-work-check` (S-3.10's tip comparison) is confirmed as the standing
signal for between-runs staleness, so retiring the watcher removes a duplicate rather than a net

## Epic 5: Fleet visibility

**Goal:** with many loop homes live, the operator gets one view derived from ledgers rather than assembled by hand — and is told, rather than left to discover, where the ledger and git disagree.

### Story 5.1: Fleet view

As the operator,
I want every loop home and its state in one command,
So that "what is running?" is one question, not five.

**Type:** feature • **Effort:** S • **Deps:** S-1.6, S-3.2 • **FR/AD:** FR-36; NFR-14; AD-5
**Surface:** `core/status.py`, `cli/status.py`

**Acceptance Criteria:**

**Given** any number of loop homes
**When** `marshal status` runs
**Then** it shows one row per home: project, branch, state (`idle | running | paused-on-escalation | stopped`), current story, elapsed time, budget consumed
**And** every row is derived from journals and run state — **never from a hand-maintained file** (AD-5)
**And** a home with a dead supervisor is shown as unsupervised, not as healthy
**And** the command completes in under 10 seconds with at least seven homes present (NFR-14)

### Story 5.2: Per-run detail

As the operator,
I want to drill into one run,
So that I can see exactly what each story did without opening a journal by hand.

**Type:** feature • **Effort:** S • **Deps:** S-5.1 • **FR/AD:** FR-37; NFR-12
**Surface:** `core/status.py`, `cli/status.py`

**Acceptance Criteria:**

**Given** a run id
**When** detail is requested
**Then** it shows the story sequence with per-story gate verdicts, escalations, deferrals and consumption
**And** every human view has a machine-readable counterpart in the standard envelope, with **no human-only information** (NFR-12)
**And** open `intent` entries are shown as open, with the evidence they await

### Story 5.3: Escalation queue

As the operator,
I want runs blocked on a decision surfaced first,
So that the thing needing me is never buried.

**Type:** feature • **Effort:** XS • **Deps:** S-5.1 • **FR/AD:** FR-38
**Surface:** `core/status.py`, `cli/status.py`

**Acceptance Criteria:**

**Given** one or more runs paused on escalations
**When** status runs
**Then** those rows are visually distinguished and sorted to the top
**And** each carries the reason and the artifact needing a decision
**And** the queue is available as a standalone filtered view for scripting

### Story 5.4: Ledger-vs-git reconciliation and the versioned status contract

As a downstream consumer,
I want a stable machine-readable status contract that reports disagreements rather than papering over them,
So that a dashboard can trust it without scraping human output.

**Type:** feature • **Effort:** M • **Deps:** S-5.1, S-4.5 • **FR/AD:** FR-39, FR-40; NFR-12; AD-33, AD-39
**Surface:** `core/status.py`, `schemas/status.json`

**Acceptance Criteria:**

**Given** a project whose sprint ledger and git history disagree
**When** status runs
**Then** a story marked done with no corresponding merge — **and the converse** — is reported as a named discrepancy
**And** git remains authoritative for the repository fact and the journal for the process fact; neither is silently rewritten (AD-33)
**And** the payload carries a `schema_version` for the envelope and a `data_version` for the status payload, bumped independently; additive fields bump neither (AD-39)
**And** the schema is published in `schemas/` and validated in tests
**And** the console generator can consume it without scraping human output

---

### Story 5.5: Durability as a reported fleet-status dimension *(added 2026-08-01 — FR-62 / AD-48)*

As the operator,
I want unpushed work reported on the owning row in `marshal status`, not only in a separate detector's output,
So that "is the fleet's work saved?" never again needs a second command.

**Type:** feature • **Effort:** S • **Deps:** S-5.1, S-3.8 • **FR/AD:** FR-62; AD-48, AD-38, AD-39
**Surface:** `core/status.py`, `schemas/status.json`

**Acceptance Criteria:**

**Given** a loop home whose branches carry local-only content
**When** `marshal status` runs
**Then** that row carries an unpushed-work finding naming the branch and the extent (line or commit count) — the row is never reported clean
**And** the finding is **read from** the unpushed-work detector's own evidence, never re-derived against git independently (AD-48)
**And** the finding's presence follows the same versioned-envelope discipline as every other status field (FR-40, AD-39) — additive, no schema-version bump

---

### Story 5.6: `marshal check` — the detector registry through the front door *(added 2026-08-01 — FR-65 / AD-50)*

As the operator,
I want the repo's detector registry reachable as `marshal check`, with project/loop-home/policy/story context resolved once for it and every other verb,
So that I stop needing to remember a separate pixi task exists, and two routed calls in one invocation never silently disagree about which project they're acting on.

**Type:** feature • **Effort:** M • **Deps:** S-5.1, S-1.3 • **FR/AD:** FR-65; AD-50, AD-16, AD-35
**Surface:** `cli/check.py`, `core/context.py`

**Acceptance Criteria:**

**Given** the repo's detector registry (`scripts/detectors.py`)
**When** `marshal check` runs
**Then** it invokes the registry and returns the same findings as the standalone pixi task — a route, never a reimplementation
**Given** a `marshal` invocation dispatching to any verb — `check`, `run` (`factory spin`), `status`, or `land`
**When** context (active project, loop home, composed policy, in-scope story) is needed
**Then** it is resolved exactly once at the front door and threaded to the dispatched verb, which never re-derives it independently
**And** `marshal status`'s fleet view may summarize detector-registry state per row; the detailed findings remain `check`'s own output
**And** this story does not rename `factory spin`/`status`/`land` (Q-15 stays open) and does not decide the route-versus-contain boundary for any other `bmad-*` skill beyond this one concrete case (Q-16 stays open)

---

### Story 5.7: The board answers "how much is left" *(added 2026-08-09 — FR-179)*

As the operator,
I want the console to show done/total/blocked per station and a PyForge roll-up,
So that the first question anyone asks of a fleet is answerable without a CLI.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** FR-179

**Why now.** Five stations ran in parallel overnight and the board could not answer "how much is
done, how much is left". It had every per-epic story list and no total.

**Acceptance Criteria:**

**Given** the tracked `sprint-status-ledger.yaml` of each project
**When** the board is generated
**Then** `data.js` carries per-station `done`/`stories`/`blocked`/`epicsDone`/`epics` plus a
PyForge roll-up, counted through the **same** `parse_sprint_status` the deploy already uses
**And** `blocked` is counted separately — the board's own states (`done`/`active`/`pending`)
cannot distinguish blocked from unstarted, and 6 blocked looked identical to 119 pending
**And** an epic counts done only when every story in it is done, matching
`scripts/fleet_picture.py` so the two can never disagree
**And** **no live field is published**: run state, projection and ATTENTION derive from tmux and
`~/.bmad-loops`, which CI cannot read — they stay in the local `fleet-picture` report
**And** `dashboard-check` (which executes the board's own JS) passes

---

### Story 5.8: A dead supervisor sidecar doesn't hide a live engine *(added 2026-08-11 — FR-181)*

As the operator,
I want a home whose supervisor sidecar is dead but whose engine is still running to read
differently from one that actually needs a re-spin,
So that I stop needing a manual `ps`/`tmux ls`/`state.json` cross-check every time a
sidecar goes missing.

**Type:** feature • **Effort:** S • **Deps:** S-5.1 • **FR/AD:** FR-181; AD-5
**Surface:** `core/status.py`, `cli/status.py`

**Why now.** On 2026-08-11, five stations resumed via bare `bmad-loop resume` (which never
spawns a fresh supervisor sidecar) reported `unsupervised — needs re-spin` for the rest of
their run's life, although each was independently verified alive and working. The operator
ran the same manual cross-check by hand three separate times in one session before
recognizing the pattern. `derive_home_state`'s first branch (`if not finished and
supervisor_alive is False: return "unsupervised"`) returns before ever checking whether the
engine itself has an in-flight task — the only signal it consults is the sidecar's own pid,
and a sidecar can go missing (crash, `--foreground`'s escape hatch, a killed-and-restarted
sidecar, a pid never recovered) for reasons independent of the engine's own health.

**Acceptance Criteria:**

**Given** a run whose supervisor sidecar pid is dead but whose engine is independently alive
**When** `derive_home_state` would otherwise return `"unsupervised"` on its first branch
**Then** it consults a fallback liveness signal before returning, and reports the row as
healthy — not `"unsupervised"` — when the engine is demonstrably still working
**And** a run whose engine is ALSO gone still reports `"unsupervised"` — this narrows a false
positive, it never softens a real one
**And** the fallback signal is itself derived from journals/process state (AD-5), never a
hand-maintained flag or an operator override
**And** the two failure shapes are distinguishable from `marshal status`'s own output, so an
operator or `fleet-picture` never again needs the `ps`/`tmux ls`/`state.json` cross-check by
hand to tell them apart

---

### Story 5.9: A story finished by hand isn't invisible to the ledger *(added 2026-08-11 — FR-186)*

As the operator,
I want a story completed and merged via `bmad-quick-dev` (the retired 6.x name of `bmad-build`) — with no `bmad-loop` run ever
touching it — reconciled into the tracked ledger the same way a loop-landed story is,
So that mixing `bmad-quick-dev` (retired name) and `bmad-loop` within one station never leaves Marshal's own
state out of sync with what actually happened.

**Type:** feature • **Effort:** M • **Deps:** S-5.4, S-4.1 • **FR/AD:** FR-186; AD-5, AD-33
**Surface:** `core/status.py`, `scripts/promote_sprint_status.py`

**Why now.** A repo-wide grep of `src/shared/packages/pyforge-marshal/` for `quick-dev`/
`quick_dev` returns zero matches — every reference lives in planning prose, none in `core/`,
`cli/`, `adapters/`, or a schema. `sprint-status-ledger.yaml`'s `development_status:` map is a
flat `done | backlog` vocabulary that only ever advances on a signal `bmad-loop` itself emits
(`scripts/promote_sprint_status.py`'s own docstring: "bmad-loop marks a story `done` at DEV
completion"). A story hand-implemented via `bmad-quick-dev` (retired name) — real, tested, merged to `main`
— never calls that path, so its key reads `backlog` forever unless an operator hand-edits a
generated file. Story 5.4 already reports the converse case (a story marked done with no
corresponding merge) as a named discrepancy; this is the mirror case Story 5.4 does not yet
cover — a real merge with no ledger signal — and it is the concrete blocker to letting an
operator hand-pick a story for `bmad-quick-dev` (retired name) while that station's loop is between stories,
or mid-run on a different one, without Marshal's own tracked state silently going stale.

**Acceptance Criteria:**

**Given** a backlog story merged to the integration branch with no corresponding `bmad-loop`
run/journal record
**When** ledger reconciliation runs
**Then** the story is detected as completed outside the loop, from git (the repository fact)
plus existing spec/story-identity artifacts alone — never a new hand-maintained flag (AD-5,
AD-33)
**And** its key advances out of `backlog` in `sprint-status-ledger.yaml` (or the mechanism
feeding it), with the completion path recorded as `bmad-quick-dev` (retired name; the shipped code label is `not-loop-native`), distinct from a
`bmad-loop` completion
**And** `marshal status` / the fleet dashboard shows the completion path with no operator
hand-edit and no commit-subject archaeology
**Given** a quick-dev'd story's spec
**When** its story is detected as done
**Then** the spec is promoted/tracked under the same durability guarantee Story 4.1 already
gives a loop-landed story's spec
**Given** a live `bmad-loop` run on a station, mid-run on a different story
**When** a separate story on that station is reconciled as quick-dev-completed
**Then** the reconciliation neither reads from nor writes to the live run's own journal, and a
test proves the live run's state is unaffected
**And** this story does not change `bmad-quick-dev` (retired name) itself, and does not decide whether
Marshal ever invokes it on an operator's behalf (PRD Q-16 stays open)

### Story 5.10: `marshal land` renders a detectable merge subject *(added 2026-08-12 — FR-187, backlog)*

As the operator,
I want `marshal land`'s own merges to render the same templated, detectable merge subject
`deploy land-story` already does,
So that `marshal_native_merged_keys` classifies every Marshal-driven landing correctly, instead
of `marshal land`'s landings being indistinguishable from a human's plain PR merge.

**Type:** feature • **Effort:** S • **Deps:** S-5.9 • **FR/AD:** FR-187; AD-5, AD-24, AD-34
**Surface:** `cli/land.py`, `ports/forge.py`, `adapters/forge_gh.py`

**Why now.** Discovered 2026-08-12 during Story 5.9's review pass 2: `core.promotion.
marshal_native_merged_keys` correctly classifies `deploy land-story`'s templated subject and
bmad-loop's own native form, but `marshal land` (`cli/land.py::run_land`) merges via
`forge.merge_pr` → `gh pr merge`, which lets GitHub auto-generate the subject — a shape
byte-identical to a human's plain PR merge. Of the keys `merged_story_keys` finds outside the
templated/native patterns, the large majority are `marshal land` landings, not genuine
`bmad-quick-dev` (retired name) sessions, so every consumer of this classification (fleet-picture, `marshal
status`, `dashboard-drift-check`, Story 5.9's own `reconcile-completions`) currently mislabels
them. Confirmed low-risk: `gh pr merge` already supports `-t/--subject` for every strategy
(merge/squash/rebase). Not urgent — backlog, not a prerequisite for Story 5.9, which ships with
the coarser `not-loop-native` label this story lets narrow automatically once it lands.

**Acceptance Criteria:**

**Given** a `marshal land` landing
**When** it merges
**Then** the merge commit's subject is the same templated form
`identity.render_merge_subject(story_key, template)` produces (AD-24), applied via an optional
`subject` parameter on `ForgePort.merge_pr` threaded to `gh pr merge -t` — never a separate,
pre-merge PR-title-edit call
**And** `core.promotion.marshal_native_merged_keys`, given that real subject, classifies the key
as native — the same outcome it already produces for a `deploy land-story` merge
**Given** `marshal land`'s existing default `landing_merge_strategy`, its gates, and every other
step of `run_land`
**When** this story ships
**Then** none of them change — only the merge commit's subject line changes
**And** this story does not retroactively relabel any ledger row already marked
`done`/`not-loop-native` before it ships, and does not change `deploy land-story`,
`bmad-quick-dev` (retired name), or Story 5.9's own `reconcile-completions` code

---

### Story 5.11: A harness-native terminal run reads as finished, not `unknown` *(added 2026-09-08 — FR-196)*

As the operator,
I want a run that bmad-loop started directly — without `marshal factory spin` — to report its
real state once it has finished,
So that a station is not stuck at `unknown` forever merely because Marshal did not launch it
itself, and `fleet-picture` can assert that station's liveness again.

**Type:** feature • **Effort:** M • **Deps:** S-5.1, S-5.8 • **FR/AD:** FR-196; AD-5
**Surface:** `core/status.py`, `cli/status.py`, `ports/harness.py`, `adapters/harness_bmadloop.py`

**Why now.** `pyforge-steward` has read `UNKNOWN — 18 left, needs re-spin` since 2026-08-20, and
`DW-STATUS-2026-09-08-1` traced it end to end. Its newest loop-home run
(`.bmad-loop/runs/20260820-140536-988f`) carries 32 journal events in bmad-loop's OWN vocabulary
— `run-start`, `story-start`, `session-start`/`session-end`, `story-done`, and a graceful
terminal `run-stop` — and not one `run-launch`/`run-resume`, which is the shape `cli/spin.py`
writes and the only shape `_gather_run_journal_facts` folds for a launch pid. So
`journal_facts.launch_pid is None`, `cli/status.py`'s FIRST `journal_unreadable` branch fires,
and the whole row degrades — even though the same journal plainly records the run as over, and
`state.json` agrees (`finished: true`, `stopped: true`, `crashed: false`). Marshal only
understands runs it launched itself. This is NOT the retired-snapshot path (`run_state_retired`
+ MRS-STATUS-012), which is already fixed and is a different cause. The consequence is not
cosmetic: a station stuck at `unknown` is a station whose liveness `fleet-picture` cannot
assert, which is the precondition for the duplicate-dispatch class recorded against 2026-08-27.

**The seam matters.** Teaching `cli/status.py` to fold bmad-loop's `run-start`/`run-stop`
vocabulary directly would couple the CLI to the harness's journal format, bypassing
`HarnessPort` — the seam that abstracts bmad-loop for exactly this reason. The capability
belongs behind the port.

**Acceptance Criteria:**

**Given** a loop-home run whose journal carries no `run-launch`/`run-resume` entry, so no launch
pid is recoverable
**When** `_gather_run_journal_facts` returns `launch_pid=None`
**Then** the derivation consults a `HarnessPort` capability that answers whether that run is
terminal, rather than degrading the row to `journal_unreadable` on the spot
**And** the capability is implemented in `adapters/harness_bmadloop.py` — `cli/status.py` and
`core/status.py` learn no bmad-loop journal kind, and no harness-specific string appears outside
the adapter
**Given** a run the port reports terminal
**Then** the row reports a finished state with a WARN naming the gap (mirroring Story 5.1's own
`journal_unreadable` treatment and MRS-STATUS-012's shape), never a healthy state with no signal
**Given** a run the port cannot classify, or reports non-terminal
**Then** the row stays `unknown` and `is_run_live` keeps it conservatively live — this narrows a
false positive and must not weaken any destructive guard
**And** `pyforge-steward`'s existing home is the acceptance fixture: it reads as finished after
this story, without a re-spin

## Epic 6: Portability proven

**Goal:** the operator can run the method on an agent other than the default, and hold a dated artifact that says so. This epic exists because 89 skills currently live only in one adapter's tree while four of six adapter profiles read from another — so "BMAD runs on any agent" is today an aspiration, not a fact.

### Story 6.1: Profile-driven adapter selection, project-scoped

As the operator,
I want adapter and model choices to resolve per project from declarative profiles,
So that two homes can run different agents simultaneously and Marshal never branches on adapter name.

**Type:** feature • **Effort:** M • **Deps:** S-1.3, S-1.7 • **FR/AD:** FR-48, FR-51; AD-19
**Surface:** `adapters/harness_bmadloop.py`, `core/policy.py`, `cli/adapters.py`

**Acceptance Criteria:**

**Given** two loop homes with different configured adapters
**When** both are launched
**Then** each resolves its own adapter and per-stage models without cross-configuration
**And** the resolved adapter and per-stage models are echoed at launch and journaled
**And** everything adapter-specific — binary name, skill-tree path, seed files, first-run requirement, bypass semantics — is read from the harness's declarative profile (packaged, overlaid by project-local) plus the probe record; **Marshal contains no `if adapter == "..."` branch**, asserted by a meta-test (AD-19)
**And** an unknown adapter is handled generically or reported `unevaluable` — never a crash
**And** per-story model tiering maps a story's declared difficulty class to per-stage models, with an undeclared story taking the mechanical default; where the harness supports only run-level selection, Marshal batches stories by tier and reports the batching (FR-51)

### Story 6.2: Skill-tree projection

As the operator,
I want skills available in every tree my configured adapters read from,
So that running the loop on a non-default agent finds the skills instead of nothing.

**Type:** feature • **Effort:** L • **Deps:** S-6.1 • **FR/AD:** FR-41; AD-12, AD-36
**Surface:** `cli/adapters.py`, `adapters/fs_local.py`

**Acceptance Criteria:**

**Given** configured adapters whose declared skill trees differ from the canonical source tree
**When** projection runs
**Then** each adapter's declared skill tree contains the project's skills afterwards
**And** the mechanism per `(adapter, platform)` is declared in **one table with one owner**; no module branches on platform outside it, and the mechanism used is reported (AD-36)
**And** the **canonical source tree is authoritative**; projected trees are derived and never edited in place (AD-12)
**And** re-projection after a source change converges and removes stale entries
**And** re-projection when nothing changed is a no-op

### Story 6.3: Projection drift detection that can actually fail

As the operator,
I want drift between canonical and projected trees detected,
So that a projection mechanism cannot report clean simply because it is incapable of drifting.

**Type:** feature • **Effort:** S • **Deps:** S-6.2 • **FR/AD:** FR-42; AD-36
**Surface:** `cli/adapters.py`, `core/conformance.py`

**Acceptance Criteria:**

**Given** a projected skill tree
**When** drift detection runs
**Then** it reports added, removed and modified skills per adapter tree
**And** the check is **mechanism-specific**: a link-based projection asserts **link-target identity** — a falsifiable check that can genuinely fail — and emits **no content-drift finding at all**; it never reports `clean` for a check that cannot fail, and it never emits `not-applicable`, which the closed lattice has no member for (AD-36, AD-31)
**And** reporting `clean` for a check that cannot fail is a meta-test failure
**And** it runs as part of preflight whenever a non-default adapter is configured

### Story 6.4: Adapter probe with a machine-scoped record

As the operator,
I want to capture what an adapter actually supports on this machine,
So that portability claims rest on observation rather than on a support table.

**Type:** feature • **Effort:** M • **Deps:** S-6.1 • **FR/AD:** FR-43; NFR-9, NFR-11; AD-31, AD-34, AD-37
**Surface:** `cli/adapters.py`, `adapters/harness_bmadloop.py`, `core/conformance.py`

**Acceptance Criteria:**

**Given** a named adapter
**When** probe runs
**Then** it records binary presence and version, the profile's declared capabilities, and probe output
**And** sensitive values are redacted via the egress serializer, not at the call site (AD-34)
**And** the record is written to the **single declared machine-scoped path** for host-and-adapter facts, not into any project's artifacts (AD-37)
**And** probing an absent adapter reports it as `unavailable` and exits 0 **in this read-only reporting surface only**; the same condition is `unevaluable` anywhere a run depends on it (AD-31)
**And** the harness's 0.9.x pure-JSON probe output shape is covered by a contract test that fails loudly on upstream drift (NFR-9)

### Story 6.5: Conformance smoke in an ephemeral home

As the operator,
I want to drive a canonical smoke story end to end on a named adapter,
So that "it works here" is something I ran, not something I assumed.

**Type:** feature • **Effort:** L • **Deps:** S-6.2, S-6.4, S-2.1 • **FR/AD:** FR-44; AD-13, AD-37
**Surface:** `cli/adapters.py`, `core/conformance.py`

**Acceptance Criteria:**

**Given** an available adapter
**When** the conformance smoke runs
**Then** the smoke story exercises spec read → change → verify → commit and is adapter-agnostic
**And** the result is `pass | fail | unavailable` with the **failing stage named**
**And** it runs in a loop home provisioned `ephemeral: true` — a flag only this command may set — which is **exempt from AD-29's promotion-reachability predicate** and produces no promotable artifact by construction (AD-37, AD-29 — **not** AD-13, whose predicate AD-29 superseded)
**And** the ephemeral home leaves no residue afterwards
**And** an adapter absent from the host reports `unavailable` without failing the command

### Story 6.6: The conformance matrix

As the operator,
I want one dated artifact recording per-adapter conformance,
So that there is exactly one place Marshal makes a portability claim.

**Type:** feature • **Effort:** S • **Deps:** S-6.5 • **FR/AD:** FR-45; SM-6; AD-31, AD-37
**Surface:** `core/conformance.py`, `schemas/conformance.json`

**Acceptance Criteria:**

**Given** accumulated probe and smoke results
**When** the matrix is written
**Then** it holds one row per adapter: status, adapter version, harness version, date, and the failing stage where applicable
**And** status distinguishes **`not-attempted` (no claim made) from `unavailable` (attempted, host lacks it) from `fail` from `pass`** (AD-31)
**And** **SM-6 counts only `pass`** — the metric is not gameable by uninstalled adapters
**And** rows older than a configured age are marked stale
**And** it lives at the **tracked, per-host** path `planning-artifacts/conformance/matrix/<hostname>.md` — reviewable in a PR and present in every clone — and is the **only** place Marshal makes a portability claim (AD-37 as amended 2026-07-30; FR-45's "tracked", NFR-8 and the architecture's Operational envelope all required this, and the machine-scoped reading contradicted all three for the one artifact SM-6 measures)

### Story 6.7: Entry-file family drift check, detect-only

As the operator,
I want cross-tool instruction-file drift reported,
So that I learn about divergence without Marshal editing files whose ownership is unsettled.

**Type:** feature • **Effort:** S • **Deps:** S-1.1 • **FR/AD:** FR-46; C-3; AD-11
**Surface:** `cli/adapters.py`, `core/conformance.py`

**Acceptance Criteria:**

**Given** the configured cross-tool entry-file family
**When** the drift check runs
**Then** it reports presence and mutual consistency, naming the specific divergence
**And** it **does not edit any of the files** — ownership between stations is an open question, and Marshal never edits a shared repo-level file (C-3, AD-11)
**And** the family membership is configuration, not a literal
**And** the check accounts for the fact that instruction content is not isolated per-CLI: one tool applies the union of two files, another reads only one — so a divergence is reported as cross-contaminating, not merely cosmetic

### Story 6.8: Upstream contribution register

As the operator,
I want the gaps that belong upstream tracked as such,
So that a workaround does not quietly become permanent.

**Type:** feature • **Effort:** S • **Deps:** S-1.1 • **FR/AD:** FR-58; AD-2
**Surface:** `cli/adapters.py` (or `cli/upstream.py`), tracked register file

**Acceptance Criteria:**

**Given** the known upstream-shaped gaps
**When** the register is created
**Then** it lists each gap, its Marshal workaround, and its upstream status
**And** initial entries are: idle-strand detection; per-story model tiering; the hard-coded `planning_artifacts` composition; ACP evaluation; non-POSIX multiplexer support
**And** each entry names the Marshal FR that compensates while the gap is open
**And** the register is readable through the standard envelope so it can be surfaced in status or docs
**And** an entry whose upstream status becomes `landed` flags its compensating workaround for removal

---

### Story 6.9: Tool-surface rendering and preflight probe *(added 2026-08-01 — AD-43 / the Q-11 resolution; post-MVP)*

As the operator,
I want the project's MCP tool surface declared in policy and rendered into the loop home,
So that a provisioned home is reproducible in the one respect it currently is not: which tools the agent can call.

**Type:** feature • **Effort:** M • **Deps:** S-1.7, S-6.1 • **FR/AD:** AD-43, AD-37; extends FR-5, FR-49
**Surface:** `cli/init.py` (seed step), `core/policy.py`, `schemas/policy.json`

**Acceptance Criteria:**

**Given** a project policy declaring MCP servers
**When** `marshal init` provisions the home
**Then** a project-scoped `.mcp.json` renders into the home with seed-not-overwrite semantics identical to adapter seeds (Story 1.7's pattern)
**And** preflight probes each declared server's resolvability and names blocking findings
**And** the user-scoped registry is never read as authority and never written
**And** the story is scheduled post-MVP; nothing in Epics 1–5 depends on it

---

## Epic 7: Foundation & the Write Guard

**Goal:** The seed module tree (inside `pyforge-marshal`), the exit-code taxonomy, the single write primitive with its
never-write guard, the manifest schema and loader, the actual V1 model manifest, and the
Copier fit spike. **Nothing else can be built safely until the guard exists** — every
subsequent component assumes writes are already policed.

**Audit note (Phase 1 backlog-truth, 2026-08-10, amended post-blind-review —
`planning-artifacts/implementation-readiness-report-2026-08-10.md`).** All E7-E12 FR/AD
citations were mechanically re-issued this date from the architecture's recorded 2026-08-08
mapping (satellite `FR1..FR62` → `FR-66..FR-127`, `AD-01..15` → `AD-51..65`; 195 references;
the retired `NFR-O1` → `NFR-12` per the PRD's own retirement row; S-12.5's typer/rich AC
re-issued to the *amended* AD-51, which forbids what the original ordered). **The `genesis`
naming contradiction (architecture-internal: the original AD-64/FR-118 vs Part II's
retirement) is RESOLVED — 2026-08-10 correct-course, operator decision: the seed installer
lives INSIDE `pyforge-marshal`.** AD-64 re-issued (no new package; `pyforge.marshal.seed`
subpackage; `marshal seed <verb>` on the shipped tree; templates as package data), FR-118
re-issued, Part II's binding names re-issued (state `.marshal/seed-state.yml`), Story 7.1
re-scoped to the seed module tree + subparser stub, S-12.1's wiring ACs re-issued, and
every E7-E12 story now carries a `Surface:` line. Prose "Genesis" survives only as the
capability's satellite-era name and binds nothing. **The block is dispatchable WITH ONE CROSS-EPIC GATE** (added by the FR-128..163
decomposition, PRD § 16.8): **S-14.1/S-14.2 (pyforge-core leaf + atomic write) land before
S-7.2/S-7.3**, whose ACs would otherwise mint atomic-write copy #21 and lattice copy #6 —
their Deps lines now carry it. Order: 7.1 → (14.1/14.2 →) 7.2/7.3 → 7.6 spike gate →
E8..E12; 8-5 stays correctly blocked on its cross-epic dep (S-10.2).

### Story 7.1: The seed module tree inside pyforge-marshal

As the seed-installer builder,
I want the `pyforge.marshal.seed` subpackage scaffolded inside the existing `pyforge-marshal`
member with the `seed` noun group stubbed on the shipped argparse tree,
So that every later story has a stable, importable home with no new package, no second
binary, and no revival of the retired `genesis` name (re-issued 2026-08-10, correct-course;
amended AD-64/AD-70).

**Type:** infra • **Effort:** S • **Deps:** none • **FR/AD:** AD-64 (as re-issued), AD-70, NFR-C1, NFR-C4
**Surface:** `cli/seed.py`, `seed/__init__.py`, `tests/unit/test_seed_scaffold.py`

**Acceptance Criteria:**

**Given** the existing `pyforge-marshal` workspace member
**When** the developer scaffolds the seed home and runs the member's test task
**Then** `src/pyforge/marshal/seed/` exists with the architecture § 4 module tree as
`__init__.py` stubs (model/, state/, regions/, detect/, plan/, apply/, engine/, derive/,
migrate/, verbs/, templates/)
**And** `marshal seed` registers as a noun-group subparser on the shipped argparse tree
(AD-70) whose verbs report not-implemented cleanly — no new console script, no typer
**And** `import pyforge.marshal.seed` succeeds in the lean `pyforge-marshal` env
**And** the existing suite stays green with one added scaffold smoke test
**And** ruff + pyright are clean on the new tree

> Root-`pixi.toml` wiring (the `copier` dependency, gates, `environment.yaml`) lands in
> S-12.1; this story adds only what imports and tests locally.

### Story 7.2: Error taxonomy and exit codes

As a CI pipeline invoking Genesis,
I want distinct, documented exit codes per failure mode,
So that automation can distinguish "repo is non-conformant" from "you gave me bad arguments"
from "Genesis broke."

**Type:** foundation • **Effort:** XS • **Deps:** S-7.1, S-14.3 (consume pyforge-core's lattice/exception root — PRD § 16.8 gate)• **FR/AD:** FR-126, P-10
**Surface:** `seed/errors.py`, `tests/unit/test_seed_errors.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

> **Cross-epic gate (2026-08-10):** the exception hierarchy and exit-code lattice here CONSUME `pyforge.core` (S-14.3) — building them standalone would mint lattice copy #6.

**Acceptance Criteria:**

**Given** `pyforge.marshal.seed.errors`
**When** any verb fails
**Then** exactly one exception type from a closed hierarchy is raised, each mapped to a
distinct exit code: `0` success · `1` conformance failure (HARD findings) · `2` usage/argument
error · `3` precondition failure (dirty worktree, not a git repo, hand-edited managed content)
· `4` `NeverWriteViolation` · `5` state invalid · `10` internal error
**And** every exception carries a `remedy` string
**And** the exit-code table is asserted by a unit test that enumerates the hierarchy, so
adding an exception without a code fails the build
**And** no module raises a bare `Exception` or `SystemExit` outside `cli.py`

### Story 7.3: The `fs` write primitive and the never-write guard

As the Genesis architecture,
I want every byte written to a target repo to pass through one guarded primitive,
So that the never-write set (Tier-0 Dreams, Tier-2 planning artifacts, Tier-3, legacy specs,
BMAD installer files) is structurally unreachable rather than merely policy.

**Type:** foundation • **Effort:** M • **Deps:** S-7.2, S-14.2 (consume pyforge-core's atomic write — PRD § 16.8 gate)• **FR/AD/P:** FR-71, FR-100, AD-61,
NFR-R4, P-01
**Surface:** `seed/fs.py`, `tests/unit/test_seed_fs.py`, `tests/meta/` (never-write proof) — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

> **Cross-epic gate (2026-08-10):** `fs.write()`'s atomic write-temp+rename CONSUMES `pyforge.core` (S-14.2) — implementing it locally would mint copy #21.

**Acceptance Criteria:**

**Given** an orchestrator constructed with a frozen `NeverWrite` path set
**When** any code calls `fs.write()`, `fs.replace_span()`, or `fs.remove()`
**Then** the target path is resolved to an absolute, **symlink-resolved** form *before* any
file handle is opened
**And** a path matching the never-write set raises `NeverWriteViolation` (exit 4) with the
matched rule in the message
**And** the symlink case is explicitly covered: writing through
`_bmad-output/planning-artifacts` (a symlink into `projects/<slug>/planning-artifacts`) is
**blocked**, proving unresolved matching would have missed it
**And** the `NeverWrite` set is immutable after construction (mutation attempt raises)
**And** `fs` imports nothing from the package except `errors`
**And** `fs.write()` is atomic (write-temp + rename) so an interrupted write cannot truncate
an existing file

### Story 7.4: Manifest schema, loader, and model-version ranges

As the Genesis engine,
I want the model declared as validated data addressed by stable artifact ids,
So that adding a model artifact never requires an engine code change.

**Type:** foundation • **Effort:** M • **Deps:** S-7.2 • **FR/AD/P:** FR-66, FR-67, FR-68, FR-70,
FR-71, AD-55, A-02, A-05, NFR-M1, P-11
**Surface:** `seed/model/manifest.py`, `seed/model/version.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** `templates/manifest.yaml`
**When** the loader parses it
**Then** each entry validates against a schema requiring: `id` (stable, unique), `class`
(one of `referenced` / `copied-managed` / `copied-seeded` / `generated-derived` /
`hybrid-managed-region` / `unclassified-deferred`), `path` (jinja-templated on slug),
`applies_to` (`init` / `adopt` / `both`), and `rationale`
**And** hybrid entries additionally require `format` and `regions[]` each with `name` and
ordered `anchor[]`
**And** referenced entries require `pin` (a version range)
**And** entries may carry `since` / `until` model-version bounds, and the loader filters by
the bundled model version
**And** entries may carry `legacy_of: <artifact-id>`
**And** the manifest declares the `never_write[]` path set consumed by S-7.3
**And** duplicate ids, unknown classes, or a hybrid entry without regions are load-time
errors, not runtime surprises
**And** model semver parsing/comparison is covered including pre-release ordering

### Story 7.5: The V1 extraction manifest (the model, as data)

As an adopting repository,
I want the operating model declared completely and correctly,
So that what Genesis installs is exactly the model this repo proved.

**Type:** content • **Effort:** L • **Deps:** S-7.4 • **FR/AD:** FR-66, FR-71, FR-118, PRD
**Surface:** `seed/templates/manifest.yaml`, `seed/model/artifact.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)
§ Extraction Manifest

**Acceptance Criteria:**

**Given** the PRD's extraction manifest
**When** `templates/manifest.yaml` and `templates/files/` are authored
**Then** every artifact named in PRD § *The V1 manifest* has an entry with the class the PRD
assigns it — REFERENCED (bmad-method ≥6.10.0, bmad-loop ≥0.8.1, copier ≥9.17<10, pixi
≥0.72.2, tmux ≥3.7b, BMAD installer dirs), COPIED·MANAGED (`bmad-switch`,
`bmad-loop-worktree`, the detector, `docs/dreams/README.md`, the CI workflow, the
`.gitignore` model region), COPIED·SEEDED (starter Dream, `.bmad-config.toml`,
`_bmad/custom/config.toml`, `.bmad-loop/policy.toml`, `specs/README.md`, deck scaffolding),
GENERATED·DERIVED (the four adapter files, `PROJECTS.md` rows, the two symlinks, directory
skeletons), HYBRID (`AGENTS.md` × 3 regions, `CLAUDE.md` × 2, `.gitignore` × 1, optional
`README.md` badge)
**And** `.claude/skills/**`, `pixi.toml` task blocks, and `library-llms-full.md` are present
as `unclassified-deferred` with a rationale
**And** the never-write set covers `docs/dreams/*.md` (except the init seed),
`**/planning-artifacts/**` (except the init-seeded `specs/README.md`),
`**/implementation-artifacts/**`, `docs/specs/*.md`, `_bmad/bmm/**`, `_bmad/core/**`
**And** template bodies render the tier table, portability contract, and Dream-first workflow
faithfully to `AGENTS.md`
**And** the manifest loads clean and passes the coverage check from S-9.5
**And** initial `model_version` is `1.0.0`

### Story 7.6: Spike-0 — Copier API fit (CRITICAL GATE)

As the Genesis architect,
I want the five load-bearing Copier behaviors proven on 9.17 before E10 is built,
So that a wrong assumption changes the design now rather than after seven stories depend on it.

**Type:** spike • **Effort:** S • **Deps:** S-7.1 • **FR/AD:** AD-52, AD-54, A-04, FR-120
**Surface:** `seed/engine/copier.py` under `src/pyforge/marshal/`; spike report in marshal planning-artifacts

**Acceptance Criteria:**

**Given** a throwaway template and a temp destination
**When** the spike runs against `copier` 9.17
**Then** `run_copy(..., pretend=True)` performs **zero writes** and returns a usable result
**And** `skip_if_exists` preserves a pre-existing file while creating its siblings
**And** `data=` combined with `defaults=True` fully suppresses interactive prompting
**And** the answers-file path is template-configurable to `.marshal/.copier-answers.yml`
(**if not**, AD-52's fallback triggers and the finding is recorded in the story's dev notes)
**And** `run_update` with `vcs_ref` orders correctly against PEP 440 tags
**And** the spike's findings are written into the story record; any failure raises a
`correct-course` before E10 begins
**And** the spike code is discarded — it is not shipped

---

## Epic 8: The Managed-Region Engine

**Goal:** The one genuinely bespoke algorithm in the product — marker-delimited spans inside
repo-owned files. Built early and tested hardest because AR-1 (region corruption) is the
project's top risk and K-01 (managed-region merge proves unreliable) is a stated kill
criterion.

### Story 8.1: Marker grammar and the per-format registry

As a model artifact in any file format,
I want one canonical marker grammar rendered in the right comment syntax,
So that regions are unambiguous, greppable, and self-describing.

**Type:** foundation • **Effort:** S • **Deps:** S-7.4 • **FR/AD:** FR-108, FR-110, AD-53
**Surface:** `seed/regions/markers.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the marker grammar
`<open> marshal-seed:begin region=<name> model-version=<semver> sha=<8-hex> <close>` and its
matching `marshal-seed:end`
**When** a region is rendered for a given file
**Then** the comment style is selected from the registry by the artifact's declared `format`
(**never sniffed** from content): `html` (`<!-- … -->`) for `.md`; `hash` (`# …`) for
`.gitignore`, `.toml`, `.yml`, `.yaml`, shell
**And** `slashstar` is registered but unused in V1 and raises `NotImplementedError` if selected
**And** `sha` covers the **region body only**, so the marker line is not self-referential
**And** a round-trip test proves render → parse → render is byte-identical for every
registered format
**And** an artifact declaring a format not in the registry is a manifest load error (S-7.4)

### Story 8.2: Region parser — span discovery, nesting rejection, fence awareness

As the detect stage,
I want to locate every managed region in a file precisely and refuse malformed ones,
So that substitution operates on a span that is provably correct.

**Type:** foundation • **Effort:** M • **Deps:** S-8.1 • **FR/AD/P:** FR-113, AD-53, P-06
**Surface:** `seed/regions/parse.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a file containing zero or more managed regions
**When** the parser runs
**Then** it returns, per region: name, model-version, declared sha, body byte-span, and
marker byte-spans
**And** **nested** regions (a begin inside an open region) are a hard error naming both
regions
**And** **overlapping** regions (interleaved begin/end) are a hard error
**And** an unterminated begin marker is a hard error
**And** a duplicate region name in one file is a hard error
**And** markers appearing inside a fenced code block (``` or ~~~) in a markdown file are
**ignored** — proven by a test where a fence contains a literal marker
**And** files with CRLF line endings parse identically to LF
**And** the parser performs no I/O — it takes text and returns spans (P-03 support)

### Story 8.3: Span substitution — the update primitive

As `marshal seed update`,
I want to replace a region's body by pure byte-span substitution,
So that a half-merged or conflict-marked file is not representable.

**Type:** foundation • **Effort:** M • **Deps:** S-8.2, S-7.3 • **FR/AD/P:** FR-109, NFR-R3,
P-06, P-01
**Surface:** `seed/regions/apply.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a file with a managed region and new body content
**When** `regions.apply` substitutes it
**Then** only the bytes between the markers change; **every byte outside the span is
identical** (asserted by comparing the prefix and suffix byte-for-byte)
**And** the begin marker's `model-version` and `sha` are updated to the new values
**And** the operation writes through `fs.replace_span()` — never `Path.write_text` (P-01)
**And** no code path can emit `<<<<<<<`, `=======`, or `>>>>>>>` — asserted by a test that
substitutes content deliberately containing conflict-marker-like text and confirms it is
written literally
**And** the file's original trailing-newline state is preserved
**And** substitution on a file whose region sha does not match the caller's expectation raises
rather than silently overwriting (the guard is evaluated in detect per P-07; this is the
belt-and-braces assertion)

### Story 8.4: Anchor resolution and region insertion

As `marshal seed adopt`,
I want to insert a region into a pre-existing file at a declared anchor,
So that a team's `CLAUDE.md` gains the model content without Genesis guessing at structure.

**Type:** feature • **Effort:** M • **Deps:** S-8.2, S-8.3 • **FR/AD:** FR-111, AD-56
**Surface:** `seed/regions/apply.py`, `seed/regions/parse.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a hybrid artifact with an ordered `anchor[]` of literal line-prefix matchers
**When** the region is absent from the target file
**Then** insertion occurs immediately after the **first** matching anchor line
**And** when no anchor matches, the region is **appended at end of file** preceded by a blank
line
**And** anchors are matched only outside fenced code blocks
**And** the special anchor `<top>` inserts after any YAML frontmatter block, or at byte 0 when
there is none
**And** Genesis never infers structure beyond these literal matchers
**And** the chosen anchor (or the append fallback) is **named in the plan** so a reviewer can
veto placement before apply
**And** inserting into a file that already has the region is a no-op that reports
`already-present` (idempotence, AD-60)
**And** insertion into an absent file creates it with only the region and a minimal header

### Story 8.5: Marker deletion as a sanctioned opt-out

As a repo maintainer who rejects a model convention,
I want deleting the markers to be a permanent, greppable opt-out,
So that I can diverge deliberately without fighting the tool every update.

**Type:** feature • **Effort:** S • **Deps:** S-8.4, S-10.2 • **FR/AD:** FR-112, AD-58
**Surface:** `seed/regions/parse.py`, `seed/state/store.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a repo where a previously-present managed region's markers have been deleted
**When** `marshal seed check` or `marshal seed adopt` runs
**Then** the region is classified `opted-out`, **not** `managed-region-missing`
**And** the opt-out is recorded in state so later runs do not reinsert it
**And** `check` reports it at **INFO** severity (never HARD or DRIFT)
**And** `--reinstate <artifact>#<region>` clears the opt-out and reinserts on the next apply
**And** the distinction is proven by two tests: markers deleted (⇒ opted-out) vs. file never
had the region and state has no record (⇒ missing, will be inserted)

---

## Epic 9: Detect & Plan

**Goal:** The pure, side-effect-free half of the pipeline — walk a repo, classify every
artifact, hash what is managed, and emit a reviewable plan. `check` is nothing more than this
epic plus a renderer, so E9 completing means the product's read-side is done.

### Story 9.1: Findings model — severity, types, remedies

As a CI pipeline,
I want every conformance problem expressed as a typed finding with a documented remedy,
So that failures are actionable without reading Genesis's source.

**Type:** foundation • **Effort:** S • **Deps:** S-7.2 • **FR/AD/P:** FR-90, AD-54, NFR-M3, P-10
**Surface:** `seed/detect/findings.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** `detect/findings.py`
**When** any check produces a finding
**Then** it is a `Finding(severity, type, path, message, remedy)` with severity from the ladder
`HARD` / `DRIFT` / `INFO` (design borrowed from `bmad_drift_check.py`, **not imported or
vendored** — AD-54)
**And** finding types are a closed enum covering at minimum: `artifact-missing`,
`managed-file-modified`, `managed-region-modified`, `managed-region-missing`, `derived-stale`,
`model-behind`, `state-invalid`, `never-write-violation`, `referenced-dep-missing`,
`uncovered`, `legacy-present`, `opted-out`
**And** every enum member has a non-empty remedy string, asserted by a test that iterates the
enum
**And** adding a member without a remedy fails the build
**And** findings serialize to stable JSON for `--json`

### Story 9.2: Repo inventory walker and artifact classification

As `marshal seed adopt`,
I want each manifest artifact classified against the target repo,
So that the plan reflects what is actually there rather than what the model assumes.

**Type:** feature • **Effort:** M • **Deps:** S-7.4, S-8.2, S-9.1 • **FR/AD/P:** FR-80, P-03
**Surface:** `seed/detect/inventory.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a manifest and a target repo
**When** detect runs
**Then** each artifact is classified `absent`, `present-conformant`, `present-divergent`, or
`present-legacy`
**And** classification is **pure**: no writes, no network, no mutation of inputs — asserted by
running detect against a read-only filesystem mount (or an equivalent write-blocking fixture)
**And** the repo tree is walked **once**, with results cached for the run (NFR-P1/P2)
**And** `.git/`, `node_modules/`, `.pixi/`, and gitignored paths are excluded from the walk
except where an artifact explicitly targets them
**And** detect works on a repo missing `.marshal/` entirely (first-ever adopt)
**And** detect returns a structure sufficient for both plan building and finding emission —
no second pass required

### Story 9.3: Content hashing for managed files and regions

As the update path,
I want a precise signal that a tool-owned artifact was hand-edited,
So that Genesis refuses rather than silently overwriting a human's change.

**Type:** feature • **Effort:** S • **Deps:** S-9.2, S-8.2 • **FR/AD/P:** FR-106, FR-86, P-07
**Surface:** `seed/detect/hashes.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a managed file or managed region recorded in state with a body sha
**When** detect hashes the current content
**Then** a mismatch yields `managed-file-modified` / `managed-region-modified` at HARD severity
**And** hashing normalizes line endings so a CRLF checkout does not false-positive
**And** region hashing covers the body only (consistent with S-8.1)
**And** hash checks happen **in detect, never in apply** (P-07) — asserted by a meta-test that
finds no hash comparison in `apply/`
**And** an artifact present in the repo but absent from state (adopted out-of-band) is
classified `present-divergent`, not silently accepted

### Story 9.4: Legacy convention detection

As a repo with a superseded-but-live convention,
I want it recognized, recorded, and left completely alone,
So that adopting the model never destroys work still in flight.

**Type:** feature • **Effort:** S • **Deps:** S-9.2 • **FR/AD:** FR-81, AD-59
**Surface:** `seed/detect/inventory.py`, `seed/detect/findings.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a manifest entry carrying `legacy_of: <successor-artifact-id>`
**When** detect finds the legacy artifact present
**Then** it is classified `present-legacy` and recorded in `state.legacy[]`
**And** it is added to the effective never-write set for the run — no plan action may target it
**And** `check` emits `legacy-present` at **INFO** naming the successor, never HARD or DRIFT
**And** the canonical case is covered by test: `docs/specs/*.md` present ⇒ preserved, recorded,
successor named as Tier-2 planning-artifacts
**And** no automated Tier-1 → Tier-2 migration is attempted (explicitly out of V1)

### Story 9.5: Manifest coverage check

As the Genesis maintainer,
I want an unclassified artifact to be a build failure,
So that the model's coverage cannot silently lapse the way undocumented conventions do.

**Type:** feature • **Effort:** S • **Deps:** S-7.5, S-9.1 • **FR/AD:** FR-69, SC-10
**Surface:** `seed/detect/inventory.py`, `seed/model/manifest.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the loaded manifest
**When** the coverage check runs
**Then** every artifact carries **exactly one** class
**And** an artifact with no class, or with a class outside the enum, produces an `uncovered`
HARD finding
**And** `unclassified-deferred` counts as covered **only** when it carries a rationale — a bare
deferral fails
**And** the check runs in Genesis's own test suite so a manifest edit that drops coverage fails
CI (this mirrors `bmad_drift_check.py`'s `uncovered` HARD finding — the design that made
coverage lapse impossible in this repo)
**And** the check reports coverage counts per class for the report renderer

### Story 9.6: Plan and Action types, repo fingerprint, and the plan builder

As a human reviewing a change before it happens,
I want the plan to be a complete, serializable, self-validating artifact,
So that "review then apply" is a real gate rather than a printed summary.

**Type:** feature • **Effort:** M • **Deps:** S-9.2, S-9.3, S-9.4 • **FR/AD/P:** FR-82, AD-57,
NFR-12, P-04, P-05
**Surface:** `seed/plan/types.py`, `seed/plan/build.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a detect result
**When** the plan builder runs
**Then** it emits a `Plan` dataclass serializable to `.marshal/plan.json`
**And** every `Action` names: artifact id, class, current state, target state, target path,
chosen anchor (where applicable), and a rationale string (P-05)
**And** the plan carries a `repo_fingerprint` = git HEAD + dirty flag + per-artifact content
hashes for every artifact it names
**And** an empty plan (zero actions) is a first-class, valid result — the idempotence signal
(AD-60)
**And** the plan is round-trippable: serialize → load → identical
**And** the plan file is written to `.marshal/plan.json` and is covered by the model's own
`.gitignore` region; `--plan-out <path>` redirects it
**And** actions are ordered deterministically (by artifact id) so two runs produce identical
plan bytes

---

## Epic 10: Materialize & the Core Verbs

**Goal:** Add writes. The Copier seam, the apply runner, the state store, the preconditions,
and then the three verbs in dependency order — `check` (no writes), `adopt` (writes), `init`
(adopt against an empty target). **Gated on S-7.6 (Spike-0).**

### Story 10.1: Copier engine wrapper — the single seam

As the Genesis architecture,
I want exactly one module that knows Copier exists,
So that the engine can be version-bumped or replaced behind one boundary and the
public-API-only rule is enforceable.

**Type:** foundation • **Effort:** M • **Deps:** S-7.6, S-7.3 • **FR/AD/P:** FR-118, FR-119, FR-120,
FR-121, FR-101, NFR-S1, NFR-S3, A-04, P-02
**Surface:** `seed/engine/copier.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** `engine/copier.py`
**When** materialization is requested
**Then** the module exposes a Genesis-internal `MaterializeRequest` → result API; callers never
see Copier types
**And** it calls only `run_copy`, `run_update`, `run_recopy` with documented kwargs — no
`Worker` attribute access, no private-module imports (asserted by S-12.4's import test)
**And** `copier` is imported in **this module only** (P-02)
**And** in-package templates are the default source; `--template <path|url>` overrides (FR-119)
**And** Copier's code-executing template features are reachable only with `--unsafe` (FR-121,
NFR-S1)
**And** `--force` maps to `run_recopy` and requires explicit confirmation (FR-101)
**And** a template that attempts to write outside its manifest-declared paths is rejected
(NFR-S3) — Copier's output is reconciled against the plan before any byte is committed
**And** all writes still route through `fs` (P-01), not Copier's own filesystem access, or the
story documents precisely how Copier's writes are fenced into a staging dir and then applied
through `fs`

### Story 10.2: State schema and the atomic store

As Genesis across runs,
I want a schema-validated, tool-owned state file written last and atomically,
So that the repo and its state can never disagree — the failure mode that cost this repo ten
hours with the `bmad-switch` marker.

**Type:** foundation • **Effort:** M • **Deps:** S-7.3 • **FR/AD/P:** FR-102, FR-103, FR-104, FR-105,
FR-106, FR-107, AD-52, AD-58, P-08
**Surface:** `seed/state/schema.json`, `seed/state/store.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** `.marshal/seed-state.yml`
**When** state is written
**Then** it contains `model_version`, `seed_model_version`, `adopted_at`, `last_update`, `mode`,
`agents[]`, `managed[]` (id, path, class, body_sha, inserted_region_span), `skips[]`,
`legacy[]`, `migrations_applied[]`, `opted_out[]`
**And** it carries a prominent do-not-hand-edit header
**And** it validates against `state/schema.json` on every read; an invalid file produces
`state-invalid` (exit 5), **never a traceback** (FR-104)
**And** it is git-tracked (FR-107) and **not** in the model's gitignore region
**And** it is written **last**, after all file writes succeed, in one atomic replace (P-08) —
asserted by a fault-injection test that fails a mid-apply write and confirms state is unchanged
**And** Copier's answers file is treated as opaque: Genesis never reads or hand-edits it
(FR-105), and answers are re-supplied from Genesis state via `data=` on every Copier call
**And** `managed[]` records enough for a future `eject` (AD-58) — asserted by a test that
reconstructs the removal set from state alone

### Story 10.3: The apply runner — transactional, guarded

As a repo owner,
I want apply to either complete or leave nothing behind,
So that an interrupted install never leaves a half-configured repo.

**Type:** feature • **Effort:** M • **Deps:** S-10.1, S-10.2, S-8.3, S-9.6 • **FR/AD/P:** FR-83,
NFR-R1, NFR-S3, P-04, P-07
**Surface:** `seed/apply/run.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a `Plan` and a matching repo
**When** apply runs
**Then** it consumes **only** the plan and never re-derives state (P-04)
**And** it refuses a plan whose `repo_fingerprint` no longer matches the repo (AD-57) with a
`stale-plan` precondition error (exit 3)
**And** every write goes through `fs` (P-01)
**And** apply performs **no** hash comparisons — it trusts detect (P-07)
**And** on any failure mid-run, all completed writes are reverted and state is untouched
(NFR-R1) — asserted by fault injection at three different action indices
**And** actions execute in the plan's deterministic order
**And** apply is a no-op on an empty plan and exits 0

### Story 10.4: Preconditions, refusals, and skips

As a repo owner,
I want Genesis to refuse loudly in the situations where it could do harm,
So that git remains a complete undo and no hand-edit is ever silently discarded.

**Type:** feature • **Effort:** S • **Deps:** S-10.3, S-9.3 • **FR/AD:** FR-85, FR-86, FR-87,
NFR-R2, SC-04, SC-05
**Surface:** `seed/apply/run.py`, `seed/verbs/` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a mutating verb invoked with `--apply` / `--run`
**When** preconditions are evaluated
**Then** running outside a git repository is refused (exit 3)
**And** running on a **dirty worktree** is refused (exit 3) — SC-05
**And** a hand-edited managed file or managed region causes refusal with the specific artifact
and region named, unless `--force` (exit 3) — SC-04
**And** `--skip <glob>` records the pattern in `state.skips[]` and is honored on every
subsequent run (FR-87)
**And** skipped artifacts appear in the plan as `skipped` actions with the matching pattern
named, so a skip is visible rather than invisible
**And** dry-run invocations bypass the clean-worktree requirement (reading is always safe)
**And** each refusal message states the remedy (P-10)

### Story 10.5: `marshal seed check`

As a CI pipeline,
I want a read-only conformance verb with a non-zero exit,
So that a repo cannot silently drift from the model it installed.

**Type:** feature • **Effort:** M • **Deps:** S-9.6, S-9.1, S-10.2 • **FR/AD:** FR-88, FR-89,
FR-90, FR-91, FR-92, FR-93, NFR-P1
**Surface:** `seed/verbs/check.py`, `cli/seed.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** an adopted repo
**When** `marshal seed check` runs
**Then** it performs detect + plan and **never writes** — including not writing state, not
writing `plan.json`, and not creating `.marshal/` (FR-88), asserted against a write-blocking
fixture
**And** it exits non-zero on any HARD finding; `--strict` additionally fails on DRIFT (FR-89)
**And** `--json` emits the full findings report, stable and CI-annotatable (FR-91)
**And** it reports the repo's `model_version` against the bundled model version as
`model-behind` / current / ahead (FR-92)
**And** it completes in **< 5 s** on a `local-recipes`-sized repo (NFR-P1), asserted by a timed
test
**And** it runs correctly on a repo that has never been adopted (reports every artifact absent
rather than erroring)
**And** the human-readable report groups findings by severity with counts, in the shape of
`bmad_drift_check.py`'s report

### Story 10.6: `marshal seed adopt`

As a team with a working repository,
I want the model layered on without disturbing what already runs,
So that adoption is a reviewable, revertible, and repeatable operation.

**Type:** feature • **Effort:** L • **Deps:** S-10.3, S-10.4, S-10.5, S-8.4 • **FR/AD:** FR-79,
FR-80, FR-81, FR-82, FR-83, FR-84, FR-87, AD-60
**Surface:** `seed/verbs/adopt.py`, `cli/seed.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** an existing repository
**When** `marshal seed adopt` runs with no flags
**Then** it is **dry-run**: a plan is written and printed, and no repo file changes (FR-79)
**And** `--apply` executes the plan; `--yes` executes without interactive confirmation
(unattended/CI use)
**And** artifacts already present are preserved unless their class is `copied-managed` or
`generated-derived` (FR-83)
**And** `present-legacy` artifacts are preserved and recorded, never modified (FR-81)
**And** a **second** `adopt` on an unchanged repo produces an **empty plan and writes nothing**
(FR-84, SC-03, AD-60)
**And** `--agents <list>` adds adapters idempotently on a repo already adopted (FR-116 support)
**And** the end-to-end journey from PRD J2 is covered by an integration test: a repo with an
existing `CLAUDE.md` and a legacy convention adopts cleanly, its build-relevant files
untouched

### Story 10.7: `marshal seed init`

As a maintainer starting a new project,
I want a complete Dream-first repository in one command,
So that day zero already has the tiers, the contract, the wiring, and a Dream to write into.

**Type:** feature • **Effort:** M • **Deps:** S-10.6 • **FR/AD:** FR-72, FR-73, FR-74, FR-75, FR-76,
FR-77, FR-78
**Surface:** `seed/verbs/init.py`, `cli/seed.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** an empty target directory
**When** `marshal seed init <path> --slug <slug> --agents claude,cursor` runs
**Then** every manifest artifact whose `applies_to` includes `init` is materialized
**And** `docs/dreams/<slug>.md` is seeded with valid Tier-0 frontmatter (`title`, `type: dream`,
`owner`, `status: seeded`) — and it is the **only** Dream written (FR-74)
**And** `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}`,
`.bmad-config.toml`, `planning-artifacts/specs/README.md`, and `PROJECTS.md` with the first row
are created (FR-75)
**And** the `.gitignore` model region covers `_bmad-output/projects/*/implementation-artifacts/`,
the two `_bmad-output` compatibility symlinks, `_bmad/custom/.active-project`,
`.bmad-loop/{runs,cache}/`, and `_bmad-output/projects/*/.bmad-config.user.toml` (FR-76)
**And** state records `mode: init` plus both versions, agents, and per-artifact hashes (FR-77)
**And** init into a **non-empty** directory is refused unless `--force`, with the message
directing the user to `adopt` (FR-78)
**And** `marshal seed check` on the fresh repo is green
**And** init runs the same `resolve → detect → plan → apply` pipeline as adopt — asserted by a
test that init produces a plan artifact identical in shape

### Story 10.8: Manifest-declared writable artifacts are exempt from their own never-write collision

As a maintainer running `init` or `adopt`,
I want a manifest entry the extraction manifest itself marks writable to actually be writable,
So that `init` and `adopt` are not refused by the same guard that is supposed to let them write
their own seeded files.

**Type:** fix • **Effort:** S • **Deps:** S-10.6 • **FR/AD:** AD-61 (corrected 2026-08-21)
**Surface:** `seed/detect/inventory.py::effective_never_write`, `seed/verbs/adopt.py`,
`seed/verbs/init.py` — all under `src/shared/packages/pyforge-marshal/`

**Why this exists.** Found live during Story 10.7's own implementation, independently
verified: `docs/dreams/*.md` and `**/planning-artifacts/**` are `never_write` patterns, but
the manifest also declares `dreams-readme` (`docs/dreams/README.md`) and `specs-readme`
(`.../planning-artifacts/specs/README.md`) as `copied-managed` artifacts every `init`/`adopt`
run must be able to write — both patterns the extraction manifest's own rationale table always
named as intentional exceptions (`extraction-manifest.md`), a clause AD-61's original text
never carried. `check_preconditions` refuses the ENTIRE plan atomically the instant it sees
either action, leaving the target directory untouched: `marshal seed init` cannot complete a
single real invocation today, and the already-shipped `marshal seed adopt --apply` (Story
10.6) fails identically against any target repo missing one of those two files.

**Acceptance Criteria:**

**Given** the manifest declares an artifact as `copied-managed` or `copied-seeded` whose
resolved path also matches a `never_write` pattern, and whose `applies_to` includes the verb
being run
**When** `effective_never_write` (or its call site) constructs the guard set
**Then** that artifact's resolved path is excluded from the set — never in the set to begin
with, not special-cased at the refusal site — so rung 4 of `check_preconditions` does not fire
on it
**And** a legacy artifact's path (`inventory.legacy`, AD-59) is NOT exempted this way even if
it happens to also be a manifest-declared writable path at the same location — legacy still
wins
**And** `marshal seed init <empty-dir> --slug test` completes against the REAL packaged
manifest (not a synthetic test fixture) and `marshal seed check` on the result is green
**And** `marshal seed adopt --apply --yes` against a plain git repo missing both
`docs/dreams/README.md` and `.../planning-artifacts/specs/README.md` completes and writes both
**And** every other `never_write` pattern still refuses normally — this exempts named manifest
entries only, never widens a glob

**Deps:** S-10.6 (fixes an already-merged defect in it). Unblocks the resumption of S-10.7,
whose own preserved implementation (`marshal/story-10-7-seed-init` branch) does not need to
change once this lands.

---

## Epic 11: Derive, Migrate & Update

**Goal:** The generated class and the upgrade path — the reason the whole architecture exists.
After this epic an installed repo can take a later model version through a reviewable plan and
version-ordered migrations, with Tier-0/Tier-2 structurally unreachable.

### Story 11.1: Neutral contract and agent-adapter fan-out

As four different coding agents,
I want one contract rendered into whichever entry file I read,
So that the four adapter files cannot drift from each other or from `AGENTS.md`.

**Type:** feature • **Effort:** M • **Deps:** S-7.5, S-8.4 • **FR/AD:** FR-114, FR-115, FR-116, FR-117,
AD-63, NFR-M1
**Surface:** `seed/derive/adapters.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** one jinja source for the neutral contract (tier table, portability contract,
Dream-first workflow)
**When** the derive stage runs
**Then** `.cursor/rules/specs.mdc`, `GEMINI.md`, and `.github/copilot-instructions.md` are
generated as **whole files** (`generated-derived`), each wrapping the same contract in its
tool-specific framing (FR-115)
**And** `AGENTS.md` and `CLAUDE.md` receive the contract as **managed regions**, never by
overwrite (FR-117)
**And** the contract has exactly one source in the manifest (FR-114) — asserted by a test that
mutates the source and confirms all four outputs change
**And** derived output is deterministic: two runs produce byte-identical files
**And** adapter selection is per-repo, recorded in `state.agents[]`, and extensible by adding a
manifest entry plus a wrapper template with **no engine change** (FR-116, NFR-M1) — asserted by
adding a fifth dummy adapter in a test
**And** the tier table rendered into `GEMINI.md` matches the tier table rendered into
`AGENTS.md` semantically (same tiers, same paths, same git dispositions)

### Story 11.2: `PROJECTS.md` index and artifact-symlink derivation

As a multi-project repo,
I want the project index and the two BMAD artifact symlinks derived from what actually exists,
So that the index cannot go stale and the marker/symlink desync cannot recur.

**Type:** feature • **Effort:** S • **Deps:** S-11.1 • **FR/AD:** FR (generated-derived class),
AD-63
**Surface:** `seed/derive/projects_index.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a repo with N `_bmad-output/projects/*/.bmad-config.toml` files
**When** the derive stage runs
**Then** `PROJECTS.md`'s Projects table has exactly N rows, one per project, with slug,
status, and description read from each `.bmad-config.toml`
**And** hand-written prose elsewhere in `PROJECTS.md` is preserved — only the table region is
derived
**And** the two `_bmad-output/{planning,implementation}-artifacts` symlinks are ensured to
exist, point at the active project, and be covered by the gitignore region
**And** a symlink pointing at a **different** project than the `.active-project` marker
produces a HARD finding naming both — the desync that cost this repo ten hours becomes a
detectable, named condition
**And** derive never writes into `projects/*/planning-artifacts/**` (never-write set)

### Story 11.3: Migration registry and runner

As an installed repo,
I want breaking model changes absorbed by ordered, once-only migrations,
So that a model upgrade is a scripted operation rather than a manual chore in every repo.

**Type:** feature • **Effort:** M • **Deps:** S-10.3, S-10.2 • **FR/AD/P:** FR-96, FR-97, AD-62,
SC-07, P-12
**Surface:** `seed/migrate/registry.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** migration modules registered with `from_version` / `to_version`
**When** the runner computes the chain from `state.model_version` to the bundled model version
**Then** migrations are selected in **semver order** and composed into a single `Plan`
**And** each migration is a **pure function** `(RepoView, State) -> Plan` that performs no
writes (P-12) — asserted against a write-blocking fixture
**And** applied migrations are appended to `state.migrations_applied[]` and **never re-run**
(FR-96) — asserted by running update twice
**And** a migration targeting a `copied-seeded` artifact emits an **offer** action that apply
skips unless `--include-seeded` is passed (FR-97)
**And** a migration targeting a never-write path fails at plan time, not apply time
**And** **SC-07 is proven**: a simulated model v1 → v2 breaking change (a tier-table rule
change plus a renamed managed artifact) is absorbed in a fixture repo with **zero manual
edits**, and `marshal seed check` is green afterward
**And** a gap in the migration chain (no path from the repo's version to the bundled version)
is a clear error naming the missing step

### Story 11.4: `marshal seed update` — two-phase

As a maintainer taking a model upgrade,
I want a plan I can review and then apply,
So that an upgrade to my repo's governance is never a surprise.

**Type:** feature • **Effort:** M • **Deps:** S-11.3, S-11.1, S-8.3 • **FR/AD:** FR-94, FR-98,
FR-99, FR-100, FR-101, SC-01
**Surface:** `seed/verbs/update.py`, `seed/migrate/registry.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** a repo behind the bundled model version
**When** `marshal seed update` runs with no flags
**Then** a plan is written naming every migration and every file action, and **nothing is
changed** (FR-94)
**And** `--run` applies the plan
**And** `copied-managed` files are regenerated wholesale and `generated-derived` files are
recomputed, after detect's hash guards pass (FR-98)
**And** only the marked span of `hybrid-managed-region` files is replaced (FR-99)
**And** `copied-seeded` artifacts are untouched unless `--include-seeded`
**And** an attempted write to the never-write set is a hard error (FR-100) — see S-12.4 for the
standing proof
**And** `--force` maps to `run_recopy` with explicit confirmation (FR-101)
**And** the PRD J3 journey is covered end to end: `check` reports `model-behind` → `update`
plans → `--run` applies → Dreams/PRDs/epics byte-identical before and after → `check` green
(this is **SC-01**'s mechanical half)

### Story 11.5: Referenced-dependency verification and Doctor delegation

As an adopting repo,
I want Genesis to tell me which required tools are missing or below floor,
So that the model's machinery is not installed into an environment that cannot run it.

**Type:** feature • **Effort:** S • **Deps:** S-10.5 • **FR/AD:** FR-95, PRD § Boundaries
**Surface:** `seed/verbs/check.py` (Doctor delegation seam) — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the manifest's REFERENCED entries with their pins
**When** `check` or `update` runs
**Then** each dependency's presence and version floor is verified (bmad-method ≥6.10.0,
bmad-loop ≥0.8.1, copier ≥9.17<10, pixi ≥0.72.2, tmux ≥3.7b)
**And** a missing or below-floor dependency yields `referenced-dep-missing` at **DRIFT**
severity (not HARD — the repo is still conformant, the machine is not ready)
**And** Genesis **never installs** any referenced dependency (FR-95)
**And** the probe is minimal and self-contained — it works in a repo that has **not** adopted
`pyforge-doctor`
**And** when `doctor` is available on PATH, Genesis delegates and reports Doctor's findings
rather than duplicating them, marking them as such in the report
**And** the probe makes no network calls

### Story 11.6: `marshal seed explain` and `marshal seed version`

As an agent reading this repo,
I want the model to describe its own rules,
So that the conventions are queryable rather than only narrated in prose.

**Type:** feature • **Effort:** S • **Deps:** S-7.4, S-10.2 • **FR/AD:** FR-125, FR-127, D1
**Surface:** `seed/verbs/explain.py`, `seed/verbs/version.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** an artifact id or path
**When** `marshal seed explain <artifact>` runs
**Then** it prints the artifact's class, its rationale from the manifest, its update behavior,
and (for hybrid) its regions and anchors
**And** it accepts a path as well as an id, resolving the path to its manifest entry
**And** an unknown artifact yields a helpful message listing near matches
**And** `--json` emits the same data structurally
**And** `marshal seed version` prints **both** the CLI version and the bundled model version, plus
the adopted repo's model version when run inside one (FR-125)
**And** both verbs are read-only

---

## Epic 12: Packaging, Oracle & Hardening

**Goal:** Ship it, and prove the claims that distinguish Genesis from every comparable tool —
the empty-plan oracle, zero egress, the write guard, and the pattern invariants as executable
tests.

### Story 12.1: Full pixi wiring, distribution, and repo-gate compliance

As the repo,
I want Genesis wired into the workspace exactly like `pyforge-warden`,
So that it builds as a conda package and its landing does not red the always-on PR gates.

**Type:** infra • **Effort:** M • **Deps:** S-7.1, S-11.6 • **FR/AD:** FR-122, AD-64, NFR-C1,
NFR-C2, NFR-C3, D3
**Surface:** root `pixi.toml`, `environment.yaml`, `docs/reference/library-llms-full.md`, plus the member's `pixi.toml`/`pyproject.toml`

**Acceptance Criteria:**

**Given** the root `pixi.toml`
**When** the member is wired in
**Then** the engine dependency the S-7.6 spike adopted (Copier `>=9.17,<10` if it passed)
lands in root `[feature.pyforge-marshal.dependencies]` AND the member's
`[package.run-dependencies]` AND `pyproject.toml` `dependencies` — the shipped conda
package and wheel must import standalone (re-issued 2026-08-10 per amended AD-64: no new
feature, no new member)
**And** the existing `pyforge-marshal` environment remains the lean env bmad-loop
worktrees materialize — no `pyforge-genesis` env is ever created
**And** the existing `pyforge-marshal-test` task covers `tests/**/seed*`; no `genesis`
task exists
**And** a version-range sync test asserts the `copier` pin in `pixi.toml` matches the constant
in `engine/copier.py` (NFR-C2, warden's established pattern)
**And** the package builds as a conda package **and** as wheel + sdist (FR-122)
**And** **`environment.yaml` is regenerated and committed**
(`pixi project export conda-environment -e build > environment.yaml`) — the ungated repo gate
**And** the PR carries the **`maintenance` label** (change outside `recipes/`)
**And** `docs/reference/library-llms-full.md` is updated: Genesis added, and the scaffolding
decision table's "Scaffold a project → cookiecutter (+ cruft)" line reconciled with Copier's
adoption; `pixi run -e local-recipes llms-full-check` passes
**And** Linux and macOS are first-class; Windows is best-effort for `init`/`check` (NFR-C3)

### Story 12.2: The `local-recipes` empty-plan oracle (CRITICAL)

As the Genesis maintainer,
I want the source repo to be the regression test for the model manifest,
So that any divergence between the model and the repo it was extracted from fails the build
the day it appears.

**Type:** test • **Effort:** M • **Deps:** S-10.6, S-11.1, S-11.2 • **FR/AD:** SC-02, NFR-M2,
AD-60
**Surface:** `tests/oracle/test_local_recipes_empty_plan.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the `local-recipes` repository at the shipped model version
**When** `marshal seed adopt --dry-run` runs against it
**Then** the resulting plan has **zero actions** (SC-02)
**And** the test runs in Genesis's own CI so drift in the source repo fails Genesis's build
(NFR-M2)
**And** a non-empty plan fails with a readable diff of exactly which artifacts diverged and how
**And** the test is resilient to the repo's mutable content (recipe counts, project counts,
dashboard state) — it asserts on the model manifest's artifacts only, never on repo volume
**And** `unclassified-deferred` artifacts are excluded from the assertion by design and the
exclusion is explicit in the test
**And** the story documents any special-casing required; **if special-casing is needed to reach
empty, kill criterion K-02 is triggered and escalated** rather than worked around

### Story 12.3: Offline operation and the egress counter

As an air-gapped adopter,
I want proof that Genesis makes no network calls,
So that the model can be installed behind a firewall with confidence rather than hope.

**Type:** test • **Effort:** S • **Deps:** S-10.7, S-10.5 • **FR/AD:** NFR-A1, NFR-A2, NFR-S2,
AD-65, P-09, SC-06
**Surface:** `tests/integration/` (egress counter) — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the package with in-package templates
**When** the meta-test inspects imports
**Then** no module imports `requests`, `httpx`, `urllib.request`, or `socket` (AD-65, P-09)
**And** an egress-counter test asserts **zero** network calls across `init`,
`adopt --dry-run`, `adopt --apply`, `check`, and `update --run` (SC-06, NFR-A1)
**And** the suite additionally runs the same set under `unshare -n` (Linux) and passes
**And** every runtime dependency resolves from conda-forge (NFR-A2), asserted by the lean env
building with no PyPI access
**And** Genesis reads and writes no credentials (NFR-S2) — trivially true given no network
stack, asserted by the import test
**And** the only network path is Copier's git fetch, reachable **only** via `--template <url>`,
asserted by a test that confirms the default path never constructs a remote source

### Story 12.4: Pattern meta-tests and the never-write proof

As the Genesis architecture,
I want the twelve conflict-prevention patterns enforced by executable tests,
So that a future story cannot quietly violate an invariant the whole design rests on.

**Type:** test • **Effort:** M • **Deps:** S-10.3, S-11.4 • **FR/AD/P:** P-01–P-12, FR-100, SC-08,
NFR-R4
**Surface:** `tests/meta/` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** the package source
**When** the meta-test suite runs
**Then** **P-01** is enforced by an AST scan finding no `open(..., 'w')`, `Path.write_text`,
`Path.write_bytes`, `shutil.copy*`, `os.remove`, or `os.rename` against a target path outside
`fs.py`
**And** **P-02** is enforced by an import scan finding `copier` imported only in
`engine/copier.py`, and no import of Copier private/deprecated modules
**And** **P-03** is enforced by running detect against a write-blocking fixture
**And** **P-07** is enforced by an AST scan finding no hash comparison inside `apply/`
**And** **P-09** is covered by S-12.3's import test
**And** the layer rule (no upward imports; `detect` never imports `apply`/`engine`) is enforced
**And** **SC-08 is proven**: `marshal seed update --run` against a fixture repo cannot write to
`docs/dreams/**` or `**/planning-artifacts/**` — tested by a deliberately malicious manifest
entry and a deliberately malicious migration, both of which must raise `NeverWriteViolation`
**And** the symlinked-planning-artifacts case is included in the SC-08 proof

### Story 12.5: CLI contract, idempotence harness, and performance gates

As a machine and as a human,
I want consistent flags, stable JSON, correct exit codes, and bounded runtimes,
So that Genesis is usable unattended and predictable interactively.

**Type:** test • **Effort:** M • **Deps:** S-10.7, S-11.6 • **FR/AD:** FR-123, FR-124, FR-126, NFR-P1,
NFR-P2, NFR-P3, NFR-12, AD-51, AD-60, SC-03, SC-09
**Surface:** `tests/integration/`, `cli/seed.py` — all under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` prefix for modules)

**Acceptance Criteria:**

**Given** every verb
**When** the contract suite runs
**Then** all verbs accept `--json` and `--quiet`, and `--json` output is schema-stable across
verbs (FR-123, NFR-12)
**And** all mutating verbs accept `--dry-run` explicitly, and `adopt` / `update` default to it
(FR-124)
**And** exit codes match S-7.2's taxonomy for every failure mode, asserted case by case (FR-126)
**And** the CLI stays argparse-only per the amended AD-51 (2026-08-08): an import test asserts **zero** `typer`/`rich` imports anywhere under `src/` — the superseded typer+rich rule is never reintroduced
**And** the **idempotence harness** applies AD-60's universal shape to every verb: run, then
detect+plan, assert zero actions — covering `init`, `adopt` (SC-03), and `update`
**And** performance gates: `check` < 5 s (NFR-P1) and `adopt --dry-run` < 10 s (NFR-P2) on a
`local-recipes`-sized fixture; `init` end-to-end < 5 min (NFR-P3, SC-09)

### Story 12.6: README, adoption guide, and the finding→remedy reference

As a first-time adopter,
I want to understand the four verbs, the five classes, and every finding I might hit,
So that adopting the model does not require reading Genesis's source.

**Type:** docs • **Effort:** S • **Deps:** S-12.5 • **FR/AD:** NFR-M3, D1
**Surface:** `src/shared/packages/pyforge-marshal/README.md` + the finding-remedy reference doc (docs/)

**Acceptance Criteria:**

**Given** the shipped package
**When** the documentation is written
**Then** the README covers all four verbs with worked examples, the five artifact classes and
what each means for the reader, the two version numbers, and the state file's role
**And** a **finding → remedy reference** documents every member of the findings enum with its
severity and its fix (NFR-M3), in the shape of `SYNC-RUNBOOK.md`'s finding→remedy mapping
**And** an adoption guide walks the brownfield path: dry-run → review plan → apply → wire
`check` into CI
**And** an air-gapped deployment note covers the in-package templates and the conda-provisioned
engine
**And** the managed-region contract is documented for humans: what the markers mean, that
editing inside them is detected, and that deleting them is a sanctioned opt-out
**And** a test asserts every findings-enum member appears in the reference doc, so the doc
cannot go stale

---

## Epic 13: Surface drift reconciliation — a gate that can be cleared, a signal that can be trusted

**Goal:** Repair the instrument Marshal already owns. `scripts/spec_surface_check.py` has
carried **61 findings on `main`** for weeks, and the repo is not 61 kinds of broken — the
detector makes its reconciliation claim at the wrong granularity, twice, so its verdict is
unactionable in one direction and untrustworthy in the other. Decomposes
`spec-surface-drift-reconciliation` (FR-164..FR-169).

**Reopened twice on 2026-08-09** — S-13.5, then S-13.6. S-13.1..S-13.4 took the gate to 0 findings; two days of
*using* it exposed a third instance of the same granularity error — a Spec that declares a
surface with no `.memlog.md` has an empty contract hash, so its contract can never move and
nothing reports it. Same instrument, same disease, same Spec: it belongs in this epic.

**Why the two fixes are one epic.** They are the same disease at two levels: baselines stamp
all-or-nothing when they should be per-spec; drift clears per-spec when it should be per-file.
Fixing one without the other leaves the gate either unclearable or untrustworthy, and the
finding-clearing stories need both levers.

**Sequenced, not parallel.** S-13.3 and S-13.4 exist to *use* the levers S-13.1/S-13.2 build;
running them first would mean clearing findings with the blanket tools this epic exists to
replace. S-13.5 needs both levers too — it disposes of seven drift-blind specs, which takes
the scoped stamp (S-13.1) to avoid blessing anyone else's drift, and the per-file rule
(S-13.2) to prove no `[drift]` was downgraded on the way. Every dependency is within-epic and
earlier — no forward-epic reference.

### Story 13.1: A baseline can be stamped for one spec

As the operator,
I want to settle one spec's baseline without accepting any other spec's pending drift,
So that the sanctioned fix for a single finding stops destroying the evidence for 34 others.

**Type:** change • **Effort:** S • **Deps:** — • **FR/AD:** FR-164, FR-167

**Acceptance Criteria:**

**Given** a committed `scripts/.spec-surface-baseline.json`
**When** `--write-baseline --spec <name>` runs (repeatable)
**Then** only the named specs' entries change and every other entry is **byte-identical**
**And** an unknown spec name exits **2** and prints the known set — never a silent no-op
**And** unscoped `--write-baseline` still works, and its `--help` states plainly that it
accepts every other spec's pending drift as correct
**And** the stamp **merges** into the committed file rather than rewriting from the in-memory
set, so a spec absent from this invocation is not silently dropped
**And** a mutation test proves the guard both ways: removing the scoping re-reds the isolation
test, restoring it passes

### Story 13.2: A moved contract reconciles only the paths it names

As the operator,
I want a memlog entry to stop speaking for governed files it never mentions,
So that unrelated activity cannot silently launder pending drift.

**Type:** change • **Effort:** M • **Deps:** — • **FR/AD:** FR-165, FR-167

**Acceptance Criteria:**

**Given** a spec whose memlog moved and whose governed files drifted
**When** the drift pass runs
**Then** a drifted file **named** in the memlog clears, and an **unnamed** one reports
`[drift-presumed]`
**And** `[drift-presumed]` is **informational** — it never contributes to the exit code
**And** a memlog naming no paths is still legal: every drifted file degrades to
`[drift-presumed]`, never to a hard failure (or the gate reds for every historical entry)
**And** matching is literal substring on the repo-relative path — no prose inference
**And** no `.memlog.md` is edited, reordered, or normalized by this change
**And** a laundering test replays the live incident — appending an unrelated entry to
`spec-regenerable-factory`'s memlog no longer clears the drift on
`scripts/bmad_drift_check.py` / `scripts/dream_chain_check.py`
**And** a mutation test proves it both ways: restoring the per-spec short-circuit re-reds that
laundering test

### Story 13.3: The no-baseline, ungoverned and stale-allowlist findings are cleared

As the operator,
I want the 27 mechanically-clearable findings dispositioned,
So that what remains is only the drift that needs real judgment.

**Type:** change • **Effort:** M • **Deps:** S-13.1 • **FR/AD:** FR-166

**Acceptance Criteria:**

**Given** S-13.1's scoped stamp
**When** the 24 `[no-baseline]` specs are registered
**Then** each is stamped **individually**, and no `[drift]` finding disappears as a side effect
— verified by diffing the finding set before and after
**And** the two `[ungoverned]` files (`docs/governance/spec-pyforge-charter/{SPEC.md,.memlog.md}`)
are given a surface **or** an allowlist entry, with the choice recorded (this is the Spec's own
open question — the Charter defines the chain this detector polices)
**And** the `[stale-allowlist]` entry `pixi.toml` is removed
**And** anything that cannot be honestly cleared is filed as deferred work with its reason,
never suppressed

### Story 13.4: The 34 drift findings are reconciled or recorded

As the operator,
I want each drifted file either genuinely reconciled or stamped with stated reasoning,
So that a green gate means the contracts actually match the code.

**Type:** change • **Effort:** L • **Deps:** S-13.1, S-13.2 • **FR/AD:** FR-166

**Acceptance Criteria:**

**Given** the 34 `[drift]` findings across five specs (steward/spec-pyforge-steward **23**,
scribe/spec-team-memory **5**, marshal/{fidelity-enforcement, factory-console, durable-runs}
**2** each)
**When** each spec is worked
**Then** every finding is partitioned into *genuine surface change* (the contract moves — the
spec is re-derived) or *already reconciled, unstamped* (scoped-stamped), and the partition is
recorded in that spec's own memlog
**And** the 23-file steward cluster is **not** bulk-stamped on the strength of being large —
if that surface changed, its contract moves
**And** `pixi run -e local-recipes spec-surface-check` exits **0**
**And** the epic's own changes to `scripts/spec_surface_check.py` are themselves reconciled
against `spec-surface-drift-reconciliation` — the detector must not be the one file that
escapes its own gate

### Story 13.5: A Spec cannot declare a surface it has no contract for

As the operator,
I want a governed Spec with no `.memlog.md` reported by name,
So that a surface whose contract can never move stops passing as green.

**Type:** change • **Effort:** M • **Deps:** S-13.1, S-13.2 • **FR/AD:** FR-168

**Added 2026-08-09**, reopening a `done` epic. Found by *operating* the gate S-13.1..S-13.4
turned green: two Specs shipped drift-blind two days apart, and the fleet sweep that followed
found seven. Same Spec, same disease, so it belongs here rather than in a new epic.

**Acceptance Criteria:**

**Given** a spec that governs ≥1 tracked file under the default `surface-drift: memlog` mode
**When** its `.memlog.md` does not exist
**Then** a **gating** `[drift-blind]` finding names the spec, its governed-file count, and the
path the memlog belongs at — because `contract_hash()` returns `""`, so the contract can never
move and the "reconcile the spec" remedy the detector prints is unreachable
**And** a spec governing **zero** files, a `surface-drift: exempt` spec, and a
`surface-drift: sentinel:<path>` spec each report **nothing** — none of them can go blind
**And** `[drift-blind]` gates even though `[drift-presumed]` does not: presumed reconciliation
is *unproven* over historical entries nobody can retro-name, blindness is *structurally
impossible* and clears by creating one file
**And** the detector never creates the memlog it checks for — a self-clearing finding is not a
finding, and it would author a decision record nobody decided
**And** the 7 live instances (**396 governed files**: mason/spec-conda-forge-expert-rebuild
**370**, herald/spec-herald-moments-2-4-live-backend **18**, four marshal specs **7**,
steward/spec-unified-container **1**) are dispositioned by writing each memlog **and**
scoped-stamping its baseline in the **same** change — a new memlog moves the contract hash off
`""`, so stamping later would silently downgrade that spec's next drift from gating `[drift]`
to informational `[drift-presumed]`
**And** a before/after finding diff proves no `[drift]` became `[drift-presumed]` as a side
effect of the seven memlogs
**And** a mutation test proves the guard both ways: deleting a governed fixture's memlog reds
the new test, and removing the check re-greens it

### Story 13.6: The presumed set is worked down by measurement

As the operator,
I want the 994 `[drift-presumed]` entries dispositioned rather than carried,
So that the informational channel stays small enough to read and a new entry means something.

**Type:** change • **Effort:** M • **Deps:** S-13.2, S-13.5 • **FR/AD:** FR-169

**Added 2026-08-09.** S-13.2 made this set visible for the first time; leaving it standing
would repeat the mistake the Dream was seeded to correct — a number that hardens into terrain.

**Acceptance Criteria:**

**Given** the 994 entries across four station Specs
**When** each is traced to the commit that last moved it
**Then** the set is partitioned `added` (baseline lag) vs `changed` (the per-file question),
and the counts are **measured, never estimated** — 932 / 62 / 0, with **994/994** traced
**And** every cluster is judged against its own Spec's capabilities, and that judgment is
recorded in that Spec's memlog **before** any stamp — a stamp is honest only after the
judgment, and the two orders are indistinguishable in the resulting number
**And** anything moved by a story that is **not** `done`, or landing outside a contracted
capability, is **reported rather than stamped** (measured: zero such files)
**And** herald's 751 `presentations/**` entries (15 deck clusters) are judged against **HER-9**,
which contracts that corpus — not waved through on the strength of being the biggest cluster
**And** no entry is cleared by naming 994 literal paths in a memlog: that satisfies the
matcher and records nothing
**And** the four Specs are scoped-stamped **individually**, each verified to change only its
own baseline key
**And** `spec-surface-check` reports **0 findings and 0 `[drift-presumed]`**, with a
before/after diff proving no gating `[drift]` was absorbed

### Story 13.7: The producer reconciles the surface it drifts *(added 2026-08-09 — FR-174)*

As the operator,
I want bmad-loop to name the governed paths it changed in the owning Spec's memlog,
So that the spec-surface gate stops being a tax paid by whoever lands the work.

**Type:** feature • **Effort:** M • **Deps:** S-13.2 • **FR/AD:** FR-174

**Why now.** The first three loop-produced stories to be landed (doctor 6.2–6.4, 2026-08-09)
drifted **14 governed paths** across `spec-pyforge-doctor`, plus `pixi.toml` against two further
surfaces — every one named by hand at landing. S-13.2's rule is correct; the machine writing
most of this repo's code has no idea it exists.

**Acceptance Criteria:**

**Given** a loop-produced story that changed governed files
**When** the story completes
**Then** the owning Spec's `.memlog.md` names **each** changed governed path, written as part of
the story rather than at landing
**And** `spec-surface-check` is green on the station branch with no human editing a memlog
**And** a story that changed **no** governed file writes nothing — silence is not a finding, and
an entry per story would be noise
**And** the loop is **never** handed `--write-baseline`: a producer that can stamp its own
baseline is precisely the laundering S-13.2 exists to end
**And** matching stays per-file naming under S-13.2's literal rule — no blanket claim

---

## Epic 14: The shared floor — pyforge-core

**Goal:** FR-157..FR-163 (`spec-pyforge-core`): the five primitives written 3-20× across
eight stations become one enforced leaf. **SEQUENCING (PRD § 16.8): S-14.1 and S-14.2 land
BEFORE seed stories S-7.2/S-7.3**, which would otherwise mint copy #21 of atomic write and
copy #6 of the verdict lattice. Decomposed 2026-08-10 from the audit's AF-R8 finding
(operator-directed); convergence-checked — nothing here is already covered. Realizes
`spec-pyforge-core` CAP-1..CAP-7: FR-157→CAP-1, FR-158→CAP-2, FR-159..161→CAP-3/CAP-4/CAP-5,
FR-162..163→CAP-6/CAP-7.

### Story 14.1: The leaf exists and is provably a leaf
**Type:** infra • **Effort:** S • **Deps:** none • **FR/AD:** FR-157; AD-66
**Surface:** `src/shared/packages/pyforge-core/**` (new member), root `pixi.toml`
**Given** the workspace **Then** `pyforge-core` exists as a pure-stdlib member and a
meta-test fails the build if any of its modules imports from `pyforge.<station>`; every
station stays independently conda-installable.

### Story 14.2: Atomic write has one implementation
**Type:** feature • **Effort:** M • **Deps:** S-14.1 • **FR/AD:** FR-158; AD-67
**Surface:** `pyforge-core` + every measured copy's module (6 stations)
**Given** the ~20 measured copies **Then** one `pyforge.core` implementation replaces ALL of
them in the same story (AD-67: extraction retires the copy), with per-call-site durability
semantics verified, not assumed uniform.

### Story 14.3: One lattice, one envelope, one exception root
**Type:** feature • **Effort:** L • **Deps:** S-14.1 • **FR/AD:** FR-159, FR-160, FR-161; AD-67, AD-68
**Surface:** `pyforge-core`, warden/doctor/marshal report+verdict modules, herald/mason error roots
**Given** the five verdict-lattice declarations, three report envelopes and two exception
roots **Then** each collapses to one core declaration with observable behaviour frozen
(AD-68): exit codes unchanged, captured real reports validate unchanged, no `except` clause
widens (asserted by test).

### Story 14.4: The subprocess seam is reconciled and sole ownership is gated
**Type:** feature • **Effort:** M • **Deps:** S-14.2, S-14.3 • **FR/AD:** FR-162, FR-163; AD-69
**Surface:** `pyforge-core`, marshal's 7 importing modules, one sole-ownership meta-test per primitive
**Given** doctor's `cli_bridge` and marshal's `ProcessPort` **Then** one guard is chosen
deliberately, Marshal's 7 modules route through it, steward's raw-propagation is folded in or
recorded as a tested opt-out — and a sole-ownership meta-test per extracted primitive fails
the build when a second implementation appears anywhere under `src/shared/packages/`.

## Epic 15: Fleet operations run themselves

**Goal:** FR-133..FR-139: the two hand-run rituals this audit performed repeatedly — loop-home
refresh and ledger promotion — become checked machinery. Convergence: FR-139's monotonic half
is ALREADY COVERED (`promote_sprint_status.py`'s terminal guard, shipped 2026-08-08, + the
ledger-regression detector) — only its lock rides along; FR-137/138 are PARTIAL (story-status
covers feed-vs-git; the landed-but-unpromoted direction is the gap).

### Story 15.1: One command refreshes the fleet's homes
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-133, FR-134, FR-135; AD-21 — realizes spec-loop-home-fleet-refresh CAP-1..CAP-3
**Surface:** `cli/factory.py` or new `cli/refresh.py`, `core/context.py`
**Given** the 8 loop homes **Then** one command reports each home's behind-count (an
unreadable home is reported, never skipped), fast-forwards clean trees only (dirty homes
refused by name; push targets `loop/<slug>` only), and re-renders the harness policy as a
checked step — each step `done | skipped | failed`; an FF-without-render reports the home
incompletely refreshed.

### Story 15.2: Landing promotes the ledger, and staleness is its own check
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-136, FR-137, FR-138, FR-139 (lock residual); AD-71 — realizes spec-sprint-status-auto-promote CAP-1..CAP-4 (named explicitly in that Spec's own memlog as this story)
**Surface:** `cli/land.py`, `scripts/promote_sprint_status.py`, `pyforge.doctor.sources` (ledger direction)
**Given** a story landing **Then** ledger promotion runs mechanically from the landing
itself (deterministic trigger, never memory); a standalone check reports ledger-vs-git drift
per key WITH DIRECTION (the landed-but-unpromoted direction story-status does not cover),
reading merge history never the feed; concurrent promotions serialize on a lock (reusing the shipped `FsPort.acquire_advisory_lock` primitive, AD-42 — never a second lock implementation); the
already-shipped downgrade refusal is regression-pinned, not rebuilt.

## Epic 16: The board derives truth

**Goal:** FR-140..FR-143: the dashboard's path plumbing stops being hand-glued.
Convergence (corrected post-blind-review): **FR-128 is ALREADY COVERED** — `_stage_globs`
has read the canonical `src/shared/packages/<slug>/tests/` tree since `2957718d4c`
(2026-08-02, `generate.py:1724-1731`, citing the testing-charter's own CAP-1), and this
branch's `data.js` shows atlas/warden TEA populated with `gaps: []`; no story minted. The
FR-140..143 set is genuinely undelivered — `index.html` still carries a retired-slug
special case.

### Story 16.1: One resolver, derived sources, loud failures
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-140, FR-141, FR-142, FR-143 — realizes spec-dashboard-project-path-derivation CAP-1..CAP-4 (that Spec's own owning surface)
**Surface:** `pyforge.doctor.sources.fleet_scan`, `docs/dashboard/index.html`, `docs/dashboard/data.js`
**Given** the dashboard build **Then** slug→path resolution lives in ONE function with one
exception table; `PROJECT_SOURCES` is discovered (a new station appears with no hand edit; a
dissolved project resolves to its owner); resolution ships computed in `data.js` (the JS
carries no slug special case — incl. removing the retired `pyforge-genesis` one); an
unresolvable slug exits non-zero naming itself.

## Epic 17: Instruments verified, chains regenerable

**Goal:** FR-144..FR-152 (FR-148..152 = the FIRST decomposition of
`spec-fleet-chain-completeness`, realized here as the `marshal chain` slice — Stories
17.3/17.4; completed by FR-192/Epic 21's `marshal planning` slice. Overlap resolved
2026-08-27, PRD § 18.1 — each id keeps its shipped owner, no renumber): gate the detectors
themselves and make chain regeneration one
invocation. Convergence (corrected post-blind-review): FR-144 is LARGELY COVERED (doctor's
fixture suites) — the `covers-dreams:` pin ALREADY EXISTS; the true residual is the
unparseable-frontmatter-becomes-a-finding behaviour, currently pinned as its opposite; FR-150 is PARTIAL (chain-completeness INV-A..D +
dream-chain cover spec/board truth; the layer-presence report is the gap).

### Story 17.1: The detectors' remaining blind spots are fixture-pinned, with an incident log
**Type:** test • **Effort:** M • **Deps:** none • **FR/AD:** FR-144 (residual), FR-145, FR-146
**Surface:** `src/shared/packages/pyforge-doctor/tests/`, a tracked detector-incident log companion
**Given** the moved detectors **Then** **unparseable frontmatter surfaces as a finding**
rather than degrading silently (the REAL FR-144 residual — today
`test_sources_chain_dream_chain.py:682` pins the opposite, degrade-to-owner-none behaviour;
this story changes it and re-pins; the `covers-dreams:` path is already pinned at
`:147/:164/:657` — corrected post-blind-review); `bmad-drift`'s pin-missing/archive-misplaced/stray-file/spec-status-stale
each gets a fixture (live-repo integrity tests stay); and a tracked incident log (date,
detector, wrong claim, true value, root cause, fixing commit, pinning fixture) exists with a
mandatory-entry rule in the same change that fixes a detector.

### Story 17.2: The dreams hygiene mode exists
**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** FR-147
**Surface:** `pyforge.doctor.sources` (dream-chain source)
**Given** the mode promised by the 2026-07-23 restructure **Then** it reports Dream-tier
hygiene findings (vocab, table sync, realization-log presence) — the checks this audit's
Phase 2b ran by hand.

### Story 17.3: Chain-completeness audit mode reports layers
**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** FR-150 (residual), FR-152; AD-72
**Surface:** `pyforge.doctor.sources` (board/chain sources), seeded from `generate.py`'s existing layer computation (`:1859` — never a second derivation)
**Given** a named project **Then** a read-only mode reports which chain layers
(Dream/Spec/brief/PRD/architecture/epics/stories) exist and which are missing, invocable
per-project without touching another's tree.

### Story 17.4: Orchestrated regeneration that cannot lose code status
**Type:** feature • **Effort:** L • **Deps:** S-17.3 • **FR/AD:** FR-148, FR-149, FR-151; AD-72
**Surface:** new `cli/` verb + `core/` orchestration, `scripts/promote_sprint_status.py` guard reuse
**Given** a project's chain **Then** regeneration is one invocation in dependency order;
every `done` story key is byte-identical after it (only backlog epics restructure — the
guard the ledger already enforces, applied to the generator); orphaned specs/epics are
reported with review-gated cleanup, nothing deleted without review.

## Epic 18: The governed tool surface

**Goal:** FR-153..FR-156 (`spec-agent-tool-surface`): every factory capability reachable
through one governed, typed surface. Convergence: FR-154's mechanism is ALREADY COVERED
(`marshal init`'s rendered `.mcp.json` pattern, AD-43) — the surface itself is the gap
(2026-07-28 measurement: 2-of-6 stations, Marshal at zero).

### Story 18.1: Marshal's capabilities become named, typed tools
**Type:** feature • **Effort:** L • **Deps:** none • **FR/AD:** FR-153, FR-154 (mechanism already covered — marshal init's rendered .mcp.json) — realizes spec-agent-tool-surface CAP-1, CAP-2
**Surface:** new `pyforge/marshal/mcp/` (or tools module), rendered per-home registration
**Given** marshal's CLI surface **Then** its capabilities are exposed as named tools with
typed arguments and structured answers, registered per-home via the existing rendered
`.mcp.json` pattern — never a machine-absolute hand edit.

### Story 18.2: Parity and coverage are gated numbers
**Type:** test • **Effort:** M • **Deps:** S-18.1 • **FR/AD:** FR-155, FR-156 — realizes spec-agent-tool-surface CAP-3, CAP-4
**Surface:** meta-test + a per-station coverage report
**Given** the CLI and tool surfaces **Then** a capability present in one and absent from the
other fails a check, and per-station tool-surface coverage is reported as a number — the
2-of-6-with-Marshal-at-zero finding is why this is measured, not asserted.

## Epic 19: The testing charter, enforced

**Goal:** FR-129..FR-132 (+FR-130's kit): the fleet's test architecture becomes generated,
current, and gated. Convergence: this epic IS the durable fix for the audit's
test-architecture-stale-at-5-stations routing — the `bmad-document-project` (retired in 6.11) sweep becomes
S-19.1's first run.

### Story 19.1: One generator produces every station's test architecture
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-129, FR-132
**Surface:** `scripts/bmad_tea_playwright.py` (or successor), all 8 `test-architecture.md`
**Given** the 8 stations **Then** one automation path produces every `test-architecture.md`
(a `TBD` token in output is a failed run); regeneration is idempotent on an unchanged tree
and produces a changed document when tests moved — its first real run replaces the audit's
routed hand-sweep.

### Story 19.2: The shared test-support kit
**Type:** feature • **Effort:** M • **Deps:** S-14.1 (Q-26: own leaf vs pyforge-core module — decided here) • **FR/AD:** FR-130
**Surface:** `pyforge-testing-kit` (or `pyforge.core.testing`), seeded from Marshal's four real mocks
**Given** Marshal's CLI-runner/page-object/DB-factory/auth-HTTP-time mocks **Then** they ship
as a shared kit (seeded, not rewritten) and at least one other station imports from it.

### Story 19.3: Coverage gates that name the module
**Type:** test • **Effort:** M • **Deps:** S-19.1 • **FR/AD:** FR-131
**Surface:** CI workflow + per-station thresholds
**Given** a PR dropping a touched package below its station's threshold **Then** CI fails
naming the uncovered module (unit >80% / integration >70%), not just printing a percentage.

### Story 19.4: Test architecture stays current as stories land
**Type:** feature • **Effort:** S • **Deps:** S-19.1 • **FR/AD:** FR-132 (spec-pyforge-testing-charter, CAP-5; found undecomposed, 2026-08-15 fleet-wide decomposition audit; re-cited 2026-08-27 from the double-assigned FR-193 — FR-132's § 16.1 registration is this story's title verbatim, PRD § 18.1)
**Surface:** `scripts/bmad_tea_playwright.py` (or successor)'s own re-run path; each station's `test-architecture.md`
**Given** an epic completes **Then** re-running S-19.1's generator against the station's own
epics regenerates its story-coverage table without hand-editing — a story that shipped
without its `test-architecture.md` row updated is a detectable drift, not a silent gap, so
Herald's and Marshal's existing real test-architecture documents do not freeze at whatever
snapshot they were generated at.

## Epic 20: The loop cannot lose work, and a landing is always recognizable

**Goal:** FR-188..FR-191: the 2026-08-14 audit's four undecomposed marshal Specs become checked
machinery. The unowned `bmad_loop` package's two work-loss modes get Marshal-side containment —
baseline drift detected and loud (five occurrences in one session, PRs #482–#484), intent-gap
reverts preserved instead of discarded (Story 10.1, PR #486) — with one gated upstream filing for
both; the bmad-switch scope triangle becomes enforcement instead of discipline (closes DW-1-4-2);
and one shared landing-evidence grammar replaces the three partial classifier dialects that
produced 3 standing story-status false positives, 26 MRS-STATUS-010 UNCONFIRMED warns, and 0
retire proposals. Everything lives on this repo's side of the seam: no edits to the installed
`bmad_loop` package, and doctor never imports `pyforge.marshal`.

### Story 20.1: Baseline-drift detector at the seam
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-188 (spec-bmad-loop-baseline-drift, CAP-1)
**Surface:** detector home is this story's design decision — `scripts/*.py` (loop-stall-check precedent) or `pyforge.doctor.sources` (story-status-check precedent); run-home feeds read-only
**Given** run `20260813-094919-bfcb`'s journal (story 9-6) **Then** a detector — reading only
feeds `bmad_loop` itself writes (`journal.jsonl`, `state.json`, `attempt-preserve/*` refs,
`failed/*/changes.patch`), never importing or editing the package — fires naming the story, both
baselines (`523e938c7978` real vs `26102ea12c6d` drifted), and the preserve ref; a clean run's
feeds yield no finding. Scope=runtime like `loop-stall-check` — excluded from `detectors-ci`.

### Story 20.2: Baseline-drift defers get loud
**Type:** feature • **Effort:** S • **Deps:** S-20.1 • **FR/AD:** FR-188 (spec-bmad-loop-baseline-drift, CAP-2)
**Surface:** the S-20.1 detector's exit/report path + the operator's existing ATTENTION plane (`fleet-picture` or equivalent)
**Given** a run carrying a baseline-drift defer **Then** the detector exits non-zero and the
finding surfaces where the operator already looks, naming the recovery inputs — story, run,
preserved ref/patch, drifted-vs-real baselines — so recovery is a named next action, never
per-occurrence archaeology; such a run cannot read healthy in the containment's output; loud
defer only, never a quiet auto-land.

### Story 20.3: The gated upstream filing
**Type:** chore • **Effort:** S • **Deps:** none • **FR/AD:** FR-188, FR-189 (spec-bmad-loop-baseline-drift CAP-3; carries spec-bmad-loop-intent-gap-work-preservation's Story 10.1 evidence — the two loss modes share one report)
**Surface:** both Dreams' Realization logs, Story 6.8's upstream contribution register
**Given** the drafted issue already in the baseline-drift Dream **Then** both gates are recorded
as checked — (1) repo access / org relationship (issue vs PR vs discussion), (2) duplicate search
first — and either the coordinated issue is filed against `bmad-code-org/bmad-loop` (URL appended
to both Dreams' Realization logs, registered in `upstream-register.json`) or a duplicate is found
and linked instead; until the gates clear, the draft stays unfiled by design.

### Story 20.4: Intent-gap attempts are preserved
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-189 (spec-bmad-loop-intent-gap-work-preservation, CAP-1 + CAP-2)
**Surface:** `adapters/harness_bmadloop.py`, `supervisor/`
**Given** an intent-gap halt on a story with tracked changes **Then** Marshal-side compensation
at the adapter seam parks the attempt exactly like the deferred-story path — an
`attempt-preserve/*` branch for real commits, a `failed/<story>/changes.patch` otherwise
(interception point, seam-observed vs proactive supervisor snapshot, is this story's design
decision) — the worktree stays reverted clean per protocol, and the escalation text names the
exact ref/patch so `bmad-loop resolve --restore-patch` restores the attempt with zero
session-transcript access; the halt's strictness never changes, and no preserved attempt
auto-relands without the contract fix.

### Story 20.5: Missing-preserve detector
**Type:** test • **Effort:** S • **Deps:** S-20.4 • **FR/AD:** FR-189 (spec-bmad-loop-intent-gap-work-preservation, CAP-3)
**Surface:** the S-20.4 preserve convention + a post-hoc detector (`story-status-check`/`loop-stall-check` precedent)
**Given** a simulated intent-gap halt with no preserve artifact **Then** the detector trips a
finding rather than passing silently (seam bypassed or upstream behavior shifted); a halt with
its artifact present passes clean.

### Story 20.6: The verify_scope primitive
**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** FR-190 (spec-bmad-switch-scope-enforcement, CAP-1)
**Surface:** one new shared module — where it physically lives (import path vs Genesis COPIED-MANAGED copy) is this story's design decision under the never-two-parallel-copies constraint
**Given** marker and both symlinks all pointing at slug B **Then** `verify_scope(root, "A")`
returns a `ScopeDrift` naming found-vs-expected, an unrecognized symlink-target shape returns a
drift reporting "unrecognized" — never inferred agreement — (DW-1-4-2 blind spots (2) and (1)),
and the all-agree happy path returns `None`; three file reads and string compares, no subprocess,
cheap enough for a write-skill preflight.

### Story 20.7: Both guards hard-fail on drift
**Type:** feature • **Effort:** S • **Deps:** S-20.6 • **FR/AD:** FR-190 (spec-bmad-switch-scope-enforcement, CAP-2 + CAP-3; closes DW-1-4-2)
**Surface:** `scripts/bmad-switch`, `cli/init.py` (MRS-INIT-003)
**Given** a deliberately desynced tree **Then** `scripts/bmad-switch --current` exits non-zero
naming the drift (no more advisory stderr at exit 0) and `marshal init` refuses a home whose
marker/symlinks agree on a different project than requested instead of silently reconciling it —
both by consuming the ONE S-20.6 primitive, retired per-caller check bodies gone, not shadowed;
DW-1-4-2 (`deferred-work-ledger.md:385`) closes against this story.

### Story 20.8: The landing-evidence grammar
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-191 (spec-landing-evidence-grammar, CAP-1)
**Surface:** the grammar artifact — contract with cross-package conformance test, shared data artifact, or `pyforge-core` module; the home is this story's own design decision inside the doctor-never-imports-`pyforge.marshal` boundary
**Given** the three-plus sanctioned landing paths **Then** ONE grammar of landing-evidence shapes
exists — merge-subject templates (FR-187's templated subject is one shape, not the grammar),
branch-name grammars (`land/<station>-<story>…`, `bmad-loop/<run>/<story>`), and a documented
recovery-commit convention so the next manual recovery is born recognizable — recognizing the
three live recovery commits (`accc097e6a`, `5290c9bcd2`, `03d8fc8c86`) as written (or via a
one-time reviewed allowlist, never a history rewrite), with a conformance surface both packages
test against.

### Story 20.9: Doctor consumes the grammar
**Type:** feature • **Effort:** S • **Deps:** S-20.8 • **FR/AD:** FR-191 (spec-landing-evidence-grammar, CAP-2)
**Surface:** `pyforge-doctor` `sources/marshal.py` story-status evidence routes (`:479-517`)
**Given** the live repo **Then** `story-status`'s evidence routes consume the shared grammar in
place of route 2/route 3's private dialects, the three standing false positives (marshal 8-2,
marshal 10-1, mason 3-7) go green with **no per-story whitelist**, and a genuinely-unlanded story
fails exactly as today — absence-of-match stays hedged.

### Story 20.10: Marshal consumes the grammar
**Type:** feature • **Effort:** S • **Deps:** S-20.8 • **FR/AD:** FR-191 (spec-landing-evidence-grammar, CAP-3)
**Surface:** `core/promotion.py` (`:93-107`), `core/status.py` (MRS-STATUS-010, `:836-861`), `marshal retire`'s patch-id matching
**Given** the live tree **Then** the promotion classifiers, MRS-STATUS-010, and `marshal retire`
consume the same grammar: the UNCONFIRMED pile shrinks from 26 to genuinely-unlanded patches
(the honest "UNCONFIRMED, not proof it never landed" wording retained), and `retire` proposes
real retirements again where recovered branches are demonstrably merged.

### Story 20.11: Doctor's own adoption gap closes — the branch-name fallback and a loose last resort
**Type:** bug • **Effort:** S • **Deps:** S-20.9, S-20.10 • **FR/AD:** FR-191 (spec-landing-evidence-grammar, CAP-4)
**Surface:** `pyforge-doctor` `sources/marshal.py` (`_keys_from_merge_subjects`, `_keys_from_main_commits`, two new local helpers), `tests/unit/test_sources_marshal_story_status.py`
**Note:** found live 2026-08-28 during a fleet-wide hygiene sweep: `story-status-check` FAILed 25
stories (doctor 6, marshal 10, mason 7, steward 2), every one independently confirmed genuinely
landed via `git merge-base --is-ancestor`. Root causes, both closed here: (a) doctor's Routes 2/3
never tried `classify_branch_name`'s `land/`/`bmad-loop/` branch-name fallback that marshal's own
`core/promotion.py::_classify_merge_subject` (Story 20.10) already has; (b) a real, irreducible
tail of hand-authored landing-commit phrasings matches no anchored grammar shape and never will.
**Given** the live repo **Then** all 25 standing false positives go green with no per-story
whitelist, a genuinely-unlanded story (wrong station, or a longer numeric key colliding with a
shorter one, e.g. "11.10" vs "11-1") still fails exactly as today, and neither
`pyforge.core.landing_evidence` nor `pyforge.marshal.core.promotion` changes — the fix is entirely
local to doctor's own port, scoped to an advisory finding.

### Story 20.12: fleet-picture names a stale primary checkout, not just stale loop homes
**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** FR-188 lineage (extends 20.1's staleness-detection family) — incident 2026-09-10
**Note:** found live 2026-09-10 running concurrent multi-station dispatch campaigns: Marshal's
own unattended CAP-4 land path (`gate_mode: none`) auto-landed pyforge-warden's Story 12.1 — commit,
push, open PR, verify, merge — with zero operator action. The operator's own primary checkout
(the repo root they run `git`/`gh`/pixi commands from) had no signal this happened; it silently
fell 3 commits behind `origin/main` and was only discovered by an explicit `git fetch` + `git
rev-list --count HEAD..origin/main`, run because the operator happened to double-check. `fleet-
picture` already has this exact detection shape for loop homes (`loop_home_staleness()`,
`STALE_BEHIND_THRESHOLD = 20`) — it has no equivalent for the primary checkout itself, the one
location that matters most since it's where the operator's own next push/merge/worktree-creation
happens.
**Given** the primary checkout is N commits behind a live-fetched `origin/main` (N >= 1) **When**
`fleet-picture` runs **Then** the ATTENTION block names it ("primary checkout is N commit(s)
behind origin/main — run `git pull`"), on its own line separate from the per-loop-home staleness
lines, using a lower threshold than loop homes' 20 (any drift on the operator's own working
checkout is worth surfacing immediately, unlike a loop home which only matters right before its
next spin)
**And** a checkout already current with `origin/main` produces no such line
**And** the check live-fetches before measuring and degrades silently on any fetch/rev-list
failure (network error, no `origin` remote, detached HEAD) — the same fault-tolerant idiom
`loop_home_staleness()` already uses, never a hard failure of the read-only, never-gating report
**Status:** backlog

## Epic 21: The planning chain regenerates itself, and audits whether it's coherent

**Goal:** FR-192 (the second, full decomposition — completes FR-148..152's Epic 17
`marshal chain` slice as the `marshal planning` verb group; overlap resolved 2026-08-27,
PRD § 18.1 — each id keeps its shipped owner, no renumber): decomposes
`spec-fleet-chain-completeness`'s CAP-1..5 (found undecomposed beyond Epic 17's slice,
2026-08-15 fleet-wide decomposition audit). The factory's 8-layer planning chain
(Dream→Spec→Research→Brief→PRD→Architecture→Epics→Code) falls out of sync by hand today — the
2026-08-02 dream-consolidation pass across all 8 stations did every satellite retirement and
Spec/PRD/epics update by hand, with nothing verifying the chain stayed coherent afterward.
CAP-1's own invocation shape (Q1) and error/resume semantics (Q2) are genuinely undecided in
the Spec's own Open Questions — this epic is **not cleared to dispatch in full**: only Story
21.1 (CAP-3, audit mode) is independent of those open questions, since it reads and reports,
never orchestrates — though 21.1 itself depends on Epic 17's Story 17.3 landing first (see
21.1's own note: it extends 17.3's layer-presence check rather than duplicating it).

### Story 21.1: Chain-completeness audit mode extends layer-presence into full CAP-3 coverage
**Type:** feature • **Effort:** S • **Deps:** S-17.3 • **FR/AD:** FR-192 (spec-fleet-chain-completeness, CAP-3)
**Surface:** extends S-17.3's own read-only mode; the fleet dashboard's own per-station chain-status surface
**Note:** this is NOT a fresh implementation — Story 17.3 ("Chain-completeness audit mode
reports layers") already delivers most of CAP-3's shape (a read-only, per-project mode
reporting which of the 8 chain layers exist). This story is the DELTA 17.3 does not cover:
coherence/staleness/orphan-freedom (not just layer *presence*), a pass/fail verdict per
contract checkpoint (not just an exists/missing list), and surfacing that verdict on the
fleet dashboard. Depends on S-17.3 landing first so this extends one real implementation
rather than duplicating it.
**Given** any of the 8 PyForge stations, once S-17.3 exists **Then** the audit additionally
answers whether the chain is coherent and free of orphaned/stale artifacts (not just which
layers are present), computed by checking real artifact presence and cross-references each
run (never a cached or hardcoded per-station table, `EXEMPLAR-STANDARD.md`'s own provenance
rule) — matching what a manual read plus `dream_chain_check` would find — and the verdict
surfaces on the fleet dashboard, not only in the operator's terminal. Generates or changes
nothing.

### Story 21.2: Orchestrated chain regeneration
**Type:** feature • **Effort:** L • **Deps:** none • **FR/AD:** FR-192 (spec-fleet-chain-completeness, CAP-1)
**Blocked:** the Spec's own Q1 (invocation shape — a new `bmad-*` skill, a Workflow tool
script, or a subagent chain, undecided) and Q2 (error/resume semantics on a mid-chain
failure — halt, retry, or resume-from-phase, undecided) are both genuine open questions
needing an operator decision before this can be scoped further. Q4 (Phases 2/3 have no
confirmed 1:1 skill mapping — `bmad-product-brief`/`bmad-prfaq` exist but no dedicated
`bmad-research` skill) is a narrower design detail within this same blocker. Tracked openly,
matching Epic 10/11's own precedent for a Spec-level open question rather than a silently
invented default.
**Surface:** design TBD pending Q1
**Given** a consolidated Dream **When** unblocked and built **Then** `bmad-spec` →
`bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories` run in sequence, each
phase's output feeding the next, without a human hand-carrying files between skill
invocations — wrapping each skill's own memlog-derivation invariant, never reimplementing or
hand-overwriting a downstream artifact directly.

### Story 21.3: Code-status preservation
**Type:** feature • **Effort:** M • **Deps:** S-21.2 (blocked transitively) • **FR/AD:** FR-192 (spec-fleet-chain-completeness, CAP-2)
**Given** an already-partially-implemented project **Then** re-running the regeneration
workflow leaves every story's done/in-progress/backlog status exactly as it was before the
run — regenerating the planning chain never clobbers recorded Code implementation status.

### Story 21.4: Orphan detection with review-gated cleanup
**Type:** feature • **Effort:** M • **Deps:** S-21.2 (blocked transitively) • **FR/AD:** FR-192 (spec-fleet-chain-completeness, CAP-4)
**Blocked:** additionally needs the Spec's own Q3 (Phase 8's git integration shape — `git add`
without commit, an unstaged working-tree diff, or something else — unspecified) resolved.
**Given** a consolidation run **Then** artifacts the regenerated chain no longer references
(old spec folders, epics from replaced specs, dream-deleted references) surface as a named
list of orphan candidates with a reviewable diff — nothing is deleted, committed, or pushed
without the operator's explicit action.

### Story 21.5: Configurable per-project invocation
**Type:** feature • **Effort:** S • **Deps:** S-21.2 (blocked transitively) • **FR/AD:** FR-192 (spec-fleet-chain-completeness, CAP-5)
**Given** the same workflow definition **Then** it runs unmodified against any of the 8
stations by varying only its parameters (`project_slug`, `dream_path`,
`preserve_code_status` default true, `auto_commit` default false, `delete_orphans`
default true-with-review-pause) — never hardcoded per station. If a future implementation
regenerates more than one station's chain in one run, each station's phases are addressed by
literal `_bmad-output/projects/<slug>/planning-artifacts/...` paths with
`BMAD_ACTIVE_PROJECT=<slug>` per invocation, never concurrent `scripts/bmad-switch` calls
(CLAUDE.md's own parallel-agent physical-path rule).

**Epic 21 clears to dispatch on Story 21.1 once S-17.3 lands** (not yet — 21.1 depends on it)
— Stories 21.2/21.3/21.4/21.5 stay blocked pending the operator decisions on Q1/Q2/Q3/Q4
above, the same treatment Epic 10's Story 10.2 and Epic 11's Story 11.8 already established
this session.

## Epic 22: Single-story dispatch is a marshal verb, not a session's discipline

**Goal:** FR-193 (sole assignment of this id as of 2026-08-27 — the former Story 19.4
double-cite is re-anchored to FR-132, PRD § 18.1): decomposes
`spec-marshal-single-story-dispatch`'s CAP-1..8 (Spec landed 2026-08-21 from
`docs/dreams/marshal-single-story-dispatch.md`; the 2026-08-21 pass covered CAP-1..6 —
CAP-7 decomposed 2026-08-27 as Story 22.7, CAP-8 added and decomposed 2026-08-27 as
Story 22.8 after the live cursor-auth dispatch failure). The fastest story-landing
pattern the factory has run — one story per fresh worktree-isolated `bmad-dev-auto` session (the retired 6.x name of `bmad-build-auto`, as run),
real-completion await, independent verification, PR landing; validated at N=22 on 2026-08-21
— exists only as an interactive session's hand ritual. This epic makes it a governed marshal
launch mode. **HARD boundary carried from the Spec:** PRD Q-1 (§5.3 wrap-and-supervise) is
not revised — dispatch is a sibling mode beside `factory spin`/`resume`, never a bmad-loop
replacement, and the dispatched engine (`bmad-dev-auto` — the Spec's recorded wording; the retired 6.x name of `bmad-build-auto`) stays external and unmodified.
Composition, not reimplementation: Epic 1 provisioning, Epic 2 gates, Epic 4 landing +
FR-187 subject, Story 4.1/Epic 15 promotion are reused as shipped. Verb naming stays
provisional (`marshal factory dispatch`) pending PRD Q-15 — the Spec binds behavior, not the
name.

### Story 22.1: The dispatch verb launches one governed, isolated story session
**Type:** feature • **Effort:** L • **Deps:** none • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-1)
**Surface:** `cli/factory.py` (new subcommand), `core/`, the FR-52 adapter seam
**Note:** the Spec's open question on the concrete headless launch mechanism is a
story-level design decision bounded by two Spec assumptions: the harness is the
agent-CLI pattern validated at N=22 (a plain background agent — never a fork-style
subagent, whose nested subagents break `bmad-build-auto`), and every harness call goes
through one adapter seam (FR-52 extended to the second engine), never scattered
subprocess calls.
**Given** a station with a backlog story **When** the operator dispatches it **Then** a
fresh isolated worktree is provisioned, exactly one `bmad-build-auto` session launches
detached with `BMAD_ACTIVE_PROJECT` passed per-invocation and physical artifact paths
(never `scripts/bmad-switch`), the launch is journaled with intent/outcome discipline
(AD-25/AD-28/AD-30), the session demonstrably receives the policy-resolved model/budget
parameters, and the run appears in `marshal status` / `fleet-picture`.

### Story 22.2: Completion is judged from git and process facts, and a zombie is never redispatched
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-2)
**Surface:** the detached supervisor (Story 3.4 shape), `core/status.py`
**Given** a dispatched session **Then** its completion or failure is judged from git facts
(AD-33: commits on the story branch, merge refs) plus running-process facts — never from
harness notifications, self-reports, or busy-wait polling — with both motivating traps
regression-pinned: (a) no foreground path busy-waits (awaiting is a detached supervisor's
job, so the ~600 s watchdog kill of a busy-waiting parent cannot recur), and (b) a session
that emitted a killed/failed notification while git facts show live progress is treated as
live — a redispatch of the same story is refused naming the evidence (the observed
"dead" agent that landed two stories after its failure notification cannot be duplicated).

### Story 22.3: Verification is the product — no landing on a self-report
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-3)
**Surface:** composition over Epic 2's standalone gate objects; the story's frozen-surface diff read
**Given** a session that reports itself complete **Then** before any landing the driver
itself runs the story's real verify commands via Epic 2's gate objects and reads the diff
against the story's frozen surface — the self-report is input, never the verdict
(never-false-green; unevaluable ≠ pass). A story that self-reports shipped with failing
gates or an out-of-surface diff ends in a loud non-landing verdict naming the failed gate:
the doctor-12.3 shape (self-marked shipped, two live-reproducible leaks) is the canonical
refusal fixture.

### Story 22.4: A verified story lands through the existing machinery, classified marshal-native
**Type:** feature • **Effort:** M • **Deps:** S-22.2, S-22.3 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-4)
**Surface:** composition over `cli/land.py`/`deploy`, FR-187 merge subject, Story 4.1 promotion, Epic 15 ledger machinery
**Given** a verified dispatched story **Then** it lands via the existing Epic 4 semantics
with FR-187's detectable merge subject, its spec is durably promoted (Story 4.1), and its
ledger key advances (Epic 15) — with zero new landing or promotion code paths, and the
landing classified marshal-native by `marshal_native_merged_keys` (never FR-186's
`not-loop-native` bucket).

### Story 22.5: One story in flight per station; stations in parallel; overlap is loud
**Type:** feature • **Effort:** S • **Deps:** S-22.1, S-22.2 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-5)
**Given** dispatch requests **Then** a second dispatch onto a station whose in-flight story
(judged by S-22.2's facts) has not completed is refused naming that story; dispatches onto
different stations proceed concurrently (the cross-project plane
`spec-horizontal-run-concurrency` explicitly excludes from FR-184's in-loop clamp — the
clamp is untouched); and a detectable overlap between in-flight stories' declared frozen
surfaces produces a loud advisory while trusting the operator to proceed.

### Story 22.6: The dispatched run survives its operator, and its journal carries the timing signal
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-6)
**Surface:** journal + attach/resume (AD-22/AD-25/AD-30 precedents), Epic 1's work-preservation discipline
**Given** a dispatched run **Then** killing the terminal that issued it leaves the session
running; a fresh `marshal status` reports it from journal + process facts alone;
attach/resume recovers supervision; a story completed while unsupervised is reconciled from
git facts rather than lost; a failed or abandoned session's worktree and diff survive for
recovery (the `changes.patch` analog); and the journal records per-story start/end and
baseline→final revisions — making dispatch the at-source producer of the effort signal
Epic 23 renders (E23 consumes; neither depends on the other landing first).

### Story 22.7: Fleet-wide drain is a marshal-orchestrated mode
**Type:** feature • **Effort:** L • **Deps:** S-22.1, S-22.2, S-22.4, S-22.5 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-7; decomposed 2026-08-27 — the one CAP the 2026-08-21 pass left uncovered)
**Surface:** `cli/dispatch.py` (fleet mode), `core/`, in-repo queue state under `pyforge-marshal`
**Note:** the Spec's Success signal binds the subsumption target: Epic 22.1+ must absorb
`.cursor/pyforge-fleet-drain/` as marshal verbs and in-repo queue state under
`pyforge-marshal` (never session-local `.cursor/`); the companion
`fleet-drain-playbook.md` (validated 2026-08-22/23) stays the interim acceptance oracle
until the verb ships. Verb naming (`marshal factory dispatch --fleet` vs `marshal drain`)
stays provisional pending PRD Q-15, matching this epic's naming posture.
**Given** the eight pyforge stations with per-station ordered backlogs (tracked ledgers +
optional overrides) **When** the operator runs the one documented fleet-drain command
**Then** marshal applies the campaign mode (`drain_to_zero`, `leave_one`,
`skip_on_blocked` policies), preflights each dispatch (S-22.2's zombie refusal), launches
one story per station in parallel (S-22.5's per-station guard and untouched FR-184 clamp
posture), and chains each station's next story when merge-through-finalize completes
(S-22.4 with merge-in-agent: merge when CI green, scoped
`sprint-ledger-sync --project <station>`, spec promotion, queue regen) — the eight-station
2026-08-22/23 hand ritual replays without session discipline.

### Story 22.8: The session harness is profile-driven across agent CLIs
**Type:** feature • **Effort:** L • **Deps:** S-22.1 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-8)
**Surface:** `adapters/harness_bmadbuild.py` (the FR-52 seam, grown profile-plural), `core/harness_profile.py` (new), `data/harness_profiles/*.toml`, `ports/build_harness.py`, `cli/dispatch.py`, `core/policy.py` (new `harness_preference` key + the documented repo-defaults layer wired into `compose()`), `adapters/harness_bmadloop.py` (`[adapter].name` derivation)
**Note:** motivated live 2026-08-27: all three real dispatches (atlas/mason/marshal) died
instantly on the hardcoded `cursor agent` harness's auth wall — `binary_present()` was
necessary-but-insufficient (binary found on PATH, session dead on `Authentication
required`). Mirrors bmad-loop's own declarative CLI-profile pattern in marshal-owned code
(AD-3: marshal never imports `bmad_loop` outside `harness_bmadloop.py`).
**Given** a station dispatch **When** the operator's policy expresses an ordered
`harness_preference` **Then** the session launches under the first profile whose binary
resolves AND whose declared authcheck passes, every skipped candidate is a structured
finding (never silent — the cursor-auth failure mode becomes a named skip), the launched
argv is rendered from that profile's declarative template (worktree, prompt, per-CLI
model-flag spelling and trust/permission flags), and the SAME one policy preference drives
both engines — `marshal factory dispatch` directly, and bmad-loop via
`render_policy_toml`'s `[adapter].name` derivation — with the previous cursor behavior
preserved as the `cursor` profile.

### Story 22.9: A dispatch branch names its station
**Type:** bug • **Effort:** S • **Deps:** S-22.7 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-2/CAP-5)
**Surface:** `core/dispatch.py::dispatch_worktree_branch`, `cli/dispatch.py::_ensure_dispatch_worktree`, landing/status consumers of the branch name, tests
**Note:** found live 2026-08-27 pushing preserve snapshots: every dispatch branch renders
`marshal/<story_key>` with no station slug (mason 12.1 landed on `marshal/12.1`), and
`_ensure_dispatch_worktree` RESOLVES THE WORKTREE BY BRANCH NAME — so two stations sharing
a story key would silently reuse each other's worktree. Correctness at fleet-drain scale
(Story 22.7 multiplies branches across all eight stations), not cosmetics. Deps on 22.7
deliberately: its in-flight session edits `cli/dispatch.py`; implementing before it lands
manufactures a merge conflict.
**Given** a dispatch for station `<slug>` story `<key>` **When** the worktree branch is
derived **Then** it carries the station (`dispatch/<slug>/<key>`), no two stations can
collide on a shared story key, in-flight or preserved branches under the legacy
`marshal/<key>` name are still resolved (or documented as land-first), and every consumer
of the branch name (worktree lookup, in-flight conflict guard, landing, status overlay)
agrees on the one derivation.

### Story 22.10: `branch_merged` requires real divergence, not just ancestry
**Type:** bug • **Effort:** S • **Deps:** S-22.2 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-9)
**Surface:** `dispatch_supervisor/__main__.py::gather_dispatch_git_facts`, `tests/unit/test_dispatch.py`
**Note:** found live 2026-08-28 during a three-story fleet-drain session: every one of three
real dispatches (mason 12.7, atlas 20.5, mason 12.8) journaled `dispatch-completion`
`verdict: "completed"` (`branch_merged: true`) within ~2 seconds of launch, before the
dispatched session had done any work (`changed_paths: []`, `current_head_sha ==
baseline_head_sha`). Root cause: `is_branch_merged` shells `git merge-base --is-ancestor
branch into`, which is trivially true the instant a branch is forked from `into`'s own
current tip — true of every fresh dispatch, not evidence of a merge.
`resolve_dispatch_session_verdict` then trusts any journaled `COMPLETED`/`FAILED` verdict
without re-deriving it (`if journal.completion_verdict in {COMPLETED, FAILED}: return
that verdict`), so this false positive poisons the run's journal for its entire
lifetime — `marshal factory dispatch-resume`/`dispatch-attach` refuse with
`MRS-DISP-023` regardless of whether the dispatched session is genuinely still alive.
Live-recovered by hand three times in the same session before this story landed the fix.
**Given** a dispatch branch that has not diverged from its own launch `baseline_head_sha`
**When** the completion supervisor gathers git facts **Then** `branch_merged` reads
`false` regardless of what `is_branch_merged`'s ancestry check answers; **given** a branch
that HAS diverged (real commits past baseline) **When** the same check runs **Then** a
genuine "merged" ancestry answer is trusted exactly as before — this is a divergence
guard on an existing fact, not a new completion signal or a rewrite of CAP-2.

### Story 22.11: Station-scoped drain and an explicit story sequence

**Type:** feature • **Effort:** M • **Deps:** S-22.7 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-10; decomposed 2026-08-31 — motivated by a live incident the same day)
**Surface:** `cli/dispatch.py` (`drain`'s argparse + `run_fleet_drain`'s per-station backlog
read; `dispatch`'s argparse), `tests/unit/test_dispatch.py`
**Note:** found live 2026-08-31 wanting to complete just `pyforge-scribe`'s 2 remaining
backlog stories (the fleet's only story with a declared cross-station `Deps:` link in the
entire remaining backlog) without touching atlas's or marshal's own in-flight backlogs.
`drain`'s six flags (`--mode`, `--leave-remaining`, `--once`, `--max-cycles`,
`--tick-seconds`, `--campaign`) carry no station filter — it always reads all eight
stations' ordered backlogs and launches one story per station in parallel; `dispatch
<slug> <story>` launches exactly one story with no chaining at all. The only path available
was two manual `dispatch` calls with an operator polling for landing between them,
forfeiting `drain`'s chaining/preflight/campaign-journal machinery for no reason but scope.
**Given** `drain --mode <mode> --station <slug>` **When** a cycle runs **Then** the
campaign's chaining/preflight/journal (S-22.7) apply to exactly that station's own tracked
backlog, and every other station's backlog is provably untouched by the same invocation;
**given** `dispatch <slug> --stories <key1>,<key2>,...` **When** it runs **Then** the named
stories launch in that order via the same chaining `drain` already uses, one dispatch at a
time (not one agent handed the whole list — the epic's own "not backlog orchestration"
non-goal is unchanged); **given** a `--stories` key that is unknown or already done on that
station's tracked backlog **When** the command runs **Then** it refuses before any worktree
is provisioned, the same zombie-refusal discipline `drain` already applies; **given**
either new flag **When** a dispatch launches **Then** it reuses S-22.2's preflight,
S-22.4's landing, and S-22.10's divergence guard unchanged — no second preflight or landing
path is introduced.

### Story 22.12: A shared-surface diff also clears its own full suite, not just the station's bound gate
**Type:** feature • **Effort:** M • **Deps:** S-22.3 • **FR/AD:** FR-193 (spec-marshal-single-story-dispatch, CAP-12; decomposed 2026-09-11 — motivated by a live rescue the same day)
**Surface:** `dispatch_verify.py::evaluate_dispatch_verification` (the CAP-3 driver — reuses
the `changed` diff it already computes via `vcs.changed_files` for the scope check, no new
diff read), `core/gate.py` (new cross-surface check + finding code, alongside
`classify_outcome`/`check_scope_with_mode`), `tests/unit/test_dispatch_verify.py`
**Note:** found live 2026-09-10/11 rescuing steward Story 49.14: it passed CAP-3's bound
`pyforge-steward-test` gate and the harness's own targeted pytest run — whose review pass
explicitly considered and rejected "verification command misses platform tests" as
false — while shipping four real defects (a `ModuleNotFoundError` masking an unresolvable
`twine`/`rich` conflict, a genuine portal client-only boundary violation, a nested
`asyncio.run()` bug, and ruff findings) that surfaced only under a full
`platform-ci-local -- --test` run. GitHub Actions, the intended backstop for exactly this
class of gap, had been down fleet-wide the entire session, so the bound per-station command
was the only gate running. `MRS-GATE-010`/`011`'s fixed, anti-gaming per-station binding is
unchanged and always runs first — this is an additive gate, never a substitute for it, and
never configurable per station (the shared directory is `src/platform/`, hardcoded, matching
the CAP's own non-goal against reopening `MRS-GATE-011`'s binding).
**Given** a dispatched story whose diff (already read for the CAP-3 scope check) touches
only its own station's package **When** verification runs **Then** it lands exactly as
today — the station-bound command runs, no new gate is reached, and `evaluate_dispatch_verification`'s
existing verdict shape is unchanged; **given** a story whose diff touches `src/platform/`
**When** verification runs **Then** the station-bound `MRS-GATE-010`/`011` command runs
first and must pass on its own, and `pixi run -e local-recipes platform-ci-local -- --test`
additionally runs and must pass before CAP-4 land — a failure produces a loud, named
non-landing finding (never a silent skip, never downgraded to advisory) distinct from the
station-bound command's own findings; **given** the 49.14 fixture replayed (bound gate
green, full platform suite red) **When** verification runs **Then** the verdict is a
refusal naming the cross-surface gate, not a landing; and **given** any two stories whose
diffs both touch `src/platform/` **When** dispatched from different stations **Then** both
are held to the identical cross-surface bar — the check keys on the diff surface alone,
never on which station dispatched the story.

**Epic 22 clears to dispatch sequentially from Story 22.1** — 22.2/22.3 fan out after 22.1;
22.4 needs both; 22.5/22.6 need only their named deps; **CAP-7 fleet drain** is decomposed
as Story 22.7 (2026-08-27, backlog), with the companion
`spec-marshal-single-story-dispatch/fleet-drain-playbook.md` (validated 2026-08-22/23) as
the acceptance oracle for the full eight-station campaign. The Spec's remaining open questions
(enforceable budget signal; advisory's comparison basis; dedicated sidecar vs generalized
supervisor) are story-level design decisions inside 22.1/22.5/22.2 respectively, not
operator blockers.

## Epic 23: Velocity captures hand-driven work

**Goal:** FR-194: decomposes `spec-dashboard-velocity-captures-hand-driven-work`'s CAP-1..3
(Spec landed 2026-08-21 from `docs/dreams/dashboard-velocity-captures-hand-driven-work.md`;
`signal-inventory.md` is part of the contract). The console's velocity chart derives
active agent-compute exclusively from bmad-loop run journals, so a hand-driven story —
doctor 8.1–8.4, the 22-story dispatch session — shows nothing and the caption's "predates
loop instrumentation" is false for part of that bucket. The honest signal census: retroactive
active-compute is unobtainable; the implementable basis is wall-clock from the promoted
spec's `baseline_revision`/`final_revision` frontmatter (written by `bmad-dev-auto` — retired name, now `bmad-build-auto` —
preserved verbatim through promotion, reachable on main because landings use `--merge`).
Constraint carriers from the Spec bind every story: never fabricate (no-signal stories stay
absent), curated values byte-identical, per-story precedence (journal floor wins), the
all-or-nothing renderer contract, offline derivation, honest bound captions.

### Story 23.1: Wall-clock fallback derivation from promoted-spec revision fields
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-194 (spec-dashboard-velocity-captures-hand-driven-work, CAP-1)
**Surface:** `pyforge.doctor.sources.fleet_scan` (`scan_timing`)
**Note:** the Spec's open question on the wall-clock bound (final−baseline overstates by
the idle gap; first-commit-in-range understates) is resolved in-story; whichever bound is
chosen, the caption states what is measured — never an unqualified "duration".
**Given** a `done` story whose tracked/promoted spec carries resolvable
`baseline_revision`/`final_revision` and zero closed journal sessions **When** the local
generate runs **Then** a wall-clock duration is derived offline from local git commit
timestamps only; doctor's 8.1–8.4 carry timing marks; a re-run refreshes (never freezes)
derived values per the existing `derived: true` discipline; and a story with no resolvable
signal stays absent.

### Story 23.2: Wall-clock is never blended with active-compute
**Type:** feature • **Effort:** S • **Deps:** S-23.1 • **FR/AD:** FR-194 (spec-dashboard-velocity-captures-hand-driven-work, CAP-2)
**Surface:** `pyforge.doctor.sources.fleet_scan`, `docs/dashboard/index.html`
**Given** a line mixing both metric classes **Then** a reader can tell each story's class
from the rendered chart/caption alone — no wall-clock number appears as if it were active
agent-compute (the atlas precedent `scan_timing`'s own comments already mandate), and
warden's/atlas's curated numbers are byte-identical before and after.

### Story 23.3: The coverage caption partitions by true reason
**Type:** feature • **Effort:** S • **Deps:** S-23.1 • **FR/AD:** FR-194 (spec-dashboard-velocity-captures-hand-driven-work, CAP-3)
**Given** a line containing hand-driven stories **Then** the rendered caption names the real
absence classes — journal-measured / wall-clock-derived / spec-without-revision-fields /
no-spec-at-all — and no caption claims "predates instrumentation" for a story whose spec
carries revision fields.

**Epic 23 clears to dispatch sequentially from Story 23.1.** Convergence with Epic 22, not
dependence: 22.6's journal becomes the at-source producer for future stories; 23.1's
derivation covers already-landed work either way.

## Epic 24: Liveness is one command

**Goal:** FR-195: decomposes `spec-bmad-loop-liveness-footgun`'s CAP-1..3 (Spec landed
2026-08-21 from `docs/dreams/bmad-loop-liveness-footgun.md`; `convergence.md` is part of the
contract — it catalogs what adjacent shipped machinery already covers, so nothing here
re-mints Story 5.8's fallback, `loop_stall_check`, or supervised-run detection). The
`engine.pid` two-token format silently breaks the habitual `ps -p $(cat engine.pid)` check;
the correct answer already ships as `bmad-loop status <run_id> --json` and nothing in this
repo points at it — spec-3-7's deferred double-drive fix names the missing Marshal-side
primitive as its verbatim blocker. **HARD boundaries carried from the Spec:** no in-place
`bmad_loop` edits, no private-API imports, on-demand only (never a per-home probe in
`marshal status`'s fleet sweep — NFR-14 stands), and `unknown` stays `unknown`.

### Story 24.1: Marshal gains the missing liveness primitive
**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** FR-195 (spec-bmad-loop-liveness-footgun, CAP-1)
**Surface:** primitive home is the story's own design decision (the Spec's open question):
`ports/harness.py` (the seam spec-3-7 names as missing) vs a `scripts/*.py` helper vs a
`pyforge.doctor` source
**Given** a live run, a stopped run, and an absent/unreadable run directory **Then** a
Marshal-side primitive consuming `bmad-loop status <run_id> --json` returns `alive`,
`dead`, and `unknown` respectively — with zero reads of `engine.pid` and zero `bmad_loop`
imports, both assertable in its tests — and spec-3-7's deferred-work entry is updated to
name the primitive as existing.

### Story 24.2: The operator answer is one documented command
**Type:** docs+feature • **Effort:** S • **Deps:** S-24.1 • **FR/AD:** FR-195 (spec-bmad-loop-liveness-footgun, CAP-2)
**Given** the tracked operator instructions (the fleet landing-pass liveness step and its
team/auto-memory carriers) **Then** the supported one-command check is the primary
prescribed answer; no tracked instruction prescribes `cat engine.pid` /
`ps -p $(cat engine.pid)` or a bare `grep 'bmad-loop run'`; any surviving corroboration
grep matches all three engine argv forms `bmad-loop (run|resume|resolve)`; and the
2026-08-14 mason scenario (engine live under `bmad-loop resume`) answers correctly by the
documented steps alone.

### Story 24.3: An UNSUPERVISED row has a cheap, documented double-check
**Type:** docs+feature • **Effort:** XS • **Deps:** S-24.1 • **FR/AD:** FR-195 (spec-bmad-loop-liveness-footgun, CAP-3)
**Given** a run Marshal did not spawn (correctly reported `UNSUPERVISED`) **Then** the
documented follow-up for "is the engine actually alive?" is the S-24.1 primitive / S-24.2
command — resolving the Dream's 2026-08-15 scenario in one command — named wherever
UNSUPERVISED is explained, with `derive_home_state`'s row derivation untouched (Story 5.8's
territory per `convergence.md`).

**Epic 24 clears to dispatch sequentially from Story 24.1.** The unknown-verdict-at-resume
policy stays with spec-3-7's own deferred fix (this epic's Non-goal), matching the Spec.

## Story DAG (critical path and key dependencies)

```mermaid
graph LR
  S11[S-1.1 spine/verdict/findings] --> S12[S-1.2 identity]
  S11 --> S13[S-1.3 policy]
  S11 --> S19[S-1.9 packaging]
  S13 --> S14[S-1.4 provision]
  S14 --> S15[S-1.5 tier3 backlink]
  S14 --> S16[S-1.6 isolation verify]
  S15 --> S16
  S13 --> S17[S-1.7 preflight/seed/ack]
  S14 --> S17
  S14 --> S18[S-1.8 teardown]

  S13 --> S21[S-2.1 verify runner]
  S21 --> S22[S-2.2 verdict fold]
  S12 --> S23[S-2.3 scope check]
  S22 --> S23
  S22 --> S24[S-2.4 doc-only]
  S22 --> S25[S-2.5 gate ladder]
  S22 --> S26[S-2.6 evidence/egress]

  S15 --> S31[S-3.1 run id + journal writer]
  S31 --> S32[S-3.2 journal fold]
  S17 --> S33[S-3.3 detached launch]
  S31 --> S33
  S33 --> S34[S-3.4 supervisor lifecycle]
  S34 --> S35[S-3.5 idle strand]
  S35 --> S36[S-3.6 budgets]
  S34 --> S37[S-3.7 escalate/defer/resume]
  S32 --> S37

  S32 --> S41[S-4.1 promotion]
  S18 --> S42[S-4.2 teardown reachability]
  S41 --> S42
  S23 --> S43[S-4.3 merge subject/review-cap]
  S12 --> S43
  S32 --> S44[S-4.4 batch PR]
  S41 --> S45[S-4.5 feed refresh]
  S41 --> S46[S-4.6 idempotence/reconcile]
  S44 --> S46

  S16 --> S51[S-5.1 fleet view]
  S32 --> S51
  S51 --> S52[S-5.2 run detail]
  S51 --> S53[S-5.3 escalation queue]
  S51 --> S54[S-5.4 reconcile/contract]
  S45 --> S54

  S17 --> S61[S-6.1 adapter selection]
  S61 --> S62[S-6.2 projection]
  S62 --> S63[S-6.3 drift detect]
  S61 --> S64[S-6.4 probe]
  S62 --> S65[S-6.5 conformance smoke]
  S64 --> S65
  S21 --> S65
  S65 --> S66[S-6.6 matrix]
  S11 --> S67[S-6.7 entry-file drift]
  S11 --> S68[S-6.8 upstream register]
```

**Critical path:** S-1.1 → S-1.3 → S-1.4 → S-1.5 → S-3.1 → S-3.2 → S-4.1 → S-4.2. Everything the product sells (never-false-green, no-silent-burn, complete-paper-trail) hangs off it.

**Hard-story batch** (flip the dev model tier up before these; revert after): **S-1.1** (establishes every meta-test), **S-2.3** (the AD-26 × AD-27 intersection semantics), **S-3.1** (concurrency and durability protocol), **S-3.2** (the fold is the source of truth), **S-3.5** (supervisor decision semantics), **S-4.1** (durability predicate), **S-6.2** (projection mechanism table). The rest are mechanical.

**Frozen surfaces to declare as the build proceeds:** after S-1.1, `core/verdict.py` and `core/findings.py`; after S-3.1, `schemas/journal.json` and the journal entry shape; after S-5.4, `schemas/status.json`.

---

## Final structured JSON (historical — Epics 1-6 only, see note)

> **Stale, corrected 2026-08-15 (fleet-wide decomposition audit).** This block was written
> once, at the end of the original Epic 1-6 planning pass, and never updated as Epics 7-21
> were added over many later sessions — it read `"epics": 6, "stories": 40"` while the real,
> current file holds 21 epics and (per the frontmatter `storyCount` above, kept live) far
> more stories. Rather than hand-maintain a second, competing summary that will just drift
> again the next time an epic is added, this block is corrected once and marked historical:
> it accurately describes Epics 1-6's own critical path and coverage, not the whole file.
> The frontmatter's `epicCount`/`storyCount` fields (top of this document) are the
> up-to-date, actively-maintained totals — treat those as current, this block as archival.

```json
{
  "status": "historical — Epics 1-6 only, see note above",
  "project": "pyforge-marshal",
  "epics": 6,
  "stories": 40,
  "epic_list": [
    {"id": "E1", "title": "Provisioned, verified loop homes", "stories": 9, "frs": ["FR-1..FR-8", "FR-49..FR-57"]},
    {"id": "E2", "title": "Gates you can run", "stories": 6, "frs": ["FR-19..FR-27"]},
    {"id": "E3", "title": "Supervised unattended runs", "stories": 7, "frs": ["FR-9..FR-18"]},
    {"id": "E4", "title": "Landing with a durable paper trail", "stories": 6, "frs": ["FR-27", "FR-28..FR-35"]},
    {"id": "E5", "title": "Fleet visibility", "stories": 4, "frs": ["FR-36..FR-40"]},
    {"id": "E6", "title": "Portability proven", "stories": 8, "frs": ["FR-41..FR-48", "FR-58"]}
  ],
  "critical_path": ["S-1.1", "S-1.3", "S-1.4", "S-1.5", "S-3.1", "S-3.2", "S-4.1", "S-4.2"],
  "hard_stories": ["S-1.1", "S-2.3", "S-3.1", "S-3.2", "S-3.5", "S-4.1", "S-6.2"],
  "fr_coverage": "FR-1..FR-58 each owned exactly once; FR-27 spans E2 (gate re-run) and E4 (landing)",
  "nfr_coverage": "NFR-1..NFR-14 all traced in the coverage map",
  "ad_coverage": "AD-1..AD-39 all traced; AD-25..AD-39 originated from the architecture reviewer gate and are carried as Additional Requirements",
  "open_questions_carried": [
    "Q-2 AGENTS.md family ownership — S-6.7 ships detect-only until settled",
    "Q-3 PR-lifecycle automation — out of scope; S-4.4 stops at open/update",
    "Q-4 fleet-level resource budgets — out of scope; S-3.6 is per-run only",
    "Q-5 OTel gen_ai.* emission — out of scope; S-3.1 journal carries equivalent data",
    "Q-6 ACP migration trigger — out of scope; S-6.8 registers it upstream",
    "Q-7 idle threshold default (25 min) needs one wave of data — S-3.5",
    "Q-8 story difficulty declaration source — settled during S-6.1",
    "Q-9 conformance smoke story content — settled during S-6.5"
  ]
}
```

---

## Appendix A — Seed installer story DAG (Epics 7-12)

```
S-7.1 ──┬─→ S-7.2 ──→ S-7.3 (GUARD) ──────────────────────────┐
        │              ↘                                       │
        │               S-7.4 ──→ S-7.5 ──→ S-9.5              │
        └─→ S-7.6 (SPIKE-0 · GATES E10)                         │
                                                               │
S-7.4 ──→ S-8.1 ──→ S-8.2 ──→ S-8.3 ──→ S-8.4 ──→ S-8.5        │
                       ↘                    ↘                  │
S-7.2 ──→ S-9.1 ──→ S-9.2 ──→ S-9.3 ──→ S-9.6 ←────────────────┘
                       ↘  ↘
                        S-9.4 ─────────↗

S-7.6 + S-7.3 ──→ S-10.1 ─┐
S-7.3 ────────→ S-10.2 ───┼─→ S-10.3 ──→ S-10.4 ──→ S-10.5 ──→ S-10.6 ──→ S-10.7
S-9.6 ───────────────────┘                                   ↘
                                                              S-8.5

S-7.5 + S-8.4 ──→ S-11.1 ──→ S-11.2
S-10.3 + S-10.2 ──→ S-11.3 ──→ S-11.4 ←── S-11.1, S-8.3
S-10.5 ──→ S-11.5
S-7.4 + S-10.2 ──→ S-11.6

S-7.1 + S-11.6 ──→ S-12.1
S-10.6 + S-11.1 + S-11.2 ──→ S-12.2 (ORACLE)
S-10.7 + S-10.5 ──→ S-12.3
S-10.3 + S-11.4 ──→ S-12.4
S-10.7 + S-11.6 ──→ S-12.5 ──→ S-12.6
```

**Critical path (single builder, no parallelism):**
S-7.1 (S) → S-7.2 (XS) → S-7.3 (M) → S-7.4 (M) → S-7.5 (L) → S-8.1 (S) → S-8.2 (M) →
S-8.3 (M) → S-8.4 (M) → S-9.2 (M) → S-9.6 (M) → S-10.1 (M) → S-10.3 (M) → S-10.5 (M) →
S-10.6 (L) → S-10.7 (M) → S-11.1 (M) → S-11.3 (M) → S-11.4 (M) → S-12.2 (M) ≈ **38 days**.
Off-critical-path work (S-7.6, S-8.5, S-9.1/9.3/9.4/9.5, S-10.2/10.4, S-11.2/11.5/11.6,
S-12.1/12.3/12.4/12.5/12.6) adds ≈ 16 days ⇒ **~54 days ≈ 11 weeks**.

**S-7.6 (Spike-0) is off the critical path in duration but gates E10 in sequence** — it must
complete before S-10.1 starts, and it is cheap (S), so it should be run in parallel with E7's
back half.

---

## Special stories

| Story | Why it is special |
|---|---|
| **S-7.3** | The write guard. Everything downstream assumes it. Build it before anything writes. |
| **S-7.6** | Spike-0 — **gates E10**. A failure changes AD-52 or promotes a bespoke materializer. |
| **S-8.3** | The one algorithm that cannot be delegated to Copier; AR-1 and kill criterion K-01 live here. |
| **S-12.2** | The oracle. A non-empty plan that needs special-casing to fix triggers **K-02**. |
| **S-12.4** | Proves SC-08 — the structural guarantee that the update path cannot touch Tier-0/Tier-2. |

**Not a conda-forge effort.** Per PRD § D5, Genesis consumes `copier` from the existing
feedstock (consume-not-submit, G58) and authors no recipe. CLAUDE.md's CFE Rule 1 (invoke
`conda-forge-expert`) and Rule 2 (closeout retro) are **not** triggered by this epic set. If a
future story adds anything under `recipes/`, both rules apply to that story.

---

---

## Appendix B — Seed installer requirements inventory (Epics 7-12)

### Functional Requirements covered

All 62 FRs (FR-66–FR-127). No FR is deferred out of V1; the deferrals named in architecture § 7
(feature modules, `check --fix`, `eject`, model-as-separate-artifact, Windows parity beyond
`init`/`check`) are all outside the FR set.

### Non-Functional Requirements covered

All NFRs (NFR-O1 retired 2026-08-08 → NFR-12) (NFR-R1–R4, A1–A2, P1–P3, C1–C4, S1–S3, M1–M3, O1). NFR enforcement concentrates
in E12, but NFR-R4 (guard at the primitive) is E7 by necessity.

### Architecture Decisions covered

All 15 ADs (AD-51–AD-65) flow into specific stories. The 12 conflict-prevention patterns
(P-01–P-12) are implemented throughout E7–E11 and enforced as executable tests by S-12.4.

### FR / Story Coverage Matrix

| FR Range | Capability | Owning Story/Stories |
|---|---|---|
| FR-66–FR-68, FR-70 | Manifest as data, five classes, deferred state | S-7.4, S-7.5 |
| FR-69 | Coverage check (no unclassified artifact) | S-9.5 |
| FR-71 | Never-write path set declared | S-7.4, S-7.5 |
| FR-72–FR-78 | `marshal seed init` | S-10.7 |
| FR-79–FR-84 | `marshal seed adopt` detect→plan→apply, idempotent | S-10.6, S-9.6, S-12.5 |
| FR-80–FR-81 | Classification incl. `present-legacy` | S-9.2, S-9.4 |
| FR-82 | Machine-readable plan artifact | S-9.6 |
| FR-85–FR-87 | Preconditions, refusals, skips | S-10.4 |
| FR-88–FR-93 | `marshal seed check` | S-10.5, S-9.1 |
| FR-94 | Two-phase update | S-11.4 |
| FR-95 | Referenced-dependency verification | S-11.5 |
| FR-96–FR-97 | Migration ordering, applied-once, seeded opt-in | S-11.3 |
| FR-98–FR-99 | Regenerate managed / recompute derived / replace regions | S-11.4, S-8.3, S-11.1 |
| FR-100 | Never-write enforcement on update | S-7.3, S-12.4 |
| FR-101 | `--force` → `run_recopy` | S-10.1, S-11.4 |
| FR-102–FR-107 | State file | S-10.2 |
| FR-108–FR-113 | Managed regions | S-8.1, S-8.2, S-8.3, S-8.4, S-8.5 |
| FR-114–FR-117 | Agent adapter fan-out | S-11.1 |
| FR-118–FR-119 | In-package templates + `--template` override | S-7.5, S-10.1 |
| FR-120–FR-121 | Copier public API only; `--unsafe` gate | S-10.1 |
| FR-122 | Distribution (conda + wheel/sdist) | S-12.1 |
| FR-123–FR-124 | `--json` / `--quiet` / `--dry-run` | S-12.5 |
| FR-125 | `marshal seed version` (both versions) | S-11.6 |
| FR-126 | Distinct documented exit codes | S-7.2, S-12.5 |
| FR-127 | `marshal seed explain <artifact>` | S-11.6 |

### NFR / Story Coverage Matrix

| NFR | Subject | Owning Story/Stories |
|---|---|---|
| NFR-R1 | No partial application | S-10.3 |
| NFR-R2 | Git is undo (clean worktree) | S-10.4 |
| NFR-R3 | No conflict markers ever | S-8.3 |
| NFR-R4 | Guard at the write primitive | S-7.3, S-12.4 |
| NFR-A1, NFR-A2 | Air-gapped, zero egress | S-12.3 |
| NFR-P1–P3 | check < 5 s, adopt --dry-run < 10 s, init < 5 min | S-12.5 |
| NFR-C1–C4 | Python ≥3.12, copier range-pin, platforms, namespace share | S-7.1, S-12.1 |
| NFR-S1 | No untrusted execution by default | S-10.1 |
| NFR-S2 | No credential handling | S-12.3 (no network stack) |
| NFR-S3 | Templates validated against manifest | S-10.1, S-10.3 |
| NFR-M1 | Manifest is the single source of truth | S-7.4, S-11.1 |
| NFR-M2 | Oracle in Genesis's own CI | S-12.2 |
| NFR-M3 | Every finding documented with a remedy | S-9.1, S-12.6 |
| NFR-12 | Machine-readable plans and reports | S-9.6, S-12.5 |

### Success-criteria ownership

| SC | Owning story |
|---|---|
| SC-01 (master switch) | S-11.4 + S-11.7-equivalent coverage inside S-11.3/S-11.4 |
| SC-02 (empty-plan oracle) | **S-12.2** |
| SC-03 (adopt idempotent) | S-12.5 |
| SC-04 (refuse on hand-edited region) | S-10.4 |
| SC-05 (refuse on dirty worktree) | S-10.4 |
| SC-06 (offline, zero network) | S-12.3 |
| SC-07 (breaking model change absorbed) | S-11.3 |
| SC-08 (update cannot write Tier-0/2) | S-12.4 |
| SC-09 (init < 5 min) | S-12.5 |
| SC-10 (100% manifest coverage) | S-9.5 |

## Epic 25: Aligned to the installed BMAD era

**Goal:** decomposes `spec-bmad-611-era-alignment` CAP-1..7 (Spec landed 2026-08-22 from
`docs/dreams/bmad-611-era-alignment.md`; `alignment-inventory.md` carries the verified
findings each story closes, `horizon-watches.md` the named watch-don't-build triggers).
The 2026-08-21/22 upgrade made the stack RUN current; this epic makes the fleet BE
current — and guards it. **HARD boundaries carried from the Spec:** never adopt what
upstream is removing (no stories.yaml / folder+id / `{spec-folder}/stories/`), HOLD the
AGENTS.md managed block, watch-don't-build the TOML cutover and bmad-ticket tree, exact
TOML scalar types in policy work, `[dev] skill = "bmad-dev-auto"` stays, shims stay
installed until 25.1's guard is green.

### Story 25.1: Retired skill IDs are purged and guarded
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-1
**Surface:** 6 planning artifacts (5 epics.md + marshal PRD.md), `seed/templates/files/dream-first-workflow.md.j2`, AGENTS.md, 3 auto-memory entries, new meta-test
**Given** the published 20-shim list **Then** no retired ID survives in live docs, seed
templates, memory, or code (historical text glossed, not rewritten), and a new meta-test
reds any reintroduction — proven by passing on the swept tree and failing on a planted ID.

### Story 25.2: bmad-loop's repo skills match the installed package
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-2
**Surface:** `.claude/skills/bmad-loop-{setup,resolve,sweep}`
**Given** the package canon in `bmad_loop/data/skills/` (today 217/134/7 diff lines stale)
**Then** a diff-reviewed refresh lands and `bmad-loop validate` stays clean across all 8
loop homes.

### Story 25.3: Every spec folder accepts a 6.11 bmad-spec update
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-3
**Surface:** 22 spec folders across all 8 stations' `planning-artifacts/specs/`
**Given** the 8 frontmatter-less memlogs and 14 memlog-less folders **Then** each gains
6.11-valid frontmatter or a genesis-baseline `.memlog.md` (marshal S-13.7 bootstrap
pattern), and `memlog.py append` verifiably succeeds against all 22.

### Story 25.4: The 0.10/0.11 policy knobs are governable
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-4 (AD-16)
**Surface:** `core/policy.py`, `adapters/harness_bmadloop.py` render pipeline, `policy-defaults.toml`, loop-home policy re-render
**Given** `review.on_timeout`, `review.on_status_contradiction`, `limits.dev_contract_nudge`,
`operator.enabled`, `verify.stream_capture_kb` **Then** each flows through the
defaults→project→flags chain with a deliberate repo default and exact TOML scalar types
(0.11 rejects coercible mismatches), rendered policies pass `bmad-loop validate`, and the
marshal suite stays green.

### Story 25.5: Marshal speaks the 0.11 status vocabulary
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-5 (absorbs DW-BL011-1)
**Surface:** `cli/status.py`, `core/status.py`, `scripts/fleet_picture.py`, `scripts/loop_stall_check.py`
**Given** a parked (`awaiting-operator`) run, a `preserve_ref`-carrying task, and a
`sweeps_refused` record **Then** each is named where operators look (`marshal status`,
fleet-picture), the stall-check reports parked runs as `awaiting-operator (run bmad-loop
confirm)` instead of stalled, `preserve_ref` feeds the escalation-preservation flow, and
the false-green detector's premise text gains the 6.11 status-before-commit note —
fixture-driven tests throughout.

### Story 25.6: A hand-driven run's deferrals reach the ledger unaided
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-6 (closes DW-BL011-2)
**Surface:** `scripts/deferred_work_*.py`, `scripts/deferred_work_check.py` intake seam
**Given** a spec-frontmatter `deferred:` list in the shape of doctor's DW-14-1-1 (the
2026-08-22 canary) **Then** the pipeline ingests it into the tracked ledger without a
human relay — loop runs stay covered by bmad-loop's own `_harvest_spec_deferrals` bridge,
both sources honored, proven by fixture.

### Story 25.7: The factory's living docs are re-grounded, with a named owner
**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-7 (+ the spec's open question)
**Surface:** `architecture-bmad-infra.md`, 8 × `projects/<slug>/project-context.md`, SYNC-RUNBOOK
**Given** the retired reconciler skills **Then** `architecture-bmad-infra.md` describes the
6.11 infra (render pipeline, TOML layers, current skill set) and all 8 rulebooks are
re-grounded via plain agents with bumped `source_pin`s, and SYNC-RUNBOOK names the
recurring owner + cadence — resolving the spec's open question with a dated entry.

**Epic 25 clears to dispatch in full — all seven stories are independent.**

---

## Canopy obligations (2026-08-24)

Marshal station boundaries under the Canopy (`spec-pyforge-unifying-strategy`, steward-owned).
Planning retirement of `spec-factory-console` is effective immediately; generator /
pixi-task / `data.js` deletion is steward Story **30.2**. Do **not** mint marshal
epics that duplicate steward Canopy 18–30. **Epic 26** is the CAP-18 loop/runner hook.
**Epic 27** (2026-08-25) is station-owned SKF skill, persona, and first portal job.

**Five-tier symmetry.** Marshal's CLI tier is shipped (`pyforge-marshal` / `marshal` verbs).
Empty portal shell and host MCP remain steward 19/21. **Skill, persona, and the first portal
job are marshal Epic 27.** Marshal does not re-spec chrome or the event backbone.

**Uniform URL.** Marshal's Lane 2 portal mounts at **`/stations/marshal/`** under the single host
session — no station-specific origin, no bookmark-breaking slug outside the shared prefix.

**Chrome.** Portals mount **`django-pyforge`** shared chrome only — no second app switcher, no
duplicated Modernist shell, no marshal-only header fork.

**Service face.** Marshal capabilities surface through the estate MCP host and shared client
(CAP-4/CAP-6) — **no extra FastAPI port** or standalone marshal microservice outside the Canopy
service pattern.

**Supervisor ingest (deferred).** Publishing bmad-loop run state into the Canopy supervisor
(`public.run_state`, steward **Epic 21**) is **deferred** to steward; marshal-side ingest hooks
land **after** Epic 21 — not in this planning pass.

**Epic 16 is not Lane 1 CMS.** Epic 16 ("The board derives truth") governs **`docs/dashboard/`
generator path plumbing** only — slug→path resolution, loud failures, derived `data.js` fields.
It is **not** the Wagtail Lane 1 front door (steward CAP-2 / Epic 20). Generator work may
continue until steward 30.2 removes the static build path.

**Kedro-Viz.** `docs/dashboard/kedro-viz/**` remains atlas-owned publish output — not superseded,
not in marshal Canopy retirement scope.

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Marshal-local:** Loop/runner plugins are station hooks (Story **26.1**). A passed loop or story is not a PR quality verdict. Path B orchestration uses the Agent Canopy + station persona; Tachyon is only a production LLM endpoint the loop may be configured to call.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`.

## Epic 26: Loop/runner hook spec

**FR-45.** Deps: steward S-32.1. `pyforge-core` already exists (Epic 14); this story consumes S-32.1 rather than minting a second floor.

### Story 26.1: Extract the loop/runner hook

As a marshal operator,
I want the loop runner as a plugin on the shared contract,
So that swapping a runner or ACP adapter does not fork marshal.

**Type:** feature • **Effort:** L • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** the current runner **When** the hook spec lands **Then** it is the default plugin
**And** an alternate runner plugin can register without a process fork
**And** a passed loop is not published as a Warden (PR-gate) verdict

## Epic 27: Marshal owns its skill, persona, and one portal job

Does **not** copy Canopy 18–30. Supervisor *ingest from bmad-loop* stays architecture-Deferred (not this epic).

### Story 27.1: SKF domain skill and BMAD persona for marshal

As an autonomous agent,
I want a marshal SKF skill from `pyforge-marshal/` and a `bmad-agent-marshal` persona,
So that Path B uses CAP-5 grammar and CAP-4 MCP only.

**Type:** feature • **Effort:** L • **Deps:** S-26.1 • **FR/AD:** canopy FR-37, FR-38 • canopy:AD-17
**Given** steward 29 proved the shape **When** this story completes **Then** SKF compiles from `src/shared/packages/pyforge-marshal/` if missing
**And** the persona uses only `pyforge marshal …` and `POST /stations/marshal/mcp`

### Story 27.2: First portal slice — list loop homes

As a marshal operator,
I want `/stations/marshal/` to list provisioned loop homes,
So that one operator job works in HTMX on the host.

**Type:** feature • **Effort:** M • **Deps:** S-27.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated marshal-role session **When** the operator opens `/stations/marshal/` **Then** homes list via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy
**And** this story does not implement bmad-loop → supervisor ingest

## Epic 28: Token economy — the loop reads less, says less, and re-learns nothing

Decomposes `spec-marshal-token-economy` (CAP-1..CAP-17; CAP-11/CAP-12 added 2026-08-30
from the operator's model/cost catalog — Stories 28.10/28.11; CAP-14/CAP-15 added
2026-08-31 from a live dispatch-ordering/retry incident — Stories 28.12/28.13; CAP-16/
CAP-17 added 2026-08-31 from the same incident's landing — Stories 28.14/28.15; Dream:
`docs/dreams/marshal-token-economy.md` + `docs/dreams/marshal-dependency-aware-dispatch.md`).
Addendum F (2026-09-01) — `spec-marshal-drain-self-resolution` CAP-1..6 / Stories
28.18–28.23 — is residual self-heal after 28.12–28.17 shipped.
Marshal owns spend *brakes* (E3 ceilings, idle
ladder, NFR-14 cache discipline, FR-51 tiering); this epic adds spend *shrinkage* as a
policy-rendered, Genesis-seeded, supervisor-metered context pipeline over five
already-packaged instruments (headroom-ai, caveman, codegraph, cocoindex, graphifyy).
Constraints binding every story (spec § Constraints): never compress the contract
(specs/ACs/verdicts/escalation), never break the provider prompt cache (prefix
byte-identical), reversible-or-absent (CCR), BSL boundary (`@caveman-ai/cli` stays out),
telemetry advisory only (no second gate), per-layer graceful degradation (an unavailable
instrument disables its layer with a named finding, never blocks a run — all five
instruments are pixi-ACTIVE since 2026-08-30 per `docs/dreams/pixi-candidate-currency.md`;
degradation now governs non-linux platforms — caveman/codegraph are linux-64-only — and
future regressions).

### Story 28.1: The context policy block, rendered once for both engines

As a marshal operator,
I want the context pipeline declared in `EffectivePolicy` and rendered into every launch surface,
So that compression and indexing are policy, not per-home hand-configuration.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-1
**Given** a policy with no `[context]` block **When** a run launches **Then** every layer is off and behavior is byte-identical to today
**And** with a block present, bmad-loop spin and factory dispatch resolve the same declaration from one composition site
**And** `schemas/policy.json` validates the block and provenance reporting covers its keys

### Story 28.2: Wire compression at the harness seam

As a marshal operator,
I want sessions launched through the wire-compression layer when policy enables it,
So that tool outputs, logs, and file reads compress before the provider call — reversibly.

**Type:** feature • **Effort:** L • **Deps:** S-28.1 • **FR/AD:** token-economy CAP-2
**Given** an enabled `[context]` wire layer **When** spin/dispatch launches a session **Then** the harness-profile wrapper demonstrably wraps the CLI and the CCR store is loop-home-scoped
**And** a compressed artifact is retrievable byte-exact via the store
**And** the prompt prefix (system prompt, tool defs, older turns) is byte-identical wrapped vs unwrapped
**And** when the instrument is unavailable the layer disables with a named finding, never a blocked run

### Story 28.3: Genesis seeds the token-economy kit

As a marshal operator,
I want `marshal seed` to install and `marshal seed check` to verify the per-loop-home kit,
So that output compression and the code-structure graph exist by provisioning, not ritual.

**Type:** feature • **Effort:** L • **Deps:** S-28.1 • **FR/AD:** token-economy CAP-3, CAP-4
**Given** a seeded loop home **When** `marshal seed check` runs **Then** it verifies caveman-skill deployment, CCR store dir, and a present+fresh codegraph index
**And** dev-session speech compresses while verdicts, journals, and escalation context stay fully articulated
**And** an unavailable instrument (pixi blocker, platform gap) reports a named finding and the seed still applies

### Story 28.4: Savings telemetry in journals and status

As a marshal operator,
I want per-layer savings recorded next to per-story spend and rendered mid-run,
So that economy is observable while a run lives, not archaeology after it dies.

**Type:** feature • **Effort:** M • **Deps:** S-28.2 • **FR/AD:** token-economy CAP-7
**Given** a live run with layers enabled **When** the supervisor ticks **Then** journal entries carry per-layer savings fields alongside the weighted spend tally
**And** `marshal status` renders spend and savings for the running story (chips at DW-FU-3-6-6)
**And** savings numbers never feed a pass/fail verdict

### Story 28.5: The pinned wrapped-vs-unwrapped benchmark

As a marshal operator,
I want a re-runnable same-story benchmark with layers off vs on,
So that ceilings recalibrate against our measurement, not upstream marketing numbers.

**Type:** feature • **Effort:** M • **Deps:** S-28.2, S-28.3 • **FR/AD:** token-economy CAP-9
**Given** the pinned benchmark story **When** the harness runs both legs **Then** it emits a per-layer before/after weighted-token comparison artifact
**And** the on-leg lands the same story: same verdict, same gate results, reviewer never skipped
**And** the ceiling-recalibration note cites the artifact

### Story 28.6: The graduated compression ladder

As a marshal operator,
I want compression aggressiveness to escalate before the kill ladder fires,
So that a story nearing its ceiling gets cheaper before it gets dead.

**Type:** feature • **Effort:** M • **Deps:** S-28.4 • **FR/AD:** token-economy CAP-8
**Given** a story approaching its token ceiling **When** the supervisor evaluates the ladder **Then** compression escalation strictly precedes stop-retry-defer
**And** escalation is compression-only — the launched model is unchanged (model movement
  stays with FR-51 declared difficulty and Story 3.12's floor-raise;
  `spec-adaptive-model-tiering` forbids downgrades)
**And** no gate or reviewer is ever skipped by escalation

### Story 28.7: Index freshness is an advisory finding

As a marshal operator,
I want `marshal check` to report codegraph/cocoindex staleness,
So that a stale index is a named admission signal, not a mid-run surprise.

**Type:** feature • **Effort:** S • **Deps:** S-28.3 • **FR/AD:** token-economy CAP-10
**Given** a stale or missing index **When** `marshal check` runs **Then** a named advisory finding reports it
**And** the exit-code domain `{0, 1, 2, 3, 4, 130}` is unchanged and the finding alone never blocks a run

### Story 28.8: Derived context recomputes only on source change

As a marshal operator,
I want epic-context and continuity distills maintained as incrementally-derived artifacts,
So that an iteration never recompiles planning context whose sources did not change.

**Type:** feature • **Effort:** L • **Deps:** S-28.1 • **FR/AD:** token-economy CAP-5
**Given** two consecutive iterations with unchanged planning sources **When** the second routes its story **Then** zero recompute occurs
**And** a planning-source edit yields exactly one refresh (cocoindex flow)
**And** BMAD skill semantics are untouched — only the freshness mechanism changes

### Story 28.9: Planning-graph retrieval behind the Scribe seam

As a marshal operator,
I want story routing to retrieve scoped planning context from the graph when the seam exists,
So that an epic-path iteration never loads `epics.md`/`prd.md` wholesale.

**Type:** feature • **Effort:** L • **Deps:** S-28.8, scribe S-6.3 • **FR/AD:** token-economy CAP-6/CAP-13
**Given** the Scribe-owned GraphStore seam is available **When** step-01 routes an epic story **Then** the iteration completes within the epic-context token target with zero full-document loads
**And** disabling the seam proves the epic-context-file fallback
**And** marshal consumes the graph — it does not build a second one
**And** a graph answer whose backing node is flagged `stale` (scribe Story 6.3) falls back to the epic-context file path (Story 28.8) rather than being served silently

### Story 28.10: The model-cost catalog makes spend legible in dollars

As a marshal operator,
I want a declared price table rendered from policy and consumed by telemetry and the benchmark,
So that spend and savings read in estimated dollars, not just weighted tokens.

**Type:** feature • **Effort:** M • **Deps:** S-28.1, S-28.4 • **FR/AD:** token-economy CAP-11
**Given** a policy with the cost catalog declared (seed: `spec-marshal-token-economy/model-economics.md`) **When** the supervisor journals **Then** per-story spend and savings carry dollar estimates derived from declared prices
**And** with no catalog declared, dollar fields are absent — never fabricated
**And** per-provider token weights (e.g. cache-read) derive from declared ratios, global constants as fallback
**And** no code path fetches prices from a network; figures stay advisory (no verdict, no exit-code change)

### Story 28.11: Difficulty tiers route across providers and pools

As a marshal operator,
I want tier entries to name (harness, model) pairs across providers with subscription pools preferred,
So that easy stories run on economy-class models and flat-rate pools drain before metered API.

**Type:** feature • **Effort:** L • **Deps:** S-28.10 • **FR/AD:** token-economy CAP-12
**Given** a populated cross-provider tier map **When** a story with a declared difficulty launches on either engine **Then** the launched (harness, model) pair matches the map — proven by rendered-launch diff
**And** subscription-marked pools are preferred and the serving pool is journaled; an exhausted or unavailable pool falls through, never blocks
**And** this remains the FR-51 seam — no second selection mechanism, run-level batching unchanged
**And** the review stage never routes below the policy-declared review floor

### Story 28.12: Dependency-derived dispatch ordering

As a marshal operator,
I want `factory drain` to compute dispatch order from each story's declared `Deps:` instead of raw ledger order,
So that a station's backlog never dispatches a story ahead of an unmet dependency, including across epics.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-14
**Given** a station's tracked backlog with a `Deps:` graph spanning more than one epic **When** `factory drain` runs with no `--stories` override **Then** the computed dispatch order never violates a declared `Deps:` edge
**And** stories with no unmet dependency either way fall back to ledger order (deterministic, no invented preference)
**And** `--stories` continues to work unchanged as an explicit override

### Story 28.13: Sanctioned retry after an operator-initiated stop

As a marshal operator,
I want an externally-stopped dispatch distinguished from a genuinely failed one, and a documented retry path for the former,
So that stopping a run to reprioritize never permanently blocks that story, and a retry never silently steps on uncommitted work or misreads a dead worktree as live.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-15
**Given** a dispatch session stopped by SIGTERM from outside marshal's own idle/budget ladder **When** the journal records the outcome **Then** it is not recorded as `failed` the way a genuine verdict/review/crash failure is
**And** the story is retryable through `drain`/`dispatch --stories` without the undocumented bare-`dispatch <slug> <story>` workaround
**And** a retry against a worktree already carrying uncommitted changes reports the diff (file count, line count) before proceeding
**And** liveness detection (`MRS-DISP-011`) does not treat leftover uncommitted worktree changes alone as proof a session process is still alive
**And** `MRS-DISP-011`'s refusal while a session process is genuinely still alive is unchanged

### Story 28.14: Auto-derived effective surface, no manual per-story widening

As a marshal operator,
I want `policy_surface` resolution to auto-derive a safe per-station default at spin/dispatch time,
So that `MRS-GATE-007` never requires hand-widening `[epic_surfaces]` per story to let legitimate, within-station work land.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-16
**Given** a story touching only files under its own station's package tree and the common bookkeeping paths (`.gitignore`, `pixi.toml`, `pixi.lock`, `environment.yaml`, `scripts/.spec-surface-baseline.json`) **When** verification runs with zero `[epic_surfaces]` entry declared **Then** `MRS-GATE-007` passes
**And** a story touching a different station's package, or repo config outside the computed default, still fails `MRS-GATE-007` — cross-station containment is preserved
**And** an existing `[epic_surfaces]` entry that narrows further continues to behave exactly as today (AD-27's intersection-only combinator is unchanged)

### Story 28.15: Scope-violation enforcement mode, policy-declared, default warn

As a marshal operator,
I want a per-station `hard`/`warn`/`off` policy flag for `MRS-GATE-007`/`008`, defaulting to `warn`,
So that scope violations stay visible without permanently deadlocking an autonomous drain, with `hard` (today's non-waivable refuse) and `off` (no check at all) available as explicit opt-in per station.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-17
**Given** no scope-violation mode declared **When** a scope violation occurs **Then** it lands as a named, journaled advisory finding and does not refuse landing (the new `warn` default)
**And** with `hard` declared for a station **When** a scope violation occurs **Then** behavior reproduces today's non-waivable refuse exactly
**And** with `off` declared for a station **When** files change **Then** `MRS-GATE-007`/`008` are not evaluated at all — zero findings, zero journal entries
**And** `marshal status`/`fleet-picture` render a `warn`-mode violation finding, not journal-only
**And** the mode is per-station — one station's declared mode never changes another's

### Story 28.17: Verify-fail terminalization and transient auto-redispatch

As a marshal operator,
I want a verify-refused dispatch with a dead session to terminalize as failed with preserve,
So that overnight `--stories` drains retry transient test failures instead of heartbeating LIVE forever.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-verify-fail-terminalization CAP-1..3
**Given** a dispatch whose build session is dead, verify outcome is `refused`, and git shows progress beyond baseline **When** the dispatch supervisor ticks **Then** it journals completion verdict `failed`, captures `failed/<story>/changes.patch`, and exits (no further LIVE heartbeats)
**And** with the same verify outcome but the session process still alive **When** the supervisor ticks **Then** verdict remains `LIVE` unchanged
**And** after a terminalized run with `MRS-GATE-001` **When** the next fleet `drain --once` cycle runs **Then** the story is not permanently blocked by `MRS-DRAIN-005` and may redispatch (transient retry)
**And** sibling to Story 28.13 — does not replace SIGTERM/stopped taxonomy

### Story 28.16: Parallel dispatch fan-out when deps and surfaces are disjoint

As a marshal operator,
I want factory drain to launch more than one story per wave on a single station when dependencies are satisfied and effective surfaces are provably disjoint,
So that unrelated backlog stories are not blocked by a slow or zombie head-of-line story whose WIP cannot collide with them — without weakening per-story LIVE semantics.

**Type:** feature • **Effort:** M • **Deps:** 28.12 • **FR/AD:** spec-marshal-parallel-dispatch-fanout CAP-1..5
**Given** `dispatch.max_parallel` unset or `1` **When** `factory drain` runs **Then** within-station behavior is byte-identical to today's serial drain
**And** with `max_parallel>1` and two ready stories whose effective frozen surfaces are pairwise disjoint **When** a wave is computed **Then** both dispatch on separate worktrees in one wave
**And** story A live by git facts does not refuse unrelated story B unless B depends on A or surfaces intersect
**And** `dispatch-wave` journal entries and `marshal status`/`fleet-picture` show wave membership and refused candidates with reason
**And** `judge_dispatch_completion()` per-story LIVE semantics are unchanged

Operational note: `pyforge-marshal`'s `[epic_surfaces]."28"` was widened to a
station-wide wildcard (`src/shared/packages/pyforge-marshal/**` + common
bookkeeping paths) as an immediate stopgap on 2026-08-31, unblocking the live
Epic 28 drain campaign without waiting on this story's own implementation.
This story ships the real mechanism to replace that stopgap.

### Story 28.18: Re-preflight when the refuse predicate can change

As a marshal operator,
I want a live `drain_to_zero` campaign to re-evaluate a previously-refused backlog head when the refuse depends on disk or API state,
So that landing a missing spec (or a mergeable flip) does not require a new campaign or a bare `factory dispatch`.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-1
**Given** a station refused on `MRS-DISP-005` **When** a unique `spec-<e>-<n>-*.md` appears on the specs path the campaign uses **Then** the next eligible tick dispatches that story without `MRS-DRAIN-005` permanent block
**And** an unchanged refuse predicate is rate-limited and journaled, not silently looped
**And** expensive `verify_commands` re-run only when the refuse predicate-hash changes
**Status:** backlog

### Story 28.19: Missing-spec escalates, never idle-with-backlog

As a marshal operator,
I want `MRS-DISP-005` to surface as `awaiting-operator` (or fleet-picture ATTENTION) with the expected spec path,
So that a station with remaining backlog never looks idle.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-2
**Given** a ledger key whose specs glob matches zero files **When** drain preflight refuses **Then** the station is `awaiting-operator` (or ATTENTION-named), not idle
**And** the remedy names the expected `planning-artifacts/specs/spec-<e>-<n>-*.md` path
**And** v1 does not auto-author a stub spec
**Status:** done

### Story 28.20: CAP-4 land heals mechanical and DIRTY PRs

As a marshal operator,
I want land to union ledger-only conflicts and to advance `main` when git is clean but GitHub is `DIRTY`,
So that a PR like #985 does not wait on a chat session.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-3
**Given** a PR whose only conflict is `sprint-status-ledger.yaml` **When** land runs **Then** keys union with `done` beating `backlog`, the branch is pushed, merge is retried
**And** if `merge-tree` is clean and GitHub `mergeable` is false **Then** marshal advances `main`, retires the PR, resyncs the ledger
**And** unknown conflict paths escalate named — never wait silently
**Status:** done

### Story 28.21: Push the dispatch branch before verify can strand it

As a marshal operator,
I want `origin/dispatch/<slug>/<story>` to exist as soon as the session has a commitable result,
So that a verify refuse cannot leave finished work only in a local worktree.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-4
**Given** a dispatch worktree with a story commit **When** verify later refuses **Then** `git ls-remote` still shows `dispatch/<slug>/<story>`
**And** "next steps: open a PR" in a session log is not an acceptable substitute
**Status:** done

### Story 28.22: Verify blast radius is pre-existing-gate, not story-refuse

As a marshal operator,
I want a `verify_commands` failure outside the story diff and effective surface classified as `pre-existing-gate`,
So that a pandas collection error in `tests/packaging` cannot refuse a marshal story and 28.17 cannot loop the same unrelated red.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-5
**Given** a story diff that does not touch the failing packaging test **When** `pyforge-deps-test` collection-fails on pandas **Then** the finding is WARN `pre-existing-gate`, not `MRS-GATE-001` refuse
**And** `pyforge-marshal-test` still refuses when the marshal package tests fail
**And** transient redispatch into the same unrelated red command does not fire
**Status:** done

### Story 28.23: Stranded-work signal after terminal verify-fail

As a marshal operator,
I want dead+`failed` to look idle, and an unpushed dispatch branch or open unmerged PR to be named in ATTENTION,
So that fleet-picture STUCK is reserved for a live refuse and stranded work is visible.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-6
**Given** completion `failed` or `stopped_externally` and a dead dispatch tail **When** `marshal status` / fleet-picture run **Then** the home is not `verifying` / STUCK
**And** an unpushed `dispatch/<slug>/<story>` or open unmerged PR is named in ATTENTION
**And** the overlay half (`20e88e8b0f`) stays locked by test
**Status:** done

### Story 28.24: Supervisor finalizes when the harness cannot run shell

As a marshal operator,
I want the dispatch supervisor to commit, push, and verify when the Cursor session cannot run shell,
So that a “done + dirty leftover” story does not wait for chat (28.18 / PR #1000).

**Type:** feature • **Effort:** S • **Deps:** 28.21 • **FR/AD:** spec-marshal-drain-self-resolution CAP-7
**Given** a dispatch worktree with a commitable dirty tree and a session that reported done or “shell unavailable” **When** the supervisor tick runs **Then** marshal commits the leftover, pushes `origin/dispatch/<slug>/<story>`, and runs `verify_commands`
**And** drain does not redispatch the same story solely because of `MRS-DISP-036` without that finalize attempt
**And** if supervisor shell also fails, the station is `awaiting-operator` naming the worktree path
**Status:** done

### Story 28.25: Finalize escalations self-clear past a later success

As a marshal operator,
I want a station's finalize-escalation report to reflect its newest dispatch run, not any past failure buried in history,
So that fleet status stops naming a worktree that is already gone and work that already landed.

**Type:** fix • **Effort:** S • **Deps:** 28.24 • **FR/AD:** spec-marshal-drain-self-resolution CAP-7 (incident 2026-09-10: pyforge-marshal/33.2)
**Given** a station whose most recent dispatch run for one story failed to finalize, and a later dispatch run for a different story on the same station has since completed **When** `gather_fleet_finalize_escalations` (`cli/dispatch.py`) walks that station's run history **Then** it reports no escalation for the station once a newer run supersedes the failed one, instead of walking arbitrarily far back past successful runs to the oldest matching failure
**And** an escalation naming a worktree path that no longer exists on disk is treated as resolved, not active
**And** `marshal status`/`fleet-picture`'s `awaiting-operator` row clears accordingly, with no change to the case where the newest run is itself the one still stuck
**Status:** done

### Story 28.26: CAP-4's own feed-sync guards missing keys too, not just regressions

As a marshal operator,
I want `_promote_sprint_ledger`'s (`cli/land.py`) feed-sync step to refuse a promotion that would drop any twin-only key, not just one moving out of a protected state,
So that CAP-4's fully-autonomous auto-land path cannot silently wipe a freshly-authored epic's still-backlog stories the moment it lands that epic's first story.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-drain-self-resolution CAP-4 (incident 2026-09-10: pyforge-warden Epic 12, restored PR #1117)
**Note:** Story 48.1 (pyforge-steward) fixed this exact class of bug in `scripts/promote_sprint_status.py`'s own standalone `main()` CLI (the `sprint-ledger-sync` / `--repair-feed` path) — but confirmed, by reading its own scope in epics.md, that it does not touch `cli/land.py`'s separate internal call site, which CAP-4's auto-land path uses directly (`promote_mod.regressions()`/`render()`, never `main()`). Found live 2026-09-10: `_promote_sprint_ledger` auto-landed pyforge-warden's Story 12.1, then its own post-land feed-sync step promoted the tracked ledger from warden's stale Tier-3 feed (which had never learned of the freshly-authored Epic 12) and silently dropped Epic 12's five still-backlog stories plus the epic/retrospective rows — `regressions()` alone never caught it, since a `backlog` key is not a protected state.
**Given** a station's tracked twin carries a key absent from its incoming Tier-3 feed, regardless of that key's status **When** `_promote_sprint_ledger`'s feed-sync step runs **Then** the promotion is refused (WARN-named, matching the existing regression-refusal shape) rather than silently written with that key dropped
**And** a feed that is a superset of (or equal to) the twin's own keys still promotes normally — this only refuses on any key disappearing, not on new keys appearing
**And** the existing `regressions()`-based refusal (a key moving OUT of `done`) is unchanged, this is additive
**Status:** done

### Story 28.27: Planning-graph is proven live for dispatch — extend the win fleet-wide

As a marshal operator,
I want the `planning-graph` context layer enabled for every station, not just marshal,
So that every dispatch session's epic-routing gets grounded, token-cheap planning context instead of loading `epics.md`/`PRD.md` wholesale.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** token-economy CAP-6/CAP-13 (verified live 2026-09-10)
**Note:** Live-verified before filing, not assumed: `marshal context retrieve --project pyforge-marshal --epic 20 --format json` (the exact command `bmad-build-auto`'s own `step-01-clarify-and-route.md` runs during dispatch) returned `"verdict": "clean"`, `"mode": "graph"`, `"grounded": true`, `"tokens_saved": 109500` — a single real call. Unlike the other four layers, this one requires ZERO new engineering: the skill-file wiring (Story 28.9), the CLI command, and scribe's `recall` grammar are all already built and working end-to-end. The only reason it isn't fleet-wide already is that `[context].planning-graph` was only ever turned on in `pyforge-marshal`'s own `marshal-policy.toml` (Story 33.2, scoped to marshal as a canary).
**Given** the other 7 stations' `marshal-policy.toml` (`pyforge-atlas`, `-steward`, `-warden`, `-doctor`, `-herald`, `-mason`, `-scribe`) **When** each gets a `[context.planning-graph]` `enabled = true` override, mirroring marshal's own **Then** `marshal context retrieve --project <slug> --epic <N> --format json` returns `grounded: true` with a positive `tokens_saved` for at least one real epic per station
**And** a station whose scribe graph has no coverage for a given epic degrades to `epic-context-fallback` cleanly (already-proven behavior, not a regression risk)
**And** `wire`/`output`/`structure-graph`/`derived-context` stay exactly as they are for these stations — this story touches only the one proven-working layer
**Status:** done — a second, deeper bug was found and fixed in the same pass: `scribe recall`'s lexical/semantic scoring had no project-scoping at all, so a query naming any project could be outscored by a DIFFERENT project's more lexically-dense document (verified live: a `pyforge-warden` query returned a `pyforge-marshal` citation before the fix). Closed by adding `scope=`/`--scope` end-to-end (`recall.py::answer`/`_answer_semantic`, `scribe recall --scope`, marshal's `render_scribe_recall_argv`/`ScribeCli.recall`/`run_context_retrieve`) — filters candidates to the requested project's own `_bmad-output/projects/<slug>/` citation tree before scoring. Re-verified after the fix: all 7 stations return `grounded: true` with a citation genuinely under their own project tree.

### Story 28.28: Scribe exposes caller-declared derived-context refresh, closing the CAP-5/CAP-6 gap

As a marshal operator,
I want `scribe index refresh` to accept a caller-declared artifact manifest, not just its own two hardcoded registrations,
So that marshal's `derived-context` layer (Story 28.8) — plumbing already built and already invoked by every dispatch session — actually engages instead of degrading every single time.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-5 (scribe-side half; marshal's consumer half already shipped, Story 28.8) — live incident 2026-09-10
**Note:** `adapters/scribe_cli.py`'s own docstring already names this exact gap: "Scribe 6.2 shipped the generic 'declare sources -> derived artifact' ENGINE (`DerivedArtifact`/`refresh_incremental`) and wired its own two registrations into `scribe index refresh`... The caller-declaration option itself is scribe-side surface that had not landed when this story was implemented, and marshal may not add it." Live-verified 2026-09-10: `marshal context refresh --project pyforge-marshal --epic 20` reports `MRS-CTX-002`, `scribe index refresh --declare ... exited 2`; direct check confirms `scribe index refresh --help` has no `--declare` option at all, only `--target`. `refresh_incremental()`'s `DerivedArtifact.derive` is a zero-arg callback scribe cannot synthesize for an arbitrary caller-declared artifact (the actual content regeneration is the AI agent's own job, done via its skill instructions when told a source changed) — so the CLI addition's `derive` per declared artifact must be a no-op (fingerprint-bookkeeping only), never content generation; scribe's role here is staleness-tracking, not authoring.
**Given** a manifest JSON (marshal's own `declarations[].{name,sources,output}` shape, already written today at `.claude/data/pyforge-marshal/derived-context/<slug>-epic-<N>.json`) **When** `scribe index refresh --declare <manifest-path>` runs **Then** it fingerprints each declared artifact's sources via the existing `refresh_incremental()` engine (scoped to a caller-namespaced index file, never colliding with scribe's own graph/move-list index), and prints the same `refreshed: ...; skipped (unchanged): ...` report line `core/derived_context.py::parse_refresh_report` already parses
**And** a `derive()` no-op means `refresh_incremental()` only ever reports an artifact `refreshed` (first-seen or source-changed) or `skipped` (unchanged) — it never fails from a derive-side exception
**And** an unparseable or missing manifest exits non-zero with a clear message — `ScribeCli.refresh()`'s existing degrade-to-off handling on the marshal side already covers that failure shape, unchanged
**And** `marshal context refresh --project pyforge-marshal --epic 20 --format json` (the exact live-verification command from this story's own Note) returns `"mode": "incremental"` with no `MRS-CTX-*` finding, proving the fix end-to-end
**Status:** backlog

### Story 28.29: Wire is dead for cursor specifically — copilot is a real but uncertain alternative, documented either way

As a marshal operator,
I want the `wire` layer's dispatch-time reason to name the real, permanent cause for cursor, and a recorded, evidence-based verdict on whether switching to copilot is worth it,
So that a future operator does not re-discover either finding from scratch, and does not assume "wire is just broken everywhere."

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** token-economy CAP-2 (incompatibility + alternative-harness finding, 2026-09-10)
**Note:** Live-verified 2026-09-10, two-part finding. **Cursor is dead**: `headroom wrap cursor --help` is IDE-only — "Cursor reads its API configuration from its settings UI, not from environment variables... open Cursor and configure Settings > Models > OpenAI API Key > Advanced > Override Base URL" — a human clicking a GUI. Marshal's dispatch fleet uses `cursor-agent`, the headless standalone CLI, launched detached with no GUI at all; there is no headless integration path, full stop. **Copilot is a real, more complex, quota-uncertain alternative**: `headroom wrap copilot [COPILOT_ARGS]...` IS a genuine headless wrap (BYOK provider routing through a local proxy, positional passthrough args — no GUI dependency), and marshal already ships a `copilot.toml` harness profile (Story 22.8). But: (a) the wrap invocation is materially more complex than claude's simple argv-prefix (`--backend`/`--provider-type`/`--subscription`/`--native` flags select how Copilot's BYOK routing works — `core/harness_profile.py::resolve_wire_wrap`/`render_dispatch_argv`'s current wrap-composition logic assumes claude's simple shape and would need real adaptation, not a one-line profile edit); (b) `copilot.toml`'s own `notes` already record a LIVE, OBSERVED quota failure on this exact machine (2026-08-27: "reached the service but failed rc=1 'You have no quota'") — Copilot has its own billing/quota ceiling, so switching to it is not a free lunch, just a different spend to manage; (c) of headroom's other wrap targets (`codex`, `aider`, `grok`, `goose`, `openhands`, `opencode`, etc.), none match any of marshal's other four harness profiles (`devin`, `gemini` have no headroom wrap support either) — copilot is the ONLY currently-viable alternative, not one of several.
**Given** a station whose `harness_preference` resolves to `cursor` (all eight, today) **When** a dispatch session launches **Then** `wire.reason` names the structural cause explicitly for cursor ("cursor-agent has no headless wire-compression path; headroom's cursor support is Cursor-IDE-only") rather than the current generic "declares no [wrapper]" message, which reads as an oversight
**And** `cursor.toml`'s own `[wrapper]`-absence is annotated with a comment citing this story, so a future harness-profile author does not attempt to add one
**And** the copilot alternative is recorded as an operator decision point, not silently pursued or silently dropped — a real go/no-go given the quota history and the wrap-composition rework cost, not this story's own call to make
**Status:** backlog

### Story 28.30: Output (caveman) compresses dispatch sessions too, not just spin

As a marshal operator,
I want the caveman skill genesis-seeded into every dispatch worktree and `bmad-build-auto`'s own skill files to reference it,
So that a dispatched story's own dev-session speech compresses the same way a spun story's already does — verdicts, journals, and escalation context still fully articulated.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-3 (dispatch half; spin half already shipped, Story 28.3)
**Note:** Confirmed live 2026-09-10: `.claude/skills/bmad-build-auto/*.md` has zero references to caveman today (unlike `derived-context`/`planning-graph`, which ARE wired into `step-01-clarify-and-route.md`) — this is a real gap, not a proven-but-off layer like 28.27's. `seed/verbs/kit.py::_apply_caveman_skill` already knows how to deploy `<home>/.claude/skills/caveman/SKILL.md` for a loop home; the dispatch worktree equivalent needs the same deployment at worktree-creation time in `cli/dispatch.py`, gated on `[context].output.enabled`.
**Given** a dispatch worktree for a project with `[context].output.enabled = true` **When** the worktree is created (`dispatch_once`'s existing worktree-seed step) **Then** `<worktree>/.claude/skills/caveman/SKILL.md` is deployed from the same packaged payload `seed/verbs/kit.py` uses, and `bmad-build-auto`'s own skill files reference it the way `step-01-clarify-and-route.md` already references `derived-context`/`planning-graph` (a new instruction block, same file)
**And** a project with the layer declared off deploys nothing — today's behavior, byte-identical
**And** an unavailable/unresolvable caveman payload disables the layer with a named finding (matching Story 28.3's own degrade contract) and dispatch proceeds unwrapped
**Status:** backlog

### Story 28.31: Structure-graph (codegraph) for dispatch — provisioning cost weighed against a single-story session

As a marshal operator,
I want a documented decision on whether a per-dispatch-worktree codegraph index is worth building, before any code assumes the answer is yes,
So that dispatch does not pay an index-build cost that exceeds what a single story's own navigation would have spent without it.

**Type:** spike • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-3 (structure-graph half; spin half already shipped, Story 28.3)
**Note:** Unlike `output` (a skill-file deploy, cheap and clearly net-positive), `structure-graph` needs a real index (`codegraph init -y`), and Story 28.3's own docstring already flags "a first codegraph index build runs unattended and can take minutes" — for a LOOP HOME running many stories across its lifetime, that one-time cost amortizes; for a DISPATCH worktree living one story's lifetime, it may not.
**Scope narrowed 2026-09-10 (Story 28.33 split):** this spike is DISPATCH-ONLY now. The spin/loop-home half no longer waits on it — Story 28.33 wires the step-01 reference to the loop-home index directly, since that index already exists and needs no cost question answered (confirmed live: `marshal preflight pyforge-marshal` built a real 229MB `.codegraph/codegraph.db` for that loop home in ~21s, well under the 900s ceiling). This story's own remaining scope is strictly the DISPATCH-worktree provisioning-cost question — whether to build one per dispatch worktree at all, given a worktree's one-story lifetime.
**Given** a representative dispatch worktree and a representative story **When** the spike measures (a) `codegraph init -y`'s wall-clock/token cost for this repo's actual size and (b) the token cost the SAME story's own file-navigation would have spent without a graph **Then** the comparison is recorded as a real artifact (matching Story 28.5's own benchmark-artifact precedent), not an assumption
**And** the spike's own recommendation — build it per-worktree, share a repo-level index across worktrees (if codegraph supports incremental sync from a shared base, matching `kit.py`'s existing `init`-vs-`sync` split), or leave this layer spin-only — is the acceptance criterion, not a specific implementation
**And** if the recommendation is "build it," the follow-on implementation story is filed separately, scoped by the spike's own findings — this story does not pre-commit to writing that code
**Status:** done

### Story 28.32: Derived-context and output roll out fleet-wide

As a marshal operator,
I want `[context."derived-context"]` and `[context.output]` enabled for the other 7 stations, not just `pyforge-marshal`,
So that every station's dispatch sessions get the token savings both layers now genuinely deliver, mirroring 28.27's fleet-wide planning-graph rollout.

**Type:** feature • **Effort:** S • **Deps:** 28.28, 28.30 • **FR/AD:** token-economy CAP-3/CAP-5
**Note:** Both prerequisite stories are done and live-verified against `pyforge-marshal` (the canary, same pattern as 28.27's own precedent): 28.28 closed the `scribe index refresh --declare` gap (plus a `cocoindex` packaging fix), 28.30 closed the dispatch-worktree caveman deployment gap. No further engineering is needed to roll either out — this is the same "flip the policy, verify live per station" shape 28.27 already proved. A real, previously-undiscovered bug was found and fixed in the same pass before this rollout: `seed/detect/kit.py::_carve_out_state` string-sliced a Python `str` using BYTE offsets (`RegionSpan.body_span`'s documented contract), which desynced whenever non-ASCII content preceded the region — exactly what the real packaged caveman `SKILL.md` carries. This silently made `marshal seed kit`/`run_preflight` re-deploy the caveman skill on EVERY single preflight forever (never idempotent) and reported a false `MRS-PREFLIGHT-015` carve-out-mismatch WARN even on a byte-correct, freshly-deployed file. Fixed by using the already-correct, already-tested `detect/hashes.py::region_body_text` (proper byte-slice-then-decode) instead of the naive `str` slice — this bug would have reproduced identically on all 7 stations' loop homes the moment `output` was enabled for them, so fixing it first (rather than rolling out onto broken detection) was load-bearing for this story, not a side quest.
**Given** the 7 non-marshal stations' `marshal-policy.toml` **When** each gets `[context."derived-context"]` and `[context.output]` `enabled = true` overrides, mirroring marshal's own **Then** `marshal context refresh --project <slug> --epic <N> --format json` returns `mode: incremental` with zero findings for at least one real epic per station, and `marshal preflight <slug>` provisions the caveman skill cleanly (idempotent on a second run — `already-present`, not `applied`)
**And** `wire`/`structure-graph` stay exactly as they are for these stations — this story touches only the two proven-working layers
**Status:** backlog

### Story 28.33: The structure-graph reference is wired for spin, unblocking the already-built loop-home index

As a marshal operator,
I want `bmad-build-auto`'s `step-01-clarify-and-route.md` to reference the loop-home `.codegraph/codegraph.db` index the same way it already references `planning-graph`/`derived-context`/`output`,
So that a spin session's already-provisioned codegraph index (built since Story 28.3) stops sitting unused and starts saving the file-navigation tokens it exists to save.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** token-economy CAP-3 (structure-graph half, spin only)
**Note:** The mirror-image gap to 28.30's own finding: Story 28.3 already builds `.codegraph/codegraph.db` for any loop home with `[context."structure-graph"]` enabled (confirmed live 2026-09-10: `marshal preflight pyforge-marshal` produced a real 229MB index), but `step-01-clarify-and-route.md` has zero reference to codegraph at all — the same reference gap `output` had before 28.30, just never closed for this layer. Unlike 28.31 (the dispatch-side spike), this half needs no cost question answered: the index already exists, was already paid for, and the only missing piece is telling the agent to query it. Scoped to the `codegraph context <task...>`/`codegraph explore <query...>` CLI verbs (`codegraph --help`, live-checked) — the same "Load context" moment `step-01`'s existing item 1 already owns, so this is a new bullet inside that item, not a new top-level section (unlike 28.30's `output`, which is a session-wide behavior and correctly sits before the intent check).
**Given** a spin session in a loop home with `[context."structure-graph"].enabled = true` and a present `.codegraph/codegraph.db` **When** step-01's "Load context" item runs **Then** the agent is told to query the index (`codegraph context <task>` / `codegraph explore <query>`) instead of unbounded file reads for that same context-gathering step
**And** a loop home with the layer off, or with no index present (dispatch worktrees, until 28.31 ships), reads nothing new — the reference is conditioned on the index's own presence, not on which engine launched the session
**And** the existing epic-context/planning-graph/derived-context context sources are unchanged — this is an additional navigation aid, not a replacement for any of them
**Status:** backlog

## Epic 29: A harness halt of `done` ends the session, not the review

**Heading added 2026-09-14, retroactively.** Stories 29.1-29.2 and their ledger
keys have existed and read `done` since 2026-09-02, but this epic's own `## Epic 29`
heading was never written, so both stories rendered under Epic 28 and the board
counted an epic `epics.md` did not declare. This file's own frontmatter already
recorded the symptom without naming the cause — `storyCount`: *"183 (181 + Epic 29's
two, never counted)"*. Found by `chain-completeness`'s new INV-B epic arm
(doctor DW-CHAIN-COMPLETENESS-7); no story content changed.

**Goal:** FR-193 CAP-11 (`spec-marshal-single-story-dispatch`, Dream addendum
2026-09-02). A harness halt of `done` is the end of the *session*, not the
start of another review. Drain may only CAP-4 land or escalate. Motivating
incidents: steward 41.2 (PR #1017, 27 write-backs, DIRTY) and mason 13.2
(18 write-backs, no PR).

### Story 29.1: A done spec HALTs unless follow-up is true

As a marshal operator,
I want `bmad-build-auto` to refuse a fresh review when the spec is already
`done` and `followup_review_recommended` is false,
So that a re-dispatch cannot write 18–27 confirmatory spec commits.

**Type:** fix • **Effort:** S • **Deps:** none • **FR/AD:** FR-193 CAP-11 (harness half)
**Surface:** `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`,
`step-04-review.md` (in-repo skill copy only)
**Given** a spec with `status: done` and `followup_review_recommended: false`
**When** `bmad-build-auto` is invoked on that file **Then** it HALTs `done`
immediately — no step-04 review, no `review_loop_iteration` reset that
authorizes another pass, no spec commit
**And** `done` + `followup_review_recommended: true` allows at most one
follow-up review, then the flag is forced `false`
**And** a review pass that applies 0 patches does not commit
**And** the vendored `bmad_loop` package is not modified
**Status:** backlog

### Story 29.2: Harness `done` is CAP-4 only — never another session

As a marshal operator,
I want drain to land or escalate after the harness exits `done`,
So that a conflicted or unopened PR cannot restart `bmad-build-auto` just
because the ledger on `main` is still `backlog`.

**Type:** fix • **Effort:** M • **Deps:** S-29.1 • **FR/AD:** FR-193 CAP-11 (marshal half)
**Surface:** `core/dispatch_fleet.py`, `dispatch_supervisor/`
**Given** a dispatched session whose harness halted `done`
**When** the fleet supervisor ticks **Then** it does not launch another
`bmad-build-auto` for that story
**And** the only legal next step is CAP-4 land (open/merge PR, ledger promote)
**And** CAP-4 fail (conflicts, no PR, dirty) parks the story
`awaiting-operator` / CHAIN naming the PR or worktree
**And** a 41.2-shaped DIRTY PR or a 13.2-shaped branch with no PR produces
zero additional harness launches
**Status:** done

---

## Epic 30: Aligned to BMAD 6.12 — the second era round

**Goal:** decomposes `spec-bmad-611-era-alignment` CAP-8..11 — the 6.12 round minted
2026-09-05 from § *The 6.12.0 era shift* of `docs/dreams/bmad-611-era-alignment.md`
(`alignment-inventory.md` rows #9–#14 carry the evidence each story closes;
`horizon-watches.md` records the re-verdicted watches). BMAD-METHOD 6.12.0 (released
2026-09-04) swapped one seat in the shim roster, emptied `persistent_facts`, discontinued
`llms-full.txt`, and bmad-loop 0.11.1 outran the repo skill copy. **HARD boundaries carried
from the Spec:** the apply itself is steward Epic 14's (operator-gated) — every story here
must be correct both before and after it lands; never adopt what upstream is removing;
watch-don't-build the TOML cutover and the bmad-ticket tree (neither shipped in 6.12);
every apply passes `--shims` explicitly and `[dev] skill = "bmad-dev-auto"` stays (the shims' adapter discriminator);
D1 — the AGENTS.md `bmad:context` block is the project-context surface — is decided,
not re-opened.

### Story 30.1: The retired-ID guard follows the 6.12 shim roster
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-8
**Surface:** `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py`, `architecture-bmad-infra.md`, `development-guide.md`
**Given** the `v6.12.0` shim roster (14 bmm + 6 core) **Then** `bmad-checkpoint-preview`
(the new shim forwarding to `bmad-walkthrough`) joins the guarded tuple;
`bmad-generate-project-context` (the retired 6.11 shim) stays guarded with a dated note that
6.12 ships it as neither a new `skill_renames` entry nor a `removals` catalog entry — it is
NOT orphaned (it still ships a live `lifecycle: shim` skill directory; no directory deletion
applies, correcting an earlier "delete the orphaned directory" premise); the two living docs
rename or gloss their bare mention; and the
guard passes on the swept tree while failing on a planted `bmad-checkpoint-preview` (the shim).
The Spec's open question — derive the tuple from steward's
`data/bmad_core_releases/<ver>.yaml` (`skill_renames` + `removals`) — is answered here: derive
once the 6.12.0 catalog exists, otherwise keep the hand tuple with a dated comment.
**Status:** done
**Outcome (2026-09-06):** `bmad-checkpoint-preview` (the new 6.12 shim forwarding to
`bmad-walkthrough`) added to the guard tuple with the CK→WT rename;
`bmad-generate-project-context` (the retired 6.11 shim)'s "not orphaned" correction recorded;
CFE retro v8.86.3 landed the guard change. `test_no_retired_bmad_skill_ids`: 9 passed.

### Story 30.2: The project-context surface follows 6.12 (D1)
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-9
**Surface:** `_bmad-output/projects/*/project-context.md` (×8), `pyforge-doctor/.../sources/factory.py`, `scripts/bmad_drift_check.py`, `scripts/fleet_scan.py`, `SYNC-RUNBOOK.md`
**Given** `persistent_facts = []` at 6.12 and D1 **Then** every consumer of the eight
station `project-context.md` rulebooks is migrated first — doctor's factory classification
and its `pin-behind (context)` row, `fleet_scan`'s context group, `bmad_drift_check`'s rule,
SYNC-RUNBOOK rows 7–9 / 45–49 / 83–85 — then the rulebooks retire (anything still needed
moves into the AGENTS.md block through `bmad-project-context adopt` / `audit`, the
post-upgrade step), `bmad-drift-check` and `detectors-ci` are green with zero
`project-context.md` rows and no `pin-missing` HARD finding, and SYNC-RUNBOOK's living-doc
cadence names `architecture-bmad-infra.md` + the AGENTS.md block only.
**Status:** done
**Outcome (2026-09-06):** all 8 station `project-context.md` files migrated off and deleted;
`factory.py`/`fleet_scan.py`/`bmad_drift_check.py`/SYNC-RUNBOOK.md updated; `bmad-project-context
adopt` run for real on pyforge-marshal and pyforge-atlas. A follow-up review pass fixed a critical
gap: 4 sibling stations' identical `test_context_files_not_hand_edited` copies would have broken
on the same migration; all fixed and verified green.

### Story 30.3: Documentation pointers follow 6.12
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-10 (+ the CAP-7 cadence)
**Surface:** `CLAUDE.md` § BMAD Method Documentation, `.claude/docs/bmad-method-llms-full.txt` (header note only), `architecture-bmad-infra.md`, `development-guide.md`
**Given** `llms.txt` / `llms-full.txt` are discontinued upstream **Then** CLAUDE.md
re-points (local copy = the last snapshot, generated 2026-08-17, 6.11-era, frozen; live =
the task-organized docs site + the package CHANGELOG), no live doc cites the dead URL,
the retired `bmad-checkpoint-preview` reads `bmad-walkthrough` in living docs, and — after steward's
apply — `architecture-bmad-infra.md` is re-grounded with `source_pin` reading BMAD 6.12.0
(the CAP-7 once-per-core-minor cadence; it also clears the `pin-behind` warnings against
CFE v8.86.x already firing on marshal's living docs).
**Status:** done
**Outcome (2026-09-06):** CLAUDE.md re-pointed off the discontinued `llms-full.txt`;
`architecture-bmad-infra.md` re-grounded to `source_pin: BMAD 6.12.0 / CFE v8.86.4` after
steward's 6.12 apply landed later the same day.

### Story 30.4: bmad-loop's repo skills match the installed package — by test
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** spec-bmad-611-era-alignment CAP-11
**Surface:** `.claude/skills/bmad-loop-setup/assets/module.yaml`, one new meta-test under `.claude/skills/conda-forge-expert/tests/meta/`
**Given** bmad-loop 0.11.1 installed and `bmad_loop/data/skills/` as canon **Then**
`bmad-loop-setup` reads `module_version: 0.11.1` (the one-line drift; `-resolve` and
`-sweep` are already identical), a meta-test diffs the three repo skills against the
installed package and reds a planted one-line divergence, and `bmad-loop validate` stays
clean across all 8 loop homes.
**Status:** done
**Outcome (2026-09-06):** `module_version` and the three skill dirs were already correct
before this story ran (an unrelated prior commit had closed the gap); the new meta-test makes
that equivalence provable going forward, verified via planted-divergence fixtures. CFE retro
v8.86.4 landed the guard.

### Story 30.5: Every live caller follows the shim retirement
**Type:** feature • **Effort:** S • **Deps:** S-30.1 • **FR/AD:** spec-bmad-611-era-alignment CAP-12 • spec-bmad-suite-lifecycle CAP-10 • lifecycle spine AD-5, AD-7
**Corrected 2026-09-06** (found live, during this story's own implementation; operator-directed spec correction, same session): the original title and scope ("The harness and every live caller...") included renaming `harness_bmadloop.py`'s vendored `[dev] skill = "bmad-dev-auto"` literal to `"bmad-build-auto"`, updating its render test, re-rendering all 8 loop-home `policy.toml` files, and widening the retired-ID guard's `SCAN_GLOBS` to the harness template — this is FALSE, verified directly against the installed `bmad_loop` 0.11.1 package source: `DevPolicy.skill` is a PERMANENT internal adapter discriminator (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated) that must read `"bmad-dev-auto"` forever on every era; the skill actually invoked is resolved separately from disk at runtime. Renaming it throws `PolicyError` and breaks `bmad-loop validate` on all 8 real loop-homes. The harness/render-test/re-render/guard-widening scope is REMOVED, permanently, not deferred — title corrected to match the surviving scope. Matching correction lands on steward Story 14.9 (its own false refusal check, keyed on the same premise, is removed in the same session).
**Surface:** callers only: doctor `sources/chain.py` (dead-path fix), marshal `cli/spin.py` + `tests/unit/test_spin.py` (present-tense docstring rename), `planning-artifacts/marshal-policy.toml` (dead-path fix), `docs/dreams/README.md` (two present-tense line renames).
**Given** the operator's 2026-09-06 decision that shims retire now (era-alignment constraint superseded by memlog) **When** every live caller in Surface above is checked **Then** the two dead file-path citations (`chain.py`, `marshal-policy.toml` — citing skill directories that moved under the 6.12 rename) resolve to real files, and the present-tense docstring/prose hits (`cli/spin.py` + its test mirror, two spots in `docs/dreams/README.md`) lead with the live skill id `bmad-build-auto`
**And** decks (`presentations/**`), `docs/specs/**` and `pixi.toml` comments are glossed, never rewritten (shipped history); `pyforge-warden/__init__.py`, `core/promotion.py`, `core/status.py`, and `cli/deploy.py` (named in the original Surface line) turned out to have zero `bmad-dev-auto` hits or cite a different retired skill (`bmad-quick-dev` → `bmad-build`, a separate rename, out of this story's scope) — verified by direct inspection, nothing to change there
**And** `pyforge-marshal-test` and `pyforge-doctor-test` stay green; `mason_cfe_surface_check` stays clean (no CFE-surface file touched by this story, since the guard-widening never happens)
**And** after the `--no-shims` apply lands (Session 2 step 9, steward 14.9), `bmad-project-context` records the pitfall "the 21 shims are gone — never author `_bmad/custom/<old-name>.toml`; old ids do not resolve" in the AGENTS.md block (recorded by the skill, not by hand) — unaffected by this correction, since the shims themselves (20 `v6-shims` + `bmad-generate-project-context`) are still genuinely retired by `--no-shims`; only the harness's permanent `[dev] skill` discriminator field is not one of them
**Status:** done
**Outcome (2026-09-06):** the two dead-path fixes and three present-tense docstring/prose
renames landed; the harness rename found false and permanently descoped (see Corrected note
above). Session 2 step 9's live `--no-shims` apply subsequently ran clean (steward 14.9,
same day): `bmad-loop validate` 8/8, no `.customization-conflict` files. The
`bmad-project-context` pitfall-recording clause remains a follow-up action, not yet run.


**Epic 30 clears to dispatch in full — 30.1–30.4 are independent of each other; 30.5 (added
2026-09-06, spec-bmad-suite-lifecycle CAP-10 / era-alignment CAP-12) lands after 30.1 and before
steward 14.9's `--no-shims` apply. 30.1's "orphan directory" premise was corrected 2026-09-06
(`bmad-generate-project-context` is a plan-tree `lifecycle: shim`, not orphaned); 30.3's
re-ground half lands after steward's 6.12 apply (Epic 14, done 2026-09-06), which this epic
never performs.**

## Epic 31: TEA replaces the generator, and marshal's own estate is cutover-ready

**Goal:** the marshal-side half of `spec-bmad-suite-lifecycle` — TEA's workflows produce every
station's test architecture and `tea-test-review` becomes a review lens (CAP-4; era-alignment
CAP-13, the retired "TEA is optional" non-goal), the seven in-place-edited installer-owned files
are governed (CAP-9 P13), loop-home readiness is defined for the cutover flip (CAP-9 G10), and
two adopted skills get their marshal routing (CAP-3). Dream `docs/dreams/bmad-suite-lifecycle.md`;
PRD `prd-bmad-suite-lifecycle-2026-09-06` FR-3/FR-4/FR-9; lifecycle spine AD-2, AD-4, AD-5.
**HARD boundaries:** the generator, its two meta-tests and its pixi tasks are deleted only in
the same story that records a passing equivalence check (AD-5) — a failing check narrows CAP-4 to
the review lens and keeps the generator; `tea-test-review` never joins `detectors` and never
changes Warden's verdict (AD-4); steward 46.3 provisions TEA first — this epic never provisions.

### Story 31.1: TEA's workflows produce every station's test architecture
**Type:** feature • **Effort:** L • **Deps:** — (after steward 46.3 — cross-station: ledger `blocked` + refuse when the AD-9 roster lacks `tea`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-4 • AD-5, AD-9, AD-10 • spec-bmad-611-era-alignment CAP-13
**Surface:** `_bmad-output/projects/*/planning-artifacts/test-architecture.md` (×8, regenerated), `.claude/skills/bmad-testarch-test-design` / `-framework` (invoked, never edited), a recorded equivalence report under `planning-artifacts/reviews/tea-equivalence-2026-xx-xx.md`
**Given** TEA provisioned and the generator's last outputs kept (`python _bmad/scripts/bmad_tea_playwright.py --all` run once more first) **When** `bmad-testarch-test-design` / `-framework` run per station **Then** eight documents regenerate, and the equivalence report shows every story id and every live test path the generator emitted present in the TEA output, with the `TBD`-free invariant held
**And** a failing equivalence for any station keeps that station's generator output, records the gap, and narrows CAP-4 for it — the story still completes with the report; 31.2 depends on a full pass

### Story 31.2: The generator, its meta-tests and its pixi tasks retire behind the equivalence check
**Type:** chore • **Effort:** S • **Deps:** S-31.1 • **FR/AD:** CAP-4 • AD-5
**Surface:** `_bmad/scripts/bmad_tea_playwright.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py`, `test_tea_architecture_generator.py`, `pixi.toml` tasks at `:854-859` (`--all`, `--all --check`), `environment.yaml`, the six blanket-glob specs governing `pixi.toml` (memlog + scoped stamps), marshal `architecture-bmad-infra.md` (FR-129/FR-132 gloss)
**Given** 31.1's equivalence report passes 8/8 **When** the generator and both pixi tasks are deleted in this story, and the drift meta-test's predicate (story-id coverage, test-inventory rows, the `TBD`-free invariant) is re-pointed at TEA's output and KEPT as the oracle (AD-5 — deleted only by a later memlog decision) **Then** `pyforge-marshal-test` is green, `detectors-ci` is green, `architecture-bmad-infra.md` glosses FR-129/FR-132 as "retired 2026-xx-xx behind TEA (Story 31.2)", and the CAP-5 story-id drift the `--check` task guarded is re-expressed as a TEA `bmad-testarch-trace` run or an explicit accepted loss recorded in the era-alignment memlog
**And** if 31.1 narrowed CAP-4 for any station, this story is refused for that station's artifacts and the generator stays (the refusal is recorded, not silent)

### Story 31.3: `tea-test-review` is a marshal review lens
**Type:** feature • **Effort:** S • **Deps:** — (after steward 46.3 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** CAP-4 • AD-4, AD-10 • Spec open question 2 (`--min-score`)
**Surface:** `_bmad/custom/bmad-review.toml` (the lens as a `bmad-review` customize override — never a harness-policy key, never an in-place skill edit, AD-4), `core/policy.py` + `policy.json` (`review.min_score` knob, exact TOML scalar type — the value 46.3's task takes as its argument), `tests/unit/test_harness_policy_render.py`, the 8 loop homes (re-render), `planning-artifacts/marshal-policy.toml`
**Given** the pixi task from steward 46.3 **When** the review step's `bmad-review` override runs `tea-test-review --base origin/main --min-score {review.min_score}` as a lens beside `edge-case-hunter` (refused while the AD-9 roster lacks `tea`, AD-10) **Then** its findings are appended to the review output as `warn`-severity observations, the run's `done`/`review` routing is unchanged by the score, `bmad-loop validate` is 8/8 after re-render, and the knob defaults to 80 with the calibration plan (first ten PRs) recorded in the era-alignment memlog

### Story 31.4: Every in-place-edited installer-owned file is governed by a marshal spec surface
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-9 (P13) • customization-inventory C5 / §2 item 5
**Surface:** `spec-marshal-single-story-dispatch/SPEC.md` and `spec-marshal-token-economy/SPEC.md` `surface:` lists (via memlog + `bmad-spec` update), `scripts/.spec-surface-baseline.json` (scoped stamps), the **eleven** files: `.claude/skills/bmad-build-auto/{step-01-clarify-and-route,step-04-review,spec-template,compile-epic-context}.md`, `.claude/skills/bmad-sprint-planning/{references/generate-tracking.md,scripts/sprint_plan.py,scripts/tests/test_sprint_plan.py,sprint-status-template.yaml}`, `.claude/skills/bmad-retrospective/scripts/{sprint_status.py,tests/test_sprint_status.py}` *(scope amended 2026-09-09, fleet-readiness decision batch § 2.4 **D9** — the pool grew from seven to eleven and four are ungoverned; three of those four had never been named in any artifact: `bmad-retrospective/scripts/sprint_status.py`, its test, and `bmad-sprint-planning/sprint-status-template.yaml`. Story not re-minted.)*
**Given** only two of the original seven were governed at the 6.12 apply, and the pool is now **eleven** with **four ungoverned** — three of which (`bmad-retrospective/scripts/sprint_status.py`, `bmad-retrospective/scripts/tests/test_sprint_status.py`, `bmad-sprint-planning/sprint-status-template.yaml`) have never been named in any artifact, and the last of those carries the Epic-44 `blocked` restore, so an ungoverned in-place edit to it silently changes a gating artifact **When** the owning marshal specs claim all **eleven** in `surface:` (the sprint-plan N.M fix and the sprint-status pair under the spec that owns the ledger contract) **Then** `spec-surface-check` reports zero `uncovered` for them, a planted edit to any of the eleven without a memlog line reds `drift`, and steward's pre-flight (47.1) lists them as governed local customizations
**And** the same governed `sprint_plan.py` gains the one-argument fix for the wrap found 2026-09-06 — `yaml.dump(doc, buf, width=<wide>)` so a `key: value` pair past 80 columns is never split onto an indented second line that `promote_sprint_status.py`'s line-based parser reads as absent — with a regression test writing a 100-char key and re-reading it through the promoter; the upstream-PR candidate is recorded, not opened

### Story 31.5: Loop-home readiness is defined for the cutover flip
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-9 (G10, P16) • `fnd:AD-12`, `AD-17`
**Surface:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/` (or the governing loop-home spec — memlog note), `architecture-bmad-infra.md` § loop homes, `cutover-readiness.md` G10/P16 (via steward memlog relay), `marshal homes` output contract
**Given** the eight `~/.bmad-loops/pyforge-*` homes are full worktrees with their own `pixi.toml`, `pyforge.toml` (`name = "local-recipes"`), `_bmad/` and `_bmad-output/` **When** this story writes the readiness definition **Then** it names what a re-provisioned home must contain after the flip (remote, `pyforge.toml` name, rendered policy naming `bmad-build-auto`, relays refreshed, no in-flight run), the check that proves it (`marshal homes --json` fields or `bmad-loop validate`), and who runs it (attended, steward 44.12's flip); `DW-CC-2026-09-04-1`'s "residue to retire" wording is reconciled with it

### Story 31.6: `bmad-os-gh-triage` and `multi-repo-git-ops` are marshal-wielded
**Type:** docs • **Effort:** XS • **Deps:** — (after steward 46.2 and 46.5 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-3 • AD-2
**Surface:** `.claude/skills/bmad-agent-marshal/SKILL.md` (routing lines), the register § 2 row (AGENTS.md carries one pointer line to the register, placed once by `bmad-project-context` — never per-skill lines, AD-2/AD-11), `adoption-register.md` § 2 rows
**Given** the two skills installed by steward **When** the marshal persona gains "reach for `bmad-os-gh-triage` for PR/issue triage and `multi-repo-git-ops` for cross-repo landings (never for a `marshal land` the harness owns)" **Then** each skill has exactly one wielding station in the register, the register rows name both and the AD-2 meta-test passes, CLAUDE.md is untouched, and `DW-HYGIENE-2026-09-05-1`'s `marshal sweep` wish notes whether `multi-repo-git-ops` covers it
**Status:** done
**Outcome (2026-09-13):** found already satisfied — the routing line is live in `bmad-agent-marshal/SKILL.md` § "Utility skill routing (AD-2)", `adoption-register.md` § 2 rows 38/45 name marshal as sole wielder for both skills, and `DW-HYGIENE-2026-09-05-1` already carries the 2026-09-07 note answering the coverage question. `pyforge-steward-test -k adoption_register` (8 tests) green. Ledger was simply never flipped after the work landed.


## Epic 32: The operating model matches its own instruments

**Goal:** `spec-fleet-consistency-standard` CAP-1..CAP-6 — the standard that defines the
Dream-to-Code model is BMAD 6.12-accurate and derives what it can (CAP-1), the fleet speaks one
test-suite vocabulary (CAP-2), no artifact survives that the toolchain no longer produces
(CAP-3), dated artifacts are machine-classifiable (CAP-4), every package's declared Python floor
is the floor its environment installs (CAP-5), and a detector fails when a governance document
references something that no longer exists (CAP-6). Dream `docs/dreams/pyforge-marshal.md`
§ *The frontier — Fleet consistency standard*. Companion `_bmad-output/EXEMPLAR-STANDARD.md`.
**HARD boundaries:** `EXEMPLAR-STANDARD.md` keeps its path — `pixi.toml`'s `dream-chain`
detector names it as its `Contract:` and 33 files reference it, so it is rewritten in place,
never deleted. `AGENTS.md` is written only through `bmad-project-context`; its managed block is
replaced on refresh, so a hand-edit inside it is destroyed. The spec-surface baseline re-stamp
runs after every file move and after `git add`, never before. No station's own suite may be red
at any story boundary. Coverage floors are seeded from measurement, never asserted — and the
coverage gate itself is `spec-pyforge-testing-charter` CAP-4's capability, amended here, not
re-minted.

### Story 32.1: The operating-model standard is 6.12-accurate and derives what it can
**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** spec-fleet-consistency-standard CAP-1
**Surface:** `_bmad-output/EXEMPLAR-STANDARD.md`
**Given** the standard named four skills removed or renamed in 6.11–6.12 (`bmad-document-project`, `bmad-create-story`, `bmad-check-implementation-readiness`, `bmad-dev-auto`) plus three research skills 6.12 consolidated into `bmad-deep-recon`, and carried dated conformance snapshots its own text warned go stale **When** the 16-stage skill-mapping table and the conformance-status sections are removed rather than refreshed, and the file is declared a companion of this Spec **Then** no skill, script or path named in it fails to resolve, INV-0..INV-5 / the conformance table / the kernel-companion rule / the provenance rules survive intact, and the self-invalidating "pyforge-atlas is right and this document is stale" clause is replaced by a reconciliation order
**And** the conformance table gains rows 12–14 (suite standard, hyphenated-ISO naming, tested Python floor) so each new normative claim has its enumeration in the same place as the old ones

### Story 32.2: Declared Python floor equals the tested floor
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** spec-fleet-consistency-standard CAP-5
**Surface:** `src/shared/packages/pyforge-{herald,marshal,mason,scribe,steward,warden,core,testing-kit}/pyproject.toml`, `pixi.toml` (`[feature.pyforge-atlas.tasks.pyforge-atlas-test]`)
**Given** `pixi.toml` pins `python = ">=3.14.7,3.14.*"` and every env-scoped pin is `3.14.*`, while eight of ten packages declare `requires-python = ">=3.12"` — a floor no environment in this repo installs and nothing has ever exercised **When** all ten are raised to `>=3.14` **Then** no package claims support for an interpreter this repo cannot produce, and the claim matches what CI actually runs
**And** `pyforge-atlas-test` exists as the canonical task name (CLAUDE.md documents `pixi run -e pyforge-<station> pyforge-<station>-test` as the fleet grammar and atlas was the sole station where that command did not exist), with `kedro-test` retained as a delegating alias so no existing caller breaks

### Story 32.3: Dated planning artifacts are machine-classifiable
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-fleet-consistency-standard CAP-4
**Surface:** `_bmad-output/projects/pyforge-{doctor,herald,mason,scribe,steward}/planning-artifacts/implementation-readiness-report-*.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/` (loose `PRD.md`, `retros/` vs `reviews/`)
**Given** `implementation-readiness-report-` exists in three date formats across 27 files and `bmad_drift_check.py`'s classifier matches only `-YYYY-MM-DD.md` **When** every compact `-YYYYMMDD` name is renamed to the hyphenated ISO form **Then** pointing `bmad-drift` at any station — not only pyforge-marshal — reports zero `uncovered` files, so a real finding is never buried under a false one
**And** marshal's directory asymmetries are resolved or recorded as deliberate in `planning-artifacts/README.md` (conformance-table row 10), never left implicit

### Story 32.4: No artifact survives that the toolchain no longer produces
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-fleet-consistency-standard CAP-3
**Surface:** `_bmad-output/projects/pyforge-*/planning-artifacts/epics-with-stories.md` (×8), `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py`, `.../doctor/sources/deps.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py`, `_bmad/scripts/bmad_tea_playwright.py`, the station `README.md` files that reference it
**Given** `epics-with-stories.md` appears nowhere in BMAD 6.12, is frozen at 2026-08-08 in six of eight stations while `epics.md` moved to 2026-09-06, and has no consumer that requires it — two exclude it explicitly as a derived summary, one is an inert allowlist entry, one reads it only as a fallback **When** all eight are audited for normative content, anything found is rehomed to the standard first (steward's suite-shape mandate at its line 61 is known; the other seven are unaudited), and only then are the files and their four code references removed **Then** no station README points at one, `pyforge-doctor` and `pyforge-marshal` suites stay green, and nothing normative was lost with the file
**And** the audit is a gate, not a formality — steward's mandate was found by accident, which is the entire reason this story reads all eight before deleting any

### Story 32.5: One test-suite vocabulary across the fleet
**Type:** chore • **Effort:** L • **Deps:** S-32.1 • **FR/AD:** spec-fleet-consistency-standard CAP-2
**Surface:** `src/shared/packages/pyforge-{steward,warden,marshal,herald,atlas}/tests/**`, `scripts/run_station_coverage_gate.py` (`_suite_test_paths`)
**Given** eight suite names cover two concepts, and the coverage gate's suite map recognises neither spelling of `conformance` — leaving 51 real test files (steward 32, warden 19) measured by nothing, herald measured on 4 of 47 files and atlas on a fraction of 129 **When** each station converges on `unit/` + `integration/` + `meta/` — steward's CLI-contract conformance and marshal's `contract/` to `unit/`, warden's oracle conformance and marshal's `oracle/` to `integration/`, herald's 43 loose files to `unit/`, atlas's 15 loose files and 23 topic dirs to `unit/` with domain structure intact, and `marshal/support/` renamed `_support/` with its imports **Then** `_suite_test_paths` needs no per-station special case and every test file belongs to a measured suite
**And** each station is a separate commit gated on its own suite passing — a green suite, never a reading of the diff — with `conftest.py` and `fixtures/` staying at each tests root so shared fixtures remain visible to both suites

### Story 32.6: Governance documents cannot go stale silently
**Type:** feature • **Effort:** M • **Deps:** S-32.1 • **FR/AD:** spec-fleet-consistency-standard CAP-6
**Surface:** `scripts/governance_currency_check.py` (net-new), `pixi.toml` (`[feature.local-recipes.tasks.governance-currency]`). *(Corrected during implementation: the `SCRIPTS`-list meta-test governs the CFE skill's own `.claude/skills/conda-forge-expert/scripts/`, not repo-root `scripts/`, so a repo-root detector needs no entry there — `scripts/detectors.py` discovers it from the filesystem via its `DETECTOR = {"scope": "repo"}` declaration.)*
**Given** the removed 16-stage table named four non-existent skills for two BMAD versions with no gate noticing — the same class of defect INV-4 identified for detectors, applied to the prose that governs them **When** a detector resolves every `bmad-*` skill name, script path and file reference in `EXEMPLAR-STANDARD.md`, `AGENTS.md`, `CLAUDE.md` and `docs/reference/test-charter.md` **Then** it exits non-zero naming each reference that no longer resolves, is discovered by `scripts/detectors.py` from the filesystem, and run against the standard as it stood on 2026-09-07 reproduces all seven staleness findings this session found by hand
**And** deliberate historical citations (a name quoted precisely because it was removed) are exempted by an explicit `governance-currency:ignore-start/end` marker, never by a silent heuristic — an unmarked dead reference must fail

### Story 32.7: Coverage is measured on all eight stations before any floor is enforced
**Type:** feature • **Effort:** M • **Deps:** S-32.5 • **FR/AD:** spec-pyforge-testing-charter CAP-4 (amended, not re-minted) • spec-fleet-consistency-standard § Constraints
**Surface:** `pixi.toml` (`pytest-cov` into the seven station features that lack it, per-station `-test-coverage` tasks), `environment.yaml`, the coverage thresholds TOML, `.github/workflows/coverage-gates.yml`
**Given** `pytest-cov` is declared in 2 of 10 pixi features, so seven station environments cannot run a coverage gate at all — verified live against scribe, which exits 1 with `unrecognized arguments: --cov` — and nobody has ever measured the fleet's real coverage, which the testing charter's own assumptions state **When** `pytest-cov` is added to the seven, all eight are measured, and each station's measured value is written as its starting floor **Then** no station reds on the first PR, coverage cannot regress below where it actually is, and floors ratchet upward only
**And** the CI matrix expands from marshal-only to all eight; extending the `--cov` target over the django/portal tier stays an open question on the Spec, not a silent inclusion

### Story 32.8: Every caller and CI lane follows the convergence
**Type:** fix • **Effort:** S • **Deps:** S-32.5, S-32.7 • **FR/AD:** spec-fleet-consistency-standard CAP-2, CAP-5 • spec-pyforge-testing-charter CAP-4
**Surface:** `pixi.toml` (ten atlas test-path tasks), `.github/workflows/{pyforge-core,pyforge-steward-five-tier,pyforge-steward-fresh-clone}.yml` (python-version), `.github/workflows/coverage-gates.yml` (setup-uv), `src/shared/packages/pyforge-atlas/tests/{unit,integration}/**`, the eight regenerated `test-architecture.md`
**Given** PR #1082's first full CI run went red in five lanes — three because CAP-5's `requires-python` raise made pip refuse on lanes still pinned to Python 3.12 (`Package 'pyforge-core' requires a different Python: 3.12.14 not in '>=3.14'`), one because the coverage lane collects `tests/meta/` and herald's SKF validator shells out to `uv`, and one because moving atlas's tests under `unit/` pulled three fail-loud gates into a lane that provisions none of their prerequisites **When** the three lanes move to 3.14 (matching `detectors.yml`, which already ran it), the coverage lane gains `astral-sh/setup-uv`, and atlas's `dashboard/`, `publish/` and `wasm/` move to `tests/integration/` **Then** every lane is green and no gate silently skips: the three fail-loud gates still run — in `pyforge-atlas-test`, which provisions Chromium, the DuckDB `httpfs` extension and the WASM build for exactly this reason
**And** the ten pixi tasks naming pre-move atlas paths are repointed and the eight `test-architecture.md` regenerated from the live inventory — a green suite proved the FILES worked and said nothing about the TASKS that name them, which is why the manifest must be grepped after a tree move
**And** CAP-5's own rationale is corrected on the record: "no environment has ever exercised 3.12" was derived from `pixi.toml` alone and never checked against `.github/workflows/` — three lanes had been exercising it


## Epic 33: Token economy in effect

**Goal:** turn on what Epic 28 built, and everything of the same shape beside it. Epic 28 shipped
24/24 `done` and **every layer is off** — no `[context]` block exists in `policy-defaults.toml`, in
any of the eight project `marshal-policy.toml` files, or in any of the eight rendered loop-home
policies — so the loop today reads and says exactly what it did before the epic landed. Five more
marshal capabilities are the same pathology: risk-tiered review depth (zero callers outside
`tests/unit/test_gate.py`), adaptive model tiering (fed on 2 of 8 stations; the retry floor-raise
unreachable from the live engine), parallel dispatch fan-out (`max_parallel = 1` everywhere, no live
wave), the two Epic-20 watchdogs (observing `~/.bmad-loops`, dormant since 2026-08-22), and Unifying
`CAP-17` run-state-as-a-service (marshal imports `django_pyforge` zero times). Minted by
`sprint-change-proposal-2026-09-09-token-economy-enablement.md` from
`docs/dreams/marshal-token-economy.md` § *Addendum (2026-09-09)* and the operator-approved
fleet-readiness decision batch
(`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`,
rows **C5**, **C6**, **C10**, **D6**). Specs: `spec-marshal-token-economy` (CAP-1..CAP-18, CAP-18
new), `spec-risk-tiered-review-depth`, `spec-adaptive-model-tiering` CAP-2,
`spec-marshal-parallel-dispatch-fanout` CAP-6 (new), `spec-bmad-loop-baseline-drift`,
`spec-bmad-loop-intent-gap-work-preservation`, `spec-bmad-switch-scope-enforcement`.

**HARD boundaries:** **Story 33.1 dispatches first and alone** — the Dream's own measurement-first
gate, which Epic 28 bypassed; no layer is enabled on any engine before a benchmark artifact records
the off-leg, and `marshal benchmark compare`'s equivalence gate **voiding** a comparison is the
answer, never a failed test. No shipped epic is reopened and no shipped CAP is re-minted — every
story here exercises a criterion its Spec already states. **One publisher, not one per engine:**
33.4 is the single `django_pyforge.supervisor` writer for both run state and savings telemetry, and
it lands jointly with steward Story 49.8 (each is ledger `blocked` on the other until they dispatch
together). Citations on this epic are always qualified: the Track is **`hub:CAP-3`** (not
token-economy CAP-3, which is caveman seeding), savings telemetry is token-economy **CAP-7**, and
run-state-as-a-service is **Unifying CAP-17** — token-economy has its own unrelated CAP-17
(`scope_violation_mode`). Ledger keys are minted by `sprint_plan.py generate` only; **no
`sprint-ledger-sync` in any form** until steward 48.1 lands. Neither `scripts/bmad-switch` nor a
fork subagent is used to dispatch any story here.

### Story 33.1: Measurement first — the benchmark artifact, with real savings getters
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-7, CAP-9 • Dream § *Gates* (measurement first) • `DW-FU-3-6-6`
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (the five stub getters), `core/token_economy_benchmark.py`, `core/supervise.py`, `cli/check.py`, `src/shared/packages/pyforge-marshal/tests/unit/**`, a committed artifact under `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/token-economy-benchmark-2026-xx-xx.md`
**Given** `_get_headroom_savings`, `_get_codegraph_stats`, `_get_cocoindex_stats` and `_get_graphifyy_savings` (`harness_bmadloop.py:1880-1898`) plus the Layer-0 caveman getter immediately above them all `return None` with the comment "would integrate with actual … stats when available", so the supervisor journals a savings block whose every field is null and `marshal status` renders nothing **When** each of the five reads its real source — headroom's CCR store, the codegraph index, the cocoindex cache, scribe's `GraphStore` seam (`extras/graphify.py`, already writing), and the caveman output delta — and the pinned benchmark runs both legs on `1-1-marshal-conformance-smoke` **Then** a committed artifact names the story, the off-leg verdict, the on-leg verdict and per-layer rows with **non-null** numbers, and `marshal benchmark compare` either reports a measured saving or **voids** the comparison because the on-leg did not match the off-leg's verdict, gate results and reviewer engagement
**And** a getter whose source is genuinely absent returns a **named unavailable reason**, never `None` — `DW-FU-3-6-6`'s mid-session ceiling blindness is answered by a savings block that distinguishes "zero saved" from "not measured", and no later story in this epic may enable a layer whose getter is still a stub
**And** the idle-threshold question (Q-14) closes here as a read, not an experiment: one wave of per-session timing is read from the dispatch journals (`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/*/journal.jsonl`) and the 25-minute default (`core/policy.py:475`) is confirmed or re-set from that data (operator 2026-09-09)

### Story 33.2: The layers are enabled on `factory dispatch`
**Type:** feature • **Effort:** S • **Deps:** S-33.1 • **FR/AD:** spec-marshal-token-economy CAP-1, CAP-2, CAP-5, CAP-6
**Surface:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` (the `[context]` block), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py`, `adapters/harness_bmadbuild.py`, `cli/dispatch.py`, `seed/verbs/kit.py`, `tests/unit/**`
**Given** `resolve_context_layers` is the single composition site both adapters call, `resolve_wire_wrap` is imported in exactly one place (`adapters/harness_bmadbuild.py:50`, used at `:235`), and CAP-1's contract makes an absent `[context]` block mean every layer off — and no block exists anywhere **When** the block is declared in **`marshal-policy.toml`** (the per-project file both engines read, per `DW-FU-28-2-3`), `marshal seed kit` runs to deploy the caveman skill and the codegraph index, and a dispatched story launches under it **Then** all five layers act on the `factory dispatch` path — output, structure-graph, wire, derived-context and planning-graph — the journal's savings block carries 33.1's real numbers, and the story's verdict, gate results and reviewer engagement are unchanged from the off-leg
**And** the on-leg is recorded against 33.1's artifact rather than asserted, and any layer that degrades is reported with a named reason (`resolve_wire_wrap`'s existing degrade path), never silently skipped

### Story 33.3: The layers are enabled on `factory spin`, or spin is declared a two-layer engine
**Type:** decision+feature • **Effort:** M • **Deps:** S-33.2 • **FR/AD:** spec-marshal-token-economy CAP-1 • `DW-FU-28-2`, `DW-FU-28-2-3`
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py`, `core/harness_profile.py`, `adapters/harness_bmadloop.py`, the eight `~/.bmad-loops/*/.bmad-loop/profiles/*.toml` overlays marshal already writes, `docs/dreams/marshal-token-economy.md` § *Addendum* matrix
**Given** on `factory spin` marshal launches `bmad-loop run` and bmad-loop launches the coding CLI, so there is no argv to prefix (`DW-FU-28-2`), and `cli/dispatch.py:318` folds `read_repo_policy_defaults()` while `cli/spin.py` does not (`DW-FU-28-2-3`) — a repo-wide `[context]` block would act on one engine and vanish silently on the other **When** the fold is added to `cli/spin.py` and the loop-home launcher shim is attempted through the seam `DW-FU-28-2` already names (bmad-loop's `adapters/profile.py` exposes `binary` / `launch_args` / `env`, and `.bmad-loop/profiles/*.toml` is an overlay marshal writes) **Then** either the wire layer acts on spin and the Dream's five-layer matrix is corrected, **or** the attempt is recorded as unavailable with its reason and **spin is declared a two-layer engine on the record** — output and structure-graph only, with the drain routed to `factory dispatch` whenever cost is the objective
**And** the decision is the deliverable either way: a dated ruling lands in the Dream's Realization log and in the Spec's memlog, and `read_repo_policy_defaults()` is folded on both engines regardless of which branch is taken, so a repo-wide block can never again act on one engine and vanish on the other

### Story 33.4: CAP-18 — one publisher: run state and savings telemetry reach the supervisor
**Type:** feature • **Effort:** L • **Deps:** S-33.1 • (cross-station: joint landing with steward Story 49.8 — ledger `blocked` on each other until they dispatch together) • **FR/AD:** spec-marshal-token-economy **CAP-18** (new) + **CAP-7** • **Unifying CAP-17** (`spec-pyforge-unifying-strategy`, qualified — *not* token-economy CAP-17) • **`hub:CAP-3`** (the Track, `spec-intelligence-hub` — *not* token-economy CAP-3)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py` (the single publisher module, reaching `django_pyforge.supervisor` through the host's `/stations/marshal/mcp` face — never a direct import), `ports/publisher.py`, `core/publish.py`, `dispatch_supervisor/__main__.py`, `core/journal.py`, `cli/status.py`, `cli/init.py` (`:331`), `src/shared/packages/django-pyforge/**`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` (`:544`, by doctor's own memlog claim first)
**Given** marshal imports `django_pyforge` **zero** times, `cli/init.py:331` resolves `Path.home() / ".bmad-loops"`, doctor's `sources/marshal.py:544` does the same, and **two** supervisors now write run state (the loop supervisor and the sibling dispatch supervisor) — so a second publisher would be two writers of one fact **When** exactly one publisher module carries both run state and CAP-7's savings fields to `django_pyforge.supervisor`, fed by both supervisors **Then** `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` returns **nothing**, and a meta-test proves exactly one module imports `pyforge.core.client` for publishing; the front door shows live run state; per-story timing survives the workstation; marshal and doctor read the published plane instead of `~/.bmad-loops`; and steward Story 49.8's criterion is met by this same act, not by a second implementation
**And** doctor records the incoming surface claim in `spec-pyforge-doctor`'s memlog **before** any code lands here, or `spec-surface-check` reds the merge; and the three CAP citations stay qualified in every artifact this story touches, because token-economy's own CAP-3 and CAP-17 mean something else entirely

### Story 33.5: Risk-tiered review depth gets a producer and a caller
**Type:** feature • **Effort:** M • **Deps:** S-33.1 • **FR/AD:** spec-risk-tiered-review-depth CAP-1..4 (FR-185 — this story is what puts every capability of that Spec in effect: the producer, the callers, the cycle resolution and the lighter path's test; cited in full 2026-09-09 after the Spec's `shipped -> in-progress` reversal made CAP-2..4 read undecomposed) • `DW-FU-2-8-2`, `DW-FU-2-8-4` (`verified: 2026-09-05 — STANDS`) • batch row **C5**
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` (`:724` `classify_review_tier`, `:768` `resolve_review_cycles`), `cli/gate.py`, `ports/vcs.py`, `.claude/skills/bmad-spec/**` and `.claude/skills/bmad-build-auto/spec-template.md` (a `declared_low_risk`-shaped key — governed by Story 31.4's surface claim), `tests/unit/test_gate.py`
**Given** both functions have **zero callers anywhere outside `tests/unit/test_gate.py`**, there is no producer of `declared_low_risk` (no CLI flag, no `low_risk`-shaped key in either spec template), no `VcsPort` call computing `changed_files`, and nothing in `cli/gate.py` calls either function — so a one-line doc fix and a cross-module rewrite still get the identical review, which is the Spec's own title **When** the producer is chosen and shipped (a story-spec frontmatter key is the default, decided inside this story and recorded), `changed_files` is computed through the existing `VcsPort`, and `cli/gate.py` calls `classify_review_tier` → `resolve_review_cycles` on the real review path **Then** a declared-low-risk story provably runs fewer review cycles than a cross-module one on the same repo, the difference is visible in the gate evidence record, and **the review never runs zero cycles** — lighter, never absent
**And** `DW-FU-2-8-2` and `DW-FU-2-8-4` are closed by this story and by nothing earlier; the Dream `docs/dreams/risk-tiered-review-depth.md` returns to `realized` only when a real dispatched story exercises the lighter path, not when this story merges

### Story 33.6: Adaptive tiering is fed on all eight stations, and the floor-raise reaches dispatch
**Type:** feature • **Effort:** M • **Deps:** S-33.1 • **FR/AD:** spec-adaptive-model-tiering CAP-1, **CAP-2** • FR-51 • Story 3.11, Story 3.12 • batch row **C6**
**Surface:** `_bmad-output/projects/pyforge-{atlas,doctor,herald,mason,scribe,steward,warden}/planning-artifacts/marshal-policy.toml` (`model_tier_map`), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` (`:2268-2277 _apply_retry_escalation`), `core/dispatch.py` (`:220-232 resolve_dispatch_model`), `cli/dispatch.py` (`:1400`), `core/dispatch_retry.py`, `tests/unit/**`
**Given** CAP-1 **is** fed — 57 story specs across six stations declare a `difficulty:` and two live dispatch journals resolved `"model": "composer-2.5-fast"` — but six of eight stations carry no `model_tier_map` and journal `"model": null` (verified on mason 13.1 and steward 43.6), and **CAP-2's retry floor-raise fires only in `run_resume`** (`_apply_retry_escalation`), with no floor-raise call anywhere in `cli/dispatch.py` or `core/dispatch.py` — the live engine since ~2026-08-22 **When** the six stations gain real tier maps and the floor-raise is wired into the dispatch retry path **Then** a dispatched story on any of the eight resolves a non-null model from its declared difficulty, and a struggling retry on `factory dispatch` demonstrably runs under a stronger model than its first attempt — proven from a live dispatch journal, not a fixture
**And** the three story specs declaring `difficulty: ''` (`spec-11-1`, `spec-11-2`, `spec-11-3`, all `:10`) are corrected or the empty value is made a lint error — `core/dispatch.py:210-218 _DIFFICULTY_RE` requires `[A-Za-z0-9_-]+`, so an empty value reads as undeclared: a declaration that looks made and is not

### Story 33.7: The two Epic-20 watchdogs observe the plane the estate actually runs
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-loop-baseline-drift CAP-1..3 • spec-bmad-loop-intent-gap-work-preservation CAP-1..2 • batch row **C6**
**Surface:** `scripts/bmad_loop_baseline_drift_check.py` (`:72`, `:142`), `scripts/missing_preserve_check.py` (`:61`), `pixi.toml` (`baseline-drift-check` at `:932`, `missing-preserve-check` at `:940-942`), `scripts/detectors.py`
**Given** both detectors scan `~/.bmad-loops/<slug>/.bmad-loop/runs/` only, the newest run in **any** of the eight loop homes is 2026-08-22 (six stopped on or before 2026-08-20; warden on 2026-07-24), and the live engine writes to `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/` — so both exit **0 "OK"** over an empty observation plane, a false green by `pixi.toml:1033`'s own rule that *a detector that cannot run reports unknown, NEVER green* **When** each detector reads both planes and classifies its own observability **Then** a run on either plane is examined, and a detector with **nothing to observe exits 2** (`could-not-observe`, scope=runtime) with the reason named — never 0
**And** the exit-2 branch is proven by a test that points the detector at an empty tree, because the failure this story fixes is precisely a green that nobody questioned

### Story 33.8: The first live fan-out wave, on a real `dispatch.max_parallel` key
**Type:** feature • **Effort:** M • **Deps:** S-33.2 • **FR/AD:** spec-marshal-parallel-dispatch-fanout **CAP-6** (new) + CAP-1..5 (Story 28.16) • `DW-FU-28-2-2` • batch rows **C6**, **C10**
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (the new `dispatch.max_parallel` key; `:513`, `:1537-1551`), `cli/dispatch.py` (`:1010-1027` `resolve_max_parallel` — named "_resolve_parallel_cap" at draft time, shipped under this name), `core/dispatch_fleet.py` (`:750-790`), `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`, the marshal story specs that must declare a `surface:`, `tests/unit/test_wave_scheduler.py`
**Given** the wave scheduler, the narrowed conflict guard and the wave journal are all `done` and `max_parallel = 1` on all eight rendered loop homes, so **no live wave has ever run**; the cap falls back to bmad-loop's `scm.max_parallel`, so raising it also fires `_max_parallel_clamp_finding` whose text names *bmad_loop 0.9.0* — wrong context on the dispatch path; and CAP-16 auto-derives `policy_surface` to the whole station package tree when no `[epic_surfaces]` entry exists, so two same-station stories overlap **by construction** and `core/dispatch_fleet.py:786` refuses **When** `dispatch.max_parallel` is minted as its own policy key, the clamp advisory is scoped to the spin engine, and two `pyforge-marshal` story specs declare disjoint `surface:` fields **Then** those two stories land in **one live wave**, the wave journal records it, and the Dream's own § *Live proof required* gate is met by a real run rather than a fixture
**And** `DW-FU-28-2-2` is closed in the same story — `headroom wrap` defaults to proxy port 8787 and attaches to a running proxy instead of starting a second, so two concurrent wrapped dispatches share the first launcher's CCR store; the station-in-flight guard made this rare per station and does nothing for exactly the fleet-parallel case this story creates

### Story 33.9: `verify_scope` guards `marshal factory dispatch`
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-switch-scope-enforcement CAP-1, CAP-2 • batch row **C10** (mars-A-B5)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py`, `cli/dispatch.py`, `tests/unit/**`, `CLAUDE.md` § *PARALLEL AGENTS* (pointer only, via `bmad-project-context` if the managed block moves)
**Given** Story 20.7 shipped the shared stdlib-only primitive to exactly two hard-failing call sites (`scripts/bmad-switch:207-210,232-233` and `cli/init.py:247`) and said so, while the remaining exposure is the **parallel-agent** case `CLAUDE.md` documents as a HARD rule and auto-memory records as a live 2026-07-25 incident — and every parallel BMAD write today enters through `marshal factory dispatch`, which already stamps `BMAD_ACTIVE_PROJECT` per invocation **When** `verify_scope` is called at the dispatch boundary against the resolved project **Then** a dispatch whose resolved project disagrees with the marker, the symlinks or the passed `BMAD_ACTIVE_PROJECT` **refuses loudly** with all three values named, and a dispatch in agreement is unaffected
**And** the skill-injection question stays deferred to the foundry cutover's 44.5 layout — this story invents no injection mechanism, because the two gitignored compatibility symlinks it would be designed against may not survive the cutover at all

### Story 33.10: The CFE pin is derived, never stamped
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** batch row **D6** • SYNC-RUNBOOK row 84 • `spec-fleet-consistency-standard` CAP-6 precedent
**Surface:** `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` (row 84), `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` (the `pin-behind` verdict), `scripts/bmad_drift_check.py` (the mutation-only residual), the seventeen pin-carrying marshal artifacts (fourteen at `conda-forge-expert v8.86.1`, one at `v8.86.4`, two at `v8.79.0`)
**Given** `bmad-drift` reports seventeen live `pin-behind` warns on marshal artifacts because each stamps a CFE version **literal** in its `source_pin:` frontmatter while `.claude/skills/conda-forge-expert/SKILL.md:10` reads `version: 8.90.1` — and CFE shipped five releases on 2026-09-09 alone, so the literal is stale within hours of every hand pass **When** the pin is **derived** (read from `SKILL.md:10`) for the artifacts whose `source_pin` exists to say *"re-ground me when the skill moves"*, and the stamped literal is retained **only** where it records a dated re-grounding event rather than a currency claim **Then** `bmad-drift` reports zero `pin-behind` on marshal artifacts without anyone typing a version number, and a genuine staleness — a living doc whose *content* predates a real CFE behaviour change — is still reported, because the finding is not suppressed, it is re-based
**And** SYNC-RUNBOOK row 84 is rewritten to describe the derived pin, and the distinction is stated once and normatively: `source_pin` answers "which skill version was this doc last re-grounded against", which is a **fact about a past act** and stays a literal; the *currency verdict* is a comparison against live `SKILL.md`, which must never be a literal — auto-memory `feedback_derive_dont_declare.md`

### Story 33.11: Attribution becomes unforgeable before the Track serves a second principal
**Type:** feature • **Effort:** L • **Deps:** S-33.4 • **FR/AD:** spec-pyforge-marshal F-4 (answered 2026-09-09: B is the contract, A the v1 state) • `hub:CAP-3` (the Track's human-approvals field) • batch § 8 item 1
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py` (`:159` the only site naming operator attribution), `cli/gate.py`, `cli/journal*.py` (the operator-attributed write surface), `tests/unit/test_journal*.py`
**Given** the governed agent is trusted in v1 and operator attribution is advisory — enforced at the call surface only, with no authentication primitive anywhere in the package, the worktree not a sandbox, and process isolation deferred — so a run record is a log, not evidence, the moment a second principal reads it
**When** the trigger fires (the Foundry cutover flag, a shared Hub, or an external adopter — whichever comes first) and this story is dispatched behind 33.4's single publisher
**Then** operator-attributed journal entries carry a signature the call surface verifies (a keyed primitive whose key never lives in the worktree), an unsigned or mis-signed operator entry is refused with a printed reason, the Track published by 33.4 carries the verified attribution in its human-approvals field, and process isolation is still deferred but named as the remaining gap
**And** this story is minted `blocked` on its trigger by design: it never outranks 33.5/33.2/33.3 on the throughput queue (operator 2026-09-09 — governance scores zero on speed-to-market until a second principal exists)

### Story 33.12: CAP-1/2/4/5 in effect — held runs, publisher identity, and the loop-home reads retire
**Type:** feature • **Effort:** L • **Deps:** S-33.4 • **FR/AD:** spec-run-state-one-publisher CAP-1, CAP-2, CAP-4, CAP-5 • cross-station: unblocks steward Story 49.8, which stays `blocked` on this story's completion, not the other way around
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py` (held-run/heartbeat/terminal-row semantics, identity mint/re-mint), `core/publish.py`, `cli/init.py:331`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544` (re-point, doctor's own memlog claim first), `src/shared/packages/django-pyforge/**` (assertion mint for `marshal`, the `marshal` realm role, `pyforge login`'s bearer-file writer — incoming surface claim recorded in steward's memlog before this lands), `cli/status.py` (render held runs alongside MCP runs)
**Given** Story 33.4 landed the mechanical publisher (zero `django_pyforge` imports, best-effort publish/heartbeat/complete) but deliberately deferred the held-run lifecycle, the real identity path, and every consumer still reading `~/.bmad-loops` (`cli/init.py:331`, doctor's `sources/marshal.py:544`), so CAP-17's own criterion ("marshal and doctor no longer read `~/.bmad-loops`") is not yet met
**When** the publisher's held rows are accepted, heartbeated, and correctly classified lost vs. terminal (never rewriting a terminal row, always opening a new attempt row instead), a fan-out wave under one operator subject is never refused by the per-subject default, `pyforge login` mints a referenced bearer with no pasted secret, the `marshal` realm role exists, and `cli/init.py` + doctor's `sources/marshal.py` read the published plane instead of the filesystem
**Then** a bmad-loop run appears at `/runs/` sourced from the published plane with no operator-home access, a completed run's timing survives the workstation, `revoke --sub <subject>` cancels a run and its next heartbeat gets a terminal answer, and CAP-17's criterion is fully met — steward Story 49.8 can then close on this act
**And** the CAP-4 kind-aware guard (a new non-test-code check matching the `.bmad-loops` literal and the run-state file names) reds any future run-state read outside the publisher and explicitly tagged loop-home-file sites; CAP-3's deployed, egress-blocked proof exercise is still NOT this story's job — it stays attended, documentary, and separate

### Story 33.13: CAP-3's mechanism tier — the automated proof `platform-ci-local` gates on
**Type:** feature • **Effort:** M • **Deps:** S-33.4, S-33.12 • **FR/AD:** spec-run-state-one-publisher CAP-3 (mechanism tier only) • cross-station: touches `src/platform/**`, steward's surface — incoming claim recorded on `spec-pyforge-unifying-strategy`'s memlog before this lands
**Surface:** `src/platform/tests/test_front_door_queries_supervisor.py` (new publish→exit→timing-survives case), `src/platform/tests/test_chart_invariants.py` (new no-`hostPath` invariant across every chart template), a new socket-guard test on the `/runs/` render path (pattern: `test_openfeature_file_flags.py:242-254`), `src/platform/deploy/overlays/ocp/core-overrides.yaml` (the DNS-egress selector fix for real OpenShift DNS)
**Given** CAP-3's success criterion names two proof tiers — an automated mechanism tier gated in `platform-ci-local --test`, and one attended CRC exercise recorded as a dated verification file — and neither exists yet; the mechanism tier is the fully-automatable half this story owns, and the OCP overlay's `networkPolicy.dns` selector still hardcodes `kube-system`/`kube-dns` (vanilla K8s), which would silently break DNS resolution the moment `networkPolicy.enabled` NetworkPolicies are actually applied on a real OpenShift cluster, whose CoreDNS runs in `openshift-dns` with pods labelled `dns.operator.openshift.io/daemonset-dns=default` (confirmed live against a running CRC 4.22.7 cluster, 2026-09-12 — do not re-guess this value)
**When** a `RunState` row is published and completed, the process that published it exits, and `/runs/` is re-queried on a fresh database connection, then `completed_at`/`duration_ms` are intact; when the `/runs/` render path executes, no outbound socket call occurs (`socket.create_connection` never invoked); when every chart template under `src/platform/deploy/charts/platform/templates/` is rendered, no template declares a `hostPath` volume; and when `overlays/ocp/core-overrides.yaml`'s `networkPolicy.dns` values are applied on a real OpenShift cluster, CoreDNS remains reachable through the egress policy
**Then** `pixi run -e local-recipes platform-ci-local -- --test` gates all three mechanism-tier proofs alongside the existing suite, and CAP-3's own `verified:` line can name this tier as exercised (`spec-run-state-one-publisher/.memlog.md`, not this story's own diff, records that update)
**And** the attended CRC exercise itself — deploying with the corrected NetworkPolicy set active, driving a real bmad-loop run through the credential flow, verifying egress-blocked + zero-`hostPath` + timing-survives-teardown on a live cluster, and writing `spec-run-state-one-publisher/verification-<date>.md` in Story 12.7's shape — is explicitly NOT this story's job; it is attended, documentary, and done separately once this story and Story 33.14 both land

### Story 33.14: CAP-5's deployed profile — a real device-code/PKCE `pyforge login`
**Type:** feature • **Effort:** L • **Deps:** S-33.12 • **FR/AD:** spec-run-state-one-publisher CAP-5 (deployed-profile half; local-profile already landed in Story 33.12) • cross-station: touches `src/platform/compose/keycloak/realms/platform-realm.json` and `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml`, steward's surface — incoming claim recorded on `spec-pyforge-unifying-strategy`'s memlog before this lands
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/pkce.py` (new, pure), `adapters/oidc_pkce.py` (new, the loopback listener + token exchange), `cli/login.py` (new `--pkce`/`--issuer`/`--client-id` mode beside the existing local-profile positional-persona mode), `src/platform/compose/keycloak/realms/platform-realm.json` (a new public `pyforge-cli` client — PKCE required, `redirectUris: ["http://127.0.0.1:*"]`, the same audience+groups mappers `platform-web` already carries — plus a seeded `marshal-operator` user in `/pyforge:station:marshal`), `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml` (the `pyforge:station:marshal` group added to the bundled/deployed realm's `groups` list — no seeded user here; production realms don't ship test credentials)
**Given** Story 33.12 landed only the local-profile `pyforge login <persona>` (wrapping `config.local_dev.mint`, no real IdP round-trip); CAP-5's own success criterion requires a mint for station `marshal` to also succeed against a real, network-reachable IdP in "the deployed profile," and no device-code or PKCE flow exists in this codebase today
**When** an operator runs `pyforge marshal login --pkce --issuer <base-url> [--client-id pyforge-cli]`, a loopback HTTP server on `127.0.0.1` receives the authorization redirect, and the CLI exchanges the authorization code plus PKCE verifier for a bearer without ever holding a client secret
**Then** the bearer is written to `PYFORGE_IDP_BEARER_FILE` at 0600 with nothing else printed but the file path, no token value appears in stdout/stderr/any journal line, and a mint for station `marshal` using that bearer returns 200 against the repo's own docker-composed Keycloak stack (`src/platform/compose/keycloak/`, per operator direction 2026-09-12 — verification target is the local compose stack, not a customer-owned IdP)
**And** `pyforge:station:marshal` exists as a real realm group in both the compose realm export and the chart's bundled realm template (the deployed-profile half of CAP-5's own success wording), so the CRC exercise (Story 33.13's own deferred half, run separately) can mint against it without further chart changes; if the full live end-to-end PKCE round-trip cannot complete in one dispatch, land the PKCE mechanics with mocked-transport unit coverage and document the deferred live-Keycloak integration test explicitly in this story's Review Triage Log and `spec-run-state-one-publisher/.memlog.md`, per that Spec's "Realized on effect, never on ledger" constraint

### Story 33.15: The tier map names Cursor models before any unattended drain
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-cursor-native-tier-map CAP-1, CAP-2 • spec-dispatch-tier-routing-fails-safe CAP-1 (unchanged)
**Surface:** the eight `planning-artifacts/marshal-policy.toml` files; `spec-cursor-native-tier-map/`
**difficulty:** medium
**Given** harness_preference is `["cursor"]` and the maps still say bare `sonnet`/`opus` after the 2026-09-12 fail-safe revert
**When** this story lands
**Then** every easy/medium/heavy stage is an inline table `{ harness = "cursor", model = "…" }` with model in `{composer-2.5, composer-2.5-fast, grok-4.6}`; stations that already carry a Cursor cost catalog also declare `grok-4.6` from the 2026-08-30 snapshot
**And** no bare Cursor model string remains in those maps
**And** existing provider-mismatch tests stay green
**And** this story is implemented from Cursor (this IDE), not via `marshal factory drain`

## Epic 34: Launch-environment integrity — no silent-success failure and no orphaned worktree

**Goal:** every finding from `docs/dreams/marshal-launch-environment-integrity.md`'s 2026-09-10
recovery session that is NOT already closed by that Dream's four environment-integrity fixes
(`fix/marshal-harness-preference-4-stations`, `fix/marshal-tmux-dependency`,
`feat/marshal-sprint-status-sync-and-drift-detection`, and the in-progress
`spec-sprint-status-promotion-regression-guard` fix) or by
[`marshal-parallel-dispatch-fanout.md`](../../../../docs/dreams/marshal-parallel-dispatch-fanout.md)'s
own 2026-09-10 addendum (`factory spin`'s missing station-in-flight guard). Three real gaps
surfaced live, each hit multiple times in the same session, each costing real operator time to
recover from by hand: `factory spin` can be launched twice against the same loop home with zero
refusal; a crashed dispatch/spin session loses uncommitted worktree progress unless the operator
notices and manually checkpoints it before the worktree is reprovisioned; and a crashed session's
terminal verdict (`failed`, `stopped_externally`) is indistinguishable from a genuine code failure
to `factory drain`, which treats both as permanently blocked with no sanctioned retry path.

**HARD boundaries:** Story 34.1 reuses `cli/dispatch.py:935`'s `station_in_flight_conflict` check
— it is a narrowed CALL, never a re-derived guard (mirrors Epic 22/28's own "narrowed conflict, not
a new one" precedent). Story 34.2's checkpoint commit is local-only (never pushed, never opens a
PR) — it exists purely so a crash cannot destroy uncommitted work; landing a story is still a
human/operator-triggered act. Story 34.3 does not weaken `factory drain`'s existing
"never-auto-retried, never-forced-past" guarantee for a GENUINE story failure — it only adds a way
to tell "the session died before doing anything" apart from "the session ran and failed."

### Story 34.1: `factory spin` refuses a second launch against a live loop home
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** `docs/dreams/marshal-parallel-dispatch-fanout.md` 2026-09-10 addendum
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (spin's `subprocess.Popen` launch site), `cli/dispatch.py` (`station_in_flight_conflict`, reused not re-derived), `cli/spin.py`, `tests/unit/test_*spin*.py`
**Given** two `marshal factory spin pyforge-mason` calls six seconds apart both launched cleanly on 2026-09-10 — no refusal, no warning — producing two live `bmad-loop run` processes and two live supervisors against the SAME loop-home checkout simultaneously, a real risk (not just wasted compute) since spin operates directly on the loop home's single working tree rather than a per-story worktree
**When** `factory spin <slug>` is invoked while a prior spin run for that same `<slug>` is still live (session or supervisor process alive, run not yet terminal)
**Then** the second call refuses before launching anything, naming the live run's id/pid, using the SAME `station_in_flight_conflict` check `factory dispatch` already applies — not a second, independently-drifting implementation
**And** a fixture reproduces the exact 2026-09-10 race (two spin calls in rapid succession) and asserts the second refuses

### Story 34.2: A dispatch/spin session's worktree is checkpointed before it can be lost to a crash
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `docs/dreams/marshal-launch-environment-integrity.md` § *No mid-session checkpointing*
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` (or the dispatch/spin supervisor's own polling loop), `adapters/vcs_git.py`, `tests/unit/test_supervise*.py`
**Given** four separate crash recoveries in one session (doctor 21.1 ×2, herald 19.1, steward 48.6 ×2) each required the OPERATOR to notice uncommitted worktree changes and manually `git add -A && git commit` a recovery checkpoint before the story could be safely relaunched — real, substantial progress (a completed story once, hundreds of lines of a WebSocket-streaming feature another time) sat one worktree cleanup away from silent loss each time, and marshal's own supervisor was already polling these sessions for completion without ever checkpointing their in-flight state
**When** the supervisor's own poll loop detects the worktree has uncommitted changes and the session has been idle past a threshold, or on an explicit `factory checkpoint <slug>` call
**Then** it commits a local-only `wip: <story> (auto-checkpoint)` commit in the story's own worktree — never pushed, never opens a PR, purely a local safety net — so a subsequent crash can never lose more than the checkpoint interval's worth of work
**And** a fixture simulates a mid-session crash after the checkpoint fires and asserts the worktree's uncommitted changes survive as a commit, not as working-tree state a `git worktree remove --force` could destroy

### Story 34.3: `factory drain` tells a crashed session apart from a genuinely failed one
**Type:** feature • **Effort:** M • **Deps:** 34.2 • **FR/AD:** `docs/dreams/marshal-launch-environment-integrity.md` § *A crashed session and a genuinely failed one look identical to the ledger*
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` (blocked-story classification), `cli/dispatch.py` (`dispatch-resume`'s own `stopped_externally`/`completion_verdict` facts, already computed but not yet used to distinguish this), `tests/unit/test_dispatch_fleet*.py`
**Given** every terminal crash this session (`completion_verdict: stopped_externally` or `failed`, confirmed via `dispatch-resume`'s own "no live dispatch to recover" check) left the story permanently blocked in `factory drain`'s eyes — correct for a genuine code failure, wrong for an external crash — and the only recovery path was an operator manually bypassing the block with a single-story `factory dispatch` and knowing that trick exists
**When** `factory drain` encounters a blocked story whose last recorded verdict shows zero git progress AND zero review/verify-cycle evidence (i.e. the session died before doing anything a real failure would have left behind)
**Then** it classifies the block as **environment** rather than **story**, and `--mode skip_on_blocked`'s existing escape hatch (or a new explicit `--retry-environment-blocks` flag) is sanctioned to clear ONLY environment-classified blocks — a genuine story failure (real git progress, a failed verify run, an escalation) still requires the existing manual override, unchanged
**And** a fixture reproduces one of each (a crashed-before-any-progress run, a real verify failure) and asserts only the crashed one is eligible for the new retry path

### Story 34.4: The ATTENTION-block's own refused-verdict check gets the same test coverage its `station_state()` sibling has
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** `docs/dreams/marshal-launch-environment-integrity.md` § finding 5, `fix/fleet-picture-stale-dispatch-verdict`
**Surface:** `scripts/fleet_picture.py` (`main()`'s ATTENTION-block `needs.append` branch, the `station_state()`-adjacent but separately-inlined check), `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_dispatch_phase.py` or a new sibling test file
**Given** `fleet_picture.py`'s live 2026-09-10 fix (`fix/fleet-picture-stale-dispatch-verdict`) closed the stale-verdict mislabeling at BOTH call sites — `station_state()`'s STUCK cell and `main()`'s ATTENTION-block `needs.append` line — but only the first got direct unit coverage (`test_not_stuck_when_refused_verdict_is_stale_and_a_different_engine_is_running`); the second is an inline ~10-line branch inside `main()` with no dedicated test, verified only by hand against the live fleet at fix time
**When** a test exercises `main()`'s ATTENTION-block branch directly, mocking `subprocess.run` for the `marshal status --format json` call the way `test_fleet_picture_verification_staleness.py` already mocks a DIFFERENT ATTENTION probe's subprocess call in the same file — not by driving the real fleet's own ledger state
**Then** a fixture pins: (1) a station with a live run, a `dispatch_phase` set, and a `refused` verdict produces the `dispatch verify REFUSED` ATTENTION line; (2) the SAME refused verdict with `dispatch_phase=None` (a different engine live, e.g. spin) produces NO such line — the exact regression this story guards against recurring
**And** no behavior changes — this story is test-coverage-only, closing the one gap the 2026-09-10 fix's own landing PR named explicitly

## Epic 35: The templated merge-subject shape never masquerades as a same-numbered story from another project

**Goal:** close the sibling gap `docs/dreams/marshal-land-cross-project-story-key-collision.md`'s
own 2026-09-09 fix deliberately left open — `pyforge.core.landing_evidence.
parse_templated_merge_subject` (the AD-24 `"Merge {key} into main"` shape, tried first in
`classify_merge_subject`'s precedence chain) is the one parser among five with no `project_slug`
scoping, since the templated subject carries no station token in its own text. Confirmed live
2026-09-11: `merged_story_keys(subjects, 'Merge {key} into main', 'pyforge-doctor')` against real
`main` returned 129 keys, a majority attributable to other stations. Caused 3 false "already
merged" dispatch verdicts and 1 orphaned dev session during doctor's Epic 22 dispatch the same
day, all recovered by hand.

**HARD boundary:** the fix scopes ONLY the templated shape's corroboration; the already-shipped
GitHub PR-merge fix (`_branch_belongs_to_project`) is untouched.

### Story 35.1: A templated-form merge subject is corroborated against the querying project's own tracked ledger, not trusted from text alone
**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** `spec-marshal-templated-merge-subject-cross-project-collision` CAP-1
**Surface:** `core/promotion.py` (`_classify_merge_subject`, `merged_story_keys`, `marshal_native_merged_keys` all gain an optional `known_keys` parameter), `dispatch_supervisor/__main__.py` (`_load_known_story_keys` new helper reads the querying project's own tracked `sprint-status-ledger.yaml`; `gather_dispatch_git_facts` wired to use it — the exact function that produced 2026-09-11's false verdicts), `tests/unit/test_promotion.py`, `tests/unit/test_dispatch.py`
**Given** a bare `"Merge 22.5 into main"` subject is accepted as ANY project's own merged key with zero station-scoping, since the templated shape's text carries no station token
**When** the caller supplies `known_keys` (the querying project's own tracked story-key catalog, loaded from its `sprint-status-ledger.yaml`) **Then** a templated-shape match is trusted only when its key is a member — corroboration the ledger provides that git text cannot; an unrelated project's colliding key number is excluded
**And** with `known_keys` omitted (the default), behavior is unchanged for any not-yet-updated caller — no silent regression
**And** a missing or malformed ledger degrades to `frozenset()` (trust nothing from the templated shape), the SAFE direction, never a crash and never the dangerous direction
**And** re-running the Dream's own live reproduction (`merged_story_keys` templated-shape matches for a `pyforge-doctor` query) drops from 79 to 30 keys, with `22.11`/`22.12`/`23.x`/`28.x`/`39.x`–`49.x` all gone
**Status:** done

**Residual, explicitly named, not closed by this story:** `gather_dispatch_git_facts` (wired, closes the exact site that caused 2026-09-11's false verdicts) is the only caller updated to supply `known_keys`. `cli/dispatch.py`'s wave/reconcile paths, `dispatch_land.py`'s "already landed" short-circuit, `cli/status.py`'s reconcile-ledger report, `cli/land.py`'s wave-based landing, and `branch_story_merge_confirmed_by_grammar` all still call `merged_story_keys`/`marshal_native_merged_keys` without `known_keys` and remain exposed to the same collision until a follow-up wires them too — mirrors the sibling Dream's own "not auditing every OTHER caller" Non-goal.

## Epic 36: The library catalog can't see a station's own build manifest

**Goal:** close `docs/dreams/library-catalog-manifest-sync.md` — every `pyforge-*` station has a
second dependency manifest (its own `src/shared/packages/pyforge-<station>/pixi.toml`
`[package.run-dependencies]` table, the one `pixi-build-python` actually builds the station's
conda package from) that root `pixi.toml`, `docs/reference/library-llms-full.md`, and
`scripts/llms_full_check.py` were all blind to, since all three only ever read root `pixi.toml`.
Found 2026-09-12 auditing the catalog's own scope; seeded from `spec-pyforge-unifying-strategy`'s
Realization log ("Manifest-sync gap found").

**Process note (2026-09-12):** both stories below were implemented directly from
`spec-library-catalog-manifest-sync` before this Epic/these Stories existed — no Story was
minted in this file and no `sprint-status-ledger.yaml` row existed until the operator caught
the gap mid-turn. Recorded here, and in `AGENTS.md` § Dream-first workflow item 5 /
`CLAUDE.md`'s Dream-first paragraph, so a `ready` Spec is never again treated as license to skip
decomposition. The work itself was independently verified (live `llms-full-check` runs, a new
`pixi lock --check`, a new unit-test file) before this reconciliation, so it stands as `done`
rather than being reverted and redone.

### Story 36.1: Root pixi.toml and the catalog document every station's already-shipped, undocumented run-dep
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** `spec-library-catalog-manifest-sync` CAP-1
**Surface:** `pixi.toml` (`[feature.local-recipes.dependencies]` plus `[feature.pyforge-marshal.dependencies]`, `[feature.pyforge-mason.dependencies]`, `[feature.pyforge-warden.dependencies]`, `[feature.pyforge-doctor.dependencies]`, `[feature.pyforge-atlas.dependencies]`), `docs/reference/library-llms-full.md` (new § 1a, `pydantic` note sharpened)
**Given** `packaging`, `jsonschema`, `psutil`, `attrs`, `packageurl-python`, `license-expression`, and `filelock` are each already a direct run-dep of a station's own nested `pixi.toml [package.run-dependencies]` and already imported directly in that station's source, but none appears anywhere in root `pixi.toml` or the catalog
**When** each is added to root `pixi.toml` — `[feature.local-recipes.dependencies]` plus the owning station's own feature block — floored at the version `pixi.lock` already resolves (`packaging` 26.3, `jsonschema` 4.26.0, `psutil` 7.2.2, `attrs` 26.1.0, `packageurl-python` 0.17.6, `license-expression` 30.4.4, `filelock` 3.32.0) **Then** `pixi lock --check` reports the lock file already up to date (no new solve required — the version was already resolved transitively) and `pixi run -e local-recipes llms-full-check` no longer reports any of the seven as `undocumented-dep`
**And** the catalog's new § 1a documents all seven with their owning station(s) and import-name gotchas (`packageurl-python` imports as `packageurl`, `license-expression` as `license_expression`), and the existing `pydantic` note is sharpened to also name pyforge-atlas's and pyforge-scribe's direct declarations without adding a new root pin
**And** `filelock` — found only after Story 36.2's own scan went live, a CAP-1 scoping miss (conflated with the separate marshal/scribe filelock *adoption* question in `spec-pyforge-unifying-strategy`'s Estate leverage table) — is folded into this story's own surface and Given/When/Then rather than deferred, since it is the identical class of gap
**Status:** done

### Story 36.2: `llms-full-check` reads every station's own nested manifest, not just root pixi.toml
**Type:** feature • **Effort:** S • **Deps:** S-36.1 • **FR/AD:** `spec-library-catalog-manifest-sync` CAP-2
**Surface:** `scripts/llms_full_check.py` (`STATION_MANIFESTS`, `station_run_deps()`, `run()`), `tests/scripts/test_llms_full_check.py` (new)
**Given** `manifest_deps()` only ever walked root `pixi.toml`, so a station declaring a real run-dep only in its own `pixi.toml [package.run-dependencies]` would never be flagged as undocumented no matter how long it went unmirrored
**When** `station_run_deps()` parses every `src/shared/packages/pyforge-*/pixi.toml`'s `[package.run-dependencies]` table (same path-dep handling as the existing root-manifest walk) and `run()` merges it into the same active-dependency set **Then** a synthetic station-manifest-only entry is caught as `undocumented-dep` (`tests/scripts/test_llms_full_check.py::test_run_flags_a_station_only_dep_as_undocumented`), and once mirrored + documented the same fixture reports clean (`::test_run_stays_clean_when_station_dep_is_mirrored_and_documented`)
**And** the pre-existing root-pixi.toml-only behavior, the exit-code contract (0/1/2), and the `--json` flag are all unchanged — proven by `::test_no_station_manifests_falls_back_to_root_only_behavior` and a full clean run against the real repo (`pixi run -e local-recipes llms-full-check`, 352 active deps / 320 catalog entries, zero findings)
**And** turning the scan on against the real repo immediately surfaced Story 36.1's own `filelock` scoping miss — the new capability catching a gap in the story that shipped one commit before it, the exact self-detection this Epic exists for
**Status:** done

## Deferred-work verification state — reconciled 2026-09-08

The fleet's tracked deferred-work backlog now reads **100% verified within 30 days on all
eight stations** (marshal: 442 entries). Before the 2026-09-08 sweep steward sat at 61% and
the other seven at 92–98%; 183 entries had never been re-checked against live code since
authoring.

Marshal's own 19 never-verified entries were verified in that pass — three resolutions and
two code fixes: `cli/config.py`'s stale "9 keys" numeral removed in favour of naming
`_UNSETTABLE_KEYS` as the authority (a literal that had gone stale three times), and
`sources/chain.py`'s `_KNOWN_FIELD_KEYS` extended with `note`.

Two marshal entries got **worse** since authoring and carry corrected numbers, not stale
ones: `architecture-bmad-infra.md` still claims 94 skill directories against a live 129, and
the generator's Story Coverage Matrix now reads 394 "none observed" of 404 rows (was 207 of
208).

`spec-deferred-work-resolution-sweep`'s CAP-2/CAP-3/CAP-6 were measured during the sweep and
found inert against these ledgers — see that Spec's `sweep-tooling-effectiveness-2026-09-08.md`.

## Epic 37: The chain audited against the code (spec-artifact-chain-reconciliation CAP-1..8)

**Retroactive.** All eight CAPs shipped 2026-08-10 as one serial session, PRs #399–#406,
and every one carries a dated `verified:` line from the 2026-09-11 CAP-effect sweep at
HEAD `fd9eeb53bc` — but no story was ever written, so `chain-completeness`'s
delivered-Spec arm flagged the Spec as undecomposed. This epic documents what already
exists; no new implementation. Stories follow the audit's own Phase 0→4 shape rather
than one-story-per-CAP, because CAP-2/4/5 **co-landed in the Phase-1 PRs and are not
separable commits**. The Spec states the premise this epic exists to honour: *"The ledger
reports intent; only the code reports fact."*

### Story 37.1: Phase 0 — mechanical debt to zero before any semantic audit

As a fleet operator,
I want every detector green and every `[drift-presumed]` warn closed before the audit
reads a single story premise,
So that semantic findings are never confused with mechanical noise.

**Type:** chore • **Effort:** M • **Deps:** — • **FR/AD:** spec-artifact-chain-reconciliation CAP-1
**Given** 51 `[drift-presumed]` warns stood fleet-wide (atlas 24 / mason 1 / marshal 26)
**When** this story lands **Then** six detectors plus the meta-suite are green and zero
`[drift-presumed]` remains
**And** dangling commits are dispositioned rather than ignored
**Status:** done — shipped `2492b849c8`, PR #400 `ef3540caf6` (2026-08-10); 13/13 detectors
green at close, baseline re-stamped at `3fd83c1aa1`. **Residual by design at the time:**
20 verified-landed debris commits were left pending an operator prune decision, resolved
the same day

### Story 37.2: Phase 1 — every remaining story gets a cited verdict

As a fleet operator,
I want all 68 remaining stories given one of five verdicts with `file:line` or
command-output evidence, plus a coverage map and both-directions repair,
So that the backlog is measured against code rather than against its own self-assessment.

**Type:** docs • **Effort:** L • **Deps:** S-37.1 • **FR/AD:** spec-artifact-chain-reconciliation CAP-2, CAP-4, CAP-5
**Surface:** companion `audit-method.md` (verdict enum, traceability-matrix row shape,
coverage-debt row shape, done-claim sampling protocol, two-sided repair rule)
**Given** the ledger reported intent and nothing had checked it against fact **When** this
story lands **Then** 68/68 verdict rows exist (STILL-VALID / ALREADY-DONE / CONTRADICTED /
NEEDS-RESPEC / DROP), each cited
**And** each gate report carries a TEA/coverage-debt table, with an uncovered AC recorded
as a visible **non-gating** row
**And** stale artifacts are rebuilt through their owning skills and diverged code is
corrected with tests, each traceable to its verdict row
**Status:** done — shipped `6fce755995`/`56f3e1eebc`/`1344bd009b`, PRs #401 `1f1af7b36c`
(steward, 4 verdicts) / #402 `bc7c7e78e7` (mason, 28) / #403 `ca516848f8` (marshal, 35+1).
**Carried, not resolved:** 6 of mason's verdicts were *unfalsifiable* at audit time pending
OQ-A1 ("corrected to 24 valid (6 unfalsifiable)"), so 68/68 includes six rows whose premise
could not be settled

### Story 37.3: Phase 2 — the five completed stations audited at equal rigor

As a fleet operator,
I want atlas, doctor, herald, scribe and warden audited as hard as the unfinished
stations,
So that "complete" is an earned status rather than an unexamined one.

**Type:** docs • **Effort:** L • **Deps:** S-37.2 • **FR/AD:** spec-artifact-chain-reconciliation CAP-3
**Given** five stations read complete and had never been sampled against code **When** this
story lands **Then** each has a gate report, every chain column is verified or carries a
dispositioned finding, and Spec statuses are corrected to their earned values
**Status:** done — shipped `28551a6b65`, PR #404 `f9bc17daa0` (2026-08-10)

### Story 37.4: Phase 2b — all 61 Dreams dispositioned

As a fleet operator,
I want every Dream in `docs/dreams/` given a verdict row covering status truth, chain
completeness, satellite-consolidation correctness and stranded artifacts,
So that the non-station estate is audited too, not just the stations.

**Type:** docs • **Effort:** M • **Deps:** S-37.2 • **FR/AD:** spec-artifact-chain-reconciliation CAP-8
**Surface:** companion `dream-inventory-2026-08-10.md` — the gate report itself
**Given** 61 live Dreams **When** this story lands **Then** 61/61 are dispositioned in an
inventory gate report with a status distribution (33 archived / 19 realized / 5 specified /
2 dreamt / 2 pitched)
**Status:** done — shipped `6a4c702474`, PR #405 `7bcffbcccd` (2026-08-10); two truth-ups
recorded, estate verified. *(Note for future readers: that 2-Dream `pitched` count is the
last known live use of the value; none remains today.)*

### Story 37.5: Phase 3 — decomposition only behind a landed gate report

As a fleet operator,
I want each queued decomposition chain to start only after its own station's audit gate
report has landed,
So that new stories are never built on an unaudited premise.

**Type:** docs • **Effort:** M • **Deps:** S-37.3 • **FR/AD:** spec-artifact-chain-reconciliation CAP-6
**Given** four chains were queued (atlas → herald → doctor → steward) **When** this story
lands **Then** every decomposition PR cites the landed gate report it builds on
**Status:** done — shipped `7e10d9158b`, PR #406 `3fd83c1aa1` (2026-08-10). **Delivered as
one landed chain, not four, and that is the point:** atlas was resolved-by-delivery, doctor
landed, and **herald and steward were PREPARED THEN REVERTED** after the blind verifier
refuted them (steward: `board.py`'s own recorded revisit condition — Epic 8 completes —
objectively unmet at 1/5; herald: its Spec's serverless-intermediates sequencing brake
dropped, Q1 unannotated, companion-AD binding gaps). The gate did what it was built to do

### Story 37.6: Phase 4 — the operator resumes on measured artifacts

As a fleet operator,
I want a final baseline re-stamp, a regenerated board and a per-station go/no-go sheet,
So that the resume decision reads measurements rather than presumption.

**Type:** docs • **Effort:** M • **Deps:** S-37.5 • **FR/AD:** spec-artifact-chain-reconciliation CAP-7
**Surface:** companion `resume-package-2026-08-10.md` — the decision sheet itself
**Given** the audit is complete **When** this story lands **Then** the baseline is stamped,
the board matches the ledger, and the story projection is backed by verdict rows
**And** the per-station sheet names specific unmet gates rather than rubber-stamping
**Status:** done — shipped `9717b8a555` (2026-08-10), closing at 267/339 stories, 53/65
epics. **Shipped NO-GO for two stations** — mason and marshal both read "NO-GO until one
correct-course session"; both were lifted the same day by `8549892cce` / `f0f631ed17`,
**outside** this Spec's eight PRs. Standing hazards were carried forward explicitly rather
than closed (Tier-3 stale records at preflight; kedro-viz export ordering churn;
`test-architecture.md` wholesale-stale at 5 of 8 stations)

## Epic 38: bmad-loop cannot dispatch a story whose dependency is still ahead of it (spec-bmad-loop-forward-dependency-blindness CAP-1..4)

**Retroactive.** All four CAPs shipped via PR #238 (`a825ac0749`, 2026-08-03) with
refinements on 2026-08-08, and each carries a dated `verified:` line from the 2026-09-11
CAP-effect sweep at HEAD `a0aba94b0a` — but no story was ever written. This epic documents
what already exists; no new implementation. The Spec's `surface:` is deliberately `[]`:
the detector moved into `pyforge-doctor` (`sources/deps.py`) on 2026-08-09 under Story 6.9
and is governed by `spec-pyforge-doctor`'s own glob. **Note for future readers:** that
frontmatter note points at "this spec's memlog for the hand-off" and **no memlog exists** —
the spec directory holds only `SPEC.md`.

### Story 38.1: Every station's epics doc is swept for forward-epic dependencies

As a fleet operator,
I want every story whose documented `**Deps:**` points into a later epic found by a sweep
across all eight stations,
So that a structural blocker is known before a run burns attempts on it.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-loop-forward-dependency-blindness CAP-1
**Given** `next_actionable` is a strict file-order scan with no `depends_on` concept, and
marshal's own epics.md documented three forward deps (2.3→S-3.2, 2.7→S-4.1, 8.5→S-10.2)
the engine could not see **When** this story lands **Then** a sweep covers all 8 stations
**Status:** done — shipped `9c054effc1`, PR #238 `a825ac0749` (2026-08-03). **The Spec
carries its own correction, and it is the honest part of this story:** an inline
`CORRECTED 2026-08-08 — the parenthetical claim was false` block records that mason had 30
deps and **zero** machine-readable (a false green) while atlas had 43 with only 5 readable
(unmeasured via a `STORY_HEADING_RE` miss). The original claim that marshal's three were
"the only real ones fleet-wide" did not survive measurement

### Story 38.2: A forward-dependent story is structurally non-actionable

As a fleet operator,
I want a found forward-dependent story set to a status the picker cannot select,
So that the engine is structurally unable to dispatch it early rather than merely advised
not to.

**Type:** feature • **Effort:** S • **Deps:** S-38.1 • **FR/AD:** spec-bmad-loop-forward-dependency-blindness CAP-2
**Given** `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}` **When** this story lands
**Then** the story reads `blocked` in both the Tier-3 feed and the tracked ledger, and
`next_actionable(epic=2)` returns 2.4 rather than the blocked story
**Status:** done — shipped with S-38.1. Marshal's own three original findings (2.3/2.7/8.5)
are now `done` in the tracked ledger, so they are no longer live cases — the mechanism they
proved stays test-covered

### Story 38.3: A permanent detector prevents recurrence

As a fleet operator,
I want a later-added unmarked forward dependency caught in CI,
So that recurrence costs a red check rather than a burned dev attempt plus review cycles.

**Type:** feature • **Effort:** S • **Deps:** S-38.2 • **FR/AD:** spec-bmad-loop-forward-dependency-blindness CAP-3
**Given** the failure mode was discovered by burning compute **When** this story lands
**Then** the detector self-registers (`detectors.py:227` → `("forward-dependency",
"forward-dependency-check")`) and fails if a forward-dependent story is still `backlog` or
`ready-for-dev`
**And** it still reports on a red run, not only a green one
**Status:** done — shipped with S-38.1; re-homed into `pyforge.doctor.sources.deps` by
`2e24406414` (Story 6.9), old script deleted by `c698d4b1ad`. Verified 2026-09-11: live
sweep reports 1 measured / 0 partial / 7 no-dispatch / 0 unmeasured, none silently clean;
`test_sources_deps_forward_dependency.py` 24/24

### Story 38.4: An unparseable epics format is reported honestly, never silently clean

As a fleet operator,
I want a station whose epics doc the detector cannot parse reported as **not determinable**
rather than clean,
So that the fidelity doctrine applies to the detector itself.

**Type:** feature • **Effort:** S • **Deps:** S-38.3 • **FR/AD:** spec-bmad-loop-forward-dependency-blindness CAP-4
**Given** some stations use an older narrative format (confirmed: `pyforge-warden`)
**When** this story lands **Then** those report not-determinable, never a bare "clean"
**Status:** done — pinned directly by `test_unparseable_heading_is_not_silently_clean` and
`test_headings_without_deps_field_report_unmeasured`. **Open by design, carried not closed:**
59 prose dependency declarations across atlas/mason/steward are **not** migrated, so those
stations report `PARTIAL` rather than `MEASURED`. A by-hand audit of all 62 confirmed no
prose declaration hides a real forward dependency — a legibility gap, not a live risk.
Migration plus a gate that fails on `PARTIAL` must land in **one** change, because the gate
reds CI until the migration completes. *(The Spec states 59 in one place and 62 in another;
the discrepancy is in the source text and is not resolved here.)*

## Epic 39: `marshal status` recovers from a poisoned harness run id (spec-marshal-status-harness-run-id-poisoning CAP-1..2)

**Retroactive.** Both CAPs shipped by direct commit `e7039b9ee6` (2026-08-15) with no story
written, and both carry dated `verified:` lines from the 2026-09-11 sweep. This epic
documents what already exists; no new implementation. **This is a defect fix, not a
capability** — the commit subject is literally "fix status permanently blinding to a healthy
run after a launch poll timeout", and the Spec's own decomposition note records the
judgement: *"like its sibling Spec, no `epics.md` story owns it — but the code is live and
covered, so the value is `shipped`, not `ready`."*

### Story 39.1: A null harness run id recovers by filesystem discovery

As a fleet operator,
I want `marshal status` to recover the real run id from `.bmad-loop/runs/` when the journal
field is null,
So that a spin-time poll timeout cannot permanently blind status to a healthy run.

**Type:** bugfix • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-status-harness-run-id-poisoning CAP-1
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`
**Given** a poll timeout (`MRS-SPIN-004`) journals `harness_run_id: null` permanently into
the launch OUTCOME entry, and the only fallback re-read the same poisoned field **When**
this story lands **Then** a timestamp-correlated `.bmad-loop/runs/` scan recovers the real
id, the same discovery `cli/spin.py::_latest_run_dir` already did
**And** status reports real state (`running`/`idle`/`stopped`) instead of `unknown`
**Status:** done — shipped `e7039b9ee6` (2026-08-15); reproduced against the live case
(`pyforge-doctor` story 9.1's spin, a healthy ~40-minute run that `marshal status`,
`fleet-picture` and `dashboard-gen`'s in-flight card had all been blind to).
`test_poisoned_harness_run_id_recovers_via_filesystem_discovery` passes. *(The Spec cites
this function at two different line numbers, `:659` and `:700` — both are drifted; cite
neither as current.)*

### Story 39.2: A genuinely unrecoverable run still degrades honestly

As a fleet operator,
I want `MRS-STATUS-002` to keep firing when no run dir is discoverable or readable,
So that the fix narrows the failure mode rather than removing honest degradation.

**Type:** bugfix • **Effort:** S • **Deps:** S-39.1 • **FR/AD:** spec-marshal-status-harness-run-id-poisoning CAP-2
**Given** recovery must not become a false green **When** this story lands **Then** a run
with no discoverable dir — and one with only stale siblings — still reports `unknown` with
the finding intact
**Status:** done — shipped `e7039b9ee6`;
`test_poisoned_harness_run_id_with_no_run_dir_still_reports_unknown` and
`test_poisoned_harness_run_id_only_stale_siblings_still_reports_unknown` both pass.
**Not to be confused with** the surviving `pyforge-steward` UNKNOWN — `DW-STATUS-2026-09-08-1`
traced that to a different cause (a harness-native run marshal never launched), owned by
Story 5.11

## Epic 40: The genesis-installer name retires completely (spec-genesis-installer-name-retirement CAP-1..8)

**Retroactive.** All eight CAPs shipped as PR #318 (`28b3bca44d`, branch
`retire/genesis-name-2026-08-08`) with a late CAP-6 follow-up `0ce1db84ce` (2026-09-12),
and each carries a dated `verified:` line — but no story was ever written. This epic
documents what already exists; no new implementation. The mandate was explicit: retire the
name *"not relabeled, not renumbered by hand, but resolved by running the standard planning
chain"*, so the CLI got designed once with its two open contradictions actually decided.

### Story 40.1: One canonical epics.md, with landed story identity preserved

As a fleet operator,
I want `epics-genesis-installer.md` merged into one `epics.md` and archived rather than
deleted, with every already-landed story key unchanged,
So that the second epics document stops existing without rewriting delivered history.

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** spec-genesis-installer-name-retirement CAP-1, CAP-8
**Given** a second epics document existed alongside the canonical one **When** this story
lands **Then** one `epics.md` remains and the old file is archived, not deleted
**And** every `status=done` key is identical after the rewrite; only backlog-only epics are
free to be restructured
**Status:** done — shipped `a135cee4fc` (2026-08-08), whose own body records *"CAP-8 PASS:
all 59 `done` keys byte-identical to the pre-rewrite snapshot"*. **CAP-8 remains `partial:`
in the Spec** — the 2026-09-11 sweep did not re-derive the pre-rewrite snapshot, which
*"isn't preserved as a companion artifact"*, so today's ledger is consistent with the claim
holding rather than independently re-proven byte-for-byte

### Story 40.2: One contiguous FR space, and every installer-only namespace decided

As a fleet operator,
I want the separate `FR1..FR62` numbering island resolved by chain rewrite rather than by
hand, and each installer-only namespace given an explicit fate,
So that one PRD has one numbering space and no bare-digit citation survives.

**Type:** docs • **Effort:** L • **Deps:** S-40.1 • **FR/AD:** spec-genesis-installer-name-retirement CAP-2, CAP-3
**Surface:** companion `citation-map.md` — the pre-rewrite ground-truth inventory, holding
the full 62-row `FR1..FR62 → FR-66..FR-127` mapping plus per-file citation-site line lists
**Given** a no-dash `FR1..FR62` island and installer-only `NFR-O1`/`SC-01..10`/`K-01..03`/
`OQ-1..9` namespaces **When** this story lands **Then** every FR is dashed and sequential
(verified 2026-09-11: 196 unique numbers, FR-1..FR-196, zero gaps)
**And** each namespace's fate is stated in the PRD — `NFR-O1` retired into `NFR-12`,
`SC-01..10` and `K-01..03` adopted as-is
**Status:** done — shipped `66511bae13` (2026-08-08). **The SHIPPED banner was FALSE when
first stamped and this is on the record:** the memlog states the 2026-08-08 success criteria
*"were FALSE when stamped — epics.md carried 195 live satellite-namespace citations until
the audit's mechanical re-issue"* (reviewer-verified at all 195: FR+65, AD+50, zero
mismatches). Corrected by the 2026-08-10 audit, i.e. by Epic 37's Phase-1 work

### Story 40.3: Both CLI contradictions are decided, not flagged

As a fleet operator,
I want the argparse-vs-typer framework question and the `init`/`check` verb collision
actually resolved in the architecture and PRD,
So that the fold-in stops preserving two undecided contradictions.

**Type:** docs • **Effort:** M • **Deps:** S-40.2 • **FR/AD:** spec-genesis-installer-name-retirement CAP-4, CAP-5
**Given** the installer architecture said typer+rich while the shipped Marshal CLI is
argparse, and `genesis init`/`genesis check` collided with shipped `marshal init <slug>`/
`marshal check` **When** this story lands **Then** AD-51 states the framework and why —
*"amended typer+rich -> argparse on measurement (14 shipped subparsers, zero typer in
tree)"* — with no "flagged, not resolved" language left
**And** the installer's distinct question gets its own verb surface: the `marshal seed
<verb>` noun group, live in `cli/seed.py`
**Status:** done — shipped `cfaa9a01ed` (2026-08-08); `grep -rn "import typer"` returns
nothing

### Story 40.4: No document still frames it as a separate thing

As a fleet operator,
I want every `Satellite: Genesis Installer` header and separate-thing prose removed from
the planning tree,
So that the retirement is real in the documents, not only in the numbering.

**Type:** docs • **Effort:** M • **Deps:** S-40.2 • **FR/AD:** spec-genesis-installer-name-retirement CAP-6
**Given** the 2026-08-02 consolidation left satellite framing in place **When** this story
lands **Then** `grep -i "genesis.installer"` across `{prds,architecture,specs,briefs}`
returns nothing outside `archive/` and memlogs
**Status:** done — but **only at the second attempt, and the Spec says so rather than
hiding it.** The 2026-09-11 sweep recorded `NOT fully passing, not fabricating a clean
result` with a live header surviving at `brief.md:172`; `0ce1db84ce` (2026-09-12) closed it,
fixing that header plus three prose mentions **and six more live headers in
`spec-pyforge-marshal/SPEC.md`** — marshal's own kernel Spec, which the prior pass had never
looked at

### Story 40.5: One dashboard row, and no code reference to the retired name

As a fleet operator,
I want the fleet dashboard to carry a single `pyforge-marshal` row with the retired name
gone from the code,
So that separateness stops leaking onto the board.

**Type:** feature • **Effort:** S • **Deps:** S-40.1 • **FR/AD:** spec-genesis-installer-name-retirement CAP-7
**Given** PR #233 had relabelled the second row rather than removing it **When** this story
lands **Then** `IMPL_CAMPAIGN` holds one marshal entry (86 stories), `IMPL_CAMPAIGN_LEDGER`
drops the key, and `dashboard_drift_check.py` is clean
**Status:** done — shipped `cfeccf3860` (2026-08-08); the code comment records the intent
exactly — *"the `genesis-installer` row is GONE, not relabelled"*. `IMPL_CAMPAIGN_LEDGER`
has itself since been retired into `_PROJECT_OVERRIDES`

## Epic 41: Every planning tree tells the truth about itself (spec-bmad-output-hygiene CAP-1..12)

**Retroactive, and closing a hole the Spec opened deliberately.** All twelve CAPs shipped
as PR #227 (`b0039075f8`, 2026-08-02, 147 files) plus two post-reopening additions, and
every CAP carries a dated `verified:` line from the 2026-09-11 sweep (PR #1226). No story
was ever written — **and that was a recorded decision, not an oversight**: the Spec's own
non-goal reads *"No new PRD, architecture, or epics chain for this cleanup itself"*, with
the memlog deciding to *"go straight from Spec to execution."* This epic closes exactly
that gap retroactively; no new implementation. Stories group the twelve CAPs by failure
mode rather than one-per-CAP, following how they actually landed.

The Spec's premise: *"Every station's planning tree should tell the truth about itself —
real content or an honest placeholder, never a templated fiction that happens to compile."*

### Story 41.1: Dead scaffolding is archived, never deleted

As a fleet operator,
I want dead test scaffolding, the hollow `sprint-status.yaml` stub and orphaned single
files moved into a mirrored `archive/` path,
So that a bulk template commit's debris leaves the live tree without losing the history.

**Type:** chore • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-output-hygiene CAP-1, CAP-2, CAP-5
**Given** `dad47c408a` (2026-08-02) stamped generic template content across all 9 projects
**When** this story lands **Then** `tests/`/`pytest.ini`/`playwright.config.ts` are absent
from the 7 station roots carrying zero real tests and present under `archive/`
**And** the dead 0%/empty-array `sprint-status.yaml` stub is archived from all 9 projects
while the live `sprint-status-ledger.yaml` stays
**And** two orphaned single files (atlas `RESUME-EPIC-10.md`, herald intake note) are
archived
**And** every move was grep-verified beforehand as read by nothing
**Status:** done — shipped `22da995c7c` (CAP-1, 95 files, pure renames) and `f7654a4c70`
(CAP-2 + CAP-5); confirmed live on disk for all 7 and all 9 respectively

### Story 41.2: Templated fiction is replaced with real content

As a fleet operator,
I want the fabricated `test-architecture.md`, the `[role]`/`[responsibilities]` README
placeholders and the drifted `project-context.md` files regenerated against live ground
truth,
So that no planning document asserts something its own project contradicts.

**Type:** docs • **Effort:** M • **Deps:** S-41.1 • **FR/AD:** spec-bmad-output-hygiene CAP-3, CAP-4, CAP-6
**Given** the bulk commit left fabricated prose in place **When** this story lands **Then**
Genesis's `test-architecture.md` makes no claim its own PRD/architecture contradicts
**And** no literal `[role]`/`[responsibilities]` token survives, and no README describes
archived scaffolding as live
**And** mason's and herald's `project-context.md` counts match their ledgers
**Status:** done — shipped `8e9c84a101` / `5c5e372782` / `9c7acb39bb` (2026-08-02).
**Scope corrections found mid-execution, recorded rather than smoothed over:** the README
placeholders actually lived in each station's project-root README, not `planning-artifacts`
as the Spec first assumed; and the Dream's own "real" counts had themselves gone stale
(Mason 4/38→4/48, Herald 4/17→4/27). **Two of the three verified artifacts no longer exist
today** — Genesis as a project, and `project-context.md` (superseded by BMAD 6.12's
`bmad-project-context`) — *verified once, then their surface legitimately retired*, not
regressed

### Story 41.3: Stale pointers and off-convention layouts are corrected

As a fleet operator,
I want the `PROJECTS.md` Dream pointers, CLAUDE.md's sync-section path, and two
off-convention directory shapes fixed,
So that content that is correct stops being reached by a wrong name or path.

**Type:** docs • **Effort:** M • **Deps:** S-41.1 • **FR/AD:** spec-bmad-output-hygiene CAP-7, CAP-8, CAP-9, CAP-10
**Given** two `PROJECTS.md` Dream pointers resolved to a renamed or deleted file, CLAUDE.md
named a stale `local-recipes` path, marshal's brief sat loose, and herald's brief/
architecture dirs carried a retired slug **When** this story lands **Then** both Dream
pointers resolve to an existing `type: dream` file
**And** CLAUDE.md matches where `bmad_drift_check.py`/`pixi.toml`/`fleet_scan` actually read
from
**And** marshal's brief is sharded to `briefs/brief-pyforge-marshal-2026-07-25/brief.md` and
herald's dirs carry the station slug
**Status:** done — shipped `f7654a4c70` (CAP-7, folded in unnamed in its subject),
`207f1d43c8` (CAP-8 + CAP-9) and `cc6db24346` (CAP-10). **CAP-8 carries a reverted-work
note kept deliberately for the record:** a relocation *"was executed, then reverted in full
… before this branch went anywhere"* — the 13 factory docs were never misfiled; CLAUDE.md
was simply stale

### Story 41.4: The currency detector is fixed before its data is caught up

As a fleet operator,
I want the zero-grace currency check given a 2-day window first, and only then the
genuinely stale pairs re-stamped,
So that noise is removed before data is touched, and real drift stays visible.

**Type:** feature • **Effort:** M • **Deps:** S-41.3 • **FR/AD:** spec-bmad-output-hygiene CAP-11, CAP-12
**Given** a user report of universal "outdated" readings after CAP-10, where 0–1 day
`spec`/`prd` findings are true by construction rather than drift **When** this story lands
**Then** `_FEEDS_GRACE_DAYS = 2` is live in the currency loop and the 0–1 day findings
vanish across all 8 stations
**And** only pairs whose own `currency_review` proves the bump was structural are
re-stamped
**Status:** done — shipped `c5aaf4f3e0` (CAP-11) and `1567a478d1` + `698d32798c` (CAP-12).
**CAP-12 deliberately leaves real findings visible rather than clearing the board** —
doctor (`prd`/`arch`, architecture genuinely behind), mason (`arch`/`epics`, a real 4-FR
gap), and warden (`prd`/`gates`, a structural property of the artifact type) are each
*"left unfixed and visible"*, out of scope for a hygiene spec. *(The Spec's own success line
says "16 → 4" while its parenthetical and Success signal both say 3 remaining; the
discrepancy is in the source text and is not resolved here.)* The `fleet_scan`-driven
dashboard surface these two CAPs measured against has since been retired fleet-wide, so
re-measurement today needs the successor tooling

## Epic 42: spec-surface tolerates governed overlap (spec-surface-overlap-tolerance CAP-1..2)

**Goal:** `spec-surface-check`'s DRIFT half stops flagging a file whose co-governing spec
already reconciled it cleanly. Extension point of `spec-regenerable-factory` CAP-3
(shipped). Contract is marshal's; the code is doctor's
(`pyforge.doctor.sources.chain`), so doctor records an incoming surface claim in its own
memlog before any code lands — the established cross-station convention.

**Why now:** the class is live and recurring, not theoretical. PR #1288 papered over 178
findings across 17 specs with per-file `surface-drift-exclude:` entries, and on
2026-09-14 a single `pixi.toml` description edit plus two source edits generated drift
against **13 more specs** — every one of them a kernel spec that co-governs a path a
narrower spec had already reconciled. Each cleared only by a hand-written memlog line and
a scoped stamp. Minting narrow specs under kernel specs is the fleet's normal shape, so
the noise compounds with every new spec.

### Story 42.1: A co-governed file is clean when any one of its governing specs reconciled it

As a station operator,
I want `spec-surface-check` to judge a changed file across all of its governing specs at
once, rather than each spec in isolation,
So that reconciling a file in the spec that actually owns the change clears it, instead
of leaving permanent noise on every other spec that happens to match the same glob.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-surface-overlap-tolerance CAP-1
**Surface:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py`
(`_drift_findings`, `chain.py:1662-1742`) + its unit tests. Cross-station: doctor owns
the module, marshal owns the contract.
**Given** two specs govern the same path and one spec's memlog moved AND names that path
**When** `spec-surface-check` runs
**Then** neither spec reports `drift` or `drift-presumed` for that path
**And** the loop groups by path before judging, rather than iterating specs independently
**And** the per-spec bar is UNCHANGED — still `spec_moved AND f in named` (the answered
open question: the existing bar is the right predicate to OR; only the loop shape changes)
**Status:** done

### Story 42.2: Overlap tolerance narrows a false positive without widening what counts as reconciled

As a station operator,
I want proof that the OR only ever removes a false finding,
So that a genuinely unreconciled file cannot be hidden by gaining a second governing spec.

**Type:** feature • **Effort:** S • **Deps:** S-42.1 • **FR/AD:** spec-surface-overlap-tolerance CAP-2
**Surface:** `src/shared/packages/pyforge-doctor/tests/unit/` fixtures for
`spec-surface`; no production change beyond 42.1.
**Given** 42.1 has landed
**Then** every existing single-owner `drift` / `drift-presumed` fixture passes unchanged
**And** a new multi-owner fixture where NEITHER co-governor names the path still produces
a finding
**And** that finding keeps the STRONGEST severity among its co-governors — a co-governor
whose memlog never moved yields `drift` (FAIL), so the group result is FAIL, never
downgraded to `drift-presumed` merely because another co-governor moved for an unrelated
reason
**And** the coverage half (`ungoverned`) is untouched
**Status:** done

## Epic 43: The citation detector shows everything it knows (spec-fleet-consistency-standard CAP-6, fix)

Minted 2026-09-14 from `DW-AD-CITATION-2026-09-14-2` — a fix on the CAP-6 detector Epic 32 shipped.
It is its own epic rather than a ninth story on Epic 32 because **a `done` epic stays `done`**: the
fleet has no precedent for a done roll-up carrying a non-done story, and `ledger-regression` (the
Doctor verdict that became a blocking CI step this morning) reads any `done → in-progress` key in
`origin/main..HEAD` as a regression — it fired on the first attempt, which had reopened `epic-32`.
The lesson is recorded so it is not re-learned: a fix on a shipped Spec gets a new epic, never a
reopened one. One story; the Spec's CAP-6 is the contract.

### Story 43.1: The citation detector shows everything it knows
**Type:** fix • **Effort:** XS • **Deps:** S-32.6 (done) • **FR/AD:** spec-fleet-consistency-standard CAP-6 • `DW-AD-CITATION-2026-09-14-2`
**Surface:** `scripts/ad_citation_check.py`, its test under `tests/scripts/`, `scripts/.ad-citation-baseline.json` and `scripts/.cap-citation-baseline.json` (the `recorded:` stamp only).
**Given** `ad_citation_check` prints at most ten NEW rows per class (`new[:10]`, `cap_new[:10]`) beneath a headline that reports the full count, so the 2026-09-14 red on `origin/main` — 4 ad + 57 cap NEW — was read and recorded as 14 from the printed rows, the same "head truncates findings out of view" class CLAUDE.md § Reading a detector's result warns about, implemented inside the detector; and `--write-baseline` / `--write-cap-baseline` stamp `recorded:` with hard-coded literals (`"2026-09-08"`, `"2026-09-10"`), so a baseline re-stamped on any later date still claims those dates **When** every NEW row is printed (the NEW set *is* the actionable set; the baselined set is already summarised by count, and a detector that exits 1 must show what it exits on) and the stamps carry the actual stamping date **Then** the printed NEW rows equal `len(new)` and `len(cap_new)` for any size, proven by a test with more than ten synthetic findings in each class
**And** `--write-baseline` / `--write-cap-baseline` write today's ISO date, proven by a test that reads it back; the two existing baseline files are re-stamped once so their `recorded:` reflects the 2026-09-14 shrink rather than the literals
**And** no other behaviour of the detector changes — the ratchet semantics, the "since fixed" accounting, the `[:10]`-free summary lines and the exit codes are byte-for-byte the same, proven by the existing `tests/scripts/` suite staying green

## Epic 44: The operator stops re-pasting the status prompt — marshal watches its own runs (spec-marshal-run-watch CAP-1..5)

Minted 2026-09-15 from `docs/dreams/marshal-run-watch.md`. A live, hand-driven `/loop` session
watching pyforge-herald run `20260914-201759-bd47` (Epic 21) worked out a repeatable ground-truth
+ delta + boundary-pacing ritual and captured it as a Claude-only project skill
(`.claude/skills/marshal-run-watch/`) — proven correct against a real multi-hour run, but
invisible to marshal's own CLI, unified grammar, MCP face, persona, and portal. Story 44.1 ports
that proven logic into a real `marshal watch` CLI verb (CAP-1+CAP-2, this epic's implementable
round); Stories 44.2–44.4 name the three follow-on faces (MCP, persona menu, portal view) as
separate, deferrable stories per the Spec's own "CLI first" constraint.

### Story 44.1: `marshal watch` ports the operator's ritual into a real CLI verb

As a fleet operator,
I want a `marshal watch` CLI verb that gathers ground truth for a pinned run, a station's
current run, or the whole fleet, diffs it against the last observation, and reports only
what changed plus a recommended next-check delay,
So that watching a live `bmad-loop` run or `bmad-build-auto` dispatch is a marshal capability
I can run from any terminal, not a chat ritual I re-paste by hand every time.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-run-watch CAP-1, CAP-2
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (new),
`cli/main.py` (subparser wiring, mirroring `status`/`homes`/`check`), and its test suite under
`src/shared/packages/pyforge-marshal/tests/`. Reuses `bmad-loop status <run_id> --json` /
`bmad-loop list --json` (bmad-loop pattern) and `marshal status --project <slug>`'s `dispatch_*`
fields (bmad-build-auto pattern) as ground truth — no new data source.
**Given** `marshal watch --project <slug> --run <run_id>` is invoked against a live `bmad-loop`
run, or `marshal watch --project <slug>` with no run pinned (auto-detecting the station's
current run, either pattern), or `marshal watch --fleet` (every project under
`_bmad-output/projects/*/`, discovered live, never a hardcoded list)
**When** ground truth is gathered and diffed against the immediately-prior persisted observation
**Then** the report states only what changed (a story's phase or `commit_sha`, the run's overall
status, a new escalation, the loop-branch SHA, a PR's state) — or plainly that nothing changed —
in the five-section shape (Session Completions / Delta Since Last Update / Currently Running /
Up Next & Full Queue / User Action Required) for a pinned/station run, or the compact
per-project snapshot (escalated/paused projects sorted first) for `--fleet`
**And** the command also prints a recommended next-check delay and a one-line reason, using the
validated pacing (`min(300s, seconds-to-next-:00/:30-boundary)` while a run is actively
progressing, boundary-only while paused/escalated, no recommendation once a run is finished)
**And** for the `bmad-loop` pattern, `marshal watch` never reads `marshal status`'s `dispatch_*`
fields as that run's per-story ground truth — a test fixture where `dispatch_*` describes a
different, older run than the live `bmad-loop status` result proves the report uses only the
`bmad-loop` result and states plainly that a stale unrelated dispatch record was present and
ignored
**And** the persisted last-observation cache is a local, regenerable file; deleting it or
pointing at a slug/run with no prior cache produces a first-observation report, never a
fabricated delta
**And** every path above is covered by a test that drives the same diff+report logic against
fixture journals/state, not a live `bmad-loop` process
**Status:** done

### Story 44.2: `marshal watch` is reachable over MCP

As an agent acting through the marshal station's service face,
I want `marshal watch`'s report available as a named tool on `POST /stations/marshal/mcp`,
So that I can watch a run without shelling out to the CLI directly.

**Type:** feature • **Effort:** S • **Deps:** S-44.1 • **FR/AD:** spec-marshal-run-watch CAP-3
**Surface:** `src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py` — a new
`@server.tool(...)`-registered tool alongside the existing `publish_loop_run` /
`heartbeat_loop_run` / `complete_loop_run` / `list_loop_story_tasks` tools.
**Given** Story 44.1 has landed
**When** the new tool is called with the same project/run/fleet parameters `marshal watch`
accepts
**Then** it returns the same report shape Story 44.1 produces, and is callable by the
`bmad-agent-marshal` persona's `mcp` action kind (`POST /stations/marshal/mcp` only, no other
URL/method/host)
**Status:** done

### Story 44.3: The Marshal persona can offer "watch a run" as a menu action

As the Marshal station persona,
I want a menu entry that dispatches `pyforge marshal watch ...` grammar,
So that an operator addressing me as Marshal can watch a run without leaving the persona.

**Type:** feature • **Effort:** XS • **Deps:** S-44.1 • **FR/AD:** spec-marshal-run-watch CAP-4
**Surface:** `bmad-agent-marshal`'s persona customization (`agent.menu` entry) — no change to
the persona skill's Allowed/Forbidden actions, since `pyforge marshal watch ...` is already a
permitted `grammar` action kind (CAP-16).
**Given** Story 44.1 has landed
**When** the operator selects the new menu entry
**Then** the persona issues a `grammar` action kind starting `pyforge marshal watch`, and the
resulting transcript shows only FR-13 grammar (no direct filesystem, no ad-hoc HTTP)
**Status:** done

### Story 44.4: `marshal watch`'s report is viewable in the portal

As an operator using the browser portal,
I want to see `marshal watch`'s report for a project or run I select, without a terminal,
So that watching a run doesn't require CLI access.

**Type:** feature • **Effort:** M • **Deps:** S-44.1 • **FR/AD:** spec-marshal-run-watch CAP-5
**Surface:** `src/shared/packages/django-marshal/src/django_marshal_portal/views.py` (new view,
alongside `chrome_home`) and `urls.py` (new route).
**Given** Story 44.1 has landed
**When** an operator selects a project/run in the portal
**Then** the new view renders Story 44.1's report for that selection, with no terminal required
**Status:** done

## Epic 45: BMAD from inside Cursor's own chat (spec-bmad-cursor-interactive-routing CAP-2..4)

Minted 2026-09-15 from `docs/dreams/bmad-cursor-interactive-routing.md` after CAP-1 ran
in Cursor Agent interactive chat and **passed**. The running model invoked the Task tool
and got a context-free in-turn review (`HUNT7K2Q`; leak recheck `PARENT_USER_QUERY=UNKNOWN`).
That is not headless `cursor-agent -p`, not a tool-less Ask panel, and not BMAD
`workflow.md` Blind Hunter by name — it is the capability the workflow needs.

**CAP-1** is closed in the Spec memlog (no story). **CAP-2** is committed: mechanical
`.mdc` generation plus a pixi task and a drift detector for the `bmad-build` /
`bmad-build-auto` pilot pair. **CAP-3b** remains the residual HALT on a surface with no
Task tool. **CAP-3a** is a later empty follow-on (no story). **CAP-4** is verified
(`Read` / `@file`; no `@path` inline import). Do not claim Ask-panel or all-skills
parity. Do not ship CAP-3a without its own equivalence evidence.

### Story 45.1: A pixi task generates `.mdc` from `SKILL.md`

As an operator working in Cursor chat,
I want `.cursor/rules` files for the BMAD pilot pair generated from each skill's
`SKILL.md`,
So that typing an equivalent request runs the same `render_skill.py → workflow.md` path
Claude Code runs, without a hand-maintained fork.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-bmad-cursor-interactive-routing CAP-2
**Surface:** a maintained pixi task (and its generator script under the three-place rule),
emitting `.mdc` for `bmad-build` and `bmad-build-auto` from `.claude/skills/bmad-*/SKILL.md`
frontmatter (`name`, `description`) plus the two-step trigger body.
**Given** either pilot `SKILL.md` exists
**When** the pixi task runs
**Then** the generated `.mdc` carries that skill's description and the same
`render_skill.py → workflow.md` trigger Claude Code uses
**And** generation is mechanical — no hand-edited body that can drift from `SKILL.md`
**And** day-one scope is the two-skill pilot, not the full BMAD skill set
**Status:** done

### Story 45.2: A drift detector fails a stale generated `.mdc`

As an operator,
I want CI to fail when a generated Cursor rule no longer matches its `SKILL.md`,
So that a skill change cannot silently rot the Cursor-chat path.

**Type:** feature • **Effort:** S • **Deps:** S-45.1 • **FR/AD:** spec-bmad-cursor-interactive-routing CAP-2 (OQ-3)
**Surface:** a doctor-sourced or script detector plus pixi task, on the three-place rule,
wired into `detectors-ci`.
**Given** a pilot `SKILL.md` changes and the generated `.mdc` is not regenerated
**When** the detector runs
**Then** it fails (findings), never a silent green
**And** a matching pair is clean
**And** a one-time untracked generate is not the lasting shape — the task + detector stay
**Status:** done

### Story 45.3: The pilot pair uses Task when available and HALTs when it is not

As an operator invoking `bmad-build-auto` from Cursor chat,
I want reviewer subagents to run through the Task tool when that tool is present, and
the workflow to HALT `blocked`/`no subagents` when it is not,
So that review never silently degrades. Team memory is reached by `alwaysApply` plus
`@file` / Read, never a claimed `@path` inline import.

**Type:** feature • **Effort:** M • **Deps:** S-45.1 • **FR/AD:** spec-bmad-cursor-interactive-routing CAP-2, CAP-3 (residual), CAP-4
**Surface:** the generated pilot `.mdc` files and any Cursor-facing note they carry;
no change to headless `cursor-agent -p` dispatch (Story 22.8).
**Given** Cursor Agent chat exposes the Task tool
**When** `bmad-build-auto` reaches a mandatory reviewer step
**Then** the step launches a context-free Task subagent and consumes the in-turn result
**Given** the running surface has no model-invoked Task tool (Ask, no-tools)
**When** that same step is reached
**Then** the workflow HALTs `blocked`/`no subagents` — it does not skip review and it
does not shell out to `cursor-agent -p` as a substitute reviewer (CAP-3a is out of
scope)
**And** team-memory content is reachable via `Read` or `@file` of
`.claude/memory/MEMORY.md`; no rule claims Claude Code's `@path` inline import
**Status:** done

## Epic 46: The session path — one substrate, silent saves, every harness (spec-marshal-token-economy CAP-19..24)

Minted 2026-09-16 from the operator-ruled token-savings consolidation: the five
token-savings Dreams folded into `docs/dreams/marshal-token-economy.md`, and the
day-old session-path seed Spec folded into `spec-marshal-token-economy` as
CAP-19..CAP-24 (no satellite Specs — one Dream, one Spec). The decision record
is the superseded folder's eleven-entry memlog
(`specs/spec-token-economy-claude-session-path/.memlog.md`): the OQ answers
(dispatch measured / interactive documented; repo-default `[context]` with wire
as capability-aware `auto`; doc thinning deferred), the multi-harness currency
matrix, the adversarial review (prompt-cache collision is the sharpest risk),
and the substrate-primary reordering.

**CAP-19d** (freshness SLA) has no story — `scribe compile_surface` owns
freshness and `spec-scribe-recall-stale-between-nightlies` already surfaces
staleness. **Do not** flip the parent Dream to `realized` — the benchmark
artifact is its realized-guard. **Do not** remint Epic 28/33 or re-litigate
28.29 (Cursor wire is dead; `auto` skips it, and that is the intended
economics). Savings telemetry stays advisory — no second PR gate.

### Story 46.1: A bare clone bootstraps the substrate

As an agent starting on a cloud runner (Devin, Copilot cloud, Cursor background),
I want nightly-built substrate artifacts (codegraph, cocoindex distills,
planning-graph export) published as CI/release assets and a
`pyforge context bootstrap` fetch-or-rebuild command,
So that a bare clone opens on the shared substrate instead of re-deriving it
privately at ACU/quota cost.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-19(a)
**Surface:** a publisher (nightly workflow or release-asset upload) for the
substrate artifacts, plus the `pyforge context bootstrap` CLI in pyforge-core or
marshal (fetch-or-rebuild; rebuild is loud and attributable, never silent).
**Given** a fresh clone with no `.codegraph/`, no distills, no planning graph
**When** `pyforge context bootstrap` runs
**Then** it fetches the latest published artifacts and verifies their digests,
or rebuilds locally with a named finding
**And** the fetched substrate is byte-identical to what a loop home produced
**Status:** backlog

### Story 46.2: The canonical context bundle is digest-pinned

As an operator running mixed harnesses,
I want a canonical, digest-pinned context bundle extending Story 28.8's
declaration half,
So that every harness opens on identical bytes and prefix stability — the only
portable cache — holds across Claude, Cursor, Copilot, Gemini, and Devin.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-19(b)
**Surface:** the 28.8 context-declaration surface extended to a canonical bundle
with a recorded digest; a compare surface two harnesses can be checked against.
**Given** two harnesses on the same commit
**When** each assembles its opening context
**Then** the bundles compare byte-identical by digest
**And** a drift in either assembly is a named finding, not a silent divergence
**Status:** backlog

### Story 46.3: `scribe capture` is the blessed session-close ritual

As an operator who wants memory write-back from every harness,
I want `scribe capture` named in the front-door docs as the harness-neutral
session-close ritual,
So that what a session learned lands in the shared substrate no matter which
harness ran it.

**Type:** docs • **Effort:** S • **Deps:** S-46.7 • **FR/AD:** spec-marshal-token-economy CAP-19(c)
**Surface:** AGENTS.md / CLAUDE.md / the station skill notes — the same docs
that name the front door — plus one line in each harness profile's notes.
**Given** a session closes in any harness
**When** the operator or agent follows the front-door docs
**Then** the close ritual is `scribe capture` with decision-grade facts, and the
docs say so in one place
**And** capture hygiene is stated: no secrets, decision-grade facts only
**Status:** backlog

### Story 46.4: Wire auto resolves against the declared wrapper

As an operator,
I want `_bmad-output/policy-defaults.toml` to carry the repo-default `[context]`
block with wire declared `enabled = "auto"` — a tri-state resolving against the
running harness profile's declared `[wrapper]`,
So that both engines gain the harness-agnostic layers by default and wire turns
on exactly where the harness can take it, with zero per-station config.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-20
**Surface:** `core/policy.py` (tri-state schema + resolution), the harness-profile
`[wrapper]` declaration read, and `policy-defaults.toml`. Per-station
`marshal-policy.toml` becomes force-override only.
**Given** a fresh loop home with zero station config
**When** a dispatch or spin launches
**Then** the harness-agnostic layers journal as on (repo default) and wire is on
iff the profile declares a `[wrapper]`
**And** on Cursor the wire layer is a clean skip — never a journaled wrap it
cannot perform (28.29)
**And** wrapper declared but binary missing stays a WARN (`MRS-DISP-033` class),
never silent
**Status:** backlog

### Story 46.5: The journal splits silent saves from configured layers, and the rollup speaks per-harness currency

As an operator reading savings,
I want the journal taxonomy to distinguish silent saves (repo default) from
configured layers, and the rollup keyed per harness × binding currency,
So that a Cursor-first station never reads a Claude-shaped number as its own —
USD for Claude, quota-burn for Cursor/Copilot, request-count for Gemini, ACUs
for Devin, never one blended token number.

**Type:** feature • **Effort:** M • **Deps:** S-46.4 • **FR/AD:** spec-marshal-token-economy CAP-20
**Surface:** `core/layer_savings_sources.py` journal schema and the rollup
report surface.
**Given** runs on at least two harnesses with different binding currencies
**When** the rollup renders
**Then** each harness's savings appear in their own currency with no blended
total
**And** silent saves and configured layers are distinguishable per journal row
**Status:** backlog

### Story 46.6: An interactive session whose layers lapse gets a persistence advisory

As an operator on the interactive path,
I want a persistence advisory when a session's declared layers would lapse,
So that silent savings do not silently stop.

**Type:** feature • **Effort:** S • **Deps:** S-46.4 • **FR/AD:** spec-marshal-token-economy CAP-20
**Surface:** the session-path advisory surface (journal + session-close output).
**Given** an interactive session whose `[context]` layers were active
**When** the session ends or the layers lapse
**Then** the journal carries a persistence advisory naming what lapsed
**Status:** backlog

### Story 46.7: The docs name marshal dispatch and spin the execution front door

As an agent choosing how to run a story,
I want AGENTS.md / CLAUDE.md / station skill notes to name `marshal factory
dispatch` / `spin` as the default execution path and bare `bmad-build-auto` as
the sanctioned-but-unmeasured path,
So that the instrumented path is the default and the bare path is a conscious
choice.

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-21
**Surface:** AGENTS.md, CLAUDE.md, and the bmad-build-auto skill note; an
advisory (never gating) doctor detector may flag a bare dispatch.
**Given** an agent reads the repo's entry docs
**When** it chooses an execution path for a story
**Then** the docs point at marshal dispatch/spin as default and explain what the
bare path forgoes (the layers, the journal, the benchmark)
**And** nothing new turns red in CI because of this story
**Status:** backlog

### Story 46.8: The interactive Claude session path is one documented invocation

As an operator starting an interactive Claude session on the shared checkout,
I want the wrap + caveman skill + retrieve/recall discipline written once where
a session actually starts,
So that the convenience path runs on the same instruments as dispatch instead of
re-discovering the repo.

**Type:** docs • **Effort:** S • **Deps:** S-46.7 • **FR/AD:** spec-marshal-token-economy CAP-22
**Surface:** the Claude-facing session docs (CLAUDE.md session-path note) naming
the one invocation; dispatch remains the measured path.
**Given** an operator starts interactive Claude on the shared checkout
**When** they follow the documented path
**Then** the session is demonstrably wrapped or seeded per the declared
`[context]` layers, and wholesale `epics.md` / PRD loads are a miss against
retrieve/recall
**Status:** backlog

### Story 46.9: Benchmark legs run per layer with cache-hit rates

As an operator trusting the savings numbers,
I want `marshal benchmark compare` to run one leg per layer — each leg reporting
prompt-cache hit rate alongside weighted tokens, with the 28.5 equivalence gate
applied per leg,
So that a cache-colliding wire layer shows as worse weighted tokens, unmasked by
other layers' gains, and Claude wire savings become verified instead of
asserted.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-23
**Surface:** `core/token_economy_benchmark.py` leg runner + per-leg artifact
schema (cache-hit rate field).
**Given** a named story and the five layers
**When** the benchmark runs one leg per layer
**Then** each artifact reports weighted tokens, dollars if the catalog is
declared, and cache-hit rate, and a non-identical landing voids that leg only
**Status:** backlog

### Story 46.10: The matrix tells the truth, copilot wrapper, gemini probe, per-currency cells

As an operator reading the multi-harness matrix,
I want the output layer recorded as multi-harness (caveman's 21 targets), a
verified `[wrapper]` in `copilot.toml` (headroom ships `wrap copilot`), and the
Gemini wire seam probed,
So that each harness × layer cell names what is real and its binding currency —
and "never" appears only with evidence.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-token-economy CAP-24
**Surface:** `data/harness_profiles/copilot.toml` `[wrapper]` declaration + one
live copilot dispatch through the wrap; a dated gemini probe finding (env/proxy
seam or upstream headroom target); the matrix doc corrected (output layer is
multi-harness).
**Given** the copilot profile declares a wrapper
**When** a copilot dispatch launches
**Then** `headroom wrap copilot` is on the argv and the run journals the wire
layer — or the profile carries a dated finding and `auto` skips honestly
**And** gemini's wire cell reads "probed, none" with evidence or gains a target
**And** Devin stays the deliberate unverified stub (loud absence)
**Status:** backlog

### Story 46.11: The dispatched Claude session is launched with the instruction-file mode pinned

As a fleet operator dispatching a story to Claude Code,
I want the launch to pass `--settings` pinning the `agents-md` mod to `claude-md-and-agents-md`,
So that nested `AGENTS.md` files (the atlas child) load in every dispatched session regardless of whose machine launched it.

**Type:** feature • **Effort:** XS • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-262 • the dispatch-launch half of scribe Story 19.3 (`spec-pyforge-scribe:CAP-29`); hand-driven 2026-09-20
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml` (`argv` gains `"--settings"` + the inline JSON token — substitution is literal `str.replace`, so the braces are safe), `tests/unit/test_harness_profile.py` (the rendered argv carries the option; `{prompt}` exactly once; wire-wrapped launch unchanged).
**Given** Claude Code 2.1.277's built-in `agents-md` mod reads its `instructionFiles` option from user settings or `--settings`, never the project, and stays out of any project with a `CLAUDE.md` in the default mode
**When** the claude profile's launch argv carries the option inline
**Then** `render_dispatch_argv` yields `--settings` followed by JSON whose `pluginConfigs.agents-md@builtin.options.instructionFiles` is `claude-md-and-agents-md`; `{prompt}` appears exactly once; the wire-wrapped launch keeps the same tokens
**And** an older Claude Code ignores the unknown plugin option and still reads `AGENTS.md` through the import — the pin is harmless below 2.1.277
**Outcome (2026-09-20):** done, hand-driven — see the tracked spec's Auto Run Result.

### Story 46.12: Marshal's shell-outs name the Guild env

As a fleet operator running marshal where only `pyforge-guild` exists,
I want the watch's bmad-loop probes, the gate's verify line and the scribe-CLI fallback to reach their commands through `-e pyforge-guild`,
So that marshal never depends on the recipe factory's 10 GB environment being installed beside it.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-263 • Dream item (11); the env side is steward 63.6
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (`list_runs` / `run_status` argv → `-e pyforge-guild`), `core/gate.py:646` (`platform-ci-local` line), `adapters/scribe_cli.py:77-78` (fallback bin dirs), `tests/unit/test_watch.py` (argv assertions), related gate / scribe-CLI tests.
**Given** `cli/watch.py` shells `pixi run -e local-recipes bmad-loop list|status` although bmad-loop is marshal's own run-dep and present in `pyforge-guild`
**When** every argv names `-e pyforge-guild` and no `.pixi/envs/local-recipes` path remains
**Then** the watch's fake-port tests assert the Guild argv; `grep -rn 'local-recipes' pyforge-marshal/src` finds only prose; steward 63.6's guard lists no marshal offender
**And** `pyforge-marshal-test` green; the live watch on this host still names the running dispatch
**Outcome (2026-09-20):** done, hand-driven in PR #1551 — see the tracked spec's Auto Run Result.

## Epic 47: The review bot remembers the correction you gave two weeks ago (spec-marshal-recall-in-the-loop CAP-1..4)

Minted 2026-09-18 from `spec-marshal-recall-in-the-loop` (`fold-exemption: cross-station-seam` —
sits at the marshal loop-orchestration / scribe memory-ownership seam by design, mirroring
`spec-pyforge-core`'s own precedent; not folded into this station's own `spec-pyforge-marshal`
chain). Named directly from "Towards Self-Driving Codebases" (blog.detail.dev): "the code review
bot needs to be aware of the correction you issued to the agent... two weeks ago." Scribe's
`recall`/`capture` primitive is real and shipped; the gap is propagation, not capture — neither
`bmad-loop`'s dev pass nor its review pass currently queries it before starting.

**Story-minting resolves three of the Spec's four Open Questions, each named below where it
applies** (the fourth — reverse-direction auto-capture from a review finding back into scribe —
stays explicitly out of scope, a separate future capability if pursued, per the Spec's own note).

### Story 47.1: A bmad-loop dev pass automatically receives relevant scribe feedback before it starts

As a fleet operator running an unattended `bmad-loop` story,
I want the dev pass to automatically query `scribe recall` scoped to the story's touched
station/surface before it starts working, and fold any relevant feedback entries into its
starting context,
So that a correction I gave scribe weeks ago reaches this session without me having to remember
to paste it in by hand.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-marshal-recall-in-the-loop CAP-1
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`
(the dev-pass session-launch path gains a pre-launch `scribe recall` subprocess call — CLI only,
never a direct `pyforge.scribe` import, per the Spec's own "scribe stays sole owner" constraint),
a small result-formatting helper turning scribe's `RecallAnswer` into a context-injectable block,
tests.
**Given** a story about to dispatch names a station and a set of touched-surface globs (from its
own Spec's `surface:` frontmatter, the same source `spec-surface-check` already reads)
**When** the dev pass launches
**Then** it first runs `scribe recall --scope <station-slug>` (this story resolves Open Question 1
by reusing the `--scope <slug>` mechanism `scribe-marshal-fact-visibility` CAP-1 already proves,
rather than a narrower per-file-glob scope) and, if the answer is grounded (non-empty), folds it
into the session's starting context as a clearly-labeled block
**And** this story resolves Open Question 2 by scoping v1 to `bmad-loop` dev passes only, matching
the source Dream's own literal text — a `bmad-build-auto` extension is out of scope here, a
separate future story if pursued
**Status:** backlog

### Story 47.2: A bmad-loop review pass sees the same scoped feedback the dev pass saw

As a fleet operator trusting an unattended review pass's verdict,
I want the review pass to receive the same scoped scribe-feedback context Story 47.1's dev pass
got,
So that a correction from a prior session is visible to whoever grades the new work, not just the
agent that wrote it.

**Type:** feature • **Effort:** S • **Deps:** S-47.1 • **FR/AD:** spec-marshal-recall-in-the-loop CAP-2
**Surface:** `harness_bmadloop.py`'s review-pass session-launch path (reuses Story 47.1's
recall-query + formatting helper — one query per story dispatch, shared between dev and review
launch, never a second independent `scribe recall` call).
**Given** Story 47.1's recall query already ran for this story's dispatch
**When** the review pass launches
**Then** it receives the identical formatted context block the dev pass received — same query,
same scope, no re-query
**And** a review verdict that contradicts a known, injected correction is a visible discrepancy in
the review's own output, not a silent miss (the review pass's existing findings-report shape
carries it as a named entry, no new reporting mechanism)
**Status:** backlog

### Story 47.3: The recall-injection layer composes with the existing [context] pipeline

As an operator reading a story's token-economy accounting,
I want Story 47.1/47.2's recall injection to be its own named `[context]` layer in
`marshal-policy.toml`, alongside the existing `wire`/`output`/`structure-graph`/`derived-context`/
`planning-graph` layers,
So that it can be toggled, sized, and measured the same way every other context layer already is
— not a bolted-on mechanism outside that discipline.

**Type:** feature • **Effort:** S • **Deps:** S-47.1 • **FR/AD:** spec-marshal-recall-in-the-loop CAP-3
**Surface:** `core/policy.py` (a new `[context.recall]` block — `enabled` / `aggressiveness`,
same shape as the existing five), `_POLICY_TEMPLATE` in `adapters/harness_bmadloop.py` (the
rendered `policy.toml` comment block gains the sixth layer's docs), tests.
**Given** `[context.recall]` is present in policy.toml with `enabled = true`
**When** a story dispatches
**Then** Story 47.1/47.2's recall query runs; `enabled = false` skips it entirely, with zero
effect on the other five layers' own behavior
**And** this story resolves Open Question 3 by defaulting `aggressiveness = "medium"` — matching
`derived-context`'s own default, the most similar existing layer (also read-only, also a
context-injection concern)
**And** the query and injected-block size are counted toward the story's existing weighted-token
accounting the same way every other layer's output already is — no separate, uncounted budget
**Status:** backlog

### Story 47.4: A genuine recall miss injects nothing, never a fabricated confidence claim

As an operator relying on this layer's honesty,
I want a scoped recall query with no relevant hits to inject nothing into the session's context,
So that the dev/review pass never sees a synthesized "no relevant corrections found" line
presented as if it were a checked fact scribe actually confirmed.

**Type:** feature • **Effort:** S • **Deps:** S-47.1 • **FR/AD:** spec-marshal-recall-in-the-loop CAP-4
**Surface:** Story 47.1's result-formatting helper (the empty-answer branch), tests.
**Given** `scribe recall --scope <station-slug>` returns a grounded miss (`RecallAnswer` with no
citable hit — scribe's own "never invents an uncited answer" behavior, unchanged by this Spec)
**When** the formatting helper processes that result
**Then** the injected context block is empty/absent entirely — no block, no placeholder sentence,
no synthesized "nothing found" confidence claim
**And** a fixture test asserts the empty-hit case produces zero injected text, distinguishing it
from a non-empty hit's formatted block
**Status:** backlog

## Epic 50: The landing self-drives — what the first autonomous drain still needed a human for (spec-pyforge-marshal CAP-244..248)

Minted 2026-09-18 from the station Dream's same-day Realization-log entry (`docs/dreams/pyforge-marshal.md`,
Dream-append-first per `one-chain-per-station`). Herald's Epic 23 was drained to zero today by
`marshal factory dispatch` on the Claude harness — four stories verified, landed and ledger-flipped
without a human in the loop — and every one of the four still needed a human within the hour. Each
story below closes one of the five things that human did, measured on the run journals named in the
Dream entry, not remembered. **Epics 48 and 49 are reserved holes, deliberately skipped:** their keys are
already poisoned on `origin/main` by steward's `Story 48.N:` / `Story 49.N:` direct-commit subjects (the
un-scoped landing-evidence shape Story 50.4 closes), and the standing rule is renumber, never exclude.
The sixth human act — `ledger-regression` reddening a story PR's `detectors` lane after the unattended
merge — is doctor's source and is Story 27.1 on `pyforge-doctor` (`spec-pyforge-doctor:CAP-78`), not re-implemented here.
**HARD boundaries:** the supervisor still observes from outside and never trusts self-report; git stays
the sole authority for merged facts (CAP-247 stops the *parser* inventing a station, it never re-attributes
history); one harness seam; no new gate.

### Story 50.1: A landing never re-dispatches the story it just landed

As a fleet operator running `marshal factory drain --mode drain_to_zero`,
I want the campaign supervisor to treat the window between a dispatch session exiting and
`dispatch_land_finalize` promoting the ledger as still in flight, and to read a session's own
"already merged" refusal as *advance*, not *blocked*,
So that a multi-story drain reaches zero with zero manual relaunches.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-244
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the fleet cycle:
`_live_dispatch_story_keys` / `_station_block_evidence` / `_classify_attempt`), `.../core/dispatch_fleet.py`
(`plan_station_queue`, `classify_fleet_block`, the harness-done advance reason), `.../dispatch_supervisor/__main__.py`
(only if a "session exited, finalize pending" journal fact is needed), tests.
**Given** the campaign cycles every 60 s and, on 2026-09-18, four times in a row saw a story neither live
nor `done` inside the ~45 s between session exit and ledger promotion (`fleet-drain-runs/…151925342Z-82ce96c8`:
`in-flight` 16:19:45Z → `dispatched` 16:20:47Z → `blocked … ended 'failed'` 16:21:47Z, `complete=true`)
**When** a station whose most recent run's supervisor is alive but has not journaled `dispatch-completion`
(or has journaled `dispatch-land` but the tracked ledger has not yet moved) reads as in flight, and a most-recent
run that is a self-refusal of the already-merged kind (zero changed paths, session log names the merged PR /
`done` spec) classifies as an advance reason
**Then** the campaign reports `in-flight` for that cycle and chains the next ready story on the following one,
and a fixture journal replaying the herald sequence completes the campaign with the next story `dispatched`
rather than the same story `blocked`
**And** a genuine failed dispatch with zero changed paths and no merged evidence still blocks exactly as today
(mutation test: removing the advance classification re-blocks the fixture)

### Story 50.2: A harness's own usage-wall wording is a transient outcome

As a fleet operator whose stations run on whichever harness has usage left this week,
I want a session that dies on a harness quota/usage wall to classify `quota_exceeded` from the harness's
*current* wording,
So that the fleet planner retries or re-routes it instead of recording a terminal block that only a human
can clear.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-245
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py` (`_QUOTA_MARKERS`
becomes per-harness and covers Cursor's live text), `.../core/dispatch_retry.py` (no behaviour change expected;
covered by test), tests with the real `pyforge-herald-20260918T132400673Z-194af3a0` session log as a fixture.
**Given** `classify_session_log` returned `unknown` for `ActionRequiredError: Increase limits for faster responses
You're out of usage. Switch to Auto, or ask your admin to increase your limit to continue.` (none of
`monthly spend limit` / `spend limit` / `usage limit` / `rate limit` / `quota exceeded` / `insufficient quota`
match), so `classify_dispatch_block` returned `terminal` and the drain refused 23.1 until a human re-dispatched it
**When** the marker table recognises `out of usage` and `increase your limit` (Cursor) beside the Claude Code
weekly/monthly-limit text already catalogued, keyed per harness in one place
**Then** the fixture classifies `QUOTA_EXCEEDED`, `classify_dispatch_block(session_log=fixture, failed_gate=None,
changed_path_count=0)` returns `TRANSIENT`, and `exclude_harness_profiles_after_transient_failure` drops the
first preference entry for it
**And** removing the new markers re-terminalises the fixture (mutation test), and no existing classification
changes (the current marker fixtures stay green)

### Story 50.3: `--harness` outranks a dead tier-map harness

As a fleet operator passing `--harness claude` because Cursor is out of usage this week,
I want the explicit invocation flag to lead the harness walk over the tier map's inline-table harness for that
dispatch,
So that a station can move on the harness I named without a policy PR first.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-246 • preserves spec-cursor-native-tier-map CAP-1
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the Story 28.11 walk-order
block: tier-map harness leads unless an explicit `--harness` flag names a different profile), `.../core/tier_routing.py`
(`resolve_tier_launch` takes the flag as an exclusion/override), `.../core/dispatch.py::resolve_tier_harness`, tests
with herald's pre-#1458 `marshal-policy.toml` as a fixture.
**Given** on 2026-09-18 `marshal factory drain --station herald --harness claude` launched
`pyforge-herald-20260918T132400673Z-194af3a0` on cursor/grok-4.6 because the station's
`[model_tier_map.medium] dev = { harness = "cursor", … }` led the walk regardless of the flag, cursor's authcheck
passed, and the session died in three seconds
**When** an explicit `--harness` (the composed `harness_preference` flag layer, not the policy layer) is present,
the walk starts from the flag's profiles and a tier-map harness the flag does not name contributes nothing,
and the model is resolved for the harness actually chosen — the tier map's model for that harness when it names
one, else the harness's own default — never a foreign model id
**Then** the launch journal records `harness_profile: claude`, `model: sonnet` for the fixture, and without the flag
the resolution is byte-identical to today's (tier map leads)
**And** the fails-safe guard (`provider_declaring_model` mismatch drops the override) is exercised by a test where
the flag names claude and the tier map names only a Cursor model

### Story 50.4: Landing evidence carries the station in every shape

As a station whose story keys collide with every other station's by construction (eight ledgers, one integer
grammar),
I want no commit-subject shape to mark my story merged unless the subject names my station,
So that a dispatch is never a one-second no-op, a land is never `already_landed` for another station's merge,
and an epic number is never poisoned by a sibling's history.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-247 • extends Story 35.1 (spec-marshal-templated-merge-subject-cross-project-collision CAP-1)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (repo default
`merge_subject_template` → `"Merge {slug}/{key} into main"`, `{slug}` a second placeholder validated beside `{key}`),
`.../core/identity.py` (`render_merge_subject` / `parse_merge_subject` / `_split_template` learn `{slug}`),
`src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`parse_templated_merge_subject` refuses a
foreign slug; `parse_story_direct_commit_subject` requires branch/station corroboration before it counts),
`.../core/promotion.py` (`_classify_merge_subject`), `.../core/dispatch_landing.py::merge_subject_is_marshal_native`,
the eight stations' `marshal-policy.toml` (herald's #1458 override becomes redundant and is removed), tests.
**Given** on 2026-09-18 atlas's seven `Merge 23-N into main` commits marked herald's 23.1/23.2/23.5/23.6
`story_merged_on_main` (doctor's 23.1–23.3 dispatches completed in one second that morning and detached from live
sessions), and steward's `Story 48.2:` / `Story 48.4:` subjects poison marshal 48.2/48.4 today — Story 35.1's
`known_keys` corroboration cannot help when the key exists in both ledgers
**When** the templated shape renders and parses with the station slug and the un-scoped direct-commit shape needs
a station-scoped branch (`<station>/…`, `dispatch/<slug>/…`, `land/<station>-…`) or the recovery allowlist to
corroborate it
**Then** `merged_story_keys` for `pyforge-marshal` against today's `origin/main` no longer contains 48.2/48.4 and for
`pyforge-herald` no longer contains 23.1..23.6 via atlas, while every `done` row of all eight tracked ledgers that
has real landing evidence still classifies (regression fixture: ledgers × `git log origin/main --format=%s`)
**And** live history is never re-attributed: the existing `Merge {key} into main` and `Story N.M:` subjects on
`main` are grandfathered through the SHA/recovery allowlist and branch-scoped shapes only; the new default applies
to landings after this story merges

### Story 50.5: The promoter reads a spec through its banner

As a station whose tracked story specs were recovered or minted with a provenance banner,
I want a tracked spec that begins with an HTML comment to count as a valid, already-promoted spec,
So that `dispatch_land_finalize` never overwrites a reconciled tracked copy with a stale Tier-3 twin.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-248
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::is_valid_spec_text`,
`.../core/spec_surface.py::parse_declared_surface` (shares the "line 1 must be `---`" assumption),
`.../cli/deploy.py::_already_promoted_keys` (covered by test, no behaviour change expected), tests with herald's
pre-#1460 `spec-1-4-…` as a fixture beside its Tier-3 twin.
**Given** on 2026-09-18 herald 23.1's finalize committed `b0b7f3019f marshal: promote 1 story spec(s) to tracked
artifacts` on local `main`, replacing the reconciled tracked `spec-1-4` (2026-08-30 Verification reconcile) with its
stale Tier-3 twin, because the tracked copy began `<!-- Promoted from implementation-artifacts/ … -->` and
`is_valid_spec_text` requires `text.startswith("---")`; PR #1460 moved 45 such banners fleet-wide as the data-side fix
**When** both parsers skip a leading `<!-- … -->` block (possibly multi-line) before looking for the frontmatter fence
**Then** the fixture's tracked copy is valid, `_already_promoted_keys` includes 1.4, `_scan_promotions` yields an empty
`to_promote` for the pair, and `parse_declared_surface` returns the banner-topped spec's `surface:` list
**And** a spec with no frontmatter at all, or an unclosed banner, is still invalid (negative fixtures), and the 45
banner-below-frontmatter files #1460 produced parse identically before and after

## Epic 51: The landing self-drives, second round — what the second autonomous drain still needed a human for (spec-pyforge-marshal CAP-249..256)

Minted 2026-09-19 from the station Dream's "2026-09-18 (later)" Realization-log entry (`docs/dreams/pyforge-marshal.md`,
Dream-append-first per `one-chain-per-station`). With Epic 50 draining under its own fixes, doctor 27.1–27.5, herald
24.1–24.3 and marshal 50.1–50.5 all landed themselves the same day — 17 `marshal factory dispatch` landings on
claude/sonnet — and the next set of human acts is different in kind from the first: a green branch suite that was not a
green merge (50.4 vs doctor 27.5, hand-composed `1a5895317f`), a landing record written into the worktree's Tier-3 twin
that finalize never saw (50.4, promoted by hand in #1488), an operator `git pull` before every campaign cycle, a `blocked`
session landed as `done` (doctor 27.3, PR #1476), a silent MRS-DISP-043, a `marshal watch` reading August's paused loop,
and a mint branch that poisoned a key (`doctor/27-4-mint`, PR #1477). Each story below closes one of them, measured on
the run journals and PRs named in the Dream entry, plus the two banner-parser deferrals 50.5's own review raised
(DW-FU-50-5, DW-FU-50-6 severity high). **Epics 48 and 49 remain reserved holes** (steward's `Story 48.N:` / `Story 49.N:`
subjects, renumber-never-exclude). The eighth human act — `pyforge-core-test` has no CI lane — is `spec-pyforge-core`
CAP-8/CAP-9 and is Epic 52, not re-implemented here.
**HARD boundaries:** the supervisor still observes from outside and never trusts self-report; git stays the sole authority
for merged facts (marshal materialises the merge-tree, never performs the merge); one harness seam; no new gate and no
second verdict owner; the primary checkout is moved only when it is a clean `main`.
**Serial dispatch order (surface-overlap matrix, `cli/dispatch.py` and `dispatch_land.py` are the hubs):**
51.8 → 51.2 → 51.3 (landed hollow; re-minted as 51.9) → 51.6 → 51.9 → 51.1 → 51.4 → 51.5 → 51.7; schedule 51.6 after Epic 52's Story 52.1 has merged (both touch `cli/watch.py` — a merge-order note, not a `Deps:` entry, so `forward-dependency` stays green).

**Closed 2026-09-20.** Thirteen stories minted (51.1–51.13; 51.3 landed hollow and was re-minted as 51.9), all `done`: 51.1–51.9 from the 2026-09-18 (later) entry; 51.10–51.13 from the 2026-09-20 (night) entry, found while draining. Every story landed through `marshal factory dispatch` except 51.10/51.12/51.13 (hand-driven the same night, operator ruling 00:40Z). Residue carried forward, not left behind: `DW-FU-50-4` stays open (51.7's amendment no longer claims it); the retro (`epic-51-retrospective`) is owed.

### Story 51.1: Verification sees the merge result

As a fleet operator whose stations land on shared modules within the same hour,
I want `dispatch land` to verify the tree `main` will actually contain — the merge of the branch onto `origin/main` —
whenever the branch's baseline predates a sibling's landing on overlapping files,
So that a story is never refused at land after a green verify (MRS-DISP-038, PR left open), and never auto-merged into a
runtime break.

**Type:** fix • **Effort:** M • **Deps:** S-51.2 • **FR/AD:** spec-pyforge-marshal CAP-249
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (the hook before `forge.merge_pr`;
the MRS-DISP-038 branch), `.../dispatch_verify.py::evaluate_dispatch_verification` (a merged-tree checkout is another
`worktree` path), `.../ports/vcs.py` + `.../adapters/vcs_git.py` (a `--write-tree` sibling of `merge_tree_conflict_paths`
that materialises the tree), `.../core/dispatch_landing.py` (pure eligibility), `.../dispatch_supervisor/__main__.py`
(`_run_and_journal_landing`, only if a new journal kind is needed), tests.
**Given** on 2026-09-18 marshal 50.4's review pass rewired doctor's `sources/marshal.py` / `sources/ledger.py` 42 min after
doctor 27.5 had rewired the same files past 50.4's baseline — the branch suite was green, land was refused, the operator
hand-composed `1a5895317f`, and the part git *would* have auto-merged called `bare_merge.py` with 2 args against the new
3-arg signature
**When** the branch baseline is behind `origin/main` on any file the branch touches, land materialises
`git merge-tree --write-tree origin/main <head>`, runs the station's own `verify_commands` against that tree, and refuses
with a named finding when it is red — while a conflict-free green merge lands with no operator action
**Then** the 50.4/27.5 fixture refuses with the runtime `TypeError` named in the finding, a fixture with a clean
merge lands, and a branch whose baseline already equals `origin/main` verifies exactly once (byte-identical to today)
**And** removing the merged-tree run lets the 50.4/27.5 fixture land green (mutation test); marshal never performs the merge
and no new gate or verdict owner appears

### Story 51.2: The landing record follows the session's write, not the primary's directory

As a station whose dispatched sessions write their Review Triage Log, Auto Run Result and deferrals into the worktree's
Tier-3 twin,
I want `dispatch_land_finalize` to discover and promote that twin, and a land refused after the PR was opened to journal
the PR it opened,
So that no tracked spec lands `done` with none of its record and no deferral is invisible to the ledger.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-250
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (accepts the
worktree beside `slug`/`key`), `.../dispatch_land.py` (spawns finalize with the worktree; the two REFUSED
`DispatchLandingResult` constructors keep `pr_number` / `marshal_native`), `.../cli/deploy.py::_scan_promotions` /
`_discover_candidates` (a second Tier-3 source: the dispatch worktree's `implementation-artifacts/`, read before
teardown), tests.
**Given** bmad-build-auto wrote 50.4's Review Triage Log, Auto Run Result, `followup_review_recommended: true` and one
deferral to `<worktree>/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-50-4-…md` (tracked spec as
`context:`), flipped only `status:` on the tracked copy, and finalize's scan of the primary's Tier-3 dir found nothing —
promoted by hand (#1488), DW-FU-50-4 ingested by hand; the same landing's `dispatch-land` projection read
`pr_number: null, marshal_native: false` for a refusal that happened after PR #1487 was opened
**When** finalize's promotion scan reads the worktree's Tier-3 dir as a discovery source beside the primary's, and the
REFUSED result carries the PR facts already known at :317
**Then** the 50.4 fixture's tracked spec carries `## Auto Run Result` and its `deferred:` item reaches
`deferred_work_intake.py` with no hand step; a post-open refusal journals `pr_number` and `marshal_native`
**And** the primary-directory promotion path is byte-identical (existing fixtures), and a worktree with no twin promotes
nothing (silence is not a finding)

### Story 51.3: The campaign reads the ledger it just promoted

As a fleet operator running a multi-story drain,
I want the campaign's next cycle to read the ledger finalize just promoted onto `origin/main` without my `git pull`,
So that a drain reaches zero with zero operator commands between landings.

**Type:** fix • **Effort:** S • **Deps:** S-51.2 • **FR/AD:** spec-pyforge-marshal CAP-251
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (post-ledger
refresh step, reusing `cli/land.py::_resync_home_branch`), `.../cli/land.py::_promote_sprint_ledger` (unchanged single
writer onto the remote tip), `.../cli/dispatch.py` (the fleet cycle's ledger read — `station_finalize_pending_story` /
the `ledger_story_statuses(ledger_path)` call — falls back to `origin/main` when the primary is not a clean `main`),
`.../core/dispatch_fleet.py::station_ledger_path`, tests.
**Given** every herald 23.x landing on 2026-09-18 promoted the ledger onto `origin/main` and the campaign kept reading
the primary checkout's stale copy until an operator pulled
**When** finalize fast-forwards the primary only when it is a clean `main` (refusing by name and journaling otherwise —
the checkout may belong to another session) and the campaign otherwise reads the promoted ledger from `origin/main`
**Then** a fixture replaying the herald sequence (ledger promoted remotely, primary one commit behind) reports the
story `done` on the next cycle and chains the next ready story with zero operator commands
**And** a dirty or non-`main` primary is never moved (fixture), `_promote_sprint_ledger` gains no second writer, and a
primary already at `origin/main` is byte-identical
**Outcome (2026-09-19):** landed HOLLOW as PR #1501 (`e7a71df640`) — the dispatched session was terminated at Claude Code's
600 s print-mode background-wait ceiling before its implementation subagent committed anything; the branch's only change was
this spec's `ready → in-progress` flip, which `has_git_progress` counted as progress, so verify (green on an unchanged tree)
and land followed and finalize promoted `done`. Nothing under CAP-251's Surface changed. Re-minted as **Story 51.9**
(identical contract); the truth is on 51.3's tracked spec. `done` never moves (`ledger-regression`).

### Story 51.4: A blocked outcome never lands

As a station whose dispatched session can discover an intent gap and stop — or be killed before it does anything,
I want a session that ends `blocked` (branch reverted to baseline, `status: blocked` written) OR hollow (no changed path
outside the story's own tracked spec — the 51.3 shape: a harness-terminated session whose only commit was the spec's
status flip) to produce no PR, no `done` promotion, and a journal fact carrying its reason,
So that the ledger tells the truth and the story is re-driven or re-minted deliberately instead of read as shipped.

**Type:** fix • **Effort:** M • **Deps:** S-51.1, S-51.9 • **FR/AD:** spec-pyforge-marshal CAP-252 (widened 2026-09-19: a hollow outcome is a blocked outcome)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py`
(`_run_supervisor_finalize_sequence` and the run-loop land trigger read the worktree spec's `status:` before verify/land),
`.../core/dispatch_completion.py::has_git_progress` (a revert-to-baseline plus a status flip is not progress),
`.../core/dispatch_harness_done.py::parse_spec_status` (reused; the pre-launch guard treats `blocked` as not
relaunchable without an operator decision), `.../core/dispatch_landing.py` (a `blocked` verdict), `.../cli/dispatch.py::
station_story_block_facts` + `.../core/dispatch_fleet.py` (the block reason; `NON_IMPLEMENT_STATUSES` already lists
`blocked`), tests.
**Given** doctor 27.3's session found an intent gap, reverted to baseline and set `blocked`; marshal landed the empty
branch (PR #1476) and promoted `27-3 → done` — the truth was written above the Auto Run Result by hand and the story
re-minted as 27.4→27.5
**When** the supervisor's finalize sequence stops before verify and land on a `blocked` spec, journals
`dispatch-blocked` with the spec's own reason, and the campaign records a station block rather than an advance
**Then** the 27.3 fixture (empty diff against baseline + `status: blocked`) and the 51.3 fixture (branch diff = the
tracked spec's frontmatter only, session log ending `Background tasks still running after 600s; terminating`) each
produce no PR and their tracked ledger rows never read `done`; the campaign fact names the reason, and the block classifier
recognises the harness-ceiling wording as `transient` (re-dispatchable), not terminal
**And** an implementation with changed paths lands exactly as today (existing fixtures), and removing the status read
re-lands the 27.3 fixture (mutation test)

### Story 51.5: MRS-DISP-043 speaks for an uncatalogued model

As a fleet operator whose tier map may name a model id no provider declares,
I want the fails-safe guard to fire for a model catalogued under *no* provider, not only under a different one —
while the chosen harness's own default and alias ids stay silent,
So that a genuinely foreign model never reaches a live launch uncaught and no claude dispatch WARNs spuriously.

**Type:** fix • **Effort:** S • **Deps:** S-51.4 • **FR/AD:** spec-pyforge-marshal CAP-253 • closes DW-FU-50-3
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the guard at the
`provider_declaring_model` / `resolved_provider` comparison), `.../core/model_cost.py::provider_declaring_model` (or a
sibling predicate that knows the harness's own default/alias set), `.../core/findings.py` / `.../core/verdict.py` only
if the finding text changes, tests.
**Given** the guard's condition (`model_provider is not None and model_provider != resolved_provider`) only fires when the
model IS found under some OTHER provider, and `provider_declaring_model` returns `None` both for a foreign id and — by
documented design — for `sonnet` / `opus` on claude
**When** the predicate distinguishes "uncatalogued and not the chosen harness's own id" from "the harness's own default"
**Then** a fixture tier map naming an id no provider declares raises MRS-DISP-043 before launch, `sonnet` on claude is
byte-identical (no finding), and the cross-provider case is unchanged
**And** removing the uncatalogued branch silences the fixture (mutation test); no second gate

### Story 51.6: `marshal watch` follows the engine that is actually driving the station

As a fleet operator watching a station that moved from bmad-loop to `factory dispatch`,
I want `marshal watch` to report the run whose journal moved last,
So that a dispatch run journaled today is never hidden behind a loop row paused in August.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-254 • schedule after Story 52.1 lands (shared `cli/watch.py`; a merge-order note, not a dependency)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py::_gather_station` (the
`_LIVE_STATUSES` row wins today; the choice becomes one pure function over the loop row's and the dispatch run's last
journal timestamps), its `WatchPorts` / `_default_ports` (importing `iter_dispatch_run_dirs` /
`gather_dispatch_journal_facts` from `cli/dispatch.py`, not re-implementing them), tests.
**Given** on 2026-09-18 the fleet watch read `dispatch-runs/` journals directly all day because `_gather_station` lets
any `running`/`paused` `bmad-loop list` row win and consults `dispatch_run_id` only when no live row exists
**When** the station's current run is the engine whose last journal fact is most recent
**Then** a fixture with a `paused` loop row from 2026-08 and a dispatch run journaled today reports the dispatch run
(harness, key, phase, last fact); with no dispatch run the loop row is chosen exactly as today; neither reports idle
**And** the choice function is mutation-tested (swapping the comparison re-selects the stale row)

### Story 51.7: Landing evidence is intent-scoped, not just station-scoped

As a station whose planning, mint and fallout branches must be allowed to mention a story key,
I want the dispatch consumers to corroborate a station-branch landing by the tracked spec's `status: done` on `origin/main`
rather than by the branch's name,
So that a branch like `doctor/27-4-mint` can never make a story read landed before its first dispatch, and no real
historical landing loses its evidence.

**Type:** fix • **Effort:** M • **Deps:** S-51.8 • **FR/AD:** spec-pyforge-marshal CAP-255 (refined 2026-09-19 night after run `…-0b70f736` blocked on an intent gap:
corroborate by content, not name; DW-FU-50-4 no longer claimed) •
co-governed by spec-landing-evidence-grammar / spec-pyforge-core
**Surface:** `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`LandingEvidenceMatch` exposes the
branch-derived shape a GitHub PR-merge subject matched through; parsers unchanged — no grammar tightening),
`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` (new `corroborated_merged_story_keys(subjects, template,
slug, *, spec_status_for)` beside the unchanged `merged_story_keys`; a banner-tolerant `spec_status_for` reader over
`origin/main:<planning-artifacts>/specs/spec-<key>-*.md`), the three dispatch consumers `dispatch_supervisor/__main__.py`
(`story_merged_on_main`), `dispatch_land.py` (already-landed check), `dispatch_land_finalize/__main__.py`; tests in both packages
incl. the PR #1477 fixture; `cli/status.py`, `cli/deploy.py`, `cli/land.py` and doctor's `sources/marshal.py` untouched — hand-verify
with `pyforge-core-test` + `pyforge-doctor-test` before land (outside marshal's `verify_commands`).
**Given** on 2026-09-18 doctor Story 27.4 was minted on `doctor/27-4-mint`; when PR #1477 merged, `story_merged_on_main`
read true for 27.4 and its first dispatch completed in one second and detached from a live session (story re-keyed to
27.5, 27.4 a reserved hole)
**When** a station-branch match reached through a GitHub PR-merge subject counts as a landing for the dispatch consumers only
when the key's tracked story spec on `origin/main` reads `status: done` (a mint/fallout/fix PR merges it `ready`/`backlog`; a
landing merges the promoted twin), and the retrospective scanners are unchanged
**Then** on the PR #1477 fixture 27.4 is absent from `promotion.corroborated_merged_story_keys` and present in
`merged_story_keys`, while every `done` row of the eight tracked ledgers with real landing evidence still classifies
retrospectively (the CAP-247 regression fixture extended; the 347-key marshal sweep yields 0 regressions), and a landing whose
tracked spec is not `done` is not corroborated (CAP-252's posture)
**And** live history is never re-attributed; the MRS-GATE scope advisory for `pyforge-core/**` is expected and recorded,
not suppressed

### Story 51.8: The banner-skip family is complete

As a station whose tracked story specs carry a provenance banner,
I want every marshal reader that skips a banner to tolerate leading whitespace or a BOM, and the last banner-blind
sibling reachable through a promoted spec to skip it too,
So that no tracked spec is misread as unpromoted or as `declared_low_risk: false`.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-256 • closes DW-FU-50-6 (severity high)
and DW-FU-50-5
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_skip_leading_banner`,
`.../core/spec_surface.py::_skip_leading_banner`, `.../core/spec_low_risk.py::parse_declared_low_risk` (reached via
`cli/gate.py::_gather_review_depth` → `_find_spec_text`), tests. `spec_difficulty.py` and
`dispatch_harness_done.py` stay untouched (verified unreachable, DW-FU-50-5).
**Given** both `_skip_leading_banner` copies recognise a banner only at literal text offset 0 (a leading blank line, BOM
or space falls through to "no frontmatter" — the failure 50.5 exists to close), and `parse_declared_low_risk` still gates
on `lines[0] == "---"` so a banner-topped spec's `declared_low_risk: true` silently reads `False`
**When** the banner skip tolerates leading whitespace/BOM and `parse_declared_low_risk` skips a banner the same way
**Then** fixtures with a blank line, spaces and a BOM before `<!--` are valid in both parsers, and a banner-topped
`declared_low_risk: true` spec resolves the declared review depth through `cli/gate.py`
**And** a spec with no frontmatter or an unclosed banner is still invalid, the 45 banner-below-frontmatter files parse
identically, and no second parser or gate appears

### Story 51.9: The campaign reads the ledger it just promoted (re-mint of 51.3)

As a fleet operator running a multi-story drain,
I want the campaign's next cycle to read the ledger finalize just promoted onto `origin/main` without my `git pull`,
So that a drain reaches zero with zero operator commands between landings.

**Type:** fix • **Effort:** S • **Deps:** S-51.2 • **FR/AD:** spec-pyforge-marshal CAP-251 • supersedes Story 51.3 (landed hollow: the session was killed at the harness's 600 s print-mode ceiling before its implementation subagent committed anything; see 51.3's tracked spec)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (post-ledger
refresh step, reusing `cli/land.py::_resync_home_branch`), `.../cli/land.py::_promote_sprint_ledger` (unchanged single
writer onto the remote tip), `.../cli/dispatch.py` (the fleet cycle's ledger read — `station_finalize_pending_story` /
the `ledger_story_statuses(ledger_path)` call — falls back to `origin/main` when the primary is not a clean `main`),
`.../core/dispatch_fleet.py::station_ledger_path`, tests.
**Given** every herald 23.x landing on 2026-09-18 promoted the ledger onto `origin/main` and the campaign kept reading
the primary checkout's stale copy until an operator pulled
**When** finalize fast-forwards the primary only when it is a clean `main` (refusing by name and journaling otherwise —
the checkout may belong to another session) and the campaign otherwise reads the promoted ledger from `origin/main`
**Then** a fixture replaying the herald sequence (ledger promoted remotely, primary one commit behind) reports the
story `done` on the next cycle and chains the next ready story with zero operator commands
**And** a dirty or non-`main` primary is never moved (fixture), `_promote_sprint_ledger` gains no second writer, and a
primary already at `origin/main` is byte-identical

### Story 51.10: The watch's marshal-status probe is executable and proven against the real interpreter

As a fleet operator asking `marshal watch --fleet` what is running,
I want the probe that reads each station's marshal home to invoke a module this interpreter can actually execute, proven by a test that runs it,
So that a live dispatch run is never reported as an idle station again.

**Type:** fix • **Effort:** XS • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-257 • realizes the CAP-254 / 51.6 detection that has been dead in production since it landed
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (`_default_ports.marshal_home` — one module-level
constant naming the console script's module `pyforge.marshal.cli.main`, used by the probe), `tests/unit/test_watch.py` (the
fake-probe argv assertions read the constant; a new regression test executes `[sys.executable, "-m", <constant>, "--help"]`
through `pyforge.core.process` and asserts exit 0). Hand-driven, same PR as the mint (operator ruling 2026-09-20 00:40Z:
fix it, don't read journals around it).
**Given** at 2026-09-20 00:38Z `marshal watch --fleet` reported all eight stations idle while doctor 26.1, steward 61.3 and marshal
51.7 dispatch sessions were live, because `python -m pyforge.marshal status …` fails (`pyforge/marshal/__main__.py` does not
exist) and the probe degrades to `None`; `test_default_ports_marshal_home_reads_homes_zero` asserted that exact argv against a fake
**When** the probe names the executable module through one constant and a test runs that module for real
**Then** `marshal watch --fleet` on that fleet names all three runs by `dispatch_run_id`, and the regression test fails on the
old module name and passes on the new one
**And** the probe remains advisory (`ProcessError` / non-JSON → `None`, existing degradation tests unchanged), no second subprocess
implementation appears (spec-pyforge-core CAP-7), and no `pyforge/marshal/__main__.py` is minted to paper over the name
**Outcome (2026-09-20):** done, hand-driven — see the tracked spec's Auto Run Result; the clone-side half became Story 51.12.

### Story 51.11: A session that halts blocked with its verdict uncommitted is a blocked outcome, not an operator stop

As a fleet operator reading a dispatch run's outcome,
I want a session that halts on an intent gap and exits with its blocked spec still uncommitted to be recorded as `dispatch-blocked`,
So that the block, its triage log and its saved attempt survive worktree teardown and show on the fleet picture instead of reading as an operator stop.

**Type:** fix • **Effort:** M • **Deps:** S-51.4, S-51.7 • **FR/AD:** spec-pyforge-marshal CAP-258 • widens CAP-252's blocked detection from committed state to the working tree
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` (the exit classifier: read the
worktree's working-tree copy of the tracked spec via `core/dispatch_harness_done.py::parse_spec_status` before deciding
`external-operator-stop`; on `blocked` commit the spec + any `*-attempted-change*.patch` under the worktree's Tier-3 onto the dispatch
branch, journal `dispatch-blocked`, preserve, complete `blocked`), `core/dispatch_completion.py`, `core/dispatch_landing.py`
(twin promotion of a `blocked` tracked spec), tests with a fixture replaying doctor run `pyforge-doctor-20260919T233255320Z-8f2b958e`.
**Given** doctor 26.1's session reverted its code, wrote `status: blocked` + an Auto Run Result into the tracked spec, saved its patch
to the worktree's Tier-3, and exited without committing; the supervisor saw HEAD `678d409fc3` (two wip commits with real code),
`session_alive: False`, wrote `dispatch-finalize ok:false` and `stop_reason: external-operator-stop`, no `dispatch-blocked` row
**When** the classifier reads the working tree's tracked spec before calling an unexplained exit an operator stop
**Then** the replay fixture yields `dispatch-blocked` (reason: intent gap) + completion verdict `blocked`, a branch commit carrying the
blocked spec and the patch, and the primary's tracked twin at `status: blocked`
**And** a session that dies with a clean working tree and no terminal spec status still reads `stopped_externally`; marshal 51.7's
committed-halt path is byte-identical; the supervisor reads files, `git status` and the process — never the session's own output

### Story 51.12: A dispatch-only checkout still has fleet rows

As a fleet operator running one station per clone,
I want `marshal status` — and so `marshal watch` — to report a station whose Tier-3 in this checkout carries a dispatch run even when no `loop/<slug>` worktree exists here,
So that a live dispatch session in a dispatch-only clone is never reported as an absent or idle station.

**Type:** fix • **Effort:** S • **Deps:** S-51.10 • **FR/AD:** spec-pyforge-marshal CAP-259 • the second half of the 2026-09-20 watch finding: with the probe fixed (51.10) the marshal and steward clones still returned `homes: []`
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (`run_status`'s fleet sweep gains `_dispatch_only_slugs(repo_root)`
— every `_bmad-output/projects/<slug>/` with a dispatch run, via `cli/dispatch.py::latest_dispatch_run_dir`; a station not already in the
loop-home fleet gets a `(slug, None)` entry, a `FleetHomeFacts(slug, branch="loop/<slug>")` placeholder — the Spec's "home with no run
yet" row — and the existing `_merge_dispatch_overlay`; `_gather_failed_patches` is skipped for a `None` home), `tests/unit/test_status.py`
(`TestDispatchOnlyCheckoutRows`). Hand-driven in the 51.10 PR.
**Given** at 2026-09-20 00:47Z, with the 51.10 probe fix installed, `marshal status --project pyforge-marshal --format json` from `lr-m50`
returned `homes: []` while marshal 51.7's dispatch session ran, because the fleet is built only from `loop/`-prefixed git worktrees
**When** the sweep also admits stations discovered from this checkout's own Tier-3 dispatch runs, as placeholder rows the overlay fills
**Then** the same command names run `pyforge-marshal-20260919T235245280Z-a215d473` with state `running`; the unit fixture (no worktrees,
one Tier-3 run) yields one row carrying `dispatch_run_id`
**And** a loop-home station is never duplicated by its own Tier-3 run, `--project` scopes the new rows, a checkout without
`_bmad-output/projects/` yields none, and no second directory convention is introduced
**Outcome (2026-09-20):** done, hand-driven in the 51.10 PR — see the tracked spec's Auto Run Result.

### Story 51.13: The watch reads the dispatch verdict in the supervisor's own vocabulary

As a fleet operator reading `marshal watch`,
I want a running dispatch to read `running`, and only a completed, failed or externally-stopped one to read `finished`,
So that the watch's state column is the supervisor's verdict and not a second, invented vocabulary.

**Type:** fix • **Effort:** XS • **Deps:** S-51.10 • **FR/AD:** spec-pyforge-marshal CAP-260 • found the moment 51.10 made the probe return data
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (`_snapshot_dispatch`'s `finished` predicate reads
`core/dispatch_completion.py::DispatchSessionVerdict` — finished iff the verdict is a member other than `LIVE`), `tests/unit/test_watch.py`
(dispatch-snapshot tests rewritten in the real vocabulary; a meta-test refuses any `dispatch_completion_verdict` literal that is not an enum member). Hand-driven.
**Given** at 2026-09-20 01:25Z doctor 26.1's two-minute-old dispatch (`marshal status`: state `running`, `dispatch_completion_verdict: live`,
`current_story: 26.1`) read `finished` in `marshal watch --fleet`, because `_snapshot_dispatch` treated any verdict outside `{"", "None", "pending",
"in-progress"}` as terminal
**When** the predicate is the enum: `live` (and absent/empty/unknown) is not finished; `completed`, `failed`, `stopped_externally` are
**Then** the same row snapshots as status `running`, `finished: false`; the three live fleet runs read `running`
**And** no watch test names a verdict outside `DispatchSessionVerdict`; `_session_completions` / `_currently_running` keep their reporting shape
**Outcome (2026-09-20):** done, hand-driven — see the tracked spec's Auto Run Result.

## Epic 52: The shared floor is enforced where the build happens (spec-pyforge-core CAP-8..9)

Minted 2026-09-19 from the marshal Dream's "2026-09-18 (later)" item (8) — routed to `spec-pyforge-core` (hosted here, as
Epic 14 was; its own Dream is archived into the marshal Dream). `pixi run --frozen -e pyforge-core pyforge-core-test` is
red on `main` today: 6 failed / 1855 passed, all CAP-5/CAP-7 conformance violations that accumulated between 09-07 and
09-15 and surfaced only because 50.4's hand-merge was verified on that suite. The Dream's causal claim is corrected in
the Spec: #1086's retirement of `pyforge-core.yml` was coverage-neutral — that lane and `pyforge-pip-install.yml` run the
same enumerated subset, and `tests/meta/*_sole_ownership.py` were never wired into any workflow. **HARD boundaries:** the
lane runs the pixi task, never a hand-enumerated file list; 52.1 lands before 52.2 (a gate born red is a gate nobody
trusts); 52.1 is hand-driven, not dispatched — half its files are warden/testing-kit, outside marshal's dispatch surface.

### Story 52.1: The six accumulated violations are cleared

As the fleet's shared floor,
I want the six CAP-5/CAP-7 violations on `main` cleared the way CAP-5 and CAP-6 prescribe,
So that the conformance suite is green before its CI lane exists.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-core CAP-9 (realizes CAP-5, CAP-6)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py`, `.../cli/watch.py`,
`src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (exception root — re-parent to the core root,
no `except` clause widens); `.../marshal/cli/login.py`, `.../marshal/cli/refresh.py` (route through the core subprocess
guard); `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py` (cleared as CAP-6's
recorded, tested opt-out — a file-level entry in the guard's `_EXEMPT_RELATIVE_PATHS` pinned to the kit's Q-26
`dependencies == []`; the kit is outside spec-pyforge-core's scope per its Non-goals until Q2 — corrected at review
2026-09-19); tests.
**Given** `test_exception_root_sole_ownership` fails for the three exception files and
`test_no_second_subprocess_implementation` for the three subprocess files (2026-09-19)
**When** each is brought under the extracted primitive
**Then** `pixi run --frozen -e pyforge-core pyforge-core-test` → 0 failed, and `pyforge-marshal-test`,
`pyforge-warden-test` and the testing-kit suite stay green
**And** the CAP-5 widening test passes for every re-parented class
**Outcome (2026-09-19):** landed hand-driven (bmad-build-auto: four review layers + one follow-up pass, 32 findings
triaged); `pyforge-core-test` 6 failed → 0 failed (1863 passed); the kit's file cleared as CAP-6's recorded opt-out with a
premise pin, CAP-9's success text corrected accordingly. The tracked story spec carries the full record.

### Story 52.2: The conformance suite is a PR gate

As the fleet's shared floor,
I want `pyforge-core-test` — the whole `tests/` tree, meta-tests included — to run on every PR that touches
`src/shared/packages/**` and inside `pr-preflight`,
So that a CAP-5/CAP-7 violation reds the PR that introduces it instead of accumulating on `main`.

**Type:** infra • **Effort:** S • **Deps:** S-52.1 • **FR/AD:** spec-pyforge-core CAP-8 (realizes CAP-7's "fails the build")
**Surface:** `.github/workflows/pyforge-station-tests.yml` (a `core-test` job beside the eight station jobs, same
shared-surface triggers, running `pixi run --frozen -e pyforge-core pyforge-core-test`), `pixi.toml`
(`pr-preflight` depends on `pyforge-core-test`; `environment.yaml` regenerated), docs that list the lanes.
**Given** no workflow invokes the `pyforge-core-test` task and the four sole-ownership meta-tests have never run in CI
**When** the job exists and `pr-preflight` depends on it
**Then** the lane is green on `main` at merge, and a fixture branch introducing a second `subprocess.run` implementation
under `src/shared/packages/` reds it
**And** the job runs the pixi task — no hand-enumerated file list
**Outcome (2026-09-19):** landed hand-driven (bmad-build-auto, four review layers, 20 findings triaged); `core-test`
job + `core` filter output, the core leg first in `pyforge-station-tests`, a structural meta-test pinning the wiring
(`test_conformance_lane_wired.py`, filesystem-derived roster), docs corrected; fixture proof exit 1 → exit 0 recorded on
the tracked spec. Epic 52 done.

## Epic 53: The dispatch landing pays its own surface tax (spec-pyforge-marshal CAP-261)

Minted 2026-09-20 (morning) from the station Dream's entry of the same name (operator ruling 08:40Z after seven
autonomous landings in twelve hours each left `main` red on `spec-surface` until a human named the paths — "we need a
permanent fix, it's causing churn and rerun"). A new epic because Epic 51 is `done` (a done key never moves). The cause is
mechanical: bmad-loop pays the tax through the S-13.7 guard `harness_bmadloop::render_policy_toml` appends to every loop's
verify commands (CAP-239); `marshal factory dispatch` never got it — `dispatch_verify` runs only the station's
`verify_commands`, the `harness_bmadbuild` prompt says nothing about memlogs, and nothing in the dispatch path runs
`deferred_work_intake`. **HARD boundaries:** never a bare `--write-baseline`; never a stamp for a Spec whose drift includes
files the branch did not change; the loop path stays byte-identical; no new gate or verdict owner; the supervisor never
trusts a self-report — the reconcile is derived from `git diff`.

### Story 53.1: The dispatched session is told and gated like a loop session

As a fleet operator dispatching a story,
I want the session to be told it must name every governed path it changes (and cite a repo path on every deferral), and to have the S-13.7 surface guard in its own verification,
So that the producer pays the surface tax the way a bmad-loop session already does, and a session that forgets fails its own verification instead of landing red.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-marshal CAP-261 (a) • extends CAP-239 to dispatch
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` (the prompt: the obligation, the
co-governor rule, never `--write-baseline`, `location:` on every `deferred:` entry), `dispatch_verify.py` / `cli/dispatch.py` (the guard
`python scripts/spec_surface_reconcile.py` appended to the effective verify commands at render — derived, mirroring
`harness_bmadloop._SURFACE_RECONCILE_COMMAND`, never declared per project), `core/gate.py::check_spec_binding` (the derived guard is implicit:
a tracked spec that lists only the station's own `verify_commands` still binds), tests.
**Given** on 2026-09-20 every dispatched session (26.1, 61.3, 51.11, 29.1, 61.4, 46.7) left its governed paths unnamed because nothing
told it to and nothing checked
**When** the prompt carries the obligation and the guard runs inside the session's verification
**Then** a session that changes governed files and names them passes; one that does not fails its own verification with the guard's
verdict naming the paths; `check_spec_binding` returns `()` for every existing pre-authored spec unchanged; the loop adapter's rendered
policy is byte-identical
**And** a `deferred:` entry the session writes without `location:` is called out by the prompt's rule and, when it still appears, is
reported by the guard's output, never silently

### Story 53.2: The landing reconciles from git facts and runs intake

As a fleet operator,
I want `dispatch_land` to name the branch's changed governed paths on the owning Spec and every co-governor from `git diff`, stamp exactly those Specs, and finalize to run intake — journaling that it had to,
So that `main` is never red after an autonomous landing and no landing waits on a human, without ever laundering foreign drift.

**Type:** feature • **Effort:** M • **Deps:** S-53.1 • **FR/AD:** spec-pyforge-marshal CAP-261 (b)
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (after verify, before `forge.merge_pr`: the spec-surface
verdict over the branch's changed paths via `pyforge.doctor.sources.chain::gather_spec_surface`; per-Spec classification own-drift vs foreign;
the memlog events through `_bmad/scripts/memlog.py append`; scoped stamps through `scripts/spec_surface_check.py --write-baseline --spec`
for exactly those Specs; a commit on the dispatch branch; `MRS-DISP-047` warn / `MRS-DISP-048` refusal in `core/findings.py`),
`dispatch_land_finalize/__main__.py` (`scripts/deferred_work_intake.py --fix --project <station>`, refusals journaled), tests with the
2026-09-20 fixture (six landings' changed paths, their owning Specs and co-governors), doctor's `sources/chain.py` untouched.
**Given** the six 2026-09-20 landings and their fallout PRs (#1533, #1537, #1544, #1546) — every reconcile a human wrote was
"Story X landed: <paths>" on the owner plus the co-governors the detector named
**When** `dispatch_land` derives that entry from `git diff`, stamps only Specs whose drift is this branch's files, and merges
**Then** on the fixture every path is named on the right Specs and `spec-surface` is green on the merged tree; a branch sharing a Spec
with foreign drift is refused with `MRS-DISP-048` naming the foreign paths; a session that reconciled itself produces no entry and no
finding; `MRS-DISP-047` is journaled whenever the landing had to name paths
**And** finalize ingests the run's deferrals and journals any refusal; never a bare `--write-baseline`; the loop path is untouched
**Outcome (2026-09-20):** landed as PR #1554 (`51bf3e10d1`, `Merge pyforge-marshal/53-2 into main`) after the fleet reformat was merged in and three deferrals ingested (DW-FU-53-2/-2/-3); the touched-module coverage floor found `dispatch_supervisor/__main__` at 35% — landed behind a dated per-module exception (Story 53.3 retires it); tracked spec carries the triage log and Auto Run Result. Ledger row promoted by hand: the session wrote its tracked spec directly, so `dispatch_land_finalize` found no Tier-3 twin to promote from.

### Story 53.3: The supervisor entrypoint reaches the floor

As the operator who landed 53.2 behind a dated exception,
I want `dispatch_supervisor/__main__.py` unit-covered to the 80% floor and the exception removed,
So that Epic 53 closes with no named debt and the touched-module gate is whole again for marshal.

**Type:** chore • **Effort:** L • **Deps:** S-53.2 • **FR/AD:** spec-pyforge-marshal CAP-264 • Dream 2026-09-20 (evening); operator ruling at the 53.2 landing
**Surface:** `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_*.py` (ports-driven tests of the finalize / halt / land / completion sequences — the 388 uncovered statements), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml` (the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry removed), no production change unless a test proves a defect.
**Given** the module sits at 35% behind a dated, story-bound exception the 53.2 landing added
**When** this story lands
**Then** `pyforge-marshal-coverage-gate` reports the module ≥ 80% and its OK line names no exception for marshal; `pyforge-marshal-test` green
**And** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` green

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch→epics` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this epics. `updated:` bumped to record that the
check ran.*
