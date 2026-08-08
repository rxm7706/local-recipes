---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/ (cli.py, progress.py, claims.py, notices.py, state.py, registry.py, deck_pipeline.py, evidence.py, watch.py, auth.py, transport/)'
  - 'src/shared/packages/pyforge-herald/web/ (Vite dashboard: App.jsx, panels/, hooks/, scripts/sync-progress.mjs)'
  - 'src/shared/packages/pyforge-herald/scripts/export_web_snapshot.py, export_notices_snapshot.py'
  - '{planning_artifacts}/retros/retro-herald-2026-08-08.md'
  - '{planning_artifacts}/deferred-work-ledger.md'
  - '{planning_artifacts}/epics.md / epics-with-stories.md (pre-pivot; see §1.3)'
  - '{project-root}/docs/dreams/herald-moments-2-4-live-backend.md'
workflowType: 'research'
lastStep: 5
research_type: 'technical'
research_topic: 'Herald''s as-shipped technical architecture (47/47 stories): the stateless-CLI + static-snapshot design, the mid-build live-backend pivot, current technical debt and risk, the deck-bridge vs dashboard maturity asymmetry, and the opportunity map for the deferred live backend'
research_goals: 'Herald''s first technical research (none existed pre-build). Written from the shipped code and the same-day retro, as the technical ground truth for any future Herald effort — especially a live-backend v2.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
project_slug: 'pyforge-herald'
---

# Research Report: Technical

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical
**Project:** pyforge-herald

---

## Research Overview

### Question

Herald is done — 47/47 stories, Epics 1–12, merged via PRs #111/#114/#116 and
#308–#316, 614+ tests. But "done" was reached through a mid-build architecture pivot
(Epics 8–10 re-specced same-day from live-backend to local-storage/CLI-triggered),
and the planning tier still describes the pre-pivot shape. This report answers, from
the code itself: what actually exists, where the risk and debt now sit, how the two
halves of the package differ in maturity, and what the deferred live-backend Dream
would technically require and enable.

### Methodology

Direct code reading of `src/shared/packages/pyforge-herald/` (~8,000 lines of
Python across 17 modules plus the `web/` Vite app), cross-checked against the
2026-08-08 whole-build retro's Review Triage Log synthesis and the project's
`deferred-work-ledger.md` (the DW-* register). No web research.

### Limitations (declared)

- Zero production-usage time: the dashboard and Moments CLIs shipped today; all
  operational-risk claims are architectural inference, not incident history.
- Four Epic-2 live proofs remain deferred (retro A5) — parts of the bridge's
  remote behavior (`deck pull` against real Design projects, `--commit`,
  `--target marp-deck`/`standalone` naming) are verified only against mocks.

---

## Part 1 — The As-Shipped Architecture

### 1.1 One package, two products

`pyforge-herald` (dist) / `pyforge.herald` (module) / `herald` (CLI, entry through
`cli.py`'s single `_route` dispatcher, `TOP_LEVEL_COMMANDS = ("deck", "progress",
"success", "notice")`) contains two architecturally distinct products:

1. **The deck bridge (Epics 1–5, "Moment 1")** — a *network-facing* CLI:
   `herald deck seed/pull/status/watch/push` against Claude Design's MCP surface.
   Core: `deck_pipeline.py` (1,388 lines), `bridge.py` + a transport abstraction
   (`transport/base.py` port, `mcp_transport.py` primary, `agent_sdk_transport.py`
   fallback), etag-based conflict discipline, `state.py`
   (`.herald/bridge-state.json`) + `registry.py` for local link records.
2. **The Moments dashboard (Epics 6–12, Moments 2–4)** — a *local-only* system:
   three storage modules (`progress.py` → `.herald/progress.json`; `claims.py` →
   `.herald/claims.json`; `notices.py` → git-tracked
   `notices/YYYY-MM/<type>/<component>.md` + `.herald/notices-index.json` cache),
   the CLI verbs over them, and a static React/Vite dashboard (`web/`) whose three
   panels `fetch()` static JSON snapshots — no server, no API, no database.

Shared spine: `errors.py`'s `HeraldError` hierarchy with `dispatch()` as the sole
catch point (AD-6) and a fixed exit-code map (0/1/2/130); every write subcommand
routes through the same closure pattern; the AD-3 determinism boundary
(bridge-core never imports a concrete transport) is enforced by a derived,
coverage-pinned AST sweep that survived four adversarial evasion rounds (retro §2).

### 1.2 The data path of the dashboard — three hand-cranked snapshot hops

The dashboard's entire freshness model is manual copies:

```
herald progress <station> --update      → .herald/progress.json
  → npm run sync-progress (predev/prebuild hook, web/scripts/sync-progress.mjs)
  → web/public/progress.json            → ProgressPanel.jsx fetch()

herald success publish                  → .herald/claims.json
  → python scripts/export_web_snapshot.py
  → web/public/success.json             → SuccessPanel.jsx fetch()

herald notice publish/close/archive     → notices/ + .herald/notices-index.json
  → python scripts/export_notices_snapshot.py
  → web/public/operations.json          → OperationsPanel.jsx fetch()
```

Note the asymmetry: progress syncs automatically on `npm run dev/build` (a
`predev`/`prebuild` hook), while success and operations require a *separately
remembered* Python script — and `export_web_snapshot.py`'s own docstring records
that publish-vs-export decoupling as deliberate. So the three tabs can be mutually
inconsistent snapshots of three different moments in time, and nothing surfaces
when any of them was taken. This is the single most user-visible technical risk in
the shipped system (see §3.1).

### 1.3 The pivot, and the documentation split it left

Epics 8–10 as planned (`epics-with-stories.md`) assumed SQLAlchemy/Alembic, a
Flask/FastAPI webhook endpoint with HMAC + retry/backoff, and APScheduler/Celery
cron. None of it was built; the 2026-08-08 scope decision (recorded in every
implementing spec and in `docs/dreams/herald-moments-2-4-live-backend.md`) replaced
triggers with operator commands while keeping the epics' data schemas intact.
Critically, **`epics.md`/`epics-with-stories.md` were never annotated** (retro A1):
the planning tier still describes webhooks and cron for stories that shipped as
CLI verbs. Every module docstring (`progress.py`, `claims.py`, `notices.py`,
`cli.py`) is honest about the divergence — the code documents itself better than
the planning docs document it. Any future reader must treat module docstrings and
per-story specs, not the epics doc, as architectural truth for Epics 8–10.

---

## Part 2 — The Maturity Asymmetry: Bridge vs. Dashboard

The two halves earned their robustness in opposite ways, and their residual-risk
profiles are mirror images.

### 2.1 The bridge (Epics 1–5): adversarially hardened, remotely under-proven

- **Hardened:** the transport spike (Story 1.2) proved the pure-MCP path live
  against `api.anthropic.com` before anything was built on it; `state.py`'s error
  boundary took three full review passes to close (`UnicodeDecodeError` as a
  `ValueError` sibling, read/write validation asymmetry, non-serializable
  `TypeError` leak); the determinism guard survived four evasion rounds. This is
  the most reviewed code in the package.
- **Under-proven:** the ledger's DW-1-2-* tail is almost entirely *remote-behavior*
  unknowns, all confirmed still open on the 2026-07-30 verification pass:
  - no request timeout on `streamablehttp_client` or `session.call_tool`
    (DW-1-2-9) inside an unbounded `mcp>=1.28.1` pin (DW-1-2-10);
  - HTTP 429 and 5xx conflated into one `TransportUnreachableError` — no
    retry-signal discrimination (DW-1-2-8); server-answered JSON-RPC errors
    misreported as unreachable (DW-1-2-7);
  - a conflicted `write_files` returns as an ordinary success `Mapping` whose
    structured-conflict wire shape has *never been observed live* (DW-1-2-5) — so
    `bridge-protocol.md`'s "seeding over Design-side edits is refused" criterion
    holds only for locally-detectable cases (DW-1-6-1);
  - one MCP session per tool call (an extra `initialize` handshake every call,
    DW-1-2-1); credential resolved once and cached for process lifetime
    (DW-1-2-11).
  Plus the four deferred live proofs (retro A5), blocked purely on
  `/design-login` availability.
- **Verdict:** locally excellent, remotely optimistic. The first sustained real
  Design-side usage session is where the bridge's next defects will surface, and
  the ledger already names where to look.

### 2.2 The dashboard (Epics 6–12): deterministic and honest, but structurally manual

- **Strengths:** no network, no server, no scheduler — nothing to be down. Atomic
  writes everywhere (temp file + `os.replace`, the `state.py` convention reused
  verbatim in all three storage modules); structural-failure discipline on read
  (duplicate-key rejection, full field/type sweeps, `HeraldError` on any malformed
  file); deterministic on-disk ordering (`write_all` sorts by `(station, date)`);
  notices deliberately dual-written so the JSON index is a rebuildable cache of
  the git-tracked markdown, never the sole copy.
- **Inherited weaknesses:** every storage module copies `state.py`'s documented
  lost-update limit — unlocked whole-file read-modify-write, so two concurrent
  writers silently drop one update (DW-1-4-2 and each module's own docstring;
  acceptable single-operator, a real bug the moment any automation also writes).
  And the recurring bug classes the retro catalogs cluster here: five-plus
  instances of raw exceptions leaking through the error boundary
  (`notices._entry_to_notice` missing-field `TypeError` being the latest), three
  write-ordering bugs ("record success before the last irreversible step" —
  Story 1.6 orphaned Design projects, Story 2.1 etag-before-export, Story 10.1
  markdown-after-index), and the argparse global-flag-position gap (Story 10.4).
  Each found instance is fixed with a pinning test; the *classes* are process
  findings (retro A2/A3), not closed risks.
- **Verdict:** robust as a record store, fragile as a *system* — its correctness
  depends on a human running the right commands in the right order (§1.2), which
  no code can currently verify.

### 2.3 Packaging debt (both halves)

Fleet-wide DW-1-1-* items still open: no `LICENSE` file despite
`license = {text = "MIT"}` (all eight sibling packages, DW-1-1-4); version `0.1.0`
hand-duplicated between `pyproject.toml` and `__init__.py` (DW-1-1-5); the
misleading `/dist/` gitignore comment (DW-1-1-2); unbounded `python-build` pin
(DW-1-1-6); no meta-test over registered pixi environments (DW-1-1-8). Plus the
environment-level operational hazards proven during the build: pixi 0.73.0's
whole-workspace re-solve on any new environment, and the ~173-byte worktree
path-length panic (DW-1-2-2) that cost Story 1.2 a full recovery cycle.

---

## Part 3 — Risk Register (as-shipped, ranked)

1. **Snapshot staleness with no freshness signal** (§1.2). Three independent
   manual export paths; a served dashboard can silently show three different
   points in time. Cheapest mitigation: stamp `generated_at` into each snapshot
   and render it per tab; better: one `herald snapshot` command that exports all
   three (the exporter script's own docstring already anticipates sibling
   `export_*_snapshot` functions in one place).
2. **Operator-dependency of record creation.** No trigger exists but human memory;
   an unrecorded ship is indistinguishable from no ship (the domain research's
   attested-truth problem, made concrete by this architecture).
3. **Bridge remote-behavior unknowns** (§2.1) — bounded, ledgered, and likely to
   convert into real defects during the first live-credential session (timeouts
   and the unpinned conflict shape first).
4. **Concurrent-write lost updates** — dormant until any second writer (including
   a future webhook or CI hook — i.e., *the live-backend Dream itself trips this
   first*). Any v2 trigger work must start by adding file locking or moving to
   SQLite, before wiring any automation.
5. **Planning-tier misinformation** — `epics.md` still describes the pre-pivot
   architecture (retro A1, open). Risk is to future contributors and agents, not
   to the running code.
6. **Hardcoded station roster in two places** — `progress.STATIONS` and
   `web/src/components/Sidebar.jsx` each hand-encode the 8 stations, mirrored by
   comment only; a ninth Smith requires remembering both (the classic
   derive-don't-declare smell this repo has already ledgered elsewhere; low
   severity because `progress.py` deliberately never *rejects* unknown stations).

---

## Part 4 — Opportunity Map

### 4.1 The seam is real — the pivot's key technical asset

The live-backend Dream's constraint ("only the data-access layer swaps... CLI
contract must not change shape") is actually satisfied by the shipped code, not
just claimed: `progress.upsert`, `claims.create/publish`, and
`notices.author/publish/close` are pure `(path, **fields) → record` functions with
no CLI coupling. A webhook handler calling `progress.upsert` is a genuinely small
delta *on this code* — the expensive parts of the Dream are the ones the Dream
itself names as open (where it runs, who operates it, what calls it — a
Herald×Steward question), plus the locking prerequisite (§3 item 4).

### 4.2 Serverless intermediate steps (highest value-per-risk, in order)

1. **`herald snapshot`** — one command exporting all three tabs' JSON with
   `generated_at` stamps. Closes risk #1 with zero new infrastructure.
2. **Telemetry-derived defaults for `herald progress`** — read
   `sprint-status-ledger.yaml` / loop journals to pre-fill `--shipped` and cost
   flags; operator confirms instead of types. Reconnects the shipped attested
   model to the 2026-07-25 market research's telemetry-native differentiator,
   still with a human in the loop.
3. **Hook/CI-triggered CLI invocation** — a git post-merge hook or CI job running
   the same CLI commands needs no server and no schema change, and converts
   "operator remembers" into "operator reviews." (Requires the locking fix
   first — this is the second writer.)
4. **`herald notice reindex`** — the rebuild-from-markdown command
   `notices.py`'s docstring already designs but defers; makes the index cache
   formally disposable.
5. **Hosting the static bundle** — the dashboard is a plain Vite build; GitHub
   Pages (where Marshal's Guildhall already publishes) would give the Four
   Moments an audience URL today, with snapshot export as the deploy step.

### 4.3 What the live backend would actually buy, priced honestly

Given 4.2, the residual unique value of the full Dream (DB + webhook + cron) is:
sub-day currency without any human, evidence re-validation on schedule (the
7-day staleness window becoming enforced rather than merely displayed), and
multi-writer correctness. It costs: persistent hosting + operational ownership
(unowned today), webhook authentication, and the migration of three storage
modules to a real DB behind the existing function seam. Recommendation: exhaust
4.2 first — items 1–3 deliver most of the operator-facing "automatic" feel and
generate the usage evidence a hosting decision needs.

## Open Questions

1. Where would a persistent Herald backend run, and under whose operational
   ownership? (Explicitly left open by the Dream; intersects Steward.)
2. Is the unpinned Design-side conflict wire shape (DW-1-2-5) observable in a
   controlled live session, and does `write_files` actually answer with a
   structured conflict at all?
3. Should the three `.herald/*.json` stores converge on SQLite (one file, real
   locking, same seam) before any second writer is added — or is per-file
   `fcntl` locking sufficient for the hook-trigger step?

## Sources

Internal only (declared in frontmatter): the shipped package source, the
2026-08-08 whole-build retro, `deferred-work-ledger.md` (DW-1-1-*, DW-1-2-*,
DW-1-4-*, DW-1-5-1, DW-1-6-1), the pre-pivot epics docs, and the live-backend
Dream.
