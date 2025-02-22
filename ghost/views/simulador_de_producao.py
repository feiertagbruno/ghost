from django.shortcuts import render,redirect
from django.urls import reverse
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd
import sqlite3
from sqlalchemy import text
from datetime import datetime
from io import StringIO
from numpy import nan
from ghost.queries import get_query_estoque_atual
from ghost.views.estruturas import explode_estrutura, forma_string_codigos, estrutura_simples
from ghost.utils.funcs import (
	get_engine, tratamento_data_referencia, gerar_codigo_aleatorio_simulador,
	get_info_produtos
)
from ghost.views.consultas import get_produzidos_na_data,get_pedidos

def simulador_de_producao(request):
	if request.session.get("codigo-aleatorio"):
		del(request.session["codigo-aleatorio"])
	context = {"inicial":True}
	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html", context)


def adicionar_producao(request):
	if not request.method == "POST":
		return redirect(reverse("ghost:simulador-de-producao"))
	
	codigo_aleatorio = request.session.get("codigo-aleatorio")

	# if codigo_aleatorio:
	# 	return adicionar_nova_producao(request)

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


	# PRODUZIDOS
	hoje_date = datetime.today().date()
	if data == hoje_date:
		produzidos = get_produzidos_na_data(
			data_inicial=data,
			codigos=codigo,
			engine=engine
		)
		if not produzidos.empty:
			quant -= produzidos.loc[produzidos["codigo"] == codigo, "quant"].values[0]

	estrutura["quant_utilizada"] = estrutura["quant_utilizada"].astype(float).map(lambda x: -round(x * quant,5))
	todos_os_codigos = pd.concat([
		todos_os_codigos, 
		estrutura.loc[estrutura["codigo_pai"].notna(),["codigo_pai"]]\
			.rename(columns={"codigo_pai":"todos_os_codigos"}),
		pd.DataFrame({"todos_os_codigos":[codigo]})
	])
	todos_os_codigos = forma_string_codigos(todos_os_codigos["todos_os_codigos"].drop_duplicates())

	query_estoque = get_query_estoque_atual()
	estoque = pd.read_sql(text(query_estoque),engine, params={
		"codigos": todos_os_codigos,
	})

	# FORMA O ESTOQUE_PIVOT
	armazens_visiveis = ['11','14','20','80','98','','Ttl Est']
	estoque_pivot = estoque.pivot(index="codigo", columns="armazem", values="quant").reset_index()
	arm_exist = [col for col in estoque_pivot.columns if len(col) == 2]
	estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)
	hoje = hoje_date.strftime('%d-%m-%Y')
	
	# ESTOQUE NOVOS CABEÇALHOS
	novos_cabecalhos = {}
	for col in estoque_pivot.columns:
		novos_cabecalhos.update({col:f"Estoquexxx{hoje}xxx{col}"})

	estoque_pivot = estoque_pivot.rename(columns=novos_cabecalhos)

	armazens = estoque["armazem"].unique().tolist()
	
	# ESTRUTURA NOVOS CABEÇALHOS
	data_str = data.strftime('%d-%m-%Y')
	estrutura, coluna_insumo = padronizar_cabecalhos_estrutura(codigo,data_str,quant,estrutura)

	# COMBINA O ESTOQUE_PIVOT COM O ESTRUTURA
	simulador = estoque_pivot.merge(
		estrutura,how="outer",
		left_on=f'Estoquexxx{hoje}xxxcodigo',
		right_on=coluna_insumo
	)

	# RESULTADO DO PA/PI PRODUZIDO
	simulador.loc[
		simulador.filter(like=f"Estoquexxx{hoje}xxxcodigo").iloc[:,0] == codigo,
		simulador.filter(like=f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada").columns
	] = quant

	# PREENCHER PRODUTOS QUE VIERAM SOMENTE NA BOM
	produtos_sem_estoque = simulador.loc[simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"].isna(),:]
	if not produtos_sem_estoque.empty:
		# simulador.replace({f"Estoquexxx{hoje}xxxcodigo":{"":nan}},inplace=True)
		simulador.loc[:,f"Estoquexxx{hoje}xxxcodigo"] = simulador[f"Estoquexxx{hoje}xxxcodigo"]\
			.combine_first(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"])
	produtos_sem_estoque = None

	# PEDIDOS
	pedidos = get_pedidos(
		solicitante="simulador",
		engine=engine
	)
	pedidos_filtrados = pedidos.loc[
		pedidos[f"codigo"].isin(simulador[f"Estoquexxx{hoje}xxxcodigo"]),:
	]
	pedidos_pivot = pedidos_filtrados.pivot_table(
		index="codigo", 
		columns="entrega", 
		values="quant",
		aggfunc="sum"
	).reset_index()

	# PEDIDOS NOVOS CABEÇALHOS
	novos_cabecalhos = {}
	for col in pedidos_pivot.columns:
		novos_cabecalhos.update({col:f"Pedidosxxx{col}xxxquant_pedidos"})

	pedidos_pivot = pedidos_pivot.rename(columns=novos_cabecalhos)

	# PEDIDOS MERGE
	simulador = simulador.merge(
		right=pedidos_pivot,how="left",
		left_on=f"Estoquexxx{hoje}xxxcodigo",
		right_on="Pedidosxxxcodigoxxxquant_pedidos"
	).drop(columns=["Pedidosxxxcodigoxxxquant_pedidos"])

	colunas_ordenadas, datas_encontradas = ordenar_colunas_por_data(simulador.columns)
	simulador = simulador[colunas_ordenadas]
	

	# RESULTADO
	simulador.fillna({f"Estoquexxx{hoje}xxxTtl Est":0}, inplace=True)

	simulador_blocos = pd.DataFrame()
	for d in datas_encontradas:
		d_str = d.strftime("%d-%m-%Y")
		colunas_para_somar = [f"Estoquexxx{hoje}xxxTtl Est"]
		bloco_dia = simulador.filter(like=d_str)
		bloco_estoque = bloco_dia.filter(like="Estoque")
		bloco_producao = bloco_dia.filter(like="Produção")
		bloco_pedidos = bloco_dia.filter(like="Pedidos")
		if not bloco_estoque.empty:
			simulador_blocos = pd.concat([simulador_blocos,bloco_estoque], axis=1)
		if not bloco_pedidos.empty:
			colunas_para_somar.append(f"Pedidosxxx{d_str}xxxquant_pedidos")
			simulador_blocos = pd.concat([simulador_blocos,bloco_pedidos], axis=1)
		if not bloco_producao.empty:
			colunas_quant_utilizada = bloco_producao.filter(like="quant_utilizada").columns
			if colunas_quant_utilizada.any():
				colunas_para_somar.append(*colunas_quant_utilizada)
			colunas_quant_utilizada = None
			simulador_blocos = pd.concat([simulador_blocos,bloco_producao], axis=1)

		simulador_blocos[f"Resultadoxxx{d_str}xxxqtd"] = simulador[colunas_para_somar].sum(axis=1).round(5)


		# NEGATIVOS MP EM
		negativos_mp = simulador_blocos.loc[	
			((simulador_blocos[f"Resultadoxxx{d_str}xxxqtd"] < 0) & 
			(simulador_blocos.filter(like="tipo_insumo").iloc[:,0] != 'PI')),:
		]
		if not negativos_mp.empty:
			for _, row in negativos_mp.iterrows():
				cod_negativo = row.filter(like=f'Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo').values[0]
				quant_neg = -row.filter(like=f'Resultadoxxx{d_str}xxxqtd').values[0]
				alternativo_de = simulador_blocos.loc[
					simulador_blocos[f'Produçãoxxx{codigo}_{d_str}_{quant}xxxalternativo_de'] == cod_negativo ,
					:
				]
				if not alternativo_de.empty:
					for _, alt in alternativo_de.sort_values(
						by=f'Produçãoxxx{codigo}_{d_str}_{quant}xxxordem_alt',ascending=True
					).iterrows():
						quant_alt = alt[f"Estoquexxx{hoje}xxxTtl Est"]
						alternativo = alt[f"Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo"]
						if quant_alt > 0:
							if quant_alt >= quant_neg:
								simulador_blocos.loc[
									(simulador_blocos[f"Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo"] == alternativo),
									f"Produçãoxxx{codigo}_{d_str}_{quant}xxxquant_utilizada"
								] -= quant_neg
								simulador_blocos.loc[
									(simulador_blocos[f"Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Produçãoxxx{codigo}_{d_str}_{quant}xxxquant_utilizada"
								] += quant_neg
								break
							elif quant_alt < quant_neg:
								simulador_blocos.loc[
									(simulador_blocos[f"Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo"] == alternativo),
									f"Produçãoxxx{codigo}_{d_str}_{quant}xxxquant_utilizada"
								] = -quant_alt
								simulador_blocos.loc[
									(simulador_blocos[f"Produçãoxxx{codigo}_{d_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Produçãoxxx{codigo}_{d_str}_{quant}xxxquant_utilizada"
								] += quant_alt
								quant_neg -= quant_alt

		simulador_blocos[f"Resultadoxxx{d_str}xxxqtd"] = simulador[colunas_para_somar].sum(axis=1).round(5)
									
		negativos_mp = None
		cod_negativo = None
		quant_neg = None
		alternativo_de = None
		quant_alt = None


		bloco_estoque = None
		bloco_producao = None
		bloco_pedidos = None
		colunas_para_somar = []

	simulador = simulador_blocos
	simulador_blocos = None

	# simulador.loc[:,f'Produçãoxxx{codigo}_{data_str}_{quant}xxxResultado'] = (
	# 	simulador[f"Estoquexxx{hoje}xxxTtl Est"] + 
	# 	simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"]
	# ).round(5)

	

	# DESCRIÇÃO PARA PRODUTOS SEM DESCRIÇÃO
	todos_os_codigos = pd.concat([
		simulador.loc[
			~simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxcodigo_pai"].isna(),
			f"Produçãoxxx{codigo}_{data_str}_{quant}xxxcodigo_pai"
		].rename("todos_os_codigos"), 
		simulador.loc[
			~simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"].isna(),
			f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"
		].rename("todos_os_codigos")
	]).drop_duplicates()
	todos_os_codigos = forma_string_codigos(todos_os_codigos)
	descricao_produtos = get_info_produtos(todos_os_codigos, engine)
	descricao_produtos = dict(zip(descricao_produtos["codigo"],descricao_produtos["descricao"]))
	simulador.loc[:,f"Produçãoxxx{codigo}_{data_str}_{quant}xxxdescricao_pai"] = \
		simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxdescricao_pai"].fillna(
			simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxcodigo_pai"].map(descricao_produtos)
		)
	simulador.loc[:,f"Produçãoxxx{codigo}_{data_str}_{quant}xxxdescricao_insumo"] = \
		simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxdescricao_insumo"].fillna(
			simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"].map(descricao_produtos)
		)
	
	# RESULTADO
	# simulador.fillna({f"Estoquexxx{hoje}xxxTtl Est":0}, inplace=True)
	# simulador.loc[:,f'Produçãoxxx{codigo}_{data_str}_{quant}xxxResultado'] = \
	# 	(simulador[f"Estoquexxx{hoje}xxxTtl Est"] + 
	# 		simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"]).round(5)
	
	# SALVAR NO BANCO DE DADOS
	if not codigo_aleatorio:
		codigo_aleatorio = gerar_codigo_aleatorio_simulador(10)
		request.session["codigo-aleatorio"] = codigo_aleatorio
	sqlite_conn = sqlite3.connect('db.sqlite3')

	simulador.to_sql(name=codigo_aleatorio, con=sqlite_conn, if_exists="replace", index=True)
	
	simulador = simulador.fillna('')

	# CABEÇALHOS
	cat_anterior = ''
	dat_anterior = ''
	cabecalhos = {
		"categoria":[],
		"data":[],
		"campo":[],
	}
	for col in simulador.columns:
		cat, dat, campo = col.split("xxx")
		if cat == cat_anterior:
			cabecalhos["categoria"][len(cabecalhos["categoria"])-1][cat] += 1
		else:
			cabecalhos["categoria"].append({cat:1})
		cat_anterior = cat

		if dat == dat_anterior:
			cabecalhos["data"][len(cabecalhos["data"])-1][dat] += 1
		else:
			cabecalhos["data"].append({dat:1})
		dat_anterior = dat

		cabecalhos["campo"].append({campo:1})


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




@api_view(["POST"])
def altera_simulador_de_producao(request):
	data = request.data
	codigo_aleatorio = data.get("codigo_aleatorio")
	unique = data.get("unique")
	novo_valor = data.get("novo_valor")

	col_name, row_index = unique.split("|")
	row_index = int(row_index)

	conn = sqlite3.connect("db.sqlite3")
	cursor = conn.cursor()

	query = f"""
UPDATE [{codigo_aleatorio}] 
SET [{col_name}] = '{novo_valor}' 
WHERE [index] = {row_index} 
"""
	try:
		cursor.execute(query)
		conn.commit()
		conn.close()
		response = Response({"sucesso": True})
	except Exception as e:
		response = Response({"erro": e})
		
	return response




def adicionar_nova_producao(request):

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

	estrutura["quant_utilizada"] = estrutura["quant_utilizada"].astype(float).map(lambda x: round(x * quant,5))

	# df_recuperado = pd.read_sql("SELECT * FROM pessoas", engine)
	# verificar se já existe produção daquele PA naquele dia, se existir, excluir bloco e adicionar com nova quant

	todos_os_codigos = forma_string_codigos(todos_os_codigos["todos_os_codigos"])

	query_estoque = get_query_estoque_atual()
	estoque = pd.read_sql(text(query_estoque),engine, params={
		"codigos": todos_os_codigos,
	})

	armazens_visiveis = ['11','14','20','80','98','','Ttl Est']
	estoque_pivot = estoque.pivot(index="codigo", columns="armazem", values="quant").fillna(0).reset_index()
	arm_exist = [col for col in armazens_visiveis if col in estoque_pivot.columns]
	estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)
	hoje = datetime.today().strftime('%d-%m-%Y')
	
	novos_cabecalhos = {}
	i=0
	for col in estoque_pivot.columns:
		i += 1
		novos_cabecalhos.update({col:f"{i:04}xxxEstoquexxx{hoje}xxx{col}"})

	estoque_pivot = estoque_pivot.rename(columns=novos_cabecalhos)

	armazens = estoque["armazem"].unique().tolist()
	
	novos_cabecalhos = {}
	data_str = data.strftime('%d-%m-%Y')
	for col in estrutura.columns:
		i += 1
		if col == 'insumo': coluna_insumo = f"{i:04}xxxProduçãoxxx{data_str}xxx{col}"
		novos_cabecalhos.update({col: f"{i:04}xxxProduçãoxxx{data_str}xxx{col}"})

	estrutura = estrutura.rename(columns=novos_cabecalhos)

	simulador = estoque_pivot.merge(
		estrutura,how="left",
		left_on=f'0001xxxEstoquexxx{hoje}xxxcodigo',
		right_on=coluna_insumo
	)

	simulador[f'{i:04}xxxProduçãoxxx{data_str}xxxResultado'] = \
		(simulador.filter(like="Ttl Est").values - simulador.filter(like="quant_utilizada").values).round(5)
	
	negativos = simulador.loc[
		(simulador.filter(like="Resultado").values < 0) & (simulador.filter(like="tipo_insumo").values == 'PI')
		,:
	]

	if not codigo_aleatorio:
		codigo_aleatorio = gerar_codigo_aleatorio_simulador(10)
		request.session["codigo-aleatorio"] = codigo_aleatorio
	sqlite_conn = sqlite3.connect('db.sqlite3')
	simulador.to_sql(name=codigo_aleatorio, con=sqlite_conn, if_exists="replace", index=True)
	
	simulador = simulador.fillna('')

	cat_anterior = ''
	dat_anterior = ''
	cabecalhos = {
		"indice":{},
		"categoria":{},
		"data":{},
		"campo":{},
	}
	for col in simulador.columns:
		i, cat, dat, campo = col.split("xxx")
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




def padronizar_cabecalhos_estrutura(codigo:str,data_str:str,quant, estrutura):
	novos_cabecalhos = {}
	
	for col in estrutura.columns:
		if col == 'insumo': coluna_insumo = f"Produçãoxxx{codigo}_{data_str}_{quant}xxx{col}"
		novos_cabecalhos.update({col: f"Produçãoxxx{codigo}_{data_str}_{quant}xxx{col}"})

	estrutura = estrutura.rename(columns=novos_cabecalhos)

	return estrutura, coluna_insumo




def ordenar_colunas_por_data(colunas):

	datas_extraidas = set()

	def extrair_data(col):
		partes = col.split("xxx")
		if partes[0] in ["Estoque","Pedidos"]:
			parte=pd.to_datetime(partes[1], format="%d-%m-%Y")
		elif partes[0] == "Produção":
			partes2 = partes[1].split("_")
			parte = pd.to_datetime(partes2[1], format="%d-%m-%Y")

		datas_extraidas.add(parte)
		return parte
	colunas_ordenadas = sorted(colunas, key=extrair_data)
	datas_encontradas = sorted(datas_extraidas)
	
	return colunas_ordenadas, datas_encontradas