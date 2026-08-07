"""pyforge.scribe.graph_store — the `GraphStore` port + flat-file v1 adapter
(Story 2.1, AD-5/AD-6).

`GraphStore` is a `typing.Protocol`: the ONLY seam `compile.py` (write) and
`recall.py` (read) are allowed to depend on. No module outside this file may
import a specific graph-database engine's client library directly (AD-5) --
the KuzuDB-archival lesson the domain research flagged (an embedded-graph
engine can itself go unmaintained). `FlatFileGraphStore` is the v1 concrete
adapter the architecture's Deferred note resolves to: one JSON index file,
extending `.claude/memory/MEMORY.md`'s existing flat-index pattern rather
than pulling in an embedded graph-database dependency before it's justified.

Nodes ARE the facts here (there is no separate edge object in a flat-file
engine) -- `invalidate_edge()`'s name deliberately mirrors the architecture's
own AD-5 vocabulary ("an invalidate-edge-shaped call for supersession") so a
future embedded-graph adapter swap has an unambiguous semantic target: it
marks a node's bi-temporal validity as ended (AD-4), it does not delete
anything.

Write path is a full in-memory rebuild + one atomic `commit()`: `reset()`
clears in-memory state, `upsert_node()`/`invalidate_edge()` mutate it, and
`commit()` performs one temp-file-then-`os.replace()` whole-file rewrite
under a cross-platform advisory lock (mirrors `capture.py`'s `_locked()` --
`fcntl` on POSIX, `msvcrt` on Windows, stdlib only). A reader never observes
a half-written file; two racing `commit()` calls resolve to one clean
last-writer-wins atomic swap, never a corrupted file. `commit()`'s JSON
output is deterministic (sorted keys, sorted node ids, fixed indent) so
`compile.py` re-running against unchanged sources produces byte-identical
output (Story 2.2's idempotency requirement).

Zero network calls anywhere in this module (AD-6) -- pure `json` + stdlib
file/lock primitives. See `tests/unit/test_graph_store.py`'s dedicated
offline-conformance test for the empirical proof.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, Protocol

from pyforge.scribe.models import GraphNode

_LOCK_TIMEOUT_S = 10.0


class GraphStore(Protocol):
    """Storage-engine-agnostic seam (AD-5).

    Write: `upsert_node` (idempotent insert-or-replace by `node.id`),
    `invalidate_edge` (mark a prior node's validity as ended -- supersession,
    never deletion, AD-4). Read: `query_by_citation` (resolve a citation path
    back to its node(s)), `iter_nodes` (full scan, e.g. for `recall.py`'s
    lexical matching). `reset`/`commit` bound one compile run's write
    transaction.
    """

    def reset(self) -> None: ...

    def upsert_node(self, node: GraphNode) -> None: ...

    def invalidate_edge(self, node_id: str, *, ended_at: datetime, superseded_by: str) -> None: ...

    def query_by_citation(self, citation: str) -> list[GraphNode]: ...

    def iter_nodes(self) -> Iterator[GraphNode]: ...

    def commit(self) -> None: ...


class FlatFileGraphStore:
    """Concrete `GraphStore` adapter: one JSON file, `{"nodes": {id: {...}}}`.

    `store_path` is always an injected `Path`, never a hardcoded location
    (matches `capture.py`'s `memory_root`-injection convention) -- this
    module has no notion of "the repo" or a default location; `compile.py`
    owns that choice.
    """

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self._nodes: dict[str, GraphNode] = {}
        self._load()

    def _load(self) -> None:
        if not self.store_path.is_file():
            return
        raw = self.store_path.read_text(encoding="utf-8")
        if not raw.strip():
            return
        document = json.loads(raw)
        self._nodes = {
            node_id: GraphNode.model_validate(payload)
            for node_id, payload in document.get("nodes", {}).items()
        }

    def reset(self) -> None:
        """Clear in-memory state -- `compile.py` calls this before a full
        rebuild (AD-1: the graph is always 100% re-derived from source, never
        hand-edited or incrementally patched)."""
        self._nodes = {}

    def upsert_node(self, node: GraphNode) -> None:
        """Insert-or-replace by `node.id` -- idempotent: upserting the same
        id twice with identical content leaves the in-memory state (and thus
        the next `commit()`'s output) unchanged."""
        self._nodes[node.id] = node

    def invalidate_edge(self, node_id: str, *, ended_at: datetime, superseded_by: str) -> None:
        """Mark `node_id`'s validity as ended (AD-4 supersession) -- the node
        stays present, never deleted. Raises `ValueError` if `node_id` has
        not been `upsert_node()`-ed in this session (the caller's bug, not a
        silently-ignored no-op)."""
        existing = self._nodes.get(node_id)
        if existing is None:
            raise ValueError(f"cannot invalidate unknown node id {node_id!r} -- upsert it first")
        self._nodes[node_id] = existing.model_copy(
            update={"valid_until": ended_at, "superseded_by": superseded_by}
        )

    def query_by_citation(self, citation: str) -> list[GraphNode]:
        return [node for node in self._nodes.values() if node.citation == citation]

    def iter_nodes(self) -> Iterator[GraphNode]:
        """Deterministic order (sorted by id) -- callers that rank/tie-break
        on this iteration order (`recall.py`) get identical results across
        runs and operators (FR-13)."""
        return iter(sorted(self._nodes.values(), key=lambda n: n.id))

    def commit(self) -> None:
        """Atomically persist the full in-memory node set.

        A whole-file rewrite (temp file + `os.replace()`), never an in-place
        patch -- a reader never observes a half-written file, and two racing
        `commit()` calls resolve to one clean last-writer-wins swap instead
        of a corrupted file. The temp file is created and cleaned up on any
        exception (a crashed writer never leaves a stray `.tmp` sibling for a
        later `commit()` to trip over).
        """
        document = {
            "nodes": {
                node_id: json.loads(node.model_dump_json())
                for node_id, node in sorted(self._nodes.items())
            }
        }
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with _locked(self.store_path):
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self.store_path.parent), prefix=".graph-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(document, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                os.replace(tmp_name, self.store_path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
                raise


@contextlib.contextmanager
def _locked(store_path: Path):
    """Serialize concurrent `commit()` calls against the same `store_path` --
    mirrors `capture.py`'s `_locked()` exactly (same lock-file-in-temp-dir,
    same fcntl/msvcrt split, same timeout), keyed by `store_path`'s resolved
    path so two different graph stores never contend on the same lock file.
    """
    root_key = hashlib.sha256(str(store_path.resolve()).encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"pyforge-scribe-graph-{root_key}.lock"
    lock_file = open(lock_path, "a+")
    deadline = time.monotonic() + _LOCK_TIMEOUT_S
    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                try:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"timed out waiting for graph-store lock: {lock_path}") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"timed out waiting for graph-store lock: {lock_path}") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()
