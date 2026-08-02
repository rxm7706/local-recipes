---
title: "Dream — PyForge Warden: Compliance Gates"
date: 2026-08-02
status: dreamt
owner: warden
scope: "Compliance gates, dependency scanning, policy enforcement, findings aggregation"
---

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
