"""CLI ⇄ MCP-tool parity gate (Story 18.2, FR-155 / CAP-3).

Not every Marshal CLI verb is on the tool surface yet. Parity is therefore
an explicit inventory contract:

* every tool that claims a CLI verb must map to a real top-level CLI verb;
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

from pyforge.marshal.mcp.tools import TOOL_SPECS

# Top-level ``marshal`` verbs that deliberately have no MCP tool yet.
# Adding a tool for one of these requires removing it from this set.
CLI_ONLY_VERBS: frozenset[str] = frozenset(
    {
        "adapters",
        "chain",
        # Story 28.8: `marshal context` answers derived-planning-context
        # freshness for ONE epic of ONE station, consumed by
        # bmad-build-auto's own routing step -- not a fleet-status read an
        # MCP client would call. CLI-only until a consumer needs it there.
        "context",
        # Story 28.5: `marshal benchmark` builds the CAP-9 counterfactual
        # artifact from two recorded legs -- operator/recalibration surface,
        # not an MCP fleet read.
        "benchmark",
        "planning",
        "config",
        "deploy",
        "factory",
        "gate",
        "init",
        "land",
        # Story 33.12 CAP-5: local-profile bearer writer; operator-only surface.
        "login",
        "retire",
        "seed",
        "teardown",
    }
)

# Named tools that intentionally have no CLI counterpart (inventory helpers).
TOOL_ONLY_NAMES: frozenset[str] = frozenset({"list_marshal_tools"})


@dataclass(frozen=True, slots=True)
class ParityFinding:
    """One CLI⇄tool inventory mismatch."""

    code: str
    detail: str


def discover_cli_verbs() -> frozenset[str]:
    """Return top-level ``marshal`` subcommand names from the live parser."""
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if getattr(action, "dest", None) == "command" and action.choices:
            return frozenset(action.choices)
    raise RuntimeError("marshal CLI parser has no top-level command choices")


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
    """Compute FR-155 parity mismatches for the given inventories.

    Defaults bind to the live Marshal CLI parser and ``TOOL_SPECS``. Tests
    inject fixtures to prove a deliberate mismatch fails the gate.
    """
    specs = dict(TOOL_SPECS if tool_specs is None else tool_specs)
    verbs = discover_cli_verbs() if cli_verbs is None else frozenset(cli_verbs)
    allow_cli_only = CLI_ONLY_VERBS if cli_only is None else frozenset(cli_only)
    allow_tool_only = TOOL_ONLY_NAMES if tool_only is None else frozenset(tool_only)

    findings: list[ParityFinding] = []

    for name in sorted(allow_tool_only - set(specs)):
        findings.append(
            ParityFinding(
                "tool_only_missing",
                f"tool-only allowlist names {name!r} but TOOL_SPECS has no such tool",
            )
        )

    for name in sorted(allow_cli_only - verbs):
        findings.append(
            ParityFinding(
                "cli_only_unknown",
                f"CLI-only allowlist names {name!r} but no such CLI verb exists",
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
                    f"tool {name!r} claims CLI verb {verb!r} which is not a top-level marshal command",
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
