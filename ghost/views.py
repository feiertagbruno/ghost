from django.shortcuts import render,redirect
from django.urls import reverse
from datetime import datetime
from ghost.functions.estruturas import (
	gerar_relatorio_excel_estruturas_simples, gerar_multiestruturas,
	estrutura_simples, get_engine, tratamento_data_referencia
)
from django.contrib import messages
from django.http import FileResponse
from ghost.functions.OPs import (
	get_info_op, combina_estrutura_e_op, combina_custos_totais_estrutura_e_op, 
	gerar_relatorio_excel_bomxop_simples, get_numeros_OPs_por_periodo
)

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

	request, compilado_estruturas, compilado_custos_totais = gerar_multiestruturas(request, produtos_filtrados, data_referencia)

	if compilado_custos_totais.empty:
		messages.info(request, "Sua busca retornou sem resultados")
		return redirect(reverse("ghost:ghost"))
	
	caminho_relatorio_excel = gerar_relatorio_excel_estruturas_simples(compilado_estruturas, compilado_custos_totais, data_referencia)

	compilado_custos_totais["data_referencia"] = compilado_custos_totais["data_referencia"].dt.strftime("%d/%m/%Y")

	custos_totais_dict = compilado_custos_totais.to_dict(orient="records")

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

def extrai_bomxop_pela_op(request, numero_op):

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

	return FileResponse(open(caminho_arquivo,"rb"),as_attachment=True, filename="BOM x OP Simples.xlsx")




def extrai_bomxop_por_periodo(request, data_inicial, data_final):
	
	engine = get_engine()

	OPs = get_numeros_OPs_por_periodo(data_inicial, data_final, engine)





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

	return redirect(reverse("ghost:bomxop"))

#extrai_bomxop_pela_op("","33056001001")