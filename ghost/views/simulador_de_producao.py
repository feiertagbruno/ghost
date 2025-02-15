from django.shortcuts import render,redirect
from django.urls import reverse
from ghost.queries import get_query_estoque_atual
from ghost.functions.estruturas import get_engine
import pandas as pd
from sqlalchemy import text
from datetime import datetime

def simulador_de_producao(request):

	engine = get_engine()

	query_estoque = get_query_estoque_atual()
	estoque = pd.read_sql(text(query_estoque),engine)

	estoque_pivot = estoque.pivot(index="codigo", columns="armazem", values="quant")
	hoje = datetime.today().strftime('%d/%m/%Y')
	estoque_pivot.columns = pd.MultiIndex.from_tuples(
		[(hoje,armazem) for armazem in estoque_pivot.columns], names=["Data","Armazém"]
	)

	context = {
		"simulador": estoque_pivot,
	}

	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html", context)

def adicionar_producao(request):
	if not request.method == "POST":
		return redirect(reverse("ghost:simulador-de-producao"))
	
	return render()