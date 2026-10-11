"""URLconf equal to config.urls minus the stations-index route (Story 91.1 AC2)."""

from config.urls import urlpatterns as _patterns

urlpatterns = [p for p in _patterns if getattr(p, "name", None) != "stations-index"]
