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
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "protected_refs_ruleset"


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


def test_fixture_match_exits_zero() -> None:
    lib = _load_lib()
    fixture_path = FIXTURES / "live_match.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
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


def test_missing_pattern_exits_one() -> None:
    doc = _matching_live_fixture()
    rs = next(r for r in doc["rulesets"] if r["name"] == "protected-refs-loop-branches")
    rs["conditions"]["ref_name"]["include"] = [
        p for p in rs["conditions"]["ref_name"]["include"] if "loop" not in p
    ]
    fixture_path = FIXTURES / "missing_loop_pattern.json"
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


def test_missing_rule_exits_one() -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["name"] == "protected-refs-loop-branches":
            rs["rules"] = [{"type": "deletion"}]
    fixture_path = FIXTURES / "missing_non_ff_rule.json"
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


def test_bypass_actors_exits_one() -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["target"] == "tag":
            rs["bypass_actors"] = [{"actor_id": 1, "actor_type": "RepositoryRole"}]
    fixture_path = FIXTURES / "bypass_actors.json"
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


def test_enforcement_drift_exits_one() -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        rs["enforcement"] = "disabled"
    fixture_path = FIXTURES / "enforcement_disabled.json"
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


def test_exclude_drift_exits_one() -> None:
    doc = _matching_live_fixture()
    for rs in doc["rulesets"]:
        if rs["name"] == "protected-refs-loop-branches":
            rs["conditions"]["ref_name"]["exclude"] = ["refs/heads/loop/skip/**"]
    fixture_path = FIXTURES / "exclude_drift.json"
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


def test_marshal_policy_drift_exits_one(tmp_path: Path) -> None:
    lib = _load_lib()
    policy = tmp_path / "marshal-policy.toml"
    policy.write_text(
        '[[protected_refs]]\nrefname = "refs/heads/loop/"\nkind = "operational-branch"\n',
        encoding="utf-8",
    )
    diffs = lib.compare_marshal_policy_to_roster(
        lib.load_roster(), policy_path=policy
    )
    assert any("attempt-preserve" in d for d in diffs)


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
