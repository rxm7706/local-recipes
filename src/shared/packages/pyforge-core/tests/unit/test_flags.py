"""Stories 76.1 / 76.2 -- the shipped flag tree, ``src/platform/config/flags.json``, and its overlay document.

What every flag in the repository's own tree must say: its owner, story and cleanup clock, and the value it
reads in each environment. These tests read the repository outside this package, so the module carries
``pytestmark = pytest.mark.live_tree`` and runs in the core suite's live-tree half (Story 117.7,
spec-pyforge-core:CAP-14); the flag reader's own tests, on synthetic trees, are in ``test_flags_reader.py``.

The shipped-flag tables stay here under their names: marshal's landing heal
(``FLAG_REGISTRY_PYTHON_TARGETS``) binds this path and ``_SHIPPED_CLOCKS``, ``expected`` and
``per_environment``. A new flag joins ``_SHIPPED_CLOCKS`` and one of ``expected`` / ``per_environment``;
a kill switch also joins ``_LATER_KILL_SWITCHES`` (``docs/reference/story-spec-flag-block.md``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.core import cutover_root, flags
from pyforge.core.flags import read_boolean

pytestmark = pytest.mark.live_tree


@pytest.fixture(autouse=True)
def _no_ambient_environment(monkeypatch):
    """A developer's or CI's own PYFORGE_ENVIRONMENT must not decide these reads."""
    monkeypatch.delenv(flags.ENV_ENVIRONMENT, raising=False)


# --- Story 76.1: the repository's own tree and overlay compose in every environment ---------


def test_the_shipped_overlay_composes_against_the_shipped_tree_in_every_environment():
    """A durable invariant of the repo's own pair (skips when the tree is not in this checkout)."""
    config = Path(__file__).resolve().parents[6] / "src" / "platform" / "config"
    tree, overlays = config / "flags.json", config / flags.OVERLAYS_FILE_NAME
    if not tree.is_file():
        pytest.skip("src/platform/config/flags.json is not in this checkout")
    assert overlays.is_file(), "the tree's value-only overlay document is missing"
    payload = json.loads(tree.read_text(encoding="utf-8"))
    document = flags.load_overlays(overlays)
    assert set(document) <= set(flags.ENVIRONMENTS)
    for environment in flags.ENVIRONMENTS:
        composed = flags.compose(payload, document, environment)
        assert set(composed["flags"]) == set(payload["flags"])  # an overlay defines nothing
        assert json.loads(flags.render(environment, flags_path=tree)) == composed


# The shipped tree: what every flag in src/platform/config/flags.json must say (Story 76.2).
_SHIPPED_CLOCKS = {
    # spec-feature-flag-governance CAP-7, the retrofit (operator ruling 2026-10-26): one kill switch per pre-rule
    # runtime capability, ON in every environment on mint day, so each clock runs from 2026-10-26 and the owning
    # station's retirement story is due 2027-01-24 (Q4: 90 days). Epics marshal 110, steward 114, atlas 42, scribe 29.
    "pyforge.marshal.front_door_environment": ("marshal", "110-1-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.loop_homes": ("marshal", "110-2-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.supervised_runs": ("marshal", "110-3-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.gate_evaluate": ("marshal", "110-4-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.fleet_status": ("marshal", "110-5-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.policy_composition": ("marshal", "110-6-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.seed_explain": ("marshal", "110-7-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.managed_regions": ("marshal", "110-8-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.seed_adopt": ("marshal", "110-9-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.seed_check": ("marshal", "110-10-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.adapter_fanout": ("marshal", "110-11-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.genesis_state_file": ("marshal", "110-12-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.supervisor_shell_finalize": ("marshal", "110-13-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.watch": ("marshal", "110-14-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.completion_from_facts": ("marshal", "110-15-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.verify_before_landing": ("marshal", "110-16-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.dispatch_lands_via_land": ("marshal", "110-17-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.one_in_flight_per_station": ("marshal", "110-18-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.branch_merged_divergence": ("marshal", "110-19-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.single_followup_review": ("marshal", "110-20-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.context_pipeline": ("marshal", "110-21-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.promotion_on_landing": ("marshal", "110-22-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.dispatch_only_fleet_rows": ("marshal", "110-23-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.guild_env_shellouts": ("marshal", "110-24-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.refresh_proven_push": ("marshal", "110-25-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.followup_review_to_ledger": ("marshal", "110-26-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.ledger_promotion_to_origin": ("marshal", "110-27-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.switch_script_placement": ("marshal", "110-28-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.seed_check_rendered_paths": ("marshal", "110-29-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.drain_followup_review": ("marshal", "110-30-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.dispatch_codegraph_index": ("marshal", "110-31-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.landing_memlog_union": ("marshal", "110-32-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.model_list_refresh": ("marshal", "110-33-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.recall_dev_pass": ("marshal", "110-34-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.recall_review_pass": ("marshal", "110-35-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.recall_context_layer": ("marshal", "110-36-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.marshal.recall_miss_injects_nothing": ("marshal", "110-37-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.budget": ("steward", "114-1-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.frame_upstream_check": ("steward", "114-2-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.workspace_clean": ("steward", "114-3-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.workspace_own_worktrees_only": ("steward", "114-4-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.deploy_perimeter": ("steward", "114-5-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.setup_hooks": ("steward", "114-6-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.workspace_full_refs": ("steward", "114-7-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.steward.station_client_identity": ("steward", "114-8-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.atlas.agent_pipeline_tools": ("atlas", "42-1-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.atlas.manifest_inventory": ("atlas", "42-2-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.scribe.bmad_estate_catalog": ("scribe", "29-1-", "2026-10-26", "2026-10-26", "2027-01-24"),
    "pyforge.cutover_root": ("steward", "44-12-", "2026-09-13", "", ""),
    "pyforge.steward.ghe_fleet_credentials": ("steward", "75-1-", "2026-09-29", "", ""),
    "pyforge.steward.object_store_consumer": ("steward", "74-1-", "2026-09-29", "", ""),
    "pyforge.steward.sync_github_only_marker": ("steward", "84-4-", "2026-10-03", "", ""),
    "pyforge.steward.workspace_preserve_tag": ("steward", "85-5-", "2026-10-04", "", ""),
    "pyforge.steward.herald_webhook_sidecar": ("steward", "87-3-", "2026-10-10", "", ""),
    "pyforge.steward.stations_index": (
        "steward",
        "91-1-",
        "2026-10-11",
        "",
        "",
    ),
    "pyforge.marshal.verify_fix_loop": ("marshal", "85-1-", "2026-10-03", "", ""),
    "pyforge.marshal.landing_ci_pauses": ("marshal", "100-1-", "2026-10-14", "", ""),
    "pyforge.marshal.egm_challenge": ("marshal", "113-1-", "2026-11-01", "", ""),
    "pyforge.marshal.egm_policy_block": ("marshal", "113-2-", "2026-11-01", "", ""),
    "pyforge.marshal.egm_dispatch_readiness": ("marshal", "113-3-", "2026-11-01", "", ""),
    "pyforge.marshal.egm_retro_drift": ("marshal", "113-4-", "2026-11-01", "", ""),
    "pyforge.marshal.egm_audit": ("marshal", "113-5-", "2026-11-01", "", ""),
    "pyforge.marshal.egm_resolve_bridge": ("marshal", "113-6-", "2026-11-01", "", ""),
    # Stories 87.3/87.7/87.15 share this key (default off in every environment).
    "pyforge.marshal.preserve_refs": ("marshal", "87-3-", "2026-10-04", "", ""),
    "pyforge.warden.fix_target_resolution": (
        "warden",
        "14-1-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fix_manifest_edit": (
        "warden",
        "14-2-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fix_draft_pr_estate": (
        "warden",
        "14-3-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fleet_inventory": (
        "warden",
        "16-1-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fleet_scan": (
        "warden",
        "16-2-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fleet_fix_proposals": (
        "warden",
        "16-3-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.fleet_project_items": (
        "warden",
        "16-5-",
        "2026-10-11",
        "",
        "",
    ),
    "pyforge.warden.non_python_ecosystems": (
        "warden",
        "16-4-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.warden.sast_opengrep": (
        "warden",
        "15-1-",
        "2026-09-28",
        "",
        "",
    ),
    "pyforge.atlas.dependency_history_sensor": ("atlas", "25-2-", "2026-09-28", "", ""),
    "pyforge.atlas.dependency_history": ("atlas", "25-1-", "2026-09-28", "", ""),
    "pyforge.atlas.viz_export_artifact": ("atlas", "30-1-", "2026-10-14", "", ""),
    "pyforge.atlas.vizro_static_boards": ("atlas", "30-2-", "2026-10-15", "", ""),
    "pyforge.atlas.live_public_sources": ("atlas", "34-4-", "2026-10-18", "", ""),
    "pyforge.atlas.live_vcs_universe": ("atlas", "35-1-", "2026-10-18", "", ""),
    "pyforge.atlas.basilisk_population": ("atlas", "36-1-", "2026-10-18", "", ""),
    "pyforge.atlas.identity_live_sources": ("atlas", "36-2-", "2026-10-18", "", ""),
    "pyforge.atlas.board_projections": ("atlas", "37-4-", "2026-10-22", "", ""),
    "pyforge.herald.deck_publish": ("herald", "29-1-", "2026-09-28", "", ""),
    # CAP-55 deck_viewer: Story 30.1 publish/twins; Story 30.2 portal + deck-twins API routes.
    "pyforge.herald.deck_viewer": ("herald", "30-1-", "2026-09-28", "", ""),
    "pyforge.herald.ci_surfaces_tile": ("herald", "39-1-", "2026-10-14", "", ""),
    "pyforge.herald.status_pages": ("herald", "42-1-", "2026-10-15", "", ""),
    "pyforge.herald.deck_export_native": ("herald", "32-1-", "2026-09-28", "", ""),
    "pyforge.steward.ledger_query_postgres_sync": (
        "steward",
        "65-1-",
        "2026-09-19",
        "",
        "",
    ),
    "pyforge.steward.ledger_query_dossier_export": (
        "steward",
        "65-1-",
        "2026-09-19",
        "",
        "",
    ),
    "pyforge.steward.ledger_query_vizro_dataset": (
        "steward",
        "65-1-",
        "2026-09-19",
        "",
        "",
    ),
    "pyforge.steward.ledger_query_herald_facts": (
        "steward",
        "65-1-",
        "2026-09-19",
        "",
        "",
    ),
    "pyforge.steward.ledger_query_jira_github_matrix": (
        "steward",
        "65-1-",
        "2026-09-19",
        "",
        "",
    ),
    "pyforge.steward.glass_export": ("steward", "61-3-", "2026-09-17", "", ""),
    "pyforge.steward.estate_refresh": ("steward", "100-2-", "2026-10-13", "", ""),
    # Story 99.3 minted; 99.4 / 99.5 reuse (CAP-166).
    "pyforge.steward.ci_pause_control": ("steward", "99-3-", "2026-10-13", "", ""),
    "pyforge.steward.pages_duty": ("steward", "102-2-", "2026-10-14", "", ""),
    # Story 103.6 (CAP-159): the touched-scope preflight; default off, dev on.
    "pyforge.steward.preflight_ci_arbitrates": ("steward", "103-6-", "2026-10-15", "", ""),
    # Story 109.3 (CAP-171): marketplace Pages regeneration; default off, dev on.
    "pyforge.steward.marketplace_pages": ("steward", "109-3-", "2026-10-21", "", ""),
    # Story 117.3 (CAP-175): critical-path lane admission; a kill switch ON everywhere from mint day, due 2027-01-25.
    "pyforge.steward.preflight_critical_path": ("steward", "117-3-", "2026-10-27", "2026-10-27", "2027-01-25"),
    "pyforge.steward.start_tool_cli": ("steward", "119-1-", "2026-11-06", "2026-11-06", "2027-02-04"),
    "pyforge.steward.start_loop_dispatch": ("steward", "119-4-", "2026-11-06", "", ""),
    "pyforge.steward.nkp_deploy": ("steward", "118-1-", "2026-10-31", "2026-10-31", "2027-01-29"),
    "pyforge.steward.nkp_packs": ("steward", "118-2-", "2026-10-31", "2026-10-31", "2027-01-29"),
    # Stories 121.1 / 121.2 (fnd:CAP-9): steward cutover plan's two write modes; registered by Story 124.4.
    "pyforge.steward.cutover_ledger_write": ("steward", "121-2-", "2026-11-10", "2026-11-10", "2027-02-08"),
}


def _shipped() -> tuple[dict, dict]:
    config = Path(__file__).resolve().parents[6] / "src" / "platform" / "config"
    tree = config / "flags.json"
    if not tree.is_file():
        pytest.skip("src/platform/config/flags.json is not in this checkout")
    return json.loads(tree.read_text(encoding="utf-8")), flags.load_overlays(config / flags.OVERLAYS_FILE_NAME)


def test_every_flag_in_the_shipped_tree_carries_the_five_string_fields():
    payload, overlays = _shipped()
    assert set(payload["flags"]) == set(_SHIPPED_CLOCKS), "a flag joined or left the tree: date it here"
    for key, entry in payload["flags"].items():
        metadata = entry["metadata"]
        assert tuple(metadata) == flags.METADATA_FIELDS, key  # exactly the five, in the documented order
        assert all(isinstance(value, str) for value in metadata.values()), key
    flags.check_metadata(payload["flags"], overlays)


def test_the_shipped_tree_records_each_flags_owner_story_and_dates():
    payload, _ = _shipped()
    for key, (owner, story_prefix, created, on_everywhere, cleanup_by) in _SHIPPED_CLOCKS.items():
        metadata = payload["flags"][key]["metadata"]
        assert metadata["owner"] == owner, key
        assert metadata["story"].startswith(story_prefix), key
        assert (metadata["created"], metadata["on_everywhere"], metadata["cleanup_by"]) == (
            created,
            on_everywhere,
            cleanup_by,
        ), key


# The CAP-7 retrofit kill switches (ON everywhere since mint day, 2026-10-26, each due 2027-01-24) and the kill
# switches minted since under the same rule (ON everywhere from mint day, due 90 days on): the only clocks the shipped
# tree runs. A new kill switch joins here with its own due date; a clock that stops is the removal story landing.
_RETROFIT_KILL_SWITCHES = frozenset(
    k for k, (_o, _s, created, on, _c) in _SHIPPED_CLOCKS.items() if on == created == "2026-10-26"
)
_LATER_KILL_SWITCHES = {
    "pyforge.steward.preflight_critical_path": "2027-01-25",  # steward Story 117.3 (CAP-175), minted 2026-10-27
    "pyforge.steward.start_tool_cli": "2027-02-04",  # steward Story 119.1
    "pyforge.steward.nkp_deploy": "2027-01-29",  # steward Story 118.1 (CAP-176), minted 2026-10-31
    "pyforge.steward.nkp_packs": "2027-01-29",  # steward Story 118.2 (CAP-177), minted 2026-10-31
    "pyforge.steward.cutover_ledger_write": "2027-02-08",  # steward Stories 121.1 / 121.2 (fnd:CAP-9), 2026-11-10
}


def test_the_only_running_cleanup_clocks_are_the_kill_switches():
    """Story 76.4 left no clock running; the retrofit (2026-10-26) starts one per kill switch, each due 2027-01-24, and
    every kill switch minted since runs its own 90-day clock from its mint day."""
    payload, _ = _shipped()
    running = {k: e["metadata"]["cleanup_by"] for k, e in payload["flags"].items() if e["metadata"]["cleanup_by"]}
    assert set(running) == _RETROFIT_KILL_SWITCHES | set(_LATER_KILL_SWITCHES)
    assert {k: v for k, v in running.items() if k in _RETROFIT_KILL_SWITCHES} == dict.fromkeys(
        _RETROFIT_KILL_SWITCHES, "2027-01-24"
    )
    assert {k: v for k, v in running.items() if k in _LATER_KILL_SWITCHES} == _LATER_KILL_SWITCHES
    assert len(_RETROFIT_KILL_SWITCHES) == 48


def test_the_shipped_tree_reads_the_same_values_in_every_environment_as_before_the_metadata(monkeypatch):
    """Metadata is inert to evaluation: the values Story 76.1 shipped, per environment."""
    payload, _ = _shipped()
    config = Path(__file__).resolve().parents[6] / "src" / "platform" / "config" / "flags.json"
    expected = {
        "pyforge.steward.ghe_fleet_credentials": False,
        "pyforge.steward.ledger_query_postgres_sync": False,
        "pyforge.steward.ledger_query_dossier_export": False,
        "pyforge.steward.ledger_query_vizro_dataset": False,
        "pyforge.steward.ledger_query_herald_facts": False,
        "pyforge.steward.ledger_query_jira_github_matrix": False,
        "pyforge.steward.glass_export": False,
        "pyforge.marshal.preserve_refs": False,
        "pyforge.steward.start_loop_dispatch": False,
        "pyforge.marshal.egm_challenge": False,
        "pyforge.marshal.egm_policy_block": False,
        "pyforge.marshal.egm_dispatch_readiness": False,
        "pyforge.marshal.egm_retro_drift": False,
        "pyforge.marshal.egm_audit": False,
        "pyforge.marshal.egm_resolve_bridge": False,
    }
    # Story 84.4 / 85.3 / 74.2: per-environment booleans (object_store_consumer, sync_github_only_marker and
    # verify_fix_loop on in dev/staging, off in production).
    per_environment = {
        # CAP-7 retrofit kill switches: ON in every environment.
        "pyforge.marshal.front_door_environment": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.loop_homes": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.supervised_runs": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.gate_evaluate": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.fleet_status": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.policy_composition": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.seed_explain": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.managed_regions": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.seed_adopt": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.seed_check": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.adapter_fanout": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.genesis_state_file": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.supervisor_shell_finalize": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.watch": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.completion_from_facts": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.verify_before_landing": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.dispatch_lands_via_land": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.one_in_flight_per_station": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.branch_merged_divergence": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.single_followup_review": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.context_pipeline": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.promotion_on_landing": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.dispatch_only_fleet_rows": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.guild_env_shellouts": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.refresh_proven_push": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.followup_review_to_ledger": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.ledger_promotion_to_origin": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.switch_script_placement": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.seed_check_rendered_paths": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.drain_followup_review": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.dispatch_codegraph_index": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.landing_memlog_union": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.model_list_refresh": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.recall_dev_pass": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.recall_review_pass": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.recall_context_layer": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.recall_miss_injects_nothing": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.budget": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.frame_upstream_check": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.workspace_clean": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.workspace_own_worktrees_only": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.deploy_perimeter": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.setup_hooks": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.workspace_full_refs": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.station_client_identity": {"dev": True, "staging": True, "production": True},
        "pyforge.atlas.agent_pipeline_tools": {"dev": True, "staging": True, "production": True},
        "pyforge.atlas.manifest_inventory": {"dev": True, "staging": True, "production": True},
        "pyforge.scribe.bmad_estate_catalog": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.object_store_consumer": {"dev": True, "staging": True, "production": False},
        "pyforge.steward.sync_github_only_marker": {"dev": True, "staging": True, "production": False},
        "pyforge.steward.workspace_preserve_tag": {"dev": False, "staging": False, "production": False},
        "pyforge.steward.herald_webhook_sidecar": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.stations_index": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.estate_refresh": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.ci_pause_control": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.pages_duty": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.preflight_ci_arbitrates": {"dev": True, "staging": False, "production": False},
        "pyforge.steward.marketplace_pages": {"dev": True, "staging": False, "production": False},
        # Story 117.3 (CAP-175): critical-path lane admission, a kill switch ON in every environment.
        "pyforge.steward.preflight_critical_path": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.start_tool_cli": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.nkp_deploy": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.nkp_packs": {"dev": True, "staging": True, "production": True},
        "pyforge.steward.cutover_ledger_write": {"dev": True, "staging": True, "production": True},
        "pyforge.marshal.verify_fix_loop": {"dev": True, "staging": True, "production": False},
        "pyforge.marshal.landing_ci_pauses": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.dependency_history_sensor": {"dev": True, "staging": True, "production": False},
        "pyforge.atlas.dependency_history": {"dev": True, "staging": True, "production": False},
        "pyforge.atlas.viz_export_artifact": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.vizro_static_boards": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.live_public_sources": {"dev": True, "staging": True, "production": False},
        "pyforge.atlas.live_vcs_universe": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.basilisk_population": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.identity_live_sources": {"dev": True, "staging": False, "production": False},
        "pyforge.atlas.board_projections": {"dev": True, "staging": False, "production": False},
        "pyforge.warden.fix_target_resolution": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fix_manifest_edit": {"dev": True, "staging": True, "production": False},
        "pyforge.herald.deck_publish": {"dev": True, "staging": True, "production": False},
        "pyforge.herald.deck_viewer": {"dev": True, "staging": True, "production": False},
        "pyforge.herald.ci_surfaces_tile": {"dev": True, "staging": False, "production": False},
        "pyforge.herald.status_pages": {"dev": True, "staging": False, "production": False},
        "pyforge.herald.deck_export_native": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fix_draft_pr_estate": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fleet_inventory": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fleet_scan": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fleet_fix_proposals": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.fleet_project_items": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.non_python_ecosystems": {"dev": True, "staging": True, "production": False},
        "pyforge.warden.sast_opengrep": {"dev": True, "staging": True, "production": False},
    }
    assert {k for k, e in payload["flags"].items() if all(isinstance(v, bool) for v in e["variants"].values())} == set(
        expected
    ) | set(per_environment)
    for environment in flags.ENVIRONMENTS:
        monkeypatch.setenv(flags.ENV_ENVIRONMENT, environment)
        for key, value in expected.items():
            assert read_boolean(key, not value, flags_path=config) is value, (environment, key)
        for key, by_environment in per_environment.items():
            value = by_environment[environment]
            assert read_boolean(key, not value, flags_path=config) is value, (environment, key)
        assert cutover_root.read_cutover_root(config) == "local-recipes", environment
        rendered = json.loads(flags.render(environment, flags_path=config))
        assert {k: e["defaultVariant"] for k, e in rendered["flags"].items()} == {
            k: e["defaultVariant"] for k, e in payload["flags"].items()
        } | {k: ("on" if by_environment[environment] else "off") for k, by_environment in per_environment.items()}
