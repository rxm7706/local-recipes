"""``scripts/fleet_scan.py`` reads archived Dreams from ``archive/docs/dreams/`` (marshal Story 75.1).

``spec-one-chain-per-station`` CAP-11 / CHAIN-STANDARD §11: a Dream is live in ``docs/dreams/``
or archived under ``archive/docs/dreams/``. ``scan_dreams()`` and ``_fleet_chains()`` read both,
``docs/dreams/`` first, one row per slug, and a Dream read from the archive is reported
``archived`` whatever its frontmatter says (operator ruling 2026-09-30).

The real script is loaded the way the doctor tests load it
(``pyforge.doctor.sources.board._load_foreign_module``: ``spec_from_file_location`` +
``exec_module``, registered in ``sys.modules``). The load is inlined because
``pyforge-doctor-scripts-test`` runs this directory in the ``pyforge-ci`` env, where
``pyforge.doctor`` is not importable. Fixture trees are built the way
``test_sources_board_chain_layers_audit._install_generate`` builds them.
"""

from __future__ import annotations

import importlib.util
import itertools
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN = _REPO_ROOT / "scripts" / "fleet_scan.py"
_ROSTER = _REPO_ROOT / "docs" / "governance" / "guild-roster.json"

pytestmark = pytest.mark.skipif(
    not (_SCAN.is_file() and _ROSTER.is_file()),
    reason="scripts/fleet_scan.py + docs/governance/guild-roster.json required",
)

# The six Dreams already under archive/docs/dreams/ when Story 75.1 landed (criterion 1).
_ARCHIVED_AT_75_1 = {
    "deckcraft",
    "design-code-bridge",
    "herald-pitch-deck-family-expansion",
    "modernist-identity",
    "pyforge-genesis",
    "video-scripts",
}
_ROW_KEYS = ("slug", "title", "status", "owner", "archived_reason")
# The one line that makes _dream_files() read the archive; the mutation test removes it.
_ARCHIVE_READ = "((DREAMS_DIR, False), (ARCHIVE_DREAMS_DIR, True))"
_LIVE_ONLY = "((DREAMS_DIR, False),)"
_NAMES = itertools.count()


def _load(path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load ``path`` as a fresh module, undone at test teardown."""
    name = f"_fleet_scan_archive_{next(_NAMES)}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The script prepends its own scripts/ dir to sys.path at import time.
    monkeypatch.setattr(sys, "path", list(sys.path))
    # Its dataclass annotations resolve through sys.modules.
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _install(target: Path, *, source: str | None = None) -> Path:
    """A minimal checkout ``_discover_repo_root()`` resolves to; returns the script path."""
    (target / "scripts").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "dreams").mkdir(parents=True, exist_ok=True)
    (target / "pixi.toml").write_text('[workspace]\nname = "fixture"\n', encoding="utf-8")
    script = target / "scripts" / "fleet_scan.py"
    if source is None:
        shutil.copy(_SCAN, script)
    else:
        script.write_text(source, encoding="utf-8")
    shutil.copy(_ROSTER, target / "docs" / "governance" / "guild-roster.json")
    return script


def _live_only_source() -> str:
    """fleet_scan.py with the archive read removed (the mutation)."""
    source = _SCAN.read_text(encoding="utf-8")
    assert source.count(_ARCHIVE_READ) == 1, "the archive read moved; update the mutation"
    return source.replace(_ARCHIVE_READ, _LIVE_ONLY)


def _dream(
    path: Path,
    *,
    title: str,
    owner: str,
    status: str,
    reason: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"title: {title}", "type: dream", f"owner: {owner}", f"status: {status}"]
    if reason:
        lines.append(f"archived-reason: {reason}")
    lines += ["---", "", f"# {title}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _spec(target: Path, project: str, slug: str, owner_dream: str) -> None:
    folder = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs"
    folder = folder / f"spec-{slug}"
    folder.mkdir(parents=True)
    (folder / "SPEC.md").write_text(
        f"---\ntitle: {slug}\nstatus: shipped\nowner-dream: {owner_dream}\n---\n",
        encoding="utf-8",
    )


def _row(fs: ModuleType, slug: str) -> dict:
    rows = [d for d in fs.scan_dreams() if d["slug"] == slug]
    assert len(rows) == 1, f"expected one {slug!r} row, got {rows}"
    return rows[0]


def _chain(fs: ModuleType, slug: str) -> tuple:
    chains = [c for c in fs._fleet_chains() if c[0] == slug]
    assert len(chains) == 1, f"expected one {slug!r} chain, got {chains}"
    return chains[0]


def _assert_moved_dream_keeps_its_row(fs: ModuleType, target: Path) -> None:
    """Criterion 2: an archived Dream moved docs/dreams -> archive/docs/dreams keeps its row."""
    live = target / "docs" / "dreams" / "old-idea.md"
    _dream(live, title="An old idea", owner="marshal", status="archived", reason="absorbed")
    before = _row(fs, "old-idea")
    moved = target / "archive" / "docs" / "dreams" / "old-idea.md"
    moved.parent.mkdir(parents=True, exist_ok=True)
    live.rename(moved)
    after = _row(fs, "old-idea")
    assert {k: after.get(k) for k in _ROW_KEYS} == {k: before.get(k) for k in _ROW_KEYS}
    assert after["archived_reason"] == "absorbed"
    assert set(after) == set(before)  # the row shape does not change


def test_todays_tree_keeps_every_live_row_and_adds_the_archive_as_archived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 1: docs/dreams rows unchanged; the archive's Dreams added, as archived."""
    fs = _load(_SCAN, monkeypatch)
    assert fs.ARCHIVE_DREAMS_DIR == _REPO_ROOT / "archive" / "docs" / "dreams"
    live_stems = {f.stem for f in (_REPO_ROOT / "docs" / "dreams").glob("*.md")}
    # _dream_files() order: sorted by path, not by stem (`foo.md` vs `foo-bar.md` differ).
    archive_only = [
        f.stem
        for f in sorted(fs.ARCHIVE_DREAMS_DIR.glob("*.md"))
        if f.name != "README.md" and f.stem not in live_stems
    ]
    assert _ARCHIVED_AT_75_1 <= set(archive_only)
    stems = set(archive_only)

    dreams, chains = fs.scan_dreams(), fs._fleet_chains()
    monkeypatch.setattr(fs, "ARCHIVE_DREAMS_DIR", tmp_path / "no-archive")
    live_dreams, live_chains = fs.scan_dreams(), fs._fleet_chains()

    assert dreams[: len(live_dreams)] == live_dreams
    added = dreams[len(live_dreams) :]
    assert [d["slug"] for d in added] == archive_only
    assert all(d["status"] == "archived" for d in added)

    # A chain named for an archive Dream, or whose `owner-dream:` (c[4]) points at one,
    # reads differently once the archive is read; every other chain is unchanged.
    def untouched(cs: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
        return [c for c in cs if c[0] not in stems and c[4] not in stems]

    assert untouched(chains) == untouched(live_chains)
    new_chains = [c for c in chains if c[0] in stems]
    assert sorted(c[0] for c in new_chains) == sorted(archive_only)
    assert all(c[3] == "archived" for c in new_chains)


def test_a_moved_archived_dream_keeps_its_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fs = _load(_install(tmp_path), monkeypatch)
    _assert_moved_dream_keeps_its_row(fs, tmp_path)


def test_an_archive_dream_reads_archived_whatever_its_frontmatter_says(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fs = _load(_install(tmp_path), monkeypatch)
    _dream(
        tmp_path / "archive" / "docs" / "dreams" / "straggler.md",
        title="A straggler",
        owner="herald",
        status="specified",
    )
    assert _row(fs, "straggler")["status"] == "archived"
    assert _chain(fs, "straggler")[1:4] == ("pyforge-herald", "herald", "archived")


def test_a_slug_in_both_places_is_read_from_docs_dreams_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 3."""
    fs = _load(_install(tmp_path), monkeypatch)
    _dream(
        tmp_path / "docs" / "dreams" / "twin.md",
        title="Live copy",
        owner="doctor",
        status="specified",
    )
    _dream(
        tmp_path / "archive" / "docs" / "dreams" / "twin.md",
        title="Archive copy",
        owner="herald",
        status="archived",
        reason="retired",
    )
    row = _row(fs, "twin")
    assert (row["title"], row["status"], row["owner"]) == ("Live copy", "specified", "doctor")
    assert "archived_reason" not in row
    assert _chain(fs, "twin")[2:4] == ("doctor", "specified")


def test_an_absorbed_spec_keeps_its_station_when_owner_dream_points_at_the_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 4: the absorbed Spec, and a sub-chain naming the same parent Dream."""
    fs = _load(_install(tmp_path), monkeypatch)
    live = tmp_path / "docs" / "dreams" / "satellite.md"
    _dream(live, title="A satellite", owner="doctor", status="archived", reason="absorbed")
    _spec(tmp_path, "pyforge-doctor", "satellite", "docs/dreams/satellite.md")
    _spec(tmp_path, "shared-work", "satellite-follow-up", "docs/dreams/satellite.md")
    before = (_chain(fs, "satellite"), _chain(fs, "satellite-follow-up"))
    assert before[0][2] == before[1][2] == "doctor"

    # The fold PR: the Dream moves, and each owner-dream is repointed at the archive path.
    moved = tmp_path / "archive" / "docs" / "dreams" / "satellite.md"
    moved.parent.mkdir(parents=True)
    live.rename(moved)
    for spec_md in tmp_path.glob("_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md"):
        text = spec_md.read_text(encoding="utf-8")
        spec_md.write_text(
            text.replace("docs/dreams/satellite.md", "archive/docs/dreams/satellite.md"),
            encoding="utf-8",
        )
    after = (_chain(fs, "satellite"), _chain(fs, "satellite-follow-up"))
    assert after == before
    assert after[1] == ("satellite-follow-up", "shared-work", "doctor", "", "satellite")


def test_no_archive_directory_scans_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 5: with no archive/docs/dreams/, output matches the live-only scan exactly."""
    results = []
    for name, source in (("current", None), ("live-only", _live_only_source())):
        target = tmp_path / name
        fs = _load(_install(target, source=source), monkeypatch)
        _dream(
            target / "docs" / "dreams" / "alpha.md",
            title="Alpha",
            owner="marshal",
            status="specified",
        )
        _dream(
            target / "docs" / "dreams" / "beta.md",
            title="Beta",
            owner="herald",
            status="archived",
            reason="retired",
        )
        (target / "docs" / "dreams" / "README.md").write_text("# Dreams\n", encoding="utf-8")
        assert not fs.ARCHIVE_DREAMS_DIR.exists()
        capsys.readouterr()
        dreams, chains = fs.scan_dreams(), fs._fleet_chains()
        results.append((dreams, chains, capsys.readouterr().out))
    assert results[0] == results[1]
    assert [d["slug"] for d in results[0][0]] == ["alpha", "beta"]


def test_mutation_removing_the_archive_read_fails_the_moved_dream_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 6: the moved-Dream check is sensitive to the archive read."""
    fs = _load(_install(tmp_path, source=_live_only_source()), monkeypatch)
    with pytest.raises(AssertionError, match="expected one 'old-idea' row"):
        _assert_moved_dream_keeps_its_row(fs, tmp_path)
