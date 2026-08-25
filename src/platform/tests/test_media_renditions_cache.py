"""Steward 20.2: RWX media, renditions cache, broker≠cache, Celery tasks."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_tasks.backends.base import BaseTaskBackend
from PIL import Image as PILImage
from wagtail.images.models import Image
from wagtail.images.models import Rendition

from platformapp.front_door.celery_task_backend import CeleryTaskBackend
from platformapp.front_door.lane1_runtime import channel_layers_for_broker
from platformapp.front_door.lane1_runtime import django_cache_aliases
from platformapp.front_door.tasks import echo_payload
from platformapp.front_door.tasks import run_django_task
from platformapp.front_door.tasks import tagged_echo

pytestmark = pytest.mark.django_db


def _png(name: str = "red.png") -> SimpleUploadedFile:
    buf = BytesIO()
    PILImage.new("RGB", (32, 32), color=(220, 20, 60)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def test_replica_b_retrieves_upload_from_shared_media_root(
    settings,
    tmp_path: Path,
) -> None:
    shared = tmp_path / "rwx"
    shared.mkdir()
    settings.MEDIA_ROOT = str(shared)

    image = Image(title="shared", file=_png())
    image.save()

    replica_b = Path(settings.MEDIA_ROOT) / image.file.name
    assert replica_b.is_file()
    assert replica_b.read_bytes() == Path(image.file.path).read_bytes()


def test_rendition_from_replica_a_is_served_from_cache_without_regeneration() -> None:
    image = Image(title="cache-me", file=_png("cache.png"))
    image.save()
    rendition = image.get_rendition("width-16")
    cache_key = rendition.get_cache_key()
    assert Rendition.cache_backend.get(cache_key) is not None

    replica_b = Image.objects.get(pk=image.pk)
    with patch.object(
        Image,
        "generate_rendition_file",
        side_effect=AssertionError("regen"),
    ):
        served = replica_b.get_rendition("width-16")

    assert served.filter_spec == "width-16"
    assert Rendition.cache_backend.get(cache_key) is not None


def test_celery_and_channels_use_broker_django_and_renditions_use_cache() -> None:
    assert settings.CELERY_BROKER_URL == settings.REDIS_BROKER_URL
    assert settings.CELERY_RESULT_BACKEND == settings.REDIS_BROKER_URL
    layers = channel_layers_for_broker("redis://broker.example:6379/0")
    assert layers["default"]["BACKEND"] == "channels_redis.core.RedisChannelLayer"
    assert layers["default"]["CONFIG"]["hosts"] == ["redis://broker.example:6379/0"]
    aliases = django_cache_aliases("redis://cache.example:6379/0")
    assert aliases["default"]["LOCATION"] == aliases["renditions"]["LOCATION"]
    assert aliases["renditions"]["KEY_PREFIX"] == "renditions"
    assert "renditions" in settings.CACHES


def test_search_is_postgres_fts_and_tasks_are_in_tree_celery() -> None:
    assert (
        settings.WAGTAILSEARCH_BACKENDS["default"]["BACKEND"]
        == "wagtail.search.backends.database"
    )
    backend = settings.TASKS["default"]["BACKEND"]
    assert backend == "platformapp.front_door.celery_task_backend.CeleryTaskBackend"
    assert issubclass(CeleryTaskBackend, BaseTaskBackend)
    langflow_redis = os.environ.get("LANGFLOW_REDIS_URL", "")
    assert langflow_redis == settings.REDIS_CACHE_URL


def test_celery_backend_enqueues_and_eager_runner_covers_both_call_shapes() -> None:
    assert echo_payload("n") == "echoed:n"
    assert run_django_task("platformapp.front_door.tasks.echo_payload", ["z"], {}) == (
        "echoed:z"
    )
    assert run_django_task("platformapp.front_door.tasks.tagged_echo", ["z"], {}) == (
        "tagged:z"
    )
    result = tagged_echo.enqueue("hi")
    assert result.backend == "default"
    assert result.args == ["hi"]


def test_image_and_document_serving_urls_are_mounted() -> None:
    assert reverse("wagtailimages_serve", args=["max-10x10", "1", "x"])
    assert reverse("wagtaildocs_serve", args=["1", "file.pdf"])


def test_front_door_lane1_modules_do_not_import_pyforge() -> None:
    root = Path(__file__).resolve().parents[1] / "platformapp" / "front_door"
    forbidden = ("import pyforge", "from pyforge")
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains {needle!r}"


def test_cache_helper_never_points_renditions_at_the_broker() -> None:
    aliases = django_cache_aliases("redis://cache:6379/0")
    layers = channel_layers_for_broker("redis://broker:6379/0")
    assert aliases["renditions"]["LOCATION"] != layers["default"]["CONFIG"]["hosts"][0]
