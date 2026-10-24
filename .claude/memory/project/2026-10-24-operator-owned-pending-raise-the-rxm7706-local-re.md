---
name: "2026-10-24-operator-owned-pending-raise-the-rxm7706-local-re"
description: "2026-10-24 operator-owned, pending: raise the rxm7706/local-recipes Actions cache size limit (repository Settings, Acti…"
metadata:
  type: project
---

2026-10-24 operator-owned, pending: raise the rxm7706/local-recipes Actions cache size limit (repository Settings, Actions, cache storage). Operator ruling 2026-10-24 for atlas Story 37.12 (option C, 'Cache + raise limit'): the kedro-viz-publish vizro job keeps the public stores' last-good copies (data/raw, data/stores/* except stores/vdb) in actions/cache under key pyforge-atlas-last-good-<run_id>, and the operator raises the limit themself; a session never changes that setting. Until then the cache is over 10 GB (10,450,545,115 bytes on 2026-10-24) and LRU eviction drops an entry unread for about 3.5 hours, so the copies never reach the weekly run. Close it by raising the limit, then confirming a weekly vizro run logs 'Cache restored from key: pyforge-atlas-last-good-'. Tracked as DW-atlas-37-12-1 in the atlas deferred-work ledger.
