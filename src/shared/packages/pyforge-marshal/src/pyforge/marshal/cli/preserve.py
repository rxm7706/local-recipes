"""``marshal preserve tag|list|push|retire`` over ``pyforge.core.preserve_refs``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyforge.core.cutover_root import resolve_flags_path
from pyforge.core.flags import disabled_help, require
from pyforge.core.preserve_refs import (
    PRESERVE_PRODUCERS,
    ContentGateReason,
    PreserveGitError,
    PreserveRefConflictError,
    PreserveRefError,
    PreserveState,
    PreserveTrailers,
    list_pending_preserve_refs,
    list_preserves,
    parse_preserve_ref,
    push_preserve_ref,
    render_preserve_ref,
    snapshot_worktree_commit,
    tag_preserve,
)
from pyforge.core.process import PosixProcess

from ..core.model import Finding, Severity, Verdict, build_envelope
from ..core.verdict import EXIT_USAGE, compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root
from .preserve_retirements import append_retirement, load_retirements, retirements_path

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
    list_p.add_argument("--state", choices=("open", "landed", "retired"), help="Filter by derived state.")
    list_p.set_defaults(handler=run_preserve_list, preserve_subcommand="list")

    push_p = subs.add_parser("push", help="Push local preserve/archive tags through the content gate.")
    push_p.add_argument("tags", nargs="*", help="Tag refnames (default: none unless --pending).")
    push_p.add_argument(
        "--pending",
        action="store_true",
        help="Push every local preserve/archive tag not yet on origin.",
    )
    push_p.set_defaults(handler=run_preserve_push, preserve_subcommand="push")

    retire_p = subs.add_parser("retire", help="Record a preserve tag as retired (ledger only; no tag mutation).")
    retire_p.add_argument("tag", help="Full annotated preserve tag refname.")
    retire_p.add_argument("--evidence", required=True, help="Evidence line (e.g. story <slug> <N.M> done <sha>).")
    retire_p.set_defaults(handler=run_preserve_retire, preserve_subcommand="retire")


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
    if args.state == "retired":
        return _run_preserve_list_retired(args, root)
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


def _normalize_tag_ref(tag: str) -> str:
    if tag.startswith("refs/tags/"):
        return tag
    return f"refs/tags/{tag.removeprefix('refs/tags/')}"


def _finding_for_gate(reason: ContentGateReason, message: str) -> Finding:
    code = (
        "MRS-PRESERVE-003"
        if reason
        in (
            ContentGateReason.PUSH_CAP_RUN,
            ContentGateReason.PUSH_CAP_STORY,
        )
        else "MRS-PRESERVE-002"
    )
    return Finding(code=code, severity=Severity.ERROR, message=message)


def run_preserve_push(args: argparse.Namespace) -> int:
    _require_flag()
    root = repo_root()
    tags = [_normalize_tag_ref(t) for t in args.tags]
    if args.pending:
        try:
            tags = list_pending_preserve_refs(root)
        except PreserveGitError as exc:
            print(f"marshal preserve push: {exc}", file=sys.stderr)
            return exit_code_for(Verdict.ERROR)
    if not tags:
        print("marshal preserve push: no tags to push", file=sys.stderr)
        return EXIT_USAGE
    findings: list[Finding] = []
    pushed: list[str] = []
    run_push_count = 0
    story_push_counts: dict[str, int] = {}
    for refname in tags:
        try:
            result = push_preserve_ref(
                root,
                refname,
                run_push_count=run_push_count,
                story_push_counts=story_push_counts,
            )
        except (PreserveRefError, PreserveGitError) as exc:
            print(f"marshal preserve push: {exc}", file=sys.stderr)
            return exit_code_for(Verdict.ERROR)
        for gate in result.findings:
            findings.append(_finding_for_gate(gate.reason, gate.message))
            print(f"marshal preserve push: {gate.message}", file=sys.stderr)
        if result.pushed:
            pushed.append(refname)
            run_push_count += 1
            try:
                parsed = parse_preserve_ref(refname)
                if parsed.project_slug and parsed.story_key:
                    key = f"{parsed.project_slug}/{parsed.story_key}"
                    story_push_counts[key] = story_push_counts.get(key, 0) + 1
            except PreserveRefError:
                pass
    payload = {"pushed": pushed, "refused": [t for t in tags if t not in pushed]}
    print(json.dumps(payload, sort_keys=True))
    if findings and not pushed:
        return exit_code_for(Verdict.GATE_FAILED)
    if findings:
        return exit_code_for(Verdict.GATE_FAILED)
    return 0


def run_preserve_retire(args: argparse.Namespace) -> int:
    _require_flag()
    root = repo_root()
    tag = _normalize_tag_ref(args.tag)
    try:
        parse_preserve_ref(tag)
    except PreserveRefError as exc:
        print(f"marshal preserve retire: {exc}", file=sys.stderr)
        return EXIT_USAGE
    path = retirements_path(root)
    try:
        row = append_retirement(path, tag=tag, evidence=args.evidence)
    except ValueError as exc:
        print(f"marshal preserve retire: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps({"tag": row.tag, "evidence": row.evidence, "retired_at": row.retired_at}, sort_keys=True))
    return 0


def _run_preserve_list_retired(args: argparse.Namespace, root: Path) -> int:
    rows_out: list[dict[str, object]] = []
    for retirement in load_retirements(retirements_path(root)):
        station = story = producer = None
        try:
            parsed = parse_preserve_ref(retirement.tag)
            station = parsed.project_slug
            story = parsed.story_key
            producer = parsed.producer
        except PreserveRefError:
            pass
        if args.station is not None and station != args.station:
            continue
        if args.story is not None and story != args.story:
            continue
        if args.producer is not None and producer != args.producer:
            continue
        rows_out.append(
            {
                "refname": retirement.tag,
                "commit": None,
                "station": station,
                "story": story,
                "producer": producer,
                "state": PreserveState.RETIRED.value,
                "evidence": retirement.evidence,
                "retired_at": retirement.retired_at,
            }
        )
    if args.format == "json":
        envelope = build_envelope(
            command="preserve list",
            verdict=compute_verdict(()),
            data={"preserves": rows_out},
            data_version=1,
            findings=(),
        )
        print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True))
        return 0
    for listed in rows_out:
        print(f"{listed['refname']}\tretired\t{listed.get('evidence', '')}")
    return 0
