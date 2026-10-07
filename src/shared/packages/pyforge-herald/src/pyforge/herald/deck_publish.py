"""Publish current deck exports to object storage (CAP-54 D1)."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from . import deck_versions
from .deck_store import DeckStore

DECK_PUBLISH_FLAG = "pyforge.herald.deck_publish"
_MANIFEST_MEDIA = "application/json"
_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ExportRecord:
    topic: str
    kind: str
    date: str
    size: int
    content_type: str
    sha256: str
    source_commit: str


@dataclass(frozen=True, slots=True)
class PublishReport:
    uploads: int
    skipped_objects: int
    manifest_written: bool


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _source_commit(repo_root: Path, export_path: Path) -> str:
    try:
        rel = export_path.relative_to(repo_root)
    except ValueError:
        rel = export_path
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-list", "-1", "HEAD", "--", str(rel)],
        check=False,
        capture_output=True,
        text=True,
    )
    sha = proc.stdout.strip()
    if proc.returncode == 0 and sha:
        return sha
    fallback = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return fallback.stdout.strip() if fallback.returncode == 0 else ""


def _stream_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _manifest_key(slug: str) -> str:
    return f"manifests/{slug}.json"


def _manifest_bytes(records: list[ExportRecord]) -> bytes:
    payload = {"exports": [asdict(record) for record in records]}
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_manifest(store: DeckStore, slug: str) -> list[ExportRecord]:
    key = _manifest_key(slug)
    head = store.head(key)
    if head is None:
        msg = f"deck {slug!r} has no published manifest in the store"
        raise FileNotFoundError(msg)
    chunks = store.open_stream(key)
    raw = b"".join(chunks)
    data = json.loads(raw.decode("utf-8"))
    exports = data.get("exports")
    if not isinstance(exports, list):
        msg = f"manifest {key!r} is missing an exports list"
        raise ValueError(msg)
    out: list[ExportRecord] = []
    for row in exports:
        if not isinstance(row, dict):
            continue
        out.append(
            ExportRecord(
                topic=str(row["topic"]),
                kind=str(row["kind"]),
                date=str(row["date"]),
                size=int(row["size"]),
                content_type=str(row["content_type"]),
                sha256=str(row["sha256"]),
                source_commit=str(row["source_commit"]),
            )
        )
    return out


def publish_deck(
    slug: str,
    *,
    repo_root: Path,
    store: DeckStore,
    dry_run: bool = False,
) -> PublishReport:
    presentations = repo_root / "presentations"
    exports = deck_versions.current_exports(repo_root, slug)
    if not exports and not (presentations / slug).is_dir():
        msg = f"presentations/{slug} not found"
        raise FileNotFoundError(msg)

    records: list[ExportRecord] = []
    uploads = 0
    skipped = 0

    for path in exports:
        kind = deck_versions.export_kind(path, presentations)
        iso = deck_versions.export_date(path)
        if kind is None or iso is None:
            continue
        sha256, size = _stream_sha256(path)
        content_type = _content_type(path)
        object_key = f"sha256/{sha256}"
        if dry_run:
            if store.head(object_key) is None:
                uploads += 1
            else:
                skipped += 1
        else:
            with path.open("rb") as handle:
                if store.put_if_absent(object_key, handle, content_type=content_type):
                    uploads += 1
                else:
                    skipped += 1
        records.append(
            ExportRecord(
                topic=slug,
                kind=kind,
                date=iso,
                size=size,
                content_type=content_type,
                sha256=sha256,
                source_commit=_source_commit(repo_root, path),
            )
        )

    manifest_written = False
    manifest_key = _manifest_key(slug)
    new_manifest = _manifest_bytes(records)
    existing_head = store.head(manifest_key)
    unchanged = False
    if existing_head is not None and existing_head.size == len(new_manifest):
        try:
            current = b"".join(store.open_stream(manifest_key))
            unchanged = current == new_manifest
        except KeyError, OSError:
            unchanged = False
    if not unchanged:
        manifest_written = True
        if not dry_run:
            store.put_bytes(manifest_key, new_manifest, content_type=_MANIFEST_MEDIA)

    return PublishReport(uploads=uploads, skipped_objects=skipped, manifest_written=manifest_written)


def exports_as_json(slug: str, *, store: DeckStore) -> str:
    records = read_manifest(store, slug)
    return json.dumps([asdict(r) for r in records], indent=2, sort_keys=True) + "\n"
