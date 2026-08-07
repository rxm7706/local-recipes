"""Unit tests for ``pyforge.doctor.cli_bridge`` (Story 2.1, AD-5) -- the
sole sanctioned subprocess site. Covers: success, script missing, non-zero
exit, timeout, unparseable JSON, argv-as-a-list (no shell interpretation),
and the ``NO_COLOR=1`` environment contract."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError, run_cli_json


def _write_script(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "script.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    return script


def test_success_returns_parsed_json(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import json, sys
        print(json.dumps({"ok": True, "argv": sys.argv[1:]}))
        """,
    )
    result = run_cli_json(script, ["--json", "--limit", "5"], timeout=10)
    assert result == {"ok": True, "argv": ["--json", "--limit", "5"]}


def test_script_missing_raises_cli_bridge_error(tmp_path: Path):
    missing = tmp_path / "does-not-exist.py"
    with pytest.raises(CliBridgeError, match="not found"):
        run_cli_json(missing, ["--json"], timeout=10)


def test_non_zero_exit_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import sys
        print("boom", file=sys.stderr)
        sys.exit(3)
        """,
    )
    with pytest.raises(CliBridgeError, match="exited 3"):
        run_cli_json(script, ["--json"], timeout=10)


def test_timeout_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import time
        time.sleep(30)
        """,
    )
    with pytest.raises(CliBridgeError, match="timed out"):
        run_cli_json(script, ["--json"], timeout=0.2)


def test_unparseable_json_raises_cli_bridge_error(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        print("not json at all {{{")
        """,
    )
    with pytest.raises(CliBridgeError, match="unparseable JSON"):
        run_cli_json(script, ["--json"], timeout=10)


def test_argv_is_never_shell_interpreted(tmp_path: Path):
    # A shell-metacharacter-laden argument must arrive at the script
    # LITERALLY -- proof that argv is passed as a list, never through a
    # shell (AD-5's own wording).
    script = _write_script(
        tmp_path,
        """
        import json, sys
        print(json.dumps({"received": sys.argv[1:]}))
        """,
    )
    dangerous = "$(echo pwned); rm -rf /tmp/nonexistent && echo done"
    result = run_cli_json(script, ["--json", dangerous], timeout=10)
    assert result == {"received": ["--json", dangerous]}


def test_no_color_is_set_in_subprocess_environment(tmp_path: Path):
    script = _write_script(
        tmp_path,
        """
        import json, os
        print(json.dumps({"no_color": os.environ.get("NO_COLOR")}))
        """,
    )
    result = run_cli_json(script, [], timeout=10)
    assert result == {"no_color": "1"}
