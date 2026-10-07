"""Unit tests for ``pyforge.herald.deck_publish``."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pyforge.herald.deck_publish import publish_deck, read_manifest
from pyforge.herald.deck_store import MemoryDeckStore


def _write_export(pptx_dir: Path, name: str, body: bytes) -> Path:
    pptx_dir.mkdir(parents=True, exist_ok=True)
    path = pptx_dir / name
    path.write_bytes(body)
    return path


def test_first_publish_uploads_and_second_is_unchanged(tmp_path: Path):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"v1-bytes")
    store = MemoryDeckStore()
    first = publish_deck(slug, repo_root=tmp_path, store=store)
    assert first.uploads == 1
    assert first.manifest_written is True
    records = read_manifest(store, slug)
    assert len(records) == 1
    assert records[0].sha256 == hashlib.sha256(b"v1-bytes").hexdigest()
    second = publish_deck(slug, repo_root=tmp_path, store=store)
    assert second.uploads == 0
    assert second.skipped_objects == 1
    assert second.manifest_written is False


def test_only_current_export_is_published_when_superseded_file_remains(tmp_path: Path):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"old")
    _write_export(pptx_dir, "demo-deck-deck-2026-09-15.pptx", b"new-current")
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store)
    records = read_manifest(store, slug)
    assert len(records) == 1
    assert records[0].date == "2026-09-15"


def test_changed_export_uploads_new_object_and_updates_manifest(tmp_path: Path):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    path = _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"v1")
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store)
    path.write_bytes(b"v2")
    report = publish_deck(slug, repo_root=tmp_path, store=store)
    assert report.uploads == 1
    assert report.manifest_written is True
    records = read_manifest(store, slug)
    assert len(records) == 1
    assert records[0].size == 2


def test_dry_run_writes_nothing(tmp_path: Path, capsys):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"v1")
    store = MemoryDeckStore()
    report = publish_deck(slug, repo_root=tmp_path, store=store, dry_run=True)
    assert report.uploads == 1
    assert store.head("manifests/demo-deck.json") is None


def test_unknown_slug_raises(tmp_path: Path):
    store = MemoryDeckStore()
    with pytest.raises(FileNotFoundError, match="presentations/nosuch"):
        publish_deck("nosuch", repo_root=tmp_path, store=store)


def test_exports_json_round_trip(tmp_path: Path):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"v1")
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store)
    from pyforge.herald.deck_publish import exports_as_json

    payload = json.loads(exports_as_json(slug, store=store))
    assert len(payload) == 1
    assert set(payload[0]) == {
        "topic",
        "kind",
        "date",
        "size",
        "content_type",
        "sha256",
        "source_commit",
    }


def test_source_commit_uses_git_when_available(tmp_path: Path):
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    path = _write_export(pptx_dir, "demo-deck-deck-2026-09-01.pptx", b"v1")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", str(path.relative_to(tmp_path))], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-m", "deck"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store)
    records = read_manifest(store, slug)
    assert len(records[0].source_commit) == 40
