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

Registry semantics: engines register via ``register_engine(factory)`` at
module-import time; ``registered_engines()`` instantiates them in
registration order — deterministic because module execution is. The registry
is ``[NullEngine, DeptryEngine, OsvEngine]``: ``NullEngine`` is a harmless
no-op retained so its 1.2 unit contract is unchanged, ``DeptryEngine`` is the
hygiene-axis engine (1.3), ``OsvEngine`` is the vulnerability-axis engine
(1.5).

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
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .hygiene import (
    _synthesize_deptry_frontdoor,
    parse_deptry_output,
    unsafe_identity_finding as hygiene_unsafe_identity_finding,
)
from .interfaces import Engine, EngineResult
from .inventory import Component, ResolvedInventory
from .models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ErrorKind,
    ErrorRecord,
    Finding,
    VulnData,
)
from .vuln import (
    DB_MAX_AGE_DAYS,
    _db_has_valid_advisory,
    _synthesize_requirements,
    db_snapshot_at,
    db_zip_path,
    is_db_stale,
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
            # utf-8-sig tolerates a leading BOM some tools prepend, then
            # decodes as utf-8; genuinely non-utf-8 bytes still raise below.
            text = Path(output_path).read_bytes().decode("utf-8-sig")
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


class NullEngine:
    """The no-op engine: assesses nothing, contributes nothing.

    Retained from 1.2 so its unit contract is unchanged; it exists so the
    pipeline runs end-to-end through the real seam even before a real engine
    contributes."""

    name: str = "null"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        return EngineResult(findings=(), errors=(), coverage=())


class DeptryEngine:
    """The first real engine: dependency-hygiene via ``deptry`` (Story 1.3).

    Runs ``deptry . -o <tempfile> --no-ansi`` with ``cwd=target`` so deptry
    reads the project's OWN ``pyproject.toml`` — honoring ``[tool.deptry]``
    (``ignore``/``per_rule_ignores``/``exclude``) NATIVELY (FR9) — and writes
    its machine output to a system-temp file we read (the pure-JSON-stdout
    seam: deptry's own chatter never touches our streams). deptry's exit code
    is ignored; the DEP001–DEP005 records become ``hygiene:<code>:<module>``
    findings, and on a successful run the hygiene axis reports
    ``deps_assessed == inventory.count``.

    Story 2.2 (FR8's conda half) ALWAYS additionally synthesizes a
    ``--requirements-files <tempfile>`` front-door from the inventory (see
    ``hygiene._synthesize_deptry_frontdoor`` and the module docstring) —
    unconditionally, never conditionally detected: deptry's own native
    ``pyproject.toml`` detection takes priority when present, so this is a
    no-op for every pre-2.2 pyproject-native scan and a real signal for a
    conda-sourced one. Because the flag REPLACES (not merges with) deptry's
    own default ``requirements.txt`` source, a ``requirements.txt`` present
    at the scan root is re-appended to the flag's comma-list so its
    pip-declared deps stay visible to deptry (fixed 2026-07-16 — verified
    live: without this, such a scan reports false DEP001s for every dep the
    project's own requirements.txt declares). The synthesized input file
    uses the SAME
    ``tempfile.mkstemp``/``finally: os.unlink`` idiom as ``OsvEngine.run``'s
    own input file (NFR-S4). Any component the NFR-S6 purity guard excludes
    from that front-door surfaces as one ``indeterminate:unsafe-identity:
    <pkg>`` finding via ``hygiene.unsafe_identity_finding`` (Fix 6,
    2026-07-16) — computed up front and merged into EVERY return path below,
    mirroring ``OsvEngine.run``'s own never-silently-dropped handling of its
    parallel-shaped ``excluded_findings``."""

    name: str = "deptry"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        synthesized = _synthesize_deptry_frontdoor(inventory.components)
        excluded_findings = tuple(
            sorted(
                (
                    hygiene_unsafe_identity_finding(c)
                    for c in synthesized.excluded
                ),
                key=lambda f: f.id,
            )
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
            )
        try:
            os.close(handle)
            content = "\n".join(synthesized.lines)
            if content:
                content += "\n"
            Path(input_path).write_text(content, encoding="utf-8")
            # Passing --requirements-files REPLACES deptry's own native
            # default requirements source (`requirements.txt`) rather than
            # merging with it (verified live against deptry 0.25.1) -- so a
            # conda-sourced scan with a sibling requirements.txt would lose
            # every pip-declared dep there to false DEP001s. Re-appending
            # deptry's own default (comma syntax per `deptry --help`;
            # relative, resolved against cwd=target exactly as deptry's
            # native detection would) keeps that behavior intact (fixed
            # 2026-07-16). Still a genuine no-op for pyproject-native scans:
            # deptry ignores the flag entirely there.
            requirements_files = input_path
            if (target / "requirements.txt").is_file():
                requirements_files = f"{input_path},requirements.txt"
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
                findings=excluded_findings, errors=(error,), coverage=()
            )
        parse = parse_deptry_output(text or "")
        if not parse.output_parsed:
            # Top-level garbage (undecodable/non-array): fail loud, no
            # coverage claim (nothing was assessed) — the purity guard's own
            # findings still survive (never silently dropped).
            return EngineResult(
                findings=excluded_findings, errors=parse.errors, coverage=()
            )
        coverage = (
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=0,
                manifests_parsed=0,
                deps_total=inventory.count,
                deps_assessed=inventory.count,
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
    for component in name_level_candidates:
        if component.pypi_identity is None:
            continue  # defensive: the caller's own filter already excludes this
        advisory_ids = name_level_critical_advisory_ids(
            zip_path, component.pypi_identity.name
        )
        if advisory_ids:
            findings.append(name_level_critical_cve_finding(component, advisory_ids))
    return tuple(sorted(findings, key=lambda f: f.id))


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
    independently of the subprocess, survive every one of these paths."""

    name: str = "osv-scanner"

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
            return EngineResult(findings=(), errors=(), coverage=())

        cache_dir = resolve_cache_dir()
        zip_path = db_zip_path(cache_dir) if cache_dir is not None else None
        if cache_dir is None or zip_path is None or not _db_has_valid_advisory(zip_path):
            return EngineResult(
                findings=_withheld_findings([*candidates, *name_level_candidates]),
                errors=(),
                coverage=(),
                vuln_data=None,
            )

        snapshot_at = db_snapshot_at(zip_path)
        stale = is_db_stale(snapshot_at, DB_MAX_AGE_DAYS, now=datetime.now(UTC))
        name_level_findings = _name_level_findings(zip_path, name_level_candidates)
        stale_findings = (stale_vuln_data_finding(),) if stale else ()

        if not candidates:
            # Name-level-only scan: osv-scanner has no "any version" query
            # mode, so this never invokes the subprocess at all.
            findings = tuple(
                sorted((*name_level_findings, *stale_findings), key=lambda f: f.id)
            )
            vuln_data = VulnData(
                source=str(zip_path), snapshot_at=snapshot_at, max_age_ok=not stale
            )
            return EngineResult(
                findings=findings, errors=(), coverage=(), vuln_data=vuln_data
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
                    (*excluded_findings, *name_level_findings, *stale_findings),
                    key=lambda f: f.id,
                )
            )
            vuln_data = VulnData(
                source=str(zip_path), snapshot_at=snapshot_at, max_age_ok=not stale
            )
            return EngineResult(
                findings=findings, errors=(), coverage=(), vuln_data=vuln_data
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
            # findings survive too (FR13).
            findings = tuple(
                sorted((*excluded_findings, *name_level_findings), key=lambda f: f.id)
            )
            return EngineResult(
                findings=findings,
                errors=(mkstemp_error,),
                coverage=(),
                vuln_data=None,
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
            # survive regardless (NFR-S6/FR13 — never silently dropped).
            findings = tuple(
                sorted((*excluded_findings, *name_level_findings), key=lambda f: f.id)
            )
            return EngineResult(
                findings=findings,
                errors=(error,),
                coverage=(),
                vuln_data=None,
            )

        if exit_code in (0, 1):
            parse = parse_osv_output(text or "")
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
            findings = tuple(
                sorted(
                    (
                        *excluded_findings,
                        *parse.findings,
                        *name_level_findings,
                        *stale_findings,
                    ),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=parse.errors,
                coverage=coverage,
                vuln_data=vuln_data,
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
                sorted((*excluded_findings, *name_level_findings), key=lambda f: f.id)
            )
            return EngineResult(
                findings=findings,
                errors=(error_record,),
                coverage=(),
                vuln_data=None,
            )

        if exit_code == 128:
            # osv found no packages to scan in the synthesized input — should
            # not normally happen given >=1 candidate, but the decision
            # record routes it identically to a failed pre-flight
            # (coverage-skipped, never a confident clean). The name-level
            # findings were computed independently of this subprocess call
            # and survive (FR13).
            findings = tuple(
                sorted(
                    (*_withheld_findings(candidates), *name_level_findings),
                    key=lambda f: f.id,
                )
            )
            return EngineResult(
                findings=findings,
                errors=(),
                coverage=(),
                vuln_data=None,
            )

        error_record = ErrorRecord(
            kind=ErrorKind.ENGINE_EXECUTION_FAILED,
            owner=self.name,
            message=f"osv-scanner exited with unexpected code {exit_code!r}",
        )
        findings = tuple(
            sorted((*excluded_findings, *name_level_findings), key=lambda f: f.id)
        )
        return EngineResult(
            findings=findings,
            errors=(error_record,),
            coverage=(),
            vuln_data=None,
        )


register_engine(NullEngine)
register_engine(DeptryEngine)
register_engine(OsvEngine)
