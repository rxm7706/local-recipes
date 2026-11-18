"""Unit tests for ``scripts/docs_github_workflows.py`` (doctor Story 59.1,
spec-pyforge-doctor CAP-84):
docs/reference/github-workflows.md generated from the workflow files under
``.github/workflows/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common
import docs_github_workflows as m

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}

_GATED = """\
name: Gated checks
on:
  pull_request:
    paths:
      - "src/**"
      - "pixi.toml"
  push:
    branches: [main]
    paths:
      - "src/**"
      - "pixi.toml"
  schedule:
    - cron: "23 */6 * * *"
  workflow_dispatch:
jobs:
  # vars.PAUSE_ONLY_IN_A_COMMENT is not read by any expression
  build:
    if: ${{ vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_GATED != 'true' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo build
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
"""

_MANUAL = """\
name: Fan out
on:
  workflow_dispatch:
    inputs:
      recipes:
        type: string
      platforms:
        type: string
jobs:
  linux:
    uses: ./.github/workflows/zz-callee.yml
  summary:
    runs-on: ubuntu-latest
    steps:
      - run: echo done
"""

_CALLEE = """\
name: Callee | piped
"on":
  workflow_call:
    inputs:
      recipes:
        type: string
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
"""


def _write_workflows(root: Path, **extra: str) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "gated.yml": _GATED,
        "manual.yml": _MANUAL,
        "zz-callee.yml": _CALLEE,
        **extra,
    }
    for filename, text in files.items():
        (directory / filename).write_text(text, encoding="utf-8")


def _row(content: str, filename: str) -> str:
    return next(
        line for line in content.splitlines() if line.startswith(f"| `{filename}` |")
    )


def test_bare_on_key_parses_as_true_and_still_yields_the_triggers():
    """PyYAML (YAML 1.1) reads a bare ``on:`` key as boolean ``True``; the
    generator must find the trigger block there, and under a quoted key."""
    import yaml

    bare = yaml.safe_load(_GATED)
    assert True in bare and "on" not in bare
    assert list(m._triggers(bare)) == [
        "pull_request",
        "push",
        "schedule",
        "workflow_dispatch",
    ]

    quoted = yaml.safe_load(_CALLEE)
    assert "on" in quoted and True not in quoted
    assert list(m._triggers(quoted)) == ["workflow_call"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("on: push\n", {"push": None}),
        ("on: [push, pull_request]\n", {"push": None, "pull_request": None}),
        ("name: no triggers\n", {}),
    ],
)
def test_triggers_accepts_every_spelling_of_on(text: str, expected: dict):
    import yaml

    assert m._triggers(yaml.safe_load(text)) == expected


def test_render_lists_every_workflow_sorted_with_name_triggers_and_jobs(tmp_path: Path):
    _write_workflows(tmp_path)

    content = m.render(tmp_path, _STAMP)

    assert "3 workflows, as of this render." in content
    assert (
        content.index("| `gated.yml` |")
        < content.index("| `manual.yml` |")
        < content.index("| `zz-callee.yml` |")
    )

    gated = _row(content, "gated.yml")
    assert "| Gated checks |" in gated
    assert "`pull_request` (2 paths)" in gated
    assert "`push` (branches `main`; 2 paths)" in gated
    assert "`schedule` (cron `23 */6 * * *`)" in gated
    assert "`workflow_dispatch`" in gated
    assert gated.endswith("| `build`, `deploy` |")

    manual = _row(content, "manual.yml")
    assert "`workflow_dispatch` (inputs `recipes`, `platforms`)" in manual
    assert "`linux` (calls `zz-callee.yml`), `summary`" in manual

    callee = _row(content, "zz-callee.yml")
    assert "`workflow_call` (inputs `recipes`)" in callee
    assert "Callee \\| piped" in callee  # a pipe in a name cannot break the table


def test_render_derives_gating_from_the_file_alone(tmp_path: Path):
    _write_workflows(tmp_path)

    content = m.render(tmp_path, _STAMP)

    gated = _row(content, "gated.yml")
    assert "path-gated; pause switches `PAUSE_ALL_CI`, `PAUSE_GATED`" in gated
    assert "PAUSE_ONLY_IN_A_COMMENT" not in content  # a comment is not an expression
    assert "manual only" not in gated

    assert "| manual only |" in _row(content, "manual.yml")
    assert "| manual only |" in _row(content, "zz-callee.yml")


def test_render_lists_path_filters_once_when_push_and_pull_request_share_them(
    tmp_path: Path,
):
    _write_workflows(tmp_path)

    content = m.render(tmp_path, _STAMP)

    section = content[content.index("## Path filters") :]
    assert "### `gated.yml`" in section
    assert "- `pull_request`, `push` `paths`: `src/**`, `pixi.toml`" in section
    assert "### `manual.yml`" not in section


def test_render_says_so_when_no_workflow_is_path_filtered(tmp_path: Path):
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "manual.yml").write_text(_MANUAL, encoding="utf-8")

    content = m.render(tmp_path, _STAMP)

    assert "1 workflow, as of this render." in content
    assert "None -- no workflow carries a `paths` or `paths-ignore` filter." in content


def test_render_survives_a_file_that_is_not_a_yaml_mapping(tmp_path: Path):
    _write_workflows(tmp_path, **{"broken.yml": "name: [unclosed\n", "empty.yaml": ""})

    content = m.render(tmp_path, _STAMP)

    assert "| `broken.yml` | *(not a YAML mapping)* |" in content
    assert "| `empty.yaml` | *(not a YAML mapping)* |" in content
    assert "5 workflows, as of this render." in content


def test_render_ignores_non_workflow_files_and_a_missing_directory(tmp_path: Path):
    assert "0 workflows, as of this render." in m.render(tmp_path, _STAMP)

    _write_workflows(tmp_path, **{"README.md": "# not a workflow\n"})
    (tmp_path / ".github" / "workflows" / "scripts").mkdir()

    content = m.render(tmp_path, _STAMP)

    assert "README.md" not in content
    assert "3 workflows, as of this render." in content


def test_render_is_deterministic(tmp_path: Path):
    _write_workflows(tmp_path)

    assert m.render(tmp_path, _STAMP) == m.render(tmp_path, dict(_STAMP))


def test_main_write_then_check_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_workflows(tmp_path)
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root: dict(_STAMP))

    monkeypatch.setattr(sys, "argv", ["docs_github_workflows.py"])
    assert m.main() == 0
    page = tmp_path / "docs" / "reference" / "github-workflows.md"
    first = page.read_text(encoding="utf-8")
    assert first.startswith("<!-- GENERATED by scripts/docs_github_workflows.py")
    assert "pixi run -e pyforge-guild docs-github-workflows" in first

    # Idempotent: a second write on the unchanged tree is byte-identical.
    assert m.main() == 0
    assert page.read_text(encoding="utf-8") == first

    monkeypatch.setattr(sys, "argv", ["docs_github_workflows.py", "--check"])
    assert m.main() == 0

    # A new workflow file, not yet regenerated -> --check reds it.
    (tmp_path / ".github" / "workflows" / "new-lane.yml").write_text(
        "name: New lane\non: push\njobs:\n  only:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    assert m.main() == 1

    monkeypatch.setattr(sys, "argv", ["docs_github_workflows.py"])
    assert m.main() == 0
    assert "| `new-lane.yml` | New lane | `push` |  | `only` |" in page.read_text(
        encoding="utf-8"
    )
