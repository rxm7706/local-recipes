"""Pages deploy duty: tree hash, build.json, and deploy-when-changed (Story 102.2 / CAP-168).

Story 102.4 adds :func:`newest_export_run`, the selection behind the Pages build's artifact download
(``scripts/pages_artifact_download.py``). Story 102.3 adds the fleet board's build input: :func:`fleet_status_document` reshapes
``sprint-ledger-query --format json`` into the ``docsite/content/fleet-status.json`` herald's board
reads (herald Story 42.1, ``docsite/tools/status_pages.py``). Pure functions only: the workflow runs
them through ``scripts/pages_fleet_status.py``, ``steward pages build`` in-process.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PAGES_DUTY_FLAG = "pyforge.steward.pages_duty"
#: The unified Pages artifact ``pages-check`` builds, relative to the repository root.
SITE_ROOT_REL = "docs-site/build/site"
#: The fleet board's build input herald reads (gitignored), relative to the repository root.
FLEET_STATUS_REL = "docsite/content/fleet-status.json"
#: Atlas's Kedro-Viz producer and the artifact it uploads (atlas Story 30.1); the mount source the
#: Pages build reads (herald Story 42.2). Story 102.4 downloads one into the other.
KEDRO_VIZ_WORKFLOW = "kedro-viz-publish.yml"
KEDRO_VIZ_ARTIFACT = "kedro-viz-export"
KEDRO_VIZ_DEST_REL = "docs/dashboard/kedro-viz"
#: Names the three env lines the download writes (``<PREFIX>``, ``<PREFIX>_RUN``, ``<PREFIX>_AT``).
KEDRO_VIZ_ENV_PREFIX = "KEDRO_VIZ_EXPORT"
#: Only a run on this branch is mounted: a producer dispatched on an unmerged branch never reaches the
#: production Pages origin (102.4's review).
EXPORT_BRANCH = "main"
#: An identical tree still deploys once the live build is older than this and its commit moved
#: (doctor 48.2's review): at most one extra deploy a day keeps the live ``last-modified`` honest.
LIVENESS_MAX_AGE = timedelta(hours=24)
#: The story fields the board's attention block reads; the rest of steward's row stays out of the input.
_FLEET_STORY_FIELDS = ("story_id", "station", "epic_id", "title", "status")
#: The per-station counts herald's board reads (herald 42.1 ``COUNT_KEYS`` plus ``done``); nothing else of
#: ``StationProgress`` reaches the input -- ``next_running`` carries the live ``marshal watch`` fact.
_FLEET_STATION_COUNTS = ("done", "in_progress", "backlog", "blocked")

# Relative paths excluded from tree_hash (never hashed silently — each entry documents why).
# Herald M3 footer paths join this list when that footer ships (design-thinking P-A).
HASH_EXCLUDE_RELATIVE: frozenset[str] = frozenset(
    {
        "build.json",  # written after hash; must not feed back into itself
    }
)


def tree_hash(root: Path, *, exclude: Iterable[str] | None = None) -> str:
    """SHA-256 over sorted relative paths and file bytes under ``root``."""
    if not root.is_dir():
        msg = f"tree_hash root is not a directory: {root}"
        raise ValueError(msg)
    excluded = HASH_EXCLUDE_RELATIVE if exclude is None else frozenset(exclude)
    digest = hashlib.sha256()
    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded or any(rel == e or rel.startswith(f"{e}/") for e in excluded):
            continue
        paths.append(rel)
    for rel in paths:
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_json(
    tree_hash_value: str,
    built_from: str,
    run_id: str,
    built_at: str,
) -> dict[str, Any]:
    """The live ``build.json`` document shape."""
    return {
        "tree_hash": tree_hash_value,
        "built_from": built_from,
        "run_id": run_id,
        "built_at": built_at,
    }


def _parse_live_document(live_text: str | None) -> dict[str, Any] | None:
    if live_text is None or not live_text.strip():
        return None
    try:
        payload = json.loads(live_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_live_tree_hash(live_text: str | None) -> str | None:
    """Return ``tree_hash`` from live JSON text, or ``None`` when absent/unusable."""
    payload = _parse_live_document(live_text)
    value = payload.get("tree_hash") if payload is not None else None
    if not isinstance(value, str) or not value:
        return None
    return value


def _parse_built_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _same_commit(a: str, b: str) -> bool:
    """Full and abbreviated SHAs of one commit compare equal."""
    a, b = a.strip().lower(), b.strip().lower()
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def decide_deploy(
    local_hash: str,
    live_text: str | None,
    *,
    flag_on: bool,
    built_from: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Whether to deploy this build (``True`` = deploy).

    Flag off, or no usable live ``tree_hash``: deploy. A different tree: deploy. An identical tree:
    skip, unless the live ``build.json`` was built more than :data:`LIVENESS_MAX_AGE` before ``now``
    and this build's commit (``built_from``) differs from the live ``built_from`` -- then deploy, at
    most once a day, so an input commit that builds an identical site still moves the live
    ``last-modified`` a liveness probe reads (doctor 48.2's review; Story 102.3). Without
    ``built_from`` and ``now`` the liveness branch does not apply."""
    if not flag_on:
        return True
    live = _parse_live_document(live_text)
    live_hash = parse_live_tree_hash(live_text)
    if live is None or live_hash is None:
        return True
    if local_hash != live_hash:
        return True
    if not built_from or now is None:
        return False
    live_from = live.get("built_from")
    live_at = _parse_built_at(live.get("built_at"))
    if not isinstance(live_from, str) or not live_from.strip() or live_at is None:
        return False
    return now - live_at > LIVENESS_MAX_AGE and not _same_commit(built_from, live_from)


def fleet_status_document(ledger_payload: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    """``sprint-ledger-query --format json`` reshaped as herald's fleet-status input.

    ``stations`` is the payload's ``summary.stations`` as a list in station order, each row
    ``station``, ``epics`` (how many of the payload's ``epics`` rows name that station), ``total`` (its
    ``total_stories``) and the ``done`` / ``in_progress`` / ``backlog`` / ``blocked`` counts it gives --
    nothing else of ``StationProgress``, so no live ``marshal watch`` fact reaches the input (the CI
    run and a local ``steward pages build`` write the same file for one commit); ``stories`` keeps each story row's
    ``story_id``, ``station``, ``epic_id``, ``title`` and ``status``. ``generated_at`` is the snapshot
    time the board names: the payload's own unless the caller passes a steadier one (the workflow
    passes the built commit's time, so a scheduled build of an unmoved tree hashes the same and
    skips its deploy). Counts are steward's; nothing is re-derived here."""
    summary = ledger_payload.get("summary")
    stations = summary.get("stations") if isinstance(summary, dict) else None
    if not isinstance(stations, dict):
        msg = "sprint-ledger-query payload has no summary.stations object"
        raise ValueError(msg)
    epics_per_station: dict[str, int] = {}
    for epic in ledger_payload.get("epics") or []:
        if isinstance(epic, dict) and isinstance(epic.get("station"), str):
            epics_per_station[epic["station"]] = epics_per_station.get(epic["station"], 0) + 1
    rows: list[dict[str, Any]] = []
    for name in sorted(stations):
        progress = stations[name]
        if not isinstance(progress, dict):
            msg = f"sprint-ledger-query payload: summary.stations[{name!r}] is not an object"
            raise ValueError(msg)
        row: dict[str, Any] = {
            "station": progress.get("station", name),
            "epics": epics_per_station.get(name, 0),
            "total": progress.get("total_stories", 0),
        }
        row.update({key: progress[key] for key in _FLEET_STATION_COUNTS if key in progress})
        rows.append(row)
    stories = [
        {field: story.get(field) for field in _FLEET_STORY_FIELDS}
        for story in ledger_payload.get("stories") or []
        if isinstance(story, dict)
    ]
    return {
        "generated_at": generated_at or ledger_payload.get("generated_at"),
        "source": "sprint-ledger-query --format json",
        "stations": rows,
        "stories": stories,
    }


def newest_export_run(
    runs_json: Iterable[Mapping[str, Any]],
    artifacts_json: Mapping[Any, Mapping[str, Any]] | Callable[[int], Mapping[str, Any] | None],
    *,
    artifact: str = KEDRO_VIZ_ARTIFACT,
    branch: str | None = EXPORT_BRANCH,
) -> int | None:
    """The newest successful producer run on ``branch`` whose ``artifact`` is listed and not expired
    (Story 102.4).

    ``runs_json`` is ``gh run list --json databaseId,createdAt,conclusion,headBranch``. ``artifacts_json``
    is either a mapping from a run id to that run's ``gh api repos/{owner}/{repo}/actions/runs/<id>/artifacts``
    payload (a run missing from it is passed over) or a ``fetch(run_id)`` callable this function calls
    newest-first, stopping at the first match (the download script's lazy read). A run whose
    ``conclusion`` is not ``success``, or whose ``headBranch`` is not ``branch`` (``None`` takes any), is
    ignored. ``None``: no such run, no artifact of that name, or only expired ones."""
    eligible = [
        run
        for run in runs_json
        if isinstance(run, Mapping)
        and run.get("conclusion") == "success"
        and isinstance(run.get("databaseId"), int)
        and (branch is None or run.get("headBranch") == branch)
    ]
    for run in sorted(eligible, key=lambda r: str(r.get("createdAt") or ""), reverse=True):
        run_id = run["databaseId"]
        if callable(artifacts_json):
            payload = artifacts_json(run_id)
        else:
            payload = artifacts_json.get(run_id, artifacts_json.get(str(run_id)))
        if not isinstance(payload, Mapping):
            continue
        for item in payload.get("artifacts") or []:
            if isinstance(item, Mapping) and item.get("name") == artifact and item.get("expired") is False:
                return run_id
    return None


#: Story 102.5: the rolling pre-release that carries the deployed site after each deploy, and its
#: one asset (the build job's ``pages-site`` artifact, zipped, ``build.json`` inside). The tag is not
#: a version (CalVer tags are) and sits outside every protected tag pattern.
RELEASE_TAG = "pages-site"
RELEASE_ASSET = "pages-site.zip"
#: The ``if:`` of the deploy job's two release-asset steps in ``pages.yml``, held here so a test reads
#: the workflow against it and :func:`release_asset_runs` evaluates the same condition.
RELEASE_ASSET_IF = "${{ needs.build.outputs.pages_duty == '1' && github.event_name != 'pull_request' }}"


def release_asset_runs(*, pages_duty: str, event_name: str) -> bool:
    """:data:`RELEASE_ASSET_IF` for one deploy: ``pages_duty`` is the build job's exported duty flag
    (``PYFORGE_PAGES_DUTY``, ``"1"`` when ``pyforge.steward.pages_duty`` reads on), ``event_name`` the
    triggering event. A pull request never publishes, whatever the flag."""
    return pages_duty == "1" and event_name != "pull_request"
