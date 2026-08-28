# Design Thinking Session: pyforge-atlas — 19-Page Vizro Spine

**Date:** 2026-08-28
**Facilitator:** Maya (Design Thinking Maestro, CIS `bmad-cis-agent-design-thinking-coach`), workflow `bmad-cis-design-thinking`
**Design Challenge:** Design the information architecture and UX for the 19 Vizro dashboard pages not yet in `dashboard/app.py::PAGE_INVENTORY`, so Story 20.5 has a technical + behavioral target to port against.

**Mode:** autonomous-headless (no live human collaborator — this is a planning-story dispatch). Grounded in a prior divergent-ideation pass run by Carson (`bmad-cis-agent-brainstorming-coach` → its own menu dispatches to `bmad-brainstorming`) on 2026-08-28, recorded at `_bmad-output/brainstorming/brainstorm-atlas-19-page-spine-2026-08-28/` — loaded here as EMPATHIZE/IDEATE input, not as a substitute for this workflow's own DEFINE/PROTOTYPE/TEST steps.

---

## 🎯 Design Challenge

pyforge-atlas's Vizro dashboard ships 9 live-confirmed pages (`behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`, `factory-status`, `estate-cache`) against a 28-page target ported from 28 legacy atlas CLIs. 21 CLI read-questions remain unaddressed by any shipped page. This session designs all of them, consolidated to exactly 19 pages (one merge: `platform-breakdown` + `pyver-breakdown` + `channel-split` → one `distribution-breakdown` page), so no CLI question is dropped and Story 20.5 can port against a frozen shape.

---

## 👥 EMPATHIZE: Understanding Users

### User Insights

Six user types actually touch this 19-page surface, reused from `reference/atlas-phases-overview.md` Part A's existing 4-persona taxonomy (no parallel taxonomy invented) plus two sub-variants surfaced by Carson's Persona Journey pass:

- **I. Feedstock Maintainer** (primary for `cve-watcher`, `version-downloads`, `release-cadence`, `adoption-stage`, `distribution-breakdown`) — arrives wanting ONE answer about THEIR OWN package(s): "did anything change since I last looked." They resent needing to memorize CLI flags to get there.
- **II. conda-forge Admin / Core Team** (channel-wide variant of I — `cve-watcher --only-increases` with no `--maintainer`, `adoption-stage` portfolio view, `release-cadence` silent-maintainer sweep) — same questions as a maintainer, but at N-maintainer scale; needs the identical page to serve both without a second UI.
- **III. Consumer / Downstream User** (primary for `find-alternative`, `scan-project`, `env-inspect`, `universe-sbom`, `inventory-match`, `library-futures`, `recommend-2027`) — often arrives in a bad moment (a broken build, a compliance deadline, a portfolio review), not browsing. Needs the page to short-circuit to an answer, not invite exploration.
- **IV. Cross-cutting / Infrastructure** (primary for `export-purls`, `mapping-gap`, `add-handoff`, and all 4 seed-gap suggesters) — curators and packaging-agent operators who treat these pages as a worklist to triage, always ending in an OUTSIDE-the-dashboard action (git review, a CLI `--write`, a handoff to `conda-forge-expert`).
- **A new maintainer** (sub-variant of I) — has never read the CLI flag docs; needs inline affordances (tooltips, plain labels), not assumed familiarity.
- **An MCP agent** (cross-cutting, sits alongside IV) — hits every page via the MCP layer, not a browser; needs a structured, machine-parseable empty/no-data state on every single page, not prose a human reads.

### Key Observations

- **Report-artifact pages are not one shape — they're two.** `inventory-match`/`add-handoff`/`library-futures` (the FR-9 exceptions) NEVER trigger a new run from the dashboard — they only ever show the last cached result. `scan-project`/`env-inspect` are the opposite: the dashboard IS how the user triggers a brand-new per-invocation scan. Treating both pairs as the same "report-artifact" `kind` was Carson's own divergent-pass draft error, caught in DEFINE below — see § kind taxonomy.
- **"No data" reads as "broken" unless a page explains WHY.** Every persona flagged variants of this: a stale scan with no visible age, a fresh checkout with nothing to show, a genuinely-good "zero results" outcome (no new CVEs, no mapping gaps) all look identical to a generic empty grid unless the page states its own reason.
- **Non-authoritative data needs one consistent visual language, not four different ones.** The seed-gap suggesters, `mapping-gap`, and `library-futures`' operator overrides all produce "likely/hint/report" tier values that a downstream reader could mistake for verified fact if the UI doesn't mark them.
- **Real incident-response chains cross page boundaries.** The already-documented triage→detail→remediation chain (`cve-watcher`→`detail-cf-atlas`→`find-alternative`) misses a second real chain: a security lead deciding whether a CVE-flagged package is even worth keeping wants to jump straight from `cve-watcher` to `library-futures`, not through `detail-cf-atlas` first.
- **Discoverability, not just correctness, is a design requirement.** The `distribution-breakdown` merge is efficient but risks burying `pyver-breakdown`'s distinct `--policy-check` mode inside a page that otherwise looks like plain reporting.

### Empathy Map Summary

| | Feedstock Maintainer (I) | Consumer arriving in a panic (III) | Curator / Infra operator (IV) |
|---|---|---|---|
| **Says** | "Did anything break since last week?" | "My build just failed, what do I do?" | "Is this suggestion safe to accept?" |
| **Thinks** | "I don't have time to run six CLIs to find out." | "I need one clear next step, not an investigation." | "I don't want the dashboard writing to my curated file." |
| **Does** | Scans a delta/trend view once a week at most. | Arrives via a link from a failure, not a bookmark. | Cross-references a proposal list against what they already know, then acts in git, not in the browser. |
| **Feels** | Mildly anxious until the page says "nothing changed." | Time-pressured, wants confidence fast. | Cautious — one bad accepted suggestion pollutes a hand-curated source of truth. |

---

## 🎨 DEFINE: Frame the Problem

### Point of View Statement

**Primary POV:** *A feedstock maintainer, downstream consumer, or curator needs a page for every one of the 21 remaining legacy-CLI read-questions that answers "what changed / what should I do next" in one glance — because today that answer only exists behind a terminal command they have to remember, and the dashboard's own honest-empty and provenance conventions (AD-8, AD-17, NFR-8) must extend to these 19 pages exactly as they already do to the 9 shipped ones.*

Bucket-level POVs (each page's own full POV statement is recorded in PROTOTYPE below, per page):

- **Atlas-CLI bucket (8 pages):** "As a maintainer or admin, I need my portfolio's health signals (CVEs, downloads, cadence, adoption, distribution) and my downstream-facing tools (find-alternative, scan-project, env-inspect) surfaced without terminal access, because triaging by memory doesn't scale past a handful of feedstocks."
- **Cyclonedx-suite bucket (7 pages):** "As a consumer or infrastructure operator, I need visibility into the universe-scale SBOM/mapping/futures surface — much of it read-only-by-design — because these are portfolio and compliance questions, not per-package lookups."
- **Seed-gap-suggester bucket (4 pages):** "As a curator, I need a pre-filtered, confidence-tiered proposal list for each hand-curated source file, because scanning full upstream catalogs by hand every time is exactly the toil these suggesters exist to remove."

### How Might We Questions

1. How might we let a maintainer see "what changed" across CVEs, downloads, and cadence without running three separate CLIs?
2. How might we make an empty result read as "good news" or "not yet run" instead of "broken," on every page?
3. How might we let a channel-wide admin reuse the exact same page a single maintainer uses, without building a second UI?
4. How might we make a write-path CLI's last output visible on the dashboard without ever letting the dashboard trigger the write?
5. How might we distinguish "the dashboard is fetching a live per-invocation scan" from "the dashboard is querying a cached catalog," so a user's mental model matches what's actually happening?
6. How might we give every likely/hint/report-tier value one consistent, unmistakable visual treatment across all the pages that produce them?
7. How might we let a security lead move from a CVE alert straight to "is this package worth keeping" without a detour?
8. How might we keep `distribution-breakdown`'s three-CLI consolidation from hiding `pyver-breakdown`'s distinct policy-check capability?
9. How might we let an MCP agent parse every page's empty/no-data state as reliably as a human reads it?
10. How might we handle the one page (`universe-sbom`) whose backing data (~856k components) is too large to render naively?

### Key Insights

- The FR-9 exceptions (`inventory-match`, `add-handoff`, `library-futures`) and the two live-invocation pages (`scan-project`, `env-inspect`) both "show a report," but the dashboard's relationship to generating that report is opposite in each case — this must be two different `PageDef.kind` values, not one shared `report-artifact` kind.
- A single cross-cutting rule ("every likely/hint/report-tier value gets the same badge") is more maintainable and more discoverable than four independent per-page decisions, and it must be stated once, not implied four separate times.
- The existing triage→detail→remediation navigation chain is real but incomplete; a second short-circuit chain (`cve-watcher` → `library-futures`) reflects an actual, distinct decision a security lead makes.
- `distribution-breakdown`'s facet-selector consolidation is the right call (validated independently by Carson's Morphological Analysis and Failure Analysis passes), provided the `--policy-check` sub-view gets an explicit discoverability affordance rather than just becoming a fourth silent facet.

---

## 💡 IDEATE: Generate Solutions

### Selected Methods

Selected from `design-methods.csv`'s `ideate` phase, chosen for a 19-page architecture problem (breadth over depth, many independent pages sharing a few repeating shapes):

- **Brainstorming** — broad generation across all 19 pages before narrowing to shared shapes.
- **SCAMPER Design** — applied specifically to the report-artifact pages (Substitute/Combine/Adapt) to resolve the two-kinds-not-one-kind question, and to the seed-gap suggesters (Combine into shared shape, but keep pages distinct per source file).
- **Analogous Inspiration** — borrowed UI patterns from tools this exact audience already trusts (Grafana panels, Dependabot/Snyk PR-comment framing, Datadog's severity color language, GitHub Insights' calendar view, Anchore's SBOM treemap, Renovate's single-issue dashboard, conda-forge's own linter-comment style) — carried forward from Carson's Analogical Thinking pass, re-validated here against the DEFINE-phase insights.

### Generated Ideas

Divergent, page-level ideas (19 pages + cross-cutting ideas), before convergence in PROTOTYPE:

1. `cve-watcher`: a severity-weighted headline score above the delta table, so a maintainer gets ONE number before the table.
2. `cve-watcher`: a maintainer-switcher dropdown so the same page serves both persona I and persona II.
3. `cve-watcher`: direct cross-link to `library-futures` for the "is this package worth keeping" decision.
4. `version-downloads`: adoption curve chart + per-version table sharing one dataset, independent sort controls.
5. `release-cadence`: a headline trend LABEL (not a number) as the first thing seen — matches the CLI's own output shape.
6. `find-alternative`: pre-fill from the last in-session `scan-project` failure if one exists.
7. `find-alternative`: distinguish "package name not recognized" from "recognized but no healthy alternative" as two different empty-state messages.
8. `adoption-stage`: click-to-filter directly on the stage-distribution chart (the chart IS the filter).
9. `adoption-stage`: a maintainer-scoped view with 0 OR 1-2 packages falls back to a plain label list instead of a degenerate stacked bar.
10. `distribution-breakdown`: ONE page, a dimension-selector (platform / python-version / channel) driving a shared chart+grid, with a one-time onboarding tooltip the first time the python-version facet is selected (so `--policy-check` isn't silently buried).
11. `scan-project` / `env-inspect`: an upload/path input control front-and-center (not styled like the catalog `Filter`s elsewhere), because the user supplies new input here — these get `kind: live-scan-artifact`, distinct from the FR-9 exceptions' `kind: report-artifact`.
12. `scan-project` / `env-inspect`: three states each — no-scan-yet (input-needed), report-available, and a failed/invalid-run state (a malformed manifest or a scan error is not the same as "never run").
13. `universe-sbom`: summary Cards first, a hard-capped paginated grid second, never a naive 856k-row render; steal Anchore's treemap-by-download-volume idea as a stretch visualization.
14. `mapping-gap`: deliberately no "accept" button — read-only by the CLI's own DRY-RUN contract; conda-forge's own linter-comment styling for each proposal row.
15. `inventory-match` / `add-handoff` / `library-futures`: `kind: report-artifact` (cached-latest-only), each with a "no cached run yet" state distinct from "ran, and the result was empty" (an empty ADD-bucket worklist is a legitimate "caught up" state, not the same as "never run").
16. `add-handoff`: license-blocker rows visually distinguished (hard stop, not soft warning); a forward-looking claim-marker note recorded for a future multi-agent coordination story (not implemented now — would cross into write-path territory).
17. `recommend-2027`: per-signal breakdown expands in-place; operator-override badges carry their own timestamp, decoupled from the compute run's timestamp.
18. `library-futures`: tier-badge color vocabulary shared with `recommend-2027` so a user moving between the two pages doesn't relearn a legend.
19. Seed-gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`): one shared shape (tier-count Card + ranked AgGrid), each still its own page since the source files are genuinely distinct artifacts; each names its ported legacy CLI explicitly.
20. Cross-cutting: a single non-authoritative badge style, stated once, applied to all four seed-gap suggesters, `mapping-gap`, and `library-futures`' override badges.
21. Cross-cutting: every report-artifact-shaped page (both kinds) shows an "as of `<timestamp>`" staleness stamp as prominently as the data itself.
22. Cross-cutting: every page's honest-empty state emits a structured, machine-parseable no-data marker for MCP-agent consumers, not just human-readable prose.

### Top Concepts

Converged to 3 structural concepts that govern all 19 pages (rather than 2-3 individual pages — for an information-architecture challenge, the "prototype" is the whole 19-page spine, and these are the load-bearing decisions that make it coherent):

1. **A corrected, two-value report-artifact `kind` taxonomy** (idea #11 + #15) — resolves the single most consequential DEFINE-phase gap.
2. **One cross-cutting non-authoritative-badge + staleness-stamp system** (idea #20 + #21), applied consistently rather than ad hoc.
3. **The `distribution-breakdown` consolidated page with an explicit discoverability affordance** (idea #10) — the spine's only page-count consolidation, so it gets the most scrutiny.

---

## 🛠️ PROTOTYPE: Make Ideas Tangible

### Prototype Approach

The "prototype" for a 19-page information-architecture spine is a full technical + behavioral page-by-page specification — low-fidelity in the sense that no pixel-level mockup or code exists, but complete in the sense that every page names its `PageDef` shape, its BSL model, its layout, and its persona/journey/edge cases, so Story 20.5 has nothing left to invent. This is captured in full in the companion documents `DESIGN.md` (technical/visual: BSL model, source dataset, layout, key columns, `kind`) and `EXPERIENCE.md` (behavioral: persona, POV, journey, interaction, edge cases, success metric) under this same `planning-artifacts/` directory — this workflow run is their authoring source; they are not a separate improvised substitute.

### Prototype Description

**Corrected `kind` taxonomy (Top Concept 1):**

| `kind` | Meaning | Pages |
|---|---|---|
| `grounded-data` | BSL model + migrated dataset both exist | (the 7 already-shipped CLI-port pages) |
| `bsl-shell` | BSL model exists, dataset not yet materialized | `adoption-stage` (model already declared) |
| `no-bsl-shell` | BSL model doesn't exist yet | most of the 19 pages, until their model ships |
| `report-artifact` | Renders the LATEST cached run only; the dashboard never triggers a new run | `inventory-match`, `add-handoff`, `library-futures` (the FR-9 exceptions) |
| `live-scan-artifact` | The dashboard itself submits a brand-new per-invocation scan on user input | `scan-project`, `env-inspect` |

The `no-bsl-shell → bsl-shell` notation used throughout the per-page entries below is a **lifecycle annotation**, not a sixth literal value: it means "ships today as `no-bsl-shell`; becomes `bsl-shell` once its named BSL model lands" — Story 20.5 assigns whichever single value is literally true at merge time.

**Cross-cutting non-authoritative-badge + staleness-stamp rule (Top Concept 2):** every page whose primary content is a "likely / hint / report"-tier proposal (the 4 seed-gap suggesters, `mapping-gap`, `library-futures`' operator-override badges) renders that value with one consistent, non-authoritative visual marker (distinct styling from a verified/confirmed value) — this is stated once here and is not repeated per page. Every `report-artifact`- or `live-scan-artifact`-kind page additionally shows an "as of `<timestamp>`" staleness stamp as prominently as its data.

**19-page technical spine (full detail):** `DESIGN.md` §§ 3–6 — 8 atlas-CLI pages, 7 cyclonedx-suite pages, 4 seed-gap-suggester pages, each with Ports (legacy CLI(s) ported), BSL model, source dataset, layout, key columns, and corrected `kind`.

**19-page behavioral spine (full detail):** `EXPERIENCE.md` §§ 1–3 — same 19 pages, each with persona, POV statement, journey, interaction pattern, edge cases (including the report-artifact/live-scan-artifact three-state sets, the `adoption-stage` 0-package case, the `find-alternative` unknown-vs-no-alternative distinction, and the `distribution-breakdown` discoverability tooltip), and success metric. Includes the corrected cross-page navigation rule (triage→detail→remediation, AND the added `cve-watcher`→`library-futures` short-circuit).

### Key Features to Test

- The two-kind report-artifact split actually gives Story 20.5's implementer an unambiguous mapping from CLI to `PageDef.kind` (no page requires guessing).
- The non-authoritative badge renders identically across all 6 pages that need it.
- The `distribution-breakdown` onboarding tooltip is discoverable on first python-version-facet selection without being intrusive on repeat visits.
- Every report-artifact / live-scan-artifact page's three states (no-report-yet, report-available, failed/invalid-run) are each reachable and visually distinct.
- An MCP agent parsing any page's empty state gets a structured marker, not only prose.

---

## ✅ TEST: Validate with Users

### Testing Plan

No pages are built yet — Story 20.5 is the first to port real code against this spine — so there are no live users to run a usability test with (matching `EXPERIENCE.md` § 4's own acknowledgment of TEST's out-of-scope status for this planning pass). In place of live usability testing, this step runs a **persona walkthrough**: each of the 4 EXPERIENCE.md personas mentally walks each of their assigned pages' journeys against the PROTOTYPE spec, checking whether the journey resolves to their stated success metric without a dead end or an ambiguous state. This is a design-review technique, not a claim that real user testing occurred.

### User Feedback

Simulated walkthrough findings (persona-in-character, not fabricated real-user quotes):

- **Feedstock Maintainer (I), walking `cve-watcher`:** "The delta table answers 'what changed,' but I almost missed that zero-new-CVEs is a GOOD outcome — the neutral/positive empty-state phrasing (not the generic gap card) is what saves this." *(Confirms the existing edge-case decision; no change needed.)*
- **Consumer (III), walking `scan-project`:** "I need to know immediately whether I'm looking at my current scan or a stale cached one, and whether a bad manifest failed silently or actually errored." *(Directly motivates the failed/invalid-run state added to the two-kind taxonomy above.)*
- **Admin (II), walking `adoption-stage` on a small maintainer scope:** "With 0 packages the stacked bar shouldn't just look broken — it should say plainly there's nothing in scope yet." *(Motivates extending the "too few packages" fallback to explicitly cover 0, not just 1-2.)*
- **Curator (IV), walking `library-futures` and `mapping-gap` back to back:** "The override-badge and the suggester-tier badge look almost the same to me now that I think about it — good, that's the point, but only if it's actually the SAME badge component, not two similar-looking ones." *(Confirms Top Concept 2 must be a literally shared component, not independently re-implemented per page.)*

### Key Learnings

- The two-kind report-artifact taxonomy from DEFINE was validated, not just theorized — the consumer walkthrough independently arrived at needing a failed/invalid-run state, which only makes sense once "the dashboard triggers a live scan" is recognized as behaviorally different from "the dashboard shows a cached report."
- Edge-case completeness (0-packages, failed-run, unknown-vs-no-alternative) is not cosmetic polish — every walkthrough surfaced at least one incomplete-state gap, confirming these needed to be explicit rather than left to Story 20.5's improvisation.
- The cross-cutting badge and staleness-stamp rules only deliver their value if genuinely shared (one component/convention), reinforcing that DESIGN.md/EXPERIENCE.md must state them once, cross-cutting, rather than re-describe them per page.

---

## 🚀 Next Steps

### Refinements Needed

- Fold every TEST-phase finding above into `DESIGN.md`/`EXPERIENCE.md` before this story closes (kind taxonomy, badge/staleness rule stated once, 0-package fallback, failed/invalid-run states, unknown-vs-no-alternative distinction, discoverability tooltip, `cve-watcher`↔`library-futures` cross-link, add-handoff claim-marker forward note).
- Correct two internal cross-references in the prior DESIGN.md draft (wrong section pointers for the FR-9 exceptions list and for the `universe-sbom` EXPERIENCE.md reference) — corrected in the current DESIGN.md/EXPERIENCE.md revision.

### Action Items

- Land the corrected `DESIGN.md` + `EXPERIENCE.md` under `planning-artifacts/`, covering all 19 pages, with this workflow run as their cited source (Story 20.4, this session).
- Close `DW-D2-1` citing both spine files and this workflow artifact.
- Carry the already-recorded deferred item (19-vs-21 page-mapping re-verification) forward explicitly for Story 20.5, rather than letting DW-D2-1's closure imply the mapping is beyond question.

### Success Metrics

- Story 20.5's implementer can assign every one of the 19 pages a `PageDef.kind` without needing to guess or invent a taxonomy.
- Zero of the 21 remaining CLI questions are dropped (19 pages, one documented 3-into-1 consolidation, reconciliation table in `DESIGN.md` § 6).
- Every report-artifact/live-scan-artifact page reaches all three of its states in the design spec; no page's edge-case coverage is left to future improvisation on a happy-path-only design.

---

_Generated using BMAD Creative Intelligence Suite — Design Thinking Workflow (`bmad-cis-design-thinking`, persona: Maya)._
