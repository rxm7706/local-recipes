from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from health_check.views import HealthCheckView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("platformapp.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    path("compliance/", include("compliance_face.urls")),
    # K8s liveness/readiness probe target (Story 10.1). Deliberately
    # unauthenticated at the app layer -- standard for a kubelet-probed
    # endpoint; restricting it to cluster-internal traffic is a network/
    # ingress-layer concern owned by the deployment epic, not this one.
    #
    # Story 10.3: this app runs against TWO django-health-check versions --
    # [feature.platform-ci-test] pins pip's `django-health-check==3.24.0` (used
    # by platform-ci.yml's `test` job) while pixi.toml's conda-sourced
    # `python-agent-platform` env pins `>=4.5.0` (used by the container
    # image `test`/`container` jobs and this Containerfile). 4.x has no
    # `health_check.urls` module at all, so both versions are wired the
    # SAME way here -- `HealthCheckView` with an explicit `checks` list --
    # rather than the deprecated `include("health_check.urls")` path 3.x
    # still (barely) supports.
    #
    # `checks` MUST be dotted STRINGS (`"health_check.Database"`), never the
    # imported classes directly -- caught live in review: 3.24.0's
    # `get_plugins()` does `check, options = check` unconditionally, caught
    # only by `except ValueError`; a raw class is non-iterable and raises
    # `TypeError`, which 3.24.0 does NOT catch (only 4.5.0's `get_checks()`
    # catches `(ValueError, TypeError)`). A bare string of length != 2 raises
    # `ValueError` on that same unpack attempt (caught), then resolves via
    # `import_string` -- the only invocation shape safe under BOTH pinned
    # versions. `health_check.Database`/`health_check.Cache` are exported at
    # the `health_check` package ROOT identically in both 3.24.0 and 4.5.0
    # (confirmed by reading both installed packages directly), so the same
    # two dotted strings resolve correctly regardless of which version is
    # installed. The DEFAULT `checks` is itself version-dependent, so it is
    # not a safe thing to fall back on here (read from both installed
    # packages): 3.24.0 defaults to `("health_check.Cache", ".Database",
    # ".Mail", ".Storage")`, while 4.5.0 defaults to
    # `("health_check.checks.Cache", ".Database", ".DNS", ".Mail",
    # ".Storage")` -- a different module path AND an extra DNS check that
    # would make this endpoint depend on outbound name resolution. Pinned
    # here to exactly `[Database, Cache]` to preserve Story 10.1's original
    # scope (PostgreSQL + the configured cache backend only); dropping the
    # explicit list is therefore a behaviour change, not a simplification.
    #
    # WHAT THIS ENDPOINT DOES AND DOES NOT PROVE, stated because the
    # behaviour changed here and a probe is easy to over-trust:
    # `health_check.Database` is a CONNECTIVITY probe (3.24.0's
    # `DatabaseHeartBeatCheck`, 4.5.0's `Database` -- both a bare `SELECT`),
    # NOT the `TestModel` write/read/delete round-trip the removed
    # `health_check.db` sub-app registered. A 200 here therefore means "the
    # database answers", not "the schema is migrated" or "writes succeed":
    # an unmigrated database, a read-only replica, or a full disk all still
    # return 200. That is the right shape for a kubelet liveness/readiness
    # probe (cheap and non-mutating), but anything that needs to know the
    # app can actually serve ORM-backed pages has to assert that separately
    # -- `platform-ci.yml`'s `container` job does it with `/admin/login/`.
    # The change is inherent to leaving the deprecated app-based mechanism;
    # it is recorded rather than fixed.
    #
    # This route is regression-tested by `tests/test_health_endpoint.py`,
    # which is the ONLY thing that exercises the string-vs-class trap above
    # against the pip-pinned 3.24.0 -- `manage.py check` cannot, because
    # `get_plugins()` is reached only from a real request.
    path(
        "ht/",
        HealthCheckView.as_view(checks=["health_check.Database", "health_check.Cache"]),
    ),
    # Your stuff: custom urls includes go here
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
