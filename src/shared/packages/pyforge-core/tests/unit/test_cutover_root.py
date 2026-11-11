"""Story 44.12 — pyforge-core cutover_root reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.core.cutover_root import (
    CUTOVER_VARIANTS,
    DEFAULT_CUTOVER_ROOT,
    FORGE_SLUGS,
    LOCAL_DEV_RELATIVE,
    CutoverRootError,
    RootOfRecord,
    forge_slug_for,
    read_cutover_root,
    root_of_record,
)


def _tree(tmp_path: Path, default: str = "local-recipes") -> Path:
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": default,
                        # Story 76.2: a string flag has no ON variant, so its clock stays empty.
                        "metadata": {
                            "owner": "steward",
                            "story": "44-12-cutover-flag-and-replay-harness",
                            "created": "2026-09-13",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_default_is_local_recipes(tmp_path: Path) -> None:
    assert read_cutover_root(_tree(tmp_path)) == DEFAULT_CUTOVER_ROOT


def test_foundry_variant(tmp_path: Path) -> None:
    assert read_cutover_root(_tree(tmp_path, "foundry")) == "foundry"


def test_unknown_variant_fails(tmp_path: Path) -> None:
    path = _tree(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["flags"]["pyforge.cutover_root"]["defaultVariant"] = "other"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unknown"):
        read_cutover_root(path)


def test_missing_flag_fails(tmp_path: Path) -> None:
    path = tmp_path / "flags.json"
    path.write_text(json.dumps({"flags": {}}), encoding="utf-8")
    with pytest.raises(CutoverRootError, match="missing"):
        read_cutover_root(path)


# --- Story 76.1: the reader composes the sibling overlay for the environment ----


def _overlay(tmp_path: Path, document: object) -> None:
    (tmp_path / "flag-overlays.json").write_text(json.dumps(document), encoding="utf-8")


def test_the_sibling_overlay_is_composed_for_the_current_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = _tree(tmp_path, "local-recipes")
    _overlay(
        tmp_path,
        {
            "dev": {"pyforge.cutover_root": "local-recipes"},
            "staging": {"pyforge.cutover_root": "foundry"},
            "production": {"pyforge.cutover_root": "local-recipes"},
        },
    )
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    assert read_cutover_root(tree) == "local-recipes"  # unset reads as dev
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert read_cutover_root(tree) == "foundry"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert read_cutover_root(tree) == "local-recipes"


def test_the_composed_reading_agrees_with_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.core import flags

    tree = _tree(tmp_path, "local-recipes")
    _overlay(tmp_path, {"production": {"pyforge.cutover_root": "foundry"}})
    for environment in flags.ENVIRONMENTS:
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        rendered = json.loads(flags.render(environment, flags_path=tree))
        assert read_cutover_root(tree) == rendered["flags"]["pyforge.cutover_root"]["defaultVariant"]


def test_a_tree_without_a_sibling_overlay_reads_as_it_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, "foundry")
    for environment in ("dev", "staging", "production"):
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        assert read_cutover_root(tree) == "foundry"


def test_an_unknown_environment_is_a_named_cutover_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "qa")
    with pytest.raises(CutoverRootError, match="qa"):
        read_cutover_root(_tree(tmp_path))


@pytest.mark.parametrize(
    "document",
    [
        {"production": {"pyforge.nope": "foundry"}},
        {"production": {"pyforge.cutover_root": "maybe"}},
        {"production": {"pyforge.cutover_root": {"variants": {}}}},
        {"qa": {"pyforge.cutover_root": "foundry"}},
        [],
    ],
)
def test_a_bad_overlay_is_a_named_cutover_error(tmp_path: Path, document: object) -> None:
    tree = _tree(tmp_path)
    _overlay(tmp_path, document)
    with pytest.raises(CutoverRootError):
        read_cutover_root(tree)


# --- Story 117.2 (spec-pyforge-core CAP-13): one function answers the root of record and the forge slug ----


def _out_of_reach(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No tree in reach: no PYFORGE_FLAGS_PATH and a working directory whose walk-up finds no
    flags.json (the filesystem root, so a TMPDIR inside a checkout cannot put one in reach)."""
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path.anchor)
    assert not (Path(tmp_path.anchor) / LOCAL_DEV_RELATIVE).is_file()


def test_root_of_record_on_a_local_recipes_tree(tmp_path: Path) -> None:
    assert root_of_record(_tree(tmp_path)) == RootOfRecord(
        root="local-recipes", forge_slug="rxm7706/local-recipes", source="flag-tree"
    )


def test_root_of_record_on_a_foundry_tree(tmp_path: Path) -> None:
    assert root_of_record(str(_tree(tmp_path, "foundry"))) == RootOfRecord(
        root="foundry", forge_slug="rxm7706/python-foundry", source="flag-tree"
    )


def test_root_of_record_composes_the_overlay_for_the_current_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = _tree(tmp_path, "local-recipes")
    _overlay(tmp_path, {"staging": {"pyforge.cutover_root": "foundry"}})
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert root_of_record(tree).root == "local-recipes"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert root_of_record(tree) == RootOfRecord("foundry", "rxm7706/python-foundry", "flag-tree")


def test_root_of_record_with_no_tree_in_reach_answers_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _out_of_reach(monkeypatch, tmp_path)
    assert root_of_record() == RootOfRecord(
        root=DEFAULT_CUTOVER_ROOT, forge_slug=FORGE_SLUGS[DEFAULT_CUTOVER_ROOT], source="default"
    )


def test_root_of_record_with_no_path_reads_the_env_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, "foundry")
    _out_of_reach(monkeypatch, tmp_path)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert root_of_record() == RootOfRecord("foundry", "rxm7706/python-foundry", "flag-tree")


def test_root_of_record_with_no_path_walks_up_to_the_checkout_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "checkout"
    config = checkout / LOCAL_DEV_RELATIVE.parent
    config.mkdir(parents=True)
    _tree(config, "foundry")
    deep = checkout / "src" / "deep"
    deep.mkdir(parents=True)
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(deep)
    assert root_of_record() == RootOfRecord("foundry", "rxm7706/python-foundry", "flag-tree")


@pytest.mark.parametrize("name", ["no-such.json", "."])
def test_root_of_record_refuses_an_explicit_path_that_is_not_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    # A mistyped path never answers the default, nor the tree PYFORGE_FLAGS_PATH names.
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_tree(tmp_path)))
    with pytest.raises(CutoverRootError, match="no flag tree"):
        root_of_record(tmp_path / name)


def test_root_of_record_refuses_a_malformed_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "flags.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unreadable"):
        root_of_record(path)
    _out_of_reach(monkeypatch, tmp_path)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    with pytest.raises(CutoverRootError, match="unreadable"):
        root_of_record()


def test_root_of_record_refuses_an_unknown_variant(tmp_path: Path) -> None:
    path = _tree(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["flags"]["pyforge.cutover_root"]["defaultVariant"] = "other"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unknown"):
        root_of_record(path)


@pytest.mark.parametrize(
    ("root", "slug"),
    [("local-recipes", "rxm7706/local-recipes"), ("foundry", "rxm7706/python-foundry")],
)
def test_forge_slug_for_each_root(root: str, slug: str) -> None:
    assert forge_slug_for(root) == slug


@pytest.mark.parametrize("root", ["other", "", "Foundry", "rxm7706/local-recipes"])
def test_forge_slug_for_an_unknown_root_fails(root: str) -> None:
    with pytest.raises(CutoverRootError, match="unknown root"):
        forge_slug_for(root)


def test_forge_slugs_keys_equal_the_cutover_variants() -> None:
    assert tuple(FORGE_SLUGS) == CUTOVER_VARIANTS


def test_forge_slugs_and_the_root_of_record_are_read_only(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        FORGE_SLUGS["foundry"] = "someone/else"  # type: ignore[index]
    answer = root_of_record(_tree(tmp_path))
    with pytest.raises(AttributeError):
        answer.root = "foundry"  # type: ignore[misc]
