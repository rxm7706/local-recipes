"""CI surfaces dossier tile — stdlib-only (Story 39.1, CAP-59).

The ``site`` pixi env uses only this module and ``PYFORGE_CI_SURFACES_TILE``. The Guild env
sets that variable via ``export_ci_surfaces_tile_env.py``, which reads the flag through
``pyforge.herald.ci_surfaces_tile``. Herald unit tests import this file by path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ENV_TILE_ENABLED = "PYFORGE_CI_SURFACES_TILE"
SNAPSHOT_NAME = "ci-status.json"

VERDICT_ORDER: tuple[str, ...] = (
    "drift",
    "stuck",
    "overdue",
    "paused",
    "paused-manually",
    "opt-in-off",
    "retired",
)

KNOWN_VERDICTS: frozenset[str] = frozenset((*VERDICT_ORDER, "live"))


class CiStatusShapeError(ValueError):
    """Snapshot envelope or row failed the tile shape check."""


def tile_enabled_from_env() -> bool:
    return os.environ.get(ENV_TILE_ENABLED, "").strip().lower() in ("1", "true", "yes")


def export_tile_env_for_ci() -> dict[str, str]:
    from pyforge.herald.ci_surfaces_tile import ci_surfaces_tile_enabled

    enabled = ci_surfaces_tile_enabled()
    return {ENV_TILE_ENABLED: "1" if enabled else "0"}


def snapshot_path(content_dir: Path) -> Path:
    return content_dir / SNAPSHOT_NAME


def _verdict_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    verdict = row["verdict"]
    if verdict in VERDICT_ORDER:
        return (0, VERDICT_ORDER.index(verdict), row["id"])
    return (1, 0, verdict)


def format_days_left(review_days_left: int | None) -> str:
    if review_days_left is None:
        return "—"
    if review_days_left < 0:
        return f"{abs(review_days_left)} days overdue"
    if review_days_left == 0:
        return "due today"
    return f"{review_days_left} days left"


def format_field(value: Any) -> str:
    if value is None:
        return "—"
    return str(value)


def validate_ci_status_envelope(data: Any, *, path: str) -> None:
    if not isinstance(data, dict):
        raise CiStatusShapeError(f"{path}: envelope is not a JSON object")
    if "fetched_at" not in data:
        raise CiStatusShapeError(f"{path}: missing fetched_at")
    if "rows" not in data:
        raise CiStatusShapeError(f"{path}: missing rows")
    rows = data["rows"]
    if not isinstance(rows, list):
        raise CiStatusShapeError(f"{path}: rows is not a list")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CiStatusShapeError(f"{path}: row {index} is not an object")
        if "id" not in row:
            raise CiStatusShapeError(f"{path}: row {index} missing id")
        if "verdict" not in row:
            row_id = row.get("id")
            if row_id is not None:
                raise CiStatusShapeError(f"{path}: row {index} ({row_id}) missing verdict")
            raise CiStatusShapeError(f"{path}: row {index} missing verdict")


def load_ci_status_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CiStatusShapeError(f"{path}: snapshot missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CiStatusShapeError(f"{path}: not valid JSON ({exc.msg})") from exc
    validate_ci_status_envelope(data, path=str(path))
    return data


def select_non_live_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    non_live = [row for row in rows if row.get("verdict") != "live"]
    return sorted(non_live, key=_verdict_sort_key)


def format_row_line(row: dict[str, Any]) -> str:
    detail = row.get("detail")
    detail_part = f" · {detail}" if detail else ""
    return (
        f"**{format_field(row.get('id'))}** · {format_field(row.get('verdict'))} · "
        f"switch {format_field(row.get('switch'))} · paused since {format_field(row.get('paused_since'))} · "
        f"review by {format_field(row.get('review_by'))} · "
        f"{format_days_left(row.get('review_days_left'))} · owner {format_field(row.get('owner'))}"
        f"{detail_part}"
    )


def build_tile_block_payload(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["rows"]
    non_live = select_non_live_rows(rows)
    if non_live:
        lines = [format_row_line(row) for row in non_live]
        all_live = False
    else:
        lines = ["All CI surfaces reported **live** at capture."]
        all_live = True
    return {
        "type": "ci_surfaces",
        "fetched_at": data["fetched_at"],
        "lines": lines,
        "all_live": all_live,
    }


def render_ci_surfaces_tile(
    *,
    flag_enabled: bool,
    snapshot_path: Path,
) -> dict[str, Any] | None:
    if not flag_enabled:
        return None
    data = load_ci_status_snapshot(snapshot_path)
    return build_tile_block_payload(data)


def apply_ci_surfaces_blocks(doc: dict[str, Any], *, content_dir: Path) -> None:
    if not tile_enabled_from_env():
        for section in doc.get("sections", []):
            blocks = section.get("blocks")
            if not blocks:
                continue
            section["blocks"] = [b for b in blocks if b.get("type") != "ci_surfaces"]
        return

    path = snapshot_path(content_dir)
    try:
        payload = render_ci_surfaces_tile(flag_enabled=True, snapshot_path=path)
    except CiStatusShapeError as exc:
        raise SystemExit(str(exc)) from exc
    assert payload is not None

    for section in doc.get("sections", []):
        blocks = section.get("blocks")
        if not blocks:
            continue
        out: list[dict[str, Any]] = []
        for block in blocks:
            if block.get("type") != "ci_surfaces":
                out.append(block)
                continue
            out.append(payload)
        section["blocks"] = out


def collect_shape_problems(content_dir: Path) -> list[str]:
    if not tile_enabled_from_env():
        return []
    path = snapshot_path(content_dir)
    try:
        load_ci_status_snapshot(path)
    except CiStatusShapeError as exc:
        return [str(exc)]
    return []
