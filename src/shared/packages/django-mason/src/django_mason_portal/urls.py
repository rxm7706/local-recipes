from django.urls import path

from django_mason_portal import views

urlpatterns = [
    path("", views.chrome_home, name="mason-home"),
]
