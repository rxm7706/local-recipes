"""Deterministic offline OSV database builder (Story 1.4 spike substrate).

``build_offline_db`` assembles the exact on-disk layout osv-scanner 2.4.0
consumes in ``--offline`` mode from a directory of readable OSV JSON records:

    <cache_root>/osv-scanner/<Ecosystem>/all.zip

(empirically confirmed against osv-scanner 2.4.0 / osv-scalibr 0.4.5 by
reproducing the tree its own ``--download-offline-databases`` writes, and by
matching a seeded advisory offline — see
``planning-artifacts/osv-db-offline-provisioning-decision.md`` § 11).

The build is **deterministic**: every zip entry is **stored uncompressed**
(``ZIP_STORED``) with a fixed DOS-epoch timestamp (``1980-01-01``) and fixed
permission/attribute bits, entries emitted in sorted order. No ``datetime.now()``
and no DEFLATE — so the bytes never depend on the host's zlib build and two
builds over the same records **on the same interpreter** produce a
**byte-identical** ``all.zip`` (the fixture is tiny; compression buys nothing and
would forfeit cross-zlib reproducibility). ``zipfile``'s create/extract-version
header bytes are NOT pinned, so cross-CPython-version byte-identity is the design
intent, not a tested guarantee (see the decision record's determinism residual
risk). This is the hermetic vulnerability-data substrate Story 1.5 / 2.5 / CI
reuse; it is intentionally side-effect free apart from writing ``all.zip`` under
``cache_root``.

The builder is **fail-loud** (always ``ValueError``, never ``AttributeError``):
a ``records_dir`` that is not an existing directory, an empty ``records_dir``, a
case-variant ``.JSON`` record or a record nested under a subdirectory that the
exact non-recursive glob would skip, a record whose top level / ``affected`` /
``package`` is the wrong JSON type, a missing/non-string ``id``, an ``id`` that
is not a safe bare filename, or a record with no ``affected`` entry that targets
the requested ``ecosystem`` **with a package name AND a concrete matchable spec**
(a non-empty ``versions`` string, or a ``ranges`` entry with ``events``) all
raise ``ValueError`` rather than silently producing an empty, mis-shelved, or
**unmatchable** DB. A DB that osv-scanner loads but can never match reads as a
clean scan — the exact false-green this whole project exists to prevent.

Scope: this builder guards the in-repo **fixture** substrate only. An
externally-provisioned DB (osv-native ``--download-offline-databases``, a conda
package, or a mirror) is out of its reach — validating THAT at load time is
Story 1.5's **content pre-flight** (decision record § 4), which reuses the same
``_entry_for_record`` shape checks on the loaded entries, since osv-scanner's
own loader accepts malformed/empty advisory content and still exits 0.

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
# 0o100644 (S_IFREG | rw-r--r--) in the high 16 bits — the file-type bit
# S_IFREG (0o100000) marks a regular file so strict zip extractors recognize the
# entry, plus fixed permissions so the attribute bytes are stable across
# machines (Gemini PR #55).
_FIXED_EXTERNAL_ATTR = 0o100644 << 16
# Store uncompressed: DEFLATE output is a function of the host zlib build and
# is NOT guaranteed byte-identical across zlib versions / CI platforms; for a
# tiny fixture DB, ZIP_STORED is truly portable-deterministic at no cost.
_COMPRESSION = zipfile.ZIP_STORED


def _entry_for_record(raw: bytes, record_path: Path, ecosystem: str) -> str:
    """Validate one OSV record's bytes and return its ``<id>.json`` entry name,
    failing loud on anything that would corrupt or silently hollow the DB.

    Every shape check raises ``ValueError`` (never ``AttributeError``): a record
    whose top level is a JSON array/string/number, or whose ``affected`` /
    ``package`` are the wrong type, is a MALFORMED record, not a crash — the
    fail-loud contract the tests assert with ``pytest.raises(ValueError)``."""
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OSV record {record_path} is not valid JSON: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError(
            f"OSV record {record_path} top level is {type(record).__name__}, "
            "expected a JSON object"
        )

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

    # MATCHABILITY (review H1-adjacent, M6/L4): a record that is shelved into
    # <ecosystem>/all.zip but that osv-scanner can never match is a silent
    # coverage hole indistinguishable from real cleanliness. Require at least one
    # `affected` entry that (a) targets THIS ecosystem, (b) names a package, and
    # (c) carries a concrete matchable spec (`versions` list or `ranges`). This
    # is stricter than the old "no conflicting ecosystem" check, which passed a
    # record with an empty/ecosystem-less `affected`.
    affected = record.get("affected")
    if not isinstance(affected, list) or not affected:
        raise ValueError(
            f"OSV record {record_id} has a missing/empty/non-list 'affected' — "
            "it could never match a scan (unmatchable coverage hole)"
        )
    matchable = False
    for entry in affected:
        if not isinstance(entry, dict):
            raise ValueError(
                f"OSV record {record_id} has a non-object 'affected' entry "
                f"({type(entry).__name__})"
            )
        package = entry.get("package")
        if package is not None and not isinstance(package, dict):
            raise ValueError(
                f"OSV record {record_id} has a non-object 'affected[].package' "
                f"({type(package).__name__})"
            )
        package = package or {}
        if package.get("ecosystem") != ecosystem:
            continue
        name = package.get("name")
        versions = entry.get("versions")
        ranges = entry.get("ranges")
        # A CONCRETE spec means at least one non-empty version STRING, or a
        # range that carries `events`. `versions: [""]` / `[123]` / `ranges:
        # [{}]` are present-but-unmatchable (osv could never match them) and
        # must NOT count — else the record is shelved yet silently false-clean,
        # the same hole an absent spec opens (review F3/EC2).
        has_versions = isinstance(versions, list) and any(
            isinstance(v, str) and v for v in versions
        )
        has_ranges = isinstance(ranges, list) and any(
            isinstance(r, dict) and r.get("events") for r in ranges
        )
        if isinstance(name, str) and name and (has_versions or has_ranges):
            matchable = True
    if not matchable:
        raise ValueError(
            f"OSV record {record_id} has no {ecosystem} 'affected' entry with a "
            "package name AND a concrete version spec ('versions' or 'ranges') — "
            "osv-scanner would shelve it but never match it (silent false-clean)"
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

    # EC3: fail loud (ValueError, per the module contract) if records_dir is not
    # an existing directory — a non-existent path or a file passed by mistake
    # must not surface as a bare FileNotFoundError/NotADirectoryError that a
    # ValueError-catching caller (Story 1.5) would miss.
    if not records_dir.is_dir():
        raise ValueError(f"records_dir {records_dir} is not an existing directory")

    # L5: glob("*.json") is case-sensitive + non-recursive on POSIX, so a record
    # dropped as `PDOS-0002.JSON` / `.Json` would be silently skipped — a
    # partial-drop coverage hole (some records present, one missing). Fail loud
    # on a file whose extension is .json only by case, so the § 11 "drop a JSON
    # record and rebuild" workflow (Story 2.5) can't lose a record.
    case_variant = sorted(
        p.name
        for p in records_dir.iterdir()
        if p.is_file() and p.suffix != ".json" and p.suffix.lower() == ".json"
    )
    if case_variant:
        raise ValueError(
            f"OSV record file(s) with a non-canonical .json extension would be "
            f"silently skipped by the builder: {case_variant} — rename to a "
            "lowercase '.json' extension so they are included"
        )
    # EC5: the same non-recursive glob also skips a record nested under a
    # subdirectory. The old comment CLAIMED to guard "under a subdir" but the
    # case-variant check above only inspects the top level — a nested record was
    # silently dropped (partial-coverage false-clean). Detect and fail loud.
    nested = sorted(
        str(p.relative_to(records_dir))
        for p in records_dir.rglob("*.json")
        if p.is_file() and p.parent != records_dir
    )
    if nested:
        raise ValueError(
            f"OSV record file(s) nested under a subdirectory would be silently "
            f"skipped by the non-recursive builder glob: {nested} — move them "
            "directly under the records dir so they are included"
        )

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
