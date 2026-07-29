---
stepsCompleted: ['step-01-init', 'step-01b-rearchitecture', 'step-01b-continue', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'update-2026-07-25-research-revision']
inputDocuments:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/CLAUDE.md'
  - '{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/briefs/brief-presenton-pixi-image-2026-07-25/brief.md'
  - '{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/research/technical-presenton-stack-ocp-airgap-research-2026-07-25.md'
  - '{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/research/domain-regulated-enterprise-airgap-ai-deck-market-research-2026-07-25.md'
externalResearchTargets:
  - 'https://github.com/presenton/presenton (the upstream repo we are repackaging — Next.js + FastAPI + Electron monorepo)'
  - 'https://github.com/presenton/presenton/blob/main/Dockerfile (current LibreOffice-based image we replace)'
  - 'https://github.com/presenton/presenton-export (release-only stub repo — source NOT published; releases ship index.js + convert-linux-x64 binaries)'
  - 'https://github.com/RaphaelRibes/pixitainer (BSD-3, prefix.dev/raphaelribes channel — image-build mechanism)'
  - 'python-pptx 1.0.2 on conda-forge (PPTX read/write engine; no thumbnail support — must be added via zipfile injection)'
  - 'python-docx on conda-forge (DOCX read engine for template-style-extractor)'
  - 'pymupdf on conda-forge (PDF parser for template-style-extractor; extracts text spans, fonts, colors, layout from text-based PDFs without rendering)'
  - 'pdfplumber on conda-forge (complement to pymupdf for layout/table reasoning)'
  - 'poppler + pdf2image on conda-forge (PDF→PNG rendering for OCR fallback path only)'
  - 'pytesseract + tesseract on conda-forge (OCR fallback for scanned/image-based PDFs in template-style-extractor)'
  - 'odfpy on conda-forge (optional — for .odp/.odt template support; pending usage signal)'
  - 'Pillow on conda-forge (image manipulation for thumbnail synthesis and slide-image overlays)'
  - 'llama.cpp on conda-forge (BSD-3, updated 2026-04-23) — production Tier-2/3 local LLM server, OpenAI-compatible HTTP'
  - 'llama-cpp-python on conda-forge (BSD-3, updated 2026-04-22) — Python bindings if needed for in-process inference'
  - 'copilot-api on conda-forge (already in this repo, recipe at recipes/copilot-api/) — dev-path bridge proxy'
  - 'litellm on conda-forge (already in this repo, recipe at recipes/litellm/) — multi-provider router for advanced bridge / production scenarios'
  - '{project-root}/docs/copilot-to-api.md — five-approach bridge pattern for dev-path Copilot-as-LLM-backend'
  - '{project-root}/docs/specs/copilot-bridge-vscode-extension.md — existing VSIX spec, 12 stories, includes Story 6 (Configure presenton); reused for THIS project'
  - 'playwright + playwright-python on conda-forge (Node + Python; browsers fetched separately, not bundled in conda artifact today)'
  - 'https://github.com/conda-forge/staged-recipes/issues/21431 (Chromium on conda-forge — three failed PRs: #5256, #7146, #11864; tracked as stretch goal only)'
  - 'https://github.com/conda-forge/pyppeteer-feedstock/issues/3 (bollwyvl 2020 proposal: bundle browser binary inside conda package — pattern to apply to playwright)'
  - 'https://github.com/pyppeteer/pyppeteer (officially unmaintained — recommends migration to playwright; ruled out)'
  - 'Playwright PLAYWRIGHT_DOWNLOAD_HOST env var (air-gap mirror pattern for browser binaries)'
projectName: 'presenton-pixi-image'
adoptionPattern: 'B-with-upgrade-path-to-C'
deliverableArtifacts:
  - 'presenton-export-node (new Node.js package, ~200–500 LOC, Playwright-based; replaces opaque presenton-export/index.js bundle; vendored in this project, source-available)'
  - 'pptx-assembler (new Python package; python-pptx + Pillow; replaces opaque convert-linux-x64 PyInstaller binary; consumes the same JSON/images.zip contract as the upstream binary; produces image-overlay + extracted text shapes — fidelity option B, matches current upstream behavior)'
  - 'pptx-thumbnail-inject (small utility; injects docProps/thumbnail.jpeg + [Content_Types].xml Override into PPTX zip; addresses dealbreaker C2 — likely folded into pptx-assembler)'
  - 'DROPPED 2026-07-25 (see Revision Log): template-style-extractor. Live upstream Presenton already does LibreOffice-free template import (stdlib zipfile+ElementTree for PPTX/DOCX/XLSX, native ODF, pdfplumber for PDF) with near-zero new dependencies, including the legacy .ppt/.doc rejection this PRD proposed inventing — no replacement component needed for v1.'
  - 'NEW 2026-07-25, Phase-0-gated (see Phase 0 exit 6): mem0ai + fastembed-vectorstore conda-forge recipes — unconditional Presenton memory/RAG dependencies, neither on conda-forge today; OR a documented v1 feature-drop of the memory/chat-history subsystem, whichever Phase 0 decides.'
  - 'playwright-with-chromium (new conda-forge recipe; bundles chrome-headless-shell binary inside the conda artifact at build-time; models on pyppeteer-feedstock#3 pattern; enables fully air-gapped runtime)'
  - 'presenton patches (replace presentation-export download with presenton-export-node package; replace convert-linux-x64 invocation with pptx-assembler; template-import needs no patch — upstream template import is already LibreOffice-free and conda-forge-clean, see Revision Log; minor docker-compose.yml UX patch to forward OPENAI_BASE_URL / ANTHROPIC_BASE_URL explicitly — ~3 LOC; LLM provider config already supported via llmai==0.2.8 + LLM=custom mode, no source patches needed)'
  - 'llmai conda-forge recipe (Apache-licensed unified LLM provider abstraction, version 0.2.8 on PyPI as of 2026-07-25 — exact-pinned by upstream, drifts fast, re-verify at submission time; transitive dep already in Presenton; needs conda-forge recipe submission if not already on the channel)'
  - 'copilot-bridge VSIX extension (existing spec at docs/specs/copilot-bridge-vscode-extension.md — reused for dev-path; verify Story 6 "Configure presenton" emits correct env-var names; package CI-built .vsix per Story 12)'
  - 'PyCharm/JetBrains dev-path docs (one-pager: how to point JetBrains AI Assistant or any OpenAI-compat client at the bridge daemon at localhost:4141; defers full JetBrains plugin to v2)'
  - 'OCP/OpenShift deployment manifests (Helm chart or kustomize overlays) supporting three-tier LLM provider config: Tier-1 internal endpoint, Tier-2 llama.cpp sidecar, Tier-3 init-container model fetch from internal registry'
  - 'GGUF model selection + benchmark report (recommended default: Qwen 2.5 7B Q4_K_M ~6GB RAM; smaller fallback: Llama 3.2 3B Q4 ~3GB RAM; subject to quality bench against Presenton prompt templates AND HuggingFace-mirror allowlist availability)'
  - 'Dependency manifest (full conda + npm + model list with transitive expansion) submitted as part of architecture sign-off; serves as input to security-review allowlist process'
  - 'Air-gap build playbook (delta on top of existing docs/enterprise-deployment.md) — mirror-entry requests to file, allowlist-gating order, recipe-submission timeline expectations'
  - 'pixi.toml + tasks for the runtime image'
  - 'pixitainer-produced OCI image consumable by podman compose'
  - 'conda-forge recipes for any other missing deps surfaced during discovery (e.g. spacy-model-en_core_web_sm, llamaindex/liteparse, presenton-export-node, pptx-assembler)'
  - 'tests/fixtures/upstream-baseline/v{N}/ — package-author golden-fixture set (captured ONLINE before air-gap cutover; AC-FX-AUTHOR-* prefix; clean-room reimpls must match byte/structurally per documented allowlist; SSIM ≥ 0.99 for image equivalence)'
  - 'tests/drift/ — recipe-maintainer online drift-detection harness (separate online weekly cron CI workflow; AC-FX-MAINT-* prefix; emits structured drift report distinguishing breaking vs benign drift; auto-files upstream-bump issue via .github/ISSUE_TEMPLATE/upstream-drift.md when breaking detected)'
  - 'tests/operational/ — day-2 operator smoke + health fixtures shipped INSIDE OCI image at /opt/presenton/tests/ (AC-FX-DAY2-* prefix; smoke deck + cred-rotation check + mark-broken-pinned-deps check; runs in air-gapped target env)'
  - 'tests/install/ — day-0 operator preflight fixtures (AC-FX-INSTALL-* prefix; registry-reachable, secrets-present, manifest-validates checks)'
  - 'Fixture-capture phase + cadence policy — documented architectural seam between online (capture) and air-gap (consumption) phases; path-watch on upstream presenton-export/ triggers refresh; signed manifests; fixture-changelog written on each refresh; "fixture maintainer" is a role/hat the recipe-maintainer wears, NOT new headcount'
hardConstraints:
  - 'No LibreOffice anywhere — not in runtime image, not as host dep, not on input or output side'
  - 'No non-conda-forge packages in the runtime image'
  - 'No non-pixi build steps in the image build'
  - 'Full air-gap (Q4 option B) — build CI runs inside the perimeter against an internal JFrog Artifactory mirror; zero external CDN access at build OR runtime'
  - 'All dependencies (conda + npm + GGUF models) must be on the internal mirror allowlist; restricted packages require pre-approved alternatives or a documented feature drop'
  - 'Browser binary (chrome-headless-shell or alternative Chromium) must be available on the internal JFrog mirror, OR vendored into the playwright-with-chromium recipe source — cannot fetch from Microsoft Playwright CDN inside the perimeter'
  - 'GGUF models for Tier-2/3 production LLM must be on the approved HuggingFace-mirror allowlist'
  - 'New conda-forge recipes authored by this project must complete upstream-merge + mirror-sync + security-review before deployment — adds delivery-timeline cost'
  - 'All browser binaries must be present in the image at OCI build time, not fetched at runtime'
  - 'Replacement components for opaque upstream binaries (presenton-export/index.js, convert-linux-x64) must be source-available and conda-forge-recipeable'
  - 'LLM provider must be operator-configurable via env vars (OPENAI_BASE_URL / ANTHROPIC_BASE_URL / GEMINI_BASE_URL); Presenton must accept any OpenAI-API-compatible endpoint with no code changes'
  - 'Default base image does NOT bundle a GGUF model — bundling is opt-in via sidecar pattern or volume mount (keeps base image <2GB instead of ~8GB)'
deferredStretchGoals:
  - 'chromium-on-conda-forge (staged-recipes#21431) — not a precondition; revisit after playwright-with-chromium proves the bundled-binary pattern'
  - 'Upstream presenton-export source request — file an issue asking the Presenton team to open-source the export bundle build pipeline; if successful, replace presenton-export-node with vendored upstream'
  - 'SVG→DrawingML fidelity tier for pptx-assembler — render slides to SVG via Playwright then convert to native PPTX shapes (option C-equivalent without HTML→shape lossiness); no conda-forge SVG→DrawingML library exists today, would be net-new work; inspired by ppt-master architecture'
competitiveIntel:
  - 'hugohe3/ppt-master (MIT, 10k+ stars, v2.5.0 2026-04-30) — competing AI deck product. Architecture: PDF/DOCX/URL/Markdown → external LLM API → SVG → DrawingML → editable PPTX. NOT a library; runs as AI IDE skill (Claude Code, Cursor, Copilot). Air-gap-incompatible (external LLM calls required). Being packaged for conda-forge as a skill bundle: staged-recipes PR #33132 and #33171 (open). Useful as architectural inspiration only; does not compose with our pipeline.'
discoveryNotes:
  - 'Adversarial review surfaced two dealbreakers: A1 (PPTX↔Marp round-trip is structurally lossy) and C2 (python-pptx omits docProps/thumbnail.jpeg)'
  - 'Gemini cross-check confirmed both dealbreakers and revealed Presenton uses LibreOffice for HTML→PPTX/PDF on the OUTPUT side and PPTX/DOCX→PDF on the INPUT side (template import)'
  - 'Code investigation revealed Presenton does NOT use Marp at all — slides are React/Next.js components rendered live by Puppeteer chrome-headless-shell against a running Next.js URL'
  - 'Earlier proposed pptx2marp-bridge-marp2pptx vendoring scope was solving the wrong problem and has been dropped'
  - 'presenton-export bundle source is NOT public; all six release tags point to a single empty commit containing only a 72-byte README.md'
  - 'convert-linux-x64 PyInstaller binary source is also not public; reverse-engineering or clean-room reimplementation is required'
  - 'Presenton API surface for Puppeteer is shallow: launch, newPage, goto({waitUntil:networkidle0}), setViewport, emulateMediaType("screen"), setContent, pdf({width,height,printBackground,margin}), screenshot, waitForSelector, waitForFunction, evaluate. No raw CDP, no displayHeaderFooter — clean drop-in target for Playwright.'
classification:
  projectType: infrastructure
  projectTypeSecondary: developer_tool
  projectTypeRationale: "Customer is handed this product (mandate from CISO/security team), not reaching for it (verb test, JTBD, John's PM lens). Therefore primary classification is infrastructure (deployable, provenance-defensible image + Helm/OCP topology). Developer_tool secondary because VSIX + 6 conda-forge recipes have independent value as developer-consumable artifacts (Winston). Infrastructure is decomposed into named sub-deliverables in PRD body (Helm chart, OCP manifests, JFrog mirror topology, LLM provider tiering) so the K8s/OCP work doesn't get under-spec'd. The VSIX gets a first-class section regardless of secondary classification rank — it's the primary editor-side delivery surface, not decoration."
  domain: general
  deploymentDomain: regulated-enterprise (air-gapped)
  domainRationale: "Product itself is horizontal (AI deck generation, applicable any industry). Deployment context = regulated-enterprise air-gapped (govtech/fintech/defense-adjacent customers; specific compliance bars like Section 508, FedRAMP NOT confirmed for v1 — surfaced as Open Question for step-02b). Plain-English label preferred over jargon (Paige) — names the constraint shape, not the customer-segment vibe."
  complexity: high
  complexityAxes:
    engineering:
      recipes: medium
      cleanroom: high
      platform: high
    supplyChain: very-high
  complexityRationale: "Engineering axis splits into three sub-axes (Amelia): recipes=medium (boring conda-forge work, well-understood shape), cleanroom=high (presenton-export-node and pptx-thumbnail-inject are clean-room reimpls of opaque upstream binaries with weak test oracles), platform=high (Helm + 3-tier LLM provider topology with sidecar lifecycle, fallback logic, allowlist gating). Supply-chain axis is very-high (multi-week security-review SLA per recipe through JFrog mirror, allowlist gating, browser-binary vendoring). Schedule should be driven by supply-chain axis, not engineering axis."
  projectContext: greenfield-with-brownfield-constraints
  projectContextRationale: "Work pattern is greenfield (designing new components from scratch — 5-7 recipes [revised 2026-07-25, was fixed at 6], fixture-capture phase, OCP manifests, fixture trees). Guardrails are brownfield (local-recipes monorepo conventions: pixi + rattler-build, v1 recipe.yaml, JFrog auth pattern via JFROG_API_KEY) and upstream Presenton API surface (llmai==0.2.8 integration [was 0.2.2], env-var contract, Puppeteer API surface for clean-room reimpl)."
  primaryUsers:
    - 'ocp-operator-day0 (platform engineer; day-0 install/configure/deploy; consumes Helm chart + manifests + JFrog mirror; preflight via tests/install/)'
    - 'ocp-operator-day2 (platform engineer; day-2 operate/patch/rotate-creds/respond-to-mark-broken; consumes tests/operational/ shipped inside the OCI image)'
    - 'recipe-maintainer (us, future-us, downstream conda-forge co-maintainer; verifies upstream drift, refreshes fixture set F when upstream Presenton ships new versions; ALSO wears "fixture maintainer" hat during online-capture phase)'
    - 'vscode-developer (in-scope for v1; installs sideload copilot-bridge VSIX; bridge daemon at localhost:4141 exposes OpenAI/Anthropic-compatible endpoints; Story 6 emits Presenton env vars)'
    - 'jetbrains-developer (out-of-scope for v1 packaging — explicit gap; v1 path = docs-only fallback pointing JetBrains AI Assistant or any OpenAI-compat client at localhost:4141; full JetBrains plugin deferred to v2)'
    - 'conda-forge-staged-recipes-reviewer (gatekeeper persona with veto power; five-to-seven recipes [revised 2026-07-25] = five-to-seven review cycles; classification surfaces this so PRD acceptance criteria can include lint-clean recipes, deterministic builds, rerender-survivability)'
    - 'end-web-user (OUT-OF-SCOPE — upstream Presenton owns this UX; we do not modify the React/Next.js UI)'
  buyer: "Platform/security team owning the OCP cluster — typically CISO + compliance officer + platform engineering director. Signs the PO; renews based on user-gate (output quality keeping ticket volume low)."
  referenceProductSubstituted: "Microsoft 365 Copilot for PowerPoint"
  referenceProductRationale: "Buyer chose this over commodity OSS substitutes (Marp, python-pptx+Jinja2) because those substitutes don't deliver Copilot-class capability (long-form-doc → exec deck summarization). Buyer can't have M365 Copilot itself because cloud-only with no on-prem/ATO path. JTBD = intersection of (Copilot-class capability) AND (survives security review). Existential competitive threat: Microsoft shipping on-prem Copilot SKU — tracked in competitive watchlist."
  supplyChainPosture: defensive-mirror-gated
  supplyChainPostureRationale: "Porter's-five lens: supplier power dominates because JFrog allowlist + Chromium binary + PyInstaller-replacement + clean-room reimpls = supply chain is simultaneously moat AND risk. Mary's strategic finding from Round 1."
  upstreamDriftRisk: high
  upstreamDriftRiskRationale: "Three clean-room reimpls (presenton-export-node, pptx-assembler, pptx-thumbnail-inject) means three divergence vectors against upstream Presenton releases; observed release cadence is faster than assumed (3 presenton-export tags in 6 days, sampled 2026-07-25 — see technical research report). tests/drift/ harness + path-watch on upstream presenton-export/ + auto-issue template are the mitigation. (John's flag, Round 1; cadence note added 2026-07-25.)"
workflowType: 'prd'
status: final
updated: 2026-07-25
---

# Product Requirements Document - presenton-pixi-image

**Author:** rxm7706
**Date:** 2026-04-30 (revised 2026-07-25)

## Revision Log (2026-07-25)

This PRD was revised against a technical research pass (`planning-artifacts/research/technical-presenton-stack-ocp-airgap-research-2026-07-25.md`) and a domain research pass (`planning-artifacts/research/domain-regulated-enterprise-airgap-ai-deck-market-research-2026-07-25.md`), distilled through `planning-artifacts/briefs/brief-presenton-pixi-image-2026-07-25/`. Full delta trail: `planning-artifacts/.memlog.md`. Six load-bearing deltas from the 2026-04-30 draft, all primary-sourced:

1. **`template-style-extractor` dropped from v1.** Live upstream Presenton (`servers/fastapi/services/office_document_service.py`, fetched 2026-07-25) already does LibreOffice-free template import — stdlib `zipfile`+`ElementTree` for DOCX/PPTX/XLSX, native ODF, `pdfplumber` (MIT) for PDF — with the exact legacy-`.doc`/`.ppt` rejection behavior this PRD proposed inventing. Recipe count drops from a fixed six to **five confirmed**, pending item 2.
2. **New Phase-0 gap: the memory/RAG subsystem.** `mem0ai` + `fastembed-vectorstore` are unconditional upstream dependencies, neither on conda-forge. New Phase-0 exit criterion 6 added (§ Phase 0 Exit Criteria) to decide: two more recipes, or a documented feature-drop.
3. **Risk R3 rewritten.** The 2026-04-30 draft's trigger ("Microsoft Copilot reaches IL5 GA," 12-24mo window) already happened without collapsing the JTBD — IL5 remains Azure Government cloud, not air-gapped. The real trigger, Microsoft's own disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24), is live now, and whether it includes a Copilot-for-PowerPoint-equivalent is unresolved — escalated to a Phase-0-blocking check, not a 12-24-month watch item.
4. **Risk R7 resolved/replaced.** PyMuPDF/AGPL is moot (template-style-extractor dropped; `pdfplumber`, MIT, is upstream's real and sufficient choice). Replaced with a smaller flag: `psycopg` (LGPL-3.0-only) for buyer legal review.
5. **`llmai` version corrected** 0.2.2 → 0.2.8 (PyPI-verified exact pin) throughout. Still Apache-2.0, still absent from conda-forge — the core claim was and remains correct.
6. **OpenShift Restricted SCC grounded** with current specifics (`restricted-v2` default: capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation; `restricted-v3` new-install default: adds pod-level user-namespace isolation) and a new risk (R9) naming the headless-Chromium-sandbox-vs-user-namespace-isolation interaction as an explicit Phase-0/architecture spike.

Everything else — classification, the 9-persona model, the buyer-gate/user-gate JTBD, the M365-Copilot-for-PowerPoint reference product, Q1/Q3/Q4 decisions, the competitive table, MVP/Growth/Vision scope shape, the measurable-outcomes table, Phase-0 exits 1-5 — carries forward from the 2026-04-30 draft unchanged; this is a revision, not a rewrite.

## Executive Summary

It's 11pm in a SCIF. The board deck is due at 8am. Microsoft Copilot is on the other side of the air gap. Today she builds it by hand. Tomorrow Presenton builds it for her.

`presenton-pixi-image` repackages the open-source Presenton AI deck-generation web app as a fully air-gapped OCI image deployable on RedHat OpenShift Container Platform (OCP). Built from five conda-forge-native recipes (plus up to two more, pending a Phase-0 memory-subsystem decision — see Revision Log) plus a sideloadable VS Code extension; assembled via pixi + pixitainer; no LibreOffice in the runtime — confirmed current as of 2026-07-25, upstream has none anywhere, not just on the output side.

**Target users (buyer → end user):**

1. **Buyer** — Platform/security team owning the OCP cluster (CISO + compliance + platform engineering director). Signs procurement once.
2. **OCP operator (day-0)** — Pulls image, configures LLM provider tier, deploys via Helm/manifests; preflight via `tests/install/`.
3. **OCP operator (day-2)** — Operates deployed cluster: rotates LLM credentials, patches CVEs (P95 14-day rebuild-and-resign capability, response SLO measured-and-conditional-on JFrog allowlist SLA ≤48h AND maintainer staffing), responds to mark-broken on pinned deps; smoke + health via on-image `tests/operational/`.
4. **Recipe-maintainer** — Verifies upstream-Presenton drift via online weekly cron (`tests/drift/`); refreshes fixture set on path-watch trigger.
5. **Analyst (end user)** — Generates brand-compliant, agent-refined decks from prompts + uploaded source material; refinement latency `<10s P95` on Tier-1 LLM endpoints (Tier-2 llama.cpp on CPU is async/batch UX, not interactive).
6. **VS Code developer** — Installs sideload `copilot-bridge` VSIX (sideload-only, no Marketplace); bridge daemon at `localhost:4141` exposes OpenAI/Anthropic-compatible endpoints for local Presenton testing.
7. **JetBrains developer** — In-scope for v1 via REST + OpenAPI spec + Postman collection; full JetBrains plugin deferred to v2.
8. **End web user of upstream Presenton** — OUT-OF-SCOPE; upstream owns the React/Next.js UI.
9. **Conda-forge staged-recipes reviewer** — Five-to-seven recipes = five-to-seven review cycles (revised 2026-07-25); PRD acceptance criteria include lint-clean recipes, deterministic builds, rerender-survivability.

**The problem being solved:** Air-gapped enterprises whose data classification prohibits the FedRAMP-cloud version of Microsoft 365 Copilot are stuck producing decks by hand — slower than LLM-assisted tooling AND systematically lower in language and style quality. M365 Copilot for PowerPoint is the reference shape but unavailable on the wrong side of the cloud-vs-on-prem boundary. Boring substitutes (Marp, python-pptx + Jinja2) trivially clear the provenance bar but fail the capability bar — they don't summarize internal long-form documents into review-ready decks.

**Jobs-to-be-Done — two gates that don't collapse:**

- **Buyer gate (signs the PO):** *"Give me a turnkey, mirrorable AI deck generator that produces zero exfiltration paths and zero unreviewed dependencies, so I can approve it once and forget it."*
- **User gate (drives renewal):** *"Turn my 40-page internal compliance/research/incident document into a 12-slide draft I'd rather edit than write from scratch, without leaving my secure workstation — and the second deck takes half the time of the first."* User-gate quality anchored at "better than writing it by hand at 2 a.m.", NOT at "M365 Copilot quality."

**Combined JTBD:** *Summarize internal documents into review-ready decks without the content leaving the air-gap perimeter — what we'll call **boundary-local inference** throughout this doc.*

**Why now:**

- **Technical readiness:** Presenton OSS is mature enough to repackage; conda-forge ecosystem (Playwright + Chromium-bundled-recipe pattern, llama.cpp, pixi/rattler-build) finally lets us ship this air-gap-clean in 2026.
- **Acute pain:** Hand-crafted decks are systematically inferior in speed AND in language/style quality versus LLM+Presenton output.
- **Window of opportunity (REVISED 2026-07-25 — see Revision Log item 3):** the 2026-04-30 draft's "12-24 months until IL5 GA" framing is falsified — GCC/GCC-High/DoD/IL5 Copilot GA already happened without collapsing this JTBD, because none of it is air-gapped. The real window is bounded by Microsoft's own disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local), GA worldwide **2026-02-24** — whether it already includes Copilot-for-PowerPoint-equivalent deck generation is unconfirmed and is now a **Phase-0-blocking verification item** (exit criterion 6), not a 12-24-month monitoring assumption. Treat the window as unknown-and-urgent, not comfortable.
- **Supply-chain math claim:** Five unsigned Python/Node/binary upstreams (revised from six — see Revision Log item 1) cannot pass an IL5 SBOM gate independently; one signed conda-forge OCI image with one SBOM can. The math only closes via repackaging.

### Differentiator

**Core insight (validated):** *"The buyer is paying for a Copilot-class deck generator they're allowed to install."* (Capability target: 70-85% parity with M365 Copilot for PowerPoint on long-form-doc summarization — analyst estimate based on feature-coverage comparison; methodology defined in Phase 0 evaluation plan; gap-closure tracked on roadmap.)

**The intersection that nothing else clears.** This product wins on the conjunction of **Copilot-class capability** AND **survives security review**. Among evaluated alternatives, the only product delivering both halves without an exfiltration path:

| Substitute | Why it loses |
|---|---|
| Marp / Marpit, python-pptx + Jinja2 templates (DIY power-user floor) | Trivially clears provenance; fails capability (no LLM long-form summarization). |
| LibreOffice Impress + local LLM plugins (open-source floor) | Air-gap-deployable but lacks integrated agent-orchestration UX for deck-class workflows. |
| M365 Copilot for PowerPoint | Reference shape; cloud-only; unavailable to customers whose data classification prohibits the FedRAMP-cloud version. |
| SlidesGPT / Gamma / Tome | SaaS, cloud-only — air-gap-incompatible. Shape end-user expectations but cannot be deployed. |
| hugohe3/ppt-master | AI IDE skill (Claude Code, Cursor, Copilot); requires external LLM API; air-gap-incompatible by design. |

**Customer-facing supply-chain framing:** *Today the customer integrates five unsigned upstream artifacts (revised 2026-07-25, was six) and owns the integration risk. With this, they integrate one signed artifact and we own the integration risk* — attested via the build-provenance section of this PRD. The five conda-forge recipes (plus up to two more, pending the Phase-0 memory-subsystem decision) + Chromium-vendoring + clean-room reimpls + JFrog mirror integration are the price of admission to the capability-plus-defensibility intersection. Each artifact is a receipt proving the platform team is permitted to install Copilot-equivalent capability inside the perimeter.

**Architecture cohesion:** The 6 recipes compose into a single OCI image; the image deploys as a standard Helm chart on OCP; the chart consumes a Tier 1/2/3 LLM endpoint as configuration, not as a bundled component.

### v1 Deliverables

**Five conda-forge recipes confirmed (each gated on a 4-check validation pattern: build + validate + scan + optimize), plus up to two more pending a Phase-0 decision:**

- `presenton-export-node` — Node + Playwright bundle; replaces opaque upstream `presenton-export/index.js`.
- `pptx-assembler` — python-pptx + Pillow; replaces opaque upstream `convert-linux-x64`; produces image-overlay + extracted text shapes.
- `pptx-thumbnail-inject` — `docProps/thumbnail.jpeg` injection for AI-generated decks.
- `playwright-with-chromium` — Playwright + bundled `chrome-headless-shell` for air-gap.
- `llmai` — Apache-licensed unified-LLM-provider abstraction (used by upstream Presenton; pinned `0.2.8` as of 2026-07-25, upstream re-pins fast, re-verify at submission time).

**DROPPED 2026-07-25:** `template-style-extractor` — live upstream Presenton already implements LibreOffice-free template import (stdlib `zipfile`+`ElementTree` for PPTX/DOCX/XLSX, native ODF, `pdfplumber` for PDF), including the legacy-`.doc`/`.ppt`-rejection behavior this recipe was going to (re)build. See Discovery & Re-Architecture and Decisions Log Q2 below.

**Phase-0-gated (new 2026-07-25):** `mem0ai` + `fastembed-vectorstore` — unconditional Presenton memory/RAG dependencies, neither on conda-forge today. Phase 0 exit criterion 6 decides: add both as recipes 6-7, or ship v1 with the memory/chat-history subsystem disabled.

**One VS Code extension:** `copilot-bridge` (sideload-only, no Marketplace; spec at `docs/specs/copilot-bridge-vscode-extension.md`).

**Five v1 platform additions** (each with explicit scope from R3 reclassification):

- **Brand-compliance enforcement** — three-lane UX framework: auto-fix high-confidence, batched-review mid-confidence, ignore low-confidence + strict-mode opt-in. Thresholds TBD pending Phase 0 spike.
- **Agent orchestration** — Presenton-existing only (pinned to specific Presenton release tag, set in Phase 0); not net-new build.
- **Observability** — Prometheus `/metrics` endpoint, scrapeable + non-blocking; no dashboards shipped.
- **Chargeback** — rides the same `/metrics` endpoint as observability; emit-only, no ledger.
- **LLM use-case approval workflow** — documentation only, not software.

### Landing Conditions (4 guardrails)

1. Engineering complexity is honestly re-rated whenever v1 scope expands (exercised already: `engineering: recipes=medium-high, cleanroom=high, platform=very-high`; supply-chain=very-high).
2. CVE-response cycle is **measured-and-conditional-on-JFrog-SLA** (per-segment SLA for upstream-patch + recipe-rebuild + JFrog-allowlist-sync), not assumed.
3. Brand-compliance enforcement: thresholds sized as a research spike; the UX-band design (auto-fix / batched-review / ignored + strict-mode) is a v1 commitment, not deferred.
4. The "knowledge-base integration = vision, not v1" boundary is held against customer pressure; v1 is explicitly scoped to "decks where source material fits in prompt + uploaded files." Fixture-capture sequencing defined in Test Strategy section (Phase 0 boundary).

### LLM Dependency (Explicit)

Customer must have at least one approved LLM endpoint (tier selection covered in deployment guide):

- **Tier 1** — Internal corporate proxy at `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` / `GEMINI_BASE_URL` (operational targets measured against Tier 1).
- **Tier 2** — `llama.cpp` sidecar with allowlisted GGUF model from HuggingFace mirror (Qwen 2.5 7B Q4_K_M default, Llama 3.2 3B Q4 fallback; async/batch UX, not interactive).
- **Tier 3** — Init-container fetches GGUF from internal artifact registry (JFrog Artifactory or equivalent) at startup.

Reference LLM class for measurable cost/latency targets selected in Phase 0 (initial discovery + benchmark-definition phase before v1 development; candidates: vLLM-served 70B-class GPU, Azure OpenAI tenant endpoint, on-prem Llama-3-70B).

### Continuity Plan (if upstream Presenton stalls or maintainer team turns over)

Maintainer-team independence covers all three engineering axes (recipes, cleanroom reimpls, platform): conda-forge recipes are mainline-eligible (any conda-forge maintainer could take over); cleanroom reimpls are documented and source-available; platform manifests are vanilla Helm/kustomize. Fixture-capture phase + drift-detection harness make ownership transferable across team turnover.

## Project Classification

- **Project type:** `infrastructure` (primary) + `developer_tool` (secondary). Customer is *handed* this product (mandate from CISO/security team), not *reaching for* it. Infrastructure decomposes into named sub-deliverables (Helm chart, OCP manifests, JFrog mirror topology, LLM provider tiering); the VSIX is a first-class delivery surface regardless of secondary classification rank.
- **Domain:** `general` (product). **Deployment domain:** `regulated-enterprise (air-gapped)`. Product is horizontal (AI deck generation, any industry); deployment context is govtech/fintech/defense-adjacent customers whose data classification prohibits cloud SaaS.
- **Complexity:** `high` with split axes —
  - **Engineering:** `recipes=medium-high`, `cleanroom=high`, `platform=very-high` (re-rated from "high" per guardrail #1 to honestly account for the 5 v1 platform-layer additions).
  - **Supply-chain:** `very-high` — multi-week security-review SLA per recipe through JFrog mirror, allowlist gating, browser-binary vendoring.

  Schedule should be driven by the supply-chain axis, not the engineering axis.
- **Project context:** `greenfield-with-brownfield-constraints` (building 6 recipes + fixture-capture phase + OCP manifests + 4 fixture trees from scratch, but constrained by upstream Presenton API surface and local-recipes monorepo conventions: pixi + rattler-build, v1 recipe.yaml, JFrog auth pattern via `JFROG_API_KEY`).

## Discovery & Re-Architecture (step-01b)

### Original assumption (step-01-init)
Repackage Presenton as a conda-forge OCI image by vendoring `hnrobert/pptx2marp` + `ebibibi/marp2pptx` into a single `pptx2marp-bridge-marp2pptx` Python package, replacing every LibreOffice-based path with bridge calls.

### Why that assumption collapsed

1. **Adversarial review** flagged two dealbreakers:
   - **A1.** PPTX ↔ Marp round-trip is structurally lossy — the two data models (OOXML object graph vs. constrained Markdown grammar) are fundamentally incompatible.
   - **C2.** `python-pptx` does not embed `docProps/thumbnail.jpeg`, so AI-generated decks land in PowerPoint/Finder/Explorer with placeholder thumbnails 100% of the time.

2. **Gemini cross-check** (gemini-2.5-pro) confirmed both dealbreakers and added that the OOXML thumbnail injection via `zipfile` + `[Content_Types].xml` Override is the standard LibreOffice-free workaround.

3. **Code investigation** of `presenton/presenton` revealed:
   - Presenton does **not use Marp**. Slides are React/Next.js components rendered live in a running Next.js server.
   - The export pipeline is `Puppeteer chrome-headless-shell → Next.js URL → page.pdf() / page.screenshot() → JSON+images.zip handoff → convert-linux-x64 (PyInstaller binary) → final .pptx`.
   - LibreOffice was, at the time of this discovery pass, on the **input side** (template import: uploaded PPTX/DOCX → soffice → PDF → screenshots → AI extraction), gated by `ARG INSTALL_LIBREOFFICE=true`. **CORRECTED 2026-07-25:** re-verified against current upstream `main` — LibreOffice is gone entirely, not even on the input side. No `ARG INSTALL_LIBREOFFICE`, zero `soffice` references anywhere in the repo (code search confirmed). Template import (`servers/fastapi/services/office_document_service.py`) now runs on pure stdlib (`zipfile`+`ElementTree`) for DOCX/PPTX/XLSX, native ODF support, and `pdfplumber` (MIT) for PDF text extraction — LibreOffice-free, near-zero new dependencies, and it already rejects legacy `.doc`/`.ppt`/`.xls`/`.rtf` with the same "save in a modern format" behavior this PRD independently proposed inventing (see Decisions Log Q2, revised). This upstream change happened sometime between this draft's original 2026-04-30 authoring and the 2026-07-25 revision pass — a reminder that Presenton moves fast and every "current state of upstream" claim in this document has a shelf life.
   - The export bundle (`index.js`, ~6 MB minified Node) and the PPTX assembler (`convert-linux-x64`, ~50 MB PyInstaller) are downloaded from `presenton/presenton-export` releases at build time. **Source for both is not published** — the repo contains only release artifacts.

4. **Conda-forge ecosystem check**:
   - `pyppeteer` is officially unmaintained; upstream recommends Playwright. Ruled out.
   - `playwright` (Node) and `playwright-python` are on conda-forge but do **not** bundle browser binaries; `playwright install` fetches at runtime. Air-gap-hostile by default; supports `PLAYWRIGHT_DOWNLOAD_HOST` mirror.
   - `chromium` is **not** on conda-forge. Three PRs (#5256, #7146, #11864) failed; staged-recipes#21431 tracks intent but the issue opener himself doubts it's worth the effort.
   - Bundled-binary pattern from `pyppeteer-feedstock#3` (bollwyvl, 2020) is the realistic path: build a `playwright-with-chromium` recipe that downloads the browser at conda-build time and ships it inside the conda artifact.

### New architecture

Four replacement components, each source-available and conda-forge-recipeable:

| Component | Replaces | Stack | Approx. size |
|---|---|---|---|
| `presenton-export-node` | `presenton-export/index.js` (opaque minified bundle) | Node + Playwright + Chromium | ~200–500 LOC |
| `pptx-assembler` | `convert-linux-x64` (opaque PyInstaller binary) | Python + python-pptx + Pillow | ~500 LOC |
| `pptx-thumbnail-inject` | (gap — no upstream solution) | Python + zipfile + Pillow | ~100 LOC, may fold into `pptx-assembler` |
| `playwright-with-chromium` | (gap — Playwright doesn't bundle browser on conda-forge) | conda-forge recipe; bundles `chrome-headless-shell` at build time | recipe + ~150 MB binary |

Plus Presenton patches: swap the upstream binary fetch for the new packages, flip `INSTALL_LIBREOFFICE=false`, and either drop or rewrite the template-import path that currently relies on `soffice --convert-to pdf`.

## Decisions Log

- **Q1 — Editable PPTX fidelity bar:** Option **(b)** image-overlay + extracted text shapes. Matches upstream `convert-linux-x64` behavior. User retains visual fidelity to web preview AND ability to edit text (fix typos, change names, copy text out, screen-reader-readable, search works). Trades away: theme/master changes, element-level animations, native chart objects, length-tolerant text edits. Industry norm for AI-deck SaaS.
- **Q2 — Template-import feature scope [SUPERSEDED 2026-07-25 — see Revision Log item 1].** Original 2026-04-30 decision: reimplement on conda-forge-native libraries via a new `template-style-extractor` component (`.pptx` via python-pptx, `.docx` via python-docx, `.pdf` via pymupdf text-based + pdf2image/pytesseract OCR fallback; ODP/ODT via odfpy deferred; legacy `.ppt`/`.doc` dropped with a clear error). **Revised decision:** build nothing — live upstream Presenton (`servers/fastapi/services/office_document_service.py` + `documents_loader.py`, verified 2026-07-25) already ships exactly this shape, LibreOffice-free, using only the Python standard library (`zipfile`+`ElementTree`) for DOCX/PPTX/XLSX, native ODF support (no `odfpy` needed), and `pdfplumber` (MIT, already conda-forge-available) for PDF text — plus the identical legacy-format rejection this PRD had independently proposed. No OCR fallback exists upstream (no `pytesseract`/`pdf2image` dependency), so scanned-PDF support remains a genuine gap, but it is a net-new capability question, not a "replace LibreOffice" one — if a buyer needs it, scope it separately in a later cycle, don't fold it into this repackaging effort. Net effect: `template-style-extractor` is dropped from v1 entirely; the pipeline Presenton already runs (`parse → JSON → LLM`, no rendering, no browser, no LibreOffice) is directly reusable as-is.
- **Q3 — AI/LLM provider strategy (two paths):**
  - **Dev path:** Reuse the existing `copilot-bridge` VSIX (spec: `docs/specs/copilot-bridge-vscode-extension.md`). Developer with VS Code or PyCharm + GitHub Copilot subscription installs the sideload-only `.vsix`; bridge daemon (`copilot-api`, recipe in this repo) runs on `localhost:4141` and exposes OpenAI/Anthropic-compatible endpoints. Story 6 ("Configure presenton") emits Presenton env vars. PyCharm support: docs-only one-pager pointing JetBrains AI Assistant at the same daemon — no separate JetBrains plugin in v1 (defers v2).
  - **Production path:** Three-tier configurable LLM provider, all OpenAI-compatible, operator picks at deploy time:
    - Tier 1 (default for OCP) — internal corporate LLM proxy via `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` / `GEMINI_BASE_URL` env vars; no in-image model.
    - Tier 2 — bundled local LLM via `llama.cpp` sidecar (conda-forge), GGUF model mounted from volume; default Qwen 2.5 7B Q4_K_M (~6GB RAM) or fallback Llama 3.2 3B Q4 (~3GB RAM).
    - Tier 3 — init-container fetches GGUF from internal artifact registry (JFrog/Harbor/S3) at startup, mounts to shared volume; model lifecycle managed centrally.
  - Same Presenton code on both paths; only env-var config differs. Air-gap-clean by construction (Tier 1 endpoint inside perimeter; Tier 2/3 fully in-image / in-cluster).
- **Q4 — Air-gap definition:** Option **(b) Full air-gap.** Build CI runs inside the perimeter against an internal JFrog Artifactory mirror; mirror holds curated subsets of conda-forge, npm, HuggingFace (and possibly more). Some packages are restricted; some GGUF models are restricted. Implies: (i) every dependency must be allowlisted on the mirror or the build fails; (ii) net-new conda-forge recipes authored by this project must complete upstream-merge → mirror-sync → security-review before deployment; (iii) build-time external CDNs (Microsoft Playwright CDN for chrome-headless-shell, etc.) cannot be reached and must be either mirrored or vendored. Existing infrastructure: `docs/enterprise-deployment.md` and the `check_dependencies` MCP tool already support JFrog Artifactory + auth env vars (`JFROG_API_KEY`).
- **Q5 — Project classification (step-02-discovery, validated through 5-method advanced elicitation + 2 party-mode rounds, 6 BMAD agents, 3 cross-talk pairings):** Locked. See `classification:` block in frontmatter for full structure. Key shifts from initial proposal: (i) projectType flipped from `web_app` to `infrastructure` primary on the JTBD verb test (John: nobody reaches for this; they're handed it), with `developer_tool` secondary for the VSIX + recipes-as-artifacts surface. (ii) Engineering complexity split into three sub-axes (recipes=medium, cleanroom=high, platform=high) — Amelia's flag that "medium" was dishonest given clean-room reimpls. (iii) primaryUsers expanded from 3 to 7 with explicit out-of-scope marking (recipe-maintainer added by 3 agents independently; OCP operator split day-0/day-2 by Sally; jetbrains-developer flagged as packaging gap not silent omission; conda-forge-staged-recipes-reviewer added as gatekeeper persona by Mary). (iv) Domain language plain-English fixed: `regulated-enterprise (air-gapped)` instead of `govtech-adjacent` (Paige). (v) New strategic frontmatter fields: `buyer`, `referenceProductSubstituted` (M365 Copilot for PowerPoint — Mary's finding), `supplyChainPosture: defensive-mirror-gated` (Porter's five lens), `upstreamDriftRisk: high` (John). (vi) JTBD reframed by Mary→John dialogue from "deck generation" → "defensible provenance" → final form: **inference-at-the-edge of a security boundary** (intersection of Copilot-class capability AND survives security review). See JTBD section below for two-gate buyer/user form.
- **Q6 — Product vision (step-02b, validated through 5-method advanced elicitation [Hindsight, What-If, Shark Tank, Failure Mode, Critique] + party-mode round 3 with all 6 BMAD agents):** Locked. 13 deltas applied to working vision model; full vision content lands in Executive Summary (step-02c). Key shifts from initial-answer vision: (i) Latency target conditional on LLM tier — `<10s P95 Tier 1+3; Tier 2 documented as async/batch` (Winston, Amelia). (ii) CVE-response 14d reframed as "rebuild-and-resign capability within 14 days; response SLO contingent on JFrog allowlist SLA ≤48h AND maintainer staffing tier" (Winston, Amelia, Mary). (iii) Five v1 scope additions re-classified rather than wholesale-added: brand-compliance enforcement = v1 with UX-band spec (auto-fix/batched-review/ignored), agent-orchestration = clarify Presenton-today vs add-on (likely already-there), observability = scope to "scrapeable + non-blocking" not "instrument from scratch", chargeback = scope to "emit metrics" not "build ledger", LLM-approval-workflow = move to documentation rather than software (John, Mary, Amelia, Sally). (iv) Engineering complexity re-rated per guardrail #1: platform high→very-high, recipes medium→medium-high, cleanroom unchanged (John, Amelia). (v) Window of opportunity reframed: "Window closes when Microsoft Arc-connected Copilot reaches IL5 GA (12-24mo, tracked)" — replaces unsourced "18-24mo on-prem" estimate (Mary, Paige). (vi) Knowledge-base deferral made explicit: v1 use case = "decks where source material fits in prompt + uploaded files"; deep-internal-data decks excluded (Sally). (vii) JetBrains gap owned: REST + OpenAPI spec + Postman collection in v1 (Sally). (viii) "WE ARE the supply chain" kept as internal posture; customer-facing translation: "Today the customer integrates six unsigned upstream artifacts and owns the integration risk; with this, they integrate ONE signed artifact and we own the integration risk" (Paige). (ix) FedRAMP language reworded as factual constraint, not verdict (Paige). (x) Continuity plan extended to cover cleanroom + platform engineering, not just recipes (John). (xi) LLM-class taxonomy added: targets measured against named reference LLM class (Mary). (xii) Confidence qualifier added to "Copilot-class" claim — Buyer should know if v1 is 70%/85%/100% Copilot-equivalent (John). (xiii) Brand-compliance UX bands as v1 commitment (auto-fix high-confidence, batched-review mid-confidence, ignore low-confidence with strict-mode opt-in) — not deferred to a future spike (Sally). Core insight UNCHANGED and validated by all six agents: "The buyer is paying for a Copilot-class deck generator they're allowed to install."

## Jobs-to-be-Done

The classification's `referenceProductSubstituted: M365 Copilot for PowerPoint` is load-bearing — it explains why boring substitutes (Marp, python-pptx + Jinja2) lose despite trivially-better provenance, and what the AI part actually buys the customer. The JTBD has two gates that don't collapse:

**Buyer gate (signs the PO):**
> "Give me a turnkey, mirrorable AI deck generator that produces zero exfiltration paths and zero unreviewed dependencies, so I can approve it once and forget it."

**User gate (drives renewal):**
> "Turn my 40-page internal compliance/research/incident document into a 12-slide draft I'd rather edit than write from scratch, without leaving my secure workstation."

Buyer signs because of gate 1. Buyer renews because of gate 2 — if user output is unusable, ticket volume rises, head-of-research calls CISO, deal dies. **Anchor user-gate quality at "better than writing it by hand at 2 a.m." NOT at "M365 Copilot quality"** — anchoring on M365 loses; anchoring on the by-hand baseline is achievable with Presenton's actual capabilities.

The combined JTBD: **inference-at-the-edge of a security boundary** — long-form internal-document summarization into review-ready decks, where "at the edge" means: the boundary is the customer's air-gap, and our five-to-seven recipes (revised 2026-07-25) + Helm chart + clean-room reimpls + JFrog mirror integration are the receipts that prove the analyst is allowed to do this.

## Risk Register

| ID | Risk | Severity | Owner | Mitigation |
|---|---|---|---|---|
| R1 | `pptx-thumbnail-inject` is the one novel recipe — python-pptx has no thumbnail support and no conda-forge recipe synthesizes OOXML thumbnails today | High | recipe-maintainer | Spike story before estimate; pick rendering method (LibreOffice headless? python-pptx slide render? Pillow synthesis from rendered HTML PNG?) before sprint planning — gates entire image generation path (Winston, Amelia) |
| R2 | Upstream Presenton drift — 6 clean-room artifacts = 6 divergence vectors when upstream ships v2.0 | High | recipe-maintainer | `tests/drift/` online weekly cron + `.github/ISSUE_TEMPLATE/upstream-drift.md` auto-fired on breaking drift; path-watch on upstream `presenton-export/` triggers fixture-capture refresh (John, Sally) |
| R3 | **[REVISED 2026-07-25]** Microsoft ships a disconnected/on-prem Copilot-equivalent — JTBD collapses. **Old trigger falsified:** GCC/GCC-High/DoD/IL5 Copilot GA already happened (2025-2026) without collapsing the JTBD — those tiers are Azure Government cloud, not air-gapped. **Real trigger, already live:** Microsoft's own disconnected stack — Azure Local disconnected operations + Microsoft 365 Local + Foundry Local — GA'd worldwide 2026-02-24, explicitly targeting "government, healthcare, and finance" sovereign/data-residency buyers. Whether the Copilot deck-generation application layer rides on this infrastructure today is **unconfirmed**. | Existential, and no longer low-probability-future — the infrastructure precondition already shipped | strategic / steering | **Phase-0-blocking** (new exit criterion 6, shared with the memory-subsystem decision — see § Phase 0 Exit Criteria): confirm or rule out Copilot-deck-generation inclusion in Microsoft 365 Local disconnected before further build investment. Audit the existing RSS/keyword-watch mechanism (`on-prem`/`sovereign`/`air-gap`/`disconnected` keywords) — it appears to have missed the 2026-02-24 announcement; fix its channel coverage. Pivot plan unchanged: harvest the conda-forge recipes as standalone tools, retire the OCI image (Mary). |
| R4 | JFrog mirror security-review SLA blocks recipe submission for multi-week periods per recipe — 6 recipes × multi-week = months of supply-chain delay | High | platform-engineer + recipe-maintainer | Submit dependency manifest + air-gap build playbook as part of architecture sign-off (Q4 deliverable); parallelize submissions; pre-stage allowlist requests during step-03 |
| R5 | Microsoft Playwright CDN not mirrored on JFrog — `playwright-with-chromium` recipe can't fetch chrome-headless-shell at conda-build time | Medium | platform-engineer | Sub-question (h) — investigate during step-02b; fallback options: vendor binary into recipe source, use already-mirrored Chromium binary, or pivot to ungoogled-chromium |
| R6 | Fixture-capture phase boundary collapses — someone tries to refresh F from inside air-gap and discovers they can't | Medium | recipe-maintainer | Architectural-seam callout in test strategy; "fixture maintainer" role wears recipe-maintainer hat during online-capture phase (Sally); cadence policy = refresh on path-watch trigger, online-only |
| R7 | **[RESOLVED/REPLACED 2026-07-25]** PyMuPDF AGPL/Artifex dual-license blocks allowlist — **moot**: `template-style-extractor` is dropped (Decisions Log Q2, revised), and upstream Presenton's actual PDF dependency is `pdfplumber` (MIT), never PyMuPDF. New, smaller flag replacing this row: `psycopg` (LGPL-3.0-only) is a direct Presenton backend dependency, a different obligation class than the Apache/MIT-dominated rest of the stack. | Low | platform-engineer | Flag for buyer legal/compliance review alongside the JFrog allowlist gap analysis (Phase 0 exit 4); likely acceptable on most enterprise allowlists but not asserted without buyer confirmation. |
| R8 | JetBrains developer population blocked — VSIX is VS Code only, no v1 plugin | Low (v1 acceptable gap) | PM | Explicit docs-only fallback path documented; revisit in v2 if pilot-customer JetBrains share warrants the plugin work |
| R9 | **[NEW 2026-07-25]** Headless-Chromium sandbox model may conflict with OpenShift `restricted-v3`'s pod-level user-namespace isolation (`hostUsers: false`, default for new OCP installs). Chromium's conventional container workaround (`--no-sandbox`) may be required regardless, may be redundant-but-harmless under OCP's own isolation, or may need a different SCC (e.g. `nonroot-v2`) — not yet spiked against a real cluster. | Medium | platform-engineer | Named Phase-0/architecture-phase spike, not assumed away; `--no-sandbox` (if needed) must be an explicit, buyer-documented security decision, not a silent default. See technical research report § 2.2. |

## Test Strategy (4 Fixture Sets + Phase Boundary)

A clean-room reimpl of opaque upstream binaries is meaningless without a test oracle. We have four distinct fixture sets, each with a different purpose, audience, and network posture. Phase boundary: **fixture-capture happens online, fixture-consumption happens air-gapped** — this is an architectural seam that must be documented or it collapses on first refresh attempt.

### Fixture Set 1 — `tests/fixtures/upstream-baseline/v{N}/` (package-author, AC-FX-AUTHOR-*)
- Captured ONCE per upstream Presenton version while internet exists
- Anchors clean-room reimpls (`presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`)
- Air-gapped CI gate: AC-FX-AUTHOR-01 = byte/structurally equivalent (zip-entry order normalized, timestamps normalized); AC-FX-AUTHOR-02 = SSIM ≥ 0.99 for image equivalence (NOT byte-equivalence — pin tolerance explicitly)
- Capture script: `tests/capture_upstream.py --version <V> --output tests/fixtures/upstream-baseline/v<V>/` runs ONCE, commits artifacts, never re-runs in CI

### Fixture Set 2 — `tests/drift/` (recipe-maintainer, AC-FX-MAINT-*)
- Online weekly cron CI workflow (separate from air-gapped build pipeline)
- Detects drift between Set 1 and current upstream
- AC-FX-MAINT-01 = `recapture.py` runs against latest upstream and emits structured drift report (added/removed/changed fixtures, per-fixture diff summary)
- AC-FX-MAINT-02 = report distinguishes **breaking drift** (clean-room reimpl will diverge) from **benign drift** (upstream cosmetic change, our reimpl still semantically correct); categorization rules in `tests/drift/README.md`
- AC-FX-MAINT-03 = breaking drift triggers `.github/ISSUE_TEMPLATE/upstream-drift.md` auto-issue with diff body
- NOT a CI gate — failure files an issue, doesn't break the build

### Fixture Set 3 — `tests/operational/` (day-2 operator, AC-FX-DAY2-*)
- Shipped INSIDE the OCI image at `/opt/presenton/tests/`
- AC-FX-DAY2-01 = post-deploy smoke runs `minimal-deck.json` end-to-end, asserts output `.pptx` opens (zip integrity + minimum slide count); 60s budget
- AC-FX-DAY2-02 = credential-rotation runbook executes `rotation-check.sh` and verifies LLM endpoint reachable with new creds, no app restart
- AC-FX-DAY2-03 = mark-broken response — `check-pinned-deps.sh` reports flagged-broken deps via conda-forge repodata-patches; gates rollback decision
- Air-gapped runtime; no upstream comparison; purely "does this image still work"

### Fixture Set 4 — `tests/install/` (day-0 operator, AC-FX-INSTALL-*)
- Day-0 preflight; runs in target environment before first `oc apply`
- AC-FX-INSTALL-* = registry-reachable, secrets-present, manifest-validates, JFrog auth working, GGUF model present (if Tier-2/3)

### The Phase Boundary
Fixture Set 1 is **captured online** by the recipe-maintainer wearing the "fixture maintainer" hat; the rest of the pipeline is air-gapped. This is a documented architectural seam — sprint-planning must allocate an explicit online-capture session before air-gap CI can run. Cadence: path-watch on upstream `presenton-export/` triggers refresh; signed manifest committed per refresh; fixture-changelog written with every refresh explaining intentional vs unintentional drift.

## Competitive Context

| Substitute | Why it doesn't displace us |
|---|---|
| **Marp / Marpit** | Markdown-to-slides; no LLM; no long-form summarization. Gives provenance for free but fails capability gate. |
| **python-pptx + Jinja2 templates** | Stamping templates; no AI generation; no long-form summarization. Same as Marp — boring path with provenance, fails capability. |
| **Microsoft 365 Copilot for PowerPoint** | THE reference shape. Cloud-only (incl. GCC/GCC-High/DoD/IL5 — all Azure Government cloud, none air-gapped), no disconnected/on-prem SKU confirmed for the Copilot application layer itself. Buyer can't have it, which is *why this product exists*. **Existential threat, status REVISED 2026-07-25: Microsoft's own disconnected infrastructure stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local) already shipped 2026-02-24 — whether the Copilot deck-generation layer rides on it is unconfirmed** (Risk R3). |
| **SlidesGPT / Gamma / Tome** | SaaS, cloud-only. Air-gap-incompatible. Shape end-user expectations though — anchoring user-gate at "M365 quality" loses; anchor at "better than 2am-by-hand" instead. |
| **hugohe3/ppt-master** | AI IDE skill (Claude Code, Cursor, Copilot); requires external LLM API; air-gap-incompatible by design. Useful as architectural inspiration (SVG→DrawingML approach) but not a competitor in our deployment context. |

**Strategic positioning:** This product wins on the intersection: Copilot-class capability that survives security review. Strip either half (capability OR defensibility) and a cheaper substitute exists. The 6 conda-forge recipes + Chromium-vendoring + PyInstaller-replacement + JFrog mirror integration are the price of admission to that intersection — they're what proves the buyer is *allowed* to install Copilot-equivalent capability inside the perimeter.

## Open Questions

*All four gating questions resolved. Sub-questions a–j land during step-02b/03 (architecture/sprint planning). Items 5–12 below are tracking-only.*

### Sub-questions surfaced from Q3 (resolve during step-02b/03)
- **a.** ✅ **Resolved (Verdict B+), re-verified 2026-07-25.** Presenton routes all LLM traffic through `llmai` (Apache-licensed unified provider abstraction), now pinned `==0.2.8` (was `0.2.2` at original drafting — upstream re-pins fast, six releases in the interval; re-verify again at submission time). First-class `LLM=custom` mode with `CUSTOM_LLM_URL` + `CUSTOM_LLM_API_KEY` env vars covers Tier-1 (internal proxy), Tier-2 (llama.cpp sidecar), and dev path (Copilot bridge) without any source patches — confirmed still present in `utils/get_env.py` (`get_custom_llm_url_env`/`get_custom_llm_api_key_env`). Optional ~3 LOC docker-compose.yml UX polish to forward `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` explicitly. New conda-forge dep: `llmai` (recipe submission needed — confirmed absent from conda-forge as of 2026-07-25 via `api.anaconda.org` lookup). Evidence: `servers/fastapi/utils/llm_config.py`, `servers/fastapi/utils/get_env.py`, `servers/fastapi/pyproject.toml`.
- **b.** Existing `copilot-bridge` extension VSIX packaging — is Story 12 (CI builds `.vsix` on tag) implemented yet, or still TODO?
- **c.** PyCharm support depth — confirmed docs-only for v1; full JetBrains plugin deferred to v2.
- **d.** Tier-2 model pick — Qwen 2.5 7B Q4_K_M vs Llama 3.2 3B Q4 vs Phi-3.5 — needs a small bench-off against Presenton's actual prompt templates; ALSO subject to mirror allowlist (sub-question g).

### Sub-questions surfaced from Q4 (resolve during step-02b/03)
- **e.** Internal JFrog conda-forge mirror — what subset is currently mirrored, and what is the SLA for adding new packages? (Drives feasibility timing for net-new recipes.)
- **f.** Internal JFrog npm registry mirror — full transitive coverage or curated? (Drives feasibility of `presenton-export-node` and the Node export bundle.)
- **g.** Approved GGUF models on the HuggingFace mirror — what's the current allowlist? (Drives Tier-2 default pick; may force a different model than Qwen 2.5 7B if it's not approved.)
- **h.** Microsoft Playwright CDN — mirrored on JFrog, or does `playwright-with-chromium` recipe need to vendor `chrome-headless-shell` into the recipe source / use an alternative Chromium binary?
- **i.** Security-review SLA for newly-authored conda-forge recipes added to the internal mirror — drives delivery timeline for `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai` (and `mem0ai`/`fastembed-vectorstore` if Phase 0 exit 6 adds them). **[REVISED 2026-07-25]** `template-style-extractor` removed from this list — dropped from scope, see Decisions Log Q2.
- **j.** ✅ **Resolved/moot 2026-07-25.** PyMuPDF licensing question no longer applies — `template-style-extractor` is dropped, and upstream Presenton's actual PDF dependency is `pdfplumber` (MIT), confirmed via live code search, never PyMuPDF. See Risk R7 (revised).
- **k. [NEW 2026-07-25]** Memory/RAG subsystem scope — does Phase 0 add `mem0ai` + `fastembed-vectorstore` as two more conda-forge recipes, or feature-drop the memory/chat-history subsystem for v1? Contingent on confirming whether the import graph can be cleanly disabled without a Presenton-side source patch (not yet verified — env-var accessors exist in `utils/get_env.py` but a full no-op path was not traced). This is Phase 0 exit criterion 6 (see below).

## Success Criteria

> **Reader's note (v5, 2026-05-01):** Three phrases in the Executive Summary, Differentiator, and Risk Register R3 reference "Copilot-class capability" / "M365 parity." These framings are superseded by the v5 scope decision (long-form-document summarization into review-ready decks; M365 retained only for procurement-recognition). Final wording lands in step-11 polish; the substance below already reflects the v5 scope.
>
> **Reader's note (v6, 2026-07-25):** See the Revision Log at the top of this document for the full delta trail. In brief: `template-style-extractor` is dropped from v1 (Decisions Log Q2, superseded); Risk R3's trigger is corrected and escalated to a Phase-0-blocking check (new exit criterion 6); Risk R7 is resolved and replaced; `llmai` is re-pinned to `0.2.8`; a new Risk R9 names an OpenShift-Chromium-sandbox interaction spike; recipe count throughout this document is now "five confirmed, plus up to two pending Phase-0 exit 6," not a fixed six.

The two-gate JTBD (buyer/user) drives a two-axis success model: one axis tracks "survives security review" (buyer-gate), the other tracks "long-form-document summarization into review-ready decks" capability (user-gate). Either axis collapsing kills the product. Phase 0 must close before v1 build is unblocked.

### User Success

The analyst (renewal-driving persona) wins when:

- **First-draft latency:** ≤30 min P95 from "deck request" to **first-slide-renderable**. The clock starts at *prompt-submit* and stops when the thumbnail strip is populated and slide 1 is paintable. Editorial judgment time (analyst scrolling through and deciding "I'd rather edit than write from scratch") is explicitly outside the budget.
- **In-flight stall recovery contract:** If no token/slide progress for >45s, the UI surfaces *"Generation paused — [Resume from slide N] [Restart] [Save partial draft]."* A silent 5-minute hang at minute 8 burns the 30-min P95 and the user's trust simultaneously.
- **Per-refinement latency:** ≤10s P95 on Tier-1 LLM. Tier-2 llama.cpp is async/batch UX and is NOT a quality-gated success criterion.
- **Quality anchor:** Output beats *"writing it by hand at 2 a.m."* Sole anchor; no M365 calibration.
- **Capability rubric (buyer-facing, JTBD-anchored):** Covers **12 deck archetypes** validated during Phase 0 by the pilot's compliance team. Initial seed list (refined with pilot during Phase 0):
  1. Quarterly board update / executive summary
  2. Incident postmortem brief
  3. Compliance review / audit response
  4. Research findings / threat-intel briefing
  5. Project status / program review
  6. Risk assessment / risk register summary
  7. Budget proposal / resource ask
  8. Vendor evaluation / make-vs-buy
  9. Architecture review / technical proposal
  10. Training / readiness brief
  11. Stakeholder/customer presentation
  12. Regulatory submission summary
- **First-run calibration (in-product, replaces lost M365 anchor):** *"Pick the archetype closest to your deck; we'll get you to a reviewable draft faster than starting from a blank slide at 2 a.m."* Tied to the 12-archetype rubric. Sets analyst expectation in the moment of first prompt.
- **Velocity signal:** Second deck takes ≤50% wall-clock time of the first.
- **Canonical task shape:** 40-page internal compliance/research/incident document → 12-slide draft.
- **Measurement protocol (air-gap-honest):** All latency and adoption metrics scraped at the customer's own Prometheus `/metrics` endpoint inside the perimeter. Customer self-reports aggregates at customer cadence and discretion. We do not see raw telemetry.

### Business Success

The buyer (CISO/platform/procurement) wins when:

- **Pilot acceptance gate (MVP):** One pilot customer signs the acceptance checklist on Tier-1 LLM configuration. The checklist requires ALL of:
  - `AC-FX-INSTALL-*` + `AC-FX-DAY2-*` green in customer's environment.
  - Pilot generates ≥10 production-shape decks from real internal documents over ≥2 weeks.
  - **AC-PILOT-001 (user-gate behavioral metric):** Pilot users demonstrate **"edit-not-rewrite" behavior on ≥60% of generated decks**, measured by:
    - (a) Edit-distance from generated draft to final deck stays below threshold X (set in Phase 0), OR
    - (b) Post-session survey: user-reported "kept the structure, edited content" on ≥60% of sessions.
    Without this, the checklist can pass on task-completion-time while users silently rewrite from scratch — which kills renewal regardless of acceptance signature.
  - **Three-signatory signoff with backup-signatory clause:**
    - **CISO or platform-owner** (deployment + security gate).
    - **Named end-user lead** (user-gate signatory) attesting in writing that ≥3 of the 10 decks were used in actual customer/board/regulatory deliverables — not internal demos.
    - **At deployment go-live, each signatory designates a backup.** If signatory turnover happens during the 12-week window, backup has 30-day signoff window AND ONE 6-week extension is available before triggering Phase 0 reset. Caps personnel-risk impact at 18 weeks total.
  - **Backup-signatory continuity kit:**
    - Backup auto-receives **read-access to running deck-quality corpus** (the 10 production-shape decks as they accrue).
    - Weekly 5-minute "what changed" digest: prompts authored, ledger entries opened/closed, brand-token version deltas.
    - **30-day signoff clock starts on *handoff-acknowledged*, NOT on promotion-effective.** Backup inherits a pre-warmed dossier, not a cold ledger.
- **Pilot acceptance failure branch:** If no acceptance achieved within 12 weeks of pilot deployment go-live (or 18 weeks if extension invoked under backup-signatory clause), the program returns to Phase 0 scoping rather than advancing to Phase 1.
  - **Phase 0 reset mechanics:** Default re-opens **exit 1** (build-complete-hold) if pilot's GRC model-source policy differs from initial assumption; **carry-forward exits** (sunk-cost-correct): exits 3 (fixture-capture v1) and 4 (JFrog allowlist gap analysis) remain valid unless explicitly invalidated by the new pilot's environment. **Re-entry criterion:** new pilot identified + Phase 0 re-scope timeline filed before Phase 1 work resumes.
- **Second-pilot validation milestone (between MVP and Growth):** 2 pilots accepted under the full checklist, where pilot #2's parent organization is different from pilot #1's AND uses a different Tier-1 endpoint shape (e.g., #1 Gemini-on-prem, #2 Azure OpenAI disconnected or Claude on-prem). If pilot #2 not in production within 12 months of pilot #1's acceptance signoff, formally re-evaluate the procurement-driven adoption thesis (strategic-review milestone).
- **Operational watch (yearly + gate-coupled + always-on RSS):**
  - **Yearly cadence:** annual review of Microsoft Arc-connected/IL5/disconnected Copilot announcements; alert thresholds defined in Phase 0; auto-trigger Redmond-contingency review if any announcement crosses an alert threshold. **[REVISED 2026-07-25]** This cadence appears to have missed the 2026-02-24 Azure Local disconnected operations / Microsoft 365 Local / Foundry Local GA announcement — channel coverage audit is part of Phase 0 exit criterion 6, not deferred to the next yearly review.
  - **At every exit-criteria gate event** (Phase 0 close, pilot #1 acceptance signoff, pilot #2 acceptance signoff, Pilot → GA reviews): auto-trigger Redmond-contingency review BEFORE signoff on any gate.
  - **Always-on lightweight trigger:** RSS/Atom subscription to Microsoft 365 roadmap + Copilot blog with keyword filter (`on-prem`, `sovereign`, `air-gap`, `disconnected`, `GCC-High` paired with `Copilot`). Hit → escalate to gate review out-of-cycle, regardless of yearly cadence. Closes the multi-month blindside window between gate events.
  - **Analyst-facing UX during gate review:** non-blocking editor banner *"Platform review in progress — your work is unaffected; signoff packet will note status."* Surfaces the operator concern at signoff time without blindsiding the analyst.
- **Adoption ramp (Growth):** 100 pilot customers via procurement pipeline (procurement-driven, not sales-driven).
- **Procurement gate (binary chain visible):** All confirmed recipes (five, plus up to two more pending Phase-0 exit 6 — revised 2026-07-25) upstream-merged on conda-forge → matching feedstocks producing artifacts → artifacts landed on customer's JFrog Artifactory mirror → OCI image landed on customer's image registry. Each link separately-trackable.
- **Procurement SLA (measured-against, not owned):** Security-review cycle completion time, set by JFrog allowlist + customer GRC.
- **Provenance simplification:** One signed OCI artifact + one SBOM + one cosign attestation replaces five-to-seven unsigned upstream Python/Node packages (revised 2026-07-25, was six).
- **Window of opportunity [REVISED 2026-07-25]:** Capture pilot adoption before Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, already GA 2026-02-24) ships Copilot-equivalent deck generation on top of it — status unconfirmed, Phase-0-blocking (exit criterion 6). The old "12-24mo to IL5 GA" framing is retired; IL5 GA already happened without ending this window, because IL5 is cloud, not air-gapped.

### Technical Success

- **Recipe quality (all confirmed recipes — five, plus up to two more pending Phase-0 exit 6; revised 2026-07-25, was "all six"):** Lint-clean (`conda-smithy` + `rattler-build lint`), deterministic builds, rerender-survivable across one full conda-forge global pinning bump.
- **Fixture acceptance (FIVE sets pass):**
  - `AC-FX-AUTHOR-01/02`: byte/structurally equivalent + SSIM ≥ 0.99.
  - `AC-FX-MAINT-01..03`: weekly drift detection runs, breaking-vs-benign categorization, auto-issues on breaking drift.
  - `AC-FX-DAY2-01..03`: 60s smoke-deck budget; cred rotation without app restart; mark-broken response on pinned deps.
  - `AC-FX-INSTALL-*`: day-0 preflight green.
  - `AC-FX-DRIFT-01..04` (drift-harness self-tests):
    - `AC-FX-DRIFT-01`: classifier categorizes 4 synthetic-release fixtures correctly (benign patch / breaking dep / breaking API / no-op rerelease).
    - **`AC-FX-DRIFT-02a` (CI-gated, deterministic):** Pattern-match against benign-drift allowlist. Categories that pass without firing an issue:
      - `*.md` and `CHANGELOG*` files (any change)
      - `*.css` class-rename-only diffs (AST-compare via PostCSS; no JSX/TSX behavior change in matched component tree)
      - `package.json` version bumps within semver-minor
      Files: `tests/drift/benign_filter.py` + `tests/drift/benign_allowlist.yaml`.
    - **`AC-FX-DRIFT-02b` (human-gated, 48hr SLA):** Fixture-only changes + ambiguous CSS/JSX edits route to maintainer review queue. Files: `tests/drift/review_queue/` + GitHub issue template `human-review-required.md`. Drift harness fires P1 issue on queue depth >5 OR oldest-item age >72hr.
    - `AC-FX-DRIFT-03`: drift-harness step failure exits 0 from cron job; emits `::warning::` annotation.
    - `AC-FX-DRIFT-04`: `.github/workflows/drift-cron.yml` includes `if: github.event_name == 'schedule'` guard + `continue-on-error: true`.
- **Internal proxy benchmark (split into gating + informational):**
  - **`AC-PROXY-001a` (CI-gating, with full hardware-class spec):**
    - **CI-side:** CI pinned to `ubuntu-22.04`, declares `hwclass-ci-x86_64-generic`. Determinism check (fixed seed + temp=0 + fixed prompt → byte-equal output) runs within this class only. Documented in `tests/proxy/determinism/HARDWARE_CLASS.md`.
    - **Customer-side boundary contract:** When customer hardware class falls outside CI matrix, recipe behavior is **fail-closed by default** — refuses to load with clear *"unverified hardware class: <detected> not in [hwclass-ci-x86_64-generic, ...]"* error. Opt-in to **degraded-determinism mode** via `PRESENTON_HW_CLASS_OVERRIDE=accept-degraded` env var; this loads with logged warning + degraded-determinism flag in output manifest.
    - **Production-deployment declaration:** Each pilot's `pilot-acceptance-checklist.yaml` includes `hardware_class: <id>`. CI matrix grows as pilots register classes.
    File: `tests/proxy/determinism/`.
  - **`AC-PROXY-001b` (informational, non-gating):** ROUGE-L/BLEU drift report posted as PR comment; threshold-alert at >0.05 deviation from rolling 30-day baseline. File: `tests/proxy/quality-drift/`.
- **Supply-chain provenance (MVP gates — all required):**
  - **SBOM** emitted in CycloneDX (primary) + SPDX (exportable secondary), regenerated per build, attached to OCI image.
  - **Signed-image attestation** via cosign / sigstore-equivalent.
  - **`/metrics` schema artifact** — versioned schema doc shipped with the Helm chart, locking metric names, label keys, histogram buckets, cardinality bounds. First-class deliverable, not a capability claim.
- **CVE-response capability:** Rebuild-and-resign within 14 days P95, *conditional on JFrog allowlist SLA ≤48h AND maintainer staffing tier*.
- **Drift-detection harness:** Weekly cron CI workflow runs against latest upstream Presenton; files `.github/ISSUE_TEMPLATE/upstream-drift.md` on breaking drift; never breaks the build (verified by `AC-FX-DRIFT-03/04`).
- **Hard constraints (no regression):** Zero LibreOffice in runtime, zero non-conda-forge packages, zero non-pixi build steps, zero external CDN access at build or runtime.

### Measurable Outcomes

| Metric | Target | Tier | Source / Note |
|---|---|---|---|
| Time-to-first-deck (P95) | ≤30 min, prompt-submit → first-slide-renderable | MVP | Customer-internal Prometheus scrape |
| Per-refinement latency on Tier-1 (P95) | ≤10s | MVP | Customer-internal Prometheus scrape |
| Stall recovery surfaced | >45s no progress → recovery dialog | MVP | UX requirement |
| Deck-archetype coverage (buyer-facing) | 12 of 12 (Phase-0-validated by pilot's compliance team) | MVP | User-gate, JTBD-anchored |
| `AC-PILOT-001` edit-not-rewrite behavior | ≥60% of decks | MVP | User-gate; renewal signal |
| `AC-PROXY-001a` deterministic-output equivalence | byte/diff-clean, fixed seed + temp=0; per-hardware-class | MVP CI gate | Hardware-class-scoped; fail-closed default |
| `AC-PROXY-001b` ROUGE-L/BLEU drift report | informational; PR comment; alert >0.05 deviation | MVP non-gating | Reports, doesn't block |
| Image equivalence SSIM | ≥0.99 | MVP | AC-FX-AUTHOR-02 |
| `AC-FX-DRIFT-01..04` pass | all 4 ACs green; benign-drift filter active (02a CI + 02b human queue) | MVP | 5th fixture set |
| Day-2 smoke-deck budget | ≤60s | MVP | AC-FX-DAY2-01 |
| CVE rebuild-and-resign (P95) | ≤14 days | MVP capability; SLO conditional | Risk R4 / JFrog SLA |
| Recipe-set landed on JFrog mirror (chain) | yes/no across 4 chain links | MVP gate | Buyer-gate |
| Signed-image attestation present | yes/no (binary) | MVP gate | cosign |
| `/metrics` schema artifact shipped | yes/no (versioned) | MVP gate | Helm chart deliverable |
| Pilot #1 acceptance signoff | 3-signatory + backup-clause; ≤12wk (or 18wk with extension) from go-live | MVP | Reset to Phase 0 on miss |
| Microsoft watch cadence | yearly + at every exit-criteria gate + always-on RSS keyword filter | MVP | Replaces ad-hoc R3 monitoring |
| Pilot #2 validation (different org + different Tier-1) | 2 pilots accepted before Growth | MVP→Growth boundary | Strategic re-eval at 12mo |
| Pilot customers in production | 100 | Growth | Procurement-driven |
| Pilot → GA: deck volume × duration × P0 | ≥30 decks/mo × 3mo × 0 P0 | Growth gate (a) | Q7(a) |
| Pilot → GA: drift-clean window | 1 upstream release OR 6mo, whichever first | Growth gate (b) | Q7(b) |
| Pilot → GA: CVE cycle exercised | ≥1 e2e (real OR synthetic drill) meeting 14d P95 | Growth gate (c) | Q7(c) |
| Pilot → GA: procurement commitment OR NULL-case substitute | (i) ≥1 pilot multi-year commitment surviving Microsoft announcement, OR (ii) NULL-case requires substitute (LOI / analyst report / RFP language match) | Growth gate (d) | Engineering baseline alone does NOT satisfy |

**P0 incident definition** (used in Pilot→GA gate (a)):
- (a) Data exfiltrated outside customer perimeter.
- (b) Deck output corrupted/unrecoverable.
- (c) Image deployment unable to start.
- (d) LLM provider integration fails for entire user population for >1 hour.

### Phase 0 Exit Criteria (gates v1 build kickoff)

Phase 0 has a critical-path long-pole (exit 1, "build-complete-hold"). Exits 2 and 3 are gated by exit 1. Exits 4, 5, and 6 run independently. **6 exits total (revised 2026-07-25, was 5 — see exit 6 below).** Exit 6 is the highest-urgency of the independent exits: it resolves whether the product's core differentiator still holds (Risk R3, revised) and materially changes the recipe-count/scope math (Risk R2, revised) — start it first among the independents, don't let it queue behind exits 4-5.

**Phase 0a (critical path — build-complete-hold):**

1. **Build-complete-hold** *(named for CISO clarity — avoids "baseline" which reads as security-baseline. Inline gloss: **build-complete-hold = recipe builds and tests pass; procurement-signal not yet sufficient to justify pilot scoping**.)*
   All of:
   - GGUF model family (Qwen / Llama / Mistral) and quantization tier (Q4_K_M / Q5 / Q6) chosen.
   - Bench methodology documented using public datasets (GovReport, BillSum for long-form summarization; 12-archetype rubric coverage demonstration).
   - **Bench-archetype coverage floor:** Methodology specifies which of the 12 archetypes GovReport+BillSum exercise; **coverage floor ≥8/12 archetypes** must have at least one public-dataset proxy task. **Uncovered archetypes named explicitly as Phase-1 deferred risk** in the bench methodology document — they are not silently absent.
   - Bench fixtures committed.
   - **Source-pathway commitment with alt-source clause:** if customer GRC bans HuggingFace as a model source, alternative paths satisfy this exit:
     - (a) Customer-supplied GGUF from approved internal registry.
     - (b) Pre-vetted internal model registry path.
     - (c) Customer-licensed model converted to GGUF via approved tooling.
   - Specific model+quant LOCK happens at customer-mirror-allowlist resolution time, NOT at Phase 0 close.
   - This is the long-pole; exits 2 and 3 cannot begin until exit 1 closes.

**Phase 0b (gated by exit 1):**

2. **Tier-1 reference LLM class chosen for methodology committal** — Named class against which user-success metrics are evaluated. Customer's actual Tier-1 endpoint may be a different specific endpoint within the class.
3. **Fixture-capture v1 committed** — `tests/fixtures/upstream-baseline/v1/` populated and signed; capture script run against locked upstream Presenton tag; fixture-changelog initialized.

**Phase 0c (independent — exit 4):**

4. **JFrog allowlist gap analysis filed** — Per-dependency gap report (conda + npm + GGUF) covering: which packages already mirrored, which need allowlist requests, which have licensing blockers (e.g., `psycopg` LGPL-3.0-only — Risk R7, revised 2026-07-25), expected security-review SLA per gap.

**Phase 0d (independent — exit 5):**

5. **Capability Claim Statement committed** — single buyer-facing sentence in canonical form:
   > *"Generates [artifact-class] at [public-bench-score] quality, fully on-prem, with [SLA]."*
   Bound to a content-review checkpoint that **explicitly forbids cloud-product comparisons** (no "Copilot-class," no parity numbers, no SaaS-equivalent framing). Required deliverable before Phase 0 close. Without it, every field conversation re-litigates positioning ad-hoc and competitors define us by negation.

**Phase 0e (independent, highest-urgency — exit 6, NEW 2026-07-25):**

6. **Microsoft disconnected-stack verification + memory-subsystem scope decision committed** — two coupled sub-items, both required:
   - **(a) Redmond-contingency check.** Confirm or rule out whether Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24) includes, or has an announced roadmap to include, Copilot-for-PowerPoint-equivalent deck generation. This directly determines Risk R3's status (materialized / partially materialized / infrastructure-only). Also audit the existing RSS/keyword-watch mechanism's channel coverage — it appears to have missed the 2026-02-24 announcement.
   - **(b) Memory-subsystem scope decision.** Decide whether `mem0ai` + `fastembed-vectorstore` (unconditional Presenton dependencies, neither on conda-forge) become two additional v1 recipes, or the memory/chat-history feature is documented as dropped for v1 — contingent on confirming a clean no-op import path if dropped (not yet verified; may require a Presenton-side patch, which changes the maintenance-burden model this PRD doesn't currently carry for any other component).
   Required before Phase 0 close, alongside exits 1-5. Given exit 6(a)'s bearing on whether the product's core differentiator still holds, this exit should be actioned first among the independent exits (4, 5, 6), not queued last because it's numbered last.

## Product Scope

### MVP — Minimum Viable Product

Ships when ALL of the following are simultaneously true:

- All confirmed conda-forge recipes lint-clean and **upstream-merged** (revised 2026-07-25 — was "all six," now five confirmed plus the Phase-0 exit-6 decision): `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai` — plus `mem0ai` and `fastembed-vectorstore` if Phase 0 exit 6(b) decides to add them rather than feature-drop the memory subsystem. `template-style-extractor` is dropped (see Decisions Log Q2, revised) — not part of this gate.
- OCI image builds reproducibly via pixi + pixitainer with zero external CDN access.
- All FIVE fixture sets pass: `AC-FX-INSTALL/DAY2/AUTHOR/MAINT/DRIFT`.
- `AC-PROXY-001a` (deterministic-output equivalence, hardware-class-scoped) passes in CI.
- `AC-PILOT-001` (edit-not-rewrite ≥60%) passes in pilot environment.
- Helm chart / kustomize overlays deploy on OCP and consume any OpenAI-compatible Tier-1 endpoint via env vars.
- SBOM (CycloneDX + SPDX) + signed-image cosign attestation + versioned `/metrics` schema artifact attached to/shipped with image.
- **Pilot #1 acceptance gate cleared:** 3-signatory acceptance checklist (with backup-signatory clause + continuity kit) on Tier-1 LLM. If no acceptance within 12 weeks of go-live (or 18 weeks if extension invoked), program returns to Phase 0 scoping per Phase 0 reset mechanics.
- Phase 0 exit criteria all met (5 exits, phased a→b→c+d).
- Buyer-facing capability rubric: 12 of 12 deck archetypes covered (Phase-0-validated by pilot's compliance team).
- Capability Claim Statement committed and approved through content-review checkpoint.
- **Tier-2 llama.cpp sidecar shipped as architectural capability — not quality-gated.**
- Operational Microsoft-watch active (yearly + gate-coupled + always-on RSS).

> **Tier-2 framing note:** Tier-2 llama.cpp ships as a *deployable option at customer discretion*. We do not claim a quality bar against it; customers selecting Tier-2 own their own quality validation. Removing it would force customers wanting offline operation to fork the recipe — a worse outcome.

### Growth Features (Post-MVP)

Tier flips when ALL of the following are met:

**Pilot → GA conjunction (4 criteria):**
- **(a)** ≥30 decks/mo × 3mo × 0 P0 incidents.
- **(b)** Drift-clean for 1 upstream Presenton release OR 6 calendar months, whichever first.
- **(c)** CVE drill (real OR synthetic) end-to-end meeting 14d P95.
- **(d)** Procurement-commitment OR NULL-case **substitutes** (no longer auto-satisfy):
  - (i) ≥1 pilot has executed multi-year purchase commitment OR budget line-item allocation that survives a Microsoft on-prem-Copilot announcement, OR
  - (ii) **NULL-case substitutes** (when no qualifying Microsoft announcement during window) — require ONE of:
    - (ii-a) Second pilot LOI from independent customer, OR
    - (ii-b) Analyst report (Gartner / Forrester) citing the category, OR
    - (ii-c) RFP language from prospect matching capability description.
  - **Engineering baseline alone does NOT satisfy (d).** Procurement-recognition needs external signal, not internal trajectory.

**Plus second-pilot validation milestone:** 2 pilots accepted under the full checklist, with pilot #2's parent org different from pilot #1's AND a different Tier-1 endpoint shape. Strategic-review milestone if pilot #2 not in production within 12 months of pilot #1's acceptance.

**Growth scope:**

- **Named commercial-grade Tier-1 endpoint shape validated** — internally-hosted Gemini is the reference. Equivalent shapes (Anthropic Claude on-prem, Azure OpenAI disconnected) substitute one-for-one.
- **Brand-compliance enforcement UX bands:**
  - **"Auto-applied (reviewable)"** band: system applies high-confidence corrections without blocking; persistent compliance-ledger chip ("N brand corrections applied — view") in editor chrome until acknowledged or exported with deck. Default is passive disclosure, not silence. Strict-mode opt-in stays.
  - **"Batched-review"** band (mid-confidence): user reviews queued corrections in batch dialog before apply.
  - **"Ignore"** band (low-confidence): no action; surfaced only in strict mode.
- **JetBrains REST one-pager** + Postman collection.
- **Adoption ramp:** 100 pilot customers via procurement pipeline.
- **Compliance posture upgrades (nice-to-have):** FIPS-mode operation; audit log shape + retention period; WCAG AA/AAA on analyst UI.

### Vision (Future)

- `chromium` upstreamed to conda-forge directly (replaces vendored `chrome-headless-shell` in `playwright-with-chromium`); resolves staged-recipes#21431.
- **SVG→DrawingML fidelity tier** — render slides to SVG via Playwright, convert to native PPTX shapes (option-C-equivalent without HTML→shape lossiness). Net-new conda-forge work; no SVG→DrawingML library exists today. Inspired by `hugohe3/ppt-master` architecture.
- **Full JetBrains plugin** — replaces docs-only one-pager.
- **Knowledge-base integration** — decks where source material does NOT fit in prompt + uploaded files. Currently held against customer pressure as a v1 boundary; revisited at Vision tier.
- **Upstream `presenton-export` source acquired** — Presenton team open-sources the export bundle build pipeline; vendored `presenton-export-node` retired in favor of canonical upstream.
