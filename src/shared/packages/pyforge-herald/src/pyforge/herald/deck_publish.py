"""Publish current deck exports to object storage (CAP-54 D1)."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from . import deck_versions, twins
from .deck_store import DeckStore
from .twins import TwinOriginError

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


def _manifest_bytes(
    records: list[ExportRecord],
    *,
    twins_payload: dict[str, object] | None = None,
) -> bytes:
    payload: dict[str, object] = {"exports": [asdict(record) for record in records]}
    if twins_payload is not None:
        payload["twins"] = twins_payload
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


def _upload_file(
    path: Path,
    *,
    store: DeckStore,
    dry_run: bool,
) -> tuple[int, int]:
    """Return ``(uploads, skipped)`` for one object."""
    sha256, _size = _stream_sha256(path)
    content_type = _content_type(path)
    object_key = f"sha256/{sha256}"
    if dry_run:
        if store.head(object_key) is None:
            return 1, 0
        return 0, 1
    with path.open("rb") as handle:
        if store.put_if_absent(object_key, handle, content_type=content_type):
            return 1, 0
        return 0, 1


def _scan_or_raise(paths: list[Path]) -> None:
    for path in paths:
        for finding in twins.scan_file(path) if path.is_file() else twins.scan_tree(path):
            raise TwinOriginError(finding)


def _publish_twins(
    slug: str,
    *,
    repo_root: Path,
    store: DeckStore,
    dry_run: bool,
) -> tuple[dict[str, object], int, int]:
    uploads = 0
    skipped = 0
    twins_payload: dict[str, object] = {}

    standalone = twins.current_standalone_twin(repo_root, slug)
    if standalone is not None:
        _scan_or_raise([standalone])
        up, skip = _upload_file(standalone, store=store, dry_run=dry_run)
        uploads += up
        skipped += skip
        sha256, size = _stream_sha256(standalone)
        try:
            rel = standalone.relative_to(repo_root).as_posix()
        except ValueError:
            rel = standalone.as_posix()
        twins_payload["standalone"] = {
            "path": rel,
            "sha256": sha256,
            "size": size,
            "content_type": _content_type(standalone),
            "source_commit": _source_commit(repo_root, standalone),
        }

    deck_dir = twins.react_deck_dir(repo_root, slug)
    if deck_dir is not None:
        dist = twins.build_react_bundle(deck_dir)
        _scan_or_raise([dist])
        file_map: dict[str, str] = {}
        for rel, file_path in twins.bundle_manifest_paths(dist).items():
            up, skip = _upload_file(file_path, store=store, dry_run=dry_run)
            uploads += up
            skipped += skip
            file_sha, _ = _stream_sha256(file_path)
            file_map[rel] = file_sha
        twins_payload["bundle"] = {
            "files": file_map,
            "source_commit": _source_commit(repo_root, deck_dir / "index.html"),
        }

    return twins_payload, uploads, skipped


def publish_deck(
    slug: str,
    *,
    repo_root: Path,
    store: DeckStore,
    dry_run: bool = False,
    include_twins: bool = False,
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
        up, skip = _upload_file(path, store=store, dry_run=dry_run)
        uploads += up
        skipped += skip
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

    twins_section: dict[str, object] | None = None
    if include_twins:
        twins_section, twin_up, twin_skip = _publish_twins(
            slug, repo_root=repo_root, store=store, dry_run=dry_run
        )
        uploads += twin_up
        skipped += twin_skip
        if not twins_section:
            twins_section = None

    manifest_written = False
    manifest_key = _manifest_key(slug)
    new_manifest = _manifest_bytes(records, twins_payload=twins_section)
    existing_head = store.head(manifest_key)
    unchanged = False
    if existing_head is not None and existing_head.size == len(new_manifest):
        try:
            current = b"".join(store.open_stream(manifest_key))
            unchanged = current == new_manifest
        except (KeyError, OSError):
            unchanged = False
    if not unchanged:
        manifest_written = True
        if not dry_run:
            store.put_bytes(manifest_key, new_manifest, content_type=_MANIFEST_MEDIA)

    return PublishReport(uploads=uploads, skipped_objects=skipped, manifest_written=manifest_written)


def exports_as_json(slug: str, *, store: DeckStore) -> str:
    records = read_manifest(store, slug)
    return json.dumps([asdict(r) for r in records], indent=2, sort_keys=True) + "\n"
