"""The real argparse CLI + scan orchestration (Story 1.2).

(The scaffold stub's docstring credited this to Story 4.1 — stale; the real
CLI landed with 1.2. Renderers proper are Story 1.8; typed errors 1.7; full
discovery 1.9.)

* D2's split (Story 1.9): the ``if not manifests:`` branch (discovery found
  NOTHING, no exception) splits on ``has_adjacent_python_source(target)`` —
  Python signals present means the recursive walk should have found
  something recognizable, so the run fails closed (``Status.ERROR``/exit 2,
  ``ErrorKind.UNPARSABLE_MANIFEST``); no Python source anywhere keeps the
  unchanged not-applicable/exit 0 stderr-only path. A SEPARATE, independent
  D2 case (c): at least one manifest parses but the whole scan feeds zero
  rungs (no components, no engine findings, no errors) — checked via
  ``manifests_parsed > 0 and not rungs`` after policy evaluation — injects
  one ``Status.INDETERMINATE`` rung with a paired ``Finding`` (the
  ratified Story 1.7 two-namespace contract: every non-error driver must
  reference an emitted finding) whose id is the FIXED literal
  ``indeterminate:empty-extraction:scan`` — never ``args.path`` — so
  ``warden scan .`` and ``warden scan <absolute path>`` against the same
  condition produce the SAME id (invocation-stability; this driver is
  whole-scan-scoped, not per-package, unlike the ``<pkg>``-shaped siblings
  in this finding-id family). ``--allow-empty`` downgrades ONLY that exit
  to 0 (``verdict.exit_code_for``'s sole-owned knob); ``status`` stays
  ``indeterminate``, never ``clean``, and ``empty_extraction=True`` is
  passed to ``assemble_report`` regardless of the flag, so ``coverage:
  none`` is recorded whether or not the downgrade fired.

Ownership decisions recorded:

* Stream discipline (NFR-I3): in ``--format json`` stdout carries EXACTLY
  one schema-valid ``ComplianceReport`` document or NOTHING; every
  diagnostic — including the empty-scan-set notice — goes to stderr.
  ``--format text`` emits ``report.render_text``'s non-contract human
  summary (a verdict line, then a driver line and one line per finding/
  error as applicable — Story 1.8) via the SAME ``sys.stdout.write`` call
  json already used, inside the try/except that already guarded both
  branches pre-1.8 — this story changed WHAT is printed on the text
  branch, not the guard structure around it.
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
  Story 1.7 ratified this as the final error-driver grammar, with the
  driver's axis set to the actually-failing stage/engine (``AXIS_INGESTION``
  for a pre-engine discovery/extract/routing failure, ``AXIS_HYGIENE``/
  ``AXIS_VULNERABILITY`` for a crashing engine's own axis) — never a
  blanket default.
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
* ``config.load_config`` (Story 3.1, FR30) runs first, before discovery —
  its resolved ``WardenConfig`` is what ``DefaultPolicy`` gates on below.
  A malformed ``[tool.pyforge-warden]`` key/value is
  ``ErrorKind.CONFIG_VALIDATION`` via the SAME ``_record_error`` seam every
  other pre-engine failure uses (typed record + error rung + stderr
  diagnostic), with ``WardenConfig.defaults()`` as the fallback so the
  rest of the scan still runs and a report is still emitted — the exit
  code is orthogonal to emission, same as every other seam here. A
  same-key ``pyproject.toml``/``pixi.toml`` conflict is NOT an error (FR30:
  "conflicts surfaced, never failing the build") — one stderr line per
  conflicting key, ``pyproject.toml``'s value already won inside
  ``load_config``.
* Strictly non-interactive: no prompts, stdin is never read.
* ``has_locked_closure`` (Story 2.6): the extraction loop tracks
  ``parsed_kinds`` — the set of manifest KINDS that actually parsed, not
  just the count — and passes ``bool(parsed_kinds & {PIXI_LOCK_KIND,
  CONDA_LOCK_KIND})`` to ``assemble_report``. ``report.py`` has no
  lockfile-kind vocabulary of its own (that's ``discovery.py``'s domain),
  so the caller states the claim.
* ``hygiene_applicable`` (Story 2.4, AC3): computed ONCE, via
  ``hygiene.has_adjacent_python_source(target)``, right before
  ``engines_to_run`` — a source-less scan target (the fleet's majority
  feedstock shape) makes deptry flag every conda-sourced dependency
  reaching the front-door as "unused" (a noise wall, never a signal), so
  ``DeptryEngine`` is filtered out of ``engines_to_run`` when it is
  ``False`` and the same value is threaded into ``assemble_report`` so the
  hygiene axis honestly reports not-applicable. Deliberately NOT a check
  inside ``DeptryEngine.run`` itself — ``tests/unit/
  test_engine_env_deptry.py`` calls the engine directly against bare
  ``tmp_path`` dirs to test its own argv/error-handling logic in isolation,
  and embedding the skip there would exercise the wrong branch in every one
  of those tests.
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
from .config import (
    FAIL_ON_CHOICES,
    FAIL_UNDER_COVERAGE_MAX,
    FAIL_UNDER_COVERAGE_MIN,
    ConfigValidationError,
    WardenConfig,
    load_config,
)
from .discovery import CONDA_LOCK_KIND, PIXI_LOCK_KIND, discover
from .engines import DeptryEngine, engine_factories
from .extract import UnparsableManifestError, extractor_for
from .hygiene import has_adjacent_python_source
from .interfaces import DefaultPolicy, EngineResult, _sanitize_id_segment
from .inventory import Component, ResolvedInventory, merge_components
from .models import (
    AXIS_HYGIENE,
    AXIS_INGESTION,
    EMPTY_EXTRACTION_DRIVER_ID,
    ErrorKind,
    ErrorRecord,
    Finding,
    Status,
    StatusDriver,
    VulnData,
)
from .report import TOOL_NAME, assemble_report, render_json, render_text
from .routing import DefaultRouter
from .verdict import EXIT_SIGINT, exit_code_for

# D2(c) empty-extraction (Story 1.9): one shared message stem for both the
# stderr notice and the paired Finding below — kept as ONE literal so a
# future wording edit can't silently drift the two apart.
_EMPTY_EXTRACTION_MESSAGE = (
    "manifest(s) parsed but zero dependencies/components extracted under "
    "{path!r}"
)


def _coverage_percentage(raw: str) -> int:
    """argparse ``type=`` for ``--fail-under-coverage``: an integer in
    ``[FAIL_UNDER_COVERAGE_MIN, FAIL_UNDER_COVERAGE_MAX]`` — argparse's own
    usage-error path (exit 2) rejects anything else before ``_run_scan``
    ever sees it (mirrors ``config._validate_fail_under_coverage``'s bound,
    the single source of truth for both surfaces)."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"must be an integer, got {raw!r}"
        ) from None
    if not (FAIL_UNDER_COVERAGE_MIN <= value <= FAIL_UNDER_COVERAGE_MAX):
        raise argparse.ArgumentTypeError(
            f"must be in [{FAIL_UNDER_COVERAGE_MIN}, {FAIL_UNDER_COVERAGE_MAX}], "
            f"got {value}"
        )
    return value


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
    scan.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "downgrade the exit code to 0 when at least one manifest "
            "parses but extraction yields zero components/findings/errors "
            "(D2(c)) — status stays 'indeterminate', never 'clean', and "
            "coverage still records no resolution-depth claim"
        ),
    )
    scan.add_argument(
        "--fail-on",
        choices=FAIL_ON_CHOICES,
        default=None,
        help=(
            "CVSS severity threshold: this tier and every tier at least as "
            "severe escalate to a blocking policy-violation, weaker tiers "
            "stay warn (default: critical — from [tool.pyforge-warden] "
            "'fail_on' if set, else 'critical'; omitting this flag falls "
            "through to that resolved config value, never overriding it "
            "with argparse's own default)"
        ),
    )
    scan.add_argument(
        "--fail-under-coverage",
        type=_coverage_percentage,
        default=None,
        metavar="0-100",
        help=(
            "minimum per-axis coverage percentage (deps assessed / deps "
            "total): below this floor the axis escalates to indeterminate "
            "(default: off — from [tool.pyforge-warden] "
            "'fail_under_coverage' if set, else unset; FR19)"
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

    # Story 3.1 (FR30): resolve [tool.pyforge-warden] before anything else
    # runs — the resolved config feeds DefaultPolicy below. A per-key
    # validation problem (unrecognized key, wrong-typed/out-of-vocabulary
    # value) never aborts resolution of the OTHER keys (review finding,
    # 2026-07-17: a CLI override for one key must survive an unrelated
    # bad key in the file) — load_config falls back to that one key's
    # default and returns every problem as a message; each becomes its
    # own typed operational error (same seam doctrine as every other
    # pre-engine failure), and the report is STILL emitted. Only a
    # STRUCTURAL failure (`[tool.pyforge-warden]` itself not a table) has
    # no sensible per-key fallback and still raises ConfigValidationError.
    # A same-key pyproject/pixi conflict is not an error — one stderr
    # line per conflict, config.py already picked pyproject's value —
    # and, unlike before this fix, is never lost just because some other
    # key also failed validation.
    try:
        config, conflicts, validation_errors = load_config(
            target,
            cli_fail_on=args.fail_on,
            cli_fail_under_coverage=args.fail_under_coverage,
        )
    except ConfigValidationError as exc:
        config = WardenConfig.defaults()
        _record_error(
            errors,
            rungs,
            kind=ErrorKind.CONFIG_VALIDATION,
            owner="config",
            subject=args.path,
            message=str(exc),
            axis=AXIS_INGESTION,
        )
    else:
        for conflict in conflicts:
            _stderr(f"{TOOL_NAME}: {conflict}")
        for message in validation_errors:
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.CONFIG_VALIDATION,
                owner="config",
                subject=args.path,
                message=message,
                axis=AXIS_INGESTION,
            )

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
            axis=AXIS_INGESTION,
        )
    else:
        if not manifests:
            if has_adjacent_python_source(target):
                # D2's misconfiguration guard (Story 1.9): the recursive
                # walk found NOTHING recognizable anywhere in the tree, yet
                # Python source exists — never silently "nothing to scan"
                # (exit 0); a fail-closed operational error (exit 2).
                _record_error(
                    errors,
                    rungs,
                    kind=ErrorKind.UNPARSABLE_MANIFEST,
                    owner="discovery",
                    subject=args.path,
                    message=(
                        f"no recognized manifest found under {args.path!r} "
                        "despite Python source present (D2 misconfiguration "
                        "guard)"
                    ),
                    axis=AXIS_INGESTION,
                )
            else:
                # The not-applicable path says so on stderr; stdout stays
                # pure.
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
                axis=AXIS_INGESTION,
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
                axis=AXIS_INGESTION,
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
                axis=AXIS_INGESTION,
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
        # A parsed manifest with nothing extractable must be distinguishable
        # on stderr from the empty-dir case (the coverage block already
        # distinguishes them). Manifest-kind-agnostic wording (Story 1.9):
        # this notice now accompanies D2(c)'s actual gate failure
        # (indeterminate/exit 1 by default) for ANY of the discovered
        # manifest kinds, not just pyproject.toml — naming a specific
        # section/format here would misdescribe 7 of 8 kinds.
        _stderr(
            f"{TOOL_NAME}: "
            f"{_EMPTY_EXTRACTION_MESSAGE.format(path=args.path)}; "
            "nothing to scan"
        )
    engine_results: list[EngineResult] = []
    # AC3: a source-less scan target makes deptry flag every conda-sourced
    # dependency reaching the front-door as "unused" (DEP002) -- a noise
    # wall, never a signal -- so DeptryEngine is filtered out when no
    # adjacent .py file exists anywhere under target. Computed once, up
    # front, so both the engine filter below and the assemble_report call
    # see the same value. Gated on manifests_parsed like the engine seam
    # itself below (review finding, 2026-07-17): with nothing extractable,
    # engines_to_run is already () and inventory.count is already 0, so the
    # walk's result can never affect the output -- skip the wasted I/O.
    hygiene_applicable = (
        has_adjacent_python_source(target) if manifests_parsed > 0 else True
    )
    # The engine seam runs only when a manifest actually parsed: with nothing
    # extractable (empty dir, or a manifest that failed to parse) there is no
    # project for a subprocess engine (deptry) to assess, and running it on an
    # absent/malformed manifest would only double the extractor's own error.
    engines_to_run = (
        tuple(
            factory
            for factory in engine_factories()
            if hygiene_applicable or factory is not DeptryEngine
        )
        if manifests_parsed > 0
        else ()
    )
    for factory in engines_to_run:
        try:
            engine = factory()
        except (SystemExit, Exception) as exc:  # noqa: BLE001 —
            # instantiation is PART of the seam: a crashing constructor (a
            # misconfigured 1.3/1.5 runner) is the engine-unavailable
            # class — typed record + error rung, report STILL emitted,
            # never a traceback with no report.
            factory_name = getattr(factory, "__name__", repr(factory))
            # `factory` is typed as Callable[[] , Engine] (the registry's
            # shape), but every REAL factory is the engine class itself, so
            # `axis` is readable as a class attribute without instantiating
            # (mirrors `factory_name` above) — getattr, not a direct
            # attribute access, keeps mypy honest about the narrower
            # Callable type while still reading the real class attribute.
            factory_axis = getattr(factory, "axis", AXIS_INGESTION)
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
                axis=factory_axis,
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
                axis=engine.axis,
            )
    for result in engine_results:
        errors.extend(result.errors)
    findings, policy_rungs = DefaultPolicy(config=config).evaluate(
        inventory, engine_results
    )
    if not hygiene_applicable:
        # AC3 (review finding, 2026-07-17): DefaultPolicy derives a
        # per-component `indeterminate:uncovered:<pkg>` (axis=hygiene)
        # finding from `component.hygiene_covered` alone -- independent of
        # whether any engine ran -- so a RAW_MALFORMED component still
        # produced a hygiene-axis finding even though the axis's own
        # AxisCoverage now honestly claims deps_total=0 (verified live: a
        # source-less manifest with an unresolvable dep reported
        # `hygiene: deps_total=0` alongside a `hygiene`-axis finding, a
        # self-contradiction the not-applicable claim must not carry).
        # Safe to drop unconditionally: a component whose name/version
        # extraction failed badly enough to be hygiene-uncovered also has
        # no resolved identity+version, so it independently produces its
        # own vulnerability-axis indeterminate signal -- this filter never
        # removes the sole driver of a non-clean verdict.
        findings = tuple(f for f in findings if f.axis != AXIS_HYGIENE)
        policy_rungs = tuple(
            (status, driver)
            for status, driver in policy_rungs
            if driver is None or driver.axis != AXIS_HYGIENE
        )
    rungs.extend(policy_rungs)

    # D2(c) (Story 1.9): at least one manifest parsed but the whole scan fed
    # ZERO rungs (no components, no engine findings, no errors) — ambiguous/
    # partial discovery, never a silent clean/not-applicable. A paired
    # Finding is added (not just a driver) so the ratified Story 1.7
    # two-namespace contract holds (every non-error status driver must
    # reference an emitted finding). The id is the FIXED literal
    # EMPTY_EXTRACTION_DRIVER_ID (models.py; verdict.py's exit_code_for and
    # ComplianceReport.__post_init__ both match it EXACTLY, never a prefix)
    # -- this driver is whole-scan-scoped, not per-package, and the id must
    # stay invocation-stable (`warden scan .` vs `warden scan <absolute
    # path>` are the SAME condition).
    empty_extraction = manifests_parsed > 0 and not rungs
    if empty_extraction:
        findings = (
            *findings,
            Finding(
                id=EMPTY_EXTRACTION_DRIVER_ID,
                axis=AXIS_INGESTION,
                message=_EMPTY_EXTRACTION_MESSAGE.format(path=args.path),
                subject=args.path,
                severity=None,
            ),
        )
        rungs.append(
            (
                Status.INDETERMINATE,
                StatusDriver(
                    axis=AXIS_INGESTION, finding_id=EMPTY_EXTRACTION_DRIVER_ID
                ),
            )
        )

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
        hygiene_applicable=hygiene_applicable,
        allow_empty=args.allow_empty,
        empty_extraction=empty_extraction,
    )
    try:
        if args.format == "json":
            sys.stdout.write(render_json(report) + "\n")
        else:
            sys.stdout.write(render_text(report) + "\n")
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
    axis: str,
) -> None:
    """Surface one operational error: typed record + error rung + stderr
    diagnostic. The rung's driver id uses the ``error:<kind>:<subject>``
    grammar and deliberately does NOT reference ``findings[]`` (see the
    module docstring; Story 1.7 ratified this as the final grammar). The
    caller states ``axis`` — the actually-failing stage/engine
    (``AXIS_INGESTION`` for a pre-engine discovery/extract/routing failure,
    or the crashing engine's/factory's own axis) — never a blanket default.
    The subject segment is sanitized like every component-derived id
    segment — the id grammar is single-line by contract even when the
    subject is a user-supplied path."""
    errors.append(ErrorRecord(kind=kind, owner=owner, message=message))
    rungs.append(
        (
            Status.ERROR,
            StatusDriver(
                axis=axis,
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
