"""Story 109.3 — ``python -m pyforge.steward.marketplace_pages --flag-env``, the Pages build line.

Split from ``test_marketplace_pages.py`` by subject (Story 109.8, ``DW-steward-109-3-7``). The line is printed only
when the flag reader's value is the one the tree and its overlay compose; every other shape is refused by name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from marketplace_testkit import _flags_tree

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    FLAG_KEY,
)

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads docs/foundry/marketplace and the estate skill
# copies, so it runs in the station's live-tree half and fires on those paths, not on every edit of the package.
pytestmark = pytest.mark.live_tree


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag tree is read for ``dev`` (where the flag is on), whatever the shell exports."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


def test_flag_env_prints_the_build_line_for_the_resolved_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``python -m pyforge.steward.marketplace_pages --flag-env`` is how the flag reaches the Pages build (review
    2026-10-28, row 6): dev on, production off, from the same tree."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 0
    assert capsys.readouterr().out == f"{FLAG_ENV}=1\n"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert main(["--flag-env"]) == 0
    assert capsys.readouterr().out == f"{FLAG_ENV}=0\n"
    with pytest.raises(SystemExit):
        main([])  # the one verb
    monkeypatch.delenv("PYFORGE_FLAGS_PATH")
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert main(["--flag-env"]) == 2  # loop 2, row 37: no tree is an error, never a silent 0
    captured = capsys.readouterr()
    assert captured.out == "" and "no flag tree found" in captured.err


def _with_entry(entry: object) -> str:
    """A flag tree that declares the marketplace flag as ``entry`` and nothing else, built rather than hand-written
    (Story 109.8, ``DW-steward-109-3-7``: TEA's M2)."""
    return json.dumps({"flags": {FLAG_KEY: entry}})


_BOOLS = {"on": True, "off": False}


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("{not json", "is not a readable JSON flag tree"),  # malformed on purpose
        (json.dumps({"flags": {}}), "declares no such flag"),
        (json.dumps({"flags": {"pyforge.other": {}}}), "declares no such flag"),
        (json.dumps({"flags": []}), "declares no such flag"),
        (json.dumps([]), "declares no such flag"),
        # loop 4, row 63: a declared entry read_boolean would default on is refused too
        (_with_entry("yes"), "a shape the reader would default on"),
        (_with_entry(None), "a shape the reader would default on"),
        (_with_entry({"defaultVariant": "off", "metadata": {}}), "a shape the reader would default on"),
        (
            _with_entry({"variants": {"on": True}, "defaultVariant": "off", "metadata": {}}),
            "a shape the reader would default on",
        ),
        (
            _with_entry({"variants": {"on": "yes", "off": False}, "defaultVariant": "on", "metadata": {}}),
            "a shape the reader would default on",
        ),
        (_with_entry({"variants": _BOOLS, "defaultVariant": "off"}), "a shape the reader would default on"),
        # loop 5, row 87: the overlay selects the variant the build reads, so every variant must be a bool
        (
            _with_entry({"variants": {"off": False, "on": "yes"}, "defaultVariant": "off", "metadata": {}}),
            "a shape the reader would default on",
        ),
        (
            _with_entry({"variants": {}, "defaultVariant": "off", "metadata": {}}),
            "a shape the reader would default on",
        ),
    ],
)
def test_flag_env_refuses_a_tree_that_does_not_declare_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], text: str, needle: str
) -> None:
    """Loop 3, row 53: a tree that resolves but is malformed or lacks the key went through read_boolean's
    WARN-and-default and printed 0 with exit 0, the row-37 failure under another cause."""
    from pyforge.steward.marketplace_pages import main

    tree = tmp_path / "flags.json"
    tree.write_text(text, encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and needle in captured.err


def test_flag_env_refuses_a_non_bool_variant_the_overlay_selects_and_a_missing_overlay_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 5, row 87: with ``on: "yes"`` under a bool default and the dev overlay naming ``on``, the reader WARNed
    and the step printed ``=0`` with exit 0; so did a tree with no ``flag-overlays.json`` beside it, though dev's
    ``on`` lives only in the overlay. The real tree prints ``=1``."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=1\n"
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"][FLAG_KEY]["variants"] = {"off": False, "on": "yes"}
    on.write_text(json.dumps(tree), encoding="utf-8")
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "a shape the reader would default on" in captured.err
    _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "flags" / "flag-overlays.json").unlink()
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "no flag-overlays.json beside" in captured.err
    real = repo_root() / "src" / "platform" / "config" / "flags.json"
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(real))
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=1\n"


def test_flag_env_refuses_an_overlay_the_reader_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 4, row 63: an overlay document the reader raises on is exit 2 with its message, never a traceback."""
    from pyforge.steward.marketplace_pages import main

    on = _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "flags" / "flag-overlays.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "refusing to print a build line" in captured.err
    # the reader's own metadata check (it runs when an overlay is composed): exit 2 with its message, no traceback
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"][FLAG_KEY]["metadata"] = {}
    on.write_text(json.dumps(tree), encoding="utf-8")
    (tmp_path / "flags" / "flag-overlays.json").write_text(
        json.dumps({"dev": {FLAG_KEY: "on"}, "staging": {}, "production": {}}), encoding="utf-8"
    )
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "metadata" in captured.err and "refusing to print a build line" in captured.err


@pytest.mark.parametrize(
    ("state", "present"),
    [("enabled", True), ("disabled", True), (None, False)],
    ids=["lower-case", "lower-case-disabled", "absent"],  # Story 109.8: DISABLED is matched whole too
)
def test_flag_env_refuses_a_state_the_flag_reader_does_not_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], state: object, present: bool
) -> None:
    """Loop 7, row 113: the flag reader's OpenFeature file provider accepts a state of exactly ``ENABLED`` or
    ``DISABLED`` and falls back to off on anything else, so the step printed ``=0`` with exit 0 while the dev overlay
    was on. The state is now refused before the reader runs."""
    from pyforge.steward.marketplace_pages import main

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    if present:
        tree["flags"][FLAG_KEY]["state"] = state
    else:
        tree["flags"][FLAG_KEY].pop("state")
    on.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "accepts ENABLED or DISABLED only" in captured.err


def test_flag_env_never_prints_a_value_the_reader_defaulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 7, row 113: a sibling flag the file provider cannot parse (``state: PAUSED``, or an unknown key) makes the
    reader fall back to off for every flag, and the step printed ``=0`` with exit 0 while the dev overlay was on. The
    reader's value is now compared with the composed one. The reader is replaced by its fallback here: the real one
    would pin the process-wide OpenFeature provider to a tree flagd cannot parse, and the next test on the worker to
    restore its provider would raise at teardown (loop 8; the real fallback was probed against flagd in loop 8)."""
    import pyforge.steward.marketplace_pages as marketplace_pages

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"]["pyforge.other"] = dict(tree["flags"][FLAG_KEY], state="PAUSED")
    on.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    monkeypatch.setattr(marketplace_pages, "pages_enabled", lambda **_: False)
    assert marketplace_pages.main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "the reader fell back to its default" in captured.err
    assert "targeting rule" not in captured.err  # review loop 2, row 11: no rule, so none is named


@pytest.mark.parametrize("value", [["on"], {"v": "on"}])
def test_flag_env_refuses_an_overlay_value_that_is_no_variant_name_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], value: object
) -> None:
    """Loop 8, row 123: the loop-7 comparison read the overlay value before the reader had validated it, so a list or
    object value raised a raw ``TypeError`` (exit 1) where ``b16ee6c0b0`` refused it by name (exit 2)."""
    from pyforge.steward.marketplace_pages import main

    on = _flags_tree(tmp_path / "flags", dev="on")
    overlays = {"dev": {FLAG_KEY: value}, "staging": {FLAG_KEY: "off"}, "production": {FLAG_KEY: "off"}}
    (tmp_path / "flags" / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert (
        captured.out == "" and "not a variant name" in captured.err and "refusing to print a build line" in captured.err
    )


def test_flag_env_reads_the_overlay_of_the_resolved_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 7, row 113: the overlay value is read for ``PYFORGE_ENVIRONMENT``, not for ``dev``; an overlay naming the
    flag under dev only is refused under staging (loop 7 found a mutant reading ``dev`` always surviving)."""
    from pyforge.steward.marketplace_pages import main

    on = _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "flags" / "flag-overlays.json").write_text(json.dumps({"dev": {FLAG_KEY: "on"}}), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "names no value for the flag under staging" in captured.err


@pytest.mark.parametrize("overlays", [{}, {"dev": {}}, {"dev": {"pyforge.other": "on"}, "staging": {}}])
def test_flag_env_refuses_an_overlay_file_with_no_value_for_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], overlays: dict
) -> None:
    """Loop 6, row 101: an overlay file that exists but names no value for the flag under the resolved environment
    read the base default and printed ``=0`` with exit 0, the silent-off row 87 refused for an absent file. A killed
    flag keeps its tree default, so it needs no overlay value."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    if "pyforge.other" in json.dumps(overlays):
        tree["flags"]["pyforge.other"] = dict(tree["flags"][FLAG_KEY])
        on.write_text(json.dumps(tree), encoding="utf-8")
    (tmp_path / "flags" / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "names no value for the flag under dev" in captured.err
    tree["flags"][FLAG_KEY]["state"] = "DISABLED"
    on.write_text(json.dumps(tree), encoding="utf-8")
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=0\n"


# --- Story 109.8 (DW-steward-109-3-10): loop 8's untested shapes ------------------------------------------------------


@pytest.mark.parametrize("where", ["own", "sibling"])
def test_flag_env_refuses_a_tree_whose_flag_reader_refuses_an_unknown_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], where: str
) -> None:
    """Loop 7, row 113's two unknown-key shapes, probed in loop 8 but not tested: flagd's file provider refuses the
    whole tree when this flag or a sibling carries a key it does not know, and the reader reads its default (off).
    What these pin is ``main``'s side: neither shape is refused earlier by the entry-shape check under another
    message; each reaches the comparison and is refused there. The reader is replaced by its fallback, as in the
    test above: the real one would pin the process-wide provider to a tree flagd cannot parse, and its readiness
    wait costs 8 s a run (the real reader exits 2 for both shapes, probed 2026-10-30 and again by review loop 1)."""
    import pyforge.steward.marketplace_pages as marketplace_pages

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    entry = tree["flags"][FLAG_KEY]
    if where == "own":
        entry["bogus"] = 1
    else:
        tree["flags"]["pyforge.other"] = {**entry, "bogus": 1}
    on.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    monkeypatch.setattr(marketplace_pages, "pages_enabled", lambda **_: False)
    assert marketplace_pages.main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "the reader fell back to its default" in captured.err
    assert "targeting rule" not in captured.err  # review loop 2, row 11: no rule, so none is named


def test_flag_env_names_a_targeting_rule_that_turns_the_flag_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A targeting rule picks the variant, or the reader fell back to its default when its provider refused the tree
    (review loop 1, row 1: a rule selecting ``on`` beside a sibling's unknown key reads off too); the refusal names
    both causes, not one that may not have happened. The reader is replaced by the value it read (``False``)."""
    import pyforge.steward.marketplace_pages as marketplace_pages

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"][FLAG_KEY]["targeting"] = {"if": [True, "off", "on"]}
    on.write_text(json.dumps(tree), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    monkeypatch.setattr(marketplace_pages, "pages_enabled", lambda **_: False)
    assert marketplace_pages.main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        "gives the flag a targeting rule; the flag reader read False where the tree and its overlay compose True, "
        "either because the rule selected that variant or because the reader fell back to its default when its "
        "provider refused the tree" in captured.err
    )
