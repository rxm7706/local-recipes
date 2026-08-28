# pyforge-atlas — EXPERIENCE.md (behavioral spine)

**Produced by:** the CIS Carson/Maya planning pass (Story 20.4, CAP-7), closing `DW-D2-1`. Carson
(`bmad-cis-agent-brainstorming-coach`) ran the divergent EMPATHIZE/IDEATE pass (recorded at
`_bmad-output/brainstorming/brainstorm-atlas-19-page-spine-2026-08-28/`); Maya
(`bmad-cis-agent-design-thinking-coach`) then ran the full `bmad-cis-design-thinking` workflow —
EMPATHIZE through TEST — recorded verbatim at
`_bmad-output/projects/pyforge-atlas/planning-artifacts/design-thinking-atlas-19-pages-2026-08-28.md`,
this document's authoring source.
**Companion:** `DESIGN.md` (technical/visual spine — BSL models, layouts, `PageDef` shapes).
**Scope:** the same 19 pages as `DESIGN.md` § 3–5. **Personas** are the 4 already established
in `reference/atlas-phases-overview.md` Part A — Maya's empathy pass deliberately reused them
rather than inventing a parallel taxonomy: **I. Feedstock Maintainer**, **II. conda-forge
Admin / Core Team**, **III. Consumer / Downstream User**, **IV. Cross-cutting /
Infrastructure**.

## 0. The design-thinking pass, in brief

Carson ran the divergent EMPATHIZE + IDEATE steps: for each of the 21 remaining CLI questions
(`DESIGN.md` § 0), who asks it, when, and what wild/broad framing of "a page that answers
this" comes to mind first — no filtering yet. Maya then ran the full `bmad-cis-design-thinking`
workflow (EMPATHIZE through TEST) end to end — DEFINE turned each divergent idea into a
"[Persona] needs [capability] because [insight]" POV statement; PROTOTYPE picked the
interaction pattern that serves that need with the fewest surprises (a filter + table for a
triage list; a single headline card for a classifier; a report viewer, never a live query, for
the three FR-9 exceptions). No real pages are built yet — Story 20.5 is the first to port real
code — so TEST ran as a **persona walkthrough** (each persona mentally walks their pages'
journeys against the prototype spec) rather than live usability testing; full detail at
`design-thinking-atlas-19-pages-2026-08-28.md` §§ TEST/Next Steps. Each page's entry below still
ends with the success metric Story 20.5's implementation should be judged against.

**Cross-cutting behavioral rules (apply to all 19 pages, not repeated per entry):**

- **Honest-empty is a UX contract, not just a data contract.** A page with no backing dataset
  yet shows a Card stating the gap plainly (mirrors `behind-upstream`/`whodepends` today) —
  never a spinner that never resolves, never a silently-blank grid.
- **No page requires memorizing a CLI flag.** Every filter the legacy CLI took as a flag
  (`--maintainer`, `--severity`, `--by-risk`, …) becomes a visible `Filter` control. The
  dashboard is the CLI's flag surface made discoverable, not a black box needing docs.
- **A write-path CLI still gets a read-only view.** For the FR-9 exceptions (and
  `mapping-gap`'s `--write` mode), the dashboard never triggers the write — the
  report-artifact pages exist so operators still SEE the last run without needing to
  re-invoke a write-path CLI from a terminal.
- **Cross-page navigation follows the maintainer's real workflow**, not the CLI list's
  alphabetical order: triage (staleness/CVE/adoption) links to detail
  (`detail-cf-atlas`/`version-downloads`/`release-cadence`) links to remediation
  (`find-alternative`/`add-handoff`). A second, distinct chain also exists: `cve-watcher` links
  directly to `library-futures` (§ 1.1, § 2.6) — a security lead deciding whether a CVE-flagged
  package is even worth keeping is a different decision from the detail/remediation chain above.
- **Non-authoritative values get one consistent badge (cross-cutting, stated once).** Every
  "likely / hint / report"-tier value — the 4 seed-gap suggesters (§ 3.1–3.4), `mapping-gap`
  (§ 2.2), and `library-futures`' operator-override badges (§ 2.6) — renders with the same
  visual marker, distinct from a verified/confirmed value. Not repeated per page below.
- **Report-artifact and live-scan-artifact pages both carry a staleness stamp.** Every page
  showing a cached or per-invocation report (`scan-project`, `env-inspect`, `inventory-match`,
  `add-handoff`, `library-futures`) shows "as of `<timestamp>`" as prominently as the data
  itself, and distinguishes three states: no-report-yet, report-available, and (for the two
  live-scan-artifact pages) a failed/invalid-run state.

---

## 1. Atlas-CLI pages (8)

### 1.1 `cve-watcher` — CVE Watch

- **Persona:** I. Feedstock Maintainer (primary); II. Admin/Core Team (channel-wide variant,
  `--only-increases` with no `--maintainer`).
- **POV:** "As a maintainer, I need to see WHICH of my packages got new CVEs since last week,
  because triaging security response by memory doesn't scale past a handful of feedstocks."
- **Journey:** land on the page → the maintainer/severity/since-days filters default to "me,
  all severities, 7 days" → scan the delta table sorted by `delta` descending → click a row to
  jump to `detail-cf-atlas` for the full health card → decide fix-now vs. watch.
- **Interaction:** filter row always visible (not hidden behind an "advanced" toggle — this
  IS the primary interaction); delta column color-coded (red increase, gray flat, green
  decrease).
- **Cross-link:** a direct link to `library-futures` (§ 2.6) for the security-lead decision
  "is this CVE-flagged package even worth keeping" — a distinct chain from the
  triage→detail→remediation flow above (see cross-cutting navigation rule).
- **Edge case (UX):** zero new CVEs this window is a GOOD outcome — the empty state reads "No
  new CVEs in the selected window" with a neutral/positive tone, not the generic "no data"
  gap card (this is a real, expected, happy answer — distinct from an unmaterialized-dataset
  gap).
- **Success metric:** a maintainer can answer "what changed since last week" without opening a
  terminal.

### 1.2 `version-downloads` — Version Downloads

- **Persona:** I. Feedstock Maintainer.
- **POV:** "As a maintainer, I need to see whether users have moved to my latest release,
  because a stalled adoption curve tells me something (a breaking change, a bad release) that
  a bare download total hides."
- **Journey:** arrive from `detail-cf-atlas`'s "view version history" link → see the adoption
  curve chart first (visual, immediate) → drop to the per-version table for exact numbers →
  toggle `--by-downloads` sort to find the actual most-used version (not always latest).
- **Interaction:** chart and table share one dataset; toggling the sort re-sorts the table
  only, the chart stays chronological (two different questions: "when" vs. "how much").
- **Edge case (UX):** a package with one version ever (no history) shows a single-bar chart +
  a one-row table, not an empty state — one data point is still data.
- **Success metric:** "which version should I tell users to pin" is answerable in one glance
  at the chart.

### 1.3 `release-cadence` — Release Cadence

- **Persona:** I. Feedstock Maintainer; II. Admin/Core Team (channel-wide "who's gone silent"
  sweep).
- **POV:** "As a maintainer, I need an honest label for my own release rhythm, because
  'accelerating vs. decelerating vs. silent' is a judgment call I'd rather the atlas make
  consistently than eyeball myself every quarter."
- **Journey:** land on the page → the trend-label Card is the FIRST thing seen (large,
  single word) → the window bar chart underneath explains WHY that label was assigned →
  maintainer either agrees and moves on, or drills into `version-downloads` if the label
  surprises them.
- **Interaction:** the headline label is deliberately not a number — a label is faster to
  parse than "1.3 releases/quarter" and matches the CLI's own output shape.
- **Edge case (UX):** "silent" (the CLI's actual classification for long-dormant packages) is
  phrased plainly, not softened — a maintainer deciding whether to archive needs the honest
  word, not a euphemism.
- **Success metric:** the trend label alone (no drill-down needed) is enough to decide
  "keep watching" vs. "investigate."

### 1.4 `find-alternative` — Find Alternative

- **Persona:** III. Consumer/Downstream User (primary — "my dependency got archived, now
  what"); I. Feedstock Maintainer (secondary — deciding what to recommend to users before
  archiving their own package).
- **POV:** "As a downstream consumer, I need a ranked, healthy replacement for an archived
  package, because manually searching conda-forge for 'something like X' is slow and
  unreliable."
- **Journey:** arrive with an archived package name already in mind (from `feedstock-health`'s
  `bad`/archived filter, or from their own build breaking) → type/select the name → scan the
  ranked candidate list → click through to that candidate's `detail-cf-atlas` before
  committing to a migration.
- **Interaction:** the similarity score renders as a visual bar (not a bare float) so ranking
  is scannable without reading numbers.
- **Edge case (UX):** two distinct empty states, not one — (1) a recognized-but-orphaned
  package with zero candidates found is a real, actionable answer ("no healthy alternative
  exists yet"), and (2) a package name not recognized in the catalog at all gets its own
  distinct message ("package not found — check the name"). Conflating the two would make a
  typo look like a real, actionable "no alternative exists" answer.
- **Success metric:** a consumer facing an archived dependency finds their next step without
  leaving the dashboard.

### 1.5 `adoption-stage` — Adoption Stage

- **Persona:** I. Feedstock Maintainer; II. Admin/Core Team (portfolio-wide lifecycle
  review).
- **POV:** "As an admin, I need to see the whole channel's lifecycle distribution at a glance,
  because 'how many packages are declining vs. thriving' is a portfolio question, not a
  per-package one."
- **Journey:** land on the distribution chart (stage counts) → click a stage segment
  (e.g. "declining") → the grid below filters to just that stage → from there, drill to
  `find-alternative` for candidates worth flagging.
- **Interaction:** click-to-filter on the chart itself (not a separate dropdown) — the chart
  IS the filter control, per Maya's "make ideas tangible quickly" principle applied to
  navigation, not just prototyping.
- **Edge case (UX):** a maintainer-scoped view with too few packages to make a meaningful
  distribution chart (0, or 1–2) falls back to a simple label list instead of a visually-empty
  or degenerate stacked bar — 0 packages states plainly "nothing in scope yet," distinct from
  the 1–2-package label-list fallback.
- **Success metric:** "where is my/the channel's portfolio trending" is answerable without
  per-package lookups.

### 1.6 `scan-project` — Scan Project

- **Persona:** III. Consumer/Downstream User.
- **POV:** "As a downstream user, I need to scan MY project's manifest/lock/image for known
  vulnerabilities before I ship, because catching this in the dashboard is faster than
  wiring a CI job just to check."
- **Journey:** arrive with a manifest path/upload in hand → submit → wait on the (per-
  invocation, not instant) scan → read the summary Card first (Critical/High/KEV counts) →
  drop to the per-package table for the fix list.
- **Interaction:** this is the one page in the atlas-CLI bucket where the user supplies input
  rather than just filtering a catalog — the UI must make that distinction obvious (an
  upload/path control front-and-center, not buried under filters that look like the other
  pages' catalog filters).
- **Edge case (UX):** three distinct states, not two — (1) no prior scan exists yet (fresh
  checkout): an explicit "no scan run yet, submit one above" state, distinct from the
  honest-empty catalog-gap card used elsewhere (an INPUT-needed state, not a DATA-missing
  state); (2) a scan ran and produced results; (3) the submitted manifest/lock/image was
  malformed or the scan itself errored — a distinct failed/invalid-run state, never silently
  folded into either "no scan yet" or an empty results table (a scan error is not the same
  answer as "nothing to report").
- **Success metric:** a consumer gets a go/no-go signal on their project without leaving the
  browser tab.

### 1.7 `env-inspect` — Environment Inspect

- **Persona:** III. Consumer/Downstream User.
- **POV:** "As a downstream user, I need a rollup of MY live environment's license and CVE
  exposure, because auditing an installed env by hand means cross-referencing a dozen
  packages manually."
- **Journey:** same per-invocation shape as `scan-project` — submit an environment reference →
  the three summary Cards (license / CVE / SBOM) load first → detail table on demand.
- **Interaction:** the three Cards are equal-weight and side-by-side (no single "primary"
  metric) — license compliance and CVE exposure are both first-class outcomes of this page,
  not one subordinate to the other.
- **Edge case (UX):** the same three states as `scan-project` § 1.6 — no-scan-yet (input-
  needed), report-available, and a distinct failed/invalid-run state (an unreadable environment
  reference is not the same answer as "nothing to report").
- **Success metric:** license + security exposure for a live env is visible in one screen,
  no separate `env-inspect --licenses` vs. `--security` invocations needed.

### 1.8 `distribution-breakdown` — Distribution Breakdown

- **Persona:** I. Feedstock Maintainer.
- **POV:** "As a maintainer, I need to see WHERE my downloads come from — which platform,
  which Python version, which channel — because three near-identical CLIs for one underlying
  question (`platform-breakdown`, `pyver-breakdown`, `channel-split`) made me run three
  commands to get one mental picture."
- **Journey:** land with "platform" as the default facet → switch the dimension selector to
  "python-version" → the chart re-renders instantly (same shape, new grouping) → if on the
  python-version facet, the `--policy-check` Card appears below, flagging bump-safe
  `python_min` candidates.
- **Interaction:** the dimension switch is a single control (radio/segmented control:
  Platform | Python Version | Channel), not three separate page links — this is the
  consolidation `DESIGN.md` § 3.8 justifies, made concrete as ONE interaction pattern instead
  of three learned layouts.
- **Edge case (UX):** the `--policy-check` sub-view is opt-in-by-facet (only appears under
  "python-version") rather than a fourth always-visible section — it answers a genuinely
  different question ("should I bump python_min") from the other two facets' pure reporting.
  Because folding three CLIs into one page risks burying this mode entirely, the FIRST time a
  user selects the python-version facet, a one-time onboarding tooltip calls out that the
  `--policy-check` view exists here — shown once, not on every subsequent visit.
- **Success metric:** a maintainer answers all three of "which platform," "which Python," and
  "which channel" questions from one page, one mental model.

## 2. Cyclonedx-suite pages (7)

### 2.1 `export-purls` — Export Purls

- **Persona:** IV. Cross-cutting/Infrastructure (SBOM tooling operators, other atlas
  consumers pulling purl artifacts programmatically).
- **POV:** "As an infrastructure operator, I need to confirm the six purl artifacts are fresh
  and find their location, because I regenerate downstream tooling off them and a stale
  artifact fails silently otherwise."
- **Journey:** land on the artifact grid → check each Card's regenerated-at stamp against
  "after every atlas rebuild" expectation → follow a download link if pulling an artifact
  manually.
- **Interaction:** the grid, not a table — six named, distinct artifacts is small enough that
  a Card-per-artifact glance beats a generic table.
- **Edge case (UX):** a stale (pre-last-rebuild) artifact is flagged visually (not just a
  date buried in text) — freshness is the whole point of this page.
- **Success metric:** "is this artifact current" is answerable at a glance, no need to
  cross-reference a rebuild log.

### 2.2 `mapping-gap` — Mapping Gap

- **Persona:** IV. Cross-cutting/Infrastructure (atlas data-quality maintainers).
- **POV:** "As the person who curates the conda↔PyPI mapping, I need to see WHAT the
  suggester found before deciding whether to accept it, because the mapping stays
  hand-curated by design and I don't want a dashboard that quietly writes to it."
- **Journey:** land on the classification-count summary → drop into the gap table → cross-
  reference against known packages → make the accept/reject call OUTSIDE the dashboard (via
  the CLI's `--write` + git review), per the CLI's own DRY-RUN-by-default contract.
- **Interaction:** deliberately no "accept"/"apply" button on the page — this reinforces
  that the dashboard is read-only here, matching the underlying CLI's own safety design.
- **Edge case (UX):** an empty gap list is a genuinely good state (the mapping is caught up)
  — phrase it that way.
- **Success metric:** a reviewer can triage mapping gaps visually before ever touching the
  CLI's `--write` flag.

### 2.3 `universe-sbom` — Universe SBOM

- **Persona:** III. Consumer/Downstream User (compliance/SBOM consumers); IV.
  Cross-cutting/Infrastructure (universe-scale tooling operators).
- **POV:** "As a compliance-focused consumer, I need to know the SHAPE of the whole
  conda-forge+PyPI universe (how much is mapped, how stale is the BOM) before I pull the full
  856k-component export, because downloading it blind to answer a scoping question wastes
  time."
- **Journey:** land on the summary Cards (total components, slice counts, freshness age) →
  pick a slice filter (actionable-only / mapped-only / …) → the paginated grid narrows → if
  freshness is beyond 14 days, a visible staleness warning appears before browsing further.
- **Interaction:** summary-first, browse-second — the ~856k-row scale means the page must
  answer the scoping question WITHOUT forcing a full-table render; pagination is a hard
  requirement here, not a nicety (this is called out explicitly since it's the one page in
  this spine where naive "show all rows" would break the experience).
- **Edge case (UX):** the >14-day staleness gate (the CLI's own `--allow-stale` escape hatch)
  surfaces as a dashboard banner, not a silent block — a consumer needs to know WHY the data
  might look old, not just that it does.
- **Success metric:** a consumer scopes their universe question (mapped vs. unmapped, fresh
  vs. stale) before committing to a full export.

### 2.4 `inventory-match` — Inventory Match (report-artifact)

- **Persona:** III. Consumer/Downstream User.
- **POV:** "As a consumer who already ran `inventory-match` against my manifest from the
  terminal, I need to SEE that result again later without re-running it, because the
  dashboard is where I check status, not where I kick off a new per-invocation match."
- **Journey:** land on the page → see the LAST run's bucket-count summary and per-package
  rows → if no run exists yet, an explicit "run `inventory-match <manifest>` to populate this
  view" instruction (never a live re-match triggered from the dashboard — FR-9's own
  boundary).
- **Interaction:** no "run new match" button — the page is a viewer, and the CLI invocation
  path is stated plainly when there's nothing to show, so the boundary is legible, not just
  enforced silently.
- **Edge case (UX):** a run that's aged out (the manifest has since changed) is not something
  this page can detect — it honestly shows the last-known result with its own timestamp,
  letting the user judge relevance themselves.
- **Success metric:** a returning consumer re-reads their last match result without leaving
  the browser or re-running the CLI.

### 2.5 `add-handoff` — Add Handoff (report-artifact)

- **Persona:** IV. Cross-cutting/Infrastructure (the `conda-forge-expert` agent workforce
  consuming the worklist; a human packaging operator secondarily).
- **POV:** "As the packaging agent picking up ADD-bucket work, I need the worklist visible
  without invoking a write-path CLI myself, because `add-handoff` is a write path and the
  dashboard should never trigger it — only show its last output."
- **Journey:** land on the worklist grid → scan readiness + license-blocker flags → pick the
  next package to hand to the recipe-authoring flow.
- **Interaction:** license-blocker rows are visually distinguished (fail-closed blockers are
  a hard stop, not a soft warning) — matches the CLI's own "fail-closed license blockers"
  design.
- **Edge case (UX):** two distinct states, not one — an empty worklist AFTER a real run
  (nothing in the ADD bucket right now) is a legitimate "caught up" state; no cached run
  existing AT ALL is a different state, with the same explicit "run `add-handoff` to populate
  this view" instruction used by `inventory-match` (§ 2.4) and `library-futures` (§ 2.6).
- **Forward-looking note (not implemented now):** the read-only constraint (FR-9) doesn't fully
  solve multi-agent coordination — two packaging agents could both pick up the same worklist
  row. A lightweight claim/lock sidecar (or at minimum a "last regenerated" + "in-progress
  elsewhere" flag) is a legitimate future need, recorded here for a future story — implementing
  it now would cross into write-path territory this story must not touch.
- **Success metric:** the next packaging candidate is identifiable without a terminal.

### 2.6 `library-futures` — Library Futures (report-artifact)

- **Persona:** III. Consumer/Downstream User (portfolio planning across a 2027–2030 horizon).
- **POV:** "As a consumer planning a multi-year dependency strategy, I need to see the LAST
  computed futures tier for each package I care about, because this scorer is intentionally
  in-memory/inventory-scoped — there's no live catalog column to query, only a cached run to
  view."
- **Journey:** land on the tier-badge grid → scan for `replace`-tier packages first (the ones
  needing action) → click through to `recommend-2027` for the full per-signal breakdown on a
  package of interest.
- **Interaction:** tier badges use consistent color coding across THIS page and
  `recommend-2027` (they share the same tier vocabulary) so a user moving between the two
  doesn't have to relearn a legend.
- **Cross-link:** direct navigation from `cve-watcher` (§ 1.1) — see that entry's cross-link
  note. Tier and operator-override badges follow the non-authoritative-badge cross-cutting rule
  (§ 0).
- **Edge case (UX):** no cached run exists — explicit "run `library-futures` to populate this
  view" instruction, same pattern as `inventory-match`.
- **Success metric:** the packages most urgently needing a migration plan are visible without
  re-running the scorer.

### 2.7 `recommend-2027` — Recommend 2027

- **Persona:** III. Consumer/Downstream User.
- **POV:** "As a consumer, I need the single scorecard that tells me which of my libraries
  survive 2027–2030 AND why, because a bare tier label without the per-signal breakdown
  doesn't let me judge whether I trust the verdict."
- **Journey:** land on the tier-distribution summary → drill into a specific package's row →
  expand the per-signal breakdown (py314 readiness, LTS/EOL horizon, operator overrides) →
  for `replace`-tier rows, the suggestion links straight to `find-alternative`.
- **Interaction:** per-signal breakdown is expand-in-place (not a separate page) — the whole
  point of this page over the bare `library-futures` tier list is the "why," so burying it
  behind another navigation click defeats the purpose.
- **Edge case (UX):** operator overrides are shown, never silent (the CLI's own contract) —
  an overridden tier displays an explicit "manually overridden" badge distinct from the
  computed tier.
- **Success metric:** a "replace"-tier verdict is never a black box — the breakdown answers
  "why" without leaving the row.

## 3. Seed-gap-suggester pages (4)

All four share one persona and one interaction shape (Maya's convergence, mirroring
`DESIGN.md` § 5's shared shape): **IV. Cross-cutting/Infrastructure** — the humans who
hand-curate `lts-registry.yaml`, `cwe_categories_seed.json`, `spdx.schema.json`, and the
`_LICENSE_TO_SPDX` map. Each page's journey is identical in shape: land on a proposal list →
scan tier/confidence → cross-reference against the curated file → make the accept/reject call
OUTSIDE the dashboard (git review), never via an "apply" button on the page — same read-only
discipline as `mapping-gap` § 2.2.

### 3.1 `lts-registry-gap` — LTS Registry Gap

- **POV:** "As the `lts-registry.yaml` curator, I need to see WHICH endoflife.date products
  aren't yet registered, tiered by confidence, because scanning the full product list by hand
  every time is exactly the toil this suggester exists to remove."
- **Edge case (UX):** a product already covered by the registry never appears here (the CLI
  excludes registry-covered names) — the list is always "genuinely new," never noise.
- **Success metric:** a registry-curation session starts from a pre-filtered candidate list,
  not a blank product catalog.

### 3.2 `cwe-seed-gap` — CWE Seed Gap

- **POV:** "As the CWE-seed curator, I need to see which `Other`-bucketed CWEs have real
  package impact, because triaging by impact count (not just alphabetically) tells me which
  reclassifications matter most."
- **Edge case (UX):** the "Other-bucket package-impact headline" Card is the entry point
  (impact-first), with the ranked CWE list below it — ordering communicates priority, not just
  data.
- **Success metric:** the curator's next reclassification is the top row, not something they
  had to find.

### 3.3 `spdx-schema-gap` — SPDX Schema Gap

- **POV:** "As the SPDX-schema curator, I need both 'what's new to add' AND 'is my vendored
  copy just stale' as separate questions, because those need different actions (add an enum
  value vs. re-vendor a whole file)."
- **Edge case (UX):** the `--drift`-only staleness view is a distinct mode/toggle on this
  page, not conflated with the add-to-schema proposal list — they're different curator tasks.
- **Success metric:** the curator can tell "add one enum" from "re-vendor everything" without
  reading CLI help text.

### 3.4 `license-map-gap` — License Map Gap

- **POV:** "As the `_LICENSE_TO_SPDX` map curator, I need unmapped raw license strings ranked
  by how many packages they affect, because a one-off license string affecting one package is
  a very different priority from one affecting hundreds."
- **Edge case (UX):** the suggested-SPDX-candidate column is a HINT, visually distinguished
  from a confirmed mapping (this suggester is conservative by design — "likely/report tiers"
  — and the UI must not make a hint look like an accepted fact).
- **Success metric:** the curator's next `_LICENSE_TO_SPDX` addition is the top-impact row,
  with its candidate SPDX id already suggested.

---

## 4. What this spine does NOT decide

Per this story's Boundaries, this spine does not implement any page, does not touch
`PAGE_INVENTORY`, and does not decide the exact Vizro widget wiring (that's `DESIGN.md`'s
technical detail plus Story 20.5's implementation judgment). Its TEST phase was a persona
walkthrough, not live usability testing — real usability testing needs actual built pages,
which for a 19-page planning pass with zero pages built yet is Story 20.5's job, not this one's.
