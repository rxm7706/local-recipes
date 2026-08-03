"""``marshal gate evaluate`` (Story 2.1, FR-20, AD-4/AD-14/AD-17/AD-26) --
the standalone verify-command runner: resolves the active project's
policy-declared ``verify_commands`` allowlist exactly like ``marshal
config`` resolves its own project layer, runs each configured command
through the injected ``ProcessPort``, and folds the outcomes into Marshal's
verdict lattice via ``core/gate.py``'s pure classification.

**Why there is no arbitrary-command flag, and no ``--project-policy``
(AD-17).** Verify commands run ONLY from ``EffectivePolicy.verify_commands``
composed from the CONVENTIONAL project-policy path -- there is deliberately
no other execution channel on this command, so AD-17's allowlist-only rule
holds structurally, not by a runtime check.

``marshal config`` additionally accepts ``--project-policy PATH`` to compose
against a policy file anywhere on disk. That flag is deliberately ABSENT
here, and must not be added: ``config`` only PRINTS the policy it reads,
whereas ``gate evaluate`` EXECUTES its ``verify_commands``. An arbitrary
path is therefore exactly the ad-hoc command channel AD-17 forbids -- it
would run a file outside ``_bmad-output/projects/`` while still reporting
``data["slug"]``, asserting a project scope the run never had, and FR-20's
"another project's gates never run" would hold for neither the slug nor the
file. (Review finding: it did exactly that, verified live -- a policy file
in ``/tmp`` declaring an arbitrary command ran it and reported ``clean``,
exit 0, under ``"slug": "pyforge-marshal"``.)

**Project-slug/policy resolution is IMPORTED, not reimplemented.**
``ENV_ACTIVE_PROJECT``, ``conventional_project_policy_path``,
``_read_project_policy``, and ``PolicyIOError`` all come from
``cli/config.py`` -- the SAME precedence (``--project`` flag, then
``$BMAD_ACTIVE_PROJECT``, then the empty string) and the SAME conventional
``_bmad-output/projects/<slug>/planning-artifacts/marshal-policy.toml``
lookup ``marshal config`` uses, so "another project's gates never run"
(FR-20) holds by construction rather than by a second, possibly-diverging
copy of that logic.

**Scope (AD-26/F-3).** With no ``--run`` supplied, this is a
policy-seed-only evaluation: ``data["scope"] == "policy-seed-only"`` plus a
``mid-run freezes not visible`` note -- AD-26's own resolution text calls
this "a complete, legitimate answer" on its own, since a live run's
mid-flight seed-field overrides (``core/journal``'s eventual fold) are not
visible to a standalone invocation. ``--run <id>`` is accepted as a CLI flag
for interface shape (matching the story's own eventual-behavior AC), but
since no journal-fold exists yet (``core/journal`` is Story 3.1/3.2, both
``backlog``), supplying it reports an explicit ``MRS-GATE-005``
``unevaluable`` finding naming the gap -- never a fabricated run-scoped
answer, never a crash -- and ``data["scope"]`` reflects that the request
could not be honored instead of claiming the ordinary policy-seed scope. A
future story swaps this stub branch for a real ``core.journal.fold`` call.

**The pure/impure split.** All ``shlex.split`` + ``ProcessPort.run`` I/O
happens HERE, at the CLI boundary; the per-command classification (pass,
fail, unresolvable, malformed) is delegated to ``core.gate.classify_outcome``
(AD-4: ``core/**`` may hold no ``subprocess``/``os``/``time``/``adapters``
import) -- mirrors ``cli/init.py::run_homes``'s own gather-here/
classify-in-core split against ``core/status.py``.

Not implemented here (see the spec's own Boundaries & Constraints/Never):
``--scope-check`` and any frozen-surface scope check (Story 2.3, itself
blocked on Story 3.2), and any further verdict-lattice/never-false-green
property test beyond correct use of the existing ``compute_verdict``/
``classify`` machinery (Story 2.2's scope). Redaction through
``core/egress.py`` does not apply here either -- ``ports/process.py`` is
explicitly carved out of AD-34's egress-port set (argv/environment to a
child process, and this CLI's own stdout, are inside Marshal's trust
boundary, not a durable/third-party sink).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
from collections.abc import Mapping
from pathlib import Path

from ..adapters.process_posix import PosixProcess, ProcessError
from ..core import gate, policy
from ..core.model import Finding, Severity, Status, build_envelope, status_for
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.process import ProcessPort
from .config import (
    ENV_ACTIVE_PROJECT,
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)


def add_gate_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``gate`` subcommand on ``main.py``'s subparser tree, with
    a nested ``evaluate`` action (matches the epics/architecture's literal
    ``marshal gate evaluate`` invocation shape and the PRD's ``marshal gate
    evaluate --scope-check`` example -- ``--scope-check`` itself is Story
    2.3, not implemented here; the nesting leaves room for it as a future
    flag on this same ``evaluate`` action rather than a new top-level
    command). ``required=True`` on the nested subparsers: a bare ``marshal
    gate`` with no action is a clean argparse usage error, not a silent
    no-op."""
    parser = subparsers.add_parser(
        "gate",
        help="Evaluate Marshal's gate (AD-17/AD-26).",
        description="Runs the active project's policy-declared checks and reports pass/fail.",
    )
    gate_subparsers = parser.add_subparsers(dest="gate_command", required=True)
    evaluate_parser = gate_subparsers.add_parser(
        "evaluate",
        help="Run the active project's policy-declared verify commands (FR-20).",
        description=(
            "Resolves the active project's policy exactly like `marshal config`, "
            "runs each configured verify command via ProcessPort, and reports "
            "pass/fail per command with captured stdout/stderr. With no --run "
            "supplied this is a policy-seed-only evaluation -- see data.scope."
        ),
    )
    evaluate_parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=f"The active project slug; falls back to ${ENV_ACTIVE_PROJECT} when omitted.",
    )
    # No --project-policy here, unlike `marshal config` -- see this module's
    # own docstring for why an arbitrary policy path on a command that RUNS
    # what it reads is the ad-hoc execution channel AD-17 forbids.
    evaluate_parser.add_argument(
        "--run",
        dest="run_id",
        default=None,
        metavar="RUN_ID",
        help=(
            "Fold a specific run's journal instead of a bare policy-seed "
            "evaluation. Not yet implemented (core/journal is a later story) "
            "-- reports MRS-GATE-005 naming the gap rather than ignoring "
            "this flag or crashing."
        ),
    )
    evaluate_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    evaluate_parser.set_defaults(handler=run_evaluate)


def run_evaluate(args: argparse.Namespace, *, process: ProcessPort | None = None) -> int:
    process = process if process is not None else PosixProcess()

    # Same is-not-None precedence as cli/config.py::run_config -- an
    # explicit `--project ""` must win over BMAD_ACTIVE_PROJECT (Python
    # truthiness would otherwise treat an empty flag value as "omitted" and
    # silently fall through to the env var).
    project_slug = (
        args.project if args.project is not None else os.environ.get(ENV_ACTIVE_PROJECT, "")
    )

    # The CONVENTIONAL path is the only policy source this command will
    # read -- `run_config`'s `--project-policy` override is deliberately not
    # offered here (see the module docstring). Resolution itself is reused,
    # not reimplemented, so "another project's gates never run" (FR-20)
    # holds by construction.
    #
    # Review finding: unlike run_config (which only ever PRINTS a
    # mis-resolved policy), this command RUNS the verify_commands a
    # traversal-shaped slug's file declares -- conventional_project_policy_
    # path builds the path by naive string interpolation with no traversal
    # check, so `--project '../../../../tmp/evil'` could read (and then
    # execute the contents of) a file outside `_bmad-output/projects/`. The
    # shape gate below runs BEFORE any filesystem touch, mirroring
    # `cli/init.py::run_preflight`'s own pre-I/O slug-shape check
    # (MRS-PREFLIGHT-010) -- an invalid slug skips the conventional-path
    # lookup entirely and falls through to `policy.compose()`, which
    # reports the malformed slug itself via the existing MRS-POLICY-006
    # (no new finding code needed).
    project_data: Mapping[str, object] = {}
    io_findings: list[Finding] = []
    policy_source: Path | None = None
    if project_slug and policy._is_valid_project_slug(project_slug):
        candidate = conventional_project_policy_path(project_slug)
        if candidate.is_file():
            policy_source = candidate
    if policy_source is not None:
        try:
            project_data = _read_project_policy(policy_source)
        except PolicyIOError as exc:
            io_findings.append(exc.finding)

    effective, policy_findings = policy.compose(
        project_slug=project_slug, project=project_data, flags={}
    )
    # io_findings FIRST: mirrors cli/config.py::run_config's own ordering --
    # an unreadable conventional policy file is the root CAUSE of every
    # "layer=default" symptom compose() then reports, so the operator
    # scanning top-down should meet cause before consequence.
    findings: list[Finding] = [*io_findings, *policy_findings]

    data: dict[str, object] = {"slug": project_slug}
    command_findings: list[Finding] = []

    if args.run_id is not None:
        # Stubbed, not implemented (spec Boundaries & Constraints/Never):
        # core/journal (Story 3.1/3.2) does not exist yet, so a run-scoped
        # answer cannot honestly be produced. Named explicitly rather than
        # silently ignoring --run or crashing; scope reflects the request
        # could not be honored (I/O matrix's own wording), distinct from the
        # ordinary policy-seed-only scope below.
        data["scope"] = "run-scope-unavailable"
        data["scope_note"] = (
            f"--run {args.run_id!r} was requested, but no run-journal fold "
            "exists yet (core/journal is Story 3.1/3.2, both backlog)"
        )
        command_findings.append(
            Finding(
                code="MRS-GATE-005",
                severity=Severity.ERROR,
                message=(
                    f"cannot honor --run {args.run_id!r}: no run-journal fold "
                    "exists yet -- see core/journal (Story 3.1/3.2, backlog)"
                ),
            )
        )
        data["commands"] = []
    else:
        # AD-26/F-3: the story's own preamble flags this note as the clause
        # a developer reading only the ACs could otherwise miss -- a
        # standalone evaluation folds the policy seed alone, so a mid-run
        # seed-field override (core/journal's eventual fold) is not visible
        # here. AD-26's own resolution text: this is "a complete, legitimate
        # answer" on its own, not a degraded one.
        data["scope"] = "policy-seed-only"
        data["scope_note"] = "mid-run freezes not visible"

        commands = effective.verify_commands.value
        if not commands:
            # MRS-GATE-004 asserts the allowlist is UNCONFIGURED. When an
            # error-class policy finding already explains why composition
            # fell back to bare defaults -- an unreadable or malformed
            # conventional policy file (MRS-POLICY-004), a malformed slug
            # (MRS-POLICY-006), a rejected layer (MRS-POLICY-002) -- that
            # assertion is false: the operator DID configure commands and
            # Marshal could not read them. Emitting it anyway misdirects
            # triage toward "add a verify command" when the real fix is the
            # policy file (review finding, verified live: a TOML syntax
            # error produced MRS-POLICY-004 and MRS-GATE-004 side by side).
            #
            # Suppressing it can never turn the run green: the finding that
            # replaces it is error-class by definition of this branch, so
            # compute_verdict already yields a non-ok verdict -- the same
            # ok-status gate cli/config.py::run_config uses before its own
            # side effects, for the same "Marshal could not determine what
            # the operator intended" reason. The I/O matrix's
            # "--project/env both omitted" row is unaffected: MRS-POLICY-005
            # is a WARN, so status stays OK and both findings still surface.
            if status_for(compute_verdict(findings)) is Status.OK:
                command_findings.append(gate.no_commands_configured_finding())
            data["commands"] = []
        else:
            reports: list[dict[str, object]] = []
            root = repo_root()
            for command in commands:
                try:
                    tokens = shlex.split(command)
                except ValueError as exc:
                    report, finding = gate.classify_outcome(
                        command,
                        None,
                        failure_code="MRS-GATE-003",
                        failure_reason=(
                            f"cannot parse verify command {command!r}: {exc}"
                        ),
                    )
                else:
                    try:
                        result = process.run(tokens, cwd=root)
                    except ProcessError as exc:
                        report, finding = gate.classify_outcome(
                            command,
                            None,
                            failure_code="MRS-GATE-002",
                            failure_reason=(
                                f"verify command {command!r} could not be run: {exc}"
                            ),
                        )
                    else:
                        report, finding = gate.classify_outcome(command, result)
                reports.append(report)
                if finding is not None:
                    command_findings.append(finding)
            data["commands"] = reports

    # Same "io/policy findings before per-command findings" ordering
    # rationale as above, one level up: the operator should meet policy-level
    # causes (an unreadable --project-policy, a malformed slug) before the
    # per-command consequences those causes can produce.
    findings = [*findings, *command_findings]

    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="gate evaluate", verdict=verdict_value, data=data, findings=tuple(findings)
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text(envelope.data, envelope.findings)

    # flush=True + the broken-pipe guard mirror cli/config.py::run_config
    # exactly -- see that function's comment for the full rationale (stdout
    # is block-buffered when piped/redirected, so an un-flushed write never
    # touches the fd inside this guard).
    try:
        print(rendered, flush=True)
    except UnicodeEncodeError:
        # Review finding: this command is the first to print ARBITRARY child
        # output, and adapters/process_posix.py decodes it with
        # errors="replace" -- so a verify command emitting one undecodable
        # byte puts U+FFFD in the text render. When stdout's own encoding
        # cannot represent it (PYTHONIOENCODING=ascii, a non-UTF-8 locale),
        # print raises UnicodeEncodeError -- a ValueError, which main()'s
        # SystemExit/KeyboardInterrupt relay does NOT catch, so the
        # invocation would die on a traceback and lose its verdict-derived
        # exit code (observed: exit 1 for a gate that had really failed, 3).
        # Re-emit backslash-escaped rather than crash; a partial first write
        # may repeat a prefix, which is the right trade against losing the
        # verdict entirely. --format json needs no such guard (json.dumps
        # defaults to ensure_ascii=True).
        try:
            print(rendered.encode("ascii", "backslashreplace").decode("ascii"), flush=True)
        except OSError:
            _suppress_downstream_pipe_close()
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


def _render_text(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``cli/config.py``'s own
    ``_render_text`` convention -- no human-only information exists.

    Review finding: the captured ``stdout``/``stderr`` are included for
    every resolvable command, not just its ``returncode`` -- the AC's own
    wording is "pass/fail is reported per command **with captured output**",
    and ``--format text`` is the DEFAULT (``--format json`` is opt-in), so
    the default invocation must not silently discard the one piece of
    output an operator needs to diagnose why a command failed."""
    slug = data["slug"] or "(no active project)"
    lines = [f"gate evaluate: {slug}", f"scope: {data['scope']} ({data['scope_note']})"]
    commands = data.get("commands") or []
    if commands:
        lines.append("commands:")
        for entry in commands:
            if entry["resolvable"]:
                lines.append(f"  {entry['command']}: returncode={entry['returncode']}")
                if entry["stdout"]:
                    lines.append(f"    stdout: {entry['stdout']!r}")
                if entry["stderr"]:
                    lines.append(f"    stderr: {entry['stderr']!r}")
            else:
                lines.append(f"  {entry['command']}: unresolvable")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
