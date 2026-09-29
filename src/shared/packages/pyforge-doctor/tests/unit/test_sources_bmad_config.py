"""Unit tests for ``sources.bmad_config`` (Story 20.2 / Epic 20).

Covers the spec's I/O & Edge-Case Matrix: today's real tracked config (one
OK Finding naming the checked-key count, the ``agents`` repetition produces
none), a planted collision matching the exact 2026-09-06 incident shape, a
missing layer file, malformed TOML in one layer, and the ``agents``
top-level exclusion in isolation -- plus unit coverage for each private
helper (``_load_layer``, ``_structural_merge``, ``_find_leaf_paths``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import bmad_config

# --- _load_layer ----------------------------------------------------------


def test_load_layer_returns_parsed_table_on_success(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("[core]\na = 1\n", encoding="utf-8")

    assert bmad_config._load_layer(path) == {"core": {"a": 1}}


def test_load_layer_missing_file_folds_to_empty(tmp_path: Path):
    assert bmad_config._load_layer(tmp_path / "does-not-exist.toml") == {}


def test_load_layer_malformed_toml_folds_to_empty(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("this is not [valid toml", encoding="utf-8")

    assert bmad_config._load_layer(path) == {}


def test_load_layer_non_table_toml_folds_to_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "config.toml"
    path.write_text("a = 1\n", encoding="utf-8")
    monkeypatch.setattr(bmad_config.tomllib, "load", lambda stream: ["not", "a", "table"])

    assert bmad_config._load_layer(path) == {}


def test_load_layer_non_utf8_file_folds_to_empty(tmp_path: Path):
    # tomllib.load raises UnicodeDecodeError (a ValueError subclass, not an
    # OSError/TOMLDecodeError) for a non-UTF-8-encoded layer file -- must
    # fold to {} like every other malformed-layer case, not escape past
    # _load_layer.
    path = tmp_path / "config.toml"
    path.write_bytes('a = "caf\xe9"\n'.encode("latin-1"))

    assert bmad_config._load_layer(path) == {}


# --- _structural_merge ------------------------------------------------------


def test_structural_merge_override_wins_on_scalar_conflict():
    assert bmad_config._structural_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_structural_merge_recursively_merges_nested_dicts():
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}
    assert bmad_config._structural_merge(base, override) == {"a": {"x": 1, "y": 2}}


def test_structural_merge_override_scalar_replaces_base_dict_wholesale():
    base = {"a": {"x": 1}}
    override = {"a": 2}
    assert bmad_config._structural_merge(base, override) == {"a": 2}


def test_structural_merge_override_dict_replaces_base_scalar_wholesale():
    base = {"a": 1}
    override = {"a": {"y": 2}}
    assert bmad_config._structural_merge(base, override) == {"a": {"y": 2}}


# --- _find_leaf_paths --------------------------------------------------------


def test_find_leaf_paths_single_leaf():
    assert bmad_config._find_leaf_paths({"a": 1}) == {"a": ["a"]}


def test_find_leaf_paths_colliding_leaf_at_two_paths():
    data = {"a": 1, "b": {"a": 2}}
    assert bmad_config._find_leaf_paths(data) == {"a": ["a", "b.a"]}


def test_find_leaf_paths_agents_shaped_repetition_produces_zero_matches():
    data = {
        "agents": {
            "one": {"name": "Alice"},
            "two": {"name": "Bob"},
        }
    }
    assert bmad_config._find_leaf_paths(data) == {}


def test_find_leaf_paths_list_value_is_a_dead_end():
    assert bmad_config._find_leaf_paths({"a": [1, 2, 3]}) == {}


def test_find_leaf_paths_list_of_tables_is_also_a_dead_end():
    # A TOML array-of-tables is never a scannable collection of leaves --
    # its contents (dicts, here) are never recursed into either, same as a
    # list of scalars above.
    assert bmad_config._find_leaf_paths({"a": [{"x": 1}, {"y": 2}]}) == {}


def test_find_leaf_paths_nested_agents_key_is_not_excluded():
    # The exclusion is scoped to the TOP-LEVEL "agents" key only -- a nested
    # key that happens to be named "agents" is scanned normally.
    data = {"nested": {"agents": {"z": 5}}}
    assert bmad_config._find_leaf_paths(data) == {"z": ["nested.agents.z"]}


# --- gather() -----------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_gather_on_empty_target_returns_ok_with_zero_checked(tmp_path: Path):
    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_RENDER_CONFIG_AMBIGUITY
    assert finding.check == "bmad-render-config-ambiguity"
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["checked"] == 0
    # Sharpened wording: 0 checked must not read as "verified clean" --
    # nothing was there to check at all.
    assert "no central config layers found" in finding.message


def test_missing_user_layers_are_treated_as_empty(tmp_path: Path):
    _write(tmp_path / "_bmad" / "config.toml", "[core]\na = 1\n")
    # No config.user.toml, no custom/ dir at all.

    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["checked"] == 1


def test_malformed_toml_layer_folds_to_empty_and_other_layers_still_merge(
    tmp_path: Path,
):
    _write(tmp_path / "_bmad" / "config.toml", "not [valid toml")
    _write(tmp_path / "_bmad" / "custom" / "config.toml", '[core]\nfoo = "bar"\n')

    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["checked"] == 1


def test_planted_collision_matches_the_2026_09_06_incident_shape(tmp_path: Path):
    _write(
        tmp_path / "_bmad" / "config.toml",
        '[core]\nuser_skill_level = "intermediate"\n',
    )
    _write(
        tmp_path / "_bmad" / "custom" / "config.toml",
        '[modules.bmm]\nuser_skill_level = "advanced"\n',
    )

    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == DoctorStatus.WARN
    assert "user_skill_level" in finding.message
    assert "core.user_skill_level" in finding.message
    assert "modules.bmm.user_skill_level" in finding.message
    assert finding.evidence["key"] == "user_skill_level"
    assert set(finding.evidence["paths"]) == {
        "core.user_skill_level",
        "modules.bmm.user_skill_level",
    }


def test_agents_top_level_repetition_produces_no_finding(tmp_path: Path):
    _write(
        tmp_path / "_bmad" / "config.toml",
        '[agents.one]\nname = "Alice"\n\n[agents.two]\nname = "Bob"\n',
    )

    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["checked"] == 0


# The real tracked layer content, copied VERBATIM (not read live from disk --
# this file's own isolation convention) to prove the empirical "11 checked, 0
# ambiguous" claim the spec's Boundaries rely on. If the tracked files change,
# this fixture must be updated deliberately, not silently re-synced.
_REAL_BMAD_CONFIG_TOML = """\
# ─────────────────────────────────────────────────────────────────
# Installer-managed. Regenerated on every install — treat as read-only.
#
# Direct edits to this file will be overwritten on the next install.
# To change an install answer durably, re-run the installer (your prior
# answers are remembered as defaults). To pin a value regardless of
# install answers, or to add custom agents / override descriptors, use:
#   _bmad/custom/config.toml       (team, committed)
#   _bmad/custom/config.user.toml  (personal, gitignored)
# Those files are never touched by the installer.
# ─────────────────────────────────────────────────────────────────

[core]
project_name = "local-recipes"
document_output_language = "English"
output_folder = "{project-root}/_bmad-output"

[modules.bmm]
planning_artifacts = "{project-root}/_bmad-output/planning-artifacts"
implementation_artifacts = "{project-root}/_bmad-output/implementation-artifacts"
project_knowledge = "{project-root}/docs"

[modules.skf]
sidecar_path = "{project-root}/{value}"
skills_output_folder = "{project-root}/.claude/skills"
forge_data_folder = "{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data"

[agents.bmad-agent-analyst]
module = "bmm"
team = "software-development"
name = "Mary"
title = "Business Analyst"
icon = "📊"
description = "Channels Porter's strategic rigor and Minto's Pyramid Principle, grounds every finding in verifiable evidence, represents every stakeholder voice. Speaks like a treasure hunter narrating the find: thrilled by every clue, precise once the pattern emerges."

[agents.bmad-agent-pm]
module = "bmm"
team = "software-development"
name = "John"
title = "Product Manager"
icon = "📋"
description = "Drives Jobs-to-be-Done over template filling, user value first, technical feasibility is a constraint not the driver. Speaks like a detective interrogating a cold case: short questions, sharper follow-ups, every 'why?' tightening the net."

[agents.bmad-agent-ux-designer]
module = "bmm"
team = "software-development"
name = "Sally"
title = "UX Designer"
icon = "🎨"
description = "Balances empathy with edge-case rigor, starts simple and evolves through feedback, every decision serves a genuine user need. Speaks like a filmmaker pitching the scene before the code exists, painting user stories that make you feel the problem."

[agents.bmad-agent-architect]
module = "bmm"
team = "software-development"
name = "Winston"
title = "System Architect"
icon = "🏗️"
description = "Favors boring technology for stability, developer productivity as architecture, ties every decision to business value. Speaks like a seasoned engineer at the whiteboard: measured, always laying out trade-offs rather than verdicts."

[agents.bmad-agent-dev]
module = "bmm"
team = "software-development"
name = "Amelia"
title = "Senior Software Engineer"
icon = "💻"
description = "Test-first discipline (red, green, refactor), 100% pass before review, no fluff all precision. Speaks like a terminal prompt: exact file paths, AC IDs, and commit-message brevity — every statement citable."
"""

_REAL_BMAD_CUSTOM_CONFIG_TOML = """\
# Team / enterprise overrides for _bmad/config.toml.
# Committed to the repo — applies to every developer on the project.
# Tables deep-merge over base config; keyed entries merge by key.
# Example: override an agent descriptor, or add a new agent.
#
# [agents.bmad-agent-pm]
# description = "Prefers short, bulleted PRDs over narrative drafts."

# BMAD 6.11 upgrade (a7547d7c03) dropped `communication_language` and
# `user_skill_level` from `_bmad/config.toml`'s [core] table; render_skill.py's
# load_central_config() merges only the four `_bmad/config*.toml` /
# `_bmad/custom/config*.toml` layers, so skills that render (bmad-build,
# bmad-build-auto, ...) HALT with "missing config value" without a tracked pin
# (the installer's `_bmad/config.user.toml` is gitignored — a fresh clone has
# no user layer at all).
#
# NOTE: render_skill.py's `_find_config_values()` scans the merged tree for the
# bare key and raises "ambiguous config value" when the SAME key sits at two
# different paths. The 6.12 installer writes `user_skill_level` under
# [modules.bmm] and `communication_language` under [core] in its regenerated
# `_bmad/config.user.toml` — so these pins MUST sit at those exact paths
# (same path = merge; a different path = HALT, seen live 2026-09-06 when the
# 6.11-era `[core] user_skill_level` pin collided with the regenerated user
# layer). Values mirror `_bmad/bmm/config.yaml`.
[core]
communication_language = "English"

[modules.bmm]
user_skill_level = "intermediate"

# skf (bmad-module-skill-forge) install answers, pinned. The 6.12 core update
# regenerated `_bmad/config.toml`'s [modules.skf] block from module.yaml
# defaults (and a literal "{project-root}/{value}" for the prompt:false
# sidecar key); base/user tomls are "regenerated on every install", this file
# is the pin layer. The skf skills themselves read `_bmad/skf/config.yaml`,
# which the steward CAP-7 reconcile restores from git after every apply —
# keep the two in step. Recorded answers: _bmad/_config/skf-manifest.yaml
# (forge_data_folder, 2026-07-17) and commit d9017e368c (export targets).
[modules.skf]
sidecar_path = "{project-root}/_bmad/_memory/forger-sidecar"
skills_output_folder = "{project-root}/.claude/skills"
forge_data_folder = "{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data"
"""


def test_real_tracked_config_reports_ok_with_eleven_checked(tmp_path: Path):
    _write(tmp_path / "_bmad" / "config.toml", _REAL_BMAD_CONFIG_TOML)
    _write(tmp_path / "_bmad" / "custom" / "config.toml", _REAL_BMAD_CUSTOM_CONFIG_TOML)

    findings = bmad_config.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["checked"] == 11
