"""Regression guard for DW-2-10-2: recipe_updater.py's bare "python" subprocess call.

Found during the pyforge-mason effort (Story 2.10, Blind Hunter review,
2026-08-12) and flagged for this closing CFE retrospective, since AD-15
forbade a Mason-side fix: `update_recipe`'s real-write path spawned
`["python", ...]` — a bare PATH lookup — while its sibling
`github_updater.py` resolved the interpreter for the identical internal call
to `recipe_editor.py`. An environment with only `python3` on PATH (no
`python` alias) would fail this call.

All four call sites now resolve `sys.executable` FIRST. `CONDA_PYTHON_EXE` is
not the activated environment's interpreter — conda sets it to the interpreter
of the conda installation itself (`context.py` writes `sys.executable` next to
`_CONDA_ROOT`, exported once by the shell hook; `conda activate <env>` never
re-exports it). Preferring it therefore ran the child under BASE python, which
need not have the parser this env has — surfacing as a misleading
"ruamel.yaml is not installed" on a machine where it plainly is.
"""
from __future__ import annotations

import inspect
import subprocess
import sys

import pytest


class TestRecipeUpdaterInterpreterResolution:
    def test_real_write_path_invokes_recipe_editor_with_resolved_interpreter(
        self, load_module, tmp_path, monkeypatch
    ):
        """Behavioral guard: drive `update_recipe`'s real (non-dry-run) write
        path end-to-end and capture the actual subprocess.run argv — a plain
        string-match on the source (the original form of this test) would
        pass even if the fix were later reformatted away without the bug
        actually returning, and would also miss a regression that kept the
        string "CONDA_PYTHON_EXE" somewhere but stopped using its resolved
        value as argv[0]."""
        # `recipe_updater.py` treats ruamel.yaml as OPTIONAL (it keeps a
        # RUAMEL_AVAILABLE flag); this test drives the parse path, so without
        # the guard a lean env fails here with a bare `assert False is True`
        # that reports an interpreter-resolution regression when the real
        # cause is a missing parser.
        pytest.importorskip("ruamel.yaml")
        updater = load_module("recipe_updater.py")

        recipe_path = tmp_path / "recipe.yaml"
        recipe_path.write_text(
            "context:\n  name: examplepkg\n  version: \"1.0.0\"\n"
        )

        monkeypatch.setattr(updater, "get_latest_pypi_version", lambda name: "2.0.0")
        monkeypatch.delenv("CONDA_PYTHON_EXE", raising=False)

        captured_cmd = {}

        class _FakeCompletedProcess:
            returncode = 0
            stderr = ""

        def _fake_run(cmd, **kwargs):
            captured_cmd["cmd"] = cmd
            return _FakeCompletedProcess()

        # recipe_updater.update_recipe does a function-local `import subprocess`,
        # which binds to the SAME cached module object as this test's own
        # top-level `import subprocess` — patching that object's `run` here
        # is visible to the function's local import too.
        monkeypatch.setattr(subprocess, "run", _fake_run)

        result = updater.update_recipe(recipe_path, dry_run=False)

        assert result["success"] is True
        assert "cmd" in captured_cmd, "the real-write path never reached subprocess.run"
        assert captured_cmd["cmd"][0] == sys.executable
        assert captured_cmd["cmd"][0] != "python"

    def test_conda_python_exe_does_not_override_the_running_interpreter(
        self, load_module, tmp_path, monkeypatch
    ):
        """`CONDA_PYTHON_EXE` names conda's OWN (base) interpreter, not the
        activated env's, so it must not win over `sys.executable` — the child
        would otherwise run under a python that need not have this env's
        dependencies. The sibling behavioural test deletes the variable, so
        this is the branch that actually exercises the precedence."""
        pytest.importorskip("ruamel.yaml")
        updater = load_module("recipe_updater.py")

        recipe_path = tmp_path / "recipe.yaml"
        recipe_path.write_text(
            "context:\n  name: examplepkg\n  version: \"1.0.0\"\n"
        )
        monkeypatch.setattr(updater, "get_latest_pypi_version", lambda name: "2.0.0")
        monkeypatch.setenv("CONDA_PYTHON_EXE", "/opt/conda/bin/python")

        captured_cmd = {}

        class _FakeCompletedProcess:
            returncode = 0
            stderr = ""

        def _fake_run(cmd, **kwargs):
            captured_cmd["cmd"] = cmd
            return _FakeCompletedProcess()

        monkeypatch.setattr(subprocess, "run", _fake_run)

        result = updater.update_recipe(recipe_path, dry_run=False)

        assert result["success"] is True
        assert captured_cmd["cmd"][0] == sys.executable
        assert captured_cmd["cmd"][0] != "/opt/conda/bin/python"

    def test_all_internal_recipe_editor_callers_agree_on_resolution_pattern(
        self, load_module
    ):
        """Drift guard across every in-skill caller, not just the two the
        original DW-2-10-2 finding named — `npm_updater.py` and
        `recipe-generator.py` make the same internal call and had the same
        precedence."""
        pattern = 'sys.executable or os.environ.get("CONDA_PYTHON_EXE") or "python"'
        for module in (
            "recipe_updater.py",
            "github_updater.py",
            "npm_updater.py",
            "recipe-generator.py",
        ):
            source = inspect.getsource(load_module(module))
            assert pattern in source, f"{module} diverged from the resolution pattern"
