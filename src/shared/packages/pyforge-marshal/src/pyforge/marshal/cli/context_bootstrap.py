"""``marshal context bootstrap`` / ``marshal context pack`` (Story 46.1,
spec-pyforge-marshal CAP-192) -- a bare clone opens on the shared substrate.

``bootstrap`` (also reached as ``pyforge context bootstrap`` through
pyforge-core's one-entry noun alias) makes every missing substrate member
present, fetch-first:

1. A member whose sentinel already exists is ``present`` and never touched.
2. The missing members are served from a published pack: by default the
   ``substrate-nightly`` release, downloaded with ``gh`` (the one network
   use, announced on stderr and recorded as ``data.source.network``);
   ``--from <dir>`` reads a local pair instead and ``--offline`` skips the
   fetch -- neither touches the network.
3. The pack is verified in full before anything is written
   (``adapters/substrate_store.py``); a refused pack is MRS-CTX-005 and
   installs nothing.
4. Every member the pack did not serve is rebuilt locally -- ``codegraph``
   through ``ProcessPort``, the two scribe members through
   ``adapters/scribe_cli.py`` -- and each rebuild is a WARN MRS-CTX-003
   naming the command and why the fetch did not serve it. A member neither
   fetched nor rebuilt is MRS-CTX-004 (UNEVALUABLE, exit 1).

``pack`` is the producer side: it writes the deterministic pair for every
member this checkout has (MRS-CTX-006 per absent member, MRS-CTX-007 when
there is nothing to pack). The nightly publisher
(``.github/workflows/substrate-nightly.yml``) runs it after building the
members and uploads the pair.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..adapters import substrate_store as store
from ..adapters.scribe_cli import ScribeCli
from ..core import substrate
from ..core.model import Finding, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..seed.verbs.kit import build_codegraph_index
from .config import _suppress_downstream_pipe_close, repo_root

__all__ = ("DEFAULT_PACK_DIR_RELPATH", "add_substrate_parsers", "run_context_bootstrap", "run_context_pack")

#: Where ``context pack`` writes the pair by default -- under the
#: blanket-gitignored ``.claude/data/``, derived and disposable.
DEFAULT_PACK_DIR_RELPATH = ".claude/data/pyforge-marshal/substrate-pack"

_ROOT_HELP = "Repo root to operate on (default: this checkout). Fixtures pass an isolated tree; live runs omit this."
_GIT_TIMEOUT_S = 30.0


def add_substrate_parsers(context_sub: argparse._SubParsersAction) -> None:
    """Register ``bootstrap`` and ``pack`` under ``marshal context``."""
    bootstrap = context_sub.add_parser(
        "bootstrap",
        help="Fetch-or-rebuild the shared substrate into this clone (Story 46.1).",
        description=(
            "Make every missing substrate member present -- the structure graph "
            "(.codegraph/codegraph.db), the planning graph and the derived-context "
            "distills. Fetches the published pair with `gh release download` "
            "(announced on stderr), verifies every digest, and installs only into "
            "absent members; whatever the fetch does not serve is rebuilt locally "
            "with a named finding. --offline and --from never touch the network."
        ),
    )
    source = bootstrap.add_mutually_exclusive_group()
    source.add_argument(
        "--from",
        dest="from_dir",
        default=None,
        metavar="DIR",
        help=f"Install from a local directory holding {substrate.ASSET_MANIFEST} + {substrate.ASSET_ARCHIVE} (no network).",
    )
    source.add_argument(
        "--offline",
        action="store_true",
        help="Never fetch: rebuild every missing member locally (no network).",
    )
    bootstrap.add_argument(
        "--tag",
        default=substrate.DEFAULT_TAG,
        help=f"Release tag holding the published pair (default: {substrate.DEFAULT_TAG}).",
    )
    bootstrap.add_argument(
        "--repo",
        default=None,
        metavar="OWNER/NAME",
        help="Repository to fetch from (default: gh resolves this clone's remote).",
    )
    bootstrap.add_argument("--root", default=None, metavar="PATH", help=_ROOT_HELP)
    bootstrap.add_argument("--format", choices=("text", "json"), default="text", help="Output format (default: text).")
    bootstrap.set_defaults(handler=run_context_bootstrap)

    pack = context_sub.add_parser(
        "pack",
        help="Write the deterministic substrate pair from this checkout (Story 46.1).",
        description=(
            f"Write {substrate.ASSET_ARCHIVE} and {substrate.ASSET_MANIFEST} (per-file "
            "sha256 + size, source commit, archive sha256) for every substrate member "
            "present here. Packing the same files twice yields the same archive bytes."
        ),
    )
    pack.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help=f"Output directory (default: <root>/{DEFAULT_PACK_DIR_RELPATH}).",
    )
    pack.add_argument(
        "--source-commit",
        default=None,
        metavar="SHA",
        help="Commit the members were built from (default: the root's git HEAD).",
    )
    pack.add_argument("--root", default=None, metavar="PATH", help=_ROOT_HELP)
    pack.add_argument("--format", choices=("text", "json"), default="text", help="Output format (default: text).")
    pack.set_defaults(handler=run_context_pack)


def _member_files(root: Path, member: substrate.SubstrateMember) -> list[str]:
    return [rel for rel in member.files if (root / rel).exists()]


def run_context_bootstrap(
    args: argparse.Namespace,
    *,
    process: ProcessPort | None = None,
    scribe: ScribeCli | None = None,
) -> int:
    """CLI entry for ``marshal context bootstrap``. ``process`` (``gh``,
    ``codegraph``) and ``scribe`` are injection seams for tests."""
    root = Path(args.root).resolve() if args.root else repo_root()
    runner: ProcessPort = process if process is not None else PosixProcess()
    scribe_cli = scribe if scribe is not None else ScribeCli(runner)
    findings: list[Finding] = []
    states = {
        member.name: substrate.STATE_PRESENT if store.member_present(root, member) else substrate.STATE_MISSING
        for member in substrate.SUBSTRATE_MEMBERS
    }
    missing = [name for name, state in states.items() if state == substrate.STATE_MISSING]
    source: dict[str, object] = {
        "kind": "none",
        "network": False,
        "tag": None,
        "repo": None,
        "dir": None,
        "source_commit": None,
    }
    not_served: dict[str, str] = {}

    if not missing:
        pass
    elif args.offline:
        source["kind"] = "offline"
        not_served = {name: "--offline was given, so no fetch was attempted" for name in missing}
    elif args.from_dir is not None:
        pack_dir = Path(args.from_dir).resolve()
        source.update(kind="local", dir=str(pack_dir))
        not_served = _serve_from(root, pack_dir, missing, findings, states, source)
    else:
        source.update(kind="release", network=True, tag=args.tag, repo=args.repo)
        print(
            f"marshal context bootstrap: fetching {substrate.ASSET_MANIFEST} + {substrate.ASSET_ARCHIVE} "
            f"from release {args.tag!r}"
            + (f" of {args.repo}" if args.repo else " of this clone's remote")
            + f" with `gh release download` (network) for: {', '.join(missing)}",
            file=sys.stderr,
            flush=True,
        )
        with tempfile.TemporaryDirectory(prefix="substrate-fetch-") as fetch_dir:
            reason = store.fetch_pair(runner, root=root, tag=args.tag, repo=args.repo, dest_dir=Path(fetch_dir))
            if reason is not None:
                not_served = {name: f"the fetch failed: {reason}" for name in missing}
            else:
                not_served = _serve_from(root, Path(fetch_dir), missing, findings, states, source)

    for member in substrate.SUBSTRATE_MEMBERS:
        if states[member.name] != substrate.STATE_MISSING:
            continue
        fetch_reason = not_served.get(member.name, "the pack did not serve it")
        failure = _rebuild(root, member, runner, scribe_cli)
        if failure is None:
            states[member.name] = substrate.STATE_REBUILT
            findings.append(substrate.rebuild_finding(member, fetch_reason=fetch_reason))
        else:
            findings.append(substrate.unevaluable_finding(member, fetch_reason=fetch_reason, rebuild_reason=failure))

    data: dict[str, object] = {
        "root": str(root),
        "source": source,
        "members": [
            {
                "name": member.name,
                "sentinel": member.sentinel,
                "state": states[member.name],
                "files": _member_files(root, member),
            }
            for member in substrate.SUBSTRATE_MEMBERS
        ],
    }
    return _emit("context bootstrap", args, findings, data)


def _serve_from(
    root: Path,
    pack_dir: Path,
    missing: list[str],
    findings: list[Finding],
    states: dict[str, str],
    source: dict[str, object],
) -> dict[str, str]:
    """Verify-and-install from a directory holding the pair. Returns the
    not-served reason for every missing member that is still missing."""
    manifest_path = pack_dir / substrate.ASSET_MANIFEST
    archive_path = pack_dir / substrate.ASSET_ARCHIVE
    absent = [
        name
        for name, path in ((substrate.ASSET_MANIFEST, manifest_path), (substrate.ASSET_ARCHIVE, archive_path))
        if not path.is_file()
    ]
    if absent:
        return {name: f"{pack_dir} holds no {' / '.join(absent)}" for name in missing}
    result = store.verify_and_install(root, manifest_path=manifest_path, archive_path=archive_path, members=missing)
    if result.refused is not None:
        findings.append(substrate.refused_pack_finding(result.refused, path=str(pack_dir)))
        return {name: f"the pack was refused ({result.refused})" for name in missing}
    if result.manifest is not None:
        source["source_commit"] = result.manifest.source_commit
    for name in result.installed:
        states[name] = substrate.STATE_FETCHED
    return dict(result.not_served)


def _rebuild(
    root: Path,
    member: substrate.SubstrateMember,
    runner: ProcessPort,
    scribe_cli: ScribeCli,
) -> str | None:
    """Rebuild one member locally. ``None`` when its sentinel now exists,
    else the reason it does not."""
    if member.name == substrate.MEMBER_STRUCTURE_GRAPH:
        failure = build_codegraph_index(root, stale=False, process=runner)
    else:
        outcome = scribe_cli.rebuild(repo_root=root, argv_tail=member.rebuild_args)
        failure = None if outcome.ok else outcome.reason
    if failure is not None:
        return failure
    if not store.member_present(root, member):
        return f"`{member.rebuild_command()}` exited 0 but {member.sentinel} does not exist"
    return None


def _source_commit(root: Path, runner: ProcessPort) -> str:
    try:
        result = runner.run(["git", "rev-parse", "HEAD"], cwd=root, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError:
        return "unknown"
    sha = (result.stdout or "").strip()
    return sha if result.returncode == 0 and sha else "unknown"


def run_context_pack(args: argparse.Namespace, *, process: ProcessPort | None = None) -> int:
    """CLI entry for ``marshal context pack``."""
    root = Path(args.root).resolve() if args.root else repo_root()
    runner: ProcessPort = process if process is not None else PosixProcess()
    out_dir = Path(args.out).resolve() if args.out else root / DEFAULT_PACK_DIR_RELPATH
    findings: list[Finding] = []
    packable: dict[str, tuple[str, ...]] = {}
    for member in substrate.SUBSTRATE_MEMBERS:
        files, reason = store.packable_files(root, member)
        if files:
            packable[member.name] = files
        else:
            findings.append(substrate.gap_finding(member, reason=reason or "not packable"))
    data: dict[str, object] = {"root": str(root), "out": str(out_dir)}
    if not packable:
        findings.append(substrate.nothing_packable_finding())
        return _emit("context pack", args, findings, data)
    source_commit = args.source_commit or _source_commit(root, runner)
    try:
        result = store.write_pack(root, out_dir, source_commit=source_commit, members=packable)
    except (OSError, ValueError) as exc:
        findings.append(substrate.nothing_packable_finding(write_error=str(exc)))
        return _emit("context pack", args, findings, data)
    data.update(
        source_commit=source_commit,
        manifest=str(result.manifest_path),
        archive=str(result.archive_path),
        archive_sha256=result.archive_sha256,
        archive_size=result.archive_size,
        members=[
            {"name": name, "files": [{"path": f.path, "sha256": f.sha256, "size": f.size} for f in files]}
            for name, files in result.members.items()
        ],
        absent=sorted({member.name for member in substrate.SUBSTRATE_MEMBERS} - set(packable)),
    )
    return _emit("context pack", args, findings, data)


def _emit(command: str, args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(command=command, verdict=verdict, data=data, findings=tuple(findings))
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            _print_text(command, data, findings, envelope.verdict)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_text(command: str, data: dict[str, object], findings: list[Finding], verdict: object) -> None:
    print(f"{command} verdict={verdict}")
    source = data.get("source")
    if isinstance(source, dict):
        print(f"source: {source.get('kind')} network={source.get('network')}")
    members = data.get("members")
    if isinstance(members, list):
        for member in members:
            if isinstance(member, dict):
                label = member.get("state") or f"{len(member.get('files') or [])} file(s)"
                print(f"  - {member.get('name')}: {label}")
    if data.get("archive_sha256"):
        print(f"archive: {data.get('archive')} sha256={data.get('archive_sha256')}")
    for finding in findings:
        print(f"{finding.code} {finding.severity.value}: {finding.message}")
