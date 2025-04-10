from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from pandas import read_sql, concat
from sqlalchemy import text

from ghost.utils.funcs import tratamento_data_referencia, get_engine, get_cabecalhos_e_rows_dataframe, forma_string_para_query
from ghost.queries import (
	get_query_ultima_op_por_produto_por_data_de_referencia, get_query_detalhamento_op,
	get_query_ultima_compra_sem_frete
)

def explop(request):
	return render(request, "ghost/explop/explop.html", {"caller": "explop"})

def explop_post(request):

	if request.method != "POST":
		return redirect(reverse("ghost:explop"))
	
	codigo = request.POST.get("codigo")
	if not codigo or len(codigo) not in [7,15]:
		messages.info(request,"Código Inválido")
		return redirect(reverse("ghost:explop"))
	codigo = str(codigo).upper()
	
	data = request.POST.get("data")
	if not data:
		messages.info(request, "Data Inválida")
		return redirect(reverse("ghost:explop"))
	
	data = tratamento_data_referencia(data)
	engine = get_engine()

	query_ult_op = text(get_query_ultima_op_por_produto_por_data_de_referencia())
	ult_op = read_sql(query_ult_op, engine, params={
		"data_referencia": data,
		"codigo": codigo
	})

	if ult_op.empty:
		messages.info(request, "OP não encontrada")
		return redirect(reverse("ghost:explop"))

	explodir_pis = False if not request.POST.get("explodir-pis") else True

	op = ult_op["op"].iloc[0]

	request, detal_ops = explode_estrutura_pela_op(request, op, engine, data, explodir_pis)


	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(df=detal_ops)

	context = {
		"caller": "explop_post",
		"cabecalhos":cabecalhos,
		"rows":rows,
	}

	return render(request, "ghost/explop/explop.html", context)




def explode_estrutura_pela_op(request, op, engine, data, explodir_pis: bool):

	query_ult_op = text(get_query_ultima_op_por_produto_por_data_de_referencia())
	query_detal = text(get_query_detalhamento_op())

	detal_op = read_sql(query_detal, engine, params={"numero_op": op})
	detal_ops = detal_op.copy(deep=True)

	if explodir_pis:
		filtro_pis = detal_op.loc[detal_op["tipo_insumo"]=="PI",:]
		tem_pi = False if filtro_pis.empty else True

		while tem_pi:
			for i, row in filtro_pis.iterrows():
				cod_pi = row["insumo"]
				quant = row["quant_utilizada"]
				data_referencia = tratamento_data_referencia(row["data_encerramento_op"])
				ult_op = read_sql(query_ult_op, engine, params={
					"data_referencia": data_referencia,
					"codigo": cod_pi
				})
				if ult_op.empty: 
					messages.info(request,f"Não foi encontrada OP para o PI {cod_pi}")
					continue
				op = ult_op["op"].iloc[0]
				detal_op = read_sql(query_detal, engine, params={"numero_op": op})
				detal_op["quant_utilizada"] = detal_op["quant_utilizada"] * quant
				detal_ops.at[i,"verificado"] = True
				detal_ops = concat([detal_ops,detal_op],ignore_index=True).reset_index(drop=True)

			filtro_pis = detal_ops.loc[
				(detal_ops["tipo_insumo"]=="PI") &
				(detal_ops["verificado"].isna())
				,:
			]
			
			tem_pi = False if filtro_pis.empty else True
	detal_op = None
	
	if "verificado" in detal_ops.columns:
		detal_ops = detal_ops.drop(columns=["verificado"])
	detal_ops = detal_ops.loc[detal_ops["tipo_insumo"] != "PI",:]

	query_ult_compra = text(get_query_ultima_compra_sem_frete())
	ult_compras = read_sql(query_ult_compra, engine, params={
		"codigos":forma_string_para_query(detal_ops["insumo"].drop_duplicates()),
		"data_referencia":data
	}).drop(columns=["comentario_ultima_compra"])

	detal_ops = detal_ops.merge(
		ult_compras,
		how="left",
		on="insumo"
	)

	detal_ops["ult_compra_custo_utilizado"] = round(detal_ops["quant_utilizada"] * detal_ops["ult_compra_custo_utilizado"],5)

	return request, detal_ops