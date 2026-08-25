from django.urls import path

from django_scribe_portal import views

urlpatterns = [
    path("", views.chrome_home, name="scribe-home"),
]
