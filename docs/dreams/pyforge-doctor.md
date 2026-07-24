---
title: Doctor — one bedside manner for the whole fleet
type: dream
owner: doctor
status: in-deck
---

# Doctor — check the vitals, keep the ecosystem alive

## The Dream

The Physician's dream: **a factory is only as autonomous as its health checks.**
Before any run, verify the machinery is sound — a missing engine or broken
config fails fast, never mid-build. After anything ships, keep a finger on the
fleet's pulse: staleness, new advisories, upstream abandonment — surfaced as
signals, not surprises. And never stop at a finding: every diagnosis names its
root cause and ships an **ordered prescription** — what to patch, upgrade, or
retire, in what order.

## What it looks like when real

- `doctor check --env --engines` — pre-flight before Marshal spins the factory.
- `doctor monitor --fleet --watch staleness,cve,abandonment` — the continuous pulse.
- `doctor diagnose --target … --prescribe` — root cause + remediation worklist.

## Why this is a consolidation, not an invention

The instruments already beat inside the factory — Doctor is one bedside manner
over all of them:

- **atlas · health**: `feedstock-health`, `staleness-report`, `behind-upstream`.
- **atlas · watch**: `cve-watcher`, `release-cadence`, adoption signals.
- **warden · self-check**: the engine-availability doctor check
  ([[pyforge-warden]] first-contact story).
- Candidate additions: credential/privilege hygiene (the known `JFROG_API_KEY`
  unconditional-injection issue in `_http.py` is exactly a Doctor finding —
  see [[enterprise-airgap]]).

## Realization log

- **2026-07-23** — persona defined in [[ecosystem-crew]]; chapter deck seeded
  (`presentations/pyforge-doctor/`). CLI awaits its `bmad-spec` run — the ideal
  small consolidative candidate.
- **2026-07-23 (gist audit)** — grounding: the fleet health reports (v2 kept in the gist snapshot) are Doctor-shaped output — the monitor's voice before the persona had a name.
