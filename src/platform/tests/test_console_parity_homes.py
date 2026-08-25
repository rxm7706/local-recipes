"""Steward 30.1 — remaining console surfaces have a named Canopy home."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import pytest
from django.apps import apps
from django.conf import settings
from django.http import Http404
from django.test import Client
from django.test import RequestFactory
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from wagtail.models import Locale
from wagtail.models import Page
from wagtail.models import Site

from platformapp.front_door.apps import _seed_detector_schedule
from platformapp.front_door.console_parity import HOMES
from platformapp.front_door.console_parity import SURFACES
from platformapp.front_door.console_parity import MissingParityHomeError
from platformapp.front_door.console_parity import directory_rows
from platformapp.front_door.console_parity import inventory_ids
from platformapp.front_door.console_parity import parity_ids
from platformapp.front_door.console_parity import require_parity_homes
from platformapp.front_door.detector_jobs import BEAT_TASK_NAME
from platformapp.front_door.detector_jobs import DETECTORS
from platformapp.front_door.detector_jobs import cache_age_label
from platformapp.front_door.detector_jobs import refresh_verdicts
from platformapp.front_door.detector_jobs import seed_detector_schedule
from platformapp.front_door.detector_jobs import stub_runner
from platformapp.front_door.models import ConsoleEditorialPage
from platformapp.front_door.models import DetectorVerdict
from platformapp.front_door.models import HomePage
from platformapp.front_door.runtime_catalog import catalog_entries
from platformapp.front_door.tasks import refresh_detector_verdicts
from platformapp.front_door.views import console_catalog

pytestmark = pytest.mark.django_db

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]

EXPECTED_PARITY = frozenset(
    {
        "dreams",
        "specs",
        "story_specs",
        "campaigns",
        "command_center",
        "launch_readiness",
        "fleet_progress_tracked",
        "pitch",
        "guild",
        "backlog",
        "open_work",
        "archived",
        "fleet_table",
        "program_story_status",
        "fleet_chain_audit_badge",
        "health_ci_overlay",
        "in_build_realized_membership",
    },
)


def test_inventory_has_twenty_three_surfaces() -> None:
    runtime = {row.surface_id for row in SURFACES if row.classification == "runtime"}
    mixed = {row.surface_id for row in SURFACES if row.classification == "mixed"}
    build = {row.surface_id for row in SURFACES if row.classification == "build"}
    assert len(runtime) + len(mixed) + len(build) == len(SURFACES)
    assert len(inventory_ids()) == len(SURFACES)
    assert runtime.isdisjoint(mixed)
    assert mixed.isdisjoint(build)


def test_parity_rows_require_named_homes() -> None:
    assert parity_ids() == EXPECTED_PARITY
    homes = require_parity_homes()
    assert set(homes) == EXPECTED_PARITY
    for surface_id, home in homes.items():
        assert home.path
        assert home.kind in {"lane1", "portal"}
        assert surface_id in HOMES


def test_missing_home_mapping_fails_the_gate() -> None:
    reduced = {key: value for key, value in HOMES.items() if key != "dreams"}
    with (
        patch("platformapp.front_door.console_parity.HOMES", reduced),
        pytest.raises(MissingParityHomeError, match="dreams"),
    ):
        require_parity_homes()


def test_directory_lists_named_homes(client: Client) -> None:
    response = client.get("/console/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert 'data-console="directory"' in body
    for surface_id in EXPECTED_PARITY:
        assert f'data-surface="{surface_id}"' in body
        assert HOMES[surface_id].path in body


def test_health_empty_cache_shows_never(client: Client) -> None:
    response = client.get("/console/health/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert 'data-health="empty"' in body
    assert 'data-age="never"' in body
    assert "never" in body


def test_health_cached_result_shows_age(client: Client) -> None:
    captured = timezone.now() - timedelta(seconds=12)

    def runner(name: str) -> dict[str, object]:
        return {"state": "green", "findings": 0, "verdict": f"{name} OK"}

    refresh_verdicts(runner, now=captured)
    response = client.get("/console/health/")
    body = response.content.decode()
    assert 'data-health="cached"' in body
    assert "bmad-drift-check" in body
    assert "12s" in body or "13s" in body


def test_scheduled_job_seeds_beat_and_refresh_task() -> None:
    seed_detector_schedule()
    task = PeriodicTask.objects.get(name=BEAT_TASK_NAME)
    assert task.task == "platformapp.front_door.refresh_detector_verdicts"
    assert task.enabled is True
    count = refresh_detector_verdicts()
    assert count == len(DETECTORS)
    assert DetectorVerdict.objects.count() == len(DETECTORS)
    assert str(DetectorVerdict.objects.get(detector="llms-full-check")) == (
        "llms-full-check"
    )


def test_seed_skipped_when_beat_not_installed() -> None:
    target = "platformapp.front_door.detector_jobs.apps.is_installed"
    with patch(target, return_value=False):
        seed_detector_schedule()


def test_editorial_home_reads_cms(client: Client) -> None:
    empty = client.get("/console/editorial/")
    assert "no published editorial pages" in empty.content.decode()
    Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)
    root = Page.get_first_root_node()
    if root is None:
        root = Page.add_root(title="Root", slug="root")
    home = HomePage(title="Estate", slug="estate-console", body="home")
    root.add_child(instance=home)
    home.save_revision().publish()
    site = Site.objects.get(is_default_site=True)
    site.root_page = home
    site.save()
    page = ConsoleEditorialPage(
        title="Program copy",
        slug="program-copy",
        surface_id="editorial_blocks",
        body="<p>cms-editorial-body</p>",
    )
    home.add_child(instance=page)
    page.save_revision().publish()
    response = client.get("/console/editorial/")
    assert "cms-editorial-body" in response.content.decode()
    rendered = client.get(page.url)
    assert rendered.status_code == HTTPStatus.OK
    assert "cms-editorial-body" in rendered.content.decode()


def test_catalog_pages_scan_tracked_files(client: Client) -> None:
    dreams = client.get("/console/dreams/")
    assert dreams.status_code == HTTPStatus.OK
    body = dreams.content.decode()
    assert 'data-console-home="dreams"' in body
    assert "pyforge-steward" in body or "pyforge" in body
    assert client.get("/console/specs/").status_code == HTTPStatus.OK
    assert client.get("/console/story-specs/").status_code == HTTPStatus.OK
    assert client.get("/console/guild/").status_code == HTTPStatus.OK
    assert client.get("/console/backlog/").status_code == HTTPStatus.OK
    assert client.get("/console/open-work/").status_code == HTTPStatus.OK
    assert client.get("/console/archived/").status_code == HTTPStatus.OK
    programs = client.get("/console/programs/")
    assert programs.status_code == HTTPStatus.OK
    assert "pyforge-steward" in programs.content.decode()


def test_catalog_unknown_surface_is_404() -> None:
    request = RequestFactory().get("/console/x/")
    with pytest.raises(Http404):
        console_catalog(request, "not-a-surface")


def test_catalog_entries_empty_root(tmp_path: Path) -> None:
    assert catalog_entries("dreams", tmp_path) == []
    assert catalog_entries("unknown", tmp_path) == []
    assert catalog_entries("story_specs", tmp_path) == []
    assert catalog_entries("open_work", tmp_path) == []
    assert catalog_entries("program_story_status", tmp_path) == []
    factory = RequestFactory()
    response = console_catalog(factory.get("/console/dreams/"), "program_story_status")
    assert response.status_code == HTTPStatus.OK


def test_directory_rows_skip_incomplete_ids() -> None:
    with patch.dict("platformapp.front_door.console_parity.HOMES", {}, clear=True):
        assert directory_rows() == []


def test_cache_age_and_stub_runner() -> None:
    now = timezone.now()
    assert cache_age_label(None, now=now) == "never"
    assert stub_runner("x")["state"] == "unknown"
    assert cache_age_label(now, now=now) == "0s"


def test_seed_hook_and_config_ready() -> None:
    _seed_detector_schedule(apps.get_app_config("front_door"))
    apps.get_app_config("front_door").ready()


def test_generator_and_kedro_viz_untouched() -> None:
    dashboard = REPO_ROOT / "docs" / "dashboard"
    assert (dashboard / "generate.py").is_file()
    assert (dashboard / "data.js").is_file()
    assert (dashboard / "kedro-viz").is_dir()
    pixi = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    for task in (
        "dashboard-gen",
        "dashboard-watch",
        "dashboard-check",
        "dashboard-drift-check",
    ):
        assert task in pixi


def _portal_home(station: str) -> str:
    return (
        REPO_ROOT
        / "src"
        / "shared"
        / "packages"
        / f"django-{station}"
        / "src"
        / f"django_{station}_portal"
        / "templates"
        / f"{station}_portal"
        / "home.html"
    ).read_text(encoding="utf-8")


def test_portal_homes_are_marked() -> None:
    assert 'data-console-home="fleet_table"' in _portal_home("doctor")
    assert 'data-console-home="pitch"' in _portal_home("herald")
    assert 'data-console-home="command_center"' in _portal_home("steward")
    assert 'data-console-home="campaigns"' in _portal_home("marshal")


def test_runs_board_still_mounted(client: Client) -> None:
    response = client.get("/runs/")
    assert response.status_code == HTTPStatus.OK
    assert 'data-board="current"' in response.content.decode()
