from django.urls import include
from django.urls import path

from . import views

urlpatterns = [
    path("", views.chrome_home, name="home"),
    path("", include("django_warden_fabric.urls")),
]
