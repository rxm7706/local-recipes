# ruff: noqa: ERA001, E501
"""Base settings to build other settings files upon."""

import importlib.util
import json
import os
import ssl
import sys
from pathlib import Path
from urllib.parse import quote

import environ
from django.urls import reverse_lazy

from config.authorization.claims import load_claims_contract
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
    # "django.contrib.humanize", # Handy template tags
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
LOGIN_URL = reverse_lazy("openid_connect_login", kwargs={"provider_id": OIDC_PROVIDER_ID})
CLAIMS_CONTRACT = load_claims_contract(env)
# Story 26.1 / FR-31: re-read IdP roles from token claims on each request.
DJANGO_PYFORGE_GROUP_CLAIM = CLAIMS_CONTRACT.group_claim or "groups"
DJANGO_PYFORGE_IDP_CLAIMS_GETTER = "config.authorization.current_claims.fetch_current_idp_claims"
IDP_CLAIMS_SNAPSHOT = None
IDP_USERINFO = None
# steward 20.1 / canopy AD-13: Wagtail admin is IdP-only (not a URLconf override).
WAGTAILADMIN_LOGIN_URL = LOGIN_URL
WAGTAILUSERS_PASSWORD_ENABLED = False
WAGTAIL_EMAIL_MANAGEMENT_ENABLED = False
WAGTAIL_PASSWORD_MANAGEMENT_ENABLED = False
WAGTAIL_SITE_NAME = env.str("WAGTAIL_SITE_NAME", default="PyForge")
WAGTAILADMIN_BASE_URL = env.str("WAGTAILADMIN_BASE_URL", default="http://localhost:8000")
WAGTAIL_ADMIN_IDP_GROUP = env.str("COMPONENT_WAGTAIL_ADMIN_GROUP", default="wagtail-admin")
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

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
REDIS_BROKER_URL = env("REDIS_BROKER_URL", default=REDIS_URL)
REDIS_CACHE_URL = env("REDIS_CACHE_URL", default=REDIS_URL)
REDIS_SSL = REDIS_BROKER_URL.startswith("rediss://")

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
CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE} if REDIS_SSL else None
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = REDIS_BROKER_URL
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
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 5 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-hijack-root-logger
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
# django-allauth
# ------------------------------------------------------------------------------
# OIDC-only: no local registration or password login (CAP-1).
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", default=False)
ACCOUNT_LOGIN_METHODS = set()
ACCOUNT_SIGNUP_FIELDS = []
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

# Langflow integration (Story 11.1, spec-python-agent-platform CAP-2)
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
    "LANGFLOW_CONFIG_DIR", default=str(BASE_DIR / ".langflow" / "config"),
)
LANGFLOW_KNOWLEDGE_BASES_DIR = env(
    "LANGFLOW_KNOWLEDGE_BASES_DIR",
    default=str(BASE_DIR / ".langflow" / "knowledge_bases"),
)
os.environ["LANGFLOW_CONFIG_DIR"] = LANGFLOW_CONFIG_DIR
os.environ["LANGFLOW_KNOWLEDGE_BASES_DIR"] = LANGFLOW_KNOWLEDGE_BASES_DIR

# DB-GPT integration (Story 11.2, spec-python-agent-platform CAP-3, AD-17
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
# Celery-driven round trip (`dbgpt_integration/tasks.py`) reads
# `DATABASES["default"]` directly instead (it registers `public`, the
# database Django's own tables live in, as a DB-GPT DATASOURCE to query --
# an entirely different connection than the sidecar's own metadata store,
# and unaffected by the limitation above).
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

# Story 18.3 / canopy AD-7: dedicated RS256 service-assertion keys.
# Not the OIDC local-dev persona mint (config.local_dev.tokens).
PYFORGE_ASSERTION_PRIVATE_KEY = env("PYFORGE_ASSERTION_PRIVATE_KEY", default="")
PYFORGE_ASSERTION_PUBLIC_KEY = env("PYFORGE_ASSERTION_PUBLIC_KEY", default="")

# Your stuff...
# ------------------------------------------------------------------------------
