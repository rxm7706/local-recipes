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
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

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
#: The page size the export download asks the artifacts listing for (the REST API's maximum).
ARTIFACTS_PER_PAGE = 100
#: An identical tree still deploys once the live build is older than this and its commit moved
#: (doctor 48.2's review): at most one extra deploy a day keeps the live ``last-modified`` honest.
LIVENESS_MAX_AGE = timedelta(hours=24)
#: The story fields the board's attention block reads; the rest of steward's row stays out of the input.
_FLEET_STORY_FIELDS = ("story_id", "station", "epic_id", "title", "status")
#: The per-station counts herald's board reads (herald 42.1 ``COUNT_KEYS`` plus ``done``); nothing else of
#: ``StationProgress`` reaches the input -- ``next_running`` carries the live ``marshal watch`` fact.
_FLEET_STATION_COUNTS = ("done", "in_progress", "backlog", "blocked")

# Relative paths excluded from tree_hash (never hashed silently — each entry documents why).
HASH_EXCLUDE_RELATIVE: frozenset[str] = frozenset(
    {
        "build.json",  # written after hash; must not feed back into itself
    }
)
#: Herald Story 43.5's built-from line (design-thinking P-A): every HTML page carries one element of plain text
#: naming the commit, the build time and the run id -- build provenance, not content, and on every page rather than
#: at a path, so tree_hash reads each ``.html`` file with that element's text dropped (the element itself still
#: counts). A rebuild of an unmoved tree then hashes the same and skips its deploy, and the liveness rule below
#: (:data:`LIVENESS_MAX_AGE`) keeps the live build honest; a commit that moves the content still changes the hash.
#: Only the exact element herald emits and its ``pages-check`` enforces is read (its review): an attribute value that
#: mentions the name, a longer attribute name or another attribute order drops nothing, so it over-deploys, never
#: hides a change.
BUILT_FROM_TEXT = re.compile(rb'(<p class="built-from" data-pages-built-from data-pagefind-ignore>)[^<]*(</p>)')


def tree_hash(root: Path, *, exclude: Iterable[str] | None = None) -> str:
    """SHA-256 over sorted relative paths and file bytes under ``root``, each HTML file's built-from text dropped."""
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
        data = (root / rel).read_bytes()
        if rel.endswith(".html"):
            data = BUILT_FROM_TEXT.sub(rb"\1\2", data)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
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


def export_artifacts_endpoint(artifact: str, *, page: int) -> str:
    """The Actions REST call that lists one page of the repository's artifacts named ``artifact``
    (``gh api`` fills ``{owner}`` and ``{repo}``): the listing :func:`newest_export_run` reads."""
    return (
        f"repos/{{owner}}/{{repo}}/actions/artifacts?name={quote(artifact, safe='')}"
        f"&per_page={ARTIFACTS_PER_PAGE}&page={page}"
    )


def newest_export_run(
    artifacts_json: Iterable[Mapping[str, Any]],
    runs_json: Mapping[Any, Mapping[str, Any]] | Callable[[int], Mapping[str, Any] | None],
    *,
    artifact: str = KEDRO_VIZ_ARTIFACT,
    workflow: str = KEDRO_VIZ_WORKFLOW,
    branch: str | None = EXPORT_BRANCH,
) -> int | None:
    """The producer run that holds the newest live ``artifact`` on ``branch`` (Story 102.4).

    Selection is by artifact, never by a window of recent runs (102.4's re-review): atlas 30.2's
    producer runs each export job only when that export's own paths change, so a run window of any
    size can hold none of one export while a live one sits further back; it would then read
    ``absent`` and the next deploy would drop that mount from production.

    ``artifacts_json`` is every ``artifacts`` entry of every page of
    :func:`export_artifacts_endpoint`. An entry counts when its ``name`` is ``artifact``, ``expired`` is
    ``false``, its ``workflow_run.head_branch`` is ``branch`` (``None`` takes any) and its run is not a
    fork's (``workflow_run.head_repository_id`` equals ``workflow_run.repository_id`` where both are
    given). Counted entries are read newest ``created_at`` first. ``runs_json`` maps a run id to its
    ``gh api repos/{owner}/{repo}/actions/runs/<id>`` payload (a run missing from it is passed over),
    or is a ``fetch(run_id)`` callable read in that order, stopping at the first match. A run matches
    when it is ``workflow``'s (``path`` is ``.github/workflows/<workflow>``), concluded ``success`` and
    ran on ``branch``. ``None``: no live artifact of that name from such a run. A live artifact of that name
    with no readable ``workflow_run.id`` raises ``ValueError``: a wrong-shape answer is never absence."""
    candidates: list[tuple[str, int]] = []
    for item in artifacts_json:
        if not isinstance(item, Mapping) or item.get("name") != artifact or item.get("expired") is not False:
            continue
        run = item.get("workflow_run")
        if not isinstance(run, Mapping) or not isinstance(run.get("id"), int):
            # A live artifact of this name whose run cannot be read is a wrong-shape answer, never a skip:
            # skipping every one would read as absence and drop the mount (102.4's lane-B re-review).
            raise ValueError(f"live artifact {artifact!r} (id {item.get('id')!r}) has no readable workflow_run.id")
        if branch is not None and run.get("head_branch") != branch:
            continue
        head_repo, repo = run.get("head_repository_id"), run.get("repository_id")
        if head_repo is not None and repo is not None and head_repo != repo:
            continue
        candidates.append((str(item.get("created_at") or ""), run["id"]))
    seen: set[int] = set()
    for _created, run_id in sorted(candidates, reverse=True):
        if run_id in seen:
            continue
        seen.add(run_id)
        payload = runs_json(run_id) if callable(runs_json) else runs_json.get(run_id, runs_json.get(str(run_id)))
        if not isinstance(payload, Mapping):
            continue
        path = str(payload.get("path") or "").split("@", 1)[0]
        if (
            path == f".github/workflows/{workflow}"
            and payload.get("conclusion") == "success"
            and (branch is None or payload.get("head_branch") == branch)
        ):
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
