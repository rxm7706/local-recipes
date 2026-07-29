---
doc_type: sprint-change-proposal
project: pyforge-atlas
date: 2026-07-27
trigger: independent Round-3 code audit (PR #131, branch fix/code-audit-remediation-2026-07-26)
scope_classification: Moderate
status: awaiting-approval
---

# Sprint Change Proposal — post-audit truth-up of the Spec kernel

## 1. Issue Summary

An independent spec-to-code recon audit, run under a different model and landed as **PR #131**
(`fix/code-audit-remediation-2026-07-26`), produced 49 `AUD-ATLAS-*` findings. Nine are
spec/AD-level; the rest are code. PR #131 already remediated most of them against the artifacts
that existed when it ran.

**The gap this proposal closes:** on 2026-07-27 the pyforge-atlas Spec kernel
(`specs/spec-pyforge-atlas/SPEC.md`) and four new peer companions were authored — *after* the
audit executed. PR #131 touches **neither the kernel nor the companions** (verified: zero files
matching `spec-pyforge-atlas/` in its file list). Because the kernel was distilled from the same
PRD / spine / epics the audit found drifted, **it inherited the same overclaims** — and in one
case restated a false safety property more confidently than the source did.

Every finding below was **independently re-verified against live code on `main`** before being
accepted. One was refuted.

### Evidence

| Finding | Verdict | Evidence gathered |
|---|---|---|
| **AUD-ATLAS-046** run admission | **CONFIRMED — severe** | `conf/base/dagster.yml` declares only the `in_process` executor, which serializes ops *within* one run and provides **no** cross-run or cross-process admission. Yet `orchestration/definitions.py:26` asserts "run admission serializes per dataset set," and SPEC § Constraints ("One execution plane") escalates it to "a concurrent trigger of an already-running pipeline is rejected or queued, never interleaved." No lock, queue, or admission code exists in `mcp/session.py` or anywhere in the package. |
| **AUD-ATLAS-047** retirement | CONFIRMED | Legacy `conda_forge_atlas.py` is still live at 402 KB. SPEC § Success signal claims "parity recorded and signed before the legacy orchestrator retired." |
| **AUD-ATLAS-041** 28 pages | CONFIRMED | `dashboard/app.py` ships **8** `PageDef` entries. SPEC CAP-8 claims "every read-only question the 28 CLIs answered is answerable from a dashboard page." |
| **AUD-ATLAS-049** F1 benchmark | CONFIRMED | `tests/singularity/test_duckdb_sole_engine.py:17` states the benchmark is the attended half. SPEC frontmatter says `status: shipped` unqualified. |
| **AUD-ATLAS-048** catalog count | CONFIRMED | Live catalog = **86** entries (pinned by `EXPECTED_TOTAL`); `spec-a2` and `spec-b6` still cite 73. |
| **AUD-ATLAS-043/044** AD-17 | CONFIRMED | `mcp/tools.py::read_dataset` returns coerced rows with no envelope; `build_stamp` in `dashboard/app.py` reaches only `_factory_status_page`. **Already fixed in PR #131.** |
| **AUD-ATLAS-042** empty contracts | **REFUTED** | `validation.py:45–49` already documents the empty `DEFAULT_CONTRACTS` registry as deliberate ("F2 delivers the machinery + seam, not speculative contracts"). The drift is confined to ARCHITECTURE-SPINE AD-9 wording, which PR #131 fixes. **No kernel change required.** |
| **AUD-ATLAS-045** frontmatter | **DECIDED BY OPERATOR** | PR #131 sets all 32 story specs to `status: shipped` YAML. 12 are verbatim recovered originals with no frontmatter. Operator chose **uniform frontmatter on all 32** (2026-07-27). |

**Cross-confirmation:** PR #131 independently adds `DW-AD23-1` with the evidence line "no
lock/queue in `pyforge.atlas.mcp.session`; `dagster.yml` has no admission policy" — reached
separately from this verification pass. Two independent reviews converging on the same
mechanism is the strongest signal in this proposal.

## 2. Impact Analysis

### Epic impact

Epics 1–9 are **complete and unaffected**. No completed epic becomes invalid; no story is
rolled back. The work is additive: one new epic captures post-audit truth-up plus the one real
code gap.

- 2.1 Current epics completable as planned — **yes**, all 9 already shipped.
- 2.2 Epic-level change — **add** Epic 10; modify none.
- 2.3/2.4 Future epics — none planned; no obsolescence.
- 2.5 Resequencing — not applicable.

### Artifact conflicts

| Artifact | Conflict | Owner |
|---|---|---|
| `specs/spec-pyforge-atlas/SPEC.md` | CAP-8 (28 pages), Constraint "One execution plane" (false admission claim), § Success signal (retirement), `status: shipped` scope | **This change** |
| `specs/spec-pyforge-atlas/gate-contract.md` | Attended-events table lists the benchmark; must not read as delivered | **This change** |
| `planning-artifacts/README.md` | Documents "two spec shapes are deliberate" — contradicted by the operator's 045 decision | **This change** |
| `specs/spec-a2*.md`, `specs/spec-b6*.md` | 73 vs live 86 | This change (or adopt PR #131) |
| all 32 `specs/spec-<story>.md` | uniform `status: shipped` frontmatter | Adopt PR #131 + extend to the 12 |
| `ARCHITECTURE-SPINE.md` AD-9 / AD-23 | demotions | **Adopt PR #131** |
| `deferred-work-ledger.md` | `DW-AD23-1` | **Adopt PR #131** (merge with local 52-entry alias correction) |
| `mcp/tools.py`, `dashboard/app.py` | AD-17 envelope + page stamps | **Adopt PR #131** |
| `orchestration/definitions.py:26` | comment asserts admission that does not exist | **This change** (1-line) |

UI/UX artifacts: **N/A** — no UX spec in this project.

Secondary artifacts (3.4): no CI/CD, IaC, or deployment change. Testing strategy gains one gate
if run admission is implemented (Epic 10 story I4).

### Technical impact

Only **AUD-ATLAS-046** implies real missing code. Everything else is documentation truth-up or
already-landed code in PR #131. The severity is not that concurrency is broken today — the
shipped default is a single operator on one machine — but that **the Spec promises a safety
property a reader may design against.** A future agent adding a second trigger path would
reasonably assume serialization exists.

## 3. Recommended Approach

**Option 1 — Direct Adjustment. Viable. Selected.**
Effort **Low–Medium**, risk **Low**. Add one epic; amend the kernel and companions; adopt
PR #131 for everything it already covers. No timeline impact — the project is shipped.

**Option 2 — Rollback. Not viable.** Nothing is wrong with the delivered code that reverting
would simplify. The audit found drift *between* artifacts and code, not defective code.

**Option 3 — PRD MVP review. Not viable / unnecessary.** The MVP shipped. FR-1…FR-22 are
unaffected; the corrections are to claims *about* delivery, not to requirements.

**Rationale.** The cheapest honest fix is to make the documents match the code, and to track
the single genuine gap as deferred work with a seeded story. Re-opening scope for a
concurrency feature nobody has hit in practice would be the wrong trade — but silently leaving
a false safety claim in the contract is also wrong. Demote-and-track resolves both.

## 4. Detailed Change Proposals

### 4.1 SPEC kernel — Constraint "One execution plane" (AUD-ATLAS-046)

**OLD**
> A dataset has **one writing run at a time**: run admission serializes on the target dataset
> set, so a concurrent trigger of an already-running pipeline is rejected or queued, never
> interleaved.

**NEW**
> **Run admission is not implemented.** The `in_process` executor serializes ops *within* a
> run; it provides no cross-run or cross-process admission. Two concurrent triggers of the same
> dataset set — an MCP trigger racing a CLI run, or two MCP triggers — are **not** serialized,
> rejected, or queued. The shipped guarantee is the shared Kedro plane and identical machinery,
> **not** single-writer safety. Tracked as `DW-AD23-1`; do not design against a serialization
> guarantee that does not exist.

*Rationale:* the strongest correction in this proposal. A false safety claim is worse than a
missing feature, because it is invisible until something corrupts.

### 4.2 SPEC kernel — CAP-8 (AUD-ATLAS-041)

**OLD** — "every read-only question the 28 CLIs answered is answerable from a dashboard page"
**NEW** — "**8 pages ship** (the live-confirmed core) plus factory-status; the full 28-CLI page
inventory is CIS-two-spine deferred (`DW-D2-1`). Pages are honest about their state: grounded,
BSL-wired shell, or no-BSL-model shell."

*Rationale:* the D2 story spec already documents the honest 3-kind taxonomy; the kernel
over-promised relative to its own story.

### 4.3 SPEC kernel — § Success signal (AUD-ATLAS-047, AUD-ATLAS-049)

**OLD** — "parity recorded and signed before the legacy orchestrator retired"
**NEW** — "parity harness delivered and fixture-green; the **credentialed parity run, operator
sign-off, and legacy retirement have not occurred** — `conda_forge_atlas.py` remains live
(`DW-B4-2`). The F1 cold/warm benchmark is likewise undelivered (`DW-F1-1`); the
DuckDB-singularity half shipped."

Plus a `shipped_scope_note` in frontmatter: `status: shipped` means **the 32 stories merged**,
not that every attended boundary event has been discharged.

### 4.4 `gate-contract.md` — attended events

Amend the attended-boundary table so the three rows read as **outstanding**, not as completed
ceremony. Add: *"None of these three has occurred as of 2026-07-27."*

### 4.5 `planning-artifacts/README.md` — reverse the 045 guidance

**OLD** — "The two spec shapes are deliberate… Normalizing the 12 would mean editing recovered
originals, which costs more in provenance than it buys in uniformity."
**NEW** — all 32 carry `status: shipped` YAML frontmatter per operator decision 2026-07-27; the
12 recovered originals retain their `<!-- RECOVERED -->` banner and verbatim body **below** the
added frontmatter, and each notes that frontmatter was added post-recovery.

*Rationale:* the operator chose uniformity; the README must not contradict the tree.

### 4.6 Code — `orchestration/definitions.py:26` (1 line)

**OLD** — "so run admission serializes per dataset set."
**NEW** — "The `in_process` executor serializes ops within a run; it is **not** cross-run
admission (`DW-AD23-1`)."

### 4.7 Adopt from PR #131 (no re-implementation)

ARCHITECTURE-SPINE AD-9 + AD-23 demotions · `DW-AD23-1` ledger entry · story-spec `status` +
`audit_note` lines · `mcp/tools.py` AD-17 envelope · `dashboard/app.py` per-page stamps · the
73→86 corrections. **Merge, do not duplicate.**

## 5. Implementation Handoff

**Scope classification: Moderate** — backlog reorganization (one new epic) plus a code story.

### New Epic 10 — Wave I: post-audit truth-up

| Story | Title | Type | Gate |
|---|---|---|---|
| **I1** | Kernel + companion truth-up (046 / 041 / 047 / 049) | docs | manual read-back; no claim without code backing |
| **I2** | Uniform story-spec frontmatter, all 32 + README reversal (045, 048) | docs | all 32 parse; 12 banners intact |
| **I3** | Reconcile with PR #131 — adopt spine, ledger, AD-17 code; resolve the 21-file overlap | merge | `kedro-test` green; no lost Implementation notes |
| **I4** | **Run admission / single-writer** (SEED-ATLAS-046, `DW-AD23-1`) | **code** | new gate: concurrent second writer rejected or queued; re-promote AD-23 only on proof |

I1–I3 are Developer-agent direct implementation. **I4 is the bmad-loop story** — real
concurrency code with a new deterministic gate.

### Success criteria

1. No claim survives in SPEC or companions that live code does not back.
2. `DW-AD23-1` is the single tracked home for the admission gap.
3. PR #131's work is adopted, not re-done, and none of the 2026-07-27 Implementation notes are
   lost in the merge.
4. AD-23 is re-promoted in the spine **only** after I4 ships a passing gate.

### Sequencing

I3 (reconcile) **before** I1/I2 to avoid editing files twice. I4 last and independent.
