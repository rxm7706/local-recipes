"""Mint path owned by the chrome package, not a station roster."""

from django.urls import path

from django_pyforge.assertion.views import mint

urlpatterns = [
    path("mint/", mint, name="django-pyforge-assertion-mint"),
]
