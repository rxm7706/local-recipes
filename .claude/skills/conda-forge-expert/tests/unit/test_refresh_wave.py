"""Unit tests for ``refresh_wave.py`` (mason Story 25.3).

Every test runs on a fixture recipe tree under ``tmp_path`` with
``CFE_RECIPES_ROOT`` pointed at it. The feedstock fetch (``_lookup``), the hash
calculation (``recipe_editor.calculate_sha256_from_url``) and the subprocess seam
(``_run``) are mocked, so no test touches the network or runs a gate or a build.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

OLD_SHA = "a" * 64
NEW_SHA = "b" * 64
OTHER_SHA = "c" * 64

CFE_TAIL = """\
#### CFE metadata AND comments
# CFE metadata
  cfe-conda-name: @NAME@
  cfe-upstream-registry: pypi
  cfe-upstream-name: @DIST@
  cfe-forge-recipe-updates-needed: none
  cfe-forge-blocker-list: []
  cfe-last-checked: 2026-08-16T23:47:43Z
  cfe-local-build-status: not-attempted
  cfe-local-build-datetime: none
  cfe-local-build-platform: none
  cfe-local-build-tool: none
####
# CFE comments
# Header:
#    # (agent rationale parks here, organized by recipe location — never
#    # inline in the body; see SKILL.md "Never Add AI Comments Inline")
####
"""

BODY = """\
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  version: "@VERSION@"

package:
  name: @NAME@
  version: ${{ version }}

source:
  url: @URL@
  sha256: @SHA@

build:
  number: @BUILD@
  noarch: python
  script: ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
@HOST@
  run:
@RUN@

tests:
  - python:
      imports:
        - @IMPORT@
      pip_check: true

about:
  homepage: https://example.org/@NAME@
  license: MIT
  license_file: LICENSE
  summary: A fixture package

extra:
  recipe-maintainers:
@MAINT@
"""


def _items(lines, indent="    "):
    return "\n".join(f"{indent}- {x}" for x in lines)


def make_recipe(
    name="widget",
    version="1.0.0",
    sha=OLD_SHA,
    url=None,
    build=3,
    maintainers=("rxm7706",),
    host=("python ${{ python_min }}.*", "pip"),
    run=("python >=${{ python_min }}", "anyio >=4.9.0"),
    dist=None,
    tail=True,
    flat_lists=False,
):
    dist = dist or name
    url = url or f"https://pypi.org/packages/source/{dist[0]}/{dist}/{name}-${{{{ version }}}}.tar.gz"
    indent = "  " if flat_lists else "    "
    text = (
        BODY.replace("@NAME@", name)
        .replace("@VERSION@", version)
        .replace("@URL@", url)
        .replace("@SHA@", sha)
        .replace("@BUILD@", str(build))
        .replace("@HOST@", _items(host, indent))
        .replace("@RUN@", _items(run, indent))
        .replace("@IMPORT@", name.replace("-", "_"))
        .replace("@MAINT@", _items(maintainers, indent))
    )
    if tail:
        text += CFE_TAIL.replace("@NAME@", name).replace("@DIST@", dist)
    return text


def fs_v1_raw(version="2.0.0", sha=NEW_SHA, maintainers=("rxm7706",),
              host=("python ${{ python_min }}.*", "pip"),
              run=("python >=${{ python_min }}", "anyio >=4.9.0")):
    return (
        f'schema_version: 1\ncontext:\n  version: "{version}"\n'
        f"source:\n  url: https://pypi.org/packages/source/w/widget/widget-${{{{ version }}}}.tar.gz\n"
        f"  sha256: {sha}\n"
        f"requirements:\n  host:\n{_items(host)}\n  run:\n{_items(run)}\n"
        f"extra:\n  recipe-maintainers:\n{_items(maintainers)}\n"
    )


def fs_v0_raw(version="2.0.0", sha=NEW_SHA, maintainers=("rxm7706",),
              host=("python", "pip"), run=("python", "anyio >=4.9.0")):
    return (
        '{% set name = "widget" %}\n'
        f'{{% set version = "{version}" %}}\n'
        "package:\n  name: {{ name|lower }}\n  version: {{ version }}\n"
        "source:\n  url: https://pypi.io/packages/source/w/widget/widget-{{ version }}.tar.gz\n"
        f"  sha256: {sha}\n"
        f"requirements:\n  host:\n{_items(host)}\n  run:\n{_items(run)}\n"
        f"extra:\n  recipe-maintainers:\n{_items(maintainers)}\n"
    )


def tree_hash(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]


def body_of(text: str) -> str:
    return text.split("#### CFE metadata")[0]


@pytest.fixture
def rw(load_module):
    return load_module("refresh_wave.py")


@pytest.fixture
def env(rw, tmp_path, monkeypatch):
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    monkeypatch.setenv("CFE_RECIPES_ROOT", str(recipes))
    fs_module = sys.modules["feedstock_lookup"]

    state = SimpleNamespace(
        tmp=tmp_path,
        recipes=recipes,
        report=tmp_path / "report",
        feedstocks={},
        hash_calls=[],
        hash_map={},
        sha=NEW_SHA,
        run_calls=[],
        run_handler=lambda argv: (0, "", ""),
        lookups=[],
    )

    def add_feedstock(name, fmt, raw):
        state.feedstocks[name] = SimpleNamespace(
            exists=True, error=None, raw_text=raw, parsed=fs_module._parse_yaml(raw),
            format="recipe.yaml" if fmt == "v1" else "meta.yaml",
        )

    def fake_lookup(name):
        state.lookups.append(name)
        return state.feedstocks.get(
            name, SimpleNamespace(exists=False, error=None, raw_text=None, parsed=None, format=None)
        )

    def fake_hash(url):
        state.hash_calls.append(url)
        value = state.hash_map.get(url, state.sha)
        if isinstance(value, Exception):
            raise value
        return value

    def fake_run(argv, *, timeout=None):
        state.run_calls.append(list(argv))
        return state.run_handler(argv)

    state.add_feedstock = add_feedstock
    monkeypatch.setattr(rw, "_lookup", fake_lookup)
    monkeypatch.setattr(rw.recipe_editor, "calculate_sha256_from_url", fake_hash)
    monkeypatch.setattr(rw, "_run", fake_run)

    def write_recipe(name="widget", text=None, **kw):
        d = recipes / name
        d.mkdir(exist_ok=True)
        (d / "recipe.yaml").write_text(text if text is not None else make_recipe(name=name, **kw))
        return d / "recipe.yaml"

    state.write_recipe = write_recipe

    def invoke(recipes_list, *flags, track="B", wave="B1"):
        manifest = {"schema_version": 1, "track": track, "wave": wave, "recipes": recipes_list}
        path = tmp_path / "manifest.yaml"
        path.write_text(json.dumps(manifest))
        rc = rw.main([str(path), "--report-dir", str(state.report), *flags])
        report_json = state.report / "report.json"
        report = json.loads(report_json.read_text()) if report_json.exists() else None
        return rc, report

    state.invoke = invoke
    return state


def rec_of(report, name="widget"):
    return next(r for r in report["recipes"] if r["name"] == name)


# ── refresh: happy path, idempotence, resume ─────────────────────────────────

def test_refresh_happy_path_changes_only_the_three_lines(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    before = path.read_text()

    rc, report = env.invoke([{"name": "widget"}], "--apply")

    assert rc == 0
    after = path.read_text()
    assert rec_of(report)["outcome"] == "refreshed"
    assert rec_of(report)["from_version"] == "1.0.0" and rec_of(report)["to_version"] == "2.0.0"
    body_changes = changed_lines(body_of(before), body_of(after))
    assert sorted(body_changes) == sorted([
        '-  version: "1.0.0"', '+  version: "2.0.0"',
        f"-  sha256: {OLD_SHA}", f"+  sha256: {NEW_SHA}",
        "-  number: 3", "+  number: 0",
    ])
    # The templated PyPI URL stays templated.
    assert "widget-${{ version }}.tar.gz" in after
    assert "files.pythonhosted.org" not in after
    # List items stay two spaces deeper than their key: no FMT-001.
    assert _fmt001(after) == []
    # The hash was recomputed against the recipe's own rendered URL.
    assert env.hash_calls == ["https://pypi.org/packages/source/w/widget/widget-2.0.0.tar.gz"]
    assert after.count("#### CFE metadata") == 1 and after.count("cfe-conda-name") == 1
    assert "${{" not in "\n".join(l for l in after.splitlines() if "refresh_wave" in l)


def _fmt001(text: str) -> list[str]:
    recipe_optimizer = sys.modules.get("recipe_optimizer")
    if recipe_optimizer is None:
        import recipe_optimizer  # type: ignore[no-redef]
    return [k for k in recipe_optimizer._FMT_LIST_INDENT_RE.finditer(text) if k.group("indent")]


def test_refresh_never_runs_a_subprocess_without_gates_or_build(rw, env):
    env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply")
    assert env.run_calls == []


def test_second_apply_is_already_current_and_third_is_resumed(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply")
    refreshed_bytes = path.read_bytes()

    rc, report = env.invoke([{"name": "widget"}], "--apply")
    assert rc == 0
    assert path.read_bytes() == refreshed_bytes
    assert rec_of(report)["outcome"] == "already-current"
    assert not rec_of(report).get("resumed")

    env.hash_calls.clear()
    env.lookups.clear()
    rc, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "already-current"
    assert rec_of(report)["resumed"] is True
    assert env.lookups == [] and env.hash_calls == []
    assert path.read_bytes() == refreshed_bytes


def test_force_reprocesses_a_terminal_recipe(rw, env):
    env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply")
    env.invoke([{"name": "widget"}], "--apply")
    rc, report = env.invoke([{"name": "widget"}], "--apply", "--force")
    assert not rec_of(report).get("resumed")
    assert rec_of(report)["outcome"] == "already-current"


def test_resume_is_dropped_when_the_recipe_file_changed(rw, env):
    path = env.write_recipe(version="2.0.0")
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply")
    path.write_text(path.read_text() + "\n")  # a hand edit
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert not rec_of(report).get("resumed")


def test_local_version_ahead_of_target_is_already_current(rw, env):
    path = env.write_recipe(version="3.0.0")
    env.add_feedstock("widget", "v1", fs_v1_raw(version="2.0.0"))
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "already-current"
    assert path.read_bytes() == before


def test_manifest_version_overrides_the_feedstock_default(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(version="2.0.0"))
    _, report = env.invoke([{"name": "widget", "version": "2.0.0"}], "--apply")
    assert rec_of(report)["outcome"] == "refreshed"
    assert 'version: "2.0.0"' in path.read_text()


def test_unquoted_numeric_looking_version_stays_a_string(rw, env):
    text = make_recipe().replace('version: "1.0.0"', "version: 1.0.0")
    path = env.write_recipe(text=text)
    env.add_feedstock("widget", "v1", fs_v1_raw(version="1.10"))
    env.invoke([{"name": "widget"}], "--apply")
    parsed = yaml.safe_load(path.read_text())
    assert parsed["context"]["version"] == "1.10"


# ── refresh: shape (C1 / C2) ─────────────────────────────────────────────────

def test_c1_v0_feedstock_mirrors_meta_yaml_even_when_a_gate_fails(rw, env):
    path = env.write_recipe()
    d = path.parent
    (d / "meta.yaml").write_text("stale: mirror\n")
    raw = fs_v0_raw()
    env.add_feedstock("widget", "v0", raw)
    env.run_handler = lambda argv: (1, "", "boom") if "validate_recipe.py" in " ".join(argv) else (0, "", "")

    rc, report = env.invoke([{"name": "widget"}], "--apply", "--gates", "--build")

    assert rc == 0
    assert rec_of(report)["outcome"] == "refreshed"
    assert (d / "meta.yaml").read_text() == raw
    assert list(d.glob(".meta.yaml*")) == []
    assert rec_of(report)["gates"]["validate"] == 1
    assert set(rec_of(report)["gates"]) == {"validate", "optimize", "check-deps", "scan"}
    build_calls = [a for a in env.run_calls if a and a[0] == "rattler-build"]
    assert len(build_calls) == 1
    target = build_calls[0][build_calls[0].index("--recipe") + 1]
    assert target == str(path)  # recipe.yaml explicitly, never the directory
    out_dir = build_calls[0][build_calls[0].index("--output-dir") + 1]
    assert out_dir.endswith("build_artifacts/widget")  # G52: per-recipe isolation


def test_c1_creates_the_mirror_when_meta_yaml_is_absent(rw, env):
    path = env.write_recipe()
    raw = fs_v0_raw()
    env.add_feedstock("widget", "v0", raw)
    env.invoke([{"name": "widget"}], "--apply")
    assert (path.parent / "meta.yaml").read_text() == raw
    assert list(path.parent.glob(".meta.yaml*")) == []


def test_c2_v1_feedstock_removes_the_local_meta_yaml(rw, env):
    path = env.write_recipe()
    (path.parent / "meta.yaml").write_text("old: v0\n")
    env.add_feedstock("widget", "v1", fs_v1_raw())
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert not (path.parent / "meta.yaml").exists()
    assert rec_of(report)["meta_yaml"] == "removed"
    assert any("meta.yaml removed" in n for n in rec_of(report)["notes"])


def test_missing_local_directory_is_blocked(rw, env):
    env.add_feedstock("ghost", "v1", fs_v1_raw())
    rc, report = env.invoke([{"name": "ghost"}], "--apply")
    assert rc == 0
    assert rec_of(report, "ghost")["outcome"] == "blocked"
    assert rec_of(report, "ghost")["reasons"] == ["no-local-mirror"]
    assert not (env.recipes / "ghost").exists()


def test_directory_without_recipe_yaml_is_blocked(rw, env):
    d = env.recipes / "oldstyle"
    d.mkdir()
    (d / "meta.yaml").write_text("package: {}\n")
    env.add_feedstock("oldstyle", "v0", fs_v0_raw())
    _, report = env.invoke([{"name": "oldstyle"}], "--apply")
    assert rec_of(report, "oldstyle")["outcome"] == "blocked"
    assert rec_of(report, "oldstyle")["reasons"] == ["no-recipe-yaml"]
    assert (d / "meta.yaml").read_text() == "package: {}\n"


def test_recipe_without_context_name_is_refreshed(rw, env):
    """The billiard shape: a literal package.name and no context.name."""
    path = env.write_recipe()
    assert "name:" not in path.read_text().split("package:")[0].split("context:")[1]
    env.add_feedstock("widget", "v1", fs_v1_raw())
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "refreshed"


# ── refresh: maintainers ─────────────────────────────────────────────────────

def test_deployed_maintainers_are_unioned_with_local_order_first(rw, env):
    path = env.write_recipe(maintainers=("rxm7706", "carol"))
    env.add_feedstock("widget", "v1", fs_v1_raw(maintainers=("bob", "carol", "rxm7706")))
    _, report = env.invoke([{"name": "widget"}], "--apply")
    parsed = yaml.safe_load(path.read_text())
    assert parsed["extra"]["recipe-maintainers"] == ["rxm7706", "carol", "bob"]
    assert rec_of(report)["maintainers_added"] == ["bob"]
    assert set(["bob", "carol", "rxm7706"]) <= set(parsed["extra"]["recipe-maintainers"])
    assert "maintainers added: bob" in path.read_text()


def test_no_maintainer_handle_is_ever_dropped(rw, env):
    path = env.write_recipe(maintainers=("rxm7706", "local-only"))
    env.add_feedstock("widget", "v1", fs_v1_raw(maintainers=("rxm7706",)))
    env.invoke([{"name": "widget"}], "--apply")
    assert "local-only" in yaml.safe_load(path.read_text())["extra"]["recipe-maintainers"]


# ── refresh: needs-review cases ──────────────────────────────────────────────

def test_sha256_mismatch_keeps_the_original_bytes(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(sha=OTHER_SHA))
    before = path.read_bytes()
    rc, report = env.invoke([{"name": "widget"}], "--apply")
    assert rc == 0
    assert rec_of(report)["outcome"] == "needs-review"
    assert any("sha256-mismatch" in r for r in rec_of(report)["reasons"])
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/dl/widget-1.0.0.tar.gz",
        "https://pypi.org/packages/source/w/widget/widget-1.0.0.tar.gz",
    ],
)
def test_version_baked_url_is_needs_review_with_no_write(rw, env, url):
    path = env.write_recipe(url=url)
    env.add_feedstock("widget", "v1", fs_v1_raw())
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("url-version-baked")
    assert path.read_bytes() == before
    assert env.hash_calls == []


def test_refresh_never_rewrites_a_hashed_url_and_names_repair(rw, env):
    url = "https://files.pythonhosted.org/packages/ab/cd/" + "e" * 40 + "/widget-1.0.0.tar.gz"
    path = env.write_recipe(url=url)
    env.add_feedstock("widget", "v1", fs_v1_raw())
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert "--repair" in rec_of(report)["reasons"][0]
    assert path.read_bytes() == before


def test_dependency_name_difference_writes_only_the_cfe_block(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(run=("python >=${{ python_min }}", "anyio >=4.9.0", "httpx")))
    before = path.read_text()
    rc, report = env.invoke([{"name": "widget"}], "--apply")
    after = path.read_text()
    assert rc == 0
    rec = rec_of(report)
    assert rec["outcome"] == "needs-review"
    assert rec["reasons"][0].startswith("dependency-fix")
    assert rec["dependency_diff"]["names"]["run"]["only_feedstock"] == ["httpx"]
    assert body_of(after) == body_of(before)
    assert "cfe-forge-recipe-updates-needed: [dependency-fix]" in after
    assert after.count("dependency-fix") >= 2  # the token and the dated comment
    assert env.hash_calls == []
    assert "${{" not in "\n".join(l for l in after.splitlines() if "refresh_wave" in l)
    assert after.count("#### CFE metadata") == 1 and after.count("cfe-conda-name") == 1


def test_deliberate_commented_pin_is_reported_and_left_alone(rw, env):
    text = make_recipe(run=("python >=${{ python_min }}", "anyio <5  # pinned: 5.x breaks the loop"))
    path = env.write_recipe(text=text)
    env.add_feedstock("widget", "v1", fs_v1_raw(run=("python >=${{ python_min }}", "anyio >=5")))
    before = path.read_text()
    _, report = env.invoke([{"name": "widget"}], "--apply")
    rec = rec_of(report)
    assert rec["outcome"] == "needs-review"
    assert rec["dependency_diff"]["pins"][0]["name"] == "anyio"
    assert body_of(path.read_text()) == body_of(before)
    assert "dependency-fix" in path.read_text()


def test_existing_dependency_fix_token_forms(rw):
    f = rw._add_updates_needed_token
    t = "extra:\n  cfe-forge-recipe-updates-needed: none\n"
    assert f(t, "dependency-fix") == "extra:\n  cfe-forge-recipe-updates-needed: [dependency-fix]\n"
    t = "extra:\n  cfe-forge-recipe-updates-needed: [meta-yaml-to-recipe-yaml]\n"
    assert "[meta-yaml-to-recipe-yaml, dependency-fix]" in f(t, "dependency-fix")
    t = "extra:\n  cfe-forge-recipe-updates-needed: recipe-regenerate\n"
    assert "[recipe-regenerate, dependency-fix]" in f(t, "dependency-fix")
    t = "extra:\n  cfe-forge-recipe-updates-needed:\n    - one\n    - two\n  cfe-x: y\n"
    out = f(t, "dependency-fix")
    assert out == "extra:\n  cfe-forge-recipe-updates-needed:\n    - one\n    - two\n    - dependency-fix\n  cfe-x: y\n"
    assert f(out, "dependency-fix") == out
    t = "extra:\n  cfe-forge-recipe-updates-needed:\n  cfe-x: y\n"
    assert "cfe-forge-recipe-updates-needed: [dependency-fix]" in f(t, "dependency-fix")


def test_tag_numbering_mismatch_is_needs_review(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(version="2.0.1"))
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget", "version": "2.0.0"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert "tag-numbering" in rec_of(report)["reasons"][0]
    assert path.read_bytes() == before


def test_non_pep440_version_is_needs_review(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(version="2.0.0"))
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget", "version": "not a version"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("non-pep440-version")
    assert path.read_bytes() == before


def test_unreadable_feedstock_is_needs_review(rw, env):
    path = env.write_recipe()
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget", "version": "2.0.0"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert path.read_bytes() == before


# ── refresh: write check (G92) ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "plant",
    [
        lambda text, **kw: text + "\n: : [unclosed\n",
        lambda text, **kw: text + "\n#### CFE metadata (second block)\n",
    ],
    ids=["breaks-the-parse", "duplicates-the-cfe-block"],
)
def test_a_broken_write_is_restored_and_exits_one(rw, env, monkeypatch, plant):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    before = path.read_bytes()
    monkeypatch.setattr(rw, "_cfe_edit", plant)
    rc, report = env.invoke([{"name": "widget"}], "--apply")
    assert rc == 1
    assert rec_of(report)["outcome"] == "failed"
    assert any(r.startswith("write-check") for r in rec_of(report)["reasons"])
    assert path.read_bytes() == before


def test_hash_fetch_failure_is_failed_with_the_original_kept(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.hash_map["https://pypi.org/packages/source/w/widget/widget-2.0.0.tar.gz"] = RuntimeError("404")
    before = path.read_bytes()
    rc, report = env.invoke([{"name": "widget"}], "--apply")
    assert rc == 1
    assert rec_of(report)["outcome"] == "failed"
    assert path.read_bytes() == before


def test_recipe_without_a_cfe_block_is_needs_review(rw, env):
    path = env.write_recipe(tail=False)
    env.add_feedstock("widget", "v1", fs_v1_raw())
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("no-cfe-block")
    assert path.read_bytes() == before


# ── gates and build stamps ───────────────────────────────────────────────────

def test_gates_run_through_the_cfe_wrappers_pointed_at_recipe_yaml(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply", "--gates")
    scripts = [Path(a[1]).name for a in env.run_calls]
    assert scripts == ["validate_recipe.py", "recipe_optimizer.py", "dependency-checker.py", "vulnerability_scanner.py"]
    assert all(Path(a[1]).parent.parts[-2:] == ("scripts", "conda-forge-expert") for a in env.run_calls)
    assert all(a[2] == str(path) for a in env.run_calls)


def test_build_stamps_the_real_outcome(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    _, report = env.invoke([{"name": "widget"}], "--apply", "--build")
    text = path.read_text()
    assert rec_of(report)["build"]["status"] == "success"
    assert "cfe-local-build-status: success" in text
    assert "cfe-local-build-tool: rattler-build" in text
    assert "cfe-local-build-datetime: none" not in text
    assert text.count("#### CFE metadata") == 1 and text.count("cfe-conda-name") == 1


def test_a_failed_build_is_stamped_failed(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.run_handler = lambda argv: (1, "compile error", "")
    _, report = env.invoke([{"name": "widget"}], "--apply", "--build")
    assert rec_of(report)["build"]["status"] == "failed"
    assert "cfe-local-build-status: failed" in path.read_text()


def test_build_clean_test_blocked_needs_an_artifact_and_a_solver_message(rw, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    assert rw._classify_build(0, "", out) == "success"
    assert rw._classify_build(1, "Could not solve the test environment", out) == "failed"
    (out / "noarch").mkdir()
    (out / "noarch" / "widget-1-0.conda").write_text("x")
    assert rw._classify_build(1, "Could not solve the test environment", out) == "build-clean-test-blocked"
    assert rw._classify_build(1, "compile error", out) == "failed"


# ── dry-run ──────────────────────────────────────────────────────────────────

def test_dry_run_writes_only_the_report(rw, env):
    for n in ("widget", "gadget", "sprocket"):
        env.write_recipe(n)
        env.add_feedstock(n, "v1", fs_v1_raw())
    (env.recipes / "widget" / "meta.yaml").write_text("old: v0\n")
    before = tree_hash(env.recipes)

    rc, report = env.invoke(
        [{"name": "widget"}, {"name": "gadget"}, {"name": "sprocket"}], "--gates", "--build"
    )

    assert rc == 0
    assert tree_hash(env.recipes) == before
    assert (env.report / "report.json").exists() and (env.report / "report.md").exists()
    assert [r["outcome"] for r in report["recipes"]] == ["would-refresh"] * 3
    assert env.run_calls == []  # no gate, no build
    assert env.hash_calls == []  # no download
    assert report["applied"] is False
    assert "would-refresh" in (env.report / "report.md").read_text()


def test_dry_run_does_not_poison_a_later_apply(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}])
    _, report = env.invoke([{"name": "widget"}], "--apply")
    assert rec_of(report)["outcome"] == "refreshed"
    assert 'version: "2.0.0"' in path.read_text()


def test_dry_run_dependency_fix_is_not_resumed_by_a_later_apply(rw, env):
    path = env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw(run=("python >=${{ python_min }}", "anyio >=4.9.0", "httpx")))
    env.invoke([{"name": "widget"}])
    assert "dependency-fix" not in path.read_text()
    env.invoke([{"name": "widget"}], "--apply")
    assert "dependency-fix" in path.read_text()


# ── manifest and CLI ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "manifest",
    [
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}], "extra": 1},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget", "bogus": 1}]},
        {"schema_version": 1, "track": "C", "wave": "B1", "recipes": [{"name": "widget"}]},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "../x"}]},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget", "feedstock": "a/b"}]},
        {"schema_version": 1, "track": "B", "wave": "../w", "recipes": [{"name": "widget"}]},
        {"schema_version": 2, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}]},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": []},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget", "version": 2.0}]},
        {"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}, {"name": "widget"}]},
    ],
)
def test_bad_manifest_exits_two_and_writes_nothing(rw, env, manifest):
    path = env.write_recipe()
    before = tree_hash(env.recipes)
    mpath = env.tmp / "bad.yaml"
    mpath.write_text(json.dumps(manifest))
    rc = rw.main([str(mpath), "--apply", "--report-dir", str(env.report)])
    assert rc == 2
    assert not env.report.exists()
    assert tree_hash(env.recipes) == before
    assert path.exists()


def test_manifest_may_be_yaml_text(rw, env):
    env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    mpath = env.tmp / "m.yaml"
    mpath.write_text(
        "schema_version: 1\ntrack: A\nwave: H9\nrecipes:\n  - name: widget\n    version: \"2.0.0\"\n"
    )
    assert rw.main([str(mpath), "--report-dir", str(env.report)]) == 0
    report = json.loads((env.report / "report.json").read_text())
    assert report["track"] == "A" and report["wave"] == "H9"


def test_unreadable_manifest_exits_two(rw, env):
    assert rw.main([str(env.tmp / "missing.yaml"), "--report-dir", str(env.report)]) == 2


def test_report_dir_under_recipes_is_refused(rw, env):
    env.write_recipe()
    mpath = env.tmp / "m.yaml"
    mpath.write_text(json.dumps({"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}]}))
    rc = rw.main([str(mpath), "--report-dir", str(env.recipes / "report")])
    assert rc == 2
    assert not (env.recipes / "report").exists()


def test_default_report_dir_comes_from_the_data_dir(rw, env, monkeypatch):
    env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    data_dir = env.tmp / "data"
    monkeypatch.setattr(rw, "get_data_dir", lambda: data_dir)
    mpath = env.tmp / "m.yaml"
    mpath.write_text(json.dumps({"schema_version": 1, "track": "B", "wave": "B7", "recipes": [{"name": "widget"}]}))
    assert rw.main([str(mpath)]) == 0
    assert (data_dir / "refresh-waves" / "B-B7" / "report.json").exists()


def test_build_is_refused_with_repair(rw, env):
    env.write_recipe()
    mpath = env.tmp / "m.yaml"
    mpath.write_text(json.dumps({"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}]}))
    with pytest.raises(SystemExit) as exc:
        rw.main([str(mpath), "--repair", "--build", "--report-dir", str(env.report)])
    assert exc.value.code == 2


def test_json_flag_prints_the_report(rw, env, capsys):
    env.write_recipe()
    env.add_feedstock("widget", "v1", fs_v1_raw())
    mpath = env.tmp / "m.yaml"
    mpath.write_text(json.dumps({"schema_version": 1, "track": "B", "wave": "B1", "recipes": [{"name": "widget"}]}))
    rw.main([str(mpath), "--json", "--report-dir", str(env.report)])
    out = capsys.readouterr().out
    assert json.loads(out)["recipes"][0]["outcome"] == "would-refresh"


def test_report_md_buckets_the_outcomes(rw, env):
    env.write_recipe("widget")
    env.write_recipe("gadget", version="9.0.0")
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.add_feedstock("gadget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}, {"name": "gadget"}, {"name": "ghost"}], "--apply")
    md = (env.report / "report.md").read_text()
    for heading in ("## refreshed (1)", "## already-current (1)", "## blocked (1)"):
        assert heading in md


# ── recipe_updater.get_current_recipe_info ───────────────────────────────────

def test_get_current_recipe_info_billiard_shape(load_module, tmp_path):
    updater = load_module("recipe_updater.py")
    p = tmp_path / "recipe.yaml"
    p.write_text(make_recipe(name="billiard"))
    assert updater.get_current_recipe_info(p) == {"name": "billiard", "version": "1.0.0"}


def test_get_current_recipe_info_prefers_context_name_then_upstream_name(load_module, tmp_path):
    updater = load_module("recipe_updater.py")
    p = tmp_path / "recipe.yaml"
    p.write_text(make_recipe(name="wasmtime-py", dist="wasmtime"))
    assert updater.get_current_recipe_info(p)["name"] == "wasmtime"
    p.write_text(make_recipe(name="x").replace('context:\n  version: "1.0.0"', 'context:\n  name: ctxname\n  version: "1.0.0"'))
    assert updater.get_current_recipe_info(p)["name"] == "ctxname"


def test_get_current_recipe_info_without_any_name_source_still_raises(load_module, tmp_path):
    updater = load_module("recipe_updater.py")
    p = tmp_path / "recipe.yaml"
    p.write_text('context:\n  version: "1.0"\npackage:\n  name: ${{ name }}\n')
    with pytest.raises(ValueError, match="Could not determine package name and version"):
        updater.get_current_recipe_info(p)
    p.write_text('package:\n  name: only\n')
    with pytest.raises(ValueError, match="Could not determine package name and version"):
        updater.get_current_recipe_info(p)


# ── repair: hashed URL ───────────────────────────────────────────────────────

HASHED = "https://files.pythonhosted.org/packages/ab/cd/" + "e" * 40 + "/widget-1.0.0.tar.gz"


def test_repair_hashed_url_rewrites_only_the_url_line(rw, env):
    path = env.write_recipe(url=HASHED)
    before = path.read_text()
    env.hash_map["https://pypi.org/packages/source/w/widget/widget-1.0.0.tar.gz"] = OLD_SHA

    rc, report = env.invoke([{"name": "widget"}], "--repair", "--apply")

    assert rc == 0
    after = path.read_text()
    assert rec_of(report)["outcome"] == "repaired"
    assert rec_of(report)["repairs"] == ["url"]
    assert changed_lines(before, after) == [
        f"-  url: {HASHED}",
        "+  url: https://pypi.org/packages/source/w/widget/widget-${{ version }}.tar.gz",
    ]
    assert f"sha256: {OLD_SHA}" in after


def test_repair_uses_the_pypi_project_name_not_the_package_name(rw, env):
    url = "https://files.pythonhosted.org/packages/ab/cd/" + "e" * 40 + "/wasmtime-1.0.0.tar.gz"
    path = env.write_recipe(name="wasmtime-py", dist="wasmtime", url=url)
    env.hash_map["https://pypi.org/packages/source/w/wasmtime/wasmtime-1.0.0.tar.gz"] = OLD_SHA
    _, report = env.invoke([{"name": "wasmtime-py"}], "--repair", "--apply")
    assert rec_of(report, "wasmtime-py")["outcome"] == "repaired"
    assert "url: https://pypi.org/packages/source/w/wasmtime/wasmtime-${{ version }}.tar.gz" in path.read_text()


def test_repair_reads_the_project_name_from_the_feedstock_when_the_recipe_has_none(rw, env):
    text = make_recipe(url=HASHED).replace("  cfe-upstream-name: widget\n", "")
    path = env.write_recipe(text=text)
    env.add_feedstock("widget", "v0", fs_v0_raw())
    env.hash_map["https://pypi.org/packages/source/w/widget/widget-1.0.0.tar.gz"] = OLD_SHA
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "repaired"
    assert "widget/widget-${{ version }}.tar.gz" in path.read_text()


def test_repair_without_any_dist_source_is_needs_review(rw, env):
    text = make_recipe(url=HASHED).replace("  cfe-upstream-name: widget\n", "")
    path = env.write_recipe(text=text)
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("no-dist-name")
    assert path.read_bytes() == before


@pytest.mark.parametrize("mode", ["mismatch", "fetch-failed"])
def test_repair_hash_trouble_leaves_the_file_byte_identical(rw, env, mode):
    path = env.write_recipe(url=HASHED)
    before = path.read_bytes()
    canonical = "https://pypi.org/packages/source/w/widget/widget-1.0.0.tar.gz"
    env.hash_map[canonical] = OTHER_SHA if mode == "mismatch" else RuntimeError("network down")
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("url-hash-mismatch" if mode == "mismatch" else "url-fetch-failed")
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "filename",
    ["widget-1.0.0-py3-none-any.whl", "widget-2.0.0.tar.gz", "widget_1.0.0.tar.gz", "widget-1.0.0.egg"],
)
def test_repair_wheel_or_odd_file_names_are_needs_review(rw, env, filename):
    url = "https://files.pythonhosted.org/packages/ab/cd/" + "e" * 40 + "/" + filename
    path = env.write_recipe(url=url)
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("url-file-shape")
    assert path.read_bytes() == before
    assert env.hash_calls == []


# ── repair: indentation ──────────────────────────────────────────────────────

def _flat_recipe():
    """A recipe whose lists sit at their parent key's depth (FMT-001), nested ones included."""
    return make_recipe(flat_lists=True).replace(
        "about:\n  homepage",
        "extras:\n  items:\n  - name: a\n    values:\n    - 1\n    - 2\n  - name: b\nabout:\n  homepage",
    )


def test_repair_reindents_flat_lists_whitespace_only(rw, env):
    text = _flat_recipe()
    path = env.write_recipe(text=text)
    assert _fmt001(text)
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    after = path.read_text()
    assert rec_of(report)["outcome"] == "repaired"
    assert rec_of(report)["repairs"] == ["indent"]
    recipe_optimizer = sys.modules["recipe_optimizer"]
    assert recipe_optimizer.analyze_yaml_indent(path) == []
    assert yaml.safe_load(after) == yaml.safe_load(text)
    assert [l.strip() for l in after.splitlines()] == [l.strip() for l in text.splitlines()]
    assert after.count("#### CFE metadata") == 1 and "# CFE comments" in after
    assert after.count("cfe-conda-name") == 1
    # The nested list was re-indented too.
    assert "      values:\n        - 1" in after


def test_repair_indent_refuses_a_change_that_alters_content(rw, env, monkeypatch):
    text = _flat_recipe()
    path = env.write_recipe(text=text)
    real = rw._reindent_fmt001
    monkeypatch.setattr(rw, "_reindent_fmt001", lambda t: real(t).replace("pip_check: true", "pip_check: false"))
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("indent-repair-refused")
    assert path.read_bytes() == before


def test_repair_indent_refuses_a_value_change_without_text_change(rw, env, monkeypatch):
    text = _flat_recipe()
    path = env.write_recipe(text=text)
    # Break one list item's nesting: same stripped text, different parse.
    def bad(t):
        return t.replace("\n  - name: b", "\n    - name: b", 1)
    monkeypatch.setattr(rw, "_reindent_fmt001", bad)
    before = path.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert path.read_bytes() == before


# ── repair: hidden meta.yaml ─────────────────────────────────────────────────

def _hide(d: Path, text="held: meta\n"):
    hold = d / ".meta.yaml.wave_h_hold"
    hold.write_text(text)
    return hold


def test_repair_hidden_meta_v0_restores_from_the_feedstock(rw, env):
    path = env.write_recipe()
    hold = _hide(path.parent, "held: different\n")
    raw = fs_v0_raw()
    env.add_feedstock("widget", "v0", raw)
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "repaired"
    assert (path.parent / "meta.yaml").read_text() == raw
    assert not hold.exists() and list(path.parent.glob(".meta.yaml*")) == []
    assert rec_of(report)["meta_matches_hold"] is False


def test_repair_hidden_meta_v0_records_when_it_equals_the_hold_file(rw, env):
    path = env.write_recipe()
    raw = fs_v0_raw()
    _hide(path.parent, raw)
    env.add_feedstock("widget", "v0", raw)
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["meta_matches_hold"] is True


def test_repair_hidden_meta_v1_leaves_no_meta_yaml(rw, env):
    path = env.write_recipe()
    hold = _hide(path.parent)
    env.add_feedstock("widget", "v1", fs_v1_raw())
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "repaired"
    assert not (path.parent / "meta.yaml").exists()
    assert not hold.exists()


def test_repair_hidden_meta_with_unreadable_feedstock_renames_the_hold_back(rw, env):
    path = env.write_recipe()
    hold = _hide(path.parent, "held: bytes\n")
    held = hold.read_bytes()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert "feedstock-unread" in rec_of(report)["reasons"][0]
    assert (path.parent / "meta.yaml").read_bytes() == held
    assert not hold.exists()


def test_repair_hold_beside_meta_yaml_touches_nothing(rw, env):
    path = env.write_recipe()
    hold = _hide(path.parent)
    meta = path.parent / "meta.yaml"
    meta.write_text("live: meta\n")
    env.add_feedstock("widget", "v0", fs_v0_raw())
    before = tree_hash(env.recipes)
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rec_of(report)["outcome"] == "needs-review"
    assert rec_of(report)["reasons"][0].startswith("hold-and-meta-both-present")
    assert tree_hash(env.recipes) == before
    assert hold.exists() and meta.exists()


# ── repair: scope, idempotence, dry-run ──────────────────────────────────────

def _all_three_defects(env):
    text = _flat_recipe().replace(
        "url: https://pypi.org/packages/source/w/widget/widget-${{ version }}.tar.gz", f"url: {HASHED}"
    )
    path = env.write_recipe(text=text)
    _hide(path.parent, "held: meta\n")
    env.add_feedstock("widget", "v0", fs_v0_raw())
    env.hash_map["https://pypi.org/packages/source/w/widget/widget-1.0.0.tar.gz"] = OLD_SHA
    return path, text


def test_repair_touches_nothing_else_and_a_rerun_is_already_clean(rw, env):
    path, before = _all_three_defects(env)
    rc, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert rc == 0
    assert rec_of(report)["outcome"] == "repaired"
    assert rec_of(report)["repairs"] == ["url", "indent", "meta-yaml"]
    old, new = yaml.safe_load(before), yaml.safe_load(path.read_text())
    for key in ("context", "build", "requirements", "tests", "about"):
        assert new[key] == old[key], key
    assert new["extra"]["recipe-maintainers"] == old["extra"]["recipe-maintainers"]
    assert new["source"]["sha256"] == old["source"]["sha256"]
    assert new["source"]["url"] != old["source"]["url"]

    after = path.read_bytes()
    tree = tree_hash(env.recipes)
    env.hash_calls.clear()
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply", "--force")
    assert rec_of(report)["outcome"] == "already-clean"
    assert path.read_bytes() == after and tree_hash(env.recipes) == tree
    assert env.hash_calls == []


def test_repair_dry_run_leaves_recipes_byte_identical_and_writes_a_report(rw, env):
    _all_three_defects(env)
    before = tree_hash(env.recipes)
    rc, report = env.invoke([{"name": "widget"}], "--repair", "--gates")
    assert rc == 0
    assert tree_hash(env.recipes) == before
    rec = rec_of(report)
    assert rec["outcome"] == "would-repair"
    assert rec["repairs"] == ["url", "indent", "meta-yaml"]
    assert (env.report / "report.json").exists() and (env.report / "report.md").exists()
    assert env.run_calls == [] and env.hash_calls == []


def test_repair_gates_run_after_an_applied_repair(rw, env):
    _all_three_defects(env)
    env.invoke([{"name": "widget"}], "--repair", "--apply", "--gates")
    assert len(env.run_calls) == 4


def test_repair_leaves_the_cfe_block_alone(rw, env):
    path, before = _all_three_defects(env)
    env.invoke([{"name": "widget"}], "--repair", "--apply")
    after = path.read_text()
    assert "cfe-last-checked: 2026-08-16T23:47:43Z" in after
    assert "refresh_wave" not in after


def test_repair_missing_directory_is_needs_review(rw, env):
    _, report = env.invoke([{"name": "ghost"}], "--repair", "--apply")
    assert rec_of(report, "ghost")["outcome"] == "needs-review"
    assert rec_of(report, "ghost")["reasons"] == ["no-local-mirror"]


def test_repair_refresh_reports_do_not_share_resume_state(rw, env):
    env.write_recipe(version="2.0.0")
    env.add_feedstock("widget", "v1", fs_v1_raw())
    env.invoke([{"name": "widget"}], "--apply")
    env.invoke([{"name": "widget"}], "--apply")  # terminal: already-current
    _, report = env.invoke([{"name": "widget"}], "--repair", "--apply")
    assert not rec_of(report).get("resumed")
    assert rec_of(report)["outcome"] == "already-clean"


# ── text helpers ─────────────────────────────────────────────────────────────

def test_header_comment_lands_under_the_header_and_is_deduplicated(rw):
    text = make_recipe()
    out = rw._append_header_comment(text, "2026-10-09 refresh_wave B-B1: refreshed 1 -> 2")
    lines = out.splitlines()
    i = lines.index("# Header:")
    assert lines[i + 3] == "#    # 2026-10-09 refresh_wave B-B1: refreshed 1 -> 2"
    assert lines[i + 4] == "####"
    assert rw._append_header_comment(out, "2026-10-09 refresh_wave B-B1: refreshed 1 -> 2") == out


def test_header_comment_never_carries_renderable_jinja(rw):
    out = rw._append_header_comment(make_recipe(), "see ${{ name|lower }} and {% if x %}")
    new = [l for l in out.splitlines() if "see " in l][0]
    assert "{{" not in new and "{%" not in new


def test_header_comment_creates_the_block_when_missing(rw):
    out = rw._append_header_comment("a: 1\n", "hello")
    assert out.endswith("# CFE comments\n# Header:\n#    # hello\n####\n")
