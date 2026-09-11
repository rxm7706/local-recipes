import sys

from config.authorization.idp_userinfo import DEFAULT_CLAIMS_CACHE_SECONDS
from config.authorization.idp_userinfo import fetch_current_userinfo
from config.observability.logging import build_logging_config
from config.startup import run_stage_one
from config.startup.stage_one import refuse_required_settings
from platformapp.front_door.lane1_runtime import channel_layers_for_broker
from platformapp.front_door.lane1_runtime import django_cache_aliases

from .base import *  # noqa: F403
from .base import DATABASES
from .base import DEBUG
from .base import DJANGO_LOG_FORMAT
from .base import DJANGO_LOG_LEVEL
from .base import INSTALLED_APPS
from .base import REDIS_BROKER_URL
from .base import REDIS_CACHE_URL
from .base import env

# CAP-3 / steward 16.2: named required-env refusals *before* django-environ
# raises an opaque ImproperlyConfigured on missing DJANGO_SECRET_KEY /
# DJANGO_ADMIN_URL. Deployed-only (see config.locality).
refuse_required_settings()

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["platform.internal"])

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# CACHES (redis-cache only — Celery/Channels stay on REDIS_BROKER_URL)
# ------------------------------------------------------------------------------
CACHES = django_cache_aliases(REDIS_CACHE_URL)
CHANNEL_LAYERS = channel_layers_for_broker(REDIS_BROKER_URL)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-name
SESSION_COOKIE_NAME = "__Secure-sessionid"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-name
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

# STATIC & MEDIA
# ------------------------
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="Python Agent Platform <noreply@platform.internal>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[Python Agent Platform] ",
)
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
ANYMAIL: dict[str, str] = {}

# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_ENABLED
COMPRESS_ENABLED = env.bool("COMPRESS_ENABLED", default=True)
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_STORAGE
COMPRESS_STORAGE = "compressor.storage.GzipCompressorFileStorage"
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_URL
COMPRESS_URL = STATIC_URL  # noqa: F405
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_OFFLINE
COMPRESS_OFFLINE = True  # Offline compression is required when using Whitenoise
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_FILTERS
COMPRESS_FILTERS = {
    "css": [
        "compressor.filters.css_default.CssAbsoluteFilter",
        "compressor.filters.cssmin.rCSSMinFilter",
    ],
    "js": ["compressor.filters.jsmin.JSMinFilter"],
}

# LOGGING (CAP-2 — structured; mail_admins retained for 500s)
# ------------------------------------------------------------------------------
LOGGING = build_logging_config(
    debug=DEBUG,
    log_level=DJANGO_LOG_LEVEL,
    log_format=DJANGO_LOG_FORMAT or None,
    extra_handlers={
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    extra_loggers={
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "mail_admins"],
            "propagate": True,
        },
    },
)
# RequireDebugFalse filter used by mail_admins (dictConfig filter registry).
LOGGING["filters"] = {
    "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
}


# Your stuff...
# ------------------------------------------------------------------------------

# Story 49.6 / CAP-12: re-read IdP roles from userinfo within a bounded cache
# window so revocation at Keycloak (Story 48.9 default profile) lands on the
# next request, not the next login. Local/test keep base.py's None hook and use
# IDP_CLAIMS_SNAPSHOT in tests instead.
IDP_CLAIMS_CACHE_SECONDS = env.int(
    "COMPONENT_IDP_CLAIMS_CACHE_SECONDS",
    default=DEFAULT_CLAIMS_CACHE_SECONDS,
)
IDP_USERINFO = fetch_current_userinfo

# CAP-3 stage 1: last statement of this leaf (not base.py). Re-checks required
# env, then refuses unverified broker TLS (Story 41.4) — that condition reads
# the composed CELERY_BROKER_URL off this module, which is why the call passes
# the module and why it has to be last.
run_stage_one(sys.modules[__name__])
