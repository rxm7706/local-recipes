---
title: Sprint Change Proposal — red-team HIGH set (Epics 41–43)
date: 2026-09-02
project: pyforge-steward
chain: spec-pyforge-unifying-strategy
status: approved — operator 2026-09-02: "approve steward Epics 40 through 43 and Mason Epic 13"
trigger: Red-team architecture review (research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md) — directives R-3 … R-16 (HIGH + the DR CRITICAL); R-17 … R-25 to the deferred-work ledger
mode: batch
scope: moderate
operator: Rxm7706
supersedes_none: true
follows: sprint-change-proposal-2026-09-02-red-team-critical.md
---

# Sprint Change Proposal — red-team HIGH set (Epics 41–43)

## 1. Issue summary

The first 2026-09-02 correct-course minted Epic 40 for the two exploitable
CRITICALs. This one binds the rest of the review: one remaining CRITICAL (no
disaster recovery, R-3) and thirteen HIGH directives (R-4 … R-16), grouped by
delivery seam so they can drain as a fleet rather than as fourteen unrelated
tickets. The nine MEDIUM/LOW directives (R-17 … R-25) become deferred-work
ledger entries with steward as owner; they are promoted to stories only when a
HIGH story needs them or a consumer exists.

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | None; trigger is the review file. Root causes span shipped Epics 10–12 (chart, Celery), 19–24 (chrome, events, MCP), 34 (plane), and the Dream itself. |
| 1.2 | Problem type | Done | Mixed: *technical limitations* (DuckDB over RWX, Celery 300 s, Python 3.12 image), *misread requirements* (CAP-8 "poison" only meant unparseable; CAP-11 separation ≠ durability), *missing architecture* (DR, API versioning, CD, rate limits). |
| 1.3 | Evidence | Done | Review § 2 tables with file:line citations; § 3 twelve failure walkthroughs. |
| 2.1 | Current epics completable | Done | Epics 18–40 unchanged; nothing reopened. |
| 2.2 | Epic-level change | Done | **Add Epics 41, 42, 43.** Grouping: data safety / agent-and-bus containment / contracts-and-document. |
| 2.3 | Remaining epics | Done | 39.4 unaffected. 42.x depend on 40.x (auth root, bounded broker). 43.3 depends on 43.2. |
| 2.4 | New epics needed | Done | Three. No epic for R-17 … R-25 (ledger entries). |
| 2.5 | Order | Done | 40 → 41 → 42 → 43. All before cutover Phase 1. Inside an epic stories are parallel-safe unless `Deps` says otherwise. |
| 3.1 | PRD | Done | No FR text changes. FR-20/26/27/28/29/30/31 each gain a story that carries their consequence to code. PRD § 14 dated paragraph. |
| 3.2 | Architecture | Done | No AD changed. 43.5 will **add** one AD (interpreter topology). 42.5's role prefixes refine AD-15's "roles re-read from token"; 43.2 refines AD-7's client rule; both recorded in the SPEC Constraints block rather than by editing the spine now. |
| 3.3 | UI/UX | N/A | 43.2's `PydanticFormErrorBridge` is a portal error pattern, already specified as BS-7. |
| 3.4 | Other artifacts | Action-needed | Chart (41.1, 42.1, 42.3, 42.4, 43.4), settings (41.4, 42.4, 43.3), workflows (43.4), Dream (43.1, 43.5, 41.2), changelog (41.3), `pyforge-core` + testing-kit (43.2). All named per story. |
| 4.1 | Direct adjustment | Viable | Fourteen stories, effort S–L, risk **Medium** (42.1, 42.4 and 43.2 change behavior on hot paths; each carries a fail-without/pass-with test). |
| 4.2 | Rollback | Not viable | Nothing to revert. |
| 4.3 | MVP review | Not viable | Scope is unchanged; production-readiness is. |
| 4.4 | Path | Done | **Direct Adjustment**, operator-chosen ("run step 2"). |
| 6.3 | Approval | Done | Operator 2026-09-02: "approve steward Epics 40 through 43 and Mason Epic 13" (covers the § 7 amendment: 43.6 and Mason 13.1 / 13.2). |
| 6.4 | Ledger | Done | Fourteen story keys `backlog`; `epic-41/42/43` `backlog`; retrospectives `optional`; `# stories: 224`. |

## 3. Recommended approach

**Direct Adjustment, scope moderate.** Three epics, fourteen stories, all
`ready-for-dev`. Dispatch by epic in order; within an epic run stories in
parallel except where `Deps` names a predecessor.

| Epic | Stories | Directives | Depends on |
|---|---|---|---|
| **41 Data safety** | 41.1 DR + backup · 41.2 plane process boundary · 41.3 Scribe DDL in the changelog · 41.4 verified broker TLS | R-3, R-11, R-12, R-14 | none |
| **42 Agent and bus containment** | 42.1 MCP transport auth + streaming proxy · 42.2 rate limits + run bounds · 42.3 bus delivery semantics + deployed consumer · 42.4 Celery hardening + builds pool · 42.5 role namespaces + tenant claim | R-7, R-8, R-9, R-10, R-13 | Epic 40 |
| **43 Contracts and the document** | 43.1 split the Dream · 43.2 station API contract · 43.3 in-process port · 43.4 CD by digest · 43.5 one interpreter story | R-4, R-5, R-6, R-15, R-16 | 43.3 → 43.2 |

**Why this grouping.** Each epic can be verified as a unit: 41 by a restore
drill plus policy tests; 42 by a runaway-agent chaos test that now degrades
gracefully; 43 by a reader who can implement from the living Dream alone.

**Effort / risk.** Roughly 4 × M for 41, 5 × M for 42, S+L+M+M+S for 43.
Risk Medium, concentrated in 42.1 (auth on a hot path), 42.4 (queue routing),
43.2 (router change). Each names its fail-without test.

## 4. Detailed change proposals

- **Stories (new):** fourteen tracked specs `specs/spec-41-*.md`, `spec-42-*.md`,
  `spec-43-*.md`, each with intent, ACs, Always/Block-If/Never, tasks,
  verification, and the review ids it closes.
- **Epics:** Epics 41–43 appended to `epics.md` before the currency notes.
- **SPEC:** `### Correct-course 2026-09-02 — red-team HIGH set` block appended to
  Constraints: one Always/Never pair per story. Intent and success clauses
  untouched.
- **Deferred-work ledger:** `DW-RT-2026-09-02-1..9` for R-17 … R-25, owner steward,
  status open, promotion rule stated.
- **Dream:** Grounding bullet extended; Realization entry (later 2026-09-02).
- **PRD § 14:** dated paragraph.
- **Review report:** disposition line updated.
- **Ledger:** fourteen keys + three epics.

## 5. Implementation handoff

**Scope: Moderate** (backlog reorganization: three new epics with a stated
order). Route to Product Owner / Developer.

| Role | Responsibility |
|---|---|
| Operator (Rxm7706) | Yes/no per epic; confirm the order 40 → 41 → 42 → 43; decide 43.5's interpreter option (a/b/c). |
| Steward (owner) | Chart, settings, workflows, changelog, DR contract; owns every DW-RT entry. |
| Mason | 43.5 option (a) feedstock work if chosen; 42.4 builds pool consumer. |
| Atlas | 41.2 writer declaration; 43.5 option (b) if chosen. |
| Scribe | 41.3 driver assert-only path. |
| Doctor | 43.1 hygiene finding; 42.3 consumer for `remedy.requested`. |
| Developer agent (`bmad-build`) | One story per session; `BMAD_ACTIVE_PROJECT=pyforge-steward`; physical paths; ledger via `sprint-ledger-sync`. |
| Warden | PR gate as usual; no second verdict. |

**Success criteria.** Each story's fail-without/pass-with test exists; per
epic: a restore drill passes (41), a runaway-agent chaos test degrades to 429
and the broker stays under `maxmemory` (42), a fresh reader implements a
station route from the living Dream + SPEC alone (43). Then cutover Phase 1
may start.

## 6. Applied

- `specs/spec-41-1 … 43-5` (fourteen files, `ready-for-dev`)
- `epics.md` Epics 41–43
- `sprint-status-ledger.yaml` (14 story keys, 3 epics, 3 retrospectives)
- `spec-pyforge-unifying-strategy/SPEC.md` Constraints block
- `deferred-work-ledger.md` DW-RT-2026-09-02-1..9
- `docs/dreams/pyforge-unifying-strategy.md` Grounding + Realization
- PRD § 14
- `implementation-readiness-report-2026-09-02-red-team-high.md`
- Review report disposition

## 7. Amendment 2026-09-02 — 43.5 decided: hybrid (a)+(c); Story 43.6 and Mason Epic 13 added

**Evidence (real `pixi lock` probes, linux-64, conda-forge + SelfExplainML):**

| Probe | Result |
|---|---|
| `python-agent-platform` feature minus langflow (52 pins) on `3.14.*` | solves clean |
| `+ langflow >=1.11.4` | blocked only by `onnxruntime >=1.20,<1.24` (no `cp314` < 1.25.1); `bcrypt ==4.0.1` only on the older `_0` build (steward 10.4 already loosened it; lock holds 4.3.0) |
| `+ dbgpt-app` | blocked only by `dbgpt-client` → `sqlalchemy >=2.0.25,<2.0.29` (no `cp314`; lock holds 2.0.52) |
| upstream `langflow-base` 1.12.0 | `requires_python <3.15,>=3.10`; onnxruntime split by `python_version` marker — a `noarch` collapse, not a real cap |

**Ruling.** (a) raise via feedstock work **and** (c) keep `mcp-host` — because
`langflow-base` pins `mcp >=1.28,<2.0` while host faces need `mcp` 2.x. The sidecar
isolates the MCP SDK major, not the interpreter; the review's S-5 / R-16 wording is
corrected. (b) dropped.

**Applied.** `spec-43-5` rewritten (decision + AD + matrix; docs only, deps none);
new `spec-43-6-platform-image-moves-to-python-3-14` (deps mason 13.1, 13.2, 43.5);
Mason **Epic 13** (13.1 langflow-base onnxruntime, 13.2 dbgpt-client sqlalchemy) minted
at `_bmad-output/projects/pyforge-mason/` under Rule 1; steward `DW-FU-10-4` bound to
Mason 13.1; SPEC 43.5 line, Dream "Python floor" bullet, review S-5 / R-16, readiness
addendum updated; ledgers: steward `43-6` backlog (225 stories), mason `13-1`, `13-2`,
`epic-13` backlog.
