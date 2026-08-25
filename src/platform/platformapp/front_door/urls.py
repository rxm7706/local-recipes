from django.urls import path

from platformapp.front_door.views import runs_board

urlpatterns = [
    path("runs/", runs_board, name="front_door_runs"),
]
