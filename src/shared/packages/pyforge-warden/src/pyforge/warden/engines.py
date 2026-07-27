"""Engine registry + the null/deptry/osv engines (Stories 1.2/1.3/1.5).

OWNERSHIP DECISION (recorded): ``engines.py`` is the package's ONLY
subprocess-capable module — the sole subprocess site. Every engine call goes
through ``_engine_env()``, the load-bearing subprocess-normalization seam
(argv **list**, machine output forced to a ``tempfile.mkstemp`` file in
SYSTEM temp — never the scanned tree, ``NO_COLOR=1`` + optional ``extra_env``,
``stdin=DEVNULL``, bounded timeout, explicit utf-8 decode → typed
``ErrorRecord``, temp cleanup on success AND failure). Story 1.5 widened the
seam (``extra_env`` param + a surfaced child exit code) rather than
reimplementing it — see the osv-db-offline-provisioning decision record's
"seam hand-off" section.

Story 6.6 (FR21) adds a SECOND, narrowly-scoped subprocess call site —
``_check_engine_version`` — a ``--version`` pre-flight run before either real
engine subprocess trusts its output. It deliberately does NOT go through
``_engine_env``: that seam's contract always writes to an
``-o``/``--output``-style tempfile flag, which ``--version`` has no
equivalent of, so this helper captures stdout directly via
``subprocess.run(..., capture_output=True)`` instead. Still typed the same
way (``ErrorRecord`` via the shared ``ErrorKind`` taxonomy), still bounded by
a timeout, still no shell — just not funneled through the tempfile contract.

Registry semantics: engines register via ``register_engine(factory)`` at
module-import time; ``registered_engines()`` instantiates them in
registration order — deterministic because module execution is. The registry
is ``[NullEngine, DeptryEngine, OsvEngine, LicenseEngine, CurrencyEngine]``:
``NullEngine`` is a harmless no-op retained so its 1.2 unit contract is
unchanged, ``DeptryEngine`` is the hygiene-axis engine (1.3), ``OsvEngine``
is the vulnerability-axis engine (1.5), ``LicenseEngine`` is the license-axis
engine (6.2), ``CurrencyEngine`` is the currency-axis engine (6.3) — the
second engine (after ``LicenseEngine``) that spawns no subprocess at all.

``NullEngine`` spawns no subprocess; ``DeptryEngine`` runs ``deptry`` via
``_engine_env`` (its exit code is CONTENT — exit 1 = issues found — never the
gate). ``OsvEngine`` runs ``osv-scanner`` fully offline via the same seam,
but osv's exit code IS partly the gate: 0/1 are content (clean/vulns-found),
127/128/other are typed operational failures — see the module's own
docstring and the decision record for why the exit code must be observed at
all for osv (the DB-absent cold start would otherwise false-green).

Story 2.5 widens ``OsvEngine.run`` with two independent honesty tiers, both
computed ONCE per scan right after the DB content pre-flight passes (this
module owns the clock — ``vuln.py``/``cli.py``/``report.py`` stay clockless):
``is_db_stale`` (FR12 — a stale/future-dated DB forces the WHOLE
vulnerability axis to ``indeterminate`` via ``stale_vuln_data_finding``,
merged into every exit-``{0,1}`` (and the name-level-only) result) and the
name-level "any version" scan (FR13 — a mapped-but-unversioned component's
name is checked directly against the SAME resolved DB zip, never a second
``osv-scanner`` subprocess). The candidate guard widens to
``not candidates and not name_level_candidates`` so a scan with ONLY
name-level candidates still reaches the pre-flight instead of bailing out
empty.

Story 2.2 widens ``DeptryEngine.run`` with an UNCONDITIONAL synthesized
front-door (FR8's conda half): ``hygiene._synthesize_deptry_frontdoor``
turns the inventory into a sorted ``name[==version]`` temp file, written
via the SAME ``tempfile.mkstemp``/``finally: os.unlink`` idiom
``OsvEngine.run`` uses for its own input file (NFR-S4), and
``--requirements-files <path>`` is ALWAYS appended to deptry's argv. This
is safe unconditionally — never conditionally detected — because deptry's
own documented rule ("if a pyproject.toml with ``[project]``/
``[tool.poetry.dependencies]`` is found, this argument is ignored") makes
the addition a no-op for every existing pyproject-native scan; duplicating
that sniffing logic here would be a second, driftable source of truth. Any
component the NFR-S6 purity guard excludes from that front-door
(``SynthesizedInput.excluded``) surfaces via ``hygiene.
unsafe_identity_finding`` (imported here as ``hygiene_unsafe_identity_
finding`` — ``vuln.py`` already exports an ``unsafe_identity_finding`` of
its own into this module's namespace) — Fix 6 (2026-07-16): previously
computed and silently discarded, unlike every other exclusion path in this
module.

Story 5.1 (D8) adds ``DoctorCheck``/``run_doctor_checks`` — the ``--doctor``
self-check aggregation ``cli.py`` calls instead of a real project scan. It
reuses ``_check_engine_version`` (deptry/osv-scanner) and the SAME OSV-DB/
KEV/EPSS detection sequences ``OsvEngine.run`` already exercises, so
``--doctor`` never carries a second, drift-prone copy of that logic. Also
threads ``OsvEngine.run``'s own ``parse_osv_output(...).fixed_versions``
(Story 5.1, AC1 — osv-scanner's discarded ``fixed`` version) into
``EngineResult.fixed_versions`` at the real-parse success site, consumed
ONLY by ``report.render_text``'s remediation lines.
"""

from __future__ import annotations

import dataclasses
import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from . import feeds
from .currency import currency_findings, currency_stale_finding
from .hygiene import (
    _synthesize_deptry_frontdoor,
    parse_deptry_output,
    unsafe_identity_finding as hygiene_unsafe_identity_finding,
    no_identity_hygiene_finding as hygiene_no_identity_finding,
)
from .interfaces import Engine, EngineResult
from .inventory import Component, ResolvedInventory
from .license import license_findings
from .models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_INGESTION,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    Epss,
    ErrorKind,
    ErrorRecord,
    FeedProvenance,
    Finding,
    VulnData,
)
from .vuln import (
    DB_MAX_AGE_DAYS,
    OSV_DB_CACHE_ENV_VAR,
    _db_has_valid_advisory,
    _synthesize_requirements,
    db_snapshot_at,
    db_zip_path,
    epss_match,
    epss_stale_finding,
    is_db_stale,
    kev_match,
    kev_stale_finding,
    build_name_level_critical_index,
    name_level_critical_advisory_ids,
    name_level_critical_cve_finding,
    offline_db_unavailable_finding,
    parse_osv_output,
    resolve_cache_dir,
    stale_vuln_data_finding,
    unsafe_identity_finding,
)

# Bounded subprocess timeout (seconds) — a hung engine must fail loud
# (engine-timeout), never wedge the scan. A fixed default in 1.3 (the
# ``_engine_env`` ``timeout`` parameter accepts an override; a user-facing
# config surface arrives with the ConfigLoader in Story 3.1). Not in
# {1, 2, 130}, so the sole-ownership exit-literal guard never mistakes it for
# an exit code.
DEPTRY_TIMEOUT_SECONDS = 120

# Story 6.6 (FR21 — the distribution gate): the ``--version`` pre-flight's own
# bounded timeout. A tiny, fixed default — ``--version`` never does real work
# — distinct from ``DEPTRY_TIMEOUT_SECONDS``/``OSV_TIMEOUT_SECONDS`` (the real
# scan's budget). Not in {1, 2, 130}, same sole-ownership guard rationale.
ENGINE_VERSION_CHECK_TIMEOUT_SECONDS = 10

# The tested version ranges (NFR-C1: a RANGE, not an exact pin — engines come
# from feedstocks — open only to patch releases of the SAME evidence-backed
# minor). Must byte-for-byte mirror ``pixi.toml``'s ``deptry``/``osv-scanner``
# run-dependency pins — enforced by
# ``tests/meta/test_engine_version_range_sync.py``. Evidence: deptry 0.25.1
# (hygiene.py's DEP005 docstring), osv-scanner 2.4.0 (vuln.py's
# "Empirically-verified 2.4.0 shape" docstring) — the exact minors this
# codebase has verified output-schema evidence for; widening beyond them "to
# be safe" defeats the whole point (an untested newer minor must fail loud,
# not silently pass).
DEPTRY_VERSION_RANGE = SpecifierSet(">=0.25.1,<0.26")
OSV_SCANNER_VERSION_RANGE = SpecifierSet(">=2.4.0,<2.5")

# ``deptry --version`` prints ``deptry 0.25.1``; ``osv-scanner --version``
# prints a multi-line block starting ``osv-scanner version: 2.4.0`` — both
# verified live against the currently-provisioned pixi environment during
# this story's implementation (2026-07-24).
_DEPTRY_VERSION_PATTERN = re.compile(r"^deptry\s+(\S+)", re.MULTILINE)
_OSV_SCANNER_VERSION_PATTERN = re.compile(
    r"^osv-scanner version:\s*(\S+)", re.MULTILINE
)

_ENGINE_FACTORIES: list[Callable[[], Engine]] = []


def register_engine(factory: Callable[[], Engine]) -> Callable[[], Engine]:
    """Register an engine factory (decorator-friendly: returns the factory).

    Order of registration is the order ``engine_factories()`` /
    ``registered_engines()`` yields. Re-registering the SAME factory object
    is a no-op — a defensive guard against a double ``register_engine``
    call. It CANNOT protect across ``importlib.reload(engines)``: reload
    re-executes this module, which RESETS the registry and silently
    discards every previously registered factory — reloading is
    unsupported."""
    if factory not in _ENGINE_FACTORIES:
        _ENGINE_FACTORIES.append(factory)
    return factory


def engine_factories() -> tuple[Callable[[], Engine], ...]:
    """The registered factories, in deterministic (registration) order.

    The CLI instantiates each factory individually under its own seam
    guard: a crashing constructor must yield a typed
    ``engine-unavailable`` ``ErrorRecord`` with the report still emitted,
    never abort the scan (instantiation is part of the seam)."""
    return tuple(_ENGINE_FACTORIES)


def registered_engines() -> tuple[Engine, ...]:
    """Fresh engine instances, in deterministic (registration) order.

    Instantiates EAGERLY and unguarded — direct/test use. The CLI goes
    through ``engine_factories()`` instead so a crashing constructor is
    contained per-factory."""
    return tuple(factory() for factory in _ENGINE_FACTORIES)


# NFR-S5 (AUD-WARDEN-017): engine machine-output files are size-capped before
# decode — mirrors lockfile/manifest bounded reads. Real deptry/osv JSON is
# far smaller; an adversarial / runaway engine must not OOM the parent.
_MAX_ENGINE_OUTPUT_BYTES = 20_000_000


def _read_engine_output_text(output_path: str) -> str:
    """Read engine stdout file under :data:`_MAX_ENGINE_OUTPUT_BYTES`.

    Raises ``OSError`` subclasses for I/O failures and ``ValueError`` when the
    file exceeds the size cap (mapped by the caller to
    ``ENGINE_OUTPUT_UNPARSEABLE``).
    """
    path = Path(output_path)
    size = path.stat().st_size
    if size > _MAX_ENGINE_OUTPUT_BYTES:
        raise ValueError(
            f"engine output exceeds the {_MAX_ENGINE_OUTPUT_BYTES}-byte "
            "size cap (NFR-S5)"
        )
    # utf-8-sig tolerates a leading BOM some tools prepend, then decodes as
    # utf-8; genuinely non-utf-8 bytes still raise UnicodeDecodeError.
    return path.read_bytes().decode("utf-8-sig")


def _engine_env(
    build_argv: Callable[[str], list[str]],
    *,
    owner: str,
    cwd: Path,
    timeout: float = DEPTRY_TIMEOUT_SECONDS,
    extra_env: dict[str, str] | None = None,
) -> tuple[str | None, ErrorRecord | None, int | None]:
    """Run one engine subprocess under a normalized environment.

    ``build_argv(output_path)`` returns the argv **list** (never
    ``shell=True``, never manifest data as a flag); the machine output is
    forced to ``output_path``, a ``tempfile.mkstemp`` file (mode 0600) in
    SYSTEM temp — never the scanned tree (NFR-S4). The child runs with
    ``NO_COLOR=1`` merged with an optional ``extra_env`` (Story 1.5: e.g.
    ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY``) over a COPY of the parent
    environment, ``stdin=DEVNULL``, and its own stdout/stderr routed to
    ``DEVNULL`` — an engine's human chatter never reaches our contract
    streams, and only the output file is read.

    Returns ``(decoded-machine-output-text, None, exit_code)`` on success, or
    ``(None, ErrorRecord, exit_code)`` on a typed failure:
    ``FileNotFoundError`` → ``engine-unavailable``; ``TimeoutExpired`` →
    ``engine-timeout``; an undecodable (non-utf-8) machine-output file →
    ``engine-output-unparseable``; any other OS failure spawning the child →
    ``engine-execution-failed``. ``exit_code`` is ``None`` on every
    EARLY-RETURN path (mkstemp failure, spawn ``FileNotFoundError``/
    ``TimeoutExpired``) — the child never ran, or its outcome is unknown —
    and is the child's REAL ``subprocess.run(...).returncode`` on every path
    where the child actually completed, including the two post-completion
    decode-failure paths and the success path (Story 1.5's osv-scanner
    runner needs to distinguish 0/1/127/128 as content, which deptry's
    caller still ignores). The temp file is cleaned up on success AND
    failure."""
    try:
        handle, output_path = tempfile.mkstemp(suffix=".json", prefix="pdos-engine-")
    except OSError as exc:
        return (
            None,
            ErrorRecord(
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=owner,
                message=f"could not create a temp output file: {exc.__class__.__name__}",
            ),
            None,
        )
    try:
        os.close(handle)  # the child reopens the path for writing — inside the
        #                    try so the finally's unlink runs even if close
        #                    raises (Gemini PR #54: no temp-file leak).
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        if extra_env:
            env.update(extra_env)
        try:
            completed = subprocess.run(  # noqa: S603 — argv list, no shell; the sole seam
                build_argv(output_path),
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,  # exit code is content, never the gate
            )
        except FileNotFoundError:
            # subprocess raises FileNotFoundError for BOTH a missing executable
            # AND a missing cwd (the pre-exec chdir fails). Disambiguate so a
            # target dir that vanished after discovery (TOCTOU) is not
            # misreported as "engine not installed" — this seam is reused
            # verbatim by Story 1.5's osv runner.
            if not os.path.isdir(cwd):
                return (
                    None,
                    ErrorRecord(
                        kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                        owner=owner,
                        message=(
                            f"scan target {str(cwd)!r} is not an existing "
                            f"directory when engine {owner!r} ran (vanished "
                            "after discovery?)"
                        ),
                    ),
                    None,
                )
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_UNAVAILABLE,
                    owner=owner,
                    message=f"engine binary for {owner!r} not found on PATH",
                ),
                None,
            )
        except subprocess.TimeoutExpired:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_TIMEOUT,
                    owner=owner,
                    message=f"engine {owner!r} exceeded the {timeout}s timeout",
                ),
                None,
            )
        except OSError as exc:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner=owner,
                    message=f"engine {owner!r} could not be executed: {exc.__class__.__name__}",
                ),
                None,
            )
        try:
            text = _read_engine_output_text(output_path)
        except UnicodeDecodeError:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=owner,
                    message=f"engine {owner!r} produced non-utf-8 output",
                ),
                completed.returncode,
            )
        except ValueError as exc:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=owner,
                    message=f"engine {owner!r} output unreadable: {exc}",
                ),
                completed.returncode,
            )
        except OSError as exc:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner=owner,
                    message=f"could not read engine output: {exc.__class__.__name__}",
                ),
                completed.returncode,
            )
        return (text, None, completed.returncode)
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


def _check_engine_version(
    *,
    owner: str,
    argv: list[str],
    version_pattern: re.Pattern[str],
    expected: SpecifierSet,
    cwd: Path,
) -> ErrorRecord | None:
    """Story 6.6 (FR21): a ``--version`` pre-flight gate run BEFORE either
    real engine subprocess trusts its output. A second, narrowly-scoped
    exception to this module's sole ``_engine_env`` subprocess seam —
    justified because ``_engine_env``'s contract always writes to an
    ``-o``/``--output``-style tempfile flag that ``--version`` has no
    equivalent of; capturing stdout directly is simpler and never touches
    disk at all.

    Mirrors ``_engine_env``'s own typed-error taxonomy for the spawn itself
    (``FileNotFoundError`` -> ``ENGINE_UNAVAILABLE`` — disambiguated against a
    vanished ``cwd`` exactly like ``_engine_env``'s own TOCTOU guard,
    ``TimeoutExpired`` -> ``ENGINE_TIMEOUT``, any other ``OSError`` ->
    ``ENGINE_EXECUTION_FAILED``) plus terminal cases unique to this check: a
    non-zero exit (content alone is never trusted — a broken install could
    still print a stale/cached version banner before failing), version text
    that fails to match ``version_pattern``, fails to parse as a PEP 440
    version, or parses but falls outside ``expected`` — ALL of which map to
    the SAME existing ``ENGINE_UNAVAILABLE`` kind (no new ``ErrorKind``
    member; FR21's "unavailable/incompatible" is one typed kind,
    schema-frozen since Story 6.1). Returns ``None`` on a passing check —
    the caller's real engine subprocess should proceed exactly as before
    this story."""
    try:
        completed = subprocess.run(  # noqa: S603 — argv list, no shell
            argv,
            cwd=str(cwd),
            env={**os.environ, "NO_COLOR": "1"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=ENGINE_VERSION_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        # Mirrors _engine_env's own disambiguation (review finding,
        # 2026-07-24): subprocess.run raises FileNotFoundError for BOTH a
        # missing executable AND a missing cwd (the pre-exec chdir fails) --
        # a target dir that vanished after discovery (TOCTOU) must not be
        # misreported as "engine not installed".
        if not os.path.isdir(cwd):
            return ErrorRecord(
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=owner,
                message=(
                    f"scan target {str(cwd)!r} is not an existing directory "
                    f"when the {owner!r} version check ran (vanished after "
                    "discovery?)"
                ),
            )
        return ErrorRecord(
            kind=ErrorKind.ENGINE_UNAVAILABLE,
            owner=owner,
            message=f"engine binary for {owner!r} not found on PATH",
        )
    except subprocess.TimeoutExpired:
        return ErrorRecord(
            kind=ErrorKind.ENGINE_TIMEOUT,
            owner=owner,
            message=(
                f"engine {owner!r} exceeded the "
                f"{ENGINE_VERSION_CHECK_TIMEOUT_SECONDS}s version-check timeout"
            ),
        )
    except OSError as exc:
        return ErrorRecord(
            kind=ErrorKind.ENGINE_EXECUTION_FAILED,
            owner=owner,
            message=f"engine {owner!r} could not be executed: {exc.__class__.__name__}",
        )
    if completed.returncode != 0:
        # Review finding, 2026-07-24: a broken/misconfigured engine install
        # that exits non-zero but still prints a matching version string
        # (e.g. a stale cached banner before a real failure) must not pass
        # the gate on stdout content alone.
        return ErrorRecord(
            kind=ErrorKind.ENGINE_UNAVAILABLE,
            owner=owner,
            message=(
                f"{owner!r} --version exited {completed.returncode} "
                "-- compatibility could not be confirmed"
            ),
        )
    stdout_text = completed.stdout.decode("utf-8", errors="replace")
    match = version_pattern.search(stdout_text)
    if match is None:
        return ErrorRecord(
            kind=ErrorKind.ENGINE_UNAVAILABLE,
            owner=owner,
            message=(
                f"could not parse version output from {owner!r} "
                f"(--version produced no recognizable version string)"
            ),
        )
    try:
        version = Version(match.group(1))
    except InvalidVersion:
        return ErrorRecord(
            kind=ErrorKind.ENGINE_UNAVAILABLE,
            owner=owner,
            message=(
                f"could not parse version {match.group(1)!r} reported by "
                f"{owner!r}"
            ),
        )
    if version not in expected:
        return ErrorRecord(
            kind=ErrorKind.ENGINE_UNAVAILABLE,
            owner=owner,
            message=(
                f"{owner!r} version {str(version)!r} is outside tested "
                f"range {expected!s}"
            ),
        )
    return None


# --- Story 5.1 (D8): the --doctor self-check aggregation ---------------------
#
# `--doctor` (cli.py) re-exposes this module's own engine-version/OSV-DB/KEV/
# EPSS detection logic as a read-only, no-network environment self-check -- an
# operability report, never a project scan (cli.py's `_run_doctor` never
# builds an inventory or runs discovery/extraction/policy for this path).
# `DoctorCheck` deliberately lives HERE, not in `models.py`: it is NOT part of
# the frozen `ComplianceReport` v1 contract (Story 6.1 froze that schema
# whole), so a new field here can never be mistaken for a sanctioned schema
# amendment.


@dataclasses.dataclass(frozen=True)
class DoctorCheck:
    """One ``--doctor`` self-check outcome. ``ok=True`` covers a healthy
    check AND an ABSENT optional KEV/EPSS feed (v1's NFR-U2 air-gap framing
    treats that as the expected default posture, never a failure — though
    the message names the scan-time consequence per feed, see
    ``_doctor_check_feed``); ``ok=False`` is reserved for a genuine
    operability problem (an unavailable/out-of-tested-range engine, an
    unusable/stale offline OSV DB, a PRESENT-but-unloadable feed file, or a
    PRESENT-but-stale feed whose gate is on by default — KEV, see
    ``_doctor_check_feed``'s ``stale_is_problem``). ``cli.py``'s ``_run_doctor`` is the ONLY place these compose
    into an exit code (``0`` when every check is ``ok``, else
    ``exit_code_for(Status.ERROR)`` — NEVER ``1``); this dataclass carries
    no exit-code opinion of its own."""

    name: str
    ok: bool
    message: str


def _doctor_check_engine(
    *,
    name: str,
    argv: list[str],
    version_pattern: re.Pattern[str],
    expected: SpecifierSet,
    cwd: Path,
) -> DoctorCheck:
    """One engine's ``--version`` pre-flight, reusing ``_check_engine_
    version`` verbatim (Story 6.6/FR21) — never a second, doctor-only
    version-probing codepath. ``_check_engine_version`` already names the
    specific problem (binary absent, timeout, out-of-range, unparsable
    output, ...) via its own ``ErrorRecord.message``; this only re-shapes a
    passing/failing result into a ``DoctorCheck``."""
    error = _check_engine_version(
        owner=name,
        argv=argv,
        version_pattern=version_pattern,
        expected=expected,
        cwd=cwd,
    )
    if error is None:
        return DoctorCheck(
            name=name, ok=True, message=f"within tested range {expected!s}"
        )
    return DoctorCheck(name=name, ok=False, message=error.message)


def _doctor_check_osv_db() -> DoctorCheck:
    """The offline OSV database pre-flight (decision record § 4), reusing
    ``OsvEngine.run``'s own ``resolve_cache_dir`` -> ``db_zip_path`` ->
    ``_db_has_valid_advisory`` -> ``db_snapshot_at`` -> ``is_db_stale``
    sequence verbatim — a genuine operability problem (absent, unreadable,
    content-corrupt, or stale/future-dated) is ``ok=False``, naming the
    specific issue (this is read as an operational gap, never a policy
    verdict — ``--doctor`` still never exits ``1`` for it; ``cli.py``
    projects a failing check to exit ``2``)."""
    cache_dir = resolve_cache_dir()
    if cache_dir is None:
        return DoctorCheck(
            name="osv-db",
            ok=False,
            message=(
                f"{OSV_DB_CACHE_ENV_VAR} is unset or empty -- no offline "
                "OSV database configured"
            ),
        )
    zip_path = db_zip_path(cache_dir)
    if zip_path is None or not _db_has_valid_advisory(zip_path):
        return DoctorCheck(
            name="osv-db",
            ok=False,
            message=(
                f"no usable offline OSV database found under {cache_dir!r} "
                "(absent, empty, or content-corrupt)"
            ),
        )
    try:
        snapshot_at = db_snapshot_at(zip_path)
    except OSError:
        # Review finding (2026-07-24): TOCTOU -- the db can vanish/become
        # unreadable between _db_has_valid_advisory's own read above and
        # this stat call. Left uncaught, this OSError would escape all the
        # way to main()'s last-resort net, turning a --doctor health-check
        # into a raw traceback instead of naming the osv-db problem
        # (mirrors _doctor_check_feed's own identical TOCTOU guard below).
        return DoctorCheck(
            name="osv-db",
            ok=False,
            message=(
                f"offline OSV database under {cache_dir!r} became unreadable "
                "while checking its snapshot"
            ),
        )
    if is_db_stale(snapshot_at, DB_MAX_AGE_DAYS, now=datetime.now(UTC)):
        return DoctorCheck(
            name="osv-db",
            ok=False,
            message=(
                f"offline OSV database is stale or future-dated (snapshot "
                f"{snapshot_at}, max age {DB_MAX_AGE_DAYS}d)"
            ),
        )
    return DoctorCheck(
        name="osv-db", ok=True, message=f"snapshot {snapshot_at} (fresh)"
    )


def _doctor_check_feed(
    feed_name: str,
    cache_path: Callable[[str | Path], Path],
    loader: Callable[[Path], Mapping[str, object] | None],
    *,
    absent_hint: str,
    stale_hint: str,
    stale_is_problem: bool = False,
) -> DoctorCheck:
    """One optional feed self-check, consulted UNCONDITIONALLY (never gated
    on ``--fail-on-kev``/``--min-epss``/currency flags — ``--doctor``
    reports environment operability regardless of which gates a LATER real
    scan might enable). An ABSENT feed is ``ok=True`` with an explicit
    "operating air-gapped" message (NFR-U2's air-gap framing: a missing
    OPTIONAL feed is the expected offline default, never a doctor failure);
    a PRESENT-but-unloadable feed file (unreadable, invalid JSON, wrong
    shape, or a directory squatting on the path) is ``ok=False`` naming the
    file — an operator who provisioned the feed must not be told it does
    not exist (review finding 2026-07-24; mirrors ``_doctor_check_osv_db``'s
    own content-corrupt handling one check up). ``absent_hint``/
    ``stale_hint`` carry the PER-FEED scan-time consequence (review finding
    2026-07-24: KEV's absent-feed consequence under the shipped
    ``fail_on_kev=True`` default is a whole-axis ``indeterminate``/exit-1,
    not "offline default assumed" — the feeds genuinely differ here, since
    ``min_epss`` defaults to ``None``). ``stale_is_problem`` makes a
    PRESENT-but-stale feed ``ok=False`` for the one feed whose gate is on
    by default (KEV): a stale KEV feed makes every default-config scan
    compose ``indeterminate`` — the same class of environment rot as a
    stale offline OSV DB one check up, so reporting it ``ok``/exit-0 would
    machine-readably green-light an environment whose default scan cannot
    produce a trusted verdict (review finding 2026-07-24; the message-level
    hint alone was not enough). Feeds with no default gate (EPSS,
    endoflife) keep the informational ``ok=True`` stale treatment."""
    check_name = f"{feed_name}-feed"
    air_gapped = DoctorCheck(
        name=check_name,
        ok=True,
        message=(
            f"operating air-gapped: {feed_name} feed not present -- "
            f"{absent_hint}"
        ),
    )
    cache_dir = feeds.resolve_cache_dir()
    if cache_dir is None:
        return air_gapped
    path = cache_path(cache_dir)
    catalog = loader(path)
    if catalog is None:
        try:
            # exists(), not is_file() (review finding 2026-07-24): a
            # directory (or other non-file) squatting on the feed path is
            # present-but-unusable -- classifying it "not present" would
            # report a provisioning mistake as healthy air-gapped operation.
            feed_file_present = path.exists()
        except OSError:
            feed_file_present = False
        if not feed_file_present:
            # Absent (or vanished mid-check — the same TOCTOU treatment as
            # _kev_enrichment's): the expected air-gapped default.
            return air_gapped
        return DoctorCheck(
            name=check_name,
            ok=False,
            message=(
                f"{feed_name} feed file present at {path} but unreadable "
                "or invalid -- refresh or remove it"
            ),
        )
    try:
        provenance = feeds.feed_provenance(
            source=str(path),
            path=path,
            max_age_days=feeds.DEFAULT_FEED_MAX_AGE_DAYS,
            now=datetime.now(UTC),
        )
    except OSError:
        # TOCTOU: the cache vanished between the load above and this stat --
        # treat exactly like "no usable feed" (mirrors _kev_enrichment's own
        # TOCTOU handling).
        return air_gapped
    if not provenance.max_age_ok:
        return DoctorCheck(
            name=check_name,
            ok=not stale_is_problem,
            message=(
                f"{feed_name} feed present but stale (snapshot "
                f"{provenance.snapshot_at}) -- {stale_hint}"
            ),
        )
    return DoctorCheck(
        name=check_name,
        ok=True,
        message=(
            f"{feed_name} feed present, snapshot {provenance.snapshot_at} "
            "(fresh)"
        ),
    )


def run_doctor_checks(target: Path) -> tuple[DoctorCheck, ...]:
    """Story 5.1 (D8)'s ``--doctor`` aggregation: the deptry/osv-scanner
    version pre-flight, the offline OSV-DB pre-flight, and the
    KEV/EPSS/endoflife feed checks — all read-only local filesystem +
    ``--version`` subprocess work, NEVER a network call by design. (The
    autouse socket-deny harness, ``tests/meta/test_socket_deny_alive.py``,
    enforces that for the IN-PROCESS half only — the ``--version`` child
    processes run outside its reach and are trusted to be local-only;
    review finding 2026-07-24: don't overclaim the harness's coverage.) No
    config parameter: every check below is constant-driven, never
    policy-driven (mirrors ``_check_engine_version``'s own config-
    independent shape) — ``cli.py``'s ``_run_doctor`` calls this BEFORE any
    discovery/extraction/policy/engine-scan work happens. Order is fixed
    (deptry, osv-scanner, osv-db, kev-feed, epss-feed, endoflife-feed) —
    ``--format text`` renders it verbatim; ``--format json`` sorts by
    ``name`` instead (its own small ad-hoc, non-schema document)."""
    return (
        _doctor_check_engine(
            name="deptry",
            argv=["deptry", "--version"],
            version_pattern=_DEPTRY_VERSION_PATTERN,
            expected=DEPTRY_VERSION_RANGE,
            cwd=target,
        ),
        _doctor_check_engine(
            name="osv-scanner",
            argv=["osv-scanner", "--version"],
            version_pattern=_OSV_SCANNER_VERSION_PATTERN,
            expected=OSV_SCANNER_VERSION_RANGE,
            cwd=target,
        ),
        _doctor_check_osv_db(),
        _doctor_check_feed(
            "kev",
            feeds.kev_cache_path,
            feeds.load_kev_catalog,
            # Truthful under the SHIPPED default (config.EffectiveConfig's
            # fail_on_kev=True): without this feed, a default-config scan's
            # vulnerability axis composes indeterminate (exit 1) — never
            # "offline default assumed" (review finding 2026-07-24).
            absent_hint=(
                "the default fail-on-kev gate will compose indeterminate "
                "on the vulnerability axis until the feed is provisioned "
                "or the gate is explicitly disabled"
            ),
            stale_hint=(
                "the default fail-on-kev gate will compose indeterminate "
                "on the vulnerability axis until the feed is refreshed "
                "or the gate is explicitly disabled"
            ),
            # Present-but-stale KEV is ok=False (review finding 2026-07-24):
            # under the shipped fail_on_kev=True default, a stale feed
            # blocks every scan's trusted verdict exactly like a stale OSV
            # DB -- doctor must not exit 0 for it.
            stale_is_problem=True,
        ),
        _doctor_check_feed(
            "epss",
            feeds.epss_cache_path,
            feeds.load_epss_scores,
            # EPSS genuinely IS optional: min_epss defaults to None, so no
            # scan consults this feed unless --min-epss is passed.
            absent_hint="no EPSS gate is active unless --min-epss is passed",
            stale_hint=(
                "an EPSS gate (--min-epss) would compose indeterminate "
                "off a stale feed; no gate is active without --min-epss"
            ),
        ),
        _doctor_check_feed(
            "endoflife",
            feeds.endoflife_cache_path,
            feeds.load_endoflife_snapshot,
            # The currency axis's tier-2 source (Story 6.3) -- the third
            # sibling under the SAME feed-cache root (review finding
            # 2026-07-24: doctor checked KEV/EPSS but skipped the one feed
            # the currency axis actually reads). No default gate:
            # currency_gating activates only via the flags named below.
            absent_hint=(
                "no currency gate is active unless --max-lag/--require-lts/"
                "--fail-on-eol is passed"
            ),
            stale_hint=(
                "an active currency gate (--max-lag/--require-lts/"
                "--fail-on-eol) skips the stale snapshot and components "
                "degrade to currency:unknown -- indeterminate under that "
                "gate; no gate is active without those flags"
            ),
        ),
    )


class NullEngine:
    """The no-op engine: assesses nothing, contributes nothing.

    Retained from 1.2 so its unit contract is unchanged; it exists so the
    pipeline runs end-to-end through the real seam even before a real engine
    contributes."""

    name: str = "null"
    axis: str = AXIS_INGESTION

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        return EngineResult(findings=(), errors=(), coverage=(), axis=self.axis)


def _deptry_requirements_sources(target: Path) -> list[str]:
    """The requirements-file paths deptry itself would read for ``target`` —
    what the unconditional ``--requirements-files`` front-door flag must
    RE-APPEND to remain behavior-preserving (the flag REPLACES deptry's
    requirements-source setting, it never merges — verified live against
    deptry 0.25.1).

    Deptry's source list is its ``[tool.deptry].requirements_files`` config
    when declared (a string or list of strings in the scan root's
    ``pyproject.toml``), else its documented default ``requirements.txt`` —
    re-appending only the literal default used to false-DEP001 every dep a
    config-declared file carries (fixed 2026-07-16; the parallel
    ``requirements_files_dev`` setting needs no handling — we never pass its
    flag, so deptry's own config/default for it stays live). Unreadable/
    malformed config degrades to the default: deptry's own run against the
    same file will surface the real problem loudly.

    Existence filtering is stat-honest (``discovery.py``'s doctrine —
    ``Path.is_file()`` swallows every ``OSError``): a definitively-absent
    path is dropped (deptry crashes outright on a nonexistent
    ``--requirements-files`` entry, unlike its tolerant native default), but
    an AMBIGUOUS stat failure (EACCES, ...) keeps the path — deptry then
    fails loudly into a typed engine error, matching its native behavior on
    the same unreadable file, rather than silently false-DEP001ing every dep
    the file declares. A path containing ``,`` or a newline is skipped: the
    flag's own comma-list syntax cannot express it."""
    configured: object = None
    try:
        with (target / "pyproject.toml").open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        data = None
    if isinstance(data, dict):
        tool = data.get("tool")
        if isinstance(tool, dict):
            deptry_config = tool.get("deptry")
            if isinstance(deptry_config, dict):
                configured = deptry_config.get("requirements_files")
    if isinstance(configured, str):
        candidates = [configured]
    elif isinstance(configured, list) and all(
        isinstance(item, str) for item in configured
    ):
        candidates = list(configured)
    else:
        candidates = ["requirements.txt"]
    target_resolved = target.resolve()
    sources: list[str] = []
    for candidate in candidates:
        if not candidate or "," in candidate or "\n" in candidate:
            continue
        raw = Path(candidate)
        if raw.is_absolute() or ".." in raw.parts:
            continue
        resolved = (target_resolved / raw).resolve()
        try:
            resolved.relative_to(target_resolved)
        except ValueError:
            continue
        try:
            os.stat(resolved)
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError:
            pass  # ambiguous: keep — deptry fails loud, never silently
        sources.append(candidate)
    return sources


class DeptryEngine:
    """The first real engine: dependency-hygiene via ``deptry`` (Story 1.3).

    Runs ``deptry . -o <tempfile> --no-ansi`` with ``cwd=target`` so deptry
    reads the project's OWN ``pyproject.toml`` — honoring ``[tool.deptry]``
    (``ignore``/``per_rule_ignores``/``exclude``) NATIVELY (FR9) — and writes
    its machine output to a system-temp file we read (the pure-JSON-stdout
    seam: deptry's own chatter never touches our streams). deptry's exit code
    is ignored; the DEP001–DEP005 records become ``hygiene:<code>:<module>``
    findings, and on a successful run the hygiene axis reports
    ``deps_assessed == len(synthesized.lines)`` (Story 1.7 — counts ONLY
    what actually reached deptry's front-door, exactly mirroring
    ``OsvEngine.run``'s own ``deps_assessed=len(synthesized.lines)``
    formula byte-for-byte; deliberately NOT ``inventory.count -
    len(excluded)``, which over-counts a THIRD bucket
    ``_synthesize_deptry_frontdoor`` silently ``continue``s past —
    ``hygiene_covered=False`` or no resolved ``pypi_identity`` — into
    neither ``lines`` nor ``excluded``). Deptry silently resolving nothing
    due to its OWN internal config/layout (a non-standard project layout,
    or an over-broad ``exclude``) is a distinct, still-open gap this story
    does NOT attempt to detect — deptry's JSON output carries no
    analyzed-count signal for it; left to a future coverage-floor gate
    (Story 3.1/FR19).

    Story 2.2 (FR8's conda half) ALWAYS additionally synthesizes a
    ``--requirements-files <tempfile>`` front-door from the inventory (see
    ``hygiene._synthesize_deptry_frontdoor`` and the module docstring) —
    unconditionally, never conditionally detected: deptry's own native
    ``pyproject.toml`` detection takes priority when present, so this is a
    no-op for every pre-2.2 pyproject-native scan and a real signal for a
    conda-sourced one. Because the flag REPLACES (not merges with) deptry's
    own requirements-source setting — the config-declared
    ``[tool.deptry].requirements_files`` list when present, else the
    ``requirements.txt`` default — deptry's own effective source list is
    re-appended to the flag's comma-list so its pip-declared deps stay
    visible to deptry (fixed 2026-07-16 — verified live: without this, such
    a scan reports false DEP001s for every dep those files declare; see
    ``_deptry_requirements_sources`` for the config-read + stat-honest
    existence rules). The synthesized input file uses the SAME
    ``tempfile.mkstemp``/``finally: os.unlink`` idiom as ``OsvEngine.run``'s
    own input file (NFR-S4). Any component the NFR-S6 purity guard excludes
    from that front-door surfaces as one ``indeterminate:unsafe-identity-
    hygiene:<pkg>`` finding via ``hygiene.unsafe_identity_finding`` (Fix 6,
    2026-07-16; the reason segment is deliberately distinct from the
    vuln-axis twin's so the policy layer's id-keyed dedupe can never drop
    one axis's record) — computed up front and merged into EVERY return
    path below, mirroring ``OsvEngine.run``'s own never-silently-dropped
    handling of its parallel-shaped ``excluded_findings``.

    Story 6.6 (FR21): a ``--version`` pre-flight (``_check_engine_version``)
    gates the top of ``run()``, right after ``excluded_findings`` is
    computed — deptry ALWAYS invokes the real subprocess below, so the gate
    is unconditional. A failing check never invokes the real deptry
    subprocess and preserves ``excluded_findings`` exactly like the
    ``mkstemp`` ``OSError`` branch immediately below it."""

    name: str = "deptry"
    axis: str = AXIS_HYGIENE

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        synthesized = _synthesize_deptry_frontdoor(inventory.components)
        excluded_findings = tuple(
            sorted(
                (
                    (
                        hygiene_no_identity_finding(c)
                        if c.pypi_identity is None
                        else hygiene_unsafe_identity_finding(c)
                    )
                    for c in synthesized.excluded
                ),
                key=lambda f: f.id,
            )
        )
        # Story 6.6 (FR21): the version pre-flight gates EVERY run — deptry
        # always invokes the real subprocess below, so the gate is
        # unconditional. A failure never drops the purity guard's own
        # findings, mirroring the mkstemp OSError branch immediately below.
        version_error = _check_engine_version(
            owner=self.name,
            argv=["deptry", "--version"],
            version_pattern=_DEPTRY_VERSION_PATTERN,
            expected=DEPTRY_VERSION_RANGE,
            cwd=target,
        )
        if version_error is not None:
            return EngineResult(
                findings=excluded_findings,
                errors=(version_error,),
                coverage=(),
                axis=self.axis,
            )
        try:
            handle, input_path = tempfile.mkstemp(
                suffix=".txt", prefix="pdos-deptry-frontdoor-"
            )
        except OSError as exc:
            return EngineResult(
                findings=excluded_findings,
                errors=(
                    ErrorRecord(
                        kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                        owner=self.name,
                        message=(
                            "could not create a temp deptry front-door "
                            f"input file: {exc.__class__.__name__}"
                        ),
                    ),
                ),
                coverage=(),
                axis=self.axis,
            )
        try:
            os.close(handle)
            content = "\n".join(synthesized.lines)
            if content:
                content += "\n"
            Path(input_path).write_text(content, encoding="utf-8")
            # Passing --requirements-files REPLACES deptry's own
            # requirements-source setting (config-declared
            # `[tool.deptry].requirements_files` OR its `requirements.txt`
            # default) rather than merging with it (verified live against
            # deptry 0.25.1) -- so a conda-sourced scan would lose every
            # pip-declared dep those files carry to false DEP001s.
            # Re-appending deptry's own effective source list (comma syntax
            # per `deptry --help`; relative, resolved against cwd=target
            # exactly as deptry itself would -- see
            # `_deptry_requirements_sources`) keeps that behavior intact
            # (fixed 2026-07-16; originally only the literal default
            # `requirements.txt` was re-appended, which still clobbered a
            # config-declared file list). Still a genuine no-op for
            # pyproject-native scans: deptry ignores the flag entirely there.
            requirements_files = ",".join(
                [input_path, *_deptry_requirements_sources(target)]
            )
            # exit_code is ignored: deptry's 0/1 stay content-only (Story 1.5
            # widened the seam for osv's own operational-exit-code needs).
            text, error, _exit_code = _engine_env(
                lambda output_path: [
                    "deptry",
                    ".",
                    "-o",
                    output_path,
                    "--no-ansi",
                    "--requirements-files",
                    requirements_files,
                ],
                owner=self.name,
                cwd=target,
            )
        finally:
            try:
                os.unlink(input_path)
            except OSError:
                pass
        if error is not None:
            return EngineResult(
                findings=excluded_findings,
                errors=(error,),
                coverage=(),
                axis=self.axis,
            )
        parse = parse_deptry_output(text or "")
        if not parse.output_parsed:
            # Top-level garbage (undecodable/non-array): fail loud, no
            # coverage claim (nothing was assessed) — the purity guard's own
            # findings still survive (never silently dropped).
            return EngineResult(
                findings=excluded_findings,
                errors=parse.errors,
                coverage=(),
                axis=self.axis,
            )
        coverage = (
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=0,
                manifests_parsed=0,
                deps_total=inventory.count,
                # Counts ONLY what actually reached deptry's front-door —
                # exactly OsvEngine.run's own deps_assessed=len(synthesized
                # .lines) formula (Story 1.7). Covered-but-no-identity and
                # NFR-S6 exclusions land on ``excluded`` (AUD-WARDEN-018);
                # uncovered deps stay for DefaultPolicy — neither bucket is
                # counted as assessed.
                deps_assessed=len(synthesized.lines),
                resolution_depth=None,
            ),
        )
        findings = tuple(
            sorted((*excluded_findings, *parse.findings), key=lambda f: f.id)
        )
        return EngineResult(
            findings=findings,
            errors=parse.errors,
            coverage=coverage,
            axis=self.axis,
        )


# Bounded osv-scanner subprocess timeout (seconds). Offline scans are
# sub-second in practice (empirically observed in the Story 1.4 spike); a
# generous fixed default until Story 3.1's config surface lands. Not in
# {1, 2, 130}, so the sole-ownership exit-literal guard never mistakes it for
# an exit code.
OSV_TIMEOUT_SECONDS = 120


def _withheld_findings(candidates: list[Component]) -> tuple[Finding, ...]:
    """One ``indeterminate:offline-db-unavailable:<pkg>`` finding per
    candidate — shared by the pre-flight-failure and the osv-exit-128 (no
    packages found) paths, which the decision record treats identically
    (coverage-skipped, never a confident clean). Callers pass BOTH
    exact-match and name-level candidates on a pre-flight failure (Story
    2.5): with no usable DB, neither kind can be assessed."""
    return tuple(offline_db_unavailable_finding(component) for component in candidates)


def _name_level_findings(
    zip_path: Path, name_level_candidates: list[Component]
) -> tuple[Finding, ...]:
    """One ``indeterminate:name-level-critical-cve:<pkg>@unspecified``
    finding per mapped-but-unversioned candidate whose resolved PyPI name
    carries >=1 CRITICAL advisory in the offline DB at ANY version (FR13) —
    an enrichment ADDED on top of the baseline withheld finding
    ``DefaultPolicy`` already derives for it, never a replacement. Computed
    via a direct zip read, never a second ``osv-scanner`` subprocess."""
    findings: list[Finding] = []
    index = build_name_level_critical_index(zip_path)
    for component in name_level_candidates:
        if component.pypi_identity is None:
            continue  # defensive: the caller's own filter already excludes this
        advisory_ids = name_level_critical_advisory_ids(
            zip_path, component.pypi_identity.name, index=index
        )
        if advisory_ids:
            findings.append(name_level_critical_cve_finding(component, advisory_ids))
    return tuple(sorted(findings, key=lambda f: f.id))


# --- Story 6.4 (FR36): CISA KEV enrichment -----------------------------------


def _kev_enrichment(
    fail_on_kev: bool,
) -> tuple[dict[str, str] | None, FeedProvenance | None, tuple[Finding, ...]]:
    """Consult the KEV feed (``feeds.py``) ONCE per ``OsvEngine.run`` call —
    mirrors the class docstring's "staleness computed ONCE" precedent for
    the OSV DB itself, one level up (feed provenance, not advisory
    content). Returns ``(catalog, kev_data, kev_axis_findings)``:

    * ``fail_on_kev=False`` -> ``(None, None, ())`` — the KEV cache is
      never even opened (matrix row 3).
    * The feed is absent/unreadable/content-corrupt -> ``(None, None,
      (kev_stale_finding(unavailable=True),))`` — no catalog to match
      against, so every ``vuln:`` finding's ``kev`` stays ``None``.
    * The feed loads but is stale -> ``(catalog, kev_data, (kev_stale_
      finding(unavailable=False),))`` — matrix row 5: per-finding matching
      still runs against the loaded (if aged) catalog; the whole axis is
      independently forced ``indeterminate`` by the returned finding.
    * The feed loads and is fresh -> ``(catalog, kev_data, ())``."""
    if not fail_on_kev:
        return None, None, ()
    cache_dir = feeds.resolve_cache_dir()
    if cache_dir is None:
        return None, None, (kev_stale_finding(unavailable=True),)
    path = feeds.kev_cache_path(cache_dir)
    catalog = feeds.load_kev_catalog(path)
    if catalog is None:
        return None, None, (kev_stale_finding(unavailable=True),)
    try:
        kev_data = feeds.feed_provenance(
            source=str(path),
            path=path,
            max_age_days=feeds.DEFAULT_FEED_MAX_AGE_DAYS,
            now=datetime.now(UTC),
        )
    except OSError:
        # The cache file vanished between the catalog read above and this
        # provenance stat (TOCTOU) -- treat exactly like "no usable feed"
        # rather than letting the race propagate as an engine crash.
        return None, None, (kev_stale_finding(unavailable=True),)
    kev_findings = () if kev_data.max_age_ok else (kev_stale_finding(unavailable=False),)
    return catalog, kev_data, kev_findings


def _stamp_kev(
    findings: tuple[Finding, ...],
    catalog: Mapping[str, str] | None,
    kev_candidates: Mapping[str, tuple[str, ...]],
) -> tuple[Finding, ...]:
    """Stamp ``kev``/``kev_date`` onto every ``vuln:`` finding via
    ``dataclasses.replace`` (this module's sole enrichment site — BEFORE
    ``EngineResult`` is returned, per the class docstring's hard
    positioning invariant: ``interfaces.py``'s engine-dedup loop must
    never see an un-stamped finding). Every non-``vuln:`` finding (the
    axis's own ``indeterminate:`` withhold/name-level/stale findings)
    passes through unchanged — KEV enrichment only ever concerns a real
    per-advisory match. ``catalog=None`` (KEV never consulted, or
    unavailable) is a no-op: every finding is returned as-is, so ``kev``
    stays its default ``None`` (matrix rows 3/4)."""
    if catalog is None:
        return findings
    stamped: list[Finding] = []
    for finding in findings:
        if not finding.id.startswith("vuln:"):
            stamped.append(finding)
            continue
        date_added = kev_match(kev_candidates.get(finding.id, ()), catalog)
        stamped.append(
            dataclasses.replace(
                finding, kev=date_added is not None, kev_date=date_added
            )
        )
    return tuple(stamped)


# --- Story 6.7 (FR: --min-epss): FIRST.org EPSS enrichment -------------------


def _epss_enrichment(
    min_epss: float | None,
) -> tuple[dict[str, tuple[float, float]] | None, FeedProvenance | None, tuple[Finding, ...]]:
    """Consult the EPSS feed (``feeds.py``) ONCE per ``OsvEngine.run`` call —
    mirrors ``_kev_enrichment`` structurally, one feed over. Returns
    ``(scores, epss_data, epss_axis_findings)``:

    * ``min_epss is None`` -> ``(None, None, ())`` — the EPSS cache is never
      even opened (gate off).
    * The feed is absent/unreadable/content-corrupt -> ``(None, None,
      (epss_stale_finding(unavailable=True),))`` — no catalog to match
      against, so every ``vuln:`` finding's ``epss`` stays its default
      ``None``.
    * The feed loads but is stale -> ``(scores, epss_data, (epss_stale_
      finding(unavailable=False),))`` — per-finding matching still runs
      against the loaded (if aged) catalog; the whole axis is independently
      forced ``indeterminate`` by the returned finding.
    * The feed loads and is fresh -> ``(scores, epss_data, ())``."""
    if min_epss is None:
        return None, None, ()
    cache_dir = feeds.resolve_cache_dir()
    if cache_dir is None:
        return None, None, (epss_stale_finding(unavailable=True),)
    path = feeds.epss_cache_path(cache_dir)
    scores = feeds.load_epss_scores(path)
    if scores is None:
        return None, None, (epss_stale_finding(unavailable=True),)
    try:
        epss_data = feeds.feed_provenance(
            source=str(path),
            path=path,
            max_age_days=feeds.DEFAULT_FEED_MAX_AGE_DAYS,
            now=datetime.now(UTC),
        )
    except OSError:
        # The cache file vanished between the catalog read above and this
        # provenance stat (TOCTOU) -- treat exactly like "no usable feed"
        # rather than letting the race propagate as an engine crash (mirrors
        # _kev_enrichment's own TOCTOU handling).
        return None, None, (epss_stale_finding(unavailable=True),)
    epss_findings = (
        () if epss_data.max_age_ok else (epss_stale_finding(unavailable=False),)
    )
    return scores, epss_data, epss_findings


def _stamp_epss(
    findings: tuple[Finding, ...],
    scores: Mapping[str, tuple[float, float]] | None,
    kev_candidates: Mapping[str, tuple[str, ...]],
) -> tuple[Finding, ...]:
    """Stamp ``epss`` onto every ``vuln:`` finding via ``dataclasses.replace``
    (called alongside ``_stamp_kev``, BEFORE ``EngineResult`` is returned —
    the same hard positioning invariant). Every non-``vuln:`` finding passes
    through unchanged. ``scores=None`` (EPSS never consulted, or
    unavailable) is a no-op: every finding is returned as-is.

    Unlike ``_stamp_kev``, which always stamps ``kev``/``kev_date`` (``True``
    or ``False``) once a catalog loads, there is no boolean equivalent for
    "no EPSS match" — only an actual match calls ``dataclasses.replace``;
    a finding with no match is returned unchanged, leaving ``finding.epss``
    at its existing ``None`` default (design note: ``finding.epss is None``
    IS the "no data" signal, never a separate flag).

    Review finding (two passes): ``feeds.load_epss_scores`` now filters
    non-finite/out-of-``[0, 1]`` entries at load time — a domain-corrupt
    cache entry never reaches this function through the normal path, so a
    matched entry is trustworthy by construction. The ``try/except
    ValueError`` around ``models.Epss`` construction stays as a last-resort
    crash-guard (e.g. against future drift between the load filter and
    ``Epss.__post_init__``): if it ever fires, degrade the SAME way a
    non-match already does (skip the stamp), never raise past this function
    and crash the whole scan."""
    if scores is None:
        return findings
    stamped: list[Finding] = []
    for finding in findings:
        if not finding.id.startswith("vuln:"):
            stamped.append(finding)
            continue
        pair = epss_match(kev_candidates.get(finding.id, ()), scores)
        if pair is None:
            stamped.append(finding)
            continue
        score, percentile = pair
        try:
            epss = Epss(score=score, percentile=percentile)
        except ValueError:
            stamped.append(finding)
            continue
        stamped.append(dataclasses.replace(finding, epss=epss))
    return tuple(stamped)


class OsvEngine:
    """The second real engine: vulnerability matching via ``osv-scanner``,
    fully offline (Story 1.5), widened with two honesty tiers (Story 2.5).

    Feeds ``vuln_matchable`` components (``candidates`` — any ecosystem with
    a resolved ``pypi_identity``, Story 2.1) through the real ``osv-scanner``
    subprocess, AND
    separately, mapped-but-unversioned components (``pypi_identity``
    resolved, ``version is None`` — ``name_level_candidates``, likewise any
    ecosystem since Story 2.1) through a
    direct, offline, in-process read of the SAME resolved DB zip (FR13 —
    osv-scanner has no "any version" query mode, so this is never a second
    subprocess). The candidate guard is widened to cover BOTH: a scan with
    ONLY name-level candidates still reaches the DB pre-flight rather than
    bailing out empty.

    A CONTENT pre-flight against the resolved offline DB (decision record
    § 4 — NOT a mere existence/non-emptiness check) runs BEFORE any
    subprocess: a DB that fails it means osv is never invoked and every
    candidate (exact AND name-level) withholds via one
    ``indeterminate:offline-db-unavailable:<pkg>`` finding (never a
    confident clean). Once the pre-flight passes, staleness (FR12) is
    computed ONCE from that SAME ``zip_path``/``snapshot_at`` — a stale or
    future-dated DB adds one whole-axis ``indeterminate:vuln-data-stale:
    vuln-database`` finding, merged into every content-bearing (exit
    ``{0,1}``, or name-level-only) result, so the WHOLE vulnerability axis
    for that scan lands ``indeterminate`` rather than a trusted clean/
    policy-violation off untrustworthy data. An NFR-S6 purity guard excludes
    any exact-match candidate whose resolved pypi identity is not a safe
    token, each with its own ``indeterminate:unsafe-identity:<pkg>``
    finding; the safe remainder is synthesized into a sorted
    ``name==version`` temp input file and run through ``_engine_env`` with
    the DB cache dir injected via ``extra_env`` and the pip-requirements
    parser forced via ``-L requirements.txt:<path>`` (decision record § 9 —
    the temp file's own name/extension is irrelevant); when there are NO
    exact-match candidates at all, this subprocess step is skipped
    entirely. osv's exit code is READ AS CONTENT beyond 0/1 (the DB-absent
    cold start would otherwise false-green — decision record § 4): 0/1
    parse for vulnerabilities, 127 (after a passing pre-flight — an
    anomaly, e.g. TOCTOU) is a typed engine error, 128 (no packages found)
    mirrors the pre-flight-failure withholding, and any other code is a
    typed engine error — the name-level findings, having been computed
    independently of the subprocess, survive every one of these paths.

    Story 6.4 (FR36): ``fail_on_kev`` (default ``True``) gates a THIRD,
    independent consultation — the CISA KEV feed (``feeds.py`` +
    ``vuln.py``'s KEV helpers), computed ONCE per run right alongside
    staleness (``_kev_enrichment``, called immediately after
    ``stale_findings`` below) and merged into every content-bearing
    result the same way ``stale_findings`` already is. When it produces a
    usable catalog, every ``vuln:`` finding is stamped ``kev``/``kev_date``
    via ``_stamp_kev`` BEFORE this method returns its ``EngineResult`` —
    a hard positioning invariant: ``interfaces.py``'s engine-dedup loop
    must never see an un-stamped finding.

    Story 6.7: ``min_epss`` (default ``None`` — gate off) gates a FOURTH,
    independent consultation — the FIRST.org EPSS feed — computed ONCE per
    run alongside KEV (``_epss_enrichment``, called right next to
    ``_kev_enrichment``) and merged into every content-bearing result the
    same way. Every ``vuln:`` finding is stamped ``epss`` via ``_stamp_epss``
    BEFORE this method returns its ``EngineResult``, same hard positioning
    invariant — but unlike ``kev``/``kev_date``, ``epss`` is stamped ONLY on
    an actual match (see ``_stamp_epss``'s own docstring).

    Story 6.6 (FR21): a ``--version`` pre-flight (``_check_engine_version``)
    gates the ONE branch that actually shells out to ``osv-scanner`` —
    placed immediately after the ``if not synthesized.lines:`` early-return
    (every early-return above it — no candidates, DB unavailable, purity
    guard excludes everything — never invoked the real subprocess before
    this story and still doesn't invoke the version check either). A
    failing check returns the same excluded/name-level/stale/KEV/EPSS
    findings tuple the adjacent ``mkstemp`` ``OSError`` branch already
    assembles — never silently dropped."""

    name: str = "osv-scanner"
    axis: str = AXIS_VULNERABILITY

    def __init__(self, *, fail_on_kev: bool = True, min_epss: float | None = None) -> None:
        self.fail_on_kev = fail_on_kev
        self.min_epss = min_epss

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        # Ecosystem-agnostic (Story 2.1): a resolved pypi_identity is the
        # matchable signal, not the component's own (conda/pypi) ecosystem —
        # otherwise a correctly-mapped conda component would be silently
        # invisible to osv-scanner (the pytorch->torch false-green Gap C
        # closes only when this filter admits it).
        candidates = [
            component
            for component in inventory.components
            if component.pypi_identity is not None and component.vuln_matchable
        ]
        name_level_candidates = [
            component
            for component in inventory.components
            if component.pypi_identity is not None and component.version is None
        ]
        if not candidates and not name_level_candidates:
            return EngineResult(findings=(), errors=(), coverage=(), axis=self.axis)

        cache_dir = resolve_cache_dir()
        zip_path = db_zip_path(cache_dir) if cache_dir is not None else None
        if cache_dir is None or zip_path is None or not _db_has_valid_advisory(zip_path):
            return EngineResult(
                findings=_withheld_findings([*candidates, *name_level_candidates]),
                errors=(),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
            )

        snapshot_at = db_snapshot_at(zip_path)
        stale = is_db_stale(snapshot_at, DB_MAX_AGE_DAYS, now=datetime.now(UTC))
        name_level_findings = _name_level_findings(zip_path, name_level_candidates)
        stale_findings = (stale_vuln_data_finding(),) if stale else ()
        # Story 6.4 (FR36): consulted ONCE here, right alongside the OSV DB's
        # own staleness above — merged into every content-bearing result
        # below the exact same way stale_findings already is (see class
        # docstring). `catalog` feeds `_stamp_kev` below; `kev_findings` is
        # the 0-or-1 whole-axis KEV-provenance indeterminate finding.
        catalog, kev_data, kev_findings = _kev_enrichment(self.fail_on_kev)
        # Story 6.7: the EPSS sibling consultation, same "computed ONCE,
        # merged into every content-bearing result" treatment as KEV above.
        scores, epss_data, epss_findings = _epss_enrichment(self.min_epss)

        if not candidates:
            # Name-level-only scan: osv-scanner has no "any version" query
            # mode, so this never invokes the subprocess at all.
            findings = tuple(
                sorted(
                    (
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            vuln_data = VulnData(
                source=str(zip_path), snapshot_at=snapshot_at, max_age_ok=not stale
            )
            return EngineResult(
                findings=findings,
                errors=(),
                coverage=(),
                axis=self.axis,
                vuln_data=vuln_data,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        synthesized = _synthesize_requirements(candidates)
        excluded_findings = tuple(
            sorted(
                (unsafe_identity_finding(c) for c in synthesized.excluded),
                key=lambda f: f.id,
            )
        )
        if not synthesized.lines:
            # Every candidate was excluded by the purity guard: nothing left
            # to feed osv, but the name-level scan already ran independently
            # (NFR-S6/FR13 — never silently dropped). The DB was still
            # genuinely consulted for that name-level scan (same zip_path/
            # snapshot_at as every other content-bearing path), so vuln_data
            # and any stale finding must survive here too — review finding,
            # 2026-07-16: this branch previously dropped both, contradicting
            # the AC that vuln_data records DB source+timestamp whenever the
            # DB was actually read.
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            vuln_data = VulnData(
                source=str(zip_path), snapshot_at=snapshot_at, max_age_ok=not stale
            )
            return EngineResult(
                findings=findings,
                errors=(),
                coverage=(),
                axis=self.axis,
                vuln_data=vuln_data,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        # Story 6.6 (FR21): the version pre-flight sits immediately before
        # the ONE branch that actually shells out to osv-scanner — every
        # early-return above (no candidates, DB unavailable, name-level-only)
        # never invoked the real subprocess before this story and must keep
        # not invoking the version check either. A failure here returns the
        # SAME merged findings tuple the adjacent mkstemp OSError branch
        # below already assembles (NFR-S6/FR13 — never silently dropped).
        version_error = _check_engine_version(
            owner=self.name,
            argv=["osv-scanner", "--version"],
            version_pattern=_OSV_SCANNER_VERSION_PATTERN,
            expected=OSV_SCANNER_VERSION_RANGE,
            cwd=target,
        )
        if version_error is not None:
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(version_error,),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        try:
            handle, input_path = tempfile.mkstemp(
                suffix=".txt", prefix="pdos-osv-input-"
            )
        except OSError as exc:
            # A distinct local name from the `_engine_env` error below (not
            # just style: reusing `error` there would reassign an
            # already-ErrorRecord-typed name from `ErrorRecord | None`, a
            # real mypy regression even though the two branches never
            # overlap at runtime).
            mkstemp_error = ErrorRecord(
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=self.name,
                message=(
                    "could not create a temp osv input file: "
                    f"{exc.__class__.__name__}"
                ),
            )
            # The purity guard already ran (candidates are known before the
            # temp file is even created): its findings must not be lost
            # just because osv itself never got to run (NFR-S6 — never
            # silently dropped). The independently-computed name-level
            # findings survive too (FR13), and so does the staleness of the
            # SAME DB they were read from (review finding, 2026-07-17).
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(mkstemp_error,),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
                kev_data=kev_data,
                epss_data=epss_data,
            )
        try:
            os.close(handle)
            Path(input_path).write_text(
                "\n".join(synthesized.lines) + "\n", encoding="utf-8"
            )
            text, error, exit_code = _engine_env(
                lambda output_path: [
                    "osv-scanner",
                    "scan",
                    "--offline",
                    "--format",
                    "json",
                    "--output-file",
                    output_path,
                    "-L",
                    f"requirements.txt:{input_path}",
                ],
                owner=self.name,
                cwd=target,
                timeout=OSV_TIMEOUT_SECONDS,
                extra_env={"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": cache_dir},
            )
        finally:
            try:
                os.unlink(input_path)
            except OSError:
                pass

        if error is not None:
            # Mirrors DeptryEngine's own error path: a spawn/timeout/decode
            # failure propagates as a typed error; the purity guard's own
            # findings AND the independently-computed name-level findings
            # survive regardless (NFR-S6/FR13 — never silently dropped), and
            # so does the staleness of the SAME DB they were read from
            # (review finding, 2026-07-17).
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(error,),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        if exit_code in (0, 1):
            parse = parse_osv_output(text or "")
            # AUD-WARDEN-011: osv exit 1 means "vulnerabilities were found".
            # If the parse produced zero `vuln:` findings, the document was
            # unusable (schema drift, truncated output, groups[] missing) —
            # never a confident clean axis. Exit 0 + empty findings remains
            # the genuine no-vulnerabilities path.
            parse_errors = list(parse.errors)
            if exit_code == 1 and not parse.findings:
                if not any(
                    err.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
                    for err in parse_errors
                ):
                    parse_errors.append(
                        ErrorRecord(
                            kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                            owner=self.name,
                            message=(
                                "osv-scanner exited 1 (vulnerabilities "
                                "reported) but no vuln: findings could be "
                                "parsed from its JSON output"
                            ),
                        )
                    )
            # Coverage is only claimed when the parse is trustworthy. An
            # unparseable document must not advertise deps_assessed == N
            # while emitting zero findings (the false-green coverage lie).
            coverage: tuple[AxisCoverage, ...] = ()
            if not parse_errors:
                coverage = (
                    AxisCoverage(
                        axis=AXIS_VULNERABILITY,
                        manifests_found=0,
                        manifests_parsed=0,
                        deps_total=inventory.count,
                        deps_assessed=len(synthesized.lines),
                        resolution_depth=None,
                    ),
                )
            vuln_data = VulnData(
                source=str(zip_path),
                snapshot_at=snapshot_at,
                max_age_ok=not stale,
            )
            # Story 6.4/6.7: the ONLY place real `vuln:` findings exist to
            # stamp -- BEFORE they are merged into `findings` and this
            # method returns (the hard positioning invariant: interfaces.py's
            # engine-dedup loop must never see an un-stamped finding). Both
            # stamps read the SAME kev_candidates set (Story 6.7 reuses it
            # verbatim, no new candidate-collection mechanism) and compose
            # freely (either, both, or neither may fire per finding).
            stamped_parse_findings = _stamp_kev(
                parse.findings, catalog, parse.kev_candidates
            )
            stamped_parse_findings = _stamp_epss(
                stamped_parse_findings, scores, parse.kev_candidates
            )
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *stamped_parse_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=tuple(parse_errors),
                coverage=coverage,
                axis=self.axis,
                # Preserve DB provenance even on parse failure (the zip was
                # read); coverage empty + errors force non-clean composition.
                vuln_data=vuln_data,
                kev_data=kev_data,
                epss_data=epss_data,
                # Story 5.1 (AC1): threaded ONLY at this real-parse success
                # site -- every other return path above/below keeps the
                # default empty mapping (nothing was actually parsed there).
                fixed_versions=parse.fixed_versions if not parse_errors else {},
            )

        if exit_code == 127:
            # A passing pre-flight but osv still failed to load the DB — an
            # anomaly (e.g. a TOCTOU DB change mid-scan), not a coverage gap.
            error_record = ErrorRecord(
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=self.name,
                message=(
                    "osv-scanner exited 127 after a passing offline-DB "
                    "content pre-flight (anomaly — e.g. the DB changed "
                    "mid-scan)"
                ),
            )
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(error_record,),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        if exit_code == 128:
            # osv found no packages to scan in the synthesized input — should
            # not normally happen given >=1 candidate, but the decision
            # record routes it identically to a failed pre-flight
            # (coverage-skipped, never a confident clean). The name-level
            # findings were computed independently of this subprocess call
            # and survive (FR13), and so does the staleness of the SAME DB
            # they were read from (review finding, 2026-07-17).
            findings = tuple(
                sorted(
                    (
                        *_withheld_findings(candidates),
                        *name_level_findings,
                        *stale_findings,
                        *kev_findings,
                        *epss_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(),
                coverage=(),
                axis=self.axis,
                vuln_data=None,
                kev_data=kev_data,
                epss_data=epss_data,
            )

        error_record = ErrorRecord(
            kind=ErrorKind.ENGINE_EXECUTION_FAILED,
            owner=self.name,
            message=f"osv-scanner exited with unexpected code {exit_code!r}",
        )
        findings = tuple(
            sorted(
                (
                    *excluded_findings,
                    *name_level_findings,
                    *stale_findings,
                    *kev_findings,
                    *epss_findings,
                ),
                key=lambda f: f.id,
            )
        )
        return EngineResult(
            findings=findings,
            errors=(error_record,),
            coverage=(),
            axis=self.axis,
            vuln_data=None,
            kev_data=kev_data,
            epss_data=epss_data,
        )


class LicenseEngine:
    """The third real engine: per-component SPDX license verdicts (Story
    6.2, axis ``"license"``). Unlike ``DeptryEngine``/``OsvEngine``, this
    engine spawns NO subprocess — ``license.license_findings`` owns the
    whole axis's substantive logic (conda's ``about: license:`` re-read,
    pypi's ``importlib.metadata`` lookup, SPDX normalization, verdict
    classification, id/finding construction); this class is a thin
    coverage-and-``EngineResult`` wrapper, mirroring ``DeptryEngine``'s/
    ``OsvEngine``'s producer-module/engine-class division of labor.

    Coverage: ``deps_assessed`` counts only components with
    ``license_covered=True`` (AUD-WARDEN-019). Today producers leave the flag
    inert/``True`` for every component, so assessed == total until a future
    producer activates structural exclusion."""

    name: str = "license"
    axis: str = AXIS_LICENSE

    def __init__(
        self,
        *,
        allow_licenses: tuple[str, ...] = (),
        deny_licenses: tuple[str, ...] = (),
    ) -> None:
        self.allow_licenses = allow_licenses
        self.deny_licenses = deny_licenses

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        findings = license_findings(
            inventory.components,
            target,
            allow_licenses=self.allow_licenses,
            deny_licenses=self.deny_licenses,
        )
        assessed = sum(1 for c in inventory.components if c.license_covered)
        coverage = (
            AxisCoverage(
                axis=AXIS_LICENSE,
                manifests_found=0,
                manifests_parsed=0,
                deps_total=inventory.count,
                deps_assessed=assessed,
                resolution_depth=None,
            ),
        )
        return EngineResult(
            findings=findings, errors=(), coverage=coverage, axis=self.axis
        )


class CurrencyEngine:
    """The fourth real engine: per-component + Python-runtime currency
    verdicts (Story 6.3, axis ``"currency"``). Mirrors ``LicenseEngine``'s
    shape exactly — ``currency.currency_findings`` owns the whole axis's
    substantive logic (tier-ladder resolution, ``!python-runtime`` sentinel,
    id/finding construction); this class is a thin coverage-and-
    ``EngineResult`` wrapper, spawning no subprocess.

    Coverage: ``deps_assessed`` counts only components with
    ``currency_covered=True`` (AUD-WARDEN-019) — same honesty rule as
    ``LicenseEngine``. Today the flag stays inert/``True``.

    Story 6.5 (NFR-S9): ``gating`` (from ``config.currency_gating``, wired
    in ``cli.py`` exactly as ``OsvEngine``'s ``fail_on_kev`` is) activates
    the freshness precondition — when active AND the bundled LTS registry is
    absent/stale (``currency_data is None`` or ``not currency_data.
    max_age_ok``), one whole-axis ``currency_stale_finding`` is appended so
    the axis lands ``indeterminate`` (never a silent pass off untrustworthy
    curated data), mirroring how ``OsvEngine`` merges ``_kev_enrichment``'s
    KEV-provenance finding. Gated on ``gating`` exactly as ``_kev_enrichment``
    gates on ``fail_on_kev``; a scan with the gate OFF is byte-identical to
    pre-6.5 (no finding appended, whatever the registry's freshness)."""

    name: str = "currency"
    axis: str = AXIS_CURRENCY

    def __init__(self, *, gating: bool = False) -> None:
        self._gating = gating

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        findings, currency_data = currency_findings(
            inventory.components, now=datetime.now(UTC)
        )
        if self._gating and (currency_data is None or not currency_data.max_age_ok):
            # NFR-S9: an absent/stale bundled registry under an active gate
            # forces the WHOLE axis indeterminate -- one provenance finding
            # merged in exactly the way OsvEngine spreads *kev_findings.
            findings = tuple(
                sorted(
                    (*findings, currency_stale_finding(unavailable=currency_data is None)),
                    key=lambda f: f.id,
                )
            )
        assessed = sum(1 for c in inventory.components if c.currency_covered)
        coverage = (
            AxisCoverage(
                axis=AXIS_CURRENCY,
                manifests_found=0,
                manifests_parsed=0,
                deps_total=inventory.count,
                deps_assessed=assessed,
                resolution_depth=None,
            ),
        )
        return EngineResult(
            findings=findings,
            errors=(),
            coverage=coverage,
            axis=self.axis,
            currency_data=currency_data,
        )


register_engine(NullEngine)
register_engine(DeptryEngine)
register_engine(OsvEngine)
register_engine(LicenseEngine)
register_engine(CurrencyEngine)
