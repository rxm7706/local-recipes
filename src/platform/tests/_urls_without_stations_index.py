"""URLconf equal to config.urls minus the stations-index route (Story 91.1 AC2)."""

from config.urls import urlpatterns as _patterns

_INDEX_ROUTE = "stations-index"

urlpatterns = [p for p in _patterns if getattr(p, "name", None) != _INDEX_ROUTE]

# AC2 compares the index against config.urls minus exactly this route. Should the
# route be renamed, the filter would drop nothing and AC2 would compare the index
# with itself, so refuse to load rather than pass vacuously.
if len(_patterns) - len(urlpatterns) != 1:
    msg = f"expected exactly one {_INDEX_ROUTE!r} pattern in config.urls"
    raise RuntimeError(msg)
