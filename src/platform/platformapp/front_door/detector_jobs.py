"""Scheduled detector cache (never presented as a per-request check)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any

from django.apps import apps
from django.utils import timezone

from platformapp.front_door.models import DetectorVerdict

if TYPE_CHECKING:
    from datetime import datetime

DETECTORS: tuple[str, ...] = (
    "bmad-drift-check",
    "spec-surface-check",
    "llms-full-check",
)

BEAT_TASK_NAME = "console-detector-refresh"
BEAT_TASK_PATH = "platformapp.front_door.refresh_detector_verdicts"

Runner = Callable[[str], dict[str, Any]]


def stub_runner(name: str) -> dict[str, Any]:
    """Deterministic runner for tests and empty-cluster first boot."""
    return {"state": "unknown", "findings": 0, "verdict": f"{name} not run"}


def refresh_verdicts(
    runner: Runner | None = None,
    *,
    now: datetime | None = None,
) -> list[DetectorVerdict]:
    capture = now or timezone.now()
    run = runner or stub_runner
    rows: list[DetectorVerdict] = []
    for name in DETECTORS:
        payload = run(name)
        row, _created = DetectorVerdict.objects.update_or_create(
            detector=name,
            defaults={
                "state": str(payload.get("state", "unknown")),
                "findings": int(payload.get("findings", 0)),
                "verdict": str(payload.get("verdict", "")),
                "captured_at": capture,
            },
        )
        rows.append(row)
    return rows


def cache_age_label(captured_at: datetime | None, *, now: datetime) -> str:
    if captured_at is None:
        return "never"
    seconds = max(0, int((now - captured_at).total_seconds()))
    return f"{seconds}s"


def seed_detector_schedule(**_kwargs: object) -> None:
    if not apps.is_installed("django_celery_beat"):
        return
    from django_celery_beat.models import IntervalSchedule  # noqa: PLC0415
    from django_celery_beat.models import PeriodicTask  # noqa: PLC0415

    schedule, _created = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.HOURS,
    )
    PeriodicTask.objects.update_or_create(
        name=BEAT_TASK_NAME,
        defaults={
            "interval": schedule,
            "task": BEAT_TASK_PATH,
            "enabled": True,
        },
    )
