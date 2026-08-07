"""Unit tests for ``pyforge.marshal.cli.check`` (Story 5.6, FR-65/AD-50).
Covers every row of the spec's own I/O & Edge-Case Matrix via a
hand-written ``_FakeProcess`` (never a mock) mirroring
``tests/unit/test_status.py``'s own established fake-port style for
``_gather_unpushed_work_findings``.
"""

from __future__ import annotations

import argparse
import json

from pyforge.marshal.adapters.process_posix import ProcessError
from pyforge.marshal.cli import check as check_cli
from pyforge.marshal.core import policy as policy_core
from pyforge.marshal.core.context import MarshalContext
from pyforge.marshal.ports.process import ProcessResult


class _FakeProcess:
    """Records every ``run`` call and returns a canned
    ``ProcessResult`` (or raises ``ProcessError``) -- mirrors
    ``tests/unit/test_status.py::_FakeProcess``'s identical shape for
    ``ProcessPort.run``."""

    def __init__(
        self,
        *,
        run_result: ProcessResult | None = None,
        run_raises: bool = False,
    ) -> None:
        self.run_calls: list[tuple[tuple[str, ...], object, float | None]] = []
        self.run_result = run_result
        self.run_raises = run_raises

    def run(self, argv, *, cwd, timeout_s=None):
        self.run_calls.append((tuple(argv), cwd, timeout_s))
        if self.run_raises:
            raise ProcessError("cannot launch the detector registry")
        if self.run_result is not None:
            return self.run_result
        return ProcessResult(
            returncode=0,
            stdout=json.dumps({"registry": [], "results": []}),
            stderr="",
        )


def _args(*, scope: str = "all", project: str | None = None, format: str = "json"):
    return argparse.Namespace(scope=scope, project=project, format=format)


def _payload(capsys):
    return json.loads(capsys.readouterr().out)


def _detector(name: str, status: str, summary: str = "") -> dict[str, object]:
    return {
        "path": f"scripts/{name}.py",
        "name": name,
        "scope": "repo",
        "task": name,
        "rc": 0,
        "status": status,
        "secs": 0.1,
        "summary": summary,
    }


def test_clean_repo_is_a_clean_verdict(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {"registry": [], "results": [_detector("dream_chain_check", "pass")]}
            ),
            stderr="",
        )
    )
    exit_code = check_cli.run_check(_args(), process=process)

    assert exit_code == 0
    payload = _payload(capsys)
    assert payload["verdict"] == "clean"
    assert payload["data"]["results"] == [_detector("dream_chain_check", "pass")]
    assert payload["findings"] == []


def test_a_detector_reporting_findings_registers_mrs_check_002(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=1,
            stdout=json.dumps(
                {
                    "registry": [],
                    "results": [_detector("check_layout", "FINDINGS", "3 files affected")],
                }
            ),
            stderr="",
        )
    )
    exit_code = check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert payload["verdict"] == "error"
    codes = [f["code"] for f in payload["findings"]]
    assert codes == ["MRS-CHECK-002"]
    assert "check_layout" in payload["findings"][0]["message"]
    assert exit_code != 0


def test_a_detector_reporting_unknown_registers_mrs_check_004_unevaluable(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=2,
            stdout=json.dumps(
                {"registry": [], "results": [_detector("flaky_check", "unknown")]}
            ),
            stderr="",
        )
    )
    check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert payload["verdict"] == "unevaluable"
    assert [f["code"] for f in payload["findings"]] == ["MRS-CHECK-004"]


def test_a_registry_gap_registers_mrs_check_003(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=1,
            stdout=json.dumps(
                {
                    "registry": ["scripts/new_check.py: declares no valid scope"],
                    "results": [],
                }
            ),
            stderr="",
        )
    )
    check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert payload["verdict"] == "error"
    assert [f["code"] for f in payload["findings"]] == ["MRS-CHECK-003"]
    assert "new_check.py" in payload["findings"][0]["message"]


def test_scope_flag_passes_through_1_to_1_to_the_underlying_script(capsys):
    process = _FakeProcess()
    check_cli.run_check(_args(scope="runtime"), process=process)

    argv, _cwd, _timeout = process.run_calls[0]
    assert "--scope" in argv
    assert argv[argv.index("--scope") + 1] == "runtime"


def test_subprocess_launch_failure_registers_mrs_check_001_warn_never_fabricated_clean(
    capsys,
):
    process = _FakeProcess(run_raises=True)
    exit_code = check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert [f["code"] for f in payload["findings"]] == ["MRS-CHECK-001"]
    assert payload["findings"][0]["severity"] == "warn"
    # WARN -- reported, never silently treated as a clean sweep.
    assert payload["data"]["results"] == []
    assert exit_code == 0


def test_unparseable_json_output_registers_mrs_check_001(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(returncode=0, stdout="not json", stderr="")
    )
    check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert [f["code"] for f in payload["findings"]] == ["MRS-CHECK-001"]


def test_malformed_json_shape_registers_mrs_check_001(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=0, stdout=json.dumps({"unexpected": "shape"}), stderr=""
        )
    )
    check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    assert [f["code"] for f in payload["findings"]] == ["MRS-CHECK-001"]


def test_unrecognized_entry_status_registers_mrs_check_001_never_silently_clean(capsys):
    """Code review (2026-08-07, Edge Case Hunter): a missing/None/
    unrecognized per-entry `status` (not one of pass/FINDINGS/unknown)
    previously fell through every branch with NO finding raised -- folded
    in as if it were `"pass"`, contradicting this module's own repeated
    "malformed is reported, never silently clean" discipline."""
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {
                    "registry": [],
                    "results": [_detector("some_check", "totally-unrecognized-status")],
                }
            ),
            stderr="",
        )
    )
    exit_code = check_cli.run_check(_args(), process=process)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-CHECK-001" in codes
    # WARN-tier -- reported, never fabricated clean, but non-blocking (the
    # SAME tier `_unavailable_finding`'s own MRS-CHECK-001 already uses).
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_text_format_never_crashes_on_null_status_or_name(capsys):
    """Code review (2026-08-07, Edge Case Hunter): `.get(key, default)`
    only substitutes when the key is ABSENT, not when it's `null` --
    `f"{None:9}"` raises `TypeError`, an unhandled crash out of `marshal
    check`'s own DEFAULT (text) output format."""
    entry = _detector("some_check", "pass")
    entry["status"] = None
    entry["name"] = None
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=0,
            stdout=json.dumps({"registry": [], "results": [entry]}),
            stderr="",
        )
    )

    exit_code = check_cli.run_check(_args(format="text"), process=process)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "?" in out


def test_format_json_and_text_carry_the_same_data(capsys):
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {"registry": [], "results": [_detector("dream_chain_check", "pass")]}
            ),
            stderr="",
        )
    )
    check_cli.run_check(_args(format="json"), process=process)
    json_payload = _payload(capsys)

    process2 = _FakeProcess(
        run_result=ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {"registry": [], "results": [_detector("dream_chain_check", "pass")]}
            ),
            stderr="",
        )
    )
    check_cli.run_check(_args(format="text"), process=process2)
    text_out = capsys.readouterr().out

    assert "dream_chain_check" in text_out
    assert json_payload["data"]["results"][0]["name"] == "dream_chain_check"


def test_project_falls_back_to_args_project_when_no_context_supplied(capsys):
    process = _FakeProcess()
    check_cli.run_check(_args(project="acme"), process=process)

    payload = _payload(capsys)
    assert payload["data"]["project"] == "acme"


def test_context_slug_is_the_primary_source_when_supplied(capsys):
    process = _FakeProcess()
    effective, _findings = policy_core.compose(project_slug="acme", project={}, flags={})
    context = MarshalContext(slug="acme", loop_home=None, policy=effective, story=None)

    check_cli.run_check(_args(project="ignored-because-context-wins"), process=process, context=context)

    payload = _payload(capsys)
    assert payload["data"]["project"] == "acme"


def test_registered_codes_are_all_registered():
    from pyforge.marshal.core.findings import REGISTERED_CODES

    for code in ("MRS-CHECK-001", "MRS-CHECK-002", "MRS-CHECK-003", "MRS-CHECK-004"):
        assert code in REGISTERED_CODES
