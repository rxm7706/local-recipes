"""``stamps.py``'s write/read round-trip over a derived artifact's
``<artifact-path>.stamp.json`` sidecar (Story 23.3).

Every case runs against a real, throwaway git repo under ``tmp_path``
(mirrors ``test_deck_pipeline.py``'s own ``_init_git_repo`` helper) --
``stamps.py`` shells real ``git`` commands to determine the tree ref, so a
synthetic non-git ``tmp_path`` is exactly the "not a git repository"
failure mode one of these tests pins deliberately.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.herald import deck_pipeline, stamps, state
from pyforge.herald.errors import HeraldError
from pyforge.herald.stamps import Stamp, read_stamp, write_stamp


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("scratch repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def _head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_write_stamp_then_read_stamp_round_trips(tmp_path: Path):
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")
    stamp = read_stamp(artifact)

    assert isinstance(stamp, Stamp)
    assert stamp.tree == _head_sha(tmp_path)
    assert stamp.etag is None
    assert stamp.derived_at  # non-empty ISO-8601 timestamp


def test_stamp_path_appends_stamp_json_to_the_full_filename(tmp_path: Path):
    """``<artifact-path>.stamp.json`` -- appended to the whole filename, not
    a suffix swap (``foo.pptx`` -> ``foo.pptx.stamp.json``, never
    ``foo.stamp.json``)."""
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    assert (tmp_path / "out.pptx.stamp.json").is_file()


def test_etag_is_none_when_the_deck_was_never_seeded(tmp_path: Path):
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    assert read_stamp(artifact).etag is None


def test_etag_is_the_deck_s_current_registered_prototype_etag(tmp_path: Path):
    _init_git_repo(tmp_path)
    state.write(
        tmp_path / state.DEFAULT_STATE_PATH,
        "pyforge-demo",
        state.DeckState(project_id="p-1", etags={"prototype": "E9"}, last_pull=None),
    )
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    assert read_stamp(artifact).etag == "E9"


def test_tree_has_no_dirty_suffix_when_only_untracked_files_exist(tmp_path: Path):
    """``git status --porcelain --untracked-files=no`` excludes untracked
    files -- mirrors ``deck_facts.py::head_info``'s own convention."""
    _init_git_repo(tmp_path)
    (tmp_path / "untracked.txt").write_text("u", encoding="utf-8")
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    assert read_stamp(artifact).tree == _head_sha(tmp_path)


def test_tree_gets_a_dirty_suffix_when_a_tracked_file_is_uncommitted(tmp_path: Path):
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("changed\n", encoding="utf-8")
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    assert read_stamp(artifact).tree == f"{_head_sha(tmp_path)}-dirty"


def test_read_stamp_of_a_missing_sidecar_returns_none(tmp_path: Path):
    assert read_stamp(tmp_path / "never-derived.pptx") is None


def test_write_stamp_against_a_non_git_directory_raises_herald_error(tmp_path: Path):
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    with pytest.raises(HeraldError, match="git"):
        write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")
    assert not (tmp_path / "out.pptx.stamp.json").exists()


def test_write_stamp_propagates_a_corrupt_state_file_as_herald_error(tmp_path: Path):
    _init_git_repo(tmp_path)
    state_path = tmp_path / state.DEFAULT_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("not json", encoding="utf-8")
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    with pytest.raises(HeraldError):
        write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")


def test_read_stamp_of_non_json_sidecar_raises_herald_error(tmp_path: Path):
    artifact = tmp_path / "out.pptx"
    (tmp_path / "out.pptx.stamp.json").write_text("not json", encoding="utf-8")

    with pytest.raises(HeraldError, match="not valid JSON"):
        read_stamp(artifact)


def test_read_stamp_of_a_non_object_json_sidecar_raises_herald_error(tmp_path: Path):
    artifact = tmp_path / "out.pptx"
    (tmp_path / "out.pptx.stamp.json").write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(HeraldError, match="JSON object"):
        read_stamp(artifact)


def test_read_stamp_of_a_sidecar_missing_a_field_raises_herald_error(tmp_path: Path):
    artifact = tmp_path / "out.pptx"
    (tmp_path / "out.pptx.stamp.json").write_text('{"tree": "abc"}', encoding="utf-8")

    with pytest.raises(HeraldError, match="missing field"):
        read_stamp(artifact)


def test_read_stamp_of_a_sidecar_with_an_unknown_field_raises_herald_error(
    tmp_path: Path,
):
    """Mirrors ``state.py``'s own unknown-field discipline: an unrecognized
    field is corruption to flag, not to silently ignore (a rename of one
    of the three known fields without updating ``read_stamp`` would
    otherwise pass every value straight through as "unknown", never
    surfacing as a bug)."""
    artifact = tmp_path / "out.pptx"
    (tmp_path / "out.pptx.stamp.json").write_text(
        '{"tree": "abc", "etag": null, "derived_at": "2026-01-01T00:00:00+00:00", "extra": "surprise"}',
        encoding="utf-8",
    )

    with pytest.raises(HeraldError, match="unknown field"):
        read_stamp(artifact)


def test_write_stamp_wraps_a_failed_replace_as_herald_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    def _refuse(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("pyforge.core.atomic_write.os.replace", _refuse)
    with pytest.raises(HeraldError, match="disk full"):
        write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")


def test_read_stamp_wraps_an_unreadable_sidecar_as_herald_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    artifact = tmp_path / "out.pptx"
    (tmp_path / "out.pptx.stamp.json").write_text("{}", encoding="utf-8")

    def _refuse(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", _refuse)
    with pytest.raises(HeraldError, match="could not be read"):
        read_stamp(artifact)


def test_write_stamp_writes_atomically_leaving_no_temp_file(tmp_path: Path):
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")

    leftovers = [
        p.name for p in tmp_path.iterdir() if p.name not in {"README.md", "out.pptx", "out.pptx.stamp.json", ".git"}
    ]
    assert leftovers == []


def test_prototype_artifact_key_mirrors_deck_pipelines_constant():
    """``stamps._PROTOTYPE_ARTIFACT_KEY`` is a second, independently
    hardcoded copy of ``deck_pipeline.PROTOTYPE_ARTIFACT_KEY`` (duplicated
    rather than imported, to avoid a cycle -- see the module docstring). A
    future rename of one without the other would make ``_current_etag``
    silently look up the wrong key and every future stamp would record
    ``etag: null`` with no failing test to catch it."""
    assert stamps._PROTOTYPE_ARTIFACT_KEY == deck_pipeline.PROTOTYPE_ARTIFACT_KEY


def test_write_stamp_wraps_a_hung_git_call_as_herald_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """``_git`` must not block forever on lock contention or a
    network-mounted ``.git`` -- mirrors the bounded-subprocess pattern
    ``deck_pipeline._PixiPartialDeckExporter`` already applies to its own
    subprocess call."""
    _init_git_repo(tmp_path)
    artifact = tmp_path / "out.pptx"
    artifact.write_bytes(b"binary")

    def _hang(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", _hang)
    with pytest.raises(HeraldError, match="exceeded"):
        write_stamp(artifact, repo_root=tmp_path, slug="pyforge-demo")
