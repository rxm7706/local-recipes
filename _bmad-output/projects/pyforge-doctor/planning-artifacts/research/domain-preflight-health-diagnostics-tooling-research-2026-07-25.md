---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/ecosystem-crew.md
research_type: 'domain'
research_topic: 'Preflight / health-check / diagnostics tooling for software supply chains and dev toolchains'
research_goals: 'Ground pyforge-doctor (Doctor) product-brief and PRD in the mental models, taxonomies, and conventions of comparable diagnostics tools, so Doctor consolidates atlas + warden signals in a shape practitioners already recognize.'
user_name: Rxm7706
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT scope by design — Doctor is an internal-facing developer tool for the pyforge factory, not a market-facing product. This report skips market-sizing/competitive-share analysis and focuses on the domain''s practices, taxonomies, and mental models: how comparable tools structure checks, communicate severity, and hand off to remediation.'
---

# Research Report: Domain Research — Preflight / Health-Check / Diagnostics Tooling

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain (light — internal tool)

---

## Research Overview

Doctor is a **consolidation, not an invention**: it wraps existing pyforge instruments
(cf_atlas health/watch CLIs, warden's engine-availability self-check) behind one CLI
with three verbs — `check` (pre-flight), `monitor` (continuous pulse), `diagnose`
(root cause + prescription). Before drafting the product brief, this report surveys
how the wider ecosystem of "doctor"-shaped tools structure the same three jobs, so
Doctor's shape is recognizable rather than novel-for-novelty's-sake.

Four reference points were surveyed, chosen because each maps to one Doctor verb or
consolidation concern:

1. **`brew doctor`** (Homebrew) — the namesake pattern; pre-flight/reactive diagnostics.
2. **`flutter doctor`** (Flutter SDK) — pre-flight toolchain verification with tri-state result categorization.
3. **`npm doctor`** (npm CLI) — a second pre-flight exemplar, useful for its explicit check taxonomy.
4. **Renovate Dependency Dashboard** / **GitHub Dependabot alert triage** — the continuous-pulse (`monitor`) and prescription-ordering (`diagnose --prescribe`) side, at fleet scale.

Methodology: targeted web search against each tool's own documentation and second-order
analysis (blog posts, GitHub discussions/issues), no paid/gated sources. Findings below
are organized by Doctor's three verbs rather than by tool, since the goal is pattern
extraction, not tool-by-tool comparison.

---

## 1. Pre-flight pattern (`doctor check`) — what `brew doctor`, `flutter doctor`, `npm doctor` agree on

All three well-known "doctor" CLIs converge on the same five structural choices,
independently arrived at across three different ecosystems (package manager, mobile
SDK, JS package manager):

- **Read-only, non-mutating.** None of the three repair anything by default. `brew doctor`
  explicitly documents itself as diagnostic-not-corrective — it "prints warnings... and
  leaves the choice of any corrective command to the operator." `flutter doctor` "detects
  problems and suggests fixes, but you must resolve them manually" (narrow exception:
  `flutter doctor --android-licenses` is an explicit opt-in mutating subcommand, not the
  default path). This is a strong, load-bearing convention: a pre-flight tool that mutates
  state by default breaks the "safe to run anytime" property that makes pre-flight checks
  trustworthy.
- **Modular, individually-nameable checks.** `brew doctor --list-checks` enumerates
  internal check names (`check_access_directories`, `check_broken_sdks`, ...) and supports
  re-running one in isolation. `npm doctor` groups checks into named categories (Node/Git
  executability, registry reachability, directory permissions, cache integrity, version
  currency). This argues for Doctor's `check` engines being addressable/filterable
  individually (`doctor check --engines osv-scanner`), not just a monolithic all-or-nothing
  run — directly reusable for warden's existing engine-availability self-check, which is
  already structured as one check per engine.
- **Tri-state (not binary) result categorization.** `flutter doctor` explicitly uses three
  states — pass / fail / potential-problem (✅ / ❌ / ⚠️) — not a pass/fail binary. This
  matters for Doctor: a missing *optional* engine (e.g., an enterprise-only scanner) is a
  different finding than a missing *required* one, and collapsing both to "FAIL" would make
  `doctor check --env --engines` too noisy to trust, which is exactly the failure mode
  `brew doctor` warns about ("please don't worry... just ignore this" for informational-only
  warnings). A tri-state model (ok / warn / fail) with a documented exit-code contract per
  state is the domain-standard shape.
- **Explicit invocation triggers, not just CI gating.** Both tools are also documented as
  reactive tools — run after a failure, after an environment change, or before filing an
  issue — in addition to being embedded in CI (`brew doctor` runs as part of Homebrew's own
  CI suite). Doctor's Dream framing ("pre-flight before Marshal spins the factory") covers
  the CI-gate case; the domain pattern suggests also documenting the reactive use case
  ("run `doctor check` after a build failure to see if it was environmental") as a first-class
  entry point, not an afterthought.
- **Version/currency checks as a first-class category, not bolted on.** `npm doctor`
  treats Node/npm version currency as one of its five named check categories, on par with
  registry reachability and cache integrity. For Doctor this suggests engine-*version*
  drift (not just engine-*presence*) belongs in `doctor check --engines` from day one —
  relevant because warden's self-check and the atlas CLIs both have meaningful minimum-version
  contracts.

**Adjacent pattern (Kubernetes ecosystem):** Replicated's `kubectl preflight` /
`kubectl support-bundle` split pre-installation conformance testing from
post-installation diagnostics as two distinct verbs — structurally the same split Doctor
already has between `check` (pre-flight) and `diagnose` (post-hoc, targeted). IBM's
`cpd-cli health` vs `cpd-cli diag` draws the identical line. This cross-validates Doctor's
three-verb design: pre-flight, continuous health, and targeted diagnosis are treated as
separate concerns industry-wide, not collapsed into one command with flags.

## 2. Continuous-pulse pattern (`doctor monitor`) — fleet-scale health surfaces

Renovate's Dependency Dashboard is the closest analog to `doctor monitor --fleet`: a
single surface aggregating per-repo dependency state (pending updates, blocked PRs,
warnings) so an operator doesn't have to check each repo individually. Two findings are
directly relevant to Doctor's fleet mode:

- **Native dashboards don't scale past the single-repo/platform boundary.** Renovate's
  dashboard is fundamentally per-repository (implemented as a GitHub/GitLab issue in that
  repo); there is no native cross-repo aggregation. Operators who need fleet-wide visibility
  either build a custom aggregator from Renovate's JSON output or adopt a third-party
  operator layer (e.g., mogenius's Kubernetes-based Renovate Operator, which adds a
  cross-repo web dashboard + Prometheus metrics + declarative scheduling on top).
  **Implication for Doctor:** `doctor monitor --fleet` is exactly the missing
  cross-repo/cross-feedstock aggregation layer this pattern shows the ecosystem building
  ad hoc — Doctor's advantage is that cf_atlas already has the fleet-scale data model
  (the `packages`/`feedstock_health` tables), so it doesn't need Renovate's workaround of
  scraping N per-repo issues; it can query the atlas directly. This is a concrete
  validation of the "consolidation, not invention" framing in the Dream.
- **Duplication/identity bugs are a known failure mode at fleet scale.** Renovate users
  hit duplicate-dashboard issues when the bot identity changes across a large repo set.
  Doctor's fleet mode should treat "stable identity of what's being monitored" (e.g., a
  feedstock's canonical name across atlas snapshots) as a correctness requirement, not an
  afterthought — directly relevant to atlas's own `feedstock_name` normalization history
  (see project memory: Phase B.5 dbt fix, v8.76.1).
- **Watch axes should be named and independently selectable**, mirroring `--watch
  staleness,cve,abandonment` in the Dream. This matches Renovate's own filterable-dashboard
  and Dependabot's per-signal (severity/EPSS/ecosystem/scope) filtering — fleet monitors
  in this domain are expected to expose their signal taxonomy as first-class filter
  arguments, not hide it behind an opaque "health score."

## 3. Diagnose-and-prescribe pattern (`doctor diagnose --prescribe`) — ordered remediation

GitHub Dependabot's alert-triage evolution is the most mature public example of turning
raw findings into an **ordered** worklist, which is the hardest part of Doctor's contract
("every diagnosis names its root cause and ships an ordered prescription"):

- **Multi-signal ranking, not single-severity sort.** Dependabot's stated evolution is
  from CVSS-only sorting to a three-pillar model — **CVSS** (severity), **EPSS**
  (exploitation likelihood), **KEV** (confirmed active exploitation) — combined with
  repository-context signals (production vs. dev dependency scope, patch availability,
  custom repo properties like business-criticality). GitHub's own framing: "only ~0.5% of
  vulnerabilities have an EPSS score above 50%," which is why EPSS is described as
  high-leverage *in combination with* CVSS, not a replacement for it. This is a direct,
  reusable validation for Doctor's `--prescribe` ordering logic — and it's already
  architecturally available: warden's v1 gates (KEV `--fail-on-kev` + EPSS `--min-epss`)
  and cf_atlas's Phase G EPSS/KEV overlays are the exact three-pillar inputs Dependabot
  describes, meaning Doctor's prescription ranking doesn't need new data — it needs a
  ranking function over data the fleet already has.
- **"Snooze until fixable" as an explicit state, not silence.** Dependabot's auto-triage
  rules include a specific state for "no fix available yet" (snooze-until-patch) rather
  than silently dropping or permanently escalating such findings. This maps to Doctor's
  `indeterminate`/`warn` semantics already established in the warden spec (D3: feed
  absence under a KEV policy → `indeterminate`, never a silent no-op) — the same
  discipline should extend to `diagnose --prescribe`: an unfixable-today finding is a
  distinct prescription state ("wait/track"), not omitted from the worklist.
- **Ordering must be explainable, not a black-box score.** The critiqued failure mode in
  Dependabot's own community feedback is that severity signal is sometimes "buried,"
  forcing manual re-scanning of alert text. The lesson for `--prescribe` is that the
  ordered worklist should show *why* each item is ranked where it is (which signals fired:
  KEV present / EPSS percentile / staleness lag / abandonment score) rather than emitting
  an opaque priority number — directly reusable as an output-contract requirement for the
  architecture stage.
- **pip-audit / Safety's operational sequencing** (scan → filter-by-fixability →
  cross-check secondary source → prioritize-by-severity) is a smaller-scale version of the
  same idea and reinforces that "filter to what's actionable today" is a distinct pipeline
  stage from "rank what's actionable" — Doctor's `--prescribe` should probably do both:
  first partition (actionable now / blocked-on-upstream-fix / accepted-risk), then rank
  within the actionable partition.

## Cross-Domain Synthesis: What Doctor Should Borrow vs. Deliberately Diverge From

| Pattern | Domain consensus | Doctor's position |
|---|---|---|
| Mutation | Read-only by default across every surveyed tool | Adopt as-is — `check`/`monitor`/`diagnose` are all read-only; any future `--fix` actuator (cf. warden's `--open-fix-prs`) must be an explicit opt-in flag, never default. |
| Check granularity | Named, individually addressable checks (`brew doctor --list-checks`) | Adopt — expose warden's per-engine self-checks and atlas's per-signal watches as individually filterable, not one opaque bundle. |
| Result states | Tri-state (ok/warn/fail), not binary | Adopt — matches warden's existing `indeterminate` semantics; extend the same three-state vocabulary to `doctor check`. |
| Fleet aggregation | Ecosystem builds this ad hoc on top of per-repo tools (Renovate operator pattern) | **Diverge favorably** — Doctor doesn't need to build this ad hoc; cf_atlas is already the fleet-scale data model Renovate users hand-roll. This is the strongest evidence for the "consolidation, not invention" thesis. |
| Prescription ranking | Multi-signal (severity + exploitability + context), explainable, partitioned by actionability | Adopt — warden (KEV+EPSS) and atlas (staleness/abandonment/CWE) already produce the exact signals this pattern needs; `--prescribe` is a ranking/explanation layer over existing data, not a new scanner. |
| Invocation model | Both CI-gate AND ad hoc/reactive (post-failure) | Adopt both — the Dream's "before Marshal spins" framing covers CI; explicitly document the reactive use case too. |

## Assumptions

- No paid/gated competitive-intelligence sources were consulted (Gartner, Forrester, etc.)
  — inappropriate for an internal developer tool with no market-facing positioning need.
- "Domain" here is interpreted as *developer-tooling UX conventions for diagnostics*, not
  an industry/market in the traditional domain-research sense (no TAM/SAM/SOM,
  competitor market share, or regulatory-compliance analysis) — this matches the parent
  task's "market research light" instruction and Doctor's internal-facing audience.
- Renovate/Dependabot are treated as *design-pattern* references (how they structure
  triage), not as products pyforge-doctor competes with or must interoperate with.

## Open Questions

- Should `doctor check --engines` expose the same `--list-checks`-style introspection
  `brew doctor` offers, so operators can `doctor check --list` before running the full
  suite? (Left to PRD/architecture — likely yes, low cost, matches domain convention.)
- Should `doctor monitor --fleet` support a Renovate-Dashboard-style persistent surface
  (e.g., a committed status file or issue), or is CLI-output-only sufficient for v1 given
  Doctor's internal/agent-facing audience (agents can re-run the CLI; humans may want a
  persistent view)? (Deferred to PRD — flag as a v1-scope decision.)
- Where exactly does the JFROG_API_KEY unconditional-injection finding (credential
  hygiene) fit the tri-state model — is a hard-coded credential-scope violation always
  `fail`, or can it be `warn` in some enterprise configurations? (Deferred to PRD/architecture.)

## Sources

- [How to run brew doctor](https://www.simplified.guide/homebrew/brew-doctor-run)
- [`brew doctor` warns about CLI tools 3 times · Issue #11697 · Homebrew/brew](https://github.com/Homebrew/brew/issues/11697)
- [brew doctor | Fig](https://fig.io/manual/brew/doctor)
- [Homebrew/brew Maintainer Guide](https://docs.brew.sh/Homebrew-brew-Maintainer-Guide)
- [Homebrew Documentation: Common Issues](https://docs.brew.sh/Common-Issues)
- [Replicated Troubleshoot README (kubectl preflight / support-bundle)](https://github.com/replicatedhq/troubleshoot/blob/52e385ffce8cfe251c82e0c228f2240466e1f879/README.md)
- [IBM cpd-cli diagnostics documentation](https://www.ibm.com/docs/en/SSNFH6_5.2.x/cpd-cli/cpd-diagnostics.html)
- [🩺 Flutter Doctor: Diagnosing Setup Problems (Medium)](https://mailharshkhatri.medium.com/flutter-doctor-diagnosing-setup-problems-768bcf783ae4)
- [Flutter Doctor command guide (flutterfever.com)](https://flutterfever.com/flutter-doctor-command/)
- [Troubleshooting installation — Flutter docs](https://docs.flutter.dev/install/troubleshoot)
- [feat: discrete npm doctor commands · npm/cli@cf57ffa](https://github.com/npm/cli/commit/cf57ffa90088fcf5b028cc02938baae6228b5a40)
- [npm-doctor | npm Docs](https://docs.npmjs.com/cli/v11/commands/npm-doctor/)
- [npm doctor command - GeeksforGeeks](https://www.geeksforgeeks.org/node-js/npm-doctor-command/)
- [Dependency Dashboard - Renovate Docs](https://docs.renovatebot.com/key-concepts/dashboard/)
- [External Dependency Dashboard · renovatebot/renovate · Discussion #28900](https://github.com/renovatebot/renovate/discussions/28900)
- [Multiple (duplicate) "Dependency Dashboard" issues · Discussion #12131](https://github.com/renovatebot/renovate/discussions/12131)
- [Renovate Operator — Self-hosted Dependency Updates on Kubernetes (mogenius)](https://mogenius.com/renovate-operator)
- [Cutting through the noise: How to prioritize Dependabot alerts — GitHub Blog](https://github.blog/security/application-security/cutting-through-the-noise-how-to-prioritize-dependabot-alerts/)
- [Metrics for Dependabot alerts - GitHub Docs](https://docs.github.com/en/code-security/concepts/supply-chain-security/about-metrics-for-dependabot-alerts)
- [Dependabot EPSS scores now generally available — GitHub Changelog](https://github.blog/changelog/2025-02-19-dependabot-helps-users-focus-on-the-most-important-alerts-by-including-epss-scores-that-indicate-likelihood-of-exploitation-now-generally-available/)
- [Customizing auto-triage rules — GitHub Docs](https://docs.github.com/en/code-security/dependabot/dependabot-auto-triage-rules/customizing-auto-triage-rules-to-prioritize-dependabot-alerts)
- [Improving Dependabot Security Alerts for Faster Vulnerability Triage · Issue #14675](https://github.com/dependabot/dependabot-core/issues/14675)
- [pip-audit · PyPI](https://pypi.org/project/pip-audit/)
- [Auditing Python dependencies with pip-audit and Safety — Stack Harbor Knowledge Base](https://stackharbor.com/en/knowledge-base/python-pip-audit-safety/)
- [Best SCA Tools for Python (2026) — AppSec Santa](https://appsecsanta.com/sca-tools/sca-tools-for-python)
