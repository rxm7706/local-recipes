---
title: Product Brief - presenton-pixi-image
status: draft
created: 2026-07-25
updated: 2026-07-25
---

# Product Brief: presenton-pixi-image

## Executive Summary

`presenton-pixi-image` repackages the open-source Presenton AI deck-generation app as a fully air-gapped OCI image deployable on Red Hat OpenShift Container Platform (OCP), built from conda-forge-native recipes and assembled via pixi + pixitainer, with no LibreOffice and no non-conda-forge packages in the runtime. It exists for one reason: regulated enterprises (govtech/fintech/defense-adjacent) whose data classification prohibits the cloud version of Microsoft 365 Copilot are stuck producing decks by hand — slower, and systematically worse in language and style, than LLM-assisted tooling. Nobody has cleared the intersection of *Copilot-class capability* and *survives security review* for this segment. This product does, by construction: every dependency resolved from governed channels, every image reproducible, no call home.

The core claim — Copilot-class capability the buyer is *allowed to install* — is unusually well-timed and unusually urgent at the same time. Presenton is mature enough to repackage cleanly; conda-forge's Chromium-bundling pattern and the pixi/rattler-build toolchain make the air-gap posture achievable in 2026. But Microsoft is not standing still: as of 2026-02-24 Microsoft shipped its own disconnected/on-prem stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local) aimed at exactly this buyer. Whether that stack already includes a Copilot-for-PowerPoint-equivalent is unconfirmed — and that single unknown is now the most consequential open question this project carries into Phase 0.

## The Problem

An analyst in a SCIF, a compliance officer at a regional bank, a program manager on a classified contract — all need to turn a 40-page internal document into a board-ready deck, and none of them can reach the cloud to do it with AI assistance. Today they build by hand: slower than LLM-assisted peers elsewhere in the org, and the output is systematically weaker in structure and language. The tools that would help — Marp, python-pptx + Jinja2 templates — clear procurement trivially (pure local code, zero exfiltration risk) but fail the actual job: they stamp templates, they don't summarize long-form source material into a reviewable draft. The tool that *would* do the job, Microsoft 365 Copilot for PowerPoint, is cloud-only with no on-prem or disconnected path for this data-classification tier.

The buyer (CISO/platform engineering) and the end user (the analyst) want different things from the same purchase, and both have to be satisfied or the deal doesn't renew: the buyer needs zero exfiltration paths and zero unreviewed dependencies to approve it once; the user needs a draft worth editing, not a template worth ignoring.

## The Solution

Six (now provisionally five-to-seven, pending Phase-0 decisions — see Scope) conda-forge recipes replace every opaque or LibreOffice-dependent piece of the Presenton pipeline with source-available, air-gap-buildable components: a clean-room Playwright-based export runtime, a PPTX assembler, a thumbnail injector, a bundled-Chromium recipe, and the `llmai` provider-abstraction library Presenton already depends on. These compose into one OCI image, deployed via a standard Helm chart on OCP, consuming any OpenAI-compatible LLM endpoint as configuration — an internal corporate proxy (Tier 1, the default), a bundled `llama.cpp` sidecar (Tier 2), or an init-container model fetch from an internal registry (Tier 3). A sideloadable VS Code extension (`copilot-bridge`, already speced and built for this repo) covers the developer inner-loop. New research materially simplified this scope: upstream Presenton has already solved template import without LibreOffice, using nothing but the Python standard library and `pdfplumber` — so one of the originally-planned recipes disappears from v1 scope entirely, and the corresponding LibreOffice-licensing risk (PyMuPDF/AGPL) goes with it.

## What Makes This Different

Nothing else clears both halves of the bar at once. Marp and python-pptx+Jinja2 clear provenance but not capability. LibreOffice Impress plus local LLM plugins can deploy air-gapped but has no integrated agent-orchestration UX for deck-class workflows. SlidesGPT, Gamma, and Tome are SaaS — air-gap-incompatible by construction, though they shape what "good" looks like for end users. `hugohe3/ppt-master` is architecturally interesting (SVG→DrawingML) but requires an external LLM API and cannot deploy inside a perimeter. Two additional self-hosted comparables surfaced during research (`Cherzing/AIPPT`, `busto-dev/PepeteX`) neither publishes regulated-buyer or air-gap-specific positioning — this remains, as far as this research can tell, uncontested ground.

The honest version of the moat: it isn't a secret algorithm, it's the supply-chain work. Today the customer would have to integrate six unsigned upstream artifacts (a closed-source export binary, a closed-source PyInstaller converter, a browser binary nobody ships on conda-forge, an LLM abstraction library, and more) and own that integration risk themselves. With this, they integrate one signed OCI image with one SBOM and we own it. That's the actual product.

**The one thing that could erase this overnight, and where it stands today:** Microsoft's cloud government rollout (GCC/GCC-High/DoD/IL5) is well underway and does *not* threaten this product — none of it is disconnected. But Microsoft's own on-prem/disconnected infrastructure stack (Azure Local disconnected operations, Microsoft 365 Local, Foundry Local) went GA worldwide on 2026-02-24, five months before this brief was written. The infrastructure pieces needed to assemble a disconnected Copilot-equivalent are now all shipped by Microsoft directly. Whether the actual PowerPoint-generation application layer rides on top of that stack today is **unconfirmed** — Phase 0 must resolve this before committing further build investment, not defer it to a yearly monitoring cadence.

## Who This Serves

- **Buyer** — CISO / platform engineering director owning the OCP cluster. Signs once; needs a turnkey, mirrorable image with zero exfiltration paths and zero unreviewed dependencies.
- **Analyst (renewal-driving user)** — turns a 40-page internal document into a 12-slide draft "I'd rather edit than write from scratch," without leaving the secure workstation. Quality bar is *better than writing it by hand at 2am*, explicitly not M365-Copilot parity.
- **OCP operator (day-0 / day-2)** — deploys via Helm, configures the LLM provider tier, later rotates credentials and responds to CVEs and pinned-dependency breaks.
- **Recipe-maintainer** (us) — tracks upstream Presenton drift (six-plus clean-room artifacts = six-plus divergence vectors); wears a "fixture maintainer" hat during periodic online-capture sessions.
- **VS Code developer** — sideloads the `copilot-bridge` extension for a local OpenAI/Anthropic-compatible dev loop; JetBrains developers get a docs-only fallback in v1.
- Out of scope: the end web user of upstream Presenton (we don't touch its UI), and the JetBrains-native plugin (deferred to v2).

## Success Criteria

Two gates that don't collapse into each other, because either one failing kills the product on its own axis:

- **Buyer-gate (binary, procurement-visible):** all recipes upstream-merged on conda-forge → landed on the customer's JFrog Artifactory mirror → OCI image on the customer's registry; SBOM (CycloneDX + SPDX) and a signed-image (cosign) attestation shipped with every build; a versioned `/metrics` schema artifact.
- **User-gate (behavioral, renewal-driving):** ≥60% of pilot decks show "edit-not-rewrite" behavior (edit-distance or self-report); ≤30 min P95 prompt-to-first-slide-renderable; ≤10s P95 per-refinement latency on Tier-1 endpoints.
- **Pilot acceptance:** one pilot customer, three-signatory signoff (CISO/platform-owner + named end-user lead + backup-signatory continuity clause), within 12 weeks of go-live (18 with the one-time extension) or the program resets to Phase-0 scoping rather than limping forward.
- **The Microsoft watch is no longer a background item.** The existing yearly-plus-gate-coupled-plus-RSS monitoring design is right in shape but appears to have missed the 2026-02-24 announcement — Phase 0 needs to both answer the Copilot-deck-generation-inclusion question directly and confirm the watch mechanism's channel coverage actually would have caught it.

## Scope

**In for v1**, revised from the pre-existing draft per this research pass:

- `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai` (re-pinned to 0.2.8) — five confirmed-necessary recipes, unchanged rationale from the original scope.
- `template-style-extractor` — **removed.** Upstream already does LibreOffice-free template import (DOCX/PPTX/XLSX/ODF via stdlib, PDF via `pdfplumber`) with a smaller footprint than what was proposed; rebuilding it would duplicate work upstream has already shipped, on a stack that's already conda-forge-clean.
- The memory/RAG subsystem (`mem0ai` + `fastembed-vectorstore`) — **new, undecided.** Both are unconditional Presenton dependencies with no conda-forge presence. Phase 0 must decide: two more recipes, or a documented v1 feature-drop (disable memory/chat-history).
- Everything else from the pre-existing PRD's platform layer carries forward as-is: brand-compliance enforcement (three-lane UX), observability (`/metrics`, scrape-only), chargeback (emit-only), the three-tier LLM provider model, the `copilot-bridge` VSIX dev path.

**Explicitly out:** knowledge-base integration beyond prompt + uploaded files, the full JetBrains plugin, `chromium` upstreamed directly to conda-forge (still stalled at staged-recipes#21431, no 2026 movement), SVG→DrawingML fidelity.

**Phase 0 gates the build**, and now carries one more hard-blocking item beyond the four already defined: confirm whether Microsoft's disconnected stack includes deck-generation capability before committing further engineering investment.

## Vision

Two to three years out, if this works: the OCP image is a reference deployment pattern other regulated-enterprise AI tooling in this factory follows (the Steward station already exists for exactly this); `chromium` lands on conda-forge directly and the vendored-binary recipe retires; upstream Presenton open-sources its export pipeline and the clean-room reimplementations retire too; and — the harder-nosed version of this vision — the product's reason to exist is still standing because Microsoft's on-prem stack turned out to be infrastructure without the application layer, or arrived too late, or arrived and this product had already earned the trust relationship. Either way, the six-week fire drill to find out happens in Phase 0, not two years from now.
