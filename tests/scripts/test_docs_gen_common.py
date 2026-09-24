"""Unit tests for ``scripts/_docs_gen_common.py`` -- the shared stamp +
write/check plumbing behind every Story 30.3 doc generator
(spec-pyforge-doctor CAP-84).

``pytest.importorskip("yaml")`` mirrors ``test_docs_map_render.py``'s own
precedent: PyYAML is not a DECLARED dependency of ``pyforge-ci`` (the
deliberately dependency-free env ``pyforge-doctor-scripts-test`` also
runs from) -- verified present there today only transitively, via another
package's own sub-dependency. Real, guaranteed coverage runs from the
``docs-gen-test`` guild-tasks task; this guard just keeps collection from
crashing if that transitive availability ever goes away.
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

import _docs_gen_common as common  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


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
    assert common.parse_frontmatter(text) == {"name": "example", "description": "a thing"}


def test_parse_frontmatter_returns_empty_dict_when_no_fence():
    assert common.parse_frontmatter("just body text\n") == {}


def test_parse_frontmatter_returns_empty_dict_on_malformed_yaml():
    text = "---\n[unclosed\n---\nbody\n"
    assert common.parse_frontmatter(text) == {}


# --- update_map_stamp ------------------------------------------------------


def test_update_map_stamp_writes_stamp_into_the_matching_page(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "pages": [
                    {"path": "how-to/pixi-tasks.md", "quadrant": "how-to", "owner": "steward", "kind": "generated"},
                ],
            }
        ),
        encoding="utf-8",
    )

    common.update_map_stamp(tmp_path, "how-to/pixi-tasks.md", {"derived_at": "2026-01-01T00:00:00", "tree": "abc"})

    data = yaml.safe_load((docs / "map.yaml").read_text(encoding="utf-8"))
    assert data["pages"][0]["stamp"] == {"derived_at": "2026-01-01T00:00:00", "tree": "abc"}


def test_update_map_stamp_is_a_noop_when_map_yaml_is_missing(tmp_path: Path):
    # Must not raise -- the generator's own page write already succeeded.
    common.update_map_stamp(tmp_path, "how-to/pixi-tasks.md", {"derived_at": "x", "tree": "y"})


def test_update_map_stamp_is_a_noop_when_page_is_not_in_the_registry(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    original = yaml.safe_dump({"schema_version": 1, "pages": []})
    (docs / "map.yaml").write_text(original, encoding="utf-8")

    common.update_map_stamp(tmp_path, "how-to/pixi-tasks.md", {"derived_at": "x", "tree": "y"})

    assert (docs / "map.yaml").read_text(encoding="utf-8") == original


# --- write_generated_page ---------------------------------------------------


def test_write_generated_page_check_mode_matches_current_content(tmp_path: Path):
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"
    page.parent.mkdir(parents=True)
    page.write_text("content\n", encoding="utf-8")

    assert common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=True) == 0


def test_write_generated_page_check_mode_reports_stale(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"
    page.parent.mkdir(parents=True)
    page.write_text("old content\n", encoding="utf-8")

    exit_code = common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "new content\n", check=True)

    assert exit_code == 1
    assert "STALE" in capsys.readouterr().err
    assert page.read_text(encoding="utf-8") == "old content\n"  # never writes in check mode


def test_write_generated_page_check_mode_reports_stale_when_never_generated(tmp_path: Path):
    assert common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=True) == 1


def test_write_generated_page_writes_and_is_idempotent(tmp_path: Path):
    # stamp=None: no docs/map.yaml touched, so this needs no git repo at all.
    exit_code_1 = common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=None)
    page = tmp_path / "docs" / "how-to" / "pixi-tasks.md"

    assert exit_code_1 == 0
    assert page.read_text(encoding="utf-8") == "content\n"

    # Re-running with the SAME content is a no-op write, and --check now agrees.
    exit_code_2 = common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=None)
    assert exit_code_2 == 0
    assert common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=True) == 0


def test_write_generated_page_records_the_passed_in_stamp_without_recomputing(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "pages": [
                    {"path": "how-to/pixi-tasks.md", "quadrant": "how-to", "owner": "steward", "kind": "generated"},
                ],
            }
        ),
        encoding="utf-8",
    )
    stamp = {"derived_at": "2026-01-01T00:00:00", "tree": "abc"}

    # No git repo exists at tmp_path -- if this recomputed head_stamp() itself
    # (rather than using the passed-in stamp), it would raise.
    exit_code = common.write_generated_page(tmp_path, "how-to/pixi-tasks.md", "content\n", check=False, stamp=stamp)

    assert exit_code == 0
    data = yaml.safe_load((docs / "map.yaml").read_text(encoding="utf-8"))
    assert data["pages"][0]["stamp"] == stamp
