"""Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05):
policy-suite parity before ``pixi.toml`` lands.

THE DEFECT THIS CATCHES
------------------------
A ``pixi.toml`` IDE-metadata commit (``098f0f0672``, "iml files") silently
dropped the ``cachebox <6`` / ``openfeature-provider-flagd <0.5.1`` ceilings
that ``src/platform/tests/policy`` guards. Nobody caught it because Platform
CI -- the only workflow that runs ``python -m pytest tests/policy`` -- was
disabled at the time (the 2026-08-30 -> 2026-09-04 GitHub Actions dormancy).
This source runs the SAME manifest-only subset (every test NOT marked
``django_db`` -- confirmed empirically: 74 pass, 2 deselected, 0.47s, no
database, no Redis) so the regression class is caught even when Platform CI
itself is disabled, was never triggered, or a developer never ran it by
hand.

WHY A DIFFERENT INTERPRETER, NOT AN IN-PROCESS IMPORT
-------------------------------------------------------
``tests/policy`` collects through Django + pytest-django (``--ds=config.
settings.test`` in ``src/platform/pyproject.toml``'s own ``addopts``) --
even the database-free tests need that to import. Doctor is a deliberately
lean package (NFR-4's five-second pre-flight); it does not carry Django and
must not gain it just for this one source. So this module shells out
(``cli_bridge.run_pytest``, AD-5's sole subprocess site) to the
``platform-ci-test`` pixi env's OWN interpreter, resolved by a fixed,
well-known path relative to ``target`` -- the same env
``.github/actions/platform-test-setup`` builds for the real Platform CI
job, and what a developer gets from ``pixi install -e platform-ci-test`` or
a prior ``platform-ci-local`` run.

WHEN THAT ENV ISN'T INSTALLED
-------------------------------
``detectors``/``detectors-ci`` runs in a leaner env that does not carry
``platform-ci-test`` (a heavy, single-purpose CI environment -- installing
it there would defeat the whole "fast repo-scope sweep" premise). Its
absence is therefore a NORMAL, EXPECTED outcome here, not a broken
detector -- WARN, never FAIL, mirroring ``sources/__init__.py``'s own
"Doctor is a dedicated lean package, not installed in every env that runs
this script" precedent (unlike ``sources/warden.py``'s FAIL-on-absent: that
source's `pyforge-warden` dependency is a fleet-wide first-class extra;
`platform-ci-test` is not). This source is a REAL, ACTIONABLE gate only on
a machine (developer or a future CI job) that has provisioned that env --
recorded honestly here rather than silently claimed.

Never raises: absent platform surface -> no findings (this repo's `src/
platform` may not exist in every checkout this package runs against);
absent interpreter -> one WARN; a `CliBridgeError` (timeout, launch
failure, an exit code outside {0, 1}) -> one WARN naming it; an actual
policy-suite failure -> one FAIL carrying the tail of pytest's own output.
"""

from __future__ import annotations

from pathlib import Path

from .. import cli_bridge
from ..cli_bridge import CliBridgeError
from ..models import DoctorStatus, Finding, Source

_PLATFORM_REL = Path("src") / "platform"
_INTERPRETER_REL = Path(".pixi") / "envs" / "platform-ci-test" / "bin" / "python"
_INSTALL_HINT = (
    "the platform-ci-test pixi env is not installed here -- run "
    "`pixi install -e platform-ci-test` (or a prior `platform-ci-local` "
    "run) to enable this check"
)
_OUTPUT_TAIL_LINES = 20


def gather(target: Path) -> tuple[Finding, ...]:
    # Resolved to absolute up front: run_pytest passes BOTH a `cwd` (the
    # platform root) and an executable path to subprocess.run, and a
    # relative executable path resolves against the NEW cwd, not the
    # caller's -- silently wrong (caught live: `target=Path(".")`'s relative
    # interpreter path raised a bogus FileNotFoundError once cwd changed).
    target = target.resolve()
    platform_root = target / _PLATFORM_REL
    if not platform_root.is_dir():
        return ()  # no src/platform in this checkout -- nothing to judge

    interpreter = target / _INTERPRETER_REL
    if not interpreter.is_file():
        return (
            Finding(
                source=Source.PLATFORM_POLICY_SUITE,
                check="platform-ci-test-env",
                status=DoctorStatus.WARN,
                message=_INSTALL_HINT,
                evidence={"interpreter": str(interpreter)},
            ),
        )

    try:
        rc, output = cli_bridge.run_pytest(
            interpreter,
            platform_root,
            ["tests/policy", "-m", "not django_db", "-q", "-p", "no:cacheprovider"],
            timeout=120.0,
        )
    except CliBridgeError as exc:
        return (
            Finding(
                source=Source.PLATFORM_POLICY_SUITE,
                check="tests-policy",
                status=DoctorStatus.WARN,
                message=f"could not run src/platform's tests/policy: {exc}",
                evidence={},
            ),
        )

    if rc == 0:
        return ()

    tail = "\n".join(output.strip().splitlines()[-_OUTPUT_TAIL_LINES:])
    return (
        Finding(
            source=Source.PLATFORM_POLICY_SUITE,
            check="tests-policy",
            status=DoctorStatus.FAIL,
            message=f"src/platform's tests/policy failed:\n{tail}",
            evidence={"output_tail": tail},
        ),
    )
