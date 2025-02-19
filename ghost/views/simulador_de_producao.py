from django.shortcuts import render,redirect
from django.urls import reverse
from django.contrib import messages
from django.db import connection
import pandas as pd
import sqlite3
from sqlalchemy import text
from datetime import datetime
from io import StringIO
from ghost.queries import get_query_estoque_atual
from ghost.views.estruturas import explode_estrutura, forma_string_codigos
from ghost.utils.funcs import get_engine, tratamento_data_referencia, gerar_codigo_aleatorio

def simulador_de_producao(request):
	context = {"inicial":True}
	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html", context)


def adicionar_producao(request):
	if not request.method == "POST":
		return redirect(reverse("ghost:simulador-de-producao"))
	
	engine = get_engine()
	
	codigo = request.POST.get("codigo-produto")
	data = request.POST.get("data-producao")
	quant = request.POST.get("quantidade")
	
	try:
		quant = float(quant)
	except:
		messages.error(request, "Quantidade inválida")
		return redirect(reverse("ghost:simulador-de-producao"))
	if data:
		data = tratamento_data_referencia(data)

	if data < datetime.today().date():
		messages.error(request, "A data digitada não pode ser menor do que hoje")
		return redirect(reverse("ghost:simulador-de-producao"))

	estrutura, todos_os_codigos = explode_estrutura(
		codigo=codigo,
		data_referencia = data,
		engine = engine,
		abre_todos_os_PIs=False,
		solicitante='simulador'
	)

	estrutura["quant_utilizada"] = estrutura["quant_utilizada"].astype(float).map(lambda x: x * quant)
	todos_os_codigos = forma_string_codigos(todos_os_codigos["todos_os_codigos"])

	query_estoque = get_query_estoque_atual()
	estoque = pd.read_sql(text(query_estoque),engine, params={
		"codigos": todos_os_codigos,
	})

	armazens_visiveis = ['11','14','20','80','98','','Ttl Est']
	estoque_pivot = estoque.pivot(index="codigo", columns="armazem", values="quant").fillna(0).reset_index()
	arm_exist = [col for col in armazens_visiveis if col in estoque_pivot.columns]
	estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)
	hoje = datetime.today().strftime('%d/%m/%Y')
	
	novos_cabecalhos = {}
	i=0
	for col in estoque_pivot.columns:
		i += 1
		novos_cabecalhos.update({col:f"{i:04}|Estoque|{hoje}|{col}"})

	estoque_pivot = estoque_pivot.rename(columns=novos_cabecalhos)

	armazens = estoque["armazem"].unique().tolist()
	
	novos_cabecalhos = {}
	data_str = data.strftime('%d/%m/%Y')
	for col in estrutura.columns:
		i += 1
		if col == 'insumo': coluna_codigo = f"{i:04}|Produção|{data_str}|{col}"
		novos_cabecalhos.update({col: f"{i:04}|Produção|{data_str}|{col}"})

	estrutura = estrutura.rename(columns=novos_cabecalhos)

	simulador = estoque_pivot.merge(
		estrutura,how="left",
		left_on=f'0001|Estoque|{hoje}|codigo',
		right_on=coluna_codigo
	)

	simulador[f'{i:04}|Produção|{data_str}|Resultado'] = \
		(simulador.filter(like="Ttl Est").values - simulador.filter(like="quant_utilizada").values).round(5)
	
	negativos = simulador.loc[
		(simulador.filter(like="Resultado").values < 0) & (simulador.filter(like="tipo_insumo").values == 'PI')
		,:
	]

	codigo_aleatorio = gerar_codigo_aleatorio(10)
	sqlite_conn = sqlite3.connect('db.sqlite3')
	simulador.to_sql(name=codigo_aleatorio, con=sqlite_conn, if_exists="replace", index=False)

	cat_anterior = ''
	dat_anterior = ''
	cabecalhos = {
		"indice":{},
		"categoria":{},
		"data":{},
		"campo":{},
	}
	for col in simulador.columns:
		i, cat, dat, campo = col.split("|")
		if cat == cat_anterior:
			cabecalhos["categoria"][cat] += 1
		else:
			cabecalhos["categoria"].update({cat:1})
		cat_anterior = cat

		if dat == dat_anterior:
			cabecalhos["data"][dat] += 1
		else:
			cabecalhos["data"].update({dat:1})
		dat_anterior = dat

		cabecalhos["campo"].update({campo:1})


	rows = []
	for i, row in simulador.iterrows():
		row_data = row.to_dict()
		row_data["index"] = i
		rows.append(row_data)
	

	context = {
		"inicial":False,
		"cabecalhos":cabecalhos,
		"rows":rows,
		"codigo_aleatorio": codigo_aleatorio,
	}

	
	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html",context)

def reprocessar_tabela(request):
	if request.method != "POST":
		return redirect(reverse("ghost:simulador-de-producao"))

	armazens = request.POST.getlist("armazem-checkbox")
	tabela = request.POST.get("tabela-simulador-html")
	if tabela:
		tabela = pd.read_html(StringIO(tabela), header=[0,1,2])[0]

	tb_filtrada = tabela.loc[:, tabela.columns.get_level_values(0) == 'Estoque']
	# tb_filtrada = tabela

	prim_cabecalho = tabela.columns.values[0]

	for col in tabela.columns.values:
		if col[2] == "Ttl Est":
			tabela = tabela.drop(columns=col)

	tabela.loc[:, (prim_cabecalho[0], prim_cabecalho[1], "Ttl Est")] = \
    	tabela.loc[:, tabela.columns.get_level_values(2).isin(armazens)].sum(axis=1)

	cabecalhos = {
		"data": tabela.columns.levels[1],
		"armazem": [*tabela.columns.levels[2]],
		"tam": len(tabela.columns.levels[2]),
	}

	rows = tabela.reset_index(drop=True).to_dict(orient="records")

	context = {
		"cabecalhos": cabecalhos,
		"rows": rows,
		"armazens_visiveis": ['Código','Ttl Est',*armazens],
		"armazens":armazens,
		"inicial": False,
	}

	return render(request, "ghost/simuladordeproducao/tabela_simulador.html",context)



