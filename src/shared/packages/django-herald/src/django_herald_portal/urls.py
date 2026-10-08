from django.urls import path

from django_herald_portal import views

urlpatterns = [
    path("", views.chrome_home, name="herald-home"),
    path("decks/", views.deck_list, name="herald-deck-list"),
    path("decks/<slug:slug>/view/", views.deck_view, name="herald-deck-view"),
]
