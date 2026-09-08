"""Epic 9's ``herald success`` CLI family: ``create`` (Story 9.2, scaled
down), ``review``/``publish``/``list``/``get`` (Story 9.3), and
``validate`` (Story 9.5, scaled down). Every test scopes storage to
``tmp_path`` via ``--repo-root`` -- none ever touches a real ``.herald/``
directory.
"""

from __future__ import annotations

import json

import pytest

from pyforge.herald import auth, claims, cli, evidence


@pytest.fixture(autouse=True)
def _stub_evidence_validation(monkeypatch):
    """Every evidence link in this file is a placeholder URL, not a real
    endpoint -- ``deny_network`` would fail any test that let a real
    ``validate_for_publish``/``validate_link`` call reach ``httpx2``.
    Individual tests override this stub when they need to exercise a
    broken-link path."""
    monkeypatch.setattr(evidence, "validate_for_publish", lambda url, **_k: None)

    class _AlwaysValid:
        is_valid = True

    monkeypatch.setattr(evidence, "validate_link", lambda url, **_k: _AlwaysValid())


# --- Story 9.2: create --------------------------------------------------


def test_create_writes_a_draft_and_prints_the_review_hint(capsys, tmp_path):
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "create",
            "warden",
            "--shipped-date",
            "2026-08-01",
            "--evidence-test-results",
            "https://ci.example/warden/tests",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "created draft claim" in out
    assert "herald success review" in out
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 1
    assert stored[0].project_name == "warden"
    assert stored[0].evidence[0].url == "https://ci.example/warden/tests"


def test_create_requires_no_operator_role(capsys, tmp_path, monkeypatch):
    """Creating a draft is the scaled-down equivalent of the original
    spec's webhook firing automatically -- never gated on operator role."""
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    rc = cli.main(["success", "--repo-root", str(tmp_path), "create", "warden"])
    assert rc == 0
    assert "unauthorized" not in capsys.readouterr().err


def test_create_all_three_evidence_flags(tmp_path):
    cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "create",
            "warden",
            "--evidence-test-results",
            "https://x/tests",
            "--evidence-metrics",
            "https://x/metrics",
            "--evidence-adoption",
            "https://x/adoption",
        ]
    )
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    types = {e.type for e in stored[0].evidence}
    assert types == {"test_results", "metrics", "adoption"}


# --- Story 11.3: --evidence-notice (cross-Moment evidence linking) -------


def test_create_with_evidence_notice_cites_an_existing_notice(tmp_path):
    from pyforge.herald import notices

    notices.author_notice(
        tmp_path,
        notice_type="deprecation",
        component="auth-api-v1",
        what="w",
        why="w",
        migration="m",
        deadline=None,
        reason_link=None,
        publish=True,
    )
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "create",
            "warden",
            "--evidence-notice",
            "auth-api-v1",
        ]
    )
    assert rc == 0
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert stored[0].evidence[0].type == "notice"
    assert stored[0].evidence[0].url == "auth-api-v1"


def test_create_with_evidence_notice_for_an_unknown_component_exits_1(capsys, tmp_path):
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "create",
            "warden",
            "--evidence-notice",
            "does-not-exist",
        ]
    )
    assert rc == 1
    assert "no notice found" in capsys.readouterr().err
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


# --- Story 9.3: review / list / get --------------------------------------


def test_review_displays_claim_and_evidence(capsys, tmp_path):
    claim = claims.create(
        tmp_path / claims.DEFAULT_CLAIMS_PATH,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://x", label="tests")],
    )
    rc = cli.main(["success", "--repo-root", str(tmp_path), "review", claim.id])
    assert rc == 0
    out = capsys.readouterr().out
    assert claim.id in out
    assert "warden" in out
    assert "tests" in out
    assert "herald success publish" in out


def test_review_unknown_claim_exits_1(capsys, tmp_path):
    rc = cli.main(["success", "--repo-root", str(tmp_path), "review", "nope"])
    assert rc == 1
    assert "ClaimNotFoundError" in capsys.readouterr().err


def test_review_never_checks_auth(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    rc = cli.main(["success", "--repo-root", str(tmp_path), "review", claim.id])
    assert rc == 0
    assert "unauthorized" not in capsys.readouterr().err


def test_list_with_no_claims_says_so(capsys, tmp_path):
    rc = cli.main(["success", "--repo-root", str(tmp_path), "list"])
    assert rc == 0
    assert "no claims found" in capsys.readouterr().out


def test_list_filters_by_status(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    draft = claims.create(claims_path, project_name="draft-one")
    published = claims.create(claims_path, project_name="published-one")
    claims.publish(claims_path, published.id, thesis="Shipped")
    rc = cli.main(
        ["success", "--repo-root", str(tmp_path), "list", "--status", "draft"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert draft.id in out
    assert published.id not in out


def test_list_json_emits_one_object_per_line(capsys, tmp_path):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claims.create(claims_path, project_name="warden")
    claims.create(claims_path, project_name="marshal")
    rc = cli.main(["success", "--repo-root", str(tmp_path), "--json", "list"])
    assert rc == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert "id" in payload
        assert "evidence" in payload


def test_bare_success_with_no_subcommand_still_lists(capsys, tmp_path):
    claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    rc = cli.main(["success", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert "warden" in capsys.readouterr().out


def test_get_shows_full_detail(capsys, tmp_path):
    claim = claims.create(
        tmp_path / claims.DEFAULT_CLAIMS_PATH,
        project_name="warden",
        evidence=[claims.Evidence(type="metrics", url="https://x", label="m")],
    )
    rc = cli.main(["success", "--repo-root", str(tmp_path), "get", claim.id])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"id: {claim.id}" in out
    assert "status: draft" in out
    assert "metrics" in out


def test_get_json(capsys, tmp_path):
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    rc = cli.main(["success", "--repo-root", str(tmp_path), "--json", "get", claim.id])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["id"] == claim.id


def test_get_unknown_claim_exits_1(capsys, tmp_path):
    rc = cli.main(["success", "--repo-root", str(tmp_path), "get", "nope"])
    assert rc == 1


# --- Story 9.3 + 9.5: publish (real, evidence-validated) -----------------


def test_publish_requires_operator_role(capsys, tmp_path, monkeypatch):
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "publish",
            claim.id,
            "--thesis",
            "x",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "unauthorized" in err
    assert (
        claims.read_one(tmp_path / claims.DEFAULT_CLAIMS_PATH, claim.id).status
        == "draft"
    )


def test_publish_with_operator_role_publishes(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(
        claims_path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://ci.example", label="t")
        ],
    )
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "publish",
            claim.id,
            "--thesis",
            "Shipped the thing",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "published" in out
    published = claims.read_one(claims_path, claim.id)
    assert published.status == "published"
    assert published.thesis == "Shipped the thing"
    assert published.evidence[0].validated is True


def test_publish_rejects_a_broken_evidence_link(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(
        claims_path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://broken", label="t")
        ],
    )
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)

    def _raise(url, **_kwargs):
        raise evidence.EvidenceLinkError(f"Evidence link broken: {url}.")

    monkeypatch.setattr(evidence, "validate_for_publish", _raise)
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "publish",
            claim.id,
            "--thesis",
            "Shipped",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "Evidence link broken" in err
    assert claims.read_one(claims_path, claim.id).status == "draft"


def test_publish_without_thesis_or_existing_one_fails(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(claims_path, project_name="warden")
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    rc = cli.main(["success", "--repo-root", str(tmp_path), "publish", claim.id])
    assert rc == 1
    assert "thesis" in capsys.readouterr().err


def test_publish_already_published_claim_fails(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(claims_path, project_name="warden")
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    args = [
        "success",
        "--repo-root",
        str(tmp_path),
        "publish",
        claim.id,
        "--thesis",
        "x",
    ]
    assert cli.main(args) == 0
    assert cli.main(args) == 1
    assert "ClaimStateError" in capsys.readouterr().err


# --- Story 9.5: validate (scaled-down weekly cron) ------------------------


def test_validate_one_claim(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://x", label="t")],
    )
    rc = cli.main(["success", "--repo-root", str(tmp_path), "validate", claim.id])
    assert rc == 0
    out = capsys.readouterr().out
    assert "revalidated claim" in out
    updated = claims.read_one(claims_path, claim.id)
    assert updated.evidence[0].validated is True
    assert updated.evidence[0].validated_at is not None


def test_validate_all(capsys, tmp_path):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://x", label="t")],
    )
    claims.create(
        claims_path,
        project_name="marshal",
        evidence=[claims.Evidence(type="metrics", url="https://y", label="m")],
    )
    rc = cli.main(["success", "--repo-root", str(tmp_path), "validate", "--all"])
    assert rc == 0
    assert "2 claim(s)" in capsys.readouterr().out


def test_validate_requires_exactly_one_of_claim_id_or_all(capsys, tmp_path):
    rc = cli.main(["success", "--repo-root", str(tmp_path), "validate"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "exactly one" in err


def test_validate_rejects_both_claim_id_and_all(capsys, tmp_path):
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    rc = cli.main(
        ["success", "--repo-root", str(tmp_path), "validate", claim.id, "--all"]
    )
    assert rc == 1


def test_validate_never_checks_auth(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    claim = claims.create(tmp_path / claims.DEFAULT_CLAIMS_PATH, project_name="warden")
    rc = cli.main(["success", "--repo-root", str(tmp_path), "validate", claim.id])
    assert rc == 0
    assert "unauthorized" not in capsys.readouterr().err


# --- help ------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["success", "create", "--help"],
        ["success", "review", "--help"],
        ["success", "list", "--help"],
        ["success", "get", "--help"],
        ["success", "validate", "--help"],
    ],
)
def test_success_subcommand_help_exits_0(capsys, argv):
    assert cli.main(argv) == 0
