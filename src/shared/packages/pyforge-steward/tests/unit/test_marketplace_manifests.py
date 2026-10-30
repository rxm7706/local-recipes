"""Story 109.3 — the two generated marketplace manifests and where they may be written.

Split from ``test_marketplace_pages.py`` by subject (Story 109.8, ``DW-steward-109-3-7``).
"""

from __future__ import annotations

import json
import os
import threading
import types
from pathlib import Path

import pytest
from marketplace_testkit import _flags_tree, _marketplace

import pyforge.steward.marketplace_pages as marketplace_pages
from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    MarketplaceIndexError,
    MarketplacePagesDisabled,
    load_listings,
    render_codex_marketplace,
    render_relative_marketplace,
    render_url_marketplace,
    write_codex_manifest,
    write_plugin_manifest,
    write_plugin_manifests,
)

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads docs/foundry/marketplace and the estate skill
# copies, so it runs in the station's live-tree half and fires on those paths, not on every edit of the package.
pytestmark = pytest.mark.live_tree

_MARKETPLACE = Path("docs/foundry/marketplace")


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag tree is read for ``dev`` (where the flag is on), whatever the shell exports."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


# --- the manifests ------------------------------------------------------------------------------


# Story 109.8 (DW-steward-109-3-7, TEA's M3): the committed-manifest test held four subjects; one each below.
def test_committed_marketplace_json_uses_documented_source_fields() -> None:
    """The relative form names each skill folder, and the committed file is that render."""
    rows = load_listings(repo_root() / _MARKETPLACE / "index.yaml")
    relative = json.loads(render_relative_marketplace(rows))
    assert relative["name"] == "pyforge-bmad-marketplace"
    assert [plugin["source"] for plugin in relative["plugins"]] == [
        "./skills/mason/environment",
        "./skills/mason/package",
        "./skills/warden/scan",
    ]
    committed = repo_root() / _MARKETPLACE / ".claude-plugin" / "marketplace.json"
    assert committed.read_text(encoding="utf-8") == render_relative_marketplace(rows)


def test_the_url_form_uses_git_subdir_plugin_sources() -> None:
    """The Pages URL form downloads only the file, so each plugin is a ``git-subdir`` source with no sparse paths."""
    rows = load_listings(repo_root() / _MARKETPLACE / "index.yaml")
    plugin = json.loads(render_url_marketplace(rows))["plugins"][0]
    assert plugin["source"]["source"] == "git-subdir"
    assert plugin["source"]["url"] == "https://github.com/rxm7706/local-recipes.git"
    assert plugin["source"]["path"] == "docs/foundry/marketplace/skills/mason/environment"
    assert "sparsePaths" not in plugin["source"]


def test_the_plugin_manifest_writer_writes_the_relative_form_while_the_flag_is_on(tmp_path: Path) -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = tmp_path / "marketplace.json"
    write_plugin_manifest(index, dest, flags_path=on)
    assert dest.read_text(encoding="utf-8") == render_relative_marketplace(load_listings(index))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_both_manifest_writers_refuse_while_the_flag_is_off(tmp_path: Path, writer) -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    off = _flags_tree(tmp_path / "off", dev="off")
    with pytest.raises(MarketplacePagesDisabled):
        writer(index, tmp_path / "no.json", flags_path=off)
    assert not (tmp_path / "no.json").exists()


def test_committed_codex_manifest_names_the_three_listings(tmp_path: Path) -> None:
    """Loop 2, row 21: the directory ``codex plugin marketplace add`` names holds a manifest with the skills."""
    index = repo_root() / _MARKETPLACE / "index.yaml"
    rows = load_listings(index)
    committed = repo_root() / _MARKETPLACE / ".agents" / "plugins" / "marketplace.json"
    assert committed.read_text(encoding="utf-8") == render_codex_marketplace(rows)
    document = json.loads(committed.read_text(encoding="utf-8"))
    assert document["name"] == "pyforge-bmad-marketplace"
    assert [plugin["name"] for plugin in document["plugins"]] == ["mason-environment", "mason-package", "warden-scan"]
    assert [plugin["source"] for plugin in document["plugins"]] == [
        {"source": "local", "path": "./skills/mason/environment"},
        {"source": "local", "path": "./skills/mason/package"},
        {"source": "local", "path": "./skills/warden/scan"},
    ]
    on = _flags_tree(tmp_path / "flags", dev="on")
    root = _marketplace(tmp_path)
    written = write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert [path.relative_to(root).as_posix() for path in written] == [
        ".claude-plugin/marketplace.json",
        ".agents/plugins/marketplace.json",
    ]
    # loop 3, row 44: the contents, not only the paths, are each renderer's bytes for the loaded rows
    loaded = load_listings(root / "index.yaml", root=root)
    assert written[0].read_text(encoding="utf-8") == render_relative_marketplace(loaded)
    assert written[1].read_text(encoding="utf-8") == render_codex_marketplace(loaded)
    assert json.loads(written[0].read_text(encoding="utf-8"))["plugins"][0]["source"] == "./skills/mason/environment"
    assert json.loads(written[1].read_text(encoding="utf-8"))["plugins"][0]["source"] == {
        "source": "local",
        "path": "./skills/mason/environment",
    }


@pytest.mark.parametrize("link", [".agents", ".agents/plugins", ".claude-plugin"])
def test_the_manifests_are_not_written_through_a_symlink(tmp_path: Path, link: str) -> None:
    """Loop 4, row 65: ``root/.agents -> /elsewhere`` took the Codex manifest outside the tree while the returned
    path was the in-tree one. The Claude manifest is written first, so it exists exactly when the link is not its
    own directory (loop 5, row 92)."""
    root = _marketplace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / link).parent.mkdir(parents=True, exist_ok=True)
    (root / link).symlink_to(elsewhere)
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="is a symlink; refusing to write through it"):
        write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert not list(elsewhere.rglob("*"))
    assert (root / ".claude-plugin" / "marketplace.json").is_file() == (link != ".claude-plugin")
    assert not (root / ".agents" / "plugins" / "marketplace.json").exists()
    # a destination outside the tree (a test's temp file) is the caller's and still written
    written = write_plugin_manifest(root / "index.yaml", tmp_path / "out" / "m.json", flags_path=on)
    assert written.is_file()


def test_the_manifests_are_not_written_through_a_symlink_when_the_root_is_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop 5, row 85: a relative root (the README snippet's ``Path('docs/foundry/marketplace')``) with an absolute
    destination made ``relative_to`` raise and the containment return, so the manifest went through the link."""
    root = _marketplace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / ".agents").symlink_to(elsewhere)
    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.chdir(tmp_path)
    index = Path("marketplace") / "index.yaml"
    with pytest.raises(MarketplaceIndexError, match=".agents is a symlink; refusing to write through it"):
        write_codex_manifest(index, root / ".agents" / "plugins" / "marketplace.json", flags_path=on)
    with pytest.raises(MarketplaceIndexError, match=".agents is a symlink; refusing to write through it"):
        write_codex_manifest(root / "index.yaml", Path("marketplace") / ".agents" / "plugins" / "m.json", flags_path=on)
    assert not list(elsewhere.rglob("*"))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
@pytest.mark.parametrize("parent_exists", [False, True])
def test_a_dot_dot_destination_is_read_lexically_for_both_manifests(
    tmp_path: Path, writer, parent_exists: bool
) -> None:
    """Loop 5, row 85: ``root/../out/m.json`` was inside the tree to ``relative_to`` and judged by its resolved parent
    only when that parent existed, so the same destination was written when ``out/`` was absent and refused when it
    was present. Normalised, it is outside the tree either way: the caller's, written where it names."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    if parent_exists:
        (tmp_path / "out").mkdir()
    written = writer(root / "index.yaml", root / ".." / "out" / "m.json", flags_path=on)
    assert written.resolve() == (tmp_path / "out" / "m.json") and written.is_file()
    assert not (root / "out").exists()
    # a .. that stays inside the tree is held to the symlink rule on the normalised path
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    (root / ".claude-plugin").symlink_to(elsewhere)
    with pytest.raises(MarketplaceIndexError, match=".claude-plugin is a symlink; refusing to write through it"):
        writer(root / "index.yaml", root / "skills" / ".." / ".claude-plugin" / "marketplace.json", flags_path=on)
    assert not list(elsewhere.rglob("*"))


@pytest.mark.parametrize(
    ("writer", "name"),
    [
        (write_plugin_manifest, ".claude-plugin/marketplace.json"),
        (write_codex_manifest, ".agents/plugins/marketplace.json"),
    ],
)
def test_a_dot_dot_after_a_symlinked_directory_is_refused_for_both_manifests(tmp_path: Path, writer, name: str) -> None:
    """Loop 6, row 96: the loop-5 lexical reading collapsed ``linkdir/..`` before the symlink walk, while the OS
    follows ``linkdir`` first, so ``root/linkdir/../<manifest>`` was written under ``linkdir``'s target's parent;
    ``4e1ac45dbc`` refused it, and since loop 7 (row 114) the walk refuses it at ``linkdir`` again. A tree reached
    under another spelling (``link -> root``) is the tree: a destination spelled through either name is held to the
    symlink rule."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "elsewhere" / "sub").mkdir(parents=True)
    (root / "linkdir").symlink_to(tmp_path / "elsewhere" / "sub")
    with pytest.raises(MarketplaceIndexError, match="linkdir is a symlink; refusing to write through it"):
        writer(root / "index.yaml", root / "linkdir" / ".." / name, flags_path=on)
    assert not list((tmp_path / "elsewhere").rglob("*.json")) and not (root / name).exists()
    (root / "linkdir").unlink()
    first = name.split("/", 1)[0]
    (root / first).symlink_to(tmp_path / "elsewhere")
    (tmp_path / "link").symlink_to(root)
    for index, dest in (
        (tmp_path / "link" / "index.yaml", root / name),
        (root / "index.yaml", tmp_path / "link" / name),
    ):
        with pytest.raises(MarketplaceIndexError, match=f"{first} is a symlink; refusing to write through it"):
            writer(index, dest, flags_path=on)
    assert not list((tmp_path / "elsewhere").rglob("*.json"))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_the_destination_is_walked_as_spelled(tmp_path: Path, writer) -> None:
    """Loop 7, row 114: the walk enters the tree at the first prefix that resolves inside it, whatever spelling
    reaches it. An alias of an in-tree directory followed by an in-tree symlink out, and an alias of the root through
    ``.claude-plugin -> root``, were written or passed; a destination that never enters the tree, or leaves it by
    ``..``, is the caller's and is written where the OS puts it."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "inner").mkdir()
    (root / "inner" / "x").symlink_to(elsewhere)
    (tmp_path / "alias").symlink_to(root / "inner")
    with pytest.raises(MarketplaceIndexError, match="^[^:]+: inner/x is a symlink; refusing to write through it"):
        writer(root / "index.yaml", tmp_path / "alias" / "x" / "m.json", flags_path=on)
    assert not list(elsewhere.rglob("*"))
    (root / "loop").symlink_to(root)
    (tmp_path / "rootalias").symlink_to(root)
    with pytest.raises(MarketplaceIndexError, match="loop is a symlink; refusing to write through it"):
        writer(root / "index.yaml", tmp_path / "rootalias" / "loop" / "m.json", flags_path=on)
    assert not (root / "m.json").exists()
    (tmp_path / "out" / "sub").mkdir(parents=True)
    (tmp_path / "outlink").symlink_to(tmp_path / "out" / "sub")
    written = writer(root / "index.yaml", tmp_path / "outlink" / ".." / "m.json", flags_path=on)
    assert written.resolve() == tmp_path / "out" / "m.json" and written.is_file()


def test_an_index_spelled_through_a_symlink_and_dot_dot_writes_beside_the_index_it_read(tmp_path: Path) -> None:
    """Loop 7, row 114: loop 6's lexical compare refused ``a/link/../index.yaml`` (``link -> root/inner``), which
    ``080ce9f012`` wrote beside the index it read; the walk follows the ``..`` as the OS does."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    (root / "inner").mkdir()
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "link").symlink_to(root / "inner")
    written = write_plugin_manifests(tmp_path / "a" / "link" / ".." / "index.yaml", flags_path=on)
    assert [path.resolve() for path in written] == [
        root / ".claude-plugin" / "marketplace.json",
        root / ".agents" / "plugins" / "marketplace.json",
    ]


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_manifest_under_a_file_is_a_listing_error(tmp_path: Path, writer) -> None:
    """Loop 6, row 97: a destination whose parent is a regular file in the tree raised a raw ``FileExistsError``
    from ``mkdir``; every containment refusal is a ``MarketplaceIndexError``."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    for dest in (root / "index.yaml" / "m.json", root / "index.yaml" / "deeper" / "m.json"):
        with pytest.raises(MarketplaceIndexError, match="index.yaml is not a directory; refusing to write under it"):
            writer(root / "index.yaml", dest, flags_path=on)
    assert (root / "index.yaml").is_file()


def test_the_manifests_refuse_a_folder_the_index_does_not_declare(tmp_path: Path) -> None:
    """Loop 2, row 30: ``write_plugin_manifest`` holds the tree to the same rule as ``write_site_from_index``."""
    root = _marketplace(tmp_path)
    extra = root / "skills/mason/extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("# x\n", encoding="utf-8")
    (extra / "listing.yaml").write_text("id: mason/extra\n", encoding="utf-8")
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="the index does not declare"):
        write_plugin_manifest(root / "index.yaml", tmp_path / "m.json", flags_path=on)
    with pytest.raises(MarketplaceIndexError, match="the index does not declare"):
        write_codex_manifest(root / "index.yaml", tmp_path / "c.json", flags_path=on)
    assert not (tmp_path / "m.json").exists() and not (tmp_path / "c.json").exists()


# --- Story 109.8 (DW-steward-109-3-5, -7 and -10): the destination itself -------------------------------------------


def _leftovers(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir() if path.name.endswith(".tmp"))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_manifest_is_rewritten_in_place(tmp_path: Path, writer) -> None:
    """The non-directory check stops before the last part: a second write over an existing manifest succeeds (a
    mutant that widened it to the last part refused every rewrite and survived)."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root / "out" / "marketplace.json"
    first = writer(root / "index.yaml", dest, flags_path=on).read_text(encoding="utf-8")
    assert writer(root / "index.yaml", dest, flags_path=on).read_text(encoding="utf-8") == first
    assert _leftovers(dest.parent) == []


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_fifo_destination_is_refused_without_blocking(tmp_path: Path, writer) -> None:
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root / "marketplace.json"
    os.mkfifo(dest)
    outcome: list[BaseException] = []

    def write() -> None:
        try:
            writer(root / "index.yaml", dest, flags_path=on)
        except BaseException as exc:  # noqa: BLE001 - the thread hands the outcome back
            outcome.append(exc)

    thread = threading.Thread(target=write, daemon=True)
    thread.start()
    thread.join(timeout=10)
    assert not thread.is_alive(), "the writer blocked on the FIFO"
    assert len(outcome) == 1 and isinstance(outcome[0], MarketplaceIndexError)
    assert "exists and is not a regular file" in str(outcome[0])


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
@pytest.mark.parametrize("shape", ["directory", "root"])
def test_a_directory_destination_is_refused_by_name(tmp_path: Path, writer, shape: str) -> None:
    """A directory destination raised a raw ``IsADirectoryError``; the marketplace root itself is one (loop 8)."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root if shape == "root" else root / "marketplace.json"
    if shape == "directory":
        dest.mkdir()
    with pytest.raises(MarketplaceIndexError, match="exists and is not a regular file; refusing to write over it"):
        writer(root / "index.yaml", dest, flags_path=on)


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_hard_linked_destination_keeps_its_other_names_bytes(tmp_path: Path, writer) -> None:
    """A hard link to a file outside the tree had that file overwritten; the write now replaces the name."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    outside = tmp_path / "outside.json"
    outside.write_text("keep", encoding="utf-8")
    dest = root / "marketplace.json"
    os.link(outside, dest)
    writer(root / "index.yaml", dest, flags_path=on)
    assert outside.read_text(encoding="utf-8") == "keep"
    assert dest.read_text(encoding="utf-8") != "keep" and dest.stat().st_ino != outside.stat().st_ino


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root writes through a 0o500 directory")
@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_an_unwritable_directory_on_the_way_is_a_listing_error(tmp_path: Path, writer) -> None:
    """An ``OSError`` from creating the directory or the file was raised raw; it names the destination now."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    locked = root / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        for dest in (locked / "sub" / "m.json", locked / "m.json"):
            with pytest.raises(MarketplaceIndexError, match=f"cannot write {dest}"):
                writer(root / "index.yaml", dest, flags_path=on)
    finally:
        locked.chmod(0o700)
    assert _leftovers(locked) == []


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_failed_move_leaves_no_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer) -> None:
    """Review loop 1, row 4: the temporary file is removed when the move over the destination fails."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root / "out" / "marketplace.json"

    def refuse(*_: object) -> None:
        raise OSError(28, "No space left on device")

    # only the module under test loses its os.replace; the flag reader keeps the real one
    monkeypatch.setattr(marketplace_pages, "os", types.SimpleNamespace(**{**vars(os), "replace": refuse}))
    with pytest.raises(MarketplaceIndexError, match="cannot write .*No space left on device"):
        writer(root / "index.yaml", dest, flags_path=on)
    assert not dest.exists() and _leftovers(dest.parent) == []


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_stale_temporary_file_does_not_block_the_write(tmp_path: Path, writer) -> None:
    """Review loop 1, rows 4 and 5: a temporary file a killed run left beside the destination, under any name, is
    neither reused nor followed (a symlink there keeps pointing where it did, its target uncreated)."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root / "marketplace.json"
    stale = root / f".marketplace.json.{os.getpid()}.tmp"
    stale.write_text("stale", encoding="utf-8")
    planted = root / ".marketplace.json.planted.tmp"
    planted.symlink_to(tmp_path / "never-created")
    writer(root / "index.yaml", dest, flags_path=on)
    assert dest.is_file() and stale.read_text(encoding="utf-8") == "stale"
    assert planted.is_symlink() and not (tmp_path / "never-created").exists()


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_the_manifest_keeps_an_existing_mode_and_is_0o644_when_new(tmp_path: Path, writer) -> None:
    """``mkstemp`` creates ``0o600``; the written manifest keeps the destination's mode, else ``0o644``."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    fresh = writer(root / "index.yaml", root / "fresh.json", flags_path=on)
    assert fresh.stat().st_mode & 0o777 == 0o644
    kept = root / "kept.json"
    kept.write_text("x", encoding="utf-8")
    kept.chmod(0o640)
    writer(root / "index.yaml", kept, flags_path=on)
    assert kept.stat().st_mode & 0o777 == 0o640


@pytest.mark.skipif(not Path("/proc/self/fd").is_dir(), reason="needs /proc/self/fd to count descriptors")
@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_failed_fdopen_closes_the_temporary_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer
) -> None:
    """Review loop 2, row 14: when ``os.fdopen`` raised, the descriptor ``mkstemp`` opened stayed open."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = root / "marketplace.json"

    def refuse(*_: object, **__: object) -> None:
        raise OSError(24, "Too many open files")

    monkeypatch.setattr(marketplace_pages, "os", types.SimpleNamespace(**{**vars(os), "fdopen": refuse}))
    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(MarketplaceIndexError, match="cannot write .*Too many open files"):
        writer(root / "index.yaml", dest, flags_path=on)
    assert len(os.listdir("/proc/self/fd")) == before
    assert not dest.exists() and _leftovers(root) == []
