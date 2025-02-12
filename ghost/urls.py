from django.urls import path
from ghost import views

app_name = "ghost"

urlpatterns = [
	path("", views.home, name="home"),
	path("ghost/", views.ghost, name="ghost"),
	path("ghost/multiestruturas/", views.multiestruturas, name="multiestruturas"),
	path("ghost/relatoriomultiestruturas", views.baixar_relatorio_multiestruturas, name="relatorio-multiestruturas"),
	path("ghost/bomxop", views.bomxop, name="bomxop"),
	path("ghost/bomxoppost", views.bomxop_post, name="bomxop-post"),
	path("ghost/relatoriobomxopsimples", views.baixar_relatorio_bomxop_simples, name="relatorio-bomxop-simples"),
	path("buscarprocessamento/", views.buscar_processamento, name="buscar_processamento"),
	path("ghost/bomxopstd", views.bomxopstd, name="bomxopstd"),
	path("ghost/bomxopstdpost", views.bomxopstd_post, name="bomxopstd-post"),
]
