"""Acceptance tests for scripts/protected_refs_ruleset_check.py (Story 85.2 / CAP-165)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "protected_refs_ruleset_check.py"
LIB_PATH = REPO_ROOT / "scripts" / "_protected_refs_ruleset_lib.py"
DOCUMENT_PATH = REPO_ROOT / "docs" / "governance" / "rulesets" / "protected-refs.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_detector():
    return _load_module(DETECTOR_PATH, "protected_refs_ruleset_check_under_test")


def _load_lib():
    return _load_module(LIB_PATH, "protected_refs_ruleset_lib_under_test")


def _matching_live_fixture() -> dict:
    lib = _load_lib()
    return lib.render_document(lib.load_roster())


def test_document_renders_byte_identical_to_tracked() -> None:
    lib = _load_lib()
    rendered = lib.serialize_document(lib.render_document())
    on_disk = DOCUMENT_PATH.read_text(encoding="utf-8")
    assert on_disk == rendered


def test_fixture_match_exits_zero(tmp_path: Path) -> None:
    fixture_path = tmp_path / "live_match.json"
    fixture_path.write_text(json.dumps(_matching_live_fixture(), indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_missing_pattern_exits_one(tmp_path: Path) -> None:
    doc = _matching_live_fixture()
    rs = next(r for r in doc["rulesets"] if r["name"] == "protected-refs-loop-branches")
    rs["conditions"]["ref_name"]["include"] = [
        p for p in rs["conditions"]["ref_name"]["include"] if "loop" not in p
    ]
    fixture_path = tmp_path / "missing_loop_pattern.json"
    fixture_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "ref_name include" in proc.stdout or "rules" in proc.stdout


def test_missing_rule_exits_one(tmp_path: Path) -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["name"] == "protected-refs-loop-branches":
            rs["rules"] = [{"type": "deletion"}]
    fixture_path = tmp_path / "missing_non_ff_rule.json"
    fixture_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "non_fast_forward" in proc.stdout


def test_bypass_actors_exits_one(tmp_path: Path) -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["target"] == "tag":
            rs["bypass_actors"] = [{"actor_id": 1, "actor_type": "RepositoryRole"}]
    fixture_path = tmp_path / "bypass_actors.json"
    fixture_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "bypass_actors" in proc.stdout


def test_hand_edited_document_fails(tmp_path: Path) -> None:
    lib = _load_lib()
    detector = _load_detector()
    bad_doc = tmp_path / "protected-refs.json"
    bad_doc.write_text("{}\n", encoding="utf-8")
    diffs = detector.check_document_freshness(
        lib.load_roster(), document_path=bad_doc
    )
    assert any("byte-identical" in d for d in diffs)


def test_unauthenticated_rate_limit_exits_two() -> None:
    detector = _load_detector()
    with mock.patch.object(
        detector,
        "gh_has_authenticated_quota",
        return_value=(False, "gh api rate_limit shows no authenticated quota (core limit 60)"),
    ):
        with mock.patch.object(sys, "argv", ["protected_refs_ruleset_check.py"]):
            code = detector.main()
    assert code == 2


def test_unauthenticated_preserves_local_findings() -> None:
    detector = _load_detector()
    lib = _load_lib()
    with mock.patch.object(
        detector,
        "check_document_freshness",
        return_value=["document drift example"],
    ):
        with mock.patch.object(
            detector,
            "gh_has_authenticated_quota",
            return_value=(False, "no authenticated quota"),
        ):
            diffs, override = detector.run_check(
                roster=lib.load_roster(),
                fixture_live=None,
                repo="rxm7706/local-recipes",
                skip_live=False,
            )
    assert override == 2
    assert "document drift example" in diffs
    assert any("no authenticated quota" in d for d in diffs)


def test_enforcement_drift_exits_one(tmp_path: Path) -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        rs["enforcement"] = "disabled"
    fixture_path = tmp_path / "enforcement_disabled.json"
    fixture_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "enforcement" in proc.stdout


def test_exclude_drift_exits_one(tmp_path: Path) -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["name"] == "protected-refs-loop-branches":
            rs["conditions"]["ref_name"]["exclude"] = ["refs/heads/loop/skip/**"]
    fixture_path = tmp_path / "exclude_drift.json"
    fixture_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--fixture",
            str(fixture_path),
            "--skip-live",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "ref_name exclude" in proc.stdout


def test_api_error_exits_two() -> None:
    detector = _load_detector()
    with mock.patch.object(detector, "gh_has_authenticated_quota", return_value=(True, "")):
        with mock.patch.object(
            detector,
            "fetch_live_rulesets",
            return_value=(None, "HTTP 403"),
        ):
            lib = _load_lib()
            diffs, override = detector.run_check(
                roster=lib.load_roster(),
                fixture_live=None,
                repo="rxm7706/local-recipes",
                skip_live=False,
            )
    assert override == 2


def test_the_protected_ref_list_is_declared_once_in_the_roster() -> None:
    """Story 85.2: the list lives in guild-roster.json only. A copy in marshal-policy.toml duplicated it and
    broke marshal's strict policy loader, which refuses unknown top-level keys."""
    import tomllib

    policy = Path(__file__).resolve().parents[2] / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    assert "protected_refs" not in tomllib.loads(policy.read_text(encoding="utf-8"))


def test_mutation_missing_creation_rule_fails() -> None:
    lib = _load_lib()
    declared = lib.rulesets_by_name(lib.render_document())
    live = dict(declared)
    restrict = live.pop("protected-refs-restrict-preserve-branch-creation")
    restrict = dict(restrict)
    restrict["rules"] = []
    live["protected-refs-restrict-preserve-branch-creation"] = restrict
    diffs = lib.compare_ruleset_maps(declared, live)
    assert any("creation" in d for d in diffs)


def test_detector_declares_runtime_scope() -> None:
    detector = _load_detector()
    assert detector.DETECTOR == {"scope": "runtime"}


# --- Story 118.9 (spec-pyforge-steward CAP-178): gitops/** is written by the deploy key alone ---------


def _gitops(doc: dict) -> dict:
    return next(r for r in doc["rulesets"] if r["name"] == "protected-refs-gitops-branches")


def test_the_gitops_ruleset_is_the_only_one_with_a_bypass_actor() -> None:
    lib = _load_lib()
    doc = lib.render_document()
    gitops = _gitops(doc)
    assert gitops["conditions"]["ref_name"]["include"] == ["refs/heads/gitops/**"]
    assert [rule["type"] for rule in gitops["rules"]] == ["creation", "update", "deletion", "non_fast_forward"]
    assert gitops["bypass_actors"] == [{"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "always"}]
    assert all(rs["bypass_actors"] == [] for rs in doc["rulesets"] if rs is not gitops)


def test_a_live_gitops_ruleset_without_its_deploy_key_bypass_drifts() -> None:
    lib = _load_lib()
    declared = lib.rulesets_by_name(lib.render_document())
    live_doc = lib.render_document()
    _gitops(live_doc)["bypass_actors"] = []
    diffs = lib.compare_ruleset_maps(declared, lib.rulesets_by_name(live_doc))
    assert diffs == [
        "protected-refs-gitops-branches: bypass_actors [] != declared "
        "[{'actor_id': None, 'actor_type': 'DeployKey', 'bypass_mode': 'always'}]"
    ]


def test_a_live_gitops_ruleset_with_another_bypass_actor_drifts() -> None:
    lib = _load_lib()
    declared = lib.rulesets_by_name(lib.render_document())
    live_doc = lib.render_document()
    _gitops(live_doc)["bypass_actors"].append({"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"})
    diffs = lib.compare_ruleset_maps(declared, lib.rulesets_by_name(live_doc))
    assert len(diffs) == 1 and "protected-refs-gitops-branches: bypass_actors" in diffs[0]


def test_a_live_gitops_ruleset_missing_a_rule_drifts() -> None:
    lib = _load_lib()
    declared = lib.rulesets_by_name(lib.render_document())
    live_doc = lib.render_document()
    _gitops(live_doc)["rules"] = [{"type": "deletion"}, {"type": "non_fast_forward"}]
    diffs = lib.compare_ruleset_maps(declared, lib.rulesets_by_name(live_doc))
    assert any("missing rule 'creation'" in d for d in diffs)
    assert any("missing rule 'update'" in d for d in diffs)


def test_the_roster_may_name_only_a_deploy_key_bypass_on_a_branch() -> None:
    import pytest

    lib = _load_lib()
    roster = lib.load_roster()
    for bad in (
        {"refname": "refs/heads/x/", "kind": "operational-branch", "scope": "origin", "rules": ["deletion"], "bypass": ["RepositoryRole"]},
        {"refname": "refs/tags/x/", "kind": "legacy", "scope": "origin", "rules": ["deletion"], "bypass": ["DeployKey"]},
    ):
        with pytest.raises(ValueError):
            lib.render_document({**roster, "protected_refs": [*roster["protected_refs"], bad]})


def test_more_than_one_write_enabled_deploy_key_is_a_finding() -> None:
    lib = _load_lib()
    assert lib.deploy_key_findings([]) == []
    assert lib.deploy_key_findings([{"title": "GITOPS_DEPLOY_KEY", "read_only": False}, {"title": "ro", "read_only": True}]) == []
    (finding,) = lib.deploy_key_findings(
        [{"title": "GITOPS_DEPLOY_KEY", "read_only": False}, {"title": "other", "read_only": False}]
    )
    assert "2 write-enabled deploy keys (GITOPS_DEPLOY_KEY, other)" in finding


def test_the_live_check_reads_the_deploy_keys_and_fails_closed() -> None:
    detector = _load_detector()
    lib = _load_lib()
    roster = lib.load_roster()
    live = lib.rulesets_by_name(lib.render_document(roster))
    two_writers = [{"title": "a", "read_only": False}, {"title": "b", "read_only": False}]
    with mock.patch.object(detector, "gh_has_authenticated_quota", return_value=(True, "")), mock.patch.object(
        detector, "check_document_freshness", return_value=[]
    ), mock.patch.object(detector, "fetch_live_rulesets", return_value=(live, "")):
        with mock.patch.object(detector, "fetch_deploy_keys", return_value=(two_writers, "")):
            diffs, override = detector.run_check(roster=roster, fixture_live=None, repo="o/r", skip_live=False)
        assert override is None and len(diffs) == 1 and "write-enabled deploy keys" in diffs[0]
        with mock.patch.object(detector, "fetch_deploy_keys", return_value=(None, "HTTP 404")):
            diffs, override = detector.run_check(roster=roster, fixture_live=None, repo="o/r", skip_live=False)
        assert override == 2 and diffs == ["deploy key fetch failed: HTTP 404"]
        with mock.patch.object(detector, "_gh_json", return_value=({"not": "a list"}, "")):
            assert detector.fetch_deploy_keys("o/r") == (None, "deploy keys response was not an array")
        with mock.patch.object(detector, "_gh_json", return_value=([{"title": "k", "read_only": True}, "x"], "")):
            assert detector.fetch_deploy_keys("o/r") == ([{"title": "k", "read_only": True}], "")
