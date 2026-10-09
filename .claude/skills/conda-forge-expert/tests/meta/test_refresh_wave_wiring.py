"""Meta: ``refresh_wave.py`` is wired in all three places and stays local-only (Story 25.3).

* Three places (``docs/reference/agent-instruction-notes.md`` § conda-forge-expert
  layout): the skill script, the thin wrapper, the pixi task + ``SCRIPTS`` entry,
  plus the ``CLI_ONLY_VERBS`` parity entry.
* Local only: the driver never pushes, forks, opens a PR, writes to any remote,
  submits or ships. An ``ast`` guard pins the source; a run test drives a dry-run
  and an ``--apply`` run with every outbound seam patched to raise.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SKILL_DIR = Path(__file__).resolve().parents[2]
SCRIPT = SKILL_DIR / "scripts" / "refresh_wave.py"
REPO_ROOT = SKILL_DIR.parents[2]
WRAPPER = REPO_ROOT / ".claude" / "scripts" / "conda-forge-expert" / "refresh_wave.py"
PIXI_TOML = REPO_ROOT / "pixi.toml"

FORBIDDEN_FRAGMENTS = ("push", "pr create", "repo fork", "--method", "-X", "submit", "ship")


# ── wiring ───────────────────────────────────────────────────────────────────

@pytest.mark.meta
def test_wrapper_exists_and_delegates_to_the_skill_script():
    assert WRAPPER.is_file()
    text = WRAPPER.read_text()
    assert '"skills" / "conda-forge-expert" / "scripts" / "refresh_wave.py"' in text
    assert "subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:])" in text
    # Shaped like recipe_updater's wrapper: no logic of its own.
    sibling = (WRAPPER.parent / "recipe_updater.py").read_text()
    assert len(text.splitlines()) == len(sibling.splitlines())


@pytest.mark.meta
def test_pixi_declares_the_refresh_wave_task_naming_the_wrapper():
    text = PIXI_TOML.read_text()
    m = re.search(r"^\[feature\.local-recipes\.tasks\.refresh-wave\]\n(.*?)(?=\n\[|\Z)", text, re.S | re.M)
    assert m, "pixi.toml has no [feature.local-recipes.tasks.refresh-wave]"
    cmd = re.search(r'^cmd = "([^"]+)"', m.group(1), re.M)
    assert cmd and cmd.group(1) == "python .claude/scripts/conda-forge-expert/refresh_wave.py"


@pytest.mark.meta
def test_script_is_declared_in_SCRIPTS_and_answers_help(script_runner):
    spec = importlib.util.spec_from_file_location(
        "_scripts_runnable", Path(__file__).with_name("test_all_scripts_runnable.py")
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "refresh_wave.py" in mod.SCRIPTS
    rc, out, err = script_runner("refresh_wave.py", "--help", timeout=30)
    assert rc == 0, err
    assert "usage" in (out + err).lower()
    assert "Traceback" not in out + err


@pytest.mark.meta
def test_wrapper_help_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(WRAPPER), "--help"], capture_output=True, text=True, timeout=30, check=False
    )
    assert proc.returncode == 0, proc.stderr
    assert "usage" in proc.stdout.lower()


@pytest.mark.meta
def test_refresh_wave_is_a_declared_cli_only_verb_and_parity_holds():
    scripts_dir = str(SKILL_DIR / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from mcp_parity import CLI_ONLY_VERBS, assert_cli_tool_parity, discover_cli_verbs, parity_findings

    assert "refresh-wave" in discover_cli_verbs()
    reason = CLI_ONLY_VERBS["refresh-wave"]
    assert reason.strip() and reason.rstrip().endswith(".")
    assert_cli_tool_parity()
    assert parity_findings() == []


# ── local-only guard ─────────────────────────────────────────────────────────

def _non_docstring_strings(tree: ast.AST) -> list[str]:
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstring_nodes.add(id(body[0].value))
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstring_nodes
    ]


@pytest.mark.meta
def test_the_driver_source_is_local_only():
    tree = ast.parse(SCRIPT.read_text())
    strings = _non_docstring_strings(tree)

    for value in strings:
        for fragment in FORBIDDEN_FRAGMENTS:
            assert fragment not in value, f"string {value!r} contains {fragment!r}"
        assert "mason" not in value.lower(), f"string {value!r} names a mason invocation"
        assert value not in ("git", "gh"), f"argv element {value!r}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            first = node.elts[0]
            if isinstance(first, ast.Constant) and first.value in ("git", "gh", "mason"):
                pytest.fail(f"argv starting with {first.value!r} at line {node.lineno}")

    banned_modules = {"submit_pr", "prepare_pr", "prepare_submission_branch", "pyforge", "git"}
    banned_names = {"submit_pr", "prepare_pr", "prepare_submission_branch"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_modules, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_modules, node.module
            for alias in node.names:
                assert alias.name not in banned_names, alias.name
        elif isinstance(node, ast.Name):
            assert node.id not in banned_names, f"{node.id} at line {node.lineno}"
        elif isinstance(node, ast.Attribute):
            assert node.attr not in banned_names, f"{node.attr} at line {node.lineno}"


@pytest.mark.meta
def test_the_guard_catches_a_planted_violation():
    planted = ast.parse('import subprocess\nsubprocess.run(["git", "push"])\nx = "gh pr create"\n')
    strings = _non_docstring_strings(planted)
    assert any("push" in s for s in strings)
    assert "git" in strings and any("pr create" in s for s in strings)


@pytest.mark.meta
def test_the_driver_has_exactly_one_subprocess_seam():
    tree = ast.parse(SCRIPT.read_text())
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "subprocess"
        and n.func.attr in {"run", "Popen", "call", "check_call", "check_output"}
    ]
    assert len(calls) == 1
    enclosing = next(
        f.name for f in ast.walk(tree)
        if isinstance(f, ast.FunctionDef) and any(c in ast.walk(f) for c in calls)
    )
    assert enclosing == "_run"


# ── run test: nothing but local disk ─────────────────────────────────────────

RECIPE = """\
schema_version: 1

context:
  version: "1.0.0"

package:
  name: widget
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/w/widget/widget-${{ version }}.tar.gz
  sha256: %s

build:
  number: 1

requirements:
  host:
    - python
  run:
    - python

extra:
  recipe-maintainers:
    - rxm7706
#### CFE metadata AND comments
# CFE metadata
  cfe-conda-name: widget
  cfe-upstream-name: widget
  cfe-forge-recipe-updates-needed: none
  cfe-last-checked: 2026-08-16T23:47:43Z
  cfe-local-build-status: not-attempted
  cfe-local-build-datetime: none
  cfe-local-build-platform: none
  cfe-local-build-tool: none
####
# CFE comments
# Header:
####
""" % ("a" * 64)

FEEDSTOCK = """\
context:
  version: "2.0.0"
source:
  sha256: %s
requirements:
  host:
    - python
  run:
    - python
extra:
  recipe-maintainers:
    - rxm7706
    - bob
""" % ("b" * 64)


def _run_wave_with_every_outbound_seam_armed(load_module, tmp_path, monkeypatch, *flags):
    import urllib.request

    import requests

    rw = load_module("refresh_wave.py")
    fs_module = sys.modules["feedstock_lookup"]
    recipes = tmp_path / "recipes"
    (recipes / "widget").mkdir(parents=True)
    (recipes / "widget" / "recipe.yaml").write_text(RECIPE)
    monkeypatch.setenv("CFE_RECIPES_ROOT", str(recipes))

    seen: list[list[str]] = []

    def guarded_run(argv, *, timeout=None):
        seen.append(list(argv))
        joined = " ".join(map(str, argv))
        for fragment in (*FORBIDDEN_FRAGMENTS, "git", "mason"):
            assert fragment not in joined.split(), joined
        assert argv[0] not in ("git", "gh", "mason"), argv
        return 0, "", ""

    def no_subprocess(*a, **k):
        raise AssertionError(f"subprocess outside the driver's seam: {a!r}")

    def no_non_get(*a, **k):
        raise AssertionError("a non-GET request was attempted")

    class _Resp:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=8192):
            yield b"payload"

    def guarded_session_request(self, method, url, *a, **k):
        assert str(method).upper() == "GET", f"{method} {url}"
        return _Resp(url)

    def guarded_open_url(request, timeout=30):
        assert request.get_method() == "GET"
        raise AssertionError("the driver must not open urllib URLs")

    http = sys.modules.get("_http")
    if http is not None:
        monkeypatch.setattr(http, "open_url", guarded_open_url)
    monkeypatch.setattr(urllib.request, "urlopen", no_non_get)
    monkeypatch.setattr(requests.sessions.Session, "request", guarded_session_request)
    monkeypatch.setattr(subprocess, "run", no_subprocess)
    monkeypatch.setattr(subprocess, "Popen", no_subprocess)
    monkeypatch.setattr(rw, "_run", guarded_run)
    monkeypatch.setattr(rw, "_lookup", lambda name: SimpleNamespace(
        exists=True, error=None, raw_text=FEEDSTOCK, parsed=fs_module._parse_yaml(FEEDSTOCK), format="recipe.yaml"
    ))
    # The download itself is the one read the driver performs; serve it locally.
    monkeypatch.setattr(rw.recipe_editor, "calculate_sha256_from_url", lambda url: "b" * 64)

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}],
    }))
    report_dir = tmp_path / "report"
    rc = rw.main([str(manifest), "--report-dir", str(report_dir), *flags])
    return rc, json.loads((report_dir / "report.json").read_text()), recipes / "widget" / "recipe.yaml", seen


@pytest.mark.meta
def test_a_dry_run_completes_with_every_outbound_seam_armed(load_module, tmp_path, monkeypatch):
    rc, report, recipe, seen = _run_wave_with_every_outbound_seam_armed(
        load_module, tmp_path, monkeypatch, "--gates", "--build"
    )
    assert rc == 0
    assert report["recipes"][0]["outcome"] == "would-refresh"
    assert recipe.read_text() == RECIPE
    assert seen == []


@pytest.mark.meta
def test_an_apply_run_completes_with_every_outbound_seam_armed(load_module, tmp_path, monkeypatch):
    rc, report, recipe, seen = _run_wave_with_every_outbound_seam_armed(
        load_module, tmp_path, monkeypatch, "--apply", "--gates", "--build"
    )
    assert rc == 0
    assert report["recipes"][0]["outcome"] == "refreshed"
    assert 'version: "2.0.0"' in recipe.read_text()
    # Only the four gates and one build went through the seam.
    assert len(seen) == 5
    assert seen[-1][0] == "rattler-build"
    assert report["recipes"][0]["build"]["status"] == "success"


@pytest.mark.meta
def test_a_repair_run_completes_with_every_outbound_seam_armed(load_module, tmp_path, monkeypatch):
    rc, report, recipe, seen = _run_wave_with_every_outbound_seam_armed(
        load_module, tmp_path, monkeypatch, "--repair", "--apply", "--gates"
    )
    assert rc == 0
    assert report["recipes"][0]["outcome"] == "already-clean"
    assert recipe.read_text() == RECIPE
    assert seen == []
