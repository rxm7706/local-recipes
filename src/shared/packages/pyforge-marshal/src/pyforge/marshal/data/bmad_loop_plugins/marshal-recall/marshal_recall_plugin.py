"""In-process marshal-recall plugin (Story 93.1).

Calls ``augment_bmad_loop_session_prompt_with_recall`` at ``pre_session`` so
live bmad-loop dev and review sessions receive the same block factory
dispatch writes through ``harness_bmadbuild``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bmad_loop.plugins.model import Plugin

if TYPE_CHECKING:
    from bmad_loop.plugins.context import HookContext


def _load_context_layers(project_root: Path) -> dict[str, dict[str, object]] | None:
    policy_path = project_root / ".bmad-loop" / "policy.toml"
    try:
        doc = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    raw = doc.get("context")
    if not isinstance(raw, dict):
        return None
    layers: dict[str, dict[str, object]] = {}
    for name, table in raw.items():
        if isinstance(table, dict):
            layers[str(name)] = {str(k): v for k, v in table.items()}
    return layers


class MarshalRecallPlugin(Plugin):
    def on_pre_session(self, ctx: HookContext) -> None:
        from pyforge.marshal.adapters.fs_local import LocalFs
        from pyforge.marshal.adapters.harness_bmadloop import (
            augment_bmad_loop_session_prompt_with_recall,
            resolve_loop_home_station_slug,
        )

        role = ctx.role or "dev"
        if role not in ("dev", "review"):
            return
        loop_home = Path(ctx.worktree or ctx.repo_root or ".")
        repo_root = Path(ctx.repo_root or loop_home)
        station_slug = resolve_loop_home_station_slug(loop_home)
        story_key = ctx.story_key or ""
        run_id = ctx.run_id or ""
        if not story_key or not run_id:
            return
        context_layers = _load_context_layers(loop_home)
        prompt = ctx.proposed_prompt or ""
        updated, _injection = augment_bmad_loop_session_prompt_with_recall(
            prompt,
            role=role,
            fs=LocalFs(),
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug=station_slug,
            story_key=story_key,
            run_id=run_id,
            context_layers=context_layers,
        )
        ctx.proposed_prompt = updated
