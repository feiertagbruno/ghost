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
import json
from ghost.queries import get_query_estoque_atual
from ghost.views.estruturas import explode_estrutura, forma_string_codigos, gerar_multiestruturas
from ghost.utils.funcs import (
	get_engine, tratamento_data_referencia, gerar_codigo_aleatorio_simulador,
	get_info_produtos
)
from ghost.views.consultas import get_produzidos_na_data,get_pedidos

def simulador_de_producao(request):
	if request.session.get("codigo-aleatorio"):
		del(request.session["codigo-aleatorio"])
	
	query_tabelas_salvas = "SELECT name FROM sqlite_master WHERE type = 'table' AND name like 'simulacao_%'"
	sqlite_conn = sqlite3.connect("db.sqlite3")

	tabelas = []
	tabelas_existentes = pd.read_sql(query_tabelas_salvas, sqlite_conn)
	if not tabelas_existentes.empty:
		lista_tabelas = tabelas_existentes["name"].to_list()

		for tb in lista_tabelas:
			tabelas.append(tb.split("_",1)[1])

	context = {
		"caller":"inicial",
		"tabelas":tabelas if tabelas else None,
	}
	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html", context)


def adicionar_producao(request):
	if not request.method == "POST":
		return redirect(reverse("ghost:simulador-de-producao"))
	
	tabela_salva = request.POST.get("tabela-salva")

	if tabela_salva:
		return adicionar_nova_producao(request, tabela_salva)
	
	codigo_aleatorio = request.session.get("codigo-aleatorio")

	engine = get_engine()
	
	codigo = request.POST.get("codigo-produto")
	data = request.POST.get("data-producao")
	quant = request.POST.get("quantidade")
	explode_pis = True if request.POST.get("explode-pis", None) else False
	abre_detalhamento = False if request.POST.get("abre-detalhamento", None) else True
	
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
		abre_todos_os_PIs=explode_pis,
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
			quant_produzida = produzidos.loc[produzidos["codigo"] == codigo, "quant"].values[0]
			quant -= quant_produzida
	
	if quant <= 0:
		messages.error(request,f"A quantidade produzida neste dia foi de {int(quant_produzida)}. "
				  "Só é possivel simular uma quantidade maior do que esta.")
		return redirect(reverse("ghost:simulador-de-producao"))
		

	estrutura["quant_utilizada"] = estrutura["quant_utilizada"].astype(float).map(lambda x: -round(x * quant,5))
	todos_os_codigos = pd.concat([
		todos_os_codigos, 
		pd.DataFrame({"todos_os_codigos":[codigo]})
	])
	todos_os_codigos = forma_string_codigos(todos_os_codigos["todos_os_codigos"].drop_duplicates())

	query_estoque = get_query_estoque_atual()
	estoque = pd.read_sql(text(query_estoque),engine, params={
		"codigos": todos_os_codigos,
	})

	# FORMA O ESTOQUE_PIVOT
	estoque_pivot = estoque.pivot(index=["codigo","tipo","descricao","origem"], columns="armazem", values="quant").reset_index()
	arm_exist = [col for col in estoque_pivot.columns if len(col) == 2]
	estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)
	hoje = hoje_date.strftime('%d-%m-%Y')
	
	# ESTOQUE NOVOS CABEÇALHOS
	estoque_pivot = padronizar_cabecalhos_estoque(estoque_pivot, hoje)
	
	# ESTRUTURA NOVOS CABEÇALHOS
	data_str = data.strftime('%d-%m-%Y')
	estrutura, coluna_insumo = padronizar_cabecalhos_estrutura(codigo,data_str,quant,estrutura)

	# COMBINA O ESTOQUE_PIVOT COM O ESTRUTURA
	simulador = estoque_pivot.merge(
		estrutura,how="outer",
		left_on=f'Estoquexxx{hoje}xxxcodigo',
		right_on=coluna_insumo
	)
	estoque_pivot = None

	# RESULTADO DO PA/PI PRODUZIDO
	simulador = resultado_pi_pa_produzido(simulador,hoje,codigo,data_str,quant)

	# PREENCHER PRODUTOS QUE VIERAM SOMENTE NA BOM
	simulador = preencher_produtos_sem_estoque(
		simulador, codigo, data_str, quant, hoje
	)

	# PEDIDOS
	pedidos_pivot = get_pedidos_pivot(
		engine=engine,
		coluna_codigos=simulador[f"Estoquexxx{hoje}xxxcodigo"]
	)

	# PEDIDOS NOVOS CABEÇALHOS
	pedidos_pivot = padronizar_cabecalhos_pedidos(pedidos_pivot)

	# PEDIDOS MERGE
	simulador = simulador.merge(
		right=pedidos_pivot,how="left",
		left_on=f"Estoquexxx{hoje}xxxcodigo",
		right_on="Pedidosxxxcodigoxxxquant_pedidos"
	).drop(columns=["Pedidosxxxcodigoxxxquant_pedidos"])

	colunas_ordenadas, datas_encontradas = ordenar_colunas_por_data(simulador.columns)
	simulador = simulador[colunas_ordenadas]
	colunas_ordenadas = None

	# DESCRIÇÃO PARA PRODUTOS SEM DESCRIÇÃO
	simulador = descricao_para_produtos_sem_descricao(simulador,hoje,codigo,data_str,quant,engine)

	# RESULTADO
	simulador.fillna({f"Estoquexxx{hoje}xxxTtl Est":0}, inplace=True)

	simulador_blocos = pd.DataFrame()
	col_resultado_anterior = f"Estoquexxx{hoje}xxxTtl Est"
	for d in datas_encontradas:
		d_str = d.strftime("%d-%m-%Y")
		colunas_para_somar = [col_resultado_anterior]
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
				colunas_para_somar.extend(colunas_quant_utilizada)
			colunas_quant_utilizada = None
			simulador_blocos = pd.concat([simulador_blocos,bloco_producao], axis=1)


		simulador_blocos[f"Resultadoxxx{d_str}xxxqtd"] = simulador_blocos[colunas_para_somar].sum(axis=1).round(5)
		col_resultado_anterior = f"Resultadoxxx{d_str}xxxqtd"

		bloco_estoque = None
		bloco_producao = None
		bloco_pedidos = None
		colunas_para_somar = []

	simulador = simulador_blocos
	simulador_blocos = None

	# NEGATIVOS MP EM
	simulador = verificar_alternativos_dos_itens_negativos(simulador, data_str, hoje, codigo, quant)
	
	# ADICIONAR EXCLUSIVIDADE
	simulador.insert(0,f"-xxx{hoje}xxxExclusividade","EXCLUSIVO")

	# SALVAR NO BANCO DE DADOS
	request = salvar_dataframe_no_bd(request,simulador,"simudraft",codigo_aleatorio)
	
	simulador = simulador.fillna('')

	# CABEÇALHOS
	cabecalhos, rows = get_cabecalhos_e_rows_simulador_de_producao(
		simulador,hoje, data_str, max(datas_encontradas).strftime("%d-%m-%Y"), abre_detalhamento
	)

	colunas_fixas = get_colunas_fixas(hoje)	
	campos_alteraveis = get_campos_alteraveis()

	context = {
		"caller":"adicionar_producao",
		"cabecalhos":cabecalhos,
		"rows":rows,
		"codigo_aleatorio": codigo_aleatorio,
		"colunas_fixas": colunas_fixas,
		"campos_alteraveis": campos_alteraveis,
		"data_estoque": hoje,
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
		"caller": "reprocessar_tabela",
	}

	return render(request, "ghost/simuladordeproducao/tabela_simulador.html",context)




@api_view(["POST"])
def altera_simulador_de_producao(request):
	data = request.data
	codigo_aleatorio = data.get("codigo_aleatorio")
	unique = data.get("unique")
	novo_valor = data.get("novo_valor")

	try: 
		novo_valor = float(novo_valor)
	except:
		...

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




def adicionar_nova_producao(request, tabela_salva):

	tabela_salva = f"simulacao_{tabela_salva.strip()}"
	engine = get_engine()
	codigo_aleatorio = request.session.get("codigo-aleatorio")
	codigo = request.POST.get("codigo-produto")
	data = request.POST.get("data-producao")
	quant = request.POST.get("quantidade")
	explode_pis = True if request.POST.get("explode-pis", None) else False
	abre_detalhamento = False if request.POST.get("abre-detalhamento", None) else True

	
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
		abre_todos_os_PIs=explode_pis,
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
			quant_produzida = produzidos.loc[produzidos["codigo"] == codigo, "quant"].values[0]
			quant -= quant_produzida
	
	if quant <= 0:
		messages.error(request,f"A quantidade produzida neste dia foi de {int(quant_produzida)}. "
				  "Só é possivel simular uma quantidade maior do que esta.")
		return redirect(reverse("ghost:simulador-de-producao"))
	
	# PEGAR A TABELA SALVA NO BANCO
	sqlite_conn = sqlite3.connect('db.sqlite3')
	simulador = pd.read_sql(f"SELECT * FROM [{tabela_salva}]",sqlite_conn).drop(columns="index")
	sqlite_conn.close()

	data_str = data.strftime('%d-%m-%Y')


	# VERIFICAR SE A PRODUÇÃO JÁ EXISTE NO SIMULADOR
	verif_producao = simulador.filter(like=f"Produçãoxxx{codigo}_{data_str}")
	if not verif_producao.empty:
		simulador.drop(columns=verif_producao.columns, inplace=True)
	verif_producao = None

	# DATA ESTOQUE
	data_estoque = simulador.filter(like="Estoque").filter(like="codigo").columns[0].split("xxx")[1]

	# QUANT_UTILIZADA
	estrutura["quant_utilizada"] = estrutura["quant_utilizada"].astype(float).map(lambda x: -round(x * quant,5))

	# ADICIONAR EXCLUSIVIDADE

	def extrair_produtos_ja_adicionados(simulador):
		produtos_ja_adicionados = set()
		for col in simulador.filter(like="Produçãoxxx").columns:
			produtos_ja_adicionados.add(col.split("xxx")[1].split("_")[0])
		return produtos_ja_adicionados
	
	produtos_ja_adicionados = extrair_produtos_ja_adicionados(simulador)
	if codigo not in produtos_ja_adicionados:
		simulador.loc[simulador[f"Estoquexxx{data_estoque}xxxcodigo"].isin(estrutura["insumo"]),f"-xxx{data_estoque}xxxExclusividade"] = "COMUM"


	todos_os_codigos = pd.concat([
		todos_os_codigos, 
		pd.DataFrame({"todos_os_codigos":[codigo]})
	])
	todos_os_codigos = todos_os_codigos.drop_duplicates("todos_os_codigos")
	todos_os_codigos = todos_os_codigos.loc[
		~todos_os_codigos["todos_os_codigos"].isin(simulador[f"Estoquexxx{data_estoque}xxxcodigo"]),
		"todos_os_codigos"
	]

	# ESTRUTURA NOVOS CABEÇALHOS
	estrutura, coluna_insumo = padronizar_cabecalhos_estrutura(codigo,data_str,quant,estrutura)


	if not todos_os_codigos.empty:

		todos_os_codigos = forma_string_codigos(todos_os_codigos)

		query_estoque = get_query_estoque_atual()
		estoque = pd.read_sql(text(query_estoque),engine, params={
			"codigos": todos_os_codigos,
		})

		
		# FORMA O ESTOQUE_PIVOT
		estoque_pivot = estoque.pivot(index=["codigo","tipo","descricao","origem"], columns="armazem", values="quant").reset_index()
		arm_exist = [col for col in estoque_pivot.columns if len(col) == 2]
		estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)
		
		# ESTOQUE NOVOS CABEÇALHOS
		novos_cabecalhos = {}
		for col in estoque_pivot.columns:
			novos_cabecalhos.update({col:f"Estoquexxx{data_estoque}xxx{col}"})

		estoque_pivot = estoque_pivot.rename(columns=novos_cabecalhos)

		simulador = pd.concat([simulador, estoque_pivot])
	

	# COMBINA O ESTOQUE_PIVOT COM O ESTRUTURA
	simulador = simulador.merge(
		estrutura,how="outer",
		left_on=f'Estoquexxx{data_estoque}xxxcodigo',
		right_on=coluna_insumo
	)

	# RESULTADO DO PA/PI PRODUZIDO
	simulador = resultado_pi_pa_produzido(simulador,data_estoque,codigo,data_str,quant)

	# PREENCHER PRODUTOS QUE VIERAM SOMENTE NA BOM
	simulador = preencher_produtos_sem_estoque(
		simulador, codigo, data_str, quant, data_estoque
	)


	# ORDENAR COLUNAS POR DATA
	colunas_ordenadas, datas_encontradas = ordenar_colunas_por_data(simulador.columns)
	simulador = simulador[colunas_ordenadas]
	

	# DESCRIÇÃO PARA PRODUTOS SEM DESCRIÇÃO
	simulador = descricao_para_produtos_sem_descricao(simulador,data_estoque,codigo,data_str,quant,engine)

	# RESULTADO
	simulador.fillna({f"Estoquexxx{data_estoque}xxxTtl Est":0}, inplace=True)

	simulador_blocos = pd.DataFrame()
	col_resultado_anterior = f"Estoquexxx{data_estoque}xxxTtl Est"
	for d in datas_encontradas:
		d_str = d.strftime("%d-%m-%Y")
		colunas_para_somar = [col_resultado_anterior]
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
				colunas_para_somar.extend(colunas_quant_utilizada)
			colunas_quant_utilizada = None
			simulador_blocos = pd.concat([simulador_blocos,bloco_producao], axis=1)

		simulador_blocos[f"Resultadoxxx{d_str}xxxqtd"] = simulador_blocos[colunas_para_somar].sum(axis=1).round(5)
		col_resultado_anterior = f"Resultadoxxx{d_str}xxxqtd"

		bloco_estoque = None
		bloco_producao = None
		bloco_pedidos = None
		colunas_para_somar = []


	simulador_blocos.insert(0,f"-xxx{data_estoque}xxxExclusividade",simulador[f"-xxx{data_estoque}xxxExclusividade"])
	simulador = simulador_blocos
	simulador_blocos = None

	# NEGATIVOS MP EM
	simulador = verificar_alternativos_dos_itens_negativos(simulador, data_str, data_estoque, codigo, quant)

	# EXCLUSIVO 2
	simulador.fillna({f"-xxx{data_estoque}xxxExclusividade":"EXCLUSIVO"}, inplace=True)	
	
	# SALVAR NO BANCO DE DADOS
	request = salvar_dataframe_no_bd(
		request=request,
		df=simulador,
		inicial_tabela="simudraft",
		codigo_aleatorio=codigo_aleatorio
	)
	
	simulador = simulador.fillna('')

	# CABEÇALHOS
	cabecalhos, rows = get_cabecalhos_e_rows_simulador_de_producao(
		simulador, data_estoque, data_str, max(datas_encontradas).strftime("%d-%m-%Y"), abre_detalhamento
	)

	colunas_fixas = get_colunas_fixas(data_estoque)
	campos_alteraveis = get_campos_alteraveis()

	context = {
		"caller":"adicionar_nova_producao",
		"cabecalhos":cabecalhos,
		"rows":rows,
		"codigo_aleatorio": codigo_aleatorio,
		"tabela_salva":tabela_salva.split("_",1)[1],
		"colunas_fixas": colunas_fixas,
		"campos_alteraveis": campos_alteraveis,
		"data_str": data_str,
		"data_estoque": data_estoque,
		"data_str_nav": data.strftime("%Y-%m-%d"),
	}

	# simulador.to_excel("a.xlsx")
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
		if partes[0] in ["Estoque","Pedidos","Resultado"]:
			parte=pd.to_datetime(partes[1], format="%d-%m-%Y")
		elif partes[0] == "Produção":
			partes2 = partes[1].split("_")
			parte = pd.to_datetime(partes2[1], format="%d-%m-%Y")
		elif partes[2] == "Exclusividade":
			parte=pd.to_datetime(partes[1], format="%d-%m-%Y")

		datas_extraidas.add(parte.date())
		return parte
	colunas_ordenadas = sorted(colunas, key=extrair_data)
	datas_encontradas = sorted(datas_extraidas)
	
	return colunas_ordenadas, datas_encontradas




@api_view(["POST"])
def salvar_simulacao(request):

	body = request.data
	codigo_aleatorio = body.get("codigo_aleatorio")
	nome_da_simulacao = body.get("nome_da_simulacao")

	nome_da_simulacao = f"simulacao_{nome_da_simulacao.strip()}"

	query_verificacao = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{nome_da_simulacao}'"

	query = f"CREATE TABLE [{nome_da_simulacao}] as SELECT * FROM [{codigo_aleatorio}]"

	try:
		sqlite_conn = sqlite3.connect('db.sqlite3')
		cursor = sqlite_conn.cursor()

		# VERIFICAR SE TABELA EXISTE
		cursor.execute(query_verificacao)
		if cursor.fetchone() is not None:
			cursor.execute(f"DROP TABLE [{nome_da_simulacao}]")

		cursor.execute(query)
		sqlite_conn.commit()
		response = {"sucesso": True}
	except Exception as e:
		response = {"erro":str(e)}

	sqlite_conn.close()

	return Response(response)




def get_colunas_fixas(data_str):
	return [
		f"-xxx{data_str}xxxExclusividade",
		f"Estoquexxx{data_str}xxxcodigo",
		f"Estoquexxx{data_str}xxxtipo",
		"Exclusividade",
		"codigo","tipo"
	]

def get_campos_alteraveis():
	return json.dumps([
		"Ttl Est","quant_utilizada","quant_pedidos"
	])




def trazer_simulacao(request):

	abre_detalhamento = False if request.COOKIES.get("abre_detalhamento_simulador_de_producao") == "true" else True

	tabela_salva = request.POST.get("simulacoes")
	sqlite_conn = sqlite3.connect("db.sqlite3")

	if not tabela_salva:
		return redirect(reverse("ghost:simulador-de-producao"))

	query = f"SELECT * FROM [simulacao_{tabela_salva}]"

	codigo_aleatorio = gerar_codigo_aleatorio_simulador(10)

	simulador = pd.read_sql(query, sqlite_conn)
	if simulador.empty:
		messages.error(request,"Problemas ao carregar esta tabela")
		return redirect(reverse("ghost:simulador-de-producao"))
	
	simulador.drop(columns=["index"],inplace=True)
	
	_, datas_encontradas = ordenar_colunas_por_data(simulador.filter(like="Produçãoxxx").columns)
	data_str = max(datas_encontradas).strftime("%d-%m-%Y")

	simulador = simulador.fillna('')

	# DATA ESTOQUE
	data_estoque = simulador.filter(like="Estoque").filter(like="codigo").columns[0].split("xxx")[1]

	cabecalhos, rows = get_cabecalhos_e_rows_simulador_de_producao(
		simulador, data_estoque, data_str, data_str,abre_detalhamento
	)
	colunas_fixas = get_colunas_fixas(data_estoque)
	campos_alteraveis = get_campos_alteraveis()

	context = {
		"caller":"trazer_simulacao",
		"cabecalhos":cabecalhos,
		"rows":rows,
		"codigo_aleatorio": codigo_aleatorio,
		"tabela_salva":tabela_salva,
		"colunas_fixas": colunas_fixas,
		"campos_alteraveis": campos_alteraveis,
		"data_str": data_str,
		"data_estoque": data_estoque,
	}

	return render(request, "ghost/simuladordeproducao/simuladordeproducao.html", context)






def get_cabecalhos_e_rows_simulador_de_producao(
		simulador:pd.DataFrame, data_estoque:str, data_str:str, maior_data:str, reduz_campos:bool = True
):
	# CABEÇALHOS
	cat_anterior = ''
	dat_anterior = ''
	cabecalhos = {
		"categoria":[],
		"data":[],
		"campo":[],
	}
	
	if reduz_campos:
		simulador = simulador.loc[
			# (
				(simulador[f"Estoquexxx{data_estoque}xxxtipo"].isin(["PA"]))
			# | (simulador.filter(like=data_str).filter(like="Resultado").iloc[:,0] < 0) |
			# (simulador.filter(like=maior_data).filter(like="Resultado").iloc[:,0] < 0))
			,:
		]
	for col in simulador.columns:
		cat, dat, campo = col.split("xxx")

		if cat != "Produção" or data_str in dat or reduz_campos == False:

			if cat == cat_anterior:
				cabecalhos["categoria"][-1][cat] = (cabecalhos["categoria"][-1][cat][0] + 1, col)
			else:
				cabecalhos["categoria"].append({cat: (1, col)})
			cat_anterior = cat

			if dat == dat_anterior:
				cabecalhos["data"][-1][dat] = (cabecalhos["data"][-1][dat][0] + 1, col)
			else:
				cabecalhos["data"].append({dat: (1, col)})
			dat_anterior = dat

			cabecalhos["campo"].append({campo: (1, col)})

	rows = []
	for i, row in simulador.iterrows():
		if reduz_campos:
			colunas_filtradas = [col for col in simulador.columns if "Produção" not in col or data_str in col]
		else:
			colunas_filtradas = simulador.columns
		row_data = row[colunas_filtradas].to_dict()
		row_data["index"] = i
		rows.append(row_data)


	return cabecalhos, rows




def resultado_pi_pa_produzido(simulador, data_estoque, codigo, data_str, quant):
	if simulador.loc[
		simulador[f"Estoquexxx{data_estoque}xxxcodigo"] == codigo,
		f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
	].empty:
		simulador = pd.concat([
			simulador,
			pd.DataFrame({f"Estoquexxx{data_estoque}xxxcodigo":[codigo]})
		]).sort_values(by=f"Estoquexxx{data_estoque}xxxcodigo",ascending=True)
	simulador.loc[
		simulador[f"Estoquexxx{data_estoque}xxxcodigo"] == codigo,
		f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
	] = quant
	return simulador




def descricao_para_produtos_sem_descricao(simulador,data_estoque,codigo,data_str,quant,engine):
	todos_os_codigos = simulador.loc[
			(simulador[f"Estoquexxx{data_estoque}xxxdescricao"].isna()),
			f"Estoquexxx{data_estoque}xxxcodigo"
		].rename("todos_os_codigos").drop_duplicates()
	if not todos_os_codigos.empty:
		todos_os_codigos = forma_string_codigos(todos_os_codigos)
		info_produtos = get_info_produtos(todos_os_codigos, engine)
		
		simulador = simulador.merge(info_produtos,how="left",left_on=f"Estoquexxx{data_estoque}xxxcodigo",right_on="codigo")

		simulador = simulador.fillna({
			f"Estoquexxx{data_estoque}xxxdescricao": simulador["descricao_produto"],
			f"Estoquexxx{data_estoque}xxxtipo": simulador["tipo_produto"],
			f"Estoquexxx{data_estoque}xxxorigem": simulador["origem_produto"]
		}).drop(columns=["descricao_produto","tipo_produto","origem_produto"])
	info_produtos = None
	return simulador




def verificar_alternativos_dos_itens_negativos(simulador, data_str, data_estoque, codigo, quant):
	
	colunas_resultado_e_estoque = pd.concat([
		simulador.filter(like="Ttl Est"),
		simulador.filter(like="Resultado")
	],axis=1).columns

	col_resultado_anterior = ""
	for col in colunas_resultado_e_estoque:
		if data_str in col:
			break
		col_resultado_anterior = col
	if col_resultado_anterior == "":
		col_resultado_anterior = f"Estoquexxx{data_str}xxxTtl Est"

	negativos_mp = simulador.loc[	
		((simulador[f"Resultadoxxx{data_str}xxxqtd"] < 0) & 
		(~simulador[f"Estoquexxx{data_estoque}xxxtipo"].isin(['PI','PA']))),:
	]
	if not negativos_mp.empty:
		for _, row in negativos_mp.iterrows():
			cod_negativo = row[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"]
			quant_neg = -row[f'Resultadoxxx{data_str}xxxqtd']
			alternativo_de = simulador.loc[
				simulador[f'Produçãoxxx{codigo}_{data_str}_{quant}xxxalternativo_de'] == cod_negativo ,
				:
			]
			if not alternativo_de.empty:
				for _, alt in alternativo_de.sort_values(
					by=f'Produçãoxxx{codigo}_{data_str}_{quant}xxxordem_alt',ascending=True
				).iterrows():
					quant_alt = alt[col_resultado_anterior]
					alternativo = alt[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"]
					if quant_alt > 0:
						if quant_alt >= quant_neg:

							#quant_utilizada
							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo),
								f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
							] = simulador.loc[
									(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo),
									f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
								].fillna(0) - quant_neg
							
							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
								f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
							] = simulador.loc[
									(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
								].fillna(0) + quant_neg
							
							# Resultado
							simulador.loc[
								simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo,
								f"Resultadoxxx{data_str}xxxqtd"
							] = simulador.loc[
									simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo,
									f"Resultadoxxx{data_str}xxxqtd"
								].fillna(0) - quant_neg
							
							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
								f"Resultadoxxx{data_str}xxxqtd"
							] = simulador.loc[
									(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Resultadoxxx{data_str}xxxqtd"
								].fillna(0) + quant_neg
							
							break

						elif quant_alt < quant_neg:

							# quant_utilizada
							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo),
								f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
							] = -quant_alt

							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
								f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
							] = simulador.loc[
									(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Produçãoxxx{codigo}_{data_str}_{quant}xxxquant_utilizada"
								].fillna(0) + quant_alt
							
							# Resultado
							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == alternativo),
								f"Resultadoxxx{data_str}xxxqtd"
							] = 0

							simulador.loc[
								(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
								f"Resultadoxxx{data_str}xxxqtd"
							] = simulador.loc[
									(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"] == cod_negativo),
									f"Resultadoxxx{data_str}xxxqtd"
								].fillna(0) + quant_alt
							
							quant_neg -= quant_alt

		negativos_mp = None
		cod_negativo = None
		quant_neg = None
		alternativo_de = None
		quant_alt = None
	return simulador




def phase_out(request):
	context = {
		"caller": "inicial",
	}
	return render(request,"ghost/simuladordeproducao/phase_out.html", context)




def get_cabecalhos_e_rows_dataframe(
		df:pd.DataFrame, reduz_campos:bool = True
):

	cabecalhos = []
	cabecalhos_anteriores = []
	size = len(df.columns[0].split("xxx"))
	for i in range(size):
		cabecalhos.append([])
		cabecalhos_anteriores.append([])

	for col in df.columns:
		for i,subcol in enumerate(col.split("xxx")):
			if subcol == cabecalhos_anteriores[i]:
				cabecalhos[i][-1][subcol] = (cabecalhos[i][-1][subcol][0] + 1, col)
			else:
				cabecalhos[i].append({subcol:(1,col)})
			cabecalhos_anteriores[i] = subcol


	rows = []
	for i, row in df.iterrows():
		row_data = row.to_dict()
		row_data["index"] = i
		rows.append(row_data)


	return cabecalhos, rows




def get_cabecalhos_e_rows_phaseout(
		df:pd.DataFrame, reduz_campos:bool = True
):

	cabecalhos = []
	cabecalhos_anteriores = []
	size = len(df.columns[0].split("xxx"))
	for i in range(size):
		cabecalhos.append([])
		cabecalhos_anteriores.append([])

	for col in df.columns:
		for i,subcol in enumerate(col.split("xxx")):
			if subcol == cabecalhos_anteriores[i]:
				cabecalhos[i][-1][subcol] = (cabecalhos[i][-1][subcol][0] + 1, col)
			else:
				cabecalhos[i].append({subcol:(1,col)})
			cabecalhos_anteriores[i] = subcol

	rows = []
	insumo_anterior = ""
	ult_indice = 0
	for i, row in df.iterrows():
		row_data = row.to_dict()
		if row["insumo"] != insumo_anterior:
			rows.append((row_data,1))
			ult_indice = len(rows) - 1
		else:
			rows[ult_indice] = (rows[ult_indice][0],rows[ult_indice][1] + 1)
			row_data.pop("insumo")
			rows.append((row_data,1))
		insumo_anterior = row["insumo"]
		


	return cabecalhos, rows




def carregar_estruturas_phase_out(request):

	if request.method != "POST": return redirect(reverse("ghost:phase-out"))

	produtos = request.POST.get("codigos-produtos")

	if not produtos: return redirect(reverse("ghost:ghost"))

	engine = get_engine()
	codigo_aleatorio = request.session.get("codigo-aleatorio")

	produtos = produtos.split("\r\n")
	produtos_filtrados = [item for item in produtos if item != ""]

	data_referencia = datetime.today().date()
	data_str = data_referencia.strftime("%d-%m-%Y")
	quant = 1

	estruturas: pd.DataFrame
	request, estruturas, _ = gerar_multiestruturas(
		request= request,
		produtos=produtos_filtrados,
		data_referencia=data_referencia,
		engine=engine,
		caller="phase_out"
	)

	estruturas = preencher_qtds_itens_alternativos_phaseout(estruturas)

	estruturas = estruturas.sort_values(by="insumo",ascending=True)
	estruturas = estruturas[["insumo","alternativo_de","codigo_original","quant_utilizada","Exclusividade"]]

	estruturas["Status"] = "CORRENTE"

	# estruturas, coluna_insumo_estru = padronizar_cabecalhos_estrutura("Produtos Correntes", data_str,quant, estruturas)


	# # ESTOQUE
	# todos_os_codigos = forma_string_codigos(estruturas[coluna_insumo_estru].drop_duplicates())

	# query_estoque = get_query_estoque_atual()
	# estoque = pd.read_sql(text(query_estoque),engine, params={
	# 	"codigos": todos_os_codigos,
	# })

	# # FORMA O ESTOQUE_PIVOT
	# estoque_pivot = estoque.pivot(index=["codigo","tipo","descricao","origem"], columns="armazem", values="quant").reset_index()
	# arm_exist = [col for col in estoque_pivot.columns if len(col) == 2]
	# estoque_pivot["Ttl Est"] = estoque_pivot[arm_exist].sum(axis=1)

	# estoque_pivot = padronizar_cabecalhos_estoque(estoque_pivot, data_str)

	# estruturas = estruturas.merge(
	# 	estoque_pivot,how="left",
	# 	left_on=coluna_insumo_estru,
	# 	right_on=f"Estoquexxx{data_str}xxxcodigo"
	# )

	# # PEDIDOS
	# pedidos_pivot = get_pedidos_pivot(
	# 	engine=engine,
	# 	coluna_codigos=estruturas[coluna_insumo_estru],
	# 	abre_datas=False
	# )
	# pedidos_pivot = padronizar_cabecalhos_pedidos(pedidos_pivot)

	# estruturas = estruturas.merge(
	# 	pedidos_pivot,how="left",
	# 	left_on=coluna_insumo_estru,
	# 	right_on=f"Pedidosxxxcodigoxxxquant_pedidos"
	# )
	# # PEDIDOS fim

	# SALVAR NO BD
	request = salvar_dataframe_no_bd(
		request=request,
		df=estruturas,
		inicial_tabela="phaseout",
		codigo_aleatorio=codigo_aleatorio
	)
	# SALVAR NO BD fim

	estruturas = estruturas.fillna("")

	# cabecalhos, rows = get_cabecalhos_e_rows_dataframe(estruturas)
	cabecalhos, rows = get_cabecalhos_e_rows_phaseout(estruturas)

	context = {
		"caller":"carregar_estruturas",
		"cabecalhos":cabecalhos,
		"rows":rows
	}

	return render(request, "ghost/simuladordeproducao/phase_out.html", context)




def carregar_phase_out(request):

	if request.method != "POST": return redirect(reverse("ghost:phase-out"))

	produtos = request.POST.get("codigos-produtos")

	if not produtos: return redirect(reverse("ghost:phase-out"))

	engine = get_engine()
	codigo_aleatorio = request.session.get("codigo-aleatorio")

	if not codigo_aleatorio: return redirect(reverse("ghost:phase-out"))

	produtos = produtos.split("\r\n")
	produtos_filtrados = [item for item in produtos if item != ""]

	data_referencia = datetime.today().date()
	data_str = data_referencia.strftime("%d-%m-%Y")
	quant = 1

	# PEGAR A TABELA SALVA NO BANCO
	sqlite_conn = sqlite3.connect('db.sqlite3')
	estruturas = pd.read_sql(f"SELECT * FROM [{codigo_aleatorio}]",sqlite_conn).drop(columns="index")
	sqlite_conn.close()

	phouts: pd.DataFrame
	request, phouts, _ = gerar_multiestruturas(
		request= request,
		produtos=produtos_filtrados,
		data_referencia=data_referencia,
		engine=engine,
		caller="phase_out"
	)

	




	estruturas = estruturas.fillna("")

	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(estruturas)

	context = {
		"caller":"carregar_phase_out",
		"cabecalhos":cabecalhos,
		"rows":rows
	}

	return render(request, "ghost/simuladordeproducao/phase_out.html", context)




def preencher_produtos_sem_estoque(
		simulador, codigo, data_str, quant, data_estoque
):
	produtos_sem_estoque = simulador.loc[simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"].isna(),:]
	if not produtos_sem_estoque.empty:
		# simulador.replace({f"Estoquexxx{hoje}xxxcodigo":{"":nan}},inplace=True)
		simulador.loc[:,f"Estoquexxx{data_estoque}xxxcodigo"] = simulador[f"Estoquexxx{data_estoque}xxxcodigo"]\
			.combine_first(simulador[f"Produçãoxxx{codigo}_{data_str}_{quant}xxxinsumo"])

	return simulador




def padronizar_cabecalhos_estoque(estoque_pivot, data_estoque):
	novos_cabecalhos = {}
	for col in estoque_pivot.columns:
		novos_cabecalhos.update({col:f"Estoquexxx{data_estoque}xxx{col}"})

	estoque_pivot = estoque_pivot.rename(columns=novos_cabecalhos)
	return estoque_pivot




def padronizar_cabecalhos_pedidos(pedidos_pivot):
	novos_cabecalhos = {}
	for col in pedidos_pivot.columns:
		novos_cabecalhos.update({col:f"Pedidosxxx{col}xxxquant_pedidos"})

	pedidos_pivot = pedidos_pivot.rename(columns=novos_cabecalhos)
	return pedidos_pivot




def get_pedidos_pivot(engine,coluna_codigos,abre_datas = True):
	pedidos = get_pedidos(
		solicitante="simulador",
		engine=engine
	)
	pedidos_filtrados = pedidos.loc[
		pedidos[f"codigo"].isin(coluna_codigos.drop_duplicates()),:
	]
	if abre_datas:
		pedidos_pivot = pedidos_filtrados.pivot_table(
			index="codigo", 
			columns="entrega", 
			values="quant",
			aggfunc="sum"
		).reset_index()
	else:
		pedidos_pivot = pedidos_filtrados.pivot_table(
			index="codigo",
			values="quant",
			aggfunc="sum"
		).reset_index()
	return pedidos_pivot




def salvar_dataframe_no_bd(request,df,inicial_tabela,codigo_aleatorio=None):
	if not codigo_aleatorio:
		codigo_aleatorio = gerar_codigo_aleatorio_simulador(10,inicial_tabela)
		request.session["codigo-aleatorio"] = codigo_aleatorio
	print(codigo_aleatorio)
	sqlite_conn = sqlite3.connect('db.sqlite3')
	df.to_sql(name=codigo_aleatorio, con=sqlite_conn, if_exists="replace", index=True)
	sqlite_conn.close()
	return request




def preencher_qtds_itens_alternativos_phaseout(df:pd.DataFrame):
	df["quant_utilizada"] = df["quant_utilizada"].fillna(
		df.merge(df,how="left",left_on=["alternativo_de","codigo_original"],right_on=["insumo","codigo_original"],suffixes=("","_alt"))["quant_utilizada_alt"]
	)
	return df