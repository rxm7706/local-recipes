from django.urls import path

from django_pyforge.workclass_probe import views

urlpatterns = [
    path("", views.chrome_home, name="infra-probe-home"),
]
