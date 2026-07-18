"""New-raw-file detection for the wiki compile sensor — dagster-free (Story H4, FR-22(d)/FR-6).

The Wave-H factory layer runs its crews on the SAME Dagster plane as the data pipeline (AD-6/AD-23,
one execution plane): a **sensor** fires the compile crew when a new raw doc lands in ``wiki/raw/``,
and a **schedule** fires the lint crew weekly (§ 7.2). This module holds the sensor's DECISION
logic — scanning the raw stage and deduping against the Dagster cursor — with ZERO dagster imports,
so AD-1's "only ``orchestration/definitions.py`` imports dagster" rule holds (mirrors
``orchestration/event_source.py`` for G3's upstream sensors).

The cursor stores the SET of raw doc names already seen (JSON-encoded, sorted). A tick that finds
names not in that set is a NEW-file event → run the compile crew; a tick with no new names skips.
Dedup is by name-set, not by seq, because raw docs are addressed by name (a re-appearing name is not
re-compiled unless its content changed — that TTL/idempotency is the crew's concern, AD-13).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


def scan_raw_docs(raw_dir: str | Path) -> tuple[str, ...]:
    """Return the sorted relative names of every ``*.md`` under ``raw_dir`` (empty if the dir does
    not exist — the offline default when no wiki is provisioned). Pure filesystem read, no dagster."""
    root = Path(raw_dir)
    if not root.is_dir():
        return ()
    return tuple(sorted(str(p.relative_to(root)) for p in root.rglob("*.md")))


@dataclass(frozen=True)
class WikiScanDecision:
    """The compile sensor's decision for one tick — mirrors G3's ``SensorDecision``."""

    run: bool
    new_docs: tuple[str, ...]
    new_cursor: str
    run_key: str | None = None
    skip_reason: str | None = None


def _decode_cursor(cursor: str | None) -> set[str]:
    if not cursor:
        return set()
    try:
        seen = json.loads(cursor)
    except (ValueError, TypeError):
        # A malformed cursor degrades to "nothing seen" — the worst case is one extra compile
        # (idempotent: the crew re-compiles the same content to the same bytes), never a crash.
        return set()
    return set(seen) if isinstance(seen, list) else set()


def evaluate_raw_scan(
    current: Sequence[str],
    cursor: str | None,
    *,
    run_key_prefix: str = "wiki_compile",
) -> WikiScanDecision:
    """Decide whether the compile crew should run given the ``current`` raw doc names and the
    Dagster ``cursor`` (the previously-seen name set).

    New names (present now, absent from the cursor) ⇒ ``run=True`` with a deterministic ``run_key``
    (a digest of the new seen-set, so the SAME new set never fires two runs — Dagster idempotency)
    and an advanced cursor. No new names ⇒ ``run=False`` with the cursor left exactly as-is.
    """
    seen = _decode_cursor(cursor)
    current_sorted = sorted(set(current))
    new_docs = tuple(d for d in current_sorted if d not in seen)
    if not new_docs:
        # Nothing new — do NOT advance the cursor (a removed file must not silently re-arm).
        return WikiScanDecision(
            run=False,
            new_docs=(),
            new_cursor=cursor if cursor is not None else json.dumps(current_sorted),
            skip_reason=f"no new raw docs ({len(current_sorted)} seen)",
        )
    new_cursor = json.dumps(current_sorted)
    digest = hashlib.sha256(new_cursor.encode("utf-8")).hexdigest()[:12]
    return WikiScanDecision(
        run=True,
        new_docs=new_docs,
        new_cursor=new_cursor,
        run_key=f"{run_key_prefix}:{digest}",
    )
