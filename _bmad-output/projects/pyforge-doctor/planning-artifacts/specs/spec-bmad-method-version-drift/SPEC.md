---
id: SPEC-bmad-method-version-drift
status: shipped   # 2026-09-06 — Epic 10 + Epic 14 done; Dream realized
owner-dream: docs/dreams/bmad-method-version-drift.md
companions: []
sources:
  - docs/dreams/bmad-method-version-drift.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only — consult it only for narrative rationale this contract intentionally omits.

# Doctor notices when BMAD-METHOD's own installed core falls behind upstream

## Why

Doctor already reports staleness for every other class of fleet dependency — feedstocks behind upstream, dependency floors behind CVE fixes — but has a blind spot for its own installed BMAD-METHOD core, a governance-layer dependency with local customizations to protect, not an ordinary pinned one. Today an operator finds out only by remembering to check, exactly as happened the session this Spec was written: confirmed live, `pixi.toml` already declares `bmad-method >= 6.11.0`, but `_bmad/_config/manifest.yaml` (the actually-installed core) still reports `6.10.0`, undetected until a human happened to ask. This is a pain to solve (an operator stuck without a signal) and a gap to close in an otherwise-consistent staleness-reporting story.

## Capabilities

- **CAP-1 — declared-vs-installed drift.**
  - **intent:** An operator or agent sees when `pixi.toml`'s declared `bmad-method` floor and the actually-installed `_bmad/_config/manifest.yaml` version disagree, without checking by hand.
  - **success:** Given today's real state (`pixi.toml` `>=6.11.0`, `manifest.yaml` `6.10.0`), the new Source's Finding fires; given both agree, no Finding fires. Needs zero new infrastructure — both are already-tracked repo files.

- **CAP-2 — installed-vs-upstream-latest drift.**
  - **intent:** An operator or agent sees when the installed core is behind the latest published upstream `bmad-method` release, not just behind the repo's own declared floor. Data source: a live npm registry query (`https://registry.npmjs.org/bmad-method/latest` or equivalent) issued at check time — an operator-approved, deliberate exception to the fleet's general "no live query per home" discipline, scoped narrowly to this one ambient, non-gating, warn-only Finding (CAP-3).
  - **success:** Given the installed `manifest.yaml` version is older than the latest upstream release returned by the live query, a Finding fires naming both versions. Given the query fails or times out (offline, registry unreachable), no Finding fires and no error surfaces — CAP-2 degrades silently to CAP-1-only, never blocking or failing the check-suite (CAP-3's constraint applies here too).

- **CAP-3 — ambient, non-gating surface.**
  - **intent:** The drift Finding appears where operators already look — Doctor's own report/verdict shape and `fleet-picture`'s ATTENTION block — and never blocks or fails a check-suite run on its own.
  - **success:** `fleet-picture`'s ATTENTION block names the drift when CAP-1 or CAP-2 fire; the check-suite's exit code is unaffected by this Finding alone (a `warn`, never a `fail`).

- **CAP-4 — suite-vs-upstream drift** *(added 2026-08-21, superseding the former "core only" non-goal).*
  - **intent:** The same ambient signal covers the installed bmad-suite, not just the core. Motivating evidence (2026-08-21, the live 6.10.0→6.11.0 upgrade session): `bmad-loop` sat at 0.9.0 against upstream 0.11.0 — 0.9.0 hardcodes `/bmad-dev-auto` and stalls every unattended session on BMAD ≥ 6.11, which upstream patched in an emergency 0.9.1 — while TEA lagged 1.19.1 vs 1.23.2 (1.19.1's `tea-test-review` bin was published empty), and three coordinated ecosystem waves rode the window. None of it produced any ambient signal until a human checked.
  - **success:** The watched set is DERIVED from `pixi.toml`'s `bmad-*` pins (never a hardcoded list — a hardcoded list omits exactly the newest tool); installed environment versions are compared against latest upstream releases through the same fail-open live-query exception CAP-2 already holds; warn-only per CAP-3. Pointed at the 2026-08-21 pre-update state, it names `bmad-loop 0.9.0 < 0.11.0` and `TEA 1.19.1 < 1.23.2`; offline it degrades silently.

## Constraints

- **Read-only, always.** This Spec never runs `npx bmad-method install` or writes to `_bmad/**` — applying an upgrade is `bmad-method-core-upgrade`'s (owner: steward) territory entirely, never this one's.
- **Fits Doctor's existing closed-taxonomy Source enum** (PRD FR-2's convention, reused verbatim by FR-12's `adoption-stage`) — never an open/stringly-typed source.
- **Must not duplicate `bmad-method-core-upgrade`'s own pre-flight diff.** That Dream may run its own dry-run check immediately before an apply; this Spec's job is the AMBIENT, continuously-refreshed signal an operator sees without running anything.
- **CAP-2's data source is settled: a live, per-check npm registry query.** Resolved in practice by Story 10.2 — `_fetch_latest_upstream_version` queries npm's public registry (`https://registry.npmjs.org/bmad-method/latest`) live at check time via stdlib `urllib.request`, fails open on any error within `_UPSTREAM_FETCH_TIMEOUT_SECONDS`, and is never a periodically-cached feed; CAP-2 was never deferred to a follow-on story.
- **Registry placement is settled: a dedicated Source, never an extension of `bmad-drift`.** Resolved in practice by Story 10.1 — this capability is registered as its own dedicated `pyforge.doctor.sources.bmad_method` module and its own `Source.BMAD_METHOD_VERSION_DRIFT` enum member, never folded into the existing `bmad-drift` source (`pyforge-marshal` artifact-vs-live-factory drift), a different artifact class entirely.

## Non-goals

- Not applying, merging, or reconciling anything — steward's territory via `bmad-method-core-upgrade`.
- Not deciding which currently-unexercised BMAD modules to keep or drop (`one-front-door`'s own open question).
- Not a general "any dependency is behind" detector — scoped to BMAD-METHOD's installed core and the `bmad-*` suite (CAP-4, 2026-08-21); every non-BMAD dependency stays out.

## Success signal

An operator running `fleet-picture` or Doctor's own report sees, without checking anything by hand, that the installed `bmad-method` core is behind either the declared `pixi.toml` floor or the latest upstream release — demonstrated today by the real, live `pixi.toml`-vs-`manifest.yaml` drift firing a Finding as soon as CAP-1 ships.
