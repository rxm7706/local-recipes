"""CAP-2 / steward 16.3 — request + Celery hop correlation.

Uses the real test client and celery eager mode. Reads events via caplog
`record.msg` dicts (never structlog.testing.capture_logs — that drops
merge_contextvars / add_otel_context).
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from typing import Any

import pytest
from django.http import HttpResponse
from django.urls import path
from django.urls import reverse

from platformapp.users.tasks import get_users_count
from platformapp.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import Client

pytestmark = pytest.mark.django_db

REQUEST_LOGGER = "django_structlog"
TASK_LOGGER = "platformapp.users.tasks"
TRACE_ID_HEX_LEN = 32


def _events(caplog: pytest.LogCaptureFixture, name: str) -> list[dict[str, Any]]:
    return [
        record.msg
        for record in caplog.records
        if isinstance(record.msg, dict) and record.msg.get("event") == name
    ]


def _fanout_view(request):
    get_users_count.delay()
    return HttpResponse("ok")


urlpatterns = [
    path("fanout-probe/", _fanout_view, name="fanout_probe"),
]


@pytest.fixture
def fanout_urls(settings):
    settings.ROOT_URLCONF = __name__
    return settings


class TestRequestLoggingIds:
    def test_request_id_and_trace_id_on_ht(
        self,
        client: Client,
        caplog: pytest.LogCaptureFixture,
    ):
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            response = client.get("/ht/")

        assert response.status_code == HTTPStatus.OK
        started = _events(caplog, "request_started")
        assert started, "expected django_structlog request_started"
        event = started[0]
        assert event.get("request_id"), event
        assert event.get("trace_id"), f"missing trace_id: {sorted(event)}"
        assert len(event["trace_id"]) == TRACE_ID_HEX_LEN

    def test_authenticated_request_carries_user_id(
        self,
        client: Client,
        caplog: pytest.LogCaptureFixture,
    ):
        user = UserFactory()
        client.force_login(user)
        with caplog.at_level(logging.INFO, logger=REQUEST_LOGGER):
            response = client.get("/ht/")
        assert response.status_code == HTTPStatus.OK
        started = _events(caplog, "request_started")
        assert started
        assert started[0].get("user_id") == user.pk


class TestWebCeleryHopCorrelation:
    def test_fanout_shares_request_id_and_trace_id(
        self,
        client: Client,
        settings,
        fanout_urls,
        caplog: pytest.LogCaptureFixture,
    ):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.CELERY_TASK_EAGER_PROPAGATES = True
        user = UserFactory()
        client.force_login(user)

        with (
            caplog.at_level(logging.INFO, logger=REQUEST_LOGGER),
            caplog.at_level(logging.INFO, logger=TASK_LOGGER),
        ):
            response = client.get(reverse("fanout_probe"))

        assert response.status_code == HTTPStatus.OK
        web = _events(caplog, "request_started")
        worker = _events(caplog, "celery_users_count")
        assert web, "missing web request_started"
        assert worker, "missing celery_users_count on worker"

        web_event = web[0]
        worker_event = worker[0]
        assert web_event.get("request_id")
        assert worker_event.get("request_id") == web_event["request_id"]
        assert web_event.get("user_id") == user.pk
        # django-structlog Celery hooks restore request-bound contextvars,
        # including user_id, onto the task log context.
        assert worker_event.get("user_id") == user.pk

        web_trace = web_event.get("trace_id")
        worker_trace = worker_event.get("trace_id")
        assert web_trace, f"web missing trace_id: {sorted(web_event)}"
        assert worker_trace, f"worker missing trace_id: {sorted(worker_event)}"
        assert web_trace == worker_trace
        assert len(web_trace) == TRACE_ID_HEX_LEN
