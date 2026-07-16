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
  caught ``SystemExit``'s code — ``None`` → success, an int passes through,
  and a non-int code (argparse never produces one under this parser config)
  projects via ``exit_code_for(error)``, never ``int()``-crashes.
* Last-resort net: any unexpected ``Exception`` escaping the scan (an
  internal defect, ``render_json``'s fail-loud self-validation, a crashing
  future engine hook) returns ``exit_code_for(error)`` with the traceback
  on stderr — NEVER the interpreter's default exit 1, which would collide
  with the ``indeterminate``/``policy-violation`` projection and read as
  "scan completed, findings found" to an exit-code-only CI consumer.
  ``SystemExit`` raised INSIDE the scan region (a component calling
  ``sys.exit`` — a sole-ownership violation, even ``sys.exit(0)``) is
  likewise projected to ``exit_code_for(error)``: nothing inside the scan
  may dictate the gate's exit, so its carried code is never trusted.
* ``--deterministic`` is accepted as a DOCUMENTED NO-OP: the 1.2 report
  carries no volatile fields, so default output is already byte-identical;
  volatile-field pinning arrives with ``determinism.py``.
* Early-fatal boundary: an empty/whitespace path (which would otherwise
  Path-normalize to ``"."`` and silently scan the CWD) or a nonexistent/
  undiscoverable target (not an existing directory) emits a stderr
  diagnostic and exits ``exit_code_for(error)`` with stdout EMPTY — no
  report exists to emit. The gate stats EXPLICITLY (``Path.is_dir()``
  swallows every ``OSError``): "could not look" (permission-denied parent,
  ELOOP) is diagnosed as could-not-stat, never as "not there". Every
  failure PAST that boundary still emits the report: the exit code is
  orthogonal to emission (a ``render_json`` self-validation failure is the
  recorded exception — an invalid report must not reach stdout, so the
  last-resort net returns the error exit with stdout empty).
* Error taxonomy (only genuine manifest problems are labeled
  ``unparsable-manifest``): a structurally-broken manifest raises
  ``UnparsableManifestError`` and an OS failure READING the manifest
  (chmod-000, TOCTOU deletion) is also a manifest problem (the errno is
  stated SYMBOLICALLY — ``EACCES`` — because strerror text is
  locale-dependent and ``OSError.__str__`` embeds the absolute path;
  report bytes must not vary by locale or scan location). Everything else
  on the discovery/extract/routing path — an unknown manifest kind, ANY
  unexpected exception out of an extractor (the extractor seam gets the
  same catch-all doctrine as the engine seam: 1.3+ plug implementations
  in), a discovery ``OSError`` — is ``internal-error``. A crashing engine
  constructor (instantiation is part of the seam) is
  ``engine-unavailable``; a crashing ``engine.run`` is
  ``engine-execution-failed``. Each yields a typed ``ErrorRecord`` + an
  error rung; the report is emitted (status ``error``, exit
  ``exit_code_for(error)``). Error-driver id segments are sanitized like
  component-derived segments (``_sanitize_id_segment``).
* Error-status drivers use the ``error:<kind>:<subject>`` grammar and do
  NOT reference ``findings[]`` — the error report's driver is a dangling
  id by design (``findings`` may be empty; the report stays schema-valid).
  Story 1.7 (typed errors) owns the final error-driver grammar.
* ``KeyboardInterrupt`` ANYWHERE in ``main`` — argument parsing, the scan,
  or mid-emission — returns ``EXIT_SIGINT``; any partial stdout must not
  be consumed.
* ``BrokenPipeError`` during stdout emission is absorbed (the consumer went
  away, e.g. ``| head``): the report's already-computed exit code is still
  returned and no traceback contaminates stderr. Stdout is FLUSHED inside
  the guarded region so a block-buffered pipe surfaces the error to the
  absorber instead of exploding at interpreter-exit flush (CPython exit
  120). Any OTHER stdout ``OSError`` (ENOSPC, EIO) is environmental, not
  an internal defect: absorbed with a stderr notice, computed exit code
  preserved. Stderr diagnostics absorb every write failure the same way
  (``_stderr`` — including ``ValueError`` on a CLOSED stderr, which
  ``print`` raises instead of ``OSError``; ``_stderr`` runs inside
  exception handlers, where a raise would escape ``main`` as interpreter
  exit 1) — a vanished diagnostic stream must not replace the computed
  exit code.
* Strictly non-interactive: no prompts, stdin is never read.
* ``has_locked_closure`` (Story 2.6): the extraction loop tracks
  ``parsed_kinds`` — the set of manifest KINDS that actually parsed, not
  just the count — and passes ``bool(parsed_kinds & {PIXI_LOCK_KIND,
  CONDA_LOCK_KIND})`` to ``assemble_report``. ``report.py`` has no
  lockfile-kind vocabulary of its own (that's ``discovery.py``'s domain),
  so the caller states the claim.
"""

from __future__ import annotations

import argparse
import errno as errno_module
import os
import stat as stat_module
import sys
import traceback
from pathlib import Path

from . import __version__
from .discovery import CONDA_LOCK_KIND, PIXI_LOCK_KIND, discover
from .engines import engine_factories
from .extract import UnparsableManifestError, extractor_for
from .interfaces import DefaultPolicy, EngineResult, _sanitize_id_segment
from .inventory import Component, ResolvedInventory, merge_components
from .models import (
    AXIS_VULNERABILITY,
    ErrorKind,
    ErrorRecord,
    Status,
    StatusDriver,
    VulnData,
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
            # variable, never an exit literal of the scan projection. A
            # non-int code (argparse never produces one under this parser
            # config) projects as an error, never an int() crash.
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            return exit_code_for(Status.ERROR)
        return _run_scan(args)
    except KeyboardInterrupt:
        # This handler wraps ALL of main — parse_args included — so no
        # interrupt window escapes as a traceback. Emission may already have
        # partially happened, so the honest claim is consumption guidance,
        # never "no report emitted".
        _stderr(
            f"{TOOL_NAME}: interrupted (SIGINT); any partial stdout must "
            "not be consumed"
        )
        return EXIT_SIGINT
    except SystemExit:
        # Exit-code sole ownership: argparse's own exits were already
        # handled at parse_args, so a SystemExit reaching here was raised
        # INSIDE the scan region — a component calling sys.exit (even
        # sys.exit(0)) must never dictate the gate's verdict. Its carried
        # code is not trusted; projected as an internal error.
        _stderr(
            f"{TOOL_NAME}: internal error: SystemExit raised inside the "
            "scan (exit-code sole-ownership violation); any partial "
            "stdout must not be consumed"
        )
        return exit_code_for(Status.ERROR)
    except Exception as exc:  # noqa: BLE001 — the last-resort net
        # An internal defect must NEVER surface as the interpreter's default
        # exit 1 (it collides with the indeterminate/policy-violation
        # projection) or as an uncaught traceback. Diagnostics to stderr;
        # stdout may hold a partial document, so the same consumption
        # guidance as SIGINT applies.
        _stderr("".join(traceback.format_exception(exc)).rstrip("\n"))
        _stderr(
            f"{TOOL_NAME}: internal error: {exc!r}; any partial stdout "
            "must not be consumed"
        )
        return exit_code_for(Status.ERROR)


def _run_scan(args: argparse.Namespace) -> int:
    if not args.path.strip():
        # "" Path-normalizes to "." — an empty/whitespace target must be
        # early-fatal, never a silent scan of the CWD.
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is empty — not an "
            "existing directory"
        )
        return exit_code_for(Status.ERROR)
    target = Path(args.path)
    # Explicit stat (is_dir() swallows every OSError): "could not look" is
    # diagnosed as could-not-stat, never as "not there".
    try:
        target_stat = target.stat()
    except (FileNotFoundError, NotADirectoryError):
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is not an existing "
            "directory"
        )
        return exit_code_for(Status.ERROR)
    except ValueError as exc:
        # A path with an embedded NUL (or otherwise unrepresentable to the OS)
        # raises ValueError, not OSError — a user-input error, not an internal
        # defect. Diagnose it here, not via main's last-resort traceback net.
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is not a valid path: {exc}"
        )
        return exit_code_for(Status.ERROR)
    except OSError as exc:
        _stderr(f"{TOOL_NAME}: cannot stat scan target {args.path!r}: {exc}")
        return exit_code_for(Status.ERROR)
    if not stat_module.S_ISDIR(target_stat.st_mode):
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} exists but is not a "
            "directory"
        )
        return exit_code_for(Status.ERROR)

    components: list[Component] = []
    errors: list[ErrorRecord] = []
    rungs: list[tuple[Status, StatusDriver | None]] = []
    manifests_parsed = 0
    parsed_kinds: set[str] = set()
    try:
        manifests = discover(target)
    except OSError as exc:
        # Discovery propagates non-absence stat failures: a permission-denied
        # target must never read as "no manifest" (a false green). Report
        # still emitted; the exit code is orthogonal to emission.
        manifests = ()
        # An OS-minted errno is stated SYMBOLICALLY (locale-independent,
        # no strerror text, no OSError.__str__ absolute path); discovery's
        # own fail-closed OSErrors carry no errno and their crafted message
        # is already deterministic.
        detail = (
            f"[errno {errno_module.errorcode.get(exc.errno, str(exc.errno))}] "
            f"{exc.__class__.__name__}"
            if exc.errno is not None
            else str(exc)
        )
        _record_error(
            errors,
            rungs,
            kind=ErrorKind.INTERNAL_ERROR,
            owner="discovery",
            subject=args.path,
            message=f"discovery failed under {args.path!r}: {detail}",
        )
    else:
        if not manifests:
            # The not-applicable path says so on stderr; stdout stays pure.
            _stderr(
                f"{TOOL_NAME}: no manifest found under {args.path!r}; "
                "nothing to scan"
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
            # genuine manifest problem. The errno is stated SYMBOLICALLY
            # (EACCES) — strerror text is locale-dependent and
            # OSError.__str__ embeds the absolute path; report bytes must
            # not vary by locale or scan location.
            code = (
                errno_module.errorcode.get(exc.errno, str(exc.errno))
                if exc.errno is not None
                else exc.__class__.__name__
            )
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.UNPARSABLE_MANIFEST,
                owner="extract",
                subject=manifest.path,
                message=(
                    f"unreadable manifest {manifest.path}: [errno {code}] "
                    f"{exc.__class__.__name__}"
                ),
            )
        except (SystemExit, Exception) as exc:  # noqa: BLE001 — the seam
            # doctrine applies to the EXTRACTOR seam exactly as to the
            # engine seam (1.3+ plug implementations into both): any other
            # exception out of the extract/routing path — unknown manifest
            # kind (ValueError), a 1.3+ extractor bug (TypeError,
            # KeyError), even a sys.exit — is NOT a manifest problem;
            # typed internal-error record, report STILL emitted, never a
            # traceback with no report (KeyboardInterrupt still
            # propagates).
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.INTERNAL_ERROR,
                owner="extract",
                subject=manifest.path,
                message=f"internal error extracting {manifest.path}: {exc!r}",
            )
        else:
            components.extend(extracted)
            manifests_parsed += 1
            parsed_kinds.add(manifest.kind)

    inventory = ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=manifests,
    )
    if manifests and manifests_parsed > 0 and not inventory.components:
        # A parsed manifest with nothing extractable is honest
        # not-applicable, but it must be distinguishable on stderr from the
        # empty-dir case (the coverage block already distinguishes them).
        # The wording names WHAT was scanned: a manifest whose deps live
        # only outside [project].dependencies (poetry table, extras,
        # dependency-groups) hits this path too, and "declares no
        # dependencies" would be a false claim for it (section-aware
        # discovery is Story 1.9's D2).
        _stderr(
            f"{TOOL_NAME}: manifest parsed but no dependencies found in "
            f"[project].dependencies (the only section scanned in 1.2) "
            f"under {args.path!r}; nothing to scan"
        )
    engine_results: list[EngineResult] = []
    # The engine seam runs only when a manifest actually parsed: with nothing
    # extractable (empty dir, or a manifest that failed to parse) there is no
    # project for a subprocess engine (deptry) to assess, and running it on an
    # absent/malformed manifest would only double the extractor's own error.
    engines_to_run = engine_factories() if manifests_parsed > 0 else ()
    for factory in engines_to_run:
        try:
            engine = factory()
        except (SystemExit, Exception) as exc:  # noqa: BLE001 —
            # instantiation is PART of the seam: a crashing constructor (a
            # misconfigured 1.3/1.5 runner) is the engine-unavailable
            # class — typed record + error rung, report STILL emitted,
            # never a traceback with no report.
            factory_name = getattr(factory, "__name__", repr(factory))
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.ENGINE_UNAVAILABLE,
                owner="engines",
                subject=factory_name,
                message=(
                    f"engine factory {factory_name!r} crashed at "
                    f"instantiation: {exc!r}"
                ),
            )
            continue
        try:
            engine_results.append(engine.run(target, inventory))
        except (SystemExit, Exception) as exc:  # noqa: BLE001 — the seam
            # doctrine: a crashing engine must yield a typed ErrorRecord +
            # error rung with the report STILL emitted, never a traceback
            # with no report — and a sys.exit-calling engine must never
            # dictate the process exit (sole ownership; SystemExit is
            # caught HERE so the report survives). KeyboardInterrupt still
            # propagates.
            engine_name = getattr(engine, "name", engine.__class__.__name__)
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=engine_name,
                subject=engine_name,
                message=f"engine {engine_name!r} crashed: {exc!r}",
            )
    for result in engine_results:
        errors.extend(result.errors)
    findings, policy_rungs = DefaultPolicy().evaluate(inventory, engine_results)
    rungs.extend(policy_rungs)

    # The first non-None vuln_data across engine results, in engine-
    # registration order (Story 1.5: OsvEngine populates it on a completed
    # 0/1 run; every other engine/path leaves it None) — else an all-None
    # VulnData (no vulnerability-axis DB was consulted at all).
    vuln_data = next(
        (result.vuln_data for result in engine_results if result.vuln_data is not None),
        VulnData(source=None, snapshot_at=None, max_age_ok=None),
    )
    report = assemble_report(
        inventory=inventory,
        findings=findings,
        rungs=rungs,
        errors=tuple(errors),
        manifests_found=len(manifests),
        manifests_parsed=manifests_parsed,
        vuln_data=vuln_data,
        engine_results=engine_results,
        has_locked_closure=bool(parsed_kinds & {PIXI_LOCK_KIND, CONDA_LOCK_KIND}),
    )
    try:
        if args.format == "json":
            sys.stdout.write(render_json(report) + "\n")
        else:
            print(
                f"{TOOL_NAME}: status={report.status.value} "
                f"exit_code={report.exit_code} findings={len(report.findings)}"
            )
        # Flush INSIDE the guarded region: on a block-buffered pipe whose
        # consumer vanished, the BrokenPipeError must surface HERE (absorbed
        # below) — not at interpreter-exit flush (CPython exit 120).
        sys.stdout.flush()
    except BrokenPipeError:
        _absorb_broken_pipe()
    except (OSError, ValueError) as exc:
        # A non-EPIPE stdout failure is environmental, not an internal defect:
        # the verdict is already computed and must NOT be replaced by the
        # error exit or misdiagnosed as an internal error. Two families:
        #   * OSError (ENOSPC full disk, EIO hung-up terminal), and
        #   * ValueError ("I/O operation on closed file") — an in-process
        #     embedder that closed/replaced sys.stdout, the exact swapped-
        #     stream case _absorb_broken_pipe supports. CPython raises
        #     ValueError, not OSError, for a closed stream, so it must be
        #     caught here or it escapes to main's last-resort net and
        #     overrides the verdict with exit 2 (exit-code sole-ownership
        #     violation). Stdout may hold a partial document — same
        #     consumption guidance as SIGINT.
        _stderr(
            f"{TOOL_NAME}: stdout emission failed "
            f"({exc.__class__.__name__}); any partial stdout must not be "
            "consumed"
        )
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
    module docstring; Story 1.7 owns the final grammar). The subject
    segment is sanitized like every component-derived id segment — the id
    grammar is single-line by contract even when the subject is a
    user-supplied path."""
    errors.append(ErrorRecord(kind=kind, owner=owner, message=message))
    rungs.append(
        (
            Status.ERROR,
            StatusDriver(
                axis=AXIS_VULNERABILITY,
                finding_id=f"error:{kind}:{_sanitize_id_segment(subject)}",
            ),
        )
    )
    _stderr(f"{TOOL_NAME}: {message}")


def _stderr(message: str) -> None:
    """Print one stderr diagnostic, absorbing ANY stream failure — a
    vanished consumer raises ``OSError``, but a CLOSED stderr raises
    ``ValueError`` from ``print``. This helper runs INSIDE exception
    handlers (the SIGINT/SystemExit/last-resort nets), where a raise would
    escape ``main`` as an uncaught traceback with interpreter exit 1 —
    the exact exit-1 collision the module docstring forbids. A diagnostic
    stream failure must never replace the computed exit code.

    ``sys.stderr is None`` (pythonw / GUI / embedded hosts) is guarded
    explicitly: ``print(..., file=None)`` falls back to ``sys.stdout`` and
    would leak the diagnostic onto the contract stdout (NFR-I3) WITHOUT
    raising, so the try/except cannot catch it — drop the diagnostic
    instead."""
    try:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001 — see docstring: absorb everything
        pass


def _absorb_broken_pipe() -> None:
    """The stdout consumer vanished mid-emission (e.g. ``| head``): the
    verdict's exit code is already computed, so the pipe error is absorbed —
    never a traceback.

    Process-stream path (``sys.stdout`` IS ``sys.__stdout__``): fd 1 is
    re-pointed at ``os.devnull`` so the interpreter's exit-time flush
    cannot raise a second BrokenPipeError (CPython exit 120). This is a
    PROCESS-GLOBAL redirect — correct for the console script (about to
    exit) and documented for in-process embedders sharing the real stream:
    their pipe is equally dead, and the redirect trades EPIPE-on-every-
    later-write for silence.

    Swapped-stream path (test captures, embedders that replaced
    ``sys.stdout``): the broken stream OBJECT is closed instead — fd 1 is
    left alone, exit-time flush skips a closed stream, and a later write
    through the object fails LOUD (``ValueError``) rather than vanishing
    into a silent process-wide devnull redirect."""
    stream = sys.stdout
    if stream is sys.__stdout__:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(devnull, stream.fileno())
            finally:
                os.close(devnull)
        except (OSError, ValueError, AttributeError):
            # No usable descriptor behind the stream (AttributeError = a
            # fileno-less stream object aliased onto sys.__stdout__): nothing
            # will flush at interpreter exit, nothing to do.
            pass
        return
    try:
        stream.close()
    except Exception:  # noqa: BLE001 — best effort: the absorber must
        # never raise (a fake test stream may lack close(), or close's
        # final flush re-raises the pipe error).
        pass


if __name__ == "__main__":
    raise SystemExit(main())
