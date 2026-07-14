"""Deterministic offline OSV database builder (Story 1.4 spike substrate).

``build_offline_db`` assembles the exact on-disk layout osv-scanner 2.4.0
consumes in ``--offline`` mode from a directory of readable OSV JSON records:

    <cache_root>/osv-scanner/<Ecosystem>/all.zip

(empirically confirmed against osv-scanner 2.4.0 / osv-scalibr 0.4.5 by
reproducing the tree its own ``--download-offline-databases`` writes, and by
matching a seeded advisory offline — see
``planning-artifacts/osv-db-offline-provisioning-decision.md`` § 11).

The build is **deterministic and portable**: every zip entry is **stored
uncompressed** (``ZIP_STORED``) with a fixed DOS-epoch timestamp
(``1980-01-01``) and fixed permission/attribute bits, entries emitted in sorted
order. No ``datetime.now()`` and no DEFLATE — so the bytes never depend on the
host's zlib build and two builds over the same records produce a
**byte-identical** ``all.zip`` on any machine (the fixture is tiny; compression
buys nothing and would forfeit cross-zlib reproducibility). This is the
hermetic vulnerability-data substrate Story 1.5 / 2.5 / CI reuse; it is
intentionally side-effect free apart from writing ``all.zip`` under
``cache_root``.

The builder is **fail-loud**: an empty ``records_dir``, a malformed record, a
record missing/with a non-string ``id``, an ``id`` that is not a safe bare
filename, or a record none of whose ``affected`` entries target the requested
``ecosystem`` all raise ``ValueError`` rather than silently producing an empty
or mis-shelved DB (an empty ``all.zip`` would make osv-scanner report a clean
scan — the exact false-green this whole project exists to prevent).

This module is a *test fixture helper*, importable by tests; it imports no
production ``python_deptry_osv_scanner`` code and does no network I/O.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

# The DOS/zip timestamp epoch — the earliest value a ZIP entry can carry, so
# the substrate is reproducible and never leaks a wall-clock time.
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
# 0o644 (rw-r--r--) in the high 16 bits, as a regular file, so the attribute
# bytes are stable across machines.
_FIXED_EXTERNAL_ATTR = 0o644 << 16
# Store uncompressed: DEFLATE output is a function of the host zlib build and
# is NOT guaranteed byte-identical across zlib versions / CI platforms; for a
# tiny fixture DB, ZIP_STORED is truly portable-deterministic at no cost.
_COMPRESSION = zipfile.ZIP_STORED


def _entry_for_record(raw: bytes, record_path: Path, ecosystem: str) -> str:
    """Validate one OSV record's bytes and return its ``<id>.json`` entry name,
    failing loud on anything that would corrupt or silently hollow the DB."""
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OSV record {record_path} is not valid JSON: {exc}") from exc

    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError(
            f"OSV record {record_path} has a missing or non-string 'id' "
            f"(got {record_id!r})"
        )
    # The zip entry must be a flat ``<id>.json`` — reject any id that would
    # escape the archive root or nest (path traversal / unexpected layout).
    if record_id != Path(record_id).name or record_id in (".", ".."):
        raise ValueError(f"unsafe OSV record id {record_id!r} in {record_path}")

    # A record whose affected packages never target this ecosystem would be
    # shelved into <ecosystem>/all.zip yet never match a scan of that
    # ecosystem — a silent coverage hole. Guard it.
    ecosystems = {
        affected.get("package", {}).get("ecosystem")
        for affected in record.get("affected", [])
    }
    ecosystems.discard(None)
    if ecosystems and ecosystem not in ecosystems:
        raise ValueError(
            f"OSV record {record_id} targets {sorted(ecosystems)} but is being "
            f"built into the {ecosystem} database"
        )

    return f"{record_id}.json"


def build_offline_db(
    records_dir: str | Path,
    cache_root: str | Path,
    *,
    ecosystem: str = "PyPI",
) -> Path:
    """Build ``<cache_root>/osv-scanner/<ecosystem>/all.zip`` from every
    ``*.json`` OSV record under ``records_dir``.

    Each zip entry is named ``<record-id>.json`` (the record's own ``id``
    field), and carries the record's exact on-disk bytes so the readable
    fixture and the zipped payload never diverge. Entries are written in
    sorted order with a fixed timestamp/attributes and no compression, so the
    output is byte-identical across runs and across machines.

    Raises ``ValueError`` if ``records_dir`` holds no ``*.json`` records, or if
    any record is malformed / unsafely-named / mis-targeted (see module
    docstring).

    Returns ``cache_root`` (as a ``Path``) — the value to hand osv-scanner as
    ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY``.
    """
    records_dir = Path(records_dir)
    cache_root = Path(cache_root)

    # Collect (entry-name, raw-bytes) pairs, keyed on the record id, sorted for
    # a stable emission order independent of the filesystem's readdir order.
    entries: dict[str, bytes] = {}
    for record_path in sorted(records_dir.glob("*.json")):
        raw = record_path.read_bytes()
        entry_name = _entry_for_record(raw, record_path, ecosystem)
        if entry_name in entries:
            raise ValueError(
                f"duplicate OSV record id for {entry_name!r} while building "
                f"{ecosystem} all.zip from {records_dir}"
            )
        entries[entry_name] = raw

    if not entries:
        # An empty DB is consumed by osv-scanner as a *successful clean scan* —
        # never emit one silently. A caller pointing at the wrong directory
        # must fail loud, not manufacture a false-green.
        raise ValueError(
            f"no OSV records (*.json) found under {records_dir} — refusing to "
            f"build an empty {ecosystem} all.zip (it would read as a clean scan)"
        )

    db_dir = cache_root / "osv-scanner" / ecosystem
    db_dir.mkdir(parents=True, exist_ok=True)
    zip_path = db_dir / "all.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        for entry_name in sorted(entries):
            info = zipfile.ZipInfo(entry_name, date_time=_FIXED_DATE_TIME)
            info.compress_type = _COMPRESSION
            info.external_attr = _FIXED_EXTERNAL_ATTR
            info.create_system = 3  # Unix — fixed, not the build host's OS.
            zf.writestr(info, entries[entry_name])

    return cache_root
