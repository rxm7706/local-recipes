"""`provision --runner bmad-loop` is RETIRED — Story 5.1 (AD-5, Marshal AD-71).

Story 3.2 built `run_bmad_loop_worktree`, a subprocess wrap of the LEGACY
`scripts/bmad-loop-worktree`. `marshal init` is a strict superset of it, so two
stations shipped two ways to make the same thing and one was the weaker one.

This file replaces that story's tests: it no longer proves the wrap works, it
proves the wrap is GONE and that nothing provisions silently in its place. The
old tests are deleted rather than skipped — a retirement whose tests still
assert the old behaviour is a deprecation, not a removal.
"""

from __future__ import annotations

import argparse
import subprocess

from pyforge.steward import provision as provision_mod
from pyforge.steward.cli import EXIT_FAILED, main
from pyforge.steward.provision import ProvisionDuty

_PIXI_TOML = """\
[environments]
pyforge-steward = { features = ["pyforge-steward"], no-default-feature = true }
"""


def _write_repo_fixture(tmp_path):
    (tmp_path / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "bmad-loop-worktree").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return tmp_path


def _ns(**kw):
    base = dict(runner=None, env=None, list=False, verify=False)
    base.update(kw)
    return argparse.Namespace(**base)


# --- the retirement itself ---------------------------------------------------


def test_the_legacy_worktree_wrapper_is_gone_not_merely_unused():
    """`run_bmad_loop_worktree` is deleted from the module surface. Leaving it
    importable would keep the second provisioning path one call away, which is
    exactly the duplication Story 5.1 removes."""
    assert not hasattr(provision_mod, "run_bmad_loop_worktree")


def test_runner_reports_and_names_marshal_init_instead_of_provisioning(monkeypatch):
    """The AC's hard requirement: never silently provisions via the legacy
    script. It must FAIL and name the supported path."""
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))  # noqa: ARG005

    result = ProvisionDuty().run(_ns(runner="bmad-loop", env="pyforge-steward"))

    assert result.ok is False
    assert "RETIRED" in result.summary
    assert "marshal init pyforge-steward" in result.summary
    assert calls == [], "the retired path still shelled out to a subprocess"


def test_runner_names_the_slug_it_was_given():
    """The remedy has to be copy-pasteable, so it carries the operator's own
    slug rather than a placeholder."""
    result = ProvisionDuty().run(_ns(runner="bmad-loop", env="pyforge-doctor"))
    assert "marshal init pyforge-doctor" in result.summary


def test_runner_without_env_reports_rather_than_crashing():
    """`--runner` with no `--env` used to be a usage error raised before any
    work happened. It must still report, not raise."""
    result = ProvisionDuty().run(_ns(runner="bmad-loop"))
    assert result.ok is False
    assert "marshal init <slug>" in result.summary


def test_runner_exits_failed_through_the_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(_write_repo_fixture(tmp_path))
    assert main(["provision", "--runner", "bmad-loop", "--env", "pyforge-steward"]) == EXIT_FAILED


def test_unsupported_runner_name_still_reports_a_clear_error():
    result = ProvisionDuty().run(_ns(runner="not-bmad-loop", env="pyforge-steward"))
    assert result.ok is False
    assert "not-bmad-loop" in result.summary


# --- the half that is genuinely Steward's, and must be unaffected ------------


def test_env_only_provisioning_is_untouched(tmp_path, monkeypatch):
    """`--env <name>` materializes a pixi environment — Steward's own job, and
    explicitly out of scope for the retirement."""
    root = _write_repo_fixture(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)
    seen = {}
    monkeypatch.setattr(
        provision_mod, "materialize_environment", lambda name, cwd=None: seen.update(name=name, cwd=cwd)
    )

    result = ProvisionDuty().run(_ns(env="pyforge-steward"))

    assert result.ok is True
    assert seen["name"] == "pyforge-steward"


def test_env_only_still_rejects_an_unknown_environment(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)

    result = ProvisionDuty().run(_ns(env="not-a-real-env"))

    assert result.ok is False
    assert "not a valid pixi environment" in result.summary
