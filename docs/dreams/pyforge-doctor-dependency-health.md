---
title: "Dream — PyForge Doctor: Dependency Health Diagnostics"
date: 2026-08-02
status: dreamt
owner: doctor
scope: "Dependency health, version tracking, obsolescence detection, remediation"
---

# PyForge Doctor — Dependency Health Diagnostics

## Vision

**Doctor** diagnoses Python and Conda dependency health — tracking versions, detecting obsolescence, monitoring adoption signals, and providing actionable remediation. It's the health monitor for every package in the factory's dependency tree.

**The ask**: Build a compliance and health diagnostics engine that makes stale, unsafe, or abandoned dependencies visible and actionable across the entire factory.

## Problem

- **Stale dependencies hide.** A package pins `numpy<1.20` from 2020. Is it intentional? Forgotten? Incompatible? No signal.
- **Obsolescence is silent.** Upstream unmaintained for 3+ years. No release in 24 months. Community moved on. The operator still doesn't know.
- **Version hell is manual.** Operators grep logs, check PyPI manually, guess when to update. No automated discovery.
- **Remediation is reactive.** Security CVE drops; factories scramble. No proactive health scoring or priority ranking.

## Realization

**Doctor** delivers:

1. **Health Scoring** — Multi-axis scoring (age, velocity, maintenance signal, adoption, community size) producing a single health grade (A–F). Operators know instantly: is this package healthy?

2. **Obsolescence Detection** — Detects packages unmaintained >N months, replaced by newer libraries, archived on GitHub, or deprecated upstream. Flags them for review.

3. **Version Intelligence** — Tracks all available versions, release cadence, breaking changes, and security patches. Recommends safe upgrade paths.

4. **Adoption Tracking** — Monitors PyPI download trends, conda adoption by # of feedstocks using it, GitHub stars, and ecosystem maturity signals.

5. **Actionable Remediation** — For each unhealthy package, suggests: "Update to X.Y.Z (safe)", "Replace with Z (recommended)", or "Pin and monitor (acceptable risk)".

6. **Fleet-wide Health Dashboard** — Operators see at a glance: how many deps are healthy, stale, or in critical condition. Sortable by risk, age, velocity.

## Success Criteria

- ✅ **Coverage**: Every dependency in the factory (Python + Conda) gets a health grade
- ✅ **Accuracy**: Health scores validated against real-world data (3+ months of trending)
- ✅ **Speed**: Health diagnosis <1 sec per dependency; fleet scan <5 min
- ✅ **Remediation**: Every unhealthy package has a suggested action (update, replace, or accept-risk)
- ✅ **Integration**: Works with Warden (compliance layer) to enforce health thresholds
- ✅ **Observability**: Every diagnosis logged, every recommendation attributed, every action auditable

## Acceptance

Doctor is done when:
1. Health scoring algorithm validated against 1000+ real packages
2. Obsolescence detection catches 95%+ of truly abandoned packages
3. Fleet-wide health dashboard deployed and tracking real factory data
4. Remediation recommendations accepted by operators in 80%+ of cases
5. Integration with Warden compliance gates proven in CI
