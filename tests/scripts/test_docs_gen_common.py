"""Unit tests for ``scripts/_docs_gen_common.py`` -- the shared stamp +
write/check plumbing behind every Story 30.3 doc generator
(spec-pyforge-doctor CAP-84).

``pytest.importorskip("yaml")`` mirrors ``test_docs_map_render.py``'s own
precedent: ``pyforge-ci``, the env ``pyforge-doctor-scripts-test`` runs
from, is stdlib-only (steward Story 103.3; the definition is the comment
above ``pyforge-ci`` in ``pixi.toml``), so this file skips there. It runs
in the ``docs-gen-test`` and ``scripts-lib-test`` guild-tasks tasks, in
``pyforge-guild``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


# --- head_stamp ---------------------------------------------------------


def test_head_stamp_clean_tree_has_no_dirty_suffix(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("v1\n", encoding="utf-8")
    _commit_all(tmp_path, "seed")

    stamp = common.head_stamp(tmp_path)

    assert not stamp["tree"].endswith("-dirty")
    assert stamp["tree"] == _git(tmp_path, "rev-parse", "HEAD").strip()


def test_head_stamp_dirty_tree_gets_suffix(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("v1\n", encoding="utf-8")
    _commit_all(tmp_path, "seed")
    (tmp_path / "a.txt").write_text("v2 uncommitted\n", encoding="utf-8")

    stamp = common.head_stamp(tmp_path)

    assert stamp["tree"].endswith("-dirty")


def test_head_stamp_is_idempotent_on_an_unchanged_tree(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("v1\n", encoding="utf-8")
    _commit_all(tmp_path, "seed")

    assert common.head_stamp(tmp_path) == common.head_stamp(tmp_path)


# --- parse_frontmatter ----------------------------------------------------


def test_parse_frontmatter_reads_a_fenced_block():
    text = "---\nname: example\ndescription: a thing\n---\n\nbody\n"
    assert common.parse_frontmatter(text) == {
        "name": "example",
        "description": "a thing",
    }


def test_parse_frontmatter_returns_empty_dict_when_no_fence():
    assert common.parse_frontmatter("just body text\n") == {}


def test_parse_frontmatter_returns_empty_dict_on_malformed_yaml():
    text = "---\n[unclosed\n---\nbody\n"
    assert common.parse_frontmatter(text) == {}


def test_parse_frontmatter_recovers_description_via_regex_when_the_block_fails_to_parse():
    # Real content (.claude/skills/performance-optimization/SKILL.md, found live
    # 2026-09-24): a mid-value ": " in an unquoted plain scalar is invalid YAML
    # (reads as a nested mapping), so the whole block fails to parse -- the
    # regex fallback must still recover `description` rather than losing it.
    text = (
        "---\n"
        "name: performance-optimization\n"
        "description: Measure before optimizing. Five-step workflow: Measure -> "
        "Identify -> Fix -> Verify -> Guard. No guessing.\n"
        "source: https://github.com/addyosmani/agent-skills\n"
        "---\n\nbody\n"
    )

    result = common.parse_frontmatter(text)

    assert result == {
        "description": "Measure before optimizing. Five-step workflow: Measure -> "
        "Identify -> Fix -> Verify -> Guard. No guessing."
    }


# --- update_map_stamp ------------------------------------------------------


def test_update_map_stamp_writes_stamp_into_the_matching_page(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "pages": [
                    {
                        "path": "how-to/pixi-tasks.md",
                        "quadrant": "how-to",
                        "owner": "steward",
                        "kind": "generated",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    common.update_map_stamp(
        tmp_path,
        "how-to/pixi-tasks.md",
        {"derived_at": "2026-01-01T00:00:00", "tree": "abc"},
    )

    data = yaml.safe_load((docs / "map.yaml").read_text(encoding="utf-8"))
    assert data["pages"][0]["stamp"] == {
        "derived_at": "2026-01-01T00:00:00",
        "tree": "abc",
    }


def test_update_map_stamp_is_a_noop_when_map_yaml_is_missing(tmp_path: Path):
    # Must not raise -- the generator's own page write already succeeded.
    common.update_map_stamp(
        tmp_path, "how-to/pixi-tasks.md", {"derived_at": "x", "tree": "y"}
    )


def test_update_map_stamp_preserves_the_2_space_indented_style_of_untouched_pages(
    tmp_path: Path,
):
    # docs/map.yaml's own hand-authored convention indents block-sequence
    # items 2 spaces under their key (`  - path:`); plain `yaml.safe_dump`
    # instead produces PyYAML's default "indentless" style (`- path:` flush
    # with the key), which would reformat every untouched page as a side
    # effect of stamping just one.
    docs = tmp_path / "docs"
    docs.mkdir()
    hand_authored = (
        "schema_version: 1\n"
        "pages:\n"
        "  - path: how-to/pixi-tasks.md\n"
        "    quadrant: how-to\n"
        "    owner: steward\n"
        "    kind: generated\n"
        "  - path: reference/other.md\n"
        "    quadrant: reference\n"
        "    owner: fleet\n"
        "    kind: authored\n"
    )
    (docs / "map.yaml").write_text(hand_authored, encoding="utf-8")

    common.update_map_stamp(
        tmp_path,
        "how-to/pixi-tasks.md",
        {"derived_at": "2026-01-01T00:00:00", "tree": "abc"},
    )

    written = (docs / "map.yaml").read_text(encoding="utf-8")
    # The untouched page's own lines are byte-identical to the original.
    assert "  - path: reference/other.md\n" in written
    assert "    quadrant: reference\n" in written
    assert "    owner: fleet\n" in written
    assert "    kind: authored\n" in written
    # The touched page gained its stamp, same indented style.
    assert "  - path: how-to/pixi-tasks.md\n" in written
    assert (
        "    stamp:\n      derived_at: '2026-01-01T00:00:00'\n      tree: abc\n"
        in written
    )


def test_update_map_stamp_is_a_noop_when_page_is_not_in_the_registry(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    original = yaml.safe_dump({"schema_version": 1, "pages": []})
    (docs / "map.yaml").write_text(original, encoding="utf-8")

    common.update_map_stamp(
        tmp_path, "how-to/pixi-tasks.md", {"derived_at": "x", "tree": "y"}
    )

    assert (docs / "map.yaml").read_text(encoding="utf-8") == original


# --- write_generated_page ---------------------------------------------------


def test_write_generated_page_check_mode_matches_current_content(tmp_path: Path):
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"
    page.parent.mkdir(parents=True)
    page.write_text("content\n", encoding="utf-8")

    assert (
        common.write_generated_page(
            tmp_path, "how-to/pixi-tasks.md", "content\n", check=True
        )
        == 0
    )


def test_write_generated_page_check_mode_reports_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"
    page.parent.mkdir(parents=True)
    page.write_text("old content\n", encoding="utf-8")

    exit_code = common.write_generated_page(
        tmp_path, "how-to/pixi-tasks.md", "new content\n", check=True
    )

    assert exit_code == 1
    assert "STALE" in capsys.readouterr().err
    assert (
        page.read_text(encoding="utf-8") == "old content\n"
    )  # never writes in check mode


def test_write_generated_page_check_mode_reports_stale_when_never_generated(
    tmp_path: Path,
):
    assert (
        common.write_generated_page(
            tmp_path, "how-to/pixi-tasks.md", "content\n", check=True
        )
        == 1
    )


def test_write_generated_page_writes_and_is_idempotent(tmp_path: Path):
    # stamp=None: no docs/map.yaml touched, so this needs no git repo at all.
    exit_code_1 = common.write_generated_page(
        tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=None
    )
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"

    assert exit_code_1 == 0
    assert page.read_text(encoding="utf-8") == "content\n"

    # Re-running with the SAME content is a no-op write, and --check now agrees.
    exit_code_2 = common.write_generated_page(
        tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=None
    )
    assert exit_code_2 == 0
    assert (
        common.write_generated_page(
            tmp_path, "how-to/pixi-tasks.md", "content\n", check=True
        )
        == 0
    )


def test_write_generated_page_check_mode_ignores_stamp_drift_from_an_unrelated_commit(
    tmp_path: Path,
):
    # Reproduces the live bug: this branch's own auto-checkpoint commits
    # advance HEAD every few seconds with the page's real source untouched,
    # which must NOT flip a generated page to stale on its own.
    _init_repo(tmp_path)
    (tmp_path / "source.txt").write_text("v1\n", encoding="utf-8")
    _commit_all(tmp_path, "seed: source.txt")
    stamp_1 = common.head_stamp(tmp_path)
    content_1 = (
        common.render_header("scripts/example.py", "example-task", stamp_1) + "\nbody\n"
    )
    common.write_generated_page(
        tmp_path, "how-to/example.md", content_1, check=False, stamp=None
    )
    _commit_all(tmp_path, "add generated page")

    # An unrelated commit that does not touch source.txt (or the page).
    (tmp_path / "unrelated.txt").write_text("unrelated change\n", encoding="utf-8")
    _commit_all(tmp_path, "unrelated commit -- advances HEAD, source.txt untouched")

    stamp_2 = common.head_stamp(tmp_path)
    assert stamp_2 != stamp_1  # HEAD really did move
    content_2 = (
        common.render_header("scripts/example.py", "example-task", stamp_2) + "\nbody\n"
    )

    assert (
        common.write_generated_page(
            tmp_path, "how-to/example.md", content_2, check=True
        )
        == 0
    )


def test_write_generated_page_records_the_passed_in_stamp_without_recomputing(
    tmp_path: Path,
):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "pages": [
                    {
                        "path": "how-to/pixi-tasks.md",
                        "quadrant": "how-to",
                        "owner": "steward",
                        "kind": "generated",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    stamp = {"derived_at": "2026-01-01T00:00:00", "tree": "abc"}

    # No git repo exists at tmp_path -- if this recomputed head_stamp() itself
    # (rather than using the passed-in stamp), it would raise.
    exit_code = common.write_generated_page(
        tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=stamp
    )

    assert exit_code == 0
    data = yaml.safe_load((docs / "map.yaml").read_text(encoding="utf-8"))
    assert data["pages"][0]["stamp"] == stamp


# --- the stamp's dirty flag is scoped to the page (doctor Story 60.2) ------

_PAGE_REL = "how-to/example.md"


def _render(stamp: dict[str, str], body: str = "body v1\n") -> str:
    return (
        common.render_header("scripts/docs_example.py", "docs-example", stamp)
        + "\n"
        + body
    )


def _scoped_repo(
    repo: Path, *, sources: list[str] | None, page_body: str | None = "body v1\n"
) -> None:
    """A committed tree: ``docs/map.yaml`` with one generated row (declaring ``sources`` unless ``None``), the
    source files, and -- unless ``page_body`` is ``None`` -- the generated page."""
    _init_repo(repo)
    row: dict = {
        "path": _PAGE_REL,
        "quadrant": "how-to",
        "owner": "fleet",
        "kind": "generated",
    }
    if sources is not None:
        row["sources"] = sources
    (repo / "docs").mkdir()
    (repo / "docs" / "map.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "pages": [row]}, sort_keys=False),
        encoding="utf-8",
    )
    (repo / "src.txt").write_text("v1\n", encoding="utf-8")
    (repo / "srcdir").mkdir()
    (repo / "srcdir" / "a.txt").write_text("v1\n", encoding="utf-8")
    (repo / "unrelated.txt").write_text("v1\n", encoding="utf-8")
    if page_body is not None:
        page = repo / "docs" / _PAGE_REL
        page.parent.mkdir(parents=True)
        page.write_text(
            _render(
                {"derived_at": "2020-01-01T00:00:00+00:00", "tree": "0" * 40}, page_body
            )
        )
    _commit_all(repo, "seed")


def test_scoped_stamp_ignores_an_unrelated_modified_file(tmp_path: Path):
    _scoped_repo(tmp_path, sources=["src.txt", "srcdir"])
    (tmp_path / "unrelated.txt").write_text("v2 uncommitted\n", encoding="utf-8")

    assert (
        common.head_stamp(tmp_path).get("tree", "").endswith("-dirty")
    )  # the whole-tree form still sees it
    stamp = common.head_stamp(tmp_path, _PAGE_REL)
    assert stamp["tree"] == _git(tmp_path, "rev-parse", "HEAD").strip()


def test_scoped_stamp_ignores_the_map_yaml_its_own_write_updates(tmp_path: Path):
    """Writing a page advances its row's stamp in ``docs/map.yaml``; that edit must not dirty the next run."""
    _scoped_repo(tmp_path, sources=["src.txt"])
    common.update_map_stamp(tmp_path, _PAGE_REL, {"derived_at": "x", "tree": "y"})
    assert _git(tmp_path, "status", "--porcelain").strip()

    assert not common.head_stamp(tmp_path, _PAGE_REL)["tree"].endswith("-dirty")


@pytest.mark.parametrize("rel", ["src.txt", "srcdir/a.txt"])
def test_scoped_stamp_is_dirty_when_a_declared_source_is_modified(
    tmp_path: Path, rel: str
):
    _scoped_repo(tmp_path, sources=["src.txt", "srcdir"])
    (tmp_path / rel).write_text("v2 uncommitted\n", encoding="utf-8")

    assert common.head_stamp(tmp_path, _PAGE_REL)["tree"].endswith("-dirty")


def test_scoped_stamp_is_dirty_when_a_declared_source_directory_gains_an_untracked_file(
    tmp_path: Path,
):
    _scoped_repo(tmp_path, sources=["srcdir"])
    (tmp_path / "srcdir" / "new.txt").write_text("not yet added\n", encoding="utf-8")

    assert common.head_stamp(tmp_path, _PAGE_REL)["tree"].endswith("-dirty")


def test_scoped_stamp_with_no_declared_sources_falls_back_to_the_whole_tree(
    tmp_path: Path,
):
    _scoped_repo(tmp_path, sources=None)
    assert not common.head_stamp(tmp_path, _PAGE_REL)["tree"].endswith("-dirty")
    (tmp_path / "unrelated.txt").write_text("v2 uncommitted\n", encoding="utf-8")

    assert common.head_stamp(tmp_path, _PAGE_REL)["tree"].endswith("-dirty")


def test_scoped_stamp_reads_the_page_body_against_head_not_its_stamp(tmp_path: Path):
    """The page is part of the flag by its BODY: a render whose body is what HEAD holds is clean (the stamp
    lines always differ from the committed ones), a render that changes the body is uncommitted work."""
    _scoped_repo(tmp_path, sources=["src.txt"])

    assert not common.head_stamp(tmp_path, _PAGE_REL, body="\nbody v1\n")[
        "tree"
    ].endswith("-dirty")
    assert common.head_stamp(tmp_path, _PAGE_REL, body="\nbody v2\n")["tree"].endswith(
        "-dirty"
    )


def test_scoped_stamp_is_dirty_for_a_page_head_does_not_hold(tmp_path: Path):
    _scoped_repo(tmp_path, sources=["src.txt"], page_body=None)

    assert common.head_stamp(tmp_path, _PAGE_REL, body="\nbody v1\n")["tree"].endswith(
        "-dirty"
    )


def _generate(repo: Path, body: str) -> tuple[dict[str, str], str]:
    calls: list[dict[str, str]] = []

    def render(stamp: dict[str, str]) -> str:
        calls.append(stamp)
        return _render(stamp, body)

    stamp, content = common.stamped_render(repo, _PAGE_REL, render)
    assert (
        len(calls) == 1
    )  # one render: a generator that shells out is not run twice for its stamp
    assert (
        common.write_generated_page(repo, _PAGE_REL, content, check=False, stamp=stamp)
        == 0
    )
    return stamp, (repo / "docs" / _PAGE_REL).read_text(encoding="utf-8")


@pytest.mark.parametrize(("body", "dirty"), [("body v1\n", False), ("body v2\n", True)])
def test_stamped_render_write_is_idempotent(tmp_path: Path, body: str, dirty: bool):
    """Two writes on the same tree are byte-identical, page and ``docs/map.yaml`` both -- whether the render
    matches what HEAD holds (clean stamp) or changes it (dirty stamp, on the first run already)."""
    _scoped_repo(tmp_path, sources=["src.txt"])
    (tmp_path / "unrelated.txt").write_text("v2 uncommitted\n", encoding="utf-8")
    head = _git(tmp_path, "rev-parse", "HEAD").strip()

    stamp_1, page_1 = _generate(tmp_path, body)
    map_1 = (tmp_path / "docs" / "map.yaml").read_text(encoding="utf-8")
    stamp_2, page_2 = _generate(tmp_path, body)

    assert stamp_1 == stamp_2
    assert stamp_1["tree"] == head + ("-dirty" if dirty else "")
    assert page_1 == page_2
    assert f"tree: {stamp_1['tree']} -->" in page_1
    assert f"derived_at: {stamp_1['derived_at']}\n" in page_1
    assert (tmp_path / "docs" / "map.yaml").read_text(encoding="utf-8") == map_1
    assert yaml.safe_load(map_1)["pages"][0]["stamp"] == stamp_1


def test_stamped_render_of_a_generator_that_ignores_its_stamp_still_returns_the_real_one(
    tmp_path: Path,
):
    _scoped_repo(tmp_path, sources=["src.txt"])

    stamp, content = common.stamped_render(
        tmp_path, _PAGE_REL, lambda stamp: "no header\nbody v1\n"
    )

    assert content == "no header\nbody v1\n"
    assert stamp["tree"].startswith(_git(tmp_path, "rev-parse", "HEAD").strip())
