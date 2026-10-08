"""Shared tracked-spec bodies for dispatch unit tests (Story 65.2).

``dispatch_once`` refuses specs with no ``## Verification`` section; an empty
``**Commands:**`` list binds trivially (same shape as ``test_drain_plan``'s
``_BOUND_SPEC_BODY``).
"""

from __future__ import annotations

BINDING_VERIFICATION_TAIL = "\n## Verification\n\n**Commands:**\n\n**Manual checks:**\n- none\n"
