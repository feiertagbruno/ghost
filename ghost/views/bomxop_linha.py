from django.shortcuts import render
from django.contrib import messages

from pandas import read_sql, DataFrame, concat
from sqlalchemy import text
from re import search

from ghost.utils.funcs import tratamento_data_referencia, forma_string_para_query, get_cabecalhos_e_rows_dataframe
from ghost.queries import (
	get_query_numeros_op_por_periodo_somente_PA
)
from ghost.utils.funcs import get_engine
from ghost.views.explop import explode_estrutura_pela_op

def bomxop_linha_do_tempo(request):
	return render(request, "ghost/BOMxOP/bomxop_linha.html", {"caller":"bomxop_linha"})

def bomxop_linha_do_tempo_post(request):

	if request.method != "POST":
		return render(request, "ghost/BOMxOP/bomxop_linha.html")

	data_inicial = request.POST.get("data-inicial")
	data_final = request.POST.get("data-final")
	if not data_inicial or not data_final:
		messages.info(request, "Datas Inválidas")
		return render(request, "ghost/BOMxOP/bomxop_linha.html")
	
	data_inicial = tratamento_data_referencia(data_inicial)
	data_final = tratamento_data_referencia(data_final)

	traz_prod = request.POST.get("traz-produzidos")
	
	if traz_prod != "on":
		codigos_pre = request.POST.get("codigos")
		if not codigos_pre:
			messages.info(request, "Códigos Inválidos")
			return render(request, "ghost/BOMxOP/bomxop_linha.html")
		codigos_pre = codigos_pre.split("\r\n")
		codigos = forma_string_para_query(list({str(c).upper().strip() for c in codigos_pre if c}))
	else:
		codigos = None
	
	engine = get_engine()

	query_ops = get_query_numeros_op_por_periodo_somente_PA()
	ops = read_sql(text(query_ops), engine, params={
		"data_inicial": data_inicial,
		"data_final": data_final,
		"codigos": codigos,
		"tipos_apontamento": '200'
	})
	query_ops = None

	if ops.empty:
		messages.info(request, "Sem OPs finalizadas no período")
		return render(request, "ghost/BOMxOP/bomxop_linha.html")

	detal_ops = DataFrame()

	for i, row in ops.iterrows():
		op = row["op"]
		data = row["data_encerramento_op"]
		request, df_op = explode_estrutura_pela_op(request, op, engine, data, True)
		df_op = df_op.rename(columns={
			"codigo_original":"codigo_pai",
			"descricao_cod_original": "descricao_pai",
			"tipo_original": "tipo_pai"
		})
		df_op["ordem"] = i + 1
		df_op["op_original"] = op
		df_op["data_encerramento_op_original"] = data
		df_op["codigo_original"] = row["produto"]
		df_op["descricao_cod_original"] = row["descricao"]
		df_op["tipo_original"] = row["tipo"]

		detal_ops = concat([detal_ops,df_op], ignore_index=True)
	
	detal_ops = detal_ops.drop(columns=["quant_total_utilizada"])


	def commodity(row):

		if row["tipo_pai"] == "PI":
			descri_pai = row["descricao_pai"]
			if search(r"(?:^| )(HOUSING|INJ|COVER|HEATER HOLDER|CARCACA)(?:$| )",descri_pai):
				return "INJECAO"
			elif search(r"(?:^| )(CALEFATOR|JUMPER|TRIAC|DIOD[OE]|HEATER|HELICAL|ION WIRE CLAMP)(?:$| )",descri_pai):
				return "CALEFATOR"
			elif search(r"(?:^| )(CONTACT SET|CHAPA CONTATO|CONTACT PLATE|SENSOR ELEG)(?:$| )",descri_pai):
				return "PATIN"
			elif search(r"(?:^| )(GRID|FILTER|GRADE)(?:$| )", descri_pai):
				return "TAMPOGRAFIA"
			elif search(r"(?:^| )(PCB[A]?)(?:$| )", descri_pai):
				return "PLACA"

		if row["tipo_insumo"] == "EM":
			return "EMBALAGEM"
		elif row["tipo_insumo"] == "BN":
			return "SERV. INDUST. TERCEIRIZADA"

		texto = str(row["descricao_insumo"]).upper().strip()

		if search(r"SWITCH",texto):
			return "CHAVES"
		elif search(r"^(MOTOR|SET MOTOR)", texto):
			return "MOTOR"
		elif search(r"(PC HS|PC HD|POWER CORD)", texto):
			return "CABO DE FORCA"
		elif search(r"^(PA[ ]?66|PC |MASTER PC)", texto):
			return "INJECAO"
		elif search(r"(^TINTA |TAMPOGRAFIA| TAMPO |CATALI[ZS]ADOR)",texto):
			return "PINTURA/TAMPOGRAFIA"
		elif search(r"(?:^| )(MICA|RIVET)(?:$| )", texto):
			return "CALEFATOR"
		elif search(r"(ALUMIN[I]?UM PLATE|T[H]?ERMISTOR PTC)", texto):
			return "PATIN"
		elif search(r"(?:^| )(PCB[A]?)(?:$| )", texto):
			return "PLACA"
		elif search(r"(?:^| )(PLAST[I]?[C]?)(?:$| )", texto):
			return "PECAS PLASTICAS"
		elif search(r"(?:^| )(HEATER)(?:$| )", texto):
			return "CALEFATOR"
		elif search(r"(?:^| )(HOUSING)", texto):
			return "HOUSING"
		elif search(r"(?:^| )(DIFFUSER)(?:$| )", texto):
			return "DIFUSOR"
		elif search(r"(?:^| )(RUBBER PAD)(?:$| )", texto):
			return "RUBBER PAD"
		elif search(r"(?:^| )(FILTER)(?:$| )", texto):
			return "FILTER"
		
		else:
			return "OUTROS"


	detal_ops["commodity"] = detal_ops.apply(commodity,axis=1)
	detal_ops = detal_ops.rename(columns={"ult_compra_custo_utilizado":"ult_compra_sem_frete"})
	
	# detal_ops = detal_ops.pivot_table(
	# 	values=["ult_compra_sem_frete"],
	# 	index=["codigo_original","descricao_cod_original","tipo_original",
	# 	 "commodity","insumo","descricao_insumo","tipo_insumo"],
	# 	columns=["op_original","data_encerramento_op_original"]
	# ).reset_index()

	# detal_ops.columns = detal_ops.columns.map(lambda x: '<br>'.join(str(i) for i in x))

	# try:
	# 	detal_ops.to_excel("b.xlsx")
	# except:
	# 	print("não imprimiu o detal_ops")

	dicio_tela = {}
	colunas_somadas_resumo = {}
	for prod in detal_ops["codigo_original"].drop_duplicates():
		dicio_tela.update({prod:{}})
		colunas_somadas_resumo.update({prod:{}})
		for commod in detal_ops.loc[detal_ops["codigo_original"] == prod,"commodity"]:
			dicio_tela[prod].update({commod:[]})
			colunas_somadas_resumo[prod].update({commod:[]})

			temp_df = detal_ops.loc[
				(detal_ops["codigo_original"] == prod) & 
				(detal_ops["commodity"] == commod), :
			].pivot_table(
				values=["ult_compra_sem_frete"],
				index=["codigo_original","descricao_cod_original","tipo_original",
				"commodity","insumo","descricao_insumo","tipo_insumo"],
				columns=["op_original","data_encerramento_op_original"]
			).reset_index()

			temp_df.columns = temp_df.columns.map(lambda x: '<br>'.join(str(i) for i in x))

			cabecalhos, rows = get_cabecalhos_e_rows_dataframe(temp_df)

			colunas_somadas = []
			for col in temp_df.columns:
				if "ult_compra_sem_frete" in col:
					soma = round(temp_df[col].sum(),5)
					colunas_somadas.append(soma)
					colunas_somadas_resumo[prod][commod].append((col.split("<br>")[2],soma))
				else:
					colunas_somadas.append("")
			dicio_tela[prod][commod].append([
				cabecalhos,
				colunas_somadas,
				rows
			])

	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(detal_ops)

	context = {
		"caller": "bomxop_linha_post",
		"cabecalhos": cabecalhos,
		"rows": rows,
		"dicio_tela": dicio_tela,
		"colunas_somadas_resumo":colunas_somadas_resumo
	}

	return render(request, "ghost/BOMxOP/bomxop_linha_post.html", context)
