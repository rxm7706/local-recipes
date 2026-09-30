"""Story 44.12 — plan preserve-moved, apply idempotent, flip refuses loops."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.cutover_root import CutoverRootError, read_cutover_root

from pyforge.steward.cutover import (
    DEFAULT_MANIFEST,
    ENV_FOUNDRY,
    FOUNDRY_EPOCH,
    REALIZATION_LOG,
    CutoverDuty,
    apply_phase,
    flip_root,
    loops_running,
    plan_append,
    plan_regenerate,
)
from pyforge.steward.interfaces import DutyResult


def _git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    pkg = root / "src/shared/packages/demo"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)
    return root


def test_regenerate_preserves_moved(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    first = plan_regenerate(root, manifest)
    assert first["rows"]
    first["rows"][0]["status"] = "moved"
    manifest.write_text(json.dumps(first), encoding="utf-8")
    second = plan_regenerate(root, manifest)
    moved = [r for r in second["rows"] if r["status"] == "moved"]
    assert moved
    assert moved[0]["path"] == first["rows"][0]["path"]


def test_append_preserves_moved(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    first = plan_regenerate(root, manifest)
    first["rows"][0]["status"] = "moved"
    manifest.write_text(json.dumps(first), encoding="utf-8")
    extra = root / "src/shared/packages/demo/extra.txt"
    extra.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "delta"], cwd=root, check=True, capture_output=True)
    second = plan_append(root, manifest)
    by_path = {r["path"]: r for r in second["rows"]}
    assert by_path[first["rows"][0]["path"]]["status"] == "moved"
    assert "src/shared/packages/demo/extra.txt" in by_path


def test_apply_is_idempotent(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    dest = tmp_path / "foundry"
    plan_regenerate(root, manifest)
    once = apply_phase(root, manifest, "1a", dest)
    twice = apply_phase(root, manifest, "1a", dest)
    assert once["copied"] >= 1
    assert twice["copied"] == 0
    assert twice["skipped"] >= 1
    copied = dest / "src/packages/demo/pyproject.toml"
    assert copied.is_file()


def test_flip_refused_while_loop_running(tmp_path: Path) -> None:
    flags = tmp_path / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": "local-recipes",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    loops = tmp_path / "loops" / "x"
    loops.mkdir(parents=True)
    (loops / "state.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
    realization = tmp_path / "dream.md"
    realization.write_text("## Realization log\n", encoding="utf-8")
    assert loops_running(tmp_path / "loops")
    with pytest.raises(CutoverRootError, match="loop is running"):
        flip_root(flags, "foundry", realization, loop_home=tmp_path / "loops")
    assert read_cutover_root(flags) == "local-recipes"


# --- Story 76.1: a flip is not masked by the per-environment overlay -------------


def _flag_tree(directory: Path, overlays: object | None = None) -> Path:
    flags = directory / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
                        "defaultVariant": "local-recipes",
                    },
                    "pyforge.other": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    if overlays is not None:
        (directory / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    return flags


_PINNED = {
    "dev": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "off"},
    "staging": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "on"},
    "production": {"pyforge.cutover_root": "local-recipes"},
}


def test_the_reader_sees_the_overlay_pinned_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flags = _flag_tree(tmp_path, {**_PINNED, "staging": {"pyforge.cutover_root": "foundry"}})
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert read_cutover_root(flags) == "foundry"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert read_cutover_root(flags) == "local-recipes"


@pytest.mark.parametrize("target", ["foundry", "local-recipes"])
def test_flip_then_read_agree_in_every_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    from pyforge.core import flags as core_flags

    flags = _flag_tree(tmp_path, _PINNED)
    other = "foundry" if target == "local-recipes" else "local-recipes"
    flip_root(flags, other, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    flip_root(flags, target, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    for environment in core_flags.ENVIRONMENTS:
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        assert read_cutover_root(flags) == target, environment
        rendered = json.loads(core_flags.render(environment, flags_path=flags))
        assert rendered["flags"]["pyforge.cutover_root"]["defaultVariant"] == target, environment


def test_flip_touches_only_the_cutover_key_of_the_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path, _PINNED)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {
        "dev": {"pyforge.cutover_root": "foundry", "pyforge.other": "off"},
        "staging": {"pyforge.cutover_root": "foundry", "pyforge.other": "on"},
        "production": {"pyforge.cutover_root": "foundry"},
    }
    assert json.loads(flags.read_text(encoding="utf-8"))["flags"]["pyforge.cutover_root"]["defaultVariant"] == "foundry"


def test_flip_leaves_an_environment_that_does_not_name_the_flag_alone(tmp_path: Path) -> None:
    flags = _flag_tree(
        tmp_path, {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "local-recipes"}}
    )
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "foundry"}}


def test_flip_without_a_sibling_overlay_writes_no_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert not (tmp_path / "flag-overlays.json").exists()
    assert read_cutover_root(flags) == "foundry"


def test_flip_refuses_a_broken_overlay_before_writing_anything(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    (tmp_path / "flag-overlays.json").write_text("{not json", encoding="utf-8")
    before = flags.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused"):
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert flags.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("overlays", "named"),
    [
        ({"dev": {"pyforge.typo": "off"}}, "pyforge.typo"),
        ({"dev": {"pyforge.other": "maybe"}}, "maybe"),
        ({"qa": {"pyforge.other": "on"}}, "qa"),
        ({"dev": {"pyforge.other": {"variants": {}}}}, "pyforge.other"),
    ],
)
def test_flip_refuses_an_invalid_overlay_entry_before_writing_anything(
    tmp_path: Path, overlays: object, named: str
) -> None:
    flags = _flag_tree(tmp_path, overlays)
    overlays_path = tmp_path / "flag-overlays.json"
    tree_before = flags.read_text(encoding="utf-8")
    overlays_before = overlays_path.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused") as excinfo:
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert named in str(excinfo.value)
    assert flags.read_text(encoding="utf-8") == tree_before
    assert overlays_path.read_text(encoding="utf-8") == overlays_before


# --- plan / apply / flip edges and the duty's verbs (coverage floor for Story 76.1) -------------

# Tracked beside the seed's src/shared/packages/demo/pyproject.toml; the last two fall outside
# every apply phase (conda-forge-expert stays on A; a root README is in no Launch tree).
_MIXED = {
    "docs/dreams/demo.md": "# demo\n",
    "docs/dreams/.env": "TOKEN=x\n",
    "presentations/deck/cert.pem": "-----BEGIN-----\n",
    ".claude/skills/conda-forge-expert/SKILL.md": "# cfe\n",
    "README.md": "# root\n",
}
_IN_SCOPE = {
    "src/shared/packages/demo/pyproject.toml",
    "docs/dreams/demo.md",
    "docs/dreams/.env",
    "presentations/deck/cert.pem",
}


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True)


def _head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _mixed_repo(tmp_path: Path) -> Path:
    root = _git_repo(tmp_path)
    for rel, text in _MIXED.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    # -f: a global excludes file may ignore .env / *.pem; the tree under test must track them.
    subprocess.run(["git", "add", "-f", "--", *_MIXED], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "mixed"], cwd=root, check=True, capture_output=True)
    return root


def _rows_by_path(manifest: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads(manifest.read_text(encoding="utf-8"))["rows"]
    return {str(row["path"]): row for row in rows if isinstance(row, dict)}


def test_regenerate_routes_each_path_by_phase_and_leaves_the_rest_out(tmp_path: Path) -> None:
    root = _mixed_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    payload = plan_regenerate(root, manifest)
    by_path = {row["path"]: row for row in payload["rows"]}
    assert set(by_path) == _IN_SCOPE
    assert by_path["src/shared/packages/demo/pyproject.toml"] == {
        "path": "src/shared/packages/demo/pyproject.toml",
        "dest": "src/packages/demo/pyproject.toml",
        "status": "planned",
        "kind": "file",
        "phase": "1a",
    }
    assert by_path["docs/dreams/demo.md"] == {
        "path": "docs/dreams/demo.md",
        "dest": "docs/dreams/demo.md",
        "status": "planned",
        "kind": "file",
        "phase": "1b",
    }
    assert by_path["docs/dreams/.env"]["kind"] == "secret"
    assert by_path["presentations/deck/cert.pem"]["kind"] == "secret"
    assert payload["source_sha"] == _head(root)
    assert payload["foundry_epoch"] == FOUNDRY_EPOCH
    assert json.loads(manifest.read_text(encoding="utf-8")) == payload


def test_regenerate_keeps_a_moved_row_whose_file_left_the_tree(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    gone = {
        "path": "src/shared/packages/gone/mod.py",
        "dest": "src/packages/gone/mod.py",
        "status": "moved",
        "kind": "file",
        "phase": "1a",
    }
    planned = {"path": "src/shared/packages/demo/pyproject.toml", "status": "planned"}
    manifest.write_text(json.dumps({"source_sha": "", "rows": ["junk", planned, gone]}), encoding="utf-8")
    payload = plan_regenerate(root, manifest)
    assert [row["path"] for row in payload["rows"]] == [
        "src/shared/packages/demo/pyproject.toml",
        "src/shared/packages/gone/mod.py",
    ]
    assert payload["rows"][0]["status"] == "planned"
    assert payload["rows"][0]["dest"] == "src/packages/demo/pyproject.toml"
    assert payload["rows"][1] == gone


@pytest.mark.parametrize("plan", [plan_regenerate, plan_append])
def test_a_manifest_that_is_not_an_object_plans_from_scratch(
    tmp_path: Path, plan: Callable[[Path, Path], dict[str, Any]]
) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]", encoding="utf-8")
    payload = plan(root, manifest)
    assert [row["path"] for row in payload["rows"]] == ["src/shared/packages/demo/pyproject.toml"]
    assert payload["source_sha"] == _head(root)
    assert payload["foundry_epoch"] == FOUNDRY_EPOCH


def test_append_without_a_manifest_plans_every_in_scope_tracked_file(tmp_path: Path) -> None:
    root = _mixed_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    payload = plan_append(root, manifest)
    assert {row["path"] for row in payload["rows"]} == _IN_SCOPE
    assert all(row["status"] == "planned" for row in payload["rows"])
    assert payload["source_sha"] == _head(root)


def test_append_survives_a_source_sha_git_no_longer_knows(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_sha": "0" * 40, "rows": []}), encoding="utf-8")
    payload = plan_append(root, manifest)
    assert [row["path"] for row in payload["rows"]] == ["src/shared/packages/demo/pyproject.toml"]
    assert payload["source_sha"] == _head(root)


def test_append_plans_a_path_only_the_delta_still_names(tmp_path: Path) -> None:
    root = _mixed_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_sha": _head(root), "rows": []}), encoding="utf-8")
    (root / "docs/dreams/demo.md").unlink()
    _commit(root, "drop the dream")
    payload = plan_append(root, manifest)
    assert {row["path"] for row in payload["rows"]} == _IN_SCOPE


def test_append_leaves_an_already_planned_row_as_it_found_it(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    first = plan_regenerate(root, manifest)
    first["rows"][0]["dest"] = "hand/edited.toml"
    manifest.write_text(json.dumps(first), encoding="utf-8")
    second = plan_append(root, manifest)
    assert second["rows"] == first["rows"]


def test_apply_replays_only_its_phase_and_passes_over_absent_sources(tmp_path: Path) -> None:
    root = _mixed_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    payload = plan_regenerate(root, manifest)
    absent = {
        "path": "src/shared/packages/demo/absent.py",
        "dest": "src/packages/demo/absent.py",
        "status": "planned",
        "kind": "file",
        "phase": "1a",
    }
    payload["rows"].extend(["junk", absent])
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    dest = tmp_path / "foundry"

    assert apply_phase(root, manifest, "1a", dest) == {"copied": 1, "skipped": 0, "phase": "1a"}
    rows = _rows_by_path(manifest)
    assert rows["src/shared/packages/demo/pyproject.toml"]["status"] == "moved"
    assert rows["src/shared/packages/demo/absent.py"]["status"] == "planned"
    assert rows["docs/dreams/demo.md"]["status"] == "planned"
    assert not (dest / "src/packages/demo/absent.py").exists()
    assert not (dest / "docs").exists()

    assert apply_phase(root, manifest, "1b", dest) == {"copied": 3, "skipped": 0, "phase": "1b"}
    assert (dest / "docs/dreams/demo.md").read_text(encoding="utf-8") == "# demo\n"
    assert (dest / "presentations/deck/cert.pem").is_file()
    assert all(row["status"] == "moved" for path, row in _rows_by_path(manifest).items() if path in _IN_SCOPE)


def test_loops_running_reads_past_unreadable_and_idle_state(tmp_path: Path) -> None:
    home = tmp_path / "loops"
    for run, text in {"a": "{not json", "b": json.dumps({"status": "done"}), "c": json.dumps({})}.items():
        (home / run).mkdir(parents=True)
        (home / run / "state.json").write_text(text, encoding="utf-8")
    assert loops_running(home) is False
    (home / "d").mkdir()
    (home / "d" / "state.json").write_text(json.dumps({"state": "Active"}), encoding="utf-8")
    assert loops_running(home) is True


def test_loops_running_without_a_loop_home_is_false(tmp_path: Path) -> None:
    assert loops_running(tmp_path / "absent") is False


def test_flip_refuses_an_unknown_variant_before_touching_the_tree(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    before = flags.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unknown cutover_root variant 'elsewhere'"):
        flip_root(flags, "elsewhere", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert flags.read_text(encoding="utf-8") == before


def test_flip_stamps_the_realization_log_when_it_exists(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    realization = tmp_path / "dream.md"
    realization.write_text("## Realization log\n", encoding="utf-8")
    flip_root(flags, "foundry", realization, loop_home=tmp_path / "loops")
    text = realization.read_text(encoding="utf-8")
    assert text.startswith("## Realization log\n")
    assert text.endswith("`pyforge.cutover_root` → `foundry`\n")


@pytest.fixture
def duty_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tracked tree as the duty's cwd, with HOME and every env override pinned inside tmp_path."""
    root = _mixed_repo(tmp_path).resolve()
    monkeypatch.chdir(root)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for name in (ENV_FOUNDRY, "PYFORGE_FLAGS_PATH", "PYFORGE_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    return root


def _run(**kwargs: object) -> DutyResult:
    return CutoverDuty().run(argparse.Namespace(**kwargs))


def test_duty_without_a_verb_names_the_three_verbs(duty_repo: Path) -> None:
    result = _run()
    assert result.ok is False
    assert result.summary == "cutover: need plan, apply, or flip"


def test_duty_plan_needs_a_mode(duty_repo: Path) -> None:
    result = _run(cutover_verb="plan", regenerate=False, append=False, manifest=None)
    assert result.ok is False
    assert result.summary == "cutover plan: pass --regenerate or --append"
    assert not (duty_repo / DEFAULT_MANIFEST).exists()


def test_duty_plan_regenerate_finds_the_repo_root_from_a_subdirectory(
    duty_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(duty_repo / "docs/dreams")
    result = _run(cutover_verb="plan", regenerate=True, append=False, manifest=None)
    manifest = duty_repo / DEFAULT_MANIFEST
    assert result.ok is True
    assert result.summary == f"cutover plan --regenerate: 4 rows → {manifest}"
    assert result.details == {"rows": 4, "path": str(manifest)}
    assert set(_rows_by_path(manifest)) == _IN_SCOPE


def test_duty_plan_append_honours_an_explicit_manifest(duty_repo: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "elsewhere.json"
    result = _run(cutover_verb="plan", regenerate=False, append=True, manifest=str(manifest))
    assert result.ok is True
    assert result.details == {"rows": 4, "path": str(manifest)}
    assert not (duty_repo / DEFAULT_MANIFEST).exists()


def test_duty_plan_on_a_malformed_manifest_is_a_failed_result_not_a_raise(duty_repo: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "bad.json"
    manifest.write_text("{not json", encoding="utf-8")
    result = _run(cutover_verb="plan", regenerate=False, append=True, manifest=str(manifest))
    assert result.ok is False
    assert result.summary.startswith("cutover: ")


@pytest.mark.parametrize("phase", [None, "", "2"])
def test_duty_apply_refuses_an_unknown_phase(duty_repo: Path, phase: str | None) -> None:
    result = _run(cutover_verb="apply", phase=phase, manifest=None, foundry_root=None)
    assert result.ok is False
    assert result.summary == "cutover apply: --phase must be 1a or 1b"


def test_duty_apply_copies_into_an_explicit_foundry_root(duty_repo: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "m.json"
    plan_regenerate(duty_repo, manifest)
    dest = tmp_path / "explicit"
    result = _run(cutover_verb="apply", phase="1a", manifest=str(manifest), foundry_root=str(dest))
    assert result.ok is True
    assert result.summary == "cutover apply --phase 1a: copied 1, skipped 0"
    assert result.details == {"copied": 1, "skipped": 0, "phase": "1a"}
    assert (dest / "src/packages/demo/pyproject.toml").is_file()


def test_duty_apply_reads_the_foundry_root_from_the_environment(
    duty_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "m.json"
    plan_regenerate(duty_repo, manifest)
    dest = tmp_path / "from-env"
    monkeypatch.setenv(ENV_FOUNDRY, str(dest))
    result = _run(cutover_verb="apply", phase="1b", manifest=str(manifest), foundry_root=None)
    assert result.ok is True
    assert result.details == {"copied": 3, "skipped": 0, "phase": "1b"}
    assert (dest / "docs/dreams/demo.md").is_file()


def test_duty_apply_defaults_to_the_sibling_python_foundry_checkout(duty_repo: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "m.json"
    plan_regenerate(duty_repo, manifest)
    result = _run(cutover_verb="apply", phase="1a", manifest=str(manifest))
    assert result.ok is True
    assert (duty_repo.parent / "python-foundry/src/packages/demo/pyproject.toml").is_file()


@pytest.mark.parametrize("flags", [None, "missing.json"])
def test_duty_flip_without_a_flag_tree_says_so(duty_repo: Path, tmp_path: Path, flags: str | None) -> None:
    explicit = str(tmp_path / flags) if flags else None
    result = _run(cutover_verb="flip", to="foundry", flags=explicit)
    assert result.ok is False
    assert result.summary == "cutover flip: no flags.json"


def test_duty_flip_sets_the_root_and_stamps_the_realization_log(duty_repo: Path, tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    log = duty_repo / REALIZATION_LOG
    log.write_text("## Realization log\n", encoding="utf-8")
    result = _run(cutover_verb="flip", to="foundry", flags=str(flags))
    assert result.ok is True
    assert result.summary == "cutover flip → foundry"
    assert read_cutover_root(flags) == "foundry"
    assert log.read_text(encoding="utf-8").endswith("`pyforge.cutover_root` → `foundry`\n")


def test_duty_flip_refused_by_a_running_loop_is_a_failed_result(duty_repo: Path, tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    state = tmp_path / "home/.bmad-loops/run-1/state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"status": "running"}), encoding="utf-8")
    before = flags.read_text(encoding="utf-8")
    result = _run(cutover_verb="flip", to="foundry", flags=str(flags))
    assert result.ok is False
    assert result.summary == "cutover: flip refused: a Marshal loop is running"
    assert flags.read_text(encoding="utf-8") == before
