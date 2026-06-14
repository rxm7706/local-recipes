"""v8.22.0 wrapper-split structural fix for `_step_cf_atlas`.

The legacy single-subprocess `cf-atlas-build` invocation surfaced a
false-negative when the wrapper timed out before the Python subprocess
finished. v8.22.0 splits the step into 4 sub-steps (core / F / K / N),
each with its own timeout + independent ✓/✗ reporting:

  * cf-atlas-core — all phases EXCEPT F/K/N. HARD failure aborts the
    bootstrap before F/K/N run.
  * cf-atlas-F — Phase F only. SOFT failure (report + continue).
  * cf-atlas-K — Phase K only. SOFT failure.
  * cf-atlas-N — Phase N only. SOFT failure; runs only when gh enabled.

The legacy escape hatch is preserved: setting
`BOOTSTRAP_CF_ATLAS_TIMEOUT` explicitly restores the single-subprocess
invocation.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bootstrap_mod():
    return _load("bootstrap_data")


def _scrub(monkeypatch):
    """Clear the v8.22.0 per-step timeout env vars + the legacy escape
    hatch so each test starts from a known state."""
    for k in (
        "BOOTSTRAP_CF_ATLAS_TIMEOUT",
        "BOOTSTRAP_CF_ATLAS_CORE_TIMEOUT",
        "BOOTSTRAP_CF_ATLAS_F_TIMEOUT",
        "BOOTSTRAP_CF_ATLAS_K_TIMEOUT",
        "BOOTSTRAP_CF_ATLAS_N_TIMEOUT",
    ):
        monkeypatch.delenv(k, raising=False)


class TestPerStepTimeoutDefaults:
    """v8.22.0 — every new sub-step has a sane default + env-override."""

    def test_core_default_is_thirty_minutes(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        assert bootstrap_mod._timeout_for("cf_atlas_core") == 1800

    def test_phase_f_default_is_two_hours(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        assert bootstrap_mod._timeout_for("cf_atlas_F") == 7200

    def test_phase_k_default_is_two_hours(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        assert bootstrap_mod._timeout_for("cf_atlas_K") == 7200

    def test_phase_n_default_is_one_hour(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        assert bootstrap_mod._timeout_for("cf_atlas_N") == 3600

    def test_each_sub_step_honours_env_override(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_CORE_TIMEOUT", "900")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_F_TIMEOUT", "1800")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_K_TIMEOUT", "1800")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_N_TIMEOUT", "1200")
        assert bootstrap_mod._timeout_for("cf_atlas_core") == 900
        assert bootstrap_mod._timeout_for("cf_atlas_F") == 1800
        assert bootstrap_mod._timeout_for("cf_atlas_K") == 1800
        assert bootstrap_mod._timeout_for("cf_atlas_N") == 1200

    def test_legacy_cf_atlas_timeout_unchanged(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        # The legacy single-subprocess wrapper timeout default is preserved
        # so explicit BOOTSTRAP_CF_ATLAS_TIMEOUT operators are unaffected.
        assert bootstrap_mod._DEFAULT_TIMEOUTS["cf_atlas"] == 14400


class TestSubStepOrchestrator:
    """v8.22.0 — `_step_cf_atlas_split` calls the right argv with the
    right env, in the right order, with the right failure semantics."""

    def _record_calls(self, monkeypatch, bootstrap_mod, *, rcs=None):
        """Replace `_run_cf_atlas_subprocess` with a recorder. `rcs` is
        a dict {step_label: bool} dictating the simulated outcome of
        each sub-step (default: every step succeeds)."""
        rcs = rcs or {}
        calls: list[dict] = []

        def fake(
            only_phases,
            skip_phases,
            timeout,
            step_label,
            description,
            env_overrides,
            dry_run=False,
        ):
            calls.append({
                "only": list(only_phases) if only_phases else None,
                "skip": list(skip_phases) if skip_phases else None,
                "timeout": timeout,
                "step_label": step_label,
                "env": dict(env_overrides),
                "dry_run": dry_run,
            })
            return rcs.get(step_label, True)

        monkeypatch.setattr(
            bootstrap_mod, "_run_cf_atlas_subprocess", fake,
        )
        return calls

    def test_cf_atlas_core_failure_aborts_before_f_k_n(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(
            monkeypatch, bootstrap_mod,
            rcs={"cf-atlas-core": False},
        )
        results = bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=True,
            phase_n_maintainer=None,
            dry_run=False,
        )
        # Only the core sub-step was invoked — F/K/N never ran.
        assert [c["step_label"] for c in calls] == ["cf-atlas-core"]
        assert results == [("cf-atlas-core", False)]

    def test_cf_atlas_F_failure_continues_to_K_and_N(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(
            monkeypatch, bootstrap_mod,
            rcs={"cf-atlas-F": False},
        )
        results = bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=True,
            phase_n_maintainer=None,
            dry_run=False,
        )
        # All 4 sub-steps were invoked despite F's soft failure.
        labels = [c["step_label"] for c in calls]
        assert labels == ["cf-atlas-core", "cf-atlas-F", "cf-atlas-K", "cf-atlas-N"]
        # F is reported as failed; the rest succeeded.
        assert ("cf-atlas-core", True) in results
        assert ("cf-atlas-F", False) in results
        assert ("cf-atlas-K", True) in results
        assert ("cf-atlas-N", True) in results

    def test_cf_atlas_skip_arg_passed_to_core_subprocess(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=False,
            phase_n_maintainer=None,
            dry_run=False,
        )
        core = next(c for c in calls if c["step_label"] == "cf-atlas-core")
        # Core sub-step excludes F/K/N via --skip.
        assert core["skip"] == ["F", "K", "N"]
        assert core["only"] is None

    def test_cf_atlas_only_arg_passed_to_f_subprocess(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=False,
            phase_n_maintainer=None,
            dry_run=False,
        )
        f_step = next(c for c in calls if c["step_label"] == "cf-atlas-F")
        assert f_step["only"] == ["F"]
        assert f_step["skip"] is None

    def test_phase_n_skipped_when_gh_disabled(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        results = bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=False,
            phase_n_maintainer=None,
            dry_run=False,
        )
        labels = [c["step_label"] for c in calls]
        assert labels == ["cf-atlas-core", "cf-atlas-F", "cf-atlas-K"]
        assert all(label != "cf-atlas-N" for label, _ in results)

    def test_phase_n_maintainer_forwarded_to_env(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=True,
            phase_n_maintainer="rxm7706",
            dry_run=False,
        )
        n_step = next(c for c in calls if c["step_label"] == "cf-atlas-N")
        assert n_step["env"].get("PHASE_N_MAINTAINER") == "rxm7706"
        assert n_step["env"].get("PHASE_N_ENABLED") == "1"

    def test_phase_h_source_forwarded_to_every_substep(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        bootstrap_mod._step_cf_atlas_split(
            phase_h="cf-graph",
            gh_enabled=True,
            phase_n_maintainer=None,
            dry_run=False,
        )
        # Every sub-step inherits PHASE_E_ENABLED + PHASE_H_SOURCE.
        for c in calls:
            assert c["env"].get("PHASE_E_ENABLED") == "1"
            assert c["env"].get("PHASE_H_SOURCE") == "cf-graph"

    def test_sub_step_timeouts_picked_from_per_step_envs(
        self, monkeypatch, bootstrap_mod,
    ):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_CORE_TIMEOUT", "900")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_F_TIMEOUT", "1800")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_K_TIMEOUT", "1800")
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_N_TIMEOUT", "1200")
        calls = self._record_calls(monkeypatch, bootstrap_mod)
        bootstrap_mod._step_cf_atlas_split(
            phase_h="pypi-json",
            gh_enabled=True,
            phase_n_maintainer=None,
            dry_run=False,
        )
        timeouts = {c["step_label"]: c["timeout"] for c in calls}
        assert timeouts["cf-atlas-core"] == 900
        assert timeouts["cf-atlas-F"] == 1800
        assert timeouts["cf-atlas-K"] == 1800
        assert timeouts["cf-atlas-N"] == 1200


class TestLegacyEscapeHatch:
    """v8.22.0 — setting BOOTSTRAP_CF_ATLAS_TIMEOUT restores the
    single-subprocess monolithic invocation (operator escape hatch)."""

    def test_legacy_env_drives_main_step4_to_single_invocation(
        self, monkeypatch, bootstrap_mod, capsys,
    ):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_TIMEOUT", "14400")
        # Stub `_run` so the test never shells out to pixi.
        recorded: list[dict] = []

        def fake_run(label, cmd, env_overrides=None, dry_run=False, timeout=1800):
            recorded.append({
                "label": label,
                "cmd": list(cmd),
                "timeout": timeout,
                "env": dict(env_overrides) if env_overrides else {},
            })
            return True

        monkeypatch.setattr(bootstrap_mod, "_run", fake_run)

        # Stub the split helper too — it must NOT be called under the
        # legacy escape hatch. If it is, the test fails loudly.
        split_called = False

        def fake_split(**_kw):
            nonlocal split_called
            split_called = True
            return []

        monkeypatch.setattr(
            bootstrap_mod, "_step_cf_atlas_split", fake_split,
        )

        # Invoke main() with arguments that trigger only Step 4.
        monkeypatch.setattr(
            sys, "argv",
            ["bootstrap_data.py", "--no-vdb", "--no-cve-db",
             "--no-mapping", "--dry-run"],
        )
        rc = bootstrap_mod.main()
        assert rc == 0
        # Split helper was NOT called.
        assert split_called is False
        # The cf_atlas step was invoked as a single monolithic call
        # with the legacy timeout.
        cf_atlas_calls = [
            r for r in recorded
            if "cf_atlas" in r["label"] or "cf-atlas" in r["label"]
        ]
        assert len(cf_atlas_calls) == 1
        assert cf_atlas_calls[0]["timeout"] == 14400
        # No `--skip` / `--only` appended to the legacy invocation.
        assert "--skip" not in cf_atlas_calls[0]["cmd"]
        assert "--only" not in cf_atlas_calls[0]["cmd"]
        _ = capsys.readouterr()  # drain banner output

    def test_split_path_used_by_default_when_no_legacy_env(
        self, monkeypatch, bootstrap_mod, capsys,
    ):
        _scrub(monkeypatch)
        # No BOOTSTRAP_CF_ATLAS_TIMEOUT set — should use the split path.
        recorded_run: list[str] = []

        def fake_run(label, cmd, env_overrides=None, dry_run=False, timeout=1800):
            recorded_run.append(label)
            return True

        monkeypatch.setattr(bootstrap_mod, "_run", fake_run)

        split_called = False

        def fake_split(**_kw):
            nonlocal split_called
            split_called = True
            return [
                ("cf-atlas-core", True),
                ("cf-atlas-F", True),
                ("cf-atlas-K", True),
            ]

        monkeypatch.setattr(
            bootstrap_mod, "_step_cf_atlas_split", fake_split,
        )
        monkeypatch.setattr(
            sys, "argv",
            ["bootstrap_data.py", "--no-vdb", "--no-cve-db",
             "--no-mapping", "--dry-run"],
        )
        rc = bootstrap_mod.main()
        assert rc == 0
        assert split_called is True
        _ = capsys.readouterr()


class TestSubprocessHelper:
    """`_run_cf_atlas_subprocess` builds argv correctly + forwards to
    `_run` with the right keyword args."""

    def test_only_phases_emits_only_flag(self, monkeypatch, bootstrap_mod):
        captured: list[list[str]] = []

        def fake_run(label, cmd, env_overrides=None, dry_run=False, timeout=1800):
            captured.append(list(cmd))
            return True

        monkeypatch.setattr(bootstrap_mod, "_run", fake_run)
        bootstrap_mod._run_cf_atlas_subprocess(
            only_phases=["F"],
            skip_phases=None,
            timeout=7200,
            step_label="cf-atlas-F",
            description="Phase F",
            env_overrides={"PHASE_E_ENABLED": "1"},
        )
        assert captured == [[
            "pixi", "run", "-e", "local-recipes", "build-cf-atlas",
            "--", "--only", "F",
        ]]

    def test_skip_phases_emits_skip_flag(self, monkeypatch, bootstrap_mod):
        captured: list[list[str]] = []

        def fake_run(label, cmd, env_overrides=None, dry_run=False, timeout=1800):
            captured.append(list(cmd))
            return True

        monkeypatch.setattr(bootstrap_mod, "_run", fake_run)
        bootstrap_mod._run_cf_atlas_subprocess(
            only_phases=None,
            skip_phases=["F", "K", "N"],
            timeout=1800,
            step_label="cf-atlas-core",
            description="Core",
            env_overrides={"PHASE_E_ENABLED": "1"},
        )
        assert captured == [[
            "pixi", "run", "-e", "local-recipes", "build-cf-atlas",
            "--", "--skip", "F,K,N",
        ]]

    def test_both_arrays_raises_value_error(self, monkeypatch, bootstrap_mod):
        monkeypatch.setattr(
            bootstrap_mod, "_run",
            lambda *a, **kw: True,
        )
        with pytest.raises(ValueError, match="mutually exclusive"):
            bootstrap_mod._run_cf_atlas_subprocess(
                only_phases=["F"],
                skip_phases=["K"],
                timeout=1800,
                step_label="invalid",
                description="invalid",
                env_overrides={},
            )
