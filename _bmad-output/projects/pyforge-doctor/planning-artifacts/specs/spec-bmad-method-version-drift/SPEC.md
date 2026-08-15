---
id: SPEC-bmad-method-version-drift
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
  - **intent:** An operator or agent sees when the installed core is behind the latest published upstream `bmad-method` release, not just behind the repo's own declared floor.
  - **success:** Given the installed `manifest.yaml` version is older than the latest upstream release, a Finding fires naming both versions. Data source for "latest upstream release" is undecided — see Open Questions.

- **CAP-3 — ambient, non-gating surface.**
  - **intent:** The drift Finding appears where operators already look — Doctor's own report/verdict shape and `fleet-picture`'s ATTENTION block — and never blocks or fails a check-suite run on its own.
  - **success:** `fleet-picture`'s ATTENTION block names the drift when CAP-1 or CAP-2 fire; the check-suite's exit code is unaffected by this Finding alone (a `warn`, never a `fail`).

## Constraints

- **Read-only, always.** This Spec never runs `npx bmad-method install` or writes to `_bmad/**` — applying an upgrade is `bmad-method-core-upgrade`'s (owner: steward) territory entirely, never this one's.
- **Fits Doctor's existing closed-taxonomy Source enum** (PRD FR-2's convention, reused verbatim by FR-12's `adoption-stage`) — never an open/stringly-typed source.
- **Must not duplicate `bmad-method-core-upgrade`'s own pre-flight diff.** That Dream may run its own dry-run check immediately before an apply; this Spec's job is the AMBIENT, continuously-refreshed signal an operator sees without running anything.

## Non-goals

- Not applying, merging, or reconciling anything — steward's territory via `bmad-method-core-upgrade`.
- Not deciding which currently-unexercised BMAD modules to keep or drop (`one-front-door`'s own open question).
- Not a general "any dependency is behind" detector — scoped specifically to BMAD-METHOD's own installed core.

## Success signal

An operator running `fleet-picture` or Doctor's own report sees, without checking anything by hand, that the installed `bmad-method` core is behind either the declared `pixi.toml` floor or the latest upstream release — demonstrated today by the real, live `pixi.toml`-vs-`manifest.yaml` drift firing a Finding as soon as CAP-1 ships.

## Open Questions

- **CAP-2's data source.** No existing fleet infrastructure covers npm-package version lookups — `atlas`'s `behind-upstream`/`version-downloads` machinery (FR-12's own precedent) is conda-forge/PyPI-scoped only, not npm. Options: a live npm registry query at check time (tension with Marshal's own "no live query per home" discipline this fleet otherwise favors), a periodically-refreshed cached feed, or shipping CAP-1 alone first and deferring CAP-2 to a follow-on story.
- **Exact registry placement.** Which `pyforge.doctor.sources.*` module this plugs into — a new dedicated source, or an extension of the existing `bmad-drift` source (already used for `pyforge-marshal` artifact-vs-live-factory drift)? An architecture-level decision, not resolved here.
