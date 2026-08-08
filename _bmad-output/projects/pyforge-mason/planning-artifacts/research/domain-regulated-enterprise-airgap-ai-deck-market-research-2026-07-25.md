---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md'
  - '{project-root}/docs/dreams/presenton-pixi-image.md'
workflowType: 'research'
lastStep: 6
research_type: 'domain'
research_topic: 'Regulated-enterprise / air-gapped AI-deck-generation market — domain context for presenton-pixi-image'
research_goals: 'Verify/sharpen the pre-existing PRD draft claims on Risk R3 (Microsoft on-prem Copilot threat + 12-24mo window), OCP adoption in this buyer segment, and comparable-product positioning.'
user_name: 'rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: 'headless-express'
---

# Research Report: Regulated-Enterprise / Air-Gapped AI-Deck-Generation Market

**Date:** 2026-07-25
**Author:** rxm7706 (headless BMAD run)
**Research Type:** Domain

---

> **Scope status (annotated 2026-08-08, station research refresh):** This report belongs to
> the **Presenton satellite** (`docs/dreams/presenton-pixi-image.md` — **archived**, blocked
> on its own unresolved Phase-0 decision gate), NOT to the `mason` CLI product that the rest
> of this planning chain describes. It is not a stale pivot of Mason's scope: per the
> 2026-08-02 consolidation (recorded in `docs/dreams/pyforge-mason.md` § "Related but out of
> scope"), the Presenton effort's planning artifacts were folded into this station's
> documents as "Satellite: Presenton" sections while the Dream itself stayed archived and
> blocked. This report shares no architecture, code, or timeline with Epics 1–5 of the mason
> CLI and informs **none of the 38 stories**. It was deliberately **not refreshed** in the
> 2026-08-08 research pass: its single Phase-0-blocking open question (whether Microsoft's
> disconnected Azure Local / M365 Local / Foundry Local stack includes a
> Copilot-for-PowerPoint-equivalent layer) gates the satellite, and re-researching it before
> the satellite unblocks would be wasted motion. Re-run this report's Microsoft-watch pass
> if and when the Presenton satellite's Phase-0 opens.

---

## Research Overview

This report tests the pre-existing PRD's Risk R3 ("Microsoft ships on-prem Copilot SKU — JTBD collapses overnight," framed as a 12–24 month window before "Microsoft Arc-connected Copilot reaches IL5 GA") against current, dated evidence. **The finding materially changes the risk posture**: the specific trigger the PRD names (IL5 GA) already happened without collapsing the JTBD — but a *different*, more direct trigger (Microsoft's own on-prem/disconnected stack: Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA'd worldwide **2026-02-24**) is already shipping, and this report could not confirm or rule out whether it includes Copilot-for-PowerPoint-equivalent deck generation. This is escalated to a Phase-0-blocking verification item, not a monitoring item. Full findings below.

## Executive Summary

**Key Domain Findings:**

- **Microsoft 365 Copilot cloud-government rollout is well past the PRD's "12-24 month window" framing, and the JTBD survived it — because IL5 GA was the wrong trigger to watch.** Official Microsoft sources (`adoption.microsoft.com/en-us/copilot/us-government/`, `techcommunity.microsoft.com` public-sector blog) confirm Microsoft 365 Copilot Chat is now generally available across **GCC, GCC-High, and DoD**; secondary coverage cites Copilot **Actions** reaching GA in GCC High/DoD in **June 2026**, and M365 Copilot in **DoD IL5** as an already-crossed milestone. None of this is on-prem or disconnected — every one of these tiers is **Azure Government cloud, network-connected to a segregated government cloud region**, not a true air gap. This confirms the PRD's underlying differentiator ("cloud-only, unavailable across the air-gap boundary") **still holds** — IL5 GA happening did not collapse the JTBD, because IL5 was never the real threshold. **The PRD's Risk R3 trigger condition should be corrected**: watching for "IL5 GA" was watching the wrong signal; the real signal is disconnected/on-prem availability, addressed next.
- **CRITICAL — Microsoft's actual on-prem/disconnected stack already shipped, 2026-02-24, and this IS the real R3 trigger.** Microsoft announced worldwide GA of three components together: **Azure Local disconnected operations**, **Microsoft 365 Local (disconnected)**, and **Foundry Local** (local multimodal-AI-model runtime, customer-controlled hardware, NVIDIA GPU support). This is confirmed via Microsoft's own Learn documentation (`learn.microsoft.com/en-us/azure/azure-local/manage/disconnected-operations-overview`, `ms.date: 2026-02-23`, updated `2026-06-23`) plus independent coverage (Thomas Maurer, Kenny Lowe — both recognized Microsoft MVP/community bloggers who cover Azure Stack HCI/Local closely). Azure Local disconnected operations is explicitly positioned for "government, healthcare, and finance" sovereign/data-residency needs, with "no network connectivity to Azure, no phone-home requirements" (Kenny Lowe's characterization, consistent with the official eligibility-criteria language: "organizations that can't connect to Azure because of connectivity issues or regulatory restrictions"). **This is a materially different and more dangerous R3 trigger than the PRD names**, and it is not a future risk — it is 5 months old as of this research date.
- **UNRESOLVED — whether the disconnected Microsoft stack includes Copilot-for-PowerPoint-equivalent deck generation could not be confirmed in this pass.** The `disconnected-operations-overview` page's "Supported services" table lists pure infrastructure primitives (Azure portal, ARM, RBAC, managed identity, Arc-enabled VMs/Kubernetes/AKS, Container Registry, Key Vault, Policy) — **no Copilot, no M365 apps, no AI service is named on that page.** Secondary sources describe "Microsoft 365 Local disconnected" as covering "productivity services" without confirming Copilot inclusion, and "Foundry Local" as AI-model-hosting infrastructure ("large multimodal models on customer-controlled hardware") without confirming a packaged deck-generation application on top of it. **Reading the pieces together: Microsoft has now shipped every infrastructure primitive needed to run a disconnected Copilot-equivalent (disconnected compute/K8s + disconnected M365 + local multimodal model hosting) but this research could not confirm the PowerPoint-generation application layer is actually turned on in the disconnected SKU today.** This is the single highest-priority open question this report surfaces — it should gate Phase 0, not wait for the yearly Microsoft-watch cadence the PRD already defines.
- **OCP is a credible, well-established substrate for this buyer segment — no need to hedge toward a more portable K8s target.** FedRAMP-authorized (multiple independent sources: Cabrillo Club, Precision Federal — the latter explicitly lists "OpenShift, and platform hardening for FedRAMP and DoD IL workloads" as a federal Kubernetes-engineering service line, implying real federal OCP deployments exist to harden). Market-sizing (Research and Markets, cited via search aggregation) pegs the *managed* OpenShift services market at ~$4.29B in 2026 growing to ~$10.99B by 2030 (26.5% CAGR) — broad enterprise adoption, not a niche. Landbase aggregator cites 6,633 verified companies using Red Hat OpenShift as of 2026. This is secondary/aggregator-sourced (not a primary Red Hat filing), so treat the specific numbers as directional, not authoritative, but the qualitative conclusion — OCP is a real, government-credible target, not a bet on an obscure platform — is well supported. **No change recommended to the PRD's OCP-first framing.**
- **Comparable self-hosted/on-prem long-form-summarization-to-deck products are not surfaced with regulated-buyer-specific positioning.** This mirrors the technical research pass's finding (§3 of the companion technical report): the three GitHub comparables found (`hugohe3/ppt-master`, `Cherzing/AIPPT`, `busto-dev/PepeteX`) are all cloud-LLM-API-dependent or don't publish air-gap/regulated-buyer material. No evidence surfaced of a direct competitor explicitly marketing "air-gapped AI deck generation for regulated enterprise" — consistent with the PRD's existing competitive-context conclusion that this positioning is currently uncontested. Domain research did not find grounds to revise that table.
- **Procurement-cycle / security-review SLA claims (JFrog-mirror-gated multi-week review) could not be independently verified externally** — this is an internal-process assumption specific to the buyer's own compliance program, not something publicly documented for a generic buyer profile. No correction is offered; flagged as an open question that Phase-0's JFrog-allowlist-gap-analysis exit criterion (already in the PRD) is the right place to resolve, not something domain research from public sources can settle.

**Domain Recommendations:**

1. **Rewrite Risk R3** to (a) correct the trigger condition — GCC/GCC-High/DoD/IL5 cloud GA already happened and did NOT collapse the JTBD, so stop watching for it — and (b) name the real trigger: Microsoft's disconnected Azure Local + M365 Local + Foundry Local stack, GA since 2026-02-24, with the open question of Copilot-deck-generation-layer inclusion elevated to a **Phase-0 blocking verification item**, not a yearly-cadence watch item.
2. **Re-anchor the "why now" / window-of-opportunity narrative.** The PRD's "12–24 months until Microsoft Arc-connected Copilot reaches IL5 GA" sentence is now falsifiable-and-false as a timing anchor (the named event happened without ending the opportunity) — replace with the corrected trigger from (1), and mark the window as **unknown-and-urgent** rather than a comfortable 12–24 month runway, pending the Phase-0 verification.
3. **Task the existing Microsoft-watch mechanism (yearly + gate-coupled + always-on RSS) to fire immediately, out of cycle**, per its own always-on RSS/keyword-filter design (`on-prem`, `sovereign`, `air-gap`, `disconnected` are literally the keywords already specified) — this finding is exactly what that mechanism was built to catch, and it should have already fired for the 2026-02-24 announcement. Note this as evidence the watch mechanism needs backfilling/backtesting against past announcements, not just forward monitoring.
4. No changes recommended to the OCP-first platform decision or the competitive-context table.

---

## 1. Microsoft 365 Copilot — Government Cloud Rollout Status (2026)

Source: `adoption.microsoft.com/en-us/copilot/us-government/` (official Microsoft adoption site) — confirms Copilot Chat GA across **GCC, GCC-High, DoD**; page contains **zero references** to on-premises, air-gapped, disconnected, or offline deployment — everything described is Azure Government cloud, network-connected. This is a directly-fetched primary source (WebFetch on the live Microsoft URL), high confidence.

Secondary corroboration (search-result snippets, not independently fetched in full — medium confidence, consistent with each other):
- `techcommunity.microsoft.com/blog/publicsectorblog/microsoft-365-copilot-is-now-available-in-gcc-high/4473310` — official MS public-sector blog confirming GCC-High availability.
- Windows Forum coverage: "Microsoft 365 Copilot Actions Launch in GCC High and DoD (June 2026)" — Actions capability reaching GA in that window.
- LinkedIn (Johnny Burton Sr.) — "M365 Copilot Arrives in DoD IL5."

**Conclusion:** the PRD's named trigger event (IL5 GA) has, per available evidence, already occurred or is imminent as of this research date — **and the product's core differentiator (cloud-only Copilot cannot cross the air gap) is unaffected**, because every one of these tiers remains Azure-cloud-hosted. The PRD was watching the right *category* of risk but the wrong specific *signal*.

## 2. Microsoft's Actual On-Prem/Disconnected Stack — The Real Trigger

Primary source: `learn.microsoft.com/en-us/azure/azure-local/manage/disconnected-operations-overview` (fetched in full). Frontmatter confirms `ms.date: 2026-02-23`, `updated_at: 2026-06-23` — an actively-maintained, current doc, not a stale draft.

- **What it is:** "Disconnected operations for Azure Local enable you to deploy and manage Azure Local instances without a connection to the Azure public cloud... by using select Azure Arc-enabled services from a local control plane."
- **Explicit target segment:** "In sectors like government, healthcare, and finance, you have data residency and sovereign requirements... When you run disconnected, data, operations, and control remain within your organization's boundaries." This is a verbatim match to this project's buyer profile.
- **Supported services (full list from the page):** Azure portal, ARM, RBAC, managed identity, Arc-enabled servers/VMs, Arc-enabled Kubernetes (preview), AKS-Arc (preview), Azure Local device management, Container Registry, Key Vault, Policy. **This is infrastructure — no AI, Copilot, or M365 service is named in this table.**
- **Eligibility gating:** requires an eligible Microsoft agreement (MOSA excluded), an active Standard-or-higher support plan, a documented "valid business need," and a pre-qualification form with up to 10-business-day approval — i.e., this is not self-service; it's a gated enterprise motion, structurally similar to the buyer-gate procurement pattern this PRD already assumes.

Companion products announced alongside (search-snippet sourced, not independently fetched — medium confidence):
- **Microsoft 365 Local (disconnected)** — "Azure Local disconnected operations and Microsoft 365 Local disconnected are now available worldwide," described as covering "productivity services" in air-gapped environments. Copilot inclusion **not confirmed** by any source found in this pass.
- **Foundry Local** — "support for large multimodal models on customer-controlled hardware," NVIDIA GPU support named. This is Microsoft's own local-AI-model-hosting runtime — architecturally the same role this project's Tier-2 `llama.cpp` sidecar plays, but shipped by Microsoft itself.

**Assessment:** Microsoft has, as of 2026-02-24, shipped every *infrastructure* building block (disconnected compute/K8s, disconnected M365, local multimodal model hosting) needed to assemble a disconnected Copilot-equivalent. What is **not confirmed** is whether the PowerPoint-generation *application layer* — the actual Copilot skill this product's JTBD is priced against — is live in that disconnected bundle today, partially available, or still cloud-only pending a future release riding on this now-shipped infrastructure. Both are plausible reads of the same evidence; this report cannot resolve it further without either (a) a Microsoft licensing/product conversation, or (b) hands-on access to a Microsoft 365 Local disconnected deployment, neither of which is available to this research pass.

## 3. OCP in the Regulated/Air-Gapped Buyer Segment

Search-aggregated (medium confidence — secondary/aggregator sources, not primary Red Hat data; two independent direct WebFetch attempts against `redhat.com` government-focused pages both 404'd, likely stale/renamed URLs guessed by this research rather than a content issue):

- **FedRAMP posture:** cited by multiple independent secondary sources as FedRAMP-authorized; Precision Federal (a federal Kubernetes-engineering vendor) lists OpenShift alongside "EKS in AWS GovCloud, AKS in Azure Government, GKE... for FedRAMP and DoD IL workloads" as a real service line — implying actual federal OCP deployments exist in the wild needing this hardening work, not a theoretical capability.
- **Adoption scale:** Landbase aggregator — 6,633 verified companies using Red Hat OpenShift (2026); Research and Markets — managed-OpenShift-services market ~$4.29B (2026) → ~$10.99B (2030), 26.5% CAGR.

**Conclusion:** OCP is a legitimate, well-evidenced platform choice for this buyer segment. The PRD's OCP-first framing needs no hedge toward a more generic/portable Kubernetes target based on this evidence — though the underlying numbers are aggregator-sourced and should be treated as directional context, not cited as precise facts in buyer-facing material.

## 4. Comparable Products — Regulated-Buyer Positioning

No material beyond what the companion technical research report already surfaced (`hugohe3/ppt-master`, `Cherzing/AIPPT`, `busto-dev/PepeteX` — see that report's §3). None publish air-gap or regulated-enterprise-specific positioning; the competitive white space the PRD already claims (intersection of Copilot-class capability + survives-security-review, currently unaddressed) is not contradicted by anything found here.

## 5. Procurement Cycle / Security-Review SLA

Not independently verifiable from public sources — this is inherently buyer-specific internal process, not a publishable industry norm. No correction offered to the PRD's JFrog-mirror-gated multi-week-SLA assumption; the PRD's own Phase-0 exit criterion 4 ("JFrog allowlist gap analysis filed") is the correct mechanism to resolve this per-buyer, and domain research from public sources cannot substitute for it.

---

## Source Verification

**Primary sources (fetched directly, this research pass, 2026-07-25):**
- `adoption.microsoft.com/en-us/copilot/us-government/` — full WebFetch.
- `learn.microsoft.com/en-us/azure/azure-local/manage/disconnected-operations-overview` — full WebFetch (frontmatter + complete body).

**Secondary sources (search-snippet level, not independently fetched in full — medium confidence, used only where internally consistent across multiple independent outlets):**
- `techcommunity.microsoft.com/blog/publicsectorblog/...` (official MS blog, title+existence confirmed, body not retrieved).
- `windowsforum.com` (2 threads — Copilot Actions GCC-High/DoD GA; Azure Local/M365 Local/Foundry Local GA announcement).
- `www.linkedin.com/pulse/...` (M365 Copilot DoD IL5).
- `www.thomasmaurer.ch`, `www.kennylowe.org` (independent Microsoft MVP/community coverage of Azure Local disconnected operations).
- Aggregator sources for OCP adoption: 6sense.com, Landbase, Datanyze, Research and Markets, Cabrillo Club, Precision Federal.

**Failed fetch attempts (recorded for transparency):** `microsoft.com/en-us/microsoft-365/copilot/government` (404), `redhat.com/en/technologies/cloud-computing/openshift/government` (404), `redhat.com/en/red-hat-openshift-government-cloud` (404), `docs.redhat.com` SCC page (403) — these were guessed URLs, not confirmed dead content; the information gap was filled via search-aggregation instead.

**Methodology note:** the `WebSearch` tool's session budget was exhausted before this research began (200/200, consumed by prior session activity). All findings were produced via `WebFetch` — including on `html.duckduckgo.com/html/?q=...` as a search-substitute, since the native `WebSearch` tool was unavailable — plus direct fetches of official Microsoft/OpenShift documentation. This is a workaround, not the intended tool, and DuckDuckGo HTML snippets are lower-fidelity than the `WebSearch` tool's normal output (no guaranteed snippet completeness or ranking transparency); treat the search-snippet-sourced claims in §§1–3 as medium confidence and prioritize the two directly-fetched primary sources when weighing this report against the PRD.

**Confidence levels:**
- **High confidence:** Microsoft 365 Copilot GA across GCC/GCC-High/DoD cloud tiers, with zero on-prem/disconnected mention (primary source, directly fetched). Azure Local disconnected-operations infrastructure scope and target segment (primary source, directly fetched, dated frontmatter).
- **Medium confidence:** Microsoft 365 Local + Foundry Local existence, GA date (2026-02-24), and general capability framing (multiple independent secondary sources, internally consistent, but not independently primary-fetched).
- **Unresolved / flagged for Phase-0:** whether the disconnected Microsoft stack includes a Copilot-for-PowerPoint-equivalent deck-generation application layer today. This is the report's single most consequential open question.

---

## Open Questions Surfaced By This Research

1. **[BLOCKING — escalate to Phase-0 exit criteria]** Does Microsoft 365 Local (disconnected, GA 2026-02-24) include Copilot deck/PowerPoint generation today, or is it Office-apps-without-Copilot pending a future release? This single fact determines whether Risk R3 has already fully materialized (JTBD collapsed), partially materialized (infra ready, app layer pending — a true "window" exists but its length is unknown, not 12-24mo), or not materialized (Foundry Local + M365 Local remain infrastructure-only, no packaged deck-gen competitor yet).
2. Does the existing always-on RSS/keyword-filter Microsoft-watch mechanism (already specified in the PRD, keywords `on-prem`/`sovereign`/`air-gap`/`disconnected`) actually cover Azure/`learn.microsoft.com` product-doc channels, or only the M365-roadmap/Copilot-blog channels named in the PRD text? The 2026-02-24 announcement should have tripped this filter — if it didn't, the watch mechanism has a channel-coverage gap that needs fixing before Phase-0 close, not after.
3. Are there other Microsoft "Local"-branded or Arc-enabled AI products (beyond Foundry Local) worth a dedicated inventory pass — this research sampled the two most search-visible ones but did not attempt an exhaustive sweep of Microsoft's on-prem AI product surface.

---

**Research Completion Date:** 2026-07-25
**Source Verification:** Primary sources directly fetched where possible; secondary sources cross-checked for internal consistency across independent outlets where primary access failed or was unavailable (WebSearch budget exhaustion).
**Confidence Level:** High for the GCC/GCC-High/DoD-is-still-cloud finding; Medium-and-urgent for the Azure Local/M365 Local/Foundry Local finding — treat as the headline delta for the PRD revision regardless of the medium-confidence caveat, given its magnitude if confirmed.
