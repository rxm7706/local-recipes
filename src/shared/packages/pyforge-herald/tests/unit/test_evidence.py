"""``evidence.py``'s link validation (Story 6.4, AD-15).

No test in this file ever constructs a real ``httpx2.Client`` -- every call
injects ``FakeHttpClient`` (a hand-written double implementing this
module's own ``_HttpClient`` duck-type: one ``head(url)`` method), matching
this package's no-``unittest.mock``, no-real-network convention
(``conftest.py``'s ``FakeCaller``/``deny_network`` is the same discipline
one layer down at the MCP ``ToolCaller`` seam). A test that forgot to
inject one would hit the autouse ``deny_network`` fixture's socket denial
instead of a real HTTP call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx2
import pytest

from pyforge.herald import evidence
from pyforge.herald.errors import EvidenceLinkError


class FakeResponse:
    def __init__(self, status_code: int, redirects: int = 0):
        self.status_code = status_code
        self.history = [object()] * redirects


class FakeHttpClient:
    """Maps a url to a canned ``FakeResponse`` or an exception instance to
    raise. An unmapped url is a test bug, not a silent 200 -- fails loudly."""

    def __init__(self, responses):
        self.responses = dict(responses)
        self.requested_urls: list[str] = []

    def head(self, url: str):
        self.requested_urls.append(url)
        canned = self.responses[url]
        if isinstance(canned, BaseException):
            raise canned
        return canned


def test_validate_link_200_is_valid():
    client = FakeHttpClient({"https://ok.example": FakeResponse(200)})
    result = evidence.validate_link("https://ok.example", client=client)
    assert result.is_valid is True
    assert result.status == 200
    assert result.redirects == 0
    assert result.url == "https://ok.example"
    assert result.is_stale is False


def test_validate_link_299_is_still_in_range():
    client = FakeHttpClient({"https://edge.example": FakeResponse(299)})
    assert evidence.validate_link("https://edge.example", client=client).is_valid


def test_validate_link_404_is_invalid():
    client = FakeHttpClient({"https://dead.example": FakeResponse(404)})
    result = evidence.validate_link("https://dead.example", client=client)
    assert result.is_valid is False
    assert result.status == 404


def test_validate_link_403_is_invalid():
    client = FakeHttpClient({"https://forbidden.example": FakeResponse(403)})
    assert not evidence.validate_link(
        "https://forbidden.example", client=client
    ).is_valid


def test_validate_link_unreachable_is_invalid_with_no_status():
    client = FakeHttpClient(
        {"https://unreachable.example": httpx2.ConnectError("refused")}
    )
    result = evidence.validate_link("https://unreachable.example", client=client)
    assert result.is_valid is False
    assert result.status is None


@pytest.mark.parametrize("redirect_count", [0, 1, 2, 3])
def test_validate_link_up_to_three_redirects_still_valid_on_a_final_200(
    redirect_count,
):
    """AD-15: 'follows up to 3 hops' -- not an off-by-one. Exactly 3 hops
    must still resolve, not be treated as one too many."""
    client = FakeHttpClient(
        {"https://redirected.example": FakeResponse(200, redirects=redirect_count)}
    )
    result = evidence.validate_link("https://redirected.example", client=client)
    assert result.is_valid is True
    assert result.redirects == redirect_count


def test_validate_link_too_many_redirects_raised_by_the_client_is_invalid():
    """A 4th hop is what the real ``httpx2.Client(max_redirects=3)`` itself
    refuses (raises ``TooManyRedirects``) -- this module must not crash on
    that, only report the link as invalid."""
    client = FakeHttpClient(
        {"https://loopy.example": httpx2.TooManyRedirects("too many redirects")}
    )
    result = evidence.validate_link("https://loopy.example", client=client)
    assert result.is_valid is False


@pytest.mark.parametrize("redirect_count", [0, 1, 2])
def test_no_warning_for_a_chain_of_two_or_fewer(redirect_count, caplog):
    client = FakeHttpClient(
        {"https://short.example": FakeResponse(200, redirects=redirect_count)}
    )
    with caplog.at_level("WARNING", logger="pyforge.herald.evidence"):
        evidence.validate_link("https://short.example", client=client)
    assert caplog.records == []


def test_warns_for_a_chain_longer_than_two(caplog):
    client = FakeHttpClient({"https://long.example": FakeResponse(200, redirects=3)})
    with caplog.at_level("WARNING", logger="pyforge.herald.evidence"):
        result = evidence.validate_link("https://long.example", client=client)
    assert result.is_valid is True
    assert any("fragile" in record.message for record in caplog.records)


def test_validate_for_publish_returns_the_validation_when_valid():
    client = FakeHttpClient({"https://ok.example": FakeResponse(200)})
    result = evidence.validate_for_publish("https://ok.example", client=client)
    assert result.is_valid is True


def test_validate_for_publish_raises_evidence_link_error_naming_the_url_when_broken():
    client = FakeHttpClient({"https://dead.example": FakeResponse(404)})
    with pytest.raises(EvidenceLinkError) as excinfo:
        evidence.validate_for_publish("https://dead.example", client=client)
    message = str(excinfo.value)
    assert "https://dead.example" in message
    assert "before publishing" in message


def test_schedule_async_validation_marks_an_overdue_entry_stale():
    now = datetime(2026, 8, 7, tzinfo=UTC)
    old = evidence.LinkValidation(
        url="https://ok.example",
        is_valid=True,
        status=200,
        redirects=0,
        last_validated_at=now - timedelta(days=10),
    )
    client = FakeHttpClient({"https://ok.example": FakeResponse(200)})
    [result] = evidence.schedule_async_validation([old], client=client, now=lambda: now)
    assert result.is_stale is True
    assert result.is_valid is True
    assert result.last_validated_at == now


def test_schedule_async_validation_does_not_mark_a_recent_entry_stale():
    now = datetime(2026, 8, 7, tzinfo=UTC)
    recent = evidence.LinkValidation(
        url="https://ok.example",
        is_valid=True,
        status=200,
        redirects=0,
        last_validated_at=now - timedelta(days=1),
    )
    client = FakeHttpClient({"https://ok.example": FakeResponse(200)})
    [result] = evidence.schedule_async_validation(
        [recent], client=client, now=lambda: now
    )
    assert result.is_stale is False


def test_schedule_async_validation_re_checks_every_url():
    now = datetime(2026, 8, 7, tzinfo=UTC)
    entries = [
        evidence.LinkValidation(
            url=url,
            is_valid=True,
            status=200,
            redirects=0,
            last_validated_at=now - timedelta(days=1),
        )
        for url in ("https://a.example", "https://b.example")
    ]
    client = FakeHttpClient(
        {"https://a.example": FakeResponse(200), "https://b.example": FakeResponse(404)}
    )
    results = evidence.schedule_async_validation(
        entries, client=client, now=lambda: now
    )
    assert [r.is_valid for r in results] == [True, False]
    assert sorted(client.requested_urls) == ["https://a.example", "https://b.example"]


def test_schedule_async_validation_respects_a_custom_stale_after():
    now = datetime(2026, 8, 7, tzinfo=UTC)
    entry = evidence.LinkValidation(
        url="https://ok.example",
        is_valid=True,
        status=200,
        redirects=0,
        last_validated_at=now - timedelta(hours=2),
    )
    client = FakeHttpClient({"https://ok.example": FakeResponse(200)})
    [result] = evidence.schedule_async_validation(
        [entry], client=client, now=lambda: now, stale_after=timedelta(hours=1)
    )
    assert result.is_stale is True
