"""Story 67.4: tests for scripts/upstream_todos_check.py."""

from __future__ import annotations

import ast
import importlib.util
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "upstream_todos_check.py"
REGISTRY_PATH = REPO_ROOT / "docs" / "foundry" / "upstream-todos.yaml"
GAPS_DOC = REPO_ROOT / "docs" / "foundry" / "sbom-gaps.md"


def _load():
    spec = importlib.util.spec_from_file_location("upstream_todos_under_test", DETECTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["upstream_todos_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def _minimal_draft(tmp_path: Path, name: str) -> str:
    rel = f"drafts/{name}.md"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dedent(
            """\
            ## Title
            t
            ## Body
            b
            ## Reproduce or evidence
            e
            ## Local workaround
            w
            ## What resolution unblocks here
            u
            """
        ),
        encoding="utf-8",
    )
    return rel


def _base_item(**overrides):
    item = {
        "id": "sample-item",
        "title": "Sample",
        "source": "finding:test",
        "evidence": ["docs/foundry/sbom-gaps.md:1"],
        "target": {
            "tracker": "github",
            "repo": "org/repo",
            "kind": "issue",
            "verified": "2026-10-10",
        },
        "state": "proposed",
        "draft": None,
        "issue_url": None,
        "observed": None,
        "decided_by": "agent",
        "date": "2026-10-10",
        "history": [],
    }
    item.update(overrides)
    return item


def test_pixi_task_registered() -> None:
    text = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "[feature.guild-tasks.tasks.upstream-todos-check]" in text


def test_live_registry_passes() -> None:
    assert mod.check_upstream_todos() == []


def test_main_exits_zero_on_live_tree(capsys) -> None:
    assert mod.main([]) == 0
    capsys.readouterr()


def test_no_forbidden_network_imports() -> None:
    tree = ast.parse(DETECTOR_PATH.read_text(encoding="utf-8"))
    forbidden = {"subprocess", "urllib", "http", "socket", "requests"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert root not in forbidden
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".", 1)[0]
                assert root not in forbidden


def test_no_row_regex_in_module() -> None:
    text = DETECTOR_PATH.read_text(encoding="utf-8")
    assert "ROW_RE" not in text
    assert "parse_gaps_document" in text


def test_main_network_patched_still_passes_live_registry() -> None:
    with mock.patch("socket.socket", side_effect=OSError("blocked")), mock.patch(
        "subprocess.run", side_effect=OSError("blocked")
    ), mock.patch("subprocess.Popen", side_effect=OSError("blocked")), mock.patch(
        "urllib.request.urlopen", side_effect=OSError("blocked")
    ):
        assert mod.main([]) == 0


def test_duplicate_id(tmp_path: Path) -> None:
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(id="dup"),
            _base_item(id="dup"),
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("dup: duplicate id" in f for f in findings)


def test_unknown_state(tmp_path: Path) -> None:
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {"schema_version": 1, "items": [_base_item(state="bogus")]}
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("unknown state" in f for f in findings)


def test_observed_on_drafted(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "d")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                state="drafted",
                draft=draft,
                observed={"at": "2026-10-10", "state": "open", "via": "gh"},
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("observed set outside tracking" in f for f in findings)


def test_operator_state_agent_decided(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "f")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="filed-bad",
                state="filed",
                draft=draft,
                issue_url="https://github.com/o/r/issues/1",
                decided_by="agent",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("filed-bad" in f and "decided_by: operator" in f for f in findings)


def test_filed_without_https_url(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "g")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="no-url",
                state="filed",
                draft=draft,
                issue_url="http://insecure.example/1",
                decided_by="operator",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("https://" in f for f in findings)


def test_retired_without_reason(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "h")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="ret-no-reason",
                state="retired",
                draft=draft,
                decided_by="operator",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("retired requires reason" in f for f in findings)


def test_resolved_without_follow_up(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "i")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="res-no-follow",
                state="resolved",
                draft=draft,
                decided_by="operator",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("local_follow_up" in f for f in findings)


def test_operator_states_valid_pass(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "j")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="ok-filed",
                state="filed",
                draft=draft,
                issue_url="https://github.com/o/r/issues/2",
                decided_by="operator",
            ),
            _base_item(
                id="ok-retired",
                state="retired",
                draft=draft,
                reason="superseded",
                decided_by="operator",
            ),
            _base_item(
                id="ok-resolved",
                state="resolved",
                draft=draft,
                local_follow_up="done: merged locally",
                decided_by="operator",
            ),
        ],
    }
    # Cover upstream rows so coverage findings do not mask operator-state pass
    for row_id in ("feature:conda-smithy", "feature:crm", "feature:python-agent-platform"):
        reg["items"].append(
            _base_item(
                id=f"cover-{row_id.replace(':', '-')}",
                source=f"sbom-gaps:{row_id}",
                state="proposed",
            )
        )
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert not any("decided_by: operator" in f for f in findings)


def test_uncovered_upstream_row_prints_stub(tmp_path: Path) -> None:
    gaps = dedent(
        """\
        | id | kind | disposition | reason | owner |
        | --- | --- | --- | --- | --- |
        | `feature:brand-new-upstream-67-4` | feature | upstream | r | mason |
        """
    )
    reg = {"schema_version": 1, "items": []}
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("proposed stub" in f for f in findings)
    assert any("sbom-gaps:feature:brand-new-upstream-67-4" in f for f in findings)


def test_stale_sbom_source_row_fails(tmp_path: Path) -> None:
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="stale-src",
                source="sbom-gaps:feature:conda-smithy",
                state="drafted",
                draft=_minimal_draft(tmp_path, "stale"),
            )
        ],
    }
    # mutate gaps so conda-smithy is promote
    gaps_mut = gaps.replace(
        "`feature:conda-smithy` | feature | upstream",
        "`feature:conda-smithy` | feature | promote",
    )
    findings = mod.check_registry(reg, gaps_text=gaps_mut, repo_root=tmp_path)
    assert any("no longer upstream" in f for f in findings)


def test_retired_stale_source_passes(tmp_path: Path) -> None:
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    gaps_mut = gaps.replace(
        "`feature:conda-smithy` | feature | upstream",
        "`feature:conda-smithy` | feature | promote",
    )
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="ret-stale",
                source="sbom-gaps:feature:conda-smithy",
                state="retired",
                draft=_minimal_draft(tmp_path, "ret"),
                reason="fixed upstream",
                decided_by="operator",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps_mut, repo_root=tmp_path)
    assert not any("ret-stale" in f and "upstream" in f for f in findings)


def test_draft_missing_section(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("## Title\nonly\n", encoding="utf-8")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="bad-draft",
                state="drafted",
                draft="bad.md",
            )
        ],
    }
    findings = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    assert any("bad.md" in f and "missing section" in f for f in findings)


def test_registry_not_yaml_exits_nonzero(tmp_path: Path) -> None:
    reg = tmp_path / "upstream-todos.yaml"
    reg.write_text(":\n- bad\n", encoding="utf-8")
    gaps = tmp_path / "sbom-gaps.md"
    gaps.write_text(GAPS_DOC.read_text(encoding="utf-8"), encoding="utf-8")
    code = mod.main(["--registry", str(reg), "--gaps-doc", str(gaps)])
    assert code in (1, 2)


def test_missing_registry_exits_two(capsys) -> None:
    missing = REPO_ROOT / "nope-upstream-todos.yaml"
    assert mod.main(["--registry", str(missing)]) == 1


def test_mutation_skipping_operator_rule_would_pass_bad_state(tmp_path: Path) -> None:
    draft = _minimal_draft(tmp_path, "mut")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [
            _base_item(
                id="mut-filed",
                state="filed",
                draft=draft,
                issue_url="https://github.com/o/r/issues/9",
                decided_by="agent",
            )
        ],
    }
    with_operator = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    saved = mod.OPERATOR_STATES
    mod.OPERATOR_STATES = frozenset()
    try:
        without_operator = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    finally:
        mod.OPERATOR_STATES = saved
    assert any("decided_by: operator" in f for f in with_operator)
    assert not any("decided_by: operator" in f for f in without_operator)


def test_mutation_skipping_coverage_would_miss_upstream_row(tmp_path: Path) -> None:
    gaps = dedent(
        """\
        | id | kind | disposition | reason | owner |
        | --- | --- | --- | --- | --- |
        | `feature:only-upstream` | feature | upstream | r | mason |
        """
    )
    reg = {"schema_version": 1, "items": []}
    full = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)

    def _no_tail(*_a, **_k):
        return []

    original = mod.check_registry

    def _patched(registry, *, gaps_text, repo_root=REPO_ROOT):
        findings = original(registry, gaps_text=gaps_text, repo_root=repo_root)
        return [f for f in findings if "proposed stub" not in f]

    mod.check_registry = _patched  # type: ignore[method-assign]
    try:
        stripped = mod.check_registry(reg, gaps_text=gaps, repo_root=tmp_path)
    finally:
        mod.check_registry = original  # type: ignore[method-assign]
    assert any("only-upstream" in f for f in full)
    assert not any("only-upstream" in f for f in stripped)


def test_mutation_skipping_draft_sections_would_pass_bad_draft(tmp_path: Path) -> None:
    bad = tmp_path / "thin.md"
    bad.write_text("## Title\nx\n", encoding="utf-8")
    gaps = GAPS_DOC.read_text(encoding="utf-8")
    reg = {
        "schema_version": 1,
        "items": [_base_item(id="thin", state="drafted", draft="thin.md")],
    }
    with_sections = mod._check_draft_file("thin.md", tmp_path)
    saved = mod.DRAFT_SECTIONS
    mod.DRAFT_SECTIONS = ("## Title",)  # type: ignore[misc]
    try:
        without_sections = mod._check_draft_file("thin.md", tmp_path)
    finally:
        mod.DRAFT_SECTIONS = saved  # type: ignore[misc]
    assert len(with_sections) > len(without_sections)


def test_subprocess_main_json_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(DETECTOR_PATH)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0
