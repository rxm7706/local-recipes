---
name: "2026-10-23-operator-ruling-atlas-story-37-6-spec-pyforge-atl"
description: "2026-10-23 operator ruling (atlas Story 37.6, spec-pyforge-atlas CAP-69, release-cadence): per-version upload times com…"
metadata:
  type: project
---

2026-10-23 operator ruling (atlas Story 37.6, spec-pyforge-atlas CAP-69, release-cadence): per-version upload times come from the full repodata.json.zst per subdir, not the anaconda.org files fan-out; a version's upload time is its earliest file timestamp across subdirs (legacy upload_unix). Public fetch behind pyforge.atlas.live_public_sources, cached per subdir with ETag + AD-13 last-good, streamed (stdlib compression.zstd + incremental JSON).
