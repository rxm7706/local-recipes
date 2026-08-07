"""``marshal upstream`` (Story 6.8, FR-58, AD-2) -- a NEW top-level,
read-only command reporting this project's own tracked upstream
contribution register: every known `bmad-loop`-shaped gap, Marshal's own
compensating workaround, its upstream status, and the Marshal FR that
compensates while the gap is open (AD-2's "wrap, do not absorb" decision).

Mirrors ``cli/retire.py``'s own standalone-top-level-verb precedent rather
than nesting under ``marshal adapters`` -- this concern is not
adapter-specific (three of the five initial entries have nothing to do
with any one adapter profile).

The register file itself is hand-curated, tracked JSON -- ``run_upstream``
never writes it (mirrors the CFE-side ``cwe-seed-gap``/``spdx-schema-gap``
suggesters' own "the curated map stays hand-owned, git review decides"
precedent this repo's CLAUDE.md already documents for a sibling concern).
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

from ..adapters.fs_local import FsError, LocalFs
from ..core.model import Finding, Severity, build_envelope
from ..core.upstream import flagged_for_removal, parse_register
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from .config import _suppress_downstream_pipe_close, repo_root

if TYPE_CHECKING:
    from ..core.context import MarshalContext

# The ONE tracked register path -- self-referential to pyforge-marshal's
# own tracked planning artifacts, never per-project-parameterized (this
# register is inherently about MARSHAL's own upstream dependency, AD-2's
# own "binds: all").
_REGISTER_RELPATH = (
    "_bmad-output",
    "projects",
    "pyforge-marshal",
    "planning-artifacts",
    "upstream-register.json",
)


def add_upstream_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "upstream",
        help="Report the tracked upstream contribution register (FR-58).",
        description=(
            "Read-only: lists every tracked bmad-loop-shaped gap, Marshal's "
            "own compensating workaround, its upstream status, and the "
            "Marshal FR that compensates while the gap is open. A 'landed' "
            "entry flags its workaround for removal (AD-2). Never edits the "
            "register -- it is hand-curated, git review decides."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_upstream)


def _render_text(data: dict[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14)."""
    lines = ["upstream contribution register"]
    entries = data.get("entries")
    flagged_ids = {
        entry.get("id")
        for entry in data.get("flagged_for_removal", [])
        if isinstance(entry, dict)
    }
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            marker = "[FLAGGED] " if entry.get("id") in flagged_ids else ""
            lines.append(
                f"  {marker}{entry.get('id', '?'):36} status={entry.get('upstream_status', '?'):8} "
                f"compensating_fr={entry.get('compensating_fr', '?')}"
            )
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="upstream",
        verdict=verdict_value,
        data=data,
        data_version=1,
        findings=tuple(findings),
    )
    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text(envelope.data, envelope.findings)
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _entry_to_dict(entry) -> dict[str, object]:
    return {
        "id": entry.id,
        "gap": entry.gap,
        "workaround": entry.workaround,
        "compensating_fr": entry.compensating_fr,
        "upstream_status": entry.upstream_status,
        "note": entry.note,
    }


def run_upstream(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    """``marshal upstream`` (Story 6.8, FR-58): reads the ONE tracked
    register file, reports every entry plus the ``landed`` subset flagged
    for workaround removal. Never writes."""
    del context
    fs = fs if fs is not None else LocalFs()

    findings: list[Finding] = []
    data: dict[str, object] = {}

    root = repo_root()
    register_path = root
    for part in _REGISTER_RELPATH:
        register_path = register_path / part
    data["path"] = str(register_path)

    # `unreadable` (a real I/O failure -- e.g. permission-denied on a file
    # that genuinely exists) and `absent` (`read_text` returns `None`, no
    # exception) are two different facts about the register and must never
    # both be reported for the same run (review finding: an earlier draft
    # fell through to the `text is None` check below even after already
    # reporting the `FsError`, producing a second, factually wrong "is
    # absent" finding on a real read failure).
    unreadable = False
    try:
        text = fs.read_text(register_path)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-UPSTREAM-001",
                severity=Severity.WARN,
                message=f"cannot read the upstream contribution register {str(register_path)!r}: {exc}",
                path=str(register_path),
            )
        )
        text = None
        unreadable = True

    entries: tuple = ()
    if text is None:
        if not unreadable:
            findings.append(
                Finding(
                    code="MRS-UPSTREAM-001",
                    severity=Severity.WARN,
                    message=(
                        f"upstream contribution register {str(register_path)!r} is absent -- "
                        "treated as empty"
                    ),
                    path=str(register_path),
                )
            )
    else:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            findings.append(
                Finding(
                    code="MRS-UPSTREAM-001",
                    severity=Severity.WARN,
                    message=(
                        f"upstream contribution register {str(register_path)!r} is not valid JSON "
                        f"({exc}) -- treated as empty"
                    ),
                    path=str(register_path),
                )
            )
        else:
            entries, errors = parse_register(raw)
            for error in errors:
                findings.append(
                    Finding(
                        code="MRS-UPSTREAM-001",
                        severity=Severity.WARN,
                        message=f"upstream contribution register {str(register_path)!r}: {error}",
                        path=str(register_path),
                    )
                )

    data["entries"] = [_entry_to_dict(entry) for entry in entries]

    landed = flagged_for_removal(entries)
    data["flagged_for_removal"] = [_entry_to_dict(entry) for entry in landed]
    if landed:
        summary = "; ".join(f"{entry.id} (compensating {entry.compensating_fr})" for entry in landed)
        findings.append(
            Finding(
                code="MRS-UPSTREAM-002",
                severity=Severity.WARN,
                message=(
                    f"{len(landed)} upstream gap(s) landed -- their compensating "
                    f"workaround(s) are flagged for review/removal: {summary}"
                ),
            )
        )

    return _emit(args, data, findings)
