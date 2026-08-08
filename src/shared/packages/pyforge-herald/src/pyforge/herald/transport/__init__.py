"""Herald's transport layer: the ``DesignTransport`` port plus its adapters.

One import surface for everything that speaks to ``claude-design``, so
bridge-core (Story 1.4) never reaches into a specific adapter module. Story
1.3's ``AgentSdkTransport`` (the FR-22 fallback) joins here without moving
any call site.
"""

from .agent_sdk_transport import (
    AgentLaunchResult,
    AgentProcessLauncher,
    AgentSdkTransport,
    SubprocessAgentLauncher,
)
from .base import (
    MODERNIST_DESIGN_SYSTEM_ID,
    DesignTransport,
    FileRead,
    ListedFile,
    PlanHandle,
    PreviewRef,
    ProjectRef,
    ToolCaller,
    ToolResult,
    as_optional_text,
    as_text,
    parse_read_response,
    require_conditional,
    sanitize_payload,
)
from .mcp_transport import (
    DESIGN_MCP_URL,
    DesignCredential,
    McpTransport,
    resolve_design_credential,
)

__all__ = [
    "DESIGN_MCP_URL",
    "MODERNIST_DESIGN_SYSTEM_ID",
    "AgentLaunchResult",
    "AgentProcessLauncher",
    "AgentSdkTransport",
    "DesignCredential",
    "DesignTransport",
    "FileRead",
    "ListedFile",
    "McpTransport",
    "PlanHandle",
    "PreviewRef",
    "ProjectRef",
    "SubprocessAgentLauncher",
    "ToolCaller",
    "ToolResult",
    "as_optional_text",
    "as_text",
    "parse_read_response",
    "require_conditional",
    "resolve_design_credential",
    "sanitize_payload",
]
