from django.urls import path, re_path

from django_herald_portal import herald_guard, views

if herald_guard.herald_is_installed():
    urlpatterns = [
        path("", views.chrome_home, name="herald-home"),
        path("decks/", views.deck_list, name="herald-deck-list"),
        path("decks/<slug:slug>/view/", views.deck_view, name="herald-deck-view"),
    ]
else:
    urlpatterns = [
        path("", views.herald_portal_unavailable, name="herald-home"),
        path("decks/", views.herald_portal_unavailable, name="herald-deck-list"),
        path(
            "decks/<slug:slug>/view/",
            views.herald_portal_unavailable,
            name="herald-deck-view",
        ),
        # Every other path under /stations/herald/ answers the same reason.
        re_path(r"^.*$", views.herald_portal_unavailable),
    ]
