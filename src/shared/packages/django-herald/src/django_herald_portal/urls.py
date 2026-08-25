from django.urls import path

from django_herald_portal import views

urlpatterns = [
    path("", views.chrome_home, name="herald-home"),
]
