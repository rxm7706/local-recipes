"""Meta test -- Doctor's exit-code domain is a real, computed subset of
warden's (Story 14.3, SPEC-pyforge-core CAP-3).

Before this story, doctor's own ``verdict.py`` docstring merely CLAIMED
Doctor's frozen ``{0, 2, 130}`` domain is "a subset of ``pyforge.warden``'s
frozen ``{0, 1, 2, 130}``" -- prose, not a computation. This test proves it:
``pyforge.doctor.verdict.LATTICE.narrows(pyforge.warden.verdict.LATTICE)``
must be ``True``.

This check CANNOT live in doctor's production code: ``test_no_warden_import.py``
(AD-3) forbids any doctor module except ``sources/warden.py`` from importing
``pyforge.warden`` at all, and ``sources/warden.py``'s own narrower guard
(``test_sources_warden_no_subprocess.py``) further restricts even THAT file
to ``pyforge.warden.engines`` only -- never ``pyforge.warden.verdict``. So
the narrows proof lives here instead, in a NEW test file that neither guard
scans (both scan the INSTALLED ``pyforge.doctor`` package, not the tests
directory) -- safe because the root ``pixi.toml``'s
``[feature.pyforge-doctor.dependencies]`` already resolves ``pyforge-warden``
in-repo at feature level (AD-1, the existing ``gate`` extra wiring) for
exactly this kind of test use, without doctor ever declaring warden as a
``pyproject.toml`` run-dependency.
"""

from __future__ import annotations

from pyforge.warden.verdict import LATTICE as WARDEN_LATTICE

from pyforge.doctor.verdict import LATTICE as DOCTOR_LATTICE


def test_doctor_lattice_narrows_warden_lattice():
    assert DOCTOR_LATTICE.exit_codes == frozenset({0, 2})
    assert WARDEN_LATTICE.exit_codes == frozenset({0, 1, 2})
    assert DOCTOR_LATTICE.narrows(WARDEN_LATTICE) is True


def test_doctor_this_module_is_not_scanned_by_the_no_warden_import_guard():
    """Sanity check on the design rationale itself: the two guards this
    module's docstring cites both scan the INSTALLED ``pyforge.doctor``
    package directory, never the ``tests/`` tree this file lives in."""
    import pyforge.doctor

    package_file = pyforge.doctor.__file__
    assert package_file is not None
    assert __file__ not in {package_file}
    assert "tests" in __file__.split("/")
