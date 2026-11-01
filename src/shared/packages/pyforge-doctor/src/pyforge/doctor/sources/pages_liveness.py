"""Story 48.2 (CAP-91 / FR-24): a Pages deploy more than a day behind its inputs.

Compares two dates nothing else compares: the live Pages root's ``last-modified``
response header (when the site was last deployed) and the committer date of the
latest first-parent commit on ``refs/remotes/origin/main`` that touched a published
input (when that input landed on main). Story 48.3 reads the clock: an input that
landed after the deploy and has waited more than ``STALE_AFTER`` by ``now`` is one
``pages-liveness-stale`` WARN; an input the site was deployed after is the OK row
whatever the clock reads. Anything this source cannot read is one
``pages-liveness-unavailable`` WARN and never an OK (the 2026-10-06 deploy sat in
``waiting`` for six days and nothing said so).

Read-only (NFR-1): one HEAD to the public root (one GET follows when HEAD answers
outside 2xx; the body is never read) and one ``git log`` through
``cli_bridge.run_git`` (AD-5; ``urllib`` is not a subprocess). No fetch, no ``gh``,
no GitHub API, no token, no write. A stale remote-tracking ref can only make the
site read fresher than it is, never staler, and every row names the commit date.
Every finding is a WARN or the one OK row (AD-2). Not in ``doctor check``'s default
set, ``monitor``'s axes or ``detectors-ci``: its read is live, as
``sibling-dreams-drift``'s and ``ci-pause-drift``'s are.

``urlopen`` and ``now`` are module attributes so tests replace them;
``cli_bridge.run_git`` is reached through the module, so tests replace it there.
"""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .. import cli_bridge
from ..cli_bridge import CliBridgeError
from ..models import UNEVALUABLE_EVIDENCE_KEY, DoctorStatus, Finding, Source
from ..refs import ORIGIN_MAIN, display_ref
from . import degrade_on_exception

__all__ = ("PAGES_ROOT_URL", "PUBLISHED_INPUTS", "STALE_AFTER", "gather")

#: The live Pages root (the second host is Spec open question 1; a constant until then).
PAGES_ROOT_URL = "https://rxm7706.github.io/local-recipes/"

#: ``.github/workflows/pages.yml``'s own ``on.push.paths`` filter, each trailing ``/**`` dropped, less the
#: files that build or deploy the site and publish nothing: the workflow itself, ``scripts/pages_*.py``,
#: steward's ``pages.py`` and ``marketplace_pages.py``, and herald's ``pages_env.py``. ``docsite`` left with
#: herald Story 43.7 (``docs-site`` is the one generator). The filter is steward's; Story 48.3's
#: ``test_the_published_inputs_are_pages_yml_s_filter_less_the_named_exclusions`` pins this list to it.
PUBLISHED_INPUTS: tuple[str, ...] = (
    "docs/tutorials",
    "docs/how-to",
    "docs/reference",
    "docs/explanation",
    "docs/index.md",
    "docs/404.md",
    "docs/map.yaml",
    "docs/dashboard",
    "docs/foundry/marketplace",
    "docs-site",
    "presentations",
)

#: The ``pages`` row's ``stuck_rules.deploy_waiting_hours: 24`` in ``docs/governance/ci-surfaces.yaml``
#: (``pyforge-steward:CAP-166``), kept here as a constant: no Doctor code reads steward's registry.
STALE_AFTER = timedelta(hours=24)

_HTTP_TIMEOUT_SECONDS = 10.0
_USER_AGENT = "pyforge-doctor-pages-liveness"
_CHECK_OK = "pages-liveness"
_CHECK_STALE = "pages-liveness-stale"
_CHECK_UNAVAILABLE = "pages-liveness-unavailable"

#: Replaced by tests; the one network call this source makes goes through it.
urlopen: Callable[..., Any] = urllib.request.urlopen


def _utc_now() -> datetime:
    return datetime.now(UTC)


#: Replaced by tests, as ``urlopen`` is: the clock an input's wait is measured against.
now: Callable[[], datetime] = _utc_now


class _Unavailable(Exception):
    """One side could not be read; the message is the finding's cause."""


def gather(target: Path) -> tuple[Finding, ...]:
    return degrade_on_exception(
        Source.PAGES_LIVENESS,
        _CHECK_UNAVAILABLE,
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    try:
        sha, commit_text, commit_date = _latest_input_commit(target)
        last_modified, requests = _last_modified()
    except _Unavailable as exc:
        return _unavailable(str(exc))

    clock = now()
    lag = commit_date - last_modified
    lag_hours = int(lag.total_seconds()) // 3600
    # Stale only when the input landed after the deploy and has waited more than STALE_AFTER since:
    # an input the site was deployed after is the OK row whatever the clock reads.
    pending = commit_date > last_modified
    waited = max(clock - commit_date, timedelta(0)) if pending else timedelta(0)
    waited_hours, remainder = divmod(int(waited.total_seconds()), 3600)
    stale_after_hours = int(STALE_AFTER.total_seconds() // 3600)
    shown_ref = display_ref(ORIGIN_MAIN)
    last_modified_text = last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_text = clock.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence: dict[str, Any] = {
        "url": PAGES_ROOT_URL,
        "last_modified": last_modified_text,
        "commit": sha,
        "commit_date": commit_text,
        "ref": ORIGIN_MAIN,
        "lag_hours": lag_hours,
        "now": now_text,
        "waited_hours": waited_hours,
        "stale_after_hours": stale_after_hours,
        "requests": requests,
    }
    if pending and waited > STALE_AFTER:
        # Whole hours, never rounded down into reading as the threshold itself: a wait of 24 h 30 min
        # is "more than 24 hours". The wait and both dates lead, so fleet-picture's 110-character
        # ATTENTION line keeps the evidence; the commit, the clock and the URL follow.
        wait_text = f"{waited_hours} hours" if remainder == 0 else f"more than {waited_hours} hours"
        return (
            Finding(
                source=Source.PAGES_LIVENESS,
                check=_CHECK_STALE,
                status=DoctorStatus.WARN,
                message=(
                    f"Pages input waited {wait_text}: last-modified {last_modified_text}, inputs {commit_text} "
                    f"(published-input commit {sha} on {shown_ref}, undeployed at {now_text}), {PAGES_ROOT_URL}"
                ),
                evidence=evidence,
            ),
        )
    standing = (
        f"not yet deployed, waiting within {stale_after_hours} hours (clock {now_text})"
        if pending
        else f"deployed after it (clock {now_text})"
    )
    return (
        Finding(
            source=Source.PAGES_LIVENESS,
            check=_CHECK_OK,
            status=DoctorStatus.OK,
            message=(
                f"Pages deploy current: {PAGES_ROOT_URL} last-modified {last_modified_text}, "
                f"latest published-input commit on {shown_ref} at {commit_text}, {standing}"
            ),
            evidence=evidence,
        ),
    )


def _latest_input_commit(target: Path) -> tuple[str, str, datetime]:
    """``(sha, committer date as git printed it, aware datetime)`` of the latest commit on
    ``refs/remotes/origin/main`` that touched a published input. No fetch.

    ``--first-parent`` reads main's own history: every landing is a merge (``gh pr merge
    --merge``), and without it history simplification can answer with a commit from the merged
    branch, dated before the inputs changed on main -- an early date that reads fresher than the
    site is."""
    argv = ["log", "-1", "--first-parent", "--format=%H %cI", ORIGIN_MAIN, "--", *PUBLISHED_INPUTS]
    try:
        stdout = cli_bridge.run_git(target, argv)
    except CliBridgeError as exc:
        lines = str(exc).strip().splitlines()
        raise _Unavailable(f"git log on {ORIGIN_MAIN} failed: {lines[0] if lines else type(exc).__name__}") from exc
    line = stdout.strip()
    if not line:
        raise _Unavailable(f"no commit on {ORIGIN_MAIN} touches the published inputs")
    sha, _, commit_text = line.partition(" ")
    try:
        commit_date = datetime.fromisoformat(commit_text)
    except ValueError as exc:
        raise _Unavailable(f"git log printed an unreadable line: {line!r}") from exc
    if not sha or commit_date.tzinfo is None:
        raise _Unavailable(f"git log printed an unreadable line: {line!r}")
    return sha, commit_text, commit_date


def _last_modified() -> tuple[datetime, list[str]]:
    """The Pages root's ``last-modified`` as an aware UTC datetime, and the requests made
    (``["HEAD 200"]``, or ``["HEAD 405", "GET 200"]`` when HEAD answered outside 2xx)."""
    requests: list[str] = []
    method = "HEAD"
    status, headers = _request(method)
    requests.append(f"{method} {status}")
    if not _is_2xx(status):
        method = "GET"
        status, headers = _request(method)
        requests.append(f"{method} {status}")
        if not _is_2xx(status):
            raise _Unavailable(f"{', '.join(requests)} from {PAGES_ROOT_URL}")
    value = headers.get("last-modified") if headers is not None else None
    if not value:
        raise _Unavailable(f"{method} {status} from {PAGES_ROOT_URL} carries no last-modified header")
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError) as exc:
        raise _Unavailable(f"last-modified {value!r} from {PAGES_ROOT_URL} is not an HTTP date") from exc
    if parsed.tzinfo is None:
        # RFC 5322's "-0000" reads as naive: the zone is unknown, and HTTP dates are GMT.
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC), requests


def _request(method: str) -> tuple[int, Any]:
    """One request to the Pages root; ``(status, headers)``. The body is never read.
    An HTTP error status is a response (returned); a transport failure is ``_Unavailable``."""
    req = urllib.request.Request(PAGES_ROOT_URL, method=method, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:
            status = getattr(resp, "status", None)
            if status is None:
                status = resp.getcode()
            return int(status), resp.headers
    except urllib.error.HTTPError as exc:
        # The error carries the response; its body is never read, and it is closed here.
        status, headers = int(exc.code), exc.headers
        exc.close()
        return status, headers
    except urllib.error.URLError as exc:
        raise _Unavailable(f"{method} {PAGES_ROOT_URL}: URLError: {exc.reason}") from exc
    except (OSError, http.client.HTTPException) as exc:
        # TimeoutError (socket.timeout) and a dropped connection land here.
        raise _Unavailable(f"{method} {PAGES_ROOT_URL}: {type(exc).__name__}: {exc}") from exc


def _is_2xx(status: int) -> bool:
    return 200 <= status < 300


def _unavailable(cause: str) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.PAGES_LIVENESS,
            check=_CHECK_UNAVAILABLE,
            status=DoctorStatus.WARN,
            message=f"Pages liveness could not be read: {cause}",
            evidence={"cause": cause, "url": PAGES_ROOT_URL, UNEVALUABLE_EVIDENCE_KEY: True},
        ),
    )
