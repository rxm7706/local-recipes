"""The bootstrap substrate's pure contract (Story 46.1, spec-pyforge-marshal
CAP-192).

A bare clone on a cloud runner opens with none of the shared substrate a
loop home carries, so every agent re-derived it privately at its own quota
cost. ``marshal context bootstrap`` (reached as ``pyforge context
bootstrap``) fetches a published pack or rebuilds locally, and ``marshal
context pack`` produces the pack a publisher uploads. This module is the one
owner of what both verbs agree on:

* **The three members**, each with exactly one sentinel file whose presence
  means "this clone already has it" -- the structure graph
  (``.codegraph/codegraph.db``), the planning graph
  (``.claude/data/pyforge-scribe/graph.json``) and the derived-context
  distills (``.claude/data/pyforge-scribe/move-list.json``, plus
  ``cocoindex-index.json`` when present). A member's declared files are its
  ONLY write roots: a manifest path that is not one of them is refused as a
  foreign-member path, so no pack can place a byte anywhere else.
* **The manifest**: per-file sha256 + size, the source commit, and the
  archive's own sha256 + size. ``render_manifest`` and ``parse_manifest``
  are the only writer and reader; the parser refuses an absolute path, a
  ``..``/``.``/empty segment, a backslash, a foreign-member path, a bad hex
  digest and a non-integer size as malformed.
* **The findings** every outcome maps to (MRS-CTX-003..007) and the argv the
  rebuild and fetch paths run -- rendered here, executed by the adapters.

It is pure -- no filesystem, no ``os``, no subprocess (AD-4, enforced by this
package's own import-linter contract). ``adapters/substrate_store.py`` owns
the hashing, the archive bytes and the install; ``adapters/scribe_cli.py``
owns every ``scribe`` subprocess; ``gh`` and ``codegraph`` run only through
``ProcessPort``.

**What the digests prove.** Integrity against the manifest, not
authenticity: the manifest and the archive come from the same release, so a
party able to replace one can replace both. That is a named limit of this
story, not a claim it makes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .model import Finding, Severity

__all__ = (
    "ASSET_ARCHIVE",
    "ASSET_MANIFEST",
    "DEFAULT_TAG",
    "MANIFEST_SCHEMA",
    "MANIFEST_SCHEMA_VERSION",
    "MEMBER_DERIVED_CONTEXT",
    "MEMBER_PLANNING_GRAPH",
    "MEMBER_STRUCTURE_GRAPH",
    "SCRIBE_GRAPH_COMPILE_ARGV",
    "SCRIBE_INDEX_REFRESH_ARGV",
    "STATE_FETCHED",
    "STATE_MISSING",
    "STATE_PRESENT",
    "STATE_REBUILT",
    "SUBSTRATE_MEMBERS",
    "ManifestError",
    "ManifestFile",
    "SubstrateManifest",
    "SubstrateMember",
    "check_archive_digest",
    "check_file_digest",
    "gap_finding",
    "member_by_name",
    "nothing_packable_finding",
    "parse_manifest",
    "path_problem",
    "rebuild_finding",
    "refused_pack_finding",
    "render_gh_download_argv",
    "render_manifest",
    "unevaluable_finding",
)

#: The two assets a published pack is made of. A pack is always the PAIR.
ASSET_MANIFEST = "substrate-manifest.json"
ASSET_ARCHIVE = "substrate.tar.gz"

#: The release tag the nightly publisher (``.github/workflows/
#: substrate-nightly.yml``) uploads to, with ``--clobber``, as a prerelease.
DEFAULT_TAG = "substrate-nightly"

MANIFEST_SCHEMA = "pyforge-marshal/substrate-manifest"
MANIFEST_SCHEMA_VERSION = 1

MEMBER_STRUCTURE_GRAPH = "structure-graph"
MEMBER_PLANNING_GRAPH = "planning-graph"
MEMBER_DERIVED_CONTEXT = "derived-context"

#: Per-member install states reported in the envelope.
STATE_PRESENT = "present"  # sentinel already in the clone -- untouched
STATE_FETCHED = "fetched"  # installed from a verified pack
STATE_REBUILT = "rebuilt"  # rebuilt locally, with a named MRS-CTX-003
STATE_MISSING = "missing"  # neither fetched nor rebuilt -- MRS-CTX-004

#: ``scribe`` argv tails for the two scribe-built members. The planning graph
#: is compiled first: ``index refresh`` upserts code nodes into the same
#: ``graph.json``, so running it before the compile would be overwritten.
SCRIBE_GRAPH_COMPILE_ARGV: tuple[str, ...] = ("graph", "compile", "--nightly")
SCRIBE_INDEX_REFRESH_ARGV: tuple[str, ...] = ("index", "refresh")

_REBUILD_CODEGRAPH = "codegraph"
_REBUILD_SCRIBE = "scribe"


@dataclass(frozen=True)
class SubstrateMember:
    """One substrate member: its sentinel, its other (optional) files, and
    how it is rebuilt. ``files`` is the member's complete write-root set."""

    name: str
    sentinel: str
    optional: tuple[str, ...]
    rebuild_tool: str
    rebuild_args: tuple[str, ...]

    @property
    def files(self) -> tuple[str, ...]:
        return (self.sentinel, *self.optional)

    def rebuild_command(self) -> str:
        """The rebuild command as an operator would type it from the repo
        root -- the text MRS-CTX-003/-004 name."""
        if self.rebuild_tool == _REBUILD_CODEGRAPH:
            return "codegraph init -y <repo-root>"
        return " ".join((self.rebuild_tool, *self.rebuild_args))


#: In rebuild order: the structure graph is independent; the planning graph
#: precedes the distills (see ``SCRIBE_GRAPH_COMPILE_ARGV``).
SUBSTRATE_MEMBERS: tuple[SubstrateMember, ...] = (
    SubstrateMember(
        name=MEMBER_STRUCTURE_GRAPH,
        sentinel=".codegraph/codegraph.db",
        optional=(),
        rebuild_tool=_REBUILD_CODEGRAPH,
        rebuild_args=("init", "-y"),
    ),
    SubstrateMember(
        name=MEMBER_PLANNING_GRAPH,
        sentinel=".claude/data/pyforge-scribe/graph.json",
        optional=(),
        rebuild_tool=_REBUILD_SCRIBE,
        rebuild_args=SCRIBE_GRAPH_COMPILE_ARGV,
    ),
    SubstrateMember(
        name=MEMBER_DERIVED_CONTEXT,
        sentinel=".claude/data/pyforge-scribe/move-list.json",
        optional=(".claude/data/pyforge-scribe/cocoindex-index.json",),
        rebuild_tool=_REBUILD_SCRIBE,
        rebuild_args=SCRIBE_INDEX_REFRESH_ARGV,
    ),
)

_MEMBERS_BY_NAME: dict[str, SubstrateMember] = {member.name: member for member in SUBSTRATE_MEMBERS}

_HEX64 = re.compile(r"[0-9a-f]{64}")


def member_by_name(name: str) -> SubstrateMember | None:
    return _MEMBERS_BY_NAME.get(name)


class ManifestError(ValueError):
    """A manifest that cannot be trusted to drive an install. The message is
    the reason MRS-CTX-005 reports."""


@dataclass(frozen=True)
class ManifestFile:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class SubstrateManifest:
    source_commit: str
    archive_sha256: str
    archive_size: int
    members: tuple[tuple[str, tuple[ManifestFile, ...]], ...]

    def member_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.members)

    def files_of(self, member: str) -> tuple[ManifestFile, ...]:
        for name, files in self.members:
            if name == member:
                return files
        return ()

    def file_index(self) -> dict[str, tuple[str, ManifestFile]]:
        """Archive entry name -> (owning member, expected file)."""
        return {entry.path: (name, entry) for name, files in self.members for entry in files}


def path_problem(path: object, member: SubstrateMember) -> str | None:
    """Why ``path`` may not be written for ``member`` -- ``None`` when safe.

    Safe means: a relative POSIX path with no empty, ``.`` or ``..``
    segment, no backslash or NUL, and one of the member's own declared
    files (anything else is a foreign-member path)."""
    if not isinstance(path, str) or not path:
        return f"member {member.name!r} lists an empty or non-string path"
    if path.startswith("/") or re.match(r"[A-Za-z]:", path):
        return f"member {member.name!r} lists an absolute path {path!r}"
    if "\\" in path or "\x00" in path:
        return f"member {member.name!r} lists a path with a backslash or NUL {path!r}"
    if any(segment in ("", ".", "..") for segment in path.split("/")):
        return f"member {member.name!r} lists a path with an empty, '.' or '..' segment {path!r}"
    if path not in member.files:
        return f"member {member.name!r} lists a foreign-member path {path!r} (allowed: {list(member.files)!r})"
    return None


def _digest_problem(value: object, where: str) -> str | None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        return f"{where} sha256 is not 64 lowercase hex digits"
    return None


def _size_problem(value: object, where: str) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return f"{where} size is not a non-negative integer"
    return None


def render_manifest(
    *,
    source_commit: str,
    archive_sha256: str,
    archive_size: int,
    members: Mapping[str, Sequence[ManifestFile]],
) -> str:
    """The manifest's canonical JSON text (sorted keys, files sorted by
    path, trailing newline). Refuses anything ``parse_manifest`` would."""
    document = {
        "schema": MANIFEST_SCHEMA,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "source_commit": source_commit,
        "archive": {"name": ASSET_ARCHIVE, "sha256": archive_sha256, "size": archive_size},
        "members": {
            name: {
                "files": [
                    {"path": entry.path, "sha256": entry.sha256, "size": entry.size}
                    for entry in sorted(files, key=lambda item: item.path)
                ]
            }
            for name, files in members.items()
        },
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    parse_manifest(text)
    return text


def parse_manifest(text: str) -> SubstrateManifest:
    """Parse and validate a manifest; raise ``ManifestError`` naming the
    first problem. Nothing here is lenient: a manifest that is wrong in any
    field drives no install at all."""
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ManifestError(f"manifest is not JSON ({exc})") from exc
    if not isinstance(document, dict):
        raise ManifestError("manifest is not a JSON object")
    if document.get("schema") != MANIFEST_SCHEMA:
        raise ManifestError(f"manifest schema is {document.get('schema')!r}, expected {MANIFEST_SCHEMA!r}")
    if document.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            f"manifest schema_version is {document.get('schema_version')!r}, expected {MANIFEST_SCHEMA_VERSION}"
        )
    source_commit = document.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit:
        raise ManifestError("manifest source_commit is missing or not a string")

    archive = document.get("archive")
    if not isinstance(archive, dict):
        raise ManifestError("manifest archive block is missing")
    if archive.get("name") != ASSET_ARCHIVE:
        raise ManifestError(f"manifest archive name is {archive.get('name')!r}, expected {ASSET_ARCHIVE!r}")
    for problem in (_digest_problem(archive.get("sha256"), "archive"), _size_problem(archive.get("size"), "archive")):
        if problem is not None:
            raise ManifestError(problem)

    raw_members = document.get("members")
    if not isinstance(raw_members, dict) or not raw_members:
        raise ManifestError("manifest members block is missing or empty")
    seen_paths: set[str] = set()
    members: list[tuple[str, tuple[ManifestFile, ...]]] = []
    for name in sorted(raw_members):
        member = member_by_name(name)
        if member is None:
            raise ManifestError(f"manifest names an unknown member {name!r}")
        block = raw_members[name]
        raw_files = block.get("files") if isinstance(block, dict) else None
        if not isinstance(raw_files, list) or not raw_files:
            raise ManifestError(f"member {name!r} lists no files")
        files: list[ManifestFile] = []
        for raw in raw_files:
            if not isinstance(raw, dict):
                raise ManifestError(f"member {name!r} has a file entry that is not an object")
            path = raw.get("path")
            problem = (
                path_problem(path, member)
                or _digest_problem(raw.get("sha256"), f"member {name!r} file {path!r}")
                or _size_problem(raw.get("size"), f"member {name!r} file {path!r}")
            )
            if problem is not None:
                raise ManifestError(problem)
            assert isinstance(path, str)
            if path in seen_paths:
                raise ManifestError(f"manifest lists {path!r} twice")
            seen_paths.add(path)
            files.append(ManifestFile(path=path, sha256=raw["sha256"], size=raw["size"]))
        if member.sentinel not in {entry.path for entry in files}:
            raise ManifestError(f"member {name!r} omits its sentinel {member.sentinel!r}")
        members.append((name, tuple(sorted(files, key=lambda item: item.path))))
    return SubstrateManifest(
        source_commit=source_commit,
        archive_sha256=archive["sha256"],
        archive_size=archive["size"],
        members=tuple(members),
    )


def check_archive_digest(manifest: SubstrateManifest, *, sha256: str, size: int) -> str | None:
    """Why the archive's measured bytes do not match the manifest, or ``None``."""
    if size != manifest.archive_size:
        return f"{ASSET_ARCHIVE} is {size} bytes, the manifest says {manifest.archive_size}"
    if sha256 != manifest.archive_sha256:
        return f"{ASSET_ARCHIVE} sha256 {sha256} does not match the manifest's {manifest.archive_sha256}"
    return None


def check_file_digest(expected: ManifestFile, *, sha256: str, size: int) -> str | None:
    """Why one extracted file does not match its manifest entry, or ``None``."""
    if size != expected.size:
        return f"{expected.path} is {size} bytes, the manifest says {expected.size}"
    if sha256 != expected.sha256:
        return f"{expected.path} sha256 {sha256} does not match the manifest's {expected.sha256}"
    return None


def render_gh_download_argv(*, tag: str, repo: str | None, dest_dir: str) -> tuple[str, ...]:
    """``gh release download`` for exactly the pair. ``repo`` omitted means
    gh resolves the repository from the clone's own remote."""
    argv: list[str] = ["gh", "release", "download", tag]
    if repo:
        argv += ["--repo", repo]
    argv += ["--pattern", ASSET_MANIFEST, "--pattern", ASSET_ARCHIVE, "--dir", dest_dir]
    return tuple(argv)


# --- findings -----------------------------------------------------------


def rebuild_finding(member: SubstrateMember, *, fetch_reason: str) -> Finding:
    """MRS-CTX-003 (WARN): a member was rebuilt locally. Names the command
    run and why the fetch did not serve that member -- never silent."""
    return Finding(
        code="MRS-CTX-003",
        severity=Severity.WARN,
        message=(
            f"substrate member {member.name!r} rebuilt locally with `{member.rebuild_command()}` -- "
            f"the fetch did not serve it: {fetch_reason}"
        ),
        path=member.sentinel,
    )


def unevaluable_finding(member: SubstrateMember, *, fetch_reason: str, rebuild_reason: str) -> Finding:
    """MRS-CTX-004 (UNEVALUABLE): a member neither fetched nor rebuilt."""
    return Finding(
        code="MRS-CTX-004",
        severity=Severity.ERROR,
        message=(
            f"substrate member {member.name!r} is neither fetched nor rebuilt -- the fetch did not "
            f"serve it ({fetch_reason}) and `{member.rebuild_command()}` failed: {rebuild_reason}"
        ),
        path=member.sentinel,
    )


def refused_pack_finding(reason: str, *, path: str | None) -> Finding:
    """MRS-CTX-005 (WARN): a digest mismatch, malformed manifest or unsafe
    archive entry. Nothing from the pack was installed."""
    return Finding(
        code="MRS-CTX-005",
        severity=Severity.WARN,
        message=f"substrate pack refused, nothing installed from it: {reason}",
        path=path,
    )


def gap_finding(member: SubstrateMember, *, reason: str) -> Finding:
    """MRS-CTX-006 (WARN): ``context pack`` wrote the pair without a member
    the producer could not supply (``reason`` says why -- its sentinel is
    absent, or is not a regular file)."""
    return Finding(
        code="MRS-CTX-006",
        severity=Severity.WARN,
        message=f"substrate member {member.name!r} not packed ({reason}) -- the pair was written without it",
        path=member.sentinel,
    )


def nothing_packable_finding(*, write_error: str | None = None) -> Finding:
    """MRS-CTX-007 (UNEVALUABLE): no pair was written -- no member is
    present, or (``write_error``) writing the pair itself failed."""
    if write_error is not None:
        message = f"the substrate pair could not be written -- no pair written: {write_error}"
    else:
        message = (
            "no substrate member is present ("
            + ", ".join(member.sentinel for member in SUBSTRATE_MEMBERS)
            + " all absent) -- nothing to pack, no pair written"
        )
    return Finding(code="MRS-CTX-007", severity=Severity.ERROR, message=message, path=None)
