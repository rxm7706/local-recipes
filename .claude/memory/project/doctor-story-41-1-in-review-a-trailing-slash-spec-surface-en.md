---
name: "doctor-story-41-1-in-review-a-trailing-slash-spec-surface-en"
description: "doctor Story 41.1 (in-review): a trailing-slash spec-surface entry now governs its directory subtree in BOTH matchers (…"
metadata:
  type: project
---

doctor Story 41.1 (in-review): a trailing-slash spec-surface entry now governs its directory subtree in BOTH matchers (chain.py::_glob_to_re and scripts/spec_surface_check.py::glob_to_re). That grew spec-pyforge-marshal's governed set by 65 paths and spec-pyforge-steward's by 40; both were reconciled on their own .memlog.md and scoped-stamped. Landing note for any branch behind main: detectors-ci's one remaining FAIL is ledger-direction on pyforge-steward/84-4 (done on origin/main, backlog on a stale branch) -- branch staleness in a foreign station's generated ledger, cleared by merging origin/main, never by hand-editing sprint-status-ledger.yaml.
