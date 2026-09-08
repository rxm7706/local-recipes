---
name: sprint-change-proposal-2026-08-21
type: sprint-change-proposal
status: approved
created: '2026-08-21'
scope: spec-python-agent-platform Epics 10-12 (pyforge-steward)
---

# Sprint Change Proposal — 2026-08-21

## 1. Issue Summary

**Trigger story:** 11-2 (DB-GPT joins as a pluggable app), spec-python-agent-platform, pyforge-steward.

**Category:** Technical limitation discovered during implementation.

**Problem statement:** Story 11-2's spec assumed DB-GPT integrates via Pattern A (ASGI-mounted
Django app, per `docs/dreams/db-gpt-django-plugin.md`) in the SAME `python-agent-platform` pixi
environment already carrying `langflow-base` (Story 11.1, done). `dbgpt-app` — the package
needed for DB-GPT's FastAPI mount, including the AgenticData text-to-SQL router — pins
`fastapi<0.113.0`. `langflow-base` requires `fastapi>=0.135.0`. The ranges are disjoint; no
`fastapi` version satisfies both.

**Evidence:** verified live by adding `dbgpt-app>=0.8.1` to `pixi.toml` and running
`pixi install -e platform-dev`, which fails to solve with exactly this conflict. Confirmed
against both `dbgpt-app`'s conda-forge metadata and DB-GPT's own upstream `pyproject.toml`
(both the `v0.8.1` tag and unreleased `main`).

**Resolution already recorded:** per pap:AD-14 ("sidecar fallback only on demonstrated
pluggability failure, Dream first"), DB-GPT moves to `db-gpt-django-plugin`'s existing
**Pattern B** (Celery + `docker-compose.yml`-managed microservice) for this integration.
Dated in `docs/dreams/db-gpt-django-plugin.md` + `docs/dreams/python-agent-platform.md`
Realization logs, PR #573 (merged 2026-08-21). Operator is filing the `fastapi` ceiling
conflict upstream with `eosphoros-ai/DB-GPT` by hand — not an action item here.

**What THIS proposal adds:** the operator directs that pattern selection (A vs. B) become a
first-class, per-engine **configuration switch** — not a hardcoded DB-GPT-specific fork —
reusable by future engine integrations, and letting DB-GPT revert to Pattern A later (once
the upstream conflict resolves) as a config change, not a rewrite. That's an architecture-level
addition, which is why this is a correct-course pass rather than a direct spec tweak.

## 2. Impact Analysis

### Epic impact

- **Epic 11 (`the host mounts its first plugin`, in progress, 1/4 stories done):** 11-2, 11-3,
  11-4 cannot proceed as originally specced — all three assumed Pattern-A in-process mounting.
  **Modification needed**, not removal: re-scope around the config-driven pattern-selection
  seam, with DB-GPT selecting Pattern B through it. 11-1 (Langflow, done) is unaffected and
  stays on Pattern A — no rework, no rollback.
- **Epic 10 (`python-agent-platform — the host takes root`, done, 4/4 stories):**
  - **Story 10.2 (One factory-sourced environment) — NOT impacted.** Its scope named
    `langflow`, `dbgpt`, `dbgpt-serve` — never `dbgpt-app`. The conflict is specific to
    `dbgpt-app`, which under Pattern B never enters the shared `python-agent-platform`
    environment at all (it lives in its own sidecar image). 10.2's "solves reproducibly"
    claim holds for what it actually shipped; no rollback needed.
  - **Story 10.3 (One image, both engines) — impacted, needs an ADDITION, not a rollback.**
    Its "both engines, one image" framing is no longer accurate for DB-GPT once DB-GPT is a
    separate sidecar. The existing image (host + Langflow) remains correct as-is. A new,
    additive scope item is needed: a DB-GPT sidecar image + `docker-compose.yml` wiring.
- **Epic 12 (Deploy anywhere, not started, 0/3 stories):** 12.1/12.3 currently frame
  deployment around "the platform image" (singular). Once Epic 11 lands, they'll need to
  additionally cover deploying/parity-testing the DB-GPT sidecar alongside it. Flagged for
  awareness — no story text changes proposed yet since Epic 12 hasn't started and its stories
  aren't blocked by this; revisit at Epic 12 kickoff.
- **No epics become obsolete. No new epic needed** — contained to an Epic 10 addition + Epic
  11 re-scoping.

### Artifact conflicts

- **SPEC.md (CAP-3 — "DB-GPT joins as a pluggable app"):** intent currently assumes Pattern A
  universally. Needs rewording to describe pattern selection as configurable; CAP-3's actual
  goal (DB-GPT usable from the platform) is unchanged and still fully achievable.
- **ARCHITECTURE-SPINE.md (status: final, AD-1..AD-16):** needs a new **AD-17** formalizing the
  config-driven, per-engine pattern-selection seam, plus updates to the "Consumed by" table for
  11.2/11.3/11.4 (and 10.3's extension). This is the one genuinely new piece of architecture.
- **Dream files:** already updated (PR #573) — no further action.
- **deferred-work-ledger.md:** worth a short note that the original Pattern-A groundwork for
  11-2 (Django app scaffold + schema migration, preserved on
  `backup/steward-11-2-blocked-adf57ec5`) is superseded, not abandoned-by-accident — so it
  isn't rediscovered later and mistaken for lost work needing recovery.
- **test-architecture.md:** 11.4's proof-suite design (schema isolation, container-replacement
  simulation) still conceptually holds — Pattern B's Dream constraint keeps DB-GPT's state in
  the shared PostgreSQL's `dbgpt_schema` regardless of pattern — but "container-replacement
  simulation" now targets the sidecar container specifically and needs a
  `docker-compose`-driven harness, not an in-process assumption.
- **PRD / UI-UX:** no impact — this station has no UI/UX spec for this effort, and the
  station-level PRD (`prds/prd-pyforge-steward-2026-07-25/prd.md`) predates and doesn't scope
  this specific effort; `spec-python-agent-platform`'s SPEC.md is the operative contract here.

## 3. Recommended Approach

**Option 1 — Direct Adjustment (RECOMMENDED).** Modify 11-2/11-3/11-4's specs, add AD-17, add
one new story for the sidecar image. Effort: **Medium** — 11-2's ASGI-dispatcher design is
discarded, but the schema-migration and settings-wiring groundwork already built (preserved on
the backup branch) is pattern-agnostic per the Dream's storage-rule constraint and is largely
reusable. Risk: **Medium** — first real use of Pattern B and of the config-switch mechanism in
this codebase, but well-precedented by the Dream's own pre-written Pattern B design.

**Option 2 — Rollback: not applicable.** Nothing landed for 11-2 (correctly reverted, never
merged). 10.3 doesn't need reverting, only extending.

**Option 3 — MVP review: not needed.** CAP-3's goal is unchanged and still achievable; no MVP
scope reduction required.

**Selected: Option 1**, with the 10.3 impact handled as an **addition** (new Story 10.5), not
an edit to a shipped, done story — rewriting an already-merged story's acceptance criteria
would misrepresent what was actually built and verified.

## 4. Detailed Change Proposals

**New — pap:AD-17 (ARCHITECTURE-SPINE.md):** "Engine integration pattern (A vs. B) is a per-engine
configuration switch, not a hardcoded fork." A named config seam (e.g. a
`PLATFORM_ENGINE_PATTERN` registry/setting keyed per engine) that the ASGI dispatcher and
Celery routing consult to decide whether an engine is in-process-mounted (Pattern A) or
sidecar-dispatched (Pattern B) — switching an engine's pattern is a config change, never a
code fork. Consumed by: 11.2, 11.3, 11.4, 10.5 (new).

**Story 11.2 — DB-GPT joins as a pluggable app (re-scope):**
```
OLD: Given the dbgpt_integration app, Then a Django data migration provisions dbgpt_schema
(...); the dispatcher routes /api/dbgpt/ (stripped); (...) a text-to-SQL round-trip succeeds
through the mount.

NEW: Given the dbgpt_integration app configured for Pattern B (AD-17), Then a Django data
migration provisions dbgpt_schema (Django ORM never crosses in; DB-GPT's Alembic never
touches public) exactly as before; the sidecar (docker-compose-managed, its own FastAPI/AWEL
process) is registered in the AD-17 pattern registry as dbgpt: B; requests route to it via
the Celery/Redis path (11.3) rather than an in-process ASGI mount; DBGPT_SESSION_STORAGE_TYPE
=db plus disabled local paths still apply inside the sidecar; a text-to-SQL round-trip
succeeds end-to-end through the sidecar.

Rationale: dbgpt-app cannot co-install with langflow-base (fastapi conflict); Pattern B
avoids the conflict entirely by never installing dbgpt-app into the shared environment.
```

**Story 11.3 — Async work never blocks Django (re-scope):**
```
OLD: Given Celery over Redis, Then LLM/AWEL work dispatches to workers that call the engines
internally (never through the public edge) (...)

NEW: Given Celery over Redis, Then LLM/AWEL work dispatches to workers that call each engine
per its AD-17 pattern — Pattern-A engines in-process, Pattern-B engines (DB-GPT) via a REST
call to the sidecar's AWEL endpoint (never through the public edge) — the host stays
responsive under a long-running agent task, and the new failure mode (timeout / partial
result, now including a sidecar-unreachable case) is named and handled.

Rationale: 11.3 already dispatches through Celery/Redis, which is exactly Pattern B's own
transport — this re-scope is additive (a routing branch), not a redesign.
```

**Story 11.4 — Isolation and statelessness proven (re-scope):**
```
OLD: (...) a container-replacement simulation (kill + fresh start) loses no flow, no session,
no state (...)

NEW: (...) a container-replacement simulation covers BOTH the in-process Pattern-A case
(existing) and the Pattern-B sidecar case (kill + restart the docker-compose service) —
neither loses a flow, session, or state, proven against the shared dbgpt_schema.

Rationale: the isolation proof must cover whichever pattern an engine actually runs under,
not assume Pattern A universally.
```

**New — Story 10.5: The DB-GPT sidecar image + docker-compose wiring:**
```
Type: infra • Effort: M • Deps: S-10.3, S-11.2 • FR/AD: spec-python-agent-platform CAP-6, AD-17
Surface: src/platform/compose/dbgpt/, platform CI

Given DB-GPT's Pattern-B deviation (AD-14, dated in db-gpt-django-plugin.md), Then a
docker-compose service builds and runs DB-GPT as its own container (model worker + API
server), rootless-clean under the same Docker∩Podman intersection discipline as Story 10.3's
image, wired into the local-dev tiers (AD-16) and CI so 11.2's sidecar integration is
testable end-to-end without a manual DB-GPT setup step.

Rationale: 10.3 shipped "one image, both engines" before this deviation existed; this is the
additive counterpart for the engine that no longer fits that image, not a correction to 10.3.
```

**No changes proposed to:** 10.1, 10.2, 10.4, 11.1 (all done, unaffected), Epic 12 (not
started, revisit at kickoff), PRD, UX.

## 5. Implementation Handoff

**Scope classification: Moderate** — backlog reorganization (3 stories re-scoped, 1 new story,
1 new AD) but no PRD/MVP replan; CAP-3's goal is unchanged.

**Routed to:** Developer agent (`bmad-dev-auto`, same pattern already in use for this station's
unattended story work) — once this proposal is approved and the artifact edits below land.

**Action items on approval:**
1. Add AD-17 to `ARCHITECTURE-SPINE.md`; update its "Consumed by" table.
2. Update CAP-3 in `SPEC.md` to describe configurable pattern selection.
3. Re-scope 11-2/11-3/11-4 in `epics.md` per the diffs above.
4. Add Story 10.5 to `epics.md`; add its ledger entry (`backlog`).
5. Note the superseded Pattern-A groundwork in `deferred-work-ledger.md`.
6. Re-launch unattended implementation starting at 11-2 (now Pattern-B-scoped), sequenced
   after 10.5 if built first, or interleaved if 10.5 rides in parallel (no story-level
   dependency prevents that — 10.5 needs S-10.3 done, which it is).

**Success criteria:** 11-2 lands a working DB-GPT sidecar integration verified end-to-end
(text-to-SQL round-trip through the sidecar), 11-3/11-4 extend cleanly onto the same seam,
and the AD-17 config switch is exercised by at least one real pattern flip in review (proving
it's genuinely a config change, not vaporware).
