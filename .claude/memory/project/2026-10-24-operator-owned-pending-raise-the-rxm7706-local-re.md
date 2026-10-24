---
name: "2026-10-24-operator-owned-pending-raise-the-rxm7706-local-re"
description: "2026-10-24 operator-owned, pending: raise the rxm7706/local-recipes Actions cache size limit (repository Settings, Acti…"
metadata:
  type: project
---

2026-10-24 operator-owned, pending: raise the rxm7706/local-recipes Actions cache size limit (repository Settings, Actions, cache storage). Operator ruling 2026-10-24 for atlas Story 37.12 (option C, 'Cache + raise limit'): the kedro-viz-publish vizro job keeps the public stores' last-good copies (data/raw, data/stores/* except stores/vdb, and the vulnerability snapshot history) in actions/cache under key pyforge-atlas-last-good-<run_id>-<run_attempt>, and the operator raises the limit themself; a session never changes that setting. Until then the cache is over 10 GB (10,450,545,115 bytes on 2026-10-24) and LRU eviction drops entries unread for a few hours (how long depends on how much the other workflows write; that day an entry about 4 hours unread was still present, a lower bound rather than a measured eviction time), so the copies never reach the weekly run. Close it by raising the limit, then confirming a weekly vizro run logs 'Cache restored from key: pyforge-atlas-last-good-'. Tracked as DW-atlas-37-12-1 in the atlas deferred-work ledger.
