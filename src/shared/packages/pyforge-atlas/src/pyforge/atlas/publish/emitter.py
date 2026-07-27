"""The host-agnostic static-host emitter + its layout contract (Story G2, FR-14).

``emit_static_site(datasets, target_dir)`` writes, for each dataset, a directory of
**chunked Parquet** files plus a top-level ``manifest.json`` describing exactly what was
written (files, row counts, byte sizes, sha256 checksums, schema). The WASM runtime pulls
the chunks it needs via **HTTP Range** (footer + row groups only, never the whole file) from
whichever static host serves ``target_dir``.

Design invariants:

* **Single owner (Spine)** — the on-disk layout (``<dataset>/<dataset>-<NNNN>.parquet``) and
  the manifest schema live ONLY in this module. Consumers read :func:`load_manifest`; they
  never reconstruct paths or re-define the chunking.
* **Host-agnostic (AD-2)** — the emitter targets a filesystem PATH. Manifest chunk paths are
  RELATIVE. No host / base URL is stored or hardcoded; a consumer supplies the base at
  runtime via :func:`chunk_url` (so an enterprise mirror substitutes by config, no code
  change).
* **Deterministic (AD-21)** — datasets and chunks are emitted in sorted, stable order; the
  Parquet bytes are reproducible for a fixed engine, so the recorded sha256 checksums are
  reproducible and ``manifest.json`` is byte-stable across two emits of the same input. No
  wall-clock timestamp is written into the manifest.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# The layout contract — DEFINED ONCE HERE (single owner, Spine convention).
# ---------------------------------------------------------------------------

#: Bump when the on-disk layout / manifest schema changes incompatibly.
LAYOUT_VERSION = 1

#: The manifest file name at the root of the emitted static site.
MANIFEST_NAME = "manifest.json"

#: Default rows per Parquet chunk file. Large so most datasets emit a single chunk; the
#: emitter still splits bigger datasets so a consumer can Range-read one chunk at a time.
DEFAULT_ROWS_PER_CHUNK = 250_000

#: Default Parquet row-group size WITHIN a chunk. Smaller row groups let an HTTP-Range
#: consumer fetch just the row groups a query touches (finer-grained Range reads).
DEFAULT_ROW_GROUP_SIZE = 100_000

_CHUNK_STEM = "{name}-{index:04d}.parquet"

# A dataset name becomes a directory under target_dir AND is rmtree'd on re-emit, so it must be a
# single, safe path segment — never a traversal (``..``), a separator (``/`` or os.sep, which
# would nest or escape), or a leading-slash/absolute (which would ignore target_dir). Reject
# anything else BEFORE any filesystem mutation (Reviewer-B path-traversal MUST-FIX).
_SAFE_NAME_RE = re.compile(r"^[^/\\]+\Z")



def _require_safe_name(name: str) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError(f"dataset name must be a non-empty string, got {name!r}")
    if len(name.encode("utf-8")) > 255:
        # An over-long name passes the char checks but fails at mkdir() mid-loop, leaving the
        # site half-rewritten against a stale manifest — reject it UP FRONT so the atomicity
        # property (validate-all-before-any-mutation) holds for it too (independent-review LOW).
        raise ValueError(f"dataset name too long ({len(name.encode())} bytes > 255): {name[:40]!r}…")
    if name in (".", "..") or ".." in name or not _SAFE_NAME_RE.match(name):
        raise ValueError(
            f"unsafe dataset name {name!r}: must be a single path segment with no '/', '\\', "
            "'..', or separators (it becomes a directory under target_dir and is deleted on "
            "re-emit — a traversal could delete a directory outside target_dir)"
        )


class ManifestChecksumError(RuntimeError):
    """A chunk on disk does not match the sha256 / byte size recorded in the manifest — a
    corrupt or truncated artifact. Raised by :func:`verify_manifest` (never silently ignored:
    a Range consumer that reads a corrupt chunk must fail loudly, not return a wrong answer)."""


def _sha256_and_size(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def _schema_of(table: pa.Table) -> list[list[str]]:
    """Ordered ``[[column, arrow_type], ...]`` — the authoritative schema of the WRITTEN
    Parquet (from pyarrow, not the pandas dtypes, so it matches what a reader sees)."""
    return [[field.name, str(field.type)] for field in table.schema]


def _write_chunk(df: pd.DataFrame, path: Path, row_group_size: int) -> pa.Table:
    """Write one chunk deterministically (no pandas index, stable row order) and return the
    pyarrow table (used to record the authoritative schema)."""
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, row_group_size=max(1, row_group_size))
    return table


def emit_static_site(
    datasets: Mapping[str, pd.DataFrame],
    target_dir: str | Path,
    *,
    rows_per_chunk: int = DEFAULT_ROWS_PER_CHUNK,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
) -> dict[str, Any]:
    """Emit the chunked-Parquet + ``manifest.json`` layout for ``datasets`` into ``target_dir``.

    ``target_dir`` is treated as "the static host filesystem": it is created (and any existing
    per-dataset directories for the emitted names are replaced) and, on return, can be served
    verbatim by any static host. The return value is the manifest dict (also written to
    ``target_dir/manifest.json``).

    ``datasets`` maps ``dataset_name -> DataFrame``. Names are emitted in sorted order; an empty
    DataFrame emits a single schema-only chunk (row_count 0) so the layout stays uniform.
    """
    if datasets is None:
        raise TypeError("datasets must be a Mapping of name -> DataFrame, got None")
    if target_dir is None:
        raise TypeError("target_dir must be a str or Path, got None")
    if rows_per_chunk < 1:
        raise ValueError(f"rows_per_chunk must be >= 1, got {rows_per_chunk}")
    root = Path(target_dir)

    # VALIDATE EVERYTHING UP FRONT — before ANY filesystem mutation (Reviewer-B). Two reasons:
    #  1. Data-loss/traversal (MUST-FIX): a dataset NAME is joined onto target_dir and its dir is
    #     rmtree'd — an unsanitized "../x" / "a/b" / leading-slash name would delete a dir OUTSIDE
    #     target_dir. `_require_safe_name` rejects any traversal/separator BEFORE the rmtree.
    #  2. Atomicity: a bad TYPE (or name) on a LATER dataset must not leave the site half-rewritten
    #     against a stale manifest — so every name + value is checked before the first rmtree/write.
    for name in sorted(datasets):
        _require_safe_name(name)
        df = datasets[name]
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"dataset {name!r} must be a pandas DataFrame, got {type(df).__name__}")

    root.mkdir(parents=True, exist_ok=True)
    manifest_datasets: dict[str, Any] = {}
    for name in sorted(datasets):
        df = datasets[name]
        ds_dir = root / name
        if ds_dir.exists():
            shutil.rmtree(ds_dir)
        ds_dir.mkdir(parents=True)

        n_rows = len(df)
        n_chunks = max(1, math.ceil(n_rows / rows_per_chunk))  # empty -> 1 schema-only chunk

        chunks: list[dict[str, Any]] = []
        schema: list[list[str]] | None = None
        for i in range(n_chunks):
            start = i * rows_per_chunk
            chunk_df = df.iloc[start : start + rows_per_chunk]
            rel = f"{name}/{_CHUNK_STEM.format(name=name, index=i)}"
            table = _write_chunk(chunk_df, root / rel, row_group_size)
            if schema is None:
                schema = _schema_of(table)
            sha, size = _sha256_and_size(root / rel)
            chunks.append(
                {"path": rel, "rows": len(chunk_df), "bytes": size, "sha256": sha}
            )

        manifest_datasets[name] = {
            "row_count": n_rows,
            "schema": schema if schema is not None else [],
            "chunks": chunks,
        }

    manifest: dict[str, Any] = {
        "layout_version": LAYOUT_VERSION,
        "chunking": {"rows_per_chunk": rows_per_chunk, "row_group_size": row_group_size},
        "datasets": manifest_datasets,
    }
    # sort_keys + trailing newline => byte-stable manifest across two identical emits.
    (root / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def load_manifest(target_dir: str | Path) -> dict[str, Any]:
    """Read the authoritative layout manifest from ``target_dir`` (the single-owner contract a
    consumer reads to discover chunks — it never reconstructs paths itself)."""
    return json.loads((Path(target_dir) / MANIFEST_NAME).read_text(encoding="utf-8"))


def verify_manifest(target_dir: str | Path) -> dict[str, Any]:
    """Recompute every chunk's sha256 + byte size and assert it matches the manifest.

    Returns the manifest on success; raises :class:`ManifestChecksumError` on the first
    missing / mismatched chunk (a truncated or corrupt artifact must fail loudly).

    AUD-ATLAS-019: each ``chunk["path"]`` must resolve under ``target_dir`` — a
    traversal in a hand-edited/corrupt manifest must not follow files outside the site.
    """
    root = Path(target_dir).resolve()
    manifest = load_manifest(root)
    for name, ds in manifest["datasets"].items():
        for chunk in ds["chunks"]:
            rel = chunk["path"]
            if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
                raise ManifestChecksumError(
                    f"{name}: unsafe chunk path {rel!r} (must be a relative path under the site root)"
                )
            path = (root / rel).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ManifestChecksumError(
                    f"{name}: chunk path {rel!r} escapes site root {root}"
                ) from exc
            if not path.exists():
                raise ManifestChecksumError(f"{name}: missing chunk {rel}")
            sha, size = _sha256_and_size(path)
            if size != chunk["bytes"] or sha != chunk["sha256"]:
                raise ManifestChecksumError(
                    f"{name}: chunk {rel} does not match manifest "
                    f"(recorded bytes={chunk['bytes']} sha256={chunk['sha256'][:12]}…, "
                    f"actual bytes={size} sha256={sha[:12]}…)"
                )
    return manifest


def chunk_url(base_url: str, chunk_path: str) -> str:
    """Compose the runtime URL for a manifest chunk path under a runtime ``base_url``.

    The host-agnostic seam (AD-2): the emitter stores only RELATIVE chunk paths; the base
    (``https://<user>.github.io/<repo>`` for the public path, an enterprise mirror otherwise)
    is supplied HERE at consume time. Trailing/leading slashes are normalized so a mirror base
    with or without a trailing ``/`` composes identically. An empty base yields the relative
    path unchanged (same-origin static host)."""
    if chunk_path is None:
        raise TypeError("chunk_path must be a string, got None")
    if base_url is None:
        raise TypeError("base_url must be a string, got None")
    path = chunk_path.lstrip("/")
    if base_url == "":
        return path
    return f"{base_url.rstrip('/')}/{path}"
