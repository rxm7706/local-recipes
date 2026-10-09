from django.urls import include
from django.urls import path

from . import views

urlpatterns = [
    path("", views.chrome_home, name="home"),
    path("audits/start/", views.start_audit, name="warden-audit-start"),
    path("audits/", views.get_audit, name="warden-audit-get"),
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
