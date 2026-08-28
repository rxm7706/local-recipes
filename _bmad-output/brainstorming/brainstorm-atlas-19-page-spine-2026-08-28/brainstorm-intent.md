# Brainstorm intent: Vizro page/interaction ideas for the 21 unaddressed pyforge-atlas legacy-CLI read-questions

## Goal
Feed Story 20.4's DESIGN.md/EXPERIENCE.md two-spine specs (Carson divergent pass, headless).

## Adopted directions
- Add staleness stamps ("as of \<timestamp\>") to every report-artifact page.
- Add a cross-cutting non-authoritative badge for every likely/report/hint-tier row (seed-gap suggesters, mapping-gap, library-futures overrides), distinct from verified/confirmed values.
- Add the extra cross-link: cve-watcher → library-futures directly, for a security lead deciding whether a flagged package is worth keeping.
- Add a discoverability affordance (e.g. one-time onboarding tooltip) for pyver-breakdown's policy-check mode inside the merged distribution-breakdown page.
- Record add-handoff's claim-marker as a forward-looking note (lightweight claim/lock sidecar for multi-agent coordination) without implementing it now.
- None of the above adds or removes a page from the existing DESIGN.md/EXPERIENCE.md page set.

## Deliberately deferred (out of scope)
- Vizro-AI natural-language query box — belongs to the later Story D3 wave, not this story.
- Drag-and-drop composable pages/widgets replacing fixed routes — a platform-level rethink, bigger than a Story 20.4 decision.
- A "propose a PR" bot for the seed-gap suggesters — turns a read-only surface into a write path (FR-9-adjacent).
- Merging distribution-breakdown/adoption-stage/release-cadence into one mega "Package Vitals" page — over-consolidates past what 3 independent CLIs justify.

## Key insights
- Report-artifact pages (scan-project/env-inspect/inventory-match/add-handoff/library-futures) need both a staleness stamp and a labeled sample/placeholder for a fresh checkout — a bare "no data" card reads as broken, not "not yet run."
- The non-authoritative-badge rule should be cross-cutting, not per-page — one consistent visual treatment for every likely/report/hint-tier value.
- Cross-page navigation should follow real incident-response chains (e.g. cve-watcher → library-futures), not just the already-documented triage-to-detail chain.
- The distribution-breakdown 3-into-1 merge is validated by two independent techniques but creates a real discoverability risk for pyver-breakdown's policy-check mode — needs an explicit UX affordance, not just a facet switch.
- add-handoff's read-only constraint (FR-9) doesn't fully solve multi-agent coordination; a lightweight claim marker is a legitimate forward-looking gap, but implementing it now would cross into write-path territory this story must not touch.

## Notable ideas (selective, not exhaustive)
- Generic "CLI Report Viewer" page type parameterized by CLI name, reused across all per-invocation/report-artifact CLIs instead of one bespoke page each.
- Shared "ranked list + summary card" template for classifier CLIs (adoption-stage, release-cadence, find-alternative) — same shape, different measure.
- "Breakdown Explorer" page with a facet selector, generalizing platform/pyver/channel breakdown into one reusable, extensible widget.
- "Curator Console" page unifying the 4 seed-gap suggesters via a single source-file selector (they share the same read-only proposal-list shape).
- "Security Posture" super-page combining cve-watcher + scan-project + env-inspect, since all three answer "am I exposed" from different angles.
- Version every page's BSL model like a dataset contract (semver) so Story 20.5 can build against a frozen shape while DESIGN.md iterates.
- Maintainer-switcher dropdown on cve-watcher so the same page serves both the single-maintainer and the admin channel-wide-sweep persona.
- Pre-fill find-alternative from the last in-session scan-project failure, for the consumer arriving in a panic after a broken build.
- Bulk CSV/SBOM export button next to recommend-2027's summary card, for a portfolio owner running it across 40 libraries.
- Datadog-style green/warn/critical color language for cve-watcher and adoption-stage, so severity reads instantly without a legend.
- Hard-cap unpaginated preview rows and force a slice filter before universe-sbom's AgGrid renders (~856k rows would otherwise hang the tab).
- npm-audit-style first line on scan-project's summary card: "N vulnerabilities, M auto-fixable."
