from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.upload_manifest, name="compliance-face-upload"),
    path("jobs/<uuid:job_id>/", views.job_status, name="compliance-face-status"),
    path(
        "jobs/<uuid:job_id>/report/",
        views.job_report,
        name="compliance-face-report",
    ),
]
