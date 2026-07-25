---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-warden.md
  - docs/dreams/pyforge-charter.md
  - docs/specs/pyforge-warden.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
research_type: 'market'
research_topic: 'Dependency-compliance / Software Composition Analysis (SCA) landscape — Snyk, GitHub Dependabot, Renovate, OSV-Scanner, Trivy/Grype, pip-audit, deptry, FOSSA/ScanCode — as comparables for pyforge-warden'
research_goals: 'Place Warden against its nearest analogues to verify — RETROSPECTIVELY, against the already-SHIPPED v1 (31/31 stories, PR #110, schema 1.1.0) — that its stated differentiators (never-false-green `indeterminate` state, conda+PyPI dual-ecosystem source-manifest bridge, the frozen exit-code contract, waivers-as-code, fleet scale) are real gaps in the comparable set, not assumed ones.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'RETROSPECTIVE scope. Warden shipped its full v1 (31/31 stories, Epics 1-6, PR #110 merged 2026-07-25) before the factory adopted the research-first convention — this report backfills the missing evidence, verifying the PRD''s own 2026-07-11 competitive claims against fresh 2026-07-25 primary-source checks rather than repeating them unverified.'
methodology_note: 'The session WebSearch budget was exhausted (200/200) before this report began. Per the task''s explicit fallback instruction, every comparable below is grounded in `gh api`/`gh repo view` repository telemetry (stars, license, last release, last push — captured 2026-07-25) plus WebFetch against each tool''s own documentation where the page resolved. Two WebFetch attempts (Snyk''s `.snyk` ignore-policy doc, GitHub''s Dependabot alert-dismissal doc) hit moved/404''d pages and could not be independently re-verified this session — those specific claims are flagged inline as established industry knowledge, not freshly re-confirmed, rather than silently asserted as verified. Three claims WERE freshly and directly confirmed via live fetch: OSV-Scanner''s supported-lockfile list does not include any conda/pixi format; Renovate''s `ignoreDeps`/`packageRules` have no expiry mechanism; `deptry`''s canonical GitHub org has transferred from `fpgmaas` to `osprey-oss`.'
---

# Research Report: Market Research — Dependency-Compliance / SCA Landscape

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Market (retrospective — verifying a shipped v1's competitive claims)

---

## Research Overview

pyforge-warden (Warden) shipped its complete v1 on 2026-07-25 (PR #110, "complete (31/31) — Epics 5 & 6, all axes + fleet-readiness"): a CI/CD dependency-compliance gate unifying `deptry` (hygiene) and Google's `osv-scanner` (security, KEV+EPSS-enriched) with license and currency axes, all flag-activated gates, over one schema-validated `ComplianceReport` (schema 1.1.0) behind one frozen exit-code contract. Warden's own PRD (2026-07-11) already made specific competitive claims about the tooling it sits beside — this report is not the pre-build research that should have preceded those claims; it is the **backfilled, retrospective verification** that they held up. Eight comparables were checked: **Snyk**, **GitHub Dependabot**, **Renovate**, **OSV-Scanner**, **Trivy**, **Grype**, **pip-audit**, **deptry**, and **FOSSA/ScanCode Toolkit** (license-scanning comparables).

---

## Competitive Landscape

### 1. OSV-Scanner (Google) — the vulnerability engine Warden orchestrates, and the direct confirmation of Warden's core wedge

`gh repo view google/osv-scanner`: 10,690 stars, Apache-2.0, latest release **v2.4.0** (2026-06-18), pushed 2026-07-25 (today). **Directly confirmed via live fetch of its own supported-lockfiles documentation**: OSV-Scanner's Python coverage is `Pipfile.lock`, `poetry.lock`, `requirements.txt`, `pdm.lock`, `pylock.toml`, `uv.lock` — **no conda `environment.yml`, no `meta.yaml`/`recipe.yaml`, no `pixi.toml`/`pixi.lock`**. This is not a stale claim carried over from Warden's 2026-07-11 PRD — it is freshly reconfirmed against the v2.4.0-era documentation, 6 weeks after that release: **the gap Warden's E1 bridge exists to close has not been closed upstream.** Warden does not compete with OSV-Scanner; it wraps it and extends its reach.

### 2. deptry — the hygiene engine Warden orchestrates, and a genuine currency finding

`gh repo view fpgmaas/deptry` resolves (via GitHub's own redirect) to **`osprey-oss/deptry`** — confirming the project has undergone an **organizational transfer** since Warden's architecture.md pinned its engine contracts against `fpgmaas/deptry` (2026-07-11/16). The transferred repo is not archived, MIT-licensed, latest release **v0.25.1** (2026-03-18), pushed 2026-07-25 (today) — actively maintained under its new home. **This is a genuine "dates the shipped design" finding**: Warden's architecture doc and its pinned-engine-contracts frontmatter still cite `fpgmaas/deptry` as the canonical source; the org is now `osprey-oss`. This does not affect Warden's behavior (same tool, same CLI, same JSON output contract — deptry's `--json-output` shape is unchanged at v0.25.1, the version Warden's own architecture doc already pins against), but the citation is stale and should be corrected in a future doc pass, not treated as urgent.

### 3. Trivy & Grype — installed-environment scanners, confirming the "source vs. installed" distinction is real

`aquasecurity/trivy`: 37,080 stars, Apache-2.0, v0.72.0 (2026-06-30), pushed today. `anchore/grype`: 12,638 stars, Apache-2.0, v0.116.0 (2026-07-16), pushed 2026-07-24. Both remain the dominant container/filesystem SCA tools and both, per their own stated scope (container images, filesystems, SBOMs of *installed* environments), operate on a resolved/installed environment — never a pre-build source recipe. This confirms Warden's PRD framing verbatim: "incumbents like Trivy/Syft do scan an already-installed conda environment via `conda-meta/`; what nobody serves is pre-build source-manifest scanning." Nothing found in this pass contradicts that — both tools remain actively developed at genuinely high adoption (37k/12.6k stars) without adding conda/pixi *source*-manifest parsing.

### 4. pip-audit — the PyPI-native comparable, confirming Warden's "delegate, don't reinvent" design

`gh repo view pypa/pip-audit`: 1,340 stars, Apache-2.0, v2.10.1 (2026-06-10), pushed today. A PyPA-maintained tool, PyPI-only by design (no conda-forge awareness at all) — confirms the PRD's framing that the PyPI side of the ecosystem is already well-served (Warden's PyPI path is pure delegation to deptry/osv-scanner's native parsers, adding no bespoke logic there) while the conda/pixi side genuinely has zero incumbents doing source-manifest hygiene+vuln scanning.

### 5. FOSSA CLI & ScanCode Toolkit — the license-axis comparables

`gh repo view fossas/fossa-cli`: 1,511 stars, v3.17.14 (2026-07-23), pushed 2026-07-24 — actively developed, "language-agnostic... 20+ build systems," but FOSSA's core product is commercial SaaS; the CLI is the OSS front-end to a paid backend. `aboutcode-org/scancode-toolkit` (formerly `nexB/scancode-toolkit`): 2,588 stars, v32.5.0 (2026-01-15), pushed 2026-07-09 — a genuinely deep, free/OSS license-and-copyright *source*-scanner, but its method is scanning actual source-file headers/copyrights, not the `about:license` metadata + `importlib.metadata` PEP 639/trove-classifier approach Warden's FR32 uses. Warden's license axis is intentionally lighter-weight than ScanCode's full-text scan (a metadata read, not a source scan) — this is a scope/depth tradeoff, not a superiority claim, and is worth stating honestly rather than implying Warden's license axis subsumes ScanCode's capability.

### 6. Renovate — confirms a genuine, freshly-verified differentiator: no expiring-waiver mechanism

`gh repo view renovatebot/renovate`: 22,098 stars, latest release **43.280.5**, pushed minutes before this report ran (2026-07-25T19:02) — an extremely active, widely-adopted dependency-update bot. **Freshly confirmed via direct fetch of Renovate's own configuration-options documentation**: `ignoreDeps` and `packageRules` are **static, permanent-until-manually-removed** exclusions — no expiry field, no automatic re-block, no built-in audit-expiry mechanism was found in the documentation reviewed. This is a real, citable point of difference from Warden's **FR24 auditable expiring waiver** (`.warden-waivers.yaml`, default 14-day expiry, `authorized_by` field, automatic re-block on expiry) — Renovate's own docs implicitly concede the gap by suggesting users "consider implementing external processes to periodically audit and rotate" ignore configurations, which is precisely the manual-process risk Warden's FR24 is designed to eliminate.

### 7. GitHub Dependabot — a partial, not-fully-re-verified comparable

`gh repo view dependabot/dependabot-core`: 5,693 stars, pushed 2026-07-25 (today) — actively maintained. A direct fetch of GitHub's Dependabot security-updates configuration doc found the `dependabot.yml` `ignore:` block governs *version-update* suppression, not *security-alert* dismissal, and could not confirm or deny an expiry mechanism on alert dismissal from the page fetched (it 404'd/redirected past the relevant detail). **This claim is therefore held at lower confidence than the Renovate finding above** — established industry knowledge is that a dismissed Dependabot alert stays dismissed until a human reopens it (no auto-expiry), consistent with Renovate's pattern, but this specific report could not freshly re-verify it via primary-source fetch this session. Flagged rather than silently asserted.

### 8. Snyk — could not be independently re-verified this session

`gh repo view snyk/cli`: 5,625 stars, latest release v1.1306.1 (2026-07-16), pushed 2026-07-25 (today) — confirms Snyk's CLI remains actively developed. However, two WebFetch attempts at Snyk's own `.snyk` ignore-policy documentation both hit moved/404'd URLs and could not retrieve the actual field list (whether `.snyk` supports an `expires` date on an ignored issue). **This is flagged honestly as unverified this session** rather than repeating the commonly-known claim (that `.snyk` policy files do support an expiry field) as freshly confirmed fact — if this matters for a future decision, it should be re-checked directly against `docs.snyk.io`'s current sitemap.

---

## Market Differentiation — Where Warden's Claimed Gaps Hold Up

| Warden claim (PRD, 2026-07-11) | 2026-07-25 retrospective check | Verdict |
|---|---|---|
| Neither deptry nor osv-scanner parses conda/pixi source manifests | OSV-Scanner's live Python lockfile list confirmed to exclude every conda/pixi format | **Holds — freshly reconfirmed** |
| Incumbents (Trivy/Grype/Syft) scan installed environments, never pre-build source recipes | Both Trivy and Grype remain scoped to containers/filesystems/installed envs; no source-manifest parsing found in either's current release notes | **Holds** |
| No incumbent brings dependency-hygiene to conda at all | pip-audit is PyPI-only; deptry (Warden's own hygiene engine) has no native conda support until Warden's E1 bridge; nothing else surveyed does hygiene-for-conda | **Holds** |
| Auditable, expiring waivers are a differentiator vs. ignore-forever patterns | Renovate's `ignoreDeps`/`packageRules` freshly confirmed to have no expiry; Dependabot's dismissal-expiry could not be confirmed either way (lower confidence); Snyk's could not be checked this session | **Holds against Renovate (high confidence); plausible but unverified against Dependabot/Snyk** |
| One frozen exit-code contract `{0,1,2,130}` vs. a per-tool patchwork | Every comparable surveyed (osv-scanner's own multiplexed 127/128 codes, deptry's non-zero-on-any-finding, Trivy/Grype's own exit conventions) has a *different*, tool-specific exit scheme — Warden's own architecture doc names reconciling exactly this patchwork (the osv-scanner 127/128 reconciliation, Story 1.4) as load-bearing work it had to do | **Holds — and Warden's own build log is itself evidence of the patchwork's realness** |
| Conda+PyPI dual-ecosystem, one report | No comparable surveyed unifies both ecosystems in one schema-validated report; each is single-ecosystem (PyPI-only: pip-audit; container/filesystem-only: Trivy/Grype; conda-absent: all of them) | **Holds** |

### Where Warden does NOT claim superiority (honest scope boundaries)

- **ScanCode Toolkit's license-scanning depth** (full source-text + copyright scanning) exceeds Warden's metadata-only license axis (FR32) — Warden is intentionally lighter-weight here, trading depth for speed and zero source-execution risk (NFR-S1), not claiming parity.
- **FOSSA's 20+-build-system breadth** and **Snyk's enterprise triage/remediation tooling** both represent mature, funded commercial products with feature surfaces (dashboards, org-wide policy management, IDE integrations) well beyond Warden's non-interactive CLI scope — Warden is not attempting to be a Snyk/FOSSA replacement, only a conda/pixi-native gate for the specific hygiene+vuln+license+currency axes it ships.

---

## Strategic Synthesis

1. **Warden's core wedge (conda/pixi source-manifest bridge) is not just real but *unclosed* six weeks after the PRD's original claim** — OSV-Scanner's v2.4.0-era docs still list zero conda/pixi formats. This is the single most load-bearing finding in this report: the gap the entire E1 bridge was built to close has not been narrowed by upstream tooling in the interim.
2. **The expiring-waiver differentiator is strongest against Renovate** (freshly, directly confirmed) and should be stated with that specific comparable rather than a blanket "no other tool has expiring waivers" claim, which this report could not fully verify against Snyk.
3. **The `fpgmaas/deptry` → `osprey-oss/deptry` transfer** is a small, low-urgency doc-currency fix, not a functional risk — worth a follow-up correction in `architecture.md`'s pinned-engine-contracts frontmatter, but the pinned version (0.25.1) and JSON contract are unchanged.
4. **Warden should not overclaim against ScanCode/FOSSA/Snyk's deeper feature surfaces** — the honest differentiation is ecosystem coverage (conda+PyPI, source-manifest-first) and the never-false-green contract, not feature-for-feature parity with funded commercial SCA suites.

## Open Questions Carried Forward

- Does Snyk's `.snyk` policy file actually support an expiry field? (Could not verify this session — worth a direct, fresh doc check before citing it competitively in any external-facing material.)
- Does a dismissed GitHub Dependabot alert ever auto-reopen, or is dismissal permanent until a human acts? (Same caveat — flagged, not resolved.)
- Should Warden's docs correct the `fpgmaas/deptry` → `osprey-oss/deptry` citation in `architecture.md`'s frontmatter? (Low-urgency housekeeping, not a behavior change.)

## Sources

- `gh repo view google/osv-scanner` (2026-07-25); [OSV-Scanner supported languages and lockfiles](https://google.github.io/osv-scanner/supported-languages-and-lockfiles/) (fetched 2026-07-25)
- `gh api repos/fpgmaas/deptry` + `gh api repos/osprey-oss/deptry` (2026-07-25) — confirms the org transfer
- `gh repo view aquasecurity/trivy`, `gh repo view anchore/grype` (2026-07-25)
- `gh repo view pypa/pip-audit` (2026-07-25)
- `gh repo view fossas/fossa-cli`, `gh repo view nexB/scancode-toolkit` (resolves to `aboutcode-org/scancode-toolkit`) (2026-07-25)
- `gh repo view renovatebot/renovate` (2026-07-25); [Renovate configuration options](https://docs.renovatebot.com/configuration-options/) (fetched 2026-07-25)
- `gh repo view dependabot/dependabot-core` (2026-07-25); [Configuring Dependabot security updates](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/configuring-dependabot-security-updates) (fetched 2026-07-25, partial/inconclusive on alert-dismissal expiry)
- `gh repo view snyk/cli` (2026-07-25); Snyk's `.snyk` ignore-policy documentation could not be located this session (two 404'd URLs) — flagged as unverified
- `gh repo view CycloneDX/specification` (2026-07-25) — confirms CycloneDX 1.7.1 shipped, consistent with Warden's FR27 SBOM axis
- Internal: `docs/specs/pyforge-warden.md` (legacy Tier-1 spec, FR1-FR40), `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` (pinned-engine-contracts frontmatter, the claims being re-verified), `.../epics.md` — Warden's own shipped design, read for comparison, not as external evidence
