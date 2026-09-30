"""Story 75.1 -- ``pyforge.core.flags``, the fleet-wide CLI flag contract.

Pins the contract every station's flagged CLI story reuses: ``read_boolean``'s
OFF/absent semantics, its one tree resolver, and the Q3 helpers (``FlagOff``,
``require``, ``disabled_help``). The module defines no exit code.

Story 76.1 adds the per-environment rendering: ``PYFORGE_ENVIRONMENT``, the value-only
``flag-overlays.json`` beside the tree, ``compose`` / ``render`` and their named errors.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pyforge.core import cutover_root, flags
from pyforge.core.flags import FlagOff, disabled_help, read_boolean, require

KEY = "pyforge.test.some_capability"


@pytest.fixture(autouse=True)
def _no_ambient_environment(monkeypatch):
    """A developer's or CI's own PYFORGE_ENVIRONMENT must not decide these reads."""
    monkeypatch.delenv(flags.ENV_ENVIRONMENT, raising=False)


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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
    }
    assert "sys.exit" not in calls and "os._exit" not in calls
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not {"SystemExit"} & names
    assert not [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id.upper().startswith("EXIT") for t in n.targets)
    ]


# --- Story 76.1: per-environment values ---------------------------------------

OTHER = "pyforge.test.other_capability"


def _overlay_tree(tmp_path: Path, overlays: object, *, tree: dict | None = None) -> Path:
    """A tree with two flags (KEY on, OTHER off) and a sibling ``flag-overlays.json``."""
    flags_json = tmp_path / "flags.json"
    flags_json.write_text(
        json.dumps(tree if tree is not None else {"flags": {KEY: _bool_entry("on"), OTHER: _bool_entry("off")}}),
        encoding="utf-8",
    )
    (tmp_path / flags.OVERLAYS_FILE_NAME).write_text(json.dumps(overlays), encoding="utf-8")
    return flags_json


def _production_off(tmp_path: Path) -> Path:
    return _overlay_tree(tmp_path, {"dev": {}, "staging": {KEY: "on"}, "production": {KEY: "off"}})


def _read_in(environment: str | None, monkeypatch, tree: Path, key: str = KEY) -> bool:
    if environment is None:
        monkeypatch.delenv(flags.ENV_ENVIRONMENT, raising=False)
    else:
        monkeypatch.setenv(flags.ENV_ENVIRONMENT, environment)
    return read_boolean(key, flags_path=tree)


def test_an_overlay_names_off_for_production_only(tmp_path, monkeypatch, capsys):
    tree = _production_off(tmp_path)
    assert _read_in("production", monkeypatch, tree) is False
    assert _read_in("staging", monkeypatch, tree) is True
    assert _read_in("dev", monkeypatch, tree) is True
    assert capsys.readouterr().err == ""
    for environment, expected in (("production", "off"), ("staging", "on"), ("dev", "on")):
        rendered = json.loads(flags.render(environment, flags_path=tree))
        assert rendered["flags"][KEY]["defaultVariant"] == expected, environment
        assert rendered["flags"][OTHER]["defaultVariant"] == "off", environment  # unnamed keys keep the tree's


def test_an_overlay_can_also_turn_a_flag_on_where_the_tree_says_off(tmp_path, monkeypatch):
    tree = _overlay_tree(tmp_path, {"staging": {OTHER: "on"}})
    assert _read_in("staging", monkeypatch, tree, OTHER) is True
    assert _read_in("production", monkeypatch, tree, OTHER) is False
    assert _read_in("dev", monkeypatch, tree, OTHER) is False


def test_the_environment_is_dev_when_unset(tmp_path, monkeypatch):
    tree = _overlay_tree(tmp_path, {"dev": {KEY: "off"}, "production": {KEY: "on"}})
    assert flags.current_environment() == "dev"
    assert _read_in(None, monkeypatch, tree) is False  # the dev rendering, not the tree's own ``on``


@pytest.mark.parametrize("environment", ["dev", "staging", "production"])
def test_the_three_environments_are_accepted(environment):
    assert flags.current_environment({flags.ENV_ENVIRONMENT: environment}) == environment


@pytest.mark.parametrize("bad", ["qa", "prod", "Production", "", " dev"])
@pytest.mark.parametrize("default", [False, True])
def test_an_unknown_environment_refuses_with_a_named_error_and_never_reads_on(
    tmp_path, monkeypatch, capsys, bad, default
):
    tree = _tree(tmp_path, _bool_entry("on"))  # even a tree that reads ON
    monkeypatch.setenv(flags.ENV_ENVIRONMENT, bad)
    with pytest.raises(flags.UnknownEnvironmentError) as caught:
        read_boolean(KEY, default, flags_path=tree)
    assert isinstance(caught.value, flags.FlagConfigError) and isinstance(caught.value, ValueError)
    assert repr(bad) in str(caught.value) and flags.ENV_ENVIRONMENT in str(caught.value)
    assert capsys.readouterr().err == ""


def test_an_unknown_environment_refuses_before_the_tree_is_looked_for(tmp_path, monkeypatch):
    monkeypatch.setenv(flags.ENV_ENVIRONMENT, "qa")
    with pytest.raises(flags.UnknownEnvironmentError):
        read_boolean(KEY, True, flags_path=tmp_path / "does-not-exist.json")


def test_require_and_disabled_help_propagate_an_unknown_environment(tmp_path, monkeypatch):
    tree = _tree(tmp_path, _bool_entry("on"))
    monkeypatch.setenv(flags.ENV_ENVIRONMENT, "qa")
    with pytest.raises(flags.UnknownEnvironmentError):
        require(KEY, flags_path=tree)
    with pytest.raises(flags.UnknownEnvironmentError):
        disabled_help("run a child", KEY, flags_path=tree)


def test_state_disabled_stays_off_in_every_environment_whatever_the_overlay_says(tmp_path, monkeypatch):
    tree = _overlay_tree(
        tmp_path,
        {name: {KEY: "on"} for name in flags.ENVIRONMENTS},
        tree={"flags": {KEY: _bool_entry("off", state="DISABLED")}},
    )
    for environment in flags.ENVIRONMENTS:
        assert _read_in(environment, monkeypatch, tree) is False, environment
        rendered = json.loads(flags.render(environment, flags_path=tree))
        assert rendered["flags"][KEY]["state"] == "DISABLED"
        assert rendered["flags"][KEY]["defaultVariant"] == "off"  # the kill switch's entry is left as it is
    assert read_boolean(KEY, True, flags_path=tree) is False


def test_an_overlay_key_the_tree_lacks_is_a_named_error_naming_it(tmp_path):
    tree = _overlay_tree(tmp_path, {"production": {"pyforge.test.missing": "off"}})
    with pytest.raises(flags.OverlayUnknownKeyError) as caught:
        flags.render("production", flags_path=tree)
    assert "production" in str(caught.value) and "pyforge.test.missing" in str(caught.value)


def test_an_overlay_variant_the_flag_lacks_is_a_named_error_naming_it(tmp_path):
    tree = _overlay_tree(tmp_path, {"staging": {KEY: "maybe"}})
    with pytest.raises(flags.OverlayUnknownVariantError) as caught:
        flags.render("staging", flags_path=tree)
    assert "staging" in str(caught.value) and KEY in str(caught.value) and "maybe" in str(caught.value)


def test_a_flag_without_variants_cannot_take_an_overlay_variant(tmp_path):
    tree = _overlay_tree(tmp_path, {"dev": {KEY: "on"}}, tree={"flags": {KEY: {"state": "ENABLED"}}})
    with pytest.raises(flags.OverlayUnknownVariantError):
        flags.render("dev", flags_path=tree)


@pytest.mark.parametrize(
    "entry",
    [
        {"state": "ENABLED", "variants": {"on": True}, "defaultVariant": "on"},
        {"off": False},
        True,
        7,
        ["off"],
        None,
    ],
)
def test_an_overlay_entry_that_is_not_a_variant_name_is_a_named_error(tmp_path, entry):
    tree = _overlay_tree(tmp_path, {"production": {KEY: entry}})
    with pytest.raises(flags.OverlayNotAVariantError) as caught:
        flags.render("production", flags_path=tree)
    assert "production" in str(caught.value) and KEY in str(caught.value)
    assert "variant name" in str(caught.value)


def test_an_environment_outside_the_three_in_the_overlay_document_is_a_named_error(tmp_path):
    tree = _overlay_tree(tmp_path, {"qa": {KEY: "off"}})
    with pytest.raises(flags.UnknownEnvironmentError) as caught:
        flags.render("dev", flags_path=tree)
    assert "'qa'" in str(caught.value)


@pytest.mark.parametrize("overlays", [[], "off", {"production": []}, {"production": "off"}, {"dev": None}])
def test_a_malformed_overlay_document_is_a_named_error(tmp_path, overlays):
    tree = _overlay_tree(tmp_path, overlays)
    with pytest.raises(flags.OverlayDocumentError):
        flags.render("production", flags_path=tree)


def test_an_unreadable_overlay_document_is_a_named_error(tmp_path):
    tree = _overlay_tree(tmp_path, {})
    (tmp_path / flags.OVERLAYS_FILE_NAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(flags.OverlayDocumentError) as caught:
        flags.render("dev", flags_path=tree)
    assert "unreadable overlay document" in str(caught.value)


def test_every_environment_of_the_document_is_validated_whichever_is_read(tmp_path, monkeypatch):
    """A typo in `production` must not wait for a production read to surface."""
    tree = _overlay_tree(tmp_path, {"production": {KEY: "maybe"}})
    monkeypatch.setenv(flags.ENV_ENVIRONMENT, "dev")
    with pytest.raises(flags.OverlayUnknownVariantError):
        read_boolean(KEY, flags_path=tree)
    with pytest.raises(flags.OverlayUnknownVariantError):
        flags.render("dev", flags_path=tree)


@pytest.mark.parametrize("default", [False, True])
def test_a_broken_overlay_never_reads_default_from_read_boolean(tmp_path, default):
    tree = _overlay_tree(tmp_path, {"production": {"pyforge.test.missing": "off"}})
    with pytest.raises(flags.OverlayUnknownKeyError):
        read_boolean(KEY, default, flags_path=tree)


def test_an_overlay_leaves_the_75_1_warn_semantics_alone(tmp_path, capsys):
    tree = _overlay_tree(tmp_path, {"dev": {KEY: "off"}})
    assert read_boolean("pyforge.test.absent", True, flags_path=tree) is True
    err = capsys.readouterr().err
    assert "WARN" in err and "pyforge.test.absent" in err and "key missing from" in err


def test_a_tree_without_a_sibling_overlay_reads_as_it_is_in_every_environment(tmp_path, monkeypatch):
    """The in-cluster mount holds the rendered tree and no sibling."""
    tree = _tree(tmp_path, _bool_entry("off"))
    for environment in (None, *flags.ENVIRONMENTS):
        assert _read_in(environment, monkeypatch, tree) is False, environment


def test_the_rendered_tree_read_back_agrees_with_read_boolean(tmp_path, monkeypatch):
    """The ConfigMap's bytes (no sibling) and the checkout (tree + overlay) evaluate alike."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    source = _overlay_tree(checkout, {"staging": {OTHER: "on"}, "production": {KEY: "off", OTHER: "on"}})
    for environment in flags.ENVIRONMENTS:
        mount = tmp_path / f"mount-{environment}"
        mount.mkdir()
        (mount / "flags.json").write_bytes(flags.render(environment, flags_path=source))
        for key in (KEY, OTHER):
            assert _read_in(environment, monkeypatch, source, key) is _read_in(
                environment, monkeypatch, mount / "flags.json", key
            ), (environment, key)


def test_compose_does_not_modify_its_inputs(tmp_path):
    tree = {"flags": {KEY: _bool_entry("on")}}
    overlays = {"production": {KEY: "off"}}
    composed = flags.compose(tree, overlays, "production")
    assert composed["flags"][KEY]["defaultVariant"] == "off"
    assert tree == {"flags": {KEY: _bool_entry("on")}}
    assert overlays == {"production": {KEY: "off"}}


def test_compose_keeps_every_other_field_of_the_tree():
    tree = {"$schema": "https://flagd.dev/schema/v0/flags.json", "flags": {KEY: {**_bool_entry("on"), "metadata": {"owner": "steward"}}}}
    composed = flags.compose(tree, {"dev": {KEY: "off"}}, "dev")
    assert composed["$schema"] == tree["$schema"]
    assert composed["flags"][KEY]["metadata"] == {"owner": "steward"}
    assert composed["flags"][KEY]["defaultVariant"] == "off"


def test_render_without_an_overlay_is_the_tree_as_json(tmp_path):
    tree = _tree(tmp_path, _bool_entry("on"))
    assert json.loads(flags.render("production", flags_path=tree)) == json.loads(tree.read_text(encoding="utf-8"))


def test_render_uses_the_one_resolver_and_ends_with_a_newline(tmp_path, monkeypatch):
    tree = _production_off(tmp_path)
    monkeypatch.setenv(cutover_root.ENV_FLAGS_PATH, str(tree))
    rendered = flags.render("production")
    assert rendered.endswith(b"\n")
    assert json.loads(rendered)["flags"][KEY]["defaultVariant"] == "off"


def test_render_refuses_an_unknown_environment_a_missing_tree_and_a_broken_tree(tmp_path, monkeypatch):
    tree = _production_off(tmp_path)
    with pytest.raises(flags.UnknownEnvironmentError):
        flags.render("qa", flags_path=tree)
    with pytest.raises(flags.FlagTreeError):
        flags.render("dev", flags_path=tmp_path / "does-not-exist.json")
    for name, text in (("garbage.json", "{not json"), ("array.json", "[]")):
        broken = tmp_path / name
        broken.write_text(text, encoding="utf-8")
        with pytest.raises(flags.FlagTreeError):
            flags.render("dev", flags_path=broken)
    bare = tmp_path / "bare"
    bare.mkdir()
    no_flags = _overlay_tree(bare, {"dev": {}}, tree={"other": 1})
    with pytest.raises(flags.FlagTreeError):
        flags.render("dev", flags_path=no_flags)


def test_overlays_path_for_is_the_sibling_document_only(tmp_path):
    tree = _tree(tmp_path, _bool_entry("on"))
    assert flags.overlays_path_for(tree) is None
    (tmp_path / flags.OVERLAYS_FILE_NAME).write_text("{}", encoding="utf-8")
    assert flags.overlays_path_for(tree) == tmp_path / flags.OVERLAYS_FILE_NAME
    assert flags.overlays_path_for(str(tree)) == tmp_path / flags.OVERLAYS_FILE_NAME


def test_the_shipped_overlay_composes_against_the_shipped_tree_in_every_environment():
    """A durable invariant of the repo's own pair (skips when the tree is not in this checkout)."""
    config = Path(__file__).resolve().parents[6] / "src" / "platform" / "config"
    tree, overlays = config / "flags.json", config / flags.OVERLAYS_FILE_NAME
    if not tree.is_file():
        pytest.skip("src/platform/config/flags.json is not in this checkout")
    assert overlays.is_file(), "the tree's value-only overlay document is missing"
    payload = json.loads(tree.read_text(encoding="utf-8"))
    document = flags.load_overlays(overlays)
    assert set(document) <= set(flags.ENVIRONMENTS)
    for environment in flags.ENVIRONMENTS:
        composed = flags.compose(payload, document, environment)
        assert set(composed["flags"]) == set(payload["flags"])  # an overlay defines nothing
        assert json.loads(flags.render(environment, flags_path=tree)) == composed
