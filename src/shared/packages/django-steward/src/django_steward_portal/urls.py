from django.urls import path

from django_steward_portal import views

urlpatterns = [
    path("", views.chrome_home, name="steward-home"),
]
