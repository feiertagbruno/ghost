from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from pandas import read_sql, concat
from sqlalchemy import text
from typing import Literal

from ghost.utils.funcs import tratamento_data_referencia, get_engine, get_cabecalhos_e_rows_dataframe, forma_string_para_query
from ghost.queries import (
	get_query_ultima_op_por_produto_por_data_de_referencia, get_query_detalhamento_op,
	get_query_ultima_compra_sem_frete, get_query_ultima_compra_produtos,
	get_query_ultimo_fechamento_produtos
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
	
	qual_custo = request.POST.get("qual-custo")
	
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

	request, detal_ops, _ = explode_estrutura_pela_op(
		request=request, 
		op=op, 
		engine=engine, 
		data=data, 
		explodir_pis=explodir_pis,
		qual_custo=qual_custo
	)


	cabecalhos, rows = get_cabecalhos_e_rows_dataframe(df=detal_ops)

	context = {
		"caller": "explop_post",
		"cabecalhos":cabecalhos,
		"rows":rows,
	}

	return render(request, "ghost/explop/explop.html", context)




def explode_estrutura_pela_op(
		request, op, engine, data, explodir_pis: bool,
		qual_custo: Literal["uesf","uecf","uf"]
):
	"""uesf -> Última entrada sem frete | uecf -> Última entrada com frete |
	uf -> Último Fechamento"""

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

	if qual_custo == "uesf":
		query_ult_compra = text(get_query_ultima_compra_sem_frete())
		df_custo = read_sql(query_ult_compra, engine, params={
			"codigos":forma_string_para_query(detal_ops["insumo"].drop_duplicates()),
			"data_referencia":data
		}).drop(columns=["comentario_ultima_compra"])
		coluna_custo = "ult_compra_custo_utilizado"
	elif qual_custo == "uecf":
		query_ult_compra = text(get_query_ultima_compra_produtos())
		df_custo = read_sql(query_ult_compra,engine, params={
			"codigos":forma_string_para_query(detal_ops["insumo"].drop_duplicates()),
			"data_referencia":data
		}).drop(columns=["comentario_ultima_compra"])
		coluna_custo = "ult_compra_custo_utilizado"
	elif qual_custo == "uf":
		query_ult_fechamento = text(get_query_ultimo_fechamento_produtos())
		df_custo = read_sql(query_ult_fechamento,engine,params={
			"codigos":forma_string_para_query(detal_ops["insumo"].drop_duplicates()),
			"data_referencia":data
		}).drop(columns=["comentario_fechamento"])
		coluna_custo = "fechamento_custo_utilizado"

	detal_ops = detal_ops.merge(
		df_custo,
		how="left",
		on="insumo"
	)

	detal_ops[coluna_custo] = round(detal_ops["quant_utilizada"] * detal_ops[coluna_custo],5)

	return request, detal_ops, coluna_custo