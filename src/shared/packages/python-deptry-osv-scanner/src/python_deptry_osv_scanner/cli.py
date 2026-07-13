"""The real argparse CLI + scan orchestration (Story 1.2).

(The scaffold stub's docstring credited this to Story 4.1 — stale; the real
CLI landed with 1.2. Renderers proper are Story 1.8; typed errors 1.7; full
discovery 1.9.)

Ownership decisions recorded:

* Stream discipline (NFR-I3): in ``--format json`` stdout carries EXACTLY
  one schema-valid ``ComplianceReport`` document or NOTHING; every
  diagnostic — including the empty-scan-set notice — goes to stderr.
  ``--format text`` emits ONE non-contract summary line.
* Exit codes come ONLY from ``verdict.exit_code_for`` / ``verdict.
  EXIT_SIGINT`` (the sole-ownership rule). argparse's own exits
  (``--version``/``--help`` → 0, usage errors → 2, never 0) surface via the
  caught ``SystemExit``'s code — a variable, never a literal.
* ``--deterministic`` is accepted as a DOCUMENTED NO-OP: the 1.2 report
  carries no volatile fields, so default output is already byte-identical;
  volatile-field pinning arrives with ``determinism.py``.
* Early-fatal boundary: an empty/whitespace path (which would otherwise
  Path-normalize to ``"."`` and silently scan the CWD) or a nonexistent/
  undiscoverable target (not an existing directory) emits a stderr
  diagnostic and exits ``exit_code_for(error)`` with stdout EMPTY — no
  report exists to emit. Every failure PAST that boundary still emits the
  report: the exit code is orthogonal to emission.
* Error taxonomy (only genuine manifest problems are labeled
  ``unparsable-manifest``): a structurally-broken manifest raises
  ``UnparsableManifestError`` and an OS failure READING the manifest
  (chmod-000, TOCTOU deletion) is also a manifest problem (the OS error
  rides in the message). Everything else on the discovery/extract/routing
  path — an unknown manifest kind, an unexpected ``ValueError``, a
  discovery ``OSError`` — is ``internal-error``. Each yields a typed
  ``ErrorRecord`` + an error rung; the report is emitted (status
  ``error``, exit ``exit_code_for(error)``).
* Error-status drivers use the ``error:<kind>:<subject>`` grammar and do
  NOT reference ``findings[]`` — the error report's driver is a dangling
  id by design (``findings`` may be empty; the report stays schema-valid).
  Story 1.7 (typed errors) owns the final error-driver grammar.
* ``KeyboardInterrupt`` ANYWHERE in ``main`` — argument parsing, the scan,
  or mid-emission — returns ``EXIT_SIGINT``; any partial stdout must not
  be consumed.
* ``BrokenPipeError`` during stdout emission is absorbed (the consumer went
  away, e.g. ``| head``): the report's already-computed exit code is still
  returned and no traceback contaminates stderr.
* Strictly non-interactive: no prompts, stdin is never read.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .discovery import discover
from .engines import registered_engines
from .extract import UnparsableManifestError, extractor_for
from .interfaces import DefaultPolicy
from .inventory import Component, ResolvedInventory, merge_components
from .models import (
    AXIS_VULNERABILITY,
    ErrorKind,
    ErrorRecord,
    Status,
    StatusDriver,
)
from .report import TOOL_NAME, assemble_report, render_json
from .routing import DefaultRouter
from .verdict import EXIT_SIGINT, exit_code_for


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Unified dependency-hygiene + vulnerability scanner emitting one "
            "schema-validated ComplianceReport and a strict exit-code gate."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser(
        "scan", help="scan a project directory and emit the compliance report"
    )
    scan.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target directory to scan (default: current directory)",
    )
    scan.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help=(
            "output format: 'json' emits the ComplianceReport document "
            "(the contract) on stdout; 'text' emits one non-contract "
            "summary line (default: text)"
        ),
    )
    scan.add_argument(
        "--deterministic",
        action="store_true",
        help=(
            "byte-identical output mode — currently a documented no-op: the "
            "report carries no volatile fields yet, so default output is "
            "already byte-identical (volatile-field pinning arrives with "
            "determinism.py)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    try:
        parser = _build_parser()
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:
            # argparse exits itself: --version/--help -> 0, usage error -> 2
            # (never 0). Surface its code as a return value — a caught
            # variable, never an exit literal.
            return 0 if exc.code is None else int(exc.code)
        return _run_scan(args)
    except KeyboardInterrupt:
        # This handler wraps ALL of main — parse_args included — so no
        # interrupt window escapes as a traceback. Emission may already have
        # partially happened, so the honest claim is consumption guidance,
        # never "no report emitted".
        print(
            f"{TOOL_NAME}: interrupted (SIGINT); any partial stdout must "
            "not be consumed",
            file=sys.stderr,
        )
        return EXIT_SIGINT


def _run_scan(args: argparse.Namespace) -> int:
    if not args.path.strip():
        # "" Path-normalizes to "." — an empty/whitespace target must be
        # early-fatal, never a silent scan of the CWD.
        print(
            f"{TOOL_NAME}: scan target {args.path!r} is empty — not an "
            "existing directory",
            file=sys.stderr,
        )
        return exit_code_for(Status.ERROR)
    target = Path(args.path)
    if not target.is_dir():
        print(
            f"{TOOL_NAME}: scan target {args.path!r} is not an existing "
            "directory",
            file=sys.stderr,
        )
        return exit_code_for(Status.ERROR)

    components: list[Component] = []
    errors: list[ErrorRecord] = []
    rungs: list[tuple[Status, StatusDriver | None]] = []
    manifests_parsed = 0
    try:
        manifests = discover(target)
    except OSError as exc:
        # Discovery propagates non-absence stat failures: a permission-denied
        # target must never read as "no manifest" (a false green). Report
        # still emitted; the exit code is orthogonal to emission.
        manifests = ()
        _record_error(
            errors,
            rungs,
            kind=ErrorKind.INTERNAL_ERROR,
            owner="discovery",
            subject=args.path,
            message=(
                f"discovery failed under {args.path!r}: "
                f"[errno {exc.errno}] {exc}"
            ),
        )
    else:
        if not manifests:
            # The not-applicable path says so on stderr; stdout stays pure.
            print(
                f"{TOOL_NAME}: no manifest found under {args.path!r}; "
                "nothing to scan",
                file=sys.stderr,
            )
    router = DefaultRouter()
    for manifest in manifests:
        try:
            # extractor_for lives INSIDE the guarded region: an unknown
            # manifest kind is an internal-error report, never a crash.
            extractor = extractor_for(manifest.kind, router)
            extracted = extractor.extract(target / manifest.path, manifest)
        except UnparsableManifestError as exc:
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.UNPARSABLE_MANIFEST,
                owner="extract",
                subject=manifest.path,
                message=str(exc),
            )
        except OSError as exc:
            # Reading the manifest failed (chmod-000, TOCTOU deletion): a
            # genuine manifest problem, with the OS error stated.
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.UNPARSABLE_MANIFEST,
                owner="extract",
                subject=manifest.path,
                message=f"unreadable manifest {manifest.path}: {exc}",
            )
        except ValueError as exc:
            # Anything else out of the extract/routing path is NOT a
            # manifest problem — never misdiagnose an internal bug as a
            # broken user manifest.
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.INTERNAL_ERROR,
                owner="extract",
                subject=manifest.path,
                message=f"internal error extracting {manifest.path}: {exc}",
            )
        else:
            components.extend(extracted)
            manifests_parsed += 1

    inventory = ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=manifests,
    )
    engine_results = tuple(
        engine.run(target, inventory) for engine in registered_engines()
    )
    for result in engine_results:
        errors.extend(result.errors)
    findings, policy_rungs = DefaultPolicy().evaluate(inventory, engine_results)
    rungs.extend(policy_rungs)

    report = assemble_report(
        inventory=inventory,
        findings=findings,
        rungs=rungs,
        errors=tuple(errors),
        manifests_found=len(manifests),
        manifests_parsed=manifests_parsed,
    )
    try:
        if args.format == "json":
            sys.stdout.write(render_json(report) + "\n")
        else:
            print(
                f"{TOOL_NAME}: status={report.status.value} "
                f"exit_code={report.exit_code} findings={len(report.findings)}"
            )
    except BrokenPipeError:
        _absorb_broken_pipe()
    return report.exit_code


def _record_error(
    errors: list[ErrorRecord],
    rungs: list[tuple[Status, StatusDriver | None]],
    *,
    kind: ErrorKind,
    owner: str,
    subject: str,
    message: str,
) -> None:
    """Surface one operational error: typed record + error rung + stderr
    diagnostic. The rung's driver id uses the ``error:<kind>:<subject>``
    grammar and deliberately does NOT reference ``findings[]`` (see the
    module docstring; Story 1.7 owns the final grammar)."""
    errors.append(ErrorRecord(kind=kind, owner=owner, message=message))
    rungs.append(
        (
            Status.ERROR,
            StatusDriver(
                axis=AXIS_VULNERABILITY, finding_id=f"error:{kind}:{subject}"
            ),
        )
    )
    print(f"{TOOL_NAME}: {message}", file=sys.stderr)


def _absorb_broken_pipe() -> None:
    """The stdout consumer vanished mid-emission (e.g. ``| head``): the
    verdict's exit code is already computed, so the pipe error is absorbed —
    never a traceback. Stdout is re-pointed at ``os.devnull`` so the
    interpreter's exit-time flush cannot raise a second BrokenPipeError."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)
    except (OSError, ValueError):
        # No real file descriptor behind sys.stdout (e.g. an in-memory test
        # capture): nothing will flush at interpreter exit, nothing to do.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
