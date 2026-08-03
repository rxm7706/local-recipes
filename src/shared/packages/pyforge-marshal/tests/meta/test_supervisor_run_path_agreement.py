"""Meta test (Story 3.4) -- ``supervisor/__main__.py`` and ``cli/spin.py``
must compute the SAME run-directory path, journal filename, launch kind and
entry-timestamp format.

The supervisor deliberately DUPLICATES those four helpers/constants rather
than importing them: this story's own AD-9 import-linter contract forbids
``pyforge.marshal.supervisor`` from importing ``pyforge.marshal.cli`` at
all, and neither story's Code Map asks for a shared third module. That is a
sound structural decision -- but it left the two copies pinned by nothing.

Follow-up review finding: the supervisor's own unit tests assert path
AGREEMENT nowhere (``read_text_calls`` is checked for length only, and
every ``appended_lines`` tuple is unpacked as ``_, line, _``), so changing
the run-directory layout in ``cli/spin.py`` -- e.g. ``runs/<run_id>`` ->
``runs/<slug>/<run_id>`` -- kept the entire suite green while every real
supervisor read a journal that does not exist, found no ``run-launch``
entry, and exited inert on every single run: total, silent loss of
supervision. This file is the pin. A test module is not part of the
``pyforge.marshal`` package, so importing both sides here does not touch
the AD-9 contract (verified: ``lint-imports`` runs over the installed
package's own modules, and ``tests/`` is not among them).

If a future story legitimately changes the layout, this test fails FIRST
and names both sides -- which is the whole point: the duplication is
allowed, the divergence is not.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.supervisor import __main__ as supervisor_module

_HOME = Path("/home/acme-loop")
_SLUG = "acme"
_RUN_ID = "acme-20260803T054512123Z-a1b2c3d4"


def test_tier3_path_agrees():
    assert supervisor_module._tier3_path(_HOME, _SLUG) == spin_module._tier3_path(
        _HOME, _SLUG
    )


def test_run_dir_agrees():
    assert supervisor_module._run_dir(_HOME, _SLUG, _RUN_ID) == spin_module._run_dir(
        _HOME, _SLUG, _RUN_ID
    )


def test_journal_filename_agrees():
    assert supervisor_module._JOURNAL_FILENAME == spin_module._JOURNAL_FILENAME


def test_launch_kind_agrees():
    """The supervisor's inert-check looks for exactly the ``kind``
    ``cli/spin.py`` writes -- a rename on either side alone makes every
    supervisor inert on every run."""
    assert supervisor_module._LAUNCH_KIND == spin_module._LAUNCH_KIND


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2026, 8, 3, 5, 45, 12, 123456, tzinfo=timezone.utc),
        # Sub-millisecond, to pin the same truncation (not rounding) on both
        # sides, and midnight, to pin the same zero-padding.
        datetime(2026, 1, 1, 0, 0, 0, 999, tzinfo=timezone.utc),
    ],
)
def test_entry_timestamp_format_agrees(moment):
    assert supervisor_module._format_entry_ts(moment) == spin_module._format_entry_ts(
        moment
    )


def test_the_supervisor_still_does_not_import_the_cli():
    """The agreement above must never be achieved by the supervisor simply
    importing ``cli/spin.py`` -- that is the AD-9 violation this whole
    duplication exists to avoid. ``lint-imports`` proves it structurally
    (``test_ad9_supervisor_no_control_channel.py``); this asserts the
    cheap, direct version so a reader of THIS file cannot conclude the
    duplication was quietly collapsed.

    Scanned as an AST over IMPORT statements only -- a plain substring
    search over the source matches this module's own prose, which discusses
    ``pyforge.marshal.cli`` at length precisely to explain why it must not
    import it."""
    tree = ast.parse(
        Path(supervisor_module.__file__).read_text(encoding="utf-8"),
        filename=supervisor_module.__file__,
    )
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offenders += [
                f"line {node.lineno}: import {alias.name}"
                for alias in node.names
                if alias.name.startswith("pyforge.marshal.cli")
            ]
        elif isinstance(node, ast.ImportFrom):
            # `level` counts the leading dots of a relative import; from
            # `pyforge/marshal/supervisor/__main__.py`, `from ..cli import x`
            # is level 2 with module "cli".
            absolute = node.module or ""
            relative_to_cli = node.level == 2 and absolute.split(".")[0] == "cli"
            if absolute.startswith("pyforge.marshal.cli") or relative_to_cli:
                offenders.append(f"line {node.lineno}: from {'.' * node.level}{absolute}")
    assert not offenders, f"the supervisor must never import the cli (AD-9): {offenders}"


def test_the_module_really_runs_under_dash_m(tmp_path):
    """Review finding: every other supervisor test calls ``run_supervisor``
    or ``main()`` IN-PROCESS, and the two real-child spawn tests in
    ``test_process_posix.py`` use ``-c`` -- so nothing ever executed the
    one invocation ``cli/spin.py`` actually builds,
    ``python -m pyforge.marshal.supervisor``. If ``supervisor/__main__.py``
    fell out of the wheel, or ``supervisor/__init__.py`` gained a failing
    import-time side effect, every sidecar would die at import while
    ``spawn_detached`` still returned a pid, ``spin`` still printed
    ``supervisor_pid`` and exited 0, and every run went unsupervised with
    the whole suite green.

    Run with no arguments so it exits on the arity gate: this asserts the
    module is IMPORTABLE and EXECUTABLE as ``__main__``, which is the part
    no in-process test can prove. ``PYTHONSAFEPATH``/``cwd`` mirror
    ``spawn_detached``'s own env, so the child resolves ``pyforge`` from the
    installed environment exactly as a real sidecar does -- with ``cwd`` a
    directory that is emphatically not the source tree."""
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.marshal.supervisor"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONSAFEPATH": "1", "PYTHONUNBUFFERED": "1"},
    )
    assert result.returncode == 1, (
        f"expected the arity gate's own exit 1, got {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "usage: python -m pyforge.marshal.supervisor" in result.stderr
