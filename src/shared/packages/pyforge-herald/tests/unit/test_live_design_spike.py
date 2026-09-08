"""The FR-21 primary-path proof, kept re-runnable (Story 1.2).

This is the prove-or-kill spike the PRD sequenced first: can a plain,
non-interactive Python process -- no Claude Code session, no agent harness
-- reach the ``claude-design`` MCP server using only the credential
``/design-login`` already stored? It answered yes on 2026-07-25, which is
why ``McpTransport`` is V1's shipped transport and Story 1.3's
``AgentSdkTransport`` is the fallback. Keeping the proof as a test rather
than a one-off script means the day that answer changes, it is a failing
run and not a mystery.

It is excluded from the default gate two ways: the ``live`` marker (which
also carves it out of the egress-deny harness in ``conftest.py``) and a
``skipif`` on ``HERALD_LIVE_DESIGN``. Run it deliberately:

    HERALD_LIVE_DESIGN=1 pixi run -e pyforge-herald pytest \\
        src/shared/packages/pyforge-herald/tests/test_live_design_spike.py -q

Strictly read-only: it resolves the credential, opens one session, and
calls ``get_claude_design_prompt``. It creates no project and writes no
file, so a re-run costs one request and changes nothing on the server.
"""

from __future__ import annotations

import os
import re

import pytest

from pyforge.herald.transport import (
    MODERNIST_DESIGN_SYSTEM_ID,
    McpTransport,
    resolve_design_credential,
)
from pyforge.herald.transport.base import REDACTED, TOKENIZED_PREVIEW_HOST

LIVE_ENV = "HERALD_LIVE_DESIGN"

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get(LIVE_ENV),
        reason=f"live claude-design spike -- set {LIVE_ENV}=1 to run it",
    ),
]


def test_stored_design_credential_resolves():
    """The credential seam works against the real stored file."""
    credential = resolve_design_credential()
    assert credential.access_token
    assert credential.is_expired() is False
    assert credential.access_token not in repr(credential)


def test_primary_mcp_path_reaches_claude_design_from_a_plain_process():
    """FR-21: the pure-MCP-client transport answers outside any session."""
    transport = McpTransport()
    prompt = transport.get_design_prompt(design_system_id=MODERNIST_DESIGN_SYSTEM_ID)
    assert isinstance(prompt, str)
    assert prompt.strip(), "the design-system prompt came back empty"
    # The prompt is prose content, so it is not redaction-scrubbed (see
    # McpTransport._call_text). Pin its substance, or an annihilated prompt
    # would sail past a mere "is it a string" check.
    assert prompt != REDACTED
    assert len(prompt) > 1000, (
        "the design-system prompt came back suspiciously short -- "
        "something replaced it wholesale"
    )
    # NFR-04 for a prose payload is "no LIVE tokenized URL", not "never
    # names the host": the real prompt names it exactly once, in the rule
    # forbidding it. Only a token-bearing serve_url is a leak.
    assert not re.search(rf"{re.escape(TOKENIZED_PREVIEW_HOST)}\S*[?&]t=", prompt), (
        "a tokenized serve_url crossed the adapter boundary"
    )
