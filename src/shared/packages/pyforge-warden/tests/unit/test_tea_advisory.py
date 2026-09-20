"""Unit tests — ``tea-test-review`` is a warden advisory finding (Story 11.2).

Covers the intent-contract I/O matrix: a provisioned-but-unreachable TEA
(fail-open, no note, no error), an unprovisioned AD-9 roster (fail-CLOSED,
``TeaRosterMissingError`` -- AD-10, resolved 2026-09-07 per DW-FU-11-2), an
injected low-scoring runner (a note appears, ``compose()``'s output is
unaffected), and a runner that errors or returns unparsable output
(fail-open, identical to the provisioned-but-unreachable case). Never
invokes a real agent-backed ``tea-test-review`` run: the "binary absent"
scenario is exercised via a deterministic ``shutil.which`` monkeypatch (see
its own test's docstring for why — this repo's ambient dev shells can leak
an unrelated pixi environment's ``tea-test-review`` copy onto ``PATH``),
and every other scenario injects a fake ``runner`` that never shells out.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pyforge.core.hooks import PluginRegistry

from pyforge.warden import tea_advisory
from pyforge.warden.hooks import PR_GATE_SCAN, invoke_pr_gate
from pyforge.warden.scanner_plugins import OPTIONAL_SCANNER_IDS
from pyforge.warden.tea_advisory import (
    TeaAdvisoryResult,
    TeaAdvisoryScanPlugin,
    TeaRosterMissingError,
    run_tea_test_review,
)


def _write_tea_roster(target: Path) -> None:
    """Write a minimal AD-9 module roster naming ``tea`` as provisioned
    (``[modules.tea]``) -- what ``steward provision --module tea`` writes.
    Used by every test that means to exercise the "roster present, binary
    merely unreachable" fail-open case, as distinct from "roster lacks tea
    entirely" (fail-closed)."""
    config_dir = target / "_bmad" / "custom"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text('[modules.tea]\nversion = "1.0"\n', encoding="utf-8")


# --- run_tea_test_review: AD-9 roster lacks tea (fail-CLOSED, AD-10) -------


def test_roster_missing_raises_when_scanner_would_run(tmp_path):
    """The chosen resolution for DW-FU-11-2: a target with no AD-9 roster
    at all (never provisioned via ``steward provision --module tea``)
    raises ``TeaRosterMissingError`` -- a hard refusal, never a silent
    ``ran=False`` pass -- regardless of whether a binary happens to be on
    PATH (not stubbed here on purpose: the roster check must fire first)."""
    try:
        run_tea_test_review(tmp_path)
    except TeaRosterMissingError as exc:
        assert "modules.tea" in str(exc)
        assert "steward provision --module tea" in str(exc)
    else:
        raise AssertionError("expected TeaRosterMissingError, none raised")


def test_roster_present_but_empty_modules_table_still_refuses(tmp_path):
    """A ``_bmad/custom/config.toml`` that exists but whose ``[modules]``
    table has no ``tea`` key (some OTHER module was provisioned, not this
    one) is exactly "the AD-9 roster lacks tea" -- still a hard refusal,
    not fail-open."""
    config_dir = tmp_path / "_bmad" / "custom"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text('[modules.skf]\nversion = "1.0"\n', encoding="utf-8")

    try:
        run_tea_test_review(tmp_path)
    except TeaRosterMissingError:
        pass
    else:
        raise AssertionError("expected TeaRosterMissingError, none raised")


def test_roster_missing_never_calls_runner(tmp_path):
    """The roster check happens BEFORE any runner would be consulted --
    the default (``runner=None``) path raises before looking at PATH at
    all, mirroring the old presence-probe-is-the-gate pin one level up."""
    try:
        run_tea_test_review(tmp_path, runner=None)
    except TeaRosterMissingError:
        pass
    else:
        raise AssertionError("expected TeaRosterMissingError, none raised")


# --- run_tea_test_review: TEA provisioned but unreachable (fail-open) -----


def test_fail_open_when_binary_absent(monkeypatch, tmp_path):
    """Roster present (provisioned) but the binary is not on THIS
    process's PATH -- an environmental blip, not a governance gap (AD-10
    only governs the roster half). Deterministic monkeypatch, not ambient
    absence: this repo's dev shells can leak an unrelated pixi
    environment's ``tea-test-review`` copy onto ``PATH`` even inside a
    scoped ``pixi run -e pyforge-warden`` invocation (verified live), so
    relying on the pyforge-warden env's own (genuinely tea-less) dependency
    set alone would make this test environment-dependent."""
    _write_tea_roster(tmp_path)
    monkeypatch.setattr(tea_advisory.shutil, "which", lambda name: None)

    result = run_tea_test_review(tmp_path)

    assert result == TeaAdvisoryResult(
        ran=False,
        score=None,
        recommendation=None,
        summary="",
        skipped_reason="tea-test-review not found on PATH",
    )


def test_absent_binary_never_calls_runner(monkeypatch, tmp_path):
    """With the roster present, the presence probe happens BEFORE any
    runner would be consulted -- the default (``runner=None``) path never
    even looks at an injected runner because there isn't one; this pins
    that ``shutil.which`` is the gate, not an incidental side effect."""
    _write_tea_roster(tmp_path)
    monkeypatch.setattr(tea_advisory.shutil, "which", lambda name: None)

    result = run_tea_test_review(tmp_path, runner=None)

    assert result.ran is False


# --- run_tea_test_review: injected runner, low score ------------------------


def _write_verdict(json_path: Path, payload: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(payload), encoding="utf-8")


def test_injected_runner_reports_a_low_score(tmp_path):
    def fake_runner(target: Path, json_path: Path) -> None:
        assert target == tmp_path
        _write_verdict(
            json_path,
            {
                "recommendation": "Request Changes",
                "qualityScore": 40,
                "violations": {"critical": 0, "high": 2, "medium": 1, "low": 0},
            },
        )

    result = run_tea_test_review(tmp_path, runner=fake_runner)

    assert result.ran is True
    assert result.score == 40
    assert result.recommendation == "Request Changes"
    assert result.skipped_reason is None
    assert "score=40" in result.summary
    assert "recommendation=Request Changes" in result.summary
    assert "high=2" in result.summary


def test_injected_runner_reports_a_passing_score(tmp_path):
    def fake_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {
                "recommendation": "Approve",
                "qualityScore": 92,
                "violations": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            },
        )

    result = run_tea_test_review(tmp_path, runner=fake_runner)

    assert result.ran is True
    assert result.score == 92
    assert result.recommendation == "Approve"


# --- run_tea_test_review: runner errors (fail-open, like TEA absent) -------


def test_runner_that_raises_is_fail_open(tmp_path):
    def raising_runner(target: Path, json_path: Path) -> None:
        raise subprocess.TimeoutExpired(cmd="tea-test-review", timeout=1800)

    result = run_tea_test_review(tmp_path, runner=raising_runner)

    assert result.ran is False
    assert result.score is None
    assert result.recommendation is None
    assert "TimeoutExpired" in result.skipped_reason


def test_runner_that_writes_malformed_json_is_fail_open(tmp_path):
    def garbled_runner(target: Path, json_path: Path) -> None:
        json_path.write_text("not-json {{{", encoding="utf-8")

    result = run_tea_test_review(tmp_path, runner=garbled_runner)

    assert result.ran is False
    assert result.skipped_reason is not None


def test_runner_that_writes_nothing_is_fail_open(tmp_path):
    """A non-zero exit that leaves no ``--json`` output (the real CLI's
    exit 2/3 shape) degrades exactly like a runner exception -- opening the
    never-written file raises, which the same handler catches."""

    def no_op_runner(target: Path, json_path: Path) -> None:
        return None

    result = run_tea_test_review(tmp_path, runner=no_op_runner)

    assert result.ran is False
    assert result.skipped_reason is not None


def test_runner_that_writes_a_non_object_json_is_fail_open(tmp_path):
    def list_runner(target: Path, json_path: Path) -> None:
        json_path.write_text("[]", encoding="utf-8")

    result = run_tea_test_review(tmp_path, runner=list_runner)

    assert result.ran is False


def test_skipped_verdict_is_fail_open_not_a_score(tmp_path):
    """The real CLI's own documented shape for "no changed test files" --
    treated as nothing-to-report, exactly like TEA absent."""

    def skipped_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {
                "skipped": True,
                "reason": "no changed test files in diff",
                "recommendation": None,
                "qualityScore": None,
            },
        )

    result = run_tea_test_review(tmp_path, runner=skipped_runner)

    assert result.ran is False
    assert result.score is None
    assert result.skipped_reason == "no changed test files in diff"


# --- run_tea_test_review: a NaN qualityScore never raises -------------------


def test_injected_runner_with_nan_score_does_not_raise(tmp_path):
    """``json.load`` parses a literal ``NaN``/``Infinity`` ``qualityScore``
    as a Python float; ``int(float('nan'))`` raises ``ValueError`` --
    verified live. The score parsing must degrade to ``score=None``, never
    escape ``run_tea_test_review``'s own documented "never raises"
    contract."""

    def nan_score_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {"recommendation": "Approve", "qualityScore": float("nan")},
        )

    result = run_tea_test_review(tmp_path, runner=nan_score_runner)

    assert result.ran is True
    assert result.score is None
    assert result.recommendation == "Approve"


# --- run_tea_test_review: the runner's exit code gates trust -----------------


def test_injected_runner_exit_1_with_valid_json_is_still_trusted(tmp_path):
    """``test-review.js``'s own documented semantics: exit 1 is a
    legitimate "verdict fail" (a real score below ``--min-score``), never a
    generic subprocess failure -- this story's own acceptance criterion
    requires it stays trusted (``ran=True``, real score/recommendation)."""

    def exit_1_runner(target: Path, json_path: Path) -> subprocess.CompletedProcess[str]:
        _write_verdict(
            json_path,
            {
                "recommendation": "Request Changes",
                "qualityScore": 40,
                "violations": {},
            },
        )
        return subprocess.CompletedProcess(args=["tea-test-review"], returncode=1, stdout="", stderr="")

    result = run_tea_test_review(tmp_path, runner=exit_1_runner)

    assert result.ran is True
    assert result.score == 40
    assert result.recommendation == "Request Changes"


def test_injected_runner_exit_2_with_valid_json_is_fail_open(tmp_path):
    """Only an exit code outside ``{0, 1}`` is untrusted/fail-open --
    defense in depth (the real ``tea-test-review`` binary today never
    leaves a JSON file behind on a genuine error exit, but this must
    degrade even when one happens to exist at ``json_path``)."""

    def exit_2_runner(target: Path, json_path: Path) -> subprocess.CompletedProcess[str]:
        _write_verdict(json_path, {"recommendation": "Approve", "qualityScore": 92})
        return subprocess.CompletedProcess(args=["tea-test-review"], returncode=2, stdout="", stderr="")

    result = run_tea_test_review(tmp_path, runner=exit_2_runner)

    assert result.ran is False
    assert result.score is None
    assert result.skipped_reason is not None


# --- TeaAdvisoryScanPlugin: optional-only registration ----------------------


def test_scanner_id_is_registered_optional_and_never_default():
    assert "tea-test-review" in OPTIONAL_SCANNER_IDS
    plugin = TeaAdvisoryScanPlugin()
    assert plugin.is_default is False
    assert plugin.scanner_id == "tea-test-review"
    assert plugin.hook_spec == PR_GATE_SCAN.name


# --- TeaAdvisoryScanPlugin: disabled by default -----------------------------


def test_disabled_plugin_contributes_nothing_and_never_calls_runner(tmp_path):
    def exploding_runner(target: Path, json_path: Path) -> None:
        raise AssertionError("must not be called while disabled")

    plugin = TeaAdvisoryScanPlugin(runner=exploding_runner)
    context: dict[str, Any] = {
        "enabled_optional": (),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    plugin.call("around", context)

    assert context["advisory_notes"] == []
    assert context["plugin_findings"] == []


# --- TeaAdvisoryScanPlugin: enabled, contributes an advisory note only -----


def test_enabled_plugin_with_low_score_runner_adds_advisory_note_only(tmp_path):
    def fake_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {"recommendation": "Request Changes", "qualityScore": 40, "violations": {}},
        )

    plugin = TeaAdvisoryScanPlugin(runner=fake_runner)
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    plugin.call("around", context)

    assert context["plugin_findings"] == []
    assert len(context["advisory_notes"]) == 1
    note = context["advisory_notes"][0]
    assert note == {
        "tool": "tea-test-review",
        "score": 40,
        "recommendation": "Request Changes",
        "summary": note["summary"],  # asserted in detail in run_tea_test_review tests
    }


def test_enabled_plugin_runner_error_never_propagates_and_adds_no_note(tmp_path):
    def raising_runner(target: Path, json_path: Path) -> None:
        raise RuntimeError("forced failure")

    plugin = TeaAdvisoryScanPlugin(runner=raising_runner)
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    plugin.call("around", context)  # must not raise

    assert context["advisory_notes"] == []
    assert context["plugin_findings"] == []


def test_enabled_plugin_absent_binary_contributes_nothing(monkeypatch, tmp_path):
    """Roster present (provisioned), binary merely unreachable -- fail-open,
    contributes nothing. Distinct from the roster-missing case below, which
    must raise instead."""
    _write_tea_roster(tmp_path)
    monkeypatch.setattr(tea_advisory.shutil, "which", lambda name: None)
    plugin = TeaAdvisoryScanPlugin()  # no runner injected: real presence probe
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    plugin.call("around", context)

    assert context["advisory_notes"] == []


def test_enabled_plugin_roster_missing_raises_not_fail_open(tmp_path):
    """DW-FU-11-2 / AD-10, at the plugin boundary: unlike every other
    runner/parse/binary problem, ``TeaRosterMissingError`` is NOT absorbed
    by ``_contribute``'s belt-and-suspenders fail-open net -- it escapes
    ``call()`` too, so a genuinely unprovisioned AD-9 roster cannot pass
    through this plugin silently. No runner injected -- production shape
    (real roster/PATH resolution); the roster check gates before any
    runner (real or injected) would ever be consulted."""
    plugin = TeaAdvisoryScanPlugin()
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    try:
        plugin.call("around", context)
    except TeaRosterMissingError:
        pass
    else:
        raise AssertionError("expected TeaRosterMissingError, none raised")

    assert context["advisory_notes"] == []
    assert context["plugin_findings"] == []


def test_enabled_plugin_with_no_target_in_context_is_fail_open():
    def exploding_runner(target: Path, json_path: Path) -> None:
        raise AssertionError("must not be called with no target")

    plugin = TeaAdvisoryScanPlugin(runner=exploding_runner)
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
    }

    plugin.call("around", context)

    assert context.get("advisory_notes") == []


# --- PluginRegistry: compose() is unaffected regardless of the plugin ------


def test_registry_invoke_with_low_score_leaves_plugin_findings_empty(tmp_path):
    """Mirrors ``tests/unit/test_hooks.py``'s direct ``invoke_pr_gate``
    pattern. ``plugin_findings`` is the ONLY channel that ever reaches
    ``compose()`` (via ``findings_from_plugin_context`` ->
    ``merge_plugin_findings`` -> policy rungs); proving it stays empty
    here -- with the plugin registered, enabled, AND reporting a failing
    score -- proves ``compose()``'s output cannot differ whether or not
    this plugin ran."""

    def fake_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {
                "recommendation": "Request Changes",
                "qualityScore": 40,
                "violations": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            },
        )

    registry = PluginRegistry()
    registry.register(TeaAdvisoryScanPlugin(runner=fake_runner))
    context: dict[str, Any] = {
        "enabled_optional": ("tea-test-review",),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    invoke_pr_gate(PR_GATE_SCAN, "around", context, registry=registry)

    assert context["plugin_findings"] == []
    assert len(context["advisory_notes"]) == 1
    assert context["advisory_notes"][0]["score"] == 40


def test_registry_invoke_without_enabling_leaves_both_channels_empty(tmp_path):
    registry = PluginRegistry()
    registry.register(TeaAdvisoryScanPlugin())
    context: dict[str, Any] = {
        "enabled_optional": (),
        "plugin_findings": [],
        "advisory_notes": [],
        "target": tmp_path,
    }

    invoke_pr_gate(PR_GATE_SCAN, "around", context, registry=registry)

    assert context["plugin_findings"] == []
    assert context["advisory_notes"] == []


# --- Full CLI pipeline: the acceptance criterion, end to end ---------------


def test_full_scan_with_low_scoring_advisory_leaves_verdict_byte_identical(monkeypatch, tmp_path, capsys):
    """Acceptance criterion: with ``TeaAdvisoryScanPlugin`` enabled and an
    injected runner reporting a score below its ``--min-score``, the
    PR-gate scan/aggregate/verdict pipeline's composed status, findings,
    and exit code are identical to a baseline run without the plugin
    registered at all -- only the additive ``advisory`` key differs."""
    import pyforge.warden.scanner_plugins as scanner_plugins_module
    from pyforge.warden.cli import main
    from pyforge.warden.engines import engine_factories
    from pyforge.warden.scanner_plugins import _plugin_for_factory

    def _defaults_only_registry() -> PluginRegistry:
        registry = PluginRegistry()
        for factory in engine_factories():
            registry.register(_plugin_for_factory(factory))
        return registry

    def fake_low_score_runner(target: Path, json_path: Path) -> None:
        _write_verdict(
            json_path,
            {
                "recommendation": "Request Changes",
                "qualityScore": 40,
                "violations": {"critical": 0, "high": 2, "medium": 1, "low": 0},
            },
        )

    def _tea_registry() -> PluginRegistry:
        registry = _defaults_only_registry()
        registry.register(TeaAdvisoryScanPlugin(runner=fake_low_score_runner))
        return registry

    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    monkeypatch.setattr(scanner_plugins_module, "scanner_plugin_registry", _defaults_only_registry)
    rc_baseline = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    baseline = json.loads(capsys.readouterr().out)

    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "tea-test-review")
    monkeypatch.setattr(scanner_plugins_module, "scanner_plugin_registry", _tea_registry)
    rc_tea = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    with_tea = json.loads(capsys.readouterr().out)

    assert rc_baseline == rc_tea
    assert baseline.get("advisory") is None
    assert with_tea["advisory"] is not None
    assert len(with_tea["advisory"]) == 1
    assert with_tea["advisory"][0]["score"] == 40
    assert with_tea["advisory"][0]["recommendation"] == "Request Changes"
    for key in baseline:
        if key == "advisory":
            continue
        assert with_tea[key] == baseline[key], f"{key!r} differs with tea enabled"


def test_full_scan_with_roster_missing_refuses_not_a_silent_pass(monkeypatch, tmp_path, capsys):
    """DW-FU-11-2's end-to-end proof: enabling ``tea-test-review`` via
    ``WARDEN_OPTIONAL_SCANNERS`` against a target with NO AD-9 roster at
    all (``tmp_path`` has no ``_bmad`` directory -- ``steward provision
    --module tea`` never ran) must refuse loudly -- a real
    ``config-validation`` error rung, a report that still names the
    refusal, and an exit code distinct from the same scan with the
    scanner left disabled. It must NOT silently pass through as if the
    scanner had contributed nothing."""
    import pyforge.warden.scanner_plugins as scanner_plugins_module
    from pyforge.warden.cli import main
    from pyforge.warden.engines import engine_factories
    from pyforge.warden.scanner_plugins import _plugin_for_factory

    def _defaults_only_registry() -> PluginRegistry:
        registry = PluginRegistry()
        for factory in engine_factories():
            registry.register(_plugin_for_factory(factory))
        return registry

    def _tea_registry() -> PluginRegistry:
        registry = _defaults_only_registry()
        registry.register(TeaAdvisoryScanPlugin())  # no runner: real roster probe
        return registry

    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    monkeypatch.setattr(scanner_plugins_module, "scanner_plugin_registry", _defaults_only_registry)
    rc_baseline = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    baseline = json.loads(capsys.readouterr().out)

    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "tea-test-review")
    monkeypatch.setattr(scanner_plugins_module, "scanner_plugin_registry", _tea_registry)
    rc_refused = main(["scan", str(tmp_path), "--format", "json", "--allow-empty"])
    refused = json.loads(capsys.readouterr().out)

    assert not any(e["owner"] == "tea-test-review" for e in baseline["errors"]), (
        "sanity: the scanner-disabled baseline records no tea-test-review error"
    )
    assert rc_refused != rc_baseline, (
        "a missing AD-9 roster must change the exit code -- a silent pass would leave it identical to the baseline"
    )
    tea_errors = [e for e in refused["errors"] if e["owner"] == "tea-test-review"]
    assert len(tea_errors) == 1, (
        f"expected exactly one recorded tea-test-review error, found {tea_errors!r} in {refused['errors']!r}"
    )
    assert tea_errors[0]["kind"] == "config-validation"
    assert "modules.tea" in tea_errors[0]["message"]
    assert "steward provision --module tea" in tea_errors[0]["message"]
    assert refused.get("advisory") is None, (
        "a refusal contributes no advisory note -- distinguishing it from the ordinary scored-finding path"
    )


# --- Story 52.1, SPEC-pyforge-core CAP-5: the re-parent widening guard ----


def test_tea_roster_missing_error_is_a_pyforge_error_and_a_runtime_error():
    """``TeaRosterMissingError`` gained ``PyforgeError`` as an additional
    base and kept its original ``RuntimeError`` base -- the exact-class
    ``except TeaRosterMissingError`` sites (``_contribute``'s deliberate
    re-raise, ``cli.py``'s ``CONFIG_VALIDATION`` mapping) and any ``except
    RuntimeError`` site behave identically; ``except PyforgeError`` newly
    catches it too."""
    from pyforge.core.errors import PyforgeError

    assert issubclass(TeaRosterMissingError, PyforgeError)
    assert issubclass(TeaRosterMissingError, RuntimeError)
    for catch in (TeaRosterMissingError, RuntimeError, PyforgeError):
        try:
            raise TeaRosterMissingError("roster lacks tea")
        except catch:
            pass
