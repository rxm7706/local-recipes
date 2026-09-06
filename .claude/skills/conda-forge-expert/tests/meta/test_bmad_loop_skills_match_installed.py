"""Meta: the repo's bmad-loop-* skill dirs never silently drift from the
installed `bmad_loop` package's own canon.

`bmad-loop-setup` vendors three skill dirs into this repo
(`.claude/skills/bmad-loop-setup`, `-sweep`, `-resolve`) as hand-copies of the
installed `bmad_loop` conda package's `bmad_loop/data/skills/<name>/` — the
same files the package's own installer would otherwise refresh on demand.
Nothing caught these copies drifting apart from the package when it upgrades:
`module.yaml`'s `module_version` field once lagged the installed package by
one release (0.11.0 vendored vs 0.11.1 installed) and no test noticed. As of
this story's landing, `test_repo_bmad_loop_skills_match_installed_package`
below passes unskipped against the live tree, which is the checkable proof
that `module_version` and the three skill-dir contents already matched the
installed package at that point in time — the gap this test closes is that
no such check existed before, so a future package bump could silently drift
the repo copies again without any signal.

This test closes that gap: it locates the installed `bmad_loop` package via
`importlib.util.find_spec` (deliberately never
`importlib.metadata.distribution(...).locate_file`, which does not reliably
locate a conda-installed package's data files the same way) and recursively
diffs each of the three repo skill dirs against the package's own
`data/skills/<name>/` canon — file sets and byte content both. If `bmad_loop`
is not importable in the environment running this suite (e.g. a pixi env that
doesn't include it), the real-tree assertion skips rather than false-failing:
this is a repo-hygiene guard, not a hard dependency requirement.

The diff logic itself is proven correct independent of whatever happens to be
installed, via a `tmp_path`-based fixture: two small synthetic directory
trees, never the real skill dirs, with a planted one-line divergence that the
guard must report.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# .claude/skills/<skill>/tests/meta/<file> -> repo root.
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SKILL_DIR.parents[2]

# The three repo skill dirs hand-vendored from the installed bmad_loop
# package's own data/skills/ canon.
BMAD_LOOP_SKILL_NAMES = ("bmad-loop-setup", "bmad-loop-sweep", "bmad-loop-resolve")

PACKAGE_NAME = "bmad_loop"


def find_installed_package_dir() -> Path | None:
    """Locate the installed `bmad_loop` package's directory, or None.

    Deliberately `importlib.util.find_spec`, never `importlib.metadata` --
    see the module docstring. Prefers `submodule_search_locations` (the
    package's own directory); falls back to the parent of `spec.origin` for
    the unlikely case a spec has no search locations but does have an
    origin.
    """
    spec = importlib.util.find_spec(PACKAGE_NAME)
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return Path(next(iter(spec.submodule_search_locations)))
    if spec.origin:
        return Path(spec.origin).parent
    return None


def _relative_files(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def diff_dirs(dir_a: Path, dir_b: Path) -> list[str]:
    """Recursively diff two directory trees: file sets, then byte content.

    Returns human-readable divergence descriptions, sorted; an empty list
    means the trees are identical.
    """
    files_a = _relative_files(dir_a)
    files_b = _relative_files(dir_b)

    diffs: list[str] = []
    diffs += [f"only in {dir_a}: {rel}" for rel in sorted(files_a - files_b)]
    diffs += [f"only in {dir_b}: {rel}" for rel in sorted(files_b - files_a)]

    for rel in sorted(files_a & files_b):
        if (dir_a / rel).read_bytes() != (dir_b / rel).read_bytes():
            diffs.append(f"content differs: {rel}")

    return diffs


@pytest.mark.meta
def test_repo_bmad_loop_skills_match_installed_package():
    """Each repo bmad-loop-* skill dir diffs empty against the installed canon."""
    pkg_dir = find_installed_package_dir()
    if pkg_dir is None:
        pytest.skip(f"{PACKAGE_NAME!r} is not importable in this environment")

    all_diffs: list[str] = []
    for name in BMAD_LOOP_SKILL_NAMES:
        installed = pkg_dir / "data" / "skills" / name
        repo = REPO_ROOT / ".claude" / "skills" / name
        # Collect missing-dir cases as diffs rather than asserting inline, so
        # one skill's missing dir never hides an already-collected divergence
        # for another, and every one of the three is always checked.
        if not installed.is_dir():
            all_diffs.append(
                f"{name}: installed {PACKAGE_NAME} package has no "
                f"data/skills/{name}/ -- the package's layout changed; "
                "update this test's scope"
            )
            continue
        if not repo.is_dir():
            all_diffs.append(f"{name}: repo skill dir missing: {repo}")
            continue
        all_diffs += [f"{name}: {d}" for d in diff_dirs(installed, repo)]

    assert not all_diffs, (
        "repo bmad-loop-* skill dirs have drifted from the installed "
        f"{PACKAGE_NAME} package's own data/skills/ canon:\n  "
        + "\n  ".join(all_diffs)
        + "\n\nRe-copy the drifted file(s) from the installed package, or "
        "re-run `bmad-loop init --project <project-root> --cli claude "
        "--force-skills` (bmad-loop-setup's upgrade refresh) so the repo "
        "copies match again."
    )


@pytest.mark.meta
def test_diff_dirs_detects_a_planted_one_line_divergence(tmp_path):
    """Red-on-plant proof: the diff logic itself catches a one-line change.

    Uses two small synthetic trees -- never the real skill dirs -- so the
    guard's own correctness is proven independent of what happens to be
    installed in the environment running this suite.
    """
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    for d in (dir_a, dir_b):
        (d / "sub").mkdir(parents=True)
        (d / "SKILL.md").write_text("# A skill\n\nUnchanged line.\n", encoding="utf-8")
        (d / "sub" / "helper.py").write_text("value = 1\n", encoding="utf-8")

    assert diff_dirs(dir_a, dir_b) == []

    # Plant a one-line divergence in a nested file.
    (dir_b / "sub" / "helper.py").write_text("value = 2\n", encoding="utf-8")

    diffs = diff_dirs(dir_a, dir_b)
    expected_rel = Path("sub") / "helper.py"
    assert diffs == [f"content differs: {expected_rel}"], (
        f"diff_dirs failed to report the planted divergence; got {diffs!r}"
    )


@pytest.mark.meta
def test_diff_dirs_detects_file_set_mismatch(tmp_path):
    """The diff also catches a file added to, or missing from, one side."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "only_a.md").write_text("only in a\n", encoding="utf-8")
    (dir_b / "only_b.md").write_text("only in b\n", encoding="utf-8")

    diffs = diff_dirs(dir_a, dir_b)
    assert f"only in {dir_a}: only_a.md" in diffs
    assert f"only in {dir_b}: only_b.md" in diffs


@pytest.mark.meta
def test_find_installed_package_dir_is_none_when_unresolvable(monkeypatch):
    """The skip path's precondition: an unresolvable spec yields None.

    Proves the real-tree test's `pytest.skip` branch is reachable, without
    requiring an environment that actually lacks `bmad_loop`.
    """
    monkeypatch.setattr(importlib.util, "find_spec", lambda *_a, **_kw: None)
    assert find_installed_package_dir() is None


@pytest.mark.meta
def test_find_installed_package_dir_uses_origin_fallback(monkeypatch, tmp_path):
    """The `spec.origin`-parent fallback branch, exercised directly.

    A spec with no `submodule_search_locations` but a real `origin` is an
    edge case `find_spec` can genuinely return (e.g. a single-file module);
    this proves that branch -- otherwise unreached by any other test in this
    file -- resolves to `origin`'s parent directory.
    """
    fake_origin = tmp_path / "somewhere" / "bmad_loop.py"
    fake_origin.parent.mkdir(parents=True)
    fake_origin.write_text("", encoding="utf-8")

    class _FakeSpec:
        submodule_search_locations = None
        origin = str(fake_origin)

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_a, **_kw: _FakeSpec())
    assert find_installed_package_dir() == fake_origin.parent
