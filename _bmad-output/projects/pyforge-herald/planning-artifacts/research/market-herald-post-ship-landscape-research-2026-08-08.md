---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '{planning_artifacts}/research/market-herald-updates-broadcast-analogues-research-2026-07-25.md (refreshed here)'
  - '{planning_artifacts}/research/market-and-requirements-analysis.md (partially superseded here)'
  - '{planning_artifacts}/retros/retro-herald-2026-08-08.md'
  - '{project-root}/docs/dreams/herald-moments-2-4-live-backend.md'
  - 'src/shared/packages/pyforge-herald/ (shipped code, Epics 1-12)'
workflowType: 'research'
lastStep: 5
research_type: 'market'
research_topic: 'Herald''s competitive/analogue landscape re-examined after ship (47/47 stories): which 2026-07-25 analogue findings still hold, what the 2026-08-01 requirements analysis got right and wrong, and how the shipped shape moves Herald''s closest market category from changelog automation to internal developer portals'
research_goals: 'Dated post-ship refresh of both prior market documents. Confirm-or-supersede each, and re-locate Herald in the landscape now that what shipped is a record-and-dashboard system rather than a broadcast pipeline.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: true
source_verification: true
project_slug: 'pyforge-herald'
---

# Research Report: Market (post-ship refresh)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Market
**Project:** pyforge-herald

> **Supersession map.** This report refreshes both prior market documents:
> `market-herald-updates-broadcast-analogues-research-2026-07-25.md` (the analogue
> scan — **still valid**, confirmed and extended in §2) and
> `market-and-requirements-analysis.md` (2026-08-01 — **partially superseded**: its
> Moments-2–4 status rows and unverifiable market sizing are corrected in §3; its
> Moment 1 requirements content remains the PRD's grounding and is not disturbed).
> Both files carry a one-line pointer here.

---

## 1. What changed between 2026-07-25 and today

Everything. On 2026-07-25 Herald was one settled spec (the Design↔Code bridge) plus
an unspecced "updates/broadcast" half. As of today Herald is **shipped, 47/47
stories** (retro, 2026-08-08): the `herald deck` bridge CLI (Epics 1–5) and the
Moments 2–4 CLI + web dashboard (Epics 6–12) — the latter built to a
**scaled-down architecture** (local JSON/markdown storage, operator-triggered CLI,
static-snapshot dashboard, no server) after a same-day scope correction, with the
originally-specced live backend preserved as a separate Dream
(`docs/dreams/herald-moments-2-4-live-backend.md`).

That pivot is market-relevant, not just technical: **what shipped is a different
product category than what was researched.** The 07-25 scan located Herald among
changelog-automation and release-comms tools (release-please, towncrier, Gitmore,
LaunchNotes) because the imagined product was `updates compile` + `broadcast`.
The shipped product — per-station records with lifecycles, review gates, and a
read-only dashboard over them — has a different nearest neighbor: the **internal
developer portal / engineering-visibility** category (§4).

## 2. The 2026-07-25 analogue scan — refreshed verdict: HOLDS, with one inversion

The four analogues and the pattern analysis remain accurate and useful; no finding
is factually stale. Three of its recommendations can now be scored against the
shipped code:

| 07-25 recommendation | Shipped outcome |
|---|---|
| **Do not** parse commit messages (release-please pattern) | **Followed.** Nothing in `progress.py`/`claims.py`/`notices.py` reads git history. |
| **Do not** adopt silently-failing, UI-only delivery (Slack Workflow Builder pattern); hold the structured-failure bar | **Followed by omission** — no delivery channel shipped at all, so the bar was never tested. The recommendation stands intact for whenever `broadcast` is built. |
| **Do** source from the factory's own telemetry (sprint-status, gate reports, ComplianceReports) — the claimed differentiator | **Inverted.** The shipped v1 sources from *operator-typed flags* (`herald progress <station> --update --shipped ... --token-spend ...`), not from telemetry. The "machine-authored fragments from telemetry" model — the one thing the scan called Herald's differentiator — is unimplemented. |

That third row is this refresh's most important market finding: **Herald's claimed
differentiator (telemetry-native sourcing) did not ship.** What shipped is closer
to towncrier's *curated* pole than the scan predicted — except the curator types
flags instead of fragment files. The differentiator is still available (the
telemetry sources named in 07-25 all still exist and are richer now — the sprint
ledger, loop journals, the Guildhall's generator inputs), and wiring CLI *defaults*
from them is a small, serverless step. Until then, competitive claims should not
cite telemetry-native sourcing as a shipped capability.

The scan's `broadcast` half remains at zero implementation and its analysis needs
no revision — it is simply still future work, now with a named home (the
live-backend Dream is the trigger/hosting prerequisite; LaunchNotes'
"one canonical artifact, many channel adapters" remains the right target shape,
and the shipped `--json` output on every read command is a plausible canonical
artifact for those adapters to consume).

## 3. The 2026-08-01 requirements analysis — refreshed verdict: PARTIALLY SUPERSEDED

`market-and-requirements-analysis.md` was written as pitch-expansion grounding.
Post-ship scoring:

**What it got right (keep):**
- The Moment 1 requirements core (FR-1..FR-10) tracked what was actually built:
  `herald deck seed/pull/status/watch/push` shipped as Epics 1–5, etag conflict
  discipline included (the transport spike proved the MCP path live against
  `api.anthropic.com` — 23 tools, intact 33,985-char design-system prompt; retro §2).
- The "Four Moments as continuous framework, Moment 1 sets the pattern" thesis —
  vindicated; Moments 2–4 did reuse the CLI/dispatcher/error-boundary pattern
  Epics 1–5 established.
- The dependency analysis's risk flags aged well: "Claude Design MCP availability"
  is exactly why four live proofs are still deferred (retro A5 — `/design-login`
  never available in the working session).

**What is now wrong or should be treated as non-authoritative (superseded):**
1. **Status rows.** Moments 2–4 listed as "Planned Tier 2 feature" — they are
   shipped (scaled down). Any reader should take status from the retro and
   `sprint-status-ledger.yaml`, not that file.
2. **Market sizing.** The $5.3B TAM build-up, "$8.2B Gartner 2026," "67% faster
   iteration / 62% less drift," and the Forrester/Adobe citations are unverifiable
   — no source URLs, and this refresh could not corroborate the specific figures.
   Consistent with this repo's standing rule that spec/research cost-and-size
   claims must be re-verified at intake
   (`feedback_bmad_verifies_spec_cost_claims.md`), treat Part II §2.2 of that file
   as illustrative narrative, not evidence. (The one figure this refresh *can*
   ground: the adjacent internal-developer-portal market is credibly described as
   a ~$2B+/yr category in 2026 trade coverage — §4.)
3. **Acceptance claims stated as plan.** Several FR acceptance criteria
   (9-station fleet seeding in <5m, WCAG 2.1 AA on all decks, pre-commit
   `.dc.html` read-only hooks, 95%-pixel roundtrip fidelity) were **not** all
   realized as stated; the shipped test evidence is the 614+-test suite and the
   per-story Review Triage Logs, which are the authoritative record of what was
   verified.

## 4. The landscape shift: Herald's nearest category is now the internal developer portal

Because what shipped is *records + scorecard-like dashboard* rather than
*compile + broadcast*, the relevant 2026 comparison set is the IDP category —
Backstage (CNCF, the open-source default), Port, Cortex, OpsLevel — a ~$2B+/yr
market where Gartner forecasts 80% of large engineering orgs running platform
teams by 2026 (up from 45% in 2022). The load-bearing concepts there map almost
1:1 onto Herald's shipped surface:

| IDP concept | Herald equivalent |
|---|---|
| Service catalog entity | Station (the 8-Smith roster) |
| Scorecard / maturity check per entity | Progress record per `(station, date)` with cost fields |
| Initiative tracking ("crash-free releases") | Success claim with evidence + review gate |
| Ownership / lifecycle metadata, deprecation tracking | Operations notices with typed lifecycle + archive |

Three lessons from that category, applied:

1. **Scorecards are attested-vs-derived battlegrounds there too.** Port/Cortex
   sell *automated* checks against live integrations; Backstage's community
   scorecard plugins that rely on hand-entry are exactly the ones that go stale.
   The category's experience supports this refresh's core caution: Herald's
   operator-attested records need either automation (the live-backend Dream) or
   visible freshness signals to stay credible.
2. **Under-operated portals die.** The 2026 comparisons consistently warn that an
   understaffed Backstage deployment "ends up unused within six months." Herald's
   equivalent staffing cost is the operator discipline of running
   `--update`/`create`/snapshot-export by hand — small, but nonzero and
   recurring, and currently carried by one person.
3. **Nobody in the category does narrative.** IDPs surface state; none of them
   *proclaim* — no IDP writes the release announcement, attaches evidence to a
   shipping claim, or archives an end-of-life story. Herald's Moments 3–4, even
   scaled down, occupy a genuinely empty intersection: **portal-shaped state with
   claim-shaped narrative.** Combined with the still-unbuilt telemetry sourcing
   and broadcast fan-out, the defensible positioning is unchanged in spirit from
   07-25 but sharper: *the proclamation layer IDPs don't have, fed by telemetry
   changelog tools don't see.*

Herald is also **not competing** in this market — it is a single-factory internal
station. The category matters as a design reference and as validation that the
problem (engineering visibility at fleet scale) is real enough to sustain a
multi-vendor market, not as a go-to-market claim.

## 5. Refreshed divergence summary (what to borrow / avoid, 2026-08-08 edition)

- **Borrow** (unchanged from 07-25): towncrier's small-units-aggregate shape,
  narrative-over-raw-list digests, LaunchNotes' one-artifact/many-adapters
  delivery.
- **Borrow** (new): IDP scorecard freshness UX — surface *when a record was last
  attested* as prominently as the record itself; an empty/stale state must read
  as "unreported," never as "nothing happened."
- **Avoid** (unchanged): commit-message parsing; UI-only silently-failing
  delivery.
- **Avoid** (new): shipping delivery channels before the freshness problem is
  solved — broadcasting stale attested records is worse than not broadcasting;
  the category's stale-scorecard failure mode confirms it.

## Sources

- Prior internal research: `market-herald-updates-broadcast-analogues-research-2026-07-25.md`; `market-and-requirements-analysis.md` (2026-08-01)
- Internal ground truth: `retros/retro-herald-2026-08-08.md`; `docs/dreams/herald-moments-2-4-live-backend.md`; shipped code under `src/shared/packages/pyforge-herald/`
- External (IDP category, 2026):
  - [Port vs Backstage vs Cortex: We Evaluated All 3 (2026) — Tasrie IT](https://tasrieit.com/blog/port-vs-backstage-vs-cortex-developer-portal-comparison-2026)
  - [Backstage vs Port vs Cortex (2026) — TeKanAid](https://tekanaid.com/posts/backstage-vs-port-vs-cortex-internal-developer-portal-comparison-2026)
  - [Best Internal Developer Platform Tools 2026 — KubernetesGuru](https://kubernetesguru.com/internal-developer-platform-tools-2026/)
  - [Internal Developer Portals — Gartner Peer Insights](https://www.gartner.com/reviews/market/internal-developer-portals)
  - [What are Scorecards? — Port](https://www.port.io/guide/scorecards)
  - [Top internal developer portals in 2026 — Northflank](https://northflank.com/blog/top-internal-developer-portals)
