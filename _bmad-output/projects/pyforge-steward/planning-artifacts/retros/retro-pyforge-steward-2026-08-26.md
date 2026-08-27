---
title: "pyforge-steward — retrospective, Epics 5–37 (the Canopy era)"
created: "2026-08-26"
updated: "2026-08-26"
scope: "Everything since retro-steward-2026-08-08.md: Epics 5–37, 113 stories, 159 commits on src/shared/packages/pyforge-steward + src/platform (2026-08-08 → 2026-08-26)"
---

# pyforge-steward — Retrospective (2026-08-26)

**Scope:** everything since the 2026-08-08 whole-build retro, which covered Epics 1–4
(the four-duty v1 CLI). This one covers Epics 5–37 — the station going from "a shipped
CLI" to the owner of the Unifying Strategy: the Canopy host, the Lane 1 front door, the
governed-DDL path, and the query-plane through-line. Evidence base:
`git log --oneline --since=2026-08-08 -- src/shared/packages/pyforge-steward src/platform`
(159 commits), the sprint ledger (37/37 epics, 131/131 stories `done` as of this date),
the strategy pack (`specs/spec-pyforge-unifying-strategy/` + companions), and the CRC
verification records
(`spec-12-1-…-verification-2026-08-25.md`, `sprint-change-proposal-2026-08-26-*.md`).

> Format note: solo / AI-driven effort (bmad-loop runs + single-story `bmad-build-auto`
> dispatches under the fleet's one-story-in-flight-per-station discipline); substance run
> faithfully, no fabricated dialogue.

## Delivery snapshot — the arc in five movements

1. **The seams and the backlog truth (08-09 → 08-13).** Epic 5 ratified the Marshal seam
   (5.2: consume the sprint ledger, never derive status). Epic 6 shipped `provision
   --module` — the market research's top-ranked growth vector, landed as a backend, not a
   state file. Epic 8 shipped the Jira ↔ GitHub Projects sync (8.1–8.7: bidirectional,
   zero-loop, idempotent, fail-loud-fail-alone). Epic 9 built the secure-live-dashboard
   pattern (9.1–9.7), whose perimeter/static verbs joined `deploy` without breaking AD-8.
   A backlog-truth audit (08-10) held 21 done-claims and produced 9 findings — verification
   before narrative, the standing house style.
2. **The host takes root (08-13 → 08-15).** Epic 10 rendered the Django host into
   `src/platform/` on one factory-sourced `python-agent-platform` env and one image
   carrying both engines; Epic 11 mounted Langflow and DB-GPT as pluggable apps on
   isolated schemas with Celery keeping async work off Django.
3. **Deploy anywhere, run repeatably (08-15 → 08-23).** Epic 12: vanilla Helm chart +
   OCP overlay, GKE portability, air-gap parity as a *failing* check, hardened Redis.
   Epics 13–15: multi-repo workspaces, the repeatable BMAD-core upgrade
   (pre-flight → deliberate apply → clobber detection → fan-out enumeration →
   prove-landed), and the bmad-suite channel as a governed product. Epic 16 earned the
   15 factors — pixi as sole dependency authority, two-stage startup refusals,
   structlog + OTel, policy-as-a-test-suite, and OIDC-delegated identity via Keycloak
   (16.5, no local passwords). Epic 17 closed the loop at the other end: a fresh machine
   reaches `validate-fast` through steward verbs alone.
4. **The Canopy drain (08-24 → 08-25).** The strategy chain's Epics 18–30 landed in two
   days: `django-pyforge` chrome + RS256 identity client + role-filtered switcher (18);
   eight portal shells under `/stations/<name>/` with the Warden rename and the
   `/compliance/` permanent redirect (19); Wagtail Lane 1 publishing without a deploy and
   the redis-broker/redis-cache split (20); supervisor tables in `public`, atlas MCP on
   the host ASGI with the dual-era `mcp` 2.0 SDK, `start`/`get` disconnect survival, the
   other seven MCP faces, and the front door querying the supervisor instead of anyone's
   home directory (21 — CAP-17 exactly as ruled); `pyforge` dispatch (22); row isolation
   (23); CloudEvents on redis-broker with depth-8 cascade halt (24); contained failure —
   async circuit wrapper, one `atlas.duckdb` writer, inline 422 rendering, restart
   reconciliation (25); revocation-on-next-request, secret references only, OpenFeature
   FILE flags flipping three surfaces without a redeploy (26); governed DDL — the
   Liquibase pre-upgrade Job, the DML-only app role, the stale-extraction CI gate, and
   the test-database carve-out (27); Scribe's plane-backed store + semantic recall (28);
   the SKF skill, grammar-and-MCP-only personas, and the five-tier check (29); and the
   console retirement (30) — parity homes first (30.1), then the deletion of the
   Guildhall generator and its 100+ inbound references (30.2).
5. **Closeout and the evergreen turn (08-26).** Attended CRC follow-through: `platform_app`
   provably DML-only (`CREATE` on `public` refused), Liquibase `:17`–`:19` executed,
   sidecar Ready, MCP host 2.x faces isolated from Langflow's `mcp<2` pin, Lane 1 `/`
   published **200** from PostgreSQL — and the Canopy SPEC stamped shipped. The same day:
   CAP-19 minted and its first slice shipped (Epic 34 read-only live attach, Kedro-written
   Parquet cache on a *named* pipeline, vectors on the plane, agents off OLTP, Scribe
   recall on the plane; Epic 36 Lane 3 BSL/Vizro over the `estate-cache` page), Epic 35.1
   made the cluster chart refuse a missing mcp-host (sibling `spec-mcp-era-isolation`
   CAP-4), and Epic 37.1 declared the eight-station roster five-tier complete (40/40;
   mason's skill cell is `conda-forge-expert`).

## What held

- **AD-1 ("wrap, never reimplement") and AD-7/AD-8 scaled by ~3× without bending.** The
  four-duty spine now dispatches ~12 duty adapters (`sync`, `workspace`, `upgrade`,
  `suite`/`suite_advance`, `bootstrap`, `deploy_profiles`, `five_tier`, `fresh_clone`,
  `dashboard/` joined the original four); `cli.main()` is still the only place an exit
  code is born, and no duty calls `sys.exit`. The v1 conventions were the cheap part of
  scaling; nothing about them needed re-litigating.
- **The factory/platform import boundary never broke.** `src/platform/` consumes
  published packages and imports no `pyforge.*` source — held across 20+ Canopy stories,
  enforced as a rule, verified at convergence.
- **Parity before removal.** CAP-2's retirement discipline worked exactly as the
  constraint demanded: `console-parity-inventory.md` (23 surfaces → 4 decisions) landed
  *before* 30.2 deleted anything, CAP-17 turned the three live-run-state surfaces into a
  supervisor rather than a loss, and the Kedro-Viz tree — explicitly not a parity
  obligation — survived the deletion untouched. The replacement is held to a higher bar
  than the thing it replaced (live queries vs. a committed snapshot), knowingly.
- **Enforcement moved from convention to substrate wherever the chain touched it.**
  DDL is refused by database privilege, not by review (CAP-9, proven live on CRC);
  portal access dies at the IdP on the next request (26.1); a missing five-tier cell or
  a stale `sqlmigrate` extraction fails CI (29.3/37.1, 27.3); an absent mcp-host fails
  `helm template` (35.1). The 08-08 retro praised invariant *tests*; this period's
  pattern is invariant *infrastructure*.
- **Research-before-build kept paying.** The 2026-08-24 research wave (MCP runtime,
  Liquibase currency, air-gap delivery, the strategy fan-out) redirected four directives
  before any code was written against them: BS-2's deprecated SSE transport became the
  `start`/`get` pair on the durable store, RFC-5's literal form became role-revocation +
  `migrate --fake` + the test-DB carve-out, CodeRed was dropped on maintenance evidence,
  and the `fastmcp`/`mcp` 2.0 incompatibility was found *before* it shipped as a Canopy
  outage — the host faces went straight to the official SDK, dual-era.

## What was harder than expected / worth remembering

- **The operator-ruling cadence was the real schedule.** Ten rulings dated 2026-08-24
  (supersede-not-coexist, build-the-supervisor, five-tier scoping, hook-spec/plugin
  shape, the CloudEvents envelope) plus the 2026-08-26 CAP-19 answers (both faces one
  boot script; named new pipeline; dual-write for Scribe) each unblocked whole epic
  groups. The chain moved at the speed decisions were made, not the speed code was
  written — worth designing for explicitly next time rather than discovering.
- **Live-cluster verification kept finding what fixtures could not.** CRC failed on
  `schema "liquibase" does not exist` (`liquibaseSchemaName` does not create it — now
  constraint text), needed the `:17`–`:19` contrib/Wagtail changesets, and left the
  isolated `mfa` sqlmigrate fake. Every one of these was invisible to the green local
  suite. The attended-CRC pass (12-7, then the 08-26 follow-through) earns its place in
  any future chain of this shape.
- **Pin metadata is a failure surface of its own.** The `fastmcp` 2.14.x line only
  *appeared* `mcp`-2.0-compatible because of a missing upper bound; Langflow's `mcp<2`
  pin had to be actively isolated from the host's 2.x faces (cb87d8c3). "The solver
  accepted it" is not evidence of compatibility.
- **Same-version packaging currency is a standing tax.** The Django `>=5.2.15,<6` pin
  sits on exactly one qualifying conda-forge build, seven CVEs behind upstream —
  audited unreachable (2026-08-24), but scanners key on version strings, so the
  reachability memo gets rewritten monthly until the feedstock's `5.x` branch is bumped.
  A currency gap left open converts into recurring analyst work.

## Strategy convergence

Steward *is* the Unifying Strategy's owner and this period made that literal: the Canopy
host, chrome, Lane 1 front door, portals, MCP faces, events, flags, governed DDL, the
five-tier gate, and now the CAP-19 through-line (atlas owns the engine; steward owns the
through-line) all live on this station's ledger. The convergence discipline held in both
directions — nothing re-minted `spec-python-agent-platform` CAP-1..6, Epic 35 stayed
correctly attributed to `spec-mcp-era-isolation`, peer stations drained on one CAP-18
process-hook story each rather than cloning Epics 18–30, and the Dream/SPEC pair is
explicitly evergreen: CAP-1..18 closeout is a dated slice, not the end of the contract.

## Rule-2 / conda-forge posture (stated, not skipped)

This period's packaging touchpoints — the OpenFeature four + `cachebox` 5.x (26.3) and
Liquibase ≥5.0.4 (27.1) — were **operator-owned feedstock work** per canopy AD-16; the
station's stories pinned and consumed, they did not author recipes, so no CFE-skill retro
is owed *by this retro*. The feedstock efforts themselves carry their own Rule-2
obligations where they were executed. (Recorded explicitly per the repo rule that a retro
states this rather than silently omitting it.)

## Open items (tracked, none blocking)

1. **Budget's spend meter** (market research OQ1) — `budget check` still exits
   `EXIT_BUDGET_NOT_CONFIGURED`; GitHub Actions billing vs. Anthropic usage remains the
   unmade pick, and the unified container is the first credible admission point.
2. **Runner reaping** (market research OQ3) — provision-not-reap is still implicit.
3. **Isolated `mfa` sqlmigrate stays fake** — the one RFC-5 leftover, recorded on the
   closeout proposal.
4. **MCP Tasks extension** — scheduled re-check, not a closed door; the `start`/`get`
   pair was built so adoption is a wire-layer swap. MCP slice 3 and optional 12.9 CI
   remain parked.
5. **Django pin → `>=5.2.17,<6`** once the feedstock's `5.x` branch publishes it
   (one-file bump; this maintainer authored the 5.2.15 one).
6. **Scribe dual-write** — the plane is primary; `scribe_schema` pgvector stays the
   safety net until the plane has operating history, then retirement is its own decision.
7. **Q5 scorecard** — parked under the sibling `build-league-scorecard` Dream; CRC PVC
   sizes stay hostpath-odd.

## Readiness

37/37 epics, 131/131 stories `done`; the strategy SPEC's open questions are empty; the
eight stations are declared five-tier complete with CI refusing regression. The station's
build phase is closed *as a dated slice* — the Dream/SPEC pair is evergreen and CAP-19
rebuild work is sanctioned to reopen it. This retro clears the `code→retro` currency edge
for everything through 2026-08-26.
