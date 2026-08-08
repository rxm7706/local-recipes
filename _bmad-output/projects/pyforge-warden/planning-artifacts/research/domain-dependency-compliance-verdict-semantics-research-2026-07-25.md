---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-warden.md
  - docs/specs/pyforge-warden.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/market-dependency-compliance-sca-landscape-research-2026-07-25.md
research_type: 'domain'
research_topic: 'Verdict-semantics and machine-contract conventions in software supply-chain compliance tooling: exit-code/status taxonomies, honest-coverage reporting, KEV/EPSS enrichment practice, and waivers-as-code, as domain grounding for pyforge-warden'
research_goals: 'Verify — RETROSPECTIVELY, against the already-SHIPPED v1 (schema 1.1.0, frozen exit-code contract {0,1,2,130}, the 7-rung verdict lattice) — that Warden''s specific machine-contract design choices are domain-standard practice, not invented conventions, and identify which pieces are genuinely novel (the never-false-green `indeterminate` state) versus adopted from established standards bodies (CycloneDX/purl, CISA KEV, FIRST EPSS).'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT + RETROSPECTIVE scope, complementary to the companion market-research report (which surveys named competitor tools). This report instead surveys the underlying STANDARDS and domain conventions those tools converge on — machine-readable feed protocols (KEV, EPSS), SBOM/purl identity standards (CycloneDX), and reporting taxonomies (SARIF) — since Warden''s FR38/FR36/FR27 design choices are explicitly built to interoperate with these standards bodies, not just with the named tools.'
methodology_note: 'The session WebSearch budget was exhausted (200/200) before this report began. Per the task''s explicit fallback instruction, claims below are grounded in WebFetch against each standard''s own publishing body (FIRST.org for EPSS, `gh` for the CycloneDX specification repository) plus internal grounding from Warden''s own architecture/PRD documents (which already independently established the CISA KEV and SARIF facts cited below, since the CISA.gov KEV catalog page itself returned HTTP 403 to WebFetch this session and could not be freshly re-fetched — flagged honestly below rather than silently asserted as freshly re-verified).'
---

# Research Report: Domain Research — Verdict Semantics & Machine-Contract Conventions in Supply-Chain Compliance Tooling

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain (light, retrospective — machine-contract conventions)

---

## Research Overview

Warden's most load-bearing design decisions are not scanning logic — they are the **machine contract**: a 7-rung verdict lattice (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`), a frozen exit-code enum (`{0, 1, 2, 130}`), a schema-versioned `ComplianceReport` (currently 1.1.0), and enrichment from two external standards feeds (CISA KEV, FIRST EPSS). This report checks each of these against the domain conventions the wider supply-chain-security tooling ecosystem has already converged on, to verify Warden adopted established practice where it exists and innovated only where the domain genuinely had a gap (principally: the `indeterminate` state itself).

---

## 1. KEV — CISA's Known Exploited Vulnerabilities catalog as a domain-standard feed

Warden's FR36 (`--fail-on-kev`) enriches vulnerability findings against the CISA KEV catalog — a U.S. government-published, machine-readable JSON feed of vulnerabilities with **confirmed, real-world active exploitation** (as distinct from theoretical CVSS severity). This is not a Warden-specific data source: KEV-based gating is the same three-pillar model GitHub's own Dependabot alert-prioritization evolution converged on independently (documented in the companion `pyforge-doctor` domain research, 2026-07-25: "CVSS + EPSS + KEV" as the mature triage model). **Methodology caveat:** the CISA.gov KEV catalog page itself returned an HTTP 403 to a direct WebFetch this session (government sites commonly block automated fetches) and could not be freshly re-confirmed here — the KEV-as-JSON-feed characterization rests on Warden's own architecture.md frontmatter (`cisa-kev: "cached JSON feed; offline default..."`) and the cross-project Doctor research's independent citation, not a fresh fetch in this report. Flagged honestly rather than claimed as newly verified.

## 2. EPSS — FIRST.org's Exploit Prediction Scoring System, freshly confirmed

**Directly confirmed via live fetch of FIRST.org's own EPSS page (2026-07-25):** EPSS is a machine-learning system, published and maintained by FIRST.org's EPSS Special Interest Group, that "estimates the probability that a published CVE will be exploited in the wild in the next 30 days" — publishing a **0–1 probability with ranking percentiles, updated daily**, "freely and openly accessible via CSV and API." This directly grounds Warden's FR36 `--min-epss` gate and its `epss{score, percentile}` schema fields (FR38) — Warden's design (cached daily feed, per-feed provenance `{source, snapshot_at, max_age_ok}`, absent/stale-under-active-policy → `indeterminate`) is a domain-conventional consumption pattern for a feed EPSS's own publisher explicitly designs for exactly this kind of daily-refresh, API-or-CSV batch consumption — not a bespoke integration.

## 3. CycloneDX + purl — SBOM identity standards, and confirmation Warden's timing bet was correct

`gh repo view CycloneDX/specification` (2026-07-25): latest release **1.7.1** (published 2026-06-02) — CycloneDX has reached OASIS/ECMA standardization (ECMA-424 per Warden's own PRD framing) and continues shipping point releases. Warden's FR27 SBOM axis targets CycloneDX 1.6 (architecture.md's NFR-I1); the standard has since moved to 1.7.x, confirming the standards body remains active and iterating, not stalled — Warden's bet on CycloneDX as the SBOM interchange format (over a bespoke format) is validated by the standard's continued cadence. The purl (Package URL) spec Warden depends on for `pkg:pypi/…` vs `pkg:conda/…?channel=` component identity likewise reached ECMA-427 standardization per the same PRD-cited grounding — both are now formal standards, not community conventions subject to unilateral change, which reduces (not eliminates) the risk Warden's FR27/FR17 purl-correctness contract depends on a moving target.

## 4. SARIF — the honest-coverage/multi-tool-aggregation precedent Warden's design independently converges with

SARIF (Static Analysis Results Interchange Format, OASIS standard, currently v2.1.0) is the industry-standard answer to aggregating multiple tools' findings into one schema-validated, tool-tagged document — the same underlying problem Warden's `ComplianceReport` solves for its own four axes (this exact cross-reference was independently made in the companion `pyforge-doctor` technical research, 2026-07-25, which surveys SARIF directly). The domain-relevant finding for Warden specifically: SARIF's "multiple runs, one log, each tagged by producing tool" discipline is the same shape Warden's per-axis `coverage`/`gating` schema fields (FR38) implement for its own four internal axes (hygiene/security/license/currency) — Warden did not adopt SARIF itself (correctly scoped out as static-analysis-specific and a heavyweight fit for a dependency-compliance report), but its schema design independently rediscovered SARIF's core discipline: never flatten multi-source findings into an undifferentiated list that loses provenance.

## 5. Verdict/exit-code taxonomies — where Warden's `indeterminate` state is the genuinely novel contribution

The market-research companion report found no comparable tool (Renovate, Dependabot, Snyk as far as verifiable) implements an expiring-waiver mechanism as rigorous as Warden's FR24. The domain-conventions angle sharpens this further: the broader pattern across SCA tooling is a **binary or ternary** verdict model (pass/fail, or pass/fail/warn) — Warden's architecture.md itself documents the reconciliation history that produced the richer 7-rung lattice, specifically citing the failure mode a binary model creates: *"the pre-architecture design shipped a green-by-default on a bare `recipe.yaml`"* (the beachhead's most common artifact) — i.e., an unresolvable manifest rendering identically to a genuinely clean one. This is the precise "no-meaningful-scan" failure mode GitHub's own Dependabot alert-prioritization writeups (cited in the Doctor domain research) describe as a real, recurring failure across the wider domain — teams re-scanning alert text by hand because severity signal was silently buried or a scan silently under-covered. **Warden's `indeterminate` rung, sitting above `warn` specifically so a clean sibling axis can never mask "existed-but-couldn't-scan,"** is this report's clearest finding of a genuine domain gap Warden closes rather than merely reproduces — no comparable surveyed in either this report or the companion market research implements an equivalent non-collapsible partial-coverage state.

## 6. Waivers-as-code — cross-referencing the market research's Renovate finding against the domain pattern

The companion market-research report freshly confirmed Renovate's `ignoreDeps`/`packageRules` have no expiry mechanism. Framed as a domain convention rather than a single-tool comparison: the dominant pattern across CI/CD dependency tooling is a **static ignore-list** (a config-file entry that suppresses a finding indefinitely until a human manually removes it) — this is the shape of Renovate's `ignoreDeps`, and (per established, though not freshly re-verified this session, knowledge) the general shape of `.trivyignore`/`.grype.yaml` ignore-rules and GitHub Dependabot's `dependabot.yml` ignore block. Warden's FR24 (`.warden-waivers.yaml`, default 14-day expiry, `authorized_by` field, automatic re-block) is a **time-boxed loan, not a permanent mute** — the domain convention it improves on is real and independently confirmed for at least one major comparable (Renovate), giving this design choice solid grounding rather than resting on an assumed gap.

---

## Cross-Domain Synthesis: Adopted Standard vs. Genuine Warden Innovation

| Warden design element | Domain status | Finding |
|---|---|---|
| CISA KEV enrichment (FR36) | Established government/domain-standard feed | Adopted practice, consistent with the wider domain's CVSS+EPSS+KEV triage model (not independently re-fetched this session — flagged) |
| FIRST EPSS enrichment (FR36) | Established, freshly-confirmed daily-updated feed with CSV/API access | Adopted practice, direct fit for the feed's own designed consumption pattern |
| CycloneDX SBOM (FR27) | OASIS/ECMA-424 standard, actively iterating (1.6→1.7.1 since Warden's architecture doc) | Adopted, and the standard's continued cadence validates the timing bet |
| purl component identity (FR17/FR27) | ECMA-427 standard | Adopted |
| SARIF-style multi-source, tool-tagged aggregation discipline | Industry-standard pattern for combining multiple tools' findings | Independently rediscovered in Warden's per-axis coverage/gating schema, not literally adopted (correctly scoped out as a heavyweight, static-analysis-specific fit) |
| The 7-rung verdict lattice with a non-collapsible `indeterminate` state | No equivalent found in any comparable surveyed (binary/ternary is the domain norm) | **Genuinely novel** — the clearest true differentiator this report identifies |
| Auditable, expiring waivers (FR24) | Static, non-expiring ignore-lists are the domain norm (confirmed against Renovate; plausible but unverified against others) | Genuine improvement on a real, at-least-partially-confirmed domain gap |

---

## Assumptions

- This report is retrospective and complementary to the market-research report — it deliberately does not re-survey named competitor tools already covered there, focusing instead on the underlying standards/conventions layer.
- The CISA KEV catalog's JSON-feed characterization rests on Warden's own architecture documentation and the cross-project Doctor research, not a fresh fetch (CISA.gov returned HTTP 403 to this session's WebFetch) — flagged rather than silently presented as newly verified.
- No claim is made that Warden invented the concept of a verdict lattice broadly — only that its specific non-collapsible `indeterminate` rung, positioned above `warn`, is not matched by any comparable this report or its companion market-research report could locate.

## Open Questions

- Should a future Warden doc pass independently re-verify the CISA KEV feed's exact publication mechanics (update cadence, JSON schema stability) via a non-blocked fetch path, given this report could not? Low urgency — Warden's own feed-provenance discipline (`snapshot_at`/`max_age_ok`) already defends against staleness regardless of the exact publication cadence.
- Is there a real precedent for Warden's `indeterminate`-above-`warn` lattice positioning in any adjacent domain (e.g., data-quality contract tools, not just SCA tools) worth a follow-up survey if the lattice design is ever revisited? Not pursued here — flagged as a possible future angle, not a v1 gap.

## Sources

- [EPSS — FIRST.org](https://www.first.org/epss/) (fetched 2026-07-25) — publisher, update cadence, score/percentile semantics
- `gh repo view CycloneDX/specification` (2026-07-25) — 1.7.1 release confirmation
- CISA KEV catalog page (`https://www.cisa.gov/known-exploited-vulnerabilities-catalog`) — WebFetch attempt returned HTTP 403 this session; characterization instead grounded in internal docs (see below)
- Internal: `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` (pinned axis-data-contracts frontmatter: cisa-kev, first-epss, endoflife-date, lts-registry) — the claims being cross-checked, not external evidence
- Internal (cross-project): `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md` § 2 (SARIF) and its own Dependabot/KEV/EPSS citations — reused here as already-verified cross-project grounding rather than re-fetching the same sources twice in one day
- Companion report: `_bmad-output/projects/pyforge-warden/planning-artifacts/research/market-dependency-compliance-sca-landscape-research-2026-07-25.md` (this project) — the Renovate/Dependabot waiver-expiry findings this report builds on

---

# Refreshed 2026-08-08 — does "the gate that never lies" survive contact with reality?

Two weeks after ship (31/31, PR #110), the question this domain report can now answer empirically rather than by design review: did the never-false-green contract actually hold, and where does dishonesty risk *actually* live in a shipped four-axis gate? Grounding: the 8 tracked epic retros (`planning-artifacts/retros/`, promoted 2026-07-25) and the per-entry-verified deferred-work ledger (2026-07-30 pass). Companion: `technical-warden-dependency-gate-refresh-2026-08-08.md` for the full debt map.

## 1. The verdict layer held — and the near-misses prove the threat model was right

No false-green incident is recorded anywhere in the retros, the ledger, or the dogfood/corpus evidence. Stronger than absence-of-evidence: the validation teeth caught the exact failure class the domain thesis predicted, *before merge*, repeatedly:

- **Cross-package fixed-version attribution (5.1):** `_extract_fixed_version` read `fixed` events from every `affected[]` entry of a multi-package advisory — a wrong "upgrade to ≥X" remediation, named in the retro as "Warden's cardinal false-green risk." Caught by adversarial review, fixed with tests pre-merge.
- **Alias-collision silent-misroute (6.3)** — same class, same outcome.
- The **frozen-trio scope-check** (`report-schema.json`/`models.py`/`verdict.py`, frozen at 6.1) came back zero-diff on all 8 subsequent Epic-6 gates — no axis producer widened the contract.
- The **strace egress counter** (5.2) upgraded "never fetch silently" from a trusted claim to a measured one across the whole subprocess tree — closing a gap the ledger itself had flagged (the in-process socket-deny harness couldn't see child processes).

Domain conclusion: the `indeterminate`-above-`warn` lattice (this report's §5 novelty finding) was the right bet, and the *discipline stack around it* (sole-ownership meta-test, frozen-trio scope-check, differential oracle, egress proof) is inseparable from the claim. The lattice alone is a design; the stack is what made "never lies" empirical.

## 2. The refined thesis: dishonesty risk migrated from the verdict to the report's edges

What real use exposed is that with the verdict layer machine-guarded, the remaining honesty gaps live in surfaces the guards don't cover — each ledger-verified open:

- **The advice layer can still lie while the verdict tells the truth.** DW-5-1-6/7/8: a remediation line can advise an upgrade bound already satisfied (oldest-branch `fixed` selection), or point at the manifest declaring the *non-vulnerable* version. The exit code is right; the sentence next to it isn't. The domain lesson generalizes: **a compliance gate's contract must cover its prose, not just its projection** — no surveyed comparable treats remediation text as contract either, so this is an unclaimed honesty frontier, not a Warden-specific lapse.
- **Suppression state is under-told in the machine contract.** DW-6-8-3 (an expired suppression is invisible in `suppressions[]`) and DW-6-5-2 (`warn-as-error` leaves no trace in the persisted report — report and exit code can disagree about why the process failed). Both are "the report under-reports" rather than "the verdict over-promises" — a distinct, milder dishonesty class this report's original taxonomy didn't separate. It should: *verdict honesty* (never false-green) vs *narrative honesty* (the report fully explains the verdict).
- **The gate doesn't gate itself.** DW-5-2-5: the corpus/differential-oracle suite — the strongest extraction-honesty check — is wired to no CI or scheduler; an extractor render-parity break merges green today. For the domain thesis this is the sharpest finding: fail-closed *runtime* semantics do not substitute for fail-closed *regression* coverage.
- **Expiry-as-honesty has a calendar failure mode.** The 6.8 design (expiry forces re-review) is validated by use, but all 19 baseline entries share one `expires_at` (2027-07-24) — a deterministic future red-day an unattended consumer would misread as a code regression (DW-5-2-7). Domain refinement for any waivers-as-code adopter: **stagger expiries at issuance; a shared cliff converts an honesty mechanism into a false alarm.**

## 3. Cross-station: is Warden's verdict logic being duplicated? (checked in code, 2026-08-08)

The four-axis gate is consumed by sibling stations; the specific question was whether Doctor's health surface or Marshal's gate mechanics overlap Warden's verdict logic.

- **Doctor — wraps, with a managed (not eliminated) duplicate.** `pyforge-doctor`'s `sources/warden.py` calls `pyforge.warden.engines.run_doctor_checks` as a **library import, never a subprocess reimplementation** (its dream names this rule). But `doctor/checks/registry.py` carries a *deliberately static mirror* of Warden's check-name catalog — its own docstring admits it is "Doctor's OWN duplicate of warden's" list, defended by a meta-test that runs `sources.warden.gather()` once and fails on any rename/reorder/addition. Verdict: overlap exists, is self-aware, and is machine-guarded — the fix that would retire it is a cheap Warden API (`run_doctor_checks` exposing check names without executing) rather than any change on Doctor's side. Worth adding to Warden's backlog as a one-function courtesy export.
- **Marshal — parallel lattice by design, shared discipline, zero shared code.** `marshal/core/verdict.py` is an independent 6-rung lattice (`error > gate-failed > scope-violation > unevaluable > warn > clean`, exits 0–4) whose docstring *cites Warden's lattice as precedent* (explicitly matching Warden's warn→0 treatment) and reuses the sole-ownership + `EXIT_SIGINT=130` conventions. The rungs don't map 1:1 (Marshal gates *process* outcomes, Warden gates *dependency* outcomes), so unifying the lattices would be false economy — but the pattern has now been hand-copied three times (Warden, Doctor's `DoctorReport` envelope, Marshal), and Marshal's concurrent unification research (being written in parallel; not visible to this report) is the right owner for whether the *skeleton* (rung-table + total exit projection + sole-ownership meta-test) becomes shared infra. From Warden's side: its `verdict.py` (140 lines) is the reference implementation, and its `_engine_env()` subprocess seam is the other proven generalization candidate (see technical refresh §5).
- No station re-implements Warden's *decision* logic (which findings mean what) — the duplication is confined to check *catalogs* (Doctor, guarded) and lattice *shape* (Marshal, deliberate). The domain risk to watch is drift between three hand-maintained exit-code contracts consumed by the same CI surfaces.

## 4. Refresh verdict on this report's original findings

- The **`indeterminate` novelty claim (§5) stands** — nothing in the 2026-08-08 market re-check (osv-scanner v2.5.0, Scalibr, Safety CLI) surfaced a comparable non-collapsible partial-coverage state.
- The **waivers-as-code claim (§6) must be restated**: Snyk's `.snyk` *does* support `expires` (2026-07-25's open question, now resolved — see the market refresh §2). The domain gap survives but narrows to failure direction: Warden is fail-closed (mandatory expiry, malformed → never suppresses), the domain norm is fail-open (optional expiry; Snyk's own docs: a malformed date "will be respected and persist indefinitely").
- **New domain finding this refresh adds:** verdict honesty and narrative honesty are separable properties, and the shipped v1 proves the first while the ledger shows the second is where all remaining risk concentrates (§2). Any v1.x scope should treat "the report fully explains the verdict" as a contract surface of equal rank with the exit code.

## Refresh sources

- `planning-artifacts/retros/` — all 8 epic retros (read 2026-08-08); `planning-artifacts/deferred-work-ledger.md` (2026-07-30 verification pass) — every DW-* citation above
- Code read 2026-08-08: `pyforge/warden/verdict.py`; `pyforge-doctor/src/pyforge/doctor/checks/registry.py` + `checks/env_hygiene.py`; `pyforge-marshal/src/pyforge/marshal/core/verdict.py`
- `docs/dreams/pyforge-doctor.md` (the wrap-don't-reimplement rule), `docs/dreams/pyforge-charter.md` §4 (Warden's mandate)
- Market refresh companion: `market-dependency-compliance-sca-landscape-research-2026-07-25.md` § "Refreshed 2026-08-08" (the Snyk `expires` resolution reused here)
