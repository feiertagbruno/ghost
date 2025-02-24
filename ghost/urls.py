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
	path("ghost/materiais/simuladordeproducao/", views.simulador_de_producao, name="simulador-de-producao"),
	path("ghost/materiais/adicionarproducao/", views.adicionar_producao, name="adicionar-producao"),
	path("ghost/materiais/reprocessartabela", views.reprocessar_tabela, name="reprocessar-tabela"),
	path("alterasimuladordeproducao/", views.altera_simulador_de_producao), #simulador_de_producao.py
    path("salvarsimulacao/", views.salvar_simulacao), #simulador_de_producao.py
    path("trazersimulacao", views.trazer_simulacao, name="trazer-simulacao"), #simulador_de_producao.py
]
