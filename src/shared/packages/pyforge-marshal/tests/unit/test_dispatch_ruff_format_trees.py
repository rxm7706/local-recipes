"""Story 95.1: pre-verify ruff grouped by each tree's ``[tool.ruff]`` table."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from pyforge.marshal.core.dispatch_cfe_commit import CFE_SURFACE_PREFIXES
from pyforge.marshal.core.dispatch_ruff_format import (
    DispatchRuffFormatResult,
    apply_dispatch_ruff_format_before_verify,
)
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

_MARSHAL_PKG = Path(__file__).resolve().parents[2]
_REPO_ROOT = _MARSHAL_PKG.parents[3]
_PLATFORM_ROOT = _REPO_ROOT / "src/platform"
_MARSHAL_STORY_PY = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/sample.py"
_PLATFORM_PROBE = "src/platform/tests/test_probe.py"
_PORTAL_FIXTURE_ROOT = "src/shared/packages/django-fixture"
_PORTAL_STORY_PY = f"{_PORTAL_FIXTURE_ROOT}/src/django_fixture/views.py"

_PORTAL_PYPROJECT = """\
[project]
name = "django-fixture"

[tool.ruff]
target-version = "py312"
line-length = 120
extend-exclude = ["*/migrations/*.py"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
"""


class _FormatVcs:
    def __init__(self, *, scope: tuple[str, ...], head: tuple[str, ...]) -> None:
        self._scope = scope
        self._head = head
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root, worktree_path
        return self._head if base == "HEAD" else self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        self._head = ()
        return "abc123"


class _RecordingProcess:
    def __init__(self, vcs: _FormatVcs) -> None:
        self.vcs = vcs
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens: list[str], *, cwd: Path) -> ProcessResult:
        self.calls.append((tokens, cwd))
        if tokens[:3] == ["ruff", "check", "--fix"] or tokens[:2] == ["ruff", "format"]:
            self.vcs._head = self.vcs._scope
        return ProcessResult(0, "", "")


def _seed_platform_ac1(worktree: Path) -> None:
    platform = worktree / "src/platform"
    platform.mkdir(parents=True, exist_ok=True)
    shutil.copy(_PLATFORM_ROOT / "pyproject.toml", platform / "pyproject.toml")
    (platform / "tests").mkdir(parents=True, exist_ok=True)
    (platform / "tests/__init__.py").write_text("", encoding="utf-8")
    (platform / "tests/test_probe.py").write_text(
        "import json, os\n\n\nx = 1\n",
        encoding="utf-8",
    )
    marshal_pkg = worktree / "src/shared/packages/pyforge-marshal"
    marshal_pkg.mkdir(parents=True, exist_ok=True)
    shutil.copy(_MARSHAL_PKG / "pyproject.toml", marshal_pkg / "pyproject.toml")
    target = marshal_pkg / "src/pyforge/marshal/sample.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x=1\n", encoding="utf-8")


def test_ac1_platform_fixed_and_fake_call_order(tmp_path: Path, ruff_from_test_env: None) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    scope = (_PLATFORM_PROBE, _MARSHAL_STORY_PY)

    vcs = _FormatVcs(scope=scope, head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    assert len(process.calls) == 4
    platform_cwd = worktree / "src/platform"
    marshal_cwd = worktree / "src/shared/packages/pyforge-marshal"
    assert process.calls[0] == (["ruff", "check", "--fix", "--force-exclude", "tests/test_probe.py"], platform_cwd)
    assert process.calls[1][0][:2] == ["ruff", "format"]
    assert process.calls[1][1] == platform_cwd
    assert process.calls[2][1] == marshal_cwd
    assert process.calls[3][1] == marshal_cwd

    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=_DiskDirtyVcs(scope=(_PLATFORM_PROBE,), worktree=worktree),
        process=PosixProcess(),
    )
    assert _PLATFORM_PROBE in result.reformatted_paths
    assert result.committed is True
    check = PosixProcess().run(
        ["ruff", "check", "--select", "I001", "tests/test_probe.py"],
        cwd=worktree / "src/platform",
    )
    fmt = PosixProcess().run(
        ["ruff", "format", "--check", "tests/test_probe.py"],
        cwd=worktree / "src/platform",
    )
    assert check.returncode == 0
    assert fmt.returncode == 0


class _DiskDirtyVcs:
    def __init__(self, *, scope: tuple[str, ...], worktree: Path) -> None:
        self._scope = scope
        self._worktree = worktree
        self._baseline = {p: (worktree / p).read_bytes() for p in scope if (worktree / p).is_file()}
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root
        if base == "HEAD":
            dirty = [
                p
                for p in self._scope
                if (worktree_path / p).is_file() and (worktree_path / p).read_bytes() != self._baseline.get(p, b"")
            ]
            return tuple(sorted(dirty))
        return self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        for path in paths:
            rel = path.as_posix()
            self._baseline[rel] = (self._worktree / rel).read_bytes()
        return "abc123"


def test_ac2_portal_uses_py312_table(tmp_path: Path, ruff_from_test_env: None) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    portal_root = worktree / _PORTAL_FIXTURE_ROOT
    portal_root.mkdir(parents=True, exist_ok=True)
    (portal_root / "pyproject.toml").write_text(_PORTAL_PYPROJECT, encoding="utf-8")
    views = portal_root / "src/django_fixture/views.py"
    views.parent.mkdir(parents=True, exist_ok=True)
    views.write_text(
        "import json, os\n\n\ndef f():\n    try:\n        pass\n    except (ValueError, TypeError):\n        pass\n",
        encoding="utf-8",
    )

    vcs = _FormatVcs(scope=(_PORTAL_STORY_PY,), head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    portal_cwd = worktree / _PORTAL_FIXTURE_ROOT
    assert any(cwd == portal_cwd and "src/django_fixture/views.py" in tokens for tokens, cwd in process.calls)

    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=_DiskDirtyVcs(scope=(_PORTAL_STORY_PY,), worktree=worktree),
        process=PosixProcess(),
    )
    text = views.read_text(encoding="utf-8")
    assert "except (ValueError, TypeError):" in text
    check = PosixProcess().run(
        ["ruff", "check", "--select", "I001", "src/django_fixture/views.py"],
        cwd=portal_cwd,
    )
    assert check.returncode == 0


def test_ac3_paths_without_table_or_cfe_or_deleted_unchanged(tmp_path: Path, ruff_from_test_env: None) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    no_ruff_pkg = worktree / "src/shared/packages/django-bare"
    no_ruff_pkg.mkdir(parents=True)
    (no_ruff_pkg / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    bare_py = no_ruff_pkg / "src/x.py"
    bare_py.parent.mkdir(parents=True)
    original_bare = "import json, os\n\nx=1\n"
    bare_py.write_text(original_bare, encoding="utf-8")
    script = worktree / "scripts/tool.py"
    script.parent.mkdir(parents=True)
    original_script = "import json, os\n\nx=1\n"
    script.write_text(original_script, encoding="utf-8")
    cfe_path = f"{CFE_SURFACE_PREFIXES[0]}probe.py"
    cfe_full = worktree / cfe_path
    cfe_full.parent.mkdir(parents=True, exist_ok=True)
    original_cfe = "import json, os\n\nx=1\n"
    cfe_full.write_text(original_cfe, encoding="utf-8")
    deleted = "src/shared/packages/django-bare/src/deleted.py"

    scope = (
        str(bare_py.relative_to(worktree)),
        str(script.relative_to(worktree)),
        cfe_path,
        deleted,
    )
    vcs = _FormatVcs(scope=scope, head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    assert process.calls == []
    assert bare_py.read_text(encoding="utf-8") == original_bare
    assert script.read_text(encoding="utf-8") == original_script
    assert cfe_full.read_text(encoding="utf-8") == original_cfe


def test_ac4_out_of_scope_file_untouched(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    other = worktree / "src/platform/tests/test_other.py"
    other.write_text("x=1\n\n\n", encoding="utf-8")
    dirty_before = other.read_bytes()
    vcs = _FormatVcs(scope=(_PLATFORM_PROBE,), head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    for tokens, _cwd in process.calls:
        assert "." not in tokens
        assert all(not t.startswith("src/platform/tests/test_other") for t in tokens)
    assert other.read_bytes() == dirty_before


class _FailFirstCheckProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path]] = []
        self._count = 0

    def run(self, tokens: list[str], *, cwd: Path) -> ProcessResult:
        self.calls.append((tokens, cwd))
        if tokens[:3] == ["ruff", "check", "--fix"]:
            self._count += 1
            if self._count == 1:
                raise ProcessError(["ruff"], 1, "", "")
        return ProcessResult(0, "", "")


def test_ac5_group_failure_does_not_stop_second_group(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    scope = (_PLATFORM_PROBE, _MARSHAL_STORY_PY)
    vcs = _FormatVcs(scope=scope, head=())
    process = _FailFirstCheckProcess()
    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    assert len(result.groups) == 2
    assert result.groups[0].ok is False
    assert result.groups[0].failed_step == "check"
    assert result.groups[1].ok is True
    assert not any(tokens[:2] == ["ruff", "format"] and cwd.name == "platform" for tokens, cwd in process.calls)


def test_ac5_journal_when_only_group_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    loop_tests._patch_verification(monkeypatch, loop_tests._clean_envelope)
    from pyforge.marshal.core.dispatch_ruff_format import DispatchRuffFormatGroupResult

    failed = DispatchRuffFormatResult(
        (),
        False,
        (
            DispatchRuffFormatGroupResult(
                root="src/platform",
                files=(_PLATFORM_PROBE,),
                changed_paths=(),
                ok=False,
                failed_step="check",
                exit_code=2,
            ),
        ),
    )
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_ruff_format_before_verify",
        lambda **_: failed,
    )
    fs = loop_tests.FakeFs()
    counter = loop_tests._verify(fs, repo_root, worktree)
    assert counter == 4
    payloads = []
    for _path, line, _ in fs.appended:
        if "dispatch-ruff-format" in line and "outcome" in line:
            payloads.append(json.loads(line))
    assert payloads
    assert payloads[-1]["payload"]["committed"] is False
    assert payloads[-1]["payload"]["groups"][0]["ok"] is False


def test_ac7_unsafe_findings_remain(tmp_path: Path, ruff_from_test_env: None) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    bad = worktree / _PLATFORM_PROBE
    bad.write_text(
        'LONG = "'
        + ("x" * 90)
        + '"\n\n\ndef compute():\n    return 1\n\n\ndef g():\n    value = compute()\n    return value\n\n\ndef h():\n    import sys\n    return sys\n',
        encoding="utf-8",
    )
    vcs = _FormatVcs(scope=(_PLATFORM_PROBE,), head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    for tokens, _ in process.calls:
        assert "--unsafe-fixes" not in tokens
    check = PosixProcess().run(
        ["ruff", "check", "--select", "E501,RET504,PLC0415", "tests/test_probe.py"],
        cwd=worktree / "src/platform",
    )
    assert check.returncode != 0


def test_ac8_migration_excluded_with_force_exclude(tmp_path: Path, ruff_from_test_env: None) -> None:
    worktree = tmp_path / "wt"
    _seed_platform_ac1(worktree)
    mig = worktree / "src/platform/app/migrations/0001_initial.py"
    mig.parent.mkdir(parents=True, exist_ok=True)
    original = "import json, os\n\nx=1\n"
    mig.write_text(original, encoding="utf-8")
    scope = (_PLATFORM_PROBE, str(mig.relative_to(worktree)))
    before = mig.read_text(encoding="utf-8")
    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=_DiskDirtyVcs(scope=scope, worktree=worktree),
        process=PosixProcess(),
    )
    assert mig.read_text(encoding="utf-8") == before
    assert str(mig.relative_to(worktree)) not in result.reformatted_paths

    marshal_mig = (
        worktree / "src/shared/packages/pyforge-marshal/src/pyforge/marshal/dashboard/migrations/0001_initial.py"
    )
    marshal_mig.parent.mkdir(parents=True, exist_ok=True)
    marshal_mig.write_text(original, encoding="utf-8")
    mscope = (_MARSHAL_STORY_PY, str(marshal_mig.relative_to(worktree)))
    mbefore = marshal_mig.read_text(encoding="utf-8")
    result2 = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=_DiskDirtyVcs(scope=mscope, worktree=worktree),
        process=PosixProcess(),
    )
    assert marshal_mig.read_text(encoding="utf-8") == mbefore
    assert str(marshal_mig.relative_to(worktree)) not in result2.reformatted_paths

    vcs = _FormatVcs(scope=(_PLATFORM_PROBE,), head=())
    process = _RecordingProcess(vcs)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )
    assert process.calls[0][0][3] == "--force-exclude"

    minimal = worktree / "src/shared/packages/pyforge-minimal"
    minimal.mkdir(parents=True)
    (minimal / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    target = minimal / "src/x.py"
    target.parent.mkdir(parents=True)
    target.write_text("x=1\n", encoding="utf-8")
    rel = str(target.relative_to(worktree))
    vcs2 = _FormatVcs(scope=(rel,), head=())
    proc2 = _RecordingProcess(vcs2)
    apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs2,
        process=proc2,
    )
    assert "--force-exclude" not in proc2.calls[0][0]
