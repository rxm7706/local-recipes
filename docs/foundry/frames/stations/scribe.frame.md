---
type: frame [0.3]
identifier: pyforge-scribe
license: https://www.apache.org/licenses/LICENSE-2.0
name: pyforge-scribe
description: Station Frame for Scribe — team memory, compiled graph, and cited recall. Load when capturing decisions or answering from grounded sources.
visibility: private
owner: scribe
version: 0.1.0
scope: station
inherits: pyforge
---

# Scribe

- Grammar: `scribe` / `pyforge scribe …`. Do not import `pyforge.scribe` internals.
- Recall never invents an uncited answer. Default recall omits `kind=code`.
- Frame files under `docs/foundry/frames/` are the git store; do not graph-ingest Frames unless a later Spec says so.
- `--promote` / `--transcripts` are exclusive with `--type` / `--text`.
