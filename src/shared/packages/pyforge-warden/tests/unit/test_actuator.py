"""Unit tests for the fix-PR actuator (Story 6.9).

The closed remediation mapping, dry-run (no client, no socket), the real path
through an injected fake ``ForgeClient`` (opened / skipped-on-dedup /
failed-captured-never-raised), ``resolve_forge`` env reading (including the
unresolved -> single ``failed`` record), and ``Actuation.to_json_dict``'s
sorted, JSON-serializable shape. Every test runs under the suite's
deny-by-default socket harness, so any accidental real egress is a hard
failure.
"""

from __future__ import annotations

import json

import pytest

from pyforge.warden.actuator import (
    Actuation,
    ForgeResolutionError,
    PROutcome,
    RemediationProposal,
    _branch_name,
    plan_remediations,
    resolve_forge,
    run_actuator,
)
from pyforge.warden.models import (
    CurrencyInfo,
    CurrencyVerdict,
    Finding,
    LicenseInfo,
    LicenseVerdict,
    Severity,
    SeverityTier,
)


def _vuln_finding(
    advisory: str = "PDOS-FIXTURE-0001", pkg: str = "pdos-vuln-fixture"
) -> Finding:
    return Finding(
        id=f"vuln:{advisory}:{pkg}@1.0.0",
        axis="vulnerability",
        message=f"{pkg}: {advisory} (severity critical)",
        subject=pkg,
        severity=Severity(tier=SeverityTier.CRITICAL, raw="CVSS:3.1/…"),
    )


def _dep002_finding(pkg: str = "requests") -> Finding:
    return Finding(
        id=f"hygiene:DEP002:{pkg}",
        axis="hygiene",
        message=f"{pkg} defined as a dependency but not used",
        subject=pkg,
        severity=None,
    )


class _FakeForge:
    """An in-memory ForgeClient: records calls, opens no socket."""

    def __init__(
        self, *, existing: str | None = None, open_error: Exception | None = None
    ) -> None:
        self._existing = existing
        self._open_error = open_error
        self.dedup_calls: list[str] = []
        self.open_calls: list[RemediationProposal] = []

    def existing_open_pr(self, finding_id: str) -> str | None:
        self.dedup_calls.append(finding_id)
        return self._existing

    def open_pull_request(self, proposal: RemediationProposal) -> str:
        self.open_calls.append(proposal)
        if self._open_error is not None:
            raise self._open_error
        return f"https://forge.example/pull/{len(self.open_calls)}"


class _ExplodingForge:
    """A ForgeClient that fails the test if ANY method is called (proves the
    dry-run path instantiates/calls no client)."""

    def existing_open_pr(self, finding_id: str) -> str | None:  # pragma: no cover
        raise AssertionError("dry-run must not call the forge client")

    def open_pull_request(
        self, proposal: RemediationProposal
    ) -> str:  # pragma: no cover
        raise AssertionError("dry-run must not call the forge client")


# --- plan_remediations: the closed mapping ----------------------------------


def test_plan_maps_vuln_to_upgrade():
    (proposal,) = plan_remediations([_vuln_finding()])
    assert proposal.action == "upgrade"
    assert proposal.finding_id == "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
    assert proposal.subject == "pdos-vuln-fixture"
    # The advisory + current version ride in the body; no computed target.
    assert "PDOS-FIXTURE-0001" in proposal.body
    assert "does not compute" in proposal.body


def test_plan_maps_dep002_to_removal():
    (proposal,) = plan_remediations([_dep002_finding("requests")])
    assert proposal.action == "removal"
    assert proposal.finding_id == "hygiene:DEP002:requests"
    assert proposal.subject == "requests"
    assert "DEP002" in proposal.body


@pytest.mark.parametrize(
    "finding_id",
    [
        "hygiene:DEP001:some-module",  # missing dependency, not DEP002
        "hygiene:DEP004:misplaced",  # misplaced dev dependency
        "indeterminate:no-version:pkg@unspecified",
    ],
)
def test_plan_ignores_non_actuatable_families(finding_id):
    finding = Finding(
        id=finding_id,
        axis="hygiene" if finding_id.startswith("hygiene") else "vulnerability",
        message="…",
        subject="pkg",
        severity=None,
    )
    assert plan_remediations([finding]) == ()


def test_plan_ignores_license_and_currency_findings():
    license_finding = Finding(
        id="license:GPL-3.0-only:pkg@1.0.0",
        axis="license",
        message="…",
        subject="pkg",
        severity=None,
        license=LicenseInfo(
            expression="GPL-3.0-only", family=None, verdict=LicenseVerdict.DENIED
        ),
    )
    currency_finding = Finding(
        id="currency:unknown:leftpad@1.0.0",
        axis="currency",
        message="…",
        subject="leftpad",
        severity=None,
        currency=CurrencyInfo(verdict=CurrencyVerdict.UNKNOWN),
    )
    assert plan_remediations([license_finding, currency_finding]) == ()


def test_plan_is_sorted_by_finding_id():
    proposals = plan_remediations(
        [
            _vuln_finding("PDOS-FIXTURE-0009", "zzz"),
            _dep002_finding("aaa"),
        ]
    )
    ids = [proposal.finding_id for proposal in proposals]
    assert ids == sorted(ids)


# --- dry-run: no client, no socket ------------------------------------------


def test_dry_run_plans_without_touching_a_client():
    findings = [_vuln_finding(), _dep002_finding()]
    actuation = run_actuator(findings, dry_run=True, client=_ExplodingForge())
    assert actuation.dry_run is True
    assert [outcome.status for outcome in actuation.outcomes] == [
        "planned",
        "planned",
    ]
    assert {outcome.action for outcome in actuation.outcomes} == {
        "upgrade",
        "removal",
    }
    assert all(outcome.pr_url is None for outcome in actuation.outcomes)


def test_dry_run_with_no_actuatable_findings_has_zero_proposals():
    actuation = run_actuator(
        [Finding(id="hygiene:DEP001:some-module", axis="hygiene", message="…",
                 subject="some-module", severity=None)],
        dry_run=True,
    )
    assert actuation.dry_run is True
    assert actuation.outcomes == ()


# --- real path via an injected fake client ----------------------------------


def test_real_path_opens_a_pr_per_proposal():
    fake = _FakeForge(existing=None)
    findings = [_vuln_finding(), _dep002_finding()]
    actuation = run_actuator(findings, dry_run=False, client=fake)
    assert actuation.dry_run is False
    assert len(actuation.outcomes) == 2
    assert {outcome.status for outcome in actuation.outcomes} == {"opened"}
    assert all(outcome.pr_url for outcome in actuation.outcomes)
    assert len(fake.open_calls) == 2


def test_real_path_dedups_to_skipped_without_opening():
    fake = _FakeForge(existing="https://forge.example/pull/7")
    actuation = run_actuator([_vuln_finding()], dry_run=False, client=fake)
    (outcome,) = actuation.outcomes
    assert outcome.status == "skipped"
    assert outcome.pr_url == "https://forge.example/pull/7"
    assert fake.open_calls == []  # never re-opened


def test_real_path_captures_a_failed_open_never_raises():
    fake = _FakeForge(existing=None, open_error=RuntimeError("boom"))
    actuation = run_actuator([_vuln_finding()], dry_run=False, client=fake)
    (outcome,) = actuation.outcomes
    assert outcome.status == "failed"
    assert "boom" in (outcome.detail or "")
    assert outcome.pr_url is None


def test_real_path_with_no_proposals_never_resolves_a_client():
    # A non-actuatable-only run must not try to resolve/open anything, even
    # without a client and without credentials (would otherwise be a failed
    # resolution record).
    actuation = run_actuator(
        [Finding(id="indeterminate:no-version:leftpad@unspecified",
                 axis="vulnerability", message="…", subject="leftpad",
                 severity=None)],
        dry_run=False,
        env={},
        client=None,
    )
    assert actuation.outcomes == ()


# --- resolve_forge: environment only ----------------------------------------


def test_resolve_forge_reads_token_and_repo_from_env():
    token, repo, api_url = resolve_forge(
        {"GITHUB_TOKEN": "t0ken", "GITHUB_REPOSITORY": "owner/name"}
    )
    assert token == "t0ken"
    assert repo == "owner/name"
    assert api_url == "https://api.github.com"


def test_resolve_forge_prefers_github_token_then_gh_token():
    _, _, _ = resolve_forge({"GH_TOKEN": "gh", "GITHUB_REPOSITORY": "o/r"})
    token, _, _ = resolve_forge(
        {"GITHUB_TOKEN": "gt", "GH_TOKEN": "gh", "GITHUB_REPOSITORY": "o/r"}
    )
    assert token == "gt"


def test_resolve_forge_honors_api_url_override():
    _, _, api_url = resolve_forge(
        {
            "GITHUB_TOKEN": "t",
            "GITHUB_REPOSITORY": "o/r",
            "GITHUB_API_URL": "http://127.0.0.1:8080/",
        }
    )
    assert api_url == "http://127.0.0.1:8080"


@pytest.mark.parametrize(
    "env",
    [
        {},  # no token, no repo
        {"GITHUB_REPOSITORY": "o/r"},  # no token
        {"GITHUB_TOKEN": "t"},  # no repo
        {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "not-a-slug"},  # bad slug
    ],
)
def test_resolve_forge_raises_when_unresolvable(env):
    with pytest.raises(ForgeResolutionError):
        resolve_forge(env)


def test_run_actuator_records_a_single_failed_resolution_record():
    actuation = run_actuator(
        [_vuln_finding()], dry_run=False, env={}, client=None
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "failed"
    assert outcome.finding_id == ""
    assert "resolution" in (outcome.detail or "").lower()


# --- Actuation.to_json_dict -------------------------------------------------


def test_to_json_dict_is_sorted_and_json_serializable():
    actuation = Actuation(
        dry_run=False,
        outcomes=(
            PROutcome("vuln:Z:z@1", "upgrade", "z", "opened", "u2"),
            PROutcome("hygiene:DEP002:a", "removal", "a", "opened", "u1"),
        ),
    )
    payload = actuation.to_json_dict()
    # Round-trips through json unchanged (JSON-serializable).
    assert json.loads(json.dumps(payload)) == payload
    ids = [outcome["finding_id"] for outcome in payload["outcomes"]]
    assert ids == sorted(ids)
    assert payload["dry_run"] is False


# --- never writes the scanned tree ------------------------------------------


def _snapshot(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


def test_actuator_never_writes_the_tree(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    before = _snapshot(tmp_path)
    run_actuator([_vuln_finding(), _dep002_finding()], dry_run=True)
    run_actuator(
        [_vuln_finding()], dry_run=False, client=_FakeForge(existing=None)
    )
    assert _snapshot(tmp_path) == before


# --- branch-name injectivity (2026-07-24 review pass) -----------------------


def test_branch_name_is_injective_across_slug_colliding_ids():
    # Two DISTINCT vuln ids whose lossy slug collides (advisory ids AND package
    # names both carry hyphens) must NOT share a branch -- else existing_open_pr
    # would match the wrong PR and silently skip a different vulnerability.
    a = _branch_name("vuln:GHSA-a-b:c-pkg@1")
    b = _branch_name("vuln:GHSA-a-b-c:pkg@1")
    assert a != b


def test_branch_name_handles_a_degenerate_all_special_id():
    # An id that sanitizes to an empty slug still yields a valid, non-empty ref.
    name = _branch_name("::@")
    assert name.startswith("warden/fix/")
    assert not name.endswith("/")
