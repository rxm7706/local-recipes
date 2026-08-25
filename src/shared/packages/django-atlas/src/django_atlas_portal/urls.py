from django.urls import path

from django_atlas_portal import views

urlpatterns = [
    path("", views.chrome_home, name="atlas-home"),
]
