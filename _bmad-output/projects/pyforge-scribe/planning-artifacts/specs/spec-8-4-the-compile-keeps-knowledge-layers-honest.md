---
title: 'The compile keeps knowledge layers honest'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Fix compile-time stale false positives (mtime vs git), bound retro/memlog/changelog walks, and add named contract surfaces (active Dreams, ready SPECs, fact ledgers).

## Boundaries & Constraints

**Always:** stale iff latest source commit author date > this compile's `compiled_at`. Retros only under `planning-artifacts/retros/`.

**Never:** `*retro*` filename glob; `archive/`; `implementation-artifacts/`; `tests/`; wholesale `docs/`.

</intent-contract>
