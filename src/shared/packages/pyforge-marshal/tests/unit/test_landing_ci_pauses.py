"""Story 100.1 (CAP-292): CI pause surfaces recorded at dispatch landing merge time."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.process import ProcessError, ProcessResult
from pyforge.testing_kit.flags import flag_states

from pyforge.marshal.adapters.steward_cli import StewardCli
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.journal import CI_PAUSES_AT_MERGE_FIELD
from pyforge.marshal.core.landing_checks import CheckRun
from pyforge.marshal.core.landing_ci_pauses import (
    LANDING_CI_PAUSES_FLAG_KEY,
    append_ci_pauses_line_to_pr_body,
    record_from_envelope,
    render_ci_pauses_pr_line,
    row_counts_as_paused_at_merge,
    surfaces_from_envelope,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.model import Severity
from pyforge.marshal.dispatch_land import _dispatch_pr_body, execute_dispatch_land
from pyforge.marshal.ports.forge import ForgeCommandError

def _load_dispatch_landing_harness():
    path = Path(__file__).with_name("test_dispatch_landing.py")
    spec = importlib.util.spec_from_file_location("_dispatch_landing_harness", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lh = _load_dispatch_landing_harness()
FakeProcess = _lh.FakeProcess
FakeVcs = _lh.FakeVcs
_FakeClock = _lh._FakeClock
_ChecksForge = _lh._ChecksForge
_GREEN = _lh._GREEN
_install_fake_spec_surface = _lh._install_fake_spec_surface

_FLAG = LANDING_CI_PAUSES_FLAG_KEY


def _install_flag_tree(repo_root: Path, *, enabled: bool) -> None:
    config_dir = repo_root / "src/platform/config"
    config_dir.mkdir(parents=True, exist_ok=True)
    variant = "on" if enabled else "off"
    (config_dir / "flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    _FLAG: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _land_with_ci_pauses(
    tmp_path: Path,
    forge: _ChecksForge,
    clock: _FakeClock,
    monkeypatch,
    *,
    process: FakeProcess | None = None,
):
    proc = process if process is not None else FakeProcess()
    _install_fake_spec_surface(monkeypatch, (), process=proc)
    worktree = tmp_path / "wt"
    worktree.mkdir(exist_ok=True)
    effective, findings = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    assert findings == ()
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="80-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=FakeVcs(merged=False),
        forge=forge,
        process=proc,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def _sample_envelope() -> dict[str, Any]:
    return {
        "fetched_at": "2026-10-14T12:00:00Z",
        "repo": "rxm7706/local-recipes",
        "rate_limit": {"core_limit": 5000, "core_remaining": 4999},
        "rows": [
            {"id": "platform-ci.container", "declared_state": "paused", "live_switch_value": "true", "verdict": "paused"},
            {
                "id": "platform-ci.container-dbgpt",
                "declared_state": "paused",
                "live_switch_value": "true",
                "verdict": "overdue",
            },
            {
                "id": "station-tests.guild-container",
                "declared_state": "paused",
                "live_switch_value": "true",
                "verdict": "paused",
            },
            {"id": "wf.manual", "declared_state": "paused-manually", "live_switch_value": None, "verdict": "paused-manually"},
            {"id": "opt.in", "declared_state": "opt-in-off", "live_switch_value": "true", "verdict": "opt-in-off"},
            {"id": "platform-ci.registry", "declared_state": "live", "live_switch_value": "https://example", "verdict": "live"},
            {"id": "lint", "declared_state": "live", "live_switch_value": "false", "verdict": "live"},
            {"id": "unregistered:PAUSE_FOO", "declared_state": "drift", "live_switch_value": "true", "verdict": "drift"},
        ],
    }


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"id": "a", "declared_state": "paused", "live_switch_value": "true"}, True),
        ({"id": "b", "declared_state": "paused", "live_switch_value": "true", "verdict": "overdue"}, True),
        ({"id": "c", "declared_state": "paused-manually", "live_switch_value": None}, True),
        ({"id": "d", "declared_state": "opt-in-off", "live_switch_value": "true"}, False),
        ({"id": "e", "declared_state": "live", "live_switch_value": "https://x"}, False),
        ({"id": "f", "declared_state": "retired", "live_switch_value": "true"}, False),
        ({"id": "unregistered:X", "declared_state": "drift", "live_switch_value": "true"}, False),
        ({"id": "g", "declared_state": "live", "live_switch_value": "TRUE "}, True),
    ],
)
def test_row_listing_rule(row: dict[str, Any], expected: bool) -> None:
    assert row_counts_as_paused_at_merge(row) is expected


def test_ac1_envelope_produces_sorted_four_paused_surfaces() -> None:
    record = record_from_envelope(_sample_envelope())
    assert record == {
        "state": "read",
        "surfaces": [
            "platform-ci.container",
            "platform-ci.container-dbgpt",
            "station-tests.guild-container",
            "wf.manual",
        ],
        "fetched_at": "2026-10-14T12:00:00Z",
    }


def test_ac2_empty_surfaces_and_pr_line() -> None:
    env = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"id": "lint", "declared_state": "live", "live_switch_value": "false", "verdict": "live"}],
    }
    record = record_from_envelope(env)
    assert record["surfaces"] == []
    assert render_ci_pauses_pr_line(record) == "CI paused at merge: none"


class _StewardProcess:
    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0, raise_timeout: bool = False):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.raise_timeout = raise_timeout

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None):
        if self.raise_timeout:
            raise ProcessError("timed out")
        return ProcessResult(returncode=self.returncode, stdout=self.stdout, stderr=self.stderr)


class _BodyRecordingForge(_ChecksForge):
    def __init__(self, *steps: object) -> None:
        super().__init__(*steps)
        self.bodies: list[str] = []

    def update_pr(self, repo, number, title, body):
        self.bodies.append(body.value if hasattr(body, "value") else str(body))
        return super().update_pr(repo, number, title, body)


@flag_states(_FLAG)
def test_ac7_flag_on_records_and_updates_pr_body(
    tmp_path: Path, monkeypatch, flag_provider: dict[str, bool]
) -> None:
    enabled = flag_provider[_FLAG]
    _install_flag_tree(tmp_path, enabled=enabled)
    sample = _sample_envelope()

    def _fake_record(self, **kwargs):
        if not enabled:
            raise AssertionError("steward must not run when flag off")
        return record_from_envelope(sample)

    monkeypatch.setattr("pyforge.marshal.dispatch_land.StewardCli.ci_status_record", _fake_record)
    forge = _BodyRecordingForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    base_text = _dispatch_pr_body(normalize("80-1-example")).text
    if enabled:
        assert envelope.data[CI_PAUSES_AT_MERGE_FIELD]["state"] == "read"
        assert len(envelope.data[CI_PAUSES_AT_MERGE_FIELD]["surfaces"]) == 4
        last_body = forge.bodies[-1]
        last_text = last_body.text if hasattr(last_body, "text") else last_body
        assert last_text == append_ci_pauses_line_to_pr_body(base_text, envelope.data[CI_PAUSES_AT_MERGE_FIELD])
    else:
        assert CI_PAUSES_AT_MERGE_FIELD not in envelope.data
        assert all(
            "CI paused at merge" not in (b.text if hasattr(b, "text") else b) for b in forge.bodies
        )


def test_ac3_unknown_on_steward_refusal_still_lands(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.StewardCli.ci_status_record",
        lambda self, **kwargs: {"state": "unknown", "reason": "steward ci status refused (exit 3): flag off"},
    )
    forge = _BodyRecordingForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data[CI_PAUSES_AT_MERGE_FIELD]["state"] == "unknown"
    last = forge.bodies[-1]
    assert "CI paused at merge: unknown" in (last.text if hasattr(last, "text") else last)


def test_ac4_update_pr_failure_warns_and_lands(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)

    class _FailUpdateForge(_BodyRecordingForge):
        def update_pr(self, repo, number, title, body):
            text = body.value if hasattr(body, "value") else str(body)
            if "CI paused at merge" in text:
                raise ForgeCommandError("rate limited")
            return super().update_pr(repo, number, title, body)

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.StewardCli.ci_status_record",
        lambda self, **kwargs: record_from_envelope(_sample_envelope()),
    )
    forge = _FailUpdateForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert any(f.code == "MRS-DISP-066" and f.severity is Severity.WARN for f in envelope.findings)


def test_ac5_check_refusal_skips_steward(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)
    calls: list[str] = []

    def _record(self, **kwargs):
        calls.append("steward")
        return record_from_envelope(_sample_envelope())

    monkeypatch.setattr("pyforge.marshal.dispatch_land.StewardCli.ci_status_record", _record)
    forge = _ChecksForge((CheckRun(name="Lint / ruff", status="completed", conclusion="failure"),))
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert calls == []
    assert CI_PAUSES_AT_MERGE_FIELD not in envelope.data


def test_steward_cli_unknown_paths() -> None:
    assert StewardCli(_StewardProcess()).ci_status_record(repo_root=Path("/tmp")).get("state") == "unknown"
    assert StewardCli(_StewardProcess(returncode=1, stderr="partial\n")).ci_status_record(repo_root=Path("/tmp"))[
        "state"
    ] == "unknown"
    assert StewardCli(_StewardProcess(stdout="not json")).ci_status_record(repo_root=Path("/tmp"))["state"] == "unknown"
    assert StewardCli(_StewardProcess(stdout="{}")).ci_status_record(repo_root=Path("/tmp"))["state"] == "unknown"


def test_finalize_ac6_invalid_json_becomes_unknown() -> None:
    from pyforge.marshal.dispatch_land_finalize.__main__ import _parse_ci_pauses_at_merge_arg

    parsed = _parse_ci_pauses_at_merge_arg("{not-json")
    assert parsed == {"state": "unknown", "reason": "finalize could not parse the landing's record"}


def test_surfaces_from_envelope_never_uses_verdict_alone() -> None:
    env = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"id": "x", "declared_state": "opt-in-off", "live_switch_value": "false", "verdict": "paused"}],
    }
    assert surfaces_from_envelope(env) == []
