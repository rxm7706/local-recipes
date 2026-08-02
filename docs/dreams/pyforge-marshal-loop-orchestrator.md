---
title: "Dream — PyForge Marshal: Loop Orchestrator"
date: 2026-08-02
status: dreamt
owner: marshal
scope: "Loop provisioning, deterministic execution, supervised runs, durable landing"
---

# PyForge Marshal — Loop Orchestrator

## Vision

**Marshal** is the loop orchestrator — the deterministic, offline-by-default execution engine for unattended factory runs. It provisions isolated loop homes, supervises long-running jobs, enforces gates, and lands results durably.

**The ask**: Build an orchestrator that enables hands-off, auditable, deterministic execution of complex multi-story workflows with zero silent failures and full recovery from crashes.

## Problem

- **Runs are fragile.** A long story crashes at hour 3; the operator rediscovers it manually. Did it checkpoint? Can it resume? No one knows.
- **Isolation is weak.** Two loops on the same machine can interfere. Shared temp dirs, port collisions, credential leakage.
- **Deadlines are hopeless.** No budget ceiling. One runaway task starves the rest. Operator kills everything manually.
- **Evidence disappears.** A run completes; the operator restarts the machine. The journal, the findings, the story specs are all gone.
- **Landing is error-prone.** Merge subjects don't conform. Specs aren't promoted. Feeds are stale. Manual cleanup needed.

## Realization

**Marshal** delivers:

1. **Provisioned Loop Homes** — Each loop gets an isolated, policy-composed, preflight-verified place to run. Two homes can't interfere; isolation is provable.

2. **Deterministic Execution** — No timestamps in logic paths, no random seeds, no "good enough" approximations. Same story → same output, always. Operators trust the results.

3. **Supervised Runs** — A supervisor sidecar watches every detached run: sends heartbeats, detects idle strands, enforces token budgets, escalates failures. No silent hangs.

4. **Durable Durability** — Tier-3 store via backlink survives machine restart. Every story spec promoted to git automatically. Run journal append-only and indexed. Zero data loss.

5. **Deterministic Gates** — Independent gate evaluation: standalone CLI, project-scoped, no LLM influence. Verdict never false-greens. Evidence records what ran and why.

6. **Batch Landing** — Stories land in waves: automatic spec promotion, merge-subject conformance checked, feeds refreshed, branch cleanup triggered. One command; full auditability.

## Success Criteria

- ✅ **Isolation**: Two loop homes provably isolated (no process leakage, no credential sharing)
- ✅ **Determinism**: Same story → byte-identical output; determinism verified in CI
- ✅ **Uptime**: Supervised runs survive machine restarts; zero data loss
- ✅ **Reliability**: 0 false-green verdicts over 100+ gate evaluations
- ✅ **Velocity**: Full 50-story run completes in <13 weeks single-builder; >80% parallelizable
- ✅ **Auditability**: Every decision logged, every finding code registered, every action attributed

## Acceptance

Marshal is done when:
1. All 6 epics (50 stories) implemented and passing tests
2. Isolated loop homes verified with two concurrent runs on same machine
3. Determinism proven: same story → identical output over 50+ reruns
4. Supervised runs survive 10+ crash-and-recover cycles with zero data loss
5. Batch landing tested: 20-story wave lands cleanly with all specs promoted
6. Integration with Warden gates verified: verdicts never false-green
