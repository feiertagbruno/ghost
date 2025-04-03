from django.shortcuts import render,redirect
from django.urls import reverse

from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text

from ghost.queries import (
    get_query_estoque_atual_com_armazens, get_query_produzidos_da_data
)
from ghost.utils.funcs import get_engine
from ghost.views.estruturas import forma_string_codigos

def lista_de_falta(request):
    context = {
        "caller":"lista_de_falta"
    }
    return render(request, "ghost/listadefalta/listadefalta.html", context)

def lista_de_falta_post(request):

    if request.method != "POST":
        return redirect(reverse("ghost:lista-de-falta"))

    codigos:list
    codigos = request.POST.getlist("codigo")
    quantidades = request.POST.getlist("quant")
    datas = request.POST.getlist("mes")
    desconta_prod = True if request.POST.get("desconta-prod") == "on" else False

    for i in range(len(codigos)):
        if not codigos[i] or not quantidades[i]:
            codigos.pop(i)
            quantidades.pop(i)
            datas.pop(i)
        else:
            codigos[i] = str(codigos[i]).upper().strip()
            quantidades[i] = int(quantidades[i])
            datas[i] = datetime.strptime(f"{datas[i]}-01","%Y-%m-%d")
            
    demandas = {
        "codigos": list(codigos),
        "quant": list(quantidades),
        "datas": list(datas)
    }
    
    engine = get_engine()

    if desconta_prod:
        demandas = desconta_producao_do_mes_atual(demandas, engine)

    # ETAPAS DA VIEW
    # 1. ESTRU Explodir as estruturas no dia 1 de cada mês (já tem as datas)
    # 2. PRODUZIDOS Pegar os produzidos, se o usuário marcar para descontar a produção do mês atual
    # 3. DEMANDA - PROD Diminuir os produzidos da demanda que está na variavel demanda
    # 4. ESTOQUE
    # 5. 

    for produto, quant, data in demandas:
        ...


    context = {
        "caller": "lista_de_falta_post"
    }
    return render(request, "ghost/listadefalta/listadefalta_tabela.html", context)

def desconta_producao_do_mes_atual(demandas, engine):
    
    codigos_str = forma_string_codigos(demandas["codigos"])
    hoje = datetime.today()
    primeiro_dia = hoje.replace(day=1)
    ultimo_dia = primeiro_dia.replace(month=primeiro_dia.month + 1, day=1) - timedelta(days=1)
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    query = get_query_produzidos_da_data()

    produzidos = pd.read_sql(text(query), engine, params={
        "data_inicial":primeiro_dia,
        "data_final": ultimo_dia,
        "codigos":codigos_str
    })

    produzidos = produzidos.groupby("codigo", as_index=True)["quant"].sum().reset_index()

    for i in range(len(demandas["codigos"])):
        data = demandas["datas"][i]
        codigo = demandas["codigos"][i]
        quant = demandas["quant"][i]
        if data.month == mes_atual and data.year == ano_atual and codigo in list(produzidos["codigo"]):
            demandas["quant"][i] -= produzidos.loc[produzidos["codigo"] == codigo,"quant"].iloc[0]
            if demandas["quant"][i] < 0:
                nova_quant = -demandas["quant"][i]
                demandas["quant"][i] = 0
                produzidos.loc[produzidos["codigo"] == codigo,"quant"] = nova_quant

    return demandas