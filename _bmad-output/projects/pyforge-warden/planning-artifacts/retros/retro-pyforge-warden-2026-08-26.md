---
title: 'Retrospective: pyforge-warden — post-v1 motion 2026-08-08 → 2026-08-26'
project: pyforge-warden
date: '2026-08-26'
updated: "2026-08-26"
scope: 'Everything that touched src/shared/packages/pyforge-warden (+ the django-warden portal) since the last retro-stage artifact (the 2026-08-08 retros promotion); closes the code→retro currency gap flagged by the 2026-08-26 chain-currency sweep.'
evidence:
  - 'git log --oneline --since=2026-08-08 -- src/shared/packages/pyforge-warden (11 commits, read this pass)'
  - 'git log -- src/shared/packages/django-warden (portal relocation + PortalClient slice)'
  - 'sprint-status-ledger.yaml (2026-08-26: 41/41 stories done, epics 1-10 done)'
  - 'deferred-work-ledger.md (open-item status re-checked)'
  - 'research/technical-warden-dependency-gate-refresh-2026-08-08.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/ (SPEC.md, convergence.md)'
---

# Retrospective — pyforge-warden, 2026-08-08 → 2026-08-26

**Honest framing first:** Warden went fleet-complete on **2026-07-25** (v1: 31/31
stories, six epics, PR #110) and was already retro'd per-epic (the 8 tracked files in
this directory). The motion since 2026-08-08 is **not** a second v1 — it is three
small, spec-bound extension epics (7–10, ten stories) plus estate maintenance riding
through the package. This retro characterizes that follow-up work, verifies what held,
and records what is still open.

## 1. What shipped since 2026-08-08 (from the git evidence)

**Estate maintenance (2026-08-10 → 08-13)** — work done *to* warden by other chains:

- `28551a6b65` (08-10) — audit phase 2: warden reconciled at equal rigor with the
  other completed stations (documentation/audit, no behavior change).
- `1d60da0193` / `5141daad88` (08-12/13, marshal Epic 14) — atomic-write consolidated
  into `pyforge-core`; the one-lattice/one-envelope/one-exception-root pass. Warden's
  own `verdict.py` remained the untouched precedent the shared `pyforge.core.verdict`
  cites — consolidation went *toward* warden's pattern, not over it.

**Epic 7 — one provenance trail, one eligibility answer (08-22;
decomposes `spec-package-inventory-eligibility`, specced 2026-08-22):**

- `332f547a4f` 7.1 — `sources.py`: SourceContract adapters (feeds.py's
  fetch/cache/provenance shape generalized) + the standalone identity API
  (`scikit_learn`/`sklearn` collapse to one identity).
- `0267b02ede` 7.2 — `eligibility.py`: the eligibility union
  (`eligible-union`/`observed-in-use`/`flagged-for-review`, distinct from the Status
  rungs) with ProvenanceEntry trails reproducible from provenance alone.
- `2fe673bcc7` 7.3 — `eligibility_sbom.py`: deterministic CycloneDX out; FABRIC's
  13-archetype manifest corpus in as fixtures (Apache-2.0, notices kept).

**Epic 9 — PR-gate hook specs; scanners are plugins (08-24; FR-44, the CAP-18
retrofit):**

- `b5e34da5d7` 9.1 — the PR-gate hook book published on `pyforge.core.hooks` (shared
  registration, never a Warden-only second loader).
- `4104636b34` 9.2 — today's engines wrapped as the default plugin bundle
  (`scanner_plugins.py`); Checkmarx/Sonar/Black Duck/GHAS become optional plugins.
- `ad4029fc3c` 9.3 — test-enforced: a default run is green with no named commercial
  scanner present; a missing optional plugin is never a failed gate.

**Epic 10 — station skill, persona, one portal job (08-26):**

- `c9877d979e` 10.1 — station meta tests for the SKF skill
  (`.claude/skills/pyforge-warden/`) + `bmad-agent-warden` persona (grammar
  `pyforge warden …`, MCP face only, never a second verdict).
- `51bbcd6d02` 10.2 — `/stations/warden/` starts and retrieves one audit through
  PortalClient only (in `django-warden`).

**Adjacent, same window (portal lineage):** Epic 8's web face (8.1/8.2, 08-22, in
`src/platform/` `compliance_face`) was relocated 2026-08-24 to
`src/shared/packages/django-warden` (`django_warden_fabric`) with `/compliance/` kept
as a permanent redirect (steward S-19.1), and the host MCP face registered 2026-08-25
(steward Epic 21). Warden's package code was not renamed in that move — as the epics'
Canopy-obligations section required.

## 2. What held

- **C0 / never-false-green and the frozen contract.** No incident in the window; the
  7-rung lattice, exit domain `{0,1,2,130}`, and schema 1.1.0 are unchanged through
  ten new stories. Epics 7–10 were producers/wrappers against existing seams —
  exactly the "producers, never editors" discipline the v1 architecture demanded.
- **Verdict sole-ownership survived the plugin layer.** Epic 9 was the designed
  stress test: a plugin API is precisely where a second pass/fail would sneak in, and
  it didn't — 9.1's AC ("the Warden verdict remains the only PR quality-gate
  pass/fail") plus 9.3's absence-is-not-failure test made the Unifying Strategy's
  Always/Never mechanical.
- **The seam bet paid off.** `feeds.py`'s fetch/cache/provenance shape generalized
  into SourceContract (7.1) and the engines wrapped as plugins (9.2) without
  reopening Epics 1–6 — the 2026-08-08 research predicted both patterns were
  "generalizable factory infrastructure," and the window confirmed it.
- **Keys-not-blobs + engines-stay-canonical.** The web face calls the existing
  engines; results render byte-equal to the CLI; no second write path appeared.

## 3. Strategy convergence (Unifying Strategy cross-check)

Warden's three named roles in `spec-pyforge-unifying-strategy` are all now landed and
evidence-backed: **sole PR-gate verdict** (Epic 9 + CAP-18; scanners register as
Warden plugins; never a competing pass/fail), **the `/compliance/` redirect on the
Canopy host** (portal at `/stations/warden/`, permanent redirect kept — convergence.md
item 3, `done`), and **portal + MCP face client** (PortalClient-only actions; `POST
/stations/warden/mcp`). The convergence doc's flagged ledger-rollup drift (warden
epic-7/epic-8 reading `backlog` under done stories) has cleared — the 2026-08-26
ledger reads `done` on all rollups. Five-tier symmetry (CLI / portal / MCP / skill /
persona) is complete for this station.

## 4. Open items (carried, verified against the 2026-08-26 ledger — not new)

- **DW-5-2-5 (P0)** — nothing schedules `pyforge-warden-test-corpus-oracle`; the
  differential-oracle + precision tests still run only by hand. Highest-leverage
  single fix in the 2026-08-08 debt map; still true.
- **DW-5-2-7 (P0)** — all 19 `.warden-baseline.yaml` entries expire simultaneously
  **2027-07-24**; stagger well before the cliff.
- **DW-1-4-1 bullet 1 (P1)** — PEP-503/440 equivalence matching against the offline
  OSV DB remains unexercised (the one untested silent-CVE-miss path).
- **A3 (P1)** — the `license.py` follow-up review (landed at the 3-cycle cap) is
  still unactioned.
- **Family A opportunity** — the "identity sole-ownership" third wall proposed by the
  research is now *more* relevant: Epic 7 added another identity consumer
  (`sources.py`'s identity API) beside `inventory.py`/`mapping.py`/`cli.py`.
- **Watch:** osv-scanner ≥2.5.0 (Scalibr) — re-run conformance before any pin
  widening (6.6 gate); deptry parked at 0.25.1 under `osprey-oss`.

No new skill-boundary findings; per-epic retro obligations for Epics 7–10 are covered
by this station retro (the ledger marks their retrospective keys `optional`).
