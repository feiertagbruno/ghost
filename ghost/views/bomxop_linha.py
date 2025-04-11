from django.shortcuts import render
from django.contrib import messages

from pandas import read_sql, DataFrame, concat, read_excel
from sqlalchemy import text
from re import search
from datetime import date

from ghost.utils.funcs import tratamento_data_referencia, forma_string_para_query, get_cabecalhos_e_rows_dataframe
from ghost.queries import (
	get_query_numeros_op_varios_periodos_somente_PA
)
from ghost.utils.funcs import get_engine, get_info_produtos
from ghost.views.explop import explode_estrutura_pela_op

def bomxop_linha_do_tempo(request):
	return render(request, "ghost/BOMxOP/bomxop_linha.html", {"caller":"bomxop_linha"})

def bomxop_linha_do_tempo_post(request):

	if request.method != "POST":
		return render(request, "ghost/BOMxOP/bomxop_linha.html")

	qual_custo = request.POST.get("qual-custo")

	datas_iniciais_str = request.POST.getlist("data-inicial")
	datas_iniciais = []
	datas_finais_str = request.POST.getlist("data-final")
	datas_finais = []
	if len(datas_iniciais_str) == 0 or len(datas_finais_str) == 0:
		messages.info(request, "Datas Inválidas")
		return render(request, "ghost/BOMxOP/bomxop_linha.html")
	
	for data_inicial in datas_iniciais_str:
		if data_inicial:
			data_inicial = tratamento_data_referencia(data_inicial)
			datas_iniciais.append(data_inicial)
	for data_final in datas_finais_str:
		if data_final:
			data_final = tratamento_data_referencia(data_final)
			datas_finais.append(data_final)

	if len(datas_iniciais) != len(datas_finais):
		messages.info(request, "Erro no processamento das datas digitadas")
		return render(request, "ghost/BOMxOP/bomxop_linha.html")
	
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

	traz_budget = True if request.POST.get("traz-budget") == "on" else False
	
	if traz_budget:
		budget = read_excel("budget25.xlsx",sheet_name="detal_std")

		info_prod = get_info_produtos(forma_string_para_query(budget["codigo_original"].drop_duplicates()), engine)
		budget = budget.merge(info_prod,how="left",left_on="codigo_original",right_on="codigo").drop(columns=["origem_produto","codigo"])\
			.rename(columns={"descricao_produto":"descricao_cod_original","tipo_produto":"tipo_original"})

		info_prod = get_info_produtos(forma_string_para_query(budget["codigo_pai"].drop_duplicates()), engine)
		budget = budget.merge(info_prod,how="left",left_on="codigo_pai",right_on="codigo").drop(columns=["origem_produto","codigo"])\
			.rename(columns={"descricao_produto":"descricao_pai","tipo_produto":"tipo_pai"})
		
		info_prod = get_info_produtos(forma_string_para_query(budget["insumo"].drop_duplicates()),engine)
		budget = budget.merge(info_prod,how="left",left_on="insumo",right_on="codigo").drop(columns=["origem_produto","codigo"])\
			.rename(columns={"descricao_produto":"descricao_insumo","tipo_produto":"tipo_insumo"})

		budget["op_original"] = "00000000000"
		budget["data_encerramento_op_original"] = date(2024,10,19)

		

	query_ops = get_query_numeros_op_varios_periodos_somente_PA(datas_iniciais, datas_finais)
	ops = read_sql(text(query_ops), engine, params={
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
	# premissa não precisa
	# detal_ops["ult_compra_custo_utilizado"] = round(detal_ops["ult_compra_custo_utilizado"] + (detal_ops["ult_compra_custo_utilizado"] * 0.1),5)


	if traz_budget:
		budget = budget.loc[budget["codigo_original"].isin(ops["produto"]),:]
		detal_ops = concat([budget,detal_ops])

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
				return "ESTAMPARIA"
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
			return "TAMPOG E PINTURA"
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
	

	dicio_tela = {}
	colunas_somadas_resumo = {}
	for prod in detal_ops["codigo_original"].drop_duplicates():
		dicio_tela.update({prod:{}})
		colunas_somadas_resumo.update({prod:{}})
		soma_por_coluna = {}
		for commod in detal_ops.loc[detal_ops["codigo_original"] == prod,"commodity"].drop_duplicates():
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

			temp_df = temp_df.drop(columns=["codigo_original<br><br>","descricao_cod_original<br><br>","tipo_original<br><br>"])

			colunas_somadas = []
			for col in temp_df.columns:
				if "ult_compra_sem_frete" in col:
					soma = round(temp_df[col].sum(),5)
					temp_df[col] = round(temp_df[col],5)
					colunas_somadas.append(soma)
					colunas_somadas_resumo[prod][commod].append((col.split("<br>")[2],soma))

					if col not in soma_por_coluna:
						soma_por_coluna.update({col:soma})
					else:
						soma_por_coluna[col] += soma

				else:
					colunas_somadas.append("")

			cabecalhos, rows = get_cabecalhos_e_rows_dataframe(temp_df)
				
			dicio_tela[prod][commod].append([
				cabecalhos,
				colunas_somadas,
				rows
			])

		colunas_somadas_resumo[prod].update({"TOTAL":[]})
		for key,val in soma_por_coluna.items():
			colunas_somadas_resumo[prod]["TOTAL"].append((key.split("<br>")[2],round(val,5)))

	try:
		detal_ops.to_excel("b.xlsx")
	except:
		print("não imprimiu o detal_ops")

	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(detal_ops)

	context = {
		"caller": "bomxop_linha_post",
		"cabecalhos": cabecalhos,
		"rows": rows,
		"dicio_tela": dicio_tela,
		"colunas_somadas_resumo":colunas_somadas_resumo
	}

	return render(request, "ghost/BOMxOP/bomxop_linha_post.html", context)
