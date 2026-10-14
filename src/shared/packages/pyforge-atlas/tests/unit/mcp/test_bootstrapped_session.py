"""Story 31.1 — unit coverage for ``bootstrapped_session`` (Kedro session seam)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyforge.atlas.mcp import session as session_mod


def test_bootstrapped_session_yields_created_session_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = MagicMock(name="kedro_session_ctx")
    create_kwargs: dict[str, object] = {}

    def fake_create(**kwargs: object) -> MagicMock:
        create_kwargs.update(kwargs)
        return ctx

    monkeypatch.setattr(session_mod, "bootstrap_project", lambda _root: None)
    monkeypatch.setattr(session_mod.KedroSession, "create", fake_create)

    with session_mod.bootstrapped_session(
        project_path=Path("/tmp/project"),
        extra_params={"k": "v"},
        env="local",
    ) as session:
        assert session is ctx

    assert create_kwargs["project_path"] == Path("/tmp/project")
    assert create_kwargs["runtime_params"] == {"k": "v"}
    assert create_kwargs["env"] == "local"
