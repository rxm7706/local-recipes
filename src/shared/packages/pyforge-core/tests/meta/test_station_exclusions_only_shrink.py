"""Meta test -- a station left out of a kernel guard is left out path by path, and the list only shrinks
(marshal Story 117.6; spec-pyforge-core:CAP-7 as amended 2026-11-10, FR-163).

Two kernel guards leave stations out whole. The exception-root guard
(``test_exception_root_sole_ownership.py``) does not scan ``pyforge-doctor`` or ``pyforge-steward``, the subprocess
guard (``test_process_sole_ownership.py``) does not scan six stations, and neither guard scans ``pyforge-core``'s own
exception classes. A new builtin-rooted class or a new raw subprocess call in one of those trees was never seen.

This module does not widen either guard; it pins what exists, path by path:

- ``_UNREPARENTED_ROOTS``: every ``pyforge-<s>/src/pyforge/<s>/<path>::<Class>`` the exception-root guard's own
  detector (``_root_violations``) reports in its ``_OUT_OF_SCOPE_STATIONS`` and in ``pyforge-core``.
  ``pyforge-core/src/pyforge/core/errors.py::PyforgeError`` -- the kernel's root, ``class PyforgeError(Exception)``,
  which the detector matches -- is excluded by name and is never a pin.
- ``_SUBPROCESS_FILES``: every ``pyforge-<s>/src/...`` file in the subprocess guard's ``_OUT_OF_SCOPE_STATIONS`` where
  that guard's own detector (``_subprocess_violations``) reports a line.

The detectors and the exclusion sets are imported from the two guards, never copied, so this module measures exactly
what each guard would report if it scanned these trees. Measured equals pinned: a new entry fails with ``root it at
pyforge.core.errors.PyforgeError`` or ``launch it through pyforge.core.process``; a pin with no measured entry fails
with ``lower the pin`` (the house pattern of steward's ``UNSPLIT_ON_A_STATION_SRC_EDIT``, which reds on a stale
name). Paths, not counts: a count would hide a violation that moves files and would red a module split. When a
station's last pin goes, the scope test reds until that station leaves the guard's ``_OUT_OF_SCOPE_STATIONS``, so the
exclusions shrink with the pins.

Re-parenting a class or rerouting a call is never done here (operator ruling 2026-11-10): each station migrates in its
own chain (DW-marshal-117-6-1, DW-marshal-117-6-2). The pins were measured on the cutover-readiness integration branch
after every story of that PR that edits a station's ``src/``; what that PR added over the plan-time measurement at
``f614d6a9b8`` is named in Story 117.6's story spec, ``## Verification``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from conftest import PACKAGES_ROOT, parse_module, station_source_files
from test_exception_root_sole_ownership import _OUT_OF_SCOPE_STATIONS as _ROOT_GUARD_OUT_OF_SCOPE
from test_exception_root_sole_ownership import _root_violations
from test_process_sole_ownership import _OUT_OF_SCOPE_STATIONS as _SUBPROCESS_GUARD_OUT_OF_SCOPE
from test_process_sole_ownership import _subprocess_violations

pytestmark = pytest.mark.live_tree

# The kernel's own root matches the exception-root detector (`class PyforgeError(Exception)`); it is the one class
# every other root is asked to carry, so it is excluded by name and never pinned.
_PYFORGE_ERROR = "pyforge-core/src/pyforge/core/errors.py::PyforgeError"

# The trees each list measures: the exception-root guard's exclusions plus pyforge-core (which no guard scans), and
# the subprocess guard's exclusions (pyforge-core owns the process seam, pyforge.core.process).
_ROOT_STATIONS = _ROOT_GUARD_OUT_OF_SCOPE | {"pyforge-core"}
_SUBPROCESS_STATIONS = _SUBPROCESS_GUARD_OUT_OF_SCOPE

# Shrink only. Remove an entry in the change that roots the class at PyforgeError; never add one.
_UNREPARENTED_ROOTS = frozenset(
    {
        "pyforge-core/src/pyforge/core/assertion.py::HostMintError",
        "pyforge-core/src/pyforge/core/client.py::StationClientError",
        "pyforge-core/src/pyforge/core/cutover_root.py::CutoverRootError",
        "pyforge-core/src/pyforge/core/flags.py::FlagConfigError",
        "pyforge-core/src/pyforge/core/flags.py::FlagOff",
        "pyforge-core/src/pyforge/core/league_measure.py::LeagueMeasureError",
        "pyforge-core/src/pyforge/core/preserve_refs.py::PreserveRefError",
        "pyforge-doctor/src/pyforge/doctor/cli_bridge.py::CliBridgeError",
        "pyforge-doctor/src/pyforge/doctor/sources/atlas.py::_FetchFailed",
        "pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py::_Unevaluable",
        "pyforge-doctor/src/pyforge/doctor/sources/chain.py::SurfaceUnevaluable",
        "pyforge-doctor/src/pyforge/doctor/sources/frozen_path.py::_Unevaluable",
        "pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py::_Unavailable",
        "pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py::_SiblingHTTPError",
        "pyforge-doctor/src/pyforge/doctor/sources/writer_lock.py::_Unevaluable",
        "pyforge-steward/src/pyforge/steward/budget.py::BudgetError",
        "pyforge-steward/src/pyforge/steward/budget.py::CapParseError",
        "pyforge-steward/src/pyforge/steward/catalog.py::CatalogConfigError",
        "pyforge-steward/src/pyforge/steward/corridor.py::CorridorConfigError",
        "pyforge-steward/src/pyforge/steward/corridor.py::CorridorLoadError",
        "pyforge-steward/src/pyforge/steward/cutover_ledger.py::CutoverLedgerError",
        "pyforge-steward/src/pyforge/steward/dashboard/cache.py::LockUnavailableError",
        "pyforge-steward/src/pyforge/steward/dashboard/export.py::ExportUnauthorizedError",
        "pyforge-steward/src/pyforge/steward/dashboard/export.py::WebhookSecretMissingError",
        "pyforge-steward/src/pyforge/steward/dashboard/middleware.py::UntrustedIngressError",
        "pyforge-steward/src/pyforge/steward/deck_integrity.py::DeckIntegrityError",
        "pyforge-steward/src/pyforge/steward/deploy.py::UnshareableStateError",
        "pyforge-steward/src/pyforge/steward/estate.py::_RefreshRefused",
        "pyforge-steward/src/pyforge/steward/fresh_clone.py::FreshCloneError",
        "pyforge-steward/src/pyforge/steward/glass.py::GlassError",
        "pyforge-steward/src/pyforge/steward/keys.py::InventoryError",
        "pyforge-steward/src/pyforge/steward/marketplace_pages.py::MarketplaceIndexError",
        "pyforge-steward/src/pyforge/steward/marketplace_pages.py::MarketplacePagesDisabled",
        "pyforge-steward/src/pyforge/steward/measures.py::MeasureConfigError",
        "pyforge-steward/src/pyforge/steward/passport.py::PassportMintError",
        "pyforge-steward/src/pyforge/steward/preflight.py::PreflightConfigError",
        "pyforge-steward/src/pyforge/steward/preflight.py::PreflightScopeError",
        "pyforge-steward/src/pyforge/steward/preflight_ci.py::_SelectAll",
        "pyforge-steward/src/pyforge/steward/preflight_ci.py::_Unevaluable",
        "pyforge-steward/src/pyforge/steward/quarantine.py::QuarantineAdmitError",
        "pyforge-steward/src/pyforge/steward/suite.py::SuiteError",
        "pyforge-steward/src/pyforge/steward/sync.py::SyncConfigError",
        "pyforge-steward/src/pyforge/steward/sync.py::SyncError",
        "pyforge-steward/src/pyforge/steward/upgrade.py::UpgradeError",
        "pyforge-steward/src/pyforge/steward/workspace.py::WorkspaceError",
    }
)

# Shrink only. Remove an entry in the change that routes the file's last call through pyforge.core.process; never
# add one. frames.py and revoke.py reference `subprocess.run` without calling it; the detector matches the reference.
_SUBPROCESS_FILES = frozenset(
    {
        "pyforge-doctor/src/pyforge/doctor/cli_bridge.py",
        "pyforge-herald/src/pyforge/herald/deck_pipeline.py",
        "pyforge-herald/src/pyforge/herald/deck_publish.py",
        "pyforge-herald/src/pyforge/herald/local_ship.py",
        "pyforge-herald/src/pyforge/herald/pptx_native.py",
        "pyforge-herald/src/pyforge/herald/stamps.py",
        "pyforge-herald/src/pyforge/herald/sync_all.py",
        "pyforge-herald/src/pyforge/herald/transport/agent_sdk_transport.py",
        "pyforge-herald/src/pyforge/herald/twins.py",
        "pyforge-mason/src/pyforge/mason/cfe.py",
        "pyforge-mason/src/pyforge/mason/engines/__init__.py",
        "pyforge-mason/src/pyforge/mason/engines/condalock.py",
        "pyforge-mason/src/pyforge/mason/engines/gh.py",
        "pyforge-mason/src/pyforge/mason/engines/pep517.py",
        "pyforge-mason/src/pyforge/mason/engines/pixi.py",
        "pyforge-mason/src/pyforge/mason/engines/twine.py",
        "pyforge-scribe/src/pyforge/scribe/catalog.py",
        "pyforge-scribe/src/pyforge/scribe/compile.py",
        "pyforge-steward/src/pyforge/steward/bootstrap.py",
        "pyforge-steward/src/pyforge/steward/ci.py",
        "pyforge-steward/src/pyforge/steward/cutover_ledger.py",
        "pyforge-steward/src/pyforge/steward/deploy.py",
        "pyforge-steward/src/pyforge/steward/deploy_nic.py",
        "pyforge-steward/src/pyforge/steward/deploy_nic_packs.py",
        "pyforge-steward/src/pyforge/steward/estate.py",
        "pyforge-steward/src/pyforge/steward/estate_realize.py",
        "pyforge-steward/src/pyforge/steward/frames.py",
        "pyforge-steward/src/pyforge/steward/keys.py",
        "pyforge-steward/src/pyforge/steward/pages_duty.py",
        "pyforge-steward/src/pyforge/steward/preflight.py",
        "pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py",
        "pyforge-steward/src/pyforge/steward/preflight_verify.py",
        "pyforge-steward/src/pyforge/steward/provision.py",
        "pyforge-steward/src/pyforge/steward/revoke.py",
        "pyforge-steward/src/pyforge/steward/session.py",
        "pyforge-steward/src/pyforge/steward/suite_advance.py",
        "pyforge-steward/src/pyforge/steward/upgrade.py",
        "pyforge-steward/src/pyforge/steward/workspace.py",
        "pyforge-warden/src/pyforge/warden/engines.py",
    }
)


# --- the measurement: the guards' own detectors over the trees they leave out --------------------------------------


def _source_files(packages_root: Path, station: str) -> list[Path]:
    """The files a guard reads for one station: ``<station>/src/pyforge/**/*.py``, as conftest's
    ``station_source_files`` enumerates them, with the root a parameter so a synthetic tree runs the same code."""
    src_pyforge = packages_root / station / "src" / "pyforge"
    return sorted(src_pyforge.rglob("*.py")) if src_pyforge.is_dir() else []


def _measure_roots(packages_root: Path, stations: Iterable[str]) -> frozenset[str]:
    found: set[str] = set()
    for station in stations:
        for path in _source_files(packages_root, station):
            rel = path.relative_to(packages_root).as_posix()
            found.update(f"{rel}::{name}" for name, _line in _root_violations(parse_module(path)))
    return frozenset(found - {_PYFORGE_ERROR})


def _measure_subprocess_files(packages_root: Path, stations: Iterable[str]) -> frozenset[str]:
    return frozenset(
        path.relative_to(packages_root).as_posix()
        for station in stations
        for path in _source_files(packages_root, station)
        if _subprocess_violations(parse_module(path))
    )


def _check_only_shrinks(measured: frozenset[str], pinned: frozenset[str], *, pin_name: str, fix: str) -> None:
    problems: list[str] = []
    new = sorted(measured - pinned)
    if new:
        problems.append(f"new entries outside the guard, not in {pin_name}: {new} -- {fix}; the pins never grow")
    stale = sorted(pinned - measured)
    if stale:
        problems.append(f"pinned in {pin_name} but no longer measured: {stale} -- lower the pin (remove them)")
    if problems:
        raise AssertionError("\n".join(problems))


def _check_roots(measured: frozenset[str], pinned: frozenset[str]) -> None:
    _check_only_shrinks(
        measured,
        pinned,
        pin_name="_UNREPARENTED_ROOTS",
        fix="root it at pyforge.core.errors.PyforgeError (`class FooError(PyforgeError, Exception)`)",
    )


def _check_subprocess_files(measured: frozenset[str], pinned: frozenset[str]) -> None:
    _check_only_shrinks(
        measured,
        pinned,
        pin_name="_SUBPROCESS_FILES",
        fix="launch it through pyforge.core.process (`PosixProcess().run(...)`)",
    )


# --- AC1: the pins equal the guards' own measurement on the live tree ----------------------------------------------


def test_unreparented_roots_equal_the_pins() -> None:
    _check_roots(_measure_roots(PACKAGES_ROOT, _ROOT_STATIONS), _UNREPARENTED_ROOTS)


def test_subprocess_files_equal_the_pins() -> None:
    _check_subprocess_files(_measure_subprocess_files(PACKAGES_ROOT, _SUBPROCESS_STATIONS), _SUBPROCESS_FILES)


def test_measurement_reads_the_files_the_guards_read() -> None:
    """The enumeration above is conftest's, root aside: for every station a guard leaves out, the same files."""
    for station in sorted(_ROOT_GUARD_OUT_OF_SCOPE | _SUBPROCESS_GUARD_OUT_OF_SCOPE):
        others = frozenset(p.name for p in PACKAGES_ROOT.iterdir() if p.is_dir()) - {station}
        assert _source_files(PACKAGES_ROOT, station) == station_source_files(exclude=others), station


# --- AC2: the ratchet fires on synthetic trees ---------------------------------------------------------------------


def _module_rel(station: str, name: str) -> str:
    return f"{station}/src/pyforge/{station.removeprefix('pyforge-')}/{name}"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("station", sorted(_ROOT_STATIONS))
def test_ratchet_fires_on_a_new_builtin_rooted_class_in_an_excluded_package(tmp_path: Path, station: str) -> None:
    known = _module_rel(station, "known.py")
    _write(tmp_path, known, "class KnownError(Exception):\n    pass\n")
    pins = frozenset({f"{known}::KnownError"})
    _check_roots(_measure_roots(tmp_path, {station}), pins)  # holds before the edit

    fresh = _module_rel(station, "fresh.py")
    _write(tmp_path, fresh, "class FreshError(RuntimeError):\n    pass\n")
    with pytest.raises(AssertionError, match=r"root it at pyforge\.core\.errors\.PyforgeError") as excinfo:
        _check_roots(_measure_roots(tmp_path, {station}), pins)
    assert f"{fresh}::FreshError" in str(excinfo.value)
    assert "lower the pin" not in str(excinfo.value)


@pytest.mark.parametrize("station", sorted(_SUBPROCESS_STATIONS))
def test_ratchet_fires_on_a_new_subprocess_call_site_in_an_excluded_station(tmp_path: Path, station: str) -> None:
    known = _module_rel(station, "known.py")
    _write(tmp_path, known, "import subprocess\nsubprocess.run(['true'])\n")
    pins = frozenset({known})
    _check_subprocess_files(_measure_subprocess_files(tmp_path, {station}), pins)  # holds before the edit

    fresh = _module_rel(station, "fresh.py")
    _write(tmp_path, fresh, "from subprocess import check_output\ncheck_output(['true'])\n")
    with pytest.raises(AssertionError, match=r"launch it through pyforge\.core\.process") as excinfo:
        _check_subprocess_files(_measure_subprocess_files(tmp_path, {station}), pins)
    assert fresh in str(excinfo.value)
    assert "lower the pin" not in str(excinfo.value)


def test_ratchet_fires_on_a_stale_root_pin(tmp_path: Path) -> None:
    budget = _module_rel("pyforge-steward", "budget.py")
    _write(tmp_path, budget, "class BudgetError(Exception):\n    pass\n")
    pins = frozenset({f"{budget}::BudgetError"})
    _check_roots(_measure_roots(tmp_path, {"pyforge-steward"}), pins)  # holds before the edit

    _write(tmp_path, budget, "class BudgetError(PyforgeError, Exception):\n    pass\n")
    with pytest.raises(AssertionError, match="lower the pin") as excinfo:
        _check_roots(_measure_roots(tmp_path, {"pyforge-steward"}), pins)
    assert f"{budget}::BudgetError" in str(excinfo.value)
    assert "root it at" not in str(excinfo.value)


def test_ratchet_fires_on_a_stale_file_pin(tmp_path: Path) -> None:
    engines = _module_rel("pyforge-warden", "engines.py")
    _write(tmp_path, engines, "import subprocess\nsubprocess.Popen(['true'])\n")
    pins = frozenset({engines})
    _check_subprocess_files(_measure_subprocess_files(tmp_path, {"pyforge-warden"}), pins)  # holds before the edit

    _write(tmp_path, engines, "from pyforge.core.process import PosixProcess\nPosixProcess().run(['true'])\n")
    with pytest.raises(AssertionError, match="lower the pin") as excinfo:
        _check_subprocess_files(_measure_subprocess_files(tmp_path, {"pyforge-warden"}), pins)
    assert engines in str(excinfo.value)
    assert "launch it through" not in str(excinfo.value)


def test_ratchet_fires_when_a_call_site_moves_files(tmp_path: Path) -> None:
    """Paths, not counts: one call moved from one file to another keeps the count and still fails, both ways."""
    old = _module_rel("pyforge-steward", "cutover.py")
    new = _module_rel("pyforge-steward", "cutover_ledger.py")
    _write(tmp_path, old, "import subprocess\nsubprocess.run(['git'])\n")
    pins = frozenset({old})
    _check_subprocess_files(_measure_subprocess_files(tmp_path, {"pyforge-steward"}), pins)  # holds before the move

    _write(tmp_path, old, "")
    _write(tmp_path, new, "import subprocess\nsubprocess.run(['git'])\n")
    measured = _measure_subprocess_files(tmp_path, {"pyforge-steward"})
    assert len(measured) == len(pins)
    with pytest.raises(AssertionError, match="launch it through pyforge.core.process") as excinfo:
        _check_subprocess_files(measured, pins)
    assert "lower the pin" in str(excinfo.value)


def test_ratchet_holds_when_measured_equals_pinned(tmp_path: Path) -> None:
    root_rel = _module_rel("pyforge-doctor", "cli_bridge.py")
    _write(tmp_path, root_rel, "import subprocess\nclass CliBridgeError(Exception):\n    pass\nsubprocess.run(['x'])\n")
    _check_roots(_measure_roots(tmp_path, {"pyforge-doctor"}), frozenset({f"{root_rel}::CliBridgeError"}))
    _check_subprocess_files(_measure_subprocess_files(tmp_path, {"pyforge-doctor"}), frozenset({root_rel}))


# --- AC3: the pinned stations are the guards' own exclusions; PyforgeError is excluded by name ---------------------


def _station_of(pin: str) -> str:
    return pin.split("/", 1)[0]


def test_scope_pinned_stations_are_each_guards_own_exclusions() -> None:
    """A pin in a station its guard scans can never be measured; an excluded station with no pin left is one the
    guard can scan now, so it leaves that guard's ``_OUT_OF_SCOPE_STATIONS`` (the exclusions shrink with the pins)."""
    for pins, stations, guard in (
        (_UNREPARENTED_ROOTS, _ROOT_STATIONS, "test_exception_root_sole_ownership.py (plus pyforge-core)"),
        (_SUBPROCESS_FILES, _SUBPROCESS_STATIONS, "test_process_sole_ownership.py"),
    ):
        pinned_stations = frozenset(_station_of(pin) for pin in pins)
        assert pinned_stations <= stations, (
            f"pins in stations {sorted(pinned_stations - stations)} that {guard} scans -- lower the pin"
        )
        assert pinned_stations == stations, (
            f"stations {sorted(stations - pinned_stations)} have no pin left -- {guard} can scan them: drop them "
            f"from its _OUT_OF_SCOPE_STATIONS"
        )
    for pin in _UNREPARENTED_ROOTS | _SUBPROCESS_FILES:
        path, _, _cls = pin.partition("::")
        assert path.startswith(f"{_station_of(pin)}/src/pyforge/") and path.endswith(".py"), pin
    assert all("::" in pin and pin.rpartition("::")[2] for pin in _UNREPARENTED_ROOTS)
    assert not any("::" in pin for pin in _SUBPROCESS_FILES)


def test_scope_pyforge_error_itself_is_never_a_pin(tmp_path: Path) -> None:
    errors_py = PACKAGES_ROOT / "pyforge-core/src/pyforge/core/errors.py"
    # Non-vacuous: the guard's own detector matches the kernel's root, `class PyforgeError(Exception)`.
    assert "PyforgeError" in {name for name, _line in _root_violations(parse_module(errors_py))}
    assert _PYFORGE_ERROR not in _measure_roots(PACKAGES_ROOT, {"pyforge-core"})
    assert _PYFORGE_ERROR not in _UNREPARENTED_ROOTS

    # By name, exactly: the kernel's errors.py::PyforgeError is excluded, a same-named class elsewhere is not.
    _write(tmp_path, "pyforge-core/src/pyforge/core/errors.py", "class PyforgeError(Exception):\n    pass\n")
    impostor = _module_rel("pyforge-steward", "errors.py")
    _write(tmp_path, impostor, "class PyforgeError(Exception):\n    pass\n")
    assert _measure_roots(tmp_path, {"pyforge-core", "pyforge-steward"}) == {f"{impostor}::PyforgeError"}
