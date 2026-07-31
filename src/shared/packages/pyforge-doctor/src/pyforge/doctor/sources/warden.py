"""The warden-doctor gather filter (Story 1.2, FR-1).

Wraps ``pyforge.warden.engines.run_doctor_checks`` -- warden's own proven
``--doctor`` engine/OSV-DB/feed self-check -- normalizing each ``DoctorCheck``
into a ``Finding(source=Source.WARDEN_DOCTOR, ...)`` 1:1. This is the ONE
sanctioned import site for ``pyforge.warden`` in the whole ``pyforge.doctor``
package (architecture spine AD-1); the meta-tests
``test_no_warden_import.py`` and ``test_sources_warden_no_subprocess.py``
enforce that no other module reaches into warden and that this module never
shells out on its own.

The import is LAZY -- inside :func:`gather`'s body, never at module import
time -- mirroring ``pyforge.atlas.pipelines.universal_sbom.gate``'s
``_load_warden`` idiom (the ``[gate]`` extra's schema-by-import doctrine).
Unlike that gate, which raises ``GateDependencyMissing`` on a missing
extra, Doctor DEGRADES: no ``Exception`` warden raises can crash
``gather()``, since Doctor's whole purpose is to survive and report on a
broken/incomplete environment, not to require one. (``BaseException`` --
``KeyboardInterrupt``, ``SystemExit`` -- intentionally propagates:
swallowing an operator's Ctrl-C would be worse than crashing, and warden's
self-check runs real ``--version`` subprocesses long enough for one to
land mid-``gather()``.) Three failure shapes map to three
distinct FAIL ``Finding`` messages, never conflated (review findings,
2026-07-30 -- telling an operator to install an extra that is already
installed would misdirect them):

- warden genuinely ABSENT (``ModuleNotFoundError`` naming ``pyforge``,
  ``pyforge.warden``, or ``pyforge.warden.engines`` itself): the
  missing-extra install hint;
- warden installed but UNIMPORTABLE (a transitive dependency's
  ``ModuleNotFoundError``, a renamed symbol's plain ``ImportError``, or
  any other exception raised while executing warden's module body): the
  real import error;
- ``run_doctor_checks`` RAISING, or its result failing to normalize into
  ``Finding``s (a future warden shape drift): the real error.
"""

from __future__ import annotations

from pathlib import Path

from ..models import DoctorStatus, Finding, Source

_INSTALL_HINT = (
    "pyforge-warden not installed -- install the `gate` extra "
    "(`pip install pyforge-doctor[gate]`) or add pyforge-warden to the "
    "environment"
)

# A ModuleNotFoundError naming one of THESE modules means warden itself is
# absent (the install hint applies); naming anything else means warden is
# installed but one of its own imports is broken (the hint would misdirect).
_WARDEN_MODULES = frozenset(
    {"pyforge", "pyforge.warden", "pyforge.warden.engines"}
)


def _one_fail_finding(message: str) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.WARDEN_DOCTOR,
            check="pyforge-warden",
            status=DoctorStatus.FAIL,
            message=message,
            evidence={},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Run warden's ``--doctor`` self-check against ``target`` and normalize
    every ``DoctorCheck`` into a ``Finding`` -- on the success path never
    dropped, never re-aggregated into one summary ``Finding``. On any
    failure -- warden absent, warden installed-but-unimportable,
    ``run_doctor_checks`` raising, or its result failing to normalize --
    the whole result degrades to exactly one FAIL ``Finding`` whose message
    names the actual failure (the three shapes in the module docstring).
    No ``Exception`` escapes ``gather()``; ``BaseException`` intentionally
    propagates (see the module docstring)."""
    try:
        from pyforge.warden.engines import run_doctor_checks
    except ModuleNotFoundError as exc:
        if exc.name in _WARDEN_MODULES:
            return _one_fail_finding(_INSTALL_HINT)
        return _one_fail_finding(
            f"pyforge-warden is installed but failed to import: {exc!r}"
        )
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash the verb
        return _one_fail_finding(
            f"pyforge-warden is installed but failed to import: {exc!r}"
        )
    try:
        return tuple(
            Finding(
                source=Source.WARDEN_DOCTOR,
                check=check.name,
                # Strict identity, not truthiness: a shape-drifted truthy
                # non-bool (e.g. the string "false") must fail safe as
                # FAIL, never false-green as OK (review finding,
                # 2026-07-30).
                status=DoctorStatus.OK
                if check.ok is True
                else DoctorStatus.FAIL,
                message=check.message,
                evidence={},
            )
            for check in run_doctor_checks(target)
        )
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash the verb
        return _one_fail_finding(
            f"warden's self-check raised an unexpected error: {exc!r}"
        )
