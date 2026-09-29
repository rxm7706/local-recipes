"""Thin MCP tool bodies over the ``marshal`` CLI (Story 18.1, FR-153).

Every callable here is a thin wrapper over ``cli.main.main`` with
``--format json`` where the verb supports it. No craft logic lives here —
parity with the CLI surface is the point (FR-155 gating is Story 18.2).
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

# Registry consumed by ``list_marshal_tools`` and by ``server.build_server``.
# ``argv_template`` is the CLI argv AFTER the program name; optional typed
# kwargs are appended as flags when provided.
TOOL_SPECS: dict[str, dict[str, Any]] = {
    "list_marshal_tools": {
        "description": "List Marshal MCP tool names and their CLI argv templates.",
        "cli": None,
    },
    "marshal_status": {
        "description": "Fleet-wide runtime status (marshal status --format json).",
        "cli": ["status", "--format", "json"],
        "optional_flags": {"project": "--project"},
    },
    "marshal_check": {
        "description": "Run detector registry via marshal check --format json.",
        "cli": ["check", "--format", "json"],
        "optional_flags": {"scope": "--scope", "project": "--project"},
    },
    "marshal_homes": {
        "description": "List loop homes (marshal homes --format json).",
        "cli": ["homes", "--format", "json"],
    },
    "marshal_preflight": {
        "description": "Preflight a loop home (marshal preflight SLUG --format json).",
        "cli": ["preflight", "{slug}", "--format", "json"],
        "required": ("slug",),
    },
    "marshal_upstream": {
        "description": "Upstream contribution register (marshal upstream --format json).",
        "cli": ["upstream", "--format", "json"],
    },
    "marshal_refresh": {
        "description": "Refresh loop homes from main (marshal refresh --format json).",
        "cli": ["refresh", "--format", "json"],
        "optional_flags": {"project": "--project", "base": "--base"},
    },
    "marshal_watch": {
        "description": ("Watch a pinned run, a station's current run, or the fleet (marshal watch --format json)."),
        "cli": ["watch", "--format", "json"],
        "optional_flags": {"project": "--project", "run": "--run"},
        "store_true_flags": {"fleet": "--fleet"},
    },
}

_ABS_PATH_RE = re.compile(r"^(/|[A-Za-z]:\\|\\\\)")


def list_marshal_tools() -> dict[str, Any]:
    """Structured inventory of named tools (no CLI invocation)."""
    tools = []
    for name, spec in TOOL_SPECS.items():
        tools.append(
            {
                "name": name,
                "description": spec["description"],
                "cli": spec.get("cli"),
                "required": list(spec.get("required") or ()),
                "optional_flags": dict(spec.get("optional_flags") or {}),
            }
        )
    return {"ok": True, "tools": tools, "count": len(tools)}


def run_marshal(
    argv: Sequence[str],
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    """Invoke the marshal CLI in-process; return a structured answer.

    Captures stdout, prefers JSON parse, and wraps non-zero exits in an
    ``ok: false`` envelope rather than raising across the MCP boundary.
    """
    if main is None:
        from pyforge.marshal.cli.main import main as _main

        main = _main

    buf = io.StringIO()
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            exit_code = main(list(argv))
    except Exception as exc:  # noqa: BLE001 — MCP boundary must stay structured
        return {
            "ok": False,
            "exit_code": None,
            "error": f"{type(exc).__name__}: {exc}",
            "stdout": buf.getvalue(),
            "stderr": err.getvalue(),
        }

    stdout = buf.getvalue()
    stderr = err.getvalue()
    payload: Any
    try:
        payload = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        payload = {"raw_stdout": stdout}

    if exit_code == 0:
        if isinstance(payload, dict):
            return {"ok": True, "exit_code": exit_code, **payload}
        return {"ok": True, "exit_code": exit_code, "data": payload}

    return {
        "ok": False,
        "exit_code": exit_code,
        "stderr": stderr,
        "data": payload,
    }


def _build_argv(spec_name: str, **kwargs: Any) -> list[str]:
    spec = TOOL_SPECS[spec_name]
    cli: list[str] = list(spec["cli"] or [])
    required = tuple(spec.get("required") or ())
    for key in required:
        if not kwargs.get(key):
            raise ValueError(f"{spec_name} requires argument {key!r}")
    argv: list[str] = []
    for token in cli:
        if token.startswith("{") and token.endswith("}"):
            argv.append(str(kwargs[token[1:-1]]))
        else:
            argv.append(token)
    for kw, flag in (spec.get("optional_flags") or {}).items():
        value = kwargs.get(kw)
        if value is not None and value != "":
            argv.extend([flag, str(value)])
    for kw, flag in (spec.get("store_true_flags") or {}).items():
        if kwargs.get(kw):
            argv.append(flag)
    return argv


def marshal_status(
    project: str | None = None,
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(_build_argv("marshal_status", project=project), main=main)


def marshal_check(
    scope: str = "all",
    project: str | None = None,
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(
        _build_argv("marshal_check", scope=scope, project=project),
        main=main,
    )


def marshal_homes(
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(_build_argv("marshal_homes"), main=main)


def marshal_preflight(
    slug: str,
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(_build_argv("marshal_preflight", slug=slug), main=main)


def marshal_upstream(
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(_build_argv("marshal_upstream"), main=main)


def marshal_refresh(
    project: str | None = None,
    base: str | None = None,
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(
        _build_argv("marshal_refresh", project=project, base=base),
        main=main,
    )


def marshal_watch(
    project: str | None = None,
    run: str | None = None,
    fleet: bool = False,
    *,
    main: Callable[[list[str] | None], int] | None = None,
) -> dict[str, Any]:
    return run_marshal(
        _build_argv("marshal_watch", project=project, run=run, fleet=fleet),
        main=main,
    )


def mcp_server_registration_spec() -> Mapping[str, Mapping[str, object]]:
    """Policy-shaped ``mcp_servers`` entry for Marshal itself (FR-154).

    PATH basename only — never an absolute path. Consumed by tests and as
    the documented shape for ``marshal-policy.toml``.
    """
    return {
        "marshal": {
            "command": "marshal-mcp",
            "args": [],
            "env": {},
        }
    }


def assert_no_absolute_command(command: str) -> None:
    """Raise ``ValueError`` if ``command`` looks machine-absolute."""
    if _ABS_PATH_RE.match(command) or "/" in command or "\\" in command:
        raise ValueError(f"mcp command must be PATH-relative, got {command!r}")
