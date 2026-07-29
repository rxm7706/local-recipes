---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/architecture/architecture-presenton-pixi-image-2026-07-25/ARCHITECTURE-SPINE.md"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/briefs/brief-presenton-pixi-image-2026-07-25/brief.md"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/research/technical-presenton-stack-ocp-airgap-research-2026-07-25.md"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/research/domain-regulated-enterprise-airgap-ai-deck-market-research-2026-07-25.md"
project_name: presenton-pixi-image
epicCount: 7
storyCount: 30
status: complete
---

# presenton-pixi-image — Epic Breakdown

## Overview

Decomposition of presenton-pixi-image's PRD (17 synthesized FRs / 10 NFRs — this PRD is narrative-shaped, not FR-numbered in source, so the list below is derived from its Deliverables, Decisions Log, Risk Register, and Phase 0 Exit Criteria sections) and architecture (8 ADs, two-plane paradigm) into 7 epics and 30 stories.

**Critical-path shape:** Epic 1 (Phase 0) gates everything else — the PRD itself defines Phase 0 as blocking v1 build kickoff, so this is a sequencing dependency, not an epic-design artifact. Epics 2–4 (the five confirmed recipes) can run in parallel with each other once Epic 1 clears, except Epic 3 (export pipeline) depends on Epic 2 (`playwright-with-chromium`) having landed, since `presenton-export-node` is built against it. Epic 5 (image assembly) depends on Epics 2–4 having merged recipes to consume. Epic 6 (OCP deployment) depends on Epic 5. Epic 7 (drift defense) can start once Epic 3 exists to have something to baseline against, and its Story 7.1 reuses the same capture script Epic 1's Story 1.3 runs manually once — Epic 7 automates and repeats what 1.3 first did by hand.

Recipe *authoring* content (the actual `recipe.yaml` files) is conda-forge-expert-governed per CLAUDE.md Rules 1 & 2 — stories below scope the recipe-shaped work items this project owns (what the recipe must do, its validation gate, its submission), not recipe internals.

Effort scale: XS (≤4 hr), S (½–1 day), M (1–3 days), L (3–5 days), XL (1–2 wk, usually a multi-week external-review wait, not local work). Story IDs use `Story {epic}.{seq}` per this skill's template convention.

## Requirements Inventory

### Functional Requirements

FR1: System provides a Playwright-based clean-room replacement for the closed-source `presenton-export/index.js` export runtime.
FR2: System provides a PPTX-assembly component producing image-overlay + extracted-text-shape decks, replacing the closed-source `convert-linux-x64` binary.
FR3: System injects `docProps/thumbnail.jpeg` into AI-generated PPTX output so decks display correctly in PowerPoint/Finder/Explorer.
FR4: System bundles a Chromium binary inside a conda-forge package for air-gapped headless rendering.
FR5: System provides a conda-forge-native `llmai` package enabling Presenton's LLM-provider abstraction.
FR6: System allows operators to select and configure one of three LLM provider tiers (internal proxy / `llama.cpp` sidecar / init-container GGUF fetch) via environment variables only, with no code-path divergence between tiers.
FR7: System assembles the five confirmed recipes into a single pixi-locked, reproducible build environment.
FR8: System packages the locked environment into a signed OCI image via pixitainer with zero external CDN access during build.
FR9: System generates a CycloneDX + SPDX SBOM and a cosign attestation for every built image.
FR10: System deploys via a Helm chart onto OpenShift Container Platform, compatible with the Restricted SCC family (`restricted-v2` baseline, `restricted-v3` asserted).
FR11: System exposes a versioned `/metrics` schema artifact for scrape-only observability.
FR12: System ships day-0 preflight fixtures (registry-reachable, secrets-present, manifest-validates, JFrog auth working, GGUF present if Tier-2/3) inside deployment tooling.
FR13: System ships day-2 operational fixtures (smoke-deck, credential-rotation check, mark-broken-pinned-deps check) inside the OCI image.
FR14: System captures an online, package-author golden-fixture baseline of upstream Presenton export behavior for clean-room-reimpl verification.
FR15: System runs a weekly online drift-detection job comparing current upstream Presenton against the captured baseline and auto-files an issue on breaking drift.
FR16: System pre-wires (via a build-time feature flag) the option to add `mem0ai` + `fastembed-vectorstore` as two more recipes, or ship v1 with the memory subsystem disabled, without an architecture rework.
FR17: System reuses the existing `copilot-bridge` VSIX for the developer inner loop, verified to emit correct Presenton env vars.

### NonFunctional Requirements

NFR1: Zero non-conda-forge packages present in the runtime image.
NFR2: Zero external CDN or network access during the air-gapped build or at runtime.
NFR3: All recipe/channel resolution during build routes through the `*_BASE_URL` JFrog-mirror env-var family — never a hardcoded public host.
NFR4: Container runs under OpenShift Restricted SCC (`restricted-v2` baseline) with no hardcoded UID/GID and no privileged mode.
NFR5: First-slide-renderable latency ≤30min P95 (prompt-submit to first paintable slide) on Tier-1 LLM — pilot-measured business metric, not a build-epic gate; noted where relevant.
NFR6: Per-refinement latency ≤10s P95 on Tier-1 LLM — same caveat as NFR5.
NFR7: Day-2 smoke-deck fixture completes within a 60s budget.
NFR8: CVE rebuild-and-resign capability within 14 days P95, conditional on JFrog allowlist SLA ≤48h.
NFR9: Recipes are lint-clean (`conda-smithy` + `rattler-build lint`), build deterministically, and survive one full conda-forge global pinning bump (rerender-survivability).
NFR10: Online fixture-capture (Set 1) and drift-detection (Set 2) never share a CI runner or network path with the air-gapped build pipeline — a hard topology split, not a convention.

### Additional Requirements (from Architecture)

- AD-1: single `pixi.toml` environment assembles the five confirmed recipes; pixitainer consumes it for OCI assembly.
- AD-2: the LLM provider (`CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY`) is the only swappable run-time seam — `values.llmProvider.tier` enum, no per-tier code fork.
- AD-3: the image-assembly layer never vendors or patches recipe internals — recipe content is conda-forge-expert territory.
- AD-4: Chromium runs `--no-sandbox` by default (explicit, documented decision); `chromiumSandboxMode` is an escape hatch, unbuilt until a real-cluster spike validates it.
- AD-5: `syft` (CycloneDX + SPDX) + `cosign` (sign + attest) run once, deterministically, post-`pixitainer`.
- AD-6: fixture Sets 1–2 run only in a separate, network-allowed CI workflow; the air-gapped build workflow has no network egress at all, enforced at the runner/network-policy level.
- AD-7: `presenton-memory` pixi feature (default off) + `values.memory.enabled` (default false) pre-wire the Phase-0 exit-6b fork.
- AD-8: Helm `SecurityContext` defaults are `restricted-v2`-compatible; `restricted-v3` asserted, not separately branch-tested until the AD-4 spike.

### UX Design Requirements

N/A — no UX design contract exists for this infrastructure/developer_tool project (no `bmad-ux` run in `planning-artifacts/`). The PRD's brand-compliance enforcement UX bands (auto-fix / batched-review / ignore) are Presenton-application-layer Growth-tier scope per the PRD's Product Scope section, not v1 architecture/build work this epic set owns.

### FR Coverage Map

| FR | Epic | Story |
|---|---|---|
| FR1 | Epic 3 | Story 3.1 |
| FR2 | Epic 3 | Story 3.2 |
| FR3 | Epic 3 | Story 3.3 |
| FR4 | Epic 2 | Story 2.1 |
| FR5 | Epic 4 | Story 4.1 |
| FR6 | Epic 4 | Story 4.3 |
| FR7 | Epic 5 | Story 5.1 |
| FR8 | Epic 5 | Story 5.2 |
| FR9 | Epic 5 | Story 5.4 |
| FR10 | Epic 6 | Story 6.1 |
| FR11 | Epic 6 | Story 6.3 |
| FR12 | Epic 6 | Story 6.4 |
| FR13 | Epic 6 | Story 6.5 |
| FR14 | Epic 1, Epic 7 | Story 1.3 (one-time), Story 7.1 (automated) |
| FR15 | Epic 7 | Story 7.3 |
| FR16 | Epic 1, Epic 5 | Story 1.7 (decision), Story 5.3 (pre-wiring) |
| FR17 | Epic 4 | Story 4.4 |

### NFR Coverage Map

| NFR | Subject | Owning Story/Stories |
|---|---|---|
| NFR1, NFR2, NFR3 | Air-gap build hygiene | Story 5.1, Story 5.2, Story 7.2, and every recipe build story (2.1, 3.1–3.3, 4.1) |
| NFR4 | Restricted SCC compatibility | Story 6.1 |
| NFR5, NFR6 | End-to-end latency | Pilot-measured (PRD Measurable Outcomes); Story 6.5's smoke fixture provides a build-time proxy signal only |
| NFR7 | Smoke-deck budget | Story 6.5 |
| NFR8 | CVE rebuild-resign SLA | Story 1.4 (SLA gap analysis), Story 7.3 (drift/response capability) |
| NFR9 | Recipe quality bar | Story 2.1, Story 3.1–3.3, Story 4.1 |
| NFR10 | CI-topology split | Story 7.2 |

## Epic List

| Epic | Title | Story Count |
|---|---|---|
| Epic 1 | Phase-0 Decision Readiness | 7 |
| Epic 2 | Air-Gapped Browser Rendering Capability | 2 |
| Epic 3 | Clean-Room Deck Export Pipeline | 5 |
| Epic 4 | LLM Provider Abstraction & Tiering | 4 |
| Epic 5 | Signed Air-Gapped Image Assembly | 4 |
| Epic 6 | OCP Deployment & Operations | 5 |
| Epic 7 | Upstream Drift Defense | 3 |
| **Total** | | **30** |

---

## Epic 1: Phase-0 Decision Readiness

Resolves the PRD's six Phase-0 exit criteria so the buyer/steering persona can commit to v1 build with the open unknowns closed, not assumed away. **Nothing in Epics 2–7 should start production work ahead of the exits relevant to it** — this epic is standalone value (an informed go/no-go and configuration baseline) and every later epic consumes its outputs without needing any later epic to function.

### Story 1.1: GGUF model and quantization tier selection

As the platform-engineering steering persona,
I want a benchmarked GGUF model + quantization tier chosen for Tier-2, with the bench methodology and coverage floor documented,
So that the Tier-2 default is defensible before any Helm chart references a specific model.

**Type:** decision • **Effort:** M • **Deps:** none • **FR/AD:** PRD Phase-0 exit 1

**Acceptance Criteria:**

**Given** the candidate models named in the PRD (Qwen 2.5 7B Q4_K_M default, Llama 3.2 3B Q4 fallback)
**When** the bench is run against GovReport + BillSum public datasets mapped to the 12-archetype rubric
**Then** a bench methodology document names which of the 12 archetypes are covered, with a floor of ≥8/12 archetypes carrying at least one public-dataset proxy task
**And** the uncovered archetypes are named explicitly as Phase-1 deferred risk, not silently absent
**And** a source-pathway commitment is recorded covering the alt-source clause (customer-supplied GGUF, pre-vetted internal registry, or customer-licensed-and-converted model) for GRC environments that ban HuggingFace as a source
**And** the specific model+quant lock is deferred to customer-mirror-allowlist resolution time, not fixed here

### Story 1.2: Tier-1 reference LLM class commitment

As the platform-engineering steering persona,
I want a named reference LLM class (e.g. vLLM-served 70B-class GPU, Azure OpenAI tenant endpoint, on-prem Llama-3-70B) committed for methodology purposes,
So that user-success latency/quality metrics have a fixed evaluation target even though a customer's actual Tier-1 endpoint may differ.

**Type:** decision • **Effort:** S • **Deps:** none • **FR/AD:** PRD Phase-0 exit 2

**Acceptance Criteria:**

**Given** the three candidate reference classes named in the PRD
**When** the steering persona commits to one
**Then** the choice and its rationale are recorded in the PRD's Phase-0 exit-criteria section (or a linked decision note)
**And** the choice is referenced by name in any future latency/quality benchmark work (Epic 6's day-2 fixtures, pilot success criteria)

### Story 1.3: Fixture-capture v1 baseline (one-time, manual)

As the recipe-maintainer wearing the fixture-maintainer hat,
I want a one-time online capture of upstream Presenton's export behavior at a locked tag, signed and committed,
So that clean-room reimpls (Epic 3) have a byte/structurally-equivalent + SSIM-scored oracle to build against before any automated drift-cron exists.

**Type:** infra • **Effort:** M • **Deps:** none (runs manually, ahead of Epic 7's automation) • **FR/AD:** FR14

**Acceptance Criteria:**

**Given** a locked upstream Presenton release tag chosen for this baseline
**When** `tests/capture_upstream.py --version <V> --output tests/fixtures/upstream-baseline/v<V>/` is run once, online, outside the air-gapped pipeline
**Then** the captured artifacts are committed to the repo under `tests/fixtures/upstream-baseline/v<V>/`
**And** a signed manifest and an initial fixture-changelog entry are written alongside them
**And** the capture script is never re-run automatically in CI — only Epic 7's separate online workflow re-invokes it on a cadence

### Story 1.4: JFrog allowlist gap analysis

As the platform engineer,
I want a per-dependency gap report across the full conda + npm + GGUF dependency closure (including the previously-unscoped `mem0ai`/`fastembed-vectorstore` pair and the `psycopg` LGPL flag),
So that delivery-timeline risk (Risk R4) and licensing risk (Risk R7, revised) are known quantities before recipe submission begins.

**Type:** decision • **Effort:** M • **Deps:** none • **FR/AD:** PRD Phase-0 exit 4, Risk R4, Risk R7

**Acceptance Criteria:**

**Given** the full dependency table from the technical research report (§1.8, all conda-forge-available packages plus the two gaps)
**When** the gap analysis is filed
**Then** it names which packages are already mirrored, which need allowlist requests, which carry licensing flags (`psycopg` LGPL-3.0-only), and the expected security-review SLA per gap
**And** the `mem0ai`/`fastembed-vectorstore` pair is included regardless of Story 1.7's outcome (the analysis covers the "add them" branch even if 1.7 chooses feature-drop, so the number is available if the decision is later revisited)

### Story 1.5: Capability Claim Statement committed

As the buyer-facing steering persona,
I want a single canonical capability-claim sentence, content-reviewed and forbidding cloud-product comparisons,
So that field conversations don't re-litigate positioning ad-hoc and competitors can't define the product by negation.

**Type:** decision • **Effort:** S • **Deps:** none • **FR/AD:** PRD Phase-0 exit 5

**Acceptance Criteria:**

**Given** the canonical form `"Generates [artifact-class] at [public-bench-score] quality, fully on-prem, with [SLA]."`
**When** the statement is drafted and passed through the content-review checkpoint
**Then** it contains no "Copilot-class," no parity numbers, and no SaaS-equivalent framing
**And** it is committed as a PRD-linked artifact before Phase 0 is considered closed

### Story 1.6: Microsoft disconnected-stack verification (Redmond-contingency check)

As the strategic/steering persona,
I want a direct confirmation of whether Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA 2026-02-24) includes or roadmaps Copilot-for-PowerPoint-equivalent deck generation,
So that Risk R3's actual status (materialized / partially materialized / infrastructure-only) is known before further build investment, and the RSS/keyword-watch mechanism's channel-coverage gap is fixed.

**Type:** decision • **Effort:** M • **Deps:** none • **FR/AD:** PRD Phase-0 exit 6(a), Risk R3 (revised)

**Acceptance Criteria:**

**Given** the domain research report's finding that Microsoft's infrastructure stack shipped without a confirmed application-layer answer
**When** the verification is performed (via a Microsoft licensing/product conversation or hands-on access to a Microsoft 365 Local disconnected deployment)
**Then** Risk R3's status is updated in the PRD from "unresolved" to one of the three named outcomes, with evidence cited
**And** the existing RSS/keyword-watch mechanism's channel coverage is audited against `learn.microsoft.com`/Azure product-doc channels (not just the M365-roadmap/Copilot-blog channels the PRD text names) and fixed if it would have missed the 2026-02-24 announcement
**And** if the outcome is "materialized," the finding is escalated to steering immediately, not held for the next yearly review cycle

### Story 1.7: Memory-subsystem scope decision

As the platform engineer,
I want a committed decision on whether `mem0ai` + `fastembed-vectorstore` become two additional v1 recipes or the memory/chat-history subsystem ships disabled,
So that Epic 5's pre-wired feature flag (AD-7) has a resolved default before the image ships, and Epics 2–4's recipe count is no longer "five, plus up to two."

**Type:** decision • **Effort:** M • **Deps:** Story 1.4 (informs cost of the "add two more recipes" branch) • **FR/AD:** FR16, AD-7

**Acceptance Criteria:**

**Given** the two options (Option A: add both recipes; Option B: feature-drop with a confirmed no-op import path)
**When** the import graph is traced to confirm whether a clean no-op is possible without a Presenton source patch
**Then** if no-op is confirmed clean, Option B is the default and `presenton-memory`/`values.memory.enabled` stay off
**And** if a source patch is required, that patch joins the `presenton-export-node`/`pptx-assembler` patch set (Epic 3's scope) and the decision is Option A or a documented patch-maintenance acceptance, not silently deferred again
**And** the outcome is recorded against AD-7 in the architecture spine's memlog

---

## Epic 2: Air-Gapped Browser Rendering Capability

Delivers a bundled-Chromium conda-forge package, standing alone as a reusable artifact for any conda-forge consumer needing headless browser rendering — and unblocks Epic 3's `presenton-export-node`, which depends on it.

### Story 2.1: Build, validate, scan, and optimize `playwright-with-chromium`

As the recipe-maintainer,
I want the `playwright-with-chromium` recipe passing the full 4-check validation pattern (build + validate + scan + optimize), bundling `chrome-headless-shell` at conda-build time,
So that air-gapped consumers get a working headless-Chromium package with zero runtime CDN dependency.

**Type:** recipe • **Effort:** L • **Deps:** Epic 1 (Story 1.4's allowlist analysis should confirm the browser binary's mirror/vendoring path) • **FR/AD:** FR4, NFR1, NFR2, NFR3, NFR9

**Acceptance Criteria:**

**Given** the pyppeteer-feedstock#3 bundled-binary pattern as the model
**When** the recipe is built via `rattler-build`
**Then** it produces a conda artifact containing a working `chrome-headless-shell` binary with no post-install network fetch
**And** `rattler-build lint` and `conda-smithy` checks pass clean
**And** a security scan finds no disqualifying findings on the vendored binary
**And** the recipe channel/source resolution routes through the `*_BASE_URL` env-var family (NFR3), never a hardcoded Microsoft Playwright CDN URL

### Story 2.2: Submit `playwright-with-chromium` to staged-recipes and land the merge

As the recipe-maintainer,
I want the validated recipe submitted through the standard staged-recipes PR flow and merged,
So that the package becomes available on the conda-forge channel for the JFrog mirror sync in Epic 5.

**Type:** submission • **Effort:** XL (external review-cycle wait) • **Deps:** Story 2.1 • **FR/AD:** FR4

**Acceptance Criteria:**

**Given** the validated recipe from Story 2.1
**When** the PR is opened against `conda-forge/staged-recipes`
**Then** it clears CI on all target platforms and addresses reviewer feedback
**And** the merge lands and the resulting feedstock's first build succeeds
**And** the package's conda-forge availability is confirmed via `api.anaconda.org` before Epic 5 depends on it

---

## Epic 3: Clean-Room Deck Export Pipeline

`presenton-export-node`, `pptx-assembler`, and `pptx-thumbnail-inject` all replace pieces of the same closed-source upstream export pipeline and are naturally sequenced against the same Fixture Set 1 oracle — consolidated into one epic per the "same core files/pipeline" grouping principle rather than three separate epics with heavy dependency coupling.

### Story 3.1: Build, validate, scan, and optimize `presenton-export-node`

As the recipe-maintainer,
I want a Playwright-based Node package replacing the opaque `presenton-export/index.js`, matching its shallow Puppeteer-shaped API surface (launch/newPage/goto/setViewport/pdf/screenshot),
So that the export pipeline's first stage is source-available and conda-forge-buildable.

**Type:** recipe • **Effort:** L • **Deps:** Epic 2 (Story 2.2 — this package runs against the bundled Chromium) • **FR/AD:** FR1, NFR1, NFR2, NFR3, NFR9

**Acceptance Criteria:**

**Given** Story 1.3's captured baseline fixtures for the locked upstream tag
**When** `presenton-export-node` runs the same export sequence against a running Presenton Next.js instance
**Then** its output matches Fixture Set 1's AC-FX-AUTHOR-01 (byte/structurally equivalent, zip-entry order and timestamps normalized)
**And** the recipe passes the 4-check validation pattern (build + validate + scan + optimize)
**And** the package depends on Epic 2's `playwright-with-chromium`, not a separate Chromium fetch

### Story 3.2: Build, validate, scan, and optimize `pptx-assembler`

As the recipe-maintainer,
I want a Python package (python-pptx + Pillow) replacing the opaque `convert-linux-x64` binary, producing image-overlay + extracted-text-shape PPTX output per PRD Decisions Log Q1,
So that the export pipeline's second stage is source-available and matches the agreed fidelity bar.

**Type:** recipe • **Effort:** L • **Deps:** Story 3.1 (consumes its JSON/images.zip handoff contract) • **FR/AD:** FR2, NFR1, NFR2, NFR3, NFR9

**Acceptance Criteria:**

**Given** the same JSON+images.zip contract the opaque `convert-linux-x64` binary currently consumes
**When** `pptx-assembler` processes it
**Then** the output `.pptx` matches Fixture Set 1's AC-FX-AUTHOR-01/02 (structural equivalence + SSIM ≥0.99 for image regions)
**And** the produced deck retains editable extracted-text shapes alongside the image overlay (Q1's fidelity bar)
**And** the recipe passes the 4-check validation pattern

### Story 3.3: Spike, build, validate, scan, and optimize `pptx-thumbnail-inject`

As the recipe-maintainer,
I want the thumbnail-synthesis approach spiked and resolved (Risk R1 — no conda-forge recipe synthesizes OOXML thumbnails today) before committing an estimate, then the recipe built,
So that AI-generated decks stop landing with placeholder thumbnails in PowerPoint/Finder/Explorer.

**Type:** recipe • **Effort:** M (spike) + M (recipe) • **Deps:** Story 3.2 (injects into its output) • **FR/AD:** FR3, NFR1, NFR2, NFR3, NFR9, Risk R1

**Acceptance Criteria:**

**Given** the three candidate rendering methods named in Risk R1 (LibreOffice headless — ruled out per the PRD's zero-LibreOffice constraint; python-pptx slide render; Pillow synthesis from rendered HTML PNG)
**When** the spike selects one
**Then** the choice and rationale are recorded before sprint estimation
**And** the resulting recipe injects `docProps/thumbnail.jpeg` + the `[Content_Types].xml` Override via `zipfile`, matching the standard LibreOffice-free workaround the PRD's Discovery section names
**And** the recipe passes the 4-check validation pattern (folded into `pptx-assembler`'s package if the spike finds that's the cleaner shape — architecture's Structural Seed treats this as a likely fold, not a hard split)

### Story 3.4: Submit the three export-pipeline recipes and land the merges

As the recipe-maintainer,
I want all three recipes submitted through staged-recipes and merged,
So that the full export-pipeline replacement is available on the conda-forge channel.

**Type:** submission • **Effort:** XL (external review-cycle wait, three parallel PRs) • **Deps:** Stories 3.1, 3.2, 3.3 • **FR/AD:** FR1, FR2, FR3

**Acceptance Criteria:**

**Given** the three validated recipes
**When** their PRs are opened against `conda-forge/staged-recipes`
**Then** each clears CI and reviewer feedback independently (a slow review on one does not block the other two's merges)
**And** all three land and their feedstocks' first builds succeed

### Story 3.5: Wire the clean-room pipeline into Presenton via patches

As the recipe-maintainer,
I want the presenton patches applied that replace the upstream binary fetch with the three merged recipes and flip any remaining upstream config,
So that a Presenton instance built from this image actually uses the clean-room pipeline end-to-end.

**Type:** integration • **Effort:** M • **Deps:** Story 3.4 • **FR/AD:** FR1, FR2, FR3

**Acceptance Criteria:**

**Given** the merged `presenton-export-node`, `pptx-assembler`, and `pptx-thumbnail-inject` packages
**When** Presenton's build-time export-download step and `convert-linux-x64` invocation are patched to use them instead
**Then** a full export run (prompt → deck → exported `.pptx`) succeeds using only the clean-room components, zero opaque binaries
**And** the `docker-compose.yml` UX patch forwarding `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` explicitly is applied (~3 LOC per PRD deliverables)
**And** Fixture Set 1's full AC-FX-AUTHOR-01/02 pass against Story 1.3's baseline

---

## Epic 4: LLM Provider Abstraction & Tiering

Delivers a working, conda-forge-native LLM client plus the three-tier configuration model that lets any deployment — dev or production — point Presenton at an LLM without code changes.

### Story 4.1: Build, validate, scan, and optimize `llmai`

As the recipe-maintainer,
I want the `llmai` package (pinned `0.2.8`, Apache-2.0) packaged for conda-forge,
So that Presenton's LLM-provider abstraction is available without a PyPI-only dependency in the runtime image.

**Type:** recipe • **Effort:** M • **Deps:** none (independent of Epics 2–3) • **FR/AD:** FR5, NFR1, NFR2, NFR3, NFR9

**Acceptance Criteria:**

**Given** `llmai==0.2.8` on PyPI, Apache-2.0
**When** the recipe is built via `rattler-build`
**Then** it passes the 4-check validation pattern
**And** the pinned version is re-verified against PyPI at submission time (upstream re-pins fast — 6 releases drifted between original PRD drafting and this revision)

### Story 4.2: Submit `llmai` to staged-recipes and land the merge

As the recipe-maintainer,
I want the validated `llmai` recipe merged on conda-forge,
So that Epic 5's image assembly can consume it.

**Type:** submission • **Effort:** XL (external review-cycle wait) • **Deps:** Story 4.1 • **FR/AD:** FR5

**Acceptance Criteria:**

**Given** the validated recipe
**When** the PR clears CI and review
**Then** it merges and the feedstock's first build succeeds
**And** availability is confirmed via `api.anaconda.org` before Epic 5 depends on it

### Story 4.3: Wire the three-tier LLM provider model into the Helm chart

As the OCP operator (day-0),
I want a single `values.llmProvider.tier` selector that configures Tier-1 (external endpoint), Tier-2 (`llama.cpp` sidecar), or Tier-3 (init-container GGUF fetch) without touching application code,
So that I can pick my LLM strategy at deploy time per architecture AD-2.

**Type:** infra • **Effort:** M • **Deps:** Story 4.2, Story 1.1 (Tier-2 model pick), Story 1.2 (Tier-1 reference class) • **FR/AD:** FR6, AD-2

**Acceptance Criteria:**

**Given** `values.llmProvider.tier: tier1`
**When** the chart renders
**Then** only `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` env vars are set, pointing at the operator-supplied endpoint, with no in-cluster LLM resource created
**And** setting `tier: tier2` instead renders a `llama.cpp` Service (sidecar or dedicated Deployment) and points the same env vars at it
**And** setting `tier: tier3` renders the same Tier-2 shape plus an init-container that fetches the GGUF from an internal registry before the main container starts
**And** no Helm template branches on tier anywhere outside this one values-driven selection (AD-2's no-fork rule)

### Story 4.4: Verify the `copilot-bridge` dev-path integration

As the VS Code developer,
I want the existing `copilot-bridge` VSIX's Story 6 ("Configure presenton") verified to emit the correct Presenton env vars against this project's actual `CUSTOM_LLM_URL` contract,
So that the sideload dev-path works without rebuilding the extension from scratch.

**Type:** integration-verification • **Effort:** S • **Deps:** Story 4.2 • **FR/AD:** FR17

**Acceptance Criteria:**

**Given** the existing VSIX at `docs/specs/copilot-bridge-vscode-extension.md` (Story 6 already scoped there)
**When** the bridge daemon at `localhost:4141` is configured against a local Presenton instance built from this project's image
**Then** the emitted env vars (`CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY`) match exactly what `llm_config.py` expects
**And** any mismatch is filed back against the copilot-bridge spec, not silently patched here (this story verifies, it does not own that extension's scope)

---

## Epic 5: Signed Air-Gapped Image Assembly

Delivers a buildable, reproducible, provenance-attested OCI image to the OCP operator — the point where all merged recipes come together.

### Story 5.1: Assemble the pixi-locked build environment

As the platform engineer,
I want a single `pixi.toml` environment pinning the five confirmed recipes (plus the `presenton-memory` feature per AD-7),
So that the image build is reproducible and every dependency resolves through governed channels.

**Type:** infra • **Effort:** M • **Deps:** Epic 2 (Story 2.2), Epic 3 (Story 3.4), Epic 4 (Story 4.2) • **FR/AD:** FR7, AD-1, NFR1, NFR2, NFR3

**Acceptance Criteria:**

**Given** the merged `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, and `llmai` packages
**When** `pixi.toml` declares them as pinned dependencies in one environment
**Then** `pixi install` resolves fully offline against the JFrog mirror (no `pypi.org`/`conda.anaconda.org` reachable in the test harness)
**And** the `presenton-memory` feature exists as a togglable feature, default off, per AD-7
**And** every channel reference in the lockfile resolves through the `*_BASE_URL` family, confirmed by inspecting the resolved URLs

### Story 5.2: Assemble the OCI image via pixitainer

As the platform engineer,
I want the locked pixi environment turned into an OCI image via pixitainer with zero external CDN access during the build,
So that the image is air-gap-buildable end-to-end.

**Type:** infra • **Effort:** M • **Deps:** Story 5.1 • **FR/AD:** FR8, AD-1, NFR2

**Acceptance Criteria:**

**Given** the locked environment from Story 5.1
**When** `pixitainer` (0.8.2) builds the image
**Then** the build completes with network egress disabled at the CI-runner level (not just by convention)
**And** the resulting image starts and a smoke test (deck generation against a stubbed LLM endpoint) succeeds
**And** no LibreOffice, no non-conda-forge package, and no non-pixi build step is present anywhere in the image (PRD hard constraints)

### Story 5.3: Wire the memory-subsystem feature-flag fork

As the platform engineer,
I want the pixi `presenton-memory` feature and Helm `values.memory.enabled` flag actually toggling the built image's behavior,
So that Story 1.7's eventual decision (Epic 1) takes effect with a values change, not a rebuild of this epic's work.

**Type:** infra • **Effort:** S • **Deps:** Story 5.1, Story 1.7 (for the default value; the wiring itself doesn't wait) • **FR/AD:** FR16, AD-7

**Acceptance Criteria:**

**Given** `presenton-memory` feature off (default)
**When** the image is built and deployed with `values.memory.enabled: false`
**Then** `mem0ai`/`fastembed-vectorstore` are absent from the locked environment and the memory/chat-history env var signals "disabled" to Presenton
**And** flipping both to "on" (feature + values) is a config change only — no code change required in this repo — once Story 1.7 confirms the no-op path or the two recipes exist

### Story 5.4: Generate SBOM and sign the image

As the buyer/CISO,
I want a CycloneDX+SPDX SBOM and a cosign attestation produced for every built image,
So that the buyer-gate provenance requirement is met without manual intervention.

**Type:** infra • **Effort:** M • **Deps:** Story 5.2 • **FR/AD:** FR9, AD-5

**Acceptance Criteria:**

**Given** the assembled OCI image from Story 5.2
**When** `syft` (1.49.0) scans it
**Then** it emits CycloneDX (primary) and SPDX (secondary export) SBOMs in one deterministic pass
**And** `cosign` (3.0.4) signs the image digest and attaches the SBOM as an in-toto attestation
**And** this runs exactly once per image build, as the terminal build-time-plane stage — no second, divergent SBOM is ever produced for the same tag

---

## Epic 6: OCP Deployment & Operations

Delivers the deployable, operable Helm chart to both day-0 and day-2 OCP operator personas.

### Story 6.1: Helm chart with Restricted-SCC-compatible SecurityContext

As the OCP operator (day-0),
I want the Helm chart's Pod/container `SecurityContext` to work under `restricted-v2` by default with no hardcoded UID/GID,
So that the chart deploys on any OCP cluster without a custom SCC grant.

**Type:** infra • **Effort:** M • **Deps:** Story 5.4 (deploys the signed image) • **FR/AD:** FR10, AD-8, NFR4

**Acceptance Criteria:**

**Given** an OCP namespace with only the default `restricted-v2` SCC available
**When** the chart is installed
**Then** all pods start successfully with all capabilities dropped, `seccompProfile: runtime/default`, `allowPrivilegeEscalation: false`, and an arbitrary namespace-assigned UID
**And** writable paths (`/app_data`, `/tmp`) use the GID-0/`chmod g=u` convention, not a hardcoded UID assumption
**And** `readOnlyRootFilesystem` is available as an opt-in values flag, default `false`

### Story 6.2: Wire the Chromium sandbox default and escape hatch

As the OCP operator (day-0),
I want the deployment to default to `--no-sandbox` for Chromium as a documented security decision, with a values-exposed escape hatch for a future namespace-sandbox mode,
So that Risk R9 has a shipped, explicit answer rather than a silent default.

**Type:** infra • **Effort:** S • **Deps:** Story 6.1 • **FR/AD:** AD-4, Risk R9

**Acceptance Criteria:**

**Given** the default `chromiumSandboxMode: none` values setting
**When** the chart deploys
**Then** the deployment's documentation (chart README or values comments) states plainly that Chromium runs `--no-sandbox` and why
**And** `chromiumSandboxMode: namespace` is present as a values option but its behavior is documented as "unvalidated, pending a real-cluster spike" — not silently wired to working code

### Story 6.3: Ship the versioned `/metrics` schema artifact

As the buyer/CISO and the OCP operator (day-2),
I want a versioned schema document locking metric names, label keys, histogram buckets, and cardinality bounds shipped with the Helm chart,
So that `/metrics` is a first-class, contract-bound deliverable, not an undocumented capability claim.

**Type:** infra • **Effort:** S • **Deps:** Story 6.1 • **FR/AD:** FR11

**Acceptance Criteria:**

**Given** the Prometheus `/metrics` endpoint already scoped as scrapeable + non-blocking (PRD v1 platform additions)
**When** the chart is packaged
**Then** a versioned schema document ships alongside it (e.g. a ConfigMap or chart-bundled file) naming every metric, label, and bucket
**And** a schema version bump is required whenever a metric name/label/bucket changes — enforced by a lint check, not just a review convention

### Story 6.4: Day-0 install preflight fixtures

As the OCP operator (day-0),
I want `tests/install/` fixtures that check registry reachability, secrets presence, manifest validity, JFrog auth, and GGUF presence (if Tier-2/3) before the first `oc apply`,
So that install failures surface before deployment, not during it.

**Type:** infra • **Effort:** M • **Deps:** Story 6.1, Story 4.3 (tier-aware checks) • **FR/AD:** FR12

**Acceptance Criteria:**

**Given** a target OCP namespace and the chart's `values.yaml`
**When** the day-0 preflight fixtures run
**Then** they report registry-reachable, secrets-present, and manifest-validates as pass/fail gates (AC-FX-INSTALL-*)
**And** for `tier2`/`tier3`, they additionally check GGUF-model presence at the configured path/registry
**And** a failing preflight blocks the operator from proceeding with a clear, actionable message — it does not silently continue

### Story 6.5: Day-2 operational fixtures shipped inside the image

As the OCP operator (day-2),
I want smoke-deck, credential-rotation, and mark-broken-pinned-deps checks shipped at `/opt/presenton/tests/` inside the running image,
So that day-2 operations have an air-gapped, no-upstream-comparison health check suite.

**Type:** infra • **Effort:** M • **Deps:** Story 5.2 (fixtures ship in the image itself) • **FR/AD:** FR13, NFR7

**Acceptance Criteria:**

**Given** a running deployed instance
**When** the post-deploy smoke fixture runs `minimal-deck.json` end-to-end
**Then** it completes within a 60-second budget and asserts the output `.pptx` opens (zip integrity + minimum slide count) — AC-FX-DAY2-01
**And** the credential-rotation fixture verifies the LLM endpoint is reachable with newly-rotated creds without an app restart — AC-FX-DAY2-02
**And** the mark-broken-pinned-deps fixture reports flagged-broken deps via conda-forge repodata-patches to gate a rollback decision — AC-FX-DAY2-03

---

## Epic 7: Upstream Drift Defense

Delivers ongoing confidence to the recipe-maintainer that the clean-room reimpls stay correct as upstream Presenton ships new releases — automating and repeating what Epic 1's Story 1.3 first did by hand.

### Story 7.1: Reusable online-capture CI workflow

As the recipe-maintainer wearing the fixture-maintainer hat,
I want the manual capture Story 1.3 ran once turned into a reusable, separately-triggerable CI workflow,
So that future baseline refreshes don't require a human to re-run a script by hand every time.

**Type:** infra • **Effort:** M • **Deps:** Story 1.3 (reuses its script), Story 3.5 (needs the clean-room pipeline to exist to be worth automating against) • **FR/AD:** FR14

**Acceptance Criteria:**

**Given** `tests/capture_upstream.py` proven out manually in Story 1.3
**When** a path-watch trigger fires on upstream `presenton-export/` (new release detected)
**Then** the online workflow re-runs the capture, commits the new fixture set, and writes a fixture-changelog entry documenting intentional vs. unintentional drift
**And** this workflow runs in a network-allowed CI runner, never the air-gapped build runner (AD-6, enforced by Story 7.2)

### Story 7.2: Enforce the air-gapped/online CI-topology split

As the platform engineer,
I want the air-gapped build pipeline and the online capture/drift workflows to run on structurally separate CI runners with no shared network policy,
So that Risk R6 (phase-boundary collapse) is prevented at the infrastructure level, not just documented as a convention.

**Type:** infra • **Effort:** S • **Deps:** Story 5.2 (the air-gapped build pipeline this must not share with), Story 7.1 • **FR/AD:** AD-6, NFR10, Risk R6

**Acceptance Criteria:**

**Given** the two workflow files (`ci/build-airgapped.yml`, `ci/online-capture.yml`)
**When** the air-gapped workflow attempts any outbound network call
**Then** it fails immediately at the network-policy level, not at an application-level check
**And** an accidental invocation of Set-1/Set-2 capture logic inside the air-gapped workflow fails loudly with a clear error, rather than silently succeeding or silently reaching out to the internet

### Story 7.3: Weekly drift-detection harness with auto-issue filing

As the recipe-maintainer,
I want a weekly online cron job comparing current upstream Presenton against the captured baseline, categorizing breaking vs. benign drift, and auto-filing an issue on breaking drift,
So that upstream changes are caught proactively instead of discovered when a clean-room reimpl silently diverges.

**Type:** infra • **Effort:** M • **Deps:** Story 7.1, Story 7.2 • **FR/AD:** FR15, NFR8

**Acceptance Criteria:**

**Given** the Set-1 baseline and the weekly cron schedule
**When** `recapture.py` runs against latest upstream
**Then** it emits a structured drift report (added/removed/changed fixtures, per-fixture diff summary) — AC-FX-MAINT-01
**And** the report distinguishes breaking drift (clean-room reimpl will diverge) from benign drift (cosmetic upstream change) per `tests/drift/README.md`'s categorization rules — AC-FX-MAINT-02
**And** breaking drift auto-files a `.github/ISSUE_TEMPLATE/upstream-drift.md` issue with the diff body — AC-FX-MAINT-03
**And** a failed drift-harness step exits 0 from the cron job with a `::warning::` annotation — it never breaks the build (per the PRD's explicit non-gating requirement, and given the observed 3-tags-in-6-days upstream release cadence found during technical research, this job's failure tolerance matters more than the PRD's original weekly-cadence assumption implied)
