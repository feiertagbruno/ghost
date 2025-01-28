from django.shortcuts import render,redirect
from django.urls import reverse
from datetime import datetime
from ghost.estruturas import estrutura_simples
import pandas as pd
from django.contrib import messages

def home(request):
	return render(request, "ghost/home.html")

def ghost(request):
	data_referencia = datetime.strftime(datetime.today().date(),"%Y-%m-%d")
	context = {
		"data_referencia":data_referencia
	}
	return render(request, "ghost/ghost_home.html", context)

def multiestruturas(request):
	
	if request.method != "POST": return redirect(reverse("ghost:ghost"))

	produtos = request.POST.get("codigos-produtos")

	if not produtos: return redirect(reverse("ghost:ghost"))

	produtos = produtos.split("\r\n")
	produtos_filtrados = [item for item in produtos if item != ""]

	data_referencia = request.POST.get("data-referencia")
	if not data_referencia: data_referencia = datetime.today().date()

	compilado_estruturas = pd.DataFrame()
	compilado_custos_totais = pd.DataFrame()

	for produto in produtos_filtrados:
		produto = produto.strip().upper()

		if len(produto) == 7 or len(produto) == 15:
			estrutura, custos_totais_produto = estrutura_simples(produto, data_referencia)
			compilado_estruturas = pd.concat([compilado_estruturas, estrutura])
			compilado_custos_totais = pd.concat([compilado_custos_totais, custos_totais_produto])
		else:
			messages.info(request, f"Produto {produto} contém um erro de digitação.")


	if compilado_custos_totais.empty:
		messages.info(request, "Sua busca retornou sem resultados")
		return redirect(reverse("ghost:ghost"))
	
	custos_totais_dict = compilado_custos_totais.to_dict(orient="records")

	context = {
		"custos_totais": custos_totais_dict,
	}

	return render(request,"ghost/ghost_multiestruturas.html", context)
	
