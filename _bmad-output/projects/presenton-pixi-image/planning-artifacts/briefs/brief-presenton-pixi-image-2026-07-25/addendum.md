---
title: Addendum - presenton-pixi-image Product Brief
status: draft
created: 2026-07-25
updated: 2026-07-25
---

# Addendum: presenton-pixi-image

Deeper material that supports `brief.md` but doesn't belong in a 1-2 page executive document. This addendum is an input to the PRD revision, not a replacement for reading the full pre-existing `planning-artifacts/prd.md` (591 lines) or the two research reports under `planning-artifacts/research/`.

## Full persona list (carried forward from the pre-existing PRD, unchanged)

1. Buyer — Platform/security team (CISO + compliance + platform engineering director).
2. OCP operator (day-0) — install/configure/deploy.
3. OCP operator (day-2) — operate/patch/rotate-creds/respond-to-mark-broken.
4. Recipe-maintainer (us) — verifies upstream drift, refreshes fixtures; wears "fixture maintainer" hat during online-capture phases.
5. Analyst (end user, renewal-driving).
6. VS Code developer — sideloads `copilot-bridge`.
7. JetBrains developer — docs-only fallback in v1, explicit packaging gap not silent omission.
8. End web user of upstream Presenton — OUT-OF-SCOPE, upstream owns the UI.
9. Conda-forge staged-recipes reviewer — gatekeeper persona, each new recipe is a review cycle with veto power.

## Technical constraints surfaced by research (detail beyond the brief's scope section)

**Recipe-count math is now genuinely open, not "six."** Confirmed-necessary: 5 (`presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai`). Removed: 1 (`template-style-extractor`). Pending Phase-0 decision: 0 or +2 (`mem0ai`, `fastembed-vectorstore`). Range: **5 to 7** recipes for v1, not a fixed six. The PRD's "six conda-forge recipes" framing throughout (executive summary, v1 deliverables, success criteria's "all six recipes... upstream-merged," MVP gate) needs a global find-and-fix during the PRD revision — every "six" needs to become either a specific number pending the Phase-0 decision, or explicitly conditional language.

**Full conda-forge-availability table for Presenton's current dependency closure** (see technical research report §1.8 for the complete table with versions/licenses): `fastmcp`, `dirtyjson`, `sqlmodel`, `asyncpg`, `aiomysql`, `psycopg` (LGPL-3.0 flag), `google-genai`, `pathvalidate`, `pdfplumber`, `python-pptx`, `fastembed` (distinct from `fastembed-vectorstore`), `nltk`, `fonttools` — all confirmed present on conda-forge, compatible licenses (modulo the `psycopg` LGPL flag). This closure was never enumerated in the original PRD/Dream — the original `externalResearchTargets` list focused narrowly on the export/PPTX/template pipeline and missed the full backend dependency graph (DB layer, memory/embeddings, MCP). The architecture phase should treat this as the actual starting dependency inventory, not the narrower list in the Dream's frontmatter.

**OpenShift Restricted SCC — specifics for the architecture phase:**
- `restricted-v2` (current default for authenticated users): all Linux capabilities dropped, only `NET_BIND_SERVICE` addable on request, `seccompProfile: runtime/default`, `allowPrivilegeEscalation` must be false/unset, pre-allocated non-root UID range, pre-allocated FSGroup, no host-directory volumes, no privileged containers.
- `restricted-v3` (default for *new* OCP installations): adds `userNamespaceLevel: RequirePodLevel` — pods run inside a Linux user namespace (`hostUsers: false`).
- **Open architectural question, not yet spiked:** headless Chromium's own sandbox model (typically requiring `CAP_SYS_ADMIN` or working nested user namespaces; conventional container workaround is `--no-sandbox`) interacting with `restricted-v3`'s pod-level user-namespace isolation. Three plausible outcomes: (a) OCP's isolation makes Chromium's internal sandbox redundant-but-harmless, (b) nested user-namespace creation is blocked and Chromium needs `--no-sandbox` regardless (the safe default assumption), (c) something breaks in a way that needs a different SCC (e.g. `nonroot-v2`) — none confirmed without a hands-on cluster spike. This must be a named Phase-0/architecture-phase action item with an explicit owner, not left implicit.
- Read-only root filesystem is *not* mandated by Restricted SCC by default (it's one of the SCC's configurable knobs, not a hard restriction) — architecture should support it as opt-in hardening (writable `/tmp`, `/app_data` via `emptyDir`/PVC) rather than assume either posture.

**`presenton-export` release cadence is faster than "weekly cron" assumes.** Three tags in six days observed during this research window (`v0.4.0` → `v0.4.1` → `v0.4.2`, 2026-07-13 to 2026-07-19). The existing Fixture Set 2 (`tests/drift/`) design already specifies weekly cron — worth revisiting whether that cadence catches breaking changes fast enough given observed upstream velocity, though this is a tuning question, not a design-flaw.

## Risk register carryforward (from pre-existing PRD, R1/R2/R4-R8 unchanged; R3 and R7 updated)

- **R1** (pptx-thumbnail-inject spike needed) — unchanged, not investigated in this research pass.
- **R2** (upstream drift, six-plus clean-room artifacts) — unchanged in kind; recipe count uncertainty (5-7) slightly changes the "six" framing but not the mitigation (drift harness).
- **R3** (Microsoft on-prem Copilot threat) — **substantially revised**, see brief.md's "What Makes This Different" closing paragraph and Success Criteria. Old mitigation (quarterly scan) is superseded by: (a) correct the trigger condition, (b) escalate the Copilot-deck-generation-inclusion question to a Phase-0 blocking item, (c) audit the existing RSS/keyword-watch mechanism's channel coverage since it appears to have missed the 2026-02-24 announcement.
- **R4** (JFrog SLA blocks recipe submission) — unchanged; now applies to a 5-7 recipe count instead of a fixed 6.
- **R5** (Playwright CDN not mirrored) — unchanged; technical research found current upstream Presenton uses pinned-Debian-package Chromium (not Playwright-managed download) via Puppeteer, which if anything validates the "vendor a pinned build into the recipe" strategy already proposed as the fallback.
- **R6** (fixture-capture phase boundary) — unchanged.
- **R7** (PyMuPDF AGPL licensing) — **resolved/moot.** Technical research confirmed upstream Presenton's actual PDF-parsing dependency is `pdfplumber` (MIT), not PyMuPDF; the `template-style-extractor` component that would have needed PyMuPDF is being dropped from scope entirely (see brief.md Scope section). Replace R7 in the revised PRD with the new, smaller finding: `psycopg` is LGPL-3.0-only, distinct obligation class from the rest of the Apache/MIT-dominated stack — flag for buyer legal review, likely-but-not-confirmed acceptable.
- **R8** (JetBrains gap) — unchanged.

## Rejected-alternative rationale (unchanged from pre-existing PRD, not relitigated)

The pre-existing PRD's `## Discovery & Re-Architecture` section already documents a substantial rejected-alternative history (the original `pptx2marp-bridge-marp2pptx` vendoring approach, killed by two adversarial-review dealbreakers — A1 lossy PPTX↔Marp round-trip, C2 missing thumbnail support). This history is sound and carries forward unchanged; this research pass found no reason to revisit it. New rejected-alternative context added by this research: rebuilding template-style-extractor from scratch is now also a rejected alternative, on different grounds (duplicates upstream's already-shipped, already-simpler solution) — see brief.md Scope section.

## Options considered — recipe-count decision for the memory subsystem (Phase-0 input, not yet decided)

- **Option A — add `mem0ai` + `fastembed-vectorstore` as recipes 6 and 7.** Keeps full upstream feature parity (chat memory, presentation memory). Cost: two more conda-forge review cycles, two more JFrog-allowlist requests, two more entries in the drift-detection surface.
- **Option B — feature-drop the memory subsystem for v1.** Requires confirming (not yet done) that the import graph can be cleanly no-op'd without a Presenton-side source patch — technical research found env-var accessors exist but did not trace a confirmed no-op path. If a source patch is required, this stops being a "drop a feature" decision and becomes "carry a Presenton fork/patch," which has its own maintenance-burden implications the PRD doesn't currently model for any other component.
- No recommendation is made here; this is explicitly a Phase-0 exit-criterion-shaped decision, structurally identical to the existing Phase-0 exits 1-5 already in the PRD (GGUF model pick, fixture-capture v1, JFrog gap analysis, Capability Claim Statement). The PRD revision should likely add this as **Phase 0 exit 6**.

## Domain research: OCP adoption evidence detail

Aggregator-sourced (not primary Red Hat data — direct fetches of `redhat.com` government-focused pages 404'd during research): 6,633 verified companies using Red Hat OpenShift (2026, Landbase); managed-OpenShift-services market ~$4.29B (2026) → ~$10.99B (2030) at 26.5% CAGR (Research and Markets); FedRAMP-authorization and DoD-IL-workload support corroborated by a federal Kubernetes-engineering vendor's service listing (Precision Federal) naming OpenShift alongside AWS GovCloud/Azure Government offerings. Treat as directional context supporting the OCP-first platform decision, not citable precise figures for buyer-facing material.
