"""Unit tests for ``scripts/docs_station_cli.py`` (Story 30.3,
spec-pyforge-doctor CAP-84): docs/reference/station-cheat-sheet.md
generated from each station's own pyproject.toml [project.scripts], live
--help text (via an injectable seam -- never a real subprocess/pixi call
here), and whether pixi.toml's feature.pyforge-guild composes it.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common  # noqa: E402
import docs_station_cli as m  # noqa: E402

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}


def _write_station(root: Path, name: str, *, scripts: dict[str, str]) -> None:
    package_dir = root / "src" / "shared" / "packages" / f"pyforge-{name}"
    package_dir.mkdir(parents=True)
    script_lines = "\n".join(f'{key} = "{value}"' for key, value in scripts.items())
    (package_dir / "pyproject.toml").write_text(
        f"[project]\nname = \"pyforge-{name}\"\n\n[project.scripts]\n{script_lines}\n",
        encoding="utf-8",
    )


def _write_pixi_toml(root: Path, *, guild_hosted: list[str]) -> None:
    deps = "\n".join(f'pyforge-{name} = {{ path = "src/shared/packages/pyforge-{name}" }}' for name in guild_hosted)
    (root / "pixi.toml").write_text(f"[feature.pyforge-guild.dependencies]\n{deps}\n", encoding="utf-8")


def test_render_marks_guild_hosted_vs_own_environment(tmp_path: Path):
    _write_station(tmp_path, "doctor", scripts={"doctor": "pyforge.doctor.__main__:main"})
    _write_station(tmp_path, "atlas", scripts={"pyforge-atlas": "pyforge.atlas.__main__:main"})
    _write_pixi_toml(tmp_path, guild_hosted=["doctor"])

    content = m.render(tmp_path, _STAMP, help_capture=lambda script: None)

    assert "## Doctor" in content
    assert "Environment: `pyforge-guild`" in content
    assert "## Atlas" in content
    assert "Environment: `pyforge-atlas`" in content


def test_render_excludes_core_and_testing_kit_packages(tmp_path: Path):
    _write_station(tmp_path, "core", scripts={"pyforge": "pyforge.core.dispatch:main"})
    _write_station(tmp_path, "testing-kit", scripts={})
    _write_station(tmp_path, "doctor", scripts={"doctor": "pyforge.doctor.__main__:main"})
    _write_pixi_toml(tmp_path, guild_hosted=["doctor"])

    content = m.render(tmp_path, _STAMP, help_capture=lambda script: None)

    assert "## Core" not in content
    assert "## Testing Kit" not in content
    assert "## Doctor" in content


def test_render_embeds_captured_help_text_verbatim(tmp_path: Path):
    _write_station(tmp_path, "doctor", scripts={"doctor": "pyforge.doctor.__main__:main"})
    _write_pixi_toml(tmp_path, guild_hosted=["doctor"])

    content = m.render(tmp_path, _STAMP, help_capture=lambda script: "usage: doctor [-h] ...")

    assert "```text" in content
    assert "usage: doctor [-h] ..." in content


# --- capture_help itself: the REAL subprocess path, not the injected seam --


def test_capture_help_returns_none_when_the_script_exits_nonzero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Reproduces the live bug: marshal-mcp --help crashes (ModuleNotFoundError:
    # No module named 'fastmcp') and exited non-zero, but the old code returned
    # stderr's traceback anyway -- embedding it, absolute filesystem paths and
    # all, straight into the committed page.
    script = tmp_path / "broken-cli"
    script.write_text(
        "#!/bin/sh\n"
        "echo 'Traceback (most recent call last):' >&2\n"
        "echo \"ModuleNotFoundError: No module named 'fastmcp'\" >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    assert m.capture_help("broken-cli") is None


def test_render_notes_when_help_is_not_capturable(tmp_path: Path):
    _write_station(tmp_path, "mason", scripts={"mason": "pyforge.mason.cli:main"})
    _write_pixi_toml(tmp_path, guild_hosted=[])

    content = m.render(tmp_path, _STAMP, help_capture=lambda script: None)

    assert "not resolvable on PATH" in content
    assert "pixi run -e pyforge-mason mason --help" in content


def test_render_notes_a_station_with_no_console_script(tmp_path: Path):
    _write_station(tmp_path, "empty", scripts={})
    _write_pixi_toml(tmp_path, guild_hosted=[])

    content = m.render(tmp_path, _STAMP, help_capture=lambda script: None)

    assert "*(no console script declared)*" in content


def test_render_is_deterministic(tmp_path: Path):
    _write_station(tmp_path, "doctor", scripts={"doctor": "pyforge.doctor.__main__:main"})
    _write_pixi_toml(tmp_path, guild_hosted=["doctor"])

    render_a = m.render(tmp_path, _STAMP, help_capture=lambda script: "fixed help text")
    render_b = m.render(tmp_path, dict(_STAMP), help_capture=lambda script: "fixed help text")
    assert render_a == render_b


def test_main_write_then_check_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_station(tmp_path, "doctor", scripts={"doctor": "pyforge.doctor.__main__:main"})
    _write_pixi_toml(tmp_path, guild_hosted=["doctor"])
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root: dict(_STAMP))
    monkeypatch.setattr(m, "capture_help", lambda script: "fixed help text")

    monkeypatch.setattr(sys, "argv", ["docs_station_cli.py"])
    assert m.main() == 0

    monkeypatch.setattr(sys, "argv", ["docs_station_cli.py", "--check"])
    assert m.main() == 0

    # A station CLI gains a verb (its captured help text changes), not yet
    # regenerated -> --check reds it.
    monkeypatch.setattr(m, "capture_help", lambda script: "fixed help text plus a new verb")
    assert m.main() == 1
