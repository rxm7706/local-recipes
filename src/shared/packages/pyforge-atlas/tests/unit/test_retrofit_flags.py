"""Two-state tests for atlas's CAP-7 retrofit kill switches (Epic 42; ``spec-feature-flag-governance`` CAP-7).

Each key runs ON and OFF through ``pyforge.testing_kit.flags.flag_states`` and a flagd FILE tree in the same
state. OFF: the MCP trigger and read tools raise ``AtlasMCPError`` naming the flag before any session is
bootstrapped, and ``pyforge atlas run`` stays listed in ``--help`` marked disabled (Q3) and refuses with exit 2
(usage, inside the frozen ``{0, 1, 2, 130}`` domain). ON: the switches read ON and the tools are not refused (the
real pipeline runs are the existing suites' business).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.flags import read_boolean
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.atlas import __main__ as atlas_main
from pyforge.atlas.mcp import tools

EXIT_USAGE = 2


def _tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, on: bool) -> Path:
    path = flagd_tree(tmp_path, {key: "on" if on else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    return path


@flag_states("pyforge.atlas.agent_pipeline_tools")
def test_pyforge_atlas_agent_pipeline_tools(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """agents trigger and read the pipeline natively (spec-pyforge-atlas CAP-9, Story 42.1)."""
    on = flag_provider["pyforge.atlas.agent_pipeline_tools"]
    tree = _tree(tmp_path, monkeypatch, "pyforge.atlas.agent_pipeline_tools", on)
    assert read_boolean(tools.AGENT_PIPELINE_TOOLS_FLAG_KEY, default=True, flags_path=tree) is on
    listing = " ".join(invoke_cli(atlas_main.main, ["--help"]).output.split())
    assert " run " in listing or listing.endswith(" run")
    if on:
        tools.require_agent_pipeline_tools()
        assert "flag pyforge.atlas.agent_pipeline_tools is off" not in listing
        return
    assert "[disabled: flag pyforge.atlas.agent_pipeline_tools is off]" in listing
    with pytest.raises(tools.AtlasMCPError, match="flag pyforge.atlas.agent_pipeline_tools is off"):
        tools.run_pipeline("core", project_path=tmp_path)
    with pytest.raises(tools.AtlasMCPError, match="flag pyforge.atlas.agent_pipeline_tools is off"):
        tools.read_dataset("anything", project_path=tmp_path)
    result = invoke_cli(atlas_main.main, ["run"])
    assert result.exit_code == EXIT_USAGE
    assert "pyforge-atlas: flag pyforge.atlas.agent_pipeline_tools is off" in result.output


@flag_states("pyforge.atlas.manifest_inventory")
def test_pyforge_atlas_manifest_inventory(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """any manifest becomes one comparable inventory, behind one exit code (spec-pyforge-atlas CAP-13, Story 42.2)."""
    on = flag_provider["pyforge.atlas.manifest_inventory"]
    tree = _tree(tmp_path, monkeypatch, "pyforge.atlas.manifest_inventory", on)
    assert read_boolean(tools.MANIFEST_INVENTORY_FLAG_KEY, default=True, flags_path=tree) is on
    if on:
        tools.require_manifest_inventory()
        return
    with pytest.raises(tools.AtlasMCPError, match="flag pyforge.atlas.manifest_inventory is off"):
        tools.run_pipeline(tools.MANIFEST_INVENTORY_PIPELINE, project_path=tmp_path)
    for argv in (
        ["run", "--pipeline", tools.MANIFEST_INVENTORY_PIPELINE],
        ["run", f"--pipeline={tools.MANIFEST_INVENTORY_PIPELINE}"],
        ["run", f"--pipelines=core,{tools.MANIFEST_INVENTORY_PIPELINE}"],
    ):
        result = invoke_cli(atlas_main.main, argv)
        assert result.exit_code == EXIT_USAGE, argv
        assert "pyforge-atlas: flag pyforge.atlas.manifest_inventory is off" in result.output, argv
    listing = " ".join(invoke_cli(atlas_main.main, ["--help"]).output.split())
    assert "[disabled: flag pyforge.atlas.manifest_inventory is off]" in listing


def test_run_short_help_is_recomputed_each_call_and_never_sticks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OFF listing marks `run` once; an ON listing in the same process reads it unmarked again."""
    key = "pyforge.atlas.agent_pipeline_tools"
    _tree(tmp_path, monkeypatch, key, False)
    invoke_cli(atlas_main.main, ["--help"])
    off = " ".join(invoke_cli(atlas_main.main, ["--help"]).output.split())
    assert off.count(f"[disabled: flag {key} is off]") == 1
    _tree(tmp_path, monkeypatch, key, True)
    on = " ".join(invoke_cli(atlas_main.main, ["--help"]).output.split())
    assert f"flag {key} is off" not in on


def test_python_dash_m_exits_with_the_refusal_code() -> None:
    """`python -m pyforge.atlas` raises SystemExit(main()), so a refusal's 2 reaches the shell."""
    source = Path(atlas_main.__file__).read_text(encoding="utf-8")
    assert source.rstrip().endswith("raise SystemExit(main())")


@flag_states("pyforge.atlas.manifest_inventory")
def test_the_manifest_inventory_switch_unregisters_its_pipeline(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-review finding 4: OFF, `universal_sbom` leaves the registry, so `__default__` (a bare `run`), `--nodes`
    and a direct `kedro run --pipeline universal_sbom` cannot reach its gate; ON, the registry is unchanged."""
    from kedro.framework.project import configure_project

    from pyforge.atlas import pipeline_registry

    # Kedro's find_pipelines needs the package configured; never rely on an earlier test on this xdist worker.
    configure_project("pyforge.atlas")
    on = flag_provider["pyforge.atlas.manifest_inventory"]
    _tree(tmp_path, monkeypatch, "pyforge.atlas.manifest_inventory", on)
    registered = pipeline_registry.register_pipelines()
    default_nodes = {node.name for node in registered["__default__"].nodes}
    if on:
        sbom_nodes = {node.name for node in registered["universal_sbom"].nodes}
        assert sbom_nodes and sbom_nodes <= default_nodes
    else:
        assert "universal_sbom" not in registered
        assert not any("normalize_intake_to_cyclonedx" in name for name in default_nodes)


def test_the_cli_and_the_mcp_face_read_the_same_keys() -> None:
    assert atlas_main.AGENT_PIPELINE_TOOLS_FLAG_KEY == tools.AGENT_PIPELINE_TOOLS_FLAG_KEY
    assert atlas_main.MANIFEST_INVENTORY_FLAG_KEY == tools.MANIFEST_INVENTORY_FLAG_KEY
    assert atlas_main.MANIFEST_INVENTORY_PIPELINE == tools.MANIFEST_INVENTORY_PIPELINE == "universal_sbom"
    assert tools.MANIFEST_INVENTORY_PIPELINE in tools.PIPELINE_NAMES


def test_no_tree_reads_every_switch_on_without_a_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    tools.require_agent_pipeline_tools()
    tools.require_manifest_inventory()
