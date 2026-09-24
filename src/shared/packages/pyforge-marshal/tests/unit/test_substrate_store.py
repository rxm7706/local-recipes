"""Story 46.1 (spec-pyforge-marshal CAP-192) -- the substrate pack I/O.

The round trip (AC2: a loop home packed, then installed into a fresh clone,
yields the loop home's exact bytes), deterministic identity (AC3: the same
member files packed twice hash the same), and every refusal the I/O matrix
names -- tampered bytes, unsafe archive entries, a malformed manifest -- each
of which must install nothing at all."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import substrate_store as store
from pyforge.marshal.core import substrate

_FILES = {
    ".codegraph/codegraph.db": b"SQLite format 3\x00" + bytes(range(256)) * 8,
    ".claude/data/pyforge-scribe/graph.json": b'{"nodes": [1, 2, 3]}\n',
    ".claude/data/pyforge-scribe/move-list.json": b'{"moves": []}\n',
    ".claude/data/pyforge-scribe/cocoindex-index.json": b'{"index": {"a": 1}}\n',
}
_ALL = [m.name for m in substrate.SUBSTRATE_MEMBERS]


def _loop_home(root: Path, files: dict[str, bytes] = _FILES) -> Path:
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def _packable(root: Path) -> dict[str, tuple[str, ...]]:
    packable: dict[str, tuple[str, ...]] = {}
    for member in substrate.SUBSTRATE_MEMBERS:
        files, _ = store.packable_files(root, member)
        if files:
            packable[member.name] = files
    return packable


def _pack(root: Path, out: Path, commit: str = "c0ffee") -> store.PackResult:
    return store.write_pack(root, out, source_commit=commit, members=_packable(root))


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _forge(
    pack_dir: Path,
    entries: list[tuple[tarfile.TarInfo, bytes | None]],
    members: dict[str, list[dict[str, object]]],
) -> None:
    """Write an arbitrary archive plus a manifest whose ARCHIVE digest is
    correct -- so the refusal under test is the entry-level one."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    archive_path = pack_dir / substrate.ASSET_ARCHIVE
    with tarfile.open(archive_path, mode="w:gz") as archive:
        for info, data in entries:
            archive.addfile(info, io.BytesIO(data) if data is not None else None)
    blob = archive_path.read_bytes()
    document = {
        "schema": substrate.MANIFEST_SCHEMA,
        "schema_version": substrate.MANIFEST_SCHEMA_VERSION,
        "source_commit": "f00d",
        "archive": {"name": substrate.ASSET_ARCHIVE, "sha256": _sha(blob), "size": len(blob)},
        "members": {name: {"files": files} for name, files in members.items()},
    }
    (pack_dir / substrate.ASSET_MANIFEST).write_text(json.dumps(document), encoding="utf-8")


def _reg(name: str, data: bytes) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


def _planning_members(data: bytes) -> dict[str, list[dict[str, object]]]:
    return {
        substrate.MEMBER_PLANNING_GRAPH: [
            {"path": ".claude/data/pyforge-scribe/graph.json", "sha256": _sha(data), "size": len(data)}
        ]
    }


def _install(clone: Path, pack_dir: Path, members: list[str] | None = None) -> store.InstallResult:
    return store.verify_and_install(
        clone,
        manifest_path=pack_dir / substrate.ASSET_MANIFEST,
        archive_path=pack_dir / substrate.ASSET_ARCHIVE,
        members=_ALL if members is None else members,
    )


class TestRoundTrip:
    def test_a_packed_loop_home_installs_its_exact_bytes_into_a_fresh_clone(self, tmp_path):
        # AC2 -- the round trip is the oracle for "byte-identical".
        home = _loop_home(tmp_path / "home")
        pack = _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        clone.mkdir()

        result = _install(clone, tmp_path / "pack")

        assert result.refused is None
        assert set(result.installed) == set(_ALL)
        assert result.not_served == {}
        assert _snapshot(clone) == _FILES
        assert pack.members[substrate.MEMBER_STRUCTURE_GRAPH][0].sha256 == _sha(_FILES[".codegraph/codegraph.db"])

    def test_manifest_describes_every_file_and_the_archive(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        pack = _pack(home, tmp_path / "pack", commit="abc")
        manifest = substrate.parse_manifest(pack.manifest_path.read_text(encoding="utf-8"))
        assert manifest.source_commit == "abc"
        assert manifest.archive_sha256 == _sha(pack.archive_path.read_bytes())
        assert {path: (entry.sha256, entry.size) for path, (_, entry) in manifest.file_index().items()} == {
            rel: (_sha(data), len(data)) for rel, data in _FILES.items()
        }

    def test_archive_entries_are_plain_sorted_regular_files(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        pack = _pack(home, tmp_path / "pack")
        with tarfile.open(pack.archive_path, mode="r:gz") as archive:
            infos = archive.getmembers()
        assert [i.name for i in infos] == sorted(_FILES)
        assert all(i.isreg() and i.mtime == 0 and i.uid == 0 and i.gid == 0 and i.mode == 0o644 for i in infos)
        assert all(i.uname == "" and i.gname == "" for i in infos)


class TestDeterministicPack:
    def test_packing_the_same_files_twice_gives_the_same_archive_sha256(self, tmp_path):
        # AC3.
        home = _loop_home(tmp_path / "home")
        first = _pack(home, tmp_path / "one")
        second = _pack(home, tmp_path / "two")
        assert first.archive_sha256 == second.archive_sha256
        assert first.archive_path.read_bytes() == second.archive_path.read_bytes()

    def test_identity_ignores_mtimes_and_the_producers_path(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        first = _pack(home, tmp_path / "one")
        elsewhere = _loop_home(tmp_path / "a" / "different" / "home")
        for rel in _FILES:
            os.utime(elsewhere / rel, (1_000_000, 1_000_000))
        second = _pack(elsewhere, tmp_path / "two")
        assert first.archive_sha256 == second.archive_sha256

    def test_different_bytes_give_a_different_archive(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        first = _pack(home, tmp_path / "one")
        (home / ".claude/data/pyforge-scribe/graph.json").write_bytes(b"{}\n")
        second = _pack(home, tmp_path / "two")
        assert first.archive_sha256 != second.archive_sha256


class TestPackable:
    def test_absent_sentinel_is_not_packable(self, tmp_path):
        member = substrate.member_by_name(substrate.MEMBER_STRUCTURE_GRAPH)
        assert member is not None
        files, reason = store.packable_files(tmp_path, member)
        assert files == ()
        assert reason is not None and "does not exist" in reason

    def test_symlinked_sentinel_is_not_packable(self, tmp_path):
        secret = tmp_path / "secret"
        secret.write_text("private")
        (tmp_path / ".codegraph").mkdir()
        (tmp_path / ".codegraph/codegraph.db").symlink_to(secret)
        member = substrate.member_by_name(substrate.MEMBER_STRUCTURE_GRAPH)
        assert member is not None
        files, reason = store.packable_files(tmp_path, member)
        assert files == ()
        assert reason is not None and "not a regular file" in reason

    def test_optional_file_is_packed_only_when_present(self, tmp_path):
        files = {k: v for k, v in _FILES.items() if "cocoindex" not in k}
        home = _loop_home(tmp_path, files)
        member = substrate.member_by_name(substrate.MEMBER_DERIVED_CONTEXT)
        assert member is not None
        assert store.packable_files(home, member) == ((".claude/data/pyforge-scribe/move-list.json",), None)


class TestRefusalsInstallNothing:
    def _assert_nothing(self, clone: Path, result: store.InstallResult, needle: str) -> None:
        assert result.refused is not None and needle in result.refused
        assert result.installed == ()
        assert _snapshot(clone) == {}

    def test_tampered_archive_byte(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        pack = _pack(home, tmp_path / "pack")
        blob = bytearray(pack.archive_path.read_bytes())
        blob[len(blob) // 2] ^= 0xFF
        pack.archive_path.write_bytes(bytes(blob))
        clone = tmp_path / "clone"
        clone.mkdir()
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "does not match")

    def test_tampered_file_under_a_recomputed_archive_digest(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        honest, evil = b'{"ok": 1}\n', b'{"no": 1}\n'
        assert len(honest) == len(evil)
        _forge(tmp_path / "pack", [_reg(".claude/data/pyforge-scribe/graph.json", evil)], _planning_members(honest))
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "does not match the manifest")

    def test_an_entry_whose_size_disagrees_with_the_manifest(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        _forge(
            tmp_path / "pack",
            [_reg(".claude/data/pyforge-scribe/graph.json", b"{}\n")],
            _planning_members(b'{"longer": 1}\n'),
        )
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "the manifest says")

    def test_an_entry_the_manifest_does_not_name(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        data = b"{}\n"
        _forge(
            tmp_path / "pack",
            [_reg(".claude/data/pyforge-scribe/graph.json", data), _reg("../escape.sh", b"rm -rf /\n")],
            _planning_members(data),
        )
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "not a manifest file")
        assert not (tmp_path / "escape.sh").exists()

    def test_a_symlink_entry_under_a_manifest_name(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        link = tarfile.TarInfo(".claude/data/pyforge-scribe/graph.json")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        _forge(tmp_path / "pack", [(link, None)], _planning_members(b""))
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "not a regular file")

    def test_a_duplicate_entry(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        data = b"{}\n"
        entry = _reg(".claude/data/pyforge-scribe/graph.json", data)
        _forge(tmp_path / "pack", [entry, _reg(".claude/data/pyforge-scribe/graph.json", data)], _planning_members(data))
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "twice")

    def test_a_manifest_file_missing_from_the_archive(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        data = b"{}\n"
        members = _planning_members(data)
        members[substrate.MEMBER_STRUCTURE_GRAPH] = [
            {"path": ".codegraph/codegraph.db", "sha256": _sha(b"db"), "size": 2}
        ]
        _forge(tmp_path / "pack", [_reg(".claude/data/pyforge-scribe/graph.json", data)], members)
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "lacks manifest files")

    def test_a_malformed_manifest(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        pack = _pack(home, tmp_path / "pack")
        document = json.loads(pack.manifest_path.read_text(encoding="utf-8"))
        document["members"][substrate.MEMBER_STRUCTURE_GRAPH]["files"][0]["path"] = "/etc/cron.d/x"
        pack.manifest_path.write_text(json.dumps(document), encoding="utf-8")
        clone = tmp_path / "clone"
        clone.mkdir()
        self._assert_nothing(clone, _install(clone, tmp_path / "pack"), "malformed")

    def test_an_unreadable_archive(self, tmp_path):
        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()
        blob = b"not a gzip stream"
        (pack_dir / substrate.ASSET_ARCHIVE).write_bytes(blob)
        data = b"{}\n"
        document = {
            "schema": substrate.MANIFEST_SCHEMA,
            "schema_version": substrate.MANIFEST_SCHEMA_VERSION,
            "source_commit": "x",
            "archive": {"name": substrate.ASSET_ARCHIVE, "sha256": _sha(blob), "size": len(blob)},
            "members": {name: {"files": files} for name, files in _planning_members(data).items()},
        }
        (pack_dir / substrate.ASSET_MANIFEST).write_text(json.dumps(document), encoding="utf-8")
        clone = tmp_path / "clone"
        clone.mkdir()
        self._assert_nothing(clone, _install(clone, pack_dir), "unreadable")


class TestInstallDestinations:
    def test_only_requested_members_are_written(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        clone.mkdir()
        result = _install(clone, tmp_path / "pack", members=[substrate.MEMBER_STRUCTURE_GRAPH])
        assert result.installed == (substrate.MEMBER_STRUCTURE_GRAPH,)
        assert set(_snapshot(clone)) == {".codegraph/codegraph.db"}

    def test_a_member_the_pack_lacks_is_not_served(self, tmp_path):
        files = {k: v for k, v in _FILES.items() if not k.startswith(".codegraph")}
        home = _loop_home(tmp_path / "home", files)
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        clone.mkdir()
        result = _install(clone, tmp_path / "pack")
        assert substrate.MEMBER_STRUCTURE_GRAPH not in result.installed
        assert "does not carry" in result.not_served[substrate.MEMBER_STRUCTURE_GRAPH]

    def test_an_existing_file_is_never_overwritten(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        stray = clone / ".claude/data/pyforge-scribe/cocoindex-index.json"
        stray.parent.mkdir(parents=True)
        stray.write_bytes(b"mine")
        result = _install(clone, tmp_path / "pack")
        assert "already exists" in result.not_served[substrate.MEMBER_DERIVED_CONTEXT]
        assert stray.read_bytes() == b"mine"
        assert not (clone / ".claude/data/pyforge-scribe/move-list.json").exists()
        assert substrate.MEMBER_PLANNING_GRAPH in result.installed

    def test_never_writes_through_a_symlinked_directory(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        (clone / ".claude").mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()
        (clone / ".claude/data").symlink_to(outside, target_is_directory=True)
        result = _install(clone, tmp_path / "pack")
        assert "symlink" in result.not_served[substrate.MEMBER_PLANNING_GRAPH]
        assert "symlink" in result.not_served[substrate.MEMBER_DERIVED_CONTEXT]
        assert result.installed == (substrate.MEMBER_STRUCTURE_GRAPH,)
        assert list(outside.iterdir()) == []

    def test_the_sentinel_is_written_last(self, tmp_path, monkeypatch):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        clone.mkdir()
        order: list[str] = []
        real = store._install_file

        def _record(staged: Path, target: Path) -> None:
            order.append(str(target.relative_to(clone)))
            real(staged, target)

        monkeypatch.setattr(store, "_install_file", _record)
        _install(clone, tmp_path / "pack", members=[substrate.MEMBER_DERIVED_CONTEXT])
        assert order == [
            ".claude/data/pyforge-scribe/cocoindex-index.json",
            ".claude/data/pyforge-scribe/move-list.json",
        ]

    def test_a_failed_file_write_leaves_the_member_absent(self, tmp_path, monkeypatch):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        clone = tmp_path / "clone"
        clone.mkdir()

        def _boom(staged: Path, target: Path) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(store, "_install_file", _boom)
        result = _install(clone, tmp_path / "pack", members=[substrate.MEMBER_PLANNING_GRAPH])
        assert result.installed == ()
        assert "disk full" in result.not_served[substrate.MEMBER_PLANNING_GRAPH]


class _FakeGh:
    def __init__(self, result: ProcessResult | None = None, *, error: Exception | None = None, source: Path | None = None):
        self.result = result or ProcessResult(returncode=0, stdout="", stderr="")
        self.error = error
        self.source = source
        self.calls: list[tuple[tuple[str, ...], Path, float | None]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append((tuple(argv), Path(cwd), timeout_s))
        if self.error is not None:
            raise self.error
        if self.source is not None and self.result.returncode == 0:
            dest = Path(argv[argv.index("--dir") + 1])
            for name in (substrate.ASSET_MANIFEST, substrate.ASSET_ARCHIVE):
                shutil.copyfile(self.source / name, dest / name)
        return self.result


class TestFetchPair:
    def test_success_downloads_the_pair_through_gh(self, tmp_path):
        home = _loop_home(tmp_path / "home")
        _pack(home, tmp_path / "pack")
        dest = tmp_path / "dest"
        dest.mkdir()
        gh = _FakeGh(source=tmp_path / "pack")
        assert store.fetch_pair(gh, root=tmp_path, tag="substrate-nightly", repo=None, dest_dir=dest) is None
        argv, cwd, timeout = gh.calls[0]
        assert argv[:4] == ("gh", "release", "download", "substrate-nightly")
        assert cwd == tmp_path
        assert timeout == store.FETCH_TIMEOUT_S

    @pytest.mark.parametrize(
        ("gh", "needle"),
        [
            (_FakeGh(error=ProcessError("executable not found: 'gh'")), "could not run"),
            (_FakeGh(error=ProcessError("timed out after 600s")), "timed out"),
            (_FakeGh(ProcessResult(returncode=1, stdout="", stderr="release not found\n")), "exited 1 (release not found)"),
            (_FakeGh(), "was not downloaded"),
        ],
    )
    def test_every_failure_is_a_reason(self, tmp_path, gh, needle):
        reason = store.fetch_pair(gh, root=tmp_path, tag="t", repo="o/r", dest_dir=tmp_path)
        assert reason is not None and needle in reason
