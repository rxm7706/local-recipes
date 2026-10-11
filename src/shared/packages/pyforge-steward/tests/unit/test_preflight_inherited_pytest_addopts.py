"""Story 90.1: child pytest runs must not inherit an outer basetemp or cache_dir."""

from __future__ import annotations

import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pyforge.steward import preflight
from pyforge.steward import preflight_suite_reduction as psr

_NOOP_INSTALL = lambda _env: 0  # noqa: E731


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _mini_pixi(*tasks: str) -> str:
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [\n"
    body += ",\n".join(f'  "{name}"' for name in tasks)
    body += "\n]\n\n"
    for name in tasks:
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "true"\n\n'
    return body


def _basetemp_tokens(addopts: str) -> list[str]:
    tokens = shlex.split(addopts)
    return [t for t in tokens if t.startswith("--basetemp") or t == "--basetemp"]


def _cache_dir_values(addopts: str) -> list[str]:
    tokens = shlex.split(addopts)
    values: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--override-ini=cache_dir="):
            values.append(tok.split("=", 2)[-1])
        elif tok == "--override-ini" and i + 1 < len(tokens) and tokens[i + 1].startswith(
            "cache_dir="
        ):
            values.append(tokens[i + 1].split("=", 1)[1])
            i += 1
        elif tok.startswith(("-ocache_dir=", "-o=cache_dir=")):
            values.append(tok.split("=", 1)[1])
        elif tok == "-o" and i + 1 < len(tokens) and tokens[i + 1].startswith("cache_dir="):
            values.append(tokens[i + 1].split("=", 1)[1])
            i += 1
        i += 1
    return values


@pytest.mark.parametrize(
    "inherited",
    [
        "-p no:randomly --basetemp=/outer -x",
        "-p no:randomly --basetemp /outer -x",
        "-p no:randomly -o cache_dir=/outer-cache -x",
        "-p no:randomly -ocache_dir=/outer-cache -x",
        "-p no:randomly -o=cache_dir=/outer-cache -x",
        "-p no:randomly --override-ini=cache_dir=/outer-cache -x",
        "-p no:randomly --override-ini cache_dir=/outer-cache -x",
        (
            "-p no:randomly --basetemp=/outer --basetemp /outer2 "
            "-o cache_dir=/c1 -ocache_dir=/c2 -o=cache_dir=/c3 "
            "--override-ini=cache_dir=/c4 --override-ini cache_dir=/c5 -x"
        ),
    ],
)
def test_lane_scratch_env_carries_only_lane_basetemp_and_cache(
    tmp_path: Path, inherited: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", inherited)
    lane_dir = tmp_path / "lane"
    env = preflight._lane_scratch_env(lane_dir)  # noqa: SLF001
    addopts = env["PYTEST_ADDOPTS"]
    basetemps = _basetemp_tokens(addopts)
    assert len(basetemps) == 1
    assert str(lane_dir / "pytest-basetemp") in addopts
    caches = _cache_dir_values(addopts)
    assert caches == [str(lane_dir / "pytest-cache")]
    tokens = shlex.split(addopts)
    assert "-p" in tokens and "no:randomly" in tokens
    assert "-x" in tokens
    randomly_idx = tokens.index("no:randomly")
    x_idx = tokens.index("-x")
    assert randomly_idx < x_idx


def test_lane_scratch_env_unset_or_empty_inherited(tmp_path: Path) -> None:
    lane_dir = tmp_path / "lane"
    env = preflight._lane_scratch_env(lane_dir)  # noqa: SLF001
    assert env["PYTEST_ADDOPTS"] == (
        f"--basetemp={lane_dir / 'pytest-basetemp'} -o cache_dir={lane_dir / 'pytest-cache'}"
    )


def test_lane_scratch_env_unclosed_quote_passes_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = '-p no:randomly --basetemp=/outer "unclosed'
    monkeypatch.setenv("PYTEST_ADDOPTS", broken)
    lane_dir = tmp_path / "lane"
    env = preflight._lane_scratch_env(lane_dir)  # noqa: SLF001
    assert env["PYTEST_ADDOPTS"].startswith(broken)
    assert str(lane_dir / "pytest-basetemp") in env["PYTEST_ADDOPTS"]


def test_collect_pytest_node_ids_strips_inherited_basetemp(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    test_file = repo / "test_one.py"
    _write(test_file, "def test_ok(): pass\n")
    outer = tmp_path / "outer-bt"
    outer.mkdir()
    cache = tmp_path / "outer-cache"
    cache.mkdir()
    addopts = f"--basetemp={outer} -o cache_dir={cache}"
    ids_plain = psr.collect_pytest_node_ids(repo, f"pytest {test_file} -q")
    ids_inherited = psr.collect_pytest_node_ids(
        repo, f"pytest {test_file} -q", env={"PYTEST_ADDOPTS": addopts}
    )
    assert ids_inherited == ids_plain
    assert repo.exists()


def test_run_preflight_child_pytest_under_outer_basetemp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("lane"))
    test_file = repo / "test_pass.py"
    _write(test_file, "def test_ok(): assert True\n")
    outer = tmp_path / "outer-bt"
    outer.mkdir()
    monkeypatch.setenv("PYTEST_ADDOPTS", f"--basetemp={outer}")

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q", "-p", "no:cacheprovider"],
            cwd=repo,
            env=ctx.env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        return preflight.EXIT_OK

    assert (
        preflight.run_preflight(
            repo,
            jobs=1,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=run_ctx,
            scratch_parent=tmp_path / "scratch",
        )
        == preflight.EXIT_OK
    )


def test_strip_helper_unit() -> None:
    assert psr.strip_inherited_pytest_basetemp_and_cache("") == ""
    assert psr.strip_inherited_pytest_basetemp_and_cache("  ") == ""
    kept = psr.strip_inherited_pytest_basetemp_and_cache("-p no:cacheprovider -x")
    assert kept == "-p no:cacheprovider -x"
