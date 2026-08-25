from django.urls import path

from django_pyforge.probe_portal import views

urlpatterns = [
    path("", views.chrome_home, name="chrome-probe-home"),
    path("form/", views.chrome_form, name="chrome-probe-form"),
]
