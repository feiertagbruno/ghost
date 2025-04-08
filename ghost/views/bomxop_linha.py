from django.shortcuts import render
from django.contrib import messages

from ghost.utils.funcs import tratamento_data_referencia

def bomxop_linha_do_tempo(request):
	return render(request, "ghost/BOMxOP/bomxop_linha.html")

def bomxop_linha_do_tempo_post(request):

	if request.method != "POST":
		return render(request, "ghost/BOMxOP/bomxop_linha.html")

	data_inicial = request.POST.get("data-inicial")
	data_final = request.POST.get("data-final")
	if not data_inicial or not data_final:
		messages.info(request, "Datas Inválidas")
		return render(request, "ghost/BOMxOP/bomxop_linha.html")
	
	data_inicial = tratamento_data_referencia(data_inicial)
	data_final = tratamento_data_referencia(data_inicial)

	traz_prod = request.POST.get("traz-produzidos")
	codigos_pre = None
	if traz_prod != "on":
		codigos_pre = request.POST.get("codigos")
		if not codigos_pre:
			messages.info(request, "Códigos Inválidos")
			return render(request, "ghost/BOMxOP/bomxop_linha.html")
		codigos_pre = codigos_pre.split("\r\n")
		codigos = [str(codigo).upper().strip() for codigo in codigos_pre if codigo]

	return render(request, "ghost/BOMxOP/bomxop_linha.html")
