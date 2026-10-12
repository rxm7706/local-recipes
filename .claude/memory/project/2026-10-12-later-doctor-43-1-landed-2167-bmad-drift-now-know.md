---
name: "2026-10-12-later-doctor-43-1-landed-2167-bmad-drift-now-know"
description: "2026-10-12 (later): doctor 43.1 landed (#2167) - bmad-drift now knows every Tier-3 kind marshal dispatch writes (TIER3_…"
metadata:
  type: project
---

2026-10-12 (later): doctor 43.1 landed (#2167) - bmad-drift now knows every Tier-3 kind marshal dispatch writes (TIER3_RUN_ARTIFACTS; the failed-attempt changes.patch and fleet-drain-runs/campaign.lock are kept classes, each row citing its real writer). Fleet excluding the cutover: 1391/1396 stories done; the 5 left are all operator- or upstream-gated (atlas 24.2 Artifactory access, marshal 33.11 second-principal gate, mason 22.3/22.4 upstream rattler-build, steward 87.2 retired but its key still reads blocked). PR #2166 belongs to another session and is left to it per the operator. Operator-owned next: create the gitignored .warden/fleet-target.toml with leak_guard_terms (the guard refuses empty terms), then start the live warden runs (16.1/16.5 AC10) under the operator's own gh login.
