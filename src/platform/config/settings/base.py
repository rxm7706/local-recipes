# ruff: noqa: ERA001, E501
"""Base settings to build other settings files upon."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import environ
from django.urls import reverse_lazy

from config.authorization.claims import load_claims_contract
from config.broker_tls import DEFAULT_REDIS_URL
from config.broker_tls import broker_use_ssl
from config.broker_tls import is_tls_broker
from config.observability.logging import build_logging_config
from config.observability.logging import configure_structlog

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# Story 18.1: when django-pyforge is not installed into site-packages, load it
# from the monorepo source tree (pytest, local manage.py). The container copies
# the module onto BASE_DIR instead, so this directory is absent there.
_CHROME_SRC = BASE_DIR.parent / "shared" / "packages" / "django-pyforge" / "src"
if _CHROME_SRC.is_dir() and importlib.util.find_spec("django_pyforge") is None:
    sys.path.insert(0, str(_CHROME_SRC))
_STATION_PORTAL_PACKAGES = (
    ("django-warden", "django_warden_fabric"),
    ("django-atlas", "django_atlas_portal"),
    ("django-doctor", "django_doctor_portal"),
    ("django-herald", "django_herald_portal"),
    ("django-marshal", "django_marshal_portal"),
    ("django-mason", "django_mason_portal"),
    ("django-scribe", "django_scribe_portal"),
    ("django-steward", "django_steward_portal"),
)
for _dist, _module in _STATION_PORTAL_PACKAGES:
    _portal_src = BASE_DIR.parent / "shared" / "packages" / _dist / "src"
    if _portal_src.is_dir() and importlib.util.find_spec(_module) is None:
        sys.path.insert(0, str(_portal_src))
# Story 49.14: django_mason_portal.boot_reconcile imports pyforge.mason.boot at
# MasonPortalConfig.ready() time (eager, not lazy -- boot reconciliation must
# run on every Django startup). pyforge-mason is deliberately NOT a pixi
# dependency of this environment: its own conda package declares a hard
# `twine>=7.0.0,<7.1` run-dependency (Story 3.1, the engine it drives), and
# twine 7.0.0 requires `rich>=14.3.3`, which conflicts outright with
# langflow-base 1.11.4's `rich<14.0.0` pin already in this same environment --
# a genuine, unresolvable-here upstream conflict, not a missing pin. The
# container COPYs pyforge/mason's raw source onto BASE_DIR instead (see
# src/platform/Containerfile) -- same "monorepo pythonpath" shape as the
# portal packages above, applied to the underlying pyforge.<station> library
# rather than its django_<station>_portal wrapper.
_MASON_SRC = BASE_DIR.parent / "shared" / "packages" / "pyforge-mason" / "src"
if _MASON_SRC.is_dir() and importlib.util.find_spec("pyforge.mason") is None:
    sys.path.insert(0, str(_MASON_SRC))
# Story 42.4: the Celery queue topology is the chrome's table, not a settings
# literal (after the sys.path insert above, hence mid-module). Plain module --
# no models, no settings access at import.
from django_pyforge.queues import ALL_QUEUES  # noqa: E402
from django_pyforge.queues import DEFAULT_QUEUE  # noqa: E402
from django_pyforge.queues import SWEEP_LOST_RUNS_TASK  # noqa: E402
from django_pyforge.queues import route_task  # noqa: E402

# platformapp/
APPS_DIR = BASE_DIR / "platformapp"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
# from django.utils.translation import gettext_lazy as _
# LANGUAGES = [
#     ('en', _('English')),
#     ('fr-fr', _('French')),
#     ('pt-br', _('Portuguese')),
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres:///platform",
    ),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # allauth MFA templates {% load humanize %} (image compress)
    "django.contrib.admin",
    "django.contrib.postgres",  # steward 20.1 / canopy AD-13: Wagtail PostgreSQL FTS
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    # CAP-1 / steward 16.5: OIDC provider ships with django-allauth (no second framework).
    "allauth.socialaccount.providers.openid_connect",
    "django_celery_beat",
    # steward 20.1 / canopy AD-13: Lane 1 CMS (standard Wagtail 7.4 set)
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_tasks",
    # Story 10.1: K8s liveness/readiness target at /ht/ -- PostgreSQL + Redis
    # (via the configured cache backend) only. health_check.storage is
    # deliberately omitted: it checks the default file storage backend, a
    # dependency outside this platform's declared "exactly PostgreSQL +
    # Redis" infrastructure boundary.
    #
    # Story 10.3: `django-health-check` is sourced from the
    # `python-agent-platform` conda env at >=4.5.0 (pixi.toml), a from-
    # scratch rewrite of the 3.x line this app was originally written
    # against -- 4.x has no `health_check.db`/`health_check.cache` sub-apps
    # (checks are plain classes wired directly at the URL, see
    # `config/urls.py`'s `/ht/` route) and no `apps.py`, so "health_check"
    # is kept in INSTALLED_APPS only so its `templates/health_check/` dir is
    # discoverable via APP_DIRS.
    "health_check",
    # CAP-2 / steward 16.3: request_id/user_id binding + Celery propagation.
    "django_structlog",
]

LOCAL_APPS = [
    # Story 18.1 / CAP-1: shared chrome. Not a station; portals register
    # themselves via AppConfig (canopy AD-1).
    "django_pyforge",
    "platformapp.users",
    # steward 20.1 / canopy AD-13: Lane 1 HomePage at /
    "platformapp.front_door.apps.FrontDoorConfig",
    # Story 11.1: migration-only app provisioning `langflow_schema` (AD-5).
    # No models -- see langflow_integration/apps.py.
    "langflow_integration",
    # Story 11.2: migration-only app provisioning `dbgpt_schema` (AD-5/AD-17).
    # No models -- see dbgpt_integration/apps.py. Registered so `manage.py
    # migrate` creates the schema; DB-GPT is Pattern B (its own sidecar
    # container, never an ASGI mount) -- see that app's own docstring.
    "dbgpt_integration",
    # Steward 19.1 / 19.2: station portal reusable apps (warden fabric + shells).
    *[module for _, module in _STATION_PORTAL_PACKAGES],
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "platformapp.contrib.sites.migrations"}

# AUTHENTICATION (CAP-1 / steward 16.5 — OIDC-delegated, no local passwords)
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
OIDC_PROVIDER_ID = env.str("COMPONENT_OIDC_PROVIDER_ID", default="oidc")
# Unauthenticated requests redirect to the IdP, not a local password form.
LOGIN_URL = reverse_lazy(
    "openid_connect_login", kwargs={"provider_id": OIDC_PROVIDER_ID}
)
CLAIMS_CONTRACT = load_claims_contract(env)
# Story 26.1 / FR-31: re-read IdP roles from token claims on each request.
DJANGO_PYFORGE_GROUP_CLAIM = CLAIMS_CONTRACT.group_claim or "groups"
DJANGO_PYFORGE_IDP_CLAIMS_GETTER = (
    "config.authorization.current_claims.fetch_current_idp_claims"
)
IDP_CLAIMS_SNAPSHOT = None
IDP_USERINFO = None
# steward 20.1 / canopy AD-13: Wagtail admin is IdP-only (not a URLconf override).
WAGTAILADMIN_LOGIN_URL = LOGIN_URL
WAGTAILUSERS_PASSWORD_ENABLED = False
WAGTAIL_EMAIL_MANAGEMENT_ENABLED = False
WAGTAIL_PASSWORD_MANAGEMENT_ENABLED = False
WAGTAIL_SITE_NAME = env.str("WAGTAIL_SITE_NAME", default="PyForge")
WAGTAILADMIN_BASE_URL = env.str(
    "WAGTAILADMIN_BASE_URL", default="http://localhost:8000"
)
WAGTAIL_ADMIN_IDP_GROUP = env.str(
    "COMPONENT_WAGTAIL_ADMIN_GROUP", default="wagtail-admin"
)
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    },
}

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "config.observability.middleware.HealthCheckMetricsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Story 26.1 / canopy AD-15: IdP roles from this request's token claims.
    # After SessionMiddleware so a claims document in the session can be read.
    "django_pyforge.middleware.TokenRolesMiddleware",
    # Story 18.3 / canopy AD-7: identity headers are not an identity path.
    "django_pyforge.assertion.middleware.AssertionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # After AuthenticationMiddleware so request.user is resolved and can be
    # bound onto the log context as user_id (CAP-2 / steward 16.3).
    "django_structlog.middlewares.RequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # steward 20.1: signed-in users without the Wagtail-admin IdP group get 403,
    # not Wagtail's default bounce to login.
    "platformapp.front_door.middleware.WagtailAdminGroupRequiredMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = env("MEDIA_ROOT", default=str(APPS_DIR / "media"))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "platformapp.users.context_processors.allauth_settings",
                "django_pyforge.context_processors.chrome",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""PyForge Steward""", "steward@platform.internal")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# https://cookiecutter-django.readthedocs.io/en/latest/settings.html#other-environment-settings
# Force the `admin` sign in process to go through the `django-allauth` workflow
DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)

# LOGGING (CAP-2 / steward 16.3 — structlog + OTel context on every line)
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
DJANGO_LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", default="INFO")
DJANGO_LOG_FORMAT = env.str("DJANGO_LOG_FORMAT", default="")

LOGGING = build_logging_config(
    debug=DEBUG,
    log_level=DJANGO_LOG_LEVEL,
    log_format=DJANGO_LOG_FORMAT or None,
)

configure_structlog()

# django-structlog binds request_id and user_id for the life of a request and
# carries request_id into the Celery tasks a request enqueues.
DJANGO_STRUCTLOG_CELERY_ENABLED = True

REDIS_URL = env("REDIS_URL", default=DEFAULT_REDIS_URL)
REDIS_BROKER_URL = env("REDIS_BROKER_URL", default=REDIS_URL)
REDIS_CACHE_URL = env("REDIS_CACHE_URL", default=REDIS_URL)
REDIS_SSL = is_tls_broker(REDIS_BROKER_URL)

# pap:AD-1 dated exception (2026-09-10, Story 50.1): S3-compatible object
# storage is permitted as a CONSUMED, never self-hosted, backing service --
# production target is NetApp StorageGRID, ops-provided and externally
# operated. Config-only, deliberately with NO default: a default here would
# either point at a specific StorageGRID instance (forbidden) or silently
# resolve to something that looks configured when it is not. See
# config/object_storage.py (Story 50.3) for the client this feeds and
# Story 50.2's local dev backend (scripts/platform_object_storage.py).
OBJECT_STORAGE_ENDPOINT_URL = env("OBJECT_STORAGE_ENDPOINT_URL", default=None)
OBJECT_STORAGE_ACCESS_KEY = env("OBJECT_STORAGE_ACCESS_KEY", default=None)
OBJECT_STORAGE_SECRET_KEY = env("OBJECT_STORAGE_SECRET_KEY", default=None)

from platformapp.front_door.lane1_runtime import locmem_cache_aliases  # noqa: E402

CACHES = locmem_cache_aliases()

TASKS = {
    "default": {
        "BACKEND": "platformapp.front_door.celery_task_backend.CeleryTaskBackend",
    },
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = REDIS_BROKER_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#redis-backend-use-ssl
# Story 41.4 / CAP-12 (red-team X-2 → R-14): a rediss:// broker is VERIFIED
# against the corporate CA bundle. CERT_NONE is laptop-only and refused at
# stage 1 when deployed -- see config/broker_tls.py for the whole posture.
CELERY_BROKER_USE_SSL = broker_use_ssl(REDIS_BROKER_URL)
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = REDIS_BROKER_URL
# Story 40.2 / canopy AD-12: every call site is fire-and-forget (.delay()
# with no AsyncResult consumer; RunState in PostgreSQL is the record of
# fact). Ignore results globally so celery-task-meta-* keys never accumulate
# on the broker; CELERY_RESULT_EXPIRES covers opt-in ignore_result=False.
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_EXPIRES = 3600
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#redis-backend-use-ssl
CELERY_REDIS_BACKEND_USE_SSL = CELERY_BROKER_USE_SSL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
CELERY_RESULT_EXTENDED = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# https://github.com/celery/celery/pull/6122
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# The GENERAL pool's hard limit. Story 42.4 keeps it at five minutes on
# purpose: hours-scale work has its own pool (`builds`, below) -- raising this
# number would hand every queue that limit and put a build on the pool that
# answers Doctor remedies.
CELERY_TASK_TIME_LIMIT = 5 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
CELERY_TASK_SOFT_TIME_LIMIT = 60
# CELERY HARDENING (Story 42.4, CAP-11 / CAP-17, red-team S-2 / T-6 -> R-10)
# ------------------------------------------------------------------------------
# At-least-once delivery. A message is acknowledged AFTER the task returns
# (acks_late), and a worker process that dies mid-task hands its message back
# to the broker instead of acking it (reject_on_worker_lost) -- so a SIGKILL'd
# worker's task is re-delivered and re-run rather than silently dropped with
# its RunState row RUNNING forever. Prefetch 1 so a worker holds only the
# message it is running: a killed worker loses one task, not a prefetched
# batch, and the priority queue is not stuck behind reservations.
#
# The trade is that every task must tolerate a re-run (at-least-once, never
# exactly-once). The supervisor bounds that to ONE re-run per task
# (`django_pyforge.supervisor.begin_attempt`), because a task that kills its
# worker every time is otherwise the message loop `reject_on_worker_lost`
# documents.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Queues. The topology lives in django_pyforge.queues (one table for the
# settings, the chart and the tests): `priority` + `default` + one queue per
# station on the general pool, `builds` on its own Deployment. Declaring every
# queue here means a worker started with no `-Q` (compose, a laptop) consumes
# all of them; the chart is what splits the pools with `-Q`.
from kombu import Queue  # noqa: E402

CELERY_TASK_DEFAULT_QUEUE = DEFAULT_QUEUE
CELERY_TASK_QUEUES = tuple(Queue(name) for name in ALL_QUEUES)
CELERY_TASK_ROUTES = (route_task,)
# The builds pool's hard limit -- hours, not minutes. Its Deployment passes
# the SAME number as `--time-limit` (values `worker.builds.taskTimeLimitSeconds`
# feeds both this env var and the args), so the sweep on any pod and the
# limit on the builds pod agree. Validated here, like the prune interval: the
# broker's visibility timeout is derived from it at settings-load, and a
# builds limit at or under the general limit is "a builds pod with the 300 s
# limit" by another route.
_DEFAULT_BUILDS_TASK_TIME_LIMIT = 4 * 60 * 60
CELERY_BUILDS_TASK_TIME_LIMIT = env.int(
    "CELERY_BUILDS_TASK_TIME_LIMIT",
    default=_DEFAULT_BUILDS_TASK_TIME_LIMIT,
)
if CELERY_BUILDS_TASK_TIME_LIMIT <= CELERY_TASK_TIME_LIMIT:
    CELERY_BUILDS_TASK_TIME_LIMIT = _DEFAULT_BUILDS_TASK_TIME_LIMIT
# https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#visibility-timeout
# With acks_late on Redis an unacked message is re-delivered once the
# visibility timeout passes, so it MUST exceed the longest task any pool may
# run or a live build is delivered twice. The longest is the builds limit;
# the general limit is the slack. `queue_order_strategy=priority` makes a
# worker drain its `-Q` list in order, which is what puts `priority` ahead of
# a station backlog.
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": CELERY_BUILDS_TASK_TIME_LIMIT + CELERY_TASK_TIME_LIMIT,
    "queue_order_strategy": "priority",
}
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Story 42.2 / red-team B-7: run_state had no retention at all, so the table
# grew for the life of the deployment. DatabaseScheduler syncs entries declared
# here into django_celery_beat on startup, so the schedule ships with the code
# rather than depending on an operator adding a row by hand.
#
# Validated HERE rather than at read time like the other 42.2 knobs: beat
# consumes this at settings-load, so a 0 or negative would ship straight into
# `schedule` as a hot loop instead of being rejected on the way out.
_DEFAULT_PRUNE_INTERVAL_SECONDS = 3600
RUN_STATE_PRUNE_INTERVAL_SECONDS = env.int(
    "RUN_STATE_PRUNE_INTERVAL_SECONDS",
    default=_DEFAULT_PRUNE_INTERVAL_SECONDS,
)
if RUN_STATE_PRUNE_INTERVAL_SECONDS <= 0:
    RUN_STATE_PRUNE_INTERVAL_SECONDS = _DEFAULT_PRUNE_INTERVAL_SECONDS
# Story 42.4: the worker-lost sweep (BS-8 partial). Every few minutes, not
# hourly: a row it fails has already sat RUNNING for at least its pool's hard
# limit, and the caller polling `get` is waiting on exactly this write.
_DEFAULT_SWEEP_INTERVAL_SECONDS = 5 * 60
RUN_STATE_SWEEP_INTERVAL_SECONDS = env.int(
    "RUN_STATE_SWEEP_INTERVAL_SECONDS",
    default=_DEFAULT_SWEEP_INTERVAL_SECONDS,
)
if RUN_STATE_SWEEP_INTERVAL_SECONDS <= 0:
    RUN_STATE_SWEEP_INTERVAL_SECONDS = _DEFAULT_SWEEP_INTERVAL_SECONDS
CELERY_BEAT_SCHEDULE = {
    "prune-run-state": {
        "task": "django_pyforge.tasks.prune_run_state_task",
        "schedule": RUN_STATE_PRUNE_INTERVAL_SECONDS,
    },
    "sweep-lost-runs": {
        "task": SWEEP_LOST_RUNS_TASK,
        "schedule": RUN_STATE_SWEEP_INTERVAL_SECONDS,
    },
    "observability-probe": {
        "task": "django_pyforge.tasks.observability_probe_task",
        "schedule": 60,
    },
}
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-hijack-root-logger
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
# django-allauth
# ------------------------------------------------------------------------------
# OIDC-only: no local registration or password login (CAP-1).
ACCOUNT_ALLOW_REGISTRATION = env.bool(
    "DJANGO_ACCOUNT_ALLOW_REGISTRATION", default=False
)
# OIDC-only: no password login. allauth W001 requires every login method
# to appear as a required signup field — empty LOGIN_METHODS always fails.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_ADAPTER = "platformapp.users.adapters.AccountAdapter"
ACCOUNT_FORMS = {"signup": "platformapp.users.forms.UserSignupForm"}
SOCIALACCOUNT_ADAPTER = "config.authorization.adapters.OIDCSocialAccountAdapter"
SOCIALACCOUNT_FORMS = {"signup": "platformapp.users.forms.UserSocialSignupForm"}
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False

OIDC_ISSUER = env.str("COMPONENT_OIDC_ISSUER", default="")
OIDC_CLIENT_ID = env.str("COMPONENT_OIDC_CLIENT_ID", default="")
OIDC_JWKS_URL = env.str("COMPONENT_OIDC_JWKS_URL", default="")
OIDC_AUDIENCE = env.str("COMPONENT_OIDC_AUDIENCE", default="") or OIDC_CLIENT_ID
OIDC_ALGORITHMS = env.list("COMPONENT_OIDC_ALGORITHMS", default=["RS256"])
OIDC_LEEWAY_SECONDS = max(0.0, env.float("COMPONENT_OIDC_LEEWAY_SECONDS", default=0.0))

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": OIDC_PROVIDER_ID,
                "name": env.str("COMPONENT_OIDC_PROVIDER_NAME", default="Platform IdP"),
                "client_id": OIDC_CLIENT_ID,
                "secret": env.str("COMPONENT_OIDC_CLIENT_SECRET", default=""),
                "settings": {
                    "server_url": OIDC_ISSUER,
                },
            },
        ],
    },
}
# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/quickstart/#installation
INSTALLED_APPS += ["compressor"]
STATICFILES_FINDERS += ["compressor.finders.CompressorFinder"]

# Langflow integration (Story 11.1, pap:CAP-2)
# ------------------------------------------------------------------------------
# AD-5: `LANGFLOW_DATABASE_URL` is derived from this platform's OWN
# `DATABASES["default"]` -- the SAME PostgreSQL instance, never a second
# hand-maintained credential -- with a `search_path` suffix pointing Langflow's
# own SQLAlchemy/Alembic layer at `langflow_schema` (provisioned by
# `langflow_integration`'s `RunSQL` migration) instead of `public`. Langflow
# reads this via `os.getenv("LANGFLOW_DATABASE_URL")` directly (its own
# pydantic-settings service, env_prefix "LANGFLOW_"), not through
# django-environ, so the derived values are exported into `os.environ` here --
# they must land there before `langflow_integration/asgi.py` calls
# `create_app()` (config/asgi.py imports that module only after this settings
# module has already executed, mirroring how it already sequences
# config.fastapi_app/config.websocket after django.setup()).
_langflow_db = DATABASES["default"]
_langflow_db_auth = ""
if _langflow_db.get("USER"):
    _langflow_db_auth = quote(_langflow_db["USER"], safe="")
    if _langflow_db.get("PASSWORD"):
        _langflow_db_auth += f":{quote(_langflow_db['PASSWORD'], safe='')}"
    _langflow_db_auth += "@"
LANGFLOW_DATABASE_URL = (
    f"postgresql://{_langflow_db_auth}"
    f"{quote(_langflow_db.get('HOST') or 'localhost', safe='')}:{_langflow_db.get('PORT') or 5432}"
    f"/{quote(_langflow_db['NAME'], safe='')}"
    "?options=-c%20search_path=langflow_schema"
)
os.environ["LANGFLOW_DATABASE_URL"] = LANGFLOW_DATABASE_URL
# The URL's `?options=` suffix alone is NOT sufficient (verified live, Story
# 11.1): `DatabaseService._get_connect_args()` (langflow/services/database/
# service.py) hardcodes `connect_args={"options": "-c timezone=utc"}` for
# every PostgreSQL engine it builds, and SQLAlchemy's `connect_args` wins over
# the URL's own query-string `options` on that same key -- so Langflow's main
# session engine (every ORM query outside Alembic, which builds its own
# connection straight from the URL and is unaffected) silently drops back to
# the `public` search_path, defeating AD-5 for anything but migrations.
# `db_driver_connection_settings`, when set, is returned by
# `_get_connect_args()` BEFORE that hardcoded default is ever reached, so
# folding both `-c` clauses into one `options` value here is the sanctioned
# override -- not a vendored patch (AD-9): a documented Langflow settings key.
os.environ["LANGFLOW_DB_DRIVER_CONNECTION_SETTINGS"] = json.dumps(
    {"options": "-c search_path=langflow_schema -c timezone=utc"},
)

# AD-6: statelessness -- Langflow's cache backend is redis-cache
# (`REDIS_CACHE_URL`), never redis-broker (Celery/Channels). Config and
# knowledge-base paths are explicit, env-overridable locations rather than
# `platformdirs.user_cache_dir()`. Defaults live under `BASE_DIR / ".langflow"`
# (gitignored). The Containerfile's arbitrary-UID runtime MUST keep
# `/app/.langflow` group-writable (GID 0, `g+rwX`) because `create_app()`
# mkdir's them at import time and `/app` itself is deliberately not writable.
LANGFLOW_CACHE_TYPE = env("LANGFLOW_CACHE_TYPE", default="redis")
os.environ["LANGFLOW_CACHE_TYPE"] = LANGFLOW_CACHE_TYPE
os.environ["LANGFLOW_REDIS_URL"] = env("LANGFLOW_REDIS_URL", default=REDIS_CACHE_URL)

LANGFLOW_CONFIG_DIR = env(
    "LANGFLOW_CONFIG_DIR",
    default=str(BASE_DIR / ".langflow" / "config"),
)
LANGFLOW_KNOWLEDGE_BASES_DIR = env(
    "LANGFLOW_KNOWLEDGE_BASES_DIR",
    default=str(BASE_DIR / ".langflow" / "knowledge_bases"),
)
os.environ["LANGFLOW_CONFIG_DIR"] = LANGFLOW_CONFIG_DIR
os.environ["LANGFLOW_KNOWLEDGE_BASES_DIR"] = LANGFLOW_KNOWLEDGE_BASES_DIR

# DB-GPT integration (Story 11.2, pap:CAP-3, AD-17
# Pattern B)
# ------------------------------------------------------------------------------
# AD-5: `DBGPT_DATABASE_URL` is derived from this platform's OWN
# `DATABASES["default"]` -- the SAME PostgreSQL instance, never a second
# hand-maintained credential -- with a `search_path` suffix pointing at
# `dbgpt_schema` (provisioned by `dbgpt_integration`'s `RunSQL` migration),
# mirroring `LANGFLOW_DATABASE_URL`'s shape exactly.
#
# UNLIKE `LANGFLOW_DATABASE_URL`, this value is NOT auto-consumed by anything
# today -- neither Django (no in-process DB-GPT import: DB-GPT is Pattern B,
# its own sidecar container, never an ASGI mount -- see `config/asgi.py`'s
# registry-consult touchpoint and `dbgpt_integration/apps.py`'s docstring)
# NOR the sidecar's own config (DB-GPT's `[service.web.database]` metadata
# store is a TOML value read by its own `ConfigurationManager`, not
# `os.environ`, and -- verified live, Story 11.2 -- only supports
# SQLite/MySQL/OceanBase as a backend; a manual `db.create_all()` against a
# real PostgreSQL engine, using DB-GPT's own public `dbgpt.storage.metadata.
# db_manager` API, fails with a genuine DDL syntax error because DB-GPT's own
# SQLAlchemy models use MySQL-specific `TEXT(length)` column definitions
# PostgreSQL's grammar rejects -- 69 occurrences repo-wide in the installed
# `dbgpt-sidecar` package set, not a one-off. AD-9 forbids forking DB-GPT's
# own model classes to fix this, so the sidecar's metadata store stays on
# Story 10.5's SQLite volume; see `src/platform/compose/compose.yml`'s
# `dbgpt` service for the full citation.
#
# This value exists anyway, as the single source of truth ANY future
# consumer of Django's real PostgreSQL credentials scoped to `dbgpt_schema`
# should read rather than re-deriving them -- e.g. a future upstream fix
# that makes DB-GPT's metadata store PostgreSQL-capable, or a different
# Pattern-B engine that doesn't share this limitation. Today, the actual
# Celery-driven estate read (`dbgpt_integration/tasks.py`) uses
# `QUERY_PLANE_ESTATE_DSN` (CAP-19 / FR-49) — not `DATABASES["default"]`.
# `DBGPT_DATABASE_URL` remains the metadata-schema credential for a future
# sidecar store, not Text-to-SQL.
_dbgpt_db = DATABASES["default"]
_dbgpt_db_auth = ""
if _dbgpt_db.get("USER"):
    _dbgpt_db_auth = quote(_dbgpt_db["USER"], safe="")
    if _dbgpt_db.get("PASSWORD"):
        _dbgpt_db_auth += f":{quote(_dbgpt_db['PASSWORD'], safe='')}"
    _dbgpt_db_auth += "@"
DBGPT_DATABASE_URL = (
    f"postgresql://{_dbgpt_db_auth}"
    f"{quote(_dbgpt_db.get('HOST') or 'localhost', safe='')}:{_dbgpt_db.get('PORT') or 5432}"
    f"/{quote(_dbgpt_db.get('NAME', ''), safe='')}"
    "?options=-c%20search_path=dbgpt_schema"
)
# Deliberately NOT mirrored into `os.environ` the way `LANGFLOW_CONFIG_DIR`
# is above: DB-GPT is Pattern B, a separate sidecar container, so nothing in
# THIS process could ever read this process's `os.environ` -- unlike
# Langflow (Pattern A, in-process), an env-var mutation here would be inert
# by construction. The Django setting above is the real, consumable form.

# CAP-19 / FR-49: agent estate reads (Text-to-SQL, Langflow RAG) hit the
# query plane, never OLTP / langflow_schema. Host does not import pyforge.*.
QUERY_PLANE_ESTATE_DSN = env("QUERY_PLANE_ESTATE_DSN", default="duckdb:atlas.duckdb")
os.environ["LANGFLOW_ESTATE_READ_DSN"] = QUERY_PLANE_ESTATE_DSN

# Story 18.3 / canopy AD-7: dedicated RS256 service-assertion keys.
# Not the OIDC local-dev persona mint (config.local_dev.tokens).
PYFORGE_ASSERTION_PRIVATE_KEY = env("PYFORGE_ASSERTION_PRIVATE_KEY", default="")
PYFORGE_ASSERTION_PUBLIC_KEY = env("PYFORGE_ASSERTION_PUBLIC_KEY", default="")

# AGENT RATE LIMITS AND RUN BOUNDS (Story 42.2, CAP-11 / CAP-17)
# ------------------------------------------------------------------------------
# Red-team A-6 / B-7 → directive R-8. Every number is a setting so a deployment
# can tune it without a code change; these are the documented defaults, and
# they are per SUBJECT (the verified `sub` claim), never per client name.
#
# Bucket state lives in CACHES["default"] — redis-cache (AD-10), evictable —
# never on redis-broker, whose exhaustion is what these bounds exist to
# prevent. See django_pyforge/rate_limit.py.
#
# The MCP route carries reads as well as writes, so it is the wider bucket. A
# `start` costs a database row and a queued task, so its bucket is narrower and
# is additionally capped by the two ceilings below.
MCP_RATE_LIMIT_PER_MINUTE = env.int("MCP_RATE_LIMIT_PER_MINUTE", default=120)
MCP_RATE_LIMIT_BURST = env.int("MCP_RATE_LIMIT_BURST", default=120)
SUPERVISOR_START_RATE_PER_MINUTE = env.int(
    "SUPERVISOR_START_RATE_PER_MINUTE",
    default=30,
)
SUPERVISOR_START_BURST = env.int("SUPERVISOR_START_BURST", default=30)
# Concurrent non-terminal runs one subject may hold. Reaching it is 409 with
# the live run ids, because the caller's own runs are the conflict.
MAX_RUNNING_PER_SUB = env.int("MAX_RUNNING_PER_SUB", default=5)
# Non-terminal runs one station may hold across all subjects — the queue-depth
# ceiling. Reaching it is 429 with Retry-After and no RunState row.
MAX_QUEUE_DEPTH_PER_STATION = env.int("MAX_QUEUE_DEPTH_PER_STATION", default=100)
# Retention: terminal rows older than this are pruned by the beat task, and the
# table is additionally capped so a burst inside the window cannot unbound it.
RUN_STATE_RETENTION_DAYS = env.int("RUN_STATE_RETENTION_DAYS", default=14)
RUN_STATE_MAX_ROWS = env.int("RUN_STATE_MAX_ROWS", default=100_000)
# Rows one sweep may remove. The first sweep after this story deploys runs over
# a table that has never been pruned, and one unbounded DELETE across it can
# exceed CELERY_TASK_SOFT_TIME_LIMIT and never complete — a retention task that
# cannot finish bounds nothing. The sweep reports `truncated` when work remains.
RUN_STATE_PRUNE_BATCH = env.int("RUN_STATE_PRUNE_BATCH", default=5_000)

# Your stuff...
# ------------------------------------------------------------------------------
