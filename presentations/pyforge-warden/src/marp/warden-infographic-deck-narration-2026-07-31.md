# Narration script — Warden - Infographic Deck

> Extracted from `Warden - Infographic Deck.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 25 scenes.

## Scene 01 — Cover

Warden — pyforge-warden. One CLI guarding both Python ecosystems across six axes of dependency trust, returning one consolidated report.

## Scene 02 — Why Warden

One gate, both Python ecosystems, six axes of dependency trust — hygiene, security, license, currency, provenance, maintenance.

## Scene 03 — Part I

Part I — the tool, shipping in v1.

## Scene 04 — The problem

Dependency hygiene and security need disjointed tools — deptry and osv-scanner as separate pipelines, neither understanding conda/pixi manifests.

## Scene 05 — Two ecosystems

Python isn't one ecosystem. PyPI: ~850K packages, open upload, 20% of footprint. conda-forge: ~30K feedstocks, curated FOSS, 80% of footprint. Engines are pluggable, not fixed.

## Scene 06 — Six axes

Six axes, each a different question. v1 ships hygiene + security; license & currency complete the v1.x gate; provenance & maintenance are vision. Engines are pluggable.

## Scene 07 — Six manifests

The manifest engine is the wedge — neither scanning engine parses conda/pixi. No untrusted input executed: yaml.safe_load only.

## Scene 08 — One pipeline

One invocation, one pipeline: discovery, extraction, parallel hygiene + security scan, aggregation into one ComplianceReport, teardown that never mutates host or source.

## Scene 09 — What comes out

Outputs: the canonical ComplianceReport JSON (schema-validated), a human summary, a CycloneDX SBOM, and actionable findings only.

## Scene 10 — The gate

The severity-tiered gate: verdict lattice highest-wins, frozen exit enum 0/1/2/130, default policy blocks on CVSS-critical + KEV tier, waivers-as-code, typed errors.

## Scene 11 — Part II

Part II — in practice, running it today.

## Scene 12 — Who runs it

Platform engineers (CI/CD), DevSecOps (compliance + SBOM), Python developers (pip + conda). Designed for a 20k+ repo fleet, concurrent (NFR1).

## Scene 13 — Three rings

Three rings: consumption edge (today), registry perimeter / JFrog blocklists (v1.x), public upstream scanning (vision). The further out, the more it prevents rather than reports.

## Scene 14 — Local mode

CI is the primary consumer, but first contact is a developer at a terminal. Same CLI, same exit codes. Waiver authoring is local-only. Local mode never softens the gate.

## Scene 15 — Flow paths

Three ways a repo flows: Path A PyPI native (delegate to engines), Path B conda/pixi wedge (manifest engine synthesizes requirements), Path C non-Python (not-applicable, exit 0).

## Scene 16 — Which tool when

Warden is the fleet edge — one of several scanning surfaces. It complements the atlas host, container tooling, and the future unified gate.

## Scene 17 — Part III

Part III — where it's going. Roadmap and vision; v1 is the gate in Parts I–II.

## Scene 18 — Beyond v1

Now: v1.x completes license + currency, baseline/grandfathering, automated fix PRs. Next: pluggable scanners, allowlist, maintenance/health, vendor-support backlog. Later: reachability, malicious-package detection, alternate-library suggestions, sibling ecosystems.

## Scene 19 — Part IV

Part IV — at enterprise scale. Fleet and ecosystem vision.

## Scene 20 — Control plane

Governing thousands of repos needs more than a per-repo gate. Warden's report contract feeds a fleet-wide control plane across five domains.

## Scene 21 — OSS sustainability

Consuming OSS at scale is stewardship, not just risk. Warden feeds the OSPO's policy, governance, and sustainability practice.

## Scene 22 — What leaders get

The same report feeds executive scorecards: CISO, CDXO, CIO, CDAO — each measured on a different outcome.

## Scene 23 — Integration surface

A producer-agnostic report contract lets tools slot in as an engine, an enrichment feed, or a downstream consumer — from deptry/osv today to commercial SCA consumers.

## Scene 24 — Start here

Adoption starts at a terminal: try it locally with --warn-only, make it pass honestly (lock/waive/fix), then gate in CI with the same command.

## Scene 25 — Honest by design

Warden refuses to fake a pass. If it can't prove your dependencies are safe, it fails — until you pin, accept the risk, or run --warn-only. An honest 'not verified' beats a false 'all clear.'
