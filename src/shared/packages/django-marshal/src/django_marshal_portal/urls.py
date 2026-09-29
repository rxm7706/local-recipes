from django.urls import path

from django_marshal_portal import views

urlpatterns = [
    path("", views.chrome_home, name="marshal-home"),
    path("watch/", views.watch_report, name="marshal-watch"),
]
