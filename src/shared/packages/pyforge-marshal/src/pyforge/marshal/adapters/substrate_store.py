"""Substrate pack I/O (Story 46.1, spec-pyforge-marshal CAP-192): hash and
collect member files, write the deterministic pair, fetch it with ``gh``, and
install it verify-first.

The contract (members, manifest shape, path safety, findings) is
``core/substrate.py``'s; this module only does the bytes.

**Install is verify-then-stage-then-replace, never ``extractall``.**

1. The manifest is parsed (``parse_manifest`` refuses unsafe or foreign
   paths before any byte is read).
2. The archive's own sha256 + size must match the manifest.
3. Every archive entry is streamed once: it must be a regular file, named
   in the manifest, not a duplicate, of the declared size, and hash to the
   declared sha256. Entries for the members being installed are copied into
   a private staging directory as they stream; nothing touches the clone.
4. Every manifest file must have been seen.

Only when all four hold is anything installed, and then only for members
whose sentinel is absent, whose target paths do not exist, and whose target
directories contain no symlinked component -- each file through
``pyforge.core.atomic_write`` (same-directory temp + ``os.replace``), the
sentinel last so a crash mid-member never leaves a member that looks
present. Any refusal in steps 1-4 installs nothing at all.

**Pack is deterministic.** Entries are sorted by path; every tar header
carries mtime 0, uid/gid 0, empty owner names and mode 0644; the gzip
header carries mtime 0 and no file name. Each file's sha256 is taken from
the very bytes written into the archive, so the manifest always describes
the archive and never a file that moved on underneath it.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import tarfile
import tempfile
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, BinaryIO, cast

from pyforge.core.atomic_write import atomic_write, atomic_write_text
from pyforge.core.process import ProcessError, ProcessPort

from ..core.substrate import (
    ASSET_ARCHIVE,
    ASSET_MANIFEST,
    ManifestError,
    ManifestFile,
    SubstrateManifest,
    SubstrateMember,
    check_archive_digest,
    check_file_digest,
    member_by_name,
    parse_manifest,
    render_gh_download_argv,
    render_manifest,
)

__all__ = (
    "FETCH_TIMEOUT_S",
    "InstallResult",
    "PackResult",
    "fetch_pair",
    "member_present",
    "packable_files",
    "sha256_file",
    "verify_and_install",
    "write_pack",
)

#: Ceiling for one ``gh release download`` of the pair.
FETCH_TIMEOUT_S = 600.0

_CHUNK = 1 << 20


def sha256_file(path: Path) -> tuple[str, int]:
    """``(sha256 hex, size)`` of ``path``'s bytes."""
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def member_present(root: Path, member: SubstrateMember) -> bool:
    """The member's sentinel exists in ``root`` -- as anything, a dangling
    symlink included. Present means bootstrap never touches it."""
    return os.path.lexists(Path(root) / member.sentinel)


def packable_files(root: Path, member: SubstrateMember) -> tuple[tuple[str, ...], str | None]:
    """``(files, None)`` for a member the producer can pack, else
    ``((), reason)``. Only regular, non-symlink files are packed: a
    symlinked member file could publish bytes from outside the member."""
    sentinel = Path(root) / member.sentinel
    if not os.path.lexists(sentinel):
        return (), f"{member.sentinel} does not exist"
    if sentinel.is_symlink() or not sentinel.is_file():
        return (), f"{member.sentinel} is not a regular file"
    files = [member.sentinel]
    for rel in member.optional:
        candidate = Path(root) / rel
        if not candidate.is_symlink() and candidate.is_file():
            files.append(rel)
    return tuple(sorted(files)), None


class _HashingReader:
    """A read-only file wrapper that hashes every byte ``tarfile`` pulls
    through it, so the manifest is computed from the archived bytes."""

    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        self._digest = hashlib.sha256()
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._handle.read(size)
        self._digest.update(chunk)
        self.size += len(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _tar_info(rel: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(rel)
    info.type = tarfile.REGTYPE
    info.size = size
    info.mtime = 0
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


@dataclass(frozen=True)
class PackResult:
    manifest_path: Path
    archive_path: Path
    archive_sha256: str
    archive_size: int
    members: Mapping[str, tuple[ManifestFile, ...]]


def write_pack(
    root: Path,
    out_dir: Path,
    *,
    source_commit: str,
    members: Mapping[str, Sequence[str]],
) -> PackResult:
    """Write ``substrate.tar.gz`` then ``substrate-manifest.json`` into
    ``out_dir`` for ``members`` (member name -> repo-relative files, as
    ``packable_files`` returned them). Raises ``OSError`` on I/O failure and
    ``ValueError`` when a file changes size while it is being archived."""
    root = Path(root)
    out_dir = Path(out_dir)
    owner_of = {rel: name for name, files in members.items() for rel in files}
    measured: dict[str, ManifestFile] = {}

    def _write_archive(tmp: Path) -> None:
        with tmp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    for rel in sorted(owner_of):
                        with (root / rel).open("rb") as handle:
                            size = os.fstat(handle.fileno()).st_size
                            reader = _HashingReader(handle)
                            archive.addfile(_tar_info(rel, size), cast(IO[bytes], reader))
                        if reader.size != size:
                            raise ValueError(f"{rel} changed size while it was being packed")
                        measured[rel] = ManifestFile(path=rel, sha256=reader.hexdigest(), size=size)

    archive_path = out_dir / ASSET_ARCHIVE
    atomic_write(archive_path, _write_archive)
    archive_sha256, archive_size = sha256_file(archive_path)
    member_files = {
        name: tuple(measured[rel] for rel in sorted(files)) for name, files in sorted(members.items())
    }
    manifest_text = render_manifest(
        source_commit=source_commit,
        archive_sha256=archive_sha256,
        archive_size=archive_size,
        members=member_files,
    )
    manifest_path = out_dir / ASSET_MANIFEST
    atomic_write_text(manifest_path, manifest_text)
    return PackResult(
        manifest_path=manifest_path,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
        archive_size=archive_size,
        members=member_files,
    )


def fetch_pair(
    process: ProcessPort,
    *,
    root: Path,
    tag: str,
    repo: str | None,
    dest_dir: Path,
) -> str | None:
    """Download the pair from release ``tag`` into ``dest_dir`` with
    ``gh`` (run from ``root`` so gh resolves the clone's own remote when
    ``repo`` is ``None``). ``None`` on success, else the reason."""
    argv = render_gh_download_argv(tag=tag, repo=repo, dest_dir=str(dest_dir))
    try:
        result = process.run(argv, cwd=Path(root), timeout_s=FETCH_TIMEOUT_S)
    except ProcessError as exc:
        return f"`{' '.join(argv)}` could not run ({exc})"
    if result.returncode != 0:
        output = ((result.stderr or "") + (result.stdout or "")).strip()
        tail = output.splitlines()[-1] if output else "<no output>"
        return f"`{' '.join(argv)}` exited {result.returncode} ({tail})"
    for name in (ASSET_MANIFEST, ASSET_ARCHIVE):
        if not (Path(dest_dir) / name).is_file():
            return f"`{' '.join(argv)}` exited 0 but {name} was not downloaded"
    return None


@dataclass(frozen=True)
class InstallResult:
    """What one ``verify_and_install`` did.

    ``refused`` set means the pack failed verification and NOTHING was
    installed. Otherwise ``installed`` names the members written and
    ``not_served`` maps every other requested member to why the pack did
    not serve it."""

    installed: tuple[str, ...] = ()
    not_served: Mapping[str, str] = field(default_factory=dict)
    refused: str | None = None
    manifest: SubstrateManifest | None = None


def _symlinked_component(root: Path, rel: str) -> Path | None:
    """The first existing symlink among ``rel``'s parent directories under
    ``root``, or ``None``."""
    current = Path(root)
    for part in rel.split("/")[:-1]:
        current = current / part
        if current.is_symlink():
            return current
    return None


def _destination_problem(root: Path, member: SubstrateMember, files: Sequence[ManifestFile]) -> str | None:
    for entry in files:
        link = _symlinked_component(root, entry.path)
        if link is not None:
            return f"{link} is a symlink; bootstrap never writes through one"
        if os.path.lexists(Path(root) / entry.path):
            return f"{entry.path} already exists; bootstrap never overwrites"
    return None


def verify_and_install(
    root: Path,
    *,
    manifest_path: Path,
    archive_path: Path,
    members: Sequence[str],
) -> InstallResult:
    """Verify the pair completely, then install the requested ``members``
    that are safe to write. See the module docstring for the order."""
    root = Path(root)
    try:
        manifest = parse_manifest(Path(manifest_path).read_text(encoding="utf-8"))
    except ManifestError as exc:
        return InstallResult(refused=f"malformed {ASSET_MANIFEST}: {exc}")
    except (OSError, UnicodeDecodeError) as exc:
        return InstallResult(refused=f"{ASSET_MANIFEST} unreadable: {exc}")

    try:
        archive_sha256, archive_size = sha256_file(Path(archive_path))
    except OSError as exc:
        return InstallResult(refused=f"{ASSET_ARCHIVE} unreadable: {exc}", manifest=manifest)
    problem = check_archive_digest(manifest, sha256=archive_sha256, size=archive_size)
    if problem is not None:
        return InstallResult(refused=problem, manifest=manifest)

    wanted = [name for name in members if name in manifest.member_names()]
    wanted_paths = {entry.path for name in wanted for entry in manifest.files_of(name)}
    index = manifest.file_index()

    with tempfile.TemporaryDirectory(prefix="substrate-stage-") as stage_dir:
        staged: dict[str, Path] = {}
        seen: set[str] = set()
        try:
            with tarfile.open(Path(archive_path), mode="r:gz") as archive:
                for info in archive:
                    problem = _stream_entry(archive, info, index, seen, wanted_paths, Path(stage_dir), staged)
                    if problem is not None:
                        return InstallResult(refused=problem, manifest=manifest)
        except (tarfile.TarError, OSError, EOFError, zlib.error) as exc:
            return InstallResult(refused=f"{ASSET_ARCHIVE} unreadable: {exc}", manifest=manifest)
        unseen = sorted(set(index) - seen)
        if unseen:
            return InstallResult(refused=f"{ASSET_ARCHIVE} lacks manifest files {unseen!r}", manifest=manifest)

        installed: list[str] = []
        not_served: dict[str, str] = {}
        for name in members:
            member = member_by_name(name)
            files = manifest.files_of(name)
            if member is None or not files:
                not_served[name] = f"the pack does not carry member {name!r} (the producer had a gap)"
                continue
            problem = _destination_problem(root, member, files)
            if problem is not None:
                not_served[name] = problem
                continue
            # Sentinel last: a member interrupted mid-install never looks present.
            ordered = sorted(files, key=lambda entry: entry.path == member.sentinel)
            try:
                for entry in ordered:
                    _install_file(staged[entry.path], root / entry.path)
            except OSError as exc:
                not_served[name] = f"installing it failed: {exc}"
                continue
            installed.append(name)
    return InstallResult(installed=tuple(installed), not_served=not_served, manifest=manifest)


def _stream_entry(
    archive: tarfile.TarFile,
    info: tarfile.TarInfo,
    index: Mapping[str, tuple[str, ManifestFile]],
    seen: set[str],
    wanted_paths: set[str],
    stage_dir: Path,
    staged: dict[str, Path],
) -> str | None:
    """Verify one archive entry against the manifest, staging it when it
    belongs to a member being installed. The refusal reason, or ``None``."""
    name = info.name
    if name not in index:
        return f"unsafe archive entry {name!r}: not a manifest file"
    if not info.isreg():
        return f"unsafe archive entry {name!r}: not a regular file"
    if name in seen:
        return f"unsafe archive entry {name!r}: appears twice"
    seen.add(name)
    _, expected = index[name]
    if info.size != expected.size:
        return f"{name} is {info.size} bytes in {ASSET_ARCHIVE}, the manifest says {expected.size}"
    source = archive.extractfile(info)
    if source is None:
        return f"unsafe archive entry {name!r}: has no data"
    digest = hashlib.sha256()
    size = 0
    # Only a member being installed is staged; every other entry is still
    # hashed, so one tampered byte anywhere refuses the whole pack.
    target = stage_dir / str(len(staged)) if name in wanted_paths else None
    sink = target.open("wb") if target is not None else None
    try:
        with source:
            for chunk in iter(lambda: source.read(_CHUNK), b""):
                digest.update(chunk)
                size += len(chunk)
                if sink is not None:
                    sink.write(chunk)
    finally:
        if sink is not None:
            sink.close()
    problem = check_file_digest(expected, sha256=digest.hexdigest(), size=size)
    if problem is not None:
        return problem
    if target is not None:
        staged[name] = target
    return None


def _install_file(staged: Path, target: Path) -> None:
    def _copy(tmp: Path) -> None:
        shutil.copyfile(staged, tmp)

    atomic_write(target, _copy)
