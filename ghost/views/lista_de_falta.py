from django.shortcuts import render,redirect
from django.urls import reverse

from datetime import datetime
import pandas as pd
from sqlalchemy import text

from ghost.queries import get_query_estoque_atual_com_armazens
from ghost.utils.funcs import get_engine

def lista_de_falta(request):
    context = {
        "caller":"lista_de_falta"
    }
    return render(request, "ghost/listadefalta/listadefalta.html", context)

def lista_de_falta_post(request):

    if request.method != "POST":
        return redirect(reverse("ghost:lista-de-falta"))


    codigos = request.POST.getlist("codigo")
    quantidades = request.POST.getlist("quant")
    datas = request.POST.getlist("mes")
    desconta_prod = True if request.POST.get("desconta-prod") == "on" else False

    demanda = []

    for i in range(len(codigos)):
        if codigos[i] and quantidades[i]:
            demanda.append([
                str(codigos[i]).strip().upper(),
                int(quantidades[i]),
                datetime.strptime(f"{datas[i]}-01","%Y-%m-%d")
            ])
    
    engine = get_engine()

    # ETAPAS DA VIEW
    # 1. ESTRU Explodir as estruturas no dia 1 de cada mês (já tem as datas)
    # 2. PRODUZIDOS Pegar os produzidos, se o usuário marcar para descontar a produção do mês atual
    # 3. DEMANDA - PROD Diminuir os produzidos da demanda que está na variavel demanda
    # 4. ESTOQUE
    # 5. 

    query = get_query_estoque_atual_com_armazens()
    estoque = pd.read_sql(text(query),engine,params={
        #codigos: pegar estruturas primeiro
    })

    context = {
        "caller": "lista_de_falta_post"
    }
    return render(request, "ghost/listadefalta/listadefalta_tabela.html", context)