from django.urls import path
from ghost import views

app_name = "ghost"

urlpatterns = [
	path("", views.home, name="home"),
	path("ghost/", views.ghost, name="ghost"),
	path("ghost/multiestruturas/", views.multiestruturas, name="multiestruturas"),
]
