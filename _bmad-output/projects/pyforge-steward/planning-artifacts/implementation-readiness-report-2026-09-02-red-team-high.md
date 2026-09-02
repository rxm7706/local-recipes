# Steward — red-team HIGH set readiness (2026-09-02)

Gate of `spec-pyforge-unifying-strategy` Epics 41–43 after the second
2026-09-02 correct-course bound review directives R-3 … R-16 as fourteen
stories and R-17 … R-25 as deferred-work entries.

**Question:** could a developer implement each story without inventing
decisions?

**Verdict: CONCERNS — proceed for Epics 41 and 42; 43.5 needs one operator
decision before dispatch.**

## Concerns (do not invent; do not block the rest)

| Concern | Where | Why it does not block |
|---|---|---|
| 43.5 needs the operator to pick interpreter option (a) raise langflow/dbgpt, (b) lower Atlas/Doctor floors, (c) formalize two interpreters | `spec-43-5-one-interpreter-story.md` | The story records the decision and mints the follow-on; dispatch it last in Epic 43 |
| 42.x assume Epic 40 shipped (verified mint root; bounded broker) | `Deps` lines | Order 40 → 42 is stated; do not dispatch 42.x on a red 40 |
| 41.1 backup destination defaults to RWX PVC; object store is a profile plugin | `spec-41-1` | RWX exists already for media (AD-13); object store stays optional |
| 42.4 changes queue names; any Celery caller with a hard-coded queue breaks | `spec-42-4` | Routing table lives in chrome; grep for `queue=` is a task |
| 43.2 moves Langflow off bare `/api/v1` | `spec-43-2` | `/langflow/api/v1/` already works; the prefix-preserving redirect test exists |
| The two detectors that fail on `main` (`chain-completeness` CAP-6, steward layers staleness) still fail | detectors | Pre-existing; not a gate for these stories. Worth a doctor ticket: 40.1 cites CAP-6 in its FR/AD line and the detector does not count it |
| Fourteen drafts carry no operator approval yet | SCP § 2 item 6.3 | Yes/no per epic owed before `bmad-build` |

## Trace

| Intent | Story |
|---|---|
| R-3 DR contract + backup | 41.1 |
| R-11 plane process boundary | 41.2 |
| R-12 Scribe DDL governed | 41.3 |
| R-14 broker TLS verified | 41.4 |
| R-7 MCP transport auth + streaming proxy | 42.1 |
| R-8 rate limits + run bounds | 42.2 |
| R-9 bus delivery semantics + consumer | 42.3 |
| R-10 Celery hardening + builds pool | 42.4 |
| R-13 role namespaces + tenant | 42.5 |
| R-4 split the Dream | 43.1 |
| R-5 station API contract | 43.2 |
| R-6 in-process port | 43.3 |
| R-15 CD by digest | 43.4 |
| R-16 one interpreter story | 43.5 |
| R-17 … R-25 | `DW-RT-2026-09-02-1..9` |

## Dispatch order

1. Epic 40 (40.1 then 40.2) — from the first correct-course.
2. Epic 41: 41.1, 41.2, 41.3, 41.4 in parallel.
3. Epic 42: 42.1, 42.2, 42.3, 42.4, 42.5 in parallel after 40 is `done`.
4. Epic 43: 43.1, 43.2, 43.4 in parallel; 43.3 after 43.2; 43.5 after the operator decision.

`BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical paths only. Cutover Phase 1
waits for all four epics.
