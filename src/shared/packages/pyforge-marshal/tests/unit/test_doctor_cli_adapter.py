"""Story 115.2 (spec-pyforge-marshal CAP-261 (b)): ``adapters/doctor_cli.py`` reads Doctor's exit domain.

Doctor exits 0 when no spec-surface row FAILs and 2 when one does (``drift`` is a FAIL); argparse also
exits 2, with nothing on stdout. A JSON list on stdout is the verdict for exit 0 and exit 2; every other
shape is ``Unavailable``, and nothing raises.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from pyforge.marshal.adapters.doctor_cli import (
    BOOTSTRAP,
    DOCTOR_SOURCE_REL,
    SurfaceRow,
    Unavailable,
    Verdict,
    read_spec_surface,
    spec_surface_argv,
)

_DRIFT_ROW = {
    "source": "spec-surface",
    "check": "drift",
    "status": "fail",
    "message": "p/spec-a: src/a.py changed but the spec's memlog did not move — reconcile the spec, then "
    "--write-baseline --spec p/spec-a",
    "evidence": {"path": "src/a.py"},
}
_PRESUMED_ROW = {
    "source": "spec-surface",
    "check": "drift-presumed",
    "status": "warn",
    "message": "p/spec-a: src/b.py changed; the memlog moved but does not name this path — confirm it was "
    "reconciled, then --write-baseline --spec p/spec-a",
    "evidence": {"path": "src/b.py"},
}


class _ScriptedProcess:
    """A ``ProcessPort`` that answers with one result (or raises one ``ProcessError``) and records calls."""

    def __init__(self, answer: ProcessResult | ProcessError) -> None:
        self.answer = answer
        self.calls: list[tuple[list[str], Path, float | None]] = []

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.calls.append((list(argv), cwd, timeout_s))
        if isinstance(self.answer, ProcessError):
            raise self.answer
        return self.answer


def _read(tmp_path: Path, answer: ProcessResult | ProcessError) -> Verdict | Unavailable:
    return read_spec_surface(tmp_path, _ScriptedProcess(answer))


def test_the_argv_is_doctors_command_run_from_the_worktree_with_a_timeout(tmp_path: Path) -> None:
    process = _ScriptedProcess(ProcessResult(returncode=0, stdout="[]", stderr=""))

    read_spec_surface(tmp_path, process)

    assert process.calls == [([sys.executable, "-c", BOOTSTRAP, "spec-surface", "--json"], tmp_path, 300.0)]
    assert spec_surface_argv() == (sys.executable, "-c", BOOTSTRAP, "spec-surface", "--json")


def test_rc_0_with_a_json_list_is_the_verdict(tmp_path: Path) -> None:
    outcome = _read(tmp_path, ProcessResult(returncode=0, stdout=json.dumps([_PRESUMED_ROW]), stderr=""))

    assert isinstance(outcome, Verdict)
    assert outcome.returncode == 0
    assert outcome.rows == (
        SurfaceRow(check="drift-presumed", message=_PRESUMED_ROW["message"], evidence={"path": "src/b.py"}),
    )


def test_rc_0_with_an_empty_list_is_a_clean_verdict(tmp_path: Path) -> None:
    outcome = _read(tmp_path, ProcessResult(returncode=0, stdout="[]\n", stderr=""))

    assert outcome == Verdict(rows=(), returncode=0)


def test_rc_2_with_a_json_list_is_the_verdict(tmp_path: Path) -> None:
    """Doctor exits 2 on any FAIL row, and ``drift`` is a FAIL: the rows are the verdict, not a failure."""
    stdout = json.dumps([_DRIFT_ROW, _PRESUMED_ROW], indent=2)

    outcome = _read(tmp_path, ProcessResult(returncode=2, stdout=stdout, stderr=""))

    assert isinstance(outcome, Verdict)
    assert outcome.returncode == 2
    assert [(row.check, row.evidence.get("path")) for row in outcome.rows] == [
        ("drift", "src/a.py"),
        ("drift-presumed", "src/b.py"),
    ]
    assert outcome.rows[0].message.endswith("--write-baseline --spec p/spec-a")


def test_extra_keys_in_a_row_are_ignored(tmp_path: Path) -> None:
    """A later Doctor may add keys to a row (Doctor Story 56.3's evidence marker); the record keeps its three."""
    row = {**_DRIFT_ROW, "unevaluable": False, "rank": 1, "evidence": {"path": "src/a.py", "unevaluable": False}}

    outcome = _read(tmp_path, ProcessResult(returncode=2, stdout=json.dumps([row]), stderr=""))

    assert isinstance(outcome, Verdict)
    assert outcome.rows[0].check == "drift"
    assert outcome.rows[0].evidence.get("path") == "src/a.py"


def test_a_verdict_row_is_frozen(tmp_path: Path) -> None:
    outcome = _read(tmp_path, ProcessResult(returncode=2, stdout=json.dumps([_DRIFT_ROW]), stderr=""))

    assert isinstance(outcome, Verdict)
    with pytest.raises(AttributeError):
        outcome.rows[0].check = "ok"  # type: ignore[misc]
    with pytest.raises(TypeError):
        outcome.rows[0].evidence["path"] = "elsewhere"  # type: ignore[index]


@pytest.mark.parametrize(
    ("answer", "named"),
    [
        (
            ProcessResult(
                returncode=2,
                stdout="",
                stderr="usage: python -m pyforge.doctor.sources [-h] source\nerror: argument source: invalid choice\n",
            ),
            "exited 2 with no verdict on stdout: error: argument source: invalid choice",
        ),
        (
            ProcessResult(returncode=2, stdout="  \n", stderr=""),
            "exited 2 with no verdict on stdout",
        ),
        (
            ProcessResult(
                returncode=1,
                stdout="",
                stderr="Traceback (most recent call last):\n  ...\nModuleNotFoundError: No module named 'yaml'\n",
            ),
            "exited 1: ModuleNotFoundError: No module named 'yaml'",
        ),
        (
            ProcessResult(returncode=1, stdout=json.dumps([_DRIFT_ROW]), stderr=""),
            "exited 1: <no stderr>",
        ),
        (ProcessResult(returncode=130, stdout="", stderr=""), "exited 130"),
        (ProcessError("executable not found: '/no/python' (No such file)"), "could not run"),
        (ProcessError("command timed out after 300.0s: python -c ..."), "timed out after 300.0s"),
        (ProcessResult(returncode=0, stdout="[spec-surface] drift: fail -- p/spec-a: ...", stderr=""), "not JSON"),
        (ProcessResult(returncode=2, stdout=json.dumps({"findings": [_DRIFT_ROW]}), stderr=""), "not a JSON list"),
        (ProcessResult(returncode=0, stdout="null", stderr=""), "not a JSON list"),
        (
            ProcessResult(returncode=2, stdout=json.dumps([_DRIFT_ROW, "drift"]), stderr=""),
            "row 1 is not a finding",
        ),
        (
            ProcessResult(returncode=2, stdout=json.dumps([{"check": "drift", "message": "m"}]), stderr=""),
            "row 0 is not a finding",
        ),
        (
            ProcessResult(
                returncode=2,
                stdout=json.dumps([{"check": "drift", "message": "m", "evidence": "src/a.py"}]),
                stderr="",
            ),
            "row 0 is not a finding",
        ),
    ],
    ids=[
        "rc_2_empty_stdout_argparse",
        "rc_2_blank_stdout",
        "rc_1_crash",
        "rc_1_even_with_a_json_list",
        "rc_130",
        "launch_failure",
        "timeout",
        "prose_stdout",
        "json_object_stdout",
        "json_null_stdout",
        "a_row_that_is_not_an_object",
        "a_row_without_evidence",
        "a_row_whose_evidence_is_not_an_object",
    ],
)
def test_everything_else_is_unavailable(tmp_path: Path, answer: ProcessResult | ProcessError, named: str) -> None:
    outcome = _read(tmp_path, answer)

    assert isinstance(outcome, Unavailable)
    assert named in outcome.reason


def _fake_doctor_worktree(tmp_path: Path, main_body: str) -> Path:
    """A worktree whose own Doctor source tree holds a stand-in ``pyforge.doctor.sources`` command module."""
    worktree = tmp_path / "wt"
    sources = worktree.joinpath(*DOCTOR_SOURCE_REL.split("/"), "pyforge", "doctor", "sources")
    sources.mkdir(parents=True)
    (sources.parent / "__init__.py").write_text("", encoding="utf-8")
    (sources / "__init__.py").write_text("", encoding="utf-8")
    (sources / "__main__.py").write_text(main_body, encoding="utf-8")
    return worktree


def test_the_bootstrap_runs_the_worktrees_own_doctor_command_module(tmp_path: Path) -> None:
    """The real bootstrap, run by the real port: the worktree's Doctor source goes first on the child's
    ``sys.path`` and its command module runs as ``__main__`` with the argv after ``-c``."""
    worktree = _fake_doctor_worktree(
        tmp_path,
        "import json, sys\n"
        "row = {'source': 'spec-surface', 'check': 'drift', 'status': 'fail',\n"
        "       'message': 'm --write-baseline --spec p/spec-a',\n"
        "       'evidence': {'path': 'src/a.py', 'argv': sys.argv[1:], 'main': __name__, 'file': __file__}}\n"
        "if __name__ == '__main__':\n"
        "    print(json.dumps([row]))\n"
        "    sys.exit(2)\n",
    )

    outcome = read_spec_surface(worktree, PosixProcess())

    assert isinstance(outcome, Verdict), outcome
    assert outcome.returncode == 2
    [row] = outcome.rows
    assert row.evidence["argv"] == ["spec-surface", "--json"]
    assert row.evidence["main"] == "__main__"
    assert Path(str(row.evidence["file"])).resolve().is_relative_to(worktree.resolve())


def test_the_bootstrap_reports_an_argparse_refusal_as_unavailable(tmp_path: Path) -> None:
    worktree = _fake_doctor_worktree(
        tmp_path,
        "import argparse\n"
        "parser = argparse.ArgumentParser(prog='python -m pyforge.doctor.sources')\n"
        "parser.add_argument('source', choices=['dream-chain'])\n"
        "parser.add_argument('--json', action='store_true')\n"
        "parser.parse_args()\n",
    )

    outcome = read_spec_surface(worktree, PosixProcess())

    assert isinstance(outcome, Unavailable)
    assert "exited 2 with no verdict on stdout" in outcome.reason
    assert "invalid choice" in outcome.reason
