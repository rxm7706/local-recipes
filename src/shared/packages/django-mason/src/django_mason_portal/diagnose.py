"""Last diagnose (or equivalent) projection. In-process only."""

from __future__ import annotations

from typing import Any

from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import audience_for

STATION = "mason"
LAST_DIAGNOSE_SUMMARY = "mason diagnose equivalent: last station diagnosis"


def last_diagnose(*, assertion: str) -> dict[str, Any]:
    claims = verify_assertion(assertion, audience=audience_for(STATION))
    subject = claims.get(CLAIM_SUB, "")
    return {
        "ok": True,
        "tool": "last_diagnose",
        "command": "mason diagnose",
        "summary": LAST_DIAGNOSE_SUMMARY,
        "subject": subject,
        "source": "portal-client",
    }
