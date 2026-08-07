"""``marshal check`` (Story 5.6, FR-65/AD-50) -- a NEW top-level command
that routes to the repo's OWN existing detector registry
(``scripts/detectors.py``, repo root, not part of this package) through
Marshal's front door, never a reimplementation. That script's own module
docstring explains why it exists: on 2026-07-31 this repo had three
disagreeing registries of its own detectors; ``scripts/detectors.py``
discovers every ``*_check.py``/``check_*.py`` detector by scanning the
filesystem and pixi tasks, fails on the registry's OWN gaps (a detector
declaring itself but missing a pixi task, or vice versa), and runs the
selected subset, reporting each one's ``pass``/``FINDINGS``/``unknown``
outcome. Reachable only as a standalone pixi task before this story, an
operator working through ``marshal`` had to remember a second, unrelated
command existed -- this closes that gap by shelling out to it and folding
its own ``registry``/``results`` payload into Marshal's envelope, exactly
the pattern ``cli/status.py``'s own ``_gather_unpushed_work_findings``
already established for ``scripts/unpushed_work_check.py`` (Story 5.5,
AD-48): ``ProcessPort.run`` via ``sys.executable`` (never a bare
``"python3"``, that story's own review finding -- a bare name resolved off
``PATH`` can silently be a DIFFERENT interpreter, or absent entirely, in a
pixi/conda env whose activated shell doesn't expose that exact name), a
bounded timeout, and "malformed/unavailable is reported, never silently
treated as clean."

``--scope`` mirrors ``scripts/detectors.py``'s own ``--scope`` values
(``repo``/``runtime``/``all``, default ``all``) 1:1 -- no scope
classification is re-derived here.

**Finding-code mapping (MRS-CHECK-*, a new domain -- one domain per CLI
module, this package's own established convention):** a detector reporting
``status == "FINDINGS"`` becomes one ``MRS-CHECK-002`` ERROR finding naming
it; a non-empty ``registry`` entry (the registry's own self-reported gap --
an undeclared or untasked detector) becomes one ``MRS-CHECK-003`` ERROR
finding per gap; a detector reporting ``status == "unknown"`` (could not
run) becomes one ``MRS-CHECK-004`` finding, classified
``Verdict.UNEVALUABLE`` (this package's own "could not determine," never
conflated with a confirmed failure) rather than ``ERROR``. A subprocess
launch failure, or output that does not parse as the expected JSON shape,
is ``MRS-CHECK-001`` -- WARN-tier, mirroring
``_gather_unpushed_work_findings``'s own ``MRS-STATUS-009`` "detector
unavailable" precedent exactly: never silently "no findings."

Story 5.6 also wires ``core/context.py::MarshalContext`` through
``cli/main.py``'s dispatch (see that module's own docstring): this
command's ``--project`` flag is consumed via the resolved
``context.slug`` as its PRIMARY source when a context is supplied
(``project``, for now the only field this command needs), falling back to
reading ``args.project`` directly when called without one (e.g. this
module's own unit tests, which construct ``run_check`` directly).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping

from ..adapters.process_posix import PosixProcess, ProcessError
from ..core.context import MarshalContext
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.process import ProcessPort
from .config import _suppress_downstream_pipe_close, repo_root

# The EXISTING, already-shipped repo-level detector registry (repo root,
# NOT part of this package) -- never a second, independently-maintained
# copy of its own discovery/scope-classification logic (AD-50).
_DETECTORS_SCRIPT_RELPATH = ("scripts", "detectors.py")

# A generous but bounded ceiling for the ONE subprocess call this command
# makes per invocation -- `scripts/detectors.py` itself bounds each
# INDIVIDUAL detector to 300s (its own `--timeout` default) and, with
# `--scope all`, can run several sequentially; this must be strictly
# larger than that per-detector ceiling or a legitimate multi-detector run
# would be killed here first. Mirrors `cli/status.py::
# _UNPUSHED_WORK_TIMEOUT_S`'s identical "bounded, never unbounded"
# rationale for its own single `ProcessPort.run` call, at a larger value
# for the same reason (this call can run many detectors, that one runs
# exactly one script).
_CHECK_TIMEOUT_S = 900.0

_MRS_CHECK_001 = "MRS-CHECK-001"
_MRS_CHECK_002 = "MRS-CHECK-002"
_MRS_CHECK_003 = "MRS-CHECK-003"
_MRS_CHECK_004 = "MRS-CHECK-004"


def add_check_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``check`` subcommand on ``main.py``'s subparser tree --
    a NEW top-level command, sibling to ``status``/``land``/``retire``."""
    parser = subparsers.add_parser(
        "check",
        help="Route to the repo's detector registry (scripts/detectors.py) through the front door (FR-65/AD-50).",
        description=(
            "Shells out to the EXISTING scripts/detectors.py --json "
            "--scope <repo|runtime|all> registry and folds its own "
            "registry/results payload into a Marshal envelope -- never a "
            "second, reimplemented detection mechanism."
        ),
    )
    parser.add_argument(
        "--scope",
        choices=("repo", "runtime", "all"),
        default="all",
        help=(
            "Mirrors scripts/detectors.py's own --scope 1:1: repo = "
            "CI-safe subset; runtime = host-state detectors (default: all)."
        ),
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=(
            "Optional project slug -- threaded through cli/main.py's "
            "resolved MarshalContext; informational only, since "
            "scripts/detectors.py itself is not project-scoped."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_check)


def _unavailable_finding(reason: str) -> Finding:
    """Mirrors ``cli/status.py::_gather_unpushed_work_findings``'s own
    ``MRS-STATUS-009`` "detector unavailable" precedent exactly: a
    subprocess launch failure or unparseable output is reported, never
    silently treated as "no findings."""
    return Finding(
        code=_MRS_CHECK_001,
        severity=Severity.WARN,
        message=(
            "the detector registry "
            f"({'/'.join(_DETECTORS_SCRIPT_RELPATH)}) could not be "
            f"consulted this run -- {reason} -- no detector findings are "
            "fabricated as clean"
        ),
    )


def _render_text_check(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14)."""
    lines = [f"check -- scope={data.get('scope')}"]
    results = data.get("results")
    if isinstance(results, list):
        for entry in results:
            if not isinstance(entry, dict):
                continue
            # Code review (2026-08-07, Edge Case Hunter): `.get(key,
            # default)` only substitutes when the key is ABSENT, not when
            # it's present with an explicit JSON `null` -- `f"{None:9}"`
            # raises `TypeError`, an unhandled crash out of `marshal
            # check`'s own DEFAULT output format for any malformed
            # detector-registry payload carrying `"status": null`/
            # `"name": null`. `or "?"` catches both "absent" and "None".
            status = entry.get("status") or "?"
            name = entry.get("name") or "?"
            secs = entry.get("secs", "?")
            summary = entry.get("summary", "")
            lines.append(f"  {status:9} {name:22} {secs}s  {summary}")
    registry = data.get("registry")
    if isinstance(registry, list) and registry:
        lines.append("registry gaps:")
        for gap in registry:
            lines.append(f"  - {gap}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(
    args: argparse.Namespace, data: dict[str, object], findings: list[Finding]
) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="check",
        verdict=verdict_value,
        data=data,
        data_version=1,
        findings=tuple(findings),
    )
    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text_check(envelope.data, envelope.findings)
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def run_check(
    args: argparse.Namespace,
    *,
    process: ProcessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    process = process if process is not None else PosixProcess()

    scope = getattr(args, "scope", "all")
    project = context.slug if context is not None else getattr(args, "project", None)

    root = repo_root()
    script_path = root.joinpath(*_DETECTORS_SCRIPT_RELPATH)

    data: dict[str, object] = {
        "project": project,
        "scope": scope,
        "registry": [],
        "results": [],
    }
    findings: list[Finding] = []

    try:
        result = process.run(
            # sys.executable, never a bare "python3" -- Story 5.5's own
            # review finding, see this module's own docstring.
            [sys.executable, str(script_path), "--json", "--scope", scope],
            cwd=root,
            timeout_s=_CHECK_TIMEOUT_S,
        )
    except ProcessError as exc:
        findings.append(_unavailable_finding(f"the script could not be launched ({exc})"))
        return _emit(args, data, findings)

    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        findings.append(_unavailable_finding("its stdout did not parse as JSON"))
        return _emit(args, data, findings)

    registry = payload.get("registry") if isinstance(payload, dict) else None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(registry, list) or not isinstance(results, list):
        findings.append(
            _unavailable_finding(
                "its JSON output did not carry the expected registry/results shape"
            )
        )
        return _emit(args, data, findings)

    data["registry"] = registry
    data["results"] = results

    for gap in registry:
        findings.append(
            Finding(
                code=_MRS_CHECK_003,
                severity=Severity.ERROR,
                message=f"registry gap: {gap}",
            )
        )

    for entry in results:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "<unknown>")
        status = entry.get("status")
        summary = entry.get("summary", "")
        if status == "FINDINGS":
            findings.append(
                Finding(
                    code=_MRS_CHECK_002,
                    severity=Severity.ERROR,
                    message=f"detector {name!r} reported findings -- {summary}",
                )
            )
        elif status == "unknown":
            findings.append(
                Finding(
                    code=_MRS_CHECK_004,
                    severity=Severity.ERROR,
                    message=f"detector {name!r} could not run (unknown) -- {summary}",
                )
            )
        elif status != "pass":
            # Code review (2026-08-07, Edge Case Hunter): a missing,
            # `None`, or unrecognized `status` (a typo, a future value, a
            # corrupted response) previously fell through both branches
            # with NO finding raised -- silently folded in as if it were
            # `"pass"`, contradicting this module's own repeated "malformed
            # is reported, never silently clean" discipline (already
            # applied at the whole-payload level via `_unavailable_
            # finding`, but not per-entry until now).
            findings.append(
                Finding(
                    code=_MRS_CHECK_001,
                    severity=Severity.WARN,
                    message=(
                        f"detector {name!r} reported an unrecognized status "
                        f"{status!r} -- not one of 'pass'/'FINDINGS'/"
                        "'unknown', never silently treated as clean"
                    ),
                )
            )

    return _emit(args, data, findings)
