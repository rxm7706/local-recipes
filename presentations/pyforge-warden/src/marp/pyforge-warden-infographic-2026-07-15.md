---
marp: true
paginate: true
size: 16:9
title: Warden — Infographic
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:24px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.part { background:#201e1d; color:#f3f2f2; }
  section.part h1, section.part h2, section.part strong { color:#f3f2f2; }
  hr { border:none; border-top:3px solid #201e1d; margin:.3em 0; }
  table { font-size:.64em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:5px 9px; }
  ul { font-size:.86em; }
---

<!-- _class: lead -->

BMAD-METHOD Tech Spec · Full agentic AI-SDLC · Status: in progress, planning complete

# Warden

`pyforge-warden`

One CLI that guards both Python ecosystems — the **PyPI** world of applications and libraries, and the **conda / conda-forge** world of scientific computing, analytics and ML/AI data platforms. Warden runs pluggable engines across **six axes** — hygiene, security, license, currency, provenance and maintenance — and returns **one consolidated report**.

SCA · not SAST · CI/CD quality gate · family naming `<language>-<hygiene-engines>-<security-engines>`

---

## At a glance

| Owner | Language | CLI | Scope | Ecosystem |
| --- | --- | --- | --- | --- |
| rxm7706 | Python 3.12+ | argparse · stdlib | 5 epics · 20 stories | PyPI + conda-forge |

### Why Warden — one gate, both ecosystems, six axes of dependency trust

**01** Hygiene · **02** Security · **03** License · **04** Currency · **05** Provenance · **06** Maintenance

---

<!-- _class: part -->

## PART I — The tool

Shipping in v1

---

## 01 · The problem

Dependency hygiene and security compliance across enterprise infrastructure require **disjointed tools**. Teams run **deptry** and **osv-scanner** as separate pipelines — friction that grows in Conda- and Pixi-heavy environments where **neither engine natively understands those manifests**.

- **2** disconnected pipelines developers maintain by hand
- **0** native conda/pixi support in either engine (as of 2026-07)

---

## 02 · Two ecosystems, one gate

Python isn't one ecosystem. Warden is built for both — and treats the scanning engines as **pluggable**, not fixed.

**Ecosystem 1 · PyPI — Application Python** — ~850K packages, open upload, any license. 20% of footprint: ~400 shipped apps ≈ 2–3K libraries. Manifests (`pyproject.toml`, `requirements.txt`, lockfiles) read **natively**.

**Ecosystem 2 · conda-forge — Scientific & Data Python** — ~30K feedstocks, curated FOSS-only. 80% of footprint: ~10 platforms ≈ 7–8K libraries. Manifests (`environment.yml`, `meta.yaml`, `recipe.yaml`, `pixi.toml`) — which **no engine parses**; Warden's manifest engine bridges them.

---

## 02 · The six axes

| Axis | Engine | Question | Maturity |
| --- | --- | --- | --- |
| 1 · Hygiene | `deptry` | Is it actually used? | v1 |
| 2 · Security | `osv-scanner` | Any known CVE? | v1 |
| 3 · License | `license-expression` | Legally allowed? | v1.x |
| 4 · Currency | `endoflife.date` | Supported / patchable? | v1.x |
| 5 · Provenance | `Sigstore / SLSA` | Authentic & untampered? | vision |
| 6 · Maintenance | `OpenSSF Scorecard` | Alive, funded, resilient? | vision |

Engines are pluggable. **v1 ships hygiene + security**; **license & currency** complete the v1.x gate; **provenance & maintenance** extend it.

---

## 03 · Six manifest formats — resolved natively

The manifest engine is the wedge: neither scanning engine parses conda/pixi manifests. No untrusted input is ever executed — `yaml.safe_load` only.

| Manifest | Notes | Parser |
| --- | --- | --- |
| `pyproject.toml` | PEP 621 · Poetry · PDM | tomllib |
| `pixi.toml` | deps · pypi-deps · features | tomllib |
| `requirements.txt` | one requirement per line | re / line-parse |
| `environment.yml` | dependencies: + nested pip: | safe_load |
| `meta.yaml` v0 | Jinja + `# [selector]` lines | neutralize → safe_load |
| `recipe.yaml` v1 | requirements: run: block | safe_load |

---

## 04 · One invocation, one pipeline

1. **Discovery** — union coverage; every manifest found is scanned and reported per-manifest. No single winner.
2. **Extraction** — flatten & de-dup dependency names; filter base packages. No execution of untrusted input.
3. **Scan (parallel)** — A · Hygiene (deptry) · B · Security (osv-scanner).
4. **Aggregation** — both branches merge into one `ComplianceReport` + human summary.
5. **Teardown** — ephemeral files removed via `try/finally` — never mutate host or source.

---

## 05 · What comes out

- **ComplianceReport JSON** — the canonical artifact, schema-validated against a committed `report-schema.json` (JSON Schema 2020-12).
- **Human summary** — a scannable stdout rollup for CI logs; the same data, never the source of truth.
- **CycloneDX SBOM** — valid BOM with correct purls (`pkg:pypi` / `pkg:conda`) + honest per-manifest coverage.
- **Actionable findings only** — package + location for hygiene; advisory ID + affected/fixed version for security. No theoretical noise.

---

## 06 · The severity-tiered gate

**Verdict lattice — highest wins:** `error` (exit 2) › `policy-violation` (exit 1, blocks) › `indeterminate` (exit 1, unproven) › `warn` › `bypassed` › `clean` › `not-applicable` (all exit 0). Frozen exit enum: `0` `1` `2` `130`.

- **Default policy** — v1 blocks on CVSS-critical CVEs only; high/med/low + all hygiene warn. **v1.x adds a KEV tier** — any CISA-KEV-listed advisory on a pinned version blocks regardless of CVSS. Configurable via `--fail-on`, `max_critical`, `--fail-on-kev`.
- **Waivers as code** — `--bypass --reason` emits an expiring stanza (default 14 days) the team commits. The tool reads it, never writes the repo.
- **Typed errors** — `unparsable-manifest` · `engine-unavailable` · `engine-crash` · `internal-error`.

---

<!-- _class: part -->

## PART II — In practice

Running it today

---

## 07 · Who runs it, at what scale

- **Platform Engineers** — CI/CD pipelines
- **DevSecOps Engineers** — compliance & SBOM data
- **Python developers** — pip- + conda-sourced, any shape

**20k+** repo fleet, concurrent (NFR1 scalability)

---

## ◎ Three rings — scan the whole supply chain

Warden runs at three depths. The further out it scans, the more it **prevents** rather than reports.

- **Public upstream** *(vision)* — scan PyPI & conda-forge themselves: malicious packages, typosquats, name-squatting, stale/abandoned feedstocks. → *blocklists*
- **Registry perimeter** *(v1.x)* — turn that intel into block / allow lists on Artifactory / JFrog; quarantine bad packages so they never cross the firewall. A census of everything that enters. → *clean pulls*
- **Consumption edge** *(today)* — scan repos, desktops & CI: the six axes on what apps actually pull. Precise per-project, but only sees what you scan.

Scan the **edge** and you report what you found; scan the **supply** and you prevent what enters.

---

## 08 · Local & workstation mode

CI is the primary consumer — but the supported **first contact is a developer at a terminal**. Same CLI, same exit codes.

- **First contact** — `--warn-only` at a terminal; trial the gate and clear a finding before wiring CI.
- **Waiver authoring** — local-only by design; `--bypass` emits a stanza for the human to commit. The tool never writes the repo, so CI can't.
- **Environment debugging** — chase an `engine-unavailable` exit 2 outside the runner image; a `doctor` self-check verifies the engines are present.

Local mode never softens the gate — same verdict lattice, same exit codes, TTY-colour auto-detect, zero prompts.

---

## 09 · Three ways a repo flows through the scanner

**Path A · PyPI project (native)** — DETECT `pyproject.toml`/`requirements.txt`/`*.lock` → DELEGATE deptry reads source, osv-scanner reads native lockfile → UNIFY one ComplianceReport → OUTCOME `clean` / `warn` / `policy-violation`.

**Path B · Conda / Pixi project (the E1 wedge)** — DETECT `environment.yml`/`meta.yaml`/`recipe.yaml`/`pixi.toml` → BRIDGE manifest engine synthesizes a version-pinned `requirements.txt` from `pixi.lock` / `conda-lock` → UNIFY deptry + osv-scanner run over it → OUTCOME `coverage-flagged` / `indeterminate` (name-only fallback never a silent pass).

**Path C · Non-Python repo (out of scope)** — DETECT no supported manifest → SKIP both engines → REPORT honestly → OUTCOME `not-applicable`, `exit 0`.

---

## 10 · Which tool, when

Warden is the fleet edge — one of several scanning surfaces. It complements, not replaces, the atlas and container tooling.

| What you have | Reach for |
| --- | --- |
| Any repo, no atlas — a CI or terminal gate on pinned deps (hygiene + CVEs) | **Warden** (this tool) |
| The atlas host — gap / version-lag buckets, freshness-percentile policy, worklists | `inventory-match --policy` |
| Exotic — containers, K8s, live envs, third-party SBOMs, non-Python | `scan-project` |
| The migrated Kedro pipeline (future) | the FR-18 unified gate |

---

<!-- _class: part -->

## PART III — Where it's going

Roadmap · not yet shipped. Everything from here down is roadmap and vision — v1 is the gate described in Parts I–II.

---

## 11 · Beyond v1 — now, next & later

**NOW · v1.x — completes the four axes**
- **License compliance** (Axis 3) — metadata-based SPDX via `license-expression`, gated by allowed families; unknown → indeterminate, written to SBOM.
- **Currency & supportability** (Axis 4) — is each dep and the runtime on a supported line: LTS · N / N-1 · not EOL?
- **Baseline & grandfathering** — accept existing debt, gate only **new** findings.
- **Automated fix PRs** — open remediation PRs, not just findings.

---

## 11 · Beyond v1 (cont.)

**NEXT · v2 — the governance layer**
- **Pluggable scanners** — multiple security backends behind one report.
- **Allowlist enforcement** — check every dep against an approved-library registry.
- **Maintenance & health** (Axis 6) — cadence, bus-factor, abandonment risk; feeds the OSS give-back loop.
- **Vendor-support backlog** — auto-generate tracked work items (fix CVE, upgrade to 3.14 LTS, drop EOL deps).

**LATER · Vision**
- **Reachability analysis** — flag a CVE only when vulnerable code is actually called.
- **Malicious-package detection** (Axis 5 · provenance) — install-script/behavior signals, signing & attestation.
- **Alternate-library suggestions** — vetted replacements for unused/risky/unmaintained deps.
- **Sibling ecosystems** — `js-depcheck-osv`, `go-<tool>-osv` share osv-scanner + the report schema.

---

<!-- _class: part -->

## PART IV — At enterprise scale

Vision · fleet & ecosystem

---

## 12 · The control plane

Governing a Python OSS footprint across thousands of repos needs more than a per-repo gate. Warden's report contract is the feed for a fleet-wide control plane.

- **Fleet intelligence** — central estate dashboard · cross-repo dependency graph · risk-trend tracking · KEV/EPSS enrichment · peer benchmarking · historical SBOM diff · fix-at-source ledger · license-mix dashboard · sponsorship candidates.
- **Policy & governance** — policy-as-code · golden-path catalog · waiver governance · typosquat detection · GRC sync · EOL calendar · establish an OSPO · license allow/deny families · outbound-OSS policy.
- **Supply-chain integrity** — SBOM registry + VEX · provenance & signing · private-index enforcement · registry/Artifactory gate · upstream intel → blocklists · maintainer-risk signals · auditor evidence packs · data residency · repackaging patch provenance · source-fix registry · patch attribution & upstreaming.

---

## 12 · The control plane (cont.)

- **Scale & operations** — incremental PR-diff scans · fleet-wide auto-remediation · SIEM/ticketing (Jira, ServiceNow, Splunk, Slack) · SSO/RBAC + evidence (SOC 2 / ISO, air-gapped DB) · API + webhooks + Terraform · notification routing · PyPI ↔ conda-forge tracking · auto NOTICE/attribution in CI · contribute-back PR automation.
- **Program management** — remediation SLAs & MTTR · ownership & chargeback · campaign mode · auto-enrollment · conda-forge onboarding · Python 3.14 support · stewardship ownership · sponsorship & funding budget · contribution OKRs & burn-down.

---

## 13 · Open-source policy, governance & sustainability

Consuming OSS at scale is a stewardship responsibility, not just a risk to gate. Warden feeds the OSPO's practice.

- **Policy (OSPO)** — usage & contribution policy · license allow/deny families · new-dependency intake review.
- **Governance (compliance)** — license-obligation tracking · stewardship ownership · export-control & provenance.
- **Sustainability (give back)** — upstream funding (Tidelift, Sponsors, Open Collective) · maintainer & community health · contribute-back tracking.

---

## 14 · What each leader gets

The same report feeds executive scorecards — each measured on a different outcome.

- **CISO** — provable, board-ready risk reduction: fleet risk score & heatmap · MTTR & SLA compliance · audit evidence on demand · zero-day readiness.
- **CDXO** — a gate developers don't route around: gate-friction metrics · shift-left ergonomics · auto-fix throughput · time-to-green.
- **CIO** — one view of the OSS portfolio: inventory · modernization dashboard · cost & consolidation · policy conformance.
- **CDAO** — governed, reproducible data stacks: data/ML dependency governance · model & pipeline SBOM lineage · diffable env reports · report as a data product.

---

## 14 · What each leader gets (cont.)

- **DevSecOps Lead** — one gate to run across the fleet: runner provisioning (engines as declared deps) · fleet rollout config-as-code · gate tuning · engine upkeep.
- **General Counsel** — license & IP exposure under control: license-obligation register · copyleft & unknown-license exposure · outbound-OSS clearance · audit-ready trail.
- **CRO** — OSS risk in the enterprise register: aggregated risk posture · third-party & acquired-code risk · regulatory exposure mapping · risk-acceptance governance.
- **OSPO Lead** — consume well, give back deliberately: stewardship ownership · upstream funding & contribute-back · source-fix ledger · community-health signals.

---

## 15 · Integration surface — engines

A producer-agnostic report contract (purl + CycloneDX) lets tools slot in as an **engine**, a **data / enrichment feed**, an **actuator**, or a downstream **consumer**.

| Tool / source | Category | Slot | Status |
| --- | --- | --- | --- |
| `deptry` | Hygiene | Hygiene engine | **Current** |
| `fawltydeps` · `pip-check-reqs` · `vulture` | Hygiene | Hygiene engine (`--engine`) | Candidate |
| `uv` (Astral) | Resolver / lockfile | Manifest & lock source | Candidate |
| `osv-scanner` | Vulnerability | Vuln engine | **Current** |
| `osv-scalibr` · `vdb` · `Trivy` · `Grype` · `pip-audit` · `Capslock` | Vulnerability | Pluggable vuln engine | Candidate |
| **`Basilisk` (prefix.dev)** | conda-forge advisory · OSV-compatible API | Conda-native vuln source (E2) | Candidate |
| **`parselmouth` (prefix.dev)** | PyPI ↔ conda mapping | Conda purl bridge (unlocks OSV/vdb for E2) | Candidate |
| `CycloneDX` | SBOM | SBOM emission | **Current** |
| `cdxgen` · `Syft` | SBOM + reachability | SBOM engine · reachability · signing | Candidate |
| `rattler-build` / `rattler` (prefix.dev) | conda build + metadata | Manifest / metadata source (E2) | Candidate |

---

## 15 · Integration surface — data & feeds

| Tool / source | Category | Slot | Status |
| --- | --- | --- | --- |
| `OSV.dev` | Advisory DB | Vuln data source | **Current** |
| `VulnerableCode` (AboutCode) | Open purl-native vuln DB | Vuln data source (offline) | Candidate |
| `PyPA Advisory DB` | PyPI advisory | Enrichment feed (OSV-format) | Candidate |
| `NVD / CVE (MITRE)` · GHSA · CWE | Advisory DB / taxonomy | Enrichment feed | Planned / Candidate |
| `EUVD` (ENISA) | EU vulnerability DB | Enrichment feed | Planned |
| `CISA KEV` | Exploit intel | **v1 gate tier** + enrichment | Candidate |
| `FIRST EPSS` · `VulnCheck` | Exploit intel | Prioritization enrichment | Candidate / Planned |
| `license-expression` · SPDX list | License (SPDX) | v1.x license engine + data | Candidate |
| `conda about:` + `importlib.metadata` | License data | v1.x license inputs (no scan) | Candidate |
| `OSS Review Toolkit (ORT)` · `ClearlyDefined` · `ScanCode` | License + policy | Engine / feed / deep scan | Candidate / Planned |
| `endoflife.date` · `Repology` | Currency / EOL | Currency feed | Planned |
| OpenSSF Scorecard · criticality_score · Libraries.io · Tidelift | Health / sustainability | Health & sponsorship feed | Candidate / Planned |
| `Sigstore / SLSA` · `in-toto / GUAC` · PyPI Trusted Publishing (PEP 740) · `model-transparency` | Provenance | Signing · attestation · graph | Planned |
| Google Assured OSS · Anaconda Defaults | Vetted base | Trusted base + provenance | Planned |
| OpenSSF Package Analysis · GuardDog | Malware | Malicious-pkg feed / engine | Planned |

---

## 15 · Integration surface — actuators, consumers & standards

**Actuators & platforms:** Renovate (fix-PR actuator) · Allstar (org security-policy enforcement) · OWASP Dependency-Track (CycloneDX monitoring) · DefectDojo (vuln management) · `cf_atlas` (internal enrichment producer/consumer — shares CycloneDX + `cfe:*` purls).

**Consumers (SCA / CNAPP):** Black Duck · Snyk · Nexus IQ · Mend · JFrog Xray · Wiz · Prisma Cloud · GitHub Advanced Security / Dependabot · Endor Labs · Semgrep Supply Chain.

**Standards Warden speaks — the contracts that make it pluggable:**
`purl` · `vers` · `OSV schema` · **CycloneDX** · `SPDX` · `OpenVEX / CSAF` · `SARIF` · `CVE 5.x` · `CVSS` · `EPSS` · `PEP 740` · `PEP 639` · `SLSA` · `in-toto`

> **Ecosystem support** is tracked per source in the infographic matrix — each tagged **pip** · **conda** · **pixi** (conda-native: Basilisk, parselmouth, rattler-build, Anaconda Defaults).

---

## → Start here — the on-ramp

Adoption starts at a terminal, not a pipeline. Three steps from first run to fleet gate.

1. **Try it locally** — run `warden scan . --warn-only` at your terminal; see findings and clear one, no CI wiring needed.
2. **Make it pass, honestly** — lock (`pixi.lock`), file an expiring waiver, or fix the finding. Green is **earned**, never faked.
3. **Gate in CI** — wire the same command; its exit code blocks risky merges. Same lattice, now running fleet-wide.

---

<!-- _class: lead -->

Honest by design — no false greens

# Warden refuses to fake a pass.

If it can't prove your dependencies are safe, it fails — until you pin them, formally accept the risk, or explicitly run `--warn-only`. An honest "not verified" beats a false "all clear."

**Warden** · module `pyforge.warden` · dist `pyforge-warden` · docs/specs/pyforge-warden.md
