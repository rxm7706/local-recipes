from django.urls import path

from django_doctor_portal import views

urlpatterns = [
    path("", views.chrome_home, name="doctor-home"),
]
