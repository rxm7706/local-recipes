from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.chrome_home, name="home"),
    path("audits/start/", views.start_audit, name="warden-audit-start"),
    path("audits/", views.get_audit, name="warden-audit-get"),
    path(
        "fleet/inventory/start/",
        views.start_fleet_inventory,
        name="warden-fleet-inventory-start",
    ),
    path(
        "fleet/project-items/start/",
        views.start_fleet_project_items,
        name="warden-fleet-project-items-start",
    ),
    path(
        "fleet/proposals/",
        views.fleet_proposal_queue,
        name="warden-fleet-proposals",
    ),
    path(
        "fleet/proposals/<uuid:proposal_id>/approve/",
        views.fleet_proposal_approve,
        name="warden-fleet-proposal-approve",
    ),
    path(
        "fleet/proposals/<uuid:proposal_id>/dismiss/",
        views.fleet_proposal_dismiss,
        name="warden-fleet-proposal-dismiss",
    ),
    path("", include("django_warden_fabric.urls")),
]
