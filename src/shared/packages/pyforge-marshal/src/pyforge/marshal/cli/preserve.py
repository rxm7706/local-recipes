"""``marshal preserve tag|list`` (Story 87.3) over ``pyforge.core.preserve_refs``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyforge.core.cutover_root import resolve_flags_path
from pyforge.core.flags import disabled_help, require
from pyforge.core.preserve_refs import (
    PRESERVE_PRODUCERS,
    PreserveGitError,
    PreserveRefConflictError,
    PreserveRefError,
    PreserveState,
    PreserveTrailers,
    list_preserves,
    render_preserve_ref,
    snapshot_worktree_commit,
    tag_preserve,
)
from pyforge.core.process import PosixProcess

from ..core.model import Finding, Severity, Verdict, build_envelope
from ..core.verdict import EXIT_USAGE, compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root

PRESERVE_FLAG_KEY = "pyforge.marshal.preserve_refs"

_HELP = "Write and list local preserve tags (AD-81 preserve namespace)."


def add_preserve_subparser(subparsers: argparse._SubParsersAction) -> None:
    flags_path = resolve_flags_path()
    if flags_path is None:
        help_text = f"{_HELP} [disabled: flag {PRESERVE_FLAG_KEY} is off]"
    else:
        help_text = disabled_help(_HELP, PRESERVE_FLAG_KEY, flags_path=flags_path)
    parser = subparsers.add_parser(
        "preserve",
        help=help_text,
        description=help_text,
    )
    subs = parser.add_subparsers(dest="preserve_command", required=True)
    tag_p = subs.add_parser("tag", help="Snapshot a worktree and write one local annotated preserve tag.")
    tag_p.add_argument("--story", nargs=2, metavar=("SLUG", "N.M"), help="BMAD project slug and story key.")
    tag_p.add_argument(
        "--producer",
        required=True,
        choices=sorted(PRESERVE_PRODUCERS),
        help="Closed producer vocabulary (Story 87.3).",
    )
    tag_p.add_argument("--from", dest="from_path", required=True, help="Git worktree to snapshot.")
    tag_p.add_argument(
        "--provenance",
        choices=("machine", "human"),
        default="human",
        help="Preserve-Provenance trailer (default: human).",
    )
    tag_p.add_argument("--reason", default="hand", help="Preserve-Reason trailer.")
    tag_p.add_argument("--source", default="", help="Preserve-Source trailer (defaults to --from path).")
    tag_p.add_argument("--run", default="", help="Preserve-Run trailer.")
    tag_p.add_argument("--journal", default="", help="Preserve-Journal trailer.")
    tag_p.set_defaults(handler=run_preserve_tag, preserve_subcommand="tag")

    list_p = subs.add_parser("list", help="List local preserve tags.")
    list_p.add_argument("--format", choices=("text", "json"), default="text")
    list_p.add_argument("--station", help="Filter by project slug.")
    list_p.add_argument("--story", help="Filter by story key (N.M).")
    list_p.add_argument("--producer", choices=sorted(PRESERVE_PRODUCERS), help="Filter by producer.")
    list_p.add_argument("--state", choices=("open", "landed"), help="Filter by derived state.")
    list_p.set_defaults(handler=run_preserve_list, preserve_subcommand="list")


def _require_flag() -> None:
    require(PRESERVE_FLAG_KEY)


def run_preserve_tag(args: argparse.Namespace) -> int:
    _require_flag()
    worktree = Path(args.from_path).resolve()
    if not _is_git_worktree(worktree):
        print(f"marshal preserve tag: not a git worktree: {worktree}", file=sys.stderr)
        return EXIT_USAGE
    slug, story = (None, None) if args.story is None else (args.story[0], args.story[1])
    try:
        commit = snapshot_worktree_commit(worktree)
        if commit is None:
            commit = _head_sha(worktree)
        refname = render_preserve_ref(
            commit_sha=commit,
            producer=args.producer,
            project_slug=slug,
            story_key=story,
        )
        trailers = PreserveTrailers(
            producer=args.producer,
            provenance=args.provenance,
            reason=args.reason,
            source=args.source or str(worktree),
            run=args.run,
            journal=args.journal,
            commit=commit,
        )
        result = tag_preserve(worktree, refname=refname, commit=commit, trailers=trailers)
    except PreserveRefConflictError as exc:
        print(f"marshal preserve tag: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except (PreserveRefError, PreserveGitError) as exc:
        print(f"marshal preserve tag: {exc}", file=sys.stderr)
        return exit_code_for(Verdict.ERROR)
    payload = {"refname": result.refname, "commit": result.commit, "noop": result.noop}
    print(json.dumps(payload, sort_keys=True))
    return 0


def run_preserve_list(args: argparse.Namespace) -> int:
    _require_flag()
    root = repo_root()
    state = PreserveState(args.state) if args.state else None
    try:
        records = list_preserves(
            root,
            station=args.station,
            story=args.story,
            producer=args.producer,
            state=state,
        )
    except (PreserveRefError, PreserveGitError) as exc:
        findings = (
            Finding(
                code="MRS-PRESERVE-001",
                severity=Severity.ERROR,
                message=str(exc),
            ),
        )
        envelope = build_envelope(
            command="preserve list",
            verdict=compute_verdict(findings),
            data={"preserves": []},
            data_version=1,
            findings=findings,
        )
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return exit_code_for(Verdict.ERROR)
    rows = [
        {
            "refname": r.refname,
            "commit": r.object_sha,
            "station": r.project_slug,
            "story": r.story_key,
            "producer": r.producer,
            "sha8": r.sha8,
            "state": r.state.value,
            "trailers": {
                "Preserve-Producer": r.trailers.producer,
                "Preserve-Provenance": r.trailers.provenance,
                "Preserve-Reason": r.trailers.reason,
                "Preserve-Source": r.trailers.source,
                "Preserve-Run": r.trailers.run,
                "Preserve-Journal": r.trailers.journal,
                "Preserve-Commit": r.trailers.commit,
            },
        }
        for r in records
    ]
    if args.format == "json":
        envelope = build_envelope(
            command="preserve list",
            verdict=compute_verdict(()),
            data={"preserves": rows},
            data_version=1,
            findings=(),
        )
        try:
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True))
        except OSError:
            _suppress_downstream_pipe_close()
        return 0
    for row in rows:
        print(f"{row['refname']}\t{row['state']}\t{row['commit']}")
    return 0


def _is_git_worktree(worktree: Path) -> bool:
    if (worktree / ".git").exists():
        return True
    result = PosixProcess().run(["git", "rev-parse", "--git-dir"], cwd=worktree)
    return result.returncode == 0


def _head_sha(worktree: Path) -> str:
    result = PosixProcess().run(["git", "rev-parse", "HEAD"], cwd=worktree)
    if result.returncode != 0:
        raise PreserveGitError(result.stderr.strip() or "git rev-parse HEAD failed")
    return result.stdout.strip()
