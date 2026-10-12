"""Story 96.1: collapse repeated story-spec frontmatter keys before verify."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core.dispatch_spec_frontmatter import (
    SPEC_FRONTMATTER_GATE_CODE,
    DispatchSpecFrontmatterResult,
    _split_story_spec,
    _top_level_key_line_map,
    apply_dispatch_spec_frontmatter_before_verify,
    collapse_story_spec_frontmatter_text,
    findings_for_spec_frontmatter_refusals,
    is_tracked_story_spec_path,
    story_spec_paths_in_changed,
)
from pyforge.marshal.core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

_REPO_ROOT = Path(__file__).resolve().parents[6]


class _DupLoader(yaml.SafeLoader):
    pass


def _dup_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[object, object]:
    out: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in out:
            found = getattr(loader, "dup_keys", None)
            if found is None:
                found = set()
                loader.dup_keys = found
            found.add(str(key))
        out[key] = loader.construct_object(value_node)
    return out


_DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_mapping)


def _story_spec_frontmatter_dup_keys(text: str) -> set[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    try:
        loader = _DupLoader("\n".join(block))
        loader.get_single_data()
    except yaml.YAMLError:
        return {"<unreadable>"}
    return set(getattr(loader, "dup_keys", set()))


def test_is_tracked_story_spec_path() -> None:
    rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-96-1-x.md"
    assert is_tracked_story_spec_path(rel)
    assert not is_tracked_story_spec_path("docs/dreams/x.md")


def test_story_spec_paths_in_changed_scopes_to_story_specs() -> None:
    paths = story_spec_paths_in_changed(
        (
            "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-a.md",
            "src/foo.py",
        )
    )
    assert paths == ("_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-a.md",)


def test_tracked_story_specs_carry_each_top_level_frontmatter_key_once() -> None:
    files = [
        p
        for p in subprocess.check_output(["git", "-C", str(_REPO_ROOT), "ls-files"], text=True).splitlines()
        if "/planning-artifacts/specs/spec-" in p and p.endswith(".md")
    ]
    offenders: list[tuple[str, list[str]]] = []
    for rel in files:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        split = _split_story_spec(text)
        if split is None:
            continue
        _o, close_idx, _body = split
        fm = text.splitlines(keepends=True)[1:close_idx]
        repeats = [k for k, v in _top_level_key_line_map(fm).items() if len(v) > 1]
        if repeats:
            offenders.append((rel, repeats))
    assert not offenders, offenders[:5]


def test_herald_shape_keeps_newer_true() -> None:
    text = (
        "---\n"
        "title: t\n"
        "followup_review_recommended: true\n"
        "followup_review_recommended: false\n"
        "status: done\n"
        "---\n\nbody\n"
    )
    blame = {
        3: ("b" * 40, 200),
        4: ("a" * 40, 100),
    }
    new_text, refusals, keys = collapse_story_spec_frontmatter_text(
        text,
        blame=blame,
        tiebreak_same_commit="refuse",
    )
    assert not refusals
    assert new_text is not None
    assert "followup_review_recommended: true\n" in new_text
    assert new_text.count("followup_review_recommended:") == 1
    assert keys == ("followup_review_recommended",)


def test_doctor_shape_keeps_newer_one(tmp_path: Path) -> None:
    spec_dir = tmp_path / "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs"
    spec_dir.mkdir(parents=True)
    rel = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-test.md"
    spec_path = spec_dir / "spec-test.md"
    spec_path.write_text(
        "---\ntitle: t\nreview_loop_iteration: 0\nstatus: done\n---\n\nbody\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    spec_path.write_text(
        "---\ntitle: t\nreview_loop_iteration: 0\nreview_loop_iteration: 1\nstatus: done\n---\n\nbody\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", spec_path], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "dup"], cwd=tmp_path, check=True, capture_output=True)
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=tmp_path, path=rel, worktree=tmp_path)
    new_text, refusals, _keys = collapse_story_spec_frontmatter_text(
        spec_path.read_text(encoding="utf-8"),
        blame=blame,
    )
    assert not refusals and new_text is not None
    assert "review_loop_iteration: 1\n" in new_text


def test_ambiguous_same_commit_refuses(tmp_path: Path) -> None:
    spec_dir = tmp_path / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
    spec_dir.mkdir(parents=True)
    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-test.md"
    spec_path = spec_dir / "spec-test.md"
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    spec_path.write_text(
        "---\ntitle: t\nreview_loop_iteration: 1\nreview_loop_iteration: 0\nstatus: done\n---\n\nbody\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "both"], cwd=tmp_path, check=True, capture_output=True)
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=tmp_path, path=rel, worktree=tmp_path)
    new_text, refusals, _ = collapse_story_spec_frontmatter_text(
        spec_path.read_text(encoding="utf-8"),
        blame=blame,
        tiebreak_same_commit="refuse",
    )
    assert new_text is None
    assert refusals
    findings = findings_for_spec_frontmatter_refusals(
        (type(refusals[0])(spec_path=rel, key=refusals[0].key, reason=refusals[0].reason),)
    )
    assert findings[0].code == SPEC_FRONTMATTER_GATE_CODE
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=findings)) == DispatchVerificationVerdict.REFUSED
    )


def test_equal_values_collapse_to_one_line(tmp_path: Path) -> None:
    spec_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs"
    spec_dir.mkdir(parents=True)
    rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-test.md"
    spec_path = spec_dir / "spec-test.md"
    text = (
        "---\n"
        "title: t\n"
        "review_loop_iteration: 0\n"
        "followup_review_recommended: false\n"
        "review_loop_iteration: 0\n"
        "followup_review_recommended: false\n"
        "status: done\n"
        "---\n\nbody unchanged\n"
    )
    spec_path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "dup"], cwd=tmp_path, check=True, capture_output=True)
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=tmp_path, path=rel, worktree=tmp_path)
    new_text, refusals, _ = collapse_story_spec_frontmatter_text(
        text,
        blame=blame,
    )
    assert not refusals and new_text is not None
    assert new_text.endswith("body unchanged\n")
    assert new_text.count("review_loop_iteration:") == 1


class _CollapseVcs:
    def __init__(self, *, scope: tuple[str, ...], blame: dict[int, tuple[str, int]] | None = None) -> None:
        self._scope = scope
        self._blame = blame or {}
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root, worktree_path, base
        return self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        return "abc"

    def line_blame_facts(self, **kwargs: object) -> dict[int, tuple[str, int]]:
        del kwargs
        return self._blame


def test_apply_commits_when_story_spec_changed(tmp_path: Path) -> None:
    rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-x.md"
    spec_dir = tmp_path / "wt" / rel
    spec_dir.parent.mkdir(parents=True, exist_ok=True)
    spec_dir.write_text(
        "---\ntitle: t\nreview_loop_iteration: 0\nreview_loop_iteration: 1\nstatus: done\n---\n\n",
        encoding="utf-8",
    )
    vcs = _CollapseVcs(
        scope=(rel,),
        blame={3: ("a" * 40, 1), 4: ("b" * 40, 2)},
    )
    result = apply_dispatch_spec_frontmatter_before_verify(
        worktree=tmp_path / "wt",
        repo_root=tmp_path,
        vcs=vcs,
        blame_vcs=vcs,
    )
    assert result.committed
    assert rel in result.committed_paths


def test_apply_skips_when_no_story_spec_in_diff(tmp_path: Path) -> None:
    vcs = _CollapseVcs(scope=("README.md",))
    result = apply_dispatch_spec_frontmatter_before_verify(
        worktree=tmp_path,
        repo_root=tmp_path,
        vcs=vcs,
        blame_vcs=vcs,
    )
    assert result == DispatchSpecFrontmatterResult((), (), (), False)


def test_verification_journals_spec_frontmatter_when_collapsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    loop_tests._patch_verification(monkeypatch, loop_tests._clean_envelope)
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_spec_frontmatter_before_verify",
        lambda **_: DispatchSpecFrontmatterResult((("spec.md", "review_loop_iteration"),), ("spec.md",), (), True),
    )
    fs = loop_tests.FakeFs()
    counter = loop_tests._verify(fs, repo_root, worktree)
    assert counter >= 2
    assert any("dispatch-spec-frontmatter" in line for _, line, _ in fs.appended)


def test_mutation_without_pre_verify_call_fails_ac2(tmp_path: Path) -> None:
    """AC8: removing the pre-verify call leaves a repeat in place (fixture shape)."""
    spec_dir = tmp_path / "_bmad-output/projects/pyforge-herald/planning-artifacts/specs"
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "spec-test.md"
    spec_path.write_text(
        "---\nfollowup_review_recommended: true\nfollowup_review_recommended: false\n---\n",
        encoding="utf-8",
    )
    assert len(_story_spec_frontmatter_dup_keys(spec_path.read_text(encoding="utf-8"))) == 1
