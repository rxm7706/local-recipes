import os
from typing import Any

from celery import Celery
from celery.signals import setup_logging
from django_structlog.celery.steps import DjangoStructLogInitStep

from config.observability import configure_observability

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
# CAP-3 locality: celery's default leaf is local (same pairing as manage.py /
# asgi.py). Production workers must set DJANGO_SETTINGS_MODULE=production and
# leave COMPONENT_RUNTIME unset (fail-closed deployed).
if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.local":
    os.environ.setdefault("COMPONENT_RUNTIME", "local")

configure_observability()

app = Celery("platform")

# Carries request_id from the request that enqueued a task into the task's own
# log context (CAP-2 / steward 16.3).
app.steps["worker"].add(DjangoStructLogInitStep)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args: Any, **kwargs: Any) -> None:
    from logging.config import dictConfig  # noqa: PLC0415

    from django.conf import settings  # noqa: PLC0415

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
