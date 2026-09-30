"""Story 74.2 (``spec-feature-flag-governance`` CAP-3): ``core/dispatch_flag_gate.py``.

The pure half of the dispatch pre-session flag-gate consult: the gate's exit code
and JSON in, one ``Finding`` (or ``None``) out. The impure edge --
``cli/dispatch.py::_consult_flag_gate`` -- is exercised through ``dispatch_once``
in ``test_dispatch.py``; the campaign-block clearing in
``test_dispatch_re_preflight.py``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pyforge.marshal.core import dispatch_flag_gate as flag_gate
from pyforge.marshal.core.model import Severity

SPEC = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-74-2-x.md"


def _gate_json(verdict: str, findings: list[dict[str, str]] | None = None, **extra: object) -> str:
    return json.dumps(
        {"verdict": verdict, "spec": SPEC, "rule_date": "2026-09-28", "findings": findings or [], **extra}
    )


_RED_FINDINGS = [
    {
        "kind": "flag-missing",
        "severity": "fail",
        "message": "a post-rule `type: feature` spec carries neither a `flag:` block nor a `flag-exempt:` value",
        "path": SPEC,
    },
    {"kind": "flag-pre-rule", "severity": "warn", "message": "not part of the refusal"},
]


# --- red -----------------------------------------------------------------------------------


def test_red_verdict_with_exit_1_refuses_naming_the_spec_the_findings_and_the_remedy() -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=1, stdout=_gate_json("red", _RED_FINDINGS), stderr="")
    assert finding is not None
    assert finding.code == "MRS-DISP-052"
    assert finding.severity is Severity.ERROR
    assert SPEC in finding.message
    assert "flag-missing" in finding.message
    assert "neither a `flag:` block nor a `flag-exempt:` value" in finding.message
    assert "`flag:` block or a `flag-exempt:` value" in finding.message  # the remedy
    assert "docs/reference/story-spec-flag-block.md" in finding.message
    assert "flag-pre-rule" not in finding.message  # only the `fail` findings name the refusal


def test_red_verdict_without_finding_text_still_refuses() -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=1, stdout=_gate_json("red"), stderr="")
    assert finding is not None
    assert (finding.code, finding.severity) == ("MRS-DISP-052", Severity.ERROR)


@pytest.mark.parametrize("findings", ["nope", [None, 3, "x"], [{"severity": "fail"}]])
def test_red_verdict_tolerates_malformed_finding_rows(findings: object) -> None:
    stdout = json.dumps({"verdict": "red", "findings": findings})
    finding = flag_gate.decide_gate_result(SPEC, returncode=1, stdout=stdout, stderr="")
    assert finding is not None and finding.code == "MRS-DISP-052"


# --- warn / pass ---------------------------------------------------------------------------


def test_warn_verdict_with_exit_0_is_one_warn_naming_the_pre_rule_spec() -> None:
    warn_rows = [{"kind": "flag-pre-rule", "severity": "warn", "message": "minted before the rule date"}]
    finding = flag_gate.decide_gate_result(SPEC, returncode=0, stdout=_gate_json("warn", warn_rows), stderr="")
    assert finding is not None
    assert finding.code == "MRS-DISP-055"
    assert finding.severity is Severity.WARN
    assert SPEC in finding.message
    assert "pre-rule" in finding.message
    assert "minted before the rule date" in finding.message


def test_warn_verdict_without_finding_text_still_names_the_pre_rule_spec() -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=0, stdout=_gate_json("warn"), stderr="")
    assert finding is not None
    assert (finding.code, finding.severity) == ("MRS-DISP-055", Severity.WARN)
    assert "a pre-rule spec that carries neither" in finding.message


def test_pass_verdict_with_exit_0_is_no_finding() -> None:
    assert flag_gate.decide_gate_result(SPEC, returncode=0, stdout=_gate_json("pass"), stderr="") is None


# --- the gate cannot judge -----------------------------------------------------------------


def test_exit_2_names_the_gates_own_error_field() -> None:
    stdout = _gate_json("unknown", error="cannot read docs/governance/flag-rule-baseline.json: no such file")
    finding = flag_gate.decide_gate_result(SPEC, returncode=2, stdout=stdout, stderr="[flag-gate] unknown -- x")
    assert finding is not None
    assert (finding.code, finding.severity) == ("MRS-DISP-052", Severity.ERROR)
    assert "flag-rule-baseline.json" in finding.message
    assert "exit 2" in finding.message
    assert "never a silent green" in finding.message


def test_non_json_output_names_the_last_stderr_line() -> None:
    finding = flag_gate.decide_gate_result(
        SPEC, returncode=1, stdout="not json at all", stderr="Traceback (most recent call last):\nKeyError: 'x'\n"
    )
    assert finding is not None
    assert finding.code == "MRS-DISP-052" and finding.severity is Severity.ERROR
    assert "KeyError: 'x'" in finding.message
    assert "exit 1" in finding.message


def test_non_json_output_with_no_stderr_still_refuses_naming_the_exit_code() -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=0, stdout="", stderr="")
    assert finding is not None
    assert finding.code == "MRS-DISP-052"
    assert "not the gate's JSON object" in finding.message
    assert "exit 0" in finding.message


@pytest.mark.parametrize("stdout", ["[]", '"red"', "3", "null", "true"])
def test_json_that_is_not_an_object_refuses(stdout: str) -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=0, stdout=stdout, stderr="")
    assert finding is not None and finding.code == "MRS-DISP-052"


@pytest.mark.parametrize("stdout", ["{}", '{"verdict": null}', '{"verdict": "unknown"}', '{"verdict": "green"}'])
def test_a_missing_or_unknown_verdict_refuses(stdout: str) -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=0, stdout=stdout, stderr="")
    assert finding is not None
    assert (finding.code, finding.severity) == ("MRS-DISP-052", Severity.ERROR)


@pytest.mark.parametrize(
    ("returncode", "verdict"),
    [(1, "pass"), (1, "warn"), (0, "red"), (2, "pass"), (2, "red"), (3, "pass"), (139, "warn"), (-9, "red")],
)
def test_a_verdict_the_exit_code_contradicts_refuses(returncode: int, verdict: str) -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=returncode, stdout=_gate_json(verdict), stderr="")
    assert finding is not None
    assert (finding.code, finding.severity) == ("MRS-DISP-052", Severity.ERROR)
    assert f"exit {returncode}" in finding.message


def test_a_contradicting_verdict_says_it_contradicts_the_exit_code() -> None:
    finding = flag_gate.decide_gate_result(SPEC, returncode=1, stdout=_gate_json("pass"), stderr="")
    assert finding is not None
    assert "contradicts its exit code" in finding.message


def test_gate_failure_carries_the_process_error_text_the_timeout_included() -> None:
    finding = flag_gate.decide_gate_failure(SPEC, "command timed out after 60.0s: python scripts/flag_gate_check.py")
    assert (finding.code, finding.severity) == ("MRS-DISP-052", Severity.ERROR)
    assert SPEC in finding.message
    assert "timed out after 60.0s" in finding.message


# --- the gate is absent --------------------------------------------------------------------


def test_gate_absent_is_one_warn_naming_the_missing_script() -> None:
    finding = flag_gate.gate_absent_finding("scripts/flag_gate_check.py")
    assert (finding.code, finding.severity) == ("MRS-DISP-055", Severity.WARN)
    assert "scripts/flag_gate_check.py is not in this repository" in finding.message
    assert flag_gate.gate_absent_finding().message == finding.message


# --- the module never reads a spec's frontmatter (AD-4; Charter Section 6) -------------------

#: What ``core/dispatch_flag_gate.py`` may import: the stdlib it decides with, and the finding model.
_ALLOWED_IMPORTS = frozenset({"__future__", "json", "collections.abc", ".model"})
_READING_CALLS = frozenset({"open", "read_text", "read_bytes", "read", "readlines"})


def _scan(source: str) -> list[str]:
    """Every import outside ``_ALLOWED_IMPORTS`` and every file-reading call in ``source``."""
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            violations += [f"import {alias.name}" for alias in node.names if alias.name not in _ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            if module not in _ALLOWED_IMPORTS:
                violations.append(f"from {module} import ...")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name in _READING_CALLS:
                violations.append(f"call {name}()")
    return violations


def test_the_module_imports_nothing_outside_the_allow_list_and_reads_no_file() -> None:
    source = Path(flag_gate.__file__).read_text(encoding="utf-8")
    assert _scan(source) == []


def test_the_scanner_catches_a_module_that_reads_frontmatter() -> None:
    """The scanner is proven on a synthetic module that does what ``dispatch_flag_gate`` must not."""
    synthetic = (
        "from __future__ import annotations\n"
        "import json\n"
        "from pathlib import Path\n"
        "import yaml\n"
        "\n"
        "def decide(spec):\n"
        "    text = Path(spec).read_text(encoding='utf-8')\n"
        "    front = yaml.safe_load(text.split('---')[1])\n"
        "    with open(spec) as handle:\n"
        "        handle.read()\n"
        "    return front.get('type')\n"
    )
    violations = _scan(synthetic)
    assert "import yaml" in violations
    assert "from pathlib import ..." in violations
    assert "call read_text()" in violations
    assert "call open()" in violations
    assert "call read()" in violations


def test_the_scanner_passes_a_module_that_only_parses_the_gates_answer() -> None:
    clean = (
        "from __future__ import annotations\n"
        "import json\n"
        "from collections.abc import Mapping\n"
        "from .model import Finding\n"
        "\n"
        "def decide(stdout):\n"
        "    return json.loads(stdout)\n"
    )
    assert _scan(clean) == []
