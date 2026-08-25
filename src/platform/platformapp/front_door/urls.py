from django.urls import path

from platformapp.front_door.views import console_catalog
from platformapp.front_door.views import console_directory
from platformapp.front_door.views import console_editorial
from platformapp.front_door.views import console_health
from platformapp.front_door.views import runs_board

urlpatterns = [
    path("runs/", runs_board, name="front_door_runs"),
    path("console/", console_directory, name="front_door_console"),
    path("console/health/", console_health, name="front_door_console_health"),
    path(
        "console/editorial/",
        console_editorial,
        name="front_door_console_editorial",
    ),
    path(
        "console/dreams/",
        console_catalog,
        {"surface_id": "dreams"},
        name="front_door_console_dreams",
    ),
    path(
        "console/specs/",
        console_catalog,
        {"surface_id": "specs"},
        name="front_door_console_specs",
    ),
    path(
        "console/story-specs/",
        console_catalog,
        {"surface_id": "story_specs"},
        name="front_door_console_story_specs",
    ),
    path(
        "console/guild/",
        console_catalog,
        {"surface_id": "guild"},
        name="front_door_console_guild",
    ),
    path(
        "console/backlog/",
        console_catalog,
        {"surface_id": "backlog"},
        name="front_door_console_backlog",
    ),
    path(
        "console/open-work/",
        console_catalog,
        {"surface_id": "open_work"},
        name="front_door_console_open_work",
    ),
    path(
        "console/archived/",
        console_catalog,
        {"surface_id": "archived"},
        name="front_door_console_archived",
    ),
    path(
        "console/programs/",
        console_catalog,
        {"surface_id": "in_build_realized_membership"},
        name="front_door_console_programs",
    ),
]
