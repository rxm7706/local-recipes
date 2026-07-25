"""Herald's transport layer: the ``DesignTransport`` port plus its adapters.

One import surface for everything that speaks to ``claude-design``, so
bridge-core (Story 1.4) never reaches into a specific adapter module and
Story 1.3's ``AgentSdkTransport`` can join without moving a call site.
"""

from .base import (
    DesignTransport,
    FileRead,
    PlanHandle,
    PreviewRef,
    ProjectRef,
    ToolCaller,
    ToolResult,
    parse_read_response,
    sanitize_payload,
)
from .mcp_transport import (
    DESIGN_MCP_URL,
    MODERNIST_DESIGN_SYSTEM_ID,
    DesignCredential,
    McpTransport,
    resolve_design_credential,
)

__all__ = [
    "DESIGN_MCP_URL",
    "MODERNIST_DESIGN_SYSTEM_ID",
    "DesignCredential",
    "DesignTransport",
    "FileRead",
    "McpTransport",
    "PlanHandle",
    "PreviewRef",
    "ProjectRef",
    "ToolCaller",
    "ToolResult",
    "parse_read_response",
    "resolve_design_credential",
    "sanitize_payload",
]
