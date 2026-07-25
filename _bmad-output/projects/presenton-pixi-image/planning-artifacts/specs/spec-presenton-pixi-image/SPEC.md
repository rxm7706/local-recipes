---
id: SPEC-presenton-pixi-image
surface:
  - helm/**                      # Helm chart (CAP-5), not yet created — exact repo path TBD (architecture "Deferred")
  - pixi.toml                    # locked build env (CAP-1..4)
  - ci/build-airgapped.yml       # air-gapped build pipeline (CAP-1, CAP-4, CAP-6)
  - ci/online-capture.yml        # drift-defense CI (CAP-6)
  - tests/**                     # 4+ fixture sets (CAP-2, CAP-5, CAP-6)
companions: []
sources:
  - ../../../../../../docs/dreams/presenton-pixi-image.md
  - ../../briefs/brief-presenton-pixi-image-2026-07-25/brief.md
  - ../../briefs/brief-presenton-pixi-image-2026-07-25/addendum.md
  - ../../prd.md
  - ../../architecture/architecture-presenton-pixi-image-2026-07-25/ARCHITECTURE-SPINE.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# presenton-pixi-image — air-gapped conda-native Presenton for OpenShift

## Why

A mandate to meet, sharpened into a two-sided commercial bet: regulated enterprises (govtech/fintech/defense-adjacent) whose data classification prohibits cloud Microsoft 365 Copilot are stuck producing decks by hand — slower, and systematically weaker in language and structure, than LLM-assisted peers elsewhere in the org. `presenton-pixi-image` repackages the open-source Presenton AI deck-generation app as a fully air-gapped OCI image for Red Hat OpenShift, replacing every LibreOffice-dependent or opaque-binary component with source-available, conda-forge-native recipes, so the buyer (CISO/platform engineering) can approve one signed artifact instead of integrating five-to-seven unsigned upstream artifacts themselves. The bet carries real urgency: Microsoft's own disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local) went GA worldwide 2026-02-24, and whether it already includes a Copilot-for-PowerPoint-equivalent is the single most consequential open question this project carries into Phase 0 — this is a window-of-opportunity bet, not a comfortable one. Presenton (`deckcraft`'s sibling) is the repackaged *app*; deckcraft is the from-primitives *pipeline* — complementary, not competing.

## Capabilities

- **CAP-1**
  - **intent:** The image renders decks using a bundled, air-gap-buildable Chromium, with zero reachable public CDN at build or runtime.
  - **success:** `playwright-with-chromium` builds, validates, is scanned, and is optimized; AD-1's zero-external-CDN build routing holds; AD-4's Chromium sandbox defaults to a documented `--no-sandbox` posture compatible with OpenShift `restricted-v2`/`restricted-v3`.
- **CAP-2**
  - **intent:** The image renders AI-generated slide content into an editable `.pptx` (image-overlay + extracted-text-shapes fidelity — Decisions Log Q1) carrying a real `docProps/thumbnail.jpeg`, replacing the opaque upstream export bundle and `convert-linux-x64` binary with clean-room, source-available components wired in via Presenton patches.
  - **success:** `presenton-export-node`, `pptx-assembler`, and `pptx-thumbnail-inject` each build+validate+scan+optimize and pass Fixture Set 1 — `AC-FX-AUTHOR-01` (byte/structural equivalence) and `AC-FX-AUTHOR-02` (image SSIM ≥ 0.99).
- **CAP-3**
  - **intent:** The deployed app selects among three OpenAI-compatible LLM tiers (Tier 1 external corporate proxy, Tier 2 in-cluster `llama.cpp` sidecar, Tier 3 init-container GGUF fetch) purely via one env-var contract, with the `copilot-bridge` VSIX covering the VS Code developer inner loop.
  - **success:** `llmai` lands on conda-forge; Helm `values.llmProvider.tier` selects a sub-block with no per-tier code fork (AD-2); per-refinement latency ≤10s P95 on Tier-1 (measurable outcomes table).
- **CAP-4**
  - **intent:** The five confirmed recipes assemble into one pixi-locked, reproducibly-buildable OCI image, carrying a pre-wired, default-off memory-subsystem feature flag, with SBOM generation and signed attestation as the final build stage.
  - **success:** image builds reproducibly with zero external CDN access; CycloneDX (primary) + SPDX (secondary) SBOM plus a cosign attestation ship with every build (AD-5); the `presenton-memory` pixi feature + `values.memory.enabled` (default `false`) are wired end to end (AD-7).
- **CAP-5**
  - **intent:** The image deploys via a standard Helm chart on OpenShift with Restricted-SCC-compatible defaults, ships a versioned `/metrics` schema artifact, and gives day-0/day-2 operators preflight, smoke, credential-rotation, and mark-broken-response fixtures.
  - **success:** AD-8's `restricted-v2` defaults hold (capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation, non-root arbitrary UID, no hardcoded UID/GID); `AC-FX-INSTALL-*` and `AC-FX-DAY2-01..03` pass; the `/metrics` schema is versioned and shipped with the chart.
- **CAP-6**
  - **intent:** Recipe-maintainers get a weekly, non-build-blocking drift-detection harness comparing current upstream Presenton against the captured Fixture Set 1 baseline, filing an auto-issue on breaking drift, in a CI workflow whose network egress is strictly separated from the air-gapped build pipeline.
  - **success:** `AC-FX-MAINT-01..03` and `AC-FX-DRIFT-01..04` all pass; the online-capture workflow never shares a runner or environment with the air-gapped build workflow, enforced at the network-policy level (AD-6), not by convention.

## Constraints

- **AD-1 build routing:** every channel/package resolution in the build pipeline routes through the `*_BASE_URL` env-var family; no recipe, build step, or CI job hardcodes a public URL; `pixitainer` only consumes the pixi-locked environment, never fetches externally itself.
- **AD-2 one true port:** the LLM provider is the *only* swappable seam. Presenton and the Helm chart set only `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` (plus optional `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` passthrough) to select a tier; no tier-specific code path may creep into the app.
- **AD-3 recipe/image boundary:** the image-assembly layer consumes published, versioned conda artifacts by name and pin only — it never vendors or patches recipe internals. `recipe.yaml` content itself is out of this Spec's scope, governed by `conda-forge-expert` per CLAUDE.md Rules 1 and 2.
- **AD-5 single provenance pass:** exactly one `syft`+`cosign` step per image build (post-`pixitainer`, pre-registry-push), producing CycloneDX (primary) + SPDX (secondary) in one deterministic pass — never two disagreeing SBOMs for the same image tag.
- **AD-6 phase-boundary enforcement:** the online-capture/drift CI workflow and the air-gapped build workflow never share a runner or environment; the air-gapped pipeline has zero network egress, enforced at the CI-runner/network-policy level, not by convention.
- **AD-8 SCC target:** Helm SecurityContext defaults to `restricted-v2` compatibility on every target cluster — all capabilities dropped, `seccompProfile: runtime/default`, `allowPrivilegeEscalation: false`, non-root arbitrary UID via the GID-0/`chmod g=u` convention, no hardcoded UID/GID anywhere; `restricted-v3` (`hostUsers: false`) is asserted but not separately branch-tested until the AD-4 Chromium-sandbox spike runs.
- **Hard, no-regression constraints:** zero LibreOffice in the runtime, zero non-conda-forge packages in the runtime, zero non-pixi build steps, zero external CDN access at build or runtime.
- **Phase 0 gates v1 build kickoff (6 exit criteria):** exit 1 (build-complete-hold: GGUF model+quant chosen, bench methodology, source-pathway with alt-source clause) is the critical-path long-pole gating exits 2–3; exits 4/5/6 are independent. Exit 6 (Microsoft disconnected-stack check + memory-subsystem scope decision) is the highest-urgency independent exit because it bears on whether the core differentiator still holds and changes the confirmed recipe count (5 vs 7) — **unresolved, see Open Questions.**

## Non-goals

- `template-style-extractor` — dropped entirely; upstream Presenton already ships LibreOffice-free template import (stdlib `zipfile`+`ElementTree`, native ODF, `pdfplumber` MIT for PDF) with the identical legacy-format rejection this project had independently proposed (Decisions Log Q2, superseded).
- The end web UI of upstream Presenton — out of scope; upstream owns the React/Next.js UI entirely.
- A full JetBrains plugin — v1 ships a docs-only one-pager (REST + OpenAPI + Postman collection); the full plugin is a Growth-tier item.
- Upstreaming `chromium` directly to conda-forge — still stalled at staged-recipes#21431 with no 2026 movement; v1 vendors `chrome-headless-shell` via `playwright-with-chromium` instead; direct upstreaming is Vision-tier.
- An SVG→DrawingML fidelity tier — net-new conda-forge work with no existing library; Vision-tier, not v1/Growth.
- Knowledge-base integration beyond prompt + uploaded files — explicitly held against customer pressure as a v1 boundary (Landing Condition 4); decks whose source material doesn't fit in prompt+files stay out of scope until Vision tier.

## Success signal

A two-gate JTBD that must both hold, because either collapsing kills the product on its own axis. **Buyer-gate** (binary, procurement-visible): all confirmed recipes upstream-merged on conda-forge → landed on the customer's JFrog Artifactory mirror → OCI image on the customer's registry, with SBOM (CycloneDX+SPDX) + a signed-image (cosign) attestation + a versioned `/metrics` schema shipped with every build. **User-gate** (behavioral, renewal-driving): one pilot customer clears a three-signatory acceptance checklist (CISO/platform-owner + named end-user lead + backup-signatory continuity clause) within 12 weeks of go-live (18 with the one-time extension) — requiring `AC-PILOT-001` (≥60% of piloted decks show "edit-not-rewrite" behavior), ≤30 min P95 prompt-to-first-slide-renderable, and ≤10s P95 per-refinement latency on Tier-1. Missing either gate within its window returns the program to Phase 0 scoping rather than limping forward.

## Assumptions

- Q1 (editable-PPTX fidelity bar) is locked at image-overlay + extracted-text-shapes, matching upstream `convert-linux-x64` behavior — not native chart objects or theme/master editability.
- Q3 (LLM provider strategy) is locked: `llmai`'s existing `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` contract covers all three production tiers plus the `copilot-bridge` dev path without any Presenton source patch.
- Q4 (air-gap definition) is locked at full air-gap: build CI runs inside the perimeter against an internal JFrog Artifactory mirror; every dependency must be allowlisted on the mirror or the build fails.
- The reference LLM class for cost/latency targets, the Tier-2 default GGUF model+quantization, and the exact repo landing path for the build/Helm artifacts are all deferred to Phase 0 / architecture-spike resolution and do not change this Spec's shape.

## Open Questions

- **Phase-0 exit 6(a), Redmond-contingency check:** does Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24) already include, or roadmap, a Copilot-for-PowerPoint-equivalent deck-generation capability? Unconfirmed — directly determines whether Risk R3 (existential, JTBD-collapsing) is materialized, partially materialized, or infrastructure-only. Must resolve before further v1 build investment.
- **Phase-0 exit 6(b), memory-subsystem scope:** does `mem0ai` + `fastembed-vectorstore` (unconditional Presenton dependencies, neither on conda-forge) become two additional v1 recipes (5→7 total), or is the memory/chat-history subsystem documented as dropped for v1? Architecture (AD-7) pre-wires both branches, but the no-op-without-a-Presenton-source-patch path is not yet verified — if a patch is required, the maintenance-burden model changes.
- **`psycopg` license flag (Risk R7 replacement):** LGPL-3.0-only, a different obligation class than the Apache/MIT-dominated rest of the stack — flagged for buyer legal/compliance review alongside the JFrog allowlist gap analysis (Phase 0 exit 4); likely-but-not-confirmed acceptable.
