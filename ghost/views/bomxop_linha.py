from django.shortcuts import render
from django.contrib import messages

from pandas import read_sql, DataFrame, concat
from sqlalchemy import text
from re import match

from ghost.utils.funcs import tratamento_data_referencia, forma_string_para_query, get_cabecalhos_e_rows_dataframe
from ghost.queries import (
	get_query_numeros_op_por_periodo, get_query_detalhamento_op
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
		codigos = forma_string_para_query([str(codigo).upper().strip() for codigo in codigos_pre if codigo])
	else:
		codigos = None
	
	engine = get_engine()

	query_ops = get_query_numeros_op_por_periodo()
	ops = read_sql(text(query_ops), engine, params={
		"data_inicial": data_inicial,
		"data_final": data_final,
		"codigos": codigos
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
		df_op["ordem"] = i + 1

		detal_ops = concat([detal_ops,df_op], ignore_index=True)


	def commodity(row):

		if row["tipo_insumo"] == "EM":
			return "EMBALAGEM"

		texto = str(row["descricao_insumo"]).upper().strip()

		if match(r"^MOTOR", texto):
			return "MOTOR"
		elif match(r"^(PA66|PA 66)", texto):
			return "INJEÇÃO"
		elif match(r"^(TINTA )",texto):
			return "PINTURA"
		elif match(r"(PC HS|PC HD)", texto):
			return "CABO DE FORÇA"
		else:
			return ""


	detal_ops["commodity"] = detal_ops.apply(commodity,axis=1)

	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(detal_ops)

	context = {
		"caller": "bomxop_linha_post",
		"cabecalhos": cabecalhos,
		"rows": rows
	}

	return render(request, "ghost/BOMxOP/bomxop_linha_post.html", context)
