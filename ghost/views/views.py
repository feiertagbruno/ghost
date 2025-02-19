from django.shortcuts import render,redirect
from django.urls import reverse
from datetime import datetime
from ghost.views.estruturas import (
	gerar_relatorio_excel_estruturas_simples, gerar_multiestruturas,
	estrutura_simples
)
from django.contrib import messages
from django.http import FileResponse
from ghost.views.OPs import (
	get_info_op, combina_estrutura_e_op, combina_custos_totais_estrutura_e_op, 
	gerar_relatorio_excel_bomxop_simples, get_numeros_OPs_por_periodo,
	get_numero_op_pelo_produto
)
import pandas as pd
from ghost.models import Processamento
from django.http import JsonResponse
import json
from ghost.utils.funcs import (
	extrai_data_fechamento_de_string_yyyy_mm, get_engine,
	tratamento_data_referencia
)

pd.set_option("future.no_silent_downcasting", True)

def home(request):
	return render(request, "ghost/home.html")

def ghost(request):
	data_referencia = datetime.strftime(datetime.today().date(),"%Y-%m-%d")
	context = {
		"data_referencia":data_referencia
	}
	return render(request, "ghost/multiestruturas/multi_simples.html", context)

def multiestruturas(request):
	
	if request.method != "POST": return redirect(reverse("ghost:ghost"))

	produtos = request.POST.get("codigos-produtos")

	if not produtos: return redirect(reverse("ghost:ghost"))

	produtos = produtos.split("\r\n")
	produtos_filtrados = [item for item in produtos if item != ""]

	data_referencia = request.POST.get("data-referencia")
	if not data_referencia: data_referencia = datetime.today().date()

	considera_frete = request.POST.get("considera-frete")
	traz_preco_futuro = request.POST.get("traz-preco-futuro")

	request, compilado_estruturas, compilado_custos_totais = gerar_multiestruturas(
		request=request, 
		produtos=produtos_filtrados, 
		data_referencia=data_referencia,
		considera_frete=considera_frete,
		traz_preco_futuro=traz_preco_futuro
	)

	if compilado_custos_totais.empty:
		messages.info(request, "Sua busca retornou sem resultados")
		return redirect(reverse("ghost:ghost"))
	
	processamento = Processamento.objects.filter(
		codigo_identificador = request.POST.get("codigo-identificador","a"),
		caller = "multiestruturas",
		finalizado = False
	)
	if processamento.exists():
		processamento_atual = processamento.first()
		processamento_atual.porcentagem = "99%"
		processamento_atual.mensagem1 = "Finalizando"
		processamento_atual.mensagem2 = "Compondo relatório em Excel"
		processamento_atual.save()

	caminho_relatorio_excel = gerar_relatorio_excel_estruturas_simples(
		compilado_estruturas, compilado_custos_totais, data_referencia
	)

	compilado_custos_totais["data_referencia"] = compilado_custos_totais["data_referencia"].dt.strftime("%d/%m/%Y")

	custos_totais_dict = compilado_custos_totais.to_dict(orient="records")

	if processamento.exists():
		processamento_atual.porcentagem = "100%"
		processamento_atual.finalizado = True
		processamento_atual.save()

	context = {
		"custos_totais": custos_totais_dict,
		"path_xlsx": caminho_relatorio_excel,
	}

	return render(request,"ghost/multiestruturas/multi_simples_post.html", context)
	
def baixar_relatorio_multiestruturas(request):
	if request.method != "POST": return redirect(reverse("ghost:home"))

	caminho_arquivo = request.POST.get("path-xlsx")
	
	if not caminho_arquivo:
		messages.error(request, "Algo saiu errado na geração do relatório.")
		return redirect(reverse("ghost:home"))

	return FileResponse(open(caminho_arquivo,"rb"),as_attachment=True, filename="Estruturas.xlsx")

def bomxop(request):
	return render(request, "ghost/BOMxOP/bomxop.html")

def extrai_bomxop_pela_op(request, numero_op, engine = None):

	if not engine:
		engine = get_engine()

	codigo, data_referencia, consulta_op, custos_totais_op = get_info_op(numero_op, engine)

	if not codigo: return redirect(reverse("ghost:bomxop"))

	estrutura, custos_totais_estrutura = estrutura_simples(codigo, data_referencia, engine, False)
	estrutura_com_op = combina_estrutura_e_op(estrutura, consulta_op)

	custos_totais_estrutura_op = combina_custos_totais_estrutura_e_op(custos_totais_estrutura, custos_totais_op)

	caminho_relatorio_excel = gerar_relatorio_excel_bomxop_simples(estrutura_com_op, custos_totais_estrutura_op, data_referencia)

	custos_totais_estrutura_op["data_referencia"] = custos_totais_estrutura_op["data_referencia"].dt.strftime("%d/%m/%Y")

	custos_totais_dict = custos_totais_estrutura_op.to_dict(orient="records")

	context = {
		"custos_totais": custos_totais_dict,
		"path_xlsx": caminho_relatorio_excel,
	}

	return render(request,"ghost/BOMxOP/bomxop_post.html", context)




def baixar_relatorio_bomxop_simples(request):
	if request.method != "POST": return redirect(reverse("ghost:home"))

	caminho_arquivo = request.POST.get("path-xlsx")
	
	if not caminho_arquivo:
		messages.error(request, "Algo saiu errado na geração do relatório.")
		return redirect(reverse("ghost:home"))

	return FileResponse(open(caminho_arquivo,"rb"),as_attachment=True, filename="BOM x OP.xlsx")




def extrai_bomxop_por_periodo(request, data_inicial, data_final,considera_frete=True):
	
	engine = get_engine()
	OPs = get_numeros_OPs_por_periodo(data_inicial, data_final, engine)

	data_std = request.POST.get('data-std')
	if data_std:
		if isinstance(data_std,str):
			data_std = extrai_data_fechamento_de_string_yyyy_mm(data_std)

	if not OPs:
		messages.info(request, "Não existem OPs finalizadas neste período.")
		return redirect(reverse("ghost:bomxop"))

	compilado_estrutura_com_op = pd.DataFrame()
	compilado_custos_totais_estrutura_op = pd.DataFrame()

	################ processamento
	processamento = Processamento.objects.create(
		codigo_identificador = request.POST.get("codigo-identificador","a"),
		caller = "bomxop",
		porcentagem = "0",
		mensagem1 = "Processando",
		mensagem2 = ""
	)
	################

	for index, numero_op in enumerate(OPs):

		################ processamento
		processamento.porcentagem = f"{int((index+1)/len(OPs)*98)}%"
		processamento.mensagem2 = f'Obtendo informações da OP {numero_op}'
		processamento.save()
		################ 

		codigo, data_referencia, consulta_op, custos_totais_op = get_info_op(
			numero_op=numero_op, 
			engine=engine, 
			data_std=data_std,
			considera_frete=considera_frete
		)

		################ processamento
		processamento.mensagem2 = f'Extraindo estrutura de {codigo}'
		processamento.save()
		################

		estrutura, custos_totais_estrutura = estrutura_simples(
			codigo=codigo, 
			data_referencia=data_referencia, 
			engine=engine, 
			abre_todos_os_PIs=False, 
			data_std=data_std,
			considera_frete=considera_frete
		)

		################ processamento
		processamento.mensagem2 = f'Unindo estrutura e OP'
		processamento.save()
		################
		
		estrutura_com_op = combina_estrutura_e_op(estrutura, consulta_op)
		custos_totais_estrutura_op = combina_custos_totais_estrutura_e_op(custos_totais_estrutura, custos_totais_op)

		compilado_estrutura_com_op = pd.concat([compilado_estrutura_com_op, estrutura_com_op],ignore_index=True)
		compilado_custos_totais_estrutura_op = pd.concat([compilado_custos_totais_estrutura_op, custos_totais_estrutura_op],ignore_index=True)


	################ processamento
	processamento.porcentagem = "99%"
	processamento.mensagem1 = 'Finalizando'
	processamento.mensagem2 = 'Compondo o relatório em Excel'
	processamento.save()
	################

	caminho_relatorio_excel = gerar_relatorio_excel_bomxop_simples(
		compilado_estrutura_com_op, compilado_custos_totais_estrutura_op, data_referencia
	)

	compilado_custos_totais_estrutura_op["data_referencia"] = compilado_custos_totais_estrutura_op["data_referencia"].dt.strftime("%d/%m/%Y")

	custos_totais_dict = compilado_custos_totais_estrutura_op.to_dict(orient="records")

	context = {
		"custos_totais": custos_totais_dict,
		"path_xlsx": caminho_relatorio_excel,
	}

	################ processamento
	processamento.finalizado = True
	processamento.save()
	################

	return render(request,"ghost/BOMxOP/bomxop_post.html", context)




def bomxop_post(request):

	if request.method != "POST":
		return redirect(reverse("ghost:bomxop"))

	numero_op = request.POST.get("numero-op")

	if numero_op:
		if len(numero_op) != 11:
			messages.info(request, "Há um erro de digitação no número da OP")
			return redirect(reverse("ghost:bomxop"))

		return extrai_bomxop_pela_op(request, numero_op)
	
	data_inicial = request.POST.get("data-inicial")
	data_final = request.POST.get("data-final")

	if data_inicial and data_final:
		data_inicial = tratamento_data_referencia(data_inicial)
		data_final = tratamento_data_referencia(data_final)
		return extrai_bomxop_por_periodo(request, data_inicial, data_final)
	
	produto = request.POST.get("codigo-produto")

	if not produto:
		messages.info(request, "Dados Inválidos")
		return redirect(reverse("ghost:bomxop"))
	
	produto = str(produto).strip().upper()

	if len(produto) != 7 and len(produto) != 15:
		messages.info(request, "Há um erro de digitação no produto")
		return redirect(reverse("ghost:bomxop"))
	
	engine = get_engine()
	numero_op = get_numero_op_pelo_produto(produto, engine)
	if numero_op:
		return extrai_bomxop_pela_op(request, numero_op, engine)


	return redirect(reverse("ghost:bomxop"))




def buscar_processamento(request):

	response = {
		"porcentagem": "",
		"mensagem1": "Processando",
		"mensagem2": "",
	}
	data = json.loads(request.body)

	codigo = data.get("codigo_identificador", "a")
	caller = data.get("caller", "a")

	processamento = Processamento.objects.filter(codigo_identificador = codigo, caller = caller, finalizado = False)
	if processamento.exists():
		processamento = processamento.first()
		response = {
			"porcentagem": processamento.porcentagem,
			"mensagem1": processamento.mensagem1,
			"mensagem2": processamento.mensagem2,
		}

	return JsonResponse(response)




def bomxopstd(request):
	return render(request, "ghost/BOMxOP/bomxopstd.html")




def extrai_bomxopstd_pela_op(request, numero_op, engine = None, considera_frete=True):

	if not engine:
		engine = get_engine()
	
	data_std = request.POST.get("data-std")
	if data_std:
		if isinstance(data_std, str):
			data_std = extrai_data_fechamento_de_string_yyyy_mm(data_std)

	codigo, data_referencia, consulta_op, custos_totais_op = get_info_op(
		numero_op=numero_op, 
		engine=engine, 
		data_std=data_std, 
		considera_frete=considera_frete
	)

	if not codigo: return redirect(reverse("ghost:bomxopstd"))

	estrutura, custos_totais_estrutura = estrutura_simples(
		codigo=codigo, 
		data_referencia=data_referencia, 
		engine=engine, 
		abre_todos_os_PIs=False,
		data_std=data_std,
		considera_frete=considera_frete
	)
	estrutura_com_op = combina_estrutura_e_op(estrutura, consulta_op)

	custos_totais_estrutura_op = combina_custos_totais_estrutura_e_op(custos_totais_estrutura, custos_totais_op)

	caminho_relatorio_excel = gerar_relatorio_excel_bomxop_simples(estrutura_com_op, custos_totais_estrutura_op, data_referencia)

	custos_totais_estrutura_op["data_referencia"] = custos_totais_estrutura_op["data_referencia"].dt.strftime("%d/%m/%Y")

	custos_totais_dict = custos_totais_estrutura_op.to_dict(orient="records")

	context = {
		"custos_totais": custos_totais_dict,
		"path_xlsx": caminho_relatorio_excel,
	}

	return render(request,"ghost/BOMxOP/bomxop_post.html", context)





def bomxopstd_post(request):

	if request.method != "POST":
		return redirect(reverse("ghost:bomxopstd"))

	numero_op = request.POST.get("numero-op")
	considera_frete = request.POST.get("considera-frete")

	if numero_op:
		if len(numero_op) != 11:
			messages.info(request, "Há um erro de digitação no número da OP")
			return redirect(reverse("ghost:bomxopstd"))

		return extrai_bomxopstd_pela_op(
			request=request, 
			numero_op=numero_op, 
			considera_frete=considera_frete
		)
	
	data_inicial = request.POST.get("data-inicial")
	data_final = request.POST.get("data-final")

	if data_inicial and data_final:
		data_inicial = tratamento_data_referencia(data_inicial)
		data_final = tratamento_data_referencia(data_final)
		return extrai_bomxop_por_periodo(
			request=request, 
			data_inicial=data_inicial, 
			data_final=data_final,
			considera_frete=considera_frete
		)
	
	produto = request.POST.get("codigo-produto")

	if not produto:
		messages.info(request, "Dados Inválidos")
		return redirect(reverse("ghost:bomxopstd"))
	
	produto = str(produto).strip().upper()

	if len(produto) != 7 and len(produto) != 15:
		messages.info(request, "Há um erro de digitação no produto")
		return redirect(reverse("ghost:bomxopstd"))
	
	engine = get_engine()
	numero_op = get_numero_op_pelo_produto(produto, engine)
	if numero_op:
		return extrai_bomxopstd_pela_op(request, numero_op, engine)

	return redirect(reverse("ghost:bomxopstd"))