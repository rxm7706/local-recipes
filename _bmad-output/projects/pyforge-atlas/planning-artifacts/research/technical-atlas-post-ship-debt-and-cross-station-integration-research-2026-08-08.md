---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-atlas.md
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py
  - .claude/skills/conda-forge-expert/SKILL.md
research_type: 'technical'
research_topic: 'Post-ship technical debt inventory + domain problem re-validation + cross-station integration audit, three weeks after the pyforge-atlas Kedro migration shipped (2026-07-18; Epic 10 truth-up 2026-07-29)'
research_goals: 'State plainly what is and is not in production three weeks post-ship; re-validate the migration''s founding domain problem against the observed operating reality; audit whether the cross-station integration points (Doctor/Marshal/Mason consuming Atlas) are exercised as designed; rank the real opportunities.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
methodology_note: 'Entirely in-repo evidence: the deferred-work ledger''s 2026-07-30 per-entry verification stamps (the deferred-work verification campaign''s output), live file reads of the pyforge-atlas and pyforge-doctor packages, SKILL.md/CHANGELOG (v8.81.0), and the shipped spec. No web claims.'
---

# Research Report: Technical Research — Atlas Post-Ship Debt & Cross-Station Integration (3 Weeks In)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical (operational-reality audit of a shipped system)

---

## Research Overview

Atlas is "SHIPPED, 38/38 stories, 100% code-complete" (`docs/dreams/pyforge-atlas.md`) — and that claim is true. This report asks the next question, which no prior research file in this folder asks: **three weeks into real use, which half of the shipped system is actually operating, who is actually consuming it, and does the founding problem statement still hold?** The headline, stated up front and without spin:

> **The production data path is still the legacy orchestrator.** Every daily-use read surface — the 17 atlas CLIs, the `conda_forge_server.py` MCP tools, and Doctor's live watch axes — runs against `cf_atlas.db` built by `conda_forge_atlas.py`. The migrated Kedro package is code-complete, contract-tested (930 tests), and **not yet the system of record**, because the chain that would make it one (fixture recapture → credentialed parity → human sign-off → legacy retirement) is a sequence of attended events none of which has happened. This is by design (AD-11/AD-19, `parity/evidence.py:51` `human_sign_off = None`), not a failure — but three weeks of "production use" has therefore exercised the *old* system, and every integration consumer is wired to the old surface.

---

## 1. Debt inventory: what the 2026-07-30 verification campaign proves is still open

The deferred-work ledger (`planning-artifacts/deferred-work-ledger.md`, 57 `DW-` entries) was per-entry verified against code on 2026-07-30: **51 open, 2 done** (the rest partially resolved/note-only). The open set is not 51 independent problems — it collapses into **five structural clusters**, which is the useful shape for planning:

### Cluster A — the retirement chain (blocks everything downstream)
`DW-B1-1(a)` → `DW-B4-3` (fixtures still stamped `shape-only-seed-B2-needs-B4-recapture` — a green `parity-diff` proves port==implementer-belief, **not** port==legacy) → `DW-B4-1` (credentialed parity run never happened) → `DW-B4-2` (`may_retire_legacy` returns `allowed=False`; nobody signed) → plus reconcile items parked on the run (`DW-B1-3`, `DW-B2-3`, `DW-B4-5`, the ~44-feedstock maintainer-universe delta). **One attended afternoon with the real `cf_atlas.db` unblocks the entire cluster.** Until then the fleet runs two parallel implementations of the same intelligence layer, and every new signal must be either double-implemented or consciously landed on only one side.

### Cluster B — the injected-seam family (the Kedro package cannot fetch)
By the A2 no-inline-IO rule (AST-scanned: no `subprocess`/HTTP imports in-package), every live fetcher is an *injected callable defaulting to None*: vdb/OSV refreshers (`DW-B5-2`), the transitive resolver (`DW-B7-2`), the Basilisk client (`DW-B8-1`, plus the credentialed 21k-package population run `DW-B8-3`), the per-request PyPI fan-out (`DW-B2-5`). Injection happens at the Dagster bring-up (`DW-C1-1` — sensors ship `default_status=STOPPED`, `orchestration/definitions.py:301`), which is itself an attended event that has not occurred. **Consequence: the migrated pipeline currently cannot produce fresh data end-to-end unattended even in principle** — offline-stale-degrade is the only live behavior. Also parked on bring-up: per-op timeout *enforcement* (the `dagster/max_runtime` tags are daemon-enforced; today's isolation is job separation only) and profile-config run-wiring (`DW-C1-2`), and the Phase-P BigQuery cost-gate routing (`DW-B2-4`/`DW-B4-4` — `conf/base/catalog.yml:198` still routes `pypi_bigquery_downloads_raw` to a gateless `api.APIDataset`; **this one is a safety item, not a convenience item**: the two-layer cost gate that exists because of a real $500+ invoice protects the class, not the catalog's default path).

### Cluster C — read-surface hollowness
The Vizro dashboard's core pages beyond `feedstock-health`/`my-feedstocks` are **BSL-wired shells rendering honestly-empty** (`dashboard/data.py:126`, `DW-D2-2` — the composed `semantic_packages` store was never materialized); the full 28-page inventory is spine-deferred (`DW-D2-1`, CIS two-spine specs never produced); the rendered UI has never been visually verified by anyone (`DW-D2-3`); Vizro-AI's NL backend is not live (`DW-D3-1`, Q3's LLM-routing question still undefined). The dashboard is therefore a *demonstration* surface, not yet an *operating* one.

### Cluster D — correctness contracts waiting on consumers
`DW-B5-4` is the sharpest: the AD-13 staleness marker is *surfaced* by the store datasets but **no consumer reads it** — `grep pipelines/ -r is_stale` = 0 hits — so an air-gapped run's empty vuln store is indistinguishable from a genuinely clean one, exactly the "silent pass" AD-13 exists to forbid. Siblings: `coerce_cvss_score` authored but not on the node path (`DW-B2-2`); `conda_license`/`upstream_version` never produced by core, leaving the spdx-gap tiers and the UPDATE-FEEDSTOCK bucket unable to fire on live data (`DW-B6-1`, `DW-B7-1`, `DW-B8-2`). These are cheap, unattended-fixable, and — unlike Clusters A/B — do not wait on any event.

### Cluster E — genuinely fine
`DW-B5-3` (JFrog per-host attach — no live surface exists to attach to) and the alias/note-only entries. No action.

**Ranked opportunity list from the debt inventory:** (1) schedule the Cluster-A attended parity afternoon — it is the single highest-leverage act available to this station; (2) fix Cluster D unattended now (staleness-consumer wiring first — it is a safety contract); (3) route the Phase-P cost gate (one catalog edit + invariant bump) before anyone runs credentialed Phase P; (4) treat Cluster C as demand-driven — materialize the composed store only for pages someone actually asks for, per the market research's own "feeds > pages" finding.

---

## 2. Domain problem re-validation

The migration's justification was deliberately re-scoped by the PRFAQ kill-test to **agent-maintainability, not urgency** (spec § 3.2: the legacy tax is "chronic and compounding, not acute"). Three weeks in:

- **The chronic framing is vindicated by observed behavior.** The legacy path kept shipping (CFE v8.80.0/v8.81.0 landed post-migration, incl. the AUD-CFE path-confinement work) and nothing broke for lack of the new stack — exactly what "chronic, not acute" predicts. No evidence contradicts the founding problem; equally, no *pressure* has yet forced the cutover, which is why Cluster A can drift. The risk is not that the migration was wrong; it is that **a chronic justification never self-schedules its own payoff event** — the parity afternoon has no forcing function, and this report recommends giving it one (attach it to the next admin-profile rebuild, which already requires the operator present with a credentialed DB).
- **The "add phase 24 by writing a node" promise is real but unexercised.** upstream-discovery (the first genuinely new post-migration signal) is specced to land as Kedro nodes — it will be the promise's first live test. Note the structural nudge: until Cluster A closes, a new signal lands *only* on the Kedro side (correct per Q7's build-once default) and therefore **won't be visible to any current consumer** (§ 3) — a subtle trap worth stating in that Spec.
- **One founding gap is now double-covered in opposite directions**: § 3.2's "no visual DAG observability" is answered by kedro-viz *manual* captures (real DAG) and the *shipped-but-shell* Vizro pages (live data absent). The kedro-org-tooling Dream's publish-kedro-viz item (companion report § 1.2) closes the first half cheaply; Cluster C's composed store closes the second.

---

## 3. Cross-station integration audit: are the integration points exercised as designed?

The Charter positions Atlas as the intelligence layer every station consumes. What is actually wired, verified by code read on this branch:

| Station | Designed consumption | Actual state (2026-08-08) |
|---|---|---|
| **Doctor** | Watch axes over atlas signals | **REAL and live — the fleet's one true Atlas integration.** `pyforge-doctor/src/pyforge/doctor/sources/atlas.py`: 4 axes (staleness / cve / abandonment / adoption) over 6 atlas instruments (`staleness_report`, `cve_watcher`, `feedstock_health`×2, `release_cadence`, `adoption_stage`, `version_downloads`), MCP-first against **`.claude/tools/conda_forge_server.py`** with CLI fallback, per-sub-call degrade-to-Finding, sole-MCP-import meta-test. Exemplary engineering — **wired entirely to the LEGACY surface.** |
| **Mason** | (docstring mention only) | `pyforge/mason/__init__.py:5` names `pyforge.atlas` in prose; **zero code consumption**. |
| **Marshal** | Loop orchestration (consumed Atlas as a *project*, not as data) | No data-plane consumption; references are to atlas-the-effort (retro learnings, loop policy). |
| **Herald / Scribe / Steward / Warden** | — | No atlas consumption. (Warden deliberately stays decoupled — atlas-provides-data/warden-verdicts, PRD § 9.13.) |
| **Anything → `pyforge.atlas.mcp`** | FR-7's migrated MCP surface (Story B3: `mcp/server.py`, `tools.py`, `session.py`, `audit.py`) | **Zero external consumers.** Repo-wide grep for `pyforge.atlas.mcp` outside the atlas package: no hits. |

Three findings fall out:

1. **The designed integration architecture is real but singly-instantiated.** Doctor proves the pattern works end-to-end (and its transport/degrade design is the template Mason/Steward should copy when they need atlas signals). But "the intelligence layer every station consumes" is today "the intelligence layer *one* station consumes."
2. **Two parallel MCP surfaces exist and all traffic is on the legacy one.** `conda_forge_server.py` (46 tools, 23 atlas-relevant, backed by `cf_atlas.db`) carries 100% of consumption; `pyforge.atlas.mcp` (Kedro-session-native, audited per FR-7) carries 0%. This is *consistent* while legacy is the system of record — but it means **legacy retirement (Cluster A) is not only an Atlas-internal event: it breaks Doctor** unless one of two re-point paths is executed, and today **neither path has an owner**: (a) re-back the `conda_forge_server.py` atlas tools with Kedro/DuckDB reads (transparent to Doctor — likely correct, since the tools are thin `_run_script` shims and Doctor's contract is the tool schema, not the store), or (b) re-point Doctor at `pyforge.atlas.mcp` (churns a shipped, meta-tested consumer). **Recommendation: (a), declared as an explicit story in the retirement plan, with Doctor's own test suite as the acceptance gate.** This is the single most important previously-unstated integration fact this research surfaces.
3. **The consumption asymmetry is also a signal-demand map.** Doctor chose staleness/cve/abandonment/adoption — four of the 17 CLIs. Nothing consumes velocity (FR-20), migration-readiness (FR-21), or Basilisk (FR-19) yet — the three *new* signals the migration added. Partly circular (B8-B10's live population runs are Cluster-B-deferred, so there is little data to consume), but worth carrying into any "what should Atlas build next" conversation: **before adding signal #25, get signals #22–24 a first consumer.**

---

## Assumptions

- The 2026-07-30 verification stamps are treated as current for code-state claims; spot-checks during this pass (e.g., `SENSOR_DEFAULT_STATUS`, `dashboard/data.py` banner, `pyforge.atlas.mcp` consumer grep, Doctor's `sources/atlas.py`) confirmed no drift in the sampled entries between 07-30 and 08-08.
- "Production use" is read as the operator's + agents' daily CFE workflow (which demonstrably continued on the legacy path) — there is no separate telemetry system to consult; absence-of-consumption claims are grep-verified absence in the working tree.

## Open Questions

- What is the forcing function for the Cluster-A parity afternoon? (Proposed above: attach it to the next credentialed admin-profile rebuild. Alternative: a dated entry in Marshal's fleet dashboard so it stops being invisible.)
- Should the legacy→Kedro re-backing of `conda_forge_server.py`'s atlas tools (§ 3 finding 2, path (a)) live in the pyforge-atlas backlog or the CFE skill's? The tools are `.claude/tools/` surface (CFE-owned) but the data contract is Atlas's — a cross-station ownership call the Charter pattern (owner ≠ mechanism) should settle explicitly.
- Does Doctor want a fifth axis over the new signals (velocity / readiness / Basilisk) once Cluster B lets them populate — or is four the right number until a persona asks?

## Sources (all internal, read 2026-08-08)

- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` — 57 entries, per-entry `verified: 2026-07-30` stamps (the primary evidence base for § 1)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/` — `orchestration/definitions.py`, `dashboard/data.py`, `parity/evidence.py`, `mcp/{server,tools,session,audit}.py`, `conf/base/catalog.yml`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py` (+ its module docstring's transport contract)
- `.claude/skills/conda-forge-expert/SKILL.md` § "Atlas Intelligence Layer" + `CHANGELOG.md` (v8.81.0, 2026-07-29) — evidence the legacy surface is the live documented one
- `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` §§ 3.2, 11 (Q2/Q3/Q7), 12.1, 15; `docs/dreams/pyforge-atlas.md` § Remaining
- Companion: `technical-kedro-ecosystem-and-stack-currency-research-2026-08-08.md` (stack currency + cross-station stack-adoption question)
