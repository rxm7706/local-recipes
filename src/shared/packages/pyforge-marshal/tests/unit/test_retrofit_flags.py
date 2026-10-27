"""Two-state tests for marshal's CAP-7 retrofit kill switches (Epic 110; ``spec-feature-flag-governance`` CAP-7).

One test per key, each run with the key ON and OFF through ``pyforge.testing_kit.flags.flag_states`` and a flagd
FILE tree carrying the same state (the shape every marshal flag test uses, ``test_preserve_cli.py`` precedent).
A verb switch (``cli/retrofit_flags.VERB_FLAGS``): ON leaves ``--help`` unmarked and the verb's keys read ON; OFF
marks the verb disabled in ``--help`` (Q3) and ``require_verb_flags`` refuses naming the key. A behaviour switch:
ON keeps the capability's behaviour; OFF is the fallback its story spec names. ``marshal status`` proves the
``main`` wiring end to end: the refusal is the usage code 2 with a ``flag <key> is off`` message.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyforge.core.dispatch import DispatchError, dispatch_argv
from pyforge.core.flags import FlagOff
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.marshal.cli import dispatch as dispatch_cli
from pyforge.marshal.cli import refresh as refresh_cli
from pyforge.marshal.cli import retrofit_flags
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.cli.main import main
from pyforge.marshal.core import policy, recall_feedback
from pyforge.marshal.dispatch_land_finalize import __main__ as finalize_main
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main
from pyforge.marshal.seed.verbs import adopt as adopt_verb

USAGE = 2


def _tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, on: bool) -> Path:
    path = flagd_tree(tmp_path, {key: "on" if on else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    return path


def _entry_blocks(output: str, verb: str) -> list[str]:
    """The ``--help`` entries for ``verb`` (the testing kit's reading of a listing), with wrapped continuations."""
    lines = output.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.split(None, 1)[:1] != [verb]:
            continue
        indent = len(line) - len(stripped)
        block = [line]
        for follow in lines[index + 1 :]:
            if not follow.strip() or len(follow) - len(follow.lstrip()) <= indent:
                break
            block.append(follow)
        blocks.append("\n".join(block))
    return blocks


def _namespace(path: tuple[str, ...]) -> argparse.Namespace:
    ns = argparse.Namespace(command=path[0])
    if len(path) > 1:
        setattr(ns, f"{path[0]}_command", path[1])
    return ns


def _assert_verb_switch(key: str, on: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch, key, on)
    marker = f"[disabled: flag {key} is off]"
    paths = retrofit_flags.gated_verbs(key)
    assert paths, f"{key} gates no verb: a verb switch must name its verbs in KEY_VERBS"
    for path in paths:
        listing = invoke_cli(main, [*path[:-1], "--help"]).output
        verb = path[-1]
        assert re.search(rf"(?<![\w-]){re.escape(verb)}(?![\w-])", listing), (key, path)
        # argparse wraps a long help across lines: compare on whitespace-normalised text.
        blocks = [" ".join(block.split()) for block in _entry_blocks(listing, verb)]
        assert blocks, (key, path, listing)
        if on:
            assert not any(marker in block for block in blocks), (key, path)
            retrofit_flags.require_verb_flags(_namespace(path))
        else:
            assert any(marker in block for block in blocks), (key, path, blocks)
            with pytest.raises(FlagOff) as raised:
                retrofit_flags.require_verb_flags(_namespace(path))
            assert raised.value.key == key


# --- verb and invariant switches -------------------------------------------------------------------------------


@flag_states("pyforge.marshal.loop_homes")
def test_pyforge_marshal_loop_homes(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """loop homes and isolation (spec-pyforge-marshal CAP-1, Story 110.2): `marshal factory spin` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.loop_homes", flag_provider["pyforge.marshal.loop_homes"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.supervised_runs")
def test_pyforge_marshal_supervised_runs(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """supervised unattended runs (spec-pyforge-marshal CAP-2, Story 110.3): `marshal factory attach|resume|checkpoint` are listed disabled and refuse with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.supervised_runs", flag_provider["pyforge.marshal.supervised_runs"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.gate_evaluate")
def test_pyforge_marshal_gate_evaluate(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gates you can run (spec-pyforge-marshal CAP-3, Story 110.4): `marshal gate evaluate` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.gate_evaluate", flag_provider["pyforge.marshal.gate_evaluate"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.fleet_status")
def test_pyforge_marshal_fleet_status(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fleet visibility (spec-pyforge-marshal CAP-5, Story 110.5): `marshal status` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.fleet_status", flag_provider["pyforge.marshal.fleet_status"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.policy_composition")
def test_pyforge_marshal_policy_composition(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """policy composition (spec-pyforge-marshal CAP-7, Story 110.6): `marshal init|preflight|homes|teardown` refuse with usage code 2; no policy is ever composed from a second site."""
    _assert_verb_switch(
        "pyforge.marshal.policy_composition", flag_provider["pyforge.marshal.policy_composition"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.seed_explain")
def test_pyforge_marshal_seed_explain(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """operating model as data (spec-pyforge-marshal CAP-10, Story 110.7): `marshal seed explain` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.seed_explain", flag_provider["pyforge.marshal.seed_explain"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.managed_regions")
def test_pyforge_marshal_managed_regions(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """managed-region upgrades (spec-pyforge-marshal CAP-11, Story 110.8): `marshal seed update` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.managed_regions", flag_provider["pyforge.marshal.managed_regions"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.seed_adopt")
def test_pyforge_marshal_seed_adopt(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """adopt onto a living repo (spec-pyforge-marshal CAP-12, Story 110.9): `marshal seed adopt` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.seed_adopt", flag_provider["pyforge.marshal.seed_adopt"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.seed_check")
def test_pyforge_marshal_seed_check(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """seed check in CI (spec-pyforge-marshal CAP-13, Story 110.10): `marshal seed check` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.seed_check", flag_provider["pyforge.marshal.seed_check"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.genesis_state_file")
def test_pyforge_marshal_genesis_state_file(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """genesis-owned state file (spec-pyforge-marshal CAP-17, Story 110.12): `marshal seed init|adopt|update` refuse with usage code 2: the state file is load-bearing and is never skipped."""
    _assert_verb_switch(
        "pyforge.marshal.genesis_state_file", flag_provider["pyforge.marshal.genesis_state_file"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.watch")
def test_pyforge_marshal_watch(flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`marshal watch` reports what changed and a recommended delay (spec-pyforge-marshal CAP-154, Story 110.14): `marshal watch` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch("pyforge.marshal.watch", flag_provider["pyforge.marshal.watch"], tmp_path, monkeypatch)


@flag_states("pyforge.marshal.completion_from_facts")
def test_pyforge_marshal_completion_from_facts(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """completion is judged from git and process facts, never self-reports (spec-pyforge-marshal CAP-160, Story 110.15): the dispatch verbs refuse with usage code 2; completion is never judged from a self-report."""
    _assert_verb_switch(
        "pyforge.marshal.completion_from_facts",
        flag_provider["pyforge.marshal.completion_from_facts"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.verify_before_landing")
def test_pyforge_marshal_verify_before_landing(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a session's self-report is input to verification, never the verdict (spec-pyforge-marshal CAP-161, Story 110.16): the dispatch verbs and `marshal land` refuse with usage code 2; nothing lands on a self-report."""
    _assert_verb_switch(
        "pyforge.marshal.verify_before_landing",
        flag_provider["pyforge.marshal.verify_before_landing"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.dispatch_lands_via_land")
def test_pyforge_marshal_dispatch_lands_via_land(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dispatch lands through existing landing machinery, never a second path (spec-pyforge-marshal CAP-162, Story 110.17): the dispatch verbs refuse with usage code 2; no second landing path exists."""
    _assert_verb_switch(
        "pyforge.marshal.dispatch_lands_via_land",
        flag_provider["pyforge.marshal.dispatch_lands_via_land"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.branch_merged_divergence")
def test_pyforge_marshal_branch_merged_divergence(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`branch_merged` is never true on ancestry alone (spec-pyforge-marshal CAP-167, Story 110.19): the dispatch verbs refuse with usage code 2; ancestry alone never reads as merged."""
    _assert_verb_switch(
        "pyforge.marshal.branch_merged_divergence",
        flag_provider["pyforge.marshal.branch_merged_divergence"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.single_followup_review")
def test_pyforge_marshal_single_followup_review(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """after harness exit, at most one follow-up review, then land (spec-pyforge-marshal CAP-169, Story 110.20): the dispatch verbs refuse with usage code 2; a second review pass never starts."""
    _assert_verb_switch(
        "pyforge.marshal.single_followup_review",
        flag_provider["pyforge.marshal.single_followup_review"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.promotion_on_landing")
def test_pyforge_marshal_promotion_on_landing(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """promotion runs on landing, not on memory (spec-pyforge-marshal CAP-229, Story 110.22): `marshal land` refuses with usage code 2; a promotion is never run from memory."""
    _assert_verb_switch(
        "pyforge.marshal.promotion_on_landing",
        flag_provider["pyforge.marshal.promotion_on_landing"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.guild_env_shellouts")
def test_pyforge_marshal_guild_env_shellouts(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """marshal's shell-outs name the Guild env (spec-pyforge-marshal CAP-263, Story 110.24): `marshal watch` and `marshal gate evaluate` refuse with usage code 2; no shell-out ever names another env."""
    _assert_verb_switch(
        "pyforge.marshal.guild_env_shellouts",
        flag_provider["pyforge.marshal.guild_env_shellouts"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.ledger_promotion_to_origin")
def test_pyforge_marshal_ledger_promotion_to_origin(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a landing's ledger promotion reaches origin/main, and a failed one is never silent (spec-pyforge-marshal CAP-277, Story 110.27): `marshal land` refuses with usage code 2; a failed promotion is never silent."""
    _assert_verb_switch(
        "pyforge.marshal.ledger_promotion_to_origin",
        flag_provider["pyforge.marshal.ledger_promotion_to_origin"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.switch_script_placement")
def test_pyforge_marshal_switch_script_placement(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """the switch script runs where it is documented to run, or says in one line why it cannot (spec-pyforge-marshal CAP-278, Story 110.28): `marshal land` refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.switch_script_placement",
        flag_provider["pyforge.marshal.switch_script_placement"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.seed_check_rendered_paths")
def test_pyforge_marshal_seed_check_rendered_paths(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`marshal seed check` judges the paths the manifest means, never its unrendered placeholders (spec-pyforge-marshal CAP-279, Story 110.29): `marshal seed check` refuses with usage code 2; an unrendered placeholder is never judged."""
    _assert_verb_switch(
        "pyforge.marshal.seed_check_rendered_paths",
        flag_provider["pyforge.marshal.seed_check_rendered_paths"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.drain_followup_review")
def test_pyforge_marshal_drain_followup_review(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a drain runs the follow-up review a landed story recommended, gated by its deferred-work row, never by the ledger (spec-pyforge-marshal CAP-281, Story 110.30): `marshal factory drain` refuses with usage code 2; a follow-up review is never gated by the ledger."""
    _assert_verb_switch(
        "pyforge.marshal.drain_followup_review",
        flag_provider["pyforge.marshal.drain_followup_review"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.landing_memlog_union")
def test_pyforge_marshal_landing_memlog_union(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a landing unions append-only memlogs instead of refusing (spec-pyforge-marshal CAP-283, Story 110.32): `marshal land` refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.landing_memlog_union",
        flag_provider["pyforge.marshal.landing_memlog_union"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.model_list_refresh")
def test_pyforge_marshal_model_list_refresh(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """an operator-run refresh reads every harness's live model list and reports drift (spec-pyforge-marshal CAP-285, Story 110.33): `marshal adapters models` is listed disabled and refuses with usage code 2."""
    _assert_verb_switch(
        "pyforge.marshal.model_list_refresh", flag_provider["pyforge.marshal.model_list_refresh"], tmp_path, monkeypatch
    )


# --- behaviour switches read through one helper at their site ---------------------------------------------------


@flag_states("pyforge.marshal.adapter_fanout")
def test_pyforge_marshal_adapter_fanout(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """adapters from one contract (spec-pyforge-marshal CAP-16, Story 110.11): `seed adopt` renders no per-tool adapter file; existing adapter files are left untouched."""
    on = flag_provider["pyforge.marshal.adapter_fanout"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.adapter_fanout", on)
    assert adopt_verb.adapter_fanout_enabled() is on


@flag_states("pyforge.marshal.supervisor_shell_finalize")
def test_pyforge_marshal_supervisor_shell_finalize(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Supervisor finalizes when the harness cannot run shell (spec-pyforge-marshal CAP-141, Story 110.13): the supervisor leaves a shell-less session's leftover for the operator (`MRS-DISP-036`), as before."""
    on = flag_provider["pyforge.marshal.supervisor_shell_finalize"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.supervisor_shell_finalize", on)
    assert supervisor_main.supervisor_shell_finalize_enabled() is on


@flag_states("pyforge.marshal.one_in_flight_per_station")
def test_pyforge_marshal_one_in_flight_per_station(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """one story in flight per station, cross-station dispatches run concurrently (spec-pyforge-marshal CAP-163, Story 110.18): a second dispatch onto a busy station is not refused (`MRS-DISP-021` is never raised); the dependency and surface-overlap checks still run."""
    on = flag_provider["pyforge.marshal.one_in_flight_per_station"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.one_in_flight_per_station", on)
    assert dispatch_cli.one_in_flight_enabled() is on


@flag_states("pyforge.marshal.dispatch_only_fleet_rows")
def test_pyforge_marshal_dispatch_only_fleet_rows(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a dispatch-only checkout still has fleet rows (spec-pyforge-marshal CAP-259, Story 110.23): `marshal status` lists loop homes only; a dispatch-only station has no row, as before Story 51.12."""
    on = flag_provider["pyforge.marshal.dispatch_only_fleet_rows"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.dispatch_only_fleet_rows", on)
    assert status_cli.dispatch_only_fleet_rows_enabled() is on


@flag_states("pyforge.marshal.refresh_proven_push")
def test_pyforge_marshal_refresh_proven_push(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a loop-home refresh sends its proven fast-forward past the pre-push preflight, journaled (spec-pyforge-marshal CAP-267, Story 110.25): a refresh pushes without the opt-out, so the pre-push preflight runs, as before Story 57.1."""
    on = flag_provider["pyforge.marshal.refresh_proven_push"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.refresh_proven_push", on)
    assert refresh_cli.refresh_proven_push_enabled() is on


@flag_states("pyforge.marshal.followup_review_to_ledger")
def test_pyforge_marshal_followup_review_to_ledger(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """a follow-up review a landed story recommends is carried into the deferred-work ledger, never dropped (spec-pyforge-marshal CAP-275, Story 110.26): finalize adds no `DW-FRR` row and closes none; the recommendation stays in the story spec only."""
    on = flag_provider["pyforge.marshal.followup_review_to_ledger"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.followup_review_to_ledger", on)
    assert finalize_main.followup_review_to_ledger_enabled() is on


# --- behaviour switches: the fallback each story spec names --------------------------------------------------------


@flag_states("pyforge.marshal.front_door_environment")
def test_pyforge_marshal_front_door_environment(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-pyforge-core CAP-11 (Story 110.1): OFF reads an uninstalled roster station as unknown, as before."""
    on = flag_provider["pyforge.marshal.front_door_environment"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.front_door_environment", on)
    with pytest.raises(DispatchError) as raised:
        dispatch_argv(["pyforge", "warden"], script_map={"marshal": "marshal"})
    message = str(raised.value)
    if on:
        assert "is not installed in this environment" in message
        assert "pixi run -e pyforge-warden" in message
    else:
        assert "unknown station 'warden'" in message
        assert "not installed in this environment" not in message


@flag_states("pyforge.marshal.context_pipeline")
def test_pyforge_marshal_context_pipeline(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-174 (Story 110.21): OFF resolves every declared layer off, as a policy with no [context] block."""
    on = flag_provider["pyforge.marshal.context_pipeline"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.context_pipeline", on)
    assert policy.context_pipeline_enabled() is on
    declared = {"recall": {"enabled": True, "aggressiveness": "high"}, "output": {"enabled": True}}
    effective = SimpleNamespace(context=SimpleNamespace(value=declared))
    resolved = policy.resolve_context_layers(effective)
    assert set(resolved) == set(policy.CONTEXT_LAYER_NAMES)
    if on:
        assert resolved["recall"] == {"enabled": True, "aggressiveness": "high"}
        assert resolved["output"]["enabled"] is True
    else:
        assert all(layer["enabled"] is False for layer in resolved.values())
        assert resolved == policy.resolve_context_layers(SimpleNamespace(context=SimpleNamespace(value={})))


@flag_states("pyforge.marshal.dispatch_codegraph_index")
def test_pyforge_marshal_dispatch_codegraph_index(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-282 (Story 110.31): OFF seeds no index -- the layer-off shape, reason `flag off`."""
    on = flag_provider["pyforge.marshal.dispatch_codegraph_index"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.dispatch_codegraph_index", on)
    assert dispatch_cli.dispatch_codegraph_index_enabled() is on
    if not on:
        seed = dispatch_cli._seed_dispatch_structure_graph(
            fs=object(),  # type: ignore[arg-type] -- refused before any port is touched
            process=object(),  # type: ignore[arg-type]
            worktree=tmp_path / "wt",
            repo_root=tmp_path,
            context_payload={"structure-graph": {"enabled": True, "aggressiveness": "medium"}},
        )
        assert seed.mode == "skipped"
        assert seed.reason == "flag off"
        assert seed.applied is False
        assert not (tmp_path / "wt").exists()


def _recall_layer_case(key: str, on: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch, key, on)
    assert key in recall_feedback.RECALL_FLAG_KEYS
    assert recall_feedback.layer_enabled({"enabled": True, "aggressiveness": "medium"}) is on
    assert recall_feedback.layer_enabled({"enabled": False}) is False  # a declared-off layer stays off either way
    assert recall_feedback.layer_enabled(None) is False


@flag_states("pyforge.marshal.recall_dev_pass")
def test_pyforge_marshal_recall_dev_pass(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-288 (Story 110.34): OFF reads the recall layer off, so no query runs before the dev pass."""
    _recall_layer_case(
        "pyforge.marshal.recall_dev_pass", flag_provider["pyforge.marshal.recall_dev_pass"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.recall_review_pass")
def test_pyforge_marshal_recall_review_pass(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-289 (Story 110.35): OFF reads the recall layer off, so the review prompt carries no block."""
    _recall_layer_case(
        "pyforge.marshal.recall_review_pass", flag_provider["pyforge.marshal.recall_review_pass"], tmp_path, monkeypatch
    )


@flag_states("pyforge.marshal.recall_context_layer")
def test_pyforge_marshal_recall_context_layer(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-290 (Story 110.36): OFF resolves the [context.recall] layer as absent."""
    _recall_layer_case(
        "pyforge.marshal.recall_context_layer",
        flag_provider["pyforge.marshal.recall_context_layer"],
        tmp_path,
        monkeypatch,
    )


@flag_states("pyforge.marshal.recall_miss_injects_nothing")
def test_pyforge_marshal_recall_miss_injects_nothing(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAP-291 (Story 110.37): OFF disables recall entirely, so a miss or a failure has nothing to inject."""
    _recall_layer_case(
        "pyforge.marshal.recall_miss_injects_nothing",
        flag_provider["pyforge.marshal.recall_miss_injects_nothing"],
        tmp_path,
        monkeypatch,
    )


# --- the main() wiring, end to end, on one verb ---------------------------------------------------------------------


@flag_states("pyforge.marshal.fleet_status")
def test_main_projects_a_flag_off_verb_to_the_usage_code_with_the_message(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = flag_provider["pyforge.marshal.fleet_status"]
    _tree(tmp_path, monkeypatch, "pyforge.marshal.fleet_status", on)
    if on:
        pytest.skip("covered by the flag-off half")
    monkeypatch.chdir(tmp_path)
    result = invoke_cli(main, ["status"])
    assert result.exit_code == USAGE
    assert "marshal: flag pyforge.marshal.fleet_status is off" in result.output


def test_no_tree_reads_every_switch_on_without_a_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A checkout with no tree (no PYFORGE_FLAGS_PATH, no flags.json above cwd) never refuses and never warns."""
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    for path in retrofit_flags.VERB_FLAGS:
        retrofit_flags.require_verb_flags(_namespace(path))
    listing = " ".join(invoke_cli(main, ["--help"]).output.split())
    for key in retrofit_flags.KEY_VERBS:
        assert f"flag {key} is off" not in listing, key


def test_every_manifest_key_gates_a_verb_or_is_a_behaviour_switch() -> None:
    """The table is closed: every verb path KEY_VERBS names exists on the parser, and no key gates nothing."""
    parser_help = invoke_cli(main, ["--help"]).output
    for key, paths in retrofit_flags.KEY_VERBS.items():
        assert key.startswith("pyforge.marshal."), key
        assert paths, key
        for path in paths:
            assert re.search(rf"(?<![\w-]){re.escape(path[0])}(?![\w-])", parser_help), (key, path)
