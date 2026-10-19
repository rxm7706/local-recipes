---
name: "2026-10-19-operator-rulings-atlas-vizro-boards-spec-pyforge"
description: "2026-10-19 operator rulings, atlas Vizro boards (spec-pyforge-atlas CAP-63 amended, CAP-69; Epic 37): 'Data-first + 10…"
metadata:
  type: project
---

2026-10-19 operator rulings, atlas Vizro boards (spec-pyforge-atlas CAP-63 amended, CAP-69; Epic 37): 'Data-first + 10 rewires' -- the Pages vizro job builds public atlas data before exporting, the dashboard reads Kedro's data root, 10 boards are rewired to the datasets the pipelines write, and the 6 boards no pipeline feeds (cve-watcher history, release cadence, find-alternative, export-purls, mapping-gap, bootstrap-index-health) are backlog Stories 37.5-37.10 with DW rows; 'Public-only Pages' -- CI runs public sources only, identity boards stay honest-empty on Pages; 'Weekly + on push' -- a weekly schedule plus push and dispatch.
