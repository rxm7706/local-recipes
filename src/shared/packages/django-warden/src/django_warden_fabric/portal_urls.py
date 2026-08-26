from django.urls import include
from django.urls import path

from . import views

urlpatterns = [
    path("", views.chrome_home, name="home"),
    path("audits/start/", views.start_audit, name="warden-audit-start"),
    path("audits/", views.get_audit, name="warden-audit-get"),
    path("", include("django_warden_fabric.urls")),
]
