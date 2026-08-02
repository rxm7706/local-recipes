---
title: "Dream — PyForge Warden: Compliance Gates"
date: 2026-08-02
status: archived
archived-reason: duplicate
owner: warden
scope: "Compliance gates, dependency scanning, policy enforcement, findings aggregation"
---

> **Superseded.** This Dream's six-item "Realization" list maps 1:1 onto capabilities
> [`docs/dreams/pyforge-warden.md`](pyforge-warden.md) (status: realized) already fully
> governs via `spec-pyforge-warden` (`status: shipped`, 31/31 stories merged via PR #110) —
> and Warden's entire shipped product already **is** "a pluggable multi-axis Python
> dependency compliance gate," verbatim from that Spec's own opening line. Multi-axis
> scanning (hygiene/security/license/currency), the never-false-green verdict lattice,
> fine-grained policy, baseline & grandfathering, the versioned `ComplianceReport` contract,
> and the fix-PR actuator are all shipped capabilities (CAP-1, CAP-4, CAP-5, CAP-6/9, CAP-7,
> CAP-12) with named stories (1.1, 1.3, 1.5, 3.1, 6.1, 6.2, 6.3, 6.4, 6.7, 6.8, 6.9). Created
> 2026-08-02 in a bulk commit later found to contain fabricated content elsewhere in the
> same commit; retired same day rather than spec'd as new work. See
> `spec-pyforge-warden-compliance-gates` for the retirement record.

# PyForge Warden — Compliance Gates

## Vision

**Warden** is a pluggable multi-axis Python dependency compliance gate — scanning manifests for security, license compliance, hygiene, and currency issues; aggregating findings; and enforcing policy with fine-grained controls (baseline, grandfathering, flag-activated gates).

**The ask**: Build a compliance engine that makes every decision verifiable, auditable, and configurable — giving operators both security confidence and operational flexibility.

## Problem

- **Compliance is multi-axis.** Security CVEs, license violations, hygiene issues (unmaintained deps, duplicates), currency (outdated versions). One tool only catches security; the operator misses license risks.
- **Violations are discovered late.** Package lands in the factory; downstream discovers the license violation. Rollback required; time lost.
- **Scanning tools conflict.** osv-scanner says "safe"; deptry flags hygiene issues; license checker complains about GPL. Operator doesn't know which to trust.
- **Policy is rigid.** Either blocks all CVEs or allows all. No nuance: "block critical; warn on medium; accept old-but-known".
- **Enforcement is scattered.** One team manually reviews security; another checks licenses. No unified gate.

## Realization

**Warden** delivers:

1. **Multi-axis Scanning** — Hygiene (deptry), Security (osv-scanner + CISA-KEV + EPSS), License, Currency (version age). One verdict aggregates all axes.

2. **Verdict Never False-Greens** — If any axis fails, verdict fails. Aggregation is pessimistic: FAIL + PASS + WARN = FAIL. No hiding behind "mostly safe."

3. **Fine-grained Policy** — Operators define: "block all CRITICAL", "warn on HIGH published ≤30 days ago", "accept numpy<=2.0 (v0 compat)". No binary on/off.

4. **Baseline & Grandfathering** — First scan establishes baseline (current state). New violations must be fixed. Old violations can be waived with expiry date.

5. **ComplianceReport Contract** — Versioned schema with all findings, verdict, policy applied, timestamp, approver. Machines can parse; humans can audit.

6. **Fix-PR Actuator** — For violations with known fixes (bump version, add license, remove duplicate), Warden auto-creates a PR. Operator reviews; bot merges if tests pass.

## Success Criteria

- ✅ **Completeness**: 4+ axes (security, license, hygiene, currency) with no false-greens
- ✅ **Accuracy**: 95%+ match with upstream tools (osv-scanner, deptry); auditable divergences documented
- ✅ **Policy**: Operators define 30+ rules; policy changes apply to in-flight scans
- ✅ **Auditability**: Every verdict includes: findings, policy applied, baseline comparison, approver
- ✅ **Speed**: Scan 1000-dep manifest <10 sec; 100-manifest fleet <5 min
- ✅ **Safety**: Zero false-greens over 1000+ audits; finding codes stable and registered

## Acceptance

Warden is done when:
1. All 4 axes (security, license, hygiene, currency) implemented and passing tests
2. Verdict never false-greens: 100+ test cases verifying aggregation logic
3. Policy system deployed: operators define 30+ rules; policy changes auto-apply
4. Baseline & grandfathering proven: baseline-set tests that old violations are waived, new ones flagged
5. Fix-PR actuator tested: auto-PRs created for 80%+ of fixable violations; 90%+ merge cleanly
6. Audit trail complete: every verdict loggable, queryable, and auditable by security team
