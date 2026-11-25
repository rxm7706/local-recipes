"""Story 48.5 flag kill-switch actuator tests.

The two tests that reach outside this package (django-pyforge's flags resolver, the shipped platform flag
tree) run in the live-tree half, ``test_live_flag_kill_switch.py`` (Story 58.2).
"""

from __future__ import annotations

import errno
import json
import stat
from pathlib import Path

import pytest

from pyforge.doctor.actuators.flag_kill_switch import (
    disable_flag,
    kill_switch,
    record_kill_switch_metric,
)


def _sample_tree() -> dict:
    return {
        "flags": {
            "pyforge.three_surfaces": {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "on",
            }
        }
    }


def test_disable_flag_writes_disabled_state(tmp_path: Path):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    result = disable_flag(path, "pyforge.three_surfaces")
    assert result.new_state == "DISABLED"
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"


def test_kill_switch_records_metric(tmp_path: Path, monkeypatch):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def _record(flag: str, reason: str) -> None:
        calls.append((flag, reason))

    monkeypatch.setattr(
        "pyforge.doctor.actuators.flag_kill_switch.record_kill_switch_metric",
        _record,
    )
    kill_switch(path, "pyforge.three_surfaces", "test")
    assert calls == [("pyforge.three_surfaces", "test")]


def test_disable_flag_missing_key_raises(tmp_path: Path):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    with pytest.raises(KeyError):
        disable_flag(path, "missing.flag")


def test_record_kill_switch_metric_noop_without_prometheus(monkeypatch):
    monkeypatch.setattr(
        "pyforge.doctor.actuators.flag_kill_switch._KILL_SWITCH_TOTAL",
        None,
    )
    record_kill_switch_metric("pyforge.three_surfaces", "test")


def test_disable_flag_replaces_the_tree_in_one_step(tmp_path: Path, monkeypatch):
    """Story 62.1 (DW-doctor-61-1-2, defect 1): a write that fails part-way leaves ``flags.json`` byte-identical
    with no temporary file beside it, so no reader sees a truncated tree and falls back to a flag's default; a
    successful run keeps the file's own mode."""
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    path.chmod(0o640)
    before = path.read_bytes()
    real_write_text = Path.write_text

    def _fails_part_way(self: Path, data: str, *args, **kwargs) -> int:
        real_write_text(self, data[: len(data) // 2], *args, **kwargs)
        raise OSError("disk full")

    with monkeypatch.context() as patched:
        patched.setattr(Path, "write_text", _fails_part_way)
        with pytest.raises(OSError, match="disk full"):
            disable_flag(path, "pyforge.three_surfaces")

    assert path.read_bytes() == before
    assert [entry.name for entry in tmp_path.iterdir()] == ["flags.json"]

    disable_flag(path, "pyforge.three_surfaces")

    assert json.loads(path.read_text(encoding="utf-8"))["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert [entry.name for entry in tmp_path.iterdir()] == ["flags.json"]


def test_kill_switch_result_line_names_the_reason(tmp_path: Path, capsys):
    """Story 62.1 (DW-doctor-61-1-2, defect 2): the counter dies with the one-shot process, so the result line is
    where the operator's reason outlives it, beside the flag, the path and the state change."""
    from pyforge.doctor.__main__ import main

    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")

    rc = main(
        [
            "flags",
            "kill-switch",
            "--flag",
            "pyforge.three_surfaces",
            "--reason",
            "incident 4711: bad rollout",
            "--flags-path",
            str(path),
        ]
    )

    assert rc == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert "pyforge.three_surfaces" in lines[0]
    assert str(path) in lines[0]
    assert "ENABLED -> DISABLED" in lines[0]
    assert "incident 4711: bad rollout" in lines[0]


def test_kill_switch_unknown_flag_exits_2_and_leaves_the_tree_byte_identical(tmp_path: Path, capsys):
    """Story 62.1: an unknown key stays a usage error (exit 2), the file untouched and nothing left beside it."""
    from pyforge.doctor.__main__ import main

    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    before = path.read_bytes()

    rc = main(["flags", "kill-switch", "--flag", "missing.flag", "--reason", "test", "--flags-path", str(path)])

    assert rc == 2
    assert path.read_bytes() == before
    assert [entry.name for entry in tmp_path.iterdir()] == ["flags.json"]
    assert capsys.readouterr().out == ""


def test_disable_flag_writes_through_a_symlinked_tree(tmp_path: Path):
    """Story 62.1: a tree reached through a symlink is replaced at its real path -- the link stays a link, the
    file every reader opens reads DISABLED with its own mode kept, and the result names the path the caller gave."""
    real_dir = tmp_path / "real"
    link_dir = tmp_path / "link"
    real_dir.mkdir()
    link_dir.mkdir()
    real = real_dir / "flags.json"
    real.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    real.chmod(0o640)
    link = link_dir / "flags.json"
    link.symlink_to(real)

    result = disable_flag(link, "pyforge.three_surfaces")

    assert result.path == link
    assert link.is_symlink()
    assert link.resolve() == real.resolve()
    assert not real.is_symlink()
    assert json.loads(real.read_text(encoding="utf-8"))["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"
    assert stat.S_IMODE(real.stat().st_mode) == 0o640
    assert [entry.name for entry in real_dir.iterdir()] == ["flags.json"]
    assert [entry.name for entry in link_dir.iterdir()] == ["flags.json"]


def test_kill_switch_prints_a_multi_line_reason_on_one_line(tmp_path: Path, capsys):
    """Story 62.1: the result is one line whatever the reason holds -- a newline, a tab or a carriage return in
    ``--reason`` is folded to one space, so a log reader keyed on the ``disabled`` line has the whole reason."""
    from pyforge.doctor.__main__ import main

    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")

    rc = main(
        [
            "flags",
            "kill-switch",
            "--flag",
            "pyforge.three_surfaces",
            "--reason",
            "incident 4711:\n  bad rollout\r\n\tpaged at 03:10",
            "--flags-path",
            str(path),
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert out.endswith("\n")
    assert out.count("\n") == 1
    assert "\r" not in out
    assert "\t" not in out
    assert out.rstrip("\n").endswith("; reason: incident 4711: bad rollout paged at 03:10")


def test_kill_switch_refuses_a_tree_in_a_directory_it_cannot_write(tmp_path: Path, capsys, monkeypatch):
    """Story 62.1: the replace needs a new file in the tree's directory. Where the process cannot create one the
    command is a named refusal (exit 2), not an internal error, and the tree is byte-identical: still ENABLED.

    The refused create is the kernel's own ``mkstemp`` raising what a read-only directory raises, so the case
    holds for any user (root writes through a 0o555 directory) with no skip.
    """
    import tempfile

    from pyforge.doctor.__main__ import main

    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    before = path.read_bytes()
    asked: list[str] = []

    def _directory_refuses(*_args, dir=None, **_kwargs):  # noqa: A002 -- mkstemp's own keyword
        asked.append(str(dir))
        raise PermissionError(errno.EACCES, "Permission denied", str(Path(str(dir)) / ".flags.json-x.tmp"))

    with monkeypatch.context() as patched:
        patched.setattr(tempfile, "mkstemp", _directory_refuses)
        rc = main(
            ["flags", "kill-switch", "--flag", "pyforge.three_surfaces", "--reason", "test", "--flags-path", str(path)]
        )

    captured = capsys.readouterr()
    assert rc == 2
    assert asked == [str(tmp_path.resolve())]
    assert path.read_bytes() == before
    assert [entry.name for entry in tmp_path.iterdir()] == ["flags.json"]
    assert captured.out == ""
    assert f"doctor flags kill-switch: cannot replace {path}: " in captured.err
    assert "Permission denied" in captured.err
    assert "internal error" not in captured.err
    assert "Traceback" not in captured.err
