"""The ``doctor`` console-script entry point.

Story 1.5 wires the ``check`` subcommand (FR-9/NFR-4): ``--engines``/
``--env`` compose Story 1.2/1.4's gather functions (``sources.warden.gather``,
``checks.env_hygiene.gather``) and Story 1.3's ``checks.registry``
(catalog + single-check filter) into one human-readable-or-``--json``
``DoctorReport``, exiting via ``verdict.exit_code_for``. ``monitor``/
``diagnose`` are not wired yet -- those land with their own epics.

``main`` always RETURNS an int; it never calls an exit primitive itself
(``verdict.py`` is the sole module permitted to do that -- the
sole-ownership meta-test enforces it), so any ``if __name__ == "__main__":``
guard must wrap the call in ``raise SystemExit(main())`` rather than embed a
literal exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import traceback
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import jsonschema

from .checks import env_hygiene, registry
from .models import DoctorReport, DoctorStatus, Finding, Source
from .sources import warden as warden_source
from .verdict import EXIT_SIGINT, exit_code_for

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant -- see models.py's module docstring for the taxonomy rationale),
# so the version string duplicates pyproject.toml's version literal here
# instead. Acceptable at scaffold stage; keep the two in sync by hand.
__version__ = "0.1.0"

# --engines/--env's nargs="?" sentinel: present with NO value ("--engines"
# alone) means "run the whole category"; present WITH a value means "run
# just that named check". Distinct object identity -- never confusable with
# a real check name (a plain string) or with the flag's absent-default
# (None).
_WHOLE_CATEGORY = object()


def _build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    parser = argparse.ArgumentParser(
        prog="doctor",
        description=(
            "Pre-flight + fleet-watch diagnostics for the pyforge factory."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser(
        "check",
        help="run pre-flight diagnostics (engine availability + env hygiene)",
    )
    check.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target directory to check (default: current directory)",
    )
    check.add_argument(
        "--engines",
        nargs="?",
        const=_WHOLE_CATEGORY,
        default=None,
        metavar="NAME",
        help=(
            "run the 'engines' category (pyforge-warden's self-check); an "
            "optional NAME runs just that named check (see --list)"
        ),
    )
    check.add_argument(
        "--env",
        nargs="?",
        const=_WHOLE_CATEGORY,
        default=None,
        metavar="NAME",
        help=(
            "run the 'env' category (credential-hygiene scan); an optional "
            "NAME runs just that named check (see --list)"
        ),
    )
    check.add_argument(
        "--list",
        action="store_true",
        help=(
            "list the full check catalog as text and exit -- never "
            "gathers/runs anything (ignores --engines/--env/--json/path)"
        ),
    )
    check.add_argument(
        "--json",
        action="store_true",
        help="emit one schema-valid DoctorReport document on stdout",
    )
    # Deliberately NO --version on this subparser: verified live against
    # `pyforge.warden.cli.main(["scan", "--version"])` (an argparse usage
    # error, exit 2) -- --version stays top-level only, mirroring warden's
    # own convention exactly (see the story spec's Design Notes).
    return parser, check


def _validate_check_names(
    args: argparse.Namespace, check_parser: argparse.ArgumentParser
) -> None:
    """A NAME given to ``--engines``/``--env`` must be a cataloged check for
    that category -- an unknown name is an argparse usage error (``.error()``,
    exit 2) raised HERE, before ``gather_one`` is ever called (resolves both
    prior stories' "validate vs pass through" deferral).

    Skipped entirely when ``--list`` is given: ``--list``'s own contract is
    to ignore ``--engines``/``--env``/``--json``/``path`` and never gather
    anything (review finding) -- validating a name it will never act on
    would make ``doctor check --list --engines <bad-name>`` a usage error
    instead of the promised catalog listing.

    A NAME rejected here that also happens to be an existing path is very
    likely a path-argument-ordering mistake, not a typo'd check name: the
    ``--engines``/``--env`` flags use ``nargs="?"`` so they can optionally
    take a value, which makes them structurally ambiguous with an adjacent
    bare positional ``path`` in argparse's own token matching (confirmed
    empirically during review -- e.g. ``doctor check --engines /some/dir``
    parses ``/some/dir`` as the check NAME, not the scan target). The error
    message names this specific, discoverable cause rather than leaving an
    operator to guess why a real path was rejected as an "unknown check
    name" (review finding)."""
    if args.list:
        return
    for category, value in (("engines", args.engines), ("env", args.env)):
        if value is None or value is _WHOLE_CATEGORY:
            continue
        known_names = sorted(
            spec.name for spec in registry.list_checks(category=category)
        )
        if value not in known_names:
            hint = ""
            # `value and`: an empty NAME (`--engines=`) must not hint --
            # Path("") normalizes to Path(".") which exists, so the bare
            # truthiness guard is load-bearing, not cosmetic (review
            # finding). shlex.quote: the suggested command must survive a
            # copy-paste even when the path embeds whitespace/newlines
            # (review finding).
            if value and Path(value).exists():
                hint = (
                    f" -- {value!r} looks like a path: if you meant to set "
                    "the scan target, place it BEFORE --engines/--env, e.g. "
                    f"`doctor check {shlex.quote(value)} --{category}`"
                )
            check_parser.error(
                f"argument --{category}: unknown check name {value!r} "
                f"(known: {', '.join(known_names)}){hint}"
            )


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code -- never raises ``SystemExit``
    itself. Exit codes stay inside Doctor's frozen ``{0, 2, 130}`` domain
    (AD-2): argparse's own ``--version``/``--help`` exits (``0``) and usage
    errors (``2``) are caught and returned as plain ints, and a
    ``KeyboardInterrupt`` during parsing returns the SIGINT constant.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser, check_parser = _build_parser()
    try:
        try:
            args = parser.parse_args(argv)
            _validate_check_names(args, check_parser)
        except SystemExit as exc:
            # argparse exits itself: --version/--help -> 0, a usage error
            # -> 2 (never 0). Surface its code as a return value, never
            # re-raised -- a non-int code (argparse never produces one
            # under this parser config) falls back to 2, still inside the
            # guarded domain. This mapping is ONLY for the parse/validate
            # phase: a SystemExit raised during dispatch is NOT argparse's
            # and lands in the outer handler below instead (review
            # finding: `SystemExit(None)` from a component calling bare
            # `sys.exit()` inside a gather would otherwise map to 0 here
            # -- a crashed run reporting success).
            if exc.code is None:
                return 0
            if isinstance(exc.code, int) and exc.code in {0, 2, 130}:
                return exc.code
            # Any other int (or non-int, e.g. a message string) is clamped
            # to 2 -- defense in depth for a future argparse action that
            # might exit with something outside Doctor's frozen {0, 2, 130}
            # domain (AD-2).
            return 2
        # `check` is the only registered subcommand today -- args.command is
        # always "check" past this point (subparsers is required=True with no
        # other subparser registered). Dispatch stays INSIDE the outer try:
        # a gather call is real multi-second work (the whole point of this
        # story), so a Ctrl-C during `_run_check` -- not just during parsing
        # -- must also return EXIT_SIGINT rather than escape as a raw
        # KeyboardInterrupt (main() never raises -- see its own docstring).
        return _run_check(args)
    except KeyboardInterrupt:
        return EXIT_SIGINT
    except SystemExit:
        # Exit-code sole ownership (mirrors warden's cli.py): argparse's
        # own exits were already handled at the parse phase above, so a
        # SystemExit reaching here was raised INSIDE dispatch -- a
        # component calling sys.exit (even sys.exit(0)) must never dictate
        # the verb's verdict. Its carried code is not trusted; projected as
        # an internal error (review finding).
        _stderr(
            "doctor: internal error: SystemExit raised inside dispatch "
            "(exit-code sole-ownership violation); any partial stdout "
            "must not be consumed"
        )
        return 2
    except Exception as exc:  # noqa: BLE001 -- last-resort net, mirrors
        # pyforge-warden's cli.py: an internal defect (e.g. a future
        # schema/model drift tripping _emit_json's jsonschema.validate
        # self-check) must never surface as the interpreter's default exit
        # 1 or an UNCAUGHT traceback -- it would violate this module's own
        # documented {0, 2, 130} exit-code domain (AD-2) (review finding).
        # The formatted traceback IS deliberately emitted to stderr first,
        # exactly as warden's net does -- Doctor's consumers are unattended
        # loop agents whose only diagnostic surface is stderr, and a bare
        # one-line repr (e.g. `ValidationError(...)`) is undiagnosable
        # without the failing frame (review finding).
        _stderr("".join(traceback.format_exception(exc)).rstrip("\n"))
        _stderr(f"doctor: internal error: {exc!r}")
        return 2


def _gather_engines(name: object, target: Path) -> tuple[Finding, ...]:
    """Findings for the "engines" category: the whole suite, or one named
    check filtered from it. ``gather_one`` returning ``None`` for a
    (already-validated) name can ONLY mean the category degraded to
    warden's all-or-nothing sentinel -- ``sources.warden.gather`` never
    partially succeeds -- so render one synthetic FAIL ``Finding`` naming
    the degradation, never a bare "not found" (story spec Design Notes)."""
    if name is _WHOLE_CATEGORY:
        return warden_source.gather(target)
    finding = registry.gather_one("engines", name, target)
    if finding is not None:
        return (finding,)
    return (
        Finding(
            source=Source.WARDEN_DOCTOR,
            check=name,
            status=DoctorStatus.FAIL,
            message=(
                f"check {name!r} did not run -- the 'engines' category "
                "degraded (pyforge-warden absent, unimportable, or its "
                "self-check crashed); re-run `doctor check --engines` "
                "(no name) to see the full degradation reason"
            ),
            evidence={},
        ),
    )


def _gather_env(name: object, target: Path) -> tuple[Finding, ...]:
    """Findings for the "env" category: the whole suite, or one named check
    filtered from it. ``env_hygiene.gather`` is ADDITIVE, never
    sentinel-replacing -- ``gather_one`` returning ``None`` here is the
    ordinary "clean, no match" outcome, not a degradation, so it yields zero
    Findings, never a synthetic one (the asymmetric complement of
    ``_gather_engines`` above; see the story spec's Design Notes for why the
    two categories are NOT handled uniformly)."""
    if name is _WHOLE_CATEGORY:
        return env_hygiene.gather(target)
    finding = registry.gather_one("env", name, target)
    return (finding,) if finding is not None else ()


def _run_check(args: argparse.Namespace) -> int:
    if args.list:
        return _render_list()

    target = Path(args.path)
    run_engines = args.engines is not None
    run_env = args.env is not None
    if not run_engines and not run_env:
        # Neither flag given -> both categories run (FR-2), each as the
        # WHOLE category -- args.engines/args.env are still None here (the
        # "flag absent" default, distinct from _WHOLE_CATEGORY, the "flag
        # given with no value" const), so the sentinel must be substituted
        # explicitly rather than forwarded as-is.
        run_engines = run_env = True
        engines_name: object = _WHOLE_CATEGORY
        env_name: object = _WHOLE_CATEGORY
    else:
        engines_name = args.engines
        env_name = args.env

    findings: tuple[Finding, ...] = ()
    if run_engines:
        findings += _gather_engines(engines_name, target)
    if run_env:
        findings += _gather_env(env_name, target)

    # Computed BEFORE emission: a stdout write failure must never replace
    # the already-computed exit code (mirrors warden's cli.py discipline).
    exit_code = exit_code_for(findings)
    if args.json:
        _emit_json(findings)
    else:
        _emit_text(findings)
    return exit_code


def _render_list() -> int:
    lines = [f"{spec.category}\t{spec.name}" for spec in registry.list_checks()]
    _write_stdout("\n".join(lines) + "\n")
    return 0


def _report_schema() -> dict:
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "report-schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _emit_json(findings: tuple[Finding, ...]) -> None:
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at=datetime.now(UTC).isoformat(),
        findings=findings,
    )
    document = report.to_json_dict()
    # Self-validated BEFORE it ever reaches stdout -- a schema-invalid
    # document must never be the one thing an automated caller (Marshal)
    # consumes as the contract.
    jsonschema.validate(document, _report_schema())
    _write_stdout(json.dumps(document, sort_keys=True, indent=2) + "\n")


def _single_line(text: str) -> str:
    """Neutralize embedded line breaks so one finding's ``message`` can
    never fabricate extra ``_emit_text`` lines (mirrors warden's
    ``report.py::_single_line`` -- its own Story 1.8 review finding, and a
    review finding here too). ``Finding.message`` is free text with no
    no-newline guarantee -- env-hygiene messages embed scanned file paths
    verbatim, and a path may legally contain ``\\n``, which would otherwise
    render as a second, indistinguishable-from-real finding line and desync
    the header's ``N finding(s)`` count."""
    return text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def _emit_text(findings: tuple[Finding, ...]) -> None:
    ok = sum(1 for f in findings if f.status is DoctorStatus.OK)
    warn = sum(1 for f in findings if f.status is DoctorStatus.WARN)
    fail = sum(1 for f in findings if f.status is DoctorStatus.FAIL)
    lines = [
        f"doctor check: {len(findings)} finding(s) -- "
        f"{ok} ok, {warn} warn, {fail} fail"
    ]
    for finding in findings:
        lines.append(
            f"  [{finding.source.value}] {finding.check}: "
            f"{finding.status.value} -- {_single_line(finding.message)}"
        )
    _write_stdout("\n".join(lines) + "\n")


def _stderr(message: str) -> None:
    """Print one stderr diagnostic, absorbing any stream failure (mirrors
    warden's ``cli.py``'s own ``_stderr`` idiom)."""
    try:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001 -- absorb everything, see docstring
        pass


def _write_stdout(text: str) -> None:
    """Write ``text`` to stdout, absorbing a ``BrokenPipeError`` (the
    consumer vanished, e.g. ``| head``) and any other stdout ``OSError``/
    ``ValueError`` -- the caller's exit code is already computed and must
    never be replaced by a stdout emission failure (mirrors warden's
    ``cli.py``, specifically its ``_run_doctor``'s rendering block).
    ``sys.stdout`` can legitimately be ``None`` (e.g. a detached/frozen
    process) -- guarded the same way the sibling ``_stderr`` already guards
    ``sys.stderr`` (review finding: this guard was missing here)."""
    if sys.stdout is None:
        return
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        _absorb_broken_pipe()
    except (OSError, ValueError) as exc:
        _stderr(
            f"doctor: stdout emission failed ({exc.__class__.__name__}); "
            "any partial stdout must not be consumed"
        )


def _absorb_broken_pipe() -> None:
    """The stdout consumer vanished mid-emission (e.g. ``| head``): the
    exit code is already computed, so the pipe error is absorbed -- never a
    traceback. Mirrors warden's ``cli.py::_absorb_broken_pipe`` exactly:
    process-stream path (``sys.stdout`` IS ``sys.__stdout__``) re-points fd 1
    at ``os.devnull``; swapped-stream path (test captures, embedders) closes
    the stream object instead."""
    stream = sys.stdout
    if stream is sys.__stdout__:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(devnull, stream.fileno())
            finally:
                os.close(devnull)
        except (OSError, ValueError, AttributeError):
            pass
        return
    try:
        stream.close()
    except Exception:  # noqa: BLE001 -- best effort, see docstring above
        pass


if __name__ == "__main__":
    raise SystemExit(main())
