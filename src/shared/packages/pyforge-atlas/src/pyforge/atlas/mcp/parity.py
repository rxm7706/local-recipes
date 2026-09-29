"""CLI ⇄ MCP-tool parity gate (Story 25.3, FR-155 / marshal Story 18.2).

Atlas's MCP surface is registered on ``server.build_server`` and declared in
``tools.TOOL_SPECS``. Parity is an explicit inventory contract:

* every tool that claims a CLI verb must map to a real Kedro project verb;
* every CLI verb declared as *on* the tool surface (i.e. not CLI-only) must
  have at least one tool;
* tools with ``cli: None`` must be declared tool-only inventory helpers;
* the CLI-only allowlist must not go stale (unknown verbs, or verbs that
  already have tools);
* a tool-only allowlist entry must not also claim a CLI verb.

Drift fails the gated meta-test; review is not the gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pyforge.atlas.mcp.tools import TOOL_SPECS

# Kedro project verbs reachable via ``pyforge-atlas`` / ``pyforge atlas …``
# that deliberately have no MCP tool yet. Each entry carries a reason
# sentence — an allowlist is a declaration with a reason, never a way to
# reach green.
CLI_ONLY_VERBS: dict[str, str] = {
    "ipython": ("Kedro interactive shell — operator surface, not an atlas MCP read/trigger."),
    "package": ("Kedro project packaging — not exposed on the atlas MCP tool surface."),
}

# Named MCP tools that intentionally have no ``pyforge-atlas`` CLI counterpart.
TOOL_ONLY_NAMES: frozenset[str] = frozenset(
    {
        "read_atlas_dataset",
        "list_atlas_pipelines",
        "list_atlas_datasets",
        "query_vizro_ai",
        "query_trending_candidates",
    }
)


@dataclass(frozen=True, slots=True)
class ParityFinding:
    """One CLI⇄tool inventory mismatch."""

    code: str
    detail: str


def discover_cli_verbs() -> frozenset[str]:
    """Return Kedro project command names for ``pyforge.atlas`` at runtime."""
    from pyforge.atlas.__main__ import discover_cli_verbs as _discover

    return _discover()


def tool_cli_verb(spec: Mapping[str, Any]) -> str | None:
    """First argv token of a tool's ``cli`` template, or ``None`` if tool-only."""
    cli = spec.get("cli")
    if cli is None:
        return None
    if not isinstance(cli, Sequence) or isinstance(cli, (str, bytes)):
        raise TypeError(f"tool cli must be a sequence of tokens, got {cli!r}")
    if not cli:
        raise ValueError("tool cli sequence must be non-empty when not None")
    first = cli[0]
    if not isinstance(first, str):
        raise TypeError(f"tool cli[0] must be str, got {first!r}")
    return first


def tools_by_cli_verb(
    tool_specs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, list[str]]:
    """Map CLI verb → tool names that claim it (excludes tool-only / malformed)."""
    specs = TOOL_SPECS if tool_specs is None else tool_specs
    by_verb: dict[str, list[str]] = {}
    for name, spec in specs.items():
        if not isinstance(spec, Mapping):
            continue
        try:
            verb = tool_cli_verb(spec)
        except TypeError, ValueError:
            continue
        if verb is None:
            continue
        by_verb.setdefault(verb, []).append(name)
    return by_verb


def parity_findings(
    *,
    tool_specs: Mapping[str, Mapping[str, Any]] | None = None,
    cli_verbs: frozenset[str] | None = None,
    cli_only: frozenset[str] | None = None,
    tool_only: frozenset[str] | None = None,
) -> list[ParityFinding]:
    """Compute FR-155 parity mismatches for the given inventories."""
    specs = dict(TOOL_SPECS if tool_specs is None else tool_specs)
    verbs = discover_cli_verbs() if cli_verbs is None else frozenset(cli_verbs)
    allow_cli_only = frozenset(CLI_ONLY_VERBS) if cli_only is None else frozenset(cli_only)
    allow_tool_only = TOOL_ONLY_NAMES if tool_only is None else frozenset(tool_only)

    findings: list[ParityFinding] = []

    for name in sorted(allow_tool_only - set(specs)):
        findings.append(
            ParityFinding(
                "tool_only_missing",
                f"tool-only allowlist names {name!r} but TOOL_SPECS has no such tool",
            )
        )

    for verb in sorted(allow_cli_only - verbs):
        findings.append(
            ParityFinding(
                "cli_only_unknown",
                f"CLI-only allowlist names {verb!r} but no such CLI verb exists",
            )
        )

    by_verb = tools_by_cli_verb(specs)

    for name, spec in sorted(specs.items()):
        if not isinstance(spec, Mapping):
            findings.append(
                ParityFinding(
                    "tool_spec_invalid",
                    f"{name}: tool spec must be a mapping, got {type(spec).__name__}",
                )
            )
            continue
        try:
            verb = tool_cli_verb(spec)
        except (TypeError, ValueError) as exc:
            findings.append(ParityFinding("tool_cli_malformed", f"{name}: {exc}"))
            continue
        if verb is None:
            if name not in allow_tool_only:
                findings.append(
                    ParityFinding(
                        "tool_without_cli",
                        f"tool {name!r} has cli=None but is not in TOOL_ONLY_NAMES",
                    )
                )
            continue
        if name in allow_tool_only:
            findings.append(
                ParityFinding(
                    "tool_only_has_cli",
                    f"tool-only allowlist names {name!r} but that tool claims CLI verb {verb!r}",
                )
            )
        if verb not in verbs:
            findings.append(
                ParityFinding(
                    "tool_cli_unknown",
                    f"tool {name!r} claims CLI verb {verb!r} which is not a Kedro project command",
                )
            )
        if verb in allow_cli_only:
            findings.append(
                ParityFinding(
                    "cli_only_has_tool",
                    f"CLI verb {verb!r} is CLI-only allowlisted but tool {name!r} claims it",
                )
            )

    on_surface = verbs - allow_cli_only
    for verb in sorted(on_surface):
        if verb not in by_verb:
            findings.append(
                ParityFinding(
                    "cli_missing_tool",
                    f"CLI verb {verb!r} is on the tool surface (not CLI-only) but no tool claims it",
                )
            )

    return findings


def assert_cli_tool_parity(
    *,
    tool_specs: Mapping[str, Mapping[str, Any]] | None = None,
    cli_verbs: frozenset[str] | None = None,
    cli_only: frozenset[str] | None = None,
    tool_only: frozenset[str] | None = None,
) -> None:
    """Raise ``AssertionError`` when FR-155 parity findings are non-empty."""
    findings = parity_findings(
        tool_specs=tool_specs,
        cli_verbs=cli_verbs,
        cli_only=cli_only,
        tool_only=tool_only,
    )
    if not findings:
        return
    lines = [f"{f.code}: {f.detail}" for f in findings]
    raise AssertionError("CLI ⇄ tool parity gate failed (FR-155):\n  - " + "\n  - ".join(lines))
