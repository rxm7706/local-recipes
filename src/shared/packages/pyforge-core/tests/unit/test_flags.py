"""Story 75.1 -- ``pyforge.core.flags``, the fleet-wide CLI flag contract.

Pins the contract every station's flagged CLI story reuses: ``read_boolean``'s
OFF/absent semantics, its one tree resolver, and the Q3 helpers (``FlagOff``,
``require``, ``disabled_help``). The module defines no exit code.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pyforge.core import cutover_root, flags
from pyforge.core.flags import FlagOff, disabled_help, read_boolean, require

KEY = "pyforge.test.some_capability"


def _tree(tmp_path: Path, entry: object, *, key: str = KEY, name: str = "flags.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"flags": {key: entry}}), encoding="utf-8")
    return path


def _bool_entry(variant: str, *, state: str = "ENABLED") -> dict[str, object]:
    return {"state": state, "variants": {"on": True, "off": False}, "defaultVariant": variant}


# --- the fourteenth acceptance criterion's tree matrix ------------------------


def test_a_boolean_key_on_reads_true_with_no_warn(tmp_path, capsys):
    assert read_boolean(KEY, flags_path=_tree(tmp_path, _bool_entry("on"))) is True
    assert capsys.readouterr().err == ""


def test_a_boolean_key_off_reads_false_with_no_warn(tmp_path, capsys):
    assert read_boolean(KEY, flags_path=_tree(tmp_path, _bool_entry("off"))) is False
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("default", [False, True])
def test_state_disabled_reads_false_whatever_else_is_set(tmp_path, capsys, default):
    tree = _tree(tmp_path, _bool_entry("on", state="DISABLED"))
    assert read_boolean(KEY, default, flags_path=tree) is False
    assert capsys.readouterr().err == ""


def _absent_trees(tmp_path: Path) -> dict[str, Path]:
    """The four reads that fall back to `default`, each with its own tree."""
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not json", encoding="utf-8")
    return {
        "missing key": _tree(tmp_path, _bool_entry("on"), key="pyforge.test.other"),
        "string-valued key": _tree(
            tmp_path,
            {"state": "ENABLED", "variants": {"on": "on", "off": "off"}, "defaultVariant": "on"},
            name="string.json",
        ),
        "malformed tree": malformed,
        "no tree": tmp_path / "does-not-exist.json",
    }


@pytest.mark.parametrize("default", [False, True])
def test_absent_reads_return_default_with_one_named_warn_each(tmp_path, capsys, default):
    for label, tree in _absent_trees(tmp_path).items():
        assert read_boolean(KEY, default, flags_path=tree) is default, label
        err = capsys.readouterr().err
        lines = [line for line in err.splitlines() if line.strip()]
        assert len(lines) == 1, (label, err)
        assert "WARN" in lines[0]
        assert KEY in lines[0], "the WARN must name the key"


def test_the_default_default_is_false(tmp_path):
    assert read_boolean(KEY, flags_path=tmp_path / "does-not-exist.json") is False


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ([], "no 'flags' object"),
        ({"flags": []}, "no 'flags' object"),
        ({"flags": {KEY: "on"}}, "not an object"),
        ({"flags": {KEY: {"state": "ENABLED"}}}, "lacks variants/defaultVariant"),
        ({"flags": {KEY: {"variants": {"on": True}, "defaultVariant": "nope"}}}, "lacks variants/defaultVariant"),
    ],
)
def test_structurally_wrong_trees_read_default_with_a_named_reason(tmp_path, capsys, payload, reason):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read_boolean(KEY, True, flags_path=path) is True
    err = capsys.readouterr().err
    assert reason in err and KEY in err


def test_an_unreadable_tree_reads_default_with_a_warn(tmp_path, capsys):
    path = tmp_path / "flags.json"
    path.write_bytes(b"\xff\xfe\x00not utf-8")
    assert read_boolean(KEY, False, flags_path=path) is False
    assert "unreadable flag tree" in capsys.readouterr().err


def test_the_kill_switch_wins_even_without_variants(tmp_path, capsys):
    tree = _tree(tmp_path, {"state": "DISABLED"})
    assert read_boolean(KEY, True, flags_path=tree) is False
    assert capsys.readouterr().err == ""


# --- one tree resolver, reused ------------------------------------------------


def test_the_explicit_path_wins_over_the_environment(tmp_path, monkeypatch):
    env_tree = _tree(tmp_path, _bool_entry("off"), name="env.json")
    explicit = _tree(tmp_path, _bool_entry("on"), name="explicit.json")
    monkeypatch.setenv(cutover_root.ENV_FLAGS_PATH, str(env_tree))
    assert read_boolean(KEY, flags_path=explicit) is True
    assert read_boolean(KEY, flags_path=str(explicit)) is True


def test_the_environment_variable_is_the_second_source(tmp_path, monkeypatch):
    monkeypatch.setenv(cutover_root.ENV_FLAGS_PATH, str(_tree(tmp_path, _bool_entry("on"))))
    assert read_boolean(KEY) is True


def test_the_walk_up_from_the_working_directory_is_the_third_source(tmp_path, monkeypatch):
    monkeypatch.delenv(cutover_root.ENV_FLAGS_PATH, raising=False)
    config = tmp_path / "src" / "platform" / "config"
    config.mkdir(parents=True)
    (config / "flags.json").write_text(json.dumps({"flags": {KEY: _bool_entry("on")}}), encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert read_boolean(KEY) is True


def test_read_boolean_calls_the_one_resolver(tmp_path, monkeypatch):
    seen: list[object] = []
    tree = _tree(tmp_path, _bool_entry("on"))

    def fake_resolver(explicit=None):
        seen.append(explicit)
        return tree

    monkeypatch.setattr(cutover_root, "resolve_flags_path", fake_resolver)
    assert read_boolean(KEY) is True
    assert read_boolean(KEY, flags_path="/anything") is True
    assert seen == [None, "/anything"]


def test_no_second_tree_resolver_exists_in_pyforge_core():
    """The tree resolver is `cutover_root.resolve_flags_path` alone: no other
    `pyforge.core` module defines a resolver of that shape or spells the env
    var / the tree's relative path itself."""
    core = Path(flags.__file__).parent
    defining: list[str] = []
    spelling: list[str] = []
    for path in sorted(core.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "flags_path" in node.name:
                defining.append(f"{path.name}:{node.name}")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in {cutover_root.ENV_FLAGS_PATH, "src/platform/config/flags.json"}
                and path.name != "cutover_root.py"
            ):
                spelling.append(f"{path.name}:{node.value}")
    assert defining == ["cutover_root.py:resolve_flags_path"]
    assert spelling == []


# --- the Q3 helpers -----------------------------------------------------------


def test_flag_off_carries_the_key_and_the_message():
    exc = FlagOff(KEY)
    assert exc.key == KEY
    assert str(exc) == f"flag {KEY} is off"
    assert isinstance(exc, Exception) and not isinstance(exc, SystemExit)


def test_require_raises_when_the_flag_is_off_and_returns_when_on(tmp_path):
    with pytest.raises(FlagOff) as caught:
        require(KEY, flags_path=_tree(tmp_path, _bool_entry("off"), name="off.json"))
    assert caught.value.key == KEY
    assert require(KEY, flags_path=_tree(tmp_path, _bool_entry("on"), name="on.json")) is None


def test_require_off_when_the_tree_is_absent_by_default(tmp_path):
    with pytest.raises(FlagOff):
        require(KEY, flags_path=tmp_path / "does-not-exist.json")


def test_require_honors_a_retrofit_default_true(tmp_path, capsys):
    absent = tmp_path / "does-not-exist.json"
    assert require(KEY, True, flags_path=absent) is None
    assert "WARN" in capsys.readouterr().err
    with pytest.raises(FlagOff):  # the kill switch still wins
        require(KEY, True, flags_path=_tree(tmp_path, _bool_entry("on", state="DISABLED")))


def test_disabled_help_marks_an_off_flag_and_leaves_an_on_flag_unchanged(tmp_path):
    off = _tree(tmp_path, _bool_entry("off"), name="off.json")
    on = _tree(tmp_path, _bool_entry("on"), name="on.json")
    assert disabled_help("run a child", KEY, flags_path=off) == f"run a child [disabled: flag {KEY} is off]"
    assert disabled_help("run a child", KEY, flags_path=on) == "run a child"


def test_the_module_defines_no_exit_code():
    """`flags` never chooses an exit code: each station's `main()` does."""
    source = Path(flags.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        f"{node.func.value.id}.{node.func.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
    }
    assert "sys.exit" not in calls and "os._exit" not in calls
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not {"SystemExit"} & names
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id.upper().startswith("EXIT") for t in n.targets
    )]
