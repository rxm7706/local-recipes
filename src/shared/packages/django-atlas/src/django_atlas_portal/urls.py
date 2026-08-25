from django.urls import path

from django_atlas_portal import board
from django_atlas_portal import views

urlpatterns = [
    path("", views.chrome_home, name="atlas-home"),
    path("board/", board.board_view, name="atlas-board"),
]
