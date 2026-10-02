"""Meta-test: the scoped spec-surface stamp refuses an unreconciled path
(Story 82.3, DW-9-1-1; ``spec-pyforge-marshal`` CAP-235).

``scripts/spec_surface_check.py --write-baseline --spec NAME`` merges every
file NAME's surface matches, so a drifted file under a broad glob used to be
absorbed as reconciled with no trace. Now a path that differs from NAME's
baseline entry stamps only when it is ``--accept``ed or NAME's memlog moved
since the baseline AND names it (Doctor's clean-pass bar); otherwise the whole
stamp refuses, exit 1, baseline untouched. A spec with no baseline entry and
the unscoped stamp are unchanged.

The script lives at the repo root, outside this package; the station's own
suite owns its tests, loading it by path (the ``test_fleet_picture_*.py``
precedent) against a miniature fixture git repo -- a patched copy of the
script with ``REPO_ROOT`` repointed, the harness shape in
``.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py``,
whose own fixtures this file deliberately does not touch.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
CHECKER = REPO_ROOT / "scripts" / "spec_surface_check.py"

_ALPHA = "proj/spec-alpha"
_BETA = "proj/spec-beta"


def _spec_dir(repo: Path, slug: str) -> Path:
    return repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts" / "specs" / slug


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Two specs: alpha governs ``a.py`` and ``a2.py``, beta governs ``b.py``.
    Every file is staged (the stamp reads ``git ls-files``) and the baseline is
    stamped once, so each test starts from a fully reconciled tree."""
    for slug, governed in (("spec-alpha", ("a.py", "a2.py")), ("spec-beta", ("b.py",))):
        directory = _spec_dir(tmp_path, slug)
        directory.mkdir(parents=True)
        surface = "".join(f"  - {name}\n" for name in governed)
        (directory / "SPEC.md").write_text(f"---\nsurface:\n{surface}---\n# {slug}\n", encoding="utf-8")
        (directory / ".memlog.md").write_text("- (note) initial\n", encoding="utf-8")
        for name in governed:
            (tmp_path / name).write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    _stamp(tmp_path)
    return tmp_path


def _checker(repo: Path) -> Path:
    """The script loaded by path, with ``REPO_ROOT`` repointed at ``repo``."""
    source = CHECKER.read_text(encoding="utf-8")
    patched = source.replace("REPO_ROOT = Path(__file__).resolve().parent.parent", f"REPO_ROOT = Path({str(repo)!r})")
    assert patched != source, "the script's REPO_ROOT line moved; update this harness"
    destination = repo / "scripts" / "checker.py"
    destination.write_text(patched, encoding="utf-8")
    return destination


def _stamp(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_checker(repo)), "--write-baseline", *args],
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
    )


def _baseline_path(repo: Path) -> Path:
    return repo / "scripts" / ".spec-surface-baseline.json"


def _baseline(repo: Path) -> dict:
    return json.loads(_baseline_path(repo).read_text(encoding="utf-8"))


def _drift(repo: Path, name: str = "a.py", text: str = "x = 2\n") -> None:
    (repo / name).write_text(text, encoding="utf-8")


def _narrate(repo: Path, slug: str, text: str) -> None:
    memlog = _spec_dir(repo, slug) / ".memlog.md"
    memlog.write_text(memlog.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_the_script_is_loadable_by_path_with_the_new_surface() -> None:
    """The harness's own premise: the file exists where this package expects it
    and carries the stamp rule and the ``--accept`` flag."""
    spec = importlib.util.spec_from_file_location("spec_surface_check_under_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "StampRefused")
    assert "--accept" in CHECKER.read_text(encoding="utf-8")


def test_a_drifted_path_the_memlog_does_not_name_refuses_and_leaves_the_baseline_byte_identical(repo: Path) -> None:
    before = _baseline_path(repo).read_bytes()
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 1
    assert f"{_ALPHA}: a.py (changed)" in result.stderr
    # The refusal names the explicit form that accepts the path.
    assert f"python scripts/spec_surface_check.py --write-baseline --spec {_ALPHA} --accept a.py" in result.stderr
    assert "baseline untouched" in result.stderr
    assert _baseline_path(repo).read_bytes() == before
    assert not _baseline_path(repo).with_name(".spec-surface-baseline.json.tmp").exists()


def test_every_unreconciled_path_is_listed_with_how_it_differs(repo: Path) -> None:
    (repo / "a3.py").write_text("x = 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    _spec_dir(repo, "spec-alpha").joinpath("SPEC.md").write_text(
        "---\nsurface:\n  - a.py\n  - a2.py\n  - a3.py\n---\n# spec-alpha\n", encoding="utf-8"
    )
    (repo / "a2.py").unlink()
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 1
    assert f"{_ALPHA}: a.py (changed)" in result.stderr
    assert f"{_ALPHA}: a2.py (removed)" in result.stderr
    assert f"{_ALPHA}: a3.py (added)" in result.stderr
    assert "--accept a.py --accept a2.py --accept a3.py" in result.stderr


def test_an_explicitly_accepted_path_stamps_the_spec(repo: Path) -> None:
    before = _baseline(repo)
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA, "--accept", "a.py")

    assert result.returncode == 0, result.stderr
    after = _baseline(repo)
    assert after[_ALPHA] != before[_ALPHA]
    assert after[_BETA] == before[_BETA]


def test_accepting_one_path_does_not_accept_another(repo: Path) -> None:
    before = _baseline_path(repo).read_bytes()
    _drift(repo)
    _drift(repo, "a2.py")

    result = _stamp(repo, "--spec", _ALPHA, "--accept", "a.py")

    assert result.returncode == 1
    assert "a2.py (changed)" in result.stderr
    assert "a.py (changed)" not in result.stderr
    assert _baseline_path(repo).read_bytes() == before


def test_a_path_named_on_a_memlog_that_moved_stamps_without_accept(repo: Path) -> None:
    before = _baseline(repo)
    _drift(repo)
    _narrate(repo, "spec-alpha", "- (event) Story 82.3 landed: a.py\n")

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 0, result.stderr
    assert _baseline(repo)[_ALPHA] != before[_ALPHA]


def test_a_memlog_that_moved_without_naming_the_path_still_refuses(repo: Path) -> None:
    """Doctor reads this as ``drift-presumed``: confirmation is the operator's."""
    before = _baseline_path(repo).read_bytes()
    _drift(repo)
    _narrate(repo, "spec-alpha", "- (event) something unrelated\n")

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 1
    assert "a.py (changed)" in result.stderr
    assert _baseline_path(repo).read_bytes() == before


def test_a_memlog_that_names_the_path_but_did_not_move_since_the_baseline_refuses(tmp_path: Path) -> None:
    """A stale mention from an earlier reconcile must not launder a fresh edit
    (Doctor reads that as ``drift``, not reconciled)."""
    directory = _spec_dir(tmp_path, "spec-alpha")
    directory.mkdir(parents=True)
    (directory / "SPEC.md").write_text("---\nsurface:\n  - a.py\n---\n# spec-alpha\n", encoding="utf-8")
    (directory / ".memlog.md").write_text("- (event) Story 1.1 landed: a.py\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    assert _stamp(tmp_path).returncode == 0
    before = _baseline_path(tmp_path).read_bytes()
    _drift(tmp_path)

    result = _stamp(tmp_path, "--spec", _ALPHA)

    assert result.returncode == 1
    assert f"{_ALPHA}: a.py (changed)" in result.stderr
    assert _baseline_path(tmp_path).read_bytes() == before


def test_one_refusal_stamps_none_of_the_named_specs(repo: Path) -> None:
    """Every named spec is checked before any write: beta is reconciled, alpha
    is not, so neither stamps."""
    before = _baseline_path(repo).read_bytes()
    _drift(repo)
    _drift(repo, "b.py", "y = 2\n")
    _narrate(repo, "spec-beta", "- (event) Story 82.3 landed: b.py\n")

    result = _stamp(repo, "--spec", _BETA, "--spec", _ALPHA)

    assert result.returncode == 1
    assert f"{_ALPHA}: a.py (changed)" in result.stderr
    assert f"{_BETA}:" not in result.stderr
    assert _baseline_path(repo).read_bytes() == before


def test_a_spec_with_no_baseline_entry_stamps_as_today(repo: Path) -> None:
    entries = _baseline(repo)
    del entries[_ALPHA]
    _baseline_path(repo).write_text(json.dumps(entries, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 0, result.stderr
    assert _ALPHA in _baseline(repo)


def test_a_spec_with_an_unusable_baseline_entry_stamps_as_today(repo: Path) -> None:
    entries = _baseline(repo)
    entries[_ALPHA] = "not-an-object"
    _baseline_path(repo).write_text(json.dumps(entries) + "\n", encoding="utf-8")
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 0, result.stderr
    assert isinstance(_baseline(repo)[_ALPHA], dict)


def test_a_scoped_stamp_with_nothing_drifted_still_stamps(repo: Path) -> None:
    result = _stamp(repo, "--spec", _ALPHA)

    assert result.returncode == 0, result.stderr


def test_the_unscoped_stamp_is_unchanged_and_accepts_every_drifted_path(repo: Path) -> None:
    before = _baseline(repo)
    _drift(repo)
    _drift(repo, "b.py", "y = 2\n")

    result = _stamp(repo)

    assert result.returncode == 0, result.stderr
    after = _baseline(repo)
    assert after[_ALPHA] != before[_ALPHA]
    assert after[_BETA] != before[_BETA]


def test_an_unknown_spec_still_exits_two(repo: Path) -> None:
    result = _stamp(repo, "--spec", "proj/spec-nope")

    assert result.returncode == 2
    assert "unknown spec" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--accept", "a.py"], id="without-write-baseline"),
        pytest.param(["--write-baseline", "--accept", "a.py"], id="without-spec"),
    ],
)
def test_accept_outside_a_scoped_stamp_is_a_usage_error(repo: Path, args: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(_checker(repo)), *args], capture_output=True, text=True, cwd=repo, check=False
    )

    assert result.returncode == 2
    assert "--accept" in result.stderr


def test_a_dot_slash_accept_path_matches_the_repo_relative_path(repo: Path) -> None:
    _drift(repo)

    result = _stamp(repo, "--spec", _ALPHA, "--accept", "./a.py")

    assert result.returncode == 0, result.stderr
