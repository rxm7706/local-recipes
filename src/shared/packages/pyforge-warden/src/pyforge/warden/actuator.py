"""Opt-in, post-verdict fix-PR actuator (Story 6.9, FR40/D12).

This is the ONE module in ``pyforge.warden`` permitted forge-API network
egress -- everything else in the installed package opens no socket (NFR-S2);
this module opens one ONLY on the real ``--open-fix-prs`` path, wrapped in the
``_EGRESS_ACTIVE`` marker the test harness's narrow carve-out keys on. It is
strictly opt-in (no flag -> never invoked) and strictly post-verdict:
``cli.py`` calls ``run_actuator`` AFTER the rungs/findings are final and BEFORE
``assemble_report``, so the payload this produces flows only into the frozen,
pass-through ``ComplianceReport.actuation`` slot -- never into a rung, the
verdict, the status, or the exit code. It reads ``findings`` only; it never
writes or edits the scanned tree (all remediation content is created
forge-side). A failed PR-open is captured, never raised.

No import of ``verdict``; no exit-code logic; no lattice-order knowledge --
the ``test_verdict_sole_ownership.py`` guard stays green.

Closed remediation mapping (every other finding family yields NO proposal):

* ``vuln:<advisory>:<pkg>@<ver>``    -> ``upgrade`` PR (cites the advisory +
  current vulnerable version; does NOT compute a target version -- the OSV
  fixed bound is discarded upstream and ``Finding`` is schema-frozen, so
  precise target resolution + manifest editing are deferred to the ledger).
* ``hygiene:DEP002:<pkg>``           -> ``removal`` PR (deptry unused dep).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from urllib.error import HTTPError
from urllib.parse import urlencode

if TYPE_CHECKING:
    from .models import Finding

# The egress marker (Design Notes): the ONLY place a real socket is authorized
# to open in this package. ``GitHubForgeClient`` sets it True around each real
# urllib call; the conftest deny-harness carve-out permits a loopback connect
# ONLY while this is True. Default False -> deny stays the default everywhere
# else (dry-run, no-flag runs, and the whole rest of the package never set it).
_EGRESS_ACTIVE: ContextVar[bool] = ContextVar("_EGRESS_ACTIVE", default=False)

_USER_AGENT = "pyforge-warden-fix-pr-actuator/1.0"
_DEFAULT_API_URL = "https://api.github.com"
_BRANCH_PREFIX = "warden/fix/"

# Finding-id family -> action (closed). A hygiene id additionally gates on its
# DEP-code middle segment: only DEP002 (unused/obsolete dependency) maps.
_ACTION_UPGRADE = "upgrade"
_ACTION_REMOVAL = "removal"


@dataclass(frozen=True)
class RemediationProposal:
    """One actuatable finding turned into a PR request (pure data)."""

    finding_id: str
    action: str
    subject: str
    title: str
    body: str


@dataclass(frozen=True)
class PROutcome:
    """The result of acting (or planning to act) on one proposal.

    ``status`` is one of ``planned`` (dry-run), ``opened`` (a PR was created),
    ``skipped`` (an open PR already existed for the finding id), or ``failed``
    (the open -- or forge resolution -- errored; captured, never raised).
    ``pr_url``/``detail`` are the volatile fields, isolated by name."""

    finding_id: str
    action: str
    subject: str
    status: str
    pr_url: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class Actuation:
    """The whole actuator run, serialized verbatim into the frozen
    ``ComplianceReport.actuation`` slot. ``to_json_dict`` returns a
    JSON-serializable dict whose outcomes are deterministically sorted by
    finding id (volatile ``pr_url``/``detail`` ride in their own fields)."""

    dry_run: bool
    outcomes: tuple[PROutcome, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "dry_run": self.dry_run,
            "outcomes": [
                {
                    "finding_id": outcome.finding_id,
                    "action": outcome.action,
                    "subject": outcome.subject,
                    "status": outcome.status,
                    "pr_url": outcome.pr_url,
                    "detail": outcome.detail,
                }
                for outcome in sorted(
                    self.outcomes, key=lambda outcome: outcome.finding_id
                )
            ],
        }


class ForgeResolutionError(RuntimeError):
    """The forge token/repo could not be resolved from the environment."""


class ForgeResponseError(RuntimeError):
    """A forge API call returned an unusable response (e.g. a 2xx PR-open with
    no url) -- captured as a ``failed`` outcome, never a silent ``opened``."""


class _BranchExistsError(RuntimeError):
    """The remediation branch already exists on the forge -- a prior actuation
    (its PR may now be closed) or a mid-sequence orphan from an earlier failed
    open. ``run_actuator`` maps this to ``skipped``, so such a finding is never
    wedged into a permanent ``failed`` (with noisy stderr) on every later run."""


@runtime_checkable
class ForgeClient(Protocol):
    """The injectable forge seam. ``GitHubForgeClient`` is the default; tests
    substitute a fake with no network."""

    def existing_open_pr(self, finding_id: str) -> str | None:
        """The url of an already-open PR for this finding id, else ``None``."""
        ...

    def open_pull_request(self, proposal: RemediationProposal) -> str:
        """Open one PR for the proposal; return its url."""
        ...


def _branch_name(finding_id: str) -> str:
    """A deterministic, git-safe, collision-resistant branch for a finding id.

    A short digest of the EXACT id is appended so two distinct findings whose
    lossy slugs collide (advisory ids AND package names both contain hyphens,
    e.g. ``GHSA-a-b:c-pkg`` vs ``GHSA-a-b-c:pkg``) never share a branch -- which
    would otherwise make ``existing_open_pr`` match the wrong PR and silently
    skip a genuinely different vulnerability. The digest also guards the
    degenerate all-special-char id (empty slug)."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", finding_id).strip("-")
    digest = hashlib.sha256(finding_id.encode("utf-8")).hexdigest()[:8]
    return f"{_BRANCH_PREFIX}{slug}-{digest}" if slug else f"{_BRANCH_PREFIX}{digest}"


def _severity_tier(finding: Finding) -> str:
    severity = finding.severity
    return severity.tier.value if severity is not None else "none"


def _proposal_body(finding: Finding, action: str, advisory: str | None) -> str:
    """The PR body: finding id + severity + advisory + recommended action.

    AUD-WARDEN-024: do **not** embed ``finding.message`` — engine messages
    often contain absolute scan-tree paths that must not land in a public
    GitHub PR body. Operators still have the finding id + subject.
    """
    lines = [
        "Opened by warden's opt-in fix-PR actuator (post-verdict; the scan's "
        "status and exit code are unchanged).",
        "",
        f"Finding: {finding.id}",
        f"Axis: {finding.axis}",
        f"Severity: {_severity_tier(finding)}",
        f"Subject: {finding.subject or '(none)'}",
    ]
    if advisory is not None:
        lines.append(f"Advisory: {advisory}")
    lines.append("")
    if action == _ACTION_UPGRADE:
        lines.append(
            f"Recommended action: upgrade {finding.subject} to a release that "
            f"resolves {advisory}. Warden does not compute the fixed target "
            "version (deferred to v1.x); pick a fixed release and update the "
            "manifest."
        )
    else:
        lines.append(
            f"Recommended action: remove the unused dependency "
            f"{finding.subject} from the project's manifest (deptry DEP002)."
        )
    return "\n".join(lines)


def plan_remediations(
    findings: Sequence[Finding],
) -> tuple[RemediationProposal, ...]:
    """Map actuatable findings to proposals via the closed mapping; every
    non-actuatable family (missing/transitive/misplaced hygiene, license,
    currency, indeterminate sentinels, error drivers) yields nothing. Pure --
    no I/O, no client. Sorted by finding id for a deterministic PR order."""
    proposals: list[RemediationProposal] = []
    for finding in findings:
        family = finding.id.split(":", 1)[0]
        subject = finding.subject or ""
        if family == "vuln":
            advisory = finding.id.split(":", 2)[1]
            proposals.append(
                RemediationProposal(
                    finding_id=finding.id,
                    action=_ACTION_UPGRADE,
                    subject=subject,
                    title=f"warden: upgrade {subject} to resolve {advisory}",
                    body=_proposal_body(finding, _ACTION_UPGRADE, advisory),
                )
            )
        elif family == "hygiene":
            parts = finding.id.split(":", 2)
            dep_code = parts[1] if len(parts) >= 2 else ""
            if dep_code == "DEP002":
                proposals.append(
                    RemediationProposal(
                        finding_id=finding.id,
                        action=_ACTION_REMOVAL,
                        subject=subject,
                        title=f"warden: remove unused dependency {subject}",
                        body=_proposal_body(finding, _ACTION_REMOVAL, None),
                    )
                )
    return tuple(sorted(proposals, key=lambda proposal: proposal.finding_id))


def resolve_forge(
    env: Mapping[str, str] | None = None,
) -> tuple[str, str, str]:
    """Resolve ``(token, repo_slug, api_url)`` from the environment ONLY
    (mirrors ``feeds.resolve_cache_dir``'s injectable-``env`` shape) -- never a
    CLI flag. Token: ``GITHUB_TOKEN`` else ``GH_TOKEN``. Repo slug:
    ``GITHUB_REPOSITORY`` (``owner/name``). API base: ``GITHUB_API_URL`` else
    the public GitHub API. A missing token or an unresolvable repo slug raises
    ``ForgeResolutionError`` -- the caller records one ``failed`` outcome.

    (The spec's "else the git remote read-only" repo fallback is deferred:
    the binding constraint is env-only, injectable resolution -- a git
    subprocess read is neither, and is nondeterministic under the offline
    test harness. ``GITHUB_REPOSITORY`` is set for every GitHub-Actions run,
    the primary intended host.)"""
    source = env if env is not None else os.environ
    token = source.get("GITHUB_TOKEN") or source.get("GH_TOKEN")
    if not token:
        raise ForgeResolutionError(
            "no forge token in the environment (set GITHUB_TOKEN or GH_TOKEN)"
        )
    repo = source.get("GITHUB_REPOSITORY")
    if not repo or "/" not in repo:
        raise ForgeResolutionError(
            "no forge repo slug in the environment (set GITHUB_REPOSITORY to "
            "'owner/name')"
        )
    api_url = source.get("GITHUB_API_URL") or _DEFAULT_API_URL
    return token, repo, api_url.rstrip("/")


class GitHubForgeClient:
    """The default forge client: stdlib ``urllib`` against the GitHub REST
    API -- the sole place this package opens a socket, and only with
    ``_EGRESS_ACTIVE`` set. Mirrors ``scripts/refresh_kev_feed.py``'s
    ``Request(url, headers=...)`` + ``urlopen(..., timeout=...)  # noqa: S310``
    shape; no third-party HTTP dependency."""

    def __init__(
        self, token: str, repo: str, api_url: str, *, timeout: int = 30
    ) -> None:
        self._token = token
        self._repo = repo
        self._owner = repo.split("/", 1)[0]
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> GitHubForgeClient:
        token, repo, api_url = resolve_forge(env)
        return cls(token, repo, api_url)

    def _api(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, object] | None = None,
        query: dict[str, str] | None = None,
    ) -> object:
        url = f"{self._api_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": _USER_AGENT,
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )
        # The sole authorized egress: mark it so the test harness's carve-out
        # permits the loopback connect, and reset it the instant the call
        # returns (deny is the default again immediately after).
        marker = _EGRESS_ACTIVE.set(True)
        try:
            with urllib.request.urlopen(  # noqa: S310 -- stdlib egress, opt-in
                request, timeout=self._timeout
            ) as response:
                body = response.read().decode("utf-8")
        finally:
            _EGRESS_ACTIVE.reset(marker)
        return json.loads(body) if body else {}

    def existing_open_pr(self, finding_id: str) -> str | None:
        branch = _branch_name(finding_id)
        result = self._api(
            "GET",
            f"/repos/{self._repo}/pulls",
            query={"state": "open", "head": f"{self._owner}:{branch}"},
        )
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                url = first.get("html_url") or first.get("url")
                return str(url) if url is not None else ""
            return ""
        return None

    def open_pull_request(self, proposal: RemediationProposal) -> str:
        branch = _branch_name(proposal.finding_id)
        repo_info = self._api("GET", f"/repos/{self._repo}")
        base = "main"
        if isinstance(repo_info, dict) and repo_info.get("default_branch"):
            base = str(repo_info["default_branch"])
        base_branch = self._api("GET", f"/repos/{self._repo}/branches/{base}")
        commit = base_branch.get("commit", {}) if isinstance(base_branch, dict) else {}
        base_sha = commit.get("sha") if isinstance(commit, dict) else None
        inner = commit.get("commit", {}) if isinstance(commit, dict) else {}
        tree = inner.get("tree", {}) if isinstance(inner, dict) else {}
        base_tree = tree.get("sha") if isinstance(tree, dict) else None
        # An empty remediation commit (same tree as base) so the branch is one
        # commit ahead and the PR can open -- the actionable content rides in
        # the PR body, not a manifest diff (deferred to v1.x).
        new_commit = self._api(
            "POST",
            f"/repos/{self._repo}/git/commits",
            payload={
                "message": proposal.title,
                "tree": base_tree,
                "parents": [base_sha] if base_sha is not None else [],
            },
        )
        new_sha = new_commit.get("sha") if isinstance(new_commit, dict) else None
        try:
            self._api(
                "POST",
                f"/repos/{self._repo}/git/refs",
                payload={"ref": f"refs/heads/{branch}", "sha": new_sha},
            )
        except HTTPError as exc:
            # 422 == the ref already exists: this finding was already actuated
            # (its PR may since have been closed) or an earlier open failed
            # after the ref was created (orphan). Skip -- never re-fail forever.
            if exc.code == 422:
                raise _BranchExistsError(branch) from exc
            raise
        pull = self._api(
            "POST",
            f"/repos/{self._repo}/pulls",
            payload={
                "title": proposal.title,
                "head": branch,
                "base": base,
                "body": proposal.body,
            },
        )
        if isinstance(pull, dict):
            url = pull.get("html_url") or pull.get("url")
            if url is not None:
                return str(url)
        # A 2xx with no url is not a real success -- fail loudly rather than
        # record an ``opened`` outcome carrying no evidence of the PR.
        raise ForgeResponseError(
            "the forge accepted the PR open but returned no url"
        )


def run_actuator(
    findings: Sequence[Finding],
    *,
    dry_run: bool,
    env: Mapping[str, str] | None = None,
    client: ForgeClient | None = None,
) -> Actuation:
    """Build the closed-mapping plan and act on it. Dry-run records
    ``planned`` for every proposal and instantiates/calls NO client (no
    socket). The real path resolves the default ``GitHubForgeClient`` from the
    environment (a resolution failure is a single ``failed`` outcome), then per
    proposal dedups via ``existing_open_pr`` (``skipped``) before
    ``open_pull_request`` (``opened``) -- every exception is captured into a
    ``failed`` outcome, never raised, never a rung, never an exit code."""
    proposals = plan_remediations(findings)
    if dry_run:
        return Actuation(
            dry_run=True,
            outcomes=tuple(
                PROutcome(
                    finding_id=proposal.finding_id,
                    action=proposal.action,
                    subject=proposal.subject,
                    status="planned",
                )
                for proposal in proposals
            ),
        )
    if not proposals:
        return Actuation(dry_run=False, outcomes=())
    if client is None:
        try:
            client = GitHubForgeClient.from_env(env)
        except ForgeResolutionError as exc:
            return Actuation(
                dry_run=False,
                outcomes=(
                    PROutcome(
                        finding_id="",
                        action="",
                        subject="",
                        status="failed",
                        detail=f"forge resolution failed: {exc}",
                    ),
                ),
            )
    outcomes: list[PROutcome] = []
    for proposal in proposals:
        try:
            existing = client.existing_open_pr(proposal.finding_id)
            if existing is not None:
                outcomes.append(
                    PROutcome(
                        finding_id=proposal.finding_id,
                        action=proposal.action,
                        subject=proposal.subject,
                        status="skipped",
                        pr_url=existing or None,
                        detail="an open PR already exists for this finding id",
                    )
                )
                continue
            pr_url = client.open_pull_request(proposal)
            outcomes.append(
                PROutcome(
                    finding_id=proposal.finding_id,
                    action=proposal.action,
                    subject=proposal.subject,
                    status="opened",
                    pr_url=pr_url or None,
                )
            )
        except _BranchExistsError:
            # The branch already exists (prior actuation / orphan) -- a skip,
            # not a failure; never wedge the finding into a permanent failed.
            outcomes.append(
                PROutcome(
                    finding_id=proposal.finding_id,
                    action=proposal.action,
                    subject=proposal.subject,
                    status="skipped",
                    detail="a remediation branch already exists (prior "
                    "actuation; its PR may be closed)",
                )
            )
        except Exception as exc:  # noqa: BLE001 -- a failed open NEVER raises
            outcomes.append(
                PROutcome(
                    finding_id=proposal.finding_id,
                    action=proposal.action,
                    subject=proposal.subject,
                    status="failed",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
    return Actuation(dry_run=False, outcomes=tuple(outcomes))
