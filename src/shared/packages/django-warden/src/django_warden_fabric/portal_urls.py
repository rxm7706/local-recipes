from django.urls import path

from . import views

urlpatterns = [
    path("", views.chrome_home, name="home"),
]
